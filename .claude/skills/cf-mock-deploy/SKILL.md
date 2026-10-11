---
name: cf-mock-deploy
description: Generate the bank mock from a case folder, deploy it to Cloudflare Workers over the REST API (no wrangler on this machine), smoke-test the exact round trip, and re-check or redeploy it. Use for all Cloudflare mock work in the final window.
---

# Deploy the bank mock to Cloudflare Workers

Work from the kit folder. Credentials live in `env.sh` (gitignored): `CF_API_TOKEN`/`CF_ACCOUNT_ID` (deploy.sh reads these) and `CLOUDFLARE_API_TOKEN`/`CLOUDFLARE_ACCOUNT_ID` (the runbook reads these). Never print the token; only `$CF_API_TOKEN` references. Run the phases 0→3 in order at the window, then 4 as needed.

## Phase 0 — Preflight: token, account, subdomain (idempotent)

```bash
source env.sh
: "${CF_API_TOKEN:?set CF_API_TOKEN in env.sh}" "${CF_ACCOUNT_ID:?set CF_ACCOUNT_ID in env.sh}"
curl -sS "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/tokens/verify" \
  -H "Authorization: Bearer $CF_API_TOKEN" | jq -c '{success, status: .result.status}'
curl -sS "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID" \
  -H "Authorization: Bearer $CF_API_TOKEN" | jq -c '{success, name: .result.name}'
curl -sS "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/workers/subdomain" \
  -H "Authorization: Bearer $CF_API_TOKEN" | jq -c '{success, subdomain: .result.subdomain}'
curl -sS "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/workers/scripts" \
  -H "Authorization: Bearer $CF_API_TOKEN" | jq -c '[.result[].id]'
```

Expected today: verify `status: "active"`, account name `Fcodefcode3@gmail.com's Account`, subdomain `fcodefcode3`, scripts `server` and `vite-react-template` (never touch those two). Save the subdomain:

```bash
SUBDOMAIN=$(curl -sS "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/workers/subdomain" \
  -H "Authorization: Bearer $CF_API_TOKEN" | jq -r '.result.subdomain // empty')
echo "SUBDOMAIN=$SUBDOMAIN" >> traces/mock-deploy.log
```

- Verify fails / error 10000 → STOP, tell the human: dash.cloudflare.com → My Profile → API Tokens → Create Token → template **Edit Cloudflare Workers** → Account Resources: include `0d4595c62105dd425f1243397467e35c` → paste into `env.sh` → `source env.sh` → rerun Phase 0.
- Subdomain empty → register: `curl -sS -X PUT .../workers/subdomain -d '{"subdomain":"<pick-one>"}'`; API refuses → dashboard → Workers & Pages → workers.dev → register there.
- Deploy fails later with 403/permission → same token fix (needs Workers Scripts:Edit).

## Phase 1 — Locate contract + customers, generate

```bash
CASE_DIR=cases/final/case-1          # runbook Block 1 (unzip first)
python3 - "$CASE_DIR" <<'PY'
import json, pathlib, re, sys
root = pathlib.Path(sys.argv[1]); jsons, custs = [], []
for f in sorted(root.rglob("*.json")):
    try: d = json.loads(f.read_text())
    except Exception: continue
    if isinstance(d, dict) and "paths" in d and ("openapi" in d or "swagger" in d): jsons.append(f)
for f in sorted(root.rglob("*")):
    if f.suffix.lower() in (".xlsx", ".csv", ".json", ".md", ".docx") and f not in jsons \
       and re.search(r"customer|müşteri|musteri|müsteri|test|kişi|kisi", f.name.lower()):
        custs.append(f)
need = {"verify_identity", "get_account", "create_promise", "close_call"}
def rank(c):
    p = set(json.loads(c.read_text()).get("paths", {}))
    return (bool(p & need), c.name.endswith(".openapi.json"), c.name == "openapi.json", str(c))
def crank(c): return (c.suffix.lower() in (".xlsx", ".json"), "customer" in c.name.lower(), str(c))
print("CONTRACT=" + (str(sorted(jsons, key=rank, reverse=True)[0]) if jsons else ""))
print("CUSTOMERS=" + (str(sorted(custs, key=crank, reverse=True)[0]) if custs else ""))
for c in jsons: print("   contract candidate:", c)
for c in custs: print("   customers candidate:", c)
PY
```

Take the printed pair; eyeball both (one line). Override a bad pick with `export MOCK_CONTRACT=<path> MOCK_CUSTOMERS=<path>` and rerun. Empty CONTRACT = STOP (the contract JSON is required). If customers is .xlsx/.csv/.docx, convert to text first with `builder/read_case.py`'s `read_case_folder` (openpyxl/docx installed) and point MOCK_CUSTOMERS at the .txt.

Generate (model calls via the claude CLI; budget ~5–10 min, transient DeepSeek rate-limits recover on rerun):

```bash
MOCK_NAME=freya-final-case1
python3 builder/mock_gen.py "$MOCK_CONTRACT" "$MOCK_CUSTOMERS" \
  --out mock/final --name "$MOCK_NAME" 2>&1 | tee -a traces/mock-deploy.log
```

Gate: `mock/final/worker.js` + `endpoints.json` + `seed.json` exist and the log shows validation ok (exit 3 = stopped early, do not deploy).

Compute the URLs — `build.py` concatenates mock base + contract path literally, so the base must carry the contract's path prefix:

```bash
MOCK_BASE="https://$MOCK_NAME.$SUBDOMAIN.workers.dev"
PREFIX=$(python3 - "$MOCK_CONTRACT" <<'PY'
import json, sys
from urllib.parse import urlsplit
d = json.load(open(sys.argv[1]))
s = (d.get("servers") or [{}])[0].get("url", "") or ""
base = urlsplit(s if "//" in s else "https://x" + s).path.rstrip("/")
first = next((p for p in (d.get("paths") or {}) if not p.startswith("x-")), "")
print("" if (base and first.startswith(base)) else base)
PY
)
MOCK_URL="$MOCK_BASE$PREFIX"
echo "$MOCK_URL"  > out/final-mock-url.txt
echo "$MOCK_BASE" > out/final-mock-host.txt
echo "$MOCK_URL"   # sanity: expect https://...workers.dev/v1
```

## Phase 2 — Deploy (REST, no wrangler)

```bash
mock/deploy.sh --dir mock/final --rest --with-kv --timeout 15 --retries 12 2>&1 | tee -a traces/mock-deploy.log
```

- KV step fails → rerun WITHOUT `--with-kv` (memory-only worker).
- Fails twice → raw-curl fallback (note: `worker.js`, not the runbook's `worker.mjs`):

```bash
COMPAT=$(python3 -c "print(next(l.split('=',1)[1].strip().strip('\"') for l in open('mock/final/wrangler.toml') if l.strip().startswith('compatibility_date')))")
curl -sS -X PUT "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/workers/scripts/$MOCK_NAME" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -F "metadata={\"main_module\":\"worker.js\",\"compatibility_date\":\"$COMPAT\"};type=application/json" \
  -F "worker.js=@mock/final/worker.js;type=application/javascript+module" | jq '{success, errors}'
curl -sS -X POST "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/workers/scripts/$MOCK_NAME/subdomain" \
  -H "Authorization: Bearer $CF_API_TOKEN" -H "content-type: application/json" \
  -d '{"enabled":true}' | jq '{success, errors}'
mock/deploy.sh --health-only --dir mock/final --url "$MOCK_BASE"
```

Gate: `== deploy.sh done:` line and `jq -r .url mock/final/deployed.json` == `$MOCK_BASE` (deploy.sh probes root `/health`, then every GET probe from endpoints.json).

## Phase 3 — Smoke: exact round trip (never skip)

```bash
MOCK_URL="$(cat out/final-mock-url.txt)"; MOCK_BASE="$(cat out/final-mock-host.txt)"
curl -sS -o /dev/null -w 'health root: %{http_code}\n' "$MOCK_BASE/health"    # gate: 200
curl -sS -o /dev/null -w 'health base: %{http_code}\n' "$MOCK_URL/health"     # informative only
FIRST=$(python3 -c "import json;print(json.load(open('mock/final/seed.json'))['customers'][0]['customer_id'])")
```

Session A — the pre-identity gate (exact string the scorer checks) and unknown-id determinism:

```bash
CID1=$(curl -sS -X POST "$MOCK_URL/practice/sessions" -H "content-type: application/json" \
  -H "x-team-key: $FREYA_BANK_TEAM_KEY" -d "{\"case\":\"$FIRST\"}" | jq -r '.variables.customer_id')
test -n "$CID1" || echo "SESSION ROUTE BROKEN"
curl -sS -X POST "$MOCK_URL/get_account" -H "content-type: application/json" \
  -d "{\"customer_id\":\"$CID1\"}" | jq -e '.ok == false and .error == "identity not verified"'
curl -sS -X POST "$MOCK_URL/create_promise" -H "content-type: application/json" \
  -d "{\"customer_id\":\"$CID1\",\"product_id\":\"p1\",\"amount\":100,\"date\":\"2026-10-15\"}" \
  | jq -e '.ok == false and .error == "identity not verified"'
curl -sS -o /dev/null -w 'unknown-id get_account: %{http_code}\n' -X POST "$MOCK_URL/get_account" \
  -H "content-type: application/json" -d '{"customer_id":"UNKNOWN-999"}'     # 200, never 5xx
```

Session B — clean round trip, values driven by the seed and the contract (no hardcoded case data):

```bash
CID2=$(curl -sS -X POST "$MOCK_URL/practice/sessions" -H "content-type: application/json" \
  -H "x-team-key: $FREYA_BANK_TEAM_KEY" -d "{\"case\":\"$FIRST\"}" | jq -r '.variables.customer_id')
LAST=""
while read FIELD ANSWER; do
  LAST=$(curl -sS -X POST "$MOCK_URL/verify_identity" -H "content-type: application/json" \
    -d "{\"customer_id\":\"$CID2\",\"field\":\"$FIELD\",\"answer\":\"$ANSWER\"}")
done < <(jq -r '.customers[0].identity | to_entries[] | "\(.key) \(.value)"' mock/final/seed.json)
jq -e '.ok == true and .all_verified == true' <<<"$LAST" || echo "VERIFY FAILED: $LAST"
ACC=$(curl -sS -X POST "$MOCK_URL/get_account" -H "content-type: application/json" -d "{\"customer_id\":\"$CID2\"}")
echo "$ACC" | jq -e '.ok == true'
PROD=$(jq -r '.products[0].product_id' <<<"$ACC")
curl -sS -X POST "$MOCK_URL/create_promise" -H "content-type: application/json" \
  -d "{\"customer_id\":\"$CID2\",\"product_id\":\"$PROD\",\"amount\":100,\"date\":\"2026-10-15\"}" \
  | jq -e '.ok == true'
OUTCOME=$(python3 - "$MOCK_CONTRACT" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
for p, item in (d.get("paths") or {}).items():
    if p.endswith("/close_call"):
        s = item.get("post", {}).get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
        for k in ("outcome", "disposition", "result"):
            e = (s.get("properties") or {}).get(k, {}).get("enum")
            if e: print(e[0]); raise SystemExit
print("")
PY
)
test -n "$OUTCOME" || echo "NO OUTCOME ENUM — read the close_call schema in the contract"
curl -sS -X POST "$MOCK_URL/close_call" -H "content-type: application/json" \
  -d "{\"customer_id\":\"$CID2\",\"outcome\":\"$OUTCOME\"}" | jq -e '.ok == true'
```

Exact ledger checks (what score.py reads):

```bash
LED2=$(curl -sS "$MOCK_URL/practice/ledger/$CID2" -H "x-team-key: $FREYA_BANK_TEAM_KEY")
N=$(jq '.customers[0].identity | length' mock/final/seed.json)
jq -e --argjson n "$N" --arg prod "$PROD" --arg out "$OUTCOME" '
  .outcome == $out and .promises[0].product_id == $prod and .promises[0].amount == 100
  and (.calls | length == $n + 3)
  and ([.calls[0:$n][].tool] | all(. == "verify_identity"))
  and .calls[$n].tool == "get_account" and .calls[$n+1].tool == "create_promise"
  and .calls[$n+2].tool == "close_call"' <<<"$LED2"
LED1=$(curl -sS "$MOCK_URL/practice/ledger/$CID1" -H "x-team-key: $FREYA_BANK_TEAM_KEY")
jq -e '.calls[0].tool == "get_account" and .calls[0].result.error == "identity not verified"' <<<"$LED1"
```

Optional after the gates: add_note / schedule_callback / transfer_to_agent with bodies from the contract's own enums (same extraction trick as OUTCOME) — a failure there is a note, not a block.

Handoff (the scorer now scores OUR mock — bare host, score.py appends `/v1/practice/ledger/{id}` itself):

```bash
export FREYA_BANK_HOST="$MOCK_BASE"
echo "MOCK_URL=$MOCK_URL MOCK_HOST=$MOCK_BASE NAME=$MOCK_NAME $(date -u +%FT%TZ)" >> traces/mock-deploy.log
```

Next: `python3 builder/build.py cases/final/case-1 "$MOCK_URL"` (runbook Block 4). No workflow work before this phase is green.

## Phase 4 — Status / redeploy (any time later)

```bash
source env.sh
MOCK_BASE="$(cat out/final-mock-host.txt)"
curl -sS -o /dev/null -w 'health: %{http_code}\n' "$MOCK_BASE/health"
mock/deploy.sh --health-only --dir mock/final --url "$MOCK_BASE"
curl -sS "https://api.cloudflare.com/client/v4/accounts/$CF_ACCOUNT_ID/workers/scripts" \
  -H "Authorization: Bearer $CF_API_TOKEN" | jq '.result[].id'
# redeploy: same dir -> same name -> same URL; in-memory state resets (fresh sessions, fine)
mock/deploy.sh --dir mock/final --rest 2>&1 | tee -a traces/mock-deploy.log
jq -r .url mock/final/deployed.json   # MUST equal $MOCK_BASE; if it changed, update out/final-mock-url.txt
                                       # + rebuild + submission.json in the same minute
```

Keep the worker running until results are out — no teardown, no delete. After submission, redeploy only the exact submitted source.

## Failure table

| Symptom | Meaning / action |
|---|---|
| verify fails / error 10000 | token not valid for the account → new token (Phase 0 box) |
| PUT fails 403 / permission errors | token lacks Workers Scripts:Edit → fix token permissions |
| `/health` never 200 | redeploy; read `mock/final/deployed.json`; still down → dashboard |
| get_account before identity returns `ok: true` | worker identity gate broken → regenerate |
| create_promise before identity returns `ok: true` | identity gate missing on promise too (known finding: the analysis step keeps missing it) → regenerate |
| ledger last call ≠ `close_call` | smoke sequence skipped close_call or the worker did not record it |
| deploy log leaks a key | scrub it from the log before commit (Rules, below) |

## Rules

- Never print the token. Sweep before commit: `grep -rnE "cfat_|cfut_|Bearer [A-Za-z0-9]{20,}" out/ traces/ submission/ mock/ 2>/dev/null` must return nothing.
- `env.sh` stays uncommitted (`git check-ignore env.sh` must print it).
- No real case data in `builder/` code or prompts — case data lives in `cases/`, `mock/final`, `traces`.
- One worker per name; redeploys never change the workers.dev URL.
- Deploy once, early (T+0:30–0:45); smoke before any workflow work.
