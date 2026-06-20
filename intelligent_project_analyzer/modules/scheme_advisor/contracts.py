"""Public contract constants for the scheme advisor formal-entry module."""

from __future__ import annotations

from typing import Any, Dict, Tuple

SCHEME_ADVISOR_ENTRY_MODULE_ID = "scheme-advisor-entry"
SCHEME_ADVISOR_ENTRY_VERSION = "v0.1-demand-reconstruction-handoff-contract"

SCHEME_ADVISOR_ENTRY_OWNED_PATHS: Tuple[str, ...] = (
    "intelligent_project_analyzer/services/scheme_advisor_entry_service.py",
    "intelligent_project_analyzer/config/scheme_advisor_version_tiers.yaml",
    "intelligent_project_analyzer/config/scheme_advisor_entry_copy.yaml",
    "intelligent_project_analyzer/interaction",
)

SCHEME_ADVISOR_ENTRY_REQUIRED_HANDOFF_KEYS: Tuple[str, ...] = (
    "handoff_requested",
    "brief_handoff_slots",
)

SCHEME_ADVISOR_ENTRY_PUBLIC_ROUTE_REQUIRES_HANDOFF = True

SCHEME_ADVISOR_ENTRY_FORBIDDEN_RESPONSIBILITIES: Tuple[str, ...] = (
    "demand_reconstruction_generation",
    "llm_first_bypass",
    "project_type_detection",
    "knowledge_asset_mutation",
)


def scheme_advisor_entry_contract() -> Dict[str, Any]:
    """Return the stable contract for formal taskbook intake after handoff."""

    return {
        "module_id": SCHEME_ADVISOR_ENTRY_MODULE_ID,
        "version": SCHEME_ADVISOR_ENTRY_VERSION,
        "owned_paths": list(SCHEME_ADVISOR_ENTRY_OWNED_PATHS),
        "public_route_requires_handoff": SCHEME_ADVISOR_ENTRY_PUBLIC_ROUTE_REQUIRES_HANDOFF,
        "required_handoff_keys": list(SCHEME_ADVISOR_ENTRY_REQUIRED_HANDOFF_KEYS),
        "forbidden_responsibilities": list(SCHEME_ADVISOR_ENTRY_FORBIDDEN_RESPONSIBILITIES),
    }
