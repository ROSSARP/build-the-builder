---
name: page-watch
description: Watch https://www.freyavoice.ai/hackathon (#rules + #submit sections) for content changes and notify the orchestrator + user. Use when the user asks to monitor the hackathon page, or during the final window to catch late rule updates.
---

# Watch the hackathon page for content changes

The organisers may update the rules or the submission instructions while the
window is open. The watcher is `tests/page_watch.py` (stdlib only, urllib). It
hashes the `#rules` and `#submit` sections (plus the whole page) and prints one
line per change. State: `out/hackathon-watch.json` (last-seen hashes, readable
by any session). Run every command from the workspace root.

## Steps

1. Check once (first run just records the baseline silently):

       python3 tests/page_watch.py --once

2. Start the poll loop and surface its events with the harness Monitor. The
   loop checks every 120 s until killed. The Monitor filter deliberately drops
   the clean cycles — silence means "unchanged"; a dead watcher ends the
   stream and the Monitor reports that instead:

       command: python3 tests/page_watch.py 2>&1 | grep --line-buffered -E 'CHANGE:|FAIL:|WARN:'
       description: hackathon page #rules/#submit changes
       timeout_ms: 1800000

   Re-arm the Monitor every 30 minutes (the cap).

3. On every `CHANGE:` line, report the section name to the orchestrating
   session and to the user verbatim (do not paraphrase the page content into
   rules — fetch the section and quote it only when asked). The rule extractor
   re-reads the page only if `#rules` changed; the submission owner only if
   `#submit` changed.

4. Before submitting (mandatory): run `python3 tests/page_watch.py --once`
   once more and confirm the state file's `checked_at` is fresh — a change
   after the workflow export but before the email must be judged and recorded
   in `tests/findings.md`.
