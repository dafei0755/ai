from pathlib import Path

from intelligent_project_analyzer.modules.scheme_advisor.contracts import (
    SCHEME_ADVISOR_ENTRY_FORBIDDEN_RESPONSIBILITIES,
    SCHEME_ADVISOR_ENTRY_OWNED_PATHS,
    SCHEME_ADVISOR_ENTRY_PUBLIC_ROUTE_REQUIRES_HANDOFF,
    SCHEME_ADVISOR_ENTRY_REQUIRED_HANDOFF_KEYS,
    SCHEME_ADVISOR_ENTRY_VERSION,
    scheme_advisor_entry_contract,
)


ROOT = Path(__file__).resolve().parents[2]
MODULE_REGISTRY = ROOT / "docs/development/MODULE_REGISTRY.md"
FEATURE_LEDGER = ROOT / "docs/development/FEATURE_VERSION_LEDGER.md"
ROUTE = ROOT / "intelligent_project_analyzer/api/dual_mode_routes.py"
SERVICE = ROOT / "intelligent_project_analyzer/services/scheme_advisor_entry_service.py"


def test_scheme_advisor_entry_contract_defines_handoff_boundary() -> None:
    contract = scheme_advisor_entry_contract()

    assert contract["module_id"] == "scheme-advisor-entry"
    assert contract["version"] == SCHEME_ADVISOR_ENTRY_VERSION
    assert contract["public_route_requires_handoff"] is True
    assert "handoff_requested" in SCHEME_ADVISOR_ENTRY_REQUIRED_HANDOFF_KEYS
    assert "brief_handoff_slots" in SCHEME_ADVISOR_ENTRY_REQUIRED_HANDOFF_KEYS
    assert "demand_reconstruction_generation" in SCHEME_ADVISOR_ENTRY_FORBIDDEN_RESPONSIBILITIES
    assert "llm_first_bypass" in SCHEME_ADVISOR_ENTRY_FORBIDDEN_RESPONSIBILITIES


def test_scheme_advisor_entry_owned_paths_exist() -> None:
    for relative_path in SCHEME_ADVISOR_ENTRY_OWNED_PATHS:
        assert (ROOT / relative_path).exists(), relative_path


def test_public_conversation_route_only_enters_formal_intake_after_demand_reconstruction_gate() -> None:
    source = ROUTE.read_text(encoding="utf-8")

    assert "DemandReconstructionService(" in source
    assert "SchemeAdvisorEntryService" in source
    assert "demand_reconstruction_result and demand_reconstruction_result.get(\"handoff_requested\")" in source
    assert "force_brief_intake_from_demand_reconstruction = True" in source
    assert "if (not demand_reconstruction_result or force_brief_intake_from_demand_reconstruction) and is_scheme_advisor_entry_enabled()" in source
    assert "SchemeAdvisorEntryService(" in source.split("DemandReconstructionService(", 1)[1]


def test_scheme_service_preserves_demand_reconstruction_handoff_context() -> None:
    source = SERVICE.read_text(encoding="utf-8")

    assert "demand_reconstruction_handoff_context" in source
    assert "has_demand_reconstruction_handoff" in source
    assert "handoff_requested" in source
    assert "_apply_demand_reconstruction_handoff_to_round_1_card" in source
    assert "已继承需求重构行动蓝图" in source
    assert '"demand_reconstruction_handoff": demand_reconstruction_context' in source


def test_scheme_advisor_entry_is_registered_in_development_docs() -> None:
    registry_text = MODULE_REGISTRY.read_text(encoding="utf-8")
    ledger_text = FEATURE_LEDGER.read_text(encoding="utf-8")

    assert "module_id: scheme-advisor-entry" in registry_text
    assert "current_version: v0.1-demand-reconstruction-handoff-contract" in registry_text
    assert "intelligent_project_analyzer/modules/scheme_advisor/contracts.py" in registry_text
    assert "tests/unit/test_scheme_advisor_entry_module_contract_guard.py" in registry_text
    assert "scheme-advisor-entry" in ledger_text
    assert "v0.1-demand-reconstruction-handoff-contract" in ledger_text
