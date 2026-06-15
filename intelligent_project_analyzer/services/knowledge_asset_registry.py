"""Runtime registry for approved file-backed knowledge assets."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import yaml
from loguru import logger

from .knowledge_asset_ingestion import ASSET_ROOT


class KnowledgeAssetRegistry:
    """Load approved knowledge cards from the file-backed asset root."""

    def __init__(self, asset_root: Optional[Path] = None) -> None:
        self.asset_root = Path(asset_root or ASSET_ROOT)

    def load_index(self) -> Dict[str, Any]:
        index_path = self.asset_root / "indexes" / "knowledge_asset_index.yaml"
        if not index_path.exists():
            return {"cards": {}, "package_index": {}, "dimension_index": {}}
        try:
            return yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            logger.warning(f"[KnowledgeAssetRegistry] failed to load {index_path}: {exc}")
            return {"cards": {}, "package_index": {}, "dimension_index": {}}

    def get_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        card_path = self.asset_root / "approved" / f"{card_id}.yaml"
        if not card_path.exists():
            return None
        try:
            card = yaml.safe_load(card_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            logger.warning(f"[KnowledgeAssetRegistry] failed to load {card_path}: {exc}")
            return None
        if card.get("status") != "approved":
            return None
        return card

    def find_cards(
        self,
        package_ids: Optional[Iterable[str]] = None,
        ontology_dimension_ids: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        index = self.load_index()
        card_ids: Set[str] = set()
        package_index = index.get("package_index") or {}
        dimension_index = index.get("dimension_index") or {}

        package_filter = [str(item) for item in package_ids or [] if item]
        dimension_filter = [str(item) for item in ontology_dimension_ids or [] if item]

        for package_id in package_filter:
            card_ids.update(str(item) for item in package_index.get(str(package_id), []) or [])
        for dimension_id in dimension_filter:
            card_ids.update(str(item) for item in dimension_index.get(str(dimension_id), []) or [])

        if not card_ids and not package_filter and not dimension_filter:
            card_ids.update(str(item) for item in (index.get("cards") or {}).keys())

        cards = []
        for card_id in sorted(card_ids):
            card = self.get_card(card_id)
            if card:
                cards.append(card)
        return cards
