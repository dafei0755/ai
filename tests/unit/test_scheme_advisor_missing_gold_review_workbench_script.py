from scripts.build_scheme_advisor_missing_gold_review_workbench import build_default_args


def test_missing_gold_review_workbench_script_defaults_to_quality_gate_and_workbench():
    args = build_default_args()

    assert "scheme-advisor-golden-quality-gate-2026-03-22.json" in args[
        args.index("--quality-gate") + 1
    ]
    assert "scheme-advisor-golden-review-workbench-2026-03-22.json" in args[
        args.index("--review-workbench") + 1
    ]
    assert "scheme-advisor-missing-gold-review-workbench-2026-03-22.json" in args[
        args.index("--output-json") + 1
    ]
    assert "scheme-advisor-missing-gold-review-workbench-2026-03-22.csv" in args[
        args.index("--output-csv") + 1
    ]
    assert "scheme-advisor-missing-gold-review-workbench-2026-03-22.md" in args[
        args.index("--output-md") + 1
    ]
