"""Context intelligence packet for Scheme Advisor entry flow.

The entry UI should not hard-code a vertical. This adapter turns the existing
space classification, ontology activation, and knowledge registry outputs into
a compact packet that the product entry flow can render.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List, Optional

import yaml
from loguru import logger

from ..utils.ontology_loader import OntologyLoader
from .capability_plan_service import CapabilityPlanService
from .knowledge_package_registry import KnowledgePackageRegistry
from .scheme_advisor_semantic_axes import (
    axis_description,
    axis_label,
    derive_semantic_axes,
    rank_main_tensions,
)
from .scheme_advisor_public_labels import public_label
from .space_classification_service import SpaceClassificationService
from .space_context_packet_service import SpaceContextPacketService


_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_ONTOLOGY_PATH = Path(__file__).resolve().parent.parent / "knowledge_base" / "ontology.yaml"
_INTELLIGENCE_CONFIG = _CONFIG_DIR / "scheme_advisor_intelligence.yaml"


class SchemeAdvisorContextIntelligence:
    """Build a backend context packet from classification / ontology / knowledge."""

    def __init__(self) -> None:
        self._classifier = SpaceClassificationService()
        self._context_packet_service = SpaceContextPacketService(
            classification_service=self._classifier
        )
        self._ontology_loader = OntologyLoader(str(_ONTOLOGY_PATH))
        self._knowledge_registry = KnowledgePackageRegistry()
        self._capability_plan_service = CapabilityPlanService()
        self._config = self._load_yaml(_INTELLIGENCE_CONFIG)

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        if not path.exists():
            logger.warning(f"[SchemeAdvisorContext] config not found: {path}")
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as exc:
            logger.warning(f"[SchemeAdvisorContext] failed to load {path}: {exc}")
            return {}

    def build(self, user_input: str) -> Dict[str, Any]:
        activation = self._classifier.classify_and_activate(user_input)
        context_packet = self._context_packet_service.build_from_activation(user_input, activation)
        classification = activation.get("space_classification") or {}
        space_axis = classification.get("space_axis") or {}
        pack = activation.get("project_definition_activation_pack") or {}
        extensions = pack.get("_v18_extensions") or {}
        packet_classification = context_packet.get("classification") or {}
        packet_ontology_binding = context_packet.get("ontology_binding") or {}
        packet_subdomain = packet_classification.get("subdomain") or {}

        ontology = self._load_context_ontology(classification, extensions)
        activation_pack = ((ontology.get("_activation_pack") or {}).get("activation_pack") or {})
        knowledge_context = self._build_knowledge_context(pack, activation_pack, classification)
        ontology_focus = self._build_ontology_focus(pack, activation_pack, extensions, ontology)
        question_plan = self._build_question_plan(
            user_input,
            classification,
            pack,
            activation_pack,
            ontology_focus,
            context_packet.get("missing_slots") or [],
        )
        score = self.score_version(user_input, classification, pack, activation_pack)
        capability_plan = self._build_capability_plan(
            classification,
            pack,
            knowledge_context,
            context_packet,
            ontology_focus,
        )

        space_label = self._space_label(classification, pack, activation_pack)
        profile_id = (
            packet_subdomain.get("primary_subdomain_id")
            or extensions.get("subdomain_id")
            or classification.get("project_type")
            or classification.get("primary_bucket")
            or "general_project"
        )
        subdomain_id = packet_subdomain.get("primary_subdomain_id") or extensions.get("subdomain_id")
        activation_pack_id = packet_ontology_binding.get("activation_pack_id") or extensions.get("activation_pack_id")

        return {
            "schema_version": "scheme_advisor_context.v1",
            "mode": "project",
            "space_label": space_label,
            "type_ontology_profile": profile_id,
            "project_type": packet_classification.get("project_type_id") or classification.get("project_type"),
            "project_type_name": classification.get("project_type_name"),
            "subdomain_id": subdomain_id,
            "activation_pack_id": activation_pack_id,
            "classification": classification,
            "space_axis": space_axis,
            "context_packet": context_packet,
            "context_vector": context_packet.get("context_vector") or {},
            "output_mode": context_packet.get("output_mode") or {},
            "discipline_switch": context_packet.get("discipline_switch") or {},
            "missing_slots": context_packet.get("missing_slots") or [],
            "activation_pack_meta": activation_pack.get("meta") or {},
            "ontology_focus": ontology_focus,
            "knowledge_context": knowledge_context,
            "capability_plan": capability_plan,
            "maturity": self._build_maturity(classification, activation_pack),
            "question_plan": question_plan,
            "version_score": score,
            "intelligence_trace": {
                "classification_source": (classification.get("evidence") or {}).get("source"),
                "confidence": classification.get("confidence"),
                "confidence_level": classification.get("confidence_level"),
                "coverage_gap": classification.get("coverage_gap"),
                "ontology_unmatched": classification.get("ontology_unmatched") or [],
                "subdomain_id": subdomain_id,
                "activation_pack_id": activation_pack_id,
                "space_axis_id": space_axis.get("primary_axis_id"),
                "knowledge_packages": knowledge_context.get("knowledge_packages") or [],
                "resolved_packages": [
                    item.get("package_id") for item in knowledge_context.get("resolved_packages") or []
                ],
                "context_packet_schema_version": context_packet.get("schema_version"),
                "context_packet_project_type_id": packet_classification.get("project_type_id"),
                "capability_plan_schema_version": capability_plan.get("schema_version"),
                "question_plan_sources": self._question_plan_sources(question_plan),
                "missing_slot_actions": sorted({
                    str(slot.get("action"))
                    for slot in context_packet.get("missing_slots") or []
                    if slot.get("action")
                }),
                "version_score": score.get("score"),
                "version_score_reasons": score.get("reasons") or [],
            },
        }

    def score_version(
        self,
        text: str,
        classification: Dict[str, Any],
        pack: Dict[str, Any],
        activation_pack: Dict[str, Any],
    ) -> Dict[str, Any]:
        scoring = self._config.get("version_scoring") or {}
        weights = scoring.get("weights") or {}
        score = 0
        reasons: List[str] = []

        def add(reason: str, key: str) -> None:
            nonlocal score
            value = int(weights.get(key) or 0)
            if value:
                score += value
                reasons.append(reason)

        if (classification.get("confidence") or 0) < 0.55:
            add("分类置信度较低", "low_confidence")
        if classification.get("coverage_gap"):
            add("存在语境或知识覆盖缺口", "coverage_gap")
        if classification.get("knowledge_gap_ticket"):
            add("需要知识缺口复核", "knowledge_gap")
        if (pack.get("_v18_extensions") or {}).get("subdomain_id"):
            add("已识别细分业态", "active_subdomain")
        if activation_pack:
            add("已激活细分业态本体包", "active_activation_pack")

        text = text or ""
        term_groups = [
            ("high_risk_terms", "存在高风险或高不确定性", "high_risk_terms"),
            ("investment_terms", "涉及投资、租金、回本或成本压力", "investment_terms"),
            ("collaboration_terms", "涉及多方协作或投资决策", "collaboration_terms"),
            ("formal_delivery_terms", "涉及正式资料或落地交付", "formal_delivery_terms"),
        ]
        for group_key, reason, weight_key in term_groups:
            terms = [str(item) for item in scoring.get(group_key) or []]
            if any(term and term in text for term in terms):
                add(reason, weight_key)

        if score <= int(scoring.get("basic_max", 2)):
            tier = "basic"
        elif score <= int(scoring.get("standard_max", 6)):
            tier = "standard"
        else:
            tier = "professional"
        return {"score": score, "recommended_version": tier, "reasons": reasons[:5]}

    def _load_context_ontology(
        self,
        classification: Dict[str, Any],
        extensions: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            return self._ontology_loader.get_layered_ontology_v18(
                project_type=classification.get("project_type"),
                subdomain_id=extensions.get("subdomain_id"),
                spatial_layer_ids=extensions.get("spatial_layer_ids") or [],
                active_ontology_dimension_ids=extensions.get("active_ontology_dimension_ids") or [],
            )
        except Exception as exc:
            logger.warning(f"[SchemeAdvisorContext] ontology loading failed: {exc}")
            return {}

    def _build_knowledge_context(
        self,
        pack: Dict[str, Any],
        activation_pack: Dict[str, Any],
        classification: Dict[str, Any],
    ) -> Dict[str, Any]:
        recall = activation_pack.get("knowledge_recall_profile") or {}
        if recall:
            binding = {
                "knowledge_packages": recall.get("package_ids") or recall.get("knowledge_packages") or [],
                "search_tags": recall.get("search_tags") or [],
            }
        else:
            binding = pack.get("knowledge_base_binding") or pack.get("knowledge_binding") or {}
        return self._knowledge_registry.build_search_context(
            binding,
            project_type=str(classification.get("project_type") or ""),
        )

    def _build_ontology_focus(
        self,
        pack: Dict[str, Any],
        activation_pack: Dict[str, Any],
        extensions: Dict[str, Any],
        ontology: Dict[str, Any],
    ) -> Dict[str, Any]:
        ontology_profile = pack.get("ontology_profile") or {}
        method_profile = (
            activation_pack.get("type_method_profile")
            or pack.get("type_method_profile")
            or pack.get("business_method_profile")
            or {}
        )
        domain_framework = activation_pack.get("domain_framework") or pack.get("domain_framework") or {}
        risk_control = activation_pack.get("risk_control") or {}
        operation_model = activation_pack.get("operation_model") or {}

        return {
            "activated_objects": self._uniq(ontology_profile.get("activated_objects") or []),
            "activated_relations": self._uniq(ontology_profile.get("activated_relations") or []),
            "activated_constraints": self._uniq(
                (ontology_profile.get("activated_constraints") or [])
                + (operation_model.get("key_conflicts") or [])
                + (risk_control.get("p0_blockers") or [])
            ),
            "key_tensions": self._uniq(ontology_profile.get("key_tensions") or []),
            "priority_sequence": self._uniq(method_profile.get("priority_sequence") or []),
            "required_dimensions": self._uniq(domain_framework.get("required_dimensions") or []),
            "recommended_dimensions": self._uniq(domain_framework.get("recommended_dimensions") or []),
            "priority_dimension_ids": extensions.get("priority_ontology_dimension_ids") or [],
            "active_dimension_ids": extensions.get("active_ontology_dimension_ids") or [],
            "activation_questions": activation_pack.get("ask_yourself") or [],
            "required_slots": (activation_pack.get("questionnaire_profile") or {}).get("required_slots") or [],
            "deliverable_hints": activation_pack.get("deliverable_hints") or {},
            "ontology_categories": [key for key in ontology.keys() if not str(key).startswith("_")][:6],
        }

    def _build_capability_plan(
        self,
        classification: Dict[str, Any],
        pack: Dict[str, Any],
        knowledge_context: Dict[str, Any],
        context_packet: Dict[str, Any] | None = None,
        ontology_focus: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        if ontology_focus is None:
            ontology_focus = {
                "key_tensions": (pack.get("ontology_profile") or {}).get("key_tensions") or [],
            }
        return self._capability_plan_service.build(
            context_packet=context_packet or {},
            knowledge_context=knowledge_context,
            ontology_focus=ontology_focus,
        )

    def _build_maturity(self, classification: Dict[str, Any], activation_pack: Dict[str, Any]) -> Dict[str, Any]:
        if classification.get("status") in {"draft", "ambiguous"}:
            level = "L2"
        elif classification.get("status") == "needs_clarification":
            level = "L1"
        else:
            level = "L0"
        return {
            "level": level,
            "known": ["用户初始项目输入", "空间分类候选"],
            "inferred": [
                classification.get("project_type_name") or "空间类型",
                (activation_pack.get("meta") or {}).get("display_name") or "本体语境",
            ],
            "pending": ["CAD/平面图", "现场照片", "品牌资料", "设备清单", "预算边界"],
        }

    def _build_question_plan(
        self,
        user_input: str,
        classification: Dict[str, Any],
        pack: Dict[str, Any],
        activation_pack: Dict[str, Any],
        ontology_focus: Dict[str, Any],
        missing_slots: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        semantic_plan = self._semantic_question_plan(user_input, classification)
        if semantic_plan:
            return semantic_plan

        space_label = self._space_label(classification, pack, activation_pack)
        templates = self._config.get("question_templates") or {}
        round_1 = self._render_round(templates.get("round_1") or {}, space_label, ontology_focus, "round_1")
        missing_slot_pages = self._missing_slot_pages(missing_slots)
        if missing_slot_pages:
            round_1["pages"] = missing_slot_pages + (round_1.get("pages") or [])
            round_1["source"] = "context_packet.missing_slots+context_intelligence_packet"
        round_2 = self._render_round(templates.get("round_2") or {}, space_label, ontology_focus, "round_2")
        return {
            "schema_version": "scheme_advisor_question_plan.v1",
            "source": "context_packet+context_intelligence_packet",
            "round_1_card": round_1,
            "round_2_card": round_2,
        }

    def _semantic_question_plan(
        self,
        user_input: str,
        classification: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        axes = derive_semantic_axes(user_input)
        main_tensions = rank_main_tensions(user_input)
        space_axis = (classification or {}).get("space_axis") or {}
        fallback_focus = self._space_axis_focus_prompts(space_axis)
        main_tension_ids = [str(item.get("id")) for item in main_tensions if item.get("id")]
        round_1_header = self._semantic_round_one_header(
            user_input,
            axes=axes,
            main_tensions=main_tensions,
        )
        space_domain_options = (
            axes.get("space_domains") or []
            if len(axes.get("space_domains") or []) > 1
            else []
        )
        main_option_tension_ids = self._drop_supporting_domain_tensions(main_tension_ids)
        main_options = self._semantic_options(
            main_option_tension_ids
            + (axes.get("founding_drivers") or [])
            + (axes.get("spatial_design_drivers") or [])
            + space_domain_options,
            fallback=[
                ("project_goal", "项目真正要解决的问题", "先确认这个项目为什么成立，而不是先套风格。"),
                ("space_experience", "空间体验主轴", "先判断使用者应该获得什么感受和行为变化。"),
                ("implementation_boundary", "落地边界", "先确认哪些条件会影响方案深度和可执行性。"),
            ],
        )
        user_options = self._semantic_options(
            (axes.get("subject_profiles") or []) + (axes.get("site_resources") or []),
            fallback=[
                ("core_user", "核心使用者", "先确认谁是这个空间真正要服务的人。"),
                ("public_private_relation", "公共与私密关系", "先确认对外展示和内部使用如何分层。"),
                ("memory_anchor", "记忆与场所锚点", "先确认哪些资源应该成为空间记忆点。"),
            ],
        )
        boundary_options = self._semantic_options(
            (axes.get("critical_constraints") or []) + (axes.get("lifecycle") or []),
            fallback=[
                ("cost_boundary", "投入与成本边界", "先确认预算、工期或维护是否会改变方案方向。"),
                ("safety_boundary", "安全与规范边界", "先确认结构、消防、卫生或使用安全的底线。"),
                ("operation_boundary", "长期运营边界", "先确认空间后续如何维护、运营和迭代。"),
            ],
        )
        round_1_pages = self._semantic_tension_pages(
            main_tensions,
            main_options=main_options,
            user_options=user_options,
            boundary_options=boundary_options,
            fallback_focus=fallback_focus,
        )
        round_2_card = self._semantic_round_two_card(
            user_input,
            axes=axes,
            main_tensions=main_tensions,
            main_options=main_options,
            user_options=user_options,
            boundary_options=boundary_options,
        )
        return {
            "schema_version": "scheme_advisor_question_plan.v1",
            "source": "semantic_axes_entry",
            "round_1_card": {
                "title": round_1_header["title"],
                "prompt_text": round_1_header["prompt_text"],
                "source": "semantic_axes_entry",
                "round": "round_1",
                "pages": round_1_pages,
            },
            "round_2_card": round_2_card,
        }

    @staticmethod
    def _round_two_focus_label(main_tensions: List[Dict[str, Any]]) -> str:
        for tension in main_tensions:
            tension_id = str(tension.get("id") or "").strip()
            if not tension_id:
                continue
            label = axis_label(tension_id)
            if label and label != "待确认项":
                return label
            title = SchemeAdvisorContextIntelligence._user_visible_title(
                str(tension.get("title") or ""),
                fallback_key=tension_id,
            )
            if title and title != "待确认项":
                return title
        return "当前项目主轴"

    @staticmethod
    def prompt_anchors(user_input: str) -> Dict[str, str]:
        """Extract explicit user-stated anchors without making a case template."""
        text = str(user_input or "")

        def _first(patterns: Iterable[str]) -> str:
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    value = str(match.group(1) or "").strip(" ：:，,。；;、")
                    if value:
                        return value
            return ""

        return {
            "benchmark": _first([
                r"(?:对标|参照|借鉴)([^，,。；;\n]{2,40})",
            ]),
            "culture": _first([
                r"(?:融入|结合|转译|表达|保留)([^，,。；;\n]{2,40}?(?:传统文化|文化|文脉|记忆|传统))",
                r"([^，,。；;\n]{2,40}?(?:传统文化|文化|文脉|记忆|传统))",
            ]),
            "stakeholders": _first([
                r"(?:需兼顾|兼顾|服务|面向)([^。；;\n]{2,80}?)(?:，|,|。|；|;|成为|请|$)",
            ]),
            "motive": _first([
                r"成为([^，,。；;\n]{2,40})",
                r"目标是([^，,。；;\n]{2,40})",
            ]),
        }

    @staticmethod
    def explicit_prompt_anchor_items(user_input: str) -> List[Dict[str, str]]:
        """Return ordered, user-visible anchors stated directly in the prompt."""
        text = str(user_input or "")
        anchors = SchemeAdvisorContextIntelligence.prompt_anchors(text)
        items: List[Dict[str, str]] = []

        def _add(label: str, value: str, response: str) -> None:
            clean_value = str(value or "").strip(" ：:，,。；;、")
            if not clean_value:
                return
            if any(item["label"] == label and item["value"] == clean_value for item in items):
                return
            items.append({"label": label, "value": clean_value, "response": response})

        project_match = re.search(r"^([^，,。；;\n]{4,80}?项目)", text)
        if not project_match:
            project_match = re.search(
                r"^([^，,。；;\n]{4,60}?(?:空间|中心|店|馆|大楼|别墅|样板房|民宿|办公室|市场|街区))",
                text,
            )
        if project_match:
            project = project_match.group(1)
            _add("项目对象", project, f"{project}是本轮判断的对象，先按它的真实类型和尺度建立问题边界")

        benchmark = anchors.get("benchmark") or ""
        if benchmark:
            _add("对标对象", benchmark, f"需要先拆{benchmark}哪些原则可迁移，哪些因为城市、客群或运营条件不同不能照搬")

        culture = anchors.get("culture") or ""
        if culture:
            _add("在地文化", culture, f"{culture}要转成空间秩序、展示节奏和日常使用线索，不能停留在符号包装")

        stakeholders = anchors.get("stakeholders") or ""
        if stakeholders:
            _add("服务对象", stakeholders, f"{stakeholders}要逐一对应，先确认谁的日常使用和公共体验不能被牺牲")

        motive = anchors.get("motive") or ""
        if motive:
            _add("目标动机", motive, f"要重新梳理{motive}到底靠民生运营、公共体验、文化传播还是商业模型成立")

        scope_match = re.search(r"(?:包括|涵盖|说明)([^。；;\n]{4,120})", text)
        if scope_match:
            scope = scope_match.group(1)
            _add("任务范围", scope, f"{scope}会进入正式方案，但第一轮只确认会改变方向的判断")

        extra_match = re.search(r"(?:另需|还需|同时还需|并需)(?:统筹|考虑|处理)?([^。；;\n]{4,120})", text)
        if extra_match:
            extra = extra_match.group(1)
            _add("补充约束", extra, f"{extra}属于后续深化约束，先记录，避免入口阶段展开过细")

        return items

    @staticmethod
    def _explicit_anchor_prompt(user_input: str, *, fallback: str) -> str:
        items = SchemeAdvisorContextIntelligence.explicit_prompt_anchor_items(user_input)
        if not items:
            return fallback
        visible = items[:6]
        lines = [
            f"{idx}. {item['label']}：{item['value']}。{item['response']}。"
            for idx, item in enumerate(visible, start=1)
        ]
        overflow = items[6:]
        if overflow:
            rest = "、".join(item["value"] for item in overflow[:3])
            lines.append(f"备注：还有{rest}等未追问部分，我会在正式任务中展开，不在第一轮把问题问散。")
        return "\n".join(lines)

    @staticmethod
    def _semantic_round_one_header(
        user_input: str,
        *,
        axes: Dict[str, List[str]],
        main_tensions: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        text = str(user_input or "")
        axis_ids = {
            str(axis_id)
            for axis_name, values in (axes or {}).items()
            if axis_name != "is_complex_project"
            for axis_id in (values or [])
        }
        axis_ids.update(str(item.get("id")) for item in main_tensions if item.get("id"))
        store_terms = ["商铺", "铺位", "门店", "店铺", "档口", "奶茶", "茶饮", "咖啡店", "小店"]
        market_terms = ["菜市场", "公共市场", "农贸市场", "生鲜市场", "买菜", "摊贩", "档口", "水产", "冷链"]
        is_store_commercial = "retail_commercial" in axis_ids or "transit_node" in axis_ids or any(
            term in text for term in store_terms
        )
        is_public_market = "public_market" in axis_ids or any(term in text for term in market_terms)

        if axis_ids.intersection({"founder_owner", "identity_expression", "family_legacy"}):
            return {
                "title": "先确认这个家真正要承载什么",
                "prompt_text": (
                    "先判断主人从草根创业到事业成功之后，这个家要优先安放成就感、"
                    "家族传承，还是内心回归。"
                ),
            }
        if is_public_market:
            return {
                "title": "先确认这个市场更新最不能牺牲什么",
                "prompt_text": SchemeAdvisorContextIntelligence._explicit_anchor_prompt(
                    text,
                    fallback=(
                        "先判断老居民买菜、摊贩经营、游客停留、社区公共性、"
                        "卫生冷链和蛇口文化展示之间，哪些是底盘，哪些是增量。"
                    ),
                ),
            }
        if is_store_commercial and axis_ids.intersection(
            {"business_roi", "operational_efficiency", "retail_commercial", "transit_node"}
        ):
            payback_phrase = "半年回本" if "半年" in text and "回" in text else "回本"
            return {
                "title": f"先确认这家店能不能支撑{payback_phrase}",
                "prompt_text": (
                    "先判断这家小店的客流转化、出杯效率、投入控制和门头吸引力，"
                    f"能不能一起撑起{payback_phrase}。"
                ),
            }
        if axis_ids.intersection({"business_roi", "operational_efficiency"}):
            return {
                "title": "先确认项目如何持续成立",
                "prompt_text": "先判断运营组织、资源投入、商业回报和长期维护之间，哪一项最会改变方案方向。",
            }
        if axis_ids.intersection({"brand_differentiation", "cultural_translation", "memory_object_integration"}):
            return {
                "title": "先确认项目靠什么被记住",
                "prompt_text": "先判断品牌差异、文化转译、场地记忆和真实使用之间，哪一条最能支撑空间主轴。",
            }
        if axis_ids.intersection({"fire_structure", "mep_climate", "accessibility_safety", "security_privacy"}):
            return {
                "title": "先确认哪些条件不能含糊",
                "prompt_text": "先判断结构、消防、机电、安全或私密管理里，哪些条件会限制后续方案确定性。",
            }

        if main_tensions:
            return {
                "title": str(main_tensions[0].get("title") or "先确认第一版判断重心"),
                "prompt_text": str(
                    main_tensions[0].get("prompt")
                    or "第一轮只确认会改变方向和目录重心的判断，不问后期执行细节。"
                ),
            }
        return {
            "title": "先确认第一版判断重心",
            "prompt_text": "第一轮只确认会改变方向和目录重心的判断，不问后期执行细节。",
        }

    @staticmethod
    def _semantic_round_two_card(
        user_input: str,
        *,
        axes: Dict[str, List[str]],
        main_tensions: List[Dict[str, Any]],
        main_options: List[Dict[str, str]],
        user_options: List[Dict[str, str]],
        boundary_options: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        text = str(user_input or "")
        axis_ids = {
            str(axis_id)
            for axis_name, values in (axes or {}).items()
            if axis_name != "is_complex_project"
            for axis_id in (values or [])
        }
        axis_ids.update(str(item.get("id")) for item in main_tensions if item.get("id"))
        option_pool = main_options + user_options + boundary_options
        options_by_id = {
            str(option.get("id")): option
            for option in option_pool
            if option.get("id")
        }
        store_terms = ["商铺", "铺位", "门店", "店铺", "档口", "奶茶", "茶饮", "咖啡店", "小店"]
        market_terms = ["菜市场", "公共市场", "农贸市场", "生鲜市场", "买菜", "摊贩", "档口", "水产", "冷链"]
        is_store_commercial = "retail_commercial" in axis_ids or "transit_node" in axis_ids or any(
            term in text for term in store_terms
        )
        is_public_market = "public_market" in axis_ids or any(term in text for term in market_terms)

        if axis_ids.intersection({"founder_owner", "identity_expression", "family_legacy"}):
            profile = {
                "title": "再确认这个家最该表达什么",
                "prompt_text": (
                    "这个家更应该先回应创业后的成就感、家族传承，"
                    "还是从草根一路走来的内心安定？"
                ),
                "page_title": "这个家先讲清楚哪件事",
                "page_prompt": "第一版方案里，主人最不希望被误读的是哪一层表达？",
                "helper_text": "这里只确认会改变空间气质和分区逻辑的一件事，其他细节后续再补。",
                "preferred_ids": [
                    "identity_expression",
                    "family_legacy",
                    "founder_owner",
                    "waterfront_view",
                    "security_privacy",
                ],
            }
        elif is_public_market:
            profile = {
                "title": "再确认背后的真实取舍",
                "prompt_text": (
                    "第二轮不重复原题里的对标、文化和功能模块，而是确认背后没有明说、"
                    "但会决定方案成败的隐含冲突。"
                ),
                "page_title": "哪组隐含冲突最容易撕裂项目",
                "page_prompt": "真正要先面对的是价格感、摊贩生计、访客体验、后勤成本和公共形象之间谁让位给谁。",
                "helper_text": "这里确认潜在取舍，不把用户已经说出的任务清单再问一遍。",
                "preferred_ids": [
                    "livelihood_practicality",
                    "vendors",
                    "daily_residents",
                    "visitors_tourists",
                    "public_market_sanitation_logistics",
                    "place_branding",
                ],
                "response_mode": "priority_pick",
                "max_select": 2,
            }
        elif is_store_commercial and axis_ids.intersection({"business_roi", "operational_efficiency", "retail_commercial", "transit_node"}):
            payback_phrase = "半年回本" if "半年" in text and "回" in text else "回本"
            profile = {
                "title": "再确认这家店靠什么成立",
                "prompt_text": (
                    f"这家店第一版要先判断什么最能让{payback_phrase}成立："
                    "客流转化、出杯效率、投入控制，还是门头吸引力？"
                ),
                "page_title": "这家店先解决哪件事",
                "page_prompt": "如果只能先讲透一个判断，哪个最会影响后续方案方向？",
                "helper_text": "这里只选最会改变方案判断的一件事，避免一开始就进入施工清单。",
                "preferred_ids": [
                    "business_roi",
                    "operational_efficiency",
                    "transit_node",
                    "brand_differentiation",
                    "budget",
                ],
            }
        elif axis_ids.intersection({"business_roi", "operational_efficiency"}):
            profile = {
                "title": "再确认项目靠什么持续成立",
                "prompt_text": "第一版更应该先讲清楚运营组织、资源投入、商业回报，还是长期维护？",
                "page_title": "项目先讲清楚哪件事",
                "page_prompt": "哪个判断一旦说错，后续空间策略和投入安排都会跑偏？",
                "helper_text": "这里只确认最会改变项目判断的一件事，不套用门店或餐饮话术。",
                "preferred_ids": [
                    "operational_efficiency",
                    "business_roi",
                    "brand_differentiation",
                    "budget",
                    "technical_solution",
                ],
            }
        elif axis_ids.intersection({"brand_differentiation", "cultural_translation", "memory_object_integration"}):
            profile = {
                "title": "再确认项目靠什么被记住",
                "prompt_text": "第一版更应该先讲清楚品牌差异、文化转译，还是场地记忆？",
                "page_title": "先让哪条表达成立",
                "page_prompt": "哪个表达一旦说错，后面的材料、动线和画面都会跑偏？",
                "helper_text": "这里只确认最会牵动空间语言的判断，不展开完整视觉清单。",
                "preferred_ids": [
                    "brand_differentiation",
                    "cultural_translation",
                    "memory_object_integration",
                    "heritage_context",
                    "waterfront_view",
                ],
            }
        elif axis_ids.intersection({"fire_structure", "mep_climate", "accessibility_safety", "security_privacy"}):
            profile = {
                "title": "再确认哪些条件会限制判断",
                "prompt_text": "第一版方案最需要先确认结构、消防、机电、安全，还是私密管理？",
                "page_title": "哪类条件最可能卡住方案",
                "page_prompt": "哪件事如果不清楚，我不能把后续方案说成确定结论？",
                "helper_text": "这里只确认会压低判断确定性的条件，不把未知信息包装成结论。",
                "preferred_ids": [
                    "fire_structure",
                    "mep_climate",
                    "accessibility_safety",
                    "security_privacy",
                    "budget",
                ],
            }
        else:
            focus = SchemeAdvisorContextIntelligence._round_two_focus_label(main_tensions)
            profile = {
                "title": "再确认第一版先讲透什么",
                "prompt_text": f"第一版更应该先讲清楚{focus}、使用者关系，还是现实条件？",
                "page_title": "第一版先回答哪件事",
                "page_prompt": "哪个判断最会改变后续目录、深度和表达方式？",
                "helper_text": "这里只选最会改变判断方向的一件事，后续可以继续补充。",
                "preferred_ids": [str(item.get("id")) for item in main_tensions if item.get("id")],
            }

        options = SchemeAdvisorContextIntelligence._option_subset(
            profile["preferred_ids"],
            option_pool,
            options_by_id,
            limit=5,
        )
        if not options:
            options = (main_options or boundary_options or user_options)[:3]

        return {
            "title": profile["title"],
            "prompt_text": profile["prompt_text"],
            "source": "semantic_axes_entry",
            "round": "round_2",
            "pages": [
                {
                    "page_title": profile["page_title"],
                    "prompt_text": profile["page_prompt"],
                    "response_mode": profile.get("response_mode", "single_select"),
                    "max_select": profile.get("max_select", 1),
                    "helper_text": profile["helper_text"],
                    "allow_freetext": True,
                    "options": options[:5],
                }
            ],
        }

    @staticmethod
    def _drop_supporting_domain_tensions(tension_ids: Iterable[str]) -> List[str]:
        ids = [str(item) for item in tension_ids if str(item or "")]
        supporting_domains = {
            "residential",
            "hospitality",
            "workplace",
            "cultural_exhibition",
            "technical_special",
        }
        concrete = [item for item in ids if item not in supporting_domains]
        return concrete or ids

    @staticmethod
    def _space_axis_focus_prompts(space_axis: Dict[str, Any]) -> List[str]:
        focus_items = space_axis.get("decision_focus") or []
        return [
            str(item).strip()
            for item in focus_items
            if str(item or "").strip()
        ]

    @staticmethod
    def _focus_title(focus: str) -> str:
        title = str(focus or "").strip().strip("。；;?？")
        for prefix in ("先", "再", "最后", "然后"):
            if title.startswith(prefix):
                title = title[len(prefix):].strip()
                break
        for verb in ("确认", "判断", "校准", "识别", "组织", "明确"):
            if title.startswith(verb):
                title = title[len(verb):].strip()
                break
        title = title.replace("如何", "").replace("是否", "").strip()
        if not title:
            return "先确认关键判断"
        return title if len(title) <= 18 else f"{title[:18]}…"

    @staticmethod
    def _space_axis_focus_page(
        focus: str,
        *,
        option_pool: List[Dict[str, str]],
        fallback_options: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        prompt = str(focus or "").strip()
        if prompt and prompt[-1] not in "。；;?？":
            prompt = f"{prompt}？"
        options: List[Dict[str, str]] = []
        seen: set[str] = set()
        for option in (fallback_options or []) + option_pool:
            option_id = str(option.get("id") or "")
            if not option_id or option_id in seen:
                continue
            options.append(option)
            seen.add(option_id)
            if len(options) >= 5:
                break
        return {
            "page_title": SchemeAdvisorContextIntelligence._focus_title(prompt),
            "prompt_text": prompt or "先确认会影响判断方向的关键条件。",
            "response_mode": "multi_select",
            "max_select": 2,
            "helper_text": "这里根据当前空间主轴补齐关键判断，不进入施工细节。",
            "allow_freetext": True,
            "options": options,
        }

    @staticmethod
    def _semantic_tension_pages(
        main_tensions: List[Dict[str, Any]],
        *,
        main_options: List[Dict[str, str]],
        user_options: List[Dict[str, str]],
        boundary_options: List[Dict[str, str]],
        fallback_focus: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        option_pool = main_options + user_options + boundary_options
        options_by_id = {
            str(option.get("id")): option
            for option in option_pool
            if option.get("id")
        }

        pages: List[Dict[str, Any]] = []
        for tension in main_tensions[:3]:
            tension_id = str(tension.get("id") or "")
            title = SchemeAdvisorContextIntelligence._user_visible_title(
                str(tension.get("title") or ""),
                fallback_key=tension_id,
            )
            prompt = SchemeAdvisorContextIntelligence._user_visible_prompt(
                str(tension.get("prompt") or ""),
                fallback_key=tension_id,
            )
            source_axes = [str(axis) for axis in tension.get("source_axes") or [] if axis]
            related_options = [str(axis) for axis in tension.get("related_options") or [] if axis]
            option_ids = related_options + [tension_id] + source_axes if related_options else [tension_id] + source_axes
            options = SchemeAdvisorContextIntelligence._option_subset(
                option_ids,
                option_pool,
                options_by_id,
                limit=5,
            )
            pages.append({
                "page_title": title,
                "prompt_text": prompt,
                "response_mode": "multi_select",
                "max_select": 2,
                "helper_text": "可以多选。这里先确认会改变判断方向的关键选择，不进入施工细节。",
                "allow_freetext": True,
                "options": options,
            })

        for index, focus in enumerate(fallback_focus or []):
            if len(pages) >= 3:
                break
            fallback_options = (
                user_options
                if index == 0
                else boundary_options if index == 1 else main_options
            )
            pages.append(
                SchemeAdvisorContextIntelligence._space_axis_focus_page(
                    focus,
                    option_pool=option_pool,
                    fallback_options=fallback_options,
                )
            )

        if len(pages) < 2:
            pages.append(
                SchemeAdvisorContextIntelligence._space_axis_focus_page(
                    "这个空间主要服务谁，以及公共、私密、服务和停留关系如何分层？",
                    option_pool=option_pool,
                    fallback_options=user_options or main_options,
                )
            )

        if len(pages) < 3:
            pages.append(
                SchemeAdvisorContextIntelligence._space_axis_focus_page(
                    "哪些安全、合规、成本或长期维护条件不清楚，后续判断最容易跑偏？",
                    option_pool=option_pool,
                    fallback_options=boundary_options or main_options,
                )
            )

        return pages[:3]

    @staticmethod
    def _has_chinese(text: str) -> bool:
        return any("\u4e00" <= ch <= "\u9fff" for ch in str(text or ""))

    @staticmethod
    def _user_visible_title(text: str, *, fallback_key: str) -> str:
        raw = str(text or "").strip()
        if raw and SchemeAdvisorContextIntelligence._has_chinese(raw):
            return raw
        translated = public_label(raw or fallback_key)
        if translated != "待确认项":
            return translated
        return axis_label(fallback_key)

    @staticmethod
    def _user_visible_prompt(text: str, *, fallback_key: str) -> str:
        raw = str(text or "").strip()
        if raw and SchemeAdvisorContextIntelligence._has_chinese(raw):
            return raw
        translated = public_label(raw or fallback_key)
        if translated != "待确认项":
            return translated
        return axis_description(fallback_key)

    @staticmethod
    def _option_subset(
        preferred_ids: Iterable[str],
        option_pool: List[Dict[str, str]],
        options_by_id: Dict[str, Dict[str, str]],
        *,
        limit: int,
    ) -> List[Dict[str, str]]:
        selected: List[Dict[str, str]] = []
        seen: set[str] = set()
        for option_id in preferred_ids:
            option = options_by_id.get(str(option_id))
            if not option or option_id in seen:
                continue
            selected.append(option)
            seen.add(str(option_id))
            if len(selected) >= limit:
                return selected
        for option in option_pool:
            option_id = str(option.get("id") or "")
            if not option_id or option_id in seen:
                continue
            selected.append(option)
            seen.add(option_id)
            if len(selected) >= limit:
                break
        return selected

    @staticmethod
    def _semantic_options(
        axis_ids: Iterable[str],
        *,
        fallback: List[tuple[str, str, str]],
    ) -> List[Dict[str, str]]:
        seen: set[str] = set()
        options: List[Dict[str, str]] = []
        for axis_id in axis_ids:
            if not axis_id or axis_id in seen:
                continue
            seen.add(axis_id)
            options.append({
                "id": str(axis_id),
                "label": axis_label(str(axis_id)),
                "description": axis_description(str(axis_id)),
            })
        if options:
            return options
        return [
            {"id": option_id, "label": label, "description": description}
            for option_id, label, description in fallback
        ]

    @staticmethod
    def _question_plan_sources(question_plan: Dict[str, Any]) -> List[str]:
        sources: List[str] = []
        if question_plan.get("source"):
            sources.append(str(question_plan["source"]))
        for key in ("round_1_card", "round_2_card"):
            card = question_plan.get(key) or {}
            if card.get("source"):
                sources.append(str(card["source"]))
            for page in card.get("pages") or []:
                if page.get("source"):
                    sources.append(str(page["source"]))
        return sorted(set(sources))

    def _missing_slot_pages(self, missing_slots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        routable_slots = [
            slot
            for slot in (missing_slots or [])
            if slot.get("active_for_current_round") is not False
        ]
        if not routable_slots:
            routable_slots = missing_slots or []

        for slot in routable_slots:
            action = str(slot.get("action") or "").strip()
            if action:
                grouped.setdefault(action, []).append(slot)

        pages: List[Dict[str, Any]] = []
        action_specs = [
            (
                "certainty_ceiling",
                "确认会卡住方案的条件",
                "这些条件不清楚时，我只能给条件级判断，不能把平面、设备和落地结论说死。",
                "confirmation_status",
                3,
            ),
            (
                "branch_answer_plus_followup",
                "补齐会改变判断的信息",
                "这些信息会改变判断分支。我可以先给方向判断，但需要你确认事实边界。",
                "fact_status",
                3,
            ),
            (
                "option_menu",
                "先选一个判断方向",
                "这些条件适合先定一个大方向，再进入下一步判断。",
                "single_select",
                1,
            ),
        ]
        for action, title, prompt, response_mode, max_select in action_specs:
            slots = grouped.get(action) or []
            if not slots:
                continue
            pages.append({
                "page_title": title,
                "prompt_text": prompt,
                "response_mode": response_mode,
                "max_select": min(max_select, max(1, len(slots))),
                "helper_text": "按当前掌握程度选择，可在补充栏写具体数值或边界。",
                "allow_freetext": True,
                "source": "context_packet.missing_slots",
                "missing_slot_action": action,
                "missing_slot_names": [str(slot.get("name")) for slot in slots if slot.get("name")],
                "options": self._missing_slot_options(slots, action),
            })
        return pages

    def _missing_slot_options(self, slots: List[Dict[str, Any]], action: str) -> List[Dict[str, Any]]:
        options: List[Dict[str, Any]] = []
        for slot in slots[:5]:
            name = str(slot.get("name") or "missing_slot")
            note = str(slot.get("user_visible_note") or "")
            label = self._label(name)
            if action == "certainty_ceiling":
                options.extend([
                    {
                        "id": f"{name}_known",
                        "label": f"{label}已明确",
                        "description": note or "可以补充明确条件，系统可提高判断确定性。",
                    },
                    {
                        "id": f"{name}_unknown",
                        "label": f"{label}待确认",
                        "description": "先按条件级判断推进，不把正式结论说死。",
                    },
                ])
            elif action == "option_menu":
                options.extend(self._subjective_preference_options(name, note))
            else:
                options.append({
                    "id": f"{name}_known",
                    "label": label,
                    "description": note or "该事实会改变后续判断分支。",
                })
        return options[:6]

    @staticmethod
    def _subjective_preference_options(name: str, note: str) -> List[Dict[str, Any]]:
        if name == "style_preference":
            return [
                {
                    "id": "style_preference_restrained_minimal",
                    "label": "克制极简",
                    "description": "收敛材料、线条和灯光，优先做安静高级的空间秩序。",
                },
                {
                    "id": "style_preference_memory_anchor",
                    "label": "记忆锚点",
                    "description": "保留克制底色，但设置一个清晰的品牌或城市记忆点。",
                },
                {
                    "id": "style_preference_social_strong",
                    "label": "社交打卡",
                    "description": "强化可拍照、可传播和可识别的场景节点。",
                },
            ]
        if name == "tone_preference":
            return [
                {
                    "id": "tone_preference_warm_relaxed",
                    "label": "温暖松弛",
                    "description": "让停留、交流和亲近感更强，适合社交和日常消费。",
                },
                {
                    "id": "tone_preference_calm_precise",
                    "label": "冷静精确",
                    "description": "强调效率、秩序和清晰识别，适合小面积与高峰运营。",
                },
            ]
        return [
            {
                "id": f"{name}_open_choice",
                "label": SchemeAdvisorContextIntelligence._public_label(name),
                "description": note or "先选择偏好路径，再进入下一步判断。",
            }
        ]

    def _render_round(
        self,
        template: Dict[str, Any],
        space_label: str,
        ontology_focus: Dict[str, Any],
        round_id: str,
    ) -> Dict[str, Any]:
        pages = []
        for index, page in enumerate(template.get("pages") or []):
            page_id = str(page.get("id") or f"page_{index + 1}")
            source_items = self._items_for_page(page_id, ontology_focus)
            options = self._options_from_items(source_items)
            if not options:
                options = self._options_from_items(ontology_focus.get("required_dimensions") or [])
            pages.append(
                {
                    "page_title": page.get("page_title") or self._label(page_id),
                    "prompt_text": str(page.get("prompt_text") or "").format(space_label=space_label),
                    "response_mode": page.get("response_mode") or "multi_select",
                    "max_select": page.get("max_select") or 3,
                    "helper_text": page.get("helper_text") or "",
                    "allow_freetext": True,
                    "options": options[:5],
                }
            )
        return {
            "title": template.get("title") or "入口问诊",
            "prompt_text": template.get("prompt_text") or "",
            "pages": pages,
            "source": "context_intelligence_packet",
            "round": round_id,
        }

    def _items_for_page(self, page_id: str, ontology_focus: Dict[str, Any]) -> List[Any]:
        if page_id == "establishment_path":
            return ontology_focus.get("priority_sequence") or ontology_focus.get("required_dimensions") or []
        if page_id == "hard_constraints":
            return ontology_focus.get("activated_constraints") or ontology_focus.get("required_dimensions") or []
        if page_id == "decision_tension":
            return ontology_focus.get("key_tensions") or ontology_focus.get("priority_sequence") or []
        if page_id == "risk_threshold":
            return ontology_focus.get("activated_constraints") or ontology_focus.get("activation_questions") or []
        if page_id == "resource_bet":
            hints = ontology_focus.get("deliverable_hints") or {}
            return (hints.get("must_have") or []) + (ontology_focus.get("priority_sequence") or [])
        if page_id == "formal_calibration":
            return ontology_focus.get("required_slots") or ontology_focus.get("required_dimensions") or []
        return ontology_focus.get("required_dimensions") or []

    def _options_from_items(self, items: Iterable[Any]) -> List[Dict[str, Any]]:
        options = []
        for item in items or []:
            if isinstance(item, dict):
                raw_id = str(item.get("id") or item.get("question") or item.get("name") or "")
                label = str(item.get("label") or item.get("name") or item.get("question") or raw_id)
                description = str(item.get("why") or item.get("description") or item.get("note") or "")
            else:
                raw_id = str(item)
                label = self._label(raw_id)
                description = self._description(raw_id)
            if not raw_id and not label:
                continue
            option_id = self._option_id(raw_id or label)
            options.append({"id": option_id, "label": label, "description": description})
        return options

    def _space_label(
        self,
        classification: Dict[str, Any],
        pack: Dict[str, Any],
        activation_pack: Dict[str, Any],
    ) -> str:
        activation_name = (activation_pack.get("meta") or {}).get("display_name")
        if activation_name:
            return str(activation_name).replace("激活包", "")
        display = (pack.get("routing") or {}).get("deliverable_label")
        if display:
            return str(display)
        name = classification.get("project_type_name")
        if name and name != "未识别":
            return str(name)
        return "空间项目"

    def _label(self, value: str) -> str:
        labels = self._config.get("labels") or {}
        if value in labels:
            return str(labels[value])
        return public_label(value)

    @staticmethod
    def _public_label(value: str) -> str:
        return public_label(value)

    def _description(self, value: str) -> str:
        text = str(value or "")
        if "_vs_" in text:
            left, right = text.split("_vs_", 1)
            return f"需要判断{self._label(left)}与{self._label(right)}之间如何取舍"
        return "会影响任务书目录重心、版本深度或正式阶段校准顺序"

    @staticmethod
    def _option_id(value: str) -> str:
        safe = "".join(ch if ch.isalnum() else "_" for ch in str(value).lower()).strip("_")
        return safe[:64] or "option"

    @staticmethod
    def _uniq(items: Iterable[Any]) -> List[Any]:
        result: List[Any] = []
        seen = set()
        for item in items or []:
            key = str(item)
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result
