"""Build actionable optimization backlogs from Scheme Advisor pressure results."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_INPUT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-pressure-test-2026-03-22.json"
)
_DEFAULT_OUTPUT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-pressure-optimization-backlog-2026-03-22.md"
)
_DEFAULT_JSON_OUTPUT = (
    _ROOT
    / "docs"
    / "system-completeness-audit"
    / "scheme-advisor-pressure-optimization-backlog-2026-03-22.json"
)


def load_pressure_result(path: Path = _DEFAULT_INPUT) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_optimization_backlog(pressure_result: Dict[str, Any]) -> Dict[str, Any]:
    items = list(pressure_result.get("items") or [])
    low_confidence = _low_confidence_samples(items)
    coverage_gap = _group_warning_by_type(
        items,
        "coverage_gap",
        "补 Registry 覆盖、Type Alias 和边界样本",
        metadata={
            "candidate_kind": "registry_boundary_candidate",
            "governance_mode": "registry_governed",
            "review_queue": "space_registry_review",
            "promotion_rule": "human_review_required",
            "verification_gate": "补充候选后必须跑 190 条回归压测，不得新增低置信或错误路由。",
        },
    )
    knowledge_gap = _group_warning_by_type(
        items,
        "knowledge_gap_ticket",
        "生成候选知识卡，进入人工审核后再批准入库",
        metadata={
            "candidate_kind": "knowledge_card_candidate",
            "governance_mode": "knowledge_governed",
            "review_queue": "knowledge_asset_review",
            "promotion_rule": "human_review_required",
            "verification_gate": "候选卡必须有来源、适用边界和不可使用边界；审核通过前不得进入 runtime recall。",
        },
    )
    activation_pack = _group_issue_by_type(
        items,
        "activation_pack_candidate",
        "进入激活包候选池，按高频和业务价值排期",
        bucket="governance_signals",
        metadata={
            "candidate_kind": "activation_pack_candidate",
            "governance_mode": "knowledge_governed",
            "review_queue": "activation_pack_review",
            "promotion_rule": "frequency_and_value_then_human_review",
            "verification_gate": "激活包候选必须先证明高频、商业价值和知识成熟度，再由人工批准上线。",
        },
    )
    activation_pack_priority_queue = _activation_pack_priority_queue(items)
    knowledge_coverage_watch = _group_issue_by_type(
        items,
        "knowledge_coverage_watch",
        "保留在基础空间推理框架观察池，继续累计样本；暂不直接立项建设专科激活包。",
        bucket="governance_signals",
        metadata={
            "candidate_kind": "coverage_watch_signal",
            "governance_mode": "runtime_rule",
            "review_queue": "coverage_watch_pool",
            "promotion_rule": "aggregate_before_candidate",
            "verification_gate": "观察池只累计信号；达到频次、风险等级或商业价值门槛后才生成 Registry 或知识候选。",
        },
    )
    warning_counts = Counter(
        issue.get("code")
        for item in items
        for issue in item.get("warning_issues") or []
        if issue.get("code")
    )
    governance_signal_counts = Counter(
        issue.get("code")
        for item in items
        for issue in item.get("governance_signals") or []
        if issue.get("code")
    )

    return {
        "schema_version": "scheme_advisor_pressure_optimization_backlog.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_summary": pressure_result.get("summary") or {},
        "summary": {
            "low_confidence_samples": len(low_confidence),
            "coverage_gap_types": len(coverage_gap),
            "knowledge_gap_types": len(knowledge_gap),
            "activation_pack_candidate_types": len(activation_pack),
            "activation_pack_ready_clusters": sum(
                1
                for row in activation_pack_priority_queue
                if row.get("readiness_band") == "ready_for_scope"
            ),
            "activation_pack_candidate_clusters": sum(
                1
                for row in activation_pack_priority_queue
                if row.get("readiness_band") == "candidate_pool"
            ),
            "activation_pack_observe_clusters": sum(
                1
                for row in activation_pack_priority_queue
                if row.get("readiness_band") == "observe_only"
            ),
            "knowledge_coverage_watch_types": len(knowledge_coverage_watch),
            "warning_counts": dict(warning_counts),
            "governance_signal_counts": dict(governance_signal_counts),
        },
        "governance_boundary": {
            "allowed_here": [
                "生成候选清单",
                "补回归测试",
                "补 Type Alias 候选",
                "补 Registry 候选",
                "生成知识卡草稿",
            ],
            "requires_human_review": [
                "正式新增项目类型或子域",
                "正式批准知识卡",
                "正式上线 Activation Pack",
                "将模型推断写入运行时事实",
            ],
            "rule": "不得自动写入正式 Registry 或知识库；候选必须人工复核后沉淀。",
        },
        "low_confidence_samples": low_confidence,
        "coverage_gap_by_type": coverage_gap,
        "knowledge_gap_by_type": knowledge_gap,
        "activation_pack_priority_queue": activation_pack_priority_queue,
        "activation_pack_candidates": activation_pack,
        "knowledge_coverage_watch": knowledge_coverage_watch,
    }


def write_backlog_markdown(backlog: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    source_summary = backlog.get("source_summary") or {}
    summary = backlog.get("summary") or {}
    lines = [
        "# 方案高参压测优化待办清单",
        "",
        f"- 生成时间: `{backlog.get('generated_at')}`",
        f"- 压测总数: {source_summary.get('total', '-')}",
        f"- 压测通过: {source_summary.get('passed', '-')}",
        f"- 阻断失败: {source_summary.get('failed', '-')}",
        f"- 有告警样本: {source_summary.get('with_warnings', '-')}",
        "",
        "## 治理边界",
        "",
        "- 可以在这里做：生成候选清单、补回归测试、补 Type Alias 候选、补 Registry 候选、生成知识卡草稿。",
        "- 需要人工复核：正式新增项目类型或子域、正式批准知识卡、正式上线 Activation Pack、将模型推断写入运行时事实。",
        "- 硬边界：不得自动写入正式 Registry 或知识库；候选必须人工复核后沉淀。",
        "",
        "## 总览",
        "",
        "| 项目 | 数量 | 优先级 |",
        "|---|---:|---|",
        f"| 低置信样本复核 | {summary.get('low_confidence_samples', 0)} | P0 |",
        f"| Registry 覆盖缺口类型 | {summary.get('coverage_gap_types', 0)} | P1 |",
        f"| 知识缺口类型 | {summary.get('knowledge_gap_types', 0)} | P1 |",
        f"| 激活包候选类型 | {summary.get('activation_pack_candidate_types', 0)} | P2 |",
        f"| 激活包可优先定义聚类 | {summary.get('activation_pack_ready_clusters', 0)} | P2 |",
        "",
        "## P0 低置信样本复核",
        "",
    ]
    _append_low_confidence_table(lines, backlog.get("low_confidence_samples") or [])
    lines.extend(["", "## P1 Registry 覆盖缺口", ""])
    _append_group_table(lines, backlog.get("coverage_gap_by_type") or [])
    lines.extend(["", "## P1 知识缺口候选", ""])
    _append_group_table(lines, backlog.get("knowledge_gap_by_type") or [])
    lines.extend(["", "## P2 激活包建设优先队列", ""])
    _append_activation_priority_table(lines, backlog.get("activation_pack_priority_queue") or [])
    lines.extend(["", "## P2 激活包候选", ""])
    _append_group_table(lines, backlog.get("activation_pack_candidates") or [])
    lines.extend(["", "## P3 基础框架观察池", ""])
    _append_group_table(lines, backlog.get("knowledge_coverage_watch") or [])
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_backlog_json(backlog: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(backlog, ensure_ascii=False, indent=2), encoding="utf-8")


def _low_confidence_samples(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    samples: List[Dict[str, Any]] = []
    for item in items:
        if not _has_warning(item, "low_classification_confidence"):
            continue
        confidence = _as_float(item.get("confidence"))
        prompt = str(item.get("prompt") or "")
        samples.append(
            {
                "id": item.get("id"),
                "project_type": item.get("project_type") or "-",
                "confidence": confidence,
                "priority": "P0",
                "suspected_issue": _suspected_issue(prompt),
                "recommended_action": _low_confidence_action(prompt),
                "requires_human_review": True,
                "prompt_excerpt": prompt[:140],
            }
        )
    return sorted(samples, key=lambda item: ((item.get("confidence") is None), item.get("confidence") or 1, item.get("id") or 0))


def _group_warning_by_type(
    items: Iterable[Dict[str, Any]],
    warning_code: str,
    recommended_action: str,
    *,
    metadata: Dict[str, str] | None = None,
) -> List[Dict[str, Any]]:
    return _group_issue_by_type(
        items,
        warning_code,
        recommended_action,
        bucket=("warning_issues", "governance_signals"),
        metadata=metadata,
    )


def _group_issue_by_type(
    items: Iterable[Dict[str, Any]],
    issue_code: str,
    recommended_action: str,
    *,
    bucket: str | Iterable[str],
    metadata: Dict[str, str] | None = None,
) -> List[Dict[str, Any]]:
    metadata = metadata or {}
    buckets = [bucket] if isinstance(bucket, str) else list(bucket)
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in items:
        if any(_has_issue(item, issue_code, bucket=current_bucket) for current_bucket in buckets):
            grouped[str(item.get("project_type") or "-")].append(item)

    rows: List[Dict[str, Any]] = []
    for project_type, grouped_items in grouped.items():
        rows.append(
            {
                "project_type": project_type,
                "count": len(grouped_items),
                "sample_ids": [item.get("id") for item in grouped_items[:12]],
                "recommended_action": recommended_action,
                "requires_human_review": True,
                **metadata,
            }
        )
    return sorted(rows, key=lambda item: (-item["count"], item["project_type"]))


def _activation_pack_priority_queue(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for item in items:
        if not _has_issue(item, "activation_pack_candidate", bucket="governance_signals"):
            continue
        project_type = str(item.get("project_type") or "-")
        space_axis_id = str(item.get("space_axis_id") or "unclassified_axis")
        grouped[(project_type, space_axis_id)].append(item)

    rows: List[Dict[str, Any]] = []
    for (project_type, space_axis_id), grouped_items in grouped.items():
        confidences = [
            value
            for value in (_as_float(item.get("confidence")) for item in grouped_items)
            if value is not None
        ]
        average_confidence = round(sum(confidences) / len(confidences), 3) if confidences else None
        sample_count = len(grouped_items)
        readiness = _activation_pack_readiness(sample_count, average_confidence)
        rows.append(
            {
                "project_type": project_type,
                "space_axis_id": space_axis_id,
                "space_axis_label": _most_common_text(
                    str(item.get("space_axis_label") or "") for item in grouped_items
                ),
                "sample_count": sample_count,
                "sample_ids": [item.get("id") for item in grouped_items[:12]],
                "average_confidence": average_confidence,
                "priority_score": _activation_pack_priority_score(sample_count, average_confidence),
                "readiness_band": readiness["band"],
                "readiness_label": readiness["label"],
                "recommended_action": readiness["action"],
                "requires_human_review": True,
                "promotion_rule": "frequency_confidence_axis_then_human_review",
                "verification_gate": "先定义包边界、适用/不适用条件和回归样本；人工批准前不得上线运行时激活包。",
            }
        )
    return sorted(
        rows,
        key=lambda item: (
            -int(item.get("priority_score") or 0),
            -int(item.get("sample_count") or 0),
            str(item.get("project_type") or ""),
            str(item.get("space_axis_id") or ""),
        ),
    )


def _activation_pack_readiness(sample_count: int, average_confidence: float | None) -> Dict[str, str]:
    confidence = average_confidence or 0.0
    if sample_count >= 6 and confidence >= 0.7:
        return {
            "band": "ready_for_scope",
            "label": "优先定义包范围",
            "action": "先做激活包范围定义、适用边界、核心追问和最小知识卡清单。",
        }
    if sample_count >= 3 and confidence >= 0.65:
        return {
            "band": "candidate_pool",
            "label": "候选池继续补证",
            "action": "继续补同类样本、边界样本和知识卡证据，暂不直接上线。",
        }
    return {
        "band": "observe_only",
        "label": "继续观察",
        "action": "只保留为观察信号，等待更多同类样本或更稳定分类证据。",
    }


def _activation_pack_priority_score(sample_count: int, average_confidence: float | None) -> int:
    confidence = average_confidence or 0.0
    frequency_score = min(sample_count, 12) * 10
    confidence_score = round(confidence * 20)
    return int(frequency_score + confidence_score)


def _most_common_text(values: Iterable[str]) -> str:
    cleaned = [value for value in values if value]
    if not cleaned:
        return "-"
    return Counter(cleaned).most_common(1)[0][0]


def _has_warning(item: Dict[str, Any], code: str) -> bool:
    return _has_issue(item, code, bucket="warning_issues")


def _has_issue(item: Dict[str, Any], code: str, *, bucket: str) -> bool:
    return any(issue.get("code") == code for issue in item.get(bucket) or [])


def _suspected_issue(prompt: str) -> str:
    text = prompt.lower()
    if any(key in text for key in ["研究中心", "实验室", "ai", "伦理", "神经科学", "行为经济学"]):
        return "跨学科/研究型空间边界不足"
    if any(key in text for key in ["地下", "极地", "火山", "干旱", "灾难", "未来城市"]):
        return "极端环境或未来场景类型覆盖不足"
    if any(key in text for key in ["夫妻", "家庭", "宠物", "儿童", "主卧", "住宅"]):
        return "居住子域和人物情绪场景别名不足"
    if any(key in text for key in ["诊所", "牙科", "医疗", "康养", "疗愈"]):
        return "医疗康养子域边界样本不足"
    if any(key in text for key in ["城市更新", "旧厂", "老街", "社区", "新区"]):
        return "城市更新/社区/规划边界不足"
    return "类型别名、边界样本或复合类型规则不足"


def _low_confidence_action(prompt: str) -> str:
    suspected = _suspected_issue(prompt)
    if "跨学科" in suspected:
        return "补跨学科空间 Type Alias、研究型空间边界样本，并复核是否需要新增子域候选。"
    if "极端环境" in suspected:
        return "补极端环境场景词和 special_function / research / resilience 边界测试。"
    if "居住" in suspected:
        return "补住宅人物画像、情绪修复、宠物/儿童/家庭结构子域别名。"
    if "医疗康养" in suspected:
        return "补诊所、牙科、康养、疗愈空间的子域 alias 和正反例。"
    if "城市更新" in suspected:
        return "补城市更新、产业园、老街区、社区改造的 Registry 边界样本。"
    return "先人工复核正确类型，再决定补 Type Alias、Registry 候选或复合类型规则。"


def _append_low_confidence_table(lines: List[str], samples: List[Dict[str, Any]]) -> None:
    if not samples:
        lines.append("无。")
        return
    lines.extend(
        [
            "| 编号 | 当前类型 | 置信度 | 疑似问题 | 建议动作 | 问题摘要 |",
            "|---:|---|---:|---|---|---|",
        ]
    )
    for item in samples:
        lines.append(
            "| {id} | {ptype} | {confidence} | {issue} | {action} | {prompt} |".format(
                id=item.get("id"),
                ptype=_cell(item.get("project_type")),
                confidence="" if item.get("confidence") is None else item.get("confidence"),
                issue=_cell(item.get("suspected_issue")),
                action=_cell(item.get("recommended_action")),
                prompt=_cell(item.get("prompt_excerpt")),
            )
        )


def _append_group_table(lines: List[str], rows: List[Dict[str, Any]]) -> None:
    if not rows:
        lines.append("无。")
        return
    lines.extend([
        "| 类型 | 数量 | 样本编号 | 候选类型 | 审核队列 | 治理方式 | 晋级规则 | 验证门槛 | 建议动作 |",
        "|---|---:|---|---|---|---|---|---|---|",
    ])
    for row in rows:
        lines.append(
            "| {ptype} | {count} | {ids} | {kind} | {queue} | {mode} | {rule} | {gate} | {action} |".format(
                ptype=_cell(row.get("project_type")),
                count=row.get("count"),
                ids=", ".join(str(item) for item in row.get("sample_ids") or []),
                kind=_cell(row.get("candidate_kind")),
                queue=_cell(row.get("review_queue")),
                mode=_cell(row.get("governance_mode")),
                rule=_cell(row.get("promotion_rule")),
                gate=_cell(row.get("verification_gate")),
                action=_cell(row.get("recommended_action")),
            )
        )


def _append_activation_priority_table(lines: List[str], rows: List[Dict[str, Any]]) -> None:
    if not rows:
        lines.append("无。")
        return
    lines.extend([
        "| 排名 | 类型 | 空间主轴 | 样本数 | 平均置信度 | 分数 | 成熟度 | 样本编号 | 建议动作 |",
        "|---:|---|---|---:|---:|---:|---|---|---|",
    ])
    for index, row in enumerate(rows, start=1):
        lines.append(
            "| {rank} | {ptype} | {axis} | {count} | {confidence} | {score} | {label} | {ids} | {action} |".format(
                rank=index,
                ptype=_cell(row.get("project_type")),
                axis=_cell(row.get("space_axis_id")),
                count=row.get("sample_count"),
                confidence="" if row.get("average_confidence") is None else row.get("average_confidence"),
                score=row.get("priority_score"),
                label=_cell(row.get("readiness_label")),
                ids=", ".join(str(item) for item in row.get("sample_ids") or []),
                action=_cell(row.get("recommended_action")),
            )
        )


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _cell(value: Any) -> str:
    return str(value or "-").replace("|", "\\|").replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Scheme Advisor pressure optimization backlog.")
    parser.add_argument("--input", type=Path, default=_DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    parser.add_argument("--json-output", type=Path, default=_DEFAULT_JSON_OUTPUT)
    args = parser.parse_args()

    backlog = build_optimization_backlog(load_pressure_result(args.input))
    write_backlog_markdown(backlog, args.output)
    write_backlog_json(backlog, args.json_output)
    print(json.dumps(backlog["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
