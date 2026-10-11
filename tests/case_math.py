"""Shared deterministic helpers for generating test cases.

All date math follows brief-a: business days Mon-Fri except the bank holidays,
deadlines on the 12th (1-7 days late) or 7th (8-45) business day after the fixed
practice date. The generators must never let an LLM do this math.
"""
import datetime

HOL = ["2026-10-26", "2026-11-11", "2026-11-26", "2026-12-25", "2027-01-01"]
NOW = datetime.date(2026, 10, 14)  # Wednesday, the fixed practice date

def is_biz(d):
    return d.weekday() < 5 and d.isoformat() not in HOL

def add_biz(d, n):
    d += datetime.timedelta(days=1)
    while True:
        if is_biz(d):
            n -= 1
            if n == 0:
                return d
        d += datetime.timedelta(days=1)

def deadline_of(days_late):
    """Per brief-a: 12th business day (1-7 days late), 7th (8-45)."""
    band = 12 if 1 <= days_late <= 7 else 7
    return add_biz(NOW, band)

def band_of(days_late):
    """'early' (1-7, one persuasion attempt) or 'late' (8-45, two attempts)."""
    return ("early", 1) if 1 <= days_late <= 7 else ("late", 2)

def next_biz(d):
    return add_biz(d, 1)

def floor_of(p):
    return p.get("minimum_payment", p.get("instalment_amount"))

def full_of(p):
    return p["past_due"]

def promise(pid, amount, date):
    return {"product_id": pid, "amount": round(float(amount), 2),
            "date": date.isoformat() if isinstance(date, datetime.date) else date}

def expected_close(outcome, reason=None, promises=(), notes=(), callbacks=(), transfers=()):
    return {"outcome": outcome, "reason": reason, "promises": list(promises),
            "notes": list(notes), "callbacks": list(callbacks), "transfers": list(transfers)}
