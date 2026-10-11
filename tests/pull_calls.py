"""Pull every call transcript from every simulation in the workspace into
results/calls/<call_id>.json, so audit agents can read them offline.

    python3 tests/pull_calls.py [--limit N]
"""
import json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import freya

def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    out_dir = ROOT / "results" / "calls"
    out_dir.mkdir(parents=True, exist_ok=True)
    ws = freya.workspace_id()
    sims = freya.api("GET", "/api/v2/simulations", workspaceId=ws)
    sims = sims.get("simulations") or sims.get("items") or []
    index = []
    for s in sims:
        sid = s.get("id")
        if not sid:
            continue
        try:
            its = freya.api("GET", f"/api/v2/simulations/{sid}/iterations", workspaceId=ws)
            its = its.get("iterations") or its.get("items") or []
        except Exception:
            continue
        for it in its:
            try:
                runs = freya.api("GET", f"/api/v2/simulations/{sid}/iterations/{it['id']}", workspaceId=ws, limit=100)
                runs = runs.get("runs") or []
            except Exception:
                continue
            for r in runs:
                if not r.get("callId"):
                    continue
                index.append({"call_id": r["callId"], "simulation": s.get("name"), "sim_id": sid,
                              "persona": r.get("personaName"), "outcome": r.get("outcome")})
                if limit and len(index) >= limit:
                    break
            if limit and len(index) >= limit:
                break
        if limit and len(index) >= limit:
            break
    # dedupe by call id
    seen, calls = set(), []
    for e in index:
        if e["call_id"] in seen:
            continue
        seen.add(e["call_id"])
        calls.append(e)
    fetched = 0
    for e in calls:
        dest = out_dir / f"{e['call_id']}.json"
        if dest.exists():
            fetched += 1
            continue
        try:
            call = freya.get_call(e["call_id"])
        except Exception as ex:
            e["fetch_error"] = str(ex)[:120]
            continue
        dest.write_text(json.dumps({**e, "call": call}, indent=1))
        fetched += 1
        time.sleep(0.2)
    (out_dir / "index.json").write_text(json.dumps(calls, indent=1))
    print(f"index: {len(calls)} calls, fetched: {fetched}")

if __name__ == "__main__":
    main()
