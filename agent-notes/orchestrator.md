# Final window orchestration (taken over from the 961031fc session, which died of context overflow ~20:35)

## 21:00 (18:00 UTC) — takeover
DONE (by previous session / its background agents):
- Case pack fully mirrored into `finalcase/` (Drive watcher `tests/drive_watch.py sync` still running)
- `tests/final_contract.json` (7 services, /voice/v1, data/call envelope) — check (a) PASS vs 34 test customers
- `tests/final_spec.json` (query domain, rule_ledger, open_questions)
- `tests/example_checks.json` — 6 example scenarios extracted — check (d) PASS
- `builder/gen_query.py` — query-domain workflow generator; dryrun workflow at `tests/final-workflow-dryrun.json`
- Cloudflare deploy pipeline tested green (see `tests/findings.md`); token/KV OK; subdomain fcodefcode3

FAILS to fix (from `tests/self_heal_last_check.json` @17:41Z):
- c_mock_dryrun: mock_gen can't consume final_contract.json without LLM ("not OpenAPI JSON") → build a deterministic mock builder (planned by the dead session: pure lookup table, no LLM)
- b_workflow_from_spec: 2 English-looking prompt texts in the generated workflow → fix gen_query.py

TODO:
- Write deterministic mock builder: final_contract.json + test-customers.json → worker.js (7 endpoints, exact responses+status)
- Generate → deploy as `final-case-mock-bank` (--with-kv optional; lookup table needs no state) → smoke
- Fix the 2 English texts in gen_query.py → `build.py finalcase/ $MOCK_URL` → export → trace
- Replay 6 examples locally (self_heal.py score) → fix → repeat
- submission.json + commit + email to yavuz@freyavoice.ai before 20:00 UTC (23:00 Istanbul)
NEXT: mock builder (builder/mock_final.py)

## 22:05 (19:05 UTC)
LIVE: orchestrator — orchestrator.md
OWN: builder/gen_query.py@cf-mock-session — Turkish prompts, week_get tool, mandatory sentences
OWN: builder/build.py@cf-mock-session — case wiring (spec reuse, api from services, gen_query dispatch)
DONE:
- Mock LIVE: final-case-mock-bank.fcodefcode3.workers.dev (34 customers, 7 services + close/transfer, smoke PASS)
- build.py wired: reuses tests/final_spec.json + builds api from final_contract.json services; gen_query dispatch
- BUILDER RUN: workflow d659b17f-78c8-4fd1-8002-46755b07d54a, agent 34b38ddd-7429-4f04-aca2-4b5d8861c2e6 (7 nodes), exported submission/finalcase.workflow.json + trace
- Platform smoke: Turkish greeting OK; BUG: opening quoted the card-selection mandatory sentence (was in system_prompt) + fixed example names (Yıldız Premium/Pratik) not the caller's own
TODO:
- Fix: mandatory sentences -> statement node task (not system_prompt); strip fixed example names in _tr_spoken_only
- Rebuild + re-smoke; then self_heal score (static example checks)
- Fill submission.json (NEED team name + member name/email from user) + git commit + email to yavuz@freyavoice.ai before 20:00 UTC
