# TEMPLATE_NOTES.md — how the mock generator is designed, and what it must guarantee

`builder/mock_gen.py` turns a final package's SERVICE CONTRACT + TEST CUSTOMERS into a
Cloudflare Worker mock bank. This file is the design record: what the model is asked to
produce, what is deterministic, and the checklist a generated mock is validated against.

At 17:00 the contract is unknown, so everything here is contract-agnostic: the generator
*reads* the contract and emits a worker that implements it. Nothing about the practice
briefs is baked into the generator (the practice contract is only ever an input, in
`mock/dryrun/`).

## Pipeline

```
contract + customers
   |-- analysis call   -> analysis.json   (endpoints, identity, ledger, sessions, faults)
   |-- seed call       -> seed.json       (customers normalised for the worker)
   |-- worker call     -> worker.js       (one complete Worker ES module)
   |-- validation      -> repair call(s)  (up to --repairs, default 2)
   |-- artefacts       -> endpoints.json, wrangler.toml, README.md, gen-trace.log
```

Model calls use the same `claude` CLI pattern as `builder/build.py`: `subprocess claude
-p <prompt> --output-format json --model claude-sonnet-5-5`, environment stripped of
`ANTHROPIC_MODEL` / `CLAUDE_CODE_SUBAGENT_MODEL` / `CLAUDE_MODEL*` / `ANTHROPIC_DEFAULT_*`,
falling back to the CLI default model on `unrecognized_model`, answer read from the
`result` field. Each call is one line in `gen-trace.log` (model, purpose, prompt/answer
sizes, seconds) mirroring the builder's trace style.

Deterministic fallbacks (no model call) keep the pipeline alive if a call fails:
`naive_analysis()` parses an OpenAPI JSON contract, `naive_seed()` normalises a JSON
customers file. A Markdown contract has no deterministic fallback — the analysis call is
required for it (that is the "raw bank material" case, so the analysis prompt accepts
Markdown, JSON or a mix, and the contract+analysis are also given to the worker call so
the model sees the original text, not only the digest).

## What the worker-generation prompt demands

The worker prompt is `analysis (authoritative) + seed + contract verbatim + customers
verbatim + a template skeleton`. The skeleton is *helper-complete*: `json()`,
`canonPath()`, `findSeed()`, `derivedSeed()`, `freshState()`, `loadState()`,
`saveState()`, `record()`, `ledgerView()`, `verifiedGate()`, `takeFault()`,
`handleCreateSession()`, the CORS/OPTIONS layer and `/health` are all written out — the
model replaces only the per-endpoint handlers. This is deliberate: the parts a model
gets wrong at speed (state plumbing, ledger ordering, path normalisation) are the parts
it does not have to write.

The prompt's non-negotiables (numbered 1-16 in the prompt itself):

1. one self-contained Workers file, `export default { async fetch(request, env, ctx) }`,
   no imports, no Node APIs;
2. exactly one `const SEED = __SEED_JSON__;` line, replaced by the generator with the
   real seed — seed data is never retyped by the model (a retyped 22 KB blob is a
   mutation waiting to happen);
3. every contract endpoint: exact path, method, request field names/types/enums,
   response field names/types, validated inputs;
4. exact error strings, the identity refusal being the load-bearing one
   (`"identity not verified"` in the practice contract);
5. the ledger: every call recorded once as
   `{seq, at, customer_id, tool, request, result}` — `result` is the exact response body
   sent, failures included;
6. ledger read routes:
   `GET <base>/practice/ledger/<customer_id>` returning at least
   `{customer_id, outcome, reason, promises[{product_id,amount,date}],
   notes[{product_id,reason}], callbacks[{date,time}], transfers[{queue}],
   identity{verified,wrong_answers,locked}, closed, calls[]}` — the shape `tools/score.py`
   reads from the practice ledger — plus `GET <base>/practice/ledger` and
   `GET <base>/practice/sessions`;
7. sessions: `POST <base>/practice/sessions` `{"case": id}` -> `{"variables": {..., customer_id}}`
   with a fresh `-sN` id and a clean state; a contract-defined session/registration
   endpoint is implemented exactly as well;
8. unknown customer ids never 500: contract policy first, else a deterministic derived
   record (hidden cases must not crash the mock);
9. identity enforced server-side (fields, order, wrong-answer counting, what is *not*
   counted as wrong, hints, lockout, gated endpoints);
10. contract faults (e.g. "the promise service fails on the first call") implemented
    deterministically per session and recorded with their exact error response;
11. state: in-memory Map authoritative, optional `env.MOCK_KV` mirror (`ctx.waitUntil`
    on writes, hydrate on miss), never required;
12. `/health` -> 200 with `{ok, status, service, customers}`, no auth, never gated;
13. CORS on every response, `OPTIONS` -> 204, `canonPath` accepts the path with and
    without the base prefix (scorers and tools may disagree about trailing slashes);
14. status codes: 200 for contract semantics *including* `ok:false` refusals, 404
    unknown path, 405 wrong method, 500 only for contract faults;
15. numbers stay numbers, dates `YYYY-MM-DD` strings;
16. try/catch everywhere; an unexpected exception is `{"ok":false,"error":"internal error"}`.

## Correctness checklist (deterministic validation, feeds the repair loop)

`validate_worker()` runs after every generation and after each repair; the model is shown
the failures and asked for the complete corrected file. Checks, in order:

| Check | Why it exists |
|---|---|
| `export default` + `async fetch(` present | a Worker that cannot deploy is worthless |
| `/health` route present | the deploy health check and uptime depend on it |
| no leftover `__SEED_JSON__` placeholder | the seed must actually be embedded |
| `SEED.customers` is read | catches a worker that retyped/ignored the seed |
| **every contract endpoint path appears as a route** (comment-stripped; regex `\/` spellings accepted; parameterised paths checked by static prefix) | the phone agent's tools must not 404 |
| every ledger read route + the session route present | the scorer reads these; hidden runs depend on them |
| `MOCK_KV` present when `state_model == cross-call` | cross-call state must survive an isolate change |
| no `import`, no `require(`, `process.`, `Buffer`, `__dirname`, `module.exports` | Workers runtime is not Node |
| delimiter balance (strings/comments/regex-aware heuristic) | catches the classic truncated answer |

Deliberate limits of the checker: it is a Python heuristic (no `node --check` in this
environment), it verifies *presence and shape*, not schema correctness — semantics come
from the model reading the contract, which is why the contract, the analysis and the
customers are all in the prompt. Comment-stripping is what makes the route checks honest:
the header comment lists endpoint paths, and without stripping, the check would pass on
the comment alone.

## Contract-driven decisions the generator encodes

Every one of these was derived from the practice contract (`tools/openapi.json` +
`tools/score.py`) and generalised, because the practice shape is the only evidence of
what the final's tooling will expect:

1. **Ledger-first**: the scorer never trusts the phone agent; it reads the bank's record.
   A mock that does not record is a mock that fails every case, so `record()` is in the
   skeleton, not left to the model.
2. **Exact refusal string**: `"identity not verified"` is compared literally by
   `score.py` (`c["result"].get("error") == "identity not verified"`). The prompt calls
   out exact error strings as non-negotiable.
3. **Ledger read routes**: the practice mock exposes `GET /v1/practice/ledger/<id>`
   (with `x-team-key` auth upstream — the generated mock does not require the key, since
   the graders' harness supplies auth and a 401 here would read as unreachable). The
   generated routes mirror the practice path so a scorer pointed at our host works
   unchanged.
4. **Sessions mint fresh ids**: `run_cases.py` opens `POST /v1/practice/sessions`
   per case and stores `variables.customer_id`; repetitions must not share state, so a
   session gets a new id and a *clean* state every time. Copying the seed's variable set
   into `variables` matches how the phone agent receives its call variables.
5. **Unknown ids never 500**: hidden cases may use ids not in the seed; the practice
   mock answers from its own store for anything, so the generated one derives a
   deterministic record instead of erroring.
6. **Fault injection is part of the contract**: PUB-10 is "the promise service fails on
   the first call" — a mock that cannot fail makes that case untestable. The analysis
   prompt extracts faults; the template has `takeFault()`; the worker prompt forbids
   inventing faults the contract does not describe.
7. **Base prefix handled both ways**: the contract's `servers[0].url` carries `/v1`
   (builder/gen.py concatenates it onto paths), but graders sometimes call the bare
   path. `canonPath` accepts both; the manifest probes use the full contract path.
8. **`/health` is unconditional**: the deploy script's health check is the first thing
   that runs at 17:00; it must not depend on auth, identity or state.
9. **Status semantics keep refusals at 200**: the practice mock returns `ok:false`
   refusals with HTTP 200; the scorer inspects bodies. A mock that 400s refusals would
   break tools that treat non-2xx as transport failure.

## Persistence: the trade-off and the decision

Workers are ephemeral: module-scope state is per-isolate and can vanish between
requests. The generated worker's stance:

* **in-memory Map is authoritative** (`globalThis.__MOCK_STATE__`) — deterministic inside
  an isolate, zero setup, no extra binding to get wrong at 17:00;
* **KV mirror is generated when the analysis says cross-call** (`env.MOCK_KV`): every
  mutation is `ctx.waitUntil`-written and a state miss hydrates from KV. Without the
  binding the worker still runs, in memory only;
* **Durable Objects are documented, not generated**: strict cross-isolate consistency is
  what a grading harness hammering one mock would want, but a DO needs a class export
  plus a migrations block — more moving parts than a mirror, and this worker is generated
  minutes before it must be up.

`wrangler.toml` carries the KV block with a `REPLACE_WITH_KV_NAMESPACE_ID` placeholder
when cross-call; `mock/deploy.sh --with-kv` creates the namespace and binds it, both on
the wrangler path and on the REST path (binding in the script `metadata`).

## Artefacts and how to run it

```
python3 builder/mock_gen.py <contract> <customers> --out mock/run      # generate
python3 builder/mock_gen.py <contract> <customers> --selftest          # no model calls
bash mock/deploy.sh --dry-run --dir mock/run                           # show the plan
export CF_API_TOKEN=... CF_ACCOUNT_ID=...
bash mock/deploy.sh --dir mock/run [--with-kv]                         # deploy + health check
```

* `worker.js` — the deployable file; `seed.json` — the embedded seed, readable;
* `analysis.json` — what the generator believed the contract says (diff it against the
  contract before trusting a run; a wrong analysis is the likeliest silent failure);
* `endpoints.json` — route manifest + `get_probes` the health check walks;
* `README.md` — the generated runbook (endpoints, ledger shape, persistence, deploy);
* `gen-trace.log` — model calls, attempts, validation results, timings.

`endpoints.json`, `analysis.json` and `gen-trace.log` are for the team; `worker.js` +
`seed.json` + `wrangler.toml` are what deploy. The mock is deployed with the team's own
Cloudflare account (`CF_API_TOKEN` + `CF_ACCOUNT_ID`); nothing here touches Freya.
