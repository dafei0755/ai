"""Build a consolidated Scheme Advisor golden review status artifact."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


_ROOT = Path(__file__).resolve().parents[1]
_AUDIT_DIR = _ROOT / "docs" / "system-completeness-audit"


def build_default_args() -> List[str]:
    return [
        "--completion",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-completion-2026-03-22.json"),
        "--apply-report",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-apply-report-2026-03-22.json"),
        "--quality-gate",
        str(_AUDIT_DIR / "scheme-advisor-golden-quality-gate-2026-03-22.json"),
        "--terminal-copy-guardrail",
        str(_AUDIT_DIR / "scheme-advisor-terminal-copy-guardrail-2026-03-22.json"),
        "--review-workbench",
        str(_AUDIT_DIR / "scheme-advisor-missing-gold-review-workbench-2026-03-22.json"),
        "--workbench-sync-report",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-workbench-sync-report-2026-03-22.json"),
        "--output",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-status-2026-03-22.json"),
    ]


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_status_report(
    *,
    completion: Dict[str, Any],
    apply_report: Dict[str, Any],
    quality_gate: Dict[str, Any],
    terminal_copy_guardrail: Dict[str, Any],
    review_workbench: Dict[str, Any] | None = None,
    workbench_sync: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    completion_summary = completion.get("summary", {})
    apply_summary = apply_report.get("summary", {})
    gate_summary = quality_gate.get("summary", {})
    terminal_copy_summary = terminal_copy_guardrail.get("summary", {})
    incomplete_rows = int(completion_summary.get("incomplete_rows") or 0)
    base_gate_status = str(gate_summary.get("gate_status") or "unknown")
    terminal_copy_violation_count = int(terminal_copy_summary.get("violation_count") or 0)
    terminal_copy_blocks_review = (
        terminal_copy_guardrail.get("violation_policy") == "fail_review"
        and terminal_copy_violation_count > 0
    )
    gate_status = "fail" if terminal_copy_blocks_review else base_gate_status

    if incomplete_rows > 0:
        review_status = "needs_human_review"
        next_action = "fill_required_gold_fields"
    elif terminal_copy_blocks_review:
        review_status = "needs_terminal_copy_cleanup"
        next_action = "fix_terminal_user_copy_violations"
    elif gate_status == "fail":
        review_status = "needs_runtime_alignment"
        next_action = "inspect_quality_gate_failures"
    else:
        review_status = "ready"
        next_action = "promote_reviewed_golden"

    return {
        "schema_version": "scheme_advisor_golden_review_status.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "review_status": review_status,
        "next_action": next_action,
        "completion": {
            "total_rows": completion_summary.get("total_rows", 0),
            "complete_rows": completion_summary.get("complete_rows", 0),
            "incomplete_rows": incomplete_rows,
            "missing_by_field": completion_summary.get("missing_by_field", {}),
        },
        "apply_report": {
            "review_rows": apply_summary.get("review_rows", 0),
            "updated_items": apply_summary.get("updated_items", 0),
            "updated_fields": apply_summary.get("updated_fields", 0),
            "unknown_review_rows": apply_summary.get("unknown_review_rows", 0),
        },
        "quality_gate": {
            "gate_status": gate_status,
            "required_items": gate_summary.get("required_items", 0),
            "required_items_with_complete_gold": gate_summary.get("required_items_with_complete_gold", 0),
            "failed_checks": gate_summary.get("failed_checks", 0),
            "failure_count": len(quality_gate.get("failures", []) or []),
            "terminal_copy_violation_count": terminal_copy_violation_count,
        },
        "terminal_copy_guardrail": {
            "guardrail_scope": terminal_copy_guardrail.get("guardrail_scope", ""),
            "violation_policy": terminal_copy_guardrail.get("violation_policy", ""),
            "summary": terminal_copy_guardrail.get("summary", {}),
            "violations": terminal_copy_guardrail.get("violations", []),
        },
        "review_workbench": {
            "summary": (review_workbench or {}).get("summary", {}),
            "source_review_batch_path": (review_workbench or {}).get("source_review_batch_path", ""),
            "source_suggestions_path": (review_workbench or {}).get("source_suggestions_path", ""),
        },
        "workbench_sync": {
            "summary": (workbench_sync or {}).get("summary", {}),
            "source_review_csv_path": (workbench_sync or {}).get("source_review_csv_path", ""),
            "source_workbench_csv_path": (workbench_sync or {}).get("source_workbench_csv_path", ""),
            "output_csv_path": (workbench_sync or {}).get("output_csv_path", ""),
        },
    }


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build consolidated golden review status.")
    parser.add_argument("--completion", type=Path, required=True)
    parser.add_argument("--apply-report", type=Path, required=True)
    parser.add_argument("--quality-gate", type=Path, required=True)
    parser.add_argument("--terminal-copy-guardrail", type=Path, required=True)
    parser.add_argument("--review-workbench", type=Path, required=True)
    parser.add_argument("--workbench-sync-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    report = build_status_report(
        completion=load_json(args.completion),
        apply_report=load_json(args.apply_report),
        quality_gate=load_json(args.quality_gate),
        terminal_copy_guardrail=load_json(args.terminal_copy_guardrail),
        review_workbench=load_json(args.review_workbench),
        workbench_sync=load_json(args.workbench_sync_report),
    )
    write_json(report, args.output)
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "review_status",
                    "next_action",
                    "completion",
                    "quality_gate",
                    "terminal_copy_guardrail",
                    "review_workbench",
                    "workbench_sync",
                )
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main(build_default_args())
