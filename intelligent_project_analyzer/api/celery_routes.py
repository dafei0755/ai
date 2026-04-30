# -*- coding: utf-8 -*-
"""
Celery 任务 API 路由

提供基于 Celery 的异步任务 API，支持多用户并发
可与原有的 BackgroundTasks 模式共存
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

# Celery 相关导入
try:
    from intelligent_project_analyzer.services.celery_app import celery_app
    from intelligent_project_analyzer.services.celery_tasks import (
        analyze_project,
        get_queue_length,
        get_task_status,
    )

    CELERY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"️ Celery 未安装或导入失败: {e}")
    CELERY_AVAILABLE = False

# 文件处理

# Redis 会话管理
from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

# 创建路由
router = APIRouter(prefix="/api/celery", tags=["Celery 任务队列"])


# ==================== 数据模型 ====================


class CeleryAnalysisRequest(BaseModel):
    """Celery 分析请求"""

    user_input: str = Field(..., description="用户输入")
    user_id: str = Field(default="web_user", description="用户ID")
    priority: int = Field(default=0, description="优先级 (0=普通, 1=高)")
    analysis_mode: str = Field(default="normal", description="分析模式 (normal/deep_thinking)")


class CeleryTaskResponse(BaseModel):
    """Celery 任务响应"""

    session_id: str
    task_id: str
    status: str
    message: str
    queue_position: Optional[int] = None
    estimated_wait: Optional[str] = None


class CeleryStatusResponse(BaseModel):
    """Celery 状态响应"""

    session_id: str
    task_id: str
    status: str  # PENDING, STARTED, PROGRESS, WAITING, SUCCESS, FAILURE
    progress: float = 0.0
    current_stage: Optional[str] = None
    detail: Optional[str] = None
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class QueueInfoResponse(BaseModel):
    """队列信息响应"""

    celery_available: bool
    queues: Dict[str, int]
    workers: List[str]
    active_tasks: int


# ==================== API 端点 ====================


@router.get("/health")
async def celery_health():
    """检查 Celery 是否可用"""
    if not CELERY_AVAILABLE:
        return {"status": "unavailable", "message": "Celery 未安装，请运行 pip install celery"}

    try:
        # 检查 Celery 连接
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        if stats:
            return {
                "status": "healthy",
                "workers": list(stats.keys()),
                "message": f"Celery 正常运行，{len(stats)} 个 Worker 在线",
            }
        else:
            return {"status": "no_workers", "workers": [], "message": "Celery Broker 已连接，但没有 Worker 运行"}
    except Exception as e:
        return {"status": "error", "error": str(e), "message": "无法连接到 Celery Broker"}


@router.post("/analysis/start", response_model=CeleryTaskResponse)
async def start_celery_analysis(request: CeleryAnalysisRequest):
    """
    使用 Celery 启动分析任务

    优势：
    - 支持多用户并发
    - 任务可重试
    - 支持优先级队列
    - 可监控任务状态
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Celery 服务不可用，请使用 /api/analysis/start 端点")

    # 生成会话 ID
    session_id = f"celery-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"

    # 初始化 Redis 会话
    session_manager = RedisSessionManager()
    await session_manager.connect()

    try:
        await session_manager.create(
            session_id,
            {
                "session_id": session_id,
                "user_input": request.user_input,
                "user_id": request.user_id,
                "mode": "celery",
                "analysis_mode": request.analysis_mode,  #  支持深度思考/深度思考pro模式
                "status": "queued",
                "progress": 0.0,
                "created_at": datetime.now().isoformat(),
            },
        )

        # 提交 Celery 任务
        task = analyze_project.apply_async(
            args=[session_id, request.user_input, request.user_id, request.analysis_mode],
            queue="analysis" if request.priority == 0 else "high_priority",
        )

        # 保存任务 ID 到会话
        await session_manager.update(session_id, {"task_id": task.id})

        # 获取队列位置
        try:
            queue_length = get_queue_length("analysis")
        except Exception:
            queue_length = None

        logger.info(f" [Celery API] 任务已提交: session={session_id}, task={task.id}")

        return CeleryTaskResponse(
            session_id=session_id,
            task_id=task.id,
            status="queued",
            message="分析任务已加入队列",
            queue_position=queue_length,
            estimated_wait=f"约 {queue_length * 3} 分钟" if queue_length else None,
        )

    finally:
        await session_manager.disconnect()


@router.get("/analysis/status/{session_id}", response_model=CeleryStatusResponse)
async def get_celery_analysis_status(session_id: str):
    """
    获取 Celery 任务状态
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Celery 服务不可用")

    # 从 Redis 获取会话
    session_manager = RedisSessionManager()
    await session_manager.connect()

    try:
        session = await session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        task_id = session.get("task_id")
        if not task_id:
            return CeleryStatusResponse(
                session_id=session_id,
                task_id="",
                status=session.get("status", "unknown"),
                progress=session.get("progress", 0.0),
                message="任务ID未找到",
            )

        # 获取 Celery 任务状态
        task_status = get_task_status(task_id)

        # 映射状态
        celery_status = task_status.get("status", "UNKNOWN")
        meta = task_status.get("meta", {})

        return CeleryStatusResponse(
            session_id=session_id,
            task_id=task_id,
            status=celery_status,
            progress=meta.get("progress", session.get("progress", 0.0)),
            current_stage=meta.get("current_stage", session.get("current_node")),
            detail=meta.get("detail", session.get("detail")),
            message=meta.get("message"),
            result=task_status.get("result") if task_status.get("ready") else None,
            error=str(task_status.get("result", {}).get("error")) if celery_status == "FAILURE" else None,
        )

    finally:
        await session_manager.disconnect()


@router.post("/analysis/cancel/{session_id}")
async def cancel_celery_analysis(session_id: str):
    """
    取消 Celery 任务
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Celery 服务不可用")

    session_manager = RedisSessionManager()
    await session_manager.connect()

    try:
        session = await session_manager.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        task_id = session.get("task_id")
        if not task_id:
            raise HTTPException(status_code=400, detail="任务ID未找到")

        # 撤销任务
        celery_app.control.revoke(task_id, terminate=True)

        # 更新会话状态
        await session_manager.update(session_id, {"status": "cancelled", "cancelled_at": datetime.now().isoformat()})

        logger.info(f" [Celery API] 任务已取消: session={session_id}, task={task_id}")

        return {"session_id": session_id, "task_id": task_id, "status": "cancelled", "message": "任务已取消"}

    finally:
        await session_manager.disconnect()


@router.get("/queue/info", response_model=QueueInfoResponse)
async def get_queue_info():
    """
    获取队列信息
    """
    if not CELERY_AVAILABLE:
        return QueueInfoResponse(celery_available=False, queues={}, workers=[], active_tasks=0)

    try:
        inspect = celery_app.control.inspect()

        # 获取 Worker 列表
        stats = inspect.stats() or {}
        workers = list(stats.keys())

        # 获取活跃任务数
        active = inspect.active() or {}
        active_tasks = sum(len(tasks) for tasks in active.values())

        # 获取队列长度
        queues = {}
        for queue_name in ["analysis", "report", "default"]:
            try:
                queues[queue_name] = get_queue_length(queue_name)
            except Exception:
                queues[queue_name] = 0

        return QueueInfoResponse(celery_available=True, queues=queues, workers=workers, active_tasks=active_tasks)

    except Exception as e:
        logger.error(f"获取队列信息失败: {e}")
        return QueueInfoResponse(celery_available=False, queues={}, workers=[], active_tasks=0)


# ==================== 注册路由的函数 ====================


def register_celery_routes(app):
    """
    将 Celery 路由注册到 FastAPI 应用

    在 server.py 中调用：
    from intelligent_project_analyzer.api.celery_routes import register_celery_routes
    register_celery_routes(app)
    """
    app.include_router(router)
    logger.info(" Celery API 路由已注册: /api/celery/*")
