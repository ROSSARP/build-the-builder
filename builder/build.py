"""The builder: brief + tool API in, a tested phone agent on Freya out.

    python3 builder/build.py briefs/brief-a.md [tools/openapi.json] [--no-fix] [--fix N] [--reps N]

Steps: extract a spec from the brief (one LLM call), generate a workflow from it,
save it on Freya, run the practice customers, fix what fails (LLM), export the
workflow for submission and leave a plain-text trace.
"""
import json, os, pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import freya
from builder import gen, spec as spec_mod

BUILDER_MODEL = os.environ.get("BUILDER_MODEL", "claude-sonnet-5-5")
TRACE = []  # set per-run in main(); a module default so helper imports work standalone

def log(msg):
    print(msg, flush=True)

def trace_line(text):
    TRACE.append(text)

def llm(prompt, purpose):
    """One model call through the claude CLI (uses the existing Claude login)."""
    t0 = time.time()
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--model", BUILDER_MODEL]
    # strip this session's model overrides so the spawned CLI uses the models we ask for
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL")
           and not k.startswith(("CLAUDE_MODEL", "ANTHROPIC_DEFAULT_"))}
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900, env=env)
    model = BUILDER_MODEL
    if r.returncode != 0 or "unrecognized_model" in (r.stderr or ""):
        model = "default"
        r = subprocess.run(["claude", "-p", prompt, "--output-format", "json"],
                           capture_output=True, text=True, timeout=900, env=env)
    took = time.time() - t0
    out = r.stdout.strip()
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
                    result = out
        else:
            result = out
    trace_line(f"model call: {model}, purpose: {purpose}, "
               f"prompt {len(prompt)} chars, answer {len(str(result))} chars, {took:.0f} s")
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

def load_briefs(brief_path):
    """The target brief plus every sibling .md brief, so a delta brief sees its base."""
    p = pathlib.Path(brief_path)
    files = sorted(pathlib.Path(p.parent).glob("*.md"), key=lambda f: f.name)
    files = [f for f in files if f.name != "README.md"]
    texts = []
    for f in files:
        mark = " (TARGET)" if f.resolve() == p.resolve() else ""
        texts.append(f"=== {f.name}{mark} ===\n{f.read_text()}")
    return "\n\n".join(texts)

def load_tool_api(path):
    return json.loads(pathlib.Path(path).read_text())

def find_tool_api(brief_path, arg):
    if arg:
        return arg
    p = pathlib.Path(brief_path)
    for f in sorted(p.parent.glob("*.openapi.json")):
        return str(f)
    return str(ROOT / "tools" / "openapi.json")

def save(slot, workflow):
    state = freya.save_workflow(slot, workflow)
    trace_line(f"freya: workflow_id {state['workflow_id']}, agent_id {state['agent_id']}, "
               f"nodes {len(workflow.get('nodes', {}))}, version {state.get('version', 'new')}")
    return state

def apply_edits(workflow, edits):
    """Apply the fix LLM's patch: prompt texts only, structure untouched."""
    if not isinstance(edits, list):
        raise ValueError("the model returned no edit list")
    for e in edits:
        node = e.get("node")
        field = e.get("field")
        value = e.get("value")
        if node not in workflow.get("nodes", {}):
            raise ValueError(f"unknown node: {node}")
        if field == "task_message" or field == "routing_prompt":
            workflow["nodes"][node][field] = value
        elif field == "on_enter.text":
            workflow["nodes"][node].setdefault("on_enter", {})["text"] = value
        else:
            raise ValueError(f"field not allowed: {field}")
        trace_line(f"fix edit: {node}.{field}")
    return workflow

def run_test(slot, agent_id, brief_letter, reps, cases_path=None):
    """One run_cases.py run, retried once after a platform hiccup.

    Returns (passed, total, failures_text, rows). The result file is removed
    first so a crashed run can never read a stale score from an earlier one.
    """
    out = ROOT / "results" / f"{slot}.json"
    if out.exists():
        out.unlink()
    cmd = [sys.executable, str(ROOT / "tools" / "run_cases.py"), agent_id]
    if cases_path:
        cmd += ["--cases", cases_path]
    else:
        cmd += ["--brief", brief_letter]
    cmd += ["--out", str(out)]
    if reps > 1:
        cmd += ["--reps", str(reps)]
    for attempt in range(2):
        log("$ " + " ".join(cmd[1:]))
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        log(r.stdout)
        if r.stderr:
            log(r.stderr[-1000:])
        if out.exists():
            data = json.loads(out.read_text())
            rows = data.get("rows", [])
            failed = [row for row in rows if not row.get("pass")]
            trace_line("test: " + (r.stdout or "").strip().splitlines()[-1] if r.stdout.strip() else "test failed")
            return (data.get("passed", 0), data.get("total", 0),
                    "\n".join(f"{row.get('id')} {row.get('family')} | tools: {' > '.join(row.get('tools', []))}"
                              f": {'; '.join(row.get('failed', []))}"
                              for row in failed), rows)
        if attempt == 0:
            log(f"-- test run crashed ({r.returncode}), retrying once after 30 s")
            trace_line("test: crashed, retrying")
            time.sleep(30)
    trace_line("test: failed twice")
    return (0, 0, (r.stdout or "")[-2000:], [])

def brief_letter(slot):
    if slot.startswith("brief-a"):
        return "A"
    if slot.startswith("brief-b"):
        return "B"
    return None

def log_findings(slot, args, state, passed, total, t0):
    """Append one dated run section to tests/findings.md, oldest first."""
    f = ROOT / "tests" / "findings.md"
    f.parent.mkdir(exist_ok=True)
    if not f.exists():
        f.write_text("# Builder test findings\n\nEvery test run of the builder is logged here, oldest first. "
                     "The builder appends one dated section per run (score, failures, ids, artifacts); "
                     "the `test-builder` skill adds the judgement line (what changed, what to try next).\n\n")
    rows = []
    out = ROOT / "results" / f"{slot}.json"
    if out.exists():
        rows = json.loads(out.read_text()).get("rows", [])
    flags = f" {args.tool_api}" if args.tool_api else ""
    flags += " --no-fix" if args.no_fix else f" --fix {args.fix}"
    if args.reps > 1:
        flags += f" --reps {args.reps}"
    if args.cases:
        flags += f" --cases {args.cases}"
    if args.fix_only:
        flags += " --fix-only"
    lines = [f"## {time.strftime('%Y-%m-%d %H:%M')} — {slot}", "",
             f"- command: python3 builder/build.py {args.brief}{flags}",
             f"- workflow {state.get('workflow_id')}, agent {state.get('agent_id')}",
             f"- score: {passed} / {total} passed" if total else "- no practice test run (test failed)",
             f"- duration: {int(time.time() - t0)} s", ""]
    for r in rows:
        mark = "PASS" if r.get("pass") else "FAIL"
        line = f"- {mark} {r.get('id')} ({r.get('level')}, {r.get('family')}):"
        line += (" " + "; ".join(str(x) for x in r.get("failed", []))) if not r.get("pass") else " ok"
        lines.append(line)
    lines += ["", f"- artifacts: results/{slot}.json, traces/{slot}.log, submission/{slot}.workflow.json",
              "- judgement: (none noted)", ""]
    with open(f, "a") as fh:
        fh.write("\n".join(lines))
    log(f"findings appended to {f}")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("brief")
    ap.add_argument("tool_api", nargs="?")
    ap.add_argument("--no-fix", action="store_true")
    ap.add_argument("--fix", type=int, default=1)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--cases", help="test on this case file instead of the practice set")
    ap.add_argument("--fix-only", action="store_true",
                    help="skip extraction and generation: test and fix the currently published workflow")
    a = ap.parse_args()

    global TRACE
    TRACE = []
    t0 = time.time()
    slot = pathlib.Path(a.brief).stem
    if slot == "brief":  # a brief file named just "brief.md": use its folder's name
        slot = pathlib.Path(a.brief).parent.name
    trace_line(f"start: {time.strftime('%Y-%m-%d %H:%M:%S')} UTC, brief {slot}")
    for k in ("FREYA_API_KEY",):
        if not os.environ.get(k):
            raise SystemExit("missing env key " + k + " - run: source env.sh")

    briefs_text = load_briefs(a.brief)

    if a.fix_only:
        # work on the currently published workflow: no extraction, no generation
        export = ROOT / "submission" / f"{slot}.workflow.json"
        if not export.exists():
            raise SystemExit(f"--fix-only needs {export} (run the builder normally once first)")
        workflow = json.loads(export.read_text())["workflow"]
        log(f"== fix-only: loaded the published workflow from {export} ==")
    else:
        api = load_tool_api(find_tool_api(a.brief, a.tool_api))

        # 1. extract the spec
        log("== extract: reading the brief ==")
        spec = None
        for attempt in range(2):
            try:
                spec = extract_json(llm(spec_mod.EXTRACT_PROMPT
                    .replace("__BRIEFS__", briefs_text)
                    .replace("__API__", json.dumps(api)[:20000]), "extract spec from brief"))
                errors = spec_mod.spec_validation_errors(spec)
                if errors:
                    raise ValueError("; ".join(errors))
                break
            except Exception as e:
                log(f"spec attempt {attempt + 1} failed: {e}")
                spec = None
        if spec is None:
            raise SystemExit("could not extract a usable spec")
        log(f"spec: {len(spec.get('identity', {}).get('questions', []))} identity questions, "
            f"{len(spec.get('dates', {}).get('holidays', []))} holidays, "
            f"{len(spec.get('closing', {}).get('table', []))} closing rows, "
            f"products max {spec.get('products', {}).get('max')}")

        # 2. generate and validate
        log("== generate: building the workflow ==")
        workflow = gen.build_workflow(spec, api)
        try:
            freya.validate_workflow(slot, workflow)
        except RuntimeError as e:
            log(f"validation failed, asking the model to fix the workflow: {e}")
            workflow = extract_json(llm(spec_mod.FIX_PROMPT
                .replace("__BRIEFS__", briefs_text)
                .replace("__WORKFLOW__", json.dumps(workflow))
                .replace("__FAILURES__", str(e)[:800]),
                "fix workflow rejected by the platform"))
            freya.validate_workflow(slot, workflow)

    # 3. save on Freya
    state = save(slot, workflow)
    agent_id = state["agent_id"]

    # 4. test and fix
    letter = brief_letter(slot)
    passed = total = 0
    best_workflow, best_passed = workflow, 0
    if letter or a.cases:
        passed, total, failures, rows = run_test(slot, agent_id, letter, a.reps, a.cases)
        best_passed = passed
        for attempt in range(0 if a.no_fix else a.fix):
            if passed >= total:
                break
            log(f"== fix pass {attempt + 1}: {passed}/{total} passed ==")
            try:
                prompt = spec_mod.FIX_PATCH_PROMPT.replace("__BRIEFS__", briefs_text) \
                    .replace("__WORKFLOW__", json.dumps(workflow)).replace("__FAILURES__", failures[:3000])
                patch = None
                for patch_attempt in range(2):
                    try:
                        patch = extract_json(llm(prompt, f"fix workflow for the failing cases"))
                        break
                    except Exception as e:
                        log(f"patch answer unreadable ({e}), retrying once")
                        prompt = prompt + "\n\nYour previous answer was not valid JSON. Reply with ONLY the JSON object."
                if patch is None:
                    raise ValueError("the fix model produced no readable patch")
                # deep copy first: keep-best compares references, an in-place edit would alias them
                workflow = apply_edits(json.loads(json.dumps(workflow)), patch.get("edits"))
                freya.validate_workflow(slot, workflow)
                state = save(slot, workflow)
            except Exception as e:
                log(f"fix pass {attempt + 1} failed, keeping the current version: {e}")
                trace_line(f"fix pass {attempt + 1} failed: {e}")
                break
            passed, total, failures, rows = run_test(slot, state["agent_id"], letter, a.reps, a.cases)
            if passed > best_passed:
                best_passed, best_workflow = passed, workflow
    else:
        log("no practice brief name matched (hidden brief?): skipping practice tests")

    # a fix can regress a passing case: publish the best scoring version so the
    # exported file matches what actually scored best
    if best_passed > 0 and best_workflow is not workflow:
        log(f"re-publishing the best version ({best_passed}/{total} passed)")
        state = save(slot, best_workflow)
        workflow = best_workflow
        passed = best_passed

    # persist the best across RUNS too: a later regeneration that scores lower
    # must not replace a better workflow on the platform. Only the standard
    # practice set counts — custom/exam/reps scores use different scales and
    # must not pollute this store.
    best_file = ROOT / "tests" / "best.json"
    best_store = json.loads(best_file.read_text()) if best_file.exists() else {}
    cur = best_store.get(slot, {})
    comparable = not a.cases and a.reps == 1
    if comparable and total and passed >= cur.get("score", -1):
        best_store[slot] = {"score": passed, "total": total, "workflow": workflow,
                            "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        best_file.write_text(json.dumps(best_store, indent=1))
        log(f"stored best for {slot}: {passed}/{total}")
    elif comparable and cur.get("workflow"):
        log(f"re-publishing the stored best for {slot} ({cur.get('score')}/{cur.get('total')} passed)")
        state = save(slot, cur["workflow"])
        workflow = cur["workflow"]
        passed = cur["score"]
    else:
        log("skipping cross-run best for this non-standard run")

    # 5. export and finish
    export = ROOT / "submission" / f"{slot}.workflow.json"
    export.parent.mkdir(exist_ok=True)
    freya.export_workflow(state["workflow_id"], str(export))
    trace_line(f"export: {export}")
    trace_line(f"end: {time.strftime('%Y-%m-%d %H:%M:%S')} UTC, {time.time() - t0:.0f} s")
    if letter:
        log(f"\n== {slot}: {passed} / {total} passed, workflow {state['workflow_id']}, agent {state['agent_id']} ==")

    traces = ROOT / "traces"
    traces.mkdir(exist_ok=True)
    (traces / f"{slot}.log").write_text("\n".join(TRACE) + "\n")
    log_findings(slot, a, state, passed, total, t0)

if __name__ == "__main__":
    main()
