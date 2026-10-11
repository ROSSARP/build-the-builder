# gen_query.py workflow generator (final case, query domain)

LIVE-END: gen-query-generator (ac778d9e574805f01) — handing off, generator work complete

## 21:06 (18:06 UTC) — final verification + handoff
OWN-RELEASED: builder/gen_query.py — released; the orchestrator session holds the live OWN claim
(cf-mock-session) and edited the file at 21:03:33/21:03:46 (mandatory sentences moved out of
system_prompt, example-name placeholder in _tr_spoken_only). Verified green on those exact bytes
(md5 7fd060e40ec6d3a6d6351bb40b4282cb, 160409 B):
DONE:
- `python3 -I gen_query.py` with builder/gen.py alongside: SELFTEST: PASS, all_assertions_pass
  true, validation_problems [].
- b-check replica (real tests/self_heal.py code, TESTS redirected to /tmp, nothing in the repo
  written): status PASS, nodes 7, problems [], warnings [], english_leaks [], bad_urls [];
  the 2 english_notes are info-level code-payload hits, never spoken.
- Mandatory-sentence scan: 0 missing. "zorunlu kalıplar" now lives in nodes/statement/task_message;
  system_prompt no longer contains it (platform smoke bug "opening quoted card-selection sentence"
  is fixed in source; the deployed workflow predates it).
- Fixture integration over all 34 customers on the same bytes: examples 1/2/4/6 still match
  (90000001: 5.000,13 TL / min 2.000,05; 95004361: 12.000,00 TL / min 4.800,00 + EUR 85,20;
  92460108: FX USD 650,00 / EUR 380,00 + e-mail yes; 96125950: no e-mail -> week-only offer;
  96158684: "kalan toplam borcunuz 5.000,00 TL'dir.").
- Public API: build_query_workflow(spec, api, mock_base) -> dict; detect_domain(spec) -> bool;
  validate_workflow_shape(wf) -> [] ; selftest().
TODO:
- Rebuild + re-smoke: live workflow d659b17f-78c8-4fd1-8002-46755b07d54a
  (submission/finalcase.workflow.json, exported 21:00) predates the 21:03 fix — run
  `build.py finalcase/ $MOCK_URL` -> export -> platform smoke (orchestrator owns build.py).
- submission.json + commit + e-mail to yavuz@freyavoice.ai before 20:00 UTC.
- Mock URL: https://final-case-mock-bank.fcodefcode3.workers.dev · Workflow id:
  d659b17f-78c8-4fd1-8002-46755b07d54a (stale, needs rebuild) · Time left: ~1h54m.
NEXT: orchestrator — rebuild the workflow from the current gen_query.py, re-smoke the opening,
then ship.
