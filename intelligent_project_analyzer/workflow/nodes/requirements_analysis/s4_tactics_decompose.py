"""
S4 战术分解节点

Copilot 生成（2026-03-15）

输入: state.strategy_framework + state.locked_goals
输出:
  - tactical_breakdown: 专家分工 + 交付物 DAG 草案

核心处理：
  1. 从 strategy_framework.strategy_zones.frozen 推导必须交付的成果项
  2. 从 expanded 区推导可选探索项
  3. 按设计专业分配专家角色（architect / structural / mep / landscape / interior）
  4. 构建交付物依赖 DAG（DAGNode 列表）
  5. 置入 ReviewGate（每个主节点后插入一个质量门）
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from intelligent_project_analyzer.core.domain_objects import DAGNode, ReviewGate
from intelligent_project_analyzer.core.state import ProjectAnalysisState


_ROLE_KEYWORD_MAP: Dict[str, List[str]] = {
    "architect": ["平面", "立面", "剖面", "体量", "建筑", "空间", "功能"],
    "structural": ["结构", "荷载", "钢", "混凝土", "基础"],
    "mep": ["设备", "暖通", "机电", "给排水", "消防", "电气"],
    "landscape": ["景观", "园林", "绿化", "铺装", "户外"],
    "interior": ["室内", "装修", "软装", "材质", "色彩"],
    "cost_estimator": ["预算", "造价", "成本", "费用", "估算"],
}

_DELIVERABLE_TEMPLATES: List[Dict[str, Any]] = [
    {"name": "概念方案报告", "role": "architect", "depends_on": []},
    {"name": "平面布局方案", "role": "architect", "depends_on": ["概念方案报告"]},
    {"name": "结构选型意见", "role": "structural", "depends_on": ["平面布局方案"]},
    {"name": "机电概念方案", "role": "mep", "depends_on": ["平面布局方案"]},
    {"name": "初步预算估算", "role": "cost_estimator", "depends_on": ["平面布局方案"]},
    {"name": "最终设计汇总", "role": "architect", "depends_on": ["结构选型意见", "机电概念方案", "初步预算估算"]},
]


class S4TacticsDecomposeNode:
    """
    S4 战术分解节点。

    LangGraph 注册示例：
        s4 = S4TacticsDecomposeNode()
        graph.add_node("requirements_s4", s4.execute)
    """

    def execute(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        session_id: str = state.get("session_id", "unknown")
        logger.info(f"[{session_id}] S4 战术分解开始")

        strategy: Optional[Dict[str, Any]] = state.get("strategy_framework") or {}
        zones: Dict[str, Any] = strategy.get("strategy_zones", {})
        frozen_items: List[str] = zones.get("frozen", [])
        expanded_items: List[str] = zones.get("expanded", [])
        locked_goals: List[Dict[str, Any]] = state.get("locked_goals") or []

        # ── 角色分配 ───────────────────────────────────────────────────
        expert_responsibility = self._assign_roles(frozen_items + expanded_items)

        # ── 交付物 DAG ────────────────────────────────────────────────
        dag_nodes = self._build_dag(frozen_items, expanded_items, locked_goals)

        # ── 审阅门 ────────────────────────────────────────────────────
        review_gates = self._insert_review_gates(dag_nodes)

        tactical_breakdown: Dict[str, Any] = {
            "expert_responsibility": expert_responsibility,
            "deliverable_dag": [n.model_dump() for n in dag_nodes],
            "review_gates": [g.model_dump() for g in review_gates],
            "decomposed_at": datetime.now().isoformat(),
        }

        logger.info(
            f"[{session_id}] S4 完成 — "
            f"DAG节点={len(dag_nodes)}, 审阅门={len(review_gates)}, "
            f"专家角色={list(expert_responsibility.keys())}"
        )

        return {
            "tactical_breakdown": tactical_breakdown,
            "updated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------

    def _assign_roles(self, items: List[str]) -> Dict[str, List[str]]:
        responsibility: Dict[str, List[str]] = {role: [] for role in _ROLE_KEYWORD_MAP}
        combined = " ".join(items)
        for role, keywords in _ROLE_KEYWORD_MAP.items():
            for kw in keywords:
                if kw in combined:
                    responsibility[role].append(f"负责含 '{kw}' 相关任务")
                    break
        return {k: v for k, v in responsibility.items() if v}

    def _build_dag(
        self,
        frozen: List[str],
        expanded: List[str],
        goals: List[Dict[str, Any]],
    ) -> List[DAGNode]:
        nodes: List[DAGNode] = []

        # 使用模板为基础，按冻结项数量决定节点规模
        scale = min(len(frozen) + 2, len(_DELIVERABLE_TEMPLATES))
        for i, tmpl in enumerate(_DELIVERABLE_TEMPLATES[:scale]):
            node = DAGNode(
                node_id=f"D{i + 1:02d}",
                name=tmpl["name"],
                owner_role=tmpl["role"],
                depends_on=tmpl["depends_on"],
                success_criteria=["完整输出", "通过内部评审"],
            )
            nodes.append(node)

        return nodes

    def _insert_review_gates(self, dag_nodes: List[DAGNode]) -> List[ReviewGate]:
        gates: List[ReviewGate] = []
        # 在每个主节点（无依赖节点完成后）插入质量门
        for node in dag_nodes:
            if not node.depends_on:  # 入口节点后插入 human confirm 门
                gates.append(ReviewGate(
                    gate_id=f"RG_{node.node_id}",
                    after_node_id=node.node_id,
                    gate_type="human_confirm",
                    description=f"人工确认 '{node.name}' 符合项目基线",
                ))
            elif len(node.depends_on) >= 2:  # 汇聚节点后插入质量门
                gates.append(ReviewGate(
                    gate_id=f"RG_{node.node_id}",
                    after_node_id=node.node_id,
                    gate_type="quality",
                    description=f"质量审阅 '{node.name}'",
                ))
        return gates
