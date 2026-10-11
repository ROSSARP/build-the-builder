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
