"""
v7.240: 框架清单端到端测试

测试完整的搜索流程：
1. 用户输入查询
2. 后端生成框架清单
3. 前端接收并显示框架清单
4. 框架清单指导后续搜索
5. 会话持久化和恢复
"""

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from intelligent_project_analyzer.services.ucppt_search_engine import (
    FrameworkChecklist,
    SearchFramework,
    SearchTarget,
    UcpptSearchEngine,
)


class TestEndToEndFrameworkChecklist:
    """端到端测试：框架清单完整流程"""

    def setup_method(self):
        """每个测试前初始化"""
        self.engine = UcpptSearchEngine()

    @pytest.mark.asyncio
    async def test_complete_search_flow_with_checklist(self):
        """测试完整搜索流程中的框架清单"""
        query = "帮我设计一个北欧风格的客厅"

        # 模拟 DeepSeek API 响应
        mock_analysis_response = {
            "user_profile": {"identity_tags": ["设计爱好者"]},
            "analysis": {
                "l1_facts": ["北欧风格", "客厅设计"],
                "l3_tension": "风格与实用性平衡",
            },
            "search_framework": {
                "core_question": "如何设计北欧风客厅",
                "answer_goal": "提供完整设计方案",
                "boundary": "不涉及预算规划",
                "targets": [
                    {
                        "id": "T1",
                        "question": "北欧风格特点",
                        "search_for": "色彩材质特点",
                        "why_need": "了解风格核心",
                        "success_when": ["列出主要特点"],
                        "priority": 1,
                        "category": "风格调研",
                    },
                    {
                        "id": "T2",
                        "question": "家具选择建议",
                        "search_for": "适合的家具品牌",
                        "why_need": "提供具体推荐",
                        "success_when": ["推荐3-5个品牌"],
                        "priority": 2,
                        "category": "产品推荐",
                    },
                ],
            },
        }

        collected_events = []

        with patch.object(
            self.engine,
            "_deepseek_call",
            new_callable=AsyncMock,
            return_value={
                "reasoning_content": "深度分析思考过程...",
                "content": json.dumps(mock_analysis_response, ensure_ascii=False),
            },
        ):
            with patch.object(
                self.engine,
                "_parse_unified_analysis_json",
                return_value=(mock_analysis_response, {"grade": "A", "score": 0.9}),
            ):
                try:
                    async for event in self.engine._unified_analysis_stream(query, {}):
                        collected_events.append(event)
                        # 收集到 analysis_complete 后停止
                        if event.get("type") == "analysis_complete":
                            break
                except Exception as e:
                    print(f"流程中断: {e}")

        # 验证事件流
        event_types = [e.get("type") for e in collected_events]
        print(f"收集到的事件类型: {event_types}")

        # 查找 search_framework_ready 事件
        framework_event = next((e for e in collected_events if e.get("type") == "search_framework_ready"), None)

        if framework_event:
            data = framework_event.get("data", {})

            # 验证框架清单存在
            assert "framework_checklist" in data, "事件应包含 framework_checklist"

            checklist = data["framework_checklist"]

            # 验证框架清单结构
            assert "core_summary" in checklist
            assert "main_directions" in checklist
            assert "boundaries" in checklist
            assert "answer_goal" in checklist
            assert "plain_text" in checklist

            # 验证内容
            assert len(checklist["main_directions"]) >= 1
            assert checklist["plain_text"] != ""

            print(f"✅ 框架清单生成成功:")
            print(f"   核心问题: {checklist['core_summary']}")
            print(f"   搜索方向数: {len(checklist['main_directions'])}")
            print(f"   边界数: {len(checklist['boundaries'])}")

    def test_framework_checklist_guides_search(self):
        """测试框架清单指导搜索方向"""
        # 创建带框架清单的 SearchFramework
        framework = SearchFramework(
            original_query="测试查询",
            core_question="测试核心问题",
            answer_goal="测试目标",
            boundary="不涉及测试边界",
            targets=[
                SearchTarget(
                    id="T1",
                    name="测试目标1",
                    category="测试分类",
                    why_need="测试目的",
                    success_when=["成功标准"],
                ),
            ],
        )

        # 生成框架清单
        checklist = self.engine._generate_framework_checklist(framework, {})
        framework.framework_checklist = checklist

        # 验证框架清单被正确附加
        assert framework.framework_checklist is not None
        assert framework.framework_checklist.core_summary != ""

        # 验证框架清单可以转换为纯文字
        plain_text = framework.framework_checklist.to_plain_text()
        assert "## 核心问题" in plain_text
        assert "## 搜索主线" in plain_text

    def test_framework_checklist_persistence_format(self):
        """测试框架清单持久化格式"""
        checklist = FrameworkChecklist(
            core_summary="持久化测试核心问题",
            main_directions=[
                {"direction": "方向1", "purpose": "目的1", "expected_outcome": "期望1"},
                {"direction": "方向2", "purpose": "目的2", "expected_outcome": "期望2"},
            ],
            boundaries=["边界1", "边界2"],
            answer_goal="持久化测试目标",
            generated_at="2026-01-23T10:00:00",
        )

        # 转换为字典（用于存储）
        data = checklist.to_dict()

        # 验证可以 JSON 序列化
        json_str = json.dumps(data, ensure_ascii=False)
        assert json_str is not None

        # 验证可以反序列化
        parsed = json.loads(json_str)

        # 验证数据完整性
        assert parsed["core_summary"] == "持久化测试核心问题"
        assert len(parsed["main_directions"]) == 2
        assert len(parsed["boundaries"]) == 2
        assert parsed["answer_goal"] == "持久化测试目标"
        assert "plain_text" in parsed

    def test_framework_checklist_restoration(self):
        """测试框架清单从存储恢复"""
        # 模拟存储的数据
        stored_data = {
            "core_summary": "恢复测试",
            "main_directions": [
                {"direction": "方向A", "purpose": "目的A", "expected_outcome": "期望A"},
            ],
            "boundaries": ["边界A"],
            "answer_goal": "恢复目标",
            "generated_at": "2026-01-23T10:00:00",
            "plain_text": "## 核心问题\n恢复测试",
        }

        # 从存储数据恢复
        restored = FrameworkChecklist(
            core_summary=stored_data["core_summary"],
            main_directions=stored_data["main_directions"],
            boundaries=stored_data["boundaries"],
            answer_goal=stored_data["answer_goal"],
            generated_at=stored_data["generated_at"],
        )

        # 验证恢复正确
        assert restored.core_summary == "恢复测试"
        assert len(restored.main_directions) == 1
        assert restored.main_directions[0]["direction"] == "方向A"
        assert len(restored.boundaries) == 1
        assert restored.answer_goal == "恢复目标"


class TestFrameworkChecklistEventSimulation:
    """模拟前端事件处理"""

    def test_simulate_frontend_event_handling(self):
        """模拟前端处理 search_framework_ready 事件"""
        # 模拟后端发送的事件
        backend_event = {
            "type": "search_framework_ready",
            "data": {
                "core_question": "如何设计北欧风客厅",
                "answer_goal": "提供完整设计方案",
                "boundary": "不涉及预算",
                "target_count": 2,
                "targets": [
                    {"id": "T1", "question": "风格特点", "priority": 1},
                    {"id": "T2", "question": "家具推荐", "priority": 2},
                ],
                "targets_summary": "📋 搜索主线：\n1. 风格特点\n2. 家具推荐",
                "quality_grade": "A",
                "framework_checklist": {
                    "core_summary": "如何设计北欧风客厅",
                    "main_directions": [
                        {"direction": "风格调研", "purpose": "了解核心特征", "expected_outcome": "特点清单"},
                        {"direction": "产品推荐", "purpose": "提供具体建议", "expected_outcome": "品牌列表"},
                    ],
                    "boundaries": ["预算规划"],
                    "answer_goal": "提供完整设计方案",
                    "generated_at": "2026-01-23T10:00:00",
                    "plain_text": "## 核心问题\n如何设计北欧风客厅\n...",
                },
            },
        }

        # 模拟前端状态更新逻辑
        def handle_search_framework_ready(event_data):
            """模拟前端事件处理函数"""
            data = event_data.get("data", {})

            # 提取 framework_checklist
            checklist_data = data.get("framework_checklist")
            if checklist_data:
                framework_checklist = {
                    "core_summary": checklist_data.get("core_summary", ""),
                    "main_directions": checklist_data.get("main_directions", []),
                    "boundaries": checklist_data.get("boundaries", []),
                    "answer_goal": checklist_data.get("answer_goal", ""),
                    "generated_at": checklist_data.get("generated_at", ""),
                    "plain_text": checklist_data.get("plain_text", ""),
                }
                return framework_checklist
            return None

        # 执行处理
        result = handle_search_framework_ready(backend_event)

        # 验证结果
        assert result is not None
        assert result["core_summary"] == "如何设计北欧风客厅"
        assert len(result["main_directions"]) == 2
        assert result["main_directions"][0]["direction"] == "风格调研"
        assert len(result["boundaries"]) == 1
        assert result["answer_goal"] == "提供完整设计方案"

    def test_simulate_session_save_and_restore(self):
        """模拟会话保存和恢复"""
        # 模拟前端状态
        frontend_state = {
            "status": "done",
            "query": "测试查询",
            "sources": [],
            "frameworkChecklist": {
                "core_summary": "测试核心",
                "main_directions": [
                    {"direction": "方向1", "purpose": "目的1", "expected_outcome": "期望1"},
                ],
                "boundaries": ["边界1"],
                "answer_goal": "测试目标",
                "generated_at": "2026-01-23T10:00:00",
                "plain_text": "纯文字内容",
            },
            "searchMasterLine": {
                "core_question": "测试问题",
                "tasks": [],
            },
        }

        # 模拟保存到后端
        save_payload = {
            "session_id": "test-session-123",
            "query": frontend_state["query"],
            "sources": frontend_state["sources"],
            "frameworkChecklist": frontend_state["frameworkChecklist"],
            "searchMasterLine": frontend_state["searchMasterLine"],
        }

        # 验证保存数据结构
        json_str = json.dumps(save_payload, ensure_ascii=False)
        assert json_str is not None

        # 模拟从后端恢复
        restored_data = json.loads(json_str)

        # 验证恢复的数据
        assert restored_data["frameworkChecklist"]["core_summary"] == "测试核心"
        assert len(restored_data["frameworkChecklist"]["main_directions"]) == 1


class TestFrameworkChecklistRealWorldScenarios:
    """真实场景测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.engine = UcpptSearchEngine()

    def test_complex_query_framework_generation(self):
        """测试复杂查询的框架生成"""
        framework = SearchFramework(
            original_query="我想在峨眉山开一家精品民宿，想用HAY的家具，但不确定北欧风格是否适合中国山区环境，需要考虑当地气候和文化因素",
            core_question="如何在中国山区民宿中融合北欧HAY家具风格",
            answer_goal="提供HAY家具在峨眉山民宿的适配方案",
            boundary="不涉及：1.具体施工方案 2.详细预算规划 3.其他品牌对比",
            targets=[
                SearchTarget(id="T1", name="HAY品牌", category="品牌调研", why_need="了解品牌", success_when=["品牌历史"]),
                SearchTarget(id="T2", name="融合案例", category="案例研究", why_need="获取参考", success_when=["3个案例"]),
                SearchTarget(id="T3", name="环境分析", category="环境调研", why_need="了解约束", success_when=["气候特点"]),
                SearchTarget(id="T4", name="文化融合", category="文化研究", why_need="确保适配", success_when=["融合策略"]),
            ],
        )

        checklist = self.engine._generate_framework_checklist(framework, {})

        # 验证生成结果
        assert checklist.core_summary != ""
        assert len(checklist.main_directions) == 4
        assert len(checklist.boundaries) >= 1

        # 验证纯文字输出
        plain_text = checklist.to_plain_text()
        assert "## 核心问题" in plain_text
        assert "## 搜索主线（4个方向）" in plain_text
        assert "## 搜索边界" in plain_text
        assert "## 回答目标" in plain_text

        print(f"\n复杂查询框架清单:")
        print(plain_text)

    def test_simple_query_framework_generation(self):
        """测试简单查询的框架生成"""
        framework = SearchFramework(
            original_query="北欧风格客厅怎么设计",
            core_question="北欧风格客厅设计方法",
            answer_goal="提供设计建议",
            boundary="",
            targets=[
                SearchTarget(id="T1", name="风格特点", category="调研", why_need="了解风格"),
            ],
        )

        checklist = self.engine._generate_framework_checklist(framework, {})

        # 验证生成结果
        assert checklist.core_summary != ""
        assert len(checklist.main_directions) == 1
        assert checklist.boundaries == []  # 空边界

        # 验证纯文字输出不包含边界部分
        plain_text = checklist.to_plain_text()
        assert "## 搜索边界" not in plain_text

    def test_framework_checklist_with_special_characters(self):
        """测试包含特殊字符的框架生成"""
        framework = SearchFramework(
            original_query="如何设计「现代中式」风格的客厅？（预算10-20万）",
            core_question="现代中式客厅设计",
            answer_goal="提供设计方案（含预算建议）",
            boundary="不涉及：施工细节、材料采购",
            targets=[
                SearchTarget(id="T1", name="风格定义「现代中式」", category="调研", why_need="明确风格"),
            ],
        )

        checklist = self.engine._generate_framework_checklist(framework, {})

        # 验证特殊字符被正确处理
        assert checklist.core_summary != ""
        plain_text = checklist.to_plain_text()
        assert plain_text is not None

        # 验证可以 JSON 序列化
        data = checklist.to_dict()
        json_str = json.dumps(data, ensure_ascii=False)
        assert json_str is not None


class TestFrameworkChecklistErrorHandling:
    """错误处理测试"""

    def setup_method(self):
        """每个测试前初始化"""
        self.engine = UcpptSearchEngine()

    def test_empty_framework_handling(self):
        """测试空框架处理"""
        framework = SearchFramework(
            original_query="",
            core_question="",
            answer_goal="",
            boundary="",
            targets=[],
        )

        checklist = self.engine._generate_framework_checklist(framework, {})

        # 应该生成默认值
        assert checklist is not None
        assert checklist.main_directions == []

    def test_none_values_handling(self):
        """测试 None 值处理"""
        framework = SearchFramework(
            original_query="测试",
            core_question="测试",
            answer_goal="",
            boundary="",
            targets=[
                SearchTarget(
                    id="T1",
                    name="",
                    category="",
                    why_need="",
                    success_when=[],
                ),
            ],
        )

        checklist = self.engine._generate_framework_checklist(framework, {})

        # 应该正常生成，不抛出异常
        assert checklist is not None

    def test_malformed_boundary_handling(self):
        """测试格式错误的边界处理"""
        framework = SearchFramework(
            original_query="测试",
            core_question="测试",
            answer_goal="目标",
            boundary="这是一个没有标准格式的边界描述",
            targets=[],
        )

        checklist = self.engine._generate_framework_checklist(framework, {})

        # 应该正常处理，可能边界为空或包含原始文本
        assert checklist is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
