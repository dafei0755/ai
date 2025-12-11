"""
核心状态管理

定义项目分析系统的状态结构和管理逻辑
"""

from typing import Dict, List, Optional, Any, Annotated
from typing_extensions import TypedDict
from datetime import datetime
from enum import Enum
import operator

from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class AnalysisStage(Enum):
    """分析阶段枚举"""
    INIT = "init"
    REQUIREMENT_COLLECTION = "requirement_collection"
    REQUIREMENT_CONFIRMATION = "requirement_confirmation"
    STRATEGIC_ANALYSIS = "strategic_analysis"
    PARALLEL_ANALYSIS = "parallel_analysis"
    BATCH_EXECUTION = "batch_execution"  # 批次执行阶段
    ANALYSIS_REVIEW = "analysis_review"  # 分析结果审核
    RESULT_AGGREGATION = "result_aggregation"
    FINAL_REVIEW = "final_review"  # 最终报告审核
    RESULT_REVIEW = "result_review"  # 保留以兼容旧代码
    PDF_GENERATION = "pdf_generation"
    COMPLETED = "completed"
    ERROR = "error"


class AgentType(Enum):
    """智能体类型枚举（仅保留核心智能体，V2-V6 已移除）"""
    REQUIREMENTS_ANALYST = "requirements_analyst"
    PROJECT_DIRECTOR = "project_director"
    RESULT_AGGREGATOR = "result_aggregator"
    PDF_GENERATOR = "pdf_generator"


def merge_agent_results(left: Optional[Dict[str, Any]], right: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    合并智能体结果的reducer函数

    用于处理并发执行的智能体节点同时更新agent_results字段的情况

    Args:
        left: 左侧(已有)的结果字典
        right: 右侧(新)的结果字典

    Returns:
        合并后的结果字典
    """
    if left is None:
        return right or {}
    if right is None:
        return left
    # 合并两个字典,右侧的值会覆盖左侧的同名键
    return {**left, **right}


def merge_lists(left: Optional[List[Any]], right: Optional[List[Any]]) -> List[Any]:
    """
    合并列表的reducer函数

    用于处理并发执行的节点同时更新列表字段的情况
    会去重,保持顺序

    Args:
        left: 左侧值(现有值)
        right: 右侧值(新值)

    Returns:
        合并后的列表
    """
    if left is None:
        return right or []
    if right is None:
        return left

    # 合并并去重,保持顺序
    result = left.copy()
    for item in right:
        if item not in result:
            result.append(item)
    return result


def take_max_timestamp(left: str, right: str) -> str:
    """
    时间戳 reducer：选择较大的时间戳

    用于 created_at 和 updated_at 字段，确保并发更新时
    总是保留最新的时间戳。

    Args:
        left: 左侧时间戳（ISO 8601 格式）
        right: 右侧时间戳（ISO 8601 格式）

    Returns:
        较大的时间戳字符串
    """
    try:
        left_dt = datetime.fromisoformat(left)
        right_dt = datetime.fromisoformat(right)
        return left if left_dt > right_dt else right
    except:
        # 如果解析失败，默认取右侧值（最新更新）
        return right


def take_last(left: Optional[str], right: Optional[str]) -> Optional[str]:
    """
    选择最后更新的值（detail 字段专用）

    用于 detail 字段，确保并发更新时总是保留最新的描述信息。
    由于 detail 仅用于前端实时显示单一状态，不需要合并，直接取最新值即可。

    用例：批次 5 执行时，2 个并行专家同时更新 detail 字段：
    - Thread 1: {"detail": "专家【V6_专业总工程师_6-2】完成分析"}
    - Thread 2: {"detail": "专家【V6_专业总工程师_6-3】完成分析"}
    - 合并结果：最后完成的专家的描述信息

    Args:
        left: 左侧值（旧值）
        right: 右侧值（新值）

    Returns:
        新值（right），如果为 None 则返回旧值（left）
    """
    return right if right is not None else left


class ProjectAnalysisState(TypedDict):
    """项目分析系统的核心状态"""
    
    # 基础信息
    session_id: str
    user_id: Optional[str]
    created_at: Annotated[str, take_max_timestamp]
    updated_at: Annotated[str, take_max_timestamp]
    
    # 用户输入和需求
    user_input: str
    structured_requirements: Optional[Dict[str, Any]]
    feasibility_assessment: Optional[Dict[str, Any]]  # 🆕 V1.5可行性分析结果（后台决策支持）
    project_type: Optional[str]  # 🆕 项目类型（用于本体论注入）: "personal_residential" | "hybrid_residential_commercial" | "commercial_enterprise"
    
    # 分析策略和任务分派
    # 使用Annotated和reducer函数来处理并发更新
    strategic_analysis: Annotated[Optional[Dict[str, Any]], merge_agent_results]
    subagents: Annotated[Optional[Dict[str, str]], merge_agent_results]  # agent_id -> task_description
    # agents_to_execute 已移除（Fixed Mode 专用字段）
    # 使用Annotated和reducer函数来处理并发更新
    # 当多个智能体节点并行执行时,它们的结果会被自动合并
    agent_results: Annotated[Optional[Dict[str, Any]], merge_agent_results]
    agent_type: Optional[Any]  # 当前执行的智能体类型(用于Send API并行执行)

    # 专业分析结果
    # 注意：系统现在使用 Dynamic Mode，专家结果存储在 agent_results 字段中
    # 旧的 v2-v6 固定字段已移除

    # 结果聚合和输出
    aggregated_results: Optional[Dict[str, Any]]
    final_report: Optional[str]
    pdf_file_path: Optional[str]
    
    # 交互和历史
    conversation_history: Annotated[List[BaseMessage], add_messages]
    human_feedback: Optional[Dict[str, Any]]
    
    # 流程控制
    current_stage: str  # AnalysisStage
    detail: Annotated[Optional[str], take_last]  # 当前节点的详细描述（用于前端实时显示，支持并发更新）
    # 使用Annotated和reducer函数来处理并发更新
    active_agents: Annotated[List[str], merge_lists]  # 当前活跃的智能体
    completed_agents: Annotated[List[str], merge_lists]  # 已完成的智能体
    failed_agents: Annotated[List[str], merge_lists]  # 失败的智能体
    
    # 🆕 流程跳过标志
    skip_unified_review: Optional[bool]  # 是否跳过统一审核
    skip_calibration: Optional[bool]  # 🆕 是否跳过校准问卷（中等复杂度任务）
    requirements_confirmed: Optional[bool]  # 需求是否已确认
    user_modification_processed: Optional[bool]  # 用户修改是否已处理
    modification_confirmation_round: Optional[int]  # 修改确认轮次

    # 🆕 问卷流程控制标志
    calibration_processed: Optional[bool]  # 是否已处理问卷（避免重复显示）
    calibration_skipped: Optional[bool]  # 是否跳过问卷（用户选择或系统判断）
    calibration_questionnaire: Optional[Dict[str, Any]]  # 生成的校准问卷
    calibration_answers: Optional[Dict[str, Any]]  # 问卷答案（兼容旧字段）
    questionnaire_responses: Optional[Dict[str, Any]]  # 问卷回答（包含答案和元数据）
    questionnaire_summary: Optional[Dict[str, Any]]  # 问卷精炼摘要（仅保留有效信息）
    interaction_history: Annotated[List[Dict[str, Any]], merge_lists]  # 交互历史记录
    post_completion_followup_completed: Optional[bool]  # 报告完成后的追问是否已结束

    # 任务依赖关系 - 新增字段
    execution_batch: Optional[str]  # 当前执行批次: "first" 或 "second" (旧字段，保留兼容)
    dependency_summary: Optional[Dict[str, Any]]  # 第一批专家的完成情况摘要

    # 🆕 批次调度字段（2025-11-18）- 支持动态批次调度
    execution_batches: Optional[List[List[str]]]  # 批次列表，每个批次是一个角色 ID 列表
    """
    批次列表，每个批次是一个角色 ID 列表（可并行执行）
    例: [
        ["V4_设计研究员_4-1"],
        ["V5_场景与用户生态专家_5-1"],
        ["V3_人物及叙事专家_3-1"],
        ["V2_设计总监_2-1"],
        ["V6_技术总监_6-1"]
    ]
    通过 BatchScheduler.schedule_batches() 自动计算
    """

    current_batch: int  # 当前执行的批次编号（从 1 开始）
    total_batches: int  # 总批次数

    # 🆕 执行模式配置（v3.6）- 控制批次确认行为
    execution_mode: Optional[str]  # 执行模式: "manual"（手动确认）, "automatic"（自动执行）, "preview"（显示后自动执行）

    completed_batches: Annotated[List[int], merge_lists]  # 已完成的批次编号列表
    """使用 reducer 支持并发更新"""

    # 第二批策略审核 - 新增字段
    second_batch_approved: Optional[bool]  # 第二批策略是否被批准
    second_batch_strategies: Optional[Dict[str, Any]]  # 第二批专家的工作策略

    # 🆕 多轮审核控制 - 循环控制字段
    review_round: int  # 当前审核轮次（从0开始）
    review_history: Annotated[List[Dict[str, Any]], merge_lists]  # 审核历史记录
    best_result: Optional[Dict[str, Any]]  # 历史最佳专家结果
    best_score: float  # 历史最佳评分
    review_feedback: Optional[Dict[str, Any]]  # 审核反馈（传递给专家用于改进）
    
    # 🆕 v2.0 递进式审核结果字段
    review_result: Optional[Dict[str, Any]]  # 完整审核结果（红蓝评委甲方）
    final_ruling: Optional[str]  # 最终裁定文档（甲方输出的可执行改进路线图）
    improvement_suggestions: Annotated[List[Dict[str, Any]], merge_lists]  # 改进建议列表
    skip_second_review: Optional[bool]  # 整改后跳过第二次审核标记

    # 错误处理
    errors: List[Dict[str, Any]]
    retry_count: int
    
    # 🆕 输入拒绝字段（内容安全与领域过滤）
    rejection_reason: Optional[str]  # 拒绝原因代码
    rejection_message: Optional[str]  # 用户友好的拒绝提示消息
    domain_risk_flag: Optional[bool]  # 领域风险标记
    domain_risk_details: Optional[Dict[str, Any]]  # 领域风险详情

    # 统一输入验证字段（v7.3 - 合并 input_guard 和 domain_validator）
    initial_validation_passed: Optional[bool]  # 初始验证是否通过
    domain_classification: Optional[Dict[str, Any]]  # 领域分类结果
    safety_check_passed: Optional[bool]  # 内容安全检测是否通过
    domain_confidence: Optional[float]  # 初始领域置信度
    needs_secondary_validation: Optional[bool]  # 是否需要二次验证
    # 移除: task_complexity, suggested_workflow, suggested_experts, estimated_duration
    # 移除: complexity_reasoning, complexity_confidence
    # 原因: 复杂度判断已整合到项目总监，由LLM自主决策
    secondary_validation_passed: Optional[bool]  # 二次验证是否通过
    secondary_domain_confidence: Optional[float]  # 二次验证置信度
    domain_drift_detected: Optional[bool]  # 是否检测到领域漂移
    domain_user_confirmed: Optional[bool]  # 用户是否手动确认领域
    confidence_delta: Optional[float]  # 置信度变化量
    validated_confidence: Optional[float]  # 最终验证置信度
    secondary_validation_skipped: Optional[bool]  # 是否跳过二次验证
    secondary_validation_reason: Optional[str]  # 跳过二次验证的原因
    trust_initial_judgment: Optional[bool]  # 是否信任初始判断

    # 追问对话历史（v3.11新增）
    followup_history: Annotated[List[Dict[str, Any]], merge_lists]
    """
    追问对话历史记录，每个元素包含：
    - turn_id: 轮次编号
    - question: 用户问题
    - answer: 系统回答
    - intent: 意图类型
    - referenced_sections: 引用章节
    - timestamp: 时间戳
    """
    followup_turn_count: int
    """当前会话的追问轮次计数"""

    # 元数据
    metadata: Dict[str, Any]


class StateManager:
    """状态管理器"""
    
    @staticmethod
    def create_initial_state(
        user_input: str,
        session_id: str,
        user_id: Optional[str] = None
    ) -> ProjectAnalysisState:
        """创建初始状态"""
        now = datetime.now().isoformat()
        
        return ProjectAnalysisState(
            # 基础信息
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
            
            # 用户输入
            user_input=user_input,
            structured_requirements=None,
            feasibility_assessment=None,  # 🆕 V1.5可行性分析结果初始化,
            
            # 分析策略
            strategic_analysis=None,
            subagents=None,
            # agents_to_execute=None,  # 已移除（Fixed Mode 专用字段）
            agent_results={},

            # 专业分析结果（V2-V6 字段已移除，使用 agent_results 字典）
            # v2_design_research=None,
            # v3_technical_architecture=None,
            # v4_ux_design=None,
            # v5_business_model=None,
            # v6_implementation_plan=None,
            
            # 结果聚合
            aggregated_results=None,
            final_report=None,
            pdf_file_path=None,
            
            # 交互历史
            conversation_history=[],
            human_feedback=None,
            
            # 🆕 问卷流程控制初始化
            skip_calibration=False,  # 🆕 是否跳过校准问卷
            calibration_processed=False,
            calibration_skipped=False,
            calibration_questionnaire=None,
            calibration_answers=None,
            questionnaire_responses=None,
            questionnaire_summary=None,
            interaction_history=[],
            post_completion_followup_completed=False,

            # 🆕 追问对话历史初始化（v3.11新增）
            followup_history=[],
            followup_turn_count=0,

            # 流程控制
            current_stage=AnalysisStage.INIT.value,
            active_agents=[],
            completed_agents=[],
            failed_agents=[],

            # 🆕 批次调度初始化（2025-11-18）
            execution_batches=None,  # 将由BatchScheduler计算
            current_batch=0,
            total_batches=0,
            completed_batches=[],

            # 🆕 多轮审核控制 - 初始化
            review_round=0,
            review_history=[],
            best_result=None,
            best_score=0.0,
            review_feedback=None,
            
            # 🆕 v2.0 递进式审核结果 - 初始化
            review_result=None,
            final_ruling=None,
            improvement_suggestions=[],
            skip_second_review=False,
            
            # 错误处理
            errors=[],
            retry_count=0,
            
            # 元数据
            metadata={}
        )
    
    @staticmethod
    def update_state(state: ProjectAnalysisState, updates: Dict[str, Any]) -> ProjectAnalysisState:
        """更新状态"""
        updated_state = state.copy()
        updated_state.update(updates)
        updated_state["updated_at"] = datetime.now().isoformat()
        return updated_state

    @staticmethod
    def update_stage(state: ProjectAnalysisState, new_stage: AnalysisStage) -> Dict[str, Any]:
        """更新分析阶段"""
        return {
            "current_stage": new_stage.value,
            "updated_at": datetime.now().isoformat()
        }
    
    @staticmethod
    def add_agent_result(
        state: ProjectAnalysisState,
        agent_type: AgentType,
        result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        添加智能体分析结果

        ✅ 已修复: 移除对已删除的V2-V6枚举值的引用
        现在使用agent_results字典存储所有智能体结果
        """
        update = {
            "updated_at": datetime.now().isoformat()
        }

        # ✅ 修复: 不再使用已删除的V2-V6枚举值
        # 所有结果统一存储在agent_results字典中
        # 这个方法现在主要用于更新完成状态

        # 更新完成的智能体列表
        completed_agents = state.get("completed_agents", []).copy()
        if agent_type.value not in completed_agents:
            completed_agents.append(agent_type.value)
        update["completed_agents"] = completed_agents

        # 从活跃智能体列表中移除
        active_agents = state.get("active_agents", []).copy()
        if agent_type.value in active_agents:
            active_agents.remove(agent_type.value)
        update["active_agents"] = active_agents

        return update
    
    @staticmethod
    def add_error(
        state: ProjectAnalysisState,
        error_type: str,
        error_message: str,
        agent_type: Optional[AgentType] = None
    ) -> Dict[str, Any]:
        """添加错误信息"""
        error_info = {
            "type": error_type,
            "message": error_message,
            "timestamp": datetime.now().isoformat(),
            "agent": agent_type.value if agent_type else None
        }
        
        errors = state.get("errors", []).copy()
        errors.append(error_info)
        
        failed_agents = state.get("failed_agents", []).copy()
        if agent_type and agent_type.value not in failed_agents:
            failed_agents.append(agent_type.value)
        
        return {
            "errors": errors,
            "failed_agents": failed_agents,
            "updated_at": datetime.now().isoformat()
        }
    
    @staticmethod
    def is_analysis_complete(state: ProjectAnalysisState) -> bool:
        """
        检查分析是否完成

        ✅ 已修复: 移除对已删除的V2-V6枚举值的引用
        现在基于动态分派的智能体列表判断完成状态
        """
        completed_agents = state.get("completed_agents", [])
        subagents = state.get("subagents", {})

        # ✅ 修复: 基于动态分派的智能体判断完成状态
        # 不再使用硬编码的V2-V6枚举值
        if subagents:
            # 检查所有分派的智能体是否都已完成
            assigned_agents = list(subagents.keys())
            return all(agent in completed_agents for agent in assigned_agents)

        # 如果没有分派信息,检查agent_results是否有内容
        agent_results = state.get("agent_results", {})
        return len(agent_results) > 0 and len(completed_agents) > 0
    
    @staticmethod
    def get_analysis_progress(state: ProjectAnalysisState) -> Dict[str, Any]:
        """获取分析进度"""
        subagents = state.get("subagents", {})
        completed_agents = state.get("completed_agents", [])
        failed_agents = state.get("failed_agents", [])
        
        if subagents:
            total_agents = len(subagents)
            completed_count = len([agent for agent in subagents.keys() if agent in completed_agents])
            failed_count = len([agent for agent in subagents.keys() if agent in failed_agents])
        else:
            # 默认所有6个智能体
            total_agents = 6
            completed_count = len(completed_agents)
            failed_count = len(failed_agents)
        
        progress_percentage = (completed_count / total_agents * 100) if total_agents > 0 else 0
        
        return {
            "total_agents": total_agents,
            "completed_count": completed_count,
            "failed_count": failed_count,
            "progress_percentage": progress_percentage,
            "current_stage": state.get("current_stage", AnalysisStage.INIT.value)
        }
