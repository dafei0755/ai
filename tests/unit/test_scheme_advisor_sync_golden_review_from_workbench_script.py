from scripts.sync_scheme_advisor_golden_review_from_workbench import build_default_args


def test_sync_golden_review_from_workbench_defaults_to_safe_output_copy():
    args = build_default_args()

    assert "scheme-advisor-golden-review-batch-01-p0-2026-03-22.csv" in args[
        args.index("--review-csv") + 1
    ]
    assert "scheme-advisor-missing-gold-review-workbench-2026-03-22.csv" in args[
        args.index("--workbench-csv") + 1
    ]
    assert "scheme-advisor-golden-review-batch-01-p0-synced-2026-03-22.csv" in args[
        args.index("--output-csv") + 1
    ]
    assert "scheme-advisor-golden-review-workbench-sync-report-2026-03-22.json" in args[
        args.index("--report-output") + 1
    ]
