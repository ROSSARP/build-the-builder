#!/usr/bin/env python3
"""sim-tester: build the local_sim inputs from tests/example_checks.json (the six
official examples) — mechanical conversion, no case data retyped by hand.

Outputs:
  tests/sim-tester-cases-p1.json   six cases in tests/local_sim.py --cases shape
  tests/sim-tester-wf-p1.json      byte-copy of submission/finalcase.workflow.json with
                                   only close_call + transfer_to_human URLs redirected to
                                   the local practice shim (tools stay on the deployed mock)

Ledger note: this contract has no promise/callback services, so expected promises/
notes/callbacks/transfers are empty and the outcome vocabulary is the scorer's fixed
collection table (no "informational success" outcome exists); expected outcome is
no_promise/refused for all six — the meaningful ledger checks are: call closed with
close_call, no identity gating violations, no unexpected transfer/promise records.
"""
import hashlib, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEPLOYED = "https://final-case-mock-bank.fcodefcode3.workers.dev"
SHIM = "http://127.0.0.1:8787"
REWRITE = {
    f"{DEPLOYED}/voice/v1/close_call": f"{SHIM}/v1/practice/close_call",
    f"{DEPLOYED}/voice/v1/transfer_to_human": f"{SHIM}/v1/practice/transfer_to_human",
}

ex_obj = json.loads((ROOT / "tests" / "example_checks.json").read_text())
seed = json.loads((ROOT / "tests" / "final-mock-dryrun" / "seed.json").read_text())
names = {}
for c in seed.get("customers", []):
    raw = c.get("raw") or {}
    if raw.get("customerNo"):
        names[str(raw["customerNo"])] = (raw.get("firstName"), raw.get("lastName"))

LEVEL = {"ordinary": "easy", "edge": "medium", "adversarial": "hard"}

cases = []
for ex in ex_obj["examples"]:
    cv = ex.get("call_variables") or {}
    no = str(cv.get("customerNumber") or "")
    fn, ln = names.get(no, ("Müşteri", "Test"))
    behaviours = [str(b) for b in (ex.get("expected_agent_behaviour") or [])]
    outcome_txt = str(ex.get("expected_outcome") or "")
    lines = [str(x) for x in (ex.get("customer_lines") or [])]
    script = (
        f"You are calling your bank's phone line (the assistant speaks Turkish, you speak Turkish). "
        f"Your goal in this call: {ex.get('title')}. "
        + ("In this call you: " + "; ".join(lines) + "." if lines else "")
    )
    cases.append({
        "id": no,
        "brief": f"sim-tester conversion of {ex['id']} ({ex.get('kind')}) from tests/example_checks.json",
        "family": str(ex.get("kind") or "ordinary").capitalize(),
        "level": LEVEL.get(str(ex.get("kind")), "medium"),
        "title": ex.get("title") or ex["id"],
        "variables": {"first_name": fn, "last_name": ln, "customerNumber": no},
        "identity": {},
        "products": [],
        "script": script,
        "expected": {"outcome": "no_promise", "reason": "refused",
                     "promises": [], "notes": [], "callbacks": [], "transfers": []},
        "checks": behaviours + ([outcome_txt] if outcome_txt else []),
    })

(ROOT / "tests" / "sim-tester-cases-p1.json").write_text(
    json.dumps(cases, ensure_ascii=False, indent=1))

src = (ROOT / "submission" / "finalcase.workflow.json").read_bytes()
src_md5 = hashlib.md5(src).hexdigest()
text = src.decode("utf-8")
hits = {k: text.count(k) for k in REWRITE}
for old, new in REWRITE.items():
    text = text.replace(old, new)
(ROOT / "tests" / "sim-tester-wf-p1.json").write_text(text)

print("source submission md5:", src_md5)
print("cases:", [(c["id"], c["title"][:40]) for c in cases])
print("url rewrite hits (expect 1 each):", hits)
