"""
v7.129 快速验证脚本 - 检查角色差异化配置

直接验证关键数据结构，不需要异步调用
"""

import sys

sys.path.insert(0, "d:/11-20/langgraph-design")

from intelligent_project_analyzer.workflow.nodes.deliverable_id_generator_node import (
    ROLE_VISUAL_IDENTITY,
    _generate_role_specific_deliverables,
    _map_role_to_format,
)

print("=" * 80)
print("🧪 v7.129 快速验证 - 角色视觉身份配置")
print("=" * 80)

# 测试1: 验证ROLE_VISUAL_IDENTITY常量
print("\n✅ 测试1: 验证角色视觉身份常量")
print("-" * 80)

for role, identity in ROLE_VISUAL_IDENTITY.items():
    print(f"\n{role}:")
    print(f"  视角: {identity['perspective']}")
    print(f"  类型: {identity['visual_type']}")
    print(f"  切入点: {identity['unique_angle']}")
    print(f"  避免: {', '.join(identity['avoid_patterns'])}")

# 测试2: 验证format映射
print("\n\n✅ 测试2: 验证角色到format的映射")
print("-" * 80)

for role in ["V2", "V3", "V4", "V5", "V6"]:
    format_type = _map_role_to_format(role)
    print(f"{role} → {format_type}")

# 测试3: 验证V3/V4/V6的交付物元数据生成
print("\n\n✅ 测试3: 验证V3/V4/V6的交付物元数据生成")
print("-" * 80)

questionnaire_keywords = {
    "location": "蛇口渔村",
    "space_type": "老渔民住宅",
    "budget": "中等预算",
    "style_label": "现代海洋风",
    "material_keywords": ["木材", "石材", "玻璃"],
    "functional_keywords": ["储物", "采光", "通风"],
    "emotional_keywords": ["温馨", "怀旧", "海洋"],
    "color_palette": "蓝色、米白色",
}

test_roles = [
    ("3-1", "V3", "叙事专家", "narrative_storyboard", "narrative"),
    ("4-1", "V4", "研究员", "research_infographic", "visualization"),
    ("6-1", "V6", "工程师", "technical_blueprint", "technical_doc"),
]

for role_id, role_type, role_name, expected_visual_type, expected_format in test_roles:
    print(f"\n{role_name} ({role_type}):")

    deliverables = _generate_role_specific_deliverables(
        role_id=role_id,
        role_base_type=role_type,
        user_input="设计蛇口渔村老宅改造",
        structured_requirements={},
        questionnaire_keywords=questionnaire_keywords,
        confirmed_core_tasks=[],
    )

    if deliverables:
        first = deliverables[0]
        constraints = first.get("constraints", {})

        role_perspective = constraints.get("role_perspective", "")
        visual_type = constraints.get("visual_type", "")
        deliverable_format = constraints.get("deliverable_format", "")
        unique_angle = constraints.get("unique_angle", "")
        avoid_patterns = constraints.get("avoid_patterns", [])

        # 验证
        is_correct_visual = visual_type == expected_visual_type
        is_correct_format = deliverable_format == expected_format
        has_avoid = len(avoid_patterns) > 0

        print(f"  ✅ 视觉类型: {visual_type} {'✓' if is_correct_visual else '✗ 期望: ' + expected_visual_type}")
        print(f"  ✅ 格式类型: {deliverable_format} {'✓' if is_correct_format else '✗ 期望: ' + expected_format}")
        print(f"  ✅ 视角: {role_perspective}")
        print(f"  ✅ 切入点: {unique_angle}")
        print(f"  ✅ 避免模式: {', '.join(avoid_patterns)} {'✓' if has_avoid else '✗ 缺失'}")

        if is_correct_visual and is_correct_format and has_avoid:
            print(f"  🎉 {role_name}配置正确！")
        else:
            print(f"  ⚠️  {role_name}配置有误")
    else:
        print(f"  ❌ 未生成交付物")

# 测试4: 验证差异化
print("\n\n✅ 测试4: 验证角色差异化")
print("-" * 80)

visual_types = set()
formats = set()

for role_id, role_type, _, _, _ in test_roles:
    deliverables = _generate_role_specific_deliverables(
        role_id=role_id,
        role_base_type=role_type,
        user_input="测试项目",
        structured_requirements={},
        questionnaire_keywords=questionnaire_keywords,
        confirmed_core_tasks=[],
    )

    if deliverables:
        constraints = deliverables[0].get("constraints", {})
        visual_types.add(constraints.get("visual_type", ""))
        formats.add(constraints.get("deliverable_format", ""))

print(f"不同的visual_type数: {len(visual_types)}/3")
print(f"不同的format数: {len(formats)}/3")
print(f"Visual types: {', '.join(visual_types)}")
print(f"Formats: {', '.join(formats)}")

# 最终结论
print("\n" + "=" * 80)
if len(visual_types) == 3 and len(formats) == 3:
    print("🎉 验证通过！所有角色都配置了不同的视觉身份")
    print("\n✅ v7.129角色差异化实施成功:")
    print("  - V3叙事专家: narrative_storyboard (避免建筑效果图)")
    print("  - V4研究员: research_infographic (避免空间效果图)")
    print("  - V6工程师: technical_blueprint (避免艺术效果图)")
    print("\n预期效果: 生成的概念图将符合各角色的专业定位")
else:
    print("❌ 验证失败！角色差异化配置不完整")
print("=" * 80)
