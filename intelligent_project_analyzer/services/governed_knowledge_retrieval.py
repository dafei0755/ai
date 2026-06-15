"""Governed retrieval service for approved knowledge cards."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .knowledge_asset_registry import KnowledgeAssetRegistry
from .knowledge_asset_runtime import resolve_governed_knowledge_cards
from .knowledge_fabric_graph import KnowledgeFabricGraph
from .knowledge_fabric_models import GovernedRetrievalResult
from .retrieval_planner import RetrievalPlanner


class GovernedKnowledgeRetrievalService:
    """Return approved cards plus graph context and an auditable trace."""

    def __init__(
        self,
        planner: Optional[RetrievalPlanner] = None,
        graph: Optional[KnowledgeFabricGraph] = None,
        asset_registry: Optional[KnowledgeAssetRegistry] = None,
    ) -> None:
        self.planner = planner or RetrievalPlanner()
        self.graph = graph or KnowledgeFabricGraph()
        self.asset_registry = asset_registry or KnowledgeAssetRegistry()

    def retrieve(
        self,
        context_packet: Dict[str, Any],
        intended_use: Optional[str] = None,
        min_evidence_level: Optional[str] = None,
    ) -> GovernedRetrievalResult:
        plan = self.planner.plan(context_packet)
        filters = dict(plan.filters)
        if intended_use is not None:
            filters["intended_use"] = intended_use
        if min_evidence_level is not None:
            filters["min_evidence_level"] = min_evidence_level

        graph_context = {"nodes": [], "edges": []}
        graph_step = next((step for step in plan.steps if step.action == "graph_expansion"), None)
        if graph_step:
            graph_context = self.graph.expand(graph_step.seed_ids, max_hops=graph_step.max_hops or 2)

        cards = resolve_governed_knowledge_cards(
            package_ids=filters.get("package_ids") or [],
            ontology_dimension_ids=filters.get("ontology_dimension_ids") or [],
            intended_use=str(filters.get("intended_use") or "theme_generation"),
            min_evidence_level=str(filters.get("min_evidence_level") or "weak_evidence"),
            registry=self.asset_registry,
        )
        retrieval_trace = self._trace(plan, filters, graph_context, cards)
        return GovernedRetrievalResult(
            cards=cards,
            graph_context=graph_context,
            retrieval_trace=retrieval_trace,
            policy=plan.policy,
        )

    def _trace(
        self,
        plan: Any,
        filters: Dict[str, Any],
        graph_context: Dict[str, Any],
        cards: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        trace: List[Dict[str, Any]] = []
        for step in plan.steps:
            item = {
                "step_id": step.step_id,
                "action": step.action,
                "seed_ids": step.seed_ids,
                "filters": filters,
            }
            if step.action == "graph_expansion":
                item["max_hops"] = step.max_hops
                item["node_count"] = len(graph_context.get("nodes") or [])
                item["edge_count"] = len(graph_context.get("edges") or [])
            if step.action == "approved_card_lookup":
                item["approved_card_count"] = len(cards)
                item["approved_only"] = True
            trace.append(item)
        return trace
