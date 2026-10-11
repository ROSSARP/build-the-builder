# Aster Bank — collections launch material (raw)

Aster Bank is fictional. Everything here is synthetic.

This file is the raw material the collections team assembled for the new outbound campaign. It is NOT a clean specification. Read everything; the memo overrides the policy where they disagree.

---

## EMAIL — from the Head of Collections

Team,

The new outbound campaign for early-stage collections starts this week. One product per customer, 1 to 45 days late. The basics, in my words:

- Verify who is on the line BEFORE anything else. Never mention collections, debt or payment before the security check passes. This is non-negotiable, even if the customer asks directly.
- Treat people decently. If someone is struggling — illness, a death in the family, job loss — one sentence of sympathy and then connect them to support if they want it. Do not push a payment on them.
- If they say they already paid this amount, do not argue. Payments take one business day to show. Close the call as paid.
- The call is recorded: say so in the opening, along with who you are.

I don't care about the rest of the detail — the policy extract below has it.

— Head of Collections

---

## POLICY EXTRACT — Early-stage collections calls

### Identity

Security questions, one at a time:
1. The last four digits of the phone number on file.
2. The postcode of the registered address (letters and digits, no spaces).

Three wrong answers in total end the check. After that the agent states nothing about the account and closes `not_verified` / `failed`. A customer who declines twice closes `not_verified` / `declined`.

### Dates

Business days are Monday to Friday except the bank holidays in the code list below. Deadlines:

| days_late | deadline |
|---|---|
| 1 to 7 | the 9th business day after today |
| 8 to 45 | the 4th business day after today |

A promise date must be today or later, a business day, not after the deadline. Weekend or holiday: offer the next business day. Vague period: ask once for the exact day, then propose the deadline. A date past the deadline: offer the deadline.

### Amounts

Ask for the full past-due amount first. The floor is `minimum_payment` for credit cards, `instalment_amount` for loans. Offer the floor once; say the rest stays overdue. Accept any customer amount from the floor to the full amount.

### Recording

Read the product, amount and date back and ask "Do you confirm?". Record only after a clear yes, once per product. If the recording fails, try once more; a second failure closes `no_promise` / `service_error`. After a recorded promise say: "You will receive a text message confirming this promise."

### Closing table

| Outcome | Reason |
|---|---|
| `promise` | none |
| `paid` | none |
| `escalated` | `restructuring`, `human`, `support` |
| `no_promise` | `refused`, `hardship`, `dispute`, `service_error` |
| `not_verified` | `failed`, `declined` |
| `not_reached` | `callback`, `no_callback`, `wrong_number`, `deceased`, `unclear` |

---

## MEMO — policy updates (this memo overrides the extract)

Two changes, effective immediately:

1. The deadline for customers **8 to 45 days late is now the 5th business day** after today, not the 4th.
2. Persuasion: one attempt for customers **1 to 7 days late**, two attempts for **8 to 45 days late**. Attempt 1 proposes the last business day of this week (next week's if today is that day). Attempt 2, late band only, proposes the floor on the deadline. When the attempts are used up, stop and close `no_promise` / `refused`.

Also a clarification from legal: the customer's own date or amount proposal is never a refusal. Handle it under the date and amount rules.

---

## CODE LIST — bank holidays (non-working days)

| Code | Date |
|---|---|
| H1 | 2026-10-20 |
| H2 | 2026-11-09 |
| H3 | 2026-12-07 |
| H4 | 2027-01-01 |

---

## ONE-PAGER — call flows nobody bothered to clean up

- Relative answers: say nothing about the call; a callback is for today or the next business day, 10:00 to 19:00, later than now. Outside the window, ask once, then close `not_reached` / `no_callback`. Wrong number: `not_reached` / `wrong_number`. Deceased: "I am sorry for your loss." then `not_reached` / `deceased`.
- "Is this a scam?": the customer can verify by calling Aster Bank's customer service number.
- New payment plan: transfer, queue `restructuring`, close `escalated` / `restructuring`. Human request: ask once whether you can help; if they insist, queue `general`, close `escalated` / `human`.
- Dispute: no argument, close `no_promise` / `dispute`.
- Never offer a discount or a waiver.
