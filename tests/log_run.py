"""Append one dated test-run section to tests/findings.md from the run artifacts.

    python3 tests/log_run.py <slot> [--note "what changed"]

Used to re-log a run (for example one made before the builder logged on its own).
The builder itself calls the same code at the end of every run.
"""
import json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent

def log_findings(slot, command, workflow_id, agent_id, passed, total, duration_s, note=""):
    f = ROOT / "tests" / "findings.md"
    f.parent.mkdir(exist_ok=True)
    if not f.exists():
        f.write_text("# Builder test findings\n\nEvery test run of the builder is logged here, oldest first. The builder appends one dated section per run (score, failures, ids, artifacts); the `test-builder` skill adds the judgement line (what changed, what to try next).\n\n")
    rows = []
    out = ROOT / "results" / f"{slot}.json"
    if out.exists():
        rows = json.loads(out.read_text()).get("rows", [])
    lines = [f"## {time.strftime('%Y-%m-%d %H:%M')} — {slot}", "",
             f"- command: {command}",
             f"- workflow {workflow_id}, agent {agent_id}",
             f"- score: {passed} / {total} passed" if total else "- no practice test run",
             f"- duration: {int(duration_s)} s", ""]
    for r in rows:
        mark = "PASS" if r.get("pass") else "FAIL"
        line = f"- {mark} {r.get('id')} ({r.get('level')}, {r.get('family')}):"
        line += (" " + "; ".join(str(x) for x in r.get("failed", []))) if not r.get("pass") else " ok"
        lines.append(line)
    lines += ["", f"- artifacts: results/{slot}.json, traces/{slot}.log, submission/{slot}.workflow.json",
              f"- judgement: {note}" if note else "- judgement: (none noted)", ""]
    with open(f, "a") as fh:
        fh.write("\n".join(lines))
    return f

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        raise SystemExit("usage: python3 tests/log_run.py <slot> [--note text]")
    slot = a[0]
    note = ""
    if "--note" in a:
        note = a[a.index("--note") + 1]
    state = json.loads((ROOT / ".freya-agents.json").read_text()).get(slot, {})
    res = {}
    out = ROOT / "results" / f"{slot}.json"
    if out.exists():
        res = json.loads(out.read_text())
    f = log_findings(slot, f"python3 builder/build.py {slot}", state.get("workflow_id", "?"),
                     state.get("agent_id", "?"), res.get("passed", 0), res.get("total", 0),
                     res.get("seconds", 0), note)
    print(f"appended to {f}")
