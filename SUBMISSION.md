# Submission — the final (one case, three hours)

The final is **one case**: Freya Bank's credit card statement-debt line, in **Turkish**.
The case folder opens **Sunday 17:00 UTC** (20:00 Istanbul); submission closes **Sunday 20:00 UTC**
(23:00 Istanbul). Results after review.

## Steps inside the window

1. Download the zip (link or e-mail). Read `BRIEF.md` first; `README.md` in the package says
   what each document is. Unzip into its own folder.
2. **Write and deploy the bank mock FIRST** — `python3 builder/mock_gen.py <case_folder> --deploy`
   (Cloudflare Workers; deploy uses your CF token). Health-check it. Keep it running until the
   results are out: a down or wrong mock fails the conversations that reach it.
3. Run the builder on the folder; keep everything it prints (that is your trace):
   ```
   python3 builder/build.py FreyaBank-Ekstre-Borc/ https://your-mock.your-subdomain.workers.dev 2>&1 | tee traces/final.log
   ```
   You may run it more than once. Submit ONE phone agent, with the trace of the run that made it.
   Never edit the agent after the run.
4. Export: `freya.export_workflow(<workflow_id>, "submission/final.workflow.json")` (the builder's
   case mode writes `submission/final-submission.json` automatically). COMMIT the workflow file
   and the trace.
5. Before 20:00 UTC, send `submission.json` to the address in the kit email. Schema:
   `team`, `members: [{name, email}]` (solo teams list one member), `repo`, `commit`,
   `run_command`, `workflow`, `trace`, `mock_url`.

## Rules to remember

- The three hours are for running the builder and fixing bugs, NOT for tuning it to the case.
- Nothing from the case folder may be written into the builder (reviewers check the commit).
- The trace is not scored but must show: start/end time, every model call (model + one-line
  purpose), what was created on Freya (workflow id, agent id, steps, tools), any self-test with
  its result. Plain text, no API keys.
- The phone agent runs on the Freya LLM (the one set in freya.py). The builder may use any model.
- One simulation at a time per workspace; 200 workflows (update in place).
