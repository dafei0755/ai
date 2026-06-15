"""Service-level pressure runner for Scheme Advisor simulation prompts."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .scheme_advisor_entry_service import SchemeAdvisorEntryService
from .scheme_advisor_semantic_axes import (
    derive_semantic_axes as _shared_derive_semantic_axes,
    evaluate_semantic_alignment as _shared_evaluate_semantic_alignment,
    load_semantic_axis_registry as _shared_load_semantic_axis_registry,
    rank_main_tensions as _shared_rank_main_tensions,
)


_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PROMPT_DIR = _ROOT / "sf" / "2026.3.22"
_INTERNAL_TERMS = [
    "context_packet",
    "knowledge_package",
    "ontology",
    "back_of_house",
    "traffic_node_conversion",
    "payback_model_inputs",
    "本体槽位",
    "知识包",
    "风险阈值",
    "预算押注",
    "决策级变量",
]
_FORMAL_ACTIVATION_PACK_SUBDOMAINS = {"tea_drink_store", "coffee_shop"}
_ACTIVATION_PACK_CANDIDATE_MIN_GROUP_SIZE = 3
_DISPLAY_SAFETY_ISSUE_CODES = {
    "english_key_visible",
    "generic_step_title_visible",
    "internal_terms_visible",
}
_QUESTION_QUALITY_ISSUE_CODES = {
    "commercial_template_leakage",
    "wrong_domain_reference",
    "core_subject_missing",
    "core_driver_missing",
}
_QUALITY_ISSUE_COUNTER_KEYS = [
    "wrong_domain_reference",
    "english_key_visible",
    "generic_step_title_visible",
    "core_subject_missing",
    "low_classification_confidence",
    "knowledge_coverage_gap",
]
_CORE_TENSION_AXIS_WEIGHTS = {
    "critical_constraints": 24,
    "subject_profiles": 22,
    "founding_drivers": 20,
    "spatial_design_drivers": 16,
    "site_resources": 10,
    "lifecycle": 8,
    "space_domains": 4,
}
_LOW_SIGNAL_CORE_TERMS = {
    "住宅",
    "别墅",
    "公寓",
    "家庭",
    "空间",
    "心理",
    "富人区",
    "完整",
    "设计框架",
    "设计概念",
    "设计方案",
    "空间策略",
}
_ALLOWED_SHORT_CORE_TERMS = {
    "女性",
    "儿童",
    "老人",
    "预算",
    "消防",
    "结构",
    "隔音",
    "安全",
    "隐私",
    "回本",
    "坪效",
    "租金",
}

def derive_semantic_axes(prompt: str, *, registry: Optional[Mapping[str, Any]] = None) -> Dict[str, List[str]]:
    """Derive stable project-level semantic axes from a prompt.

    This is intentionally broad and taxonomy-like. It is used for pressure
    evaluation and guardrails, not as a single-case answer generator.
    """

    return _shared_derive_semantic_axes(prompt, registry=registry)


def evaluate_semantic_alignment(
    prompt: str,
    visible_text: str,
    *,
    project_type: Optional[str] = None,
    card_pages: Optional[Iterable[str]] = None,
    registry: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, str]]:
    return _shared_evaluate_semantic_alignment(
        prompt,
        visible_text,
        project_type=project_type,
        card_pages=card_pages,
        registry=registry,
    )
def load_simulation_questions(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    prompt_path = Path(path) if path else _find_default_prompt_file()
    text = prompt_path.read_text(encoding="utf-8")
    matches = list(re.finditer(r"(?m)^(\d+)\.\s+", text))
    questions: List[Dict[str, Any]] = []
    is_tea_golden_file = "茶饮" in prompt_path.name
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        prompt = _clean_numbered_prompt(text[start:end])
        if not prompt:
            continue
        ordinal = len(questions) + 1
        item = {
            "id": int(match.group(1)),
            "ordinal": ordinal,
            "prompt": prompt,
            "source_path": str(prompt_path),
        }
        if is_tea_golden_file:
            item["source_group"] = _tea_golden_group(ordinal)
            item[
                "domain_context"
            ] = "当前是茶饮店项目，请按茶饮小店、奶茶店或现制饮品店场景理解下面的问题。"
        questions.append(
            item
        )
    return questions


def analyze_prompt(
    prompt: str,
    *,
    question_id: Optional[int] = None,
    service: Optional[SchemeAdvisorEntryService] = None,
    domain_context: Optional[str] = None,
) -> Dict[str, Any]:
    service = service or SchemeAdvisorEntryService()
    blocking: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []
    governance_signals: List[Dict[str, str]] = []
    profile: Dict[str, Any] = {}
    card: Dict[str, Any] = {}
    reply = ""

    try:
        result = service.handle_message(
            session={},
            user_message=_with_domain_context(prompt, domain_context),
            in_response_to_card_id=None,
            selected_option_id=None,
        )
    except Exception as exc:  # pragma: no cover - exercised by full pressure runs
        return {
            "id": question_id,
            "status": "fail",
            "project_type": None,
            "project_type_name": None,
            "subdomain_id": None,
            "activation_pack_id": None,
            "confidence": None,
            "reply_preview": "",
            "card_pages": [],
            "round_2_card_title": "",
            "round_2_pages": [],
            "round_2_reply_preview": "",
            "blocking_issues": [
                {"code": "entry_exception", "message": f"{type(exc).__name__}: {exc}"}
            ],
            "warning_issues": [],
            "governance_signals": [],
        }

    if not result:
        blocking.append({"code": "entry_unhandled", "message": "SchemeAdvisorEntryService returned None"})
        result = {}

    reply = str(result.get("reply") or "")
    card = result.get("guidance_card") or {}
    state = result.get("scheme_entry_state") or {}
    profile = state.get("profile") or {}
    mode = profile.get("mode") or "project"
    trace = profile.get("intelligence_trace") or {}
    context_packet = profile.get("context_packet") or {}
    classification = profile.get("classification") or {}
    space_axis = profile.get("space_axis") or classification.get("space_axis") or {}
    activation_pack_status = _activation_pack_status(profile, mode)
    coverage_ceiling = _coverage_ceiling(context_packet)

    if not profile:
        blocking.append({"code": "missing_profile", "message": "Entry state did not include context profile"})
    if mode != "redirect" and context_packet.get("schema_version") != "context_packet.v3.3":
        blocking.append(
            {
                "code": "invalid_context_packet",
                "message": f"context_packet schema={context_packet.get('schema_version')}",
            }
        )
    if not card:
        blocking.append({"code": "missing_guidance_card", "message": "Entry did not return a guidance card"})

    round_2_reply = ""
    round_2_card: Dict[str, Any] = {}
    if state and card.get("card_type") == "scheme_round_1":
        try:
            round_2_result = service.handle_message(
                session={
                    "scheme_advisor_entry_v2": state,
                    "pending_guidance_card": card,
                },
                user_message=_round_one_probe_message(prompt),
                in_response_to_card_id=card.get("card_id"),
                selected_option_id=None,
            )
        except Exception as exc:  # pragma: no cover - exercised by full pressure runs
            blocking.append(
                {
                    "code": "round_2_probe_exception",
                    "message": f"{type(exc).__name__}: {exc}",
                }
            )
        else:
            round_2_reply = str((round_2_result or {}).get("reply") or "")
            round_2_card = (round_2_result or {}).get("guidance_card") or {}

    card_page_titles = _card_page_titles(card)
    round_2_page_titles = _card_page_titles(round_2_card)

    visible_text = reply + " " + _visible_text(card) + " " + round_2_reply + " " + _visible_text(round_2_card)
    leaked_terms = [term for term in _INTERNAL_TERMS if term in visible_text]
    internal_term_issues: List[Dict[str, str]] = []
    if leaked_terms:
        internal_term_issues.append(
            _warning_issue("internal_terms_visible", ", ".join(leaked_terms))
        )
        blocking.extend(internal_term_issues)

    semantic_axes = derive_semantic_axes(prompt)
    semantic_issues = evaluate_semantic_alignment(
        prompt,
        visible_text,
        project_type=profile.get("project_type"),
        card_pages=card_page_titles + round_2_page_titles,
    )
    for issue in semantic_issues:
        normalized = {"code": issue["code"], "message": issue["message"]}
        if issue.get("severity") == "blocking":
            blocking.append(normalized)
        else:
            warnings.append(normalized)
    question_quality_issues = [
        dict(issue)
        for issue in semantic_issues
        if issue.get("code") in _QUESTION_QUALITY_ISSUE_CODES
    ]
    display_safety_issues = [
        dict(issue)
        for issue in semantic_issues
        if issue.get("code") in _DISPLAY_SAFETY_ISSUE_CODES
    ] + internal_term_issues

    confidence = _as_float(trace.get("confidence"))
    active_missing_slot_count = sum(
        1 for slot in profile.get("missing_slots") or [] if slot.get("active_for_current_round")
    )
    allowed_output_depth = _allowed_output_depth(
        mode=mode,
        confidence=confidence,
        coverage_ceiling=coverage_ceiling,
        active_missing_slot_count=active_missing_slot_count,
    )
    input_mode = _input_mode(mode=mode, semantic_axes=semantic_axes)
    candidate_allowed_output_depth = _candidate_allowed_output_depth(
        allowed_output_depth,
        input_mode=input_mode,
    )
    if confidence is not None and confidence < 0.55:
        warnings.append(_warning_issue("low_classification_confidence", f"分类置信度偏低：{confidence}"))
    if trace.get("coverage_gap"):
        governance_signals.append(
            _governance_signal("coverage_gap", "空间分类覆盖存在缺口，进入 Registry/边界样本治理")
        )
    if classification.get("knowledge_gap_ticket"):
        governance_signals.append(
            _governance_signal("knowledge_gap_ticket", "已生成知识缺口线索，进入知识资产候选治理")
        )
    if activation_pack_status == "missing_formal_pack":
        warnings.append(_warning_issue("missing_activation_pack", "正式专科缺少激活包绑定"))
    elif activation_pack_status == "candidate_needed":
        governance_signals.append(_governance_signal("activation_pack_candidate", "进入激活包候选建设池"))

    if activation_pack_status == "candidate_needed":
        governance_signals = [
            signal
            for signal in governance_signals
            if signal.get("code") != "activation_pack_candidate"
        ]
        governance_signals.append(
            _governance_signal(
                "knowledge_coverage_watch",
                "暂以基础空间推理框架服务，进入知识覆盖观察池；不自动视为专科激活包建设对象",
            )
        )

    reported_space_axis_id = space_axis.get("primary_axis_id")
    reported_space_axis_label = space_axis.get("primary_axis_label")
    if not reported_space_axis_id and mode == "methodology":
        reported_space_axis_id = "methodology_not_project"
        reported_space_axis_label = "方法论问题，不进入空间分类主轴"
    elif not reported_space_axis_id and mode == "redirect":
        reported_space_axis_id = "redirect_not_project"
        reported_space_axis_label = "非空间设计问题，已转出"
    candidate_core_tension = _candidate_core_tension(
        prompt,
        input_mode=input_mode,
        space_axis_label=reported_space_axis_label,
        semantic_axes=semantic_axes,
    )
    layer_boundary_issues = _layer_boundary_issues(
        {
            "input_mode": input_mode,
            "mode": mode,
            "project_type": profile.get("project_type"),
            "space_axis_id": reported_space_axis_id,
            "space_axis_label": reported_space_axis_label,
        }
    )
    for issue_code in layer_boundary_issues:
        blocking.append(
            {
                "code": issue_code,
                "message": "input_mode / project_type / space_axis 三层边界发生越权",
            }
        )

    return {
        "id": question_id,
        "status": "fail" if blocking else "pass",
        "mode": mode,
        "project_type": profile.get("project_type"),
        "project_type_name": profile.get("project_type_name"),
        "subdomain_id": profile.get("subdomain_id"),
        "activation_pack_id": profile.get("activation_pack_id"),
        "activation_pack_status": activation_pack_status,
        "input_mode": input_mode,
        "knowledge_coverage_level": coverage_ceiling.get("coverage_level"),
        "coverage_ceiling_level": coverage_ceiling.get("ceiling_level"),
        "allowed_output_depth": allowed_output_depth,
        "candidate_allowed_output_depth": candidate_allowed_output_depth,
        "candidate_core_tension": candidate_core_tension,
        "space_axis_id": reported_space_axis_id,
        "space_axis_label": reported_space_axis_label,
        "space_axis_registry_source": space_axis.get("registry_source"),
        "space_axis_matched_rule_id": space_axis.get("matched_rule_id"),
        "confidence": confidence,
        "recommended_version": (profile.get("version_score") or {}).get("recommended_version"),
        "missing_slot_count": len(profile.get("missing_slots") or []),
        "active_missing_slot_count": active_missing_slot_count,
        "semantic_axes": semantic_axes,
        "semantic_alignment_issues": semantic_issues,
        "question_quality_issues": question_quality_issues,
        "display_safety_issues": display_safety_issues,
        "layer_boundary_issues": layer_boundary_issues,
        "card_pages": card_page_titles,
        "round_2_card_title": str(round_2_card.get("title") or ""),
        "round_2_pages": round_2_page_titles,
        "round_2_reply_preview": round_2_reply[:260],
            "reply_preview": reply[:260],
            "blocking_issues": blocking,
            "warning_issues": warnings,
            "governance_signals": governance_signals,
            "governance_candidate_emitted": bool(governance_signals),
        }


def run_pressure_suite(
    *,
    path: Optional[Path] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    questions = load_simulation_questions(path)
    if limit is not None:
        questions = questions[:limit]
    service = SchemeAdvisorEntryService()
    items = [
        {
            **analyze_prompt(
                question["prompt"],
                question_id=question.get("ordinal") if question.get("source_group") else question["id"],
                service=service,
                domain_context=question.get("domain_context"),
            ),
            "prompt": question["prompt"],
            "ordinal": question.get("ordinal"),
            "source_id": question.get("id"),
            "source_group": question.get("source_group"),
            "domain_context": question.get("domain_context"),
        }
        for question in questions
    ]
    items = _promote_activation_pack_candidates(items)
    failed = [item for item in items if item["status"] != "pass"]
    warnings = [item for item in items if item["warning_issues"]]
    governance_signal_items = [item for item in items if item.get("governance_signals")]
    space_axis_counts = Counter(_space_axis_summary_key(item) for item in items)
    governance_signal_counts = Counter(
        issue.get("code")
        for item in items
        for issue in item.get("governance_signals") or []
        if issue.get("code")
    )
    output_depth_counts = Counter(
        item.get("allowed_output_depth") or "unknown"
        for item in items
    )
    coverage_ceiling_counts = Counter(
        item.get("coverage_ceiling_level") or "not_applicable"
        for item in items
    )
    round_2_generic_fallback_count = sum(
        1 for item in items if _has_round_2_generic_fallback(item)
    )
    layer_boundary_violation_count = sum(
        1 for item in items if item.get("layer_boundary_issues")
    )
    quality_issue_counts = _quality_issue_counts(items)
    knowledge_coverage_gap_axis_counts = _knowledge_coverage_gap_axis_counts(items)
    knowledge_coverage_gap_project_type_counts = _knowledge_coverage_gap_project_type_counts(items)
    return {
        "schema_version": "scheme_advisor_pressure_run.v1",
        "source_path": questions[0]["source_path"] if questions else str(path or _find_default_prompt_file()),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "total": len(items),
            "passed": len(items) - len(failed),
            "failed": len(failed),
            "with_warnings": len(warnings),
            "with_governance_signals": len(governance_signal_items),
            "governance_signal_counts": dict(governance_signal_counts),
            "space_axis_counts": dict(space_axis_counts),
            "output_depth_counts": dict(output_depth_counts),
            "coverage_ceiling_counts": dict(coverage_ceiling_counts),
            "quality_issue_counts": quality_issue_counts,
            "knowledge_coverage_gap_axis_counts": dict(knowledge_coverage_gap_axis_counts),
            "knowledge_coverage_gap_project_type_counts": dict(knowledge_coverage_gap_project_type_counts),
            "round_2_generic_fallback_count": round_2_generic_fallback_count,
            "layer_boundary_violation_count": layer_boundary_violation_count,
        },
        "items": items,
    }


def _quality_issue_counts(items: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {key: 0 for key in _QUALITY_ISSUE_COUNTER_KEYS}
    for item in items:
        item_codes: set[str] = set()

        for issue in item.get("semantic_alignment_issues") or []:
            code = str((issue or {}).get("code") or "").strip()
            if code:
                item_codes.add(code)
        for issue in item.get("display_safety_issues") or []:
            code = str((issue or {}).get("code") or "").strip()
            if code:
                item_codes.add(code)
        for issue in item.get("warning_issues") or []:
            code = str((issue or {}).get("code") or "").strip()
            if code:
                item_codes.add(code)

        governance_codes = {
            str((issue or {}).get("code") or "").strip()
            for issue in item.get("governance_signals") or []
            if str((issue or {}).get("code") or "").strip()
        }
        if governance_codes.intersection(
            {"coverage_gap", "knowledge_gap_ticket", "knowledge_coverage_watch"}
        ):
            item_codes.add("knowledge_coverage_gap")

        for code in _QUALITY_ISSUE_COUNTER_KEYS:
            if code in item_codes:
                counts[code] += 1
    return counts


def _has_knowledge_coverage_gap(item: Mapping[str, Any]) -> bool:
    governance_codes = {
        str((issue or {}).get("code") or "").strip()
        for issue in item.get("governance_signals") or []
        if str((issue or {}).get("code") or "").strip()
    }
    return bool(
        governance_codes.intersection(
            {"coverage_gap", "knowledge_gap_ticket", "knowledge_coverage_watch"}
        )
    )


def _knowledge_coverage_gap_axis_counts(items: Iterable[Mapping[str, Any]]) -> Counter:
    counts: Counter = Counter()
    for item in items:
        if not _has_knowledge_coverage_gap(item):
            continue
        if str(item.get("mode") or "") != "project":
            continue
        axis_id = str(item.get("space_axis_id") or "").strip()
        if not axis_id or axis_id in {"-", "methodology_not_project", "redirect_not_project"}:
            continue
        counts[axis_id] += 1
    return counts


def _knowledge_coverage_gap_project_type_counts(items: Iterable[Mapping[str, Any]]) -> Counter:
    counts: Counter = Counter()
    for item in items:
        if not _has_knowledge_coverage_gap(item):
            continue
        if str(item.get("mode") or "") != "project":
            continue
        project_type = str(item.get("project_type") or "").strip()
        if not project_type or project_type == "-":
            continue
        counts[project_type] += 1
    return counts


def _promote_activation_pack_candidates(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Promote repeatable coverage-watch groups into activation-pack candidates.

    A single unsupported project should not automatically become a specialist
    activation-pack build request. The candidate signal is a batch-level
    governance judgement based on stable classification, repeat frequency, and
    non-experimental domain fit.
    """

    group_counts = Counter(
        str(item.get("project_type") or "-")
        for item in items
        if _activation_pack_candidate_eligible(item)
    )
    promoted: List[Dict[str, Any]] = []
    for item in items:
        current = dict(item)
        signals = [dict(signal) for signal in current.get("governance_signals") or []]
        group_key = str(current.get("project_type") or "-")
        group_size = int(group_counts.get(group_key) or 0)
        if (
            group_size >= _ACTIVATION_PACK_CANDIDATE_MIN_GROUP_SIZE
            and _activation_pack_candidate_eligible(current)
        ):
            signals = [
                signal
                for signal in signals
                if signal.get("code") != "knowledge_coverage_watch"
            ]
            signal = _governance_signal(
                "activation_pack_candidate",
                "同类项目样本达到批量候选阈值，进入专科激活包候选池",
            )
            signal["group_key"] = group_key
            signal["group_size"] = str(group_size)
            signals.append(signal)
            current["activation_pack_candidate_group_size"] = group_size
        current["governance_signals"] = signals
        promoted.append(current)
    return promoted


def _activation_pack_candidate_eligible(item: Mapping[str, Any]) -> bool:
    if str(item.get("mode") or "") != "project":
        return False
    if not any(
        signal.get("code") == "knowledge_coverage_watch"
        for signal in item.get("governance_signals") or []
    ):
        return False
    confidence = _as_float(item.get("confidence"))
    if confidence is None or confidence < 0.55:
        return False
    project_type = str(item.get("project_type") or "").strip()
    if not project_type or project_type in {"-", "special_function"}:
        return False
    axes = item.get("semantic_axes") or {}
    space_domains = set(_as_string_list(axes.get("space_domains")))
    spatial_design_drivers = set(_as_string_list(axes.get("spatial_design_drivers")))
    if "technical_special" in space_domains:
        return False
    if "extreme_resilience_prototype" in spatial_design_drivers:
        return False
    return True


def _as_string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item).strip()]
    if value is None:
        return []
    return [str(value)]


def write_markdown_report(result: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 方案高参模拟问题服务层压测清单",
        "",
        f"- 生成时间: `{result.get('generated_at')}`",
        f"- 来源: `{result.get('source_path')}`",
        f"- 总数: {result['summary']['total']}",
        f"- 通过: {result['summary']['passed']}",
        f"- 阻断失败: {result['summary']['failed']}",
        f"- 有警告: {result['summary']['with_warnings']}",
        f"- 第二轮通用兜底残留: {result['summary'].get('round_2_generic_fallback_count', 0)}",
        f"- 三层边界越权: {result['summary'].get('layer_boundary_violation_count', 0)}",
        "",
        "## 质量指标汇总",
        "",
    ]
    quality_issue_counts = result.get("summary", {}).get("quality_issue_counts") or {}
    if quality_issue_counts:
        lines.extend(["| 质量指标 | 数量 | 含义 |", "|---|---:|---|"])
        for code in _QUALITY_ISSUE_COUNTER_KEYS:
            lines.append(
                f"| `{code}` | {int(quality_issue_counts.get(code, 0))} | {_quality_issue_meaning(code)} |"
            )
        extra_codes = sorted(set(quality_issue_counts) - set(_QUALITY_ISSUE_COUNTER_KEYS))
        for code in extra_codes:
            lines.append(
                f"| `{code}` | {int(quality_issue_counts.get(code, 0))} | {_quality_issue_meaning(code)} |"
            )
    else:
        lines.append("无。")

    lines.extend(["", "## 知识覆盖缺口聚合", ""])
    gap_axis_counts = result.get("summary", {}).get("knowledge_coverage_gap_axis_counts") or {}
    gap_project_type_counts = result.get("summary", {}).get("knowledge_coverage_gap_project_type_counts") or {}
    if not gap_axis_counts and not gap_project_type_counts:
        lines.append("无。")
    if gap_axis_counts:
        lines.extend(["### 按空间主轴", "", "| 空间主轴 | 数量 |", "|---|---:|"])
        for axis_id, count in sorted(
            gap_axis_counts.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        ):
            lines.append(f"| `{axis_id}` | {count} |")
    if gap_project_type_counts:
        lines.extend(["", "### 按项目类型", "", "| 项目类型 | 数量 |", "|---|---:|"])
        for project_type, count in sorted(
            gap_project_type_counts.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        ):
            lines.append(f"| `{project_type}` | {count} |")

    lines.extend([
        "",
        "## 空间主轴汇总",
        "",
    ])
    space_axis_counts = result.get("summary", {}).get("space_axis_counts") or {}
    if space_axis_counts:
        lines.extend(["| 空间主轴 | 数量 |", "|---|---:|"])
        for axis_id, count in sorted(
            space_axis_counts.items(),
            key=lambda item: (-int(item[1]), str(item[0])),
        ):
            lines.append(f"| `{axis_id}` | {count} |")
    else:
        lines.append("无。")

    lines.extend(
        [
            "",
            "## 告警汇总",
            "",
        ]
    )
    warning_counts = Counter(
        issue.get("code")
        for item in result.get("items") or []
        for issue in item.get("warning_issues") or []
        if issue.get("code")
    )
    priority_counts = Counter(
        (issue.get("priority") or _warning_governance_profile(str(issue.get("code") or ""))["priority"])
        for item in result.get("items") or []
        for issue in item.get("warning_issues") or []
        if issue.get("code")
    )
    governance_signal_counts = Counter(
        issue.get("code")
        for item in result.get("items") or []
        for issue in item.get("governance_signals") or []
        if issue.get("code")
    )
    if warning_counts:
        lines.extend(["| 告警类型 | 数量 | 优先级 | 治理轨道 | 含义 |", "|---|---:|---|---|---|"])
        for code, count in warning_counts.most_common():
            profile = _warning_governance_profile(str(code))
            lines.append(
                f"| `{code}` | {count} | `{profile['priority']}` | `{profile['track']}` | {profile['meaning']} |"
            )
    else:
        lines.append("无。")

    if priority_counts:
        lines.extend(
            [
                "",
                "### 治理优先级汇总",
                "",
                "| 治理优先级 | 数量 | 处理原则 |",
                "|---|---:|---|",
            ]
        )
        for priority, count in sorted(priority_counts.items()):
            lines.append(f"| `{priority}` | {count} | {_priority_meaning(priority)} |")

    lines.extend(["", "## 治理信号汇总", ""])
    if governance_signal_counts:
        lines.extend(["| 治理信号 | 数量 | 优先级 | 治理轨道 | 含义 |", "|---|---:|---|---|---|"])
        for code, count in governance_signal_counts.most_common():
            profile = _warning_governance_profile(str(code))
            lines.append(
                f"| `{code}` | {count} | `{profile['priority']}` | `{profile['track']}` | {profile['meaning']} |"
            )
    else:
        lines.append("无。")

    lines.extend(["", "## 输出封顶汇总", ""])
    output_depth_counts = result.get("summary", {}).get("output_depth_counts") or {}
    if output_depth_counts:
        lines.extend(["| 允许输出深度 | 数量 | 含义 |", "|---|---:|---|"])
        for depth, count in sorted(output_depth_counts.items()):
            lines.append(f"| `{depth}` | {count} | {_output_depth_meaning(str(depth))} |")
    else:
        lines.append("无。")

    lines.extend(["", "## 知识覆盖封顶汇总", ""])
    coverage_ceiling_counts = result.get("summary", {}).get("coverage_ceiling_counts") or {}
    if coverage_ceiling_counts:
        lines.extend(["| 覆盖封顶等级 | 数量 | 含义 |", "|---|---:|---|"])
        for level, count in sorted(coverage_ceiling_counts.items()):
            lines.append(f"| `{level}` | {count} | {_coverage_ceiling_meaning(str(level))} |")
    else:
        lines.append("无。")

    lines.extend(
        [
            "",
            "## 优化清单",
            "",
        ]
    )
    optimization_lines = _optimization_lines(warning_counts + governance_signal_counts)
    if optimization_lines:
        lines.extend(optimization_lines)
    else:
        lines.append("- 当前压测未发现需要跟进的阻断项或告警项。")

    lines.extend(
        [
            "",
            "## 逐条结果",
            "",
        "| 编号 | 状态 | 项目类型 | 子域 | 激活包 | 置信度 | 警告 | 治理信号 | 阻断 | 第二轮追问 | 问题摘要 |",
        "|---:|---|---|---|---|---:|---|---|---|---|---|",
        ]
    )
    for item in result.get("items") or []:
        lines.append(
            "| {id} | {status} | {ptype} | {subdomain} | {pack} | {confidence} | {warnings} | {signals} | {blockers} | {round2} | {prompt} |".format(
                id=item.get("id"),
                status=item.get("status"),
                ptype=_cell(item.get("project_type")),
                subdomain=_cell(item.get("subdomain_id")),
                pack=_cell(item.get("activation_pack_id")),
                confidence="" if item.get("confidence") is None else item.get("confidence"),
                warnings=_cell(_issue_codes(item.get("warning_issues") or [])),
                signals=_cell(_issue_codes(item.get("governance_signals") or [])),
                blockers=_cell(_issue_codes(item.get("blocking_issues") or [])),
                round2=_cell(_round_2_summary(item)),
                prompt=_cell(str(item.get("prompt") or "")[:120]),
            )
        )
    lines.append("")
    lines.append("## 阻断详情")
    failures = [item for item in result.get("items") or [] if item.get("blocking_issues")]
    if not failures:
        lines.append("")
        lines.append("无。")
    for item in failures:
        lines.append("")
        lines.append(f"### {item.get('id')}. {_cell(str(item.get('prompt') or '')[:80])}")
        for issue in item.get("blocking_issues") or []:
            lines.append(f"- `{issue.get('code')}`: {issue.get('message')}")

    lines.append("")
    lines.append("## 警告详情")
    warned = [item for item in result.get("items") or [] if item.get("warning_issues")]
    if not warned:
        lines.append("")
        lines.append("无。")
    for item in warned:
        lines.append("")
        lines.append(f"### {item.get('id')}. {_cell(str(item.get('prompt') or '')[:80])}")
        for issue in item.get("warning_issues") or []:
            profile = _warning_governance_profile(str(issue.get("code") or ""))
            priority = issue.get("priority") or profile["priority"]
            track = issue.get("track") or profile["track"]
            lines.append(
                f"- `{issue.get('code')}` (`{priority}` / `{track}`): {issue.get('message')}"
            )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _find_default_prompt_file() -> Path:
    candidates = [
        path
        for path in _DEFAULT_PROMPT_DIR.iterdir()
        if path.is_file() and path.suffix == ".txt" and path.stat().st_size > 10000
    ]
    if not candidates:
        raise FileNotFoundError(f"simulation prompt file not found under {_DEFAULT_PROMPT_DIR}")
    return candidates[0]


def _clean_numbered_prompt(raw: str) -> str:
    lines = []
    for line in raw.splitlines():
        text = line.strip()
        if not text:
            continue
        if re.match(r"^\*\*.*\*\*$", text):
            continue
        if re.match(r"^#+\s+", text):
            continue
        lines.append(text)
    return "\n".join(lines).strip()


def _with_domain_context(prompt: str, domain_context: Optional[str]) -> str:
    if not domain_context:
        return prompt
    return f"{domain_context}\n\n用户问题：{prompt}"


def _round_one_probe_message(prompt: str) -> str:
    semantic_axes = derive_semantic_axes(prompt)
    terms: List[str] = []
    if "commercial_operation_roi" in semantic_axes.get("business_drivers", []):
        terms.extend(["回本", "运营", "客流"])
    if "founder_owner" in semantic_axes.get("subject_profiles", []):
        terms.extend(["主人身份", "家族", "成就"])
    if "family_legacy" in semantic_axes.get("founding_drivers", []):
        terms.extend(["家族传承", "内心回归"])
    if "waterfront_view" in semantic_axes.get("site_resources", []):
        terms.append("景观资源")
    if not terms:
        terms.append("当前项目主轴")
    return "先按" + "、".join(dict.fromkeys(terms[:4])) + "继续确认最影响方向的一件事。"


def _card_page_titles(card: Mapping[str, Any]) -> List[str]:
    return [str(page.get("page_title") or "") for page in card.get("pages") or []]


def _tea_golden_group(ordinal: int) -> str:
    groups = [
        (10, "site_business_model"),
        (17, "hard_constraint_feasibility"),
        (25, "visibility_conversion"),
        (30, "customer_brand_goal"),
        (40, "store_model_scene_strategy"),
        (50, "product_menu_operation"),
        (62, "queue_pickup_flow"),
        (71, "waiting_experience_repurchase"),
        (80, "brand_price_visual_memory"),
        (87, "equipment_logistics_maintenance"),
        (92, "standard_competition_positioning"),
        (100, "opening_validation_review"),
    ]
    for max_ordinal, group in groups:
        if ordinal <= max_ordinal:
            return group
    return "extended_tea_golden"


def _visible_text(value: Any) -> str:
    if isinstance(value, dict):
        visible_keys = {
            "title",
            "prompt_text",
            "page_title",
            "helper_text",
            "label",
            "description",
            "reply",
            "name",
            "price_label",
            "summary",
        }
        structural_keys = {"pages", "options", "version_cards"}
        return " ".join(
            _visible_text(item)
            for key, item in value.items()
            if key in visible_keys or key in structural_keys
        )
    if isinstance(value, list):
        return " ".join(_visible_text(item) for item in value)
    return str(value)


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _coverage_ceiling(context_packet: Mapping[str, Any]) -> Dict[str, Any]:
    knowledge_binding = context_packet.get("knowledge_binding") or {}
    ceiling = knowledge_binding.get("coverage_ceiling") or {}
    if isinstance(ceiling, Mapping):
        return dict(ceiling)
    return {}


def _allowed_output_depth(
    *,
    mode: str,
    confidence: Optional[float],
    coverage_ceiling: Mapping[str, Any],
    active_missing_slot_count: int = 0,
) -> str:
    if mode == "redirect":
        return "out_of_scope_redirect"
    if mode == "methodology":
        return "methodology_framework"
    if confidence is not None and confidence < 0.55:
        return "conditional_judgement"

    ceiling_level = str(coverage_ceiling.get("ceiling_level") or "")
    if ceiling_level == "full_specialist":
        if active_missing_slot_count > 0:
            return "conditional_design_framework"
        return "full_specialist_design"
    if ceiling_level == "conditional_framework":
        return "conditional_design_framework"
    return "strategy_framework"


def _input_mode(*, mode: str, semantic_axes: Mapping[str, List[str]]) -> str:
    problem_modes = set(semantic_axes.get("problem_modes") or [])
    if mode == "redirect":
        return "out_of_scope"
    if mode == "project":
        return "project"
    if "value_argument" in problem_modes:
        return "decision_argument"
    if mode == "methodology":
        return "methodology"
    return "project"


def _candidate_allowed_output_depth(depth: str, *, input_mode: str) -> str:
    if input_mode == "decision_argument":
        return "决策论证级：可给判断框架与证据清单，不输出空间方案"
    labels = {
        "full_specialist_design": "完整方案级：信息足够、类型明确、可给结构化完整建议",
        "conditional_design_framework": "条件方案级：可给方案框架，但要声明前提和缺口",
        "strategy_framework": "策略框架级：适合规划、定位、竞标、概念阶段",
        "methodology_framework": "方法论框架级：可给通用框架、适用边界与落地验证",
        "conditional_judgement": "风险提示级：硬约束或信息不足，先止损和补条件",
        "out_of_scope_redirect": "出域引导级：不进入空间方案",
    }
    return labels.get(depth, labels["strategy_framework"])


def _candidate_core_tension(
    prompt: str,
    *,
    input_mode: str,
    space_axis_label: Optional[str],
    semantic_axes: Mapping[str, List[str]],
) -> str:
    if input_mode == "decision_argument":
        if "material_sustainability_value" in set(semantic_axes.get("spatial_design_drivers") or []):
            return "材料替换的短期成本、长期价值与证据链是否成立"
        return "短期成本与长期价值是否成立"

    if input_mode == "methodology":
        tensions = _shared_rank_main_tensions(prompt, limit=2)
        titles = [str(item.get("title") or "").strip() for item in tensions if item.get("title")]
        if titles:
            return "、".join(titles)

    if input_mode == "project":
        prompt_specific = _project_prompt_core_tension(prompt, semantic_axes=semantic_axes)
        if prompt_specific:
            return prompt_specific

    if space_axis_label:
        label = str(space_axis_label).strip()
        if "：" in label:
            label = label.split("：", 1)[1].strip()
        if label:
            return label

    tensions = _shared_rank_main_tensions(prompt, limit=2)
    titles = [str(item.get("title") or "").strip() for item in tensions if item.get("title")]
    if titles:
        return "、".join(titles)
    return "项目目标、核心使用者与现实边界"


def _project_prompt_core_tension(
    prompt: str,
    *,
    semantic_axes: Mapping[str, List[str]],
    limit: int = 5,
) -> str:
    """Build a project-specific tension from the user's own wording.

    The semantic registry decides which concepts are important; the prompt
    clauses keep the current project's subject, driver and boundary visible.
    """

    matched_terms = _matched_semantic_core_terms(prompt, semantic_axes)
    candidates = _core_phrase_candidates(prompt, matched_terms=matched_terms)
    selected: List[str] = []

    for phrase, _score in candidates:
        cleaned = _clean_core_phrase(phrase)
        if not cleaned or _core_phrase_redundant(cleaned, selected):
            continue
        selected.append(cleaned)
        if len(selected) >= limit:
            break

    if selected:
        return "、".join(selected)
    return ""


def _matched_semantic_core_terms(
    prompt: str,
    semantic_axes: Mapping[str, List[str]],
) -> Dict[str, int]:
    registry = _shared_load_semantic_axis_registry()
    text = str(prompt or "")
    matched: Dict[str, int] = {}

    for axis_name, axis_ids in semantic_axes.items():
        axis_weight = _CORE_TENSION_AXIS_WEIGHTS.get(axis_name)
        if axis_weight is None:
            continue
        rule_map = (registry.get("axes") or {}).get(axis_name) or {}
        for axis_id in axis_ids or []:
            spec = rule_map.get(axis_id) or {}
            for term in spec.get("terms") or []:
                normalized = str(term or "").strip()
                if not normalized or normalized in _LOW_SIGNAL_CORE_TERMS or normalized not in text:
                    continue
                if len(normalized) < 3 and normalized not in _ALLOWED_SHORT_CORE_TERMS:
                    continue
                matched[normalized] = max(matched.get(normalized, 0), axis_weight + len(normalized))

    return matched


def _core_phrase_candidates(
    prompt: str,
    *,
    matched_terms: Mapping[str, int],
) -> List[tuple[str, int]]:
    text = str(prompt or "")
    candidates: Dict[str, int] = {}

    for quoted in re.findall(r"[“\"']([^”\"']{2,24})[”\"']", text):
        _add_core_candidate(candidates, quoted, 18 + len(quoted))

    for clause in re.split(r"[。；;，,\n]", text):
        cleaned = _clean_core_phrase(clause)
        if not cleaned:
            continue
        score = _score_core_clause(cleaned, matched_terms=matched_terms)
        if score > 0:
            _add_core_candidate(candidates, cleaned, score)

    for term, score in matched_terms.items():
        _add_core_candidate(candidates, term, score)

    return sorted(candidates.items(), key=lambda item: (-item[1], len(item[0]), item[0]))


def _score_core_clause(clause: str, *, matched_terms: Mapping[str, int]) -> int:
    score = 0
    for term, term_score in matched_terms.items():
        if term in clause:
            score += term_score

    if re.search(r"(业主|客户|主人|目标用户|先生|太太|创始人|创业者)", clause):
        score += 24
    if re.search(r"(希望|需要|要求|期待|避免|成为|形成|兼顾|融合)", clause):
        score += 12
    if re.search(r"(精神|传承|回归|身份|成就|价值|品牌|运营|效率|差异|仪式|认同)", clause):
        score += 10
    if re.search(r"[A-Za-z][A-Za-z0-9&.\-]{2,}", clause):
        score += 18
    if re.search(r"(面积|楼层|㎡|层|客房|大堂|展厅|餐厅|泳池|健身)", clause):
        score -= 10
    if clause.startswith(("请提出", "包括", "涵盖")):
        score -= 14

    return score


def _add_core_candidate(candidates: Dict[str, int], phrase: str, score: int) -> None:
    cleaned = _clean_core_phrase(phrase)
    if not cleaned:
        return
    candidates[cleaned] = max(candidates.get(cleaned, 0), score)


def _clean_core_phrase(phrase: str) -> str:
    cleaned = re.sub(r"\s+", "", str(phrase or "").strip())
    cleaned = cleaned.strip("：:，,。；;、")
    cleaned = re.sub(r"^请(从|以|围绕)?", "", cleaned)
    cleaned = re.sub(r"^(提出|给出|构建|说明|阐述|包括|涵盖)", "", cleaned)
    return cleaned.strip("：:，,。；;、")


def _core_phrase_redundant(phrase: str, selected: Iterable[str]) -> bool:
    if len(phrase) < 2:
        return True
    for current in selected:
        if phrase in current or current in phrase:
            return True
    return False


def _activation_pack_status(profile: Mapping[str, Any], mode: str) -> str:
    if mode in {"redirect", "methodology"}:
        return "not_required"
    if profile.get("activation_pack_id"):
        return "formal_bound"
    if profile.get("subdomain_id") in _FORMAL_ACTIVATION_PACK_SUBDOMAINS:
        return "missing_formal_pack"
    return "candidate_needed"


def _space_axis_summary_key(item: Mapping[str, Any]) -> str:
    axis_id = str(item.get("space_axis_id") or "").strip()
    if axis_id:
        return axis_id
    mode = str(item.get("mode") or "").strip()
    if mode == "methodology":
        return "methodology_not_project"
    if mode == "redirect":
        return "redirect_not_project"
    return "unknown"


def _layer_boundary_issues(item: Mapping[str, Any]) -> List[str]:
    """Detect cross-layer leakage between input mode, project type, and space axis.

    These are invariant checks, not case-specific classification rules.
    """

    input_mode = str(item.get("input_mode") or "").strip()
    mode = str(item.get("mode") or "").strip()
    project_type = str(item.get("project_type") or "").strip()
    space_axis_id = str(item.get("space_axis_id") or "").strip()
    non_project_axes = {"methodology_not_project", "redirect_not_project"}
    non_project_modes = {"methodology", "decision_argument", "out_of_scope"}
    issues: List[str] = []

    if input_mode == "project":
        if not project_type:
            issues.append("project_input_requires_project_type")
        if space_axis_id in non_project_axes:
            issues.append("project_input_must_not_use_non_project_space_axis")

    if input_mode in non_project_modes:
        if project_type:
            issues.append("non_project_input_must_not_keep_project_type")
        if input_mode in {"methodology", "decision_argument"} and space_axis_id not in {"", "methodology_not_project"}:
            issues.append("non_project_input_must_not_use_project_space_axis")
        if input_mode == "out_of_scope" and space_axis_id not in {"", "redirect_not_project"}:
            issues.append("out_of_scope_input_must_not_use_project_space_axis")

    if mode == "project" and input_mode != "project":
        issues.append("project_mode_must_keep_project_input_mode")
    if mode in {"methodology", "redirect"} and input_mode == "project":
        issues.append("non_project_mode_must_not_keep_project_input_mode")

    return issues


def _warning_issue(code: str, message: str) -> Dict[str, str]:
    profile = _warning_governance_profile(code)
    return {
        "code": code,
        "message": message,
        "priority": profile["priority"],
        "track": profile["track"],
        "meaning": profile["meaning"],
        "next_action": profile["next_action"],
    }


def _governance_signal(code: str, message: str) -> Dict[str, str]:
    return _warning_issue(code, message)


def _warning_governance_profile(code: str) -> Dict[str, str]:
    profiles = {
        "missing_activation_pack": {
            "priority": "P0",
            "track": "runtime_configuration_gap",
            "meaning": "已纳入正式专科的子域缺少正式激活包绑定，这是配置缺口。",
            "next_action": "补齐正式激活包文件或从正式专科名单移出，避免运行时错误期待。",
        },
        "low_classification_confidence": {
            "priority": "P1",
            "track": "classification_registry_review",
            "meaning": "空间分类置信度偏低，可能需要补别名、边界样本或复合类型规则。",
            "next_action": "优先复核样本，判断是分类规则不足、输入过抽象，还是需要人工候选。",
        },
        "coverage_gap": {
            "priority": "P1",
            "track": "space_registry_coverage",
            "meaning": "分类链路发现覆盖缺口，需要进入 Registry 或边界样本治理。",
            "next_action": "按高频空间主轴聚合，优先补稳定分类、Type Alias 和边界样本。",
        },
        "knowledge_gap_ticket": {
            "priority": "P2",
            "track": "knowledge_asset_pipeline",
            "meaning": "已生成知识缺口线索，需要后续沉淀为审核通过的知识资产。",
            "next_action": "进入 candidate card / package review，不直接进入运行时事实。",
        },
        "activation_pack_candidate": {
            "priority": "P3",
            "track": "activation_pack_candidate_pool",
            "meaning": "当前项目可服务，但尚无正式专科激活包；这是建设池信号，不阻断通用框架输出。",
            "next_action": "按业务价值、出现频次和知识成熟度决定是否建设专科激活包。",
        },
    }
    profiles["knowledge_coverage_watch"] = {
        "priority": "P3",
        "track": "basic_framework_coverage_watch",
        "meaning": "当前可用基础空间推理框架服务，但样本不足以直接进入专科激活包建设池。",
        "next_action": "继续累计同类样本、分类稳定性和知识成熟度；达到批量阈值后再晋级为 activation_pack_candidate。",
    }
    return profiles.get(
        code,
        {
            "priority": "P2",
            "track": "unclassified_governance_signal",
            "meaning": "未登记含义的治理信号，需要补充说明。",
            "next_action": "先登记含义、优先级和处理轨道，再决定是否纳入报告。",
        },
    )


def _priority_meaning(priority: str) -> str:
    meanings = {
        "P0": "会影响已承诺正式能力或运行配置，优先修复。",
        "P1": "会影响分类稳定性或基础判断，应进入近期整改。",
        "P2": "知识资产生产缺口，进入审核和沉淀队列。",
        "P3": "能力建设候选池，按业务价值排期，不代表当前回答失败。",
    }
    return meanings.get(priority, "未登记优先级，需要补充治理口径。")


def _output_depth_meaning(depth: str) -> str:
    meanings = {
        "full_specialist_design": "专科知识覆盖充分，可进入完整专科方案建议。",
        "conditional_design_framework": "有部分专业覆盖，但必须保留条件判断，不能输出施工级确定结论。",
        "conditional_judgement": "分类或输入置信度不足，只能给条件级判断和补充问题。",
        "methodology_framework": "方法论讨论，不进入具体项目方案承诺。",
        "strategy_framework": "仅有通用方法支撑，只能给战略框架和下一步核验路径。",
        "out_of_scope_redirect": "非空间设计问题，应礼貌转出。",
    }
    return meanings.get(depth, "未登记输出深度，需要补充封顶口径。")


def _coverage_ceiling_meaning(level: str) -> str:
    meanings = {
        "full_specialist": "正式专科覆盖，可以调用专科卡片和激活包。",
        "conditional_framework": "只有部分专业或邻近知识覆盖，必须压低输出确定性。",
        "strategy_framework": "缺少专科覆盖，只能给通用空间方法和风险提示。",
        "not_applicable": "方法论或转出问题，不适用知识覆盖封顶。",
    }
    return meanings.get(level, "未登记覆盖封顶等级，需要补充治理口径。")


def _quality_issue_meaning(code: str) -> str:
    meanings = {
        "wrong_domain_reference": "错误领域引用",
        "english_key_visible": "用户侧英文或字段名泄露",
        "generic_step_title_visible": "固定流程词外露",
        "core_subject_missing": "未回应用户输入里的关键主体",
        "low_classification_confidence": "空间分类低置信",
        "knowledge_coverage_gap": "知识覆盖不足或候选治理信号",
    }
    return meanings.get(code, "未登记质量指标，需要补充治理口径。")


def _issue_codes(issues: Iterable[Dict[str, str]]) -> str:
    return ",".join(str(issue.get("code")) for issue in issues if issue.get("code"))


def _round_2_summary(item: Mapping[str, Any]) -> str:
    title = str(item.get("round_2_card_title") or "").strip()
    pages = [str(page).strip() for page in item.get("round_2_pages") or [] if str(page).strip()]
    if title and pages:
        return f"{title}: {' / '.join(pages)}"
    if title:
        return title
    if pages:
        return " / ".join(pages)
    return "-"


def _has_round_2_generic_fallback(item: Mapping[str, Any]) -> bool:
    text = " ".join(
        [
            str(item.get("round_2_card_title") or ""),
            " ".join(str(page or "") for page in item.get("round_2_pages") or []),
            str(item.get("round_2_reply_preview") or ""),
        ]
    )
    generic_markers = [
        "当前项目主轴",
        "最后确认优先级",
        "最不能跑偏",
        "项目主轴最先保什么",
    ]
    return any(marker in text for marker in generic_markers)


def _warning_meaning(code: str) -> str:
    return _warning_governance_profile(code)["meaning"]


def _optimization_lines(warning_counts: Counter) -> List[str]:
    lines: List[str] = []
    if warning_counts.get("missing_activation_pack"):
        lines.append(
            "- `missing_activation_pack`: 只处理已纳入正式专科、理论上应有激活包但未绑定的配置缺口。"
        )
    if warning_counts.get("activation_pack_candidate"):
        lines.append(
            "- `activation_pack_candidate`: 其他高频类型先进入激活包候选池，按业务价值和重复出现频次排期，不自动上线。"
        )
    if warning_counts.get("coverage_gap"):
        lines.append(
            "- `coverage_gap`: 从高频项目类型开始补 Registry 覆盖、Type Alias 和边界样本，避免业务语义长期停留在代码规则里。"
        )
    if warning_counts.get("knowledge_gap_ticket"):
        lines.append(
            "- `knowledge_gap_ticket`: 将缺口按项目类型聚合，进入知识卡片审核链路，批准后再进入运行时召回。"
        )
    if warning_counts.get("low_classification_confidence"):
        lines.append(
            "- `low_classification_confidence`: 优先复核低置信样本是否存在复合空间、跨学科主题或表述过抽象，再决定补规则还是补 Registry。"
        )
    return lines


def _cell(value: Any) -> str:
    text = str(value or "-").replace("|", "\\|").replace("\n", " ")
    return text


def _pressure_exit_code(summary: Mapping[str, Any]) -> int:
    if int(summary.get("failed") or 0) > 0:
        return 1
    if int(summary.get("round_2_generic_fallback_count") or 0) > 0:
        return 1
    if int(summary.get("layer_boundary_violation_count") or 0) > 0:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Scheme Advisor service pressure tests.")
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json-output", type=Path, default=None)
    args = parser.parse_args()

    result = run_pressure_suite(path=args.input, limit=args.limit)
    if args.output:
        write_markdown_report(result, args.output)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False))
    return _pressure_exit_code(result["summary"])


if __name__ == "__main__":
    raise SystemExit(main())
