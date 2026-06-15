"""
execution/skills/reasoning_skills.py 鈥?鎺ㄧ悊鍒嗘瀽鎶€鑳?

Copilot 鐢熸垚锛?026-03-22锛?

鎶€鑳藉垪琛細
  - compare_options       (A 绫婚棬鎺?锛氬姣旇嫢骞叉柟妗堥€夐」鐨勬潈琛″彇鑸?
  - validate_constraints  (A 绫婚棬鎺?锛氭牎楠屽瓧娈垫槸鍚︽弧瓒宠鑼冭鍒?
  - risk_forecast         (A 绫婚棬鎺?锛氶娴嬪綋鍓嶆柟妗堟綔鍦ㄩ闄?
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


class CompareResult:
    def __init__(self, options: List[str], analysis: Dict[str, Any]) -> None:
        self.options = options
        self.analysis = analysis  # {"preferred": ..., "trade_offs": {...}}

    def to_dict(self) -> Dict[str, Any]:
        return {"options": self.options, "analysis": self.analysis}


class ValidationResult:
    def __init__(
        self,
        fields: Dict[str, Any],
        violations: List[str],
        passed: bool,
    ) -> None:
        self.fields = fields
        self.violations = violations
        self.passed = passed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fields": self.fields,
            "violations": self.violations,
            "passed": self.passed,
        }


class RiskForecastResult:
    def __init__(self, risks: List[Dict[str, str]], overall_level: str) -> None:
        self.risks = risks            # [{"area": ..., "description": ..., "severity": ...}]
        self.overall_level = overall_level   # "low" | "medium" | "high"

    def to_dict(self) -> Dict[str, Any]:
        return {"risks": self.risks, "overall_level": self.overall_level}


# ---------------------------------------------------------------------------
# 鎺ㄧ悊鎶€鑳?
# ---------------------------------------------------------------------------


def compare_options(
    options: List[str],
    criteria: List[str],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> CompareResult:
    """
    A 绫婚棬鎺?鈥?瀵规瘮鑻ュ共鏂规閫夐」锛岃繑鍥炴潈琛″垎鏋愩€?

    鍙傛暟:
      options  鈥?閫夐」鍚嶇О鍒楄〃锛堝 ["鏋佺畝椋?, "鐜颁唬宸ヤ笟椋?]锛?
      criteria 鈥?璇勪及缁村害锛堝 ["鎴愭湰", "宸ユ湡", "浣撻獙"]锛?
    """
    request = ActionRequest(
        action_name="reasoning_evaluate",
        context={"session_id": session_id},
        description=f"鏂规瀵规瘮: {options}",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        logger.warning(f"[{session_id}] compare_options gate blocked")
        return CompareResult(options=options, analysis={"blocked": True})

    logger.info(f"[{session_id}] compare_options: {options}, criteria={criteria}")
    # 鎺ㄧ悊鍒嗘瀽鐢?LLM 灞傚湪鏇撮珮灞傝皟鐢紱姝ゅ杩斿洖鍗犱綅缁撴瀯渚?orchestrator 缁勮
    analysis: Dict[str, Any] = {
        "preferred": options[0] if options else "",
        "trade_offs": {opt: {} for opt in options},
        "criteria_used": criteria,
    }
    return CompareResult(options=options, analysis=analysis)


def validate_constraints(
    fields: Dict[str, Any],
    rules_db: Dict[str, Any],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> ValidationResult:
    """
    A 绫婚棬鎺?鈥?鏍￠獙瀛楁闆嗗悎鏄惁婊¤冻瑙勮寖瑙勫垯搴撱€?

    鍙傛暟:
      fields   鈥?寰呮牎楠屽瓧娈碉紙濡?{"floor_area_ratio": 2.8, "height": 25}锛?
      rules_db 鈥?瑙勮寖绾︽潫锛堝 {"max_floor_area_ratio": 2.5, "max_height": 24}锛?
    """
    request = ActionRequest(
        action_name="validate_constraints",
        context={"session_id": session_id},
        description="绾︽潫鏍￠獙",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        logger.warning(f"[{session_id}] validate_constraints gate blocked")
        return ValidationResult(fields=fields, violations=["gate_blocked"], passed=False)

    violations: List[str] = []
    for field, value in fields.items():
        rule_key = f"max_{field}"
        if rule_key in rules_db and isinstance(value, (int, float)):
            if value > rules_db[rule_key]:
                violations.append(
                    f"{field}={value} 瓒呰繃闄愬埗 {rules_db[rule_key]}"
                )

    passed = len(violations) == 0
    logger.info(
        f"[{session_id}] validate_constraints: passed={passed}, violations={violations}"
    )
    return ValidationResult(fields=fields, violations=violations, passed=passed)


def risk_forecast(
    taskbook_raw: Dict[str, Any],
    blueprint_raw: Dict[str, Any],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> RiskForecastResult:
    """
    A 绫婚棬鎺?鈥?鍩轰簬璁捐浠诲姟涔﹀拰鎵ц钃濆浘棰勬祴娼滃湪椋庨櫓銆?
    """
    request = ActionRequest(
        action_name="reasoning_evaluate",
        context={"session_id": session_id, "task": "risk_forecast"},
        description="椋庨櫓棰勬祴",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        return RiskForecastResult(risks=[], overall_level="unknown")

    # 鍩轰簬绾㈢嚎鍜屽喕缁撳尯鍩熻瘎浼颁竴绾ч闄?
    risks: List[Dict[str, str]] = []
    redlines: List[str] = taskbook_raw.get("boundaries_and_redlines", [])
    frozen: List[str] = (
        taskbook_raw.get("strategy_zones", {}).get("frozen", [])
    )

    for rl in redlines[:3]:  # 鏈€澶氭彁鍙栧墠 3 鏉?
        risks.append({
            "area": "绾㈢嚎绾︽潫",
            "description": rl[:80],
            "severity": "high",
        })

    budget_guard: Dict[str, int] = blueprint_raw.get("budget_guard", {})
    for skill, limit in budget_guard.items():
        if limit < 3:
            risks.append({
                "area": "棰勭畻椋庨櫓",
                "description": f"{skill} budget guard is too low ({limit})",
                "severity": "medium",
            })

    overall = "high" if any(r["severity"] == "high" for r in risks) else (
        "medium" if risks else "low"
    )

    logger.info(f"[{session_id}] risk_forecast: {len(risks)} risks, overall={overall}")
    return RiskForecastResult(risks=risks, overall_level=overall)
