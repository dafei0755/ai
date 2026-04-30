"""
Echo Card 节点 — S1 解构回显卡

Copilot 生成（2026-03-17）

将 S1 输入解构的结果以"归纳确认卡"（card_type="echo"）的形式出示给用户：
  - 系统先出牌：展示对用户输入的完整理解（各维度预填值 + 来源标注）
  - 用户后校准：Confirm / Edit / Add / Defer 四种标准动作
  - 响应写回：将用户覆盖值合并进 s1_v2_snapshot

流程：
  1. 从 s1_v1_snapshot 构建 CandidateCard（status=candidate）
  2. 转换为前端兼容的 GuidanceCard 格式，写入 pending_guidance_card
  3. 等待用户通过 guidance_traces 写回响应
  4. 消费响应 → 更新 echo_card 为 confirmed 状态
  5. 将 user_overrides 合并 → 写入 s1_v2_snapshot
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.core.domain_objects import (
    CandidateCard,
    CandidateField,
    CardAction,
    CardStatus,
    S1Snapshot,
)
from intelligent_project_analyzer.core.state import ProjectAnalysisState

# 维度中文映射
_DIM_LABELS: Dict[str, str] = {
    "functional": "功能需求",
    "spatial": "空间条件",
    "aesthetic": "风格审美",
    "technical": "技术约束",
    "budget": "预算条件",
    "time": "工期要求",
}


class EchoCardNode:
    """
    Echo Card 节点（L2 协作层入口）。

    两段式执行：
    - execute_build()  —— 从 s1_v1_snapshot 构建并写出 Echo Card（第一轮）
    - execute_consume() —— 消费 guidance_traces 中的用户响应，写入 s1_v2_snapshot（第二轮）

    LangGraph 注册示例（ENABLE_DUAL_MODE_V2）：
        echo_build   = EchoCardNode()
        echo_consume = EchoCardNode()
        graph.add_node("requirements_echo_card_build",   echo_build.execute_build)
        graph.add_node("requirements_echo_card_consume", echo_consume.execute_consume)
    """

    # ------------------------------------------------------------------
    # 阶段一：构建并出示 Echo Card
    # ------------------------------------------------------------------

    def execute_build(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        session_id: str = state.get("session_id", "unknown")
        logger.info(f"[{session_id}] EchoCard BUILD 开始")

        s1_v1: Optional[Dict[str, Any]] = state.get("s1_v1_snapshot")
        if not s1_v1:
            logger.warning(f"[{session_id}] s1_v1_snapshot 为空，跳过 Echo Card 构建")
            return {
                "s1_v3_complete": False,
                "updated_at": datetime.now().isoformat(),
            }

        card = self._build_echo_card(s1_v1)
        guidance_card_payload = self._to_guidance_card_payload(card)

        logger.info(
            f"[{session_id}] EchoCard BUILD 完成 — "
            f"字段数={len(card.fields)}, card_id={card.card_id}"
        )

        return {
            "echo_card": card.model_dump(),
            "pending_guidance_card": guidance_card_payload,
            "updated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # 阶段二：消费用户响应，生成 s1_v2_snapshot
    # ------------------------------------------------------------------

    def execute_consume(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        session_id: str = state.get("session_id", "unknown")
        logger.info(f"[{session_id}] EchoCard CONSUME 开始")

        echo_card_raw: Optional[Dict[str, Any]] = state.get("echo_card")
        if not echo_card_raw:
            logger.warning(f"[{session_id}] echo_card 为空，跳过 CONSUME")
            return {"updated_at": datetime.now().isoformat()}

        echo_card = CandidateCard(**echo_card_raw)

        # 读取 guidance_traces 中针对本 echo card 的最新响应
        traces: List[Dict[str, Any]] = state.get("guidance_traces") or []
        user_response = self._find_response(traces, echo_card.card_id)

        # 解析用户动作和覆盖值
        action, user_overrides = self._parse_response(user_response, echo_card)

        # 更新 echo_card 为 confirmed
        echo_card.status = CardStatus.CONFIRMED
        echo_card.action = action.value if action else CardAction.CONFIRM.value
        echo_card.responded_at = datetime.now().isoformat()

        # 更新被编辑的字段
        for field in echo_card.fields:
            override = user_overrides.get(field.field_id)
            if override:
                field.user_value = override

        # 生成 s1_v2_snapshot（= v1 基础 + 用户覆盖）
        s1_v1: Dict[str, Any] = state.get("s1_v1_snapshot") or {}
        s1_v2 = S1Snapshot(
            version="v2",
            dimension_slices=dict(s1_v1.get("dimension_slices", {})),
            open_gaps=list(s1_v1.get("open_gaps", [])),
            prefill_hints=dict(s1_v1.get("prefill_hints", {})),
            snapshot_at=datetime.now().isoformat(),
            user_overrides=user_overrides,
        )

        # 用 user_overrides 覆盖对应维度切片
        for field_id, new_val in user_overrides.items():
            # field_id 形如 "dim_functional" → 维度 key 为 "functional"
            dim = field_id.replace("dim_", "")
            if dim in s1_v2.dimension_slices:
                s1_v2.dimension_slices[dim] = new_val

        logger.info(
            f"[{session_id}] EchoCard CONSUME 完成 — "
            f"action={echo_card.action}, overrides={len(user_overrides)}"
        )

        return {
            "echo_card": echo_card.model_dump(),
            "s1_v2_snapshot": s1_v2.model_dump(),
            "pending_guidance_card": None,  # 清空，防止前端重复显示
            "updated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _build_echo_card(self, s1_v1: Dict[str, Any]) -> CandidateCard:
        dim_slices: Dict[str, str] = s1_v1.get("dimension_slices", {})
        open_gaps: List[str] = s1_v1.get("open_gaps", [])

        fields: List[CandidateField] = []
        for dim, snippet in dim_slices.items():
            if not snippet:
                continue
            fields.append(
                CandidateField(
                    field_id=f"dim_{dim}",
                    key=_DIM_LABELS.get(dim, dim),
                    value=snippet,
                    source_ref=f"来自你的描述: {snippet[:40]}...",
                    inferred=True,
                )
            )

        # 缺口字段（标注推测）
        for i, gap in enumerate(open_gaps[:3]):
            fields.append(
                CandidateField(
                    field_id=f"gap_{i}",
                    key=f"待补充项 {i + 1}",
                    value=f"[未明确] {gap}",
                    source_ref="门禁诊断出的信息缺口",
                    inferred=True,
                )
            )

        return CandidateCard(
            card_id=f"echo-{uuid.uuid4().hex[:8]}",
            card_type="echo",
            title="这是我对你项目的理解——请确认或修正",
            summary=(
                "以下是根据你的描述提炼出的关键信息。"
                "每个字段来自你的原话（标注了来源）。"
                "如有偏差，请点击字段直接修改；确认准确请点击【全部确认】。"
            ),
            fields=fields,
            status=CardStatus.CANDIDATE,
            created_at=datetime.now().isoformat(),
        )

    def _to_guidance_card_payload(self, card: CandidateCard) -> Dict[str, Any]:
        """将 CandidateCard 转换为前端 GuidanceCard 格式（兼容现有渲染器）。"""
        # 每个字段对应一个选项；前端 CandidateCard 组件通过 fields 字段做特殊渲染
        options = [
            {
                "id": f.field_id,
                "label": f.key,
                "description": f.value,
                "consequence_hint": f.source_ref,
                "recommended": not f.inferred,
            }
            for f in card.fields
        ]
        return {
            "card_id": card.card_id,
            "card_type": "candidate",  # 前端使用 CandidateCard 渲染器
            "title": card.title,
            "prompt_text": card.summary,
            "options": options,
            "allow_freetext": True,
            # 扩展字段：原始 CandidateCard 数据，供 CandidateCard 组件使用
            "candidate_fields": [f.model_dump() for f in card.fields],
            "card_status": card.status.value,
        }

    @staticmethod
    def _find_response(
        traces: List[Dict[str, Any]], card_id: str
    ) -> Optional[Dict[str, Any]]:
        """在 guidance_traces 中查找针对该卡片的最新用户响应。"""
        for trace in reversed(traces):
            if trace.get("card_id") == card_id:
                return trace
        return None

    @staticmethod
    def _parse_response(
        response: Optional[Dict[str, Any]],
        card: CandidateCard,
    ) -> tuple[Optional[CardAction], Dict[str, str]]:
        """解析用户响应，返回 (action, field_overrides)。"""
        if not response:
            # 无响应 → 视为默认 Confirm（用户点击"继续"）
            return CardAction.CONFIRM, {}

        action_str: str = response.get("action", CardAction.CONFIRM.value)
        try:
            action = CardAction(action_str)
        except ValueError:
            action = CardAction.CONFIRM

        # 字段覆盖值：response["field_edits"] = {"dim_functional": "新值", ...}
        field_edits: Dict[str, str] = response.get("field_edits", {})

        # 若用户只提供了 freetext（Add 动作），追加到 open_gaps
        freetext: str = response.get("freetext", "")
        if freetext and action == CardAction.ADD:
            # freetext 归入第一个 gap_ 字段或新建
            gap_field_id = f"gap_user_{uuid.uuid4().hex[:4]}"
            field_edits[gap_field_id] = freetext

        return action, field_edits
