"""
搜索模式工作流程集成器 - 将搜索任务规划集成到主工作流程
实现搜索模式的端到端流程：需求分析 → 搜索规划 → 执行协调 → 结果分发 → 动态扩展
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .dynamic_search_expander import DynamicSearchExpander, ExpansionTrigger, SearchGap
from .search_coordinator import SearchCoordinator, SearchExecutionReport, SearchResult
from .search_result_distributor import DistributionReport, SearchResultDistributor
from .search_task_planner import SearchMasterPlan, SearchTask, SearchTaskPlanner

logger = logging.getLogger(__name__)


class SearchWorkflowPhase(Enum):
    """搜索工作流程阶段"""

    INIT = "initialization"
    PLANNING = "planning"
    COORDINATION = "coordination"
    DISTRIBUTION = "distribution"
    EXPANSION = "expansion"
    COMPLETION = "completion"
    ERROR = "error"


@dataclass
class SearchWorkflowConfig:
    """搜索工作流程配置"""

    enable_dynamic_expansion: bool = True
    max_expansion_rounds: int = 2
    quality_threshold: float = 0.7
    enable_result_sharing: bool = True
    max_parallel_searches: int = 3
    enable_quality_monitoring: bool = True

    # 性能配置
    timeout_per_phase: Dict[str, int] = field(
        default_factory=lambda: {"planning": 60, "coordination": 300, "distribution": 30, "expansion": 120}
    )

    # 成本控制
    cost_limits: Dict[str, float] = field(
        default_factory=lambda: {
            "max_total_cost": 2.0,  # 单次工作流程最大成本
            "max_api_calls": 100,  # 最大API调用次数
            "cost_per_call": 0.01,  # 每次调用成本
        }
    )


@dataclass
class WorkflowState:
    """工作流程状态"""

    session_id: str
    current_phase: SearchWorkflowPhase = SearchWorkflowPhase.INIT
    start_time: datetime = field(default_factory=datetime.now)
    phase_start_time: datetime = field(default_factory=datetime.now)

    # 阶段数据
    requirements_analysis: Optional[Dict[str, Any]] = None
    search_plan: Optional[SearchMasterPlan] = None
    execution_results: List[SearchResult] = field(default_factory=list)
    distribution_report: Optional[DistributionReport] = None
    expansion_rounds: int = 0

    # 性能数据
    total_time: float = 0
    phase_times: Dict[str, float] = field(default_factory=dict)
    api_calls_count: int = 0
    total_cost: float = 0.0

    # 错误处理
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class SearchWorkflowResult:
    """搜索工作流程结果"""

    session_id: str
    success: bool
    final_phase: SearchWorkflowPhase

    # 核心结果
    search_results: List[SearchResult]
    distribution_report: DistributionReport
    quality_metrics: Dict[str, Any]

    # 性能指标
    total_execution_time: float
    phase_breakdown: Dict[str, float]
    resource_usage: Dict[str, Any]

    # 扩展信息
    expansion_performed: bool
    expansion_rounds: int
    discovered_gaps: List[SearchGap]

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SearchWorkflowIntegrator:
    """搜索工作流程集成器 - 端到端搜索模式实现"""

    def __init__(self, config: Optional[SearchWorkflowConfig] = None):
        self.config = config or SearchWorkflowConfig()

        # 初始化组件
        self.planner = SearchTaskPlanner()
        self.coordinator = SearchCoordinator()
        self.distributor = SearchResultDistributor()
        self.expander = DynamicSearchExpander()

        # 状态管理
        self.active_workflows: Dict[str, WorkflowState] = {}
        self.completed_workflows: List[SearchWorkflowResult] = []

        # 性能监控
        self.performance_metrics = {
            "total_workflows": 0,
            "successful_workflows": 0,
            "average_execution_time": 0.0,
            "total_api_calls": 0,
            "total_cost": 0.0,
        }

    async def execute_search_workflow(
        self, session_id: str, requirements_analysis: Dict[str, Any], deliverable_metadata: List[Dict[str, Any]]
    ) -> SearchWorkflowResult:
        """
        执行完整的搜索工作流程

        Args:
            session_id: 会话ID
            requirements_analysis: 需求分析结果
            deliverable_metadata: 交付物元数据

        Returns:
            搜索工作流程结果
        """
        logger.info(f"🚀 [SearchWorkflow] 启动搜索工作流程，会话ID: {session_id}")

        # 初始化工作流程状态
        workflow_state = WorkflowState(session_id=session_id, requirements_analysis=requirements_analysis)
        self.active_workflows[session_id] = workflow_state

        try:
            # Phase 1: 搜索任务规划
            await self._execute_planning_phase(workflow_state, deliverable_metadata)

            # Phase 2: 搜索协调执行
            await self._execute_coordination_phase(workflow_state)

            # Phase 3: 结果分发
            await self._execute_distribution_phase(workflow_state)

            # Phase 4: 动态扩展（可选）
            if self.config.enable_dynamic_expansion:
                await self._execute_expansion_phase(workflow_state)

            # Phase 5: 完成
            workflow_result = await self._execute_completion_phase(workflow_state)

            # 更新性能指标
            self._update_performance_metrics(workflow_result)

            logger.info(f"✅ [SearchWorkflow] 搜索工作流程完成，会话ID: {session_id}")
            return workflow_result

        except Exception as e:
            logger.error(f"❌ [SearchWorkflow] 工作流程执行失败: {e}")
            return await self._handle_workflow_error(workflow_state, e)

        finally:
            # 清理活动工作流程
            if session_id in self.active_workflows:
                del self.active_workflows[session_id]

    async def _execute_planning_phase(self, state: WorkflowState, deliverable_metadata: List[Dict[str, Any]]):
        """执行搜索任务规划阶段"""
        self._transition_to_phase(state, SearchWorkflowPhase.PLANNING)

        logger.info(f"📋 [SearchWorkflow] 开始搜索任务规划阶段")

        try:
            # 使用搜索任务规划器
            search_plan = await self.planner.generate_search_plan(
                requirements_summary=state.requirements_analysis.get("summary", ""),
                deliverable_metadata=deliverable_metadata,
                quality_requirements={"min_quality": self.config.quality_threshold},
            )

            if not search_plan or not search_plan.search_tasks:
                raise ValueError("搜索任务规划失败：未生成有效的搜索任务")

            state.search_plan = search_plan

            # 成本预估
            estimated_cost = self._estimate_plan_cost(search_plan)
            if estimated_cost > self.config.cost_limits["max_total_cost"]:
                state.warnings.append(f"预估成本 ${estimated_cost:.2f} 超过限制 ${self.config.cost_limits['max_total_cost']}")

            phase_time = self._complete_phase(state)
            logger.info(f"✅ [SearchWorkflow] 规划阶段完成，耗时{phase_time:.2f}秒，生成{len(search_plan.search_tasks)}个搜索任务")

        except Exception as e:
            logger.error(f"❌ [SearchWorkflow] 规划阶段失败: {e}")
            state.errors.append({"phase": "planning", "error": str(e), "timestamp": datetime.now()})
            raise

    async def _execute_coordination_phase(self, state: WorkflowState):
        """执行搜索协调阶段"""
        self._transition_to_phase(state, SearchWorkflowPhase.COORDINATION)

        logger.info(f"🎯 [SearchWorkflow] 开始搜索协调执行阶段")

        try:
            # 使用搜索协调器执行搜索计划
            execution_report = await self.coordinator.execute_search_plan(
                search_plan=state.search_plan, max_parallel=self.config.max_parallel_searches
            )

            if not execution_report or not execution_report.successful_results:
                raise ValueError("搜索协调执行失败：未获得有效搜索结果")

            state.execution_results = execution_report.successful_results
            state.api_calls_count += execution_report.total_api_calls
            state.total_cost += execution_report.total_cost

            # 质量检查
            quality_check = self._check_results_quality(execution_report.successful_results)
            if quality_check["overall_quality"] < self.config.quality_threshold:
                state.warnings.append(
                    f"搜索结果质量 {quality_check['overall_quality']:.2f} 低于阈值 {self.config.quality_threshold}"
                )

            phase_time = self._complete_phase(state)
            logger.info(
                f"✅ [SearchWorkflow] 协调阶段完成，耗时{phase_time:.2f}秒，获得{len(execution_report.successful_results)}个有效结果"
            )

        except Exception as e:
            logger.error(f"❌ [SearchWorkflow] 协调阶段失败: {e}")
            state.errors.append({"phase": "coordination", "error": str(e), "timestamp": datetime.now()})
            raise

    async def _execute_distribution_phase(self, state: WorkflowState):
        """执行结果分发阶段"""
        self._transition_to_phase(state, SearchWorkflowPhase.DISTRIBUTION)

        logger.info(f"📊 [SearchWorkflow] 开始结果分发阶段")

        try:
            # 使用结果分发器
            distribution_report = await self.distributor.distribute_search_results(
                search_results=state.execution_results,
                deliverable_bindings=state.search_plan.deliverable_bindings,
                enable_sharing=self.config.enable_result_sharing,
            )

            state.distribution_report = distribution_report

            phase_time = self._complete_phase(state)
            logger.info(f"✅ [SearchWorkflow] 分发阶段完成，耗时{phase_time:.2f}秒")

        except Exception as e:
            logger.error(f"❌ [SearchWorkflow] 分发阶段失败: {e}")
            state.errors.append({"phase": "distribution", "error": str(e), "timestamp": datetime.now()})
            raise

    async def _execute_expansion_phase(self, state: WorkflowState):
        """执行动态扩展阶段"""
        if state.expansion_rounds >= self.config.max_expansion_rounds:
            logger.info(f"⏭️ [SearchWorkflow] 跳过扩展阶段，已达到最大扩展轮数: {state.expansion_rounds}")
            return

        self._transition_to_phase(state, SearchWorkflowPhase.EXPANSION)

        logger.info(f"🔄 [SearchWorkflow] 开始动态扩展阶段（第{state.expansion_rounds + 1}轮）")

        try:
            # 使用动态搜索扩展器
            expansion_plan = await self.expander.analyze_and_expand_search(
                original_plan=state.search_plan, search_results=state.execution_results
            )

            if expansion_plan and expansion_plan.search_tasks:
                logger.info(f"🎯 [SearchWorkflow] 发现扩展机会，执行{len(expansion_plan.search_tasks)}个扩展任务")

                # 执行扩展搜索
                expansion_execution = await self.coordinator.execute_search_plan(
                    search_plan=expansion_plan, max_parallel=2  # 扩展搜索并发较低
                )

                if expansion_execution and expansion_execution.successful_results:
                    # 合并扩展结果
                    state.execution_results.extend(expansion_execution.successful_results)
                    state.api_calls_count += expansion_execution.total_api_calls
                    state.total_cost += expansion_execution.total_cost

                    # 重新分发结果
                    state.distribution_report = await self.distributor.distribute_search_results(
                        search_results=state.execution_results,
                        deliverable_bindings=state.search_plan.deliverable_bindings,
                        enable_sharing=self.config.enable_result_sharing,
                    )

                state.expansion_rounds += 1

                # 递归扩展（如果还有轮次）
                if state.expansion_rounds < self.config.max_expansion_rounds:
                    await self._execute_expansion_phase(state)
            else:
                logger.info(f"✅ [SearchWorkflow] 无需进一步扩展")

            phase_time = self._complete_phase(state)
            logger.info(f"✅ [SearchWorkflow] 扩展阶段完成，耗时{phase_time:.2f}秒")

        except Exception as e:
            logger.warning(f"⚠️ [SearchWorkflow] 扩展阶段失败，继续主流程: {e}")
            state.warnings.append(f"扩展阶段失败: {str(e)}")
            self._complete_phase(state)

    async def _execute_completion_phase(self, state: WorkflowState) -> SearchWorkflowResult:
        """执行完成阶段"""
        self._transition_to_phase(state, SearchWorkflowPhase.COMPLETION)

        logger.info(f"🏁 [SearchWorkflow] 开始完成阶段")

        # 计算质量指标
        quality_metrics = self._calculate_quality_metrics(state)

        # 识别发现的缺口
        discovered_gaps = []
        if hasattr(self.expander, "gap_history"):
            discovered_gaps = self.expander.gap_history

        # 计算总执行时间
        total_time = (datetime.now() - state.start_time).total_seconds()
        state.total_time = total_time

        # 构建工作流程结果
        workflow_result = SearchWorkflowResult(
            session_id=state.session_id,
            success=len(state.errors) == 0 and len(state.execution_results) > 0,
            final_phase=SearchWorkflowPhase.COMPLETION,
            search_results=state.execution_results,
            distribution_report=state.distribution_report,
            quality_metrics=quality_metrics,
            total_execution_time=total_time,
            phase_breakdown=state.phase_times,
            resource_usage={
                "api_calls": state.api_calls_count,
                "total_cost": state.total_cost,
                "warnings": len(state.warnings),
                "errors": len(state.errors),
            },
            expansion_performed=state.expansion_rounds > 0,
            expansion_rounds=state.expansion_rounds,
            discovered_gaps=discovered_gaps,
            metadata={
                "config": {
                    "enable_dynamic_expansion": self.config.enable_dynamic_expansion,
                    "max_expansion_rounds": self.config.max_expansion_rounds,
                    "quality_threshold": self.config.quality_threshold,
                },
                "warnings": state.warnings,
                "errors": state.errors,
            },
        )

        # 记录完成的工作流程
        self.completed_workflows.append(workflow_result)

        phase_time = self._complete_phase(state)
        logger.info(f"✅ [SearchWorkflow] 完成阶段结束，总耗时{total_time:.2f}秒")

        return workflow_result

    async def _handle_workflow_error(self, state: WorkflowState, error: Exception) -> SearchWorkflowResult:
        """处理工作流程错误"""
        self._transition_to_phase(state, SearchWorkflowPhase.ERROR)

        logger.error(f"🚨 [SearchWorkflow] 工作流程异常终止: {error}")

        # 构建错误结果
        error_result = SearchWorkflowResult(
            session_id=state.session_id,
            success=False,
            final_phase=SearchWorkflowPhase.ERROR,
            search_results=state.execution_results,  # 返回已获得的结果
            distribution_report=state.distribution_report,
            quality_metrics={"error": str(error)},
            total_execution_time=(datetime.now() - state.start_time).total_seconds(),
            phase_breakdown=state.phase_times,
            resource_usage={
                "api_calls": state.api_calls_count,
                "total_cost": state.total_cost,
                "warnings": len(state.warnings),
                "errors": len(state.errors) + 1,
            },
            expansion_performed=state.expansion_rounds > 0,
            expansion_rounds=state.expansion_rounds,
            discovered_gaps=[],
            metadata={"error": str(error), "errors": state.errors, "warnings": state.warnings},
        )

        return error_result

    # 辅助方法
    def _transition_to_phase(self, state: WorkflowState, new_phase: SearchWorkflowPhase):
        """转换到新阶段"""
        if state.current_phase != SearchWorkflowPhase.INIT:
            # 完成上一阶段的时间记录
            phase_duration = (datetime.now() - state.phase_start_time).total_seconds()
            state.phase_times[state.current_phase.value] = phase_duration

        state.current_phase = new_phase
        state.phase_start_time = datetime.now()

        logger.debug(f"🔄 [SearchWorkflow] 阶段转换: {new_phase.value}")

    def _complete_phase(self, state: WorkflowState) -> float:
        """完成当前阶段并返回耗时"""
        phase_duration = (datetime.now() - state.phase_start_time).total_seconds()
        state.phase_times[state.current_phase.value] = phase_duration
        return phase_duration

    def _estimate_plan_cost(self, search_plan: SearchMasterPlan) -> float:
        """估算搜索计划成本"""
        total_queries = sum(len(task.queries) for task in search_plan.search_tasks)
        return total_queries * self.config.cost_limits["cost_per_call"]

    def _check_results_quality(self, results: List[SearchResult]) -> Dict[str, Any]:
        """检查结果质量"""
        if not results:
            return {"overall_quality": 0.0, "details": "no_results"}

        quality_scores = [r.quality_score / 100.0 for r in results if r.success]
        overall_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        return {
            "overall_quality": overall_quality,
            "total_results": len(results),
            "successful_results": len(quality_scores),
            "average_score": overall_quality,
            "details": "quality_analysis_complete",
        }

    def _calculate_quality_metrics(self, state: WorkflowState) -> Dict[str, Any]:
        """计算质量指标"""
        results = state.execution_results

        if not results:
            return {"overall_quality": 0.0, "error": "no_results"}

        # 基本指标
        total_results = len(results)
        successful_results = len([r for r in results if r.success])
        success_rate = successful_results / total_results if total_results > 0 else 0.0

        # 质量分布
        quality_scores = [r.quality_score for r in results if r.success]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        # 覆盖度分析
        covered_deliverables = len(set(r.deliverable_id for r in results))
        covered_search_types = len(set(r.search_type for r in results))

        return {
            "overall_quality": avg_quality / 100.0,
            "success_rate": success_rate,
            "total_results": total_results,
            "successful_results": successful_results,
            "covered_deliverables": covered_deliverables,
            "covered_search_types": covered_search_types,
            "average_quality_score": avg_quality,
            "expansion_rounds": state.expansion_rounds,
            "warnings_count": len(state.warnings),
            "errors_count": len(state.errors),
        }

    def _update_performance_metrics(self, result: SearchWorkflowResult):
        """更新性能指标"""
        self.performance_metrics["total_workflows"] += 1
        if result.success:
            self.performance_metrics["successful_workflows"] += 1

        self.performance_metrics["total_api_calls"] += result.resource_usage["api_calls"]
        self.performance_metrics["total_cost"] += result.resource_usage["total_cost"]

        # 更新平均执行时间
        total_time = (
            self.performance_metrics["average_execution_time"] * (self.performance_metrics["total_workflows"] - 1)
            + result.total_execution_time
        ) / self.performance_metrics["total_workflows"]
        self.performance_metrics["average_execution_time"] = total_time

    # 公开方法
    def get_workflow_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流程状态"""
        if session_id not in self.active_workflows:
            return None

        state = self.active_workflows[session_id]

        return {
            "session_id": session_id,
            "current_phase": state.current_phase.value,
            "elapsed_time": (datetime.now() - state.start_time).total_seconds(),
            "api_calls": state.api_calls_count,
            "total_cost": state.total_cost,
            "results_count": len(state.execution_results),
            "expansion_rounds": state.expansion_rounds,
            "warnings": len(state.warnings),
            "errors": len(state.errors),
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        return {
            **self.performance_metrics,
            "success_rate": (
                self.performance_metrics["successful_workflows"] / max(self.performance_metrics["total_workflows"], 1)
            ),
            "average_cost_per_workflow": (
                self.performance_metrics["total_cost"] / max(self.performance_metrics["total_workflows"], 1)
            ),
            "active_workflows": len(self.active_workflows),
            "completed_workflows": len(self.completed_workflows),
        }


# 便捷函数
async def execute_search_mode_workflow(
    session_id: str,
    requirements_analysis: Dict[str, Any],
    deliverable_metadata: List[Dict[str, Any]],
    config: Optional[SearchWorkflowConfig] = None,
) -> SearchWorkflowResult:
    """执行搜索模式工作流程的便捷函数"""
    integrator = SearchWorkflowIntegrator(config)
    return await integrator.execute_search_workflow(
        session_id=session_id, requirements_analysis=requirements_analysis, deliverable_metadata=deliverable_metadata
    )
