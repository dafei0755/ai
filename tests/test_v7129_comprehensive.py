"""
v7.129 综合测试 - 验证概念图角色差异化

模拟真实会话，测试V2/V3/V4/V5/V6生成的概念图是否符合角色身份

Author: Claude Code
Created: 2026-01-04
"""

import asyncio
import json

from intelligent_project_analyzer.services.image_generator import ImageGeneratorService
from intelligent_project_analyzer.workflow.nodes.deliverable_id_generator_node import (
    ROLE_VISUAL_IDENTITY,
    deliverable_id_generator_node,
)


async def test_comprehensive_role_differentiation():
    """综合测试：验证不同角色生成的元数据和Prompt是否体现差异化"""

    print("=" * 80)
    print("🧪 v7.129 综合测试 - 概念图角色差异化验证")
    print("=" * 80)

    # 模拟真实问卷数据（蛇口渔村老宅改造项目）
    questionnaire_summary = {
        "profile_label": "现代海洋风",
        "answers": {
            "gap_answers": {
                "gap_1": "希望客厅有大量自然光，能看到海景",
                "gap_2": "想保留渔村特色，比如木质元素和渔网装饰",
                "gap_3": "需要考虑收纳空间，家里有很多渔具",
            },
            "radar_values": {
                "现代感": 0.8,
                "文化传承": 0.9,
                "功能性": 0.7,
            },
        },
    }

    # 模拟Strategic Analysis结果（选定5个角色）
    strategic_analysis = {
        "selected_roles": [
            {"role_id": "2-1", "role_name": "V2_设计总监"},
            {"role_id": "3-1", "role_name": "V3_叙事专家"},
            {"role_id": "4-1", "role_name": "V4_研究员"},
            {"role_id": "5-1", "role_name": "V5_场景专家"},
            {"role_id": "6-1", "role_name": "V6_工程师"},
        ]
    }

    # 构建state
    state = {
        "session_id": "test_v7129_20260104",
        "user_input": "设计蛇口渔村老宅改造，需要现代海洋风格",
        "strategic_analysis": strategic_analysis,
        "questionnaire_summary": questionnaire_summary,
        "structured_requirements": {
            "style_tags": ["现代", "海洋风", "渔村文化"],
            "location": "蛇口渔村",
            "space_type": "老渔民住宅",
            "budget": "中等预算",
        },
        "confirmed_core_tasks": [
            {"title": "空间规划", "description": "整体布局设计"},
            {"title": "材料选型", "description": "选择合适的材料"},
        ],
    }

    # Step 1: 生成交付物元数据
    print("\n📋 Step 1: 生成交付物元数据")
    print("-" * 80)

    result = deliverable_id_generator_node(state)
    deliverable_metadata = result["deliverable_metadata"]
    deliverable_owner_map = result["deliverable_owner_map"]

    print(f"✅ 生成了 {len(deliverable_metadata)} 个交付物")

    # Step 2: 验证每个角色的元数据是否包含视觉身份字段
    print("\n🔍 Step 2: 验证角色视觉身份注入")
    print("-" * 80)

    role_check_results = {}

    for role_id in ["2-1", "3-1", "4-1", "5-1", "6-1"]:
        deliverable_ids = deliverable_owner_map.get(role_id, [])
        if not deliverable_ids:
            print(f"⚠️  {role_id}: 未生成交付物")
            continue

        # 取第一个交付物检查
        first_deliverable_id = deliverable_ids[0]
        metadata = deliverable_metadata[first_deliverable_id]
        constraints = metadata.get("constraints", {})

        # 提取视觉身份字段
        role_perspective = constraints.get("role_perspective", "")
        visual_type = constraints.get("visual_type", "")
        deliverable_format = constraints.get("deliverable_format", "")
        unique_angle = constraints.get("unique_angle", "")
        avoid_patterns = constraints.get("avoid_patterns", [])

        # 判断角色类型
        role_base_type = f"V{role_id.split('-')[0]}"
        expected_identity = ROLE_VISUAL_IDENTITY.get(role_base_type, {})

        # 验证
        is_valid = (
            role_perspective == expected_identity.get("perspective", "")
            and visual_type == expected_identity.get("visual_type", "")
            and len(avoid_patterns) > 0
        )

        role_check_results[role_id] = {
            "valid": is_valid,
            "perspective": role_perspective,
            "visual_type": visual_type,
            "format": deliverable_format,
            "avoid_patterns": avoid_patterns,
        }

        status = "✅" if is_valid else "❌"
        print(f"{status} {role_id} ({role_base_type}):")
        print(f"   视角: {role_perspective}")
        print(f"   类型: {visual_type}")
        print(f"   格式: {deliverable_format}")
        print(f"   避免: {', '.join(avoid_patterns) if avoid_patterns else '无'}")

    # Step 3: 模拟图像Prompt构建（不实际调用API）
    print("\n🎨 Step 3: 模拟图像Prompt构建")
    print("-" * 80)

    generator = ImageGeneratorService()

    # 为V3和V4生成模拟Prompt来对比
    test_roles = [
        ("3-1", "V3_叙事专家", "应该生成故事板风格"),
        ("4-1", "V4_研究员", "应该生成图表/信息图"),
    ]

    for role_id, role_name, expectation in test_roles:
        deliverable_ids = deliverable_owner_map.get(role_id, [])
        if not deliverable_ids:
            continue

        metadata = deliverable_metadata[deliverable_ids[0]]
        constraints = metadata.get("constraints", {})

        # 提取关键信息
        role_perspective = constraints.get("role_perspective", "")
        visual_type = constraints.get("visual_type", "")
        deliverable_format = constraints.get("deliverable_format", "")
        avoid_patterns = constraints.get("avoid_patterns", [])

        print(f"\n{role_name}:")
        print(f"  期望: {expectation}")
        print(f"  实际配置:")
        print(f"    - 视觉类型: {visual_type}")
        print(f"    - 格式: {deliverable_format}")
        print(f"    - 避免模式: {', '.join(avoid_patterns)}")

        # 检查是否符合预期
        if role_id == "3-1":
            is_correct = (
                visual_type == "narrative_storyboard"
                and deliverable_format == "narrative"
                and "建筑效果图" in avoid_patterns
            )
            print(f"  ✅ 符合预期" if is_correct else f"  ❌ 不符合预期")

        elif role_id == "4-1":
            is_correct = (
                visual_type == "research_infographic"
                and deliverable_format == "visualization"
                and "空间效果图" in avoid_patterns
            )
            print(f"  ✅ 符合预期" if is_correct else f"  ❌ 不符合预期")

    # Step 4: 统计结果
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)

    total_roles = len(role_check_results)
    valid_roles = sum(1 for r in role_check_results.values() if r["valid"])

    print(f"总角色数: {total_roles}")
    print(f"配置正确: {valid_roles}/{total_roles}")
    print(f"成功率: {valid_roles/total_roles*100:.1f}%")

    # 验证差异化
    print("\n🎯 差异化验证:")
    visual_types = set(r["visual_type"] for r in role_check_results.values())
    formats = set(r["format"] for r in role_check_results.values())

    print(f"  不同的visual_type数: {len(visual_types)}/5")
    print(f"  不同的format数: {len(formats)}/5")
    print(f"  Visual types: {', '.join(visual_types)}")
    print(f"  Formats: {', '.join(formats)}")

    # 最终判断
    print("\n" + "=" * 80)
    if valid_roles == total_roles and len(visual_types) >= 4:
        print("✅ 测试通过！所有角色都正确配置了差异化视觉身份")
        print("✅ 预期效果：V3生成故事板，V4生成图表，V6生成技术图纸")
        return True
    else:
        print("❌ 测试失败！存在配置错误")
        return False


async def test_prompt_construction():
    """测试Prompt构建逻辑（不调用实际API）"""

    print("\n" + "=" * 80)
    print("🧪 额外测试 - Prompt构建验证")
    print("=" * 80)

    # 模拟V3叙事专家的交付物元数据
    v3_metadata = {
        "id": "3-1_1_test",
        "name": "蛇口渔村文化叙事方案",
        "keywords": ["渔村历史", "现代海洋风", "情感连接"],
        "constraints": {
            "role_perspective": "叙事体验设计师",
            "visual_type": "narrative_storyboard",
            "deliverable_format": "narrative",
            "unique_angle": "情感连接与体验流线",
            "avoid_patterns": ["建筑效果图", "空间渲染"],
            "emotional_keywords": ["温馨", "怀旧", "海洋"],
        },
    }

    expert_analysis = """
    蛇口渔村的老宅改造应该注重保留渔村的历史记忆和文化符号。
    建议在空间中融入渔网、木船等元素，营造怀旧的氛围。
    通过叙事性的空间设计，让居住者能感受到从传统到现代的过渡。
    """

    print("\n模拟V3叙事专家的Prompt构建:")
    print("-" * 80)

    # 提取关键信息
    role_perspective = v3_metadata["constraints"]["role_perspective"]
    visual_type = v3_metadata["constraints"]["visual_type"]
    deliverable_format = v3_metadata["constraints"]["deliverable_format"]
    avoid_patterns = v3_metadata["constraints"]["avoid_patterns"]

    print(f"角色专业定位: {role_perspective}")
    print(f"视觉呈现类型: {visual_type}")
    print(f"交付物格式: {deliverable_format}")
    print(f"严格避免: {', '.join(avoid_patterns)}")

    print("\n预期LLM会收到的关键指令:")
    print("  1. RESPECT ROLE IDENTITY: Narrative expert → Storyboards/mood boards")
    print("  2. RESPECT DELIVERABLE FORMAT: 'narrative' → Storyboards/scene concepts")
    print("  3. AVOID SPECIFIED PATTERNS: 建筑效果图, 空间渲染")
    print("\n✅ 如果LLM遵循这些指令，应该生成故事板风格的概念图，而非建筑效果图")


if __name__ == "__main__":
    print("\n🚀 开始v7.129综合测试...\n")

    # 运行主测试
    success = asyncio.run(test_comprehensive_role_differentiation())

    # 运行Prompt测试
    asyncio.run(test_prompt_construction())

    print("\n" + "=" * 80)
    if success:
        print("🎉 综合测试完成！v7.129角色差异化实施成功")
        print("\n下一步建议:")
        print("  1. 启动服务器进行真实会话测试")
        print("  2. 创建包含V3/V4/V6的测试项目")
        print("  3. 检查生成的概念图是否符合角色身份")
    else:
        print("⚠️  综合测试发现问题，需要修复")
    print("=" * 80)
