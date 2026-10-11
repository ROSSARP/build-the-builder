"""Assemble a bulk exam (e.g. 100 cases) from scenario-slice files that subagents
write, then validate the result.

Scenario entries describe behaviour and expected values by KIND (full/floor,
today/deadline/fixed dates); this script computes every exact ledger value with
case_math so no LLM ever does date arithmetic.

    python3 tests/make_exam_bulk.py <slice1.json> [slice2.json ...] --out tests/exam-100.json [--expect 100]
"""
import copy, datetime, json, pathlib, sys

from case_math import deadline_of, band_of, floor_of, full_of, promise, expected_close

ROOT = pathlib.Path(__file__).resolve().parent.parent

def assemble(spec, base):
    """One scenario spec -> a full case (QA schema + run_cases fields)."""
    out = copy.deepcopy(base)
    p = base["products"][0]
    band, _ = band_of(p["days_late"])
    # the runner's `id` stays the plain bank id (the session key); the QA case_id
    # is unique per scenario so reports and validators can tell them apart
    out["case_id"] = f"{base['id']}-{spec['suffix']}"
    out["difficulty"] = spec["difficulty"]
    out["theme"] = spec["theme"]
    out["disposition"] = spec["disposition"]
    out["debt_band"] = band
    out["customer_profile"] = {
        "first_name": base["variables"]["first_name"],
        "last_name": base["variables"]["last_name"],
        "title": base["variables"]["title"],
        "actual_dob": base["identity"]["date_of_birth"],
        "actual_phone_last4": base["identity"]["phone_last4"],
        "product": p["type"],
        "days_late": p["days_late"],
        "past_due_amount": p["past_due"],
        "floor_amount": floor_of(p),
    }
    out["simulator_instructions"] = {
        "identity_behavior": spec["identity_behavior"],
        "negotiation_behavior": spec["negotiation_behavior"],
        "quirks": spec.get("quirks", ""),
    }
    out["title"] = base["title"] + " — " + spec["suffix"]
    out["script"] = spec["script"]
    out["checks"] = spec["checks"]

    exp = spec["expected"]
    promises = []
    if exp.get("amount") == "full":
        amount = full_of(p)
    elif exp.get("amount") == "floor":
        amount = floor_of(p)
    elif isinstance(exp.get("amount"), str) and exp["amount"].startswith("mid:"):
        # a customer-proposed amount between floor and full (brief-a rule 27)
        amount = round(float(exp["amount"].split(":", 1)[1]), 2)
    else:
        amount = None
    if amount is not None:
        dk = exp.get("date")
        if dk == "today":
            date = datetime.date(2026, 10, 14)
        elif dk == "deadline":
            date = deadline_of(p["days_late"])
        elif isinstance(dk, str) and dk.startswith("next_biz:"):
            date = datetime.date.fromisoformat(dk.split(":", 1)[1])
            while date.weekday() >= 5 or date.isoformat() in ["2026-10-26", "2026-11-11", "2026-11-26", "2026-12-25", "2027-01-01"]:
                date += datetime.timedelta(days=1)
        else:
            date = datetime.date.fromisoformat(dk)
        promises = [promise("p1", amount, date)]
    callbacks = [exp["callback"]] if exp.get("callback") else []
    transfers = [{"queue": exp["transfer"]}] if exp.get("transfer") else []
    notes = exp.get("notes") or []
    out["expected"] = expected_close(exp["outcome"], exp.get("reason"), promises, notes, callbacks, transfers)
    out["expected_evaluation"] = {
        "expected_tool_calls_ordered": spec.get("tool_calls") or [],
        "expected_close_outcome": exp["outcome"],
        "expected_close_reason": exp.get("reason"),
        "expected_ledger_amount": amount,
        "expected_ledger_date": promises[0]["date"] if promises else None,
    }
    out["level"] = spec["difficulty"].lower().replace("edge-case", "hard")
    return out

def main():
    args = sys.argv[1:]
    if "--out" not in args or "--expect" not in args:
        raise SystemExit("usage: python3 tests/make_exam_bulk.py <slice.json>... --out <file> --expect <n>")
    out_path = args[args.index("--out") + 1]
    expect = int(args[args.index("--expect") + 1])
    slices = [a for a in args if a.endswith(".json") and a != out_path and not a.startswith("--")]
    bases = {c["id"]: c for c in json.loads((ROOT / "public-test-set.json").read_text())}
    cases, seen = [], set()
    for slice_path in slices:
        for spec in json.loads(pathlib.Path(slice_path).read_text()):
            key = (spec.get("theme"), spec.get("disposition"), spec.get("suffix"))
            if key in seen:
                raise SystemExit(f"duplicate scenario: {key} in {slice_path}")
            seen.add(key)
            base = bases[spec["base_id"]]
            cases.append(assemble(spec, base))
    if len(cases) != expect:
        raise SystemExit(f"expected {expect} cases, got {len(cases)}")
    pathlib.Path(out_path).write_text(json.dumps(cases, indent=1))
    print(f"wrote {len(cases)} cases to {out_path}")

if __name__ == "__main__":
    main()
