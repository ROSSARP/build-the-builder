# Mock exam — final-day rehearsal

Three mock hidden briefs in the two formats the final uses: **exam-1** and **exam-2**
are clean specifications, **exam-3** is raw bank material (a mail, a policy extract,
a memo that changes it, a code list). Each exam folder holds one brief plus its own
tool API file whose fields and allowed values differ from the practice one — exactly
like the final ("the seven tool names stay the same. Their fields and allowed values
can change").

Every brief uses a different bank, different identity questions, different holidays,
deadline bands, callback windows and closing tables. Nothing here is copied from
brief-a/brief-b.

## Run the exam

```bash
source env.sh

# clean spec, postcode + birth year identity, "escalated" outcome
python3 builder/build.py mock-exam/exam-1/exam-1.md mock-exam/exam-1/tools.openapi.json 2>&1 | tee traces/exam-1.log

# clean spec, THREE security questions, different calendar
python3 builder/build.py mock-exam/exam-2/exam-2.md mock-exam/exam-2/tools.openapi.json 2>&1 | tee traces/exam-2.log

# raw material: mail + policy + memo + code list
python3 builder/build.py mock-exam/exam-3/exam-3.md mock-exam/exam-3/tools.openapi.json 2>&1 | tee traces/exam-3.log
```

Each run takes 1-3 minutes (no practice tests exist for these briefs, so the builder
generates, validates, saves and exports).

## What to verify after each run

1. **Saved and published:** the run prints a `workflow_id` and `agent_id`; `.freya-agents.json` has the slot.
2. **Export exists:** `submission/<exam>.workflow.json` loads and has `workflow_id`, `agent_id`, `workflow`.
3. **Trace is complete:** `traces/<exam>.log` has start and end time, the model call line, the Freya ids, the export path.
4. **Identity questions match the brief** (grep the workflow):
   - exam-1: `postcode`, `birth_year` (and NOT `date_of_birth`)
   - exam-2: `postcode`, `birth_year`, `phone_last4`
   - exam-3: `phone_last4`, `postcode` (phone FIRST, per the policy)
5. **Closing table matches the brief:** `close_call`'s outcome enum contains `escalated` (all three), and the no-reason outcomes are `promise` and `paid`.
6. **Holidays match the brief** (grep the dates code): exam-1 has `2026-10-12`/`2026-10-29`/`2026-12-31`/`2027-01-18`; exam-2 has `2026-11-02`/`2026-11-27`/`2026-12-24`/`2026-12-25`/`2027-01-04`; exam-3 has `2026-10-20`/`2026-11-09`/`2026-12-07`/`2027-01-01` — and the MEMO's 5th-business-day band (not the extract's 4th) is baked into the code.
7. **Deadline bands match:** exam-1 `10th/5th` business day; exam-2 `14th/6th`; exam-3 `9th/5th` (memo override).
8. **No leaks from the practice briefs:** grep the workflow for `date_of_birth`, `Freya Bank`, `transferred` (outcome), `2026-10-26` — none may appear.
9. **Greeting:** contains the right bank name and the word "monitored", never the literal word "recorded".
10. **Time:** each run well under 30 minutes (expect ~1-3 minutes).

## Example 1 — a good run (exam-1)

```
$ python3 builder/build.py mock-exam/exam-1/exam-1.md mock-exam/exam-1/tools.openapi.json
== extract: reading the brief ==
spec: 2 identity questions, 4 holidays, 6 closing rows, products max 1
== generate: building the workflow ==
no practice brief name matched (hidden brief?): skipping practice tests
...
== exam-1: 0 / 0 passed, workflow <id>, agent <id> ==
findings appended to tests/findings.md
```

Checks: 2 questions (postcode, birth year) ✓ · 4 holidays ✓ · `escalated` in the closing rows ✓ · no test run ✓.

## Example 2 — greps that prove the rules landed

```bash
# identity fields came from the exam's tool API
python3 -c "import json;w=json.load(open('submission/exam-1.workflow.json'))['workflow'];print([t['function']['parameters']['properties']['body']['properties']['field'].get('enum') for t in w['nodes']['identity']['tools'] if t['function']['name']=='verify_identity'])"
# -> [['postcode', 'birth_year']]

# the memo override won (5th business day, not the 4th)
grep -o 'business_day.: 5' submission/exam-3.workflow.json
# -> business_day: 5

# no practice-brief leakage
grep -cE 'date_of_birth|transferred|Freya Bank' submission/exam-1.workflow.json
# -> 0
```

If any check fails, fix the generator (`builder/gen.py`, `builder/spec.py`), not the
workflow by hand, and run the exam again.
