"""Runtime governance for approved knowledge cards."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .knowledge_asset_registry import KnowledgeAssetRegistry


EVIDENCE_RANK = {
    "none": 0,
    "weak_evidence": 1,
    "supporting_evidence": 2,
    "strong_evidence": 3,
}


def _rank(level: str) -> int:
    return EVIDENCE_RANK.get(str(level or ""), -1)


def compact_card(card: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "card_id": card.get("card_id"),
        "title": card.get("title"),
        "summary": card.get("summary"),
        "source_role": card.get("source_role"),
        "species": card.get("species") or [],
        "knowledge_status": card.get("knowledge_status"),
        "evidence_level": card.get("evidence_level"),
        "evidence_strength": card.get("evidence_strength"),
        "allowed_use": card.get("allowed_use") or [],
        "not_allowed_use": card.get("not_allowed_use") or [],
        "package_ids": card.get("package_ids") or [],
        "ontology_dimension_ids": card.get("ontology_dimension_ids") or [],
        "source_refs": card.get("source_refs") or [],
        "grid_coordinate": card.get("grid_coordinate") or {},
        "transferability": card.get("transferability") or {},
        "time_validity": card.get("time_validity") or {},
        "output_usage": card.get("output_usage") or [],
        "task_brief_chapter": card.get("task_brief_chapter") or [],
    }


def resolve_governed_knowledge_cards(
    package_ids: Optional[Iterable[str]] = None,
    ontology_dimension_ids: Optional[Iterable[str]] = None,
    intended_use: str = "theme_generation",
    min_evidence_level: str = "weak_evidence",
    registry: Optional[KnowledgeAssetRegistry] = None,
) -> List[Dict[str, Any]]:
    registry = registry or KnowledgeAssetRegistry()
    package_set = {str(item) for item in package_ids or [] if item}
    dimension_set = {str(item) for item in ontology_dimension_ids or [] if item}
    cards = registry.find_cards(package_ids=package_set, ontology_dimension_ids=dimension_set)
    min_rank = _rank(min_evidence_level)
    result: List[Dict[str, Any]] = []

    for card in cards:
        card_packages = {str(item) for item in card.get("package_ids") or []}
        card_dimensions = {str(item) for item in card.get("ontology_dimension_ids") or []}
        package_match = bool(package_set and card_packages.intersection(package_set))
        dimension_match = bool(dimension_set and card_dimensions.intersection(dimension_set))
        if (package_set or dimension_set) and not (package_match or dimension_match):
            continue
        if intended_use and intended_use not in (card.get("allowed_use") or []):
            continue
        if intended_use and intended_use in (card.get("not_allowed_use") or []):
            continue
        if _rank(card.get("evidence_level", "")) < min_rank:
            continue
        result.append(compact_card(card))
    return sorted(result, key=lambda item: str(item.get("card_id") or ""))
