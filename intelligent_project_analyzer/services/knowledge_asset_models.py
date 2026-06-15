"""Governance primitives for file-backed knowledge assets."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


class KnowledgeAssetValidationError(ValueError):
    """Raised when a candidate knowledge asset fails governance checks."""


REQUIRED_CARD_FIELDS = (
    "card_id",
    "title",
    "source_role",
    "species",
    "knowledge_status",
    "evidence_level",
    "allowed_use",
    "not_allowed_use",
    "ontology_dimension_ids",
    "package_ids",
)

V33_APPROVED_CARD_FIELDS = (
    "source_refs",
    "grid_coordinate",
    "production_method",
    "time_validity",
    "transferability",
    "output_usage",
    "task_brief_chapter",
    "judgment_bet",
)

VALID_SOURCE_ROLES = {
    "source_to_translate",
    "transformation_boundary",
    "tool_material",
    "translation_method",
    "project_output",
}

VALID_KNOWLEDGE_STATUS = {
    "raw_source",
    "candidate",
    "processed_insight",
    "verified_evidence",
    "deprecated",
}

VALID_EVIDENCE_LEVEL = {
    "none",
    "weak_evidence",
    "supporting_evidence",
    "strong_evidence",
}


def require_non_empty_mapping(data: Dict[str, Any], field_names: Iterable[str]) -> None:
    for field_name in field_names:
        value = data.get(field_name)
        if value is None or value == "" or value == [] or value == {}:
            raise KnowledgeAssetValidationError(f"{field_name} is required")


def _require_list(data: Dict[str, Any], field_name: str) -> List[Any]:
    value = data.get(field_name)
    if not isinstance(value, list) or not value:
        raise KnowledgeAssetValidationError(f"{field_name} must be a non-empty list")
    return value


def validate_candidate_bundle(bundle: Dict[str, Any]) -> None:
    """Validate a candidate bundle before review or approval."""
    if not isinstance(bundle, dict):
        raise KnowledgeAssetValidationError("bundle must be a mapping")

    card = bundle.get("candidate_card")
    if not isinstance(card, dict):
        raise KnowledgeAssetValidationError("candidate_card is required")

    require_non_empty_mapping(card, REQUIRED_CARD_FIELDS)

    if card["source_role"] not in VALID_SOURCE_ROLES:
        raise KnowledgeAssetValidationError(f"invalid source_role: {card['source_role']}")
    if card["knowledge_status"] not in VALID_KNOWLEDGE_STATUS:
        raise KnowledgeAssetValidationError(f"invalid knowledge_status: {card['knowledge_status']}")
    if card["evidence_level"] not in VALID_EVIDENCE_LEVEL:
        raise KnowledgeAssetValidationError(f"invalid evidence_level: {card['evidence_level']}")

    for field_name in ("species", "allowed_use", "not_allowed_use", "ontology_dimension_ids", "package_ids"):
        _require_list(card, field_name)

    for package_id in card["package_ids"]:
        if not str(package_id).startswith("kp."):
            raise KnowledgeAssetValidationError(f"invalid package_id: {package_id}")

    source = bundle.get("source_document")
    if not isinstance(source, dict):
        raise KnowledgeAssetValidationError("source_document is required")
    require_non_empty_mapping(source, ("source_id", "source_path", "source_type"))

    observation = bundle.get("observation_card")
    if not isinstance(observation, dict):
        raise KnowledgeAssetValidationError("observation_card is required")
    require_non_empty_mapping(observation, ("observation_id", "source_type"))

    cases = bundle.get("case_objects")
    if not isinstance(cases, list) or not cases:
        raise KnowledgeAssetValidationError("case_objects must be a non-empty list")

    motif_vocabulary = bundle.get("motif_vocabulary")
    if not isinstance(motif_vocabulary, dict):
        raise KnowledgeAssetValidationError("motif_vocabulary is required")
    families = motif_vocabulary.get("motif_families")
    if not isinstance(families, dict) or not families:
        raise KnowledgeAssetValidationError("motif_vocabulary.motif_families is required")
