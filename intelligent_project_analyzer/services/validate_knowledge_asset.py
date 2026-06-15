"""Validate file-backed knowledge assets."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from .knowledge_asset_ingestion import ASSET_ROOT
from .knowledge_asset_models import (
    KnowledgeAssetValidationError,
    V33_APPROVED_CARD_FIELDS,
    validate_candidate_bundle,
)


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PACKAGE_REGISTRY_PATH = _PROJECT_ROOT / "config" / "knowledge_package_registry.yaml"
_ONTOLOGY_DIMENSION_REGISTRY_PATH = _PROJECT_ROOT / "knowledge_base" / "ontology_dimension_registry.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _known_package_ids() -> Set[str]:
    data = _load_yaml(_PACKAGE_REGISTRY_PATH)
    return set((data.get("packages") or {}).keys())


def _known_ontology_dimension_ids() -> Set[str]:
    data = _load_yaml(_ONTOLOGY_DIMENSION_REGISTRY_PATH)
    return set((data.get("ontology_dimensions") or {}).keys())


def validate_asset_root(asset_root: Path | str = ASSET_ROOT) -> Dict[str, List[str]]:
    asset_root = Path(asset_root)
    errors: List[str] = []
    approved_cards: List[str] = []
    known_packages = _known_package_ids()
    known_dimensions = _known_ontology_dimension_ids()

    for candidate_path in sorted((asset_root / "candidates").glob("*.yaml")):
        try:
            bundle = yaml.safe_load(candidate_path.read_text(encoding="utf-8")) or {}
            validate_candidate_bundle(bundle)
        except KnowledgeAssetValidationError as exc:
            errors.append(f"{candidate_path}: {exc}")

    for approved_path in sorted((asset_root / "approved").glob("*.yaml")):
        card = yaml.safe_load(approved_path.read_text(encoding="utf-8")) or {}
        required = ["card_id", "status", "allowed_use", "not_allowed_use", "package_ids", "ontology_dimension_ids"]
        missing = [field for field in required if not card.get(field)]
        if missing:
            errors.append(f"{approved_path}: missing {', '.join(missing)}")
        missing_v33 = [field for field in V33_APPROVED_CARD_FIELDS if not card.get(field)]
        if missing_v33:
            errors.append(f"{approved_path}: missing v3.3 fields {', '.join(missing_v33)}")
        if card.get("status") != "approved":
            errors.append(f"{approved_path}: status must be approved")
        if card.get("card_id"):
            approved_cards.append(card["card_id"])
        for package_id in card.get("package_ids") or []:
            if package_id not in known_packages:
                errors.append(f"{approved_path}: unknown package_id {package_id}")
        for dimension_id in card.get("ontology_dimension_ids") or []:
            if dimension_id not in known_dimensions:
                errors.append(f"{approved_path}: unknown ontology_dimension_id {dimension_id}")

    approved_set = set(approved_cards)
    index_path = asset_root / "indexes" / "knowledge_asset_index.yaml"
    index = _load_yaml(index_path)
    for card_id in (index.get("cards") or {}).keys():
        if card_id not in approved_set:
            errors.append(f"{index_path}: index points to missing approved card {card_id}")
    for package_id, card_ids in (index.get("package_index") or {}).items():
        if package_id not in known_packages:
            errors.append(f"{index_path}: unknown package_id {package_id}")
        for card_id in card_ids or []:
            if card_id not in approved_set:
                errors.append(f"{index_path}: package index points to missing approved card {card_id}")
    for dimension_id, card_ids in (index.get("dimension_index") or {}).items():
        if dimension_id not in known_dimensions:
            errors.append(f"{index_path}: unknown ontology_dimension_id {dimension_id}")
        for card_id in card_ids or []:
            if card_id not in approved_set:
                errors.append(f"{index_path}: dimension index points to missing approved card {card_id}")

    for case_path in sorted((asset_root / "case_objects").glob("*.yaml")):
        group = _load_yaml(case_path)
        cases = group.get("cases")
        if not isinstance(cases, list) or not cases:
            errors.append(f"{case_path}: case object group has zero cases")
        card_id = group.get("card_id")
        if card_id and card_id not in approved_set:
            errors.append(f"{case_path}: case group points to missing approved card {card_id}")

    return {"errors": errors, "approved_cards": approved_cards}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate knowledge assets")
    parser.add_argument("--asset-root", default=str(ASSET_ROOT))
    args = parser.parse_args(argv)
    result = validate_asset_root(Path(args.asset_root))
    if result["errors"]:
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print(f"validated_approved_cards: {len(result['approved_cards'])}")
    for card_id in result["approved_cards"]:
        print(f"- {card_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
