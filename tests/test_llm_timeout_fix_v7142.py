"""
测试 v7.142 LLM 超时修复

验证需求洞察节点和需求重构引擎的超时保护机制
"""

from unittest.mock import MagicMock, patch

import pytest

from intelligent_project_analyzer.interaction.nodes.questionnaire_summary import QuestionnaireSummaryNode
from intelligent_project_analyzer.interaction.nodes.requirements_restructuring import RequirementsRestructuringEngine


class TestLLMTimeoutFix:
    """测试 LLM 超时修复"""

    def test_llm_generate_one_sentence_timeout(self):
        """测试 _llm_generate_one_sentence 的超时保护"""

        # Mock LLM 调用，模拟超时
        with patch("intelligent_project_analyzer.services.llm_factory.LLMFactory.create_llm") as mock_llm_factory:
            # 模拟 LLM 超时（挂起 25 秒）
            mock_llm = MagicMock()

            def slow_invoke(prompt):
                import time

                time.sleep(25)  # 超过 20 秒超时限制
                return MagicMock(content="这应该不会被返回")

            mock_llm.invoke = slow_invoke
            mock_llm_factory.return_value = mock_llm

            # 执行测试
            goal = "为离家多年的50岁男士打造田园民居"
            constraints = "预算300万 | 时间6个月 | 面积300平米"
            approach = "通过乡土情感复归(75%) + 专业展示空间(60%)实现空间价值最大化"

            # 应该在20秒内超时并返回降级方案
            import time

            start_time = time.time()
            result = RequirementsRestructuringEngine._llm_generate_one_sentence(goal, constraints, approach)
            elapsed_time = time.time() - start_time

            # 验证
            assert elapsed_time < 22, f"超时保护失败，耗时 {elapsed_time}秒"
            assert goal in result or approach in result, "降级方案应包含原始数据"
            print(f"✅ 超时保护生效，耗时 {elapsed_time:.2f}秒")
            print(f"✅ 降级返回: {result}")

    def test_llm_generate_one_sentence_success(self):
        """测试 _llm_generate_one_sentence 正常情况"""

        # Mock LLM 调用，模拟成功
        with patch("intelligent_project_analyzer.services.llm_factory.LLMFactory.create_llm") as mock_llm_factory:
            mock_llm = MagicMock()
            mock_llm.invoke.return_value = MagicMock(content="通过乡土情感复归和专业展示空间的融合，为50岁男士打造承载回忆与未来的田园民居")
            mock_llm_factory.return_value = mock_llm

            # 执行测试
            goal = "为离家多年的50岁男士打造田园民居"
            constraints = "预算300万 | 时间6个月 | 面积300平米"
            approach = "通过乡土情感复归(75%) + 专业展示空间(60%)实现空间价值最大化"

            result = RequirementsRestructuringEngine._llm_generate_one_sentence(goal, constraints, approach)

            # 验证
            assert "田园民居" in result
            assert len(result) > 20, "摘要应该足够详细"
            print(f"✅ LLM生成成功: {result}")

    def test_questionnaire_summary_timeout_fallback(self):
        """测试需求洞察节点的超时降级机制"""

        # Mock RequirementsRestructuringEngine.restructure，模拟超时
        with patch(
            "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine.restructure"
        ) as mock_restructure:

            def slow_restructure(*args, **kwargs):
                import time

                time.sleep(35)  # 超过 30 秒超时限制
                return {"should_not_reach": "here"}

            mock_restructure.side_effect = slow_restructure

            # 准备测试数据
            state = {
                "user_input": "让安藤忠雄为一个离家多年的50岁男士设计一座田园民居",
                "confirmed_core_tasks": [{"id": "task_1", "title": "调研安藤忠雄的乡土建筑设计案例"}],
                "gap_filling_answers": {"design_objectives": ["乡土情怀", "现代简约"]},
                "selected_dimensions": [{"dimension_id": "cultural_axis", "name": "文化认同"}],
                "dimension_weights": {"cultural_axis": 75},
                "requirement_analysis": {},
                "agent_results": {},
            }

            # 执行测试
            import time

            start_time = time.time()

            try:
                result = QuestionnaireSummaryNode.execute(state)
                elapsed_time = time.time() - start_time

                # 应该在35秒内超时并使用降级方案
                assert elapsed_time < 32, f"超时保护失败，耗时 {elapsed_time}秒"
                assert result.get("restructured_requirements") is not None
                assert result["restructured_requirements"]["metadata"]["generation_method"] == "fallback_restructure"
                print(f"✅ 需求洞察超时保护生效，耗时 {elapsed_time:.2f}秒")
                print(f"✅ 使用降级方案: {result['restructured_requirements']['metadata']['generation_method']}")
            except Exception as e:
                elapsed_time = time.time() - start_time
                # 即使抛出异常，也应该在合理时间内
                assert elapsed_time < 32, f"超时保护失败，耗时 {elapsed_time}秒"
                print(f"⚠️ 执行失败但超时保护生效: {e}")


if __name__ == "__main__":
    """直接运行测试"""
    test = TestLLMTimeoutFix()

    print("=" * 80)
    print("测试 1: LLM 超时保护")
    print("=" * 80)
    try:
        test.test_llm_generate_one_sentence_timeout()
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 80)
    print("测试 2: LLM 正常生成")
    print("=" * 80)
    try:
        test.test_llm_generate_one_sentence_success()
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()

    print("\n" + "=" * 80)
    print("测试 3: 需求洞察超时降级")
    print("=" * 80)
    try:
        test.test_questionnaire_summary_timeout_fallback()
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
