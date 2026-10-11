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
