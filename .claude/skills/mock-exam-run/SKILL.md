---
name: mock-exam-run
description: Run the mock-exam cases against a phone agent with the real simulation (ledger + judge scoring) and print the pass/fail table. Use when asked to run the mock exam, test the exam cases or score an agent on the exam.
---

# Run the mock exam

Work from the kit folder. The exam runs as real simulations on the practice bank,
so a run takes 5 to 15 minutes. Run it in the foreground and wait for it to
finish; never start a second simulation while one is running, and never end the
turn while a run is in progress.

## Steps

1. `source env.sh` (needs `FREYA_API_KEY` and `FREYA_BANK_TEAM_KEY`).
2. Run: `python3 tests/run_custom.py [agent_id] tests/exam-10.json`
   With no agent id the current brief-a agent from `.freya-agents.json` is used.
   The runner splits the cases into id-safe batches automatically.
3. Note the total line (`== exam-10 total: N / 10 passed ==`) and every FAIL
   line with its reasons.
4. Finish by running the report skill (`/mock-exam-report`) so the results land
   in `tests/findings.md`.

## Rules

- Never edit the agent on the platform by hand. Improve the builder and rerun.
- A single green run is a hint, not proof — repeat before trusting a score.
