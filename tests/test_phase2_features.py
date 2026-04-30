"""
测试 Phase 2 功能：
1. LLM智能推理
2. 学习系统周分析
3. 深度洞察分析
"""

import asyncio
import os
import sys

import pytest

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from intelligent_project_analyzer.services.motivation_engine import (
    MotivationLearningSystem,
    MotivationTypeRegistry,
    deep_motivation_analysis,
    get_motivation_engine,
)


@pytest.mark.asyncio
async def test_llm_inference():
    """测试LLM推理功能"""
    print("\n" + "=" * 60)
    print("测试 1: LLM智能推理")
    print("=" * 60)

    engine = get_motivation_engine()

    # 测试案例：复杂的设计需求
    test_cases = [
        {
            "task": {"title": "深圳蛇口渔村改造", "description": "为老渔村设计公共空间，保留渔民文化记忆"},
            "user_input": "我们希望通过设计让年轻人重新认识蛇口的渔村文化，让老渔民感到自豪，同时也要考虑商业可持续性",
            "structured_data": {"target_users": "渔民社区 + 年轻游客", "location": "深圳蛇口", "constraints": "预算有限，需要分期实施"},
        },
        {
            "task": {"title": "咖啡店空间优化", "description": "提升咖啡店的空间利用率和客单价"},
            "user_input": "店铺面积只有50平米，目前坪效不高，希望通过设计提升翻台率，同时保持舒适的氛围",
            "structured_data": {"current_issues": "空间拥挤，翻台率低", "business_goal": "提升坪效30%", "budget": "10万元"},
        },
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n--- 案例 {i} ---")
        print(f"任务: {case['task']['title']}")
        print(f"输入: {case['user_input'][:60]}...")

        try:
            result = await engine.infer(
                task=case["task"], user_input=case["user_input"], structured_data=case["structured_data"]
            )

            print("✅ 识别成功")
            print(f"  - 主要动机: {result.primary_label} ({result.primary})")
            print(f"  - 置信度: {result.confidence:.2f}")
            print(f"  - 方法: {result.method}")
            print(f"  - 推理: {result.reasoning[:100]}...")
            if result.scores:
                top_scores = sorted(result.scores.items(), key=lambda x: x[1], reverse=True)[:3]
                print("  - Top 3 得分:")
                for type_id, score in top_scores:
                    registry = MotivationTypeRegistry()
                    type_obj = registry.get_type(type_id)
                    label = type_obj.label_zh if type_obj else type_id
                    print(f"    * {label}: {score:.2f}")

        except Exception as e:
            print(f"❌ 错误: {e}")


async def test_deep_insight():
    """测试深度洞察分析"""
    print("\n" + "=" * 60)
    print("测试 2: 深度洞察分析 (L1/L2/L3)")
    print("=" * 60)

    engine = get_motivation_engine()

    task = {"title": "社区无障碍设施改造", "description": "为老旧社区增加无障碍通道和设施"}

    user_input = """
    我们社区有很多老年人和残障人士，出行非常不便。
    希望通过改造让他们能够更自由地活动，不再依赖家人。
    同时也希望这个项目能够引起社会对无障碍设施的重视。
    """

    structured_data = {"target_users": "老年人、残障人士", "pain_points": "出行困难、缺乏独立性", "stakeholders": "居民、物业、政府"}

    print(f"\n任务: {task['title']}")
    print(f"输入: {user_input.strip()[:80]}...")

    try:
        # 先获取基础识别结果
        basic_result = await engine.infer(task, user_input, structured_data)
        print(f"\n基础识别: {basic_result.primary_label} (置信度: {basic_result.confidence:.2f})")

        # 深度洞察分析
        insight = await deep_motivation_analysis(task, user_input, basic_result, structured_data)

        print("\n✅ 深度洞察分析完成")

        # L1层
        print("\n【L1层 - 表层需求】")
        print(f"  主要动机: {insight.l1_surface['primary_label']}")
        print(f"  显性关键词: {', '.join(insight.l1_surface.get('explicit_keywords', [])[:5])}")

        # L2层
        print("\n【L2层 - 隐含动机】")
        if "hidden_motivations" in insight.l2_implicit:
            print("  隐含动机:")
            for m in insight.l2_implicit["hidden_motivations"][:3]:
                print(f"    - {m}")
        if "emotional_drivers" in insight.l2_implicit:
            print("  情绪驱动:")
            for e in insight.l2_implicit["emotional_drivers"][:3]:
                print(f"    - {e}")

        # L3层
        print("\n【L3层 - 深层驱动】")
        if "maslow_level" in insight.l3_deep:
            print(f"  马斯洛层次: {insight.l3_deep['maslow_level']}")
        if "psychological_drivers" in insight.l3_deep:
            print("  心理驱动:")
            for p in insight.l3_deep["psychological_drivers"][:3]:
                print(f"    - {p}")
        if "underlying_values" in insight.l3_deep:
            print("  底层价值观:")
            for v in insight.l3_deep["underlying_values"][:3]:
                print(f"    - {v}")

        # 关键分析
        if insight.core_tensions:
            print("\n【核心张力】")
            for t in insight.core_tensions[:3]:
                print(f"  - {t}")

        if insight.unspoken_expectations:
            print("\n【未说出口的期待】")
            for e in insight.unspoken_expectations[:3]:
                print(f"  - {e}")

        if insight.risk_blind_spots:
            print("\n【风险盲区】")
            for r in insight.risk_blind_spots[:3]:
                print(f"  - {r}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback

        traceback.print_exc()


async def test_learning_analysis():
    """测试学习系统周分析"""
    print("\n" + "=" * 60)
    print("测试 3: 学习系统周分析")
    print("=" * 60)

    registry = MotivationTypeRegistry()
    learning = MotivationLearningSystem(registry)

    # 先生成一些测试案例
    print("\n生成测试案例...")
    test_tasks = [
        {
            "task": {"title": "医院导视系统", "description": "优化医院导视", "session_id": "test1"},
            "user_input": "患者找不到科室，容易迷路",
            "type": "wellness",
            "confidence": 0.65,
        },
        {
            "task": {"title": "博物馆展陈", "description": "文物展示设计", "session_id": "test2"},
            "user_input": "希望传承历史文化",
            "type": "cultural",
            "confidence": 0.55,
        },
        {
            "task": {"title": "共享办公空间", "description": "联合办公设计", "session_id": "test3"},
            "user_input": "提升空间利用率和收益",
            "type": "commercial",
            "confidence": 0.60,
        },
        {
            "task": {"title": "儿童游乐场", "description": "社区游乐设施", "session_id": "test4"},
            "user_input": "让孩子们能安全玩耍，家长也能放心",
            "type": "mixed",
            "confidence": 0.40,
        },
        {
            "task": {"title": "老年活动中心", "description": "社区活动空间", "session_id": "test5"},
            "user_input": "希望老人能有交流的地方",
            "type": "social",
            "confidence": 0.45,
        },
    ]

    from intelligent_project_analyzer.services.motivation_engine import MotivationResult

    for case in test_tasks:
        result = MotivationResult(
            primary=case["type"],
            primary_label=case["type"],
            scores={case["type"]: case["confidence"]},
            confidence=case["confidence"],
            reasoning="测试案例",
            method="test",
        )
        learning.record_unmatched_case(case["task"], case["user_input"], result)

    print(f"✅ 已记录 {len(test_tasks)} 个测试案例")

    # 执行周分析
    print("\n执行周分析...")
    try:
        report = await learning.weekly_pattern_analysis()

        print("\n✅ 分析完成")
        print(f"  状态: {report['status']}")
        print(f"  案例数量: {report.get('case_count', 0)}")
        print(f"  低置信度案例: {report.get('low_confidence_count', 0)}")

        if "type_distribution" in report:
            print("\n  类型分布:")
            for type_id, count in sorted(report["type_distribution"].items(), key=lambda x: x[1], reverse=True):
                print(f"    - {type_id}: {count}")

        if "frequent_phrases" in report and report["frequent_phrases"]:
            print("\n  高频短语 (前10):")
            for phrase_data in report["frequent_phrases"][:10]:
                print(f"    - {phrase_data['phrase']}: {phrase_data['count']}次")

        if "llm_analysis" in report and isinstance(report["llm_analysis"], dict):
            llm = report["llm_analysis"]

            if "discovered_patterns" in llm and llm["discovered_patterns"]:
                print("\n  发现的模式:")
                for pattern in llm["discovered_patterns"][:3]:
                    print(f"    - {pattern.get('pattern_name', 'Unknown')}: {pattern.get('description', '')[:60]}...")

            if "new_dimensions" in llm and llm["new_dimensions"]:
                print("\n  新维度建议:")
                for dim in llm["new_dimensions"][:2]:
                    print(f"    - {dim.get('dimension_name', 'Unknown')}: {dim.get('description', '')[:60]}...")

            if "enhancement_suggestions" in llm and llm["enhancement_suggestions"]:
                print("\n  增强建议:")
                for sugg in llm["enhancement_suggestions"][:3]:
                    print(f"    - {sugg.get('type_id', 'Unknown')}: +{len(sugg.get('add_keywords', []))} 关键词")

        if "recommendation" in report:
            rec = report["recommendation"]
            print(f"\n  建议优先级: {rec.get('priority', 'unknown')}")
            if "actions" in rec and rec["actions"]:
                print(f"  行动项 ({len(rec['actions'])}):")
                for action in rec["actions"][:3]:
                    print(f"    - {action.get('type', 'unknown')}: {action.get('message', '')[:80]}...")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """主测试流程"""
    print("\n🚀 Phase 2 功能测试")
    print("=" * 60)

    # 测试1: LLM推理
    await test_llm_inference()

    # 测试2: 深度洞察
    await test_deep_insight()

    # 测试3: 学习分析
    await test_learning_analysis()

    print("\n" + "=" * 60)
    print("✅ Phase 2 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
