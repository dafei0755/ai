"""Sync human-filled Golden review workbench fields into a review CSV copy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import List


_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from intelligent_project_analyzer.services.scheme_advisor_golden_verifier import (
    sync_review_csv_file_from_workbench,
)


_AUDIT_DIR = _ROOT / "docs" / "system-completeness-audit"


def build_default_args() -> List[str]:
    return [
        "--review-csv",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-batch-01-p0-2026-03-22.csv"),
        "--workbench-csv",
        str(_AUDIT_DIR / "scheme-advisor-missing-gold-review-workbench-2026-03-22.csv"),
        "--output-csv",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-batch-01-p0-synced-2026-03-22.csv"),
        "--report-output",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-workbench-sync-report-2026-03-22.json"),
    ]


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Sync Scheme Advisor Golden review CSV from workbench.")
    parser.add_argument("--review-csv", type=Path, required=True)
    parser.add_argument("--workbench-csv", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    args = parser.parse_args(argv)

    report = sync_review_csv_file_from_workbench(
        review_csv_path=args.review_csv,
        workbench_csv_path=args.workbench_csv,
        output_csv_path=args.output_csv,
        report_output_path=args.report_output,
    )
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main(build_default_args())
