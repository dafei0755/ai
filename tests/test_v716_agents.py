"""
v7.16 LangGraph Agent 架构升级测试

测试新创建的 5 个 LangGraph Agent：
1. AnalysisReviewAgent
2. ResultAggregatorAgentV2
3. ChallengeDetectionAgent
4. QualityPreflightAgent
5. QuestionnaireAgent

运行方式:
    python tests/test_v716_agents.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger


def test_analysis_review_agent():
    """测试 AnalysisReviewAgent 图结构"""
    print("\n" + "=" * 60)
    print("测试 1: AnalysisReviewAgent 图结构")
    print("=" * 60)
    
    try:
        from intelligent_project_analyzer.agents.analysis_review_agent import (
            AnalysisReviewAgent,
            build_analysis_review_graph
        )
        
        # 测试图构建
        graph = build_analysis_review_graph()
        compiled = graph.compile()
        
        print(f"✅ 图类型: {type(compiled).__name__}")
        print(f"✅ 节点: {list(compiled.nodes.keys()) if hasattr(compiled, 'nodes') else '编译成功'}")
        
        # 测试 Agent 初始化
        agent = AnalysisReviewAgent(llm_model=None)
        print(f"✅ Agent 初始化成功")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_result_aggregator_agent():
    """测试 ResultAggregatorAgentV2 图结构"""
    print("\n" + "=" * 60)
    print("测试 2: ResultAggregatorAgentV2 图结构")
    print("=" * 60)
    
    try:
        from intelligent_project_analyzer.agents.result_aggregator_agent import (
            ResultAggregatorAgentV2,
            build_result_aggregator_graph
        )
        
        # 测试图构建
        graph = build_result_aggregator_graph()
        compiled = graph.compile()
        
        print(f"✅ 图类型: {type(compiled).__name__}")
        
        # 测试 Agent 初始化
        agent = ResultAggregatorAgentV2(llm_model=None)
        print(f"✅ Agent 初始化成功")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_challenge_detection_agent():
    """测试 ChallengeDetectionAgent 图结构"""
    print("\n" + "=" * 60)
    print("测试 3: ChallengeDetectionAgent 图结构")
    print("=" * 60)
    
    try:
        from intelligent_project_analyzer.agents.challenge_detection_agent import (
            ChallengeDetectionAgent,
            build_challenge_detection_graph
        )
        
        # 测试图构建
        graph = build_challenge_detection_graph()
        compiled = graph.compile()
        
        print(f"✅ 图类型: {type(compiled).__name__}")
        
        # 测试 Agent 初始化
        agent = ChallengeDetectionAgent()
        print(f"✅ Agent 初始化成功")
        
        # 测试执行（空状态）
        result = agent.execute({
            "agent_results": {},
            "batch_results": {}
        })
        print(f"✅ 执行成功: {result.get('has_active_challenges', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_quality_preflight_agent():
    """测试 QualityPreflightAgent 图结构"""
    print("\n" + "=" * 60)
    print("测试 4: QualityPreflightAgent 图结构")
    print("=" * 60)
    
    try:
        from intelligent_project_analyzer.agents.quality_preflight_agent import (
            QualityPreflightAgent,
            build_quality_preflight_graph
        )
        
        # 测试图构建
        graph = build_quality_preflight_graph()
        compiled = graph.compile()
        
        print(f"✅ 图类型: {type(compiled).__name__}")
        
        # 测试 Agent 初始化
        agent = QualityPreflightAgent(llm_model=None)
        print(f"✅ Agent 初始化成功")
        
        # 测试执行（模拟状态）
        result = agent.execute({
            "active_agents": ["V3_测试专家", "V4_设计师"],
            "strategic_analysis": {
                "selected_roles": [
                    {"role_id": "V3_测试专家", "dynamic_role_name": "测试专家", "task": "执行测试任务"},
                    {"role_id": "V4_设计师", "dynamic_role_name": "设计师", "task": "设计任务"}
                ]
            },
            "user_input": "测试用户输入"
        })
        print(f"✅ 执行成功: {len(result.get('quality_checklists', {}))} 个检查清单")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_questionnaire_agent():
    """测试 QuestionnaireAgent 图结构"""
    print("\n" + "=" * 60)
    print("测试 5: QuestionnaireAgent 图结构")
    print("=" * 60)
    
    try:
        from intelligent_project_analyzer.agents.questionnaire_agent import (
            QuestionnaireAgent,
            build_questionnaire_graph
        )
        
        # 测试图构建
        graph = build_questionnaire_graph()
        compiled = graph.compile()
        
        print(f"✅ 图类型: {type(compiled).__name__}")
        
        # 测试 Agent 初始化
        agent = QuestionnaireAgent(llm_model=None)
        print(f"✅ Agent 初始化成功")
        
        # 测试执行（无LLM，会使用回退方案）
        questions, source = agent.generate(
            user_input="我想设计一个三代同堂的住宅，面积150平米",
            structured_data={
                "project_type": "personal_residential",
                "project_overview": "三代同堂住宅设计"
            }
        )
        print(f"✅ 执行成功: {len(questions)} 个问题, 来源: {source}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_followup_agent():
    """测试 FollowupAgent 图结构 (v7.15)"""
    print("\n" + "=" * 60)
    print("测试 6: FollowupAgent 图结构 (v7.15)")
    print("=" * 60)
    
    try:
        from intelligent_project_analyzer.agents.followup_agent import (
            FollowupAgent,
            build_followup_agent  # v7.15 使用的函数名
        )
        
        # 测试图构建 (build_followup_agent 已返回编译后的图)
        compiled = build_followup_agent()
        
        print(f"✅ 图类型: {type(compiled).__name__}")
        
        # 测试 Agent 初始化 (v7.15 无参数构造)
        agent = FollowupAgent()
        print(f"✅ Agent 初始化成功")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("  v7.16 LangGraph Agent 架构升级测试")
    print("=" * 70)
    
    results = []
    
    # 运行测试
    results.append(("AnalysisReviewAgent", test_analysis_review_agent()))
    results.append(("ResultAggregatorAgentV2", test_result_aggregator_agent()))
    results.append(("ChallengeDetectionAgent", test_challenge_detection_agent()))
    results.append(("QualityPreflightAgent", test_quality_preflight_agent()))
    results.append(("QuestionnaireAgent", test_questionnaire_agent()))
    results.append(("FollowupAgent", test_followup_agent()))
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("  测试结果汇总")
    print("=" * 70)
    
    passed = 0
    failed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print("-" * 70)
    print(f"  通过: {passed}/{len(results)}, 失败: {failed}/{len(results)}")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
