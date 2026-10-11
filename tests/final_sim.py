"""Run final-case scenarios against the published agent in a REAL simulation
(platform engine, same path the organisers use — the chat route skips
pre_actions, simulations do not). One scenario at a time.

    python3 tests/final_sim.py --list
    python3 tests/final_sim.py s1_ada_debt s5_no_card            # selected scenarios
    python3 tests/final_sim.py --all                              # every scenario
    python3 tests/final_sim.py --all --max-sec 300

For each scenario: create the persona (cached), start a chat-mode simulation
with customerVariablesMap {customerNumber, now}, wait, fetch the transcript,
read the mock's KV-merged __log for that customer, and print PASS/FAIL per
check (phrase in transcript) and per expected tool (in the mock log).
"""
import argparse, hashlib, json, os, pathlib, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import freya  # noqa: E402

SCENARIOS = ROOT / "tests" / "final-scenarios.json"
STORE = ROOT / ".personas-final.json"
MOCK_URL = "https://final-case-mock-bank.fcodefcode3.workers.dev/voice/v1"
NOW = "2026-10-12T10:30:00+03:00"


def mock_host():
    """The mock's bare host, from the file the deploy pipeline writes."""
    p = ROOT / "out" / "final-mock-host.txt"
    if p.is_file():
        v = p.read_text().strip()
        if v.startswith("http"):
            return v.rstrip("/")
    return MOCK_URL.replace("/voice/v1", "")


def mock_log_url():
    return mock_host() + "/__log"

PERSONA = """OUTPUT RULE: Write only the words you say on the phone. No stage directions, no brackets. One or two short sentences per turn, then wait for the other side. SPEAK ONLY TURKISH: every sentence you say must be in Turkish.

WHO YOU ARE: You are {who}. You are a customer of Freya Bank.

WHAT HAPPENS IN THIS CALL: {script}

RULES:
- Answer what you are asked. Do not volunteer information nobody asked for.
- Do not invent dates, amounts or facts that are not written above. If asked something that is not covered, give a short neutral answer.
- If the caller reads something back and it matches what you agreed, say "Evet, onaylıyorum." or "Yes, I confirm."
- When the caller says goodbye, say "Teşekkürler, iyi günler." and say nothing more."""


def load():
    return json.loads(SCENARIOS.read_text(encoding="utf-8"))["scenarios"]


def persona_ids(scenarios):
    store = json.loads(STORE.read_text()) if STORE.exists() else {}
    specs, key = {}, {}
    for s in scenarios:
        text = PERSONA.format(who=s["who"], script=s["script"])
        p = {"name": f"{s['id']} {s['title']}", "prompt": text,
             "successCriteria": "The customer gets what the script says they want.",
             "tags": ["hackathon", "final-case"]}
        specs[s["id"]] = p
        key[s["id"]] = s["id"] + ":" + hashlib.sha1(json.dumps(p, sort_keys=True).encode()).hexdigest()[:10]
    new = [s for s in scenarios if key[s["id"]] not in store]
    if new:
        made = freya.create_personas([specs[s["id"]] for s in new])["personas"]
        for s, m in zip(new, made):
            store[key[s["id"]]] = m["id"]
        STORE.write_text(json.dumps(store, indent=1))
    return {s["id"]: store[key[s["id"]]] for s in scenarios}


def transcript_text(call):
    """Agent-side transcript: prefer the call's own transcript field, else join
    assistant messages (the message text field is 'message')."""
    tr = call.get("transcript")
    if isinstance(tr, str) and tr.strip():
        return tr
    out = []
    for m in call.get("messages") or []:
        if str(m.get("role") or "").lower() in ("assistant", "agent"):
            text = m.get("message") or m.get("text") or ""
            if isinstance(text, list):
                text = " ".join(str(t.get("text", "")) for t in text if isinstance(t, dict))
            if text:
                out.append(str(text))
    return " ".join(out)


def mock_calls(customer_number, since=None):
    req = urllib.request.Request(mock_log_url(), headers={"user-agent": "final-sim/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        return [], f"mock log unreadable ({mock_log_url()}): {e}"
    hits = []
    for c in data.get("calls") or []:
        at = c.get("at") or ""
        if since and at < since:
            continue
        req_json = json.dumps(c.get("request") or {}, ensure_ascii=False)
        # cardNumber-keyed services carry no customer number: match within the
        # sim's time window by path instead
        if customer_number in req_json or (c.get("path") or "").split("/")[-1] in (
                "cards.balance", "statement.week.get", "statement.week.decide", "statement.week.change"):
            hits.append({"path": c.get("path"), "status": c.get("status"), "at": at})
    return hits, ""


def run_one(s, agent_id, max_seconds, quiet):
    t0 = time.time()
    pid = persona_ids([s])[s["id"]]
    variables = {pid: {"customerNumber": s["customerNumber"], "now": NOW}}
    sim_id, it_id, status = freya.run_simulation(
        agent_id, s["id"], variables, max_seconds=max_seconds, concurrency=1)
    it = freya.get_iteration(sim_id, it_id)
    runs = it.get("runs") or []
    if not runs:
        print(f"  {s['id']}: no runs in the iteration (status {status})")
        return
    call_id = runs[0].get("call_id") or runs[0].get("callId") or runs[0].get("id")
    call = freya.get_call(call_id).get("call") or freya.get_call(call_id)
    text = transcript_text(call)
    calls, log_err = mock_calls(s["customerNumber"], since=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0 - 3)))
    tools_hit = [t for t in s["tools"] if any(t in (c["path"] or "") for c in calls)]
    tools_miss = [t for t in s["tools"] if t not in tools_hit]
    checks_hit = [c for c in s["checks"] if c.lower() in text.lower()]
    checks_miss = [c for c in s["checks"] if c.lower() not in text.lower()]
    ok = not checks_miss and not tools_miss
    print(f"  {s['id']} [{s['title']}]: {'PASS' if ok else 'FAIL'} in {time.time() - t0:.0f}s "
          f"(status {status})")
    print(f"     transcript checks: {len(checks_hit)}/{len(s['checks'])}"
          + (f"  MISSING: {checks_miss}" if checks_miss else ""))
    print(f"     mock tools: {len(tools_hit)}/{len(s['tools'])}"
          + (f"  MISSING: {tools_miss}" if tools_miss else ""))
    if log_err:
        print(f"     {log_err}")
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    with open(out / f"final-sim-{s['id']}.json", "w") as f:
        json.dump({"scenario": s, "status": status, "sim_id": sim_id, "iteration_id": it_id,
                   "transcript_agent_text": text, "mock_calls": calls,
                   "checks_hit": checks_hit, "checks_miss": checks_miss,
                   "tools_hit": tools_hit, "tools_miss": tools_miss,
                   "passed": ok, "seconds": round(time.time() - t0)}, f,
                  ensure_ascii=False, indent=1)
    if not quiet and not ok:
        print(f"     agent text tail: ...{text[-500:]}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--agent", default=os.environ.get("FREYA_AGENT_ID", ""))
    ap.add_argument("--max-sec", type=int, default=420)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    scenarios = load()
    if a.list:
        for s in scenarios:
            print(f"{s['id']:16} {s['title']}")
        return
    if not a.agent:
        raise SystemExit("pass --agent <agent_id> (the published agent to test)")
    picked = scenarios if a.all else [s for s in scenarios if s["id"] in a.ids]
    if not picked:
        raise SystemExit("no scenarios selected (use ids, --all, or --list)")
    print(f"== final-case simulation runs against agent {a.agent} ==")
    results = []
    for s in picked:
        try:
            results.append(run_one(s, a.agent, a.max_sec, a.quiet))
        except Exception as e:
            print(f"  {s['id']}: ERROR {type(e).__name__}: {e}")
            results.append(False)
    print(f"== {sum(1 for r in results if r)}/{len(results)} scenarios passed ==")


if __name__ == "__main__":
    main()
