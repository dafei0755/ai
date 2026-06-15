"""Admin-facing governance views for approved knowledge cards."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .knowledge_asset_ingestion import ASSET_ROOT
from .knowledge_asset_models import V33_APPROVED_CARD_FIELDS
from .knowledge_asset_registry import KnowledgeAssetRegistry
from .validate_knowledge_asset import validate_asset_root


class ApprovedKnowledgeCardService:
    """List and validate approved cards without exposing candidate assets."""

    def __init__(self, asset_root: Optional[Path] = None) -> None:
        self.asset_root = Path(asset_root or ASSET_ROOT)
        self.registry = KnowledgeAssetRegistry(self.asset_root)

    def list_cards(self) -> Dict[str, Any]:
        cards = [self._summarize_card(card) for card in self.registry.find_cards()]
        package_ids = {
            package_id
            for card in cards
            for package_id in card.get("package_ids", [])
        }
        missing_count = sum(len(card["missing_v33_fields"]) for card in cards)
        return {
            "schema_version": "approved_knowledge_cards.v1",
            "summary": {
                "approved_card_count": len(cards),
                "v33_complete_count": sum(1 for card in cards if card["v33_complete"]),
                "missing_v33_field_count": missing_count,
                "package_with_cards_count": len(package_ids),
            },
            "items": cards,
        }

    def health(self) -> Dict[str, Any]:
        data = self.list_cards()
        validation = validate_asset_root(self.asset_root)
        cards_missing_v33 = [
            card["card_id"]
            for card in data["items"]
            if card["missing_v33_fields"]
        ]
        index_errors = [
            error
            for error in validation["errors"]
            if "index points to missing approved card" in error
        ]
        field_errors = [
            error
            for error in validation["errors"]
            if "missing v3.3 fields" in error
        ]
        issues = {
            "cards_missing_v33_fields": cards_missing_v33,
            "index_points_to_missing_cards": index_errors,
            "validation_errors": [
                error for error in validation["errors"] if error not in index_errors + field_errors
            ],
        }
        blocking_count = sum(len(values) for values in issues.values())
        return {
            "schema_version": "approved_knowledge_cards_health.v1",
            "status": "ok" if blocking_count == 0 else "needs_attention",
            "summary": {
                **data["summary"],
                "blocking_issue_count": blocking_count,
            },
            "issues": issues,
        }

    @staticmethod
    def _summarize_card(card: Dict[str, Any]) -> Dict[str, Any]:
        missing = [
            field
            for field in V33_APPROVED_CARD_FIELDS
            if card.get(field) in (None, "", [], {})
        ]
        return {
            "card_id": card.get("card_id"),
            "title": card.get("title"),
            "status": card.get("status"),
            "summary": card.get("summary"),
            "source_role": card.get("source_role"),
            "species": card.get("species") or [],
            "knowledge_status": card.get("knowledge_status"),
            "evidence_level": card.get("evidence_level"),
            "evidence_strength": card.get("evidence_strength"),
            "package_ids": card.get("package_ids") or [],
            "ontology_dimension_ids": card.get("ontology_dimension_ids") or [],
            "allowed_use": card.get("allowed_use") or [],
            "not_allowed_use": card.get("not_allowed_use") or [],
            "source_refs": card.get("source_refs") or [],
            "grid_coordinate": card.get("grid_coordinate") or {},
            "transferability": card.get("transferability") or {},
            "time_validity": card.get("time_validity") or {},
            "output_usage": card.get("output_usage") or [],
            "task_brief_chapter": card.get("task_brief_chapter") or [],
            "judgment_bet": card.get("judgment_bet") or {},
            "v33_complete": not missing,
            "missing_v33_fields": missing,
        }
