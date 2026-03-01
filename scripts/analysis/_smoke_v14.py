import sys

sys.path.insert(0, ".")

print("=" * 60)
print("v14.0 权重语义翻译 — 冒烟测试")
print("=" * 60)

# Test 1: WeightSemanticTranslator 基本功能
print("\n[Test 1] WeightSemanticTranslator.translate()")
from intelligent_project_analyzer.services.weight_semantic_translator import WeightSemanticTranslator

t = WeightSemanticTranslator()
r = t.translate(
    radar_dimension_values={
        "aesthetic_preference": 85,
        "functional_priority": 60,
        "budget_priority": 35,
        "technology_adoption": 15,
        "cultural_axis": 50,
    },
    selected_radar_dimensions=[
        {
            "id": "aesthetic_preference",
            "name": "美学偏好",
            "left_label": "实用",
            "right_label": "艺术",
            "category": "aesthetic",
            "default_value": 50,
        },
        {
            "id": "functional_priority",
            "name": "功能优先",
            "left_label": "简约",
            "right_label": "全能",
            "category": "functional",
            "default_value": 50,
        },
        {
            "id": "budget_priority",
            "name": "预算权重",
            "left_label": "经济",
            "right_label": "不惜成本",
            "category": "resource",
            "default_value": 50,
        },
        {
            "id": "technology_adoption",
            "name": "技术接受度",
            "left_label": "传统",
            "right_label": "智能",
            "category": "technology",
            "default_value": 50,
        },
        {
            "id": "cultural_axis",
            "name": "文化倾向",
            "left_label": "现代",
            "right_label": "传统",
            "category": "aesthetic",
            "default_value": 50,
        },
    ],
)

# Validate structure
assert "_summary" in r, "Missing _summary"
assert "core_drivers" in r["_summary"], "Missing core_drivers"
assert "important" in r["_summary"], "Missing important"
assert "de_emphasized" in r["_summary"], "Missing de_emphasized"

# Validate tier classification
assert (
    "aesthetic_preference" in r["_summary"]["core_drivers"]
), f"aesthetic_preference should be core, got tiers: {r['_summary']}"
assert "technology_adoption" in r["_summary"]["de_emphasized"], f"technology_adoption should be de_emphasized"

# Validate fields for a core dimension
ae = r["aesthetic_preference"]
for field in ["tier", "tendency_label", "design_intent", "expert_instruction", "dimension_label", "adjusted"]:
    assert field in ae, f"Missing field: {field}"
assert ae["tier"] == "core_driver"
assert ae["dimension_label"] == "美学偏好"
assert len(ae["design_intent"]) > 10, f"design_intent too short: {ae['design_intent']}"

print(f"  ✅ 5 dims translated: core={r['_summary']['core_drivers']}, de_emph={r['_summary']['de_emphasized']}")
print(f"  ✅ aesthetic_preference intent: {ae['design_intent'][:60]}")

# Test 2: build_initial_manifest
print("\n[Test 2] WeightSemanticTranslator.build_initial_manifest()")
manifest = WeightSemanticTranslator.build_initial_manifest(r)
assert isinstance(manifest, dict)
assert "aesthetic_preference" in manifest
assert manifest["aesthetic_preference"]["responses"]
print(f"  ✅ Manifest entries: {len(manifest)}")

# Test 3: Empty input handling
print("\n[Test 3] 空输入处理")
r_empty = t.translate({}, [])
assert "_summary" in r_empty
assert r_empty["_summary"]["core_drivers"] == []
print("  ✅ 空输入返回空结果，无异常")

# Test 4: prompt_templates weight context
print("\n[Test 4] ExpertPromptTemplate._build_weight_context_section()")
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate

pt = ExpertPromptTemplate.__new__(ExpertPromptTemplate)
pt.role_type = "V2"

# With weight_interpretations
state_with_wi = {"weight_interpretations": r}
section = pt._build_weight_context_section(state_with_wi)
assert "核心驱动维度" in section, f"Missing core section in: {section[:100]}"
assert "美学偏好" in section
print(f"  ✅ 权重上下文生成成功 ({len(section)} chars)")

# Without weight_interpretations
state_without = {}
section_empty = pt._build_weight_context_section(state_without)
assert section_empty == ""
print("  ✅ 无数据时返回空字符串")

# Test 5: questionnaire_summary corrections method signature
print("\n[Test 5] _apply_corrections_and_build_review signature")
import inspect
from intelligent_project_analyzer.interaction.nodes.questionnaire_summary import QuestionnaireSummaryNode

sig = inspect.signature(QuestionnaireSummaryNode._apply_corrections_and_build_review)
params = list(sig.parameters.keys())
assert "weight_interpretations" in params, f"Missing weight_interpretations param. Params: {params}"
print(f"  ✅ 方法签名包含 weight_interpretations 参数")

# Test 6: _apply_corrections_and_build_review with weight_interpretations
print("\n[Test 6] _apply_corrections_and_build_review 功能测试")
corrected, review = QuestionnaireSummaryNode._apply_corrections_and_build_review(
    snapshot=[{"id": "task1", "title": "任务1"}],
    current_tasks=[{"id": "task1", "title": "任务1"}],
    task_corrections=[],
    gap_filling={"budget": {"total": "50万"}},
    radar_values={"aesthetic_preference": 85, "functional_priority": 60},
    selected_dims=[],
    restructured_doc={"design_priorities": [], "constraints": {"budget": {"total": "50万"}}},
    weight_interpretations=r,
)
assert "radar_response_ledger" in review, f"Missing radar_response_ledger. Keys: {list(review.keys())}"
assert "coverage_rate" in review["effectiveness"]["radar_evidence"], "Missing coverage_rate"
print(f"  ✅ review 包含 radar_response_ledger ({len(review['radar_response_ledger'])} 条)")
print(f"  ✅ coverage_rate = {review['effectiveness']['radar_evidence']['coverage_rate']}")

for item in review["strengthened_items"]:
    assert "design_driver" in item, f"strengthened_item missing design_driver: {item}"
print(f"  ✅ strengthened_items 使用 design_driver 字段 ({len(review['strengthened_items'])} 条)")

print("\n" + "=" * 60)
print("ALL v14.0 SMOKE TESTS PASSED ✅")
print("=" * 60)
