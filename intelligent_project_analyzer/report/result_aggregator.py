"""
结果聚合器

负责整合所有智能体的分析结果，生成最终报告结构
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..agents.base import LLMAgent
from ..core.prompt_manager import PromptManager
from ..core.state import AgentType, AnalysisStage, ProjectAnalysisState
from ..core.types import AnalysisResult, ReportSection
from ..utils.jtbd_parser import transform_jtbd_to_natural_language

# ============================================================================
# Pydantic 模型定义 - 用于结构化输出
# ============================================================================


class ExecutiveSummary(BaseModel):
    """
    执行摘要

    ✅ 配置 extra='forbid' 以支持 OpenAI Structured Outputs 的 strict mode
    ✅ 移除所有默认值,使字段成为必填项
    """

    model_config = ConfigDict(extra="forbid")

    project_overview: str = Field(description="项目概述")
    key_findings: List[str] = Field(description="关键发现列表")
    key_recommendations: List[str] = Field(description="核心建议列表")
    success_factors: List[str] = Field(description="成功要素列表")


# 🔥 Phase 1.4+ P4: 核心答案模型
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


# 🆕 v7.0: 单个交付物的责任者答案
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
    quality_score: Optional[float] = Field(default=None, description="质量分数（0-100）")

    # 🆕 v7.108: 关联的概念图
    concept_images: List[Dict[str, Any]] = Field(default_factory=list, description="该交付物关联的概念图列表（ImageMetadata格式）")


# 🆕 v7.0: 专家支撑链
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


# 🆕 v7.0: 增强版核心答案（支持多交付物）
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


# 🔥 新增：洞察区块
class InsightsSection(BaseModel):
    """
    洞察 - 从所有专家分析中提炼的关键洞察
    """

    model_config = ConfigDict(extra="forbid")

    key_insights: List[str] = Field(description="3-5条核心洞察，每条1-2句话")
    cross_domain_connections: List[str] = Field(description="跨领域关联发现（如设计与商业的关联）")
    user_needs_interpretation: str = Field(description="对用户需求的深层解读")


# 🔥 新增：推敲过程区块
class DeliberationProcess(BaseModel):
    """
    推敲过程 - 项目总监的战略分析和决策思路
    """

    model_config = ConfigDict(extra="forbid")

    inquiry_architecture: str = Field(description="选择的探询架构类型")
    reasoning: str = Field(description="为什么选择这个探询架构（2-3句话）")
    role_selection: List[str] = Field(description="选择的专家角色及理由")
    strategic_approach: str = Field(description="整体战略方向（3-5句话）")


# 🔥 新增：建议区块（V2升级 - 五维度分类）
class RecommendationItem(BaseModel):
    """单条建议"""

    model_config = ConfigDict(extra="forbid")

    content: str = Field(description="建议内容（50-150字）")

    dimension: Literal["critical", "difficult", "overlooked", "risky", "ideal"] = Field(
        description="建议维度：critical=重点, difficult=难点, overlooked=易忽略, risky=有风险, ideal=理想"
    )

    reasoning: str = Field(description="为什么属于这个维度（1-2句话）")

    source_expert: str = Field(description="建议来源专家（如 V2_设计总监_2-2）")

    estimated_effort: Optional[str] = Field(default=None, description="预估工作量（如'2-3天'、'1周'、'需专业团队'）")

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

    ✅ 使用List[ReportSectionWithId]替代Dict[str, ReportSectionData]
    ✅ 解决OpenAI Structured Outputs对动态键字典支持不佳的问题
    ✅ 配置 extra='forbid' 以支持 OpenAI Structured Outputs 的 strict mode
    """

    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(description="章节ID,如design_research, technical_architecture等")
    title: str = Field(description="章节标题")
    content: str = Field(description="章节内容,包含该领域的详细分析(使用字符串格式以确保LLM能够正确返回)")
    confidence: float = Field(description="分析置信度,0-1之间", ge=0, le=1)


class ComprehensiveAnalysis(BaseModel):
    """
    综合分析

    ✅ 配置 extra='forbid' 以支持 OpenAI Structured Outputs 的 strict mode
    ✅ 移除所有默认值,使字段成为必填项
    """

    model_config = ConfigDict(extra="forbid")

    cross_domain_insights: List[str] = Field(description="跨领域洞察")
    integrated_recommendations: List[str] = Field(description="整合建议")
    risk_assessment: List[str] = Field(description="风险评估")
    implementation_roadmap: List[str] = Field(description="实施路线图")


class Conclusions(BaseModel):
    """
    结论和建议

    ✅ 配置 extra='forbid' 以支持 OpenAI Structured Outputs 的 strict mode
    ✅ 移除所有默认值,使字段成为必填项
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
    🔥 重构后的报告结构 - 完全动态化，无预定义章节

    新的报告结构：
    1. 用户原始输入（从state获取）
    2. 问卷（仅展示有修改的）
    3. 洞察（从所有专家分析中提炼）
    4. 答案（核心答案TL;DR）
    5. 推敲过程（项目总监的战略分析 + 角色选择理由）
    6. 各专家的报告
    7. 建议（整合所有专家的建议）

    🔧 v7.154: 将 extra='forbid' 改为 extra='ignore' 以允许 LLM 返回额外字段
    这样可以避免因 LLM 返回 sections 等额外字段而导致验证失败
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # 🔥 3. 洞察（已废弃 - 改用需求分析师的 structured_requirements）
    insights: Optional[InsightsSection] = Field(default=None, description="[已废弃] 从所有专家分析中提炼的核心洞察（不再使用）")

    # 🔥 4. 答案（必填）
    core_answer: CoreAnswer = Field(description="核心答案：用户最关心的TL;DR信息")

    # 🔥 5. 推敲过程（必填）
    deliberation_process: DeliberationProcess = Field(description="项目总监的战略分析和决策思路")

    # 🔥 6. 各专家的报告（必填）
    # 🔧 v7.11: 添加default_factory防止None值引起验证失败
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

    # 🔥 7. 建议（必填）
    recommendations: RecommendationsSection = Field(description="整合所有专家的可执行建议")

    # 🔥 2. 问卷（可选，仅有修改时填充）
    questionnaire_responses: Optional[QuestionnaireResponses] = Field(
        default=None, description="用户访谈记录（校准问卷的完整回答，仅展示有修改的问题）"
    )

    # 🔥 审核反馈（可选）
    review_feedback: Optional[ReviewFeedback] = Field(default=None, description="审核反馈章节（包含红队质疑、蓝队验证、评委裁决、迭代改进过程）")

    # 🔥 审核可视化（可选）
    review_visualization: Optional[ReviewVisualization] = Field(default=None, description="多轮审核可视化数据（红蓝对抗过程的火力图）")

    # 🆕 v7.154: 添加 sections 字段以支持 LLM 返回的章节数据
    sections: Optional[List[Dict[str, Any]]] = Field(default=None, description="报告章节列表（LLM 可能返回此字段）")


class ResultAggregatorAgent(LLMAgent):
    """结果聚合器智能体"""

    def __init__(self, llm_model, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_type=AgentType.RESULT_AGGREGATOR,
            name="结果聚合器",
            description="整合所有分析结果，生成结构化的最终报告",
            llm_model=llm_model,
            config=config,
        )

        # 初始化提示词管理器
        self.prompt_manager = PromptManager()

    def validate_input(self, state: ProjectAnalysisState) -> bool:
        """验证输入是否有效"""
        agent_results = state.get("agent_results") or {}  # 🔥 修复：确保不为 None
        return len(agent_results) > 0

    def prepare_messages(self, state: ProjectAnalysisState) -> List:
        """
        准备LLM消息 - 重写父类方法以使用正确的消息格式

        🔧 性能优化: 移除few-shot示例，直接使用structured output
        ✅ 减少token消耗约60%，加速LLM响应
        """
        messages = []

        # ✅ 使用 SystemMessage 传递系统提示词
        system_prompt = self.get_system_prompt()
        messages.append(SystemMessage(content=system_prompt))

        # 🔧 性能优化: 直接使用structured output，无需few-shot示例
        task_description = self.get_task_description(state)
        messages.append(HumanMessage(content=task_description))

        return messages

    def get_system_prompt(self) -> str:
        """
        获取系统提示词 - 从外部配置加载

        ✅ 修复: 简化提示词，聚焦核心任务
        ✅ 优化: 明确 sections 字段的填充规则
        """
        # 尝试从外部配置加载
        prompt = self.prompt_manager.get_prompt("result_aggregator")

        # 如果配置不存在，抛出错误（不再使用硬编码 fallback）
        if not prompt:
            raise ValueError(
                "❌ 未找到提示词配置: result_aggregator\n"
                "请确保配置文件存在: config/prompts/result_aggregator.yaml\n"
                "系统无法使用硬编码提示词，请检查配置文件。"
            )

        return prompt

    def get_task_description(self, state: ProjectAnalysisState) -> str:
        """
        获取具体任务描述 - v3.0版本（包含审核反馈、问卷回答、可视化数据）

        ✅ 新增: review_feedback（审核反馈章节）
        ✅ 新增: questionnaire_responses（用户访谈记录）
        ✅ 新增: review_visualization（多轮审核可视化）
        """
        agent_results = state.get("agent_results") or {}
        structured_requirements = state.get("structured_requirements") or {}
        strategic_analysis = state.get("strategic_analysis") or {}  # 🔥 修复：确保不为 None

        # 🆕 获取审核结果（原有逻辑）
        final_ruling = state.get("final_ruling") or ""
        improvement_suggestions = state.get("improvement_suggestions") or []

        # 🆕 获取完整审核数据（新增）
        review_result = state.get("review_result") or {}  # 🔥 修复：确保不为 None
        review_history = state.get("review_history") or []  # 🔥 修复：确保不为 None

        # 🆕 获取问卷数据（🔧 修复: 同时获取 calibration_answers 作为备用）
        calibration_questionnaire = state.get("calibration_questionnaire") or {}
        questionnaire_responses = state.get("questionnaire_responses") or {}
        questionnaire_summary = state.get("questionnaire_summary") or {}
        calibration_answers = state.get("calibration_answers") or {}

        # 🔧 修复: 如果 questionnaire_responses 为空，尝试从 calibration_answers 构建
        if not questionnaire_responses.get("entries") and not questionnaire_responses.get("answers"):
            if calibration_answers:
                logger.info(
                    f"🔧 [问卷数据恢复] questionnaire_responses 为空，从 calibration_answers 恢复 ({len(calibration_answers)} 个答案)"
                )
                questionnaire_responses = {"answers": calibration_answers, "source": "calibration_answers_fallback"}

        # 提取项目总监的战略分析信息
        query_type = strategic_analysis.get("query_type", "深度优先探询")
        query_type_reasoning = strategic_analysis.get("query_type_reasoning", "")

        # ========== 1. 构建审核反馈数据 ==========
        review_feedback_data = None
        if review_result or review_history:
            review_feedback_data = self._extract_review_feedback(review_result, review_history, improvement_suggestions)

        # ========== 2. 构建问卷回答数据 ==========
        questionnaire_data = None
        if questionnaire_summary or questionnaire_responses or calibration_questionnaire:
            questionnaire_data = self._extract_questionnaire_data(
                calibration_questionnaire, questionnaire_responses, questionnaire_summary
            )

        # ========== 3. 构建可视化数据 ==========
        visualization_data = None
        if review_history:
            visualization_data = self._extract_visualization_data(review_history, review_result)

        # 构建审核结果部分（原有逻辑，保留用于提示词）
        review_section = ""
        if final_ruling:
            review_section = f"""

## 📋 审核系统的最终裁定

{final_ruling}

### 改进建议摘要
"""
            if improvement_suggestions:
                for idx, suggestion in enumerate(improvement_suggestions[:5], 1):
                    priority = suggestion.get("priority", "should_fix")
                    deadline = suggestion.get("deadline", "before_launch")
                    review_section += f"{idx}. [{priority}] {suggestion.get('issue_id', 'N/A')} - {deadline}\n"
            else:
                review_section += "无需改进，分析质量已达标。\n"

        # 构建新增数据部分
        additional_data_section = ""
        if review_feedback_data:
            additional_data_section += f"""

## 🔍 审核反馈数据（用于填充review_feedback字段）

{json.dumps(review_feedback_data, ensure_ascii=False, indent=2)}
"""

        if questionnaire_data:
            additional_data_section += f"""

## 📝 问卷回答数据（用于填充questionnaire_responses字段）

{json.dumps(questionnaire_data, ensure_ascii=False, indent=2)}
"""

        if visualization_data:
            additional_data_section += f"""

## 📊 可视化数据（用于填充review_visualization字段）

{json.dumps(visualization_data, ensure_ascii=False, indent=2)}
"""

        return f"""请整合以下分析结果，生成综合项目分析报告。

## 项目总监的作战计划

**探询架构类型：** {query_type}
**判定理由：** {query_type_reasoning}

## 项目基本信息

**项目概述：** {structured_requirements.get("project_overview", "暂无")}
**核心目标：** {json.dumps(structured_requirements.get("core_objectives", []), ensure_ascii=False)}

## V2-V6 专家的分析成果

{self._format_agent_results(agent_results)}
{review_section}
{additional_data_section}

## 任务要求

1. **识别探询架构**：使用上述探询架构类型（{query_type}）
2. **填充sections字段**：为每个专家创建对应的section条目
   - 使用专家标注的章节名称作为键（如 "design_research"）
   - 将专家的完整分析结果放入content字段
   - 保留专家的置信度
3. **整合审核结果**：如果存在最终裁定，请在综合分析中体现改进建议
4. **生成综合分析**：整合所有专家的洞察
5. **填充新增字段**（如果数据存在）：
   - review_feedback: 使用上面提供的审核反馈数据
   - questionnaire_responses: 使用上面提供的问卷回答数据
   - review_visualization: 使用上面提供的可视化数据
6. **输出格式**：纯JSON，不要添加markdown标记

⚠️ 重要：必须为所有专家创建section条目，不要遗漏任何一个！

请立即生成JSON格式的报告。"""

    def execute(
        self, state: ProjectAnalysisState, config: RunnableConfig, store: Optional[BaseStore] = None
    ) -> AnalysisResult:
        """执行结果聚合 - 使用结构化输出"""
        start_time = time.time()

        try:
            logger.info(f"Starting result aggregation for session {state.get('session_id')}")

            # 🚀 Phase 1.4: 发送初始进度更新
            self._update_progress(state, "准备整合专家分析结果", 0.0)

            # 验证输入
            if not self.validate_input(state):
                raise ValueError("Invalid input: no agent results found")

            # 准备消息
            self._update_progress(state, "构建聚合提示词", 0.1)
            messages = self.prepare_messages(state)

            # 🔧 性能优化: 精简JSON格式提醒（structured output已包含格式要求）
            json_format_reminder = SystemMessage(content="OUTPUT: Use structured JSON schema provided")
            messages.insert(1, json_format_reminder)

            # 使用 with_structured_output 强制 LLM 返回符合 Pydantic 模型的结构
            # ⚠️ 注意: 由于 content 字段是 Dict[str, Any]（灵活字典），无法使用 strict mode
            # OpenAI strict mode 要求所有对象都设置 additionalProperties: false
            # 但 Dict[str, Any] 需要 additionalProperties: true 来允许任意键
            # 因此使用 function_calling 方法而不是 json_schema + strict
            logger.info("Using structured output with Pydantic model (function_calling method)")

            # 🚀 Phase 1.4: 进度更新
            self._update_progress(state, "配置结构化输出模型", 0.2)

            structured_llm = self.llm_model.with_structured_output(
                FinalReport,
                method="function_calling",  # 使用 function_calling 以支持灵活的 Dict[str, Any]
                include_raw=True,  # 官方推荐：处理复杂schema时避免抛出异常
            )
            logger.info("Successfully configured function_calling method")

            # 调用 LLM 并获取结构化输出
            # ✅ 修复: 添加更详细的错误处理，捕获超时和网络错误
            # ✅ 修复: 显式传递 max_tokens 和 request_timeout 参数
            # 🔧 新增: 添加重试逻辑以应对不稳定的API响应
            # 这些参数在 ChatOpenAI 初始化时设置，但为了确保它们被使用，我们在这里再次传递
            import os

            max_tokens = int(os.getenv("MAX_TOKENS", "32000"))
            request_timeout = int(os.getenv("LLM_TIMEOUT", "600"))
            max_retries = int(os.getenv("MAX_RETRIES", "3"))
            retry_delay = int(os.getenv("RETRY_DELAY", "5"))

            result = None
            last_error = None

            # 🚀 Phase 1.4: 进度更新
            agent_count = len(state.get("agent_results", {}))
            self._update_progress(state, f"调用LLM整合{agent_count}位专家的分析结果（预计60-90秒）", 0.3)

            # 🔧 重试循环
            for attempt in range(max_retries):
                try:
                    # 🚀 Phase 1.4: 进度更新（重试提示）
                    if attempt > 0:
                        self._update_progress(state, f"LLM调用重试中（第{attempt + 1}次尝试）", 0.3 + (attempt * 0.05))

                    logger.info(
                        f"Invoking LLM (attempt {attempt + 1}/{max_retries}) with max_tokens={max_tokens}, request_timeout={request_timeout}"
                    )

                    # 记录开始时间
                    start_time = time.time()

                    result = structured_llm.invoke(messages, max_tokens=max_tokens, request_timeout=request_timeout)

                    # 记录结束时间
                    elapsed_time = time.time() - start_time
                    logger.info(f"LLM invocation completed in {elapsed_time:.2f}s")

                    # 🚀 Phase 1.4: 进度更新
                    self._update_progress(state, "LLM响应完成，正在解析结果", 0.6)

                    # 成功，跳出重试循环
                    break

                except json.JSONDecodeError as e:
                    # JSON解析错误 - 通常是响应被截断或超时
                    last_error = e
                    logger.error(f"Attempt {attempt + 1}/{max_retries} - JSON parsing failed: {e}")
                    logger.error(f"This usually indicates a timeout or incomplete response from the API")

                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"All {max_retries} attempts failed")
                        logger.info("Attempting to use fallback parsing method")
                        raise ValueError(
                            f"LLM response was incomplete or truncated after {max_retries} attempts. This may be due to timeout or network issues. Original error: {e}"
                        )

                except Exception as e:
                    # 其他错误（网络超时、API错误等）
                    last_error = e
                    logger.error(f"Attempt {attempt + 1}/{max_retries} - LLM invocation failed: {e}")

                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        logger.error(f"All {max_retries} attempts failed")
                        raise

            # 如果所有重试都失败了
            if result is None:
                raise ValueError(f"LLM invocation failed after {max_retries} attempts. Last error: {last_error}")

            # 检查是否有解析错误
            if result.get("parsing_error"):
                # 解析失败，使用备用方案
                logger.warning(f"Structured output parsing failed: {result['parsing_error']}")
                logger.info("Falling back to manual parsing")

                # 🚀 Phase 1.4: 进度更新
                self._update_progress(state, "结构化解析失败，使用备用解析方案", 0.65)

                raw_message = result["raw"]
                final_report = self._parse_final_report(raw_message.content, state)

                # ✅ P0修复: 备用解析路径也必须提取真实数据
                # 🔧 v7.1.4: 确保无条件覆盖，避免与主路径重复
                logger.info("Fallback path: extracting real expert_reports from state")
                if "expert_reports" not in final_report or not final_report["expert_reports"]:
                    final_report["expert_reports"] = self._extract_expert_reports(state)
                final_report["challenge_resolutions"] = self._extract_challenge_resolutions(state)

                # 🔥 v7.5修复: fallback 路径也必须提取问卷数据
                # 原因：问卷数据提取逻辑原本只在成功解析路径，导致 fallback 时前端显示空问卷
                self._update_progress(state, "[Fallback] 提取校准问卷回答", 0.7)
                calibration_questionnaire = state.get("calibration_questionnaire") or {}
                questionnaire_responses_state = state.get("questionnaire_responses") or {}
                questionnaire_summary = state.get("questionnaire_summary") or {}

                if calibration_questionnaire or questionnaire_responses_state or questionnaire_summary:
                    real_questionnaire_data = self._extract_questionnaire_data(
                        calibration_questionnaire, questionnaire_responses_state, questionnaire_summary
                    )
                    if real_questionnaire_data and real_questionnaire_data.get("responses"):
                        final_report["questionnaire_responses"] = real_questionnaire_data
                        logger.info(
                            f"✅ [Fallback] 已提取 questionnaire_responses: {len(real_questionnaire_data['responses'])} 条回答"
                        )
                    else:
                        logger.debug("ℹ️ [Fallback] 无问卷数据可提取")

                # 🔥 v7.5修复: fallback 路径也必须提取需求分析结果
                # 原因：需求分析师的输出需要正确传递到前端
                if "requirements_analysis" not in final_report or not final_report.get("requirements_analysis"):
                    structured_requirements = state.get("structured_requirements") or {}
                    if structured_requirements:
                        final_report["requirements_analysis"] = structured_requirements
                        logger.info(f"✅ [Fallback] 已提取 requirements_analysis")

                # ✅ P2修复: 确保 raw_content 保存原始LLM响应
                final_report["raw_content"] = raw_message.content
                final_report["metadata"] = {
                    **final_report.get("metadata", {}),
                    "parsing_mode": "fallback",
                    "fallback_reason": str(result.get("parsing_error", "unknown")),
                }
            else:
                # 解析成功
                logger.info("Successfully received and parsed structured output from LLM")

                # 🚀 Phase 1.4: 进度更新
                self._update_progress(state, "结构化解析成功，正在验证数据完整性", 0.7)

                final_report_pydantic = result["parsed"]

                if final_report_pydantic is None:
                    logger.warning("Structured output parsing returned None, falling back to manual parsing")
                    self._update_progress(state, "解析结果为空，使用备用方案", 0.72)
                    raw_message = result.get("raw")
                    if raw_message:
                        final_report = self._parse_final_report(raw_message.content, state)
                        # ✅ P0修复: 备用解析路径也必须提取真实数据
                        # 🔧 v7.1.4: 确保无条件覆盖，避免与主路径重复
                        logger.info("Fallback path (None parsed): extracting real expert_reports from state")
                        if "expert_reports" not in final_report or not final_report["expert_reports"]:
                            final_report["expert_reports"] = self._extract_expert_reports(state)
                        final_report["challenge_resolutions"] = self._extract_challenge_resolutions(state)

                        # 🔥 v7.5修复: fallback_none_parsed 路径也必须提取问卷和需求分析
                        self._update_progress(state, "[Fallback-None] 提取校准问卷回答", 0.74)
                        calibration_questionnaire = state.get("calibration_questionnaire") or {}
                        questionnaire_responses_state = state.get("questionnaire_responses") or {}
                        questionnaire_summary = state.get("questionnaire_summary") or {}

                        if calibration_questionnaire or questionnaire_responses_state or questionnaire_summary:
                            real_questionnaire_data = self._extract_questionnaire_data(
                                calibration_questionnaire, questionnaire_responses_state, questionnaire_summary
                            )
                            if real_questionnaire_data and real_questionnaire_data.get("responses"):
                                final_report["questionnaire_responses"] = real_questionnaire_data
                                logger.info(
                                    f"✅ [Fallback-None] 已提取 questionnaire_responses: {len(real_questionnaire_data['responses'])} 条回答"
                                )

                        # 提取需求分析
                        if "requirements_analysis" not in final_report or not final_report.get("requirements_analysis"):
                            structured_requirements = state.get("structured_requirements") or {}
                            if structured_requirements:
                                final_report["requirements_analysis"] = structured_requirements
                                logger.info(f"✅ [Fallback-None] 已提取 requirements_analysis")

                        # ✅ P2修复: 确保 raw_content 保存原始LLM响应
                        final_report["raw_content"] = raw_message.content
                        final_report["metadata"] = {
                            **final_report.get("metadata", {}),
                            "parsing_mode": "fallback_none_parsed",
                        }
                    else:
                        raise ValueError("LLM response parsed as None and no raw message available")
                else:
                    # 转换 Pydantic 模型为字典
                    # 🔥 Phase 0优化: 排除None和默认值以减少token消耗
                    final_report = final_report_pydantic.model_dump(exclude_none=True, exclude_defaults=True)

                # ✅ 新增: 检查 sections 是否为空，如果为空则手动填充
                if not final_report.get("sections") or len(final_report["sections"]) == 0:
                    logger.warning("LLM returned empty sections, manually populating from agent_results")
                    self._update_progress(state, "LLM未返回章节数据，正在手动填充", 0.75)
                    final_report["sections"] = self._manually_populate_sections(state)
                    logger.info(f"Manually populated {len(final_report['sections'])} sections")

                # ✅ 修复v4.0: 始终用真实数据覆盖 expert_reports
                # 原因：LLM 可能返回占位符文本如 "{...内容略...}"，必须用真实数据覆盖
                # 🔧 v7.1.4修复: 简化逻辑，无条件覆盖以避免重复
                logger.info("Overwriting expert_reports with actual expert content from state")
                self._update_progress(state, "提取专家原始报告", 0.8)
                real_expert_reports = self._extract_expert_reports(state)

                # 直接覆盖，无需检查占位符（避免重复赋值）
                final_report["expert_reports"] = real_expert_reports

                logger.info(f"Extracted {len(final_report['expert_reports'])} expert reports")

                # 🔥 修复：从 sections 中提取 requirements_analysis 并提升到顶层
                # 原因：requirements_analysis 被 _manually_populate_sections 放在了 sections 数组中
                # 但前端期望它在顶层（与 insights、deliberation_process 同级）
                sections_list = final_report.get("sections", [])
                if isinstance(sections_list, list):
                    for section in sections_list:
                        if isinstance(section, dict) and section.get("section_id") == "requirements_analysis":
                            # 提取 requirements_analysis 的 content（可能是JSON字符串）
                            content_str = section.get("content", "")
                            if content_str:
                                try:
                                    # 尝试解析为字典
                                    requirements_data = (
                                        json.loads(content_str) if isinstance(content_str, str) else content_str
                                    )
                                    final_report["requirements_analysis"] = requirements_data
                                    logger.info("✅ 已从 sections 提取 requirements_analysis 到顶层")
                                except json.JSONDecodeError:
                                    logger.warning(f"⚠️ requirements_analysis 内容不是有效 JSON: {content_str[:100]}")
                            break

                # 🆕 v3.5.1: 添加挑战解决结果
                self._update_progress(state, "提取专家挑战解决结果", 0.85)
                final_report["challenge_resolutions"] = self._extract_challenge_resolutions(state)

                # 🆕 v4.1修复: 强制用真实问卷数据覆盖 questionnaire_responses
                # 原因：LLM 结构化输出可能返回 None（可选字段），导致前端显示"未回答"
                self._update_progress(state, "提取校准问卷回答", 0.87)
                calibration_questionnaire = state.get("calibration_questionnaire") or {}
                questionnaire_responses_state = state.get("questionnaire_responses") or {}
                questionnaire_summary = state.get("questionnaire_summary") or {}

                if calibration_questionnaire or questionnaire_responses_state or questionnaire_summary:
                    real_questionnaire_data = self._extract_questionnaire_data(
                        calibration_questionnaire, questionnaire_responses_state, questionnaire_summary
                    )
                    if real_questionnaire_data and real_questionnaire_data.get("responses"):
                        final_report["questionnaire_responses"] = real_questionnaire_data
                        logger.info(f"✅ 已覆盖 questionnaire_responses: {len(real_questionnaire_data['responses'])} 条回答")
                    else:
                        logger.debug("ℹ️ 无问卷数据可覆盖")

                # 添加元数据
                self._update_progress(state, "生成报告元数据", 0.9)

                # 🆕 v7.4: 增强执行元数据，提升用户体验
                # 收集更多统计数据
                agent_results = state.get("agent_results", {})
                questionnaire_responses = final_report.get("questionnaire_responses", {})
                batches = state.get("batches", [])
                review_iterations = state.get("review_iterations", 0)

                # 计算问卷回答数量
                questionnaire_count = 0
                if questionnaire_responses:
                    responses = questionnaire_responses.get("responses", [])
                    questionnaire_count = len([r for r in responses if r.get("answer") and r.get("answer") != "未回答"])

                # 计算平均置信度
                confidence_values = []
                for role_id, result in agent_results.items():
                    if isinstance(result, dict):
                        # 从任务导向专家输出中提取置信度
                        exec_meta = result.get("execution_metadata", {})
                        if exec_meta and isinstance(exec_meta, dict):
                            conf = exec_meta.get("confidence")
                            if conf is not None:
                                confidence_values.append(float(conf))

                avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else None

                # 获取复杂度级别
                task_complexity = state.get("task_complexity", "complex")
                complexity_display = {"simple": "简单", "medium": "中等", "complex": "复杂"}.get(task_complexity, "复杂")

                # 计算分析耗时（如果有开始时间）
                analysis_duration = None
                created_at = state.get("created_at")
                if created_at:
                    try:
                        if isinstance(created_at, str):
                            analysis_start_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        else:
                            analysis_start_time = created_at
                        duration_seconds = (datetime.now() - analysis_start_time.replace(tzinfo=None)).total_seconds()
                        if duration_seconds < 60:
                            analysis_duration = f"{int(duration_seconds)}秒"
                        elif duration_seconds < 3600:
                            minutes = int(duration_seconds // 60)
                            seconds = int(duration_seconds % 60)
                            analysis_duration = f"{minutes}分{seconds}秒"
                        else:
                            hours = int(duration_seconds // 3600)
                            minutes = int((duration_seconds % 3600) // 60)
                            analysis_duration = f"{hours}时{minutes}分"
                    except Exception as e:
                        logger.debug(f"计算分析耗时失败: {e}")

                # 🔥 修复: 从 deliberation_process 中提取 inquiry_architecture
                inquiry_arch = "深度优先探询"  # 默认值
                deliberation = final_report.get("deliberation_process")
                if deliberation:
                    if isinstance(deliberation, dict):
                        inquiry_arch = deliberation.get("inquiry_architecture", inquiry_arch)
                    elif hasattr(deliberation, "inquiry_architecture"):
                        inquiry_arch = deliberation.inquiry_architecture or inquiry_arch
                # 也同步到顶层，方便其他地方使用
                final_report["inquiry_architecture"] = inquiry_arch

                final_report["metadata"] = {
                    "generated_at": datetime.now().isoformat(),
                    "session_id": state.get("session_id"),
                    "total_agents": len(agent_results),
                    "overall_confidence": self._calculate_overall_confidence(state),
                    "estimated_pages": self._estimate_report_pages(final_report),
                    "inquiry_architecture": inquiry_arch,
                    # 🆕 v7.4 新增字段
                    "total_batches": len(batches) if batches else 1,
                    "complexity_level": complexity_display,
                    "questionnaire_answered": questionnaire_count,
                    "review_rounds": review_iterations,
                    "confidence_average": avg_confidence,
                    "analysis_duration": analysis_duration,
                    # 专家分布统计
                    "expert_distribution": self._get_expert_distribution(agent_results),
                }

                # 保存原始 LLM 响应内容
                # ✅ P2修复: 仅在未设置时才设置，避免覆盖备用路径的值
                if "raw_content" not in final_report or not final_report.get("raw_content"):
                    raw_msg = result.get("raw")
                    if raw_msg:
                        final_report["raw_content"] = raw_msg.content
                    else:
                        final_report["raw_content"] = str(final_report_pydantic)

            # 🆕 v7.0: 从责任者输出中提取交付物答案，覆盖 LLM 生成的 core_answer
            self._update_progress(state, "提取交付物责任者答案", 0.92)
            deliverable_metadata = state.get("deliverable_metadata") or {}

            if deliverable_metadata:
                logger.info(f"🎯 [v7.0] 检测到 {len(deliverable_metadata)} 个交付物元数据，开始提取责任者答案")
                extracted_core_answer = self._extract_deliverable_answers(state)

                # 覆盖 LLM 生成的 core_answer
                if extracted_core_answer.get("deliverable_answers"):
                    final_report["core_answer"] = extracted_core_answer
                    logger.info(
                        f"✅ [v7.0] 已用责任者答案覆盖 core_answer: {len(extracted_core_answer['deliverable_answers'])} 个交付物"
                    )
                else:
                    logger.warning("⚠️ [v7.0] 未提取到交付物答案，保留 LLM 生成的 core_answer")
            else:
                logger.info("ℹ️ [v7.0] 无交付物元数据，保留 LLM 生成的 core_answer")

            # 🆕 v7.108: 提取概念图数据并转换为前端格式
            self._update_progress(state, "提取概念图数据", 0.93)
            generated_images_by_expert = self._extract_generated_images_by_expert(state)
            if generated_images_by_expert:
                final_report["generated_images_by_expert"] = generated_images_by_expert
                total_images = sum(len(expert_data["images"]) for expert_data in generated_images_by_expert.values())
                logger.info(f"✅ [v7.108] 已提取 {len(generated_images_by_expert)} 个专家的 {total_images} 张概念图")
            else:
                logger.debug("ℹ️ [v7.108] 无概念图数据可提取")

            # 🆕 v7.122: 统一处理搜索引用（去重、验证、聚合）
            self._update_progress(state, "处理搜索引用", 0.94)
            search_references = self._consolidate_search_references(state)
            if search_references:
                final_report["search_references"] = search_references
                logger.info(f"✅ [v7.122] 已处理 {len(search_references)} 条搜索引用")
            else:
                logger.debug("ℹ️ [v7.122] 无搜索引用数据")

            # 创建分析结果
            self._update_progress(state, "构建最终分析结果", 0.95)
            result = self.create_analysis_result(
                content=str(final_report.get("executive_summary", {})),
                structured_data=final_report,
                confidence=self._calculate_overall_confidence(state),
                sources=["all_agents", "requirements_analysis", "comprehensive_analysis"],
            )

            end_time = time.time()
            self._track_execution_time(start_time, end_time)

            # 🚀 Phase 1.4: 最终进度更新
            self._update_progress(state, "终审聚合完成", 1.0)

            logger.info("Result aggregation completed successfully")
            return result

        except Exception as e:
            error = self.handle_error(e, "Result aggregation")
            raise error

    def _update_progress(self, state: ProjectAnalysisState, detail: str, progress: float):
        """
        🚀 Phase 1.4: 更新进度到状态（用于WebSocket推送）

        Args:
            state: 当前状态
            detail: 进度详情描述
            progress: 进度值（0.0-1.0）
        """
        try:
            # 更新状态中的进度信息
            state["current_stage"] = "终审聚合"
            state["detail"] = detail
            state["progress"] = progress

            logger.info(f"📊 [终审聚合] {detail} ({progress*100:.0f}%)")
        except Exception as e:
            # 进度更新失败不应阻塞主流程
            logger.warning(f"⚠️ 进度更新失败: {e}")

    def _format_agent_results(self, agent_results: Dict[str, Any]) -> str:
        """格式化智能体结果用于聚合输出 - 支持TaskOrientedExpertOutput结构"""
        if not agent_results:
            return "(no agent results available)"

        formatted_blocks: List[str] = []

        for agent_id, result in agent_results.items():
            if not result:
                continue

            # 检查是否为TaskOrientedExpertOutput结构
            structured_output = result.get("structured_output")
            if structured_output and isinstance(structured_output, dict):
                # 新的任务导向输出格式
                formatted_block = self._format_task_oriented_output(agent_id, result, structured_output)
            else:
                # 传统格式（向后兼容）
                formatted_block = self._format_legacy_output(agent_id, result)

            if formatted_block:
                formatted_blocks.append(formatted_block)

        return "\n\n".join(formatted_blocks) if formatted_blocks else "(no agent results available)"

    def _format_task_oriented_output(
        self, agent_id: str, result: Dict[str, Any], structured_output: Dict[str, Any]
    ) -> str:
        """
        格式化TaskOrientedExpertOutput结构的专家输出

        Args:
            agent_id: 专家ID
            result: 完整的专家执行结果
            structured_output: TaskOrientedExpertOutput结构化数据

        Returns:
            str: 格式化的输出字符串
        """
        lines = []

        # 🆕 V7情感洞察专家特殊处理
        if agent_id.startswith("7-") or agent_id.startswith("V7_"):
            expert_name = result.get("expert_name", "V7_情感洞察专家")
            confidence = structured_output.get("confidence", 0.0)

            lines.append(f"### {expert_name} ({agent_id}) - 人性维度洞察")
            lines.append(f"**分析置信度**: {confidence:.1%}")
            lines.append("")

            # 提取情感字段
            emotional_fields = {
                "emotional_landscape": "情绪地图",
                "spiritual_aspirations": "精神追求",
                "psychological_safety_needs": "心理安全需求",
                "ritual_behaviors": "仪式行为洞察",
                "memory_anchors": "记忆锚点识别",
            }

            for field_key, field_name in emotional_fields.items():
                field_value = structured_output.get(field_key)
                if field_value:
                    lines.append(f"**{field_name}**:")
                    if isinstance(field_value, dict):
                        for k, v in field_value.items():
                            lines.append(f"  - {k}: {v}")
                    elif isinstance(field_value, list):
                        for item in field_value:
                            if isinstance(item, dict):
                                lines.append(f"  - {json.dumps(item, ensure_ascii=False)}")
                            else:
                                lines.append(f"  - {item}")
                    else:
                        lines.append(f"  {field_value}")
                    lines.append("")

            # targeted_analysis特殊处理
            targeted = structured_output.get("targeted_analysis")
            if targeted:
                lines.append("**专项情感分析**:")
                lines.append(json.dumps(targeted, ensure_ascii=False, indent=2))
                lines.append("")

            return "\n".join(lines).strip()

        # 原有V2-V6专家处理逻辑
        # 专家基本信息
        expert_summary = structured_output.get("expert_summary", {})
        expert_name = expert_summary.get("expert_name", result.get("expert_name", agent_id))
        objective = expert_summary.get("objective_statement", "未指定目标")

        lines.append(f"### {expert_name} ({agent_id}) - 任务导向输出")
        lines.append(f"**完成目标**: {objective}")
        lines.append("")

        # 任务结果
        task_results = structured_output.get("task_results", [])
        if task_results:
            lines.append("**交付物结果**:")
            for i, deliverable in enumerate(task_results, 1):
                name = deliverable.get("deliverable_name", f"交付物{i}")
                content = deliverable.get("content", "")
                format_type = deliverable.get("format", "analysis")
                completeness = deliverable.get("completeness_score", 0.0)
                methodology = deliverable.get("methodology", "未指定")

                lines.append(f"  {i}. **{name}** ({format_type}, 完成度: {completeness:.1%})")
                lines.append(f"     方法: {methodology}")

                # 内容摘要（限制长度）
                if content:
                    if len(content) > 500:
                        content_preview = content[:500] + "..."
                    else:
                        content_preview = content
                    lines.append(f"     内容: {content_preview}")
                lines.append("")

        # 协议执行状态
        protocol_execution = structured_output.get("protocol_execution", {})
        if protocol_execution:
            final_status = protocol_execution.get("final_status", "unknown")
            confidence_level = protocol_execution.get("confidence_level", 0.0)
            lines.append(f"**协议执行状态**: {final_status} (信心水平: {confidence_level:.1%})")

            # 自主行动
            autonomy_actions = protocol_execution.get("autonomy_actions_taken", [])
            if autonomy_actions:
                lines.append("**采取的自主行动**:")
                for action in autonomy_actions[:3]:  # 限制显示前3个
                    lines.append(f"  - {action}")
                if len(autonomy_actions) > 3:
                    lines.append(f"  - ... (共{len(autonomy_actions)}项)")

            # 挑战和重新解释
            challenges = protocol_execution.get("challenges_raised", [])
            reinterpretations = protocol_execution.get("reinterpretations_made", [])
            if challenges:
                lines.append(f"**提出挑战**: {len(challenges)}项")
            if reinterpretations:
                lines.append(f"**重新解释**: {len(reinterpretations)}项")
            lines.append("")

        # 验证清单
        validation_checklist = structured_output.get("validation_checklist", [])
        if validation_checklist:
            met_criteria = sum(1 for item in validation_checklist if item.get("status") == "met")
            total_criteria = len(validation_checklist)
            lines.append(f"**质量验证**: {met_criteria}/{total_criteria} 项标准满足")
            lines.append("")

        # 原始输出引用（如果需要）
        if result.get("analysis"):
            analysis = result["analysis"]
            if len(analysis) > 200:
                analysis_preview = analysis[:200] + "..."
            else:
                analysis_preview = analysis
            lines.append(f"**原始输出预览**: {analysis_preview}")
            lines.append("")

        return "\n".join(lines).strip()

    def _format_legacy_output(self, agent_id: str, result: Dict[str, Any]) -> str:
        """
        格式化传统格式的专家输出（向后兼容）
        """
        role_name = result.get("role_name", result.get("expert_name", agent_id))
        confidence = result.get("confidence", 0.0)

        structured_data = result.get("structured_data", {})
        if isinstance(structured_data, dict):
            structured_str = json.dumps(structured_data, ensure_ascii=False, indent=2)
            if len(structured_str) > 2000:
                structured_str = structured_str[:2000] + "\n... (truncated)"
        else:
            structured_str = str(structured_data)

        narrative = result.get("analysis") or result.get("content") or ""
        if isinstance(narrative, str) and len(narrative) > 2000:
            narrative = narrative[:2000] + "\n... (truncated)"
        if not narrative:
            narrative = "_No narrative summary provided._"

        return "\n".join(
            [
                f"### {role_name} ({agent_id}) - 传统格式",
                f"confidence: {confidence:.2f}",
                "structured_data:",
                structured_str or "{}",
                "narrative_summary:",
                narrative,
            ]
        )

    def _parse_final_report(self, llm_response: str, state: ProjectAnalysisState) -> Dict[str, Any]:
        """解析最终报告结构"""
        try:
            # 尝试提取JSON部分
            start_idx = llm_response.find("{")
            end_idx = llm_response.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = llm_response[start_idx:end_idx]
                final_report = json.loads(json_str)
            else:
                # 如果没有找到JSON，创建基础结构
                final_report = self._create_fallback_report(llm_response, state)

            # 添加元数据
            final_report["metadata"] = {
                "generated_at": datetime.now().isoformat(),
                "session_id": state.get("session_id"),
                "total_agents": len(state.get("agent_results", {})),
                "overall_confidence": self._calculate_overall_confidence(state),
                "estimated_pages": self._estimate_report_pages(final_report),
            }

            return final_report

        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from final report, using fallback structure")
            return self._create_fallback_report(llm_response, state)

    def _create_fallback_report(self, content: str, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        创建备用的报告结构

        🔧 v7.154: 增强 fallback 路径，从专家报告中提取实际内容而非占位符
        """
        structured_requirements = state.get("structured_requirements", {})
        agent_results = state.get("agent_results", {})
        active_agents = state.get("active_agents", [])
        strategic_analysis = state.get("strategic_analysis", {})

        # ✅ P1修复: 使用动态角色ID提取内容，而非硬编码的agent key
        # 辅助函数：根据动态role_id提取内容
        def extract_content_by_role_prefix(prefix: str) -> Dict[str, Any]:
            """根据角色前缀从动态role_id中提取structured_data"""
            for role_id in active_agents:
                if role_id.startswith(prefix):
                    agent_result = agent_results.get(role_id, {})
                    if isinstance(agent_result, dict):
                        return agent_result.get("structured_data", agent_result.get("content", {}))
            return {}

        # 辅助函数：根据动态role_id提取confidence
        def extract_confidence_by_role_prefix(prefix: str) -> float:
            """根据角色前缀从动态role_id中提取confidence"""
            for role_id in active_agents:
                if role_id.startswith(prefix):
                    agent_result = agent_results.get(role_id, {})
                    if isinstance(agent_result, dict):
                        return agent_result.get("confidence", 0.0)
            return 0.0

        # 🆕 v7.154: 从专家报告中提取关键发现
        def extract_key_findings() -> List[str]:
            """从专家报告中提取关键发现"""
            findings = []
            for role_id in active_agents:
                if not any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_", "V7_"]):
                    continue
                agent_result = agent_results.get(role_id, {})
                if not isinstance(agent_result, dict):
                    continue

                # 从 structured_data 中提取
                structured_data = agent_result.get("structured_data", {})
                if isinstance(structured_data, dict):
                    ter = structured_data.get("task_execution_report", {})
                    if isinstance(ter, dict):
                        # 提取 additional_insights
                        insights = ter.get("additional_insights", [])
                        if isinstance(insights, list):
                            for insight in insights[:2]:
                                if isinstance(insight, str) and insight and len(insight) > 10:
                                    findings.append(insight[:150])
                        # 提取 task_completion_summary
                        summary = ter.get("task_completion_summary", "")
                        if isinstance(summary, str) and summary and len(summary) > 20:
                            findings.append(summary[:150])

                # 从 analysis 字段提取
                analysis = agent_result.get("analysis", "")
                if isinstance(analysis, str) and analysis and len(analysis) > 50:
                    # 提取第一句话作为发现
                    first_sentence = analysis.split("。")[0]
                    if first_sentence and len(first_sentence) > 10:
                        findings.append(first_sentence[:150])

                if len(findings) >= 5:
                    break

            return findings[:5] if findings else ["基于多智能体分析的综合发现"]

        # 🆕 v7.154: 从专家报告中提取建议
        def extract_key_recommendations() -> List[str]:
            """从专家报告中提取关键建议"""
            recommendations = []
            for role_id in active_agents:
                if not any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_", "V7_"]):
                    continue
                agent_result = agent_results.get(role_id, {})
                if not isinstance(agent_result, dict):
                    continue

                structured_data = agent_result.get("structured_data", {})
                if isinstance(structured_data, dict):
                    ter = structured_data.get("task_execution_report", {})
                    if isinstance(ter, dict):
                        # 提取 execution_challenges 作为建议
                        challenges = ter.get("execution_challenges", [])
                        if isinstance(challenges, list):
                            for challenge in challenges[:2]:
                                if isinstance(challenge, str) and challenge:
                                    recommendations.append(f"注意: {challenge[:100]}")
                                elif isinstance(challenge, dict):
                                    desc = challenge.get("description", challenge.get("challenge", ""))
                                    if desc:
                                        recommendations.append(f"注意: {desc[:100]}")

                if len(recommendations) >= 5:
                    break

            return recommendations[:5] if recommendations else ["基于分析结果的核心建议"]

        # 🆕 v7.154: 提取跨领域洞察
        def extract_cross_domain_insights() -> List[str]:
            """提取跨领域洞察"""
            insights = []
            expert_summaries = []

            for role_id in active_agents:
                if not any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_", "V7_"]):
                    continue
                agent_result = agent_results.get(role_id, {})
                if not isinstance(agent_result, dict):
                    continue

                role_name = agent_result.get("role_name", role_id)
                analysis = agent_result.get("analysis", "")
                if analysis and len(analysis) > 50:
                    expert_summaries.append(f"{role_name}: {analysis[:100]}")

            if expert_summaries:
                insights.append(f"综合{len(expert_summaries)}位专家的分析视角")
                for summary in expert_summaries[:3]:
                    insights.append(summary)

            return insights if insights else ["跨领域的关键洞察"]

        # 🆕 对所有可能包含 JTBD 公式的字段进行转换
        transformed_requirements = structured_requirements.copy()

        # 转换 project_overview（最重要）
        if "project_overview" in transformed_requirements:
            transformed_requirements["project_overview"] = transform_jtbd_to_natural_language(
                transformed_requirements["project_overview"]
            )

        # 转换 project_task（JTBD 公式来源）
        if "project_task" in transformed_requirements:
            transformed_requirements["project_task"] = transform_jtbd_to_natural_language(
                transformed_requirements["project_task"]
            )

        # 转换 core_objectives（可能包含 JTBD 公式）
        if "core_objectives" in transformed_requirements and isinstance(
            transformed_requirements["core_objectives"], list
        ):
            transformed_requirements["core_objectives"] = [
                transform_jtbd_to_natural_language(obj) if isinstance(obj, str) else obj
                for obj in transformed_requirements["core_objectives"]
            ]

        # 🔥 v7.26.2: 提取用户核心问题和交付物
        user_input = state.get("user_input", "")
        user_question = user_input[:100] + "..." if len(user_input) > 100 else user_input

        # 从专家结果中提取交付物名称
        deliverable_names = []
        for role_id in active_agents:
            if any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_", "V7_"]):
                agent_result = agent_results.get(role_id, {})
                if isinstance(agent_result, dict):
                    structured = agent_result.get("structured_data", {})
                    if isinstance(structured, dict):
                        ter = structured.get("task_execution_report", {})
                        if isinstance(ter, dict):
                            outputs = ter.get("deliverable_outputs", [])
                            for output in outputs:
                                if isinstance(output, dict):
                                    name = output.get("deliverable_name", output.get("name", ""))
                                    if name and name not in deliverable_names:
                                        deliverable_names.append(name)

        if not deliverable_names:
            deliverable_names = ["综合分析报告", "专家建议汇总"]

        # 🆕 v7.154: 提取实际内容而非占位符
        key_findings = extract_key_findings()
        key_recommendations = extract_key_recommendations()
        cross_domain_insights = extract_cross_domain_insights()

        # 🆕 v7.154: 从 strategic_analysis 提取推敲过程
        query_type = "深度优先探询"
        query_type_reasoning = ""
        role_selection = []
        if isinstance(strategic_analysis, dict):
            query_type = strategic_analysis.get("query_type", "深度优先探询")
            query_type_reasoning = strategic_analysis.get("query_type_reasoning", "")
            selected_roles = strategic_analysis.get("selected_roles", [])
            for role in selected_roles[:5]:
                if isinstance(role, dict):
                    role_name = role.get("dynamic_role_name", role.get("role_id", ""))
                    reason = role.get("selection_reason", "")
                    if role_name:
                        role_selection.append(f"{role_name}: {reason[:50]}" if reason else role_name)

        return {
            "executive_summary": {
                "project_overview": transform_jtbd_to_natural_language(
                    structured_requirements.get("project_overview", "")
                ),
                "key_findings": key_findings,
                "key_recommendations": key_recommendations,
                "success_factors": [
                    f"专家团队协作: {len(active_agents)}位专家参与分析",
                    "多维度视角: 涵盖设计、研究、叙事等多个领域",
                    "结构化输出: 提供可执行的交付物清单",
                ],
            },
            # 🔥 v7.26.2: 添加 core_answer 字段（fallback 路径必须）
            "core_answer": {
                "question": user_question or "用户咨询问题",
                "answer": structured_requirements.get("project_overview", "请查看各专家的详细分析报告"),
                "deliverables": deliverable_names[:5],
                "timeline": "请参考工程师专家的实施规划",
                "budget_range": "请参考工程师专家的成本估算",
            },
            # 🔥 v7.26.2: 添加 insights 字段（fallback 路径必须）
            "insights": {
                "key_insights": key_findings[:3]
                if key_findings
                else [structured_requirements.get("project_overview", "基于用户需求的综合分析")],
                "cross_domain_connections": cross_domain_insights[:3],
                "user_needs_interpretation": structured_requirements.get("project_task", "用户需求的深度解读"),
            },
            # 🔥 v7.154: 增强 deliberation_process 字段
            "deliberation_process": {
                "inquiry_architecture": query_type,
                "reasoning": query_type_reasoning[:200] if query_type_reasoning else "基于用户需求进行多维度分析",
                "role_selection": role_selection if role_selection else [f"选择了 {len(active_agents)} 位专家进行协同分析"],
                "strategic_approach": f"采用{query_type}策略，综合{len(active_agents)}位专家的专业视角进行深度分析",
            },
            "sections": {
                ReportSection.REQUIREMENTS_ANALYSIS.value: {
                    "title": "需求分析",
                    "content": transformed_requirements,
                    "confidence": 0.8,
                },
                ReportSection.DESIGN_RESEARCH.value: {
                    "title": "设计研究",
                    "content": extract_content_by_role_prefix("V4_"),  # V4是设计研究
                    "confidence": extract_confidence_by_role_prefix("V4_"),
                },
                ReportSection.TECHNICAL_ARCHITECTURE.value: {
                    "title": "技术架构",
                    "content": extract_content_by_role_prefix("V2_"),  # V2是设计总监/技术
                    "confidence": extract_confidence_by_role_prefix("V2_"),
                },
                ReportSection.UX_DESIGN.value: {
                    "title": "用户体验设计",
                    "content": extract_content_by_role_prefix("V3_"),  # V3是叙事/体验
                    "confidence": extract_confidence_by_role_prefix("V3_"),
                },
                ReportSection.BUSINESS_MODEL.value: {
                    "title": "商业模式",
                    "content": extract_content_by_role_prefix("V5_"),  # V5是场景专家
                    "confidence": extract_confidence_by_role_prefix("V5_"),
                },
                ReportSection.IMPLEMENTATION_PLAN.value: {
                    "title": "实施规划",
                    "content": extract_content_by_role_prefix("V6_"),  # V6是工程师
                    "confidence": extract_confidence_by_role_prefix("V6_"),
                },
            },
            "comprehensive_analysis": {
                "cross_domain_insights": cross_domain_insights,
                "integrated_recommendations": key_recommendations,
                "risk_assessment": [challenge for challenge in key_recommendations if "注意" in challenge]
                or ["请参考各专家报告中的风险提示"],
                "implementation_roadmap": [f"交付物: {name}" for name in deliverable_names[:5]],
            },
            "conclusions": {
                "project_analysis_summary": structured_requirements.get("project_overview", "项目分析总结"),
                "next_steps": key_recommendations[:3] if key_recommendations else ["下一步行动建议"],
                "success_metrics": [
                    f"完成{len(deliverable_names)}项核心交付物",
                    f"获得{len(active_agents)}位专家的专业分析",
                    "形成可执行的实施方案",
                ],
            },
            "raw_content": content,
        }

    def _has_placeholder_content(self, expert_reports: Dict[str, str]) -> bool:
        """
        检测 expert_reports 内容是否为占位符

        LLM 有时会返回类似 "{...内容略，详见原始输入...}" 的占位符文本
        这种情况需要用真实数据覆盖

        Returns:
            True 如果包含占位符内容，False 如果内容有效
        """
        if not expert_reports:
            return True

        placeholders = ["...内容略", "内容略，详见", "详见原始输入", "...(truncated)", "暂无报告内容", "(omitted)", "省略", "略..."]

        for role_id, content in expert_reports.items():
            if isinstance(content, str):
                for placeholder in placeholders:
                    if placeholder in content:
                        logger.debug(f"Detected placeholder in {role_id}: '{placeholder}'")
                        return True

        return False

    def _extract_expert_reports(self, state: ProjectAnalysisState) -> Dict[str, str]:
        """
        提取专家原始报告用于附录

        返回格式：
        {
            "V2_设计总监_2-1": "完整的原始报告内容...",
            "V3_人物及叙事专家_3-1": "完整的原始报告内容...",
            ...
        }

        ✅ 修复: 支持 Dynamic Mode，使用动态角色 ID（如 "V2_设计总监_2-1"）
        ✅ 优化: 使用 dynamic_role_name 作为显示名称（如 "V5_商业零售运营专家_5-2"）
        """
        agent_results = state.get("agent_results", {})
        active_agents = state.get("active_agents", [])
        strategic_analysis = state.get("strategic_analysis", {})
        selected_roles = strategic_analysis.get("selected_roles", []) if isinstance(strategic_analysis, dict) else []
        expert_reports = {}

        # 🔧 构建 role_id -> dynamic_role_name 的映射
        role_display_names = {}
        for role in selected_roles:
            if isinstance(role, dict):
                rid = role.get("role_id", "")
                dynamic_name = role.get("dynamic_role_name", "")
                if rid and dynamic_name:
                    role_display_names[rid] = dynamic_name

        logger.debug(f"🔍 Extracting expert reports from {len(active_agents)} active agents")
        logger.debug(f"📋 Role display names mapping: {role_display_names}")

        for role_id in active_agents:
            # 跳过需求分析师和项目总监（不需要在附录中）
            if role_id in ["requirements_analyst", "project_director"]:
                continue

            # 只提取 V2-V6 专家的报告
            if not any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_"]):
                continue

            agent_result = agent_results.get(role_id, {})
            if agent_result:
                # 提取完整的内容
                content = agent_result.get("content", "")
                structured_data = agent_result.get("structured_data", {})

                # 🔥 v7.9.2: 智能提取实际内容,与前端逻辑一致
                # 检测 TaskOrientedExpertOutput 结构,提取 deliverable_outputs
                if structured_data and isinstance(structured_data, dict):
                    # 检查是否有 task_execution_report 嵌套结构
                    ter = structured_data.get("task_execution_report")
                    if ter and isinstance(ter, dict):
                        deliverable_outputs = ter.get("deliverable_outputs")
                        if deliverable_outputs and isinstance(deliverable_outputs, list):
                            # 只提取交付物内容,忽略元数据
                            extracted_content = {"deliverable_outputs": deliverable_outputs}
                            # 可选: 添加额外信息(但不包括元数据)
                            if ter.get("task_completion_summary"):
                                extracted_content["task_completion_summary"] = ter["task_completion_summary"]
                            if ter.get("additional_insights"):
                                extracted_content["additional_insights"] = ter["additional_insights"]
                            if ter.get("execution_challenges"):
                                extracted_content["execution_challenges"] = ter["execution_challenges"]

                            report_content = json.dumps(extracted_content, ensure_ascii=False, indent=2)
                        else:
                            # 没有 deliverable_outputs,使用整个 structured_data
                            report_content = json.dumps(structured_data, ensure_ascii=False, indent=2)
                    else:
                        # 没有 task_execution_report,使用整个 structured_data
                        report_content = json.dumps(structured_data, ensure_ascii=False, indent=2)
                elif content:
                    report_content = content
                else:
                    report_content = "暂无报告内容"

                # 🔧 使用 dynamic_role_name 构建显示名称
                # 格式: "4-1 潮玩风格案例研究员"
                display_name = role_id

                # 🔥 v7.25: 从完整格式 role_id 提取短格式后缀用于查找
                # role_id 格式: "V2_设计总监_2-1" -> 短格式: "2-1"
                # role_display_names 的 key 是短格式 "2-1"
                import re

                suffix_match = re.search(r"(\d+-\d+)$", role_id)
                short_role_id = suffix_match.group(1) if suffix_match else role_id

                # 尝试用短格式查找 dynamic_role_name
                if short_role_id in role_display_names:
                    dynamic_name = role_display_names[short_role_id]
                    display_name = f"{short_role_id} {dynamic_name}"
                    logger.debug(f"🎯 [v7.25] 使用动态名称: {role_id} → {display_name}")
                elif role_id in role_display_names:
                    # 兼容：也支持完整格式作为 key
                    dynamic_name = role_display_names[role_id]
                    if suffix_match:
                        display_name = f"{short_role_id} {dynamic_name}"
                    else:
                        display_name = dynamic_name

                expert_reports[display_name] = report_content
                logger.debug(f"✅ Extracted expert report: {display_name} ({len(report_content)} chars)")

        logger.info(f"📊 Extracted {len(expert_reports)} expert reports: {list(expert_reports.keys())}")
        return expert_reports

    def _manually_populate_sections(self, state: ProjectAnalysisState) -> List[Dict[str, Any]]:
        """
        手动从 agent_results 中提取并填充 sections

        这是一个兜底方案，当 LLM 返回空 sections 时使用

        ✅ 修复: 支持 Dynamic Mode，使用动态角色 ID（如 "V2_设计总监_2-1"）
        ✅ 修复: 返回List而不是Dict,以匹配新的数据结构
        """
        agent_results = state.get("agent_results", {})
        active_agents = state.get("active_agents", [])
        sections = []  # 改为列表
        sections_dict: Dict[str, Dict[str, Any]] = {}

        section_order = [
            "requirements_analysis",
            "design_research",
            "technical_architecture",
            "ux_design",
            "business_model",
            "implementation_plan",
        ]

        logger.debug(f"🔍 agent_results keys: {list(agent_results.keys())}")
        logger.debug(f"🔍 active_agents: {active_agents}")

        # 章节类型到标题的映射
        section_titles = {
            "requirements_analysis": "需求分析",
            "design_research": "设计研究",
            "technical_architecture": "技术架构",
            "ux_design": "用户体验设计",
            "business_model": "商业模式",
            "implementation_plan": "实施规划",
        }

        # 1. 处理需求分析师（固定键名）
        requirements_result = agent_results.get("requirements_analyst", {})
        if requirements_result and requirements_result.get("structured_data"):
            # 将structured_data转换为字符串格式
            structured_data = requirements_result.get("structured_data", {})
            content_str = json.dumps(structured_data, ensure_ascii=False, indent=2)

            sections_dict["requirements_analysis"] = {
                "section_id": "requirements_analysis",  # 添加section_id
                "title": section_titles["requirements_analysis"],
                "content": content_str,  # 使用字符串格式
                "confidence": requirements_result.get("confidence", 0.5),
            }
            logger.debug(f"✅ Manually populated section: requirements_analysis from requirements_analyst")

        # 2. 处理 V2-V6 专家（Dynamic Mode 使用动态角色 ID）
        # 根据角色 ID 前缀映射到章节类型
        role_prefix_to_section = {
            "V2_": "technical_architecture",
            "V3_": "ux_design",
            "V4_": "design_research",
            "V5_": "business_model",
            "V6_": "implementation_plan",
        }

        for role_id in active_agents:
            # 跳过需求分析师（已处理）
            if role_id == "requirements_analyst":
                continue

            # 根据前缀确定章节类型
            section_key = None
            for prefix, section_type in role_prefix_to_section.items():
                if role_id.startswith(prefix):
                    section_key = section_type
                    break

            if not section_key:
                logger.warning(f"⚠️ Unknown role prefix for {role_id}, skipping")
                continue

            # 从 agent_results 中获取数据
            agent_result = agent_results.get(role_id, {})
            section_entry = sections_dict.get(section_key)
            if section_entry is None:
                section_entry = {
                    "section_id": section_key,
                    "title": section_titles[section_key],
                    "content": "",
                    "confidence": 0.0,
                }
                sections_dict[section_key] = section_entry

            if agent_result and agent_result.get("structured_data"):
                structured_data = agent_result.get("structured_data", {})
                content_str = json.dumps(structured_data, ensure_ascii=False, indent=2)

                if not section_entry["content"] or section_entry["content"].startswith("暂无"):
                    section_entry["content"] = content_str
                    confidence_value = agent_result.get("confidence", 0.5)
                    try:
                        section_entry["confidence"] = float(confidence_value)
                    except (TypeError, ValueError):
                        section_entry["confidence"] = 0.5
                else:
                    logger.debug(
                        "ℹ️ Section {} already populated, skipping additional content from {}",
                        section_key,
                        role_id,
                    )
                logger.debug(f"✅ Manually populated section: {section_key} from {role_id}")
            else:
                if not section_entry["content"]:
                    section_entry["content"] = f"暂无{section_titles[section_key]}数据"
                    section_entry["confidence"] = 0.0
                logger.warning(f"⚠️ No data found for {role_id}, created empty section for {section_key}")

        for section_id in section_order:
            if section_id in sections_dict:
                sections.append(sections_dict[section_id])

        for section_id, payload in sections_dict.items():
            if section_id not in section_order:
                sections.append(payload)

        logger.info(
            "📊 Manually populated %d sections: %s",
            len(sections),
            [section["section_id"] for section in sections],
        )
        return sections

    def _extract_challenge_resolutions(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        🆕 v3.5.1: 提取挑战解决结果

        从state中提取专家挑战的闭环处理结果，用于报告生成

        Returns:
            {
                "accepted_reinterpretations": [...],  # Accept决策的结果
                "synthesized_frameworks": [...],      # Synthesize决策的结果
                "escalated_to_client": [...],         # Escalate决策的结果
                "summary": {...}                      # 统计摘要
            }
        """
        # 提取各类闭环结果
        expert_driven_insights = state.get("expert_driven_insights", {})
        framework_synthesis = state.get("framework_synthesis", {})
        escalated_challenges = state.get("escalated_challenges", [])

        # 统计
        accepted_count = len(expert_driven_insights)
        synthesized_count = len(framework_synthesis)
        escalated_count = len(escalated_challenges)

        # 如果没有任何挑战解决，返回空结构
        if accepted_count == 0 and synthesized_count == 0 and escalated_count == 0:
            return {"has_challenges": False, "summary": "所有专家接受需求分析师的洞察，无挑战标记"}

        # 格式化Accept决策结果
        accepted_reinterpretations = []
        for item, insight in expert_driven_insights.items():
            accepted_reinterpretations.append(
                {
                    "challenged_item": item,
                    "expert": insight.get("accepted_from", "unknown"),
                    "reinterpretation": insight.get("expert_reinterpretation", ""),
                    "design_impact": insight.get("design_impact", ""),
                    "timestamp": insight.get("timestamp", ""),
                }
            )

        # 格式化Synthesize决策结果
        synthesized_frameworks = []
        for item, synthesis in framework_synthesis.items():
            synthesized_frameworks.append(
                {
                    "challenged_item": item,
                    "competing_count": len(synthesis.get("competing_frames", [])),
                    "synthesis_summary": synthesis.get("synthesis_summary", ""),
                    "recommendation": synthesis.get("recommendation", ""),
                }
            )

        # 格式化Escalate决策结果
        escalated_items = []
        for challenge in escalated_challenges:
            escalated_items.append(
                {
                    "issue_id": challenge.get("issue_id", ""),
                    "description": challenge.get("description", ""),
                    "expert_rationale": challenge.get("expert_rationale", ""),
                    "requires_client_decision": challenge.get("requires_client_decision", True),
                }
            )

        return {
            "has_challenges": True,
            "accepted_reinterpretations": accepted_reinterpretations,
            "synthesized_frameworks": synthesized_frameworks,
            "escalated_to_client": escalated_items,
            "summary": {
                "total_challenges": accepted_count + synthesized_count + escalated_count,
                "accepted_count": accepted_count,
                "synthesized_count": synthesized_count,
                "escalated_count": escalated_count,
                "closure_rate": f"{(accepted_count + synthesized_count) / max(1, accepted_count + synthesized_count + escalated_count) * 100:.1f}%",
            },
        }

    def _calculate_overall_confidence(self, state: ProjectAnalysisState) -> float:
        """计算整体置信度"""
        agent_results = state.get("agent_results", {})

        if not agent_results:
            return 0.0

        confidences = [
            result.get("confidence", 0)
            for result in agent_results.values()
            if result and isinstance(result.get("confidence"), (int, float))
        ]

        if not confidences:
            return 0.0

        # 计算加权平均置信度
        return sum(confidences) / len(confidences)

    def _get_expert_distribution(self, agent_results: Dict[str, Any]) -> Dict[str, int]:
        """
        获取专家分布统计

        🔧 v7.154: 修复模式匹配逻辑，支持完整格式 role_id

        Args:
            agent_results: 专家执行结果

        Returns:
            按专家层级（V2-V7）分类的数量统计
        """
        distribution = {
            "V2_设计总监": 0,
            "V3_领域专家": 0,
            "V4_研究专家": 0,
            "V5_创新专家": 0,
            "V6_实施专家": 0,
            "V7_情感专家": 0,  # 🆕 v7.154: 添加 V7 支持
        }

        for role_id in agent_results.keys():
            if isinstance(role_id, str):
                # 🔧 v7.154: 支持多种格式
                # 格式1: "2-1" (短格式)
                # 格式2: "V2_设计总监_2-1" (完整格式)

                if role_id.startswith("V2_") or "2-" in role_id:
                    distribution["V2_设计总监"] += 1
                elif role_id.startswith("V3_") or "3-" in role_id:
                    distribution["V3_领域专家"] += 1
                elif role_id.startswith("V4_") or "4-" in role_id:
                    distribution["V4_研究专家"] += 1
                elif role_id.startswith("V5_") or "5-" in role_id:
                    distribution["V5_创新专家"] += 1
                elif role_id.startswith("V6_") or "6-" in role_id:
                    distribution["V6_实施专家"] += 1
                elif role_id.startswith("V7_") or "7-" in role_id:
                    distribution["V7_情感专家"] += 1

        # 只返回有值的分布
        return {k: v for k, v in distribution.items() if v > 0}

    def _estimate_report_pages(self, report: Dict[str, Any]) -> int:
        """估算报告页数"""
        # 基于内容量估算页数
        total_content = 0

        # 计算各部分内容量
        # sections 现在是 List[ReportSectionWithId]，不是字典
        sections = report.get("sections", [])
        for section in sections:
            content = section.get("content", "") if isinstance(section, dict) else ""
            total_content += len(str(content))

        # 添加其他部分
        total_content += len(str(report.get("executive_summary", {})))
        total_content += len(str(report.get("comprehensive_analysis", {})))
        total_content += len(str(report.get("conclusions", {})))

        # 估算页数（假设每页约2000字符）
        estimated_pages = max(10, total_content // 2000)

        return min(estimated_pages, 50)  # 限制在10-50页之间

    def _extract_review_feedback(
        self,
        review_result: Dict[str, Any],
        review_history: List[Dict[str, Any]],
        improvement_suggestions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        提取审核反馈数据

        Args:
            review_result: 当前审核结果
            review_history: 审核历史记录
            improvement_suggestions: 改进建议列表

        Returns:
            格式化的审核反馈数据
        """
        from datetime import datetime

        red_team_challenges = []
        blue_team_validations = []
        judge_rulings = []
        client_decisions = []

        # 从审核历史中提取数据（支持多轮审核）
        for round_data in review_history:
            round_num = round_data.get("round", 1)

            # 提取红队质疑点
            red_review = round_data.get("red_team_review", {})
            if isinstance(red_review, dict):
                improvements = red_review.get("improvements", [])
                for imp in improvements:
                    red_team_challenges.append(
                        {
                            "issue_id": imp.get("issue_id", f"R{round_num}-{len(red_team_challenges)+1}"),
                            "reviewer": f"红队（第{round_num}轮）",
                            "issue_type": "风险",
                            "description": imp.get("issue", ""),
                            "response": imp.get("suggested_action", "待处理"),
                            "status": "已修复"
                            if imp.get("issue_id") in [s.get("issue_id") for s in improvement_suggestions]
                            else "待处理",
                            "priority": imp.get("priority", "medium"),
                        }
                    )

            # 提取蓝队验证结果
            blue_review = round_data.get("blue_team_review", {})
            if isinstance(blue_review, dict):
                # ✅ 蓝队有两种数据：keep_as_is（优势）和 enhancements（优化建议）
                keep_as_is = blue_review.get("keep_as_is", [])
                for item in keep_as_is:
                    blue_team_validations.append(
                        {
                            "issue_id": item.get("red_issue_id", f"B{round_num}-{len(blue_team_validations)+1}"),
                            "reviewer": f"蓝队（第{round_num}轮）",
                            "issue_type": "验证",
                            "description": item.get("defense", ""),
                            "response": item.get("evidence", "已验证"),
                            "status": "已验证",
                            "priority": "medium",
                        }
                    )

                enhancements = blue_review.get("enhancements", [])
                for enh in enhancements:
                    blue_team_validations.append(
                        {
                            "issue_id": enh.get("enhancement_id", f"B{round_num}-{len(blue_team_validations)+1}"),
                            "reviewer": f"蓝队（第{round_num}轮）",
                            "issue_type": "优化",
                            "description": enh.get("enhancement", ""),
                            "response": enh.get("value_add", "已采纳"),
                            "status": "已采纳",
                            "priority": enh.get("priority", "medium"),
                        }
                    )

            # 提取评委裁决
            judge_review = round_data.get("judge_review", {})
            if isinstance(judge_review, dict):
                prioritized = judge_review.get("prioritized_improvements", [])
                for item in prioritized:
                    # ✅ 正确的字段映射：task -> description, rationale -> response
                    judge_rulings.append(
                        {
                            "issue_id": item.get("issue_id", f"J{round_num}-{len(judge_rulings)+1}"),
                            "reviewer": f"评委（第{round_num}轮）",
                            "issue_type": "建议",
                            "description": item.get("task", ""),  # ✅ 从 task 字段提取
                            "response": item.get("rationale", ""),  # ✅ 从 rationale 字段提取
                            "status": "已修复" if item.get("priority", 999) <= 2 else "待定",  # ✅ priority 是数字
                            "priority": "high" if item.get("priority", 999) <= 2 else "medium",
                        }
                    )

            # 提取甲方决策
            client_review = round_data.get("client_review", {})
            if isinstance(client_review, dict):
                accepted = client_review.get("accepted_improvements", [])
                for acc in accepted:
                    client_decisions.append(
                        {
                            "issue_id": acc.get("issue_id", f"C{round_num}-{len(client_decisions)+1}"),
                            "reviewer": f"甲方（第{round_num}轮）",
                            "issue_type": "决策",
                            "description": acc.get("issue", ""),
                            "response": acc.get("implementation_plan", ""),
                            "status": "已采纳",
                            "priority": acc.get("priority", "high"),
                        }
                    )

        # 生成迭代总结
        total_issues = len(red_team_challenges)
        resolved_issues = len([x for x in red_team_challenges if x["status"] == "已修复"])
        iteration_summary = f"""
## 审核迭代过程总结

**总审核轮次**: {len(review_history)}轮
**红队发现问题数**: {total_issues}个
**蓝队验证优化点**: {len(blue_team_validations)}个
**评委裁决项目**: {len(judge_rulings)}个
**甲方最终决策**: {len(client_decisions)}个
**问题解决率**: {resolved_issues}/{total_issues} ({resolved_issues/max(1, total_issues)*100:.1f}%)

### 改进效果
通过多轮审核，项目质量显著提升：
- 风险识别与应对：红队发现的{total_issues}个潜在风险中，{resolved_issues}个已完成修复
- 价值增强：蓝队提出的{len(blue_team_validations)}个优化建议已全部采纳
- 专业裁决：评委团队提供{len(judge_rulings)}个专业建议，确保技术方案可行性
- 最终决策：甲方审核通过{len(client_decisions)}个关键改进措施

### 关键改进亮点
{self._format_key_improvements(improvement_suggestions[:3])}
"""

        return {
            "red_team_challenges": red_team_challenges,
            "blue_team_validations": blue_team_validations,
            "judge_rulings": judge_rulings,
            "client_decisions": client_decisions,
            "iteration_summary": iteration_summary.strip(),
        }

    def _extract_questionnaire_data(
        self,
        calibration_questionnaire: Dict[str, Any],
        questionnaire_responses: Dict[str, Any],
        questionnaire_summary: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        提取问卷回答数据

        Args:
            calibration_questionnaire: 校准问卷
            questionnaire_responses: 用户回答

        Returns:
            格式化的问卷数据，如果所有问题都未回答则返回 None

        🔧 修复: 过滤掉未回答的问题，避免前端显示"未回答"
        🔧 v7.5 修复: 增加对 entries 中 answer 字段的支持（前端提交格式）
        """
        from datetime import datetime

        summary_entries = []
        if questionnaire_summary and questionnaire_summary.get("entries"):
            summary_entries = questionnaire_summary.get("entries", [])
        elif questionnaire_responses.get("entries"):
            summary_entries = questionnaire_responses.get("entries", [])

        responses = []

        if summary_entries:
            logger.debug(f"🔍 [问卷提取] 从 entries 提取，共 {len(summary_entries)} 项")
            for idx, entry in enumerate(summary_entries, 1):
                # 🔧 v7.5 修复: 同时检查 value 和 answer 字段（前端提交格式兼容）
                answer_value = entry.get("value") or entry.get("answer")
                # 🔧 修复: 跳过未回答的问题
                if answer_value is None or answer_value == "" or answer_value == []:
                    continue

                answer_str = self._stringify_answer(answer_value)
                # 🔧 修复: 再次检查格式化后的答案
                if answer_str == "未回答" or answer_str == "":
                    continue

                responses.append(
                    {
                        "question_id": entry.get("id") or entry.get("question_id", f"Q{idx}"),
                        "question": entry.get("question", ""),
                        "answer": answer_str,
                        "context": entry.get("context", ""),
                    }
                )
        else:
            questions = calibration_questionnaire.get("questions", [])
            answers = questionnaire_responses.get("answers", {})
            logger.debug(f"🔍 [问卷提取] 从 questions/answers 提取，{len(questions)} 问题，{len(answers)} 答案")

            for idx, q in enumerate(questions, 1):
                question_id = q.get("id", f"Q{idx}")
                raw_answer = answers.get(question_id) or answers.get(f"q{idx}")

                # 🔧 修复: 跳过未回答的问题
                if raw_answer is None or raw_answer == "" or raw_answer == []:
                    continue

                answer_str = self._stringify_answer(raw_answer)
                # 🔧 修复: 再次检查格式化后的答案
                if answer_str == "未回答" or answer_str == "":
                    continue

                responses.append(
                    {
                        "question_id": question_id,
                        "question": q.get("question", ""),
                        "answer": answer_str,
                        "context": q.get("context", ""),
                    }
                )

        # 🔧 修复: 如果所有问题都未回答，返回 None（前端会隐藏整个问卷区块）
        if not responses:
            logger.info("📋 所有问卷问题都未回答，返回 None（前端将隐藏问卷区块）")
            return None

        timestamp = (
            (questionnaire_summary or {}).get("submitted_at")
            or questionnaire_responses.get("submitted_at")
            or questionnaire_responses.get("timestamp")
            or datetime.now().isoformat()
        )

        notes = (questionnaire_summary or {}).get("notes") or questionnaire_responses.get("notes", "")

        # 生成洞察分析
        analysis_insights = self._analyze_questionnaire_insights(responses)

        logger.info(f"✅ 提取到 {len(responses)} 个有效问卷回答")

        return {"responses": responses, "timestamp": timestamp, "notes": notes, "analysis_insights": analysis_insights}

    @staticmethod
    def _stringify_answer(value: Any) -> str:
        """将问卷答案格式化为易读字符串"""
        if value is None:
            return "未回答"

        if isinstance(value, (list, tuple, set)):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            return "、".join(cleaned) if cleaned else "未回答"

        if isinstance(value, dict):
            try:
                serialized = json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError):
                serialized = str(value)
            return serialized.strip() or "未回答"

        text = str(value).strip()
        return text or "未回答"

    def _extract_visualization_data(
        self, review_history: List[Dict[str, Any]], review_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        提取可视化数据

        Args:
            review_history: 审核历史记录
            review_result: 最终审核结果

        Returns:
            格式化的可视化数据
        """
        from datetime import datetime

        rounds = []
        for round_data in review_history:
            round_num = round_data.get("round", 1)

            # 提取各方评分
            red_review = round_data.get("red_team_review", {})
            blue_review = round_data.get("blue_team_review", {})
            judge_review = round_data.get("judge_review", {})

            red_score = red_review.get("score", 0) if isinstance(red_review, dict) else 0
            blue_score = blue_review.get("score", 0) if isinstance(blue_review, dict) else 0
            judge_score = judge_review.get("score", 0) if isinstance(judge_review, dict) else 0

            issues_found = len(red_review.get("improvements", [])) if isinstance(red_review, dict) else 0
            issues_resolved = len(blue_review.get("enhancements", [])) if isinstance(blue_review, dict) else 0

            rounds.append(
                {
                    "round_number": round_num,
                    "red_score": red_score,
                    "blue_score": blue_score,
                    "judge_score": judge_score,
                    "issues_found": issues_found,
                    "issues_resolved": issues_resolved,
                    "timestamp": round_data.get("timestamp", datetime.now().isoformat()),
                }
            )

        # 计算改进率
        if rounds:
            first_round_score = rounds[0]["red_score"]
            last_round_score = rounds[-1]["judge_score"]
            improvement_rate = (last_round_score - first_round_score) / max(1, first_round_score)
        else:
            improvement_rate = 0.0

        # 获取最终决策
        client_review = review_result.get("client_review", {})
        final_decision = "通过"
        if isinstance(client_review, dict):
            decision = client_review.get("final_decision", "approved")
            if decision == "approved":
                final_decision = "通过"
            elif decision == "conditional_approval":
                final_decision = "有条件通过"
            else:
                final_decision = "拒绝"

        return {
            "rounds": rounds,
            "final_decision": final_decision,
            "total_rounds": len(rounds),
            "improvement_rate": round(improvement_rate, 2),
        }

    def _format_key_improvements(self, improvements: List[Dict[str, Any]]) -> str:
        """格式化关键改进点"""
        if not improvements:
            return "无需改进，分析质量已达标。"

        formatted = []
        for idx, imp in enumerate(improvements, 1):
            formatted.append(
                f"{idx}. **{imp.get('issue_id', 'N/A')}**: {imp.get('issue', '未知问题')} "
                f"（优先级: {imp.get('priority', 'medium')}）"
            )

        return "\n".join(formatted)

    def _analyze_questionnaire_insights(self, responses: List[Dict[str, Any]]) -> str:
        """从问卷回答中提取关键洞察"""
        if not responses:
            return "无有效问卷数据。"

        insights = ["## 用户需求关键洞察", "", f"基于{len(responses)}个问题的深入访谈，我们提取了以下关键洞察：", ""]

        # 简单分析：提取非空回答的数量
        answered = [r for r in responses if r.get("answer") and r["answer"] != "未回答"]
        insights.append(f"- **回答完整度**: {len(answered)}/{len(responses)} ({len(answered)/len(responses)*100:.1f}%)")

        # 如果有回答，提取前3个关键回答
        if answered:
            insights.append("- **关键回答**:")
            for r in answered[:3]:
                insights.append(f"  - {r.get('question', '未知问题')[:50]}...")
                insights.append(f"    > {r.get('answer', '未知回答')[:100]}...")

        return "\n".join(insights)

    def _extract_generated_images_by_expert(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        🆕 v7.108: 从 agent_results[role_id]['concept_images'] 提取并转换为前端期望格式

        前端期望格式:
        {
            "2-1": {  # role_id作为key
                "expert_name": "V2 设计总监",
                "images": [
                    {
                        "id": "2-1_1_143022_abc",
                        "image_url": "/generated_images/session_id/...",  # 注意：后端用url，前端用image_url
                        "prompt": "...",
                        "aspect_ratio": "16:9",
                        ...
                    }
                ]
            }
        }
        """
        generated_images_by_expert = {}
        agent_results = state.get("agent_results", {})

        for role_id, result in agent_results.items():
            if not result:
                continue

            # 跳过需求分析师和项目总监（他们不生成概念图）
            if role_id in ["requirements_analyst", "project_director"]:
                continue

            # 从专家结果中提取concept_images
            concept_images = result.get("concept_images", [])
            if not concept_images:
                continue

            # 获取专家名称
            expert_name = result.get("expert_name", role_id)

            # 转换为前端格式：将 url 字段映射为 image_url
            converted_images = []
            for img_data in concept_images:
                converted_img = dict(img_data)  # 复制原数据

                # 字段映射：url -> image_url (前端期望)
                if "url" in converted_img:
                    converted_img["image_url"] = converted_img.pop("url")

                # 确保id字段存在（使用deliverable_id作为备选）
                if "id" not in converted_img and "deliverable_id" in converted_img:
                    converted_img["id"] = converted_img["deliverable_id"]

                converted_images.append(converted_img)

            # 添加到结果字典
            generated_images_by_expert[role_id] = {"expert_name": expert_name, "images": converted_images}

        return generated_images_by_expert

    # =========================================================================
    # 🆕 v7.0: 多交付物核心答案提取方法
    # =========================================================================

    def _extract_deliverable_answers(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        🆕 v7.0: 从责任者输出中提取交付物答案

        核心逻辑：
        1. 从 deliverable_metadata 获取每个交付物的 owner
        2. 从 agent_results[owner] 中提取该专家的输出
        3. 直接使用专家输出作为答案，不做LLM二次综合

        Returns:
            {
                "deliverable_answers": [...],  # 各交付物的责任者答案
                "expert_support_chain": [...], # 专家支撑链
                "question": str,               # 用户核心问题
                "answer": str,                 # 综合摘要（向后兼容）
                "deliverables": [...],         # 交付物清单（向后兼容）
                "timeline": str,
                "budget_range": str
            }
        """
        deliverable_metadata = state.get("deliverable_metadata") or {}
        deliverable_owner_map = state.get("deliverable_owner_map") or {}
        agent_results = state.get("agent_results") or {}
        structured_requirements = state.get("structured_requirements") or {}
        user_input = state.get("user_input", "")

        logger.info(f"🎯 [v7.0] 开始提取交付物答案: {len(deliverable_metadata)} 个交付物")
        logger.debug(f"deliverable_owner_map: {deliverable_owner_map}")
        logger.debug(f"agent_results keys: {list(agent_results.keys())}")

        deliverable_answers = []
        expert_support_chain = []
        owners_set = set()  # 记录已作为owner的专家
        seen_names = {}  # 🆕 v7.154: 用于交付物名称去重

        # 🆕 v7.283: 数据验证 - 过滤异常ID（防止搜索结果混入）
        import re

        valid_deliverable_pattern = re.compile(r"^\d+-\d+_\d+_\d+_[a-z]{3}$")  # 正确格式：2-1_1_143022_abc
        invalid_count = 0

        for deliverable_id in list(deliverable_metadata.keys()):
            if not valid_deliverable_pattern.match(deliverable_id):
                logger.error(f"🚫 [v7.283] 检测到异常交付物ID格式: {deliverable_id}，已过滤")
                logger.error(f"   交付物名称: {deliverable_metadata[deliverable_id].get('name', 'N/A')}")
                logger.error(f"   正确格式应为: role_id_sequence_timestamp_hash (如 2-1_1_143022_abc)")
                deliverable_metadata.pop(deliverable_id)
                invalid_count += 1

        if invalid_count > 0:
            logger.warning(f"⚠️ [v7.283] 已过滤 {invalid_count} 个异常交付物ID（可能是搜索结果数据混入）")

        # 1. 提取每个交付物的责任者答案
        for deliverable_id, metadata in deliverable_metadata.items():
            owner_role = metadata.get("owner") or deliverable_owner_map.get(deliverable_id)

            if not owner_role:
                logger.warning(f"⚠️ 交付物 {deliverable_id} 无责任者，跳过")
                continue

            owners_set.add(owner_role)

            # 在 agent_results 中查找匹配的专家输出
            # owner_role 格式可能是 "V2_设计总监_室内策略方向" 这样的完整ID
            # agent_results 的 key 可能是 "V2_设计总监_2-1" 这样的格式
            owner_result = self._find_owner_result(agent_results, owner_role)

            if not owner_result:
                logger.warning(f"⚠️ 未找到责任者 {owner_role} 的输出")
                owner_answer = f"（{owner_role} 的输出待生成）"
                answer_summary = owner_answer
                quality_score = None
            else:
                owner_answer = self._extract_owner_deliverable_output(owner_result, deliverable_id)
                answer_summary = self._generate_answer_summary(owner_answer)
                quality_score = self._extract_quality_score(owner_result)

            # 🆕 v7.108: 提取概念图
            # 🔧 v7.154: 增强概念图关联逻辑
            concept_images = []
            if owner_result:
                concept_images_data = owner_result.get("concept_images", [])
                # 过滤出属于该交付物的概念图
                for img_data in concept_images_data:
                    img_deliverable_id = img_data.get("deliverable_id", "")
                    # 精确匹配
                    if img_deliverable_id == deliverable_id:
                        concept_images.append(img_data)
                    # 🆕 v7.154: 如果是主交付物（如 D1），关联该专家的所有概念图
                    elif deliverable_id.startswith("D") and deliverable_id[1:].isdigit():
                        # D1, D2 等主交付物，关联该专家的所有概念图
                        concept_images.append(img_data)
                        logger.debug(f"🖼️ [v7.154] 主交付物 {deliverable_id} 关联概念图: {img_deliverable_id}")

            # 🆕 v7.154: 交付物名称去重
            deliverable_name = metadata.get("name", deliverable_id)
            if deliverable_name in seen_names:
                # 名称重复，添加后缀区分
                seen_names[deliverable_name] += 1
                # 从 owner_role 中提取专家标识作为后缀
                import re

                suffix_match = re.search(r"(\d+-\d+)$", owner_role)
                if suffix_match:
                    deliverable_name = f"{deliverable_name} ({suffix_match.group(1)})"
                else:
                    deliverable_name = f"{deliverable_name} ({seen_names[deliverable_name]})"
                logger.debug(f"🔄 [v7.154] 交付物名称去重: {metadata.get('name')} -> {deliverable_name}")
            else:
                seen_names[deliverable_name] = 1

            deliverable_answer = {
                "deliverable_id": deliverable_id,
                "deliverable_name": deliverable_name,
                "deliverable_type": metadata.get("type", "unknown"),
                "owner_role": owner_role,
                "owner_answer": owner_answer,
                "answer_summary": answer_summary,
                "supporters": metadata.get("supporters", []),
                "quality_score": quality_score,
                "concept_images": concept_images,  # 🆕 v7.108: 关联概念图
            }

            deliverable_answers.append(deliverable_answer)
            logger.info(f"✅ 提取 {deliverable_id} 答案: owner={owner_role}, 长度={len(owner_answer)}")

        # 2. 构建专家支撑链（非owner专家的贡献）
        active_agents = state.get("active_agents", [])
        for role_id in agent_results.keys():
            # 跳过需求分析师、项目总监和已作为owner的专家
            if role_id in ["requirements_analyst", "project_director"]:
                continue
            if role_id in owners_set:
                continue
            if not any(role_id.startswith(prefix) for prefix in ["V2_", "V3_", "V4_", "V5_", "V6_"]):
                continue

            agent_result = agent_results.get(role_id, {})
            if not agent_result:
                continue

            # 提取贡献信息
            contribution = self._extract_supporter_contribution(role_id, agent_result, deliverable_metadata)
            if contribution:
                expert_support_chain.append(contribution)

        # 3. 按依赖顺序排序支撑链（V4 → V3 → V5 → V6 → V2）
        tier_order = {"V4_": 1, "V3_": 2, "V5_": 3, "V6_": 4, "V2_": 5}
        expert_support_chain.sort(
            key=lambda x: min(
                (tier_order.get(prefix, 99) for prefix in tier_order if x.get("role_id", "").startswith(prefix)),
                default=99,
            )
        )

        # 4. 生成向后兼容字段
        question = structured_requirements.get("project_task") or user_input[:200] if user_input else "待定"
        deliverables_list = [d.get("deliverable_name", d.get("deliverable_id")) for d in deliverable_answers]
        answer_summary = self._generate_combined_summary(deliverable_answers)

        # 🆕 v7.154: 增强 timeline 和 budget 提取逻辑
        # 优先级：顶层字段 > constraints 子字段 > 默认值
        timeline = structured_requirements.get("timeline")
        if not timeline or timeline == "待定":
            constraints = structured_requirements.get("constraints", {})
            if isinstance(constraints, dict):
                timeline = constraints.get("timeline") or constraints.get("project_timeline")
        if not timeline or timeline in ["待定", "未明确", "N/A", None]:
            timeline = "请参考专家报告中的实施规划"

        budget_range = structured_requirements.get("budget_range")
        if not budget_range or budget_range == "待定":
            constraints = structured_requirements.get("constraints", {})
            if isinstance(constraints, dict):
                budget_range = constraints.get("budget") or constraints.get("budget_range")
        if not budget_range or budget_range in ["待定", "未明确", "N/A", None]:
            budget_range = "请参考专家报告中的成本估算"

        result = {
            "deliverable_answers": deliverable_answers,
            "expert_support_chain": expert_support_chain,
            "question": question,
            "answer": answer_summary,
            "deliverables": deliverables_list,
            "timeline": timeline if isinstance(timeline, str) else "请参考专家报告中的实施规划",
            "budget_range": budget_range if isinstance(budget_range, str) else "请参考专家报告中的成本估算",
        }

        logger.info(f"🎯 [v7.0] 提取完成: {len(deliverable_answers)} 个交付物答案, {len(expert_support_chain)} 个支撑专家")
        return result

    def _find_owner_result(self, agent_results: Dict[str, Any], owner_role: str) -> Optional[Dict[str, Any]]:
        """
        在 agent_results 中查找匹配的专家输出

        owner_role 可能是完整描述如 "V2_高净值住宅空间与个性化设计总规划师_2-1"
        agent_results key 可能是 "V2_设计总监_2-1"

        匹配策略（按优先级）：
        1. 精确匹配
        2. 后缀匹配（如 "2-1"）- 最可靠，因为后缀是唯一标识符
        3. 前缀匹配（如 "V2_"）- 作为兜底

        🔧 v7.154: 增强匹配逻辑，支持动态角色名称与简化角色名称的匹配
        """
        import re

        # 1. 精确匹配
        if owner_role in agent_results:
            return agent_results[owner_role]

        # 2. 后缀匹配（提取 "2-1" 这样的后缀）
        # owner_role 格式: "V2_高净值住宅空间与个性化设计总规划师_2-1"
        # agent_results key 格式: "V2_设计总监_2-1"
        suffix_match = re.search(r"(\d+-\d+)$", owner_role)
        if suffix_match:
            suffix = suffix_match.group(1)  # 如 "2-1"
            tier_prefix = owner_role.split("_")[0] if "_" in owner_role else ""  # 如 "V2"

            for key in agent_results.keys():
                # 检查 key 是否以相同后缀结尾，且前缀匹配
                if key.endswith(f"_{suffix}") or key.endswith(f"-{suffix}"):
                    # 确保层级前缀也匹配（V2 匹配 V2，不匹配 V3）
                    key_prefix = key.split("_")[0] if "_" in key else ""
                    if tier_prefix and key_prefix == tier_prefix:
                        logger.debug(f"🎯 [v7.154] 后缀匹配成功: {owner_role} -> {key} (suffix={suffix})")
                        return agent_results[key]

        # 3. 前缀匹配（如 V2_）- 作为兜底
        parts = owner_role.split("_")
        if len(parts) >= 1:
            tier_prefix = parts[0]  # V2, V3, V4 等

            # 查找以此前缀开头的专家
            for key in agent_results.keys():
                if key.startswith(f"{tier_prefix}_"):
                    logger.debug(f"🔄 [v7.154] 前缀匹配成功: {owner_role} -> {key} (prefix={tier_prefix})")
                    return agent_results[key]

        logger.warning(f"⚠️ [v7.154] 未找到匹配的专家: {owner_role}")
        return None

    def _extract_owner_deliverable_output(self, owner_result: Dict[str, Any], deliverable_id: str) -> str:
        """
        从责任者输出中提取针对特定交付物的答案

        优先顺序：
        1. structured_data.task_execution_report.deliverable_outputs 中匹配的内容
        2. structured_output.task_results 中匹配 deliverable_id 的内容
        3. structured_data 中的主要内容
        4. analysis 或 content 字段

        🔧 v7.6: 增强处理嵌套 JSON 字符串和重复内容
        """
        if not owner_result:
            return "暂无输出"

        # 🔧 v7.6: 优先从 structured_data.task_execution_report.deliverable_outputs 提取
        structured_data = owner_result.get("structured_data", {})
        if structured_data and isinstance(structured_data, dict):
            task_execution_report = structured_data.get("task_execution_report", {})
            if task_execution_report and isinstance(task_execution_report, dict):
                deliverable_outputs = task_execution_report.get("deliverable_outputs", [])
                if deliverable_outputs and isinstance(deliverable_outputs, list):
                    for output in deliverable_outputs:
                        if not isinstance(output, dict):
                            continue
                        output_name = output.get("deliverable_name", "")
                        content = output.get("content", "")

                        if content:
                            # 🔧 处理嵌套 JSON 字符串（LLM 可能返回 markdown 代码块）
                            cleaned_content = self._clean_nested_json_content(content)
                            if cleaned_content:
                                logger.debug(f"✅ 从 deliverable_outputs 提取内容: {output_name[:30]}")
                                return cleaned_content

        # 尝试从 TaskOrientedExpertOutput 结构中提取
        structured_output = owner_result.get("structured_output", {})
        if structured_output and isinstance(structured_output, dict):
            task_results = structured_output.get("task_results", [])
            for task in task_results:
                if task.get("deliverable_id") == deliverable_id:
                    content = task.get("content", "")
                    if content:
                        return self._clean_nested_json_content(content)

            # 如果没有匹配的 deliverable_id，返回第一个 task 的内容
            if task_results:
                first_task = task_results[0]
                content = first_task.get("content", "")
                if content:
                    return self._clean_nested_json_content(content)

        # 从 structured_data 中提取核心输出字段
        if structured_data and isinstance(structured_data, dict):
            # 尝试提取核心输出字段
            for key in ["core_output", "deliverable_output", "main_content", "analysis_result", "recommendation"]:
                if key in structured_data:
                    value = structured_data[key]
                    if isinstance(value, str) and value:
                        return self._clean_nested_json_content(value)
                    elif isinstance(value, dict):
                        return self._format_dict_as_readable(value)

            # 🔧 v7.6: 不再将整个 structured_data 作为 JSON 返回
            # 而是尝试提取有意义的内容
            # 跳过元数据字段
            skip_keys = {"protocol_execution", "execution_metadata", "task_completion_summary", "content"}
            meaningful_data = {k: v for k, v in structured_data.items() if k not in skip_keys and v}
            if meaningful_data:
                return self._format_dict_as_readable(meaningful_data)

        # 回退到 analysis 或 content 字段
        analysis = owner_result.get("analysis", "")
        if analysis:
            return self._clean_nested_json_content(analysis)

        content = owner_result.get("content", "")
        if content:
            return self._clean_nested_json_content(content)

        return "暂无输出"

    def _clean_nested_json_content(self, content: Any) -> str:
        """
        清理嵌套的 JSON 内容

        处理 LLM 返回的 markdown 代码块包裹的 JSON，
        提取实际有意义的内容而不是原始 JSON 字符串
        """
        if not content:
            return ""

        # 如果是字典或列表，转换为可读格式
        if isinstance(content, (dict, list)):
            return self._format_dict_as_readable(content)

        # 如果是字符串
        if isinstance(content, str):
            text = content.strip()

            # 移除 markdown 代码块包裹
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            # 尝试解析为 JSON
            if text.startswith("{") or text.startswith("["):
                try:
                    parsed = json.loads(text)
                    # 如果解析成功，检查是否包含嵌套的 task_execution_report
                    if isinstance(parsed, dict):
                        # 提取有意义的内容
                        if "task_execution_report" in parsed:
                            ter = parsed["task_execution_report"]
                            if isinstance(ter, dict) and "deliverable_outputs" in ter:
                                outputs = ter["deliverable_outputs"]
                                if outputs and isinstance(outputs, list):
                                    # 递归提取第一个交付物的内容
                                    first_output = outputs[0]
                                    if isinstance(first_output, dict):
                                        inner_content = first_output.get("content", "")
                                        if inner_content:
                                            return self._clean_nested_json_content(inner_content)
                        # 格式化为可读内容
                        return self._format_dict_as_readable(parsed)
                    elif isinstance(parsed, list):
                        return self._format_dict_as_readable(parsed)
                except json.JSONDecodeError:
                    pass

            # 返回清理后的文本
            return text

        return str(content)

    def _format_dict_as_readable(self, data: Any, indent: int = 0) -> str:
        """
        将字典/列表格式化为人类可读的 Markdown 格式
        而不是原始 JSON
        """
        if data is None:
            return ""

        lines = []
        prefix = "  " * indent

        if isinstance(data, dict):
            for key, value in data.items():
                # 跳过元数据字段
                if key in {
                    "completion_status",
                    "completion_rate",
                    "quality_self_assessment",
                    "notes",
                    "protocol_status",
                    "compliance_confirmation",
                    "challenge_details",
                    "reinterpretation",
                    "confidence",
                    "execution_time_estimate",
                    "execution_notes",
                    "dependencies_satisfied",
                }:
                    continue

                # 格式化键名
                readable_key = key.replace("_", " ").title()

                if isinstance(value, dict):
                    lines.append(f"{prefix}**{readable_key}**:")
                    lines.append(self._format_dict_as_readable(value, indent + 1))
                elif isinstance(value, list):
                    lines.append(f"{prefix}**{readable_key}**:")
                    for item in value:
                        if isinstance(item, dict):
                            lines.append(self._format_dict_as_readable(item, indent + 1))
                        else:
                            lines.append(f"{prefix}  - {item}")
                elif value:
                    lines.append(f"{prefix}**{readable_key}**: {value}")
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    lines.append(self._format_dict_as_readable(item, indent))
                    lines.append("")  # 空行分隔
                else:
                    lines.append(f"{prefix}- {item}")
        else:
            lines.append(f"{prefix}{data}")

        return "\n".join(lines)

    def _extract_quality_score(self, owner_result: Dict[str, Any]) -> Optional[float]:
        """从专家输出中提取质量分数"""
        if not owner_result:
            return None

        # 从 structured_output 提取
        structured_output = owner_result.get("structured_output", {})
        if structured_output and isinstance(structured_output, dict):
            # 从 protocol_execution 提取
            protocol_execution = structured_output.get("protocol_execution", {})
            if protocol_execution:
                confidence = protocol_execution.get("confidence_level")
                if confidence is not None:
                    try:
                        return float(confidence) * 100  # 转换为百分制
                    except (TypeError, ValueError):
                        pass

            # 从 task_results 提取
            task_results = structured_output.get("task_results", [])
            if task_results:
                completeness_scores = [
                    t.get("completeness_score", 0)
                    for t in task_results
                    if isinstance(t.get("completeness_score"), (int, float))
                ]
                if completeness_scores:
                    return sum(completeness_scores) / len(completeness_scores) * 100

        # 从 confidence 字段提取
        confidence = owner_result.get("confidence")
        if confidence is not None:
            try:
                return float(confidence) * 100
            except (TypeError, ValueError):
                pass

        return None

    def _generate_answer_summary(self, full_answer: str) -> str:
        """生成答案摘要（200字以内）"""
        if not full_answer or full_answer == "暂无输出":
            return "暂无摘要"

        # 简单截取前200字
        if len(full_answer) <= 200:
            return full_answer

        # 尝试在句子边界截断
        truncated = full_answer[:200]
        last_period = max(truncated.rfind("。"), truncated.rfind("！"), truncated.rfind("？"))
        if last_period > 100:
            return truncated[: last_period + 1]

        return truncated + "..."

    def _generate_combined_summary(self, deliverable_answers: List[Dict[str, Any]]) -> str:
        """生成多交付物的综合摘要（向后兼容用）"""
        if not deliverable_answers:
            return "暂无核心答案"

        summaries = []
        for da in deliverable_answers:
            name = da.get("deliverable_name", da.get("deliverable_id", "未知"))
            summary = da.get("answer_summary", "")
            if summary:
                summaries.append(f"【{name}】{summary}")

        if not summaries:
            return "暂无核心答案"

        return " ".join(summaries)

    def _extract_supporter_contribution(
        self, role_id: str, agent_result: Dict[str, Any], deliverable_metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """提取支撑专家的贡献信息"""
        if not agent_result:
            return None

        # 确定角色名称
        role_name = agent_result.get("role_name", role_id)

        # 提取贡献摘要
        analysis = agent_result.get("analysis", "")
        content = agent_result.get("content", "")
        contribution_text = analysis or content or ""

        if not contribution_text:
            structured_data = agent_result.get("structured_data", {})
            if structured_data:
                contribution_text = json.dumps(structured_data, ensure_ascii=False)[:500]

        if not contribution_text:
            return None

        # 生成摘要
        contribution_summary = contribution_text[:200] + "..." if len(contribution_text) > 200 else contribution_text

        # 确定关联的交付物
        related_deliverables = []
        for d_id, d_meta in deliverable_metadata.items():
            supporters = d_meta.get("supporters", [])
            if any(
                role_id.startswith(s.split("_")[0] + "_" + s.split("_")[1]) if len(s.split("_")) >= 2 else s == role_id
                for s in supporters
            ):
                related_deliverables.append(d_id)

        return {
            "role_id": role_id,
            "role_name": role_name,
            "contribution_type": "support",
            "contribution_summary": contribution_summary,
            "related_deliverables": related_deliverables,
        }

    def _consolidate_search_references(self, state: ProjectAnalysisState) -> List[Dict[str, Any]]:
        """
        🆕 v7.122: 统一处理搜索引用，确保数据完整性和一致性

        功能：
        1. 从 state 中提取 search_references
        2. 容错处理（处理 None 或空列表）
        3. 去重（基于 title + url）
        4. 按质量分数排序
        5. 验证必需字段

        Args:
            state: 项目分析状态

        Returns:
            处理后的搜索引用列表
        """
        # 1. 提取搜索引用（容错处理）
        raw_references = state.get("search_references") or []

        if not raw_references:
            logger.debug("ℹ️ [v7.122] 无搜索引用数据")
            return []

        if not isinstance(raw_references, list):
            logger.warning(f"⚠️ [v7.122] search_references 类型错误: {type(raw_references)}")
            return []

        logger.info(f"📚 [v7.122] 开始处理 {len(raw_references)} 条原始搜索引用")

        # 2. 去重（基于 title + url）
        unique_references = []
        seen = set()

        for ref in raw_references:
            if not isinstance(ref, dict):
                logger.warning(f"⚠️ [v7.122] 跳过非字典引用: {type(ref)}")
                continue

            # 验证必需字段
            if not ref.get("title"):
                logger.warning("⚠️ [v7.122] 跳过缺少标题的引用")
                continue

            # 去重键
            title = ref.get("title", "")
            url = ref.get("url", "")
            key = (title, url)

            if key in seen:
                logger.debug(f"⚠️ [v7.122] 跳过重复引用: {title}")
                continue

            seen.add(key)
            unique_references.append(ref)

        logger.info(f"📋 [v7.122] 去重后: {len(unique_references)} 条唯一引用")

        # 3. 按质量分数排序（如果有）
        def get_quality_score(ref: Dict[str, Any]) -> float:
            """提取质量分数，支持多种格式"""
            # 优先使用 quality_score
            if "quality_score" in ref and ref["quality_score"] is not None:
                try:
                    return float(ref["quality_score"])
                except (TypeError, ValueError):
                    pass

            # 次选 relevance_score
            if "relevance_score" in ref and ref["relevance_score"] is not None:
                try:
                    return float(ref["relevance_score"]) * 100  # 转换为 0-100 范围
                except (TypeError, ValueError):
                    pass

            # 默认分数
            return 50.0

        try:
            sorted_references = sorted(unique_references, key=get_quality_score, reverse=True)  # 高分在前
            logger.debug("✅ [v7.122] 已按质量分数排序")
        except Exception as e:
            logger.warning(f"⚠️ [v7.122] 排序失败，保持原顺序: {e}")
            sorted_references = unique_references

        # 4. 添加引用编号（如果没有）
        for idx, ref in enumerate(sorted_references, 1):
            if "reference_number" not in ref:
                ref["reference_number"] = idx

        logger.info(f"✅ [v7.122] 搜索引用处理完成: {len(sorted_references)} 条")

        return sorted_references
