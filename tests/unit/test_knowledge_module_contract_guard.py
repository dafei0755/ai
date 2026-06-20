from pathlib import Path

from intelligent_project_analyzer.modules.knowledge_governance.contracts import (
    KNOWLEDGE_GOVERNANCE_FORBIDDEN_RESPONSIBILITIES,
    KNOWLEDGE_GOVERNANCE_OWNED_PATHS,
    KNOWLEDGE_GOVERNANCE_VERSION,
    knowledge_governance_contract,
)
from intelligent_project_analyzer.modules.knowledge_recall.contracts import (
    KNOWLEDGE_RECALL_FORBIDDEN_RESPONSIBILITIES,
    KNOWLEDGE_RECALL_OWNED_PATHS,
    KNOWLEDGE_RECALL_VERSION,
    knowledge_recall_contract,
)


ROOT = Path(__file__).resolve().parents[2]
MODULE_REGISTRY = ROOT / "docs/development/MODULE_REGISTRY.md"
FEATURE_LEDGER = ROOT / "docs/development/FEATURE_VERSION_LEDGER.md"
GOVERNANCE_STORE = ROOT / "intelligent_project_analyzer/services/knowledge_governance_store.py"
RECALL_RUNTIME = ROOT / "intelligent_project_analyzer/services/knowledge_asset_runtime.py"
RETRIEVAL_SERVICE = ROOT / "intelligent_project_analyzer/services/governed_knowledge_retrieval.py"


def test_knowledge_governance_contract_defines_candidate_review_approval_boundary() -> None:
    contract = knowledge_governance_contract()

    assert contract["module_id"] == "knowledge-governance"
    assert contract["version"] == KNOWLEDGE_GOVERNANCE_VERSION
    assert "publish_approved_card" in contract["allowed_actions"]
    assert "append_audit_event" in contract["allowed_actions"]
    assert "runtime_card_ranking" in KNOWLEDGE_GOVERNANCE_FORBIDDEN_RESPONSIBILITIES
    assert "classification_mutation" in KNOWLEDGE_GOVERNANCE_FORBIDDEN_RESPONSIBILITIES


def test_knowledge_recall_contract_defines_readonly_runtime_boundary() -> None:
    contract = knowledge_recall_contract()

    assert contract["module_id"] == "knowledge-recall"
    assert contract["version"] == KNOWLEDGE_RECALL_VERSION
    assert "cards" in contract["output_keys"]
    assert "retrieval_trace" in contract["output_keys"]
    assert "publish_approved_card" in KNOWLEDGE_RECALL_FORBIDDEN_RESPONSIBILITIES
    assert "classification_mutation" in KNOWLEDGE_RECALL_FORBIDDEN_RESPONSIBILITIES


def test_knowledge_module_owned_paths_exist() -> None:
    for relative_path in list(KNOWLEDGE_GOVERNANCE_OWNED_PATHS) + list(KNOWLEDGE_RECALL_OWNED_PATHS):
        assert (ROOT / relative_path).exists(), relative_path


def test_governance_store_owns_mutating_review_and_audit_actions() -> None:
    source = GOVERNANCE_STORE.read_text(encoding="utf-8")

    assert "def create_asset_draft" in source
    assert "def create_learning_candidate" in source
    assert "def publish_approved_card" in source
    assert "def _enqueue_review_item" in source
    assert "def _append_audit" in source


def test_runtime_recall_stays_on_approved_card_lookup_and_trace() -> None:
    runtime_source = RECALL_RUNTIME.read_text(encoding="utf-8")
    retrieval_source = RETRIEVAL_SERVICE.read_text(encoding="utf-8")

    assert "def resolve_governed_knowledge_cards" in runtime_source
    assert "allowed_use" in runtime_source
    assert "not_allowed_use" in runtime_source
    assert "approved_card_lookup" in retrieval_source
    assert "approved_only" in retrieval_source
    assert "publish_approved_card" not in runtime_source
    assert "create_asset_draft" not in retrieval_source


def test_knowledge_governance_and_recall_are_separate_registered_modules() -> None:
    registry_text = MODULE_REGISTRY.read_text(encoding="utf-8")
    ledger_text = FEATURE_LEDGER.read_text(encoding="utf-8")

    assert "module_id: knowledge-governance" in registry_text
    assert "module_id: knowledge-recall" in registry_text
    assert "name: 知识资产治理、候选、审核、批准与审计" in registry_text
    assert "name: 知识资产运行时召回" in registry_text
    assert "knowledge-governance" in ledger_text
    assert "knowledge-recall" in ledger_text
