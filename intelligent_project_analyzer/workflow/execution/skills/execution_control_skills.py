"""
execution/skills/execution_control_skills.py 鈥?鎵ц鎺у埗鎶€鑳?

Copilot 鐢熸垚锛?026-03-22锛?

鎶€鑳藉垪琛細
  - schedule_batch         (C 绫婚棬鎺?锛氭壒閲忚皟搴﹀涓敓鎴愪换鍔?
  - route_delta            (A 绫婚棬鎺?锛氬湪鎵ц闃舵鍐呰Е鍙戝閲忚矾鐢?
  - assemble_incremental   (C 绫婚棬鎺?锛氬皢澧為噺缁撴灉涓庡熀绾跨増鏈嫾瑁呮垚鏂颁骇鐗?
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
# 缁撴灉缁撴瀯
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
# 鎵ц鎺у埗鎶€鑳?
# ---------------------------------------------------------------------------


def schedule_batch(
    tasks: List[Dict[str, Any]],
    task_executor: Callable[[Dict[str, Any]], Dict[str, Any]],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> BatchScheduleResult:
    """
    C 绫婚棬鎺?鈥?鎵归噺璋冨害鐢熸垚浠诲姟銆?

    鍙傛暟:
      tasks         鈥?浠诲姟鎻忚堪鍒楄〃锛屾瘡鏉″惈 {"task_id", "action_name", "params"}
      task_executor 鈥?鍚屾鎵ц鍗曚釜浠诲姟鐨勫洖璋冿紙鍙浛鎹负寮傛瀹炵幇锛?
    """
    request = ActionRequest(
        action_name="regenerate_delta",
        context={"session_id": session_id, "task": "batch_schedule"},
        description=f"batch schedule {len(tasks)} tasks",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        reason = outcome.block_reason or "C 绫昏秴閰嶉"
        logger.warning(f"[{session_id}] schedule_batch 琚棬鎺ч樆鏂? {reason}")
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
    A 绫婚棬鎺?鈥?鎵ц闃舵鍐呯殑澧為噺璺敱鍒ゆ柇锛堜笉缁忚繃 LangGraph锛屼粎杩斿洖鍐崇瓥淇″彿锛夈€?

    鐢?ExecutionOrchestrator 鍦ㄥ彂鐜伴渶瑕佸閲忎慨鏀规椂璋冪敤锛?
    鏇村鏉傜殑璺敱浠嶇敱 DeltaRouter 鑺傜偣澶勭悊銆?
    """
    request = ActionRequest(
        action_name="reasoning_evaluate",
        context={"session_id": session_id, "task": "route_delta"},
        description=f"鎵ц灞傝矾鐢卞垽鏂? {user_input[:60]}",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        return DeltaRouteResult(route_decision="conversation", impact_summary={})

    # 杞婚噺璺敱閫昏緫锛堜笉缁忚繃 DeltaRouter 鑺傜偣锛?
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
    C 绫婚棬鎺?鈥?灏嗗閲忕粨鏋滀笌鍩虹嚎鐗堟湰鎷艰鎴愭柊鐨?DeliveryBundle銆?

    鍙傛暟:
      base_bundle_raw 鈥?鍩虹嚎 DeliveryBundle.model_dump()
      delta_result    鈥?澧為噺鎵ц缁撴灉瀛楀吀
      modified_fields 鈥?鏈淇敼鐨勫瓧娈靛垪琛?
    """
    request = ActionRequest(
        action_name="regenerate_delta",
        context={"session_id": session_id, "task": "assemble_incremental"},
        description=f"澧為噺鎷艰: modified={modified_fields}",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

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

    # 灏?delta_result 鍚堝苟鍒?base_bundle 鐨?stage_deliverables
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
        f"[{session_id}] assemble_incremental: {base_version} 鈫?{new_version}, "
        f"fields={modified_fields}"
    )
    return IncrementalAssemblyResult(
        base_version=base_version,
        new_version=new_version,
        merged_fields=modified_fields,
        assembly_ok=True,
    )
