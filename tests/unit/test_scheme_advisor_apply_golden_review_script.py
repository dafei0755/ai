import subprocess
import sys

from scripts.apply_scheme_advisor_golden_review import build_default_args


def test_apply_golden_review_script_defaults_to_p0_review_csv_and_updated_copy():
    args = build_default_args()

    assert "scheme-advisor-190-golden-annotation-base-2026-03-22.json" in args[
        args.index("--golden") + 1
    ]
    assert "scheme-advisor-golden-review-batch-01-p0-synced-2026-03-22.csv" in args[
        args.index("--review-csv") + 1
    ]
    assert "scheme-advisor-190-golden-annotation-updated-2026-03-22.json" in args[
        args.index("--updated-golden-output") + 1
    ]
    assert "scheme-advisor-golden-review-apply-report-2026-03-22.json" in args[
        args.index("--apply-report-output") + 1
    ]


def test_apply_golden_review_script_runs_from_file_path_without_overwriting_base():
    result = subprocess.run(
        [sys.executable, "scripts/apply_scheme_advisor_golden_review.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0
    assert "ModuleNotFoundError" not in result.stderr
    assert "updated_fields" in result.stdout
    assert "updated_golden_output" in result.stdout
