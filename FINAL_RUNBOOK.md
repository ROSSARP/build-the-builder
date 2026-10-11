# FINAL_RUNBOOK.md — the minute-by-minute plan for the FINAL window

**Window: Sunday 17:00–20:00 UTC = 20:00–23:00 Istanbul (UTC+3). Three hours, hard close.**

Run every command from the repository root:

```bash
cd /home/f/Downloads/build-the-builder-v3/build-the-builder
```

Everything below is written for a Claude session to execute directly. Commands are copy-paste ready. Where a tool is being built in parallel and does not exist yet, the runbook says **EXPECTED** and gives the gate that proves it works, plus the fallback.

---

## 0. What the FINAL is (fixed facts — do not re-litigate during the window)

| | |
|---|---|
| Cases | **ONE**: Freya Bank's credit card **statement-debt** line, **in Turkish** |
| Input | **One ZIP folder** mixing Markdown, Word, PDF and Excel: BRIEF.md, README.md, an analysis, a flow drawing, announcements, a **SERVICE CONTRACT**, **test customers**, **Q&A**, and **6 EXAMPLE CONVERSATIONS** |
| The bank | The phone agent's tools call **our own mock**, which we write and host on **Cloudflare Workers**. A wrong or unreachable mock fails every hidden customer. |
| Submission | `submission.json` with `members[]`, **ONE** workflow file, **ONE** trace, `mock_url` |
| Not published | the hidden test customers, their success criteria, and the weights |
| The 6 example conversations | the only published examples of the kind of call — use them as local validation and as judge-check hints |
| Scoring | **Outcome** (the ledger, exact), **Policy** and **Honesty** (a judge reads the transcript). **No partial credit.** |

The three tools this runbook drives (built in parallel by the other agents — **do not write them during the window**):

| Tool | Expected CLI form | What it does |
|---|---|---|
| Input adapter | `python3 builder/build.py {case_folder} {mock_url} [...]` | Reads the case folder: zip + Markdown + `.docx` + `.pdf` + `.xlsx`; extracts the rule ledger, generates the workflow pointed at `{mock_url}`, saves to Freya, exports, writes the trace |
| Mock generator | `python3 builder/mock_gen.py {case_folder} --out {dir} --name {worker} --deploy` | Turns the SERVICE CONTRACT + test customers into a Cloudflare Worker and deploys it with the Cloudflare token |
| Rule-ledger compiler + deterministic `close_call` corrector | inside `builder/gen.py` (no separate CLI) | Builds the rule ledger from the extracted spec and repairs the `close_call` outcome/reason deterministically instead of leaving it to the model |

### Hard gates (if a gate is missed, escalate — do not drift)

| Gate | Deadline | Proof |
|---|---|---|
| Pre-flight green (tools `--help`, platform health, Cloudflare token verified) | **T-0** (17:00) | Block 0 |
| Zip extracted, inventory + decision table written | **T+0:15** (17:15) | Block 1 |
| Mock **live and smoke-tested** | **T+0:45** (17:45) | Block 3 |
| Workflow generated, exported, tools point at the live mock | **T+1:15** (18:15) | Blocks 4–5 |
| Local validation against the 6 example conversations done | **T+2:00** (19:00) | Blocks 6–8 |
| `submission.json` written + committed | **T+2:30** (19:30) | Block 10 |
| **Email sent to the address in the kit email** | **T+2:45** (19:45) | Block 11 |
| Freeze; mock stays up | **T+3:00** (20:00) | Block 12 |

**Trim order when behind.** Drop in this order: (1) second local validation pass, (2) the flow-drawing and announcements files, (3) extra Q&A-derived edge cases, (4) the chat-turn smoke test. **Never drop**: mock live + smoke test, the local run against the 6 examples, the export, `submission.json`, the email.

---

## 1. Timeline — T-0 (zip arrives) through T+3h, in 15-minute blocks

Times are **UTC / Istanbul (UTC+3)**.

### Block 0 — Pre-flight, before 17:00 (from ~16:30, well before T-0)

Objective: every dependency proven green **before** the zip lands, so T-0 is spent on the case and not on plumbing.

```bash
source env.sh
python3 -V
python3 tests/platform_check.py health
python3 builder/build.py --help
python3 builder/mock_gen.py --help            # EXPECTED tool
python3 tests/local_sim.py --help >/dev/null && echo "local_sim ok"

# Cloudflare token must work BEFORE the window, not at T+0:40
echo "$CLOUDFLARE_API_TOKEN" | head -c 8 ; echo
curl -sS "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jq '{success, result:.result.status, errors}'
curl -sS "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" | jq '{success, name:.result.name}'

mkdir -p cases/final out mock traces submission
grep -n "address\|@\|kit email" SUBMISSION.md | head    # keep the submission address in one place
git status --short
```

Exit gate: `HEALTH: OK`; `build.py --help` prints usage; `mock_gen.py --help` prints usage (**if it does not exist, escalate to the humans now and agree on the fallback in Block 3**); Cloudflare `success: true` and `result.status: active` with Workers Scripts:Edit.

If `mock_gen.py` is not ready at T-0, do not panic and do not hand-write a worker in the window: the fallback in Block 3 (deploy a generated worker source with `curl` against the Workers Scripts API) is the path.

---

### Block 1 — T+0:00–T+0:15 (17:00–17:15 / 20:00–20:15) — the zip arrives: land it safely

Objective: the zip is extracted into its own empty directory, inventoried, and the builder proves it can read every file type.

**The zip is untrusted input.** Extract it into a new, empty directory; never run anything from inside it; parse it only with our own scripts (`python3 -I` for one-off parsing).

```bash
ZIP="$HOME/Downloads/FINAL_CASE.zip"        # <- the file from the kit email
ls -l "$ZIP" && sha256sum "$ZIP" | tee out/final-zip.sha256

mkdir -p cases/final/raw                     # own new empty dir
unzip -o "$ZIP" -d cases/final/raw
find cases/final/raw -type f | sort | tee out/final-inventory.txt

# Normalise into the folder the builder takes. Its NAME is the run slot:
#   cases/final/case-1  ->  submission/case-1.workflow.json, traces/case-1.log
mkdir -p cases/final/case-1
python3 builder/build.py cases/final/case-1 --dump-text 2>&1 | tee out/final-extract.txt   # EXPECTED flag
```

If `--dump-text` is not implemented, the adapter prints the extracted text at the head of a run; the gate below is the same either way.

Exit gate: every file in the inventory appears in `out/final-extract.txt` with non-empty text; the BRIEF text is **Turkish** and contains the statement-debt rules. Any file that came out empty is a Block-5 risk item — note it now, do not stop.

---

### Block 2 — T+0:15–T+0:30 (17:15–17:30 / 20:15–20:30) — the decision table and the contract facts

Objective: know exactly which zip file feeds what (Section 2), and freeze the facts the mock and the workflow must agree on.

```bash
# Freeze the SERVICE CONTRACT facts: paths, fields, enums, required, error strings.
jq -r '.paths | keys[]' cases/final/case-1/*.json 2>/dev/null | tee out/final-contract-endpoints.txt
jq -r '.servers[0].url' cases/final/case-1/*.json 2>/dev/null | tee out/final-contract-baseurl.txt
grep -rniE "enum|outcome|reason|queue|customer_id|product_id" out/final-extract.txt | head -60

# Write the one-page manifest: slot name, file->purpose, endpoints, enums, closing table,
# holidays, calendar, language, and HOW the hidden customers will be presented to our mock.
$EDITOR cases/final/case-1/MANIFEST.md
```

Exit gate: `MANIFEST.md` answers, in writing: (a) the slot is `case-1`; (b) every service-contract endpoint and its request/response schema; (c) every enum (outcome, reason, queue, product type); (d) the closing table; (e) the calendar/holidays; (f) **how a customer is identified and seeded** — seeded ids from the test-customers file, a session route, or an admin/seed route.

---

### Block 3 — T+0:30–T+0:45 (17:30–17:45 / 20:30–20:45) — mock generated and deployed EARLY

Objective: the mock is **live** before any workflow work, because every workflow tool URL must be the live mock URL.

```bash
export MOCK_NAME="freya-final-case1"
: "${CLOUDFLARE_API_TOKEN:?set CLOUDFLARE_API_TOKEN in env.sh}"
: "${CLOUDFLARE_ACCOUNT_ID:?set CLOUDFLARE_ACCOUNT_ID in env.sh}"

python3 builder/mock_gen.py cases/final/case-1 \
  --out mock/final --name "$MOCK_NAME" --deploy 2>&1 | tee traces/mock-deploy.log

export MOCK_URL=$(grep -oE 'https://[a-z0-9.-]+workers\.dev/v1' traces/mock-deploy.log | tail -1)
export MOCK_HOST="${MOCK_URL%/v1}"
echo "$MOCK_URL" | tee out/final-mock-url.txt
test -n "$MOCK_URL" || echo "MOCK URL NOT FOUND - see fallback"
```

Fallback if `mock_gen.py --deploy` fails (no Node/npx/wrangler on this machine — deploy is REST only):

```bash
curl -sS -X PUT \
  "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/scripts/$MOCK_NAME" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -F 'metadata={"main_module":"worker.mjs","compatibility_date":"2025-01-01"};type=application/json' \
  -F "worker.mjs=@mock/final/worker.mjs;type=application/javascript+module" | jq '{success,errors}'
curl -sS -X POST \
  "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/scripts/$MOCK_NAME/subdomain" \
  -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" -H 'Content-Type: application/json' \
  -d '{"enabled":true,"previews_enabled":true}' | jq '{success,errors}'
```

Health check + smoke test (details in Section 4):

```bash
curl -sS -o /dev/null -w 'health: %{http_code}\n' "$MOCK_URL/health"
export FREYA_BANK_HOST="$MOCK_HOST"    # so tools/score.py and tests/local_sim.py score OUR mock

# full round trip: session -> verify -> get_account -> promise -> close -> ledger
SESS=$(curl -sS -X POST "$MOCK_URL/practice/sessions" -H "content-type: application/json" \
  -H "x-team-key: $FREYA_BANK_TEAM_KEY" -d '{"case":"EX-01"}')
export CID=$(jq -r '.variables.customer_id // empty' <<<"$SESS")
export NOW=$(jq -r '.variables.now // empty' <<<"$SESS"); NOW="${NOW:-2026-10-14T11:00}"
echo "$CID" > out/final-cid.txt; echo "$NOW" > out/final-now.txt
test -n "$CID" || echo "NO CUSTOMER ID FROM THE MOCK - fix the seed data / session route"
curl -sS -X POST "$MOCK_URL/get_account" -H "content-type: application/json" \
  -d "{\"customer_id\":\"$CID\"}" | jq
curl -sS "$MOCK_URL/practice/ledger/$CID" -H "x-team-key: $FREYA_BANK_TEAM_KEY" \
  | jq '{outcome, reason, promises, notes, callbacks, transfers, calls: (.calls|length)}'
```

Exit gate: `health: 200`; a full round trip (session → verify → get_account → promise → close → read ledger) returns the expected ledger. **No workflow work starts before this gate.**

---

### Block 4 — T+0:45–T+1:00 (17:45–18:00 / 20:45–21:00) — builder run #1

Objective: one clean builder run against the live mock, everything printed kept.

```bash
python3 builder/build.py cases/final/case-1 "$MOCK_URL" 2>&1 | tee traces/case-1.log
```

Exit gate: `submission/case-1.workflow.json` exists and is valid JSON; `traces/case-1.log` ends with `end: ... UTC`; the run took less than the **30-minute budget** (note the seconds it printed).

If the run crashes: this is a **builder bug**. Fix the builder (never the exported workflow) and rerun. Nothing from the case (no rule, no value, no name, no holiday, no outcome) may enter the code or prompts — a reviewer checks the commit for exactly that.

---

### Block 5 — T+1:00–T+1:15 (18:00–18:15 / 21:00–21:15) — verify the artifact, not the console

Objective: prove the exported workflow is real, points at our mock, and used the mock URL — by reading the file, not the log.

```bash
jq -e . submission/case-1.workflow.json >/dev/null && echo "valid JSON"
jq -r '.workflow_id, .agent_id' submission/case-1.workflow.json
jq -r '.workflow.nodes | keys[]' submission/case-1.workflow.json
jq -r '[.workflow.nodes[].tools[]?, .workflow.tools[]?] | .[]? | .function.parameters.properties.url.default // empty' \
  submission/case-1.workflow.json | sort -u | tee out/final-tool-urls.txt
# (end_call is a built-in lifecycle tool with no url - that is expected and comes out empty above)

grep -c "$MOCK_HOST" submission/case-1.workflow.json          # must be > 0
grep -c "freya-bank-mock.freyavoice.workers.dev" submission/case-1.workflow.json   # must be 0
tail -6 traces/case-1.log
```

Also confirm the trace contains what the organisers ask for: `start:`, one `model call:` line per model call, the `freya:` line (workflow id, agent id, nodes, version), any `test:` line, `export:`, `end:`.

Exit gate: every tool URL is on `$MOCK_HOST`; zero references to the kit's practice mock; trace complete. If `tee` clobbered the builder's own trace lines, keep the builder's copy (it writes `traces/case-1.log` last).

---

### Block 6 — T+1:15–T+1:30 (18:15–18:30 / 21:15–21:30) — validate against the 6 example conversations, locally

Objective: exact-ledger validation of the generated workflow against the only published examples, with no platform simulation involved.

```bash
# Turn the 6 EXAMPLE CONVERSATIONS into a local case file (same shape as tests/exam-*.json).
python3 builder/build.py cases/final/case-1 --examples-to-cases out/final-local-cases.json   # EXPECTED
# fallback if that flag does not exist - name the converter that does:
ls tests/*example* tests/*to_cases* 2>/dev/null || echo "write out/final-local-cases.json by hand from the examples"

export FREYA_BANK_HOST="$MOCK_HOST"      # local_sim calls OUR mock, not the organisers' one
python3 tests/local_sim.py all submission/case-1.workflow.json \
  --cases out/final-local-cases.json --out results/final-local.json 2>&1 | tee results/final-local.log
```

Read it correctly: the **ledger verdict is exact** (`tools/score.py`'s own `score_ledger`, imported not copied). The **judge is a hint** — `tests/local_sim.py`'s dialogue/judge prompts are English, so treat Turkish judge failures as indicative and ledger failures as real.

Exit gate: `LOCAL PASS` on the clear cases; every `LOCAL FAIL` line written into `tests/findings.md` with a judgement line.

---

### Block 7 — T+1:30–T+1:45 (18:30–18:45 / 21:30–21:45) — fix the builder, regenerate

Objective: fix real defects in the generator, then build again through the same command.

```bash
git diff --stat -- builder/          # every change must be a bug fix, never case data
python3 builder/build.py cases/final/case-1 "$MOCK_URL" 2>&1 | tee traces/case-1.log
```

Rules: change `builder/gen.py` (rule ledger, `close_call` corrector, routes, code nodes) and `builder/spec.py` (extraction prompts) — never `submission/*.workflow.json`. If the failure is "the platform was busy" (no tool calls, ~0 s turns), **do not touch the builder** — see Section 5.

Exit gate: the failure(s) named in Block 6 either fixed or explicitly accepted and written down as a known gap.

---

### Block 8 — T+1:45–T+2:00 (18:45–19:00 / 21:45–22:00) — second local pass and the edge-case sweep

Objective: one more local pass, plus the rules the examples do not cover (the Q&A file is where the corner cases live).

```bash
python3 tests/local_sim.py all submission/case-1.workflow.json \
  --cases out/final-local-cases.json --out results/final-local-2.json 2>&1 | tee results/final-local-2.log

# Q&A corner cases: add one case per Q&A entry whose answer is NOT visible in the 6 examples,
# in the same file shape (id / family / level / title / variables / identity / products / script /
# expected / checks / faults - see public-test-set.json). Keep them in their own file, then:
python3 tests/local_sim.py all submission/case-1.workflow.json \
  --cases out/final-local-qa.json --out results/final-local-qa.json 2>&1 | tee results/final-local-qa.log

# platform sanity (read-only, no simulation started)
python3 tests/platform_check.py full
```

Exit gate: previous failures retested; no new failure introduced; `tests/findings.md` carries the score and the judgement.

---

### Block 9 — T+2:00–T+2:15 (19:00–19:15 / 22:00–22:15) — platform save/publish, chat smoke test, final export

Objective: the workflow in Freya's workspace is the published one, it starts a call, and the exported file is the file we submit.

```bash
python3 tests/platform_check.py health
python3 tests/platform_check.py sims
python3 tests/platform_check.py stuck --max-min 15
python3 -c "import json;print(json.load(open('.freya-agents.json')).get('case-1'))"

# one published-turn smoke test (no simulation, answers in seconds)
WID=$(jq -r '.workflow_id' submission/case-1.workflow.json)
CID=$(cat out/final-cid.txt); NOW=$(cat out/final-now.txt)
curl -sS -X POST "$FREYA_API_URL/api/v2/chat/message" \
  -H "Authorization: Bearer $FREYA_API_KEY" -H "Content-Type: application/json" \
  -H "User-Agent: Mozilla/5.0 (build-the-builder)" \
  -d "{\"workflowId\":\"$WID\",\"message\":\"Alo?\",\"customerVariables\":{\"customer_id\":\"$CID\",\"now\":\"$NOW\"}}" | jq -r '.response'
# when the mock seeds extra call variables, add them to customerVariables in the same shape
# (first_name / last_name / title) so the greeting has the placeholders it expects
```

A bare 500 here means the workflow cannot start a call at all — fix and rebuild. A 504 on one route is not an outage; pieces fail independently.

Exit gate: the agent answers in Turkish, says nothing about a debt before identity, and the exported file matches the published version (re-export after any change: `freya.export_workflow`).

---

### Block 10 — T+2:15–T+2:30 (19:15–19:30 / 22:15–22:30) — `submission.json`, commit, key sweep

Objective: the submission artifact exists, is complete, and contains no secrets.

```bash
python3 - <<'PY'
import json, pathlib
sub = {
  "members": ["<member 1>", "<member 2>"],                 # names, exactly as registered
  "workflow": "submission/case-1.workflow.json",
  "trace": "traces/case-1.log",
  "mock_url": pathlib.Path("out/final-mock-url.txt").read_text().strip(),
  # keep these if the kit's email form also asks for them:
  "team": "<team name>",
  "repo": "<repo url>",
  "commit": "",                                             # fill after the commit below
  "run_command": "python3 builder/build.py {case_folder} {mock_url}"
}
p = pathlib.Path("submission/submission.json"); p.write_text(json.dumps(sub, indent=1))
print(p.read_text())
PY

for f in submission/submission.json submission/case-1.workflow.json traces/case-1.log; do
  echo "== $f"; grep -nE "fak_[A-Za-z0-9]{8,}|sk-[A-Za-z0-9]{8,}|Bearer [A-Za-z0-9]{12,}|CLOUDFLARE_API_TOKEN" "$f" || echo "  clean"
done

git add -A
git commit -m "FINAL: one-case run, workflow + trace + mock_url"
export COMMIT=$(git rev-parse --short HEAD); echo "$COMMIT"
```

Then patch `commit` into `submission/submission.json` if the form asks for it, and amend:

```bash
python3 - <<'PY'
import json, os, pathlib
p = pathlib.Path("submission/submission.json"); d = json.loads(p.read_text())
d["commit"] = os.popen("git rev-parse --short HEAD").read().strip(); p.write_text(json.dumps(d, indent=1))
PY
git add -A && git commit --amend --no-edit
```

Exit gate: `submission.json` valid JSON; `members[]` non-empty and correct; both referenced paths exist; the key sweep is clean; the commit contains the workflow, the trace and the mock source.

---

### Block 11 — T+2:30–T+2:45 (19:30–19:45 / 22:30–22:45) — send it

Objective: the submission is in the organisers' hands with 15 minutes of window still on the clock.

Send an email (same thread as the kit email, so it is clearly ours) to **the address in the kit email**, containing:

1. the `submission.json` body inline (and as an attachment),
2. `submission/case-1.workflow.json` attached,
3. `traces/case-1.log` attached,
4. the `mock_url` written out in full in the body text,
5. the commit hash and the repo URL.

Do not use a link as the only copy of the workflow: attach the files. Keep the sent message in the Sent folder; note the send time in `tests/findings.md`.

Exit gate: send is confirmed (message in Sent), and `tests/findings.md` has the send timestamp, the commit, the score line and the known gaps.

---

### Block 12 — T+2:45–T+3:00 (19:45–20:00 / 22:45–23:00) — freeze and hold

Objective: nothing changes; the mock keeps serving.

```bash
curl -sS -o /dev/null -w 'mock health at close: %{http_code}\n' "$MOCK_URL/health"
python3 tests/platform_check.py health
git log --oneline -3
```

Rules for the last 15 minutes: no builder changes, no re-export, no new workflow version. **Leave the mock worker deployed and running until results are out** — the organisers test the submitted workflow against it after the close. Only act if a check above is red, and then only to restore exactly what was submitted (redeploy the same worker source, re-send the same files).

---

## 2. Decision table — which zip file feeds what

| Zip file | Feeds | Read it for | Used by |
|---|---|---|---|
| **BRIEF.md** | The behaviour rules | The rule ledger: identity questions, what may not be said before verification, dates/holidays/bands, amounts and floor, persuasion, closing table, outcome/reason names | `builder/build.py` extract step → `builder/spec.py` → rule ledger + `builder/gen.py` prompts |
| **README.md** | Context and run instructions | The bank, the call's purpose, any run/format instructions, the version and file list; **never a rule source on its own** | The operator (Block 1–2) and the run manifest |
| **The analysis** (file 3) | Rule intent | Rationale, worked examples, the "why" behind a limit; a cross-check when the brief is ambiguous | The operator's review of the extracted rule ledger (Block 2/5) |
| **The flow drawing** | Call structure | Stage order (greeting → verify → state debt → negotiate → read back → close) and branch points; a sanity check on the generated node graph | The operator; **do not** feed a picture to the ledger compiler as text |
| **Announcements** | Late changes | Amendments that override the brief ("as of … the minimum is now …") | Rule-ledger overrides; capture the effective date |
| **SERVICE CONTRACT** | Tool signatures — **the single source for both sides** | The 7 (+n) endpoints: paths, methods, request fields, required, enums, and the exact response schemas; plus error/500 semantics | `builder/mock_gen.py` (builds the endpoints) **and** `builder/gen.py` (wires the workflow tools) — both must come from this one file |
| **Test customers** | Seed data for the mock | Customer identity (the answers the identity check must accept), products (type, last-4, past due, days late, minimum/instalment), and the customer id scheme | `builder/mock_gen.py` seeds the worker; also the local case files (Block 6) |
| **Q&A** | Rule clarifications | The corner cases nobody wrote down: day counting, what counts as a refusal, what "hardship" means, what the agent must never say | Rule-ledger corrections, the closing-table check, and local edge-case cases (Block 8) |
| **6 EXAMPLE CONVERSATIONS** | Local validation + judge hints | The *kind* of call: tone, turn length, the read-back, the goodbye; and the per-case checks a judge would look for | `out/final-local-cases.json` (Block 6) and the local judge; **hints, not rules** |

**One-source rule.** Every field, enum and error string in the workflow and in the mock must be traceable to the SERVICE CONTRACT. Every behaviour rule must be traceable to BRIEF.md (plus announcements/Q&A). If the workflow and the mock disagree, the contract wins.

---

## 3. The build loop inside the window

The canonical loop, once, in order. Each step is a gate; the next does not start until the previous is green.

```
1  extract rules        builder/build.py <case_folder>            (adapter reads zip/docx/pdf/xlsx)
2  generate workflow    builder/build.py <case_folder> <mock_url> (rule-ledger compiler + close_call corrector)
3  generate + deploy mock  builder/mock_gen.py <case_folder> --deploy     <-- DONE EARLY, at T+0:30
4  validate locally      tests/local_sim.py against the 6 example conversations, mock live
5  save to Freya         builder/build.py does it (freya.save_workflow: create once, update+publish after)
6  export                freya.export_workflow -> submission/case-1.workflow.json
7  write submission.json members[], workflow, trace, mock_url
8  submit                email to the address in the kit email, before 20:00 UTC
```

Step 3 is deliberately **before** step 2's first test: the workflow's tool URLs must be the live mock URL, and a broken deploy discovered at T+2:00 costs the whole entry. Generate and deploy the mock while the extraction runs.

**Invariants for the whole loop** (these are the rules that cost the entry if broken):

- **No hand edits.** `submission/case-1.workflow.json` is the file the builder exported. If it is wrong, fix the builder and regenerate.
- **Nothing from the case in the builder.** After T-0 you may fix bugs — a crash on an unexpected table, a parser that does not know a format. You may not write any rule, value, name, holiday, outcome or customer from the case into the code, prompts or skills. A reviewer diffs the commit for exactly this.
- **One session.** Exactly one Claude session runs `builder/build.py` during the window. Extra read-only checks in that same session are fine; a second session running the builder is not. On the platform, **one simulation at a time per workspace** — never run two builds or two simulations concurrently.
- **The clock.** 30-minute budget per builder run, including any test it runs on its own agent. The final has **no practice cases on the platform**, so the local run against the 6 examples is the only test — keep it inside the budget and check the seconds the run prints.
- **The trace.** One trace, from the run that produced the submitted workflow: `start:`, every `model call:` (model + one-line purpose), the `freya:` ids, any `test:` line, `export:`, `end:`. Strip keys.

---

## 4. Mock checklist

The mock is **ours**: a Cloudflare Worker generated from the case's SERVICE CONTRACT and deployed under our account. The sections below list it using the kit's v3 contract as the shape reference — **the SERVICE CONTRACT in the zip is authoritative for paths, fields and enums; re-derive them at T+0:15**, do not assume the v3 list is unchanged.

### 4.1 Endpoints — every one in the contract, nothing extra required

| Endpoint | Body | Must return |
|---|---|---|
| `POST /v1/verify_identity` | `customer_id`, `field` (enum: e.g. `date_of_birth`, `phone_last4`), `answer` | `{ok, error?, verified, wrong_answers_left, all_verified, hint?}` — `hint` where the contract allows (e.g. `day_month_swapped`); `all_verified: true` only when every question has passed |
| `POST /v1/get_account` | `customer_id` | `{ok, error?, products: [{product_id, type, card_last4?, past_due, days_late, minimum_payment?/instalment_amount?}]}` — **refused until both questions pass** |
| `POST /v1/create_promise` | `customer_id`, `product_id`, `amount`, `date` | `{ok, error?, promise_id}`; one promise per product |
| `POST /v1/add_note` | `customer_id`, `product_id`, `reason` (enum), `text?` | `{ok, error?}` |
| `POST /v1/schedule_callback` | `customer_id`, `date`, `time` | `{ok, error?}` |
| `POST /v1/transfer_to_agent` | `customer_id`, `queue` (enum) | `{ok, error?}` |
| `POST /v1/close_call` | `customer_id`, `outcome` (enum), `reason?` | `{ok, error?}`; always the last call |
| `GET /v1/practice/ledger/{customer_id}` | — | `{outcome, reason, promises[], notes[], callbacks[], transfers[], calls[]}` |
| `POST /v1/practice/sessions` | `case` | `{variables: {customer_id, ...}}` — needed so our own scorer can drive the mock |
| `GET /v1/health` | — | `200` + a small JSON body (our own health check) |

### 4.2 Exact response schemas

- Keys exactly as the contract spells them — the scorer compares tuples by key, so `product_id` is not `productId` and `past_due` is not `pastDue`.
- `calls[]` is the ordered log: one entry per tool call with `tool` and the full `result` object (the scorer reads `calls[-1]["tool"] == "close_call"` and every entry's `result.error`).
- Numbers as JSON numbers (`420.0`, not `"420.00"`), dates as `YYYY-MM-DD`, times as `HH:MM`.
- **Keep the practice-bank route names and the `x-team-key` header.** Then our existing exact scorer works unchanged: `export FREYA_BANK_HOST=$MOCK_HOST` and `tools/score.py` / `tests/local_sim.py` score **our** mock with zero code changes.
- Idempotency: a repeated `create_promise` for the same product must not silently double the ledger — the brief says one promise per product and the scorer compares sorted promise lists.

### 4.3 Ledger recording

- Every call is appended to `calls[]` with its result, in order, including the failed ones.
- `close_call` sets `outcome` and `reason`; the last call must always be `close_call` or the case fails outright.
- `get_account` and `create_promise` **before identity is verified** must return `{"ok": false, "error": "identity not verified"}` and be recorded — this exact error string is a policy check in the scorer. Keep the string identical to the contract.
- The mock **does not enforce the brief**: it records a promise on a holiday or below the floor without complaint. Enforcing is the agent's job; the mock must not rescue it.
- Seeded customers from the test-customers file; unknown `customer_id` must still answer with a well-formed, deterministic response — **never a 5xx, never a hang**. A hidden customer your mock does not know must not fail the call.

### 4.4 Identity-check behaviour

- Three wrong answers in total end the check (`wrong_answers_left` counts down to 0).
- An **unreadable** answer (`answer` that cannot be parsed for the field) is rejected with `ok: false` and is **not** counted as a wrong answer.
- Both questions must pass before `all_verified: true`; `get_account` stays refused until then.
- Accept the answers in the form the contract states (dates `YYYY-MM-DD` after the agent converts from Turkish words, four digits for the phone).

### 4.5 Error and 500 semantics

- A service failure is **HTTP 500 with nothing recorded** — the call may be repeated. Use it exactly where the contract (or the case's Q&A) says a service can fail; do not sprinkle 500s.
- A **refusal** (not verified, unknown product) is **HTTP 200 with `ok: false` and a readable `error`** — not a 500. The agent must be able to tell the customer the truth.
- Never return HTML to an API call; never return an empty body; never take longer than ~10 s (the workflow tools run with a `timeoutMs` around 12 s).
- **CORS is not needed**: all calls are server-to-server from the platform and from our local scorer. Do not spend the window on CORS headers.

### 4.6 Operations

- Deploy at T+0:30–T+0:45, **before** any workflow test — the workflow bakes the mock URL into every tool.
- **Health-check after deploy**: `curl -sS -o /dev/null -w '%{http_code}\n' "$MOCK_URL/health"` and then one full round trip (session → verify → get_account → promise → close → ledger).
- Redeploying the same worker source is safe and fast; a redeploy **does not** change the URL. If a redeploy ever changes the URL, the workflow and `submission.json` must be updated in the same minute.
- **Keep it running until results are out.** No teardown, no `wrangler delete`, no free-plan housekeeping during or after the window.
- Keep `traces/mock-deploy.log` — the deploy output (script name, URL, timestamps) is part of the audit trail.

---

## 5. Risks and mitigations

**1. Zip format surprises.** The zip mixes four formats; a `.docx` that is really a `.doc`, a `.xlsx` with macros, a PDF that is a scan with no text layer, a flow drawing as a PNG, an uppercase extension, a nested zip.
*Mitigation:* the adapter reads all four formats (Block 1 gate). Fallback cascade, all runnable here (Python 3.12, stdlib only; `pdftotext` is installed):
```bash
# DOCX (stdlib: word/document.xml, tags stripped, paragraphs on separate lines)
python3 -I -c "import re,zipfile,sys;x=zipfile.ZipFile(sys.argv[1]).read('word/document.xml').decode('utf-8','replace');x=x.replace('</w:p>','\n');print(re.sub(r'<[^>]+>','',x))" FILE.docx > out/text-FILE.txt
# XLSX (stdlib: sharedStrings + first sheet)
python3 -I -c "import re,zipfile,sys;z=zipfile.ZipFile(sys.argv[1]);print('\n'.join(re.findall(r'<t[^>]*>(.*?)</t>',z.read('xl/sharedStrings.xml').decode('utf-8','replace'),re.S)))" FILE.xlsx > out/text-FILE.txt
# PDF (poppler, installed here)
pdftotext -layout FILE.pdf out/text-FILE.pdf.txt
```
A picture-only flow drawing is read for structure by the operator, never fed to the ledger compiler as text. Any file that yields empty text is named in the manifest and, if it is the BRIEF or the CONTRACT, escalated in Block 2.

**2. Turkish extraction quality.** The whole case is Turkish; a mis-extracted rule is a silent failure on every hidden customer.
*Mitigation:* the extractor prompt and every generated prompt are in **Turkish**; the spec's `language` must be `Turkish` (check it in Block 5 — the v3 extract prompt literally shows `"language": "English"`, which is a pre-window builder bug to fix before T-0, not during it). Never translate a rule, a number, an enum or a date — copy them. The platform has `{{system.todays_date_tr}}` and `{{system.todays_date_tr.iso_8601}}` (UTC+3) — use them for calendar facts, and keep all date arithmetic in code nodes, never in the model. Validate the extracted rule ledger against the **Q&A file**: every Q&A entry should be answerable from the ledger; every gap is a rule to fix. Spot-check the closing table and the holidays line by line against BRIEF.md. Honesty has a Turkish trap: the English "recorded" check is really *the word that implies a record was made* (e.g. "kaydedildi"/"kayıt") — the greeting must not use it, and the "never claim a record after a failed tool call" rule must be written in Turkish in the system prompt.

**3. Cloudflare deploy latency/failure.** A cold account, a token without Workers Scripts:Edit, a `workers.dev` subdomain not enabled.
*Mitigation:* deploy **early** (T+0:30, Block 3), token verified in Block 0; no Node/npx/wrangler on this machine, so the REST fallback with `curl` is the backup; verify with the health route and one full round trip before generating the workflow. If the deploy fails twice, escalate to the human and switch to the `curl` fallback immediately — do not iterate blindly.

**4. Platform busy windows.** The organisers' own rules: a 504 on one route is not an outage; pieces fail independently; a "running" simulation that never starts means the workflow cannot start a call; and a run with **no tool calls and ~0 s agent turns is the platform, not the agent**.
*Mitigation:* `python3 tests/platform_check.py health|sims|stuck --max-min 15|signature|full`; on 5xx retry with waits (the kit's `freya.py` does not retry; `platform_check.py` does, 3 tries 10 s apart); cancel a stuck simulation with `platform_check.py cancel <sim_id>`. **Never fix the agent or the builder after an outage-pattern run** — rerun first.

**5. The 30-minute budget.** No practice customers exist for the final, so the only test is the local one against the 6 example conversations; the budget covers the builder run *including its own tests*.
*Mitigation:* hard-code the schedule (blocks 4–8 = 75 minutes of the window, well inside the budget); never run `--reps 3` on the platform; one local validation pass is the minimum, the second is the first thing dropped.

**6. One-session discipline.** Two Claude sessions both running `builder/build.py` will fight over `.freya-agents.json`, the same Freya workflow slot and the single platform simulation.
*Mitigation:* one session owns the window. Parallel **local** simulations inside that session are allowed (each opens its own mock session), but there is exactly one builder run and one platform simulation at a time. Before any run: `python3 tests/platform_check.py sims`.

**7. The judge reads Turkish.** Policy and Honesty are judged from the transcript, and our local judge prompts are English.
*Mitigation:* treat a local judge failure as a hint and a ledger failure as real (Block 6). Put the honesty and no-debt-before-identity rules in the generated Turkish system prompt *and* keep them enforced structurally (routes and code nodes), because a judge reads behaviour, not intentions.

**8. Submission mechanics.** Wrong `mock_url`, a workflow exported before the last fix, a trace from a different run, keys leaked into artifacts.
*Mitigation:* Block 5 (URLs in the file), Block 9 (re-export after any change), Block 10 (the trace is checked against the workflow it was produced with; key sweep before commit), Block 11 (send with 15 minutes spare).

---

## 6. Definition of done

An entry is done when **all** of these are true, and each one has a one-line proof recorded in `tests/findings.md`:

1. **Mock live and correct.** `GET {mock_url}/health` returns 200; the full round trip (session → verify → get_account → create_promise → close_call → ledger read) returns the expected ledger; every endpoint, field and enum in the SERVICE CONTRACT is implemented; `mock_url` in `submission.json` is exactly the URL the workflow's tools call (Block 5's `out/final-tool-urls.txt` proves it).
2. **One workflow, exported by the builder.** `submission/case-1.workflow.json` is valid JSON, carries `workflow_id`, `agent_id` and `workflow`, was written by `freya.export_workflow` at the end of the submitted run, and **zero** of its tool URLs point anywhere but the mock.
3. **One trace, from that run.** `traces/case-1.log` has `start:`, one `model call:` line per model call with model and purpose, the `freya:` ids matching the exported workflow's ids, any `test:` line, `export:`, and `end: ... UTC`.
4. **`submission.json` complete and clean.** `members[]` lists the registered team (both members if two); `workflow`, `trace` and `mock_url` present and pointing at real, checked things; no API keys anywhere in `submission/` or `traces/`.
5. **Local validation recorded.** The run against the 6 example conversations is in `results/final-local.json` with its pass/fail line and the known gaps, and the judgement line is in `tests/findings.md`.
6. **The commit.** `git log -1` shows the commit containing the workflow, the trace, `submission.json`, the mock source and the findings; the builder diff since T-0 contains bug fixes only, with no rule, value, name, outcome, holiday or customer from the case in the code or prompts.
7. **Sent, on time, and still serving.** The email went to the address in the kit email before **20:00 UTC** (19:45 target), with the workflow, the trace and the `mock_url` in the body; the send time, commit and score are noted; and the mock worker is still deployed and answering at the close, to stay up until results are out.
