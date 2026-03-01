"""
搜索和推荐API路由

提供语义搜索、相似项目、推荐等功能
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/external/search", tags=["外部数据-搜索"])


# ============================================================================
# 数据模型
# ============================================================================


class SearchRequest(BaseModel):
    """搜索请求"""

    query: str
    limit: int = 10
    min_quality_score: float = 0.5
    source: Optional[str] = None
    category: Optional[str] = None


class RecommendRequest(BaseModel):
    """推荐请求"""

    categories: Optional[List[str]] = None
    styles: Optional[List[str]] = None
    min_year: Optional[int] = None
    limit: int = 20


# ============================================================================
# API端点
# ===========================================================================


@router.post("/semantic", summary="语义搜索")
async def semantic_search(request: SearchRequest) -> Dict[str, Any]:
    """
    基于语义的项目搜索

    Args:
        request: 搜索请求

    Returns:
        匹配项目列表
    """
    try:
        from ..models import get_external_db
        from ..utils import SemanticSearchService

        logger.info(f"🔍 语义搜索: {request.query}")

        db = get_external_db()
        with db.get_session() as session:
            service = SemanticSearchService(session)
            results = service.search_by_text(
                query_text=request.query,
                limit=request.limit,
                min_quality_score=request.min_quality_score,
                source=request.source,
                category=request.category,
            )

        return {"status": "success", "query": request.query, "total": len(results), "results": results}

    except Exception as e:
        logger.error(f"❌ 语义搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/similar/{project_id}", summary="查找相似项目")
async def find_similar(project_id: int, limit: int = Query(10, ge=1, le=50)) -> Dict[str, Any]:
    """
    根据项目ID查找相似项目

    Args:
        project_id: 参考项目ID
        limit: 返回数量

    Returns:
        相似项目列表
    """
    try:
        from ..models import get_external_db
        from ..utils import SemanticSearchService

        logger.info(f"🔍 查找相似项目: {project_id}")

        db = get_external_db()
        with db.get_session() as session:
            service = SemanticSearchService(session)
            results = service.find_similar_projects(project_id=project_id, limit=limit)

        return {"status": "success", "reference_project_id": project_id, "total": len(results), "results": results}

    except Exception as e:
        logger.error(f"❌ 查找相似项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recommend", summary="项目推荐")
async def recommend_projects(request: RecommendRequest) -> Dict[str, Any]:
    """
    基于用户偏好的项目推荐

    Args:
        request: 推荐请求

    Returns:
        推荐项目列表
    """
    try:
        from ..models import get_external_db
        from ..utils import RecommendationEngine

        logger.info(f"🎯 项目推荐: {request.dict()}")

        db = get_external_db()
        with db.get_session() as session:
            engine = RecommendationEngine(session)
            results = engine.recommend_by_preferences(
                preferred_categories=request.categories,
                preferred_styles=request.styles,
                min_year=request.min_year,
                limit=request.limit,
            )

        return {"status": "success", "total": len(results), "results": results}

    except Exception as e:
        logger.error(f"❌ 项目推荐失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending", summary="热门趋势")
async def get_trending(
    days: int = Query(30, ge=1, le=365), category: Optional[str] = None, limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """
    获取热门/趋势项目

    Args:
        days: 时间范围（天）
        category: 分类筛选
        limit: 返回数量

    Returns:
        热门项目列表
    """
    try:
        from ..models import get_external_db
        from ..utils import RecommendationEngine

        logger.info(f"📈 获取热门项目: days={days}, category={category}")

        db = get_external_db()
        with db.get_session() as session:
            engine = RecommendationEngine(session)
            results = engine.get_trending_projects(days=days, category=category, limit=limit)

        return {"status": "success", "days": days, "category": category, "total": len(results), "results": results}

    except Exception as e:
        logger.error(f"❌ 获取热门项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/showcase", summary="高质量展示")
async def get_showcase(
    min_score: float = Query(0.8, ge=0, le=1), limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    """
    获取高质量项目展示

    Args:
        min_score: 最小质量分数
        limit: 返回数量

    Returns:
        高质量项目列表
    """
    try:
        from ..models import get_external_db
        from ..utils import RecommendationEngine

        logger.info(f"⭐ 获取高质量展示: min_score={min_score}")

        db = get_external_db()
        with db.get_session() as session:
            engine = RecommendationEngine(session)
            results = engine.get_high_quality_showcase(min_score=min_score, limit=limit)

        return {"status": "success", "min_score": min_score, "total": len(results), "results": results}

    except Exception as e:
        logger.error(f"❌ 获取高质量展示失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]
