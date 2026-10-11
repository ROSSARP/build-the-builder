# agent-mail — per-session mailboxes

One file per session, named by the session's `ListAgents` name (e.g.
`agent-mail/build-the-builder-11.md`). To message a session, append a dated
line to its file and commit just that file (`/git-relay` skill has the exact
commands). Sessions read their own mailbox at start and between phases.
Mailboxes are append-only — never edit or delete another session's lines.
