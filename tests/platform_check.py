"""Platform health checks and stuck-simulation handling, per the organisers'
outage guidance. freya.py never retries 5xx, so this does.

    python3 tests/platform_check.py health              # basic API health (3 tries, 10 s apart)
    python3 tests/platform_check.py sims                # what is running in the workspace
    python3 tests/platform_check.py stuck [--max-min 15]  # simulations running longer than N minutes
    python3 tests/platform_check.py cancel <sim_id>     # cancel a stuck simulation (keeps the record)
    python3 tests/platform_check.py signature           # outage signature in the latest results:
                                                        # no tool calls + ~0 s agent turns = platform, not the agent
    python3 tests/platform_check.py full                # all of the above
"""
import json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import freya

def api_retry(method, path, tries=3, wait=10, **params):
    """The kit's freya.py never retries. This does, 10 s apart, on 5xx only."""
    last = None
    for i in range(tries):
        try:
            return freya.api(method, path, **params)
        except RuntimeError as e:
            last = e
            if " -> 5" not in str(e):
                raise
            if i < tries - 1:
                print(f"5xx on {method} {path}, retrying in {wait} s ({i + 1}/{tries})", flush=True)
                time.sleep(wait)
    raise last

def health():
    try:
        api_retry("GET", "/api/v2/workspaces")
        print("HEALTH: OK")
        return True
    except Exception as e:
        print(f"HEALTH: DOWN ({str(e)[:100]})")
        return False

def simulations():
    ws = freya.workspace_id()
    sims = api_retry("GET", "/api/v2/simulations", workspaceId=ws, limit=10)
    sims = sims.get("simulations") or sims.get("items") or []
    print(f"{len(sims)} recent simulations:")
    for s in sims:
        started = s.get("createdAt") or s.get("startedAt") or "?"
        print(f"  {s.get('status'):<10} {s.get('name'):<22} {started[:19]}  {s.get('id')}")
    return sims

def stuck(max_minutes=15):
    now = time.time()
    out = []
    for s in simulations():
        if s.get("status") != "running":
            continue
        started = s.get("createdAt") or s.get("startedAt")
        age = None
        if started:
            try:
                import datetime
                t = datetime.datetime.fromisoformat(started.replace("Z", "+00:00"))
                age = (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds()
            except Exception:
                pass
        age_min = (age / 60) if age is not None else None
        if age_min is not None and age_min > max_minutes:
            out.append(s)
            print(f"STUCK: {s.get('name')} running for {age_min:.0f} min -> id {s['id']}")
        elif age_min is not None:
            print(f"running ok: {s.get('name')} {age_min:.0f} min")
    if not out:
        print(f"no simulation running longer than {max_minutes} minutes")
    return out

def cancel(sim_id):
    try:
        r = api_retry("POST", f"/api/v2/simulations/{sim_id}/cancel")
        print("cancel:", r)
    except RuntimeError as e:
        if "404" in str(e) or "405" in str(e) or "not found" in str(e).lower():
            # older platform without the cancel route: fall back to delete
            r = freya.api("DELETE", f"/api/v2/simulations/{sim_id}")
            print("cancel route missing, deleted instead:", r)
        else:
            raise

def signature():
    """Outage signature: the latest runs show no tool calls and ~0 s agent turns.
    That means the platform, not the agent. Never 'fix' the workflow after such a run."""
    results = sorted((ROOT / "results").glob("*-b*.json")) + [ROOT / "results" / "brief-a.json"]
    for f in results:
        if not f.exists():
            continue
        data = json.loads(f.read_text())
        rows = data.get("rows", [])
        if not rows:
            continue
        empty = [r for r in rows if not r.get("tools") and r.get("slowest_turn_s", 0) == 0]
        if len(empty) == len(rows) and rows:
            print(f"OUTAGE SIGNATURE in {f.name}: all {len(rows)} calls have no tool calls and 0 s turns")
            return True
    print("no outage signature in the recent results")
    return False

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "full"
    if cmd == "health":
        raise SystemExit(0 if health() else 1)
    if cmd == "sims":
        simulations()
    elif cmd == "stuck":
        max_min = int(sys.argv[sys.argv.index("--max-min") + 1]) if "--max-min" in sys.argv else 15
        stuck(max_min)
    elif cmd == "cancel":
        cancel(sys.argv[2])
    elif cmd == "signature":
        signature()
    elif cmd == "full":
        ok = health()
        if ok:
            simulations()
            stuck()
        signature()
    else:
        raise SystemExit(__doc__)

if __name__ == "__main__":
    main()
