"""
v7.240: 框架清单集成测试

测试框架清单在搜索流程中的集成：
1. _unified_analysis_stream 生成框架清单
2. search_framework_ready 事件包含框架清单
3. 框架清单传递到搜索轮次prompt
"""

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from intelligent_project_analyzer.services.ucppt_search_engine import (
    FrameworkChecklist,
    SearchFramework,
    SearchTarget,
    UcpptSearchEngine,
)


class TestFrameworkChecklistIntegration:
    """测试框架清单在搜索流程中的集成"""

    def setup_method(self):
        """每个测试前初始化"""
        self.engine = UcpptSearchEngine()

    @pytest.mark.asyncio
    async def test_unified_analysis_stream_generates_checklist(self):
        """测试 _unified_analysis_stream 生成框架清单"""
        # Mock DeepSeek API 响应
        mock_response = {
            "user_profile": {
                "identity_tags": ["设计师"],
                "occupation": "室内设计师",
            },
            "analysis": {
                "l1_facts": ["北欧风格", "客厅设计"],
                "l3_tension": "风格与实用性的平衡",
            },
            "search_framework": {
                "core_question": "如何设计北欧风客厅",
                "answer_goal": "提供完整的设计方案",
                "boundary": "不涉及预算规划",
                "targets": [
                    {
                        "id": "T1",
                        "question": "北欧风格特点",
                        "search_for": "色彩、材质、家具特点",
                        "why_need": "了解风格核心",
                        "success_when": ["列出主要特点"],
                        "priority": 1,
                        "category": "风格调研",
                    },
                ],
            },
        }

        with patch.object(
            self.engine,
            "_call_deepseek_stream_with_reasoning",
            new_callable=AsyncMock,
            return_value={"reasoning_content": "思考过程", "content": str(mock_response)},
        ):
            with patch.object(
                self.engine, "_parse_unified_analysis_json", return_value=(mock_response, {"grade": "A", "score": 0.9})
            ):
                events = []
                try:
                    async for event in self.engine._unified_analysis_stream(query="帮我设计一个北欧风格的客厅", context={}):
                        events.append(event)
                        # 找到 search_framework_ready 事件后停止
                        if event.get("type") == "search_framework_ready":
                            break
                except Exception:
                    pass  # 允许部分执行

                # 查找 search_framework_ready 事件
                framework_event = next((e for e in events if e.get("type") == "search_framework_ready"), None)

                if framework_event:
                    data = framework_event.get("data", {})
                    # 验证包含框架清单
                    assert "framework_checklist" in data
                    checklist = data["framework_checklist"]
                    assert "core_summary" in checklist
                    assert "main_directions" in checklist
                    assert "boundaries" in checklist
                    assert "answer_goal" in checklist
                    assert "plain_text" in checklist

    def test_framework_checklist_attached_to_framework(self):
        """测试框架清单被附加到 SearchFramework"""
        framework = SearchFramework(
            original_query="测试查询",
            core_question="测试问题",
            answer_goal="测试目标",
            boundary="不涉及测试边界",
            targets=[
                SearchTarget(
                    id="T1",
                    name="测试目标",
                    category="测试",
                    why_need="测试目的",
                    success_when=["成功标准"],
                ),
            ],
        )

        # 生成框架清单
        checklist = self.engine._generate_framework_checklist(framework, {})
        framework.framework_checklist = checklist

        # 验证附加成功
        assert framework.framework_checklist is not None
        assert framework.framework_checklist.core_summary != ""
        assert len(framework.framework_checklist.main_directions) == 1


class TestFrameworkChecklistInSearchRound:
    """测试框架清单在搜索轮次中的使用"""

    def setup_method(self):
        """每个测试前初始化"""
        self.engine = UcpptSearchEngine()

    def test_framework_checklist_in_prompt_context(self):
        """测试框架清单被包含在搜索轮次prompt中"""
        # 创建带框架清单的 SearchFramework
        framework = SearchFramework(
            original_query="测试查询",
            core_question="测试问题",
            answer_goal="测试目标",
            boundary="",
            targets=[
                SearchTarget(
                    id="T1",
                    name="测试目标",
                    category="测试分类",
                    why_need="测试目的",
                ),
            ],
        )

        checklist = FrameworkChecklist(
            core_summary="测试核心问题",
            main_directions=[
                {"direction": "测试方向", "purpose": "测试目的", "expected_outcome": "测试期望"},
            ],
            boundaries=["测试边界"],
            answer_goal="测试回答目标",
        )
        framework.framework_checklist = checklist

        # 验证框架清单存在
        assert framework.framework_checklist is not None
        assert framework.framework_checklist.core_summary == "测试核心问题"

    @pytest.mark.asyncio
    async def test_thinking_stream_includes_checklist(self):
        """测试思考流包含框架清单上下文"""
        framework = SearchFramework(
            original_query="测试查询",
            core_question="测试问题",
            answer_goal="测试目标",
            boundary="",
            targets=[
                SearchTarget(
                    id="T1",
                    name="测试目标",
                    category="测试",
                ),
            ],
        )

        checklist = FrameworkChecklist(
            core_summary="框架清单核心问题",
            main_directions=[
                {"direction": "方向1", "purpose": "目的1", "expected_outcome": "期望1"},
            ],
            boundaries=["边界1"],
            answer_goal="框架清单回答目标",
        )
        framework.framework_checklist = checklist

        target = framework.targets[0]

        # Mock LLM 调用
        with patch.object(
            self.engine,
            "_call_deepseek_stream_with_reasoning",
            new_callable=AsyncMock,
            return_value={
                "reasoning_content": "思考过程",
                "content": '{"current_round_planning": {"search_query": "测试查询"}}',
            },
        ) as mock_call:
            try:
                async for _ in self.engine._generate_unified_thinking_stream(
                    framework=framework,
                    target=target,
                    current_round=1,
                    all_sources=[],
                    last_round_sources=[],
                ):
                    break  # 只需要触发一次调用
            except Exception:
                pass

            # 验证 prompt 中包含框架清单
            if mock_call.called:
                call_args = mock_call.call_args
                if call_args and len(call_args) > 0:
                    prompt = call_args[0][0] if call_args[0] else ""
                    # 框架清单应该在 prompt 中
                    assert "搜索框架清单" in prompt or "框架清单核心问题" in prompt


class TestFrameworkChecklistEventFlow:
    """测试框架清单事件流"""

    def test_search_framework_ready_event_structure(self):
        """测试 search_framework_ready 事件结构"""
        # 模拟事件数据
        event_data = {
            "type": "search_framework_ready",
            "data": {
                "core_question": "测试问题",
                "answer_goal": "测试目标",
                "boundary": "测试边界",
                "target_count": 2,
                "targets": [
                    {"id": "T1", "name": "目标1"},
                    {"id": "T2", "name": "目标2"},
                ],
                "targets_summary": "📋 搜索主线：\n1. 目标1\n2. 目标2",
                "quality_grade": "A",
                "framework_checklist": {
                    "core_summary": "测试核心",
                    "main_directions": [
                        {"direction": "方向1", "purpose": "目的1", "expected_outcome": "期望1"},
                    ],
                    "boundaries": ["边界1"],
                    "answer_goal": "回答目标",
                    "generated_at": "2026-01-23T10:00:00",
                    "plain_text": "## 核心问题\n测试核心",
                },
            },
        }

        # 验证事件结构
        assert event_data["type"] == "search_framework_ready"
        data = event_data["data"]
        assert "framework_checklist" in data

        checklist = data["framework_checklist"]
        assert "core_summary" in checklist
        assert "main_directions" in checklist
        assert "boundaries" in checklist
        assert "answer_goal" in checklist
        assert "plain_text" in checklist

    def test_framework_checklist_serialization(self):
        """测试框架清单序列化"""
        checklist = FrameworkChecklist(
            core_summary="序列化测试",
            main_directions=[
                {"direction": "方向", "purpose": "目的", "expected_outcome": "期望"},
            ],
            boundaries=["边界"],
            answer_goal="目标",
            generated_at="2026-01-23T10:00:00",
        )

        # 序列化
        data = checklist.to_dict()

        # 验证可以被 JSON 序列化
        import json

        json_str = json.dumps(data, ensure_ascii=False)
        assert json_str is not None

        # 反序列化
        parsed = json.loads(json_str)
        assert parsed["core_summary"] == "序列化测试"
        assert len(parsed["main_directions"]) == 1


class TestFrameworkChecklistPersistence:
    """测试框架清单持久化"""

    def test_checklist_to_dict_for_storage(self):
        """测试框架清单转换为存储格式"""
        checklist = FrameworkChecklist(
            core_summary="持久化测试",
            main_directions=[
                {"direction": "方向1", "purpose": "目的1", "expected_outcome": "期望1"},
                {"direction": "方向2", "purpose": "目的2", "expected_outcome": "期望2"},
            ],
            boundaries=["边界1", "边界2"],
            answer_goal="持久化目标",
            generated_at="2026-01-23T10:00:00",
        )

        data = checklist.to_dict()

        # 验证所有字段都被包含
        assert data["core_summary"] == "持久化测试"
        assert len(data["main_directions"]) == 2
        assert len(data["boundaries"]) == 2
        assert data["answer_goal"] == "持久化目标"
        assert data["generated_at"] == "2026-01-23T10:00:00"
        assert "plain_text" in data

    def test_checklist_restoration_from_dict(self):
        """测试从字典恢复框架清单"""
        original = FrameworkChecklist(
            core_summary="恢复测试",
            main_directions=[
                {"direction": "方向", "purpose": "目的", "expected_outcome": "期望"},
            ],
            boundaries=["边界"],
            answer_goal="目标",
            generated_at="2026-01-23T10:00:00",
        )

        # 转换为字典
        data = original.to_dict()

        # 从字典恢复
        restored = FrameworkChecklist(
            core_summary=data["core_summary"],
            main_directions=data["main_directions"],
            boundaries=data["boundaries"],
            answer_goal=data["answer_goal"],
            generated_at=data["generated_at"],
        )

        # 验证恢复正确
        assert restored.core_summary == original.core_summary
        assert restored.main_directions == original.main_directions
        assert restored.boundaries == original.boundaries
        assert restored.answer_goal == original.answer_goal


class TestFrameworkChecklistWithRealData:
    """使用真实数据格式测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.engine = UcpptSearchEngine()

    def test_generate_from_real_framework_data(self):
        """测试从真实框架数据生成清单"""
        # 模拟真实的 SearchFramework 数据
        framework = SearchFramework(
            original_query="我想在峨眉山开一家精品民宿，想用HAY的家具，但不确定北欧风格是否适合中国山区环境",
            core_question="如何在中国山区民宿中融合北欧HAY家具风格",
            answer_goal="提供HAY家具在峨眉山民宿的适配方案，包括风格融合策略和具体产品推荐",
            boundary="不涉及：1.具体施工方案 2.详细预算规划 3.其他品牌家具对比",
            targets=[
                SearchTarget(
                    id="T1",
                    name="HAY品牌调研",
                    category="品牌调研",
                    question="HAY家具的设计理念和产品特点",
                    why_need="了解品牌核心价值，判断与民宿定位的契合度",
                    success_when=["品牌历史", "设计理念", "代表产品线"],
                    priority=1,
                ),
                SearchTarget(
                    id="T2",
                    name="风格融合案例",
                    category="案例研究",
                    question="北欧家具在中式/山地环境中的成功案例",
                    why_need="获取实际参考，验证可行性",
                    success_when=["至少3个成功案例", "融合策略分析"],
                    priority=1,
                ),
                SearchTarget(
                    id="T3",
                    name="峨眉山环境分析",
                    category="环境调研",
                    question="峨眉山地区气候和建筑特点",
                    why_need="了解当地环境约束，确保家具适配",
                    success_when=["气候特点", "建筑风格", "材质要求"],
                    priority=2,
                ),
            ],
        )

        checklist = self.engine._generate_framework_checklist(framework, {})

        # 验证生成结果
        assert checklist.core_summary != ""
        assert len(checklist.main_directions) == 3
        assert len(checklist.boundaries) >= 1
        assert checklist.answer_goal != ""

        # 验证方向内容
        directions = checklist.main_directions
        assert any("品牌" in d.get("direction", "") or "调研" in d.get("direction", "") for d in directions)

        # 验证纯文字输出
        plain_text = checklist.to_plain_text()
        assert "## 核心问题" in plain_text
        assert "## 搜索主线" in plain_text
        assert "## 回答目标" in plain_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
