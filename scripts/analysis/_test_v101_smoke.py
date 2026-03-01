"""v10.1 Smoke test for _extract_framework_signals"""
import json
import sys

sys.path.insert(0, ".")

from intelligent_project_analyzer.interaction.nodes.output_intent_detection import _extract_framework_signals

# Test 1: Gaming bedroom (small space, budget, acoustics + smart tech)
sig1 = _extract_framework_signals(
    "我要设计一个50平米的电竞主题卧室，预算大约3万元，需要声学处理和RGB灯光系统", {}, ["design_professional"], [{"id": "gamer", "label": "电竞玩家"}]
)
print("=== TEST 1: 电竞卧室 ===")
print(json.dumps(sig1, ensure_ascii=False, indent=2))
assert sig1["scope"]["object_count"] == "single_space", f"Expected single_space, got {sig1['scope']['object_count']}"
assert any(
    c["type"] == "budget" for c in sig1["constraints"]
), f"Should detect budget constraint, got: {sig1['constraints']}"
assert "acoustics" in sig1["mandatory_dimensions"], f"Should detect acoustics, got: {sig1['mandatory_dimensions']}"
assert (
    "smart_technology" in sig1["mandatory_dimensions"]
), f"Should detect smart_technology (RGB), got: {sig1['mandatory_dimensions']}"
print("✓ PASS\n")

# Test 2: Village cluster (district, cultural, sustainability)
sig2 = _extract_framework_signals(
    "广东省增城区狮岭村整体更新改造，含5栋民居和公共空间，需要文化转译和可持续策略，预算有限",
    {"project_features": {"special_requirements": ["消防合规", "无障碍适老化"]}},
    ["design_professional", "government_policy"],
    [{"id": "villager", "label": "村民"}, {"id": "tourist", "label": "游客"}],
)
print("=== TEST 2: 狮岭村聚落 ===")
print(json.dumps(sig2, ensure_ascii=False, indent=2))
assert (
    sig2["scope"]["object_count"] == "district_cluster"
), f"Expected district_cluster, got {sig2['scope']['object_count']}"
assert any(c["type"] == "budget" for c in sig2["constraints"]), "Should detect budget constraint"
assert "cultural_translation" in sig2["mandatory_dimensions"], "Should detect cultural_translation"
assert "sustainability" in sig2["mandatory_dimensions"], "Should detect sustainability"
assert "fire_safety" in sig2["mandatory_dimensions"], "Should detect fire_safety from structured_requirements"
assert (
    "accessibility_safety" in sig2["mandatory_dimensions"]
), "Should detect accessibility from structured_requirements"
print("✓ PASS\n")

# Test 3: Hotel/complex (large, operations, competitive)
sig3 = _extract_framework_signals(
    "50000㎡度假酒店综合体设计，需要运营模式分析和竞品对标，完整框架", {}, ["design_professional", "investor_operator"], []
)
print("=== TEST 3: 大型酒店 ===")
print(json.dumps(sig3, ensure_ascii=False, indent=2))
assert sig3["scope"]["scale_markers"], "Should have scale markers"
assert "operation_model" in sig3["mandatory_dimensions"], "Should detect operation_model"
assert "competitive_strategy" in sig3["mandatory_dimensions"], "Should detect competitive_strategy"
assert sig3["output_calibration"]["depth_hint"] == "exhaustive", f"Got {sig3['output_calibration']['depth_hint']}"
print("✓ PASS\n")

# Test 4: Extreme environment
sig4 = _extract_framework_signals(
    "高原地区海拔4500米的寺庙修缮，极寒条件下施工，需要结构加固和恒温恒湿控制", {}, ["design_professional", "construction_execution"], []
)
print("=== TEST 4: 极端环境 ===")
print(json.dumps(sig4, ensure_ascii=False, indent=2))
assert any(c["type"] == "extreme_environment" for c in sig4["constraints"]), "Should detect extreme_environment"
assert "structural_engineering" in sig4["mandatory_dimensions"], "Should detect structural_engineering"
assert "environmental_control" in sig4["mandatory_dimensions"], "Should detect environmental_control"
print("✓ PASS\n")

print("=" * 40)
print("ALL 4 TESTS PASSED ✓")
