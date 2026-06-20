"""LLM insight protocol for demand reconstruction.

This module centralizes the demand-reconstruction insight algorithm so the
service layer only orchestrates routing, fallback, and rendering.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional


class DemandReconstructionInsightProtocol:
    """Build and validate the LLM insight layer for demand reconstruction."""

    _FORBIDDEN_TERMS = (
        "完整方案",
        "完整任务书",
        "施工级",
        "施工图",
        "报价",
        "材料清单",
        "平面排布",
    )
    _GENERIC_TERMS = ("建议先明确需求", "可以做", "根据你的需求")
    _CLICHE_TERMS = (
        "温馨舒适",
        "品质生活",
        "有归属感",
        "家的感觉",
        "放松身心",
        "温暖惬意",
        "功能齐全",
        "动线合理",
        "空间利用率高",
        "满足需求",
        "布局合理",
        "简约大气",
        "时尚现代",
        "低调奢华",
        "自然和谐",
        "喜欢什么风格",
        "重视功能还是氛围",
    )
    _GENERIC_STEP_TITLES = (
        "选择判断路径",
        "成立路径",
        "硬约束",
        "取舍边界",
    )
    _BLUEPRINT_FIELDS = (
        "task_reframe",
        "project_viability_judgment",
        "primary_risk",
        "sections",
        "key_forks",
        "unknowns",
        "next_question",
    )
    _MEANINGFUL_FIELDS = {"task_reframe", "project_viability_judgment", "primary_risk", "sections"}
    _MIN_LENGTHS = {
        "task_reframe": 35,
        "project_viability_judgment": 18,
        "primary_risk": 18,
        "next_question": 10,
    }

    def build_prompt(self, adapter_context: Dict[str, Any], rule_plan: Dict[str, Any]) -> str:
        compact_context = self._build_prompt_context(adapter_context)
        compact_rule_plan = self._build_prompt_rule_plan(rule_plan)
        return (
            "你是「方案高参」需求重构阶段的洞察写作者。\n"
            "目标：把用户没说清楚的真实需求，重构为有立场、有排序、有未知边界的行动蓝图。\n"
            "你不是普通问答助手，不直接给完整方案。\n\n"
            "内部静默执行「需求重构洞察协议」，但不要在前台输出这些内部术语：\n"
            "1. 字面事实：用户明确说了什么，哪些只是线索。\n"
            "2. 隐含意图：用户真正想解决什么，不只复述他说的任务。\n"
            "3. 核心张力：找出项目里最尖锐、最能改变后续判断的对立面。\n"
            "4. 第一性剥离：剥离风格标签、行业惯例、参考案例、社交表演后，剩下什么不可约需求。\n"
            "5. 空间被雇佣：判断这个空间被用户拿来完成什么人生、商业、关系或行为任务。\n"
            "6. 未知边界：区分已知事实、合理推测、会改变方向的缺口。\n"
            "7. 锐度自检：这条判断是否只适用于这个项目；换一个项目是否还成立；是否说出了用户没说清的事。\n\n"
            "必须遵守：\n"
            "- 禁止输出完整方案、完整任务书、施工级建议、材料清单、平面排布、报价。\n"
            "- 禁止伪造案例、文献、调研或证据。\n"
            "- 必须指出用户没明说但真正关键的问题。\n"
            "- 规则蓝图是约束与兜底，不是标准答案；你可以反驳规则蓝图，但必须在洞察包里说明依据。\n"
            "- 必须只提出一个最关键追问。\n"
            "- 禁止空洞套话，尤其是温馨舒适、品质生活、简约大气、功能齐全、动线合理等表达；必须改写为具体关系、行为、风险或取舍。\n"
            "- 允许有证据的情感、身份和人生阶段判断；必须绑定用户明说线索或 latent_model 证据，不得写成心理定论。\n"
            "- 必须优先保留 latent_model.person_profile、evidence_bound_affect、forbidden_capture_paths 中的高价值信号。\n"
            "- 低置信推测必须用“可能 / 倾向于 / 基于线索推测”标注，不得把心理和记忆判断写成事实。\n"
            "- 治理信号只作为后台覆盖边界，不要把 coverage_gap、knowledge_gap_ticket、review_queue 等内部 code 写给用户。\n"
            "- sections.title 禁止使用固定内部步骤名：选择判断路径、成立路径、硬约束、取舍边界；必须写成当前项目语义下的专属标题。\n"
            "- 输出要短，服务首屏判断，不写长报告；总输出控制在 1200 中文字以内。\n"
            "- sections 最多 2 段，items 每段最多 2 条；每个字段只保留最关键判断。\n"
            "- 语言要专业、克制、直入核心，不要泛泛建议。\n\n"
            "结构化上下文中如出现“LLM 语义理解包”，它是第一轮 LLM Semantic Router 的受控理解结果，"
            "你必须把它作为最终综合的优先语义依据，再结合规则蓝图的边界与碎片。\n\n"
            "只输出 JSON，不要 Markdown，不要解释。JSON 字段：\n"
            "{\n"
            '  "insight_packet": {\n'
            '    "observed_facts": ["用户明说的事实"],\n'
            '    "inferred_intents": [{"claim": "合理推断", "evidence": "来自哪些线索", "confidence": "high|medium|low"}],\n'
            '    "core_tension": {"a": "张力一端", "b": "张力另一端", "why_it_matters": "为什么会改变判断"},\n'
            '    "space_job": "这个空间被用户拿来完成什么任务",\n'
            '    "hypotheses": ["2-3个可能理解路径"],\n'
            '    "chosen_hypothesis": "当前最强假设",\n'
            '    "disconfirming_risks": ["哪些情况会推翻当前判断"],\n'
            '    "decisive_question": "一个最能推进判断的问题",\n'
            '    "anti_cliche_check": "说明哪些判断只适用于本项目"\n'
            "  },\n"
            '  "task_reframe": "一句真实需求重构",\n'
            '  "project_viability_judgment": "项目成立判断",\n'
            '  "primary_risk": "头号风险",\n'
            '  "sections": [{"title": "...", "body": "...", "items": ["..."], "emphasis": "high|medium"}],\n'
            '  "key_forks": ["2-3个关键分叉"],\n'
            '  "unknowns": ["2-4个未知边界"],\n'
            '  "next_question": "一个关键追问，不加问号"\n'
            "}\n\n"
            f"结构化上下文：{json.dumps(compact_context, ensure_ascii=False)}\n\n"
            f"当前规则蓝图（只作为约束、边界和兜底，不作为标准答案）：{json.dumps(compact_rule_plan, ensure_ascii=False)}"
        )

    def _build_prompt_context(self, adapter_context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "source_message": adapter_context.get("source_message"),
            "project_type": adapter_context.get("project_type"),
            "project_type_name": adapter_context.get("project_type_name"),
            "space_label": adapter_context.get("space_label"),
            "classification": self._compact_classification(adapter_context.get("classification")),
            "context_vector": self._compact_mapping(adapter_context.get("context_vector")),
            "semantic_axes": self._compact_semantic_axes(adapter_context.get("semantic_axes")),
            "main_tensions": self._compact_main_tensions(adapter_context.get("main_tensions")),
            "missing_slots": self._compact_missing_slots(adapter_context.get("missing_slots")),
            "knowledge_coverage_ceiling": self._compact_coverage(adapter_context.get("knowledge_coverage_ceiling")),
            "semantic_candidate_set": self._compact_candidates(adapter_context.get("semantic_candidate_set")),
            "archetype": self._compact_archetype(adapter_context.get("archetype")),
            "latent_model": self._compact_latent_model(adapter_context.get("latent_model")),
            "llm_semantic_understanding": self._compact_llm_semantic_understanding(
                adapter_context.get("llm_semantic_understanding")
            ),
            "llm_semantic_scan": self._compact_llm_semantic_scan(
                adapter_context.get("llm_semantic_scan")
            ),
            "governed_knowledge_assets": self._compact_governed_knowledge_assets(
                adapter_context.get("governed_knowledge_assets")
            ),
            "context_source": adapter_context.get("context_source"),
        }

    def _build_prompt_rule_plan(self, rule_plan: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "task_reframe": rule_plan.get("task_reframe"),
            "project_viability_judgment": rule_plan.get("project_viability_judgment"),
            "primary_risk": rule_plan.get("primary_risk"),
            "key_forks": self._take_strings(rule_plan.get("key_forks"), limit=4),
            "unknowns": self._take_strings(rule_plan.get("unknowns"), limit=5),
            "sections": self._compact_sections(rule_plan.get("sections")),
            "next_question": rule_plan.get("next_question"),
            "routing_recommendation": rule_plan.get("routing_recommendation"),
            "coverage_level": rule_plan.get("coverage_level"),
            "component_intent": self._compact_component_intents(rule_plan.get("component_intent")),
            "governance_signals": self._compact_governance_signals(rule_plan.get("governance_signals")),
        }

    def _compact_latent_model(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        return {
            key: self._compact_value(value.get(key))
            for key in (
                "schema_version",
                "mode",
                "person_profile",
                "existential_job",
                "evidence_bound_affect",
                "forbidden_capture_paths",
                "latent_variables",
                "tensions",
                "uncertainty_ledger",
                "decision_frontier",
            )
            if value.get(key) not in (None, "", [], {})
        }

    def _compact_classification(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        result = {
            key: value.get(key)
            for key in (
                "status",
                "primary_bucket",
                "parent_type",
                "project_type",
                "project_type_name",
                "confidence",
                "confidence_level",
                "coverage_gap",
                "knowledge_gap",
                "needs_industry_clarification",
            )
            if key in value
        }
        if value.get("specialty_tags"):
            result["specialty_tags"] = self._take_strings(value.get("specialty_tags"), limit=5)
        if value.get("secondary_candidates"):
            result["secondary_candidates"] = self._compact_candidates(value.get("secondary_candidates"), limit=3)
        if value.get("clarification_questions"):
            result["clarification_questions"] = self._take_strings(value.get("clarification_questions"), limit=3)
        ambiguity = value.get("ambiguity")
        if isinstance(ambiguity, dict):
            result["ambiguity"] = {
                key: ambiguity.get(key)
                for key in ("is_ambiguous", "ambiguity_type")
                if key in ambiguity
            }
        return result

    def _compact_mapping(self, value: Any, *, max_items: int = 12) -> Any:
        if not isinstance(value, dict):
            return value
        result: Dict[str, Any] = {}
        for key, item in value.items():
            if len(result) >= max_items:
                break
            compacted = self._compact_value(item)
            if compacted not in (None, "", [], {}, "Unknown"):
                result[key] = compacted
        return result

    def _compact_llm_semantic_scan(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        result: Dict[str, Any] = {}
        for key in (
            "result",
            "matched_targets",
            "novelty_level",
            "confidence_band",
            "max_confidence",
            "source",
        ):
            compacted = self._compact_value(value.get(key))
            if compacted not in (None, "", [], {}, "Unknown"):
                result[key] = compacted
        asset_scan = value.get("asset_scan")
        if isinstance(asset_scan, dict):
            compacted_asset_scan: Dict[str, Any] = {}
            rule_fragments = self._compact_llm_semantic_items(
                asset_scan.get("rule_fragments"),
                label_keys=("group_id", "fragment_id", "source"),
                limit=5,
            )
            if rule_fragments:
                compacted_asset_scan["rule_fragments"] = rule_fragments
            approved_assets = self._compact_asset_scan_items(
                asset_scan.get("approved_knowledge_assets"),
                keys=("card_id", "title", "project_type", "evidence_level", "source"),
                limit=5,
            )
            if approved_assets:
                compacted_asset_scan["approved_knowledge_assets"] = approved_assets
            for key in ("semantic_axes", "main_tensions", "knowledge_coverage"):
                compacted = self._compact_value(asset_scan.get(key))
                if compacted not in (None, "", [], {}, "Unknown"):
                    compacted_asset_scan[key] = compacted
            if compacted_asset_scan:
                result["asset_scan"] = compacted_asset_scan
        return result

    def _compact_llm_semantic_understanding(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        result: Dict[str, Any] = {}
        for key in (
            "intent_type",
            "project_anchor",
            "project_object",
            "novelty_level",
            "recommended_scan_targets",
            "package_ids",
            "ontology_dimension_ids",
        ):
            compacted = self._compact_value(value.get(key))
            if compacted not in (None, "", [], {}, "Unknown"):
                result[key] = compacted
        candidates = self._compact_llm_semantic_items(
            value.get("space_candidates"),
            label_keys=("label", "id"),
            limit=5,
        )
        if candidates:
            result["space_candidates"] = candidates
        tensions = self._compact_llm_semantic_items(
            value.get("core_tensions"),
            label_keys=("title", "label"),
            limit=4,
        )
        if tensions:
            result["core_tensions"] = tensions
        fragment_targets = self._compact_llm_semantic_items(
            value.get("recommended_fragment_targets"),
            label_keys=("group_id", "fragment_id"),
            limit=4,
        )
        if fragment_targets:
            result["recommended_fragment_targets"] = fragment_targets
        missing_slots = self._take_strings(value.get("missing_slots"), limit=5)
        if missing_slots:
            result["missing_slots"] = missing_slots
        return result

    def _compact_llm_semantic_items(
        self,
        value: Any,
        *,
        label_keys: tuple[str, ...],
        limit: int,
    ) -> list[Dict[str, Any]]:
        result: list[Dict[str, Any]] = []
        for item in value or []:
            if not isinstance(item, dict):
                continue
            compacted: Dict[str, Any] = {}
            for key in label_keys:
                if item.get(key) not in (None, "", [], {}):
                    compacted[key] = self._compact_value(item.get(key))
            if item.get("confidence") not in (None, "", [], {}):
                compacted["confidence"] = item.get("confidence")
            evidence = self._take_strings(item.get("evidence"), limit=3)
            if evidence:
                compacted["evidence"] = evidence
            if compacted:
                result.append(compacted)
            if len(result) >= limit:
                break
        return result

    def _compact_asset_scan_items(
        self,
        value: Any,
        *,
        keys: tuple[str, ...],
        limit: int,
    ) -> list[Dict[str, Any]]:
        result: list[Dict[str, Any]] = []
        for item in value or []:
            if not isinstance(item, dict):
                continue
            compacted: Dict[str, Any] = {}
            for key in keys:
                if item.get(key) not in (None, "", [], {}):
                    compacted[key] = self._compact_value(item.get(key))
            evidence = self._take_strings(item.get("evidence"), limit=3)
            if evidence:
                compacted["evidence"] = evidence
            match_metadata = item.get("match_metadata")
            if isinstance(match_metadata, dict):
                compacted["match_metadata"] = self._compact_mapping(match_metadata, max_items=5)
            if compacted:
                result.append(compacted)
            if len(result) >= limit:
                break
        return result

    def _compact_semantic_axes(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        return {
            key: self._take_strings(item, limit=5)
            for key, item in value.items()
            if item
        }

    def _compact_main_tensions(self, value: Any, *, limit: int = 4) -> list[Dict[str, Any]]:
        result = []
        for item in value or []:
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    key: self._compact_value(item.get(key))
                    for key in ("title", "prompt", "score", "axis", "related_options", "relevance_terms")
                    if item.get(key) not in (None, "", [], {})
                }
            )
            if len(result) >= limit:
                break
        return result

    def _compact_missing_slots(self, value: Any, *, limit: int = 5) -> list[Dict[str, Any]]:
        result = []
        for item in value or []:
            if isinstance(item, str):
                result.append({"note": item})
            elif isinstance(item, dict):
                result.append(
                    {
                        key: self._compact_value(item.get(key))
                        for key in ("slot", "label", "note", "user_visible_note", "priority")
                        if item.get(key) not in (None, "", [], {})
                    }
                )
            if len(result) >= limit:
                break
        return result

    def _compact_coverage(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        return {
            key: self._compact_value(value.get(key))
            for key in (
                "coverage_level",
                "ceiling_level",
                "must_not_claim_specialist_coverage",
                "source",
                "reasons",
                "allowed_outputs",
                "forbidden_outputs",
                "user_visible_note",
            )
            if value.get(key) not in (None, "", [], {})
        }

    def _compact_candidates(self, value: Any, *, limit: int = 5) -> list[Dict[str, Any]]:
        result = []
        for item in value or []:
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    key: self._compact_value(item.get(key))
                    for key in ("id", "score", "role", "evidence", "counter_evidence", "routing_target")
                    if item.get(key) not in (None, "", [], {})
                }
            )
            if len(result) >= limit:
                break
        return result

    def _compact_archetype(self, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        return {
            key: self._compact_value(value.get(key))
            for key in ("primary", "secondary", "downweighted", "routing_target")
            if value.get(key) not in (None, "", [], {})
        }

    def _compact_sections(self, value: Any, *, limit: int = 4) -> list[Dict[str, Any]]:
        result = []
        for section in value or []:
            if not isinstance(section, dict):
                continue
            result.append(
                {
                    "title": section.get("title"),
                    "body": section.get("body"),
                    "items": self._take_strings(section.get("items"), limit=3),
                    "emphasis": section.get("emphasis"),
                }
            )
            if len(result) >= limit:
                break
        return result

    def _compact_component_intents(self, value: Any, *, limit: int = 3) -> list[Dict[str, Any]]:
        result = []
        for item in value or []:
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    key: self._compact_value(item.get(key))
                    for key in ("type", "title", "body", "prompt", "options")
                    if item.get(key) not in (None, "", [], {})
                }
            )
            if len(result) >= limit:
                break
        return result

    def _compact_governance_signals(self, value: Any, *, limit: int = 3) -> list[Dict[str, Any]]:
        result = []
        for item in value or []:
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    key: self._compact_value(item.get(key))
                    for key in ("code", "level", "review_queue", "message")
                    if item.get(key) not in (None, "", [], {})
                }
            )
            if len(result) >= limit:
                break
        return result

    def _compact_governed_knowledge_assets(self, value: Any, *, limit: int = 3) -> list[Dict[str, Any]]:
        result = []
        for item in value or []:
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    key: self._compact_value(item.get(key))
                    for key in (
                        "card_id",
                        "title",
                        "project_type",
                        "summary",
                        "evidence",
                        "allowed_use",
                        "not_allowed_use",
                        "evidence_level",
                        "source",
                    )
                    if item.get(key) not in (None, "", [], {})
                }
            )
            if len(result) >= limit:
                break
        return result

    def _compact_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return self._compact_mapping(value, max_items=6)
        if isinstance(value, list):
            return self._take_strings(value, limit=5)
        return value

    def _take_strings(self, value: Any, *, limit: int) -> list[Any]:
        result = []
        for item in value or []:
            if isinstance(item, dict):
                text = item.get("user_visible_note") or item.get("note") or item.get("label") or item.get("title")
                if text:
                    result.append(text)
            else:
                result.append(item)
            if len(result) >= limit:
                break
        return result

    def build_repair_prompt(
        self,
        *,
        original_prompt: str,
        rejected_content: str,
        rejection_reason: str,
    ) -> str:
        return (
            f"{original_prompt}\n\n"
            "上一次输出被需求重构协议门拒绝。\n"
            f"拒绝原因：{rejection_reason}\n"
            "请重新输出完整 JSON：先给 insight_packet，再给前台蓝图字段；"
            "保留项目特异性判断，删除所有套话、泛化风格词和完整方案倾向；"
            "不要解释，不要 Markdown。"
            "\n\n"
            f"上一次输出：{rejected_content}"
        )

    def build_blueprint_from_response(
        self,
        *,
        rule_plan: Dict[str, Any],
        content: str,
    ) -> Optional[Dict[str, Any]]:
        merged, _diagnostics = self.build_blueprint_from_response_detailed(
            rule_plan=rule_plan,
            content=content,
        )
        return merged

    def build_blueprint_from_response_detailed(
        self,
        *,
        rule_plan: Dict[str, Any],
        content: str,
    ) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        text = str(content or "").strip()
        if not text:
            return None, {"status": "empty_response"}

        candidate = self.parse_response_json(text)
        if not candidate:
            return None, {"status": "invalid_json"}

        merged, quality_report = self.merge_blueprint_with_quality(rule_plan, candidate)
        accepted_fields = set(quality_report["accepted_fields"])
        accepted_blueprint_fields = accepted_fields.intersection(self._BLUEPRINT_FIELDS)
        has_meaningful_insight = bool(accepted_fields.intersection(self._MEANINGFUL_FIELDS))
        if not has_meaningful_insight or len(accepted_blueprint_fields) < 3:
            return None, {
                "status": "quality_rejected",
                "reason": quality_report.get("dominant_rejection_reason") or "low_field_acceptance",
                "quality_report": quality_report,
            }

        status = "partial" if quality_report["fallback_fields"] else "used"
        merged["insight_source"] = "llm_partial" if status == "partial" else "llm"
        merged["llm_status"] = status
        merged["quality_report"] = quality_report
        return merged, {"status": status, "quality_report": quality_report}

    @staticmethod
    def parse_response_json(content: str) -> Optional[Dict[str, Any]]:
        text = str(content or "").strip()
        if not text:
            return None
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
        if fenced:
            text = fenced.group(1).strip()
        elif "{" in text and "}" in text:
            text = text[text.find("{") : text.rfind("}") + 1]
        try:
            data = json.loads(text)
        except Exception:
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def merge_blueprint(rule_plan: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(rule_plan)
        for field in (
            "task_reframe",
            "project_viability_judgment",
            "primary_risk",
            "key_forks",
            "unknowns",
            "sections",
            "next_question",
        ):
            value = candidate.get(field)
            if value:
                merged[field] = value
        return merged

    def merge_blueprint_with_quality(
        self,
        rule_plan: Dict[str, Any],
        candidate: Dict[str, Any],
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        merged = dict(rule_plan)
        accepted_fields: list[str] = []
        rejected_fields: Dict[str, str] = {}
        fallback_fields: list[str] = []

        for field in self._BLUEPRINT_FIELDS:
            if field not in candidate or candidate.get(field) in (None, "", [], {}):
                continue
            valid, reason = self._validate_field(field, candidate.get(field))
            if valid:
                merged[field] = candidate[field]
                accepted_fields.append(field)
            else:
                rejected_fields[field] = reason
                fallback_fields.append(field)

        insight_packet = candidate.get("insight_packet")
        if insight_packet:
            valid, reason = self._validate_insight_packet(insight_packet)
            if valid:
                merged["insight_packet"] = insight_packet
                accepted_fields.append("insight_packet")
            else:
                rejected_fields["insight_packet"] = reason

        return merged, {
            "accepted_fields": accepted_fields,
            "rejected_fields": rejected_fields,
            "fallback_fields": fallback_fields,
            "dominant_rejection_reason": self._dominant_rejection_reason(rejected_fields),
            "specificity_score": self._score_specificity(accepted_fields, rejected_fields),
            "evidence_score": 1.0 if "insight_packet" in accepted_fields else 0.45,
            "tension_score": 1.0 if "primary_risk" in accepted_fields and "insight_packet" in accepted_fields else 0.6,
            "boundary_score": 1.0 if not self._contains_forbidden(json.dumps(candidate, ensure_ascii=False)) else 0.0,
            "generic_penalty": self._generic_penalty(rejected_fields),
        }

    def _validate_field(self, field: str, value: Any) -> tuple[bool, str]:
        if field in {"sections"}:
            return self._validate_sections(value)
        if field in {"key_forks", "unknowns"}:
            return self._validate_string_list(value)
        return self._validate_text_field(field, value)

    def _validate_text_field(self, field: str, value: Any) -> tuple[bool, str]:
        text = str(value or "").strip()
        if not text:
            return False, "missing"
        if len(text) < self._MIN_LENGTHS.get(field, 1):
            return False, "too_short"
        if self._contains_forbidden(text):
            return False, "over_reaching"
        if self._contains_cliche(text):
            return False, "cliche"
        if field == "task_reframe" and self._is_generic_text(text):
            return False, "generic_reframe"
        if field == "next_question" and self._is_generic_text(text):
            return False, "generic_question"
        return True, "accepted"

    def _validate_string_list(self, value: Any) -> tuple[bool, str]:
        if not isinstance(value, list) or not value:
            return False, "missing_required_fields"
        joined = "\n".join(str(item) for item in value)
        if self._contains_forbidden(joined):
            return False, "over_reaching"
        if self._contains_cliche(joined):
            return False, "cliche"
        if all(len(str(item).strip()) < 6 for item in value):
            return False, "too_short"
        return True, "accepted"

    def _validate_sections(self, value: Any) -> tuple[bool, str]:
        if not isinstance(value, list) or not value:
            return False, "missing_required_fields"
        joined = json.dumps(value, ensure_ascii=False)
        if self._contains_forbidden(joined):
            return False, "over_reaching"
        if self._contains_cliche(joined):
            return False, "cliche"
        for section in value:
            if not isinstance(section, dict):
                return False, "invalid_section"
            if not str(section.get("title") or "").strip() or not str(section.get("body") or "").strip():
                return False, "invalid_section"
            if self._contains_generic_step_title(str(section.get("title") or "")):
                return False, "generic_step_title"
            items = section.get("items") or []
            if not isinstance(items, list) or not items:
                return False, "invalid_section"
        return True, "accepted"

    def _validate_insight_packet(self, value: Any) -> tuple[bool, str]:
        if not isinstance(value, dict) or not value:
            return False, "missing"
        joined = json.dumps(value, ensure_ascii=False)
        if self._contains_forbidden(joined):
            return False, "over_reaching"
        if self._contains_cliche(joined):
            return False, "cliche"
        has_hypothesis = bool(value.get("hypotheses")) and bool(value.get("chosen_hypothesis"))
        has_tension = bool(value.get("core_tension"))
        has_evidence = bool(value.get("observed_facts")) or bool(value.get("inferred_intents"))
        if not (has_hypothesis and has_tension and has_evidence):
            return False, "weak_insight_packet"
        return True, "accepted"

    def _contains_forbidden(self, text: str) -> bool:
        return any(term in text for term in self._FORBIDDEN_TERMS)

    def _contains_cliche(self, text: str) -> bool:
        return any(term in text for term in self._CLICHE_TERMS)

    def _contains_generic_step_title(self, text: str) -> bool:
        return any(term in text for term in self._GENERIC_STEP_TITLES)

    def _is_generic_text(self, text: str) -> bool:
        stripped = text.strip("。！？? ")
        return any(term == stripped or term in stripped for term in self._GENERIC_TERMS)

    @staticmethod
    def _score_specificity(accepted_fields: list[str], rejected_fields: Dict[str, str]) -> float:
        total = len(accepted_fields) + len(rejected_fields)
        if total == 0:
            return 0.0
        return round(len(accepted_fields) / total, 2)

    @staticmethod
    def _generic_penalty(rejected_fields: Dict[str, str]) -> float:
        generic_reasons = {"cliche", "generic_reframe", "generic_question", "generic_step_title"}
        if not rejected_fields:
            return 0.0
        generic_count = sum(1 for reason in rejected_fields.values() if reason in generic_reasons)
        return round(generic_count / len(rejected_fields), 2)

    @staticmethod
    def _dominant_rejection_reason(rejected_fields: Dict[str, str]) -> Optional[str]:
        if not rejected_fields:
            return None
        reasons = list(rejected_fields.values())
        for reason in ("over_reaching", "cliche", "too_short", "missing_required_fields", "generic_reframe"):
            if reason in reasons:
                return reason
        return reasons[0]

    def passes_quality_gate(self, plan: Dict[str, Any]) -> bool:
        return self.quality_gate_rejection_reason(plan) is None

    def quality_gate_rejection_reason(self, plan: Dict[str, Any]) -> Optional[str]:
        task_reframe = str(plan.get("task_reframe") or "").strip()
        primary_risk = str(plan.get("primary_risk") or "").strip()
        sections = plan.get("sections") or []
        key_forks = plan.get("key_forks") or []
        unknowns = plan.get("unknowns") or []
        joined = "\n".join(
            [
                task_reframe,
                str(plan.get("project_viability_judgment") or ""),
                primary_risk,
                str(plan.get("next_question") or ""),
                json.dumps(sections, ensure_ascii=False),
            ]
        )
        if len(task_reframe) < 35 or len(primary_risk) < 18:
            return "too_short"
        if not sections or not key_forks or not unknowns:
            return "missing_required_fields"
        if any(term in joined for term in self._FORBIDDEN_TERMS):
            return "over_reaching"
        if any(term in joined for term in self._CLICHE_TERMS):
            return "cliche"
        if task_reframe in self._GENERIC_TERMS or any(term == task_reframe for term in self._GENERIC_TERMS):
            return "generic_reframe"
        return None
