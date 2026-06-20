"""Governance integration for demand reconstruction."""

from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, Optional

from loguru import logger


class DemandReconstructionGovernance:
    """Apply governed knowledge cards and persist review signals."""

    def __init__(self, *, governance_store: Any = None) -> None:
        self._governance_store = governance_store

    def persist_governance_signals(
        self,
        *,
        session: Dict[str, Any],
        source_message: str,
        blueprint: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if self._governance_store is None:
            return None
        signals = [signal for signal in (blueprint.get("governance_signals") or []) if isinstance(signal, dict)]
        if not signals:
            return None

        scope = self.governance_scope(session)
        digest = uuid.uuid5(uuid.NAMESPACE_URL, str(source_message or "")).hex[:12]
        queued_item_ids: list[str] = []
        failed: list[Dict[str, Any]] = []
        for signal in signals:
            code = str(signal.get("code") or "governance_signal").strip()
            review_queue = str(signal.get("review_queue") or "manual_governance_triage").strip()
            object_id = f"{code}:{digest}"
            try:
                item = self._governance_store.enqueue_review_item(
                    tenant_id=scope["tenant_id"],
                    workspace_id=scope["workspace_id"],
                    user_id=scope["user_id"],
                    module="demand_reconstruction",
                    object_type="governance_signal",
                    object_id=object_id,
                    title=str(signal.get("meaning") or signal.get("message") or code),
                    source=str(signal.get("source") or "demand_reconstruction"),
                    risk=str(signal.get("severity") or signal.get("risk") or "P2"),
                    target_admin_path=f"/admin/review-queue?queue={review_queue}",
                    metadata={
                        "code": code,
                        "review_queue": review_queue,
                        "source_message_digest": digest,
                        "signal": signal,
                    },
                    created_by=scope["created_by"],
                )
                queued_item_ids.append(str(item.get("id") or f"demand_reconstruction:{object_id}"))
            except Exception as exc:  # governance persistence must not break user output
                logger.warning(
                    "[DemandReconstruction] governance signal persistence failed: "
                    f"code={code}, error_type={type(exc).__name__}, error={exc}"
                )
                failed.append({"code": code, "error": str(exc), "error_type": type(exc).__name__})

        if queued_item_ids:
            status = "queued_for_review" if not failed else "partial"
        else:
            status = "failed"
        return {
            "status": status,
            "queued_count": len(queued_item_ids),
            "item_ids": queued_item_ids,
            "failed": failed,
        }

    def apply_governed_knowledge_assets(
        self,
        *,
        adapter_context: Dict[str, Any],
        session: Dict[str, Any],
        source_message: str,
        refresh_asset_scan: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        if self._governance_store is None:
            return
        try:
            scope = self.governance_scope(session)
            cards = self._governance_store.find_approved_cards(
                tenant_id=scope["tenant_id"],
                workspace_id=scope["workspace_id"],
                user_id=scope["user_id"],
            )
        except Exception as exc:
            logger.warning(
                "[DemandReconstruction] governed knowledge asset scan failed: "
                f"error_type={type(exc).__name__}, error={exc}"
            )
            return
        terms = self.governed_knowledge_match_terms(adapter_context, source_message)
        scored_matches: list[tuple[int, Dict[str, Any]]] = []
        for card in cards:
            match_metadata = self.approved_card_match_metadata(card, terms)
            if match_metadata["decision"] == "accepted":
                scored_matches.append(
                    (
                        int(match_metadata["score"]),
                        self.compact_governed_knowledge_asset(card, match_metadata=match_metadata),
                    )
                )
        if not scored_matches:
            return
        scored_matches.sort(key=lambda item: item[0], reverse=True)
        adapter_context["governed_knowledge_assets"] = [item[1] for item in scored_matches[:3]]
        context_source = dict(adapter_context.get("context_source") or {})
        context_source["governed_knowledge_assets"] = True
        adapter_context["context_source"] = context_source
        if refresh_asset_scan is not None:
            refresh_asset_scan(adapter_context)

    @staticmethod
    def governed_knowledge_match_terms(adapter_context: Dict[str, Any], source_message: str) -> list[str]:
        terms: list[str] = []

        def add(value: Any) -> None:
            text = str(value or "").strip()
            if len(text) >= 2 and text not in terms:
                terms.append(text)

        add(source_message)
        package = adapter_context.get("llm_semantic_understanding")
        if isinstance(package, dict):
            add(package.get("project_object"))
            for item in package.get("recommended_scan_targets") or []:
                add(item)
            for candidate in package.get("space_candidates") or []:
                if isinstance(candidate, dict):
                    add(candidate.get("label"))
                    for evidence in candidate.get("evidence") or []:
                        add(evidence)
            for tension in package.get("core_tensions") or []:
                if isinstance(tension, dict):
                    add(tension.get("title"))
                    for evidence in tension.get("evidence") or []:
                        add(evidence)
        for item in adapter_context.get("semantic_candidate_set") or []:
            if isinstance(item, dict):
                add(item.get("id"))
                add(item.get("label"))
        return terms

    @staticmethod
    def approved_card_matches_terms(card: Dict[str, Any], terms: list[str]) -> bool:
        return DemandReconstructionGovernance.approved_card_match_metadata(card, terms)["decision"] == "accepted"

    @staticmethod
    def approved_card_match_metadata(card: Dict[str, Any], terms: list[str]) -> Dict[str, Any]:
        normalized_terms = [str(term or "").strip().lower() for term in terms if str(term or "").strip()]

        def list_values(key: str) -> list[str]:
            return [str(item or "").strip() for item in card.get(key) or [] if str(item or "").strip()]

        def hits(values: list[str]) -> list[str]:
            matched: list[str] = []
            for value in values:
                normalized_value = value.lower()
                if any(normalized_value and (normalized_value in term or term in normalized_value) for term in normalized_terms):
                    matched.append(value)
            return matched

        package_ids = list_values("package_ids")
        dimension_ids = list_values("ontology_dimension_ids")
        package_hits = hits(package_ids)
        dimension_hits = hits(dimension_ids)
        searchable = " ".join(
            str(value)
            for value in (
                card.get("card_id"),
                card.get("title"),
                card.get("project_type"),
                card.get("summary"),
                card.get("source_gap_type"),
                " ".join(str(item) for item in card.get("evidence") or []),
            )
            if value
        ).lower()
        text_match = any(term and (term in searchable or searchable in term) for term in normalized_terms)
        evidence_level = str(card.get("evidence_level") or "").strip()
        strong_evidence_levels = {
            "expert_review",
            "approved_review",
            "approved_card",
            "e2_research",
            "e3_case",
            "case_evidence",
            "research_report",
            "validated_asset",
        }
        evidence_strong = evidence_level.lower() in strong_evidence_levels
        score = 0
        if text_match:
            score += 1
        score += len(package_hits) * 3
        score += len(dimension_hits) * 3
        if evidence_strong:
            score += 2
        decision = "accepted" if text_match and (package_hits or dimension_hits or evidence_strong) else "rejected"
        return {
            "decision": decision,
            "score": score,
            "text_match": text_match,
            "package_hits": package_hits,
            "dimension_hits": dimension_hits,
            "evidence_level": evidence_level,
            "evidence_strong": evidence_strong,
        }

    @staticmethod
    def compact_governed_knowledge_asset(
        card: Dict[str, Any],
        *,
        match_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "card_id": card.get("card_id"),
            "title": card.get("title"),
            "project_type": card.get("project_type"),
            "summary": card.get("summary"),
            "evidence": list(card.get("evidence") or [])[:5],
            "package_ids": list(card.get("package_ids") or [])[:5],
            "ontology_dimension_ids": list(card.get("ontology_dimension_ids") or [])[:5],
            "allowed_use": list(card.get("allowed_use") or [])[:5],
            "not_allowed_use": list(card.get("not_allowed_use") or [])[:5],
            "evidence_level": card.get("evidence_level"),
            "match_metadata": dict(match_metadata or {}),
            "source": "approved_governance_knowledge_card",
        }

    @staticmethod
    def governance_scope(session: Dict[str, Any]) -> Dict[str, str]:
        user = session.get("user") if isinstance(session.get("user"), dict) else {}
        user_id = (
            session.get("user_id")
            or session.get("userId")
            or user.get("id")
            or user.get("username")
            or "runtime"
        )
        return {
            "tenant_id": str(session.get("tenant_id") or session.get("tenantId") or "default"),
            "workspace_id": str(session.get("workspace_id") or session.get("workspaceId") or "default"),
            "user_id": str(user_id),
            "created_by": str(session.get("created_by") or user_id or "runtime"),
        }
