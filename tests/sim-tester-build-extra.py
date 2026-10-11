#!/usr/bin/env python3
"""sim-tester: the two gap probes the six official examples do not cover.

  probe-ncut    (R3, no-statement-yet): reuses the PRE-AUTHORED s8_no_cut script from
                tests/final-scenarios.json (customer 97631186, Arda Bulut). Fixture:
                statementDate "", totalDebt 860.4 TL, first cut 05.11.2026.
  probe-cutday  (R4b, cut-day totalDebt): AUTHORED by sim-tester (no prepared scenario
                exists — disclosed here). Same customer, call "now" set to the cut day
                05.11.2026 via a test_variables.now override in a dedicated harness copy.
                Decisive: statementDebt 0 vs totalDebt 860.4 — if the agent reads the
                statement fields instead of totalDebt it says 0 / "no debt".

Outputs: tests/sim-tester-cases-p1-extra.json, tests/sim-tester-wf-p1-cutday.json
"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

sc = {s["id"]: s for s in json.loads((ROOT / "tests" / "final-scenarios.json").read_text())["scenarios"]}
s8 = sc["s8_no_cut"]
NO = s8["customerNumber"]            # 97631186
WHO = s8["who"]                      # Arda Bulut
first, last = WHO.split(" ", 1)

probe_ncut = {
    "id": NO,
    "brief": "sim-tester R3 probe from pre-authored tests/final-scenarios.json s8_no_cut",
    "family": "Edge", "level": "medium",
    "title": s8["title"],
    "variables": {"first_name": first, "last_name": last, "customerNumber": NO},
    "identity": {}, "products": [],
    "script": ("Sen aradın; asistan Türkçe konuşuyor, sen Türkçe konuş. "
               + s8["script"]),
    "expected": {"outcome": "no_promise", "reason": "refused",
                 "promises": [], "notes": [], "callbacks": [], "transfers": []},
    "checks": [
        "Asistan kartta henüz kesilmiş bir ekstre olmadığını söyler ('henüz kesilmiş bir ekstresi olmadığı' kalıbı) ve ekstre borcu bulunmadığını belirtir.",
        "Asistan ilk hesap kesim tarihini 5 Kasım 2026 (05.11.2026) olarak söyler ve başka bir ekstre/kesim tarihi UYDURMAZ.",
        "Müşteriye başka bir kartının borcu sorulmaz (tek kart) ve uydurma borç tutarı söylenmez.",
    ],
}

probe_cutday = {
    "id": NO,
    "brief": "sim-tester AUTHORED R4b probe: cut-day call, totalDebt 860.4 vs statementDebt 0 (fixture check via cards.balance probe 2026-10-11)",
    "family": "Edge", "level": "hard",
    "title": "Cut day: total debt per currency must be read (rule 4)",
    "variables": {"first_name": first, "last_name": last, "customerNumber": NO},
    "identity": {}, "products": [],
    "script": ("Bugün hesap kesim gününüz (5 Kasım 2026). Kartınızın bugün kesilen ekstresiyle birlikte TOPLAM "
               "borcunuzu öğrenmek istiyorsunuz. 'Alo' deyin, 'Bugün hesap kesim günüm, kartımın toplam borcunu "
               "öğrenmek istiyorum' deyin. Borç okununca 'Anladım, teşekkürler' deyin. Size başka bir şey "
               "önerilirse 'Hayır, teşekkürler' deyin."),
    "expected": {"outcome": "no_promise", "reason": "refused",
                 "promises": [], "notes": [], "callbacks": [], "transfers": []},
    "checks": [
        "Asistan hesap kesim tarihinin bugün olduğunu söyler ('Hesap kesim tarihiniz bugün' kalıbı).",
        "Asistan TOPLAM borcu 860,40 Türk Lirası olarak okur (toplam borç). Asistan 'borç yok' veya '0' derse bu başarısızlıktır: kartın toplam borcu 860,4 TL'dir, sadece bugün kesilen ekstrenin borcu 0'dır.",
        "Asistan TL dışındaki para birimleri (Dolar, Euro, İngiliz Sterlini) için borç olmadığını tek cümlede, para birimlerinin tam adlarıyla söyler.",
    ],
}

(ROOT / "tests" / "sim-tester-cases-p1-extra.json").write_text(
    json.dumps([probe_ncut, probe_cutday], ensure_ascii=False, indent=1))

base = (ROOT / "tests" / "sim-tester-wf-p1.json").read_text()
OLD_NOW = "2026-10-12T10:30:00+03:00"
NEW_NOW = "2026-11-05T10:30:00+03:00"
n = base.count(OLD_NOW)
(ROOT / "tests" / "sim-tester-wf-p1-cutday.json").write_text(base.replace(OLD_NOW, NEW_NOW))
print("extra cases written (ids:", NO, "); now-override replacements (expect 1):", n)
