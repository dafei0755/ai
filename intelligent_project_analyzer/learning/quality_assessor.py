"""
质量评估器 (Quality Assessor)

评估维度的质量和有效性。

评估维度:
1. 有效性 - 维度是否帮助专家产生高质量输出
2. 覆盖面 - 维度是否被广泛使用
3. 清晰度 - 维度描述是否易懂
4. 专家反馈 - 人工评分

版本: v3.0
创建日期: 2026-02-10
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from loguru import logger
import statistics


@dataclass
class QualityMetrics:
    """维度质量指标"""

    effectiveness_score: float  # 有效性得分 (0-1)
    coverage_score: float  # 覆盖面得分 (0-1)
    clarity_score: float  # 清晰度得分 (0-1)
    usage_frequency: float  # 使用频率
    expert_rating_avg: float  # 专家平均评分 (1-5)
    recommendation: str  # keep, optimize, deprecate

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def get_composite_score(self) -> float:
        """计算综合得分"""
        # 归一化专家评分到 0-1
        normalized_rating = self.expert_rating_avg / 5.0 if self.expert_rating_avg > 0 else 0.5

        # 加权计算综合得分
        composite = (
            self.effectiveness_score * 0.4
            + self.coverage_score * 0.2
            + self.clarity_score * 0.2
            + normalized_rating * 0.2
        )
        return composite


class QualityAssessor:
    """
    评估维度的质量和有效性

    核心能力:
    1. 有效性评估 - 基于使用效果
    2. 覆盖面统计 - 使用频率分析
    3. 清晰度分析 - 描述质量评估
    4. 专家反馈整合
    """

    def __init__(self, db_connection=None):
        """
        初始化评估器

        Args:
            db_connection: 数据库连接（可选，未实现时为None）
        """
        self.db = db_connection
        logger.info(" 初始化质量评估器")

    async def assess_dimension(self, dimension_id: int = None, dimension_data: Dict[str, Any] = None) -> QualityMetrics:
        """
        评估单个维度

        Args:
            dimension_id: 维度ID（从数据库查询）
            dimension_data: 维度数据（直接传入）

        Returns:
            质量指标对象
        """
        if dimension_id:
            # 从数据库获取维度数据
            try:
                from .database_manager import get_db_manager

                db = get_db_manager()
                db_dim = db.get_dimension(dimension_id)
                if db_dim:
                    dimension_data = {
                        "name": db_dim.get("name", ""),
                        "description": db_dim.get("description", ""),
                        "ask_yourself": db_dim.get("ask_yourself", ""),
                        "examples": db_dim.get("examples", ""),
                        "usage_count": db_dim.get("usage_count", 0),
                        "expert_rating": db_dim.get("effectiveness_score", 0.0),
                    }
                    logger.debug(f" 从数据库加载维度 {dimension_id}: {db_dim.get('name', '')}")
                else:
                    logger.warning(f" 数据库中未找到维度 {dimension_id}")
                    dimension_data = {}
            except Exception as e:
                logger.warning(f" 数据库查询失败，回退到空数据: {e}")
                dimension_data = {}

        if not dimension_data:
            logger.error(" 缺少维度数据")
            return self._create_default_metrics()

        # 计算各项指标
        effectiveness = await self._calculate_effectiveness(dimension_data)
        coverage = self._calculate_coverage(dimension_data)
        clarity = self._calculate_clarity(dimension_data)
        usage_freq = dimension_data.get("usage_count", 0)
        expert_rating = dimension_data.get("expert_rating", 0.0)

        # 生成建议
        recommendation = self._make_recommendation(effectiveness, coverage, clarity, expert_rating)

        metrics = QualityMetrics(
            effectiveness_score=effectiveness,
            coverage_score=coverage,
            clarity_score=clarity,
            usage_frequency=usage_freq,
            expert_rating_avg=expert_rating,
            recommendation=recommendation,
        )

        logger.debug(f" 维度评估完成: {metrics.get_composite_score():.2f}")
        return metrics

    async def batch_assess(
        self, dimensions: List[Dict[str, Any]] = None, project_type: str = None
    ) -> Dict[str, QualityMetrics]:
        """
        批量评估多个维度

        Args:
            dimensions: 维度列表
            project_type: 项目类型过滤

        Returns:
            维度名称 -> 质量指标的字典
        """
        if not dimensions:
            logger.warning("️ 没有维度需要评估")
            return {}

        results = {}
        for dim in dimensions:
            dim_name = dim.get("name", "unknown")
            metrics = await self.assess_dimension(dimension_data=dim)
            results[dim_name] = metrics

        logger.info(f" 批量评估完成: {len(results)} 个维度")
        return results

    async def _calculate_effectiveness(self, dimension_data: Dict[str, Any]) -> float:
        """
        计算有效性得分

        策略：
        - 查询使用该维度的会话
        - 评估这些会话的输出质量
        - 计算相关性

        简化版本：基于使用次数的简单估计
        """
        usage_count = dimension_data.get("usage_count", 0)

        # 简单启发式：使用次数越多，说明越有效
        if usage_count >= 50:
            return 0.9
        elif usage_count >= 20:
            return 0.7
        elif usage_count >= 10:
            return 0.5
        elif usage_count >= 5:
            return 0.3
        else:
            return 0.1

    def _calculate_coverage(self, dimension_data: Dict[str, Any]) -> float:
        """
        计算覆盖面得分

        策略：
        - 统计维度在不同项目类型中的使用
        - 计算覆盖的项目类型比例

        简化版本：基于使用频率
        """
        usage_count = dimension_data.get("usage_count", 0)

        # 归一化到 0-1
        # 假设100次使用为满分
        coverage = min(usage_count / 100.0, 1.0)
        return coverage

    def _calculate_clarity(self, dimension_data: Dict[str, Any]) -> float:
        """
        计算清晰度得分

        策略：
        - 描述长度合理性（50-200字为佳）
        - 问题是否明确（包含"?"）
        - 示例是否充分（至少2个）

        简化版本：基于结构完整性
        """
        description = dimension_data.get("description", "")
        ask_yourself = dimension_data.get("ask_yourself", "")
        examples = dimension_data.get("examples", "")

        score = 0.0

        # 描述长度
        desc_len = len(description)
        if 50 <= desc_len <= 200:
            score += 0.4
        elif 20 <= desc_len <= 300:
            score += 0.2

        # 问题明确性
        if "?" in ask_yourself or "？" in ask_yourself:
            score += 0.3

        # 示例充分性
        example_count = len(examples.split(","))
        if example_count >= 3:
            score += 0.3
        elif example_count >= 2:
            score += 0.2
        elif example_count >= 1:
            score += 0.1

        return min(score, 1.0)

    def _make_recommendation(self, effectiveness: float, coverage: float, clarity: float, expert_rating: float) -> str:
        """
        综合判断维度的处理建议

        Returns:
            "keep" - 保留
            "optimize" - 优化
            "deprecate" - 废弃
        """
        # 归一化专家评分到 0-1
        normalized_rating = expert_rating / 5.0 if expert_rating > 0 else 0.5

        # 加权计算综合得分
        composite_score = effectiveness * 0.4 + coverage * 0.2 + clarity * 0.2 + normalized_rating * 0.2

        if composite_score >= 0.7:
            return "keep"
        elif composite_score >= 0.5:
            return "optimize"
        else:
            return "deprecate"

    def _create_default_metrics(self) -> QualityMetrics:
        """创建默认指标"""
        return QualityMetrics(
            effectiveness_score=0.0,
            coverage_score=0.0,
            clarity_score=0.0,
            usage_frequency=0.0,
            expert_rating_avg=0.0,
            recommendation="unknown",
        )

    def assess_dimension_sync(self, dimension_data: Dict[str, Any]) -> QualityMetrics:
        """同步版本的评估方法（用于测试）"""
        import asyncio

        return asyncio.run(self.assess_dimension(dimension_data=dimension_data))
