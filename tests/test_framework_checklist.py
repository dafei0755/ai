"""
v7.240: 框架清单单元测试

测试 FrameworkChecklist 数据类的功能：
1. 数据结构正确性
2. to_plain_text() 方法
3. to_dict() 方法
4. _generate_framework_checklist() 方法
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# 导入被测试的类
from intelligent_project_analyzer.services.ucppt_search_engine import (
    FrameworkChecklist,
    SearchFramework,
    SearchTarget,
    UcpptSearchEngine,
)


class TestFrameworkChecklistDataClass:
    """测试 FrameworkChecklist 数据类"""

    def test_default_values(self):
        """测试默认值初始化"""
        checklist = FrameworkChecklist()

        assert checklist.core_summary == ""
        assert checklist.main_directions == []
        assert checklist.boundaries == []
        assert checklist.answer_goal == ""
        assert checklist.generated_at == ""

    def test_with_values(self):
        """测试带值初始化"""
        checklist = FrameworkChecklist(
            core_summary="如何设计北欧风客厅",
            main_directions=[
                {"direction": "风格调研", "purpose": "了解北欧风核心特征", "expected_outcome": "色彩、材质特点"},
                {"direction": "空间规划", "purpose": "确定功能分区", "expected_outcome": "动线方案"},
            ],
            boundaries=["不涉及厨房设计", "不涉及预算规划"],
            answer_goal="提供完整的北欧风客厅设计方案",
            generated_at="2026-01-23T10:00:00",
        )

        assert checklist.core_summary == "如何设计北欧风客厅"
        assert len(checklist.main_directions) == 2
        assert len(checklist.boundaries) == 2
        assert checklist.answer_goal == "提供完整的北欧风客厅设计方案"


class TestFrameworkChecklistToPlainText:
    """测试 to_plain_text() 方法"""

    def test_basic_plain_text(self):
        """测试基本纯文字输出"""
        checklist = FrameworkChecklist(
            core_summary="测试问题",
            main_directions=[
                {"direction": "方向1", "purpose": "目的1", "expected_outcome": "期望1"},
            ],
            boundaries=["边界1"],
            answer_goal="回答目标",
        )

        plain_text = checklist.to_plain_text()

        assert "## 核心问题" in plain_text
        assert "测试问题" in plain_text
        assert "## 搜索主线（1个方向）" in plain_text
        assert "**方向1**" in plain_text
        assert "目的：目的1" in plain_text
        assert "期望：期望1" in plain_text
        assert "## 搜索边界（不涉及）" in plain_text
        assert "边界1" in plain_text
        assert "## 回答目标" in plain_text
        assert "回答目标" in plain_text

    def test_multiple_directions(self):
        """测试多个搜索方向"""
        checklist = FrameworkChecklist(
            core_summary="多方向测试",
            main_directions=[
                {"direction": "方向A", "purpose": "目的A", "expected_outcome": "期望A"},
                {"direction": "方向B", "purpose": "目的B", "expected_outcome": "期望B"},
                {"direction": "方向C", "purpose": "目的C", "expected_outcome": "期望C"},
            ],
            boundaries=[],
            answer_goal="测试目标",
        )

        plain_text = checklist.to_plain_text()

        assert "## 搜索主线（3个方向）" in plain_text
        assert "1. **方向A**" in plain_text
        assert "2. **方向B**" in plain_text
        assert "3. **方向C**" in plain_text

    def test_empty_boundaries(self):
        """测试空边界列表"""
        checklist = FrameworkChecklist(
            core_summary="无边界测试",
            main_directions=[{"direction": "方向1", "purpose": "", "expected_outcome": ""}],
            boundaries=[],
            answer_goal="目标",
        )

        plain_text = checklist.to_plain_text()

        # 空边界时不应该有边界部分
        assert "## 搜索边界" not in plain_text

    def test_optional_fields(self):
        """测试可选字段（purpose/expected_outcome为空）"""
        checklist = FrameworkChecklist(
            core_summary="可选字段测试",
            main_directions=[
                {"direction": "只有方向", "purpose": "", "expected_outcome": ""},
            ],
            boundaries=[],
            answer_goal="目标",
        )

        plain_text = checklist.to_plain_text()

        assert "**只有方向**" in plain_text
        # 空的purpose和expected_outcome不应该显示
        assert "目的：\n" not in plain_text or "目的：" not in plain_text


class TestFrameworkChecklistToDict:
    """测试 to_dict() 方法"""

    def test_to_dict_structure(self):
        """测试字典结构"""
        checklist = FrameworkChecklist(
            core_summary="字典测试",
            main_directions=[{"direction": "方向1", "purpose": "目的1", "expected_outcome": "期望1"}],
            boundaries=["边界1", "边界2"],
            answer_goal="回答目标",
            generated_at="2026-01-23T10:00:00",
        )

        result = checklist.to_dict()

        assert "core_summary" in result
        assert "main_directions" in result
        assert "boundaries" in result
        assert "answer_goal" in result
        assert "generated_at" in result
        assert "plain_text" in result

        assert result["core_summary"] == "字典测试"
        assert len(result["main_directions"]) == 1
        assert len(result["boundaries"]) == 2
        assert result["answer_goal"] == "回答目标"
        assert isinstance(result["plain_text"], str)

    def test_to_dict_plain_text_included(self):
        """测试字典包含plain_text"""
        checklist = FrameworkChecklist(
            core_summary="包含纯文字",
            main_directions=[],
            boundaries=[],
            answer_goal="目标",
        )

        result = checklist.to_dict()

        assert "plain_text" in result
        assert "## 核心问题" in result["plain_text"]


class TestGenerateFrameworkChecklist:
    """测试 _generate_framework_checklist() 方法"""

    def setup_method(self):
        """每个测试前初始化"""
        self.engine = UcpptSearchEngine()

    def test_generate_from_targets(self):
        """测试从 targets 生成框架清单"""
        framework = SearchFramework(
            original_query="如何选择适合的装修风格",
            core_question="如何选择适合的装修风格",
            answer_goal="提供风格选择建议和实施方案",
            boundary="不涉及具体施工细节、不涉及预算规划",
            targets=[
                SearchTarget(
                    id="T1",
                    name="风格对比",
                    category="调研",
                    question="主流装修风格有哪些特点",
                    why_need="帮助用户了解选项",
                    success_when=["列出5种以上风格", "包含优缺点对比"],
                ),
                SearchTarget(
                    id="T2",
                    name="案例参考",
                    category="案例",
                    question="各风格的实际案例效果",
                    why_need="提供视觉参考",
                    success_when=["每种风格至少3个案例"],
                ),
            ],
        )

        checklist = self.engine._generate_framework_checklist(framework, {})

        assert checklist.core_summary != ""
        assert len(checklist.main_directions) == 2
        assert checklist.answer_goal == "提供风格选择建议和实施方案"
        # 边界应该被解析
        assert len(checklist.boundaries) >= 1

    def test_generate_with_long_core_question(self):
        """测试长核心问题被截断"""
        long_question = "这是一个非常非常非常非常非常非常非常非常非常非常长的核心问题描述"
        framework = SearchFramework(
            original_query=long_question,
            core_question=long_question,
            answer_goal="目标",
            boundary="",
            targets=[],
        )

        checklist = self.engine._generate_framework_checklist(framework, {})

        # 核心问题应该被截断到30字以内
        assert len(checklist.core_summary) <= 33  # 30 + "..."

    def test_generate_with_empty_targets(self):
        """测试空 targets 列表"""
        framework = SearchFramework(
            original_query="测试查询",
            core_question="测试问题",
            answer_goal="测试目标",
            boundary="",
            targets=[],
        )

        checklist = self.engine._generate_framework_checklist(framework, {})

        assert checklist.core_summary != ""
        assert checklist.main_directions == []
        assert checklist.answer_goal == "测试目标"

    def test_generate_boundary_parsing(self):
        """测试边界字符串解析"""
        framework = SearchFramework(
            original_query="测试",
            core_question="测试",
            answer_goal="目标",
            boundary="不搜索：1.具体施工 2.预算规划 3.材料采购",
            targets=[],
        )

        checklist = self.engine._generate_framework_checklist(framework, {})

        # 边界应该被正确解析
        assert len(checklist.boundaries) >= 1

    def test_generate_boundary_parsing_alternative_format(self):
        """测试边界字符串解析（顿号分隔格式）"""
        framework = SearchFramework(
            original_query="测试",
            core_question="测试",
            answer_goal="目标",
            boundary="不涉及：施工细节、预算规划、材料采购",
            targets=[],
        )

        checklist = self.engine._generate_framework_checklist(framework, {})

        # 边界应该被正确解析
        assert len(checklist.boundaries) >= 1

    def test_generate_timestamp(self):
        """测试生成时间戳"""
        framework = SearchFramework(
            original_query="测试",
            core_question="测试",
            answer_goal="目标",
            boundary="",
            targets=[],
        )

        checklist = self.engine._generate_framework_checklist(framework, {})

        assert checklist.generated_at != ""
        # 验证是有效的ISO格式时间戳
        datetime.fromisoformat(checklist.generated_at)

    def test_generate_direction_from_target_fields(self):
        """测试从 target 各字段提取方向信息"""
        framework = SearchFramework(
            original_query="测试",
            core_question="测试",
            answer_goal="目标",
            boundary="",
            targets=[
                SearchTarget(
                    id="T1",
                    name="测试目标",
                    category="测试分类",
                    why_need="测试目的",
                    purpose="备用目的",
                    success_when=["成功标准1", "成功标准2"],
                    expected_info=["期望信息1"],
                ),
            ],
        )

        checklist = self.engine._generate_framework_checklist(framework, {})

        assert len(checklist.main_directions) == 1
        direction = checklist.main_directions[0]
        # category 优先于 name
        assert direction["direction"] == "测试分类"
        # why_need 优先于 purpose
        assert direction["purpose"] == "测试目的"
        # success_when 优先于 expected_info
        assert "成功标准1" in direction["expected_outcome"]


class TestSearchFrameworkWithChecklist:
    """测试 SearchFramework 与 FrameworkChecklist 的集成"""

    def test_framework_checklist_field(self):
        """测试 SearchFramework 的 framework_checklist 字段"""
        framework = SearchFramework(
            original_query="测试",
            core_question="测试",
        )

        # 默认应该是 None
        assert framework.framework_checklist is None

        # 可以设置
        checklist = FrameworkChecklist(core_summary="测试")
        framework.framework_checklist = checklist

        assert framework.framework_checklist is not None
        assert framework.framework_checklist.core_summary == "测试"


class TestFrameworkChecklistEdgeCases:
    """测试边界情况"""

    def test_special_characters_in_content(self):
        """测试内容中的特殊字符"""
        checklist = FrameworkChecklist(
            core_summary="包含特殊字符：<>&\"'",
            main_directions=[
                {"direction": "方向<>", "purpose": "目的&", "expected_outcome": "期望\"'"},
            ],
            boundaries=["边界<>&"],
            answer_goal="目标<>&",
        )

        plain_text = checklist.to_plain_text()
        result = checklist.to_dict()

        # 应该正常处理特殊字符
        assert "<>" in plain_text
        assert "&" in plain_text
        assert result["core_summary"] == "包含特殊字符：<>&\"'"

    def test_unicode_content(self):
        """测试Unicode内容"""
        checklist = FrameworkChecklist(
            core_summary="中文测试 🎯 日本語テスト",
            main_directions=[
                {"direction": "方向🔍", "purpose": "目的📋", "expected_outcome": "期望✅"},
            ],
            boundaries=["边界🚫"],
            answer_goal="目标🎯",
        )

        plain_text = checklist.to_plain_text()
        result = checklist.to_dict()

        assert "🎯" in plain_text
        assert "🔍" in plain_text
        assert "中文测试" in result["core_summary"]

    def test_empty_direction_fields(self):
        """测试方向字段为空的情况"""
        checklist = FrameworkChecklist(
            core_summary="测试",
            main_directions=[
                {"direction": "", "purpose": "", "expected_outcome": ""},
            ],
            boundaries=[],
            answer_goal="目标",
        )

        plain_text = checklist.to_plain_text()

        # 空方向名应该被处理
        assert "1. ****" in plain_text or "1." in plain_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
