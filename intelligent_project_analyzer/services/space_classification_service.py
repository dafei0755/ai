from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from intelligent_project_analyzer.models.space_classification import (
    AmbiguityInfo,
    RoutingInfo,
    SecondaryCandidate,
    SpaceClassificationResult,
)
from intelligent_project_analyzer.services.project_type_detector import (
    PARENT_TYPE_MAP,
    ProjectTypeDetector,
    get_type_label,
)

logger = logging.getLogger(__name__)

_QUESTIONNAIRE_PROFILE_MAP: Dict[str, str] = {
    "commercial_hospitality": "hospitality_v1",
    "personal_residential": "residential_v1",
    "residential_renovation": "renovation_v1",
    "commercial_office": "office_v1",
    "commercial_retail": "retail_v1",
    "brand_experience": "brand_experience_v1",
    "healthcare_wellness": "healthcare_v1",
    "rural_construction": "rural_v1",
    "popup_temporary": "popup_v1",
    "public_cultural": "cultural_v1",
    "community_public": "community_v1",
    "education_childcare": "education_v1",
    "leisure_entertainment": "leisure_v1",
    "sports_fitness": "sports_v1",
    "restaurant_cafe": "restaurant_v1",
    "urban_renewal": "urban_renewal_v1",
    "industrial_loft": "industrial_v1",
    "landscape_outdoor": "landscape_v1",
}

_ONTOLOGY_KEY_MAP: Dict[str, str] = {
    "residential": "residential",
    "hospitality": "commercial_hospitality",
    "office": "commercial_office",
    "retail": "commercial_retail",
    "leisure": "leisure_entertainment",
    "education": "education",
    "healthcare": "healthcare",
    "public": "public_space",
    "urban_renewal": "urban_renewal",
    "industrial": "industrial",
    "outdoor": "landscape",
    "special": "other",
}


class SpaceClassificationService:
    """
    旁路分类服务：包装 ProjectTypeDetector 输出 SpaceClassificationResult。
    不修改主链 project_type，仅追加 space_classification 字段。
    """

    _instance: Optional["SpaceClassificationService"] = None

    def __init__(self) -> None:
        self._detector = ProjectTypeDetector()
        self._boundary_rules: List[Dict[str, Any]] = []
        self._load_boundary_rules()

    @classmethod
    def get_instance(cls) -> "SpaceClassificationService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_boundary_rules(self) -> None:
        rules_path = (
            Path(__file__).parent.parent
            / "config"
            / "space_classification"
            / "boundary_cases.yaml"
        )
        try:
            data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
            self._boundary_rules = data.get("boundary_cases", [])
            logger.debug(
                f"[SpaceClassificationService] 加载 {len(self._boundary_rules)} 条边界规则"
            )
        except Exception as exc:
            logger.warning(
                f"[SpaceClassificationService] boundary_cases.yaml 加载失败: {exc}"
            )

    def classify(
        self,
        user_input: str,
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
        spatial_zone_refs: Optional[List[str]] = None,
    ) -> SpaceClassificationResult:
        raw = self._detector.detect_with_details(user_input, confirmed_tasks)
        result = self._build_result(raw, spatial_zone_refs or [])
        result = self._apply_boundary_rules(result, user_input)

        _metrics = {
            "event": "space_classification",
            "project_type": result.project_type,
            "confidence": round(result.confidence, 3),
            "confidence_level": result.confidence_level,
            "primary_bucket": result.primary_bucket,
            "boundary_risk": result.ambiguity.boundary_risk,
            "needs_clarification": result.ambiguity.needs_clarification,
            "ambiguity_level": result.ambiguity.level,
            "specialty_tags_count": len(result.specialty_tags),
            "secondary_candidates_count": len(result.secondary_candidates),
        }
        logger.info(f"[space_classification_metrics] {_metrics}")
        return result

    def _build_result(
        self, raw: Dict[str, Any], spatial_zone_refs: List[str]
    ) -> SpaceClassificationResult:
        project_type = raw.get("project_type") or "other"
        confidence = float(raw.get("confidence", 0.0))
        parent_type = raw.get("parent_type")
        specialty_tag = raw.get("specialty_tag")
        secondary_type = raw.get("secondary_type")
        is_ambiguous = bool(raw.get("is_ambiguous", False))
        reason = raw.get("reason", "")

        confidence_level = (
            "high" if confidence >= 0.75
            else "medium" if confidence >= 0.5
            else "low"
        )

        secondary_candidates: List[SecondaryCandidate] = []
        if secondary_type:
            secondary_candidates.append(
                SecondaryCandidate(
                    project_type=secondary_type,
                    confidence=max(0.0, confidence - 0.2),
                    role="competing_primary" if is_ambiguous else "supporting_function",
                )
            )

        ambiguity = AmbiguityInfo(
            level="high" if is_ambiguous else ("medium" if confidence < 0.6 else "low"),
            competing_types=[secondary_type] if secondary_type else [],
        )

        bucket = parent_type or PARENT_TYPE_MAP.get(project_type)
        ontology_key = _ONTOLOGY_KEY_MAP.get(bucket or "", "other")
        questionnaire_profile = _QUESTIONNAIRE_PROFILE_MAP.get(
            project_type, "general_v1"
        )

        routing = RoutingInfo(
            questionnaire_profile=questionnaire_profile,
            ontology_key=ontology_key,
            deliverable_label=get_type_label(project_type),
        )

        evidence = [reason] if reason else []

        return SpaceClassificationResult(
            primary_bucket=bucket,
            project_type=project_type,
            project_type_name=raw.get("project_type_name"),
            confidence=confidence,
            confidence_level=confidence_level,
            specialty_tags=[specialty_tag] if specialty_tag else [],
            secondary_candidates=secondary_candidates,
            ambiguity=ambiguity,
            routing=routing,
            evidence=evidence,
            spatial_zone_refs=spatial_zone_refs,
        )

    def _apply_boundary_rules(
        self, result: SpaceClassificationResult, user_input: str
    ) -> SpaceClassificationResult:
        lower_input = user_input.lower()

        for rule in self._boundary_rules:
            if result.project_type not in rule.get("types", []):
                continue
            triggers = rule.get("trigger_keywords", [])
            if not any(kw in lower_input for kw in triggers):
                continue

            result.ambiguity.boundary_risk = True
            result.ambiguity.needs_clarification = True
            if rule.get("clarification"):
                result.ambiguity.clarification_questions.append(rule["clarification"])

            competing = [
                t for t in rule.get("types", []) if t != result.project_type
            ]
            for ct in competing:
                if ct not in result.ambiguity.competing_types:
                    result.ambiguity.competing_types.append(ct)

            risk_level = rule.get("risk_level", "low")
            if risk_level == "high":
                result.ambiguity.level = "high"
            elif risk_level == "medium" and result.ambiguity.level == "low":
                result.ambiguity.level = "medium"

            logger.info(
                f"[SpaceClassificationService] 边界规则命中: {rule['id']} "
                f"({result.project_type}, risk={risk_level})"
            )

        return result

    def classify_with_llm_fallback(
        self,
        user_input: str,
        confirmed_tasks=None,
        spatial_zone_refs=None,
    ) -> SpaceClassificationResult:
        result = self.classify(user_input, confirmed_tasks, spatial_zone_refs)

        if result.ambiguity.level != "high":
            return result

        try:
            return self._llm_boundary_resolve(user_input, result)
        except Exception as exc:
            logger.warning(
                f"[SpaceClassificationService] LLM 兜底失败，降级为追问: {exc}"
            )
            result.ambiguity.needs_clarification = True
            return result

    def _llm_boundary_resolve(
        self, user_input: str, initial_result: SpaceClassificationResult
    ) -> SpaceClassificationResult:
        from intelligent_project_analyzer.services.llm_factory import LLMFactory
        from intelligent_project_analyzer.models.space_classification import (
            SpaceClassificationResult as SCR,
        )

        candidates = [initial_result.project_type] + [
            c.project_type for c in initial_result.secondary_candidates
        ]
        candidates_str = "、".join(candidates)

        prompt = (
            f"用户描述：{user_input}\n\n"
            f"初步检测类型：{initial_result.project_type}"
            f"（置信度 {initial_result.confidence:.0%}）\n"
            f"竞争候选类型：{candidates_str}\n\n"
            f"请根据用户描述，从候选类型中选择最合适的项目类型，"
            f"并说明判断依据。只能选择候选类型中的一个，不能创造新类型。"
        )

        structured_llm = LLMFactory.create_structured_llm(schema=SCR)
        llm_result: SCR = structured_llm.invoke(prompt)

        from intelligent_project_analyzer.services.project_type_detector import (
            PROJECT_TYPE_REGISTRY,
        )

        valid_ids = set(PROJECT_TYPE_REGISTRY.keys())
        valid_ids.add("other")

        if llm_result.project_type not in valid_ids:
            logger.warning(
                f"[LLM 兜底] 输出类型 {llm_result.project_type!r} 不在注册表中，"
                f"回退初始结果"
            )
            initial_result.ambiguity.needs_clarification = True
            return initial_result

        logger.info(
            f"[LLM 兜底] 裁决结果: {llm_result.project_type} "
            f"(初始: {initial_result.project_type})"
        )
        return llm_result
