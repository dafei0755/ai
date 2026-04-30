"""
模式路由器 — 双态架构中负责在对话态与项目态之间切换的路由节点

Copilot 生成（2026-03-15）

路由逻辑：
  1. 初次进入 → GateNode 已产出 gate_decision
     - interaction_state == "conversation" → conversation_engine
     - interaction_state == "project"      → requirements_s1
     - interaction_state == "rejected"     → input_rejected

  2. 对话态中出现 upgrade_signal（用户确认升级）
     → 调用升级编译器，将草稿 → RawBriefPacket，切换到 requirements_s1

  3. 项目执行中途用户发起轻问答
     → 临时插入 conversation_engine，返回后继续原项目态节点

  4. DeltaModification 分支
     → delta_router（增量派生）

本模块中的 upgrade_compiler() 负责：
  draft 对象列表 → RawBriefPacket（含 prefill_from_drafts 映射）
  + 将 state.system_mode 切换为 "project"
  + 设置 state.gate_decision.interaction_state = "project"
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from langgraph.types import Command
from loguru import logger

from intelligent_project_analyzer.core.domain_objects import (
    GateDecision,
    GateStatus,
    RawBriefPacket,
)
from intelligent_project_analyzer.core.state import ProjectAnalysisState


# ---------------------------------------------------------------------------
# 工具：从草稿列表编译 RawBriefPacket
# ---------------------------------------------------------------------------


def upgrade_compiler(
    drafts: List[Dict[str, Any]],
    session_id: str = "",
) -> RawBriefPacket:
    """
    将对话态积累的草稿对象列表编译为 RawBriefPacket。

    映射规则：
      IntentSeed            → raw_text / project_type hint
      ProblemFrameDraft     → core_problem_statement
      DirectionCandidatePack→ style_keywords
      ConflictPack          → constraint_hints（冲突描述）
      BoundaryDraft         → site_info / area_info
      ConsensusPack         → confirmed_facts
    """
    raw_text_parts: List[str] = []
    project_type: Optional[str] = None
    style_keywords: List[str] = []
    confirmed_facts: List[str] = []
    constraint_hints: List[str] = []
    site_info: Optional[str] = None
    area_info: Optional[str] = None

    for draft in drafts:
        dtype = draft.get("draft_type", "")

        if dtype == "IntentSeed":
            raw_text_parts.append(draft.get("content", ""))
            kws = draft.get("keywords", [])
            if kws:
                raw_text_parts.extend(kws[:3])

        elif dtype == "ProblemFrameDraft":
            problem = draft.get("core_problem", "")
            if problem:
                raw_text_parts.append(problem)

        elif dtype == "DirectionCandidatePack":
            candidates = draft.get("candidates", [])
            for c in candidates[:3]:
                desc = c.get("description", "") if isinstance(c, dict) else str(c)
                if desc:
                    style_keywords.append(desc)

        elif dtype == "ConflictPack":
            conflicts = draft.get("conflicts", [])
            for cf in conflicts[:2]:
                desc = cf.get("description", "") if isinstance(cf, dict) else str(cf)
                if desc:
                    constraint_hints.append(desc)

        elif dtype == "BoundaryDraft":
            site_info = site_info or draft.get("site_description", "")
            area_info = area_info or str(draft.get("area_sqm", ""))

        elif dtype == "ConsensusPack":
            facts = draft.get("facts", [])
            confirmed_facts.extend(facts[:5])

    raw_prompt = " / ".join(filter(None, raw_text_parts)) or "（对话态积累）"

    prefill: Dict[str, Any] = {}
    if project_type:
        prefill["project_type"] = project_type
    if style_keywords:
        prefill["style_keywords"] = style_keywords
    if confirmed_facts:
        prefill["confirmed_facts"] = confirmed_facts
    if constraint_hints:
        prefill["constraint_hints"] = constraint_hints
    if site_info:
        prefill["site_info"] = site_info
    if area_info:
        prefill["area_info"] = area_info
    prefill["source_session_id"] = session_id
    prefill["prefilled_from_conversation"] = True

    return RawBriefPacket(
        raw_user_prompt=raw_prompt,
        prefill_from_drafts=prefill,
    )


# ---------------------------------------------------------------------------
# ModeRouter 节点
# ---------------------------------------------------------------------------


class ModeRouter:
    """
    模式路由器节点。

    LangGraph 注册示例：
        router = ModeRouter()
        graph.add_node("mode_router", router.route)
        graph.add_conditional_edges("mode_router", ...)
    """

    def route(
        self, state: ProjectAnalysisState
    ) -> Command[
        Literal[
            "conversation_engine",
            "requirements_s1",
            "delta_router",
            "input_rejected",
        ]
    ]:
        session_id: str = state.get("session_id", "unknown")
        system_mode: Optional[str] = state.get("system_mode")
        gate_raw: Optional[Dict[str, Any]] = state.get("gate_decision")
        upgrade_raw: Optional[Dict[str, Any]] = state.get("upgrade_signal")
        is_delta: Optional[bool] = state.get("is_delta_modification")

        logger.info(
            f"[{session_id}] ModeRouter — "
            f"system_mode={system_mode}, "
            f"gate={gate_raw and gate_raw.get('interaction_state')}, "
            f"upgrade_triggered={upgrade_raw and upgrade_raw.get('triggered')}"
        )

        # ── 增量修改分支 ──────────────────────────────────────────────
        if is_delta:
            logger.info(f"[{session_id}] 路由 → delta_router（增量修改）")
            return Command(goto="delta_router")

        # ── 用户在对话态中确认升级 ────────────────────────────────────
        if upgrade_raw and upgrade_raw.get("triggered") and upgrade_raw.get("user_accepted"):
            compiled_updates = self._do_upgrade(state, session_id)
            return Command(
                goto="requirements_s1",
                update=compiled_updates,
            )

        # ── 依据门禁决策路由 ─────────────────────────────────────────
        if gate_raw:
            interaction_state = gate_raw.get("interaction_state", "")

            if interaction_state == GateStatus.REJECTED.value:
                logger.info(f"[{session_id}] 路由 → input_rejected")
                return Command(goto="input_rejected")

            if interaction_state == GateStatus.PROJECT.value:
                logger.info(f"[{session_id}] 路由 → requirements_s1（项目态）")
                return Command(
                    goto="requirements_s1",
                    update={"system_mode": "project"},
                )

        # 默认：对话态
        logger.info(f"[{session_id}] 路由 → conversation_engine（对话态）")
        return Command(
            goto="conversation_engine",
            update={"system_mode": "conversation"},
        )

    # ------------------------------------------------------------------
    # 升级编译（对话态 → 项目态）
    # ------------------------------------------------------------------

    def _do_upgrade(
        self, state: ProjectAnalysisState, session_id: str
    ) -> Dict[str, Any]:
        """将草稿列表编译为 RawBriefPacket，写入 state，切换为项目态。"""
        drafts: List[Dict[str, Any]] = state.get("conversation_drafts") or []
        packet = upgrade_compiler(drafts, session_id=session_id)

        gate_raw = state.get("gate_decision") or {}
        gate_raw = {
            **gate_raw,
            "interaction_state": GateStatus.PROJECT.value,
            "upgraded_at": datetime.now().isoformat(),
        }

        logger.info(
            f"[{session_id}] 升级编译完成 — "
            f"raw_text={packet.raw_text[:60]}..."
        )

        return {
            "system_mode": "project",
            "gate_decision": gate_raw,
            "raw_brief_packet": packet.model_dump(),
        }
