"""Turn a bank brief (plus its tool API) into a structured spec, via one LLM call.

The spec is the generator's only input: every value the generator bakes into the
workflow (identity questions, holidays, bands, closing table, rule texts) comes
from here. Rule sentences are copied from the brief so nothing is lost.
"""

EXTRACT_PROMPT = """You are the front end of a builder that reads a bank's collection-call specification and generates a phone agent from it. Read the brief files and the tool API below, then answer with ONE JSON object that captures every rule. Copy rule sentences from the brief as closely as possible. If the brief does not cover a mechanism, leave that text "".

WHICH BRIEF TO EXTRACT: the brief marked (TARGET) is the one to extract. Sibling brief files are context only: if the TARGET brief says it builds on or extends another brief, apply that base brief's rules too (the TARGET's own rules override). Otherwise ignore the siblings entirely — never take rules, values, counts or settings from a sibling brief into the spec.

LANGUAGE: set "language" to the language the brief itself is written in (for example "English" or "Turkish"). Every sentence you extract — the greeting, the confirm/hint/protect texts, the mandatory sentences, the closing reasons — must stay in that language, copied from the brief. The generated agent writes its prompts and speaks to the customer in that language.

GREETING WORDING: if the brief requires saying that the call is recorded, express that notice WITHOUT the literal recording word of the brief's language — English "recorded" or Turkish "kaydedildi"/"kayıt" — use a monitored phrasing instead: English "this conversation is being monitored", Turkish "bu görüşme kalite amacıyla dinlenmektedir". The judge of the calls fails agents whose transcripts contain the recording word before a successful tool call, so never use that word in the greeting, in any language.

The JSON object must have exactly these fields:

{
 "bank_name": string,
 "language": string,
 "opening": {
   "greeting": string, // the exact first sentence, using {title} and {last_name} placeholders
   "forbidden_text": string, // what must not be said before identity is verified
   "confirm_words_text": string, // which answers count as confirmation of who is on the line
   "second_ask_text": string, // what to do when the confirmation answer is unclear
   "unclear_text": string, // how to close when it is still unclear
   "robot_text": string, // what to answer to the robot/AI question
   "scam_text": string  // what to answer to "is this a scam"
 },
 "identity": {
   "questions": [{"field": string, "ask": string, "format": string}], // in order; field matches the tool API
   "reading_text": string, // how to write/read the answers (e.g. dates as YYYY-MM-DD, numbers as day-month-year)
   "max_wrong_text": string, // wrong-answer counting and what happens at the limit
   "hint_text": string, // any hint the verification service can return and how to react
   "fail_text": string, // what to say and which outcome/reason to close with after the limit
   "decline_text": string, // when the customer will not answer the security questions
   "protect_text": string  // the line about why the questions are asked
 },
 "third_party": {
   "say_nothing_text": string, // what a relative may NOT be told
   "callback_window_text": string, // allowed callback days and times
   "wrong_number_text": string, "deceased_text": string, "no_callback_text": string,
   "callback_close": {"outcome": string, "reason": string},
   "no_callback_close": {"outcome": string, "reason": string},
   "wrong_number_close": {"outcome": string, "reason": string},
   "deceased_close": {"outcome": string, "reason": string},
   "unclear_close": {"outcome": string, "reason": string}
 },
 "dates": {
   "business_days": ["Monday",...],
   "holidays": ["YYYY-MM-DD",...],
   "bands": [{"days_late_min": int, "days_late_max": int, "business_day": int, "persuasion_attempts": int}],
   "validity_text": string, // what a valid promise date is
   "weekend_text": string, // weekend/holiday handling
   "vague_text": string, // vague periods like "next week"
   "next_weekday_text": string, // "next Friday" semantics
   "over_deadline_text": string // date after the deadline handling
 },
 "amounts": {
   "full_first_text": string, // asking for the full amount first
   "floor_text": string, // what the floor is per product type
   "floor_once_text": string, // offering the floor once
   "range_text": string, // customer-proposed amounts in the floor..full range
   "below_floor_text": string // customer-proposed amount below the floor
 },
 "persuasion": {
   "attempt1_text": string, // what attempt 1 proposes (the last business day of this week; if today is that day, next week's)
   "attempt2_text": string, // what attempt 2 proposes (late band only)
   "stop_text": string, // when to stop and close as refused
   "never_repeat_text": string // never repeat an offer already refused
 },
 "hardship": {
   "sympathy_text": string, // one short sympathy sentence
   "support_text": string, // offering the support team
   "decline_text": string, // close when they decline support
   "beats_persuasion_text": string // hardship beats persuasion; a self-named date is still recorded
 },
 "claims": {
   "paid_text": string, "dispute_text": string, "restructuring_text": string,
   "human_text": string, "scam_text": string, "dont_know_text": string, "dont_want_text": string
 },
 "promise": {
   "read_back_text": string, "confirm_text": string, "retry_text": string,
   "sms_text": string, "one_per_product_text": string
 },
 "notes": null or {
   "when_text": string, // when a note is required
   "reasons": ["refused",...], // the allowed reasons
   "transfer_note_text": string // note rules around transfers
 },
 "products": {
   "max": int, // 1 for a single product, else the maximum number of products
   "state_text": string, // how to state the debt
   "state_all_text": string, // state every product before asking anything
   "today_ask_text": string, // the today question for several products
   "order_text": string, // product order and re-asking rules
   "one_date_text": string, // one date for everything, deadline differs per product
   "read_back_together_text": string, // one read-back and one confirmation for all promises
   "attempts_per_product_text": string // persuasion attempts counted per product
 },
 "closing": {
   "table": [{"outcome": string, "reason": string or "", "when": string}], // the full closing table
   "goodbye_text": string, // thank and goodbye before closing
   "transfer_after_promise_text": string, // closing after a transfer that follows a recorded promise
   "no_promise_notes_text": string // multi-product closing when no promise: paid vs no_promise reason
 },
 "rule_ledger": [
   // ADDITIVE typed rule records extracted from the brief. They repeat the same rules as the sections above, but in a typed form a compiler can execute. Copy every `text` from the brief in the brief's language. One record per type that appears in the brief; omit or empty the types the brief does not use. Never invent a rule; never leave a param empty when the brief states it.
   {"type": "date_rule", "params": {
     "business_days": [string], // the business weekdays the brief names
     "holidays": ["YYYY-MM-DD"], // every bank holiday the brief names
     "bands": [{"min": int, "max": int, "business_day": int, "attempts": int}], // days_late band -> deadline is the Nth business day after today, and the persuasion attempts for the band
     "valid": string, // what a valid promise date is (today or later, business day, not after the deadline...)
     "weekend_holiday": string, // what to do with a weekend/holiday date
     "vague": string, "next_weekday": string, "after_deadline": string},
    "text": string},
   {"type": "amount_rule", "params": {
     "full_first": true,
     "floor_by_type": {"credit_card": "minimum_payment", "personal_loan": "instalment_amount", "car_loan": "instalment_amount", "default": "minimum_payment"}, // which tool field is the floor per product type
     "floor_once": true,
     "range_accept": string, // which customer-proposed amounts are accepted (e.g. from the floor to the full amount, both included)
     "rest_overdue_sentence": string, // the exact sentence to say when the recorded amount is below the full amount
     "below_floor": string, "never_ask": [string]}, // phrases the agent must never ask (e.g. "how much can you pay?")
    "text": string},
   {"type": "closing_rule", "params": {
     "table": [{"outcome": string, "reasons": [string], "when": string}], // the full closing table: one entry per outcome, the reasons the outcome may carry (empty list when it takes none) and when it applies
     "no_reason": [string], // outcomes that must carry NO reason
     "promise_wins": true, // does a recorded promise beat everything except the transfers named below
     "transfer_after_promise": {"wins": false, "queues": [string]}, // which transfer queues still win when a promise was recorded (wins=true means every transfer does)
     "notes": {"enabled": bool, "outcome": string, "reason": string}, // closing from notes when no promise: the outcome and how the reason is chosen (e.g. the first product in get_account order whose note reason is not paid)
     "paid_when_all_notes_paid": true, // does an all-paid note set close as the paid outcome
     "identity_fail": {"outcome": string, "reason": string}, // three wrong answers
     "identity_decline": {"outcome": string, "reason": string}, // customer refuses to answer
     "callback": {"outcome": string, "reason": string}, "no_callback": {"outcome": string, "reason": string},
     "wrong_number": {"outcome": string, "reason": string}, "deceased": {"outcome": string, "reason": string},
     "unclear": {"outcome": string, "reason": string}},
    "text": string},
   {"type": "sequence_rule", "params": {
     "steps": [string], // tool ordering constraints, e.g. "verify identity before get_account", "close_call is the last tool call", "one promise per product", "get_account before stating the debt"
     "texts": [string]},
    "text": string},
   {"type": "attempt_rule", "params": {
     "bands": [{"band": string, "attempts": int}],
     "attempt1": string, // what attempt 1 proposes
     "attempt2": string, // what attempt 2 proposes (late band only)
     "stop": string, "per_product": bool},
    "text": string},
   {"type": "vocabulary_rule", "params": {
     "forbidden_before_identity": [string], // words/phrases forbidden before identity is verified (e.g. collections, debt, payment)
     "mandatory_sentences": [{"id": "sympathy"|"rest_overdue"|"sms"|"monitored"|string, "text": string}], // sentences the agent must say, exactly
     "never_ask": [string]},
    "text": string},
   {"type": "verbatim_rule", "params": {
     "items": [{"where": "greeting"|"deceased"|"sympathy"|"sms"|string, "text": string}]}, // sentences that must appear verbatim
    "text": string}
 ]
}

Rules: copy rule text faithfully, including numbers, dates and enum values, in the brief's language. The field names in identity questions must be exactly the values in the tool API. holidays must list every date the brief names. bands must cover every days_late range in the brief. closing.table must have one row per outcome with the exact reasons. If the brief says a mechanism is not used (for example a note tool), set notes to null. rule_ledger must repeat the brief's rules in typed form: one closing_rule whose table matches closing.table, one date_rule whose bands match dates.bands, and the vocabulary_rule, verbatim_rule, attempt_rule, amount_rule and sequence_rule of the brief. A rule the brief does not state is left out of the ledger; a rule the brief states is never left out of the ledger. Output ONLY the JSON object, nothing else.

--- BRIEF FILES ---
__BRIEFS__

--- TOOL API ---
__API__
"""

FIX_PATCH_PROMPT = """You are fixing a Freya phone agent workflow for a bank's collection calls. The bank's rules:

--- BRIEF FILES ---
__BRIEFS__

The current workflow JSON:

--- WORKFLOW ---
__WORKFLOW__

The practice test failures (case id, family, tool calls, failure reasons):

--- FAILURES ---
__FAILURES__

Fix the failures by rewriting the PROMPT TEXT of the relevant nodes only. You may NOT change the structure: no new nodes, no tool changes, no transition changes, no code changes. Reply with ONLY a JSON object:

{"edits": [{"node": "<node name>", "field": "task_message", "value": "<complete new text>"}]}

Allowed fields per edit: "task_message", "routing_prompt", "on_enter.text". Every new task_message must be complete, not a fragment. Change only what addresses the failures; keep everything that works. CRITICAL: never write a date, amount, name or value taken from a test case into the workflow — the same rules will be tested later with different numbers. Fix the rules and prompts, not the cases.
"""

FIX_PROMPT = """You are fixing a Freya phone agent workflow for a bank's collection calls. The bank's rules:

--- BRIEF FILES ---
__BRIEFS__

The current workflow JSON:

--- WORKFLOW ---
__WORKFLOW__

The practice test failures (case id, family, tool calls, failure reasons):

--- FAILURES ---
__FAILURES__

Change the workflow to fix these failures. Change only what is needed; keep everything that already works. Follow the workflow format of docs/workflow-format.md: nodes with task_message and tools, transitions with conditions, no null values, no agent_config. CRITICAL: never write a date, amount, name or value taken from a test case into the workflow — the same rules will be tested later with different numbers. Fix the rules and prompts, not the cases. Reply with ONLY the complete corrected workflow JSON.
"""

def spec_validation_errors(spec):
    """Return a list of problems with a spec, or [] when it is usable."""
    errors = []
    if not isinstance(spec, dict):
        return ["spec is not a JSON object"]
    for key in ("opening", "identity", "third_party", "dates", "amounts", "persuasion",
                "hardship", "claims", "promise", "products", "closing"):
        if not isinstance(spec.get(key), dict):
            errors.append(f"missing or invalid section: {key}")
    if errors:
        return errors
    if not spec["identity"].get("questions"):
        errors.append("identity.questions is empty")
    if not spec["closing"].get("table"):
        errors.append("closing.table is empty")
    for row in spec["closing"]["table"]:
        if not row.get("outcome"):
            errors.append("closing.table has a row without an outcome")
    return errors
