# SUBMISSION.md — Sunday runbook

Hidden briefs open **Sunday 17:00 UTC**; submission closes **20:00 UTC**. Two hidden briefs
arrive, each with its own tool API file. You run the builder **once per brief** (reruns are
allowed — submit one phone agent per brief with the trace of the run that made it) and send
the form to the address in the kit email before the close.

## Before 17:00 — pre-flight (do this once, well before the briefs arrive)

1. `source env.sh` — team Freya key + bank team key.
2. `python3 tests/platform_check.py health` — platform responds; if not, check again later
   (piecemeal failures are normal, see the `platform-check` skill).
3. `python3 builder/build.py --help` — the builder starts and prints usage.
4. Optional rehearsal with the local practice hidden brief (kept out of the repo):
   ```
   python3 builder/build.py hidden-demo/hidden-1.md hidden-demo/hidden-1.openapi.json 2>&1 | tee /tmp/rehearsal.log
   ```
   Confirm `submission/hidden-1.workflow.json` is rewritten and `/tmp/rehearsal.log` shows
   the run. Do not reuse `hidden-1` as a real brief slot unless you want to overwrite it.

## When the briefs arrive (17:00)

1. Save each brief and its tool API in **its own folder** under `briefs/`:
   ```
   briefs/hidden-1/hidden-1.md      briefs/hidden-1/hidden-1.openapi.json
   briefs/hidden-2/hidden-2.md      briefs/hidden-2/hidden-2.openapi.json
   ```
   The folder matters: the extractor reads every sibling `*.md` in the brief's folder as
   context. Isolating each brief keeps the practice briefs and the other hidden brief out
   of the extraction. The file stem (`hidden-1`) is the run slot → `submission/hidden-1.workflow.json`
   and `traces/hidden-1.log`.

2. Run the builder once per brief, one at a time, keeping everything it prints:
   ```
   python3 builder/build.py briefs/hidden-1/hidden-1.md briefs/hidden-1/hidden-1.openapi.json 2>&1 | tee traces/hidden-1.log
   python3 builder/build.py briefs/hidden-2/hidden-2.md briefs/hidden-2/hidden-2.openapi.json 2>&1 | tee traces/hidden-2.log
   ```
   - Budget: **30 minutes maximum per brief**, including any test the builder runs on its
     own agent. A hidden run is normally a few minutes (one extract call + generation +
     save + export; no practice tests — hidden customers do not exist to test against).
   - The builder also writes its own trace to `traces/<slot>.log` at the end — the same
     path the `tee` targets. After each run, open `traces/hidden-1.log` and check it
     contains the builder's trace lines (`start:` / `model call:` / `freya:` / `export:` /
     `end:`). If the tee'd console output overwrote them, the authoritative copy is what
     the builder wrote last; fix the file before committing.
   - Do **not** pass `--cases` with Brief A/B practice cases for a hidden brief: the fix
     loop would tune prompts against the wrong rules. If a run crashes, fix the bug in the
     builder and rerun — not the phone agent.
   - One simulation at a time per workspace; do not run the two briefs concurrently.

3. Check after each run: `submission/hidden-N.workflow.json` exists and is valid JSON, and
   the trace ends with `end: ... UTC`. You may run again and keep the best agent, but the
   submitted trace must be from the run that produced the submitted agent.

## Fill and send the form (before 20:00 UTC)

1. Commit the results so the submitted commit contains them: `submission/`, `traces/`,
   `tests/findings.md`. The phone agents must come out of that commit with **no manual
   edits**.
2. Fill `submission/form.json` (shape already in place):
   - `team` — your team name.
   - `repo` — the repository URL.
   - `commit` — `git rev-parse HEAD` of the submitted commit.
   - `run_command` — `python3 builder/build.py {brief_path} {tool_api_path}` (unchanged).
   - `workflows` / `traces` — point at `submission/hidden-1.workflow.json`,
     `submission/hidden-2.workflow.json`, `traces/hidden-1.log`, `traces/hidden-2.log`
     (adjust if the hidden briefs were named differently).
3. Send the form to the address in the kit email **before 20:00 UTC**. Plain text is fine.

## Rules to remember

- **No manual agent edits.** Every submitted workflow is the file the builder exported; the
  run's trace must match it. Reviewers rerun the builder at the submitted commit and
  compare.
- **Nothing from a hidden brief into the builder.** After the briefs open you may fix bugs,
  but no rule, value, name, outcome, holiday or date from a hidden brief may enter the
  code, prompts or skills. A reviewer checks the commit for exactly that.
- **30-minute budget per brief**, including the builder's own tests.
- **One simulation at a time** per workspace (the workspace limit is 200 workflows — the
  builder updates in place, so reruns do not create new ones).
- **Remove API keys from artifacts.** Traces and submissions must not contain keys. Check
  `traces/*.log` and `submission/*.json` before committing. (`env.sh` is the deliberate
  exception: it ships the team's keys because this repository is private — keep it private,
  and rotate the keys before any wider sharing or if visibility changes.)
- Equal scores are ranked by promised amount on passed customers, then shorter build time,
  then earlier submission — send early, before the 20:00 close.
