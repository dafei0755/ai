"""Build a human-editable Scheme Advisor golden review workbench."""

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
    write_review_workbench_artifacts,
)


_AUDIT_DIR = _ROOT / "docs" / "system-completeness-audit"


def build_default_args() -> List[str]:
    return [
        "--review-batch",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-batch-01-p0-2026-03-22.json"),
        "--suggestions",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-batch-01-p0-suggestions-2026-03-22.json"),
        "--output-json",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-workbench-2026-03-22.json"),
        "--output-csv",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-workbench-2026-03-22.csv"),
        "--output-md",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-workbench-2026-03-22.md"),
    ]


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build Scheme Advisor golden review workbench.")
    parser.add_argument("--review-batch", type=Path, required=True)
    parser.add_argument("--suggestions", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args(argv)

    report = write_review_workbench_artifacts(
        review_batch_path=args.review_batch,
        suggestions_path=args.suggestions,
        output_json=args.output_json,
        output_csv=args.output_csv,
        output_md=args.output_md,
    )
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main(build_default_args())
