"""
框架清单持久化 - 回归测试 v7.241

确保修复没有破坏现有功能
"""

import asyncio
from datetime import datetime

import pytest

from intelligent_project_analyzer.services.session_archive_manager import get_archive_manager


class TestFrameworkChecklistRegression:
    """框架清单回归测试"""

    @pytest.fixture
    def test_session_id(self):
        """生成测试会话ID"""
        return f"test-regression-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    @pytest.mark.asyncio
    async def test_backward_compatibility_old_sessions(self, test_session_id):
        """测试向后兼容：旧会话（无框架清单）仍可正常加载"""
        manager = get_archive_manager()

        # 保存旧格式会话（不包含框架清单）
        success = await manager.archive_search_session(
            session_id=test_session_id,
            query="旧格式测试查询",
            search_result={
                "sources": [{"title": "来源1", "url": "http://example.com"}],
                "images": [],
                "thinkingContent": "旧格式思考",
                "answerContent": "旧格式答案",
                "searchPlan": None,
                "rounds": [],
                "totalRounds": 0,
                "executionTime": 5.0,
                "isDeepMode": False,
            },
            user_id=None,
            force=True,
        )

        assert success, "保存旧格式会话失败"

        # 加载旧格式会话
        session = await manager.get_search_session(test_session_id)

        assert session is not None, "旧格式会话未找到"
        result = session["search_result"]

        # 验证旧字段仍然存在
        assert "sources" in result
        assert len(result["sources"]) == 1
        assert "thinkingContent" in result
        assert result["thinkingContent"] == "旧格式思考"
        assert "answerContent" in result
        assert result["answerContent"] == "旧格式答案"

        # 验证新字段存在但为 None（向后兼容）
        assert "frameworkChecklist" in result
        assert result["frameworkChecklist"] is None

    @pytest.mark.asyncio
    async def test_existing_fields_not_affected(self, test_session_id):
        """测试现有字段不受影响"""
        manager = get_archive_manager()

        # 保存包含所有字段的会话
        success = await manager.archive_search_session(
            session_id=test_session_id,
            query="完整字段测试",
            search_result={
                "sources": [{"title": "来源1", "url": "http://example.com"}],
                "images": [{"url": "http://example.com/image.jpg"}],
                "thinkingContent": "思考内容",
                "answerContent": "答案内容",
                "searchPlan": {"plan": "搜索计划"},
                "rounds": [{"round": 1}],
                "totalRounds": 1,
                "executionTime": 10.5,
                "isDeepMode": True,
                "l0Content": "L0内容",
                "problemSolvingThinking": "解题思考",
                "structuredInfo": {"info": "结构化信息"},
                "frameworkChecklist": {
                    "core_summary": "测试摘要",
                    "main_directions": [],
                    "boundaries": [],
                    "answer_goal": "测试目标",
                },
            },
            user_id=None,
            force=True,
        )

        assert success, "保存完整字段会话失败"

        # 加载会话
        session = await manager.get_search_session(test_session_id)
        result = session["search_result"]

        # 验证所有现有字段都正确保存和加载
        assert len(result["sources"]) == 1
        assert len(result["images"]) == 1
        assert result["thinkingContent"] == "思考内容"
        assert result["answerContent"] == "答案内容"
        assert result["searchPlan"] == {"plan": "搜索计划"}
        assert len(result["rounds"]) == 1
        assert result["totalRounds"] == 1
        assert result["executionTime"] == 10.5
        assert result["isDeepMode"] is True
        assert result["l0Content"] == "L0内容"
        assert result["problemSolvingThinking"] == "解题思考"
        assert result["structuredInfo"] == {"info": "结构化信息"}

        # 验证新字段也正确保存
        assert result["frameworkChecklist"]["core_summary"] == "测试摘要"

    @pytest.mark.asyncio
    async def test_update_preserves_existing_data(self, test_session_id):
        """测试更新操作保留现有数据"""
        manager = get_archive_manager()

        # 首次保存
        await manager.archive_search_session(
            session_id=test_session_id,
            query="更新测试",
            search_result={
                "sources": [{"title": "原始来源", "url": "http://example.com"}],
                "images": [],
                "thinkingContent": "原始思考",
                "answerContent": "原始答案",
                "searchPlan": None,
                "rounds": [],
                "totalRounds": 0,
                "executionTime": 5.0,
                "isDeepMode": True,
                "frameworkChecklist": {
                    "core_summary": "原始摘要",
                    "main_directions": [],
                    "boundaries": [],
                    "answer_goal": "原始目标",
                },
            },
            user_id=None,
            force=True,
        )

        # 更新会话（只更新部分字段）
        await manager.archive_search_session(
            session_id=test_session_id,
            query="更新测试",
            search_result={
                "sources": [{"title": "更新来源", "url": "http://example.com"}],
                "images": [],
                "thinkingContent": "更新思考",
                "answerContent": "更新答案",
                "searchPlan": None,
                "rounds": [],
                "totalRounds": 0,
                "executionTime": 5.0,
                "isDeepMode": True,
                "frameworkChecklist": {
                    "core_summary": "更新摘要",
                    "main_directions": [],
                    "boundaries": [],
                    "answer_goal": "更新目标",
                },
            },
            user_id=None,
            force=True,
        )

        # 验证更新成功
        session = await manager.get_search_session(test_session_id)
        result = session["search_result"]

        assert result["sources"][0]["title"] == "更新来源"
        assert result["thinkingContent"] == "更新思考"
        assert result["frameworkChecklist"]["core_summary"] == "更新摘要"

    @pytest.mark.asyncio
    async def test_null_and_empty_values(self, test_session_id):
        """测试 null 和空值处理"""
        manager = get_archive_manager()

        # 保存包含 null 和空值的会话
        success = await manager.archive_search_session(
            session_id=test_session_id,
            query="空值测试",
            search_result={
                "sources": [],
                "images": [],
                "thinkingContent": "",
                "answerContent": "",
                "searchPlan": None,
                "rounds": [],
                "totalRounds": 0,
                "executionTime": 0,
                "isDeepMode": False,
                "l0Content": "",
                "problemSolvingThinking": "",
                "structuredInfo": None,
                "frameworkChecklist": None,
                "searchMasterLine": None,
            },
            user_id=None,
            force=True,
        )

        assert success, "保存空值会话失败"

        # 加载会话
        session = await manager.get_search_session(test_session_id)
        result = session["search_result"]

        # 验证空值正确处理
        assert result["sources"] == []
        assert result["images"] == []
        assert result["thinkingContent"] == ""
        assert result["answerContent"] == ""
        assert result["searchPlan"] is None
        assert result["frameworkChecklist"] is None
        assert result["searchMasterLine"] is None

    @pytest.mark.asyncio
    async def test_large_framework_checklist(self, test_session_id):
        """测试大型框架清单（边界情况）"""
        manager = get_archive_manager()

        # 创建大型框架清单
        large_checklist = {
            "core_summary": "这是一个非常长的核心摘要" * 10,
            "main_directions": [
                {"direction": f"方向{i}", "purpose": f"目的{i}" * 5, "expected_outcome": f"期望{i}" * 5} for i in range(20)
            ],
            "boundaries": [f"边界{i}" for i in range(50)],
            "answer_goal": "这是一个非常长的回答目标" * 10,
            "generated_at": datetime.now().isoformat(),
        }

        success = await manager.archive_search_session(
            session_id=test_session_id,
            query="大型框架清单测试",
            search_result={
                "sources": [],
                "images": [],
                "thinkingContent": "",
                "answerContent": "",
                "searchPlan": None,
                "rounds": [],
                "totalRounds": 0,
                "executionTime": 0,
                "isDeepMode": True,
                "frameworkChecklist": large_checklist,
            },
            user_id=None,
            force=True,
        )

        assert success, "保存大型框架清单失败"

        # 加载并验证
        session = await manager.get_search_session(test_session_id)
        result = session["search_result"]
        checklist = result["frameworkChecklist"]

        assert len(checklist["main_directions"]) == 20
        assert len(checklist["boundaries"]) == 50

    @pytest.mark.asyncio
    async def test_special_characters_in_checklist(self, test_session_id):
        """测试框架清单中的特殊字符"""
        manager = get_archive_manager()

        special_checklist = {
            "core_summary": "包含特殊字符：<>&\"'`\n\t",
            "main_directions": [
                {
                    "direction": "方向<script>alert('xss')</script>",
                    "purpose": "目的 & 原因",
                    "expected_outcome": "期望 \"引号\" '单引号'",
                }
            ],
            "boundaries": ["边界\n换行", "边界\t制表符"],
            "answer_goal": "目标 <html> & 'quotes'",
        }

        success = await manager.archive_search_session(
            session_id=test_session_id,
            query="特殊字符测试",
            search_result={
                "sources": [],
                "images": [],
                "thinkingContent": "",
                "answerContent": "",
                "searchPlan": None,
                "rounds": [],
                "totalRounds": 0,
                "executionTime": 0,
                "isDeepMode": True,
                "frameworkChecklist": special_checklist,
            },
            user_id=None,
            force=True,
        )

        assert success, "保存特殊字符框架清单失败"

        # 加载并验证特殊字符正确保存
        session = await manager.get_search_session(test_session_id)
        result = session["search_result"]
        checklist = result["frameworkChecklist"]

        assert "<>&\"'`" in checklist["core_summary"]
        assert "<script>" in checklist["main_directions"][0]["direction"]
        assert "\n" in checklist["boundaries"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
