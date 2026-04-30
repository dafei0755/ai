"""
execution/skills/review_skills.py — 审查核查技能

Copilot 生成（2026-03-22）

技能列表：
  - quality_preflight   (A 类门控)：交付前质量预检
  - consistency_check   (A 类门控)：多版本、多节点产物一致性校验
  - redline_detection   (A 类门控)：识别当前产物是否触碰红线
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.workflow.execution.risk_gates import (
    ActionRequest,
    RiskGateEngine,
)


# ---------------------------------------------------------------------------
# 结果结构
# ---------------------------------------------------------------------------


class PreflightResult:
    def __init__(
        self,
        passed: bool,
        issues: List[Dict[str, str]],
        score: float = 1.0,
    ) -> None:
        self.passed = passed
        self.issues = issues   # [{"level": "error"|"warn", "message": ...}]
        self.score = score     # 0.0–1.0 综合评分

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "issues": self.issues,
            "score": self.score,
        }


class ConsistencyResult:
    def __init__(
        self,
        consistent: bool,
        conflicts: List[Dict[str, str]],
    ) -> None:
        self.consistent = consistent
        self.conflicts = conflicts   # [{"field": ..., "versions": [...], "detail": ...}]

    def to_dict(self) -> Dict[str, Any]:
        return {"consistent": self.consistent, "conflicts": self.conflicts}


class RedlineDetectionResult:
    def __init__(
        self,
        alerts: List[str],
        requires_derived_project: bool,
    ) -> None:
        self.alerts = alerts
        self.requires_derived_project = requires_derived_project

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alerts": self.alerts,
            "requires_derived_project": self.requires_derived_project,
        }


# ---------------------------------------------------------------------------
# 审查技能
# ---------------------------------------------------------------------------

# 交付物必需字段
_REQUIRED_DELIVERABLE_KEYS = ("id", "type", "content")

# 红线典型标记词（与 delta_router 共享语义）
_REDLINE_MARKERS = (
    "容积率", "退红线", "消防", "日照", "限高",
    "结构体系", "地基", "选址重选",
)


def quality_preflight(
    deliverables: List[Dict[str, Any]],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> PreflightResult:
    """
    A 类门控 — 交付前质量预检。

    检查每个交付物的必需字段是否完整，内容是否非空。
    """
    request = ActionRequest(
        action_name="validate_constraints",
        context={"session_id": session_id, "task": "preflight"},
        description=f"质量预检: {len(deliverables)} 项交付物",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        return PreflightResult(passed=False, issues=[{"level": "error", "message": "gate_blocked"}])

    issues: List[Dict[str, str]] = []
    for idx, item in enumerate(deliverables):
        for key in _REQUIRED_DELIVERABLE_KEYS:
            if key not in item or not item[key]:
                issues.append({
                    "level": "error",
                    "message": f"交付物[{idx}] 缺少必需字段: {key}",
                })

    passed = all(i["level"] != "error" for i in issues)
    score = max(0.0, 1.0 - len(issues) * 0.1)
    logger.info(
        f"[{session_id}] quality_preflight: passed={passed}, "
        f"issues={len(issues)}, score={score:.2f}"
    )
    return PreflightResult(passed=passed, issues=issues, score=score)


def consistency_check(
    bundle_a: Dict[str, Any],
    bundle_b: Dict[str, Any],
    key_fields: List[str],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> ConsistencyResult:
    """
    A 类门控 — 比较两个 DeliveryBundle 快照的指定字段是否一致。

    参数:
      bundle_a, bundle_b — 两个 DeliveryBundle.model_dump() 结果
      key_fields         — 需要比较的顶层字段名列表
    """
    request = ActionRequest(
        action_name="baseline_compare",
        context={"session_id": session_id},
        description=f"一致性校验: fields={key_fields}",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        return ConsistencyResult(consistent=False, conflicts=[{"field": "gate_blocked", "versions": [], "detail": ""}])

    conflicts: List[Dict[str, str]] = []
    for field in key_fields:
        val_a = bundle_a.get(field)
        val_b = bundle_b.get(field)
        if val_a != val_b:
            conflicts.append({
                "field": field,
                "versions": [str(val_a)[:80], str(val_b)[:80]],
                "detail": f"{field} 在两个版本间不一致",
            })

    consistent = len(conflicts) == 0
    logger.info(
        f"[{session_id}] consistency_check: consistent={consistent}, "
        f"conflicts={len(conflicts)}"
    )
    return ConsistencyResult(consistent=consistent, conflicts=conflicts)


def redline_detection(
    content: str,
    boundaries_and_redlines: List[str],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> RedlineDetectionResult:
    """
    A 类门控 — 检测文本内容是否触碰项目红线或系统级红线标记词。

    参数:
      content                 — 待检测的文字内容（用户输入或交付物摘要）
      boundaries_and_redlines — 来自 DesignTaskBook 的项目级红线约束
    """
    request = ActionRequest(
        action_name="validate_constraints",
        context={"session_id": session_id, "task": "redline_detection"},
        description="红线检测",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        return RedlineDetectionResult(alerts=["gate_blocked"], requires_derived_project=False)

    alerts: List[str] = []

    # 系统级红线
    for marker in _REDLINE_MARKERS:
        if marker in content:
            alerts.append(f"触碰系统级红线标记: {marker}")

    # 项目级红线
    for redline in boundaries_and_redlines:
        keywords = [w for w in redline.split() if len(w) >= 2]
        for kw in keywords:
            if kw in content:
                alerts.append(f"触碰项目红线: {redline[:60]}")
                break

    requires_derived = len(alerts) > 0
    logger.info(
        f"[{session_id}] redline_detection: alerts={len(alerts)}, "
        f"requires_derived={requires_derived}"
    )
    return RedlineDetectionResult(alerts=alerts, requires_derived_project=requires_derived)
