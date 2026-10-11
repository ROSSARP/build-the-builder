#!/usr/bin/env python3
"""
mock_matrix_test.py -- diversified local test suite for the LIVE final-case mock.

Target : https://final-case-mock-bank.fcodefcode3.workers.dev
Truth  : finalcase/test-environment/test-customers.json (the mock serves it verbatim)
Scope  : MOCK layer only -- no platform, no LLM. Finds data / serving defects
         across ALL 34 customers.

Covers (see task spec):
  1. per-customer sweep: cards.list, cards.balance, statement.week.get,
     statement.week.decide (week as number AND string), statement.week.change
     (week as number AND string), contact.email.get (intAddressInfoType "E"),
     statement.pdf.send (present -> verbatim, absent -> 404 FB_IVR_CHANNEL_107).
     customerNo is sent both as the file's string form and as a JSON number.
  2. error paths: missing customerNo / unknown customer / unknown card /
     unknown week / empty intAddressInfoType / unknown path (+ extra contract
     checks for missing cardNumber and missing newStatementWeek).
  3. flat body vs {"data": ...} envelope for cards.list -> same entry.
  4. template variable customerNo "{{customerNumber}}" -> first customer entry.
  5. compact report; exit 0 on PASS, 1 on any mismatch.

Stdlib only. Usage:
  python3 tests/mock_matrix_test.py [--base-url URL] [--customers PATH]
                                    [--workers N] [--timeout SECONDS] [--verbose]
"""
import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
DEFAULT_BASE = "https://final-case-mock-bank.fcodefcode3.workers.dev"
DEFAULT_CUSTOMERS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..",
    "finalcase", "test-environment", "test-customers.json")

P = "/voice/v1"
MISSING = "<missing>"


# ---------------------------------------------------------------- HTTP client
def http_request(base, path, payload, timeout, method="POST"):
    """Return dict(status, body, body_error, error, elapsed)."""
    url = base.rstrip("/") + path
    headers = {"User-Agent": UA, "Accept": "application/json"}
    data = None
    if method == "POST":
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            code = resp.status
    except urllib.error.HTTPError as e:      # 4xx/5xx still carry a body
        try:
            raw = e.read()
        except Exception:
            raw = b""
        code = e.code
    except Exception as e:                   # DNS / TLS / timeout / reset
        return {"status": None, "body": None, "body_error": None,
                "error": "%s: %s" % (type(e).__name__, e),
                "elapsed": time.time() - t0}
    elapsed = time.time() - t0
    try:
        body = json.loads(raw.decode("utf-8"))
        body_error = None
    except Exception as e:
        body = None
        body_error = "non-JSON body (%s): %s" % (e, raw[:200].decode("utf-8", "replace"))
    return {"status": code, "body": body, "body_error": body_error,
            "error": None, "elapsed": elapsed}


# ---------------------------------------------------------------- diff helpers
def first_diff(a, b, path=""):
    """Return (path, a_value, b_value) at the first JSON difference, else None."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k not in b:
                return (path + "/" + str(k), a[k], MISSING)
            r = first_diff(a[k], b[k], path + "/" + str(k))
            if r:
                return r
        for k in b:
            if k not in a:
                return (path + "/" + str(k), MISSING, b[k])
        return None
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return (path, "len=%d" % len(a), "len=%d" % len(b))
        for i, (x, y) in enumerate(zip(a, b)):
            r = first_diff(x, y, path + "/%d" % i)
            if r:
                return r
        return None
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and \
            not isinstance(a, bool) and not isinstance(b, bool):
        if a != b:
            return (path or "/", a, b)
        return None
    if type(a) is not type(b):
        return (path or "/", a, b)
    if a != b:
        return (path or "/", a, b)
    return None


def js(o, n=200):
    """Compact JSON preview, first n chars."""
    try:
        s = json.dumps(o, ensure_ascii=False, sort_keys=True)
    except Exception:
        s = repr(o)
    return s if len(s) <= n else s[:n] + "..."


def dig(o, *keys):
    for k in keys:
        if not isinstance(o, dict) or k not in o:
            return None
        o = o[k]
    return o


# ---------------------------------------------------------------- job model
def job(customer, service, label, path, payload, expect_status,
        expect_body=None, expect_code=None, note=None, extra=False):
    return {"customer": customer, "service": service, "label": label,
            "path": path, "payload": payload, "expect_status": expect_status,
            "expect_body": expect_body, "expect_code": expect_code,
            "note": note, "extra": extra}


def run_job(j, base, timeout):
    """Execute one job; return (job, checks, result) where checks is a list of
    (ok, assertion_name, detail) tuples."""
    r = http_request(base, j["path"], j["payload"], timeout)
    checks = []
    tag = j["label"]
    if r["error"]:
        checks.append((False, "request", "transport error: %s" % r["error"]))
        return j, checks, r
    ok = (r["status"] == j["expect_status"])
    checks.append((ok, "status", "" if ok else "expected HTTP %s, got %s"
                   % (j["expect_status"], r["status"])))
    if j["expect_body"] is not None:
        if r["body_error"]:
            checks.append((False, "body", r["body_error"]))
        elif r["body"] != j["expect_body"]:
            d = first_diff(j["expect_body"], r["body"])
            detail = ""
            if d:
                detail = "first diff at %s: expected=%s got=%s | " % (
                    d[0], js(d[1], 80), js(d[2], 80))
            detail += "expected(%d): %s | got(%d): %s" % (
                j["expect_status"], js(j["expect_body"]),
                r["status"], js(r["body"]))
            checks.append((False, "body", detail))
        else:
            checks.append((True, "body", ""))
    if j["expect_code"] is not None:
        got_code = dig(r["body"], "result", "code")
        got_rc = dig(r["body"], "result", "returnCode")
        ok = (got_code == j["expect_code"] and got_rc == j["expect_code"])
        checks.append((ok, "code", "" if ok else
                       "expected result.code/returnCode=%s, got code=%s returnCode=%s"
                       % (j["expect_code"], js(got_code, 60), js(got_rc, 60))))
    return j, checks, r


# ---------------------------------------------------------------- job builder
def build_jobs(customers):
    jobs = []
    for c in customers:
        cno = c["customerNo"]
        s = c.get("services", {})
        cards_entry = s.get("cards.list")

        # -- cards.list (string and numeric customerNo) --------------------
        if cards_entry:
            jobs.append(job(cno, "cards.list", "cards.list c=%s (string)" % cno,
                            P + "/cards.list", {"customerNo": cno},
                            cards_entry["http"], cards_entry["response"]))
            jobs.append(job(cno, "cards.list", "cards.list c=%s (number)" % cno,
                            P + "/cards.list", {"customerNo": int(cno)},
                            cards_entry["http"], cards_entry["response"]))

        # -- cards.balance / statement.week.get (keyed by masked card) -----
        for svc, path in (("cards.balance", P + "/cards.balance"),
                          ("statement.week.get", P + "/statement.week.get")):
            for card, entry in (s.get(svc) or {}).items():
                note = None
                if entry.get("delaySeconds"):
                    note = ("delaySeconds=%s declared for %s %s -- latency allowed"
                            % (entry["delaySeconds"], svc, card))
                jobs.append(job(cno, svc, "%s c=%s card=%s" % (svc, cno, card),
                                path, {"cardNumber": card},
                                entry["http"], entry["response"], note=note))

        # -- decide / change: every card x every week x (number,string) ----
        for svc, path in (("statement.week.decide", P + "/statement.week.decide"),
                          ("statement.week.change", P + "/statement.week.change")):
            for card, weeks in (s.get(svc) or {}).items():
                for wk, entry in weeks.items():
                    for variant, value in (("num", int(wk)), ("str", wk)):
                        jobs.append(job(
                            cno, svc,
                            "%s c=%s card=%s week=%s(%s)" % (svc, cno, card, wk, variant),
                            path, {"cardNumber": card, "newStatementWeek": value},
                            entry["http"], entry["response"]))

        # -- contact.email.get (string + numeric customerNo) ---------------
        email_entry = s.get("contact.email.get")
        if email_entry:
            jobs.append(job(cno, "contact.email.get",
                            "contact.email.get c=%s (string)" % cno,
                            P + "/contact.email.get",
                            {"customerNo": cno, "intAddressInfoType": "E"},
                            email_entry["http"], email_entry["response"]))
            jobs.append(job(cno, "contact.email.get",
                            "contact.email.get c=%s (number)" % cno,
                            P + "/contact.email.get",
                            {"customerNo": int(cno), "intAddressInfoType": "E"},
                            email_entry["http"], email_entry["response"]))

        # -- statement.pdf.send (present -> verbatim; absent -> 404 107) ---
        pdf_entry = s.get("statement.pdf.send")
        first_card = None
        if cards_entry and cards_entry["http"] == 200:
            cards = dig(cards_entry["response"], "data", "cards") or []
            if cards:
                first_card = cards[0].get("cardNumber")
        body = {"customerNo": cno}
        if first_card:
            body["cardNumber"] = first_card
            body["statementWeek"] = 2
        if pdf_entry:
            jobs.append(job(cno, "statement.pdf.send", "statement.pdf.send c=%s" % cno,
                            P + "/statement.pdf.send", body,
                            pdf_entry["http"], pdf_entry["response"]))
        else:
            jobs.append(job(cno, "statement.pdf.send",
                            "statement.pdf.send c=%s (absent -> 107)" % cno,
                            P + "/statement.pdf.send", body,
                            404, None, expect_code="FB_IVR_CHANNEL_107"))
    return jobs


def build_error_jobs(customers, known_cards):
    """Error-path jobs. required=True for the ones the task spec names."""
    c0 = customers[0]
    cno0 = c0["customerNo"]
    card0 = known_cards[0]
    unknown_cno = "99999999"
    assert unknown_cno not in {c["customerNo"] for c in customers}
    unknown_card = "999999******9999"
    assert unknown_card not in known_cards
    jobs = [
        # --- required by spec ---
        job("-", "cards.list", "ERR cards.list missing customerNo",
            P + "/cards.list", {}, 400, None, expect_code="INVALID_ARGUMENTS_ERROR"),
        job("-", "cards.list", "ERR cards.list unknown customer %s" % unknown_cno,
            P + "/cards.list", {"customerNo": unknown_cno}, 404, None,
            expect_code="FB_IVR_CHANNEL_102"),
        job("-", "cards.balance", "ERR cards.balance unknown card",
            P + "/cards.balance", {"cardNumber": unknown_card}, 404, None,
            expect_code="FB_IVR_CHANNEL_120"),
        job("-", "statement.week.get", "ERR week.get unknown card",
            P + "/statement.week.get", {"cardNumber": unknown_card}, 404, None,
            expect_code="FB_IVR_CHANNEL_121"),
        job("-", "statement.week.decide", "ERR decide unknown week 9",
            P + "/statement.week.decide",
            {"cardNumber": card0, "newStatementWeek": 9}, 400, None,
            expect_code="INVALID_ARGUMENTS_ERROR"),
        job("-", "contact.email.get", "ERR email empty intAddressInfoType",
            P + "/contact.email.get",
            {"customerNo": cno0, "intAddressInfoType": ""}, 400, None,
            expect_code="INVALID_ARGUMENTS_ERROR"),
        job("-", "unknown", "ERR unknown path -> 404",
            "/voice/v1/no.such.service", {}, 404, None),
        # --- extra contract coverage (contract facts: missing field -> 400) ---
        job("-", "cards.balance", "ERR cards.balance missing cardNumber [extra]",
            P + "/cards.balance", {}, 400, None,
            expect_code="INVALID_ARGUMENTS_ERROR", extra=True),
        job("-", "statement.week.get", "ERR week.get missing cardNumber [extra]",
            P + "/statement.week.get", {}, 400, None,
            expect_code="INVALID_ARGUMENTS_ERROR", extra=True),
        job("-", "statement.week.decide", "ERR decide missing newStatementWeek [extra]",
            P + "/statement.week.decide", {"cardNumber": card0}, 400, None,
            expect_code="INVALID_ARGUMENTS_ERROR", extra=True),
        job("-", "statement.week.change", "ERR change unknown week 9 [extra]",
            P + "/statement.week.change",
            {"cardNumber": card0, "newStatementWeek": 9}, 400, None,
            expect_code="INVALID_ARGUMENTS_ERROR", extra=True),
        job("-", "contact.email.get", "ERR email unknown customer [extra]",
            P + "/contact.email.get",
            {"customerNo": unknown_cno, "intAddressInfoType": "E"}, 400, None,
            expect_code="INVALID_ARGUMENTS_ERROR", extra=True),
        job("-", "statement.pdf.send", "ERR pdf.send missing customerNo [extra]",
            P + "/statement.pdf.send", {}, 400, None,
            expect_code="INVALID_ARGUMENTS_ERROR", extra=True),
    ]
    return jobs


# ---------------------------------------------------------------- reporting
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-url", default=os.environ.get("MOCK_BASE_URL", DEFAULT_BASE))
    ap.add_argument("--customers", default=DEFAULT_CUSTOMERS)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--verbose", action="store_true",
                    help="also print one OK line per customer")
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    with open(args.customers, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    customers = data["customers"]
    known_cards = []
    for c in customers:
        s = c.get("services", {})
        for svc in ("cards.balance", "statement.week.get",
                    "statement.week.decide", "statement.week.change"):
            for k in (s.get(svc) or {}):
                if k not in known_cards:
                    known_cards.append(k)

    print("=== mock_matrix_test: final-case mock layer ===")
    print("target:    %s" % base)
    print("truth:     %s" % os.path.normpath(args.customers))
    print("customers: %d   workers: %d   timeout: %.0fs"
          % (len(customers), args.workers, args.timeout))

    # -- preflight: /health (browser UA) --------------------------------
    h = http_request(base, "/health", None, args.timeout, method="GET")
    preflight_fail = None
    if h["error"]:
        preflight_fail = "transport error: %s" % h["error"]
    elif h["status"] != 200 or dig(h["body"], "ok") is not True:
        preflight_fail = "expected 200 {ok:true...}, got %s %s" % (h["status"], js(h["body"]))
    if preflight_fail:
        print("\nFAIL: /health preflight failed -- %s" % preflight_fail)
        return 1
    health_customers = dig(h["body"], "customers")
    health_warn = None
    if health_customers != len(customers):
        health_warn = ("health reports customers=%s, truth file has %d"
                       % (health_customers, len(customers)))
    print("health:    OK (%s)%s" % (js(h["body"], 120),
                                    "  WARN: " + health_warn if health_warn else ""))

    jobs = build_jobs(customers) + build_error_jobs(customers, known_cards)

    # -- run the matrix (threaded; results kept in job order) -----------
    results = [None] * len(jobs)
    done = [0]
    lock = threading.Lock()

    def worker(idx_j):
        idx, j = idx_j
        out = run_job(j, base, args.timeout)
        results[idx] = out
        with lock:
            done[0] += 1
            if done[0] % 100 == 0 or done[0] == len(jobs):
                sys.stderr.write("\r  ... %d/%d requests" % (done[0], len(jobs)))
                sys.stderr.flush()

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        list(ex.map(worker, list(enumerate(jobs))))
    sys.stderr.write("\n")

    # -- post-run cross checks: flat vs wrapped, template variable ------
    c0 = customers[0]
    lst0 = c0["services"]["cards.list"]
    cno0 = c0["customerNo"]
    r_flat = http_request(base, P + "/cards.list", {"customerNo": cno0}, args.timeout)
    r_wrap = http_request(base, P + "/cards.list", {"data": {"customerNo": cno0}}, args.timeout)
    r_tpl = http_request(base, P + "/cards.list", {"customerNo": "{{customerNumber}}"}, args.timeout)
    r_tpl_enc = http_request(base, P + "/cards.list",
                             {"customerNo": "%7B%7BcustomerNumber%7D%7D"}, args.timeout)

    special = []          # (label, ok, detail)
    def check_simple(label, r, status, body=None, code=None):
        if r["error"]:
            special.append((label, False, "transport error: %s" % r["error"]))
            return
        if r["status"] != status:
            special.append((label, False, "expected HTTP %s, got %s | %s"
                            % (status, r["status"], js(r["body"]))))
            return
        if body is not None and r["body"] != body:
            d = first_diff(body, r["body"])
            special.append((label, False, "first diff at %s | expected(200): %s | got(200): %s"
                            % ((d[0] if d else "?"), js(body), js(r["body"]))))
            return
        if code is not None and dig(r["body"], "result", "code") != code:
            special.append((label, False, "expected result.code=%s, got %s"
                            % (code, js(r["body"], 150))))
            return
        special.append((label, True, ""))

    check_simple("flat body cards.list -> file entry", r_flat, lst0["http"], lst0["response"])
    check_simple("wrapped {data:...} cards.list -> file entry", r_wrap, lst0["http"], lst0["response"])
    if r_flat["body"] is not None and r_wrap["body"] is not None:
        ok = r_flat["body"] == r_wrap["body"]
        special.append(("flat vs wrapped bodies identical", ok,
                        "" if ok else "flat=%s wrapped=%s"
                        % (js(r_flat["body"], 150), js(r_wrap["body"], 150))))
    else:
        special.append(("flat vs wrapped bodies identical", False, "no body to compare"))
    check_simple('template customerNo "{{customerNumber}}" -> first customer entry',
                 r_tpl, lst0["http"], lst0["response"])
    check_simple('extra: encoded template "%7B%7BcustomerNumber%7D%7D"',
                 r_tpl_enc, lst0["http"], lst0["response"])

    # -- aggregate -------------------------------------------------------
    total_assertions = len(special)
    failures = []         # (customer, service, label, detail)
    ok_by_customer = {}
    notes = []
    transport_errors = 0
    for j, checks, r in results:
        n_ok = sum(1 for c in checks if c[0])
        total_assertions += len(checks)
        ok_by_customer.setdefault(j["customer"], [0, 0])
        ok_by_customer[j["customer"]][1] += len(checks)
        ok_by_customer[j["customer"]][0] += n_ok
        if j["note"]:
            notes.append("NOTE %s -- %s (responded in %.1fs)"
                         % (j["label"], j["note"], r["elapsed"]))
        if r["error"]:
            transport_errors += 1
        for ok, name, detail in checks:
            if not ok:
                failures.append((j["customer"], j["service"], j["label"],
                                 "%s: %s" % (name, detail), j["extra"]))
    for label, ok, detail in special:
        if not ok:
            failures.append(("-", "cross-check", label, detail, "extra" in label))

    # -- report ----------------------------------------------------------
    print("requests:  %d (matrix %d + cross-checks 4)"
          % (len(jobs) + 4, len(jobs)))
    print("assertions: %d" % total_assertions)
    if transport_errors:
        print("transport errors: %d" % transport_errors)
    for n in dict.fromkeys(notes):
        print(n)
    print("")

    if args.verbose:
        for cno in sorted(ok_by_customer):
            o, t = ok_by_customer[cno]
            print("  customer %s: %d/%d %s" % (cno, o, t, "OK" if o == t else "FAIL"))
        print("")

    if failures:
        by_cust = {}
        for f in failures:
            by_cust.setdefault(f[0], []).append(f)
        print("FAILURES: %d assertion(s) across %d customer(s)"
              % (len(failures), len(by_cust)))
        for cno in sorted(by_cust):
            print(" customer %s:" % cno)
            for _, svc, label, detail, extra in by_cust[cno]:
                print("   [%s] %s%s" % (svc, label, " [extra]" if extra else ""))
                print("     %s" % (detail[:400]))
        print("")
        extra_fails = sum(1 for f in failures if f[4])
        print("RESULT: FAIL -- %d failing assertion(s)%s"
              % (len(failures),
                 " (%d in extra/out-of-spec checks)" % extra_fails if extra_fails else ""))
        return 1

    print("RESULT: PASS -- %d/%d assertions OK across all %d customers"
          % (total_assertions, total_assertions, len(customers)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
