"""
测试 v7.129: 概念图角色差异化
验证V2-V6各角色生成不同类型的概念图，而非都是空间效果图

Author: Claude Code
Created: 2026-01-04
"""

import pytest

from intelligent_project_analyzer.workflow.nodes.deliverable_id_generator_node import (
    ROLE_VISUAL_IDENTITY,
    _generate_role_specific_deliverables,
    _map_role_to_format,
)


class TestRoleVisualIdentity:
    """测试角色视觉身份常量定义"""

    def test_role_visual_identity_completeness(self):
        """测试所有角色都有视觉身份定义"""
        expected_roles = ["V2", "V3", "V4", "V5", "V6", "V7"]  # 🆕 v7.145: 添加V7

        for role in expected_roles:
            assert role in ROLE_VISUAL_IDENTITY, f"缺少{role}的视觉身份定义"

            identity = ROLE_VISUAL_IDENTITY[role]
            assert "perspective" in identity, f"{role}缺少perspective字段"
            assert "visual_type" in identity, f"{role}缺少visual_type字段"
            assert "unique_angle" in identity, f"{role}缺少unique_angle字段"
            assert "avoid_patterns" in identity, f"{role}缺少avoid_patterns字段"

    def test_v2_identity(self):
        """测试V2设计总监的视觉身份"""
        v2 = ROLE_VISUAL_IDENTITY["V2"]

        assert v2["perspective"] == "综合设计协调者"
        assert v2["visual_type"] == "architectural_section"
        assert "空间整合" in v2["unique_angle"]
        assert "纯效果图" in v2["avoid_patterns"]

    def test_v3_identity(self):
        """测试V3叙事专家的视觉身份"""
        v3 = ROLE_VISUAL_IDENTITY["V3"]

        assert v3["perspective"] == "叙事体验设计师"
        assert v3["visual_type"] == "narrative_storyboard"
        assert "情感连接" in v3["unique_angle"]
        assert "建筑效果图" in v3["avoid_patterns"]  # 🔥 V3应避免空间效果图

    def test_v4_identity(self):
        """测试V4研究员的视觉身份"""
        v4 = ROLE_VISUAL_IDENTITY["V4"]

        assert v4["perspective"] == "设计研究分析师"
        assert v4["visual_type"] == "research_infographic"
        assert "数据洞察" in v4["unique_angle"]
        assert "空间效果图" in v4["avoid_patterns"]  # 🔥 V4应避免空间效果图

    def test_v5_identity(self):
        """测试V5场景专家的视觉身份"""
        v5 = ROLE_VISUAL_IDENTITY["V5"]

        assert v5["perspective"] == "场景与行为专家"
        assert v5["visual_type"] == "contextual_flowchart"
        assert "行为" in v5["unique_angle"]
        assert "静态空间图" in v5["avoid_patterns"]

    def test_v6_identity(self):
        """测试V6工程师的视觉身份"""
        v6 = ROLE_VISUAL_IDENTITY["V6"]

        assert v6["perspective"] == "技术实施工程师"
        assert v6["visual_type"] == "technical_blueprint"
        assert "工程可行性" in v6["unique_angle"]
        assert "艺术效果图" in v6["avoid_patterns"]  # 🔥 V6应避免艺术效果图

    def test_v7_identity(self):
        """测试V7情感洞察专家的视觉身份"""
        v7 = ROLE_VISUAL_IDENTITY["V7"]

        assert v7["perspective"] == "空间情感洞察专家"
        assert v7["visual_type"] == "emotional_atmosphere"
        assert "心理安全" in v7["unique_angle"] or "情感连接" in v7["unique_angle"]
        assert "冰冷技术图纸" in v7["avoid_patterns"] or "纯功能性布局" in v7["avoid_patterns"]


class TestRoleFormatMapping:
    """测试角色到format的映射"""

    def test_v2_format(self):
        """V2 → architectural_design"""
        assert _map_role_to_format("V2") == "architectural_design"

    def test_v3_format(self):
        """V3 → narrative"""
        assert _map_role_to_format("V3") == "narrative"

    def test_v4_format(self):
        """V4 → visualization (图表类)"""
        assert _map_role_to_format("V4") == "visualization"

    def test_v5_format(self):
        """V5 → contextual (情境类)"""
        assert _map_role_to_format("V5") == "contextual"

    def test_v6_format(self):
        """V6 → technical_doc (技术文档类)"""
        assert _map_role_to_format("V6") == "technical_doc"

    def test_v7_format(self):
        """V7 → emotional_insight (情感洞察类)"""
        assert _map_role_to_format("V7") == "emotional_insight"

    def test_default_format(self):
        """未知角色应返回analysis"""
        assert _map_role_to_format("V9") == "analysis"


class TestDeliverableMetadataGeneration:
    """测试交付物元数据生成是否正确注入视觉身份"""

    @pytest.fixture
    def questionnaire_keywords(self):
        """模拟问卷关键词"""
        return {
            "location": "蛇口渔村",
            "space_type": "老渔民住宅",
            "budget": "中等预算",
            "style_label": "现代海洋风",
            "material_keywords": ["木材", "石材", "玻璃"],
            "functional_keywords": ["储物", "采光", "通风"],
            "emotional_keywords": ["温馨", "怀旧", "海洋"],
            "color_palette": "蓝色、米白色",
        }

    def test_v2_deliverable_has_visual_identity(self, questionnaire_keywords):
        """测试V2交付物包含视觉身份字段"""
        deliverables = _generate_role_specific_deliverables(
            role_id="2-1",
            role_base_type="V2",
            user_input="设计蛇口渔村老宅改造",
            structured_requirements={},
            questionnaire_keywords=questionnaire_keywords,
            confirmed_core_tasks=[],
        )

        assert len(deliverables) > 0
        first_deliverable = deliverables[0]

        # 检查constraints中是否有视觉身份字段
        constraints = first_deliverable.get("constraints", {})
        assert "role_perspective" in constraints, "V2缺少role_perspective字段"
        assert "visual_type" in constraints, "V2缺少visual_type字段"
        assert "deliverable_format" in constraints, "V2缺少deliverable_format字段"
        assert "unique_angle" in constraints, "V2缺少unique_angle字段"
        assert "avoid_patterns" in constraints, "V2缺少avoid_patterns字段"

        # 验证值的正确性
        assert constraints["role_perspective"] == "综合设计协调者"
        assert constraints["visual_type"] == "architectural_section"
        assert constraints["deliverable_format"] == "architectural_design"

    def test_v3_deliverable_has_visual_identity(self, questionnaire_keywords):
        """测试V3交付物包含视觉身份字段"""
        deliverables = _generate_role_specific_deliverables(
            role_id="3-1",
            role_base_type="V3",
            user_input="设计蛇口渔村老宅改造",
            structured_requirements={},
            questionnaire_keywords=questionnaire_keywords,
            confirmed_core_tasks=[],
        )

        assert len(deliverables) > 0
        first_deliverable = deliverables[0]
        constraints = first_deliverable.get("constraints", {})

        # 验证V3的独特视觉身份
        assert constraints["role_perspective"] == "叙事体验设计师"
        assert constraints["visual_type"] == "narrative_storyboard"
        assert constraints["deliverable_format"] == "narrative"
        assert "情感连接" in constraints["unique_angle"]
        assert "建筑效果图" in constraints["avoid_patterns"]  # 🔥 V3避免建筑图

    def test_v4_deliverable_has_visual_identity(self, questionnaire_keywords):
        """测试V4交付物包含视觉身份字段（新增动态生成）"""
        deliverables = _generate_role_specific_deliverables(
            role_id="4-1",
            role_base_type="V4",
            user_input="设计蛇口渔村老宅改造",
            structured_requirements={},
            questionnaire_keywords=questionnaire_keywords,
            confirmed_core_tasks=[],
        )

        assert len(deliverables) > 0
        first_deliverable = deliverables[0]
        constraints = first_deliverable.get("constraints", {})

        # 验证V4的研究视觉身份
        assert constraints["role_perspective"] == "设计研究分析师"
        assert constraints["visual_type"] == "research_infographic"
        assert constraints["deliverable_format"] == "visualization"  # 🔥 图表类
        assert "数据洞察" in constraints["unique_angle"]
        assert "空间效果图" in constraints["avoid_patterns"]  # 🔥 V4避免空间图

    def test_v5_deliverable_has_visual_identity(self, questionnaire_keywords):
        """测试V5交付物包含视觉身份字段"""
        deliverables = _generate_role_specific_deliverables(
            role_id="5-1",
            role_base_type="V5",
            user_input="设计蛇口渔村老宅改造",
            structured_requirements={},
            questionnaire_keywords=questionnaire_keywords,
            confirmed_core_tasks=[],
        )

        assert len(deliverables) > 0
        first_deliverable = deliverables[0]
        constraints = first_deliverable.get("constraints", {})

        # 验证V5的场景视觉身份
        assert constraints["role_perspective"] == "场景与行为专家"
        assert constraints["visual_type"] == "contextual_flowchart"
        assert constraints["deliverable_format"] == "contextual"
        assert "行为" in constraints["unique_angle"]

    def test_v6_deliverable_has_visual_identity(self, questionnaire_keywords):
        """测试V6交付物包含视觉身份字段"""
        deliverables = _generate_role_specific_deliverables(
            role_id="6-1",
            role_base_type="V6",
            user_input="设计蛇口渔村老宅改造",
            structured_requirements={},
            questionnaire_keywords=questionnaire_keywords,
            confirmed_core_tasks=[],
        )

        assert len(deliverables) > 0
        first_deliverable = deliverables[0]
        constraints = first_deliverable.get("constraints", {})

        # 验证V6的技术视觉身份
        assert constraints["role_perspective"] == "技术实施工程师"
        assert constraints["visual_type"] == "technical_blueprint"
        assert constraints["deliverable_format"] == "technical_doc"  # 技术文档类
        assert "工程可行性" in constraints["unique_angle"]
        assert "艺术效果图" in constraints["avoid_patterns"]  # V6避免艺术图

    def test_v7_deliverable_has_visual_identity(self, questionnaire_keywords):
        """测试V7交付物包含视觉身份字段"""
        deliverables = _generate_role_specific_deliverables(
            role_id="7-1",
            role_base_type="V7",
            user_input="设计蛇口渔村老宅改造",
            structured_requirements={},
            questionnaire_keywords=questionnaire_keywords,
            confirmed_core_tasks=[],
        )

        assert len(deliverables) > 0
        first_deliverable = deliverables[0]
        constraints = first_deliverable.get("constraints", {})

        # 验证V7的情感视觉身份
        assert constraints["role_perspective"] == "空间情感洞察专家"
        assert constraints["visual_type"] == "emotional_atmosphere"
        assert constraints["deliverable_format"] == "emotional_insight"
        assert "心理安全" in constraints["unique_angle"] or "情感连接" in constraints["unique_angle"]
        assert "冰冷技术图纸" in constraints["avoid_patterns"]  # V7避免冰冷技术图纸


class TestVisualTypeDifferentiation:
    """测试各角色的visual_type确实不同"""

    def test_all_roles_have_different_visual_types(self):
        """测试所有角色的visual_type都不相同"""
        visual_types = set()

        for role, identity in ROLE_VISUAL_IDENTITY.items():
            visual_type = identity["visual_type"]
            assert visual_type not in visual_types, f"{role}的visual_type重复: {visual_type}"
            visual_types.add(visual_type)

        # 🆕 v7.145: 确保有7种不同的类型（V2-V7）
        assert len(visual_types) == 7

    def test_v2_to_v7_format_mapping_unique(self):
        """测试V2-V7的format映射都不相同（除了默认值）"""
        formats = {_map_role_to_format(f"V{i}") for i in [2, 3, 4, 5, 6, 7]}

        # 所有角色应该有不同的format（允许部分相同，但至少5种以上）
        assert len(formats) >= 5, f"format类型太少: {formats}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
