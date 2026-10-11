"""Run a generated case file against an agent in id-safe batches.

run_cases.py keys personas and bank sessions by case id, so two cases with the
same id in one run collapse into one call. Batches avoid that: every batch holds
at most one case per id. Prints a combined summary.

    python3 tests/run_custom.py [agent_id] [case_file]
    # defaults: the brief-a agent from .freya-agents.json, tests/custom-30.json
"""
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

def main():
    agent = sys.argv[1] if len(sys.argv) > 1 else None
    case_path = sys.argv[2] if len(sys.argv) > 2 else str(ROOT / "tests" / "custom-30.json")
    if not agent:
        state = json.loads((ROOT / ".freya-agents.json").read_text())
        agent = state["brief-a"]["agent_id"]
    stem = pathlib.Path(case_path).stem
    cases = json.loads(pathlib.Path(case_path).read_text())
    by_id = {}
    for c in cases:
        by_id.setdefault(c["id"], []).append(c)
    batches = []
    while True:
        batch = []
        for variants in by_id.values():
            if len(variants) > len(batches):
                batch.append(variants[len(batches)])
        if not batch:
            break
        batches.append(batch)

    combined = []
    for bi, batch in enumerate(batches, start=1):
        f = ROOT / "tests" / f"{stem}-batch{bi}.json"
        f.write_text(json.dumps(batch, indent=1))
        out = ROOT / "results" / f"{stem}-b{bi}.json"
        cmd = [sys.executable, str(ROOT / "tools" / "run_cases.py"), agent,
               "--cases", str(f), "--out", str(out)]
        print(f"== batch {bi}: {len(batch)} cases ==", flush=True)
        print("$", " ".join(cmd[1:]), flush=True)
        r = subprocess.run(cmd, text=True)
        print(r.stdout, flush=True)
        if r.stderr:
            print(r.stderr[-500:], flush=True)
        if out.exists():
            data = json.loads(out.read_text())
            for c, row in zip(batch, data.get("rows", [])):
                row["title"] = c["title"]
                combined.append(row)
    passed = sum(1 for r in combined if r.get("pass"))
    print(f"\n== {stem} total: {passed} / {len(combined)} passed ==")
    for r in combined:
        mark = "PASS" if r.get("pass") else "FAIL"
        print(f"{mark} {r.get('id')} {r.get('title')}")
        for f_ in r.get("failed", []):
            print(f"     - {f_[:200]}")

if __name__ == "__main__":
    main()
