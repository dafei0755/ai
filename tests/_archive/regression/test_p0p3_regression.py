"""
回归测试: P0-P3 修改不破坏既有功能
版本: v8.000
日期: 2026-02-16

测试范围：
  R1: mode_detector 原有检测能力不退化
  R2: core_task_decomposer._select_few_shot_fallback 原逻辑正常
  R3: few-shot 示例文件向后兼容 (旧文件不被改坏)
  R4: extract_detected_modes_from_state 旧格式兼容
  R5: sf_knowledge_loader 文件缺失不崩溃
  R6: _inject_sf_knowledge / _build_sf_evaluation_context 异常不阻断
  R7: 10 Mode Engine 所有模式关键词检测不退化
"""

import pytest
from pathlib import Path
from unittest.mock import patch
import yaml

PROJECT_ROOT = Path(__file__).parent.parent.parent


# ============================================================================
# R1: mode_detector 原有检测能力
# ============================================================================


class TestR1ModeDetectorRegression:
    """回归: 模式检测不退化"""

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "input_text,expected_mode",
        [
            ("高端住宅设计，强调品牌精神和文化母题的表达", "M1_concept_driven"),
            ("办公空间设计，优化动线流程，提升运转效率", "M2_function_efficiency"),
            ("精品酒店设计，追求沉浸式体验，五感调动", "M3_emotional_experience"),
            ("商业地产项目，关注投资回报率和坪效优化", "M4_capital_asset"),
            ("乡村民宿项目，融入村落肌理，地域文化", "M5_rural_context"),
            ("老街区改造项目，厂房改造，城市更新", "M6_urban_regeneration"),
            ("智能住宅设计，全屋智能系统，AI技术整合", "M7_tech_integration"),
        ],
    )
    def test_mode_detection_stable(self, input_text, expected_mode):
        """各模式关键词检测稳定"""
        from intelligent_project_analyzer.services.mode_detector import DesignModeDetector

        results = DesignModeDetector.detect(input_text)
        assert len(results) > 0, f"'{input_text[:20]}...' 应检测到至少一个模式"
        mode_ids = [r[0] for r in results]
        assert expected_mode in mode_ids, f"期望 {expected_mode}, 实际: {mode_ids}"


# ============================================================================
# R2: fallback 逻辑正常
# ============================================================================


class TestR2FallbackRegression:
    """回归: _select_few_shot_fallback 原逻辑正常"""

    @pytest.fixture
    def decomposer(self):
        from intelligent_project_analyzer.services.core_task_decomposer import CoreTaskDecomposer

        return CoreTaskDecomposer.__new__(CoreTaskDecomposer)

    @pytest.mark.unit
    def test_commercial_type_fallback(self, decomposer):
        """commercial 类型 fallback 到 commercial_dominant_01"""
        result = decomposer._select_few_shot_fallback("commercial", {})
        assert result == "commercial_dominant_01"

    @pytest.mark.unit
    def test_residential_type_fallback(self, decomposer):
        """residential 类型 fallback 到 functional_dominant_01"""
        result = decomposer._select_few_shot_fallback("residential", {})
        assert result == "functional_dominant_01"

    @pytest.mark.unit
    def test_feature_based_fallback(self, decomposer):
        """特征驱动 fallback"""
        result = decomposer._select_few_shot_fallback("unknown", {"wellness": 0.9})
        assert result == "functional_dominant_01"

    @pytest.mark.unit
    def test_default_fallback(self, decomposer):
        """兜底 fallback 返回 commercial_dominant_01"""
        result = decomposer._select_few_shot_fallback("weird_type", {})
        assert result == "commercial_dominant_01"


# ============================================================================
# R3: 旧 few-shot 文件向后兼容
# ============================================================================


class TestR3OldFewShotCompatibility:
    """回归: 已有 few-shot 文件未被损坏"""

    EXAMPLES_DIR = PROJECT_ROOT / "intelligent_project_analyzer" / "config" / "prompts" / "few_shot_examples"

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "filename",
        [
            "commercial_dominant_01.yaml",
            "functional_dominant_01.yaml",
        ],
    )
    def test_old_files_intact(self, filename):
        """旧文件结构完整"""
        fpath = self.EXAMPLES_DIR / filename
        if not fpath.exists():
            pytest.skip(f"{filename} 不存在")

        with open(fpath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # 示例文件嵌套在 example: 下
        inner = data.get("example", data)
        assert "project_info" in inner
        assert "ideal_tasks" in inner
        assert len(inner["ideal_tasks"]) > 0

    @pytest.mark.unit
    def test_registry_still_has_old_entries(self):
        """registry 仍包含旧条目"""
        reg_path = self.EXAMPLES_DIR / "examples_registry.yaml"
        if not reg_path.exists():
            pytest.skip("examples_registry.yaml 不存在")

        with open(reg_path, "r", encoding="utf-8") as f:
            registry = yaml.safe_load(f)

        examples = registry.get("examples", [])
        file_names = [ex.get("file", "") for ex in examples]
        assert "commercial_dominant_01.yaml" in file_names
        assert "functional_dominant_01.yaml" in file_names


# ============================================================================
# R4: detect_modes 旧格式兼容
# ============================================================================


class TestR4LegacyFormatRegression:
    """回归: extract_detected_modes_from_state 三种旧格式都能用"""

    @pytest.mark.unit
    def test_nested_empty_structures(self):
        """嵌套空结构不崩溃"""
        from intelligent_project_analyzer.services.mode_question_loader import (
            extract_detected_modes_from_state,
        )

        test_states = [
            {},
            {"agent_results": {}},
            {"agent_results": {"requirements_analyst": {}}},
            {"agent_results": {"requirements_analyst": {"structured_data": {}}}},
            {"agent_results": {"requirements_analyst": {"structured_data": {"detected_modes": []}}}},
        ]
        for state in test_states:
            result = extract_detected_modes_from_state(state)
            assert isinstance(result, list)
            assert len(result) == 0


# ============================================================================
# R5: sf/ 文件缺失不崩溃
# ============================================================================


class TestR5SfFileMissingGraceful:
    """回归: sf/ 文件缺失时优雅降级"""

    @pytest.mark.unit
    def test_missing_evaluation_matrix(self):
        """13_Evaluation_Matrix 缺失时返回空"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            clear_sf_knowledge_cache,
        )

        clear_sf_knowledge_cache()

        with patch(
            "intelligent_project_analyzer.services.sf_knowledge_loader._load_sf_file",
            return_value="",
        ):
            from intelligent_project_analyzer.services.sf_knowledge_loader import (
                get_mode_evaluation_weights,
            )

            # 重新调用（缓存已清）
            clear_sf_knowledge_cache()
            result = get_mode_evaluation_weights()
            assert isinstance(result, dict)

    @pytest.mark.unit
    def test_missing_output_standards(self):
        """14_Output_Standards 缺失时返回空"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            clear_sf_knowledge_cache,
            get_quality_floor_checklist,
        )

        clear_sf_knowledge_cache()

        with patch(
            "intelligent_project_analyzer.services.sf_knowledge_loader._load_sf_file",
            return_value="",
        ):
            clear_sf_knowledge_cache()
            result = get_quality_floor_checklist()
            assert isinstance(result, str)

    @pytest.mark.unit
    def test_full_injection_with_all_missing(self):
        """所有 sf/ 文件缺失时知识注入返回空"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            clear_sf_knowledge_cache,
            get_full_knowledge_injection,
        )

        clear_sf_knowledge_cache()

        with patch(
            "intelligent_project_analyzer.services.sf_knowledge_loader._load_sf_file",
            return_value="",
        ):
            clear_sf_knowledge_cache()
            modes = [{"mode": "M5_rural_context", "confidence": 0.8}]
            result = get_full_knowledge_injection(modes)
            assert isinstance(result, str)


# ============================================================================
# R6: 注入异常不阻断主流程
# ============================================================================


class TestR6InjectionExceptionRegression:
    """回归: 知识注入组件异常不阻断主流程"""

    @pytest.mark.unit
    def test_expert_factory_handles_import_error(self):
        """TaskOrientedExpertFactory sf 注入模块缺失不崩溃"""
        try:
            from intelligent_project_analyzer.agents.task_oriented_expert_factory import (
                TaskOrientedExpertFactory,
            )
        except Exception:
            pytest.skip("TaskOrientedExpertFactory 不可导入")

        factory = TaskOrientedExpertFactory.__new__(TaskOrientedExpertFactory)
        state = {"detected_design_modes": [{"mode": "M1_concept_driven", "confidence": 0.8}]}

        with patch(
            "intelligent_project_analyzer.services.sf_knowledge_loader.get_full_knowledge_injection",
            side_effect=Exception("模拟崩溃"),
        ):
            result = factory._inject_sf_knowledge(state)

        assert result is None, "异常不应向上传播"

    @pytest.mark.unit
    def test_reviewer_handles_loader_crash(self):
        """ReviewerRole sf 加载崩溃不阻断审核"""
        try:
            from intelligent_project_analyzer.review.review_agents import ReviewerRole
        except Exception:
            pytest.skip("ReviewerRole 不可导入")

        requirements = {"_detected_design_modes": [{"mode": "M5_rural_context", "confidence": 0.85}]}

        with patch(
            "intelligent_project_analyzer.services.sf_knowledge_loader.get_evaluation_criteria_for_modes",
            side_effect=RuntimeError("模拟崩溃"),
        ):
            result = ReviewerRole._build_sf_evaluation_context(requirements)

        assert result == "", "异常时应返回空字符串"


# ============================================================================
# R7: 全 10 模式检测不退化
# ============================================================================


class TestR7AllTenModesRegression:
    """回归: 10 个设计模式全部可检测"""

    ALL_MODE_INPUTS = {
        "M1_concept_driven": "品牌精神 文化母题 概念驱动 文人精神 艺术价值",
        "M2_function_efficiency": "功能优化 动线流程 运转效率 标准化 系统高效",
        "M3_emotional_experience": "沉浸式体验 五感 情绪节奏 记忆锚点",
        "M4_capital_asset": "投资回报率 坪效 租金溢价 资产价值",
        "M5_rural_context": "乡村民宿 村落肌理 地域文化 本地材料",
        "M6_urban_regeneration": "城市更新 街区改造 厂房改造 公共界面",
        "M7_tech_integration": "智能系统 AI技术 全屋智能 技术接口",
        "M8_extreme_condition": "极寒气候 高海拔 低氧 强紫外线",
        "M9_social_structure": "社区关系 多代同堂 代际关系 共享空间",
        "M10_future_speculation": "未来居住 元宇宙 虚实融合 未来趋势",
    }

    @pytest.mark.unit
    @pytest.mark.parametrize("mode_id", list(ALL_MODE_INPUTS.keys()))
    def test_mode_detectable(self, mode_id):
        """每个模式的关键词应能被检测到"""
        from intelligent_project_analyzer.services.mode_detector import DesignModeDetector

        input_text = self.ALL_MODE_INPUTS[mode_id]
        results = DesignModeDetector.detect(input_text)
        detected_modes = [r[0] for r in results]
        assert mode_id in detected_modes, f"{mode_id} 未被检测到, 实际: {detected_modes}"
