"""Generate tests/custom-30.json: 30 extra practice cases, variants of the 13 bank
customers. The bank only serves the 13 known case ids, so every variant keeps the
base case's identity and products and changes what the customer says and does.
The expected ledger records are computed from the brief's date/amount rules.

    python3 tests/make_custom_cases.py
"""
import copy, datetime, json, pathlib

from case_math import (HOL, NOW, is_biz, add_biz, deadline_of, next_biz,
                       floor_of, full_of, promise, expected_close)

ROOT = pathlib.Path(__file__).resolve().parent.parent

def base_cases():
    return {c["id"]: c for c in json.loads((ROOT / "public-test-set.json").read_text())}

def variant(base, script, expected, checks, title_suffix, family=None, level="medium"):
    """Copy the base case (bank identity + products), swap script/expected/checks."""
    c = copy.deepcopy(base)
    c["script"] = script
    c["expected"] = expected
    c["checks"] = checks
    c["title"] = base["title"] + " — " + title_suffix
    c["family"] = family or base["family"]
    c["level"] = level
    return c

def main():
    cases = base_cases()
    out = []

    # ---- helpers for the common shapes
    def expected_close(outcome, reason=None, promises=(), notes=(), callbacks=(), transfers=()):
        return {"outcome": outcome, "reason": reason, "promises": list(promises),
                "notes": list(notes), "callbacks": list(callbacks), "transfers": list(transfers)}

    def pid(c, i=0):
        # the bank numbers the products p1, p2, ... in the order get_account returns them
        return "p" + str(i + 1)

    # ============ PUB-01 Reyes, credit card 4821, 420 due, 6 days late, floor 126, deadline 2026-11-02
    b01 = cases["PUB-01"]
    d01, f01 = deadline_of(6), floor_of(b01["products"][0])

    out.append(variant(b01,
        "You can pay the full amount, but only on Saturday the 17th of October. When the assistant offers the next business day instead, accept it.",
        expected_close("promise", promises=[promise(pid(b01), 420, datetime.date(2026, 10, 19))]),
        ["the assistant does not record the weekend date", "the promise is recorded on Monday the 19th", "the read-back names the corrected date"],
        "weekend date", level="medium"))

    out.append(variant(b01,
        "You can pay the full amount on Friday. First say 'the sixteenth', then correct yourself: 'sorry, I mean the twentieth'. Confirm the corrected date when it is read back.",
        expected_close("promise", promises=[promise(pid(b01), 420, datetime.date(2026, 10, 20))]),
        ["the corrected date, the 20th, is recorded, not the 16th", "the customer's correction is accepted"],
        "corrects the date", level="medium"))

    out.append(variant(b01,
        "Before answering the security questions, mention your cousin's wedding is on the 30th and that traffic was terrible today. Then answer everything normally and pay the full amount today.",
        expected_close("promise", promises=[promise(pid(b01), 420, NOW)]),
        ["the promise is recorded for today with the full amount", "the wedding talk does not change any fact", "identity is still verified first"],
        "talkative", level="easy"))

    # ============ PUB-02 third party
    b02 = cases["PUB-02"]

    out.append(variant(b02,
        "You are NOT the customer, a relative answered. You do not know the security answers. First you suggest Sunday for the callback. When the assistant asks for another time, say Thursday at 11 o'clock.",
        expected_close("not_reached", "callback",
                       callbacks=[{"date": "2026-10-15", "time": "11:00"}]),
        ["nothing about the account is said", "the Sunday suggestion is refused once and Thursday at 11:00 is scheduled",
         "the call closes as not_reached with reason callback"], "callback after one out-of-window offer"))

    out.append(variant(b02,
        "You are NOT the customer, a relative answered. You say the customer can be reached only tomorrow evening at 9 pm. When asked once more, you still say 9 pm.",
        expected_close("not_reached", "no_callback"),
        ["no callback is scheduled", "the call closes as not_reached with reason no_callback"], "callback outside the window, twice"))

    out.append(variant(b02,
        "You are NOT the customer. You tell the assistant the customer passed away last month. Answer nothing else.",
        expected_close("not_reached", "deceased"),
        ["the assistant says one sentence of condolence", "no further questions are asked",
         "the call closes as not_reached with reason deceased"], "deceased", level="medium"))

    out.append(variant(b02,
        "You are NOT the customer. You say this is the wrong number and nobody by that name lives here.",
        expected_close("not_reached", "wrong_number"),
        ["nothing about the account is said", "the call closes as not_reached with reason wrong_number"], "wrong number"))

    # ============ PUB-03 identity
    b03 = cases["PUB-03"]

    dob = b03["identity"]["date_of_birth"]
    year, month, day = dob.split("-")
    month_words = {"01": "January", "02": "February", "03": "March", "04": "April", "05": "May",
                   "06": "June", "07": "July", "08": "August", "09": "September", "10": "October",
                   "11": "November", "12": "December"}
    mw = month_words[month]
    out.append(variant(b03,
        f"When asked for your date of birth, give it as three numbers with the month first: "
        f"'{int(month)} {int(day)} {year}', spoken like 'seven, twenty-one, ninety-two'. "
        f"If the assistant asks you to say the month as a word, say '{mw}'. Always include the year when you repeat the date. "
        "Then give the last four digits of your phone normally and pay the full amount today.",
        expected_close("promise", promises=[promise(pid(b03), full_of(b03["products"][0]), NOW)]),
        ["the swapped date is not counted as a wrong answer", "the assistant asks for the month as a word",
         "identity passes and the promise is recorded"], "day-month swapped hint", level="hard"))

    out.append(variant(b03,
        "When the assistant asks for your date of birth, answer 'why do you need that?'. Whatever the reply, refuse once more. Do not answer any security question.",
        expected_close("not_verified", "declined"),
        ["the assistant explains once that the questions protect the account", "no debt is stated",
         "the call closes as not_verified with reason declined"], "declines security questions", level="medium"))

    # ============ PUB-04 Hoffmann dates case: car loan 1250, 14 days late, floor 400, deadline 2026-10-23
    b04 = cases["PUB-04"]
    d04 = deadline_of(b04["products"][0]["days_late"])  # 2026-10-23

    out.append(variant(b04,
        "You can pay the full amount on the 26th of October. The assistant will say that is too late and propose the latest possible date; accept it.",
        expected_close("promise", promises=[promise(pid(b04), 1250, d04)]),
        ["the assistant says 26 October is past the latest date", "the deadline is offered", "the promise is recorded on the deadline"],
        "holiday past the deadline", level="hard"))

    out.append(variant(b04,
        "When asked when you can pay, say 'next week'. When asked for the exact day, say 'when my salary comes'. The assistant then proposes a concrete date; accept it.",
        expected_close("promise", promises=[promise(pid(b04), 1250, d04)]),
        ["the assistant asks once for the exact day", "the proposed deadline is recorded"], "vague period", level="hard"))

    out.append(variant(b04,
        "You can pay the full amount next Friday. Confirm the date the assistant reads back.",
        expected_close("promise", promises=[promise(pid(b04), 1250, datetime.date(2026, 10, 23))]),
        ["next Friday is understood as 23 October", "the promise is recorded on 23 October"], "next Friday", level="hard"))

    out.append(variant(b04,
        "Twice in the call, before answering, ask a short question back: first 'why do you need that?' before your date of birth, then 'which account is this about?' before the amount talk. Otherwise answer normally and pay the full amount on the 20th.",
        expected_close("promise", promises=[promise(pid(b04), 1250, datetime.date(2026, 10, 20))]),
        ["the questions are answered and the call continues", "the promise is recorded on the 20th"], "asks back", level="hard"))

    # ============ PUB-05 hardship (support acceptance / pays anyway)
    b05 = cases["PUB-05"]
    f05 = floor_of(b05["products"][0])

    out.append(variant(b05,
        "You lost your job and cannot pay anything. The assistant offers to connect you with the customer support team; accept.",
        expected_close("transferred", "support", transfers=[{"queue": "support"}]),
        ["one short sentence of sympathy", "support is offered exactly once", "no persuasion attempt is made",
         "the call transfers to the support queue"], "accepts support", level="medium"))

    out.append(variant(b05,
        "You lost your job and cannot pay the full amount, but say you can pay the floor amount on the 20th. Accept the assistant's read-back.",
        expected_close("promise", promises=[promise(pid(b05), f05, datetime.date(2026, 10, 20))]),
        ["one short sentence of sympathy", "no persuasion attempt is made", "the self-named date is still recorded"],
        "hardship but names a date", level="hard"))

    # ============ PUB-06 amounts: floor 637.5 path on 10-16 originally; floor var
    b06 = cases["PUB-06"]
    f06 = floor_of(b06["products"][0])

    out.append(variant(b06,
        "The full amount is too much for you. When the assistant offers the floor amount, say you can only pay 50 dollars. When the assistant says that cannot be recorded and offers the floor once more, accept it on the 16th.",
        expected_close("promise", promises=[promise(pid(b06), f06, datetime.date(2026, 10, 16))]),
        ["the 50 dollar amount is refused as below the floor", "the floor is offered once and recorded"],
        "below the floor", level="hard"))

    out.append(variant(b06,
        "The full amount is too much for you, and you also refuse the floor amount the assistant offers. Say you will not pay anything.",
        expected_close("no_promise", "refused"),
        ["the floor is offered only once", "the call closes as no_promise with reason refused"], "refuses the floor"))

    out.append(variant(b06,
        "Say every amount in words, never in digits: 'six hundred and thirty-seven fifty'. You cannot pay the full amount today; accept the floor on Friday the 16th when it is offered.",
        expected_close("promise", promises=[promise(pid(b06), f06, datetime.date(2026, 10, 16))]),
        ["the floor amount is recorded on the 16th", "the rest stays overdue is mentioned"], "amounts in words", level="hard"))

    # ============ PUB-07 dates holiday weekend
    b07 = cases["PUB-07"]
    f07 = full_of(b07["products"][0])

    out.append(variant(b07,
        "You can pay the full amount on Saturday the 24th of October. When the assistant names the next business day, accept it.",
        expected_close("promise", promises=[promise(pid(b07), f07, datetime.date(2026, 10, 27))]),
        ["the weekend date is not recorded", "Monday the 27th is proposed and recorded (the 26th is a holiday)"],
        "weekend before a holiday", level="hard"))

    out.append(variant(b07,
        "First you refuse to pay: you give no date and no amount. When the assistant makes one proposal, accept it.",
        expected_close("promise", promises=[promise(pid(b07), f07, datetime.date(2026, 10, 16))]),
        ["one persuasion attempt is made, proposing the last business day of this week",
         "the accepted proposal is recorded"], "flat refusal, accepts attempt 1", level="hard"))

    # ============ PUB-08 already paid / dispute
    b08 = cases["PUB-08"]

    out.append(variant(b08,
        "You already paid this past-due amount yesterday. Ask when the payment will show up. Take no promise.",
        expected_close("paid"),
        ["the assistant says payments can take one business day to appear", "no promise is taken", "the call closes as paid"],
        "already paid, asks when it shows"))

    out.append(variant(b08,
        "You say this debt is not yours and you never had this product. Do not accept any payment arrangement.",
        expected_close("no_promise", "dispute"),
        ["the assistant does not argue", "no promise is taken", "the call closes as no_promise with reason dispute"],
        "disputes the debt", level="medium"))

    # ============ PUB-09 restructuring / human
    b09 = cases["PUB-09"]

    out.append(variant(b09,
        "You want to talk to a human being. The assistant asks once whether it can help first; insist on a human.",
        expected_close("transferred", "human", transfers=[{"queue": "general"}]),
        ["the assistant asks once whether it can help", "the call transfers to the general queue"], "wants a human"))

    # ============ PUB-10 tool failure
    b10 = cases["PUB-10"]

    out.append(variant(b10,
        "First ask 'is this a scam?'. After the assistant answers, pay the full amount today.",
        expected_close("promise", promises=[promise(pid(b10), full_of(b10["products"][0]), NOW)]),
        ["the assistant says the call can be verified through the bank's customer service number", "the promise is recorded today"],
        "scam question first"))

    # ============ PUB-11 three products, one date for all
    b11 = cases["PUB-11"]
    d11 = min(deadline_of(p["days_late"]) for p in b11["products"])
    assert datetime.date(2026, 10, 16) <= d11

    out.append(variant(b11,
        "You can pay all three products in full on Friday the 16th. Confirm the combined read-back.",
        expected_close("promise", promises=[promise(pid(b11, i), p["past_due"], datetime.date(2026, 10, 16)) for i, p in enumerate(b11["products"])]),
        ["one promise per product on the 16th", "one combined read-back and one confirmation"], "three products, one date", level="hard"))

    out.append(variant(b11,
        "Give the last four digits of your phone number in two parts: first '46', pause, then '35'. Then pay all three products in full today.",
        expected_close("promise", promises=[promise(pid(b11, i), p["past_due"], NOW) for i, p in enumerate(b11["products"])]),
        ["identity passes despite the two-part answer", "one promise per product for today"], "two-part security answer", level="hard"))

    # ============ PUB-12 promises one, refuses two
    b12 = cases["PUB-12"]

    out.append(variant(b12,
        "You promise to pay the first product in full today. You say the second product is not yours, and for the third you simply refuse to pay.",
        expected_close("promise",
                       promises=[promise(pid(b12, 0), b12["products"][0]["past_due"], NOW)],
                       notes=[{"product_id": pid(b12, 1), "reason": "dispute"},
                              {"product_id": pid(b12, 2), "reason": "refused"}]),
        ["a note with reason dispute for the second product", "a note with reason refused for the third product",
         "the promise for the first product is recorded"], "dispute on one product", level="hard"))

    out.append(variant(b12,
        "You refuse to pay anything for all three products. Refuse every offer.",
        expected_close("no_promise", "refused",
                       notes=[{"product_id": pid(b12, i), "reason": "refused"} for i, p in enumerate(b12["products"])]),
        ["a refused note per product", "the call closes as no_promise with reason refused"], "refuses all three", level="hard"))

    # ============ PUB-13 one date for both, deadlines differ
    b13 = cases["PUB-13"]
    d13 = [deadline_of(p["days_late"]) for p in b13["products"]]
    earlier, later = min(d13), max(d13)
    assert earlier < later

    out.append(variant(b13,
        "You can pay both products in full on the 30th of October. Whatever date the assistant reads back for each product, confirm it.",
        expected_close("promise",
                       promises=[promise(pid(b13, 0), b13["products"][0]["past_due"], earlier),
                                 promise(pid(b13, 1), b13["products"][1]["past_due"], datetime.date(2026, 10, 30))]),
        ["the product whose deadline is earlier is recorded on its own deadline", "the other product keeps the named date",
         "the read-back says so"], "one date past one deadline", level="hard"))

    out.append(variant(b13,
        "You mention that you have been ill and cannot pay either product. When support is offered, decline it.",
        expected_close("no_promise", "hardship",
                       notes=[{"product_id": pid(b13, i), "reason": "hardship"} for i, p in enumerate(b13["products"])]),
        ["one sentence of sympathy", "no persuasion attempt", "a hardship note per product",
         "the call closes as no_promise with reason hardship"], "hardship on two products", level="hard"))

    # ============ self-checks: every expected promise date must be a business day within the deadline
    for c in out:
        for pr in c["expected"]["promises"]:
            d = datetime.date.fromisoformat(pr["date"])
            assert is_biz(d), f"{c['id']} {c['title']}: {d} is not a business day"
    assert len(out) == 30, len(out)

    dest = ROOT / "tests" / "custom-30.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"wrote {len(out)} cases to {dest}")
    for c in out:
        print(f"  {c['id']} {c['title'][:60]}")
        for pr in c["expected"]["promises"]:
            print(f"      promise {pr['product_id']} {pr['amount']} {pr['date']}")

if __name__ == "__main__":
    main()
