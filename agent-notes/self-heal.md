# self-heal — final-case validation harness (tests/self_heal.py + final_contract.json + final_spec.json)

## 20:45 (17:45 UTC)
DONE:
- Harness `tests/self_heal.py` (a-d) written; artefacts extracted: tests/final_contract.json (7 services), tests/final_spec.json, tests/example_checks.json (6 examples). check (a) PASS, (d) PASS.
- Known FAILs from 17:41Z run: (b) 2 English texts in tool param descriptions (scan too broad), (c) mock_gen --no-llm rejects final_contract.json ("not OpenAPI JSON"), and NEW finding: workflow `system_prompt` carries a ~1.9k-char English outcome block (from spec closing_rule text) — must translate spec prose.
TODO:
- Narrow check (b) English scan to model-facing prompt fields (sentence-level).
- Translate final_spec.json closing_rule prose to Turkish (keep outcome enum keys); try adding week.get to spec.tool_paths.move.
- Emit tests/final_tool_api.json (OpenAPI shape) for check (c) dry-run; re-run until green.
- Mock URL: NOT deployed yet (orchestrator planning final-case-mock-bank). Workflow id: none deployed. Time left: ~2h.
17:52 UTC — SIDE TASK (hackathon değil): yerel Claude Code backend'i DeepSeek→Zhipu GLM'e geçirme isteği. API key test edildi, https://open.bigmodel.cn/api/anthropic çalışıyor (glm-5.3 tool-use + glm-5.3-flash mesaj testi geçti). Kullanıcıya kopyala-yapıştır export bloğu verildi. DONE.

## 20:53 (17:53 UTC)
DONE:
- ALL FOUR CHECKS GREEN (`python3 -I tests/self_heal.py check`): a PASS (contract vs customers), b PASS (7-node workflow, no English sentences in prompt fields; 2 info-level English param descriptions remain, never spoken), c PASS (mock_gen --no-llm dry-run rc=3 = documented stop; all 7 /voice/v1 paths present in tests/final-mock-dryrun/analysis.json), d PASS.
- Fixes landed (all in my files): final_spec.json — translated every rule text gen_query embeds (query.move_rule_text, dates.*_text, date_rule.text+params, closing_rule table `when` x16 + closing_lines/no_input_text/goodbye_text; originals kept under *_source_en; outcome/reason enum keys stay English). self_heal.py — sentence-level English scan scoped to prompt fields (system_prompt/task_message/on_enter/routing_prompt/...), param-desc English now info; status FAIL/PASS (warnings informational); check (c) regenerates tests/final_tool_api.json (OpenAPI shape) and accepts rc=3 as the --no-llm clean stop.
- NOTE: prepended fix worked — the system_prompt/outcome description/actions task_message are Turkish now.
TODO:
- Full mock_gen run (worker.js attempt) started in background, log /tmp/selfheal/mockfull.log, out tests/final-mock-dryrun.
- Remaining warnings worth a gen_query fix (unowned): /voice/v1/statement.week.get is never called (week_preview role picked decide only — probably OK: cards.balance carries nextStatementDate/nextLastPayDate; week number derivable) and 'Sizi ana menüye aktarıyorum.' mandatory line not found verbatim.
- gen_query.py still being edited by ac778d9e574805f01 (133680 B @17:51:54Z) — ownership gate not yet open.
- Mock URL: orchestrator building final-case-mock-bank (builder/mock_final.py). Workflow id: none deployed. Time left: ~2h.
NEXT: append Cycle sections to tests/self_heal_report.md; re-run check after each gen_query landing; status line to main.
