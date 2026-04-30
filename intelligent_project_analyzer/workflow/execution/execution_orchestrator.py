"""
实施执行调度器

Copilot 生成（2026-03-15）

职责：
  接受已冻结的 DesignTaskBook + ExecutionBlueprint，
  按交付物 DAG 的拓扑顺序将任务分批派发给专家角色（Agent），
  并在每批次完成后经过 ReviewGate（若有）决定继续/回流。

运行模式：
  - 轻量规则模式（默认）：无 LLM，基于 DAG 顺序串行调用
  - LLM 增强模式（可选）：每批次结果由 LLM 质量预判

DAG 执行策略：
  1. 拓扑排序 → 批次化（同一层的节点并发 / 此处串行占位）
  2. 每个 DAGNode 对应一次 _execute_dag_node() 调用
  3. ReviewGate 插入在标记节点后：rejected → 回退最近冻结前驱
  4. 所有节点完成 → 输出 stage_deliverables 列表

与现有批次执行的关系：
  - 不替换 batch_executor / batch_aggregator（现有主链保留）
  - 本模块是 v2.0 项目态主链中的新实施执行节点，通过
    feature flag ENABLE_DUAL_MODE_V2 选择挂载到图中
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Tuple

from loguru import logger

from intelligent_project_analyzer.core.domain_objects import (
    DAGNode,
    ExecutionBlueprint,
    ReviewGate,
)
from intelligent_project_analyzer.core.state import ProjectAnalysisState


# ---------------------------------------------------------------------------
# 技能 → 动作 映射表（A/B/C/D 四级门禁）
# ---------------------------------------------------------------------------

_SKILL_GATE_LEVEL: Dict[str, str] = {
    "evidence": "B",        # 外部取证，自动但强审计
    "reasoning": "A",       # 安全认知，自动
    "generation": "C",      # 高成本生成，预设配额
    "transformation": "A",  # 转换，安全
    "review": "A",          # 审阅，安全
    "execution_control": "D",  # 阻断级，需人工确认
}

_DEFAULT_BUDGET_PER_ROLE = 5   # 每个角色默认最多调用次数


# ---------------------------------------------------------------------------
# ExecutionOrchestrator
# ---------------------------------------------------------------------------


class ExecutionOrchestrator:
    """
    实施执行调度器。

    LangGraph 注册示例：
        orchestrator = ExecutionOrchestrator()
        graph.add_node("execution_orchestrator", orchestrator.execute)
    """

    def __init__(self, llm: Optional[Any] = None) -> None:
        self._llm = llm

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def execute(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        实施执行主逻辑。

        前提: state.requirements_frozen == True
              state.execution_blueprint 已设置
              state.design_task_book 已设置
        """
        session_id: str = state.get("session_id", "unknown")
        logger.info(f"[{session_id}] ExecutionOrchestrator 开始")

        # ── 前置检查 ──────────────────────────────────────────────────
        if not state.get("requirements_frozen"):
            logger.warning(f"[{session_id}] requirements_frozen=False，拒绝执行")
            return {
                "execution_error": "需求基线未冻结，禁止启动实施执行",
                "updated_at": datetime.now().isoformat(),
            }

        blueprint_raw: Optional[Dict[str, Any]] = state.get("execution_blueprint")
        taskbook_raw: Optional[Dict[str, Any]] = state.get("design_task_book")
        if not blueprint_raw or not taskbook_raw:
            logger.warning(f"[{session_id}] blueprint 或 taskbook 为空，中止执行")
            return {
                "execution_error": "ExecutionBlueprint 或 DesignTaskBook 缺失",
                "updated_at": datetime.now().isoformat(),
            }

        blueprint = ExecutionBlueprint(**blueprint_raw)
        budget_guard: Dict[str, int] = blueprint.budget_guard or {}

        # ── 拓扑排序 ─────────────────────────────────────────────────
        ordered_batches = list(self._topo_batches(blueprint.deliverable_dag))
        total = sum(len(b) for b in ordered_batches)
        logger.info(f"[{session_id}] DAG 共 {total} 节点，分 {len(ordered_batches)} 批")

        # ── 按批次执行 ────────────────────────────────────────────────
        stage_deliverables: List[Dict[str, Any]] = []
        review_log: List[Dict[str, Any]] = []
        call_counts: Dict[str, int] = {}
        execution_halted = False

        for batch_idx, batch in enumerate(ordered_batches):
            if execution_halted:
                break

            batch_results = []
            for dag_node in batch:
                # 预算熔断
                role = dag_node.owner_role
                limit = budget_guard.get(role, _DEFAULT_BUDGET_PER_ROLE)
                call_counts[role] = call_counts.get(role, 0) + 1
                if call_counts[role] > limit:
                    logger.warning(
                        f"[{session_id}] 角色 '{role}' 超出预算 {limit}，跳过节点 {dag_node.node_id}"
                    )
                    batch_results.append({
                        "node_id": dag_node.node_id,
                        "name": dag_node.name,
                        "status": "budget_exceeded",
                        "result": None,
                    })
                    continue

                result = self._execute_dag_node(dag_node, taskbook_raw, state, session_id)
                batch_results.append(result)

            stage_deliverables.extend(batch_results)

            # ── ReviewGate 检查 ────────────────────────────────────
            for node_result in batch_results:
                gate = self._find_gate(blueprint.review_gates, node_result["node_id"])
                if gate is None:
                    continue

                gate_outcome = self._evaluate_gate(gate, node_result, session_id)
                review_log.append(gate_outcome)

                if gate_outcome.get("verdict") == "rejected":
                    logger.warning(
                        f"[{session_id}] ReviewGate '{gate.gate_id}' 拒绝 → 执行暂停，等待人工介入"
                    )
                    execution_halted = True
                    break

        logger.info(
            f"[{session_id}] ExecutionOrchestrator 完成 — "
            f"交付物={len(stage_deliverables)}, "
            f"审阅={len(review_log)}, "
            f"halted={execution_halted}"
        )

        return {
            "stage_deliverables_v2": stage_deliverables,
            "execution_review_log": review_log,
            "execution_halted": execution_halted,
            "updated_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # DAG 拓扑排序（分层）
    # ------------------------------------------------------------------

    def _topo_batches(self, dag: List[DAGNode]) -> Iterator[List[DAGNode]]:
        """将 DAG 按依赖关系分层（同层可并发执行）。"""
        node_map: Dict[str, DAGNode] = {n.node_id: n for n in dag}
        # 所有已完成的节点集合
        completed: set = set()
        remaining = list(dag)

        while remaining:
            # 取出当前可执行的节点（依赖全部已完成）
            ready = [
                n for n in remaining
                if all(dep in completed for dep in n.depends_on)
            ]
            if not ready:
                # 存在循环依赖或孤立节点，强制释放
                logger.warning("DAG 中存在无法解决的依赖，强制释放剩余节点")
                yield remaining
                break

            yield ready
            for n in ready:
                completed.add(n.node_id)
                remaining.remove(n)

    # ------------------------------------------------------------------
    # 单节点执行（轻量占位，后续挂载真实 Agent 调用）
    # ------------------------------------------------------------------

    def _execute_dag_node(
        self,
        dag_node: DAGNode,
        taskbook_raw: Dict[str, Any],
        state: ProjectAnalysisState,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        轻量执行单个 DAG 节点。

        TODO: 挂载真实专家 Agent（通过 AgentFactory 动态查找）
        当前为占位实现，返回结构化结果框架。
        """
        logger.info(
            f"[{session_id}] 执行 DAG 节点: {dag_node.node_id} "
            f"({dag_node.name}) owner={dag_node.owner_role}"
        )

        # 核心意图从 taskbook 中读取
        core_prop = taskbook_raw.get("core_proposition", "（未指定）")

        return {
            "node_id": dag_node.node_id,
            "name": dag_node.name,
            "owner_role": dag_node.owner_role,
            "status": "completed",
            "result": {
                "summary": f"[{dag_node.owner_role}] 完成《{dag_node.name}》，核心命题: {core_prop[:40]}",
                "key_decisions": [],
                "artifacts": [],
            },
            "executed_at": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------
    # ReviewGate 工具
    # ------------------------------------------------------------------

    def _find_gate(
        self, gates: List[ReviewGate], node_id: str
    ) -> Optional[ReviewGate]:
        for g in gates:
            if g.after_node_id == node_id:
                return g
        return None

    def _evaluate_gate(
        self,
        gate: ReviewGate,
        node_result: Dict[str, Any],
        session_id: str,
    ) -> Dict[str, Any]:
        """
        评估 ReviewGate。
        - quality/redline 门：轻量规则检查（当前默认通过）
        - human_confirm 门：需挂起等待 Interrupt（当前占位为 auto-pass）
        """
        node_status = node_result.get("status", "")
        if node_status == "budget_exceeded":
            verdict = "rejected"
            reason = "预算超限，节点未执行"
        elif gate.gate_type == "redline":
            # TODO: 接入 RedlineValidator
            verdict = "passed"
            reason = "redline 检查通过（占位）"
        elif gate.gate_type == "human_confirm":
            # TODO: 接入 Interrupt 机制
            verdict = "passed"
            reason = "human_confirm auto-pass（占位，后续需接入 Interrupt）"
        else:
            verdict = "passed"
            reason = "quality 检查通过（占位）"

        logger.info(
            f"[{session_id}] ReviewGate '{gate.gate_id}' → {verdict}: {reason}"
        )
        return {
            "gate_id": gate.gate_id,
            "after_node_id": gate.after_node_id,
            "gate_type": gate.gate_type,
            "verdict": verdict,
            "reason": reason,
            "evaluated_at": datetime.now().isoformat(),
        }
