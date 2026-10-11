LIVE: sim-tester — sim-tester.md — agent sim-tester

## 22:10 (19:10 UTC) — phase 1 baseline launched on v5 export
DONE:
- Read fleet protocol (mock-exam-local, git-relay), comm-review + verify-mock tails, findings tail.
- Acked coordinator hold: baseline = current export (21:55 Istanbul, updated_at 18:55Z, md5 d5852d72cec3be33dd40a6bee3b4de87); R3 phrase present, totalDebt absent (R4b -> v6, waiting for ack commit before comparison run).
- No JS runtime on this box (no node/npx) -> can't run the dryrun worker. Built a local practice-namespace shim instead: tests/sim-tester-practice-shim.py (sessions/ledger/close_call/transfer_to_human on 127.0.0.1:8787). The 7 contract tools stay on the DEPLOYED mock (real envelope + cross-call state).
- Mechanical conversion (no hand-copied case data): tests/sim-tester-build.py -> tests/sim-tester-cases-p1.json (6 local_sim cases from tests/example_checks.json; ids = customerNumber; script from title+customer_lines; checks = expected_agent_behaviour + expected_outcome; expected outcome no_promise/refused — collection vocabulary, no "info success" outcome exists).
- Harness copy tests/sim-tester-wf-p1.json = byte-copy of the v5 export with ONLY close_call + transfer_to_human URLs redirected to the shim (1 replacement each, verified). Workflow logic untouched.
- Found: deployed mock (mock/final/worker.js, mock_final.py) serves /voice/v1/close_call OK but has NO practice/ledger read; week.change accepted a same-week change with NO token (contract says 401-once + already-has-week error) -> mock behavioral gap, relay after results.
- State hygiene: example-2 and example-5 share customer 96158684 and both change statement week -> restore to week 1 via direct week.change between them (proven safe probe: change-to-current-week is accepted, no token needed).
- Two parallel streams launched ~19:10 UTC: A=ex1,ex3,ex4; B=ex6,ex2,[restore],ex5. Shim PID in bg task bk1mlz657.
TODO:
- Record per-case PASS/FAIL + reasons in tests/findings.md; relay mock gaps + any builder defects.
- Phase 2: WAIT for orchestrator R4b/v6 ack commit, then re-run same six.

## 22:35 (19:35 UTC) — RETARGETED to v9 (9274e0c, md5 c0968dc8, updated_at 19:25:54Z)
DONE:
- v9 verified: totalDebt 2 refs, henüz kesilmiş 2, cut-day trigger 3 — R4b IN. Harness copies rebuilt from v9 (tests/sim-tester-wf-p1.json, tests/sim-tester-wf-p1-cutday.json; shim redirects + now-override intact).
- Triage: 3-way stream concurrency caused claude-CLI 120 s timeouts (ex1 + probe-ncut poisoned; ex1's tool data was CORRECT pre-timeout). All streams stopped; now ONE sequential runner: v9 probe-cutday -> v9 probe-ncut -> v9 ex1. Nothing new after ~19:45 UTC per coordinator.
- ex6 completed its whole dialogue cleanly on v5 (log kept) but verdict wasn't reached; other v5 examples stopped at triage. v5 baseline evidence stands on: ex1 tool-data + structural grep + comm-review 29fe76f independent audit.
TODO:
- Report cutday/ncut/ex1 verdicts + append findings; relay @main the acceptance result.

## 22:45 (19:45 UTC) — FINAL: stopped by user directive
DONE: findings updated with partial verdicts (v9: cutday incomplete, ncut judge FAIL on card-selection stall, R3/R4b structural fixes verified; ex1-v9 not started). All background runners stopped. LIVE-END: sim-tester.
