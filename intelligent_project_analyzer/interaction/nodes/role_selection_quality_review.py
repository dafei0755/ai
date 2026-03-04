"""
角色选择质量审核节点 - 在角色选择后、任务分解前进行质量检查

实现红蓝对抗机制，审核角色选择的合理性、完整性和协同性
"""

from typing import Any, Dict, List, Literal

from langgraph.store.base import BaseStore
from langgraph.types import Command
from loguru import logger

from ...core.state import AnalysisStage, ProjectAnalysisState
from ...review import MultiPerspectiveReviewCoordinator


class RoleSelectionQualityReviewNode:
    """
    角色选择质量审核节点

    在角色选择后、任务分解前运行，使用LLM红蓝对抗机制审核：
    - 角色选择的适配性
    - 角色覆盖的完整性
    - 角色之间的协同性
    - 潜在的能力缺口或冗余

    输出：
    - critical_issues: 关键问题（阻塞流程，需要用户决策）
    - warnings: 警告（记录但不阻塞）
    - strengths: 优势（角色选择的亮点）
    - overall_assessment: 总体评估
    """

    # 类级别的审核协调器实例（延迟初始化）
    _review_coordinator = None
    _llm_model = None

    @classmethod
    def initialize_coordinator(cls, llm_model, config: Dict[str, Any] | None = None):
        """初始化审核协调器"""
        if cls._review_coordinator is None or cls._llm_model != llm_model:
            cls._llm_model = llm_model
            cls._review_coordinator = MultiPerspectiveReviewCoordinator(llm_model=llm_model, config=config or {})
            logger.info("角色选择质量审核协调器已初始化")

    @classmethod
    def execute(
        cls,
        state: ProjectAnalysisState,
        store: BaseStore | None = None,
        llm_model=None,
        config: Dict[str, Any] | None = None,
    ) -> Command[Literal["user_question", "project_director"]]:
        """
        执行角色选择质量审核

        Args:
            state: 项目分析状态
            store: 存储接口
            llm_model: LLM模型实例
            config: 配置参数

        Returns:
            Command对象，指向下一个节点（user_question或project_director）
        """
        logger.info("=" * 100)
        logger.info(" 开始角色选择质量审核（红蓝对抗）")
        logger.info("=" * 100)

        # 初始化审核协调器
        if llm_model:
            cls.initialize_coordinator(llm_model, config)

        if cls._review_coordinator is None:
            logger.error("审核协调器未初始化，跳过质量审核")
            return cls._skip_review_fallback(state)

        # 获取角色选择结果和需求
        selected_roles = state.get("selected_roles", [])
        requirements = state.get("structured_requirements", {})
        strategy = state.get("project_strategy", {})

        # 验证输入
        if not selected_roles:
            logger.warning("未找到已选择的角色，跳过质量审核")
            return cls._skip_review_fallback(state)

        # 记录审核上下文
        cls._log_review_context(selected_roles, requirements)

        # 执行红蓝对抗审核
        logger.info("\n 启动红蓝对抗审核")

        # 执行红蓝对抗审核（带错误处理）
        try:
            review_result = cls._review_coordinator.conduct_role_selection_review(
                selected_roles=selected_roles, requirements=requirements, strategy=strategy
            )
        except Exception as e:
            logger.error(f" 质量审核执行失败: {e}")
            logger.warning("️ 降级处理：跳过质量审核，继续流程")
            return cls._skip_review_fallback(state)

        # 获取审核结果
        critical_issues = review_result.get("critical_issues", [])
        warnings = review_result.get("warnings", [])
        strengths = review_result.get("strengths", [])
        overall_assessment = review_result.get("overall_assessment", "")

        # 记录审核摘要
        cls._log_review_summary(review_result)

        # 更新状态
        updated_state = {
            "current_stage": AnalysisStage.ROLE_SELECTION.value,
            "role_quality_review_result": review_result,
            "role_quality_review_completed": True,
        }

        # 决定下一步路由
        if critical_issues:
            # 有关键问题，需要用户决策
            logger.warning(f"️ 发现 {len(critical_issues)} 个关键问题，需要用户决策")

            # 准备用户问题
            user_question_data = cls._prepare_user_question(critical_issues, warnings, strengths)
            updated_state["pending_user_question"] = user_question_data

            return Command(update=updated_state, goto="user_question")
        else:
            # 无关键问题，继续流程
            if warnings:
                logger.info(f"ℹ️ 发现 {len(warnings)} 个警告，已记录但不阻塞流程")
            logger.info(" 角色选择质量审核通过，继续任务分解")

            return Command(update=updated_state, goto="quality_preflight")

    @classmethod
    def _log_review_context(cls, selected_roles: List[Dict[str, Any]], requirements: Dict[str, Any]):
        """记录审核上下文"""
        logger.info("\n 审核上下文：")
        logger.info(f"  - 已选择角色数量: {len(selected_roles)}")

        role_names = []
        for role in selected_roles:
            if isinstance(role, dict):
                role_name = role.get("role_name") or role.get("dynamic_role_name", "未知角色")
                role_names.append(role_name)

        logger.info(f"  - 角色列表: {', '.join(role_names)}")

        project_task = requirements.get("project_task", "")
        if project_task:
            logger.info(f"  - 项目任务: {project_task[:100]}...")

    @classmethod
    def _log_review_summary(cls, review_result: Dict[str, Any]):
        """记录审核摘要"""
        critical_issues = review_result.get("critical_issues", [])
        warnings = review_result.get("warnings", [])
        strengths = review_result.get("strengths", [])
        overall_assessment = review_result.get("overall_assessment", "")

        logger.info("\n 审核结果摘要：")
        logger.info(f"  - 关键问题: {len(critical_issues)} 个")
        logger.info(f"  - 警告: {len(warnings)} 个")
        logger.info(f"  - 优势: {len(strengths)} 个")
        logger.info(f"  - 总体评估: {overall_assessment}")

        if critical_issues:
            logger.info("\n️ 关键问题详情：")
            for i, issue in enumerate(critical_issues, 1):
                issue_text = issue.get("issue", "未知问题")
                impact = issue.get("impact", "")
                logger.info(f"  {i}. {issue_text}")
                if impact:
                    logger.info(f"     影响: {impact}")

        if warnings:
            logger.info("\nℹ️ 警告详情：")
            for i, warning in enumerate(warnings, 1):
                warning_text = warning.get("issue", "未知警告")
                logger.info(f"  {i}. {warning_text}")

    @classmethod
    def _prepare_user_question(
        cls, critical_issues: List[Dict[str, Any]], warnings: List[Dict[str, Any]], strengths: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        准备用户问题数据

        Returns:
            用户问题数据，包含问题描述和选项
        """
        # 构建问题描述
        question_parts = ["角色选择质量审核发现以下关键问题：\n"]

        for i, issue in enumerate(critical_issues, 1):
            issue_text = issue.get("issue", "未知问题")
            impact = issue.get("impact", "")
            suggestion = issue.get("suggestion", "")

            question_parts.append(f"{i}. {issue_text}")
            if impact:
                question_parts.append(f"   影响: {impact}")
            if suggestion:
                question_parts.append(f"   建议: {suggestion}")
            question_parts.append("")

        if warnings:
            question_parts.append("\n另外还有以下警告：")
            for i, warning in enumerate(warnings, 1):
                warning_text = warning.get("issue", "未知警告")
                question_parts.append(f"{i}. {warning_text}")

        question_text = "\n".join(question_parts)

        # 构建选项
        options = [
            {"label": "调整角色选择", "value": "adjust_roles", "description": "返回角色选择阶段，重新选择或调整角色配置"},
            {"label": "继续执行", "value": "proceed_anyway", "description": "忽略这些问题，继续进行任务分解和执行"},
            {"label": "提供更多信息", "value": "provide_context", "description": "补充更多需求信息，帮助系统更好地理解项目"},
        ]

        return {
            "question_type": "role_quality_review",
            "question_text": question_text,
            "options": options,
            "context": {"critical_issues": critical_issues, "warnings": warnings, "strengths": strengths},
        }

    @classmethod
    def _skip_review_fallback(cls, state: ProjectAnalysisState) -> Command[Literal["quality_preflight"]]:
        """
        跳过审核的回退逻辑

        当审核无法执行时（如缺少必要数据），直接继续流程
        """
        logger.info("️ 跳过角色选择质量审核，直接继续")

        return Command(
            update={
                "role_quality_review_result": {"skipped": True, "reason": "缺少必要数据或审核协调器未初始化"},
                "role_quality_review_completed": False,
            },
            goto="quality_preflight",
        )


# 导出节点执行函数（用于workflow集成）
def role_selection_quality_review_node(
    state: ProjectAnalysisState, store: BaseStore | None = None, config: Dict[str, Any] | None = None
) -> Command[Literal["user_question", "project_director"]]:
    """
    角色选择质量审核节点（workflow入口）

    Args:
        state: 项目分析状态
        store: 存储接口
        config: 配置参数（包含llm_model）

    Returns:
        Command对象，指向下一个节点
    """
    llm_model = config.get("configurable", {}).get("llm_model") if config else None

    return RoleSelectionQualityReviewNode.execute(state=state, store=store, llm_model=llm_model, config=config)
