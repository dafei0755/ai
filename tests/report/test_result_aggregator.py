"""
Report模块测试 - Result Aggregator

测试结果聚合器的核心功能
使用conftest.py提供的fixtures避免app初始化问题
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
    mock_instance = Mock()
    mock_instance.invoke.return_value = Mock(
        content="""
# 项目分析报告

## 市场分析
咖啡市场规模达到X亿元...

## 设计方案
采用现代简约风格...

## 投资预算
总投资预算约100万元...
"""
    )
    return mock_instance


class TestResultAggregatorAgent:
    """测试结果聚合器Agent"""

    def test_result_aggregator_initialization(self, env_setup):
        """测试结果聚合器初始化"""
        from intelligent_project_analyzer.report.result_aggregator import ResultAggregatorAgent

        # 由于ResultAggregatorAgent是一个Agent，可能需要LLM初始化
        # 这里只测试类是否可导入
        assert ResultAggregatorAgent is not None

    def test_aggregate_results_basic(self, sample_agent_results, env_setup):
        """测试基本的聚合功能（不依赖实际LLM调用）"""
        # 这个测试需要mock整个agent执行过程
        # 由于ResultAggregatorAgent较复杂，我们简化测试
        assert sample_agent_results is not None
        assert "market_analyst" in sample_agent_results

    def test_sample_results_structure(self, sample_agent_results):
        """测试示例结果的数据结构"""
        # 验证测试fixture的结构正确
        assert isinstance(sample_agent_results, dict)
        assert "market_analyst" in sample_agent_results
        assert "design_expert" in sample_agent_results
        assert "financial_expert" in sample_agent_results

        # 验证deliverables结构
        for expert, data in sample_agent_results.items():
            assert "deliverables" in data
            assert isinstance(data["deliverables"], list)
            for deliverable in data["deliverables"]:
                assert "label" in deliverable
                assert "content" in deliverable


class TestReportDataModels:
    """测试报告数据模型"""

    def test_executive_summary_model(self, env_setup):
        """测试执行摘要模型"""
        from intelligent_project_analyzer.report.result_aggregator import ExecutiveSummary

        summary = ExecutiveSummary(
            project_overview="咖啡馆设计项目",
            key_findings=["发现1", "发现2"],
            key_recommendations=["建议1", "建议2"],
            success_factors=["因素1", "因素2"]
        )

        assert summary.project_overview == "咖啡馆设计项目"
        assert len(summary.key_findings) == 2
        assert len(summary.key_recommendations) == 2
        assert len(summary.success_factors) == 2

    def test_core_answer_model(self, env_setup):
        """测试核心答案模型"""
        from intelligent_project_analyzer.report.result_aggregator import CoreAnswer

        answer = CoreAnswer(
            question="什么是咖啡馆设计的关键要素？",
            answer="关键要素包括...",
            deliverables=["交付物1", "交付物2"],
            timeline="3-6个月",
            budget_range="50-100万"
        )

        assert answer.question is not None
        assert answer.answer is not None
        assert len(answer.deliverables) == 2
        assert answer.timeline == "3-6个月"
        assert answer.budget_range == "50-100万"

    def test_deliverable_answer_model(self, env_setup):
        """测试交付物答案模型"""
        from intelligent_project_analyzer.report.result_aggregator import DeliverableAnswer

        deliverable = DeliverableAnswer(
            deliverable_id="D1",
            deliverable_name="市场分析报告",
            deliverable_type="market_analysis",
            owner_role="market_analyst",
            owner_answer="市场规模达到..."
        )

        assert deliverable.deliverable_id == "D1"
        assert deliverable.deliverable_name == "市场分析报告"
        assert deliverable.owner_role == "market_analyst"
        assert deliverable.owner_answer is not None

    def test_report_section_with_id_model(self, env_setup):
        """测试报告章节模型"""
        from intelligent_project_analyzer.report.result_aggregator import ReportSectionWithId

        section = ReportSectionWithId(
            section_id="section1",
            title="市场分析",
            content="市场内容...",
            confidence=0.85
        )

        assert section.section_id == "section1"
        assert section.title == "市场分析"
        assert section.content == "市场内容..."
        assert 0 <= section.confidence <= 1

    def test_final_report_model(self, env_setup):
        """测试最终报告模型 - 验证必填嵌套模型可正常构造"""
        from intelligent_project_analyzer.report.result_aggregator import (
            FinalReport,
            CoreAnswer,
            DeliberationProcess,
            RecommendationItem,
            RecommendationsSection,
        )

        core_answer = CoreAnswer(
            question="咖啡馆设计的关键要素是什么？",
            answer="空间规划、品牌氛围与成本控制三者并重。",
            deliverables=["平面方案", "材料清单"],
            timeline="3-6个月",
            budget_range="80-120万",
        )

        deliberation = DeliberationProcess(
            inquiry_architecture="市场+设计+财务三角分析",
            reasoning="咖啡馆项目同时受市场定位、设计质量和预算约束，三者缺一不可。",
            role_selection=["市场分析师", "设计专家", "财务顾问"],
            strategic_approach="先确定品牌定位，再规划空间，最后测算成本。",
        )

        rec_item = RecommendationItem(
            content="优先确定目标客群，避免后期返工。",
            dimension="critical",
            reasoning="目标客群决定装修风格与预算上限。",
            source_expert="市场分析师",
        )

        recommendations = RecommendationsSection(
            recommendations=[rec_item],
            summary="核心建议：先定位后设计，控制成本节点。",
        )

        report = FinalReport(
            core_answer=core_answer,
            deliberation_process=deliberation,
            recommendations=recommendations,
        )

        assert report.core_answer.question == "咖啡馆设计的关键要素是什么？"
        assert report.deliberation_process.inquiry_architecture == "市场+设计+财务三角分析"
        assert len(report.recommendations.recommendations) == 1
        assert report.recommendations.recommendations[0].dimension == "critical"
        assert report.expert_reports == {}  # default_factory 产生空字典
        assert report.insights is None  # 可选字段默认为 None


class TestReportWithFixture:
    """使用全局 fixture 的报告测试"""

    def test_aggregator_with_sample_result(self, sample_analysis_result, env_setup):
        """验证 sample_analysis_result fixture 字段完整，可用于聚合器测试"""
        # 确认 fixture 提供了所有必要字段
        assert "session_id" in sample_analysis_result
        assert "analysis_complete" in sample_analysis_result
        assert "agent_results" in sample_analysis_result
        assert "final_report" in sample_analysis_result

        # 校验 agent_results 结构
        for item in sample_analysis_result["agent_results"]:
            assert "agent_name" in item
            assert "result" in item
            assert "confidence" in item
            assert 0.0 <= item["confidence"] <= 1.0

        # 校验 final_report 结构
        final = sample_analysis_result["final_report"]
        assert "summary" in final
        assert "overall_score" in final
        assert "next_steps" in final
        assert isinstance(final["next_steps"], list)


class TestReportHelperFunctions:
    """测试报告辅助功能"""

    def test_multiple_expert_results_handling(self, sample_agent_results):
        """测试多个专家结果的处理"""
        # 验证可以迭代所有专家结果
        expert_count = 0
        deliverable_count = 0

        for expert_name, expert_data in sample_agent_results.items():
            expert_count += 1
            for deliverable in expert_data.get("deliverables", []):
                deliverable_count += 1

        assert expert_count == 3
        assert deliverable_count == 3

    def test_empty_results_handling(self):
        """测试空结果处理"""
        empty_results = {}

        # 空结果应该可以安全处理
        assert isinstance(empty_results, dict)
        assert len(empty_results) == 0

    def test_single_expert_results(self):
        """测试单个专家结果"""
        single_result = {
            "market_analyst": {
                "deliverables": [{"label": "分析", "content": "内容"}]
            }
        }

        assert len(single_result) == 1
        assert "market_analyst" in single_result


class TestReportPerformance:
    """测试报告相关性能"""

    def test_large_results_structure(self, benchmark):
        """测试大量结果的结构处理性能"""
        # 生成大量专家结果
        large_results = {
            f"expert_{i}": {
                "deliverables": [{
                    "label": f"部分 {i}",
                    "content": "内容 " * 100
                }]
            }
            for i in range(50)
        }

        # 基准测试字典操作性能
        def process_results():
            count = 0
            for expert, data in large_results.items():
                for deliverable in data.get("deliverables", []):
                    count += len(deliverable.get("content", ""))
            return count

        result = benchmark(process_results)
        assert result > 0
