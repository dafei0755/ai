"""Public contract constants for knowledge governance."""

from __future__ import annotations

from typing import Any, Dict, Tuple

KNOWLEDGE_GOVERNANCE_MODULE_ID = "knowledge-governance"
KNOWLEDGE_GOVERNANCE_VERSION = "v0.1-governed-contract"

KNOWLEDGE_GOVERNANCE_OWNED_PATHS: Tuple[str, ...] = (
    "intelligent_project_analyzer/services/knowledge_governance_store.py",
    "intelligent_project_analyzer/services/knowledge_asset_draft_generation.py",
    "intelligent_project_analyzer/services/approved_knowledge_card_service.py",
    "intelligent_project_analyzer/api/routes/advisor_knowledge_asset_drafts.py",
)

KNOWLEDGE_GOVERNANCE_ALLOWED_ACTIONS: Tuple[str, ...] = (
    "create_asset_draft",
    "create_learning_candidate",
    "enqueue_review_item",
    "publish_approved_card",
    "append_audit_event",
)

KNOWLEDGE_GOVERNANCE_FORBIDDEN_RESPONSIBILITIES: Tuple[str, ...] = (
    "runtime_card_ranking",
    "classification_mutation",
    "ontology_mutation",
    "project_type_detection",
    "final_solution_generation",
)


def knowledge_governance_contract() -> Dict[str, Any]:
    """Return the stable boundary for candidate/review/approval/audit flows."""

    return {
        "module_id": KNOWLEDGE_GOVERNANCE_MODULE_ID,
        "version": KNOWLEDGE_GOVERNANCE_VERSION,
        "owned_paths": list(KNOWLEDGE_GOVERNANCE_OWNED_PATHS),
        "allowed_actions": list(KNOWLEDGE_GOVERNANCE_ALLOWED_ACTIONS),
        "forbidden_responsibilities": list(KNOWLEDGE_GOVERNANCE_FORBIDDEN_RESPONSIBILITIES),
    }
