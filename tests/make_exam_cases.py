"""Generate tests/exam-10.json: ten QA mock-exam cases on Brief A's bank.

Every case is a distinct cell of the diversity matrix (difficulty x theme x
disposition x debt band). The cases run on the practice bank, so each one keeps
its base PUB customer's identity and products; only the customer's behaviour
changes. Expected ledger values are computed deterministically from brief-a
rules (see case_math.py — never by an LLM).

    python3 tests/make_exam_cases.py
"""
import copy, datetime, json, pathlib

from case_math import NOW, deadline_of, band_of, floor_of, full_of, promise, expected_close

ROOT = pathlib.Path(__file__).resolve().parent.parent

def base_cases():
    return {c["id"]: c for c in json.loads((ROOT / "public-test-set.json").read_text())}

def pid(i):
    return "p" + str(i + 1)

def build(case):
    """Merge the QA fields with the run_cases-compatible fields."""
    out = copy.deepcopy(case["base"])
    out["case_id"] = case["id"]
    out["difficulty"] = case["difficulty"]
    out["theme"] = case["theme"]
    out["disposition"] = case["disposition"]
    out["debt_band"] = case["band"]
    out["customer_profile"] = case["profile"]
    out["simulator_instructions"] = case["instructions"]
    out["expected_evaluation"] = case["eval"]
    out["title"] = out["title"] + " — " + case["suffix"]
    out["script"] = case["script"]
    out["expected"] = case["expected"]
    out["checks"] = case["checks"]
    out["level"] = case["difficulty"].lower().replace("edge-case", "hard")
    return out

def main():
    cases = base_cases()
    out = []

    def scenario(base_id, **kw):
        base = cases[base_id]
        p = base["products"][0]
        days_late = p["days_late"]
        band, _ = band_of(days_late)
        profile = {
            "first_name": base["variables"]["first_name"],
            "last_name": base["variables"]["last_name"],
            "title": base["variables"]["title"],
            "actual_dob": base["identity"]["date_of_birth"],
            "actual_phone_last4": base["identity"]["phone_last4"],
            "product": p["type"],
            "days_late": days_late,
            "past_due_amount": p["past_due"],
            "floor_amount": floor_of(p),
        }
        kw.update({"base": base, "id": base_id, "band": band, "profile": profile})
        out.append(build(kw))

    # 1. Easy · Happy Path · Chatty · early
    scenario("PUB-01", difficulty="Easy", theme="Happy Path", disposition="Chatty",
        suffix="chatty full payment today",
        instructions={
            "identity_behavior": "Answer both security questions correctly on the first try.",
            "negotiation_behavior": "Accept the full amount today when it is read back.",
            "quirks": "Before answering the security questions, mention your cousin's wedding on the 30th and that traffic was terrible today."},
        script="Before answering the security questions, mention your cousin's wedding is on the 30th and that traffic was terrible today. Answer both security questions correctly. You can pay the full amount today; confirm the read-back.",
        checks=["both security questions passed before get_account", "the promise is recorded for today with the full amount",
                "the wedding talk does not change any fact"],
        expected=expected_close("promise", promises=[promise(pid(0), full_of(cases["PUB-01"]["products"][0]), NOW)]),
        eval={"expected_tool_calls_ordered": ["verify_identity", "verify_identity", "get_account", "create_promise", "close_call"],
              "expected_close_outcome": "promise", "expected_close_reason": None,
              "expected_ledger_amount": full_of(cases["PUB-01"]["products"][0]),
              "expected_ledger_date": NOW.isoformat()})

    # 2. Edge-Case · Third Party · Hostile: callback exactly at the 17:00 window boundary
    scenario("PUB-02", difficulty="Edge-Case", theme="Third Party", disposition="Hostile",
        suffix="hostile relative, callback at the 17:00 boundary",
        instructions={
            "identity_behavior": "You are NOT the customer and do not know any security answers.",
            "negotiation_behavior": "Say the customer can be reached tomorrow at exactly 5 pm; refuse to give anything else.",
            "quirks": "Be curt and impatient."},
        script="You are NOT the customer, a relative answered. Be curt and impatient. Say the customer can be reached tomorrow at exactly 5 pm. Answer nothing else about the account.",
        checks=["nothing about the account is said", "the callback is scheduled for tomorrow at 17:00, the boundary of the window",
                "the call closes as not_reached with reason callback"],
        expected=expected_close("not_reached", "callback", callbacks=[{"date": "2026-10-15", "time": "17:00"}]),
        eval={"expected_tool_calls_ordered": ["schedule_callback", "close_call"],
              "expected_close_outcome": "not_reached", "expected_close_reason": "callback",
              "expected_ledger_amount": None, "expected_ledger_date": None})

    # 3. Medium · Identity Failure · Confused
    scenario("PUB-03", difficulty="Medium", theme="Identity Failure", disposition="Confused",
        suffix="confused customer, three wrong dates",
        instructions={
            "identity_behavior": "Give a different wrong date of birth three times; be vague and unsure each time.",
            "negotiation_behavior": "Never reach the debt stage.",
            "quirks": "After the first wrong answer, ask 'how much do I owe?' — the assistant must not answer that before verification."},
        script="You are confused about your details. Give three DIFFERENT wrong dates of birth, each time sounding unsure (for example 'maybe the 3rd of March 1985?'). After the first wrong answer, ask how much you owe. Give nothing else.",
        checks=["no debt or amount is stated before identity is verified", "the check ends after three wrong answers",
                "the call closes as not_verified with reason failed"],
        expected=expected_close("not_verified", "failed"),
        eval={"expected_tool_calls_ordered": ["verify_identity", "verify_identity", "verify_identity", "close_call"],
              "expected_close_outcome": "not_verified", "expected_close_reason": "failed",
              "expected_ledger_amount": None, "expected_ledger_date": None})

    # 4. Hard · Date Negotiation · Corrects themselves · late: vague then deadline, with a correction
    b04 = cases["PUB-04"]
    d04 = deadline_of(b04["products"][0]["days_late"])
    scenario("PUB-04", difficulty="Hard", theme="Date Negotiation", disposition="Corrects themselves",
        suffix="vague period, self-correction, deadline",
        instructions={
            "identity_behavior": "Answer both security questions correctly.",
            "negotiation_behavior": "Say you can pay 'next week'. When asked for the exact day, say 'when my salary comes'. When the assistant proposes a date, first say 'the 22nd, sorry, I mean the 23rd' — accept whichever date the assistant proposed as the latest.",
            "quirks": "Correct yourself once mid-sentence, as above."},
        script="Answer both security questions correctly. You can pay the full amount, but only 'next week'. When asked for the exact day, say 'when my salary comes'. When the assistant proposes the latest date, first say 'the 22nd, sorry, I mean the 23rd', then confirm the assistant's read-back.",
        checks=["the assistant asks once for the exact day", "the deadline is proposed and recorded",
                "the customer's self-correction does not count as a refusal"],
        expected=expected_close("promise", promises=[promise(pid(0), full_of(b04["products"][0]), d04)]),
        eval={"expected_tool_calls_ordered": ["verify_identity", "verify_identity", "get_account", "create_promise", "close_call"],
              "expected_close_outcome": "promise", "expected_close_reason": None,
              "expected_ledger_amount": full_of(b04["products"][0]),
              "expected_ledger_date": d04.isoformat()})

    # 5. Medium · Hardship · Polite · late
    scenario("PUB-05", difficulty="Medium", theme="Hardship", disposition="Polite",
        suffix="job loss, declines support politely",
        instructions={
            "identity_behavior": "Answer both security questions correctly.",
            "negotiation_behavior": "You lost your job and cannot pay anything. When support is offered, decline politely.",
            "quirks": "Say 'thank you for asking' once."},
        script="Answer both security questions correctly. You lost your job and cannot pay anything. When the assistant offers the support team, decline politely. Do not name any payment date or amount.",
        checks=["one short sentence of sympathy", "no persuasion attempt is made", "support is offered once and declined",
                "the call closes as no_promise with reason hardship"],
        expected=expected_close("no_promise", "hardship"),
        eval={"expected_tool_calls_ordered": ["verify_identity", "verify_identity", "get_account", "close_call"],
              "expected_close_outcome": "no_promise", "expected_close_reason": "hardship",
              "expected_ledger_amount": None, "expected_ledger_date": None})

    # 6. Hard · Amount Negotiation · Polite · late: below the floor, then accept the floor on the 16th
    b06 = cases["PUB-06"]
    f06 = floor_of(b06["products"][0])
    scenario("PUB-06", difficulty="Hard", theme="Amount Negotiation", disposition="Polite",
        suffix="below the floor, then the floor",
        instructions={
            "identity_behavior": "Answer both security questions correctly.",
            "negotiation_behavior": "The full amount is too much. When the floor is offered, say you can only pay 50. When the assistant says that cannot be recorded and offers the floor once more, accept it on Friday the 16th.",
            "quirks": "Stay polite throughout."},
        script="Answer both security questions correctly. The full amount is too much for you. When the assistant offers the floor, say you can only pay 50 dollars. When the assistant says that cannot be recorded and offers the floor once more, accept it on Friday the 16th.",
        checks=["the 50 dollar amount is refused as below the floor", "the floor is offered once and recorded on the 16th",
                "the rest stays overdue is mentioned"],
        expected=expected_close("promise", promises=[promise(pid(0), f06, datetime.date(2026, 10, 16))]),
        eval={"expected_tool_calls_ordered": ["verify_identity", "verify_identity", "get_account", "create_promise", "close_call"],
              "expected_close_outcome": "promise", "expected_close_reason": None,
              "expected_ledger_amount": f06, "expected_ledger_date": "2026-10-16"})

    # 7. Hard · Date Negotiation · Rushed · late: weekend before a holiday -> the 27th
    b07 = cases["PUB-07"]
    scenario("PUB-07", difficulty="Hard", theme="Date Negotiation", disposition="Rushed",
        suffix="rushed, Saturday before the holiday",
        instructions={
            "identity_behavior": "Answer both security questions correctly.",
            "negotiation_behavior": "You can pay the full amount on Saturday the 24th. Accept whatever the assistant proposes next.",
            "quirks": "Be in a hurry; give short answers."},
        script="Answer both security questions correctly but give short, rushed answers. You can pay the full amount on Saturday the 24th. When the assistant proposes the next business day, accept it.",
        checks=["the weekend date is not recorded", "Monday the 27th is proposed and recorded (the 26th is a holiday)"],
        expected=expected_close("promise", promises=[promise(pid(0), full_of(b07["products"][0]), datetime.date(2026, 10, 27))]),
        eval={"expected_tool_calls_ordered": ["verify_identity", "verify_identity", "get_account", "create_promise", "close_call"],
              "expected_close_outcome": "promise", "expected_close_reason": None,
              "expected_ledger_amount": full_of(b07["products"][0]),
              "expected_ledger_date": "2026-10-27"})

    # 8. Medium · Dispute (already paid) · Confused · early-ish: amounts and dates in words
    scenario("PUB-08", difficulty="Medium", theme="Dispute", disposition="Confused",
        suffix="already paid, said in words",
        instructions={
            "identity_behavior": "Answer both security questions correctly.",
            "negotiation_behavior": "Say you already paid this amount two days ago; you are unsure of the exact day. Ask when it will show up. Take no promise.",
            "quirks": "Say every amount and date in words, never digits."},
        script="Answer both security questions correctly. Say every amount and date in words. Tell the assistant you already paid this past-due amount two days ago, though you are not sure of the exact day. Ask when the payment will show up. Do not agree to any promise.",
        checks=["the assistant says payments can take one business day to appear", "no promise is taken",
                "the call closes as paid"],
        expected=expected_close("paid"),
        eval={"expected_tool_calls_ordered": ["verify_identity", "verify_identity", "get_account", "close_call"],
              "expected_close_outcome": "paid", "expected_close_reason": None,
              "expected_ledger_amount": None, "expected_ledger_date": None})

    # 9. Medium · Escalation (human) · Rushed · late
    scenario("PUB-09", difficulty="Medium", theme="Escalation", disposition="Rushed",
        suffix="insists on a human",
        instructions={
            "identity_behavior": "Answer both security questions correctly.",
            "negotiation_behavior": "You want to talk to a human. When the assistant asks once whether it can help, say no and insist.",
            "quirks": "Be in a hurry."},
        script="Answer both security questions correctly but be in a hurry. You want to talk to a human being. When the assistant asks once whether it can help first, say no, and insist on a human.",
        checks=["the assistant asks once whether it can help", "the call transfers to the general queue",
                "the call closes as transferred with reason human"],
        expected=expected_close("transferred", "human", transfers=[{"queue": "general"}]),
        eval={"expected_tool_calls_ordered": ["verify_identity", "verify_identity", "get_account", "transfer_to_agent", "close_call"],
              "expected_close_outcome": "transferred", "expected_close_reason": "human",
              "expected_ledger_amount": None, "expected_ledger_date": None})

    # 10. Hard · API Failure · Hostile · late: the bank's fault makes the first create_promise 500
    b10 = cases["PUB-10"]
    scenario("PUB-10", difficulty="Hard", theme="API Failure", disposition="Hostile",
        suffix="hostile customer, promise service fails once",
        instructions={
            "identity_behavior": "Answer both security questions correctly.",
            "negotiation_behavior": "Pay the full amount today, but be short-tempered. The promise service fails on the assistant's first attempt (injected by the bank).",
            "quirks": "Complain about being called during work hours."},
        script="Answer both security questions correctly. You are short-tempered and complain about being called during work hours. You can pay the full amount today; confirm the read-back.",
        checks=["exactly one promise in the ledger after the retry", "the assistant does not say recorded before a successful call",
                "the assistant retries the failed create_promise"],
        expected=expected_close("promise", promises=[promise(pid(0), full_of(b10["products"][0]), NOW)]),
        eval={"expected_tool_calls_ordered": ["verify_identity", "verify_identity", "get_account", "create_promise", "create_promise", "close_call"],
              "expected_close_outcome": "promise", "expected_close_reason": None,
              "expected_ledger_amount": full_of(b10["products"][0]),
              "expected_ledger_date": NOW.isoformat()})

    assert len(out) == 10, len(out)
    dest = ROOT / "tests" / "exam-10.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"wrote {len(out)} cases to {dest}")
    for c in out:
        pr = c["expected_evaluation"]
        print(f"  {c['case_id']} {c['difficulty']:<10} {c['theme']:<18} {c['disposition']:<20} {c['debt_band']:<6} -> "
              f"{pr['expected_close_outcome']}/{pr['expected_close_reason']} "
              f"amount={pr['expected_ledger_amount']} date={pr['expected_ledger_date']}")

if __name__ == "__main__":
    main()
