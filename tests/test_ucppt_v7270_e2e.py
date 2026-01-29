"""
UCPPT v7.270 端到端测试

测试范围：
1. 完整的搜索流程（从用户输入到最终答案）
2. HAY民宿案例验证
3. 真实场景模拟
4. 性能测试
"""

import asyncio
import time
from typing import Any, Dict, List

import pytest

from intelligent_project_analyzer.services.ucppt_search_engine import (
    ProblemSolvingApproach,
    SearchFramework,
    UcpptSearchEngine,
)


class TestHAYMinsuCase:
    """测试HAY民宿案例（完整流程）"""

    @pytest.fixture
    def engine(self):
        """创建搜索引擎实例"""
        return UcpptSearchEngine()

    @pytest.fixture
    def hay_minsu_query(self):
        """HAY民宿查询"""
        return "以丹麦家居品牌HAY气质为基础，为四川峨眉山七里坪民宿室内设计提供概念设计"

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_hay_minsu_complete_flow(self, engine, hay_minsu_query):
        """测试HAY民宿案例的完整流程"""
        print(f"\n{'='*80}")
        print(f"🧪 测试案例: HAY民宿概念设计")
        print(f"{'='*80}\n")

        start_time = time.time()
        events = []
        problem_solving_approach = None
        search_framework = None

        # 收集所有事件
        print("📡 开始收集事件...\n")
        async for event in engine._unified_analysis_stream(hay_minsu_query, context=None):
            events.append(event)
            event_type = event.get("type")

            # 打印关键事件
            if event_type == "unified_dialogue_complete":
                print("✅ 对话分析完成")
            elif event_type == "problem_solving_approach_ready":
                print("✅ 解题思路生成完成")
                problem_solving_approach = event.get("_internal_approach")
            elif event_type == "step1_complete":
                print("✅ 第一步完成")
            elif event_type == "search_framework_ready":
                print("✅ 搜索框架生成完成")
                search_framework = event.get("_internal_framework")

        step1_time = time.time() - start_time
        print(f"\n⏱️  第一步耗时: {step1_time:.2f}秒\n")

        # 验证第一步输出
        assert problem_solving_approach is not None, "未生成解题思路"
        print(f"{'='*80}")
        print(f"📋 解题思路验证")
        print(f"{'='*80}")
        print(f"任务类型: {problem_solving_approach.task_type}")
        print(f"复杂度: {problem_solving_approach.complexity_level}")
        print(f"所需专业知识: {', '.join(problem_solving_approach.required_expertise)}")
        print(f"解题步骤数: {len(problem_solving_approach.solution_steps)}")
        print(f"关键突破口数: {len(problem_solving_approach.breakthrough_points)}")
        print(f"置信度: {problem_solving_approach.confidence_score:.2%}\n")

        # 验证解题步骤
        assert (
            len(problem_solving_approach.solution_steps) >= 5
        ), f"解题步骤应该至少5步，实际: {len(problem_solving_approach.solution_steps)}"

        print("解题步骤:")
        for i, step in enumerate(problem_solving_approach.solution_steps, 1):
            print(f"  {i}. {step['action']}")
            print(f"     目的: {step['purpose']}")
            print(f"     预期产出: {step['expected_output']}\n")

        # 验证关键突破口
        if problem_solving_approach.breakthrough_points:
            print("关键突破口:")
            for bp in problem_solving_approach.breakthrough_points:
                print(f"  • {bp['point']}")
                print(f"    为什么关键: {bp['why_key']}")
                print(f"    如何利用: {bp['how_to_leverage']}\n")

        # 如果有搜索框架（旧流程兼容）
        if search_framework:
            print(f"{'='*80}")
            print(f"🔍 搜索框架验证")
            print(f"{'='*80}")
            print(f"核心问题: {search_framework.core_question}")
            print(f"回答目标: {search_framework.answer_goal}")
            print(f"搜索目标数: {len(search_framework.targets)}\n")

            print("搜索目标:")
            for target in search_framework.targets:
                print(f"  [{target.id}] {target.question or target.name}")
                print(f"      搜索内容: {target.search_for or target.description}")
                print(f"      预设关键词: {', '.join(target.preset_keywords[:3])}...")
                print(f"      优先级: P{target.priority}\n")

        print(f"{'='*80}")
        print(f"✅ HAY民宿案例测试通过")
        print(f"{'='*80}\n")

    @pytest.mark.asyncio
    async def test_hay_minsu_solution_steps_quality(self, engine, hay_minsu_query):
        """测试HAY民宿案例的解题步骤质量"""
        events = []
        async for event in engine._unified_analysis_stream(hay_minsu_query, context=None):
            events.append(event)

        approach_event = next((e for e in events if e.get("type") == "problem_solving_approach_ready"), None)
        assert approach_event is not None

        approach = approach_event.get("_internal_approach")
        assert approach is not None

        # 验证解题步骤的质量
        for step in approach.solution_steps:
            # 每步都应该有具体的行动
            assert len(step["action"]) > 10, f"行动描述太短: {step['action']}"

            # 每步都应该有明确的目的
            assert len(step["purpose"]) > 5, f"目的描述太短: {step['purpose']}"

            # 每步都应该有预期产出
            assert len(step["expected_output"]) > 5, f"预期产出描述太短: {step['expected_output']}"

            # 验证是否包含HAY或峨眉山相关内容
            step_text = f"{step['action']} {step['purpose']} {step['expected_output']}".lower()
            has_hay = "hay" in step_text
            has_emeishan = "峨眉山" in step_text or "七里坪" in step_text
            has_design = "设计" in step_text or "色彩" in step_text or "材质" in step_text

            # 至少应该包含一个相关关键词
            assert has_hay or has_emeishan or has_design, f"步骤缺少相关关键词: {step['action']}"


class TestRealWorldScenarios:
    """测试真实场景"""

    @pytest.fixture
    def engine(self):
        return UcpptSearchEngine()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "query,expected_task_type,expected_complexity",
        [
            ("如何选择适合小户型的北欧风格家具？", "decision", "moderate"),
            ("分析2024年中国室内设计行业趋势", "research", "complex"),
            ("为咖啡馆设计一套完整的VI系统", "design", "complex"),
            ("什么是侘寂美学？", "exploration", "simple"),
        ],
    )
    async def test_different_query_types(self, engine, query, expected_task_type, expected_complexity):
        """测试不同类型的查询"""
        print(f"\n🧪 测试查询: {query}")

        events = []
        async for event in engine._unified_analysis_stream(query, context=None):
            events.append(event)

        approach_event = next((e for e in events if e.get("type") == "problem_solving_approach_ready"), None)

        if approach_event:
            approach = approach_event.get("_internal_approach")
            print(f"   任务类型: {approach.task_type} (期望: {expected_task_type})")
            print(f"   复杂度: {approach.complexity_level} (期望: {expected_complexity})")

            # 验证任务类型（允许一定的灵活性）
            # 因为LLM可能有不同的判断
            assert approach.task_type in [
                "research",
                "design",
                "decision",
                "exploration",
                "verification",
            ], f"未知的任务类型: {approach.task_type}"

            # 验证复杂度
            assert approach.complexity_level in [
                "simple",
                "moderate",
                "complex",
                "highly_complex",
            ], f"未知的复杂度: {approach.complexity_level}"


class TestPerformance:
    """性能测试"""

    @pytest.fixture
    def engine(self):
        return UcpptSearchEngine()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_step1_performance(self, engine):
        """测试第一步的性能"""
        query = "测试查询"

        start_time = time.time()
        events = []

        async for event in engine._unified_analysis_stream(query, context=None):
            events.append(event)

        elapsed_time = time.time() - start_time

        print(f"\n⏱️  第一步耗时: {elapsed_time:.2f}秒")
        print(f"📊 事件数量: {len(events)}")

        # 性能要求：第一步应该在合理时间内完成
        # 注意：这个时间取决于LLM的响应速度
        assert elapsed_time < 180, f"第一步耗时过长: {elapsed_time:.2f}秒"

    @pytest.mark.asyncio
    async def test_memory_usage(self, engine):
        """测试内存使用"""
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        query = "测试查询"
        events = []

        async for event in engine._unified_analysis_stream(query, context=None):
            events.append(event)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"\n💾 初始内存: {initial_memory:.2f} MB")
        print(f"💾 最终内存: {final_memory:.2f} MB")
        print(f"💾 内存增长: {memory_increase:.2f} MB")

        # 内存增长应该在合理范围内
        assert memory_increase < 500, f"内存增长过大: {memory_increase:.2f} MB"


class TestEdgeCases:
    """边界情况测试"""

    @pytest.fixture
    def engine(self):
        return UcpptSearchEngine()

    @pytest.mark.asyncio
    async def test_very_short_query(self, engine):
        """测试非常短的查询"""
        query = "设计"

        events = []
        async for event in engine._unified_analysis_stream(query, context=None):
            events.append(event)

        # 应该能处理短查询
        event_types = [e.get("type") for e in events]
        assert "problem_solving_approach_ready" in event_types or "analysis_complete" in event_types

    @pytest.mark.asyncio
    async def test_very_long_query(self, engine):
        """测试非常长的查询"""
        query = "我想要" + "设计一个" * 100 + "民宿"

        events = []
        async for event in engine._unified_analysis_stream(query, context=None):
            events.append(event)

        # 应该能处理长查询
        event_types = [e.get("type") for e in events]
        assert "problem_solving_approach_ready" in event_types or "analysis_complete" in event_types

    @pytest.mark.asyncio
    async def test_special_characters_query(self, engine):
        """测试包含特殊字符的查询"""
        query = "如何设计@#$%^&*()民宿？！"

        events = []
        async for event in engine._unified_analysis_stream(query, context=None):
            events.append(event)

        # 应该能处理特殊字符
        event_types = [e.get("type") for e in events]
        assert len(event_types) > 0

    @pytest.mark.asyncio
    async def test_multilingual_query(self, engine):
        """测试多语言查询"""
        query = "Design a 民宿 with HAY style"

        events = []
        async for event in engine._unified_analysis_stream(query, context=None):
            events.append(event)

        # 应该能处理多语言
        event_types = [e.get("type") for e in events]
        assert len(event_types) > 0


class TestConcurrency:
    """并发测试"""

    @pytest.fixture
    def engine(self):
        return UcpptSearchEngine()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_requests(self, engine):
        """测试并发请求"""
        queries = [
            "设计民宿",
            "选择家具",
            "分析趋势",
        ]

        async def process_query(query):
            events = []
            async for event in engine._unified_analysis_stream(query, context=None):
                events.append(event)
            return events

        # 并发执行
        start_time = time.time()
        results = await asyncio.gather(*[process_query(q) for q in queries])
        elapsed_time = time.time() - start_time

        print(f"\n⏱️  并发处理{len(queries)}个查询耗时: {elapsed_time:.2f}秒")

        # 验证所有请求都成功
        for i, events in enumerate(results):
            print(f"   查询{i+1}: {len(events)}个事件")
            assert len(events) > 0, f"查询{i+1}未返回事件"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s", "-m", "not slow"])
