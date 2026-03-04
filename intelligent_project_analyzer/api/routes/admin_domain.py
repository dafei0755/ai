"""域名质量统计 + 能力边界违规监控 API"""

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from loguru import logger

from ..auth_middleware import require_admin

router = APIRouter()


# ============================================================================
# 域名质量统计与自动审核 API (v7.155)
# ============================================================================


@router.get("/domain-quality/review-queue")
async def get_review_queue(_=Depends(require_admin)):
    """
    获取待审核域名队列

    返回根据质量分自动识别的低质量域名列表，需要管理员审核决定是否屏蔽

    返回：
    - queue: 待审核域名列表（按严重程度排序）
    - count: 待审核数量
    """
    try:
        from ..services.auto_review_service import get_auto_review_service

        service = get_auto_review_service()
        queue = service.get_review_queue()

        return {
            "status": "success",
            "data": {
                "queue": queue,
                "count": len(queue),
            },
        }

    except Exception as e:
        logger.error(f" 获取审核队列失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domain-quality/statistics")
async def get_domain_quality_statistics(_=Depends(require_admin)):
    """
    获取域名质量统计概要

    返回：
    - domain_tracking: 域名追踪统计
    - search_filters: 搜索过滤器统计
    - review_queue_size: 待审核队列大小
    """
    try:
        from ..services.auto_review_service import get_auto_review_service

        service = get_auto_review_service()
        stats = service.get_statistics()

        return {
            "status": "success",
            "data": stats,
        }

    except Exception as e:
        logger.error(f" 获取域名质量统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domain-quality/low-quality")
async def get_low_quality_domains(
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    _=Depends(require_admin),
):
    """
    获取低质量域名列表（按质量分排序）

    参数：
    - limit: 返回数量限制

    返回：
    - domains: 低质量域名列表
    """
    try:
        from ..services.auto_review_service import get_auto_review_service

        service = get_auto_review_service()
        domains = service.get_low_quality_domains(limit=limit)

        return {
            "status": "success",
            "data": {
                "domains": domains,
                "count": len(domains),
            },
        }

    except Exception as e:
        logger.error(f" 获取低质量域名列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domain-quality/detail/{domain:path}")
async def get_domain_detail(domain: str, _=Depends(require_admin)):
    """
    获取单个域名的详细统计信息

    参数：
    - domain: 域名

    返回：
    - 域名详细统计信息
    """
    try:
        from ..services.auto_review_service import get_auto_review_service

        service = get_auto_review_service()
        detail = service.get_domain_detail(domain)

        if not detail:
            raise HTTPException(status_code=404, detail=f"域名 {domain} 未找到统计记录")

        return {
            "status": "success",
            "data": detail,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 获取域名详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/domain-quality/approve")
async def approve_domain(
    domain: str = Body(..., embed=True, description="域名"),
    add_to_whitelist: bool = Body(False, embed=True, description="是否加入白名单"),
    admin_notes: str | None = Body(None, embed=True, description="管理员备注"),
    _=Depends(require_admin),
):
    """
    批准域名（移出审核队列）

    参数：
    - domain: 域名
    - add_to_whitelist: 是否同时加入白名单
    - admin_notes: 管理员备注

    返回：
    - 操作结果
    """
    try:
        from ..services.auto_review_service import get_auto_review_service

        service = get_auto_review_service()
        result = service.approve_domain(domain, add_to_whitelist, admin_notes)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "操作失败"))

        return {
            "status": "success",
            "data": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 批准域名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/domain-quality/block")
async def block_domain(
    domain: str = Body(..., embed=True, description="域名"),
    admin_notes: str | None = Body(None, embed=True, description="管理员备注"),
    _=Depends(require_admin),
):
    """
    屏蔽域名（加入黑名单）

    参数：
    - domain: 域名
    - admin_notes: 管理员备注

    返回：
    - 操作结果
    """
    try:
        from ..services.auto_review_service import get_auto_review_service

        service = get_auto_review_service()
        result = service.block_domain(domain, admin_notes)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "操作失败"))

        return {
            "status": "success",
            "data": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 屏蔽域名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/domain-quality/dismiss")
async def dismiss_domain(
    domain: str = Body(..., embed=True, description="域名"),
    admin_notes: str | None = Body(None, embed=True, description="管理员备注"),
    _=Depends(require_admin),
):
    """
    移出审核队列（保持观察）

    参数：
    - domain: 域名
    - admin_notes: 管理员备注

    返回：
    - 操作结果
    """
    try:
        from ..services.auto_review_service import get_auto_review_service

        service = get_auto_review_service()
        result = service.dismiss_domain(domain, admin_notes)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "操作失败"))

        return {
            "status": "success",
            "data": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 移出审核队列失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/domain-quality/batch-action")
async def batch_domain_action(
    domains: List[str] = Body(..., description="域名列表"),
    action: str = Body(..., description="操作类型: approve/block/dismiss"),
    admin_notes: str | None = Body(None, description="管理员备注"),
    _=Depends(require_admin),
):
    """
    批量操作域名

    参数：
    - domains: 域名列表
    - action: 操作类型 (approve/block/dismiss)
    - admin_notes: 管理员备注

    返回：
    - 批量操作结果汇总
    """
    try:
        if action not in ["approve", "block", "dismiss"]:
            raise HTTPException(status_code=400, detail=f"无效的操作类型: {action}")

        from ..services.auto_review_service import get_auto_review_service

        service = get_auto_review_service()
        result = service.batch_action(domains, action, admin_notes)

        return {
            "status": "success",
            "data": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 批量操作失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 能力边界违规监控 API
# ============================================================================


@router.get("/capability-boundary/stats")
async def get_capability_boundary_stats(
    time_range: str = Query("7d", regex="^(24h|7d|30d)$"), _admin=Depends(require_admin)
):
    """
    获取能力边界违规统计数据

    Args:
        time_range: 时间范围 (24h, 7d, 30d)

    Returns:
        {
            "violations": [...],  # 违规记录列表
            "node_stats": [...],  # 节点统计
            "trends": [...]       # 趋势数据
        }
    """
    try:
        # TODO: 实际实现从数据库或日志中统计
        # 这里提供模拟数据结构，实际需要：
        # 1. 从 Redis/PostgreSQL 读取能力边界检查记录
        # 2. 统计各节点的检查次数和转化次数
        # 3. 分析趋势数据

        logger.info(f" [能力边界监控] 获取统计数据，时间范围: {time_range}")

        # 计算时间范围
        now = datetime.now()
        if time_range == "24h":
            now - timedelta(hours=24)
        elif time_range == "7d":
            now - timedelta(days=7)
        else:  # 30d
            now - timedelta(days=30)

        # 模拟数据 - 实际应从数据库查询
        violations = [
            {
                "id": "1",
                "timestamp": (now - timedelta(hours=2)).isoformat(),
                "node": "progressive_step3_gap_filling",
                "original_deliverable": "施工图",
                "transformed_deliverable": "设计策略文档",
                "user_input": "35岁首套，骑士大华悦，程序员...",
                "session_id": "session_123",
                "match_score": 0.45,
                "transformation_reason": "施工图需要AutoCAD专业工具，超出系统能力边界",
            }
        ]

        node_stats = [
            {
                "node_name": "progressive_step3_gap_filling",
                "total_checks": 156,
                "violation_count": 42,
                "violation_rate": 0.269,
                "most_common_violations": [
                    {"original": "施工图", "transformed": "设计策略文档", "count": 18},
                    {"original": "效果图", "transformed": "空间概念描述", "count": 15},
                ],
            }
        ]

        trends = [
            {"date": (now - timedelta(days=i)).strftime("%Y-%m-%d"), "violations": 10 + i, "checks": 45 + i * 2}
            for i in range(7, 0, -1)
        ]

        return {
            "violations": violations,
            "node_stats": node_stats,
            "trends": trends,
            "time_range": time_range,
            "query_time": now.isoformat(),
        }

    except Exception as e:
        logger.error(f" [能力边界监控] 获取统计数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
