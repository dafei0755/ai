"""
四级动作门禁

Copilot 生成（2026-03-15）

职责：
  在实施执行阶段，对所有外部动作调用进行四级门控：
    A 类：安全认知动作（私有检索、基线对比、草稿编撰）→ 自动，无阻塞
    B 类：外部取证动作（广域网搜索、外部案例抓取） → 自动 + 强审计留痕
    C 类：高成本生成动作（批量图像、重资源调用）    → Budget Guard 前置熔断
    D 类：不可逆 / 现实操作（核心区修改、外发指令） → 阻断级，强制人工 Confirm

设计原则：
  - 门控逻辑与业务节点解耦，任何执行层节点均可调用 RiskGateEngine
  - C 类超配额时返回 GateOutcome(blocked=True)，由调用方决定如何提示用户
  - D 类通过 LangGraph Interrupt 机制暂停流程，等待人工放行
  - 门控结果全部记录到 audit_trail，支持事后审计

使用示例：
    engine = RiskGateEngine()
    outcome = engine.check("generation/image", context={"role": "designer"}, call_counts={"generation": 5})
    if outcome.blocked:
        # C 类超配额 → 提示用户
        ...
    elif outcome.needs_confirm:
        # D 类 → 应由 LangGraph 上层触发 Interrupt
        ...
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


# ---------------------------------------------------------------------------
# 枚举与数据结构
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    """四级动作门禁等级"""

    A = "A"  # 安全认知：私有检索、基线对比、草稿编撰
    B = "B"  # 外部取证：广域网搜索、外部案例抓取
    C = "C"  # 高成本生成：批量图像、重资源调用
    D = "D"  # 不可逆 / 现实操作：核心区修改、外发指令


# 动作名称 → 门禁等级
_ACTION_GATE_MAP: Dict[str, RiskLevel] = {
    # A 类：安全认知
    "query_knowledge_base": RiskLevel.A,
    "baseline_compare": RiskLevel.A,
    "draft_compile": RiskLevel.A,
    "reasoning_evaluate": RiskLevel.A,
    "validate_constraints": RiskLevel.A,

    # B 类：外部取证（强审计）
    "search_web": RiskLevel.B,
    "fetch_external_case": RiskLevel.B,
    "crawl_reference": RiskLevel.B,

    # C 类：高成本生成
    "generate_image": RiskLevel.C,
    "generate_render": RiskLevel.C,
    "generate_text_package": RiskLevel.C,
    "assemble_chart": RiskLevel.C,
    "regenerate_delta": RiskLevel.C,

    # D 类：不可逆 / 现实操作
    "modify_frozen_zone": RiskLevel.D,
    "send_external_api": RiskLevel.D,
    "auto_submit_order": RiskLevel.D,
    "push_report_external": RiskLevel.D,
}

# 每类技能的默认 Budget Guard 配额（可被 ExecutionBlueprint.budget_guard 覆盖）
_DEFAULT_C_BUDGET = 15   # C 类每会话最多 15 次


class ActionRequest:
    """动作调用请求"""

    def __init__(
        self,
        action_name: str,
        context: Optional[Dict[str, Any]] = None,
        description: str = "",
    ) -> None:
        self.request_id = uuid.uuid4().hex[:8]
        self.action_name = action_name
        self.context = context or {}
        self.description = description
        self.requested_at = datetime.now().isoformat()

    def risk_level(self) -> RiskLevel:
        """从动作名称推断门禁等级，未知动作默认为 B 类"""
        return _ACTION_GATE_MAP.get(self.action_name, RiskLevel.B)


class GateOutcome:
    """门禁检查结果"""

    def __init__(
        self,
        request_id: str,
        action_name: str,
        level: RiskLevel,
        allowed: bool,
        blocked: bool = False,
        needs_confirm: bool = False,
        block_reason: str = "",
        audit_record: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.request_id = request_id
        self.action_name = action_name
        self.level = level
        self.allowed = allowed
        self.blocked = blocked
        self.needs_confirm = needs_confirm
        self.block_reason = block_reason
        self.audit_record = audit_record or {}
        self.checked_at = datetime.now().isoformat()

    @property
    def can_proceed(self) -> bool:
        return self.allowed and not self.blocked and not self.needs_confirm

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "action_name": self.action_name,
            "level": self.level.value,
            "allowed": self.allowed,
            "blocked": self.blocked,
            "needs_confirm": self.needs_confirm,
            "block_reason": self.block_reason,
            "checked_at": self.checked_at,
        }


# ---------------------------------------------------------------------------
# RiskGateEngine
# ---------------------------------------------------------------------------


class RiskGateEngine:
    """
    四级动作门禁引擎。

    用法：
        engine = RiskGateEngine(budget_override={"generate_image": 10})
        outcome = engine.check(request, call_counts={"generate_image": 3})
        if outcome.can_proceed:
            # 执行动作
            ...
        elif outcome.blocked:
            # C 类超配额：向用户显示 budget_guard_alert
            ...
        elif outcome.needs_confirm:
            # D 类：上层触发 LangGraph Interrupt，等待人工确认
            ...
    """

    def __init__(
        self,
        budget_override: Optional[Dict[str, int]] = None,
        audit_trail: Optional[List[Dict[str, Any]]] = None,
        session_id: str = "unknown",
    ) -> None:
        self._budget: Dict[str, int] = budget_override or {}
        self._audit_trail: List[Dict[str, Any]] = audit_trail if audit_trail is not None else []
        self._session_id = session_id

    @property
    def audit_trail(self) -> List[Dict[str, Any]]:
        return list(self._audit_trail)

    # ------------------------------------------------------------------
    # 主检查入口
    # ------------------------------------------------------------------

    def check(
        self,
        request: ActionRequest,
        call_counts: Optional[Dict[str, int]] = None,
    ) -> GateOutcome:
        """
        对一次动作调用进行门禁检查。

        Args:
            request:     动作调用请求
            call_counts: 当前会话内各动作的已调用次数（由调用方维护）

        Returns:
            GateOutcome — 包含是否允许执行、是否需要人工确认等信息
        """
        level = request.risk_level()
        call_counts = call_counts or {}

        if level == RiskLevel.A:
            return self._check_level_a(request)
        elif level == RiskLevel.B:
            return self._check_level_b(request)
        elif level == RiskLevel.C:
            return self._check_level_c(request, call_counts)
        else:  # D
            return self._check_level_d(request)

    # ------------------------------------------------------------------
    # A 类：安全认知（自动，无阻塞）
    # ------------------------------------------------------------------

    def _check_level_a(self, request: ActionRequest) -> GateOutcome:
        """A 类：无副作用，直接放行。"""
        logger.debug(
            f"[{self._session_id}] 门禁 A 类通过: {request.action_name}"
        )
        outcome = GateOutcome(
            request_id=request.request_id,
            action_name=request.action_name,
            level=RiskLevel.A,
            allowed=True,
        )
        self._record_audit(request, outcome, notes="A 类自动放行")
        return outcome

    # ------------------------------------------------------------------
    # B 类：外部取证（自动 + 强审计）
    # ------------------------------------------------------------------

    def _check_level_b(self, request: ActionRequest) -> GateOutcome:
        """B 类：自动放行，但必须留痕入审计流。"""
        logger.info(
            f"[{self._session_id}] 门禁 B 类审计: {request.action_name} | "
            f"描述: {request.description[:60]}"
        )
        outcome = GateOutcome(
            request_id=request.request_id,
            action_name=request.action_name,
            level=RiskLevel.B,
            allowed=True,
        )
        audit_record = {
            "type": "B",
            "action": request.action_name,
            "context": request.context,
            "description": request.description,
            "session_id": self._session_id,
            "recorded_at": datetime.now().isoformat(),
        }
        outcome.audit_record = audit_record
        self._record_audit(request, outcome, notes="B 类自动放行，已入审计流")
        return outcome

    # ------------------------------------------------------------------
    # C 类：高成本生成（Budget Guard）
    # ------------------------------------------------------------------

    def _check_level_c(
        self,
        request: ActionRequest,
        call_counts: Dict[str, int],
    ) -> GateOutcome:
        """C 类：检查 Budget Guard 配额，超出则阻断。"""
        limit = self._budget.get(request.action_name, _DEFAULT_C_BUDGET)
        current_count = call_counts.get(request.action_name, 0)

        if current_count >= limit:
            logger.warning(
                f"[{self._session_id}] 门禁 C 类阻断: {request.action_name} | "
                f"已用={current_count}, 上限={limit}"
            )
            outcome = GateOutcome(
                request_id=request.request_id,
                action_name=request.action_name,
                level=RiskLevel.C,
                allowed=False,
                blocked=True,
                block_reason=(
                    f"动作 '{request.action_name}' 已达到配额上限 {limit} 次"
                    f"（当前已用 {current_count} 次）。"
                    f"如需继续，请申请追加配额。"
                ),
            )
            self._record_audit(request, outcome, notes=f"C 类超配额: {current_count}/{limit}")
            return outcome

        logger.info(
            f"[{self._session_id}] 门禁 C 类通过: {request.action_name} | "
            f"已用={current_count + 1}/{limit}"
        )
        outcome = GateOutcome(
            request_id=request.request_id,
            action_name=request.action_name,
            level=RiskLevel.C,
            allowed=True,
        )
        self._record_audit(request, outcome, notes=f"C 类通过: {current_count + 1}/{limit}")
        return outcome

    # ------------------------------------------------------------------
    # D 类：不可逆操作（阻断，需人工确认）
    # ------------------------------------------------------------------

    def _check_level_d(self, request: ActionRequest) -> GateOutcome:
        """
        D 类：强制阻断，标记 needs_confirm=True。

        调用方应在收到此结果后，通过 LangGraph Interrupt 机制暂停流程，
        向用户弹出确认卡片，等待明确的 Confirm 再放行。
        """
        logger.warning(
            f"[{self._session_id}] 门禁 D 类阻断（需人工确认）: {request.action_name} | "
            f"{request.description[:80]}"
        )
        outcome = GateOutcome(
            request_id=request.request_id,
            action_name=request.action_name,
            level=RiskLevel.D,
            allowed=False,
            needs_confirm=True,
            block_reason=(
                f"动作 '{request.action_name}' 属于不可逆或现实操作（D 类），"
                f"必须由您明确确认后才能执行。"
                f"\n操作描述：{request.description}"
            ),
        )
        self._record_audit(request, outcome, notes="D 类阻断，等待人工 Confirm")
        return outcome

    # ------------------------------------------------------------------
    # 审计记录
    # ------------------------------------------------------------------

    def _record_audit(
        self,
        request: ActionRequest,
        outcome: GateOutcome,
        notes: str = "",
    ) -> None:
        """将每次门禁检查结果记录到审计流水。"""
        self._audit_trail.append({
            "request_id": request.request_id,
            "action_name": request.action_name,
            "level": outcome.level.value,
            "allowed": outcome.allowed,
            "blocked": outcome.blocked,
            "needs_confirm": outcome.needs_confirm,
            "block_reason": outcome.block_reason,
            "description": request.description,
            "context": request.context,
            "notes": notes,
            "recorded_at": datetime.now().isoformat(),
        })


# ---------------------------------------------------------------------------
# 便捷工厂
# ---------------------------------------------------------------------------


def create_gate_engine_from_blueprint(
    blueprint_raw: Optional[Dict[str, Any]],
    session_id: str = "unknown",
) -> RiskGateEngine:
    """
    从 ExecutionBlueprint 的 budget_guard 字段创建门禁引擎。

    Args:
        blueprint_raw: ExecutionBlueprint 的 dict 序列化（state 中取出的原始值）
        session_id:    当前会话 ID，用于日志
    """
    budget: Dict[str, int] = {}
    if blueprint_raw:
        budget = blueprint_raw.get("budget_guard") or {}

    return RiskGateEngine(
        budget_override=budget,
        session_id=session_id,
    )
