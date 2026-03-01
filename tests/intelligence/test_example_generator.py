"""
测试示例生成器模块
测试LLM驱动的Few-Shot示例自动生成功能

作者: Intelligence Evolution System
创建时间: 2026-02-11
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from intelligent_project_analyzer.intelligence.example_generator import (
    ExampleGenerator,
    GeneratorConfig,
    GenerationResult,
)
from intelligent_project_analyzer.utils.few_shot_loader import FewShotExample


@pytest.fixture
def generator():
    """创建生成器实例"""
    config = GeneratorConfig(model="gpt-4", temperature=0.7, min_length=5000, max_length=8000)
    return ExampleGenerator(config=config)


@pytest.fixture
def reference_examples():
    """参考示例列表"""
    return [
        FewShotExample(
            example_id="ref_001",
            description="参考示例1",
            user_request="用户需求示例",
            correct_output="这是一个参考输出，长度至少5000字符..." + "内容" * 2000,
            category="analysis",
            difficulty_level=3,
            context={},
        ),
        FewShotExample(
            example_id="ref_002",
            description="参考示例2",
            user_request="另一个需求示例",
            correct_output="另一个参考输出格式..." + "详细内容" * 1500,
            category="analysis",
            difficulty_level=4,
            context={},
        ),
    ]


@pytest.fixture
def mock_openai_generation_response():
    """Mock OpenAI生成响应"""
    return {
        "id": "chatcmpl-gen123",
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "example_id": "generated_001",
                            "description": "自动生成的示例描述",
                            "user_request": "这是生成的用户需求",
                            "correct_output": "这是生成的输出内容，包含详细分析和建议..." + "详细内容" * 1800,
                            "category": "business_analysis",
                            "difficulty_level": 4,
                        }
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 800, "completion_tokens": 600},
    }


class TestGeneratorConfig:
    """测试生成器配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = GeneratorConfig()
        assert config.model == "gpt-4"
        assert config.temperature == 0.7  # 生成比优化需要更高温度
        assert config.min_length == 5000
        assert config.max_length == 8000
        assert config.max_retries == 3

    def test_custom_config(self):
        """测试自定义配置"""
        config = GeneratorConfig(model="gpt-3.5-turbo", temperature=0.9, min_length=3000, max_length=6000)
        assert config.model == "gpt-3.5-turbo"
        assert config.temperature == 0.9
        assert config.min_length == 3000


class TestGenerationPromptBuild:
    """测试生成提示构建"""

    @patch("intelligent_project_analyzer.intelligence.example_generator.RoleManager")
    def test_build_generation_prompt(self, mock_role_manager_class, generator, reference_examples):
        """测试生成提示构建"""
        # Mock RoleManager
        mock_role_manager = MagicMock()
        mock_role_config = {"role_name": "Requirements Analyst", "identity": "需求分析专家", "expertise": ["需求分析", "业务理解"]}
        mock_role_manager.get_role_config.return_value = mock_role_config
        mock_role_manager_class.return_value = mock_role_manager

        # 重新创建generator使用mock
        generator.role_manager = mock_role_manager

        scenario_desc = "用户提供模糊的业务需求，需要深入挖掘真实意图"
        prompt = generator._build_generation_prompt(
            role_id="V7_0",
            scenario_description=scenario_desc,
            reference_examples=reference_examples,
            category="business_analysis",
        )

        # 验证提示内容
        assert "V7_0" in prompt or "Requirements Analyst" in prompt
        assert scenario_desc in prompt
        assert "business_analysis" in prompt
        assert "参考示例" in prompt or "reference" in prompt.lower()


class TestValidation:
    """测试生成结果验证"""

    def test_validate_valid_example(self, generator):
        """测试有效示例验证"""
        valid_data = {
            "example_id": "gen_001",
            "description": "有效的描述",
            "user_request": "用户需求",
            "correct_output": "输出内容" * 1000,  # 至少5000字符
            "category": "test",
            "difficulty_level": 3,
        }

        result = generator._validate_generated_example(valid_data)
        assert result["valid"] is True
        assert result["reason"] == ""

    def test_validate_missing_fields(self, generator):
        """测试缺少必需字段"""
        invalid_data = {
            "example_id": "gen_002",
            "description": "描述",
            # 缺少 user_request
            "correct_output": "输出" * 1000,
            "category": "test",
        }

        result = generator._validate_generated_example(invalid_data)
        assert result["valid"] is False
        assert "缺少必需字段" in result["reason"]

    def test_validate_output_too_short(self, generator):
        """测试输出过短"""
        short_output_data = {
            "example_id": "gen_003",
            "description": "描述",
            "user_request": "需求",
            "correct_output": "太短了",  # 远少于5000字符
            "category": "test",
            "difficulty_level": 3,
        }

        result = generator._validate_generated_example(short_output_data)
        assert result["valid"] is False
        assert "输出长度不足" in result["reason"]

    def test_validate_output_too_long(self, generator):
        """测试输出过长"""
        config = GeneratorConfig(max_length=100)
        gen = ExampleGenerator(config=config)

        long_output_data = {
            "example_id": "gen_004",
            "description": "描述",
            "user_request": "需求",
            "correct_output": "很长的内容" * 50,  # 超过100字符
            "category": "test",
            "difficulty_level": 3,
        }

        result = gen._validate_generated_example(long_output_data)
        assert result["valid"] is False
        assert "输出长度过长" in result["reason"]

    def test_validate_empty_content(self, generator):
        """测试空内容"""
        empty_data = {
            "example_id": "gen_005",
            "description": "描述",
            "user_request": "",  # 空请求
            "correct_output": "输出" * 1000,
            "category": "test",
            "difficulty_level": 3,
        }

        result = generator._validate_generated_example(empty_data)
        assert result["valid"] is False
        assert "不能为空" in result["reason"]


class TestExampleGeneration:
    """测试示例生成功能"""

    @patch("intelligent_project_analyzer.intelligence.example_generator.RoleManager")
    @patch("intelligent_project_analyzer.intelligence.example_generator.OpenAI")
    def test_generate_example_success(
        self, mock_openai_class, mock_role_manager_class, generator, reference_examples, mock_openai_generation_response
    ):
        """测试成功生成示例"""
        # Mock RoleManager
        mock_role_manager = MagicMock()
        mock_role_manager.get_role_config.return_value = {
            "role_name": "Test Role",
            "identity": "Test Identity",
            "expertise": ["test"],
        }
        mock_role_manager_class.return_value = mock_role_manager
        generator.role_manager = mock_role_manager

        # Mock OpenAI
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = mock_openai_generation_response["choices"][0]["message"]["content"]
        mock_completion.usage.prompt_tokens = 800
        mock_completion.usage.completion_tokens = 600
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        generator.client = mock_client

        # 执行生成
        result = generator.generate_example(
            role_id="V7_0",
            scenario_description="测试场景：用户提供模糊需求",
            reference_examples=reference_examples,
            category="business_analysis",
        )

        # 验证结果
        assert isinstance(result, GenerationResult)
        assert result.success is True
        assert result.generated_example is not None
        assert result.generated_example.example_id == "generated_001"
        assert result.token_cost["total"] == 1400
        assert result.validation_passed is True

    @patch("intelligent_project_analyzer.intelligence.example_generator.RoleManager")
    @patch("intelligent_project_analyzer.intelligence.example_generator.OpenAI")
    def test_generate_example_validation_failure(self, mock_openai_class, mock_role_manager_class, generator):
        """测试生成但验证失败"""
        # Mock RoleManager
        mock_role_manager = MagicMock()
        mock_role_manager.get_role_config.return_value = {"role_name": "Test", "identity": "Test", "expertise": []}
        mock_role_manager_class.return_value = mock_role_manager
        generator.role_manager = mock_role_manager

        # Mock OpenAI返回无效数据（输出过短）
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        invalid_response = json.dumps(
            {
                "example_id": "gen_invalid",
                "description": "desc",
                "user_request": "req",
                "correct_output": "too short",  # 验证失败
                "category": "test",
                "difficulty_level": 3,
            }
        )
        mock_completion.choices[0].message.content = invalid_response
        mock_completion.usage.prompt_tokens = 100
        mock_completion.usage.completion_tokens = 50
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        generator.client = mock_client

        result = generator.generate_example(
            role_id="V7_0", scenario_description="test", reference_examples=[], category="test"
        )

        assert result.success is False
        assert "输出长度不足" in result.error_message

    @patch("intelligent_project_analyzer.intelligence.example_generator.RoleManager")
    @patch("intelligent_project_analyzer.intelligence.example_generator.OpenAI")
    def test_generate_example_llm_failure(self, mock_openai_class, mock_role_manager_class, generator):
        """测试LLM调用失败"""
        # Mock RoleManager
        mock_role_manager = MagicMock()
        mock_role_manager.get_role_config.return_value = {"role_name": "Test", "identity": "Test", "expertise": []}
        mock_role_manager_class.return_value = mock_role_manager
        generator.role_manager = mock_role_manager

        # Mock异常
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client
        generator.client = mock_client

        result = generator.generate_example(
            role_id="V7_0", scenario_description="test", reference_examples=[], category="test"
        )

        assert result.success is False
        assert "API Error" in result.error_message


class TestScenarioGapIdentification:
    """测试场景缺口识别"""

    def test_identify_scenario_gaps_basic(self, generator):
        """测试基础缺口识别"""
        existing_examples = [
            FewShotExample("ex1", "desc1", "req1", "out1", "cat1", 3, {}),
            FewShotExample("ex2", "desc2", "req2", "out2", "cat2", 3, {}),
        ]

        usage_logs = [
            {
                "role_id": "V7_0",
                "user_query": "复杂的多维度需求",
                "user_feedback": {"rating": 2, "comment": "没有相关示例"},
                "timestamp": datetime.now().isoformat(),
            },
            {
                "role_id": "V7_0",
                "user_query": "跨领域业务分析",
                "user_feedback": {"rating": 2, "comment": "示例不够"},
                "timestamp": datetime.now().isoformat(),
            },
        ]

        gaps = generator.identify_scenario_gaps("V7_0", existing_examples, usage_logs)

        # 验证返回格式
        assert isinstance(gaps, list)
        assert len(gaps) > 0
        for gap in gaps:
            assert "scenario" in gap
            assert "frequency" in gap
            assert "sample_requests" in gap

    def test_identify_scenario_gaps_empty_logs(self, generator):
        """测试空日志情况"""
        existing_examples = [FewShotExample("ex1", "desc1", "req1", "out1", "cat1", 3, {})]

        gaps = generator.identify_scenario_gaps("V7_0", existing_examples, [])

        # 空日志应该返回空缺口列表
        assert isinstance(gaps, list)
        assert len(gaps) == 0


class TestBatchGeneration:
    """测试批量生成"""

    @patch("intelligent_project_analyzer.intelligence.example_generator.RoleManager")
    @patch("intelligent_project_analyzer.intelligence.example_generator.OpenAI")
    def test_batch_generate(self, mock_openai_class, mock_role_manager_class, generator):
        """测试批量生成功能"""
        # Mock RoleManager
        mock_role_manager = MagicMock()
        mock_role_manager.get_role_config.return_value = {"role_name": "Test", "identity": "Test", "expertise": []}
        mock_role_manager_class.return_value = mock_role_manager
        generator.role_manager = mock_role_manager

        # Mock OpenAI
        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(
            {
                "example_id": "batch_gen_001",
                "description": "Batch generated",
                "user_request": "Batch request",
                "correct_output": "批量生成的内容" * 1000,
                "category": "test",
                "difficulty_level": 3,
            }
        )
        mock_completion.usage.prompt_tokens = 200
        mock_completion.usage.completion_tokens = 150
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client
        generator.client = mock_client

        # 准备场景列表
        scenario_gaps = [
            {"scenario": "场景1", "frequency": 0.3, "sample_requests": ["req1"]},
            {"scenario": "场景2", "frequency": 0.2, "sample_requests": ["req2"]},
        ]

        results = generator.batch_generate(
            role_id="V7_0", scenario_gaps=scenario_gaps, reference_examples=[], category="test"
        )

        # 验证结果
        assert len(results) == 2
        assert all(isinstance(r, GenerationResult) for r in results)
        assert all(r.success for r in results)


class TestSaveGeneratedExamples:
    """测试保存生成的示例"""

    @patch("builtins.open", create=True)
    @patch("os.path.exists", return_value=True)
    @patch("json.load")
    @patch("json.dump")
    def test_save_generated_examples(self, mock_json_dump, mock_json_load, mock_exists, mock_open, generator):
        """测试保存生成的示例"""
        # Mock现有文件
        mock_json_load.return_value = [{"example_id": "existing_001", "description": "existing"}]

        generated_examples = [
            FewShotExample("gen_001", "Generated", "Request", "Output" * 1000, "test", 3, {"generated": True})
        ]

        generator.save_generated_examples("V7_0", generated_examples)

        # 验证调用了dump
        assert mock_json_dump.call_count >= 1


class TestIntegration:
    """集成测试"""

    @patch("intelligent_project_analyzer.intelligence.example_generator.RoleManager")
    @patch("intelligent_project_analyzer.intelligence.example_generator.OpenAI")
    def test_end_to_end_generation(self, mock_openai_class, mock_role_manager_class):
        """端到端生成流程测试"""
        # Setup mocks
        mock_role_manager = MagicMock()
        mock_role_manager.get_role_config.return_value = {
            "role_name": "Integration Test Role",
            "identity": "Test Identity",
            "expertise": ["testing", "integration"],
        }
        mock_role_manager_class.return_value = mock_role_manager

        mock_client = MagicMock()
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(
            {
                "example_id": "int_gen_001",
                "description": "Integration test generated example",
                "user_request": "Test user request for integration",
                "correct_output": "集成测试生成的详细输出内容，包含各种分析和建议..." * 500,
                "category": "integration_test",
                "difficulty_level": 4,
            }
        )
        mock_completion.usage.prompt_tokens = 500
        mock_completion.usage.completion_tokens = 400
        mock_client.chat.completions.create.return_value = mock_completion
        mock_openai_class.return_value = mock_client

        # 创建生成器
        config = GeneratorConfig(min_length=5000, max_length=8000)
        generator = ExampleGenerator(config=config)
        generator.client = mock_client
        generator.role_manager = mock_role_manager

        # 执行完整流程
        reference_examples = [FewShotExample("ref_int_001", "Reference", "Ref request", "参考输出" * 1000, "test", 3, {})]

        result = generator.generate_example(
            role_id="V7_0",
            scenario_description="复杂的集成测试场景，需要综合考虑多个因素",
            reference_examples=reference_examples,
            category="integration_test",
        )

        # 验证完整流程
        assert result.success is True
        assert result.generated_example is not None
        assert result.generated_example.context.get("generated") is True
        assert "scenario" in result.generated_example.context
        assert result.token_cost["total"] == 900
        assert result.validation_passed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
