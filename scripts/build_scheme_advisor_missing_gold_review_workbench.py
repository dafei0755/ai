"""Build a focused workbench for golden fields still blocking the quality gate."""

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
    write_missing_gold_review_artifacts,
)


_AUDIT_DIR = _ROOT / "docs" / "system-completeness-audit"


def build_default_args() -> List[str]:
    return [
        "--quality-gate",
        str(_AUDIT_DIR / "scheme-advisor-golden-quality-gate-2026-03-22.json"),
        "--review-workbench",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-workbench-2026-03-22.json"),
        "--output-json",
        str(_AUDIT_DIR / "scheme-advisor-missing-gold-review-workbench-2026-03-22.json"),
        "--output-csv",
        str(_AUDIT_DIR / "scheme-advisor-missing-gold-review-workbench-2026-03-22.csv"),
        "--output-md",
        str(_AUDIT_DIR / "scheme-advisor-missing-gold-review-workbench-2026-03-22.md"),
    ]


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build missing golden-field review workbench.")
    parser.add_argument("--quality-gate", type=Path, required=True)
    parser.add_argument("--review-workbench", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args(argv)

    report = write_missing_gold_review_artifacts(
        quality_gate_path=args.quality_gate,
        review_workbench_path=args.review_workbench,
        output_json=args.output_json,
        output_csv=args.output_csv,
        output_md=args.output_md,
    )
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main(build_default_args())
