"""Apply reviewed Scheme Advisor golden CSV into an updated golden copy."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import List


_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from intelligent_project_analyzer.services.scheme_advisor_golden_verifier import main as verifier_main


_AUDIT_DIR = _ROOT / "docs" / "system-completeness-audit"


def build_default_args() -> List[str]:
    return [
        "--golden",
        str(_AUDIT_DIR / "scheme-advisor-190-golden-annotation-base-2026-03-22.json"),
        "--review-csv",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-batch-01-p0-synced-2026-03-22.csv"),
        "--updated-golden-output",
        str(_AUDIT_DIR / "scheme-advisor-190-golden-annotation-updated-2026-03-22.json"),
        "--apply-report-output",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-apply-report-2026-03-22.json"),
    ]


def main() -> None:
    verifier_main(build_default_args())
    report_path = _AUDIT_DIR / "scheme-advisor-golden-review-apply-report-2026-03-22.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        summary = dict(report.get("summary", {}))
        summary["updated_golden_output"] = str(
            _AUDIT_DIR / "scheme-advisor-190-golden-annotation-updated-2026-03-22.json"
        )
        print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
