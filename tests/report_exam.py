"""Report the mock-exam results: a case table with matrix coverage, appended to
tests/findings.md as a dated section.

    python3 tests/report_exam.py [case_file] [--note "what changed"]
"""
import json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent

def main():
    case_path = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "tests" / "exam-10.json")
    note = sys.argv[sys.argv.index("--note") + 1] if "--note" in sys.argv else ""
    stem = pathlib.Path(case_path).stem
    cases = json.loads(pathlib.Path(case_path).read_text())
    combined = []
    bi = 1
    while (ROOT / "results" / f"{stem}-b{bi}.json").exists():
        data = json.loads((ROOT / "results" / f"{stem}-b{bi}.json").read_text())
        combined += data.get("rows", [])
        bi += 1
    if not combined:
        raise SystemExit(f"no results found for {stem} — run tests/run_custom.py first")
    rows = {r["id"]: r for r in combined}
    passed = sum(1 for r in combined if r.get("pass"))

    lines = [f"## {time.strftime('%Y-%m-%d %H:%M')} — mock exam {stem}", "",
             f"- score: {passed} / {len(combined)} passed", "",
             "| case | difficulty | theme | disposition | band | result |", "|---|---|---|---|---|---|"]
    for c in cases:
        r = rows.get(c["id"])
        mark = "PASS" if r and r.get("pass") else "FAIL"
        lines.append(f"| {c['case_id']} | {c['difficulty']} | {c['theme']} | {c['disposition']} | {c['debt_band']} | {mark} |")
    lines += ["", "Failures:", ""]
    for c in cases:
        r = rows.get(c["id"])
        if r and not r.get("pass"):
            lines.append(f"- {c['case_id']} ({c['theme']}): " + "; ".join(str(x) for x in r.get("failed", []))[:300])
    if not any(r and not r.get("pass") for r in combined):
        lines.append("- none")
    lines += ["", f"- judgement: {note}" if note else "- judgement: (none noted)", ""]
    report = "\n".join(lines)
    print(report)
    with open(ROOT / "tests" / "findings.md", "a") as f:
        f.write(report + "\n")
    print(f"appended to tests/findings.md")

if __name__ == "__main__":
    main()
