"""Generate a Freya workflow JSON from a structured spec and the bank's tool API.

The generator is spec-driven: every value that can change between briefs
(identity questions, holidays, deadline bands, closing table, note reasons,
tool fields) comes from the extracted spec or the tool API file. The
mechanism (node structure, business-day math, tool wiring) is fixed.
"""
import json

def bool_group(variable, operands=("true", "True")):
    return {"logic": "or", "conditions": [
        {"variable": variable, "operator": "equals", "operand": o} for o in operands]}

def cond(var, op, operand):
    return {"logic": "or", "conditions": [{"variable": var, "operator": op, "operand": operand}]}

def cond_is_set(var):
    return {"logic": "or", "conditions": [{"variable": var, "operator": "is_set"}]}

def always():
    return {"operator": "always"}

def trans(target, description, condition):
    return {"target_node": target, "description": description, "condition": condition}

def self_trans(description="Keep going"):
    return {"target_node": None, "description": description, "condition": always()}  # target filled by caller

def api_tool(api, path, guidance, response_mapping=None, max_retries=0,
             pre_process_code=None, post_process_code=None, always_runs_at=None,
             body_defaults=None):
    """One bank API call as a Freya function object, fields taken from the tool API file."""
    op = api["paths"][path]["post"]
    url = api["servers"][0]["url"] + path
    schema = op["requestBody"]["content"]["application/json"]["schema"]
    props = {}
    for fname, fspec in schema.get("properties", {}).items():
        leaf = {}
        if "type" in fspec:
            leaf["type"] = fspec["type"]
        if "enum" in fspec:
            leaf["enum"] = fspec["enum"]
        if "description" in fspec:
            leaf["description"] = fspec["description"]
        # customer_id is baked from the call variable; every other field the model fills.
        # The {{var}} default is what makes the model fill it — without a default the
        # model sends nothing (proven by the 0/10 identity run). The editor's
        # "will not resolve" warning for these is noise.
        if fname == "customer_id":
            leaf["default"] = "{{customer_id}}"
        elif body_defaults and fname in body_defaults:
            leaf["default"] = body_defaults[fname]
        else:
            leaf["default"] = "{{" + fname + "}}"
        props[fname] = leaf
    required = [r for r in schema.get("required", []) if r != "customer_id"]
    body = {"type": "object", "properties": props}
    if required:
        body["required"] = required
    tool = {
        "type": "function",
        "config": {"timeoutMs": 12000, "maxRetries": max_retries},
        "function": {
            "name": path.lstrip("/"),
            "handler": "__function__:api_call",
            "description": guidance,
            "parameters": {"type": "object", "properties": {
                "url": {"type": "string", "default": url},
                "method": {"type": "string", "default": "POST"},
                "headers": {"type": "object", "properties": {
                    "Content-Type": {"type": "string", "default": "application/json"}}},
                "body": body,
            }},
        },
    }
    if always_runs_at:
        tool["config"]["alwaysRunsAt"] = always_runs_at
    if response_mapping:
        tool["response_mapping"] = response_mapping
    if pre_process_code:
        tool["pre_process_code"] = pre_process_code
    if post_process_code:
        tool["post_process_code"] = post_process_code
    return tool

# The extraction model anchors relative dates (today, next Friday...) on the REAL
# clock, but every call has its own `now`. Without this prompt the extractor turns
# "today" into the real world date and the whole date pipeline shifts.
EXTRACT_DATE_ANCHOR = ("The current call date is {{now}}. Interpret every date the caller says "
    "(today, tomorrow, next Friday, the 20th, dates in words) relative to {{now}}, never to the real-world clock.\n\n"
    "{{extractor.speech}}\n\n{{extractor.type_preamble}}\n\n{{extractor.variables_list}}\n\n"
    "{{extractor.conversation.last-10}}")

END_CALL_TOOL = {
    "type": "function",
    "config": {"timeoutMs": 10000},
    "function": {
        "name": "end_call",
        "handler": "__function__:end_call",
        "parameters": {"type": "object", "properties": {
            "message_mode": {"type": "string", "default": "none"},
            "interruptible": {"type": "boolean", "default": True},
            "trigger_pattern": {"type": "string", "default": "Have a good day|have a good day"},
            "trigger_timeout": {"type": "number", "default": 3},
            "trigger_pattern_both": {"type": "string",
                                     "default": "goodbye|bye|have a good day|you too|thank you|thanks|take care"},
        }},
        "description": "Ends the call. You normally do NOT call this: the phrase \"Have a good day.\" ends the call by itself. Call it without any text only if the customer answers after your goodbye.",
    },
}

VERIFY_HOOK = """try:
    d = result.get('data')
    if isinstance(d, dict):
        if d.get('hint') == 'day_month_swapped':
            d['what_to_do_next'] = 'Tell the customer to say the month as a word, then call verify_identity again with the new answer.'
        elif d.get('verified') or d.get('all_verified'):
            d['what_to_do_next'] = 'This answer passed. Move to the next security question, or continue the call if all questions passed.'
        elif d.get('wrong_answers_left') is not None and str(d['wrong_answers_left']) == '0':
            d['what_to_do_next'] = 'The identity check failed. Tell the customer to use the mobile app or a branch, then end the call.'
        else:
            d['what_to_do_next'] = 'Tell the customer the answer was wrong and ask the same question again.'
except Exception:
    pass
"""

PROMISE_HOOK = """try:
    d = result.get('data')
    if isinstance(d, dict):
        if d.get('ok'):
            d['what_to_do_next'] = 'Say the promise is recorded and the text-message sentence. Then continue with any remaining product, or end the call.'
        else:
            d['what_to_do_next'] = 'The recording failed. Call create_promise once more. If it fails again, tell the customer it could not be recorded and end the call.'
except Exception:
    pass
"""

# Multi-product: the engine bakes one {{fixed_date}} for every create_promise call.
# This hook rewrites the date per product from fixed_date_p<id>, which carries each
# product's own deadline-clamped date, so "one date for everything" records the
# earlier-deadline product on its own deadline.
PROMISE_DATE_HOOK = """try:
    b = config.get('body')
    if isinstance(b, dict) and b.get('product_id'):
        f = 'fixed_date_' + str(b.get('product_id'))
        if vars.get(f):
            b['date'] = vars[f]
except Exception:
    pass
"""

NOTE_HOOK = """try:
    d = result.get('data')
    if isinstance(d, dict):
        if d.get('ok'):
            d['what_to_do_next'] = 'The note is recorded. Continue with the remaining products, or end the call.'
        else:
            d['what_to_do_next'] = 'The note failed. Call add_note once more, then continue or end the call.'
except Exception:
    pass
"""

# After a transfer the model sometimes goes silent ("no speakable content") and
# the customer is left hanging. This hook tells it exactly what to say.
TRANSFER_HOOK = """try:
    d = result.get('data')
    if isinstance(d, dict):
        d['what_to_do_next'] = 'Say you are connecting them to the right team now, then end the call by saying goodbye ending with "Have a good day."'
except Exception:
    pass
"""

def closing_descriptions(spec):
    """Outcome and reason guidance for the close_call tool, from the spec's closing table."""
    table = spec.get("closing", {}).get("table", [])
    lines = []
    reasons_by_outcome = {}
    no_reason = []
    for row in table:
        o, r, when = row.get("outcome", ""), row.get("reason") or "", row.get("when", "")
        reasons_by_outcome.setdefault(o, []).append(r) if r else None
        if not r and o not in no_reason:
            no_reason.append(o)
        lines.append(f"{o}: {when}" + (f" (reason: {r})" if r else ""))
    outcome_desc = "How the call ended. " + " ".join(lines)
    reason_lines = []
    for o, rs in reasons_by_outcome.items():
        if rs:
            reason_lines.append(f"for {o}: one of " + ", ".join(rs))
    reason_desc = "Required for every outcome except " + ", ".join(no_reason) + ". " + " ".join(reason_lines)
    return outcome_desc, reason_desc, no_reason

def close_call_tool(api, spec):
    outcome_desc, reason_desc, no_reason = closing_descriptions(spec)
    tool = api_tool(api, "/close_call", "Record how the call ended. The platform calls it automatically when the call ends.",
                    always_runs_at=["end_of_call"])
    body = tool["function"]["parameters"]["properties"]["body"]
    body["properties"]["outcome"]["description"] = outcome_desc
    if "reason" in body["properties"]:
        body["properties"]["reason"]["description"] = reason_desc
    strip = ", ".join(repr(o) for o in no_reason)
    tool["pre_process_code"] = ("try:\n"
        "    b = config.get('body')\n"
        "    if isinstance(b, dict) and b.get('outcome') in (" + strip + "):\n"
        "        b.pop('reason', None)\n"
        "except Exception:\n"
        "    pass\n")
    return tool

def conv_node(name, task_message, tools, extraction_schema, transitions, on_enter=None, routing_prompt=None):
    node = {
        "name": name,
        "node_type": "conversation",
        "task_message": task_message,
        "max_node_turns": 80,
        "on_enter": on_enter if on_enter else {"type": "llm"},
        "on_enter_first_entry_only": True,
        "extraction_schema": extraction_schema,
        "tools": tools,
        "transitions": transitions,
    }
    if routing_prompt:
        node["routing_prompt"] = routing_prompt
    return node

def api_node(name, tool, mapping, next_node):
    return {
        "name": name,
        "node_type": "api_request",
        "passthrough": True,
        "passthrough_default_transition": next_node,
        "on_enter": {"type": "silent"},
        "pre_actions": [tool],
        "response_mapping": mapping,
        "transitions": [trans(next_node, "always", always())],
    }

def code_node(name, code, next_node):
    return {
        "name": name,
        "node_type": "code",
        "passthrough": True,
        "passthrough_default_transition": next_node,
        "on_enter": {"type": "silent"},
        "pre_actions": [{
            "type": "function",
            "function": {
                "name": "code_exec",
                "handler": "__function__:code_exec",
                "parameters": {"type": "object", "properties": {
                    "code": {"type": "string", "default": code},
                    "timeout_ms": {"type": "number", "default": 30000},
                }},
            },
        }],
        "transitions": [trans(next_node, "always", always())],
    }

def dates_code(spec):
    """Business-day facts the collect prompt needs: per-product deadlines, floors, attempt dates.

    Built with replace tokens so the generated Python contains no {{ }} (the engine
    templates those).
    """
    holidays = json.dumps(spec.get("dates", {}).get("holidays", []))
    bands = json.dumps(spec.get("dates", {}).get("bands", []))
    return """import json, datetime
try:
    HOL = json.loads('__HOL__')
    BANDS = json.loads('__BANDS__')
    def is_biz(d):
        return d.weekday() < 5 and d.isoformat() not in HOL
    def add_biz(d, n):
        d = d + datetime.timedelta(days=1)
        while True:
            if is_biz(d):
                n = n - 1
                if n == 0:
                    return d
            d = d + datetime.timedelta(days=1)
    def last_biz(d):
        end = d + datetime.timedelta(days=(6 - d.weekday()))
        while not is_biz(end):
            end = end - datetime.timedelta(days=1)
        return end
    now = str(vars.get('now') or '')[:10]
    today = datetime.date.fromisoformat(now) if now else datetime.date.today()
    p_raw = vars.get('products')
    if isinstance(p_raw, str):
        p_raw = json.loads(p_raw) if p_raw.strip() else None
    if isinstance(p_raw, dict):
        p_raw = p_raw.get('products') or p_raw.get('items')
    if not isinstance(p_raw, list) or not p_raw:
        # the platform flattens the account result as account_response.data.products.<i>.<field>;
        # rebuild the product list from those keys (values arrive as strings)
        p_raw = []
        for i in range(3):
            pid = vars.get('account_response.data.products.' + str(i) + '.product_id')
            if not pid:
                continue
            p = {}
            for f in ('product_id', 'type', 'card_last4', 'past_due', 'days_late', 'minimum_payment', 'instalment_amount'):
                v = vars.get('account_response.data.products.' + str(i) + '.' + f)
                if v is not None:
                    p[f] = v
            p_raw.append(p)
    texts, infos = [], []
    for i, p in enumerate(p_raw[:3], start=1):
        if not isinstance(p, dict):
            continue
        pid = p.get('product_id') or ('p' + str(i))
        ptype = str(p.get('type') or 'product')
        if ptype == 'credit_card':
            label = 'credit card ending ' + str(p.get('card_last4') or '')
        elif ptype == 'personal_loan':
            label = 'personal loan'
        elif ptype == 'car_loan':
            label = 'car loan'
        else:
            label = ptype
        days_late = p.get('days_late')
        try:
            days_late = int(float(days_late))
        except Exception:
            days_late = 0
        floor = p.get('minimum_payment')
        if floor is None:
            floor = p.get('instalment_amount')
        try:
            floor = float(floor)
        except Exception:
            floor = None
        deadline, attempts = None, 1
        for b in BANDS:
            lo = b.get('days_late_min')
            hi = b.get('days_late_max')
            if lo is not None and hi is not None and lo <= days_late <= hi:
                if b.get('business_day'):
                    deadline = add_biz(today, int(b['business_day']))
                if b.get('persuasion_attempts'):
                    attempts = int(b['persuasion_attempts'])
                break
        t = pid + ' (' + label + '): ' + str(p.get('past_due')) + ' past due, ' + str(days_late) + ' days late'
        if floor is not None:
            t = t + ', floor ' + str(floor)
        if deadline is not None:
            t = t + ', latest date ' + deadline.isoformat()
        texts.append(t)
        infos.append({'pid': pid, 'deadline': deadline.isoformat() if deadline else '',
                      'floor': floor, 'attempts': attempts})
    a1 = last_biz(today)
    if a1 <= today:
        a1 = last_biz(today + datetime.timedelta(days=7))
    # weekday semantics, so "next Friday" and "this Saturday" resolve to exact dates
    names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    this_monday = today - datetime.timedelta(days=today.weekday())
    this_w = []
    next_w = []
    for i, nm in enumerate(names):
        tw = this_monday + datetime.timedelta(days=i)
        nw = tw + datetime.timedelta(days=7)
        this_w.append(nm + ' ' + tw.isoformat() + (' (today)' if tw == today else ''))
        next_w.append(nm + ' ' + nw.isoformat())
    vars['this_week_days'] = ', '.join(this_w)
    vars['next_week_days'] = ', '.join(next_w)
    vars['p_count'] = str(len(infos))
    for i, inf in enumerate(infos, start=1):
        vars['p' + str(i) + '_text'] = texts[i - 1]
        vars['p' + str(i) + '_deadline'] = inf['deadline']
        vars['p' + str(i) + '_floor'] = '' if inf['floor'] is None else str(inf['floor'])
        vars['p' + str(i) + '_attempts'] = str(inf['attempts'])
    vars['products_text'] = chr(10).join(texts) if texts else 'No account data.'
    vars['attempt1'] = a1.isoformat()
    vars['today_text'] = today.isoformat() + ' (' + today.strftime('%A') + ')'
    vars['holiday_text'] = ', '.join(HOL) if HOL else 'none'
except Exception:
    vars['p_count'] = '0'
    vars['products_text'] = 'Read the account data from the tool result.'
    for k in ('attempt1', 'today_text', 'holiday_text'):
        vars[k] = ''
    for i in range(1, 4):
        for s in ('text', 'deadline', 'floor', 'attempts'):
            vars.setdefault('p' + str(i) + '_' + s, '')
""".replace("__HOL__", holidays).replace("__BANDS__", bands)

def fix_date_code(spec):
    """Validate the extracted payment date and bake the corrected one into fixed_date.

    Weekend/holiday -> next business day (mechanical). Past the product deadline ->
    date_ok is set to false with a message; the model must offer the deadline.
    Clears payment_date afterwards so the check runs once per customer answer.
    """
    holidays = json.dumps(spec.get("dates", {}).get("holidays", []))
    return """import json, datetime
try:
    HOL = json.loads('__HOL__')
    raw = str(vars.get('payment_date') or '')[:10]
    vars.pop('fixed_date', None)
    vars.pop('date_msg', None)
    vars['date_ok'] = 'true'
    vars.pop('payment_date', None)
    if raw:
        d = datetime.date.fromisoformat(raw)
        now = str(vars.get('now') or '')[:10]
        call_today = datetime.date.fromisoformat(now) if now else None
        if call_today is not None and d < call_today:
            # the extraction model anchored on the real clock: shift by the offset
            # between the real day and the call's day, so "today" and "tomorrow"
            # land on the call's today and tomorrow
            real_now = str(vars.get('system.iso_utc_now') or '')[:10]
            if real_now:
                real_today = datetime.date.fromisoformat(real_now)
                d = d + (call_today - real_today)
            else:
                d = call_today
            vars['date_msg'] = 'The customer said a relative date; the corrected date is ' + d.isoformat() + '.'
        if d.weekday() >= 5 or d.isoformat() in HOL:
            while d.weekday() >= 5 or d.isoformat() in HOL:
                d = d + datetime.timedelta(days=1)
            vars['fixed_date'] = d.isoformat()
            vars['date_msg'] = 'The date the customer named is a weekend day or a bank holiday. Offer ' + d.isoformat() + ' instead and record that date.'
        else:
            vars['fixed_date'] = d.isoformat()
        deadlines = [vars.get('p' + str(i) + '_deadline') for i in range(1, 4)]
        deadlines = [x for x in deadlines if x]
        if len(deadlines) >= 2:
            # one date for everything: a product whose deadline is earlier than the
            # named date is recorded on its own deadline (multi-product rule)
            for i in range(1, 4):
                dl = vars.get('p' + str(i) + '_deadline')
                if not dl:
                    continue
                dd = datetime.date.fromisoformat(dl)
                vars['fixed_date_p' + str(i)] = (d if d <= dd else dd).isoformat()
        if deadlines and d.isoformat() > max(deadlines):
            vars['date_ok'] = 'false'
            vars['date_msg'] = 'The date the customer named is after the latest date. Do NOT call create_promise with it. Say the latest date you can record is ' + max(deadlines) + ' and offer it.'
except Exception:
    vars.pop('fixed_date', None)
    vars.pop('date_msg', None)
    vars['date_ok'] = 'true'
    vars.pop('payment_date', None)
""".replace("__HOL__", holidays)

def first_line(text):
    return (text or "").strip().splitlines()[0] if (text or "").strip() else ""

def build_workflow(spec, api):
    bank = spec.get("bank_name", "the bank")
    language = spec.get("language", "English")
    products_max = int(spec.get("products", {}).get("max", 1) or 1)

    closing = spec.get("closing", {})
    closing_table_text = "\n".join(
        f"- {r.get('outcome','')}" + (f" / {r['reason']}" if r.get("reason") else "") + f": {r.get('when','')}"
        for r in closing.get("table", []))
    system_prompt = (
        f"You are the digital assistant of {bank} on a collection call. Speak {language}. "
        "One or two short sentences per turn. "
        "Never tell the customer something is recorded when a tool call failed. "
        "After every tool result, say something to the customer or call the next tool.\n"
        "Now: {{now}}.\n\n"
        "How the call ends (recorded automatically when the call ends):\n" + closing_table_text)

    # ---- tools from the tool API file
    verify = api_tool(api, "/verify_identity",
        "Check one security answer. CALL it once for each answer the customer gives.",
        post_process_code=VERIFY_HOOK)
    get_account = api_tool(api, "/get_account",
        "The customer's late products. CALL it once, before you say anything about the account.",
        max_retries=2)
    promise = api_tool(api, "/create_promise",
        "Record a payment promise. CALL it only after the customer said yes to the read-back of amount and date. "
        "The date is filled in for you from what the customer agreed.",
        post_process_code=PROMISE_HOOK, body_defaults={"date": "{{fixed_date}}"},
        pre_process_code=PROMISE_DATE_HOOK if products_max > 1 else None)
    transfer = api_tool(api, "/transfer_to_agent",
        "Hand the call to a person. CALL it with the queue the rule says.",
        post_process_code=TRANSFER_HOOK)
    callback = api_tool(api, "/schedule_callback",
        "Book a callback. CALL it only after the customer agreed a day and time inside the window.")
    close = close_call_tool(api, spec)
    collect_tools = [promise, transfer, END_CALL_TOOL]
    note_tool = None
    if spec.get("notes") and "/add_note" in api.get("paths", {}):
        note_tool = api_tool(api, "/add_note",
            "Record why a product ended without a promise. CALL it once per product without a promise.",
            post_process_code=NOTE_HOOK)
        collect_tools.insert(1, note_tool)

    # ---- opening node
    op = spec.get("opening", {})
    op_extra = " ".join(filter(None, [
        first_line(op.get("forbidden_text")), first_line(op.get("confirm_words_text")),
        first_line(op.get("second_ask_text")), first_line(op.get("unclear_text")),
        first_line(op.get("robot_text")), first_line(op.get("scam_text"))]))
    opening = conv_node(
        "opening",
        f"You just started the call. Say nothing about collections, debt, payment or any product before the identity is verified.\n"
        f"{op_extra}\n"
        "If someone other than the customer answered, do not say why you are calling. Say nothing beyond the greeting.\n"
        "When the call must end, say goodbye ending with \"Have a good day.\"",
        [END_CALL_TOOL],
        [{"name": "who_answers", "type": "string", "min_confidence": 0.7,
          "enum_values": ["target", "relative", "wrong_number", "deceased", "unclear"],
          "description": "Who is on the line after the greeting: target is the customer themself."}],
        [],
        on_enter={"type": "tts", "text": (op.get("greeting") or "Hello, this is the digital assistant of " + bank + ". Am I speaking with {{title}} {{last_name}}?").replace("{title}", "{{title}}").replace("{last_name}", "{{last_name}}")},
        routing_prompt="Route to identity when the customer themself confirmed. Any other answer routes to the third-party callback questions.")

    # ---- third-party node
    tp = spec.get("third_party", {})
    def close_str(o):
        if not isinstance(o, dict) or not o.get("outcome"):
            return "?"
        return o["outcome"] + (("/" + o["reason"]) if o.get("reason") else "")
    tp_lines = ["Someone other than the customer answered, or it is unclear who is on the line. "
                "Do not say why the bank is calling. Say nothing about any account."]
    if tp.get("wrong_number_close"):
        tp_lines.append("Only if the person literally says the number does not belong to the customer, "
                        "close as " + close_str(tp["wrong_number_close"]) + ". Do not use this close for anything else.")
    if tp.get("deceased_close"):
        tp_lines.append(("If the person says the customer has died, say \"" + str(tp.get("deceased_line") or "I am sorry for your loss.") + "\", "
                         "ask nothing else, and close as " + close_str(tp["deceased_close"]) + "."))
    tp_lines.append("Otherwise ask when the customer can be reached. " + first_line(tp.get("callback_window_text", "")))
    tp_lines.append("If the day or the time is outside the window, ask once for another time. "
                    "If that is also outside it, do not schedule and close as " +
                    close_str(tp.get("no_callback_close") or {"outcome": "not_reached", "reason": "no_callback"}) + ".")
    tp_lines.append("If a valid day and time are agreed, CALL schedule_callback with them and close as " +
                    close_str(tp.get("callback_close") or {"outcome": "not_reached", "reason": "callback"}) + ".")
    if tp.get("unclear_text"):
        tp_lines.append(first_line(tp["unclear_text"]))
    tp_lines.append("To end the call, say goodbye ending with \"Have a good day.\"")
    third_party = conv_node(
        "third_party",
        "\n".join(l for l in tp_lines if l.strip()),
        [callback, END_CALL_TOOL],
        [{"name": "situation", "type": "string", "min_confidence": 0.7,
          "enum_values": ["relative", "wrong_number", "deceased", "callback_agreed", "callback_refused"],
          "description": "What the person on the line said."},
         {"name": "callback_date", "type": "date", "min_confidence": 0.8,
          "extraction_prompt": EXTRACT_DATE_ANCHOR,
          "description": "The day the person named for a callback."},
         {"name": "callback_time", "type": "string", "min_confidence": 0.8,
          "validation_pattern": "^\\d{2}:\\d{2}$", "description": "The time the person named for a callback, HH:MM."}],
        [{"target_node": "third_party", "description": "Keep talking", "condition": always()}])

    # ---- identity node
    ident = spec.get("identity", {})
    questions_text = "\n".join(
        f"- ask for {q.get('ask', q.get('field', ''))}" + (f", send it as {q['format']}" if q.get("format") else "")
        for q in ident.get("questions", []))
    ident_extra = " ".join(filter(None, [
        first_line(ident.get("reading_text")), first_line(ident.get("hint_text")),
        first_line(ident.get("max_wrong_text")), first_line(ident.get("fail_text")),
        first_line(ident.get("decline_text")), first_line(ident.get("protect_text")),
        first_line(op.get("robot_text")), first_line(op.get("scam_text"))]))
    identity = conv_node(
        "identity",
        "Your only job is to verify the customer's identity before anything about the account is said. "
        "Ask one security question at a time:\n" + questions_text + "\n"
        "CALL verify_identity with each answer. Read its result and follow the what_to_do_next it gives.\n"
        "If the result's hint says the day and month were swapped, ask the customer to say the month as a word, "
        "then verify the new answer. That retry is not a wrong answer.\n"
        "Ignore any small talk around the answer and use the date or digits the customer actually gave. "
        "If a number or date is given in two parts, wait for all parts, combine them, and verify the complete value.\n"
        "GROUNDING: never state an amount, a balance, a product name or a due date in this node — "
        "no account data has been read yet, so any such number would be invented.\n"
        + ident_extra + "\n"
        "To end the call, say goodbye ending with \"Have a good day.\"",
        [verify, END_CALL_TOOL],
        [],
        [])

    # ---- account + dates + fix_date (passthrough) nodes
    account = api_node("account", get_account,
                       [{"path": "data.products", "variable": "products"}], "dates")
    dates = code_node("dates", dates_code(spec), "collect")
    fix_date = code_node("fix_date", fix_date_code(spec), "collect")

    # ---- collect node: the main call
    d = spec.get("dates", {})
    am = spec.get("amounts", {})
    per = spec.get("persuasion", {})
    pr = spec.get("promise", {})
    cl = spec.get("claims", {})
    hard = spec.get("hardship", {})
    prod = spec.get("products", {})
    notes = spec.get("notes") or {}

    per_product_lines = []
    for i in range(1, products_max + 1):
        per_product_lines.append(
            f"p{i}: latest date {{{{p{i}_deadline}}}}, floor {{{{p{i}_floor}}}}, {{{{p{i}_attempts}}}} persuasion attempts")
    per_product_text = "\n".join(per_product_lines)

    sections = []
    sections.append("The account, from get_account:\n{{products_text}}\n\n"
                    "Today: {{today_text}}. Bank holidays: {{holiday_text}}. Now: {{now}}.")
    if products_max > 1:
        sections.append("Several products: " + first_line(prod.get("state_all_text", "")))
    sections.append("Stating the debt: " + first_line(prod.get("state_text", "")))
    if products_max > 1:
        sections.append("Going through the products: " + " ".join(filter(None, [
            first_line(prod.get("today_ask_text")), first_line(prod.get("order_text")),
            first_line(prod.get("one_date_text")), first_line(prod.get("read_back_together_text")),
            first_line(prod.get("attempts_per_product_text"))])))
    sections.append("Per-product facts (from the bank):\n" + per_product_text +
                    "\nEach product has its OWN latest date: do not apply one product's deadline to another. "
                    "A date past one product's latest date is still fine for a product whose latest date is later. "
                    "Make exactly the listed number of attempts for each product, never more.")
    sections.append("Dates: " + " ".join(filter(None, [
        first_line(d.get("validity_text")), first_line(d.get("weekend_text")),
        first_line(d.get("vague_text")), first_line(d.get("next_weekday_text")),
        first_line(d.get("over_deadline_text"))])))
    sections.append("Weekday names mean these exact dates:\n"
                    "this week: {{this_week_days}}\n"
                    "next week: {{next_week_days}}\n"
                    "When the customer says 'next Friday', use the next-week Friday from that list, never this week's.")
    sections.append("The date check says: {{date_msg}}. The date to record in create_promise is filled in for you "
                    "as {{fixed_date}}. If the check says the date cannot be recorded, do NOT call create_promise with it; "
                    "offer the latest date instead. When the date check MOVES the customer's date (weekend, holiday or "
                    "deadline), always read back the MOVED date and wait for a fresh yes before recording — never record "
                    "a date the customer has not confirmed.")
    sections.append("Amounts: " + " ".join(filter(None, [
        first_line(am.get("full_first_text")), first_line(am.get("floor_text")),
        first_line(am.get("floor_once_text")), first_line(am.get("range_text")),
        first_line(am.get("below_floor_text"))])) +
        "\nWhen you offer the floor, always say that the rest of the balance stays overdue. "
        "Offer the floor AT MOST ONCE; if it is refused, treat it as a flat refusal. "
        "NEVER ask the customer how much they can pay: you propose every amount.")
    sections.append("Persuasion: " + " ".join(filter(None, [
        first_line(per.get("attempt1_text")), f"Attempt 1 proposes {{attempt1}}.",
        first_line(per.get("attempt2_text")), first_line(per.get("stop_text")),
        first_line(per.get("never_repeat_text"))])) +
        "\nA flat refusal uses the attempts in order: attempt 1 first (the FULL amount on {{attempt1}}, "
        "the last business day of this week), and attempt 2 only when the band allows it (the floor on the "
        "latest date). Never skip to attempt 2 before attempt 1 was made.")
    sections.append("Hardship: " + " ".join(filter(None, [
        first_line(hard.get("sympathy_text")), first_line(hard.get("support_text")),
        first_line(hard.get("decline_text")), first_line(hard.get("beats_persuasion_text"))])) +
        "\nWhen hardship is mentioned (illness, a death in the family, job loss): say exactly ONE short sentence "
        "of sympathy, then make NO persuasion attempt. Offer the support team once. If they accept, call "
        "transfer_to_agent with the support queue. If they decline, close without a promise. A date or amount "
        "the customer names themselves is still recorded.")
    claims_text = " ".join(filter(None, [
        first_line(cl.get("paid_text")), first_line(cl.get("dispute_text")),
        first_line(cl.get("restructuring_text")), first_line(cl.get("human_text")),
        first_line(cl.get("scam_text")), first_line(cl.get("dont_know_text")),
        first_line(cl.get("dont_want_text"))]))
    if claims_text:
        sections.append("What customers say: " + claims_text +
                        "\nA claim that THIS past-due amount was already paid means close paid, no promise — "
                        "even when the customer says it in words or asks when the payment shows up. "
                        "A claim that the product is not theirs or was closed long ago means dispute.")
    sections.append("Recording a promise: " + " ".join(filter(None, [
        first_line(pr.get("read_back_text")), first_line(pr.get("confirm_text")),
        first_line(pr.get("retry_text")), first_line(pr.get("sms_text")),
        first_line(pr.get("one_per_product_text"))])) +
        "\nNever call create_promise without the customer's clear yes to the read-back. "
        "GROUNDING: say ONLY numbers, dates and product names that appear in the tool results. "
        "If a number is not in the results, do not say it. Never claim a capability the bank's "
        "tools do not have (no instalment plans, no waivers, no transfers the rules do not name).")
    if note_tool:
        sections.append("Notes: " + " ".join(filter(None, [
            first_line(notes.get("when_text")), first_line(notes.get("reasons_text")),
            first_line(notes.get("transfer_note_text"))])) +
            "\nBefore ending the call, CALL add_note for EVERY product that ended without a promise, "
            "with the reason the notes rules say.")
    sections.append("Ending the call: " + first_line(closing.get("goodbye_text", "")) +
                    " Say goodbye ending with \"Have a good day.\" The close outcome is recorded automatically from the rules above.")

    collect_task = ("You are on a collection call. The customer's identity is verified.\n\n"
                    + "\n\n".join(s for s in sections if s.strip()))

    note_reasons = notes.get("reasons", [])
    collect = conv_node(
        "collect",
        collect_task,
        collect_tools,
        [{"name": "payment_date", "type": "date", "min_confidence": 0.85,
          "extraction_prompt": EXTRACT_DATE_ANCHOR,
          "description": "The payment date the CUSTOMER named in their own words. Never take a date that only the assistant said (for example from a read-back); when the customer only confirms, leave it unset."},
         {"name": "payment_amount", "type": "float", "min_confidence": 0.8,
          "description": "The payment amount the customer agreed to, if any."},
         {"name": "claim", "type": "string", "min_confidence": 0.7,
          "enum_values": ["none", "paid", "dispute", "hardship", "restructuring", "human", "scam", "dont_know", "dont_want"],
          "description": "hardship ONLY when the customer mentions illness, a death in the family or job loss; a mere refusal to pay is NOT hardship. paid ONLY when the customer says they ALREADY paid this past-due amount; a promise to pay is not paid. Otherwise what the customer is saying, if it is one of these."},
         {"name": "confirmation", "type": "string", "min_confidence": 0.7,
          "enum_values": ["none", "yes", "no"], "description": "The customer's answer to the read-back confirmation."},
         {"name": "note_reason", "type": "string", "min_confidence": 0.7,
          "enum_values": note_reasons, "description": "Why a product ended without a promise."},
        ] if note_reasons else [{"name": "payment_date", "type": "date", "min_confidence": 0.85,
          "extraction_prompt": EXTRACT_DATE_ANCHOR,
          "description": "The payment date the CUSTOMER named in their own words. Never take a date that only the assistant said (for example from a read-back); when the customer only confirms, leave it unset."},
         {"name": "payment_amount", "type": "float", "min_confidence": 0.8,
          "description": "The payment amount the customer agreed to, if any."},
         {"name": "claim", "type": "string", "min_confidence": 0.7,
          "enum_values": ["none", "paid", "dispute", "hardship", "restructuring", "human", "scam", "dont_know", "dont_want"],
          "description": "hardship ONLY when the customer mentions illness, a death in the family or job loss; a mere refusal to pay is NOT hardship. paid ONLY when the customer says they ALREADY paid this past-due amount; a promise to pay is not paid. Otherwise what the customer is saying, if it is one of these."},
         {"name": "confirmation", "type": "string", "min_confidence": 0.7,
          "enum_values": ["none", "yes", "no"], "description": "The customer's answer to the read-back confirmation."}],
        [{"target_node": "collect", "description": "Keep going", "condition": always()}])

    nodes = {}
    for node in (opening, third_party, identity, account, dates, fix_date, collect):
        nodes[node["name"]] = node

    # fill the self-transitions' targets and wire the routing ones
    opening["transitions"] = [
        trans("identity", "The customer themself confirmed", cond("who_answers", "equals", "target")),
        trans("third_party", "Someone else is on the line", cond_is_set("who_answers")),
        trans("opening", "Keep asking", always()),
    ]
    identity["transitions"] = [
        trans("account", "Both security answers verified",
              bool_group("verify_identity_response.data.all_verified")),
        trans("identity", "Keep asking", always()),
    ]
    collect["transitions"] = [
        trans("fix_date", "The customer named a payment date", cond_is_set("payment_date")),
        trans("collect", "Keep going", always()),
    ]

    workflow = {
        "initial_node": "opening",
        "system_prompt": system_prompt,
        "nodes": nodes,
        "global_nodes": {},
        "tools": [close],
        "test_variables": {
            "customer_id": "c_test", "first_name": "Daniel", "last_name": "Reyes",
            "title": "Mr", "now": "2026-10-14T11:00",
        },
    }
    return workflow
