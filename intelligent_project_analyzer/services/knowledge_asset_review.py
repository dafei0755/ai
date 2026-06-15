"""Review and promotion helpers for knowledge assets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .knowledge_asset_ingestion import ASSET_ROOT, CASE_GROUP_ID
from .knowledge_asset_models import validate_candidate_bundle


def _read_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _update_index(asset_root: Path, approved_card: Dict[str, Any]) -> None:
    index_path = asset_root / "indexes" / "knowledge_asset_index.yaml"
    index = _read_yaml(index_path) if index_path.exists() else {
        "schema_version": "knowledge_asset_index.v1",
        "cards": {},
        "package_index": {},
        "dimension_index": {},
    }
    card_id = approved_card["card_id"]
    index["cards"][card_id] = {
        "title": approved_card["title"],
        "status": approved_card["status"],
        "evidence_level": approved_card["evidence_level"],
        "knowledge_status": approved_card["knowledge_status"],
        "package_ids": approved_card["package_ids"],
        "ontology_dimension_ids": approved_card["ontology_dimension_ids"],
    }
    for package_id in approved_card["package_ids"]:
        index.setdefault("package_index", {}).setdefault(package_id, [])
        if card_id not in index["package_index"][package_id]:
            index["package_index"][package_id].append(card_id)
    for dimension_id in approved_card["ontology_dimension_ids"]:
        index.setdefault("dimension_index", {}).setdefault(dimension_id, [])
        if card_id not in index["dimension_index"][dimension_id]:
            index["dimension_index"][dimension_id].append(card_id)
    _write_yaml(index_path, index)


def approve_candidate(
    card_id: str,
    asset_root: Path | str = ASSET_ROOT,
    reviewer_id: str = "codex",
    note: str = "",
) -> Dict[str, Any]:
    asset_root = Path(asset_root)
    candidate_path = asset_root / "candidates" / f"{card_id}.yaml"
    bundle = _read_yaml(candidate_path)
    validate_candidate_bundle(bundle)

    review = {
        "reviewer_id": reviewer_id,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "decision": "approved",
        "note": note,
    }
    approved_card = dict(bundle["candidate_card"])
    approved_card["status"] = "approved"
    approved_card["review"] = review

    _write_yaml(asset_root / "approved" / f"{card_id}.yaml", approved_card)
    _write_yaml(
        asset_root / "case_objects" / f"{CASE_GROUP_ID}.yaml",
        {
            "schema_version": "case_object_group.v1",
            "case_group_id": CASE_GROUP_ID,
            "card_id": card_id,
            "cases": bundle["case_objects"],
        },
    )
    _write_yaml(
        asset_root / "vocabularies" / f"{bundle['motif_vocabulary']['vocabulary_id']}.yaml",
        bundle["motif_vocabulary"],
    )
    _write_yaml(
        asset_root / "reviews" / f"{card_id}.review.yaml",
        {"schema_version": "knowledge_asset_review.v1", "card_id": card_id, "review": review},
    )
    _update_index(asset_root, approved_card)
    return {"status": "approved", "card_id": card_id}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Knowledge asset review")
    subparsers = parser.add_subparsers(dest="command", required=True)
    approve = subparsers.add_parser("approve")
    approve.add_argument("card_id")
    approve.add_argument("--asset-root", default=str(ASSET_ROOT))
    approve.add_argument("--reviewer", default="codex")
    approve.add_argument("--note", default="")
    args = parser.parse_args(argv)

    if args.command == "approve":
        result = approve_candidate(args.card_id, Path(args.asset_root), args.reviewer, args.note)
        print(f"approved: {result['card_id']}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
