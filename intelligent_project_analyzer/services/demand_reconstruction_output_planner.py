"""Dynamic output planning for demand reconstruction action blueprints."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .scheme_advisor_semantic_axes import axis_label
from .demand_reconstruction_boundary_guard import DemandReconstructionBoundaryGuard


_SEMANTIC_AXES_REGISTRY_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "registries" / "scheme_advisor_semantic_axes.yaml"
)
_BLUEPRINT_FRAGMENTS_REGISTRY_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "registries" / "demand_reconstruction_blueprints.yaml"
)
_DEFAULT_BLUEPRINT_OVERRIDE_TERMS = {
    "collection_museum": ["博物馆", "美术馆", "收藏馆", "收藏家", "藏品"],
    "urban_renewal": ["城市更新", "街区更新", "老旧街区", "原住民", "社区商业"],
    "workplace_headquarters": ["办公", "总部", "研发团队", "工位", "员工"],
    "healthcare_care": ["医院", "病房", "诊所", "康养", "照护"],
}
_DEFAULT_SECONDARY_BLUEPRINT_FRAGMENTS = {
    "commercial_operation": {
        "title": "商业运营边界",
        "body": "次候选出现商业运营时，任务书不能只写体验叙事，还要确认经营动作会不会反向改变空间组织。",
        "items": [
            "确认售卖、排队、等候和收银是否进入公共体验动线。",
            "确认商业收入是主目标、配套服务，还是只承担停留激活功能。",
            "确认运营高峰是否会挤压展陈、活动或公共使用。",
        ],
        "emphasis": "medium",
    },
    "hard_constraint": {
        "title": "硬约束边界",
        "body": "次候选出现硬性约束时，应先把设备、消防、结构、机电或卫生边界列入需求重构，而不是后期补丁。",
        "items": [
            "确认哪些约束会直接改变平面、层高、动线或材料选择。",
            "确认约束是已知参数、待测参数，还是需要专项顾问确认。",
            "确认硬约束与体验目标冲突时谁拥有优先级。",
        ],
        "emphasis": "medium",
    },
    "media_production": {
        "title": "内容生产边界",
        "body": "次候选出现内容生产时，空间不只服务现场使用，还要确认镜头、声光、收纳和切换效率。",
        "items": [
            "确认哪些区域必须为拍摄、直播或录制保持可控背景。",
            "确认灯光、声学、设备和布线是否会改变日常使用。",
            "确认内容生产与真实运营同时发生时的切换规则。",
        ],
        "emphasis": "medium",
    },
    "style_semantics": {
        "title": "语义表达边界",
        "body": "次候选出现风格语义时，不应直接套视觉标签，而要先拆解哪些符号、材料和比例真正支撑项目立场。",
        "items": [
            "确认关键词是文化语义、品牌识别，还是用户审美偏好。",
            "确认哪些符号可以被转译，哪些会造成表面化误读。",
            "确认表达强度是否会压过功能、运营或公共使用。",
        ],
        "emphasis": "medium",
    },
    "public_cultural_experience": {
        "title": "公共体验边界",
        "body": "次候选出现公共文化体验时，要确认公众如何进入、理解、停留和被管理，而不是只补一个展示区。",
        "items": [
            "确认访客、居民、会员或员工是否共享同一套动线。",
            "确认教育、展陈、活动和休息谁是公共体验主线。",
            "确认开放程度、管理边界和安全责任。",
        ],
        "emphasis": "medium",
    },
    "life_identity": {
        "title": "生活身份边界",
        "body": "次候选出现生活身份时，任务书要校准真实使用者的长期生活，而不是只保留项目的形象目标。",
        "items": [
            "确认日常居住、家庭关系、工作身份或精神寄托谁是底盘。",
            "确认使用者画像是否会改变私密、接待和维护边界。",
            "确认项目表达是否会牺牲长期生活韧性。",
        ],
        "emphasis": "medium",
    },
    "cultural_research": {
        "title": "研究证据边界",
        "body": "次候选出现文化研究时，应先判断哪些文化判断需要证据支撑，避免把未经验证的转译写成结论。",
        "items": [
            "确认研究对象是历史事实、地域材料、人物线索，还是方法论借鉴。",
            "确认哪些内容需要案例、文献或田野证据再进入设计任务书。",
            "确认研究深度是否会推迟正式方案生成。",
        ],
        "emphasis": "medium",
    },
}
_DEFAULT_PRIMARY_BLUEPRINT_FRAGMENTS = {
    "style_semantics": {
        "task_reframe": "这不是寻找风格标签的问题，而是把模糊审美词拆成可控制、可验证、可执行的空间语义边界。",
        "viability": "项目成立先看语义边界能否被收住，再看材料、形式和图像参考是否匹配。",
        "primary_risk": "头号风险是用风格词替代空间判断，最后得到一套看似统一但无法指导使用、材料和运营的氛围包装。",
        "key_forks": [
            "东方感来自文化母题、空间比例，还是材料触感？",
            "不老气是减少符号，还是提升构造和光线的现代性？",
            "茶空间主要服务独处、社交、零售展示还是接待？",
        ],
        "unknowns": [
            "目标客群会改变表达强度。",
            "茶空间使用方式会改变停留机制。",
            "已有品牌或场地条件会改变可用语义。",
        ],
        "sections": [
            {
                "title": "语义边界",
                "body": "风格需求重构要先防止词语滑向符号堆叠。",
                "items": [
                    "“东方感”需要拆成比例、光线、材质、留白或仪式感中的具体来源。",
                    "“不老气”通常不是去掉传统元素，而是控制符号密度和材料年代感。",
                    "茶空间还要判断是社交、独处、展示，还是生活方式消费。",
                ],
                "emphasis": "high",
            },
            {
                "title": "表达禁区",
                "body": "需求重构会明确哪些表达方式必须先被排除，避免审美词直接变成图像拼贴。",
                "items": [
                    "直接堆中式符号，容易让东方感变成仿古感。",
                    "只追求极简，可能丢掉茶空间应有的停留层次。",
                    "只看参考图，会掩盖真实使用、品牌调性和维护边界。",
                ],
                "emphasis": "medium",
            },
        ],
        "slots": {
            "core_tension": "文化语义与现代使用之间的张力",
            "recommended_brief_focus": "优先冻结风格边界、使用场景和符号禁区",
        },
    },
    "commercial_operation": {
        "sections": [
            {
                "title": "商业成立方式",
                "body": "商业类需求重构要先确认项目靠什么成立，而不是直接把所有商业空间都写成单一业态的效率问题。",
                "items": [
                    "确认收入来自高频交易、低频高客单、会员复购，还是品牌信任建立。",
                    "确认空间首先解决转化、停留、展示、服务，还是运营效率。",
                    "确认经营模型会不会反向改变入口、动线、收纳和人员配置。",
                ],
                "emphasis": "high",
            }
        ],
    },
    "public_cultural_experience": {
        "sections": [
            {
                "title": "公共成立边界",
                "body": "公共文化类需求重构要先确认谁进入、为什么停留、如何理解内容，以及开放管理责任由谁承担。",
                "items": [
                    "确认核心受众是公众、专业访客、居民、学生、会员，还是合作伙伴。",
                    "确认空间首先服务展陈理解、教育互动、公共停留、品牌信任，还是运营活动。",
                    "确认开放程度、安全责任、维护强度和人员管理是否支撑公共使用。",
                ],
                "emphasis": "high",
            }
        ],
    },
}


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


@lru_cache(maxsize=1)
def _demand_reconstruction_blueprint_overrides() -> Dict[str, Any]:
    try:
        data = yaml.safe_load(_SEMANTIC_AXES_REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    overrides = data.get("demand_reconstruction_blueprint_overrides") or {}
    return overrides if isinstance(overrides, dict) else {}


def _blueprint_override_terms(override_id: str) -> List[str]:
    override = _demand_reconstruction_blueprint_overrides().get(override_id) or {}
    terms = override.get("trigger_terms") if isinstance(override, dict) else None
    if isinstance(terms, list):
        result = [str(term) for term in terms if str(term)]
        if result:
            return result
    return list(_DEFAULT_BLUEPRINT_OVERRIDE_TERMS.get(override_id, []))


def _merged_terms(*term_groups: List[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for terms in term_groups:
        for term in terms or []:
            text = str(term or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
    return result


@lru_cache(maxsize=1)
def _demand_reconstruction_blueprint_fragments() -> Dict[str, Any]:
    for registry_path in (_BLUEPRINT_FRAGMENTS_REGISTRY_PATH, _SEMANTIC_AXES_REGISTRY_PATH):
        try:
            data = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        fragments = data.get("demand_reconstruction_blueprint_fragments") or {}
        if isinstance(fragments, dict):
            return fragments
    return {}


def _secondary_blueprint_fragment(candidate_id: str) -> Dict[str, Any]:
    fragments = _demand_reconstruction_blueprint_fragments().get("secondary_candidates") or {}
    fragment = fragments.get(candidate_id) if isinstance(fragments, dict) else None
    if isinstance(fragment, dict) and fragment.get("title") and fragment.get("body"):
        return fragment
    return dict(_DEFAULT_SECONDARY_BLUEPRINT_FRAGMENTS.get(candidate_id, {}))


def _primary_blueprint_fragment(archetype_id: str) -> Dict[str, Any]:
    fragments = _demand_reconstruction_blueprint_fragments().get("primary_archetypes") or {}
    fragment = fragments.get(archetype_id) if isinstance(fragments, dict) else None
    if isinstance(fragment, dict) and fragment.get("sections"):
        return fragment
    return dict(_DEFAULT_PRIMARY_BLUEPRINT_FRAGMENTS.get(archetype_id, {}))


def _specialized_blueprint_fragment(group_id: str, fragment_id: str) -> Dict[str, Any]:
    group = _demand_reconstruction_blueprint_fragments().get(group_id) or {}
    fragment = group.get(fragment_id) if isinstance(group, dict) else None
    if isinstance(fragment, dict) and fragment.get("sections"):
        return fragment
    return {}


def _specialized_blueprint_trigger_terms(group_id: str, fragment_id: str) -> List[str]:
    return _specialized_blueprint_terms(group_id, fragment_id, "trigger_terms")


def _specialized_blueprint_terms(group_id: str, fragment_id: str, term_key: str) -> List[str]:
    group = _demand_reconstruction_blueprint_fragments().get(group_id) or {}
    fragment = group.get(fragment_id) if isinstance(group, dict) else None
    terms = fragment.get(term_key) if isinstance(fragment, dict) else None
    if isinstance(terms, list):
        return [str(term) for term in terms if str(term)]
    return []


def _specialized_blueprint_text(group_id: str, fragment_id: str, text_key: str) -> str:
    group = _demand_reconstruction_blueprint_fragments().get(group_id) or {}
    fragment = group.get(fragment_id) if isinstance(group, dict) else None
    value = fragment.get(text_key) if isinstance(fragment, dict) else None
    return str(value or "")


def _research_phrase_extractor_config(extractor_id: str) -> Dict[str, Any]:
    extractors = _demand_reconstruction_blueprint_fragments().get("research_phrase_extractors") or {}
    config = extractors.get(extractor_id) if isinstance(extractors, dict) else None
    return config if isinstance(config, dict) else {}


def _subject_phrase_mapping_config() -> Dict[str, Any]:
    config = _demand_reconstruction_blueprint_fragments().get("subject_phrase_mapping") or {}
    return config if isinstance(config, dict) else {}


class DemandReconstructionOutputPlanner:
    """Select user-facing demand reconstruction modules from a reusable context packet."""

    def __init__(self, boundary_guard: DemandReconstructionBoundaryGuard | None = None) -> None:
        self._boundary_guard = boundary_guard or DemandReconstructionBoundaryGuard()

    def build_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        archetype = (context.get("archetype") or {}).get("primary") or "general_project"
        builders = {
            "life_identity": self._life_identity_plan,
            "commercial_operation": self._commercial_operation_plan,
            "public_cultural_experience": self._public_cultural_experience_plan,
            "media_production": self._media_production_plan,
            "style_semantics": self._style_semantics_plan,
            "hard_constraint": self._hard_constraint_plan,
            "cultural_research": self._cultural_research_plan,
            "healthcare_care": self._healthcare_care_plan,
            "workplace_headquarters": self._workplace_headquarters_plan,
            "urban_renewal": self._urban_renewal_plan,
            "collection_museum": self._collection_museum_plan,
        }
        if self._is_urban_renewal_project(context):
            plan = self._urban_renewal_plan(context)
        elif self._is_collection_museum_project(context):
            plan = self._collection_museum_plan(context)
        elif archetype == "style_semantics":
            plan = self._style_semantics_plan(context)
        else:
            builder = builders.get(archetype)
            if builder:
                plan = builder(context)
                primary_sections = self._primary_fragment_sections(context, archetype)
                fragment_source = str((plan.get("brief_handoff_slots") or {}).get("fragment_source") or "")
                if primary_sections and not fragment_source.startswith("registry:primary_archetypes."):
                    plan["sections"] = list(plan.get("sections") or []) + primary_sections
            else:
                registry_plan = self._primary_fragment_plan(context, archetype)
                plan = registry_plan or self._general_project_plan(context)
        plan = self._apply_semantic_overrides(context, plan)
        plan["archetype"] = self._public_archetype(context, archetype)
        plan["context_source"] = context.get("context_source") or {}
        plan["routing"] = self._boundary_guard.routing_for(context)
        plan.setdefault("routing_recommendation", plan["routing"]["reason"])
        return self._boundary_guard.clamp_plan(plan)

    def _primary_fragment_plan(self, context: Dict[str, Any], archetype: str) -> Dict[str, Any] | None:
        fragment = _primary_blueprint_fragment(archetype)
        if not fragment:
            return None
        return self._fragment_plan(
            context,
            fragment,
            fragment_source=f"registry:primary_archetypes.{archetype}",
        )

    def _specialized_fragment_plan(
        self,
        context: Dict[str, Any],
        group_id: str,
        fragment_id: str,
    ) -> Dict[str, Any] | None:
        fragment = _specialized_blueprint_fragment(group_id, fragment_id)
        if not fragment:
            return None
        return self._fragment_plan(
            context,
            fragment,
            fragment_source=f"registry:{group_id}.{fragment_id}",
        )

    def _llm_semantic_fragment_plan(self, context: Dict[str, Any], group_id: str) -> Dict[str, Any] | None:
        for target in context.get("llm_semantic_fragment_targets") or []:
            if not isinstance(target, dict):
                continue
            if str(target.get("group_id") or "") != group_id:
                continue
            fragment_id = str(target.get("fragment_id") or "").strip()
            if not fragment_id:
                continue
            registry_plan = self._specialized_fragment_plan(context, group_id, fragment_id)
            if registry_plan:
                slots = dict(registry_plan.get("brief_handoff_slots") or {})
                slots["fragment_match_source"] = "llm_semantic_router"
                slots["fragment_match_evidence"] = list(target.get("evidence") or [])
                registry_plan["brief_handoff_slots"] = slots
                return registry_plan
        return None

    def _fragment_plan(
        self,
        context: Dict[str, Any],
        fragment: Dict[str, Any],
        *,
        fragment_source: str | None = None,
    ) -> Dict[str, Any] | None:
        if not (fragment.get("task_reframe") and fragment.get("viability") and fragment.get("primary_risk")):
            return None
        raw_sections = fragment.get("sections") if isinstance(fragment.get("sections"), list) else []
        sections = []
        for section in raw_sections:
            if not isinstance(section, dict) or not section.get("title") or not section.get("body"):
                continue
            items = section.get("items") if isinstance(section.get("items"), list) else []
            sections.append(
                self._section(
                    self._format_fragment_text(section.get("title") or "", context),
                    self._format_fragment_text(section.get("body") or "", context),
                    [self._format_fragment_text(item, context) for item in items if str(item)],
                    str(section.get("emphasis") or "medium"),
                )
            )
        if not sections:
            return None
        slots = {
            str(key): self._format_fragment_text(value, context)
            for key, value in dict(fragment.get("slots") or {}).items()
        }
        if fragment_source:
            slots["fragment_source"] = fragment_source
        return self._common_plan(
            context,
            task_reframe=self._format_fragment_text(fragment.get("task_reframe") or "", context),
            viability=self._format_fragment_text(fragment.get("viability") or "", context),
            primary_risk=self._format_fragment_text(fragment.get("primary_risk") or "", context),
            key_forks=[
                self._format_fragment_text(item, context)
                for item in (fragment.get("key_forks") or [])
                if str(item)
            ],
            unknowns=[
                self._format_fragment_text(item, context)
                for item in (fragment.get("unknowns") or [])
                if str(item)
            ],
            sections=sections,
            slots=slots,
            next_question=self._format_fragment_text(fragment.get("next_question") or "", context) or None,
        )

    def _primary_fragment_sections(self, context: Dict[str, Any], archetype: str) -> List[Dict[str, Any]]:
        fragment = _primary_blueprint_fragment(archetype)
        if not fragment:
            return []
        raw_sections = fragment.get("sections") if isinstance(fragment.get("sections"), list) else []
        sections: List[Dict[str, Any]] = []
        for section in raw_sections:
            if not isinstance(section, dict) or not section.get("title") or not section.get("body"):
                continue
            items = section.get("items") if isinstance(section.get("items"), list) else []
            sections.append(
                self._section(
                    self._format_fragment_text(section.get("title") or "", context),
                    self._format_fragment_text(section.get("body") or "", context),
                    [self._format_fragment_text(item, context) for item in items if str(item)],
                    str(section.get("emphasis") or "medium"),
                )
            )
        return sections

    def _format_fragment_text(self, value: Any, context: Dict[str, Any]) -> str:
        text = str(value)
        if "{" not in text:
            return text
        return text.format_map(_SafeFormatDict(self._fragment_format_values(context)))

    def _fragment_format_values(self, context: Dict[str, Any]) -> Dict[str, str]:
        return {
            "space_label": str(context.get("space_label") or context.get("project_type_name") or "空间"),
            "project_type_name": str(context.get("project_type_name") or "项目"),
            "owner_profile": self._subject_phrase(context),
            "research_subject": self._research_subject_phrase(context),
            "target_space": self._research_target_space_phrase(context),
        }

    def clamp_existing_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        return self._boundary_guard.clamp_plan(plan)

    def _apply_semantic_overrides(self, context: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        enriched = dict(plan)
        main_tensions = self._relevant_main_tensions(context)
        missing_slots = [item for item in (context.get("missing_slots") or []) if isinstance(item, dict)]

        tension_forks = [str(item.get("title") or "").strip() for item in main_tensions if item.get("title")]
        if tension_forks:
            enriched["key_forks"] = self._unique(tension_forks + list(enriched.get("key_forks") or []))
        first_tension_prompt = next(
            (str(item.get("prompt") or "").strip() for item in main_tensions if item.get("prompt")),
            "",
        )
        if first_tension_prompt:
            existing_question = str(enriched.get("next_question") or "").strip().rstrip("？?")
            if (
                existing_question
                and existing_question not in first_tension_prompt
                and existing_question not in {"目标优先级", "使用者结构", "场地与资源边界"}
            ):
                enriched["next_question"] = f"{existing_question}；同时{first_tension_prompt.rstrip('？?')}"
            else:
                enriched["next_question"] = first_tension_prompt.rstrip("？?")

        slot_notes = []
        for slot in missing_slots:
            note = str(slot.get("user_visible_note") or slot.get("note") or slot.get("label") or slot.get("slot") or "").strip()
            if note:
                slot_notes.append(note)
        if slot_notes:
            enriched["unknowns"] = self._unique(slot_notes + list(enriched.get("unknowns") or []))

        coverage = self._coverage_ceiling(context)
        if coverage:
            coverage_level = (
                coverage.get("level")
                or coverage.get("coverage_level")
                or coverage.get("ceiling")
                or coverage.get("status")
            )
            if coverage_level:
                enriched["coverage_level"] = coverage_level
                self._apply_coverage_commitment(enriched, str(coverage_level))
            note = (
                coverage.get("user_visible_note")
                or coverage.get("note")
                or coverage.get("reason")
                or coverage.get("message")
            )
            if note:
                sections = list(enriched.get("sections") or [])
                sections.append(
                    self._section(
                        "知识覆盖边界",
                        "当前判断会按知识覆盖上限控制深度，避免把低置信信息写成确定结论。",
                        [str(note)],
                        "medium",
                    )
                )
                enriched["sections"] = sections

        governance_signals = self._governance_signals(context)
        if governance_signals:
            enriched["governance_signals"] = governance_signals

        candidates = context.get("semantic_candidate_set") or (context.get("archetype") or {}).get("candidate_set")
        if candidates:
            enriched["component_intent"] = self._component_intent(main_tensions, missing_slots)
        secondary_sections = self._secondary_candidate_sections(context)
        if secondary_sections:
            enriched["sections"] = list(enriched.get("sections") or []) + secondary_sections
        composite_section = self._composite_relation_section(context)
        if composite_section:
            enriched["sections"] = list(enriched.get("sections") or []) + [composite_section]
        return enriched

    @staticmethod
    def _public_archetype(context: Dict[str, Any], fallback: str) -> Dict[str, Any]:
        archetype = context.get("archetype") or {"primary": fallback, "secondary": []}
        return {
            "primary": archetype.get("primary") or fallback,
            "secondary": list(archetype.get("secondary") or []),
            "downweighted": list(archetype.get("downweighted") or []),
            "routing_target": archetype.get("routing_target") or "demand_reconstruction",
        }

    @staticmethod
    def _unique(values: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in values:
            text = str(value or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result

    @staticmethod
    def _coverage_ceiling(context: Dict[str, Any]) -> Dict[str, Any]:
        coverage = context.get("knowledge_coverage_ceiling")
        if isinstance(coverage, dict) and coverage:
            return coverage
        advisor_packet = context.get("advisor_packet") or {}
        context_packet = advisor_packet.get("context_packet") or {}
        knowledge_binding = context_packet.get("knowledge_binding") or {}
        fallback = knowledge_binding.get("coverage_ceiling") or {}
        return fallback if isinstance(fallback, dict) else {}

    @staticmethod
    def _apply_coverage_commitment(plan: Dict[str, Any], coverage_level: str) -> None:
        level = str(coverage_level or "").strip().lower()
        slots = plan.get("brief_handoff_slots") if isinstance(plan.get("brief_handoff_slots"), dict) else {}
        project_object = str(slots.get("project_object") or "\u5f53\u524d\u9879\u76ee").strip()
        if level in {"partial_specialist", "l1", "neighbor_transfer", "l1_neighbor_transfer"}:
            existing_risk = str(plan.get("primary_risk") or "").strip()
            plan["project_viability_judgment"] = (
                f"\u5f53\u524d\u53ea\u80fd\u6309\u90bb\u8fd1\u8fc1\u79fb\u5224\u65ad{project_object}\uff0c\u53ef\u501f\u7528\u547d\u4e2d\u89c4\u5219\u7684\u7ed3\u6784\u7ea6\u675f\uff0c"
                "\u4f46\u4e0d\u80fd\u628a\u5b83\u5199\u6210\u5df2\u7ecf\u9a8c\u8bc1\u7684\u5b8c\u6574\u4e13\u79d1\u7ed3\u8bba\u3002"
            )
            plan["primary_risk"] = (
                "\u4e0d\u80fd\u628a\u90bb\u8fd1\u89c4\u5219\u5192\u5145\u5b8c\u6574\u4e13\u79d1\u7ed3\u8bba\uff1b"
                + (existing_risk if existing_risk else "\u5e94\u5148\u8865\u9f50\u4e13\u79d1\u77e5\u8bc6\u8986\u76d6\u3001\u573a\u5730\u8fb9\u754c\u548c\u5173\u952e\u53c2\u6570\u3002")
            )
            return
        if level not in {"general_method_only", "methodology_framework", "low", "l0", "limited"}:
            return
        plan["task_reframe"] = (
            f"\u5f53\u524d\u53ea\u80fd\u5728\u901a\u7528\u65b9\u6cd5\u8bba\u5c42\u9762\u91cd\u6784{project_object}\uff0c\u5148\u8bc6\u522b\u76ee\u6807\u3001\u4f7f\u7528\u8005\u3001\u5173\u952e\u7ea6\u675f\u548c\u77e5\u8bc6\u7f3a\u53e3\uff0c"
            "\u4e0d\u80fd\u628a\u4e13\u79d1\u7ed3\u8bba\u5199\u6210\u5df2\u7ecf\u9a8c\u8bc1\u7684\u786e\u5b9a\u5224\u65ad\u3002"
        )
        plan["project_viability_judgment"] = (
            "\u5f53\u524d\u53ea\u80fd\u6309\u901a\u7528\u65b9\u6cd5\u8bba\u5224\u65ad\u9879\u76ee\u8def\u5f84\uff0c\u4e0d\u80fd\u628a\u4e13\u79d1\u7ed3\u8bba\u5199\u6210\u5df2\u7ecf\u9a8c\u8bc1\u7684\u786e\u5b9a\u5224\u65ad\u3002"
        )
        existing_risk = str(plan.get("primary_risk") or "").strip()
        plan["primary_risk"] = (
            "\u4e0d\u80fd\u8fc7\u5ea6\u627f\u8bfa\u4e13\u79d1\u6df1\u5ea6\uff1b"
            + (existing_risk if existing_risk else "\u5e94\u5148\u8865\u9f50\u77e5\u8bc6\u8986\u76d6\u3001\u573a\u5730\u8fb9\u754c\u548c\u5173\u952e\u53c2\u6570\u3002")
        )
    @staticmethod
    def _governance_signals(context: Dict[str, Any]) -> List[Dict[str, Any]]:
        classification = context.get("classification") or {}
        if not isinstance(classification, dict):
            classification = {}
        signals: List[Dict[str, Any]] = []
        if classification.get("coverage_gap"):
            signals.append(
                {
                    "code": "coverage_gap",
                    "track": "space_registry",
                    "review_queue": "space_registry_review",
                    "severity": "P1",
                    "meaning": "空间分类或语义覆盖存在缺口，需要进入 registry/边界样本治理。",
                    "user_visible": False,
                }
            )
        ticket = classification.get("knowledge_gap_ticket")
        if isinstance(ticket, dict) and ticket:
            signals.append(
                {
                    "code": "knowledge_gap_ticket",
                    "track": "knowledge_asset_pipeline",
                    "review_queue": "knowledge_asset_review",
                    "severity": "P2",
                    "meaning": "已生成知识缺口线索，需要后续沉淀为审核通过的知识资产。",
                    "ticket": {
                        "gap_type": ticket.get("gap_type"),
                        "project_type": ticket.get("project_type"),
                        "summary": ticket.get("summary"),
                    },
                    "source": ticket.get("source"),
                    "evidence": ticket.get("evidence"),
                    "scan_result": ticket.get("scan_result"),
                    "matched_targets": ticket.get("matched_targets"),
                    "user_visible": False,
                }
            )
        fragment_candidate = classification.get("new_fragment_candidate")
        if isinstance(fragment_candidate, dict) and fragment_candidate:
            signals.append(
                {
                    "code": "new_fragment_candidate",
                    "track": "blueprint_fragment_pipeline",
                    "review_queue": "blueprint_fragment_review",
                    "severity": "P2",
                    "meaning": "LLM 识别到现有规则蓝图无法覆盖的新型需求，需要评估是否沉淀为新的规则碎片。",
                    "candidate": {
                        "fragment_id": fragment_candidate.get("fragment_id"),
                        "project_object": fragment_candidate.get("project_object"),
                        "summary": fragment_candidate.get("summary"),
                    },
                    "source": fragment_candidate.get("source"),
                    "evidence": fragment_candidate.get("evidence"),
                    "scan_result": fragment_candidate.get("scan_result"),
                    "user_visible": False,
                }
            )
        coverage = DemandReconstructionOutputPlanner._coverage_ceiling(context)
        coverage_level = (
            coverage.get("level")
            or coverage.get("coverage_level")
            or coverage.get("ceiling")
            or coverage.get("status")
        )
        if str(coverage_level or "").strip().lower() in {"partial_specialist", "l1", "neighbor_transfer"}:
            signals.append(
                {
                    "code": "knowledge_coverage_watch",
                    "track": "coverage_watch",
                    "review_queue": "coverage_watch_pool",
                    "severity": "P3",
                    "meaning": "当前仅能做邻近迁移判断，需要观察是否应补专科知识包。",
                    "user_visible": False,
                }
            )
        return signals

    @staticmethod
    def _component_intent(
        main_tensions: List[Dict[str, Any]],
        missing_slots: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        intents: List[Dict[str, Any]] = []
        if main_tensions:
            tension_items = [
                str(item.get("title") or item.get("label") or "").strip()
                for item in main_tensions
                if str(item.get("title") or item.get("label") or "").strip()
            ][:3]
            prompt = str(main_tensions[0].get("prompt") or "").strip()
            intents.append(
                {
                    "type": "conflict_check",
                    "reason": "main_tensions",
                    "title": "关键取舍",
                    "items": tension_items,
                    "prompt": prompt,
                }
            )
        if missing_slots:
            slot_items = [
                str(item.get("user_visible_note") or item.get("note") or item.get("label") or item.get("slot") or "").strip()
                for item in missing_slots
                if str(item.get("user_visible_note") or item.get("note") or item.get("label") or item.get("slot") or "").strip()
            ][:4]
            intents.append(
                {
                    "type": "data_checklist",
                    "reason": "missing_slots",
                    "title": "条件清单",
                    "items": slot_items,
                }
            )
        if not intents:
            intents.append(
                {
                    "type": "insight_panel",
                    "reason": "default_reframe",
                    "title": "洞察面板",
                    "items": ["先把项目成立条件、关键风险和下一步追问收束成一个可判断的方向。"],
                }
            )
        return intents

    def _secondary_candidate_sections(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        sections: List[Dict[str, Any]] = []
        primary = str((context.get("archetype") or {}).get("primary") or "")
        secondary_ids = [str(item) for item in ((context.get("archetype") or {}).get("secondary") or []) if item]
        for candidate_id in secondary_ids:
            if candidate_id == primary:
                continue
            fragment = _secondary_blueprint_fragment(candidate_id)
            if not fragment:
                continue
            items = fragment.get("items") if isinstance(fragment.get("items"), list) else []
            sections.append(
                self._section(
                    self._format_fragment_text(fragment.get("title") or "", context),
                    self._format_fragment_text(fragment.get("body") or "", context),
                    [self._format_fragment_text(item, context) for item in items if str(item)],
                    str(fragment.get("emphasis") or "medium"),
                )
            )
            if len(sections) >= 2:
                break
        return sections

    def _composite_relation_section(self, context: Dict[str, Any]) -> Dict[str, Any] | None:
        secondary_ids = [str(item) for item in ((context.get("archetype") or {}).get("secondary") or []) if item]
        if not secondary_ids:
            return None
        labels = [self._candidate_label(item) for item in secondary_ids[:3]]
        labels = [label for label in labels if label]
        if not labels:
            return None
        return self._section(
            "复合关系",
            "这个项目不是单一类型题，次要候选会改变任务书的边界和追问顺序。",
            [f"除主线外，还需要校准：{'、'.join(labels)}。"],
            "medium",
        )

    @staticmethod
    def _candidate_label(candidate_id: str) -> str:
        labels = {
            "life_identity": "生活身份",
            "commercial_operation": "商业运营",
            "public_cultural_experience": "公共文化体验",
            "media_production": "媒体生产",
            "style_semantics": "风格语义",
            "hard_constraint": "硬性技术约束",
            "cultural_research": "文化研究",
            "healthcare_care": "医疗照护",
            "workplace_headquarters": "办公协作",
            "urban_renewal": "城市更新",
            "collection_museum": "收藏展陈",
            "general_project": "通用项目结构",
        }
        return labels.get(str(candidate_id), str(candidate_id))

    @staticmethod
    def _relevant_main_tensions(context: Dict[str, Any]) -> List[Dict[str, Any]]:
        source = str(context.get("source_message") or "")
        relevant: List[Dict[str, Any]] = []
        for tension in context.get("main_tensions") or []:
            if not isinstance(tension, dict):
                continue
            relevance_terms = [str(term) for term in (tension.get("relevance_terms") or []) if str(term)]
            if relevance_terms and not any(term in source for term in relevance_terms):
                # Tension carries domain-specific framing (declared via registry
                # relevance_terms) that has zero support in the source message.
                # Treat it as an unverified main tension and drop it instead of
                # injecting a frame the user never raised.
                continue
            relevant.append(tension)
        return relevant

    def _life_identity_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._life_identity_specialty_plan(context)
        if registry_plan:
            return registry_plan
        residential_fragment = _specialized_blueprint_fragment(
            "life_identity_specialties",
            "residential_life_order",
        )
        if residential_fragment and self._life_identity_specialty_matches(
            context,
            "residential_life_order",
            residential_fragment,
        ):
            residential_plan = self._residential_life_order_plan(context)
            if residential_plan:
                return residential_plan
        primary_plan = self._primary_fragment_plan(context, "life_identity")
        if primary_plan:
            return primary_plan
        return self._general_project_plan(context)

    def _life_identity_specialty_plan(self, context: Dict[str, Any]) -> Dict[str, Any] | None:
        llm_plan = self._llm_semantic_fragment_plan(context, "life_identity_specialties")
        if llm_plan:
            return llm_plan
        group = _demand_reconstruction_blueprint_fragments().get("life_identity_specialties") or {}
        if not isinstance(group, dict):
            return None
        for fragment_id, fragment in group.items():
            if self._is_default_blueprint_fragment(fragment) or not isinstance(fragment, dict):
                continue
            if not self._life_identity_specialty_matches(context, fragment_id, fragment):
                continue
            registry_plan = self._specialized_fragment_plan(context, "life_identity_specialties", str(fragment_id))
            if registry_plan:
                return registry_plan
        return None

    @staticmethod
    def _life_identity_specialty_matches(
        context: Dict[str, Any],
        fragment_id: str,
        fragment: Dict[str, Any],
    ) -> bool:
        text = str(context.get("source_message") or "")
        terms = fragment.get("trigger_terms") if isinstance(fragment.get("trigger_terms"), list) else []
        if any(str(term) and str(term) in text for term in terms):
            return True
        axes = context.get("semantic_axes") or {}
        return DemandReconstructionOutputPlanner._fragment_semantic_axis_matches(axes, fragment)

    def _residential_life_order_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._specialized_fragment_plan(
            context,
            "life_identity_specialties",
            "residential_life_order",
        )
        if registry_plan:
            return registry_plan
        return self._general_project_plan(context)

    def _commercial_operation_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if self._is_workplace_headquarters_project(context):
            return self._workplace_headquarters_plan(context)
        if self._is_hotel_hospitality_operation(context):
            return self._hotel_hospitality_operation_plan(context)
        if self._is_shared_living_amenity_operation(context):
            return self._shared_living_amenity_operation_plan(context)
        registry_plan = self._commercial_specialty_plan(context)
        if registry_plan:
            return registry_plan
        return self._generic_commercial_operation_plan(context)

    def _generic_commercial_operation_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._primary_fragment_plan(context, "commercial_operation")
        if registry_plan:
            return registry_plan
        return self._general_project_plan(context)

    def _commercial_specialty_plan(self, context: Dict[str, Any]) -> Dict[str, Any] | None:
        llm_plan = self._llm_semantic_fragment_plan(context, "commercial_specialties")
        if llm_plan:
            return llm_plan
        group = _demand_reconstruction_blueprint_fragments().get("commercial_specialties") or {}
        if not isinstance(group, dict):
            return None
        scored_fragments: List[tuple[int, int, str]] = []
        for index, (fragment_id, fragment) in enumerate(group.items()):
            if not isinstance(fragment, dict) or not fragment.get("sections"):
                continue
            score = self._commercial_specialty_score(context, str(fragment_id), fragment)
            if score <= 0:
                continue
            scored_fragments.append((score, -index, str(fragment_id)))
        if not scored_fragments:
            return None
        _score, _index, fragment_id = max(scored_fragments)
        return self._specialized_fragment_plan(context, "commercial_specialties", fragment_id)

    @staticmethod
    def _commercial_specialty_score(context: Dict[str, Any], fragment_id: str, fragment: Dict[str, Any]) -> int:
        return DemandReconstructionOutputPlanner._fragment_term_rule_score(
            context,
            "commercial_specialties",
            fragment,
        )

    @staticmethod
    def _is_hotel_hospitality_operation(context: Dict[str, Any]) -> bool:
        text = str(context.get("source_message") or "")
        return any(term in text for term in _specialized_blueprint_trigger_terms("hospitality_specialties", "hotel_lobby"))

    @staticmethod
    def _is_shared_living_amenity_operation(context: Dict[str, Any]) -> bool:
        text = str(context.get("source_message") or "")
        return any(
            term in text
            for term in _specialized_blueprint_trigger_terms(
                "hospitality_specialties",
                "long_term_apartment_amenity",
            )
        )

    def _hotel_hospitality_operation_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._specialized_fragment_plan(context, "hospitality_specialties", "hotel_lobby")
        if registry_plan:
            return registry_plan
        return self._generic_commercial_operation_plan(context)

    def _shared_living_amenity_operation_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._specialized_fragment_plan(
            context,
            "hospitality_specialties",
            "long_term_apartment_amenity",
        )
        if registry_plan:
            return registry_plan
        return self._generic_commercial_operation_plan(context)

    def _retail_brand_conversion_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._specialized_fragment_plan(context, "commercial_specialties", "retail_brand_conversion")
        if registry_plan:
            return registry_plan
        return self._generic_commercial_operation_plan(context)

    def _media_production_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._media_specialty_plan(context)
        if registry_plan:
            return registry_plan
        primary_plan = self._primary_fragment_plan(context, "media_production")
        if primary_plan:
            return primary_plan
        return self._general_media_production_plan(context)

    def _media_specialty_plan(self, context: Dict[str, Any]) -> Dict[str, Any] | None:
        llm_plan = self._llm_semantic_fragment_plan(context, "media_specialties")
        if llm_plan:
            return llm_plan
        group = _demand_reconstruction_blueprint_fragments().get("media_specialties") or {}
        if not isinstance(group, dict):
            return None
        scored_fragments: List[tuple[int, int, str]] = []
        for index, (fragment_id, fragment) in enumerate(group.items()):
            if fragment_id.endswith("_exclusion") or not isinstance(fragment, dict) or not fragment.get("sections"):
                continue
            score = self._media_specialty_score(context, str(fragment_id), fragment)
            if score <= 0:
                continue
            scored_fragments.append((score, -index, str(fragment_id)))
        if not scored_fragments:
            return None
        _score, _index, fragment_id = max(scored_fragments)
        return self._specialized_fragment_plan(context, "media_specialties", fragment_id)

    @staticmethod
    def _media_specialty_score(context: Dict[str, Any], fragment_id: str, fragment: Dict[str, Any]) -> int:
        return DemandReconstructionOutputPlanner._fragment_term_rule_score(
            context,
            "media_specialties",
            fragment,
        )

    @staticmethod
    def _fragment_term_rule_score(context: Dict[str, Any], group_id: str, fragment: Dict[str, Any]) -> int:
        text = str(context.get("source_message") or "")
        exclusion_groups = fragment.get("exclude_when_any_fragment_terms") or []
        if isinstance(exclusion_groups, str):
            exclusion_groups = [exclusion_groups]
        for exclusion_group in exclusion_groups:
            exclusion_terms = _specialized_blueprint_trigger_terms(group_id, str(exclusion_group))
            if any(term in text for term in exclusion_terms):
                return 0
        required_groups = fragment.get("require_any_fragment_terms") or []
        if isinstance(required_groups, str):
            required_groups = [required_groups]
        for required_group in required_groups:
            required_terms = _specialized_blueprint_trigger_terms(group_id, str(required_group))
            if not any(term in text for term in required_terms):
                return 0
        return DemandReconstructionOutputPlanner._fragment_trigger_score(context, fragment)

    def _general_media_production_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._specialized_fragment_plan(context, "media_specialties", "live_commerce_studio")
        if registry_plan:
            return registry_plan
        return self._general_project_plan(context)

    def _public_cultural_experience_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._public_cultural_specialty_plan(context)
        if registry_plan:
            return registry_plan
        return self._generic_public_cultural_plan(context)

    def _public_cultural_specialty_plan(self, context: Dict[str, Any]) -> Dict[str, Any] | None:
        llm_plan = self._llm_semantic_fragment_plan(context, "public_cultural_specialties")
        if llm_plan:
            return llm_plan
        group = _demand_reconstruction_blueprint_fragments().get("public_cultural_specialties") or {}
        if not isinstance(group, dict):
            return None
        scored_fragments: List[tuple[int, int, str]] = []
        for index, (fragment_id, fragment) in enumerate(group.items()):
            if self._is_default_blueprint_fragment(fragment) or not isinstance(fragment, dict) or not fragment.get("sections"):
                continue
            score = self._public_cultural_specialty_score(context, fragment)
            if score <= 0:
                continue
            scored_fragments.append((score, -index, str(fragment_id)))
        if not scored_fragments:
            return None
        _score, _index, fragment_id = max(scored_fragments)
        registry_plan = self._specialized_fragment_plan(context, "public_cultural_specialties", fragment_id)
        if registry_plan:
            fragment = group.get(fragment_id) if isinstance(group, dict) else None
            return self._apply_anchor_missing_postprocess(
                context,
                fragment if isinstance(fragment, dict) else {},
                registry_plan,
            )
        return None

    @staticmethod
    def _public_cultural_specialty_score(context: Dict[str, Any], fragment: Dict[str, Any]) -> int:
        return DemandReconstructionOutputPlanner._fragment_trigger_score(context, fragment)

    @staticmethod
    def _is_performance_heritage_project(text: str) -> bool:
        return any(
            term in text
            for term in _specialized_blueprint_trigger_terms("public_cultural_specialties", "performance_heritage")
        )

    @staticmethod
    def _is_farm_learning_center(text: str) -> bool:
        return any(
            term in text
            for term in _specialized_blueprint_trigger_terms("public_cultural_specialties", "farm_learning_center")
        )

    @staticmethod
    def _apply_anchor_missing_postprocess(
        context: Dict[str, Any],
        fragment: Dict[str, Any],
        plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        postprocess = fragment.get("anchor_missing_postprocess") if isinstance(fragment, dict) else None
        if not isinstance(postprocess, dict):
            return plan
        anchor_terms_key = str(postprocess.get("anchor_terms_key") or "")
        replacement_key = str(postprocess.get("replacement_key") or "")
        anchor_terms = fragment.get(anchor_terms_key) if anchor_terms_key else []
        text = str(context.get("source_message") or "")
        if any(str(term) and str(term) in text for term in anchor_terms or []):
            return plan
        cleaned = dict(plan)
        configured_replacements = fragment.get(replacement_key) if replacement_key else None
        replacements = {
            str(old): str(new)
            for old, new in (configured_replacements or {}).items()
            if str(old) and str(new)
        } if isinstance(configured_replacements, dict) else {}

        def replace_text(value: Any) -> Any:
            if isinstance(value, str):
                result = value
                for old, new in replacements.items():
                    result = result.replace(old, new)
                return result
            if isinstance(value, list):
                return [replace_text(item) for item in value]
            if isinstance(value, dict):
                return {key: replace_text(item) for key, item in value.items()}
            return value

        for key in ("task_reframe", "project_viability_judgment", "primary_risk", "next_question", "routing_recommendation"):
            if key in cleaned:
                cleaned[key] = replace_text(cleaned[key])
        cleaned["key_forks"] = replace_text(cleaned.get("key_forks") or [])
        cleaned["unknowns"] = replace_text(cleaned.get("unknowns") or [])
        cleaned["sections"] = replace_text(cleaned.get("sections") or [])
        cleaned["brief_handoff_slots"] = replace_text(cleaned.get("brief_handoff_slots") or {})
        return cleaned

    @staticmethod
    def _is_library_reading_project(text: str) -> bool:
        return any(
            term in text
            for term in _specialized_blueprint_trigger_terms("public_cultural_specialties", "library_reading")
        )

    def _library_reading_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._specialized_fragment_plan(context, "public_cultural_specialties", "library_reading")
        if registry_plan:
            return registry_plan
        return self._generic_public_cultural_plan(context)

    def _generic_public_cultural_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        text = str(context.get("source_message") or "")
        generic_fragment = _specialized_blueprint_fragment(
            "public_cultural_specialties",
            "generic_exhibition",
        )
        if generic_fragment and (
            self._public_cultural_specialty_score(context, generic_fragment) > 0
            or self._has_generic_exhibition_material_topic(text)
        ):
            registry_plan = self._specialized_fragment_plan(
                context,
                "public_cultural_specialties",
                "generic_exhibition",
            )
            if registry_plan:
                if self._has_generic_exhibition_material_topic(text):
                    registry_plan = self._with_generic_exhibition_material_topic(registry_plan)
                return registry_plan

        primary_plan = self._primary_fragment_plan(context, "public_cultural_experience")
        if primary_plan:
            return primary_plan

        return self._general_project_plan(context)

    @staticmethod
    def _has_generic_exhibition_material_topic(text: str) -> bool:
        return any(
            term in text
            for term in _specialized_blueprint_terms(
                "public_cultural_specialties",
                "generic_exhibition",
                "material_topic_terms",
            )
        )

    @staticmethod
    def _with_generic_exhibition_material_topic(plan: Dict[str, Any]) -> Dict[str, Any]:
        material_item = _specialized_blueprint_text(
            "public_cultural_specialties",
            "generic_exhibition",
            "material_topic_item",
        )
        if not material_item:
            return plan
        enriched = dict(plan)
        sections: List[Dict[str, Any]] = []
        appended = False
        for section in plan.get("sections") or []:
            if not isinstance(section, dict):
                continue
            next_section = dict(section)
            if not appended and next_section.get("title") == "叙事路径":
                items = list(next_section.get("items") or [])
                if material_item not in items:
                    items.append(material_item)
                next_section["items"] = items
                appended = True
            sections.append(next_section)
        enriched["sections"] = sections or plan.get("sections")
        return enriched

    def _style_semantics_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._style_specialty_plan(context) or self._primary_fragment_plan(context, "style_semantics")
        if registry_plan:
            return registry_plan
        return self._general_project_plan(context)

    def _style_specialty_plan(self, context: Dict[str, Any]) -> Dict[str, Any] | None:
        llm_plan = self._llm_semantic_fragment_plan(context, "style_specialties")
        if llm_plan:
            return llm_plan
        group = _demand_reconstruction_blueprint_fragments().get("style_specialties") or {}
        if not isinstance(group, dict):
            return None
        scored_fragments: List[tuple[int, int, str]] = []
        for index, (fragment_id, fragment) in enumerate(group.items()):
            if not isinstance(fragment, dict) or not fragment.get("sections"):
                continue
            score = self._fragment_trigger_score(context, fragment)
            if score <= 0:
                continue
            scored_fragments.append((score, -index, str(fragment_id)))
        if not scored_fragments:
            return None
        _score, _index, fragment_id = max(scored_fragments)
        return self._specialized_fragment_plan(context, "style_specialties", fragment_id)

    @staticmethod
    def _fragment_trigger_score(context: Dict[str, Any], fragment: Dict[str, Any]) -> int:
        text = str(context.get("source_message") or "")
        terms = fragment.get("trigger_terms") if isinstance(fragment.get("trigger_terms"), list) else []
        score = sum(1 for term in terms if str(term) and str(term) in text)
        axes = context.get("semantic_axes") or {}
        axis_matches = fragment.get("semantic_axis_matches") if isinstance(fragment, dict) else None
        if isinstance(axis_matches, dict):
            for axis_id, expected_values in axis_matches.items():
                actual_values = set(axes.get(str(axis_id)) or [])
                score += sum(1 for value in expected_values or [] if str(value) in actual_values)
        return score

    def _hard_constraint_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._technical_specialty_plan(context)
        if registry_plan:
            return registry_plan
        primary_plan = self._primary_fragment_plan(context, "hard_constraint")
        if primary_plan:
            return primary_plan
        return self._technical_constraint_plan(context)

    def _technical_specialty_plan(self, context: Dict[str, Any]) -> Dict[str, Any] | None:
        llm_plan = self._llm_semantic_fragment_plan(context, "technical_specialties")
        if llm_plan:
            return llm_plan
        group = _demand_reconstruction_blueprint_fragments().get("technical_specialties") or {}
        if not isinstance(group, dict):
            return None
        for fragment_id, fragment in group.items():
            if self._is_default_blueprint_fragment(fragment) or not isinstance(fragment, dict):
                continue
            if not self._technical_specialty_matches(context, fragment_id, fragment):
                continue
            registry_plan = self._specialized_fragment_plan(context, "technical_specialties", str(fragment_id))
            if registry_plan:
                return registry_plan
        return None

    @staticmethod
    def _technical_specialty_matches(
        context: Dict[str, Any],
        fragment_id: str,
        fragment: Dict[str, Any],
    ) -> bool:
        text = str(context.get("source_message") or "")
        terms = fragment.get("trigger_terms") if isinstance(fragment.get("trigger_terms"), list) else []
        if any(str(term) and str(term) in text for term in terms):
            return True
        axes = context.get("semantic_axes") or {}
        return DemandReconstructionOutputPlanner._fragment_semantic_axis_matches(axes, fragment)

    @staticmethod
    def _is_default_blueprint_fragment(fragment: Any) -> bool:
        return isinstance(fragment, dict) and fragment.get("is_default_fragment") is True

    @staticmethod
    def _fragment_semantic_axis_matches(axes: Dict[str, Any], fragment: Dict[str, Any]) -> bool:
        axis_matches = fragment.get("semantic_axis_matches") if isinstance(fragment, dict) else None
        if not isinstance(axis_matches, dict):
            return False
        for axis_id, expected_values in axis_matches.items():
            actual_values = set(axes.get(str(axis_id)) or [])
            if any(str(value) in actual_values for value in expected_values or []):
                return True
        return False

    def _technical_constraint_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._specialized_fragment_plan(context, "technical_specialties", "generic_constraint")
        if registry_plan:
            return registry_plan
        return self._general_project_plan(context)

    @staticmethod
    def _technical_constraint_items(context: Dict[str, Any]) -> List[str]:
        axes = context.get("semantic_axes") or {}
        constraints = set(axes.get("critical_constraints") or [])
        items: List[str] = []
        if "fire_structure" in constraints:
            items.append("消防、防火分区、疏散和结构条件属于优先级最高的成立边界。")
        if "mep_climate" in constraints:
            items.append("恒温恒湿、新风、电力或环境控制会决定设备层级和维护空间。")
        if "security_privacy" in constraints:
            items.append("安防、隐私和后台管理会改变开放区、查阅区和库区的分离方式。")
        if "acoustics" in constraints:
            items.append("声学或隔音要求会改变材料、构造和相邻功能关系。")
        if "accessibility_safety" in constraints:
            items.append("无障碍、安全和特殊人群尺度会改变动线、界面和停留策略。")
        if not items:
            items.append("先把法规、安全、设备、运营维护四类边界分清，再谈空间表达。")
        return items[:5]

    def _cultural_research_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._primary_fragment_plan(context, "cultural_research")
        if registry_plan:
            return registry_plan
        return self._general_project_plan(context)

    @staticmethod
    def _research_subject_phrase(context: Dict[str, Any]) -> str:
        text = str(context.get("source_message") or "")
        config = _research_phrase_extractor_config("cultural_research")
        start_terms = [str(term) for term in (config.get("subject_start_terms") or []) if str(term)]
        for marker in [str(term) for term in (config.get("subject_end_markers") or []) if str(term)]:
            if marker in text:
                left = text.split(marker, 1)[0]
                start_term = next((term for term in start_terms if term in left), "")
                if start_term:
                    candidate = left.rsplit(start_term, 1)[-1].strip(" ，,。；;：:")
                    if candidate:
                        return candidate[:24]
        return "文化主题"

    @staticmethod
    def _research_target_space_phrase(context: Dict[str, Any]) -> str:
        text = str(context.get("source_message") or "")
        config = _research_phrase_extractor_config("cultural_research")
        start_marker = str(config.get("target_start_marker") or "")
        if start_marker and start_marker in text:
            right = text.split(start_marker, 1)[-1]
            for marker in [str(term) for term in (config.get("target_end_markers") or []) if str(term)]:
                if marker in right:
                    candidate = right.split(marker, 1)[0].strip(" ，,。；;：:")
                    if candidate:
                        return candidate[:24]
        return str(context.get("space_label") or context.get("project_type_name") or "当代空间")

    def _urban_renewal_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._specialized_fragment_plan(
            context,
            "urban_renewal_specialties",
            "district_renewal",
        )
        if registry_plan:
            return registry_plan
        return self._general_project_plan(context)

    def _collection_museum_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._specialized_fragment_plan(
            context,
            "public_cultural_specialties",
            "collection_museum",
        )
        if registry_plan:
            return registry_plan
        return self._generic_public_cultural_plan(context)

    @staticmethod
    def _is_collection_museum_project(context: Dict[str, Any]) -> bool:
        text = str(context.get("source_message") or "")
        terms = _specialized_blueprint_trigger_terms(
            "public_cultural_specialties",
            "collection_museum",
        )
        return any(term in text for term in _merged_terms(terms, _blueprint_override_terms("collection_museum")))

    @staticmethod
    def _is_urban_renewal_project(context: Dict[str, Any]) -> bool:
        text = str(context.get("source_message") or "")
        project_type = str(context.get("project_type") or "")
        if project_type in {"urban_renewal", "city_renewal", "community_renewal"}:
            return True
        terms = _specialized_blueprint_trigger_terms(
            "urban_renewal_specialties",
            "district_renewal",
        )
        return any(term in text for term in _merged_terms(terms, _blueprint_override_terms("urban_renewal")))

    def _general_project_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if self._is_healthcare_care_project(context):
            return self._healthcare_care_plan(context)
        if self._is_workplace_headquarters_project(context):
            return self._workplace_headquarters_plan(context)

        registry_plan = self._primary_fragment_plan(context, "general_project")
        if registry_plan:
            return registry_plan
        return self._common_plan(
            context,
            task_reframe="当前需要先补齐项目对象、目标和约束。",
            viability="当前信息不足以冻结设计任务书。",
            primary_risk="头号风险是过早给方案。",
            key_forks=["目标优先级", "使用者结构", "场地与资源边界"],
            unknowns=["空间对象", "使用方式", "预算与落地条件"],
            sections=[],
            slots={},
        )

    def _workplace_headquarters_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if self._is_professional_service_workplace(context):
            return self._professional_service_workplace_plan(context)
        registry_plan = self._specialized_fragment_plan(context, "workplace_specialties", "headquarters")
        if registry_plan:
            return registry_plan
        return self._general_project_plan(context)

    def _professional_service_workplace_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._specialized_fragment_plan(context, "workplace_specialties", "professional_service")
        if registry_plan:
            return registry_plan
        return self._general_project_plan(context)

    @staticmethod
    def _is_professional_service_workplace(context: Dict[str, Any]) -> bool:
        text = str(context.get("source_message") or "")
        return any(
            term in text
            for term in _specialized_blueprint_trigger_terms("workplace_specialties", "professional_service")
        )

    @staticmethod
    def _is_workplace_headquarters_project(context: Dict[str, Any]) -> bool:
        text = str(context.get("source_message") or "")
        project_type = str(context.get("project_type") or "")
        if project_type in {"commercial_office", "office_workspace", "workplace"}:
            return True
        terms = _specialized_blueprint_trigger_terms("workplace_specialties", "headquarters")
        # Keep generic override words such as "员工" or "办公" from stealing a
        # brand exhibition or commercial-reception project. The planner should
        # enter workplace only from explicit headquarters/workplace terms or a
        # classified workplace project type; weaker workplace signals remain
        # visible through secondary candidates instead of changing the main plan.
        strong_terms = [
            term
            for term in _merged_terms(terms, _blueprint_override_terms("workplace_headquarters"))
            if term not in {"员工", "办公"}
        ]
        return any(term in text for term in strong_terms)

    def _healthcare_care_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if self._is_dental_clinic_project(context):
            return self._dental_clinic_plan(context)
        if self._is_maternity_center_project(context):
            return self._maternity_center_plan(context)
        if self._is_rehabilitation_center_project(context):
            return self._rehabilitation_center_plan(context)

        registry_plan = self._primary_fragment_plan(context, "healthcare_care")
        if registry_plan:
            return registry_plan
        return self._general_project_plan(context)

    def _dental_clinic_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._specialized_fragment_plan(context, "healthcare_specialties", "dental_clinic")
        if registry_plan:
            return registry_plan
        return self._general_project_plan(context)

    @staticmethod
    def _is_dental_clinic_project(context: Dict[str, Any]) -> bool:
        text = str(context.get("source_message") or "")
        return any(term in text for term in _specialized_blueprint_trigger_terms("healthcare_specialties", "dental_clinic"))

    def _maternity_center_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._specialized_fragment_plan(context, "healthcare_specialties", "maternity_center")
        if registry_plan:
            return registry_plan
        return self._general_project_plan(context)

    @staticmethod
    def _is_maternity_center_project(context: Dict[str, Any]) -> bool:
        text = str(context.get("source_message") or "")
        return any(
            term in text
            for term in _specialized_blueprint_trigger_terms("healthcare_specialties", "maternity_center")
        )

    def _rehabilitation_center_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        registry_plan = self._specialized_fragment_plan(context, "healthcare_specialties", "rehabilitation_center")
        if registry_plan:
            return registry_plan
        return self._general_project_plan(context)

    @staticmethod
    def _is_rehabilitation_center_project(context: Dict[str, Any]) -> bool:
        text = str(context.get("source_message") or "")
        return any(
            term in text
            for term in _specialized_blueprint_trigger_terms("healthcare_specialties", "rehabilitation_center")
        )

    @staticmethod
    def _is_healthcare_care_project(context: Dict[str, Any]) -> bool:
        text = str(context.get("source_message") or "")
        project_type = str(context.get("project_type") or "")
        if project_type == "healthcare_wellness":
            return True
        specialty_terms: List[str] = []
        for fragment_id in ("dental_clinic", "maternity_center", "rehabilitation_center"):
            specialty_terms.extend(_specialized_blueprint_trigger_terms("healthcare_specialties", fragment_id))
        return any(term in text for term in _merged_terms(specialty_terms, _blueprint_override_terms("healthcare_care")))

    def _common_plan(
        self,
        context: Dict[str, Any],
        *,
        task_reframe: str,
        viability: str,
        primary_risk: str,
        key_forks: List[str],
        unknowns: List[str],
        sections: List[Dict[str, Any]],
        slots: Dict[str, Any],
        next_question: str | None = None,
    ) -> Dict[str, Any]:
        merged_slots = {
            "project_object": context.get("space_label") or context.get("project_type_name") or "空间项目",
            "project_type": context.get("project_type"),
            "project_type_name": context.get("project_type_name"),
            **slots,
        }
        archetype = (context.get("archetype") or {}).get("primary")
        if archetype == "life_identity" and not merged_slots.get("owner_profile"):
            merged_slots["owner_profile"] = self._subject_phrase(context)
        return {
            "reconstruction_type": "demand_reconstruction",
            "artifact_name": "action_blueprint",
            "display_title": "需求重构",
            "display_artifact_name": "行动蓝图",
            "task_reframe": task_reframe,
            "project_viability_judgment": viability,
            "primary_risk": primary_risk,
            "key_forks": key_forks,
            "unknowns": unknowns,
            "sections": sections,
            "next_question": next_question or (key_forks[0] if key_forks else "哪个变量最先改变后续判断"),
            "routing_recommendation": "可以继续需求重构；若要形成可交付文件，再整理成设计任务书草稿。",
            "brief_handoff_slots": merged_slots,
        }

    @staticmethod
    def _section(title: str, body: str, items: List[str], emphasis: str) -> Dict[str, Any]:
        return {
            "title": title,
            "body": body,
            "items": items,
            "emphasis": emphasis,
        }

    @staticmethod
    def _subject_phrase(context: Dict[str, Any]) -> str:
        text = str(context.get("source_message") or "")
        config = _subject_phrase_mapping_config()
        for rule in (config.get("text_rules") or []):
            if not isinstance(rule, dict):
                continue
            all_terms = [str(term) for term in (rule.get("all_terms") or []) if str(term)]
            any_terms = [str(term) for term in (rule.get("any_terms") or []) if str(term)]
            label = str(rule.get("label") or "")
            if all(term in text for term in all_terms) and (not any_terms or any(term in text for term in any_terms)):
                if label:
                    return label
        axes = context.get("semantic_axes") or {}
        subjects = set(str(item) for item in (axes.get("subject_profiles") or []) if str(item))
        for rule in (config.get("axis_rules") or []):
            if not isinstance(rule, dict):
                continue
            subject_ids = {str(item) for item in (rule.get("subject_profiles") or []) if str(item)}
            label = str(rule.get("label") or "")
            if label and subjects & subject_ids:
                return label
        return str(config.get("default") or "使用者")

    @staticmethod
    def _axis_labels(context: Dict[str, Any]) -> List[str]:
        labels: List[str] = []
        for values in (context.get("semantic_axes") or {}).values():
            for axis_id in values or []:
                label = axis_label(axis_id)
                if label and label not in labels:
                    labels.append(label)
        return labels
