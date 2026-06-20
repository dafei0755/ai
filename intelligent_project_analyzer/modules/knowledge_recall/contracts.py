"""Public contract constants for runtime knowledge recall."""

from __future__ import annotations

from typing import Any, Dict, Tuple

KNOWLEDGE_RECALL_MODULE_ID = "knowledge-recall"
KNOWLEDGE_RECALL_VERSION = "v0.1-readonly-runtime-contract"

KNOWLEDGE_RECALL_OWNED_PATHS: Tuple[str, ...] = (
    "intelligent_project_analyzer/services/knowledge_asset_runtime.py",
    "intelligent_project_analyzer/services/knowledge_asset_registry.py",
    "intelligent_project_analyzer/services/governed_knowledge_retrieval.py",
    "intelligent_project_analyzer/services/knowledge_package_registry.py",
)

KNOWLEDGE_RECALL_OUTPUT_KEYS: Tuple[str, ...] = (
    "cards",
    "graph_context",
    "retrieval_trace",
    "policy",
)

KNOWLEDGE_RECALL_FORBIDDEN_RESPONSIBILITIES: Tuple[str, ...] = (
    "create_asset_draft",
    "publish_approved_card",
    "enqueue_review_item",
    "classification_mutation",
    "ontology_mutation",
)


def knowledge_recall_contract() -> Dict[str, Any]:
    """Return the stable boundary for approved-card runtime recall."""

    return {
        "module_id": KNOWLEDGE_RECALL_MODULE_ID,
        "version": KNOWLEDGE_RECALL_VERSION,
        "owned_paths": list(KNOWLEDGE_RECALL_OWNED_PATHS),
        "output_keys": list(KNOWLEDGE_RECALL_OUTPUT_KEYS),
        "forbidden_responsibilities": list(KNOWLEDGE_RECALL_FORBIDDEN_RESPONSIBILITIES),
    }
