import json
import subprocess
import sys

from scripts.build_scheme_advisor_baseline_drift_review import (
    build_default_args,
    build_drift_review,
)


def _sample_systemic_backlog():
    return {
        "summary": {
            "baseline_drift": {
                "has_drift": True,
                "policy": "report_only_never_auto_sync",
                "requires_human_review": True,
                "items": [
                    {
                        "field": "warning_counts.coverage_gap",
                        "golden": 110,
                        "pressure": 107,
                    },
                    {
                        "field": "governance_signal_counts.activation_pack_candidate",
                        "golden": 183,
                        "pressure": 181,
                    },
                ],
            }
        }
    }


def _sample_golden_annotation():
    return {
        "items": [
            {
                "id": 1,
                "warning_codes": "coverage_gap；activation_pack_candidate",
                "prompt_excerpt": "一号题题干",
                "current_project_type": "personal_residential",
            },
            {
                "id": 2,
                "warning_codes": "coverage_gap",
                "prompt_excerpt": "二号题题干",
                "current_project_type": "community_public",
            },
            {
                "id": 3,
                "warning_codes": "activation_pack_candidate",
                "prompt_excerpt": "三号题题干",
                "current_project_type": "public_cultural",
            },
        ]
    }


def _sample_pressure_result():
    return {
        "items": [
            {
                "id": 1,
                "warning_issues": [{"code": "coverage_gap"}],
                "governance_signals": [{"code": "activation_pack_candidate"}],
                "prompt_excerpt": "一号题最新题干",
                "project_type": "personal_residential",
            },
            {
                "id": 4,
                "warning_issues": [{"code": "coverage_gap"}],
                "governance_signals": [],
                "prompt_excerpt": "四号题题干",
                "project_type": "commercial_retail",
            },
        ]
    }


def test_baseline_drift_review_defaults_to_current_audit_artifacts():
    args = build_default_args()

    assert "scheme-advisor-systemic-remediation-backlog-2026-03-22.json" in args[
        args.index("--systemic-backlog") + 1
    ]
    assert "scheme-advisor-190-golden-annotation-base-2026-03-22.json" in args[
        args.index("--golden") + 1
    ]
    assert "scheme-advisor-pressure-test-2026-03-22.json" in args[
        args.index("--pressure-result") + 1
    ]
    assert "scheme-advisor-baseline-drift-review-2026-03-22.json" in args[
        args.index("--output") + 1
    ]
    assert "scheme-advisor-baseline-drift-review-2026-03-22.md" in args[
        args.index("--markdown-output") + 1
    ]


def test_build_drift_review_keeps_report_only_human_review_policy():
    review = build_drift_review(_sample_systemic_backlog())

    assert review["schema_version"] == "scheme_advisor_baseline_drift_review.v1"
    assert review["summary"]["drift_items"] == 2
    assert review["summary"]["requires_human_review"] is True
    assert review["summary"]["policy"] == "report_only_never_auto_sync"
    assert review["summary"]["will_auto_update_golden"] is False

    first = review["items"][0]
    assert first["status"] == "needs_human_review"
    assert first["field"] == "warning_counts.coverage_gap"
    assert first["golden_value"] == 110
    assert first["latest_pressure_value"] == 107
    assert "keep_golden" in first["allowed_decisions"]
    assert "accept_latest_pressure" in first["allowed_decisions"]


def test_build_drift_review_locates_per_sample_delta_ids():
    review = build_drift_review(
        _sample_systemic_backlog(),
        golden_annotation=_sample_golden_annotation(),
        pressure_result=_sample_pressure_result(),
    )

    by_field = {item["field"]: item for item in review["items"]}

    coverage = by_field["warning_counts.coverage_gap"]
    assert coverage["golden_ids"] == [1, 2]
    assert coverage["latest_pressure_ids"] == [1, 4]
    assert coverage["golden_only_ids"] == [2]
    assert coverage["latest_pressure_only_ids"] == [4]

    activation = by_field["governance_signal_counts.activation_pack_candidate"]
    assert activation["golden_ids"] == [1, 3]
    assert activation["latest_pressure_ids"] == [1]
    assert activation["golden_only_ids"] == [3]
    assert activation["latest_pressure_only_ids"] == []


def test_build_drift_review_groups_per_sample_review_items():
    review = build_drift_review(
        _sample_systemic_backlog(),
        golden_annotation=_sample_golden_annotation(),
        pressure_result=_sample_pressure_result(),
    )

    by_id = {item["id"]: item for item in review["sample_review_items"]}

    assert review["summary"]["sample_review_items"] == 3
    assert by_id[2]["delta_fields"] == ["warning_counts.coverage_gap"]
    assert by_id[2]["golden_codes"] == ["coverage_gap"]
    assert by_id[2]["latest_pressure_codes"] == []
    assert by_id[2]["prompt_excerpt"] == "二号题题干"
    assert by_id[2]["status"] == "needs_human_review"

    assert by_id[3]["delta_fields"] == ["governance_signal_counts.activation_pack_candidate"]
    assert by_id[3]["golden_codes"] == ["activation_pack_candidate"]
    assert by_id[3]["latest_pressure_codes"] == []

    assert by_id[4]["delta_fields"] == ["warning_counts.coverage_gap"]
    assert by_id[4]["golden_codes"] == []
    assert by_id[4]["latest_pressure_codes"] == ["coverage_gap"]
    assert by_id[4]["prompt_excerpt"] == "四号题题干"


def test_baseline_drift_review_script_runs_from_file_path():
    result = subprocess.run(
        [sys.executable, "scripts/build_scheme_advisor_baseline_drift_review.py"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert result.returncode == 0
    assert "ModuleNotFoundError" not in result.stderr
    summary = json.loads(result.stdout)
    assert summary["policy"] == "report_only_never_auto_sync"
    assert summary["will_auto_update_golden"] is False
