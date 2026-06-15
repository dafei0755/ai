"""Pydantic contracts for governed knowledge-fabric retrieval."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class KnowledgeFabricNode(BaseModel):
    """A typed node in the governed knowledge network."""

    id: str
    node_type: str
    title: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeFabricEdge(BaseModel):
    """A directed relationship between knowledge-fabric nodes."""

    source_id: str
    target_id: str
    relation: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphStep(BaseModel):
    """One executable step in a governed retrieval plan."""

    step_id: str
    action: str
    seed_ids: List[str] = Field(default_factory=list)
    max_hops: Optional[int] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalPlan(BaseModel):
    """A policy-bound plan derived from a context packet."""

    seed_ids: List[str] = Field(default_factory=list)
    steps: List[KnowledgeGraphStep] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    policy: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GovernedRetrievalResult(BaseModel):
    """Approved-card retrieval output with graph context and audit trace."""

    cards: List[Dict[str, Any]] = Field(default_factory=list)
    graph_context: Dict[str, Any] = Field(default_factory=lambda: {"nodes": [], "edges": []})
    retrieval_trace: List[Dict[str, Any]] = Field(default_factory=list)
    policy: Dict[str, Any] = Field(default_factory=dict)
