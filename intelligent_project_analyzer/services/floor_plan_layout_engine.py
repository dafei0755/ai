"""Lightweight layout variant engine for Plan Sandbox.

This module implements the first executable step of the floor-plan reasoning
architecture: deterministic, explainable multi-variant layout drafts from SPG
and structural facts. It deliberately avoids LLM geometry generation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from intelligent_project_analyzer.core.domain_objects import (
    DesignConstraint,
    DesignConstraintGraph,
    DesignIntent,
    FloorPlanFacts,
    LayoutGenerationPackage,
    LayoutIR,
    LayoutScore,
    LayoutSpace,
    LayoutVariant,
    LayoutVersionGraph,
    LayoutVersionNode,
    SPGZone,
    SpatialProgramGraph,
)


@dataclass(frozen=True)
class LayoutStrategyPreset:
    """A deterministic strategy profile for early layout generation."""

    strategy: str
    title: str
    primary_axis: str
    priorities: Sequence[str]
    tradeoffs: Sequence[str]
    source_experts: Sequence[str]


DEFAULT_STRATEGIES: Sequence[LayoutStrategyPreset] = (
    LayoutStrategyPreset(
        strategy="conservative_low_change",
        title="低改造稳妥版",
        primary_axis="优先保留结构与既有空间秩序，降低施工风险。",
        priorities=("锁定不可动构件", "减少空间交换", "保守处理开敞边界"),
        tradeoffs=("空间惊喜感较弱", "部分动线不做激进优化"),
        source_experts=("实施边界", "风险总控"),
    ),
    LayoutStrategyPreset(
        strategy="functional_efficiency",
        title="功能效率版",
        primary_axis="优先压缩无效交通并强化高频功能邻接。",
        priorities=("缩短主路径", "厨餐/服务空间邻接", "提高面积利用率"),
        tradeoffs=("仪式感与松弛感会被压缩", "局部空间边界更理性"),
        source_experts=("运营效率", "空间规划"),
    ),
    LayoutStrategyPreset(
        strategy="experience_value",
        title="体验价值版",
        primary_axis="优先把公共核心、景观面和到达首感组织成项目记忆点。",
        priorities=("公共核心靠近最佳资源", "入口序列更完整", "强化可讲述的空间节点"),
        tradeoffs=("改造成本可能上升", "面积效率不是第一目标"),
        source_experts=("用户研究", "品牌总监"),
    ),
)


def generate_layout_variants(
    spg: SpatialProgramGraph,
    facts: Optional[FloorPlanFacts] = None,
    session_id: str = "",
    variant_count: int = 3,
) -> LayoutGenerationPackage:
    """Generate strategy-different layout drafts.

    The result is intentionally coarse: normalized room blocks, adjacency
    traces, scores and explanations. It is the MVP substrate for later LLM
    reasoning, local operations and solver-backed refinement.
    """

    safe_facts = facts or FloorPlanFacts(
        facts_id=f"facts-{spg.spg_id or 'draft'}",
        session_id=session_id,
        boundary=[[0, 0], [1, 0], [1, 1], [0, 1]],
    )
    graph = build_constraint_graph(spg, safe_facts, session_id=session_id)
    zones = _normalized_zones(spg.zones)
    strategies = list(DEFAULT_STRATEGIES[: max(1, min(variant_count, len(DEFAULT_STRATEGIES)))])

    variants = [
        _build_variant(
            preset=preset,
            zones=zones,
            spg=spg,
            facts=safe_facts,
            graph=graph,
            index=index,
            session_id=session_id,
        )
        for index, preset in enumerate(strategies, start=1)
    ]
    version_graph = LayoutVersionGraph(
        graph_id=f"layout-graph-{spg.spg_id or session_id or 'draft'}",
        session_id=session_id,
        nodes=[
            LayoutVersionNode(
                version_id=variant.variant_id,
                layout_id=variant.layout.layout_id,
                decision_trace=[
                    f"生成策略：{variant.intent.title}",
                    f"主轴：{variant.intent.primary_axis}",
                    "状态：候选，等待用户选择/锁定/指令推演。",
                ],
            )
            for variant in variants
        ],
    )

    return LayoutGenerationPackage(
        package_id=f"layout-package-{spg.spg_id or session_id or 'draft'}",
        session_id=session_id,
        facts=safe_facts,
        constraint_graph=graph,
        variants=variants,
        version_graph=version_graph,
        generation_notes=[
            "Phase 0 采用粗空间块布局，不承诺施工级墙线精度。",
            "每个版本代表不同设计判断，评分只用于比较，不替代用户裁决。",
        ],
    )


def build_constraint_graph(
    spg: SpatialProgramGraph,
    facts: FloorPlanFacts,
    session_id: str = "",
) -> DesignConstraintGraph:
    """Compile SPG + facts into a lightweight constraint graph."""

    constraints: List[DesignConstraint] = []

    for element in facts.immutable_elements:
        constraints.append(
            DesignConstraint(
                constraint_id=f"lock-{element.element_id}",
                constraint_type="hard_lock",
                target_ids=[element.element_id],
                value={"element_type": element.element_type, "locked": element.locked},
                priority="hard" if element.locked else "high",
                source="floor_plan_facts",
            )
        )

    for zone in spg.zones:
        if zone.approx_area_m2:
            constraints.append(
                DesignConstraint(
                    constraint_id=f"area-{zone.zone_id}",
                    constraint_type="area",
                    target_ids=[zone.zone_id],
                    value={"target_area_m2": zone.approx_area_m2},
                    priority="medium",
                    source="spg",
                )
            )
        for adjacent_id in zone.required_adjacencies:
            constraints.append(
                DesignConstraint(
                    constraint_id=f"adj-{zone.zone_id}-{adjacent_id}",
                    constraint_type="adjacency",
                    target_ids=[zone.zone_id, adjacent_id],
                    value={"required": True},
                    priority="high",
                    source="spg",
                )
            )
        for adjacent_id in zone.forbidden_adjacencies:
            constraints.append(
                DesignConstraint(
                    constraint_id=f"avoid-{zone.zone_id}-{adjacent_id}",
                    constraint_type="forbidden_adjacency",
                    target_ids=[zone.zone_id, adjacent_id],
                    value={"forbidden": True},
                    priority="high",
                    source="spg",
                )
            )
        if zone.orientation_preference:
            constraints.append(
                DesignConstraint(
                    constraint_id=f"orient-{zone.zone_id}",
                    constraint_type="orientation",
                    target_ids=[zone.zone_id],
                    value={"preference": zone.orientation_preference},
                    priority="medium",
                    source="spg",
                )
            )

    return DesignConstraintGraph(
        graph_id=f"constraint-{spg.spg_id or session_id or 'draft'}",
        session_id=session_id,
        spg_id=spg.spg_id,
        facts_id=facts.facts_id,
        constraints=constraints,
        locked_zone_ids=[
            element.element_id
            for element in facts.immutable_elements
            if element.locked
        ],
        preferred_objectives=["user_choice", "explainable_variants", "layout_feasibility"],
    )


def _build_variant(
    preset: LayoutStrategyPreset,
    zones: Sequence[SPGZone],
    spg: SpatialProgramGraph,
    facts: FloorPlanFacts,
    graph: DesignConstraintGraph,
    index: int,
    session_id: str,
) -> LayoutVariant:
    intent = DesignIntent(
        intent_id=f"intent-{index}-{preset.strategy}",
        title=preset.title,
        strategy=preset.strategy,  # type: ignore[arg-type]
        primary_axis=preset.primary_axis,
        spatial_priorities=list(preset.priorities),
        accepted_tradeoffs=list(preset.tradeoffs),
        source_experts=list(preset.source_experts),
        rationale=f"根据 {spg.space_type or '当前项目'} 的 SPG 与结构底座，生成一个代表“{preset.title}”的候选方向。",
    )
    ordered_zones = _order_zones_for_strategy(zones, preset.strategy)
    spaces = _pack_spaces(ordered_zones, preset.strategy)
    score = _score_layout(spaces, preset.strategy, graph)
    risks = _collect_risks(spaces, facts, preset.strategy)
    layout = LayoutIR(
        layout_id=f"layout-{index}-{preset.strategy}",
        session_id=session_id,
        based_on_facts_id=facts.facts_id,
        based_on_spg_version=spg.version,
        design_intent_id=intent.intent_id,
        strategy=preset.strategy,
        spaces=spaces,
        circulation=_build_circulation(spg, spaces),
        open_boundaries=_suggest_open_boundaries(spaces, preset.strategy),
        closed_boundaries=_suggest_closed_boundaries(spaces, preset.strategy),
        score=score,
        risks=risks,
        explanation=_explain_variant(preset, score, risks),
    )

    return LayoutVariant(
        variant_id=f"variant-{index}-{preset.strategy}",
        name=preset.title,
        intent=intent,
        layout=layout,
        comparison_summary=_compare_summary(preset.strategy, score),
    )


def _normalized_zones(zones: Sequence[SPGZone]) -> List[SPGZone]:
    if zones:
        return list(zones)
    return [
        SPGZone(zone_id="public_core", name="公共核心", function="public", approx_area_m2=35, privacy_level="public"),
        SPGZone(zone_id="private_room", name="私密房间", function="private", approx_area_m2=20, privacy_level="private"),
        SPGZone(zone_id="service", name="服务空间", function="service", approx_area_m2=12, privacy_level="service"),
    ]


def _order_zones_for_strategy(zones: Sequence[SPGZone], strategy: str) -> List[SPGZone]:
    privacy_rank = {"public": 0, "semi_public": 1, "service": 2, "private": 3}
    if strategy == "experience_value":
        return sorted(zones, key=lambda z: (0 if z.privacy_level == "public" else 1, -(z.approx_area_m2 or 0)))
    if strategy == "functional_efficiency":
        return sorted(zones, key=lambda z: (0 if z.privacy_level == "service" else 1, privacy_rank.get(z.privacy_level, 2)))
    return sorted(zones, key=lambda z: privacy_rank.get(z.privacy_level, 2))


def _pack_spaces(zones: Sequence[SPGZone], strategy: str) -> List[LayoutSpace]:
    total_area = sum(max(zone.approx_area_m2 or 12, 1) for zone in zones) or 1
    spaces: List[LayoutSpace] = []

    if strategy == "experience_value":
        cursor_y = 0.04
        for index, zone in enumerate(zones):
            area_ratio = max(zone.approx_area_m2 or 12, 1) / total_area
            height = max(0.12, min(0.34, area_ratio * 0.86))
            width = 0.66 if index == 0 else 0.42
            x = 0.05 if index == 0 else 0.53
            spaces.append(_space_from_zone(zone, x, cursor_y, width, height))
            cursor_y = min(0.86, cursor_y + height + 0.035)
        return spaces

    if strategy == "functional_efficiency":
        cursor_x = 0.04
        for zone in zones:
            area_ratio = max(zone.approx_area_m2 or 12, 1) / total_area
            width = max(0.14, min(0.32, area_ratio * 0.9))
            spaces.append(_space_from_zone(zone, cursor_x, 0.12, width, 0.72))
            cursor_x = min(0.84, cursor_x + width + 0.025)
        return spaces

    cursor_y = 0.05
    for zone in zones:
        area_ratio = max(zone.approx_area_m2 or 12, 1) / total_area
        height = max(0.10, min(0.28, area_ratio * 0.82))
        spaces.append(_space_from_zone(zone, 0.08, cursor_y, 0.80, height))
        cursor_y = min(0.86, cursor_y + height + 0.04)
    return spaces


def _space_from_zone(zone: SPGZone, x: float, y: float, w: float, h: float) -> LayoutSpace:
    return LayoutSpace(
        space_id=zone.zone_id,
        name=zone.name,
        function=zone.function,
        x=round(x, 4),
        y=round(y, 4),
        w=round(min(w, 0.92 - x), 4),
        h=round(min(h, 0.92 - y), 4),
        area_target_m2=zone.approx_area_m2,
        privacy_level=zone.privacy_level,
        adjacent_to=list(zone.required_adjacencies),
    )


def _build_circulation(spg: SpatialProgramGraph, spaces: Sequence[LayoutSpace]) -> dict:
    if spg.flows:
        return {
            flow.flow_id: [flow.from_zone, flow.to_zone]
            for flow in spg.flows
        }
    ordered = [space.space_id for space in spaces]
    return {"main_path": ordered}


def _suggest_open_boundaries(spaces: Sequence[LayoutSpace], strategy: str) -> List[List[str]]:
    if strategy not in {"experience_value", "functional_efficiency"}:
        return []
    public_ids = [space.space_id for space in spaces if space.privacy_level in {"public", "semi_public"}]
    return [[a, b] for a, b in zip(public_ids, public_ids[1:])]


def _suggest_closed_boundaries(spaces: Sequence[LayoutSpace], strategy: str) -> List[List[str]]:
    if strategy == "experience_value":
        return []
    public_ids = [space.space_id for space in spaces if space.privacy_level == "public"]
    private_ids = [space.space_id for space in spaces if space.privacy_level == "private"]
    return [[public_id, private_id] for public_id in public_ids for private_id in private_ids]


def _score_layout(spaces: Sequence[LayoutSpace], strategy: str, graph: DesignConstraintGraph) -> LayoutScore:
    hard_locks = len([c for c in graph.constraints if c.priority == "hard"])
    adjacency_targets = len([c for c in graph.constraints if c.constraint_type == "adjacency"])
    has_public = any(space.privacy_level == "public" for space in spaces)
    has_private = any(space.privacy_level == "private" for space in spaces)

    base = LayoutScore(
        functional_efficiency=72 + min(adjacency_targets * 3, 12),
        privacy_order=70 + (8 if has_public and has_private else 0),
        view_resource=68,
        renovation_cost=78 - min(hard_locks * 2, 10),
        project_fit=74 + min(len(spaces), 8),
        user_preference_fit=70,
    )
    if strategy == "functional_efficiency":
        base.functional_efficiency = min(base.functional_efficiency + 12, 95)
        base.renovation_cost = max(base.renovation_cost - 4, 50)
    elif strategy == "experience_value":
        base.view_resource = 88
        base.project_fit = min(base.project_fit + 8, 96)
        base.renovation_cost = max(base.renovation_cost - 14, 45)
    else:
        base.renovation_cost = min(base.renovation_cost + 8, 92)
        base.privacy_order = min(base.privacy_order + 4, 92)
    return base


def _collect_risks(spaces: Sequence[LayoutSpace], facts: FloorPlanFacts, strategy: str) -> List[str]:
    risks: List[str] = []
    if not facts.boundary:
        risks.append("缺少明确外轮廓，当前布局只能作为概念块推演。")
    if facts.review_flags:
        risks.extend(f"结构底座待复核：{flag}" for flag in facts.review_flags[:3])
    if strategy == "experience_value":
        risks.append("体验价值版可能提高改造成本，需在下一轮校核结构与预算。")
    if len(spaces) > 8:
        risks.append("空间数量较多，粗块布局需要进入局部重排以避免动线拥挤。")
    return risks


def _explain_variant(preset: LayoutStrategyPreset, score: LayoutScore, risks: Sequence[str]) -> str:
    risk_text = "；".join(risks) if risks else "暂无硬风险，仍需用户选择后进入细化校核。"
    return (
        f"{preset.title}以“{preset.primary_axis}”为主轴。"
        f"它优先处理：{'、'.join(preset.priorities)}。"
        f"当前项目匹配度 {score.project_fit}，功能效率 {score.functional_efficiency}，"
        f"改造成本友好度 {score.renovation_cost}。风险提示：{risk_text}"
    )


def _compare_summary(strategy: str, score: LayoutScore) -> str:
    if strategy == "functional_efficiency":
        return f"更适合追求高频使用效率，功能效率 {score.functional_efficiency}。"
    if strategy == "experience_value":
        return f"更适合强调首感、景观和品牌记忆点，景观资源 {score.view_resource}。"
    return f"更适合先稳住结构与预算，改造成本友好度 {score.renovation_cost}。"


def list_supported_operations() -> Iterable[str]:
    """Expose the operation vocabulary for command parsing prompts and docs."""

    return (
        "lock_space",
        "move_space",
        "resize_space",
        "swap_space",
        "merge_spaces",
        "split_space",
        "add_buffer",
        "reduce_corridor",
        "increase_privacy",
        "improve_view",
        "shorten_path",
        "separate_flow",
        "open_boundary",
        "close_boundary",
        "merge_strategy",
        "reduce_cost",
    )
