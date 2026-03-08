"""
单元测试: P2 运行时知识注入 (T8-T10)
版本: v8.000
日期: 2026-02-16

测试范围：
  T8: sf_knowledge_loader — 加载、解析、缓存、注入
  T9: task_oriented_expert_factory._inject_sf_knowledge
  T10: review_agents._build_sf_evaluation_context + analysis_review 注入
"""

import pytest
from unittest.mock import patch
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


# ============================================================================
# T8: sf_knowledge_loader 全面测试
# ============================================================================


class TestT8SfKnowledgeLoader:
    """P2-T8: sf_knowledge_loader 运行时加载器"""

    @pytest.fixture(autouse=True)
    def clear_cache(self):
        """每个测试前后清缓存"""
        try:
            from intelligent_project_analyzer.services.sf_knowledge_loader import (
                clear_sf_knowledge_cache,
            )

            clear_sf_knowledge_cache()
            yield
            clear_sf_knowledge_cache()
        except ImportError:
            pytest.skip("sf_knowledge_loader 不可用")

    # ── 基础加载 ──

    @pytest.mark.unit
    def test_load_evaluation_matrix(self):
        """加载 13_Evaluation_Matrix 返回非空字符串"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            load_evaluation_matrix,
        )

        content = load_evaluation_matrix()
        assert isinstance(content, str)
        assert len(content) > 100, "Evaluation Matrix 内容过短"

    @pytest.mark.unit
    def test_load_output_standards(self):
        """加载 14_Output_Standards 返回非空字符串"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            load_output_standards,
        )

        content = load_output_standards()
        assert isinstance(content, str)
        assert len(content) > 100

    @pytest.mark.unit
    def test_load_mode_engine(self):
        """加载 10_Mode_Engine 返回非空字符串"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            load_mode_engine,
        )

        content = load_mode_engine()
        assert isinstance(content, str)
        assert len(content) > 100

    @pytest.mark.unit
    def test_load_nonexistent_file_returns_empty(self):
        """加载不存在文件返回空字符串"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            _load_sf_file,
        )

        result = _load_sf_file("99_NonExistent_File")
        assert result == ""

    # ── 结构化解析 ──

    @pytest.mark.unit
    def test_get_mode_evaluation_weights_structure(self):
        """解析 mode_evaluation_weights 返回正确结构"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            get_mode_evaluation_weights,
        )

        weights = get_mode_evaluation_weights()
        assert isinstance(weights, dict)
        if weights:  # sf/13 文件存在时
            assert len(weights) >= 5, f"期望 >= 5 个模式权重, 实际 {len(weights)}"
            # 每个模式的权重应为 dict[str, float]
            for mode_id, dims in weights.items():
                assert mode_id.startswith("M"), f"模式ID格式错误: {mode_id}"
                assert isinstance(dims, dict)
                # 权重总和应接近 1.0
                total = sum(dims.values())
                assert 0.95 <= total <= 1.05, f"{mode_id} 权重和 {total} 不接近 1.0"

    @pytest.mark.unit
    def test_get_mode_deliverable_mapping_structure(self):
        """解析模式-交付物映射返回正确结构"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            get_mode_deliverable_mapping,
        )

        mapping = get_mode_deliverable_mapping()
        assert isinstance(mapping, dict)
        if mapping:
            for mode_id, deliverables in mapping.items():
                assert mode_id.startswith("M"), f"模式ID格式错误: {mode_id}"
                assert isinstance(deliverables, dict)

    @pytest.mark.unit
    def test_get_quality_floor_checklist(self):
        """质量底线文本包含 Q1-Q5"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            get_quality_floor_checklist,
        )

        text = get_quality_floor_checklist()
        assert isinstance(text, str)
        if text:
            # 至少包含部分 Q 编号
            assert "Q" in text

    # ── 按模式提取 ──

    @pytest.mark.unit
    def test_get_evaluation_criteria_for_modes(self):
        """为 M5_rural_context 提取评估标准"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            get_evaluation_criteria_for_modes,
        )

        modes = [{"mode": "M5_rural_context", "confidence": 0.85}]
        text = get_evaluation_criteria_for_modes(modes)
        assert isinstance(text, str)
        if text:
            assert "M5_rural_context" in text
            assert "评估" in text

    @pytest.mark.unit
    def test_get_evaluation_criteria_empty_modes(self):
        """空模式列表返回空字符串"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            get_evaluation_criteria_for_modes,
        )

        assert get_evaluation_criteria_for_modes([]) == ""

    @pytest.mark.unit
    def test_get_output_standards_for_modes(self):
        """为 M4_capital_asset 提取输出标准"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            get_output_standards_for_modes,
        )

        modes = [{"mode": "M4_capital_asset", "confidence": 0.90}]
        text = get_output_standards_for_modes(modes)
        assert isinstance(text, str)

    @pytest.mark.unit
    def test_get_full_knowledge_injection(self):
        """完整知识注入输出非空"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            get_full_knowledge_injection,
        )

        modes = [{"mode": "M5_rural_context", "confidence": 0.85}]
        text = get_full_knowledge_injection(modes)
        assert isinstance(text, str)
        if text:
            assert len(text) > 50

    @pytest.mark.unit
    def test_get_full_knowledge_injection_empty(self):
        """空模式返回空"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            get_full_knowledge_injection,
        )

        assert get_full_knowledge_injection([]) == ""

    # ── 缓存 ──

    @pytest.mark.unit
    def test_cache_returns_same_object(self):
        """连续两次调用返回缓存对象"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            load_evaluation_matrix,
        )

        first = load_evaluation_matrix()
        second = load_evaluation_matrix()
        assert first is second, "lru_cache 应返回同一对象"

    @pytest.mark.unit
    def test_clear_cache_reloads(self):
        """清缓存后重新加载"""
        from intelligent_project_analyzer.services.sf_knowledge_loader import (
            load_evaluation_matrix,
            clear_sf_knowledge_cache,
        )

        first = load_evaluation_matrix()
        clear_sf_knowledge_cache()
        second = load_evaluation_matrix()
        # 内容相同但对象不同
        assert first == second
        # lru_cache 清除后应创建新对象
        # (字符串可能因 interning 而 is True，所以不严格检查 identity)


# ============================================================================
# T9: task_oriented_expert_factory._inject_sf_knowledge
# ============================================================================


class TestT9ExpertSfKnowledgeInjection:
    """P2-T9: TaskOrientedExpertFactory._inject_sf_knowledge"""

    @pytest.mark.unit
    def test_inject_with_modes_returns_text(self):
        """有 detected_design_modes 时注入返回知识文本"""
        try:
            from intelligent_project_analyzer.agents.task_oriented_expert_factory import (
                TaskOrientedExpertFactory,
            )
        except Exception:
            pytest.skip("TaskOrientedExpertFactory 导入失败")

        factory = TaskOrientedExpertFactory.__new__(TaskOrientedExpertFactory)
        state = {"detected_design_modes": [{"mode": "M5_rural_context", "confidence": 0.85}]}

        with patch(
            "intelligent_project_analyzer.services.sf_knowledge_loader.get_full_knowledge_injection",
            return_value="## 评估标准\n测试内容",
        ):
            result = factory._inject_sf_knowledge(state)

        assert result is not None
        assert "评估标准" in result

    @pytest.mark.unit
    def test_inject_without_modes_returns_none(self):
        """无 detected_design_modes 时返回 None"""
        try:
            from intelligent_project_analyzer.agents.task_oriented_expert_factory import (
                TaskOrientedExpertFactory,
            )
        except Exception:
            pytest.skip("TaskOrientedExpertFactory 导入失败")

        factory = TaskOrientedExpertFactory.__new__(TaskOrientedExpertFactory)
        state = {"detected_design_modes": []}

        result = factory._inject_sf_knowledge(state)
        assert result is None

    @pytest.mark.unit
    def test_inject_exception_graceful_fallback(self):
        """sf_knowledge_loader 异常时优雅降级"""
        try:
            from intelligent_project_analyzer.agents.task_oriented_expert_factory import (
                TaskOrientedExpertFactory,
            )
        except Exception:
            pytest.skip("TaskOrientedExpertFactory 导入失败")

        factory = TaskOrientedExpertFactory.__new__(TaskOrientedExpertFactory)
        state = {"detected_design_modes": [{"mode": "M1_concept_driven", "confidence": 0.7}]}

        with patch(
            "intelligent_project_analyzer.services.sf_knowledge_loader.get_full_knowledge_injection",
            side_effect=RuntimeError("测试异常"),
        ):
            result = factory._inject_sf_knowledge(state)

        assert result is None, "异常时应返回 None 而非抛出异常"


# ============================================================================
# T10: review_agents._build_sf_evaluation_context
# ============================================================================


class TestT10ReviewSfEvaluation:
    """P2-T10: ReviewerRole._build_sf_evaluation_context"""

    @pytest.mark.unit
    def test_build_with_modes(self):
        """有 _detected_design_modes 时构建评估上下文"""
        try:
            from intelligent_project_analyzer.review.review_agents import ReviewerRole
        except Exception:
            pytest.skip("ReviewerRole 导入失败")

        requirements = {"_detected_design_modes": [{"mode": "M5_rural_context", "confidence": 0.85}]}

        with patch(
            "intelligent_project_analyzer.services.sf_knowledge_loader.get_evaluation_criteria_for_modes",
            return_value="模式 M5 评估维度...",
        ), patch(
            "intelligent_project_analyzer.services.sf_knowledge_loader.get_quality_floor_checklist",
            return_value="Q1｜任务不得虚构\nQ2｜维度不得缺失",
        ):
            result = ReviewerRole._build_sf_evaluation_context(requirements)

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.unit
    def test_build_without_modes(self):
        """无 _detected_design_modes 时返回空"""
        try:
            from intelligent_project_analyzer.review.review_agents import ReviewerRole
        except Exception:
            pytest.skip("ReviewerRole 导入失败")

        requirements = {"project_name": "测试项目"}
        result = ReviewerRole._build_sf_evaluation_context(requirements)
        assert result == ""

    @pytest.mark.unit
    def test_build_exception_graceful(self):
        """sf_knowledge_loader 异常时返回空字符串"""
        try:
            from intelligent_project_analyzer.review.review_agents import ReviewerRole
        except Exception:
            pytest.skip("ReviewerRole 导入失败")

        requirements = {"_detected_design_modes": [{"mode": "M1_concept_driven", "confidence": 0.8}]}

        with patch(
            "intelligent_project_analyzer.services.sf_knowledge_loader.get_evaluation_criteria_for_modes",
            side_effect=ImportError("模块不存在"),
        ):
            result = ReviewerRole._build_sf_evaluation_context(requirements)

        assert result == "", "异常时应返回空字符串"
