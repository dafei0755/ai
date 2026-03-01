from intelligent_project_analyzer.models.research_scan import (
    ClaimVerification,
    ClaimVerificationStatus,
    ComparisonRow,
    EvidenceType,
    ResearchReport,
    ScanTask,
    SourceItem,
    TrustTier,
)


def test_scan_task_defaults():
    task = ScanTask(topic="  低空经济政策跟踪  ")

    assert task.topic == "低空经济政策跟踪"
    assert task.time_window == "不限"
    assert task.max_depth_per_site == 2
    assert "中文" in task.languages


def test_source_item_and_report_schema():
    source = SourceItem(
        title="FAA Rule Update",
        url="https://www.faa.gov/newsroom/example",
        publisher="FAA",
        published_at="2026-02-20",
        trust_tier=TrustTier.T1,
        evidence_type=EvidenceType.primary,
        key_claims=["Rule timeline updated"],
    )

    row = ComparisonRow(
        claim="Rule timeline updated",
        source_title=source.title,
        source_url=source.url,
        position="Confirms effective date in 2026",
    )

    verification = ClaimVerification(
        claim="Rule timeline updated",
        status=ClaimVerificationStatus.verified,
        supporting_urls=[source.url],
    )

    report = ResearchReport(
        summary="FAA and secondary media are aligned on timeline.",
        findings=["Timeline confirmed by two sources"],
        comparison_table=[row],
        sources=[source],
        verification=[verification],
        open_questions=["Whether regional exceptions exist"],
    )

    assert report.summary.startswith("FAA")
    assert report.sources[0].trust_tier == TrustTier.T1
    assert report.verification[0].status == ClaimVerificationStatus.verified
