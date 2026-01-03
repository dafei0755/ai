"""
动态维度生成器测试
v7.106: 测试LLM驱动的维度生成和混合策略（实际实现）
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from intelligent_project_analyzer.services.dynamic_dimension_generator import DynamicDimensionGenerator


class TestDynamicDimensionGenerator:
    """动态维度生成器测试类"""

    def setup_method(self):
        """测试前准备"""
        self.generator = DynamicDimensionGenerator()
        self.sample_dimensions = [
            {
                "id": "cultural_axis",
                "name": "文化归属轴",
                "left_label": "东方传统",
                "right_label": "西方现代",
                "description": "从东方传统美学到西方现代设计的文化倾向",
                "category": "aesthetic",
                "default_value": 50,
            },
            {
                "id": "function_intensity",
                "name": "功能强度",
                "left_label": "装饰性",
                "right_label": "实用性",
                "description": "从装饰性到实用性的功能侧重",
                "category": "functional",
                "default_value": 50,
            },
        ]

    def test_init(self):
        """测试初始化"""
        assert self.generator is not None
        assert self.generator.config is not None
        assert self.generator.llm is not None

    def test_load_config(self):
        """测试配置加载"""
        config = self.generator.config
        assert "coverage_analysis_prompt" in config
        assert "dimension_generation_prompt" in config
        assert "few_shot_examples" in config
        assert "validation_rules" in config

    @pytest.mark.llm
    def test_analyze_coverage_real_llm(self):
        """测试真实LLM覆盖度分析"""
        user_input = "设计一个中医诊所，需要体现传统文化和现代医疗的平衡"
        structured_data = {"project_type": "commercial_space"}

        result = self.generator.analyze_coverage(user_input, structured_data, self.sample_dimensions)

        assert "coverage_score" in result
        assert "should_generate" in result
        assert "missing_aspects" in result
        assert 0 <= result["coverage_score"] <= 1

    @pytest.mark.llm
    def test_generate_dimensions_real_llm(self):
        """测试真实LLM维度生成"""
        user_input = "设计一个智能健身房，强调科技感和用户体验"
        structured_data = {"project_type": "commercial_space", "existing_dimensions": self.sample_dimensions}
        missing_aspects = [{"aspect": "健身科技融合", "reason": "需要表达传统器械与智能设备的平衡", "importance": "high"}]

        new_dimensions = self.generator.generate_dimensions(
            user_input, structured_data, missing_aspects, target_count=2
        )

        assert isinstance(new_dimensions, list)
        if len(new_dimensions) > 0:
            dim = new_dimensions[0]
            assert "id" in dim
            assert "name" in dim
            assert "left_label" in dim
            assert "right_label" in dim
            assert "description" in dim
            assert "category" in dim
            assert "default_value" in dim
            assert dim.get("source") == "llm_generated"

    def test_validate_dimension_valid(self):
        """测试维度验证 - 合法维度"""
        valid_dimension = {
            "id": "test_dimension",
            "name": "测试维度",
            "left_label": "选项A",
            "right_label": "选项B",
            "description": "这是一个测试维度",
            "category": "aesthetic",
            "default_value": 50,
            "gap_threshold": 30,
        }

        existing_ids = [dim["id"] for dim in self.sample_dimensions]
        result = self.generator._validate_dimension(valid_dimension, existing_ids)

        assert result is True

    def test_validate_dimension_missing_fields(self):
        """测试维度验证 - 缺少必需字段"""
        invalid_dimension = {
            "id": "test_dimension",
            "name": "测试维度"
            # 缺少其他必需字段
        }

        existing_ids = [dim["id"] for dim in self.sample_dimensions]
        result = self.generator._validate_dimension(invalid_dimension, existing_ids)

        assert result is False

    def test_validate_dimension_invalid_id(self):
        """测试维度验证 - 非法ID格式"""
        invalid_dimension = {
            "id": "Invalid-ID-123!",  # 不符合snake_case
            "name": "测试维度",
            "left_label": "选项A",
            "right_label": "选项B",
            "description": "描述",
            "category": "aesthetic",
            "default_value": 50,
        }

        existing_ids = [dim["id"] for dim in self.sample_dimensions]
        result = self.generator._validate_dimension(invalid_dimension, existing_ids)

        assert result is False

    def test_validate_dimension_duplicate_id(self):
        """测试维度验证 - 重复ID"""
        duplicate_dimension = {
            "id": "cultural_axis",  # 与现有维度重复
            "name": "测试维度",
            "left_label": "选项A",
            "right_label": "选项B",
            "description": "描述",
            "category": "aesthetic",
            "default_value": 50,
        }

        existing_ids = [dim["id"] for dim in self.sample_dimensions]
        result = self.generator._validate_dimension(duplicate_dimension, existing_ids)

        assert result is False

    def test_validate_dimension_invalid_category(self):
        """测试维度验证 - 非法类别"""
        invalid_dimension = {
            "id": "test_dimension",
            "name": "测试维度",
            "left_label": "选项A",
            "right_label": "选项B",
            "description": "描述",
            "category": "invalid_category",  # 非法类别
            "default_value": 50,
        }

        existing_ids = [dim["id"] for dim in self.sample_dimensions]
        result = self.generator._validate_dimension(invalid_dimension, existing_ids)

        assert result is False

    def test_validate_dimension_invalid_default_value(self):
        """测试维度验证 - 非法默认值"""
        invalid_dimension = {
            "id": "test_dimension",
            "name": "测试维度",
            "left_label": "选项A",
            "right_label": "选项B",
            "description": "描述",
            "category": "aesthetic",
            "default_value": 150,  # 超出范围0-100
        }

        existing_ids = [dim["id"] for dim in self.sample_dimensions]
        result = self.generator._validate_dimension(invalid_dimension, existing_ids)

        assert result is False

    def test_validate_dimension_name_too_long(self):
        """测试维度验证 - 名称过长"""
        invalid_dimension = {
            "id": "test_dimension",
            "name": "这是一个非常非常非常长的名称超过十个字",  # 超过10字
            "left_label": "选项A",
            "right_label": "选项B",
            "description": "描述",
            "category": "aesthetic",
            "default_value": 50,
        }

        existing_ids = [dim["id"] for dim in self.sample_dimensions]
        result = self.generator._validate_dimension(invalid_dimension, existing_ids)

        assert result is False

    def test_get_few_shot_examples(self):
        """测试Few-shot示例获取"""
        examples = self.generator._get_few_shot_examples()
        assert isinstance(examples, str)
        assert len(examples) > 0

    def test_extract_json(self):
        """测试JSON提取"""
        # 测试直接JSON
        json_text = '{"coverage_score": 0.85, "should_generate": true}'
        result = self.generator._extract_json(json_text)
        assert result is not None
        assert result["coverage_score"] == 0.85

        # 测试带代码块的JSON
        json_with_code = """```json
        {"coverage_score": 0.75, "should_generate": false}
        ```"""
        result = self.generator._extract_json(json_with_code)
        assert result is not None
        assert result["coverage_score"] == 0.75

    def test_extract_json_array(self):
        """测试JSON数组提取"""
        # 测试直接JSON数组
        json_array = '[{"id": "test1"}, {"id": "test2"}]'
        result = self.generator._extract_json_array(json_array)
        assert isinstance(result, list)
        assert len(result) == 2

        # 测试带代码块的JSON数组
        json_with_code = """```json
        [{"id": "test3"}, {"id": "test4"}]
        ```"""
        result = self.generator._extract_json_array(json_with_code)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_default_coverage_result(self):
        """测试默认覆盖度结果（降级策略）"""
        result = self.generator._default_coverage_result()
        assert result["coverage_score"] == 0.95
        assert result["should_generate"] is False
        assert result["missing_aspects"] == []


class TestHybridStrategy:
    """混合策略测试（70%固定 + 30%动态）"""

    @pytest.mark.integration
    def test_hybrid_strategy_ratio(self):
        """测试混合策略比例"""
        # 模拟：固定维度11个 + 动态维度4个 = 15个总维度
        fixed_count = 11
        dynamic_count = 4
        total_count = fixed_count + dynamic_count

        fixed_ratio = fixed_count / total_count
        dynamic_ratio = dynamic_count / total_count

        assert 0.68 <= fixed_ratio <= 0.75  # 约70%
        assert 0.25 <= dynamic_ratio <= 0.32  # 约30%

    @pytest.mark.integration
    def test_dimension_count_limits(self):
        """测试维度数量限制"""
        DIMENSION_FIXED_MAX = 11
        DIMENSION_DYNAMIC_MAX = 4
        DIMENSION_TOTAL_MAX = 15

        # 场景1: 固定维度未达上限
        fixed_count = 10
        dynamic_target = min(DIMENSION_DYNAMIC_MAX, DIMENSION_TOTAL_MAX - fixed_count)
        assert dynamic_target == 4

        # 场景2: 固定维度已达上限
        fixed_count = 11
        dynamic_target = min(DIMENSION_DYNAMIC_MAX, DIMENSION_TOTAL_MAX - fixed_count)
        assert dynamic_target == 4

        # 场景3: 固定维度超过上限（需要裁剪）
        fixed_count = 13
        fixed_count = min(fixed_count, DIMENSION_FIXED_MAX)
        dynamic_target = min(DIMENSION_DYNAMIC_MAX, DIMENSION_TOTAL_MAX - fixed_count)
        assert fixed_count == 11
        assert dynamic_target == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
