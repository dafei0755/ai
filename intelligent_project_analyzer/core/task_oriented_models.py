"""
任务导向的统一数据模型
重新梳理专家输出结构，确保完全围绕任务分配

版本: v1.0
创建日期: 2025-12-05
目标:
1. 任务分配与预期输出合并为明确指令
2. 主动性协议闭环执行
3. 输出完全围绕任务，消除不可预计输出
"""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, validator


class DeliverableFormat(str, Enum):
    """交付物格式类型"""

    ANALYSIS = "analysis"  # 分析报告
    STRATEGY = "strategy"  # 策略方案
    DESIGN = "design"  # 设计方案
    RECOMMENDATION = "recommendation"  # 建议清单
    EVALUATION = "evaluation"  # 评估报告
    GUIDELINE = "guideline"  # 指导方针
    #  v7.3扩展：LLM常用的额外格式类型
    FRAMEWORK = "framework"  # 框架方案
    MODEL = "model"  # 模型/建模
    CHECKLIST = "checklist"  # 检查清单
    PLAN = "plan"  # 计划方案
    #  v7.20: 扩展更多 LLM 常生成的格式类型（解决 Pydantic 验证失败问题）
    REPORT = "report"  # 通用报告
    BLUEPRINT = "blueprint"  # 蓝图/规划图
    CASE_STUDY = "case_study"  # 案例研究
    DOCUMENT = "document"  # 通用文档
    PROPOSAL = "proposal"  # 提案
    DIAGRAM = "diagram"  # 图表/流程图
    #  v7.23: 全面扩展 - 解决项目总监6次验证失败问题（日志显示缺失的值）
    PRESENTATION = "presentation"  # 演示文稿 (PPT/Keynote)
    GUIDEBOOK = "guidebook"  # 指南手册
    MANUAL = "manual"  # 操作手册
    NARRATIVE = "narrative"  # 叙事/故事
    EXPERIENCE_MAP = "experience_map"  # 体验地图
    MATERIALS_LIST = "materials_list"  # 材料清单
    RESEARCH = "research"  # 研究报告
    CONCEPT = "concept"  # 概念设计
    SPECIFICATION = "specification"  # 规格说明
    PERSONA = "persona"  # 用户画像
    SCENARIO = "scenario"  # 场景设计
    JOURNEY_MAP = "journey_map"  # 旅程地图
    AUDIT = "audit"  # 审计报告
    BENCHMARK = "benchmark"  # 基准对标
    SUMMARY = "summary"  # 摘要总结
    ROADMAP = "roadmap"  # 路线图
    MATRIX = "matrix"  # 矩阵分析
    CANVAS = "canvas"  # 画布工具
    PROFILE = "profile"  # 档案/画像
    INSIGHT = "insight"  # 洞察报告
    MAPPING = "mapping"  # 映射/对应关系
    #  v7.130: 补充缺失的枚举值（修复 Pydantic 验证错误）
    GUIDE = "guide"  # 指南
    VISUALIZATION = "visualization"  # 可视化
    CATALOG = "catalog"  # 目录
    LIST = "list"  # 清单列表


#  v7.20+v7.23: LLM 输出格式映射表（将非标准格式映射到标准枚举）
# 解决项目总监验证失败问题：日志显示 presentation, guidebook, manual 等值验证失败
DELIVERABLE_FORMAT_MAPPING: Dict[str, str] = {
    # === 设计类映射 ===
    "design_plan": "design",
    "flow_design": "design",
    "spatial_design": "design",
    "interior_design": "design",
    "design_scheme": "design",
    "design_document": "design",
    "design_guideline": "guideline",
    "design_detail": "design",
    "concept_design": "concept",
    "concept_presentation": "presentation",
    # === 分析/报告类映射 ===
    "case_study_report": "case_study",
    "technical_report": "report",
    "compliance_report": "evaluation",
    "research_report": "research",
    "analysis_report": "analysis",
    "feasibility_report": "analysis",
    "financial_analysis": "analysis",
    "market_analysis": "analysis",
    "user_research": "research",
    "competitive_analysis": "benchmark",
    "written_report": "report",
    "written_memo": "document",
    # === 图表/可视化类映射 ===
    "flow_diagram": "diagram",
    "flow_chart": "diagram",
    "flowchart": "diagram",
    "technical_illustration": "diagram",
    "technical_drawing": "blueprint",
    "technical_manual": "manual",
    # === 计划/策略类映射 ===
    "action_plan": "plan",
    "implementation_plan": "plan",
    "project_plan": "plan",
    "strategy_document": "strategy",
    "strategic_framework": "framework",
    "operation_strategy": "strategy",
    "business_strategy": "strategy",
    # === 叙事/体验类映射 ===
    "narrative_framework": "narrative",
    "narrative_design": "narrative",
    "experience_design": "experience_map",
    "user_journey": "journey_map",
    "customer_journey": "journey_map",
    "persona_profile": "persona",
    "user_persona": "persona",
    "scenario_design": "scenario",
    # === 指南/手册类映射 ===
    "design_blueprint": "blueprint",
    "guidelines": "guideline",
    "construction_guideline": "guideline",
    "brand_guideline": "guideline",
    "style_guide": "guideline",
    "user_manual": "manual",
    "operation_manual": "manual",
    # === 演示/文档类映射 ===
    "proposal_document": "proposal",
    "framework_document": "framework",
    "pdf": "document",
    "powerpoint": "presentation",
    "ppt": "presentation",
    "spreadsheet": "document",
    "excel": "document",
    # === 材料/清单类映射 ===
    "materials_specification": "materials_list",
    "material_list": "materials_list",
    "bill_of_materials": "materials_list",
    "quality_checklist": "checklist",
    "review_checklist": "checklist",
    # === 其他常见格式映射 ===
    "insight_report": "insight",
    "summary_report": "summary",
    "executive_summary": "summary",
    "project_roadmap": "roadmap",
    "decision_matrix": "matrix",
    "comparison_matrix": "matrix",
    "business_canvas": "canvas",
    "model_canvas": "canvas",
    # ===  P1修复: 描述性文本格式映射 ===
    "schematic drawings": "diagram",
    "schematic drawing": "diagram",
    "3d visualizations": "visualization",
    "3d visualization": "visualization",
    "product catalog": "catalog",
    "product catalogue": "catalog",
    "cost estimate": "report",
    "cost estimation": "report",
    "color boards": "design",
    "color board": "design",
    "material palettes": "design",
    "material palette": "design",
    "technical guide": "guide",
    "priority list": "list",
    "priority listing": "list",
}


class Priority(str, Enum):
    """优先级"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DeliverableSpec(BaseModel):
    """交付物规格说明

    v7.65: 增加 require_search 字段，支持强制搜索标记
    """

    name: str = Field(title="名称", description="交付物名称")
    description: str = Field(title="描述", description="具体要求和内容描述")
    format: DeliverableFormat = Field(title="格式", description="输出格式类型")
    priority: Priority = Field(title="优先级", default=Priority.HIGH, description="优先级")
    success_criteria: List[str] = Field(title="验收标准", description="该交付物的验收标准", min_items=1, max_items=3)

    #  v7.65: 强制搜索标记（针对案例库、趋势分析等必须外部资料的交付物）
    require_search: bool = Field(title="强制搜索", default=False, description="是否强制要求使用搜索工具获取外部资料（适用于案例库、趋势分析等类型）")

    #  v7.20: 自动映射非标准格式到标准枚举
    @validator("format", pre=True)
    def normalize_format(cls, v):
        """将非标准格式名称映射到标准 DeliverableFormat 枚举"""
        if isinstance(v, DeliverableFormat):
            return v
        if isinstance(v, str):
            v_lower = v.lower().strip()
            # 1. 尝试直接匹配枚举值
            try:
                return DeliverableFormat(v_lower)
            except ValueError:
                pass
            # 2. 尝试通过映射表转换
            if v_lower in DELIVERABLE_FORMAT_MAPPING:
                mapped = DELIVERABLE_FORMAT_MAPPING[v_lower]
                return DeliverableFormat(mapped)
            # 3. 模糊匹配：检查是否包含关键词
            for fmt in DeliverableFormat:
                if fmt.value in v_lower or v_lower in fmt.value:
                    return fmt
            # 4. 兜底：返回 ANALYSIS（最通用的类型）
            import logging

            logging.getLogger(__name__).warning(f"️ 未知交付物格式 '{v}'，回退到 analysis")
            return DeliverableFormat.ANALYSIS
        return v


class TaskInstruction(BaseModel):
    """
    统一的任务执行指令（合并tasks+expected_output+focus_areas）

     v7.10: 支持创意叙事模式标识
    """

    objective: str = Field(title="核心目标", description="这个角色在本项目中的核心目标（1句话明确表述）")
    deliverables: List[DeliverableSpec] = Field(title="交付物清单", description="具体的交付物要求列表", min_items=1, max_items=5)
    success_criteria: List[str] = Field(title="成功标准", description="整体任务完成的判断标准（2-4条）", min_items=2, max_items=4)
    constraints: List[str] = Field(title="执行约束", default_factory=list, description="执行约束条件（如时间、预算、技术限制）")
    context_requirements: List[str] = Field(title="上下文需求", default_factory=list, description="执行此任务需要的上下文信息")
    #  v7.10: 创意叙事模式标识
    is_creative_narrative: bool = Field(title="创意叙事模式", default=False, description="是否为创意叙事类任务（V3专家）- 此模式下放宽量化指标要求")

    @validator("success_criteria", pre=True, always=True)
    def ensure_min_success_criteria(cls, v):
        """v8.0 修复：自动补全不足2条的 success_criteria，防止 LLM 少填导致 ValidationError"""
        if not v:
            return ["分析内容完整准确", "提供可执行建议"]
        lst = list(v)
        defaults = ["分析内容完整准确", "提供可执行建议", "符合预期输出格式", "满足项目目标要求"]
        while len(lst) < 2:
            lst.append(defaults[len(lst)])
        return lst[:4]


# ============================================================================
# 协议执行相关模型
# ============================================================================


class ProtocolStatus(str, Enum):
    """协议执行状态"""

    COMPLIED = "complied"  # 遵照执行
    CHALLENGED = "challenged"  # 提出挑战
    REINTERPRETED = "reinterpreted"  # 重新诠释


class ChallengeFlag(BaseModel):
    """挑战标记"""

    challenged_item: str = Field(title="被挑战内容", description="被挑战的具体内容")
    challenge_reason: str = Field(title="挑战理由", description="挑战理由和依据")
    alternative_proposal: str = Field(title="替代方案", description="替代方案或建议")
    confidence: float = Field(title="置信度", ge=0.0, le=1.0, description="挑战的置信度")


class ReinterpretationDetail(BaseModel):
    """重新诠释详情"""

    original_interpretation: str = Field(title="原始诠释", description="原始诠释内容")
    new_interpretation: str = Field(title="新诠释", description="新的诠释角度")
    reinterpretation_rationale: str = Field(title="诠释依据", description="重新诠释的依据和理由")
    impact_on_approach: str = Field(title="方法论影响", description="对方法论的影响")


class ProtocolExecutionReport(BaseModel):
    """专家主动性协议执行报告（确保闭环）"""

    protocol_status: ProtocolStatus = Field(title="协议状态", description="协议执行状态")

    # 遵照执行的情况
    compliance_confirmation: Optional[str] = Field(
        title="合规确认", default=None, description="确认接受需求分析师洞察的声明（当protocol_status=complied时必填）"
    )

    # 有挑战的情况
    challenge_details: Optional[List[ChallengeFlag]] = Field(
        title="挑战详情", default=None, description="挑战详情列表（当protocol_status=challenged时必填）"
    )

    # 重新诠释的情况
    reinterpretation: Optional[ReinterpretationDetail] = Field(
        title="重新诠释", default=None, description="重新诠释详情（当protocol_status=reinterpreted时必填）"
    )

    def model_post_init(self, __context):
        """验证协议状态与对应字段的一致性"""
        if self.protocol_status == ProtocolStatus.COMPLIED and not self.compliance_confirmation:
            raise ValueError("protocol_status为complied时，compliance_confirmation字段必须填充")
        if self.protocol_status == ProtocolStatus.CHALLENGED and not self.challenge_details:
            raise ValueError("protocol_status为challenged时，challenge_details字段必须填充")
        if self.protocol_status == ProtocolStatus.REINTERPRETED and not self.reinterpretation:
            raise ValueError("protocol_status为reinterpreted时，reinterpretation字段必须填充")


# ============================================================================
# 任务执行相关模型
# ============================================================================


class CompletionStatus(str, Enum):
    """完成状态"""

    COMPLETED = "completed"  # 完全完成
    PARTIAL = "partial"  # 部分完成
    UNABLE = "unable"  # 无法完成


class DeliverableOutput(BaseModel):
    """
    交付物输出

     v7.10: 支持创意模式 - 叙事类交付物可选填量化指标
     v7.18.2: 移除 validator 以修复 OpenAI structured output schema 验证错误
     v7.64: 添加搜索引用字段 - 记录工具调用产生的搜索结果
    """

    deliverable_name: str = Field(title="交付物名称", description="对应TaskInstruction中的deliverable名称")
    content: str = Field(title="内容", description="交付物具体内容（纯文本格式）。LLM应直接生成文本内容，而非结构化数据。")
    completion_status: CompletionStatus = Field(title="完成状态", description="完成状态")
    #  v7.10: 放宽量化指标约束 - 创意叙事模式下可选
    completion_rate: Optional[float] = Field(
        title="完成度", ge=0.0, le=1.0, default=1.0, description="完成度百分比（创意叙事模式下可省略，默认1.0）"  # 默认完成
    )
    notes: Optional[str] = Field(title="备注", default=None, description="说明或备注")
    quality_self_assessment: Optional[float] = Field(
        title="质量自评", ge=0.0, le=1.0, default=None, description="质量自评分数（0-1）（创意叙事模式下可省略）"  # 创意模式下可不填
    )
    #  v7.64: 搜索引用记录
    search_references: Optional[List["SearchReference"]] = Field(
        title="搜索引用", default=None, description="此交付物使用的搜索结果引用列表（v7.64+）"
    )


class TaskExecutionReport(BaseModel):
    """任务执行报告"""

    deliverable_outputs: List[DeliverableOutput] = Field(title="交付物输出", description="按任务指令要求的交付物输出", min_items=1)
    task_completion_summary: str = Field(title="任务完成总结", description="任务完成情况总结（2-3句话）")
    additional_insights: Optional[List[str]] = Field(
        title="额外洞察", default=None, description="执行任务过程中的额外洞察（仅在与任务直接相关时填充）"
    )
    execution_challenges: Optional[List[str]] = Field(title="执行挑战", default=None, description="执行过程中遇到的挑战或限制")


class ExecutionMetadata(BaseModel):
    """
    执行元数据

     v7.10: 支持创意叙事模式 - 部分字段可选
    """

    confidence: float = Field(title="置信度", ge=0.0, le=1.0, description="整体执行置信度")
    #  v7.10: 创意叙事模式下可省略 completion_rate
    completion_rate: Optional[float] = Field(
        title="完成度", ge=0.0, le=1.0, default=1.0, description="整体完成度（创意叙事模式下默认1.0）"
    )
    execution_time_estimate: Optional[str] = Field(title="执行时间估算", default=None, description="执行时间估算（创意叙事模式下可省略）")
    execution_notes: Optional[str] = Field(title="执行备注", default=None, description="执行备注")
    dependencies_satisfied: bool = Field(title="依赖满足", description="依赖条件是否满足", default=True)


# ============================================================================
# 统一的专家输出结构
# ============================================================================


class TaskOrientedExpertOutput(BaseModel):
    """任务导向的专家输出结构（完全围绕任务分配）"""

    # === 核心部分：任务响应（必填） ===
    task_execution_report: TaskExecutionReport = Field(title="任务执行报告", description="任务执行报告 - 核心输出内容")

    # === 协议部分：主动性闭环（必填） ===
    protocol_execution: ProtocolExecutionReport = Field(title="协议执行报告", description="协议执行报告 - 说明是否遵照/挑战/重新诠释")

    # === 元数据：质量评估（必填） ===
    execution_metadata: ExecutionMetadata = Field(title="执行元数据", description="执行元数据 - 置信度、完成度等")

    def get_completion_summary(self) -> Dict[str, Any]:
        """获取完成情况摘要"""
        total_deliverables = len(self.task_execution_report.deliverable_outputs)
        completed_deliverables = sum(
            1
            for d in self.task_execution_report.deliverable_outputs
            if d.completion_status == CompletionStatus.COMPLETED
        )

        avg_quality = (
            sum(d.quality_self_assessment for d in self.task_execution_report.deliverable_outputs) / total_deliverables
            if total_deliverables > 0
            else 0.0
        )

        return {
            "total_deliverables": total_deliverables,
            "completed_deliverables": completed_deliverables,
            "completion_percentage": completed_deliverables / total_deliverables * 100,
            "average_quality_score": round(avg_quality, 2),
            "protocol_status": self.protocol_execution.protocol_status.value,
            "overall_confidence": self.execution_metadata.confidence,
        }


# ============================================================================
# 角色配置相关模型（用于项目总监）
# ============================================================================


class RoleWithTaskInstruction(BaseModel):
    """包含明确任务指令的角色对象"""

    role_id: str = Field(title="角色ID", description="角色ID（如'3-1'）")
    dynamic_role_name: str = Field(title="动态角色名称", description="动态角色名称")
    task_instruction: TaskInstruction = Field(title="任务执行指令", description="统一的任务执行指令")
    dependencies: List[str] = Field(title="依赖关系", default_factory=list, description="依赖的其他角色")
    execution_priority: int = Field(title="执行优先级", default=1, description="执行优先级（1最高）")


class TaskInstructionSet(BaseModel):
    """任务指令集（项目总监输出）"""

    project_objective: str = Field(title="项目目标", description="整个项目的核心目标")
    roles_with_instructions: List[RoleWithTaskInstruction] = Field(
        title="角色任务分配", description="带有任务指令的角色列表", min_items=3, max_items=8
    )
    execution_strategy: str = Field(title="执行策略", description="执行策略说明")
    success_metrics: List[str] = Field(title="成功指标", description="项目成功指标")


# ============================================================================
# 辅助工具函数
# ============================================================================


def validate_task_instruction_completeness(instruction: TaskInstruction) -> List[str]:
    """验证任务指令的完整性"""
    issues = []

    if len(instruction.objective) < 10:
        issues.append("objective目标描述过于简短")

    if not instruction.deliverables:
        issues.append("缺少deliverables交付物定义")

    for i, deliverable in enumerate(instruction.deliverables):
        if len(deliverable.description) < 10:
            issues.append(f"交付物{i+1}描述过于简短")
        if not deliverable.success_criteria:
            issues.append(f"交付物{i+1}缺少验收标准")

    if len(instruction.success_criteria) < 2:
        issues.append("success_criteria成功标准不足（至少需要2条）")

    return issues


def generate_task_instruction_template(role_type: str) -> TaskInstruction:
    """为不同角色类型生成任务指令模板"""
    templates = {
        "V2_design_director": TaskInstruction(
            objective="作为设计总监，整合所有专家建议，制定最终设计方案",
            deliverables=[
                DeliverableSpec(
                    name="综合设计方案",
                    description="整合所有专家建议的最终设计方案",
                    format=DeliverableFormat.DESIGN,
                    priority=Priority.HIGH,
                    success_criteria=["方案完整可执行", "预算控制合理"],
                )
            ],
            success_criteria=["所有专家建议得到合理整合", "最终方案满足用户核心需求"],
        ),
        "V3_narrative_expert": TaskInstruction(
            objective="构建项目的人物叙事体系和体验设计",
            deliverables=[
                DeliverableSpec(
                    name="人物原型分析",
                    description="核心用户画像和需求特征",
                    format=DeliverableFormat.ANALYSIS,
                    priority=Priority.HIGH,
                    success_criteria=["画像真实可信", "需求明确具体"],
                ),
                DeliverableSpec(
                    name="体验旅程地图",
                    description="用户完整体验流程设计",
                    format=DeliverableFormat.DESIGN,
                    priority=Priority.HIGH,
                    success_criteria=["流程完整", "触点清晰"],
                ),
            ],
            success_criteria=["人物叙事具有设计指导价值", "体验设计可操作落地"],
        ),
    }

    return templates.get(
        role_type,
        TaskInstruction(
            objective="完成专业领域的深度分析",
            deliverables=[
                DeliverableSpec(
                    name="专业分析报告",
                    description="基于专业知识的深度分析",
                    format=DeliverableFormat.ANALYSIS,
                    priority=Priority.HIGH,
                    success_criteria=["分析深入专业", "结论明确可信"],
                )
            ],
            success_criteria=["分析质量达到专业标准", "结论对项目有指导意义"],
        ),
    )


# ============================================================================
#  v7.64: 搜索工具集成 - 搜索引用和质量控制
# ============================================================================


class SearchReference(BaseModel):
    """
    单条搜索结果引用（v7.64）

    用于记录工具调用产生的搜索结果，支持质量评分和引用追踪
    """

    # === 基本信息 ===
    source_tool: Literal["tavily", "arxiv", "milvus", "bocha"] = Field(
        title="来源工具", description="搜索工具名称"
    )  # v7.154: ragflow → milvus
    title: str = Field(title="标题", description="搜索结果标题")
    url: Optional[str] = Field(title="URL", default=None, description="结果链接（知识库可能无URL）")
    snippet: str = Field(title="摘要", max_length=300, description="搜索结果摘要（限制300字）")

    # === 质量评分 ===
    relevance_score: float = Field(title="相关性分数", ge=0.0, le=1.0, description="搜索引擎返回的相关性分数（0-1）")
    quality_score: Optional[float] = Field(
        title="综合质量分数", ge=0.0, le=100.0, default=None, description="综合质量分数（0-100）= 相关性40% + 时效性20% + 可信度20% + 完整性20%"
    )

    # === 质量控制字段 ===
    content_complete: bool = Field(title="内容完整性", default=True, description="内容是否完整（长度检查）")
    source_credibility: Literal["high", "medium", "low", "unknown"] = Field(
        title="来源可信度", default="unknown", description="来源可信度评级"
    )

    # === 关联信息 ===
    deliverable_id: str = Field(title="关联交付物ID", description="关联的交付物名称（用于追踪）")
    query: str = Field(title="搜索查询", description="生成此结果的搜索查询")
    timestamp: str = Field(title="时间戳", description="搜索时间（ISO格式）")

    # === LLM二次评分（可选） ===
    llm_relevance_score: Optional[int] = Field(
        title="LLM相关性评分", ge=0, le=100, default=None, description="LLM对交付物适配度的二次评分（0-100）"
    )
    llm_scoring_reason: Optional[str] = Field(
        title="LLM评分理由", default=None, max_length=200, description="LLM评分的简要理由（限制200字）"
    )
