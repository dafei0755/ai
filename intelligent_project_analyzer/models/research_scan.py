"""
Research scan models for theme-based website scanning and reporting.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class TrustTier(str, Enum):
    """Source trust level."""

    T1 = "T1"
    T2 = "T2"
    T3 = "T3"


class EvidenceType(str, Enum):
    """Primary vs secondary evidence."""

    primary = "primary"
    secondary = "secondary"


class ClaimVerificationStatus(str, Enum):
    """Verification status for a normalized claim."""

    verified = "verified"
    pending = "pending"
    conflict = "conflict"


class ScanTask(BaseModel):
    """Input contract for two-phase website scan."""

    topic: str = Field(..., min_length=1, description="Research topic")
    time_window: str = Field(default="不限", description="e.g. 近7天 / 近30天 / 不限")
    seed_sites: List[str] = Field(default_factory=list, description="Priority sites for deep-dive")
    languages: List[str] = Field(default_factory=lambda: ["中文"], description="Language scope")
    max_depth_per_site: int = Field(default=2, ge=0, le=5, description="Max crawl depth per deep-dive site")
    exclusions: List[str] = Field(
        default_factory=lambda: ["论坛", "广告站", "低可信聚合站"],
        description="Filters to exclude noisy sources",
    )

    @field_validator("topic")
    @classmethod
    def strip_topic(cls, value: str) -> str:
        return value.strip()

    @field_validator("seed_sites", mode="before")
    @classmethod
    def default_seed_sites(cls, value: Optional[List[str]]) -> List[str]:
        if value is None:
            return []
        return value

    @model_validator(mode="after")
    def validate_topic_not_empty(self) -> "ScanTask":
        if not self.topic:
            raise ValueError("topic cannot be empty after trimming")
        return self


class SourceItem(BaseModel):
    """Normalized source record."""

    title: str = Field(..., min_length=1)
    url: HttpUrl
    publisher: str = Field(..., min_length=1)
    published_at: str = Field(..., description="Absolute date/time string, e.g. 2026-02-25")
    captured_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When this source was captured",
    )
    trust_tier: TrustTier = Field(default=TrustTier.T2)
    evidence_type: EvidenceType = Field(default=EvidenceType.secondary)
    key_claims: List[str] = Field(default_factory=list)

    @field_validator("title", "publisher", "published_at")
    @classmethod
    def required_text_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("text fields cannot be blank")
        return cleaned


class ClaimVerification(BaseModel):
    """Claim-level verification entry."""

    claim: str = Field(..., min_length=1)
    status: ClaimVerificationStatus
    supporting_urls: List[HttpUrl] = Field(default_factory=list)
    note: Optional[str] = None


class ComparisonRow(BaseModel):
    """Row in claim/source comparison table."""

    claim: str = Field(..., min_length=1)
    source_title: str = Field(..., min_length=1)
    source_url: HttpUrl
    position: str = Field(..., min_length=1, description="Source stance or extracted position")


class ResearchReport(BaseModel):
    """Output contract for structured markdown-compatible report."""

    summary: str = Field(..., min_length=1)
    findings: List[str] = Field(default_factory=list)
    comparison_table: List[ComparisonRow] = Field(default_factory=list)
    sources: List[SourceItem] = Field(default_factory=list)
    verification: List[ClaimVerification] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_summary(self) -> "ResearchReport":
        self.summary = self.summary.strip()
        if not self.summary:
            raise ValueError("summary cannot be blank")
        return self
