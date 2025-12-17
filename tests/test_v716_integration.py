"""
v7.16 集成测试 - 真实工作流中验证 USE_V716_AGENTS=true 路径

测试内容:
1. 环境变量控制验证
2. 新旧版本接口兼容性
3. 状态传递正确性
4. 性能对比
"""

import os
import sys
import time
import unittest
from typing import Dict, Any

# 设置环境变量（必须在导入之前）
os.environ["USE_V716_AGENTS"] = "true"

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger


class TestV716Integration(unittest.TestCase):
    """v7.16 集成测试套件"""
    
    @classmethod
    def setUpClass(cls):
        """测试前设置"""
        logger.info("=" * 60)
        logger.info("v7.16 集成测试 - USE_V716_AGENTS=true")
        logger.info("=" * 60)
    
    def test_01_environment_variable_control(self):
        """测试1: 环境变量控制验证"""
        print("\n" + "=" * 50)
        print("测试 1: 环境变量控制验证")
        print("=" * 50)
        
        use_v716 = os.getenv("USE_V716_AGENTS", "false").lower() == "true"
        self.assertTrue(use_v716, "USE_V716_AGENTS 应为 true")
        
        try:
            from intelligent_project_analyzer.agents.challenge_detection_agent import ChallengeDetectionAgent
            from intelligent_project_analyzer.agents.quality_preflight_agent import QualityPreflightAgent
            from intelligent_project_analyzer.agents.result_aggregator_agent import ResultAggregatorAgentV2
            from intelligent_project_analyzer.agents.analysis_review_agent import AnalysisReviewAgent
            from intelligent_project_analyzer.agents.questionnaire_agent import QuestionnaireAgent
            print("✅ 所有 v7.16 Agent 导入成功")
        except ImportError as e:
            self.fail(f"v7.16 Agent 导入失败: {e}")
    
    def test_02_challenge_detection_compatibility(self):
        """测试2: 挑战检测兼容性"""
        print("\n" + "=" * 50)
        print("测试 2: ChallengeDetectionAgent 兼容性")
        print("=" * 50)
        
        test_state = {
            "agent_results": {"V4_设计研究员_4-1": {"structured_data": {"analysis": "完成"}}},
            "batch_results": {}
        }
        
        from intelligent_project_analyzer.agents.challenge_detection_agent import detect_and_handle_challenges_v2
        from intelligent_project_analyzer.agents.dynamic_project_director import detect_and_handle_challenges_node
        
        start = time.time()
        result_new = detect_and_handle_challenges_v2(test_state)
        new_time = time.time() - start
        
        start = time.time()
        result_old = detect_and_handle_challenges_node(test_state)
        old_time = time.time() - start
        
        self.assertIn("challenge_detection", result_new)
        self.assertEqual(result_new.get("has_active_challenges"), result_old.get("has_active_challenges"))
        
        print(f"✅ 新版: {new_time*1000:.2f}ms, 原版: {old_time*1000:.2f}ms")
        print(f"✅ 结果一致性验证通过")
    
    def test_03_quality_preflight_compatibility(self):
        """测试3: 质量预检兼容性"""
        print("\n" + "=" * 50)
        print("测试 3: QualityPreflightAgent 兼容性")
        print("=" * 50)
        
        test_state = {
            "selected_roles": [{"role_id": "4-1", "role_name": "设计研究员", "dynamic_role_name": "研究专家"}],
            "confirmed_requirements": {"user_input": "设计一套住宅"}
        }
        
        from intelligent_project_analyzer.agents.quality_preflight_agent import QualityPreflightAgent
        
        agent = QualityPreflightAgent()
        start = time.time()
        result = agent.execute(test_state)
        exec_time = time.time() - start
        
        self.assertIn("quality_checklists", result)
        self.assertIn("preflight_completed", result)
        
        print(f"✅ 执行时间: {exec_time*1000:.2f}ms")
        print(f"✅ 预检完成: {result.get('preflight_completed')}")
    
    def test_04_questionnaire_agent_compatibility(self):
        """测试4: 问卷生成兼容性"""
        print("\n" + "=" * 50)
        print("测试 4: QuestionnaireAgent 兼容性")
        print("=" * 50)
        
        from intelligent_project_analyzer.agents.questionnaire_agent import QuestionnaireAgent
        
        agent = QuestionnaireAgent()
        start = time.time()
        result = agent.generate(
            user_input="我需要一套150平米的住宅设计",
            structured_data={"project_type": "住宅设计"}
        )
        exec_time = time.time() - start
        
        # 返回格式可能是 tuple 或 dict
        if isinstance(result, tuple):
            questions, source = result
        else:
            questions = result.get("questions", [])
            source = result.get("source", "unknown")
        
        self.assertTrue(len(questions) > 0)
        print(f"✅ 执行时间: {exec_time*1000:.2f}ms")
        print(f"✅ 问题数量: {len(questions)}, 来源: {source}")
    
    def test_05_result_aggregator_compatibility(self):
        """测试5: 结果聚合兼容性"""
        print("\n" + "=" * 50)
        print("测试 5: ResultAggregatorAgentV2 兼容性")
        print("=" * 50)
        
        test_state = {
            "user_input": "设计一套住宅",
            "agent_results": {"V4_4-1": {"content": "分析报告", "structured_data": {"发现": "需求明确"}}},
            "selected_roles": [{"role_id": "4-1", "dynamic_role_name": "研究专家"}],
            "confirmed_requirements": {"user_input": "设计一套住宅"}
        }
        
        from intelligent_project_analyzer.agents.result_aggregator_agent import ResultAggregatorAgentV2
        
        agent = ResultAggregatorAgentV2()
        start = time.time()
        result = agent.execute(test_state)
        exec_time = time.time() - start
        
        # 验证有返回结果
        self.assertIsNotNone(result)
        print(f"✅ 执行时间: {exec_time*1000:.2f}ms")
        print(f"✅ 返回字段: {list(result.keys())[:5]}...")
    
    def test_06_analysis_review_compatibility(self):
        """测试6: 分析审核兼容性"""
        print("\n" + "=" * 50)
        print("测试 6: AnalysisReviewAgent 兼容性")
        print("=" * 50)
        
        from intelligent_project_analyzer.agents.analysis_review_agent import AnalysisReviewAgent
        from intelligent_project_analyzer.agents.base import NullLLM
        
        null_llm = NullLLM("test")
        agent = AnalysisReviewAgent(llm_model=null_llm)
        
        self.assertIsNotNone(agent._graph)
        print(f"✅ Agent 初始化成功")
        print(f"✅ 图类型: {type(agent._graph).__name__}")
    
    def test_07_state_passing_correctness(self):
        """测试7: 状态传递正确性"""
        print("\n" + "=" * 50)
        print("测试 7: 状态传递正确性")
        print("=" * 50)
        
        from intelligent_project_analyzer.agents.challenge_detection_agent import ChallengeDetectionAgent
        
        test_state = {
            "agent_results": {"expert_1": {"structured_data": {"challenge_flags": [{"item": "A"}]}}},
            "batch_results": {}
        }
        
        agent = ChallengeDetectionAgent()
        result = agent.execute(test_state)
        
        self.assertIn("processing_log", result)
        print(f"✅ 处理日志: {len(result['processing_log'])} 条")
    
    def test_08_performance_comparison(self):
        """测试8: 性能对比"""
        print("\n" + "=" * 50)
        print("测试 8: 性能对比汇总")
        print("=" * 50)
        
        from intelligent_project_analyzer.agents.challenge_detection_agent import ChallengeDetectionAgent
        from intelligent_project_analyzer.agents.dynamic_project_director import detect_and_handle_challenges_node
        
        test_state = {"agent_results": {}, "batch_results": {}}
        agent = ChallengeDetectionAgent()
        
        # 新版
        start = time.time()
        for _ in range(10):
            agent.execute(test_state)
        new_avg = (time.time() - start) / 10 * 1000
        
        # 原版
        start = time.time()
        for _ in range(10):
            detect_and_handle_challenges_node(test_state)
        old_avg = (time.time() - start) / 10 * 1000
        
        overhead = (new_avg - old_avg) / old_avg * 100 if old_avg > 0 else 0
        
        print(f"\n性能对比:")
        print(f"  新版 Agent: {new_avg:.2f}ms/次")
        print(f"  原版函数:   {old_avg:.2f}ms/次")
        print(f"  开销增加:   {overhead:.1f}%")
        print(f"\n⚠️ 注意: LangGraph 图执行有固定开销，但提供更好的可追踪性")


if __name__ == "__main__":
    print("=" * 60)
    print("v7.16 集成测试 - USE_V716_AGENTS=true")
    print("=" * 60)
    
    unittest.main(verbosity=2)
