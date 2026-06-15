"""Check Scheme Advisor P0 golden review CSV completion."""

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
    build_review_completion_report,
    load_review_csv,
    write_report_json,
)


_AUDIT_DIR = _ROOT / "docs" / "system-completeness-audit"
_REQUIRED_GOLD_FIELDS = (
    "gold_expected_project_type,"
    "gold_expected_core_tension,"
    "gold_expected_output_depth"
)


def build_default_args() -> List[str]:
    return [
        "--review-csv",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-batch-01-p0-synced-2026-03-22.csv"),
        "--output",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-completion-2026-03-22.json"),
        "--markdown-output",
        str(_AUDIT_DIR / "scheme-advisor-golden-review-completion-2026-03-22.md"),
        "--required-gold-fields",
        _REQUIRED_GOLD_FIELDS,
        "--fail-on-incomplete",
    ]


def _parse_comma_separated_arg(value: str) -> List[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(_ROOT).as_posix()
    except ValueError:
        return str(path)


def write_completion_markdown(report: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = report.get("summary", {})
    lines = [
        "# 方案高参 Golden 复核进度",
        "",
        f"- 来源：`{report.get('source_review_csv', '')}`",
        f"- 总行数：{summary.get('total_rows', 0)}",
        f"- 已完成：{summary.get('complete_rows', 0)}",
        f"- 未完成：{summary.get('incomplete_rows', 0)}",
        "",
        "## 字段缺失统计",
        "",
        "| 字段 | 缺失数量 |",
        "|---|---:|",
    ]
    for field, count in (summary.get("missing_by_field") or {}).items():
        lines.append(f"| `{field}` | {count} |")
    lines.extend(
        [
            "",
            "## 未完成样本",
            "",
            "| ID | 缺失字段 |",
            "|---:|---|",
        ]
    )
    for item in report.get("incomplete_items", []) or []:
        missing = ", ".join(f"`{field}`" for field in item.get("missing_fields", []))
        lines.append(f"| {item.get('id')} | {missing} |")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Check golden review CSV completion.")
    parser.add_argument("--review-csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, default=None)
    parser.add_argument("--required-gold-fields", required=True)
    parser.add_argument("--fail-on-incomplete", action="store_true")
    args = parser.parse_args(argv)

    report = build_review_completion_report(
        load_review_csv(args.review_csv),
        required_gold_fields=_parse_comma_separated_arg(args.required_gold_fields),
    )
    report["source_review_csv"] = str(args.review_csv)
    write_report_json(report, args.output)
    if args.markdown_output:
        write_completion_markdown(report, args.markdown_output)
        report["summary"]["markdown_output"] = _display_path(args.markdown_output)

    print(json.dumps(report["summary"], ensure_ascii=False))
    if args.fail_on_incomplete and report["summary"]["incomplete_rows"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main(build_default_args())
