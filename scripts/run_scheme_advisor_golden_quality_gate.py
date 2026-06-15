"""Run the Scheme Advisor P0 golden quality gate.

This script is intentionally a thin wrapper around the verifier CLI defaults
used by the current 2026-03-22 pressure-test audit. It gives humans and CI a
single stable command instead of copying a long argument list.
"""

from __future__ import annotations

from pathlib import Path
import json
import sys
from typing import List


_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from intelligent_project_analyzer.services.scheme_advisor_golden_verifier import (
    main as verifier_main,
    write_missing_gold_review_artifacts,
)

_AUDIT_DIR = _ROOT / "docs" / "system-completeness-audit"
_MISSING_GOLD_WORKBENCH_JSON = (
    _AUDIT_DIR / "scheme-advisor-missing-gold-review-workbench-2026-03-22.json"
)
_MISSING_GOLD_WORKBENCH_CSV = (
    _AUDIT_DIR / "scheme-advisor-missing-gold-review-workbench-2026-03-22.csv"
)
_MISSING_GOLD_WORKBENCH_MD = (
    _AUDIT_DIR / "scheme-advisor-missing-gold-review-workbench-2026-03-22.md"
)
_REQUIRED_GOLD_FIELDS = (
    "gold_expected_project_type,"
    "gold_expected_core_tension,"
    "gold_expected_output_depth"
)


def build_default_args() -> List[str]:
    return [
        "--pressure",
        str(_AUDIT_DIR / "scheme-advisor-pressure-test-2026-03-22.json"),
        "--golden",
        str(_AUDIT_DIR / "scheme-advisor-190-golden-annotation-updated-2026-03-22.json"),
        "--output",
        str(_AUDIT_DIR / "scheme-advisor-golden-verification-2026-03-22.json"),
        "--markdown-output",
        str(_AUDIT_DIR / "scheme-advisor-golden-verification-2026-03-22.md"),
        "--quality-gate-output",
        str(_AUDIT_DIR / "scheme-advisor-golden-quality-gate-2026-03-22.json"),
        "--required-review-batch",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-batch-01-p0-2026-03-22.json"),
        "--required-review-priority",
        "P0",
        "--required-gold-fields",
        _REQUIRED_GOLD_FIELDS,
        "--fail-on-quality-gate",
    ]


def build_missing_gold_review_workbench() -> dict:
    return write_missing_gold_review_artifacts(
        quality_gate_path=_AUDIT_DIR / "scheme-advisor-golden-quality-gate-2026-03-22.json",
        review_workbench_path=_AUDIT_DIR / "scheme-advisor-golden-review-workbench-2026-03-22.json",
        output_json=_MISSING_GOLD_WORKBENCH_JSON,
        output_csv=_MISSING_GOLD_WORKBENCH_CSV,
        output_md=_MISSING_GOLD_WORKBENCH_MD,
    )


def main() -> None:
    exit_code = 0
    try:
        verifier_main(build_default_args())
    except SystemExit as exc:
        exit_code = int(exc.code or 0)

    workbench = build_missing_gold_review_workbench()
    print(
        json.dumps(
            {
                "missing_gold_review_workbench_json": str(_MISSING_GOLD_WORKBENCH_JSON),
                "missing_gold_review_workbench_csv": str(_MISSING_GOLD_WORKBENCH_CSV),
                "missing_gold_review_workbench_markdown": str(_MISSING_GOLD_WORKBENCH_MD),
                "missing_gold_review_items": workbench["summary"]["total"],
                "policy": workbench["summary"]["policy"],
            },
            ensure_ascii=False,
        )
    )
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
