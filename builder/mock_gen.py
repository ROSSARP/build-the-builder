"""Generate a Cloudflare Workers mock bank from a service contract + test customers.

    python3 builder/mock_gen.py <case_folder> --deploy          # final package, one step
    python3 builder/mock_gen.py <case_folder> [--out mock]      # generate, no deploy
    python3 builder/mock_gen.py <contract_file> <customers_file> [--out mock] [--name NAME]
                                [--model claude-sonnet-5-5] [--repairs 2] [--no-verify] [--no-llm] [--selftest]

<case_folder> is the package as delivered: a folder or a .zip (Markdown, .docx, .pdf,
.xlsx are read through builder/read_case.py when its optional libraries are installed;
a plain fallback reads the text formats). The service contract and the test customers
are located inside it by filename and content; a Markdown brief, a contract document and
the customer table can all be the same package, so the contract side of the prompt gets
the whole package ordered contract-likelihood-first. With two file arguments the two
inputs are taken exactly as given (a single file argument is used as both).
`--deploy` then runs mock/deploy.sh against the generated files (needs CF_API_TOKEN +
CF_ACCOUNT_ID) and prints MOCK_URL=<workers.dev host + contract base path> for
builder/build.py.

`generate_mock(contract_text, customers_text, out_dir)` writes into out_dir:

    worker.js       one complete Cloudflare Worker (ES module) implementing every
                    contract endpoint, the identity gate, contract error semantics and
                    faults, a deterministic per-customer ledger, GET ledger routes and
                    /health (200).
    seed.json       the test customers, normalised for the worker (embedded verbatim
                    into worker.js by replacing the __SEED_JSON__ placeholder).
    README.md       generated runbook: endpoints, ledger shape, the persistence
                    trade-off, deploy + health-check steps.
    endpoints.json  machine-readable route manifest; mock/deploy.sh reads it to probe
                    /health and every GET endpoint after deploying.
    analysis.json   the contract analysis the worker was generated from.
    wrangler.toml   deploy config; carries the optional MOCK_KV block when the ledger
                    must survive across Worker isolates.
    gen-trace.log   one line per model call, mirroring builder/build.py's trace style.

Model calls go through the same `claude` CLI pattern as builder/build.py:
subprocess `claude -p ... --output-format json --model ...` with the enclosing
session's model overrides stripped from the environment. Environment knobs:
MOCK_GEN_MODEL (or BUILDER_MODEL) picks the model, MOCK_GEN_TIMEOUT bounds one call
(default 900 s), MOCK_GEN_BUDGET bounds the whole generation (default 1800 s).

Nothing in the generation path deploys anything: deploy is mock/deploy.sh (wrangler or
the Cloudflare REST API) with CF_API_TOKEN + CF_ACCOUNT_ID, invoked by --deploy or by
hand.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = (os.environ.get("MOCK_GEN_MODEL") or os.environ.get("BUILDER_MODEL")
         or "claude-sonnet-5-5")
LLM_TIMEOUT = int(os.environ.get("MOCK_GEN_TIMEOUT", "900"))
BUDGET = int(os.environ.get("MOCK_GEN_BUDGET", "1800"))  # total seconds for all model calls
SEED_PLACEHOLDER = "__SEED_JSON__"

TRACE = []  # filled by generate_mock(); every model call lands here


def log(msg):
    print(msg, flush=True)


def trace_line(text):
    TRACE.append(text)


# --------------------------------------------------------------------------- llm
def llm(prompt, purpose, timeout=None):
    """One model call through the claude CLI (same pattern as builder/build.py)."""
    tmo = timeout or LLM_TIMEOUT
    t0 = time.time()
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--model", MODEL]
    # strip this session's model overrides so the spawned CLI uses the models we ask for
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL")
           and not k.startswith(("CLAUDE_MODEL", "ANTHROPIC_DEFAULT_"))}
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=tmo, env=env)
    model = MODEL
    if r.returncode != 0 or "unrecognized_model" in (r.stderr or ""):
        model = "default"
        r = subprocess.run(["claude", "-p", prompt, "--output-format", "json"],
                           capture_output=True, text=True, timeout=tmo, env=env)
    took = time.time() - t0
    out = r.stdout.strip()
    try:
        result = json.loads(out).get("result", "")
    except Exception:
        result = None
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    result = json.loads(line).get("result", "")
                    break
                except Exception:
                    result = None
        if result is None:
            result = out
    trace_line(f"model call: {model}, purpose: {purpose}, "
               f"prompt {len(prompt)} chars, answer {len(str(result))} chars, {took:.0f} s")
    log(f"-- model call ({purpose}): {len(prompt)} chars in, {len(str(result))} chars out, {took:.0f} s")
    if r.returncode != 0 and not str(result).strip():
        raise RuntimeError(f"model call failed ({purpose}): {r.stderr[:400]}")
    return str(result)


def extract_json(text):
    """The JSON object inside an LLM answer, fences and chatter stripped."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in the model answer")
    return json.loads(t[start:end + 1])


def extract_code(text):
    """The JavaScript file inside an LLM answer (fences and prose stripped)."""
    t = str(text).strip()
    m = re.search(r"```(?:javascript|js|worker|mjs)?\s*\n(.*?)```", t, re.S)
    if m:
        return m.group(1).strip() + "\n"
    lines = t.splitlines()
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("//") or s.startswith("/*") or s.startswith("const ") or s.startswith("export "):
            return "\n".join(lines[i:]).strip() + "\n"
    return t + "\n"


_TOKEN_RE = re.compile(r"__[A-Z][A-Z_]*__|<<<[A-Z]+>>>")


def fill_tokens(text, mapping):
    """Single-pass substitution: inserted text can never be substituted again.

    Tokens not in the mapping (notably __SEED_JSON__, which must survive into the
    model's answer) are left untouched.
    """
    return _TOKEN_RE.sub(lambda m: str(mapping.get(m.group(0), m.group(0))), text)


# ------------------------------------------------------- deterministic fallbacks
def _schema_fields(schema):
    """Compact {field: type/enum note} from an OpenAPI schema object."""
    out = {}
    if not isinstance(schema, dict):
        return out
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    for name, spec in props.items():
        if not isinstance(spec, dict):
            out[name] = "unknown"
            continue
        kind = spec.get("type") or ("object" if spec.get("properties") else "string")
        note = kind
        if spec.get("enum"):
            note = f"enum({', '.join(str(x) for x in spec['enum'])})"
        elif kind == "array":
            item = spec.get("items") or {}
            note = f"array of {item.get('type', 'object')}"
        if name in required:
            note += " (required)"
        desc = (spec.get("description") or "").strip()
        if desc:
            note += f" - {desc[:120]}"
        out[name] = note
    return out


def _op_schema(paths, path, method):
    op = ((paths.get(path) or {}).get(method)) or {}
    body = (op.get("requestBody") or {}).get("content", {}).get("application/json", {})
    resp = (op.get("responses") or {}).get("200", {}).get("content", {}) \
        .get("application/json", {})
    return op, _schema_fields(body.get("schema")), _schema_fields(resp.get("schema"))


def naive_analysis(contract_text):
    """Deterministic fallback: read an OpenAPI JSON contract without a model call."""
    try:
        doc = json.loads(contract_text)
    except Exception:
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("paths"), dict):
        return None
    base = ""
    servers = doc.get("servers") or []
    if servers and isinstance(servers[0], dict):
        base = urlsplit(str(servers[0].get("url") or "")).path.rstrip("/")
    endpoints = []
    for path, ops in doc["paths"].items():
        if not isinstance(ops, dict):
            continue
        for method in ("get", "post", "put", "patch", "delete"):
            if method not in ops:
                continue
            op, req, resp = _op_schema(doc["paths"], path, method)
            endpoints.append({
                "method": method.upper(),
                "path": (base + path) or path,
                "summary": (op.get("summary") or "").strip(),
                "request_fields": req,
                "response_fields": resp,
                "errors": [{"when": k, "response": (v.get("description") or "")[:160]}
                           for k, v in (op.get("responses") or {}).items() if k != "200"],
            })
    info = doc.get("info") or {}
    return {
        "service_name": (info.get("title") or "bank-mock").strip(),
        "base_path": base,
        "state_model": "cross-call" if any(e["method"] != "GET" for e in endpoints) else "stateless",
        "state_reason": "tool endpoints write state that later reads and the ledger must see",
        "endpoints": endpoints,
        "identity": {},
        "ledger": {},
        "sessions": {},
        "faults": [],
        "unknown_customer_policy": "",
        "extra_notes": [],
        "source": "naive OpenAPI parse (no model call)",
    }


def naive_seed(customers_text):
    """Deterministic fallback: normalise a JSON customer file without a model call."""
    try:
        data = json.loads(customers_text)
    except Exception as exc:
        raise ValueError(f"customers file is not JSON and the seed model call failed: {exc}")
    if isinstance(data, dict):
        cases = data.get("customers") or data.get("cases") or data.get("test_customers") or []
    elif isinstance(data, list):
        cases = data
    else:
        raise ValueError("customers file is neither a JSON list nor an object with customers[]")
    customers = []
    for i, c in enumerate(cases):
        if not isinstance(c, dict):
            continue
        cid = c.get("customer_id") or c.get("id") or f"case-{i + 1}"
        variables = c.get("variables") or {}
        name = (f"{variables.get('first_name', '')} {variables.get('last_name', '')}").strip() or None
        products = []
        for j, p in enumerate(c.get("products") or []):
            if isinstance(p, dict):
                products.append(dict(p, product_id=p.get("product_id") or f"p{j + 1}"))
        exp = c.get("expected") or {}
        customers.append({
            "customer_id": str(cid),
            "case_id": c.get("id") or c.get("case_id"),
            "name": name,
            "variables": variables,
            "identity": c.get("identity") or {},
            "products": products,
            "outcome": exp.get("outcome", c.get("outcome")),
            "reason": exp.get("reason", c.get("reason")),
            "promises": exp.get("promises") or c.get("promises") or [],
            "notes": exp.get("notes") or c.get("notes") or [],
            "callbacks": exp.get("callbacks") or c.get("callbacks") or [],
            "transfers": exp.get("transfers") or c.get("transfers") or [],
            "faults": c.get("faults") or [],
            "script": c.get("script"),
            "checks": c.get("checks") or [],
            "raw": c,
        })
    if not customers:
        raise ValueError("no customers found in the customers file")
    return {"customers": customers, "source": "naive JSON normalisation (no model call)"}


# ------------------------------------------------------------------- normalisers
def normalize_analysis(analysis, base_fallback=""):
    """Fill the analysis schema so later stages never KeyError on a thin answer."""
    if not isinstance(analysis, dict):
        analysis = {}
    a = dict(analysis)
    a.setdefault("service_name", "bank-mock")
    base = str(a.get("base_path") or base_fallback or "").strip()
    if base == "/":
        base = ""
    a["base_path"] = base
    a.setdefault("state_model", "cross-call")
    ep = []
    for e in a.get("endpoints") or []:
        if not isinstance(e, dict):
            continue
        path = str(e.get("path") or "")
        if not path.startswith("/"):
            path = "/" + path
        if base and not path.startswith(base) and path != "/health":
            path = base + path
        ep.append({
            "method": str(e.get("method") or "POST").upper(),
            "path": path,
            "summary": str(e.get("summary") or ""),
            "request_fields": e.get("request_fields") or {},
            "response_fields": e.get("response_fields") or {},
            "errors": e.get("errors") or [],
        })
    a["endpoints"] = ep
    led = a.get("ledger") if isinstance(a.get("ledger"), dict) else {}
    routes = []
    for r in led.get("read_routes") or led.get("read_routes_to_add") or []:
        if isinstance(r, dict) and r.get("path"):
            p = str(r["path"])
            routes.append({"method": str(r.get("method") or "GET").upper(),
                           "path": p if p.startswith("/") else "/" + p,
                           "summary": str(r.get("summary") or "read the recorded ledger")})
    if not routes:
        routes = [
            {"method": "GET", "path": f"{base}/practice/ledger/{{customer_id}}",
             "summary": "the recorded ledger for one customer (what a scorer reads)"},
            {"method": "GET", "path": f"{base}/practice/ledger",
             "summary": "every live session's ledger"},
        ]
    led["read_routes"] = routes
    led.setdefault("record_every_call", True)
    a["ledger"] = led
    sess = a.get("sessions") if isinstance(a.get("sessions"), dict) else {}
    sess.setdefault("add", True)
    sess.setdefault("path", f"{base}/practice/sessions")
    a["sessions"] = sess
    ident = a.get("identity") if isinstance(a.get("identity"), dict) else {}
    a["identity"] = ident
    a["faults"] = a.get("faults") or []
    a.setdefault("unknown_customer_policy", "")
    a.setdefault("extra_notes", [])
    return a


def normalize_seed(seed):
    if not isinstance(seed, dict) or not isinstance(seed.get("customers"), list):
        raise ValueError("seed must be an object with a customers list")
    seen = set()
    out = []
    for i, c in enumerate(seed["customers"]):
        if not isinstance(c, dict):
            continue
        cid = str(c.get("customer_id") or c.get("case_id") or f"case-{i + 1}")
        if cid in seen:
            cid = f"{cid}-{i + 1}"
        seen.add(cid)
        products = []
        for j, p in enumerate(c.get("products") or []):
            if isinstance(p, dict):
                products.append(dict(p, product_id=p.get("product_id") or f"p{j + 1}"))
        out.append({
            "customer_id": cid,
            "case_id": c.get("case_id") or c.get("id"),
            "name": c.get("name"),
            "variables": c.get("variables") or {},
            "identity": c.get("identity") or {},
            "products": products,
            "outcome": c.get("outcome"),
            "reason": c.get("reason"),
            "promises": c.get("promises") or [],
            "notes": c.get("notes") or [],
            "callbacks": c.get("callbacks") or [],
            "transfers": c.get("transfers") or [],
            "faults": c.get("faults") or [],
            "script": c.get("script"),
            "checks": c.get("checks") or [],
            "raw": c.get("raw", c),
        })
    if not out:
        raise ValueError("seed has no usable customers")
    return {"customers": out}


# -------------------------------------------------------------------- validation
def path_variants(path, base):
    """Accepted spellings of one route inside the generated file.

    Never a bare name without its slash: bare tool names ("create_promise") occur in
    seed scripts and would false-positive against the seed blob.
    """
    out = [path]
    if base:
        if path.startswith(base):
            rest = path[len(base):] or "/"
            out.append(rest)
        elif path.startswith("/"):
            out.append(base + path)
    return list(dict.fromkeys(v for v in out if v))


def _static_prefix(path):
    for cut in ("{", "<", ":"):
        if cut in path:
            path = path.split(cut)[0]
    return path.rstrip("/")


def js_delimiter_balance(js):
    """Heuristic truncation check: strip comments/strings, then balance delimiters."""
    i, n = 0, len(js)
    stack = []
    pairs = {"}": "{", ")": "(", "]": "["}
    prev_sig = ""
    while i < n:
        c = js[i]
        if c == "/" and i + 1 < n and js[i + 1] == "/":
            j = js.find("\n", i)
            i = n if j == -1 else j
            continue
        if c == "/" and i + 1 < n and js[i + 1] == "*":
            j = js.find("*/", i + 2)
            i = n if j == -1 else j + 2
            continue
        if c in ("'", '"', "`"):
            q = c
            i += 1
            while i < n:
                ch = js[i]
                if ch == "\\":
                    i += 2
                    continue
                if ch == q:
                    i += 1
                    break
                if q == "`" and ch == "$" and i + 1 < n and js[i + 1] == "{":
                    i += 2
                    depth = 1
                    while i < n and depth:
                        d = js[i]
                        if d == "{":
                            depth += 1
                        elif d == "}":
                            depth -= 1
                        elif d in ("'", '"', "`"):
                            qq = d
                            i += 1
                            while i < n:
                                if js[i] == "\\":
                                    i += 2
                                    continue
                                if js[i] == qq:
                                    break
                                i += 1
                        i += 1
                    continue
                i += 1
            continue
        if c == "/" and prev_sig in "(,=:[!&|?{};+-*%~^" and not (i + 1 < n and js[i + 1] in "*/"):
            i += 1
            in_cls = False
            while i < n:
                ch = js[i]
                if ch == "\\":
                    i += 2
                    continue
                if ch == "[":
                    in_cls = True
                elif ch == "]":
                    in_cls = False
                elif ch == "/" and not in_cls:
                    i += 1
                    break
                elif ch == "\n":
                    break
                i += 1
            prev_sig = "/"
            continue
        if c in "({[":
            stack.append(c)
        elif c in ")}]":
            if not stack or stack[-1] != pairs[c]:
                return f"delimiter mismatch at char {i}: unexpected {c!r}"
            stack.pop()
        if not c.isspace():
            prev_sig = c
        i += 1
    if stack:
        return (f"{len(stack)} unclosed delimiter(s) at the end of the file "
                f"(truncated answer?): {''.join(stack[-12:])}")
    return None


def strip_js_comments(js):
    """The code with comments removed (string and regex literals kept verbatim).

    Route checks run on this: a comment that merely mentions a path must not count
    as a route.
    """
    out, i, n = [], 0, len(js)
    prev_sig = ""
    while i < n:
        c = js[i]
        if c == "/" and i + 1 < n and js[i + 1] == "/":
            j = js.find("\n", i)
            i = n if j == -1 else j
            out.append("\n")
            continue
        if c == "/" and i + 1 < n and js[i + 1] == "*":
            j = js.find("*/", i + 2)
            i = n if j == -1 else j + 2
            out.append(" ")
            continue
        if c in ("'", '"', "`"):
            q = c
            start = i
            i += 1
            while i < n:
                ch = js[i]
                if ch == "\\":
                    i += 2
                    continue
                if ch == q:
                    i += 1
                    break
                if q == "`" and ch == "$" and i + 1 < n and js[i + 1] == "{":
                    i += 2
                    depth = 1
                    while i < n and depth:
                        d = js[i]
                        if d in ("'", '"', "`"):
                            qq = d
                            i += 1
                            while i < n:
                                if js[i] == "\\":
                                    i += 2
                                    continue
                                if js[i] == qq:
                                    break
                                i += 1
                        elif d == "{":
                            depth += 1
                        elif d == "}":
                            depth -= 1
                        i += 1
                    continue
                i += 1
            out.append(js[start:i])
            prev_sig = q
            continue
        if c == "/" and prev_sig in "(,=:[!&|?{};+-*%~^" and not (i + 1 < n and js[i + 1] in "*/"):
            start = i
            i += 1
            in_cls = False
            while i < n:
                ch = js[i]
                if ch == "\\":
                    i += 2
                    continue
                if ch == "[":
                    in_cls = True
                elif ch == "]":
                    in_cls = False
                elif ch == "/" and not in_cls:
                    i += 1
                    break
                elif ch == "\n":
                    break
                i += 1
            out.append(js[start:i])
            prev_sig = "/"
            continue
        out.append(c)
        if not c.isspace():
            prev_sig = c
        i += 1
    return "".join(out)


def validate_worker(js, analysis, seed):
    """The correctness checklist run on every generated file (feeds the repair loop)."""
    problems = []
    js_nc = strip_js_comments(js)
    js_flat = js_nc.replace("\\/", "/")  # regex-literal routes spell "/" as "\/"
    if "export default" not in js_nc:
        problems.append("missing `export default { async fetch(request, env, ctx) }`")
    if not re.search(r"async\s+fetch\s*\(", js_nc):
        problems.append("missing an `async fetch(...)` handler")
    if "/health" not in js_nc:
        problems.append("missing the /health route")
    if SEED_PLACEHOLDER in js:
        problems.append(f"the {SEED_PLACEHOLDER} placeholder was not replaced; the file must "
                        f"define `const SEED = {SEED_PLACEHOLDER};` exactly once")
    if not re.search(r"SEED\s*[\.\[]\s*['\"]?customers", js_nc):
        problems.append("the worker never reads SEED.customers (seed data must live in SEED)")
    base = analysis.get("base_path") or ""

    def route_present(path):
        needle = _static_prefix(path) if any(c in path for c in "{<:") else path
        return any(v in js_nc or v in js_flat for v in path_variants(needle, base) if v)

    for ep in analysis.get("endpoints") or []:
        if not route_present(ep["path"]):
            problems.append(f'no route for contract endpoint {ep["method"]} {ep["path"]}')
    for r in (analysis.get("ledger") or {}).get("read_routes") or []:
        if not route_present(r["path"]):
            problems.append(f'no ledger read route {r["method"]} {r["path"]}')
    if (analysis.get("sessions") or {}).get("add"):
        sp = (analysis.get("sessions") or {}).get("path") or f"{base}/practice/sessions"
        if not route_present(sp):
            problems.append(f"missing the session route {sp} (POST -> variables incl. customer_id)")
    if analysis.get("state_model") == "cross-call" and "MOCK_KV" not in js_nc:
        problems.append("cross-call state: the worker must implement the optional KV mirror "
                        "(env.MOCK_KV) so the ledger survives a change of isolate")
    # the ledger keys the scoring contract reads (tools/score.py: calls[].tool/.result,
    # promises[], notes[], callbacks[], transfers[], outcome, reason)
    for key in ("calls", "promises", "notes", "callbacks", "transfers", "outcome", "reason",
                "customer_id", "closed", "seq", "tool", "request", "result"):
        if f'"{key}"' not in js_nc and f"{key}:" not in js_nc:
            problems.append(f"the ledger never mentions the key {key!r} (the scorer reads it)")
    ident = analysis.get("identity") or {}
    if ident and (ident.get("gated_endpoints") or []):
        raw = str(ident.get("refusal_error") or "").strip()
        # the analysis often quotes the string inside an explanation: pull the quoted
        # candidates out, and accept the practice-convention default as a fallback
        quoted = re.findall(r'"([^"\n]{3,80})"|\'([^\'\n]{3,80})\'', raw)
        candidates = [a or b for a, b in quoted]
        if 0 < len(raw) <= 60:
            candidates.append(raw)
        candidates.append("identity not verified")
        if not any(c in js_nc for c in candidates):
            problems.append("none of the identity refusal strings "
                            f"{candidates[:3]} appear in the worker "
                            f"(the scorer compares the error string literally)")
    if re.search(r"^\s*import\b", js_nc, re.M):
        problems.append("ES `import` statements are not allowed: one self-contained file, no bundles")
    # SESSION_SUFFIX_RE has no capture group: stripping the base id from a "-sN" session
    # id must be a .replace(), never .exec(...)[1] (undefined -> session customers fall
    # through to derived hash identities and every identity check fails)
    if re.search(r"SESSION_SUFFIX_RE\.exec", js_nc) and "replace(SESSION_SUFFIX_RE" not in js_nc:
        problems.append("the session-suffix strip uses .exec()[1] on a regex without a capture "
                        "group — use String(id).replace(SESSION_SUFFIX_RE, '') instead")
    for bad, label in ((r"\brequire\s*\(", "require()"), (r"\bprocess\.", "process."),
                       (r"\bBuffer\b", "Buffer"), (r"\b__dirname\b", "__dirname"),
                       (r"\bmodule\.exports\b", "module.exports")):
        if re.search(bad, js_nc):
            problems.append(f"Node-only construct in a Workers file: {label}")
    bal = js_delimiter_balance(js)
    if bal:
        problems.append(bal)
    return problems


def apply_seed(js, seed):
    """Replace the __SEED_JSON__ placeholder with the real seed (JS object literal)."""
    blob = json.dumps(seed, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    if SEED_PLACEHOLDER in js:
        return js.replace(SEED_PLACEHOLDER, blob)
    return js


# ------------------------------------------------------------------ worker prompt
WORKER_TEMPLATE_JS = r'''// __SERVICE__ mock service — generated from the service contract by builder/mock_gen.py.
// Do not edit by hand: regenerate with `python3 builder/mock_gen.py <contract> <customers>`.
// Endpoints: __ENDPOINT_LIST__
//
// Every tool call is written to a per-customer ledger. Read it at
// GET __LEDGER_ROUTE__ (add ?pretty=1 for a human view); the graders and scorers read
// what actually happened from there, not from what the phone agent said.
const SEED = __SEED_JSON__;

const SERVICE = "__SERVICE__";
const BASE_PREFIX = "__BASE__"; // contract base path ("" when the contract has none)

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers": "content-type, authorization, x-team-key",
  "access-control-max-age": "86400"
};

// The in-memory store is authoritative inside one Worker isolate. When the MOCK_KV
// binding exists, every mutation is mirrored to KV and a state miss in a fresh
// isolate is hydrated from it (best effort: KV is eventually consistent). Without
// the binding everything still works, in memory only.
const MEM = globalThis.__MOCK_STATE__ ||
  (globalThis.__MOCK_STATE__ = { sessions: {}, counts: {}, seq: 0 });

function json(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: Object.assign({ "content-type": "application/json; charset=utf-8" }, CORS)
  });
}

// Accepts the contract path with or without the base prefix, with/without trailing "/".
function canonPath(pathname) {
  let p = String(pathname || "/").replace(/\/+/g, "/");
  if (p.length > 1 && p.endsWith("/")) p = p.slice(0, -1);
  if (p === "/health") return p;
  if (BASE_PREFIX) {
    if (p !== BASE_PREFIX && !p.startsWith(BASE_PREFIX + "/")) {
      p = BASE_PREFIX + (p === "/" ? "" : p);
    }
  }
  return p;
}

function hashInt(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return Math.abs(h);
}

function findSeed(id) {
  const key = String(id);
  for (const c of SEED.customers) {
    if (String(c.customer_id) === key || (c.case_id && String(c.case_id) === key)) return c;
  }
  return null;
}

// Unknown customer ids (for example hidden cases) must never 500: derive a
// deterministic record so the service stays usable; the ledger records everything.
function derivedSeed(id) {
  const h = hashInt(String(id));
  return {
    customer_id: String(id), case_id: null, derived: true, variables: {}, identity: {},
    products: [{ product_id: "p1", type: "credit_card", card_last4: String(1000 + (h % 9000)),
                 past_due: Math.round((100 + (h % 1900)) * 100) / 100, days_late: 1 + (h % 45),
                 minimum_payment: Math.round((30 + (h % 400)) * 100) / 100 }],
    outcome: null, reason: null, promises: [], notes: [], callbacks: [], transfers: [], faults: []
  };
}

function freshState(seedCustomer, id) {
  return {
    customer_id: String(id),
    case_id: seedCustomer.case_id || null,
    derived: !!seedCustomer.derived,
    seed: seedCustomer,
    variables: Object.assign({}, seedCustomer.variables || {}),
    identity: { verified: false, wrong_answers: 0, locked: false, answers: {} },
    products: (seedCustomer.products || []).map(function (p) { return Object.assign({}, p); }),
    calls: [], promises: [], notes: [], callbacks: [], transfers: [],
    outcome: null, reason: null, closed: false,
    counters: {}, faults: (seedCustomer.faults || []).slice()
  };
}

async function loadState(env, id) {
  const key = String(id);
  // KV is authoritative on reads when bound: a stale in-memory copy from before an
  // earlier tool call would otherwise shadow newer state written by another isolate.
  if (env && env.MOCK_KV) {
    try {
      const raw = await env.MOCK_KV.get("session:" + key);
      if (raw) { const s = JSON.parse(raw); MEM.sessions[key] = s; return s; }
    } catch (e) { /* KV is a mirror; memory still serves the request */ }
  }
  if (MEM.sessions[key]) return MEM.sessions[key];
  const sc = findSeed(key) || derivedSeed(key);
  const s = freshState(sc, key);
  MEM.sessions[key] = s;
  return s;
}

function saveState(env, ctx, s) {
  MEM.sessions[s.customer_id] = s;
  if (env && env.MOCK_KV && ctx && ctx.waitUntil) {
    ctx.waitUntil(env.MOCK_KV.put("session:" + s.customer_id, JSON.stringify(s)));
  }
}

// One ledger entry per call: seq is monotonic, order is insertion order.
function record(s, tool, request, result) {
  s.calls.push({ seq: ++MEM.seq, at: new Date().toISOString(), customer_id: s.customer_id,
                 tool: tool, request: request, result: result });
  return result;
}

function ledgerView(s) {
  return {
    customer_id: s.customer_id, case_id: s.case_id, derived: s.derived,
    identity: s.identity, outcome: s.outcome, reason: s.reason, closed: s.closed,
    promises: s.promises, notes: s.notes, callbacks: s.callbacks, transfers: s.transfers,
    calls: s.calls, product_count: s.products.length
  };
}

// Returns the exact refusal body when a gated tool is called before identity passed,
// recorded like any other call; null when the call may proceed.
function verifiedGate(s, tool, body) {
  if (s.identity.verified) return null;
  return record(s, tool, body, { ok: false, error: "identity not verified" });
}

// Deterministic per-session failure injection from seed "faults".
function takeFault(s, tool) {
  for (const f of s.faults) {
    if (f && f.tool === tool) {
      const n = (s.counters["fault:" + tool] || 0) + 1;
      s.counters["fault:" + tool] = n;
      const limit = (f.times == null) ? 1 : f.times;
      if (n <= limit) return f;
    }
  }
  return null;
}

async function handleCreateSession(body, env, ctx) {
  const key = String((body && (body.case || body.case_id || body.customer_id || body.id)) || "");
  const sc = findSeed(key);
  if (!sc) return json({ ok: false, error: "unknown case", case: key }, 404);
  // The counter is read/incremented through KV when bound, so two isolates never
  // issue the same session id (a collision lets their states overwrite each other).
  let n = (MEM.counts[key] || 0) + 1;
  if (env && env.MOCK_KV) {
    try {
      const cur = await env.MOCK_KV.get("counter:" + key);
      const prev = cur ? parseInt(cur, 10) : 0;
      n = Math.max(n, prev + 1);
      ctx.waitUntil(env.MOCK_KV.put("counter:" + key, String(n)));
    } catch (e) { /* the memory counter still serves */ }
  }
  MEM.counts[key] = n;
  const id = String(sc.customer_id) + "-s" + n;
  const s = freshState(sc, id);
  MEM.sessions[id] = s;
  saveState(env, ctx, s);
  const variables = Object.assign({}, sc.variables || {}, { customer_id: id });
  return json({ variables: variables });
}

function findSessionId(id) {
  const key = String(id);
  if (MEM.sessions[key]) return key;
  let best = null;
  for (const k of Object.keys(MEM.sessions)) {
    const s = MEM.sessions[k];
    if (s && (String(s.case_id) === key || s.customer_id.indexOf(key + "-s") === 0)) {
      if (!best || s.calls.length >= MEM.sessions[best].calls.length) best = k;
    }
  }
  return best || key;
}

// ------------------------------------------------------------------- handlers --
// EXAMPLE HANDLER (replace with the contract's handlers; keep this exact shape:
// validate the body, mutate state, record(s, tool, body, result), saveState, return).

async function handleVerifyIdentity(body, env, ctx) {
  const b = body || {};
  const s = await loadState(env, b.customer_id);
  const tool = "verify_identity";
  const answer = b.answer == null ? "" : String(b.answer).trim();
  let res;
  if (s.identity.locked) {
    res = { ok: false, error: "identity check is locked" };
  } else if (b.field !== "date_of_birth" && b.field !== "phone_last4") {
    res = { ok: false, error: "invalid request: field" };
  } else if (!answer) {
    res = { ok: false, error: "invalid request: answer" };
  } else if (answer === String(s.seed.identity[b.field] == null ? "" : s.seed.identity[b.field])) {
    s.identity.answers[b.field] = true;
    if (s.identity.answers.date_of_birth && s.identity.answers.phone_last4) s.identity.verified = true;
    res = { ok: true, verified: true, all_verified: s.identity.verified };
  } else {
    // An unreadable value is rejected with ok=false and is NOT counted as a wrong
    // answer; only readable-but-wrong answers count toward the limit.
    if (b.field === "date_of_birth" && !/^\d{4}-\d{2}-\d{2}$/.test(answer)) {
      res = { ok: false, error: "invalid request: answer" };
    } else {
      s.identity.wrong_answers += 1;
      if (s.identity.wrong_answers >= 3) s.identity.locked = true;
      res = { ok: false, error: "wrong answer", wrong_answers_left: Math.max(0, 3 - s.identity.wrong_answers) };
    }
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// EXAMPLE of a gated tool: refuse until identity is verified, then serve seed data.
async function handleGetAccount(body, env, ctx) {
  const b = body || {};
  const s = await loadState(env, b.customer_id);
  const refused = verifiedGate(s, "get_account", b);
  if (refused) { saveState(env, ctx, s); return json(refused); }
  const res = { ok: true, products: s.products };
  record(s, "get_account", b, res);
  saveState(env, ctx, s);
  return json(res);
}

// todo: one handler per remaining contract endpoint, exact request/response schema.

// --------------------------------------------------------------------- fetch ---
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = canonPath(url.pathname);
    try {
      if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });

      if (path === "/health" && request.method === "GET") {
        return json({ ok: true, status: "healthy", service: SERVICE,
                      state_model: "cross-call", customers: SEED.customers.length });
      }

      let body = null;
      if (request.method === "POST" || request.method === "PUT" || request.method === "PATCH") {
        try { body = await request.json(); } catch (e) { body = null; }
      }

      // --- contract endpoints: one route per endpoint in the contract analysis ---
      if (path === "__BASE__/verify_identity" && request.method === "POST") return await handleVerifyIdentity(body, env, ctx);
      if (path === "__BASE__/get_account" && request.method === "POST") return await handleGetAccount(body, env, ctx);
      // todo: every other contract endpoint, exact path + method.

      // --- session opener: POST {"case": "<case or customer id>"} -> {"variables": {...}} ---
      // If the contract defines its own session/registration endpoint, that route is
      // implemented separately above; this one stays as the compatibility route.
      if (path === "__BASE__/practice/sessions" && request.method === "POST") return await handleCreateSession(body, env, ctx);

      // --- ledger and session read routes (the scorers read these) ---
      // Prefixes are built from BASE_PREFIX (never regex literals) so the base path
      // cannot corrupt the pattern.
      const LEDGER_PREFIX = "__BASE__/practice/ledger/";
      if (request.method === "GET" && path.indexOf(LEDGER_PREFIX) === 0 && path.length > LEDGER_PREFIX.length) {
        const id = decodeURIComponent(path.slice(LEDGER_PREFIX.length));
        const s = await loadState(env, findSessionId(id));
        return json(ledgerView(s));
      }
      if (path === "__BASE__/practice/ledger" && request.method === "GET") {
        const all = {};
        for (const k of Object.keys(MEM.sessions)) all[k] = ledgerView(MEM.sessions[k]);
        return json({ ok: true, sessions: all });
      }
      if (path === "__BASE__/practice/sessions" && request.method === "GET") {
        return json({ ok: true, sessions: Object.keys(MEM.sessions) });
      }
      const RESET_PREFIX = "__BASE__/practice/reset/";
      if (request.method === "POST" && path.indexOf(RESET_PREFIX) === 0 && path.length > RESET_PREFIX.length) {
        const key = String(findSessionId(decodeURIComponent(path.slice(RESET_PREFIX.length))));
        delete MEM.sessions[key];
        if (env && env.MOCK_KV && ctx && ctx.waitUntil) ctx.waitUntil(env.MOCK_KV.delete("session:" + key));
        return json({ ok: true });
      }
      return json({ ok: false, error: "not found", path: path }, 404);
    } catch (e) {
      return json({ ok: false, error: "internal error" }, 500);
    }
  }
};
'''

ANALYSIS_PROMPT = """You are the contract analyst for a bank-mock generator. Read the SERVICE CONTRACT and the TEST CUSTOMERS below and return ONE JSON object, no prose and no markdown fences.

The mock must implement the contract exactly. A phone agent's tools call it during a debt-collection simulation; a scorer then reads the recorded ledger. Hidden customers will be served by the same mock, so describe general semantics, not only the test customers.

Return this exact JSON shape (every key present; use null, "" or [] where not applicable):

{
  "service_name": "short service name",
  "base_path": "path prefix of the endpoints, e.g. /v1, or \\"\\"",
  "language": "en / tr / ...",
  "state_model": "stateless | call-scoped | cross-call",
  "state_reason": "one line: why",
  "identity": {
    "questions": [{"field": "...", "format": "...", "description": "..."}],
    "order": ["...fields in the order they are asked..."],
    "wrong_answer_limit": 3,
    "not_counted_as_wrong": "e.g. an unreadable date",
    "hints": ["e.g. day_month_swapped"],
    "gated_endpoints": ["tools refused until all questions pass"],
    "refusal_error": "the exact error string those tools return when refused",
    "notes": "anything else about the identity check"
  },
  "endpoints": [
    {"method": "POST", "path": "/v1/verify_identity",
     "summary": "one line",
     "request_fields": {"customer_id": "string (required)", "...": "exact type/enum"},
     "response_fields": {"ok": "boolean", "...": "exact type/enum"},
     "errors": [{"when": "condition", "response": "exact body/status"}]}
  ],
  "ledger": {
    "record_every_call": true,
    "fields": ["calls[] {seq, at, customer_id, tool, request, result}", "outcome", "reason",
               "promises[] {product_id, amount, date}", "notes[] {product_id, reason}",
               "callbacks[] {date, time}", "transfers[] {queue}",
               "identity {verified, wrong_answers, locked}"],
    "read_routes": [{"method": "GET", "path": "/v1/practice/ledger/{customer_id}",
                     "summary": "the ledger a scorer reads"}]
  },
  "sessions": {"add": true, "path": "/v1/practice/sessions",
               "request": {"case": "case or customer id"},
               "response": {"variables": "call variables incl. a fresh customer_id"},
               "notes": "copy the contract's own endpoint if it defines one, else propose the practice-style route"},
  "faults": [{"tool": "...", "when": "e.g. first call of the session", "behavior": "e.g. 500 once"}],
  "products": {"shape": "field names of one product/account object, with types", "ids": "how product ids are formed"},
  "unknown_customer_policy": "what to do for a customer_id not in the seed (contract first; else derive deterministically and never 500)",
  "extra_notes": ["anything else a correct mock must do"]
}

Rules:
- Copy exact spellings, field names, enum values, and error strings from the contract. Never invent fields the contract does not have.
- "endpoints" lists EVERY endpoint in the contract, in contract order. The path must include the base prefix (e.g. /v1/verify_identity).
- "state_model": "stateless" if nothing crosses requests; "call-scoped" if state lives only inside one request; "cross-call" if anything (identity progress, promises, the ledger) must survive across separate HTTP calls.
- The ledger must record every tool call; if the contract does not define ledger read routes, propose GET routes under the base path mirroring the practice style (/v1/practice/ledger/{customer_id} and /v1/practice/ledger).
- "faults": any failure injection the contract or customers describe (a service failing on the first call, etc). Empty list if none.
- If the TEST CUSTOMERS define expected final state, note the outcome/reason vocabulary in "extra_notes".

CONTRACT:
<<<CONTRACT>>>

TEST CUSTOMERS:
<<<CUSTOMERS>>>
"""

SEED_PROMPT = """You convert a test-customer file into seed.json for a mock bank service. Return ONE JSON object, no prose and no markdown fences.

The SERVICE CONTRACT is included so you use its field names.

Shape:
{"customers": [
  {
    "customer_id": "string; the source's id kept EXACTLY if it has one (customer_id / id / case id)",
    "case_id": "the source case id, else null",
    "name": "display name, else null",
    "variables": { "every call variable from the source, verbatim": "e.g. first_name, last_name, title, now" },
    "identity": { "contract identity question fields, e.g. date_of_birth": "the source's answer value, verbatim" },
    "products": [ { "the source's products copied verbatim, field names mapped to the contract's product schema": "...",
                    "product_id": "keep the source's id (e.g. p1); assign p1, p2, ... in source order if absent" } ],
    "outcome": "expected outcome if the source has one, else null",
    "reason": "expected reason, else null",
    "promises": [], "notes": [], "callbacks": [], "transfers": [],
    "faults": [{"tool": "...", "when": "...", "behavior": "...", "times": 1}],
    "script": "the source's script/notes text, else null",
    "checks": ["the source's checks, else []"],
    "raw": { "the original source object EXACTLY as given": "..." }
  }
]}

Rules:
- The source may be a JSON list of cases or an object with a cases/customers list; handle either.
- Never invent values, never drop fields, keep numbers as numbers and dates as strings.
- Copy the source's expected outcome/promises/notes/callbacks/transfers into the matching
  top-level fields (not only into "raw").
- If the source describes a tool failing for a case (fault injection), list it in "faults"
  with the tool name, the trigger, and how many times it fails.
- One customer per case, even when the source has no products.

CONTRACT:
<<<CONTRACT>>>

TEST CUSTOMERS:
<<<CUSTOMERS>>>
"""

WORKER_PROMPT = """You write ONE complete Cloudflare Worker JavaScript file. Output ONLY the file: no markdown fences, no commentary before or after.

## Goal
A mock of the bank service described by the contract below. The phone agent's tools call it; the graders' hidden customers' tools call it too; scorers read its ledger. A wrong or unreachable mock fails the graders, so exact field names, exact error strings, and correct ledger records matter more than elegance.

## What you must produce
A single self-contained JavaScript file (ES module, Cloudflare Workers runtime). No imports, no Node APIs, no bundlers. Follow the TEMPLATE below; keep its helper layer (json, canonPath, findSeed, derivedSeed, freshState, loadState, saveState, record, ledgerView, verifiedGate, takeFault); replace the EXAMPLE handlers with the contract's endpoints, keeping the same handler shape (validate body -> mutate state -> record -> saveState -> return json(result)).

## Non-negotiable requirements
1. `export default { async fetch(request, env, ctx) { ... } }` and one file only.
2. Near the top, exactly one line `const SEED = __SEED_JSON__;` with that EXACT token. The generator replaces it with `{"customers":[...]}`. Never paste or retype seed data; read it from SEED at runtime.
3. Implement EVERY endpoint in the contract: exact path (with its base prefix and any path parameter), exact method, exact request field names/types/enums/required, exact response field names/types. Validate inputs; a missing or invalid field returns the contract's error shape (if the contract is silent: {"ok": false, "error": "invalid request: <field>"}).
4. Error strings: copy the contract's exact strings, casing included. The identity refusal convention from the practice service is exactly "identity not verified". Record the exact response body you send.
5. LEDGER: every call to any tool endpoint, success or failure, is appended exactly once to that customer's ledger as {seq (monotonic integer), at (ISO timestamp), customer_id, tool (endpoint name without prefix or leading slash), request (parsed body), result (the exact response body)}. Maintain the current state the endpoints write (promises, notes, callbacks, transfers, identity, outcome, reason, closed) in insertion order. Ledger reads must be deterministic: counters for ids, no Math.random, no timers.
6. LEDGER READ ROUTES (this is how scoring works): GET <base>/practice/ledger/<customer_id> returns AT LEAST {customer_id, outcome, reason, promises[{product_id,amount,date}], notes[{product_id,reason}], callbacks[{date,time}], transfers[{queue}], identity{verified,wrong_answers,locked}, closed, calls[]}. Also GET <base>/practice/ledger (all live sessions, keyed by id) and GET <base>/practice/sessions. A read must accept the base customer id even after sessions appended "-sN".
7. SESSIONS: POST <base>/practice/sessions with {"case": "<case or customer id>"} returns {"variables": {...}} containing every seed variable PLUS a fresh "customer_id" (seed id + "-s" + monotonic counter); each session starts clean. The "-sN" counter must be read/incremented through KV (key "counter:<case>") when MOCK_KV is bound — two isolates must never issue the same session id, or their states overwrite each other in KV. If the contract defines its own session/registration customer endpoint, implement that EXACTLY as well, creating state from its request body.
8. UNKNOWN CUSTOMER IDS must never 500: follow the contract's policy; otherwise use derivedSeed() and keep serving. Also support a POST <base>/practice/reset/<customer_id> that clears a session.
8b. The "-sN" session suffix regex has NO capture group: to strip the base id from a session id, use String(id).replace(SESSION_SUFFIX_RE, ''). Never use .exec(...)[1] — it yields undefined and every session customer falls through to a derived hash identity, failing the real identity check.
9. IDENTITY: enforce the contract's identity rules server-side (fields, order, wrong-answer counting, what is not counted as wrong, hints, lockout, which endpoints are gated). Until verified, gated endpoints return the contract's exact refusal and the refusal is recorded in the ledger.
10. FAULTS: implement every failure injection from the analysis/seed/contract deterministically per session (e.g. the first call to a tool returns 500 once, then succeeds). Record the failed call with its exact error response. Never inject faults the contract does not describe.
11. STATE: the in-memory Map is authoritative; when `env.MOCK_KV` is bound, mirror every mutation (`ctx.waitUntil(put)`) and hydrate a state miss from KV. Never require the binding; never throw when it is absent.
12. /health returns 200 JSON with {ok: true, status: "healthy", service, customers: SEED.customers.length} — no auth, no state change, never blocked by the identity gate.
13. CORS: every response carries access-control-allow-origin: *; OPTIONS returns 204 with the CORS headers. canonPath must accept the contract path both with and without the base prefix.
14. Status codes: 200 for contract semantics including ok:false refusals (unless the contract says otherwise); 404 unknown path/unknown case; 405 wrong method where practical; 500 only for contract faults or unhandled exceptions. Every response is JSON; never leak a stack trace.
15. Numbers stay numbers (never stringify amount/past_due/days_late), booleans booleans, dates "YYYY-MM-DD" strings.
16. Wrap body parsing and each handler so an unexpected exception returns {"ok": false, "error": "internal error"} with status 500 — but only as a last resort.

## TEMPLATE (follow it; replace the EXAMPLE handlers)
```javascript
__TEMPLATE__
```

## Contract analysis (authoritative interpretation; copy exact names and strings from it)
__ANALYSIS__

## Seed data (the exact object that will replace __SEED_JSON__)
__SEED__

## Service contract (verbatim; the analysis above is derived from it — the contract wins on any conflict)
__CONTRACT__

## Test customers (verbatim; for edge-case semantics)
__CUSTOMERS__

Remember: output ONLY the JavaScript file, starting with a `//` comment, containing the `const SEED = __SEED_JSON__;` line, implementing every endpoint, the ledger routes and /health.
"""

REPAIR_PROMPT = """Your previous attempt at a Cloudflare Worker mock failed automatic checks. Fix every listed problem and return the COMPLETE corrected file. Output ONLY the JavaScript, no fences, no commentary.

## Problems found
__PROBLEMS__

## Rules that were violated (reminders)
- One self-contained Workers ES-module file; `export default { async fetch(request, env, ctx) {...} }`.
- Exactly one line `const SEED = __SEED_JSON__;` with that exact token (do not paste seed data).
- Every contract endpoint route present, exact paths; ledger read routes and /health present.
- Cross-call state: keep the env.MOCK_KV mirror hooks.
- No imports, no Node APIs (require/process/Buffer), the file must be complete (not truncated).

## Contract analysis (authoritative)
__ANALYSIS__

## Previous file
```javascript
__JS__
```
"""


VERIFY_PROMPT = """You are the conformance checker for a generated Cloudflare Worker mock. Compare the WORKER against the SERVICE CONTRACT and its analysis, and report every mismatch. Return ONE JSON object, no prose and no markdown fences:

{"ok": true|false, "issues": ["one line per mismatch, precise and actionable"], "notes": "one line"}

Check, in this order:
1. every contract endpoint is implemented, with the exact path (base prefix included), the exact method, and no extra invented endpoints;
2. request bodies use the contract's exact field names and types; required fields are validated and invalid input returns the contract's error shape;
3. responses use the contract's exact field names, types and enum values (never a renamed or missing field);
4. error strings and status codes match the contract exactly — especially the identity refusal, which must be the contract's exact string;
5. the identity rules are enforced server-side: the questions, their order, the wrong-answer limit, what is not counted as wrong, hints, lockout, and which endpoints are gated;
6. the ledger records EVERY call (success and failure) once, with {seq, at, customer_id, tool, request, result} where result is the exact response body sent, and maintains outcome/reason/promises/notes/callbacks/transfers with the contract's field names;
7. the ledger read routes return the keys a scorer reads, including for a customer id that had a session suffix added;
8. sessions hand out a fresh customer_id and a clean state per session; close_call (or the contract's terminal tool) sets the final outcome/reason exactly as the contract defines;
9. faults are implemented exactly as described (which tool, when, how many times, what error) and no faults are invented;
10. /health returns 200 JSON without touching state; unknown paths are 404; the worker cannot 500 on a well-formed call.

Only real mismatches — do not report style, structure or performance. If the worker is conformant, return {"ok": true, "issues": []}.

## Contract analysis (the interpretation the worker was built from)
__ANALYSIS__

## Service contract (verbatim; authoritative)
__CONTRACT__

## Generated worker
```javascript
__JS__
```
"""


def build_verify_prompt(js, analysis, contract_text):
    return fill_tokens(VERIFY_PROMPT, {
        "__ANALYSIS__": render_analysis_digest(analysis) + "\n\n"
                        + json.dumps(analysis, ensure_ascii=False, indent=1)[:12000],
        "__CONTRACT__": contract_text[:50000],
        "__JS__": js[:80000],
    })


def render_endpoint_list(analysis):
    lines = []
    for ep in analysis.get("endpoints") or []:
        line = f"{ep['method']} {ep['path']}"
        if ep.get("summary"):
            line += f" — {ep['summary'][:80]}"
        lines.append(line)
    for r in (analysis.get("ledger") or {}).get("read_routes") or []:
        lines.append(f"{r['method']} {r['path']}")
    return " | ".join(lines) if lines else "see the contract"


def render_analysis_digest(analysis):
    """A compact, model-friendly rendering of the analysis next to its JSON."""
    out = [f"service: {analysis.get('service_name')}  base: {analysis.get('base_path') or '(none)'}",
           f"state_model: {analysis.get('state_model')} ({analysis.get('state_reason') or 'n/a'})"]
    ident = analysis.get("identity") or {}
    if ident:
        out.append("identity: " + json.dumps(ident, ensure_ascii=False)[:2000])
    for ep in analysis.get("endpoints") or []:
        out.append(f"- {ep['method']} {ep['path']}: req {json.dumps(ep.get('request_fields') or {}, ensure_ascii=False)}"
                   f" -> resp {json.dumps(ep.get('response_fields') or {}, ensure_ascii=False)}")
    for f in analysis.get("faults") or []:
        out.append(f"fault: {json.dumps(f, ensure_ascii=False)}")
    for n in analysis.get("extra_notes") or []:
        out.append(f"note: {n}")
    return "\n".join(out)


def render_template(analysis):
    """The skeleton with its own tokens filled (__SEED_JSON__ deliberately left in)."""
    routes = (analysis.get("ledger") or {}).get("read_routes") or []
    return fill_tokens(WORKER_TEMPLATE_JS, {
        "__ENDPOINT_LIST__": render_endpoint_list(analysis),
        "__SERVICE__": analysis.get("service_name") or "bank-mock",
        "__BASE__": analysis.get("base_path") or "",
        "__LEDGER_ROUTE__": (routes[0].get("path") if routes else "") or "/practice/ledger/{customer_id}",
    })


def build_worker_prompt(contract_text, customers_text, analysis, seed):
    return fill_tokens(WORKER_PROMPT, {
        "__TEMPLATE__": render_template(analysis),
        "__ANALYSIS__": render_analysis_digest(analysis) + "\n\n"
                        + json.dumps(analysis, ensure_ascii=False, indent=1)[:12000],
        "__SEED__": json.dumps(seed, ensure_ascii=False, indent=1)[:20000],
        "__CONTRACT__": contract_text[:60000],
        "__CUSTOMERS__": customers_text[:40000],
    })


def build_repair_prompt(js, problems, analysis):
    return fill_tokens(REPAIR_PROMPT, {
        "__PROBLEMS__": "\n".join(f"- {p}" for p in problems),
        "__ANALYSIS__": render_analysis_digest(analysis),
        "__JS__": js[:80000],
    })


# ------------------------------------------------------------------- artefacts --
def build_endpoints_manifest(analysis, seed, name):
    eps = []
    for ep in analysis.get("endpoints") or []:
        eps.append({"method": ep["method"], "path": ep["path"], "source": "contract",
                    "summary": ep.get("summary", "")})
    for r in (analysis.get("ledger") or {}).get("read_routes") or []:
        eps.append({"method": r["method"], "path": r["path"], "source": "ledger",
                    "summary": r.get("summary", "")})
    sess = analysis.get("sessions") or {}
    if sess.get("add"):
        eps.append({"method": "POST", "path": sess.get("path") or "/practice/sessions",
                    "source": "sessions", "summary": "open a fresh session for a seed case"})
    eps.append({"method": "GET", "path": "/health", "source": "health",
                "summary": "liveness; must return 200"})
    probe_id = (seed["customers"][0]["customer_id"] if seed.get("customers") else "probe")
    probes = [{"path": "/health"}]
    seen = {"/health"}
    for ep in eps:
        if ep["method"] != "GET":
            continue
        concrete = ep["path"]
        concrete = re.sub(r"\{[^}]+\}", probe_id, concrete)
        concrete = re.sub(r"<[^>]+>", probe_id, concrete)
        concrete = re.sub(r":[A-Za-z_][A-Za-z0-9_]*", probe_id, concrete)
        if concrete not in seen:
            seen.add(concrete)
            probes.append({"path": concrete, "probe_of": ep["path"], "source": ep["source"]})
    return {
        "service": analysis.get("service_name"),
        "worker_name": name,
        "base_path": analysis.get("base_path") or "",
        "health_path": "/health",
        "state_model": analysis.get("state_model"),
        "kv_optional": analysis.get("state_model") == "cross-call",
        "endpoints": eps,
        "get_probes": probes,
    }


def render_wrangler_toml(name, analysis):
    lines = [
        f'name = "{name}"',
        'main = "worker.js"',
        'compatibility_date = "' + time.strftime("%Y-%m-%d") + '"',
        'workers_dev = true',
    ]
    if analysis.get("state_model") == "cross-call":
        lines += [
            "",
            "# Optional KV mirror so the ledger survives a change of Worker isolate.",
            "# mock/deploy.sh --with-kv creates the namespace and fills the id; or do it",
            "# yourself:  npx wrangler kv namespace create MOCK_KV   and paste the id here.",
            "[[kv_namespaces]]",
            'binding = "MOCK_KV"',
            'id = "REPLACE_WITH_KV_NAMESPACE_ID"',
        ]
    return "\n".join(lines) + "\n"


def render_readme(paths, analysis, seed, name, problems_fixed, model_calls):
    ep_rows = []
    for ep in analysis.get("endpoints") or []:
        ep_rows.append(f"| {ep['method']} | `{ep['path']}` | contract | {ep.get('summary', '')} |")
    for r in (analysis.get("ledger") or {}).get("read_routes") or []:
        ep_rows.append(f"| {r['method']} | `{r['path']}` | ledger read | {r.get('summary', '')} |")
    sess = analysis.get("sessions") or {}
    if sess.get("add"):
        ep_rows.append(f"| POST | `{sess.get('path')}` | session opener | body `{{\"case\": \"<id>\"}}` -> `{{\"variables\": {{..., customer_id}}}}` |")
    ep_rows.append("| GET | `/health` | health | 200 when the worker is up |")
    state = analysis.get("state_model") or "cross-call"
    cust_ids = ", ".join(c["customer_id"] for c in seed.get("customers", [])[:8])
    kv_block = ""
    if state == "cross-call":
        kv_block = """
## Persistence — the trade-off

The worker keeps its state in a module-scope `Map` (`globalThis.__MOCK_STATE__`):

* inside **one Worker isolate** it is exact and consistent — every request in a burst
  sees every earlier write, and the ledger is deterministic (`seq` is monotonic);
* a Worker may, at any time, run a request in a **different isolate** (a fresh cold
  start elsewhere). A new isolate starts empty.

That is why the generated worker also carries an **optional KV mirror**: bind a KV
namespace as `MOCK_KV` and every mutation is written through (`ctx.waitUntil`) and a
state miss in a fresh isolate is hydrated from KV. Without the binding everything
still works, in memory only.

Recommended: bind KV (deploy.sh does it for you with `--with-kv`). Caveat: Cloudflare
KV is eventually consistent (a mirror is best-effort, typically visible in seconds).
If the graders ever demand strict cross-isolate consistency, the upgrade path is a
single Durable Object holding all state (bind a DO class and route every request
through it) — deliberately not generated here: it needs a class export plus a
migrations block, and the extra failure modes are not worth it at 17:00.

Binding it yourself:
```
npx wrangler kv namespace create MOCK_KV     # paste the id into wrangler.toml
# or REST: POST /accounts/{account_id}/storage/kv/namespaces {"title": "..."}
```
"""
    else:
        kv_block = """
## Persistence

The analysis says the contract is **call-scoped**: no state has to survive between
requests, so the in-memory Map is exact and no KV binding is needed.
"""
    return f"""# {analysis.get('service_name') or 'bank'} mock — Cloudflare Worker

Generated by `builder/mock_gen.py` from the service contract and test customers.
Deployed with `mock/deploy.sh`. This mock is what the phone agent's tools call and
what the scorer reads; a wrong or unreachable mock fails the run.

* worker name: `{name}` (wrangler.toml)
* state model: **{state}** — {analysis.get('state_reason') or 'per the contract analysis'}
* seed customers: {len(seed.get('customers', []))} ({cust_ids}{', …' if len(seed.get('customers', [])) > 8 else ''})
* model calls: {model_calls}; validation problems repaired after first generation: {problems_fixed}

## Endpoints

| Method | Path | Kind | Notes |
|---|---|---|---|
{chr(10).join(ep_rows)}

The ledger route returns at least: `customer_id, outcome, reason, promises[],
notes[], callbacks[], transfers[], identity{{}}, closed, calls[]` — every call with its
`tool`, `request` and the exact `result` body. `seq` is monotonic; the order is the
order the calls arrived. This mirrors the practice mock's ledger, which the scanner
reads with `GET /v1/practice/ledger/<customer_id>`.

## Deploy and health check

```
export CF_API_TOKEN=... CF_ACCOUNT_ID=...
mock/deploy.sh --dir {paths['out_dir']}          # npx wrangler deploy if node exists,
                                                 # else REST PUT /workers/scripts/{name}
mock/deploy.sh --health-only --url https://<worker>.<subdomain>.workers.dev
```

`deploy.sh` pings `/health` and every GET endpoint in `endpoints.json` after deploy and
writes the deployed URL to `deployed.json`. Both env vars are required; the script
never prints the token.

{kv_block}
## Notes and policies

* Identity: {json.dumps(analysis.get('identity') or {}, ensure_ascii=False)[:1200]}
* Unknown customer ids: {analysis.get('unknown_customer_policy') or 'derived deterministically; never 500'}
* Faults: {json.dumps(analysis.get('faults') or [], ensure_ascii=False)[:800]}
* Regenerate: `python3 builder/mock_gen.py <contract> <customers> --out {paths['out_dir']}`
* The seed is embedded in `worker.js` (`const SEED = ...`); `seed.json` is the same data
  for inspection and for re-embedding.
"""


# --------------------------------------------------------------- case folder ---
# The final package is one folder of documents (Markdown, .docx, .pdf, .xlsx;
# Turkish). read_inputs() turns it into (contract_text, customers_text): the
# contract side is the whole package ordered contract-likelihood-first (the truth
# may be split across a contract, a memo and examples), the customers side is the
# files that look like the test-customer table. File reading goes through the
# sibling builder/read_case.py when it is importable (it handles the optional
# libraries); the fallback reads the text formats only.

CONTRACT_NAME_HINTS = ("contract", "sözleşme", "sozlesme", "sozlesmesi", "servis", "service",
                       "api", "openapi", "teknik", "endpoint", "arayüz", "arayuz", "tool")
CUSTOMER_NAME_HINTS = ("customer", "müşteri", "musteri", "musteriler", "müşteriler", "case",
                       "cases", "senaryo", "senaryolar", "örnek", "ornek", "example", "test",
                       "veri", "data", "liste", "list")


def _load_read_case():
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        import read_case  # sibling module; optional
        return read_case
    except Exception:
        return None


def _read_case_files(path):
    """[{name, text}] for every readable file in a case folder (or zip)."""
    p = pathlib.Path(path)
    if p.suffix.lower() == ".zip":
        rc = _load_read_case()
        if rc and hasattr(rc, "unzip_case"):
            p = pathlib.Path(rc.unzip_case(str(p)))
        else:
            import tempfile
            import zipfile
            dest = pathlib.Path(tempfile.mkdtemp(prefix="case_"))
            with zipfile.ZipFile(str(p)) as zf:
                for name in zf.namelist():
                    pure = pathlib.PurePosixPath(name)
                    if name.startswith("/") or ".." in pure.parts or "__MACOSX" in name \
                            or pure.name.startswith("._"):
                        continue
                    zf.extract(name, dest)
            p = dest
    rc = _load_read_case()
    if rc:
        data = rc.read_case_folder(str(p))
        files = list(data.get("files") or [])
        if not files:
            raise RuntimeError(f"read_case.py read no files from {p}")
        return files
    exts = {".md", ".markdown", ".txt", ".json", ".csv", ".tsv", ".yml", ".yaml"}
    files = []
    for f in sorted(pathlib.Path(p).rglob("*")):
        if not f.is_file() or f.name.startswith(".") or "__MACOSX" in f.parts:
            continue
        if f.suffix.lower() in exts:
            try:
                files.append({"name": str(f.relative_to(p)), "text": f.read_text(errors="replace")})
            except Exception:
                pass
    if not files:
        raise RuntimeError(f"no readable text files in {p} (install python-docx/openpyxl/pypdf "
                           f"for .docx/.xlsx/.pdf, or pass the contract and customers files directly)")
    return files


def score_contract_file(name, text):
    s = 0
    low = str(name).lower()
    if any(h in low for h in CONTRACT_NAME_HINTS):
        s += 3
    if _looks_like_openapi(text):
        s += 6
    verbs = len(re.findall(r"\b(POST|GET|PUT|PATCH|DELETE)\b", text or ""))
    s += min(3, verbs // 5)
    if "v1/" in (text or "") or "/v1" in (text or ""):
        s += 1
    return s


def score_customers_file(name, text):
    s = 0
    low = str(name).lower()
    if any(h in low for h in CUSTOMER_NAME_HINTS):
        s += 3
    try:
        d = json.loads(text or "")
    except Exception:
        d = None
    if d is not None:
        data = d if isinstance(d, list) else \
            (d.get("customers") or d.get("cases") or d.get("test_customers") if isinstance(d, dict) else None)
        if isinstance(data, list) and data and isinstance(data[0], dict):
            keys = set()
            for row in data[:3]:
                if isinstance(row, dict):
                    keys |= set(row.keys())
            if keys & {"variables", "identity", "products"}:
                s += 6
            else:
                s += 2
    return s


def _looks_like_openapi(text):
    try:
        d = json.loads(text or "")
    except Exception:
        return False
    return isinstance(d, dict) and isinstance(d.get("paths"), dict)


def _classify_case_files(files):
    """(contract_text, customers_text, primaries, notes) from a case folder."""
    scored = []
    for f in files:
        name, text = str(f.get("name") or ""), f.get("text") or ""
        scored.append((name, text, score_contract_file(name, text), score_customers_file(name, text)))
    c_order = sorted(scored, key=lambda x: -x[2])
    k_order = sorted((x for x in scored if x[3] >= 2), key=lambda x: -x[3])
    contract_text = "\n\n".join(f"--- FILE: {n} ---\n{t}" for n, t, _, _ in c_order)
    chosen = k_order[:3]
    customers_text = "\n\n".join(f"--- FILE: {n} ---\n{t}" for n, t, _, _ in chosen) or contract_text
    primary_contract = c_order[0][1] if c_order and c_order[0][2] >= 3 else ""
    primary_customers = k_order[0][1] if k_order else ""
    notes = [
        "case folder read: " + ", ".join(n for n, _, _, _ in scored[:12]) +
        (f" (+{len(scored) - 12} more)" if len(scored) > 12 else ""),
        "contract likelihood order: " + ", ".join(f"{n}={c}" for n, _, c, _ in c_order[:6]),
        "customers files: " + (", ".join(f"{n}={k}" for n, _, _, k in chosen) or "none found"),
    ]
    if primary_contract:
        notes.append(f"primary contract file: {c_order[0][0]}")
    else:
        notes.append("no single contract file scored high enough: the analysis call reads the "
                     "whole package")
    if not chosen:
        notes.append("no customers file recognised: the analysis and seed calls read the whole package")
    return contract_text, customers_text, primary_contract, primary_customers, notes


def read_inputs(first, second=None, quiet=False):
    """(folder | zip | file [| customers file]) -> the texts the generator consumes.

    One positional that is a folder or .zip: the case package (read_case.py handles
    .docx/.xlsx/.pdf). One positional that is a file: that file is used as both
    contract and customers (the model finds both inside it). Two positionals: an
    explicit contract file and customers file.
    """
    if second is None:
        p = pathlib.Path(first)
        if p.is_dir() or p.suffix.lower() == ".zip":
            contract_text, customers_text, pc, pk, notes = _classify_case_files(_read_case_files(p))
            for n in notes:
                log(f"   {n}")
            trace_line("case read: " + "; ".join(notes))
            return {"contract_text": contract_text, "customers_text": customers_text,
                    "context_text": contract_text, "primary_contract_text": pc,
                    "primary_customers_text": pk, "source": str(p), "notes": notes}
        if p.suffix.lower() in {".docx", ".xlsx", ".pdf"}:
            import shutil
            import tempfile
            tmp = pathlib.Path(tempfile.mkdtemp(prefix="casefile_"))
            shutil.copy2(p, tmp / p.name)
            files = _read_case_files(tmp)
            text = files[0]["text"] if files else ""
            if not text:
                raise RuntimeError(f"could not read any text out of {p} "
                                   f"(install python-docx/openpyxl/pypdf)")
        else:
            text = p.read_text()
        note = f"single file input: {p} used as contract and customers"
        log(f"   {note}")
        return {"contract_text": text, "customers_text": text, "context_text": text,
                "primary_contract_text": text, "primary_customers_text": text,
                "source": str(p), "notes": [note]}
    ctext = pathlib.Path(first).read_text()
    ktext = pathlib.Path(second).read_text()
    # Printed so a wrong pairing is caught by eye — a wrong seed fails every case.
    verb_count = len(re.findall(r"\b(POST|GET|PUT|PATCH|DELETE)\b", ctext))
    c_verdict = "openapi json" if _looks_like_openapi(ctext) else f"{verb_count} HTTP verb mentions"
    try:
        kd = json.loads(ktext)
        rows = kd if isinstance(kd, list) else \
            (kd.get("customers") or kd.get("cases") or kd.get("test_customers") or []
             if isinstance(kd, dict) else [])
        k_verdict = f"JSON with {len(rows)} case(s)" if isinstance(rows, list) else "JSON"
    except Exception:
        k_verdict = "not JSON (text)"
    log(f"   contract:  {first} ({len(ctext)} chars, {c_verdict})")
    log(f"   customers: {second} ({len(ktext)} chars, {k_verdict})")
    if not _looks_like_openapi(ctext) and score_contract_file(first, ctext) < 3:
        log("   WARNING: the contract file does not look like a service contract (no OpenAPI "
            "paths, few HTTP verbs) — check the pairing")
    if score_customers_file(second, ktext) < 2:
        log("   WARNING: the customers file does not look like a test-customer file — "
            "a wrong seed fails every case")
    return {"contract_text": ctext, "customers_text": ktext,
            "context_text": ctext + "\n\n" + ktext,
            "primary_contract_text": ctext, "primary_customers_text": ktext,
            "source": f"{first} + {second}", "notes": []}


# ------------------------------------------------------------------- generator --
def _llm_json(prompt, purpose, attempts=2, timeout=None):
    last = None
    for i in range(attempts):
        try:
            text = llm(prompt if i == 0 else prompt + "\n\nYour previous answer was not valid JSON. Reply with ONLY the JSON object.",
                       f"{purpose} (attempt {i + 1})", timeout=timeout)
            return extract_json(text)
        except Exception as exc:
            last = exc
            log(f"-- {purpose} attempt {i + 1} failed: {exc}")
    raise RuntimeError(f"{purpose}: no readable JSON answer ({last})")


def generate_mock(contract_text, customers_text, out_dir, *, name=None, repairs=2,
                  use_llm=True, verify=True, quiet=False,
                  primary_contract_text=None, primary_customers_text=None):
    """Generate worker.js, seed.json, README.md (+ analysis.json, endpoints.json,
    wrangler.toml, gen-trace.log) into out_dir. Returns a summary dict.

    contract_text/customers_text may be a whole package concatenated (the case-folder
    path); primary_contract_text/primary_customers_text then name the single best
    contract/customers file, which the deterministic fallback parsers use when they can.
    """
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    deadline = t0 + BUDGET

    def remaining():
        return max(0, int(deadline - time.time()))

    def call_timeout():
        return min(LLM_TIMEOUT, max(180, remaining()))

    trace_line(f"start: mock generation into {out} at {time.strftime('%Y-%m-%d %H:%M:%S')} UTC, "
               f"model {MODEL if use_llm else '(no-llm deterministic fallback)'}, "
               f"budget {BUDGET}s")
    trace_line(f"inputs: contract {len(contract_text)} chars, customers {len(customers_text)} chars")

    # 1. contract analysis (model call; deterministic OpenAPI fallback)
    analysis = None
    if use_llm:
        try:
            analysis = _llm_json(fill_tokens(ANALYSIS_PROMPT, {
                "<<<CONTRACT>>>": contract_text[:60000],
                "<<<CUSTOMERS>>>": customers_text[:40000],
            }), "analyse the service contract", timeout=call_timeout())
        except Exception as exc:
            log(f"-- contract analysis fell back to the deterministic parser: {exc}")
            trace_line(f"analysis fallback: {exc}")
    naive = naive_analysis(primary_contract_text or contract_text)
    if analysis is None:
        if naive is None:
            raise RuntimeError("the contract is not OpenAPI JSON and no model analysis is available")
        analysis = naive
    analysis = normalize_analysis(analysis, (naive or {}).get("base_path", ""))
    if not analysis["endpoints"] and naive:
        analysis["endpoints"] = normalize_analysis(naive)["endpoints"]
    trace_line(f"analysis: {len(analysis['endpoints'])} contract endpoints, "
               f"state_model {analysis['state_model']}, "
               f"{len(analysis.get('faults') or [])} faults, base '{analysis['base_path']}'")

    # 2. seed (model call; deterministic fallback for JSON customer files)
    seed = None
    if use_llm:
        try:
            seed = _llm_json(fill_tokens(SEED_PROMPT, {
                "<<<CONTRACT>>>": contract_text[:30000],
                "<<<CUSTOMERS>>>": customers_text[:60000],
            }), "normalise the test customers into seed.json", timeout=call_timeout())
        except Exception as exc:
            log(f"-- seed extraction fell back to the deterministic normaliser: {exc}")
            trace_line(f"seed fallback: {exc}")
    if seed is None:
        seed = naive_seed(primary_customers_text or customers_text)
    seed = normalize_seed(seed)
    trace_line(f"seed: {len(seed['customers'])} customers "
               f"({', '.join(c['customer_id'] for c in seed['customers'][:6])})")
    (out / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=1) + "\n")
    (out / "seed.json").write_text(json.dumps(seed, ensure_ascii=False, indent=1) + "\n")

    # 3. worker generation, validation, repair
    worker_name = name or _slug(analysis.get("service_name") or "bank-mock")
    if not worker_name.endswith("mock") and not worker_name.endswith("-mock"):
        worker_name = _slug(worker_name + "-mock")
    js = ""
    problems = []
    repairs_used = 0
    verify_left = 1 if (verify and use_llm) else 0
    if use_llm:
        prompt = build_worker_prompt(contract_text, customers_text, analysis, seed)
        for attempt in range(repairs + 1):
            try:
                if attempt == 0 or not js:
                    purpose = "generate the Cloudflare Worker" if attempt == 0 \
                        else f"retry the Worker generation (pass {attempt + 1})"
                    js = extract_code(llm(prompt, purpose, timeout=call_timeout()))
                else:
                    repairs_used = attempt
                    js = extract_code(llm(build_repair_prompt(js, problems, analysis),
                                          f"repair the Worker (pass {attempt})",
                                          timeout=call_timeout()))
            except Exception as exc:
                trace_line(f"worker attempt {attempt + 1} raised: {exc}")
                log(f"-- worker attempt {attempt + 1} raised: {exc}")
                if remaining() < 60:
                    raise
                problems = [f"the previous attempt failed before producing a file ({exc}); "
                            f"produce the complete worker file"]
                js = ""
                continue
            js = apply_seed(js, seed)
            problems = validate_worker(js, analysis, seed)
            trace_line(f"worker attempt {attempt + 1}: {len(js)} chars, "
                       f"{len(problems)} validation problem(s)"
                       + (": " + "; ".join(problems) if problems else " — clean"))
            if not problems and verify_left:
                # one conformance pass: does the worker actually match the contract?
                verify_left -= 1
                try:
                    verdict = _llm_json(build_verify_prompt(js, analysis, contract_text),
                                        "verify the worker against the contract",
                                        attempts=1, timeout=call_timeout())
                    issues = [str(i) for i in (verdict.get("issues") or []) if str(i).strip()]
                    trace_line("verification: " + ("clean"
                               if not issues else f"{len(issues)} issue(s): " + "; ".join(issues)[:600]))
                    log(f"-- verification: {'clean' if not issues else str(len(issues)) + ' issue(s)'}")
                    problems = [f"conformance check: {i}" for i in issues]
                except Exception as exc:
                    trace_line(f"verification skipped: {exc}")
                    log(f"-- verification skipped: {exc}")
            if not problems:
                break
        if problems:
            (out / "worker.rejected.js").write_text(js)
            raise RuntimeError("the generated Worker failed validation after "
                               f"{repairs + 1} attempts: " + "; ".join(problems)
                               + f" (kept as {out / 'worker.rejected.js'})")
    else:
        trace_line("stopped: --no-llm wrote analysis.json + seed.json; the worker step needs the model")
        (out / "gen-trace.log").write_text("\n".join(TRACE) + "\n")
        summary = {"out_dir": str(out), "worker": None, "seed": str(out / "seed.json"),
                   "contract_endpoints": len(analysis["endpoints"]),
                   "customers": len(seed["customers"]),
                   "state_model": analysis["state_model"],
                   "stopped": "no-llm mode: analysis.json + seed.json written; "
                              "worker generation is the model call itself"}
        if not quiet:
            log("-- no-llm mode: analysis.json + seed.json written; "
                "run again without --no-llm to generate worker.js")
        return summary
    (out / "worker.js").write_text(js)

    # 4. manifest, deploy config, README
    manifest = build_endpoints_manifest(analysis, seed, worker_name)
    (out / "endpoints.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n")
    (out / "wrangler.toml").write_text(render_wrangler_toml(worker_name, analysis))
    readme = render_readme({"out_dir": str(out)}, analysis, seed, worker_name,
                           repairs_used,
                           sum(1 for t in TRACE if t.startswith("model call:")))
    (out / "README.md").write_text(readme)

    trace_line(f"written: worker.js ({len(js)} chars), seed.json, endpoints.json, "
               f"wrangler.toml, README.md")
    trace_line(f"end: {time.strftime('%Y-%m-%d %H:%M:%S')} UTC, {time.time() - t0:.0f} s")
    (out / "gen-trace.log").write_text("\n".join(TRACE) + "\n")
    summary = {
        "out_dir": str(out),
        "worker": str(out / "worker.js"),
        "seed": str(out / "seed.json"),
        "readme": str(out / "README.md"),
        "endpoints": str(out / "endpoints.json"),
        "worker_name": worker_name,
        "contract_endpoints": len(analysis["endpoints"]),
        "customers": len(seed["customers"]),
        "state_model": analysis["state_model"],
        "repairs_used": repairs_used,
        "validation_problems": problems,
        "model_calls": len(TRACE),
        "seconds": round(time.time() - t0),
    }
    if not quiet:
        log("\n== mock generated ==")
        for k, v in summary.items():
            log(f"   {k}: {v}")
    return summary


def selftest(contract_path, customers_path):
    """Deterministic pipeline check with no model calls: template, seed embedding, validation.

    Catches damage to the template and to the deterministic path before the run that
    matters. Returns 0 when the structural checks pass.
    """
    contract_text = pathlib.Path(contract_path).read_text()
    customers_text = pathlib.Path(customers_path).read_text()
    structural, notes = [], []

    analysis = naive_analysis(contract_text)
    if analysis is None:
        notes.append("contract is not OpenAPI JSON: the deterministic analysis cannot run "
                     "(fine - the model analysis call handles Markdown contracts)")
        analysis = {"service_name": "selftest", "base_path": "", "endpoints": [],
                    "ledger": {}, "sessions": {}}
    analysis = normalize_analysis(analysis)
    try:
        seed = normalize_seed(naive_seed(customers_text))
    except Exception as exc:
        notes.append(f"customers are not normalisable without the model ({exc})")
        seed = {"customers": []}

    template = render_template(analysis)
    if SEED_PLACEHOLDER not in template:
        structural.append("the template lost the __SEED_JSON__ placeholder")
    for marker in ("export default", "async fetch", "/health", "MOCK_KV", "SEED.customers",
                   "LEDGER_PREFIX", "RESET_PREFIX", "handleCreateSession",
                   "function json(", "function canonPath(", "async function loadState(",
                   "function saveState(", "function record(", "function ledgerView(",
                   "function verifiedGate(", "function takeFault("):
        if marker not in template:
            structural.append(f"the template lost the marker: {marker}")
    bal = js_delimiter_balance(template)
    if bal:
        structural.append(f"template delimiter balance: {bal}")

    js = apply_seed(template, seed)
    seed_line = next((l for l in js.splitlines() if l.startswith("const SEED =")), None)
    if seed_line is None:
        structural.append("apply_seed did not produce a `const SEED = ...;` line")
    else:
        try:
            json.loads(seed_line[len("const SEED ="):].strip().rstrip(";"))
        except Exception as exc:
            structural.append(f"the embedded SEED is not valid JSON: {exc}")

    problems = validate_worker(js, analysis, seed)
    route_notes = [p for p in problems
                   if p.startswith(("no route for contract endpoint", "no ledger read route"))]
    notes.append(f"template coverage: {len(analysis.get('endpoints') or [])} contract endpoints; "
                 f"the model must wire {len(route_notes)} more route(s) than the template "
                 f"(the template has the ledger/health/session routes)")
    notes += [p for p in problems if p not in route_notes]

    log("== selftest ==")
    for n in notes:
        log(f"   note: {n}")
    for p in structural:
        log(f"   FAIL: {p}")
    log(f"   {'FAIL' if structural else 'ok'}: {len(seed['customers'])} customers seeded, "
        f"template {len(template)} chars, embedded seed {len(seed_line or '')} chars")
    return 1 if structural else 0


def _slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")
    return (s or "bank-mock")[:54]


def _deployed_url(out_dir):
    """The deployed mock base URL: host + the contract base path when known.

    deploy.sh records url, base_path and mock_url in deployed.json; build.py wants the
    base path included (gen.py appends the tool paths to the URL it is handed).
    """
    try:
        data = json.loads((pathlib.Path(out_dir) / "deployed.json").read_text())
    except Exception:
        return ""
    return str(data.get("mock_url") or data.get("url") or "")


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("case", nargs="?",
                    help="the case folder (or .zip) as delivered — contract and customers are "
                         "found inside it; or, with two arguments, the service contract file")
    ap.add_argument("customers", nargs="?",
                    help="test customers file (only when two positional arguments are given)")
    ap.add_argument("--out", default=str(ROOT / "mock"), help="output directory (default: mock/)")
    ap.add_argument("--name", default=None, help="Cloudflare worker name (default: derived from the contract)")
    ap.add_argument("--model", default=None, help="model for the generation calls (default: claude-sonnet-5-5)")
    ap.add_argument("--repairs", type=int, default=2, help="repair attempts after failed validation (default 2)")
    ap.add_argument("--deploy", action="store_true",
                    help="after generating, run mock/deploy.sh (needs CF_API_TOKEN + CF_ACCOUNT_ID) "
                         "and print MOCK_URL=... for builder/build.py")
    ap.add_argument("--with-kv", action="store_true",
                    help="with --deploy: create/bind the MOCK_KV namespace (state across isolates)")
    ap.add_argument("--no-verify", action="store_true",
                    help="skip the conformance-verification model call (it feeds the repair loop)")
    ap.add_argument("--no-llm", action="store_true",
                    help="deterministic path only: write analysis.json + seed.json, skip the worker step")
    ap.add_argument("--selftest", action="store_true",
                    help="no model calls: check the template, the seed embedding and the validators")
    a = ap.parse_args()

    global MODEL
    if a.model:
        MODEL = a.model
    if not a.case:
        rc = _load_read_case()
        default_case = str(getattr(rc, "DEFAULT_CASE_DIR", "")) if rc else ""
        for cand in (default_case, "case", "case_folder"):
            if cand and pathlib.Path(cand).is_dir():
                a.case = cand
                log(f"-- using the case folder {cand}/")
                break
        else:
            ap.error("give the case folder (python3 builder/mock_gen.py <case_folder> --deploy) "
                     "or a contract file plus a customers file")
    if a.customers is not None and pathlib.Path(a.case).is_dir():
        ap.error("<case> is a folder — pass either the folder alone, or two files "
                 "(<contract_file> <customers_file>)")
    if a.selftest:
        if a.customers is None:
            ap.error("--selftest wants the explicit pair: "
                     "python3 builder/mock_gen.py <contract_file> <customers_file> --selftest")
        sys.exit(selftest(a.case, a.customers))

    inputs = read_inputs(a.case, a.customers)
    summary = generate_mock(inputs["contract_text"], inputs["customers_text"], a.out,
                            name=a.name, repairs=a.repairs, use_llm=not a.no_llm,
                            verify=not a.no_verify,
                            primary_contract_text=inputs.get("primary_contract_text"),
                            primary_customers_text=inputs.get("primary_customers_text"))
    if not summary.get("worker"):
        log(f"\n{summary.get('stopped', '')}")
        sys.exit(3)

    deploy_cmd = (f"bash {ROOT / 'mock' / 'deploy.sh'} --dir {summary['out_dir']}"
                  f"{' --with-kv' if a.with_kv else ''}")
    if not a.deploy:
        log(f"\nnext: export CF_API_TOKEN=... CF_ACCOUNT_ID=...\n      {deploy_cmd}")
        return
    cmd = ["bash", str(ROOT / "mock" / "deploy.sh"), "--dir", summary["out_dir"]]
    if a.with_kv:
        cmd.append("--with-kv")
    log(f"\n== deploy: {' '.join(cmd)} ==")
    try:  # a stale URL from an earlier deploy must never print as this run's
        (pathlib.Path(summary["out_dir"]) / "deployed.json").unlink()
    except FileNotFoundError:
        pass
    rc = subprocess.run(cmd, check=False).returncode
    url = _deployed_url(summary["out_dir"])
    if url:
        log(f"\nMOCK_URL={url}")
        log(f"next: python3 builder/build.py <case_folder> {url}")
    if rc != 0:
        log(f"-- deploy.sh exited {rc}; after fixing, re-run: {' '.join(cmd)}")
    sys.exit(rc)


if __name__ == "__main__":
    main()
