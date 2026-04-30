"""
分析模式配置管理器单元测试

Author: Claude Code
Created: 2026-01-03
Version: v1.0
"""

import pytest

from intelligent_project_analyzer.utils.mode_config import (
    AnalysisModeConfigError,
    get_all_modes,
    get_concept_image_config,
    is_mode_editable,
    validate_concept_image_count,
)


class TestGetConceptImageConfig:
    """测试 get_concept_image_config 函数"""

    def test_normal_mode(self):
        """测试普通模式配置"""
        config = get_concept_image_config("normal")

        assert config["count"] == 1
        assert config["editable"] is False
        assert config["max_count"] == 1
        assert config["min_count"] == 1
        assert "mode_name" in config
        assert "mode_description" in config

    def test_deep_thinking_mode(self):
        """测试深度思考模式配置"""
        config = get_concept_image_config("deep_thinking")

        assert config["count"] == 3
        assert config["editable"] is True
        assert config["max_count"] == 10
        assert config["min_count"] == 1
        assert "mode_name" in config

    def test_invalid_mode_with_fallback(self):
        """测试非法模式值（启用降级）"""
        config = get_concept_image_config("invalid_mode", fallback_to_default=True)

        # 应降级到默认模式 (normal)
        assert config["count"] == 1
        assert config["editable"] is False

    def test_invalid_mode_without_fallback(self):
        """测试非法模式值（禁用降级）"""
        with pytest.raises(AnalysisModeConfigError) as exc_info:
            get_concept_image_config("invalid_mode", fallback_to_default=False)

        assert "不支持的分析模式" in str(exc_info.value)


class TestValidateConceptImageCount:
    """测试 validate_concept_image_count 函数"""

    def test_valid_count_normal_mode(self):
        """测试普通模式的有效数量"""
        result = validate_concept_image_count(1, "normal")
        assert result == 1

    def test_valid_count_deep_thinking_mode(self):
        """测试深度思考模式的有效数量"""
        result = validate_concept_image_count(5, "deep_thinking")
        assert result == 5

    def test_count_below_minimum(self):
        """测试低于最小值的数量"""
        result = validate_concept_image_count(0, "deep_thinking")
        assert result == 1  # 调整为 min_count

    def test_count_above_maximum(self):
        """测试超过最大值的数量"""
        result = validate_concept_image_count(15, "deep_thinking")
        assert result == 10  # 调整为 max_count

    def test_count_at_boundary(self):
        """测试边界值"""
        # 最小边界
        assert validate_concept_image_count(1, "deep_thinking") == 1

        # 最大边界
        assert validate_concept_image_count(10, "deep_thinking") == 10


class TestGetAllModes:
    """测试 get_all_modes 函数"""

    def test_returns_dict(self):
        """测试返回字典"""
        modes = get_all_modes()
        assert isinstance(modes, dict)

    def test_contains_required_modes(self):
        """测试包含必需的模式"""
        modes = get_all_modes()
        assert "normal" in modes
        assert "deep_thinking" in modes

    def test_mode_structure(self):
        """测试模式结构完整性"""
        modes = get_all_modes()

        for mode_name, mode_config in modes.items():
            assert "concept_image" in mode_config
            assert "name" in mode_config
            assert "description" in mode_config

            concept_config = mode_config["concept_image"]
            assert "count" in concept_config
            assert "editable" in concept_config
            assert "max_count" in concept_config


class TestIsModeEditable:
    """测试 is_mode_editable 函数"""

    def test_normal_mode_not_editable(self):
        """测试普通模式不可编辑"""
        assert is_mode_editable("normal") is False

    def test_deep_thinking_mode_editable(self):
        """测试深度思考模式可编辑"""
        assert is_mode_editable("deep_thinking") is True

    def test_invalid_mode_defaults_to_false(self):
        """测试非法模式默认不可编辑"""
        # 由于 get_concept_image_config 会降级到默认模式
        result = is_mode_editable("invalid_mode")
        assert result is False  # 降级到 normal 模式


class TestConfigIntegration:
    """集成测试：验证配置的一致性"""

    def test_normal_mode_consistency(self):
        """测试普通模式配置一致性"""
        config = get_concept_image_config("normal")

        # 不可编辑的模式，count 应等于 max_count
        assert config["count"] == config["max_count"]
        assert config["editable"] is False

    def test_deep_thinking_mode_flexibility(self):
        """测试深度思考模式灵活性"""
        config = get_concept_image_config("deep_thinking")

        # 可编辑的模式，count 应小于 max_count
        assert config["count"] < config["max_count"]
        assert config["editable"] is True

    def test_validation_respects_mode_limits(self):
        """测试验证函数遵守模式限制"""
        # 普通模式
        assert validate_concept_image_count(100, "normal") == 1

        # 深度思考模式
        assert validate_concept_image_count(100, "deep_thinking") == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
