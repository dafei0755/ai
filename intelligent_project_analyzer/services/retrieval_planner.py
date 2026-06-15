"""Plan governed knowledge retrieval from context packets."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from .knowledge_fabric_models import KnowledgeGraphStep, RetrievalPlan


class RetrievalPlanner:
    """Convert a v3.3 context packet into policy-bound retrieval steps."""

    def plan(self, context_packet: Dict[str, Any]) -> RetrievalPlan:
        packet = context_packet or {}
        knowledge_binding = packet.get("knowledge_binding") or {}
        ontology_binding = packet.get("ontology_binding") or {}
        coordination = packet.get("activation_pack_coordination") or {}

        package_ids = self._unique_strings(
            list(knowledge_binding.get("knowledge_package_ids") or [])
            + list(knowledge_binding.get("package_ids") or [])
            + list(knowledge_binding.get("knowledge_packages") or [])
        )
        ontology_dimension_ids = self._unique_strings(ontology_binding.get("ontology_dimension_ids") or [])
        activation_pack_ids = self._unique_strings(
            [ontology_binding.get("activation_pack_id")]
            + list(ontology_binding.get("secondary_activation_pack_ids") or [])
            + list(coordination.get("loaded_pack_ids") or [])
            + [item.get("pack_id") for item in coordination.get("secondary_packs") or [] if isinstance(item, dict)]
        )
        approved_card_ids = self._unique_strings(
            [
                card.get("card_id")
                for card in knowledge_binding.get("approved_knowledge_cards") or []
                if isinstance(card, dict)
            ]
        )
        seed_ids = self._unique_strings(package_ids + activation_pack_ids + ontology_dimension_ids + approved_card_ids)
        filters = {
            "package_ids": package_ids,
            "ontology_dimension_ids": ontology_dimension_ids,
            "intended_use": "theme_generation",
            "min_evidence_level": "weak_evidence",
        }
        policy = {
            "approved_only": True,
            "human_review_required_for_candidates": True,
        }

        steps = [
            KnowledgeGraphStep(
                step_id="seed_context",
                action="seed_context",
                seed_ids=seed_ids,
                filters=filters,
            )
        ]
        if self._requires_graph_expansion(packet):
            steps.append(
                KnowledgeGraphStep(
                    step_id="graph_expansion",
                    action="graph_expansion",
                    seed_ids=seed_ids,
                    max_hops=2,
                    filters=filters,
                )
            )
        steps.append(
            KnowledgeGraphStep(
                step_id="approved_card_lookup",
                action="approved_card_lookup",
                seed_ids=seed_ids,
                filters=filters,
            )
        )

        return RetrievalPlan(
            seed_ids=seed_ids,
            steps=steps,
            filters=filters,
            policy=policy,
            metadata={
                "source_schema_version": packet.get("schema_version"),
                "classification_project_type_id": (packet.get("classification") or {}).get("project_type_id"),
            },
        )

    def _requires_graph_expansion(self, packet: Dict[str, Any]) -> bool:
        coordination = packet.get("activation_pack_coordination") or {}
        ontology_binding = packet.get("ontology_binding") or {}
        classification = packet.get("classification") or {}
        subdomain = classification.get("subdomain") or {}
        mode = str(coordination.get("mode") or "")
        return any(
            [
                "composite" in mode,
                bool(ontology_binding.get("secondary_activation_pack_ids")),
                len(coordination.get("secondary_packs") or []) > 0,
                len(subdomain.get("complement_roles") or []) > 1,
            ]
        )

    @staticmethod
    def _unique_strings(items: Iterable[Any]) -> List[str]:
        seen = set()
        result = []
        for item in items or []:
            if item is None:
                continue
            text = str(item).strip()
            if text and text not in seen:
                seen.add(text)
                result.append(text)
        return result
