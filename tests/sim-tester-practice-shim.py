#!/usr/bin/env python3
"""sim-tester local practice-namespace shim (session opener + ledger + close records).

The deployed final-case mock serves the 7 contract services (and close_call) but has
no /v1/practice/* ledger; the dryrun worker has one but needs a JS runtime to run.
This shim serves ONLY the practice namespace local_sim needs; the 7 services stay on
the deployed mock so tool behavior (envelope, cross-call state) is the real thing.

Serves (paths as tools/score.py + tests/local_sim.py call them, FREYA_BANK_HOST base):
  POST /v1/practice/sessions          {"case": id} -> {"variables": {...}}
  POST /v1/practice/close_call        record {customerNumber, outcome, reason}
  POST /v1/practice/transfer_to_human record {queue, ...}
  GET  /v1/practice/ledger/<id>       ledger view (score_ledger-shaped)
  GET  /health

Names come from tests/final-mock-dryrun/seed.json (customerNo -> first/last name).
customerNumber is returned WITHOUT a -sN suffix so the deployed mock sees the real
seeded customer; customer_id keeps the suffix so sessions don't collide.
"""
import argparse, json, re, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = threading.Lock()
SESSION_COUNTS = {}
LEDGERS = {}  # base customerNo -> {"calls": [...], "transfers": [...], "outcome", "reason", "closed"}

NAMES = {}
try:
    seed = json.loads((ROOT / "tests" / "final-mock-dryrun" / "seed.json").read_text())
    for c in seed.get("customers", []):
        raw = c.get("raw") or {}
        if raw.get("customerNo"):
            NAMES[str(raw["customerNo"])] = (raw.get("firstName"), raw.get("lastName"))
except Exception:
    pass


def base_of(key):
    return re.sub(r"-s\d+$", "", str(key or ""))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet
        pass

    def _json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("content-length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_GET(self):
        if self.path == "/health":
            return self._json({"ok": True, "service": "sim-tester-practice-shim"})
        m = re.match(r"^/v1/practice/ledger/(.+)$", self.path)
        if m:
            base = base_of(m.group(1).split("?")[0])
            with LOCK:
                rec = LEDGERS.get(base) or {}
                calls = list(rec.get("calls") or [])
                transfers = list(rec.get("transfers") or [])
                out = {
                    "customer_id": m.group(1),
                    "case_id": rec.get("case_id"),
                    "outcome": rec.get("outcome"),
                    "reason": rec.get("reason"),
                    "promises": [],
                    "notes": [],
                    "callbacks": [],
                    "transfers": transfers,
                    "identity": {},
                    "closed": rec.get("closed", False),
                    "calls": calls,
                }
            return self._json(out)
        return self._json({"hata": "kayit bulunamadi"}, 404)

    def do_POST(self):
        body = self._body()
        if self.path == "/v1/practice/sessions":
            case = str(body.get("case") or "")
            with LOCK:
                n = SESSION_COUNTS.get(case, 0) + 1
                SESSION_COUNTS[case] = n
            cid = f"{case}-s{n}"
            fn, ln = NAMES.get(case, (None, None))
            return self._json({"variables": {
                "customer_id": cid,
                "customerNo": cid,
                "customerNumber": case,   # real seeded customer number, no suffix
                "case_id": case,
                "first_name": fn,
                "last_name": ln,
            }})
        if self.path == "/v1/practice/close_call":
            base = base_of(body.get("customerNumber") or body.get("customerNo") or "unknown")
            with LOCK:
                rec = LEDGERS.setdefault(base, {"calls": [], "transfers": []})
                rec["case_id"] = base
                rec["outcome"] = body.get("outcome")
                rec["reason"] = body.get("reason")
                rec["closed"] = True
                rec["calls"].append({"seq": len(rec["calls"]) + 1, "tool": "close_call",
                                     "request": body, "result": {"ok": True}})
            return self._json({"ok": True})
        if self.path == "/v1/practice/transfer_to_human":
            base = base_of(body.get("customerNumber") or body.get("customerNo") or "unknown")
            with LOCK:
                rec = LEDGERS.setdefault(base, {"calls": [], "transfers": []})
                rec["transfers"].append({"queue": body.get("queue") or "unknown", "request": body})
            return self._json({"ok": True})
        return self._json({"hata": "kayit bulunamadi"}, 404)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"sim-tester practice shim on 127.0.0.1:{a.port} (names for {len(NAMES)} customers)")
    srv.serve_forever()
