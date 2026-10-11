---
name: mock-exam-generate
description: Generate ten diverse QA mock-exam cases for Brief A following the diversity matrix (difficulty x theme x disposition x debt band), validate them and list them. Use when asked to create mock exams, QA cases or exam scenarios.
---

# Generate mock-exam cases

Work from the kit folder. The ten cases live in `tests/exam-10.json`, generated
deterministically from Brief A's rules (`briefs/brief-a.md` + `tools/openapi.json`)
so every expected ledger value is exact — no LLM date math, ever.

## Steps

1. Read `briefs/brief-a.md` to refresh the rules the cases exercise.
2. Run `python3 tests/make_exam_cases.py` — it writes `tests/exam-10.json` and
   prints one line per case (difficulty, theme, disposition, band, expected close).
3. Run `python3 tests/validate_exam_cases.py` — it checks the schema, the matrix
   diversity (no repeated theme x disposition, all four difficulties, both debt
   bands) and that every expected date is a business day inside the deadline.
4. Present the ten cases as a table.

## Rules

- Every case keeps its base PUB customer's identity and products: the practice
  bank only knows PUB-01..13. Only the customer's behaviour changes.
- The API-failure theme must use PUB-10: the bank injects the 500 on that id.
- To add or change a scenario, edit the scenario table in
  `tests/make_exam_cases.py` — never hand-edit `tests/exam-10.json`.
