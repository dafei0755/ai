import json
import subprocess
import sys

from scripts.run_scheme_advisor_golden_quality_gate import build_default_args


def test_golden_quality_gate_script_uses_p0_review_batch_and_fails_on_gate():
    args = build_default_args()

    assert "scheme-advisor-190-golden-annotation-updated-2026-03-22.json" in args[
        args.index("--golden") + 1
    ]
    assert "--required-review-batch" in args
    assert "scheme-advisor-golden-review-batch-01-p0-2026-03-22.json" in args[
        args.index("--required-review-batch") + 1
    ]
    assert args[args.index("--required-review-priority") + 1] == "P0"
    assert args[args.index("--required-gold-fields") + 1] == (
        "gold_expected_project_type,"
        "gold_expected_core_tension,"
        "gold_expected_output_depth"
    )
    assert "--fail-on-quality-gate" in args


def test_golden_quality_gate_script_runs_from_file_path():
    result = subprocess.run(
        [sys.executable, "scripts/run_scheme_advisor_golden_quality_gate.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode in {0, 1}
    assert "ModuleNotFoundError" not in result.stderr
    assert "quality_gate_status" in result.stdout
    lines = [
        json.loads(line)
        for line in result.stdout.splitlines()
        if line.strip().startswith("{")
    ]
    workbench_line = next(
        line for line in lines if "missing_gold_review_workbench_json" in line
    )

    assert workbench_line["missing_gold_review_workbench_json"].endswith(".json")
    assert workbench_line["missing_gold_review_workbench_csv"].endswith(".csv")
    assert workbench_line["missing_gold_review_workbench_markdown"].endswith(".md")
    assert workbench_line["missing_gold_review_items"] >= 0
    assert (
        workbench_line["policy"]
        == "human_review_only_never_auto_fill_gold"
    )
