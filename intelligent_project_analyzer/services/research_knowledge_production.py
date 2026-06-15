"""Bridge structured research reports into governed knowledge asset drafts."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

from ..models.research_scan import ClaimVerificationStatus, ResearchReport, ScanTask, TrustTier
from .knowledge_asset_draft_generation import _base_draft


def _source_urls(report: ResearchReport) -> List[str]:
    urls: List[str] = []
    for source in report.sources:
        url = str(source.url)
        if url not in urls:
            urls.append(url)
    return urls


def _research_source_key(report: ResearchReport, scan_task: Optional[ScanTask]) -> str:
    topic = scan_task.topic if scan_task else report.summary[:80]
    digest_input = "|".join([topic, report.summary, *(_source_urls(report))])
    digest = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:16]
    return f"research_report:{topic}:{digest}"


def _evidence_strength(report: ResearchReport) -> str:
    has_t1_source = any(source.trust_tier == TrustTier.T1 for source in report.sources)
    verified_claims = [
        item for item in report.verification if item.status == ClaimVerificationStatus.verified
    ]
    if has_t1_source and len(verified_claims) >= 2:
        return "strong"
    if has_t1_source and verified_claims:
        return "moderate"
    if verified_claims:
        return "weak_to_moderate"
    return "weak"


def _report_to_markdown(report: ResearchReport, scan_task: Optional[ScanTask]) -> str:
    lines = []
    if scan_task:
        lines.extend([f"# {scan_task.topic}", ""])
    lines.extend(["## Summary", report.summary, ""])
    if report.findings:
        lines.append("## Findings")
        lines.extend(f"- {item}" for item in report.findings)
        lines.append("")
    if report.sources:
        lines.append("## Sources")
        for index, source in enumerate(report.sources, start=1):
            lines.append(
                f"- S{index}: {source.title} | {source.publisher} | {source.published_at} | "
                f"{source.trust_tier.value}/{source.evidence_type.value} | {source.url}"
            )
        lines.append("")
    if report.verification:
        lines.append("## Claim Verification")
        for item in report.verification:
            urls = ", ".join(str(url) for url in item.supporting_urls)
            lines.append(f"- {item.status.value}: {item.claim} ({urls})")
        lines.append("")
    if report.open_questions:
        lines.append("## Open Questions")
        lines.extend(f"- {item}" for item in report.open_questions)
        lines.append("")
    return "\n".join(lines).strip()


def generate_asset_draft_from_research_report(
    report: ResearchReport,
    *,
    scan_task: Optional[ScanTask] = None,
) -> Dict[str, Any]:
    """Convert a structured research report into a manual-review AssetDraft.

    Research output is candidate evidence only. This function deliberately does
    not approve cards or update runtime recall indexes.
    """
    topic = scan_task.topic if scan_task else "Research report"
    body_markdown = _report_to_markdown(report, scan_task)
    source_urls = _source_urls(report)
    limitations = [
        "Research report is candidate evidence only and requires manual review before approval.",
        "Source rights, transferability, and domain binding must be checked before runtime recall.",
    ]
    if report.open_questions:
        limitations.extend(report.open_questions)

    draft = _base_draft(
        source_key=_research_source_key(report, scan_task),
        source_ref={
            "source_type": "research_report",
            "topic": topic,
            "review_gate": "asset_draft_manual_review",
        },
        title=topic,
        summary=report.summary,
        body_markdown=body_markdown,
        evidence_map={
            "source_observations": [],
            "local_source_paths": [],
            "source_urls": source_urls,
            "cleaning_reports": [],
            "evidence_strength": _evidence_strength(report),
            "limitations": limitations,
        },
    )
    draft["metadata_candidate"]["asset_type"] = "ResearchFinding"
    draft["generation_notes"].append(
        "Generated from ResearchReport; manual review is required before approved knowledge card creation."
    )
    return draft
