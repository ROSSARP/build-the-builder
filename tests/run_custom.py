"""Run tests/custom-30.json in batches — one variant per base customer per batch.

run_cases.py keys personas and bank sessions by case id, so two variants of the
same id in one run collapse into one call. Batches avoid that: every batch holds
at most one variant per base customer. Prints a combined summary.

    python3 tests/run_custom.py [agent_id]     # defaults to the brief-a agent
"""
import json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

def main():
    if len(sys.argv) > 1:
        agent = sys.argv[1]
    else:
        state = json.loads((ROOT / ".freya-agents.json").read_text())
        agent = state["brief-a"]["agent_id"]
    cases = json.loads((ROOT / "tests" / "custom-30.json").read_text())
    by_base = {}
    for c in cases:
        by_base.setdefault(c["id"], []).append(c)
    batches = []
    while True:
        batch = []
        for variants in by_base.values():
            if len(variants) > len(batches):
                batch.append(variants[len(batches)])
        if not batch:
            break
        batches.append(batch)

    combined = []
    for bi, batch in enumerate(batches, start=1):
        f = ROOT / "tests" / f"custom-batch{bi}.json"
        f.write_text(json.dumps(batch, indent=1))
        out = ROOT / "results" / f"custom-b{bi}.json"
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
    print(f"\n== custom total: {passed} / {len(combined)} passed ==")
    for r in combined:
        mark = "PASS" if r.get("pass") else "FAIL"
        print(f"{mark} {r.get('id')} {r.get('title')}")
        for f_ in r.get("failed", []):
            print(f"     - {f_[:200]}")

if __name__ == "__main__":
    main()
