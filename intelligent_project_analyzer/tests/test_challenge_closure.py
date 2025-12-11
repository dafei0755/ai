"""
专家挑战闭环机制测试

测试v3.5.1新增的三种闭环机制:
1. Accept决策: 更新expert_driven_insights
2. Synthesize决策: 综合竞争性框架
3. Escalate决策: 提交甲方裁决
"""

import json
import sys
from datetime import datetime

# 添加项目路径
sys.path.insert(0, "d:\\11-20\\langgraph-design")

# 测试数据
MOCK_EXPERT_OUTPUTS = {
    "V2_设计总监_2-1": {
        "challenge_flags": [
            {
                "challenged_item": "核心张力定义",
                "rationale": "真正的张力不是'传统vs现代'，而是'仪式感vs日常感'",
                "reinterpretation": "用户需要的是可以'切换模式'的空间",
                "design_impact": "设计策略从'融合'转向'多模态切换'"
            }
        ]
    },
    "V3_人物及叙事专家_3-1": {
        "challenge_flags": [
            {
                "challenged_item": "用户画像准确性",
                "rationale": "需求分析师认为目标用户是'追求品质的中产'，但我标记不确定",
                "reinterpretation": "建议回访用户确认，是'追求品质'还是'追求独特性'",
                "design_impact": "在确认前，提供两个方案"
            }
        ]
    },
    "V5_场景与用户生态专家_5-1": {
        "challenge_flags": [
            {
                "challenged_item": "核心场景优先级",
                "rationale": "与V2对场景重要性的判断不一致",
                "reinterpretation": "我认为社交场景是核心，而非支撑",
                "design_impact": "需要综合两种框架"
            }
        ]
    },
    "V6_专业总工程师_6-1": {
        "challenge_flags": [
            {
                "challenged_item": "预算分配策略",
                "rationale": "需求分析师建议70%用于硬装，但这超出我的技术评估范围",
                "reinterpretation": "这是战略决策，建议交甲方裁决",
                "design_impact": "预算比例影响整体质量"
            }
        ]
    }
}


def test_accept_closure():
    """测试1: Accept决策的闭环机制"""
    print("\n" + "="*80)
    print("测试1: Accept决策的闭环机制")
    print("="*80)
    
    # 模拟专家挑战
    challenge = {
        "expert_role": "V2_设计总监_2-1",
        "challenged_item": "核心张力定义",
        "rationale": "真正的张力不是'传统vs现代'，而是'仪式感vs日常感'",
        "reinterpretation": "用户需要的是可以'切换模式'的空间",
        "design_impact": "设计策略从'融合'转向'多模态切换'"
    }
    
    # 模拟state
    mock_state = {}
    
    # 导入实际的闭环函数
    from intelligent_project_analyzer.agents.dynamic_project_director import _apply_accepted_reinterpretation
    
    # 执行闭环逻辑
    _apply_accepted_reinterpretation(mock_state, challenge)
    
    # 验证结果
    print("\n✅ 验证1: expert_driven_insights字段存在")
    assert "expert_driven_insights" in mock_state, "❌ 缺少expert_driven_insights字段"
    print(f"   ✓ expert_driven_insights: {list(mock_state['expert_driven_insights'].keys())}")
    
    print("\n✅ 验证2: 包含被挑战的项目")
    assert "核心张力定义" in mock_state["expert_driven_insights"], "❌ 缺少'核心张力定义'条目"
    insight = mock_state["expert_driven_insights"]["核心张力定义"]
    print(f"   ✓ 专家: {insight['accepted_from']}")
    print(f"   ✓ 重新诠释: {insight['expert_reinterpretation'][:50]}...")
    print(f"   ✓ 设计影响: {insight['design_impact'][:50]}...")
    
    print("\n✅ 验证3: insight_updates字段存在")
    assert "insight_updates" in mock_state, "❌ 缺少insight_updates字段"
    assert len(mock_state["insight_updates"]) > 0, "❌ insight_updates为空"
    print(f"   ✓ 更新数量: {len(mock_state['insight_updates'])}")
    print(f"   ✓ 更新内容: {mock_state['insight_updates'][0]['reason']}")
    
    print("\n🎉 测试1通过: Accept闭环机制正常工作")
    return True


def test_synthesize_closure():
    """测试2: Synthesize决策的闭环机制"""
    print("\n" + "="*80)
    print("测试2: Synthesize决策的闭环机制")
    print("="*80)
    
    # 模拟多个专家提出竞争性框架
    challenges = [
        {
            "expert_role": "V2_设计总监_2-1",
            "challenged_item": "核心场景优先级",
            "rationale": "我认为社交场景是支撑",
            "reinterpretation": "方案A: 以独处为核心，社交为点缀",
            "design_impact": "强调私密性"
        },
        {
            "expert_role": "V5_场景与用户生态专家_5-1",
            "challenged_item": "核心场景优先级",
            "rationale": "我认为社交场景是核心",
            "reinterpretation": "方案B: 以社交为核心，独处为过渡",
            "design_impact": "强调开放性"
        }
    ]
    
    # 模拟state
    mock_state = {}
    
    # 导入实际的闭环函数
    from intelligent_project_analyzer.agents.dynamic_project_director import _synthesize_competing_frames
    
    # 执行闭环逻辑
    _synthesize_competing_frames(mock_state, challenges)
    
    # 验证结果
    print("\n✅ 验证1: framework_synthesis字段存在")
    assert "framework_synthesis" in mock_state, "❌ 缺少framework_synthesis字段"
    print(f"   ✓ framework_synthesis: {list(mock_state['framework_synthesis'].keys())}")
    
    print("\n✅ 验证2: 包含竞争项的综合")
    assert "核心场景优先级" in mock_state["framework_synthesis"], "❌ 缺少'核心场景优先级'综合"
    synthesis = mock_state["framework_synthesis"]["核心场景优先级"]
    print(f"   ✓ 竞争框架数量: {len(synthesis['competing_frames'])}")
    print(f"   ✓ 综合摘要: {synthesis['synthesis_summary'][:80]}...")
    print(f"   ✓ 推荐方案: {synthesis['recommendation'][:60]}...")
    
    print("\n✅ 验证3: 标志位正确设置")
    assert mock_state.get("has_competing_frameworks") == True, "❌ has_competing_frameworks未设置"
    assert mock_state.get("synthesis_required") == True, "❌ synthesis_required未设置"
    print("   ✓ has_competing_frameworks: True")
    print("   ✓ synthesis_required: True")
    
    print("\n🎉 测试2通过: Synthesize闭环机制正常工作")
    return True


def test_escalate_closure():
    """测试3: Escalate决策的闭环机制"""
    print("\n" + "="*80)
    print("测试3: Escalate决策的闭环机制")
    print("="*80)
    
    # 模拟需要甲方裁决的挑战
    from intelligent_project_analyzer.agents.dynamic_project_director import detect_and_handle_challenges_node
    
    mock_state = {
        "batch_results": {
            "batch_6": {
                "V6_专业总工程师_6-1": {
                    "challenge_flags": [
                        {
                            "challenged_item": "预算分配策略",
                            "rationale": "需求分析师建议70%用于硬装，但这超出我的技术评估范围",
                            "reinterpretation": "这是战略决策，建议交甲方裁决",
                            "design_impact": "预算比例影响整体质量"
                        }
                    ]
                }
            }
        }
    }
    
    # 执行检测和处理
    updated_state = detect_and_handle_challenges_node(mock_state)
    
    # 合并更新
    for key, value in updated_state.items():
        mock_state[key] = value
    
    # 验证结果
    print("\n✅ 验证1: escalated_challenges字段存在")
    assert "escalated_challenges" in mock_state, "❌ 缺少escalated_challenges字段"
    print(f"   ✓ 需要甲方裁决的挑战数量: {len(mock_state['escalated_challenges'])}")
    
    print("\n✅ 验证2: 挑战格式正确")
    if mock_state["escalated_challenges"]:
        escalated = mock_state["escalated_challenges"][0]
        assert "issue_id" in escalated, "❌ 缺少issue_id"
        assert "requires_client_decision" in escalated, "❌ 缺少requires_client_decision"
        print(f"   ✓ issue_id: {escalated['issue_id']}")
        print(f"   ✓ 描述: {escalated['description']}")
        print(f"   ✓ 需要甲方决策: {escalated['requires_client_decision']}")
    
    print("\n✅ 验证3: requires_client_review标志位")
    assert mock_state.get("requires_client_review") == True, "❌ requires_client_review未设置"
    print("   ✓ requires_client_review: True")
    
    print("\n🎉 测试3通过: Escalate闭环机制正常工作")
    return True


def test_routing_logic():
    """测试4: 路由逻辑优先级"""
    print("\n" + "="*80)
    print("测试4: 路由逻辑优先级")
    print("="*80)
    
    from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow
    
    # 创建workflow实例
    workflow = MainWorkflow()
    
    # 测试场景1: escalate优先
    print("\n场景1: 同时有escalate和revisit_ra，应优先escalate")
    state1 = {
        "requires_client_review": True,
        "requires_feedback_loop": True,
        "escalated_challenges": [{"issue_id": "TEST"}]
    }
    route1 = workflow._route_after_challenge_detection(state1)
    assert route1 == "analysis_review", f"❌ 路由错误: {route1}"
    print(f"   ✓ 路由到: {route1}")
    
    # 测试场景2: 只有revisit_ra
    print("\n场景2: 只有revisit_ra，应回访需求分析师")
    state2 = {
        "requires_client_review": False,
        "requires_feedback_loop": True
    }
    route2 = workflow._route_after_challenge_detection(state2)
    assert route2 == "revisit_requirements", f"❌ 路由错误: {route2}"
    print(f"   ✓ 路由到: {route2}")
    
    # 测试场景3: 无挑战
    print("\n场景3: 无挑战，继续正常流程")
    state3 = {
        "requires_client_review": False,
        "requires_feedback_loop": False
    }
    route3 = workflow._route_after_challenge_detection(state3)
    assert route3 == "continue_workflow", f"❌ 路由错误: {route3}"
    print(f"   ✓ 路由到: {route3}")
    
    print("\n🎉 测试4通过: 路由逻辑优先级正确")
    return True


def test_report_integration():
    """测试5: 报告生成集成"""
    print("\n" + "="*80)
    print("测试5: 报告生成集成")
    print("="*80)
    
    from intelligent_project_analyzer.report.result_aggregator import ResultAggregatorAgent
    
    # 模拟包含挑战解决结果的state
    mock_state = {
        "expert_driven_insights": {
            "核心张力定义": {
                "accepted_from": "V2_设计总监_2-1",
                "expert_reinterpretation": "用户需要的是可以'切换模式'的空间",
                "design_impact": "设计策略从'融合'转向'多模态切换'",
                "timestamp": datetime.now().isoformat()
            }
        },
        "framework_synthesis": {
            "核心场景优先级": {
                "competing_frames": [
                    {"expert": "V2", "interpretation": "方案A"},
                    {"expert": "V5", "interpretation": "方案B"}
                ],
                "synthesis_summary": "综合摘要",
                "recommendation": "建议方案"
            }
        },
        "escalated_challenges": [
            {
                "issue_id": "CHALLENGE_V6_123456",
                "description": "预算分配需要甲方决策",
                "requires_client_decision": True
            }
        ]
    }
    
    # 创建聚合器实例（不需要LLM）
    aggregator = ResultAggregatorAgent(llm_model=None)
    
    # 调用提取方法
    challenge_resolutions = aggregator._extract_challenge_resolutions(mock_state)
    
    # 验证结果
    print("\n✅ 验证1: 基本结构")
    assert challenge_resolutions["has_challenges"] == True, "❌ has_challenges应为True"
    print(f"   ✓ has_challenges: True")
    
    print("\n✅ 验证2: Accept结果")
    assert len(challenge_resolutions["accepted_reinterpretations"]) == 1, "❌ Accept结果数量错误"
    print(f"   ✓ 采纳的重新诠释: {len(challenge_resolutions['accepted_reinterpretations'])}个")
    
    print("\n✅ 验证3: Synthesize结果")
    assert len(challenge_resolutions["synthesized_frameworks"]) == 1, "❌ Synthesize结果数量错误"
    print(f"   ✓ 综合的框架: {len(challenge_resolutions['synthesized_frameworks'])}个")
    
    print("\n✅ 验证4: Escalate结果")
    assert len(challenge_resolutions["escalated_to_client"]) == 1, "❌ Escalate结果数量错误"
    print(f"   ✓ 提交甲方的挑战: {len(challenge_resolutions['escalated_to_client'])}个")
    
    print("\n✅ 验证5: 统计摘要")
    summary = challenge_resolutions["summary"]
    assert summary["total_challenges"] == 3, "❌ 总数错误"
    assert summary["accepted_count"] == 1, "❌ Accept数量错误"
    assert summary["synthesized_count"] == 1, "❌ Synthesize数量错误"
    assert summary["escalated_count"] == 1, "❌ Escalate数量错误"
    print(f"   ✓ 总挑战数: {summary['total_challenges']}")
    print(f"   ✓ 闭环率: {summary['closure_rate']}")
    
    print("\n🎉 测试5通过: 报告生成集成正常")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🚀"*40)
    print("专家挑战闭环机制 - 完整测试套件")
    print("🚀"*40)
    
    results = []
    
    # 测试1: Accept闭环
    try:
        results.append(("Accept闭环", test_accept_closure()))
    except Exception as e:
        print(f"❌ Accept闭环测试失败: {e}")
        results.append(("Accept闭环", False))
    
    # 测试2: Synthesize闭环
    try:
        results.append(("Synthesize闭环", test_synthesize_closure()))
    except Exception as e:
        print(f"❌ Synthesize闭环测试失败: {e}")
        results.append(("Synthesize闭环", False))
    
    # 测试3: Escalate闭环
    try:
        results.append(("Escalate闭环", test_escalate_closure()))
    except Exception as e:
        print(f"❌ Escalate闭环测试失败: {e}")
        results.append(("Escalate闭环", False))
    
    # 测试4: 路由逻辑
    try:
        results.append(("路由逻辑", test_routing_logic()))
    except Exception as e:
        print(f"❌ 路由逻辑测试失败: {e}")
        results.append(("路由逻辑", False))
    
    # 测试5: 报告集成
    try:
        results.append(("报告集成", test_report_integration()))
    except Exception as e:
        print(f"❌ 报告集成测试失败: {e}")
        results.append(("报告集成", False))
    
    # 汇总结果
    print("\n" + "="*80)
    print("测试结果汇总")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print("\n" + "="*80)
    print(f"总计: {passed}/{total} 测试通过")
    print("="*80)
    
    if passed == total:
        print("\n🎉🎉🎉 所有测试通过！闭环机制实施成功！")
    else:
        print(f"\n⚠️ {total - passed} 个测试失败，请检查实现")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
