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

    def build_prompt(self, adapter_context: Dict[str, Any], rule_plan: Dict[str, Any]) -> str:
        compact_context = {
            "source_message": adapter_context.get("source_message"),
            "project_type": adapter_context.get("project_type"),
            "project_type_name": adapter_context.get("project_type_name"),
            "space_label": adapter_context.get("space_label"),
            "semantic_axes": adapter_context.get("semantic_axes"),
            "main_tensions": adapter_context.get("main_tensions"),
            "missing_slots": adapter_context.get("missing_slots"),
            "archetype": adapter_context.get("archetype"),
            "latent_model": adapter_context.get("latent_model"),
        }
        return (
            "你是「方案高参」需求重构阶段的洞察写作者。\n"
            "目标：把用户没说清楚的真实需求，重构为有立场、有排序、有未知边界的行动蓝图。\n"
            "你不是普通问答助手，不直接给完整方案。\n\n"
            "内部静默执行「需求重构洞察协议」，但不要在前台输出这些内部术语：\n"
            "1. 字面事实：用户明确说了什么，哪些只是线索。\n"
            "2. 隐含意图：用户真正想解决什么，不只复述他说的任务。\n"
            "3. 核心张力：找出项目里最尖锐、最能改变后续判断的对立面。\n"
            "4. 第一性剥离：剥离风格标签、行业惯例、参考案例、社交表演后，剩下什么不可约需求。\n"
            "5. 空间被雇佣：先判断这个空间被用户拿来完成什么人生、身份、关系或行为任务；不要把人生任务压缩成功能配比。\n"
            "6. 未知边界：区分已知事实、合理推测、会改变方向的缺口。\n"
            "7. 锐度自检：这条判断是否只适用于这个项目；换一个项目是否还成立；是否说出了用户没说清的事。\n\n"
            "必须遵守：\n"
            "- 禁止输出完整方案、完整任务书、施工级建议、材料清单、平面排布、报价。\n"
            "- 禁止伪造案例、文献、调研或证据。\n"
            "- 必须指出用户没明说但真正关键的问题。\n"
            "- 必须只提出一个最关键追问。\n"
            "- 禁止空洞套话：温馨舒适、品质生活、简约大气、功能齐全、动线合理等没有证据的暖词必须拒绝。\n"
            "- 允许有证据的情感、身份和人生阶段判断：只有当 latent_model.evidence_bound_affect/person_profile 提供证据引用，且该判断会改变后续任务书分叉时，才可以写返乡、故乡、身心安放、职业后半场等表达。\n"
            "- 必须优先保留 latent_model.person_profile、evidence_bound_affect、forbidden_capture_paths 中的高价值信号，不能被风格、施工、设备或预算问题覆盖。\n"
            "- 低置信推测必须用“可能 / 倾向于 / 基于线索推测”标注，不得把心理和记忆判断写成事实。\n"
            "- 语言要专业、克制、直入核心，不要泛泛建议。\n\n"
            "只输出 JSON，不要 Markdown，不要解释。JSON 字段：\n"
            "{\n"
            '  "task_reframe": "一句真实需求重构",\n'
            '  "project_viability_judgment": "项目成立判断",\n'
            '  "primary_risk": "头号风险",\n'
            '  "sections": [{"title": "...", "body": "...", "items": ["..."], "emphasis": "high|medium"}],\n'
            '  "key_forks": ["2-3个关键分叉"],\n'
            '  "unknowns": ["2-4个未知边界"],\n'
            '  "next_question": "一个关键追问，不加问号"\n'
            "}\n\n"
            f"结构化上下文：{json.dumps(compact_context, ensure_ascii=False)}\n\n"
            f"当前规则蓝图：{json.dumps(rule_plan, ensure_ascii=False)}"
        )

    def build_blueprint_from_response(
        self,
        *,
        rule_plan: Dict[str, Any],
        content: str,
    ) -> Optional[Dict[str, Any]]:
        candidate = self.parse_response_json(content)
        if not candidate:
            return None
        merged = self.merge_blueprint(rule_plan, candidate)
        if not self.passes_quality_gate(merged):
            return None
        merged["insight_source"] = "llm"
        return merged

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

    def passes_quality_gate(self, plan: Dict[str, Any]) -> bool:
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
            return False
        if not sections or not key_forks or not unknowns:
            return False
        if any(term in joined for term in self._FORBIDDEN_TERMS):
            return False
        if any(term in joined for term in self._CLICHE_TERMS):
            return False
        if task_reframe in self._GENERIC_TERMS or any(term == task_reframe for term in self._GENERIC_TERMS):
            return False
        return True


