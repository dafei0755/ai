"""Shared semantic-axis registry for Scheme Advisor entry and pressure checks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import yaml

from .scheme_advisor_public_labels import public_label


SEMANTIC_AXIS_REGISTRY_PATH = (
    Path(__file__).resolve().parent.parent
    / "config"
    / "registries"
    / "scheme_advisor_semantic_axes.yaml"
)

_REGISTRY_CACHE: Dict[Path, Dict[str, Any]] = {}


def load_semantic_axis_registry(
    path: Optional[Path] = None,
    *,
    use_cache: bool = True,
) -> Dict[str, Any]:
    registry_path = Path(path or SEMANTIC_AXIS_REGISTRY_PATH)
    if use_cache and registry_path in _REGISTRY_CACHE:
        return _REGISTRY_CACHE[registry_path]

    if not registry_path.exists():
        raise FileNotFoundError(f"Semantic axis registry not found: {registry_path}")

    data = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data.get("axes"), Mapping):
        raise ValueError(f"Invalid semantic axis registry: missing axes in {registry_path}")

    normalized = _normalize_registry(data)
    if use_cache:
        _REGISTRY_CACHE[registry_path] = normalized
    return normalized


def derive_semantic_axes(
    prompt: str,
    *,
    registry: Optional[Mapping[str, Any]] = None,
) -> Dict[str, List[str]]:
    text = str(prompt or "")
    source = registry or load_semantic_axis_registry()
    axes: Dict[str, List[str]] = {}

    for axis_name, rule_map in (source.get("axes") or {}).items():
        axes[axis_name] = [
            axis_id
            for axis_id, spec in rule_map.items()
            if _any_term_matches(text, spec.get("terms") or [])
        ]

    _apply_inference_rules(text, axes, source)
    axes["is_complex_project"] = ["true"] if len(axes.get("space_domains") or []) > 1 else []
    return axes


def axis_label(axis_id: str, *, registry: Optional[Mapping[str, Any]] = None) -> str:
    source = registry or load_semantic_axis_registry()
    labels = source.get("labels") or {}
    if str(axis_id) in labels:
        return str(labels[str(axis_id)])
    return public_label(str(axis_id))


def axis_description(axis_id: str, *, registry: Optional[Mapping[str, Any]] = None) -> str:
    source = registry or load_semantic_axis_registry()
    descriptions = source.get("descriptions") or {}
    default_text = source.get("default_description") or "会影响方案主轴、追问顺序和后续目录重心。"
    return str(descriptions.get(str(axis_id), default_text))


def has_problem_mode(axes: Mapping[str, List[str]]) -> bool:
    return bool(axes.get("problem_modes") or [])


def has_input_intent(axes: Mapping[str, List[str]]) -> bool:
    return bool(axes.get("input_intents") or [])


def is_pure_naming_copy_request(message: str) -> bool:
    text = str(message or "")
    has_naming_or_copy = any(term in text for term in ("命名", "取名", "名称", "文案", "slogan", "Slogan"))
    if not has_naming_or_copy:
        return False
    explicit_non_spatial = any(
        term in text for term in ("不涉及空间设计", "不需要空间设计", "只要名称", "只要命名", "只要文案")
    )
    spatial_design_terms = ("空间语言", "空间设计", "动线", "材料", "灯光", "展陈", "功能", "平面", "室内")
    has_spatial_design_scope = any(term in text for term in spatial_design_terms)
    return explicit_non_spatial or not has_spatial_design_scope


def is_reference_material_request(message: str) -> bool:
    text = str(message or "")
    has_reference_target = any(term in text for term in ("案例", "资料", "参考图", "参考图片", "图集", "标杆"))
    if not has_reference_target:
        return False
    has_collection_action = any(
        term in text for term in ("整理", "推荐", "收集", "列出", "找", "给我参考", "参考方向")
    )
    explicit_project_action = any(
        term in text
        for term in (
            "重构需求",
            "帮我重构",
            "请先帮我重构需求",
            "怎么改造",
            "希望改造",
            "希望打造",
            "需要改造",
            "需要打造",
            "请提出完整设计",
            "设计框架",
            "设计方案",
        )
    )
    return has_collection_action and not explicit_project_action


def is_competition_strategy_request(message: str) -> bool:
    text = str(message or "")
    has_competition = any(term in text for term in ("竞标", "投标", "竞赛", "评审"))
    has_strategy = any(term in text for term in ("汇报策略", "评审打动", "PPT", "提案策略", "投标策略", "竞标策略"))
    return has_competition and has_strategy


def is_methodology_discussion_request(message: str) -> bool:
    text = str(message or "")
    return any(
        term in text
        for term in (
            "方法论",
            "分析框架",
            "判断方法",
            "研究方法",
            "如何研究",
            "怎么研究",
            "应该怎么研究",
            "可迁移的方法",
        )
    )


def semantic_axis_density(
    axes: Mapping[str, List[str]],
    *,
    include_problem_modes: bool = False,
) -> int:
    excluded = {"is_complex_project"}
    if not include_problem_modes:
        excluded.add("problem_modes")
    return sum(
        1
        for axis_name, axis_values in axes.items()
        if axis_name not in excluded and bool(axis_values)
    )


def has_concrete_project_anchor(message: str) -> bool:
    """Authoritative, registry-driven detector for a concrete project anchor.

    Shared by the Scheme Advisor entry triage and the demand reconstruction
    entry gate so both layers decide "is this a real design/project input"
    from the same semantic-axis signals instead of divergent word lists.
    """
    text = str(message or "")
    if not text.strip():
        return False

    semantic_axes = derive_semantic_axes(text)
    space_domains = set(semantic_axes.get("space_domains") or [])
    input_intents = set(semantic_axes.get("input_intents") or [])
    has_methodology_mode = has_problem_mode(semantic_axes)
    semantic_density = semantic_axis_density(semantic_axes)
    numeric_anchor = bool(
        re.search(r"\d+(?:\.\d+)?\s*(?:㎡|平米|平方米|m2|m²|万平|间|层|小时|夜间|个夜间)", text, flags=re.IGNORECASE)
    )
    project_anchor_terms = (
        "项目",
        "位于",
        "业主",
        "总建筑面积",
        "功能涵盖",
        "需要在",
        "希望打造",
        "计划",
        "商铺",
        "门店",
        "买手店",
        "酒店",
        "民宿",
        "会所",
        "总部",
        "中心",
        "大堂",
        "多功能厅",
        "公寓",
        "别墅",
        "住宅",
        "书房",
        "展厅",
        "展馆",
        "体验店",
        "品牌空间",
        "历史街区",
        "社区",
        "办公",
    )
    strong_anchor_terms = (
        "项目为",
        "项目位于",
        "客户希望",
        "客户要求",
        "请提出完整室内设计",
        "请提出完整设计",
        "请提出基于",
    )
    anchor_hits = sum(1 for term in project_anchor_terms if term in text)
    strong_hits = sum(1 for term in strong_anchor_terms if term in text)
    concrete_design_request = bool(
        re.search(r"^为.+设计.+(?:概念|框架|策略|方案)", text)
    )
    has_project_specificity = (
        numeric_anchor
        or strong_hits >= 1
        or anchor_hits >= 2
        or concrete_design_request
    )
    semantic_project_anchor = (
        bool(space_domains)
        and bool(input_intents)
        and (
            not has_methodology_mode
            or has_project_specificity
        )
    )

    return (
        semantic_project_anchor
        or (bool(space_domains) and numeric_anchor)
        or (semantic_density >= 4 and has_project_specificity)
        or (numeric_anchor and anchor_hits >= 1)
        or anchor_hits >= 2
        or (anchor_hits >= 1 and strong_hits >= 1)
        or concrete_design_request
    )


def should_enter_demand_reconstruction(message: str) -> bool:
    """Shared pure gate for the demand reconstruction entry stage.

    The Scheme Advisor entry flow and the demand reconstruction service both
    need one answer to "is this a project-like input that should be reframed
    before formal intake?". Keep that answer here with the semantic-axis rules,
    rather than scattering local keyword gates across orchestration services.
    """
    text = str(message or "").strip()
    if not text:
        return False
    if is_competition_strategy_request(text):
        return False
    if is_pure_naming_copy_request(text):
        return False
    if is_reference_material_request(text):
        return False
    if is_methodology_discussion_request(text):
        has_project_reconstruction_intent = any(
            term in text for term in ("重构需求", "帮我重构", "梳理需求", "重构我的需求", "请提出完整设计")
        )
        if not has_project_reconstruction_intent:
            return False
    has_project_anchor = has_concrete_project_anchor(text)
    if has_project_anchor:
        return True

    axes = derive_semantic_axes(text)
    has_explicit_request = any(
        term in text for term in ("重构需求", "帮我重构", "梳理需求", "重构我的需求")
    )
    if has_problem_mode(axes) and not has_explicit_request:
        return False

    if has_explicit_request and semantic_axis_density(axes) >= 1:
        return True

    if bool(axes.get("space_domains")) and semantic_axis_density(axes) >= 3:
        return True

    has_spatial_focus = (
        "空间" in text
        or bool(axes.get("space_domains"))
        or bool(axes.get("site_resources"))
    )
    has_research_or_advice = any(
        term in text
        for term in (
            "研究",
            "源流",
            "历史",
            "文人",
            "雅集",
            "转译",
            "启发",
            "给出建议",
            "给点建议",
            "怎么看",
        )
    )
    return has_spatial_focus and has_research_or_advice


def rank_main_tensions(
    prompt: str,
    *,
    registry: Optional[Mapping[str, Any]] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    source = registry or load_semantic_axis_registry()
    axes = derive_semantic_axes(prompt, registry=source)
    priority_specs = source.get("tension_priority") or {}
    candidates: Dict[str, Dict[str, Any]] = {}

    axis_weights = {
        "critical_constraints": 18,
        "founding_drivers": 14,
        "spatial_design_drivers": 12,
        "subject_profiles": 8,
        "site_resources": 6,
        "space_domains": 4,
        "input_intents": 3,
        "problem_modes": 10,
        "lifecycle": 3,
    }

    for axis_name, axis_ids in axes.items():
        if axis_name == "is_complex_project":
            continue
        for axis_id in axis_ids or []:
            spec = priority_specs.get(axis_id)
            if not isinstance(spec, Mapping):
                continue
            item = candidates.setdefault(
                axis_id,
                {
                    "id": axis_id,
                    "label": axis_label(axis_id, registry=source),
                    "title": str(spec.get("title") or axis_label(axis_id, registry=source)),
                    "prompt": str(spec.get("prompt") or axis_description(axis_id, registry=source)),
                    "related_options": [str(item) for item in (spec.get("related_options") or []) if str(item)],
                    "relevance_terms": [str(item) for item in (spec.get("relevance_terms") or []) if str(item)],
                    "score": int(spec.get("base_weight") or 50),
                    "source_axes": [],
                },
            )
            item["score"] += axis_weights.get(axis_name, 1)
            item["source_axes"].append(axis_name)

    ranked = sorted(
        candidates.values(),
        key=lambda item: (-int(item.get("score") or 0), str(item.get("id") or "")),
    )
    return ranked[:limit]


def evaluate_semantic_alignment(
    prompt: str,
    visible_text: str,
    *,
    project_type: Optional[str] = None,
    card_pages: Optional[Iterable[str]] = None,
    registry: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, str]]:
    source = registry or load_semantic_axis_registry()
    axes = derive_semantic_axes(prompt, registry=source)
    guardrails = source.get("guardrails") or {}
    visible = str(visible_text or "")
    page_text = " ".join(str(page or "") for page in (card_pages or []))
    issues: List[Dict[str, str]] = []

    domains = set(axes.get("space_domains") or [])
    project_type_value = str(project_type or "")
    commercial_project_types = set(guardrails.get("commercial_project_types") or [])
    commercial_domains = set(guardrails.get("commercial_domains") or [])
    is_commercial_or_food = bool(domains.intersection(commercial_domains)) or project_type_value in commercial_project_types

    if not is_commercial_or_food and _any_term_matches(visible, guardrails.get("commercial_template_terms") or []):
        issues.append(_issue("commercial_template_leakage", "blocking", "非商业/非餐饮题出现茶饮或高周转门店模板话术"))

    generic_step_titles = guardrails.get("generic_step_titles") or []
    if _any_term_matches(visible, generic_step_titles) or _any_term_matches(page_text, generic_step_titles):
        issues.append(_issue("generic_step_title_visible", "blocking", "用户侧出现固定内部追问步骤名，未按当前项目语义生成问题"))

    english_key_pattern = str(guardrails.get("english_key_pattern") or "")
    if english_key_pattern and re.search(english_key_pattern, visible):
        issues.append(_issue("english_key_visible", "blocking", "用户侧出现英文/蛇形命名字段"))

    heritage_or_urban_domains = set(guardrails.get("heritage_or_urban_domains") or [])
    heritage_or_urban_resources = set(guardrails.get("heritage_or_urban_resources") or [])
    has_heritage_or_urban = bool(domains.intersection(heritage_or_urban_domains)) or bool(
        set(axes.get("site_resources") or []).intersection(heritage_or_urban_resources)
    )
    if not has_heritage_or_urban and _any_term_matches(visible, guardrails.get("wrong_domain_references") or []):
        issues.append(_issue("wrong_domain_reference", "blocking", "输出引用了当前问题不相关的城市更新或历史建筑语境"))

    subject_terms = guardrails.get("core_subject_visible_terms") or {}
    if "founder_owner" in set(axes.get("subject_profiles") or []) and not _any_term_matches(
        visible,
        subject_terms.get("founder_owner") or [],
    ):
        issues.append(_issue("core_subject_missing", "warning", "输出没有回应题目中的关键主体画像"))

    driver_terms = guardrails.get("core_driver_visible_terms") or {}
    if "family_legacy" in set(axes.get("founding_drivers") or []) and not _any_term_matches(
        visible,
        driver_terms.get("family_legacy") or [],
    ):
        issues.append(_issue("core_driver_missing", "warning", "输出没有回应题目中的关键成立原因"))

    return issues


def _normalize_registry(data: Mapping[str, Any]) -> Dict[str, Any]:
    axes: Dict[str, Dict[str, Dict[str, List[str]]]] = {}
    for axis_name, rule_map in (data.get("axes") or {}).items():
        axes[str(axis_name)] = {}
        for axis_id, spec in (rule_map or {}).items():
            if isinstance(spec, Mapping):
                terms = spec.get("terms") or []
            else:
                terms = spec or []
            axes[str(axis_name)][str(axis_id)] = {"terms": [str(term) for term in terms if str(term)]}

    normalized = dict(data)
    normalized["axes"] = axes
    normalized["labels"] = {str(k): str(v) for k, v in (data.get("labels") or {}).items()}
    normalized["descriptions"] = {str(k): str(v) for k, v in (data.get("descriptions") or {}).items()}
    normalized["tension_priority"] = {
        str(k): dict(v)
        for k, v in (data.get("tension_priority") or {}).items()
        if isinstance(v, Mapping)
    }
    normalized["inference_rules"] = [
        dict(rule)
        for rule in (data.get("inference_rules") or [])
        if isinstance(rule, Mapping)
    ]
    normalized["guardrails"] = data.get("guardrails") or {}
    return normalized


def _any_term_matches(text: str, terms: Iterable[str]) -> bool:
    return any(str(term) and str(term) in text for term in terms)


def _apply_inference_rules(
    text: str,
    axes: Dict[str, List[str]],
    registry: Mapping[str, Any],
) -> None:
    for rule in registry.get("inference_rules") or []:
        if not isinstance(rule, Mapping):
            continue
        if not _condition_matches(text, rule.get("when") or {}):
            continue
        for target in rule.get("append_axes") or []:
            if not isinstance(target, Mapping):
                continue
            axis_name = str(target.get("axis") or "")
            axis_id = str(target.get("id") or "")
            if axis_name and axis_id:
                _append_axis(axes, axis_name, axis_id)


def _condition_matches(text: str, condition: Mapping[str, Any]) -> bool:
    if not isinstance(condition, Mapping):
        return False
    if "all" in condition:
        return all(_condition_matches(text, item) for item in condition.get("all") or [])
    if "any" in condition:
        return any(_condition_matches(text, item) for item in condition.get("any") or [])
    if "not" in condition:
        return not _condition_matches(text, condition.get("not") or {})
    if "any_terms" in condition:
        return _any_term_matches(text, condition.get("any_terms") or [])
    if "all_terms" in condition:
        return all(str(term) and str(term) in text for term in condition.get("all_terms") or [])
    return False


def _append_axis(axes: Dict[str, List[str]], axis_name: str, axis_id: str) -> None:
    values = axes.setdefault(axis_name, [])
    if axis_id not in values:
        values.append(axis_id)


def _issue(code: str, severity: str, message: str) -> Dict[str, str]:
    return {"code": code, "severity": severity, "message": message}
