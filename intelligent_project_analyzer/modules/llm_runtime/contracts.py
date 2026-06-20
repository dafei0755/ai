"""Public contract constants for LLM provider runtime and fallback behavior."""

from __future__ import annotations

from typing import Any, Dict, Tuple

LLM_RUNTIME_MODULE_ID = "llm-runtime"
LLM_RUNTIME_VERSION = "v0.1-provider-fallback-contract"

LLM_RUNTIME_OWNED_PATHS: Tuple[str, ...] = (
    "intelligent_project_analyzer/services/llm_factory.py",
    "intelligent_project_analyzer/services/multi_llm_factory.py",
    "intelligent_project_analyzer/services/demand_reconstruction_llm.py",
    "scripts/smoke_demand_reconstruction_llm.py",
)

LLM_RUNTIME_DIAGNOSTIC_KEYS: Tuple[str, ...] = (
    "provider_chain",
    "providers",
    "ready",
    "blocked_reasons",
    "llm_status",
    "llm_error",
    "llm_rejection_reason",
)

LLM_RUNTIME_FORBIDDEN_REQUIRED_SUCCESS_STATES: Tuple[str, ...] = (
    "llm_partial",
    "llm_unavailable",
    "llm_failed",
    "semantic_fallback",
)

LLM_RUNTIME_REQUIRED_FAILURE_CONTRACT = "typed_unavailability_http_503"


def llm_runtime_contract() -> Dict[str, Any]:
    """Return the stable contract for provider readiness and fallback semantics."""

    return {
        "module_id": LLM_RUNTIME_MODULE_ID,
        "version": LLM_RUNTIME_VERSION,
        "owned_paths": list(LLM_RUNTIME_OWNED_PATHS),
        "diagnostic_keys": list(LLM_RUNTIME_DIAGNOSTIC_KEYS),
        "forbidden_required_success_states": list(
            LLM_RUNTIME_FORBIDDEN_REQUIRED_SUCCESS_STATES
        ),
        "required_failure_contract": LLM_RUNTIME_REQUIRED_FAILURE_CONTRACT,
    }
