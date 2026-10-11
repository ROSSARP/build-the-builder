#!/usr/bin/env python3
"""Watch the Freya hackathon page (https://www.freyavoice.ai/hackathon) for
content changes, per section: #rules and #submit (plus the whole page).

Prints one line per detected change:
    CHANGE: rules section
    CHANGE: submit section
    CHANGE: page (outside watched sections)
    FAIL: <reason>        (transient fetch error, retried next cycle)
    WARN: <reason>
State lives in out/hackathon-watch.json ({section: sha256, checked_at}) so any
session can read the last-seen hashes.

Usage:
    python3 tests/page_watch.py --once
    python3 tests/page_watch.py            # poll every 120 s until killed
    python3 tests/page_watch.py --interval 60
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
URL = "https://www.freyavoice.ai/hackathon"
STATE = ROOT / "out" / "hackathon-watch.json"
SECTIONS = ("rules", "submit")


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": "build-the-builder page-watch"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def section_hash(html, sid):
    m = re.search(rf'<section\s+class="pane"\s+id="{sid}">(.*?)</section>', html, re.S)
    if not m:
        return None
    return hashlib.sha256(re.sub(r"\s+", "", m.group(1)).encode("utf-8")).hexdigest()


def check_once():
    try:
        html = fetch()
    except Exception as e:  # noqa: BLE001 - transient network issues are the norm
        print(f"FAIL: {URL} ({e})")
        return 1
    page_h = hashlib.sha256(re.sub(r"\s+", "", html).encode("utf-8")).hexdigest()
    cur = {"page": page_h}
    for sid in SECTIONS:
        h = section_hash(html, sid)
        if h is None:
            print(f"WARN: section #{sid} not found in page")
        else:
            cur[sid] = h

    old = {}
    if STATE.exists():
        try:
            old = json.loads(STATE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    if old:
        if old.get("page") != page_h:
            print("CHANGE: page (outside watched sections)")
        for sid in SECTIONS:
            if sid in cur and old.get(sid) != cur[sid]:
                print(f"CHANGE: {sid} section")

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({**cur, "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                                ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Watch the Freya hackathon page for changes")
    ap.add_argument("--once", action="store_true", help="check once and exit")
    ap.add_argument("--interval", type=int, default=120, help="poll seconds (default 120)")
    a = ap.parse_args()

    if a.once:
        sys.exit(check_once())
    while True:
        check_once()
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
