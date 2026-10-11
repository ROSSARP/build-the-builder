"""Generate a workflow with the current builder code WITHOUT touching Freya,
so the local simulator can validate regenerations instantly.

    python3 tests/gen_local.py <brief.md> [tool_api.json] [--out out/<slot>.workflow.json]
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from builder import gen, spec as spec_mod
from builder.build import llm, extract_json, load_briefs, load_tool_api, find_tool_api

def main():
    brief = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "briefs" / "brief-a.md")
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else None
    pos = [a for a in sys.argv[2:] if not a.startswith("--") and a != out]
    api_path = find_tool_api(brief, pos[0] if pos else None)
    slot = pathlib.Path(brief).stem
    briefs_text = load_briefs(brief)
    api = load_tool_api(api_path)
    spec = None
    for attempt in range(2):
        try:
            spec = extract_json(llm(spec_mod.EXTRACT_PROMPT
                .replace("__BRIEFS__", briefs_text)
                .replace("__API__", json.dumps(api)[:20000]), "extract spec from brief"))
            errors = spec_mod.spec_validation_errors(spec)
            if errors:
                raise ValueError("; ".join(errors))
            break
        except Exception as e:
            print(f"spec attempt {attempt + 1} failed: {e}")
            spec = None
    if spec is None:
        raise SystemExit("could not extract a usable spec")
    workflow = gen.build_workflow(spec, api)
    dest = out or str(ROOT / "out" / f"{slot}.workflow.json")
    pathlib.Path(dest).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(dest).write_text(json.dumps({"workflow_id": "local", "agent_id": "local", "workflow": workflow}, indent=1))
    print(f"wrote local workflow to {dest} (nodes: {list(workflow['nodes'])})")

if __name__ == "__main__":
    main()
