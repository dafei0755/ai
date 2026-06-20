from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "intelligent_project_analyzer/services/demand_reconstruction_service.py"
ROUTE = ROOT / "intelligent_project_analyzer/api/dual_mode_routes.py"
CONTRACTS = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/contracts.py"
SEMANTIC_ROUTER = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/semantic_router.py"
SYNTHESIS = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/synthesis.py"
GOVERNANCE = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/governance.py"
DOC = ROOT / "docs/development/方案高参需求重构运行时开发纲领.md"


def test_demand_reconstruction_service_keeps_llm_first_semantic_router_contract() -> None:
    source = SERVICE.read_text(encoding="utf-8")

    assert "class DemandReconstructionUnavailable" in source
    assert "def _build_llm_semantic_understanding" in source
    assert "LLM Semantic Router" in source
    assert "UNDERSTANDING_UNAVAILABLE" in source
    assert "SYNTHESIS_UNAVAILABLE" in source
    assert "DEMAND_RECONSTRUCTION_CARD_TYPE" in source
    assert "semantic_fallback" in source


def test_conversation_route_maps_required_llm_unavailability_to_http_503() -> None:
    source = ROUTE.read_text(encoding="utf-8")

    assert "DemandReconstructionUnavailable" in source
    assert "DEMAND_RECONSTRUCTION_USE_LLM" in source
    assert "LLM_FIRST_REQUIRED_HTTP_STATUS" in source
    assert "exc.error_code" in source


def test_runtime_doctrine_does_not_reintroduce_silent_rule_fallback_for_llm_first() -> None:
    text = DOC.read_text(encoding="utf-8")

    assert "不得静默退回旧规则蓝图" in text
    assert "UNDERSTANDING_UNAVAILABLE" in text
    assert "SYNTHESIS_UNAVAILABLE" in text
    assert "关闭或失败时，系统必须继续返回规则蓝图" not in text


def test_demand_reconstruction_contracts_centralize_llm_first_identifiers() -> None:
    text = CONTRACTS.read_text(encoding="utf-8")

    assert "DEMAND_RECONSTRUCTION_MODULE_ID" in text
    assert "DEMAND_RECONSTRUCTION_VERSION" in text
    assert "UNDERSTANDING_UNAVAILABLE" in text
    assert "SYNTHESIS_UNAVAILABLE" in text
    assert "LLM_FIRST_REQUIRED_HTTP_STATUS = 503" in text
    assert "不得静默退回旧规则蓝图" in text


def test_demand_reconstruction_semantic_router_is_module_boundary() -> None:
    router_source = SEMANTIC_ROUTER.read_text(encoding="utf-8")
    service_source = SERVICE.read_text(encoding="utf-8")

    assert "class DemandReconstructionSemanticRouter" in router_source
    assert "def build_understanding" in router_source
    assert "def build_prompt" in router_source
    assert "def invoke_with_llm" in router_source
    assert "def parse" in router_source
    assert "DemandReconstructionSemanticRouter" in service_source
    assert "self._semantic_router.build_understanding" in service_source


def test_demand_reconstruction_synthesis_is_module_boundary() -> None:
    synthesis_source = SYNTHESIS.read_text(encoding="utf-8")
    service_source = SERVICE.read_text(encoding="utf-8")

    assert "class DemandReconstructionSynthesis" in synthesis_source
    assert "def build_blueprint" in synthesis_source
    assert "def build_blueprint_with_llm" in synthesis_source
    assert "build_blueprint_from_response_detailed" in synthesis_source
    assert "build_repair_prompt" in synthesis_source
    assert "DemandReconstructionSynthesis" in service_source
    assert "self._synthesis.build_blueprint" in service_source


def test_demand_reconstruction_governance_is_module_boundary() -> None:
    governance_source = GOVERNANCE.read_text(encoding="utf-8")
    service_source = SERVICE.read_text(encoding="utf-8")

    assert "class DemandReconstructionGovernance" in governance_source
    assert "def apply_governed_knowledge_assets" in governance_source
    assert "def persist_governance_signals" in governance_source
    assert "def approved_card_match_metadata" in governance_source
    assert "def compact_governed_knowledge_asset" in governance_source
    assert "DemandReconstructionGovernance" in service_source
    assert "self._governance.apply_governed_knowledge_assets" in service_source
    assert "self._governance.persist_governance_signals" in service_source
