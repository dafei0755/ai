# -*- coding: utf-8 -*-
"""
MT-1 (2026-03-01): 系统监控、健康检查、用户管理路由

从 api/server.py 提取的系统级端点：
  - / (root)
  - /api/rate-limit/stats, /api/keys/stats
  - /health, /readiness
  - /api/debug/redis-health, /api/debug/sessions, /api/debug/redis
  - /api/v1/dimensions/validate
  - /api/user/{user_id}/*

外部状态通过 _server 惰性代理访问。
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from loguru import logger
from pydantic import BaseModel, Field

from intelligent_project_analyzer.services.file_processor import file_processor
from intelligent_project_analyzer.settings import settings

router = APIRouter(tags=["System & Monitoring"])
from intelligent_project_analyzer.api._server_proxy import server_proxy as _server


@router.get("/")
async def root():
    """根路径"""
    return {"message": "智能项目分析系统 API", "version": "2.0.0", "docs": "/docs"}


@router.get("/api/rate-limit/stats")
async def get_rate_limit_stats():
    """
    获取 LLM API 限流统计

    v3.9新增：监控 LLM API 调用限流状态
    """
    try:
        from intelligent_project_analyzer.services.rate_limiter import rate_limit_manager

        return {"status": "ok", "stats": rate_limit_manager.get_all_stats()}
    except Exception as e:
        return {"status": "error", "error": str(e), "message": "限流模块未初始化"}


@router.get("/api/keys/stats")
async def get_api_key_stats():
    """
    获取 API Key 负载均衡统计

    v3.9新增：监控多 Key 使用状态
    """
    try:
        from intelligent_project_analyzer.services.key_balancer import key_balancer

        return {
            "status": "ok",
            "available_providers": key_balancer.available_providers,
            "stats": key_balancer.get_all_stats(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "message": "Key 负载均衡器未初始化"}


@router.get("/health")
async def health_check():
    """
     P2优化: 增强健康检查端点 - 返回详细组件状态

    用于负载均衡器和监控系统快速检查服务状态
    返回各组件（Redis/Playwright/LLM）的健康状态
    """
    import time

    start_time = time.time()

    health_status = {"status": "healthy", "timestamp": datetime.now().isoformat(), "components": {}, "metrics": {}}

    try:
        # 1. 检查Redis连接
        redis_healthy = False
        redis_latency = 0
        try:
            redis_start = time.time()
            await _server.session_manager.redis_client.ping()
            redis_latency = (time.time() - redis_start) * 1000
            redis_healthy = True
            health_status["components"]["redis"] = {
                "status": "up",
                "latency_ms": round(redis_latency, 2),
                "mode": "redis",
            }
        except Exception as redis_err:
            health_status["components"]["redis"] = {
                "status": "degraded",
                "mode": "memory_fallback",
                "error": str(redis_err),
            }

        # 2. 检查Playwright浏览器池
        playwright_healthy = False
        try:
            from intelligent_project_analyzer.api.html_pdf_generator import get_browser_pool

            browser_pool = get_browser_pool()
            if browser_pool._initialized and browser_pool._browser:
                playwright_healthy = browser_pool._browser.is_connected()
                health_status["components"]["playwright"] = {
                    "status": "up" if playwright_healthy else "down",
                    "initialized": browser_pool._initialized,
                    "connected": playwright_healthy,
                }
            else:
                health_status["components"]["playwright"] = {
                    "status": "not_initialized",
                    "pdf_generation": "unavailable",
                }
        except Exception as pw_err:
            health_status["components"]["playwright"] = {"status": "error", "error": str(pw_err)}

        # 3. 检查LLM配置
        llm_configured = False
        app_settings = None
        llm_configured = False
        try:
            from intelligent_project_analyzer.settings import settings as app_settings

            llm_provider = getattr(app_settings.llm, "provider", "openai")
            api_key = getattr(app_settings.llm, "api_key", "")
            llm_configured = bool(api_key and api_key != "your-api-key-here")

            if llm_configured:
                health_status["components"]["llm"] = {"status": "configured", "provider": llm_provider}
            else:
                status_label = "not_configured"
                warning = "LLM API key not set"
                if app_settings.is_development:
                    status_label = "dev_mode"
                    warning += " (allowed in dev)"
                health_status["components"]["llm"] = {
                    "status": status_label,
                    "provider": llm_provider,
                    "warning": warning,
                }
        except Exception as llm_err:
            health_status["components"]["llm"] = {"status": "error", "error": str(llm_err)}

        # 4. 会话统计
        try:
            active_sessions = await _server.session_manager.list_all_sessions()
            health_status["metrics"]["active_sessions"] = len(active_sessions)
            health_status["metrics"]["active_websockets"] = sum(
                len(conns) for conns in _server.websocket_connections.values()
            )
        except Exception:
            health_status["metrics"]["active_sessions"] = 0
            health_status["metrics"]["active_websockets"] = 0

        # 5. 总体健康判断
        if not redis_healthy and not health_status["components"]["redis"].get("mode") == "memory_fallback":
            health_status["status"] = "degraded"
        if not llm_configured and not getattr(app_settings, "is_development", False):
            health_status["status"] = "degraded"

        health_status["response_time_ms"] = round((time.time() - start_time) * 1000, 2)

        return health_status

    except Exception as e:
        logger.error(f" 健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
        }


@router.get("/api/debug/redis-health")
async def redis_health_check():
    """
    Redis 健康检查端点 - 用于诊断 Redis 性能问题

    执行完整的 CRUD 操作并返回延迟时间
    """
    import time

    start = time.time()

    try:
        test_id = f"test-health-{int(time.time())}"

        # 测试 Create
        create_start = time.time()
        await _server.session_manager.create(test_id, {"test": "data", "timestamp": datetime.now().isoformat()})
        create_time = (time.time() - create_start) * 1000

        # 测试 Read
        read_start = time.time()
        data = await _server.session_manager.get(test_id)
        read_time = (time.time() - read_start) * 1000

        # 测试 Update
        update_start = time.time()
        await _server.session_manager.update(test_id, {"test": "updated"})
        update_time = (time.time() - update_start) * 1000

        # 测试 Delete
        delete_start = time.time()
        await _server.session_manager.delete(test_id)
        delete_time = (time.time() - delete_start) * 1000

        total_time = (time.time() - start) * 1000

        return {
            "status": "healthy",
            "total_latency_ms": int(total_time),
            "operations": {
                "create_ms": int(create_time),
                "read_ms": int(read_time),
                "update_ms": int(update_time),
                "delete_ms": int(delete_time),
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        logger.error(f" Redis健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "elapsed_ms": int(elapsed),
            "timestamp": datetime.now().isoformat(),
        }


# ========================================
#  v7.139 Phase 3: 维度关联检测API
# ========================================


class DimensionValidationRequest(BaseModel):
    """维度验证请求"""

    dimensions: List[Dict[str, Any]] = Field(..., description="维度配置列表")
    mode: Optional[str] = Field(None, description="检测模式: strict/balanced/lenient")


class DimensionValidationResponse(BaseModel):
    """维度验证响应"""

    conflicts: List[Dict[str, Any]] = Field(default_factory=list, description="冲突列表")
    adjustment_suggestions: List[Dict[str, Any]] = Field(default_factory=list, description="调整建议列表")
    is_valid: bool = Field(..., description="是否通过验证（无critical冲突）")


@router.post("/api/v1/dimensions/validate", response_model=DimensionValidationResponse)
async def validate_dimensions(request: DimensionValidationRequest):
    """
     v7.139: 验证维度配置，检测冲突并生成调整建议

    用于前端实时验证用户调整后的维度配置。

    Args:
        request: 包含dimensions和mode的请求体

    Returns:
        包含冲突列表、调整建议和验证结果
    """
    try:
        from intelligent_project_analyzer.services.dimension_selector import DimensionSelector

        selector = DimensionSelector()
        result = selector.validate_dimensions(request.dimensions, mode=request.mode)

        return DimensionValidationResponse(
            conflicts=result.get("conflicts", []),
            adjustment_suggestions=result.get("adjustment_suggestions", []),
            is_valid=result.get("is_valid", True),
        )

    except Exception as e:
        logger.error(f" 维度验证失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"维度验证失败: {str(e)}")


@router.get("/readiness")
async def readiness_check():
    """
    就绪检查端点 - 检查服务是否准备好接收流量

    检查项：
    1. Redis连接状态
    2. 腾讯云API可达性
    3. 动态规则加载器状态
    4. 会话管理器状态
    """
    checks = {}
    is_ready = True

    # 1. 检查Redis连接
    try:
        if _server.session_manager:
            # 尝试ping Redis
            await _server.session_manager.list_all_sessions()
            checks["redis"] = {"status": "ok", "message": "Redis连接正常"}
        else:
            checks["redis"] = {"status": "warning", "message": "会话管理器未初始化"}
            is_ready = False
    except Exception as e:
        checks["redis"] = {"status": "error", "message": f"Redis连接失败: {str(e)}"}
        is_ready = False

    # 2. 检查腾讯云API可达性（如果启用）
    try:
        if os.getenv("ENABLE_TENCENT_CONTENT_SAFETY") == "true":
            from intelligent_project_analyzer.security.tencent_content_safety import get_tencent_content_safety_client

            client = get_tencent_content_safety_client()
            if client:
                checks["tencent_api"] = {"status": "ok", "message": "腾讯云API已配置"}
            else:
                checks["tencent_api"] = {"status": "warning", "message": "腾讯云API未启用"}
        else:
            checks["tencent_api"] = {"status": "disabled", "message": "腾讯云API未启用"}
    except Exception as e:
        checks["tencent_api"] = {"status": "error", "message": f"腾讯云API检查失败: {str(e)}"}
        # 腾讯云API失败不影响就绪状态（可以降级到本地检测）

    # 3. 检查动态规则加载器状态
    try:
        from intelligent_project_analyzer.security.dynamic_rule_loader import get_rule_loader

        loader = get_rule_loader()
        if loader:
            stats = loader.get_stats()
            checks["dynamic_rules"] = {
                "status": "ok",
                "message": "动态规则加载器正常",
                "version": stats.get("version", "unknown"),
                "categories": stats["keywords"]["total_categories"],
            }
        else:
            checks["dynamic_rules"] = {"status": "warning", "message": "动态规则加载器未初始化"}
    except Exception as e:
        checks["dynamic_rules"] = {"status": "error", "message": f"动态规则检查失败: {str(e)}"}
        # 动态规则失败不影响就绪状态（可以回退到静态规则）

    # 4. 检查会话管理器状态
    try:
        if _server.session_manager:
            checks["session_manager"] = {"status": "ok", "message": "会话管理器正常"}
        else:
            checks["session_manager"] = {"status": "error", "message": "会话管理器未初始化"}
            is_ready = False
    except Exception as e:
        checks["session_manager"] = {"status": "error", "message": f"会话管理器检查失败: {str(e)}"}
        is_ready = False

    # 5. 检查文件处理器（可选）
    try:
        if file_processor:
            checks["file_processor"] = {"status": "ok", "message": "文件处理器正常"}
        else:
            checks["file_processor"] = {"status": "warning", "message": "文件处理器未初始化"}
    except Exception as e:
        checks["file_processor"] = {"status": "warning", "message": f"文件处理器检查失败: {str(e)}"}

    # 构建响应
    response = {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.now().isoformat(),
        "checks": checks,
    }

    # 如果不就绪，返回503状态码
    if not is_ready:
        return Response(
            content=json.dumps(response, ensure_ascii=False, indent=2), status_code=503, media_type="application/json"
        )

    return response


# ==================== 用户隔离 API ====================


@router.get("/api/user/{user_id}/sessions")
async def get_user_sessions(user_id: str, limit: int = 10):
    """
    获取用户的所有会话

    v3.9新增：用户会话隔离
    """
    try:
        from intelligent_project_analyzer.services.user_session_manager import get_user_session_manager

        manager = await get_user_session_manager()
        sessions = await manager.get_user_sessions(user_id, limit)
        return {"user_id": user_id, "sessions": sessions, "count": len(sessions)}
    except Exception as e:
        return {"error": str(e), "sessions": []}


@router.get("/api/user/{user_id}/progress")
async def get_user_all_progress(user_id: str):
    """
    获取用户所有会话的进度

    v3.9新增：用户独立进度
    """
    try:
        from intelligent_project_analyzer.services.user_session_manager import get_user_session_manager

        manager = await get_user_session_manager()
        progress_list = await manager.get_all_user_progress(user_id)
        return {"user_id": user_id, "progress": progress_list}
    except Exception as e:
        return {"error": str(e), "progress": []}


@router.get("/api/user/{user_id}/quota")
async def get_user_quota(user_id: str):
    """
    获取用户配额信息

    v3.9新增：用户配额管理
    """
    try:
        from intelligent_project_analyzer.services.user_session_manager import get_user_session_manager

        manager = await get_user_session_manager()
        quota = await manager.check_user_quota(user_id)
        usage = await manager.get_user_usage(user_id)
        return {**quota, **usage}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/user/{user_id}/active")
async def get_user_active_session(user_id: str):
    """
    获取用户当前活跃会话

    v3.9新增：快速获取用户正在进行的分析
    """
    try:
        from intelligent_project_analyzer.services.user_session_manager import get_user_session_manager

        manager = await get_user_session_manager()
        active_session_id = await manager.get_user_active_session(user_id)

        if active_session_id:
            progress = await manager.get_progress(user_id, active_session_id)
            return {
                "user_id": user_id,
                "active_session_id": active_session_id,
                "progress": progress.to_dict() if progress else None,
            }

        return {"user_id": user_id, "active_session_id": None, "message": "没有活跃会话"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/debug/sessions")
async def debug_sessions():
    """调试：列出所有活跃会话"""
    all_sessions = await _server.session_manager.get_all_sessions()
    return {
        "active_sessions": [s["session_id"] for s in all_sessions],
        "session_details": {
            s["session_id"]: {
                "status": s.get("status"),
                "current_node": s.get("current_node"),
                "has_interrupt": s.get("interrupt_data") is not None,
            }
            for s in all_sessions
        },
    }


@router.get("/api/debug/redis")
async def check_redis_status():
    """
    调试：检查Redis连接状态和配置

    v3.6新增：用于诊断会话历史不稳定问题
    """
    try:
        if _server.session_manager._memory_mode:
            return {
                "mode": "memory",
                "status": "fallback",
                "warning": "Redis不可用，使用内存模式（数据不持久化）",
                "sessions_in_memory": len(_server.session_manager._memory_sessions),
                "redis_url": _server.session_manager.redis_url,
                "ttl": _server.session_manager.SESSION_TTL,
            }

        # 测试Redis连接
        await _server.session_manager.redis_client.ping()
        session_keys = await _server.session_manager.list_all_sessions()

        # 获取Redis配置
        redis_info = await _server.session_manager.redis_client.info("persistence")

        return {
            "mode": "redis",
            "status": "connected",
            "redis_url": _server.session_manager.redis_url,
            "session_count": len(session_keys),
            "session_ttl": f"{_server.session_manager.SESSION_TTL}秒 ({_server.session_manager.SESSION_TTL // 3600}小时)",
            "persistence": {
                "rdb_enabled": redis_info.get("rdb_bgsave_in_progress", "unknown"),
                "aof_enabled": redis_info.get("aof_enabled", "unknown"),
                "last_save_time": redis_info.get("rdb_last_save_time", "unknown"),
            },
            "recommendation": " Redis已连接，会话数据持久化存储" if redis_info.get("aof_enabled") == "1" else "️ 建议启用AOF持久化以防止数据丢失",
        }
    except Exception as e:
        return {"mode": "error", "status": "failed", "error": str(e), "recommendation": " Redis连接失败，请检查Redis服务是否运行"}
