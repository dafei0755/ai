# -*- coding: utf-8 -*-
"""
分析路由模块 (MT-1 提取自 api/server.py)

Routes:
  POST /api/analysis/start
  POST /api/analysis/start-with-files
  POST /api/analysis/{session_id}/visual-reference/describe
  GET  /api/analysis/status/{session_id}
  POST /api/analysis/resume
  POST /api/analysis/followup
  GET  /api/analysis/result/{session_id}
  GET  /api/analysis/report/{session_id}
  GET  /api/analysis/report/{session_id}/download-pdf
  GET  /api/analysis/report/{session_id}/download-all-experts-pdf
"""
from __future__ import annotations

import asyncio
import io
import json
import os
import re
import time
import uuid
from collections import OrderedDict, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from intelligent_project_analyzer.services.file_processor import file_processor
from intelligent_project_analyzer.services.geoip_service import get_geoip_service

from .deps import DEV_MODE, sessions_cache
from .helpers import (
    _derive_section_identity,
    _enrich_sections_with_agent_results,
    _format_agent_payload,
    _is_blank_section,
    _normalize_section_id,
    _sanitize_custom_analysis,
    _sanitize_structured_data,
)
from .models import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisStatus,
    ChallengeDetectionResponse,
    ChallengeItemResponse,
    ComprehensiveAnalysisResponse,
    ConclusionsResponse,
    CoreAnswerResponse,
    CoreAnswerV7Response,
    DeliberationProcessResponse,
    DeliverableAnswerResponse,
    ExecutiveSummaryResponse,
    ExpertSupportChainResponse,
    InsightsSectionResponse,
    QuestionnaireResponseData,
    QuestionnaireResponseItem,
    RecommendationsSectionResponse,
    ReportResponse,
    ReportSectionResponse,
    RequirementsAnalysisResponse,
    ResumeRequest,
    ReviewFeedbackItemResponse,
    ReviewFeedbackResponse,
    ReviewRoundDataResponse,
    ReviewVisualizationResponse,
    SessionResponse,
    StructuredReportResponse,
)
from .pdf_generator import (
    PDFGenerator,
    generate_all_experts_pdf,
    generate_all_experts_pdf_async,
    generate_all_experts_pdf_fast,
    generate_report_pdf,
)
from .workflow_runner import run_workflow_async
from intelligent_project_analyzer.api._server_proxy import server_proxy as _server


async def _get_session_manager():
    """向后兼容：代理到 server._get_session_manager()"""
    return await _server._get_session_manager()


router = APIRouter(tags=["analysis"])


@router.post("/api/analysis/start", response_model=SessionResponse)
async def start_analysis(
    request: Request,  #  用于IP采集
    analysis_request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(_server.get_current_user),  #  v7.158: 强制JWT认证，禁止未登录访问
):
    """
    开始分析（仅 Dynamic Mode）

    创建新的分析会话并在后台执行工作流

     v7.39: 支持 analysis_mode 参数
    - normal: 深度思考模式，集中生成1张概念图
    - deep_thinking: 深度思考pro模式，每个专家都生成对应的概念图

     v7.130: 支持JWT认证获取真实WordPress用户信息
     v7.158: 强制登录才能使用分析功能
    """
    print(f"\n 收到分析请求")
    print(f"用户输入: {analysis_request.user_input[:100]}...")
    print(f"分析模式: {analysis_request.analysis_mode}")  #  v7.39

    #  v7.158: 强制认证，current_user 必定存在
    # 从JWT中提取用户信息
    username = None
    display_name = None

    #  采集IP地址和地理位置
    geoip_service = get_geoip_service()
    client_ip = geoip_service.get_client_ip(request)
    location_info = geoip_service.get_location(client_ip)

    logger.info(f" 客户端IP: {client_ip} -> {location_info.get('country')}/{location_info.get('city')}")

    #  v7.201: 使用统一的用户标识获取函数
    actual_user_id = _server.get_user_identifier(current_user)
    username = actual_user_id
    display_name = current_user.get("name") or current_user.get("display_name") or username
    logger.info(f" JWT认证用户: {username} ({display_name})")

    #  v7.110: 添加模式使用统计日志
    logger.info(f" [模式统计] 用户 {actual_user_id} " f"选择 {analysis_request.analysis_mode} 模式")

    print(f"运行模式: Dynamic Mode")

    # 输入守卫：空字符串直接拒绝（避免创建无意义会话）
    if not analysis_request.user_input or not analysis_request.user_input.strip():
        raise HTTPException(status_code=400, detail="requirement/user_input 不能为空")

    sm = await _get_session_manager()

    #  v7.189: 生成纯随机session_id（analysis前缀，不包含用户ID）
    session_id = f"analysis-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:12]}"
    print(f"生成 Session ID: {session_id}")

    #  使用 Redis 创建会话
    session_data = {
        "session_id": session_id,
        "user_id": actual_user_id,  #  v7.130: 真实用户ID
        "user_input": analysis_request.user_input,
        "mode": "dynamic",
        "analysis_mode": analysis_request.analysis_mode,  #  v7.39: 分析模式
        "status": "initializing",
        "progress": 0.0,
        "events": [],
        "interrupt_data": None,
        "current_node": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "metadata": {  #  添加元数据
            "client_ip": client_ip,
            "location": location_info.get("city", "未知"),
            "geo_info": location_info,
            "user_agent": request.headers.get("User-Agent", ""),
        },
    }

    #  v7.130: 添加用户详细信息（如果有JWT认证）
    if username:
        session_data["username"] = username
    if display_name:
        session_data["display_name"] = display_name

    await sm.create(session_id, session_data)

    #  v7.120 P1: 使缓存失效
    sessions_cache.invalidate(f"sessions:{actual_user_id}")

    #  v7.129: 初始化trace追踪
    from ..core.trace_context import TraceContext

    trace_id = TraceContext.init_trace(session_id)
    logger.info(f" 会话状态已初始化（Redis）| Trace: {trace_id}")

    #  v7.129 Week2 P1: 初始化工具权限设置并推送到前端
    from ..services.tool_factory import ToolFactory

    # 定义默认工具权限配置
    #  v7.154: ragflow_kb 已废弃，全部替换为 milvus_kb
    default_tool_settings = {
        "V2": {
            "enable_search": False,
            "available_tools": ["milvus_kb"],
            "recommended": [],
            "description": "设计总监仅使用内部知识库（Milvus），避免外部搜索干扰创意判断",
        },
        "V3": {
            "enable_search": True,
            "available_tools": ["bocha_search", "tavily_search", "milvus_kb"],
            "recommended": ["bocha_search", "tavily_search"],
            "description": "叙事专家可使用中文+国际搜索+内部知识库（Milvus）",
        },
        "V4": {
            "enable_search": True,
            "available_tools": ["bocha_search", "tavily_search", "arxiv_search", "milvus_kb"],
            "recommended": ["tavily_search", "arxiv_search"],
            "description": "设计研究员拥有全部搜索工具权限",
        },
        "V5": {
            "enable_search": True,
            "available_tools": ["bocha_search", "tavily_search", "milvus_kb"],
            "recommended": ["bocha_search", "tavily_search"],
            "description": "场景专家可使用中文+国际搜索+内部知识库（Milvus）",
        },
        "V6": {
            "enable_search": True,
            "available_tools": ["bocha_search", "tavily_search", "arxiv_search", "milvus_kb"],
            "recommended": ["tavily_search", "arxiv_search"],
            "description": "总工程师拥有全部搜索工具权限",
        },
    }

    # 广播工具权限配置到前端
    await _server.broadcast_to_websockets(
        session_id,
        {
            "type": "tool_permissions_initialized",
            "tool_settings": default_tool_settings,
            "message": "工具权限系统已初始化",
            "trace_id": trace_id,
        },
    )
    logger.info(f" [v7.129] 已广播工具权限配置到前端 | Trace: {trace_id}")

    # 在后台执行工作流
    print(f" 添加后台任务...")
    background_tasks.add_task(run_workflow_async, session_id, analysis_request.user_input)

    print(f" 后台任务已添加，返回响应\n")

    return SessionResponse(session_id=session_id, status="pending", message="分析已开始，请使用 session_id 查询状态")


# ========================================================================
#  v7.155: 多模态视觉参考辅助函数
# ========================================================================


def _generate_global_style_anchor(visual_references: List[Dict[str, Any]]) -> str:
    """
     v7.155: 从所有视觉参考中生成全局风格锚点

    将多张参考图的风格特征合并为统一的风格锚点，
    用于确保全流程输出风格一致性。

    Args:
        visual_references: 视觉参考列表

    Returns:
        风格锚点字符串，如 "北欧简约, 暖白色, 原木, 温馨舒适"
    """
    if not visual_references:
        return ""

    all_styles = []
    all_colors = []
    all_materials = []
    all_atmospheres = []

    for ref in visual_references:
        features = ref.get("structured_features", {})
        all_styles.extend(features.get("style_keywords", []))
        all_colors.extend(features.get("dominant_colors", []))
        all_materials.extend(features.get("materials", []))
        atmosphere = features.get("mood_atmosphere", "")
        if atmosphere:
            all_atmospheres.append(atmosphere)

    # 去重并取前几个（保持顺序）
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

    unique_styles = unique_list(all_styles, 3)
    unique_colors = unique_list(all_colors, 2)
    unique_materials = unique_list(all_materials, 2)

    # 组合风格锚点
    anchor_parts = unique_styles + unique_colors + unique_materials
    if all_atmospheres:
        # 取第一个氛围描述的关键词
        first_atmosphere = all_atmospheres[0]
        if len(first_atmosphere) <= 10:
            anchor_parts.append(first_atmosphere)

    return ", ".join(anchor_parts) if anchor_parts else ""


@router.post("/api/analysis/start-with-files", response_model=SessionResponse)
async def start_analysis_with_files(
    background_tasks: BackgroundTasks,  #  修复：移到前面，移除默认值
    user_input: str = Form(default=""),
    requirement: str = Form(default=""),  # 兼容旧前端字段名
    user_id: str = Form(default="web_user"),
    analysis_mode: str = Form(default="normal"),  #  v7.39: 分析模式
    file_metadata: str = Form(default="[]"),  #  v7.157: 文件元数据JSON
    files: List[UploadFile] = File(default=[]),
    current_user: dict = Depends(_server.get_current_user),  #  v7.158: 强制JWT认证，禁止未登录访问
):
    """
     v3.7: 支持多模态输入的分析接口

    接受文本 + 多个文件（PDF, TXT, 图片）

     v7.39: 支持 analysis_mode 参数
    - normal: 深度思考模式，集中生成1张概念图
    - deep_thinking: 深度思考pro模式，每个专家都生成对应的概念图

     v7.157: 支持 file_metadata 参数
    - 包含每个文件的分类标签和自定义描述
    - JSON格式: [{"filename": "xxx.jpg", "categories": ["color", "style"], "custom_description": "..."}]

     v7.350: 文件上传模式限制
    - normal: 禁止文件上传
    - deep_thinking: 允许文件上传

    Args:
        user_input: 用户输入的文本描述
        user_id: 用户ID
        analysis_mode: 分析模式 (normal/deep_thinking)
        file_metadata: 文件元数据JSON字符串
        files: 上传的文件列表
        background_tasks: 后台任务管理器

    Returns:
        会话响应
    """
    logger.info(f"\n 收到多模态分析请求")
    logger.info(f"用户输入: {user_input[:100] if user_input else '(无文本)'}...")
    logger.info(f"分析模式: {analysis_mode}")  #  v7.39
    logger.info(f"文件数量: {len(files)}")

    #  v7.350: 验证文件上传是否被允许
    from intelligent_project_analyzer.utils.mode_config import get_file_upload_config

    file_upload_config = get_file_upload_config(analysis_mode)
    if files and not file_upload_config.get("enabled", False):
        logger.warning(f"️ [v7.350] 模式 '{analysis_mode}' 不支持文件上传，拒绝请求")
        raise HTTPException(status_code=400, detail=f"当前模式 '{analysis_mode}' 不支持文件上传功能。如需上传文件，请切换到深度思考pro模式。")

    if len(files) > file_upload_config.get("max_files", 0):
        logger.warning(f"️ [v7.350] 文件数量 {len(files)} 超过限制 {file_upload_config['max_files']}")
        raise HTTPException(status_code=400, detail=f"文件数量超过限制。当前模式最多允许上传 {file_upload_config['max_files']} 个文件。")

    #  v7.157: 解析文件元数据
    try:
        import json

        file_metadata_list = json.loads(file_metadata) if file_metadata else []
        logger.info(f" [v7.157] 文件元数据: {len(file_metadata_list)} 条")
    except json.JSONDecodeError as e:
        logger.warning(f"️ [v7.157] 文件元数据解析失败: {e}")
        file_metadata_list = []

    # 构建文件名到元数据的映射
    metadata_by_filename = {m.get("filename"): m for m in file_metadata_list}

    #  v7.201: 使用统一的用户标识获取函数
    actual_user_id = _server.get_user_identifier(current_user)
    username = actual_user_id
    display_name = current_user.get("name") or current_user.get("display_name") or username
    logger.info(f" JWT认证用户: {username} ({display_name})")

    # 1. 验证输入
    if not user_input.strip() and not files:
        raise HTTPException(status_code=400, detail="请提供文本输入或上传文件")

    # 2. 生成会话 ID（使用真实用户标识）
    session_id = f"{actual_user_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    logger.info(f"生成 Session ID: {session_id}")

    # 3. 保存并处理文件
    file_contents = []
    attachment_metadata = []
    visual_references = []  #  v7.155: 收集视觉参考

    for file in files:
        try:
            # 验证文件大小 (10MB限制)
            content = await file.read()
            file_size = len(content)

            if file_size > 10 * 1024 * 1024:
                logger.warning(f"️ 文件过大，跳过: {file.filename} ({file_size} bytes)")
                continue

            # 保存文件
            file_path = await file_processor.save_file(
                file_content=content, filename=file.filename, session_id=session_id
            )

            #  v7.157: 获取该文件的元数据
            file_meta = metadata_by_filename.get(file.filename, {})
            categories = file_meta.get("categories", [])
            custom_description = file_meta.get("custom_description", "")
            is_image = file_meta.get(
                "is_image", file.content_type in ["image/png", "image/jpeg", "image/jpg", "image/webp"]
            )

            #  v7.155: 判断是否为图片，使用增强版提取
            if file.content_type in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
                # 使用增强版图片提取（提取结构化视觉特征）
                extracted_content = await file_processor.extract_image_enhanced(file_path)

                #  v7.157: 根据用户选择的分类确定参考类型
                # 优先级: style > layout > color > general
                reference_type = "general"
                if "style" in categories:
                    reference_type = "style"
                elif "layout" in categories:
                    reference_type = "layout"
                elif "color" in categories:
                    reference_type = "color"

                #  v7.156: 收集视觉参考（使用相对路径 + 持久化特征，性能优化）
                # 相对路径格式: {session_id}/{filename} - 容器/分布式部署兼容
                relative_path = f"{session_id}/{file_path.name}"

                visual_references.append(
                    {
                        "file_path": str(file_path),  # 绝对路径（本地快速访问）
                        "relative_path": relative_path,  # 相对路径（持久化/部署兼容）
                        "width": extracted_content.get("width"),
                        "height": extracted_content.get("height"),
                        "format": extracted_content.get("format"),
                        "vision_analysis": extracted_content.get("vision_analysis", ""),
                        "structured_features": extracted_content.get("structured_features", {}),
                        "user_description": custom_description if custom_description else None,  #  v7.157
                        "reference_type": reference_type,  #  v7.157
                        "categories": categories,  #  v7.157: 保存完整分类列表
                        "cached_at": datetime.now().isoformat(),  #  v7.156: 缓存时间戳
                    }
                )
                logger.info(f"️ [v7.157] 视觉参考已提取: {file.filename} | 类型: {reference_type} | 分类: {categories}")
            else:
                # 非图片文件使用原有逻辑
                extracted_content = await file_processor.extract_content(
                    file_path=file_path, content_type=file.content_type
                )

            file_contents.append(extracted_content)

            # 保存元数据
            attachment_metadata.append(
                {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "size": file_size,
                    "path": str(file_path),
                    "extracted_summary": extracted_content.get("summary", ""),
                    "extraction_error": extracted_content.get("error", None),
                    "categories": categories,  #  v7.157
                    "custom_description": custom_description,  #  v7.157
                }
            )

            logger.info(f" 文件处理完成: {file.filename} - {extracted_content.get('summary', '')}")

        except Exception as e:
            logger.error(f" 文件处理失败: {file.filename} - {str(e)}")
            attachment_metadata.append({"filename": file.filename, "content_type": file.content_type, "error": str(e)})

    #  v7.155: 生成全局风格锚点
    visual_style_anchor = _generate_global_style_anchor(visual_references) if visual_references else None
    if visual_style_anchor:
        logger.info(f" [v7.155] 全局风格锚点: {visual_style_anchor}")

    # 4. 合并用户输入和文件内容
    # 兼容：如果前端传的是 requirement 字段，则映射到 user_input
    effective_user_input = user_input or requirement
    if not effective_user_input and not files:
        raise HTTPException(status_code=400, detail="user_input/requirement 或 files 至少提供一个")

    combined_input = build_combined_input(effective_user_input, file_contents)

    logger.info(f" 内容合并完成: 最终输入长度 {len(combined_input)} 字符")

    # 5. 创建会话（增强状态）
    sm = await _get_session_manager()
    session_data = {
        "session_id": session_id,
        "user_id": actual_user_id,  #  v7.130: 真实用户ID
        "user_input": effective_user_input,  # 原始文本
        "combined_input": combined_input,  #  合并后的输入
        "attachments": attachment_metadata,  #  附件元数据
        "mode": "dynamic",
        "analysis_mode": analysis_mode,  #  v7.39: 分析模式
        "status": "initializing",
        "progress": 0.0,
        "events": [],
        "interrupt_data": None,
        "current_node": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        #  v7.155: 多模态视觉参考
        "visual_references": visual_references if visual_references else None,
        "visual_style_anchor": visual_style_anchor,
    }

    #  v7.130: 添加用户详细信息（如果有JWT认证）
    if username:
        session_data["username"] = username
    if display_name:
        session_data["display_name"] = display_name

    await sm.create(session_id, session_data)

    logger.info(f" 会话状态已初始化（Redis + 文件）")

    # 6. 启动工作流（传入 combined_input）
    background_tasks.add_task(run_workflow_async, session_id, combined_input)  #  使用增强后的输入

    logger.info(f" 后台任务已添加\n")

    return SessionResponse(session_id=session_id, status="pending", message=f"分析已开始，已接收 {len(files)} 个文件")


# ========================================================================
#  v7.155: 视觉参考描述接口
# ========================================================================


class VisualReferenceDescriptionRequest(BaseModel):
    """视觉参考描述请求"""

    reference_index: int = Field(..., description="参考图索引（从0开始）")
    description: str = Field(..., description="用户描述")
    reference_type: str = Field(default="general", description="参考类型: style|layout|color|general")


@router.post("/api/analysis/{session_id}/visual-reference/describe")
async def add_visual_reference_description(
    session_id: str,
    request: VisualReferenceDescriptionRequest,
):
    """
     v7.155: 用户为上传的参考图追加描述

    允许用户在上传图片后补充说明这张图片的用途和参考意图，
    例如："保留这个风格，但改成蓝色调"

    Args:
        session_id: 会话ID
        request: 包含 reference_index, description, reference_type

    Returns:
        更新后的视觉参考列表
    """
    logger.info(f"️ [v7.155] 添加视觉参考描述: session={session_id}, index={request.reference_index}")

    sm = await _get_session_manager()
    session = await sm.get(session_id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    visual_refs = session.get("visual_references", [])

    if not visual_refs:
        raise HTTPException(status_code=400, detail="No visual references in this session")

    if request.reference_index >= len(visual_refs):
        raise HTTPException(
            status_code=400, detail=f"Invalid reference index: {request.reference_index}, max is {len(visual_refs) - 1}"
        )

    # 更新描述
    visual_refs[request.reference_index]["user_description"] = request.description
    visual_refs[request.reference_index]["reference_type"] = request.reference_type

    # 保存更新
    await sm.update(session_id, {"visual_references": visual_refs})

    logger.info(f" [v7.155] 视觉参考描述已更新: index={request.reference_index}, type={request.reference_type}")

    return {
        "status": "success",
        "message": f"Description added to reference {request.reference_index}",
        "visual_references": visual_refs,
    }


@router.get("/api/analysis/status/{session_id}", response_model=AnalysisStatus)
async def get_analysis_status(
    session_id: str,
    extend_ttl: bool = False,
    include_history: bool = Query(False, description="是否包含完整history（影响性能）"),  #  v7.120 P1
):
    """
    获取分析状态

    查询指定会话的当前状态和进度

    Args:
        session_id: 会话ID
        extend_ttl: 是否延长TTL（默认False，避免频繁轮询时过度续期）
        include_history: 是否包含完整history（默认False，减少序列化开销） v7.120 P1优化

     v7.120 P1优化: 默认不返回history字段，预期性能提升: 2.03s→0.5s
     性能优化: 添加Redis缓存机制（30秒TTL），预期响应时间: <500ms
    """
    import time

    start_time = time.time()

    #  使用 Redis 读取会话（带缓存）
    sm = await _get_session_manager()
    session = await sm.get_status_with_cache(session_id, include_history=include_history)

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    #  Fix 2.5: 仅在明确请求时才续期TTL（减少95% Redis负载）
    if extend_ttl:
        await sm.extend_ttl(session_id)

    #  v7.119: 检查 waiting_for_input 状态的超时
    if session["status"] == "waiting_for_input":
        interrupt_timestamp = session.get("interrupt_timestamp")
        if interrupt_timestamp:
            elapsed_minutes = (time.time() - interrupt_timestamp) / 60

            # 超过15分钟发送WebSocket提醒
            if elapsed_minutes > 15 and not session.get("timeout_reminder_sent"):
                logger.warning(f" Session {session_id} 等待用户输入已超过15分钟")
                await _server.broadcast_to_websockets(
                    session_id,
                    {
                        "type": "status_update",
                        "status": "waiting_for_input",
                        "message": "️ 系统已等待您的确认超过15分钟，请及时响应",
                        "detail": "超时提醒",
                    },
                )
                await sm.update(session_id, {"timeout_reminder_sent": True})

            # 超过30分钟自动标记为timeout
            if elapsed_minutes > 30:
                logger.error(f" Session {session_id} 等待用户输入超时（30分钟）")
                await sm.update(session_id, {"status": "timeout", "error": "用户未在30分钟内响应，会话已超时", "detail": "会话超时"})
                session["status"] = "timeout"
                session["error"] = "用户未在30分钟内响应，会话已超时"

    # 性能监控日志
    elapsed_ms = (time.time() - start_time) * 1000
    if elapsed_ms > 1000:
        logger.warning(f" 慢请求检测: GET /api/analysis/status/{session_id} 耗时 {elapsed_ms:.0f}ms")
    else:
        logger.debug(f" 状态查询完成: {session_id}, 耗时 {elapsed_ms:.0f}ms")

    return AnalysisStatus(
        session_id=session_id,
        status=session["status"],
        current_stage=session.get("current_node"),
        detail=session.get("detail"),  #  新增：返回详细信息
        progress=session["progress"],
        history=session.get("history", []) if include_history else [],  #  v7.120 P1: 按需返回
        interrupt_data=session.get("interrupt_data"),
        error=session.get("error"),
        traceback=session.get("traceback"),  # 返回traceback用于调试
        rejection_message=session.get("rejection_message"),  #  返回拒绝提示
        user_input=session.get("user_input"),  #  v7.37.7: 返回用户原始输入
        flow_route_name=session.get("flow_route_name"),
        flow_route_decision=session.get("flow_route_decision"),
        flow_route_reason_codes=session.get("flow_route_reason_codes"),
        routing_scores=session.get("routing_scores"),
        active_steps=session.get("active_steps"),
    )


@router.post("/api/analysis/resume", response_model=SessionResponse)
async def resume_analysis(request: ResumeRequest, background_tasks: BackgroundTasks):
    """
    恢复分析

    在 interrupt 后提供用户输入并继续执行
    """
    session_id = request.session_id

    sm = await _get_session_manager()

    #  获取活跃会话列表
    active_sessions = await sm.list_all_sessions()

    logger.info(f" 收到 resume 请求: session_id={session_id}")
    logger.info(f"   resume_value: {request.resume_value}")
    logger.info(f"   当前活跃会话: {active_sessions}")

    #  检查会话是否存在
    session = await sm.get(session_id)
    if not session:
        logger.error(f" 会话不存在: {session_id}")
        logger.error(f"   可用会话: {active_sessions}")
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

    # 兼容：历史数据/旧实现可能使用 interrupted 表示等待用户输入
    if session.get("status") not in {"waiting_for_input", "interrupted"}:
        raise HTTPException(status_code=400, detail=f"会话状态不正确: {session.get('status')}")

    # 获取工作流
    workflow = workflows.get(session_id)
    if not workflow:
        logger.error(f" 工作流实例不存在: {session_id}")
        logger.error(f"   这通常发生在服务器重启后，工作流无法继续")
        logger.error(f"   建议：使用持久化的检查点存储（如SqliteSaver）而非MemorySaver")

        #  DEV_MODE：测试/本地调试时，不用 410 直接阻塞（单测只关注 API 是否可用）
        if DEV_MODE:
            # DEV_MODE 下尽量不依赖 Redis 分布式锁更新（测试环境 mock redis_client 不一定支持 Lock）
            try:
                await sm.update(session_id, {"status": "running", "interrupt_data": None})
            except Exception:
                pass
            return SessionResponse(
                session_id=session_id, status="processing", message="恢复请求已接收（DEV_MODE 下跳过 workflow 实例校验）"
            )

        raise HTTPException(
            status_code=410, detail="工作流已失效，请重新开始分析。如果问题持续出现，请联系管理员。"  # 410 Gone - resource no longer available
        )

    # 更新状态
    logger.debug(f"[DEBUG] Resume request for session {session_id}")
    logger.debug(f"[DEBUG] resume_value type: {type(request.resume_value)}")
    logger.debug(f"[DEBUG] resume_value content: {request.resume_value}")

    #  v7.119: 立即更新 Redis 状态为 running，清除超时相关字段
    await sm.update(
        session_id,
        {
            "status": "running",
            "interrupt_data": None,
            "interrupt_timestamp": None,  # 清除超时时间戳
            "timeout_reminder_sent": None,  # 清除提醒标记
        },
    )

    # 更新本地 session 对象（虽然 continue_workflow 使用的是闭包中的 session，但为了保险起见）
    session["status"] = "running"
    session["interrupt_data"] = None

    # 继续执行工作流
    async def continue_workflow():
        #  导入GraphRecursionError
        from langgraph.errors import GraphRecursionError

        try:
            config = {"configurable": {"thread_id": session_id}, "recursion_limit": 100}  # 增加递归限制，默认是25

            logger.info(f"[DEBUG] Resuming workflow with Command(resume={request.resume_value})")

            # 使用 Command(resume) 继续执行
            # 不指定 stream_mode，使用默认模式以正确接收 __interrupt__
            async for chunk in workflow.graph.astream(Command(resume=request.resume_value), config):
                logger.debug(f"[DEBUG] Resume stream chunk keys: {chunk.keys()}")

                #  更新当前节点和详细信息
                for node_name, node_output in chunk.items():
                    if node_name != "__interrupt__":
                        session["current_node"] = node_name
                        detail = ""
                        if isinstance(node_output, dict):
                            if "current_stage" in node_output:
                                detail = node_output["current_stage"]
                            elif "status" in node_output:
                                detail = node_output["status"]
                        session["detail"] = detail
                        logger.debug(f"[PROGRESS] 节点: {node_name}, 详情: {detail}")

                session["events"].append(chunk)
                #  v7.21: 节点映射与 main_workflow.py 对齐
                current_node = session.get("current_node", "")
                node_progress_map = {
                    "unified_input_validator_initial": 0.05,
                    "unified_input_validator_secondary": 0.10,
                    "requirements_analyst": 0.15,
                    "feasibility_analyst": 0.20,
                    "calibration_questionnaire": 0.25,
                    "questionnaire_summary": 0.35,  #  v7.151: 替换 requirements_confirmation
                    "project_director": 0.40,
                    "role_task_unified_review": 0.45,
                    "quality_preflight": 0.50,
                    "batch_executor": 0.55,
                    "agent_executor": 0.70,
                    "batch_aggregator": 0.75,
                    "batch_router": 0.76,
                    "batch_strategy_review": 0.78,
                    "detect_challenges": 0.80,
                    "analysis_review": 0.85,
                    "result_aggregator": 0.90,
                    "report_guard": 0.95,
                    "pdf_generator": 0.98,
                }
                session["progress"] = node_progress_map.get(current_node, min(0.9, len(session["events"]) * 0.1))

                #  确保 Redis 和 WebSocket 原子性同步
                # 1. 先更新 Redis
                await _server.session_manager.update(
                    session_id,
                    {
                        "status": session["status"],
                        "progress": session["progress"],
                        "current_node": current_node,
                        "detail": session.get("detail"),
                        "events": session["events"],
                    },
                )

                # 2. 基于最新 Redis 数据广播 WebSocket
                updated_session = await _server.session_manager.get(session_id)
                if updated_session:
                    await _server.broadcast_to_websockets(
                        request.session_id,
                        {
                            "type": "status_update",
                            "status": updated_session["status"],
                            "progress": updated_session["progress"],
                            "current_node": updated_session.get("current_node"),
                            "detail": updated_session.get("detail"),
                        },
                    )

                # 检查是否又有 interrupt - interrupt 作为独立的 chunk 返回
                if "__interrupt__" in chunk:
                    # 提取 interrupt 数据
                    interrupt_tuple = chunk["__interrupt__"]
                    # interrupt_tuple 是一个元组，第一个元素是 Interrupt 对象
                    if interrupt_tuple:
                        interrupt_obj = interrupt_tuple[0] if isinstance(interrupt_tuple, tuple) else interrupt_tuple

                        # 提取 interrupt 的 value
                        interrupt_value = None
                        if hasattr(interrupt_obj, "value"):
                            interrupt_value = interrupt_obj.value
                        else:
                            interrupt_value = interrupt_obj

                        session["status"] = "waiting_for_input"
                        session["interrupt_data"] = interrupt_value
                        session["current_node"] = "interrupt"

                        #  广播 interrupt 到 WebSocket
                        await _server.broadcast_to_websockets(
                            request.session_id,
                            {"type": "interrupt", "status": "waiting_for_input", "interrupt_data": interrupt_value},
                        )

                        #  更新 Redis 中的 interrupt 状态
                        await _server.session_manager.update(
                            session_id,
                            {
                                "status": "waiting_for_input",
                                "interrupt_data": interrupt_value,
                                "current_node": "interrupt",
                            },
                        )

                        logger.info(
                            f" 已广播第二个 interrupt 到 WebSocket: {interrupt_value.get('interaction_type', 'unknown') if isinstance(interrupt_value, dict) else type(interrupt_value)}"
                        )
                        return

            # 检查是否有节点错误
            has_error = False
            error_message = None
            for event in session["events"]:
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        if node_output.get("error") or node_output.get("status") == "error":
                            has_error = True
                            error_message = node_output.get("error", f"节点 {node_name} 执行失败")
                            break
                if has_error:
                    break

            # 根据是否有错误设置状态
            if has_error:
                session["status"] = "failed"
                session["error"] = error_message
                logger.error(f"工作流失败: {error_message}")

                #  广播失败状态到 WebSocket
                await _server.broadcast_to_websockets(
                    request.session_id, {"type": "status", "status": "failed", "message": error_message}
                )

                #  更新 Redis 失败状态
                await _server.session_manager.update(session_id, {"status": "failed", "error": error_message})
            else:
                #  v7.146: stream 结束 ≠ 一定完成。
                # 在某些路由缺失/边未连接的情况下，图会提前结束，过去会被误判为 completed 并触发自动归档。
                # 这里通过检查图状态中的批次执行进度 / final_report 来判定是否真的完成。
                #  v7.153: 修复 AsyncSqliteSaver 同步调用错误，使用 aget_state 异步方法
                try:
                    current_state = await workflow.graph.aget_state(config)
                    state_values = getattr(current_state, "values", {}) or {}
                except Exception as state_read_error:
                    logger.warning(f"️ Resume结束后读取graph state失败: {type(state_read_error).__name__}: {state_read_error}")
                    state_values = {}

                total_batches = state_values.get("total_batches", 0) or 0
                completed_batches = state_values.get("completed_batches", []) or []
                state_final_report = state_values.get("final_report")

                # 兼容 completed_batches 非 list 的异常情况
                completed_batch_count = len(completed_batches) if isinstance(completed_batches, list) else 0
                is_batches_completed = (
                    isinstance(total_batches, int)
                    and total_batches > 0
                    and isinstance(completed_batches, list)
                    and completed_batch_count >= total_batches
                )

                #  完成判定：
                # - 若 state 已写入 final_report，则认为完成；
                # - 或者批次已全部完成（total_batches>0 且 completed_batches 覆盖）。
                is_truly_completed = bool(state_final_report) or is_batches_completed

                logger.info(
                    f"[DEBUG] Resume stream finished. is_truly_completed={is_truly_completed}, "
                    f"current_node={session.get('current_node')}, total_batches={total_batches}, "
                    f"completed_batches={completed_batch_count}, has_state_final_report={bool(state_final_report)}"
                )

                if not is_truly_completed:
                    # 视为异常提前结束：不归档、不标 completed，避免误完成。
                    session["status"] = "failed"
                    session["error"] = "工作流提前结束（未检测到最终完成条件）。" "可能原因：路由缺失/边未连接/节点未按预期返回 Command(goto=...)。"

                    await _server.broadcast_to_websockets(
                        request.session_id,
                        {
                            "type": "status",
                            "status": "failed",
                            "message": session["error"],
                        },
                    )

                    await _server.session_manager.update(
                        session_id,
                        {
                            "status": "failed",
                            "error": session["error"],
                            "detail": session.get("detail"),
                        },
                    )
                    logger.error(
                        f" Resume流程提前结束且未满足完成条件: session_id={session_id}, "
                        f"current_node={session.get('current_node')}, total_batches={total_batches}, "
                        f"completed_batches={completed_batch_count}"
                    )
                    return

                session["status"] = "completed"
                session["progress"] = 1.0

                # 提取最终报告（优先使用 state 中的 final_report）
                final_report = state_final_report
                if not final_report:
                    for event in session["events"]:
                        for node_name, node_output in event.items():
                            if isinstance(node_output, dict) and "final_report" in node_output:
                                final_report = node_output["final_report"]
                                break
                        if final_report:
                            break

                session["final_report"] = final_report or "分析完成"

                #  广播完成状态到 WebSocket
                await _server.broadcast_to_websockets(
                    request.session_id,
                    {
                        "type": "status",
                        "status": "completed",
                        "progress": 1.0,
                        "message": "分析完成",
                        "final_report": session.get("final_report"),
                    },
                )

                #  v7.153: 先同步 checkpoint 数据到 Redis，确保 final_report 和 aggregated_result 完整
                try:
                    sync_success = await _server.sync_checkpoint_to_redis(session_id)
                    if sync_success:
                        logger.info(f" [v7.153] checkpoint 数据已同步到 Redis（resume流程完成）")
                    else:
                        logger.warning(f"️ [v7.153] checkpoint 同步未成功，使用 state_values 中的 final_report")
                        # 同步失败时，至少确保 final_report 被保存（从 state_values 获取）
                        if state_final_report and isinstance(state_final_report, dict):
                            await _server.session_manager.update(session_id, {"final_report": state_final_report})
                except Exception as sync_error:
                    logger.error(f" [v7.153] checkpoint 同步异常: {sync_error}")

                #  更新 Redis 完成状态
                await _server.session_manager.update(session_id, {"status": "completed", "progress": 1.0})

                #  v3.6新增: 自动归档完成的会话（永久保存）
                if _server.archive_manager:
                    try:
                        #  v7.145: 归档前同步 checkpoint 数据到 Redis
                        sync_success = await _server.sync_checkpoint_to_redis(session_id)
                        if sync_success:
                            logger.info(f" [v7.145] checkpoint 数据已同步（resume流程），准备归档")

                        # 获取完整会话数据
                        final_session = await _server.session_manager.get(session_id)
                        if final_session:
                            await _server.archive_manager.archive_session(
                                session_id=session_id, session_data=final_session, force=False
                            )
                            logger.info(f" 会话已自动归档（永久保存）: {session_id}")
                    except Exception as archive_error:
                        logger.warning(f"️ 自动归档失败（不影响主流程）: {archive_error}")

                logger.info(f" 已广播完成状态到 WebSocket: {request.session_id}")

        #  处理递归限制错误
        except GraphRecursionError as e:
            logger.warning(f"️ Resume时达到递归限制！会话: {session_id}")
            logger.info(" 尝试获取最佳结果...")

            #  v7.153: 修复 AsyncSqliteSaver 同步调用错误，使用 aget_state 异步方法
            try:
                current_state = await workflow.graph.aget_state(config)
                state_values = current_state.values

                best_result = state_values.get("best_result")
                if best_result:
                    logger.info(f" 找到最佳结果（评分{state_values.get('best_score', 0):.1f}）")
                    state_values["agent_results"] = best_result
                else:
                    logger.warning("️ 未找到最佳结果，使用当前结果")

                session["status"] = "completed"
                session["progress"] = 1.0
                session["final_report"] = "分析已完成（达到递归限制）"

                #  广播完成状态到 WebSocket
                await _server.broadcast_to_websockets(
                    session_id, {"type": "status", "status": "completed", "progress": 1.0, "message": "分析已完成（达到递归限制）"}
                )
                logger.info(f" 已广播完成状态到 WebSocket (递归限制): {session_id}")
                session["metadata"] = {"forced_completion": True, "best_score": state_values.get("best_score", 0)}

            except Exception as state_error:
                logger.error(f" 获取状态失败: {state_error}")
                session["status"] = "failed"
                session["error"] = f"达到递归限制: {str(e)}"

        except Exception as e:
            session["status"] = "failed"
            session["error"] = str(e)
            import traceback

            session["traceback"] = traceback.format_exc()
            logger.error(f"[ERROR] Resume workflow failed: {e}")
            logger.error(f"[ERROR] Traceback:\n{traceback.format_exc()}")

    background_tasks.add_task(continue_workflow)

    return SessionResponse(session_id=session_id, status="resumed", message="分析已恢复")


@router.post("/api/analysis/followup", response_model=SessionResponse)
async def submit_followup_question(
    session_id: str = Form(...),
    question: str = Form(...),
    requires_analysis: bool = Form(True),
    image: Optional[UploadFile] = File(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    提交追问（支持持续对话 + 图片上传）

     v3.11 重大改造：
    - 不再创建新会话，在原会话上追加对话历史
    - 支持无限轮次的连续追问
    - 支持"记忆全部"模式（智能上下文管理）
    - 对话历史持久化到Redis

     v7.108 新增：
    - 支持图片上传（multipart/form-data）
    - 图片永久保存到 data/followup_images/{session_id}/
    - 自动生成缩略图（400px）
    - 集成 Vision API 分析图片内容

    与 /api/analysis/resume 的区别:
    - resume: 用于 waiting_for_input 状态的中断恢复
    - followup: 用于 completed 状态的后续追问
    """
    logger.info(f" 收到追问请求: session_id={session_id}")
    logger.info(f"   问题: {question}")
    logger.info(f"   需要分析: {requires_analysis}")
    logger.info(f"   包含图片: {image is not None}")

    # 检查会话是否存在
    session = await _server.session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

    # 允许 completed 状态的会话进行追问
    if session["status"] not in ["completed", "waiting_for_input"]:
        raise HTTPException(status_code=400, detail=f"无法追问，会话状态: {session['status']}（只能对已完成或等待输入的会话追问）")

    #  关键改变：不创建新会话，直接在原会话上追问
    logger.info(f" 在原会话上追问（不创建新会话）")

    #  使用后台任务处理追问
    async def handle_followup():
        try:
            # 更新会话状态
            await _server.session_manager.update(session_id, {"status": "processing_followup", "detail": "正在思考回答..."})

            #  获取追问历史
            history_data = await _server.followup_history_manager.get_history(session_id, limit=None)  # 获取全部
            next_turn_id = len(history_data) + 1
            logger.info(f" 当前对话历史: {len(history_data)} 轮")

            #  v7.108: 处理图片上传（如果有）
            image_metadata = None
            enhanced_question = question

            if image is not None:
                try:
                    from pathlib import Path

                    from intelligent_project_analyzer.services.file_processor import FileProcessor
                    from intelligent_project_analyzer.services.followup_image_storage_manager import (
                        FollowupImageStorageManager,
                    )

                    logger.info(f" 开始处理图片: {image.filename}")

                    # 保存图片（原图 + 缩略图）
                    image_metadata = await FollowupImageStorageManager.save_image(
                        image_file=image, session_id=session_id, turn_id=next_turn_id
                    )
                    logger.info(f" 图片已保存: {image_metadata['stored_filename']}")

                    # Vision API 分析（使用 FileProcessor）
                    try:
                        file_processor = FileProcessor(enable_vision_api=True)
                        image_path = Path(f"data/followup_images/{session_id}/{image_metadata['stored_filename']}")

                        vision_result = await file_processor._extract_image(image_path)
                        vision_analysis = (
                            vision_result.get("text", "").split("## AI视觉分析")[-1].strip()
                            if "## AI视觉分析" in vision_result.get("text", "")
                            else ""
                        )

                        image_metadata["vision_analysis"] = vision_analysis
                        logger.info(f" Vision API 分析完成: {len(vision_analysis)} 字符")

                    except Exception as e:
                        logger.warning(f"️ Vision API 分析失败: {e}")
                        image_metadata["vision_analysis"] = ""

                    # 增强问题文本（拼接 Vision 分析）
                    if image_metadata.get("vision_analysis"):
                        enhanced_question = f"""{question}

[图片: {image_metadata['original_filename']}]
AI分析: {image_metadata['vision_analysis']}
"""

                except Exception as e:
                    logger.error(f" 图片处理失败: {e}")
                    import traceback

                    traceback.print_exc()
                    # 不阻塞追问，继续处理

            #  v7.15: 使用 FollowupAgent (LangGraph)
            agent = FollowupAgent()

            # 构建上下文
            parent_session = await _server.session_manager.get(session_id)
            aggregated_results = parent_session.get("aggregated_results", {})
            agent_results = parent_session.get("agent_results", {})
            structured_requirements = parent_session.get("structured_requirements", {})
            original_input = parent_session.get("user_input", "")

            # 如果没有结构化数据，尝试从 final_report 解析
            final_report = parent_session.get("final_report")
            if isinstance(final_report, dict) and not aggregated_results:
                aggregated_results = final_report

            #  v7.15: 构建 report_context (新格式)
            report_context = {
                "final_report": aggregated_results if isinstance(aggregated_results, dict) else {},
                "agent_results": agent_results if isinstance(agent_results, dict) else {},
                "requirements": structured_requirements if isinstance(structured_requirements, dict) else {},
                "user_input": original_input,
            }

            #  v7.15: 调用 FollowupAgent（使用增强后的问题）
            logger.info(f" 调用 FollowupAgent (LangGraph)（历史轮次: {len(history_data)}）")
            result = await agent.answer_question_async(
                question=enhanced_question, report_context=report_context, conversation_history=history_data
            )

            answer = result.get("answer", "抱歉，我无法回答这个问题。")

            #  v7.60.5: 累加追问Token到会话metadata
            from intelligent_project_analyzer.utils.token_utils import extract_tokens_from_result, update_session_tokens

            token_data = extract_tokens_from_result(result)
            if token_data:
                success = await update_session_tokens(
                    _server.session_manager, session_id, token_data, agent_name="followup_qa"
                )
                if success:
                    logger.info(f" [追问Token] 已累加到会话 {session_id}")

            #  保存到追问历史（包含附件）
            attachments = []
            if image_metadata:
                attachments.append({"type": "image", **image_metadata})

            await _server.followup_history_manager.add_turn(
                session_id=session_id,
                question=question,
                answer=answer,
                intent=result.get("intent", "general"),
                referenced_sections=result.get("references", []),
                attachments=attachments,
            )

            # 更新会话状态（保持completed状态）
            await _server.session_manager.update(
                session_id, {"status": "completed", "detail": "追问回答完成", "last_followup_at": datetime.now().isoformat()}
            )

            #  通过WebSocket广播更新（前端实时显示）
            await _server.broadcast_to_websockets(
                session_id,
                {
                    "type": "followup_answer",
                    "turn_id": next_turn_id,
                    "question": question,
                    "answer": answer,
                    "intent": result.get("intent", "general"),
                    "referenced_sections": result.get("references", []),
                    "attachments": attachments,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            logger.info(f" 追问完成: {session_id}, 轮次={next_turn_id}")

        except Exception as e:
            logger.error(f" 追问处理失败: {e}")
            import traceback

            traceback.print_exc()
            await _server.session_manager.update(
                session_id, {"status": "completed", "detail": f"追问失败: {str(e)}"}  # 回到completed状态
            )

            # 广播错误
            await _server.broadcast_to_websockets(session_id, {"type": "followup_error", "error": str(e)})

    # 添加后台任务
    background_tasks.add_task(handle_followup)

    return SessionResponse(session_id=session_id, status="processing", message="追问已提交，正在生成回答...")  #  返回原会话ID，不是新会话


@router.get("/api/analysis/result/{session_id}", response_model=AnalysisResult)
async def get_analysis_result(session_id: str):
    """
    获取分析结果

    获取已完成分析的完整结果
    """
    #  使用 Redis 获取会话
    sm = await _get_session_manager()
    session = await sm.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"分析尚未完成，当前状态: {session['status']}")

    # 兼容：不同版本的会话结构字段名可能不同
    results = session.get("results")
    agent_results = session.get("agent_results")
    final_report = session.get("final_report")
    final_result = session.get("final_result")

    return AnalysisResult(
        session_id=session_id,
        status=session["status"],
        results=results if results is not None else agent_results,
        final_report=final_report if final_report is not None else final_result,
        final_result=final_result,
        agent_results=agent_results,
    )


def _normalize_image_urls(generated_images_by_expert: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
     v7.123: 规范化图片URL字段，确保兼容性

    目的: 修复概念图显示黑色方块问题
    - 旧格式使用 "url" 字段
    - 新格式使用 "image_url" 字段
    - Base64格式直接可用

    确保所有图片数据包含 image_url 字段
    """
    if not generated_images_by_expert:
        return generated_images_by_expert

    logger.debug(" [v7.123] 规范化图片URL字段...")

    for expert_name, expert_data in generated_images_by_expert.items():
        if not isinstance(expert_data, dict):
            continue

        images = expert_data.get("images", [])
        if not isinstance(images, list):
            continue

        for img in images:
            if not isinstance(img, dict):
                continue

            # 如果是Base64 Data URL，保留
            if img.get("image_url", "").startswith("data:"):
                logger.debug(f"   {expert_name}: Base64格式，无需处理")
                continue

            # 如果有url但没有image_url，复制url到image_url
            if "url" in img and "image_url" not in img:
                img["image_url"] = img["url"]
                logger.debug(f"   {expert_name}: 添加image_url字段 (from url)")

            # 如果两者都不存在，标记错误
            if "image_url" not in img and "url" not in img:
                logger.error(f"   {expert_name}: 图片数据缺少URL - {img.get('id', 'unknown')}")
                img["image_url"] = ""  # 设置空值避免前端崩溃

    logger.debug(" [v7.123] 图片URL字段规范化完成")
    return generated_images_by_expert


@router.get("/api/analysis/report/{session_id}", response_model=ReportResponse)
async def get_analysis_report(session_id: str):
    """
    获取分析报告（专门为前端设计的端点）

    返回格式化的报告内容，适配前端 AnalysisReport 类型
    """
    #  使用 Redis 获取会话
    sm = await _get_session_manager()
    session = await sm.get(session_id)

    #  v7.144: 如果 Redis 中没有会话，尝试从归档中获取
    if not session:
        logger.info(f" [v7.144] Redis 中未找到会话 {session_id}，尝试查询归档...")
        if _server.archive_manager:
            try:
                session = await _server.archive_manager.get_archived_session(session_id)
                if session:
                    logger.info(f" [v7.144] 从归档中找到会话 {session_id}")
            except Exception as e:
                logger.error(f" [v7.144] 查询归档失败: {e}")

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"分析尚未完成，当前状态: {session['status']}")

    # 获取报告文本路径
    pdf_path = session.get("pdf_path")
    report_text = ""

    #  v7.144: 修复 PDF 文件读取逻辑 - 读取同名的 .md 或 .txt 文件，而非 PDF 二进制文件
    if pdf_path and os.path.exists(pdf_path):
        try:
            # 尝试读取同名的 .md 文件
            txt_path = pdf_path.replace(".pdf", ".md")
            if not os.path.exists(txt_path):
                # 回退到 .txt 文件
                txt_path = pdf_path.replace(".pdf", ".txt")

            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8") as f:
                    report_text = f.read()
                logger.info(f" [v7.144] 成功读取报告文本文件: {txt_path}")
            else:
                logger.warning(f"️ [v7.144] 未找到报告文本文件: {txt_path}")
                report_text = "报告文件读取失败，请查看结构化数据"
        except Exception as e:
            logger.warning(f"️ 无法读取报告文本文件: {e}")
            #  v7.52.5: 降级方案 - 不使用json.dumps，让FastAPI自动序列化
            # report_text 仅用于简短提示，实际数据在 structured_report 中
            report_text = "报告文件读取失败，请查看结构化数据"
    else:
        #  v7.52.5: 没有文件路径时，返回简短提示
        # structured_report 字段会包含完整数据，不需要json.dumps
        report_text = "请查看结构化报告内容"

    #  解析结构化报告数据
    structured_report = None
    final_report = session.get("final_report", {})

    if isinstance(final_report, dict) and final_report:
        try:
            #  Phase 1.4+ P4 & v7.0: 解析 core_answer（支持新旧两种格式）
            core_answer_data = None
            ca_raw = final_report.get("core_answer")
            if ca_raw and isinstance(ca_raw, dict):
                # 检测是否是 v7.0 格式（有 deliverable_answers 字段）
                if "deliverable_answers" in ca_raw:
                    #  v7.0 格式：直接传递整个结构
                    core_answer_data = ca_raw
                    deliverable_count = len(ca_raw.get("deliverable_answers", []))
                    logger.info(f" [v7.0] 解析到多交付物核心答案: {deliverable_count} 个交付物")
                else:
                    # 旧格式：转换为字典（保持向后兼容）
                    core_answer_data = {
                        "question": ca_raw.get("question", ""),
                        "answer": ca_raw.get("answer", ""),
                        "deliverables": ca_raw.get("deliverables", []),
                        "timeline": ca_raw.get("timeline", ""),
                        "budget_range": ca_raw.get("budget_range", ""),
                        # v7.0 向后兼容字段（为空）
                        "deliverable_answers": [],
                        "expert_support_chain": [],
                    }
                    logger.info(f" 解析到核心答案（旧格式）: {ca_raw.get('answer', '')[:50]}...")

            # 解析 executive_summary
            exec_summary_data = final_report.get("executive_summary", {})
            exec_summary = ExecutiveSummaryResponse(
                project_overview=exec_summary_data.get("project_overview", ""),
                key_findings=exec_summary_data.get("key_findings", []),
                key_recommendations=exec_summary_data.get("key_recommendations", []),
                success_factors=exec_summary_data.get("success_factors", []),
            )

            # 解析 sections（支持数组和字典两种格式）
            sections_data = final_report.get("sections", {})
            sections = []

            #  修复：sections可能是dict（key=section_id）或list格式
            if isinstance(sections_data, dict):
                # 字典格式：{"requirements_analysis": {...}, "design_research": {...}}
                for section_id, section_content in sections_data.items():
                    if isinstance(section_content, dict):
                        #  v7.52.5: content可能是dict或string
                        # 如果是字典，提取主要文本内容，不使用json.dumps
                        content_val = section_content.get("content", "")
                        if isinstance(content_val, dict):
                            # 尝试提取主要文本字段，而不是JSON字符串
                            if "text" in content_val:
                                content_val = content_val["text"]
                            elif "content" in content_val:
                                content_val = content_val["content"]
                            else:
                                # 如果实在需要展示结构化内容，用简短描述
                                content_val = f"[结构化内容: {len(content_val)} 个字段]"

                        raw_confidence = section_content.get("confidence", 0.0)
                        try:
                            confidence_value = float(raw_confidence)
                        except (TypeError, ValueError):
                            confidence_value = 0.0

                        sections.append(
                            ReportSectionResponse(
                                section_id=section_id,
                                title=section_content.get("title", section_id),
                                content=str(content_val) if content_val else "",
                                confidence=confidence_value,
                            )
                        )
            elif isinstance(sections_data, list):
                # 数组格式：[{section_id, title, content, confidence}, ...]
                for s in sections_data:
                    if isinstance(s, dict):
                        #  v7.52.5: content可能是dict或string
                        # 如果是字典，提取主要文本内容，不使用json.dumps
                        content_val = s.get("content", "")
                        if isinstance(content_val, dict):
                            # 尝试提取主要文本字段，而不是JSON字符串
                            if "text" in content_val:
                                content_val = content_val["text"]
                            elif "content" in content_val:
                                content_val = content_val["content"]
                            else:
                                # 如果实在需要展示结构化内容，用简短描述
                                content_val = f"[结构化内容: {len(content_val)} 个字段]"

                        raw_confidence = s.get("confidence", 0.0)
                        try:
                            confidence_value = float(raw_confidence)
                        except (TypeError, ValueError):
                            confidence_value = 0.0

                        sections.append(
                            ReportSectionResponse(
                                section_id=s.get("section_id", ""),
                                title=s.get("title", ""),
                                content=str(content_val) if content_val else "",
                                confidence=confidence_value,
                            )
                        )

            # 使用智能体原始输出补全章节
            sections = _enrich_sections_with_agent_results(sections, session)

            # 解析 comprehensive_analysis（兼容字段名差异）
            comp_data = final_report.get("comprehensive_analysis", {})
            comp_analysis = ComprehensiveAnalysisResponse(
                cross_domain_insights=comp_data.get("cross_domain_insights", []),
                integrated_recommendations=comp_data.get("integrated_recommendations")
                or comp_data.get("integration_recommendations", []),
                risk_assessment=comp_data.get("risk_assessment", []),
                implementation_roadmap=comp_data.get("implementation_roadmap", []),
            )

            # 解析 conclusions（兼容 summary 和 project_analysis_summary）
            concl_data = final_report.get("conclusions", {})
            conclusions = ConclusionsResponse(
                project_analysis_summary=concl_data.get("project_analysis_summary") or concl_data.get("summary", ""),
                next_steps=concl_data.get("next_steps", []),
                success_metrics=concl_data.get("success_metrics", []),
            )

            # 解析 review_feedback
            review_feedback = None
            rf_data = final_report.get("review_feedback")
            if rf_data and isinstance(rf_data, dict):

                def parse_feedback_items(items_data):
                    items = []
                    for item in items_data or []:
                        if isinstance(item, dict):
                            items.append(
                                ReviewFeedbackItemResponse(
                                    issue_id=item.get("issue_id", ""),
                                    reviewer=item.get("reviewer", ""),
                                    issue_type=item.get("issue_type", ""),
                                    description=item.get("description", ""),
                                    response=item.get("response", ""),
                                    status=item.get("status", ""),
                                    priority=str(item.get("priority", "medium")),
                                )
                            )
                    return items

                review_feedback = ReviewFeedbackResponse(
                    red_team_challenges=parse_feedback_items(rf_data.get("red_team_challenges")),
                    blue_team_validations=parse_feedback_items(rf_data.get("blue_team_validations")),
                    judge_rulings=parse_feedback_items(rf_data.get("judge_rulings")),
                    client_decisions=parse_feedback_items(rf_data.get("client_decisions")),
                    iteration_summary=rf_data.get("iteration_summary", ""),
                )

            # 解析 review_visualization
            review_viz = None
            rv_data = final_report.get("review_visualization")
            if rv_data and isinstance(rv_data, dict):
                rounds = []
                for rd in rv_data.get("rounds", []):
                    if isinstance(rd, dict):
                        rounds.append(
                            ReviewRoundDataResponse(
                                round_number=rd.get("round_number", 0),
                                red_score=rd.get("red_score", 0),
                                blue_score=rd.get("blue_score", 0),
                                judge_score=rd.get("judge_score", 0),
                                issues_found=rd.get("issues_found", 0),
                                issues_resolved=rd.get("issues_resolved", 0),
                                timestamp=rd.get("timestamp", ""),
                            )
                        )
                review_viz = ReviewVisualizationResponse(
                    rounds=rounds,
                    final_decision=rv_data.get("final_decision", ""),
                    total_rounds=rv_data.get("total_rounds", 0),
                    improvement_rate=float(rv_data.get("improvement_rate", 0.0)),
                )

            #  解析 challenge_detection（从 session state 中获取）
            challenge_detection = None
            cd_data = session.get("challenge_detection")
            if cd_data and isinstance(cd_data, dict):
                challenges_list = []
                raw_challenges = cd_data.get("challenges", [])
                must_fix_count = 0
                should_fix_count = 0

                for ch in raw_challenges:
                    if isinstance(ch, dict):
                        severity = ch.get("severity", "should-fix")
                        if severity == "must-fix":
                            must_fix_count += 1
                        else:
                            should_fix_count += 1

                        challenges_list.append(
                            ChallengeItemResponse(
                                expert_id=ch.get("expert_id", ""),
                                expert_name=ch.get("expert_name", ch.get("expert_id", "")),
                                challenged_item=ch.get("challenged_item", ""),
                                challenge_type=ch.get("challenge_type", ""),
                                severity=severity,
                                rationale=ch.get("rationale", ""),
                                proposed_alternative=ch.get("proposed_alternative", ""),
                                design_impact=ch.get("design_impact", ""),
                                decision=ch.get("decision", ""),
                            )
                        )

                # 获取处理摘要
                handling_data = session.get("challenge_handling", {})
                handling_summary = handling_data.get("summary", "") if isinstance(handling_data, dict) else ""

                challenge_detection = ChallengeDetectionResponse(
                    has_challenges=cd_data.get("has_challenges", False),
                    total_count=len(challenges_list),
                    must_fix_count=must_fix_count,
                    should_fix_count=should_fix_count,
                    challenges=challenges_list,
                    handling_summary=handling_summary,
                )

                if challenges_list:
                    logger.info(f" 挑战检测: {must_fix_count} must-fix, {should_fix_count} should-fix")

            #  修复：从 session.agent_results 提取 expert_reports（如果 final_report 里没有）
            expert_reports_data = final_report.get("expert_reports", {})
            if not expert_reports_data:
                # 从 agent_results 提取专家报告
                agent_results = session.get("agent_results", {})
                active_agents = session.get("active_agents", [])
                expert_reports_data = {}

                for role_id in active_agents:
                    # 跳过需求分析师和项目总监
                    if role_id in ["requirements_analyst", "project_director"]:
                        continue
                    # 只提取 V2-V6 专家的报告
                    if not any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_"]):
                        continue

                    agent_result = agent_results.get(role_id, {})
                    if agent_result:
                        structured_raw = agent_result.get("structured_data", {})
                        structured_data, validation_warnings = _sanitize_structured_data(structured_raw)
                        content = agent_result.get("content", "")

                        if structured_data and content:
                            payload = OrderedDict()
                            payload["structured_data"] = structured_data
                            payload["narrative_summary"] = content
                            if validation_warnings:
                                payload["validation_warnings"] = validation_warnings
                            expert_reports_data[role_id] = json.dumps(payload, ensure_ascii=False, indent=2)
                        elif structured_data:
                            if validation_warnings:
                                payload = OrderedDict()
                                payload["structured_data"] = structured_data
                                payload["validation_warnings"] = validation_warnings
                                expert_reports_data[role_id] = json.dumps(payload, ensure_ascii=False, indent=2)
                            else:
                                expert_reports_data[role_id] = json.dumps(structured_data, ensure_ascii=False, indent=2)
                        elif content:
                            if validation_warnings:
                                payload = OrderedDict()
                                payload["narrative_summary"] = content
                                payload["validation_warnings"] = validation_warnings
                                expert_reports_data[role_id] = json.dumps(payload, ensure_ascii=False, indent=2)
                            else:
                                expert_reports_data[role_id] = content
                        elif validation_warnings:
                            payload = OrderedDict()
                            payload["validation_warnings"] = validation_warnings
                            expert_reports_data[role_id] = json.dumps(payload, ensure_ascii=False, indent=2)

                if expert_reports_data:
                    logger.info(f" 从agent_results提取了 {len(expert_reports_data)} 个专家报告")

            #  修复：如果sections仍为空，从agent_results动态填充
            if not sections:
                agent_results = session.get("agent_results") or {}
                if agent_results:
                    active_agents = session.get("active_agents") or list(agent_results.keys())

                    section_contributions: Dict[str, OrderedDict] = {}
                    section_titles: Dict[str, str] = {}
                    section_confidences: Dict[str, List[float]] = defaultdict(list)
                    section_sequence: List[str] = []

                    for role_id in active_agents:
                        if role_id in ["requirements_analyst", "project_director"]:
                            continue

                        agent_result = agent_results.get(role_id) or {}
                        payload = _format_agent_payload(agent_result)
                        if not payload:
                            continue

                        section_id, section_title = _derive_section_identity(role_id, agent_result)
                        source_name = agent_result.get("display_name") or agent_result.get("role_name") or role_id

                        section_contributions.setdefault(section_id, OrderedDict())
                        section_contributions[section_id][source_name] = payload

                        if section_title:
                            section_titles.setdefault(section_id, section_title)

                        if section_id not in section_sequence:
                            section_sequence.append(section_id)

                        raw_confidence = agent_result.get("confidence")
                        try:
                            if raw_confidence is not None:
                                section_confidences[section_id].append(float(raw_confidence))
                        except (TypeError, ValueError):
                            logger.debug(f"️ 无法解析 {role_id} 的置信度: {raw_confidence}")

                    for section_id in section_sequence:
                        payload = section_contributions.get(section_id)
                        if not payload:
                            continue

                        confidence_values = section_confidences.get(section_id, [])
                        if confidence_values:
                            confidence = max(confidence_values)
                        else:
                            confidence = 0.8

                        section_content = json.dumps(payload, ensure_ascii=False, indent=2)
                        sections.append(
                            ReportSectionResponse(
                                section_id=section_id,
                                title=section_titles.get(section_id, section_id),
                                content=section_content,
                                confidence=confidence,
                            )
                        )

                    if sections:
                        logger.info(f" 从agent_results动态填充了 {len(sections)} 个章节")

            #  Phase 1.4+ P3: 解析问卷回答数据
            questionnaire_data = None
            qr_raw = final_report.get("questionnaire_responses")
            if qr_raw and isinstance(qr_raw, dict):
                responses_list = []
                for resp_item in qr_raw.get("responses", []):
                    if isinstance(resp_item, dict):
                        responses_list.append(
                            QuestionnaireResponseItem(
                                question_id=resp_item.get("question_id", ""),
                                question=resp_item.get("question", ""),
                                answer=resp_item.get("answer", ""),
                                context=resp_item.get("context", ""),
                            )
                        )

                if responses_list:
                    questionnaire_data = QuestionnaireResponseData(
                        responses=responses_list,
                        timestamp=qr_raw.get("timestamp", ""),
                        analysis_insights=qr_raw.get("analysis_insights", ""),
                    )
                    logger.info(f" 解析到 {len(responses_list)} 条问卷回答")

            #  Phase 1.4+ v4.1: 解析洞察区块 - 已废弃（改用需求分析师的原始输出）
            insights_data = None
            # insights_raw = final_report.get("insights")
            # if insights_raw:
            #     # 支持 Pydantic 对象和 dict 两种格式
            #     if hasattr(insights_raw, 'model_dump'):
            #         insights_dict = insights_raw.model_dump()
            #     elif isinstance(insights_raw, dict):
            #         insights_dict = insights_raw
            #     else:
            #         insights_dict = {}
            #
            #     if insights_dict:
            #         insights_data = InsightsSectionResponse(
            #             key_insights=insights_dict.get("key_insights", []),
            #             cross_domain_connections=insights_dict.get("cross_domain_connections", []),
            #             user_needs_interpretation=insights_dict.get("user_needs_interpretation", "")
            #         )
            #         logger.info(f" 解析到洞察区块: {len(insights_data.key_insights)} 条关键洞察")

            #  Phase 1.4+ v4.1: 解析推敲过程
            deliberation_data = None
            deliberation_raw = final_report.get("deliberation_process")
            if deliberation_raw:
                if hasattr(deliberation_raw, "model_dump"):
                    #  Phase 0优化: 排除None和默认值
                    deliberation_dict = deliberation_raw.model_dump(exclude_none=True, exclude_defaults=True)
                elif isinstance(deliberation_raw, dict):
                    deliberation_dict = deliberation_raw
                else:
                    deliberation_dict = {}

                if deliberation_dict:
                    deliberation_data = DeliberationProcessResponse(
                        inquiry_architecture=deliberation_dict.get("inquiry_architecture", ""),
                        reasoning=deliberation_dict.get("reasoning", ""),
                        role_selection=deliberation_dict.get("role_selection", []),
                        strategic_approach=deliberation_dict.get("strategic_approach", ""),
                    )
                    logger.info(f" 解析到推敲过程: 架构={deliberation_data.inquiry_architecture}")

            #  Phase 1.4+ v4.1: 解析建议区块
            recommendations_data = None
            recommendations_raw = final_report.get("recommendations")
            if recommendations_raw:
                if hasattr(recommendations_raw, "model_dump"):
                    #  Phase 0优化: 排除None和默认值
                    recommendations_dict = recommendations_raw.model_dump(exclude_none=True, exclude_defaults=True)
                elif isinstance(recommendations_raw, dict):
                    recommendations_dict = recommendations_raw
                else:
                    recommendations_dict = {}

                if recommendations_dict:
                    recommendations_data = RecommendationsSectionResponse(
                        immediate_actions=recommendations_dict.get("immediate_actions", []),
                        short_term_priorities=recommendations_dict.get("short_term_priorities", []),
                        long_term_strategy=recommendations_dict.get("long_term_strategy", []),
                        risk_mitigation=recommendations_dict.get("risk_mitigation", []),
                    )
                    logger.info(f" 解析到建议区块: {len(recommendations_data.immediate_actions)} 条立即行动")

            #  解析需求分析结果（需求分析师原始输出）
            #  修复：应从 final_report 读取，而不是从 session.structured_requirements
            requirements_analysis_data = None
            requirements_analysis_raw = final_report.get("requirements_analysis")

            # 尝试从 final_report 顶层获取
            if requirements_analysis_raw and isinstance(requirements_analysis_raw, dict):
                requirements_analysis_data = RequirementsAnalysisResponse(
                    project_overview=requirements_analysis_raw.get("project_overview", ""),
                    core_objectives=requirements_analysis_raw.get("core_objectives", []),
                    project_tasks=requirements_analysis_raw.get("project_tasks", []),
                    narrative_characters=requirements_analysis_raw.get("narrative_characters", []),
                    physical_contexts=requirements_analysis_raw.get("physical_contexts", []),
                    constraints_opportunities=requirements_analysis_raw.get("constraints_opportunities", {}),
                    #  传递用户修改标识
                    has_user_modifications=session.get("has_user_modifications", False),
                    user_modification_summary=session.get("user_modification_summary"),
                )
                logger.info(f" 解析到需求分析结果（从 final_report）: {len(requirements_analysis_data.core_objectives)} 个核心目标")
            else:
                #  备用方案1：从 sections 数组中查找（针对已有会话）
                sections_data = final_report.get("sections", [])
                logger.debug(
                    f" [DEBUG] sections_data type: {type(sections_data)}, length: {len(sections_data) if isinstance(sections_data, list) else 'N/A'}"
                )

                if isinstance(sections_data, list):
                    for section in sections_data:
                        if isinstance(section, dict):
                            section_id = section.get("section_id", "")
                            logger.debug(f" [DEBUG] Checking section: {section_id}")

                            if section_id == "requirements_analysis":
                                content_str = section.get("content", "")
                                logger.info(
                                    f" Found requirements_analysis in sections, content length: {len(content_str)}"
                                )

                                if content_str:
                                    try:
                                        # 解析 JSON 字符串
                                        req_data = (
                                            json.loads(content_str) if isinstance(content_str, str) else content_str
                                        )

                                        #  修复：正确映射 requirements_analyst 的实际输出字段
                                        # requirements_analyst 输出的是完整的结构化数据，包含多个字段
                                        logger.debug(f" [FIELD MAPPING] req_data keys: {list(req_data.keys())}")
                                        logger.debug(
                                            f" [FIELD MAPPING] project_task: '{req_data.get('project_task', '')}' (len={len(req_data.get('project_task', ''))})"
                                        )
                                        logger.debug(
                                            f" [FIELD MAPPING] character_narrative: (len={len(req_data.get('character_narrative', ''))})"
                                        )
                                        logger.debug(
                                            f" [FIELD MAPPING] physical_context: (len={len(req_data.get('physical_context', ''))})"
                                        )

                                        #  v7.131: 安全处理 physical_context（可能是字符串或字典）
                                        physical_context_raw = req_data.get("physical_context", "")
                                        if isinstance(physical_context_raw, dict):
                                            context_parts = []
                                            if physical_context_raw.get("location"):
                                                context_parts.append(f"位置: {physical_context_raw['location']}")
                                            if physical_context_raw.get("space_type"):
                                                context_parts.append(f"空间类型: {physical_context_raw['space_type']}")
                                            if physical_context_raw.get("floor_height"):
                                                context_parts.append(f"层高: {physical_context_raw['floor_height']}")
                                            if physical_context_raw.get("area"):
                                                context_parts.append(f"面积: {physical_context_raw['area']}")
                                            physical_context_list = ["; ".join(context_parts)] if context_parts else []
                                        elif isinstance(physical_context_raw, str) and physical_context_raw:
                                            physical_context_list = [physical_context_raw]
                                        else:
                                            physical_context_list = []

                                        requirements_analysis_data = RequirementsAnalysisResponse(
                                            project_overview=req_data.get("project_overview")
                                            or req_data.get("project_task", ""),
                                            core_objectives=req_data.get("core_objectives", []),
                                            project_tasks=[req_data.get("project_task", "")]
                                            if req_data.get("project_task")
                                            else [],
                                            narrative_characters=[req_data.get("character_narrative", "")]
                                            if req_data.get("character_narrative")
                                            else [],
                                            physical_contexts=physical_context_list,
                                            constraints_opportunities={
                                                "resource_constraints": req_data.get("resource_constraints", ""),
                                                "regulatory_requirements": req_data.get("regulatory_requirements", ""),
                                                "space_constraints": req_data.get("space_constraints", ""),
                                                "core_tension": req_data.get("core_tension", ""),
                                                "design_challenge": req_data.get("design_challenge", ""),
                                            },
                                            #  传递用户修改标识
                                            has_user_modifications=session.get("has_user_modifications", False),
                                            user_modification_summary=session.get("user_modification_summary"),
                                        )
                                        logger.info(
                                            f" 解析到需求分析结果（从 sections）: {len(requirements_analysis_data.core_objectives)} 个核心目标"
                                        )
                                        logger.debug(
                                            f" [FIELD MAPPING] project_tasks after mapping: {len(requirements_analysis_data.project_tasks)} items"
                                        )
                                        logger.debug(
                                            f" [FIELD MAPPING] narrative_characters after mapping: {len(requirements_analysis_data.narrative_characters)} items"
                                        )
                                        logger.debug(
                                            f" [FIELD MAPPING] physical_contexts after mapping: {len(requirements_analysis_data.physical_contexts)} items"
                                        )
                                        break
                                    except (json.JSONDecodeError, TypeError) as e:
                                        logger.warning(f"️ 解析 sections 中的 requirements_analysis 失败: {e}")
                else:
                    logger.debug(f" [DEBUG] sections_data is not a list, type: {type(sections_data)}")

                #  备用方案2：如果以上都失败，尝试从 session.structured_requirements 读取（向后兼容）
                if not requirements_analysis_data:
                    structured_req = session.get("structured_requirements")
                    if structured_req and isinstance(structured_req, dict):
                        requirements_analysis_data = RequirementsAnalysisResponse(
                            project_overview=structured_req.get("project_overview", ""),
                            core_objectives=structured_req.get("core_objectives", []),
                            project_tasks=structured_req.get("project_tasks", []),
                            narrative_characters=structured_req.get("narrative_characters", []),
                            physical_contexts=structured_req.get("physical_contexts", []),
                            constraints_opportunities=structured_req.get("constraints_opportunities", {}),
                            #  传递用户修改标识
                            has_user_modifications=session.get("has_user_modifications", False),
                            user_modification_summary=session.get("user_modification_summary"),
                        )
                        logger.info(
                            f" 解析到需求分析结果（从 session.structured_requirements 备用）: {len(requirements_analysis_data.core_objectives)} 个核心目标"
                        )

            structured_report = StructuredReportResponse(
                inquiry_architecture=final_report.get("inquiry_architecture", ""),
                core_answer=core_answer_data,  #  添加核心答案
                insights=None,  #  已废弃：不再使用LLM综合洞察
                requirements_analysis=requirements_analysis_data,  #  添加需求分析结果（需求分析师原始输出）
                deliberation_process=deliberation_data,  #  Phase 1.4+ v4.1: 添加推敲过程
                recommendations=recommendations_data,  #  Phase 1.4+ v4.1: 添加建议
                executive_summary=exec_summary,
                sections=sections,
                comprehensive_analysis=comp_analysis,
                conclusions=conclusions,
                expert_reports=expert_reports_data,
                review_feedback=review_feedback,
                questionnaire_responses=questionnaire_data,  #  添加问卷数据
                review_visualization=review_viz,
                challenge_detection=challenge_detection,
                #  v7.4: 添加执行元数据汇总
                execution_metadata=final_report.get("metadata"),
                #  v3.0.26: 添加思维导图内容结构
                mindmap_content=final_report.get("mindmap_content"),
                # 深度思考模式概念图（集中生成）
                generated_images=final_report.get("generated_images"),
                image_prompts=final_report.get("image_prompts"),
                image_top_constraints=final_report.get("image_top_constraints"),
                #  v7.39: 添加专家概念图（深度思考pro模式）
                #  v7.123: 确保图片数据包含正确的URL字段
                generated_images_by_expert=_normalize_image_urls(final_report.get("generated_images_by_expert")),
                #  v7.154: 添加雷达图维度数据
                radar_dimensions=session.get("selected_dimensions") or session.get("selected_radar_dimensions"),
                radar_dimension_values=session.get("radar_dimension_values"),
            )

            logger.info(f" 成功解析结构化报告，包含 {len(sections)} 个章节")

        except Exception as e:
            logger.warning(f"️ 解析结构化报告失败: {e}，将返回 None")
            structured_report = None

    # 获取用户原始输入
    user_input = session.get("user_input", "")

    return ReportResponse(
        session_id=session_id,
        report_text=report_text,
        report_pdf_path=pdf_path,
        created_at=session.get("created_at", datetime.now().isoformat()),
        user_input=user_input,
        structured_report=structured_report,
    )


@router.get("/api/analysis/report/{session_id}/download-pdf")
async def download_report_pdf(session_id: str):
    """
    下载分析报告 PDF（v7.0 重构版）

    生成可编辑的 PDF 文件（文本可选中复制）

    包含 5 个核心章节：
    1. 用户原始需求
    2. 校准问卷回顾（过滤"未回答"）
    3. 需求洞察
    4. 核心答案（支持 v7.0 多交付物格式）
    5. 执行元数据

    不包含专家报告（专家报告有独立下载入口）
    """
    session = await _server.session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"分析尚未完成，当前状态: {session['status']}")

    # 获取报告数据
    final_report = session.get("final_report", {})
    user_input = session.get("user_input", "")

    if not isinstance(final_report, dict) or not final_report:
        raise HTTPException(status_code=400, detail="报告数据不可用")

    try:
        pdf_bytes = generate_report_pdf(final_report, user_input)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=project_report_{session_id}.pdf"},
        )
    except Exception as e:
        logger.error(f" 生成 PDF 失败: {e}")
        raise HTTPException(status_code=500, detail=f"PDF 生成失败: {str(e)}")


@router.get("/api/analysis/report/{session_id}/download-all-experts-pdf")
async def download_all_experts_pdf(session_id: str):
    """
    下载所有专家报告的合并 PDF

    v7.1.3 升级：
    - 切换为 FPDF 原生生成引擎 (generate_all_experts_pdf_fast)
    - 速度提升 10x (10s -> <1s)
    - 移除 Playwright 依赖，更稳定
    """
    #  缓存检查 - 缓存命中直接返回
    cache_key = f"all_experts_pdf_fast_{session_id}"
    if cache_key in _server.pdf_cache:
        logger.info(f" PDF 缓存命中: {session_id}")
        pdf_bytes = _server.pdf_cache[cache_key]
        from urllib.parse import quote

        safe_filename = quote(f"all_expert_reports_{session_id}.pdf", safe="")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"},
        )

    session = await _server.session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"分析尚未完成，当前状态: {session['status']}")

    # 获取专家报告
    final_report = session.get("final_report", {})
    expert_reports = final_report.get("expert_reports", {}) if isinstance(final_report, dict) else {}

    if not expert_reports:
        raise HTTPException(status_code=400, detail="无专家报告数据")

    user_input = session.get("user_input", "")

    try:
        logger.info(f" 快速生成 PDF (FPDF): {session_id}")
        # 使用新的快速生成函数
        pdf_bytes = generate_all_experts_pdf_fast(expert_reports, user_input)

        #  缓存 PDF
        _server.pdf_cache[cache_key] = pdf_bytes
        logger.info(f" PDF 已缓存: {session_id} ({len(pdf_bytes)} bytes)")

        # 使用 URL 编码处理中文文件名
        from urllib.parse import quote

        safe_filename = quote(f"all_expert_reports_{session_id}.pdf", safe="")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"},
        )
    except Exception as e:
        logger.error(f" 生成所有专家报告 PDF 失败: {e}")
        raise HTTPException(status_code=500, detail=f"PDF 生成失败: {str(e)}")


# =============================================================================
# MT-4: WebSocket 事件回放端点
# =============================================================================


class _EventReplayResponse(BaseModel):
    """GET /api/analysis/events/{session_id} 响应体。"""

    session_id: str
    after_seq: int
    events: list  # List[WSEvent]
    count: int


@router.get(
    "/api/analysis/events/{session_id}",
    summary="[MT-4] 获取 WebSocket 事件回放列表",
    description=("返回 session 内 seq > after_seq 的全部 WebSocket 事件。" "断线重连后由前端调用，用于补偿遗漏消息。"),
    tags=["MT-4: WebSocket 事件补偿"],
)
async def get_ws_events(
    session_id: str,
    after_seq: int = 0,
):
    """
    返回 WebSocket 事件回放列表。

    Parameters
    ----------
    session_id:
        会话 ID
    after_seq:
        客户端已收到的最后一个事件序号；返回 seq > after_seq 的全部事件。
        首次调用传 ``0`` 获取全部历史（有 TTL，最多 1h）。
    """
    from intelligent_project_analyzer.services.event_store import get_event_store

    events = await get_event_store().get_after(session_id, after_seq)
    return {
        "session_id": session_id,
        "after_seq": after_seq,
        "events": events,
        "count": len(events),
    }
