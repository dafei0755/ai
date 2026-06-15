"""
门禁节点 — 双态架构入口治理

Copilot 生成（2026-03-15）
替代旧的 UnifiedInputValidatorNode，将门禁从「死板拦截器」重新定义为
「项目首诊医生 + 风险测试盘 + 状态路由器」。

职责链（顺序执行）：
  1. 安全校验       — 过滤不允许内容与高风险输入
  2. 合法性与边界校验 — 系统职责边界检查
  3. 可行性初判     — 最低可行条件检查
  4. 状态判定       — 判断进对话态 or 项目态
  5. 硬缺口诊断     — 提取最关键的 3 个硬缺口
  6. 极端条件发散   — 矛盾需求抛出 A/B 极端路径
  → 产出 GateDecision，写入 state.gate_decision

旧节点兼容：
  unified_input_validator_node.py → 标 deprecated，本节点为直接替代
"""

from __future__ import annotations

import re
from typing import Any, Dict, Literal, Optional

from langchain_core.language_models import BaseChatModel
from langgraph.types import Command
from loguru import logger

from intelligent_project_analyzer.core.domain_objects import (
    ExtremeOption,
    GapDiagnosis,
    GateDecision,
    GateStatus,
    InteractionState,
)
from intelligent_project_analyzer.core.state import AnalysisStage, ProjectAnalysisState


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

_SAFETY_DENY_PATTERNS = re.compile(
    r"(暴力|色情|违法|炸弹|武器|毒品|自杀|hack|exploit)",
    re.IGNORECASE,
)

_PROJECT_SIGNAL_KEYWORDS = (
    "方案", "设计", "项目", "民宿", "住宅", "商业", "改造",
    "规划", "平米", "预算", "风格", "施工", "装修",
)

# 对话态反向判据关键词（保持对话态不升级）
_STAY_CONVERSATION_PATTERNS = (
    "随便问", "随口问", "案例", "规范", "有没有", "闲聊",
    "了解一下", "参考", "推荐", "什么感觉", "会不会",
)

# 最低可行条件缺失提示
_MIN_VIABLE_FIELDS = ("项目对象", "大概面积", "主要用途")


# ---------------------------------------------------------------------------
# GateNode
# ---------------------------------------------------------------------------


class GateNode:
    """
    门禁节点

    用法（LangGraph 注册）：
        gate = GateNode(llm=llm_model)
        graph.add_node("gatekeeper", gate.execute)
    """

    def __init__(self, llm: Optional[BaseChatModel] = None) -> None:
        self._llm = llm

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def execute(
        self,
        state: ProjectAnalysisState,
    ) -> Command[Literal["conversation_engine", "requirements_s1", "input_rejected"]]:
        """
        门禁主执行逻辑。

        Returns:
            Command → conversation_engine  （对话态）
            Command → requirements_s1      （项目态主链）
            Command → input_rejected       （拒绝）
        """
        logger.info("=" * 80)
        logger.info("🚧 门禁节点 — 项目首诊启动")
        logger.info("=" * 80)

        user_input: str = state.get("user_input", "")
        session_id: str = state.get("session_id", "unknown")

        # ── Step 1: 安全校验 ──────────────────────────────────────────
        safety_result = self._check_safety(user_input)
        if not safety_result["passed"]:
            decision = GateDecision(
                status=GateStatus.REJECT,
                reason=safety_result["reason"],
                interaction_state=InteractionState.CONVERSATION,
            )
            logger.warning(f"[{session_id}] 安全校验拒绝: {safety_result['reason']}")
            return Command(
                update={
                    "gate_decision": decision.model_dump(),
                    "current_stage": AnalysisStage.ERROR.value,
                    "rejection_reason": "safety_violation",
                    "rejection_message": "该内容不符合系统使用规范，无法处理。",
                },
                goto="input_rejected",
            )

        # ── Step 2: 合法性与边界校验 ──────────────────────────────────
        boundary_notes = self._check_boundary(user_input)

        entry_gate = self._evaluate_scheme_advisor_entry_gate(state, boundary_notes)
        if entry_gate is not None:
            decision, goto_node, next_mode, extra_update = entry_gate
            logger.info(
                f"[{session_id}] Scheme Advisor entry gate -> {goto_node} | "
                f"status={decision.status.value}"
            )
            return Command(
                update={
                    "gate_decision": decision.model_dump(),
                    "system_mode": next_mode,
                    "current_stage": AnalysisStage.REQUIREMENT_COLLECTION.value,
                    **extra_update,
                },
                goto=goto_node,
            )

        # ── Step 3: 可行性初判 ────────────────────────────────────────
        feasibility = self._check_feasibility(user_input)
        if not feasibility["viable"]:
            decision = GateDecision(
                status=GateStatus.NEED_MORE_PREREQUISITE,
                reason=feasibility["reason"],
                required_preconditions=feasibility["missing"],
                boundary_notes=boundary_notes,
                interaction_state=InteractionState.CONVERSATION,
            )
            logger.info(f"[{session_id}] 可行性不足，路由到对话态补充信息")
            return Command(
                update={
                    "gate_decision": decision.model_dump(),
                    "system_mode": "conversation",
                    "current_stage": AnalysisStage.REQUIREMENT_COLLECTION.value,
                },
                goto="conversation_engine",
            )

        # ── Step 4: 状态判定（对话态 or 项目态）──────────────────────
        interaction_state = self._determine_interaction_state(user_input, state)

        # ── Step 5: 硬缺口诊断 ───────────────────────────────────────
        gaps = self._diagnose_gaps(user_input)

        # ── Step 6: 极端条件发散 ─────────────────────────────────────
        extreme_options = self._detect_extreme_conflict(user_input)

        # ── 构造 GateDecision ─────────────────────────────────────────
        if interaction_state == InteractionState.CONVERSATION:
            status = GateStatus.CONVERSATION
            goto_node = "conversation_engine"
            next_mode = "conversation"
        else:
            status = GateStatus.CONTINUE
            goto_node = "requirements_s1"
            next_mode = "project"

        decision = GateDecision(
            status=status,
            reason=f"状态判定结果: {interaction_state.value}",
            boundary_notes=boundary_notes,
            interaction_state=interaction_state,
            gap_diagnosis=gaps,
            extreme_options=extreme_options,
        )

        logger.info(
            f"[{session_id}] 门禁通过 → {goto_node} | "
            f"gaps={len(gaps)} | extremes={len(extreme_options)}"
        )

        return Command(
            update={
                "gate_decision": decision.model_dump(),
                "system_mode": next_mode,
                "current_stage": AnalysisStage.REQUIREMENT_COLLECTION.value,
            },
            goto=goto_node,
        )

    # ------------------------------------------------------------------
    # Step 1: 安全校验
    # ------------------------------------------------------------------

    def _check_safety(self, text: str) -> Dict[str, Any]:
        if _SAFETY_DENY_PATTERNS.search(text):
            return {"passed": False, "reason": "输入包含不允许的内容"}
        return {"passed": True, "reason": ""}

    # ------------------------------------------------------------------
    # Step 2: 合法性与边界校验
    # ------------------------------------------------------------------

    def _check_boundary(self, text: str) -> list[str]:
        notes: list[str] = []
        if len(text) > 8000:
            notes.append("输入超过 8000 字，系统将截取前 8000 字处理。")
        return notes

    def _evaluate_scheme_advisor_entry_gate(
        self, state: ProjectAnalysisState, boundary_notes: list[str]
    ) -> Optional[tuple[GateDecision, str, str, Dict[str, Any]]]:
        entry_state = state.get("scheme_advisor_entry_v2") or {}
        if not isinstance(entry_state, dict) or not entry_state:
            return None

        step = entry_state.get("step")
        if step != "version_selected":
            decision = GateDecision(
                status=GateStatus.NEED_MORE_PREREQUISITE,
                reason="Scheme Advisor entry has not completed version selection.",
                required_preconditions=["scheme_advisor_version_selection"],
                boundary_notes=[
                    *boundary_notes,
                    "Complete Scheme Advisor version selection before entering the formal project gate.",
                ],
                interaction_state=InteractionState.CONVERSATION,
            )
            return decision, "conversation_engine", "conversation", {
                "formal_gate_status": "entry_not_ready",
            }

        pending_assets = self._extract_pending_formal_assets(state, entry_state)
        if not pending_assets:
            return None

        decision = GateDecision(
            status=GateStatus.CONDITIONAL_CONTINUE,
            reason="Scheme Advisor entry is selected, but formal project assets still need calibration.",
            required_preconditions=pending_assets,
            boundary_notes=[
                *boundary_notes,
                "Missing formal assets are calibration items, not entry blockers.",
            ],
            interaction_state=InteractionState.PROJECT,
        )
        return decision, "requirements_s1", "project", {
            "formal_gate_status": "calibration_required",
            "pending_formal_assets": pending_assets,
        }

    def _extract_pending_formal_assets(
        self, state: ProjectAnalysisState, entry_state: Dict[str, Any]
    ) -> list[str]:
        candidates = [
            state.get("pending_formal_assets"),
            entry_state.get("pending_formal_assets"),
            (entry_state.get("profile") or {}).get("pending_formal_assets"),
            ((entry_state.get("profile") or {}).get("maturity") or {}).get("pending"),
        ]

        raw_brief = state.get("raw_brief_packet") or {}
        if isinstance(raw_brief, dict):
            prefill = raw_brief.get("prefill_from_drafts") or {}
            if isinstance(prefill, dict):
                candidates.append(prefill.get("pending_formal_assets"))

        pending: list[str] = []
        for candidate in candidates:
            if isinstance(candidate, str):
                values = [candidate]
            elif isinstance(candidate, list):
                values = candidate
            else:
                continue
            for value in values:
                if isinstance(value, str) and value and value not in pending:
                    pending.append(value)
        return pending

    # ------------------------------------------------------------------
    # Step 3: 可行性初判
    # ------------------------------------------------------------------

    def _check_feasibility(self, text: str) -> Dict[str, Any]:
        """
        轻量规则判断：输入是否包含最低限度的项目信息。
        如果完全是零散问句，让其走对话态而非拒绝。
        """
        # 纯问句 → 可行（对话态处理）
        if text.strip().endswith("？") or text.strip().endswith("?"):
            return {"viable": True, "reason": "问句形式，路由对话态", "missing": []}

        # 含项目信号词 → 检查最低字段
        has_signal = any(kw in text for kw in _PROJECT_SIGNAL_KEYWORDS)
        if has_signal and len(text) < 15:
            return {
                "viable": False,
                "reason": "项目描述过于简短，缺少基本信息",
                "missing": list(_MIN_VIABLE_FIELDS),
            }

        return {"viable": True, "reason": "通过可行性初判", "missing": []}

    # ------------------------------------------------------------------
    # Step 4: 状态判定
    # ------------------------------------------------------------------

    def _determine_interaction_state(
        self, text: str, state: ProjectAnalysisState
    ) -> InteractionState:
        """
        判断当前输入应归属对话态还是项目态。

        对话态反向判据（满足任一 → 留对话态）：
          - 纯问句 / 随口问 / 案例查询 / 灵感试探
          - 不含明确项目名词信号

        项目态判据：
          - 含有 2 个以上项目信号词
          - 明确提到"做方案 / 需要帮助 / 完整方案"等
        """
        # 反向判据先行
        for pattern in _STAY_CONVERSATION_PATTERNS:
            if pattern in text:
                return InteractionState.CONVERSATION

        if text.strip().endswith("？") or text.strip().endswith("?"):
            return InteractionState.CONVERSATION

        # 项目信号计数
        signal_count = sum(1 for kw in _PROJECT_SIGNAL_KEYWORDS if kw in text)
        if signal_count >= 2:
            return InteractionState.PROJECT

        # 用户在 state 里已经处于项目态 → 保持
        if state.get("system_mode") == "project":
            return InteractionState.PROJECT

        return InteractionState.CONVERSATION

    # ------------------------------------------------------------------
    # Step 5: 硬缺口诊断（最多 3 条）
    # ------------------------------------------------------------------

    def _diagnose_gaps(self, text: str) -> list[GapDiagnosis]:
        gaps: list[GapDiagnosis] = []

        gap_rules = [
            ("选址", "项目具体地点或选址尚未明确", "blocker"),
            ("面积", "建筑或空间面积缺失", "major"),
            ("预算", "预算范围未提及", "major"),
            ("风格", "风格偏好尚未明确", "minor"),
        ]

        for idx, (keyword, desc, severity) in enumerate(gap_rules):
            if keyword not in text:
                gaps.append(
                    GapDiagnosis(
                        gap_index=idx,
                        description=desc,
                        severity=severity,  # type: ignore[arg-type]
                    )
                )
            if len(gaps) >= 3:
                break

        return gaps

    # ------------------------------------------------------------------
    # Step 6: 极端条件发散
    # ------------------------------------------------------------------

    def _detect_extreme_conflict(self, text: str) -> list[ExtremeOption]:
        """
        检测「最低预算 + 顶级效果」等极端矛盾，抛出两条极端路径。
        """
        has_low_budget = any(w in text for w in ("最低预算", "省钱", "便宜", "少花"))
        has_high_quality = any(w in text for w in ("顶级", "最好", "高端", "奢华", "精品"))

        if has_low_budget and has_high_quality:
            return [
                ExtremeOption(
                    label="A 极省",
                    description="以最低成本完成基础功能，放弃高端材料与定制设计",
                    trade_offs=["外观普通", "耐久性有限", "定制化程度低"],
                ),
                ExtremeOption(
                    label="B 极好",
                    description="不限预算追求最高品质，优先品牌材料与顶级工艺",
                    trade_offs=["成本大幅超出原始预期", "工期拉长", "运营成本较高"],
                ),
            ]
        return []
