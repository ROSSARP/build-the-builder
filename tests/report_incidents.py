"""Merge the audit agents' incident lists into one report, grouped by type, and
append it to tests/findings.md.

    python3 tests/report_incidents.py [incidents-1.json incidents-2.json ...]
"""
import json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent

def main():
    paths = sys.argv[1:] or sorted(str(p) for p in (ROOT / "results").glob("incidents-*.json"))
    incidents, seen = [], set()
    for p in paths:
        for inc in json.loads(pathlib.Path(p).read_text()):
            key = (inc.get("call_id"), inc.get("incident_type"), inc.get("title"))
            if key in seen:
                continue
            seen.add(key)
            incidents.append(inc)
    by_type = {}
    for inc in incidents:
        by_type.setdefault(inc["incident_type"], []).append(inc)
    lines = [f"## {time.strftime('%Y-%m-%d %H:%M')} — transcript audit (all calls so far)", "",
             f"- calls audited: see results/calls/index.json; incidents: {len(incidents)}", ""]
    for t in ("brief_violation", "customer_unhelped", "out_of_scope", "platform_error"):
        for inc in by_type.get(t, []):
            lines.append(f"- [{t}] {inc['title']} — call {inc.get('call_id', '?')[:8]}…, severity {inc.get('severity', '?')}")
            lines.append(f"  - {inc.get('description', '')[:220]}")
            ev = inc.get("evidence") or []
            if ev:
                lines.append(f"  - evidence: {ev[0][:160]!r}")
            if inc.get("suggested_fix"):
                lines.append(f"  - suggested fix: {inc.get('suggested_fix', '')[:160]}")
    if not incidents:
        lines.append("- no incidents found")
    lines.append("")
    report = "\n".join(lines)
    print(report)
    with open(ROOT / "tests" / "findings.md", "a") as f:
        f.write(report + "\n")
    print(f"appended {len(incidents)} incidents to tests/findings.md")

if __name__ == "__main__":
    main()
