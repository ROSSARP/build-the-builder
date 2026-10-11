#!/usr/bin/env python3
"""Local test harness for the Freya brief workflows: run ONE case against ONE workflow,
without the Freya platform.

    python3 tests/local_sim.py <case_id|all> [workflow.json] [--no-judge] [--max-exchanges N]

The mock bank is real and always reachable; the agent and the customer are `claude` CLI
calls; the ledger scoring is the exact one from tools/score.py.

------------------------------------------------------------------------------
README - how it works, and what it does not promise
------------------------------------------------------------------------------
What is faithful
  * The bank. Sessions, tool calls, the ledger: all against the mock, the same
    endpoints run_cases.py/score.py use. `score_ledger` is imported, not copied,
    so the PASS/FAIL on the ledger is the platform's own verdict.
  * The workflow engine, approximately: node entry (on_enter tts/llm/silent,
    first-entry-only), pre_actions for api_request/code nodes with `{{var}}`
    substitution and pre/post_process_code hooks, exec of code-node snippets with
    the `vars` dict, `{{var}}` substitution in prompts and tool parameters,
    tool baking (a `{{var}}` default with a value is baked and hidden from the
    model; without a value the model fills it), transition evaluation after each
    user message AND after each tool result, in list order, deterministic
    operators implemented in Python, the `<tool>_args.*` / `<tool>_response.*` /
    `<tool>_status_code` / `<tool>_success_count` variable flattening, extraction
    after each user message with min_confidence/enum/validation_pattern checks,
    and the end_of_call `close_call` lifecycle tool with its pre_process_code.

What is approximate
  * The dialogue, extraction and intent models are `claude` CLI calls (default
    claude-sonnet-5-5), not the platform's models - wording and tool-calling
    habits differ.
  * matches_intent is judged by one small LLM call; confidence is self-reported
    instead of read from token probabilities; the customer is an LLM playing the
    case script, so it improvises.
  * So: trust the ledger verdict, treat the local judge (conversation checks) as
    a hint. A local PASS is good evidence; a local FAIL may be a harness artifact.

Usage
    python3 tests/local_sim.py PUB-01                       # one case
    python3 tests/local_sim.py all                          # every id in the case file
    python3 tests/local_sim.py PUB-08 other.workflow.json   # another workflow
    python3 tests/local_sim.py all --no-judge --max-exchanges 30

Needs FREYA_BANK_TEAM_KEY (the same team key score.py uses) in the environment.
Standard library + subprocess only.
"""
import argparse, json, os, pathlib, re, subprocess, sys, time, traceback
import datetime as _dt
import urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from score import http as bank_http, score_ledger  # noqa: E402  (the scorer is the platform's)

UA = "Mozilla/5.0 (local-sim)"
LLM_MODEL = os.environ.get("LOCAL_SIM_MODEL", "claude-sonnet-5-5")
LLM_TIMEOUT = 120                 # seconds per LLM call
MAX_EXCHANGES = 40                # agent+customer exchanges before the run is cut off
MAX_TOOL_STEPS = 5                # tool calls inside one agent turn
MAX_HOPS = 200                    # node entries before the run is cut off
MISSING = object()
EXTRACTION_CONF_CAP = 0.6         # see keep_extracted()

TRACE = []                        # every printed line, for the final dump


def log(msg=""):
    print(msg, flush=True)
    TRACE.append(str(msg))


# ---------------------------------------------------------------- LLM (claude CLI)

def llm(prompt, purpose, timeout=LLM_TIMEOUT):
    """One model call through the claude CLI, like builder/build.py llm()."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL")
           and not k.startswith(("CLAUDE_MODEL", "ANTHROPIC_DEFAULT_"))}
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--model", LLM_MODEL]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    if r.returncode != 0 or "unrecognized_model" in (r.stderr or ""):
        r = subprocess.run(["claude", "-p", prompt, "--output-format", "json"],
                           capture_output=True, text=True, timeout=timeout, env=env)
    out = r.stdout.strip()
    try:
        result = json.loads(out).get("result", "")
    except Exception:
        result = out
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    result = json.loads(line).get("result", "")
                    break
                except Exception:
                    pass
    if r.returncode != 0 and not str(result).strip():
        raise RuntimeError(f"model call failed ({purpose}): {(r.stderr or '')[:300]}")
    log(f"    . llm {purpose}: {time.time() - t0:.0f}s, {len(str(result))} chars")
    return str(result)


def extract_json(text):
    """The JSON object inside an LLM answer, fences and chatter stripped."""
    t = str(text).strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    start, end = t.find("{"), t.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in the model answer")
    return json.loads(t[start:end + 1])


# ---------------------------------------------------------------- the bank

TEAM_KEY = os.environ.get("FREYA_BANK_TEAM_KEY", "")


def bank(path, body=None, tries=4):
    """score.http with retries (the mock occasionally answers a non-JSON error) and a
    friendlier failure mode (score.py raises KeyError without the team key)."""
    last = None
    for attempt in range(tries):
        try:
            return bank_http(path, body)
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read()[:200].decode("utf-8", "replace")
            except Exception:
                pass
            raise RuntimeError(f"bank call {path} failed: HTTP {e.code} {detail}"
                               + ("  (check FREYA_BANK_TEAM_KEY)" if e.code in (401, 403) else "")) from None
        except Exception as e:
            last = e
            if attempt + 1 < tries:
                log(f"    . bank {path} hiccup ({e}); retrying")
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"bank call {path} failed after {tries} tries: {last}") from None


def bank_call(url, method, body, headers):
    """Raw call to a full URL (the tool urls point straight at the mock)."""
    data = json.dumps(body).encode() if body is not None else None
    h = {"user-agent": UA, "content-type": "application/json", "x-team-key": TEAM_KEY}
    h.update({str(k): str(v) for k, v in (headers or {}).items()})
    for attempt in range(3):
        req = urllib.request.Request(url, data=data, headers=h, method=str(method or "POST").upper())
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                raw, code, hdr = r.read(), r.status, dict(r.headers)
            break
        except urllib.error.HTTPError as e:
            raw, code, hdr = e.read(), e.code, dict(e.headers)
            break
        except Exception as e:                    # connection flake: retry like connect_retries
            if attempt == 2:
                return None, None, {"error": str(e)}
            time.sleep(1 + attempt)
    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = raw.decode("utf-8", "replace")
    return code, parsed, hdr


def flatten(prefix, obj, out):
    """The engine's dotted variable table: <tool>_response.data.a.b, list indices as numbers."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten(f"{prefix}.{k}" if prefix else str(k), v, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            flatten(f"{prefix}.{i}", v, out)
    else:
        if obj is None:
            out[prefix] = None
        elif isinstance(obj, bool):
            out[prefix] = "true" if obj else "false"   # booleans arrive as strings
        else:
            out[prefix] = str(obj)


# ---------------------------------------------------------------- workflow helpers

def subst(text, variables):
    """{{var}} and {{var:json}} substitution. An unresolved placeholder stays literal."""
    if not isinstance(text, str) or "{{" not in text:
        return text

    def rep(m):
        name, mode = m.group(1).strip(), (m.group(2) or "").strip().lower()
        val = variables.get(name, MISSING)
        if val is MISSING:
            return m.group(0)
        if mode == "json":
            return json.dumps(val)
        return "" if val is None else str(val)

    return re.sub(r"\{\{\s*([\w.$-]+)\s*(?::\s*([a-zA-Z]+))?\s*\}\}", rep, text)


def strval(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def eval_cond(cond, variables):
    """True / False / None. None = a matches_intent judgement that needs the routing model."""
    if not isinstance(cond, dict):
        return False
    if cond.get("operator") is None and "conditions" in cond:
        logic = str(cond.get("logic") or "or").lower()
        return _combine([eval_cond(c, variables) for c in cond.get("conditions") or []], logic)
    op = str(cond.get("operator") or "always")
    var = cond.get("variable")
    operand = cond.get("operand")
    if op == "always":
        return True
    if op == "matches_intent":
        return None
    value = variables.get(var, MISSING) if var is not None else MISSING
    if op == "is_set":
        return value is not MISSING and value is not None and strval(value) != ""
    if op == "is_not_set":
        return value is MISSING or value is None or strval(value) == ""
    if op in ("equals", "not_equals"):     # string compare: tests both "true" and "True"
        eq = strval(value) == strval(operand)
        return eq if op == "equals" else not eq
    if op in ("greater_than", "less_than"):
        try:
            a, b = float(value), float(operand)
        except (TypeError, ValueError):
            return False
        return a > b if op == "greater_than" else a < b
    if op == "contains":
        try:
            return strval(operand).lower() in strval(value).lower()
        except Exception:
            return False
    return False


def _combine(vals, logic):
    if logic == "and":
        if any(v is False for v in vals):
            return False
        if any(v is None for v in vals):
            return None
        return True
    if any(v is True for v in vals):
        return True
    if any(v is None for v in vals):
        return None
    return False


def route(node, variables, ctx, node_key):
    """First matching transition, in list order. Deterministic conditions first, then one
    routing-model call for the matches_intent conditions (doc: workflow-format.md)."""
    deferred = []
    for tr in node.get("transitions") or []:
        if tr.get("is_tool_call"):
            continue                      # offered to the dialogue model as a tool instead
        r = eval_cond(tr.get("condition") or {"operator": "always"}, variables)
        if r is True:
            return tr
        if r is None:
            deferred.append(tr)
    if deferred and not ctx.get("no_intent"):
        verdicts = judge_intents([t.get("condition") for t in deferred], ctx)
        for tr, ok in zip(deferred, verdicts):
            if ok:
                return tr
    return None


def judge_intents(conditions, ctx):
    """One model call judging every matches_intent of the evaluation (doc: one call)."""
    items = []
    for i, c in enumerate(conditions):
        items.append({"n": i,
                      "description": c.get("description") or "",
                      "condition": json.dumps(c)})
    prompt = ("You are the router of a phone agent. Judge the customer's LAST message against "
              "each condition. Reply with STRICT JSON only: {\"matches\": [true, false, ...]} "
              "with one entry per condition, in order.\n\n"
              "CONVERSATION:\n" + render_history(ctx["history"]) + "\n\nCONDITIONS:\n" +
              json.dumps(items, indent=1))
    try:
        data = extract_json(llm(prompt, "route matches_intent", timeout=LLM_TIMEOUT))
        m = data.get("matches") if isinstance(data, dict) else None
        if isinstance(m, list) and len(m) == len(conditions):
            return [bool(x) if not isinstance(x, str) else x.strip().lower() in ("true", "yes", "1")
                    for x in m]
    except Exception as e:
        log(f"    ! intent judgement failed ({e}); treating as no match")
    return [False] * len(conditions)


# ---------------------------------------------------------------- tool baking / calling

def _placeholder_var(text):
    m = re.fullmatch(r"\s*\{\{\s*([\w.$-]+)\s*\}\}\s*", str(text))
    return m.group(1) if m else None


def bake_api_tool(tool, variables):
    """Resolve the tool's `default`s against the variable table (doc: baking at node entry).
    Baked fields are hidden from the model; unresolved `{{var}}`/missing defaults stay visible."""
    fn = tool.get("function") or {}
    props = ((fn.get("parameters") or {}).get("properties") or {})
    base = {"url": "", "method": "POST", "headers": {}, "body": {}}
    visible = []
    for key in ("url", "method"):
        spec = props.get(key)
        if isinstance(spec, dict) and "default" in spec:
            base[key] = subst(str(spec["default"]), variables)
    hspec = props.get("headers")
    if isinstance(hspec, dict):
        for hk, hs in (hspec.get("properties") or {}).items():
            if isinstance(hs, dict) and "default" in hs:
                base["headers"][hk] = subst(str(hs["default"]), variables)
    bspec = props.get("body")
    body_props = (bspec or {}).get("properties") or {}
    for field, fs in body_props.items():
        if not isinstance(fs, dict):
            continue
        if "default" not in fs:
            visible.append({"param": field, "field": field, "spec": fs})
            continue
        raw = fs["default"]
        var = _placeholder_var(raw) if isinstance(raw, str) else None
        if var:
            val = variables.get(var, MISSING)
            if val is MISSING or val is None or strval(val) == "":
                visible.append({"param": var, "field": field, "spec": fs})   # model fills it
            else:
                base["body"][field] = val                                    # baked
        else:
            base["body"][field] = subst(raw, variables)
    if not body_props:
        for k, fs in props.items():
            if k in ("url", "method", "headers", "body") or not isinstance(fs, dict):
                continue
            if "default" not in fs:
                visible.append({"param": k, "field": k, "spec": fs})
    return base, visible


def visible_schema(name, tool, visible, description):
    props, required = {}, []
    for v in visible:
        spec = dict(v["spec"])
        spec.pop("default", None)
        props[v["param"]] = spec
        if v["field"] in ((tool.get("function", {}).get("parameters") or {}).get("body") or {}).get("required", []):
            required.append(v["param"])
    schema = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return {"name": name, "description": description or "", "parameters": schema}


def execute_tool(tool, name, base, visible, args, variables):
    """One api_call: pre_process_code, the HTTP call, post_process_code, response_mapping,
    then the engine's automatic variable flattening and counters. Returns (envelope, ok)."""
    body = dict(base.get("body") or {})
    for k, v in (args or {}).items():
        field = next((vis["field"] for vis in visible if vis["param"] == k), k)
        body[field] = v
    config = {"url": base["url"], "method": base["method"],
              "headers": dict(base["headers"]), "body": body}
    pre = tool.get("pre_process_code") or ""
    if pre.strip():
        try:
            exec(pre, {"vars": variables, "config": config, "__builtins__": __builtins__})
        except Exception as e:
            log(f"    ! pre_process_code of {name} raised: {e}")
    # a field that is exactly one unresolved placeholder is dropped from the request
    config["body"] = {k: v for k, v in (config.get("body") or {}).items()
                      if not (isinstance(v, str) and _placeholder_var(v))}
    code, parsed, _hdr = bank_call(config.get("url"), config.get("method"),
                                   config.get("body"), config.get("headers"))
    ok = isinstance(code, int) and 200 <= code < 300
    result = {"status": "success" if ok else "error",
              "data": parsed,
              "message": "Successfully executed POST request" if ok else f"Request failed ({code})",
              "status_code": code}
    post = tool.get("post_process_code") or ""
    if post.strip():
        try:
            exec(post, {"vars": variables, "config": config, "result": result,
                        "__builtins__": __builtins__})
        except Exception as e:
            log(f"    ! post_process_code of {name} raised: {e}")
    for m in tool.get("response_mapping") or []:
        val = path_get(result, m.get("path"))
        if val is not MISSING and m.get("variable"):
            variables[m["variable"]] = val
    for k, v in (args or {}).items():
        variables[f"{name}_args.{k}"] = v
    variables[f"{name}_status_code"] = code
    flat = {}
    flatten(f"{name}_response", result, flat)
    variables.update(flat)
    n = int(str(variables.get(f"{name}_success_count") or 0)) + (1 if ok else 0)
    variables[f"{name}_success_count"] = n
    variables[f"{name}_failure_count"] = int(str(variables.get(f"{name}_failure_count") or 0)) + (0 if ok else 1)
    return result, ok


def path_get(obj, path):
    if not path:
        return MISSING
    cur = obj
    for part in str(path).split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return MISSING
    return cur


# ---------------------------------------------------------------- node entry

def code_sources(node):
    out = []
    for a in node.get("pre_actions") or []:
        fn = a.get("function") or {}
        if fn.get("handler") == "__function__:code_exec":
            props = ((fn.get("parameters") or {}).get("properties") or {})
            code = (props.get("code") or {}).get("default")
            if code:
                out.append(code)
    return out


def run_code(node_key, code, variables):
    ns = {"vars": variables, "__builtins__": __builtins__}
    ok = True
    try:
        exec(code, ns)
    except Exception as e:
        ok = False
        log(f"    ! code node {node_key} raised: {e}")
    result = {"status": "success" if ok else "error", "data": None,
              "message": "Code executed successfully" if ok else "Code failed",
              "status_code": 200 if ok else 500}
    variables[f"{node_key}_status_code"] = result["status_code"]
    variables[f"{node_key}_success_count"] = (int(str(variables.get(f"{node_key}_success_count") or 0))
                                              + (1 if ok else 0))
    variables[f"{node_key}_failure_count"] = (int(str(variables.get(f"{node_key}_failure_count") or 0))
                                              + (0 if ok else 1))
    return result


def run_pre_actions(node, node_key, variables):
    """api_request node pre_actions + its node-level response_mapping."""
    results = []
    for a in node.get("pre_actions") or []:
        fn = a.get("function") or {}
        name = fn.get("name") or node_key
        if fn.get("handler") == "__function__:code_exec":
            for code in code_sources(node):
                results.append((name, run_code(node_key, code, variables)))
            break
        base, _ = bake_api_tool(a, variables)
        code, parsed, _ = bank_call(base["url"], base["method"], base["body"], base["headers"])
        ok = isinstance(code, int) and 200 <= code < 300
        result = {"status": "success" if ok else "error", "data": parsed,
                  "message": "Successfully executed POST request" if ok else f"Request failed ({code})",
                  "status_code": code}
        post = a.get("post_process_code") or ""
        if post.strip():
            try:
                exec(post, {"vars": variables, "config": base, "result": result,
                            "__builtins__": __builtins__})
            except Exception as e:
                log(f"    ! post_process_code of {name} raised: {e}")
        log(f"[tool] {name} {json.dumps(base.get('body') or {})} -> {json.dumps(result.get('data'))[:220]}")
        for m in node.get("response_mapping") or []:
            val = path_get(result, m.get("path"))
            if val is not MISSING and m.get("variable"):
                variables[m["variable"]] = val
        # engine keys: pre_actions nodes are named after the node, not the tool
        variables[f"{node_key}_status_code"] = code
        variables[f"{node_key}_success_count"] = (int(str(variables.get(f"{node_key}_success_count") or 0))
                                                  + (1 if ok else 0))
        variables[f"{node_key}_failure_count"] = (int(str(variables.get(f"{node_key}_failure_count") or 0))
                                                  + (0 if ok else 1))
        flat = {}
        flatten(f"{name}_response", result, flat)
        variables.update(flat)
        results.append((name, result))
    return results


def entry(node, node_key, variables, visited):
    """on_enter behaviour. Returns a line the agent speaks (or None)."""
    on_enter = node.get("on_enter") or {}
    kind = on_enter.get("type") or "llm"
    first_only = bool(node.get("on_enter_first_entry_only"))
    if first_only and visited.get(node_key):
        return None
    visited[node_key] = visited.get(node_key, 0) + 1
    if kind == "tts":
        text = subst(str(on_enter.get("text") or ""), variables)
        if text.strip():
            log(f"[agent] {text}")
        return text or None
    if kind == "audio":
        return None
    if kind == "silent":
        return None
    return "LLM_ENTRY"      # the caller makes a dialogue turn from task_message
    # (on_enter.prompt would override the entry instruction; rarely used)


# ---------------------------------------------------------------- prompts

STAGE = {
    "opening": "This is the first turn of the node: write the opening line for the Current Task. "
               "Do not call a tool in this turn unless the task says to.",
    "reply": "Answer the customer's last line and follow the Current Task.",
    "after_tool": "A tool result is above. Read it and follow the Current Task: speak to the "
                  "customer now, or call the next tool if the task still requires one. Never "
                  "end the turn with nothing.",
}


def render_history(messages):
    if not messages:
        return "(nothing yet)"
    out = []
    for m in messages:
        r, text = m.get("role"), m.get("text") or ""
        if r == "agent":
            out.append(f"AGENT: {text}")
        elif r == "customer":
            out.append(f"CUSTOMER: {text}")
        elif r == "tool_call":
            out.append(f"[tool call] {text}")
        elif r == "tool_result":
            out.append(f"[tool result] {text}")
    return "\n".join(out)


def agent_prompt(node, variables, system_prompt, tools_shown, messages, stage):
    parts = [subst(str(system_prompt or ""), variables)]
    role = subst(str(node.get("role_message") or ""), variables)
    if role.strip():
        parts.append(role)
    parts.append("## Current Task\n" + subst(str(node.get("task_message") or ""), variables))
    if tools_shown:
        parts.append("## Tools you may call (at most one per turn)\n" +
                     "\n".join(json.dumps(t, ensure_ascii=False) for t in tools_shown))
    else:
        parts.append("## Tools\nNo tool call is allowed in this turn.")
    parts.append("## Conversation so far\n" + render_history(messages))
    parts.append("## Your turn\n" + STAGE.get(stage, STAGE["reply"]))
    parts.append('Reply with STRICT JSON only, no markdown and no code fences:\n'
                 '{"speak": "<the words you say on the phone, one or two short sentences>", '
                 '"tool": "<tool name or null>", "args": {<arguments, or {}>}}\n'
                 'Put the tool name in "tool" (null when you do not call one); put its arguments '
                 'in "args". Speak after every tool result. Ground every number, date and product '
                 'name in the tool results.')
    return "\n\n".join(parts)


def agent_turn(node, node_key, variables, system_prompt, tools, messages, stage, ctx):
    """One dialogue-model turn, including tool calls and routing on their results.
    `tools` is the node-entry bake: (name, tool object, baked base config, visible params).
    Returns the target node key when a tool result triggers a transition, else None."""
    tools_shown = [visible_schema(name, t, visible, (t.get("function") or {}).get("description"))
                   for name, t, _base, visible in tools]
    for _ in range(MAX_TOOL_STEPS):
        prompt = agent_prompt(node, variables, system_prompt, tools_shown, messages, stage)
        try:
            data = extract_json(llm(prompt, f"agent/{node_key}/{stage}"))
        except Exception as e:
            log(f"    ! agent answer unreadable ({e}); stopping the turn")
            return None
        speak = str(data.get("speak") or "").strip()
        tool = data.get("tool")
        tool = None if tool in (None, "", "null", "none", "None") else str(tool)
        if speak:
            messages.append({"role": "agent", "text": speak})
            log(f"[agent] {speak}")
        if not tool:
            return None
        match = next(((n, t, b, v) for n, t, b, v in tools if n == tool), None)
        if match is None:
            result = {"status": "error", "data": {"error": f"The function `{tool}` is not currently available."}}
            messages.append({"role": "tool_call", "text": f"{tool}({json.dumps(data.get('args') or {})})"})
            messages.append({"role": "tool_result", "text": json.dumps(result)})
            log(f"[tool] {tool} -> not available")
            continue
        name, tool_obj, base, visible = match
        if (tool_obj.get("function") or {}).get("handler") == "__function__:end_call":
            log(f"[tool] {name} -> call ended")
            ctx["ended"] = True
            return None
        args = data.get("args") if isinstance(data.get("args"), dict) else {}
        messages.append({"role": "tool_call", "text": f"{name}({json.dumps(args)})"})
        result, _ok = execute_tool(tool_obj, name, base, visible, args, variables)
        shown = result
        if node.get("suppress_tool_results"):
            shown = {"status": result.get("status")}
        messages.append({"role": "tool_result", "text": json.dumps(shown, default=str)})
        log(f"[tool] {name} {json.dumps(args)} -> {json.dumps(result.get('data'))[:220]}")
        # routing runs again after a tool result (doc: tools-and-code.md)
        tr = route(node, variables, ctx, node_key)
        if tr and tr.get("target_node") != node_key:
            log(f"[route] {node_key} -> {tr['target_node']}  ({tr.get('description') or ''})")
            return tr["target_node"]
    return None


# ---------------------------------------------------------------- extraction

TYPES_DOC = ("Types: string, integer, float, boolean, date (ISO YYYY-MM-DD), datetime, "
             "name, phone_number. Dates are relative to the current call date, which is "
             "{{now}}.")


def extraction_prompt(node, variables, messages):
    schema = node.get("extraction_schema") or []
    if not schema:
        return None
    lines = []
    for v in schema:
        s = f"- {v.get('name')} ({v.get('type') or 'string'})"
        if v.get("description"):
            s += ": " + str(v["description"])
        if v.get("enum_values"):
            s += f" Allowed values: {v['enum_values']}."
        lines.append(s)
    listing = "\n".join(lines)
    custom = next((v.get("extraction_prompt") for v in schema if v.get("extraction_prompt")), None)
    last = next((m["text"] for m in reversed(messages) if m.get("role") == "customer"), "")
    if custom:
        body = (str(custom)
                .replace("{{extractor.speech}}", last)
                .replace("{{extractor.conversation.last-10}}",
                         "\n".join(render_history(messages).splitlines()[-10:]))
                .replace("{{extractor.variables_list}}", listing)
                .replace("{{extractor.type_preamble}}", TYPES_DOC))
        body = subst(body, variables)
    else:
        body = ("Read the conversation and the customer's last message, then fill these variables:\n"
                + listing + "\n\n" + subst(TYPES_DOC, variables) + "\n\nCONVERSATION:\n"
                + render_history(messages))
    return (body + "\n\nReply with STRICT JSON only: one key per variable, "
            '{"<name>": {"value": <value or null>, "confidence": <0.0-1.0>}}. '
            "Use null for a variable the customer did not give. A date value must be ISO "
            "YYYY-MM-DD. Do not take a value that only the assistant said.")


def keep_extracted(v, value, confidence):
    """min_confidence check. The platform reads confidence from token probabilities; a model
    self-report is coarser, so a declared threshold is capped at EXTRACTION_CONF_CAP."""
    thr = float(v.get("min_confidence") or 0.95)
    thr = min(thr, EXTRACTION_CONF_CAP)
    if confidence is not None and float(confidence) < thr:
        return None
    if v.get("enum_values") and strval(value) not in [strval(x) for x in v["enum_values"]]:
        return None
    pat = v.get("validation_pattern")
    if pat and not re.fullmatch(str(pat), strval(value)):
        return None
    if (v.get("type") in ("date", "datetime")) and isinstance(value, str):
        iso = normalize_date(value)
        if iso is None:
            return None
        return iso
    if v.get("type") == "boolean" and isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    return value


def normalize_date(text):
    t = str(text).strip()[:10]
    try:
        _dt.date.fromisoformat(t)
        return t
    except Exception:
        pass
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d %B %Y", "%d %b %Y", "%B %d %Y", "%B %d, %Y",
                "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return _dt.datetime.strptime(str(text).strip(), fmt).date().isoformat()
        except Exception:
            continue
    return None


def run_extraction(node, variables, messages):
    prompt = extraction_prompt(node, variables, messages)
    if not prompt:
        return
    try:
        data = extract_json(llm(prompt, "extract"))
    except Exception as e:
        log(f"    ! extraction unreadable ({e})")
        return
    schema = {v["name"]: v for v in (node.get("extraction_schema") or [])}
    for name, raw in (data or {}).items():
        if name not in schema:
            continue
        v = schema[name]
        if isinstance(raw, dict):
            value, conf = raw.get("value"), raw.get("confidence")
        else:
            value, conf = raw, None
        if value in (None, "", "null"):
            continue
        kept = keep_extracted(v, value, conf)
        if kept is None:
            log(f"[extract] {name}: dropped ({value!r}, conf {conf})")
            continue
        variables[name] = kept
        log(f"[extract] {name} = {kept!r}")


# ---------------------------------------------------------------- the customer

PERSONA = """OUTPUT RULE: Write only the words you say on the phone. No stage directions, no brackets. One or two short sentences per turn, then wait for the other side.

WHO YOU ARE: {who}

WHAT HAPPENS IN THIS CALL: {script}

RULES:
- Answer what you are asked. Do not volunteer information nobody asked for.
- When you give a number or a date, say all of it in one turn. Never stop halfway through.
- Do not invent dates, amounts or facts that are not written above. If asked something that is not covered, give a short neutral answer.
- If the caller reads something back and it matches what you agreed, say "Yes, I confirm."
- When the caller says goodbye, say "Thank you, goodbye." and say nothing more."""


def persona_text(case):
    v, i = case["variables"], case["identity"]
    me = f"{v['first_name']} {v['last_name']}"
    if case.get("family") == "Third party" or case.get("third_party"):
        who = (f"You are NOT {me}. You answered this phone. You do not know {me}'s security "
               "answers and you would not give them. The text below says who you are.")
    else:
        say = {"date_of_birth": "Your date of birth is {} (say it in words, like '14 March 1988').",
               "phone_last4": "The last four digits of your phone number on file are {}.",
               "postcode": "The postcode of your registered address is {}.",
               "birth_year": "Your year of birth is {}.",
               "company_number": "Your company number is {}.",
               "founded_year": "The company was founded in {}."}
        who = (f"You are {me}. " + " ".join(
            say.get(k, "Your " + k.replace("_", " ") + " is {}.").format(x) for k, x in i.items())
            + " Give these only when asked, and give the wrong ones where the text below says so.")
    text = PERSONA.format(who=who, script=case["script"])
    if case.get("style"):
        text += "\n\nSTYLE: the case notes a speaking style; keep it natural."
    return text


def customer_turn(case, variables, messages, ctx):
    today = str(variables.get("now") or "")[:10] or "today"
    weekday = ""
    iso = normalize_date(today)
    if iso:
        weekday = _dt.date.fromisoformat(iso).strftime("%A")
    prompt = (persona_text(case)
              + f"\n\nThe call is happening on {today}" + (f" ({weekday})" if weekday else "")
              + ". 'Today' and 'tomorrow' in the text above mean relative to that date.\n\n"
              + "CONVERSATION SO FAR:\n" + render_history(messages)
              + "\n\nThe caller just finished their turn. Write your next line. "
                "Output ONLY the words you speak.")
    try:
        line = llm(prompt, "customer").strip()
    except Exception as e:
        log(f"    ! customer model failed ({e}); the customer hangs up")
        ctx["ended"] = True
        return None
    line = " ".join(line.split())
    if line.startswith('"') and line.endswith('"') and len(line) > 1:
        line = line[1:-1]
    log(f"[customer] {line}")
    return line


# ---------------------------------------------------------------- end of call

OUTCOMES = {
    "promise": [], "paid": [],
    "transferred": ["restructuring", "human", "support"],
    "no_promise": ["refused", "hardship", "dispute", "service_error"],
    "not_verified": ["failed", "declined"],
    "not_reached": ["callback", "no_callback", "wrong_number", "deceased", "unclear"],
}
END_RE = re.compile(r"(have a good day|goodbye|good bye)", re.I)


def closing_decision(system_prompt, variables, messages, ledger_calls):
    table = "\n".join(f"- {o}: reason one of {r}" if r else f"- {o}: no reason" for o, r in OUTCOMES.items())
    tools_made = "\n".join(f"- {c['tool']} {json.dumps(c.get('args') or {})} -> {json.dumps(c.get('result'))[:120]}"
                           for c in ledger_calls) or "(none)"
    prompt = (subst(str(system_prompt or ""), variables)
              + "\n\nDecide how this call ended, from the transcript and the tool calls made.\n"
              + table
              + "\n\nTOOL CALLS MADE (in order):\n" + tools_made
              + "\n\nTRANSCRIPT:\n" + render_history(messages)
              + '\n\nReply with STRICT JSON only: {"outcome": "<one outcome>", "reason": "<reason or null>"}. '
                "Use null for the reason when the outcome takes none.")
    try:
        data = extract_json(llm(prompt, "close_call decision"))
    except Exception as e:
        log(f"    ! closing decision unreadable ({e}); using the fallback")
        data = {}
    outcome = str(data.get("outcome") or "").strip()
    reason = data.get("reason")
    reason = str(reason).strip() if reason not in (None, "", "null", "None") else None
    if outcome not in OUTCOMES or (OUTCOMES[outcome] and reason not in OUTCOMES[outcome]):
        outcome, reason = fallback_outcome(ledger_calls)
        log(f"    ! closing decision unusable; fallback {outcome}/{reason}")
    if not OUTCOMES[outcome]:
        reason = None
    return outcome, reason


def fallback_outcome(calls):
    for c in calls:
        if c["tool"] == "create_promise" and isinstance(c.get("result"), dict) and c["result"].get("ok"):
            return "promise", None
    for c in calls:
        if c["tool"] == "transfer_to_agent":
            return "transferred", (c.get("args") or {}).get("queue")
    for c in calls:
        if c["tool"] == "schedule_callback" and isinstance(c.get("result"), dict) and c["result"].get("ok"):
            return "not_reached", "callback"
    return "no_promise", "refused"


def close_call(workflow, variables, outcome, reason):
    """The end_of_call lifecycle tool: pre_process_code then the HTTP call."""
    tool = next((t for t in (workflow.get("tools") or [])
                 if (t.get("function") or {}).get("name") == "close_call"), None)
    if tool is None:
        log("! the workflow has no close_call tool")
        return None
    base, _ = bake_api_tool(tool, variables)
    body = dict(base["body"])
    body["outcome"] = outcome
    if reason:
        body["reason"] = reason
    config = {"url": base["url"], "method": base["method"],
              "headers": dict(base["headers"]), "body": body}
    pre = tool.get("pre_process_code") or ""
    if pre.strip():
        try:
            exec(pre, {"vars": variables, "config": config, "__builtins__": __builtins__})
        except Exception as e:
            log(f"    ! close_call pre_process_code raised: {e}")
    config["body"] = {k: v for k, v in (config.get("body") or {}).items()
                      if not (isinstance(v, str) and _placeholder_var(v))}
    code, parsed, _ = bank_call(config["url"], config["method"], config["body"], config["headers"])
    log(f"[tool] close_call {json.dumps(config['body'])} -> {json.dumps(parsed)}")
    return code, parsed


# ---------------------------------------------------------------- the run

def run_case(case, workflow, opts):
    variables = dict(workflow.get("test_variables") or {})
    session = bank("/v1/practice/sessions", {"case": case["id"]})
    if not session.get("variables"):
        raise RuntimeError(f"could not open a bank session for {case['id']}: {session}")
    variables.update(session["variables"])            # call variables win over test_variables
    variables.setdefault("system.iso_utc_now",
                         _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    customer_id = variables["customer_id"]
    log(f"case {case['id']} - {case['title']}  ({case['family']}, {case['level']})")
    if case.get("faults"):
        log(f"faults injected by the bank mock: {json.dumps(case['faults'])}")
    log(f"bank session customer_id={customer_id}  now={variables.get('now')}")

    nodes = workflow.get("nodes") or {}
    globals_ = workflow.get("global_nodes") or {}
    system_prompt = workflow.get("system_prompt") or ""
    ctx = {"history": [], "ended": False, "no_intent": opts.no_intent}
    visited, baked, node_key = {}, {}, workflow.get("initial_node")
    exchanges, hops, entering = 0, 0, True
    while not ctx["ended"] and exchanges < opts.max_exchanges and hops < MAX_HOPS:
        hops += 1
        node = nodes.get(node_key)
        if node is None:
            log(f"! unknown node {node_key}; stopping")
            break
        kind = node.get("node_type")
        spoken = None
        if entering:                       # the engine's node-entry pass
            entering = False
            log(f"[node] {node_key} ({kind})")
            try:
                spoken = entry(node, node_key, variables, visited)
            except Exception as e:
                log(f"! entry of {node_key} raised: {e}")
            if kind in ("api_request", "code"):
                try:
                    run_pre_actions(node, node_key, variables)
                except Exception as e:
                    log(f"    ! pre_actions of {node_key} raised: {e}")
                tr = route(node, variables, ctx, node_key)
                target = (tr or {}).get("target_node") or node.get("passthrough_default_transition")
                if not target or target == node_key:
                    log(f"! passthrough node {node_key} deadlocked; stopping")
                    break
                log(f"[route] {node_key} -> {target}")
                node_key, entering = target, True
                continue
            if kind == "end_call":
                props = ((node.get("terminal") or {}).get("parameters") or {}).get("properties") or {}
                msg = (props.get("spoken_message") or {}).get("default")
                if msg:
                    line = subst(str(msg), variables)
                    ctx["history"].append({"role": "agent", "text": line})
                    log(f"[agent] {line}")
                ctx["ended"] = True
                break
            # conversation node: bake the tools now (baking happens when the node is entered)
            baked[node_key] = [(t.get("function", {}).get("name"), t) + bake_api_tool(t, variables)
                               for t in (node.get("tools") or [])
                               if (t.get("function") or {}).get("handler") == "__function__:api_call"]
        tools = baked.get(node_key) or []
        if spoken == "LLM_ENTRY":          # the model writes the first line of the node
            moved = agent_turn(node, node_key, variables, system_prompt, tools,
                               ctx["history"], "opening", ctx)
            if ctx["ended"]:
                break
            if moved:
                node_key, entering = moved, True
                continue
        elif last_is_customer(ctx["history"]) and not ctx["ended"]:
            moved = agent_turn(node, node_key, variables, system_prompt, tools,
                               ctx["history"], "reply", ctx)
            if ctx["ended"]:
                break
            if moved:
                node_key, entering = moved, True
                continue
        if ctx["ended"]:
            break
        if agent_said_goodbye(ctx["history"]):
            ctx["ended"] = True
            log("[call] the agent said goodbye")
            break
        line = customer_turn(case, variables, ctx["history"], ctx)
        if line is None:
            break
        ctx["history"].append({"role": "customer", "text": line})
        exchanges += 1
        try:
            run_extraction(node, variables, ctx["history"])
        except Exception as e:
            log(f"    ! extraction of {node_key} raised: {e}")
        tr = route(node, variables, ctx, node_key)
        if not tr:                         # global nodes are checked after the node's own
            for gk, gnode in globals_.items():
                if node_key in (gnode.get("excluded_nodes") or []):
                    continue
                if eval_cond(gnode.get("condition") or {}, variables) is True:
                    tr = {"target_node": gk, "description": "global node"}
                    break
        if tr:
            target = tr.get("target_node")
            if target == "__previous__":
                target = node_key
            if target != node_key:
                log(f"[route] {node_key} -> {target}  ({tr.get('description') or ''})")
                node_key, entering = target, True
            else:
                log(f"[route] {node_key} stays  ({tr.get('description') or ''})")
        # no match: stay in the node and answer from the same task_message
    if exchanges >= opts.max_exchanges:
        log(f"! turn budget reached ({opts.max_exchanges} exchanges)")
    if ctx["ended"]:
        log("[call] the agent ended the call")

    # ---- close_call, ledger, score
    ledger_before = bank("/v1/practice/ledger/" + customer_id)
    outcome, reason = closing_decision(system_prompt, variables, ctx["history"],
                                       ledger_before.get("calls") or [])
    log(f"[close] decided outcome={outcome!r} reason={reason!r}")
    close_call(workflow, variables, outcome, reason)
    # the judge reads ctx["history"]; make the close visible there too
    ctx["history"].append({"role": "system",
                           "text": f"[tool] close_call outcome={outcome!r} reason={reason!r} (recorded by the platform)"})
    ledger = bank("/v1/practice/ledger/" + customer_id)
    verdict = score_ledger(case, ledger)
    tools = [x["tool"] for x in ledger.get("calls") or []]
    log(f"[ledger] {json.dumps({k: ledger.get(k) for k in ('outcome', 'reason', 'promises', 'notes', 'callbacks', 'transfers')}, default=str)}")
    log(f"[tools] {' > '.join(tools) or '(none)'}")
    log(f"LOCAL {'PASS' if verdict['pass'] else 'FAIL'}  {case['id']}  (ledger, platform scorer)")
    for f in verdict["failed"]:
        log("       - " + str(f)[:300])
    judge = None
    if not opts.no_judge:
        judge = judge_checks(case, ctx["history"])
    return {"id": case["id"], "pass": verdict["pass"], "failed": verdict["failed"],
            "judge": judge, "outcome": outcome, "reason": reason,
            "tools": tools, "customer_id": customer_id, "history": ctx["history"]}


def last_is_customer(history):
    return bool(history) and history[-1].get("role") == "customer"


def agent_said_goodbye(history):
    """The end-call trigger: the agent's last line says goodbye (the workflow's end_call
    trigger patterns are 'Have a good day' / goodbye)."""
    last = next((m.get("text") or "" for m in reversed(history) if m.get("role") == "agent"), "")
    return bool(END_RE.search(last))


def judge_checks(case, messages):
    """The conversation checks of the platform judge, approximated locally and labelled as such."""
    prompt = ("You are a strict call reviewer. Read the transcript and decide whether each "
              "success criterion holds. Judge only what the transcript shows. Reply with STRICT "
              'JSON: {"checks": [{"check": "<text>", "pass": true|false, "why": "<short>"}], '
              '"verdict": "pass"|"fail"}.\n\nSUCCESS CRITERIA:\n- '
              + "\n- ".join(case["checks"])
              + "\n\nTRANSCRIPT:\n" + render_history(messages))
    try:
        data = extract_json(llm(prompt, "local judge"))
    except Exception as e:
        log(f"[judge] unreadable answer ({e})")
        return None
    checks = data.get("checks") or []
    verdict = str(data.get("verdict") or "").lower()
    ok = verdict == "pass" and all(c.get("pass") for c in checks)
    log(f"local judge (approximate, not authoritative): {'PASS' if ok else 'FAIL'}")
    for c in checks:
        log(f"       - {'ok ' if c.get('pass') else 'BAD'} {str(c.get('check'))[:90]}"
            + ("" if c.get("pass") else f"  -- {str(c.get('why'))[:160]}"))
    return {"pass": ok, "checks": checks}


# ---------------------------------------------------------------- main

def load_cases(path):
    return json.loads(pathlib.Path(path).read_text())


def main():
    ap = argparse.ArgumentParser(description="Run Freya cases against a workflow, locally.")
    ap.add_argument("case", help="a case id from the case file, or all")
    ap.add_argument("workflow", nargs="?", default=str(ROOT / "submission" / "brief-a.workflow.json"))
    ap.add_argument("--cases", default=str(ROOT / "public-test-set.json"))
    ap.add_argument("--no-judge", action="store_true", help="skip the local transcript judge")
    ap.add_argument("--no-intent", action="store_true", help="treat matches_intent as never matching")
    ap.add_argument("--max-exchanges", type=int, default=MAX_EXCHANGES)
    ap.add_argument("--out", help="write the run (verdicts, transcripts) to this JSON file")
    a = ap.parse_args()
    if not TEAM_KEY:
        raise SystemExit("missing FREYA_BANK_TEAM_KEY - run: source env.sh (any secret of 16+ chars)")
    raw = json.loads(pathlib.Path(a.workflow).read_text())
    workflow = raw.get("workflow", raw)
    cases = load_cases(a.cases)
    picked = cases if a.case == "all" else [c for c in cases if c["id"] == a.case]
    if not picked:
        raise SystemExit(f"no case {a.case} in {a.cases} (have: {', '.join(c['id'] for c in cases)})")
    results = []
    for case in picked:
        log("=" * 78)
        t0 = time.time()
        try:
            r = run_case(case, workflow, a)
        except Exception as e:
            log(f"! {case['id']} crashed: {e}")
            traceback.print_exc()
            r = {"id": case["id"], "pass": False, "failed": [f"harness crash: {e}"], "judge": None}
        r["seconds"] = round(time.time() - t0)
        results.append(r)
        log(f"-- {case['id']}: {'PASS' if r.get('pass') else 'FAIL'} in {r['seconds']} s\n")
    log("=" * 78)
    for r in results:
        j = r.get("judge")
        jv = "" if j is None else ("  judge: " + ("PASS" if j["pass"] else "FAIL"))
        log(f"{'PASS' if r.get('pass') else 'FAIL'}  {r['id']}  ledger{jv}"
            + (f"  ({'; '.join(str(x)[:90] for x in r.get('failed') or [])})" if not r.get("pass") else ""))
    log(f"\n{sum(1 for r in results if r.get('pass'))} / {len(results)} passed the ledger check "
        f"(the platform's scorer, run locally).")
    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(json.dumps(results, indent=1, default=str))
        pathlib.Path(str(a.out) + ".log").write_text("\n".join(TRACE) + "\n")
        log(f"run written to {a.out} (trace: {a.out}.log)")


if __name__ == "__main__":
    main()
