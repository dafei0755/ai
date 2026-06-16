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
