"""Generate governed activation-pack scope drafts from pressure-test backlog.

This module deliberately writes review drafts only. It must not create or edit
runtime activation pack YAML files under knowledge_base/activation_packs.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_BACKLOG = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-pressure-optimization-backlog-2026-03-22.json"
)
_DEFAULT_PRESSURE = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-pressure-test-2026-03-22.json"
)
_DEFAULT_JSON_OUTPUT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-activation-pack-scope-drafts-2026-03-22.json"
)
_DEFAULT_MARKDOWN_OUTPUT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-activation-pack-scope-drafts-2026-03-22.md"
)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_scope_draft_report(
    backlog: Mapping[str, Any],
    pressure_result: Mapping[str, Any],
    *,
    max_drafts: int = 2,
) -> Dict[str, Any]:
    items_by_id = {
        item.get("id"): item
        for item in pressure_result.get("items") or []
        if isinstance(item, Mapping)
    }
    ready_rows = [
        row
        for row in backlog.get("activation_pack_priority_queue") or []
        if row.get("readiness_band") == "ready_for_scope"
    ][:max_drafts]

    return {
        "schema_version": "activation_pack_scope_draft_report.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_backlog": str(_DEFAULT_BACKLOG),
        "source_pressure_result": str(_DEFAULT_PRESSURE),
        "governance_boundary": {
            "runtime_load_allowed": False,
            "formal_pack_write_allowed": False,
            "human_review_required": True,
            "rule": "本报告只生成激活包范围草案，不自动写入正式 Registry、知识库或运行时激活包。",
        },
        "drafts": [
            _build_single_scope_draft(row, items_by_id)
            for row in ready_rows
        ],
    }


def write_scope_draft_json(report: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_scope_draft_markdown(report: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 激活包范围草案",
        "",
        f"- 生成时间: `{report.get('generated_at')}`",
        "- 边界: 本文件不是正式运行时激活包，不会被运行时加载。",
        "- 规则: 草案必须经人工复核后，才能另行转写为正式激活包 YAML。",
        "",
        "## 治理边界",
        "",
        f"- runtime_load_allowed: `{report.get('governance_boundary', {}).get('runtime_load_allowed')}`",
        f"- formal_pack_write_allowed: `{report.get('governance_boundary', {}).get('formal_pack_write_allowed')}`",
        f"- human_review_required: `{report.get('governance_boundary', {}).get('human_review_required')}`",
        "",
    ]

    drafts = list(report.get("drafts") or [])
    if not drafts:
        lines.extend(["## 草案", "", "无。"])
    for draft in drafts:
        lines.extend(_draft_markdown_lines(draft))

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_single_scope_draft(
    row: Mapping[str, Any],
    items_by_id: Mapping[Any, Mapping[str, Any]],
) -> Dict[str, Any]:
    project_type = str(row.get("project_type") or "-")
    space_axis_id = str(row.get("space_axis_id") or "unclassified_axis")
    sample_ids = list(row.get("sample_ids") or [])
    sample_prompts = [
        {
            "id": sample_id,
            "prompt_excerpt": str((items_by_id.get(sample_id) or {}).get("prompt") or "")[:180],
        }
        for sample_id in sample_ids[:8]
    ]

    return {
        "draft_id": f"activation_scope_draft.{project_type}.{space_axis_id}",
        "schema_version": "activation_pack_scope_draft.v1",
        "status": "draft_needs_human_review",
        "runtime_load_allowed": False,
        "project_type": project_type,
        "space_axis_id": space_axis_id,
        "space_axis_label": row.get("space_axis_label") or "-",
        "sample_count": row.get("sample_count") or 0,
        "sample_ids": sample_ids,
        "sample_prompts": sample_prompts,
        "average_confidence": row.get("average_confidence"),
        "priority_score": row.get("priority_score"),
        "scope_hypothesis": _scope_hypothesis(project_type, space_axis_id, row.get("space_axis_label")),
        "must_define_sections": [
            "routing_boundary",
            "assumptions",
            "non_goals",
            "required_slots",
            "type_method_profile",
            "risk_control",
            "knowledge_recall_plan",
            "regression_samples",
        ],
        "minimum_review_gates": [
            "确认是否确实需要正式激活包，而不是继续使用基础空间推理框架。",
            "确认适用边界、不适用边界和父级项目类型，不得扩大到所有相邻空间。",
            "补齐 required_slots、risk_control 和最小知识卡清单后，才能转写正式激活包。",
            "正式激活包上线前必须通过激活包校验器、190 条压力测试和用户侧文案守门。",
        ],
        "next_action": "组织人工复核会，先裁定范围和不适用边界，再决定是否进入正式激活包编写。",
    }


def _scope_hypothesis(project_type: str, space_axis_id: str, space_axis_label: Any) -> str:
    label = str(space_axis_label or space_axis_id or "该空间主轴")
    return (
        f"围绕 `{project_type}` 下的 `{space_axis_id}` 聚类，先定义“{label}”的"
        "适用项目边界、核心追问、风险红线和最小知识召回范围。"
    )


def _draft_markdown_lines(draft: Mapping[str, Any]) -> List[str]:
    lines = [
        f"## {draft.get('draft_id')}",
        "",
        f"- 状态: `{draft.get('status')}`",
        f"- 项目类型: `{draft.get('project_type')}`",
        f"- 空间主轴: `{draft.get('space_axis_id')}` / {draft.get('space_axis_label')}",
        f"- 样本数: {draft.get('sample_count')}",
        f"- 平均置信度: {draft.get('average_confidence')}",
        f"- 优先级分数: {draft.get('priority_score')}",
        f"- 运行时可加载: `{draft.get('runtime_load_allowed')}`",
        "",
        "### 范围假设",
        "",
        str(draft.get("scope_hypothesis") or "-"),
        "",
        "### 必须补齐的定义",
        "",
    ]
    lines.extend(f"- `{section}`" for section in draft.get("must_define_sections") or [])
    lines.extend(["", "### 最小复核门槛", ""])
    lines.extend(f"- {gate}" for gate in draft.get("minimum_review_gates") or [])
    lines.extend(["", "### 样本摘录", ""])
    for sample in draft.get("sample_prompts") or []:
        lines.append(f"- {sample.get('id')}: {sample.get('prompt_excerpt')}")
    lines.append("")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Build governed activation-pack scope drafts.")
    parser.add_argument("--backlog", type=Path, default=_DEFAULT_BACKLOG)
    parser.add_argument("--pressure", type=Path, default=_DEFAULT_PRESSURE)
    parser.add_argument("--json-output", type=Path, default=_DEFAULT_JSON_OUTPUT)
    parser.add_argument("--output", type=Path, default=_DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--max-drafts", type=int, default=2)
    args = parser.parse_args()

    report = build_scope_draft_report(
        load_json(args.backlog),
        load_json(args.pressure),
        max_drafts=args.max_drafts,
    )
    write_scope_draft_json(report, args.json_output)
    write_scope_draft_markdown(report, args.output)
    print(json.dumps({
        "draft_count": len(report.get("drafts") or []),
        "runtime_load_allowed": report["governance_boundary"]["runtime_load_allowed"],
        "formal_pack_write_allowed": report["governance_boundary"]["formal_pack_write_allowed"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
