# -*- coding: utf-8 -*-
"""Plan Sandbox layout generation routes.

These routes expose the first executable version of the bidirectional floor-plan
compiler: SPG + FloorPlanFacts in, strategy-different LayoutVariant objects out.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from intelligent_project_analyzer.core.domain_objects import (
    FloorPlanFacts,
    LayoutGenerationPackage,
    SpatialProgramGraph,
)
from intelligent_project_analyzer.services.floor_plan_layout_engine import (
    generate_layout_variants,
)


router = APIRouter(prefix="/api/v1/floor-plan", tags=["平面推演"])


class LayoutVariantRequest(BaseModel):
    """Generate layout variants from project program and optional plan facts."""

    session_id: str = Field(default="")
    spg: SpatialProgramGraph
    facts: Optional[FloorPlanFacts] = None
    variant_count: int = Field(default=3, ge=1, le=3)


@router.post("/generate-variants", response_model=LayoutGenerationPackage)
async def generate_floor_plan_variants(request: LayoutVariantRequest) -> LayoutGenerationPackage:
    """Generate strategy-different layout variants for Plan Sandbox.

    This endpoint is intentionally deterministic in Phase 0. LLM reasoning can
    consume the returned package to explain differences, parse user commands,
    and trigger later local regeneration.
    """

    return generate_layout_variants(
        spg=request.spg,
        facts=request.facts,
        session_id=request.session_id,
        variant_count=request.variant_count,
    )
