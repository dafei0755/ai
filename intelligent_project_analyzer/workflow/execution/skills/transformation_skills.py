"""
execution/skills/transformation_skills.py — 转换变换技能

Copilot 生成（2026-03-22）

技能列表：
  - rewrite_outline    (A 类门控)：重写方案大纲/文案框架
  - map_version_params (A 类门控)：版本参数映射（v1 → v1.1 参数继承）
  - parse_format       (A 类门控)：解析外部格式（PDF 规范、CAD 属性表）
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


class RewriteResult:
    def __init__(self, original: str, rewritten: str, rationale: str = "") -> None:
        self.original = original
        self.rewritten = rewritten
        self.rationale = rationale

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original": self.original,
            "rewritten": self.rewritten,
            "rationale": self.rationale,
        }


class VersionMapResult:
    def __init__(
        self,
        from_version: str,
        to_version: str,
        inherited_params: Dict[str, Any],
        overridden_params: Dict[str, Any],
    ) -> None:
        self.from_version = from_version
        self.to_version = to_version
        self.inherited_params = inherited_params
        self.overridden_params = overridden_params

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "inherited_params": self.inherited_params,
            "overridden_params": self.overridden_params,
        }


class ParseFormatResult:
    def __init__(
        self,
        source_format: str,
        extracted_fields: Dict[str, Any],
        parse_errors: List[str],
    ) -> None:
        self.source_format = source_format
        self.extracted_fields = extracted_fields
        self.parse_errors = parse_errors

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_format": self.source_format,
            "extracted_fields": self.extracted_fields,
            "parse_errors": self.parse_errors,
        }


# ---------------------------------------------------------------------------
# 转换技能
# ---------------------------------------------------------------------------


def rewrite_outline(
    original_text: str,
    rewrite_instruction: str,
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> RewriteResult:
    """
    A 类门控 — 按指令重写方案大纲或文案框架。

    参数:
      original_text       — 待改写的原始文本
      rewrite_instruction — 改写指令（如 "更简洁，突出成本优先"）
    """
    request = ActionRequest(
        action_name="draft_compile",
        context={"session_id": session_id, "task": "rewrite"},
        description=f"重写大纲: {rewrite_instruction[:80]}",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        return RewriteResult(
            original=original_text,
            rewritten=original_text,
            rationale="gate_blocked",
        )

    logger.info(f"[{session_id}] rewrite_outline: instruction='{rewrite_instruction[:60]}'")
    # 实际改写由 LLM 层完成；此处返回占位结构
    return RewriteResult(
        original=original_text,
        rewritten=original_text,  # placeholder — LLM 填充
        rationale=rewrite_instruction,
    )


def map_version_params(
    from_version: str,
    to_version: str,
    base_params: Dict[str, Any],
    delta_overrides: Dict[str, Any],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> VersionMapResult:
    """
    A 类门控 — 版本参数继承映射。

    将 from_version 的基础参数与 delta_overrides 合并，生成 to_version 的参数集。
    """
    request = ActionRequest(
        action_name="reasoning_evaluate",
        context={"session_id": session_id, "task": "version_map"},
        description=f"版本参数映射 {from_version} → {to_version}",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        return VersionMapResult(
            from_version=from_version,
            to_version=to_version,
            inherited_params=base_params,
            overridden_params={},
        )

    # 合并：base_params 覆盖写入 delta_overrides
    inherited = {k: v for k, v in base_params.items() if k not in delta_overrides}
    logger.info(
        f"[{session_id}] map_version_params: {from_version}→{to_version}, "
        f"overrides={list(delta_overrides.keys())}"
    )
    return VersionMapResult(
        from_version=from_version,
        to_version=to_version,
        inherited_params=inherited,
        overridden_params=delta_overrides,
    )


def parse_format(
    raw_content: str,
    source_format: str,
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> ParseFormatResult:
    """
    A 类门控 — 解析外部格式（PDF 规范、CAD 属性表、JSON 摘要等）提取结构化字段。
    """
    request = ActionRequest(
        action_name="draft_compile",
        context={"session_id": session_id, "task": "parse"},
        description=f"格式解析: source_format={source_format}",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        return ParseFormatResult(
            source_format=source_format,
            extracted_fields={},
            parse_errors=["gate_blocked"],
        )

    logger.info(f"[{session_id}] parse_format: format={source_format}, len={len(raw_content)}")
    # 实际解析逻辑由 actions 层完成
    return ParseFormatResult(
        source_format=source_format,
        extracted_fields={},
        parse_errors=[],
    )
