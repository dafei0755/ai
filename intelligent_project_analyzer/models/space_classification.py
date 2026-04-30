from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SecondaryCandidate(BaseModel):
    project_type: str
    confidence: float
    role: Literal[
        "supporting_function", "competing_primary", "seasonal_variant", "unknown"
    ] = "unknown"
    weight: Optional[float] = None
    weight_status: Literal["known", "unknown"] = "unknown"


class AmbiguityInfo(BaseModel):
    level: Literal["low", "medium", "high"]
    boundary_risk: bool = False
    competing_types: List[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_questions: List[str] = Field(default_factory=list)


class RoutingInfo(BaseModel):
    questionnaire_profile: str
    ontology_key: str
    deliverable_label: Optional[str] = None
    floorplan_profile: Optional[str] = None
    visual_profile: Optional[str] = None


class SpaceClassificationResult(BaseModel):
    schema_version: str = "space_classification.v1"
    primary_bucket: Optional[str] = None
    project_type: str
    project_type_name: Optional[str] = None
    confidence: float
    confidence_level: Literal["high", "medium", "low"]
    specialty_tags: List[str] = Field(default_factory=list)
    secondary_candidates: List[SecondaryCandidate] = Field(default_factory=list)
    runtime_modifiers: Dict[str, Any] = Field(default_factory=dict)
    ambiguity: AmbiguityInfo
    routing: RoutingInfo
    evidence: List[str] = Field(default_factory=list)
    spatial_zone_refs: List[str] = Field(default_factory=list)
    freeze_state: Literal["open", "user_confirmed", "system_locked"] = "open"
