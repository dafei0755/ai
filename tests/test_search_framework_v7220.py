"""
SearchFramework v7.220 系统测试套件
测试新的 SearchTarget 和 SearchFramework 类及其集成

测试范围：
1. 单元测试：SearchTarget, SearchFramework 类
2. 集成测试：search_deep() 主流程
3. 端到端测试：完整搜索流程
4. 回归测试：确保旧功能正常
"""

import asyncio
import os
import sys
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from intelligent_project_analyzer.services.ucppt_search_engine import SearchFramework, SearchTarget, UcpptSearchEngine

# ==================== 单元测试：SearchTarget ====================


class TestSearchTarget:
    """SearchTarget 类单元测试"""

    def test_search_target_creation(self):
        """测试 SearchTarget 创建"""
        target = SearchTarget(
            id="T1",
            name="技术实现方案",
            description="技术实现的详细方案",
            purpose="了解具体的技术实现细节",
            priority=1,
        )

        assert target.id == "T1"
        assert target.name == "技术实现方案"
        assert target.description == "技术实现的详细方案"
        assert target.purpose == "了解具体的技术实现细节"
        assert target.priority == 1
        assert target.status == "pending"
        assert target.completion_score == 0.0
        assert target.sources == []

    def test_search_target_is_complete(self):
        """测试 is_complete() 方法"""
        target = SearchTarget(
            id="T1",
            name="测试目标",
            description="测试描述",
            purpose="测试",
            priority=1,
        )

        # 初始状态：未完成
        assert not target.is_complete()

        # 设置为 complete
        target.status = "complete"
        assert target.is_complete()

        # 高完成度也算完成
        target.status = "partial"
        target.completion_score = 0.85
        assert target.is_complete()

        # 低完成度不算完成
        target.completion_score = 0.7
        assert not target.is_complete()

    def test_search_target_mark_complete(self):
        """测试 mark_complete() 方法"""
        target = SearchTarget(
            id="T1",
            name="测试目标",
            description="测试描述",
            purpose="测试",
            priority=1,
        )

        target.mark_complete(0.9)

        assert target.status == "complete"
        assert target.completion_score == 0.9

    def test_search_target_add_info(self):
        """测试添加信息"""
        target = SearchTarget(
            id="T1",
            name="测试目标",
            description="测试描述",
            purpose="测试",
            priority=1,
        )

        target.sources.append({"title": "来源1", "url": "https://example.com/1"})
        target.sources.append({"title": "来源2", "url": "https://example.com/2"})
        target.sources_count = len(target.sources)

        assert len(target.sources) == 2
        assert target.sources_count == 2
        assert target.sources[0]["title"] == "来源1"


# ==================== 单元测试：SearchFramework ====================


class TestSearchFramework:
    """SearchFramework 类单元测试"""

    def test_search_framework_creation(self):
        """测试 SearchFramework 创建"""
        framework = SearchFramework(
            original_query="如何设计一个高性能的搜索引擎？",
            core_question="搜索引擎的核心架构是什么？",
            answer_goal="全面了解搜索引擎的设计原理",
            boundary="不涉及具体代码实现",
        )

        assert framework.original_query == "如何设计一个高性能的搜索引擎？"
        assert framework.core_question == "搜索引擎的核心架构是什么？"
        assert framework.answer_goal == "全面了解搜索引擎的设计原理"
        assert framework.boundary == "不涉及具体代码实现"
        assert framework.targets == []
        assert framework.overall_completeness == 0.0

    def test_search_framework_add_targets(self):
        """测试添加搜索目标"""
        framework = SearchFramework(
            original_query="测试问题",
            core_question="核心问题",
            answer_goal="回答目标",
        )

        target1 = SearchTarget(
            id="T1",
            name="目标1",
            description="目标1的描述",
            purpose="了解目标1",
            priority=1,
        )
        target2 = SearchTarget(
            id="T2",
            name="目标2",
            description="目标2的描述",
            purpose="了解目标2",
            priority=2,
        )

        framework.targets.append(target1)
        framework.targets.append(target2)

        assert len(framework.targets) == 2
        assert framework.targets[0].id == "T1"
        assert framework.targets[1].id == "T2"

    def test_search_framework_get_next_target(self):
        """测试 get_next_target() 方法"""
        framework = SearchFramework(
            original_query="测试问题",
            core_question="核心问题",
            answer_goal="回答目标",
        )

        # 添加多个目标
        target1 = SearchTarget(id="T1", name="目标1", description="目标1", purpose="目标1", priority=2)
        target2 = SearchTarget(id="T2", name="目标2", description="目标2", purpose="目标2", priority=1)
        target3 = SearchTarget(id="T3", name="目标3", description="目标3", purpose="目标3", priority=3)

        framework.targets.extend([target1, target2, target3])

        # 应该返回优先级最高的（priority=1）
        next_target = framework.get_next_target()
        assert next_target is not None
        assert next_target.id == "T2"
        assert next_target.priority == 1

        # 标记为完成后，应该返回下一个
        target2.mark_complete(1.0)
        next_target = framework.get_next_target()
        assert next_target.id == "T1"
        assert next_target.priority == 2

    def test_search_framework_get_target_by_id(self):
        """测试 get_target_by_id() 方法"""
        framework = SearchFramework(
            original_query="测试问题",
            core_question="核心问题",
            answer_goal="回答目标",
        )

        target1 = SearchTarget(id="T1", name="目标1", description="目标1", purpose="目标1", priority=1)
        target2 = SearchTarget(id="T2", name="目标2", description="目标2", purpose="目标2", priority=2)

        framework.targets.extend([target1, target2])

        # 查找存在的目标
        found = framework.get_target_by_id("T2")
        assert found is not None
        assert found.id == "T2"

        # 查找不存在的目标
        not_found = framework.get_target_by_id("T999")
        assert not_found is None

    def test_search_framework_update_completeness(self):
        """测试 update_completeness() 方法"""
        framework = SearchFramework(
            original_query="测试问题",
            core_question="核心问题",
            answer_goal="回答目标",
        )

        target1 = SearchTarget(id="T1", name="目标1", description="目标1", purpose="目标1", priority=1)
        target2 = SearchTarget(id="T2", name="目标2", description="目标2", purpose="目标2", priority=2)
        target3 = SearchTarget(id="T3", name="目标3", description="目标3", purpose="目标3", priority=3)

        framework.targets.extend([target1, target2, target3])

        # 初始完成度应该是 0
        framework.update_completeness()
        assert framework.overall_completeness == 0.0
        assert framework.completed_count == 0

        # 完成一个目标
        target1.completion_score = 1.0
        framework.update_completeness()
        assert framework.overall_completeness == pytest.approx(1.0 / 3, rel=0.01)
        assert framework.completed_count == 1

        # 完成所有目标
        target2.completion_score = 1.0
        target3.completion_score = 1.0
        framework.update_completeness()
        assert framework.overall_completeness == 1.0
        assert framework.completed_count == 3

    def test_search_framework_l1_l5_fields(self):
        """测试 L1-L5 深度分析字段"""
        framework = SearchFramework(
            original_query="测试问题",
            core_question="核心问题",
            answer_goal="回答目标",
        )

        # 设置 L1-L5 字段
        framework.l1_facts = ["事实1", "事实2", "事实3"]
        framework.l2_models = {
            "心理模型": "用户心理分析",
            "社会模型": "社会影响分析",
        }
        framework.l3_tension = "核心矛盾：效率 vs 质量"
        framework.l4_jtbd = "用户想要快速找到准确信息"
        framework.l5_sharpness = {
            "锐度评分": 0.85,
            "关键洞察": "搜索意图识别是关键",
        }

        assert len(framework.l1_facts) == 3
        assert "心理模型" in framework.l2_models
        assert "效率 vs 质量" in framework.l3_tension
        assert "快速找到" in framework.l4_jtbd
        assert framework.l5_sharpness["锐度评分"] == 0.85


# ==================== 集成测试：UcpptSearchEngine ====================


class TestUcpptSearchEngineIntegration:
    """UcpptSearchEngine 集成测试"""

    @pytest.fixture
    def search_engine(self):
        """创建搜索引擎实例"""
        return UcpptSearchEngine()

    def test_build_simple_search_framework(self, search_engine):
        """测试 _build_simple_search_framework() 方法"""
        query = "如何设计一个高性能的搜索引擎？"

        framework = search_engine._build_simple_search_framework(query)

        assert framework is not None
        assert isinstance(framework, SearchFramework)
        assert framework.original_query == query
        assert len(framework.targets) > 0
        assert framework.answer_goal != ""

        # 检查目标的优先级设置
        for target in framework.targets:
            assert target.priority in [1, 2, 3]
            assert target.name != ""
            assert target.purpose != ""

    @pytest.mark.asyncio
    async def test_build_unified_analysis_prompt(self, search_engine):
        """测试 _build_unified_analysis_prompt() 方法

        v7.270 重构后，第一步(需求分析)和第二步(搜索框架)已分离：
        - _build_unified_analysis_prompt: 只负责需求理解+深度分析+解题思路
        - _build_step2_search_framework_prompt: 负责搜索框架生成
        """
        query = "如何设计一个高性能的搜索引擎？"
        context = {
            "user_background": "技术专家",
            "urgency": "高",
        }

        prompt = search_engine._build_unified_analysis_prompt(query, context)

        assert prompt is not None
        assert isinstance(prompt, str)
        assert query in prompt
        # v7.270: 第一步 prompt 应包含分析要素，但不包含搜索框架
        # 检查关键分析要素（L1-L5分析、用户画像、解题思路等）
        assert "用户" in prompt or "分析" in prompt  # 应包含分析相关内容
        assert "problem_solving_approach" in prompt or "解题思路" in prompt or "solution_steps" in prompt

    def test_build_search_framework_from_json(self, search_engine):
        """测试 _build_search_framework_from_json() 方法"""
        query = "如何设计一个高性能的搜索引擎？"

        # 模拟 LLM 返回的 JSON 数据
        json_data = {
            "user_profile": {},
            "analysis": {
                "l1_facts": [
                    "搜索引擎需要处理海量数据",
                    "用户期望毫秒级响应",
                    "相关性排序是核心挑战",
                ],
                "l3_tension": "速度与准确性的平衡",
                "l4_jtbd": "用户想要快速找到最相关的信息",
            },
            "search_framework": {
                "core_question": "搜索引擎的核心架构是什么？",
                "answer_goal": "全面了解搜索引擎的设计原理和实现方法",
                "boundary": "不涉及具体的代码实现细节",
                "targets": [
                    {
                        "id": "T1",
                        "name": "索引结构设计",
                        "description": "了解倒排索引等核心数据结构",
                        "purpose": "了解倒排索引等核心数据结构",
                        "priority": 1,
                        "expected_info": ["倒排索引", "数据结构"],
                    },
                    {
                        "id": "T2",
                        "name": "查询处理流程",
                        "description": "理解查询解析、匹配、排序的完整流程",
                        "purpose": "理解查询解析、匹配、排序的完整流程",
                        "priority": 2,
                        "expected_info": ["查询解析", "排序算法"],
                    },
                    {
                        "id": "T3",
                        "name": "性能优化策略",
                        "description": "掌握缓存、分布式等性能优化方法",
                        "purpose": "掌握缓存、分布式等性能优化方法",
                        "priority": 1,
                        "expected_info": ["缓存", "分布式"],
                    },
                ],
            },
        }

        framework = search_engine._build_search_framework_from_json(query, json_data)

        assert framework is not None
        assert isinstance(framework, SearchFramework)
        assert framework.original_query == query
        assert framework.core_question == "搜索引擎的核心架构是什么？"
        assert framework.boundary == "不涉及具体的代码实现细节"

        # 检查搜索目标
        assert len(framework.targets) == 3
        assert framework.targets[0].id == "T1"
        assert framework.targets[0].priority == 1
        assert framework.targets[1].id == "T2"
        assert framework.targets[2].id == "T3"

        # 检查 L1-L5 字段
        assert len(framework.l1_facts) == 3
        assert framework.l3_tension == "速度与准确性的平衡"
        assert framework.l4_jtbd == "用户想要快速找到最相关的信息"

    def test_build_search_framework_from_json_minimal(self, search_engine):
        """测试 _build_search_framework_from_json() 最小数据"""
        query = "测试问题"

        # 最小化的 JSON 数据
        json_data = {
            "search_framework": {
                "answer_goal": "回答测试问题",
                "targets": [
                    {
                        "id": "T1",
                        "name": "基础信息",
                        "description": "了解基础信息",
                        "purpose": "了解基础信息",
                        "priority": 1,
                    },
                ],
            },
        }

        framework = search_engine._build_search_framework_from_json(query, json_data)

        assert framework is not None
        assert framework.original_query == query
        assert framework.answer_goal == "回答测试问题"
        assert len(framework.targets) == 1

        # 缺失字段应该有默认值
        assert framework.core_question == ""
        assert framework.boundary == ""
        assert framework.l1_facts == []


# ==================== 端到端测试 ====================


class TestSearchDeepE2E:
    """search_deep() 端到端测试"""

    @pytest.fixture
    def search_engine(self):
        """创建搜索引擎实例"""
        engine = UcpptSearchEngine()
        return engine

    @pytest.mark.asyncio
    async def test_search_deep_with_simple_framework(self, search_engine):
        """测试 search_deep() 使用简单框架"""
        query = "什么是机器学习？"

        # Mock LLM 调用，避免实际 API 请求
        with patch.object(search_engine, "_unified_analysis_stream") as mock_analysis:
            # 模拟分析失败，使用简单框架
            async def mock_stream(*args, **kwargs):
                yield {"type": "error", "data": {"message": "分析失败"}}

            mock_analysis.return_value = mock_stream()

            # Mock 搜索调用
            with patch.object(search_engine, "_execute_search_with_quality_filter") as mock_search:
                mock_search.return_value = [
                    {
                        "title": "机器学习入门",
                        "url": "https://example.com/ml",
                        "content": "机器学习是人工智能的一个分支...",
                        "relevance_score": 0.9,
                    }
                ]

                # 执行搜索（限制1轮）
                events = []
                async for event in search_engine.search_deep(query, max_rounds=1):
                    events.append(event)

                # 验证事件流
                event_types = [e.get("type") for e in events]

                # 应该包含关键事件
                assert "phase" in event_types  # 阶段开始
                assert "question_analyzed" in event_types  # 问题分析完成

                # 检查 question_analyzed 事件的数据结构
                analyzed_event = next((e for e in events if e.get("type") == "question_analyzed"), None)
                assert analyzed_event is not None

                data = analyzed_event.get("data", {})
                assert "search_targets" in data  # 新字段名
                assert "total_targets" in data  # 新字段名
                assert isinstance(data["search_targets"], list)

    @pytest.mark.asyncio
    async def test_search_deep_framework_integration(self, search_engine):
        """测试 search_deep() 与 SearchFramework 的集成"""
        query = "如何优化数据库性能？"

        # 创建一个预定义的 SearchFramework
        framework = SearchFramework(
            original_query=query,
            core_question="数据库性能瓶颈在哪里？",
            answer_goal="了解数据库性能优化的方法",
            boundary="不涉及具体数据库产品",
        )

        target1 = SearchTarget(
            id="T1",
            name="索引优化",
            description="了解索引设计和优化方法",
            purpose="了解索引设计和优化方法",
            priority=1,
            search_queries=["数据库索引优化"],
        )

        framework.targets.append(target1)

        # Mock 统一分析流，返回预定义框架
        with patch.object(search_engine, "_unified_analysis_stream") as mock_analysis:

            async def mock_stream(*args, **kwargs):
                yield {
                    "type": "analysis_complete",
                    "framework": framework,
                    "_search_master_line": None,
                }

            mock_analysis.return_value = mock_stream()

            # Mock 搜索
            with patch.object(search_engine, "_execute_search_with_quality_filter") as mock_search:
                mock_search.return_value = [
                    {
                        "title": "数据库索引优化指南",
                        "url": "https://example.com/db-index",
                        "content": "索引是提升查询性能的关键...",
                        "relevance_score": 0.95,
                    }
                ]

                # Mock 统一思考流
                with patch.object(search_engine, "_generate_unified_thinking_stream") as mock_thinking:

                    async def mock_thinking_stream(*args, **kwargs):
                        from intelligent_project_analyzer.services.ucppt_search_engine import UnifiedThinkingResult

                        result = UnifiedThinkingResult(
                            thinking_narrative="让我搜索索引优化的相关信息",
                            search_strategy="搜索数据库索引优化最佳实践",
                            search_query="数据库索引优化 最佳实践",
                            reasoning_content="索引是关键",
                            info_sufficiency=0.7,
                            estimated_rounds_remaining=1,
                        )

                        yield {"type": "unified_thinking_complete", "result": result}

                    mock_thinking.return_value = mock_thinking_stream()

                    # 执行搜索
                    events = []
                    async for event in search_engine.search_deep(query, max_rounds=1):
                        events.append(event)

                    # 验证使用了 SearchFramework
                    analyzed_event = next((e for e in events if e.get("type") == "question_analyzed"), None)
                    assert analyzed_event is not None

                    data = analyzed_event.get("data", {})
                    assert "search_targets" in data
                    assert len(data["search_targets"]) == 1
                    assert data["search_targets"][0]["name"] == "索引优化"


# ==================== 回归测试 ====================


class TestRegressionTests:
    """回归测试：确保旧功能仍然正常"""

    @pytest.fixture
    def search_engine(self):
        """创建搜索引擎实例"""
        return UcpptSearchEngine()

    def test_old_data_structures_still_exist(self, search_engine):
        """测试旧数据结构仍然存在（向后兼容）"""
        # 检查旧类是否仍然可用
        from intelligent_project_analyzer.services.ucppt_search_engine import (
            AnswerFramework,
            KeyAspect,
            SearchMasterLine,
            SearchTask,
        )

        # 应该能够创建旧对象
        aspect = KeyAspect(
            id="A1",
            aspect_name="测试信息面",
            answer_goal="测试目标",
            importance=5,
        )
        assert aspect.id == "A1"

        framework = AnswerFramework(
            original_query="测试问题",
            answer_goal="测试目标",
            created_at=0.0,
        )
        assert framework.original_query == "测试问题"

    def test_simple_framework_fallback(self, search_engine):
        """测试简单框架降级机制"""
        query = "测试问题"

        # 调用旧的 _build_simple_framework 方法（如果存在）
        if hasattr(search_engine, "_build_simple_framework"):
            old_framework = search_engine._build_simple_framework(query)
            assert old_framework is not None

        # 调用新的 _build_simple_search_framework 方法
        new_framework = search_engine._build_simple_search_framework(query)
        assert new_framework is not None
        assert isinstance(new_framework, SearchFramework)


# ==================== 性能测试 ====================


class TestPerformance:
    """性能测试"""

    def test_search_target_creation_performance(self):
        """测试 SearchTarget 创建性能"""
        import time

        start = time.time()
        targets = []
        for i in range(1000):
            target = SearchTarget(
                id=f"T{i}",
                name=f"目标{i}",
                description=f"目标{i}的描述",
                purpose=f"了解目标{i}",
                priority=i % 3 + 1,
            )
            targets.append(target)

        elapsed = time.time() - start

        assert len(targets) == 1000
        assert elapsed < 0.1  # 应该在 100ms 内完成

    def test_search_framework_update_completeness_performance(self):
        """测试 update_completeness() 性能"""
        import time

        framework = SearchFramework(
            original_query="测试",
            core_question="测试",
            answer_goal="测试",
        )

        # 添加 100 个目标
        for i in range(100):
            target = SearchTarget(
                id=f"T{i}",
                name=f"目标{i}",
                description=f"目标{i}的描述",
                purpose=f"目标{i}",
                priority=1,
            )
            target.completion_score = i / 100.0
            framework.targets.append(target)

        start = time.time()
        for _ in range(100):
            framework.update_completeness()

        elapsed = time.time() - start

        assert elapsed < 0.1  # 100 次更新应该在 100ms 内完成


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
