"""Quick smoke test for Projection Dispatcher v10.0"""
from intelligent_project_analyzer.services.projection_dispatcher import (
    load_projections_config,
    calculate_axis_scores,
    determine_active_projections,
    build_projection_context,
    _extract_analysis_pool,
)

# 1. Config loading
config = load_projections_config()
assert "projections" in config, "Missing projections key"
assert len(config["projections"]) == 5, f"Expected 5 projections, got {len(config['projections'])}"
print("[1/5] Config loading: PASS")

# 2. Axis scoring with empty state
scores = calculate_axis_scores({})
assert all(k in scores for k in ["identity", "power", "operation", "emotion", "civilization"])
print(f"[2/5] Default axis scores: PASS {scores}")

# 3. Projection activation for M5 rural + 施工
state = {
    "detected_design_modes": ["M5_rural_context"],
    "user_input": "四川狮岭村乡村振兴民宿设计，含施工深化需求",
    "radar_scores": {"cultural_axis": 8, "energy_level": 5, "sensory_focus": 6},
}
active = determine_active_projections(scores, state)
assert "design_professional" in active, "design_professional should always activate"
assert "construction_execution" in active, "construction_execution should match keyword 施工"
print(f"[3/5] Projection activation: PASS {active}")

# 4. Context building
proj_cfg = config["projections"]["design_professional"]
ctx = build_projection_context("design_professional", proj_cfg, {"test": 1}, scores, {})
assert ctx["projection_id"] == "design_professional"
assert "discourse_register" in ctx
assert ctx["discourse_register"]["tone"] == "专业批评性写作"
print("[4/5] Context building: PASS")

# 5. Analysis pool extraction
pool = _extract_analysis_pool(
    {
        "agent_results": {"V1_需求分析": {"content": "测试用例内容", "structured_data": {}}},
        "user_input": "测试",
        "final_report": {"project_name": "狮岭村民宿"},
    }
)
assert "expert_outputs" in pool
assert "V1_需求分析" in pool["expert_outputs"]
assert pool["final_report"]["project_name"] == "狮岭村民宿"
print("[5/5] Analysis pool extraction: PASS")

print("\n=== ALL 5 SMOKE TESTS PASSED ===")
