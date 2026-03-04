"""
Celery 任务 API 路由

提供基于 Celery 的异步任务 API，支持多用户并发
可与原有的 BackgroundTasks 模式共存
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel, Field

# Celery 相关导入
try:
    from intelligent_project_analyzer.services.celery_app import celery_app
    from intelligent_project_analyzer.services.celery_tasks import (
        analyze_project,
        analyze_project_with_files,
        get_queue_length,
        get_task_status,
    )

    CELERY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"️ Celery 未安装或导入失败: {e}")
    CELERY_AVAILABLE = False

# 文件处理
from intelligent_project_analyzer.services.file_processor import file_processor

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
    queue_position: int | None = None
    estimated_wait: str | None = None


class CeleryStatusResponse(BaseModel):
    """Celery 状态响应"""

    session_id: str
    task_id: str
    status: str  # PENDING, STARTED, PROGRESS, WAITING, SUCCESS, FAILURE
    progress: float = 0.0
    current_stage: str | None = None
    detail: str | None = None
    message: str | None = None
    result: Dict[str, Any] | None = None
    error: str | None = None


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
        except:
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


@router.post("/analysis/start-with-files", response_model=CeleryTaskResponse)
async def start_celery_analysis_with_files(
    user_input: str = Form(default=""),
    user_id: str = Form(default="web_user"),
    priority: int = Form(default=0),
    analysis_mode: str = Form(default="normal"),
    file_metadata: str = Form(default="[]"),
    files: List[UploadFile] = File(default=[]),
):
    """
    使用 Celery 启动带文件的分析任务

    支持多模态输入：文本 + 文件（PDF, TXT, 图片）

    Args:
        user_input: 用户输入的文本描述
        user_id: 用户ID
        priority: 优先级 (0=普通, 1=高)
        analysis_mode: 分析模式 (normal/deep_thinking)
        file_metadata: 文件元数据JSON字符串
        files: 上传的文件列表
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Celery 服务不可用，请使用 /api/analysis/start-with-files 端点")

    logger.info(" [Celery] 收到多模态分析请求")
    logger.info(f"用户输入: {user_input[:100] if user_input else '(无文本)'}...")
    logger.info(f"分析模式: {analysis_mode}")
    logger.info(f"文件数量: {len(files)}")

    # 验证输入
    if not user_input.strip() and not files:
        raise HTTPException(status_code=400, detail="请提供文本输入或上传文件")

    # 解析文件元数据
    try:
        file_metadata_list = json.loads(file_metadata) if file_metadata else []
        logger.info(f" 文件元数据: {len(file_metadata_list)} 条")
    except json.JSONDecodeError as e:
        logger.warning(f"️ 文件元数据解析失败: {e}")
        file_metadata_list = []

    metadata_by_filename = {m.get("filename"): m for m in file_metadata_list}

    # 生成会话 ID
    session_id = f"celery-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    logger.info(f"生成 Session ID: {session_id}")

    # 处理文件（在 API 层同步完成）
    file_contents = []
    attachment_metadata = []
    visual_references = []

    for file in files:
        try:
            content = await file.read()
            file_size = len(content)

            if file_size > 10 * 1024 * 1024:
                logger.warning(f"️ 文件过大，跳过: {file.filename} ({file_size} bytes)")
                continue

            # 保存文件
            file_path = await file_processor.save_file(
                file_content=content, filename=file.filename, session_id=session_id
            )

            # 获取该文件的元数据
            file_meta = metadata_by_filename.get(file.filename, {})
            categories = file_meta.get("categories", [])
            custom_description = file_meta.get("custom_description", "")

            # 判断是否为图片
            if file.content_type in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
                extracted_content = await file_processor.extract_image_enhanced(file_path)

                reference_type = "general"
                if "style" in categories:
                    reference_type = "style"
                elif "layout" in categories:
                    reference_type = "layout"
                elif "color" in categories:
                    reference_type = "color"

                relative_path = f"{session_id}/{file_path.name}"
                visual_references.append(
                    {
                        "file_path": str(file_path),
                        "relative_path": relative_path,
                        "width": extracted_content.get("width"),
                        "height": extracted_content.get("height"),
                        "format": extracted_content.get("format"),
                        "vision_analysis": extracted_content.get("vision_analysis", ""),
                        "structured_features": extracted_content.get("structured_features", {}),
                        "user_description": custom_description if custom_description else None,
                        "reference_type": reference_type,
                        "categories": categories,
                        "cached_at": datetime.now().isoformat(),
                    }
                )
                logger.info(f"️ 视觉参考已提取: {file.filename} | 类型: {reference_type}")
            else:
                extracted_content = await file_processor.extract_content(
                    file_path=file_path, content_type=file.content_type
                )

            file_contents.append(extracted_content)
            attachment_metadata.append(
                {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "size": file_size,
                    "path": str(file_path),
                    "extracted_summary": extracted_content.get("summary", ""),
                    "categories": categories,
                    "custom_description": custom_description,
                }
            )

            logger.info(f" 文件处理完成: {file.filename}")

        except Exception as e:
            logger.error(f" 文件处理失败: {file.filename} - {str(e)}")
            attachment_metadata.append({"filename": file.filename, "content_type": file.content_type, "error": str(e)})

    # 生成全局风格锚点
    visual_style_anchor = _generate_style_anchor(visual_references) if visual_references else None

    # 合并输入
    combined_input = _build_combined_input(user_input, file_contents)

    # 初始化 Redis 会话
    session_manager = RedisSessionManager()
    await session_manager.connect()

    try:
        await session_manager.create(
            session_id,
            {
                "session_id": session_id,
                "user_input": user_input,
                "combined_input": combined_input,
                "user_id": user_id,
                "mode": "celery",
                "analysis_mode": analysis_mode,
                "status": "queued",
                "progress": 0.0,
                "attachments": attachment_metadata,
                "visual_references": visual_references if visual_references else None,
                "visual_style_anchor": visual_style_anchor,
                "created_at": datetime.now().isoformat(),
            },
        )

        # 提交 Celery 任务
        task = analyze_project_with_files.apply_async(
            args=[session_id, combined_input, user_id, analysis_mode, visual_references, visual_style_anchor],
            queue="analysis" if priority == 0 else "high_priority",
        )

        await session_manager.update(session_id, {"task_id": task.id})

        try:
            queue_length = get_queue_length("analysis")
        except:
            queue_length = None

        logger.info(f" [Celery API] 带文件任务已提交: session={session_id}, task={task.id}, files={len(files)}")

        return CeleryTaskResponse(
            session_id=session_id,
            task_id=task.id,
            status="queued",
            message=f"分析任务已加入队列，已接收 {len(files)} 个文件",
            queue_position=queue_length,
            estimated_wait=f"约 {queue_length * 3} 分钟" if queue_length else None,
        )

    finally:
        await session_manager.disconnect()


def _generate_style_anchor(visual_references: List[Dict[str, Any]]) -> str:
    """从视觉参考中生成全局风格锚点"""
    if not visual_references:
        return ""

    all_styles = []
    all_colors = []
    all_materials = []

    for ref in visual_references:
        features = ref.get("structured_features", {})
        all_styles.extend(features.get("style_keywords", []))
        all_colors.extend(features.get("dominant_colors", []))
        all_materials.extend(features.get("materials", []))

    # 去重
    def unique_list(items: List[str], max_count: int = 3) -> List[str]:
        seen = set()
        result = []
        for item in items:
            if item and item not in seen:
                seen.add(item)
                result.append(item)
                if len(result) >= max_count:
                    break
        return result

    anchor_parts = unique_list(all_styles, 3) + unique_list(all_colors, 2) + unique_list(all_materials, 2)
    return ", ".join(anchor_parts) if anchor_parts else ""


def _build_combined_input(user_input: str, file_contents: List[Dict[str, Any]]) -> str:
    """合并用户输入和文件内容"""
    parts = []

    if user_input and user_input.strip():
        parts.append(f"用户需求：\n{user_input.strip()}")

    for i, content in enumerate(file_contents, 1):
        summary = content.get("summary", "")
        if summary:
            parts.append(f"\n附件{i}内容摘要：\n{summary}")

    return "\n\n".join(parts) if parts else user_input


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
            except:
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
