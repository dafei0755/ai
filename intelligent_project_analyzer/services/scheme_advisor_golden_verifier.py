"""Verify Scheme Advisor pressure results against reviewed golden annotations."""

from __future__ import annotations

import argparse
import csv
import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PRESSURE = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-pressure-test-2026-03-22.json"
)
_DEFAULT_GOLDEN = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-190-golden-annotation-base-2026-03-22.json"
)
_DEFAULT_OUTPUT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-golden-verification-2026-03-22.json"
)
_DEFAULT_MD_OUTPUT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-golden-verification-2026-03-22.md"
)
_DEFAULT_QUALITY_GATE_OUTPUT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-golden-quality-gate-2026-03-22.json"
)
_DEFAULT_APPLY_OUTPUT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-190-golden-annotation-updated-2026-03-22.json"
)
_DEFAULT_APPLY_REPORT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-golden-review-apply-report-2026-03-22.json"
)


_OBSERVED_FIELD_BY_GOLD_FIELD = {
    "gold_expected_project_type": "project_type",
    "gold_expected_spatial_extent": "candidate_spatial_extent",
    "gold_expected_project_stage": "candidate_project_stage",
    "gold_expected_core_tension": "candidate_core_tension",
    "gold_expected_output_depth": "candidate_allowed_output_depth",
}
_GOLD_FIELD_LABELS = {
    "gold_expected_project_type": "空间分类",
    "gold_expected_spatial_extent": "空间尺度",
    "gold_expected_project_stage": "项目阶段",
    "gold_expected_core_tension": "核心矛盾",
    "gold_expected_output_depth": "输出深度",
}
_GOLD_FIELD_REVIEW_GUIDANCE = {
    "gold_expected_project_type": "填写系统应识别的稳定空间类型；无法归类时写入应进入复核的候选类型，不要临时造正式类型。",
    "gold_expected_spatial_extent": "填写题目实际对应的尺度层级，例如单房间、住宅、店铺、园区、城市片区或方法论。",
    "gold_expected_project_stage": "填写当前问题处于入口咨询、概念策略、方案框架、深化决策或方法论讨论等阶段。",
    "gold_expected_core_tension": "用一句人话写出本题最关键的冲突或取舍，不要照抄系统候选值。",
    "gold_expected_output_depth": "填写系统此时最多能输出到什么深度，例如策略框架、条件方案、决策论证或方法论，不要越过资料和知识覆盖边界。",
}
_REVIEW_MERGE_FIELDS = tuple(_OBSERVED_FIELD_BY_GOLD_FIELD.keys()) + ("review_decision", "review_note")
_WORKBENCH_SYNC_FIELDS = tuple(_OBSERVED_FIELD_BY_GOLD_FIELD.keys()) + ("review_decision", "review_note")
_APPROVED_REVIEW_DECISIONS = {"approved", "approve", "pass", "passed", "通过", "批准", "确认"}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_review_csv(path: Path) -> List[Dict[str, str]]:
    with Path(path).open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def apply_review_rows_to_golden_annotation(
    golden_annotation: Mapping[str, Any],
    review_rows: Iterable[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Merge approved human review fields into a golden annotation copy.

    `gold_expected_*` fields become official only after the reviewer explicitly
    marks the row approved. Notes can still be copied for draft rows so the next
    reviewer sees the context without accidentally promoting draft suggestions.
    """

    review_rows_list = list(review_rows)
    updated_annotation = copy.deepcopy(dict(golden_annotation))
    items = updated_annotation.get("items") or []
    items_by_id = {
        str(item.get("id")): item
        for item in items
        if isinstance(item, dict) and item.get("id") is not None
    }

    updated_item_ids: set[str] = set()
    updated_fields = 0
    skipped_empty_fields = 0
    skipped_unapproved_gold_fields = 0
    review_rows_pending_decision = 0
    unknown_ids: List[str] = []

    for row in review_rows_list:
        item_id = str(row.get("id") or "").strip()
        if not item_id or item_id not in items_by_id:
            if item_id:
                unknown_ids.append(item_id)
            continue
        item = items_by_id[item_id]
        item_updated = False
        review_decision = str(row.get("review_decision") or "").strip()
        is_approved = review_decision.lower() in _APPROVED_REVIEW_DECISIONS
        row_has_gold_values = any(
            str(row.get(field) or "").strip()
            for field in _OBSERVED_FIELD_BY_GOLD_FIELD
        )
        if row_has_gold_values and not is_approved:
            review_rows_pending_decision += 1
        for field in _REVIEW_MERGE_FIELDS:
            if field not in row:
                continue
            value = str(row.get(field) or "").strip()
            if not value:
                skipped_empty_fields += 1
                continue
            if field in _OBSERVED_FIELD_BY_GOLD_FIELD and not is_approved:
                skipped_unapproved_gold_fields += 1
                continue
            if item.get(field) != value:
                item[field] = value
                updated_fields += 1
                item_updated = True
        if item_updated:
            updated_item_ids.add(item_id)

    return {
        "schema_version": "scheme_advisor_golden_review_apply.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "review_rows": len(review_rows_list),
            "updated_items": len(updated_item_ids),
            "updated_fields": updated_fields,
            "skipped_empty_fields": skipped_empty_fields,
            "skipped_unapproved_gold_fields": skipped_unapproved_gold_fields,
            "review_rows_pending_decision": review_rows_pending_decision,
            "unknown_review_rows": len(unknown_ids),
        },
        "unknown_ids": unknown_ids,
        "updated_annotation": updated_annotation,
    }


def apply_review_csv_file(
    *,
    golden_path: Path,
    review_csv_path: Path,
    updated_golden_output: Path,
    apply_report_output: Path,
) -> Dict[str, Any]:
    result = apply_review_rows_to_golden_annotation(load_json(golden_path), load_review_csv(review_csv_path))
    updated_golden_output.parent.mkdir(parents=True, exist_ok=True)
    updated_golden_output.write_text(
        json.dumps(result["updated_annotation"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = {
        key: value
        for key, value in result.items()
        if key != "updated_annotation"
    }
    report["source_golden_path"] = str(golden_path)
    report["review_csv_path"] = str(review_csv_path)
    report["updated_golden_output"] = str(updated_golden_output)
    apply_report_output.parent.mkdir(parents=True, exist_ok=True)
    apply_report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def sync_review_csv_rows_from_workbench(
    review_rows: Iterable[Mapping[str, Any]],
    workbench_rows: Iterable[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Copy human-filled fields from a workbench back to review CSV rows.

    This deliberately ignores `suggested_gold_expected_*` fields. Suggestions are
    reference material only; the reviewer must type or paste values into the
    official `gold_expected_*` fields before they can be synced.
    """

    review_rows_copy = [dict(row) for row in review_rows]
    workbench_by_id = {
        str(row.get("id") or "").strip(): row
        for row in workbench_rows
        if str(row.get("id") or "").strip()
    }
    updated_rows = 0
    copied_fields = 0
    skipped_empty_fields = 0
    missing_workbench_rows: List[str] = []

    for row in review_rows_copy:
        item_id = str(row.get("id") or "").strip()
        workbench_row = workbench_by_id.get(item_id)
        if not workbench_row:
            if item_id:
                missing_workbench_rows.append(item_id)
            continue
        row_updated = False
        for field in _WORKBENCH_SYNC_FIELDS:
            if field not in row:
                continue
            value = str(workbench_row.get(field) or "").strip()
            if not value:
                skipped_empty_fields += 1
                continue
            if row.get(field) != value:
                row[field] = value
                copied_fields += 1
                row_updated = True
        if row_updated:
            updated_rows += 1

    return {
        "schema_version": "scheme_advisor_golden_review_workbench_sync.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "review_rows": len(review_rows_copy),
            "workbench_rows": len(workbench_by_id),
            "updated_rows": updated_rows,
            "copied_fields": copied_fields,
            "skipped_empty_fields": skipped_empty_fields,
            "missing_workbench_rows": len(missing_workbench_rows),
        },
        "missing_workbench_ids": missing_workbench_rows,
        "review_rows": review_rows_copy,
    }


def sync_review_csv_file_from_workbench(
    *,
    review_csv_path: Path,
    workbench_csv_path: Path,
    output_csv_path: Path,
    report_output_path: Path,
) -> Dict[str, Any]:
    result = sync_review_csv_rows_from_workbench(
        load_review_csv(review_csv_path),
        load_review_csv(workbench_csv_path),
    )

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    review_rows = result["review_rows"]
    fieldnames = list(review_rows[0].keys()) if review_rows else ["id"]
    with output_csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(review_rows)

    report = {
        key: value
        for key, value in result.items()
        if key != "review_rows"
    }
    report["source_review_csv_path"] = str(review_csv_path)
    report["source_workbench_csv_path"] = str(workbench_csv_path)
    report["output_csv_path"] = str(output_csv_path)
    report_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def build_review_suggestion_rows(review_batch: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Build machine suggestions for human review without writing gold fields."""

    rows: List[Dict[str, Any]] = []
    for item in review_batch.get("items", []) or []:
        if not isinstance(item, Mapping):
            continue
        classification_safe = _classification_is_safe(item)
        suggested_project_type = str(item.get("current_project_type") or "").strip() if classification_safe else ""
        suggested_spatial_extent = str(item.get("candidate_spatial_extent") or "").strip()
        suggested_project_stage = str(item.get("candidate_project_stage") or "").strip()
        suggested_core_tension = str(item.get("candidate_core_tension") or "").strip()
        suggested_output_depth = str(item.get("candidate_allowed_output_depth") or "").strip()

        complete_suggestion = all(
            [
                suggested_project_type,
                suggested_spatial_extent,
                suggested_project_stage,
                suggested_core_tension,
                suggested_output_depth,
            ]
        )
        row = {
            "id": item.get("id"),
            "prompt_excerpt": item.get("prompt_excerpt", ""),
            "review_priority": item.get("review_priority", ""),
            "remediation_family": item.get("remediation_family", ""),
            "current_project_type": item.get("current_project_type", ""),
            "confidence": item.get("confidence", ""),
            "suggested_gold_expected_project_type": suggested_project_type,
            "suggested_gold_expected_spatial_extent": suggested_spatial_extent,
            "suggested_gold_expected_project_stage": suggested_project_stage,
            "suggested_gold_expected_core_tension": suggested_core_tension,
            "suggested_gold_expected_output_depth": suggested_output_depth,
            "suggestion_decision": "ready_for_fast_review" if complete_suggestion else "needs_human_decision",
            "suggestion_note": _suggestion_note(item, classification_safe),
        }
        rows.append(row)
    return rows


def write_review_suggestion_artifacts(
    *,
    review_batch_path: Path,
    output_json: Path,
    output_csv: Path,
    output_md: Path,
) -> Dict[str, Any]:
    rows = build_review_suggestion_rows(load_json(review_batch_path))
    summary = {
        "total": len(rows),
        "ready_for_fast_review": sum(1 for row in rows if row.get("suggestion_decision") == "ready_for_fast_review"),
        "needs_human_decision": sum(1 for row in rows if row.get("suggestion_decision") == "needs_human_decision"),
    }
    report = {
        "schema_version": "scheme_advisor_golden_review_suggestions.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_review_batch_path": str(review_batch_path),
        "summary": summary,
        "items": rows,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["id"]
    with output_csv.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    output_md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 方案高参黄金标注人工复核建议",
        "",
        f"- 来源批次：`{review_batch_path}`",
        f"- 总数：{summary['total']}",
        f"- 可快速复核：{summary['ready_for_fast_review']}",
        f"- 需人工裁决：{summary['needs_human_decision']}",
        "- 边界：本文件只提供人工复核建议，不自动写入 `gold_expected_*` 字段。",
        "",
        "| ID | 优先级 | 系统性问题族 | 建议状态 | 建议项目类型 | 建议空间尺度 | 建议项目阶段 | 核心矛盾建议 | 建议输出深度 | 问题摘要 |",
        "|---:|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('id')} | {_md(row.get('review_priority'))} | {_md(row.get('remediation_family'))} | "
            f"{_md(row.get('suggestion_decision'))} | {_md(row.get('suggested_gold_expected_project_type'))} | "
            f"{_md(row.get('suggested_gold_expected_spatial_extent'))} | "
            f"{_md(row.get('suggested_gold_expected_project_stage'))} | "
            f"{_md(row.get('suggested_gold_expected_core_tension'))} | "
            f"{_md(row.get('suggested_gold_expected_output_depth'))} | "
            f"{_md(str(row.get('prompt_excerpt') or '')[:80])} |"
        )
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_review_workbench_rows(
    review_batch: Mapping[str, Any],
    suggestions_report: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    """Build a single human-editing sheet from candidates and advisory suggestions.

    The workbench intentionally keeps `gold_expected_*` blank. The reviewer can
    copy or edit suggested values after checking the case, but the system never
    promotes suggestions into gold fields automatically.
    """

    suggestions_by_id = {
        str(item.get("id")): item
        for item in suggestions_report.get("items", []) or []
        if isinstance(item, Mapping) and item.get("id") is not None
    }
    rows: List[Dict[str, Any]] = []
    for item in review_batch.get("items", []) or []:
        if not isinstance(item, Mapping):
            continue
        item_id = str(item.get("id") or "").strip()
        suggestion = suggestions_by_id.get(item_id, {})
        rows.append(
            {
                "id": item.get("id"),
                "review_priority": item.get("review_priority", ""),
                "remediation_family": item.get("remediation_family", ""),
                "review_task": item.get("review_task", ""),
                "review_instruction": "人工确认后填写 gold_expected_*，不要直接把建议值当事实。",
                "prompt_excerpt": item.get("prompt_excerpt", ""),
                "candidate_project_type": item.get("current_project_type", ""),
                "candidate_confidence": item.get("confidence", ""),
                "candidate_warning_codes": item.get("warning_codes", ""),
                "candidate_spatial_extent": item.get("candidate_spatial_extent", ""),
                "candidate_project_stage": item.get("candidate_project_stage", ""),
                "candidate_core_tension": item.get("candidate_core_tension", ""),
                "candidate_allowed_output_depth": item.get("candidate_allowed_output_depth", ""),
                "suggestion_decision": suggestion.get("suggestion_decision", ""),
                "suggestion_note": suggestion.get("suggestion_note", ""),
                "suggested_gold_expected_project_type": suggestion.get(
                    "suggested_gold_expected_project_type", ""
                ),
                "suggested_gold_expected_spatial_extent": suggestion.get(
                    "suggested_gold_expected_spatial_extent", ""
                ),
                "suggested_gold_expected_project_stage": suggestion.get(
                    "suggested_gold_expected_project_stage", ""
                ),
                "suggested_gold_expected_core_tension": suggestion.get(
                    "suggested_gold_expected_core_tension", ""
                ),
                "suggested_gold_expected_output_depth": suggestion.get(
                    "suggested_gold_expected_output_depth", ""
                ),
                "gold_expected_project_type": "",
                "gold_expected_spatial_extent": "",
                "gold_expected_project_stage": "",
                "gold_expected_core_tension": "",
                "gold_expected_output_depth": "",
                "review_decision": "",
                "review_note": "",
            }
        )
    return rows


def write_review_workbench_artifacts(
    *,
    review_batch_path: Path,
    suggestions_path: Path,
    output_json: Path,
    output_csv: Path,
    output_md: Path,
) -> Dict[str, Any]:
    rows = build_review_workbench_rows(load_json(review_batch_path), load_json(suggestions_path))
    summary = {
        "total": len(rows),
        "ready_for_fast_review": sum(
            1 for row in rows if row.get("suggestion_decision") == "ready_for_fast_review"
        ),
        "needs_human_decision": sum(
            1 for row in rows if row.get("suggestion_decision") == "needs_human_decision"
        ),
        "gold_fields_are_blank": all(
            not str(row.get(field) or "").strip()
            for row in rows
            for field in _OBSERVED_FIELD_BY_GOLD_FIELD
        ),
    }
    report = {
        "schema_version": "scheme_advisor_golden_review_workbench.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_review_batch_path": str(review_batch_path),
        "source_suggestions_path": str(suggestions_path),
        "summary": summary,
        "items": rows,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["id"]
    with output_csv.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    output_md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 方案高参 Golden 复核工作单",
        "",
        f"- 来源批次：`{review_batch_path}`",
        f"- 建议来源：`{suggestions_path}`",
        f"- 总数：{summary['total']}",
        f"- 可快速复核：{summary['ready_for_fast_review']}",
        f"- 需人工裁决：{summary['needs_human_decision']}",
        "- 边界：人工确认后填写 `gold_expected_*`，不要直接把建议值当事实。",
        "",
        "## 复核清单",
        "",
        "| ID | 优先级 | 建议状态 | 候选类型 | 建议类型 | 人工填写类型 | 核心矛盾建议 | 人工填写核心矛盾 | 问题摘要 |",
        "|---:|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('id')} | {_md(row.get('review_priority'))} | "
            f"{_md(row.get('suggestion_decision'))} | {_md(row.get('candidate_project_type'))} | "
            f"{_md(row.get('suggested_gold_expected_project_type'))} | "
            f"{_md(row.get('gold_expected_project_type'))} | "
            f"{_md(row.get('suggested_gold_expected_core_tension'))} | "
            f"{_md(row.get('gold_expected_core_tension'))} | "
            f"{_md(str(row.get('prompt_excerpt') or '')[:80])} |"
        )
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def build_missing_gold_review_rows(
    quality_gate_report: Mapping[str, Any],
    review_workbench: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    """Filter a review workbench down to rows still blocking the quality gate."""

    workbench_by_id = {
        str(row.get("id")): row
        for row in review_workbench.get("items", []) or []
        if isinstance(row, Mapping) and row.get("id") is not None
    }

    rows: List[Dict[str, Any]] = []
    for missing in quality_gate_report.get("missing_gold_summary", []) or []:
        if not isinstance(missing, Mapping):
            continue
        item_id = str(missing.get("id") or "").strip()
        if not item_id:
            continue
        workbench_row = dict(workbench_by_id.get(item_id) or {"id": item_id})
        missing_fields = [
            str(field)
            for field in missing.get("missing_fields", []) or []
            if str(field).strip()
        ]
        workbench_row["id"] = item_id
        workbench_row["input_mode"] = str(missing.get("input_mode") or "project")
        workbench_row["missing_fields"] = "；".join(missing_fields)
        workbench_row["fields_to_fill"] = "；".join(missing_fields)
        workbench_row["fields_to_fill_zh"] = "；".join(
            _GOLD_FIELD_LABELS.get(field, field)
            for field in missing_fields
        )
        workbench_row["待填字段（中文）"] = workbench_row["fields_to_fill_zh"]
        workbench_row["field_review_guidance"] = "；".join(
            _GOLD_FIELD_REVIEW_GUIDANCE.get(field, "人工复核后填写。")
            for field in missing_fields
        )
        workbench_row["字段填写口径"] = workbench_row["field_review_guidance"]
        workbench_row["human_review_policy"] = (
            "候选值只作参考；必须人工确认后填写 gold_expected_* 字段，"
            "未确认不得同步为正式 Golden 标注。"
        )
        workbench_row["人工复核边界"] = workbench_row["human_review_policy"]
        workbench_row["next_action"] = str(
            missing.get("next_action")
            or "人工复核并填写缺失的黄金字段；不要直接采用系统建议值。"
        )
        rows.append(workbench_row)
    return rows


def write_missing_gold_review_artifacts(
    *,
    quality_gate_path: Path,
    review_workbench_path: Path,
    output_json: Path,
    output_csv: Path,
    output_md: Path,
) -> Dict[str, Any]:
    rows = build_missing_gold_review_rows(
        load_json(quality_gate_path),
        load_json(review_workbench_path),
    )
    summary = {
        "total": len(rows),
        "project_items": sum(1 for row in rows if row.get("input_mode") == "project"),
        "non_project_items": sum(1 for row in rows if row.get("input_mode") != "project"),
        "policy": "human_review_only_never_auto_fill_gold",
    }
    report = {
        "schema_version": "scheme_advisor_missing_gold_review_workbench.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_quality_gate_path": str(quality_gate_path),
        "source_review_workbench_path": str(review_workbench_path),
        "summary": summary,
        "items": rows,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _ordered_csv_fields(rows)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    output_md.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 方案高参待人工补齐 Golden 字段",
        "",
        f"- 质量门禁：`{quality_gate_path}`",
        f"- 来源工作台：`{review_workbench_path}`",
        f"- 待补条目：{summary['total']}",
        f"- 项目题：{summary['project_items']}",
        f"- 非项目题：{summary['non_project_items']}",
        "- 边界：只缩小人工复核范围，不自动填写 `gold_expected_*`。",
        "",
        "## 待补清单",
        "",
        "| ID | 输入类型 | 待填字段 | 待填字段（中文） | 候选核心矛盾 | 候选输出深度 | 问题摘要 | 下一步 |",
        "|---:|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('id')} | {_md(row.get('input_mode'))} | {_md(row.get('fields_to_fill'))} | "
            f"{_md(row.get('fields_to_fill_zh'))} | "
            f"{_md(row.get('suggested_gold_expected_core_tension') or row.get('candidate_core_tension'))} | "
            f"{_md(row.get('suggested_gold_expected_output_depth') or row.get('candidate_allowed_output_depth'))} | "
            f"{_md(str(row.get('prompt_excerpt') or '')[:90])} | {_md(row.get('next_action'))} |"
        )
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def _ordered_csv_fields(rows: List[Mapping[str, Any]]) -> List[str]:
    preferred = [
        "id",
        "input_mode",
        "missing_fields",
        "fields_to_fill",
        "fields_to_fill_zh",
        "待填字段（中文）",
        "field_review_guidance",
        "字段填写口径",
        "human_review_policy",
        "人工复核边界",
        "next_action",
        "prompt_excerpt",
        "candidate_project_type",
        "candidate_core_tension",
        "candidate_allowed_output_depth",
        "suggested_gold_expected_project_type",
        "suggested_gold_expected_core_tension",
        "suggested_gold_expected_output_depth",
        "gold_expected_project_type",
        "gold_expected_core_tension",
        "gold_expected_output_depth",
        "review_decision",
        "review_note",
    ]
    existing = {
        key
        for row in rows
        for key in row.keys()
    }
    ordered = [field for field in preferred if field in existing]
    ordered.extend(sorted(existing - set(ordered)))
    return ordered or ["id"]


def build_golden_verification_report(
    pressure_result: Mapping[str, Any],
    golden_annotation: Mapping[str, Any],
) -> Dict[str, Any]:
    """Compare filled gold_expected fields with matching pressure-result fields.

    Empty gold fields are ignored. If a gold field is filled but the current
    pressure result does not expose the corresponding observed field yet, the
    check is marked as skipped instead of failed. This lets the annotation table
    be introduced before every runtime metric is available.
    """

    pressure_by_id = {
        str(item.get("id")): item
        for item in pressure_result.get("items", []) or []
        if isinstance(item, Mapping) and item.get("id") is not None
    }

    rows: List[Dict[str, Any]] = []
    passed = 0
    failed = 0
    skipped = 0

    for annotation in golden_annotation.get("items", []) or []:
        if not isinstance(annotation, Mapping):
            continue
        expected_fields = _filled_expected_fields(annotation)
        if not expected_fields:
            continue

        item_id = str(annotation.get("id"))
        pressure_item = pressure_by_id.get(item_id) or {}
        checks: List[Dict[str, Any]] = []

        for gold_field, expected in expected_fields:
            observed_field = _OBSERVED_FIELD_BY_GOLD_FIELD[gold_field]
            observed = pressure_item.get(observed_field)
            if observed in (None, ""):
                skipped += 1
                checks.append(
                    {
                        "field": gold_field,
                        "observed_field": observed_field,
                        "expected": expected,
                        "observed": None,
                        "status": "skipped",
                        "reason": "observed field not present in pressure result",
                    }
                )
                continue
            if str(observed) == expected:
                passed += 1
                status = "pass"
            else:
                failed += 1
                status = "fail"
            checks.append(
                {
                    "field": gold_field,
                    "observed_field": observed_field,
                    "expected": expected,
                    "observed": observed,
                    "status": status,
                }
            )

        rows.append(
            {
                "id": annotation.get("id"),
                "status": _item_status(checks),
                "checks": checks,
            }
        )

    return {
        "schema_version": "scheme_advisor_golden_verification.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "golden_items": len(golden_annotation.get("items", []) or []),
            "active_gold_items": len(rows),
            "checks": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        },
        "items": rows,
    }


def build_golden_quality_gate_report(
    pressure_result: Mapping[str, Any],
    golden_annotation: Mapping[str, Any],
    *,
    required_item_ids: Iterable[Any],
    required_gold_fields: Iterable[str] = tuple(_OBSERVED_FIELD_BY_GOLD_FIELD.keys()),
) -> Dict[str, Any]:
    """Build a hard gate for reviewed high-risk golden samples.

    The normal verifier is permissive: it compares whatever human-filled gold
    fields exist and ignores empty fields. This gate is stricter for selected
    P0/P1 samples: required rows must have required gold fields, and those
    expectations must match the current pressure output.
    """

    required_ids = [str(item_id) for item_id in required_item_ids]
    required_fields = [
        str(field)
        for field in required_gold_fields
        if str(field) in _OBSERVED_FIELD_BY_GOLD_FIELD
    ]
    annotations_by_id = {
        str(item.get("id")): item
        for item in golden_annotation.get("items", []) or []
        if isinstance(item, Mapping) and item.get("id") is not None
    }
    pressure_by_id = {
        str(item.get("id")): item
        for item in pressure_result.get("items", []) or []
        if isinstance(item, Mapping) and item.get("id") is not None
    }
    verification = build_golden_verification_report(pressure_result, golden_annotation)
    verification_by_id = {
        str(item.get("id")): item
        for item in verification.get("items", []) or []
        if isinstance(item, Mapping) and item.get("id") is not None
    }

    failures: List[Dict[str, Any]] = []
    missing_gold_summary: List[Dict[str, Any]] = []
    missing_required_gold_by_field = {field: 0 for field in required_fields}
    missing_required_gold_fields = 0
    required_items_with_complete_gold = 0
    passed_checks = 0
    failed_checks = 0
    skipped_checks = 0

    for item_id in required_ids:
        annotation = annotations_by_id.get(item_id)
        pressure_item = pressure_by_id.get(item_id) or {}
        if not annotation:
            failures.append(
                {
                    "code": "required_gold_item_missing",
                    "id": _display_item_id(item_id),
                    "message": "Required golden annotation item is missing.",
                }
            )
            continue

        item_required_fields = _required_gold_fields_for_input_mode(
            required_fields,
            pressure_item=pressure_item,
        )
        missing_fields = [
            field
            for field in item_required_fields
            if not str(annotation.get(field) or "").strip()
        ]
        if missing_fields:
            missing_required_gold_fields += len(missing_fields)
            for field in missing_fields:
                missing_required_gold_by_field[field] = missing_required_gold_by_field.get(field, 0) + 1
            missing_gold_summary.append(
                {
                    "id": item_id,
                    "input_mode": str(pressure_item.get("input_mode") or "project"),
                    "missing_fields": missing_fields,
                    "next_action": "人工复核并填写缺失的黄金字段；不要直接采用系统建议值。",
                }
            )
            failures.append(
                {
                    "code": "required_gold_fields_missing",
                    "id": annotation.get("id"),
                    "missing_fields": missing_fields,
                    "message": "Required golden fields are not filled.",
                }
            )
            continue

        required_items_with_complete_gold += 1
        verification_item = verification_by_id.get(item_id)
        if not verification_item:
            failures.append(
                {
                    "code": "verification_item_missing",
                    "id": annotation.get("id"),
                    "message": "Required item was not checked by the verifier.",
                }
            )
            continue

        for check in verification_item.get("checks", []) or []:
            if check.get("field") not in item_required_fields:
                continue
            status = str(check.get("status") or "")
            if status == "pass":
                passed_checks += 1
            elif status == "fail":
                failed_checks += 1
                failures.append(
                    {
                        "code": "golden_mismatch",
                        "id": annotation.get("id"),
                        "field": check.get("field"),
                        "expected": check.get("expected"),
                        "observed": check.get("observed"),
                        "message": "Current pressure result does not match required golden expectation.",
                    }
                )
            elif status == "skipped":
                skipped_checks += 1
                failures.append(
                    {
                        "code": "required_observed_field_missing",
                        "id": annotation.get("id"),
                        "field": check.get("field"),
                        "observed_field": check.get("observed_field"),
                        "message": "Current pressure result lacks a field required by the golden gate.",
                    }
                )

    gate_status = "pass" if not failures else "fail"
    return {
        "schema_version": "scheme_advisor_golden_quality_gate.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "gate_status": gate_status,
            "required_items": len(required_ids),
            "required_items_with_complete_gold": required_items_with_complete_gold,
            "active_gold_items": verification.get("summary", {}).get("active_gold_items", 0),
            "required_fields": required_fields,
            "missing_required_gold_items": len(missing_gold_summary),
            "missing_required_gold_fields": missing_required_gold_fields,
            "missing_required_gold_by_field": missing_required_gold_by_field,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "skipped_checks": skipped_checks,
        },
        "failures": failures,
        "missing_gold_summary": missing_gold_summary,
        "verification_summary": verification.get("summary", {}),
    }


def _required_gold_fields_for_input_mode(
    required_fields: Iterable[str],
    *,
    pressure_item: Mapping[str, Any],
) -> List[str]:
    fields = [str(field) for field in required_fields]
    input_mode = str(pressure_item.get("input_mode") or "project")
    if input_mode in {"methodology", "decision_argument", "out_of_scope"}:
        return [field for field in fields if field != "gold_expected_project_type"]
    return fields


def build_review_completion_report(
    review_rows: Iterable[Mapping[str, Any]],
    *,
    required_gold_fields: Iterable[str],
) -> Dict[str, Any]:
    """Report which human review rows are still missing required gold fields."""

    rows = list(review_rows)
    required_fields = [str(field) for field in required_gold_fields if str(field).strip()]
    missing_by_field = {field: 0 for field in required_fields}
    incomplete_items: List[Dict[str, Any]] = []

    for row in rows:
        row_missing_fields = [
            field
            for field in required_fields
            if not str(row.get(field) or "").strip()
        ]
        if not row_missing_fields:
            continue
        for field in row_missing_fields:
            missing_by_field[field] += 1
        incomplete_items.append(
            {
                "id": row.get("id"),
                "missing_fields": row_missing_fields,
            }
        )

    incomplete_rows = len(incomplete_items)
    return {
        "schema_version": "scheme_advisor_golden_review_completion.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total_rows": len(rows),
            "complete_rows": len(rows) - incomplete_rows,
            "incomplete_rows": incomplete_rows,
            "required_fields": required_fields,
            "missing_by_field": missing_by_field,
        },
        "incomplete_items": incomplete_items,
    }


def write_report_json(report: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report_markdown(report: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = report.get("summary") or {}
    lines = [
        "# 方案高参黄金标注校验报告",
        "",
        f"- 生成时间：`{report.get('generated_at')}`",
        f"- 黄金标注总数：{summary.get('golden_items', 0)}",
        f"- 已填写黄金标注：{summary.get('active_gold_items', 0)}",
        f"- 已执行检查：{summary.get('checks', 0)}",
        f"- 通过：{summary.get('passed', 0)}",
        f"- 失败：{summary.get('failed', 0)}",
        f"- 跳过：{summary.get('skipped', 0)}",
        "",
        "## 明细",
        "",
        "| ID | 状态 | 字段 | 期望 | 当前 |",
        "|---:|---|---|---|---|",
    ]
    for item in report.get("items", []) or []:
        for check in item.get("checks", []) or []:
            lines.append(
                f"| {item.get('id')} | {check.get('status')} | {check.get('field')} | "
                f"{_md(check.get('expected'))} | {_md(check.get('observed'))} |"
            )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _filled_expected_fields(annotation: Mapping[str, Any]) -> List[tuple[str, str]]:
    fields: List[tuple[str, str]] = []
    for gold_field in _OBSERVED_FIELD_BY_GOLD_FIELD:
        value = str(annotation.get(gold_field) or "").strip()
        if value:
            fields.append((gold_field, value))
    return fields


def _classification_is_safe(item: Mapping[str, Any]) -> bool:
    confidence = _as_float(item.get("confidence"))
    warnings = str(item.get("warning_codes") or "")
    remediation_family = str(item.get("remediation_family") or "")
    current_project_type = str(item.get("current_project_type") or "").strip()
    if not current_project_type:
        return False
    if confidence < 0.7:
        return False
    if "low_classification_confidence" in warnings:
        return False
    if remediation_family == "类型边界低置信":
        return False
    return True


def _suggestion_note(item: Mapping[str, Any], classification_safe: bool) -> str:
    notes: List[str] = []
    confidence = _as_float(item.get("confidence"))
    warnings = str(item.get("warning_codes") or "")
    remediation_family = str(item.get("remediation_family") or "")
    if not classification_safe:
        if confidence < 0.7 or "low_classification_confidence" in warnings:
            notes.append("分类置信度不足，项目类型不得自动写入 gold")
        if remediation_family == "类型边界低置信":
            notes.append("类型边界低置信，需要人工判定父类与主轴")
    if "coverage_gap" in warnings:
        notes.append("存在 Registry 覆盖缺口")
    if "knowledge_gap_ticket" in warnings:
        notes.append("存在知识覆盖缺口")
    if "activation_pack_candidate" in warnings:
        notes.append("可能需要激活包候选")
    if not notes:
        notes.append("候选字段完整，可快速复核；建议仍需人工确认")
    notes.append("本建议不自动写入 golden")
    return "；".join(notes)


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _item_status(checks: Iterable[Mapping[str, Any]]) -> str:
    statuses = {str(check.get("status")) for check in checks}
    if "fail" in statuses:
        return "fail"
    if "pass" in statuses and "skipped" not in statuses:
        return "pass"
    if "pass" in statuses and "skipped" in statuses:
        return "partial"
    return "skipped"


def _display_item_id(item_id: str) -> Any:
    try:
        return int(item_id)
    except (TypeError, ValueError):
        return item_id


def _parse_comma_separated_arg(value: Any) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in str(value).split(",") if part.strip()]


def _required_item_ids_from_review_batch(review_batch: Mapping[str, Any], *, priority: str = "") -> List[str]:
    required_ids: List[str] = []
    priority_filter = str(priority or "").strip()
    for item in review_batch.get("items", []) or []:
        if not isinstance(item, Mapping):
            continue
        if priority_filter and str(item.get("review_priority") or "").strip() != priority_filter:
            continue
        item_id = item.get("id")
        if item_id is None or str(item_id).strip() == "":
            continue
        required_ids.append(str(item_id).strip())
    return required_ids


def _dedupe_preserve_order(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    deduped: List[str] = []
    for value in values:
        key = str(value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return deduped


def _md(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "｜")


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Verify Scheme Advisor pressure results against golden annotations.")
    parser.add_argument("--pressure", type=Path, default=_DEFAULT_PRESSURE)
    parser.add_argument("--golden", type=Path, default=_DEFAULT_GOLDEN)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=_DEFAULT_MD_OUTPUT)
    parser.add_argument("--review-csv", type=Path, default=None)
    parser.add_argument("--updated-golden-output", type=Path, default=_DEFAULT_APPLY_OUTPUT)
    parser.add_argument("--apply-report-output", type=Path, default=_DEFAULT_APPLY_REPORT)
    parser.add_argument("--quality-gate-output", type=Path, default=None)
    parser.add_argument("--required-item-ids", default="")
    parser.add_argument("--required-review-batch", type=Path, default=None)
    parser.add_argument("--required-review-priority", default="")
    parser.add_argument("--required-gold-fields", default="")
    parser.add_argument("--fail-on-quality-gate", action="store_true")
    args = parser.parse_args(argv)

    if args.review_csv:
        report = apply_review_csv_file(
            golden_path=args.golden,
            review_csv_path=args.review_csv,
            updated_golden_output=args.updated_golden_output,
            apply_report_output=args.apply_report_output,
        )
        print(json.dumps(report["summary"], ensure_ascii=False))
        return

    pressure = load_json(args.pressure)
    golden = load_json(args.golden)
    report = build_golden_verification_report(pressure, golden)
    write_report_json(report, args.output)
    write_report_markdown(report, args.markdown_output)

    required_item_ids = _parse_comma_separated_arg(args.required_item_ids)
    if args.required_review_batch:
        required_item_ids.extend(
            _required_item_ids_from_review_batch(
                load_json(args.required_review_batch),
                priority=args.required_review_priority,
            )
        )
    required_item_ids = _dedupe_preserve_order(required_item_ids)
    quality_gate_output = args.quality_gate_output
    summary = dict(report["summary"])
    if quality_gate_output or required_item_ids:
        quality_gate_output = quality_gate_output or _DEFAULT_QUALITY_GATE_OUTPUT
        required_gold_fields = _parse_comma_separated_arg(args.required_gold_fields) or list(
            _OBSERVED_FIELD_BY_GOLD_FIELD.keys()
        )
        quality_gate_report = build_golden_quality_gate_report(
            pressure,
            golden,
            required_item_ids=required_item_ids,
            required_gold_fields=required_gold_fields,
        )
        quality_gate_report["source_pressure_path"] = str(args.pressure)
        quality_gate_report["source_golden_path"] = str(args.golden)
        write_report_json(quality_gate_report, quality_gate_output)
        summary["quality_gate_status"] = quality_gate_report["summary"]["gate_status"]
        summary["quality_gate_output"] = str(quality_gate_output)

    print(json.dumps(summary, ensure_ascii=False))
    if args.fail_on_quality_gate and summary.get("quality_gate_status") == "fail":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
