"""
v12.0 智能约束识别系统 — 单元测试

测试范围：
U1: _extract_spatial_zones — 空间区域提取（正则 + structured_requirements）
U2: _build_constraint_envelope — 三层约束信封组装
U3: _auto_classify_constraint_level — 约束等级自动分类
U4: ConstraintSourceExtractor — 初始化和 prompt 路由
U5: State 字段 — visual_constraints / extracted_spatial_zones 默认值
U6: _run_constraint_pipeline — 空输入短路返回 None
"""

import asyncio
import os
import sys
import pytest
from unittest.mock import MagicMock

# 添加项目根目录
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytestmark = [pytest.mark.unit]


# ==============================================================================
# U1: _extract_spatial_zones
# ==============================================================================


class TestU1ExtractSpatialZones:
    """空间区域提取器单元测试"""

    @pytest.fixture(autouse=True)
    def _import(self):
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            _extract_spatial_zones,
        )

        self.fn = _extract_spatial_zones

    def test_always_includes_overall(self):
        """U1.1: 任何输入都应包含 'overall' 兜底区域"""
        zones = self.fn({}, "")
        ids = [z["id"] for z in zones]
        assert "overall" in ids
        assert zones[0]["id"] == "overall"
        assert zones[0]["source"] == "preset"

    def test_extracts_numbered_floors(self):
        """U1.2: 从 '1楼/2层/3F' 等模式提取楼层"""
        zones = self.fn({}, "1楼客厅很大，2层有三间卧室")
        ids = {z["id"] for z in zones}
        assert "1f" in ids
        assert "2f" in ids

    def test_extracts_special_zones(self):
        """U1.3: 提取地下室、阁楼、露台、庭院等特殊区域"""
        text = "这个项目有地下室车库，顶层有阁楼和露台，后院有庭院"
        zones = self.fn({}, text)
        ids = {z["id"] for z in zones}
        assert "basement" in ids
        assert "attic" in ids
        assert "terrace" in ids
        assert "garden" in ids

    def test_extracts_room_types(self):
        """U1.4: 提取常见功能区名称（客厅、卧室、书房等）"""
        text = "需要一个开放式客厅和餐厅连通，主卧带独立书房，儿童房要阳光充足"
        zones = self.fn({}, text)
        ids = {z["id"] for z in zones}
        assert "living_room" in ids
        assert "dining_room" in ids
        assert "master_bedroom" in ids
        assert "study" in ids
        assert "kids_room" in ids

    def test_no_duplicate_ids(self):
        """U1.5: 不会产生重复的区域ID"""
        text = "客厅很大，客厅需要改造，客厅采光好"
        zones = self.fn({}, text)
        ids = [z["id"] for z in zones]
        assert len(ids) == len(set(ids)), f"存在重复ID: {ids}"

    def test_structured_requirements_zones(self):
        """U1.6: 从 structured_requirements.spatial_description.zones 提取区域"""
        sr = {"spatial_description": {"zones": ["影音室", "健身房"]}}
        zones = self.fn(sr, "")
        labels = {z["label"] for z in zones}
        assert "影音室" in labels
        assert "健身房" in labels

    def test_empty_input_only_overall(self):
        """U1.7: 空输入仅返回 overall"""
        zones = self.fn({}, "")
        assert len(zones) == 1
        assert zones[0]["id"] == "overall"

    def test_complex_mixed_input(self):
        """U1.8: 复杂混合输入（楼层+功能区+特殊区域）"""
        text = "三层别墅，1楼客厅餐厅厨房，2楼主卧书房卫生间，3楼阁楼，地下室车库，后花园"
        zones = self.fn({}, text)
        # 至少应该有 overall + 1f + 2f + 3f + 多个功能区
        assert len(zones) >= 8, f"Only got {len(zones)} zones: {[z['label'] for z in zones]}"


# ==============================================================================
# U2: _build_constraint_envelope
# ==============================================================================


class TestU2BuildConstraintEnvelope:
    """三层约束信封组装单元测试"""

    @pytest.fixture(autouse=True)
    def _import(self):
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            _build_constraint_envelope,
        )

        self.fn = _build_constraint_envelope

    def _default_zones(self):
        return [
            {"id": "overall", "label": "整体", "source": "preset"},
            {"id": "1f", "label": "1F", "source": "extracted"},
        ]

    def test_empty_constraints_returns_empty(self):
        """U2.1: 空约束返回空字符串"""
        result = self.fn({}, self._default_zones())
        assert result == ""

    def test_envelope_has_header_and_footer(self):
        """U2.2: 非空约束应包含标准头尾标记"""
        constraints = {"overall": [{"level": "immutable", "description": "承重墙不可移动"}]}
        result = self.fn(constraints, self._default_zones())
        assert "设计参照系" in result
        assert "END" in result

    def test_three_level_labels_present(self):
        """U2.3: 三个等级的中文标签正确显示"""
        constraints = {
            "overall": [
                {"level": "immutable", "description": "A"},
                {"level": "baseline", "description": "B"},
                {"level": "opportunity", "description": "C"},
            ]
        }
        result = self.fn(constraints, self._default_zones())
        assert "L1 不可变" in result
        assert "L2 基准" in result
        assert "L3 机会" in result

    def test_multi_zone_shows_zone_headers(self):
        """U2.4: 多区域时显示区域标题"""
        constraints = {
            "overall": [{"level": "baseline", "description": "层高2.8m"}],
            "1f": [{"level": "immutable", "description": "入户门朝北"}],
        }
        result = self.fn(constraints, self._default_zones())
        assert "整体" in result
        assert "1F" in result

    def test_style_tendencies_included(self):
        """U2.5: 风格倾向正确附加"""
        constraints = {"overall": [{"level": "baseline", "description": "X"}]}
        style = {"prefer": ["现代简约", "北欧"], "avoid": ["欧式古典"]}
        result = self.fn(constraints, self._default_zones(), style)
        assert "现代简约" in result
        assert "欧式古典" in result

    def test_soft_limit_truncation(self):
        """U2.6: 超过800字符时被截断"""
        # 制造大量约束
        constraints = {
            "overall": [
                {"level": "baseline", "description": f"这是一条很长的约束描述用于测试截断逻辑，编号{i}，请确保系统能正确处理"} for i in range(50)
            ]
        }
        result = self.fn(constraints, self._default_zones())
        assert len(result) <= 800 or result.endswith("...")

    def test_per_level_max_5_items(self):
        """U2.7: 每个级别最多显示5条"""
        constraints = {"overall": [{"level": "immutable", "description": f"约束{i}"} for i in range(10)]}
        result = self.fn(constraints, self._default_zones())
        # 计算 L1 区域内的 '-' 开头行数
        lines = result.split("\n")
        l1_items = [line for line in lines if line.strip().startswith("- 约束")]
        assert len(l1_items) <= 5

    def test_none_style_tendencies_no_crash(self):
        """U2.8: style_tendencies=None 不崩溃"""
        constraints = {"overall": [{"level": "baseline", "description": "X"}]}
        result = self.fn(constraints, self._default_zones(), None)
        assert "设计参照系" in result


# ==============================================================================
# U3: _auto_classify_constraint_level
# ==============================================================================


class TestU3AutoClassifyConstraintLevel:
    """约束等级自动分类单元测试"""

    @pytest.fixture(autouse=True)
    def _import(self):
        from intelligent_project_analyzer.services.file_processor import (
            _auto_classify_constraint_level,
        )

        self.fn = _auto_classify_constraint_level

    def test_immutable_keywords(self):
        """U3.1: 包含'承重'关键词应归类为 immutable"""
        level = self.fn("承重墙位置不可移动", "floor_plan", False)
        assert level == "immutable"

    def test_immutable_by_removable_false(self):
        """U3.2: removable=False 应归类为 immutable"""
        level = self.fn("某个固定元素", "floor_plan", False)
        assert level == "immutable"

    def test_opportunity_keywords(self):
        """U3.3: 包含'机会'/'改善'关键词应归类为 opportunity"""
        level = self.fn("可以改善的采光区域", "site_photo", True)
        assert level == "opportunity"

    def test_baseline_default(self):
        """U3.4: 无特殊关键词时默认为 baseline"""
        level = self.fn("普通的层高描述", "floor_plan", True)
        assert level == "baseline"

    def test_plumbing_is_immutable(self):
        """U3.5: 管井/管道应为 immutable"""
        level = self.fn("管井位于卫生间旁边", "floor_plan", True)
        assert level == "immutable"


# ==============================================================================
# U4: ConstraintSourceExtractor
# ==============================================================================


class TestU4ConstraintSourceExtractor:
    """ConstraintSourceExtractor 类单元测试"""

    @pytest.fixture(autouse=True)
    def _import(self):
        from intelligent_project_analyzer.services.file_processor import (
            ConstraintSourceExtractor,
        )

        self.cls = ConstraintSourceExtractor

    def test_init_with_none_llm(self):
        """U4.1: vision_llm=None 时不崩溃"""
        ext = self.cls(vision_llm=None, enable_vision_api=False)
        assert ext.vision_llm is None
        assert ext.enable_vision_api is False

    def test_init_with_mock_llm(self):
        """U4.2: 传入 mock LLM 正常初始化"""
        mock_llm = MagicMock()
        ext = self.cls(vision_llm=mock_llm, enable_vision_api=True)
        assert ext.vision_llm is mock_llm
        assert ext.enable_vision_api is True

    def test_floor_plan_prompt_contains_topology(self):
        """U4.3: 平面图 prompt 包含空间拓扑相关关键词"""
        ext = self.cls(vision_llm=None, enable_vision_api=False)
        prompt = ext._get_floor_plan_prompt("1F")
        assert "spatial_topology" in prompt or "拓扑" in prompt or "topology" in prompt.lower()

    def test_site_photo_prompt_contains_conditions(self):
        """U4.4: 现场照片 prompt 包含现有条件相关关键词"""
        ext = self.cls(vision_llm=None, enable_vision_api=False)
        prompt = ext._get_site_photo_prompt("客厅")
        assert "existing_conditions" in prompt or "现有" in prompt or "conditions" in prompt.lower()


# ==============================================================================
# U5: State 字段默认值
# ==============================================================================


class TestU5StateFields:
    """State 新字段默认值测试"""

    def test_visual_constraints_default_none(self):
        """U5.1: visual_constraints 初始为 None"""
        from intelligent_project_analyzer.core.state import StateManager

        sm = StateManager()
        state = sm.create_initial_state("test input", "test-session-001")
        assert state.get("visual_constraints") is None

    def test_extracted_spatial_zones_default_none(self):
        """U5.2: extracted_spatial_zones 初始为 None"""
        from intelligent_project_analyzer.core.state import StateManager

        sm = StateManager()
        state = sm.create_initial_state("test input", "test-session-001")
        assert state.get("extracted_spatial_zones") is None

    def test_state_has_visual_constraints_key(self):
        """U5.3: 初始 state 字典包含 visual_constraints 键"""
        from intelligent_project_analyzer.core.state import StateManager

        sm = StateManager()
        state = sm.create_initial_state("test input", "test-session-001")
        assert "visual_constraints" in state

    def test_state_has_extracted_spatial_zones_key(self):
        """U5.4: 初始 state 字典包含 extracted_spatial_zones 键"""
        from intelligent_project_analyzer.core.state import StateManager

        sm = StateManager()
        state = sm.create_initial_state("test input", "test-session-001")
        assert "extracted_spatial_zones" in state


# ==============================================================================
# U6: _run_constraint_pipeline 空输入
# ==============================================================================


class TestU6RunConstraintPipelineEmpty:
    """约束管线空输入短路测试"""

    @pytest.fixture(autouse=True)
    def _import(self):
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            _run_constraint_pipeline,
        )

        self.fn = _run_constraint_pipeline

    def test_no_uploaded_refs_returns_none(self):
        """U6.1: 无上传图片时管线返回 None"""
        result = asyncio.run(self.fn({}))
        assert result is None

    def test_empty_uploaded_refs_returns_none(self):
        """U6.2: 上传图片列表为空时返回 None"""
        result = asyncio.run(self.fn({"uploaded_visual_references": []}))
        assert result is None

    def test_only_context_docs_returns_none(self):
        """U6.3: 仅有 context_document 类型图片时返回 None"""
        refs = [
            {
                "file_path": "/tmp/test.pdf",
                "structured_features": {"image_type": "context_document"},
            }
        ]
        result = asyncio.run(self.fn({"uploaded_visual_references": refs}))
        assert result is None
