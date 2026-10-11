# Inter-agent communication review (session: comm-review)

LIVE: comm-review — comm-review.md — agent build-the-builder-87

## 21:08 (18:08 UTC)
DONE (user request: agents talk via git diffs):
- NEW skill .claude/skills/git-relay/SKILL.md — relay protocol: @<session>: lines in commit bodies, --allow-empty pure notes, agent-mail/<name>.md mailboxes, ack ritual, scoped-add/no-push/no-rewrite rules.
- agent-mail/README.md seeded. agent-notes SKILL.md: LIVE line now carries the ListAgents name + rule 9 cross-refs git-relay. CLAUDE.md: git-relay bullet added.
- First relay commit carries the assignment note to all 4 live sessions; SendMessage sent to each as backup.
OWN: .claude/skills/git-relay/SKILL.md@comm-review
OWN: agent-mail/README.md@comm-review
OWN: .claude/skills/agent-notes/SKILL.md@comm-review
OWN: CLAUDE.md@comm-review
TODO:
- Watch for ack commits from live sessions (git log --grep='ack: git-relay').
- Post-window: watcher tee (see entry below), lock-dir decision.
- Mock URL: unchanged (see self-heal.md). Workflow id: none deployed for final case yet. Time left: ~1h50m.

## 21:12 (18:12 UTC)
DONE:
- ACK status: build-the-builder-11 acked BY MESSAGE (read-only one-shot conformance-checker, produces no files — empty ack commit waived, correct call). Pending commit-acks: cloudflare-mock-deploy-skill, final-case-mock-bank, build-the-builder-e5. Monitor re-armed with subject-only filter (old one false-matched commit BODIES containing "ack: git-relay" — e.g. my own a32be13).
OWN: agent-notes/comm-review.md@comm-review
TODO:
- 3 ack commits still expected; relay-note the stragglers after the monitor window.

## 21:02 (18:02 UTC)
DONE:
- Reviewed all 11 skills + live workspace state (5 claude procs, drive_watch poll owned by a LIVE session, mock_gen full run in background at self-heal).
- Found 4 comm gaps: (1) file ownership is prose not mechanism, (2) no LIVE-session registry → SendMessage targets unknown to new sessions, (3) Monitors are session-local — a dead owner session silently drops NEW/CHANGED events (happened once today), (4) two sessions can race on self_heal output files (low risk).
- FIXED gaps 1+2: agent-notes SKILL.md rules 7-8 (OWN:/OWN-RELEASED: file claims, LIVE:/LIVE-END: session announce) + template; CLAUDE.md logbook bullet points at them. Additive only — running sessions unaffected; new/takeover sessions get the protocol.
TODO (post-window, do NOT touch the running watcher):
- Add `tee -a finalcase/.watch.log` to the case-watch Monitor command so events survive a dead owner session; update .claude/skills/case-watch/SKILL.md step 3 accordingly.
- Consider a lock dir (agent-notes/locks/) if OWN: lines prove insufficient — decide after the window.
- Mock URL: unchanged (see self-heal.md). Workflow id: none deployed for final case yet. Time left: ~2h.

## 21:37 (18:37 UTC) — input-health audit (user assignment: inputs to builder, format correctness)
LIVE: comm-review/input-health — comm-review.md — agent build-the-builder-87
DONE:
- Flow-drawing audit (statement-debt-call-flow.pdf, 27 branches) on a FRESH gen_query build (/tmp/selfheal/wf_fresh.json, from current gen_query.py + final_spec.json + api_from_services(final_contract.json)): 25/27 present. R2 another-card question BEFORE offer: correct order. R1 full currency names: in.
- GAPS FOUND: (R3) no-statement-yet card (empty cut date) — rule IS in spec (rule_ledger[0].params.no_debt_text) but gen_query DROPS it from the workflow; (R4b) cut-day reading — statement_facts code extracts totalDebt but the statement prompt never switches to it on the cut day; reads last-statement debt instead.
- ROOT CAUSE of R4b spec blind spot: finalcase/sources/meetings/2026-10-10-follow-up-session-transcript.txt downloaded 20:57:02, spec last written 20:51:38 — the late file never reached extraction. Patched final_spec.json: rule_ledger[0].params.cut_today_rule + call_flow[3] field-level totalDebt text.
OWN: tests/final_spec.json@comm-review (cut_today_rule + call_flow[3] patch only — released to next reader)
OWN-RELEASED: tests/final_spec.json — patch landed, byte-stable for the orchestrator's rebuild
TODO:
- @cf-mock-session/orchestrator: gen_query.py needs R3 + R4b before the FINAL rebuild (details in relay commit) — relayed.
- Spawned: update-tracker + sim-tester agents (user assignment).
- Run self_heal b-check replica on wf_fresh.json (no repo writes).
- Mock URL: final-case-mock-bank.fcodefcode3.workers.dev. Workflow d659b17f (pre-fix). Time left: ~1h20m.
