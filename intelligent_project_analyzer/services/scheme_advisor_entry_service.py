"""Feature-flagged entry flow for Scheme Advisor first two product steps.

This service implements the lightweight front-door defined in
sf/2026.5.23/6 and /7: two confidence-building inquiry rounds, a phase
conclusion, then three-tier version selection and directory preforming.
"""

from __future__ import annotations

import os
import re
import uuid
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml
from loguru import logger

from .scheme_advisor_context_intelligence import SchemeAdvisorContextIntelligence
from .scheme_advisor_public_labels import public_label
from .scheme_advisor_semantic_axes import (
    axis_label,
    derive_semantic_axes,
    has_concrete_project_anchor,
    has_input_intent,
    has_problem_mode,
    is_methodology_discussion_request,
    is_pure_naming_copy_request,
    is_reference_material_request,
    rank_main_tensions,
    semantic_axis_density,
)


ENTRY_STATE_KEY = "scheme_advisor_entry_v2"
ENV_FLAG = "SCHEME_ADVISOR_ENTRY_V2_ENABLED"
ENV_LLM_FLAG = "SCHEME_ADVISOR_ENTRY_V2_USE_LLM"

TEA_BUSINESS_TERMS = (
    "茶饮",
    "奶茶",
    "果茶",
    "柠檬茶",
    "原叶茶",
    "鲜奶",
    "饮品",
    "手作茶",
    "冰品",
    "茶馆",
    "霸王茶姬",
    "蜜雪冰城",
    "古茗",
)

TEA_OPERATION_TERMS = (
    "门头",
    "菜单",
    "点单",
    "出杯",
    "取餐",
    "外卖",
    "自提",
    "排队",
    "高峰",
    "顾客",
    "店员",
    "杯套",
    "杯盖",
    "吸管",
    "糖度",
    "冰量",
    "加料",
    "试饮",
    "复购",
    "小票",
    "包装",
    "垃圾桶",
    "空间转化率",
    "目光停留",
    "驻足",
    "进店",
    "下单",
    "吧台",
    "铺位",
    "商铺",
    "识别",
    "5秒",
    "店铺",
    "视觉焦点",
    "视平线",
    "产品",
    "入口产品",
    "标价",
    "首次必喝",
    "尝鲜杯",
    "门口",
    "公共通道",
    "地面材质",
    "信息牌",
    "今日特价",
    "隐藏菜单",
    "等待",
    "等候",
    "停留",
    "安抚",
    "拍照",
    "拍摄",
    "出品区",
    "后台",
    "表演",
    "站位",
    "腰靠",
    "搁板",
    "试运营",
    "杯身",
    "封口膜",
    "第一口",
    "隐藏喝法",
    "店内",
    "座位",
    "高脚凳",
    "离开",
    "送别语",
    "包装袋",
    "杯体",
    "广告位",
    "SKU",
    "座位",
    "面宽",
    "进深",
    "铺型",
    "营业额",
    "开业",
    "装修",
    "小红书",
    "打卡墙",
)

TEA_HARD_BOUNDARY_TERMS = (
    "上下水",
    "给排水",
    "电量",
    "排烟",
    "消防",
    "喷淋",
    "明火",
    "制冰机",
    "萃茶机",
    "开水机",
    "冰箱",
    "封口机",
    "设备",
    "物业",
    "平面",
)

WEAK_TEA_OPERATION_TERMS = {
    "座位",
    "装修",
    "风险",
    "方案",
    "品牌",
    "平面",
    "物业",
    "设备",
}

STRONG_TEA_SHOP_CONTEXT_TERMS = (
    "铺位",
    "商铺",
    "门店",
    "店铺",
    "吧台",
    "商场",
    "外卖",
    "面宽",
    "进深",
    "铺型",
    "营业额",
    "开业",
    "打卡墙",
    "标准图",
    "加盟",
)

STRONG_TEA_OPERATION_TERMS = tuple(
    term for term in set(TEA_OPERATION_TERMS) if term not in WEAK_TEA_OPERATION_TERMS
)


def is_scheme_advisor_entry_enabled() -> bool:
    return os.getenv(ENV_FLAG, "").strip().lower() in {"1", "true", "yes", "on"}


def is_scheme_advisor_entry_llm_enabled() -> bool:
    return os.getenv(ENV_LLM_FLAG, "").strip().lower() in {"1", "true", "yes", "on"}


class SchemeAdvisorEntryService:
    """Deterministic orchestration layer for the high-conversion entry flow."""

    def __init__(self, llm: Any = None) -> None:
        self._llm = llm
        self._tiers = self._load_tiers()
        self._entry_copy = self._load_entry_copy()
        self._context_intelligence = SchemeAdvisorContextIntelligence()

    def handle_message(
        self,
        *,
        session: Dict[str, Any],
        user_message: str,
        in_response_to_card_id: Optional[str],
        selected_option_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        state = dict(session.get(ENTRY_STATE_KEY) or {})
        pending_card = session.get("pending_guidance_card") or {}
        pending_type = pending_card.get("card_type")
        demand_reconstruction_handoff_context = session.get("demand_reconstruction_context") or {}
        has_demand_reconstruction_handoff = bool(demand_reconstruction_handoff_context.get("handoff_requested"))

        if not state and not self._should_enter_flow(user_message) and not has_demand_reconstruction_handoff:
            return None

        if state and not in_response_to_card_id and self._is_fresh_project_restart(user_message):
            logger.info("[SchemeAdvisorEntryV2] Fresh project brief detected, restarting entry flow")
            return self._start_flow(user_message)

        if not state:
            return self._start_flow(user_message, demand_reconstruction_context=demand_reconstruction_handoff_context or None)

        tier_ids = {t["id"] for t in self._tiers}
        if in_response_to_card_id and selected_option_id in tier_ids and state.get("step") == "version_selected":
            return self._select_version(state, selected_option_id)

        if in_response_to_card_id and pending_type == "scheme_round_1":
            return self._after_round_1(state, user_message)

        if in_response_to_card_id and pending_type == "scheme_round_2":
            return self._after_round_2(state, user_message)

        if in_response_to_card_id and pending_type == "scheme_stage_conclusion":
            if selected_option_id == "view_versions":
                return self._show_versions(state)
            return self._show_versions(state)

        if in_response_to_card_id and pending_type == "scheme_version_selection":
            return self._select_version(state, selected_option_id)

        # Once inside the entry flow, plain follow-up text is treated as extra
        # input for the current step instead of falling back into the old engine.
        step = state.get("step")
        if step == "round_1":
            return self._after_round_1(state, user_message)
        if step == "round_2":
            return self._after_round_2(state, user_message)
        if step == "stage_conclusion":
            return self._show_versions(state)
        if step == "version_selection":
            return self._select_version(state, selected_option_id)
        if step == "version_selected":
            return self._after_version_selected_followup(state, user_message)
        if state:
            logger.warning(
                f"[SchemeAdvisorEntryV2] Unknown step, handled by entry fallback: step={step}"
            )
            return self._after_version_selected_followup(state, user_message)
        return None

    def _start_flow(self, message: str, demand_reconstruction_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        profile = self._classify_input(message)
        if profile["mode"] == "redirect":
            reply = self._copy_text("first_confidence.redirect")
            card = self._round_1_card(
                "把问题落到项目",
                "先补 3 个方向级变量，我就能判断它是否适合进入任务书生成。",
                [
                    ("project_type", "项目类型", "例如茶饮、餐饮、办公、民宿、住宅改造"),
                    ("site_condition", "场地条件", "面积、城市、楼层、是否已有图纸或现场限制"),
                    ("failure_point", "最不能失败点", "例如回本、形象、动线、审批、工期"),
                ],
            )
        elif profile["mode"] == "methodology":
            reply = self._build_methodology_first_confidence(profile, message)
            card = self._methodology_round_1_card()
        else:
            reply = self._build_first_confidence_fallback(profile, message)
            card = self._round_1_card_for_profile(profile)

        reply = self._generate_reply(
            stage="first_confidence",
            fallback=reply,
            user_message=message,
            state={"profile": profile},
            instruction=(
                "生成首轮信心响应。要求：120-220字，3段以内；先直入人心，再直击本质，"
                "最后引导进入第一轮追问。不要要求上传CAD，不要提前报价，不要输出目录，"
                "不要在正文里额外提出具体问题。"
            ),
        )

        if demand_reconstruction_context:
            card = self._apply_demand_reconstruction_handoff_to_round_1_card(card, demand_reconstruction_context)

        return self._result(
            reply,
            card,
            {
                "step": "round_1",
                "initial_input": message,
                "profile": profile,
                "demand_reconstruction_handoff": demand_reconstruction_context,
                "rounds": [],
                "created_at": datetime.now().isoformat(),
            },
        )

    @staticmethod
    def _apply_demand_reconstruction_handoff_to_round_1_card(
        card: Dict[str, Any],
        demand_reconstruction_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Mark formal intake as inheriting the demand reconstruction blueprint."""
        slots = dict(demand_reconstruction_context.get("brief_handoff_slots") or {})
        if not slots:
            return card
        inherited_labels = [
            label
            for key, label in (
                ("project_object", "项目对象"),
                ("owner_profile", "业主画像"),
                ("emotional_motive", "目标动机"),
                ("risk_boundary", "风险边界"),
                ("core_proposition_candidate", "核心命题"),
            )
            if slots.get(key)
        ]
        card = dict(card)
        prefix = "已继承需求重构行动蓝图"
        if inherited_labels:
            prefix = f"{prefix}：{'、'.join(inherited_labels)}"
        card["prompt_text"] = f"{prefix}。这一轮只补正式任务书还缺的边界。{card.get('prompt_text', '')}"
        card["demand_reconstruction_handoff_slots"] = slots
        return card

    def _after_round_1(self, state: Dict[str, Any], message: str) -> Dict[str, Any]:
        state = self._append_round(state, "round_1", message)
        profile = state.get("profile") or {}
        if self._is_beverage_entry_profile(profile):
            reply = (
                "基于你刚才的补充，这家店的主轴已经更清楚：现在不是继续补工程条件，"
                "而是把回本打法、最怕失败的点和建议深度定下来。\n\n"
                "下一轮只问三个决策问题：这家店靠什么打法成立、最不能接受哪类失败、"
                "这次建议需要服务到哪一层。问完就进入阶段判断和版本选择。"
            )
        else:
            reply = self._build_second_confidence_fallback(state, message)
        reply = self._generate_reply(
            stage="second_confidence",
            fallback=reply,
            user_message=message,
            state=state,
            instruction=(
                "生成二次信心强化。要求：100-180字；基于第一轮回答给阶段性判断，"
                "指出一个更深的成败杠杆，然后引导第二轮决策级追问。不要展开完整方案。"
            ),
        )
        if self._is_beverage_entry_profile(profile):
            reply = (
                "基于你刚才的补充，这家店的主轴已经更清楚：现在不是继续补工程条件，"
                "而是把回本打法、最怕失败的点和建议深度定下来。\n\n"
                "下一轮只问三个决策问题：这家店靠什么打法成立、最不能接受哪类失败、"
                "这次建议需要服务到哪一层。问完就进入阶段判断和版本选择。"
            )
        card = self._round_2_card_for_profile(profile)
        return self._result(reply, card, {**state, "step": "round_2"})

    def _round_2_card_for_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        if self._is_beverage_entry_profile(profile):
            return self._beverage_round_2_card(profile)

        planned = ((profile.get("question_plan") or {}).get("round_2_card") or {})
        if planned.get("pages"):
            return self._planned_card(planned, "scheme-r2", "scheme_round_2")

        return {
            "card_id": f"scheme-r2-{uuid.uuid4().hex[:8]}",
            "card_type": "scheme_round_2",
            "title": "再确认关键选择",
            "prompt_text": "第二轮只确认最关键的取舍、风险和优先级，问完就进入阶段结论与三档选择。",
            "options": [],
            "allow_freetext": True,
            "pages": [
                {
                    "page_title": "优先级",
                    "prompt_text": "在速度、成本、体验三项里，哪两项必须优先保障？",
                    "options": [
                        {"id": "speed_cost", "label": "速度+成本", "description": "先保开业速度与投入控制"},
                        {"id": "speed_experience", "label": "速度+体验", "description": "先保快速落地与到店转化"},
                        {"id": "cost_experience", "label": "成本+体验", "description": "先保预算效率与用户感知"},
                    ],
                    "allow_freetext": True,
                },
                {
                    "page_title": "投入优先级",
                    "prompt_text": "如果只能把预算集中到一个环节，你希望优先保障哪里？",
                    "options": [
                        {"id": "facade", "label": "门头界面", "description": "优先解决识别、进店和第一眼转化"},
                        {"id": "bar", "label": "吧台出品", "description": "优先解决效率、排队与现场信任"},
                        {"id": "equipment", "label": "设备后场", "description": "优先解决稳定出品和运营强度"},
                    ],
                    "allow_freetext": True,
                },
                {
                    "page_title": "最不能接受的风险",
                    "prompt_text": "出现什么情况时，你会认为当前方向必须立刻调整？",
                    "options": [
                        {"id": "over_budget", "label": "超预算", "description": "投入超过可承受上限"},
                        {"id": "slow_opening", "label": "开业延误", "description": "工期影响租金消耗与回本节奏"},
                        {"id": "low_conversion", "label": "转化不足", "description": "门店识别、排队或购买动线不成立"},
                    ],
                    "allow_freetext": True,
                },
            ],
        }

    def _after_round_2(self, state: Dict[str, Any], message: str) -> Dict[str, Any]:
        state = self._append_round(state, "round_2", message)
        profile = state.get("profile") or {}
        recommended = self._recommend_version(state)
        state["recommended_version"] = recommended
        reply = self._build_stage_conclusion_fallback(state, message, recommended)
        reply = self._generate_reply(
            stage="stage_conclusion",
            fallback=reply,
            user_message=message,
            state={**state, "recommended_version": recommended},
            instruction=(
                "生成第二轮后的阶段结论。要求：130-220字；明确说明已满足目录预成型条件，"
                "把空间分类、本体对象、经营路径、回本约束串起来；提醒CAD等资料进入正式阶段校准。"
            ),
        )
        card = {
            "card_id": f"scheme-stage-{uuid.uuid4().hex[:8]}",
            "card_type": "scheme_stage_conclusion",
            "title": "阶段结论",
            "prompt_text": "已完成入口判断。下一步查看三档版本与目录预成型。",
            "options": [
                {
                    "id": "view_versions",
                    "label": "查看三档版本",
                    "description": "展示基础版、标准版、高级版三档选择",
                    "recommended": True,
                }
            ],
            "allow_freetext": False,
            "summary": {
                "space_classification": self._display_space_label(profile),
                "ontology_focus": self._summary_ontology_focus(profile),
                "knowledge_modules": self._summary_knowledge_modules(profile),
                "pending_formal_assets": (profile.get("maturity") or {}).get("pending")
                or ["CAD 平面图", "现场照片", "品牌资料", "设备清单", "预算明细"],
            },
        }
        return self._result(reply, card, {**state, "step": "stage_conclusion"})

    def _show_versions(self, state: Dict[str, Any]) -> Dict[str, Any]:
        recommended = state.get("recommended_version") or self._recommend_version(state)
        reply = self._build_version_intro_fallback(state, recommended)
        reply = self._generate_reply(
            stage="version_selection",
            fallback=reply,
            user_message="查看三档版本",
            state={**state, "recommended_version": recommended, "tiers": self._tiers},
            instruction=(
                "生成三档版本选择前的说明。要求：80-150字；说明推荐逻辑不是推高版本，"
                "而是匹配决策压力；引导用户选择基础版、标准版或高级版。"
            ),
        )
        card = {
            "card_id": f"scheme-version-{uuid.uuid4().hex[:8]}",
            "card_type": "scheme_version_selection",
            "title": "选择任务书版本",
            "prompt_text": self._build_version_prompt_text(state),
            "options": [
                {
                    "id": tier["id"],
                    "label": tier["name"],
                    "description": tier["subtitle"],
                    "recommended": tier["id"] == recommended,
                }
                for tier in self._tiers
            ],
            "allow_freetext": False,
            "version_cards": self._tiers,
            "recommended_version": recommended,
            "maturity_note": "当前为入口阶段预成型目录，正式开始后再用 CAD、现场与品牌资料校准。",
        }
        return self._result(reply, card, {**state, "step": "version_selection"})

    def _select_version(self, state: Dict[str, Any], selected_option_id: Optional[str]) -> Dict[str, Any]:
        selected = selected_option_id if selected_option_id in {t["id"] for t in self._tiers} else state.get("recommended_version", "standard")
        tier = next((t for t in self._tiers if t["id"] == selected), self._tiers[1])
        reply = (
            f"已记录选择：{tier['name']}。下一阶段会基于这一档进入正式任务书工作，"
            "再校准 CAD、现场照片、品牌资料、设备清单和预算边界。"
            "当前不会在入口阶段继续追问，避免把正式工作前置成问卷。"
        )
        reply = self._generate_reply(
            stage="version_selected",
            fallback=reply,
            user_message=f"用户选择了{tier['name']}",
            state={**state, "selected_version": selected},
            instruction=(
                "生成版本选择后的确认回复。要求：60-120字；确认选择，说明下一阶段会校准正式资料，"
                "不要继续追问，不要要求立即付款。"
            ),
        )
        revision_count = int(state.get("version_selection_revision_count") or 0)
        state = {
            **state,
            "step": "version_selected",
            "selected_version": selected,
            "version_selection_revision_count": revision_count + 1,
            "version_selected_at": datetime.now().isoformat(),
        }
        return self._result(reply, None, state)

    def _after_version_selected_followup(self, state: Dict[str, Any], message: str) -> Dict[str, Any]:
        selected = state.get("selected_version") or state.get("recommended_version") or "standard"
        tier = next((t for t in self._tiers if t["id"] == selected), self._tiers[1])
        reply = (
            f"已在入口阶段记录为{tier['name']}。你刚补充的信息我会作为正式任务书阶段的校准素材处理，"
            "不会再退回漫聊或旧问卷链路。下一步应进入资料校准：CAD、现场照片、品牌资料、设备清单和预算边界。"
        )
        reply = self._generate_reply(
            stage="post_version_followup",
            fallback=reply,
            user_message=message,
            state={**state, "selected_version": selected},
            instruction=(
                "生成版本已选择后的继续输入回复。要求：70-130字；承接用户补充的信息，"
                "明确已进入正式任务书前的资料校准阶段；不要重新开始问诊，不要让用户现在上传CAD，"
                "不要落回普通聊天。"
            ),
        )
        next_state = self._append_round(state, "post_version_followup", message)
        next_state = {**next_state, "step": "version_selected", "selected_version": selected}
        return self._result(reply, None, next_state)

    def _build_second_confidence_fallback(self, state: Dict[str, Any], message: str) -> str:
        profile = state.get("profile") or {}
        space_label = profile.get("space_label") or "这个项目"
        focus = self._focus_phrase(profile)
        state_text = self._state_text(state, message)
        context_sentence = self._semantic_context_sentence(derive_semantic_axes(state_text), state_text)
        if context_sentence:
            context_sentence = f"{context_sentence}"
        else:
            context_sentence = f"现在要把{focus}转成可判断的现场条件。"
        return (
            f"基于你刚才的补充，{space_label}的主轴已经更清楚：当前不是继续补背景，"
            f"{context_sentence}下一轮只确认最不能牺牲什么、哪些风险必须提前避开，"
            "问完就进入入口阶段判断与版本选择。"
        )

    def _build_stage_conclusion_fallback(
        self,
        state: Dict[str, Any],
        message: str,
        recommended: str,
    ) -> str:
        profile = state.get("profile") or {}
        if self._is_beverage_entry_profile(profile):
            configured = self._render_configured_beverage_template(
                "stage_conclusion_selection_rules",
                "tea_retail_space.stage_conclusion_template",
                state,
                message,
                recommended,
            )
            if configured:
                return configured
        configured = self._render_configured_generic_template(
            "stage_conclusion_selection_rules",
            "generic_project.stage_conclusion",
            state,
            message,
            recommended,
        )
        if configured:
            return configured
        space_label = self._display_space_label(profile)
        focus = self._focus_phrase(profile)
        tier_name = self._tier_name(recommended)
        state_text = self._state_text(state, message)
        context_sentence = self._semantic_context_sentence(derive_semantic_axes(state_text), state_text)
        if context_sentence:
            decision_sentence = context_sentence
        else:
            decision_sentence = f"我会按{space_label}处理，把{focus}放进同一份任务书目录里。"
        pending = "、".join((profile.get("maturity") or {}).get("pending") or ["CAD/平面图", "现场照片", "品牌资料"])
        return (
            "现在可以收束，不需要继续问卷化。初始输入加两轮回答，已经足够形成入口阶段判断："
            f"{decision_sentence}\n\n"
            f"当前更适合用{tier_name}承接。{pending}不是入口阶段卡住你的理由，"
            "而是正式任务书阶段校准平面、边界和落地深度的依据。"
        )

    def _build_version_intro_fallback(self, state: Dict[str, Any], recommended: str) -> str:
        profile = state.get("profile") or {}
        if self._is_beverage_entry_profile(profile):
            configured = self._render_configured_beverage_template(
                "version_intro_selection_rules",
                "tea_retail_space.version_intro_template",
                state,
                "",
                recommended,
            )
            if configured:
                return configured
        configured = self._render_configured_generic_template(
            "version_intro_selection_rules",
            "generic_project.version_intro",
            state,
            "",
            recommended,
        )
        if configured:
            return configured
        space_label = self._display_space_label(profile)
        reasons = ((profile.get("version_score") or {}).get("reasons") or [])[:3]
        reason_text = (
            "、".join(self._humanize_version_reason(reason, profile) for reason in reasons)
            if reasons
            else "当前项目的决策压力"
        )
        return (
            f"下面不是单纯买文档，而是在选择这份{space_label}任务书要做到多深。"
            f"当前推荐{self._tier_name(recommended)}，依据是{reason_text}；"
            "你仍可以根据预算、协作强度和正式交付需求改选。"
        )

    def _build_version_prompt_text(self, state: Dict[str, Any]) -> str:
        return self._copy_text("generic_project.version_prompt_text")

    def _state_text(self, state: Dict[str, Any], extra: str = "") -> str:
        parts = [state.get("initial_input", "")]
        parts.extend(str(r.get("content", "")) for r in state.get("rounds", []))
        if extra:
            parts.append(extra)
        return "；".join(part for part in parts if part)

    def _round_1_card(self, title: str, prompt: str, fields: List[tuple[str, str, str]]) -> Dict[str, Any]:
        return {
            "card_id": f"scheme-r1-{uuid.uuid4().hex[:8]}",
            "card_type": "scheme_round_1",
            "title": title,
            "prompt_text": prompt,
            "options": [],
            "allow_freetext": True,
            "pages": [
                {
                    "page_title": label,
                    "prompt_text": desc,
                    "options": [
                        {"id": f"{field}_known", "label": "已明确", "description": "我可以直接补充具体信息"},
                        {"id": f"{field}_range", "label": "有范围", "description": "目前只有大致判断"},
                        {"id": f"{field}_unknown", "label": "待确认", "description": "先按假设进入下一步"},
                    ],
                    "allow_freetext": True,
                }
                for field, label, desc in fields
            ],
        }

    def _round_1_card_for_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        if self._is_beverage_entry_profile(profile):
            return self._beverage_round_1_card(profile)

        configured = self._generic_round_1_card(profile)
        if configured:
            return configured

        planned = ((profile.get("question_plan") or {}).get("round_1_card") or {})
        if planned.get("pages"):
            return self._planned_card(planned, "scheme-r1", "scheme_round_1")

        return self._round_1_card(
            "先锁定方向级变量",
            "第一轮只问会改变目录和报价口径的关键变量。",
            [
                ("failure_point", "最不能失败点", "回本、坪效、品牌形象、施工速度里哪个不能失守"),
                ("customer", "目标客群", "通勤客、商场客、办公客、外卖客的主次关系"),
                ("investment", "投入边界", "硬装、设备、招牌、软装与开业投入的大致上限"),
            ],
        )

    def _build_first_confidence_fallback(self, profile: Dict[str, Any], message: str = "") -> str:
        space_label = profile.get("space_label") or "这个项目"
        focus = self._focus_phrase(profile)
        if self._is_beverage_entry_profile(profile):
            return self._build_beverage_first_confidence(profile)
        configured = self._render_configured_generic_template(
            "first_confidence_selection_rules",
            "",
            {"profile": profile, "initial_input": message, "rounds": []},
            message,
            "standard",
        )
        if configured:
            return configured
        semantic_reply = self._build_semantic_first_confidence(profile, message)
        if semantic_reply:
            return semantic_reply
        conditions = (
            ((profile.get("context_packet") or {}).get("classification") or {}).get("project_conditions")
            or (profile.get("classification") or {}).get("contextual_project_conditions")
            or []
        )
        is_transit = "transit_connection" in conditions
        has_payback = "payback_pressure" in conditions
        opening = f"这更像是一个小面积高周转的{space_label}，不能先从风格入手。"
        if is_transit and has_payback:
            opening = (
                f"这更像是一个地铁连接口的小面积高周转{space_label}，"
                "半年回本会把设计重点从“好看”推向“截流、出杯、排队和投入上限”。"
            )
        elif is_transit:
            opening = f"这更像是一个交通节点型{space_label}，门头截流、导视和排队外溢会先于风格成立。"
        elif has_payback:
            opening = f"这更像是一个带明确回本压力的{space_label}，需要先校准投入、坪效和出杯效率。"

        return (
            f"{opening}\n\n"
            "初步框架可以先按五条线展开：第一，门头与地铁客流的瞬时识别；"
            "第二，点单、制作、取餐和外卖自提的动线拆分；第三，后场设备、给排水、排烟、电力和消防边界；"
            "第四，低成本但有记忆点的材料与灯光体系；第五，用租金、客单价、日单量和装修设备投入反推半年回本是否成立。\n\n"
            f"下一步应优先确认{focus}，确认后再把它收敛成完整设计建议，而不是在入口阶段直接要求 CAD。"
        )

    @staticmethod
    def _build_semantic_first_confidence(profile: Dict[str, Any], message: str) -> str:
        axes = derive_semantic_axes(message)
        domains = set(axes.get("space_domains") or [])
        intents = set(axes.get("input_intents") or [])
        main_tensions = rank_main_tensions(message, limit=3)
        space_label = profile.get("space_label") or profile.get("project_type_name") or "这个项目"
        project_type = str(profile.get("project_type") or "")
        space_axis = profile.get("space_axis") or (profile.get("classification") or {}).get("space_axis") or {}
        space_axis_id = str(space_axis.get("primary_axis_id") or "")
        is_hospitality = (
            project_type in {"commercial_hospitality"}
            or space_axis_id.startswith("hospitality")
            or "hospitality" in domains
        )
        is_technical = (
            project_type in {"special_function"}
            or space_axis_id in {
                "technical_performance_environment",
                "mission_critical_resilience",
                "climate_resilience_construction",
            }
            or "technical_special" in domains
        )
        is_healthcare = (
            project_type in {"healthcare_wellness"}
            or "healthcare_wellness" in domains
        )
        is_workplace = (
            project_type in {"commercial_office", "commercial_enterprise"}
            or "workplace" in domains
        )
        is_cultural = (
            project_type in {"public_cultural", "brand_experience"}
            or "cultural_exhibition" in domains
        )
        is_urban_renewal = (
            project_type in {"urban_renewal_heritage", "urban_renewal_market"}
            or "urban_renewal" in domains
        )
        is_public_market = "public_market" in domains
        is_retail = (
            project_type in {"commercial_retail", "commercial_dining"}
            or "retail_commercial" in domains
        )
        is_residential = (
            project_type in {"personal_residential", "residential_renovation", "hybrid_residential_commercial"}
            or "residential" in domains
        )

        if "methodology" in intents and not domains:
            opening = "这更像是一个空间方法论问题，重点不是套某个项目模板，而是先把可迁移的判断框架搭起来。"
        elif is_technical:
            opening = f"这更像是一个{space_label}问题，设备性能、声学、光热和环境控制会先于风格表达成立。"
        elif is_hospitality:
            opening = f"这更像是一个{space_label}的住宿体验与运营模型共同成立的问题，不能只谈氛围感。"
        elif is_healthcare:
            opening = f"这更像是一个健康照护与情绪安全问题，专业边界会先于视觉表达成立。"
        elif is_workplace:
            opening = f"这更像是一个组织效率与品牌气质共同塑造的问题，不能只做漂亮办公室。"
        elif is_cultural:
            opening = f"这更像是一个叙事、展陈与公众理解路径的问题，不能只堆文化符号。"
        elif is_public_market:
            opening = f"这更像是一个公共市场更新问题，不能先套网红菜市场模板，也不能只做文化包装。"
        elif is_urban_renewal:
            opening = f"这更像是一个更新再生问题，必须同时看原有场地、使用者和后续运营。"
        elif is_retail:
            opening = f"这更像是一个商业体验与转化效率问题，需要先判断顾客为什么进入、停留和购买。"
        elif is_residential:
            opening = f"这更像是一个居住关系与生活秩序问题，不能只从风格或效果图理解{space_label}。"
        else:
            opening = f"这更像是一个复合空间判断题，第一步不是给答案，而是先抓住项目成立的主轴。"

        tension_labels = [
            str(item.get("label") or item.get("title"))
            for item in main_tensions
            if item.get("label") or item.get("title")
        ][:3]
        if tension_labels:
            middle = "当前最值得先锁定的是：" + "、".join(tension_labels) + "。这些会影响第一版建议先判断什么、哪些条件暂时不能下死结论。"
        else:
            middle = "当前最值得先锁定的是：项目目标、核心使用者、现实边界和最不能跑偏的判断。"
        subject_sentence = SchemeAdvisorEntryService._semantic_subject_sentence(axes)
        if subject_sentence:
            middle = f"{middle}{subject_sentence}"
        context_sentence = SchemeAdvisorEntryService._semantic_context_sentence(axes, message)
        if context_sentence:
            middle = f"{middle}{context_sentence}"
        prompt_anchor_sentence = SchemeAdvisorEntryService._semantic_prompt_anchor_sentence(axes, message)
        if prompt_anchor_sentence:
            middle = f"{middle}{prompt_anchor_sentence}"

        next_focus = "、".join(tension_labels[:2])
        if not next_focus:
            next_focus = "最不能跑偏的判断"

        return (
            f"{opening}\n\n"
            f"{middle}\n\n"
            f"下一步先围绕{next_focus}补齐判断，确认后再进入完整设计建议，不在入口阶段把不确定条件包装成确定结论。"
        )

    @staticmethod
    def _semantic_subject_sentence(axes: Dict[str, Any]) -> str:
        subject_ids = [str(item) for item in axes.get("subject_profiles") or [] if item]
        if not subject_ids:
            return ""
        labels = [axis_label(item) for item in subject_ids[:3]]
        labels = [label for label in labels if label and label != "关键判断"]
        if not labels:
            return ""
        return " 题目里的关键人物不是背景：" + "、".join(labels) + "会影响空间权力、叙事分寸和日常使用方式。"

    @staticmethod
    def _semantic_context_sentence(axes: Dict[str, Any], message: str) -> str:
        founding = set(axes.get("founding_drivers") or [])
        site_resources = set(axes.get("site_resources") or [])
        constraints = set(axes.get("critical_constraints") or [])
        text = str(message or "")
        details: List[str] = []

        if "business_roi" in founding and "operational_efficiency" in founding:
            payback_word = "半年回本" if ("半年" in text or re.search(r"6\s*个?月", text)) else "回本"
            if "transit_node" in site_resources:
                details.append(
                    f"地铁/交通节点带来的是瞬时客流，不等于自然成交；高租金、{payback_word}和快周转要一起算，设计先要证明截流、转化、动线和周转效率成立"
                )
            else:
                details.append(
                    f"{payback_word}压力会把设计重点推向投入上限、成交转化和运营效率，而不是单纯做氛围"
                )
        elif "business_roi" in founding:
            details.append("商业回报不能只看形象，需要先把投入上限、客流来源和成交路径讲清楚")
        elif "operational_efficiency" in founding:
            details.append("运营效率会直接决定动线、排队、服务半径和后台配置")

        if "budget" in constraints and "business_roi" not in founding:
            details.append("预算或成本边界会限制材料、设备和阶段深度，不能先按理想状态展开")

        if not details:
            return ""
        return "；".join(details[:2]) + "。"

    @staticmethod
    def _semantic_prompt_anchor_sentence(axes: Dict[str, Any], message: str) -> str:
        domains = set(axes.get("space_domains") or [])
        anchors = SchemeAdvisorContextIntelligence.prompt_anchors(message)
        benchmark = anchors.get("benchmark")
        culture = anchors.get("culture")
        stakeholders = anchors.get("stakeholders")
        motive = anchors.get("motive")
        text = str(message or "")
        details: List[str] = []

        if "public_market" in domains and benchmark:
            location = "深圳蛇口" if "深圳" in text and "蛇口" in text else ""
            location_prefix = f"{location}和" if location else ""
            details.append(
                f"对标{benchmark}要先拆哪些可迁移，{location_prefix}{benchmark}的城市语境、客群结构和运营后勤不一样，不能照搬"
            )
        elif benchmark:
            details.append(f"对标{benchmark}要先拆可迁移原则和不可照搬的边界")

        if culture:
            details.append(f"{culture}需要专题转译为空间秩序、展示节奏和日常使用线索，而不是做表皮符号")
        if stakeholders:
            details.append(f"题目明确要兼顾{stakeholders}，这会直接改变动线、停留、消费和公共性分配")
        if motive:
            details.append(f"最终目标是成为{motive}，需要重新梳理它到底靠民生运营、公共体验还是城市传播成立")

        if not details:
            return ""
        return "；".join(details[:4]) + "。"

    @staticmethod
    def _build_methodology_first_confidence(profile: Dict[str, Any], message: str) -> str:
        axes = profile.get("semantic_axes") or derive_semantic_axes(message)
        modes = set(axes.get("problem_modes") or [])
        main_tensions = rank_main_tensions(message, limit=3)
        tension_labels = [
            str(item.get("label") or item.get("title"))
            for item in main_tensions
            if item.get("label") or item.get("title")
        ][:3]
        focus_text = "、".join(tension_labels) if tension_labels else "方法主轴、适用边界和落地验证"

        if "analogy_translation" in modes:
            opening = "这更像是一个方法转译问题，可以讨论，但不能把外部体系直接套进空间设计。"
            middle = "关键是先拆出可迁移原则，再转成住宅或其他空间里的访谈、材料、符号和交付流程。"
        elif "value_argument" in modes:
            opening = "这更像是一个设计价值论证问题，可以讨论，但不能把成本增加包装成一句好听的概念。"
            middle = "关键是把材料替换、成本边界、长期维护、品牌价值和可持续证据链讲清楚。"
        else:
            opening = "这更像是一个空间方法论问题，可以先搭建可迁移框架，而不是要求你立刻给出具体项目。"
            middle = "关键是把抽象观点转成空间判断、适用边界和验证路径，避免停留在概念口号。"

        return (
            f"{opening}\n\n"
            f"当前最值得先锁定的是：{focus_text}。{middle}\n\n"
            "下一步先确认方法主轴、适用边界和落地验证，再决定是否升级为具体项目任务书。"
        )

    @staticmethod
    def _methodology_round_1_card() -> Dict[str, Any]:
        return {
            "card_id": f"scheme-method-{uuid.uuid4().hex[:8]}",
            "card_type": "scheme_round_1",
            "title": "先把方法论说清楚",
            "prompt_text": "这类问题先确认方法主轴、适用边界和验证方式，不急着伪装成具体项目。",
            "options": [],
            "allow_freetext": True,
            "pages": [
                {
                    "page_title": "方法主轴",
                    "prompt_text": "这套方法最想解决哪类空间判断？",
                    "options": [
                        {"id": "concept_structure", "label": "概念结构", "description": "优先解释概念如何形成空间秩序"},
                        {"id": "process_method", "label": "流程方法", "description": "优先解释访谈、判断和交付流程"},
                        {"id": "value_translation", "label": "价值转译", "description": "优先解释文化、品牌或外部体系如何被转成空间"},
                    ],
                    "allow_freetext": True,
                },
                {
                    "page_title": "适用边界",
                    "prompt_text": "这套方法适合哪些场景，不适合哪些场景？",
                    "options": [
                        {"id": "space_scope", "label": "空间范围", "description": "明确住宅、商业、展陈或公共空间的适用边界"},
                        {"id": "user_scope", "label": "使用者范围", "description": "明确服务对象和关系复杂度"},
                        {"id": "risk_scope", "label": "风险边界", "description": "明确哪些条件下不能直接套用"},
                    ],
                    "allow_freetext": True,
                },
                {
                    "page_title": "落地验证",
                    "prompt_text": "这套方法最后靠什么证明有效？",
                    "options": [
                        {"id": "design_output", "label": "设计输出", "description": "看能否产出清晰目录、策略和表达原则"},
                        {"id": "user_feedback", "label": "用户反馈", "description": "看使用者是否理解并认可空间逻辑"},
                        {"id": "project_reuse", "label": "项目复用", "description": "看能否迁移到不同项目而不变形"},
                    ],
                    "allow_freetext": True,
                },
            ],
        }

    def _build_beverage_first_confidence(self, profile: Dict[str, Any]) -> str:
        variant = self._beverage_first_confidence_variant(profile)
        configured = self._copy_text(f"tea_retail_space.first_confidence_variants.{variant}")
        if configured:
            return configured
        return self._copy_text("first_confidence.tea_retail_space")

    def _beverage_first_confidence_variant(self, profile: Dict[str, Any]) -> str:
        configured_variant = self._configured_beverage_first_confidence_variant(profile)
        if configured_variant:
            return configured_variant
        return "default"

    def _configured_beverage_first_confidence_variant(
        self, profile: Dict[str, Any]
    ) -> Optional[str]:
        rules = (
            self._entry_copy.get("tea_retail_space", {}).get(
                "first_confidence_variant_rules"
            )
            or []
        )
        default_variant: Optional[str] = None

        for rule in rules:
            if not isinstance(rule, dict):
                continue
            variant = str(rule.get("variant") or "").strip()
            if not variant:
                continue
            if rule.get("default"):
                default_variant = default_variant or variant
                continue
            if self._profile_rule_matches(profile, rule.get("when") or {}):
                return variant

        return default_variant

    def _profile_rule_matches(
        self, profile: Dict[str, Any], conditions: Dict[str, Any]
    ) -> bool:
        if not conditions:
            return False

        tags = {str(tag) for tag in (profile.get("entry_scene_tags") or [])}

        tags_all = [str(tag) for tag in (conditions.get("tags_all") or [])]
        if tags_all and not all(tag in tags for tag in tags_all):
            return False

        tags_any = [str(tag) for tag in (conditions.get("tags_any") or [])]
        if tags_any and not any(tag in tags for tag in tags_any):
            return False

        profile_equals = conditions.get("profile_equals") or {}
        for field, expected_values in profile_equals.items():
            expected = {str(value) for value in (expected_values or [])}
            if str(self._profile_rule_value(profile, str(field)) or "") not in expected:
                return False

        profile_contains = conditions.get("profile_contains") or {}
        for field, expected_tokens in profile_contains.items():
            value = str(self._profile_rule_value(profile, str(field)) or "").lower()
            tokens = [str(token).lower() for token in (expected_tokens or [])]
            if tokens and not any(token in value for token in tokens):
                return False

        profile_contains_any = conditions.get("profile_contains_any") or {}
        if profile_contains_any:
            matched_any_field = False
            for field, expected_tokens in profile_contains_any.items():
                value = str(self._profile_rule_value(profile, str(field)) or "").lower()
                tokens = [str(token).lower() for token in (expected_tokens or [])]
                if tokens and any(token in value for token in tokens):
                    matched_any_field = True
                    break
            if not matched_any_field:
                return False

        return True

    @staticmethod
    def _profile_rule_value(profile: Dict[str, Any], field: str) -> Any:
        if field in profile:
            return profile.get(field)

        current: Any = profile
        if "." in field:
            for part in field.split("."):
                if not isinstance(current, dict):
                    return ""
                current = current.get(part)
            return current

        classification = profile.get("classification") or {}
        space_axis = profile.get("space_axis") or classification.get("space_axis") or {}

        if field == "project_type":
            return profile.get("project_type") or classification.get("project_type")
        if field == "space_axis_id":
            return (
                profile.get("space_axis_id")
                or space_axis.get("primary_axis_id")
                or (profile.get("intelligence_trace") or {}).get("space_axis_id")
            )
        if field == "space_axis_label":
            return profile.get("space_axis_label") or space_axis.get("label")

        return ""

    @staticmethod
    def _is_beverage_entry_profile(profile: Dict[str, Any]) -> bool:
        markers = {
            str(profile.get("subdomain_id") or ""),
            str(profile.get("activation_pack_id") or ""),
            str(profile.get("project_type") or ""),
        }
        text = " ".join(markers).lower()
        return any(
            marker in text
            for marker in (
                "tea_drink_store",
                "tea_drink_store_pack",
                "coffee_shop",
                "coffee_shop_pack",
            )
        )

    def _beverage_round_1_card(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        card_path = self._configured_beverage_round_1_card_path(profile)
        if card_path:
            configured = self._configured_card(card_path, "scheme-r1", "scheme_round_1")
            if configured:
                return configured
        return self._configured_card(
            "tea_retail_space.contextual_round_1_cards.default",
            "scheme-r1",
            "scheme_round_1",
        ) or self._planned_card({}, "scheme-r1", "scheme_round_1")

    def _generic_round_1_card(self, profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        card_path = self._configured_card_path(
            "generic_project",
            profile,
            "round_1_card_selection_rules",
            "",
        )
        if not card_path:
            return None
        return self._configured_card(card_path, "scheme-r1", "scheme_round_1")

    def _configured_beverage_round_1_card_path(
        self, profile: Dict[str, Any]
    ) -> Optional[str]:
        return self._configured_card_path(
            "tea_retail_space",
            profile,
            "round_1_card_selection_rules",
            "",
        )

    def _beverage_round_2_card(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        card_path = self._configured_beverage_round_2_card_path(profile)
        if card_path:
            configured = self._configured_card(card_path, "scheme-r2", "scheme_round_2")
            if configured:
                return configured
        configured = self._configured_card(
            "tea_retail_space.round_2_card",
            "scheme-r2",
            "scheme_round_2",
        )
        if configured:
            return configured
        planned = ((profile.get("question_plan") or {}).get("round_2_card") or {})
        return self._planned_card(planned, "scheme-r2", "scheme_round_2")

    def _configured_beverage_round_2_card_path(
        self, profile: Dict[str, Any]
    ) -> Optional[str]:
        return self._configured_card_path(
            "tea_retail_space",
            profile,
            "round_2_card_selection_rules",
            "",
        )

    def _render_configured_beverage_template(
        self,
        rule_key: str,
        default_template_path: str,
        state: Dict[str, Any],
        message: str,
        recommended: str,
    ) -> str:
        profile = state.get("profile") or {}
        template_path = self._configured_beverage_template_path(
            profile,
            rule_key,
            default_template_path,
        )
        template = self._copy_text(template_path)
        if not template:
            return ""

        values = self._beverage_template_values(state, message, recommended)
        try:
            return template.format(**values)
        except KeyError as exc:
            logger.warning(
                f"[SchemeAdvisorEntryV2] beverage template missing variable: "
                f"path={template_path}, variable={exc}"
            )
            return ""

    def _configured_beverage_template_path(
        self,
        profile: Dict[str, Any],
        rule_key: str,
        default_template_path: str,
    ) -> str:
        rules = self._entry_copy.get("tea_retail_space", {}).get(rule_key) or []
        default_path = default_template_path

        for rule in rules:
            if not isinstance(rule, dict):
                continue
            template_path = str(rule.get("template_path") or "").strip()
            if not template_path:
                continue
            if rule.get("default"):
                default_path = template_path
                continue
            if self._profile_rule_matches(profile, rule.get("when") or {}):
                return template_path

        return default_path

    def _render_configured_generic_template(
        self,
        rule_key: str,
        default_template_path: str,
        state: Dict[str, Any],
        message: str,
        recommended: str,
    ) -> str:
        profile = state.get("profile") or {}
        template_path = self._configured_template_path(
            "generic_project",
            profile,
            rule_key,
            default_template_path,
        )
        template = self._copy_text(template_path)
        if not template:
            return ""

        values = self._generic_template_values(state, message, recommended)
        try:
            return template.format(**values)
        except KeyError as exc:
            logger.warning(
                f"[SchemeAdvisorEntryV2] generic template missing variable: "
                f"path={template_path}, variable={exc}"
            )
            return ""

    def _configured_template_path(
        self,
        section_key: str,
        profile: Dict[str, Any],
        rule_key: str,
        default_template_path: str,
    ) -> str:
        rules = self._entry_copy.get(section_key, {}).get(rule_key) or []
        default_path = default_template_path

        for rule in rules:
            if not isinstance(rule, dict):
                continue
            template_path = str(rule.get("template_path") or "").strip()
            if not template_path:
                continue
            if rule.get("default"):
                default_path = template_path
                continue
            if self._profile_rule_matches(profile, rule.get("when") or {}):
                return template_path

        return default_path

    def _configured_card_path(
        self,
        section_key: str,
        profile: Dict[str, Any],
        rule_key: str,
        default_card_path: str,
    ) -> Optional[str]:
        rules = self._entry_copy.get(section_key, {}).get(rule_key) or []
        default_path = default_card_path or None

        for rule in rules:
            if not isinstance(rule, dict):
                continue
            card_path = str(rule.get("card_path") or "").strip()
            if not card_path:
                continue
            if rule.get("default"):
                default_path = default_path or card_path
                continue
            if self._profile_rule_matches(profile, rule.get("when") or {}):
                return card_path

        return default_path

    def _generic_template_values(
        self,
        state: Dict[str, Any],
        message: str,
        recommended: str,
    ) -> Dict[str, str]:
        profile = state.get("profile") or {}
        state_text = self._state_text(state, message)
        axes = profile.get("semantic_axes") or derive_semantic_axes(state_text)
        reasons = ((profile.get("version_score") or {}).get("reasons") or [])[:3]
        reason_text = (
            "、".join(self._humanize_version_reason(reason, profile) for reason in reasons)
            if reasons
            else "当前项目的决策压力"
        )

        return {
            "tier_name": self._tier_name(recommended),
            "space_label": self._display_space_label(profile),
            "focus": self._focus_phrase(profile),
            "decision_focus": self._generic_decision_focus(axes, state_text),
            "pending": "、".join(
                (profile.get("maturity") or {}).get("pending")
                or ["CAD/平面图", "现场照片", "品牌资料"]
            ),
            "reason_text": reason_text,
            "coverage_note": self._knowledge_coverage_note(profile),
        }

    def _generic_decision_focus(self, axes: Dict[str, Any], state_text: str) -> str:
        context_sentence = self._semantic_context_sentence(axes, state_text).strip("。")
        tension_labels = [
            str(item.get("label") or item.get("title"))
            for item in rank_main_tensions(state_text, limit=3)
            if item.get("label") or item.get("title")
        ]
        if tension_labels:
            return "、".join(tension_labels[:3])
        if context_sentence:
            return context_sentence
        return "目标、约束、使用者和风险边界"

    @staticmethod
    def _knowledge_coverage_note(profile: Dict[str, Any]) -> str:
        context_packet = profile.get("context_packet") or {}
        knowledge_binding = context_packet.get("knowledge_binding") or {}
        ceiling = (
            knowledge_binding.get("coverage_ceiling")
            or (profile.get("knowledge_context") or {}).get("coverage_ceiling")
            or (profile.get("capability_plan") or {}).get("knowledge_coverage")
            or {}
        )
        if not isinstance(ceiling, dict):
            return ""
        coverage_level = str(ceiling.get("coverage_level") or "")
        should_warn = bool(ceiling.get("must_not_claim_specialist_coverage")) or coverage_level in {
            "general_method_only",
            "partial_specialist",
        }
        if not should_warn:
            return ""
        note = str(ceiling.get("user_visible_note") or "").strip()
        if not note:
            if coverage_level == "partial_specialist":
                note = "当前只有部分专科依据，可以先做条件级判断，不能直接当成完整专科方案。"
            else:
                note = "当前还没有足够的专科知识支撑，只能先给通用方法论和策略级判断，不能套用专科知识包。"
        return f"\n\n{note}"

    def _beverage_template_values(
        self,
        state: Dict[str, Any],
        message: str,
        recommended: str,
    ) -> Dict[str, str]:
        profile = state.get("profile") or {}
        state_text = self._state_text(state, message)
        signals = self._beverage_signals(profile, state_text)
        directory_focus = self._beverage_directory_focus(signals)

        return {
            "tier_name": self._tier_name(recommended),
            "space_label": self._display_space_label(profile),
            "focus": self._focus_phrase(profile),
            "model_label": self._select_rule_text(
                "tea_retail_space.model_label_rules",
                signals,
            )
            or self._display_space_label(profile),
            "model_sentence": self._select_rule_text(
                "tea_retail_space.model_sentence_rules",
                signals,
            ),
            "lever_sentence": self._select_rule_text(
                "tea_retail_space.lever_sentence_rules",
                signals,
            ),
            "directory_focus": "、".join(directory_focus),
            "pending": "、".join(
                (profile.get("maturity") or {}).get("pending")
                or ["CAD/平面图", "现场照片", "品牌资料", "设备清单", "预算边界"]
            ),
        }

    def _beverage_signals(
        self,
        profile: Dict[str, Any],
        state_text: str,
    ) -> Dict[str, bool]:
        signal_terms = self._copy_get("tea_retail_space.signals") or {}
        searchable = " ".join(
            [
                str(state_text or ""),
                " ".join(str(tag) for tag in (profile.get("entry_scene_tags") or [])),
                str(profile.get("subdomain_id") or ""),
                str(profile.get("activation_pack_id") or ""),
                str(profile.get("space_label") or ""),
            ]
        )
        return {
            str(signal): any(str(term) and str(term) in searchable for term in (terms or []))
            for signal, terms in signal_terms.items()
        }

    def _beverage_directory_focus(self, signals: Dict[str, bool]) -> List[str]:
        focus_map = self._copy_get("tea_retail_space.directory_focus") or {}
        selected: List[str] = []
        for signal, matched in signals.items():
            if not matched:
                continue
            for item in focus_map.get(signal) or []:
                text = str(item or "").strip()
                if text and text not in selected:
                    selected.append(text)
        if selected:
            return selected[:4]
        return [str(item) for item in (focus_map.get("default") or []) if str(item)]

    def _focus_phrase(self, profile: Dict[str, Any]) -> str:
        planned_pages = (((profile.get("question_plan") or {}).get("round_1_card") or {}).get("pages") or [])
        if planned_pages:
            labels = self._unique_focus_labels(
                str(option.get("label"))
                for option in (planned_pages[0].get("options") or [])[:6]
                if option.get("label")
            )
            if labels:
                return "、".join(labels)
        focus = profile.get("ontology_focus") or {}
        items = (
            focus.get("priority_sequence")
            or focus.get("required_dimensions")
            or focus.get("activated_constraints")
            or []
        )
        labels = [self._humanize(str(item)) for item in items[:3] if item]
        return "、".join(labels) if labels else "目标、约束、使用者和风险边界"

    def _knowledge_phrase(self, profile: Dict[str, Any]) -> str:
        context = profile.get("knowledge_context") or {}
        packages = context.get("resolved_packages") or []
        titles = [str(pkg.get("title")) for pkg in packages[:2] if pkg.get("title")]
        if titles:
            return "、".join(titles)
        tags = context.get("search_tags") or []
        if tags:
            return "、".join(str(tag) for tag in tags[:3])
        return "项目知识库"

    @staticmethod
    def _humanize(value: str) -> str:
        return public_label(value)

    @staticmethod
    def _display_space_label(profile: Dict[str, Any]) -> str:
        label = str(profile.get("space_label") or "这个项目")
        subdomain = str(profile.get("subdomain_id") or "")
        if subdomain == "tea_drink_store" and label == "茶饮店":
            return "茶饮小店"
        return label

    @staticmethod
    def _humanize_version_reason(reason: str, profile: Dict[str, Any]) -> str:
        text = str(reason or "").strip()
        space_label = SchemeAdvisorEntryService._display_space_label(profile)
        replacements = {
            "已识别细分业态": f"已识别为{space_label}",
            "已激活细分业态本体包": f"已匹配{space_label}的判断框架",
            "涉及投资、租金、回本或成本压力": "存在投资、租金、回本压力",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)
        text = text.replace("本体包", "判断框架")
        text = text.replace("本体", "判断框架")
        text = text.replace("知识包", "判断资料")
        return text or "当前项目的决策压力"

    @staticmethod
    def _unique_focus_labels(labels: Iterable[str]) -> List[str]:
        result: List[str] = []
        seen = set()
        for label in labels:
            text = str(label or "").strip()
            for suffix in ("已明确", "待确认"):
                if text.endswith(suffix):
                    text = text[: -len(suffix)]
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
            if len(result) >= 3:
                break
        return result

    def _planned_card(self, planned: Dict[str, Any], card_prefix: str, card_type: str) -> Dict[str, Any]:
        return {
            "card_id": f"{card_prefix}-{uuid.uuid4().hex[:8]}",
            "card_type": card_type,
            "title": planned.get("title", ""),
            "prompt_text": planned.get("prompt_text", ""),
            "options": [],
            "allow_freetext": True,
            "pages": planned.get("pages") or [],
            "source": planned.get("source") or "context_intelligence_packet",
        }

    def _summary_ontology_focus(self, profile: Dict[str, Any]) -> List[str]:
        focus = profile.get("ontology_focus") or {}
        items = (
            focus.get("activated_objects")
            or focus.get("priority_sequence")
            or focus.get("required_dimensions")
            or []
        )
        return [self._humanize(str(item)) for item in items[:5]] or ["空间对象", "使用行为", "约束边界", "风险底线"]

    @staticmethod
    def _summary_knowledge_modules(profile: Dict[str, Any]) -> List[str]:
        context = profile.get("knowledge_context") or {}
        packages = context.get("resolved_packages") or []
        titles = [
            SchemeAdvisorEntryService._humanize_knowledge_module_title(str(pkg.get("title")))
            for pkg in packages
            if pkg.get("title")
        ]
        if titles:
            return titles[:5]
        package_ids = [str(item) for item in context.get("knowledge_packages") or []]
        labels = [
            SchemeAdvisorEntryService._humanize_knowledge_module_title(item)
            for item in package_ids[:5]
        ]
        return labels or ["空间类型判断", "项目成立判断", "设计资料调用"]

    @staticmethod
    def _humanize_knowledge_module_title(title: str) -> str:
        translated = public_label(title)
        if translated != "待确认项":
            return (
                translated.replace("Knowledge Package", "判断资料")
                .replace("knowledge package", "判断资料")
                .replace("知识包", "判断")
                .replace("本体论", "项目判断框架")
                .replace("本体", "判断框架")
            )
        return translated

    def _result(self, reply: str, card: Optional[Dict[str, Any]], state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "reply": reply,
            "intent": "scheme_advisor_entry",
            "guidance_card": card,
            "scheme_entry_state": state,
            "drafts": [],
            "upgrade_signal": None,
            "upgrade_suggested": False,
        }

    def _append_round(self, state: Dict[str, Any], round_id: str, message: str) -> Dict[str, Any]:
        rounds = list(state.get("rounds") or [])
        rounds.append({"round": round_id, "content": message, "timestamp": datetime.now().isoformat()})
        return {**state, "rounds": rounds}

    def _generate_reply(
        self,
        *,
        stage: str,
        fallback: str,
        user_message: str,
        state: Dict[str, Any],
        instruction: str,
    ) -> str:
        if self._llm is None:
            return fallback

        prompt = (
            "你是「方案高参」的入口问诊助手，只服务于把具体空间设计项目转成设计任务书。\n"
            "你的职责是生成用户看得见的正文回复，卡片和流程由系统另行控制。\n"
            "必须遵守：不索要CAD上传；不提前付款；不展开完整设计方案；不使用标题列表堆砌；"
            "语言要专业、克制、有洞察；不要在正文里提出独立追问，具体追问由系统卡片承接。\n"
            "质量要求：不要只归纳信息，要指出项目真正危险、真正值钱、真正需要先判断的地方；"
            "如果上下文包含用户已选答案，必须把答案转译成阶段判断，不得复用上一轮模板；"
            "少用内部术语，多用用户能感到现场压力的语言，例如门头能不能停下、出杯会不会拖死、排队会不会外溢、投入会不会拉长回本。\n\n"
            f"当前阶段：{stage}\n"
            f"任务要求：{instruction}\n"
            f"用户本轮输入：{user_message}\n"
            f"结构化上下文：{state}\n"
        )
        try:
            response = self._llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            content = str(content).strip()
            if content:
                logger.info(f"[SchemeAdvisorEntryV2] LLM reply generated: stage={stage}, chars={len(content)}")
                return content
        except Exception as exc:
            logger.warning(f"[SchemeAdvisorEntryV2] LLM reply failed, fallback used: stage={stage}, error={exc}")
        return fallback

    def _apply_tea_entry_overrides(self, profile: Dict[str, Any], message: str) -> Dict[str, Any]:
        if not (
            self._is_explicit_tea_context(message)
            or self._is_tea_classification_profile(profile)
        ):
            return profile

        updated = dict(profile or {})
        updated["mode"] = "project"
        updated["space_label"] = "茶饮小店"
        updated["type_ontology_profile"] = "tea_drink_store"
        updated["project_type"] = "commercial_dining"
        updated["project_type_name"] = "餐饮/食饮空间"
        updated["subdomain_id"] = "tea_drink_store"
        updated["activation_pack_id"] = "tea_drink_store_pack"
        updated["entry_scene_tags"] = self._tea_scene_tags(message)

        classification = dict(updated.get("classification") or {})
        classification["project_type"] = "commercial_dining"
        classification["project_type_name"] = "餐饮/食饮空间"
        classification["confidence"] = max(float(classification.get("confidence") or 0), 0.74)
        classification["confidence_level"] = "high"
        classification["status"] = "classified"
        classification["coverage_gap"] = False
        classification["knowledge_gap_ticket"] = None
        classification["ontology_unmatched"] = [
            item
            for item in classification.get("ontology_unmatched") or []
            if item != "low_project_type_confidence"
        ]
        updated["classification"] = classification

        packet = deepcopy(updated.get("context_packet") or {})
        if packet:
            packet_classification = dict(packet.get("classification") or {})
            packet_classification["project_type_id"] = "commercial_dining"
            packet_classification["project_type_name"] = "餐饮/食饮空间"
            subdomain = dict(packet_classification.get("subdomain") or {})
            subdomain["primary_subdomain_id"] = "tea_drink_store"
            subdomain["confidence"] = max(float(subdomain.get("confidence") or 0), 0.74)
            packet_classification["subdomain"] = subdomain
            packet["classification"] = packet_classification

            ontology_binding = dict(packet.get("ontology_binding") or {})
            ontology_binding["framework_id"] = "commercial_dining"
            ontology_binding["activation_pack_id"] = "tea_drink_store_pack"
            packet["ontology_binding"] = ontology_binding

            coordination = dict(packet.get("activation_pack_coordination") or {})
            loaded_ids = list(coordination.get("loaded_pack_ids") or [])
            if "tea_drink_store_pack" not in loaded_ids:
                loaded_ids.insert(0, "tea_drink_store_pack")
            coordination["loaded_pack_ids"] = loaded_ids
            packet["activation_pack_coordination"] = coordination
            updated["context_packet"] = packet
            updated["context_vector"] = packet.get("context_vector") or updated.get("context_vector") or {}

        trace = dict(updated.get("intelligence_trace") or {})
        trace["confidence"] = max(float(trace.get("confidence") or 0), 0.74)
        trace["confidence_level"] = "high"
        trace["coverage_gap"] = False
        trace["subdomain_id"] = "tea_drink_store"
        trace["activation_pack_id"] = "tea_drink_store_pack"
        trace["context_packet_project_type_id"] = "commercial_dining"
        updated["intelligence_trace"] = trace

        return updated

    def _tea_scene_tags(self, message: str) -> List[str]:
        text = message or ""
        tags: List[str] = []

        def add(tag: str, *terms: str) -> None:
            if any(term in text for term in terms) and tag not in tags:
                tags.append(tag)

        if self._is_tea_operational_diagnostic(text):
            tags.append("operational_diagnostic")
        if any(term in text for term in TEA_HARD_BOUNDARY_TERMS):
            tags.append("hard_boundary")
        add("transit", "地铁", "高铁", "站内", "车站", "通道", "负一楼", "地下")
        add("payback", "回本", "赚钱", "成本", "投入", "租金", "预算", "盈利")
        add("community", "社区", "小区", "老人", "小孩", "孩子", "宝妈", "镇上", "县城")
        add("office", "写字楼", "园区", "上班族", "互联网", "国贸", "大堂", "办公")
        add("campus", "大学城", "学生", "学校")
        add("tourism", "古镇", "景区", "游客", "老街", "老建筑", "文创", "地方文化")
        add("competition", "竞品", "咖啡", "甜品", "隔壁", "蜜雪", "霸王茶姬", "瑞幸", "同一条街")
        add("franchise", "加盟", "总部", "标准图", "品牌方")
        add("delivery", "外卖", "自提", "外带")
        add("renovation", "翻新", "改成", "改造", "老旧", "原来是")
        if (
            len(text) <= 35
            or any(term in text for term in ("不知道", "没想好", "别问那么多", "先不要问太多", "只有初步想法"))
        ) and "low_info" not in tags:
            tags.append("low_info")
        if not tags:
            tags.append("general_tea")
        return tags

    @staticmethod
    def _has_any(text: str, terms: Iterable[str]) -> bool:
        return any(term in text for term in terms)

    def _is_tea_entry_context(self, message: str) -> bool:
        text = message.strip()
        if not text:
            return False
        has_tea_term = self._has_any(text, TEA_BUSINESS_TERMS)
        if has_tea_term:
            return True
        if "咖啡" in text and not has_tea_term:
            return False
        hard_hits = sum(1 for term in TEA_HARD_BOUNDARY_TERMS if term in text)
        shop_context = self._has_any(
            text,
            (
                "铺位",
                "商铺",
                "店",
                "吧台",
                "平面",
                "物业",
                "设备",
                "商场",
                "座位",
                "外卖",
                "面宽",
                "进深",
                "铺型",
                "营业额",
                "开业",
                "装修",
                "风险",
                "赚钱",
                "方案",
                "打卡墙",
                "标准图",
                "加盟",
            ),
        )
        strong_shop_context = self._has_any(text, STRONG_TEA_SHOP_CONTEXT_TERMS)
        if hard_hits and strong_shop_context:
            return True
        operation_hits = sum(1 for term in STRONG_TEA_OPERATION_TERMS if term in text)
        if operation_hits >= 2 and strong_shop_context:
            return True
        if operation_hits >= 1 and strong_shop_context and self._has_any(text, ("SKU", "出杯", "外卖", "打卡墙", "菜单")):
            return True
        return bool(has_tea_term and shop_context)

    @classmethod
    def _is_explicit_tea_context(cls, message: str) -> bool:
        return cls._has_any(str(message or ""), TEA_BUSINESS_TERMS)

    @staticmethod
    def _is_tea_classification_profile(profile: Dict[str, Any]) -> bool:
        markers = {
            str(profile.get("subdomain_id") or ""),
            str(profile.get("activation_pack_id") or ""),
        }
        classification = profile.get("classification") or {}
        context_packet = profile.get("context_packet") or {}
        packet_classification = context_packet.get("classification") or {}
        packet_subdomain = packet_classification.get("subdomain") or {}
        ontology_binding = context_packet.get("ontology_binding") or {}
        markers.update(
            {
                str((classification.get("_v18_extensions") or {}).get("subdomain_id") or ""),
                str(packet_subdomain.get("primary_subdomain_id") or ""),
                str(ontology_binding.get("activation_pack_id") or ""),
            }
        )
        return bool(markers.intersection({"tea_drink_store", "tea_drink_store_pack"}))

    def _is_tea_operational_diagnostic(self, message: str) -> bool:
        text = message.strip()
        if not text:
            return False
        diagnostic_signal = self._has_any(
            text,
            (
                "是否",
                "能否",
                "有没有",
                "有无",
                "测试",
                "观察",
                "记录",
                "计算",
                "检验标准",
                "平均",
                "比例",
            ),
        )
        operation_hits = sum(1 for term in TEA_OPERATION_TERMS if term in text)
        if diagnostic_signal and self._has_any(text, TEA_BUSINESS_TERMS):
            return True
        return diagnostic_signal and operation_hits >= 2

    def _should_enter_flow(self, message: str) -> bool:
        text = message.strip()
        if not text:
            return False
        if is_reference_material_request(text):
            return False
        if is_pure_naming_copy_request(text):
            return True
        if self._is_general_method_question(text):
            return True
        if self._is_tea_entry_context(text):
            return True
        if self._has_concrete_project_anchor(text):
            return True

        axes = derive_semantic_axes(text)
        axis_hits = semantic_axis_density(axes)
        return (has_input_intent(axes) and axis_hits >= 2) or axis_hits >= 3

    def _is_fresh_project_restart(self, message: str) -> bool:
        text = message.strip()
        if not text:
            return False
        if not self._should_enter_flow(text):
            return False
        restart_signal = any(
            key in text
            for key in (
                "设计任务书",
                "任务书",
                "需要设计",
                "帮我做",
                "重新开始",
                "另一个项目",
                "新项目",
            )
        )
        if not restart_signal:
            return False
        if self._has_concrete_project_anchor(text):
            return True

        semantic_axes = derive_semantic_axes(text)
        axis_hits = semantic_axis_density(semantic_axes)
        numeric_anchor = bool(
            re.search(
                r"\d+(?:\.\d+)?\s*(?:㎡|平米|平方米|m2|m²|万平|间|层|小时|夜间|个夜间)",
                text,
                flags=re.IGNORECASE,
            )
        )
        place_or_space_carrier = self._has_any(
            text,
            (
                "位于",
                "商场",
                "商铺",
                "铺位",
                "门店",
                "店铺",
                "餐厅",
                "咖啡店",
                "别墅",
                "住宅",
                "民宿",
                "酒店",
                "展厅",
                "办公室",
                "社区",
                "街区",
                "公园",
                "校园",
                "医院",
                "会所",
            ),
        )
        return (numeric_anchor and place_or_space_carrier) or axis_hits >= 2

    def _classify_input(self, message: str) -> Dict[str, Any]:
        axes = derive_semantic_axes(message)
        if is_pure_naming_copy_request(message):
            return {"mode": "redirect", "space_label": "待明确项目"}
        if self._is_competition_strategy_request(message):
            return self._methodology_profile(axes)
        if is_methodology_discussion_request(message) and not self._has_project_reconstruction_intent(message):
            return self._methodology_profile(axes)
        if has_problem_mode(axes) and not self._has_concrete_project_anchor(message):
            return self._methodology_profile(axes)
        if self._is_general_method_question(message):
            return {"mode": "redirect", "space_label": "待明确项目"}
        profile = self._context_intelligence.build(message)
        return self._apply_tea_entry_overrides(profile, message)

    @staticmethod
    def _is_competition_strategy_request(message: str) -> bool:
        text = str(message or "")
        has_competition = any(term in text for term in ("竞标", "投标", "竞赛", "评审"))
        has_strategy = any(term in text for term in ("汇报策略", "评审打动", "PPT", "提案策略", "投标策略", "竞标策略"))
        return has_competition and has_strategy

    @staticmethod
    def _has_project_reconstruction_intent(message: str) -> bool:
        text = str(message or "")
        return any(
            term in text
            for term in (
                "重构需求",
                "帮我重构",
                "梳理需求",
                "重构我的需求",
                "请提出完整设计",
            )
        )

    @staticmethod
    def _has_concrete_project_anchor(message: str) -> bool:
        # Delegates to the shared registry-driven detector so entry triage and
        # demand reconstruction share one authoritative anchor definition.
        return has_concrete_project_anchor(message)

    @staticmethod
    def _methodology_profile(axes: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "mode": "methodology",
            "space_label": "方法论问题",
            "semantic_axes": axes,
            "project_type": None,
            "project_type_name": None,
            "context_packet": {
                "schema_version": "context_packet.v3.3",
                "packet_type": "methodology_discussion",
                "classification": {
                    "mode": "methodology",
                    "space_domains": axes.get("space_domains") or [],
                    "problem_modes": axes.get("problem_modes") or [],
                },
                "missing_slots": [],
                "knowledge_coverage": {
                    "level": "framework",
                    "ceiling": "methodology_framework",
                },
            },
            "intelligence_trace": {
                "confidence": 0.72,
                "coverage_gap": False,
            },
        }

    def _is_general_method_question(self, message: str) -> bool:
        axes = derive_semantic_axes(message)
        return has_problem_mode(axes) and not self._has_concrete_project_anchor(message)

    def _recommend_version(self, state: Dict[str, Any]) -> str:
        profile = state.get("profile") or {}
        score = profile.get("version_score") or {}
        if score.get("recommended_version"):
            return str(score["recommended_version"])
        text = " ".join([state.get("initial_input", "")] + [r.get("content", "") for r in state.get("rounds", [])])
        refreshed_score = self._context_intelligence.score_version(
            text,
            profile.get("classification") or {},
            {"_v18_extensions": {"subdomain_id": profile.get("subdomain_id")}},
            profile.get("activation_pack_meta") or {},
        )
        return str(refreshed_score.get("recommended_version") or "standard")

    def _tier_name(self, tier_id: str) -> str:
        tier = next((t for t in self._tiers if t["id"] == tier_id), None)
        return tier["name"] if tier else "标准版"

    def _load_tiers(self) -> List[Dict[str, Any]]:
        config_path = Path(__file__).resolve().parents[1] / "config" / "scheme_advisor_version_tiers.yaml"
        with config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        tiers = data.get("tiers") or []
        if not tiers:
            raise ValueError(f"方案高参三档配置为空: {config_path}")
        return tiers

    def _load_entry_copy(self) -> Dict[str, Any]:
        config_path = Path(__file__).resolve().parents[1] / "config" / "scheme_advisor_entry_copy.yaml"
        with config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if not data:
            raise ValueError(f"方案高参入口文案配置为空: {config_path}")
        return data

    def _copy_get(self, dotted_path: str) -> Any:
        current: Any = self._entry_copy
        for part in dotted_path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
        return current

    def _copy_text(self, dotted_path: str) -> str:
        value = self._copy_get(dotted_path)
        return str(value or "")

    def _render_copy(self, dotted_path: str, **values: Any) -> str:
        template = self._copy_text(dotted_path)
        return template.format(**values) if template else ""

    def _configured_card(self, dotted_path: str, card_prefix: str, card_type: str) -> Optional[Dict[str, Any]]:
        config = self._copy_get(dotted_path)
        if not isinstance(config, dict):
            return None
        return {
            "card_id": f"{card_prefix}-{uuid.uuid4().hex[:8]}",
            "card_type": card_type,
            "title": config.get("title", ""),
            "prompt_text": config.get("prompt_text", ""),
            "options": [],
            "allow_freetext": True,
            "source": "entry_copy.configured",
            "pages": deepcopy(config.get("pages") or []),
            "deferred_formal_checks": config.get("deferred_formal_checks")
            or [
                "property_conditions",
                "plan_measurement",
                "equipment_layout",
                "safety_and_compliance",
            ],
        }

    def _select_rule_text(self, dotted_path: str, signals: Dict[str, bool]) -> str:
        rules = self._copy_get(dotted_path) or []
        default_text = ""
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            text = str(rule.get("text") or "")
            if rule.get("default"):
                default_text = text
                continue
            required = rule.get("when") or []
            if all(signals.get(str(key), False) for key in required):
                return text
        return default_text
