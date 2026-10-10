---
name: test-builder
description: Run the builder on a brief, test the phone agent against the practice customers and record the run in tests/findings.md. Use when asked to test the builder, run the practice cases or check a score.
---

# Test the builder

Work from the kit folder. Every run is logged to `tests/findings.md` — the builder appends the facts, you add the judgement.

## Steps

1. `source env.sh` (needs `FREYA_API_KEY` and `FREYA_BANK_TEAM_KEY`).
2. Run the builder. A test run takes 3 to 11 minutes; run it in the foreground and wait for it to finish. Never start a second simulation while one is running, and never end the turn while a test runs.
   - raw generator score: `python3 builder/build.py briefs/brief-a.md --no-fix`
   - with the fix loop: `python3 builder/build.py briefs/brief-a.md` (add `--fix N`; each fix pass re-runs the test)
   - brief B: `python3 builder/build.py briefs/brief-b.md`
   - the final-like run: `--reps 3` (a customer counts only when every run passes)
3. The builder appends a dated section to `tests/findings.md` at the end of the run. Add one line to that section: what changed since the previous run and what to try next. If a run was made before the logging existed, re-log it with `python3 tests/log_run.py <slot> --note "..."`.
4. Read every FAIL line and its reason before changing anything. Prefer fixes in `builder/gen.py` (routes, tools, code nodes) and `builder/spec.py` (extraction prompts) over hand-editing workflows.
5. Never edit the agent on the platform by hand. Change the builder and run it again.
