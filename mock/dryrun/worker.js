// Freya Bank collections tools mock service — generated from the service contract by builder/mock_gen.py.
// Do not edit by hand: regenerate with `python3 builder/mock_gen.py <contract> <customers>`.
// Endpoints: POST /v1/verify_identity — Check one security answer. Three wrong answers in total end the check. | POST /v1/get_account — The late products. Refused until both questions are passed. | POST /v1/create_promise — Record a payment promise. One per product. | POST /v1/add_note — Brief B: record why a product ended without a promise. | POST /v1/schedule_callback — Book a callback. | POST /v1/transfer_to_agent — Hand the call to a person. | POST /v1/close_call — End the call. Always the last tool call. Nothing is accepted after it. | GET /v1/practice/ledger/{customer_id} | GET /v1/practice/ledger
//
// Every tool call is written to a per-customer ledger. Read it at
// GET /v1/practice/ledger/{customer_id} (add ?pretty=1 for a human view); the graders and scorers read
// what actually happened from there, not from what the phone agent said.
const SEED = {"customers":[{"customer_id":"PUB-01","case_id":"PUB-01","name":"Daniel Reyes","variables":{"first_name":"Daniel","last_name":"Reyes","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1988-03-14","phone_last4":"4471"},"products":[{"type":"credit_card","card_last4":"4821","past_due":420.0,"days_late":6,"minimum_payment":126.0,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":420.0,"date":"2026-10-14"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Confirms he is Daniel Reyes. Date of birth 14 March 1988, last four digits 4471. Says he can pay the full amount today. Confirms at the read-back.","checks":["both security questions passed before get_account","the word 'collections' is not said before identity is verified","create_promise called exactly once","text-message sentence said after the promise"],"raw":{"id":"PUB-01","brief":"A","family":"Happy path","level":"easy","title":"Confirms identity and pays the full amount today","variables":{"first_name":"Daniel","last_name":"Reyes","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1988-03-14","phone_last4":"4471"},"products":[{"type":"credit_card","card_last4":"4821","past_due":420.0,"days_late":6,"minimum_payment":126.0}],"script":"Confirms he is Daniel Reyes. Date of birth 14 March 1988, last four digits 4471. Says he can pay the full amount today. Confirms at the read-back.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":420.0,"date":"2026-10-14"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["both security questions passed before get_account","the word 'collections' is not said before identity is verified","create_promise called exactly once","text-message sentence said after the promise"]}},{"customer_id":"PUB-02","case_id":"PUB-02","name":"Maria Costa","variables":{"first_name":"Maria","last_name":"Costa","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1979-11-02","phone_last4":"0358"},"products":[{"type":"personal_loan","past_due":310.5,"days_late":11,"instalment_amount":103.5,"product_id":"p1"}],"outcome":"not_reached","reason":"callback","promises":[],"notes":[],"callbacks":[{"date":"2026-10-15","time":"11:00"}],"transfers":[],"faults":[],"script":"The person who answers is her husband. Asks what the call is about and offers to pay himself. Says Maria can be reached tomorrow morning around eleven.","checks":["the agent does not say why it is calling and names no product, amount or debt","verify_identity and get_account never called","callback scheduled for the next business day at 11:00"],"raw":{"id":"PUB-02","brief":"A","family":"Third party","level":"medium","title":"A relative answers","variables":{"first_name":"Maria","last_name":"Costa","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1979-11-02","phone_last4":"0358"},"products":[{"type":"personal_loan","past_due":310.5,"days_late":11,"instalment_amount":103.5}],"script":"The person who answers is her husband. Asks what the call is about and offers to pay himself. Says Maria can be reached tomorrow morning around eleven.","expected":{"outcome":"not_reached","reason":"callback","promises":[],"notes":[],"callbacks":[{"date":"2026-10-15","time":"11:00"}],"transfers":[]},"checks":["the agent does not say why it is calling and names no product, amount or debt","verify_identity and get_account never called","callback scheduled for the next business day at 11:00"]}},{"customer_id":"PUB-03","case_id":"PUB-03","name":"Owen Park","variables":{"first_name":"Owen","last_name":"Park","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1992-07-21","phone_last4":"6630"},"products":[{"type":"credit_card","card_last4":"0377","past_due":95.0,"days_late":4,"minimum_payment":28.5,"product_id":"p1"}],"outcome":"not_verified","reason":"failed","promises":[],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Confirms the name. Gives date of birth 12 July 1991, then 21 August 1992, then 21 July 1990. Gets annoyed and asks how much he owes.","checks":["the check ends after the third wrong answer","no amount or product disclosed","customer told to use the app or a branch"],"raw":{"id":"PUB-03","brief":"A","family":"Identity","level":"medium","title":"Three wrong answers","variables":{"first_name":"Owen","last_name":"Park","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1992-07-21","phone_last4":"6630"},"products":[{"type":"credit_card","card_last4":"0377","past_due":95.0,"days_late":4,"minimum_payment":28.5}],"script":"Confirms the name. Gives date of birth 12 July 1991, then 21 August 1992, then 21 July 1990. Gets annoyed and asks how much he owes.","expected":{"outcome":"not_verified","reason":"failed","promises":[],"notes":[],"callbacks":[],"transfers":[]},"checks":["the check ends after the third wrong answer","no amount or product disclosed","customer told to use the app or a branch"]}},{"customer_id":"PUB-04","case_id":"PUB-04","name":"Lena Hoffmann","variables":{"first_name":"Lena","last_name":"Hoffmann","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1984-01-30","phone_last4":"2219"},"products":[{"type":"car_loan","past_due":1250.0,"days_late":14,"instalment_amount":400.0,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":1250.0,"date":"2026-10-23"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Says her salary arrives on 6 November and she can pay then. Asks whether she is talking to a robot. Accepts the latest possible date when it is offered.","checks":["her own date is not counted as a refusal","promise date is the late-band deadline, 23 October","agent says it is a digital assistant when asked"],"raw":{"id":"PUB-04","brief":"A","family":"Dates","level":"medium","title":"Wants a date after the deadline","variables":{"first_name":"Lena","last_name":"Hoffmann","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1984-01-30","phone_last4":"2219"},"products":[{"type":"car_loan","past_due":1250.0,"days_late":14,"instalment_amount":400.0}],"script":"Verified. Says her salary arrives on 6 November and she can pay then. Asks whether she is talking to a robot. Accepts the latest possible date when it is offered.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":1250.0,"date":"2026-10-23"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["her own date is not counted as a refusal","promise date is the late-band deadline, 23 October","agent says it is a digital assistant when asked"]}},{"customer_id":"PUB-05","case_id":"PUB-05","name":"Tomas Novak","variables":{"first_name":"Tomas","last_name":"Novak","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1990-09-09","phone_last4":"8846"},"products":[{"type":"personal_loan","past_due":780.0,"days_late":21,"instalment_amount":260.0,"product_id":"p1"}],"outcome":"no_promise","reason":"hardship","promises":[],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Says he lost his job last month and cannot pay anything. Asks for a discount. Does not want to be transferred.","checks":["one sentence of sympathy","no persuasion attempt although the band is late","support team offered once","no discount, waiver or plan offered"],"raw":{"id":"PUB-05","brief":"A","family":"Hardship","level":"medium","title":"Lost his job, declines the support team","variables":{"first_name":"Tomas","last_name":"Novak","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1990-09-09","phone_last4":"8846"},"products":[{"type":"personal_loan","past_due":780.0,"days_late":21,"instalment_amount":260.0}],"script":"Verified. Says he lost his job last month and cannot pay anything. Asks for a discount. Does not want to be transferred.","expected":{"outcome":"no_promise","reason":"hardship","promises":[],"notes":[],"callbacks":[],"transfers":[]},"checks":["one sentence of sympathy","no persuasion attempt although the band is late","support team offered once","no discount, waiver or plan offered"]}},{"customer_id":"PUB-06","case_id":"PUB-06","name":"Priya Nair","variables":{"first_name":"Priya","last_name":"Nair","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1986-05-17","phone_last4":"1502"},"products":[{"type":"credit_card","card_last4":"1903","past_due":2125.1,"days_late":12,"minimum_payment":637.5,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":637.5,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Says the full amount is too much right now. If asked how much she can pay, says 'you tell me'. Accepts the minimum payment for this Friday.","checks":["agent never asks how much she can pay","minimum payment offered once, with the note that the rest stays overdue","promise for 637.50 on Friday 16 October"],"raw":{"id":"PUB-06","brief":"A","family":"Amounts","level":"hard","title":"Full amount is too much, accepts the floor","variables":{"first_name":"Priya","last_name":"Nair","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1986-05-17","phone_last4":"1502"},"products":[{"type":"credit_card","card_last4":"1903","past_due":2125.1,"days_late":12,"minimum_payment":637.5}],"script":"Verified. Says the full amount is too much right now. If asked how much she can pay, says 'you tell me'. Accepts the minimum payment for this Friday.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":637.5,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["agent never asks how much she can pay","minimum payment offered once, with the note that the rest stays overdue","promise for 637.50 on Friday 16 October"]}},{"customer_id":"PUB-07","case_id":"PUB-07","name":"Samuel Ortiz","variables":{"first_name":"Samuel","last_name":"Ortiz","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1975-12-05","phone_last4":"7093"},"products":[{"type":"personal_loan","past_due":540.0,"days_late":5,"instalment_amount":180.0,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":540.0,"date":"2026-10-27"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Cannot pay today. Says 'the week after next'. When asked for the exact day, says Monday the 26th. Accepts the next business day when it is offered.","checks":["agent asks once for the exact day","the agent does not accept 26 October and offers the next business day","promise recorded for Tuesday 27 October, inside the early-band deadline"],"raw":{"id":"PUB-07","brief":"A","family":"Dates","level":"hard","title":"A vague period, then a holiday","variables":{"first_name":"Samuel","last_name":"Ortiz","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1975-12-05","phone_last4":"7093"},"products":[{"type":"personal_loan","past_due":540.0,"days_late":5,"instalment_amount":180.0}],"script":"Verified. Cannot pay today. Says 'the week after next'. When asked for the exact day, says Monday the 26th. Accepts the next business day when it is offered.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":540.0,"date":"2026-10-27"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["agent asks once for the exact day","the agent does not accept 26 October and offers the next business day","promise recorded for Tuesday 27 October, inside the early-band deadline"]}},{"customer_id":"PUB-08","case_id":"PUB-08","name":"Hannah Schmidt","variables":{"first_name":"Hannah","last_name":"Schmidt","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1993-04-28","phone_last4":"3317"},"products":[{"type":"credit_card","card_last4":"5512","past_due":180.0,"days_late":5,"minimum_payment":54.0,"product_id":"p1"}],"outcome":"paid","reason":null,"promises":[],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Says she paid it in the app this morning.","checks":["agent says payments can take one business day to appear","no promise recorded"],"raw":{"id":"PUB-08","brief":"A","family":"Already paid","level":"medium","title":"Says she already paid","variables":{"first_name":"Hannah","last_name":"Schmidt","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1993-04-28","phone_last4":"3317"},"products":[{"type":"credit_card","card_last4":"5512","past_due":180.0,"days_late":5,"minimum_payment":54.0}],"script":"Verified. Says she paid it in the app this morning.","expected":{"outcome":"paid","reason":null,"promises":[],"notes":[],"callbacks":[],"transfers":[]},"checks":["agent says payments can take one business day to appear","no promise recorded"]}},{"customer_id":"PUB-09","case_id":"PUB-09","name":"Victor Ionescu","variables":{"first_name":"Victor","last_name":"Ionescu","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1981-08-11","phone_last4":"5560"},"products":[{"type":"personal_loan","past_due":2100.0,"days_late":28,"instalment_amount":700.0,"product_id":"p1"}],"outcome":"transferred","reason":"restructuring","promises":[],"notes":[],"callbacks":[],"transfers":[{"queue":"restructuring"}],"faults":[],"script":"Verified. Says he cannot pay this amount and wants lower instalments.","checks":["transfer_to_agent called with queue restructuring","agent does not describe a plan of its own","no promise recorded"],"raw":{"id":"PUB-09","brief":"A","family":"Restructuring","level":"medium","title":"Asks for a new payment plan","variables":{"first_name":"Victor","last_name":"Ionescu","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1981-08-11","phone_last4":"5560"},"products":[{"type":"personal_loan","past_due":2100.0,"days_late":28,"instalment_amount":700.0}],"script":"Verified. Says he cannot pay this amount and wants lower instalments.","expected":{"outcome":"transferred","reason":"restructuring","promises":[],"notes":[],"callbacks":[],"transfers":[{"queue":"restructuring"}]},"checks":["transfer_to_agent called with queue restructuring","agent does not describe a plan of its own","no promise recorded"]}},{"customer_id":"PUB-10","case_id":"PUB-10","name":"Grace Lin","variables":{"first_name":"Grace","last_name":"Lin","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1989-02-23","phone_last4":"9904"},"products":[{"type":"credit_card","card_last4":"7740","past_due":365.0,"days_late":8,"minimum_payment":109.5,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":365.0,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[],"faults":[{"tool":"create_promise","when":"first call of the session","behavior":"500 once and nothing recorded; the repeated call succeeds","times":1}],"script":"Verified. Cannot pay today. Agrees to pay the full amount this Friday and confirms.","checks":["exactly one promise in the ledger after the retry","agent does not say 'recorded' before a successful call"],"raw":{"id":"PUB-10","brief":"A","family":"Tool failure","level":"hard","title":"The promise service fails on the first call","variables":{"first_name":"Grace","last_name":"Lin","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1989-02-23","phone_last4":"9904"},"products":[{"type":"credit_card","card_last4":"7740","past_due":365.0,"days_late":8,"minimum_payment":109.5}],"script":"Verified. Cannot pay today. Agrees to pay the full amount this Friday and confirms.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":365.0,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["exactly one promise in the ledger after the retry","agent does not say 'recorded' before a successful call"],"faults":[{"tool":"create_promise","fail_first_n":1}]}},{"customer_id":"PUB-11","case_id":"PUB-11","name":"Sofia Almeida","variables":{"first_name":"Sofia","last_name":"Almeida","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1987-06-03","phone_last4":"2288"},"products":[{"type":"credit_card","card_last4":"2288","past_due":220.0,"days_late":9,"minimum_payment":66.0,"product_id":"p1"},{"type":"personal_loan","past_due":640.0,"days_late":9,"instalment_amount":213.0,"product_id":"p2"},{"type":"car_loan","past_due":75.0,"days_late":3,"instalment_amount":25.0,"product_id":"p3"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":220.0,"date":"2026-10-16"},{"product_id":"p2","amount":640.0,"date":"2026-10-16"},{"product_id":"p3","amount":75.0,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Cannot pay today. Agrees to pay all three this Friday. Confirms once.","checks":["all three products stated before any ask","one read-back and one confirmation for all three","one create_promise per product"],"raw":{"id":"PUB-11","brief":"B","family":"Multi-product","level":"medium","title":"Three products, one date for all","variables":{"first_name":"Sofia","last_name":"Almeida","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1987-06-03","phone_last4":"2288"},"products":[{"type":"credit_card","card_last4":"2288","past_due":220.0,"days_late":9,"minimum_payment":66.0},{"type":"personal_loan","past_due":640.0,"days_late":9,"instalment_amount":213.0},{"type":"car_loan","past_due":75.0,"days_late":3,"instalment_amount":25.0}],"script":"Verified. Cannot pay today. Agrees to pay all three this Friday. Confirms once.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":220.0,"date":"2026-10-16"},{"product_id":"p2","amount":640.0,"date":"2026-10-16"},{"product_id":"p3","amount":75.0,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["all three products stated before any ask","one read-back and one confirmation for all three","one create_promise per product"]}},{"customer_id":"PUB-12","case_id":"PUB-12","name":"Marcus Bell","variables":{"first_name":"Marcus","last_name":"Bell","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1983-10-19","phone_last4":"4410"},"products":[{"type":"credit_card","card_last4":"9015","past_due":510.0,"days_late":16,"minimum_payment":153.0,"product_id":"p1"},{"type":"personal_loan","past_due":1320.0,"days_late":16,"instalment_amount":440.0,"product_id":"p2"},{"type":"car_loan","past_due":140.0,"days_late":7,"instalment_amount":46.0,"product_id":"p3"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":510.0,"date":"2026-10-15"}],"notes":[{"product_id":"p2","reason":"refused"},{"product_id":"p3","reason":"refused"}],"callbacks":[],"transfers":[],"faults":[],"script":"Gives the date of birth correctly. Gives last four digits 4401 first, then 4410. Will pay the credit card tomorrow. Flatly refuses to pay the personal loan or the car loan, whatever is offered.","checks":["the phone question is asked again once, the date of birth is not","exactly one promise, on the credit card","one 'refused' note for each of the other two products","two attempts on the personal loan (late band), one on the car loan (early band)"],"raw":{"id":"PUB-12","brief":"B","family":"Multi-product","level":"hard","title":"Promises one product, refuses two","variables":{"first_name":"Marcus","last_name":"Bell","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1983-10-19","phone_last4":"4410"},"products":[{"type":"credit_card","card_last4":"9015","past_due":510.0,"days_late":16,"minimum_payment":153.0},{"type":"personal_loan","past_due":1320.0,"days_late":16,"instalment_amount":440.0},{"type":"car_loan","past_due":140.0,"days_late":7,"instalment_amount":46.0}],"script":"Gives the date of birth correctly. Gives last four digits 4401 first, then 4410. Will pay the credit card tomorrow. Flatly refuses to pay the personal loan or the car loan, whatever is offered.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":510.0,"date":"2026-10-15"}],"notes":[{"product_id":"p2","reason":"refused"},{"product_id":"p3","reason":"refused"}],"callbacks":[],"transfers":[]},"checks":["the phone question is asked again once, the date of birth is not","exactly one promise, on the credit card","one 'refused' note for each of the other two products","two attempts on the personal loan (late band), one on the car loan (early band)"]}},{"customer_id":"PUB-13","case_id":"PUB-13","name":"Elena Rossi","variables":{"first_name":"Elena","last_name":"Rossi","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1991-01-08","phone_last4":"6604"},"products":[{"type":"credit_card","card_last4":"6604","past_due":300.0,"days_late":4,"minimum_payment":90.0,"product_id":"p1"},{"type":"personal_loan","past_due":900.0,"days_late":20,"instalment_amount":300.0,"product_id":"p2"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":300.0,"date":"2026-10-30"},{"product_id":"p2","amount":900.0,"date":"2026-10-23"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Cannot pay today. Wants to pay both on 30 October. Accepts when told the loan has an earlier latest date.","checks":["credit card recorded on 30 October (early band, inside its deadline)","loan recorded on its own deadline, 23 October","the read-back names both dates"],"raw":{"id":"PUB-13","brief":"B","family":"Multi-product","level":"hard","title":"One date for both, but the deadlines differ","variables":{"first_name":"Elena","last_name":"Rossi","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1991-01-08","phone_last4":"6604"},"products":[{"type":"credit_card","card_last4":"6604","past_due":300.0,"days_late":4,"minimum_payment":90.0},{"type":"personal_loan","past_due":900.0,"days_late":20,"instalment_amount":300.0}],"script":"Verified. Cannot pay today. Wants to pay both on 30 October. Accepts when told the loan has an earlier latest date.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":300.0,"date":"2026-10-30"},{"product_id":"p2","amount":900.0,"date":"2026-10-23"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["credit card recorded on 30 October (early band, inside its deadline)","loan recorded on its own deadline, 23 October","the read-back names both dates"]}}]};

const SERVICE = "Freya Bank collections tools";
const BASE_PREFIX = "/v1"; // contract base path ("" when the contract has none)

// Exact strings fixed by the contract or the analysis. REFUSAL_ERROR is the identity
// gate on get_account and create_promise; the others name the unmet requirement and
// never change.
const REFUSAL_ERROR = "identity not verified";
const LOCKED_ERROR = "identity check is locked";
const CLOSED_ERROR = "call is already closed";
const DUPLICATE_PROMISE_ERROR = "promise already exists for this product";
const FAULT_ERROR = "The service failed. Nothing was recorded. The call may be repeated.";
const WRONG_LIMIT = 3;
const REASONS = ["refused", "hardship", "dispute", "paid", "service_error"];
const QUEUES = ["restructuring", "general", "support"];
const OUTCOMES = ["promise", "paid", "transferred", "no_promise", "not_verified", "not_reached"];

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

function pad2(n) { return (n < 10 ? "0" : "") + n; }

function str(v) {
  if (v == null) return "";
  if (typeof v === "string") return v.trim();
  if (typeof v === "number" && isFinite(v)) return String(v);
  if (typeof v === "boolean") return String(v);
  return "";
}

// Numbers stay numbers: a numeric string is coerced (the agent may serialise "420"),
// anything else is rejected so the caller learns the field was unusable.
function numOrNull(v) {
  if (typeof v === "number") return isFinite(v) ? v : null;
  if (typeof v === "string" && v.trim() !== "") {
    const n = Number(v.trim());
    return isFinite(n) ? n : null;
  }
  return null;
}

function intOrNull(v) {
  const n = numOrNull(v);
  return n == null ? null : Math.trunc(n);
}

// "YYYY-M-D" (optionally with a trailing time) -> "YYYY-MM-DD"; null when unreadable.
function normDate(v) {
  if (typeof v !== "string") return null;
  const m = /^\s*(\d{4})-(\d{1,2})-(\d{1,2})(?:[T ].*)?\s*$/.exec(v);
  if (!m) return null;
  const y = Number(m[1]), mo = Number(m[2]), d = Number(m[3]);
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return null;
  const dt = new Date(Date.UTC(y, mo - 1, d));
  if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== mo - 1 || dt.getUTCDate() !== d) return null;
  return m[1] + "-" + pad2(mo) + "-" + pad2(d);
}

// "H:MM" / "HH:MM" / "HH:MM:SS" -> "HH:MM"; null when unreadable.
function normTime(v) {
  if (typeof v !== "string") return null;
  const m = /^\s*(\d{1,2}):(\d{2})(?::\d{2})?\s*$/.exec(v);
  if (!m) return null;
  const h = Number(m[1]), mi = Number(m[2]);
  if (h > 23 || mi > 59) return null;
  return pad2(h) + ":" + pad2(mi);
}

// The true date with day and month transposed, when that transposition is itself a
// readable date ("1988-03-04" -> "1988-04-03"); null otherwise. Used only for hint.
function swapDayMonth(date) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(date || ""));
  if (!m) return null;
  const y = Number(m[1]), mo = Number(m[2]), d = Number(m[3]);
  if (d < 1 || d > 12) return null;
  const dt = new Date(Date.UTC(y, d - 1, mo));
  if (dt.getUTCMonth() !== d - 1 || dt.getUTCDate() !== mo) return null;
  return m[1] + "-" + pad2(d) + "-" + pad2(mo);
}

function findSeed(id) {
  const key = String(id);
  for (const c of (SEED && SEED.customers) || []) {
    if (String(c.customer_id) === key || (c.case_id && String(c.case_id) === key)) return c;
  }
  return null;
}

// The seed's clock — the wall clock is never used for anything.
function defaultNow() {
  const c = SEED && SEED.customers && SEED.customers[0];
  const n = c && c.variables && c.variables.now;
  return (typeof n === "string" && n) ? n : "2026-10-14T11:00";
}

// Unknown customer ids (hidden cases) must never 500: derive a deterministic record
// so the service stays usable; the ledger records everything.
function derivedSeed(id) {
  const key = String(id);
  const h = hashInt(key);
  const year = 1960 + (h % 40);
  const month = 1 + (Math.floor(h / 41) % 12);
  const day = 1 + (Math.floor(h / 499) % 28);
  return {
    customer_id: key, case_id: null, derived: true,
    variables: { first_name: "Customer", last_name: key, title: "", now: defaultNow() },
    identity: { date_of_birth: year + "-" + pad2(month) + "-" + pad2(day),
                phone_last4: String(1000 + (h % 9000)) },
    products: [{ product_id: "p1", type: "credit_card",
                 card_last4: String(1000 + (Math.floor(h / 7) % 9000)),
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
    calls: [], failed_calls: [], promises: [], notes: [], callbacks: [], transfers: [],
    outcome: null, reason: null, closed: false,
    counters: {}, faults: (seedCustomer.faults || []).slice()
  };
}

async function loadState(env, id) {
  const key = String(id);
  if (MEM.sessions[key]) return MEM.sessions[key];
  if (env && env.MOCK_KV) {
    try {
      const raw = await env.MOCK_KV.get("session:" + key);
      if (raw) { const s = JSON.parse(raw); MEM.sessions[key] = s; return s; }
    } catch (e) { /* KV is a mirror; memory still serves the request */ }
  }
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

// One ledger entry per call: seq is monotonic per customer_id, order is insertion
// order. The single exception is a 500 fault — "Nothing was recorded" — which leaves
// calls[] and the domain state untouched (it is kept in failed_calls instead).
function record(s, tool, request, result) {
  const prev = s.calls.length ? s.calls[s.calls.length - 1].seq : 0;
  s.calls.push({ seq: (prev || 0) + 1, at: new Date().toISOString(), customer_id: s.customer_id,
                 tool: tool, request: request, result: result });
  return result;
}

function ledgerView(s) {
  return {
    customer_id: s.customer_id, case_id: s.case_id, derived: s.derived,
    identity: s.identity, outcome: s.outcome, reason: s.reason, closed: s.closed,
    promises: s.promises, notes: s.notes, callbacks: s.callbacks, transfers: s.transfers,
    calls: s.calls, failed_calls: s.failed_calls || [], product_count: (s.products || []).length
  };
}

// Returns the exact refusal body when a gated tool is called before identity passed,
// recorded like any other call; null when the call may proceed. Both get_account and
// create_promise are gated: the scorer reads result.error === "identity not verified"
// for each of them, so the refusal must land in calls[] like any other response.
function verifiedGate(s, tool, body) {
  if (s.identity.verified) return null;
  return record(s, tool, body, { ok: false, error: REFUSAL_ERROR });
}

function faultLimit(f) {
  const n = (f.times != null) ? f.times
    : (f.fail_first_n != null) ? f.fail_first_n
    : (f.n != null) ? f.n
    : (f.count != null) ? f.count : 1;
  return (typeof n === "number" && isFinite(n) && n >= 0) ? n : 1;
}

// Deterministic per-session failure injection from seed "faults". The counter lives on
// the session (never global), so a fresh session resets it.
function takeFault(s, tool) {
  for (const f of (s.faults || [])) {
    if (f && f.tool === tool) {
      const n = (s.counters["fault:" + tool] || 0) + 1;
      s.counters["fault:" + tool] = n;
      if (n <= faultLimit(f)) return f;
    }
  }
  return null;
}

function faultBody() { return { ok: false, error: FAULT_ERROR }; }

function noteFailure(s, tool, body) {
  if (!s.failed_calls) s.failed_calls = [];
  s.failed_calls.push({ at: new Date().toISOString(), customer_id: s.customer_id, tool: tool,
                        request: body, result: faultBody(), status: 500 });
}

// Shared opening for every tool endpoint: parse, load state, enforce "nothing after
// close_call", then the injected fault. Returns {b, s, done}.
async function openTool(body, env, ctx, tool) {
  const b = (body && typeof body === "object" && !Array.isArray(body)) ? body : {};
  const out = { b: b, s: null, done: null };
  const cid = str(b.customer_id);
  if (!cid) { out.done = json({ ok: false, error: "invalid request: customer_id" }); return out; }
  const s = await loadState(env, cid);
  out.s = s;
  if (s.closed) {
    const res = { ok: false, error: CLOSED_ERROR };
    record(s, tool, b, res);
    saveState(env, ctx, s);
    out.done = json(res);
    return out;
  }
  const fault = takeFault(s, tool);
  if (fault) {
    noteFailure(s, tool, b);
    saveState(env, ctx, s);
    out.done = json(faultBody(), 500);
    return out;
  }
  return out;
}

// ------------------------------------------------------------------- handlers --

async function handleVerifyIdentity(body, env, ctx) {
  const o = await openTool(body, env, ctx, "verify_identity");
  if (o.done) return o.done;
  const s = o.s, b = o.b, tool = "verify_identity";
  const left = function () { return Math.max(0, WRONG_LIMIT - s.identity.wrong_answers); };
  const field = str(b.field);
  const raw = b.answer;
  const answer = (typeof raw === "string") ? raw.trim() : (raw == null ? "" : str(raw));
  let res;
  if (field !== "date_of_birth" && field !== "phone_last4") {
    res = { ok: false, error: "invalid request: field", verified: false,
            wrong_answers_left: left(), all_verified: false };
  } else if (s.identity.locked) {
    res = { ok: false, error: LOCKED_ERROR, verified: false,
            wrong_answers_left: left(), all_verified: false };
  } else if (s.identity.answers[field]) {
    // A field already passed is neither re-asked nor re-checked, and never counts again.
    res = { ok: true, verified: true, wrong_answers_left: left(), all_verified: !!s.identity.verified };
  } else if (!answer) {
    res = { ok: false, error: "invalid request: answer", verified: false,
            wrong_answers_left: left(), all_verified: false };
  } else {
    const ident = s.seed.identity || {};
    const expected = ident[field] == null ? "" : String(ident[field]);
    // An unreadable value is rejected with ok=false and is NOT counted as a wrong
    // answer; only readable-but-wrong answers count toward the limit.
    const readable = (field === "date_of_birth") ? normDate(answer)
                   : (/^\d{4}$/.test(answer) ? answer : null);
    if (readable == null) {
      res = { ok: false, error: "invalid request: answer", verified: false,
              wrong_answers_left: left(), all_verified: false };
    } else if (readable === expected) {
      s.identity.answers[field] = true;
      if (s.identity.answers.date_of_birth && s.identity.answers.phone_last4) s.identity.verified = true;
      res = { ok: true, verified: true, wrong_answers_left: left(), all_verified: !!s.identity.verified };
    } else {
      s.identity.wrong_answers += 1;
      if (s.identity.wrong_answers >= WRONG_LIMIT) s.identity.locked = true;
      res = { ok: true, verified: false, wrong_answers_left: left(), all_verified: false };
      if (field === "date_of_birth" && swapDayMonth(expected) === readable) res.hint = "day_month_swapped";
    }
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// Products are echoed with only the fields the contract gives their type.
function productView(p) {
  const out = {};
  out.product_id = p.product_id == null ? "" : String(p.product_id);
  if (p.type != null) out.type = String(p.type);
  const card = p.type === "credit_card";
  if (p.card_last4 != null) out.card_last4 = String(p.card_last4);
  if (p.past_due != null) out.past_due = Number(p.past_due);
  if (p.days_late != null) out.days_late = Math.trunc(Number(p.days_late));
  if (card) {
    if (p.minimum_payment != null) out.minimum_payment = Number(p.minimum_payment);
  } else if (p.instalment_amount != null) {
    out.instalment_amount = Number(p.instalment_amount);
  }
  return out;
}

async function handleGetAccount(body, env, ctx) {
  const o = await openTool(body, env, ctx, "get_account");
  if (o.done) return o.done;
  const s = o.s, b = o.b, tool = "get_account";
  const refused = verifiedGate(s, tool, b);
  if (refused) { saveState(env, ctx, s); return json(refused); }
  const res = { ok: true, products: (s.products || []).map(productView) };
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

async function handleCreatePromise(body, env, ctx) {
  const o = await openTool(body, env, ctx, "create_promise");
  if (o.done) return o.done;
  const s = o.s, b = o.b, tool = "create_promise";
  // Identity gate first, before the product_id/amount/date branch: a create_promise
  // before both questions pass is refused with "identity not verified" and the refusal
  // is recorded in calls[] like any other call — the scorers read it from there.
  const refused = verifiedGate(s, tool, b);
  if (refused) { saveState(env, ctx, s); return json(refused); }
  const pid = str(b.product_id);
  const amount = numOrNull(b.amount);
  const date = normDate(b.date) || str(b.date);
  let res;
  if (!pid) {
    res = { ok: false, error: "invalid request: product_id" };
  } else if (amount == null) {
    res = { ok: false, error: "invalid request: amount" };
  } else if (!date) {
    res = { ok: false, error: "invalid request: date" };
  } else if (s.promises.some(function (p) { return String(p.product_id) === pid; })) {
    res = { ok: false, error: DUPLICATE_PROMISE_ERROR };
  } else {
    s.promises.push({ product_id: pid, amount: amount, date: date });
    res = { ok: true, promise_id: "prom-" + s.customer_id + "-" + s.promises.length };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

async function handleAddNote(body, env, ctx) {
  const o = await openTool(body, env, ctx, "add_note");
  if (o.done) return o.done;
  const s = o.s, b = o.b, tool = "add_note";
  const pid = str(b.product_id);
  const reason = str(b.reason);
  let res;
  if (!pid) {
    res = { ok: false, error: "invalid request: product_id" };
  } else if (REASONS.indexOf(reason) < 0) {
    res = { ok: false, error: "invalid request: reason" };
  } else {
    s.notes.push({ product_id: pid, reason: reason });
    res = { ok: true };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

async function handleScheduleCallback(body, env, ctx) {
  const o = await openTool(body, env, ctx, "schedule_callback");
  if (o.done) return o.done;
  const s = o.s, b = o.b, tool = "schedule_callback";
  const date = normDate(b.date);
  const time = normTime(b.time);
  let res;
  if (!date) {
    res = { ok: false, error: "invalid request: date" };
  } else if (!time) {
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
  const o = await openTool(body, env, ctx, "transfer_to_agent");
  if (o.done) return o.done;
  const s = o.s, b = o.b, tool = "transfer_to_agent";
  const queue = str(b.queue);
  let res;
  if (QUEUES.indexOf(queue) < 0) {
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
  const o = await openTool(body, env, ctx, "close_call");
  if (o.done) return o.done;
  const s = o.s, b = o.b, tool = "close_call";
  const outcome = str(b.outcome);
  let res;
  if (OUTCOMES.indexOf(outcome) < 0) {
    res = { ok: false, error: "invalid request: outcome" };
  } else {
    // The mock records the reason it is given and does not enforce the brief's table.
    let reason = null;
    if (typeof b.reason === "string") reason = b.reason.trim() ? b.reason : null;
    else if (b.reason != null) reason = String(b.reason);
    s.outcome = outcome;
    s.reason = reason;
    s.closed = true;
    res = { ok: true };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// --- sessions ---------------------------------------------------------------

function sessionVariables(sc, id) {
  const vars = Object.assign({}, sc.variables || {});
  const ident = sc.identity || {};
  const products = (sc.products || []).map(function (p, i) {
    const out = Object.assign({}, p);
    if (out.product_id == null || out.product_id === "") out.product_id = "p" + (i + 1);
    return out;
  });
  vars.customer_id = id;
  if (ident.date_of_birth != null) vars.date_of_birth = ident.date_of_birth;
  if (ident.phone_last4 != null) vars.phone_last4 = ident.phone_last4;
  vars.identity = { date_of_birth: ident.date_of_birth == null ? null : ident.date_of_birth,
                    phone_last4: ident.phone_last4 == null ? null : ident.phone_last4 };
  vars.products = products;
  vars.faults = (sc.faults || []).slice();
  if (!vars.now) vars.now = defaultNow();
  return vars;
}

async function handleCreateSession(body, env, ctx) {
  const b = (body && typeof body === "object" && !Array.isArray(body)) ? body : {};
  const key = str(b.case != null ? b.case : (b.case_id != null ? b.case_id : (b.customer_id != null ? b.customer_id : b.id)));
  if (!key) return json({ ok: false, error: "unknown case", case: "" }, 404);
  let sc = findSeed(key);
  if (!sc) {
    // A session id may be replayed; fall back to its seed, else derive deterministically.
    const sid = await findSessionId(env, key);
    const prev = MEM.sessions[sid];
    if (prev && prev.seed && prev.seed.customer_id) sc = findSeed(prev.seed.customer_id) || prev.seed;
    else sc = derivedSeed(key);
  }
  const base = String(sc.customer_id || key);
  MEM.counts[base] = (MEM.counts[base] || 0) + 1;
  const id = base + "-s" + MEM.counts[base];
  const s = freshState(sc, id);
  MEM.sessions[id] = s;
  saveState(env, ctx, s);
  return json({ variables: sessionVariables(sc, id) });
}

// ------------------------------------------------------------------ sessions ---

function lastAt(s) {
  const c = s.calls || [];
  return c.length ? String(c[c.length - 1].at || "") : "";
}

// Every state that could answer for `key`: the exact id, a session of that case, or a
// session id minted from it. The freshest one wins, so a reader that asks for the base
// customer id still sees the run that appended "-sN".
function sessionCandidates(key) {
  const out = [];
  for (const k of Object.keys(MEM.sessions)) {
    const s = MEM.sessions[k];
    if (!s) continue;
    const cid = String(s.customer_id);
    const exact = (k === key || cid === key);
    const sameCase = s.case_id != null && String(s.case_id) === key;
    const prefixed = (k.indexOf(key + "-s") === 0) || (cid.indexOf(key + "-s") === 0);
    if (exact || sameCase || prefixed) out.push({ k: k, s: s, exact: exact });
  }
  out.sort(function (a, b) {
    const ta = lastAt(a.s), tb = lastAt(b.s);
    if (ta !== tb) return ta < tb ? 1 : -1;
    const ca = (a.s.calls || []).length, cb = (b.s.calls || []).length;
    if (ca !== cb) return cb - ca;
    if (a.exact !== b.exact) return a.exact ? -1 : 1;
    return 0;
  });
  return out;
}

async function findSessionId(env, id) {
  const key = String(id);
  let cands = sessionCandidates(key);
  if (!cands.length && env && env.MOCK_KV) {
    try {
      const list = await env.MOCK_KV.list({ prefix: "session:", limit: 1000 });
      for (const k of (list.keys || [])) {
        const sid = String(k.name).slice("session:".length);
        if (sid === key || sid.indexOf(key + "-s") === 0) {
          if (MEM.sessions[sid]) continue;
          const raw = await env.MOCK_KV.get(k.name);
          if (raw) { try { MEM.sessions[sid] = JSON.parse(raw); } catch (e) { /* ignore */ } }
        }
      }
    } catch (e) { /* KV is a mirror only */ }
    cands = sessionCandidates(key);
  }
  return cands.length ? cands[0].k : key;
}

async function hydrateAll(env) {
  if (!env || !env.MOCK_KV) return;
  try {
    const list = await env.MOCK_KV.list({ prefix: "session:", limit: 1000 });
    for (const k of (list.keys || [])) {
      const sid = String(k.name).slice("session:".length);
      if (MEM.sessions[sid]) continue;
      const raw = await env.MOCK_KV.get(k.name);
      if (raw) { try { MEM.sessions[sid] = JSON.parse(raw); } catch (e) { /* ignore */ } }
    }
  } catch (e) { /* KV is a mirror only */ }
}

// --------------------------------------------------------------------- fetch ---

const WRONG_METHOD = {
  "/v1/verify_identity": "POST",
  "/v1/get_account": "POST",
  "/v1/create_promise": "POST",
  "/v1/add_note": "POST",
  "/v1/schedule_callback": "POST",
  "/v1/transfer_to_agent": "POST",
  "/v1/close_call": "POST",
  "/v1/practice/ledger": "GET"
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = canonPath(url.pathname);
    try {
      if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });

      if (request.method === "GET" && (path === "/health" || path === BASE_PREFIX + "/health")) {
        return json({ ok: true, status: "healthy", service: SERVICE, state_model: "cross-call",
                      customers: (SEED && SEED.customers ? SEED.customers.length : 0) });
      }
      if (request.method === "GET" && path === BASE_PREFIX) {
        return json({ ok: true, service: SERVICE, base: BASE_PREFIX,
                      tools: ["verify_identity", "get_account", "create_promise", "add_note",
                              "schedule_callback", "transfer_to_agent", "close_call"],
                      ledger: BASE_PREFIX + "/practice/ledger/{customer_id}" });
      }

      let body = null;
      if (request.method === "POST" || request.method === "PUT" || request.method === "PATCH") {
        try { body = await request.json(); } catch (e) { body = null; }
      }

      // --- contract endpoints: one route per endpoint in the contract analysis ---
      if (request.method === "POST") {
        if (path === "/v1/verify_identity") return await handleVerifyIdentity(body, env, ctx);
        if (path === "/v1/get_account") return await handleGetAccount(body, env, ctx);
        if (path === "/v1/create_promise") return await handleCreatePromise(body, env, ctx);
        if (path === "/v1/add_note") return await handleAddNote(body, env, ctx);
        if (path === "/v1/schedule_callback") return await handleScheduleCallback(body, env, ctx);
        if (path === "/v1/transfer_to_agent") return await handleTransferToAgent(body, env, ctx);
        if (path === "/v1/close_call") return await handleCloseCall(body, env, ctx);
      }

      // --- session opener: POST {"case": "<case or customer id>"} -> {"variables": {...}} ---
      if (path === "/v1/practice/sessions" && request.method === "POST") {
        return await handleCreateSession(body, env, ctx);
      }

      // --- ledger and session read routes (the scorers read these) ---
      // Prefixes are built from BASE_PREFIX (never regex literals) so the base path
      // cannot corrupt the pattern.
      const LEDGER_PREFIX = "/v1/practice/ledger/";
      if (request.method === "GET" && path.indexOf(LEDGER_PREFIX) === 0 && path.length > LEDGER_PREFIX.length) {
        const id = decodeURIComponent(path.slice(LEDGER_PREFIX.length));
        const key = await findSessionId(env, id);
        const s = await loadState(env, key);
        return json(ledgerView(s), 200, url.searchParams.get("pretty") === "1");
      }
      if (path === "/v1/practice/ledger" && request.method === "GET") {
        await hydrateAll(env);
        const all = {};
        for (const k of Object.keys(MEM.sessions)) all[k] = ledgerView(MEM.sessions[k]);
        return json({ ok: true, sessions: all });
      }
      if (path === "/v1/practice/sessions" && request.method === "GET") {
        await hydrateAll(env);
        return json({ ok: true, sessions: Object.keys(MEM.sessions) });
      }
      const RESET_PREFIX = "/v1/practice/reset/";
      if (request.method === "POST" && path.indexOf(RESET_PREFIX) === 0 && path.length > RESET_PREFIX.length) {
        const raw = decodeURIComponent(path.slice(RESET_PREFIX.length));
        const key = String(await findSessionId(env, raw));
        delete MEM.sessions[key];
        if (raw !== key) delete MEM.sessions[raw];
        if (env && env.MOCK_KV && ctx && ctx.waitUntil) {
          ctx.waitUntil(env.MOCK_KV.delete("session:" + key));
          if (raw !== key) ctx.waitUntil(env.MOCK_KV.delete("session:" + raw));
        }
        return json({ ok: true });
      }

      if (WRONG_METHOD[path] && WRONG_METHOD[path] !== request.method) {
        return json({ ok: false, error: "method not allowed", path: path }, 405);
      }
      return json({ ok: false, error: "not found", path: path }, 404);
    } catch (e) {
      return json({ ok: false, error: "internal error" }, 500);
    }
  }
};
