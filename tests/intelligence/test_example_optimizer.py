"""
测试示例优化器模块
测试LLM驱动的Few-Shot示例优化功能

作者: Intelligence Evolution System
创建时间: 2026-02-11
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from intelligent_project_analyzer.intelligence.example_optimizer import (
    ExampleOptimizer,
    OptimizationConfig,
    OptimizationResult,
)
from intelligent_project_analyzer.utils.few_shot_loader import FewShotExample


@pytest.fixture
def optimizer():
    """创建优化器实例"""
    config = OptimizationConfig(model="gpt-4", temperature=0.3, min_feedback_count=2)  # 降低阈值便于测试
    return ExampleOptimizer(config=config)


@pytest.fixture
def sample_example():
    """示例对象"""
    return FewShotExample(
        example_id="test_001",
        description="测试示例",
        user_request="帮我分析需求",
        correct_output="这是原始输出内容",
        category="analysis",
        difficulty_level=3,
        context={},
    )


@pytest.fixture
def sample_feedback():
    """用户反馈数据"""
    return [
        {"timestamp": datetime.now().isoformat(), "rating": 2, "comment": "输出太简单，缺少深度分析", "example_id": "test_001"},
        {"timestamp": datetime.now().isoformat(), "rating": 3, "comment": "格式不够清晰", "example_id": "test_001"},
        {"timestamp": datetime.now().isoformat(), "rating": 2, "comment": "没有给出具体建议", "example_id": "test_001"},
    ]


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API响应"""
    return {
        "id": "chatcmpl-test123",
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "example_id": "test_001",
                            "description": "改进后的测试示例",
                            "user_request": "帮我分析需求",
                            "correct_output": "这是优化后的输出内容，包含更详细的分析和具体建议...",
                            "category": "analysis",
                            "difficulty_level": 3,
                        }
                    )
                }
            }
        ],
        "usage": {"prompt_tokens": 500, "completion_tokens": 300},
    }


class TestOptimizationConfig:
    """测试优化配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = OptimizationConfig()
        assert config.model == "gpt-4"
        assert config.temperature == 0.3
        assert config.min_feedback_count == 3
        assert config.max_retries == 3

    def test_custom_config(self):
        """测试自定义配置"""
        config = OptimizationConfig(model="gpt-3.5-turbo", temperature=0.5, min_feedback_count=5)
        assert config.model == "gpt-3.5-turbo"
        assert config.temperature == 0.5
        assert config.min_feedback_count == 5


class TestFeedbackSummarization:
    """测试反馈摘要功能"""

    def test_summarize_feedback(self, optimizer, sample_feedback):
        """测试反馈摘要生成"""
        summary = optimizer._summarize_feedback(sample_feedback)

        assert "total_count" in summary
        assert summary["total_count"] == 3

        assert "avg_rating" in summary
        assert summary["avg_rating"] == pytest.approx(2.33, 0.1)

        assert "positive_count" in summary
        assert "negative_count" in summary
        assert summary["negative_count"] == 3  # 所有评分 < 3.5

        assert "common_complaints" in summary
        assert len(summary["common_complaints"]) > 0

    def test_empty_feedback(self, optimizer):
        """测试空反馈列表"""
        summary = optimizer._summarize_feedback([])
        assert summary["total_count"] == 0
        assert summary["avg_rating"] == 0
        assert len(summary["common_complaints"]) == 0


class TestOptimizationPromptBuild:
    """测试优化提示构建"""

    def test_build_optimization_prompt(self, optimizer, sample_example, sample_feedback):
        """测试优化提示生成"""
        summary = optimizer._summarize_feedback(sample_feedback)
        prompt = optimizer._build_optimization_prompt(sample_example, summary, "V7_0")

        # 验证提示内容
        assert "V7_0" in prompt
        assert "test_001" in prompt
        assert "原始输出内容" in prompt
        assert str(summary["avg_rating"]) in prompt
        assert "改进建议" in prompt or "优化目标" in prompt


class TestExampleOptimization:
    """测试示例优化功能"""

    @patch("intelligent_project_analyzer.intelligence.example_optimizer.OpenAI")
    def test_optimize_example_success(
        self, mock_openai_class, optimizer, sample_example, sample_feedback, mock_openai_response
    ):
        """测试成功优化示例"""
        # Mock OpenAI客户端
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock chat completion响应
        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = mock_openai_response["choices"][0]["message"]["content"]
        mock_completion.usage.prompt_tokens = 500
        mock_completion.usage.completion_tokens = 300
        mock_client.chat.completions.create.return_value = mock_completion

        # 重新创建optimizer以使用mock
        optimizer.client = mock_client

        # 执行优化
        result = optimizer.optimize_example(sample_example, sample_feedback, "V7_0")

        # 验证结果
        assert isinstance(result, OptimizationResult)
        assert result.success is True
        assert result.optimized_example is not None
        assert len(result.changes_made) > 0
        assert result.token_cost["total"] == 800

    def test_optimize_example_insufficient_feedback(self, optimizer, sample_example):
        """测试反馈不足时的处理"""
        # 只提供1条反馈（少于min_feedback_count=2）
        insufficient_feedback = [{"timestamp": datetime.now().isoformat(), "rating": 2, "comment": "不好"}]

        result = optimizer.optimize_example(sample_example, insufficient_feedback, "V7_0")

        assert result.success is False
        assert "反馈数量不足" in result.error_message

    @patch("intelligent_project_analyzer.intelligence.example_optimizer.OpenAI")
    def test_optimize_example_llm_failure(self, mock_openai_class, optimizer, sample_example, sample_feedback):
        """测试LLM调用失败情况"""
        # Mock异常
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        optimizer.client = mock_client

        result = optimizer.optimize_example(sample_example, sample_feedback, "V7_0")

        assert result.success is False
        assert "API Error" in result.error_message


class TestChangeIdentification:
    """测试变更识别"""

    def test_identify_changes(self, optimizer, sample_example):
        """测试变更检测"""
        # 创建修改后的示例
        optimized = FewShotExample(
            example_id="test_001",
            description="改进后的测试示例",  # 修改了
            user_request="帮我分析需求",  # 未修改
            correct_output="完全不同的输出内容，包含更多细节和分析",  # 修改了
            category="analysis",
            difficulty_level=3,
            context={},
        )

        changes = optimizer._identify_changes(sample_example, optimized)

        assert len(changes) > 0
        assert any(c["field"] == "description" for c in changes)
        assert any(c["field"] == "correct_output" for c in changes)
        assert not any(c["field"] == "user_request" for c in changes)


class TestBatchOptimization:
    """测试批量优化"""

    @patch("intelligent_project_analyzer.intelligence.example_optimizer.ExampleQualityAnalyzer")
    @patch("intelligent_project_analyzer.intelligence.example_optimizer.OpenAI")
    def test_batch_optimize(self, mock_openai_class, mock_analyzer_class, optimizer):
        """测试批量优化流程"""
        # Mock质量分析报告
        mock_analyzer = MagicMock()
        mock_report = MagicMock()
        mock_report.low_quality_examples = [
            {"id": "ex1", "quality_score": 0.2},
            {"id": "ex2", "quality_score": 0.25},
            {"id": "ex3", "quality_score": 0.4},  # 这个会被过滤（>0.3）
        ]
        mock_analyzer.analyze_role.return_value = mock_report
        mock_analyzer_class.return_value = mock_analyzer

        # Mock FewShotExampleLoader
        with patch(
            "intelligent_project_analyzer.intelligence.example_optimizer.FewShotExampleLoader"
        ) as mock_loader_class:
            mock_loader = MagicMock()
            mock_loader.load_examples.return_value = [
                FewShotExample("ex1", "desc1", "req1", "out1", "cat1", 3, {}),
                FewShotExample("ex2", "desc2", "req2", "out2", "cat2", 3, {}),
            ]
            mock_loader_class.return_value = mock_loader

            # Mock UsageTracker获取反馈
            optimizer.tracker.get_example_feedback = MagicMock(
                return_value=[{"rating": 2, "comment": "不好", "timestamp": datetime.now().isoformat()} for _ in range(3)]
            )

            # Mock OpenAI
            mock_client = MagicMock()
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = json.dumps(
                {
                    "example_id": "ex1",
                    "description": "optimized",
                    "user_request": "req",
                    "correct_output": "optimized output",
                    "category": "cat",
                    "difficulty_level": 3,
                }
            )
            mock_completion.usage.prompt_tokens = 100
            mock_completion.usage.completion_tokens = 50
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai_class.return_value = mock_client
            optimizer.client = mock_client

            # 执行批量优化
            results = optimizer.batch_optimize("V7_0", quality_threshold=0.3, days=7)

            # 验证：应该只优化2个（quality_score < 0.3的）
            assert len(results) == 2
            assert all(isinstance(r, OptimizationResult) for r in results)


class TestSaveOptimizedExamples:
    """测试保存优化后的示例"""

    @patch("builtins.open", create=True)
    @patch("os.path.exists", return_value=True)
    @patch("json.load")
    @patch("json.dump")
    def test_save_with_backup(self, mock_json_dump, mock_json_load, mock_exists, mock_open, optimizer):
        """测试带备份的保存"""
        # Mock现有文件内容
        mock_json_load.return_value = [{"example_id": "test_001", "description": "old"}]

        optimized_examples = [FewShotExample("test_001", "new desc", "req", "out", "cat", 3, {})]

        optimizer.save_optimized_examples("V7_0", optimized_examples)

        # 验证调用了dump（保存原始+优化版本）
        assert mock_json_dump.call_count >= 1


class TestIntegration:
    """集成测试"""

    @patch("intelligent_project_analyzer.intelligence.example_optimizer.OpenAI")
    @patch("intelligent_project_analyzer.intelligence.example_optimizer.UsageTracker")
    def test_end_to_end_optimization(self, mock_tracker_class, mock_openai_class):
        """端到端优化流程测试"""
        # 设置完整的mock链
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_completion = MagicMock()
        mock_completion.choices = [MagicMock()]
        mock_completion.choices[0].message.content = json.dumps(
            {
                "example_id": "int_test_001",
                "description": "Optimized integration test",
                "user_request": "Test request",
                "correct_output": "Enhanced output with more details",
                "category": "test",
                "difficulty_level": 3,
            }
        )
        mock_completion.usage.prompt_tokens = 200
        mock_completion.usage.completion_tokens = 100
        mock_client.chat.completions.create.return_value = mock_completion

        # 创建优化器并执行
        config = OptimizationConfig(min_feedback_count=2)
        optimizer = ExampleOptimizer(config=config, usage_tracker=mock_tracker)
        optimizer.client = mock_client

        example = FewShotExample("int_test_001", "Original", "Test request", "Basic output", "test", 3, {})

        feedback = [
            {"rating": 2, "comment": "Too basic", "timestamp": datetime.now().isoformat()},
            {"rating": 3, "comment": "Needs more", "timestamp": datetime.now().isoformat()},
        ]

        result = optimizer.optimize_example(example, feedback, "V7_0")

        # 验证完整流程
        assert result.success is True
        assert result.optimized_example.correct_output != example.correct_output
        assert result.token_cost["total"] == 300


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
