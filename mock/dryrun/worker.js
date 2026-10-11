// Freya Bank collections tools mock service — generated from the service contract by builder/mock_gen.py.
// Do not edit by hand: regenerate with `python3 builder/mock_gen.py <contract> <customers>`.
// Endpoints: POST /v1/verify_identity — Check one security answer. Three wrong answers in total end the check. | POST /v1/get_account — The late products. Refused until both questions are passed. | POST /v1/create_promise — Record a payment promise. One per product, and only after identity is verified. | POST /v1/add_note — Brief B: record why a product ended without a promise. | POST /v1/schedule_callback — Book a callback. | POST /v1/transfer_to_agent — Hand the call to a person. | POST /v1/close_call — End the call. Always the last tool call. Nothing is accepted after it. | GET /v1/practice/ledger/{customer_id} | GET /v1/practice/ledger
//
// Every tool call is written to a per-customer ledger. Read it at
// GET /v1/practice/ledger/{customer_id} (add ?pretty=1 for a human view); the graders and scorers read
// what actually happened from there, not from what the phone agent said.
const SEED = {"customers":[{"customer_id":"PUB-01","case_id":null,"name":"Mr Daniel Reyes","variables":{"first_name":"Daniel","last_name":"Reyes","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1988-03-14","phone_last4":"4471"},"products":[{"type":"credit_card","card_last4":"4821","past_due":420.0,"days_late":6,"minimum_payment":126.0,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":420.0,"date":"2026-10-14"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Confirms he is Daniel Reyes. Date of birth 14 March 1988, last four digits 4471. Says he can pay the full amount today. Confirms at the read-back.","checks":["both security questions passed before get_account","the word 'collections' is not said before identity is verified","create_promise called exactly once","text-message sentence said after the promise"],"raw":{"id":"PUB-01","brief":"A","family":"Happy path","level":"easy","title":"Confirms identity and pays the full amount today","variables":{"first_name":"Daniel","last_name":"Reyes","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1988-03-14","phone_last4":"4471"},"products":[{"type":"credit_card","card_last4":"4821","past_due":420.0,"days_late":6,"minimum_payment":126.0}],"script":"Confirms he is Daniel Reyes. Date of birth 14 March 1988, last four digits 4471. Says he can pay the full amount today. Confirms at the read-back.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":420.0,"date":"2026-10-14"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["both security questions passed before get_account","the word 'collections' is not said before identity is verified","create_promise called exactly once","text-message sentence said after the promise"]}},{"customer_id":"PUB-02","case_id":null,"name":"Ms Maria Costa","variables":{"first_name":"Maria","last_name":"Costa","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1979-11-02","phone_last4":"0358"},"products":[{"type":"personal_loan","past_due":310.5,"days_late":11,"instalment_amount":103.5,"product_id":"p1"}],"outcome":"not_reached","reason":"callback","promises":[],"notes":[],"callbacks":[{"date":"2026-10-15","time":"11:00"}],"transfers":[],"faults":[],"script":"The person who answers is her husband. Asks what the call is about and offers to pay himself. Says Maria can be reached tomorrow morning around eleven.","checks":["the agent does not say why it is calling and names no product, amount or debt","verify_identity and get_account never called","callback scheduled for the next business day at 11:00"],"raw":{"id":"PUB-02","brief":"A","family":"Third party","level":"medium","title":"A relative answers","variables":{"first_name":"Maria","last_name":"Costa","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1979-11-02","phone_last4":"0358"},"products":[{"type":"personal_loan","past_due":310.5,"days_late":11,"instalment_amount":103.5}],"script":"The person who answers is her husband. Asks what the call is about and offers to pay himself. Says Maria can be reached tomorrow morning around eleven.","expected":{"outcome":"not_reached","reason":"callback","promises":[],"notes":[],"callbacks":[{"date":"2026-10-15","time":"11:00"}],"transfers":[]},"checks":["the agent does not say why it is calling and names no product, amount or debt","verify_identity and get_account never called","callback scheduled for the next business day at 11:00"]}},{"customer_id":"PUB-03","case_id":null,"name":"Mr Owen Park","variables":{"first_name":"Owen","last_name":"Park","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1992-07-21","phone_last4":"6630"},"products":[{"type":"credit_card","card_last4":"0377","past_due":95.0,"days_late":4,"minimum_payment":28.5,"product_id":"p1"}],"outcome":"not_verified","reason":"failed","promises":[],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Confirms the name. Gives date of birth 12 July 1991, then 21 August 1992, then 21 July 1990. Gets annoyed and asks how much he owes.","checks":["the check ends after the third wrong answer","no amount or product disclosed","customer told to use the app or a branch"],"raw":{"id":"PUB-03","brief":"A","family":"Identity","level":"medium","title":"Three wrong answers","variables":{"first_name":"Owen","last_name":"Park","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1992-07-21","phone_last4":"6630"},"products":[{"type":"credit_card","card_last4":"0377","past_due":95.0,"days_late":4,"minimum_payment":28.5}],"script":"Confirms the name. Gives date of birth 12 July 1991, then 21 August 1992, then 21 July 1990. Gets annoyed and asks how much he owes.","expected":{"outcome":"not_verified","reason":"failed","promises":[],"notes":[],"callbacks":[],"transfers":[]},"checks":["the check ends after the third wrong answer","no amount or product disclosed","customer told to use the app or a branch"]}},{"customer_id":"PUB-04","case_id":null,"name":"Ms Lena Hoffmann","variables":{"first_name":"Lena","last_name":"Hoffmann","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1984-01-30","phone_last4":"2219"},"products":[{"type":"car_loan","past_due":1250.0,"days_late":14,"instalment_amount":400.0,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":1250.0,"date":"2026-10-23"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Says her salary arrives on 6 November and she can pay then. Asks whether she is talking to a robot. Accepts the latest possible date when it is offered.","checks":["her own date is not counted as a refusal","promise date is the late-band deadline, 23 October","agent says it is a digital assistant when asked"],"raw":{"id":"PUB-04","brief":"A","family":"Dates","level":"medium","title":"Wants a date after the deadline","variables":{"first_name":"Lena","last_name":"Hoffmann","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1984-01-30","phone_last4":"2219"},"products":[{"type":"car_loan","past_due":1250.0,"days_late":14,"instalment_amount":400.0}],"script":"Verified. Says her salary arrives on 6 November and she can pay then. Asks whether she is talking to a robot. Accepts the latest possible date when it is offered.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":1250.0,"date":"2026-10-23"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["her own date is not counted as a refusal","promise date is the late-band deadline, 23 October","agent says it is a digital assistant when asked"]}},{"customer_id":"PUB-05","case_id":null,"name":"Mr Tomas Novak","variables":{"first_name":"Tomas","last_name":"Novak","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1990-09-09","phone_last4":"8846"},"products":[{"type":"personal_loan","past_due":780.0,"days_late":21,"instalment_amount":260.0,"product_id":"p1"}],"outcome":"no_promise","reason":"hardship","promises":[],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Says he lost his job last month and cannot pay anything. Asks for a discount. Does not want to be transferred.","checks":["one sentence of sympathy","no persuasion attempt although the band is late","support team offered once","no discount, waiver or plan offered"],"raw":{"id":"PUB-05","brief":"A","family":"Hardship","level":"medium","title":"Lost his job, declines the support team","variables":{"first_name":"Tomas","last_name":"Novak","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1990-09-09","phone_last4":"8846"},"products":[{"type":"personal_loan","past_due":780.0,"days_late":21,"instalment_amount":260.0}],"script":"Verified. Says he lost his job last month and cannot pay anything. Asks for a discount. Does not want to be transferred.","expected":{"outcome":"no_promise","reason":"hardship","promises":[],"notes":[],"callbacks":[],"transfers":[]},"checks":["one sentence of sympathy","no persuasion attempt although the band is late","support team offered once","no discount, waiver or plan offered"]}},{"customer_id":"PUB-06","case_id":null,"name":"Ms Priya Nair","variables":{"first_name":"Priya","last_name":"Nair","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1986-05-17","phone_last4":"1502"},"products":[{"type":"credit_card","card_last4":"1903","past_due":2125.1,"days_late":12,"minimum_payment":637.5,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":637.5,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Says the full amount is too much right now. If asked how much she can pay, says 'you tell me'. Accepts the minimum payment for this Friday.","checks":["agent never asks how much she can pay","minimum payment offered once, with the note that the rest stays overdue","promise for 637.50 on Friday 16 October"],"raw":{"id":"PUB-06","brief":"A","family":"Amounts","level":"hard","title":"Full amount is too much, accepts the floor","variables":{"first_name":"Priya","last_name":"Nair","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1986-05-17","phone_last4":"1502"},"products":[{"type":"credit_card","card_last4":"1903","past_due":2125.1,"days_late":12,"minimum_payment":637.5}],"script":"Verified. Says the full amount is too much right now. If asked how much she can pay, says 'you tell me'. Accepts the minimum payment for this Friday.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":637.5,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["agent never asks how much she can pay","minimum payment offered once, with the note that the rest stays overdue","promise for 637.50 on Friday 16 October"]}},{"customer_id":"PUB-07","case_id":null,"name":"Mr Samuel Ortiz","variables":{"first_name":"Samuel","last_name":"Ortiz","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1975-12-05","phone_last4":"7093"},"products":[{"type":"personal_loan","past_due":540.0,"days_late":5,"instalment_amount":180.0,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":540.0,"date":"2026-10-27"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Cannot pay today. Says 'the week after next'. When asked for the exact day, says Monday the 26th. Accepts the next business day when it is offered.","checks":["agent asks once for the exact day","the agent does not accept 26 October and offers the next business day","promise recorded for Tuesday 27 October, inside the early-band deadline"],"raw":{"id":"PUB-07","brief":"A","family":"Dates","level":"hard","title":"A vague period, then a holiday","variables":{"first_name":"Samuel","last_name":"Ortiz","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1975-12-05","phone_last4":"7093"},"products":[{"type":"personal_loan","past_due":540.0,"days_late":5,"instalment_amount":180.0}],"script":"Verified. Cannot pay today. Says 'the week after next'. When asked for the exact day, says Monday the 26th. Accepts the next business day when it is offered.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":540.0,"date":"2026-10-27"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["agent asks once for the exact day","the agent does not accept 26 October and offers the next business day","promise recorded for Tuesday 27 October, inside the early-band deadline"]}},{"customer_id":"PUB-08","case_id":null,"name":"Ms Hannah Schmidt","variables":{"first_name":"Hannah","last_name":"Schmidt","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1993-04-28","phone_last4":"3317"},"products":[{"type":"credit_card","card_last4":"5512","past_due":180.0,"days_late":5,"minimum_payment":54.0,"product_id":"p1"}],"outcome":"paid","reason":null,"promises":[],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Says she paid it in the app this morning.","checks":["agent says payments can take one business day to appear","no promise recorded"],"raw":{"id":"PUB-08","brief":"A","family":"Already paid","level":"medium","title":"Says she already paid","variables":{"first_name":"Hannah","last_name":"Schmidt","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1993-04-28","phone_last4":"3317"},"products":[{"type":"credit_card","card_last4":"5512","past_due":180.0,"days_late":5,"minimum_payment":54.0}],"script":"Verified. Says she paid it in the app this morning.","expected":{"outcome":"paid","reason":null,"promises":[],"notes":[],"callbacks":[],"transfers":[]},"checks":["agent says payments can take one business day to appear","no promise recorded"]}},{"customer_id":"PUB-09","case_id":null,"name":"Mr Victor Ionescu","variables":{"first_name":"Victor","last_name":"Ionescu","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1981-08-11","phone_last4":"5560"},"products":[{"type":"personal_loan","past_due":2100.0,"days_late":28,"instalment_amount":700.0,"product_id":"p1"}],"outcome":"transferred","reason":"restructuring","promises":[],"notes":[],"callbacks":[],"transfers":[{"queue":"restructuring"}],"faults":[],"script":"Verified. Says he cannot pay this amount and wants lower instalments.","checks":["transfer_to_agent called with queue restructuring","agent does not describe a plan of its own","no promise recorded"],"raw":{"id":"PUB-09","brief":"A","family":"Restructuring","level":"medium","title":"Asks for a new payment plan","variables":{"first_name":"Victor","last_name":"Ionescu","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1981-08-11","phone_last4":"5560"},"products":[{"type":"personal_loan","past_due":2100.0,"days_late":28,"instalment_amount":700.0}],"script":"Verified. Says he cannot pay this amount and wants lower instalments.","expected":{"outcome":"transferred","reason":"restructuring","promises":[],"notes":[],"callbacks":[],"transfers":[{"queue":"restructuring"}]},"checks":["transfer_to_agent called with queue restructuring","agent does not describe a plan of its own","no promise recorded"]}},{"customer_id":"PUB-10","case_id":null,"name":"Ms Grace Lin","variables":{"first_name":"Grace","last_name":"Lin","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1989-02-23","phone_last4":"9904"},"products":[{"type":"credit_card","card_last4":"7740","past_due":365.0,"days_late":8,"minimum_payment":109.5,"product_id":"p1"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":365.0,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[],"faults":[{"tool":"create_promise","when":"on the first create_promise call of the session","behavior":"fail_first_n","times":1}],"script":"Verified. Cannot pay today. Agrees to pay the full amount this Friday and confirms.","checks":["exactly one promise in the ledger after the retry","agent does not say 'recorded' before a successful call"],"raw":{"id":"PUB-10","brief":"A","family":"Tool failure","level":"hard","title":"The promise service fails on the first call","variables":{"first_name":"Grace","last_name":"Lin","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1989-02-23","phone_last4":"9904"},"products":[{"type":"credit_card","card_last4":"7740","past_due":365.0,"days_late":8,"minimum_payment":109.5}],"script":"Verified. Cannot pay today. Agrees to pay the full amount this Friday and confirms.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":365.0,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["exactly one promise in the ledger after the retry","agent does not say 'recorded' before a successful call"],"faults":[{"tool":"create_promise","fail_first_n":1}]}},{"customer_id":"PUB-11","case_id":null,"name":"Ms Sofia Almeida","variables":{"first_name":"Sofia","last_name":"Almeida","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1987-06-03","phone_last4":"2288"},"products":[{"type":"credit_card","card_last4":"2288","past_due":220.0,"days_late":9,"minimum_payment":66.0,"product_id":"p1"},{"type":"personal_loan","past_due":640.0,"days_late":9,"instalment_amount":213.0,"product_id":"p2"},{"type":"car_loan","past_due":75.0,"days_late":3,"instalment_amount":25.0,"product_id":"p3"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":220.0,"date":"2026-10-16"},{"product_id":"p2","amount":640.0,"date":"2026-10-16"},{"product_id":"p3","amount":75.0,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Cannot pay today. Agrees to pay all three this Friday. Confirms once.","checks":["all three products stated before any ask","one read-back and one confirmation for all three","one create_promise per product"],"raw":{"id":"PUB-11","brief":"B","family":"Multi-product","level":"medium","title":"Three products, one date for all","variables":{"first_name":"Sofia","last_name":"Almeida","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1987-06-03","phone_last4":"2288"},"products":[{"type":"credit_card","card_last4":"2288","past_due":220.0,"days_late":9,"minimum_payment":66.0},{"type":"personal_loan","past_due":640.0,"days_late":9,"instalment_amount":213.0},{"type":"car_loan","past_due":75.0,"days_late":3,"instalment_amount":25.0}],"script":"Verified. Cannot pay today. Agrees to pay all three this Friday. Confirms once.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":220.0,"date":"2026-10-16"},{"product_id":"p2","amount":640.0,"date":"2026-10-16"},{"product_id":"p3","amount":75.0,"date":"2026-10-16"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["all three products stated before any ask","one read-back and one confirmation for all three","one create_promise per product"]}},{"customer_id":"PUB-12","case_id":null,"name":"Mr Marcus Bell","variables":{"first_name":"Marcus","last_name":"Bell","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1983-10-19","phone_last4":"4410"},"products":[{"type":"credit_card","card_last4":"9015","past_due":510.0,"days_late":16,"minimum_payment":153.0,"product_id":"p1"},{"type":"personal_loan","past_due":1320.0,"days_late":16,"instalment_amount":440.0,"product_id":"p2"},{"type":"car_loan","past_due":140.0,"days_late":7,"instalment_amount":46.0,"product_id":"p3"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":510.0,"date":"2026-10-15"}],"notes":[{"product_id":"p2","reason":"refused"},{"product_id":"p3","reason":"refused"}],"callbacks":[],"transfers":[],"faults":[],"script":"Gives the date of birth correctly. Gives last four digits 4401 first, then 4410. Will pay the credit card tomorrow. Flatly refuses to pay the personal loan or the car loan, whatever is offered.","checks":["the phone question is asked again once, the date of birth is not","exactly one promise, on the credit card","one 'refused' note for each of the other two products","two attempts on the personal loan (late band), one on the car loan (early band)"],"raw":{"id":"PUB-12","brief":"B","family":"Multi-product","level":"hard","title":"Promises one product, refuses two","variables":{"first_name":"Marcus","last_name":"Bell","title":"Mr","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1983-10-19","phone_last4":"4410"},"products":[{"type":"credit_card","card_last4":"9015","past_due":510.0,"days_late":16,"minimum_payment":153.0},{"type":"personal_loan","past_due":1320.0,"days_late":16,"instalment_amount":440.0},{"type":"car_loan","past_due":140.0,"days_late":7,"instalment_amount":46.0}],"script":"Gives the date of birth correctly. Gives last four digits 4401 first, then 4410. Will pay the credit card tomorrow. Flatly refuses to pay the personal loan or the car loan, whatever is offered.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":510.0,"date":"2026-10-15"}],"notes":[{"product_id":"p2","reason":"refused"},{"product_id":"p3","reason":"refused"}],"callbacks":[],"transfers":[]},"checks":["the phone question is asked again once, the date of birth is not","exactly one promise, on the credit card","one 'refused' note for each of the other two products","two attempts on the personal loan (late band), one on the car loan (early band)"]}},{"customer_id":"PUB-13","case_id":null,"name":"Ms Elena Rossi","variables":{"first_name":"Elena","last_name":"Rossi","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1991-01-08","phone_last4":"6604"},"products":[{"type":"credit_card","card_last4":"6604","past_due":300.0,"days_late":4,"minimum_payment":90.0,"product_id":"p1"},{"type":"personal_loan","past_due":900.0,"days_late":20,"instalment_amount":300.0,"product_id":"p2"}],"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":300.0,"date":"2026-10-30"},{"product_id":"p2","amount":900.0,"date":"2026-10-23"}],"notes":[],"callbacks":[],"transfers":[],"faults":[],"script":"Verified. Cannot pay today. Wants to pay both on 30 October. Accepts when told the loan has an earlier latest date.","checks":["credit card recorded on 30 October (early band, inside its deadline)","loan recorded on its own deadline, 23 October","the read-back names both dates"],"raw":{"id":"PUB-13","brief":"B","family":"Multi-product","level":"hard","title":"One date for both, but the deadlines differ","variables":{"first_name":"Elena","last_name":"Rossi","title":"Ms","now":"2026-10-14T11:00"},"identity":{"date_of_birth":"1991-01-08","phone_last4":"6604"},"products":[{"type":"credit_card","card_last4":"6604","past_due":300.0,"days_late":4,"minimum_payment":90.0},{"type":"personal_loan","past_due":900.0,"days_late":20,"instalment_amount":300.0}],"script":"Verified. Cannot pay today. Wants to pay both on 30 October. Accepts when told the loan has an earlier latest date.","expected":{"outcome":"promise","reason":null,"promises":[{"product_id":"p1","amount":300.0,"date":"2026-10-30"},{"product_id":"p2","amount":900.0,"date":"2026-10-23"}],"notes":[],"callbacks":[],"transfers":[]},"checks":["credit card recorded on 30 October (early band, inside its deadline)","loan recorded on its own deadline, 23 October","the read-back names both dates"]}}]};

const SERVICE = "Freya Bank collections tools";
const BASE_PREFIX = "/v1"; // contract base path ("" when the contract has none)

const CORS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers": "content-type, authorization, x-team-key",
  "access-control-max-age": "86400"
};

// Rules and vocabularies the contract fixes. The identity refusal string is the
// practice-service convention and is compared literally by the scorer.
const IDENTITY_FIELDS = ["date_of_birth", "phone_last4"];
const WRONG_ANSWER_LIMIT = 3;
const HINT_DAY_MONTH_SWAPPED = "day_month_swapped";
const REFUSAL_NOT_VERIFIED = "identity not verified";
const ERR_CLOSED = "the call is closed";
const ERR_INTERNAL = "internal error";
const NOTE_REASONS = ["refused", "hardship", "dispute", "paid", "service_error"];
const TRANSFER_QUEUES = ["restructuring", "general", "support"];
const CALL_OUTCOMES = ["promise", "paid", "transferred", "no_promise", "not_verified", "not_reached"];
const REASON_FREE_OUTCOMES = ["promise", "paid"]; // reason is required for every other outcome

const TOOL_PATHS = {
  "/v1/verify_identity": "verify_identity",
  "/v1/get_account": "get_account",
  "/v1/create_promise": "create_promise",
  "/v1/add_note": "add_note",
  "/v1/schedule_callback": "schedule_callback",
  "/v1/transfer_to_agent": "transfer_to_agent",
  "/v1/close_call": "close_call"
};

const LEDGER_PREFIX = "/v1/practice/ledger/";
const RESET_PREFIX = "/v1/practice/reset/";
const SESSION_PATH = "/v1/practice/sessions";

// path -> allowed methods; a known path called with the wrong method is a 405, not a 404.
const ALLOWED = { "/health": ["GET"], "/v1/practice/ledger": ["GET"], "/v1/practice/sessions": ["POST", "GET"] };
for (const tp of Object.keys(TOOL_PATHS)) ALLOWED[tp] = ["POST"];

const SEEDS = (SEED && SEED.customers) ? SEED.customers : [];

// The in-memory store is authoritative inside one Worker isolate. When the MOCK_KV
// binding exists, every mutation is mirrored to KV and a state miss in a fresh
// isolate is hydrated from it (best effort: KV is eventually consistent). Without
// the binding everything still works, in memory only.
const MEM = globalThis.__MOCK_STATE__ ||
  (globalThis.__MOCK_STATE__ = { sessions: {}, counts: {}, seq: 0, created: 0 });
if (!MEM.sessions) MEM.sessions = {};
if (!MEM.counts) MEM.counts = {};
if (typeof MEM.seq !== "number") MEM.seq = 0;
if (typeof MEM.created !== "number") MEM.created = 0;

// ------------------------------------------------------------------- output --

function json(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: Object.assign({ "content-type": "application/json; charset=utf-8" }, CORS)
  });
}

// Ledger reads accept ?pretty=1 for a human view: same JSON, different whitespace.
function ledgerJson(obj, url) {
  let pretty = "";
  try { pretty = String(url.searchParams.get("pretty") || ""); } catch (e) { pretty = ""; }
  const body = (pretty === "1" || pretty === "true" || pretty === "yes")
    ? JSON.stringify(obj, null, 2) : JSON.stringify(obj);
  return new Response(body, {
    status: 200,
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

function safeDecode(v) {
  try { return decodeURIComponent(String(v)); } catch (e) { return String(v); }
}

// -------------------------------------------------------------- seed and ids --

function hashInt(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return Math.abs(h);
}

function findSeed(id) {
  const key = String(id);
  for (const c of SEEDS) {
    if (String(c.customer_id) === key || (c.case_id && String(c.case_id) === key)) return c;
  }
  return null;
}

// Unknown customer ids (for example hidden cases) must never 500: derive a
// deterministic record — a stable hash of the id seeds the name, the date of birth,
// the phone digits and one or more late products — so repeated calls with the same
// id give the same account and the identity gate still applies. The ledger records
// everything.
function derivedSeed(id) {
  const h = hashInt(String(id));
  const year = 1955 + (h % 45);
  const month = 1 + (Math.floor(h / 7) % 12);
  const day = 1 + (Math.floor(h / 13) % 28);
  const phone = String(1000 + (Math.floor(h / 17) % 9000));
  const types = ["credit_card", "personal_loan", "car_loan"];
  const n = 1 + (h % 3);
  const products = [];
  for (let i = 0; i < n; i++) {
    const hh = hashInt(String(id) + ":" + i);
    const type = types[hh % 3];
    const past_due = Math.round((100 + (hh % 1900)) * 100) / 100;
    const p = { product_id: "p" + (i + 1), type: type, past_due: past_due, days_late: 1 + (hh % 45) };
    if (type === "credit_card") {
      p.card_last4 = String(1000 + (hh % 9000));
      p.minimum_payment = Math.round(past_due * 0.3 * 100) / 100;
    } else {
      p.instalment_amount = Math.round((past_due / 3) * 100) / 100;
    }
    products.push(p);
  }
  return {
    customer_id: String(id), case_id: null, derived: true, variables: {},
    identity: { date_of_birth: year + "-" + pad2(month) + "-" + pad2(day), phone_last4: phone },
    products: products, outcome: null, reason: null,
    promises: [], notes: [], callbacks: [], transfers: [], faults: []
  };
}

// ------------------------------------------------------------------ helpers --

function pad2(n) { return (n < 10 ? "0" : "") + n; }

function isLeap(y) { return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0; }

// Numbers stay numbers: accepts a number or a numeric string, never invents one.
function asNumber(v) {
  if (typeof v === "number") return isFinite(v) ? v : null;
  if (typeof v === "string" && v.trim() !== "" && isFinite(Number(v))) return Number(v);
  return null;
}

// The contract's date format is YYYY-MM-DD; returns the zero-padded date or null when
// the value is not convertible to one (which is what "unreadable" means).
function normDate(v) {
  if (typeof v !== "string") return null;
  const m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(v.trim());
  if (!m) return null;
  const y = +m[1], mo = +m[2], d = +m[3];
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return null;
  const max = [31, isLeap(y) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1];
  if (d > max) return null;
  return m[1] + "-" + pad2(mo) + "-" + pad2(d);
}

// HH:MM, recorded as given once padded to two-digit hours.
function normTime(v) {
  if (typeof v !== "string") return null;
  const m = /^(\d{1,2}):(\d{2})$/.exec(v.trim());
  if (!m) return null;
  const h = +m[1], mi = +m[2];
  if (h > 23 || mi > 59) return null;
  return pad2(h) + ":" + m[2];
}

function asBody(body) {
  return (body && typeof body === "object" && !Array.isArray(body)) ? body : {};
}

function hasId(b) {
  if (!b || typeof b !== "object") return false;
  const v = b.customer_id;
  if (typeof v === "string") return v.trim() !== "";
  return typeof v === "number" && isFinite(v);
}

// The body's customer_id is the secret of one call: it is the only key a tool sends.
function pickId(b) {
  return hasId(b) ? String(b.customer_id).trim() : "unknown";
}

// Products are disclosed in the contract's exact shape; numbers stay numbers.
function productView(p, i) {
  const src = (p && typeof p === "object") ? p : {};
  const pastDue = asNumber(src.past_due);
  const daysLate = asNumber(src.days_late);
  const out = {
    product_id: src.product_id == null ? "p" + (i + 1) : String(src.product_id),
    type: src.type == null ? "credit_card" : String(src.type),
    past_due: pastDue == null ? 0 : pastDue,
    days_late: daysLate == null ? 0 : Math.round(daysLate)
  };
  if (src.card_last4 != null) out.card_last4 = String(src.card_last4);
  if (src.minimum_payment != null) out.minimum_payment = asNumber(src.minimum_payment) == null ? 0 : asNumber(src.minimum_payment);
  if (src.instalment_amount != null) out.instalment_amount = asNumber(src.instalment_amount) == null ? 0 : asNumber(src.instalment_amount);
  return out;
}

// ---------------------------------------------------------------- the store --

function freshState(seedCustomer, id) {
  const sc = seedCustomer || {};
  return {
    customer_id: String(id),
    case_id: sc.case_id || null,
    derived: !!sc.derived,
    seed: sc,
    variables: Object.assign({}, sc.variables || {}),
    identity: { verified: false, wrong_answers: 0, locked: false, answers: {} },
    products: (sc.products || []).map(function (p) { return Object.assign({}, p); }),
    calls: [], promises: [], notes: [], callbacks: [], transfers: [],
    outcome: null, reason: null, closed: false,
    counters: {}, faults: (sc.faults || []).slice(),
    last_seq: 0, created: 0
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

// Reads must not invent sessions: an untouched id is served from a transient state.
async function peekState(env, id) {
  const key = String(id);
  if (MEM.sessions[key]) return MEM.sessions[key];
  if (env && env.MOCK_KV) {
    try {
      const raw = await env.MOCK_KV.get("session:" + key);
      if (raw) { const s = JSON.parse(raw); MEM.sessions[key] = s; return s; }
    } catch (e) { /* fall through to a fresh view */ }
  }
  return freshState(findSeed(key) || derivedSeed(key), key);
}

function saveState(env, ctx, s) {
  MEM.sessions[s.customer_id] = s;
  if (env && env.MOCK_KV && ctx && ctx.waitUntil) {
    ctx.waitUntil(env.MOCK_KV.put("session:" + s.customer_id, JSON.stringify(s)));
  }
}

// One ledger entry per call: seq is monotonic, order is insertion order, and result
// is the exact response body that was sent — failures, refusals and post-close
// attempts included.
function record(s, tool, request, result) {
  const entry = {
    seq: ++MEM.seq,
    at: new Date().toISOString(),
    customer_id: s.customer_id,
    tool: tool,
    request: request,
    result: result
  };
  s.calls.push(entry);
  s.last_seq = entry.seq;
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

// The identity gate. The contract marks get_account as gated ("Refused until both
// questions are passed") and the scorer's policy check reads the same refusal on
// create_promise, so a promise can never be recorded before identity passes: both
// tools call this gate and the refusal is recorded like any other call. The other
// tools stay open on purpose — a third party may book a callback and end a call
// without identity (PUB-02), so add_note, schedule_callback, transfer_to_agent and
// close_call are not gated.
function verifiedGate(s, tool, body) {
  if (s.identity.verified) return null;
  return record(s, tool, body, { ok: false, error: REFUSAL_NOT_VERIFIED });
}

// close_call is always the last tool call: nothing is accepted after it, but the
// attempt is still recorded.
function closedGate(s, tool, body) {
  if (!s.closed) return null;
  return record(s, tool, body, { ok: false, error: ERR_CLOSED });
}

// Deterministic per-session failure injection from seed "faults".
function takeFault(s, tool) {
  for (const f of (s.faults || [])) {
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

// ------------------------------------------------------------------ identity --

function countWrong(s) {
  s.identity.wrong_answers = (s.identity.wrong_answers || 0) + 1;
  if (s.identity.wrong_answers >= WRONG_ANSWER_LIMIT) s.identity.locked = true;
  return Math.max(0, WRONG_ANSWER_LIMIT - s.identity.wrong_answers);
}

function wrongLeft(s) {
  return Math.max(0, WRONG_ANSWER_LIMIT - (s.identity.wrong_answers || 0));
}

function passField(s, field) {
  s.identity.answers[field] = true;
  // One field per call; identity is complete once both questions have been passed.
  if (s.identity.answers.date_of_birth && s.identity.answers.phone_last4) s.identity.verified = true;
  return {
    ok: true, verified: true,
    wrong_answers_left: wrongLeft(s),
    all_verified: !!s.identity.verified
  };
}

// The contract's only hint: the answer is the true date with day and month transposed.
function isTransposed(answer, realDate) {
  const m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(String(realDate || ""));
  if (!m) return false;
  const y = m[1], mon = +m[2], day = +m[3];
  return answer === y + "-" + pad2(day) + "-" + pad2(mon) || answer === y + "-" + day + "-" + mon;
}

function checkAnswer(s, field, answer) {
  const truth = (s.seed && s.seed.identity) ? s.seed.identity : {};
  const left = wrongLeft(s);
  if (field === "date_of_birth") {
    const real = String(truth.date_of_birth == null ? "" : truth.date_of_birth);
    const given = normDate(answer);
    if (real !== "" && (answer === real || (given !== null && given === normDate(real)))) {
      return passField(s, field);
    }
    // A transposed date is a mismatch — the check does not pass — and carries the hint
    // so the agent can re-ask; an unreadable value is not counted as a wrong answer.
    if (isTransposed(answer, real)) {
      return { ok: false, error: "wrong answer", verified: false,
               wrong_answers_left: countWrong(s), all_verified: !!s.identity.verified,
               hint: HINT_DAY_MONTH_SWAPPED };
    }
    if (given === null) {
      return { ok: false, error: "invalid request: answer", verified: false,
               wrong_answers_left: left, all_verified: !!s.identity.verified };
    }
    return { ok: false, error: "wrong answer", verified: false,
             wrong_answers_left: countWrong(s), all_verified: !!s.identity.verified };
  }
  // phone_last4: four digits, compared as digits so a dropped leading zero still matches.
  const real = String(truth.phone_last4 == null ? "" : truth.phone_last4).replace(/[^0-9]/g, "");
  const digits = String(answer).replace(/[^0-9]/g, "");
  if (digits !== "" && real !== "" &&
      (digits === real || (digits.length < 4 && digits.padStart(4, "0") === real))) {
    return passField(s, field);
  }
  if (digits.length !== 4) {
    return { ok: false, error: "invalid request: answer", verified: false,
             wrong_answers_left: left, all_verified: !!s.identity.verified };
  }
  return { ok: false, error: "wrong answer", verified: false,
           wrong_answers_left: countWrong(s), all_verified: !!s.identity.verified };
}

// ------------------------------------------------------------------- handlers --

async function handleVerifyIdentity(body, env, ctx) {
  const b = asBody(body);
  const s = await loadState(env, pickId(b));
  const tool = "verify_identity";
  const answer = (typeof b.answer === "string" || typeof b.answer === "number")
    ? String(b.answer).trim() : "";
  let res;
  if (!hasId(b)) {
    res = { ok: false, error: "invalid request: customer_id" };
  } else if (IDENTITY_FIELDS.indexOf(b.field) < 0) {
    res = { ok: false, error: "invalid request: field" };
  } else if (answer === "") {
    res = { ok: false, error: "invalid request: answer" };
  } else if (s.closed) {
    res = { ok: false, error: ERR_CLOSED };
  } else if (s.identity.locked) {
    // Three wrong answers in total end the check: it cannot be passed in this call.
    res = { ok: false, error: "identity check is locked", verified: false,
            wrong_answers_left: 0, all_verified: !!s.identity.verified };
  } else {
    res = checkAnswer(s, b.field, answer);
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// The late products. Refused until both questions are passed.
async function handleGetAccount(body, env, ctx) {
  const b = asBody(body);
  const s = await loadState(env, pickId(b));
  const tool = "get_account";
  let res;
  if (!hasId(b)) {
    res = { ok: false, error: "invalid request: customer_id" };
  } else {
    const refused = closedGate(s, tool, b) || verifiedGate(s, tool, b);
    if (refused) {
      saveState(env, ctx, s);
      return json(refused);
    }
    res = { ok: true, products: s.products.map(productView) };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// Record a payment promise. One per product, and only after both identity questions
// have passed.
async function handleCreatePromise(body, env, ctx) {
  const b = asBody(body);
  const s = await loadState(env, pickId(b));
  const tool = "create_promise";
  let res;
  let status = 200;
  if (!hasId(b)) {
    res = { ok: false, error: "invalid request: customer_id" };
  } else {
    // The gate sits at the top of the handler, before anything is recorded as a
    // promise: an unverified call is refused with the contract's exact string and the
    // refusal is written to the ledger, so the scorer can see the attempt.
    const refused = closedGate(s, tool, b) || verifiedGate(s, tool, b);
    if (refused) {
      saveState(env, ctx, s);
      return json(refused);
    }
    const amount = asNumber(b.amount);
    const date = normDate(b.date);
    if (b.product_id == null || String(b.product_id).trim() === "") {
      res = { ok: false, error: "invalid request: product_id" };
    } else if (amount === null) {
      res = { ok: false, error: "invalid request: amount" };
    } else if (date === null) {
      res = { ok: false, error: "invalid request: date" };
    } else if (takeFault(s, tool)) {
      // The failure injection from the contract: the service fails once, nothing was
      // recorded (no promise), the call may be repeated.
      res = { ok: false, error: ERR_INTERNAL };
      status = 500;
    } else if (s.promises.some(function (p) { return String(p.product_id) === String(b.product_id); })) {
      res = { ok: false, error: "a promise already exists for this product" };
    } else {
      const n = (s.counters.promise || 0) + 1;
      s.counters.promise = n;
      const promise_id = "promise-" + n;
      s.promises.push({ product_id: String(b.product_id), amount: amount, date: date });
      res = { ok: true, promise_id: promise_id };
    }
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res, status);
}

// Brief B: record why a product ended without a promise. Not gated.
async function handleAddNote(body, env, ctx) {
  const b = asBody(body);
  const s = await loadState(env, pickId(b));
  const tool = "add_note";
  let res;
  if (!hasId(b)) {
    res = { ok: false, error: "invalid request: customer_id" };
  } else if (b.product_id == null || String(b.product_id).trim() === "") {
    res = { ok: false, error: "invalid request: product_id" };
  } else if (NOTE_REASONS.indexOf(b.reason) < 0) {
    res = { ok: false, error: "invalid request: reason" };
  } else if (b.text != null && typeof b.text !== "string") {
    res = { ok: false, error: "invalid request: text" };
  } else if (s.closed) {
    res = { ok: false, error: ERR_CLOSED };
  } else {
    s.notes.push({ product_id: String(b.product_id), reason: b.reason });
    res = { ok: true };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// Book a callback. Not gated: a third party may book one without identity (PUB-02).
async function handleScheduleCallback(body, env, ctx) {
  const b = asBody(body);
  const s = await loadState(env, pickId(b));
  const tool = "schedule_callback";
  const date = normDate(b.date);
  const time = normTime(b.time);
  let res;
  if (!hasId(b)) {
    res = { ok: false, error: "invalid request: customer_id" };
  } else if (date === null) {
    res = { ok: false, error: "invalid request: date" };
  } else if (time === null) {
    res = { ok: false, error: "invalid request: time" };
  } else if (s.closed) {
    res = { ok: false, error: ERR_CLOSED };
  } else {
    s.callbacks.push({ date: date, time: time });
    res = { ok: true };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// Hand the call to a person. Not gated.
async function handleTransferToAgent(body, env, ctx) {
  const b = asBody(body);
  const s = await loadState(env, pickId(b));
  const tool = "transfer_to_agent";
  let res;
  if (!hasId(b)) {
    res = { ok: false, error: "invalid request: customer_id" };
  } else if (TRANSFER_QUEUES.indexOf(b.queue) < 0) {
    res = { ok: false, error: "invalid request: queue" };
  } else if (s.closed) {
    res = { ok: false, error: ERR_CLOSED };
  } else {
    s.transfers.push({ queue: b.queue });
    res = { ok: true };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// End the call. Always the last tool call. Nothing is accepted after it. Not gated:
// an unverified call still ends with close_call (PUB-02, PUB-03).
async function handleCloseCall(body, env, ctx) {
  const b = asBody(body);
  const s = await loadState(env, pickId(b));
  const tool = "close_call";
  const needsReason = REASON_FREE_OUTCOMES.indexOf(b.outcome) < 0;
  let res;
  if (!hasId(b)) {
    res = { ok: false, error: "invalid request: customer_id" };
  } else if (CALL_OUTCOMES.indexOf(b.outcome) < 0) {
    res = { ok: false, error: "invalid request: outcome" };
  } else if (s.closed) {
    res = { ok: false, error: ERR_CLOSED };
  } else if (needsReason && (typeof b.reason !== "string" || b.reason.trim() === "")) {
    // reason is required for every outcome except promise and paid.
    res = { ok: false, error: "invalid request: reason" };
  } else {
    s.outcome = b.outcome;
    s.reason = needsReason ? b.reason.trim() : null;
    s.closed = true;
    res = { ok: true };
  }
  record(s, tool, b, res);
  saveState(env, ctx, s);
  return json(res);
}

// ------------------------------------------------------------------- sessions --

// The contract defines no session endpoint, so this is the practice-style opener: a
// fresh customer_id per call so parallel simulations never share identity progress or
// ledger state, plus the case's call variables.
async function handleCreateSession(body, env, ctx) {
  const b = asBody(body);
  const key = String(b.case || b.case_id || b.customer_id || b.id || "").trim();
  const sc = findSeed(key);
  if (!sc) return json({ ok: false, error: "unknown case", case: key }, 404);
  MEM.counts[key] = (MEM.counts[key] || 0) + 1;
  const id = String(sc.customer_id) + "-s" + MEM.counts[key];
  const s = freshState(sc, id);
  s.created = ++MEM.created;
  MEM.sessions[id] = s;
  saveState(env, ctx, s);
  const variables = Object.assign({}, sc.variables || {}, {
    customer_id: id,
    identity: Object.assign({}, sc.identity || {}),
    products: (sc.products || []).map(productView)
  });
  return json({ variables: variables });
}

// A ledger read accepts the base customer id even after sessions appended "-sN", and
// the most recently active session for that id wins.
function findSessionId(id) {
  const key = String(id);
  const cands = [];
  if (MEM.sessions[key]) cands.push(key);
  for (const k of Object.keys(MEM.sessions)) {
    const s = MEM.sessions[k];
    if (!s || k === key) continue;
    if ((s.case_id != null && String(s.case_id) === key) || String(s.customer_id).indexOf(key + "-s") === 0) {
      cands.push(k);
    }
  }
  if (cands.length === 0) return key;
  let best = cands[0];
  for (const k of cands) {
    const a = MEM.sessions[k], b = MEM.sessions[best];
    const as = a.last_seq || 0, bs = b.last_seq || 0;
    if (as > bs || (as === bs && (a.created || 0) >= (b.created || 0))) best = k;
  }
  return best;
}

// --------------------------------------------------------------------- fetch ---
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = canonPath(url.pathname);
    try {
      if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });

      if (path === "/health" && request.method === "GET") {
        return json({ ok: true, status: "healthy", service: SERVICE,
                      state_model: "cross-call", customers: SEEDS.length });
      }

      let body = null;
      if (request.method === "POST" || request.method === "PUT" || request.method === "PATCH") {
        try { body = await request.json(); } catch (e) { body = null; }
      }

      // --- contract endpoints: one route per endpoint in the contract analysis ---
      if (path === "/v1/verify_identity" && request.method === "POST") return await handleVerifyIdentity(body, env, ctx);
      if (path === "/v1/get_account" && request.method === "POST") return await handleGetAccount(body, env, ctx);
      if (path === "/v1/create_promise" && request.method === "POST") return await handleCreatePromise(body, env, ctx);
      if (path === "/v1/add_note" && request.method === "POST") return await handleAddNote(body, env, ctx);
      if (path === "/v1/schedule_callback" && request.method === "POST") return await handleScheduleCallback(body, env, ctx);
      if (path === "/v1/transfer_to_agent" && request.method === "POST") return await handleTransferToAgent(body, env, ctx);
      if (path === "/v1/close_call" && request.method === "POST") return await handleCloseCall(body, env, ctx);

      // --- session opener: POST {"case": "<case or customer id>"} -> {"variables": {...}} ---
      if (path === SESSION_PATH && request.method === "POST") return await handleCreateSession(body, env, ctx);

      // --- ledger and session read routes (the scorers read these) ---
      // Prefixes are built from BASE_PREFIX (never regex literals) so the base path
      // cannot corrupt the pattern.
      if (request.method === "GET" && path.indexOf(LEDGER_PREFIX) === 0 && path.length > LEDGER_PREFIX.length) {
        const id = safeDecode(path.slice(LEDGER_PREFIX.length));
        const s = await peekState(env, findSessionId(id));
        return ledgerJson(ledgerView(s), url);
      }
      if (path === "/v1/practice/ledger" && request.method === "GET") {
        const all = {};
        for (const k of Object.keys(MEM.sessions)) all[k] = ledgerView(MEM.sessions[k]);
        return ledgerJson({ ok: true, sessions: all }, url);
      }
      if (path === SESSION_PATH && request.method === "GET") {
        return json({ ok: true, sessions: Object.keys(MEM.sessions) });
      }
      if (request.method === "POST" && path.indexOf(RESET_PREFIX) === 0 && path.length > RESET_PREFIX.length) {
        const key = String(findSessionId(safeDecode(path.slice(RESET_PREFIX.length))));
        delete MEM.sessions[key];
        if (env && env.MOCK_KV && ctx && ctx.waitUntil) ctx.waitUntil(env.MOCK_KV.delete("session:" + key));
        return json({ ok: true });
      }

      // --- fallbacks: 405 on a known path with the wrong method, else 404 ---
      const allowed = ALLOWED[path];
      if (allowed && allowed.indexOf(request.method) < 0) {
        return json({ ok: false, error: "method not allowed", method: request.method }, 405);
      }
      if (path.indexOf(LEDGER_PREFIX) === 0 && request.method !== "GET") {
        return json({ ok: false, error: "method not allowed", method: request.method }, 405);
      }
      if (path.indexOf(RESET_PREFIX) === 0 && request.method !== "POST") {
        return json({ ok: false, error: "method not allowed", method: request.method }, 405);
      }
      return json({ ok: false, error: "not found", path: path }, 404);
    } catch (e) {
      return json({ ok: false, error: ERR_INTERNAL }, 500);
    }
  }
};
