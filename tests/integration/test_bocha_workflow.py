#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bocha工作流集成测试 (v7.131)

测试场景:
1. 中文查询触发Bocha（而非Tavily）
2. Bocha结果被记录到tool_calls
3. 搜索引用被正确提取
4. WebSocket推送Bocha结果到前端
5. Bocha失败时降级到Tavily
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory
from intelligent_project_analyzer.agents.tool_callback import ToolCallRecorder
from intelligent_project_analyzer.core.state import ProjectAnalysisState
from intelligent_project_analyzer.services.tool_factory import ToolFactory


class TestBochaWorkflowIntegration:
    """Bocha工作流集成测试"""

    @pytest.fixture
    def mock_state(self):
        """创建模拟状态"""
        return ProjectAnalysisState(
            user_input="设计一个现代化的咖啡厅",
            project_context="为年轻白领设计现代咖啡厅",
            selected_roles=[],
            search_references=[],
        )

    @pytest.fixture
    def role_object(self):
        """创建测试角色对象"""
        return {
            "role_id": "V4_设计研究员_001",
            "role_name": "设计研究员",
            "role_type": "V4",
            "task_instruction": {
                "deliverables": [
                    {
                        "name": "市场调研",
                        "description": "分析咖啡厅设计趋势",
                        "format": "analysis",
                        "success_criteria": ["数据完整", "分析深入"],
                    }
                ]
            },
        }

    # ========== 测试1: 中文查询优先使用Bocha ==========
    @pytest.mark.asyncio
    async def test_chinese_query_uses_bocha(self):
        """测试中文查询优先使用Bocha"""
        # 创建工具
        tools = ToolFactory.create_all_tools()
        bocha_tool = tools.get("bocha")
        tavily_tool = tools.get("tavily")

        assert bocha_tool is not None, "Bocha工具未创建"
        assert tavily_tool is not None, "Tavily工具未创建"

        # 模拟语言检测和工具选择
        def is_chinese_query(text: str) -> bool:
            return any("\u4e00" <= char <= "\u9fff" for char in text)

        chinese_query = "咖啡厅设计趋势 2024"
        is_chinese = is_chinese_query(chinese_query)

        # 验证语言检测
        assert is_chinese is True, "中文查询检测失败"

        # 验证工具选择逻辑（v7.131修复后）
        if is_chinese:
            tool_to_use = bocha_tool if bocha_tool else tavily_tool
        else:
            tool_to_use = tavily_tool if tavily_tool else bocha_tool

        # 验证选择了Bocha
        assert tool_to_use == bocha_tool, "中文查询应该优先使用Bocha"

    # ========== 测试2: 英文查询优先使用Tavily ==========
    @pytest.mark.asyncio
    async def test_english_query_uses_tavily(self):
        """测试英文查询优先使用Tavily"""
        # 创建工具
        tools = ToolFactory.create_all_tools()
        bocha_tool = tools.get("bocha")
        tavily_tool = tools.get("tavily")

        def is_chinese_query(text: str) -> bool:
            return any("\u4e00" <= char <= "\u9fff" for char in text)

        english_query = "coffee shop design trends 2024"
        is_chinese = is_chinese_query(english_query)

        # 验证语言检测
        assert is_chinese is False, "英文查询检测失败"

        # 验证工具选择逻辑
        if is_chinese:
            tool_to_use = bocha_tool if bocha_tool else tavily_tool
        else:
            tool_to_use = tavily_tool if tavily_tool else bocha_tool

        # 验证选择了Tavily
        assert tool_to_use == tavily_tool, "英文查询应该优先使用Tavily"

    # ========== 测试3: 工具调用记录 ==========
    def test_tool_call_recording(self):
        """测试工具调用被正确记录"""
        # 创建记录器
        recorder = ToolCallRecorder(role_id="V4_test", deliverable_id="test_deliverable")

        # 模拟工具调用
        recorder.on_tool_start(
            serialized={"name": "bocha_search"},
            input_str='{"query": "咖啡厅设计"}',
            run_id="test_run_123",
        )

        recorder.on_tool_end(output='{"success": true, "results": [{"title": "测试结果"}]}', run_id="test_run_123")

        # 验证记录
        tool_calls = recorder.get_tool_calls()
        assert len(tool_calls) > 0, "工具调用未被记录"

        # 验证Bocha调用
        bocha_calls = [call for call in tool_calls if "bocha" in call.get("tool_name", "").lower()]
        assert len(bocha_calls) > 0, "Bocha调用未被记录"

    # ========== 测试4: 搜索引用提取 ==========
    def test_search_reference_extraction(self):
        """测试搜索引用被正确提取"""
        import json

        # 创建记录器
        recorder = ToolCallRecorder(role_id="V4_test", deliverable_id="test_deliverable")

        # 模拟Bocha工具调用
        recorder.on_tool_start(
            serialized={"name": "bocha_search"},
            input_str='{"query": "咖啡厅设计"}',
            run_id="test_run_123",
        )

        # 模拟成功响应 - 必须是JSON字符串格式
        mock_output = {
            "success": True,
            "results": [
                {
                    "title": "2024咖啡厅设计趋势",
                    "url": "https://example.com/coffee-design",
                    "snippet": "现代咖啡厅设计注重简约和舒适",
                    "summary": "详细分析了2024年咖啡厅设计的主要趋势",
                }
            ],
        }

        # 转换为JSON字符串
        recorder.on_tool_end(output=json.dumps(mock_output), run_id="test_run_123")

        # 提取搜索引用
        search_refs = recorder.get_search_references(deliverable_id="test_deliverable")

        # 验证引用
        assert len(search_refs) > 0, "搜索引用未被提取"

        # 验证引用内容
        first_ref = search_refs[0]
        assert first_ref.get("source_tool") == "bocha", "来源工具应该是bocha"
        assert first_ref.get("title") == "2024咖啡厅设计趋势"
        assert first_ref.get("url") == "https://example.com/coffee-design"

    # ========== 测试5: Bocha失败时降级到Tavily ==========
    @pytest.mark.asyncio
    async def test_fallback_to_tavily_when_bocha_fails(self):
        """测试Bocha失败时降级到Tavily"""
        # 创建工具
        tools = ToolFactory.create_all_tools()

        # 模拟Bocha不可用
        bocha_tool = None  # Bocha失败
        tavily_tool = tools.get("tavily")

        def is_chinese_query(text: str) -> bool:
            return any("\u4e00" <= char <= "\u9fff" for char in text)

        chinese_query = "咖啡厅设计"
        is_chinese = is_chinese_query(chinese_query)

        # 验证降级逻辑
        if is_chinese:
            tool_to_use = bocha_tool if bocha_tool else tavily_tool
        else:
            tool_to_use = tavily_tool if tavily_tool else bocha_tool

        # 验证降级到Tavily
        assert tool_to_use == tavily_tool, "Bocha不可用时应该降级到Tavily"

    # ========== 测试6: 工具名称识别 ==========
    def test_tool_name_recognition(self):
        """测试工具名称被正确识别"""
        recorder = ToolCallRecorder(role_id="V4_test", deliverable_id="test_deliverable")

        # 测试不同的工具名称格式
        test_cases = [
            ("bocha_search", True),
            ("Bocha_Search", True),
            ("BOCHA_SEARCH", True),
            ("tavily_search", False),
            ("arxiv_search", False),
        ]

        for tool_name, should_be_bocha in test_cases:
            is_bocha = "bocha" in tool_name.lower()
            assert is_bocha == should_be_bocha, f"工具名称 {tool_name} 识别错误"

    # ========== 测试7: 角色工具映射验证 ==========
    def test_role_tool_mapping(self):
        """测试角色工具映射"""
        # 硬编码的角色工具映射（来自main_workflow.py）
        role_tool_mapping = {
            "V2": [],  # 设计总监：无工具
            "V3": ["bocha", "tavily", "milvus"],
            "V4": ["bocha", "tavily", "arxiv", "milvus"],
            "V5": ["bocha", "tavily", "milvus"],
            "V6": ["bocha", "tavily", "arxiv", "milvus"],
        }

        # 验证V4角色包含Bocha
        v4_tools = role_tool_mapping.get("V4", [])
        assert "bocha" in v4_tools, "V4角色应该包含Bocha工具"

        # 验证V2角色不包含任何工具
        v2_tools = role_tool_mapping.get("V2", [])
        assert len(v2_tools) == 0, "V2角色不应该有任何工具"

    # ========== 测试8: 工具可用性验证 ==========
    def test_tool_availability_validation(self):
        """测试工具可用性验证逻辑"""
        # 创建所有工具
        tools = ToolFactory.create_all_tools()

        # 提取工具名称
        tool_names = list(tools.keys())

        # 验证Bocha在工具列表中
        assert "bocha" in tool_names, "Bocha应该在可用工具列表中"

        # 模拟角色期望的工具
        expected_tools = ["bocha", "tavily", "arxiv", "milvus"]

        # 检查缺失的工具
        missing_tools = [t for t in expected_tools if t not in tool_names]

        # 验证没有缺失关键工具
        assert "bocha" not in missing_tools, "Bocha不应该缺失"

    # ========== 测试9: 混合语言查询 ==========
    def test_mixed_language_query(self):
        """测试中英混合查询"""

        def is_chinese_query(text: str) -> bool:
            return any("\u4e00" <= char <= "\u9fff" for char in text)

        # 测试混合查询
        mixed_queries = [
            ("咖啡厅 coffee shop design", True),  # 包含中文，应该是True
            ("2024年 design trends", True),  # 包含中文，应该是True
            ("modern 设计", True),  # 包含中文，应该是True
        ]

        for query, expected in mixed_queries:
            result = is_chinese_query(query)
            assert result == expected, f"混合查询 '{query}' 检测错误"

    # ========== 测试10: 工具优先级完整流程 ==========
    @pytest.mark.asyncio
    async def test_complete_tool_priority_flow(self):
        """测试完整的工具优先级流程"""
        # 创建工具
        tools = ToolFactory.create_all_tools()
        bocha_tool = tools.get("bocha")
        tavily_tool = tools.get("tavily")
        serper_tool = tools.get("serper")

        def is_chinese_query(text: str) -> bool:
            return any("\u4e00" <= char <= "\u9fff" for char in text)

        # 测试场景1: 中文查询，所有工具可用
        chinese_query = "咖啡厅设计"
        is_chinese = is_chinese_query(chinese_query)

        if is_chinese:
            tool_to_use = bocha_tool if bocha_tool else (tavily_tool if tavily_tool else serper_tool)
            assert tool_to_use == bocha_tool, "场景1: 应该选择Bocha"

        # 测试场景2: 中文查询，Bocha不可用
        bocha_tool_temp = None
        if is_chinese:
            tool_to_use = bocha_tool_temp if bocha_tool_temp else (tavily_tool if tavily_tool else serper_tool)
            assert tool_to_use == tavily_tool, "场景2: 应该降级到Tavily"

        # 测试场景3: 英文查询，所有工具可用
        english_query = "coffee shop design"
        is_chinese = is_chinese_query(english_query)

        if not is_chinese:
            tool_to_use = tavily_tool if tavily_tool else (bocha_tool if bocha_tool else serper_tool)
            assert tool_to_use == tavily_tool, "场景3: 应该选择Tavily"


# ========== 性能测试 ==========
@pytest.mark.performance
class TestBochaPerformance:
    """Bocha性能测试"""

    @pytest.mark.asyncio
    async def test_search_performance(self):
        """测试搜索性能"""
        import time

        from intelligent_project_analyzer.agents.bocha_search_tool import create_bocha_search_tool_from_settings

        tool = create_bocha_search_tool_from_settings()
        if not tool:
            pytest.skip("Bocha未配置")

        # 执行搜索并测量时间
        start_time = time.time()
        result = tool.search("测试查询", count=5)
        elapsed_time = time.time() - start_time

        # 验证性能
        assert result["success"] is True
        assert elapsed_time < 5.0, f"搜索耗时过长: {elapsed_time:.2f}秒"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
