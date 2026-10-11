---
name: platform-check
description: Check the Freya platform health, list and cancel stuck simulations, and detect outage signatures in test results. Use when simulations fail, hang, 504 or behave strangely — BEFORE touching the builder.
---

# Check the platform before blaming the agent

Work from the kit folder. The organisers' outage rules, in order:

1. A 504 on one endpoint (for example `POST /api/v2/chat/message`) does NOT mean
   simulations are down — the pieces fail independently. Check each piece.
2. Only ONE simulation runs at a time per workspace. Look at what is running:
   `python3 tests/platform_check.py sims`.
3. Never stop `run_cases.py` locally to "fix" a hang: the simulation keeps
   running on Freya, and the next test waits for it.
4. Cancel a stuck simulation with `python3 tests/platform_check.py cancel <sim_id>`
   (POST /api/v2/simulations/{id}/cancel; falls back to delete when the route is
   missing). A simulation stuck in "running" for hours stops immediately.
5. On 5xx errors, retry with waits — the kit's freya.py does not retry.
   `tests/platform_check.py` retries 3 times, 10 seconds apart.
6. Outage signature: no tool calls on any customer AND ~0 s average agent turns
   is a platform outage, NOT an agent bug. `python3 tests/platform_check.py signature`
   scans the latest results for it. NEVER "fix" the workflow after such a run —
   wait and rerun the test instead.

## Steps

1. `source env.sh`.
2. Run `python3 tests/platform_check.py full` — it prints health, the recent
   simulations, any stuck ones, and the outage signature.
3. Decide:
   - healthy + no stuck + no signature: the failures are real; use
     `/mock-exam-improve` or the patch loop.
   - stuck simulation found: cancel it with
     `python3 tests/platform_check.py cancel <id>`, wait 30 s, rerun.
   - outage signature: do nothing to the builder. Wait, then rerun the test.
4. Log the incident and the decision in `tests/findings.md`.

## Rules

- Never edit the agent or the builder because of a run that matches the outage signature.
- Never start a second simulation while one is running; never end your turn while a test runs.
