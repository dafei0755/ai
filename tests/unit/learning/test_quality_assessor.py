"""
测试质量评估器 (Test Quality Assessor)

测试维度质量评估功能。

版本: v3.0
创建日期: 2026-02-10
"""

import pytest
from intelligent_project_analyzer.learning.quality_assessor import QualityAssessor, QualityMetrics


class TestQualityAssessor:
    """测试质量评估器"""

    @pytest.fixture
    def assessor(self):
        """创建评估器实例"""
        return QualityAssessor(db_connection=None)

    def test_initialization(self, assessor):
        """测试初始化"""
        assert assessor is not None

    def test_calculate_clarity_full(self, assessor):
        """测试清晰度计算 - 完整维度"""
        dimension_data = {
            "name": "空间序列编排",
            "description": "从入口到核心空间的动线叙事与情绪曲线设计，通过空间的序列组织创造体验节奏。" * 2,  # 足够长度
            "ask_yourself": "参观者的'啊哈时刻'应该在第几个转角？",
            "examples": "渐入式序列, 震撼式入口, 迷宫式探索, 线性引导",
            "usage_count": 25,
        }

        clarity = assessor._calculate_clarity(dimension_data)
        assert 0.0 <= clarity <= 1.0
        assert clarity >= 0.8  # 应该得高分

    def test_calculate_clarity_minimal(self, assessor):
        """测试清晰度计算 - 最小维度"""
        dimension_data = {"name": "测试", "description": "短", "ask_yourself": "无问号", "examples": "无", "usage_count": 0}

        clarity = assessor._calculate_clarity(dimension_data)
        assert 0.0 <= clarity <= 1.0
        assert clarity < 0.5  # 应该得低分

    def test_calculate_effectiveness(self, assessor):
        """测试有效性计算"""
        # 高使用量
        high_usage = {"usage_count": 100}
        effectiveness_high = assessor.assess_dimension_sync(high_usage)

        # 低使用量
        low_usage = {"usage_count": 2}
        effectiveness_low = assessor.assess_dimension_sync(low_usage)

        assert effectiveness_high.effectiveness_score > effectiveness_low.effectiveness_score

    def test_calculate_coverage(self, assessor):
        """测试覆盖面计算"""
        dimension_data = {"usage_count": 50}
        coverage = assessor._calculate_coverage(dimension_data)

        assert 0.0 <= coverage <= 1.0
        assert coverage == 0.5  # 50/100

    def test_make_recommendation_keep(self, assessor):
        """测试推荐 - 保留"""
        recommendation = assessor._make_recommendation(effectiveness=0.9, coverage=0.8, clarity=0.9, expert_rating=4.5)
        assert recommendation == "keep"

    def test_make_recommendation_optimize(self, assessor):
        """测试推荐 - 优化"""
        recommendation = assessor._make_recommendation(effectiveness=0.6, coverage=0.5, clarity=0.6, expert_rating=3.0)
        assert recommendation == "optimize"

    def test_make_recommendation_deprecate(self, assessor):
        """测试推荐 - 废弃"""
        recommendation = assessor._make_recommendation(effectiveness=0.3, coverage=0.2, clarity=0.3, expert_rating=2.0)
        assert recommendation == "deprecate"

    def test_assess_dimension_sync(self, assessor):
        """测试同步评估"""
        dimension_data = {
            "name": "功能邻近度矩阵",
            "description": "基于使用频率、流程逻辑、声学干扰等因素的功能分区优化。",
            "ask_yourself": "厨房与餐厅要多近？安静区与活动区如何隔离？",
            "examples": "高频邻近, 流程连贯性, 干扰隔离, 紧急响应距离",
            "usage_count": 30,
            "expert_rating": 4.2,
        }

        metrics = assessor.assess_dimension_sync(dimension_data)

        assert isinstance(metrics, QualityMetrics)
        assert 0.0 <= metrics.effectiveness_score <= 1.0
        assert 0.0 <= metrics.coverage_score <= 1.0
        assert 0.0 <= metrics.clarity_score <= 1.0
        assert metrics.usage_frequency == 30
        assert metrics.expert_rating_avg == 4.2
        assert metrics.recommendation in ["keep", "optimize", "deprecate"]

    def test_quality_metrics_composite_score(self):
        """测试质量指标综合得分"""
        metrics = QualityMetrics(
            effectiveness_score=0.8,
            coverage_score=0.6,
            clarity_score=0.7,
            usage_frequency=50,
            expert_rating_avg=4.0,
            recommendation="keep",
        )

        composite = metrics.get_composite_score()
        assert 0.0 <= composite <= 1.0
        # 0.8*0.4 + 0.6*0.2 + 0.7*0.2 + (4.0/5)*0.2 = 0.32 + 0.12 + 0.14 + 0.16 = 0.74
        assert abs(composite - 0.74) < 0.01

    def test_batch_assess(self, assessor):
        """测试批量评估"""
        dimensions = [
            {
                "name": "维度1",
                "description": "测试描述1" * 10,
                "ask_yourself": "如何测试？",
                "examples": "例1, 例2, 例3",
                "usage_count": 20,
            },
            {
                "name": "维度2",
                "description": "测试描述2" * 10,
                "ask_yourself": "是否有效？",
                "examples": "例4, 例5",
                "usage_count": 50,
            },
        ]

        import asyncio

        results = asyncio.run(assessor.batch_assess(dimensions=dimensions))

        assert len(results) == 2
        assert "维度1" in results
        assert "维度2" in results
        assert all(isinstance(m, QualityMetrics) for m in results.values())
