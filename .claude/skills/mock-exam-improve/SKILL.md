---
name: mock-exam-improve
description: Fix the builder based on mock-exam failures — durable fixes in the generator, targeted fixes through the patch loop — then rerun the exam and report. Use when asked to improve the builder, fix exam failures or run the self-improvement loop.
---

# Self-improve from exam failures

Work from the kit folder. Fix the builder, never the agent: change
`builder/gen.py` or `builder/spec.py` for durable fixes, or run the patch loop
for targeted prompt fixes.

## Steps

1. Read every FAIL line from the last exam run (`tests/findings.md` or the
   runner output). Group the failures by root cause: date math, identity,
   amounts, claims, notes, or conversation wording.
2. Decide per group:
   - **durable fix** (rules, routes, tools, code nodes, extraction schemas):
     edit `builder/gen.py` / `builder/spec.py`, then rebuild the agent with
     `python3 builder/build.py briefs/brief-a.md --no-fix` and test again.
   - **targeted fix** (prompt wording only): run the patch loop against the
     exam cases:
     `python3 builder/build.py briefs/brief-a.md --fix-only --cases tests/exam-10.json`
     The patch loop only rewrites `task_message` / `on_enter.text` /
     `routing_prompt`, so it cannot break the workflow structure; keep-best
     re-publishes the better version automatically.
3. Rerun the exam (`/mock-exam-run`) and report the delta (`/mock-exam-report`
   with a `--note` naming what changed).

## Rules

- Never write a date, amount, name or value taken from an exam case into the
  builder — fix the rules and prompts, not the cases.
- Never edit the agent on the platform by hand.
- A single green run is a hint, not proof — repeat before trusting a score.
