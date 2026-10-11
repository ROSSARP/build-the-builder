---
name: agent-notes
description: Timestamped session logbook — every session in this repo writes what it did and what remains into agent-notes/*.md. Use at the start of work, after every meaningful step, and before ending a turn or handing off.
---

# Agent notes — the shared logbook

All Claude sessions in this repo share one logbook: `agent-notes/`. Each session keeps its own file `agent-notes/<session-name>.md` and appends dated lines. The point: any other session (or a fresh session after a crash/overflow) can read the logbook and continue without replaying transcripts.

## Rules

1. **One file per session.** Name it after what you are doing (`cf-mock`, `orchestrator`, `builder-run`, `validation`). If you take over another session's work, continue ITS file with a `## resumed by <you>` line instead of starting a new one.
2. **Every entry carries a timestamp** (Istanbul local time + UTC): `## 22:10 (19:10 UTC)`.
3. **Each entry has two lists: DONE and TODO.** One line per item, command or file path included where it matters.
4. **Write BEFORE you act** (the TODO you are about to work on) and **again when it lands** (DONE + result). If the session dies mid-action, the TODO line is how the next session knows what was in flight.
5. **Keep entries short.** The logbook is for humans and agents under time pressure — no paragraphs, no transcripts.
6. Also mirror the three project-wide facts that change often: current mock URL, current workflow id, time left until the 20:00 UTC deadline.

## Template

```markdown
# <what this file tracks>

## 22:10 (19:10 UTC)
DONE:
- ...
TODO:
- ...
```

Start a session: read `agent-notes/` first (the freshest file is the freshest state). End a session: write the final entry with an explicit "NEXT:" line for whoever continues.
