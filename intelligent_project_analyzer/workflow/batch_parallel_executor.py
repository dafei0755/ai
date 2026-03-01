"""
 P0优化: 真并行批次执行器
v7.502 - 2026-02-10

解决问题: LangGraph Send API 在同步模式下实际上是串行执行
优化方案: asyncio.gather 实现真正的并行执行

预期收益:
- Batch1: 10s → 3.3s (67%加速)
- Batch2: 6s → 2s (67%加速)
- 整体: 16s → 5.3s (67%加速)
"""

import asyncio
import time
from typing import Any, Dict, List

from loguru import logger

from ..core.state import ProjectAnalysisState


class BatchParallelExecutor:
    """批次并行执行器 - 真正的并行执行"""

    def __init__(self, workflow_instance):
        """
        初始化批次并行执行器

        Args:
            workflow_instance: MainWorkflow实例，用于访问_execute_agent_node
        """
        self.workflow = workflow_instance

    async def execute_batch_parallel(
        self, state: ProjectAnalysisState, batch_agents: List[str], batch_number: int
    ) -> Dict[str, Any]:
        """
         真并行执行批次中的所有专家

        Args:
            state: 项目分析状态
            batch_agents: 批次中的专家角色ID列表
            batch_number: 批次编号 (1-based)

        Returns:
            Dict包含所有专家的执行结果
        """
        batch_start = time.time()
        logger.info(f" [BatchParallel] 开始真并行执行 Batch{batch_number}: {len(batch_agents)} 个专家")

        # 创建并行任务
        tasks = []
        for role_id in batch_agents:
            # 为每个专家创建独立的状态副本
            agent_state = dict(state)
            agent_state["role_id"] = role_id
            agent_state["execution_batch"] = f"batch_{batch_number}"
            agent_state["current_stage"] = "parallel_analysis"

            # 创建异步任务
            task = asyncio.create_task(self._execute_single_agent_with_timing(agent_state, role_id))
            tasks.append((role_id, task))

        #  真并行执行 - asyncio.gather
        logger.info(f" [BatchParallel] 启动 {len(tasks)} 个并行任务...")
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

        # 处理结果
        agent_results: Dict[str, Dict[str, Any]] = {}
        successful = 0
        failed = 0

        for (role_id, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(f" [BatchParallel] {role_id} 执行失败: {result}")
                agent_results[role_id] = {
                    "role_id": role_id,
                    "error": str(result),
                    "analysis": f"执行失败: {result}",
                    "confidence": 0.0,
                }
                failed += 1
            elif isinstance(result, dict):
                # 从结果中提取agent_results字段
                nested_results = result.get("agent_results")
                if isinstance(nested_results, dict) and role_id in nested_results:
                    nested = nested_results[role_id]
                    agent_results[role_id] = nested if isinstance(nested, dict) else {"analysis": str(nested)}
                    successful += 1
                else:
                    logger.warning(f"️ [BatchParallel] {role_id} 结果格式异常")
                    agent_results[role_id] = result
                    failed += 1
            else:
                logger.warning(f"️ [BatchParallel] {role_id} 返回非字典结果: {type(result)}")
                agent_results[role_id] = {"role_id": role_id, "analysis": str(result), "confidence": 0.0}
                failed += 1

        batch_elapsed = time.time() - batch_start

        # 性能日志
        logger.info(f" [BatchParallel] Batch{batch_number} 完成:")
        logger.info(f"   - 总耗时: {batch_elapsed:.2f}s")
        logger.info(f"   - 成功: {successful}/{len(batch_agents)}")
        logger.info(f"   - 失败: {failed}/{len(batch_agents)}")
        logger.info(
            f"   - 平均延迟: {batch_elapsed / len(batch_agents):.2f}s/expert "
            f"(理论串行: {batch_elapsed * len(batch_agents):.2f}s)"
        )

        # 详细日志
        for role_id in batch_agents:
            if role_id in agent_results:
                result = agent_results[role_id]
                analysis_len = len(str(result.get("analysis", "")))
                logger.info(f"   - {role_id}: {analysis_len}字符")

        return {"agent_results": agent_results, "batch_elapsed_seconds": batch_elapsed}

    async def _execute_single_agent_with_timing(self, agent_state: Dict[str, Any], role_id: str) -> Dict[str, Any]:
        """
        执行单个专家并记录耗时

        Args:
            agent_state: 专家状态
            role_id: 角色ID

        Returns:
            执行结果
        """
        start = time.time()
        logger.info(f"▶️ [Agent] {role_id} 开始执行...")

        try:
            result = await self.workflow._execute_agent_node(agent_state)
            elapsed = time.time() - start
            logger.info(f" [Agent] {role_id} 完成，耗时 {elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f" [Agent] {role_id} 失败，耗时 {elapsed:.2f}s: {e}")
            raise


async def execute_batch_truly_parallel(
    workflow_instance, state: ProjectAnalysisState, batch_agents: List[str], batch_number: int
) -> Dict[str, Any]:
    """
     便捷函数: 真并行执行批次

    这是一个工厂函数，用于MainWorkflow中快速调用

    Example:
        >>> from .batch_parallel_executor import execute_batch_truly_parallel
        >>> result = await execute_batch_truly_parallel(self, state, batch1_agents, 1)
    """
    executor = BatchParallelExecutor(workflow_instance)
    return await executor.execute_batch_parallel(state, batch_agents, batch_number)
