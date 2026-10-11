---
name: git-relay
description: Pass notes between the parallel Claude sessions sharing this working tree through git — addressed @-lines in commit messages and agent-mail/ mailbox files. Use whenever you need to tell, ask, warn or hand over to another session, and to read mail addressed to you at session start and between phases.
---

# Relay notes between sessions through git

All sessions share ONE working tree on `main`, so a local commit is instantly
visible to everyone — no push, no pull. A relay note is either an `@<session>:`
line in a commit body, or a dated line in the target's mailbox file
`agent-mail/<session>.md`. The logbook (`/agent-notes`) stays the durable
handoff; git-relay is the live channel: quick, addressed, acked.

Your relay address is your session name as `ListAgents` shows it (e.g.
`build-the-builder-11`) — mirror it in your logbook's `LIVE:` line.

## Send a note

1. Short note, own change landing anyway: make the commit and put the note in
   its body. Stage ONLY files you own — never `git add -A` / `git add .`
   (other sessions' in-flight work lives in the same dirty tree):

       git add <your-files> && git commit -m "<area>: <what changed>

       @<target-session>: <one-line note — instruction, warning, question>
       ACK-REQ"

   - `@<session>:` lines are the notes; one line per note, repeat the prefix
     for several targets.
   - Append `ACK-REQ` when you need a reply.
   - A `NEXT: <action>` line hands over a concrete next step.
2. Pure message, nothing to commit:

       git commit --allow-empty -m "relay: <you> -> <target>: <note>"
3. Longer message (instructions, a decision, background): append a dated line
   to the target's mailbox and commit just that file:

       printf '\n## %s from %s — %s\n%s\n' "$(date '+%H:%M %Z')" "<you>" "<subject>" "<body>" >> agent-mail/<target>.md
       git add agent-mail/<target>.md && git commit -m "mail: <you> -> <target>: <subject>"

## Read your mail

At session start, between phases, and before touching any shared file:

    git log --oneline -15                     # what just landed
    git log --grep='@<my-session>' -i -10     # notes addressed to you
    cat agent-mail/<my-session>.md 2>/dev/null # your mailbox
    git diff --stat                            # others' work in flight right now

Ack every `ACK-REQ` with a one-line commit (`ack: <topic> — <you>`) or a
logbook DONE line, so the sender knows you saw it. Un-acked notes older than
10 minutes: SendMessage the target as a backup.

## Before editing a shared file

`git diff <path>` first — it shows what other sessions changed in flight.
Pair it with the `OWN:` lines in the logbook: never edit a file carrying
someone else's live OWN claim, and never build on top of their uncommitted
diff — relay them a note instead.

## Rules

- Commit message = medium. First line says what changed; the body carries
  the `@notes`. Keep notes one line each; no transcripts, no case data.
- Scoped adds only. Never stage another session's uncommitted files.
- No branch switches, rebases, resets, checkouts, no push — fast-forward
  commits on `main`, local only (the remote is the human's call).
- `git commit` refused over `index.lock`: another session is committing —
  wait 2 s and retry. A lock older than ~2 min with no `git` process alive
  (`ps aux | grep 'git commit'`) is stale: remove it and retry.
- Sweep secrets before committing:
  `grep -rnE "cfat_|cfut_|Bearer [A-Za-z0-9]{20,}" <staged-files>` must be
  empty. `env.sh` and `.claude/settings.local.json` stay uncommitted
  (gitignored).
- A note needing a human decision goes to the human; relay the answer back
  with a commit.
