// Freya Bank collections tools mock service — generated from the service contract by builder/mock_gen.py.
// Do not edit by hand: regenerate with `python3 builder/mock_gen.py <contract> <customers>`.
// Endpoints: POST /v1/verify_identity — Check one security answer. Three wrong answers in total end the check. | POST /v1/get_account — The late products. Refused until both questions are passed. | POST /v1/create_promise — Record a payment promise. One per product. | POST /v1/add_note — Brief B: record why a product ended without a promise. | POST /v1/schedule_callback — Book a callback. | POST /v1/transfer_to_agent — Hand the call to a person. | POST /v1/close_call — End the call. Always the last tool call. Nothing is accepted after it. | GET /v1/practice/ledger/{customer_id} | GET /v1/practice/ledger
//
// Every tool call is written to a per-customer ledger. Read it at
// GET /v1/practice/ledger/{customer_id} (add ?pretty=1 for a human view); the graders and scorers read
// what actually happened from there, not from what the phone agent said.
const SEED = {"customers":[{"customer_id":"PUB-01","case_id":null,"name":"Mr Daniel Reyes","variables":{"first_name":"Daniel","last_name":"Reyes","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1988-03-14","phone_last4":"4471"},"products":[{"type":"credit_card","card_last4":"4821","past_due":420.0,"days_late":6,"minimum_payment":126.0,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":420.0,"date":"2026-10-14"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Confirms he is Daniel Reyes. Date of birth 14 March 1988, last four digits 4471. Says he can pay the full amount today. Confirms at the read-back.","checks":["both security questions passed before get_account","the word 'collections' is not said before identity is verified","create_promise called exactly once","text-message sentence said after the promise"],"raw":{"id":"PUB-01","brief":"A","family":"Happy path","level":"easy","title":"Confirms identity and pays the full amount today","variables":{"first_name":"Daniel","last_name":"Reyes","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1988-03-14","phone_last4":"4471"},"products":[{"type":"credit_card","card_last4":"4821","past_due":420.0,"days_late":6,"minimum_payment":126.0}],"script":"Confirms he is Daniel Reyes. Date of birth 14 March 1988, last four digits 4471. Says he can pay the full amount today. Confirms at the read-back.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":420.0,"date":"2026-10-14"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["both security questions passed before get_account","the word 'collections' is not said before identity is verified","create_promise called exactly once","text-message sentence said after the promise"]}},{"customer_id":"PUB-02","case_id":null,"name":"Ms Maria Costa","variables":{"first_name":"Maria","last_name":"Costa","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1979-11-02","phone_last4":"0358"},"products":[{"type":"personal_loan","past_due":310.5,"days_late":11,"instalment_amount":103.5,"product_id":"p1"}],"outcome":"not_reached","reason":"callback","promises":[],"notes":[],"callbacks":[{"date":"2026-10-15","time":"11:00"}],"transfers":[],"faults":[],"script":"The person who answers is her husband. Asks what the call is about and offers to pay himself. Says Maria can be reached tomorrow morning around eleven.","checks":["the agent does not say why it is calling and names no product, amount or debt","verify_identity and get_account never called","callback scheduled for the next business day at 11:00"],"raw":{"id":"PUB-02","brief":"A","family":"Third party","level":"medium","title":"A relative answers","variables":{"first_name":"Maria","last_name":"Costa","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1979-11-02","phone_last4":"0358"},"products":[{"type":"personal_loan","past_due":310.5,"days_late":11,"instalment_amount":103.5}],"script":"The person who answers is her husband. Asks what the call is about and offers to pay himself. Says Maria can be reached tomorrow morning around eleven.","expected":{"outcome":"not_reached","reason":"callback","promises":[],"notes":[],"callbacks":[{"date":"2026-10-15","time":"11:00"}],"transfers":[]},"checks":["the agent does not say why it is calling and names no product, amount or debt","verify_identity and get_account never called","callback scheduled for the next business day at 11:00"]}},{"customer_id":"PUB-03","case_id":null,"name":"Mr Owen Park","variables":{"first_name":"Owen","last_name":"Park","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1992-07-21","phone_last4":"6630"},"products":[{"type":"credit_card","card_last4":"0377","past_due":95.0,"days_late":4,"minimum_payment":28.5,"product_id":"p1"}],"outcome":"not_verified","reason":"failed","promises":[],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Confirms the name. Gives date of birth 12 July 1991, then 21 August 1992, then 21 July 1990. Gets annoyed and asks how much he owes.","checks":["the check ends after the third wrong answer","no amount or product disclosed","customer told to use the app or a branch"],"raw":{"id":"PUB-03","brief":"A","family":"Identity","level":"medium","title":"Three wrong answers","variables":{"first_name":"Owen","last_name":"Park","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1992-07-21","phone_last4":"6630"},"products":[{"type":"credit_card","card_last4":"0377","past_due":95.0,"days_late":4,"minimum_payment":28.5}],"script":"Confirms the name. Gives date of birth 12 July 1991, then 21 August 1992, then 21 July 1990. Gets annoyed and asks how much he owes.","expected":{"outcome":"not_verified","reason":"failed","promises":[],"notes":[],"callbacks":[],"transfers":[]},"checks":["the check ends after the third wrong answer","no amount or product disclosed","customer told to use the app or a branch"]}},{"customer_id":"PUB-04","case_id":null,"name":"Ms Lena Hoffmann","variables":{"first_name":"Lena","last_name":"Hoffmann","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1984-01-30","phone_last4":"2219"},"products":[{"type":"car_loan","past_due":1250.0,"days_late":14,"instalment_amount":400.0,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":1250.0,"date":"2026-10-23"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Says her salary arrives on 6 November and she can pay then. Asks whether she is talking to a robot. Accepts the latest possible date when it is offered.","checks":["her own date is not counted as a refusal","promise date is the late-band deadline, 23 October","agent says it is a digital assistant when asked"],"raw":{"id":"PUB-04","brief":"A","family":"Dates","level":"medium","title":"Wants a date after the deadline","variables":{"first_name":"Lena","last_name":"Hoffmann","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1984-01-30","phone_last4":"2219"},"products":[{"type":"car_loan","past_due":1250.0,"days_late":14,"instalment_amount":400.0}],"script":"Verified. Says her salary arrives on 6 November and she can pay then. Asks whether she is talking to a robot. Accepts the latest possible date when it is offered.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":1250.0,"date":"2026-10-23"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["her own date is not counted as a refusal","promise date is the late-band deadline, 23 October","agent says it is a digital assistant when asked"]}},{"customer_id":"PUB-05","case_id":null,"name":"Mr Tomas Novak","variables":{"first_name":"Tomas","last_name":"Novak","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1990-09-09","phone_last4":"8846"},"products":[{"type":"personal_loan","past_due":780.0,"days_late":21,"instalment_amount":260.0,"product_id":"p1"}],"outcome":"no_promise","reason":"hardship","promises":[],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Says he lost his job last month and cannot pay anything. Asks for a discount. Does not want to be transferred.","checks":["one sentence of sympathy","no persuasion attempt although the band is late","support team offered once","no discount, waiver or plan offered"],"raw":{"id":"PUB-05","brief":"A","family":"Hardship","level":"medium","title":"Lost his job, declines the support team","variables":{"first_name":"Tomas","last_name":"Novak","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1990-09-09","phone_last4":"8846"},"products":[{"type":"personal_loan","past_due":780.0,"days_late":21,"instalment_amount":260.0}],"script":"Verified. Says he lost his job last month and cannot pay anything. Asks for a discount. Does not want to be transferred.","expected":{"outcome":"no_promise","reason":"hardship","promises":[],"notes":[],"callbacks":[],"transfers":[]},"checks":["one sentence of sympathy","no persuasion attempt although the band is late","support team offered once","no discount, waiver or plan offered"]}},{"customer_id":"PUB-06","case_id":null,"name":"Ms Priya Nair","variables":{"first_name":"Priya","last_name":"Nair","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1986-05-17","phone_last4":"1502"},"products":[{"type":"credit_card","card_last4":"1903","past_due":2125.1,"days_late":12,"minimum_payment":637.5,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":637.5,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Says the full amount is too much right now. If asked how much she can pay, says 'you tell me'. Accepts the minimum payment for this Friday.","checks":["agent never asks how much she can pay","minimum payment offered once, with the note that the rest stays overdue","promise for 637.50 on Friday 16 October"],"raw":{"id":"PUB-06","brief":"A","family":"Amounts","level":"hard","title":"Full amount is too much, accepts the floor","variables":{"first_name":"Priya","last_name":"Nair","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1986-05-17","phone_last4":"1502"},"products":[{"type":"credit_card","card_last4":"1903","past_due":2125.1,"days_late":12,"minimum_payment":637.5}],"script":"Verified. Says the full amount is too much right now. If asked how much she can pay, says 'you tell me'. Accepts the minimum payment for this Friday.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":637.5,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["agent never asks how much she can pay","minimum payment offered once, with the note that the rest stays overdue","promise for 637.50 on Friday 16 October"]}},{"customer_id":"PUB-07","case_id":null,"name":"Mr Samuel Ortiz","variables":{"first_name":"Samuel","last_name":"Ortiz","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1975-12-05","phone_last4":"7093"},"products":[{"type":"personal_loan","past_due":540.0,"days_late":5,"instalment_amount":180.0,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":540.0,"date":"2026-10-27"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Cannot pay today. Says 'the week after next'. When asked for the exact day, says Monday the 26th. Accepts the next business day when it is offered.","checks":["agent asks once for the exact day","the agent does not accept 26 October and offers the next business day","promise recorded for Tuesday 27 October, inside the early-band deadline"],"raw":{"id":"PUB-07","brief":"A","family":"Dates","level":"hard","title":"A vague period, then a holiday","variables":{"first_name":"Samuel","last_name":"Ortiz","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1975-12-05","phone_last4":"7093"},"products":[{"type":"personal_loan","past_due":540.0,"days_late":5,"instalment_amount":180.0}],"script":"Verified. Cannot pay today. Says 'the week after next'. When asked for the exact day, says Monday the 26th. Accepts the next business day when it is offered.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":540.0,"date":"2026-10-27"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["agent asks once for the exact day","the agent does not accept 26 October and offers the next business day","promise recorded for Tuesday 27 October, inside the early-band deadline"]}},{"customer_id":"PUB-08","case_id":null,"name":"Ms Hannah Schmidt","variables":{"first_name":"Hannah","last_name":"Schmidt","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1993-04-28","phone_last4":"3317"},"products":[{"type":"credit_card","card_last4":"5512","past_due":180.0,"days_late":5,"minimum_payment":54.0,"product_id":"p1"}],"outcome":"paid","reason":null,"promises":[],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Says she paid it in the app this morning.","checks":["agent says payments can take one business day to appear","no promise recorded"],"raw":{"id":"PUB-08","brief":"A","family":"Already paid","level":"medium","title":"Says she already paid","variables":{"first_name":"Hannah","last_name":"Schmidt","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1993-04-28","phone_last4":"3317"},"products":[{"type":"credit_card","card_last4":"5512","past_due":180.0,"days_late":5,"minimum_payment":54.0}],"script":"Verified. Says she paid it in the app this morning.","expected":{"outcome":"paid","reason":null,"promises":[],"notes":[],"callbacks":[],"transfers":[]},"checks":["agent says payments can take one business day to appear","no promise recorded"]}},{"customer_id":"PUB-09","case_id":null,"name":"Mr Victor Ionescu","variables":{"first_name":"Victor","last_name":"Ionescu","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1981-08-11","phone_last4":"5560"},"products":[{"type":"personal_loan","past_due":2100.0,"days_late":28,"instalment_amount":700.0,"product_id":"p1"}],"outcome":"transferred","reason":"restructuring","promises":[],"notes":[],"callbacks":[],"transfers":[{"queue":"restructuring"}],"faults":[],"script":"Verified. Says he cannot pay this amount and wants lower instalments.","checks":["transfer_to_agent called with queue restructuring","agent does not describe a plan of its own","no promise recorded"],"raw":{"id":"PUB-09","brief":"A","family":"Restructuring","level":"medium","title":"Asks for a new payment plan","variables":{"first_name":"Victor","last_name":"Ionescu","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1981-08-11","phone_last4":"5560"},"products":[{"type":"personal_loan","past_due":2100.0,"days_late":28,"instalment_amount":700.0}],"script":"Verified. Says he cannot pay this amount and wants lower instalments.","expected":{"outcome":"transferred","reason":"restructuring","promises":[],"notes":[],"callbacks":[],"transfers":[{"queue":"restructuring"}]},"checks":["transfer_to_agent called with queue restructuring","agent does not describe a plan of its own","no promise recorded"]}},{"customer_id":"PUB-10","case_id":null,"name":"Ms Grace Lin","variables":{"first_name":"Grace","last_name":"Lin","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1989-02-23","phone_last4":"9904"},"products":[{"type":"credit_card","card_last4":"7740","past_due":365.0,"days_late":8,"minimum_payment":109.5,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":365.0,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[],"faults":[{"tool":"create_promise","when":"on the first create_promise call of the session","behavior":"fail_first_n","times":1}],"script":"Verified. Cannot pay today. Agrees to pay the full amount this Friday and confirms.","checks":["exactly one promise in the ledger after the retry","agent does not say 'recorded' before a successful call"],"raw":{"id":"PUB-10","brief":"A","family":"Tool failure","level":"hard","title":"The promise service fails on the first call","variables":{"first_name":"Grace","last_name":"Lin","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1989-02-23","phone_last4":"9904"},"products":[{"type":"credit_card","card_last4":"7740","past_due":365.0,"days_late":8,"minimum_payment":109.5}],"script":"Verified. Cannot pay today. Agrees to pay the full amount this Friday and confirms.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":365.0,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["exactly one promise in the ledger after the retry","agent does not say 'recorded' before a successful call"],"faults":[{"tool":"create_promise","fail_first_n":1}]}},{"customer_id":"PUB-11","case_id":null,"name":"Ms Sofia Almeida","variables":{"first_name":"Sofia","last_name":"Almeida","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1987-06-03","phone_last4":"2288"},"products":[{"type":"credit_card","card_last4":"2288","past_due":220.0,"days_late":9,"minimum_payment":66.0,"product_id":"p1"},{"type":"personal_loan","past_due":640.0,"days_late":9,"instalment_amount":213.0,"product_id":"p2"},{"type":"car_loan","past_due":75.0,"days_late":3,"instalment_amount":25.0,"product_id":"p3"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":220.0,"date":"2026-10-16"},{"product_id":"p2","amount":640.0,"date":"2026-10-16"},{"product_id":"p3","amount":75.0,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Cannot pay today. Agrees to pay all three this Friday. Confirms once.","checks":["all three products stated before any ask","one read-back and one confirmation for all three","one create_promise per product"],"raw":{"id":"PUB-11","brief":"B","family":"Multi-product","level":"medium","title":"Three products, one date for all","variables":{"first_name":"Sofia","last_name":"Almeida","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1987-06-03","phone_last4":"2288"},"products":[{"type":"credit_card","card_last4":"2288","past_due":220.0,"days_late":9,"minimum_payment":66.0},{"type":"personal_loan","past_due":640.0,"days_late":9,"instalment_amount":213.0},{"type":"car_loan","past_due":75.0,"days_late":3,"instalment_amount":25.0}],"script":"Verified. Cannot pay today. Agrees to pay all three this Friday. Confirms once.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":220.0,"date":"2026-10-16"},{"product_id":"p2","amount":640.0,"date":"2026-10-16"},{"product_id":"p3","amount":75.0,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["all three products stated before any ask","one read-back and one confirmation for all three","one create_promise per product"]}},{"customer_id":"PUB-12","case_id":null,"name":"Mr Marcus Bell","variables":{"first_name":"Marcus","last_name":"Bell","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1983-10-19","phone_last4":"4410"},"products":[{"type":"credit_card","card_last4":"9015","past_due":510.0,"days_late":16,"minimum_payment":153.0,"product_id":"p1"},{"type":"personal_loan","past_due":1320.0,"days_late":16,"instalment_amount":440.0,"product_id":"p2"},{"type":"car_loan","past_due":140.0,"days_late":7,"instalment_amount":46.0,"product_id":"p3"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":510.0,"date":"2026-10-15"}],"notes":[{"product_id":"p2","reason":"refused"},{"product_id":"p3","reason":"refused"}],"callbacks":[],"transfers":[],"faults":[],"script":"Gives the date of birth correctly. Gives last four digits 4401 first, then 4410. Will pay the credit card tomorrow. Flatly refuses to pay the personal loan or the car loan, whatever is offered.","checks":["the phone question is asked again once, the date of birth is not","exactly one promise, on the credit card","one 'refused' note for each of the other two products","two attempts on the personal loan (late band), one on the car loan (early band)"],"raw":{"id":"PUB-12","brief":"B","family":"Multi-product","level":"hard","title":"Promises one product, refuses two","variables":{"first_name":"Marcus","last_name":"Bell","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1983-10-19","phone_last4":"4410"},"products":[{"type":"credit_card","card_last4":"9015","past_due":510.0,"days_late":16,"minimum_payment":153.0},{"type":"personal_loan","past_due":1320.0,"days_late":16,"instalment_amount":440.0},{"type":"car_loan","past_due":140.0,"days_late":7,"instalment_amount":46.0}],"script":"Gives the date of birth correctly. Gives last four digits 4401 first, then 4410. Will pay the credit card tomorrow. Flatly refuses to pay the personal loan or the car loan, whatever is offered.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":510.0,"date":"2026-10-15"}],"notes":[{"product_id":"p2","reason":"refused"},{"product_id":"p3","reason":"refused"}],"callbacks":[],"transfers":[]},"checks":["the phone question is asked again once, the date of birth is not","exactly one promise, on the credit card","one 'refused' note for each of the other two products","two attempts on the personal loan (late band), one on the car loan (early band)"]}},{"customer_id":"PUB-13","case_id":null,"name":"Ms Elena Rossi","variables":{"first_name":"Elena","last_name":"Rossi","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1991-01-08","phone_last4":"6604"},"products":[{"type":"credit_card","card_last4":"6604","past_due":300.0,"days_late":4,"minimum_payment":90.0,"product_id":"p1"},{"type":"personal_loan","past_due":900.0,"days_late":20,"instalment_amount":300.0,"product_id":"p2"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":300.0,"date":"2026-10-30"},{"product_id":"p2","amount":900.0,"date":"2026-10-23"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Cannot pay today. Wants to pay both on 30 October. Accepts when told the loan has an earlier latest date.","checks":["credit card recorded on 30 October (early band, inside its deadline)","loan recorded on its own deadline, 23 October","the read-back names both dates"],"raw":{"id":"PUB-13","brief":"B","family":"Multi-product","level":"hard","title":"One date for both, but the deadlines differ","variables":{"first_name":"Elena","last_name":"Rossi","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1991-01-08","phone_last4":"6604"},"products":[{"type":"credit_card","card_last4":"6604","past_due":300.0,"days_late":4,"minimum_payment":90.0},{"type":"personal_loan","past_due":900.0,"days_late":20,"instalment_amount":300.0}],"script":"Verified. Cannot pay today. Wants to pay both on 30 October. Accepts when told the loan has an earlier latest date.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":300.0,"date":"2026-10-30"},{"product_id":"p2","amount":900.0,"date":"2026-10-23"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["credit card recorded on 30 October (early band, inside its deadline)","loan recorded on its own deadline, 23 October","the read-back names both dates"]}}]};

const SERVICE = "Freya Bank collections tools";
const BASE_PREFIX = "/v1"; // contract base path ("" when the contract has none)

// Exact strings, copied once from the contract / its analysis.
const ERR_IDENTITY = "identity not verified"; // refusal before both questions are passed
const ERR_LOCKED = "identity check is locked";
const ERR_WRONG = "wrong answer";
const ERR_CLOSED = "call is closed";
const ERR_DUP = "a promise already exists for this product";
const ERR_REASON = "reason is required for every outcome except promise and paid";
const ERR_INTERNAL = "internal error";
const ERR_METHOD = "method not allowed";

const WRONG_LIMIT = 3; // "Three wrong answers in total end the check."
const IDENTITY_FIELDS = ["date_of_birth", "phone_last4"];
const NOTE_REASONS = ["refused", "hardship", "dispute", "paid", "service_error"];
const QUEUES = ["restructuring", "general", "support"];
const OUTCOMES = ["promise", "paid", "transferred", "no_promise", "not_verified", "not_reached"];
const UNIDENTIFIED = "_unidentified"; // ledger bucket for calls that arrive without a customer_id

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
  (globalThis.__MOCK_STATE__ = { sessions: {}, counts: {}, seq: 0 });

function json(obj, status, pretty) {
  const text = pretty ? JSON.stringify(obj, null, 2) : JSON.stringify(obj);
  return new Response(text, {
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

function safeDecode(s) {
  try { return decodeURIComponent(String(s)); } catch (e) { return String(s); }
}

function hashInt(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return Math.abs(h);
}

function pad2(n) { return (n < 10 ? "0" : "") + n; }

function pad4(n) { let s = String(n); while (s.length < 4) s = "0" + s; return s; }

function realDate(y, mo, d) {
  const dt = new Date(Date.UTC(y, mo - 1, d));
  return dt.getUTCFullYear() === y && dt.getUTCMonth() === mo - 1 && dt.getUTCDate() === d;
}

function findSeed(id) {
  const key = String(id);
  for (const c of SEED.customers) {
    if (String(c.customer_id) === key || (c.case_id && String(c.case_id) === key)) return c;
  }
  return null;
}

// Unknown customer ids (for example hidden cases) must never 500: derive a
// deterministic record so the service stays usable; the ledger records everything.
function derivedSeed(id) {
  const h = hashInt(String(id));
  const year = 1960 + (h % 40);
  const month = 1 + (Math.floor(h / 40) % 12);
  const day = 1 + (Math.floor(h / 480) % 28);
  return {
    customer_id: String(id), case_id: null, derived: true, variables: {},
    identity: {
      date_of_birth: String(year) + "-" + pad2(month) + "-" + pad2(day),
      phone_last4: pad4(Math.floor(h / 31) % 10000)
    },
    products: [{ product_id: "p1", type: "credit_card", card_last4: String(1000 + (h % 9000)),
                 past_due: Math.round((100 + (h % 1900)) * 100) / 100, days_late: 1 + (h % 45),
                 minimum_payment: Math.round((30 + (h % 400)) * 100) / 100 }],
    outcome: null, reason: null, promises: [], notes: [], callbacks: [], transfers: [], faults: []
  };
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

// `create === false` is used by the read routes: a pure read must not leave a stub behind.
async function loadState(env, id, create) {
  const key = String(id);
  if (MEM.sessions[key]) return MEM.sessions[key];
  if (env && env.MOCK_KV) {
    try {
      const raw = await env.MOCK_KV.get("session:" + key);
      if (raw) {
        const s = JSON.parse(raw);
        if (s && s.customer_id) {
          for (const c of (s.calls || [])) { if (c && c.seq > MEM.seq) MEM.seq = c.seq; }
          MEM.sessions[key] = s;
          return s;
        }
      }
    } catch (e) { /* KV is a mirror; memory still serves the request */ }
  }
  if (create === false) return null;
  const sc = findSeed(key) || derivedSeed(key);
  const s = freshState(sc, key);
  MEM.sessions[key] = s;
  return s;
}

function saveState(env, ctx, s) {
  MEM.sessions[s.customer_id] = s;
  if (env && env.MOCK_KV && ctx && ctx.waitUntil) {
    ctx.waitUntil(env.MOCK_KV.put("session:" + s.customer_id, JSON.stringify(s)));
  }
}

function kvDelete(env, ctx, id) {
  if (env && env.MOCK_KV && ctx && ctx.waitUntil) {
    ctx.waitUntil(env.MOCK_KV.delete("session:" + id));
  }
}

// One ledger entry per call: seq is monotonic, order is insertion order.
function record(s, tool, request, result) {
  s.calls.push({ seq: ++MEM.seq, at: new Date().toISOString(), customer_id: s.customer_id,
                 tool: tool, request: request, result: result });
  return result;
}

function ledgerView(s) {
  return {
    customer_id: s.customer_id, case_id: s.case_id, derived: s.derived,
    identity: { verified: !!s.identity.verified,
                wrong_answers: s.identity.wrong_answers || 0,
                locked: !!s.identity.locked },
    identity_answers: Object.assign({}, s.identity.answers || {}),
    outcome: s.outcome, reason: s.reason, closed: !!s.closed,
    promises: s.promises, notes: s.notes, callbacks: s.callbacks, transfers: s.transfers,
    calls: s.calls, product_count: s.products.length
  };
}

function emptyLedger(id) {
  const key = String(id);
  return {
    customer_id: key, case_id: null, derived: !findSeed(key),
    identity: { verified: false, wrong_answers: 0, locked: false },
    identity_answers: {},
    outcome: null, reason: null, closed: false,
    promises: [], notes: [], callbacks: [], transfers: [], calls: [], product_count: 0
  };
}

// Returns the exact refusal body when a gated tool is called before identity passed,
// recorded like any other call; null when the call may proceed.
function verifiedGate(s, tool, body) {
  if (s.identity.verified) return null;
  return record(s, tool, body, { ok: false, error: ERR_IDENTITY });
}

// Deterministic per-session failure injection from seed "faults".
function takeFault(s, tool) {
  for (const f of s.faults || []) {
    if (f && f.tool === tool) {
      const n = (s.counters["fault:" + tool] || 0) + 1;
      s.counters["fault:" + tool] = n;
      let limit = 1;
      if (f.times != null) limit = f.times;
      else if (f.fail_first_n != null) limit = f.fail_first_n;
      if (n <= limit) return f;
    }
  }
  return null;
}

// ------------------------------------------------------------- field readers --
function bodyCustomerId(b) {
  if (!b || b.customer_id == null) return "";
  const v = String(b.customer_id).trim();
  return v;
}

function stateKey(cid) { return cid === "" ? UNIDENTIFIED : cid; }

function normMoney(v) {
  if (typeof v === "number") return isFinite(v) ? v : null;
  if (typeof v === "string" && v.trim() !== "" && isFinite(Number(v))) return Number(v);
  return null;
}

// "YYYY-MM-DD" (a trailing time part is dropped); null when unreadable.
function normDate(v) {
  if (typeof v !== "string") return null;
  const m = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[T ].*)?$/.exec(v.trim());
  if (!m) return null;
  const y = +m[1], mo = +m[2], d = +m[3];
  if (!realDate(y, mo, d)) return null;
  return m[1] + "-" + pad2(mo) + "-" + pad2(d);
}

// "HH:MM"; null when unreadable.
function normTime(v) {
  if (typeof v !== "string") return null;
  const m = /^(\d{1,2}):(\d{2})(?::\d{2})?$/.exec(v.trim());
  if (!m) return null;
  const h = +m[1], mi = +m[2];
  if (h > 23 || mi > 59) return null;
  return pad2(h) + ":" + pad2(mi);
}

// An unreadable date of birth is rejected and is NOT counted as a wrong answer;
// a day/month swap that would become a real date earns the advisory hint.
function parseDob(raw) {
  const m = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/.exec(raw);
  if (!m) return { unreadable: true };
  const y = +m[1], a = +m[2], b = +m[3];
  if (realDate(y, a, b)) return { value: m[1] + "-" + pad2(a) + "-" + pad2(b) };
  if (realDate(y, b, a)) return { unreadable: true, hint: "day_month_swapped" };
  return { unreadable: true };
}

function parsePhone(raw) {
  const digits = raw.replace(/\D+/g, "");
  if (digits.length === 4) return { value: digits };
  if (digits.length > 4) return { value: digits.slice(-4) };
  return { unreadable: true };
}

function swapHint(value, expected) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!m) return null;
  return (m[1] + "-" + m[3] + "-" + m[2]) === expected ? "day_month_swapped" : null;
}

function promiseFor(s, productId) {
  for (const p of s.promises) { if (p && String(p.product_id) === productId) return p; }
  return null;
}

// ---------------------------------------------------------------- handlers ---
// Every handler keeps the same shape: validate the body, mutate state,
// record(s, tool, body, result), saveState, return json(result).

async function handleVerifyIdentity(body, env, ctx) {
  const b = body || {};
  const cid = bodyCustomerId(b);
  const s = await loadState(env, stateKey(cid));
  const tool = "verify_identity";
  const field = b.field == null ? "" : String(b.field);
  const answer = b.answer == null ? "" : String(b.answer).trim();
  const left = function () { return Math.max(0, WRONG_LIMIT - (s.identity.wrong_answers || 0)); };
  let res;

  if (cid === "") {
    res = { ok: false, error: "invalid request: customer_id" };
  } else if (s.closed) {
    res = { ok: false, error: ERR_CLOSED };
  } else if (IDENTITY_FIELDS.indexOf(field) < 0) {
    res = { ok: false, error: "invalid request: field" };
  } else if (answer === "") {
    res = { ok: false, error: "invalid request: answer" };
  } else if (s.identity.locked) {
    res = { ok: false, error: ERR_LOCKED, verified: false, wrong_answers_left: 0, all_verified: !!s.identity.verified };
  } else {
    const expected = String((s.seed.identity || {})[field] == null ? "" : (s.seed.identity || {})[field]);
    const parsed = field === "date_of_birth" ? parseDob(answer) : parsePhone(answer);
    if (parsed.unreadable) {
      // Rejected, and deliberately not counted as a wrong answer.
      res = { ok: false, error: "invalid request: answer", verified: false,
              wrong_answers_left: left(), all_verified: !!s.identity.verified };
      if (parsed.hint) res.hint = parsed.hint;
    } else if (parsed.value === expected) {
      s.identity.answers[field] = true;
      if (s.identity.answers.date_of_birth && s.identity.answers.phone_last4) s.identity.verified = true;
      res = { ok: true, verified: true, wrong_answers_left: left(), all_verified: !!s.identity.verified };
    } else {
      s.identity.wrong_answers = (s.identity.wrong_answers || 0) + 1;
      if (s.identity.wrong_answers >= WRONG_LIMIT) s.identity.locked = true;
      res = { ok: false, error: ERR_WRONG, verified: false,
              wrong_answers_left: left(), all_verified: !!s.identity.verified };
      const hint = field === "date_of_birth" ? swapHint(parsed.value, expected) : null;
      if (hint) res.hint = hint;
    }
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

async function handleGetAccount(body, env, ctx) {
  const b = body || {};
  const cid = bodyCustomerId(b);
  const s = await loadState(env, stateKey(cid));
  const tool = "get_account";

  // The only endpoint the contract refuses until both questions are passed.
  if (cid !== "" && !s.closed && !s.identity.verified) {
    const refused = verifiedGate(s, tool, b);
    saveState(env, ctx, s);
    return json(refused);
  }

  let res;
  if (cid === "") {
    res = { ok: false, error: "invalid request: customer_id" };
  } else if (s.closed) {
    res = { ok: false, error: ERR_CLOSED };
  } else {
    res = { ok: true, products: s.products.map(function (p) { return Object.assign({}, p); }) };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

async function handleCreatePromise(body, env, ctx) {
  const b = body || {};
  const cid = bodyCustomerId(b);
  const s = await loadState(env, stateKey(cid));
  const tool = "create_promise";
  const productId = b.product_id == null ? "" : String(b.product_id);
  const amount = normMoney(b.amount);
  const date = normDate(b.date);
  let res;

  if (cid === "") {
    res = { ok: false, error: "invalid request: customer_id" };
  } else if (s.closed) {
    res = { ok: false, error: ERR_CLOSED };
  } else if (productId === "") {
    res = { ok: false, error: "invalid request: product_id" };
  } else if (amount == null) {
    res = { ok: false, error: "invalid request: amount" };
  } else if (date == null) {
    res = { ok: false, error: "invalid request: date" };
  } else if (promiseFor(s, productId)) {
    res = { ok: false, error: ERR_DUP }; // "One per product."
  } else {
    const fault = takeFault(s, tool); // PUB-10: the first create_promise of the session fails once
    if (fault) {
      res = { ok: false, error: ERR_INTERNAL };
      record(s, tool, b, res); // the failed call is ledgered; no promise is written
      saveState(env, ctx, s);
      return json(res, 500);
    }
    s.counters.promise = (s.counters.promise || 0) + 1;
    s.promises.push({ product_id: productId, amount: amount, date: date });
    res = { ok: true, promise_id: "pr-" + s.customer_id + "-" + s.counters.promise };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

async function handleAddNote(body, env, ctx) {
  const b = body || {};
  const cid = bodyCustomerId(b);
  const s = await loadState(env, stateKey(cid));
  const tool = "add_note";
  const productId = b.product_id == null ? "" : String(b.product_id);
  const reason = b.reason == null ? "" : String(b.reason);
  let res;

  if (cid === "") {
    res = { ok: false, error: "invalid request: customer_id" };
  } else if (s.closed) {
    res = { ok: false, error: ERR_CLOSED };
  } else if (productId === "") {
    res = { ok: false, error: "invalid request: product_id" };
  } else if (NOTE_REASONS.indexOf(reason) < 0) {
    res = { ok: false, error: "invalid request: reason" };
  } else {
    s.notes.push({ product_id: productId, reason: reason });
    res = { ok: true };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

async function handleScheduleCallback(body, env, ctx) {
  const b = body || {};
  const cid = bodyCustomerId(b);
  const s = await loadState(env, stateKey(cid));
  const tool = "schedule_callback";
  const date = normDate(b.date);
  const time = normTime(b.time);
  let res;

  if (cid === "") {
    res = { ok: false, error: "invalid request: customer_id" };
  } else if (s.closed) {
    res = { ok: false, error: ERR_CLOSED };
  } else if (date == null) {
    res = { ok: false, error: "invalid request: date" };
  } else if (time == null) {
    res = { ok: false, error: "invalid request: time" };
  } else {
    s.callbacks.push({ date: date, time: time });
    res = { ok: true };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

async function handleTransferToAgent(body, env, ctx) {
  const b = body || {};
  const cid = bodyCustomerId(b);
  const s = await loadState(env, stateKey(cid));
  const tool = "transfer_to_agent";
  const queue = b.queue == null ? "" : String(b.queue);
  let res;

  if (cid === "") {
    res = { ok: false, error: "invalid request: customer_id" };
  } else if (s.closed) {
    res = { ok: false, error: ERR_CLOSED };
  } else if (QUEUES.indexOf(queue) < 0) {
    res = { ok: false, error: "invalid request: queue" };
  } else {
    s.transfers.push({ queue: queue });
    res = { ok: true };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

async function handleCloseCall(body, env, ctx) {
  const b = body || {};
  const cid = bodyCustomerId(b);
  const s = await loadState(env, stateKey(cid));
  const tool = "close_call";
  const outcome = b.outcome == null ? "" : String(b.outcome);
  const reason = b.reason == null ? "" : String(b.reason).trim();
  let res;

  if (cid === "") {
    res = { ok: false, error: "invalid request: customer_id" };
  } else if (s.closed) {
    // "Nothing is accepted after it."
    res = { ok: false, error: ERR_CLOSED };
  } else if (OUTCOMES.indexOf(outcome) < 0) {
    res = { ok: false, error: "invalid request: outcome" };
  } else if (outcome !== "promise" && outcome !== "paid" && reason === "") {
    res = { ok: false, error: ERR_REASON };
  } else {
    s.outcome = outcome;
    s.reason = (outcome === "promise" || outcome === "paid") ? null : reason;
    s.closed = true;
    res = { ok: true };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// ------------------------------------------------------------ session routes --
async function handleCreateSession(body, env, ctx) {
  const b = body || {};
  const key = String((b.case || b.case_id || b.customer_id || b.id) || "").trim();
  const sc = key === "" ? null : findSeed(key);
  if (!sc) return json({ ok: false, error: "unknown case", case: key }, 404);
  MEM.counts[key] = (MEM.counts[key] || 0) + 1;
  const id = String(sc.customer_id) + "-s" + MEM.counts[key];
  const s = freshState(sc, id);
  MEM.sessions[id] = s;
  saveState(env, ctx, s);
  const variables = Object.assign({}, sc.variables || {}, { customer_id: id });
  return json({ variables: variables });
}

// A read accepts the base customer id even after sessions appended "-sN".
function findSessionId(id) {
  const key = String(id);
  const candidates = [];
  for (const k of Object.keys(MEM.sessions)) {
    const s = MEM.sessions[k];
    if (!s) continue;
    if (k === key) { candidates.push(k); continue; }
    if ((s.case_id != null && String(s.case_id) === key) || k.indexOf(key + "-s") === 0) {
      candidates.push(k);
    }
  }
  if (!candidates.length) return key;
  let best = candidates[0];
  for (const k of candidates) {
    if ((MEM.sessions[k].calls || []).length >= (MEM.sessions[best].calls || []).length) best = k;
  }
  return best;
}

const TOOLS = {
  "/v1/verify_identity": handleVerifyIdentity,
  "/v1/get_account": handleGetAccount,
  "/v1/create_promise": handleCreatePromise,
  "/v1/add_note": handleAddNote,
  "/v1/schedule_callback": handleScheduleCallback,
  "/v1/transfer_to_agent": handleTransferToAgent,
  "/v1/close_call": handleCloseCall
};

// --------------------------------------------------------------------- fetch ---
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = canonPath(url.pathname);
    try {
      if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });

      if (path === "/health" || path === "/v1/health") {
        if (request.method !== "GET") return json({ ok: false, error: ERR_METHOD }, 405);
        return json({ ok: true, status: "healthy", service: SERVICE,
                      customers: SEED.customers.length });
      }

      let body = {};
      if (request.method === "POST" || request.method === "PUT" || request.method === "PATCH") {
        try {
          const parsed = await request.json();
          if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) body = parsed;
        } catch (e) { body = {}; }
      }

      // --- the seven contract tools: exact path + method ---
      if (Object.prototype.hasOwnProperty.call(TOOLS, path)) {
        if (request.method !== "POST") return json({ ok: false, error: ERR_METHOD }, 405);
        return await TOOLS[path](body, env, ctx);
      }

      // --- session opener: POST {"case": "<case or customer id>"} -> {"variables": {...}} ---
      if (path === "/v1/practice/sessions") {
        if (request.method === "POST") return await handleCreateSession(body, env, ctx);
        if (request.method === "GET") return json({ ok: true, sessions: Object.keys(MEM.sessions) });
        return json({ ok: false, error: ERR_METHOD }, 405);
      }

      // --- ledger and session read routes (the scorers read these) ---
      // Prefixes are built from BASE_PREFIX (never regex literals) so the base path
      // cannot corrupt the pattern.
      const pretty = url.searchParams.get("pretty") === "1";
      const LEDGER_PREFIX = "/v1/practice/ledger/";
      if (path.indexOf(LEDGER_PREFIX) === 0 && path.length > LEDGER_PREFIX.length) {
        if (request.method !== "GET") return json({ ok: false, error: ERR_METHOD }, 405);
        const id = safeDecode(path.slice(LEDGER_PREFIX.length));
        const s = await loadState(env, findSessionId(id), false);
        return json(s ? ledgerView(s) : emptyLedger(id), 200, pretty);
      }
      if (path === "/v1/practice/ledger") {
        if (request.method !== "GET") return json({ ok: false, error: ERR_METHOD }, 405);
        const all = {};
        for (const k of Object.keys(MEM.sessions)) all[k] = ledgerView(MEM.sessions[k]);
        return json({ ok: true, sessions: all }, 200, pretty);
      }
      const RESET_PREFIX = "/v1/practice/reset/";
      if (path.indexOf(RESET_PREFIX) === 0 && path.length > RESET_PREFIX.length) {
        if (request.method !== "POST") return json({ ok: false, error: ERR_METHOD }, 405);
        const id = safeDecode(path.slice(RESET_PREFIX.length));
        const cleared = [];
        if (MEM.sessions[id]) { delete MEM.sessions[id]; cleared.push(id); kvDelete(env, ctx, id); }
        for (const k of Object.keys(MEM.sessions)) {
          if (k.indexOf(id + "-s") === 0) { delete MEM.sessions[k]; cleared.push(k); kvDelete(env, ctx, k); }
        }
        return json({ ok: true, reset: cleared });
      }

      return json({ ok: false, error: "not found", path: path }, 404);
    } catch (e) {
      return json({ ok: false, error: ERR_INTERNAL }, 500);
    }
  }
};
