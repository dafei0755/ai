"""
execution/skills/review_skills.py 鈥?瀹℃煡鏍告煡鎶€鑳?

Copilot 鐢熸垚锛?026-03-22锛?

鎶€鑳藉垪琛細
  - quality_preflight   (A 绫婚棬鎺?锛氫氦浠樺墠璐ㄩ噺棰勬
  - consistency_check   (A 绫婚棬鎺?锛氬鐗堟湰銆佸鑺傜偣浜х墿涓€鑷存€ф牎楠?
  - redline_detection   (A 绫婚棬鎺?锛氳瘑鍒綋鍓嶄骇鐗╂槸鍚﹁Е纰扮孩绾?
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.workflow.execution.risk_gates import (
    ActionRequest,
    RiskGateEngine,
)


# ---------------------------------------------------------------------------
# 缁撴灉缁撴瀯
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
        self.score = score     # 0.0鈥?.0 缁煎悎璇勫垎

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
# 瀹℃煡鎶€鑳?
# ---------------------------------------------------------------------------

# 浜や粯鐗╁繀闇€瀛楁
_REQUIRED_DELIVERABLE_KEYS = ("id", "type", "content")

# 绾㈢嚎鍏稿瀷鏍囪璇嶏紙涓?delta_router 鍏变韩璇箟锛?
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
    A 绫婚棬鎺?鈥?浜や粯鍓嶈川閲忛妫€銆?

    妫€鏌ユ瘡涓氦浠樼墿鐨勫繀闇€瀛楁鏄惁瀹屾暣锛屽唴瀹规槸鍚﹂潪绌恒€?
    """
    request = ActionRequest(
        action_name="validate_constraints",
        context={"session_id": session_id, "task": "preflight"},
        description=f"璐ㄩ噺棰勬: {len(deliverables)} 椤逛氦浠樼墿",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        return PreflightResult(passed=False, issues=[{"level": "error", "message": "gate_blocked"}])

    issues: List[Dict[str, str]] = []
    for idx, item in enumerate(deliverables):
        for key in _REQUIRED_DELIVERABLE_KEYS:
            if key not in item or not item[key]:
                issues.append({
                    "level": "error",
                    "message": f"浜や粯鐗{idx}] 缂哄皯蹇呴渶瀛楁: {key}",
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
    A 绫婚棬鎺?鈥?姣旇緝涓や釜 DeliveryBundle 蹇収鐨勬寚瀹氬瓧娈垫槸鍚︿竴鑷淬€?

    鍙傛暟:
      bundle_a, bundle_b 鈥?涓や釜 DeliveryBundle.model_dump() 缁撴灉
      key_fields         鈥?闇€瑕佹瘮杈冪殑椤跺眰瀛楁鍚嶅垪琛?
    """
    request = ActionRequest(
        action_name="baseline_compare",
        context={"session_id": session_id},
        description=f"涓€鑷存€ф牎楠? fields={key_fields}",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

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
                "detail": f"{field} is inconsistent between versions",
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
    A 绫婚棬鎺?鈥?妫€娴嬫枃鏈唴瀹规槸鍚﹁Е纰伴」鐩孩绾挎垨绯荤粺绾х孩绾挎爣璁拌瘝銆?

    鍙傛暟:
      content                 鈥?寰呮娴嬬殑鏂囧瓧鍐呭锛堢敤鎴疯緭鍏ユ垨浜や粯鐗╂憳瑕侊級
      boundaries_and_redlines 鈥?鏉ヨ嚜 DesignTaskBook 鐨勯」鐩骇绾㈢嚎绾︽潫
    """
    request = ActionRequest(
        action_name="validate_constraints",
        context={"session_id": session_id, "task": "redline_detection"},
        description="redline detection",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        return RedlineDetectionResult(alerts=["gate_blocked"], requires_derived_project=False)

    alerts: List[str] = []

    # 绯荤粺绾х孩绾?
    for marker in _REDLINE_MARKERS:
        if marker in content:
            alerts.append(f"瑙︾绯荤粺绾х孩绾挎爣璁? {marker}")

    # 椤圭洰绾х孩绾?
    for redline in boundaries_and_redlines:
        keywords = [w for w in redline.split() if len(w) >= 2]
        for kw in keywords:
            if kw in content:
                alerts.append(f"瑙︾椤圭洰绾㈢嚎: {redline[:60]}")
                break

    requires_derived = len(alerts) > 0
    logger.info(
        f"[{session_id}] redline_detection: alerts={len(alerts)}, "
        f"requires_derived={requires_derived}"
    )
    return RedlineDetectionResult(alerts=alerts, requires_derived_project=requires_derived)
