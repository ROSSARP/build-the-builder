"""Turn a bank brief (plus its tool API) into a structured spec, via one LLM call.

The spec is the generator's only input: every value the generator bakes into the
workflow (identity questions, holidays, bands, closing table, rule texts) comes
from here. Rule sentences are copied from the brief so nothing is lost.
"""

EXTRACT_PROMPT = """You are the front end of a builder that reads a bank's collection-call specification and generates a phone agent from it. Read the brief files and the tool API below, then answer with ONE JSON object that captures every rule. Copy rule sentences from the brief as closely as possible. If the brief does not cover a mechanism, leave that text "".

The JSON object must have exactly these fields:

{
 "bank_name": string,
 "language": "English",
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
 }
}

Rules: copy rule text faithfully, including numbers, dates and enum values. The field names in identity questions must be exactly the values in the tool API. holidays must list every date the brief names. bands must cover every days_late range in the brief. closing.table must have one row per outcome with the exact reasons. If the brief says a mechanism is not used (for example a note tool), set notes to null. Output ONLY the JSON object, nothing else.

--- BRIEF FILES ---
__BRIEFS__

--- TOOL API ---
__API__
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
