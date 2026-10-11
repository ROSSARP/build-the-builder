# Build the Builder

Build an AI agent that builds other agents on Freya.

October 10 and 11, online. Solo or in teams of two. First place gets a Combinator interview.

You build an agent. It builds an agent. We test that agent.

*This file is the event page consolidated into one document. For the kit itself, start with `README.md`.*

## Key facts

| | |
|---|---|
| Format | Online |
| Domain | Debt collection |
| Conversations | Text |
| Practice cases | 13 |
| Metric | Pass rate |
| Start | Saturday 10:00 UTC — kit and keys; build against the 13 practice cases |
| Final case | One: Freya Bank's credit card statement-debt line, in Turkish |
| Final opens | Sunday 17:00 UTC (20:00 Istanbul) — download the case folder |
| Close | Sunday 20:00 UTC (23:00 Istanbul) — submit |
| Results | After review |

Register on YC. Your Freya account and the support channel arrive by email at the start.

## What this is

A bank has customers who are late on a payment. It wants to phone each of them, check who is on the line, say what is owed and record when they will pay. On Freya, software makes that call instead of a person.

```
Phone agent   Your credit card has 420 dollars past due. Can you pay today?
Customer      Not today. I can do it on Friday.
Phone agent   420 dollars on Friday the sixteenth. Do you confirm?
Customer      Yes.

create_promise  420.00  2026-10-16   recorded in the bank's system
```

A piece of one call. The last line is what the bank's system keeps. We check that record, and we check the conversation.

That software does not know the bank's rules by itself. Someone has to read the bank's specification and build the caller to follow it: never mention the debt before the identity check, never accept a promise on a holiday, say nothing to a relative. Today a person does this by hand, and one bank takes days.

The question of this hackathon: can a program do that work instead?

### Three words

- **Phone agent** — the software that talks to the customer. It lives on Freya as a workflow: steps, prompts and tools.
- **Brief** — the bank's specification for these calls: who to ask for, how to check identity, which payment dates are allowed, how to close the call.
- **Builder** — the program you write. It reads a brief and creates the phone agent. Nobody edits the phone agent by hand.

You write the builder. We score the phone agent it creates.

| Brief | Your builder | Phone agent | Our benchmark |
|---|---|---|---|
| policies | reads the brief | a workflow on Freya | simulated customers |
| tool API docs | creates the phone agent | conditional routes | talk to the phone agent |
| practice customers | tests and improves it | tool calls | we read the bank's records |
| | *the part you write* | | score = cases passed / cases run |

A new brief goes in, a different phone agent comes out, no edits by hand. The builder must work alone: one command, a brief as input, a phone agent as output. No manual edits after it runs.

One run. You write the orange box. Everything else is provided.

## How the weekend goes

1. You download the kit from the Data tab. Two briefs, the bank's tool API, thirteen practice customers, the Freya workflow reference and a small working builder.
2. You run the sample builder. It creates a phone agent on Freya in your workspace.
3. You test that phone agent. Simulated customers talk to it in text. You see which ones it handled correctly and why the others failed.
4. You write your own builder and repeat steps 2 and 3 as often as you like.
5. Sunday 17:00 UTC: the final opens. One case: Freya Bank's credit card statement-debt line, in Turkish. You download one zip of the bank's documents. Read `BRIEF.md` first; `README.md` says what each document is.
6. You write and host the bank's mock on Cloudflare Workers, from the service contract and the test customers. Deploy it before you run the builder, and keep it running until the results are out: the phone agent's tools call your mock, and a mock that is down or wrong fails the conversations that reach it.
7. You run your builder on the folder and keep everything it prints. That printout is the trace. You may run it more than once, but you submit one phone agent, with the trace of the run that made it, and you never edit the agent after the run.

```
We give the evidence.       The bank's documents: BRIEF.md, README.md, an analysis, a flow
                            drawing, announcements, a service contract, test customers,
                            Q&A, 6 example conversations.
Your builder does the       Reads, builds, tests and fixes, against your own mock on
construction.               Cloudflare Workers. Then it submits the workflow JSON and the
                            trace.
We run the evaluation.      Hidden simulated customers on the Freya LLM, in our workspace.
                            Their tools call your mock. We review the workflow; the trace
                            is read, not scored.
```

```
Start, Sat 10:00 UTC        Final opens, Sun 17:00 UTC            Close, Sun 20:00 UTC
kit and keys                download the case folder              submit
build against the 13        write and deploy the mock
practice cases              run your builder
                            ────────────────────────────────
                            Results: after review
```

The three hours in orange are for running your builder on the final case and fixing bugs, not for tuning it to that case.

### What counts

- The final is one case your builder has never seen, in Turkish. A builder tuned to the practice briefs does not win.
- You may fix a bug in your builder during the three hours. You may not write anything from the final case into it: no rule, no value, no name. Fixing a crash on a table your parser did not expect is allowed. Adding the case's holiday dates or outcome names to your code or prompts is not.
- The phone agent gets the date and time of the call as a variable, `now`. Every date rule uses it.
- Every phone agent runs on the same Freya model. Your builder may use any model or coding agent you like.

## Inside a phone agent

A phone agent on Freya is a workflow. Each step has its own prompt and tools. Conditional routes decide which step takes the conversation next. Calculations such as business days can run as code instead of being left to the model.

The event page draws it as a chain of seven decision points around one step, the tool it calls and a route with a condition. The labels are left out on purpose: how many steps, which routes and which tools is the design problem your builder solves.

## Kit contents

Everything here is synthetic. The bank, the customers, the debts and the payments do not exist.

Download the kit (version 3). Unzip it and read `README.md` first. The kit has a version number in its file name and at the top of `README.md`. To run it you need a Freya API key — create one in your Freya workspace under API keys.

| File | What it is |
|---|---|
| `briefs/brief-a.md` | Freya Bank's specification for customers who are late on one product. 47 rules. |
| `briefs/brief-b.md` | The extra rules for customers with up to three products. Builds on Brief A. |
| `tools/openapi.json` | The bank's tool API that the phone agent calls. Seven tools: `verify_identity`, `get_account`, `create_promise`, `add_note`, `schedule_callback`, `transfer_to_agent`, `close_call`. |
| `public-test-set.json` | The thirteen cases below: who the customer is, what they do and what the bank's records must show afterwards. |
| `docs/` | The Freya workflow format, tools and code nodes, and the API calls a builder needs. Written for a program to read. |
| `freya.py` | A small client for the Freya API. Creates a workflow once and updates it on later runs. Standard library only. |
| `examples/base-agent.json` | An example phone agent: two steps, four tools. The same one that is in your workspace. A place to start, not a good score. |
| `examples/agent_builder.py` | An example builder on the Claude Agent SDK with one skill. Claude reads the brief, builds the agent, tests it and fixes what fails. |
| `env.example` | The two keys you set: your Freya API key, and a team key you make up for the practice bank. |
| `tools/run_cases.py` | Runs the practice cases against your phone agent and prints pass or fail per case, with the reason. |

### How one case runs

| Simulated customer | The phone agent | Mock bank API | Ledger | Scorer |
|---|---|---|---|---|
| follows the case script | your builder made | identity, debts, promises — we host it | every call and its result | pass or fail per case |
| text, not audio | | | | conversation, tool calls, final state, transcript |

The mock bank API stands in for the bank's own systems. The phone agent calls it to check identity, read the debt and record a promise. We host it, so we can see what was really recorded. The scorer reads that record, not what the phone agent says it did. You pick a team key, and your practice sessions and their records belong to that key.

### Practice cases

Ten cases use Brief A and three use Brief B. Every case runs on Wednesday 14 October 2026 at 11:00, so the dates are fixed. (`public-test-set.json` holds the customer script and the checks for each case.)

| Case | Brief | Family | What happens | Level |
|---|---|---|---|---|
| PUB-01 | A | Happy path | Confirms identity and pays the full amount today | easy |
| PUB-02 | A | Third party | A relative answers | medium |
| PUB-03 | A | Identity | Three wrong answers | medium |
| PUB-04 | A | Dates | Wants a date after the deadline | medium |
| PUB-05 | A | Hardship | Lost his job, declines the support team | medium |
| PUB-06 | A | Amounts | Full amount is too much, accepts the floor | hard |
| PUB-07 | A | Dates | A vague period, then a holiday | hard |
| PUB-08 | A | Already paid | Says she already paid | medium |
| PUB-09 | A | Restructuring | Asks for a new payment plan | medium |
| PUB-10 | A | Tool failure | The promise service fails on the first call | hard |
| PUB-11 | B | Multi-product | Three products, one date for all | medium |
| PUB-12 | B | Multi-product | Promises one product, refuses two | hard |
| PUB-13 | B | Multi-product | One date for both, but the deadlines differ | hard |

## Scoring

One number: the share of hidden cases passed.

A case is one simulated customer. It passes only when all three checks pass. There is no partial credit.

The bank's API does not enforce the brief. It records a promise on a holiday or below the minimum without complaint. Keeping the rules is the phone agent's job.

- **Outcome** — is the ledger in the right state? Promise on the right product, date and amount, recorded once.
- **Policy** — did it stay inside the brief? No debt read before the identity check, no date past the limit.
- **Honesty** — did it tell the customer the truth? Never says "recorded" when the tool call failed.

Outcome is read from the bank's records. Policy and honesty are read from the transcript by a judge model, against the checks listed in each case.

A correct refusal counts. When the customer disputes the debt, the passing outcome is a recorded dispute and no promise. A phone agent that pushes for a promise anyway fails.

### The final

| Item | Value |
|---|---|
| Case | One: Freya Bank's credit card statement-debt line, in Turkish |
| Test customers | Hidden, and so are their success criteria and the weights |
| Example conversations | 6, in the zip. They show the kind of call |
| Scored | Outcome from the bank's records, policy and honesty from the transcript. No partial credit |

Only the phone agent is scored; your rank comes from its result. We rerun the builders of the top entries to verify them.

### Score yourself

The kit includes the scorer. Point it at a phone agent and it runs the practice cases and prints, for each one, the tool calls the phone agent made and why it failed.

```
$ python3 tools/run_cases.py <agent_id> --brief A

PASS PUB-01 easy   Happy path   | verify > verify > get_account > promise > close_call
FAIL PUB-04 medium Dates        | verify > verify > get_account > promise > close_call
       - promises [('p1', 1250.0, '2026-10-27')], expected [('p1', 1250.0, '2026-10-23')]
...
5 / 10 passed
```

The printout shortens two tool names: `verify` is `verify_identity` and `promise` is `create_promise`.

A ten-case run takes 3 to 11 minutes. One simulation runs at a time per workspace, and a team has one workspace. The same phone agent can pass a case in one run and fail it in the next, so run more than once before you trust a score: `--reps 3` counts a customer only when every run passes, as the final does.

## Submission

One phone agent, one commit and the builder's trace.

1. Download the case folder and read `BRIEF.md` first.
2. Write the bank's mock from the service contract and the test customers, and deploy it on Cloudflare Workers.
3. Run your builder on the folder and keep everything it prints. That is the trace. You may run it more than once.
4. Export the phone agent with `freya.export_workflow` and commit the file with the trace. Submit one phone agent, the one that run made, and do not edit it after the run.
5. Before 20:00 UTC, send the form below to the address in the kit email.

```
$ python3 builder/build.py FreyaBank-Ekstre-Borc/ https://your-mock.your-subdomain.workers.dev 2>&1 | tee traces/final.log

{
  "team": "your-team-name",
  "members": [{"name": "your-name", "email": "you@example.com"}],
  "repo": "https://github.com/you/your-builder",
  "commit": "9f2c1ab",
  "run_command": "python3 builder/build.py {case_folder} {mock_url}",
  "workflow": "submission/final.workflow.json",
  "trace": "traces/final.log",
  "mock_url": "https://your-mock.your-subdomain.workers.dev"
}
```

A solo team lists one member.

### The builder's trace

A trace is the record of one builder run: what it read, what it decided and what it created. One trace, from the run that made the phone agent you submit. Commit it with the workflow.

| In the trace | Why |
|---|---|
| Start and end time of the run | Shows the run happened, and when. |
| Every model call the builder made: which model, and what it was asked for in one line | Shows how the builder works, not only what it produced. |
| What it created on Freya: workflow id, agent id, number of steps and tools | Ties the phone agent you submit to this run. |
| Any test it ran on its own phone agent, with the result | A builder that checks its own work is the point of the exercise. |

The trace is not scored. Plain text is fine. There is no required format. Remove API keys before you commit.

If you built your builder with a coding agent such as Claude Code or Codex, you may also share those session logs. This is optional. The top three teams talk their approach through with us, and a log is the easiest way to show it.

### How we verify

We run the phone agent you submitted on hidden simulated customers, in our workspace; their tools call your mock. A reviewer reads every trace against the commit and the submitted phone agent. The top entries may have their builder rerun; a run clearly worse than yours removes the entry. A hand-edited agent, or a builder with the final case written into it, is removed.

### Limits

| Limit | Value |
|---|---|
| Phone agents | One, and the trace of the run that made it |
| Mock | On Cloudflare Workers, deployed before the builder run and running until the results are out |
| Workflows per workspace | 200. Update one in place instead of creating a new one per run. |
| Models the builder may use | Any. You pay for your builder's own model calls. |
| Model the phone agent runs on | The Freya LLM: the only model on staging, the one set in `freya.py`. The same for every team. |

## Rules

1. Enter solo or as a team of two.
2. You submit a builder. A hand-built phone agent on its own is not a valid entry.
3. The phone agent must come out of the submitted commit with no manual edits.
4. Submit the trace of the run that made your phone agent. An entry without a trace is not ranked.
5. The phone agent may call only your mock. A call to any other service fails the case.
6. Do not probe or load-test the platform. One Freya key per team.
7. You may fix your builder during the three hours. Nothing from the final case may be written into it; a builder with the case written into it is removed. A reviewer checks the commit for that.
8. All data is synthetic. Do not bring real customer data.

## FAQ

**I did not get the login mail.**
Look in your spam folder first. Mail to Outlook, Hotmail and some university addresses was filtered. If it is not there, reply to us and we send it again.

**Where is the kit?**
On the Data tab: "Download the kit". Unzip it and read `README.md` first.

**Where do I get a Freya API key?**
Sign in with the account we mailed you, open API keys in the dashboard and create one. Put it in `env.sh` as `FREYA_API_KEY`.

**My teammate has no account, or we have two workspaces.**
Work in one workspace. Its owner invites the teammate from Workspace settings. If your teammate has no account at all, reply to us with the address.

**A test call in the dashboard never passes identity.**
Your workspace has one practice customer for dashboard test calls. Answer as that customer: date of birth 14 March 1988, last four digits 4471. After a call has closed, the same customer starts fresh once it has been idle for 5 minutes. `run_cases.py` opens a fresh customer for every case, so it is not affected.

**How many workflows can a workspace hold?**
200. Still, update your workflow in place instead of creating a new one per run.

**Can my builder open practice customers of its own?**
No. The practice bank serves the 13 cases PUB-01 to PUB-13 only. To check a phone agent on a case with no practice customers, talk to it with `POST /api/v2/chat/message` (see `docs/api.md`).

**Are there practice cases for the final?**
No. The 6 example conversations in the zip show the kind of call; the customers we score with are hidden.

**May I take the mock down after I submit?**
No. Leave it running until the results are out.

**May I use code I wrote before the event?**
Yes. Nothing from the final case may be in your builder, and the phone agent must come out of your builder with no edits by hand.

**Is the score taken from the phone agent we submit, or from your rerun?**
From the phone agent you export and submit. We rerun the builders of the top entries only, to check that the submitted phone agent really came out of your builder. Model output varies from run to run, so we do not expect an identical workflow. We look at its structure and its score.

**My score dropped and I changed nothing.**
The simulated customers and your phone agent are language models, so runs differ. A run also suffers when the model is busy: `run_cases.py` prints the slowest agent turn per call. Run again, and use `--reps 3` before you trust a number.

**Something else?**
Reply to the login mail. It reaches us.
