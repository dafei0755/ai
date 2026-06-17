"""Demand reconstruction orchestration for Scheme Advisor.

This layer is the purchase-before-proof shape for Design Brief 2.0:
it returns an action blueprint that reconstructs vague demand, not a formal
intake questionnaire.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

from .demand_reconstruction_context_adapter import DemandReconstructionContextAdapter
from .demand_reconstruction_output_planner import DemandReconstructionOutputPlanner


class DemandReconstructionService:
    """Generate a non-freezing demand reconstruction for early ambiguous inputs."""

    CARD_TYPE = "demand_reconstruction_blueprint"
    INTENT = "demand_reconstruction_blueprint"

    _FORMAL_TERMS = (
        "设计任务书",
        "任务书",
        "完整设计",
        "完整室内设计",
        "完整室内设计概念框架",
        "完整概念框架",
        "完整框架",
        "可执行版本",
        "按这个做",
        "定稿",
        "输出方案",
    )
    _ADVICE_TERMS = ("给出建议", "给点建议", "怎么建议", "帮我想想", "怎么看", "如何", "怎么")
    _SPACE_TERMS = (
        "民居",
        "住宅",
        "老家",
        "乡村",
        "自宅",
        "茶饮",
        "茶空间",
        "咖啡",
        "店",
        "办公室",
        "展厅",
        "民宿",
        "酒店",
        "社区",
        "改造",
        "会所",
        "空间",
        "冷藏柜",
    )

    def __init__(
        self,
        *,
        llm: Any = None,
        context_adapter: Optional[DemandReconstructionContextAdapter] = None,
        output_planner: Optional[DemandReconstructionOutputPlanner] = None,
    ) -> None:
        self._llm = llm
        self._context_adapter = context_adapter or DemandReconstructionContextAdapter()
        self._output_planner = output_planner or DemandReconstructionOutputPlanner()

    def handle_message(
        self,
        *,
        session: Dict[str, Any],
        user_message: str,
        in_response_to_card_id: Optional[str],
        selected_option_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        pending_card = session.get("pending_guidance_card") or {}
        if pending_card.get("card_type") == self.CARD_TYPE:
            context = dict(session.get("demand_reconstruction_context") or {})
            if selected_option_id == "handoff_to_brief":
                context["handoff_requested"] = True
                return {
                    "handoff_requested": True,
                    "demand_reconstruction_context": context,
                }
            if selected_option_id == "continue_demand_reconstruction" or self._is_demand_reconstruction_followup(user_message):
                return self._result(user_message, previous_context=context)
            return None

        if not self.should_handle(user_message):
            return None
        return self._result(user_message)

    def should_handle(self, message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        if self.is_formal_brief_request(text):
            return False
        has_advice_intent = any(term in text for term in self._ADVICE_TERMS)
        has_space_hint = any(term in text for term in self._SPACE_TERMS)
        has_research_hint = any(term in text for term in ("研究", "源流", "历史", "文人", "雅集", "文化", "转译"))
        return has_advice_intent and (has_space_hint or has_research_hint)

    def is_formal_brief_request(self, message: str) -> bool:
        text = str(message or "")
        if any(term in text for term in self._FORMAL_TERMS):
            return True
        has_complete = "完整" in text
        has_framework = any(term in text for term in ("框架", "概念", "方案"))
        has_multi_topic = sum(1 for term in ("光", "材料", "动线", "自然", "空间", "界面", "精神性") if term in text) >= 3
        return has_complete and has_framework and has_multi_topic

    def _result(self, message: str, previous_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        adapter_context = self._context_adapter.build(message)
        if previous_context and previous_context.get("blueprint", {}).get("task_reframe"):
            adapter_context["previous_blueprint"] = previous_context["blueprint"]
        blueprint = self._build_blueprint(adapter_context)
        context = {
            "schema_version": "demand_reconstruction_context.v1",
            "reconstruction_type": "demand_reconstruction",
            "artifact_name": "action_blueprint",
            "display_title": "需求重构",
            "display_artifact_name": "行动蓝图",
            "created_at": datetime.now().isoformat(),
            "source_message": message,
            "adapter_context": self._public_adapter_context(adapter_context),
            "blueprint": blueprint,
            "brief_handoff_slots": blueprint["brief_handoff_slots"],
        }
        reply = self._render_reply(blueprint)
        return {
            "reply": reply,
            "intent": self.INTENT,
            "dialogue_layer": "demand_reconstruction",
            "handoff_available": True,
            "guidance_card": self._card(blueprint),
            "demand_reconstruction_context": context,
            "drafts": [],
            "upgrade_signal": None,
            "upgrade_suggested": False,
        }

    @staticmethod
    def _is_demand_reconstruction_followup(message: str) -> bool:
        return bool(str(message or "").strip())

    def _build_blueprint(self, adapter_context: Dict[str, Any]) -> Dict[str, Any]:
        rule_plan = self._output_planner.build_plan(adapter_context)
        if self._llm is None:
            return {**rule_plan, "insight_source": "rule"}
        llm_plan = self._build_llm_insight_blueprint(adapter_context, rule_plan)
        if llm_plan is None:
            return {**rule_plan, "insight_source": "rule_fallback"}
        return llm_plan

    def _build_llm_insight_blueprint(
        self,
        adapter_context: Dict[str, Any],
        rule_plan: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        prompt = self._llm_insight_prompt(adapter_context, rule_plan)
        try:
            response = self._llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            candidate = self._parse_llm_json(str(content or ""))
            if not candidate:
                return None
            merged = self._merge_llm_blueprint(rule_plan, candidate)
            if not self._passes_insight_quality_gate(merged):
                return None
            merged["insight_source"] = "llm"
            return self._output_planner.clamp_existing_plan(merged)
        except Exception as exc:
            logger.warning(f"[DemandReconstruction] LLM insight failed, fallback used: {exc}")
            return None

    @staticmethod
    def _llm_insight_prompt(adapter_context: Dict[str, Any], rule_plan: Dict[str, Any]) -> str:
        compact_context = {
            "source_message": adapter_context.get("source_message"),
            "project_type": adapter_context.get("project_type"),
            "project_type_name": adapter_context.get("project_type_name"),
            "space_label": adapter_context.get("space_label"),
            "semantic_axes": adapter_context.get("semantic_axes"),
            "main_tensions": adapter_context.get("main_tensions"),
            "missing_slots": adapter_context.get("missing_slots"),
            "archetype": adapter_context.get("archetype"),
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
            "5. 空间被雇佣：判断这个空间被用户拿来完成什么人生、商业、关系或行为任务。\n"
            "6. 未知边界：区分已知事实、合理推测、会改变方向的缺口。\n"
            "7. 锐度自检：这条判断是否只适用于这个项目；换一个项目是否还成立；是否说出了用户没说清的事。\n\n"
            "必须遵守：\n"
            "- 禁止输出完整方案、完整任务书、施工级建议、材料清单、平面排布、报价。\n"
            "- 禁止伪造案例、文献、调研或证据。\n"
            "- 必须指出用户没明说但真正关键的问题。\n"
            "- 必须只提出一个最关键追问。\n"
            "- 禁止使用温馨舒适、品质生活、简约大气、功能齐全、动线合理等套话；必须改写为具体关系、行为、风险或取舍。\n"
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

    @staticmethod
    def _parse_llm_json(content: str) -> Optional[Dict[str, Any]]:
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
    def _merge_llm_blueprint(rule_plan: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
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

    @staticmethod
    def _passes_insight_quality_gate(plan: Dict[str, Any]) -> bool:
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
        forbidden_terms = (
            "完整方案",
            "完整任务书",
            "施工级",
            "施工图",
            "报价",
            "材料清单",
            "平面排布",
        )
        generic_terms = ("建议先明确需求", "可以做", "根据你的需求")
        cliche_terms = (
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
        if len(task_reframe) < 35 or len(primary_risk) < 18:
            return False
        if not sections or not key_forks or not unknowns:
            return False
        if any(term in joined for term in forbidden_terms):
            return False
        if any(term in joined for term in cliche_terms):
            return False
        if task_reframe in generic_terms or any(term == task_reframe for term in generic_terms):
            return False
        return True

    @staticmethod
    def _render_reply(plan: Dict[str, Any]) -> str:
        forks = "\n".join(f"- {item}" for item in plan["key_forks"][:3])
        unknowns = "\n".join(f"- {item}" for item in plan["unknowns"][:4])
        section_blocks = []
        for section in plan.get("sections") or []:
            items = "\n".join(f"- {item}" for item in section.get("items") or [])
            section_blocks.append(
                f"**{section.get('title')}**\n{section.get('body')}\n{items}".strip()
            )
        dynamic_sections = "\n\n".join(section_blocks)
        next_question = (plan.get("next_question") or (plan.get("key_forks") or [""])[0]).strip("？?")
        return (
            "## 需求重构\n\n"
            f"{plan['task_reframe']}\n\n"
            f"我先不急着给方案。这里真正要先判断的是：{plan['project_viability_judgment']}\n\n"
            f"**关键判断**\n{plan['primary_risk']}\n\n"
            f"{dynamic_sections}\n\n"
            f"**会改变后续判断的分叉**\n{forks}\n\n"
            f"**现在不能直接下结论的原因**\n{unknowns}\n\n"
            f"**我建议先追问一个关键点**\n{next_question}？\n\n"
            f"**下一步**\n{plan['routing_recommendation']}"
        )

    @staticmethod
    def _card(plan: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "card_id": f"demand_reconstruction-{uuid.uuid4().hex[:8]}",
            "card_type": DemandReconstructionService.CARD_TYPE,
            "title": "需求重构",
            "display_label": "需求重构",
            "artifact_name": "行动蓝图",
            "reconstruction_type": "demand_reconstruction",
            "prompt_text": plan["task_reframe"],
            "options": [
                {
                    "id": "continue_demand_reconstruction",
                    "label": "继续需求重构",
                    "description": "继续把这个问题想清楚，不进入正式任务书。",
                },
                {
                    "id": "handoff_to_brief",
                    "label": "整理成设计任务书草稿",
                    "description": "把当前行动蓝图带入正式任务书问诊。",
                    "recommended": True,
                },
            ],
            "allow_freetext": True,
            "summary": plan,
            "sections": plan.get("sections") or [],
        }

    @staticmethod
    def _public_adapter_context(adapter_context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "project_type": adapter_context.get("project_type"),
            "project_type_name": adapter_context.get("project_type_name"),
            "space_label": adapter_context.get("space_label"),
            "semantic_axes": adapter_context.get("semantic_axes"),
            "main_tensions": adapter_context.get("main_tensions"),
            "archetype": adapter_context.get("archetype"),
            "context_source": adapter_context.get("context_source"),
        }
