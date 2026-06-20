from pathlib import Path

from intelligent_project_analyzer.modules.project_type.contracts import (
    PROJECT_TYPE_CANONICAL_REGISTRY,
    PROJECT_TYPE_CONTEXT_ROLE,
    PROJECT_TYPE_FORBIDDEN_RESPONSIBILITIES,
    PROJECT_TYPE_REGISTRY_PATHS,
    PROJECT_TYPE_VERSION,
    project_type_detection_contract,
)
from intelligent_project_analyzer.modules.project_type.registry_audit import (
    ProjectTypeRegistryAuditError,
    audit_project_type_registries,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "intelligent_project_analyzer/modules/project_type/contracts.py"
PROJECT_TYPE_DETECTOR = ROOT / "intelligent_project_analyzer/services/project_type_detector.py"
SPACE_CLASSIFICATION = ROOT / "intelligent_project_analyzer/services/space_classification_service.py"
MODULE_REGISTRY = ROOT / "docs/development/MODULE_REGISTRY.md"
FEATURE_LEDGER = ROOT / "docs/development/FEATURE_VERSION_LEDGER.md"


def test_project_type_detection_contract_centralizes_module_boundary() -> None:
    contract = project_type_detection_contract()

    assert contract["module_id"] == "project-type-detection"
    assert contract["version"] == PROJECT_TYPE_VERSION
    assert contract["context_role"] == PROJECT_TYPE_CONTEXT_ROLE
    assert contract["canonical_registry"] == PROJECT_TYPE_CANONICAL_REGISTRY
    assert "demand_reconstruction_entry_preemption" in PROJECT_TYPE_FORBIDDEN_RESPONSIBILITIES
    assert "project_type" in contract["classification_output_keys"]
    assert "evidence" in contract["classification_output_keys"]


def test_project_type_registry_paths_are_real_current_authorities() -> None:
    for relative_path in PROJECT_TYPE_REGISTRY_PATHS:
        assert (ROOT / relative_path).exists(), relative_path

    stale_meta_path = ROOT / "config/project_type_registry_meta.yaml"
    stale_nested_meta_path = (
        ROOT / "intelligent_project_analyzer/config/registries/project_type_registry_meta.yaml"
    )

    assert not stale_meta_path.exists()
    assert not stale_nested_meta_path.exists()


def test_project_type_detector_remains_behavioral_truth_source() -> None:
    detector_source = PROJECT_TYPE_DETECTOR.read_text(encoding="utf-8")
    space_classification_source = SPACE_CLASSIFICATION.read_text(encoding="utf-8")

    assert "PROJECT_TYPE_REGISTRY" in detector_source
    assert "def _get_registry" in detector_source
    assert "detect_with_details(user_input" in space_classification_source
    assert "ProjectTypeDetector()" in space_classification_source


def test_project_type_detection_is_documented_as_context_not_entry_mainline() -> None:
    registry_text = MODULE_REGISTRY.read_text(encoding="utf-8")
    ledger_text = FEATURE_LEDGER.read_text(encoding="utf-8")
    contracts_text = CONTRACTS.read_text(encoding="utf-8")

    assert "current_version: v0.1-governed-contract" in registry_text
    assert "intelligent_project_analyzer/modules/project_type/contracts.py" in registry_text
    assert "tests/unit/test_project_type_module_contract_guard.py" in registry_text
    assert "不得绕过需求重构入口成为新对话第一响应主线" in registry_text
    assert "context_evidence_after_llm_semantic_router" in contracts_text
    assert "project-type-detection" in ledger_text
    assert "v0.1-governed-contract" in ledger_text


def test_project_type_registry_strict_audit_passes_current_authorities() -> None:
    report = audit_project_type_registries()

    assert report["status"] == "ok"
    assert "intelligent_project_analyzer/services/project_type_detector.py" in report["checked_paths"]


def test_project_type_registry_strict_audit_raises_on_yaml_parse_failure(tmp_path) -> None:
    broken = tmp_path / "broken.yaml"
    broken.write_text("items: [unterminated", encoding="utf-8")

    try:
        audit_project_type_registries(root=tmp_path, registry_paths=("broken.yaml",))
    except ProjectTypeRegistryAuditError as exc:
        assert "YAML parse failed" in str(exc)
    else:
        raise AssertionError("expected strict registry audit to fail on invalid YAML")
