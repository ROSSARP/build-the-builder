#!/usr/bin/env python3
"""Self-healing harness for the final case (Freya Bank statement-debt phone agent).

Owner: the self-healing agent.  This file is the test harness described in the
final-window brief:

    python3 -I tests/self_heal.py scan      # diff finalcase/ (+case-download/) vs state
    python3 -I tests/self_heal.py extract   # LLM-extract final_contract/spec/examples
    python3 -I tests/self_heal.py check     # tests (a)-(d) against the artefacts
    python3 -I tests/self_heal.py all       # scan + extract-if-needed + check

Artefacts this harness owns and reads (all under tests/):
    final_contract.json   the bank services, normalised OpenAPI-like
    final_spec.json       the query-domain rule ledger (feeds builder/gen_query.py)
    example_checks.json   replayable checks derived from example-scenarios.md
    self_heal_state.json  the file manifest of the last cycle
    self_heal_report.md   the dated cycle log (appended by --report)
    patches/              unified diffs for files owned by other agents

stdlib only.  Every doc read is defensive: a corrupt file is skipped, never fatal.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
STATE_PATH = TESTS / "self_heal_state.json"
REPORT_PATH = TESTS / "self_heal_report.md"
CONTRACT_PATH = TESTS / "final_contract.json"
SPEC_PATH = TESTS / "final_spec.json"
EXAMPLES_PATH = TESTS / "example_checks.json"
PATCHES = TESTS / "patches"

CASE_SOURCES = ["finalcase", "case-download"]
TEXT_EXTS = {".md", ".markdown", ".txt", ".csv", ".tsv", ".json", ".yml", ".yaml"}

DUMMY_MOCK = "https://mock-selfheal.example.workers.dev"


def now_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------- #
# reading case files (downloaded, untrusted: decode defensively)
# --------------------------------------------------------------------------- #

def read_text_any(path: pathlib.Path) -> str | None:
    """Best-effort text of one case file; None when it has no extractable text."""
    ext = path.suffix.lower()
    try:
        if ext in TEXT_EXTS:
            data = path.read_bytes()
            for enc in ("utf-8-sig", "utf-8", "cp1254"):
                try:
                    return data.decode(enc)
                except UnicodeDecodeError:
                    continue
            return data.decode("utf-8", errors="replace")
        if ext == ".pdf":
            try:
                r = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                                   capture_output=True, text=True, timeout=120)
                return r.stdout if r.returncode == 0 else None
            except Exception:
                return None
        if ext == ".docx":
            try:
                import docx  # type: ignore
            except ImportError:
                return None
            try:
                d = docx.Document(str(path))
                parts = [p.text for p in d.paragraphs]
                for i, t in enumerate(d.tables, 1):
                    parts.append(f"[table {i}]")
                    for row in t.rows:
                        parts.append(" | ".join(c.text.strip() for c in row.cells))
                return "\n".join(parts)
            except Exception:
                return None
        if ext == ".xlsx":
            try:
                import openpyxl  # type: ignore
            except ImportError:
                return None
            try:
                wb = openpyxl.load_workbook(filename=str(path), read_only=True, data_only=True)
                try:
                    out = []
                    for ws in wb.worksheets:
                        out.append(f"[sheet: {ws.title}]")
                        for row in ws.iter_rows(values_only=True):
                            vals = ["" if v is None else str(v) for v in row]
                            if any(v.strip() for v in vals):
                                out.append(" | ".join(vals).rstrip(" |"))
                    return "\n".join(out)
                finally:
                    wb.close()
            except Exception:
                return None
    except Exception:
        return None
    return None


def case_files(source: str) -> list[pathlib.Path]:
    base = ROOT / source
    if not base.is_dir():
        return []
    skip = {".manifest.json"}
    return sorted((p for p in base.rglob("*")
                   if p.is_file() and p.name not in skip
                   and not any(part.startswith(".") for part in p.relative_to(base).parts)),
                  key=lambda p: str(p.relative_to(base)).lower())


def case_manifest() -> dict:
    man = {}
    for source in CASE_SOURCES:
        for p in case_files(source):
            rel = str(p.relative_to(ROOT / source))
            try:
                size = p.stat().st_size
            except OSError:
                size = -1
            man[f"{source}/{rel}"] = {"size": size}
    return man


def load_case_docs() -> dict[str, str]:
    """{source/relpath: text} for every readable file in the case sources.

    When the same relative path exists in both sources, finalcase/ wins.
    """
    docs: dict[str, str] = {}
    for source in CASE_SOURCES:  # finalcase first, then case-download fills gaps
        for p in case_files(source):
            rel = str(p.relative_to(ROOT / source))
            if rel in docs:
                continue
            text = read_text_any(p)
            if text is not None:
                docs[rel] = text
    return docs


def pick_docs(docs: dict[str, str], *needles: str, limit: int = 60_000,
              skip: tuple[str, ...] = (), total_limit: int = 380_000) -> str:
    """Concatenate the docs whose (lowercased) path contains any needle.

    A `skip` needle excludes a path even when another needle matches it.  Each
    file is truncated at `limit`, the whole blob at `total_limit` — a prompt
    over ARG_MAX/stdin practicality is worse than a truncated document.
    """
    wanted = [n.lower() for n in needles]
    skipped = [n.lower() for n in skip]
    parts, used = [], 0
    for rel, text in docs.items():
        low = rel.lower()
        if not any(n in low for n in wanted):
            continue
        if any(n in low for n in skipped):
            continue
        if len(text) > limit:
            text = text[:limit] + "\n...[truncated]"
        if used + len(text) > total_limit:
            parts.append(f"=== {rel} ===\n...[skipped: prompt budget]")
            continue
        used += len(text)
        parts.append(f"=== {rel} ===\n{text}")
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- #
# scan: manifest diff
# --------------------------------------------------------------------------- #

def cmd_scan(update_state: bool = True, verbose: bool = True) -> dict:
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        state = {"manifest": {}}
    prev = state.get("manifest") or {}
    cur = case_manifest()

    new = sorted(k for k in cur if k not in prev)
    changed = sorted(k for k in cur if k in prev and cur[k].get("size") != prev[k].get("size"))
    gone = sorted(k for k in prev if k not in cur)

    state["manifest"] = cur
    state["last_scan_utc"] = now_utc()
    if "created_utc" not in state:
        state["created_utc"] = now_utc()
    if update_state:
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n",
                              encoding="utf-8")
    result = {"new": new, "changed": changed, "gone": gone, "total": len(cur)}
    if verbose:
        log(f"scan {state['last_scan_utc']}: {len(cur)} files, "
            f"{len(new)} new, {len(changed)} changed, {len(gone)} gone")
        for k in new:
            log(f"  NEW     {k}")
        for k in changed:
            log(f"  CHANGED {k}")
        for k in gone:
            log(f"  GONE    {k}")
    return result


# --------------------------------------------------------------------------- #
# LLM calls through the claude CLI (session model; no --model flag)
# --------------------------------------------------------------------------- #

def llm(prompt: str, purpose: str, timeout: int = 900) -> str:
    # the prompt goes over stdin: a case-document prompt can exceed ARG_MAX
    cmd = ["claude", "-p", "--output-format", "json"]
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("ANTHROPIC_MODEL", "CLAUDE_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL"))
           and not k.startswith("ANTHROPIC_DEFAULT_")}
    t0 = _dt.datetime.now()
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout, env=env)
    took = (_dt.datetime.now() - t0).total_seconds()
    out = (r.stdout or "").strip()
    result = ""
    try:
        result = json.loads(out).get("result", "")
    except Exception:
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    result = json.loads(line).get("result", "")
                    break
                except Exception:
                    continue
    if not result and r.returncode != 0:
        raise RuntimeError(f"model call failed ({purpose}): {(r.stderr or '')[:400]}")
    log(f"  model call: purpose={purpose}, prompt {len(prompt)} chars, "
        f"answer {len(str(result))} chars, {took:.0f}s")
    return str(result)


def extract_json(text: str) -> dict:
    """The first JSON object inside an LLM answer, fences and chatter stripped."""
    t = str(text).strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in the model answer")
    return json.loads(t[start:end + 1])


# --------------------------------------------------------------------------- #
# extract: contract / spec / example checks
# --------------------------------------------------------------------------- #

CONTRACT_PROMPT = """You are normalising a bank's IVR integration document into ONE machine-readable service contract.

--- DOCUMENTS ---
{docs}

--- TASK ---
From the services section of the integration document — the numbered service subsections that define each service's request and response (in the 2026-10-01 contract these are sections 5.1–5.7; the BRIEF to us called it section 6, so whatever section carries the per-service definitions) and from the service-response examples themselves, produce ONE JSON object with exactly these keys:

{{
 "base_path": "the common path prefix of every service (e.g. /v1), or \\"\\"",
 "servers": ["every base URL the document names"],
 "transport": "POST|GET|...",          // the method the services use
 "content_type": "application/json",
 "customer_number": {{"field": "the request field carrying the 8-digit customer number", "type": "string", "digits": 8}},
 "services": [
   {{"name": "short snake_case name",
    "path": "path after the base path, e.g. /cards",
    "description": "one line, from the document",
    "request": [{{"name": "field", "type": "string|number|boolean|object|array", "required": true/false, "description": "..."}}],
    "response": [{{"name": "field", "type": "...", "always_present": true/false, "description": "..."}}],
    "errors": [{{"status": 200/400/404/409/500, "when": "the condition the document gives", "response": {{}}}}]
   }}
 ],
 "error_semantics": "the document's rules for HTTP status vs. not-found vs. invalid input, as sentences",
 "notes": ["every other rule the document states that a mock or agent must obey (state, idempotency, ordering, second factor...)"]
}}

Rules: copy names, paths, field names, enum values and status codes EXACTLY as the document writes them. Never invent a service, field or status. A service the document describes as returning two answers (e.g. found / not found) must carry both branches in response/errors. Output ONLY the JSON object.

--- SERVICE EXAMPLES (may be empty) ---
{examples}
"""

SPEC_PROMPT = """You are building the rule ledger for a Turkish phone agent that answers Freya Bank's "how much is my credit card statement debt?" call. Read the documents below and answer with ONE JSON object, in the rule-ledger style: typed rule records whose `text` fields copy the documents' own sentences (Turkish where the source is Turkish), plus the structured params a compiler needs.

--- DOCUMENTS ---
{docs}

--- SERVICE CONTRACT (normalised from the integration document; use its paths) ---
{contract_hint}

--- REQUIRED JSON ---
{{
 "domain": "statement_debt_query",
 "bank_name": "Freya Bank",
 "language": "Turkish",
 "tool_paths": {{"statement": "the contract path that returns the card(s) and the statement debt",
   "move": "the contract path that moves the statement date", "email": "the contract path that e-mails the statement",
   "transfer": "the contract path that hands the call to a human", "close": "the contract path that closes the call"}},
 "query": {{"currencies": ["TRY","USD","EUR","GBP"],
   "move_rule_text": "one paragraph: the statement-date move rule with its exact date semantics"}},
 "dates": {{"holidays": ["every holiday the documents name, YYYY-MM-DD"],
   "validity_text": "what makes a date valid (not in the past, business day, ...)",
   "weekend_text": "weekend/holiday handling", "vague_text": "vague period handling",
   "next_weekday_text": "next-Friday-style semantics"}},
 "variables": {{"customerNumber": "8-digit customer number from the phone menu (agent never asks)",
   "now": "Istanbul date-time of the call; every date decision uses it, never the system clock"}},
 "call_flow": [
   {{"stage": "snake_case stage name", "step": int, "what": "what happens", "source": "file it came from"}}
 ],
 "rule_ledger": [
   {{"type": "debt_read_rule", "params": {{"currencies": ["TRY","USD","EUR","GBP"],
       "per_card": "read the card's last 4 digits, card name, cut-off date and due date before the amounts",
       "no_debt_text": "the exact Turkish sentence for a card with no statement debt",
       "zero_vs_missing": "how 'no debt' differs from 'card not found'",
       "amounts_reading": "how each currency amount is said"}}, "text": "the source sentences"}},
   {{"type": "date_rule", "params": {{"weeks": [1, 2, ...],
       "valid": "what makes the new date valid", "weekend_holiday": "weekend/holiday handling",
       "vague": "vague period handling", "next_weekday": "next-Friday-style semantics",
       "after_deadline": "what happens if the requested week is already past",
       "date_semantics": "what each week label means for dates (which weekday, when it takes effect, first statement? next statement?)",
       "shared_statement": "primary vs linked card rules for shared statements",
       "limits": ["any prohibition (e.g. cannot move backwards, cannot move within the same week)"]}}, "text": "the statement-date move rule, verbatim"}},
   {{"type": "email_rule", "params": {{"registered_lookup": "...", "read_address_text": "...",
       "confirm_text": "...", "send_text": "...", "no_address_text": "...",
       "address_format": "how the address is read out"}}, "text": "..."}},
   {{"type": "transfer_rule", "params": {{"to_human_when": ["every trigger that hands the call to a human (pay intent, explicit ask, other intents)"],
       "transfer_text": "...", "what_to_say_before": "...", "supervisor_return": "what returning to the supervisor means"}}, "text": "..."}},
   {{"type": "ivr_rule", "params": {{"second_factor": "what the flow says about the second factor and who performs it",
       "handoff": "what the IVR hands to the assistant and what it does not"}}, "text": "..."}},
   {{"type": "language_rule", "params": {{"only_turkish": "YALNIZCA Türkçe konuşun",
       "mandatory_sentences": [{{"id": "monitored|language|other", "text": "exact Turkish sentence"}}],
       "forbidden_phrases": ["words/phrases the agent must never say (English words, recording words, out-of-scope promises...)"]}}, "text": "..."}},
   {{"type": "closing_rule", "params": {{"table": [{{"outcome": "...", "reasons": ["..."], "when": "..."}}],
       "closing_lines": ["how a call ends when the caller is done"],
       "no_input_text": "...", "goodbye_text": "...", "outcome_vocabulary": ["any outcome/reason words the documents define, else []"]}}, "text": "..."}},
   {{"type": "vocabulary_rule", "params": {{"mandatory_sentences": [{{"id": "...", "text": "exact Turkish sentence"}}],
       "forbidden_before_identity": [], "must_say": ["..."], "never_say": ["..."],
       "numbers_and_dates": "how amounts/dates are read aloud"}}, "text": "..."}},
   {{"type": "sequence_rule", "params": {{"steps": ["ordering constraints between the services and stages, e.g. card list before statement debt"]}}, "text": "..."}}
 ],
 "open_questions": ["every place the documents disagree; name both readings and their sources"]
}}

Rules:
- Derive EVERY rule from the documents; never invent a rule. Where the documents disagree, record the disagreement in open_questions and pick the reading that the newer/more specific document supports (say which in the text).
- The four-currency debt reading (TRY, USD, EUR, GBP) and its exact Turkish sentences must be complete.
- The statement-date move rule must state the date semantics precisely (which dates the customer is offered, which weekday each week starts on, what happens on/after the cut-off, the first vs next statement distinction if the documents make one, and every limit). Put the same rule text in query.move_rule_text and in the date_rule ledger text.
- The e-mail rule and the transfer-to-human rules must be complete, including what the agent may NOT do.
- forbidden_phrases and mandatory_sentences must be exhaustive for what the documents state.
- tool_paths must use exactly the paths of the service contract above; when the contract has no path for a role, use "".
- Output ONLY the JSON object.
"""

EXAMPLES_PROMPT = """You turn the bank's six example conversations into replayable checks.

--- EXAMPLE SCENARIOS DOCUMENT ---
{docs}

--- TASK ---
For EACH of the six example conversations, answer with ONE JSON object:

{{
 "source": "the file name",
 "examples": [
   {{"id": "example-1",
    "kind": "ordinary|edge|adversarial",
    "title": "short title",
    "call_variables": {{"customerNumber": "...", "now": "..."}},
    "customer_lines": ["every caller utterance, in order, verbatim"],
    "agent_before_each": ["what the agent must do/say before the caller's nth line; derive ONLY from the document"],
    "expected_tool_calls": [{{"service": "the service/path name the call implies", "when": "before/after which customer line", "request_highlights": {{}}}}],
    "expected_agent_behaviour": ["every assertion the document supports: required sentences (verbatim), forbidden phrases, tool ordering, what must be read (amounts, dates, addresses), how the call ends"],
    "expected_outcome": "any closing outcome the document shows, else \\"\\"",
    "source_quotes": ["the exact document sentences each assertion is derived from"]}}
 ],
 "global_rules": ["rules the document states that apply to every conversation"]
}}

Rules: derive every assertion ONLY from the document — never invent expected behaviour. If the document shows a sentence the agent says, quote it verbatim in expected_agent_behaviour and in source_quotes. If an example has no customerNumber or now, infer from the document or mark with "" . Output ONLY the JSON object.
"""


def _write_json(path: pathlib.Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(f"  wrote {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")


def cmd_extract(only: str = "all") -> None:
    docs = load_case_docs()
    if not docs:
        log("extract: no case documents readable yet — nothing to do")
        return
    log(f"extract: {len(docs)} readable docs: {', '.join(sorted(docs))}")

    if only in ("all", "contract"):
        body = pick_docs(docs, "integration", "entegrasyon", "entegre", "ivr", "api",
                         "service-contract", "service_contract", "kontrat")
        examples = pick_docs(docs, "service-example", "service_example", "servis-ornek",
                             "serviceexamples", "examples-service", "servis-ornegi",
                             "ornek", skip=("scenario", "senaryo"))
        if not body:
            log("extract contract: the IVR integration document is not here yet")
        else:
            obj = extract_json(llm(CONTRACT_PROMPT.format(docs=body, examples=examples),
                                   "extract contract"))
            obj["_extracted_utc"] = now_utc()
            _write_json(CONTRACT_PATH, obj)

    if only in ("all", "spec"):
        body = pick_docs(docs, "brief", "readme", "flow", "akis", "announce", "duyuru",
                         "faq", "sss", "sikca", "abbrev", "kisaltma", "analiz", "analysis",
                         "meeting", "toplanti", "notlar", "notes", "data-model", "veri",
                         "email", "mail", "test-environment", "customer",
                         "service-contract", "service_contract", "kontrat",
                         skip=(".json", ".csv", ".xlsx"))
        if not body.strip():
            log("extract spec: no key documents readable yet")
        else:
            hint = ""
            try:
                c = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
                hint = json.dumps({"base_path": c.get("base_path"),
                                   "services": [{"name": s.get("name"), "path": s.get("path"),
                                                 "method": s.get("method", "POST")}
                                                for s in c.get("services", [])]},
                                  ensure_ascii=False, indent=1)
            except Exception:
                hint = "(no contract extracted yet — use the integration document's paths)"
            obj = extract_json(llm(SPEC_PROMPT.format(docs=body, contract_hint=hint), "extract spec"))
            obj["_extracted_utc"] = now_utc()
            _write_json(SPEC_PATH, obj)

    if only in ("all", "examples"):
        body = pick_docs(docs, "example-scenarios", "example_scenarios", "ornek", "example")
        if not body:
            log("extract examples: example-scenarios file is not here yet")
        else:
            obj = extract_json(llm(EXAMPLES_PROMPT.format(docs=body), "extract examples"))
            obj["_extracted_utc"] = now_utc()
            _write_json(EXAMPLES_PATH, obj)


# --------------------------------------------------------------------------- #
# check (a): contract vs. test customers
# --------------------------------------------------------------------------- #

def check_contract_vs_customers(res: dict) -> None:
    name = "a_contract_vs_customers"
    problems = []
    try:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        res[name] = {"status": "SKIP", "why": f"final_contract.json unreadable: {e}"}
        return
    cust_paths = []
    for source in CASE_SOURCES:
        for p in case_files(source):
            if p.name.lower().startswith("test-customers") and p.suffix.lower() == ".json":
                cust_paths.append(p)
    if not cust_paths:
        res[name] = {"status": "SKIP", "why": "no test-customers.json in the case yet"}
        return
    try:
        customers = json.loads(cust_paths[0].read_text(encoding="utf-8"))
    except Exception as e:
        res[name] = {"status": "FAIL", "why": f"test-customers.json unreadable: {e}"}
        return

    records: list[dict] = []
    if isinstance(customers, list):
        records = [c for c in customers if isinstance(c, dict)]
    elif isinstance(customers, dict):
        for v in customers.values():
            if isinstance(v, list):
                records = [c for c in v if isinstance(c, dict)]
                break
            if isinstance(v, dict):
                records = [c for c in customers.values() if isinstance(c, dict)]
                break
    if not records:
        res[name] = {"status": "FAIL", "why": "no customer records found in test-customers.json"}
        return

    # every request field a contract service references must exist somewhere in the
    # seed data — the field the agent/tool sends must be resolvable in the mock
    required_fields = set()
    cust_field = ((contract.get("customer_number") or {}).get("field")) or "customerNumber"
    required_fields.add(cust_field)
    for svc in contract.get("services", []):
        for f in svc.get("request", []):
            if isinstance(f, dict) and f.get("name"):
                required_fields.add(f["name"])
    sample = records[0]
    sample_keys = set(sample.keys())

    # the customer-number field must be present on every record (the IVR passes it)
    missing_on_some = [i for i, r in enumerate(records) if cust_field not in r]
    if missing_on_some:
        problems.append(f"{cust_field} missing on records {missing_on_some[:5]}")
    # other request fields: the request may carry more than the record exposes
    # (nullable/optional extra parameter), so only report them as a warning list
    absent = sorted(f for f in required_fields if f not in sample_keys and f != cust_field)

    res[name] = {"status": "FAIL" if problems else "PASS",
                 "records": len(records),
                 "customer_field": cust_field,
                 "request_fields": sorted(required_fields),
                 "fields_not_on_a_customer_record": absent,
                 "problems": problems,
                 "note": "fields_not_on_a_customer_record are reported, not failures: a request "
                         "may legitimately carry parameters beyond the seed record"}


# --------------------------------------------------------------------------- #
# check (b): build the workflow from final_spec.json + final_contract.json
# --------------------------------------------------------------------------- #

def _load_gen_query():
    if not (ROOT / "builder" / "gen_query.py").is_file():
        return None
    sys.path.insert(0, str(ROOT))
    try:
        from builder import gen_query  # type: ignore
        return gen_query
    except Exception as e:
        log(f"  gen_query import failed: {type(e).__name__}: {e}")
        return None


def _fake_api_from_contract(contract: dict) -> dict:
    """An OpenAPI-like dict shaped the way gen.py/gen_query expect (paths -> post)."""
    api = {"servers": [{"url": DUMMY_MOCK}], "mock_url": DUMMY_MOCK, "paths": {}}
    base = contract.get("base_path", "")
    for svc in contract.get("services", []):
        path = svc.get("path", "")
        if not path.startswith("/"):
            path = "/" + path
        full = base + path
        req_props = {}
        required = []
        for f in svc.get("request", []):
            req_props[f["name"]] = {"type": f.get("type", "string"),
                                    "description": f.get("description", "")}
            if f.get("required"):
                required.append(f["name"])
        api["paths"][full] = {"post": {
            "requestBody": {"content": {"application/json": {"schema": {
                "type": "object", "properties": req_props, "required": required}}}},
            "responses": {"200": {"description": "ok"}},
        }}
    return api


_EN_STOP = {"the", "and", "you", "your", "this", "that", "with", "for", "are", "is",
            "will", "must", "not", "say", "tell", "ask", "call", "please", "should",
            "from", "when", "after", "before", "customer", "card", "statement", "date"}
_TR_STOP = {"ve", "bir", "bu", "için", "siz", "sizin", "değil", "lütfen", "müşteri",
            "kart", "borç", "tarih", "söyle", "söyleyin", "isteyin", "edin", "ise",
            "olarak", "diye", "sonra", "gün", "hafta", "ekstre", "arayan", "hakkında"}


def _turksh_score(text: str) -> tuple[int, int]:
    """(english_hits, turkish_hits) for one text: distinct stopword counts."""
    low = " " + re.sub(r"\s+", " ", str(text).lower()) + " "
    eh = sum(1 for w in _EN_STOP if f" {w} " in low)
    th = sum(1 for w in _TR_STOP if f" {w} " in low)
    return eh, th


def _english_sentences(text: str) -> list:
    """Sentences that look English: >=3 English stopwords and no Turkish one.

    Sentence-level so English prose embedded inside otherwise-Turkish text is
    caught (the classic leak: English rule texts pasted into a task_message).
    """
    flat = re.sub(r"\s+", " ", str(text or ""))
    out = []
    for s in re.split(r"(?<=[.!?])\s+", flat):
        if len(s) < 60:
            continue
        low = " " + s.lower() + " "
        eh = sum(1 for w in _EN_STOP if f" {w} " in low)
        th = sum(1 for w in _TR_STOP if f" {w} " in low)
        if eh >= 3 and th == 0:
            out.append(s.strip())
    return out


def _walk_strings(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def check_workflow_from_spec(res: dict) -> None:
    name = "b_workflow_from_spec"
    if not SPEC_PATH.is_file() or not CONTRACT_PATH.is_file():
        res[name] = {"status": "SKIP", "why": "final_spec.json / final_contract.json not written yet"}
        return
    gq = _load_gen_query()
    if gq is None:
        res[name] = {"status": "SKIP", "why": "builder/gen_query.py not present/compilable yet"}
        return
    try:
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        res[name] = {"status": "FAIL", "why": f"artefact unreadable: {e}"}
        return

    api = _fake_api_from_contract(contract)
    os.environ["MOCK_URL"] = DUMMY_MOCK
    workflow = None
    err = None
    try:
        fn = None
        for cand in ("build_query_workflow", "build_workflow", "generate_workflow",
                     "build", "generate"):
            f = getattr(gq, cand, None)
            if callable(f):
                fn = f
                break
        if fn is None:
            raise RuntimeError("gen_query has no build_query_workflow/build_workflow entry point")
        for call in (lambda: fn(spec, api, DUMMY_MOCK), lambda: fn(spec, api),
                     lambda: fn(spec, contract, api), lambda: fn(spec=spec, api=api,
                                                               mock_base=DUMMY_MOCK)):
            try:
                workflow = call()
                break
            except TypeError as e:
                err = e
                continue
        if workflow is None:
            raise RuntimeError(f"no call convention worked for {fn}: {err}")
    except Exception as e:
        res[name] = {"status": "FAIL", "why": f"gen_query build failed: {type(e).__name__}: {e}"}
        return

    problems, warnings = [], []
    if not isinstance(workflow, dict):
        res[name] = {"status": "FAIL", "why": "build returned a non-dict workflow"}
        return
    nodes = workflow.get("nodes") or {}
    if not nodes:
        problems.append("workflow has no nodes")
    if workflow.get("initial_node") not in nodes:
        problems.append("initial_node missing from nodes")

    # wiring: transitions/max_turn targets must exist; every node must be
    # reachable from the initial node
    targets = set()
    for nid, node in nodes.items():
        if not isinstance(node, dict):
            continue
        for tr in node.get("transitions") or []:
            if isinstance(tr, dict) and tr.get("target_node"):
                targets.add(str(tr["target_node"]))
        if node.get("max_turn_transition"):
            targets.add(str(node["max_turn_transition"]))
        for k in ("passthrough_default_transition", "on_enter_target"):
            if node.get(k):
                targets.add(str(node[k]))
    bad_targets = sorted(t for t in targets if t not in nodes)
    if bad_targets:
        problems.append(f"transitions point to unknown nodes: {bad_targets}")
    seen, stack = set(), [workflow.get("initial_node")]
    while stack:
        cur = stack.pop()
        if cur in seen or cur not in nodes:
            continue
        seen.add(cur)
        node = nodes[cur]
        nxt = [tr["target_node"] for tr in (node.get("transitions") or [])
               if isinstance(tr, dict) and tr.get("target_node")]
        if node.get("max_turn_transition"):
            nxt.append(node["max_turn_transition"])
        if node.get("passthrough_default_transition"):
            nxt.append(node["passthrough_default_transition"])
        stack.extend(nxt)
    unreachable = sorted(set(nodes) - seen)
    if unreachable:
        warnings.append(f"nodes unreachable from initial: {unreachable}")

    # language: Turkish-only. The model-facing prompt fields must carry no
    # English sentences (the task's assertion: no English in task_message /
    # on_enter; the other prompt-bearing fields are covered too). English text
    # in parameter/description metadata copied from the English contract is
    # recorded as info, not a failure — it is never spoken.
    en_leaks, en_notes = [], []
    for path, text in _walk_strings(workflow):
        sentences = _english_sentences(text)
        if not sentences:
            continue
        last = path.split(".")[-1].split("[")[0]
        if (last in ("system_prompt", "task_message", "routing_prompt", "loop_prompt",
                     "role_message", "on_enter") or ".on_enter" in path):
            en_leaks.append({"where": path, "sentences": sentences[:2]})
        else:
            en_notes.append({"where": path, "text": sentences[0][:120]})
    if en_leaks:
        problems.append(f"English sentences in prompt fields: {len(en_leaks)}")
    sp = str(workflow.get("system_prompt", ""))
    if "YALNIZCA" not in sp and "yalnızca" not in sp.lower():
        problems.append("system_prompt does not carry the hard 'YALNIZCA Türkçe konuşun' line")

    # tool URLs must use the dummy mock base
    bad_urls = []
    for path, text in _walk_strings(workflow):
        if path.endswith(".url.default") and text.startswith("http") and not text.startswith(DUMMY_MOCK):
            bad_urls.append({"where": path, "url": text})
    if bad_urls:
        problems.append(f"tool URLs not on the mock base: {len(bad_urls)}")

    # every contract service path must be one of the tool URLs
    base = str(contract.get("base_path", "") or "")
    contract_paths = []
    for svc in contract.get("services", []):
        p = str(svc.get("path", "") or "")
        if p and not p.startswith("/"):
            p = "/" + p
        if p:
            contract_paths.append(base + p)
    url_texts = [t for path, t in _walk_strings(workflow)
                 if path.endswith(".url.default") and t.startswith("http")]
    unused = [p for p in contract_paths if not any(u.rstrip("/").endswith(p.rstrip("/")) for u in url_texts)]
    if unused:
        # a contract may hold services the agent never calls (IVR-side only) —
        # report, do not fail
        warnings.append(f"contract paths no tool posts to: {unused}")

    # no template leaks in code payloads
    code_leaks = []
    for path, text in _walk_strings(workflow):
        if "pre_process_code" in path or "post_process_code" in path or "code_exec" in path or "code" == path.split(".")[-1]:
            if "{{" in text:
                code_leaks.append(path)
    if code_leaks:
        problems.append(f"code payloads contain '{{{{' leaks: {code_leaks[:5]}")

    # close corrector: a code hook that assigns outcome and reason deterministically
    correctors = []
    for path, text in _walk_strings(workflow):
        if "pre_process_code" in path or "post_process_code" in path:
            if re.search(r"outcome", text) and re.search(r"reason", text):
                correctors.append(path)
    for path, text in _walk_strings(workflow):
        if "code_exec" in path and re.search(r"outcome", text) and re.search(r"reason", text):
            correctors.append(path)
    if not correctors:
        problems.append("no deterministic close call outcome/reason corrector found")

    # mandatory sentences from the spec must appear somewhere
    try:
        spec_texts = []
        for typ in ("language_rule", "vocabulary_rule"):
            for rule in (spec.get("rule_ledger") or spec.get("rules") or []):
                if rule.get("type") == typ:
                    params = rule.get("params") or {}
                    for s in (params.get("mandatory_sentences") or []):
                        if isinstance(s, dict) and s.get("text"):
                            spec_texts.append(s["text"])
                    spec_texts += [x for x in (params.get("must_say") or []) if isinstance(x, str)]
        blob = "\n".join(t for _, t in _walk_strings(workflow))
        blob_flat = re.sub(r"\s+", " ", blob).lower()
        for sentence in spec_texts[:30]:
            # parentheticals are guidance, not speech; templates with fill-in
            # slots cannot appear verbatim in a generated workflow
            core = re.sub(r"\([^)]*\)", "", re.sub(r"\s+", " ", sentence)).strip()
            if len(core) < 8:
                continue
            if re.search(r"[\[\]…]|XXX|YYY|ZZZ|TTT|GGG|\{[^}]*\}", core):
                continue
            if core.lower() not in blob_flat:
                warnings.append(f"mandatory sentence not found verbatim: {core[:60]!r}")
    except Exception as e:
        warnings.append(f"mandatory sentence scan skipped: {e}")

    res[name] = {"status": "FAIL" if problems else "PASS",
                 "nodes": len(nodes),
                 "problems": problems,
                 "warnings": warnings[:10],
                 "english_leaks": en_leaks[:5],
                 "english_notes": en_notes[:5],
                 "bad_urls": bad_urls[:5]}
    try:
        (TESTS / "final-workflow-dryrun.json").write_text(
            json.dumps(workflow, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# check (c): mock generator dry-run + path coverage
# --------------------------------------------------------------------------- #

def write_tool_api(contract: dict) -> pathlib.Path:
    """OpenAPI-shaped tool API derived from final_contract.json.

    mock_gen's deterministic parser (`naive_analysis`) needs
    {"paths": {...}, "servers": [{"url": ...}]}; the bank's contract JSON is
    not OpenAPI, so every check (c) run regenerates this file from the current
    contract and feeds it to the dry-run. Path keys carry the base path so the
    endpoint paths in analysis.json/worker.js are the real /voice/v1/<service>.
    """
    base = str(contract.get("base_path", "") or "").rstrip("/")
    paths = {}
    for svc in contract.get("services", []) or []:
        p = str(svc.get("path", "") or "")
        if not p:
            continue
        if not p.startswith("/"):
            p = "/" + p
        props, required = {}, []
        for f in svc.get("request", []) or []:
            name = f.get("name")
            if not name:
                continue
            spec = {"type": f.get("type", "string")}
            if f.get("description"):
                spec["description"] = str(f["description"])[:300]
            props[name] = spec
            if f.get("required"):
                required.append(name)
        rprops = {}
        for f in svc.get("response", []) or []:
            name = f.get("name")
            if not name:
                continue
            spec = {"type": f.get("type", "string")}
            if f.get("description"):
                spec["description"] = str(f["description"])[:300]
            rprops[name] = spec
        responses = {"200": {
            "description": "success",
            "content": {"application/json": {"schema": {
                "type": "object", "properties": rprops}}}}}
        for err in svc.get("errors", []) or []:
            if not isinstance(err, dict):
                continue
            status = str(err.get("status") or 500)
            r = err.get("response") if isinstance(err.get("response"), dict) else {}
            desc = " - ".join(x for x in (str(r.get("code") or ""),
                                          str(err.get("when") or "")) if x) or "error"
            if status in responses:
                responses[status]["description"] += " | " + desc
            else:
                responses[status] = {"description": desc[:300]}
        paths[base + p] = {"post": {
            "summary": str(svc.get("description", ""))[:300],
            "operationId": str(svc.get("name", "")) or p.strip("/"),
            "requestBody": {"content": {"application/json": {"schema": {
                "type": "object", "properties": props, "required": required}}}},
            "responses": responses,
        }}
    doc = {
        "openapi": "3.0.0",
        "info": {"title": "freyabank-final-tool-api", "version": "1.0.0"},
        "servers": [{"url": (contract.get("servers") or ["https://api.freyabank.example"])[0]}],
        "paths": paths,
    }
    path = TESTS / "final_tool_api.json"
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def check_mock_dryrun(res: dict, full: bool = False) -> None:
    name = "c_mock_dryrun"
    if not CONTRACT_PATH.is_file():
        res[name] = {"status": "SKIP", "why": "final_contract.json not written yet"}
        return
    out = TESTS / "final-mock-dryrun"
    cust = None
    for source in CASE_SOURCES:
        for p in case_files(source):
            if p.name.lower().startswith("test-customers") and p.suffix.lower() == ".json":
                cust = p
                break
        if cust:
            break
    if cust is None and (ROOT / "mock" / "test-customers.json").is_file():
        cust = ROOT / "mock" / "test-customers.json"
    if cust is None:
        res[name] = {"status": "SKIP", "why": "no test customers yet"}
        return

    try:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        res[name] = {"status": "FAIL", "why": f"final_contract.json unreadable: {e}"}
        return
    tool_api = write_tool_api(contract)
    wanted = []
    base = str(contract.get("base_path", "") or "").rstrip("/")
    for svc in contract.get("services", []) or []:
        p = str(svc.get("path", "") or "")
        if p and not p.startswith("/"):
            p = "/" + p
        if p:
            wanted.append(base + p)

    cmd = [sys.executable, str(ROOT / "builder" / "mock_gen.py"),
           str(tool_api), str(cust), "--out", str(out)]
    if not full:
        cmd.append("--no-llm")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, cwd=str(ROOT))
    except subprocess.TimeoutExpired:
        res[name] = {"status": "FAIL", "why": "mock_gen timed out"}
        return
    tail = (r.stdout or "")[-2000:]
    worker = out / "worker.js"
    analysis = out / "analysis.json"
    rejected = out / "worker.rejected.js"

    # grep-verify every contract path: the no-llm dry-run stops after the
    # deterministic analysis (the worker step IS the model call), so the fresh
    # analysis.json is the evidence at that stage; when a worker.js exists
    # (full run), it must carry every path too.
    analysis_missing = []
    if analysis.is_file():
        hay = analysis.read_text(encoding="utf-8", errors="replace")
        analysis_missing = [p for p in wanted if p not in hay]
    else:
        analysis_missing = list(wanted)
    worker_missing = None
    if worker.is_file():
        hay = worker.read_text(encoding="utf-8", errors="replace")
        worker_missing = [p for p in wanted if p not in hay]

    problems, warnings = [], []
    # mock_gen's documented --no-llm stop is exit code 3 (analysis + seed
    # written; the worker step is the model call) — that is a clean dry-run.
    rc_ok = r.returncode == 0 or (not full and r.returncode == 3 and analysis.is_file())
    if not rc_ok:
        problems.append(f"mock_gen rc={r.returncode}")
    if analysis_missing:
        problems.append(f"paths missing from analysis.json: {analysis_missing}")
    if worker_missing:
        problems.append(f"paths missing from worker.js: {worker_missing}")
    if rejected.is_file() and not worker.is_file():
        warnings.append("a rejected worker.js attempt is on disk (validation failed earlier)")
    res[name] = {"status": "FAIL" if problems else "PASS",
                 "returncode": r.returncode,
                 "stage": ("worker.js" if worker.is_file()
                           else "analysis.json (--no-llm dry-run; the worker step is the model call)"),
                 "tool_api": str(tool_api),
                 "paths_checked": wanted,
                 "paths_missing": analysis_missing,
                 "worker_paths_missing": worker_missing,
                 "problems": problems,
                 "warnings": warnings,
                 "stdout_tail": tail[-800:],
                 "stderr_tail": (r.stderr or "")[-400:]}


# --------------------------------------------------------------------------- #
# check (d): example checks schema + static workflow scoring
# --------------------------------------------------------------------------- #

def check_examples(res: dict) -> None:
    name = "d_example_checks"
    if not EXAMPLES_PATH.is_file():
        res[name] = {"status": "SKIP", "why": "example_checks.json not written yet"}
        return
    try:
        obj = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        res[name] = {"status": "FAIL", "why": f"unreadable: {e}"}
        return
    examples = obj.get("examples")
    if not isinstance(examples, list) or len(examples) != 6:
        res[name] = {"status": "FAIL",
                     "why": f"expected 6 examples, found {len(examples) if isinstance(examples, list) else 'none'}"}
        return
    problems = []
    for ex in examples:
        for key in ("id", "customer_lines", "expected_agent_behaviour"):
            if not ex.get(key):
                problems.append(f"{ex.get('id', '?')}: missing {key}")
        if not ex.get("source_quotes"):
            problems.append(f"{ex.get('id', '?')}: no source_quotes (assertions must be document-derived)")
    res[name] = {"status": "FAIL" if problems else "PASS",
                 "examples": len(examples),
                 "kinds": [ex.get("kind", "?") for ex in examples],
                 "problems": problems}


def cmd_check(full_mock: bool = False, skip_mock: bool = False) -> dict:
    res: dict = {"checked_utc": now_utc()}
    check_contract_vs_customers(res)
    check_workflow_from_spec(res)
    if not skip_mock:
        check_mock_dryrun(res, full=full_mock)
    else:
        res["c_mock_dryrun"] = {"status": "SKIP", "why": "--skip-mock"}
    check_examples(res)
    (TESTS / "self_heal_last_check.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for k, v in res.items():
        if k == "checked_utc":
            continue
        log(f"{v.get('status', '?'):4}  {k}  {v.get('why', '') or ''}")
        for p in (v.get("problems") or [])[:6]:
            log(f"        - {p}")
    return res


# --------------------------------------------------------------------------- #
# score: the six examples as replayable checks against the built artefacts
# --------------------------------------------------------------------------- #

def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().lower()


_SERVICE_HINTS = (
    # most specific first; needles matched against the extracted description
    ("contact.email.get", ("email.get", "contact.email", "registered address", "kayıtlı adres")),
    ("statement.week.get", ("week.get", "current statement week", "current week")),
    ("statement.week.decide", ("week.decide", "preview")),
    ("statement.week.change", ("week.change", "statement week change", "change the statement week")),
    ("statement.pdf.send", ("pdf.send", "statement email send", "email send", "send the statement")),
    ("cards.list", ("cards.list", "card list", "cards list", "customer data", "list of cards")),
    ("cards.balance", ("cards.balance", "balance", "debt", "statement")),
)


def cmd_score() -> dict:
    """Static scoring of example_checks.json against the dry-run workflow/mock.

    A full replay needs the live platform (never called from here), so this
    scores everything checkable offline: every expected service exists in the
    workflow's tool URLs and in the generated worker; every quoted expected
    sentence appears in the workflow's prompt texts; forbidden phrases do not.
    """
    out: dict = {"scored_utc": now_utc(), "examples": []}
    try:
        checks = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        out["error"] = f"example_checks.json unreadable: {e}"
        log(json.dumps(out, ensure_ascii=False, indent=1))
        return out

    wf_path = TESTS / "final-workflow-dryrun.json"
    wf_text, wf_urls, services_in_wf = "", [], set()
    if wf_path.is_file():
        wf_text = wf_path.read_text(encoding="utf-8", errors="replace")
        try:
            wf = json.loads(wf_text)
            for path, text in _walk_strings(wf):
                if path.endswith(".url.default") and text.startswith("http"):
                    wf_urls.append(text)
        except Exception:
            pass
    worker_text = ""
    for cand in (TESTS / "final-mock-dryrun" / "worker.js", ROOT / "mock" / "final" / "worker.js"):
        if cand.is_file():
            worker_text = cand.read_text(encoding="utf-8", errors="replace")

    for ex in checks.get("examples", []):
        r = {"id": ex.get("id"), "kind": ex.get("kind"), "pass": 0, "fail": 0, "notes": []}
        for tc in ex.get("expected_tool_calls", []):
            svc = str(tc.get("service", ""))
            if not svc:
                continue
            # the extracted service field is a document-style description; map
            # it onto the contract's real service names before grepping
            mapped = None
            low = svc.lower()
            for known, needles in _SERVICE_HINTS:
                if any(nd in low for nd in needles):
                    mapped = known
                    break
            if mapped is None:
                r["notes"].append(f"no static mapping for service: {svc[:70]}")
                continue
            hit = any(mapped.lower() in u.lower() for u in wf_urls)
            if not hit and worker_text:
                hit = mapped.lower() in worker_text.lower()
            if hit:
                r["pass"] += 1
            else:
                r["fail"] += 1
                r["notes"].append(f"service {mapped} not found in workflow/worker (for: {svc[:50]})")
        for beh in ex.get("expected_agent_behaviour", []):
            b = _normalize(beh)
            quoted = re.findall(r'"([^"]{8,})"', str(beh)) or re.findall(r"'([^']{8,})'", str(beh))
            for q in quoted:
                if not re.search(r"[çğıöşüÇĞİÖŞÜ]", q) and _turksh_score(q)[1] == 0:
                    # the examples document is English; only Turkish quotes can
                    # be matched against the Turkish workflow
                    r["notes"].append(f"english quote not statically checkable: {q[:60]}")
                    continue
                qn = _normalize(q)
                if wf_text and qn in _normalize(wf_text):
                    r["pass"] += 1
                elif wf_text:
                    r["fail"] += 1
                    r["notes"].append(f"quoted expectation absent from workflow: {q[:60]}")
            if not quoted and wf_text:
                r["notes"].append(f"behaviour not statically checkable: {beh[:60]}")
        r["status"] = "PASS" if r["fail"] == 0 and r["pass"] else ("FAIL" if r["fail"] else "UNCHECKED")
        out["examples"].append(r)
    out["totals"] = {
        "examples": len(out["examples"]),
        "pass": sum(e["pass"] for e in out["examples"]),
        "fail": sum(e["fail"] for e in out["examples"]),
    }
    (TESTS / "self_heal_score.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    log(json.dumps(out.get("totals"), ensure_ascii=False))
    for e in out["examples"]:
        log(f"  {e['status']:9} {e['id']} pass={e['pass']} fail={e['fail']} {e['notes'][:2]}")
    return out


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #

def append_report(lines: list[str]) -> None:
    with REPORT_PATH.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="final-case self-healing harness")
    ap.add_argument("cmd", choices=["scan", "extract", "check", "all", "mockfull", "score"])
    ap.add_argument("--only", default="all", choices=["all", "contract", "spec", "examples"])
    ap.add_argument("--full-mock", action="store_true",
                    help="run the mock generator without --no-llm (generates worker.js)")
    ap.add_argument("--skip-mock", action="store_true")
    a = ap.parse_args()
    if a.cmd == "scan":
        cmd_scan()
    elif a.cmd == "extract":
        cmd_extract(a.only)
    elif a.cmd == "check":
        cmd_check(full_mock=a.full_mock, skip_mock=a.skip_mock)
    elif a.cmd == "score":
        cmd_score()
    elif a.cmd == "mockfull":
        res: dict = {"checked_utc": now_utc()}
        check_mock_dryrun(res, full=True)
        log(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        cmd_scan()
        if CONTRACT_PATH.is_file() or SPEC_PATH.is_file():
            cmd_check(full_mock=a.full_mock, skip_mock=a.skip_mock)
        else:
            log("all: no artefacts yet; run extract first")
    return 0


if __name__ == "__main__":
    sys.exit(main())
