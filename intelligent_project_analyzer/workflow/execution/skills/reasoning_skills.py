"""
execution/skills/reasoning_skills.py — 推理分析技能

Copilot 生成（2026-03-22）

技能列表：
  - compare_options       (A 类门控)：对比若干方案选项的权衡取舍
  - validate_constraints  (A 类门控)：校验字段是否满足规范规则
  - risk_forecast         (A 类门控)：预测当前方案潜在风险
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
# 推理技能
# ---------------------------------------------------------------------------


def compare_options(
    options: List[str],
    criteria: List[str],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> CompareResult:
    """
    A 类门控 — 对比若干方案选项，返回权衡分析。

    参数:
      options  — 选项名称列表（如 ["极简风", "现代工业风"]）
      criteria — 评估维度（如 ["成本", "工期", "体验"]）
    """
    request = ActionRequest(
        action_name="reasoning_evaluate",
        context={"session_id": session_id},
        description=f"方案对比: {options}",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        logger.warning(f"[{session_id}] compare_options 被门控阻断")
        return CompareResult(options=options, analysis={"blocked": True})

    logger.info(f"[{session_id}] compare_options: {options}, criteria={criteria}")
    # 推理分析由 LLM 层在更高层调用；此处返回占位结构供 orchestrator 组装
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
    A 类门控 — 校验字段集合是否满足规范规则库。

    参数:
      fields   — 待校验字段（如 {"floor_area_ratio": 2.8, "height": 25}）
      rules_db — 规范约束（如 {"max_floor_area_ratio": 2.5, "max_height": 24}）
    """
    request = ActionRequest(
        action_name="validate_constraints",
        context={"session_id": session_id},
        description="约束校验",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        logger.warning(f"[{session_id}] validate_constraints 被门控阻断")
        return ValidationResult(fields=fields, violations=["gate_blocked"], passed=False)

    violations: List[str] = []
    for field, value in fields.items():
        rule_key = f"max_{field}"
        if rule_key in rules_db and isinstance(value, (int, float)):
            if value > rules_db[rule_key]:
                violations.append(
                    f"{field}={value} 超过限制 {rules_db[rule_key]}"
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
    A 类门控 — 基于设计任务书和执行蓝图预测潜在风险。
    """
    request = ActionRequest(
        action_name="reasoning_evaluate",
        context={"session_id": session_id, "task": "risk_forecast"},
        description="风险预测",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        return RiskForecastResult(risks=[], overall_level="unknown")

    # 基于红线和冻结区域评估一级风险
    risks: List[Dict[str, str]] = []
    redlines: List[str] = taskbook_raw.get("boundaries_and_redlines", [])
    frozen: List[str] = (
        taskbook_raw.get("strategy_zones", {}).get("frozen", [])
    )

    for rl in redlines[:3]:  # 最多提取前 3 条
        risks.append({
            "area": "红线约束",
            "description": rl[:80],
            "severity": "high",
        })

    budget_guard: Dict[str, int] = blueprint_raw.get("budget_guard", {})
    for skill, limit in budget_guard.items():
        if limit < 3:
            risks.append({
                "area": "预算风险",
                "description": f"{skill} 配额过低（{limit}）",
                "severity": "medium",
            })

    overall = "high" if any(r["severity"] == "high" for r in risks) else (
        "medium" if risks else "low"
    )

    logger.info(f"[{session_id}] risk_forecast: {len(risks)} risks, overall={overall}")
    return RiskForecastResult(risks=risks, overall_level=overall)
