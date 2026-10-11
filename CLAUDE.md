# Build the Builder — repo rules for every Claude session

Final window: 17:00–20:00 UTC (20:00–23:00 Istanbul), submit to yavuz@freyavoice.ai. Read `FINAL_RUNBOOK.md` for the plan; run `/agent-notes` for the shared logbook (`agent-notes/*.md` — read the freshest file first, write DONE/TODO with timestamps).

## Context guardrails (the orchestrator session died of a 1M-token overflow — do not repeat it)

1. **Never Read a file over ~40 KB into context.** Summarize big files with `python3 -`/`jq`/`grep` instead. `finalcase/test-environment/test-customers.json` is 707 KB — always access it via code, never Read it.
2. **Compact proactively.** If a session's context passes ~60% of the limit, stop and write a full handoff note to `agent-notes/`, then `/compact` (or end the session and let a fresh one resume from the logbook).
3. **Monitors stay tiny.** Monitor/monitor-like event lines must be short paths/status only (`NEW: path`, `sync done: ...`), never file contents.
4. **No marathon sessions.** Yesterday's session ran ~28 h and died mid-window. End a session once a phase is done; a new session resumes from `agent-notes/` + `tests/findings.md` + memory in minutes.
5. **Never commit secrets.** `env.sh` and `.claude/settings.local.json` are gitignored; sweep `cfat_|cfut_|Bearer` before any commit.

## State on disk (the single source of truth between sessions)

- `agent-notes/*.md` — who did what, what is next (the logbook; claim shared files with `OWN:` lines and announce your session with `LIVE:` — see the agent-notes skill)
- Live inter-agent notes go through git: `@<session>:` lines in commit bodies + `agent-mail/<session>.md` mailboxes (see the `git-relay` skill; scoped `git add` only, never `-A`, no push)
- `tests/self_heal.py` — scan/extract/check/all/mockfull/score harness; `tests/self_heal_last_check.json` — last check results
- `tests/final_contract.json` / `tests/final_spec.json` / `tests/example_checks.json` — extracted case artefacts
- `tests/findings.md` — every run's record + judgement
- Memory (`~/.claude/projects/.../memory/`) — cross-session facts
