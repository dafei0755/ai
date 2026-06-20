"""Public contract constants for the demand reconstruction module.

This module is intentionally small: it gives runtime code, routes, tests, and
documentation one shared place for the LLM-first contract identifiers.
"""

from __future__ import annotations

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