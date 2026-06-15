import json
import subprocess
import sys

from scripts.build_scheme_advisor_golden_review_status import build_default_args, build_status_report


def test_golden_review_status_script_defaults_to_current_audit_artifacts():
    args = build_default_args()

    assert "scheme-advisor-golden-review-completion-2026-03-22.json" in args[
        args.index("--completion") + 1
    ]
    assert "scheme-advisor-golden-review-apply-report-2026-03-22.json" in args[
        args.index("--apply-report") + 1
    ]
    assert "scheme-advisor-golden-quality-gate-2026-03-22.json" in args[
        args.index("--quality-gate") + 1
    ]
    assert "scheme-advisor-terminal-copy-guardrail-2026-03-22.json" in args[
        args.index("--terminal-copy-guardrail") + 1
    ]
    assert "scheme-advisor-missing-gold-review-workbench-2026-03-22.json" in args[
        args.index("--review-workbench") + 1
    ]
    assert "scheme-advisor-golden-review-workbench-sync-report-2026-03-22.json" in args[
        args.index("--workbench-sync-report") + 1
    ]
    assert "scheme-advisor-golden-review-status-2026-03-22.json" in args[
        args.index("--output") + 1
    ]


def test_golden_review_status_script_runs_from_file_path():
    result = subprocess.run(
        [sys.executable, "scripts/build_scheme_advisor_golden_review_status.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0
    assert "ModuleNotFoundError" not in result.stderr
    summary = json.loads(result.stdout)
    assert summary["review_status"] == "needs_human_review"
    assert summary["completion"]["incomplete_rows"] >= 1
    assert summary["quality_gate"]["gate_status"] == "fail"
    assert summary["terminal_copy_guardrail"]["summary"]["violation_count"] == 0
    assert summary["review_workbench"]["summary"]["total"] == 28
    assert summary["review_workbench"]["summary"]["policy"] == "human_review_only_never_auto_fill_gold"
    assert summary["workbench_sync"]["summary"]["updated_rows"] == 0
    assert summary["workbench_sync"]["summary"]["copied_fields"] == 0


def test_terminal_copy_violations_block_golden_promotion():
    report = build_status_report(
        completion={
            "summary": {
                "total_rows": 1,
                "complete_rows": 1,
                "incomplete_rows": 0,
            }
        },
        apply_report={"summary": {"review_rows": 1, "updated_items": 1, "updated_fields": 3}},
        quality_gate={
            "summary": {
                "gate_status": "pass",
                "required_items": 1,
                "required_items_with_complete_gold": 1,
                "failed_checks": 0,
            },
            "failures": [],
        },
        terminal_copy_guardrail={
            "guardrail_scope": "terminal_user_visible_copy",
            "violation_policy": "fail_review",
            "summary": {
                "forbidden_term_count": 10,
                "violation_count": 2,
            },
            "violations": [
                {"path": "app/page.tsx", "line": 10, "term": "core_tension"},
                {"path": "app/page.tsx", "line": 11, "term": "ontology"},
            ],
        },
        review_workbench={"summary": {"total": 1, "gold_fields_are_blank": True}},
        workbench_sync={"summary": {"updated_rows": 0, "copied_fields": 0}},
    )

    assert report["review_status"] == "needs_terminal_copy_cleanup"
    assert report["next_action"] == "fix_terminal_user_copy_violations"
    assert report["quality_gate"]["gate_status"] == "fail"
    assert report["quality_gate"]["terminal_copy_violation_count"] == 2
    assert report["workbench_sync"]["summary"]["copied_fields"] == 0
