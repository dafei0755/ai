"""
execution/skills/generation_skills.py — 生成类技能

Copilot 生成（2026-03-22）

技能列表：
  - generate_image         (C 类门控)：生成效果图 / 平面图
  - assemble_text_package  (C 类门控)：组装文字交付物包
  - build_chart            (C 类门控)：生成数据图表
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.workflow.execution.risk_gates import (
    ActionRequest,
    RiskGateEngine,
)


# ---------------------------------------------------------------------------
# 结果结构
# ---------------------------------------------------------------------------


class ImageResult:
    def __init__(
        self,
        prompt: str,
        image_urls: List[str],
        blocked: bool = False,
        block_reason: str = "",
    ) -> None:
        self.prompt = prompt
        self.image_urls = image_urls
        self.blocked = blocked
        self.block_reason = block_reason
        self.generated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "image_urls": self.image_urls,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "generated_at": self.generated_at,
        }


class TextPackageResult:
    def __init__(
        self,
        template_id: str,
        sections: List[Dict[str, str]],
        blocked: bool = False,
    ) -> None:
        self.template_id = template_id
        self.sections = sections
        self.blocked = blocked
        self.assembled_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "sections": self.sections,
            "blocked": self.blocked,
            "assembled_at": self.assembled_at,
        }


class ChartResult:
    def __init__(
        self,
        chart_type: str,
        data: Dict[str, Any],
        chart_url: str = "",
        blocked: bool = False,
    ) -> None:
        self.chart_type = chart_type
        self.data = data
        self.chart_url = chart_url
        self.blocked = blocked

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chart_type": self.chart_type,
            "data": self.data,
            "chart_url": self.chart_url,
            "blocked": self.blocked,
        }


# ---------------------------------------------------------------------------
# 生成技能
# ---------------------------------------------------------------------------


def generate_image(
    prompt: str,
    params: Dict[str, Any],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> ImageResult:
    """
    C 类门控 — 生成效果图 / 平面图。

    params: {"style": "写实", "resolution": "1024x768", "count": 2}
    """
    request = ActionRequest(
        action_name="generate_image",
        context={"session_id": session_id},
        description=f"生成图像: {prompt[:80]}",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        reason = outcome.block_reason or (
            "等待用户确认" if outcome.needs_confirm else "超过生成配额"
        )
        logger.warning(f"[{session_id}] generate_image 被门控阻断: {reason}")
        return ImageResult(prompt=prompt, image_urls=[], blocked=True, block_reason=reason)

    logger.info(f"[{session_id}] generate_image: {prompt[:80]}, params={params}")
    # 实际图像生成委托 actions 层（generate_image_action）完成
    image_urls: List[str] = []
    return ImageResult(prompt=prompt, image_urls=image_urls)


def assemble_text_package(
    template: str,
    context: Dict[str, Any],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> TextPackageResult:
    """
    C 类门控 — 组装文字交付物包（设计说明书、评审报告等）。
    """
    request = ActionRequest(
        action_name="generate_text_package",
        context={"session_id": session_id},
        description=f"文字包组装: template={template}",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        return TextPackageResult(template_id=template, sections=[], blocked=True)

    logger.info(f"[{session_id}] assemble_text_package: template={template}")
    sections: List[Dict[str, str]] = []
    return TextPackageResult(template_id=template, sections=sections)


def build_chart(
    chart_type: str,
    data: Dict[str, Any],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> ChartResult:
    """
    C 类门控 — 生成数据图表（预算对比、进度甘特图等）。
    """
    request = ActionRequest(
        action_name="assemble_chart",
        context={"session_id": session_id},
        description=f"图表生成: type={chart_type}",
    )
    outcome = gate_engine.check(
        request.action_name,
        context=request.context,
        call_counts=call_counts or {},
    )

    if not outcome.can_proceed:
        return ChartResult(chart_type=chart_type, data=data, blocked=True)

    logger.info(f"[{session_id}] build_chart: type={chart_type}")
    return ChartResult(chart_type=chart_type, data=data)
