"""Adapter that projects existing Scheme Advisor intelligence into demand_reconstruction context."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .scheme_advisor_context_intelligence import SchemeAdvisorContextIntelligence
from .scheme_advisor_semantic_axes import derive_semantic_axes, rank_main_tensions


class DemandReconstructionContextAdapter:
    """Build the demand-reconstruction-layer context without creating a second classifier."""

    def __init__(self, context_intelligence: Optional[SchemeAdvisorContextIntelligence] = None) -> None:
        self._context_intelligence = context_intelligence

    def build(self, user_message: str) -> Dict[str, Any]:
        text = str(user_message or "")
        advisor_packet = self._safe_context_packet(text)
        semantic_axes = derive_semantic_axes(text)
        main_tensions = rank_main_tensions(text)
        classification = advisor_packet.get("classification") or {}
        context_vector = advisor_packet.get("context_vector") or {}
        semantic_candidate_set = self._build_semantic_candidate_set(
            text,
            semantic_axes=semantic_axes,
            classification=classification,
            context_vector=context_vector,
        )
        archetype = self._archetype_from_candidates(semantic_candidate_set)
        return {
            "schema_version": "demand_reconstruction_context_adapter.v1",
            "source_message": text,
            "advisor_packet": advisor_packet,
            "project_type": advisor_packet.get("project_type") or classification.get("project_type"),
            "project_type_name": advisor_packet.get("project_type_name") or classification.get("project_type_name"),
            "space_label": advisor_packet.get("space_label") or "空间项目",
            "classification": classification,
            "context_vector": context_vector,
            "semantic_axes": semantic_axes,
            "main_tensions": main_tensions,
            "missing_slots": advisor_packet.get("missing_slots") or [],
            "knowledge_coverage_ceiling": self._extract_coverage_ceiling(advisor_packet),
            "semantic_candidate_set": semantic_candidate_set,
            "archetype": archetype,
            "context_source": {
                "context_intelligence": bool(advisor_packet),
                "space_classification": bool(classification),
                "semantic_axes": True,
                "ontology_focus": bool(advisor_packet.get("ontology_focus")),
                "knowledge_context": bool(advisor_packet.get("knowledge_context")),
            },
        }

    def _safe_context_packet(self, text: str) -> Dict[str, Any]:
        try:
            return self._get_context_intelligence().build(text)
        except Exception:
            return {}

    def _get_context_intelligence(self) -> SchemeAdvisorContextIntelligence:
        if self._context_intelligence is None:
            self._context_intelligence = SchemeAdvisorContextIntelligence()
        return self._context_intelligence

    @staticmethod
    def _build_semantic_candidate_set(
        text: str,
        *,
        semantic_axes: Dict[str, List[str]],
        classification: Dict[str, Any],
        context_vector: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        normalized = str(text or "")
        project_type = str(classification.get("project_type") or "")
        primary_bucket = str(classification.get("primary_bucket") or "")
        domains = set(semantic_axes.get("space_domains") or [])
        drivers = set(semantic_axes.get("founding_drivers") or [])
        subject_profiles = set(semantic_axes.get("subject_profiles") or [])
        vector_values = {str(value) for value in context_vector.values() if value}
        candidates: List[Dict[str, Any]] = []

        def add_candidate(
            candidate_id: str,
            *,
            score: int,
            evidence: List[str],
            counter_evidence: Optional[List[str]] = None,
            routing_target: str = "demand_reconstruction",
        ) -> None:
            if score <= 0:
                return
            candidates.append(
                {
                    "id": candidate_id,
                    "score": score,
                    "role": "secondary",
                    "evidence": [item for item in evidence if item],
                    "counter_evidence": [item for item in (counter_evidence or []) if item],
                    "routing_target": routing_target,
                }
            )

        if DemandReconstructionContextAdapter._has_any(
            normalized,
            ("研究", "源流", "历史", "宋代", "文人", "雅集", "文化母题", "证据", "转译", "启发"),
        ):
            is_concrete_design_project = DemandReconstructionContextAdapter._has_concrete_project_intent(
                normalized,
                project_type=project_type,
                domains=domains,
            )
            add_candidate(
                "cultural_research",
                score=45 if is_concrete_design_project else 95,
                evidence=["输入包含研究、历史、文化转译或证据线索。"],
                counter_evidence=["具体项目锚点优先，历史/转译只作为辅助研究线索。"] if is_concrete_design_project else None,
                routing_target="demand_reconstruction" if is_concrete_design_project else "deep_research",
            )

        hard_constraint_score = 0
        if DemandReconstructionContextAdapter._has_any(
            normalized,
            (
                "冷藏柜",
                "留多大",
                "尺寸",
                "设备",
                "给排水",
                "上下水",
                "多少平",
                "多大",
                "预算",
                "恒温恒湿",
                "温湿度",
                "防火",
                "安防",
                "声学",
                "隔音",
                "结构",
                "消防",
            ),
        ):
            hard_constraint_score += 80
        if DemandReconstructionContextAdapter._has_any(
            normalized,
            ("冷藏柜", "留多大", "尺寸", "多少平", "多大", "恒温恒湿", "防火分区"),
        ):
            hard_constraint_score += 20
        if semantic_axes.get("critical_constraints"):
            hard_constraint_score += 20
        add_candidate(
            "hard_constraint",
            score=hard_constraint_score,
            evidence=["输入包含尺寸、设备、预算或硬约束线索。"],
        )

        is_healthcare_care = DemandReconstructionContextAdapter._has_healthcare_care_anchor(normalized)
        if is_healthcare_care:
            add_candidate(
                "healthcare_care",
                score=92,
                evidence=["输入包含医疗、照护、康养、医护或患者行为线索。"],
            )

        is_workplace_project_type = DemandReconstructionContextAdapter._is_workplace_project_signal(
            normalized,
            project_type=project_type,
        )
        if is_workplace_project_type:
            add_candidate(
                "workplace_headquarters",
                score=90,
                evidence=["输入包含办公、团队协作、客户会谈、会议或保密工作流线索。"],
            )

        if DemandReconstructionContextAdapter._has_urban_renewal_anchor(normalized, project_type=project_type):
            add_candidate(
                "urban_renewal",
                score=125,
                evidence=["输入包含城市更新、街区更新、原住民、存量商户或分期实施线索。"],
            )

        if DemandReconstructionContextAdapter._has_collection_museum_anchor(normalized, project_type=project_type):
            add_candidate(
                "collection_museum",
                score=125,
                evidence=["输入包含收藏、博物馆、美术馆、藏品展示或专题展陈线索。"],
            )

        style_terms = ("东方感", "不老气", "风格", "侘寂", "松弛感", "安藤", "精神性", "材料气质", "氛围")
        style_matches = [term for term in style_terms if term in normalized]
        if style_matches:
            style_score = 96 if len(style_matches) >= 2 else 82
            add_candidate(
                "style_semantics",
                score=style_score,
                evidence=["输入以风格语义、材料气质或精神性表达为核心线索。"],
            )

        is_media_production = (
            project_type == "digital_media_studio"
            or "digital_media_studio" in domains
            or DemandReconstructionContextAdapter._has_any(
                normalized,
                (
                    "直播",
                    "拍摄",
                    "视频录制",
                    "录播",
                    "影棚",
                    "摄影棚",
                    "美食实验室",
                    "美食工作室",
                    "布景",
                    "灯光布置",
                    "播客",
                    "录音室",
                    "录音",
                    "导播",
                    "访谈",
                    "后期剪辑",
                    "电竞",
                    "赛事直播",
                    "选手训练",
                    "战术复盘",
                    "粉丝互动",
                ),
            )
        )
        if is_media_production:
            media_score = 88
            if DemandReconstructionContextAdapter._has_any(normalized, ("播客", "录音室", "录音", "导播", "访谈", "后期剪辑")):
                media_score = 110
            if DemandReconstructionContextAdapter._has_any(normalized, ("电竞", "赛事直播", "选手训练", "战术复盘", "粉丝互动")):
                media_score = 130
            add_candidate(
                "media_production",
                score=media_score,
                evidence=["输入包含拍摄、视频录制、影棚、布景或内容生产工作流。"],
            )

        is_commercial_project_type = DemandReconstructionContextAdapter._is_commercial_project_signal(
            normalized,
            project_type=project_type,
            domains=domains,
        )
        has_explicit_public_cultural_anchor = DemandReconstructionContextAdapter._has_public_cultural_anchor(
            normalized,
            is_commercial_project=is_commercial_project_type,
        )
        is_public_cultural_experience = (
            project_type == "public_cultural"
            or "education_public" in domains
            or "cultural_exhibition" in domains
            or has_explicit_public_cultural_anchor
        )
        if is_public_cultural_experience:
            public_cultural_score = 90
            public_counter_evidence = []
            if is_commercial_project_type and not has_explicit_public_cultural_anchor:
                public_cultural_score = 40
                public_counter_evidence.append("商业餐饮或零售项目中的文化体验更像品牌与服务线索，不应直接改判为公共文化项目。")
            add_candidate(
                "public_cultural_experience",
                score=public_cultural_score,
                evidence=["输入包含访客中心、公共体验、科普教育、亲子或展陈线索。"],
                counter_evidence=public_counter_evidence,
            )

        is_commercial = (
            "retail_commercial" in domains
            or "operational_efficiency" in drivers
            or is_commercial_project_type
            or bool({"FoodBeverage", "CommercialDining", "TakeawayPriority", "PotentialHighPeak"}.intersection(vector_values))
            or DemandReconstructionContextAdapter._has_any(normalized, ("咖啡", "茶饮", "店", "翻台", "外带", "坪效", "出杯", "客流"))
        )
        if is_commercial:
            counter_evidence = []
            commercial_score = 84
            if is_public_cultural_experience and not (is_commercial_project_type and not has_explicit_public_cultural_anchor):
                commercial_score = 35
                counter_evidence.append("咖啡区更像访客停留、等候和社交支撑功能，不应反向主导公共体验项目。")
            add_candidate(
                "commercial_operation",
                score=commercial_score,
                evidence=["输入包含商业、门店、咖啡、外带、翻台、坪效或运营效率线索。"],
                counter_evidence=counter_evidence,
            )

        is_commercial_project = is_commercial_project_type
        has_explicit_life_identity_anchor = DemandReconstructionContextAdapter._has_life_identity_anchor(
            normalized,
            is_commercial_project=is_commercial_project,
        )
        is_life_identity = (
            (project_type == "personal_residential" and not is_commercial_project)
            or (primary_bucket == "residential" and not is_commercial_project)
            or ("residential" in domains and not is_commercial_project)
            or ("professional_user" in subject_profiles and not is_commercial_project and not is_workplace_project_type)
            or has_explicit_life_identity_anchor
        )
        if is_life_identity:
            add_candidate(
                "life_identity",
                score=86,
                evidence=["输入包含居住、返乡、家族、专业使用者或身份安放线索。"],
            )

        if not candidates:
            add_candidate(
                "general_project",
                score=10,
                evidence=["尚未形成明确细分候选，先按通用空间项目处理。"],
            )

        ranked = sorted(candidates, key=lambda item: (-int(item.get("score") or 0), str(item.get("id") or "")))
        primary_id = ranked[0]["id"]
        for item in ranked:
            if item["id"] == primary_id:
                item["role"] = "primary"
            elif item["score"] < 50:
                item["role"] = "downweighted"
            else:
                item["role"] = "secondary"
        return ranked

    @staticmethod
    def _archetype_from_candidates(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not candidates:
            return {"primary": "general_project", "secondary": [], "routing_target": "demand_reconstruction"}
        primary = candidates[0]
        return {
            "primary": primary.get("id") or "general_project",
            "secondary": [item.get("id") for item in candidates[1:] if item.get("role") == "secondary"],
            "downweighted": [item.get("id") for item in candidates[1:] if item.get("role") == "downweighted"],
            "routing_target": primary.get("routing_target") or "demand_reconstruction",
            "candidate_set": candidates,
        }

    @staticmethod
    def _extract_coverage_ceiling(advisor_packet: Dict[str, Any]) -> Dict[str, Any]:
        context_packet = advisor_packet.get("context_packet") or {}
        knowledge_binding = context_packet.get("knowledge_binding") or {}
        coverage = knowledge_binding.get("coverage_ceiling") or {}
        return coverage if isinstance(coverage, dict) else {}

    @staticmethod
    def _is_commercial_project_signal(text: str, *, project_type: str, domains: set[str]) -> bool:
        commercial_project_types = {
            "commercial_dining",
            "tea_drink_store",
            "commercial_retail",
            "brand_experience",
            "popup_temporary",
            "commercial_hospitality",
        }
        return (
            project_type in commercial_project_types
            or "retail_commercial" in domains
            or DemandReconstructionContextAdapter._has_any(
                text,
                (
                    "体验店",
                    "快闪",
                    "品牌",
                    "会员",
                    "销售转化",
                    "门店",
                    "旗舰店",
                    "买手店",
                    "餐厅",
                    "咖啡店",
                    "酒店",
                    "大堂",
                    "入住接待",
                    "行李寄存",
                    "早餐外摆",
                    "商务等候",
                ),
            )
        )

    @staticmethod
    def _is_workplace_project_signal(text: str, *, project_type: str) -> bool:
        if project_type in {"commercial_office", "office_workspace", "workplace"}:
            return True
        return DemandReconstructionContextAdapter._has_any(
            text,
            (
                "办公室",
                "独立办公",
                "客户会谈",
                "合伙人会议",
                "团队协作",
                "档案保密",
                "会议室",
                "开放办公",
                "混合办公",
                "企业协作枢纽",
                "工位",
                "研发团队",
            ),
        )

    @staticmethod
    def _has_urban_renewal_anchor(text: str, *, project_type: str) -> bool:
        if project_type in {"urban_renewal", "city_renewal", "community_renewal"}:
            return True
        return DemandReconstructionContextAdapter._has_any(
            text,
            (
                "城市更新",
                "街区更新",
                "老旧街区",
                "旧城",
                "老城",
                "历史街区",
                "原住民",
                "存量商户",
                "分期实施",
                "社区商业",
                "片区焕新",
            ),
        )

    @staticmethod
    def _has_collection_museum_anchor(text: str, *, project_type: str) -> bool:
        if project_type in {"museum_exhibition", "cultural_exhibition", "gallery"}:
            return True
        return DemandReconstructionContextAdapter._has_any(
            text,
            (
                "博物馆",
                "美术馆",
                "收藏馆",
                "收藏家",
                "藏品",
                "限量藏品",
                "收藏墙",
                "藏品展示",
                "常设展",
                "专题展",
                "珍藏展厅",
                "限量鞋款",
                "品牌时间线",
            ),
        )

    @staticmethod
    def _has_public_cultural_anchor(text: str, *, is_commercial_project: bool) -> bool:
        strong_public_terms = ("访客中心", "游客中心", "市民农场", "公共体验", "公众参观", "公众开放", "展示馆", "展示中心")
        if DemandReconstructionContextAdapter._has_any(text, strong_public_terms):
            return True
        if is_commercial_project:
            return False
        if DemandReconstructionContextAdapter._has_any(text, ("科普教育", "科普", "亲子")):
            return True
        if "展陈" in text and not is_commercial_project:
            return True
        return False

    @staticmethod
    def _has_life_identity_anchor(text: str, *, is_commercial_project: bool) -> bool:
        personal_life_terms = (
            "返乡",
            "老家",
            "背井离乡",
            "自宅",
            "自住",
            "父母",
            "孩子",
            "老人",
            "长期居住",
            "养老居住",
            "后半生",
            "乡土",
        )
        if DemandReconstructionContextAdapter._has_any(text, personal_life_terms):
            return True
        if is_commercial_project:
            return False
        return DemandReconstructionContextAdapter._has_any(text, ("民居", "住宅", "家族", "退休", "家庭"))

    @staticmethod
    def _has_healthcare_care_anchor(text: str) -> bool:
        return DemandReconstructionContextAdapter._has_any(
            text,
            (
                "医院",
                "病房",
                "诊所",
                "康养",
                "疗养",
                "照护",
                "日间照料",
                "医护",
                "护理",
                "康复",
                "康复中心",
                "物理治疗",
                "器械训练",
                "评估室",
                "患者",
                "感染控制",
                "临终关怀",
                "安宁疗护",
                "社区食堂",
                "值班",
            ),
        )

    @staticmethod
    def _has_concrete_project_intent(text: str, *, project_type: str, domains: set[str]) -> bool:
        if not (project_type or domains):
            return False
        if DemandReconstructionContextAdapter._has_any(text, ("我想研究", "研究路径", "方法论", "源流", "启发")):
            concrete_project_terms = (
                "打造",
                "改造",
                "重构需求",
                "完整设计",
                "设计框架",
                "项目",
                "体验店",
                "品牌展厅",
                "访客中心",
                "酒店",
                "大堂",
                "餐厅",
                "办公室",
                "住宅",
                "民居",
            )
            if not DemandReconstructionContextAdapter._has_any(text, concrete_project_terms):
                return False
        return DemandReconstructionContextAdapter._has_any(
            text,
            (
                "请提出完整设计",
                "完整设计框架",
                "完整设计方案",
                "空间策略",
                "设计框架",
                "设计方案",
                "打造",
                "改造",
                "改造为",
                "重构需求",
                "给出建议",
                "提出建议",
            ),
        )

    @staticmethod
    def _has_any(text: str, terms: tuple[str, ...]) -> bool:
        return any(term in text for term in terms)
