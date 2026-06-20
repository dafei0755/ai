"""
dual_mode_routes.py — v2.0 双态架构 API 路由层
Created by GitHub Copilot · 2026-03-15

新增端点（prefix=/api/v2）：
  POST /api/v2/conversation/message            对话态消息入口
  GET  /api/v2/conversation/{session_id}/drafts 草稿列表
  POST /api/v2/conversation/{session_id}/upgrade 确认升级到项目态
  GET  /api/v2/session/{session_id}/mode        当前 system_mode
  POST /api/v2/project/gate                     门禁（GateNode）
  GET  /api/v2/project/{session_id}/taskbook    DesignTaskBook
  GET  /api/v2/project/{session_id}/blueprint   ExecutionBlueprint
  POST /api/v2/project/{session_id}/delta       提交增量修改
  GET  /api/v2/project/{session_id}/archive     ProjectArchive

遵循约束：不触碰现有字段，仅读写 v2.0 追加字段。
"""

from __future__ import annotations

import asyncio
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from pydantic import BaseModel, Field

from intelligent_project_analyzer.services.demand_reconstruction_service import (
    DemandReconstructionService,
    DemandReconstructionUnavailable,
)
from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

router = APIRouter(prefix="/api/v2", tags=["dual-mode-v2"])

# ── 模块级 LLM 单例（懒加载，避免每次请求重新初始化）──────────────────────
_conv_llm: Any = None
_demand_reconstruction_llm: Any = None
_demand_reconstruction_governance_store: Any = None
_FALSE_ENV_VALUES = {"0", "false", "no", "off"}


def _get_conv_llm() -> Any:
    """懒加载并缓存对话态 LLM 实例。"""
    global _conv_llm
    if _conv_llm is None:
        try:
            from intelligent_project_analyzer.services.llm_factory import LLMFactory
            # 对话态优先响应稳定性：限制超时与重试，避免单轮长时间阻塞
            # 可通过环境变量覆盖（秒）
            conv_timeout = int(__import__("os").getenv("CONV_LLM_TIMEOUT", "25"))
            conv_retries = int(__import__("os").getenv("CONV_LLM_MAX_RETRIES", "1"))
            _conv_llm = LLMFactory.create_llm(timeout=conv_timeout, max_retries=conv_retries)
            logger.info(
                f"[dual_mode] 对话态 LLM 初始化完成 (timeout={conv_timeout}s, max_retries={conv_retries})"
            )
        except Exception as exc:
            logger.warning(f"[dual_mode] LLM 初始化失败，将使用占位回复: {exc}")
            _conv_llm = None
    return _conv_llm


def _env_flag_enabled(name: str, default: str = "1") -> bool:
    return __import__("os").getenv(name, default).strip().lower() not in _FALSE_ENV_VALUES


def _is_demand_reconstruction_llm_enabled() -> bool:
    return _env_flag_enabled("DEMAND_RECONSTRUCTION_USE_LLM", "1")


def _get_demand_reconstruction_governance_store() -> Any:
    """Optional governance queue persistence for demand reconstruction signals."""
    global _demand_reconstruction_governance_store
    if not _env_flag_enabled("DEMAND_RECONSTRUCTION_GOVERNANCE_PERSIST", "0"):
        return None
    if _demand_reconstruction_governance_store is None:
        from intelligent_project_analyzer.services.knowledge_governance_store import (
            KnowledgeGovernanceStore,
        )

        store = KnowledgeGovernanceStore()
        store.create_all()
        _demand_reconstruction_governance_store = store
        logger.info("[dual_mode] 需求重构治理信号持久化已启用")
    return _demand_reconstruction_governance_store


def _get_demand_reconstruction_llm() -> Any:
    """短超时 LLM：需求重构第一屏要增强洞察，但不能拖住入口。"""
    global _demand_reconstruction_llm
    if not _is_demand_reconstruction_llm_enabled():
        return None
    if _demand_reconstruction_llm is None:
        try:
            from intelligent_project_analyzer.services import demand_reconstruction_llm
            from intelligent_project_analyzer.services.llm_factory import LLMFactory

            _demand_reconstruction_llm = demand_reconstruction_llm.create_demand_reconstruction_llm(
                fallback_factory=LLMFactory.create_llm,
            )
            if _demand_reconstruction_llm is not None:
                logger.info(
                    "[dual_mode] 需求重构 LLM 初始化完成 "
                    f"(class={_demand_reconstruction_llm.__class__.__name__})"
                )
        except Exception as exc:
            logger.warning(f"[dual_mode] 需求重构 LLM 初始化失败，将使用规则蓝图: {exc}")
            _demand_reconstruction_llm = None
    return _demand_reconstruction_llm

# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

_session_manager_instance: Optional[RedisSessionManager] = None


async def _get_sm() -> RedisSessionManager:
    """复用 server.py 的全局会话管理器单例，避免 Redis 不可用时出现内存字典分裂。"""
    # 延迟导入避免循环引用（server.py 在启动后已完全加载）
    from intelligent_project_analyzer.api.server import _get_session_manager  # noqa: PLC0415
    return await _get_session_manager()


async def _require_session(session_id: str) -> Dict[str, Any]:
    """读取会话；不存在则 404。"""
    sm = await _get_sm()
    session = await sm.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
    return session


async def _optional_current_user(request: Request) -> Optional[dict]:
    """复用主 API 的可选认证，避免对话态会话落到固定 web_user。"""
    from intelligent_project_analyzer.api.server import optional_auth  # noqa: PLC0415

    return await optional_auth(request)


def _resolve_user_identifier(current_user: Optional[dict], fallback: str) -> str:
    """统一对话态会话的 user_id 存储口径。"""
    if current_user:
        from intelligent_project_analyzer.api.server import get_user_identifier  # noqa: PLC0415

        return get_user_identifier(current_user)
    return fallback or "web_user"


def _title_from_message(message: str) -> str:
    """从首条用户消息生成历史记录标题。"""
    return " ".join((message or "").split())[:200]


def _invalidate_sessions_cache(user_id: str) -> None:
    """对话会话写入后立即刷新历史列表缓存。"""
    try:
        from intelligent_project_analyzer.api.server import sessions_cache  # noqa: PLC0415

        sessions_cache.invalidate(f"sessions:{user_id}")
        sessions_cache.invalidate("sessions:web_user")
        sessions_cache.invalidate("sessions:dev_user")
    except Exception as exc:
        logger.debug(f"[dual_mode] 会话缓存失效失败，可忽略: {exc}")


_LEGACY_DEMAND_RECONSTRUCTION_CARD_TYPES = {
    "shallow_battle_plan",
    "shallow_dialogue_blueprint",
}


def _normalize_legacy_demand_reconstruction_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize pre-rename demand-reconstruction card state so old sessions do not hit legacy engines."""
    pending_card = session.get("pending_guidance_card")
    if not isinstance(pending_card, dict):
        return session
    if pending_card.get("card_type") not in _LEGACY_DEMAND_RECONSTRUCTION_CARD_TYPES:
        return session

    migrated_card = {
        **pending_card,
        "card_type": "demand_reconstruction_blueprint",
        "title": pending_card.get("title") or "需求重构",
        "display_label": "需求重构",
        "artifact_name": "行动蓝图",
        "reconstruction_type": "demand_reconstruction",
    }
    migrated = {**session, "pending_guidance_card": migrated_card}
    if "demand_reconstruction_context" not in migrated and "shallow_context" in migrated:
        migrated["demand_reconstruction_context"] = migrated.get("shallow_context")
    return migrated


def _normalize_legacy_demand_reconstruction_option(option_id: Optional[str]) -> Optional[str]:
    if option_id == "continue_shallow":
        return "continue_demand_reconstruction"
    return option_id


async def _archive_conversation_snapshot(session_id: str, session_data: Dict[str, Any]) -> None:
    """对话态也写入归档库，避免 Redis TTL 到期后历史消失。"""
    try:
        from intelligent_project_analyzer.services.session_archive_manager import get_archive_manager  # noqa: PLC0415

        manager = get_archive_manager()
        await manager.archive_session(session_id=session_id, session_data=session_data, force=True)
    except Exception as exc:
        logger.warning(f"[dual_mode] 对话态归档失败（不影响响应）: {session_id}, {exc}")


# ─────────────────────────────────────────────
# 请求 / 响应模型
# ─────────────────────────────────────────────


class ConversationMessageRequest(BaseModel):
    """对话态消息请求。"""

    session_id: Optional[str] = Field(None, description="已有会话ID；为空则自动创建")
    message: str = Field(..., description="用户消息内容")
    user_id: str = Field(default="web_user", description="用户标识")
    context_hint: Optional[str] = Field(None, description="可选：章节/主题提示")
    # 引导卡片交互字段（2026-03-16）
    in_response_to_card_id: Optional[str] = Field(None, description="正在响应的引导卡片 ID")
    selected_option_id: Optional[str] = Field(None, description="用户选择的选项 ID")
    card_response: Optional[Dict[str, Any]] = Field(None, description="结构化卡片响应，支持多页、多选和排序")


class ConversationMessageResponse(BaseModel):
    session_id: str
    reply: str
    intent: str
    drafts_count: int
    upgrade_suggested: bool
    upgrade_signal: Optional[Dict[str, Any]] = None
    system_mode: str
    # 引导卡片（2026-03-16）：None 表示本轮无引导卡
    guidance_card: Optional[Dict[str, Any]] = None
    dialogue_layer: str = Field(default="demand_reconstruction", description="demand_reconstruction | brief_intake | project")
    handoff_available: bool = Field(default=False, description="需求重构行动蓝图是否可转入任务书")
    demand_reconstruction_context: Optional[Dict[str, Any]] = Field(None, description="需求重构行动蓝图上下文")
    reconstruction_type: Optional[str] = Field(None, description="需求重构类型，兼容旧需求重构入口")
    artifact_name: Optional[str] = Field(None, description="需求重构产物名")


class DraftItem(BaseModel):
    draft_id: str
    draft_type: str
    content: Dict[str, Any]
    status: str
    created_at: str


class DraftsResponse(BaseModel):
    session_id: str
    drafts: List[DraftItem]
    total: int
    upgrade_suggested: bool


class UpgradeRequest(BaseModel):
    """用户确认升级到项目态。"""

    session_id: str
    confirmed: bool = Field(..., description="必须为 True 才触发升级")
    user_id: str = Field(default="web_user")


class UpgradeResponse(BaseModel):
    session_id: str
    status: str  # "upgraded" | "already_in_project_mode" | "not_ready"
    system_mode: str
    raw_brief_packet: Optional[Dict[str, Any]] = None
    message: str


class SessionModeResponse(BaseModel):
    session_id: str
    system_mode: str
    requirements_frozen: bool
    has_task_book: bool
    has_blueprint: bool
    has_archive: bool


class GateRequest(BaseModel):
    """向门禁节点投递一段用户输入。"""

    session_id: str
    raw_user_prompt: str
    user_id: str = Field(default="web_user")


class GateResponse(BaseModel):
    session_id: str
    gate_status: str  # CONTINUE | CONVERSATION | CONDITIONAL_CONTINUE | REJECT | NEED_MORE_PREREQUISITE
    interaction_state: Optional[str] = None
    gap_questions: List[str] = Field(default_factory=list)
    gate_decision: Optional[Dict[str, Any]] = None
    message: str


class TaskBookResponse(BaseModel):
    session_id: str
    task_book: Optional[Dict[str, Any]] = None
    frozen: bool
    retrieved_at: str


class BlueprintResponse(BaseModel):
    session_id: str
    blueprint: Optional[Dict[str, Any]] = None
    frozen: bool
    retrieved_at: str


class DeltaRequest(BaseModel):
    """提交局部增量修改请求。"""

    session_id: str
    modification_text: str = Field(..., description="用户描述的修改意图")
    user_id: str = Field(default="web_user")


class DeltaResponse(BaseModel):
    session_id: str
    delta_type: str  # "delta" | "derived"
    routed_to: str
    impact_graph: Optional[Dict[str, Any]] = None
    message: str


class ArchiveResponse(BaseModel):
    session_id: str
    archive: Optional[Dict[str, Any]] = None
    retrieved_at: str


# ─────────────────────────────────────────────
# 端点实现
# ─────────────────────────────────────────────


@router.post("/conversation/message", response_model=ConversationMessageResponse, summary="对话态消息入口")
async def post_conversation_message(
    req: ConversationMessageRequest,
    current_user: Optional[dict] = Depends(_optional_current_user),
) -> ConversationMessageResponse:
    """
    对话态消息入口。

    - session_id 为空时自动创建新会话（system_mode = "conversation"）。
    - 将消息写入会话后交由后台 ConversationEngine 处理（异步）。
    - 此端点仅负责收件 & 响应基础状态；实时进度由 WebSocket 推送。
    """
    sm = await _get_sm()
    user_id = _resolve_user_identifier(current_user, req.user_id)
    message_title = _title_from_message(req.message)

    # ── 1. 创建或读取会话 ──
    if not req.session_id:
        session_id = f"conv-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        await sm.create(
            session_id,
            {
                "session_id": session_id,
                "user_id": user_id,
                "user_input": message_title,
                "system_mode": "conversation",
                "status": "conversation_active",
                "conversation_drafts": [],
                "upgrade_signal": None,
                "cognition_indicators": None,
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
            },
        )
        logger.info(f"[dual_mode] 新对话会话: {session_id}")
    else:
        session_id = req.session_id
        sm2 = await _get_sm()
        existing = await sm2.get(session_id)
        if existing is None:
            # 旧分析流会话在 Redis 里不存在，自动初始化一条对话态记录
            await sm2.create(
                session_id,
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "user_input": message_title,
                    "system_mode": "conversation",
                    "status": "conversation_active",
                    "conversation_drafts": [],
                    "upgrade_signal": None,
                    "cognition_indicators": None,
                    "created_at": datetime.now().isoformat(),
                    "last_active": datetime.now().isoformat(),
                },
            )
            logger.info(f"[dual_mode] 旧会话自动迁移为对话态: {session_id}")
        elif message_title and not existing.get("user_input"):
            await sm2.update(session_id, {"user_input": message_title, "user_id": existing.get("user_id") or user_id})

    # ── 2. 追加消息事件到会话 ──
    session = _normalize_legacy_demand_reconstruction_session(await sm.get(session_id))
    selected_option_id = _normalize_legacy_demand_reconstruction_option(req.selected_option_id)
    conversation_history: List[Dict[str, Any]] = session.get("conversation_history_v2", [])
    conversation_history.append(
        {
            "role": "user",
            "content": req.message,
            "context_hint": req.context_hint,
            "in_response_to_card_id": req.in_response_to_card_id,
            "selected_option_id": selected_option_id,
            "card_response": req.card_response,
            "timestamp": datetime.now().isoformat(),
        }
    )

    # ── 3. 可选：方案高参入口 V2（Feature Flag 灰度） ──
    result: Dict[str, Any] = {}
    scheme_entry_state: Optional[Dict[str, Any]] = None
    scheme_entry_handled = False
    demand_reconstruction_context: Optional[Dict[str, Any]] = session.get("demand_reconstruction_context")
    dialogue_layer = "demand_reconstruction"
    handoff_available = False
    try:
        # ── 3a. 需求重构：购买前理解力证明，不直接进入正式一二轮 ──
        pending_card_type = (session.get("pending_guidance_card") or {}).get("card_type")
        has_formal_intake_state = bool(session.get("scheme_advisor_entry_v2"))
        allow_demand_reconstruction = (
            not has_formal_intake_state
            or pending_card_type == DemandReconstructionService.CARD_TYPE
        )
        if pending_card_type and str(pending_card_type).startswith("scheme_"):
            allow_demand_reconstruction = False

        demand_reconstruction_result = None
        if allow_demand_reconstruction:
            demand_reconstruction_service = DemandReconstructionService(
                llm=_get_demand_reconstruction_llm(),
                require_llm=_is_demand_reconstruction_llm_enabled(),
                governance_store=_get_demand_reconstruction_governance_store(),
            )
            loop = asyncio.get_event_loop()
            demand_reconstruction_result = await loop.run_in_executor(
                None,
                lambda: demand_reconstruction_service.handle_message(
                    session=session,
                    user_message=req.message,
                    in_response_to_card_id=req.in_response_to_card_id,
                    selected_option_id=selected_option_id,
                ),
            )
        force_brief_intake_from_demand_reconstruction = False
        scheme_user_message = req.message
        if demand_reconstruction_result and demand_reconstruction_result.get("handoff_requested"):
            force_brief_intake_from_demand_reconstruction = True
            demand_reconstruction_context = demand_reconstruction_result.get("demand_reconstruction_context") or demand_reconstruction_context
            blueprint = (demand_reconstruction_context or {}).get("blueprint") or {}
            source_message = (demand_reconstruction_context or {}).get("source_message") or req.message
            scheme_user_message = (
                f"{source_message}\n\n"
                "请把以上需求重构行动蓝图整理成设计任务书草稿，并进入正式任务书问诊。"
            )
            session = {**session, "demand_reconstruction_context": demand_reconstruction_context}
            if blueprint:
                session["conversation_drafts"] = list(session.get("conversation_drafts") or [])
        elif demand_reconstruction_result:
            reply = demand_reconstruction_result.get("reply", "我先为你做一轮需求重构。")
            intent = demand_reconstruction_result.get("intent", "demand_reconstruction_blueprint")
            drafts = session.get("conversation_drafts", [])
            upgrade_sig = None
            upgrade_suggested = False
            guidance_card = demand_reconstruction_result.get("guidance_card")
            demand_reconstruction_context = demand_reconstruction_result.get("demand_reconstruction_context")
            dialogue_layer = "demand_reconstruction"
            handoff_available = bool(demand_reconstruction_result.get("handoff_available", True))
            result = {
                "conv_s_step": session.get("conv_s_step", "dialogue"),
                "asked_gaps": session.get("asked_gaps", []),
            }
            blueprint = (demand_reconstruction_context or {}).get("blueprint") or {}
            logger.info(
                f"[dual_mode] DemandReconstruction handled: session={session_id}, "
                f"card={guidance_card and guidance_card.get('card_type')}, "
                f"source={blueprint.get('insight_source')}, llm_status={blueprint.get('llm_status')}"
            )

        from intelligent_project_analyzer.services.scheme_advisor_entry_service import (  # noqa: PLC0415
            SchemeAdvisorEntryService,
            is_scheme_advisor_entry_enabled,
            is_scheme_advisor_entry_llm_enabled,
        )

        if (not demand_reconstruction_result or force_brief_intake_from_demand_reconstruction) and is_scheme_advisor_entry_enabled():
            scheme_llm = _get_conv_llm() if is_scheme_advisor_entry_llm_enabled() else None
            scheme_service = SchemeAdvisorEntryService(llm=scheme_llm)
            loop = asyncio.get_event_loop()
            scheme_result = await loop.run_in_executor(
                None,
                lambda: scheme_service.handle_message(
                    session=session,
                    user_message=scheme_user_message,
                    in_response_to_card_id=req.in_response_to_card_id,
                    selected_option_id=selected_option_id,
                ),
            )
            if scheme_result:
                scheme_entry_handled = True
                reply = scheme_result.get("reply", "收到，继续告诉我更多。")
                intent = scheme_result.get("intent", "scheme_advisor_entry")
                drafts = session.get("conversation_drafts", [])
                upgrade_sig = None
                upgrade_suggested = False
                guidance_card = scheme_result.get("guidance_card")
                scheme_entry_state = scheme_result.get("scheme_entry_state")
                dialogue_layer = "brief_intake"
                handoff_available = False
                logger.info(
                    f"[dual_mode] SchemeAdvisorEntryV2 handled: session={session_id}, "
                    f"step={(scheme_entry_state or {}).get('step')}, card={guidance_card and guidance_card.get('card_type')}"
                )

        # ── 4. 默认：同步调用 ConversationEngine ──
        if (not demand_reconstruction_result or force_brief_intake_from_demand_reconstruction) and not scheme_entry_handled:
            from intelligent_project_analyzer.workflow.conversation_engine import ConversationEngine
            from langchain_core.messages import AIMessage as _AM, HumanMessage as _HM

            # 把会话历史转换为 LangChain messages，让 LLM 保持上下文
            _role_map = {"user": _HM, "assistant": _AM}
            lc_history = [
                _role_map[h["role"]](content=h.get("content", ""))
                for h in session.get("conversation_history_v2", [])
                if h.get("role") in _role_map
            ]

            engine = ConversationEngine(llm=_get_conv_llm())
            state_patch = {
                "user_input": req.message,
                "session_id": session_id,
                "system_mode": session.get("system_mode", "conversation"),
                "conversation_drafts": session.get("conversation_drafts", []),
                "cognition_indicators": session.get("cognition_indicators"),
                "upgrade_signal": session.get("upgrade_signal"),
                "metadata": session.get("metadata", {}),
                # 历史消息（LangChain 格式，供 _handle_knowledge_qa 传给 LLM）
                "conversation_history": lc_history,
                # 引导卡片交互字段
                "in_response_to_card_id": req.in_response_to_card_id,
                "selected_option_id": selected_option_id,
                "card_response": req.card_response,
                "pending_guidance_card": session.get("pending_guidance_card"),
                # S-step 流水线状态（跨轮次持久化）
                "conv_s_step": session.get("conv_s_step", "dialogue"),
                "asked_gaps": session.get("asked_gaps", []),
            }
            # engine.execute() 是同步阻塞调用（内含 LLM HTTP 请求），
            # 必须在线程池中运行，否则会卡死 asyncio event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, engine.execute, state_patch)

            reply = result.get("conversation_reply", "收到，继续告诉我更多。")
            intent = result.get("conversation_intent", "knowledge_qa")
            drafts = result.get("conversation_drafts", session.get("conversation_drafts", []))
            upgrade_sig = result.get("upgrade_signal")
            cognition = result.get("cognition_indicators")
            upgrade_suggested = bool(upgrade_sig) or (
                isinstance(cognition, dict) and cognition.get("should_trigger_upgrade", False)
            )
            guidance_card = result.get("pending_guidance_card")
            dialogue_layer = "project" if session.get("system_mode") == "project" else "demand_reconstruction"
            handoff_available = bool(upgrade_suggested)

    except DemandReconstructionUnavailable as exc:
        logger.error(
            "[dual_mode] DemandReconstruction unavailable: "
            f"session={session_id}, code={exc.error_code}, diagnostics={exc.diagnostics}"
        )
        raise HTTPException(
            status_code=503,
            detail={
                "code": exc.error_code,
                "message": exc.user_message,
            },
        ) from exc

    except Exception as exc:
        logger.error(
            f"[dual_mode] ConversationEngine 调用异常:\n{traceback.format_exc()}"
        )
        reply = "收到你的消息，稍后为你处理。"
        intent = "knowledge_qa"
        drafts = session.get("conversation_drafts", [])
        upgrade_sig = None
        upgrade_suggested = False
        guidance_card = None
        dialogue_layer = "demand_reconstruction"
        handoff_available = False

    # ── 4. 回写会话 ──
    conversation_history.append(
        {
            "role": "assistant",
            "content": reply,
            "intent": intent,
            "guidance_card": guidance_card,
            "timestamp": datetime.now().isoformat(),
        }
    )
    session_update = {
        "conversation_history_v2": conversation_history,
        "user_input": session.get("user_input") or message_title,
        "user_id": session.get("user_id") or user_id,
        "conversation_drafts": drafts,
        "upgrade_signal": upgrade_sig,
        "pending_guidance_card": guidance_card,
        "demand_reconstruction_context": demand_reconstruction_context,
        "dialogue_layer": dialogue_layer,
        "last_active": datetime.now().isoformat(),
        # 持久化 S-step 流水线状态（engine 可能已推进步骤）
        "conv_s_step": result.get("conv_s_step", session.get("conv_s_step", "dialogue")),
        "asked_gaps": result.get("asked_gaps", session.get("asked_gaps", [])),
    }
    if scheme_entry_state is not None:
        session_update["scheme_advisor_entry_v2"] = scheme_entry_state
    await sm.update(
        session_id,
        session_update,
    )
    _invalidate_sessions_cache(session.get("user_id") or user_id)
    await _archive_conversation_snapshot(session_id, {**session, **session_update, "session_id": session_id})

    return ConversationMessageResponse(
        session_id=session_id,
        reply=reply,
        intent=intent,
        drafts_count=len(drafts),
        upgrade_suggested=upgrade_suggested,
        upgrade_signal=upgrade_sig,
        system_mode=session.get("system_mode", "conversation"),
        guidance_card=guidance_card,
        dialogue_layer=dialogue_layer,
        handoff_available=handoff_available,
        demand_reconstruction_context=demand_reconstruction_context,
        reconstruction_type=(demand_reconstruction_context or {}).get("reconstruction_type"),
        artifact_name=(demand_reconstruction_context or {}).get("artifact_name"),
    )


@router.get(
    "/conversation/{session_id}/drafts",
    response_model=DraftsResponse,
    summary="获取对话草稿列表",
)
async def get_conversation_drafts(session_id: str) -> DraftsResponse:
    """返回当前会话积累的草稿对象列表。"""
    session = await _require_session(session_id)
    raw_drafts: List[Dict[str, Any]] = session.get("conversation_drafts", [])
    upgrade_sig = session.get("upgrade_signal")
    cognition = session.get("cognition_indicators")
    upgrade_suggested = bool(upgrade_sig) or (
        isinstance(cognition, dict) and cognition.get("should_trigger_upgrade", False)
    )

    draft_items: List[DraftItem] = []
    for d in raw_drafts:
        if not isinstance(d, dict):
            continue
        draft_items.append(
            DraftItem(
                draft_id=d.get("draft_id", uuid.uuid4().hex[:8]),
                draft_type=d.get("draft_type", "unknown"),
                content=d.get("content", {}),
                status=d.get("status", "draft"),
                created_at=d.get("created_at", ""),
            )
        )

    return DraftsResponse(
        session_id=session_id,
        drafts=draft_items,
        total=len(draft_items),
        upgrade_suggested=upgrade_suggested,
    )


@router.post(
    "/conversation/{session_id}/upgrade",
    response_model=UpgradeResponse,
    summary="确认升级到项目态",
)
async def confirm_upgrade(session_id: str, req: UpgradeRequest) -> UpgradeResponse:
    """
    用户确认将对话态升级为项目态。

    - 调用 upgrade_compiler() 将草稿压缩为 RawBriefPacket
    - 将 system_mode 置为 "project"
    - 触发后续门禁节点（异步，通过 WebSocket 通知）
    """
    if not req.confirmed:
        raise HTTPException(status_code=400, detail="confirmed 必须为 True")

    session = await _require_session(session_id)
    current_mode = session.get("system_mode", "conversation")

    if current_mode == "project":
        return UpgradeResponse(
            session_id=session_id,
            status="already_in_project_mode",
            system_mode="project",
            message="会话已处于项目态，无需重复升级。",
        )

    drafts: List[Dict[str, Any]] = session.get("conversation_drafts", [])
    if not drafts:
        return UpgradeResponse(
            session_id=session_id,
            status="not_ready",
            system_mode=current_mode,
            message="当前草稿为空，请先在对话中描述更多项目信息后再升级。",
        )

    # 调用 upgrade_compiler
    try:
        from intelligent_project_analyzer.workflow.mode_router import upgrade_compiler

        raw_brief = upgrade_compiler(drafts, session_id)
        raw_brief_dict = raw_brief.model_dump()
    except Exception as exc:
        logger.error(f"[dual_mode] upgrade_compiler 失败: {exc}")
        raise HTTPException(status_code=500, detail=f"升级编译失败: {exc}")

    sm = await _get_sm()
    await sm.update(
        session_id,
        {
            "system_mode": "project",
            "status": "gate_pending",
            "raw_brief_packet": raw_brief_dict,
            "upgrade_confirmed_at": datetime.now().isoformat(),
        },
    )
    logger.info(f"[dual_mode] 会话 {session_id} 升级到项目态")

    return UpgradeResponse(
        session_id=session_id,
        status="upgraded",
        system_mode="project",
        raw_brief_packet=raw_brief_dict,
        message="已成功升级到项目态，门禁节点将开始评估。",
    )


@router.get(
    "/session/{session_id}/mode",
    response_model=SessionModeResponse,
    summary="查询会话当前 system_mode",
)
async def get_session_mode(session_id: str) -> SessionModeResponse:
    """返回会话的当前状态快照（mode、冻结、任务书、蓝图、归档）。"""
    session = await _require_session(session_id)
    return SessionModeResponse(
        session_id=session_id,
        system_mode=session.get("system_mode", "conversation"),
        requirements_frozen=bool(session.get("requirements_frozen", False)),
        has_task_book=session.get("design_task_book") is not None,
        has_blueprint=session.get("execution_blueprint") is not None,
        has_archive=session.get("project_archive") is not None,
    )


@router.post("/project/gate", response_model=GateResponse, summary="门禁节点评估")
async def run_gate(req: GateRequest) -> GateResponse:
    """
    对一段原始用户输入执行门禁评估。

    内部调用 GateNode.execute()；同步返回 GateDecision。
    """
    session = await _require_session(req.session_id)

    try:
        from intelligent_project_analyzer.workflow.nodes.gate_node import GateNode

        gate = GateNode()
        state_patch = {
            "user_input": req.raw_user_prompt,
            "session_id": req.session_id,
            "system_mode": session.get("system_mode", "project"),
            "gate_decision": None,
            "metadata": session.get("metadata", {}),
            "scheme_advisor_entry_v2": session.get("scheme_advisor_entry_v2"),
            "raw_brief_packet": session.get("raw_brief_packet"),
            "pending_formal_assets": session.get("pending_formal_assets"),
        }
        # GateNode.execute 返回 Command；提取 update 字段中的 gate_decision
        result = gate.execute(state_patch)  # type: ignore[arg-type]
        update = getattr(result, "update", {}) or {}
        gate_decision = update.get("gate_decision")
        gate_decision_dict = gate_decision.model_dump() if hasattr(gate_decision, "model_dump") else gate_decision or {}
    except Exception as exc:
        logger.error(f"[dual_mode] GateNode 调用失败: {exc}")
        raise HTTPException(status_code=500, detail=f"门禁评估失败: {exc}")

    gate_status = gate_decision_dict.get("status", "CONVERSATION")
    interaction_state = gate_decision_dict.get("interaction_state")
    gap_questions = (
        gate_decision_dict.get("gap_questions")
        or gate_decision_dict.get("required_preconditions")
        or [gap.get("description") for gap in gate_decision_dict.get("gap_diagnosis", []) if isinstance(gap, dict)]
    )

    # 将门禁结果写回会话
    sm = await _get_sm()
    session_patch = {"gate_decision": gate_decision_dict}
    for key in ("formal_gate_status", "pending_formal_assets", "system_mode", "current_stage"):
        if key in update:
            session_patch[key] = update[key]
    await sm.update(req.session_id, session_patch)

    msg_map = {
        "CONTINUE": "门禁通过，请求可以进入需求分析流程。",
        "continue": "门禁通过，请求可以进入需求分析流程。",
        "CONVERSATION": "需要补充更多信息，请参照 gap_questions。",
        "conversation": "需要补充更多信息，请参照 gap_questions。",
        "CONDITIONAL_CONTINUE": "条件满足后可继续，请参照 gap_questions。",
        "conditional_continue": "条件满足后可继续，请参照 gap_questions。",
        "REJECT": "请求不符合要求，已拒绝。",
        "reject": "请求不符合要求，已拒绝。",
        "NEED_MORE_PREREQUISITE": "前置条件不足，需要先满足基础要求。",
        "need_more_prerequisite": "前置条件不足，需要先满足基础要求。",
    }

    return GateResponse(
        session_id=req.session_id,
        gate_status=gate_status,
        interaction_state=interaction_state,
        gap_questions=gap_questions,
        gate_decision=gate_decision_dict,
        message=msg_map.get(gate_status, "门禁评估完成。"),
    )


@router.get(
    "/project/{session_id}/taskbook",
    response_model=TaskBookResponse,
    summary="读取 DesignTaskBook",
)
async def get_task_book(session_id: str) -> TaskBookResponse:
    """读取当前会话的 DesignTaskBook（需求冻结后才有值）。"""
    session = await _require_session(session_id)
    task_book = session.get("design_task_book")
    frozen = bool(session.get("requirements_frozen", False))

    if task_book is None and frozen:
        raise HTTPException(status_code=404, detail="DesignTaskBook 尚未生成，请检查需求分析流程是否完成。")

    return TaskBookResponse(
        session_id=session_id,
        task_book=task_book,
        frozen=frozen,
        retrieved_at=datetime.now().isoformat(),
    )


@router.get(
    "/project/{session_id}/blueprint",
    response_model=BlueprintResponse,
    summary="读取 ExecutionBlueprint",
)
async def get_blueprint(session_id: str) -> BlueprintResponse:
    """读取当前会话的 ExecutionBlueprint。"""
    session = await _require_session(session_id)
    blueprint = session.get("execution_blueprint")
    frozen = bool(session.get("requirements_frozen", False))

    return BlueprintResponse(
        session_id=session_id,
        blueprint=blueprint,
        frozen=frozen,
        retrieved_at=datetime.now().isoformat(),
    )


@router.post("/project/{session_id}/delta", response_model=DeltaResponse, summary="提交增量修改")
async def submit_delta(session_id: str, req: DeltaRequest) -> DeltaResponse:
    """
    提交局部增量修改请求。

    - 调用 DeltaRouter 判断路由方向（delta / derived）
    - 将路由结果和 impact_graph 写回会话
    """
    session = await _require_session(session_id)

    if not session.get("requirements_frozen"):
        raise HTTPException(status_code=400, detail="需求尚未冻结，无法提交增量修改。请先完成需求分析流程。")

    try:
        from intelligent_project_analyzer.workflow.nodes.delta_router import DeltaRouter

        delta_router = DeltaRouter()
        state_patch = {
            "user_input": req.modification_text,
            "session_id": session_id,
            "system_mode": session.get("system_mode", "project"),
            "design_task_book": session.get("design_task_book"),
            "execution_blueprint": session.get("execution_blueprint"),
            "requirements_frozen": True,
            "metadata": session.get("metadata", {}),
        }
        result = delta_router.route(state_patch)  # type: ignore[arg-type]
        update = getattr(result, "update", {}) or {}
        impact_graph = update.get("impact_graph")
        impact_dict = impact_graph.model_dump() if hasattr(impact_graph, "model_dump") else impact_graph or {}
        goto = getattr(result, "goto", "execution_orchestrator")
    except Exception as exc:
        logger.error(f"[dual_mode] DeltaRouter 失败: {exc}")
        raise HTTPException(status_code=500, detail=f"增量路由失败: {exc}")

    delta_type = "derived" if impact_dict.get("requires_derived_project") else "delta"

    sm = await _get_sm()
    await sm.update(
        session_id,
        {
            "is_delta_modification": True,
            "delta_router_state": {"modification_text": req.modification_text, "goto": goto},
            "impact_graph": impact_dict,
        },
    )

    msg_map = {
        "delta": "已识别为局部修改，将直接更新相关节点。",
        "derived": "修改幅度较大，将创建派生项目版本。",
    }
    return DeltaResponse(
        session_id=session_id,
        delta_type=delta_type,
        routed_to=goto,
        impact_graph=impact_dict,
        message=msg_map.get(delta_type, "增量路由完成。"),
    )


@router.get(
    "/project/{session_id}/archive",
    response_model=ArchiveResponse,
    summary="读取 ProjectArchive",
)
async def get_project_archive(session_id: str) -> ArchiveResponse:
    """读取当前会话的 ProjectArchive（项目归档快照）。"""
    session = await _require_session(session_id)
    archive = session.get("project_archive")
    if archive is None:
        raise HTTPException(
            status_code=404,
            detail="ProjectArchive 尚未生成。归档在执行态完成并交付后自动创建。",
        )
    return ArchiveResponse(
        session_id=session_id,
        archive=archive,
        retrieved_at=datetime.now().isoformat(),
    )
