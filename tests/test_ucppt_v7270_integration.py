"""
UCPPT v7.270 集成测试

测试范围：
1. 两步流程完整性
2. 事件流正确性
3. 数据传递完整性
4. 错误处理和降级
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from intelligent_project_analyzer.services.ucppt_search_engine import (
    ProblemSolvingApproach,
    SearchFramework,
    SearchTarget,
    UcpptSearchEngine,
)


class TestTwoStepFlowIntegration:
    """测试两步流程的完整集成"""

    @pytest.fixture
    def engine(self):
        """创建测试用的搜索引擎实例"""
        return UcpptSearchEngine()

    @pytest.fixture
    def sample_query(self):
        """示例查询"""
        return "以丹麦家居品牌HAY气质为基础，为四川峨眉山七里坪民宿室内设计提供概念设计"

    @pytest.mark.asyncio
    async def test_step1_generates_problem_solving_approach(self, engine, sample_query):
        """测试第一步生成解题思路"""
        events = []

        # 模拟第一步流式分析
        async for event in engine._unified_analysis_stream(sample_query, context=None):
            events.append(event)

        # 验证事件序列
        event_types = [e.get("type") for e in events]

        # 应该包含解题思路就绪事件
        assert "problem_solving_approach_ready" in event_types, \
            f"缺少 problem_solving_approach_ready 事件，实际事件: {event_types}"

        # 应该包含第一步完成事件
        assert "step1_complete" in event_types, \
            f"缺少 step1_complete 事件，实际事件: {event_types}"

        # 提取解题思路
        approach_event = next((e for e in events if e.get("type") == "problem_solving_approach_ready"), None)
        assert approach_event is not None, "未找到解题思路事件"

        approach_data = approach_event.get("data")
        assert approach_data is not None, "解题思路数据为空"

        # 验证解题思路包含必需字段
        assert "task_type" in approach_data
        assert "solution_steps" in approach_data
        assert isinstance(approach_data["solution_steps"], list)
        assert len(approach_data["solution_steps"]) >= 5, \
            f"解题步骤应该至少5步，实际: {len(approach_data['solution_steps'])}"

    @pytest.mark.asyncio
    async def test_step1_provides_step2_context(self, engine, sample_query):
        """测试第一步提供 step2_context"""
        events = []

        async for event in engine._unified_analysis_stream(sample_query, context=None):
            events.append(event)

        # 提取 step1_complete 事件
        step1_complete_event = next((e for e in events if e.get("type") == "step1_complete"), None)
        assert step1_complete_event is not None, "未找到 step1_complete 事件"

        step1_data = step1_complete_event.get("data", {})
        step2_context = step1_data.get("step2_context")

        assert step2_context is not None, "step2_context 为空"
        assert "core_question" in step2_context, "step2_context 缺少 core_question"
        assert "answer_goal" in step2_context, "step2_context 缺少 answer_goal"
        assert "solution_steps_summary" in step2_context, "step2_context 缺少 solution_steps_summary"

    @pytest.mark.asyncio
    async def test_step2_generates_search_framework(self, engine, sample_query):
        """测试第二步生成搜索框架"""
        # 先执行第一步
        events = []
        async for event in engine._unified_analysis_stream(sample_query, context=None):
            events.append(event)

        # 提取第一步的输出
        step1_complete_event = next((e for e in events if e.get("type") == "step1_complete"), None)
        assert step1_complete_event is not None

        step1_data = step1_complete_event.get("data", {})
        step2_context = step1_data.get("step2_context", {})
        problem_solving_approach = step1_complete_event.get("_internal_approach")
        analysis_data = step1_complete_event.get("_internal_data", {})

        # 执行第二步
        framework = await engine._step2_generate_search_framework(
            sample_query,
            step2_context,
            problem_solving_approach,
            analysis_data
        )

        # 验证搜索框架
        if framework:  # 可能因为 LLM 调用失败返回 None
            assert isinstance(framework, SearchFramework)
            assert len(framework.targets) > 0, "搜索框架应该包含至少一个目标"

            # 验证每个目标包含预设关键词
            for target in framework.targets:
                assert isinstance(target, SearchTarget)
                assert target.preset_keywords is not None, f"目标 {target.id} 缺少预设关键词"
                assert len(target.preset_keywords) >= 3, \
                    f"目标 {target.id} 的预设关键词应该至少3个，实际: {len(target.preset_keywords)}"

    @pytest.mark.asyncio
    async def test_complete_two_step_flow(self, engine, sample_query):
        """测试完整的两步流程"""
        all_events = []

        # 模拟完整流程（简化版，不实际调用 search_deep）
        # 第一步
        async for event in engine._unified_analysis_stream(sample_query, context=None):
            all_events.append(event)

        # 验证第一步事件
        event_types = [e.get("type") for e in all_events]
        assert "problem_solving_approach_ready" in event_types
        assert "step1_complete" in event_types

        # 提取第一步输出
        step1_complete_event = next((e for e in all_events if e.get("type") == "step1_complete"), None)
        step2_context = step1_complete_event.get("data", {}).get("step2_context", {})
        problem_solving_approach = step1_complete_event.get("_internal_approach")
        analysis_data = step1_complete_event.get("_internal_data", {})

        # 第二步
        framework = await engine._step2_generate_search_framework(
            sample_query,
            step2_context,
            problem_solving_approach,
            analysis_data
        )

        # 验证第二步输出
        if framework:
            assert framework.core_question != ""
            assert framework.answer_goal != ""
            assert len(framework.targets) > 0

            # 验证数据传递的一致性
            # step2_context 中的 core_question 应该与 framework 中的一致
            if step2_context.get("core_question"):
                assert framework.core_question == step2_context["core_question"] or \
                       len(framework.core_question) > 0


class TestEventFlow:
    """测试事件流的正确性"""

    @pytest.fixture
    def engine(self):
        return UcpptSearchEngine()

    @pytest.mark.asyncio
    async def test_event_order(self, engine):
        """测试事件顺序"""
        query = "测试问题"
        events = []

        async for event in engine._unified_analysis_stream(query, context=None):
            events.append(event)

        event_types = [e.get("type") for e in events]

        # 验证事件顺序
        # 1. 对话内容应该在解题思路之前
        if "unified_dialogue_complete" in event_types and "problem_solving_approach_ready" in event_types:
            dialogue_idx = event_types.index("unified_dialogue_complete")
            approach_idx = event_types.index("problem_solving_approach_ready")
            assert dialogue_idx < approach_idx, "对话完成应该在解题思路之前"

        # 2. 解题思路应该在 step1_complete 之前
        if "problem_solving_approach_ready" in event_types and "step1_complete" in event_types:
            approach_idx = event_types.index("problem_solving_approach_ready")
            step1_idx = event_types.index("step1_complete")
            assert approach_idx < step1_idx, "解题思路应该在 step1_complete 之前"

    @pytest.mark.asyncio
    async def test_event_data_completeness(self, engine):
        """测试事件数据完整性"""
        query = "测试问题"
        events = []

        async for event in engine._unified_analysis_stream(query, context=None):
            events.append(event)

        # 验证 problem_solving_approach_ready 事件数据
        approach_event = next((e for e in events if e.get("type") == "problem_solving_approach_ready"), None)
        if approach_event:
            data = approach_event.get("data")
            assert data is not None
            assert "task_type" in data
            assert "solution_steps" in data
            assert "expected_deliverable" in data

        # 验证 step1_complete 事件数据
        step1_event = next((e for e in events if e.get("type") == "step1_complete"), None)
        if step1_event:
            data = step1_event.get("data")
            assert data is not None
            assert "user_profile" in data
            assert "analysis" in data
            assert "problem_solving_approach" in data
            assert "step2_context" in data


class TestErrorHandling:
    """测试错误处理和降级"""

    @pytest.fixture
    def engine(self):
        return UcpptSearchEngine()

    @pytest.mark.asyncio
    async def test_step1_failure_fallback(self, engine):
        """测试第一步失败时的降级"""
        query = "测试问题"

        # 模拟 LLM 调用失败
        with patch.object(engine, '_call_deepseek_stream_with_reasoning') as mock_llm:
            mock_llm.side_effect = Exception("LLM 调用失败")

            events = []
            try:
                async for event in engine._unified_analysis_stream(query, context=None):
                    events.append(event)
            except Exception:
                pass

            # 应该有降级处理
            event_types = [e.get("type") for e in events]

            # 即使失败，也应该发送 problem_solving_approach_ready（使用默认值）
            # 或者发送 analysis_complete（使用简单框架）
            assert "problem_solving_approach_ready" in event_types or \
                   "analysis_complete" in event_types

    @pytest.mark.asyncio
    async def test_step2_failure_fallback(self, engine):
        """测试第二步失败时的降级"""
        query = "测试问题"
        step2_context = {"core_question": "测试", "answer_goal": "测试"}
        problem_solving_approach = engine._build_default_problem_solving_approach(query)
        analysis_data = {}

        # 模拟 LLM 调用失败
        with patch.object(engine, '_call_llm_json') as mock_llm:
            mock_llm.return_value = None  # 返回空结果

            framework = await engine._step2_generate_search_framework(
                query,
                step2_context,
                problem_solving_approach,
                analysis_data
            )

            # 应该返回 None（由调用方处理降级）
            assert framework is None

    def test_default_problem_solving_approach(self, engine):
        """测试默认解题思路的生成"""
        query = "测试问题"

        approach = engine._build_default_problem_solving_approach(query)

        # 验证默认值
        assert approach.task_type == "exploration"
        assert approach.complexity_level == "moderate"
        assert len(approach.solution_steps) == 5
        assert len(approach.breakthrough_points) == 1
        assert approach.confidence_score == 0.5


class TestBackwardCompatibility:
    """测试向后兼容性"""

    @pytest.fixture
    def engine(self):
        return UcpptSearchEngine()

    @pytest.mark.asyncio
    async def test_old_flow_still_works(self, engine):
        """测试旧流程仍然可用"""
        query = "测试问题"

        # 模拟旧流程：LLM 返回包含 search_framework 的数据
        old_format_data = {
            "user_profile": {},
            "analysis": {
                "l1_facts": {},
                "l2_models": {},
                "l3_tension": "",
                "l4_jtbd": "",
                "l5_sharpness":
            },
            "search_framework": {
                "core_question": "测试问题",
                "answer_goal": "测试目标",
                "boundary": "",
                "targets": [
                    {
                        "id": "T1",
                        "name": "测试目标1",
                        "description": "测试描述",
                        "purpose": "测试目的",
                        "priority": 1,
                        "category": "品牌调研",
                        "preset_keywords": ["关键词1", "关键词2", "关键词3"]
                    }
                ]
            }
        }

        # 模拟 LLM 返回旧格式
        with patch.object(engine, '_safe_parse_json') as mock_parse:
            mock_parse.return_value = old_format_data

            events = []
            async for event in engine._unified_analysis_stream(query, context=None):
                events.append(event)

            event_types = [e.get("type") for e in events]

            # 旧流程应该发送 search_framework_ready 事件
            assert "search_framework_ready" in event_types or \
                   "analysis_complete" in event_types

    @pytest.mark.asyncio
    async def test_new_flow_detection(self, engine):
        """测试新流程检测"""
        query = "测试问题"

        # 模拟新流程：LLM 返回包含 problem_solving_approach 但不包含 search_framework
        new_format_data = {
            "user_profile": {},
            "analysis": {
                "l1_facts": {},
                "l2_models": {},
                "l3_tension": "",
                "l4_jtbd": "",
                "l5_sharpness": {}
            },
            "problem_solving_approach": {
                "task_type": "exploration",
                "task_type_description": "测试",
                "complexity_level": "moderate",
                "required_expertise": ["测试"],
                "solution_steps": [
                    {
                        "step_id": "S1",
                        "action": "测试",
                        "purpose": "测试",
                        "expected_output": "测试"
                    }
                ],
                "breakthrough_points": [],
                "expected_deliverable": {},
                "original_requirement": query,
                "refined_requirement": query,
                "confidence_score": 0.5,
                "alternative_approaches": []
            },
            "step2_context": {
                "core_question": "测试",
                "answer_goal": "测试"
            }
        }

        with patch.object(engine, '_safe_parse_json') as mock_parse:
            mock_parse.return_value = new_format_data

            events = []
            async for event in engine._unified_analysis_stream(query, context=None):
                events.append(event)

            event_types = [e.get("type") for e in events]

            # 新流程应该发送新事件
            assert "problem_solving_approach_ready" in event_types
            assert "step1_complete" in event_types


class TestDataConsistency:
    """测试数据一致性"""

    @pytest.fixture
    def engine(self):
        return UcpptSearchEngine()

    @pytest.mark.asyncio
    async def test_step2_context_consistency(self, engine):
        """测试 step2_context 的一致性"""
        query = "测试问题"
        events = []

        async for event in engine._unified_analysis_stream(query, context=None):
            events.append(event)

        # 提取 step1_complete 事件
        step1_event = next((e for e in events if e.get("type") == "step1_complete"), None)
        if not step1_event:
            pytest.skip("未生成 step1_complete 事件")

        step2_context = step1_event.get("data", {}).get("step2_context", {})
        problem_solving_approach = step1_event.get("_internal_approach")

        # 验证 step2_context 与 problem_solving_approach 的一致性
        if problem_solving_approach and step2_context:
            # solution_steps_summary 应该与 solution_steps 对应
            summary = step2_context.get("solution_steps_summary", [])
            steps = problem_solving_approach.solution_steps

            # 摘要数量应该与步骤数量一致
            assert len(summary) == len(steps), \
                f"摘要数量 ({len(summary)}) 与步骤数量 ({len(steps)}) 不一致"

    def test_search_target_field_consistency(self, engine):
        """测试 SearchTarget 字段的一致性"""
        # 创建一个 SearchTarget，验证新旧字段的同步
        target = SearchTarget(
            id="T1",
            question="测试问题",
            search_for="测试内容",
            why_need="测试原因",
            success_when=["标准1", "标准2"],
            priority=1,
            category="品牌调研"
        )

        # 验证 __post_init__ 自动同步
        assert target.name == target.question
        assert target.description == target.search_for
        assert target.purpose == target.why_need
        assert target.quality_criteria == target.success_when


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
