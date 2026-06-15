"""Build human-review checklists for activation-pack scope drafts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping


_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SCOPE_DRAFTS = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-activation-pack-scope-drafts-2026-03-22.json"
)
_DEFAULT_JSON_OUTPUT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-activation-pack-review-checklist-2026-03-22.json"
)
_DEFAULT_MARKDOWN_OUTPUT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-activation-pack-review-checklist-2026-03-22.md"
)


_ALLOWED_DECISIONS = [
    "approve_for_formal_pack_authoring",
    "request_more_evidence",
    "keep_observing",
    "reject_scope",
]


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_review_checklist(scope_draft_report: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": "activation_pack_scope_review_checklist.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_scope_draft_report": str(_DEFAULT_SCOPE_DRAFTS),
        "governance_boundary": {
            "runtime_load_allowed": False,
            "formal_pack_write_allowed": False,
            "human_review_required": True,
            "rule": "本清单只服务人工裁决，不得自动写入正式激活包、Registry 或知识库。",
        },
        "allowed_decisions": list(_ALLOWED_DECISIONS),
        "review_items": [
            _build_review_item(draft)
            for draft in scope_draft_report.get("drafts") or []
            if isinstance(draft, Mapping)
        ],
    }


def write_review_checklist_json(checklist: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(checklist, ensure_ascii=False, indent=2), encoding="utf-8")


def write_review_checklist_markdown(checklist: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 激活包范围草案人工复核清单",
        "",
        f"- 生成时间: `{checklist.get('generated_at')}`",
        "- 边界: 本清单不得自动写入正式激活包、Registry 或知识库。",
        "- 复核结果只能作为人工裁决记录；正式包编写必须另走激活包校验流程。",
        "",
        "## 可选裁决",
        "",
    ]
    for decision in checklist.get("allowed_decisions") or []:
        lines.append(f"- `{decision}`")

    lines.extend(["", "## 复核项", ""])
    review_items = list(checklist.get("review_items") or [])
    if not review_items:
        lines.append("无。")
    for item in review_items:
        lines.extend(_review_item_markdown_lines(item))

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_review_item(draft: Mapping[str, Any]) -> Dict[str, Any]:
    blockers = _promotion_blockers(draft)
    return {
        "draft_id": draft.get("draft_id"),
        "project_type": draft.get("project_type"),
        "space_axis_id": draft.get("space_axis_id"),
        "space_axis_label": draft.get("space_axis_label"),
        "sample_count": draft.get("sample_count") or 0,
        "average_confidence": draft.get("average_confidence"),
        "priority_score": draft.get("priority_score"),
        "default_decision": "reject_scope" if blockers else "request_more_evidence",
        "required_review_roles": [
            "domain_expert",
            "knowledge_architect",
            "product_owner",
        ],
        "promotion_blockers": blockers,
        "checkpoints": _checkpoints(draft),
        "decision_record_template": {
            "decision": None,
            "reviewer": None,
            "reviewed_at": None,
            "reason": None,
            "required_changes": [],
        },
    }


def _promotion_blockers(draft: Mapping[str, Any]) -> List[str]:
    blockers: List[str] = []
    if draft.get("runtime_load_allowed") is not False:
        blockers.append("runtime_load_allowed_must_be_false")
    if not draft.get("draft_id"):
        blockers.append("draft_id_required")
    if not draft.get("project_type"):
        blockers.append("project_type_required")
    if not draft.get("space_axis_id"):
        blockers.append("space_axis_id_required")
    if not draft.get("must_define_sections"):
        blockers.append("must_define_sections_required")
    return blockers


def _checkpoints(draft: Mapping[str, Any]) -> List[str]:
    must_define = ", ".join(str(item) for item in draft.get("must_define_sections") or [])
    gates = "；".join(str(item) for item in draft.get("minimum_review_gates") or [])
    return [
        "适用边界是否足够窄，是否能说明哪些项目可以使用这个激活包。",
        "不适用边界是否明确，是否能防止相邻空间被误激活。",
        "父级项目类型、空间主轴和样本证据是否一致。",
        f"必须补齐的定义是否完整：{must_define or '未提供'}。",
        "required_slots 是否能支持首轮问诊，不会暴露内部术语给终端用户。",
        "risk_control 是否覆盖安全、法规、机电、运营或知识覆盖封顶风险。",
        "knowledge_recall_plan 是否只调用审核通过的知识卡，不直接召回原始研究长文。",
        f"最小复核门槛是否可执行：{gates or '未提供'}。",
    ]


def _review_item_markdown_lines(item: Mapping[str, Any]) -> List[str]:
    lines = [
        f"### {item.get('draft_id')}",
        "",
        f"- 项目类型: `{item.get('project_type')}`",
        f"- 空间主轴: `{item.get('space_axis_id')}` / {item.get('space_axis_label')}",
        f"- 样本数: {item.get('sample_count')}",
        f"- 平均置信度: {item.get('average_confidence')}",
        f"- 默认裁决: `{item.get('default_decision')}`",
        f"- 复核角色: {', '.join(str(role) for role in item.get('required_review_roles') or [])}",
        f"- 阻断项: {', '.join(str(blocker) for blocker in item.get('promotion_blockers') or []) or '无'}",
        "",
        "#### 检查点",
        "",
    ]
    lines.extend(f"- {checkpoint}" for checkpoint in item.get("checkpoints") or [])
    lines.extend([
        "",
        "#### 裁决记录模板",
        "",
        "- decision:",
        "- reviewer:",
        "- reviewed_at:",
        "- reason:",
        "- required_changes:",
        "",
    ])
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Build activation-pack scope review checklist.")
    parser.add_argument("--scope-drafts", type=Path, default=_DEFAULT_SCOPE_DRAFTS)
    parser.add_argument("--json-output", type=Path, default=_DEFAULT_JSON_OUTPUT)
    parser.add_argument("--output", type=Path, default=_DEFAULT_MARKDOWN_OUTPUT)
    args = parser.parse_args()

    checklist = build_review_checklist(load_json(args.scope_drafts))
    write_review_checklist_json(checklist, args.json_output)
    write_review_checklist_markdown(checklist, args.output)
    print(json.dumps({
        "review_item_count": len(checklist.get("review_items") or []),
        "runtime_load_allowed": checklist["governance_boundary"]["runtime_load_allowed"],
        "formal_pack_write_allowed": checklist["governance_boundary"]["formal_pack_write_allowed"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
