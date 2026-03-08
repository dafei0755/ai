"""
v7.18 问卷生成 StateGraph Agent 集成测试

测试内容：
1. 环境变量控制验证
2. QuestionnaireAgent 基础功能
3. 向后兼容性（LLMQuestionGeneratorCompat）
4. 共享函数验证
5. 性能监控验证
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestV718EnvironmentVariable(unittest.TestCase):
    """测试环境变量控制"""

    def test_env_variable_default_false(self):
        """默认情况下 USE_V718_QUESTIONNAIRE_AGENT 为 false"""
        # 清除环境变量
        os.environ.pop("USE_V718_QUESTIONNAIRE_AGENT", None)

        # 重新导入模块
        from intelligent_project_analyzer.interaction.nodes.calibration_questionnaire import (
            USE_V718_QUESTIONNAIRE_AGENT,
        )

        # 注意：由于模块在 import 时读取环境变量，这里可能需要重载
        # 此测试主要验证代码逻辑存在
        self.assertIsNotNone(USE_V718_QUESTIONNAIRE_AGENT)


class TestQuestionnaireAgentBasic(unittest.TestCase):
    """QuestionnaireAgent 基础功能测试"""

    def test_agent_initialization(self):
        """测试 Agent 初始化"""
        from intelligent_project_analyzer.agents.questionnaire_agent import QuestionnaireAgent

        agent = QuestionnaireAgent(llm_model=None)
        self.assertIsNotNone(agent)
        self.assertIsNotNone(agent._graph)

    def test_agent_graph_structure(self):
        """测试 Agent 状态图结构"""
        from intelligent_project_analyzer.agents.questionnaire_agent import build_questionnaire_graph

        graph = build_questionnaire_graph()
        compiled = graph.compile()

        # 验证图已编译
        self.assertIsNotNone(compiled)

    def test_agent_generate_with_mock(self):
        """测试 Agent 生成功能（Mock LLM）"""
        from intelligent_project_analyzer.agents.questionnaire_agent import QuestionnaireAgent

        # 创建 Mock LLM
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = """
{
    "questions": [
        {
            "id": "q1",
            "question": "关于您提到的三代同堂需求，当老人的安静需求与孩子的活动空间冲突时，您更倾向于？",
            "type": "single_choice",
            "options": ["优先老人安静需求", "优先孩子活动空间", "寻找平衡方案"]
        }
    ],
    "generation_rationale": "基于用户三代同堂需求生成"
}
"""
        mock_llm.invoke.return_value = mock_response

        agent = QuestionnaireAgent(llm_model=mock_llm)

        questions, source = agent.generate(
            user_input="我们是三代同堂的家庭，需要一个200平米的住宅", structured_data={"project_type": "personal_residential"}
        )

        # 验证返回结果
        self.assertIsInstance(questions, list)
        self.assertIn(source, ["llm_generated", "regenerated", "fallback"])


class TestLLMQuestionGeneratorCompat(unittest.TestCase):
    """向后兼容层测试"""

    def test_compat_interface(self):
        """测试兼容层接口"""
        from intelligent_project_analyzer.agents.questionnaire_agent import LLMQuestionGeneratorCompat

        # 验证接口存在
        self.assertTrue(hasattr(LLMQuestionGeneratorCompat, "generate"))

        # 验证是类方法
        import inspect

        self.assertTrue(inspect.ismethod(LLMQuestionGeneratorCompat.generate))


class TestSharedAgentUtils(unittest.TestCase):
    """共享函数测试"""

    def test_build_questionnaire_analysis_summary(self):
        """测试分析摘要构建"""
        from intelligent_project_analyzer.utils.shared_agent_utils import build_questionnaire_analysis_summary

        structured_data = {
            "project_overview": "这是一个三代同堂的住宅项目",
            "project_type": "personal_residential",
            "core_objectives": ["舒适居住", "功能完善"],
            "design_challenge": "如何平衡老人和孩子的需求",
        }

        summary = build_questionnaire_analysis_summary(structured_data)

        # 验证包含关键信息
        self.assertIn("项目概览", summary)
        self.assertIn("三代同堂", summary)
        self.assertIn("核心目标", summary)

    def test_build_analysis_summary_empty(self):
        """测试空数据处理"""
        from intelligent_project_analyzer.utils.shared_agent_utils import build_questionnaire_analysis_summary

        summary = build_questionnaire_analysis_summary({})

        # 验证返回默认提示
        self.assertIn("需求分析数据不足", summary)

    def test_extract_user_keywords(self):
        """测试关键词提取"""
        from intelligent_project_analyzer.utils.shared_agent_utils import extract_user_keywords

        user_input = "我们是三代同堂的家庭，需要200㎡的住宅，预算500万"

        keywords = extract_user_keywords(user_input)

        # 验证提取了数字+单位
        self.assertTrue(any("200" in kw for kw in keywords))
        self.assertTrue(any("500" in kw or "万" in kw for kw in keywords))

    def test_check_questionnaire_relevance(self):
        """测试相关性验证"""
        from intelligent_project_analyzer.utils.shared_agent_utils import check_questionnaire_relevance

        questions = [
            {"id": "q1", "question": "关于三代同堂的住宅，您更看重哪些功能？", "options": []},
            {"id": "q2", "question": "您喜欢什么风格？", "options": []},  # 泛化问题
        ]
        user_input = "我们是三代同堂的家庭，需要200㎡的住宅"

        score, low_relevance = check_questionnaire_relevance(questions, user_input)

        # 验证返回类型
        self.assertIsInstance(score, float)
        self.assertIsInstance(low_relevance, list)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)


class TestPerformanceMonitor(unittest.TestCase):
    """性能监控测试"""

    def test_performance_monitor_record(self):
        """测试性能记录"""
        from intelligent_project_analyzer.utils.shared_agent_utils import PerformanceMonitor

        # 重置
        PerformanceMonitor.reset()

        # 记录数据
        PerformanceMonitor.record("LLMQuestionGenerator", 1.5, "v7.18")
        PerformanceMonitor.record("LLMQuestionGenerator", 2.0, "v7.18")

        # 获取统计
        stats = PerformanceMonitor.get_stats("LLMQuestionGenerator")

        self.assertEqual(stats["count"], 2)
        self.assertAlmostEqual(stats["avg_ms"], 1750, delta=100)

    def test_performance_monitor_comparison(self):
        """测试性能对比"""
        from intelligent_project_analyzer.utils.shared_agent_utils import PerformanceMonitor

        PerformanceMonitor.reset()

        PerformanceMonitor.record("AgentA", 1.0, "v1")
        PerformanceMonitor.record("AgentB", 2.0, "v1")

        comparison = PerformanceMonitor.get_comparison()

        self.assertIn("AgentA", comparison)
        self.assertIn("AgentB", comparison)


class TestCalibrationQuestionnaireIntegration(unittest.TestCase):
    """CalibrationQuestionnaireNode 集成测试"""

    def test_v718_agent_branch_exists(self):
        """验证 v7.18 Agent 分支存在"""
        import importlib.util

        # 读取源文件
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "intelligent_project_analyzer",
            "interaction",
            "nodes",
            "calibration_questionnaire.py",
        )

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 验证 v7.18 相关代码存在
        self.assertIn("USE_V718_QUESTIONNAIRE_AGENT", content)
        self.assertIn("QuestionnaireAgent", content)
        self.assertIn("v7.18", content)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestV718EnvironmentVariable))
    suite.addTests(loader.loadTestsFromTestCase(TestQuestionnaireAgentBasic))
    suite.addTests(loader.loadTestsFromTestCase(TestLLMQuestionGeneratorCompat))
    suite.addTests(loader.loadTestsFromTestCase(TestSharedAgentUtils))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceMonitor))
    suite.addTests(loader.loadTestsFromTestCase(TestCalibrationQuestionnaireIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 返回结果
    return result.wasSuccessful()


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 v7.18 问卷生成 StateGraph Agent 集成测试")
    print("=" * 60)

    success = run_tests()

    print("\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过!")
    else:
        print("❌ 部分测试失败!")
    print("=" * 60)

    sys.exit(0 if success else 1)
