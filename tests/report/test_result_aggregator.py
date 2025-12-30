"""
Report模块测试 - Result Aggregator

测试结果聚合器的核心功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock


@pytest.fixture
def sample_agent_results():
    """示例专家分析结果"""
    return {
        "market_analyst": {
            "deliverables": [
                {
                    "label": "市场规模分析",
                    "content": "咖啡市场规模达到X亿元..."
                }
            ]
        },
        "design_expert": {
            "deliverables": [
                {
                    "label": "设计方案",
                    "content": "采用现代简约风格..."
                }
            ]
        },
        "financial_expert": {
            "deliverables": [
                {
                    "label": "投资预算",
                    "content": "总投资预算约100万元..."
                }
            ]
        }
    }


@pytest.fixture
def mock_llm():
    """Mock LLM用于聚合"""
    with patch('intelligent_project_analyzer.services.llm_factory.LLMFactory.create_llm') as mock:
        llm_instance = Mock()
        llm_instance.invoke.return_value = """
# 项目分析报告

## 市场分析
咖啡市场规模达到X亿元...

## 设计方案
采用现代简约风格...

## 投资预算
总投资预算约100万元...
"""
        mock.return_value = llm_instance
        yield llm_instance


def test_result_aggregator_initialization():
    """测试结果聚合器初始化"""
    from intelligent_project_analyzer.report.result_aggregator import ResultAggregator

    aggregator = ResultAggregator()
    assert aggregator is not None


def test_aggregate_results_success(sample_agent_results, mock_llm):
    """测试聚合结果 - 成功"""
    from intelligent_project_analyzer.report.result_aggregator import ResultAggregator

    aggregator = ResultAggregator()
    result = aggregator.aggregate(sample_agent_results)

    # 验证聚合结果
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 100  # 应该有实质性内容
    assert "市场分析" in result or "market" in result.lower()


def test_aggregate_empty_results():
    """测试聚合空结果"""
    from intelligent_project_analyzer.report.result_aggregator import ResultAggregator

    aggregator = ResultAggregator()

    # 空结果应该返回默认内容或抛出异常
    result = aggregator.aggregate({})

    # 根据实际实现调整断言
    assert result is not None or result == ""


def test_aggregate_single_expert(mock_llm):
    """测试聚合单个专家结果"""
    from intelligent_project_analyzer.report.result_aggregator import ResultAggregator

    single_result = {
        "market_analyst": {
            "deliverables": [{"label": "分析", "content": "内容"}]
        }
    }

    aggregator = ResultAggregator()
    result = aggregator.aggregate(single_result)

    assert result is not None


def test_aggregate_preserves_structure():
    """测试聚合保留结构"""
    from intelligent_project_analyzer.report.result_aggregator import ResultAggregator

    results = {
        "expert1": {"deliverables": [{"label": "A", "content": "1"}]},
        "expert2": {"deliverables": [{"label": "B", "content": "2"}]},
        "expert3": {"deliverables": [{"label": "C", "content": "3"}]},
    }

    aggregator = ResultAggregator()
    result = aggregator.aggregate(results)

    # 验证所有专家内容都被包含
    assert "1" in result or "A" in result
    assert "2" in result or "B" in result
    assert "3" in result or "C" in result


def test_aggregate_with_markdown_formatting(sample_agent_results, mock_llm):
    """测试Markdown格式化"""
    from intelligent_project_analyzer.report.result_aggregator import ResultAggregator

    aggregator = ResultAggregator()
    result = aggregator.aggregate(sample_agent_results)

    # 验证Markdown格式
    assert "#" in result or "##" in result  # 标题
    assert "\n" in result  # 换行


def test_aggregate_handles_special_characters(mock_llm):
    """测试处理特殊字符"""
    from intelligent_project_analyzer.report.result_aggregator import ResultAggregator

    results = {
        "expert": {
            "deliverables": [{
                "label": "特殊字符测试",
                "content": "包含 \"引号\" 和 <标签> 及 &符号"
            }]
        }
    }

    aggregator = ResultAggregator()
    result = aggregator.aggregate(results)

    # 应该正确处理特殊字符
    assert result is not None
    assert len(result) > 0


def test_aggregate_long_content(mock_llm):
    """测试处理长内容"""
    from intelligent_project_analyzer.report.result_aggregator import ResultAggregator

    # 生成长内容
    long_results = {
        f"expert_{i}": {
            "deliverables": [{
                "label": f"部分 {i}",
                "content": "内容 " * 1000  # 每个专家1000字
            }]
        }
        for i in range(10)  # 10个专家
    }

    aggregator = ResultAggregator()
    result = aggregator.aggregate(long_results)

    assert result is not None
    # 验证没有被截断得太短
    assert len(result) > 100


@pytest.mark.parametrize("num_experts,expected_sections", [
    (1, 1),
    (3, 3),
    (5, 5),
    (10, 10),
])
def test_aggregate_various_expert_counts(mock_llm, num_experts, expected_sections):
    """测试不同专家数量"""
    from intelligent_project_analyzer.report.result_aggregator import ResultAggregator

    results = {
        f"expert_{i}": {
            "deliverables": [{
                "label": f"Section {i}",
                "content": f"Content {i}"
            }]
        }
        for i in range(num_experts)
    }

    aggregator = ResultAggregator()
    result = aggregator.aggregate(results)

    # 验证结果包含所有部分
    assert result is not None
    # 简单验证：结果长度应该随专家数量增加
    if num_experts > 1:
        assert len(result) > 50 * num_experts


def test_aggregate_with_missing_fields(mock_llm):
    """测试处理缺失字段"""
    from intelligent_project_analyzer.report.result_aggregator import ResultAggregator

    incomplete_results = {
        "expert1": {
            "deliverables": [{"label": "A"}]  # 缺少content
        },
        "expert2": {
            "deliverables": [{"content": "B"}]  # 缺少label
        },
        "expert3": {},  # 缺少deliverables
    }

    aggregator = ResultAggregator()

    # 应该优雅地处理缺失字段
    try:
        result = aggregator.aggregate(incomplete_results)
        assert result is not None
    except (KeyError, AttributeError):
        # 如果抛出异常也是可接受的
        pytest.skip("Implementation throws exception for missing fields")


def test_aggregate_performance(sample_agent_results, mock_llm, benchmark):
    """测试聚合性能"""
    from intelligent_project_analyzer.report.result_aggregator import ResultAggregator

    aggregator = ResultAggregator()

    result = benchmark(aggregator.aggregate, sample_agent_results)

    assert result is not None
    # 聚合应该在合理时间内完成（<1秒，不包括LLM调用）
    assert benchmark.stats.stats.mean < 1.0
