# intelligent_project_analyzer/graph/observer.py
# Observer Intelligence Layer — 独立第三方方案认知中枢
# 职责：接收右侧生产环节产出，以资深顾问视角独立重新理解，不回写生产链路
# Copilot 生成 2026-03-15

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# 数据模型
# ─────────────────────────────────────────────────────────────────────────────

NODE_TYPES = {
    "purpose":      "项目目的/核心意图",
    "tension":      "矛盾/冲突张力",
    "strategy":     "策略/解法",
    "stakeholder":  "利益相关方/人群",
    "constraint":   "约束条件",
    "gap":          "缺口/盲区/未验证假设",
    "factor":       "关键因素",
    "insight":      "洞察/突破判断",
    "deliverable":  "落地载体/交付物",
}

EDGE_TYPES = {
    "conflicts":    "冲突/对立",
    "resolves":     "策略解决矛盾",
    "addresses":    "回应/服务于",
    "influences":   "影响/导致",
    "contains":     "包含/属于",
    "depends_on":   "依赖于",
    "constrains":   "约束",
    "derives":      "推导出洞察",
}


class ObserverNode(BaseModel):
    id: str
    label: str
    nodeType: str  # one of NODE_TYPES keys
    description: str  # 1-2 句独立判断，不复述
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ObserverEdge(BaseModel):
    source: str
    target: str
    relType: str   # one of EDGE_TYPES keys
    label: str     # 简短关系说明
    reasoning: str  # 为什么存在这条关系


class ObserverResult(BaseModel):
    nodes: List[ObserverNode] = Field(default_factory=list)
    edges: List[ObserverEdge] = Field(default_factory=list)
    main_insight: str = ""           # 最重要的一句独立判断
    key_contradictions: List[str] = Field(default_factory=list)  # 2-3 条核心冲突
    blind_spots: List[str] = Field(default_factory=list)         # 盲区/风险预警
    stage: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Prompt 构建
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """你是一位资深空间设计独立顾问，以第三方旁观视角审视项目分析。
你的职责不是复述内容，而是独立判断：
1. 这个项目真正要解决的核心问题是什么（不要重复用户说的，给出你的独立解读）
2. 提取关键结构节点（目的/人群/矛盾/策略/约束/缺口）及其关系
3. 指出当前分析最重要的盲区或风险（哪些假设未验证，哪些关键问题没有被覆盖）

节点类型说明：
- purpose: 项目真正意图（不是表面诉求）
- tension: 必须平衡的核心矛盾（两端对立）
- strategy: 解决矛盾的策略路径
- stakeholder: 利益相关方、使用人群
- constraint: 硬约束（预算/规范/运营/场地）
- gap: 盲区、缺口、未验证假设
- factor: 关键影响因素
- insight: 穿透性洞察（你独立得出的判断）
- deliverable: 落地手段、交付物

边类型：conflicts / resolves / addresses / influences / contains / depends_on / constrains / derives

注意事项：
- 节点 label 用简短词组（3-8字），不要长句
- description 用 1-2 句判断语，第一人称（"我认为..."），不是描述
- main_insight 必须是独立判断句，不能是"该项目涉及..."这类复述
- 每个 tension 节点都应有对应的 strategy 节点通过 resolves 边连接（若无策略则标记 gap）
- gap 节点描述要说明"缺少什么"以及"如果不解决会有什么风险"

输出严格 JSON，格式：
{
  "nodes": [{"id":"...","label":"...","nodeType":"...","description":"...","confidence":0.8}],
  "edges": [{"source":"...","target":"...","relType":"...","label":"...","reasoning":"..."}],
  "main_insight": "...",
  "key_contradictions": ["..."],
  "blind_spots": ["..."]
}"""


def _build_user_message(interrupt_data: Dict[str, Any], stage: str) -> str:
    """将 interrupt_data 整理为结构化分析上下文"""
    parts: List[str] = [f"[分析阶段] {stage}\n"]

    id_ = interrupt_data

    # 突破洞察（右侧产出的原始判断）
    insight = (
        id_.get("requirements_review", {}).get("breakthrough_insight")
        or id_.get("breakthrough_insight", "")
    )
    if insight:
        parts.append(f"[右侧产出的突破洞察]\n{insight}\n")

    # 核心张力（可能是 {name, implication} 对象或字符串）
    tensions_raw = (
        id_.get("requirements_review", {}).get("core_tensions")
        or id_.get("core_tensions", [])
    )
    if tensions_raw:
        tension_lines: List[str] = []
        for t in tensions_raw:
            if isinstance(t, dict):
                name = t.get("name") or t.get("tension", "")
                impl = t.get("implication") or t.get("design_implication", "")
                if name:
                    tension_lines.append(f"  - {name}" + (f"：{impl}" if impl else ""))
            elif isinstance(t, str) and t.strip():
                tension_lines.append(f"  - {t.strip()}")
        if tension_lines:
            parts.append("[已识别核心张力]\n" + "\n".join(tension_lines) + "\n")

    # 已识别维度
    identified = id_.get("already_identified", [])
    if identified:
        dim_lines: List[str] = []
        for d in identified:
            label = d if isinstance(d, str) else (d.get("name") or d.get("dimension") or "")
            if label:
                dim_lines.append(f"  - {label}")
        if dim_lines:
            parts.append("[已识别维度]\n" + "\n".join(dim_lines) + "\n")

    # 缺失信息
    missing = (
        id_.get("missing_information", [])
        or id_.get("requirements_review", {}).get("info_quality", {}).get("missing_dimensions", [])
    )
    if missing:
        miss_lines = [f"  - {m}" for m in missing if m]
        if miss_lines:
            parts.append("[识别到的信息缺口]\n" + "\n".join(miss_lines) + "\n")

    # 设计原则
    principles = id_.get("design_principles", [])
    if principles:
        parts.append("[设计原则]\n" + "\n".join(f"  - {p}" for p in principles) + "\n")

    # 用户原始输入（若在 interrupt_data 中）
    user_input = id_.get("user_input", "")
    if user_input:
        parts.append(f"[用户原始描述]\n{user_input[:500]}\n")

    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# 核心函数
# ─────────────────────────────────────────────────────────────────────────────

def run_observer(
    interrupt_data: Dict[str, Any],
    stage: str,
    llm: Any,
) -> ObserverResult:
    """
    以第三方顾问视角重新理解 interrupt_data，返回结构化图谱节点+洞见。
    纯只读，不写入任何生产状态。
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    user_msg = _build_user_message(interrupt_data, stage)

    try:
        response = llm.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])
        raw = response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        logger.error(f"[Observer] LLM 调用失败: {e}")
        return ObserverResult(stage=stage)

    # 提取 JSON（兼容 markdown code block 包裹）
    raw = raw.strip()
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if json_match:
        raw = json_match.group(1)
    elif raw.startswith("```"):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # 尝试找到第一个 { 到最后一个 }
        start = raw.find('{')
        end = raw.rfind('}')
        if start != -1 and end != -1:
            try:
                data = json.loads(raw[start:end + 1])
            except Exception:
                logger.error(f"[Observer] JSON 解析失败，raw={raw[:300]}")
                return ObserverResult(stage=stage)
        else:
            logger.error(f"[Observer] 无法从 LLM 响应中提取 JSON")
            return ObserverResult(stage=stage)

    # 构建结果（defensive，LLM 输出可能不完整）
    nodes: List[ObserverNode] = []
    for n in data.get("nodes", []):
        try:
            node_type = n.get("nodeType", "factor")
            if node_type not in NODE_TYPES:
                node_type = "factor"
            nodes.append(ObserverNode(
                id=str(n.get("id", f"obs_{len(nodes)}")),
                label=str(n.get("label", ""))[:30],
                nodeType=node_type,
                description=str(n.get("description", ""))[:200],
                confidence=float(n.get("confidence", 0.8)),
            ))
        except Exception:
            continue

    edges: List[ObserverEdge] = []
    node_ids = {n.id for n in nodes}
    for e in data.get("edges", []):
        try:
            src = str(e.get("source", ""))
            tgt = str(e.get("target", ""))
            if src not in node_ids or tgt not in node_ids:
                continue
            rel = e.get("relType", "influences")
            if rel not in EDGE_TYPES:
                rel = "influences"
            edges.append(ObserverEdge(
                source=src,
                target=tgt,
                relType=rel,
                label=str(e.get("label", rel))[:30],
                reasoning=str(e.get("reasoning", ""))[:200],
            ))
        except Exception:
            continue

    result = ObserverResult(
        nodes=nodes,
        edges=edges,
        main_insight=str(data.get("main_insight", ""))[:500],
        key_contradictions=[str(c)[:200] for c in data.get("key_contradictions", [])],
        blind_spots=[str(b)[:200] for b in data.get("blind_spots", [])],
        stage=stage,
    )

    logger.info(
        f"[Observer] 完成 stage={stage} | "
        f"nodes={len(nodes)} edges={len(edges)} | "
        f"insight={result.main_insight[:60]!r}"
    )
    return result
