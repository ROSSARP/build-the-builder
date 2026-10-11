"""Salvage results from a simulation whose runs finished but whose analysis
wedged: fetch each run's call, extract the customer_id, read the bank ledger and
score it with the platform's own score_ledger.

    python3 tests/salvage.py <sim_id> <case_file> [--out results/salvaged-<sim>.json]
"""
import json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import freya
from score import http, score_ledger
try:
    from platform_check import api_retry as _retry
except ImportError:
    _retry = lambda method, path, **params: freya.api(method, path, **params)

def main():
    sim_id = sys.argv[1]
    case_file = sys.argv[2]
    out_path = None
    if "--out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--out") + 1]
    cases = {c["case_id"]: c for c in json.loads(pathlib.Path(case_file).read_text())}
    cases.update({c["id"]: c for c in cases.values()})
    import os
    freya._ws = os.environ.get("FREYA_WORKSPACE_ID")  # skip the flaky workspaces call
    ws = freya.workspace_id()
    its = _retry("GET", f"/api/v2/simulations/{sim_id}/iterations", workspaceId=ws)
    its = its.get("iterations") or its.get("items") or []
    rows = []
    for it in its:
        runs = _retry("GET", f"/api/v2/simulations/{sim_id}/iterations/{it['id']}", workspaceId=ws, limit=100)
        runs = runs.get("runs") or []
        for r in runs:
            name = r.get("personaName") or ""
            cid = name.split(" ")[0]
            suffix = name.split(" — ", 1)[1] if " — " in name else None
            case = cases.get(f"{cid}-{suffix}") if suffix else None
            if not case:
                case = cases.get(cid)
            if not case:
                print(f"skip {name}: no case match")
                continue
            call_id = r.get("callId")
            customer_id = None
            tools = []
            if call_id:
                try:
                    call = freya.get_call(call_id)
                    for m in call.get("messages", []):
                        if m.get("role") != "system":
                            continue
                        try:
                            ev = json.loads(m["message"])
                        except Exception:
                            continue
                        if ev.get("event") == "function_call_start" and ev.get("function") != "code_exec":
                            tools.append(ev.get("function"))
                        if ev.get("event") == "node_enter" and not customer_id:
                            vt = ev.get("variable_table") or {}
                            v = vt.get("customer_id")
                            if isinstance(v, dict):
                                v = v.get("value")
                            if v:
                                customer_id = v
                except Exception as e:
                    print(f"{cid}: transcript fetch failed: {str(e)[:80]}")
            if not customer_id:
                print(f"{cid}: no customer_id found, skip")
                continue
            led = http("/v1/practice/ledger/" + customer_id)
            sc = score_ledger(case, led)
            plat = r.get("outcome")
            failed = list(sc.get("failed", []))
            if plat and plat != "pass":
                failed.append(f"platform: {plat} {str(r.get('reason') or '')[:120]}")
            row = {"id": cid, "case_id": case.get("case_id", cid), "title": case.get("title", name),
                   "pass": not failed, "failed": failed, "tools": tools,
                   "call_id": call_id, "customer_id": customer_id, "platform_outcome": plat}
            rows.append(row)
            print(("PASS" if row["pass"] else "FAIL"), cid, "|", " > ".join(t.replace("verify_identity", "verify").replace("create_promise", "promise") for t in tools))
            for f in failed:
                print("       -", f[:200])
            time.sleep(0.2)
    passed = sum(1 for r in rows if r["pass"])
    print(f"\n== salvaged: {passed} / {len(rows)} passed (ledger scoring) ==")
    if out_path:
        pathlib.Path(out_path).write_text(json.dumps({"simulation_id": sim_id, "passed": passed,
                                                      "total": len(rows), "rows": rows}, indent=1))
        print("wrote", out_path)

if __name__ == "__main__":
    main()
