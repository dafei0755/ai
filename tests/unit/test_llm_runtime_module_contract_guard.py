from pathlib import Path

from intelligent_project_analyzer.modules.demand_reconstruction.contracts import (
    LLM_FIRST_REQUIRED_HTTP_STATUS,
    UNDERSTANDING_UNAVAILABLE,
)
from intelligent_project_analyzer.modules.llm_runtime.contracts import (
    LLM_RUNTIME_DIAGNOSTIC_KEYS,
    LLM_RUNTIME_FORBIDDEN_REQUIRED_SUCCESS_STATES,
    LLM_RUNTIME_OWNED_PATHS,
    LLM_RUNTIME_REQUIRED_FAILURE_CONTRACT,
    LLM_RUNTIME_VERSION,
    llm_runtime_contract,
)


ROOT = Path(__file__).resolve().parents[2]
MODULE_REGISTRY = ROOT / "docs/development/MODULE_REGISTRY.md"
FEATURE_LEDGER = ROOT / "docs/development/FEATURE_VERSION_LEDGER.md"
LLM_FACTORY = ROOT / "intelligent_project_analyzer/services/llm_factory.py"
MULTI_LLM_FACTORY = ROOT / "intelligent_project_analyzer/services/multi_llm_factory.py"
DEMAND_LLM = ROOT / "intelligent_project_analyzer/services/demand_reconstruction_llm.py"
DUAL_MODE_ROUTE = ROOT / "intelligent_project_analyzer/api/dual_mode_routes.py"


def test_llm_runtime_contract_centralizes_provider_fallback_semantics() -> None:
    contract = llm_runtime_contract()

    assert contract["module_id"] == "llm-runtime"
    assert contract["version"] == LLM_RUNTIME_VERSION
    assert contract["required_failure_contract"] == LLM_RUNTIME_REQUIRED_FAILURE_CONTRACT
    assert "provider_chain" in LLM_RUNTIME_DIAGNOSTIC_KEYS
    assert "blocked_reasons" in LLM_RUNTIME_DIAGNOSTIC_KEYS
    assert "llm_partial" in LLM_RUNTIME_FORBIDDEN_REQUIRED_SUCCESS_STATES
    assert "semantic_fallback" in LLM_RUNTIME_FORBIDDEN_REQUIRED_SUCCESS_STATES


def test_llm_runtime_owned_paths_exist() -> None:
    for relative_path in LLM_RUNTIME_OWNED_PATHS:
        assert (ROOT / relative_path).exists(), relative_path


def test_llm_runtime_sources_keep_fallback_and_diagnostics_entrypoints() -> None:
    llm_factory_source = LLM_FACTORY.read_text(encoding="utf-8")
    multi_source = MULTI_LLM_FACTORY.read_text(encoding="utf-8")
    demand_llm_source = DEMAND_LLM.read_text(encoding="utf-8-sig")

    assert "def create_llm" in llm_factory_source
    assert "class FallbackLLM" in multi_source
    assert "def invoke" in multi_source
    assert "所有 LLM 提供商调用失败" in multi_source
    assert "def create_demand_reconstruction_llm" in demand_llm_source
    assert "def describe_demand_reconstruction_llm_config" in demand_llm_source
    assert "blocked_reasons" in demand_llm_source


def test_required_llm_failure_remains_typed_http_503_not_partial_success() -> None:
    route_source = DUAL_MODE_ROUTE.read_text(encoding="utf-8")
    registry_text = MODULE_REGISTRY.read_text(encoding="utf-8")

    assert LLM_FIRST_REQUIRED_HTTP_STATUS == 503
    assert UNDERSTANDING_UNAVAILABLE == "UNDERSTANDING_UNAVAILABLE"
    assert "DemandReconstructionUnavailable" in route_source
    assert "LLM_FIRST_REQUIRED_HTTP_STATUS" in route_source
    assert "llm_partial 不能在 required 模式下被当成最终成功" in registry_text
    assert "typed_unavailability_http_503" in registry_text


def test_llm_runtime_is_registered_in_development_docs() -> None:
    registry_text = MODULE_REGISTRY.read_text(encoding="utf-8")
    ledger_text = FEATURE_LEDGER.read_text(encoding="utf-8")

    assert "module_id: llm-runtime" in registry_text
    assert "current_version: v0.1-provider-fallback-contract" in registry_text
    assert "intelligent_project_analyzer/modules/llm_runtime/contracts.py" in registry_text
    assert "tests/unit/test_llm_runtime_module_contract_guard.py" in registry_text
    assert "llm-runtime" in ledger_text
    assert "v0.1-provider-fallback-contract" in ledger_text
