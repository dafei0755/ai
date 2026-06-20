from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "intelligent_project_analyzer/services/demand_reconstruction_service.py"
ROUTE = ROOT / "intelligent_project_analyzer/api/dual_mode_routes.py"
CONTRACTS = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/contracts.py"
SEMANTIC_ROUTER = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/semantic_router.py"
SYNTHESIS = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/synthesis.py"
GOVERNANCE = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/governance.py"
ALIGNMENT_GATE = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/alignment_gate.py"
INSIGHT_QUALITY_GATE = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/insight_quality_gate.py"
RESPONSE_BUILDER = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/response_builder.py"
SEMANTIC_CONTEXT_APPLIER = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/semantic_context_applier.py"
BLUEPRINT_COORDINATOR = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/blueprint_coordinator.py"
ENTRY_CLASSIFIER = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/entry_classifier.py"
PIPELINE = ROOT / "intelligent_project_analyzer/modules/demand_reconstruction/pipeline.py"
DOC = ROOT / "docs/development/方案高参需求重构运行时开发纲领.md"


def test_demand_reconstruction_service_keeps_llm_first_semantic_router_contract() -> None:
    source = SERVICE.read_text(encoding="utf-8")
    coordinator_source = BLUEPRINT_COORDINATOR.read_text(encoding="utf-8")

    assert "class DemandReconstructionUnavailable" in source
    assert "def _build_llm_semantic_understanding" in source
    assert "LLM Semantic Router" in source
    assert "UNDERSTANDING_UNAVAILABLE" in source
    assert "SYNTHESIS_UNAVAILABLE" in source
    assert "DEMAND_RECONSTRUCTION_CARD_TYPE" in source
    assert "semantic_fallback" in coordinator_source


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


def test_demand_reconstruction_alignment_gate_is_module_boundary() -> None:
    gate_source = ALIGNMENT_GATE.read_text(encoding="utf-8")
    service_source = SERVICE.read_text(encoding="utf-8")
    pipeline_source = PIPELINE.read_text(encoding="utf-8")

    assert "class DemandReconstructionAlignmentGate" in gate_source
    assert "def maybe_reject_to_semantic_fallback" in gate_source
    assert "def reject_to_semantic_fallback" in gate_source
    assert "def evaluate_alignment_shadow" in gate_source
    assert "def append_alignment_rejection_signal" in gate_source
    assert "DemandReconstructionAlignmentGate" in service_source
    assert "self._alignment_gate.maybe_reject_to_semantic_fallback" in pipeline_source
    assert "evaluate_semantic_alignment" not in service_source


def test_demand_reconstruction_insight_quality_gate_is_module_boundary() -> None:
    gate_source = INSIGHT_QUALITY_GATE.read_text(encoding="utf-8")
    service_source = SERVICE.read_text(encoding="utf-8")
    pipeline_source = PIPELINE.read_text(encoding="utf-8")

    assert "class DemandReconstructionInsightQualityGate" in gate_source
    assert "def apply" in gate_source
    assert "def append_insight_quality_signal" in gate_source
    assert "DemandReconstructionInsightQualityEvaluator" in gate_source
    assert "DemandReconstructionInsightQualityGate" in service_source
    assert "self._insight_quality_gate.apply" in pipeline_source
    assert "self._insight_quality_evaluator.evaluate" not in service_source


def test_demand_reconstruction_response_builder_is_module_boundary() -> None:
    builder_source = RESPONSE_BUILDER.read_text(encoding="utf-8")
    service_source = SERVICE.read_text(encoding="utf-8")
    pipeline_source = PIPELINE.read_text(encoding="utf-8")

    assert "class DemandReconstructionResponseBuilder" in builder_source
    assert "def render_reply" in builder_source
    assert "def build_card" in builder_source
    assert "def build_result" in builder_source
    assert "def public_adapter_context" in builder_source
    assert "DemandReconstructionResponseBuilder" in service_source
    assert "self._response_builder.render_reply" in pipeline_source
    assert "self._response_builder.build_result" in pipeline_source
    assert "datetime.now().isoformat()" not in service_source


def test_demand_reconstruction_semantic_context_applier_is_module_boundary() -> None:
    applier_source = SEMANTIC_CONTEXT_APPLIER.read_text(encoding="utf-8")
    service_source = SERVICE.read_text(encoding="utf-8")

    assert "class DemandReconstructionSemanticContextApplier" in applier_source
    assert "def apply" in applier_source
    assert "def refresh_asset_scan" in applier_source
    assert "def apply_governance_context" in applier_source
    assert "def llm_semantic_candidates" in applier_source
    assert "def merge_llm_and_rule_candidates" in applier_source
    assert "DemandReconstructionSemanticContextApplier" in service_source
    assert "self._semantic_context_applier.apply" in service_source
    assert "self._semantic_context_applier.llm_semantic_candidates" in service_source


def test_demand_reconstruction_blueprint_coordinator_is_module_boundary() -> None:
    coordinator_source = BLUEPRINT_COORDINATOR.read_text(encoding="utf-8")
    service_source = SERVICE.read_text(encoding="utf-8")

    assert "class DemandReconstructionBlueprintCoordinator" in coordinator_source
    assert "def build_blueprint" in coordinator_source
    assert "def _fallback_plan" in coordinator_source
    assert "SYNTHESIS_UNAVAILABLE" in coordinator_source
    assert "UNDERSTANDING_UNAVAILABLE" in coordinator_source
    assert "DemandReconstructionBlueprintCoordinator" in service_source
    assert "self._blueprint_coordinator.build_blueprint" in service_source


def test_demand_reconstruction_entry_classifier_is_module_boundary() -> None:
    classifier_source = ENTRY_CLASSIFIER.read_text(encoding="utf-8")
    service_source = SERVICE.read_text(encoding="utf-8")

    assert "class DemandReconstructionEntryClassifier" in classifier_source
    assert "def should_handle" in classifier_source
    assert "def is_formal_brief_request" in classifier_source
    assert "def is_demand_reconstruction_followup" in classifier_source
    assert "should_enter_demand_reconstruction" in classifier_source
    assert "DemandReconstructionEntryClassifier" in service_source
    assert "self._entry_classifier.should_handle" in service_source
    assert "_FORMAL_TERMS" not in service_source


def test_demand_reconstruction_pipeline_is_module_boundary() -> None:
    pipeline_source = PIPELINE.read_text(encoding="utf-8")
    service_source = SERVICE.read_text(encoding="utf-8")

    assert "class DemandReconstructionPipeline" in pipeline_source
    assert "def run" in pipeline_source
    assert "def _build_llm_semantic_understanding" in pipeline_source
    assert "semantic_alignment_shadow" in pipeline_source
    assert "governance_persistence" in pipeline_source
    assert "DemandReconstructionPipeline" in service_source
    assert "self._pipeline.run" in service_source
    assert "self._response_builder.build_result" not in service_source
