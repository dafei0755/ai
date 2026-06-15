"""
execution/skills/generation_skills.py 鈥?鐢熸垚绫绘妧鑳?

Copilot 鐢熸垚锛?026-03-22锛?

鎶€鑳藉垪琛細
  - generate_image         (C 绫婚棬鎺?锛氱敓鎴愭晥鏋滃浘 / 骞抽潰鍥?
  - assemble_text_package  (C 绫婚棬鎺?锛氱粍瑁呮枃瀛椾氦浠樼墿鍖?
  - build_chart            (C 绫婚棬鎺?锛氱敓鎴愭暟鎹浘琛?
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
# 缁撴灉缁撴瀯
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
# 鐢熸垚鎶€鑳?
# ---------------------------------------------------------------------------


def generate_image(
    prompt: str,
    params: Dict[str, Any],
    gate_engine: RiskGateEngine,
    session_id: str = "unknown",
    call_counts: Optional[Dict[str, int]] = None,
) -> ImageResult:
    """
    C 绫婚棬鎺?鈥?鐢熸垚鏁堟灉鍥?/ 骞抽潰鍥俱€?

    params: {"style": "鍐欏疄", "resolution": "1024x768", "count": 2}
    """
    request = ActionRequest(
        action_name="generate_image",
        context={"session_id": session_id},
        description=f"鐢熸垚鍥惧儚: {prompt[:80]}",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        reason = outcome.block_reason or (
            "绛夊緟鐢ㄦ埛纭" if outcome.needs_confirm else "瓒呰繃鐢熸垚閰嶉"
        )
        logger.warning(f"[{session_id}] generate_image 琚棬鎺ч樆鏂? {reason}")
        return ImageResult(prompt=prompt, image_urls=[], blocked=True, block_reason=reason)

    logger.info(f"[{session_id}] generate_image: {prompt[:80]}, params={params}")
    # 瀹為檯鍥惧儚鐢熸垚濮旀墭 actions 灞傦紙generate_image_action锛夊畬鎴?
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
    C 绫婚棬鎺?鈥?缁勮鏂囧瓧浜や粯鐗╁寘锛堣璁¤鏄庝功銆佽瘎瀹℃姤鍛婄瓑锛夈€?
    """
    request = ActionRequest(
        action_name="generate_text_package",
        context={"session_id": session_id},
        description=f"鏂囧瓧鍖呯粍瑁? template={template}",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

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
    C 绫婚棬鎺?鈥?鐢熸垚鏁版嵁鍥捐〃锛堥绠楀姣斻€佽繘搴︾敇鐗瑰浘绛夛級銆?
    """
    request = ActionRequest(
        action_name="assemble_chart",
        context={"session_id": session_id},
        description=f"鍥捐〃鐢熸垚: type={chart_type}",
    )
    outcome = gate_engine.check(request, call_counts=call_counts or {})

    if not outcome.can_proceed:
        return ChartResult(chart_type=chart_type, data=data, blocked=True)

    logger.info(f"[{session_id}] build_chart: type={chart_type}")
    return ChartResult(chart_type=chart_type, data=data)
