#!/usr/bin/env python3
"""Run ONE exam case against a published agent in VOICE simulation mode (audio).

Mirrors the organisers' flow (tools/run_cases.py + freya.run_simulation) with two changes:

  * "mode": "voice" - the platform default per the Freya docs (POST /api/v2/simulations
    accepts "voice" | "chat"). Voice mode needs no phone number: the persona's text is
    spoken by TTS, the agent answers with its own TTS, and the transcript comes from STT.
  * the persona prompt (persona_for-style, copied from tools/run_cases.py) carries an
    explicit SPEAK ONLY TURKISH instruction inside the script text, so the customer
    actually speaks Turkish even when the agent answers in English.

Everything else is the reference flow: persona via POST /api/v2/personas, a bank practice
session via score.http POST /v1/practice/sessions {"case": "<ID>"}, then POST
/api/v2/simulations with the same LLM overrides freya.py uses.

    python3 tests/run_voice_case.py                              # PUB-01 against the brief-a agent
    python3 tests/run_voice_case.py --case-file tests/turkish-pub01.json --case PUB-01
    python3 tests/run_voice_case.py --mode chat                  # same case, text mode (comparison)
    python3 tests/run_voice_case.py --agent <id> --out results/x.json

Needs FREYA_API_KEY and FREYA_BANK_TEAM_KEY. Set FREYA_WORKSPACE_ID to skip the flaky
workspaces call. Writes results/voice-<case>.json with the simulation status, the run's
judge verdict, the ledger score (tools/score.py) and the full transcript from the call.
"""
import argparse, hashlib, json, os, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import freya                                    # noqa: E402
from score import http as bank_http, score_ledger  # noqa: E402

DEFAULT_AGENT = "8580c81d-938f-4854-9600-6901f5a1f4d6"   # brief-a 1010-224203 (English prompts)
PERSONA_STORE = ROOT / ".personas-voice.json"
TURKISH_ONLY = "SPEAK ONLY TURKISH. Every sentence you say must be in Turkish."

# The organisers' persona template (tools/run_cases.py), unchanged.
PERSONA = """OUTPUT RULE: Write only the words you say on the phone. No stage directions, no brackets. One or two short sentences per turn, then wait for the other side.

WHO YOU ARE: {who}

WHAT HAPPENS IN THIS CALL: {script}

RULES:
- Answer what you are asked. Do not volunteer information nobody asked for.
- When you give a number or a date, say all of it in one turn. Never stop halfway through.
- Do not invent dates, amounts or facts that are not written above. If asked something that is not covered, give a short neutral answer.
- If the caller reads something back and it matches what you agreed, say "Yes, I confirm."
- When the caller says goodbye, say "Thank you, goodbye." and say nothing more."""


def persona_for(case, turkish=True):
    """tools/run_cases.py persona_for, with SPEAK ONLY TURKISH prepended to the script."""
    v, i = case["variables"], case["identity"]
    me = f"{v['first_name']} {v['last_name']}"
    if case["family"] == "Third party" or case.get("third_party"):
        who = f"You are NOT {me}. You answered this phone. You do not know {me}'s security answers and you would not give them. The text below says who you are."
    else:
        say = {"date_of_birth": "Your date of birth is {} (say it in words, like '14 March 1988').",
               "phone_last4": "The last four digits of your phone number on file are {}.",
               "postcode": "The postcode of your registered address is {}.",
               "birth_year": "Your year of birth is {}.",
               "company_number": "Your company number is {}.",
               "founded_year": "The company was founded in {}."}
        who = f"You are {me}. " + " ".join(
            say.get(k, "Your " + k.replace("_", " ") + " is {}.").format(x) for k, x in i.items()
        ) + " Give these only when asked, and give the wrong ones where the text below says so."
    script = case["script"]
    if turkish:
        script = TURKISH_ONLY + "\n\n" + script
    text = PERSONA.format(who=who, script=script)
    return {"name": case["id"] + " " + case["title"] + " [voice-tr]",
            "prompt": text,
            "successCriteria": "All of these are true:\n- " + "\n- ".join(case["checks"]),
            "tags": ["hackathon", "brief-" + case["brief"], "turkish", "voice"]}


def ensure_persona(spec, store=PERSONA_STORE):
    """Reuse the persona while its text is unchanged, create it once when it changes."""
    ids = json.loads(store.read_text()) if store.exists() else {}
    key = hashlib.sha1(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:12]
    if key in ids:
        return ids[key], False
    made = freya.create_personas([spec])["personas"][0]
    ids[key] = made["id"]
    store.write_text(json.dumps(ids, indent=1))
    return made["id"], True


def api_retry(method, path, body=None, tries=3, wait=10, **params):
    """freya.api with 5xx retries, 10 s apart (the kit's client never retries)."""
    last = None
    for attempt in range(tries):
        try:
            return freya.api(method, path, body, **params)
        except RuntimeError as e:
            last = e
            if " -> 5" not in str(e):
                raise
            if attempt + 1 < tries:
                print(f"5xx on {method} {path}, retrying in {wait} s ({attempt + 1}/{tries})", flush=True)
                time.sleep(wait)
    raise last


def start_simulation(agent_id, name, persona_id, variables, max_seconds, mode, concurrency=1):
    body = {"agentId": agent_id, "name": name, "mode": mode,
            "selectedPersonaIds": [persona_id], "customerVariablesMap": {persona_id: variables},
            "maxConcurrentCalls": concurrency, "runsPerPersona": 1,
            "maxCallDurationSeconds": max_seconds,
            "assistantLlmOverride": freya.AGENT_LLM, "routingLlmOverride": freya.AGENT_LLM,
            "extractionLlmOverride": freya.AGENT_LLM,
            "personaLlmOverride": freya.SIM_LLM, "analysisLlmOverride": freya.SIM_LLM}
    while True:
        try:
            sim = api_retry("POST", "/api/v2/simulations", body)
            break
        except RuntimeError as e:
            if "concurrent simulations" not in str(e):
                raise
            print("another simulation is running in this workspace, waiting 30 s", flush=True)
            time.sleep(30)
    return sim.get("simulation") or sim


def poll_simulation(sim_id, timeout_s=1800):
    """GET the simulation every 10 s until completed/failed/paused (5xx retried inside)."""
    t0 = time.time()
    while True:
        time.sleep(10)
        try:
            s = api_retry("GET", f"/api/v2/simulations/{sim_id}")
        except RuntimeError as e:
            print("poll failed:", str(e)[:200], flush=True)
            if time.time() - t0 > timeout_s:
                raise
            continue
        s = s.get("simulation") or s
        status = s.get("status")
        print(f"  [{time.time() - t0:5.0f} s] {status}", flush=True)
        if status in ("completed", "failed", "paused"):
            return s, time.time() - t0
        if time.time() - t0 > timeout_s:
            raise RuntimeError(f"simulation still {status} after {timeout_s} s")


def run(agent_id, case_file, case_id, mode, max_seconds, poll_timeout, turkish, out_path):
    cases = json.loads(pathlib.Path(case_file).read_text())
    case = next((c for c in cases if c["id"] == case_id), None)
    if case is None:
        raise SystemExit(f"no case {case_id} in {case_file} (have: {', '.join(c['id'] for c in cases)})")

    spec = persona_for(case, turkish=turkish)
    persona_id, created = ensure_persona(spec)
    print(f"persona {persona_id} ({'created' if created else 'reused'}) for case {case_id}")

    session = bank_http("/v1/practice/sessions", {"case": case_id})
    variables = session["variables"]
    customer_id = variables["customer_id"]
    print(f"bank session: customer_id={customer_id} now={variables.get('now')}")

    name = f"voice {case_id} {time.strftime('%H:%M:%S')}" if mode == "voice" else f"chat {case_id} {time.strftime('%H:%M:%S')}"
    print(f"starting {mode} simulation '{name}' against agent {agent_id}")
    sim = start_simulation(agent_id, name, persona_id, variables, max_seconds, mode)
    sim_id = sim["id"]
    print(f"simulation id {sim_id}; polling every 10 s")
    sim_final, wall_s = poll_simulation(sim_id, poll_timeout)

    its = api_retry("GET", f"/api/v2/simulations/{sim_id}/iterations")
    its = its.get("iterations") or its.get("items") or its
    it_id = its[0]["id"]
    it = freya.get_iteration(sim_id, it_id)
    runs = it.get("runs") or []
    run_row = next((r for r in runs if r.get("personaId") == persona_id), runs[0] if runs else {})
    print(f"iteration {it_id}: {len(runs)} run(s); judge outcome={run_row.get('outcome')!r} "
          f"reason={str(run_row.get('reason'))[:200]!r}")

    call, messages = {}, []
    if run_row.get("callId"):
        call = freya.get_call(run_row["callId"])
        for m in call.get("messages") or []:
            if m.get("role") in ("user", "assistant") and isinstance(m.get("message"), str):
                messages.append({"role": m["role"], "text": m["message"],
                                 "secondsFromStart": m.get("secondsFromStart")})

    ledger = bank_http("/v1/practice/ledger/" + customer_id)
    verdict = score_ledger(case, ledger)
    print(f"LEDGER {'PASS' if verdict['pass'] else 'FAIL'}  {case_id}  "
          f"outcome={ledger.get('outcome')!r} reason={ledger.get('reason')!r}")
    for bad in verdict["failed"]:
        print("  -", bad[:300])
    print("tools:", " > ".join(c["tool"] for c in ledger.get("calls") or []) or "(none)")

    print("\n--- transcript (STT) ---")
    for m in messages:
        who = "agent  " if m["role"] == "assistant" else "customer"
        t = m.get("secondsFromStart")
        print(f"[{who} {'-' if t is None else f'{t:5.1f}s'}] {m['text']}")

    result = {
        "agent_id": agent_id, "case": case_id, "mode": mode, "persona_id": persona_id,
        "persona_created": created, "simulation_id": sim_id, "simulation_name": name,
        "status": sim_final.get("status"), "wall_seconds": round(wall_s, 1),
        "simulation": sim_final, "iteration_id": it_id, "run": run_row,
        "customer_id": customer_id, "ledger": ledger, "ledger_verdict": verdict,
        "call": {"id": run_row.get("callId"), "endedReason": call.get("endedReason"),
                 "duration": call.get("duration"), "transcript_raw": call.get("transcript")},
        "messages": messages,
    }
    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(out_path).write_text(json.dumps(result, indent=1, ensure_ascii=False))
    print(f"\nwritten to {out_path}")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", default=DEFAULT_AGENT)
    ap.add_argument("--case-file", default=str(ROOT / "tests" / "turkish-pub01.json"))
    ap.add_argument("--case", default="PUB-01")
    ap.add_argument("--mode", default="voice", choices=("voice", "chat"))
    ap.add_argument("--max-seconds", type=int, default=420, dest="max_seconds")
    ap.add_argument("--poll-timeout", type=int, default=1800, dest="poll_timeout")
    ap.add_argument("--no-turkish-instruction", action="store_false", dest="turkish",
                    help="leave the persona script exactly as the case file has it")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = a.out or str(ROOT / "results" / f"voice-{a.case}.json")
    run(a.agent, a.case_file, a.case, a.mode, a.max_seconds, a.poll_timeout, a.turkish, out)


if __name__ == "__main__":
    main()
