"""Unified latent-variable contract for demand reconstruction.

The model is intentionally small and explicit: every inferred variable must be
traceable to evidence so downstream planners can use psychological or symbolic
signals without turning them into unconstrained storytelling.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, model_validator


class EvidenceItem(BaseModel):
    """A source-bound evidence fragment used by latent variables."""

    evidence_id: str
    excerpt: str
    source_span: Dict[str, int] = Field(default_factory=dict)
    evidence_type: Literal["explicit", "derived", "contextual"] = "explicit"
    reliability: Literal["high", "medium", "low"] = "medium"


class LatentVariableItem(BaseModel):
    """One latent variable with evidence and uncertainty metadata."""

    id: str
    label: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_refs: List[str] = Field(default_factory=list)
    source: Literal["explicit", "inferred", "derived", "llm"] = "inferred"
    status: Literal["observed", "hypothesis", "unknown"] = "hypothesis"


class LatentModel(BaseModel):
    """Canonical contract shared by adapters, evaluators, and planners."""

    schema_version: str = "latent_model.v1"
    mode: Literal["project_reconstruction", "methodology", "unknown"] = "project_reconstruction"
    input_frame: Dict[str, Any] = Field(default_factory=dict)
    latent_variables: Dict[str, List[LatentVariableItem]] = Field(default_factory=dict)
    tensions: List[Dict[str, Any]] = Field(default_factory=list)
    hypotheses: List[Dict[str, Any]] = Field(default_factory=list)
    uncertainty_ledger: List[Dict[str, Any]] = Field(default_factory=list)
    decision_frontier: Dict[str, Any] = Field(default_factory=dict)
    evidence_index: List[EvidenceItem] = Field(default_factory=list)
    quality_gate: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
    person_profile: List[Dict[str, Any]] = Field(default_factory=list)
    existential_job: Dict[str, Any] = Field(default_factory=dict)
    evidence_bound_affect: List[Dict[str, Any]] = Field(default_factory=list)
    forbidden_capture_paths: List[Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_inferred_variables_are_evidence_bound(self) -> "LatentModel":
        evidence_ids = {item.evidence_id for item in self.evidence_index}
        missing_refs: List[str] = []
        unknown_refs: List[str] = []
        for group, items in self.latent_variables.items():
            for item in items:
                if item.source in {"inferred", "derived", "llm"} and not item.evidence_refs:
                    missing_refs.append(f"{group}.{item.id}")
                for ref in item.evidence_refs:
                    if ref not in evidence_ids:
                        unknown_refs.append(f"{group}.{item.id}:{ref}")
        if missing_refs:
            raise ValueError("inferred latent variables require evidence_refs: " + ", ".join(missing_refs))
        if unknown_refs:
            raise ValueError("latent variable evidence_refs must exist in evidence_index: " + ", ".join(unknown_refs))
        return self
