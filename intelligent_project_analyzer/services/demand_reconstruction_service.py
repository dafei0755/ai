"""Demand reconstruction orchestration for Scheme Advisor.

This layer is the purchase-before-proof shape for Design Brief 2.0:
it returns an action blueprint that reconstructs vague demand, not a formal
intake questionnaire.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

from .demand_reconstruction_context_adapter import DemandReconstructionContextAdapter
from .demand_reconstruction_insight_protocol import DemandReconstructionInsightProtocol
from .demand_reconstruction_insight_quality import DemandReconstructionInsightQualityEvaluator
from .demand_reconstruction_output_planner import DemandReconstructionOutputPlanner
from .latent_model_adapter import LatentModelAdapter


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
    _ADVICE_TERMS = ("给出建议", "给点建议", "怎么建议", "帮我想想", "怎么看", "如何", "怎么", "提出", "请提出", "分析", "系统分析", "梳理", "给出")
    _PROJECT_INTENT_TERMS = (
        "设计",
        "设计建议",
        "室内设计",
        "概念框架",
        "方案",
        "规划",
        "装修",
        "改造",
        "建",
        "做一个",
        "打算做",
        "想做",
        "需要一份",
        "请提出",
        "打造",
        "建设",
        "构建",
        "策略",
        "框架",
        "概念",
        "设计一个",
    )
    _SPACE_TERMS = (
        "民居",
        "住宅",
        "老家",
        "乡村",
        "自宅",
        "茶饮",
        "茶空间",
        "餐厅",
        "自建房",
        "木结构",
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
        "商铺",
        "铺位",
        "门店",
        "店铺",
        "奶茶",
        "饮品",
        "商场",
        "地铁",
        "总部",
        "大堂",
        "别墅",
        "大平层",
        "厨房",
        "茶室",
        "幼儿园",
        "活动室",
        "休息区",
        "月子中心",
        "展示墙",
        "汽车",
        "NIO House",
        "体验馆",
        "研究中心",
        "实验室",
        "展馆",
        "展陈",
        "零售",
        "办公",
        "用地",
        "园区",
        "VIP",
    )

    def __init__(
        self,
        *,
        llm: Any = None,
        context_adapter: Optional[DemandReconstructionContextAdapter] = None,
        insight_protocol: Optional[DemandReconstructionInsightProtocol] = None,
        output_planner: Optional[DemandReconstructionOutputPlanner] = None,
        latent_model_adapter: Optional[LatentModelAdapter] = None,
        insight_quality_evaluator: Optional[DemandReconstructionInsightQualityEvaluator] = None,
        require_llm: bool = False,
    ) -> None:
        self._llm = llm
        self._require_llm = require_llm
        self._context_adapter = context_adapter or DemandReconstructionContextAdapter()
        self._insight_protocol = insight_protocol or DemandReconstructionInsightProtocol()
        self._output_planner = output_planner or DemandReconstructionOutputPlanner()
        self._latent_model_adapter = latent_model_adapter or LatentModelAdapter()
        self._insight_quality_evaluator = insight_quality_evaluator or DemandReconstructionInsightQualityEvaluator()

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
        has_advice_intent = any(term in text for term in self._ADVICE_TERMS)
        has_project_intent = any(term in text for term in self._PROJECT_INTENT_TERMS)
        has_space_hint = any(term in text for term in self._SPACE_TERMS)
        has_research_hint = any(term in text for term in ("研究", "源流", "历史", "文人", "雅集", "文化", "转译"))
        has_numeric_project_anchor = bool(
            re.search(r"\d+(?:\.\d+)?\s*(?:㎡|平米|平方米|m2|m²|万平|层|楼|间)", text, flags=re.IGNORECASE)
        )
        has_business_anchor = any(term in text for term in ("回本", "收回成本", "客单", "租金", "营业额", "成本"))
        has_project_anchor = has_space_hint or has_numeric_project_anchor or has_business_anchor
        has_design_domain = any(term in text for term in ("室内设计", "空间设计", "建筑", "规划", "软装", "动线", "材料", "灯光", "展陈", "设计概念"))
        if has_project_anchor and (has_project_intent or has_advice_intent or has_research_hint):
            return True
        return has_design_domain and (has_project_intent or has_advice_intent or has_research_hint)

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
        latent_model = self._latent_model_adapter.build(
            source_message=message,
            adapter_context=adapter_context,
        )
        adapter_context["latent_model"] = latent_model.model_dump(mode="json")
        if previous_context and previous_context.get("blueprint", {}).get("task_reframe"):
            adapter_context["previous_blueprint"] = previous_context["blueprint"]

        blueprint = self._build_blueprint(adapter_context)
        reply = self._render_reply(blueprint)
        insight_quality = self._insight_quality_evaluator.evaluate(
            source_message=message,
            semantic_package={},
            latent_model=adapter_context.get("latent_model") or {},
            blueprint=blueprint,
            visible_reply=reply,
        )
        blueprint["insight_quality"] = insight_quality
        blueprint["governance_signals"] = self._append_insight_quality_signal(
            blueprint.get("governance_signals") or [],
            insight_quality,
        )

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
        prompt = self._insight_protocol.build_prompt(adapter_context, rule_plan)
        try:
            response = self._llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            merged = self._insight_protocol.build_blueprint_from_response(
                rule_plan=rule_plan,
                content=str(content or ""),
            )
            if merged is None:
                return None
            return self._output_planner.clamp_existing_plan(merged)
        except Exception as exc:
            logger.warning(f"[DemandReconstruction] LLM insight failed, fallback used: {exc}")
            return None

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
            "summary": DemandReconstructionService._public_card_summary(plan),
            "sections": plan.get("sections") or [],
        }

    @staticmethod
    def _public_card_summary(plan: Dict[str, Any]) -> Dict[str, Any]:
        hidden_keys = {"insight_quality"}
        return {key: value for key, value in plan.items() if key not in hidden_keys}

    @staticmethod
    def _append_insight_quality_signal(signals: Any, insight_quality: Dict[str, Any]) -> list[Dict[str, Any]]:
        result = [signal for signal in (signals or []) if isinstance(signal, dict)]
        result.append(
            {
                "type": "insight_quality_watch",
                "level": insight_quality.get("level"),
                "score": insight_quality.get("score"),
                "missing_high_value_signals": insight_quality.get("missing_high_value_signals") or [],
                "warning_count": len(insight_quality.get("warning_issues") or []),
            }
        )
        return result

    @staticmethod
    def _public_adapter_context(adapter_context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "project_type": adapter_context.get("project_type"),
            "project_type_name": adapter_context.get("project_type_name"),
            "space_label": adapter_context.get("space_label"),
            "semantic_axes": adapter_context.get("semantic_axes"),
            "main_tensions": adapter_context.get("main_tensions"),
            "missing_slots": adapter_context.get("missing_slots"),
            "knowledge_coverage_ceiling": adapter_context.get("knowledge_coverage_ceiling"),
            "semantic_candidate_set": adapter_context.get("semantic_candidate_set"),
            "archetype": adapter_context.get("archetype"),
            "latent_model": adapter_context.get("latent_model"),
            "context_source": adapter_context.get("context_source"),
        }



