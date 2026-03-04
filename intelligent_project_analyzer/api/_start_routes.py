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

import json
import os
import time
import uuid
from collections import OrderedDict, defaultdict
from datetime import datetime
from typing import Any, Dict, List

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from langgraph.types import Command
from loguru import logger
from pydantic import BaseModel, Field

from intelligent_project_analyzer.agents.followup_agent import FollowupAgent
from intelligent_project_analyzer.api._server_proxy import server_proxy as _server
from intelligent_project_analyzer.services.file_processor import (
    build_combined_input,
    file_processor,
)
from intelligent_project_analyzer.services.geoip_service import get_geoip_service

from .deps import DEV_MODE, sessions_cache
from .helpers import (
    _derive_section_identity,
    _enrich_sections_with_agent_results,
    _format_agent_payload,
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
    DeliberationProcessResponse,
    ExecutiveSummaryResponse,
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
    generate_all_experts_pdf_fast,
    generate_report_pdf,
)
from .workflow_runner import run_workflow_async


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
    print("\n 收到分析请求")
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

    print("运行模式: Dynamic Mode")

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
    print(" 添加后台任务...")
    background_tasks.add_task(run_workflow_async, session_id, analysis_request.user_input)

    print(" 后台任务已添加，返回响应\n")

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
    logger.info("\n 收到多模态分析请求")
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
            file_meta.get(
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

    logger.info(" 会话状态已初始化（Redis + 文件）")

    # 6. 启动工作流（传入 combined_input）
    background_tasks.add_task(run_workflow_async, session_id, combined_input)  #  使用增强后的输入

    logger.info(" 后台任务已添加\n")

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


