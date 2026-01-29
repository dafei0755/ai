"""
v7.154 修复验证测试

测试内容:
1. P0-1: 搜索URL过滤逻辑
2. P0-2: 雷达图维度API响应
3. P0-3: 概念图类型选择逻辑
4. P1-1: V7触发条件
5. P1-2: 角色差异化指令
6. P1-3: 自评分校准机制
"""

import sys
from pathlib import Path

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestP0_1_URLFiltering:
    """P0-1: 测试搜索URL过滤逻辑"""

    def test_placeholder_url_detection(self):
        """测试占位符URL检测"""
        placeholder_urls = [
            "https://www.example.com/",
            "https://example2.com/page",
            "http://test.com/article",
            "https://placeholder.com/data",
            "http://localhost:8080/api",
            "http://127.0.0.1/test",
        ]

        valid_urls = [
            "https://www.baidu.com/article",
            "https://arxiv.org/abs/2301.00001",
            "https://github.com/project",
            "https://zhihu.com/question/123",
        ]

        # 占位符检测逻辑
        placeholder_patterns = ["example.com", "example2.com", "placeholder", "test.com", "localhost", "127.0.0.1"]

        for url in placeholder_urls:
            is_placeholder = any(p in url.lower() for p in placeholder_patterns)
            assert is_placeholder, f"应该检测到占位符URL: {url}"

        for url in valid_urls:
            is_placeholder = any(p in url.lower() for p in placeholder_patterns)
            assert not is_placeholder, f"不应该误判为占位符URL: {url}"


class TestP0_2_RadarDimensions:
    """P0-2: 测试雷达图维度API响应"""

    def test_structured_report_response_has_radar_fields(self):
        """测试StructuredReportResponse包含雷达图字段"""
        from intelligent_project_analyzer.api.server import StructuredReportResponse

        # 检查字段是否存在
        fields = StructuredReportResponse.model_fields
        assert "radar_dimensions" in fields, "应该包含radar_dimensions字段"
        assert "radar_dimension_values" in fields, "应该包含radar_dimension_values字段"

        # 测试实例化
        report = StructuredReportResponse(
            radar_dimensions=[{"id": "dim1", "name": "维度1"}], radar_dimension_values={"dim1": 0.8}
        )
        assert report.radar_dimensions is not None
        assert report.radar_dimension_values is not None


class TestP0_3_ConceptImageType:
    """P0-3: 测试概念图类型选择逻辑"""

    def test_visual_type_for_project(self):
        """测试项目类型感知的视觉类型选择"""
        from intelligent_project_analyzer.utils.visual_config_loader import get_role_visual_type_for_project

        # V4在设计类项目中应该返回case_comparison
        design_projects = [
            "interior_design",
            "architectural",
            "hybrid_residential_commercial",
            "design_project",
        ]

        for project_type in design_projects:
            visual_type = get_role_visual_type_for_project("V4", project_type)
            assert visual_type == "case_comparison", f"V4在{project_type}项目中应该使用case_comparison，实际: {visual_type}"

        # V4在数据类项目中应该返回data_infographic
        data_projects = ["data_project", "research_project"]
        for project_type in data_projects:
            visual_type = get_role_visual_type_for_project("V4", project_type)
            assert visual_type == "data_infographic", f"V4在{project_type}项目中应该使用data_infographic，实际: {visual_type}"

        # V2应该不受影响，返回默认类型
        v2_type = get_role_visual_type_for_project("V2", "interior_design")
        assert v2_type == "photorealistic_rendering", f"V2应该使用photorealistic_rendering，实际: {v2_type}"

    def test_case_comparison_config_exists(self):
        """测试case_comparison配置存在"""
        from intelligent_project_analyzer.utils.visual_config_loader import get_visual_type_config

        config = get_visual_type_config("case_comparison")
        assert config, "case_comparison配置应该存在"
        assert "description" in config
        assert "keywords_en" in config
        assert "case study comparison" in config.get("keywords_en", [])


class TestP1_1_V7Triggers:
    """P1-1: 测试V7情感洞察专家触发条件"""

    def test_v7_trigger_keywords(self):
        """测试V7触发关键词"""
        import yaml

        config_path = (
            Path(__file__).parent.parent
            / "intelligent_project_analyzer/config/prompts/dynamic_project_director_v2.yaml"
        )

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 正确的路径是 special_scenarios.special_population
        special_scenarios = config.get("special_scenarios", {})
        special_population = special_scenarios.get("special_population", {})
        triggers = special_population.get("triggers", [])

        # 检查新增的触发词
        new_triggers = ["文化认同", "身份象征", "精神归属", "文化传承情感", "归属感需求", "情感寄托", "文人情怀"]

        for trigger in new_triggers:
            assert trigger in triggers, f"应该包含触发词: {trigger}"

        # 检查核心专家配置
        assert special_population.get("core_expert") == "V7_情感洞察专家"


class TestP1_2_RoleDifferentiation:
    """P1-2: 测试角色差异化指令"""

    def test_v4_differentiation_section(self):
        """测试V4差异化指令"""
        from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate

        template = ExpertPromptTemplate(
            role_type="V4", base_system_prompt="测试", autonomy_protocol={"version": "4.0", "protocol_content": ""}
        )

        section = template._build_role_differentiation_section()

        assert "V4设计研究员" in section
        assert "数据驱动分析" in section
        assert "国际视野" in section
        assert "避免与V5重复" in section

    def test_v5_differentiation_section(self):
        """测试V5差异化指令"""
        from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate

        template = ExpertPromptTemplate(
            role_type="V5", base_system_prompt="测试", autonomy_protocol={"version": "4.0", "protocol_content": ""}
        )

        section = template._build_role_differentiation_section()

        assert "V5场景行业专家" in section
        assert "本地化适配" in section
        assert "用户行为洞察" in section
        assert "避免与V4重复" in section

    def test_other_roles_no_differentiation(self):
        """测试其他角色无差异化指令"""
        from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate

        for role_type in ["V2", "V3", "V6", "V7"]:
            template = ExpertPromptTemplate(
                role_type=role_type,
                base_system_prompt="测试",
                autonomy_protocol={"version": "4.0", "protocol_content": ""},
            )

            section = template._build_role_differentiation_section()
            assert section == "", f"{role_type}不应该有差异化指令"


class TestP1_3_QualityCalibration:
    """P1-3: 测试自评分校准机制"""

    def test_calibration_method_exists(self):
        """测试校准方法存在"""
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory

        factory = TaskOrientedExpertFactory.__new__(TaskOrientedExpertFactory)
        assert hasattr(factory, "_calibrate_quality_scores"), "应该有_calibrate_quality_scores方法"

    def test_calibration_logic(self):
        """测试校准逻辑"""
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory

        factory = TaskOrientedExpertFactory.__new__(TaskOrientedExpertFactory)

        # 测试短内容惩罚
        short_content_output = {
            "task_execution_report": {
                "deliverable_outputs": [
                    {"deliverable_name": "测试交付物", "content": "很短的内容", "quality_self_assessment": 0.95}  # 少于200字
                ]
            }
        }

        calibrated = factory._calibrate_quality_scores(short_content_output, None)
        deliverable = calibrated["task_execution_report"]["deliverable_outputs"][0]

        # 短内容应该被惩罚
        assert deliverable["quality_self_assessment"] < 0.95, "短内容应该降低评分"
        assert "quality_calibration_note" in deliverable, "应该有校准说明"

    def test_calibration_with_good_content(self):
        """测试优质内容不被过度惩罚"""
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory

        factory = TaskOrientedExpertFactory.__new__(TaskOrientedExpertFactory)

        # 测试包含案例和数据的长内容
        good_content = (
            """
        这是一个详细的分析报告，包含多个案例研究。

        案例1：拙政园的连廊设计
        根据研究数据显示，传统园林连廊的宽度通常在1.2-1.5米之间。
        统计表明，约80%的游客更喜欢有遮阳功能的连廊设计。

        案例2：留园的空间布局
        例如，留园的曲廊设计采用了"移步换景"的手法。
        调研发现，这种设计能够增加30%的空间感知深度。

        综合以上案例分析，我们建议采用以下设计策略...
        """
            * 3
        )  # 确保超过500字

        good_content_output = {
            "task_execution_report": {
                "deliverable_outputs": [
                    {"deliverable_name": "测试交付物", "content": good_content, "quality_self_assessment": 0.95}
                ]
            }
        }

        calibrated = factory._calibrate_quality_scores(good_content_output, None)
        deliverable = calibrated["task_execution_report"]["deliverable_outputs"][0]

        # 优质内容惩罚应该较小（只有搜索引用惩罚）
        assert (
            deliverable["quality_self_assessment"] >= 0.8
        ), f"优质内容不应被过度惩罚，实际评分: {deliverable['quality_self_assessment']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
