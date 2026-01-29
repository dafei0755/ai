"""
v7.139 Phase 3: 维度关联建模 - 单元测试

测试维度关联检测器的核心功能：
1. 初始化和配置加载
2. 互斥关系检测
3. 正相关关系检测
4. 负相关关系检测
5. 特殊约束检测
6. 调整建议生成
7. 集成测试
"""

import pytest

from intelligent_project_analyzer.services.dimension_correlation_detector import DimensionCorrelationDetector
from intelligent_project_analyzer.services.dimension_selector import DimensionSelector


class TestDimensionCorrelationDetectorInitialization:
    """测试关联检测器的初始化"""

    def test_singleton_pattern(self):
        """测试单例模式"""
        detector1 = DimensionCorrelationDetector()
        detector2 = DimensionCorrelationDetector()
        assert detector1 is detector2

    def test_config_loading(self):
        """测试配置加载"""
        detector = DimensionCorrelationDetector()
        assert detector.config is not None
        assert "mutual_exclusion" in detector.config
        assert "positive_correlation" in detector.config
        assert "negative_correlation" in detector.config


class TestMutualExclusionDetection:
    """测试互斥关系检测"""

    def test_detect_minimalist_vs_decorative(self):
        """测试极简美学vs装饰丰富度冲突"""
        detector = DimensionCorrelationDetector()
        dimensions = [
            {"dimension_id": "minimalist_aesthetic", "default_value": 85},
            {"dimension_id": "decorative_richness", "default_value": 75},
        ]

        conflicts = detector.detect_conflicts(dimensions)
        # minimalist(85) + decorative(75) = 160
        # mutual_exclusion threshold=140, negative_correlation max_sum=130
        # Both can be detected, accept either type
        assert len(conflicts) > 0
        assert any(
            c["conflict_type"] in ["mutual_exclusion", "negative_correlation"]
            and c["dimension_a"] in ["minimalist_aesthetic", "decorative_richness"]
            and c["dimension_b"] in ["minimalist_aesthetic", "decorative_richness"]
            for c in conflicts
        )


class TestPositiveCorrelationDetection:
    """测试正相关关系检测"""

    def test_detect_material_quality_vs_craftsmanship(self):
        """测试材料品质vs工艺水平差距过大"""
        detector = DimensionCorrelationDetector()
        dimensions = [
            {"dimension_id": "material_quality", "default_value": 90},
            {"dimension_id": "craftsmanship_level", "default_value": 40},
        ]

        conflicts = detector.detect_conflicts(dimensions)
        assert len(conflicts) > 0
        assert any(c["conflict_type"] == "positive_correlation" for c in conflicts)


class TestNegativeCorrelationDetection:
    """测试负相关关系检测"""

    def test_detect_budget_vs_material_quality(self):
        """测试预算优先级vs材料品质冲突"""
        detector = DimensionCorrelationDetector()
        dimensions = [
            {"dimension_id": "budget_priority", "default_value": 85},  # Increased to meet confidence threshold
            {"dimension_id": "material_quality", "default_value": 85},  # Increased to meet confidence threshold
        ]

        conflicts = detector.detect_conflicts(dimensions)
        # budget(85) + material(85) = 170 > max_sum(140)
        # confidence = (170-140)/40 = 0.75 >= min_confidence(0.7)
        assert len(conflicts) > 0
        assert any(c["conflict_type"] == "negative_correlation" for c in conflicts)


class TestSpecialConstraintsDetection:
    """测试特殊约束检测"""

    def test_detect_elderly_accessibility_constraint(self):
        """测试适老化→安全性约束"""
        detector = DimensionCorrelationDetector()
        dimensions = [
            {"dimension_id": "accessibility_level", "default_value": 80},
            {"dimension_id": "safety_priority", "default_value": 50},
        ]

        conflicts = detector.detect_conflicts(dimensions)
        assert len(conflicts) > 0
        assert any(c["conflict_type"] == "special_constraint" for c in conflicts)


class TestAdjustmentSuggestions:
    """测试调整建议生成"""

    def test_suggest_adjustments_for_mutual_exclusion(self):
        """测试为互斥冲突生成调整建议"""
        detector = DimensionCorrelationDetector()
        dimensions = [
            {"dimension_id": "minimalist_aesthetic", "default_value": 85},
            {"dimension_id": "decorative_richness", "default_value": 75},
        ]

        conflicts = detector.detect_conflicts(dimensions)
        suggestions = detector.suggest_adjustments(conflicts, dimensions)

        assert len(suggestions) > 0
        assert all("dimension_id" in s for s in suggestions)
        assert all("suggested_value" in s for s in suggestions)


class TestIntegrationWithDimensionSelector:
    """测试与DimensionSelector的集成"""

    def test_select_for_project_returns_correlation_info(self):
        """测试select_for_project返回关联检测信息"""
        selector = DimensionSelector()
        result = selector.select_for_project(
            project_type="personal_residential",
            user_input="极简风格，但希望有丰富的装饰",
        )

        assert isinstance(result, dict)
        assert "dimensions" in result
        assert "conflicts" in result
        assert "adjustment_suggestions" in result

    def test_validate_dimensions_api(self):
        """测试validate_dimensions独立API"""
        selector = DimensionSelector()
        dimensions = [
            {"dimension_id": "minimalist_aesthetic", "default_value": 85},
            {"dimension_id": "decorative_richness", "default_value": 75},
        ]

        result = selector.validate_dimensions(dimensions)

        assert "conflicts" in result
        assert "adjustment_suggestions" in result
        assert "is_valid" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
