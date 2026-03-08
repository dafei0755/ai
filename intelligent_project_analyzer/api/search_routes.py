"""
搜索模式 API 路由 (v7.201)

统一使用 ucppt 深度迭代搜索引擎
- 删除旧版 /stream、/quick、/test 端点
- 保留 /ucppt/stream 作为主搜索 API
- 保留会话管理相关 API
"""

import json
import os
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

#  v7.189: 导入数据库模型（用于会话迁移）
from intelligent_project_analyzer.services.session_archive_manager import (
    ArchivedSearchSession,
    ArchivedSession,
)

router = APIRouter(prefix="/api/search", tags=["Search Mode"])


#  v7.201: 本地定义可选认证函数，避免循环导入
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"


async def optional_auth(request: Request) -> dict | None:
    """
    可选认证依赖函数：如果有JWT Token则验证，没有也不报错

    用于支持登录和未登录用户都能访问的端点
    """
    auth_header = request.headers.get("Authorization", "")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None  # 未提供 Token，返回 None

    token = auth_header[7:]

    # 开发模式支持
    if DEV_MODE and token == "dev-token-mock":
        return {
            "user_id": 9999,
            "username": "dev_user",
            "email": "dev@localhost",
            "name": "开发测试用户",
            "roles": ["administrator"],
        }

    # 验证 JWT Token
    try:
        from intelligent_project_analyzer.services.wordpress_jwt_service import get_jwt_service

        jwt_service = get_jwt_service()
        payload = jwt_service.verify_token(token)

        if not payload:
            return None  # Token 无效，返回 None（不报错）

        return {
            "user_id": payload.get("user_id"),
            "username": payload.get("username"),
            "email": payload.get("email"),
            "name": payload.get("name"),
            "roles": payload.get("roles", []),
        }
    except Exception as e:
        logger.debug(f"Token 验证失败（可选认证）: {e}")
        return None


def get_user_identifier(current_user: dict | None) -> str | None:
    """
     v7.277: 统一获取用户标识符（用户名字符串）

    解决开发模式下 user_id (数字 9999) 与 username (字符串 "dev_user") 不一致的问题。
    确保搜索会话的存储和查询使用相同的用户标识符。

    优先级：sub > username > str(user_id)

    Returns:
        用户标识符字符串，或 None（未登录用户）
    """
    if not current_user:
        return None

    # 优先使用 sub（JWT标准字段），然后是 username
    identifier = current_user.get("sub") or current_user.get("username")

    # 如果都没有，使用 user_id 的字符串形式
    if not identifier:
        user_id = current_user.get("user_id")
        identifier = str(user_id) if user_id else None

    return identifier


#  v7.189: 删除搜索会话端点
@router.delete("/session/{session_id}")
async def delete_search_session(
    session_id: str,
    current_user: dict = Depends(optional_auth),
):
    """
    删除搜索会话

    验证用户权限后从 SearchSession 表删除
    """
    try:
        from intelligent_project_analyzer.services.session_archive_manager import (
            get_archive_manager,
        )

        archive_manager = get_archive_manager()

        # 获取会话信息
        session = await archive_manager.get_search_session(session_id)
        if not session:
            logger.warning(f"️ 尝试删除不存在的搜索会话: {session_id}")
            return {"success": False, "message": "会话不存在"}

        # 验证权限：只有会话所有者可以删除
        #  v7.277: 使用统一的用户标识符函数
        user_id = get_user_identifier(current_user)
        session_user_id = session.get("user_id")

        # 允许删除的情况：
        # 1. 会话没有 user_id（guest 会话）
        # 2. 会话的 user_id 匹配当前用户
        # 3. session_id 以当前用户 ID 开头（兼容旧会话）
        if session_user_id and session_user_id != user_id:
            # 额外检查 session_id 前缀
            user_id_short = user_id[:8] if user_id and len(user_id) > 8 else user_id
            if not session_id.startswith(f"{user_id_short}-"):
                logger.warning(f"️ 无权删除搜索会话: {session_id} | user={user_id}")
                return {"success": False, "message": "无权删除此会话"}

        # 执行删除
        success = await archive_manager.delete_search_session(session_id)

        if success:
            logger.info(f" 搜索会话已删除: {session_id}")
            return {"success": True, "message": "删除成功"}
        else:
            logger.error(f" 删除搜索会话失败: {session_id}")
            return {"success": False, "message": "删除失败"}

    except Exception as e:
        logger.error(f" 删除搜索会话异常: {session_id} | {e}")
        return {"success": False, "message": str(e)}


# ====================  v7.163: 搜索会话持久化 API ====================


class CreateSearchSessionRequest(BaseModel):
    """创建搜索会话请求"""

    query: str = Field(..., description="搜索查询", min_length=1, max_length=2000)
    deep_mode: bool = Field(default=False, description="是否深度搜索模式")


@router.post("/session/create")
async def create_search_session(
    request: CreateSearchSessionRequest,
    current_user: dict = Depends(optional_auth),
):
    """
    创建搜索会话（仅保存查询，不执行搜索）

    返回 session_id，前端跳转到 /search/{session_id} 后再执行搜索
    URL 中不包含查询参数，便于分享
    """
    try:
        from intelligent_project_analyzer.services.session_archive_manager import (
            get_archive_manager,
        )

        #  v7.189: 生成纯随机session_id，不包含用户ID（隐私安全）
        session_id = f"search-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:12]}"

        # 获取用户标识符用于数据库存储（不在URL中暴露）
        #  v7.277: 使用统一的用户标识符函数
        user_id = get_user_identifier(current_user)

        archive_manager = get_archive_manager()

        # 保存初始会话（只有查询，没有结果）
        success = await archive_manager.archive_search_session(
            session_id=session_id,
            query=request.query,
            search_result={
                "sources": [],
                "images": [],
                "thinkingContent": "",
                "answerContent": "",
                "searchPlan": None,
                "rounds": [],
                "totalRounds": 0,
                "executionTime": 0,
                "isDeepMode": request.deep_mode,
                "status": "pending",  # 标记为待执行
            },
            user_id=user_id,
            force=True,
        )

        if success:
            logger.info(f" 创建搜索会话成功: {session_id} | query={request.query[:50]}...")
            return {
                "success": True,
                "session_id": session_id,
                "query": request.query,
                "deep_mode": request.deep_mode,
            }
        else:
            return {"success": False, "error": "创建会话失败"}

    except Exception as e:
        logger.error(f" 创建搜索会话失败: {e}")
        return {"success": False, "error": str(e)}


class SaveSearchSessionRequest(BaseModel):
    """保存搜索会话请求"""

    session_id: str = Field(..., description="搜索会话ID")
    query: str = Field(..., description="搜索查询")
    sources: list = Field(default=[], description="来源列表")
    images: list = Field(default=[], description="图片列表")
    #  v7.171: 支持新字段名
    thinkingContent: str = Field(default="", description="深度思考内容")
    answerContent: str = Field(default="", description="AI回答内容")
    searchPlan: dict | None = Field(default=None, description="搜索规划")
    rounds: list = Field(default=[], description="搜索轮次记录")
    totalRounds: int = Field(default=0, description="总轮数")
    executionTime: float = Field(default=0, description="执行时间(秒)")
    isDeepMode: bool = Field(default=False, description="是否深度搜索模式")
    # 兼容旧字段
    reasoning: str = Field(default="", description="推理过程(旧)")
    content: str = Field(default="", description="AI回答内容(旧)")
    #  v7.219: 需求洞察相关字段（完整链路持久化）
    l0Content: str = Field(default="", description="L0分析对话内容")
    problemSolvingThinking: str = Field(default="", description="解题思考内容")
    structuredInfo: dict | None = Field(default=None, description="结构化用户信息")
    #  v7.241: 框架清单和搜索主线字段
    frameworkChecklist: dict | None = Field(default=None, description="框架清单")
    searchMasterLine: dict | None = Field(default=None, description="搜索主线")
    #  v7.330: 深度分析相关字段（修复历史记录丢失）
    deepAnalysisResult: dict | None = Field(default=None, description="深度分析结果")
    fourMissionsResult: dict | None = Field(default=None, description="4条使命结果")
    qualityAssessment: dict | None = Field(default=None, description="答案质量评估")
    answerThinkingContent: str = Field(default="", description="答案思考过程")


@router.post("/session/save")
async def save_search_session(
    request: SaveSearchSessionRequest,
    current_user: dict = Depends(optional_auth),
):
    """
    保存搜索会话到数据库（持久化）

    与主对话使用相同的归档机制
    """
    try:
        from intelligent_project_analyzer.services.session_archive_manager import (
            get_archive_manager,
        )

        archive_manager = get_archive_manager()

        #  v7.277: 使用统一的用户标识符函数
        user_id = get_user_identifier(current_user)

        success = await archive_manager.archive_search_session(
            session_id=request.session_id,
            query=request.query,
            search_result={
                "sources": request.sources,
                "images": request.images,
                #  v7.171: 使用新字段名，兼容旧字段
                "thinkingContent": request.thinkingContent or request.reasoning,
                "answerContent": request.answerContent or request.content,
                "searchPlan": request.searchPlan,
                "rounds": request.rounds,
                "totalRounds": request.totalRounds,
                "executionTime": request.executionTime,
                "isDeepMode": request.isDeepMode,
                #  v7.219: 需求洞察相关字段
                "l0Content": request.l0Content,
                "problemSolvingThinking": request.problemSolvingThinking,
                "structuredInfo": request.structuredInfo,
                #  v7.241: 保存框架清单和搜索主线
                "frameworkChecklist": request.frameworkChecklist,
                "searchMasterLine": request.searchMasterLine,
                #  v7.330: 保存深度分析相关字段（修复历史记录丢失）
                "deepAnalysisResult": request.deepAnalysisResult,
                "fourMissionsResult": request.fourMissionsResult,
                "qualityAssessment": request.qualityAssessment,
                "answerThinkingContent": request.answerThinkingContent,
            },
            user_id=user_id,
            force=True,  # 允许更新
        )

        if success:
            logger.info(
                f" [v7.241] 搜索会话已保存 | session_id={request.session_id} | has_checklist={request.frameworkChecklist is not None}"
            )
            return {"success": True, "message": "搜索会话已保存"}
        else:
            return {"success": False, "error": "保存失败"}

    except Exception as e:
        logger.error(f" 保存搜索会话失败: {e}")
        return {"success": False, "error": str(e)}


@router.get("/session/{session_id}")
async def get_search_session(
    session_id: str,
    current_user: dict = Depends(optional_auth),
):
    """
    获取已保存的搜索会话

    从数据库加载持久化的搜索结果
    """
    try:
        from intelligent_project_analyzer.services.session_archive_manager import (
            get_archive_manager,
        )

        archive_manager = get_archive_manager()

        session = await archive_manager.get_search_session(session_id)

        if session:
            return {"success": True, "session": session}
        else:
            return {"success": False, "error": "会话不存在"}

    except Exception as e:
        logger.error(f" 获取搜索会话失败: {e}")
        return {"success": False, "error": str(e)}


@router.get("/history")
async def get_search_history(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(optional_auth),
):
    """
    获取搜索历史列表

    返回用户的搜索历史记录
    """
    try:
        from intelligent_project_analyzer.services.session_archive_manager import (
            get_archive_manager,
        )

        archive_manager = get_archive_manager()

        #  v7.277: 使用统一的用户标识符函数
        user_id = get_user_identifier(current_user)

        sessions = await archive_manager.list_search_sessions(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

        return {"success": True, "sessions": sessions, "count": len(sessions)}

    except Exception as e:
        logger.error(f" 获取搜索历史失败: {e}")
        return {"success": False, "error": str(e), "sessions": []}


# ====================  v7.180: ucppt 深度迭代搜索 API ====================


class UcpptSearchRequest(BaseModel):
    """ucppt深度搜索请求"""

    query: str = Field(..., description="搜索查询", min_length=1, max_length=2000)
    max_rounds: int = Field(default=30, description="最大搜索轮数", ge=3, le=30)
    confidence_threshold: float = Field(default=0.8, description="信息充分度阈值", ge=0.5, le=0.95)
    session_id: str | None = Field(default=None, description="会话ID")  #  v7.280: 支持分阶段模式
    phase_mode: str | None = Field(default="full", description="执行模式: full(完整) / step1_only(仅分析) / step2_only(仅搜索)")
    framework_data: dict | None = Field(default=None, description="用户编辑后的框架数据（step2_only模式时必填）")


@router.post("/ucppt/stream")
async def ucppt_search_stream(
    request: UcpptSearchRequest,
    current_user: dict = Depends(optional_auth),
):
    """
    ucppt 深度迭代搜索（流式）

    借鉴 ucppt 的多轮迭代搜索范式：
    - 动态轮次：根据信息充分度自动决定搜索轮数（上限30轮）
    - 知识框架：构建概念→维度→证据的树状结构
    - 反思循环：每轮搜索后用gpt-4o-mini评估是否继续
    - 深度钻取：发现关键概念后自动深入探索
    - 实时推送：前端可见每轮搜索状态

    事件类型：
    - phase: 搜索阶段变化 {phase, phase_name, message}
    - framework: 知识框架 {core_concepts, dimensions, initial_gaps}
    - round_start: 轮次开始 {round, total, topic, query, confidence}
    - round_sources: 轮次搜索结果 {round, sources_count, new_concepts, sources}
    - round_reflecting: 反思中 {round, status, message}
    - round_complete: 轮次完成 {round, confidence, should_continue, gaps, reasoning}
    - search_complete: 搜索结束 {reason, total_rounds, final_confidence}
    - drill_start: 深度钻取开始 {round, concept, query}
    - drill_complete: 深度钻取完成 {round, concept, sources_count}
    - answer_chunk: 答案片段 {content}
    - done: 全部完成 {total_rounds, total_sources, final_confidence, execution_time}
    - error: 错误 {message}
    """
    #  v7.189: 生成纯随机session_id（mm前缀表示ucppt）
    if not request.session_id:
        session_id = f"mm-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:12]}"
    else:
        session_id = request.session_id

    logger.info(
        f" [Ucppt Stream] 开始深度搜索 | "
        f"session={session_id} | query={request.query[:50]}... | "
        f"max_rounds={request.max_rounds} | threshold={request.confidence_threshold} | "
        f"phase_mode={request.phase_mode}"
    )

    async def event_generator():
        try:
            from intelligent_project_analyzer.services.ucppt_search_engine import get_ucppt_engine

            engine = get_ucppt_engine()

            # 更新引擎配置
            engine.max_rounds = request.max_rounds
            engine.confidence_threshold = request.confidence_threshold

            #  v7.280: 根据 phase_mode 选择执行方式
            if request.phase_mode == "step1_only":
                # 仅执行 Step 1 分析 + Step 2 任务分解（v7.333），返回框架供用户编辑
                logger.info(" [v7.280] Step1 Only 模式")
                async for event in engine.execute_step1_only(
                    query=request.query,
                    session_id=session_id,
                ):
                    event_type = event.get("type", "message")
                    event_data = event.get("data", {})
                    if not event_data:
                        event_data = {
                            k: v
                            for k, v in event.items()
                            if k not in ("type", "_internal_data", "_internal_framework", "_internal_approach")
                        }

                    # v7.333.7: 详细日志记录事件发送
                    logger.info(f" [SSE] 发送事件: {event_type}")

                    yield f"event: {event_type}\n"
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

                    # v7.333.7: 在 awaiting_confirmation 后断开（此时 Step 1 + Step 2 都完成）
                    if event_type in ("awaiting_confirmation", "error"):
                        logger.info(f" [SSE] 断开连接: event_type={event_type}")
                        break

            elif request.phase_mode == "step2_only":
                # 仅执行 Step 2 搜索，使用用户编辑后的框架
                logger.info(f" [v7.280] Step2 Only 模式 | framework_data={bool(request.framework_data)}")
                if not request.framework_data:
                    yield "event: error\n"
                    yield f"data: {json.dumps({'message': 'step2_only模式需要提供framework_data'}, ensure_ascii=False)}\n\n"
                    return

                async for event in engine.execute_step2_only(
                    query=request.query,
                    session_id=session_id,
                    framework_data=request.framework_data,
                    max_rounds=request.max_rounds,
                ):
                    event_type = event.get("type", "message")
                    event_data = event.get("data", {})
                    if not event_data:
                        event_data = {
                            k: v for k, v in event.items() if k not in ("type", "_internal_data", "_internal_framework")
                        }
                    yield f"event: {event_type}\n"
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                    if event_type in ("done", "error"):
                        break
            else:
                # 完整模式（默认）
                async for event in engine.search_deep(
                    query=request.query,
                    max_rounds=request.max_rounds,
                ):
                    event_type = event.get("type", "message")

                    # v7.223: 修复事件结构不一致问题
                    # 某些事件（unified_dialogue_chunk, unified_dialogue_complete）的数据直接在顶层
                    # 而不是包装在 data 字段中
                    if event_type in ("unified_dialogue_chunk", "unified_dialogue_complete"):
                        event_data = {"content": event.get("content", "")}
                    else:
                        # 大部分事件使用 {type, data: {...}} 结构
                        event_data = event.get("data", {})
                        # 兜底：如果 data 为空但事件有其他字段，排除 type 和内部字段后返回
                        if not event_data:
                            event_data = {
                                k: v
                                for k, v in event.items()
                                if k not in ("type", "_internal_data", "_internal_master_line")
                            }

                    yield f"event: {event_type}\n"
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

                    if event_type in ("done", "error"):
                        break

        except Exception as e:
            logger.error(f" [Ucppt Stream] 搜索失败: {e}", exc_info=True)
            yield "event: error\n"
            yield f"data: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Session-ID": session_id,
        },
    )


# ====================  v7.189: Guest会话迁移和关联 ====================


@router.post("/session/migrate")
async def migrate_guest_sessions(
    current_user: dict = Depends(optional_auth),
):
    """
    将当前用户的所有guest会话迁移到用户账户

    登录后自动调用，将之前的guest-开头的会话关联到用户ID
    """
    #  v7.277: 使用统一的用户标识符函数
    user_id = get_user_identifier(current_user)
    if not user_id:
        return {"success": False, "error": "需要登录"}

    try:
        from intelligent_project_analyzer.services.session_archive_manager import (
            get_archive_manager,
        )

        archive_manager = get_archive_manager()

        # 查询所有guest会话（包括分析会话和搜索会话）
        migrated_count = 0

        # 1. 迁移搜索会话
        db = archive_manager._get_db()
        guest_search_sessions = (
            db.query(ArchivedSearchSession)
            .filter(
                (ArchivedSearchSession.user_id.is_(None))
                | (ArchivedSearchSession.user_id == "guest")
                | (ArchivedSearchSession.session_id.like("guest-%"))
            )
            .all()
        )

        for session in guest_search_sessions:
            # 生成新的session_id（使用用户ID前缀）
            old_session_id = session.session_id
            (old_session_id.split("-")[1] if len(old_session_id.split("-")) > 1 else datetime.now().strftime("%Y%m%d"))
            old_session_id.split("-")[-1] if len(old_session_id.split("-")) > 2 else uuid.uuid4().hex[:8]
            user_id[:8] if len(user_id) > 8 else user_id

            # 创建新记录（保持旧记录，避免破坏URL）
            session.user_id = user_id
            session.updated_at = datetime.now()
            migrated_count += 1
            logger.info(f" 迁移搜索会话: {old_session_id} -> user_id={user_id}")

        # 2. 迁移分析会话
        guest_analysis_sessions = (
            db.query(ArchivedSession)
            .filter(
                (ArchivedSession.user_id.is_(None))
                | (ArchivedSession.user_id == "guest")
                | (ArchivedSession.session_id.like("guest-%"))
            )
            .all()
        )

        for session in guest_analysis_sessions:
            session.user_id = user_id
            session.archived_at = datetime.now()
            migrated_count += 1
            logger.info(f" 迁移分析会话: {session.session_id} -> user_id={user_id}")

        db.commit()
        db.close()

        return {"success": True, "migrated_count": migrated_count, "message": f"成功迁移 {migrated_count} 个会话到用户账户"}

    except Exception as e:
        logger.error(f" 迁移guest会话失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.post("/session/associate")
async def associate_guest_session(
    session_id: str,
    current_user: dict = Depends(optional_auth),
):
    """
    将单个guest会话关联到当前用户

    用于登录前创建的会话，登录后自动关联
    """
    #  v7.277: 使用统一的用户标识符函数
    user_id = get_user_identifier(current_user)
    if not user_id:
        return {"success": False, "error": "需要登录"}

    try:
        from intelligent_project_analyzer.services.session_archive_manager import (
            get_archive_manager,
        )

        archive_manager = get_archive_manager()

        db = archive_manager._get_db()

        # 尝试查找搜索会话
        search_session = db.query(ArchivedSearchSession).filter(ArchivedSearchSession.session_id == session_id).first()

        if search_session:
            search_session.user_id = user_id
            search_session.updated_at = datetime.now()
            db.commit()
            db.close()
            logger.info(f" 关联搜索会话: {session_id} -> user_id={user_id}")
            return {"success": True, "session_id": session_id, "message": "搜索会话已关联到用户账户"}

        # 尝试查找分析会话
        analysis_session = db.query(ArchivedSession).filter(ArchivedSession.session_id == session_id).first()

        if analysis_session:
            analysis_session.user_id = user_id
            analysis_session.archived_at = datetime.now()
            db.commit()
            db.close()
            logger.info(f" 关联分析会话: {session_id} -> user_id={user_id}")
            return {"success": True, "session_id": session_id, "message": "分析会话已关联到用户账户"}

        db.close()
        return {"success": False, "error": "会话不存在"}

    except Exception as e:
        logger.error(f" 关联guest会话失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ==================== v7.300: 4步工作流 API ====================


class UpdateSearchPlanRequest(BaseModel):
    """v7.300: 更新搜索计划请求"""

    session_id: str = Field(..., description="会话ID")
    action: str = Field(..., description="操作类型: add/delete/update/reorder")
    step_id: str | None = Field(default=None, description="步骤ID（delete/update时必填）")
    step_data: dict | None = Field(default=None, description="步骤数据（add/update时必填）")
    new_order: List[str] | None = Field(default=None, description="新顺序（reorder时必填）")


@router.post("/step2/update")
async def update_search_plan(
    request: UpdateSearchPlanRequest,
    current_user: dict = Depends(optional_auth),
):
    """
    v7.300: 更新搜索计划（添加/删除/编辑步骤）

    用户在第2步编辑搜索任务列表时调用
    """
    try:
        from intelligent_project_analyzer.services.session_archive_manager import (
            get_archive_manager,
        )

        archive_manager = get_archive_manager()

        # 获取当前会话
        session = await archive_manager.get_search_session(request.session_id)
        if not session:
            return {"success": False, "error": "会话不存在"}

        # 获取当前搜索计划
        search_result = session.get("search_result", {})
        search_plan = search_result.get("step2_search_plan", {})
        search_steps = search_plan.get("search_steps", [])

        if request.action == "add":
            # 添加新步骤
            if not request.step_data:
                return {"success": False, "error": "添加步骤需要提供 step_data"}

            new_step = {
                "id": f"S{len(search_steps) + 1}",
                "step_number": len(search_steps) + 1,
                "task_description": request.step_data.get("task_description", ""),
                "expected_outcome": request.step_data.get("expected_outcome", ""),
                "search_keywords": request.step_data.get("search_keywords", []),
                "priority": request.step_data.get("priority", "medium"),
                "can_parallel": request.step_data.get("can_parallel", True),
                "status": "pending",
                "is_user_added": True,
            }
            search_steps.append(new_step)
            logger.info(f" [v7.300] 添加搜索步骤 | session={request.session_id} | step_id={new_step['id']}")

        elif request.action == "delete":
            # 删除步骤
            if not request.step_id:
                return {"success": False, "error": "删除步骤需要提供 step_id"}

            search_steps = [s for s in search_steps if s.get("id") != request.step_id]
            # 重新编号
            for i, step in enumerate(search_steps):
                step["step_number"] = i + 1
            logger.info(f" [v7.300] 删除搜索步骤 | session={request.session_id} | step_id={request.step_id}")

        elif request.action == "update":
            # 更新步骤
            if not request.step_id or not request.step_data:
                return {"success": False, "error": "更新步骤需要提供 step_id 和 step_data"}

            for step in search_steps:
                if step.get("id") == request.step_id:
                    step.update(request.step_data)
                    step["is_user_modified"] = True
                    break
            logger.info(f" [v7.300] 更新搜索步骤 | session={request.session_id} | step_id={request.step_id}")

        elif request.action == "reorder":
            # 重新排序
            if not request.new_order:
                return {"success": False, "error": "重新排序需要提供 new_order"}

            step_map = {s.get("id"): s for s in search_steps}
            search_steps = []
            for i, step_id in enumerate(request.new_order):
                if step_id in step_map:
                    step = step_map[step_id]
                    step["step_number"] = i + 1
                    search_steps.append(step)
            logger.info(f" [v7.300] 重新排序搜索步骤 | session={request.session_id}")

        else:
            return {"success": False, "error": f"未知操作类型: {request.action}"}

        # 更新搜索计划
        search_plan["search_steps"] = search_steps
        search_result["step2_search_plan"] = search_plan

        # 保存会话
        success = await archive_manager.archive_search_session(
            session_id=request.session_id,
            query=session.get("query", ""),
            search_result=search_result,
            user_id=get_user_identifier(current_user),
            force=True,
        )

        if success:
            return {"success": True, "search_plan": search_plan, "message": f"搜索计划已更新（{request.action}）"}
        else:
            return {"success": False, "error": "保存失败"}

    except Exception as e:
        logger.error(f" [v7.300] 更新搜索计划失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


class ConfirmSearchPlanRequest(BaseModel):
    """v7.300: 确认搜索计划请求"""

    session_id: str = Field(..., description="会话ID")
    search_plan: dict | None = Field(default=None, description="用户编辑后的搜索计划（可选）")


@router.post("/step2/confirm")
async def confirm_search_plan(
    request: ConfirmSearchPlanRequest,
    current_user: dict = Depends(optional_auth),
):
    """
    v7.300: 确认搜索计划并准备执行

    用户点击"运行"按钮后调用，标记计划已确认
    """
    try:
        from intelligent_project_analyzer.services.session_archive_manager import (
            get_archive_manager,
        )

        archive_manager = get_archive_manager()

        # 获取当前会话
        session = await archive_manager.get_search_session(request.session_id)
        if not session:
            return {"success": False, "error": "会话不存在"}

        search_result = session.get("search_result", {})

        # 如果提供了新的搜索计划，更新它
        if request.search_plan:
            search_result["step2_search_plan"] = request.search_plan

        # 标记计划已确认
        search_plan = search_result.get("step2_search_plan", {})
        search_plan["is_confirmed"] = True
        search_plan["confirmed_at"] = datetime.now().isoformat()
        search_result["step2_search_plan"] = search_plan

        # 保存会话
        success = await archive_manager.archive_search_session(
            session_id=request.session_id,
            query=session.get("query", ""),
            search_result=search_result,
            user_id=get_user_identifier(current_user),
            force=True,
        )

        if success:
            logger.info(
                f" [v7.300] 搜索计划已确认 | session={request.session_id} | steps={len(search_plan.get('search_steps', []))}"
            )
            return {
                "success": True,
                "message": "搜索计划已确认，可以开始执行",
                "search_plan": search_plan,
            }
        else:
            return {"success": False, "error": "保存失败"}

    except Exception as e:
        logger.error(f" [v7.300] 确认搜索计划失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


class ValidateSearchPlanRequest(BaseModel):
    """v7.300: 验证搜索计划请求（智能补充）"""

    session_id: str = Field(..., description="会话ID")
    search_plan: dict = Field(..., description="用户编辑后的搜索计划")


@router.post("/step2/validate")
async def validate_search_plan(
    request: ValidateSearchPlanRequest,
    current_user: dict = Depends(optional_auth),
):
    """
    v7.300: 验证搜索计划并智能补充

    用户编辑后点击运行时，后端检查是否有遗漏的重要维度，
    如发现遗漏，自动建议补充任务（用户可忽略）
    """
    try:
        from intelligent_project_analyzer.services.session_archive_manager import (
            get_archive_manager,
        )

        archive_manager = get_archive_manager()

        # 获取当前会话
        session = await archive_manager.get_search_session(request.session_id)
        if not session:
            return {"success": False, "error": "会话不存在"}

        search_result = session.get("search_result", {})

        # 获取原始分析数据
        step1_output = search_result.get("step1_analysis_output", {})
        original_directions = step1_output.get("search_directions", [])

        # 获取用户编辑后的步骤
        user_steps = request.search_plan.get("search_steps", [])
        user_step_descriptions = [s.get("task_description", "").lower() for s in user_steps]

        # 检查是否有遗漏的重要方向
        suggested_additions = []
        for direction in original_directions:
            if direction.get("priority") in ["P0", "P1"]:
                direction_text = direction.get("what_to_search", "").lower()
                # 简单检查：如果原始方向的关键词不在用户步骤中
                is_covered = any(
                    direction_text[:20] in desc or desc in direction_text for desc in user_step_descriptions
                )
                if not is_covered:
                    suggested_additions.append(
                        {
                            "direction": direction.get("direction", ""),
                            "what_to_search": direction.get("what_to_search", ""),
                            "why_important": direction.get("why_search", ""),
                            "priority": direction.get("priority", "P1"),
                            "derived_from": direction.get("derived_from", ""),
                        }
                    )

        if suggested_additions:
            logger.info(f" [v7.300] 发现可能遗漏的搜索方向 | session={request.session_id} | count={len(suggested_additions)}")
            return {
                "success": True,
                "has_suggestions": True,
                "suggestions": suggested_additions,
                "message": f"发现 {len(suggested_additions)} 个可能遗漏的重要搜索方向",
            }
        else:
            return {
                "success": True,
                "has_suggestions": False,
                "suggestions": [],
                "message": "搜索计划覆盖完整",
            }

    except Exception as e:
        logger.error(f" [v7.300] 验证搜索计划失败: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
