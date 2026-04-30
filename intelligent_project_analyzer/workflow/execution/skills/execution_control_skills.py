"""
execution/skills/execution_control_skills.py — 执行控制技能

Copilot 生成（2026-03-22）

技能列表：
  - schedule_batch         (C 类门控)：批量调度多个生成任务
  - route_delta            (A 类门控)：在执行阶段内触发增量路由
  - assemble_incremental   (C 类门控)：将增量结果与基线版本拼装成新产物
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.workflow.execution.risk_gates import (
    ActionRequest,
    RiskGateEngine,
)


# ---------------------------------------------------------------------------
# 结果结构
# ---------------------------------------------------------------------------


class BatchScheduleResult:
    def __init__(
        self,
        task_ids: List[str],
        scheduled: int,
        blocked: int,
        results: List[Dict[str, Any]],
    ) -> None:
        self.task_ids = task_ids
        self.scheduled = scheduled
        self.blocked = blocked
        self.results = results
        self.scheduled_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_ids": self.task_ids,
            "scheduled": self.scheduled,
            "blocked": self.blocked,
            "results": self.results,
            "scheduled_at": self.scheduled_at,
        }


class DeltaRouteResult:
    def __init__(
        self,
        route_decision: str,       # "delta" | "derived" | "conversation"
        impact_summary: Dict[str, Any],
    ) -> None:
        self.route_decision = route_decision
        self.impact_summary = impact_summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route_decision": self.route_decision,
            "impact_summary": self.impact_summary,
        }


class IncrementalAssemblyResult:
    def __init__(
        self,
        base_version: str,
        new_version: str,
        merged_fields: List[str],
        assembly_ok: bool,
    ) -> None:
        self.base_version = base_version
        self.new_version = new_version
        self.merged_fields = merged_fields
        self.assembly_ok = assembly_ok

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_version": self.base_version,
            "new_version": self.new_version,
            "merged_fields": self.merged_fields,
            "assembly_ok": self.assembly_ok,
        }


# ---------------------------------------------------------------------------
# 执行控制技能
# ---------------------------------------------------------------------------


def schedule_batch(
    tasks: List[Dict[str, Any]],
    task_executor: Callable[[Dict[str, Any]], Dict[str, Any]],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> BatchScheduleResult:
    """
    C 类门控 — 批量调度生成任务。

    参数:
      tasks         — 任务描述列表，每条含 {"task_id", "action_name", "params"}
      task_executor — 同步执行单个任务的回调（可替换为异步实现）
    """
    request = ActionRequest(
        action_name="regenerate_delta",
        context={"session_id": session_id, "task": "batch_schedule"},
        description=f"批量调度 {len(tasks)} 个任务",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        reason = outcome.block_reason or "C 类超配额"
        logger.warning(f"[{session_id}] schedule_batch 被门控阻断: {reason}")
        return BatchScheduleResult(
            task_ids=[t.get("task_id", "") for t in tasks],
            scheduled=0,
            blocked=len(tasks),
            results=[],
        )

    task_ids = [t.get("task_id", f"task_{i}") for i, t in enumerate(tasks)]
    results: List[Dict[str, Any]] = []
    blocked_count = 0

    for task in tasks:
        try:
            result = task_executor(task)
            results.append({"task_id": task.get("task_id"), "status": "ok", "result": result})
        except Exception as exc:
            results.append({"task_id": task.get("task_id"), "status": "error", "error": str(exc)})
            blocked_count += 1

    logger.info(
        f"[{session_id}] schedule_batch: total={len(tasks)}, "
        f"ok={len(tasks) - blocked_count}, failed={blocked_count}"
    )
    return BatchScheduleResult(
        task_ids=task_ids,
        scheduled=len(tasks) - blocked_count,
        blocked=blocked_count,
        results=results,
    )


def route_delta(
    user_input: str,
    taskbook_raw: Dict[str, Any],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> DeltaRouteResult:
    """
    A 类门控 — 执行阶段内的增量路由判断（不经过 LangGraph，仅返回决策信号）。

    由 ExecutionOrchestrator 在发现需要增量修改时调用；
    更复杂的路由仍由 DeltaRouter 节点处理。
    """
    request = ActionRequest(
        action_name="reasoning_evaluate",
        context={"session_id": session_id, "task": "route_delta"},
        description=f"执行层路由判断: {user_input[:60]}",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        return DeltaRouteResult(route_decision="conversation", impact_summary={})

    # 轻量路由逻辑（不经过 DeltaRouter 节点）
    from intelligent_project_analyzer.workflow.nodes.delta_router import DeltaRouter
    router = DeltaRouter()
    impact = router._compute_impact(user_input, taskbook_raw)

    if impact.requires_derived_project:
        decision = "derived"
    elif router._is_clear_delta(user_input, impact):
        decision = "delta"
    else:
        decision = "conversation"

    logger.info(f"[{session_id}] route_delta: decision={decision}")
    return DeltaRouteResult(
        route_decision=decision,
        impact_summary=impact.model_dump(),
    )


def assemble_incremental(
    base_bundle_raw: Dict[str, Any],
    delta_result: Dict[str, Any],
    modified_fields: List[str],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> IncrementalAssemblyResult:
    """
    C 类门控 — 将增量结果与基线版本拼装成新的 DeliveryBundle。

    参数:
      base_bundle_raw — 基线 DeliveryBundle.model_dump()
      delta_result    — 增量执行结果字典
      modified_fields — 本次修改的字段列表
    """
    request = ActionRequest(
        action_name="regenerate_delta",
        context={"session_id": session_id, "task": "assemble_incremental"},
        description=f"增量拼装: modified={modified_fields}",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        return IncrementalAssemblyResult(
            base_version="unknown",
            new_version="unknown",
            merged_fields=[],
            assembly_ok=False,
        )

    version_lineage: List[str] = base_bundle_raw.get("version_lineage", [])
    base_version = version_lineage[-1] if version_lineage else "v1"
    new_version = f"{base_version}.delta"

    # 将 delta_result 合并到 base_bundle 的 stage_deliverables
    merged_bundle = dict(base_bundle_raw)
    stage = list(merged_bundle.get("stage_deliverables", []))
    stage.append({
        "version": new_version,
        "delta": delta_result,
        "modified_fields": modified_fields,
    })
    merged_bundle["stage_deliverables"] = stage
    merged_bundle["version_lineage"] = version_lineage + [new_version]

    logger.info(
        f"[{session_id}] assemble_incremental: {base_version} → {new_version}, "
        f"fields={modified_fields}"
    )
    return IncrementalAssemblyResult(
        base_version=base_version,
        new_version=new_version,
        merged_fields=modified_fields,
        assembly_ok=True,
    )
