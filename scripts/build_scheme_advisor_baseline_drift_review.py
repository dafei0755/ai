"""Build a human-review batch for Scheme Advisor golden/pressure drift."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping


_ROOT = Path(__file__).resolve().parents[1]
_AUDIT_DIR = _ROOT / "docs" / "system-completeness-audit"
_DEFAULT_SYSTEMIC_BACKLOG = _AUDIT_DIR / "scheme-advisor-systemic-remediation-backlog-2026-03-22.json"
_DEFAULT_GOLDEN = _AUDIT_DIR / "scheme-advisor-190-golden-annotation-base-2026-03-22.json"
_DEFAULT_PRESSURE_RESULT = _AUDIT_DIR / "scheme-advisor-pressure-test-2026-03-22.json"
_DEFAULT_JSON_OUTPUT = _AUDIT_DIR / "scheme-advisor-baseline-drift-review-2026-03-22.json"
_DEFAULT_MD_OUTPUT = _AUDIT_DIR / "scheme-advisor-baseline-drift-review-2026-03-22.md"


def build_default_args() -> List[str]:
    return [
        "--systemic-backlog",
        str(_DEFAULT_SYSTEMIC_BACKLOG),
        "--golden",
        str(_DEFAULT_GOLDEN),
        "--pressure-result",
        str(_DEFAULT_PRESSURE_RESULT),
        "--output",
        str(_DEFAULT_JSON_OUTPUT),
        "--markdown-output",
        str(_DEFAULT_MD_OUTPUT),
    ]


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(data: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_drift_review(
    systemic_backlog: Mapping[str, Any],
    *,
    golden_annotation: Mapping[str, Any] | None = None,
    pressure_result: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    drift = (systemic_backlog.get("summary") or {}).get("baseline_drift") or {}
    drift_items = list(drift.get("items") or [])
    policy = str(drift.get("policy") or "report_only_never_auto_sync")
    requires_review = bool(drift.get("requires_human_review") or drift_items)
    golden_index = _build_golden_issue_index(golden_annotation or {})
    pressure_index = _build_pressure_issue_index(pressure_result or {})
    sample_review_items = _build_sample_review_items(
        drift_items,
        golden_annotation=golden_annotation or {},
        pressure_result=pressure_result or {},
        golden_index=golden_index,
        pressure_index=pressure_index,
    )

    return {
        "schema_version": "scheme_advisor_baseline_drift_review.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "drift_items": len(drift_items),
            "requires_human_review": requires_review,
            "policy": policy,
            "will_auto_update_golden": False,
            "sample_review_items": len(sample_review_items),
        },
        "items": [
            _review_item(index + 1, item, golden_index=golden_index, pressure_index=pressure_index)
            for index, item in enumerate(drift_items)
        ],
        "sample_review_items": sample_review_items,
    }


def write_drift_review_markdown(review: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = review.get("summary") or {}
    lines = [
        "# 方案高参 Golden/压测基线差异复核",
        "",
        f"- 生成时间：`{review.get('generated_at')}`",
        f"- 差异项：{summary.get('drift_items', 0)}",
        f"- 需要人工复核：{summary.get('requires_human_review')}",
        f"- 处理策略：`{summary.get('policy')}`",
        f"- 自动更新 Golden：{summary.get('will_auto_update_golden')}",
        "",
        "## 复核项",
        "",
        "| ID | 字段 | Golden 批注 | 最新压测 | Golden 独有题号 | 最新压测独有题号 | 状态 | 允许决策 |",
        "|---:|---|---:|---:|---|---|---|---|",
    ]
    for item in review.get("items", []) or []:
        decisions = " / ".join(f"`{decision}`" for decision in item.get("allowed_decisions", []) or [])
        lines.append(
            "| {id} | `{field}` | {golden} | {pressure} | {golden_only} | {pressure_only} | `{status}` | {decisions} |".format(
                id=item.get("id"),
                field=_md(item.get("field")),
                golden=item.get("golden_value", 0),
                pressure=item.get("latest_pressure_value", 0),
                golden_only=_format_ids(item.get("golden_only_ids") or []),
                pressure_only=_format_ids(item.get("latest_pressure_only_ids") or []),
                status=item.get("status", ""),
                decisions=decisions,
            )
        )
    lines.extend(
        [
            "",
            "## 逐题复核",
            "",
            "| 题号 | 差异字段 | Golden 归因 | 最新压测归因 | 当前类型 | 题干摘要 |",
            "|---:|---|---|---|---|---|",
        ]
    )
    for item in review.get("sample_review_items", []) or []:
        lines.append(
            "| {id} | {fields} | {golden_codes} | {pressure_codes} | {project_type} | {excerpt} |".format(
                id=item.get("id"),
                fields=_format_code_list(item.get("delta_fields") or []),
                golden_codes=_format_code_list(item.get("golden_codes") or []),
                pressure_codes=_format_code_list(item.get("latest_pressure_codes") or []),
                project_type=_md(item.get("project_type")),
                excerpt=_md(item.get("prompt_excerpt")),
            )
        )
    lines.extend(
        [
            "",
            "## 处理规则",
            "",
            "- 该文件只用于人工复核，不会自动修改 golden annotation。",
            "- `keep_golden` 表示保留人工批注口径。",
            "- `accept_latest_pressure` 表示接受最新服务层压测统计，后续由人工确认后生成 updated golden。",
            "- `split_review_needed` 表示该差异需要拆成逐样本复核，不能只按汇总数判断。",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _review_item(
    index: int,
    item: Mapping[str, Any],
    *,
    golden_index: Mapping[str, List[int]],
    pressure_index: Mapping[str, List[int]],
) -> Dict[str, Any]:
    field = str(item.get("field") or "")
    golden_ids = sorted(golden_index.get(field) or [])
    pressure_ids = sorted(pressure_index.get(field) or [])
    return {
        "id": index,
        "field": field,
        "golden_value": int(item.get("golden") or 0),
        "latest_pressure_value": int(item.get("pressure") or 0),
        "golden_ids": golden_ids,
        "latest_pressure_ids": pressure_ids,
        "golden_only_ids": sorted(set(golden_ids) - set(pressure_ids)),
        "latest_pressure_only_ids": sorted(set(pressure_ids) - set(golden_ids)),
        "status": "needs_human_review",
        "allowed_decisions": [
            "keep_golden",
            "accept_latest_pressure",
            "split_review_needed",
        ],
        "selected_decision": "",
        "review_note": "",
    }


def _build_sample_review_items(
    drift_items: List[Mapping[str, Any]],
    *,
    golden_annotation: Mapping[str, Any],
    pressure_result: Mapping[str, Any],
    golden_index: Mapping[str, List[int]],
    pressure_index: Mapping[str, List[int]],
) -> List[Dict[str, Any]]:
    golden_items = _items_by_id(golden_annotation)
    pressure_items = _items_by_id(pressure_result)
    sample_fields: Dict[int, List[str]] = {}

    for item in drift_items:
        field = str(item.get("field") or "")
        golden_ids = set(golden_index.get(field) or [])
        pressure_ids = set(pressure_index.get(field) or [])
        for item_id in sorted(golden_ids ^ pressure_ids):
            sample_fields.setdefault(item_id, []).append(field)

    rows: List[Dict[str, Any]] = []
    for item_id in sorted(sample_fields):
        golden_item = golden_items.get(item_id) or {}
        pressure_item = pressure_items.get(item_id) or {}
        rows.append(
            {
                "id": item_id,
                "status": "needs_human_review",
                "delta_fields": sorted(sample_fields[item_id]),
                "golden_codes": _golden_codes(golden_item),
                "latest_pressure_codes": _pressure_codes(pressure_item),
                "project_type": (
                    pressure_item.get("project_type")
                    or golden_item.get("current_project_type")
                    or "-"
                ),
                "prompt_excerpt": (
                    golden_item.get("prompt_excerpt")
                    or pressure_item.get("prompt_excerpt")
                    or ""
                ),
                "allowed_decisions": [
                    "keep_golden",
                    "accept_latest_pressure",
                    "split_review_needed",
                ],
                "selected_decision": "",
                "review_note": "",
            }
        )
    return rows


def _items_by_id(source: Mapping[str, Any]) -> Dict[int, Mapping[str, Any]]:
    rows: Dict[int, Mapping[str, Any]] = {}
    for item in source.get("items", []) or []:
        if isinstance(item, Mapping) and item.get("id") is not None:
            rows[int(item["id"])] = item
    return rows


def _golden_codes(item: Mapping[str, Any]) -> List[str]:
    return sorted(_split_codes(str(item.get("warning_codes") or "")))


def _pressure_codes(item: Mapping[str, Any]) -> List[str]:
    codes: List[str] = []
    for bucket in ("warning_issues", "governance_signals"):
        for issue in item.get(bucket) or []:
            if isinstance(issue, Mapping) and issue.get("code"):
                codes.append(str(issue["code"]))
    return sorted(set(codes))


def _build_golden_issue_index(golden_annotation: Mapping[str, Any]) -> Dict[str, List[int]]:
    index: Dict[str, List[int]] = {}
    for item in golden_annotation.get("items", []) or []:
        if not isinstance(item, Mapping) or item.get("id") is None:
            continue
        item_id = int(item["id"])
        codes = _split_codes(str(item.get("warning_codes") or ""))
        for code in codes:
            field = _field_for_code(code)
            if field:
                index.setdefault(field, []).append(item_id)
    return {field: sorted(set(ids)) for field, ids in index.items()}


def _build_pressure_issue_index(pressure_result: Mapping[str, Any]) -> Dict[str, List[int]]:
    index: Dict[str, List[int]] = {}
    for item in pressure_result.get("items", []) or []:
        if not isinstance(item, Mapping) or item.get("id") is None:
            continue
        item_id = int(item["id"])
        for issue in item.get("warning_issues") or []:
            if isinstance(issue, Mapping):
                field = _field_for_code(str(issue.get("code") or ""))
                if field:
                    index.setdefault(field, []).append(item_id)
        for issue in item.get("governance_signals") or []:
            if isinstance(issue, Mapping):
                field = _field_for_code(str(issue.get("code") or ""))
                if field:
                    index.setdefault(field, []).append(item_id)
    return {field: sorted(set(ids)) for field, ids in index.items()}


def _split_codes(value: str) -> List[str]:
    normalized = value.replace("；", ",").replace(";", ",")
    return [part.strip() for part in normalized.split(",") if part.strip()]


def _field_for_code(code: str) -> str:
    if code in {"coverage_gap", "knowledge_gap_ticket", "low_classification_confidence"}:
        return f"warning_counts.{code}"
    if code == "activation_pack_candidate":
        return f"governance_signal_counts.{code}"
    return ""


def _format_ids(ids: List[int]) -> str:
    if not ids:
        return "-"
    return ", ".join(str(item) for item in ids[:20])


def _format_code_list(values: List[str]) -> str:
    if not values:
        return "-"
    return ", ".join(f"`{_md(value)}`" for value in values)


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build baseline drift review batch.")
    parser.add_argument("--systemic-backlog", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--pressure-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, default=None)
    args = parser.parse_args(argv)

    review = build_drift_review(
        load_json(args.systemic_backlog),
        golden_annotation=load_json(args.golden),
        pressure_result=load_json(args.pressure_result),
    )
    write_json(review, args.output)
    if args.markdown_output:
        write_drift_review_markdown(review, args.markdown_output)
    print(json.dumps(review["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main(build_default_args())
