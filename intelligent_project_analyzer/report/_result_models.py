"""
结果聚合器 - Pydantic 数据模型

所有报告相关的结构化模型定义，从 result_aggregator.py 中拆分而来。
供 ResultAggregatorAgent 及外部模块使用。
"""

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================================================
# Pydantic 模型定义 - 用于结构化输出
# ============================================================================


class ExecutiveSummary(BaseModel):
    """
    执行摘要

     配置 extra='forbid' 以支持 OpenAI Structured Outputs 的 strict mode
     移除所有默认值,使字段成为必填项
    """

    model_config = ConfigDict(extra="forbid")

    project_overview: str = Field(description="项目概述")
    key_findings: List[str] = Field(description="关键发现列表")
    key_recommendations: List[str] = Field(description="核心建议列表")
    success_factors: List[str] = Field(description="成功要素列表")


#  Phase 1.4+ P4: 核心答案模型
class CoreAnswer(BaseModel):
    """
    核心答案 - 用户最关心的TL;DR信息
    """

    model_config = ConfigDict(extra="forbid")

    question: str = Field(description="从用户输入提取的核心问题")
    answer: str = Field(description="直接明了的核心答案（1-2句话）")
    deliverables: List[str] = Field(description="交付物清单")
    timeline: str = Field(description="预估时间线")
    budget_range: str = Field(description="预算估算范围")


#  v7.0: 单个交付物的责任者答案
class DeliverableAnswer(BaseModel):
    """
    单个交付物的责任者答案 - 直接从 owner 专家的输出提取，不做 LLM 二次综合
    """

    model_config = ConfigDict(extra="allow")  # 允许额外字段以兼容扩展

    deliverable_id: str = Field(description="交付物ID (如 D1, D2)")
    deliverable_name: str = Field(description="交付物名称/描述")
    deliverable_type: str = Field(default="unknown", description="交付物类型")
    owner_role: str = Field(description="责任者角色ID")
    owner_answer: str = Field(description="责任者的核心答案（直接提取，不综合）")
    answer_summary: str = Field(default="", description="答案摘要（200字以内）")
    supporters: List[str] = Field(default_factory=list, description="支撑专家列表")
    quality_score: float | None = Field(default=None, description="质量分数（0-100）")

    #  v7.108: 关联的概念图
    concept_images: List[Dict[str, Any]] = Field(default_factory=list, description="该交付物关联的概念图列表（ImageMetadata格式）")


#  v7.0: 专家支撑链
class ExpertSupportChain(BaseModel):
    """
    专家支撑链 - 展示非 owner 专家的贡献
    """

    model_config = ConfigDict(extra="allow")

    role_id: str = Field(description="专家角色ID")
    role_name: str = Field(default="", description="专家名称")
    contribution_type: str = Field(default="support", description="贡献类型")
    contribution_summary: str = Field(default="", description="贡献摘要")
    related_deliverables: List[str] = Field(default_factory=list, description="关联的交付物ID列表")


#  v7.0: 增强版核心答案（支持多交付物）
class CoreAnswerV7(BaseModel):
    """
    v7.0 增强版核心答案 - 支持多个交付物，每个交付物有独立的责任者答案

    核心理念：
    - 核心答案 = 各责任者的最终交付（不做LLM综合）
    - 每个交付物有一个 primary_owner，其输出即为该交付物的答案
    - 专家支撑链展示非 owner 专家的贡献
    """

    model_config = ConfigDict(extra="allow")

    question: str = Field(description="从用户输入提取的核心问题")
    deliverable_answers: List[DeliverableAnswer] = Field(default_factory=list, description="各交付物的责任者答案列表（按优先级排序）")
    expert_support_chain: List[ExpertSupportChain] = Field(default_factory=list, description="专家支撑链（非owner专家的贡献）")
    timeline: str = Field(default="待定", description="预估时间线")
    budget_range: str = Field(default="待定", description="预算估算范围")

    # 向后兼容字段
    answer: str = Field(default="", description="综合摘要（向后兼容）")
    deliverables: List[str] = Field(default_factory=list, description="交付物清单（向后兼容）")


#  新增：洞察区块
class InsightsSection(BaseModel):
    """
    洞察 - 从所有专家分析中提炼的关键洞察
    """

    model_config = ConfigDict(extra="forbid")

    key_insights: List[str] = Field(description="3-5条核心洞察，每条1-2句话")
    cross_domain_connections: List[str] = Field(description="跨领域关联发现（如设计与商业的关联）")
    user_needs_interpretation: str = Field(description="对用户需求的深层解读")


#  新增：推敲过程区块
class DeliberationProcess(BaseModel):
    """
    推敲过程 - 项目总监的战略分析和决策思路
    """

    model_config = ConfigDict(extra="forbid")

    inquiry_architecture: str = Field(description="选择的探询架构类型")
    reasoning: str = Field(description="为什么选择这个探询架构（2-3句话）")
    role_selection: List[str] = Field(description="选择的专家角色及理由")
    strategic_approach: str = Field(description="整体战略方向（3-5句话）")


#  新增：建议区块（V2升级 - 五维度分类）
class RecommendationItem(BaseModel):
    """单条建议"""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(description="建议内容（50-150字）")

    dimension: Literal["critical", "difficult", "overlooked", "risky", "ideal"] = Field(
        description="建议维度：critical=重点, difficult=难点, overlooked=易忽略, risky=有风险, ideal=理想"
    )

    reasoning: str = Field(description="为什么属于这个维度（1-2句话）")

    source_expert: str = Field(description="建议来源专家（如 V2_设计总监_2-2）")

    estimated_effort: str | None = Field(default=None, description="预估工作量（如'2-3天'、'1周'、'需专业团队'）")

    dependencies: List[str] = Field(default=[], description="依赖的其他建议内容（用于排序）")


class RecommendationsSection(BaseModel):
    """
    建议提醒区块（V2升级 - 五维度分类）

    维度说明：
    - critical（重点）: 项目核心工作，必须完成
    - difficult（难点）: 技术难度高，需要重点攻克
    - overlooked（易忽略）: 容易被遗漏但很重要
    - risky（有风险）: 不做会出问题
    - ideal（理想）: 锦上添花，有余力再做
    """

    model_config = ConfigDict(extra="forbid")

    recommendations: List[RecommendationItem] = Field(description="所有建议列表（按维度分类）")

    summary: str = Field(description="建议总览（2-3句话概括核心要点）")


# ============================================================================
# 专家内容模型定义 - 替换Dict[str, Any]
# ============================================================================


class V2DesignDirectorContent(BaseModel):
    """V2设计总监的内容结构"""

    model_config = ConfigDict(extra="forbid")

    spatial_concept: str = Field(default="", description="空间概念与大创意")
    narrative_translation: str = Field(default="", description="空间叙事转译方案")
    aesthetic_framework: str = Field(default="", description="美学框架定义")
    design_language: str = Field(default="", description="设计语言体系")
    functional_planning: str = Field(default="", description="功能布局与动线规划")
    sensory_experience: str = Field(default="", description="感官体验设计")
    material_palette: str = Field(default="", description="材质与色彩方案")
    key_visuals: str = Field(default="", description="关键视觉画面描述")
    implementation_guidance: str = Field(default="", description="实施指导建议")


class V3NarrativeExpertContent(BaseModel):
    """V3人物及叙事专家的内容结构"""

    model_config = ConfigDict(extra="forbid")

    character_archetype: str = Field(default="", description="核心人物原型定义")
    narrative_worldview: str = Field(default="", description="叙事世界观构建")
    core_theme: str = Field(default="", description="核心母题与精神内核")
    emotional_journey: str = Field(default="", description="情感旅程地图")
    scene_storyboard: str = Field(default="", description="关键场景分镜脚本")
    sensory_script: str = Field(default="", description="五感设计脚本")
    symbolic_elements: str = Field(default="", description="意象与符号体系")
    experience_choreography: str = Field(default="", description="体验编排方案")
    narrative_guidelines: str = Field(default="", description="叙事指导原则")


class V4DesignResearcherContent(BaseModel):
    """V4设计研究员的内容结构"""

    model_config = ConfigDict(extra="forbid")

    case_studies: str = Field(default="", description="相关案例研究与分析")
    design_patterns: str = Field(default="", description="识别的设计模式与规律")
    methodology_insights: str = Field(default="", description="方法论解构与提炼")
    knowledge_framework: str = Field(default="", description="知识框架构建")
    trend_analysis: str = Field(default="", description="前沿趋势分析")
    best_practices: str = Field(default="", description="最佳实践总结")
    theoretical_foundation: str = Field(default="", description="理论基础支撑")
    reference_materials: str = Field(default="", description="参考资料与文献")
    application_guidelines: str = Field(default="", description="应用指导建议")


class V5ScenarioExpertContent(BaseModel):
    """V5场景与用户生态专家的内容结构"""

    model_config = ConfigDict(extra="forbid")

    context_analysis: str = Field(default="", description="情境分析(B2B/住宅/B2C)")
    user_ecosystem: str = Field(default="", description="用户生态系统测绘")
    behavioral_patterns: str = Field(default="", description="行为模式分析")
    life_script: str = Field(default="", description="生活剧本/消费路径")
    trend_insights: str = Field(default="", description="情境化趋势洞察")
    core_value_proposition: str = Field(default="", description="核心价值主张")
    design_challenges: str = Field(default="", description="设计挑战定义")
    stakeholder_analysis: str = Field(default="", description="利益相关方分析")
    success_metrics: str = Field(default="", description="成功指标定义")


class V6ChiefEngineerContent(BaseModel):
    """V6专业总工程师的内容结构"""

    model_config = ConfigDict(extra="forbid")

    feasibility_assessment: str = Field(default="", description="技术可行性评估")
    risk_analysis: str = Field(default="", description="风险识别与应对")
    system_integration: str = Field(default="", description="多系统集成方案")
    material_specifications: str = Field(default="", description="材料选择与规格")
    construction_technology: str = Field(default="", description="建造工艺方案")
    cost_estimation: str = Field(default="", description="成本估算与控制")
    compliance_requirements: str = Field(default="", description="法规合规要求")
    lifecycle_analysis: str = Field(default="", description="全生命周期分析")
    implementation_roadmap: str = Field(default="", description="实施路线图")


class V7EmotionalInsightContent(BaseModel):
    """V7情感洞察专家的内容结构"""

    model_config = ConfigDict(extra="forbid")

    emotional_landscape: str = Field(default="", description="情绪地图：空间情绪转化路径")
    spiritual_aspirations: str = Field(default="", description="精神追求：基于马斯洛需求层次的精神目标")
    psychological_safety_needs: str = Field(default="", description="心理安全需求：安全基地需求和恐惧对抗策略")
    ritual_behaviors: str = Field(default="", description="仪式行为：日常仪式感行为及其心理意义")
    memory_anchors: str = Field(default="", description="记忆锚点：承载情感记忆的物品和元素")
    human_centered_synthesis: str = Field(default="", description="人性维度综合：整体情感洞察与设计建议")


# ============================================================================
# 报告章节数据模型
# ============================================================================


class ReportSectionWithId(BaseModel):
    """
    报告章节数据 - 包含section_id字段

     使用List[ReportSectionWithId]替代Dict[str, ReportSectionData]
     解决OpenAI Structured Outputs对动态键字典支持不佳的问题
     配置 extra='forbid' 以支持 OpenAI Structured Outputs 的 strict mode
    """

    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(description="章节ID,如design_research, technical_architecture等")
    title: str = Field(description="章节标题")
    content: str = Field(description="章节内容,包含该领域的详细分析(使用字符串格式以确保LLM能够正确返回)")
    confidence: float = Field(description="分析置信度,0-1之间", ge=0, le=1)


class ComprehensiveAnalysis(BaseModel):
    """
    综合分析

     配置 extra='forbid' 以支持 OpenAI Structured Outputs 的 strict mode
     移除所有默认值,使字段成为必填项
    """

    model_config = ConfigDict(extra="forbid")

    cross_domain_insights: List[str] = Field(description="跨领域洞察")
    integrated_recommendations: List[str] = Field(description="整合建议")
    risk_assessment: List[str] = Field(description="风险评估")
    implementation_roadmap: List[str] = Field(description="实施路线图")


class Conclusions(BaseModel):
    """
    结论和建议

     配置 extra='forbid' 以支持 OpenAI Structured Outputs 的 strict mode
     移除所有默认值,使字段成为必填项
    """

    model_config = ConfigDict(extra="forbid")

    project_analysis_summary: str = Field(description="项目分析总结")
    next_steps: List[str] = Field(description="下一步行动建议")
    success_metrics: List[str] = Field(description="成功指标")


class ReviewFeedbackItem(BaseModel):
    """单个审核反馈项"""

    model_config = ConfigDict(extra="forbid")

    issue_id: str = Field(description="问题ID（如R1, R2, B1等）")
    reviewer: str = Field(description="审核专家（红队/蓝队/评委/甲方）")
    issue_type: str = Field(description="问题类型（风险/优化/建议）")
    description: str = Field(description="问题描述")
    response: str = Field(description="如何响应（采取的改进措施）")
    status: str = Field(description="状态（已修复/进行中/待定）")
    priority: str = Field(description="优先级（high/medium/low）")

    @field_validator("priority", mode="before")
    @classmethod
    def ensure_priority_is_string(cls, v):
        """确保 priority 字段是字符串类型（兼容 int 输入）"""
        if isinstance(v, int):
            # 将数字优先级映射为字符串
            priority_map = {1: "high", 2: "medium", 3: "low"}
            return priority_map.get(v, "medium")
        return str(v) if v is not None else "medium"


class ReviewFeedback(BaseModel):
    """审核反馈章节"""

    model_config = ConfigDict(extra="forbid")

    red_team_challenges: List[ReviewFeedbackItem] = Field(description="红队质疑点列表")
    blue_team_validations: List[ReviewFeedbackItem] = Field(description="蓝队验证结果")
    judge_rulings: List[ReviewFeedbackItem] = Field(description="评委裁决要点")
    client_decisions: List[ReviewFeedbackItem] = Field(description="甲方最终决策")
    iteration_summary: str = Field(description="迭代改进过程总结")


class QuestionnaireResponse(BaseModel):
    """单个问卷问题的回答"""

    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(description="问题ID")
    question: str = Field(description="问题内容")
    answer: str = Field(description="用户回答")
    context: str = Field(description="问题上下文说明")


class QuestionnaireResponses(BaseModel):
    """用户访谈记录（校准问卷回答）"""

    model_config = ConfigDict(extra="forbid")

    responses: List[QuestionnaireResponse] = Field(description="问卷回答列表")
    timestamp: str = Field(description="提交时间")
    analysis_insights: str = Field(description="从回答中提取的关键洞察")


class ReviewRoundData(BaseModel):
    """单轮审核数据"""

    model_config = ConfigDict(extra="forbid")

    round_number: int = Field(description="轮次编号")
    red_score: int = Field(description="红队评分（0-100）")
    blue_score: int = Field(description="蓝队评分（0-100）")
    judge_score: int = Field(description="评委评分（0-100）")
    issues_found: int = Field(description="发现的问题数量")
    issues_resolved: int = Field(description="解决的问题数量")
    timestamp: str = Field(description="审核时间")


class ReviewVisualization(BaseModel):
    """多轮审核可视化数据"""

    model_config = ConfigDict(extra="forbid")

    rounds: List[ReviewRoundData] = Field(description="各轮审核数据")
    final_decision: str = Field(description="最终决策（通过/有条件通过/拒绝）")
    total_rounds: int = Field(description="总审核轮次")
    improvement_rate: float = Field(description="改进率（0-1之间）")


class FinalReport(BaseModel):
    """
     重构后的报告结构 - 完全动态化，无预定义章节

    新的报告结构：
    1. 用户原始输入（从state获取）
    2. 问卷（仅展示有修改的）
    3. 洞察（从所有专家分析中提炼）
    4. 答案（核心答案TL;DR）
    5. 推敲过程（项目总监的战略分析 + 角色选择理由）
    6. 各专家的报告
    7. 建议（整合所有专家的建议）

     v7.154: 将 extra='forbid' 改为 extra='ignore' 以允许 LLM 返回额外字段
    这样可以避免因 LLM 返回 sections 等额外字段而导致验证失败
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    #  3. 洞察（已废弃 - 改用需求分析师的 structured_requirements）
    insights: InsightsSection | None = Field(default=None, description="[已废弃] 从所有专家分析中提炼的核心洞察（不再使用）")

    #  4. 答案（必填）
    core_answer: CoreAnswer = Field(description="核心答案：用户最关心的TL;DR信息")

    #  5. 推敲过程（必填）
    deliberation_process: DeliberationProcess = Field(description="项目总监的战略分析和决策思路")

    #  6. 各专家的报告（必填）
    #  v7.11: 添加default_factory防止None值引起验证失败
    expert_reports: Dict[str, str] = Field(
        default_factory=dict,
        description="""
        专家原始报告字典，完整展示各专家的分析内容

        格式示例:
        {
            "V2_设计总监_2-1": "完整的设计分析...",
            "V3_人物及叙事专家_3-1": "完整的叙事分析...",
            ...
        }
        """,
    )

    #  7. 建议（必填）
    recommendations: RecommendationsSection = Field(description="整合所有专家的可执行建议")

    #  2. 问卷（可选，仅有修改时填充）
    questionnaire_responses: QuestionnaireResponses | None = Field(
        default=None, description="用户访谈记录（校准问卷的完整回答，仅展示有修改的问题）"
    )

    #  审核反馈（可选）
    review_feedback: ReviewFeedback | None = Field(default=None, description="审核反馈章节（包含红队质疑、蓝队验证、评委裁决、迭代改进过程）")

    #  审核可视化（可选）
    review_visualization: ReviewVisualization | None = Field(default=None, description="多轮审核可视化数据（红蓝对抗过程的火力图）")

    #  v7.154: 添加 sections 字段以支持 LLM 返回的章节数据
    sections: List[Dict[str, Any]] | None = Field(default=None, description="报告章节列表（LLM 可能返回此字段）")


# ============================================================================
# 公开导出列表
# ============================================================================

__all__ = [
    "ExecutiveSummary",
    "CoreAnswer",
    "DeliverableAnswer",
    "ExpertSupportChain",
    "CoreAnswerV7",
    "InsightsSection",
    "DeliberationProcess",
    "RecommendationItem",
    "RecommendationsSection",
    "V2DesignDirectorContent",
    "V3NarrativeExpertContent",
    "V4DesignResearcherContent",
    "V5ScenarioExpertContent",
    "V6ChiefEngineerContent",
    "V7EmotionalInsightContent",
    "ReportSectionWithId",
    "ComprehensiveAnalysis",
    "Conclusions",
    "ReviewFeedbackItem",
    "ReviewFeedback",
    "QuestionnaireResponse",
    "QuestionnaireResponses",
    "ReviewRoundData",
    "ReviewVisualization",
    "FinalReport",
]
