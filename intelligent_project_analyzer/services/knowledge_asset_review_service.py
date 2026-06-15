"""
File-backed knowledge asset review service.

This is the minimal governance layer for candidate knowledge assets:
external generators and internal settlement loops can submit candidates, while
runtime lookup only reads approved assets.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


REVIEWABLE_SOURCE_TYPES = {
    "external_generation",
    "internal_settlement",
    "expert_note",
    "case_material",
}

SETTLEMENT_ATTRIBUTIONS = {
    "card_wrong",
    "card_validated",
    "recall_wrong",
    "execution_deviation",
    "weak_observation",
}

PROMOTION_ATTRIBUTIONS = {
    "card_wrong",
    "card_validated",
}


class KnowledgeAssetReviewService:
    """Manage candidate, approved, and review records for knowledge assets."""

    def __init__(self, root_dir: Optional[Path | str] = None):
        base = Path(__file__).resolve().parents[1] / "knowledge_base" / "assets"
        self.root_dir = Path(root_dir) if root_dir is not None else base
        self.candidates_dir = self.root_dir / "candidates"
        self.approved_dir = self.root_dir / "approved"
        self.reviews_dir = self.root_dir / "reviews"
        self.sources_dir = self.root_dir / "sources"
        self.indexes_dir = self.root_dir / "indexes"
        self.consumption_ledger_dir = self.root_dir / "consumption_ledger"
        self.settlement_events_dir = self.root_dir / "settlement_events"
        self._ensure_dirs()

    def submit_candidate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Store a candidate asset for later review."""

        source_type = str(data.get("source_type", "")).strip()
        asset_type = str(data.get("asset_type", "")).strip()
        if not source_type:
            raise ValueError("source_type is required")
        if source_type not in REVIEWABLE_SOURCE_TYPES:
            raise ValueError(f"unsupported source_type: {source_type}")
        if not asset_type:
            raise ValueError("asset_type is required")

        now = _utc_now()
        candidate = dict(data)
        candidate.setdefault("asset_id", self._generate_asset_id(candidate))
        candidate.setdefault("created_at", now)
        candidate["updated_at"] = now
        candidate["source_type"] = source_type
        candidate["asset_type"] = asset_type
        candidate["lifecycle_status"] = "needs_review"
        candidate.setdefault("maturity", "observed")
        candidate.setdefault("source_evidence_level", "E5_inference")
        candidate.setdefault("package_ids", [])
        candidate.setdefault("ontology_dimension_ids", [])
        candidate.setdefault("tags", [])
        candidate.setdefault("review_history", [])
        candidate["checksum"] = candidate.get("checksum") or self._checksum(candidate)

        self._write_json(self.candidates_dir / f"{candidate['asset_id']}.json", candidate)
        self._write_source_record(candidate)
        return candidate

    def list_candidates(
        self,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        asset_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        items = self._read_all_json(self.candidates_dir)
        if status:
            items = [item for item in items if item.get("lifecycle_status") == status]
        if source_type:
            items = [item for item in items if item.get("source_type") == source_type]
        if asset_type:
            items = [item for item in items if item.get("asset_type") == asset_type]
        return sorted(items, key=lambda item: item.get("created_at", ""))

    def get_candidate(self, asset_id: str) -> Dict[str, Any]:
        path = self.candidates_dir / f"{asset_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"candidate not found: {asset_id}")
        return self._read_json(path)

    def approve_candidate(
        self,
        asset_id: str,
        reviewer_id: str,
        reviewer_note: str = "",
        approved_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        candidate = self.get_candidate(asset_id)
        now = _utc_now()
        approved = dict(candidate)
        if approved_overrides:
            approved.update(approved_overrides)
        approved["lifecycle_status"] = "approved"
        approved["reviewer_id"] = reviewer_id
        approved["reviewer_note"] = reviewer_note
        approved["approved_at"] = now
        approved["updated_at"] = now
        approved["review_history"] = self._append_review(
            approved,
            action="approve",
            reviewer_id=reviewer_id,
            note=reviewer_note,
            timestamp=now,
        )

        self._write_json(self.approved_dir / f"{asset_id}.json", approved)
        self._write_json(self.candidates_dir / f"{asset_id}.json", approved)
        self._write_review_record(asset_id, approved["review_history"][-1])
        self._rebuild_approved_index()
        return approved

    def reject_candidate(
        self,
        asset_id: str,
        reviewer_id: str,
        reason: str = "",
    ) -> Dict[str, Any]:
        candidate = self.get_candidate(asset_id)
        now = _utc_now()
        rejected = dict(candidate)
        rejected["lifecycle_status"] = "rejected"
        rejected["reviewer_id"] = reviewer_id
        rejected["reviewer_note"] = reason
        rejected["rejected_at"] = now
        rejected["updated_at"] = now
        rejected["review_history"] = self._append_review(
            rejected,
            action="reject",
            reviewer_id=reviewer_id,
            note=reason,
            timestamp=now,
        )

        self._write_json(self.candidates_dir / f"{asset_id}.json", rejected)
        self._write_review_record(asset_id, rejected["review_history"][-1])
        approved_path = self.approved_dir / f"{asset_id}.json"
        if approved_path.exists():
            approved_path.unlink()
            self._rebuild_approved_index()
        return rejected

    def mark_needs_revision(
        self,
        asset_id: str,
        reviewer_id: str,
        reason: str = "",
    ) -> Dict[str, Any]:
        candidate = self.get_candidate(asset_id)
        now = _utc_now()
        candidate["lifecycle_status"] = "needs_revision"
        candidate["reviewer_id"] = reviewer_id
        candidate["reviewer_note"] = reason
        candidate["updated_at"] = now
        candidate["review_history"] = self._append_review(
            candidate,
            action="needs_revision",
            reviewer_id=reviewer_id,
            note=reason,
            timestamp=now,
        )
        self._write_json(self.candidates_dir / f"{asset_id}.json", candidate)
        self._write_review_record(asset_id, candidate["review_history"][-1])
        return candidate

    def find_approved_assets(
        self,
        package_ids: Optional[List[str]] = None,
        asset_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        assets = [
            item
            for item in self._read_all_json(self.approved_dir)
            if item.get("lifecycle_status") == "approved"
        ]
        if package_ids is not None:
            wanted = set(package_ids)
            assets = [
                item
                for item in assets
                if wanted.intersection(set(item.get("package_ids") or []))
            ]
        if asset_type is not None:
            assets = [item for item in assets if item.get("asset_type") == asset_type]
        if tags is not None:
            wanted_tags = set(tags)
            assets = [
                item for item in assets if wanted_tags.intersection(set(item.get("tags") or []))
            ]
        return sorted(assets, key=lambda item: item.get("approved_at", item.get("created_at", "")))

    def get_stats(self) -> Dict[str, int]:
        candidates = self._read_all_json(self.candidates_dir)
        approved = self.find_approved_assets()
        settlement_events = self._read_all_json(self.settlement_events_dir)
        consumption_events = self._read_all_json(self.consumption_ledger_dir)
        return {
            "total_candidates": len(candidates),
            "needs_review": sum(1 for item in candidates if item.get("lifecycle_status") == "needs_review"),
            "approved": len(approved),
            "rejected": sum(1 for item in candidates if item.get("lifecycle_status") == "rejected"),
            "needs_revision": sum(1 for item in candidates if item.get("lifecycle_status") == "needs_revision"),
            "consumption_events": len(consumption_events),
            "settlement_events": len(settlement_events),
            "settlement_promotion_candidates": sum(
                1 for item in candidates if item.get("source_type") == "internal_settlement"
            ),
        }

    def record_consumption_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Record which approved assets actually influenced an answer."""

        now = _utc_now()
        event = dict(data)
        event.setdefault("consumption_id", self._generate_record_id("CL", event))
        event.setdefault("created_at", now)
        event["updated_at"] = now
        event.setdefault("project_id", None)
        event.setdefault("session_id", None)
        event["consumed_asset_ids"] = list(event.get("consumed_asset_ids") or [])
        event["recalled_not_used_asset_ids"] = list(event.get("recalled_not_used_asset_ids") or [])
        event.setdefault("missing_slots", [])
        event.setdefault("ceiling_level", "unknown")
        event.setdefault("answer_trace", {})

        self._write_json(self.consumption_ledger_dir / f"{event['consumption_id']}.json", event)
        return event

    def list_consumption_events(
        self,
        project_id: Optional[str] = None,
        asset_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        items = self._read_all_json(self.consumption_ledger_dir)
        if project_id:
            items = [item for item in items if item.get("project_id") == project_id]
        if asset_id:
            items = [
                item for item in items
                if asset_id in (item.get("consumed_asset_ids") or [])
                or asset_id in (item.get("recalled_not_used_asset_ids") or [])
            ]
        return sorted(items, key=lambda item: item.get("created_at", ""))

    def submit_settlement_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store project feedback and optionally route valid self-learning signals to review.

        A feedback event never mutates approved assets directly. It can only create
        an internal_settlement candidate when attribution says the card itself is
        wrong or validated.
        """

        attribution = str(data.get("attribution", "")).strip()
        if not attribution:
            raise ValueError("attribution is required")
        if attribution not in SETTLEMENT_ATTRIBUTIONS:
            raise ValueError(f"unsupported attribution: {attribution}")

        consumption_id = str(data.get("consumption_id", "")).strip()
        if not consumption_id:
            raise ValueError("consumption_id is required")

        now = _utc_now()
        event = dict(data)
        event.setdefault("settlement_event_id", self._generate_record_id("SE", event))
        event.setdefault("created_at", now)
        event["updated_at"] = now
        event["consumption_id"] = consumption_id
        event["attribution"] = attribution
        event.setdefault("outcome", "needs_review")
        event.setdefault("evidence_strength", "L3_weak_feedback")
        event.setdefault("observation", "")
        event.setdefault("promotion_candidate_asset_id", None)

        promotion_payload = event.pop("promotion_candidate", None)
        self._write_json(
            self.settlement_events_dir / f"{event['settlement_event_id']}.json",
            event,
        )

        if promotion_payload and attribution in PROMOTION_ATTRIBUTIONS:
            candidate_data = dict(promotion_payload)
            candidate_data["source_type"] = "internal_settlement"
            candidate_data.setdefault("asset_type", "PromotionCandidate")
            candidate_data["related_consumption_id"] = event["consumption_id"]
            candidate_data["related_settlement_event_id"] = event["settlement_event_id"]
            candidate_data.setdefault("source_evidence_level", event.get("evidence_strength"))
            candidate_data.setdefault("provenance", {})
            candidate_data["provenance"] = {
                **(candidate_data.get("provenance") or {}),
                "settlement_event_id": event["settlement_event_id"],
                "consumption_id": event["consumption_id"],
                "attribution": attribution,
                "outcome": event.get("outcome"),
            }
            candidate = self.submit_candidate(candidate_data)
            event["promotion_candidate_asset_id"] = candidate["asset_id"]
            self._write_json(
                self.settlement_events_dir / f"{event['settlement_event_id']}.json",
                event,
            )

        return event

    def list_settlement_events(
        self,
        attribution: Optional[str] = None,
        outcome: Optional[str] = None,
        asset_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        items = self._read_all_json(self.settlement_events_dir)
        if attribution:
            items = [item for item in items if item.get("attribution") == attribution]
        if outcome:
            items = [item for item in items if item.get("outcome") == outcome]
        if asset_id:
            items = [item for item in items if item.get("asset_id") == asset_id]
        return sorted(items, key=lambda item: item.get("created_at", ""))

    def _ensure_dirs(self) -> None:
        for path in [
            self.candidates_dir,
            self.approved_dir,
            self.reviews_dir,
            self.sources_dir,
            self.indexes_dir,
            self.consumption_ledger_dir,
            self.settlement_events_dir,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def _generate_asset_id(self, data: Dict[str, Any]) -> str:
        digest = self._checksum(data)[:10].upper()
        return f"KA-{digest}"

    def _generate_record_id(self, prefix: str, data: Dict[str, Any]) -> str:
        digest = self._checksum(data)[:12].upper()
        return f"{prefix}-{digest}"

    def _checksum(self, data: Dict[str, Any]) -> str:
        safe = {
            key: value
            for key, value in data.items()
            if key
            not in {
                "checksum",
                "created_at",
                "updated_at",
                "review_history",
                "approved_at",
                "rejected_at",
            }
        }
        raw = json.dumps(safe, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _append_review(
        self,
        asset: Dict[str, Any],
        action: str,
        reviewer_id: str,
        note: str,
        timestamp: str,
    ) -> List[Dict[str, Any]]:
        history = list(asset.get("review_history") or [])
        history.append(
            {
                "action": action,
                "reviewer_id": reviewer_id,
                "reviewer_note": note,
                "reviewed_at": timestamp,
            }
        )
        return history

    def _write_review_record(self, asset_id: str, review: Dict[str, Any]) -> None:
        path = self.reviews_dir / f"{asset_id}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(review, ensure_ascii=False, sort_keys=True) + "\n")

    def _write_source_record(self, candidate: Dict[str, Any]) -> None:
        source = {
            "asset_id": candidate["asset_id"],
            "source_type": candidate.get("source_type"),
            "source_machine_id": candidate.get("source_machine_id"),
            "batch_id": candidate.get("batch_id"),
            "provenance": candidate.get("provenance", {}),
            "checksum": candidate.get("checksum"),
            "created_at": candidate.get("created_at"),
        }
        self._write_json(self.sources_dir / f"{candidate['asset_id']}.json", source)

    def _rebuild_approved_index(self) -> None:
        assets = self.find_approved_assets()
        index = {
            "updated_at": _utc_now(),
            "total": len(assets),
            "assets": [
                {
                    "asset_id": item.get("asset_id"),
                    "asset_type": item.get("asset_type"),
                    "title": item.get("title"),
                    "package_ids": item.get("package_ids", []),
                    "ontology_dimension_ids": item.get("ontology_dimension_ids", []),
                    "maturity": item.get("maturity"),
                    "source_evidence_level": item.get("source_evidence_level"),
                    "approved_at": item.get("approved_at"),
                }
                for item in assets
            ],
        }
        self._write_json(self.indexes_dir / "approved_index.json", index)

    def _read_all_json(self, directory: Path) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        if not directory.exists():
            return items
        for path in directory.glob("*.json"):
            items.append(self._read_json(path))
        return items

    def _read_json(self, path: Path) -> Dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


_service: Optional[KnowledgeAssetReviewService] = None


def get_knowledge_asset_review_service() -> KnowledgeAssetReviewService:
    global _service
    if _service is None:
        _service = KnowledgeAssetReviewService()
    return _service
