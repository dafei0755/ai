#!/usr/bin/env python
"""
v7.152 重构引擎测试脚本
验证空 analysis_layers 时的降级策略
"""

import json

from intelligent_project_analyzer.interaction.nodes.requirements_restructuring import RequirementsRestructuringEngine

# 模拟问卷数据
mock_questionnaire_data = {
    "answers": {"budget": "30万左右", "timeline": "3个月内完成", "style": "现代简约风格"},
    "tasks": [{"task": "设计一个舒适的家居环境", "priority": "high"}, {"task": "注重收纳空间", "priority": "medium"}],
    "gap_filling": {"space_area": "150平米", "room_count": "三室两厅", "budget_range": "25-35万"},
    "dimensions": {"风格取向": {"value": 7, "tendency": "偏现代"}, "功能性": {"value": 8, "tendency": "注重实用"}},
}

mock_analysis_layers = {}  # 模拟空的 analysis_layers

# 模拟 AI 分析结果
mock_ai_analysis = {
    "requirement_analysis": {
        "project_type": "室内设计",
        "key_requirements": ["现代简约", "收纳", "采光"],
        "summary": "150平米现代简约住宅设计",
    }
}


def test_restructuring():
    engine = RequirementsRestructuringEngine()

    print("=" * 60)
    print("🧪 v7.152 重构测试 - 空 analysis_layers 场景")
    print("=" * 60)

    # 测试重构（同步方法）
    result = engine.restructure(
        questionnaire_data=mock_questionnaire_data,
        ai_analysis=mock_ai_analysis,
        analysis_layers=mock_analysis_layers,
        user_input="我需要设计一个150平米的现代简约风格住宅",
        use_llm=True,
    )

    print("\n📊 洞察摘要 (insight_summary):")
    insight = result.get("insight_summary", {})
    score = insight.get("L5_sharpness_score", "N/A")
    note = insight.get("L5_sharpness_note", "")
    tension = insight.get("L3_core_tension", "")
    jtbd = insight.get("L4_project_task_jtbd", "")
    status = insight.get("_status", "N/A")

    print(f"  L5_sharpness_score: {score}")
    print(f"  L5_sharpness_note: {note[:80] if note else '空'}...")
    print(f"  L3_core_tension: {tension[:80] if tension else '空'}...")
    print(f"  L4_project_task_jtbd: {jtbd[:80] if jtbd else '空'}...")
    print(f"  _status: {status}")

    # 验证降级逻辑
    print("\n🔍 降级逻辑验证:")
    if score == -1:
        print("  ✅ score=-1 表示'生成中'状态正确")
    elif score == 0:
        print("  ⚠️ score=0 旧版降级，需检查")
    elif score > 0:
        print(f"  ✅ score={score} LLM 成功生成")

    if status == "pending":
        print("  ✅ _status='pending' 标记正确")
    elif status == "N/A":
        print("  ⚠️ _status 未设置")

    # 检查深度洞察
    print("\n💡 深度洞察 (deep_insights):")
    essence = result.get("project_essence", "")
    implicit = result.get("implicit_requirements", [])
    conflicts = result.get("key_conflicts", [])

    print(f"  project_essence: {essence[:100] if essence else '空'}...")
    print(f"  implicit_requirements: {len(implicit)} 个")
    print(f"  key_conflicts: {len(conflicts)} 个")

    for i, c in enumerate(conflicts[:2]):
        if isinstance(c, dict):
            print(f"    [{i+1}] {c.get('conflict', str(c))[:60]}...")
        else:
            print(f"    [{i+1}] {str(c)[:60]}...")

    # 检查项目目标
    print("\n🎯 项目目标 (project_objectives):")
    obj = result.get("project_objectives", {})
    goal = obj.get("primary_goal", "")
    source = obj.get("primary_goal_source", "")

    print(f"  primary_goal: {goal[:80] if goal else '空'}...")
    print(f"  primary_goal_source: {source}")

    # 总结
    print("\n" + "=" * 60)
    success = True
    if not essence and not tension and not jtbd:
        print("❌ 测试失败: 深度洞察全部为空")
        success = False
    elif score == 0 and note == "待分析":
        print("⚠️ 测试部分通过: 使用旧版降级值")
        success = False
    else:
        print("✅ 测试通过: v7.152 降级策略正常工作")

    return success


if __name__ == "__main__":
    success = test_restructuring()
    exit(0 if success else 1)
