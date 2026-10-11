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

## 21:02 (18:02 UTC)
DONE:
- Reviewed all 11 skills + live workspace state (5 claude procs, drive_watch poll owned by a LIVE session, mock_gen full run in background at self-heal).
- Found 4 comm gaps: (1) file ownership is prose not mechanism, (2) no LIVE-session registry → SendMessage targets unknown to new sessions, (3) Monitors are session-local — a dead owner session silently drops NEW/CHANGED events (happened once today), (4) two sessions can race on self_heal output files (low risk).
- FIXED gaps 1+2: agent-notes SKILL.md rules 7-8 (OWN:/OWN-RELEASED: file claims, LIVE:/LIVE-END: session announce) + template; CLAUDE.md logbook bullet points at them. Additive only — running sessions unaffected; new/takeover sessions get the protocol.
TODO (post-window, do NOT touch the running watcher):
- Add `tee -a finalcase/.watch.log` to the case-watch Monitor command so events survive a dead owner session; update .claude/skills/case-watch/SKILL.md step 3 accordingly.
- Consider a lock dir (agent-notes/locks/) if OWN: lines prove insufficient — decide after the window.
- Mock URL: unchanged (see self-heal.md). Workflow id: none deployed for final case yet. Time left: ~2h.
