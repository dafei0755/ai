import subprocess
import sys

from scripts.check_scheme_advisor_golden_review_progress import build_default_args


def test_golden_review_progress_script_defaults_to_synced_p0_batch_and_fails_on_incomplete():
    args = build_default_args()

    assert "scheme-advisor-golden-review-batch-01-p0-synced-2026-03-22.csv" in args[
        args.index("--review-csv") + 1
    ]
    assert "scheme-advisor-golden-review-completion-2026-03-22.json" in args[
        args.index("--output") + 1
    ]
    assert "scheme-advisor-golden-review-completion-2026-03-22.md" in args[
        args.index("--markdown-output") + 1
    ]
    assert args[args.index("--required-gold-fields") + 1] == (
        "gold_expected_project_type,"
        "gold_expected_core_tension,"
        "gold_expected_output_depth"
    )
    assert "--fail-on-incomplete" in args


def test_golden_review_progress_script_runs_from_file_path():
    result = subprocess.run(
        [sys.executable, "scripts/check_scheme_advisor_golden_review_progress.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode in {0, 1}
    assert "ModuleNotFoundError" not in result.stderr
    assert "incomplete_rows" in result.stdout
    assert "docs/system-completeness-audit/scheme-advisor-golden-review-completion-2026-03-22.md" in result.stdout
