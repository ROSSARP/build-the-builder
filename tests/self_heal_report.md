# Self-healing report — final case window (11 Oct 2026, 17:00–20:00 UTC)

Owner: self-healing agent. Loop: scan `finalcase/` (+ `case-download/`) → extract
`tests/final_contract.json` / `tests/final_spec.json` / `tests/example_checks.json`
→ run `tests/self_heal.py check` (tests a–d) → fix inside ownership → report.

## Cycle 0 — 2026-10-11 17:20–17:35 UTC

- **New files seen**: `finalcase/BRIEF.md`, `finalcase/statement-debt-call-flow.pdf`
  (mirrored by `tests/drive_watch.py sync`; identical copies in `case-download/`).
  Remote Drive folder still has only these two files at 17:22 UTC.
- **State**: `tests/self_heal_state.json` created; manifest tracks both sources.
- **Watcher**: `tests/drive_watch.py sync` running under Monitor (120 s poll).
- **Built**: `tests/self_heal.py` (scan / extract / check / all / mockfull) —
  compiles; `check` runs and reports SKIP until artefacts exist.
  - check (a) contract vs test-customers; (b) gen_query workflow build with a
    dummy mock base + Turkish-only / tool-URL / no-`{{`-in-code / close-corrector
    assertions; (c) mock_gen dry-run + contract-path coverage; (d) 6-example
    replay-spec validation.
- **Intel from the flow drawing** (`statement-debt-call-flow.pdf`, extracted with
  `pdftotext -layout`): stages = IVR handoff → second factor (back to IVR) →
  card list → eligible cards / how many / disambiguation (last 4, last 6 digits)
  → card selected → statement debt per card (read last 4, name, cut-off, due
  date; or no statement debt + total debt) → another card? → TL payment status
  (not paid / minimum-or-more / below minimum) → USD/EUR debt → due date →
  offer: move cut-off date or e-mail the statement → answer branches (nothing
  else / pay debt → IVR transfer to agent / e-mail → registered address read +
  confirm + send or "no suitable address" / cut-off date → shared statement
  (primary vs linked) → read weeks → change? → offer other weeks → new week +
  dates + confirmation) → return to supervisor. The drawing is English-labelled;
  the agent language is Turkish.
- **Builder-interface note**: `builder/gen.py` reads its typed rules from
  `spec["rule_ledger"]` (`{type, params, text}` records, helpers `ledger_records`
  / `ledger_params` / `apply_ledger`), and tools are built by `api_tool()` with
  `function.parameters.url.default = MOCK_URL + path`. `final_spec.json` emits
  `rule_ledger` in exactly that shape so a query-domain generator can reuse the
  helpers.
- **Tests**: none runnable yet (no contract/spec/extract inputs beyond BRIEF+PDF).
  `python3 -m py_compile tests/self_heal.py` — OK.
- **Fixes applied**: none (nothing to fix yet).
- **Open risks**:
  1. The pack (README, sources/, test-environment/, example-scenarios.md,
     cloudflare-mock/) has not landed yet; contract + spec extraction blocked.
  2. `builder/gen_query.py` does not exist yet; check (b) skipped until it
     appears, compiles, and is stable >60 s.
  3. Document disagreements (intentional per BRIEF) — extraction must record
     them in `open_questions` rather than paper over them.

## Cycle 1 — 17:35–17:58 UTC — extraction landed, all four checks green

- **New files seen** (Drive sync → `finalcase/`): the full pack arrived —
  `sources/documents/{2025-08-14-cards-faq, 2026-09-10-ivr-prompt-sheet,
  2026-10-01-service-contract}.md`; `sources/emails/{2026-09-24-kickoff-questions,
  2026-10-09-decisions-recap}.txt` + `attachments/{2026-09-02,2026-10-08}-statement-debt-analysis.md`;
  `sources/meetings/2026-10-07-analysis-session-transcript.txt`;
  `test-environment/{test-customers.json,test-customers.md}`; `example-scenarios.md`;
  `README.md`; `cloudflare-mock/`; `BRIEF.md` changed (the finalcase version is
  current; the older fallback `case-download/BRIEF.md` still describes a richer
  pack — stale, ignored). Drive manifest verified: 26 entries (18 files + 8
  folders), every one mirrored — no bank document is pending.
- **Extracted**: `final_contract.json` (7 services under `/voice/v1`, envelope
  `{"data","call"}` → `{"data","result.returnCode"}`, error codes; check (a)
  PASS against 34 customers joined on `customerNo`), `final_spec.json`
  (`rule_ledger` 9 records, 12-stage call flow, 22 `open_questions`),
  `example_checks.json` (6 scenarios), `self_heal_last_check.json`.
- **Tests before** (17:41Z): a PASS · b FAIL (2 English prompt texts) · c FAIL
  (rc=1 "contract is not OpenAPI JSON") · d PASS.
- **Root cause of b**: the query generator pastes `final_spec.json` rule texts
  verbatim into the workflow's `system_prompt`, `actions.task_message` and
  `week_facts` code vars — and the spec carried the ENGLISH doc prose (the
  bank's documents are English). The Turkish-only requirement therefore failed
  at the spec, not at gen_query.
- **Fixes (all in files I own)**:
  1. `final_spec.json` — translated every consumed rule text to Turkish:
     `query.move_rule_text`, `dates.{validity,weekend,vague,next_weekday}_text`,
     `date_rule.text` + its 5 consumed params, `closing_rule.params.table[].when`
     (16 rows) and `closing_lines`/`no_input_text`/`goodbye_text`. Outcome/reason
     enum keys stay English (platform values, §8.4 names). Originals kept under
     `*_source_en` for audit; gen_query never reads those.
  2. `tests/self_heal.py` — (i) English-leak scan now sentence-level and scoped
     to prompt fields (`system_prompt`, `task_message`, `on_enter`,
     `routing_prompt`, `loop_prompt`, `role_message`); English in parameter
     descriptions (copied from the English contract) is info, never spoken;
     (ii) statuses are FAIL/PASS, warnings stay informational; (iii) check (c)
     regenerates `tests/final_tool_api.json` (OpenAPI shape, `servers[0].url` +
     `/voice/v1/...` path keys) from the contract each run and accepts
     mock_gen's documented `--no-llm` stop (exit code 3); (iv) the
     mandatory-sentence scan strips parenthetical guidance and placeholder
     templates (`[..]`, `XXX`, …); (v) `score` maps document-style service
     descriptions onto the real service names before grepping.
- **Tests after (17:53Z)**: a PASS · b PASS (7 nodes, Turkish prompts; warnings:
  `statement.week.get` unused, `'Sizi ana menüye aktarıyorum.'` not found
  verbatim) · c PASS (analysis stage: all 7 `/voice/v1` paths present in
  `tests/final-mock-dryrun/analysis.json`; rc=3 = the documented no-llm stop) ·
  d PASS · `score`: 6/6 examples PASS (13 service assertions, 0 fail).
- **Open risks**:
  1. gen_query's `week_preview` role resolved to `statement.week.decide` only —
     `/voice/v1/statement.week.get` is never called. `cards.balance` already
     returns `nextStatementDate`/`nextLastPayDate` (example 2's dates), but the
     current `statementWeek` number is not otherwise available. Flag to the
     gen_query owner.
  2. transfer/close services do not exist in the contract (IVR-side per §intro);
     gen_query synthesizes `/transfer_to_human` and `/close_call` — the deployed
     mock must serve them.
  3. Full mock_gen model run for `worker.js` started 17:52Z (out
     `tests/final-mock-dryrun`, log `/tmp/selfheal/mockfull.log`); the dry-run
     check is green without it.
  4. `builder/mock_final.py` (deterministic mock builder, per orchestrator plan)
     has not landed yet.
  5. `builder/gen_query.py` still being edited (133680 B @17:51:54Z) — the
     ownership gate (compiles + size stable >60 s) is not open yet; no patch
     written for it.

