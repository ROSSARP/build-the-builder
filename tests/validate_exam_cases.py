"""Validate tests/exam-10.json: schema, matrix diversity, and rule consistency.

    python3 tests/validate_exam_cases.py [case_file]

Every expected date must be a business day within the deadline; every outcome
and reason must be in brief-a's closing table; the matrix cells must not repeat.
"""
import datetime, json, pathlib, sys

from case_math import HOL, is_biz, deadline_of, band_of

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLOSING = {"promise": {None}, "paid": {None},
           "transferred": {"restructuring", "human", "support"},
           "no_promise": {"refused", "hardship", "dispute", "service_error"},
           "not_verified": {"failed", "declined"},
           "not_reached": {"callback", "no_callback", "wrong_number", "deceased", "unclear"}}
DIFFICULTIES = {"Easy", "Medium", "Hard", "Edge-Case"}
REQUIRED_QA = ("case_id", "difficulty", "theme", "disposition", "customer_profile",
               "simulator_instructions", "expected_evaluation")
REQUIRED_EVAL = ("expected_tool_calls_ordered", "expected_close_outcome",
                 "expected_close_reason", "expected_ledger_amount", "expected_ledger_date")
REQUIRED_RUNNER = ("id", "brief", "family", "level", "title", "variables", "identity",
                   "products", "script", "expected", "checks")

def validate(cases, expect=None):
    expect = expect or (10 if len(cases) <= 10 else len(cases))
    errors = []
    if not isinstance(cases, list) or len(cases) != expect:
        errors.append(f"expected {expect} cases, got {len(cases) if isinstance(cases, list) else 'not a list'}")
        return errors

    ids = [c.get("case_id") for c in cases]
    if len(set(ids)) != len(ids):
        errors.append(f"duplicate case ids: {ids}")
    for c in cases:
        cid = c.get("case_id", "?")
        for f in REQUIRED_QA + REQUIRED_RUNNER:
            if f not in c:
                errors.append(f"{cid}: missing field {f}")
        ev = c.get("expected_evaluation") or {}
        for f in REQUIRED_EVAL:
            if f not in ev:
                errors.append(f"{cid}: expected_evaluation missing {f}")
        out_, reason = ev.get("expected_close_outcome"), ev.get("expected_close_reason")
        if out_ not in CLOSING:
            errors.append(f"{cid}: outcome {out_} not in brief-a's closing table")
        elif reason not in CLOSING[out_]:
            errors.append(f"{cid}: reason {reason} is not valid for outcome {out_}")
        if ev.get("expected_ledger_date"):
            try:
                d = datetime.date.fromisoformat(ev["expected_ledger_date"])
            except ValueError:
                errors.append(f"{cid}: bad date {ev['expected_ledger_date']}")
                continue
            if not is_biz(d):
                errors.append(f"{cid}: {d} is a weekend day or a holiday")
            if out_ == "promise" and d is not None:
                p = c["products"][0]
                if d > deadline_of(p["days_late"]):
                    errors.append(f"{cid}: {d} is after the deadline {deadline_of(p['days_late'])}")
        expected = c.get("expected") or {}
        eo, er = expected.get("outcome"), expected.get("reason")
        if eo not in CLOSING:
            errors.append(f"{cid}: runner expected outcome {eo} not in brief-a's closing table")
        elif er not in CLOSING[eo]:
            errors.append(f"{cid}: runner expected reason {er} is not valid for outcome {eo}")
        for pr in expected.get("promises", []):
            p = c["products"][0]
            floor = p.get("minimum_payment") or p.get("instalment_amount") or 0
            a = pr.get("amount", 0)
            in_range = floor - 1e-6 <= a <= p["past_due"] + 1e-6
            if abs(a - p["past_due"]) > 1e-6 and abs(a - floor) > 1e-6 and not in_range:
                errors.append(f"{cid}: promise amount {a} is outside the floor..full range")
            try:
                pd = datetime.date.fromisoformat(pr["date"])
            except (KeyError, ValueError):
                errors.append(f"{cid}: promise date missing or unreadable: {pr.get('date')}")
                continue
            if not is_biz(pd):
                errors.append(f"{cid}: promise date {pd} is a weekend day or a holiday")
            if pd > deadline_of(p["days_late"]):
                errors.append(f"{cid}: promise date {pd} is after the deadline {deadline_of(p['days_late'])}")
        if "faults" in c or (c.get("id") == "PUB-10" and "API Failure" in c.get("theme", "")):
            pass  # the bank injects the 500 for PUB-10

    # matrix diversity: unique (theme, disposition, suffix), all difficulties, both bands.
    # The 10-case exam forbids repeated theme x disposition; bulk exams (n > 10) only
    # forbid exact duplicates and require every difficulty to appear.
    combos = [(c.get("theme"), c.get("disposition"), c.get("title")) for c in cases]
    if len(set(combos)) != len(combos):
        errors.append(f"duplicate theme x disposition x title: {combos}")
    diffs = {c.get("difficulty") for c in cases}
    if expect == 10 and diffs != DIFFICULTIES:
        errors.append(f"difficulties used: {diffs}, expected all of {DIFFICULTIES}")
    elif expect != 10 and not diffs.issubset(DIFFICULTIES):
        errors.append(f"unknown difficulty in {diffs}")
    bands = {c.get("debt_band") for c in cases}
    if bands != {"early", "late"}:
        errors.append(f"debt bands used: {bands}, expected both early and late")
    return errors

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "tests" / "exam-10.json")
    expect = int(sys.argv[sys.argv.index("--expect") + 1]) if "--expect" in sys.argv else None
    cases = json.loads(pathlib.Path(path).read_text())
    errors = validate(cases, expect)
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(" -", e)
        raise SystemExit(1)
    print(f"validation OK: {len(cases)} cases, matrix diversity clean")

if __name__ == "__main__":
    main()
