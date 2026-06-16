"""
对话态引擎 — 双态架构中的轻量常驻引擎

Copilot 生成（2026-03-15）
本模块实现对话态（conversation mode）的核心逻辑：

  接收用户消息
    ↓
  意图识别（零星问答 / 灵感探索 / 项目级信号）
    ↓
  ├─ 知识问答   → 直接 LLM 回答
  ├─ 灵感探索   → 草稿沉淀（更新草稿对象列表）
  └─ 项目级信号 → 三大认知指标检测
                    ├─ 未超阈值 → 继续对话
                    └─ 超过阈值 → 生成 UpgradeSignal（软提示，不强切）

对话态与项目态共享同一个 ProjectAnalysisState，
通过 system_mode 字段区分当前运行态。

Note: 升级编译器（草稿 → RawBriefPacket）在 mode_router.py 中实现。
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from loguru import logger

from intelligent_project_analyzer.core.domain_objects import (
    BoundaryDraft,
    CognitionIndicators,
    ConflictPack,
    ConsensusPack,
    DirectionCandidatePack,
    DraftObjectMeta,
    GuidanceCard,
    GuidanceCardOption,
    GuidanceCardPage,
    GuidanceCardType,
    GuidanceTrace,
    IntentSeed,
    ProblemFrameDraft,
    UpgradeSignal,
)
from intelligent_project_analyzer.core.state import AnalysisStage, ProjectAnalysisState


# ---------------------------------------------------------------------------
# 认知诊断结果
# ---------------------------------------------------------------------------

class CognitionDiagnosis(TypedDict):
    """LLM 诊断结果：意图分类 + 认知状态 + 本轮回复提示"""

    intent: str                            # knowledge_qa / inspiration / project_signal
    gap_item: Optional[str]                # 缺失的关键参数名，如 "预算"
    fork_directions: Optional[List[str]]   # 可选方向列表
    fork_consequences: Optional[List[str]] # 各方向后果提示
    summary_ready: bool                    # 是否适合归纳共识
    hypothesis_prompt: Optional[str]       # 值得探索的假设（一句话）
    reply_hint: str                        # 本轮聚焦主题


# ---------------------------------------------------------------------------
# 意图类型
# ---------------------------------------------------------------------------

_INTENT_KNOWLEDGE_QA = "knowledge_qa"       # 零星问答，直接回答
_INTENT_INSPIRATION = "inspiration"         # 灵感探索，沉淀草稿
_INTENT_PROJECT_SIGNAL = "project_signal"   # 项目级需求，检测升级指标

_QA_TRIGGERS = (
    "规范", "标准", "一般怎么", "通常", "是什么", "有没有", "什么是",
    "怎么理解", "解释一下", "介绍一下",
)
_INSPIRATION_TRIGGERS = (
    "感觉", "风格", "想法", "尝试", "试试", "灵感", "参考", "案例",
    "氛围", "调性", "方向", "如果", "会不会",
)
_PROJECT_TRIGGERS = (
    "方案", "项目", "设计", "民宿", "住宅", "商业", "规划",
    "装修", "改造", "完整", "帮我做", "需要方案",
)

# ---------------------------------------------------------------------------
# 升级阈值（可通过配置覆盖）
# ---------------------------------------------------------------------------

_UPGRADE_FREEZE_THRESHOLD = 0.7
_UPGRADE_DEBT_THRESHOLD = 0.6
_UPGRADE_FATIGUE_THRESHOLD = 0.6


# ---------------------------------------------------------------------------
# ConversationEngine
# ---------------------------------------------------------------------------


class ConversationEngine:
    """
    对话态轻量引擎。

    LangGraph 注册示例：
        engine = ConversationEngine(llm=llm_model)
        graph.add_node("conversation_engine", engine.execute)
    """

    def __init__(self, llm: Optional[BaseChatModel] = None) -> None:
        self._llm = llm

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def execute(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        对话态主逻辑。

        返回 state 更新 dict（LangGraph 节点标准返回形式）。

        支持引导卡片交互：
          - 若请求携带 in_response_to_card_id，先处理卡片响应（沉淀草稿）
          - 正常回复之后，评估是否生成新引导卡片并附带下发
        """
        user_input: str = state.get("user_input", "")
        session_id: str = state.get("session_id", "unknown")
        existing_drafts: List[Dict[str, Any]] = state.get("conversation_drafts") or []

        # 引导卡片响应字段（由 API 层注入 state_patch）
        in_response_to_card_id: Optional[str] = state.get("in_response_to_card_id")  # type: ignore[assignment]
        selected_option_id: Optional[str] = state.get("selected_option_id")  # type: ignore[assignment]
        card_response: Optional[Dict[str, Any]] = state.get("card_response")  # type: ignore[assignment]
        pending_card_raw: Optional[Dict[str, Any]] = state.get("pending_guidance_card")

        logger.info(f"[{session_id}] 对话态引擎接收输入: {user_input[:60]}…")

        # S-step 流水线状态（跨轮次持久化）
        conv_s_step: str = str(state.get("conv_s_step") or "dialogue")
        asked_gaps: List[str] = list(state.get("asked_gaps") or [])
        # 处于需求分析流水线中：s1_done / s2_done / s3_done / s4_done
        _PIPELINE_STEPS = frozenset(["s1_done", "s2_done", "s3_done", "s4_done"])
        _is_in_pipeline: bool = conv_s_step in _PIPELINE_STEPS

        updates: Dict[str, Any] = {
            "system_mode": "conversation",
            "current_stage": AnalysisStage.REQUIREMENT_COLLECTION.value,
            # 每轮开始时清空上一轮卡片，避免前端重复展示
            "pending_guidance_card": None,
        }

        # ── Phase A：处理用户对上一张引导卡片的响应 ──────────────────
        if in_response_to_card_id and pending_card_raw:
            card_updates = self._process_card_response(
                state,
                in_response_to_card_id,
                selected_option_id,
                user_input,
                card_response,
                pending_card_raw,
                session_id,
            )
            updates.update(card_updates)
            # 刷新 existing_drafts，使后续指标计算能看到新草稿
            existing_drafts = updates.get("conversation_drafts") or existing_drafts

        # ── Phase B：认知诊断 & 主回复（单次 LLM）────────────────────
        # 卡片回应时，构造对 LLM 友好的输入（避免把 "[card:a]" 发给 LLM）
        llm_input = user_input
        if in_response_to_card_id and pending_card_raw:
            card_title = pending_card_raw.get("title") or pending_card_raw.get("card_type", "")
            all_opts = list(pending_card_raw.get("options") or []) + [
                o
                for p in (pending_card_raw.get("pages") or [])
                for o in (p.get("options") or [])
            ]
            selected_opt = next(
                (o for o in all_opts if o.get("id") == selected_option_id), None
            )
            if selected_opt:
                label = selected_opt.get("label", "")
                desc = selected_opt.get("description", "")
                llm_input = f"我选择了「{label}」{('：' + desc) if desc else ''}。请继续深入这个方向。"
            elif card_response:
                llm_input = self._card_response_summary(card_response) or "我已经完成这轮判断，请继续。"
            elif user_input.startswith("["):
                llm_input = "我已经做出了选择，请继续。"

        # 预检：完整项目简报（高富集度）→ 跳过苏格拉底，直接执行 S1 拆解
        _pre_indicators = self._compute_cognition_indicators(user_input, existing_drafts, state)
        _is_direct_brief = _pre_indicators.should_trigger_upgrade and not in_response_to_card_id

        if _is_direct_brief:
            # 直接 S1 路径：单次 LLM，使用 S1 专用 prompt
            reply_text = self._run_s1_analysis(llm_input, session_id)
            # 合成最小诊断：fork_directions=None 阻止卡片生成
            diagnosis: CognitionDiagnosis = {
                "intent": _INTENT_PROJECT_SIGNAL,
                "gap_item": None,
                "fork_directions": None,
                "fork_consequences": None,
                "summary_ready": False,
                "hypothesis_prompt": None,
                "reply_hint": "S1 原料拆解",
            }
            signal = UpgradeSignal(
                indicators=_pre_indicators,
                suggestion_text=reply_text,
                triggered=True,
            )
            updates["upgrade_signal"] = signal.model_dump()
            updates["cognition_indicators"] = _pre_indicators.model_dump()
            # 记录步骤状态：S1 完成，下次进入 S2
            updates["conv_s_step"] = "s1_done"
            updates["asked_gaps"] = []
            logger.info(f"[{session_id}] 高富集简报，直接执行 S1 拆解 → conv_s_step=s1_done")

        elif _is_in_pipeline and in_response_to_card_id:
            # 流水线内答卡：确认选择，禁止触发新诊断或出新卡
            # 用户的卡片选择已在 Phase A _process_card_response 中沉淀为草稿
            reply_text = "已记录你的选择。说「继续」就进入下一步分析，或者补充更多细节。"
            diagnosis = self._fallback_diagnosis_obj(user_input, _INTENT_PROJECT_SIGNAL)
            # gap/fork 均为 None → Phase C 不会出任何引导卡
            logger.info(f"[{session_id}] 流水线内答卡，短路诊断，等待继续指令")

        elif _is_in_pipeline and not in_response_to_card_id:
            # S-step 流水线推进（S2→S3→S4→S5）
            # 用户非卡片响应时，执行下一步分析
            reply_text, next_conv_s_step = self._run_s_step_analysis(
                conv_s_step, llm_input, state, session_id
            )
            diagnosis = self._fallback_diagnosis_obj(user_input, _INTENT_PROJECT_SIGNAL)
            updates["conv_s_step"] = next_conv_s_step
            logger.info(
                f"[{session_id}] S-step 推进: {conv_s_step} → {next_conv_s_step}"
            )

        else:
            # 普通对话路径：苏格拉底诊断（含 LLM 调用）
            reply_text, diagnosis = self._diagnose_cognition(
                llm_input, state, existing_drafts, session_id
            )

        intent = diagnosis["intent"]
        logger.info(
            f"[{session_id}] 认知诊断: intent={intent} gap={diagnosis['gap_item']} "
            f"fork={bool(diagnosis['fork_directions'])} summary={diagnosis['summary_ready']}"
        )
        updates["conversation_intent"] = intent

        if intent == _INTENT_INSPIRATION:
            new_draft = self._create_inspiration_draft(user_input, session_id)
            existing_drafts = self._append_draft(existing_drafts, new_draft)
            updates["conversation_drafts"] = existing_drafts

        elif intent == _INTENT_PROJECT_SIGNAL:
            new_draft = self._create_intent_seed(user_input, session_id)
            existing_drafts = self._append_draft(existing_drafts, new_draft)
            updates["conversation_drafts"] = existing_drafts

            if not _is_direct_brief and not _is_in_pipeline:
                # 渐进路径：用含新草稿的指标判断是否升级
                indicators = self._compute_cognition_indicators(user_input, existing_drafts, state)
                updates["cognition_indicators"] = indicators.model_dump()

                if indicators.should_trigger_upgrade:
                    signal = UpgradeSignal(
                        indicators=indicators,
                        suggestion_text=self._build_upgrade_suggestion(user_input, indicators),
                        triggered=True,
                    )
                    updates["upgrade_signal"] = signal.model_dump()
                    reply_text = signal.suggestion_text
                    logger.info(f"[{session_id}] 渐进升级信号触发: {signal.suggestion_text[:80]}")

        updates["conversation_history"] = [
            HumanMessage(content=user_input),
            AIMessage(content=reply_text),
        ]
        updates["conversation_reply"] = reply_text

        # ── Phase C：生成引导卡片（诊断驱动）─────────────────────────
        # Gap 去重：已问过的 gap 跳过，防止重复询问同一缺失项
        _raw_gap = diagnosis.get("gap_item")
        _effective_gap = _raw_gap if (_raw_gap and _raw_gap not in asked_gaps) else None
        if _raw_gap and _raw_gap in asked_gaps:
            logger.debug(f"[{session_id}] gap={_raw_gap!r} 已询问过，跳过 GAP 卡生成")
        effective_diagnosis: CognitionDiagnosis = {**diagnosis, "gap_item": _effective_gap}  # type: ignore[misc]

        card = self._maybe_generate_guidance_card(
            state, updates.get("conversation_drafts") or existing_drafts, effective_diagnosis
        )
        if card:
            updates["pending_guidance_card"] = card.model_dump()
            logger.info(f"[{session_id}] 生成引导卡片: type={card.card_type} id={card.card_id}")
            # 记录已生成 GAP 卡的 gap 项，防止下轮重复
            if card.card_type == GuidanceCardType.GAP and _effective_gap:
                updates["asked_gaps"] = asked_gaps + [_effective_gap]

        updates["updated_at"] = datetime.now().isoformat()
        return updates

    # ------------------------------------------------------------------
    # 意图识别
    # ------------------------------------------------------------------

    def _classify_intent(self, text: str) -> str:
        """轻量规则意图分类（无 LLM 调用，快速响应）"""
        text_lower = text.lower()

        # 问句形式 → 优先知识问答
        if text.strip().endswith("？") or text.strip().endswith("?"):
            if any(t in text for t in _QA_TRIGGERS):
                return _INTENT_KNOWLEDGE_QA

        # 灵感探索触发词
        if any(t in text for t in _INSPIRATION_TRIGGERS):
            return _INTENT_INSPIRATION

        # 项目信号词计数
        project_hit = sum(1 for t in _PROJECT_TRIGGERS if t in text)
        if project_hit >= 2:
            return _INTENT_PROJECT_SIGNAL

        # 默认：知识问答
        return _INTENT_KNOWLEDGE_QA

    # ------------------------------------------------------------------
    # 知识问答处理
    # ------------------------------------------------------------------

    _SYSTEM_PROMPT_QA = (
        "你是「方案高参」，一位经验丰富、思维锱利的室内/建筑设计顾问。"
        "回答用户的题问时运用专业知识，语言简洁直接，防止兑余标题和广播式输出。"
    )

    _SYSTEM_PROMPT_PROJECT = (
        "你是「方案高参」，一位专注室内/建筑设计的资深顾问。"
        "你的工作方式是《渐进式深潜》：先聊后做，逐步探将设计意图。请严格遵守以下规则：\n"
        "1. 每次回应只提出 1～2 个考题或追问，不要一次吐完整方案；\n"
        "2. 考题要具体且尖锐（如预算、使用者画像、关键矛盾点），脑力肌而非信息表单；\n"
        "3. 当相互已把核心需求、限制、目标用户分析清楚后，再推进到设计框架阶段；\n"
        "4. 回应长度开始不超过 100 字，随着对话深入可逐步展开；\n"
        "5. 不要用标题带序号（###、——等）输出整篇结构文档，保持对话感。"
    )

    def _handle_knowledge_qa(
        self, user_input: str, state: ProjectAnalysisState, intent: str = _INTENT_KNOWLEDGE_QA
    ) -> Dict[str, Any]:
        """
        直接回答知识类问题。
        无 LLM 时返回占位回复；有 LLM 时调用生成。
        """
        if self._llm is None:
            reply = "抱歉，AI 服务暂未就绪，请稍后再试。"
        else:
            sys_prompt = (
                self._SYSTEM_PROMPT_PROJECT
                if intent == _INTENT_PROJECT_SIGNAL
                else self._SYSTEM_PROMPT_QA
            )
            try:
                history = state.get("conversation_history") or []
                messages = [SystemMessage(content=sys_prompt)] + list(history) + [HumanMessage(content=user_input)]
                response = self._llm.invoke(messages)
                reply = response.content if hasattr(response, "content") else str(response)
            except Exception as exc:
                logger.warning(f"LLM 调用失败，降级为占位回复: {exc}")
                reply = "抱歉，AI 服务暂时不可用，请稍后重试。"

        return {
            "conversation_history": [
                HumanMessage(content=user_input),
                AIMessage(content=reply),
            ]
        }

    # ------------------------------------------------------------------
    # S1 拆解（需求分析第一步：原料分层）
    # ------------------------------------------------------------------

    _SYSTEM_PROMPT_S1 = (
        "你是「方案高参」的需求分析引擎，正在执行 **S1 原料拆解**步骤。\n"
        "规则：只整理原始表达，不推断、不评价、不提建议。严谨、克制、零推断。\n\n"
        "输出格式（严格按此，不加其他标题或说明）：\n\n"
        "## S1 原料拆解\n\n"
        "**事实层**（可验证的客观信息：项目类型、地点、品牌、面积、交付物等）\n"
        "- （逐条列出，每条一行）\n\n"
        "**偏好层**（用户表达的倾向、风格参考、期望方向）\n"
        "- （逐条列出，每条一行）\n\n"
        "**初始边界**（已提及的限制条件、硬约束、不可触碰的前提）\n"
        "- （逐条列出；若原始表达中无明确约束，写「暂无明确约束」）\n\n"
        "---\n"
        "拆解完成后，用一句话指出：哪个层面信息最薄弱，是下一步需要优先补充的方向。"
    )

    def _run_s1_analysis(self, brief_text: str, session_id: str) -> str:
        """执行 S1 原料拆解：把原始 brief 分解为事实 / 偏好 / 初始边界三层"""
        if self._llm is None:
            return (
                "## S1 原料拆解\n\n"
                "（AI 服务暂未就绪，无法执行自动拆解。请重试或检查 LLM 配置。）"
            )
        try:
            messages = [
                SystemMessage(content=self._SYSTEM_PROMPT_S1),
                HumanMessage(content=brief_text),
            ]
            response = self._llm.invoke(messages)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as exc:
            logger.warning(f"[{session_id}] S1 拆解 LLM 调用失败: {exc}")
            return (
                "## S1 原料拆解\n\n"
                "（拆解暂时失败，请稍后重试。你也可以继续补充更多细节，我来帮你整理。）"
            )

    # S2：目标锁定
    _SYSTEM_PROMPT_S2 = (
        "你是「方案高参」的需求分析引擎，正在执行 **S2 目标锁定**步骤。\n"
        "基于对话历史中已提供的项目信息（S1 已完成三层拆解），提炼并锁定核心待解命题。\n"
        "规则：验证优先——先确认事实层是否支撑目标，再下潜挖掘隐性需求，最后冻结核心命题。\n\n"
        "输出格式（严格按此）：\n\n"
        "## S2 目标锁定\n\n"
        "**核心待解命题**（一句话：这个项目最终要解决/实现什么）\n\n"
        "**主要成功标准**（2-3 条可验证的结果指标）\n"
        "- ...\n\n"
        "**关键设计张力**（核心矛盾或取舍点，如「亲子体验 vs 极简风格」）\n"
        "- ...\n\n"
        "---\n"
        "最后一句话：指出目标锁定中最大的不确定性，或下一步 S3 战略框架预期要解决的核心矛盾。"
    )

    # S3：战略框架
    _SYSTEM_PROMPT_S3 = (
        "你是「方案高参」的需求分析引擎，正在执行 **S3 战略框架**步骤。\n"
        "基于 S2 锁定的核心命题，提供 2-3 个高质量战略方向。像董事会一样讨论：\n"
        "只谈方向、定位、取舍原则——不谈具体空间方案，不展开战术细节。\n\n"
        "输出格式（严格按此）：\n\n"
        "## S3 战略框架\n\n"
        "**方向 A — [方向名称]**\n"
        "- 核心定位：...\n"
        "- 主要取舍：...\n"
        "- 最适合：...\n\n"
        "**方向 B — [方向名称]**\n"
        "- 核心定位：...\n"
        "- 主要取舍：...\n"
        "- 最适合：...\n\n"
        "（如有，方向 C 同结构）\n\n"
        "---\n"
        "最后：建议优先考虑哪个方向，并说明理由（一句话）。等你确认战略方向后进入 S4 战术分解。"
    )

    # S4：战术分解
    _SYSTEM_PROMPT_S4 = (
        "你是「方案高参」的需求分析引擎，正在执行 **S4 战术分解**步骤。\n"
        "基于已确认的战略方向，作为总设计师将战略落地为各专题的可交接任务结构。\n"
        "规则：各专题如何响应战略——不重开战略讨论，只做降维翻译。\n\n"
        "输出格式（严格按此）：\n\n"
        "## S4 战术分解\n\n"
        "**空间规划专题**\n"
        "- 响应战略的核心任务：...\n"
        "- 关键决策点：...\n\n"
        "**材料与界面专题**\n"
        "- 响应战略的核心任务：...\n"
        "- 关键决策点：...\n\n"
        "**体验动线专题**\n"
        "- 响应战略的核心任务：...\n"
        "- 关键决策点：...\n\n"
        "（按项目类型增减专题，每个专题1-2条，不展开细节）\n\n"
        "---\n"
        "最后：哪个专题是关键路径，需要优先锁定。确认后进入 S5 任务书编译。"
    )

    # S5：形成成果
    _SYSTEM_PROMPT_S5 = (
        "你是「方案高参」的需求分析引擎，正在执行 **S5 形成成果**步骤。\n"
        "基于 S1-S4 的完整分析，编译为结构化的设计任务书草稿。严谨、闭环、可交接。\n\n"
        "输出格式（严格按此）：\n\n"
        "## S5 设计任务书草稿\n\n"
        "**项目基本信息**\n"
        "- 项目类型：...\n"
        "- 核心待解命题：...\n\n"
        "**战略方向**\n"
        "- 已确认方向：...\n"
        "- 核心取舍原则：...\n\n"
        "**各专题任务清单**\n"
        "- 空间规划：...\n"
        "- 材料与界面：...\n"
        "- 体验动线：...\n\n"
        "**待确认事项**（进入执行前需用户最终确认的内容）\n"
        "- ...\n\n"
        "---\n"
        "任务书草稿已生成。确认无误后可进入实施执行阶段；如需调整，请直接告诉我。"
    )

    _S_STEP_PROMPTS: Dict[str, str] = {}  # populated in __init_subclass__ below; see _get_s_step_prompt

    def _get_s_step_prompt(self, conv_s_step: str) -> tuple[str, str]:
        """返回 (system_prompt, next_conv_s_step) 对应于当前步骤状态"""
        mapping = {
            "s1_done": (self._SYSTEM_PROMPT_S2, "s2_done"),
            "s2_done": (self._SYSTEM_PROMPT_S3, "s3_done"),
            "s3_done": (self._SYSTEM_PROMPT_S4, "s4_done"),
            "s4_done": (self._SYSTEM_PROMPT_S5, "s5_done"),
        }
        return mapping.get(conv_s_step, (self._SYSTEM_PROMPT_S2, "s2_done"))

    def _run_s_step_analysis(
        self,
        conv_s_step: str,
        user_input: str,
        state: "ProjectAnalysisState",
        session_id: str,
    ) -> tuple[str, str]:
        """
        执行 S2-S5 需求分析步骤。
        返回 (reply_text, next_conv_s_step)。
        对话历史会注入给 LLM 以保持上下文。
        """
        system_prompt, next_step = self._get_s_step_prompt(conv_s_step)
        step_label = next_step.replace("_done", "").upper()

        if self._llm is None:
            return (
                f"## {step_label} 分析\n\n（AI 服务暂未就绪，无法执行分析。请重试。）",
                conv_s_step,
            )
        try:
            # 注入对话历史（最近 10 条），让 LLM 知道 S1 的分析结果
            history: List = state.get("conversation_history") or []
            recent = history[-10:] if len(history) > 10 else history
            messages = [SystemMessage(content=system_prompt)] + list(recent)
            if user_input.strip():
                messages.append(HumanMessage(content=user_input))
            response = self._llm.invoke(messages)
            reply = response.content if hasattr(response, "content") else str(response)
            return reply, next_step
        except Exception as exc:
            logger.warning(f"[{session_id}] {step_label} LLM 调用失败: {exc}")
            return (
                f"## {step_label} 分析\n\n（分析暂时失败，当前步骤未推进。请稍后重试或直接回复“继续”重试本步骤。）",
                conv_s_step,
            )

    # ------------------------------------------------------------------
    # 认知诊断（单次 LLM → 回复文本 + CognitionDiagnosis）
    # ------------------------------------------------------------------

    _SYSTEM_PROMPT_DIAGNOSE = (
        "你是「方案高参」，一位专注室内/建筑设计的资深顾问。\n"
        "在回应用户时，你需要同时输出回复文本和一个诊断JSON，格式严格如下：\n\n"
        "[REPLY]\n"
        "...你的回复（苏格拉底式，最多1～2个追问；project_signal意图≤100字；"
        "knowledge_qa/inspiration可放宽至200字）...\n"
        "[/REPLY]\n\n"
        "[DIAGNOSIS]\n"
        "{\n"
        "  \"intent\": \"knowledge_qa|inspiration|project_signal\",\n"
        "  \"gap_item\": \"预算\" 或 null,\n"
        "  \"fork_directions\": [\"方向A\", \"方向B\"] 或 null,\n"
        "  \"fork_consequences\": [\"后果A\", \"后果B\"] 或 null,\n"
        "  \"summary_ready\": true 或 false,\n"
        "  \"hypothesis_prompt\": \"...\" 或 null,\n"
        "  \"reply_hint\": \"本轮聚焦点（一句话）\"\n"
        "}\n"
        "[/DIAGNOSIS]\n\n"
        "规则：\n"
        "- intent 只能是三选一（knowledge_qa/inspiration/project_signal）\n"
        "- gap_item：只能填 [REPLY] 正文中你**明确追问**的那个参数名（如预算/面积/使用性质）；若 [REPLY] 没有追问任何参数，必须填 null\n"
        "- fork_directions：只能填 [REPLY] 中你**明确让用户选择**的方向列表；若 [REPLY] 没有提方向选择，必须填 null\n"
        "- summary_ready：已积累4+轮且核心参数趋于清晰时设为 true，否则 false\n"
        "- hypothesis_prompt：用户表达了假设性意图（如果…/假设…），提炼为一句话；否则 null\n"
        "- gap_item / fork_directions 必须与 [REPLY] 正文焦点保持一致，不能在 [REPLY] 聊别的却在这里填不同信息\n"
        "- 不要用###标题，保持对话感"
    )

    def _diagnose_cognition(
        self,
        user_input: str,
        state: ProjectAnalysisState,
        existing_drafts: List[Dict[str, Any]],
        session_id: str,
    ) -> tuple[str, CognitionDiagnosis]:
        """
        单次 LLM 调用，同时产出：回复文本 + 认知诊断。
        返回 (reply_text, CognitionDiagnosis)。
        无 LLM 时走规则兜底。
        """
        if self._llm is None:
            return self._fallback_diagnose(user_input)
        try:
            history = state.get("conversation_history") or []
            messages = [
                SystemMessage(content=self._SYSTEM_PROMPT_DIAGNOSE),
                *list(history),
                HumanMessage(content=user_input),
            ]
            response = self._llm.invoke(messages)
            raw_text = response.content if hasattr(response, "content") else str(response)
            return self._parse_diagnose_response(raw_text, user_input)
        except Exception as exc:
            logger.warning(f"[{session_id}] _diagnose_cognition LLM 调用失败，降级: {exc}")
            return self._fallback_diagnose(user_input)

    def _parse_diagnose_response(
        self, raw_text: str, user_input: str
    ) -> tuple[str, CognitionDiagnosis]:
        """解析 [REPLY]...[/REPLY] 和 [DIAGNOSIS]...json...[/DIAGNOSIS] 格式。
        同时兼容 LLM 误写的 [DIAGNOSTIC] 标签名。"""
        import re

        reply = ""
        diagnosis = self._fallback_diagnosis_obj(user_input)

        m_reply = re.search(r"\[REPLY\](.*?)\[/REPLY\]", raw_text, re.DOTALL)
        if m_reply:
            reply = m_reply.group(1).strip()
        else:
            # 若无 REPLY 标签，将整个文本视为回复（降级兼容）
            reply = raw_text.strip()

        # 兼容 [DIAGNOSIS] 和 LLM 误用的 [DIAGNOSTIC]
        m_diag = re.search(
            r"\[DIAGNOS(?:IS|TIC)\](.*?)\[/DIAGNOS(?:IS|TIC)\]", raw_text, re.DOTALL
        )
        if m_diag:
            try:
                parsed = json.loads(m_diag.group(1).strip())
                diagnosis = CognitionDiagnosis(
                    intent=parsed.get("intent", _INTENT_KNOWLEDGE_QA),
                    gap_item=parsed.get("gap_item"),
                    fork_directions=parsed.get("fork_directions"),
                    fork_consequences=parsed.get("fork_consequences"),
                    summary_ready=bool(parsed.get("summary_ready", False)),
                    hypothesis_prompt=parsed.get("hypothesis_prompt"),
                    reply_hint=parsed.get("reply_hint", ""),
                )
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                logger.debug(f"诊断 JSON 解析失败，用规则兜底: {exc}")
                diagnosis = self._fallback_diagnosis_obj(user_input)

        # 无论哪条路径，最终回复文本都不应含任何标签块
        reply = re.sub(
            r"\[(?:REPLY|DIAGNOS(?:IS|TIC))\].*?\[/(?:REPLY|DIAGNOS(?:IS|TIC))\]",
            "",
            reply,
            flags=re.DOTALL,
        ).strip()

        return reply or "已收到，请继续描述。", diagnosis

    def _fallback_diagnose(self, user_input: str) -> tuple[str, CognitionDiagnosis]:
        """无 LLM 时的规则兜底"""
        return "抱歉，AI 服务暂未就绪，请稍后再试。", self._fallback_diagnosis_obj(user_input)

    def _fallback_diagnosis_obj(
        self, user_input: str, intent: Optional[str] = None
    ) -> CognitionDiagnosis:
        if intent is None:
            intent = self._classify_intent(user_input)
        return CognitionDiagnosis(
            intent=intent,
            gap_item=None,
            fork_directions=None,
            fork_consequences=None,
            summary_ready=False,
            hypothesis_prompt=None,
            reply_hint="",
        )

    # ------------------------------------------------------------------
    # 草稿对象创建
    # ------------------------------------------------------------------

    def _create_intent_seed(self, text: str, session_id: str) -> Dict[str, Any]:
        seed = IntentSeed(
            content=text,
            keywords=self._extract_keywords(text),
            meta=DraftObjectMeta(
                source=session_id,
                user_confirmed=False,
                inferred=False,
                open_questions=[],
                upgrade_ready=False,
            ),
        )
        return {"draft_type": "IntentSeed", **seed.model_dump()}

    def _create_inspiration_draft(self, text: str, session_id: str) -> Dict[str, Any]:
        draft = DirectionCandidatePack(
            candidates=[{"description": text}],
            meta=DraftObjectMeta(
                source=session_id,
                user_confirmed=False,
                inferred=True,
            ),
        )
        return {"draft_type": "DirectionCandidatePack", **draft.model_dump()}

    def _append_draft(
        self, existing: List[Dict[str, Any]], new_draft: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        return existing + [new_draft]

    # ------------------------------------------------------------------
    # 三大认知指标估算
    # ------------------------------------------------------------------

    def _compute_cognition_indicators(
        self,
        current_input: str,
        drafts: List[Dict[str, Any]],
        state: ProjectAnalysisState,
    ) -> CognitionIndicators:
        """
        轻量规则估算三大认知指标。
        后续可替换为 LLM 评分版本。
        """
        history: List = state.get("conversation_history") or []
        total_rounds = len([m for m in history if hasattr(m, "type") and m.type == "human"])

        # 冻结准备度
        # ① 硬约束词（原有）
        hard_constraint_words = ("面积", "预算", "层高", "容积率", "红线")
        freeze_hits = sum(1 for w in hard_constraint_words if w in current_input)
        freeze_readiness = min(freeze_hits * 0.25, 1.0)

        # ② 直接完整简报检测：品牌/项目类型 + 地点 + 多交付物 + "完整"类词
        #    满足时将 freeze_readiness 提升至 0.9，触发单指标升级快速路径
        complete_brief_phrases = ("完整设计框架", "完整方案", "完整设计", "设计概念", "设计框架")
        deliverable_words = (
            "色彩", "家具", "空间尺度", "公共社交", "灯光", "材料", "立面",
            "平面", "动线", "软装", "硬装", "景观", "标识",
        )
        deliverable_hits = sum(1 for w in deliverable_words if w in current_input)
        has_complete_phrase = any(p in current_input for p in complete_brief_phrases)
        has_multi_deliverables = deliverable_hits >= 3
        # 同时满足：多交付物罗列 + 完整框架关键词
        if has_complete_phrase and has_multi_deliverables:
            freeze_readiness = 0.9

        # 认知债务：草稿中积累的未确认项数量
        unconfirmed = sum(
            1 for d in drafts if not d.get("meta", {}).get("user_confirmed", False)
        )
        cognitive_debt = min(unconfirmed * 0.15, 1.0)

        # 发散疲劳度：超过一定轮次且无新词汇出现
        diverge_fatigue = 0.0
        if total_rounds >= 6:
            diverge_fatigue = min((total_rounds - 4) * 0.1, 1.0)

        return CognitionIndicators(
            freeze_readiness=round(freeze_readiness, 2),
            cognitive_debt=round(cognitive_debt, 2),
            diverge_fatigue=round(diverge_fatigue, 2),
        )

    # ------------------------------------------------------------------
    # 升级软提示文案
    # ------------------------------------------------------------------

    def _build_upgrade_suggestion(
        self, user_input: str, indicators: CognitionIndicators
    ) -> str:
        # 直接完整 brief 路径——首条消息即为完整项目简报
        if indicators.freeze_readiness >= 0.85:
            return (
                "你提供的内容已经是一份完整的项目简报——品牌基调、场地背景、"
                "交付目标都很清晰。\n\n"
                "**建议进入项目模式**，我来先做 S1 拆解：把你的原始表达整理成"
                "「事实 / 偏好 / 初始边界」三层原料，然后逐步推进到需求分析框架。\n\n"
                "你确认开始吗？（也可以继续补充任何细节）"
            )
        # 渐进路径——多轮积累后的升级提示
        return (
            "我发现我们已经聊到了一些具体的限制条件（如面积、预算等），"
            "核心方向也开始变清晰。如果继续漫聊可能会打空转。"
            "建议我先帮你把当前的框架整理一下，确立一个正式的项目基线，继续吗？"
        )

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _extract_keywords(self, text: str) -> List[str]:
        """简单关键词提取（按空格+标点分割，过滤短词）"""
        import re

        tokens = re.split(r"[，。！？、\s]+", text)
        return [t for t in tokens if len(t) >= 2][:10]

    # ------------------------------------------------------------------
    # 引导卡片生成
    # ------------------------------------------------------------------

    def _maybe_generate_guidance_card(
        self,
        state: ProjectAnalysisState,
        current_drafts: List[Dict[str, Any]],
        diagnosis: CognitionDiagnosis,
    ) -> Optional[GuidanceCard]:
        """
        按优先级（gap > fork > mirror > hypothesis）生成引导卡片。
        完全由 CognitionDiagnosis 驱动，动态生成卡片标题与选项。
        """
        history: List = state.get("conversation_history") or []
        total_rounds = len([m for m in history if hasattr(m, "type") and m.type == "human"])

        # Gap 卡：诊断识别出缺失的关键参数
        if diagnosis["gap_item"]:
            gap = diagnosis["gap_item"]
            return GuidanceCard(
                card_id=f"gc-{uuid.uuid4().hex[:8]}",
                card_type=GuidanceCardType.GAP,
                title=f"补全：{gap}",
                prompt_text=f"我注意到还没有确定 **{gap}**，这里不定下来后续推演可能失准。请帮我补充：",
                options=[
                    GuidanceCardOption(id="a", label=f"说明{gap}", description=f"提供{gap}的具体数值或范围"),
                    GuidanceCardOption(id="b", label=f"{gap}暂时不定", description="先跳过，后续再确认"),
                    GuidanceCardOption(id="c", label="有其他优先项", description="有其他更需要先确定的事项"),
                ],
                allow_freetext=True,
                pages=[
                    GuidanceCardPage(
                        page_title=f"{gap}说明",
                        prompt_text=f"关于 {gap}，你有哪些限定？",
                        options=[
                            GuidanceCardOption(id="a", label=f"已有明确{gap}", description=f"{gap}已定，可以告诉我具体值"),
                            GuidanceCardOption(id="b", label=f"{gap}有范围", description="有大致区间但还没精确"),
                            GuidanceCardOption(id="c", label=f"{gap}待定", description="目前还无法确定"),
                        ],
                        allow_freetext=True,
                    ),
                ],
            )

        # Fork 卡：诊断识别出方向分叉
        if diagnosis["fork_directions"] and len(diagnosis["fork_directions"]) >= 2:
            directions = diagnosis["fork_directions"]
            consequences = diagnosis.get("fork_consequences") or []
            options = [
                GuidanceCardOption(
                    id=str(chr(ord("a") + i)),
                    label=directions[i],
                    description=directions[i],
                    consequence_hint=consequences[i] if i < len(consequences) else "沿此方向深化设计方案",
                )
                for i in range(min(len(directions), 4))
            ]
            return GuidanceCard(
                card_id=f"gc-{uuid.uuid4().hex[:8]}",
                card_type=GuidanceCardType.FORK,
                title="锁定方向",
                prompt_text="我看到这里出现了几个可能的方向，你更倾向于哪一个？",
                options=options,
                allow_freetext=True,
            )

        # Mirror 卡：诊断认为可以归纳
        if diagnosis["summary_ready"] and total_rounds >= 3:
            return GuidanceCard(
                card_id=f"gc-{uuid.uuid4().hex[:8]}",
                card_type=GuidanceCardType.MIRROR,
                title="阶段共识确认",
                prompt_text="我来归纳一下目前的共识，请确认这些要点是否准确：",
                options=[
                    GuidanceCardOption(id="a", label="是，准确", description="确认归纳内容，作为已达成共识记录", recommended=True),
                    GuidanceCardOption(id="b", label="有偏差", description="选此项后请说明哪里不准确"),
                ],
                allow_freetext=True,
            )

        # Hypothesis 卡：诊断识别出假设性意图
        if diagnosis["hypothesis_prompt"]:
            return GuidanceCard(
                card_id=f"gc-{uuid.uuid4().hex[:8]}",
                card_type=GuidanceCardType.HYPOTHESIS,
                title="设想探索",
                prompt_text=f"你提到「{diagnosis['hypothesis_prompt']}」——这是你想深入探索的方向吗？",
                options=[
                    GuidanceCardOption(id="a", label="是，深入探索", description="将此设想记为方向候选，继续展开", recommended=True),
                    GuidanceCardOption(id="b", label="只是随手一问", description="不需要记录，继续当前话题"),
                ],
                allow_freetext=False,
            )

        return None

    # ------------------------------------------------------------------
    # 处理卡片响应 → 草稿沉淀
    # ------------------------------------------------------------------

    def _process_card_response(
        self,
        state: ProjectAnalysisState,
        card_id: str,
        option_id: Optional[str],
        freetext: str,
        card_response: Optional[Dict[str, Any]],
        pending_card_raw: Dict[str, Any],
        session_id: str,
    ) -> Dict[str, Any]:
        """
        根据用户对引导卡片的选择，沉淀对应草稿对象，返回 state 更新 dict。
        卡片→草稿对象映射表（user_confirmed=True）：
          mirror     → ConsensusPack
          fork       → DirectionCandidatePack（已选）+ ConflictPack（已解）
          gap        → BoundaryDraft
          hypothesis → IntentSeed / ProblemFrameDraft
        """
        updates: Dict[str, Any] = {}
        existing_drafts: List[Dict[str, Any]] = state.get("conversation_drafts") or []
        existing_traces: List[Dict[str, Any]] = state.get("guidance_traces") or []

        card_type_raw: str = pending_card_raw.get("card_type", "")
        action: Literal["select", "skip", "rewrite", "supplement"] = (
            "select" if option_id or card_response else ("supplement" if freetext else "skip")
        )
        captured_signal = self._card_response_summary(card_response) if card_response else (freetext or option_id or "")
        promoted_type: Optional[str] = None

        meta = DraftObjectMeta(
            source=session_id,
            user_confirmed=True,
            inferred=False,
        )

        if action != "skip":
            if card_type_raw == GuidanceCardType.GAP.value:
                # Gap → BoundaryDraft
                # 支持多页：freetext 可能是分号分隔的多页选择汇总
                selected_labels = [
                    opt["label"]
                    for opt in pending_card_raw.get("options", [])
                    if opt.get("id") == option_id
                ]
                additional = [
                    s.strip() for s in (freetext or "").split(";") if s.strip()
                ] if freetext else []
                constraints = list(dict.fromkeys(selected_labels + additional)) or ([freetext] if freetext else [])
                draft = BoundaryDraft(hard_constraints=constraints, meta=meta)
                existing_drafts = self._append_draft(
                    existing_drafts, {"draft_type": "BoundaryDraft", **draft.model_dump()}
                )
                promoted_type = "BoundaryDraft"

            elif card_type_raw == GuidanceCardType.FORK.value:
                # Fork → DirectionCandidatePack + ConflictPack resolved
                selected_desc = next(
                    (
                        opt["description"]
                        for opt in pending_card_raw.get("options", [])
                        if opt.get("id") == option_id
                    ),
                    freetext or captured_signal,
                )
                dir_draft = DirectionCandidatePack(
                    candidates=[{"description": selected_desc}],
                    meta=meta,
                )
                existing_drafts = self._append_draft(
                    existing_drafts,
                    {"draft_type": "DirectionCandidatePack", **dir_draft.model_dump()},
                )
                conflict_draft = ConflictPack(
                    conflicts=[f"方向已选定：{selected_desc[:40]}"],
                    meta=meta,
                )
                existing_drafts = self._append_draft(
                    existing_drafts,
                    {"draft_type": "ConflictPack", **conflict_draft.model_dump()},
                )
                promoted_type = "DirectionCandidatePack"

            elif card_type_raw == GuidanceCardType.MIRROR.value:
                # Mirror → ConsensusPack（归纳共识）
                agreed_items = [
                    d.get("agreed_items", [])
                    for d in existing_drafts
                    if d.get("draft_type") == "ConsensusPack"
                ]
                flat_items: List[str] = [item for sub in agreed_items for item in sub]
                consensus = ConsensusPack(agreed_items=flat_items, meta=meta)
                existing_drafts = self._append_draft(
                    existing_drafts,
                    {"draft_type": "ConsensusPack", **consensus.model_dump()},
                )
                promoted_type = "ConsensusPack"

            elif card_type_raw == GuidanceCardType.HYPOTHESIS.value:
                # Hypothesis → IntentSeed（设想记录）
                hypothesis_text = freetext or captured_signal
                seed = IntentSeed(
                    content=hypothesis_text,
                    keywords=self._extract_keywords(hypothesis_text),
                    meta=meta,
                )
                existing_drafts = self._append_draft(
                    existing_drafts,
                    {"draft_type": "IntentSeed", **seed.model_dump()},
                )
                promoted_type = "IntentSeed"

        # 记录 GuidanceTrace
        trace = GuidanceTrace(
            trace_id=f"gt-{uuid.uuid4().hex[:8]}",
            card_id=card_id,
            card_type=GuidanceCardType(card_type_raw) if card_type_raw else GuidanceCardType.MIRROR,
            user_action=action,
            selected_option_id=option_id,
            freetext_input=freetext if freetext else None,
            captured_signal=captured_signal,
            promoted_to_draft_type=promoted_type,
            timestamp=datetime.now().isoformat(),
        )
        trace_data = trace.model_dump()
        if card_response:
            trace_data["card_response"] = card_response
        updates["conversation_drafts"] = existing_drafts
        updates["guidance_traces"] = existing_traces + [trace_data]
        return updates

    @staticmethod
    def _card_response_summary(card_response: Optional[Dict[str, Any]]) -> str:
        if not isinstance(card_response, dict):
            return ""
        lines: List[str] = []
        for page in card_response.get("pages") or []:
            if not isinstance(page, dict):
                continue
            title = str(page.get("page_title") or "").strip()
            selected = []
            for option in page.get("selected_options") or []:
                if not isinstance(option, dict):
                    continue
                label = str(option.get("label") or option.get("id") or "").strip()
                if not label:
                    continue
                priority = option.get("priority")
                selected.append(f"{priority}. {label}" if priority else label)
            if page.get("freetext"):
                selected.append(str(page.get("freetext")).strip())
            if selected:
                lines.append(f"{title}：{'、'.join(selected)}" if title else "、".join(selected))
        return "；".join(lines)
