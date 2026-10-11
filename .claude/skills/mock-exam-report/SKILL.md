---
name: mock-exam-report
description: List the mock-exam results as a case table with matrix coverage and append them to tests/findings.md. Use when asked to list exam results, report the exam, or record a run.
---

# Report the mock exam

Work from the kit folder. The report reads the results the runner wrote
(`results/exam-10-b*.json`) and lists every case with its matrix cell.

## Steps

1. Run: `python3 tests/report_exam.py [case_file] [--note "what changed"]`
   It prints the table (case, difficulty, theme, disposition, band, result),
   the failure reasons, and appends the same section to `tests/findings.md`.
2. Add the `--note` line with what changed since the previous run and what to
   try next — the facts are appended automatically, the judgement is yours.
3. If a run was made but the report says no results exist, run the runner first
   (`/mock-exam-run`).

## Rules

- Report failures faithfully: quote the ledger and judge reasons, do not soften them.
- One dated section per run, oldest first, in `tests/findings.md`.
