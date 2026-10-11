"""Build the FINAL mock Worker deterministically from the service contract's
test customers. No LLM involved: the mock is a lookup table, exactly as the
pack requires — same paths, same fields, same response bodies, same HTTP
statuses as test-customers.json. Synthesised errors follow the contract's
section-4 shape (result envelope, returnCode == code, type ERROR/WARNING).

Usage:
    python3 builder/mock_final.py [contract_json] [customers_json] [--out mock/final] [--name final-case-mock-bank]

Outputs: {out}/worker.js  ({out}/endpoints.json for deploy.sh probes)
"""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def norm(v):
    """customerNo / week may arrive as number or string; treat them the same."""
    if isinstance(v, bool):
        return ""
    if isinstance(v, (int, float)):
        return str(int(v)) if float(v).is_integer() else str(v)
    return str(v).strip() if v is not None else ""


def build_tables(customers):
    """Flatten the 34 customers into per-service lookup tables."""
    tables = {
        "LIST": {},       # customerNo -> {http, response}
        "BALANCE": {},    # cardNumber -> {http, response, delay?}
        "WEEKGET": {},    # cardNumber -> {http, response}
        "DECIDE": {},     # cardNumber -> {week -> {http, response}}
        "CHANGE": {},     # cardNumber -> {week -> {http, response}}
        "EMAIL": {},      # customerNo -> {http, response}
        "PDF": {},        # customerNo -> {http, response}
    }
    n = 0
    for c in customers.get("customers") or []:
        cno = norm(c.get("customerNo"))
        if not cno:
            continue
        svcs = c.get("services") or {}
        if isinstance(svcs.get("cards.list"), dict):
            tables["LIST"][cno] = svcs["cards.list"]
        if isinstance(svcs.get("contact.email.get"), dict):
            tables["EMAIL"][cno] = svcs["contact.email.get"]
        if isinstance(svcs.get("statement.pdf.send"), dict):
            tables["PDF"][cno] = svcs["statement.pdf.send"]
        for table, name in (("BALANCE", "cards.balance"), ("WEEKGET", "statement.week.get")):
            entries = svcs.get(name)
            if isinstance(entries, dict):
                for card, entry in entries.items():
                    if isinstance(entry, dict):
                        tables[table][card] = entry
        for table, name in (("DECIDE", "statement.week.decide"), ("CHANGE", "statement.week.change")):
            entries = svcs.get(name)
            if isinstance(entries, dict):
                for card, weeks in entries.items():
                    if isinstance(weeks, dict):
                        slot = tables[table].setdefault(card, {})
                        for week, entry in weeks.items():
                            if isinstance(entry, dict):
                                slot[norm(week)] = entry
        n += 1
    return tables, n


def js_literal(obj):
    """JSON as a JS object literal (no JSON.parse at runtime)."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def emit_worker(tables, n_customers):
    data = {}
    data["LIST"] = tables["LIST"]
    data["BALANCE"] = tables["BALANCE"]
    data["WEEKGET"] = tables["WEEKGET"]
    data["DECIDE"] = tables["DECIDE"]
    data["CHANGE"] = tables["CHANGE"]
    data["EMAIL"] = tables["EMAIL"]
    data["PDF"] = tables["PDF"]
    d = js_literal(data)
    return WORKER_JS.replace("__DATA__", d).replace("__N_CUSTOMERS__", str(n_customers))


WORKER_JS = r"""// freya statement-debt mock — deterministic lookup table built by builder/mock_final.py
// from finalcase/test-environment/test-customers.json. Every response body and
// HTTP status below is served EXACTLY as the test data gives it; nothing is
// invented. Synthesised errors follow the contract section 4 (result envelope).
const DATA = __DATA__;
const N_CUSTOMERS = __N_CUSTOMERS__;

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "*",
};

function json(body, status = 200) {
  return Response.json(body, { status: status, headers: CORS });
}

async function readBody(request) {
  try { return await request.json(); } catch (e) { return null; }
}

// The panel's "Test API Request" button sends variables unfilled, e.g. "{{customerNumber}}".
function isTemplateVariable(value) {
  return typeof value === "string" && (value.startsWith("{{") || value.startsWith("%7B%7B"));
}

function firstKey(obj) {
  for (const k in obj) return k;
  return null;
}

// --- error synthesis (contract section 4: returnCode == code, type ERROR/WARNING) ---
let SEQ = 0;
function guid() {
  SEQ += 1;
  return "mock" + String(SEQ).padStart(12, "0");
}
function errInvalid(field, status = 400) {
  const g = guid();
  const msg = field + " cannot be empty";
  return json({
    result: {
      guid: g, returnCode: "INVALID_ARGUMENTS_ERROR", messageText: msg,
      code: "INVALID_ARGUMENTS_ERROR", message: msg, type: "ERROR",
      details: { guid: g, rootCause: "BadRequestException", errorOrigin: "gateway" },
    },
  }, status);
}
function errChannel(code, messageText, rootCause, status = 404) {
  const g = guid();
  return json({
    result: {
      guid: g, returnCode: code, messageText: messageText,
      code: code, message: messageText, type: "WARNING",
      details: { guid: g, rootCause: rootCause, errorOrigin: "gateway" },
    },
  }, status);
}
function errTech(status = 500) {
  const g = guid();
  const msg = "Teknik hata: ABORTED: ";
  return json({
    result: {
      guid: g, returnCode: "FBE00099", messageText: msg,
      code: "FBE00099", message: msg, type: "ERROR",
      details: { guid: g, rootCause: "TechnicalException", errorOrigin: "gateway" },
    },
  }, status);
}

function serve(entry) {
  // entry: {http, response, delaySeconds?} — the test data's own answer, verbatim.
  const delay = entry && typeof entry.delaySeconds === "number" ? entry.delaySeconds : 0;
  const answer = () => json(entry.response, entry.http || 200);
  if (delay > 0) return new Promise((resolve) => setTimeout(() => resolve(answer()), delay * 1000));
  return answer();
}

function tableEntry(table, key, fallbackTemplate) {
  // Direct hit wins; an unfilled template variable gets the first entry (valid
  // record, like the pack's own example worker does for the panel).
  const k = key == null ? "" : String(key).trim();
  if (Object.prototype.hasOwnProperty.call(table, k)) return table[k];
  if (isTemplateVariable(k) && fallbackTemplate) {
    const fk = firstKey(table);
    if (fk != null) return table[fk];
  }
  return null;
}

// --- call log (best effort, in-memory; for our own smoke tests and the review) ---
const CALL_LOG = [];
let ENV = null;   // set by fetch; lets logCall mirror to KV across isolates
let CTX = null;

function logCall(path, request, status) {
  const entry = { at: new Date().toISOString(), path, request, status };
  CALL_LOG.push(entry);
  if (CALL_LOG.length > 5000) CALL_LOG.splice(0, CALL_LOG.length - 5000);
  if (ENV && ENV.MOCK_KV && CTX) {
    try {
      const key = "call:" + Date.now() + ":" + Math.random().toString(36).slice(2, 8);
      CTX.waitUntil(ENV.MOCK_KV.put(key, JSON.stringify(entry)));
      // merged recent log (read-merge-write) so __log never freezes at the
      // per-key list limit
      CTX.waitUntil((async () => {
        try {
          const raw = await ENV.MOCK_KV.get("call-log");
          let arr = raw ? JSON.parse(raw) : [];
          arr.push(entry);
          if (arr.length > 300) arr = arr.slice(-300);
          await ENV.MOCK_KV.put("call-log", JSON.stringify(arr));
        } catch (e) { /* best effort */ }
      })());
    } catch (e) { /* best effort */ }
  }
}

// Request envelope: the contract wraps service fields in "data" (+ a "call" object
// the test env ignores); accept the flat shape too, so the workflow's tools work
// whichever way the platform serialises their body.
function payload(body) {
  if (!body || typeof body !== "object") return null;
  return typeof body.data === "object" ? body.data : body;
}

// --- handlers ---
async function handleCardsList(body, path) {
  const d = payload(body);
  if (!d || d.customerNo == null || String(d.customerNo).trim() === "") {
    const r = errInvalid("customer number"); logCall(path, body, 400); return r;
  }
  const entry = tableEntry(DATA.LIST, String(d.customerNo).trim(), true);
  if (!entry) {
    const r = errChannel("FB_IVR_CHANNEL_102", "Müşteriye ait geçerli kart bilgisi bulunamadı.", "NotFoundException");
    logCall(path, body, 404); return r;
  }
  logCall(path, body, entry.http || 200);
  return await serve(entry);
}

async function handleCardsBalance(body, path) {
  const d = payload(body);
  if (!d || !d.cardNumber || String(d.cardNumber).trim() === "") {
    const r = errInvalid("card number"); logCall(path, body, 400); return r;
  }
  const entry = tableEntry(DATA.BALANCE, String(d.cardNumber).trim(), true);
  if (!entry) {
    const r = errChannel("FB_IVR_CHANNEL_120", "Kart bakiye servisi hatası: kart bulunamadı", "NotFoundException");
    logCall(path, body, 404); return r;
  }
  logCall(path, body, entry.http || 200);
  return await serve(entry);
}

async function handleWeekGet(body, path) {
  const d = payload(body);
  if (!d || !d.cardNumber || String(d.cardNumber).trim() === "") {
    const r = errInvalid("card number"); logCall(path, body, 400); return r;
  }
  const entry = tableEntry(DATA.WEEKGET, String(d.cardNumber).trim(), true);
  if (!entry) {
    const r = errChannel("FB_IVR_CHANNEL_121", "Kart bulunamadı", "NotFoundException");
    logCall(path, body, 404); return r;
  }
  logCall(path, body, entry.http || 200);
  return await serve(entry);
}

async function handleWeekDecide(body, path) {
  const d = payload(body);
  if (!d || !d.cardNumber || String(d.cardNumber).trim() === "") {
    const r = errInvalid("card number"); logCall(path, body, 400); return r;
  }
  const w = d.newStatementWeek;
  if (w == null || String(w).trim() === "") {
    const r = errInvalid("new statement week"); logCall(path, body, 400); return r;
  }
  const card = tableEntry(DATA.DECIDE, String(d.cardNumber).trim(), false);
  const entry = card ? card[String(w).trim()] : null;
  if (!entry) {
    // no 404 in the contract for this service -> 400 INVALID_ARGUMENTS_ERROR
    const r = errInvalid("new statement week"); logCall(path, body, 400); return r;
  }
  logCall(path, body, entry.http || 200);
  return await serve(entry);
}

async function handleWeekChange(body, path) {
  const d = payload(body);
  if (!d || !d.cardNumber || String(d.cardNumber).trim() === "") {
    const r = errInvalid("card number"); logCall(path, body, 400); return r;
  }
  const w = d.newStatementWeek;
  if (w == null || String(w).trim() === "") {
    const r = errInvalid("new statement week"); logCall(path, body, 400); return r;
  }
  const card = tableEntry(DATA.CHANGE, String(d.cardNumber).trim(), false);
  const entry = card ? card[String(w).trim()] : null;
  if (!entry) {
    const r = errInvalid("new statement week"); logCall(path, body, 400); return r;
  }
  logCall(path, body, entry.http || 200);
  return await serve(entry);
}

async function handleEmailGet(body, path) {
  const d = payload(body);
  if (!d || d.customerNo == null || String(d.customerNo).trim() === "") {
    const r = errInvalid("customer number"); logCall(path, body, 400); return r;
  }
  if (!d.intAddressInfoType || String(d.intAddressInfoType).trim() === "") {
    const r = errInvalid("intAddressInfoType"); logCall(path, body, 400); return r;
  }
  const entry = tableEntry(DATA.EMAIL, String(d.customerNo).trim(), true);
  if (!entry) {
    const r = errInvalid("customer number"); logCall(path, body, 400); return r;
  }
  logCall(path, body, entry.http || 200);
  return await serve(entry);
}

async function handlePdfSend(body, path) {
  const d = payload(body);
  if (!d || d.customerNo == null || String(d.customerNo).trim() === "") {
    const r = errInvalid("customer number"); logCall(path, body, 400); return r;
  }
  const entry = tableEntry(DATA.PDF, String(d.customerNo).trim(), true);
  if (!entry) {
    const r = errChannel("FB_IVR_CHANNEL_107", "Pdf dokümanı bulunamadı", "NotFoundException");
    logCall(path, body, 404); return r;
  }
  logCall(path, body, entry.http || 200);
  return await serve(entry);
}

async function handleCloseOrTransfer(body, path) {
  // The workflow's synthesized close/transfer tools post here: accept and log,
  // never fail the call.
  const g = guid();
  const res = { result: { guid: g, returnCode: "1", code: "1", messageText: "Success",
                          message: "Success", type: null,
                          details: { guid: g, rootCause: null, errorOrigin: null } } };
  logCall(path, body, 200);
  return json(res);
}

const HANDLERS = {
  "/voice/v1/cards.list": handleCardsList,
  "/voice/v1/cards.balance": handleCardsBalance,
  "/voice/v1/statement.week.get": handleWeekGet,
  "/voice/v1/statement.week.decide": handleWeekDecide,
  "/voice/v1/statement.week.change": handleWeekChange,
  "/voice/v1/contact.email.get": handleEmailGet,
  "/voice/v1/statement.pdf.send": handlePdfSend,
  "/voice/v1/close_call": handleCloseOrTransfer,
  "/voice/v1/transfer_to_human": handleCloseOrTransfer,
};

export default {
  async fetch(request, env, ctx) {
    ENV = env; CTX = ctx;
    const url = new URL(request.url);
    const path = url.pathname;
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS });
    }
    if (request.method === "GET" && path === "/health") {
      return json({ ok: true, status: "healthy", service: "statement-debt", customers: N_CUSTOMERS });
    }
    if (request.method === "GET" && path === "/__log") {
      const all = CALL_LOG.slice();
      let merged = null;
      if (env && env.MOCK_KV) {
        try {
          const raw = await env.MOCK_KV.get("call-log");
          if (raw) merged = JSON.parse(raw);
        } catch (e) { /* memory log still serves */ }
        try {
          const listed = await env.MOCK_KV.list({ prefix: "call:", limit: 500 });
          for (const k of listed.keys) {
            try {
              const raw = await env.MOCK_KV.get(k.name);
              if (raw) all.push(JSON.parse(raw));
            } catch (e) { /* skip */ }
          }
        } catch (e) { /* memory log still serves */ }
      }
      if (Array.isArray(merged)) {
        for (const e of merged) all.push(e);
      }
      all.sort(function (a, b) { return a.at < b.at ? -1 : 1; });
      return json({ ok: true, calls: all.slice(-200), total: all.length });
    }
    const handler = HANDLERS[path];
    if (!handler) {
      return json({ hata: "kayıt bulunamadı" }, 404);
    }
    if (request.method !== "POST") {
      return json({ result: { returnCode: "INVALID_ARGUMENTS_ERROR", code: "INVALID_ARGUMENTS_ERROR", message: "method not allowed", messageText: "method not allowed", type: "ERROR" } }, 405);
    }
    const body = await readBody(request);
    if (body == null) {
      const r = errInvalid("request body"); logCall(path, null, 400); return r;
    }
    return await handler(body, path);
  },
};
"""


def main():
    ap = argparse.ArgumentParser(description="Deterministic final-case mock builder (no LLM)")
    ap.add_argument("contract", nargs="?", default=str(ROOT / "tests" / "final_contract.json"))
    ap.add_argument("customers", nargs="?", default=str(ROOT / "finalcase" / "test-environment" / "test-customers.json"))
    ap.add_argument("--out", default=str(ROOT / "mock" / "final"))
    ap.add_argument("--name", default="final-case-mock-bank")
    a = ap.parse_args()

    contract = load(a.contract)
    customers = load(a.customers)
    tables, n = build_tables(customers)
    if not n:
        raise SystemExit("no customers found in the customers file")

    base = contract.get("base_path") or ""
    services = contract.get("services") or []
    wanted = [base + (s.get("path") or "") for s in services]

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    worker = emit_worker(tables, n)
    (out / "worker.js").write_text(worker, encoding="utf-8")
    (out / "endpoints.json").write_text(json.dumps({
        "worker_name": a.name,
        "get_probes": [{"path": "/health", "probe_of": "/health"}],
        "services": wanted,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    missing = [p for p in wanted if p not in worker]
    print(f"worker: {out / 'worker.js'} ({len(worker)} chars)")
    print(f"customers: {n}; tables: LIST {len(tables['LIST'])}, BALANCE {len(tables['BALANCE'])}, "
          f"WEEKGET {len(tables['WEEKGET'])}, DECIDE {len(tables['DECIDE'])}, CHANGE {len(tables['CHANGE'])}, "
          f"EMAIL {len(tables['EMAIL'])}, PDF {len(tables['PDF'])}")
    print("service paths:", "OK" if not missing else f"MISSING {missing}")
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
