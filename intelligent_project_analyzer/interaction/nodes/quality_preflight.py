"""
质量预检节点 - 任务执行前的质量预防机制

v7.280 重构：
- 移除用户中断弹窗（质量控制已前置到 role_task_unified_review 的 TaskGenerationGuard）
- 简化为日志记录+状态标记
- 保留检查清单注入到执行环境
"""

from typing import Any, Dict, List

from loguru import logger

from ...core.state import ProjectAnalysisState


class QualityPreflightNode:
    """
    质量预检节点 - 前置预防第1层

    v7.280 简化版：
    - 不再使用 interrupt 阻塞流程
    - 风险评估结果仅记录日志和写入 state
    - 主要质量控制已前置到 TaskGenerationGuard
    """

    def __init__(self, llm_model):
        self.llm_model = llm_model

    async def __call__(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        执行质量预检（异步版本）

        v7.280 简化：
        - 移除用户中断逻辑
        - 仅记录风险日志
        - 快速通过，不阻塞流程
        """
        try:
            logger.info(" 开始质量预检（Pre-flight Check - 静默模式）")

            # 幂等性检查 - 避免重复执行
            if state.get("quality_preflight_completed"):
                logger.info(" 质量预检已完成，跳过重复执行")
                return {}

            # 检查是否已有 TaskGenerationGuard 结果
            unified_review_result = state.get("unified_review_result", {})
            if unified_review_result.get("approved"):
                logger.info(" [v7.280] 检测到 TaskGuard 已在统一审核中完成评估，简化预检")
                return {
                    "quality_preflight_completed": True,
                    "quality_preflight_source": "task_generation_guard",
                }

            # 检查问卷阶段是否已做专家视角分析
            completeness_analysis = state.get("completeness_analysis", {})
            expert_perspective_gaps = completeness_analysis.get("expert_perspective_gaps", {})

            if expert_perspective_gaps:
                logger.info(f" [v7.136] 检测到问卷阶段已做专家视角分析（{len(expert_perspective_gaps)} 个角色）")

                # 只记录极端风险，不阻塞
                extreme_risks = [
                    (role_id, gaps)
                    for role_id, gaps in expert_perspective_gaps.items()
                    if gaps.get("risk_score", 0) > 90
                ]

                if extreme_risks:
                    logger.warning(f"️ [v7.280] 发现 {len(extreme_risks)} 个极端风险（仅记录，不阻塞）")
                    for role_id, gaps in extreme_risks:
                        logger.warning(f"   - {role_id}: 风险分数 {gaps.get('risk_score', 0)}")

                return {"quality_preflight_completed": True}

            # 简化版质量预检
            logger.info(" [v7.280] 执行简化版质量预检")

            strategic_analysis = state.get("strategic_analysis")
            if strategic_analysis is None:
                logger.error(" strategic_analysis 为 None，跳过质量预检")
                return {"quality_preflight_completed": True}

            selected_roles = strategic_analysis.get("selected_roles", [])
            active_agents = state.get("active_agents", [])

            if not active_agents and selected_roles:
                active_agents = [role.get("role_id", "") for role in selected_roles if isinstance(role, dict)]

            if not active_agents:
                logger.warning("️ 没有活跃代理，跳过质量预检")
                return {"quality_preflight_completed": True}

            logger.info(f" [v7.280] 快速检查 {len(active_agents)} 个活跃代理")

            # 简化的风险评估（不调用 LLM，使用静态规则）
            high_risk_count = 0
            for role in selected_roles:
                role_id = role.get("role_id", "")
                tasks = role.get("tasks", [])

                # 简单规则：任务过多或过少都标记风险
                if len(tasks) == 0:
                    logger.warning(f"️ {role_id}: 无分配任务")
                    high_risk_count += 1
                elif len(tasks) > 5:
                    logger.warning(f"️ {role_id}: 任务过多 ({len(tasks)})")
                    high_risk_count += 1

            if high_risk_count > 0:
                logger.warning(f"️ [v7.280] 发现 {high_risk_count} 个潜在风险角色（已记录，继续执行）")
            else:
                logger.info(" [v7.280] 质量预检通过")

            # v9.2 fix: DWP 覆盖率检查
            dwp_coverage_rate = None
            try:
                deliverable_work_packages = state.get("deliverable_work_packages", [])
                confirmed_tasks = state.get("confirmed_core_tasks", [])
                if deliverable_work_packages and confirmed_tasks:
                    all_task_ids = {
                        t.get("task_id") or t.get("id", "")
                        for t in confirmed_tasks
                        if t.get("task_id") or t.get("id", "")
                    }
                    covered_ids = set()
                    for dwp in deliverable_work_packages:
                        src_ids = dwp.get("source_task_ids", []) if isinstance(dwp, dict) else getattr(dwp, "source_task_ids", [])
                        for sid in (src_ids or []):
                            if sid != "UNLINKED":
                                covered_ids.add(sid)
                    if all_task_ids:
                        dwp_coverage_rate = len(covered_ids & all_task_ids) / len(all_task_ids)
                        if dwp_coverage_rate < 0.6:
                            logger.warning(
                                f"⚠️ [v9.2] DWP 覆盖率偏低: {dwp_coverage_rate:.1%} "
                                f"({len(covered_ids & all_task_ids)}/{len(all_task_ids)} 任务被覆盖)"
                            )
                        else:
                            logger.info(f"✅ [v9.2] DWP 覆盖率: {dwp_coverage_rate:.1%}")
            except Exception as e:
                logger.warning(f"⚠️ [v9.2] DWP 覆盖率检查失败: {e}")

            result = {
                "quality_preflight_completed": True,
                "high_risk_count": high_risk_count,
                "preflight_mode": "silent",
            }
            if dwp_coverage_rate is not None:
                result["dwp_coverage_rate"] = dwp_coverage_rate
            return result

        except Exception as e:
            logger.error(f" 质量预检失败（不阻塞流程）: {e}")
            return {
                "quality_preflight_completed": True,
                "preflight_error": str(e),
            }


# 创建节点实例的工厂函数
def create_quality_preflight_node(llm_model):
    """创建质量预检节点"""
    return QualityPreflightNode(llm_model)
