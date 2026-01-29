"""
UCPPT v7.270 回归测试

测试范围：
1. 向后兼容性验证
2. 旧功能未受影响
3. 数据格式兼容性
4. API接口兼容性
"""

import asyncio
from unittest.mock import Mock, patch

import pytest

from intelligent_project_analyzer.services.ucppt_search_engine import SearchFramework, SearchTarget, UcpptSearchEngine


class TestBackwardCompatibility:
    """测试向后兼容性"""

    @pytest.fixture
    def engine(self):
        return UcpptSearchEngine()

    @pytest.mark.asyncio
    async def test_old_search_framework_format_still_works(self, engine):
        """测试旧的搜索框架格式仍然可用"""
        query = "测试问题"

        # 模拟旧格式的 LLM 响应
        old_format_response = {
            "user_profile": {
                "location": "测试地点",
                "occupation": "测试职业",
                "identity_tags": ["标签1"],
                "explicit_need": "明确需求",
                "implicit_needs": ["隐性需求1"],
                "motivation_types": {
                    "primary": "aesthetic",
                    "primary_reason": "测试原因",
                    "secondary": [],
                    "secondary_reason": "",
                },
            },
            "analysis": {
                "l1_facts": {
                    "brand_entities": [],
                    "location_entities": [],
                    "competitor_entities": [],
                    "style_entities": [],
                    "person_entities": [],
                },
                "l2_models": {"selected_perspectives": ["心理学", "美学"], "psychological": "心理学分析", "aesthetic": "美学分析"},
                "l3_tension": {"formula": "A vs B", "description": "张力描述", "resolution_strategy": "解决策略"},
                "l4_jtbd": "当...时，我想要...，以便...",
                "l5_sharpness": {"score": 0.8, "specificity": "是", "actionability": "是", "depth": "是"},
            },
            "search_framework": {
                "core_question": "核心问题",
                "answer_goal": "回答目标",
                "boundary": "不搜索价格",
                "targets": [
                    {
                        "id": "T1",
                        "name": "目标1",
                        "description": "描述1",
                        "purpose": "目的1",
                        "priority": 1,
                        "category": "品牌调研",
                        "preset_keywords": ["关键词1", "关键词2", "关键词3"],
                        "quality_criteria": ["标准1"],
                        "expected_info": ["信息1"],
                    }
                ],
            },
        }

        with patch.object(engine, "_safe_parse_json") as mock_parse:
            mock_parse.return_value = old_format_response

            events = []
            async for event in engine._unified_analysis_stream(query, context=None):
                events.append(event)

            event_types = [e.get("type") for e in events]

            # 应该能处理旧格式
            assert "search_framework_ready" in event_types or "analysis_complete" in event_types

            # 验证搜索框架被正确构建
            framework_event = next((e for e in events if e.get("type") == "search_framework_ready"), None)
            if framework_event:
                framework = framework_event.get("_internal_framework")
                assert framework is not None
                assert len(framework.targets) == 1
                assert framework.targets[0].id == "T1"

    @pytest.mark.asyncio
    async def test_mixed_format_handling(self, engine):
        """测试混合格式处理（同时包含旧字段和新字段）"""
        query = "测试问题"

        # 模拟包含新旧字段的响应
        mixed_format_response = {
            "user_profile": {},
            "analysis": {"l1_facts": {}, "l2_models": {}, "l3_tension": {}, "l4_jtbd": "", "l5_sharpness": {}},
            "problem_solving_approach": {
                "task_type": "exploration",
                "task_type_description": "探索任务",
                "complexity_level": "moderate",
                "required_expertise": ["知识1"],
                "solution_steps": [{"step_id": "S1", "action": "行动1", "purpose": "目的1", "expected_output": "产出1"}],
                "breakthrough_points": [],
                "expected_deliverable": {},
                "original_requirement": query,
                "refined_requirement": query,
                "confidence_score": 0.7,
                "alternative_approaches": [],
            },
            "step2_context": {"core_question": "核心问题", "answer_goal": "回答目标"},
            # 同时包含旧的 search_framework（不应该出现，但测试兼容性）
            "search_framework": {"core_question": "旧核心问题", "answer_goal": "旧回答目标", "boundary": "", "targets": []},
        }

        with patch.object(engine, "_safe_parse_json") as mock_parse:
            mock_parse.return_value = mixed_format_response

            events = []
            async for event in engine._unified_analysis_stream(query, context=None):
                events.append(event)

            event_types = [e.get("type") for e in events]

            # 应该优先处理新格式
            assert "problem_solving_approach_ready" in event_types
            assert "step1_complete" in event_types


class TestExistingFeaturesUnaffected:
    """测试现有功能未受影响"""

    @pytest.fixture
    def engine(self):
        return UcpptSearchEngine()

    def test_search_target_creation(self, engine):
        """测试 SearchTarget 创建（旧方式）"""
        # 使用旧字段创建
        target = SearchTarget(
            id="T1",
            name="测试目标",
            description="测试描述",
            purpose="测试目的",
            priority=1,
            category="品牌调研",
            quality_criteria=["标准1", "标准2"],
        )

        # 验证旧字段仍然可用
        assert target.name == "测试目标"
        assert target.description == "测试描述"
        assert target.purpose == "测试目的"
        assert target.quality_criteria == ["标准1", "标准2"]

        # 验证新字段被自动填充
        assert target.question == "测试目标"
        assert target.search_for == "测试描述"
        assert target.why_need == "测试目的"
        assert target.success_when == ["标准1", "标准2"]

    def test_search_target_to_dict(self, engine):
        """测试 SearchTarget.to_dict() 向后兼容"""
        target = SearchTarget(id="T1", name="测试目标", description="测试描述", purpose="测试目的", priority=1, category="品牌调研")

        data = target.to_dict()

        # 验证旧字段仍然存在
        assert "name" in data
        assert "description" in data
        assert "purpose" in data
        assert "quality_criteria" in data

        # 验证新字段也存在
        assert "question" in data
        assert "search_for" in data
        assert "why_need" in data
        assert "success_when" in data

    def test_search_framework_creation(self, engine):
        """测试 SearchFramework 创建"""
        framework = SearchFramework(
            original_query="测试问题", core_question="核心问题", answer_goal="回答目标", boundary="边界", targets=[]
        )

        # 验证基本字段
        assert framework.original_query == "测试问题"
        assert framework.core_question == "核心问题"
        assert framework.answer_goal == "回答目标"
        assert framework.boundary == "边界"
        assert isinstance(framework.targets, list)

    def test_search_framework_get_next_target(self, engine):
        """测试 SearchFramework.get_next_target() 方法"""
        target1 = SearchTarget(id="T1", name="目标1", priority=1)
        target2 = SearchTarget(id="T2", name="目标2", priority=2)
        target1.mark_complete()

        framework = SearchFramework(original_query="测试", targets=[target1, target2])

        next_target = framework.get_next_target()
        assert next_target is not None
        assert next_target.id == "T2"


class TestDataFormatCompatibility:
    """测试数据格式兼容性"""

    @pytest.fixture
    def engine(self):
        return UcpptSearchEngine()

    def test_old_json_format_parsing(self, engine):
        """测试旧 JSON 格式解析"""
        old_json = """
        {
            "user_profile": {
                "location": "北京",
                "occupation": "设计师"
            },
            "analysis": {
                "l1_facts": {},
                "l2_models": {},
                "l3_tension": "",
                "l4_jtbd": "",
                "l5_sharpness": {}
            },
            "search_framework": {
                "core_question": "如何设计？",
                "answer_goal": "提供方案",
                "boundary": "",
                "targets": [
                    {
                        "id": "T1",
                        "name": "调研品牌",
                        "description": "了解品牌特点",
                        "purpose": "建立认知",
                        "priority": 1,
                        "category": "品牌调研",
                        "preset_keywords": ["品牌", "设计", "理念"]
                    }
                ]
            }
        }
        """

        import json

        data = json.loads(old_json)

        # 应该能正常解析
        assert "user_profile" in data
        assert "analysis" in data
        assert "search_framework" in data

        # 构建 SearchFramework
        framework = engine._build_search_framework_from_json("测试", data)
        assert framework is not None
        assert len(framework.targets) == 1
        assert framework.targets[0].preset_keywords == ["品牌", "设计", "理念"]

    def test_new_json_format_parsing(self, engine):
        """测试新 JSON 格式解析"""
        new_json = """
        {
            "user_profile": {},
            "analysis": {
                "l1_facts": {},
                "l2_models": {},
                "l3_tension": "",
                "l4_jtbd": "",
                "l5_sharpness": {}
            },
            "problem_solving_approach": {
                "task_type": "design",
                "task_type_description": "设计任务",
                "complexity_level": "complex",
                "required_expertise": ["室内设计"],
                "solution_steps": [
                    {
                        "step_id": "S1",
                        "action": "分析需求",
                        "purpose": "理解问题",
                        "expected_output": "需求清单"
                    }
                ],
                "breakthrough_points": [],
                "expected_deliverable": {
                    "format": "report",
                    "sections": ["概述"],
                    "key_elements": ["图表"],
                    "quality_criteria": ["准确性"]
                },
                "original_requirement": "测试",
                "refined_requirement": "测试",
                "confidence_score": 0.8,
                "alternative_approaches": []
            },
            "step2_context": {
                "core_question": "核心问题",
                "answer_goal": "回答目标"
            }
        }
        """

        import json

        data = json.loads(new_json)

        # 应该能正常解析
        assert "problem_solving_approach" in data
        assert "step2_context" in data

        # 构建 ProblemSolvingApproach
        from intelligent_project_analyzer.services.ucppt_search_engine import ProblemSolvingApproach

        approach = ProblemSolvingApproach.from_dict(data["problem_solving_approach"])
        assert approach.task_type == "design"
        assert len(approach.solution_steps) == 1


class TestAPIInterfaceCompatibility:
    """测试 API 接口兼容性"""

    @pytest.fixture
    def engine(self):
        return UcpptSearchEngine()

    @pytest.mark.asyncio
    async def test_unified_analysis_stream_signature(self, engine):
        """测试 _unified_analysis_stream 方法签名未变"""
        query = "测试"
        context = {"key": "value"}

        # 应该能正常调用
        events = []
        async for event in engine._unified_analysis_stream(query, context):
            events.append(event)
            break  # 只测试能否调用

        assert len(events) > 0

    def test_build_search_framework_from_json_signature(self, engine):
        """测试 _build_search_framework_from_json 方法签名未变"""
        query = "测试"
        data = {
            "user_profile": {},
            "analysis": {},
            "search_framework": {"core_question": "测试", "answer_goal": "测试", "boundary": "", "targets": []},
        }

        # 应该能正常调用
        framework = engine._build_search_framework_from_json(query, data)
        assert framework is not None

    def test_search_target_methods_unchanged(self, engine):
        """测试 SearchTarget 方法未变"""
        target = SearchTarget(id="T1", name="测试", priority=1)

        # 验证方法仍然存在且可用
        assert hasattr(target, "is_complete")
        assert hasattr(target, "mark_searching")
        assert hasattr(target, "mark_complete")
        assert hasattr(target, "to_dict")

        # 测试方法功能
        assert not target.is_complete()
        target.mark_complete()
        assert target.is_complete()


class TestEventStreamCompatibility:
    """测试事件流兼容性"""

    @pytest.fixture
    def engine(self):
        return UcpptSearchEngine()

    @pytest.mark.asyncio
    async def test_old_events_still_emitted(self, engine):
        """测试旧事件仍然被发送"""
        query = "测试"
        events = []

        async for event in engine._unified_analysis_stream(query, context=None):
            events.append(event)

        event_types = [e.get("type") for e in events]

        # 验证旧事件仍然存在（如果适用）
        # 注意：某些旧事件可能已被新事件替代
        # 这里主要验证关键事件
        assert "unified_dialogue_complete" in event_types or "analysis_complete" in event_types

    @pytest.mark.asyncio
    async def test_new_events_are_optional(self, engine):
        """测试新事件是可选的"""
        query = "测试"

        # 模拟旧流程（不生成新事件）
        old_response = {
            "user_profile": {},
            "analysis": {"l1_facts": {}, "l2_models": {}, "l3_tension": "", "l4_jtbd": "", "l5_sharpness": {}},
            "search_framework": {"core_question": "测试", "answer_goal": "测试", "boundary": "", "targets": []},
        }

        with patch.object(engine, "_safe_parse_json") as mock_parse:
            mock_parse.return_value = old_response

            events = []
            async for event in engine._unified_analysis_stream(query, context=None):
                events.append(event)

            event_types = [e.get("type") for e in events]

            # 即使没有新事件，流程也应该正常完成
            assert "analysis_complete" in event_types or "search_framework_ready" in event_types


class TestRegressionScenarios:
    """回归场景测试"""

    @pytest.fixture
    def engine(self):
        return UcpptSearchEngine()

    @pytest.mark.asyncio
    async def test_simple_query_still_works(self, engine):
        """测试简单查询仍然可用"""
        query = "什么是北欧风格？"

        events = []
        async for event in engine._unified_analysis_stream(query, context=None):
            events.append(event)

        # 应该能正常处理
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_complex_query_still_works(self, engine):
        """测试复杂查询仍然可用"""
        query = """
        我想为一个位于上海的高端咖啡馆设计室内空间。
        咖啡馆面积约150平米，目标客户是25-40岁的都市白领。
        希望营造温馨、专业、有设计感的氛围。
        预算在50-80万之间。
        """

        events = []
        async for event in engine._unified_analysis_stream(query, context=None):
            events.append(event)

        # 应该能正常处理
        assert len(events) > 0

    def test_default_values_unchanged(self, engine):
        """测试默认值未变"""
        # 验证常量
        from intelligent_project_analyzer.services.ucppt_search_engine import (
            COMPLETENESS_THRESHOLD,
            MAX_SEARCH_ROUNDS,
            MIN_SEARCH_ROUNDS,
        )

        assert MAX_SEARCH_ROUNDS == 30
        assert MIN_SEARCH_ROUNDS == 4
        assert COMPLETENESS_THRESHOLD == 0.88


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
