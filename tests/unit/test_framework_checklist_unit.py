"""
框架清单持久化 - 单元测试 v7.241

测试 FrameworkChecklist 数据类和相关方法的单元功能
"""

from datetime import datetime

import pytest

from intelligent_project_analyzer.services.ucppt_search_engine import (
    FrameworkChecklist,
    SearchFramework,
    SearchTarget,
    UcpptSearchEngine,
)


class TestFrameworkChecklistUnit:
    """框架清单单元测试"""

    def test_framework_checklist_initialization(self):
        """测试框架清单初始化"""
        checklist = FrameworkChecklist(
            core_summary="测试核心摘要",
            main_directions=[{"direction": "方向1", "purpose": "目的1", "expected_outcome": "期望1"}],
            boundaries=["边界1", "边界2"],
            answer_goal="测试目标",
            generated_at="2026-01-23T15:00:00",
        )

        assert checklist.core_summary == "测试核心摘要"
        assert len(checklist.main_directions) == 1
        assert len(checklist.boundaries) == 2
        assert checklist.answer_goal == "测试目标"
        assert checklist.generated_at == "2026-01-23T15:00:00"

    def test_framework_checklist_to_dict(self):
        """测试 to_dict 方法"""
        checklist = FrameworkChecklist(
            core_summary="测试",
            main_directions=[],
            boundaries=[],
            answer_goal="目标",
        )

        result = checklist.to_dict()

        assert "core_summary" in result
        assert "main_directions" in result
        assert "boundaries" in result
        assert "answer_goal" in result
        assert "generated_at" in result
        assert "plain_text" in result

    def test_framework_checklist_to_plain_text(self):
        """测试 to_plain_text 方法"""
        checklist = FrameworkChecklist(
            core_summary="如何设计民宿",
            main_directions=[{"direction": "风格调研", "purpose": "了解风格", "expected_outcome": "色彩方案"}],
            boundaries=["不涉及预算"],
            answer_goal="提供设计方案",
        )

        plain_text = checklist.to_plain_text()

        assert "## 核心问题" in plain_text
        assert "如何设计民宿" in plain_text
        assert "## 搜索主线" in plain_text
        assert "风格调研" in plain_text
        assert "## 搜索边界" in plain_text
        assert "不涉及预算" in plain_text
        assert "## 回答目标" in plain_text
        assert "提供设计方案" in plain_text

    def test_generate_framework_checklist_from_targets(self):
        """测试从 targets 生成框架清单"""
        engine = UcpptSearchEngine()

        framework = SearchFramework(
            original_query="测试查询",
            core_question="测试问题",
            answer_goal="测试目标",
            boundary="不涉及：预算、施工",
            targets=[
                SearchTarget(
                    id="T1",
                    name="目标1",
                    category="调研",
                    question="问题1",
                    why_need="原因1",
                    success_when=["标准1"],
                ),
                SearchTarget(
                    id="T2",
                    name="目标2",
                    category="分析",
                    question="问题2",
                    why_need="原因2",
                    success_when=["标准2"],
                ),
            ],
        )

        checklist = engine._generate_framework_checklist(framework, {})

        assert checklist.core_summary != ""
        assert len(checklist.main_directions) == 2
        assert checklist.answer_goal == "测试目标"
        assert len(checklist.boundaries) >= 1  # 应该解析出边界

    def test_generate_framework_checklist_empty_targets(self):
        """测试空 targets 列表"""
        engine = UcpptSearchEngine()

        framework = SearchFramework(
            original_query="测试查询",
            core_question="测试问题",
            answer_goal="测试目标",
            boundary="",
            targets=[],
        )

        checklist = engine._generate_framework_checklist(framework, {})

        assert checklist.core_summary != ""
        assert checklist.main_directions == []
        assert checklist.answer_goal == "测试目标"

    def test_boundary_parsing(self):
        """测试边界字符串解析"""
        engine = UcpptSearchEngine()

        # 测试不同格式的边界字符串
        test_cases = [
            ("不涉及：预算、施工、材料", 3),
            ("不搜索：1.预算 2.施工 3.材料", 3),
            ("不涉及预算规划和施工细节", 2),
            ("", 0),
        ]

        for boundary_str, expected_count in test_cases:
            framework = SearchFramework(
                original_query="测试",
                core_question="测试",
                answer_goal="目标",
                boundary=boundary_str,
                targets=[],
            )

            checklist = engine._generate_framework_checklist(framework, {})

            if expected_count > 0:
                assert len(checklist.boundaries) >= 1, f"Failed for: {boundary_str}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
