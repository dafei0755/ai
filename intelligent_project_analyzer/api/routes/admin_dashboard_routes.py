"""
后台管理 - 分类体系监控API（v7.500 维度学习系统）
"""
import json
import logging
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from ...models.taxonomy_models import (
    TaxonomyConceptDiscovery,
    TaxonomyEmergingType,
    TaxonomyExtendedType,
)
from ..auth_middleware import require_admin

router = APIRouter()
logger = logging.getLogger(__name__)

# 数据库连接（PostgreSQL）
database_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/project_analyzer")
engine = create_engine(database_url, pool_pre_ping=True, echo=False)
SessionLocal = sessionmaker(bind=engine)


@router.get("/stats", dependencies=[Depends(require_admin)])
async def get_dimension_learning_stats():
    """维度学习系统统计数据（前端兼容格式）"""
    logger.info(" 获取维度学习系统统计数据")

    db = SessionLocal()
    try:
        # 获取实际数据
        extended_count = db.query(TaxonomyExtendedType).count()
        emerging_count = db.query(TaxonomyEmergingType).count()
        discovery_count = db.query(TaxonomyConceptDiscovery).count()

        # 按维度统计扩展类型
        dimension_stats = (
            db.query(
                TaxonomyExtendedType.dimension,
                func.count(TaxonomyExtendedType.id),
                func.sum(TaxonomyExtendedType.usage_count),
            )
            .group_by(TaxonomyExtendedType.dimension)
            .all()
        )

        top_dimensions = [
            {"name": dim, "usage_count": int(total_usage or 0), "type_count": count}
            for dim, count, total_usage in dimension_stats
        ][:5]

        return {
            "status": "success",
            "message": f"学习系统已启用 - {extended_count}个扩展标签, {emerging_count}个新兴候选",
            "placeholder_data": {"total_feedbacks": discovery_count, "avg_score": 0, "top_dimensions": top_dimensions},
            "overview": {
                "total_types": 92 + extended_count + emerging_count,  # 92核心+扩展+新兴
                "by_tier": {"core": 92, "extended": extended_count, "emerging": emerging_count},
                "activity_stats": {
                    "discoveries_total": discovery_count,
                    "extended_types": extended_count,
                    "emerging_types": emerging_count,
                },
            },
            "timestamp": datetime.now().isoformat(),
        }
    finally:
        db.close()


@router.get("/overview", dependencies=[Depends(require_admin)])
async def get_taxonomy_overview():
    """分类体系总览"""
    logger.info(" 获取分类体系总览数据")

    db = SessionLocal()
    try:
        extended_count = db.query(TaxonomyExtendedType).count()
        emerging_count = db.query(TaxonomyEmergingType).count()
        discovery_count = db.query(TaxonomyConceptDiscovery).count()

        # 按维度统计
        dimension_breakdown = []
        for dim in [
            "motivation",
            "space",
            "target_user",
            "style",
            "emotion",
            "method",
            "constraint",
            "reference",
            "locality",
        ]:
            ext_count = db.query(TaxonomyExtendedType).filter_by(dimension=dim).count()
            emg_count = db.query(TaxonomyEmergingType).filter_by(dimension=dim).count()
            total_usage = db.query(func.sum(TaxonomyExtendedType.usage_count)).filter_by(dimension=dim).scalar() or 0

            dimension_breakdown.append(
                {
                    "dimension": dim,
                    "core": 10,  # 假设每个维度10个核心类型
                    "extended": ext_count,
                    "emerging": emg_count,
                    "total": 10 + ext_count + emg_count,
                    "total_usage": int(total_usage),
                }
            )

        return {
            "total_types": 92 + extended_count + emerging_count,
            "by_tier": {"core": 92, "extended": extended_count, "emerging": emerging_count},
            "dimension_breakdown": dimension_breakdown,
            "activity_stats": {
                "discoveries_total": discovery_count,
                "extended_types": extended_count,
                "emerging_types": emerging_count,
            },
            "pending_review": {"discoveries": discovery_count},
        }
    finally:
        db.close()


@router.get("/emerging-types", dependencies=[Depends(require_admin)])
async def list_emerging_types(
    dimension: str | None = None,
    sort_by: str = Query("case_count", regex="^(case_count|success_rate|created_at)$"),
    limit: int = Query(50, ge=1, le=200),
):
    """新兴标签列表"""
    logger.info(f"️ 获取新兴标签列表: dimension={dimension}, sort_by={sort_by}")

    db = SessionLocal()
    try:
        query = db.query(TaxonomyEmergingType)

        if dimension:
            query = query.filter(TaxonomyEmergingType.dimension == dimension)

        # 排序
        if sort_by == "case_count":
            query = query.order_by(TaxonomyEmergingType.case_count.desc())
        elif sort_by == "created_at":
            query = query.order_by(TaxonomyEmergingType.created_at.desc())

        emerging_types = query.limit(limit).all()

        items = []
        for et in emerging_types:
            success_rate = et.success_count / et.case_count if et.case_count > 0 else 0
            days_since = (datetime.now() - et.created_at).days

            # 计算晋升进度（基于规则：8次使用，80%成功率）
            progress = min((et.case_count / 8) * 0.5 + (success_rate / 0.8) * 0.5, 1.0)

            items.append(
                {
                    "dimension": et.dimension,
                    "id": et.type_id,
                    "label_zh": et.label_zh,
                    "label_en": et.label_en,
                    "keywords": json.loads(et.keywords) if et.keywords else [],
                    "case_count": et.case_count,
                    "success_count": et.success_count,
                    "success_rate": success_rate,
                    "created_at": et.created_at.isoformat(),
                    "last_used_at": et.last_used_at.isoformat() if et.last_used_at else None,
                    "source": et.source,
                    "confidence_score": et.confidence_score,
                    "promotion_progress": progress,
                    "days_since_created": days_since,
                }
            )

        return {"total": len(items), "items": items}
    finally:
        db.close()


@router.get("/discoveries", dependencies=[Depends(require_admin)])
async def list_concept_discoveries(
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """概念发现列表"""
    logger.info(f" 获取概念发现列表: min_confidence={min_confidence}")

    db = SessionLocal()
    try:
        query = (
            db.query(TaxonomyConceptDiscovery)
            .filter(TaxonomyConceptDiscovery.confidence >= min_confidence)
            .order_by(TaxonomyConceptDiscovery.occurrence_count.desc())
        )

        total = query.count()
        discoveries = query.limit(limit).offset(offset).all()

        items = []
        for disc in discoveries:
            items.append(
                {
                    "id": disc.id,
                    "concept_cluster": disc.concept_cluster,
                    "keywords": json.loads(disc.keywords) if disc.keywords else [],
                    "occurrence_count": disc.occurrence_count,
                    "confidence": disc.confidence,
                    "suggested_dimension": disc.suggested_dimension,
                    "suggested_type_id": disc.suggested_type_id,
                    "discovered_at": disc.discovered_at.isoformat(),
                    "last_seen_at": disc.last_seen_at.isoformat() if disc.last_seen_at else None,
                }
            )

        return {"total": total, "items": items}
    finally:
        db.close()


@router.post("/run-discovery", dependencies=[Depends(require_admin)])
async def run_concept_discovery(user_input: str, session_id: str):
    """手动触发概念发现分析"""
    logger.info(f" 手动触发概念发现: session={session_id}")

    from ...services.concept_discovery_service import ConceptDiscoveryService

    service = ConceptDiscoveryService(database_url)
    result = await service.analyze_session(session_id, user_input)

    return result


@router.post("/run-promotion", dependencies=[Depends(require_admin)])
async def run_tag_promotion(auto_promote: bool = True):
    """手动触发标签晋升检查"""
    logger.info(f"⬆️ 手动触发标签晋升检查: auto_promote={auto_promote}")

    from ...services.taxonomy_promotion_service import TaxonomyPromotionService

    service = TaxonomyPromotionService(database_url)
    result = service.run_promotion_check(auto_promote=auto_promote)

    return result


@router.get("/learning-curve", dependencies=[Depends(require_admin)])
async def get_learning_curve(days: int = Query(30, ge=7, le=90)):
    """
    获取学习曲线数据（过去N天的学习趋势）

    Args:
        days: 统计天数（7-90天）

    Returns:
        学习曲线数据：每天的发现数、晋升数、总类型数
    """
    logger.info(f" 获取学习曲线数据: {days}天")

    db = SessionLocal()
    try:
        start_date = datetime.now() - timedelta(days=days)

        # 按日期统计概念发现
        discoveries_by_date = {}
        discoveries = (
            db.query(TaxonomyConceptDiscovery).filter(TaxonomyConceptDiscovery.discovered_at >= start_date).all()
        )

        for disc in discoveries:
            date_key = disc.discovered_at.date().isoformat()
            discoveries_by_date[date_key] = discoveries_by_date.get(date_key, 0) + 1

        # 按日期统计标签晋升
        promotions_by_date = {}
        extended_types = db.query(TaxonomyExtendedType).filter(TaxonomyExtendedType.promoted_at >= start_date).all()

        for ext in extended_types:
            date_key = ext.promoted_at.date().isoformat()
            promotions_by_date[date_key] = promotions_by_date.get(date_key, 0) + 1

        # 构建时间序列数据
        curve_data = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=(days - i - 1))).date()
            date_key = date.isoformat()

            curve_data.append(
                {
                    "date": date_key,
                    "discoveries": discoveries_by_date.get(date_key, 0),
                    "promotions": promotions_by_date.get(date_key, 0),
                }
            )

        # 计算累积数量
        total_extended = db.query(TaxonomyExtendedType).count()
        total_emerging = db.query(TaxonomyEmergingType).count()
        total_discoveries = db.query(TaxonomyConceptDiscovery).count()

        return {
            "curve_data": curve_data,
            "summary": {
                "total_extended": total_extended,
                "total_emerging": total_emerging,
                "total_discoveries": total_discoveries,
                "period_days": days,
            },
        }

    finally:
        db.close()
