#!/usr/bin/env bash
# deploy.sh — deploy a generated mock bank Worker to Cloudflare and health-check it.
#
#   export CF_API_TOKEN=...        # Cloudflare API token, Workers Scripts:Edit (+ KV if --with-kv)
#   export CF_ACCOUNT_ID=...
#   mock/deploy.sh --dir mock/     # deploy + health check
#   mock/deploy.sh --health-only --url https://<worker>.<subdomain>.workers.dev
#
# Deploy path, in order of preference:
#   1. npx wrangler deploy        (used when npx exists and --rest was not passed)
#   2. Cloudflare REST API        PUT /accounts/{account_id}/workers/scripts/{name}
#      (fallback; also what runs when node/npx is not installed). Implemented with
#      python3's stdlib (urllib) — no node, no wrangler, no curl needed. The curl
#      one-liners in FINAL_RUNBOOK Block 3 remain the manual fallback if this breaks.
#
# URL resolution: after the upload the script enables the workers.dev route, reads the
# account subdomain and prints the deployed host AND the submission URL with the
# contract base path (contract analysis -> endpoints.json -> base_path), e.g.
#    deployed: https://name.subdomain.workers.dev
#    mock url: https://name.subdomain.workers.dev/v1
# deployed.json records url, base_path and mock_url; mock_gen.py prints MOCK_URL from
# mock_url, which is the value builder/build.py wants (it appends the tool paths).
#
# --with-kv creates a KV namespace MOCK_KV, binds it (the worker then mirrors its ledger
# to KV so state survives a change of Worker isolate) and records the id in
# deploy.wrangler.toml / deployed.json. Without it, the KV block is stripped for the
# deploy: the worker runs fully in memory.
#
# The post-deploy health check pings /health (with retries — a fresh worker takes a
# moment to propagate) and then every GET route from endpoints.json; each probe prints
# PASS/FAIL and the result is recorded in deployed.json next to the worker.
#
# Flags: --dir DIR --name NAME --url URL --with-kv --rest --wrangler --health-only
#        --no-health --dry-run --timeout SECONDS --retries N --insecure
set -euo pipefail

usage() {
  sed -n '2,34p' "$0" | sed 's/^# \{0,1\}//'
}

DIR=""
NAME=""
URL=""
MODE="auto"          # auto | wrangler | rest
WITH_KV=0
HEALTH=1
HEALTH_ONLY=0
DRY_RUN=0
TIMEOUT=15
RETRIES=12
INSECURE=0

die() { echo "deploy.sh: $*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --dir) DIR="${2:-}"; shift 2;;
    --name) NAME="${2:-}"; shift 2;;
    --url) URL="${2:-}"; shift 2;;
    --with-kv) WITH_KV=1; shift;;
    --rest) MODE="rest"; shift;;
    --wrangler) MODE="wrangler"; shift;;
    --health-only) HEALTH_ONLY=1; shift;;
    --no-health) HEALTH=0; shift;;
    --dry-run) DRY_RUN=1; shift;;
    --timeout) TIMEOUT="${2:-}"; shift 2;;
    --retries) RETRIES="${2:-}"; shift 2;;
    --insecure) INSECURE=1; shift;;
    -h|--help) usage; exit 0;;
    *) die "unknown flag: $1 (try --help)";;
  esac
done

# The runbook's env.sh also carries the CLOUDFLARE_* spellings; accept either.
CF_API_TOKEN="${CF_API_TOKEN:-${CLOUDFLARE_API_TOKEN:-}}"
CF_ACCOUNT_ID="${CF_ACCOUNT_ID:-${CLOUDFLARE_ACCOUNT_ID:-}}"
export CF_API_TOKEN CF_ACCOUNT_ID

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR="${DIR:-$HERE}"
[ -d "$DIR" ] || die "no such directory: $DIR"
DIR="$(cd "$DIR" && pwd)"

WORKER="$DIR/worker.js"
MANIFEST="$DIR/endpoints.json"

if [ "$HEALTH_ONLY" -eq 0 ] && [ "$DRY_RUN" -eq 0 ]; then
  [ -f "$WORKER" ] || die "no worker.js in $DIR — generate it first, e.g.
       python3 builder/mock_gen.py <contract> <customers> --out $DIR"
  [ -f "$MANIFEST" ] || echo "deploy.sh: warning: no endpoints.json in $DIR; health check will ping /health only" >&2
fi

# worker name: --name, else endpoints.json, else wrangler.toml, else the directory name
if [ -z "$NAME" ]; then
  if [ -f "$MANIFEST" ]; then
    NAME="$(python3 -c 'import json,sys
try: print(json.load(open(sys.argv[1])).get("worker_name") or "")
except Exception: print("")' "$MANIFEST")"
  fi
  if [ -z "$NAME" ] && [ -f "$DIR/wrangler.toml" ]; then
    NAME="$(sed -n 's/^name[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$DIR/wrangler.toml" | head -1)"
  fi
  if [ -z "$NAME" ]; then
    NAME="$(basename "$DIR")"
  fi
fi
case "$NAME" in
  *[!a-z0-9-]*) die "worker name '$NAME' must be lowercase letters, digits and dashes";;
esac

if [ "$MODE" = "auto" ]; then
  if command -v npx >/dev/null 2>&1; then MODE="wrangler"; else MODE="rest"; fi
fi
if [ "$MODE" = "wrangler" ] && ! command -v npx >/dev/null 2>&1; then
  echo "deploy.sh: npx not found — falling back to the REST API" >&2
  MODE="rest"
fi

if [ "$DRY_RUN" -eq 1 ]; then
  echo "== deploy plan =="
  echo "   dir:        $DIR"
  echo "   worker:     $WORKER"
  echo "   name:       $NAME"
  echo "   path:       $MODE"
  echo "   with-kv:    $WITH_KV"
  echo "   health:     $HEALTH (health-only: $HEALTH_ONLY)"
  echo "   url:        ${URL:-(resolved after deploy)}"
  echo "   token:      $([ -n "${CF_API_TOKEN:-}" ] && echo set || echo 'MISSING (export CF_API_TOKEN)')"
  echo "   account:    ${CF_ACCOUNT_ID:-MISSING (export CF_ACCOUNT_ID)}"
  exit 0
fi

if [ "$HEALTH_ONLY" -eq 0 ]; then
  [ -n "${CF_API_TOKEN:-}" ] || die "CF_API_TOKEN is not set (export CF_API_TOKEN=...)"
  [ -n "${CF_ACCOUNT_ID:-}" ] || die "CF_ACCOUNT_ID is not set (export CF_ACCOUNT_ID=...)"
fi

health_check() {
  # args: url
  local target="$1"
  python3 - "$target" "$MANIFEST" "$TIMEOUT" "$RETRIES" "$INSECURE" "$DIR" "$NAME" <<'PY'
import json, os, ssl, sys, time, urllib.error, urllib.request
from urllib.parse import urlsplit

url, manifest_path, timeout, retries, insecure, outdir, name = sys.argv[1:8]
timeout, retries, insecure = float(timeout), int(retries), insecure == "1"
ctx = ssl._create_unverified_context() if insecure else None
target = url.rstrip("/")

def get(path):
    req = urllib.request.Request(target + path, headers={"user-agent": "mock-health/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.status, r.read(200000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read(200000).decode("utf-8", "replace")
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"

probes = ["/health"]
probe_of = {"/health": "/health"}
base_path = ""
if manifest_path and os.path.exists(manifest_path):
    try:
        man = json.load(open(manifest_path))
        base_path = (man.get("base_path") or "").rstrip("/")
        for p in man.get("get_probes") or []:
            path = p.get("path") or ""
            if path and path not in probe_of:
                probes.append(path)
                probe_of[path] = p.get("probe_of", path)
    except Exception as e:
        print(f"   warning: could not read {manifest_path}: {e}")

# The URL may be handed in with the contract's base path (the runbook's MOCK_URL is
# https://host/v1): the probe paths below already carry it, so the health target is
# the bare host.
if base_path and urlsplit(target).path.rstrip("/") == base_path:
    target = target[: -len(base_path)].rstrip("/")

def probe(path):
    code, body = get(path)
    if code == 0:
        return False, code, body[:200]
    if path == "/health":
        ok = code == 200
    else:
        ok = code < 500 and code != 0
        if code == 404:
            ok = False
    return ok, code, body[:200]

print(f"== health check: {target} ==")
health_ok = False
for attempt in range(1, retries + 1):
    ok, code, body = probe("/health")
    if ok:
        health_ok = True
        print(f"   PASS /health -> {code} {body[:120]}")
        break
    if attempt == 1 or attempt % 3 == 0:
        print(f"   waiting for /health ... attempt {attempt}/{retries}: {code} {body[:120]}")
    time.sleep(3)
if not health_ok:
    print("   FAIL /health never returned 200")

results = []
for path in probes[1:]:
    ok, code, body = probe(path)
    mark = "PASS" if ok else "FAIL"
    print(f"   {mark} GET {probe_of[path]} -> {code} {body[:160]}")
    results.append({"path": probe_of[path], "status": code, "pass": ok})

passed, total = sum(1 for r in results if r["pass"]), len(results)
print(f"   health: {'ok' if health_ok else 'FAILED'}; get endpoints: {passed}/{total} passed")

out = {"url": target, "base_path": base_path,
       "mock_url": (target + base_path) if base_path else target,
       "worker_name": name, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "health": health_ok, "get_probes": results, "passed": passed, "total": total}
try:
    with open(os.path.join(outdir, "deployed.json"), "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print(f"   wrote {os.path.join(outdir, 'deployed.json')}")
except Exception as e:
    print(f"   warning: could not write deployed.json: {e}")

sys.exit(0 if health_ok and passed == total else 1)
PY
}

deploy_rest() {
  python3 - "$DIR" "$NAME" "$WITH_KV" "$DRY_RUN" <<'PY'
import json, os, sys, urllib.request, urllib.error, uuid

outdir, name, with_kv, dry = sys.argv[1:5]
with_kv, dry = with_kv == "1", dry == "1"
acct = os.environ.get("CF_ACCOUNT_ID", "")
tok = os.environ.get("CF_API_TOKEN", "")
# CF_API_BASE exists so the REST path can be exercised against a local stub of the
# Cloudflare API; in normal use it is unset and the real API is called.
api_base = (os.environ.get("CF_API_BASE") or "https://api.cloudflare.com/client/v4").rstrip("/")
api = f"{api_base}/accounts/{acct}"
headers = {"authorization": "Bearer " + tok, "user-agent": "mock-deploy/1.0"}

# The contract base path (e.g. /v1) — appended to the deployed host so the printed
# URL and deployed.json carry what build.py and the submission need.
base_path = ""
try:
    base_path = (json.load(open(os.path.join(outdir, "endpoints.json")))
                 .get("base_path") or "").rstrip("/")
except Exception:
    pass

def call(method, path, body=None, raw=None, ctype=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    h = dict(headers)
    if ctype:
        h["content-type"] = ctype
    elif body is not None:
        h["content-type"] = "application/json"
    req = urllib.request.Request(api + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:800]
        raise SystemExit(f"REST {method} {path} failed: HTTP {e.code}: {detail}")

# --- optional KV namespace MOCK_KV -------------------------------------------------
binding = None
if with_kv:
    title = f"{name}-MOCK_KV"
    found = None
    page = 1
    while page <= 10 and not found:
        res = call("GET", f"/storage/kv/namespaces?per_page=100&page={page}")
        for ns in res.get("result") or []:
            if ns.get("title") == title:
                found = ns
                break
        if not res.get("result_info") or page >= (res["result_info"].get("total_pages") or 1):
            break
        page += 1
    if not found:
        found = call("POST", "/storage/kv/namespaces", {"title": title})["result"]
        print(f"   created KV namespace {title}: {found['id']}")
    else:
        print(f"   reusing KV namespace {title}: {found['id']}")
    binding = {"type": "kv_namespace", "name": "MOCK_KV", "namespace_id": found["id"]}

worker = open(os.path.join(outdir, "worker.js"), "rb").read()
compat = "2026-10-01"
cfg = os.path.join(outdir, "wrangler.toml")
if os.path.exists(cfg):
    for line in open(cfg):
        if line.strip().startswith("compatibility_date"):
            compat = line.split("=", 1)[1].strip().strip('"')
metadata = {"main_module": "worker.js", "compatibility_date": compat}
if binding:
    metadata["bindings"] = [binding]

boundary = "----mockdeploy" + uuid.uuid4().hex
def part(field, content, ctype):
    head = (f"--{boundary}\r\ncontent-disposition: form-data; name=\"{field}\"\r\n"
            f"content-type: {ctype}\r\n\r\n").encode()
    body = content if isinstance(content, bytes) else content.encode()
    return head + body + b"\r\n"

multipart = (part("metadata", json.dumps(metadata), "application/json")
             + part("worker.js", worker, "application/javascript+module")
             + f"--{boundary}--\r\n".encode())

print(f"   PUT /accounts/.../workers/scripts/{name} "
      f"({len(worker)} bytes, compat {compat}{', +MOCK_KV binding' if binding else ''})")
if not dry:
    res = call("PUT", f"/workers/scripts/{name}", raw=multipart,
               ctype=f"multipart/form-data; boundary={boundary}")
    if not res.get("success", True):
        raise SystemExit(f"upload failed: {json.dumps(res.get('errors'))[:600]}")

# --- enable the workers.dev route and resolve the URL ------------------------------
url = ""
if not dry:
    try:
        call("POST", f"/workers/scripts/{name}/subdomain", {"enabled": True})
    except SystemExit as e:
        print(f"   note: could not enable the workers.dev subdomain: {e}")
    try:
        sub = (call("GET", "/workers/subdomain").get("result") or {}).get("subdomain")
        if sub:
            url = f"https://{name}.{sub}.workers.dev"
    except SystemExit as e:
        print(f"   note: could not read the account subdomain: {e}")

if url:
    print(f"   deployed: {url}")
    with open(os.path.join(outdir, "deployed.json"), "w") as f:
        json.dump({"url": url, "base_path": base_path,
                   "mock_url": (url + base_path) if base_path else url,
                   "worker_name": name,
                   "deployed_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
                   "path": "rest", "kv": bool(binding)}, f, indent=1)
        f.write("\n")
else:
    print("   deployed; could not resolve the workers.dev URL — pass it to "
          "--health-only --url once known")
print(url or "URL_UNKNOWN")
PY
}

deploy_wrangler() {
  # A deploy copy of wrangler.toml: the KV block survives only when a real id is known.
  local cfg="$DIR/deploy.wrangler.toml"
  python3 - "$DIR/wrangler.toml" "$cfg" "$WITH_KV" <<'PY'
import re, sys
src, dst, with_kv = sys.argv[1:4]
with_kv = with_kv == "1"
text = open(src).read() if __import__("os").path.exists(src) else "main = \"worker.js\"\n"
if "[[" in text:
    blocks = text.split("[[kv_namespaces]]")
    head, kv = blocks[0], ("[[kv_namespaces]]" + "".join(blocks[1:]))
    if with_kv and "REPLACE_WITH_KV_NAMESPACE_ID" in kv:
        # the deploy step fills the id (see --with-kv below); keep the block for now
        text = head + kv
    elif not with_kv:
        text = head.rstrip() + "\n"
open(dst, "w").write(text)
print(f"   config: {dst}")
PY
  if [ "$WITH_KV" -eq 1 ]; then
    echo "   creating/reusing KV namespace MOCK_KV ..."
    local kvout
    kvout="$(cd "$DIR" && CLOUDFLARE_API_TOKEN="$CF_API_TOKEN" CLOUDFLARE_ACCOUNT_ID="$CF_ACCOUNT_ID" \
             npx --yes wrangler@4 kv namespace create MOCK_KV 2>&1 || true)"
    local kvid
    kvid="$(printf '%s\n' "$kvout" | sed -n 's/.*id[[:space:]]*=[[:space:]]*"\([0-9a-f]\{32\}\)".*/\1/p' | head -1)"
    if [ -n "$kvid" ]; then
      python3 - "$cfg" "$kvid" <<'PY'
import sys
cfg, kvid = sys.argv[1:3]
text = open(cfg).read().replace("REPLACE_WITH_KV_NAMESPACE_ID", kvid)
open(cfg, "w").write(text)
print(f"   KV namespace id: {kvid}")
PY
    else
      echo "   warning: could not read the KV namespace id from wrangler output:" >&2
      printf '%s\n' "$kvout" | tail -5 >&2
    fi
  fi
  echo "   npx --yes wrangler@4 deploy (config deploy.wrangler.toml)"
  local raw
  raw="$(mktemp)"
  ( cd "$DIR" && CLOUDFLARE_API_TOKEN="$CF_API_TOKEN" CLOUDFLARE_ACCOUNT_ID="$CF_ACCOUNT_ID" \
      npx --yes wrangler@4 deploy --config deploy.wrangler.toml 2>&1 ) | tee "$raw" \
      | sed 's/[A-Za-z0-9_-]\{30,\}/[redacted]/g'
  DEPLOYED_URL="$(grep -oE 'https://[A-Za-z0-9.-]+\.workers\.dev' "$raw" | tail -1 || true)"
  rm -f "$raw"
}

if [ "$HEALTH_ONLY" -eq 0 ]; then
  echo "== deploy: worker '$NAME' from $DIR (path: $MODE) =="
  DEPLOYED_URL=""
  if [ "$MODE" = "wrangler" ]; then
    deploy_wrangler
  else
    DEPLOY_OUT="$(deploy_rest)"
    printf '%s\n' "$DEPLOY_OUT"
    if [ -z "$URL" ]; then
      URL="$(printf '%s\n' "$DEPLOY_OUT" | tail -1)"
      [ "$URL" = "URL_UNKNOWN" ] && URL=""
    fi
  fi
  if [ -z "$URL" ] && [ -n "$DEPLOYED_URL" ]; then
    URL="$DEPLOYED_URL"
  fi
  if [ -n "$URL" ]; then
    # The submission, build.py and the runbook want the URL *with* the contract base
    # path (https://<worker>.<subdomain>.workers.dev/v1); the health check wants the
    # bare host, because the probe paths from endpoints.json already carry the prefix.
    BASE_PATH="$(python3 - "$MANIFEST" <<'PY'
import json, sys
try:
    print((json.load(open(sys.argv[1])).get("base_path") or "").rstrip("/"))
except Exception:
    print("")
PY
)"
    # --url may hand in the URL with the base path already (--health-only accepts both
    # forms): never append it twice.
    MOCK_URL="$URL"
    if [ -n "$BASE_PATH" ]; then
      case "$URL" in
        *"$BASE_PATH") : ;;
        *) MOCK_URL="$URL$BASE_PATH" ;;
      esac
    fi
    echo "   deployed: $URL"
    if [ -n "$BASE_PATH" ]; then
      echo "   mock url: $MOCK_URL"
    fi
    python3 - "$DIR" "$NAME" "$URL" "$BASE_PATH" "$MOCK_URL" "$MODE" <<'PY'
import json, sys, time
outdir, name, url, base, mock_url, mode = sys.argv[1:7]
with open(outdir + "/deployed.json", "w") as f:
    json.dump({"url": url, "base_path": base, "mock_url": mock_url,
               "worker_name": name,
               "deployed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "path": mode}, f, indent=1)
    f.write("\n")
PY
  fi
fi

if [ "$HEALTH" -eq 1 ]; then
  if [ -z "$URL" ]; then
    die "no URL to health-check — pass --url https://<worker>.<subdomain>.workers.dev"
  fi
  health_check "$URL"
  echo "== deploy.sh done: $URL =="
else
  echo "== deploy.sh done (health check skipped) =="
fi
