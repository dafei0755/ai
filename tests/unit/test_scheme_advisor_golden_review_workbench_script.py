from scripts.build_scheme_advisor_golden_review_workbench import build_default_args


def test_golden_review_workbench_script_defaults_to_p0_batch_and_suggestions():
    args = build_default_args()

    assert "scheme-advisor-golden-review-batch-01-p0-2026-03-22.json" in args[
        args.index("--review-batch") + 1
    ]
    assert "scheme-advisor-golden-review-batch-01-p0-suggestions-2026-03-22.json" in args[
        args.index("--suggestions") + 1
    ]
    assert "scheme-advisor-golden-review-workbench-2026-03-22.json" in args[
        args.index("--output-json") + 1
    ]
    assert "scheme-advisor-golden-review-workbench-2026-03-22.csv" in args[
        args.index("--output-csv") + 1
    ]
    assert "scheme-advisor-golden-review-workbench-2026-03-22.md" in args[
        args.index("--output-md") + 1
    ]
