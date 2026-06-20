"""Public contract constants for the demand reconstruction module.

This module is intentionally small: it gives runtime code, routes, tests, and
documentation one shared place for the LLM-first contract identifiers.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

DEMAND_RECONSTRUCTION_MODULE_ID = "demand-reconstruction"
DEMAND_RECONSTRUCTION_VERSION = "v1.4-llm-first-typed-unavailability"

DEMAND_RECONSTRUCTION_CARD_TYPE = "demand_reconstruction_blueprint"
DEMAND_RECONSTRUCTION_INTENT = "demand_reconstruction_blueprint"

UNDERSTANDING_UNAVAILABLE = "UNDERSTANDING_UNAVAILABLE"
SYNTHESIS_UNAVAILABLE = "SYNTHESIS_UNAVAILABLE"
LLM_FIRST_REQUIRED_ERROR_CODES = frozenset(
    {
        UNDERSTANDING_UNAVAILABLE,
        SYNTHESIS_UNAVAILABLE,
    }
)
LLM_FIRST_REQUIRED_HTTP_STATUS = 503

SILENT_RULE_FALLBACK_FORBIDDEN = "不得静默退回旧规则蓝图"


class DemandReconstructionUnavailable(RuntimeError):
    """Raised when the LLM-first demand reconstruction path cannot produce output."""

    def __init__(
        self,
        *,
        error_code: str,
        diagnostics: Optional[Dict[str, Any]] = None,
        user_message: str = "智能识别暂不可用，请重试。",
    ) -> None:
        super().__init__(user_message)
        self.error_code = error_code
        self.user_message = user_message
        self.diagnostics = dict(diagnostics or {})
