"""Export approved knowledge assets into Milvus-importable documents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .knowledge_asset_registry import KnowledgeAssetRegistry


def export_approved_assets_as_documents(
    registry: Optional[KnowledgeAssetRegistry] = None,
) -> List[Dict[str, Any]]:
    registry = registry or KnowledgeAssetRegistry()
    documents: List[Dict[str, Any]] = []
    for card in registry.find_cards():
        for package_id in card.get("package_ids") or []:
            text = "\n".join(
                part
                for part in [
                    str(card.get("title") or ""),
                    str(card.get("summary") or ""),
                    "allowed_use: " + ", ".join(card.get("allowed_use") or []),
                    "not_allowed_use: " + ", ".join(card.get("not_allowed_use") or []),
                ]
                if part
            )
            documents.append(
                {
                    "text": text,
                    "metadata": {
                        "card_id": card.get("card_id"),
                        "package_id": package_id,
                        "source_type": "approved_knowledge_card",
                        "review_status": card.get("status") or "approved",
                        "ontology_dimension_ids": card.get("ontology_dimension_ids") or [],
                        "evidence_level": card.get("evidence_level"),
                        "evidence_strength": card.get("evidence_strength"),
                        "knowledge_status": card.get("knowledge_status"),
                        "allowed_use": card.get("allowed_use") or [],
                        "not_allowed_use": card.get("not_allowed_use") or [],
                        "source_refs": card.get("source_refs") or [],
                        "transferability": card.get("transferability") or {},
                        "time_validity": card.get("time_validity") or {},
                    },
                }
            )
    return documents


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export approved knowledge assets as JSONL documents")
    parser.add_argument("--jsonl", required=True)
    args = parser.parse_args(argv)

    output_path = Path(args.jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    docs = export_approved_assets_as_documents()
    output_path.write_text(
        "\n".join(json.dumps(doc, ensure_ascii=False) for doc in docs),
        encoding="utf-8",
    )
    print(f"exported_documents: {len(docs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
