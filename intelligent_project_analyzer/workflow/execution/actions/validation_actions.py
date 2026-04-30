"""
execution/actions/validation_actions.py — 校验类原子动作

Copilot 生成（2026-03-22）

原子动作：
  - validate_fields_against_rules  ：字段约束批量校验
  - check_redline_in_text          ：文本红线检测
"""

from __future__ import annotations

from typing import Any, Dict, List


# 系统级红线标记词（与 delta_router 保持一致）
_REDLINE_MARKERS = (
    "容积率", "退红线", "消防", "日照", "限高",
    "结构体系", "地基", "选址重选",
)


def validate_fields_against_rules(
    fields: Dict[str, Any],
    rules: Dict[str, Any],
) -> Dict[str, Any]:
    """
    字段约束批量校验。

    参数:
      fields — 待校验字段字典（如 {"floor_area_ratio": 3.0, "height_m": 30}）
      rules  — 约束规则字典（如 {"max_floor_area_ratio": 2.5, "max_height_m": 24}）

    返回:
      {
        "passed": bool,
        "violations": [{"field": ..., "value": ..., "max": ..., "message": ...}],
      }
    """
    violations: List[Dict[str, Any]] = []
    for field, value in fields.items():
        max_key = f"max_{field}"
        min_key = f"min_{field}"
        if max_key in rules and isinstance(value, (int, float)):
            if value > rules[max_key]:
                violations.append({
                    "field": field,
                    "value": value,
                    "max": rules[max_key],
                    "message": f"{field}={value} 超过上限 {rules[max_key]}",
                })
        if min_key in rules and isinstance(value, (int, float)):
            if value < rules[min_key]:
                violations.append({
                    "field": field,
                    "value": value,
                    "min": rules[min_key],
                    "message": f"{field}={value} 低于下限 {rules[min_key]}",
                })
    return {
        "passed": len(violations) == 0,
        "violations": violations,
    }


def check_redline_in_text(
    text: str,
    project_redlines: List[str],
) -> Dict[str, Any]:
    """
    文本红线检测。

    参数:
      text              — 待检测文本（用户指令或交付物内容摘要）
      project_redlines  — 项目级红线约束列表（来自 DesignTaskBook）

    返回:
      {
        "alerts": [...],
        "has_redline": bool,
      }
    """
    alerts: List[str] = []

    # 系统级红线词检测
    for marker in _REDLINE_MARKERS:
        if marker in text:
            alerts.append(f"系统级红线: {marker}")

    # 项目级红线检测（关键词匹配）
    for redline in project_redlines:
        tokens = [w for w in redline.split() if len(w) >= 2]
        for token in tokens:
            if token in text:
                alerts.append(f"项目红线: {redline[:60]}")
                break

    return {
        "alerts": alerts,
        "has_redline": len(alerts) > 0,
    }
