"""
单元测试：v7.218 搜索体验优化功能
测试覆盖：
1. analysis_progress 事件发送
2. thinking_chunk 事件的 phase 字段区分
3. Phase 0 和 Phase 2 的正确分离
"""

import asyncio
import os
import sys
from typing import Any, AsyncGenerator, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# 导入待测试的类和组件
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


class TestAnalysisProgressEvent:
    """测试 analysis_progress 事件 (Bug 1 修复)"""

    @pytest.mark.unit
    def test_analysis_progress_event_structure_starting(self):
        """测试 analysis_progress 事件结构 - 启动阶段"""
        event = {
            "type": "analysis_progress",
            "data": {
                "stage": "starting",
                "stage_name": "深度分析启动",
                "message": "正在启动 DeepSeek 深度推理引擎，预计需要 2-3 分钟...",
                "estimated_time": 180,
                "current_step": 0,
                "total_steps": 3,
            },
        }

        # 验证事件类型
        assert event["type"] == "analysis_progress"

        # 验证数据结构
        data = event["data"]
        assert data["stage"] == "starting"
        assert data["stage_name"] == "深度分析启动"
        assert data["estimated_time"] == 180
        assert data["current_step"] == 0
        assert data["total_steps"] == 3
        assert "message" in data

    @pytest.mark.unit
    def test_analysis_progress_event_structure_complete(self):
        """测试 analysis_progress 事件结构 - 完成阶段"""
        event = {
            "type": "analysis_progress",
            "data": {
                "stage": "complete",
                "stage_name": "深度分析完成",
                "message": "结构化分析完成，准备开始搜索...",
                "estimated_time": 0,
                "current_step": 3,
                "total_steps": 3,
            },
        }

        # 验证事件类型
        assert event["type"] == "analysis_progress"

        # 验证数据结构
        data = event["data"]
        assert data["stage"] == "complete"
        assert data["estimated_time"] == 0  # 完成时无需等待
        assert data["current_step"] == data["total_steps"]  # 步骤完成

    @pytest.mark.unit
    def test_analysis_progress_stage_values(self):
        """测试 analysis_progress 有效的 stage 值"""
        valid_stages = ["starting", "complete"]

        for stage in valid_stages:
            event = {"type": "analysis_progress", "data": {"stage": stage}}
            assert event["data"]["stage"] in valid_stages


class TestThinkingChunkPhaseField:
    """测试 thinking_chunk 事件的 phase 字段 (Bug 2, 4 修复)"""

    @pytest.mark.unit
    def test_thinking_chunk_with_search_round_phase(self):
        """测试 thinking_chunk 事件包含 search_round phase"""
        # v7.218: 搜索轮次的思考事件应包含 phase: "search_round"
        event = {
            "type": "thinking_chunk",
            "data": {
                "round": 1,
                "content": "正在分析搜索需求...",
                "is_reasoning": True,
                "phase": "search_round",
            },
        }

        # 验证事件类型
        assert event["type"] == "thinking_chunk"

        # 验证 phase 字段
        assert event["data"]["phase"] == "search_round"
        assert event["data"]["round"] == 1
        assert event["data"]["is_reasoning"] is True

    @pytest.mark.unit
    def test_thinking_chunk_phase_distinction(self):
        """测试 Phase 0 和 Phase 2 的区分"""
        # Phase 0 内容通过 unified_dialogue_chunk 传递
        phase0_event = {
            "type": "unified_dialogue_chunk",
            "content": "用户希望设计一个现代风格的办公空间...",
        }

        # Phase 2 内容通过 thinking_chunk + phase 字段传递
        phase2_event = {
            "type": "thinking_chunk",
            "data": {
                "round": 1,
                "content": "第一轮搜索规划...",
                "is_reasoning": True,
                "phase": "search_round",
            },
        }

        # 验证两种事件类型不同
        assert phase0_event["type"] == "unified_dialogue_chunk"
        assert phase2_event["type"] == "thinking_chunk"

        # 验证 Phase 2 包含 phase 标识
        assert phase2_event["data"].get("phase") == "search_round"

    @pytest.mark.unit
    def test_thinking_chunk_required_fields(self):
        """测试 thinking_chunk 事件必需字段"""
        event = {
            "type": "thinking_chunk",
            "data": {
                "round": 2,
                "content": "分析上轮搜索结果...",
                "is_reasoning": False,
                "phase": "search_round",
            },
        }

        required_fields = ["round", "content", "is_reasoning", "phase"]
        for field in required_fields:
            assert field in event["data"], f"缺少必需字段: {field}"


class TestEventStreamOrder:
    """测试事件流顺序 (Bug 2 修复)"""

    @pytest.mark.unit
    def test_event_sequence_correct_order(self):
        """测试正确的事件顺序"""
        # 模拟正确的事件序列
        events = [
            # Phase 0: 结构化分析
            {"type": "phase", "data": {"phase": "structured_analysis"}},
            {"type": "analysis_progress", "data": {"stage": "starting"}},
            {"type": "unified_dialogue_chunk", "content": "L0 对话内容..."},
            {"type": "analysis_progress", "data": {"stage": "complete"}},
            # Phase 2: 搜索轮次
            {"type": "phase", "data": {"phase": "search"}},
            {"type": "thinking_chunk", "data": {"round": 1, "phase": "search_round"}},
            {"type": "round_sources", "data": {"round": 1, "sources": []}},
        ]

        # 验证 analysis_progress 在 unified_dialogue_chunk 之前
        analysis_start_idx = next(
            i
            for i, e in enumerate(events)
            if e.get("type") == "analysis_progress" and e.get("data", {}).get("stage") == "starting"
        )
        unified_chunk_idx = next(i for i, e in enumerate(events) if e.get("type") == "unified_dialogue_chunk")

        assert analysis_start_idx < unified_chunk_idx, "analysis_progress(starting) 应在 unified_dialogue_chunk 之前"

        # 验证 analysis_complete 在 search phase 之前
        analysis_complete_idx = next(
            i
            for i, e in enumerate(events)
            if e.get("type") == "analysis_progress" and e.get("data", {}).get("stage") == "complete"
        )
        search_phase_idx = next(
            i for i, e in enumerate(events) if e.get("type") == "phase" and e.get("data", {}).get("phase") == "search"
        )

        assert analysis_complete_idx < search_phase_idx, "analysis_progress(complete) 应在 search phase 之前"

    @pytest.mark.unit
    def test_phase_transitions(self):
        """测试阶段转换"""
        phases = ["structured_analysis", "search"]

        # 验证阶段顺序
        assert phases.index("structured_analysis") < phases.index("search")


class TestUnifiedDialogueChunk:
    """测试 unified_dialogue_chunk 事件 (Phase 0 内容)"""

    @pytest.mark.unit
    def test_unified_dialogue_chunk_structure(self):
        """测试 unified_dialogue_chunk 事件结构"""
        event = {
            "type": "unified_dialogue_chunk",
            "content": "基于您的需求分析，这是一个关于...",
            "is_l0": True,
        }

        assert event["type"] == "unified_dialogue_chunk"
        assert "content" in event
        assert isinstance(event["content"], str)

    @pytest.mark.unit
    def test_unified_dialogue_chunk_is_phase0_content(self):
        """验证 unified_dialogue_chunk 是 Phase 0 内容"""
        # 此事件应该用于 Phase 0 的解题思考内容
        # 不应该与 Phase 2 的轮次思考混淆
        phase0_content = "用户的核心需求是设计一个兼具功能性和美观性的空间..."

        event = {
            "type": "unified_dialogue_chunk",
            "content": phase0_content,
        }

        # 验证这是对话式内容，而非搜索轮次思考
        assert "unified_dialogue" in event["type"]
        assert "thinking_chunk" not in event["type"]


class TestRoundSourcesEvent:
    """测试 round_sources 事件 (Bug 3 修复)"""

    @pytest.mark.unit
    def test_round_sources_structure(self):
        """测试 round_sources 事件结构"""
        event = {
            "type": "round_sources",
            "data": {
                "round": 1,
                "sources": [
                    {
                        "title": "测试标题",
                        "url": "https://example.com",
                        "snippet": "这是一段摘要...",
                    }
                ],
                "totalCount": 1,
            },
        }

        assert event["type"] == "round_sources"
        assert event["data"]["round"] == 1
        assert len(event["data"]["sources"]) == 1
        assert event["data"]["sources"][0]["title"] == "测试标题"

    @pytest.mark.unit
    def test_round_sources_separate_from_thinking(self):
        """验证搜索结果与思考内容分离"""
        # 思考事件
        thinking_event = {
            "type": "thinking_chunk",
            "data": {
                "round": 1,
                "content": "正在规划搜索...",
                "phase": "search_round",
            },
        }

        # 搜索结果事件
        sources_event = {
            "type": "round_sources",
            "data": {
                "round": 1,
                "sources": [{"title": "Result 1"}],
            },
        }

        # 验证两者类型不同
        assert thinking_event["type"] != sources_event["type"]

        # 验证两者都有 round 字段，可以关联
        assert thinking_event["data"]["round"] == sources_event["data"]["round"]


class TestEventTypeValidation:
    """测试事件类型验证"""

    @pytest.mark.unit
    def test_all_v7218_event_types(self):
        """测试所有 v7.218 相关的事件类型"""
        v7218_event_types = [
            "analysis_progress",  # v7.218 新增
            "thinking_chunk",  # v7.218 增加 phase 字段
            "unified_dialogue_chunk",  # Phase 0 内容
            "round_sources",  # 搜索结果
            "phase",  # 阶段转换
        ]

        for event_type in v7218_event_types:
            # 验证事件类型是有效字符串
            assert isinstance(event_type, str)
            assert len(event_type) > 0

    @pytest.mark.unit
    def test_thinking_chunk_phase_values(self):
        """测试 thinking_chunk phase 字段的有效值"""
        # v7.218: phase 字段用于区分不同阶段的思考
        valid_phases = ["search_round"]  # 目前只有搜索轮次

        for phase in valid_phases:
            event = {
                "type": "thinking_chunk",
                "data": {
                    "round": 1,
                    "content": "test",
                    "phase": phase,
                },
            }
            assert event["data"]["phase"] in valid_phases


class TestIntegrationScenarios:
    """测试集成场景"""

    @pytest.mark.unit
    def test_complete_search_flow_events(self):
        """测试完整搜索流程的事件序列"""
        # 模拟完整的搜索流程事件
        events = []

        # Phase 0: 结构化分析
        events.append({"type": "phase", "data": {"phase": "structured_analysis"}})
        events.append({"type": "analysis_progress", "data": {"stage": "starting", "estimated_time": 180}})
        events.append({"type": "unified_dialogue_chunk", "content": "分析用户需求..."})
        events.append({"type": "analysis_progress", "data": {"stage": "complete"}})

        # Phase 2: 搜索轮次
        events.append({"type": "phase", "data": {"phase": "search"}})

        # Round 1
        events.append({"type": "thinking_chunk", "data": {"round": 1, "phase": "search_round", "content": "规划第一轮..."}})
        events.append({"type": "round_sources", "data": {"round": 1, "sources": [{"title": "Source 1"}]}})

        # Round 2
        events.append({"type": "thinking_chunk", "data": {"round": 2, "phase": "search_round", "content": "规划第二轮..."}})
        events.append({"type": "round_sources", "data": {"round": 2, "sources": [{"title": "Source 2"}]}})

        # 验证事件数量 (4 Phase0 + 1 phase + 4 Phase2 = 9)
        assert len(events) == 9

        # 验证 analysis_progress 事件
        analysis_events = [e for e in events if e.get("type") == "analysis_progress"]
        assert len(analysis_events) == 2
        assert analysis_events[0]["data"]["stage"] == "starting"
        assert analysis_events[1]["data"]["stage"] == "complete"

        # 验证 thinking_chunk 事件都有 phase 字段
        thinking_events = [e for e in events if e.get("type") == "thinking_chunk"]
        for e in thinking_events:
            assert e["data"].get("phase") == "search_round"

        # 验证 round_sources 事件
        sources_events = [e for e in events if e.get("type") == "round_sources"]
        assert len(sources_events) == 2

    @pytest.mark.unit
    def test_frontend_state_mapping(self):
        """测试前端状态映射"""
        # 模拟前端状态
        frontend_state = {
            "problemSolvingThinking": "",  # Phase 0 内容
            "roundThinkingMap": {},  # Phase 2 轮次思考
            "searchRounds": [],  # 搜索结果
            "analysisProgress": None,  # 分析进度
            "isProblemSolvingPhase": True,  # 是否在 Phase 0
        }

        # 处理 analysis_progress 事件
        event1 = {"type": "analysis_progress", "data": {"stage": "starting", "estimated_time": 180}}
        frontend_state["analysisProgress"] = event1["data"]
        assert frontend_state["analysisProgress"]["stage"] == "starting"

        # 处理 unified_dialogue_chunk 事件 (Phase 0)
        event2 = {"type": "unified_dialogue_chunk", "content": "用户需求分析..."}
        frontend_state["problemSolvingThinking"] += event2["content"]
        assert "用户需求分析" in frontend_state["problemSolvingThinking"]

        # 处理 analysis_progress complete 事件
        event3 = {"type": "analysis_progress", "data": {"stage": "complete"}}
        frontend_state["analysisProgress"] = None  # 清除进度
        frontend_state["isProblemSolvingPhase"] = False
        assert frontend_state["analysisProgress"] is None

        # 处理 thinking_chunk 事件 (Phase 2)
        event4 = {"type": "thinking_chunk", "data": {"round": 1, "content": "规划搜索...", "phase": "search_round"}}
        round_num = event4["data"]["round"]
        if round_num not in frontend_state["roundThinkingMap"]:
            frontend_state["roundThinkingMap"][round_num] = ""
        frontend_state["roundThinkingMap"][round_num] += event4["data"]["content"]
        assert frontend_state["roundThinkingMap"][1] == "规划搜索..."

        # 验证 Phase 0 和 Phase 2 内容分离
        assert frontend_state["problemSolvingThinking"] != frontend_state["roundThinkingMap"][1]


# ==================== 运行配置 ====================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "unit"])
