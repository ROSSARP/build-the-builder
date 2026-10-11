---
name: mock-exam-local
description: Run the workflow through the LOCAL simulator (no Freya platform) — exact ledger scoring against the real bank mock plus an approximate LLM judge. Use when the platform is down or to iterate quickly; run several case files in parallel with sub-agents.
---

# Test locally, without the platform

Work from the kit folder. `tests/local_sim.py` interprets the workflow JSON
locally: node loop, deterministic transitions, code nodes, extraction, tool
calls against the real bank mock, and scoring with the platform's own
`score_ledger`. The agent and customer are LLMs (the claude CLI), so the ledger
score is exact and the judge is approximate.

## Steps

1. `source env.sh` (needs FREYA_BANK_TEAM_KEY; Freya API key is only used to
   fetch nothing — the bank mock is called directly).
2. Run one case: `python3 tests/local_sim.py PUB-01 submission/brief-a.workflow.json`
   or a whole file: `python3 tests/local_sim.py all submission/brief-a.workflow.json --cases tests/exam-10.json --out results/local-exam10.json`
   (~2 minutes per case; prints every dialogue line and each LLM call).
3. For speed, partition the case file and run partitions in PARALLEL sub-agents:
   one sub-agent per partition, each running local_sim with its own `--cases`
   file. Bank sessions are per case, so parallel runs do not interfere.
4. Read every LOCAL FAIL line. Ledger failures are real defects; judge failures
   are indicative. Fix the builder (`builder/gen.py`, `builder/spec.py`),
   regenerate, and rerun locally — no platform window needed.
5. Record the run in `tests/findings.md` with a `--note`-style judgement line.

## Rules

- Local verdicts are a fast approximation of the platform; confirm important
  changes on the platform when it is healthy.
- Never fix the workflow by hand; fix the generator and regenerate.
