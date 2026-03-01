# -*- coding: utf-8 -*-
"""
MT-1 (2026-03-01): API 数据模型

从 api/server.py 提取的所有 Pydantic BaseModel 定义。
纯数据模型，无服务器状态依赖，可独立测试。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

# ==================== 数据模型 ====================


class AnalysisRequest(BaseModel):
    """分析请求"""

    # Backward compatible aliases:
    # - legacy clients use `requirement` instead of `user_input`
    # - some clients may send `username`/`userId` etc; we only normalize what we actually need
    model_config = ConfigDict(populate_by_name=True, coerce_numbers_to_str=True)

    user_input: str = Field(validation_alias=AliasChoices("user_input", "requirement"))
    user_id: str = Field(default="web_user", validation_alias=AliasChoices("user_id", "username"))  # 用户ID
    #  v7.39: 分析模式 - normal(深度思考) 或 deep_thinking(深度思考pro)
    # 深度思考pro模式会为每个专家生成概念图像
    analysis_mode: str = Field(default="normal", validation_alias=AliasChoices("analysis_mode", "mode"))

    # Optional legacy field: accepted but currently not used by backend.
    domain: Optional[str] = None


class ResumeRequest(BaseModel):
    """恢复请求"""

    model_config = ConfigDict(populate_by_name=True)

    session_id: str
    # Backward compatible alias: some older clients used `user_response`
    resume_value: Any = Field(validation_alias=AliasChoices("resume_value", "user_response"))


class FollowupRequest(BaseModel):
    """追问请求（用于已完成的分析报告）"""

    session_id: str
    question: str
    requires_analysis: bool = True  # 是否需要重新分析


class SessionResponse(BaseModel):
    """会话响应"""

    session_id: str
    status: str
    message: str


class AnalysisStatus(BaseModel):
    """分析状态"""

    session_id: str
    status: str  # running, waiting_for_input, completed, failed, rejected
    current_stage: Optional[str] = None
    detail: Optional[str] = None  #  新增：当前节点的详细信息
    progress: float = 0.0
    history: Optional[List[Dict[str, Any]]] = None  #  新增：执行历史
    interrupt_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    traceback: Optional[str] = None  # 添加traceback字段用于调试
    rejection_message: Optional[str] = None  #  拒绝原因提示
    user_input: Optional[str] = None  #  v7.37.7: 用户原始输入


class AnalysisResult(BaseModel):
    """分析结果"""

    session_id: str
    status: str
    # 现行字段
    results: Optional[Any] = None
    final_report: Optional[Any] = None

    # 兼容旧字段（tests/api/test_analysis_endpoints.py 仍在使用）
    final_result: Optional[Any] = None
    agent_results: Optional[Any] = None


#  对话相关数据模型
class ConversationRequest(BaseModel):
    """对话请求"""

    session_id: str
    question: str
    context_hint: Optional[str] = None  # 可选：章节提示


class ConversationResponse(BaseModel):
    """对话响应"""

    answer: str
    intent: str
    references: List[str]


# ==================== 结构化报告类型 ====================


class ExecutiveSummaryResponse(BaseModel):
    """执行摘要响应"""

    project_overview: str = Field(default="", description="项目概述")
    key_findings: List[str] = Field(default_factory=list, description="关键发现列表")
    key_recommendations: List[str] = Field(default_factory=list, description="核心建议列表")
    success_factors: List[str] = Field(default_factory=list, description="成功要素列表")


#  Phase 1.4+ P4: 核心答案响应模型（向后兼容版）
class CoreAnswerResponse(BaseModel):
    """核心答案响应（向后兼容）"""

    question: str = Field(default="", description="从用户输入提取的核心问题")
    answer: str = Field(default="", description="直接明了的核心答案")
    deliverables: List[str] = Field(default_factory=list, description="交付物清单")
    timeline: str = Field(default="", description="预估时间线")
    budget_range: str = Field(default="", description="预算估算范围")


#  v7.0: 单个交付物的责任者答案响应
class DeliverableAnswerResponse(BaseModel):
    """单个交付物的责任者答案响应"""

    deliverable_id: str = Field(default="", description="交付物ID")
    deliverable_name: str = Field(default="", description="交付物名称")
    deliverable_type: str = Field(default="unknown", description="交付物类型")
    owner_role: str = Field(default="", description="责任者角色ID")
    owner_answer: str = Field(default="", description="责任者的核心答案")
    answer_summary: str = Field(default="", description="答案摘要")
    supporters: List[str] = Field(default_factory=list, description="支撑专家列表")
    quality_score: Optional[float] = Field(default=None, description="质量分数")


#  v7.0: 专家支撑链响应
class ExpertSupportChainResponse(BaseModel):
    """专家支撑链响应"""

    role_id: str = Field(default="", description="专家角色ID")
    role_name: str = Field(default="", description="专家名称")
    contribution_type: str = Field(default="support", description="贡献类型")
    contribution_summary: str = Field(default="", description="贡献摘要")
    related_deliverables: List[str] = Field(default_factory=list, description="关联的交付物ID")


#  v7.0: 增强版核心答案响应（支持多交付物）
class CoreAnswerV7Response(BaseModel):
    """
    v7.0 增强版核心答案响应 - 支持多个交付物

    核心理念：
    - 核心答案 = 各责任者的最终交付（不做LLM综合）
    - 每个交付物有一个 primary_owner，其输出即为该交付物的答案
    - 专家支撑链展示非 owner 专家的贡献
    """

    question: str = Field(default="", description="从用户输入提取的核心问题")
    deliverable_answers: List[DeliverableAnswerResponse] = Field(default_factory=list, description="各交付物的责任者答案列表")
    expert_support_chain: List[ExpertSupportChainResponse] = Field(default_factory=list, description="专家支撑链")
    timeline: str = Field(default="待定", description="预估时间线")
    budget_range: str = Field(default="待定", description="预算估算范围")

    # 向后兼容字段
    answer: str = Field(default="", description="综合摘要（向后兼容）")
    deliverables: List[str] = Field(default_factory=list, description="交付物清单（向后兼容）")


#  Phase 1.4+ v4.1: 洞察区块响应模型
class InsightsSectionResponse(BaseModel):
    """洞察区块响应 - 从需求分析师和所有专家中提炼的关键洞察"""

    key_insights: List[str] = Field(default_factory=list, description="3-5条核心洞察")
    cross_domain_connections: List[str] = Field(default_factory=list, description="跨领域关联发现")
    user_needs_interpretation: str = Field(default="", description="对用户需求的深层解读")


#  Phase 1.4+ v4.1: 推敲过程响应模型
class DeliberationProcessResponse(BaseModel):
    """推敲过程响应 - 项目总监的战略分析和决策思路"""

    inquiry_architecture: str = Field(default="", description="选择的探询架构类型")
    reasoning: str = Field(default="", description="为什么选择这个探询架构")
    role_selection: List[str] = Field(default_factory=list, description="选择的专家角色及理由")
    strategic_approach: str = Field(default="", description="整体战略方向")


#  Phase 1.4+ v4.1: 建议区块响应模型
class RecommendationsSectionResponse(BaseModel):
    """建议区块响应 - 整合所有专家的可执行建议"""

    immediate_actions: List[str] = Field(default_factory=list, description="立即可执行的行动")
    short_term_priorities: List[str] = Field(default_factory=list, description="短期优先级")
    long_term_strategy: List[str] = Field(default_factory=list, description="长期战略方向")
    risk_mitigation: List[str] = Field(default_factory=list, description="风险缓解措施")


class ReportSectionResponse(BaseModel):
    """报告章节响应"""

    section_id: str = Field(default="", description="章节ID")
    title: str = Field(default="", description="章节标题")
    content: str = Field(default="", description="章节内容")
    confidence: float = Field(default=0.0, description="置信度")


class ComprehensiveAnalysisResponse(BaseModel):
    """综合分析响应"""

    cross_domain_insights: List[str] = Field(default_factory=list, description="跨领域洞察")
    integrated_recommendations: List[str] = Field(default_factory=list, description="整合建议")
    risk_assessment: List[str] = Field(default_factory=list, description="风险评估")
    implementation_roadmap: List[str] = Field(default_factory=list, description="实施路线图")


class ConclusionsResponse(BaseModel):
    """结论响应"""

    project_analysis_summary: str = Field(default="", description="项目分析总结")
    next_steps: List[str] = Field(default_factory=list, description="下一步行动建议")
    success_metrics: List[str] = Field(default_factory=list, description="成功指标")


class ReviewFeedbackItemResponse(BaseModel):
    """审核反馈项响应"""

    issue_id: str = Field(default="", description="问题ID")
    reviewer: str = Field(default="", description="审核专家")
    issue_type: str = Field(default="", description="问题类型")
    description: str = Field(default="", description="问题描述")
    response: str = Field(default="", description="响应措施")
    status: str = Field(default="", description="状态")
    priority: str = Field(default="medium", description="优先级")


class ReviewFeedbackResponse(BaseModel):
    """审核反馈响应"""

    red_team_challenges: List[ReviewFeedbackItemResponse] = Field(default_factory=list)
    blue_team_validations: List[ReviewFeedbackItemResponse] = Field(default_factory=list)
    judge_rulings: List[ReviewFeedbackItemResponse] = Field(default_factory=list)
    client_decisions: List[ReviewFeedbackItemResponse] = Field(default_factory=list)
    iteration_summary: str = Field(default="")


class ReviewRoundDataResponse(BaseModel):
    """审核轮次数据响应"""

    round_number: int = Field(default=0)
    red_score: int = Field(default=0)
    blue_score: int = Field(default=0)
    judge_score: int = Field(default=0)
    issues_found: int = Field(default=0)
    issues_resolved: int = Field(default=0)
    timestamp: str = Field(default="")


class ReviewVisualizationResponse(BaseModel):
    """审核可视化响应"""

    rounds: List[ReviewRoundDataResponse] = Field(default_factory=list)
    final_decision: str = Field(default="")
    total_rounds: int = Field(default=0)
    improvement_rate: float = Field(default=0.0)


class ChallengeItemResponse(BaseModel):
    """单个挑战项响应"""

    expert_id: str = Field(default="", description="专家ID")
    expert_name: str = Field(default="", description="专家名称")
    challenged_item: str = Field(default="", description="质疑的事项")
    challenge_type: str = Field(default="", description="挑战类型: reinterpret/flag_risk/escalate")
    severity: str = Field(default="should-fix", description="严重程度: must-fix/should-fix")
    rationale: str = Field(default="", description="质疑理由")
    proposed_alternative: str = Field(default="", description="建议的替代方案")
    design_impact: str = Field(default="", description="对设计的影响")
    decision: str = Field(default="", description="处理决策: accept/synthesize/escalate")


class ChallengeDetectionResponse(BaseModel):
    """挑战检测响应"""

    has_challenges: bool = Field(default=False, description="是否有挑战")
    total_count: int = Field(default=0, description="挑战总数")
    must_fix_count: int = Field(default=0, description="必须修复的问题数")
    should_fix_count: int = Field(default=0, description="建议修复的问题数")
    challenges: List[ChallengeItemResponse] = Field(default_factory=list, description="挑战列表")
    handling_summary: str = Field(default="", description="处理摘要")


class QuestionnaireResponseItem(BaseModel):
    """单个问卷回答项"""

    question_id: str = Field(default="", description="问题ID")
    question: str = Field(default="", description="问题内容")
    answer: str = Field(default="", description="用户回答")
    context: str = Field(default="", description="问题上下文说明")


class QuestionnaireResponseData(BaseModel):
    """问卷回答数据"""

    responses: List[QuestionnaireResponseItem] = Field(default_factory=list, description="问卷回答列表")
    timestamp: str = Field(default="", description="提交时间")
    analysis_insights: str = Field(default="", description="从回答中提取的关键洞察")


class RequirementsAnalysisResponse(BaseModel):
    """需求分析结果（需求分析师原始输出 - 融合用户修改后的最终版本）"""

    project_overview: str = Field(default="", description="项目概览")
    core_objectives: List[str] = Field(default_factory=list, description="核心目标")
    project_tasks: List[str] = Field(default_factory=list, description="项目任务")
    narrative_characters: List[str] = Field(default_factory=list, description="叙事角色")
    physical_contexts: List[str] = Field(default_factory=list, description="物理环境")
    constraints_opportunities: Dict[str, Any] = Field(default_factory=dict, description="约束与机遇")


class StructuredReportResponse(BaseModel):
    """结构化报告响应"""

    inquiry_architecture: str = Field(default="", description="探询架构类型")
    #  Phase 1.4+ P4: 核心答案（用户最关心的TL;DR）
    #  v7.0: 支持新的多交付物格式和旧格式（向后兼容）
    # 如果有 deliverable_answers 字段，则是 v7.0 格式
    # 否则是旧格式（只有 answer 字段）
    core_answer: Optional[Dict[str, Any]] = Field(default=None, description="核心答案（支持v7.0多交付物格式和旧格式）")
    #  Phase 1.4+ v4.1: 新增洞察、推敲过程、建议区块
    insights: Optional[InsightsSectionResponse] = Field(default=None, description="需求洞察（LLM综合）")
    requirements_analysis: Optional[RequirementsAnalysisResponse] = Field(default=None, description="需求分析结果（需求分析师原始输出）")
    deliberation_process: Optional[DeliberationProcessResponse] = Field(default=None, description="推敲过程")
    recommendations: Optional[RecommendationsSectionResponse] = Field(default=None, description="建议")
    executive_summary: ExecutiveSummaryResponse = Field(default_factory=ExecutiveSummaryResponse)
    sections: List[ReportSectionResponse] = Field(default_factory=list)
    comprehensive_analysis: ComprehensiveAnalysisResponse = Field(default_factory=ComprehensiveAnalysisResponse)
    conclusions: ConclusionsResponse = Field(default_factory=ConclusionsResponse)
    expert_reports: Dict[str, str] = Field(default_factory=dict, description="专家原始报告")
    review_feedback: Optional[ReviewFeedbackResponse] = None
    questionnaire_responses: Optional[QuestionnaireResponseData] = Field(default=None, description="问卷回答数据")
    review_visualization: Optional[ReviewVisualizationResponse] = None
    challenge_detection: Optional[ChallengeDetectionResponse] = Field(default=None, description="挑战检测结果")
    #  v7.4: 执行元数据汇总
    execution_metadata: Optional[Dict[str, Any]] = Field(default=None, description="执行元数据汇总")
    #  v3.0.26: 思维导图内容结构（以内容为中心）
    mindmap_content: Optional[Dict[str, Any]] = Field(default=None, description="思维导图内容结构")
    #  深度思考模式概念图（集中生成）
    generated_images: Optional[List[str]] = Field(default=None, description="AI 概念图（深度思考模式）")
    image_prompts: Optional[List[str]] = Field(default=None, description="AI 概念图提示词（深度思考模式）")
    image_top_constraints: Optional[str] = Field(default=None, description="AI 概念图顶层约束（深度思考模式）")
    #  v7.39: 专家概念图（深度思考pro模式）
    generated_images_by_expert: Optional[Dict[str, Any]] = Field(default=None, description="专家概念图（深度思考pro模式）")
    #  v7.154: 雷达图维度数据
    radar_dimensions: Optional[List[Dict[str, Any]]] = Field(default=None, description="雷达图维度列表")
    radar_dimension_values: Optional[Dict[str, Any]] = Field(default=None, description="雷达图维度值")


class ReportResponse(BaseModel):
    """报告响应（专门用于前端获取报告）"""

    session_id: str
    report_text: str
    report_pdf_path: Optional[str] = None
    created_at: str
    user_input: str = Field(default="", description="用户原始输入")
    suggestions: List[str] = Field(default_factory=list)
    conversation_id: Optional[int] = None
    structured_report: Optional[StructuredReportResponse] = Field(default=None, description="结构化报告数据")


# ==================== 报告数据清洗辅助函数 ====================
