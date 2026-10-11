# Build the Builder — team submission

Our entry to the **Build the Builder** hackathon (kit v3, 10–11 October 2026; domain: debt
collection). This repository contains our **builder**: a program that reads a bank's brief
plus the bank's tool API file and generates a Freya phone-agent workflow. It is a full
pipeline — spec extraction, workflow generation, saving on Freya, testing against practice
customers, prompt-level fixing, export for submission, and a plain-text trace of the run.

No phone agent in `submission/` was edited by hand: each one is the output of a builder run,
with that run's trace in `traces/`.

`SUBMISSION.md` is the Sunday runbook (hidden briefs at 17:00 UTC, submit by 20:00 UTC).

## Quick start

```bash
source env.sh                                            # team Freya key + bank team key (shipped configured)
python3 builder/build.py briefs/brief-a.md tools/openapi.json
```

The run prints the per-case pass/fail table, writes the exported workflow to
`submission/brief-a.workflow.json`, its builder trace to `traces/brief-a.log`, and appends a
dated section to `tests/findings.md`. Re-running is safe: the builder updates the same
workflow in place (one workflow per brief name, so the workspace does not fill up).

## Requirements

- **Python 3.10 or newer.** The builder and all our tooling use the standard library only —
  nothing to `pip install`. (The kit's optional `examples/agent_builder.py` needs
  `claude-agent-sdk`; we do not use it.)
- **Freya API key.** `env.sh` ships the team's (`FREYA_API_KEY`, `FREYA_BANK_TEAM_KEY`,
  `FREYA_API_URL`); `env.example` is the placeholder-only template. Organisers can export
  their own keys instead — nothing in the builder is tied to ours.
- **A working `claude` CLI.** `builder/build.py` makes its model calls by running
  `claude -p <prompt> --output-format json --model <model>` as a subprocess, so it works
  with either:
  - a normal `claude` CLI login, or
  - any Claude-compatible backend configured through the standard environment variables
    `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN` (or `ANTHROPIC_API_KEY`) and
    `ANTHROPIC_MODEL` — reviewers can point it at their own backend without any key from
    us. Our environment points the CLI at a Claude-compatible gateway this way.

  Model-selection details:
  - The model the builder requests is `BUILDER_MODEL` (default `claude-sonnet-5-5`);
    `tests/local_sim.py` requests `LOCAL_SIM_MODEL` (same default). The builder passes
    `--model` explicitly, so a compatible gateway that ignores or remaps the requested
    model name serves the call regardless; if a backend answers `unrecognized_model`, the
    builder retries once without `--model` and the gateway/CLI default applies.
  - Endpoint and auth variables (`ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`,
    `ANTHROPIC_API_KEY`) pass through to the subprocess unchanged.
  - Enclosing-session model overrides (`CLAUDE_MODEL*`, `ANTHROPIC_DEFAULT_*`,
    `CLAUDE_CODE_SUBAGENT_MODEL`, `ANTHROPIC_MODEL`) are filtered out of the subprocess
    environment, so a Claude Code session the builder runs inside cannot change the model
    the builder asked for.

## The exact run command

```
python3 builder/build.py {brief_path} {tool_api_path}
```

- `{brief_path}` — the brief `.md` to build from. Every sibling `*.md` in the same folder is
  passed to the extractor; the named file is marked `(TARGET)`, siblings are context only
  (used when the target brief says it builds on or extends another brief). The file's stem
  is the run slot: `briefs/brief-a.md` → `submission/brief-a.workflow.json`,
  `traces/brief-a.log`.
- `{tool_api_path}` — optional. When omitted, a sibling `*.openapi.json` is used, else
  `tools/openapi.json`.
- Flags: `--no-fix`, `--fix N` (default 1), `--reps N`, `--cases FILE` (test on a custom
  case file), `--fix-only` (test/fix the currently published workflow).
- Hidden-brief style run (Sunday, keeping everything printed):
  `python3 builder/build.py <brief_path> <tool_api_path> 2>&1 | tee traces/<name>.log` —
  see `SUBMISSION.md`.

## Artifacts

| Path | What it holds |
|---|---|
| `submission/` | Exported phone-agent workflows (`freya.export_workflow`, one per run) and `form.json`. |
| `traces/` | One plain-text builder trace per run: start/end UTC, every model call (model, purpose, sizes, seconds), Freya workflow/agent ids and published versions, test results, export path. |
| `results/` | Per-run local test output written by `run_cases.py` (regenerated; not committed). |
| `tests/findings.md` | Dated log of every builder run: command, ids, score, per-case failures, artifacts. |
| `tests/best.json` | Best practice score per slot across runs; a later weaker run re-publishes the stored best instead of regressing. |

## Architecture

Pipeline in `builder/build.py`, LLM work in `builder/spec.py` (prompts, spec validation) and
deterministic generation in `builder/gen.py`:

1. **extract** — one LLM call reads all sibling briefs + the tool API and returns a
   structured spec: identity questions, dates/holidays/bands, amounts, persuasion, notes,
   products, closing table, with rule sentences copied from the brief. The spec is validated
   before use and retried once if unusable.
2. **generate** — code (no LLM) turns the spec + tool API into a workflow JSON: nodes,
   tool wiring and response mappings, transitions with conditions, and code nodes. The
   mechanism is fixed; every value that can change between briefs comes from the spec or
   the API file.
3. **save** — `freya.validate_workflow` (dry run), then `freya.save_workflow`: create once
   per slot, update and publish in place afterwards (a plain update does not publish).
4. **test / fix** — for practice briefs, `tools/run_cases.py` scores the saved agent. Each
   fix pass sends the failures to the LLM and accepts **prompt-text-only patches**
   (`task_message`, `routing_prompt`, `on_enter.text`); structure, tools and transitions
   cannot change. Patches must fix rules, never bake in test-case values (no dates, amounts
   or names from cases). The best-scoring version across passes — and across runs,
   `tests/best.json` — is re-published and exported.
5. **export / trace** — `freya.export_workflow` to `submission/<slot>.workflow.json`, a
   plain-text trace to `traces/<slot>.log`, and a dated section appended to
   `tests/findings.md`.

**Deterministic date pipeline.** The LLM only extracts rule text and never does date
arithmetic: relative expressions are anchored to the platform's call-time `{{now}}`
variable, and all calendar work runs in code nodes generated by `builder/gen.py`
(`dates_code`, `fix_date_code`) — business-day/holiday math, deadline bands, per-product
deadline clamping, "one date for everything", weekend/holiday correction and the
"date after the deadline" rejection. The same rules therefore apply identically on every
call, on any calendar the brief defines.

## Test tooling

| Tool | What it does |
|---|---|
| `tools/run_cases.py` | Runs cases against an agent on Freya (`--brief A|B`, `--cases FILE`, `--reps N`, `--style ...`) and prints pass/fail with reasons; `tools/score.py` is the platform's ledger scorer. |
| `tests/run_custom.py` | Runs large custom case files in id-safe batches (`tests/exam-*.json`, `tests/custom-30.json`, slices) with stuck-simulation cancellation. |
| `tests/local_sim.py` | Local simulator, no Freya simulations: real bank mock, the platform's own `score_ledger` for exact ledger verdicts, LLM agent/customer/judge for approximate dialogue. Fast iteration and platform-outage fallback. |
| `tests/platform_check.py` | Platform health, running/stuck simulations, cancel, outage signature. |
| `tests/make_*.py`, `report_exam.py`, `validate_exam_cases.py`, `log_run.py`, `pull_calls.py`, `salvage.py`, `case_math.py` | Case generation/validation, run reporting, transcript pulling, result salvage. |
| `.claude/skills/` | The agent-facing skills used to drive the work: `build-phone-agent`, `test-builder`, `platform-check`, and the mock-exam set (`mock-exam-generate`, `-run`, `-local`, `-report`, `-improve`). |

Mock exams: `mock-exam/exam-1..3/` each hold a brief and its own tool API; run one with
`python3 builder/build.py mock-exam/exam-N/exam-N.md mock-exam/exam-N/tools.openapi.json`.
Every builder run is logged to `tests/findings.md`; the judgement lines (what changed, what
to try next) come from the `test-builder` / `mock-exam-*` skills.

---

## Organiser kit README (unchanged, for reference)

The text below is the kit's original `README.md`, kept here so nothing from the kit is
lost. Our submission documentation is the part above this line.

# Build the Builder

**Kit version 3** (10 October 2026). The file `VERSION` holds the number. When we update the kit, the number goes up and the changes are listed here.

- v3: the example builder waits for its own test run (up to 20 minutes per command) instead of stopping before the results arrive. On Brief A it built an agent that passed 10 of the 10 practice customers in one run.
- v2: `examples/base-agent.json` (an example phone agent) and `examples/agent_builder.py` with the skill `.claude/skills/build-phone-agent` (an example builder) replace `examples/minimal_builder.py`.
- v1: first release.

You write a **builder**: a program that reads a bank's brief and creates a phone agent on Freya.
We put that phone agent in front of simulated customers. The share it handles correctly is your score.

One simulated customer is one case. A step of a phone agent is called a node in the platform's documents.

## The ten-minute start

You need Python 3.10 or newer.

```bash
cp env.example env.sh        # put your Freya API key in it, and a team key you make up
source env.sh

# 1. Put the example agent on Freya and test it. It prints {"workflow_id": ..., "agent_id": ...}
python3 -c "import freya,json; print(freya.save_workflow('base', json.load(open('examples/base-agent.json'))))"
python3 tools/run_cases.py <agent_id> --brief A            # ten practice customers, 3 to 11 minutes

# 2. Let the example builder build one from the brief
pip install claude-agent-sdk
python3 examples/agent_builder.py briefs/brief-a.md
python3 examples/agent_builder.py briefs/brief-a.md briefs/brief-b.md   # Brief B builds on Brief A, so pass both
```

`run_cases.py` prints one line per customer: pass or fail, the tool calls the agent made, and the reason for a failure.

`examples/base-agent.json` is an agent, not a builder. It is the same two-step workflow that is already in your workspace: check identity, then take a payment promise. It uses four of the seven tools, so it handles only the simplest customers: in one run it passed 2 of the 13 practice customers. Read it to see what a valid workflow looks like.

`examples/agent_builder.py` is a builder. It runs Claude through the Claude Agent SDK with one skill, `.claude/skills/build-phone-agent/SKILL.md`. Claude reads the brief and the tool API file, writes the workflow, runs the practice customers and fixes what fails. The skill is short on purpose. Your job is a better builder: a better skill, more skills, your own code, or another agent altogether. It needs a Claude login or `ANTHROPIC_API_KEY`.

## What is in this kit

| Path | What it is |
|---|---|
| `briefs/brief-a.md` | Freya Bank's specification for customers late on one product. 47 rules. Read all of it. |
| `briefs/brief-b.md` | The extra rules for customers with up to three products. It builds on Brief A. |
| `tools/openapi.json` | The bank's tool API that the phone agent calls during a call. |
| `public-test-set.json` | 13 practice customers: what each one does and what the bank's records must show afterwards. |
| `examples/base-agent.json` | An example phone agent: two steps, four tools. The same one that is in your workspace. |
| `examples/agent_builder.py` | An example builder on the Claude Agent SDK. Claude builds, tests and fixes the agent. |
| `.claude/skills/build-phone-agent/SKILL.md` | The one skill the example builder uses. |
| `freya.py` | A small client for the Freya API. Standard library only. |
| `tools/run_cases.py`, `tools/score.py` | Run the practice customers against a phone agent and score it. |
| `docs/workflow-format.md` | What a phone agent is made of: steps, prompts, variables, routes. |
| `docs/tools-and-code.md` | Tools that call an API, code steps, hooks, where a tool's response lands. |
| `docs/api.md` | The API calls a builder needs. |

## How you are scored

A customer counts as handled when all of these hold:

1. **Outcome: the bank's records are right.** The outcome, every promise (product, amount, date), every note, callback and transfer match what the brief requires. The scorer reads them from the bank, not from what the agent said.
2. **Policy: the conversation stayed inside the brief.**
3. **Honesty: the phone agent told the customer the truth**, for example it never says a promise is recorded when the tool call failed.

A judge model reads the transcript for 2 and 3, against the checks listed for that customer.

There is no partial credit. Your score is the share of customers handled.

The same phone agent can pass a customer in one run and fail it in the next. Treat one green run as a hint, not as proof.

## The final

- On Sunday we publish briefs you have not seen. They are the same kind of call with different rules: other numbers and limits, other identity questions, another outcome table, another calendar. Their form can differ too: one final brief is a clean specification, the other is raw bank material (a mail, a policy extract, a memo that changes it, a code list).
- Each final brief comes with its own tool API file. The seven tool names stay the same. The fields and the allowed values can change.
- After the final briefs open you may fix a bug in your builder. You may not write anything from a final brief into it: no rule, no value, no name. Fixing a crash on a table your parser did not expect is allowed. Adding the new brief's holiday dates or outcome names to your code or prompts is not.
- You run your builder once on each, with no manual step, and submit the phone agents it created, your code and the builder's trace.
- You export each phone agent to a file with `freya.export_workflow(workflow_id, "<brief>.workflow.json")` and submit those files. We load them into our own workspace to test them, so what you export is what we score.
- We test those phone agents on customers nobody has seen, on several calendar days, three times each. A customer counts only when all three runs pass. A phone agent that is right most of the time is not right.
- Final customers can have up to three products, as in Brief B.
- Final customers talk like people. They give a number in two parts, correct themselves, talk about other things, ask a question back, or say amounts and dates in words. The facts stay the same. Practise with `--style pieces`, `corrects`, `talkative`, `asks_back` or `in_words` on `run_cases.py`.

So build something that reads a brief, not something that knows this one. Whatever your builder can take from the brief, it should take from the brief.

## Rules

- Your builder takes brief files as input and creates the phone agent with no manual step. Do not edit a phone agent by hand after it is created.
- The phone agent runs on the model set in `freya.py` (`AGENT_LLM`). Do not change it. Your builder may use any model or coding agent.
- The phone agent may call only the bank's tool API. Code steps and hooks inside the workflow are allowed and expected.
- Use `freya.save_workflow(...)` or update your workflow in place. A workspace holds 200 workflows. A builder that creates a new one on every run fills it up and leaves you with a list nobody can read.
- One simulation runs at a time per workspace. A ten-customer run takes 3 to 11 minutes. A second `run_cases.py` started meanwhile waits for the first.
- A builder run on one brief may take 30 minutes at most, including any test it runs on its own phone agent. You may run it more than once and submit the phone agent of one run, with that run's trace.
- Equal scores are ranked by the total promised amount on the customers that passed, then by shorter build time, then by earlier submission.
- Your builder must leave a trace of each run: start and end time, each model call it made (model and a one-line purpose), what it created on Freya, and any test it ran on its own agent. Plain text, no fixed format. You submit one trace per final brief.
- All data here is synthetic. Do not bring real customer data.

## When something does not work

- `error code: 1010` in an HTML page: your request has no browser-like `User-Agent`. `freya.py` sets one.
- `Workspace plan limit reached`: you created too many workflows. Update one in place.
- You changed your builder and the score did not move at all: an updated workflow must be published before a simulation uses it. `freya.save_workflow` publishes. A plain `PUT` does not. See "Update a workflow" in `docs/api.md`.
- A customer fails and you do not see why: `freya.get_call(call_id)["messages"]` is the full transcript with the tool calls. `run_cases.py --out results/run.json` saves the call id of every customer.
- Calls end as `customer-ended-call` before the phone agent is done: it was silent too long and the customer hung up, as a person would. `run_cases.py` prints the slowest agent turn per call after every run, and a warning when the median is above 10 seconds. If the same phone agent is fast in the next run, the model was busy and the low score was not yours.
- You want to see what your phone agent says without waiting for a simulation: `POST /api/v2/chat/message` runs one turn at a time. See `docs/api.md`.
- The bank answers `unknown product_id`: the model made an id up. Product ids come from `get_account` (`p1`, `p2`, ...). Give them to the model in the tool result, or fill them in with code.
- A simulation stays at "running" and no call ever starts: the workflow cannot start a call. Try one chat turn. Leave `agent_config` out of the workflow you send.
- The agent says nothing after a tool call and the customer hangs up: see "Tool results and the next turn" in `docs/tools-and-code.md`.
