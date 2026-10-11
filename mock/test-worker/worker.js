// freya-collections mock service — one self-contained Cloudflare Workers ES module.
// Tool routes (POST, exact contract paths, base prefix /v1):
//   POST /v1/verify_identity     POST /v1/get_account        POST /v1/create_promise
//   POST /v1/add_note            POST /v1/schedule_callback  POST /v1/transfer_to_agent
//   POST /v1/close_call
// Read routes: GET /health, GET /v1/practice/ledger, GET /v1/practice/ledger/{customer_id}
//
// Every tool call is written to a per-customer ledger. Read it at
// GET /v1/practice/ledger/{customer_id} (add ?pretty=1 for a human view); the graders and
// scorers read what actually happened from there, not from what the phone agent said.
//
// The seed line below keeps its placeholder token: the generator replaces it with
// {"customers":[...]} at deploy time. Never paste seed data here.
const SEED = {"customers":[{"customer_id":"T-1001","case_id":null,"name":null,"variables":{"first_name":"Test","last_name":"Musteri","title":"Bey","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1988-03-14","phone_last4":"4471"},"products":[{"product_id":"p1","type":"credit_card","card_last4":"1234","past_due":420.0,"days_late":12,"minimum_payment":100.0}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":420.0,"date":"2026-10-14"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Confirms identity, promises the full amount today, closes the call.","checks":[],"raw":{"id":"T-1001","family":"smoke","title":"Smoke test customer (synthetic — deploy pipeline test only)","variables":{"first_name":"Test","last_name":"Musteri","title":"Bey","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1988-03-14","phone_last4":"4471"},"products":[{"product_id":"p1","type":"credit_card","card_last4":"1234","past_due":420.0,"days_late":12,"minimum_payment":100.0}],"script":"Confirms identity, promises the full amount today, closes the call.","expected":{"outcome":"promise","promises":[{"product_id":"p1","amount":420.0,"date":"2026-10-14"}]},"checks":[]}}]};

const SERVICE = "freya-collections";
const BASE_PREFIX = "/v1"; // the contract's base path ("" when the contract has none)

// The contract's seven tools, each on its exact contract path. The routes are matched
// literally in fetch() below, so a path can never be silently mis-composed.
const CONTRACT_ROUTES = {
  "/v1/verify_identity": "verify_identity",
  "/v1/get_account": "get_account",
  "/v1/create_promise": "create_promise",
  "/v1/add_note": "add_note",
  "/v1/schedule_callback": "schedule_callback",
  "/v1/transfer_to_agent": "transfer_to_agent",
  "/v1/close_call": "close_call"
};

// Vocabulary the contract fixes.
const IDENTITY_FIELDS = ["date_of_birth", "phone_last4"]; // one answer per call, either order
const WRONG_LIMIT = 3;                                    // three wrong answers lock the check
const NOTE_REASONS = ["refused", "hardship", "dispute", "paid", "service_error"]; // enforced
const QUEUES = ["restructuring", "general", "support"];
const OUTCOMES = ["promise", "paid", "transferred", "no_promise", "not_verified", "not_reached"];
// reason is required for every outcome except promise and paid; the contract defers the
// reason table to the brief, so any non-empty string is accepted — the brief is not enforced.
const REASON_REQUIRED = { transferred: true, no_promise: true, not_verified: true, not_reached: true };

// The one refusal string the mock uses for a missing/failed identity check. The contract
// fixes no exact spelling (only ok=false plus a non-empty error), so the mock picks this
// exact string and keeps it identical on every gated endpoint, every time.
const IDENTITY_REFUSAL = "identity not verified";

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const TIME_RE = /^([01]?\d|2[0-3]):[0-5]\d$/;
const SESSION_SUFFIX_RE = /-s\d+$/;

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers": "content-type, authorization, x-team-key",
  "access-control-max-age": "86400"
};

// The in-memory store is authoritative inside one Worker isolate. When the MOCK_KV
// binding exists, every mutation is mirrored to KV and a state miss in a fresh
// isolate is hydrated from it (best effort: KV is eventually consistent). Without
// the binding everything still works, in memory only.
const MEM = globalThis.__MOCK_STATE__ ||
  (globalThis.__MOCK_STATE__ = { sessions: {}, counts: {}, current: {}, seq: 0 });
if (!MEM.sessions) MEM.sessions = {};
if (!MEM.counts) MEM.counts = {};
if (!MEM.current) MEM.current = {};   // base id -> the session opened most recently for it
if (typeof MEM.seq !== "number") MEM.seq = 0;

function json(obj, status, pretty) {
  return new Response(JSON.stringify(obj, null, pretty ? 2 : 0), {
    status: status || 200,
    headers: Object.assign({ "content-type": "application/json; charset=utf-8" }, CORS)
  });
}

// Accepts the contract path with or without the base prefix, with/without trailing "/".
function canonPath(pathname) {
  let p = String(pathname || "/").replace(/\/+/g, "/");
  if (p.length > 1 && p.endsWith("/")) p = p.slice(0, -1);
  if (p === "/health") return p;
  if (BASE_PREFIX) {
    if (p !== BASE_PREFIX && !p.startsWith(BASE_PREFIX + "/")) {
      p = BASE_PREFIX + (p === "/" ? "" : p);
    }
  }
  return p;
}

function hashInt(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return Math.abs(h);
}

// The seed's customer list — the only place seed data comes from.
function seedList() {
  return (SEED && Array.isArray(SEED.customers)) ? SEED.customers : [];
}

function findSeed(id) {
  const key = String(id);
  const list = seedList();
  for (let i = 0; i < list.length; i++) {
    const c = list[i];
    if (String(c.customer_id) === key || (c.case_id && String(c.case_id) === key)) return c;
  }
  return null;
}

// Unknown customer ids (for example hidden cases, or a session id whose state was
// lost) must never 500: derive a deterministic record so the service stays usable and
// the ledger records everything. The answers are a stable hash of the id, so the same
// unknown id always yields the same customer and the identity check still has real
// answers to compare against.
function derivedSeed(id) {
  const h = hashInt(String(id));
  const pad = function (n) { return n < 10 ? "0" + n : String(n); };
  const dob = (1955 + ((h >>> 5) % 45)) + "-" + pad(1 + (h % 12)) + "-" + pad(1 + ((h >>> 3) % 28));
  return {
    customer_id: String(id), case_id: null, derived: true, variables: {},
    identity: { date_of_birth: dob, phone_last4: pad((h >>> 7) % 100) + pad((h >>> 11) % 100) },
    products: [{ product_id: "p1", type: "credit_card", card_last4: String(1000 + (h % 9000)),
                 past_due: Math.round((100 + (h % 1900)) * 100) / 100, days_late: 1 + (h % 45),
                 minimum_payment: Math.round((30 + (h % 400)) * 100) / 100 }],
    outcome: null, reason: null, promises: [], notes: [], callbacks: [], transfers: [], faults: []
  };
}

// Registers (or re-registers) a case as a seed customer, so tool calls carrying its
// customer_id find the case's identity answers, products, variables and faults.
// Anything the case object leaves out is kept from the customer already in the seed.
function registerRecord(obj, fallbackId) {
  obj = (obj && typeof obj === "object") ? obj : {};
  const raw = (obj.raw && typeof obj.raw === "object") ? obj.raw : {};
  const id = String(obj.customer_id || obj.id || obj.case_id ||
                    raw.customer_id || raw.id || raw.case_id || fallbackId || "").trim();
  if (!id) return null;
  const prev = findSeed(id) || {};
  const products = obj.products || raw.products || prev.products;
  const faults = obj.faults || raw.faults || prev.faults;
  const rec = {
    customer_id: id,
    case_id: (obj.case_id != null ? String(obj.case_id)
              : (raw.case_id != null ? String(raw.case_id) : (prev.case_id || null))),
    variables: Object.assign({}, prev.variables || {}, raw.variables || {}, obj.variables || {}),
    identity: Object.assign({}, prev.identity || {}, raw.identity || {}, obj.identity || {}),
    products: Array.isArray(products) ? products.map(function (p) { return Object.assign({}, p); }) : [],
    faults: Array.isArray(faults) ? faults.slice() : [],
    script: obj.script || raw.script || prev.script || null,
    expected: obj.expected || raw.expected || prev.expected || null
  };
  const list = seedList();
  for (let i = 0; i < list.length; i++) {
    if (String(list[i].customer_id) === id) { list[i] = rec; return rec; }
  }
  list.push(rec);
  return rec;
}

async function seedLookup(env, key) {
  const local = findSeed(key);
  if (local) return local;
  if (env && env.MOCK_KV) {
    try {
      const raw = await env.MOCK_KV.get("customer:" + String(key));
      if (raw) { const rec = JSON.parse(raw); if (rec && rec.customer_id) return registerRecord(rec); }
    } catch (e) { /* KV is a mirror; memory still serves the request */ }
  }
  return null;
}

// The seed for an id: the seed/registered customer, else "<case>-sN"'s base customer,
// else a deterministic derived record.
async function seedFor(env, key) {
  const direct = await seedLookup(env, key);
  if (direct) return direct;
  // SESSION_SUFFIX_RE has no capture group: strip with replace, never exec()[1].
  const base = String(key).replace(SESSION_SUFFIX_RE, "");
  if (base !== String(key)) { const rec = await seedLookup(env, base); if (rec) return rec; }
  return derivedSeed(key);
}

function freshState(seedCustomer, id) {
  return {
    customer_id: String(id),
    case_id: seedCustomer.case_id || null,
    derived: !!seedCustomer.derived,
    seed: seedCustomer,
    variables: Object.assign({}, seedCustomer.variables || {}),
    identity: { verified: false, wrong_answers: 0, locked: false, answers: {} },
    products: (seedCustomer.products || []).map(function (p) { return Object.assign({}, p); }),
    calls: [], promises: [], notes: [], callbacks: [], transfers: [],
    outcome: null, reason: null, closed: false,
    counters: {}, faults: (seedCustomer.faults || []).slice()
  };
}

// Ledger seq stays monotonic inside an isolate even when state arrives from KV.
function bumpSeq(s) {
  if (s && s.calls && s.calls.length) {
    const last = s.calls[s.calls.length - 1].seq;
    if (typeof last === "number" && last > MEM.seq) MEM.seq = last;
  }
}

async function loadState(env, id, register) {
  const key = String(id);
  // KV is authoritative on reads when bound: a stale in-memory copy from before an
  // earlier tool call would otherwise shadow newer state written by another isolate.
  if (env && env.MOCK_KV) {
    try {
      const raw = await env.MOCK_KV.get("session:" + key);
      if (raw) {
        const s = JSON.parse(raw);
        MEM.sessions[key] = s;
        bumpSeq(s);
        return s;
      }
    } catch (e) { /* KV is a mirror; memory still serves the request */ }
  }
  if (MEM.sessions[key]) return MEM.sessions[key];
  const sc = await seedFor(env, key);
  const s = freshState(sc, key);
  if (register !== false) MEM.sessions[key] = s;
  return s;
}

function saveState(env, ctx, s) {
  MEM.sessions[s.customer_id] = s;
  if (env && env.MOCK_KV && ctx && ctx.waitUntil) {
    ctx.waitUntil(env.MOCK_KV.put("session:" + s.customer_id, JSON.stringify(s)));
    // A read may arrive at another isolate asking for the base id; point it at this session.
    const base = String(s.customer_id).replace(SESSION_SUFFIX_RE, "");
    if (base !== s.customer_id) ctx.waitUntil(env.MOCK_KV.put("index:" + base, s.customer_id));
    if (s.case_id) ctx.waitUntil(env.MOCK_KV.put("index:" + s.case_id, s.customer_id));
  }
}

// The case's variables.now is the service clock (the contract's determinism note):
// one second per recorded call keeps ledger timestamps ordered and reproducible.
function callTime(s) {
  const now = (s && s.variables) ? s.variables.now : null;
  if (typeof now === "string" && now.trim()) {
    let iso = now.trim();
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(iso)) iso += ":00";
    if (!/(Z|[+-]\d{2}:?\d{2})$/.test(iso)) iso += "Z";
    const base = Date.parse(iso);
    if (!isNaN(base)) return new Date(base + s.calls.length * 1000).toISOString();
  }
  return new Date().toISOString();
}

// One ledger entry per call: seq is monotonic, order is insertion order, request is the
// parsed body as sent, result is the exact response body returned. Every call is written,
// including refusals and anything arriving after close_call.
function record(s, tool, request, result) {
  s.calls.push({ seq: ++MEM.seq, at: callTime(s), customer_id: s.customer_id,
                 tool: tool, request: request, result: result });
  return result;
}

function ledgerView(s) {
  return {
    customer_id: s.customer_id, case_id: s.case_id, derived: s.derived,
    identity: s.identity, outcome: s.outcome, reason: s.reason, closed: s.closed,
    promises: s.promises, notes: s.notes, callbacks: s.callbacks, transfers: s.transfers,
    calls: s.calls, product_count: s.products.length
  };
}

// The identity gate. The contract gates get_account; the conformance policy gates
// create_promise the same way, so both go through this one function and therefore
// return the same refusal string. The check is on all_verified (both questions
// passed), not on the first passing answer. The refusal is recorded like any other
// call — the ledger is the scorer's evidence, so a refused create_promise must appear
// in calls[] exactly as it was sent, with the refusal as its result.
function verifiedGate(s, tool, body) {
  if (s.identity && s.identity.verified) return null;
  return record(s, tool, body, { ok: false, error: IDENTITY_REFUSAL });
}

function normTool(v) {
  let t = String(v == null ? "" : v).trim().toLowerCase();
  t = t.replace(/^post\s+/, "").replace(/^\/v1\//, "").replace(/^\//, "");
  return t;
}

// Deterministic per-session failure injection. Off by default: no seed customer arms one,
// so it fires only when a practice call arms it. The fault still bumps its own counter (so
// it fires exactly `times` and the repeat then succeeds) but records no ledger entry and
// leaves every contract-visible value — identity counter, lock, promises, notes, callbacks,
// transfers, closed flag — exactly as it was.
function takeFault(s, tool) {
  for (const f of s.faults) {
    if (!f) continue;
    const name = normTool(f.tool != null ? f.tool : (f.endpoint != null ? f.endpoint : f.name));
    if (name !== "*" && name !== "any" && name !== tool) continue;
    const n = (s.counters["fault:" + tool] || 0) + 1;
    s.counters["fault:" + tool] = n;
    let limit = (f.times == null) ? 1 : Number(f.times);
    if (!isFinite(limit)) limit = 1;
    if (n <= limit) return f;
  }
  return null;
}

// ------------------------------------------------------------------- helpers ---
function asObject(v) { return (v && typeof v === "object" && !Array.isArray(v)) ? v : {}; }

// The customer_id in the body is the secret of one call: it is the only identifying
// value, and everything is keyed by it. Numbers are accepted as ids for convenience.
function customerKey(b) {
  const v = b ? b.customer_id : null;
  if (typeof v === "string" && v.trim()) return v.trim();
  if (typeof v === "number" && isFinite(v)) return String(v);
  return null;
}

function reqString(v) {
  if (typeof v === "string" && v.trim()) return v.trim();
  if (typeof v === "number" && isFinite(v)) return String(v);
  return "";
}

function answerString(v) {
  if (typeof v === "string") return v.trim();
  if (typeof v === "number" && isFinite(v)) return String(v);
  return "";
}

// Shapes are validated; business rules are not (the service records a promise on a
// holiday, past the deadline, or for any amount without complaint — following the
// brief is the agent's job, not the mock's).
function toNumber(v) {
  if (typeof v === "number") return isFinite(v) ? v : null;
  if (typeof v === "string" && /^-?\d+(\.\d+)?$/.test(v.trim())) {
    const n = Number(v.trim());
    return isFinite(n) ? n : null;
  }
  return null;
}

function isRealDate(v) {
  if (typeof v !== "string" || !DATE_RE.test(v)) return false;
  const y = Number(v.slice(0, 4)), m = Number(v.slice(5, 7)), d = Number(v.slice(8, 10));
  if (m < 1 || m > 12 || d < 1 || d > 31) return false;
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === m - 1 && dt.getUTCDate() === d;
}

function canonicalTime(v) {
  if (typeof v !== "string") return "";
  const t = v.trim();
  if (!TIME_RE.test(t)) return "";
  const parts = t.split(":");
  return (parts[0].length < 2 ? "0" + parts[0] : parts[0]) + ":" + parts[1];
}

function digitsOnly(v) { return String(v == null ? "" : v).replace(/\D+/g, ""); }

function matchAnswer(field, answer, expected) {
  if (expected == null || expected === "") return false;
  if (field === "phone_last4") {
    const a = digitsOnly(answer), e = digitsOnly(expected);
    if (!a || !e) return false;
    // four digits, or a longer number the caller read out in full
    return a === e || (a.length > e.length && a.slice(-e.length) === e);
  }
  return answer === String(expected).trim();
}

// "1988-03-14" -> "1988-14-03" (the value the hint is attached to; it is often not a
// readable date, which is why the agent produces it in the first place).
function transposeDate(v) {
  if (typeof v !== "string" || !DATE_RE.test(v)) return null;
  return v.slice(0, 4) + "-" + v.slice(8, 10) + "-" + v.slice(5, 7);
}

function transposedMatch(answer, expected) {
  if (expected == null || expected === "") return false;
  const t = transposeDate(String(expected).trim());
  return !!t && answer === t;
}

// Every tool shares two pre-checks that run before validation: a closed call refuses
// everything (recorded, as the contract requires), an armed fault fails with 500 and
// nothing recorded (no ledger entry, no contract-visible state change; the call may be
// repeated and must then succeed). Returns a ready Response, or null to proceed.
function preflight(s, tool, body, env, ctx) {
  if (s.closed) {
    const res = { ok: false, error: "call_closed" };
    record(s, tool, body, res);
    saveState(env, ctx, s);
    return json(res);
  }
  if (takeFault(s, tool)) {
    saveState(env, ctx, s);   // mirrors only the fault counter, so the repeat is not failed again
    return json({ ok: false, error: "service_failed" }, 500);
  }
  return null;
}

// ------------------------------------------------------------------- handlers --

// POST /v1/verify_identity — one security answer per call, either field, any order.
// An unreadable date_of_birth is rejected with ok=false and is NOT a wrong answer;
// unreadable means not a real YYYY-MM-DD date, and it never consumes an attempt.
async function handleVerifyIdentity(body, env, ctx) {
  const b = asObject(body);
  const tool = "verify_identity";
  const key = customerKey(b);
  if (!key) return json({ ok: false, error: "invalid request: customer_id" });
  const s = await loadState(env, key);
  const pre = preflight(s, tool, b, env, ctx);
  if (pre) return pre;

  const left = Math.max(0, WRONG_LIMIT - s.identity.wrong_answers);
  const field = typeof b.field === "string" ? b.field.trim() : "";
  const answer = answerString(b.answer);
  let res;

  if (s.identity.locked) {
    // Three wrong answers end the check for good: every further call is refused.
    res = { ok: false, error: "locked", verified: false, all_verified: false, wrong_answers_left: 0 };
  } else if (IDENTITY_FIELDS.indexOf(field) === -1) {
    res = { ok: false, error: "invalid request: field", verified: false,
            all_verified: s.identity.verified, wrong_answers_left: left };
  } else if (!answer) {
    res = { ok: false, error: "invalid request: answer", verified: false,
            all_verified: s.identity.verified, wrong_answers_left: left };
  } else if (s.identity.answers[field]) {
    // A repeat of an already-passed field is ok and consumes nothing; passing the
    // same field twice must not verify the other one.
    res = { ok: true, verified: true, all_verified: s.identity.verified, wrong_answers_left: left };
  } else {
    const expected = (s.seed && s.seed.identity) ? s.seed.identity[field] : null;
    if (field === "date_of_birth" && !isRealDate(answer)) {
      res = { ok: false, error: "unreadable_date", verified: false, all_verified: false,
              wrong_answers_left: left };
      // The usual way an agent produces an unreadable date is by transposing the
      // day and the month, so the one defined hint is attached to exactly that value.
      if (transposedMatch(answer, expected)) res.hint = "day_month_swapped";
    } else if (matchAnswer(field, answer, expected)) {
      s.identity.answers[field] = true;
      if (s.identity.answers.date_of_birth && s.identity.answers.phone_last4) s.identity.verified = true;
      res = { ok: true, verified: true, all_verified: s.identity.verified, wrong_answers_left: left };
    } else {
      // Wrong answers are counted cumulatively across both fields, per customer.
      s.identity.wrong_answers += 1;
      if (s.identity.wrong_answers >= WRONG_LIMIT) s.identity.locked = true;
      res = { ok: false, error: "wrong_answer", verified: false, all_verified: false,
              wrong_answers_left: Math.max(0, WRONG_LIMIT - s.identity.wrong_answers) };
      if (field === "date_of_birth" && transposedMatch(answer, expected)) res.hint = "day_month_swapped";
    }
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// POST /v1/get_account — the late products; identity-gated (both questions must pass).
async function handleGetAccount(body, env, ctx) {
  const b = asObject(body);
  const tool = "get_account";
  const key = customerKey(b);
  if (!key) return json({ ok: false, error: "invalid request: customer_id" });
  const s = await loadState(env, key);
  const pre = preflight(s, tool, b, env, ctx);
  if (pre) return pre;

  const refused = verifiedGate(s, tool, b);
  if (refused) { saveState(env, ctx, s); return json(refused); }

  const res = { ok: true, products: s.products };
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// POST /v1/create_promise — identity-gated exactly like get_account: the gate runs at
// the top, before the product_id/amount/date branch, so an unverified create_promise
// returns 200 {ok:false, error:"identity not verified"} and appends nothing to promises[].
// The refusal is recorded in calls[] like any other call. No business rule is enforced:
// any amount and any real date are accepted (following the brief is the agent's job).
async function handleCreatePromise(body, env, ctx) {
  const b = asObject(body);
  const tool = "create_promise";
  const key = customerKey(b);
  if (!key) return json({ ok: false, error: "bad_request" });
  const s = await loadState(env, key);
  const pre = preflight(s, tool, b, env, ctx);
  if (pre) return pre;

  const refused = verifiedGate(s, tool, b);
  if (refused) { saveState(env, ctx, s); return json(refused); }

  const productId = reqString(b.product_id);
  const amount = toNumber(b.amount);
  const date = reqString(b.date);
  let res;
  if (!productId || amount === null || !isRealDate(date)) {
    res = { ok: false, error: "bad_request" };
  } else if (s.promises.some(function (p) { return String(p.product_id) === productId; })) {
    res = { ok: false, error: "already_promised" };
  } else {
    const n = (s.counters.promise || 0) + 1;
    s.counters.promise = n;
    const promiseId = "pr" + n;
    s.promises.push({ product_id: productId, amount: amount, date: date });
    res = { ok: true, promise_id: promiseId };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// POST /v1/add_note — Brief B: why a product ended without a promise. The reason enum
// is the one vocabulary the service does enforce; the text is free.
async function handleAddNote(body, env, ctx) {
  const b = asObject(body);
  const tool = "add_note";
  const key = customerKey(b);
  if (!key) return json({ ok: false, error: "bad_request" });
  const s = await loadState(env, key);
  const pre = preflight(s, tool, b, env, ctx);
  if (pre) return pre;

  const productId = reqString(b.product_id);
  const reason = typeof b.reason === "string" ? b.reason.trim() : "";
  let res;
  if (!productId || NOTE_REASONS.indexOf(reason) === -1) {
    res = { ok: false, error: "bad_request" };
  } else {
    s.notes.push({ product_id: productId, reason: reason });
    res = { ok: true };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// POST /v1/schedule_callback — book a callback; date is YYYY-MM-DD, time is HH:MM.
async function handleScheduleCallback(body, env, ctx) {
  const b = asObject(body);
  const tool = "schedule_callback";
  const key = customerKey(b);
  if (!key) return json({ ok: false, error: "bad_request" });
  const s = await loadState(env, key);
  const pre = preflight(s, tool, b, env, ctx);
  if (pre) return pre;

  const date = reqString(b.date);
  const time = canonicalTime(b.time);
  let res;
  if (!isRealDate(date) || !time) {
    res = { ok: false, error: "bad_request" };
  } else {
    s.callbacks.push({ date: date, time: time });
    res = { ok: true };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// POST /v1/transfer_to_agent — hand the call to a person. It does not end the call:
// a close_call with outcome=transferred must still follow.
async function handleTransferToAgent(body, env, ctx) {
  const b = asObject(body);
  const tool = "transfer_to_agent";
  const key = customerKey(b);
  if (!key) return json({ ok: false, error: "bad_request" });
  const s = await loadState(env, key);
  const pre = preflight(s, tool, b, env, ctx);
  if (pre) return pre;

  const queue = typeof b.queue === "string" ? b.queue.trim() : "";
  let res;
  if (QUEUES.indexOf(queue) === -1) {
    res = { ok: false, error: "bad_request" };
  } else {
    s.transfers.push({ queue: queue });
    res = { ok: true };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// POST /v1/close_call — always the last tool call. reason is required for every
// outcome except promise and paid; any non-empty string is accepted (the brief's
// reason table is not enforced here).
async function handleCloseCall(body, env, ctx) {
  const b = asObject(body);
  const tool = "close_call";
  const key = customerKey(b);
  if (!key) return json({ ok: false, error: "invalid request: customer_id" });
  const s = await loadState(env, key);
  const pre = preflight(s, tool, b, env, ctx);
  if (pre) return pre;

  const outcome = typeof b.outcome === "string" ? b.outcome.trim() : "";
  const reason = typeof b.reason === "string" ? b.reason.trim() : "";
  let res;
  if (OUTCOMES.indexOf(outcome) === -1) {
    res = { ok: false, error: "invalid request: outcome" };
  } else if (REASON_REQUIRED[outcome] && !reason) {
    res = { ok: false, error: "reason_required" };   // the call is not closed
  } else {
    s.outcome = outcome;
    s.reason = REASON_REQUIRED[outcome] ? reason : null;
    s.closed = true;
    res = { ok: true };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

const HANDLERS = {
  verify_identity: handleVerifyIdentity,
  get_account: handleGetAccount,
  create_promise: handleCreatePromise,
  add_note: handleAddNote,
  schedule_callback: handleScheduleCallback,
  transfer_to_agent: handleTransferToAgent,
  close_call: handleCloseCall
};

// ------------------------------------------------------- sessions and reads ---

function pickCase(body) {
  const keys = ["case", "case_id", "customer_id", "customer", "id"];
  for (const k of keys) {
    const v = body ? body[k] : null;
    if (typeof v === "string" && v.trim()) return v.trim();
    if (v && typeof v === "object") return v;
  }
  if (body && (body.variables || body.identity || body.products || body.raw)) return body;
  return null;
}

// POST /v1/practice/sessions {"case": "<case object or id>"} -> {"variables": {...}}
// The contract has no session endpoint, so this practice route registers the case's
// customer in the seed (identity answers, products, variables, faults) and opens a
// fresh "<customer_id>-sN" session so parallel runs never share state.
async function handleCreateSession(body, env, ctx) {
  const b = asObject(body);
  const pick = pickCase(b);
  let sc = null;
  if (typeof pick === "string") {
    // The body may carry the case itself next to the id: register it so the case's
    // identity answers, products and variables actually serve the session.
    if (b.variables || b.identity || b.products || b.raw) {
      sc = registerRecord(Object.assign({ customer_id: pick }, b));
    }
    if (!sc) sc = findSeed(pick);
    if (!sc) return json({ ok: false, error: "unknown case", case: pick }, 404);
  } else if (pick && typeof pick === "object") {
    sc = registerRecord(pick);
    if (!sc) return json({ ok: false, error: "unknown case" }, 404);
  } else {
    return json({ ok: false, error: "unknown case" }, 404);
  }

  const base = String(sc.customer_id);
  // The counter is read/incremented through KV when bound, so two isolates never
  // issue the same session id (a collision lets their states overwrite each other).
  let n = (MEM.counts[base] || 0) + 1;
  if (env && env.MOCK_KV) {
    try {
      const cur = await env.MOCK_KV.get("counter:" + base);
      const prev = cur ? parseInt(cur, 10) : 0;
      n = Math.max(n, prev + 1);
      ctx.waitUntil(env.MOCK_KV.put("counter:" + base, String(n)));
    } catch (e) { /* the memory counter still serves */ }
  }
  MEM.counts[base] = n;
  const id = base + "-s" + n;
  const s = freshState(sc, id);
  MEM.sessions[id] = s;
  MEM.current[base] = id;
  if (sc.case_id) MEM.current[String(sc.case_id)] = id;
  // A new session is a clean run of the case: drop the bare-id state a previous run
  // left behind. Sessions already opened for this case are left alone, so parallel
  // runs keep their own "-sN" state.
  if (MEM.sessions[base] && MEM.sessions[base] !== s) {
    delete MEM.sessions[base];
    if (env && env.MOCK_KV && ctx && ctx.waitUntil) ctx.waitUntil(env.MOCK_KV.delete("session:" + base));
  }
  saveState(env, ctx, s);
  if (env && env.MOCK_KV && ctx && ctx.waitUntil) {
    ctx.waitUntil(env.MOCK_KV.put("customer:" + base, JSON.stringify(sc)));
  }
  const variables = Object.assign({}, sc.variables || {}, { customer_id: id });
  return json({ ok: true, customer_id: id, variables: variables });
}

// Resolves a read id to a live session: the id itself when it holds calls, else the
// session opened most recently for that case, else the sibling with the most calls —
// so a read accepts the base customer id even after sessions appended "-sN".
function findSessionId(id) {
  const key = String(id);
  const exact = MEM.sessions[key];
  if (exact && exact.calls.length) return key;
  const cur = MEM.current[key];
  if (cur && MEM.sessions[cur]) return cur;
  if (exact) return key;
  const cand = [];
  for (const k of Object.keys(MEM.sessions)) {
    const s = MEM.sessions[k];
    if (!s) continue;
    if (String(s.case_id) === key || k.indexOf(key + "-s") === 0) cand.push(k);
  }
  if (!cand.length) return key;
  cand.sort(function (a, b2) {
    const ca = MEM.sessions[a].calls.length, cb = MEM.sessions[b2].calls.length;
    if (ca !== cb) return cb - ca;
    return a < b2 ? 1 : (a > b2 ? -1 : 0);
  });
  return cand[0];
}

// Cross-isolate reads: KV holds a base-id -> session-id index written with every save.
async function resolveSessionId(env, id) {
  const key = findSessionId(id);
  if (MEM.sessions[key]) return key;
  if (env && env.MOCK_KV) {
    try {
      const mapped = await env.MOCK_KV.get("index:" + String(id));
      if (mapped) return String(mapped);
    } catch (e) { /* KV is a mirror; memory still serves the request */ }
  }
  return key;
}

// Best effort: a read landing in a fresh isolate still sees the sessions in KV.
async function hydrateAll(env) {
  if (!env || !env.MOCK_KV || !env.MOCK_KV.list) return;
  if (Object.keys(MEM.sessions).length) return;
  try {
    const list = await env.MOCK_KV.list({ prefix: "session:", limit: 100 });
    for (const k of (list && list.keys) || []) {
      const id = String(k.name).slice("session:".length);
      if (!MEM.sessions[id]) {
        const raw = await env.MOCK_KV.get(k.name);
        if (raw) { const s = JSON.parse(raw); MEM.sessions[id] = s; bumpSeq(s); }
      }
    }
  } catch (e) { /* KV is a mirror; memory still serves the request */ }
}

function isPretty(url) {
  const p = url.searchParams.get("pretty");
  if (p === null) return false;
  const v = p.toLowerCase();
  return p === "" || p === "1" || v === "true" || v === "yes";
}

// --------------------------------------------------------------------- fetch ---
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = canonPath(url.pathname);
    try {
      if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });

      // No auth, no state change, never blocked by the identity gate.
      if (path === "/health" && request.method === "GET") {
        return json({ ok: true, status: "healthy", service: SERVICE,
                      state_model: "cross-call", customers: seedList().length });
      }

      let body = null;
      if (request.method === "POST" || request.method === "PUT" || request.method === "PATCH") {
        try { body = await request.json(); } catch (e) { body = null; }
      }

      // --- the contract's seven tool endpoints: exact paths, POST only ---
      if (path === "/v1/verify_identity" ||
          path === "/v1/get_account" ||
          path === "/v1/create_promise" ||
          path === "/v1/add_note" ||
          path === "/v1/schedule_callback" ||
          path === "/v1/transfer_to_agent" ||
          path === "/v1/close_call") {
        if (request.method !== "POST") {
          return json({ ok: false, error: "method not allowed", path: path }, 405);
        }
        return await HANDLERS[CONTRACT_ROUTES[path]](body, env, ctx);
      }

      // --- session opener: POST {"case": "<case object or id>"} -> {"variables": {...}} ---
      if (path === "/v1/practice/sessions" && request.method === "POST") {
        return await handleCreateSession(body, env, ctx);
      }

      // --- ledger and session read routes (the scorers read these) ---
      const LEDGER_PREFIX = "/v1/practice/ledger/";
      if (request.method === "GET" && path.indexOf(LEDGER_PREFIX) === 0 && path.length > LEDGER_PREFIX.length) {
        const id = decodeURIComponent(path.slice(LEDGER_PREFIX.length));
        await hydrateAll(env);
        const s = await loadState(env, await resolveSessionId(env, id), false);
        return json(ledgerView(s), 200, isPretty(url));
      }
      if (path === "/v1/practice/ledger" && request.method === "GET") {
        await hydrateAll(env);
        const all = {};
        for (const k of Object.keys(MEM.sessions)) all[k] = ledgerView(MEM.sessions[k]);
        return json({ ok: true, sessions: all }, 200, isPretty(url));
      }
      if (path === "/v1/practice/sessions" && request.method === "GET") {
        await hydrateAll(env);
        return json({ ok: true, sessions: Object.keys(MEM.sessions) });
      }
      const RESET_PREFIX = "/v1/practice/reset/";
      if (request.method === "POST" && path.indexOf(RESET_PREFIX) === 0 && path.length > RESET_PREFIX.length) {
        const key = await resolveSessionId(env, decodeURIComponent(path.slice(RESET_PREFIX.length)));
        delete MEM.sessions[key];
        if (env && env.MOCK_KV && ctx && ctx.waitUntil) ctx.waitUntil(env.MOCK_KV.delete("session:" + key));
        return json({ ok: true, customer_id: key });
      }
      // Test hook: POST /v1/practice/faults/<customer_id> {"tool":"get_account","times":1}
      // arms a contract fault (off by default); {"clear": true} disarms them again.
      const FAULT_PREFIX = "/v1/practice/faults/";
      if (request.method === "POST" && path.indexOf(FAULT_PREFIX) === 0 && path.length > FAULT_PREFIX.length) {
        const b = asObject(body);
        const s = await loadState(env, findSessionId(decodeURIComponent(path.slice(FAULT_PREFIX.length))));
        if (b.clear) {
          s.faults = [];
          s.counters = {};
          saveState(env, ctx, s);
          return json({ ok: true, customer_id: s.customer_id, faults: [] });
        }
        const name = normTool(b.tool != null ? b.tool : b.endpoint);
        if (!name) return json({ ok: false, error: "invalid request: tool" });
        s.faults.push({ tool: name, times: b.times == null ? 1 : b.times });
        saveState(env, ctx, s);
        return json({ ok: true, customer_id: s.customer_id, faults: s.faults });
      }
      return json({ ok: false, error: "not found", path: path }, 404);
    } catch (e) {
      return json({ ok: false, error: "internal error" }, 500);
    }
  }
};
