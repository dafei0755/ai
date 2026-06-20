"""Public contract constants for the project type detection module.

This module does not change classification behavior. It gives docs, tests, and
future refactors one stable place to define what project type detection owns and
what it must not do in the LLM-first demand reconstruction path.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

PROJECT_TYPE_MODULE_ID = "project-type-detection"
PROJECT_TYPE_VERSION = "v0.1-governed-contract"

PROJECT_TYPE_CONTEXT_ROLE = "context_evidence_after_llm_semantic_router"
PROJECT_TYPE_CANONICAL_REGISTRY = (
    "intelligent_project_analyzer.services.project_type_detector.PROJECT_TYPE_REGISTRY"
)

PROJECT_TYPE_REGISTRY_PATHS: Tuple[str, ...] = (
    "intelligent_project_analyzer/services/project_type_detector.py",
    "intelligent_project_analyzer/config/registries/classification_master_index.yaml",
    "intelligent_project_analyzer/config/registries/subdomain_registry.yaml",
    "intelligent_project_analyzer/config/registries/founding_type_registry.yaml",
    "intelligent_project_analyzer/config/registries/project_condition_registry.yaml",
    "intelligent_project_analyzer/config/registries/space_axis_registry.yaml",
    "intelligent_project_analyzer/utils/ontology_loader.py",
)

PROJECT_TYPE_CLASSIFICATION_OUTPUT_KEYS: Tuple[str, ...] = (
    "project_type",
    "project_type_name",
    "parent_type",
    "primary_bucket",
    "confidence",
    "industry_domain",
    "space_axis",
    "evidence",
)

PROJECT_TYPE_FORBIDDEN_RESPONSIBILITIES: Tuple[str, ...] = (
    "final_solution_generation",
    "demand_reconstruction_entry_preemption",
    "llm_first_rule_fallback",
    "knowledge_asset_mutation",
    "ontology_mutation",
)


def project_type_detection_contract() -> Dict[str, Any]:
    """Return the stable module contract used by guard tests and docs."""

    return {
        "module_id": PROJECT_TYPE_MODULE_ID,
        "version": PROJECT_TYPE_VERSION,
        "context_role": PROJECT_TYPE_CONTEXT_ROLE,
        "canonical_registry": PROJECT_TYPE_CANONICAL_REGISTRY,
        "registry_paths": list(PROJECT_TYPE_REGISTRY_PATHS),
        "classification_output_keys": list(PROJECT_TYPE_CLASSIFICATION_OUTPUT_KEYS),
        "forbidden_responsibilities": list(PROJECT_TYPE_FORBIDDEN_RESPONSIBILITIES),
    }
