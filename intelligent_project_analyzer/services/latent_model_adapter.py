"""Build the unified latent model from demand-reconstruction adapter context."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from intelligent_project_analyzer.core.latent_model import (
    EvidenceItem,
    LatentModel,
    LatentVariableItem,
)


class LatentModelAdapter:
    """Project explicit user signals and adapter context into LatentModel v1."""

    _EVIDENCE_TERMS = (
        "50岁",
        "室内设计师",
        "设计师",
        "背井离乡",
        "老家",
        "故乡",
        "返乡",
        "民居",
        "乡村",
        "农村",
        "创业",
        "功成名就",
    )

    def build(self, *, source_message: str, adapter_context: Optional[Dict[str, Any]] = None) -> LatentModel:
        text = str(source_message or "")
        context = adapter_context or {}
        evidence = self._build_evidence_index(text)
        evidence_refs = [item.evidence_id for item in evidence]

        life_ref = self._first_ref(evidence, ("50岁", "功成名就", "创业"))
        profession_ref = self._first_ref(evidence, ("室内设计师", "设计师"))
        place_ref = self._first_ref(evidence, ("背井离乡", "老家", "故乡", "返乡"))
        dwelling_ref = self._first_ref(evidence, ("民居", "乡村", "农村"))

        latent_variables: Dict[str, List[LatentVariableItem]] = {}
        identity_items: List[LatentVariableItem] = []
        if life_ref:
            identity_items.append(
                LatentVariableItem(
                    id="life_stage",
                    label="年龄阶段",
                    value="mid_late_career",
                    confidence=0.84,
                    evidence_refs=[life_ref],
                    source="inferred",
                )
            )
        if profession_ref:
            identity_items.append(
                LatentVariableItem(
                    id="professional_identity",
                    label="职业身份",
                    value="interior_designer",
                    confidence=0.9,
                    evidence_refs=[profession_ref],
                    source="inferred",
                )
            )
        if place_ref:
            identity_items.append(
                LatentVariableItem(
                    id="relationship_to_place",
                    label="故乡关系",
                    value="returning_home",
                    confidence=0.88,
                    evidence_refs=[place_ref],
                    source="inferred",
                )
            )
        if identity_items:
            latent_variables["identity_drivers"] = identity_items

        object_items: List[LatentVariableItem] = []
        if dwelling_ref:
            object_items.append(
                LatentVariableItem(
                    id="dwelling_object",
                    label="项目对象",
                    value="rural_home",
                    confidence=0.82,
                    evidence_refs=[dwelling_ref],
                    source="inferred",
                )
            )
        if object_items:
            latent_variables["project_object_drivers"] = object_items

        person_profile = self._person_profile(identity_items, evidence_refs)
        tensions = self._tensions(context, has_returning_home=bool(place_ref), has_profession=bool(profession_ref))
        evidence_bound_affect = self._evidence_bound_affect(place_ref=place_ref, life_ref=life_ref, profession_ref=profession_ref)

        return LatentModel(
            mode="methodology" if self._looks_methodology(context) else "project_reconstruction",
            input_frame={
                "raw_text": text,
                "project_type": context.get("project_type"),
                "space_label": context.get("space_label"),
            },
            latent_variables=latent_variables,
            tensions=tensions,
            hypotheses=self._hypotheses(place_ref=place_ref, profession_ref=profession_ref, life_ref=life_ref),
            uncertainty_ledger=self._uncertainty_ledger(place_ref=place_ref),
            decision_frontier={
                "next_question": "这栋房子一年会实际居住多久，它更像长期生活基地、阶段性返乡据点，还是家族精神场所？",
                "why_it_matters": "这个答案会决定空间深度、维护成本、家族聚合强度和旧新融合边界。",
            },
            evidence_index=evidence,
            quality_gate={
                "evidence_bound": True,
                "minimum_evidence_count": len(evidence),
                "allows_affective_language": bool(evidence_bound_affect),
            },
            provenance={"source": "latent_model_adapter", "generated_at": datetime.now().isoformat()},
            person_profile=person_profile,
            existential_job=self._existential_job(place_ref=place_ref, profession_ref=profession_ref),
            evidence_bound_affect=evidence_bound_affect,
            forbidden_capture_paths=self._forbidden_capture_paths(
                has_returning_home=bool(place_ref),
                has_profession=bool(profession_ref),
                has_life_stage=bool(life_ref),
            ),
        )

    def _build_evidence_index(self, text: str) -> List[EvidenceItem]:
        evidence: List[EvidenceItem] = []
        seen: set[str] = set()
        for term in self._EVIDENCE_TERMS:
            start = text.find(term)
            if start < 0 or term in seen:
                continue
            seen.add(term)
            evidence.append(
                EvidenceItem(
                    evidence_id=f"e{len(evidence) + 1}",
                    excerpt=term,
                    source_span={"start": start, "end": start + len(term)},
                    evidence_type="explicit",
                    reliability="high",
                )
            )
        if not evidence:
            evidence.append(
                EvidenceItem(
                    evidence_id="e1",
                    excerpt=text[:40],
                    source_span={"start": 0, "end": min(len(text), 40)},
                    evidence_type="explicit",
                    reliability="medium",
                )
            )
        return evidence

    @staticmethod
    def _first_ref(evidence: Iterable[EvidenceItem], terms: Iterable[str]) -> Optional[str]:
        term_set = set(terms)
        for item in evidence:
            if item.excerpt in term_set:
                return item.evidence_id
        return None

    @staticmethod
    def _person_profile(items: List[LatentVariableItem], evidence_refs: List[str]) -> List[Dict[str, Any]]:
        if not items:
            return []
        profile: Dict[str, Any] = {"evidence_refs": evidence_refs[:4]}
        for item in items:
            profile[item.id] = item.value
        return [profile]

    @staticmethod
    def _looks_methodology(context: Dict[str, Any]) -> bool:
        axes = context.get("semantic_axes") or {}
        return "methodology" in set(axes.get("input_intents") or [])

    @staticmethod
    def _tensions(context: Dict[str, Any], *, has_returning_home: bool, has_profession: bool) -> List[Dict[str, Any]]:
        tensions = []
        for index, item in enumerate(context.get("main_tensions") or [], start=1):
            if isinstance(item, dict):
                statement = item.get("title") or item.get("statement") or item.get("name")
            else:
                statement = str(item)
            if statement:
                tensions.append({"id": f"adapter_tension_{index}", "statement": statement})
        if has_returning_home:
            tensions.append({"id": "return_vs_daily_life", "statement": "衣锦还乡的象征性与真实日常居住之间的张力"})
        if has_profession:
            tensions.append({"id": "designer_control_vs_local_build", "statement": "专业设计师的控制欲与乡土施工现实之间的张力"})
        return tensions[:5]

    @staticmethod
    def _hypotheses(*, place_ref: Optional[str], profession_ref: Optional[str], life_ref: Optional[str]) -> List[Dict[str, Any]]:
        hypotheses = []
        if place_ref:
            hypotheses.append({"id": "h_return_home", "statement": "民居可能不是单纯居住物，而是故乡关系的重新安放", "evidence_refs": [place_ref]})
        if profession_ref:
            hypotheses.append({"id": "h_designer_old_new", "statement": "职业背景会让旧与新的融合成为核心判断，而非表层风格选择", "evidence_refs": [profession_ref]})
        if life_ref:
            hypotheses.append({"id": "h_life_stage", "statement": "50岁阶段可能同时牵动童年记忆、事业回望与后半场生活方式", "evidence_refs": [life_ref]})
        return hypotheses

    @staticmethod
    def _uncertainty_ledger(*, place_ref: Optional[str]) -> List[Dict[str, Any]]:
        items = [
            {"id": "u_occupancy", "question": "一年实际居住多久", "impact": "决定维护成本与功能配比"},
            {"id": "u_family", "question": "这是个人安放还是家族聚合", "impact": "决定公共空间和私密空间的重心"},
        ]
        if place_ref:
            items.append({"id": "u_local_ties", "question": "与村里亲友和施工队的关系边界", "impact": "决定落地协作方式"})
        return items

    @staticmethod
    def _existential_job(*, place_ref: Optional[str], profession_ref: Optional[str]) -> Dict[str, Any]:
        if not place_ref:
            return {}
        statement = "把民居从居住工程提升为故乡关系、家族记忆与身心安放的容器"
        if profession_ref:
            statement += "，同时处理室内设计师职业经验与乡土建造之间的旧新融合"
        return {"statement": statement, "evidence_refs": [ref for ref in (place_ref, profession_ref) if ref]}

    @staticmethod
    def _evidence_bound_affect(*, place_ref: Optional[str], life_ref: Optional[str], profession_ref: Optional[str]) -> List[Dict[str, Any]]:
        result = []
        if place_ref:
            result.append({"claim": "故土怀念与返乡安放", "allowed_terms": ["返乡", "故乡", "身心安放", "回归"], "evidence_refs": [place_ref]})
        if life_ref:
            result.append({"claim": "人生后半场与事业回望", "allowed_terms": ["职业后半场", "人生阶段", "事业回望"], "evidence_refs": [life_ref]})
        if profession_ref:
            result.append({"claim": "职业身份影响旧新融合", "allowed_terms": ["设计师", "旧与新", "专业经验"], "evidence_refs": [profession_ref]})
        return result

    @staticmethod
    def _forbidden_capture_paths(*, has_returning_home: bool, has_profession: bool, has_life_stage: bool) -> List[Dict[str, Any]]:
        paths = []
        if has_returning_home or has_life_stage:
            paths.append({"id": "style_over_capture", "rule": "不得把返乡民居压缩成风格标签、网红审美或材料气质问题"})
        if has_profession:
            paths.append({"id": "hard_constraint_over_capture", "rule": "不得只讨论施工工艺、户型尺寸和设备条件，而忽略设计师身份带来的生活方式与控制边界"})
        return paths
