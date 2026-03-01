"""
标签晋升服务

自动监控新兴标签的表现，将达标的标签晋升为扩展标签。
"""

from datetime import datetime, timedelta
from typing import Dict

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..models.taxonomy_models import (
    TaxonomyEmergingType,
    TaxonomyExtendedType,
)


class TaxonomyPromotionService:
    """标签晋升服务"""

    def __init__(self, database_url: str = None):
        """初始化服务"""
        if database_url is None:
            import os

            database_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/project_analyzer")

        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # 晋升规则
        self.PROMOTION_RULES = {
            "min_case_count": 8,  # 最少使用8次
            "min_success_rate": 0.80,  # 成功率≥80%
            "min_confidence": 0.70,  # 置信度≥0.70（LLM发现的标签）
            "min_days_active": 7,  # 至少活跃7天
        }

        logger.info(" 标签晋升服务已初始化")

    def evaluate_emerging_type(self, emerging_type: TaxonomyEmergingType) -> Dict:
        """
        评估新兴标签是否达到晋升标准

        Args:
            emerging_type: 新兴标签记录

        Returns:
            评估结果字典
        """
        success_rate = emerging_type.success_count / emerging_type.case_count if emerging_type.case_count > 0 else 0

        days_active = (datetime.now() - emerging_type.created_at).days

        # 检查各项指标
        checks = {
            "case_count": emerging_type.case_count >= self.PROMOTION_RULES["min_case_count"],
            "success_rate": success_rate >= self.PROMOTION_RULES["min_success_rate"],
            "confidence": emerging_type.confidence_score >= self.PROMOTION_RULES["min_confidence"],
            "days_active": days_active >= self.PROMOTION_RULES["min_days_active"],
        }

        qualified = all(checks.values())

        return {
            "qualified": qualified,
            "checks": checks,
            "metrics": {
                "case_count": emerging_type.case_count,
                "success_rate": success_rate,
                "confidence": emerging_type.confidence_score,
                "days_active": days_active,
            },
        }

    def promote_to_extended(self, emerging_type: TaxonomyEmergingType, db_session) -> bool:
        """
        将新兴标签晋升为扩展标签

        Args:
            emerging_type: 新兴标签记录
            db_session: 数据库会话

        Returns:
            是否成功晋升
        """
        try:
            # 检查是否已存在
            existing = (
                db_session.query(TaxonomyExtendedType)
                .filter_by(dimension=emerging_type.dimension, type_id=emerging_type.type_id)
                .first()
            )

            if existing:
                logger.warning(f"  ️  扩展标签已存在: {emerging_type.label_zh}, 跳过")
                return False

            # 创建扩展标签
            extended = TaxonomyExtendedType(
                dimension=emerging_type.dimension,
                type_id=emerging_type.type_id,
                label_zh=emerging_type.label_zh,
                label_en=emerging_type.label_en,
                keywords=emerging_type.keywords,
                usage_count=emerging_type.case_count,
                success_count=emerging_type.success_count,
                promoted_at=datetime.now(),
                last_used_at=emerging_type.last_used_at,
            )

            db_session.add(extended)

            # 删除新兴标签记录（已晋升）
            db_session.delete(emerging_type)

            logger.info(
                f"  ⬆️ 晋升成功: {emerging_type.label_zh} "
                f"({emerging_type.case_count}次使用, "
                f"{emerging_type.success_count/emerging_type.case_count:.1%}成功率)"
            )

            return True

        except Exception as e:
            logger.error(f"   晋升失败: {e}")
            return False

    def run_promotion_check(self, auto_promote: bool = True) -> Dict:
        """
        执行晋升检查

        Args:
            auto_promote: 是否自动晋升达标标签

        Returns:
            晋升结果统计
        """
        logger.info(" 开始标签晋升检查")

        db = self.SessionLocal()
        results = {
            "total_emerging": 0,
            "qualified": 0,
            "promoted": 0,
            "failed": 0,
            "details": [],
        }

        try:
            # 获取所有新兴标签
            emerging_types = db.query(TaxonomyEmergingType).all()
            results["total_emerging"] = len(emerging_types)

            logger.info(f"   共有 {len(emerging_types)} 个新兴标签")

            for emerging_type in emerging_types:
                # 评估
                evaluation = self.evaluate_emerging_type(emerging_type)

                detail = {
                    "dimension": emerging_type.dimension,
                    "type_id": emerging_type.type_id,
                    "label_zh": emerging_type.label_zh,
                    "evaluation": evaluation,
                    "promoted": False,
                }

                if evaluation["qualified"]:
                    results["qualified"] += 1

                    if auto_promote:
                        success = self.promote_to_extended(emerging_type, db)
                        detail["promoted"] = success

                        if success:
                            results["promoted"] += 1
                        else:
                            results["failed"] += 1

                results["details"].append(detail)

            if auto_promote:
                db.commit()
                logger.info(
                    f" 晋升检查完成: {results['qualified']}个达标, " f"{results['promoted']}个成功晋升, {results['failed']}个失败"
                )
            else:
                logger.info(f" 晋升检查完成: {results['qualified']}个达标 (仅评估，未晋升)")

            return results

        except Exception as e:
            db.rollback()
            logger.error(f" 晋升检查失败: {e}")
            results["error"] = str(e)
            return results

        finally:
            db.close()

    def get_promotion_statistics(self) -> Dict:
        """获取晋升统计信息"""
        db = self.SessionLocal()

        try:
            # 新兴标签统计
            total_emerging = db.query(TaxonomyEmergingType).count()

            # 符合条件的新兴标签（模拟评估）
            qualified_count = 0
            emerging_types = db.query(TaxonomyEmergingType).all()

            for et in emerging_types:
                evaluation = self.evaluate_emerging_type(et)
                if evaluation["qualified"]:
                    qualified_count += 1

            # 扩展标签统计
            total_extended = db.query(TaxonomyExtendedType).count()

            # 最近30天晋升的标签
            month_ago = datetime.now() - timedelta(days=30)
            recent_promotions = (
                db.query(TaxonomyExtendedType).filter(TaxonomyExtendedType.promoted_at >= month_ago).count()
            )

            return {
                "total_emerging": total_emerging,
                "qualified_for_promotion": qualified_count,
                "total_extended": total_extended,
                "recent_promotions_30d": recent_promotions,
                "promotion_rules": self.PROMOTION_RULES,
            }

        finally:
            db.close()

    def adjust_promotion_rules(
        self,
        min_case_count: int = None,
        min_success_rate: float = None,
        min_confidence: float = None,
        min_days_active: int = None,
    ):
        """
        动态调整晋升规则

        Args:
            min_case_count: 最少使用次数
            min_success_rate: 最低成功率
            min_confidence: 最低置信度
            min_days_active: 最少活跃天数
        """
        if min_case_count is not None:
            self.PROMOTION_RULES["min_case_count"] = min_case_count

        if min_success_rate is not None:
            self.PROMOTION_RULES["min_success_rate"] = min_success_rate

        if min_confidence is not None:
            self.PROMOTION_RULES["min_confidence"] = min_confidence

        if min_days_active is not None:
            self.PROMOTION_RULES["min_days_active"] = min_days_active

        logger.info(f"️  晋升规则已更新: {self.PROMOTION_RULES}")
