---
name: case-watch
description: Watch the public final-case Google Drive folder, mirror the case pack into finalcase/, and notify the orchestrator about NEW/CHANGED documents so the mock generator and rule extractor can re-read them. Use at the start of the final window and re-run it during the first hour, because the bank keeps adding documents.
---

# Watch the final-case Drive folder

The final case pack is a PUBLIC Google Drive folder:

    https://drive.google.com/drive/folders/1r9KOek3SXiE0mu1wBofezD0bjiAJhcYQ

(folder id `1r9KOek3SXiE0mu1wBofezD0bjiAJhcYQ`). The bank ADDS documents to it
during the first hour of the window, so no single listing is final.

The watcher is `tests/drive_watch.py` (stdlib only, urllib). It maintains the
mirror `finalcase/` at the workspace root plus `finalcase/.manifest.json`
(`{file_id: {name, kind, size, path}}`), detects changes by id + name + size,
and NEVER deletes local files. Run every command from the workspace root.

## Steps

1. Show the current tree:

       python3 tests/drive_watch.py list

   Folders and files are both listed (files, then any folder's contents).
   Expected pack at the end: `README.md`, `BRIEF.md`,
   `statement-debt-call-flow.pdf`, `example-scenarios.md`, `sources/emails/...`,
   `sources/documents/...`, `sources/meetings/...`, `test-environment/...`,
   `cloudflare-mock/...`.

2. Sync once and read the event lines:

       python3 tests/drive_watch.py sync --once

   Output lines: `NEW: finalcase/<path>` / `CHANGED: finalcase/<path>` (one per
   file) and `sync done: N new, M changed`. Files land directly in `finalcase/`
   — that IS the copy step; other agents read them from there. A `FAIL: <path>
   <reason>` line means one file could not be downloaded: report that exact
   name and reason to the user (they can fetch it in a browser), and continue
   with the rest of the pack. A healthy re-run prints `sync done: 0 new,
   0 changed`.

3. Start the polling watcher and surface its events with the harness Monitor.
   The default mode syncs once, then polls every 120 s until killed:

       python3 tests/drive_watch.py sync          # poll loop (--interval N to change)

   Monitor it so each event becomes a chat notification (re-arm every 30 min,
   the Monitor cap):

       command: python3 tests/drive_watch.py sync 2>&1 | grep --line-buffered -E 'NEW:|CHANGED:|FAIL:|sync done:|WARN:'
       description: final-case Drive NEW/CHANGED events
       timeout_ms: 1800000

   The `sync done: 0 new, 0 changed` heartbeat proves the watcher is alive.

4. On every NEW/CHANGED event, NOTIFY the orchestrating session (SendMessage to
   the main/orchestrator agent, or the Monitor event itself is the notice) with
   the exact repo-relative file list, e.g.:

       NEW: finalcase/sources/emails/2025-...-complaint.eml
       NEW: finalcase/cloudflare-mock/worker.js

   Say which agents must re-read them: the mock generator re-reads
   `finalcase/cloudflare-mock/**` and `finalcase/sources/**`, the rule
   extractor re-reads `finalcase/sources/**`, `finalcase/example-scenarios.md`
   and `finalcase/BRIEF.md`. Do not paraphrase content — send ids/paths only.

5. Re-check before finishing (mandatory). The bank adds documents during the
   first hour: before declaring the case pack complete, run
   `python3 tests/drive_watch.py sync --once` once more; if it reports NEW or
   CHANGED, notify the orchestrator again and have the affected agents re-read.
   Only when a fresh listing is unchanged (`0 new, 0 changed`) is `finalcase/`
   current. If the window is still inside the first hour, keep the poll loop
   from step 3 running.

## Recovery

- `WARN: cannot list folder <id>` or `WARN: empty listing` — transient network
  or Drive throttling; keep polling, the next cycle retries. The alternative
  embedded-view endpoints (`?id=<id>` without `#list`, then `#grid`) are tried
  automatically.
- `FAIL: <path> ...` — one file only; everything else still syncs. Reason
  strings: `quota exceeded by Google Drive`, `permission denied (access
  request required)`, `sign-in required`, `download-confirm page could not be
  followed`, `truncated download (N/M bytes)`.
- Different destination for a test run: `python3 tests/drive_watch.py sync
  --once --dest /tmp/other-mirror`.
