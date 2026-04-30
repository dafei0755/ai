"""
缺口补全节点 — Gap Completion (0..n 轮循环)

Copilot 生成（2026-03-17）

在 S2 目标锁定后，对所有 status="pending_input" 的目标逐轮生成候选卡片，
直至所有缺口被用户填写或推迟，随后设置 s1_v3_complete=True 放行 S3。

每一轮流程：
  1. 扫描 locked_goals 中 status="pending_input" 的记录（最多 3 条合并为 1 张卡）
  2. 生成 gap 候选卡，写入 pending_guidance_card
  3. 等待用户写回 guidance_traces
  4. 消费响应，更新对应 locked_goals 字段
  5. 若无剩余 pending_input → s1_v3_complete=True，gap_completion_count 停止递增

路由约束（在 main_workflow.py 中配置）：
    - "need_more_gaps"  →  继续回到本节点（继续轮询）
    - "gaps_complete"   →  路由到 requirements_s3

    router 函数：
        def _gap_router(state):
            if state.get("s1_v3_complete"):
                return "gaps_complete"
            return "need_more_gaps"
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from intelligent_project_analyzer.core.domain_objects import (
    CandidateCard,
    CandidateField,
    CardAction,
    CardStatus,
    GapCompletionRound,
    S1Snapshot,
)
from intelligent_project_analyzer.core.state import ProjectAnalysisState

# 每张候选卡最多覆盖的缺口字段数
_MAX_FIELDS_PER_CARD = 3

# 每个会话最多补全轮次（防止无限循环）
_MAX_ROUNDS = 5


def should_run_gap_completion(state: ProjectAnalysisState) -> bool:
    """静态检查：是否需要进入缺口补全循环。"""
    if state.get("s1_v3_complete"):
        return False
    goals: List[Dict[str, Any]] = state.get("locked_goals") or []
    return any(g.get("status") == "pending_input" for g in goals)


class GapCompletionNode:
    """
    缺口补全节点（条件循环）。

    两段式执行（与 EchoCardNode 类似）：
    - execute_build()   —— 构建并出示缺口候选卡
    - execute_consume() —— 消费用户响应，更新 locked_goals

    LangGraph 注册示例：
        gap_build   = GapCompletionNode()
        gap_consume = GapCompletionNode()
        graph.add_node("requirements_gap_build",   gap_build.execute_build)
        graph.add_node("requirements_gap_consume", gap_consume.execute_consume)

        # 条件路由（在 gap_consume 之后）
        graph.add_conditional_edges(
            "requirements_gap_consume",
            lambda s: "gaps_complete" if s.get("s1_v3_complete") else "need_more_gaps",
            {"need_more_gaps": "requirements_gap_build", "gaps_complete": "requirements_s3"},
        )
    """

    # ------------------------------------------------------------------
    # 阶段一：构建缺口候选卡
    # ------------------------------------------------------------------

    def execute_build(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        session_id: str = state.get("session_id", "unknown")
        count: int = state.get("gap_completion_count") or 0
        logger.info(f"[{session_id}] GapCompletion BUILD 第 {count + 1} 轮")

        # 防无限循环
        if count >= _MAX_ROUNDS:
            logger.warning(
                f"[{session_id}] 缺口补全已到达最大轮次 {_MAX_ROUNDS}，强制放行 S3"
            )
            return {
                "s1_v3_complete": True,
                "pending_guidance_card": None,
                "updated_at": datetime.now().isoformat(),
            }

        goals: List[Dict[str, Any]] = list(state.get("locked_goals") or [])
        pending = [g for g in goals if g.get("status") == "pending_input"]

        if not pending:
            # 无需补全 → 直接完成
            logger.info(f"[{session_id}] 无待补全缺口，s1_v3_complete=True")
            return {
                "s1_v3_complete": True,
                "pending_guidance_card": None,
                "updated_at": datetime.now().isoformat(),
            }

        # 取本轮处理的缺口（最多 _MAX_FIELDS_PER_CARD 条）
        this_batch = pending[:_MAX_FIELDS_PER_CARD]
        card = self._build_gap_card(this_batch, count + 1)
        guidance_payload = self._to_guidance_card_payload(card)

        # 记录本轮
        round_record = GapCompletionRound(
            round_index=count + 1,
            gap_descriptions=[g.get("description", "") for g in this_batch],
            candidate_card_id=card.card_id,
        )

        return {
            "candidate_cards": [card.model_dump()],
            "pending_guidance_card": guidance_payload,
            "gap_completion_rounds": [round_record.model_dump()],
            "gap_completion_count": count + 1,
            "updated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # 阶段二：消费用户响应，更新 locked_goals
    # ------------------------------------------------------------------

    def execute_consume(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        session_id: str = state.get("session_id", "unknown")
        logger.info(f"[{session_id}] GapCompletion CONSUME 开始")

        candidate_cards_raw: List[Dict[str, Any]] = state.get("candidate_cards") or []
        if not candidate_cards_raw:
            logger.warning(f"[{session_id}] 无 candidate_cards，跳过 CONSUME")
            return {"updated_at": datetime.now().isoformat()}

        # 取最新一张卡
        latest_card = CandidateCard(**candidate_cards_raw[-1])
        traces: List[Dict[str, Any]] = state.get("guidance_traces") or []
        response = self._find_response(traces, latest_card.card_id)
        action, field_fills = self._parse_response(response, latest_card)

        # 更新卡片状态
        latest_card.status = CardStatus.CONFIRMED
        latest_card.action = action.value
        latest_card.responded_at = datetime.now().isoformat()

        # 把用户填写的值同步回 locked_goals
        goals: List[Dict[str, Any]] = list(state.get("locked_goals") or [])
        updated_goals = self._apply_fills(goals, latest_card.fields, field_fills, action)

        # 检查是否仍有待补全缺口
        remaining = [g for g in updated_goals if g.get("status") == "pending_input"]
        complete = len(remaining) == 0

        # 同步更新 s1_v2_snapshot（如已存在则追加覆盖）
        s1_v2_raw: Optional[Dict[str, Any]] = state.get("s1_v2_snapshot")
        if s1_v2_raw:
            s1_v2 = S1Snapshot(**s1_v2_raw)
            # 把用户补全的缺口信息合并进 open_gaps（从中移除已解决的）
            resolved = {f.field_id for f in latest_card.fields if f.field_id in field_fills}
            s1_v2.open_gaps = [
                g for g in s1_v2.open_gaps
                if not any(f.value in g for f in latest_card.fields if f.field_id in resolved)
            ]
            s1_v2.snapshot_at = datetime.now().isoformat()
            s1_v2_out = s1_v2.model_dump()
        else:
            s1_v2_out = None

        if complete:
            logger.info(f"[{session_id}] 所有缺口已补全，s1_v3_complete=True")

        result: Dict[str, Any] = {
            "locked_goals": updated_goals,
            "candidate_cards": [latest_card.model_dump()],
            "pending_guidance_card": None,
            "updated_at": datetime.now().isoformat(),
        }
        if complete:
            result["s1_v3_complete"] = True
        if s1_v2_out:
            result["s1_v2_snapshot"] = s1_v2_out

        return result

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _build_gap_card(
        pending_goals: List[Dict[str, Any]], round_index: int
    ) -> CandidateCard:
        fields: List[CandidateField] = []
        for i, goal in enumerate(pending_goals):
            desc: str = goal.get("description", f"缺口项 {i + 1}")
            fields.append(
                CandidateField(
                    field_id=f"gap_r{round_index}_{i}",
                    key=desc.replace("[待补全] ", ""),
                    value="",
                    source_ref="门禁诊断时发现的信息缺口",
                    inferred=False,  # 明确标注为需要用户填写
                )
            )

        return CandidateCard(
            card_id=f"gap-{uuid.uuid4().hex[:8]}",
            card_type="gap",
            title=f"还有 {len(pending_goals)} 项信息需要你补充（第 {round_index} 轮）",
            summary=(
                "以下信息暂时未能从你的描述中找到，"
                "请填写或选择最接近的描述；如暂时无法确定，可点击「先跳过」。"
            ),
            fields=fields,
            status=CardStatus.CANDIDATE,
            created_at=datetime.now().isoformat(),
        )

    @staticmethod
    def _to_guidance_card_payload(card: CandidateCard) -> Dict[str, Any]:
        """转换为前端 GuidanceCard 格式（candidate 类型）。"""
        options = [
            {
                "id": f.field_id,
                "label": f.key,
                "description": f.value or "（请在此填写）",
                "consequence_hint": f.source_ref,
                "recommended": False,
            }
            for f in card.fields
        ]
        return {
            "card_id": card.card_id,
            "card_type": "candidate",
            "title": card.title,
            "prompt_text": card.summary,
            "options": options,
            "allow_freetext": True,
            "candidate_fields": [f.model_dump() for f in card.fields],
            "card_status": card.status.value,
            "gap_round": True,
        }

    @staticmethod
    def _find_response(
        traces: List[Dict[str, Any]], card_id: str
    ) -> Optional[Dict[str, Any]]:
        for trace in reversed(traces):
            if trace.get("card_id") == card_id:
                return trace
        return None

    @staticmethod
    def _parse_response(
        response: Optional[Dict[str, Any]],
        card: CandidateCard,
    ) -> Tuple[CardAction, Dict[str, str]]:
        if not response:
            return CardAction.DEFER, {}

        action_str = response.get("action", CardAction.DEFER.value)
        try:
            action = CardAction(action_str)
        except ValueError:
            action = CardAction.DEFER

        field_fills: Dict[str, str] = {}
        # field_edits: {"gap_r1_0": "用户填写的内容"}
        field_fills.update(response.get("field_edits", {}))

        # 通用 freetext 作为补充，追加进 field_fills（使用 freetext 键）
        freetext: str = response.get("freetext", "")
        if freetext:
            field_fills["freetext_supplement"] = freetext

        return action, field_fills

    @staticmethod
    def _apply_fills(
        goals: List[Dict[str, Any]],
        fields: List[CandidateField],
        field_fills: Dict[str, str],
        action: CardAction,
    ) -> List[Dict[str, Any]]:
        """将用户填写的值应用到对应的 locked_goals 记录。"""
        # 建立 field_id → goal 的映射（基于 field.key 与 goal description 匹配）
        field_key_set = {f.key for f in fields}

        updated: List[Dict[str, Any]] = []
        for goal in goals:
            if goal.get("status") != "pending_input":
                updated.append(goal)
                continue

            desc: str = goal.get("description", "")
            matched_key = None
            for f in fields:
                if f.key in desc or desc in f.key:
                    matched_key = f.field_id
                    break

            if matched_key is None:
                updated.append(goal)
                continue

            fill_val: str = field_fills.get(matched_key, "")
            if fill_val:
                goal = dict(goal)
                goal["description"] = fill_val.replace("[待补全] ", "")
                goal["status"] = "locked"
            elif action == CardAction.DEFER:
                # 推迟：保留 pending_input 但添加 defer 标注
                goal = dict(goal)
                goal["defer_noted"] = True
                # 推迟的字段在最终冻结时标注 [待定]
            updated.append(goal)

        return updated
