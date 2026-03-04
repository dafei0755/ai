"""
4-Step Flow 数据结构定义

定义4步骤搜索流程所需的数据类型
- Step 1: 深度分析结果
- Step 2: 搜索任务列表
- Step 3: 补充查询和框架增补
- Step 4: 最终输出文档

Author: AI Assistant
Created: 2026-02-01
Version: 1.0
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Literal

# ============================================================================
# Step 1: 深度分析相关数据结构 (v3.0 - Complete Redesign)
# ============================================================================


@dataclass
class L1ProblemDeconstruction:
    """L1 问题解构 - 结构化 (v3.1: 增加分析视角)"""

    user_identity: str  # 用户是谁（身份、角色、背景）
    explicit_needs: str  # 显性需求（用户明确表达的需求）
    implicit_motivations: str  # 隐性动机（用户未明说但暗含的动机）
    key_constraints: str  # 关键约束（时间、资源、能力等限制）
    analysis_perspective: str = ""  # v3.1: 分析视角（如"功利视角"、"体验视角"）


@dataclass
class L2MotivationDimension:
    """L2 动机维度 - v4.0: 轻量参考，不再驱动板块生成"""

    name: Literal[
        "效率",
        "控制",
        "安全",  # 功能型
        "归属",
        "认同",
        "愉悦",  # 情感型
        "地位",
        "影响",
        "连接",  # 社会型
        "意义",
        "成长",
        "超越",  # 精神型
    ]
    type: Literal["功能型", "情感型", "社会型", "精神型"]
    score: int  # 1-5分
    reason: str = ""  # v4.0: 理由（可选，不再强制30字）
    evidence: List[str] = field(default_factory=list)  # v4.0: 证据（可选）
    scenario_expression: str = ""  # 场景化表达

    def __post_init__(self):
        """验证数据完整性"""
        if not 1 <= self.score <= 5:
            raise ValueError(f"Score must be between 1-5, got {self.score}")


@dataclass
class L3CoreTension:
    """L3 核心张力 - v4.0: 简化，移除格式验证"""

    primary_motivation: str  # 主导动机
    secondary_motivation: str  # 次要动机
    tension_formula: str = ""  # v4.0: 张力公式（自由文本，不再强制 vs/+ 格式）
    tension_description: str = ""  # v4.0: 张力描述（自由文本替代）
    resolution_strategy: str = ""  # 如何平衡/解决这个张力
    hidden_insights: List[str] = None  # 隐性需求洞察列表

    def __post_init__(self):
        """v4.0: 移除张力公式格式验证"""
        if self.hidden_insights is None:
            self.hidden_insights = []


@dataclass
class L4JTBDDefinition:
    """L4 JTBD定义 - v4.0: 简化，移除 full_statement 长度要求"""

    user_role: str  # [用户身份]
    information_type: str  # [信息类型]
    task_1: str  # [任务1]
    task_2: str  # [任务2]
    full_statement: str = ""  # v4.0: 完整陈述（可选，不再强制50字）

    def __post_init__(self):
        """验证JTBD定义完整性"""
        expected_parts = [
            self.user_role,
            self.information_type,
            self.task_1,
            self.task_2,
        ]
        if not all(expected_parts):
            raise ValueError("All JTBD components (user_role, information_type, task_1, task_2) must be provided")


@dataclass
class L5SharpnessTest:
    """L5 锐度测试 - v4.0: 简化，仅保留分数+一句话理由"""

    specificity_score: int  # 1-10，专一性得分
    specificity_reason: str = ""  # v4.0: 一句话理由（不再强制30字）
    specificity_evidence: str = ""  # v4.0: 证据（可选）
    actionability_score: int = 0  # 1-10，可操作性得分
    actionability_reason: str = ""  # v4.0: 一句话理由
    actionability_evidence: str = ""  # v4.0: 证据（可选）
    depth_score: int = 0  # 1-10，深度得分
    depth_reason: str = ""  # v4.0: 一句话理由
    depth_evidence: str = ""  # v4.0: 证据（可选）
    searchability_score: int = 0  # v4.0: 新增搜索可行性得分
    searchability_reason: str = ""  # v4.0: 搜索可行性理由
    overall_quality: Literal["优秀", "良好", "合格", "不合格"] = "合格"

    def __post_init__(self):
        """验证锐度测试数据"""
        scores = [self.specificity_score, self.actionability_score, self.depth_score]
        for score in scores:
            if score != 0 and not 1 <= score <= 10:
                raise ValueError(f"All scores must be between 1-10, got {score}")


@dataclass
class HumanDimensions:
    """人性维度分析（针对设计/生活类问题）"""

    enabled: bool = False
    emotional_landscape: str | None = None  # 情绪地图
    spiritual_aspirations: str | None = None  # 精神追求
    psychological_safety_needs: str | None = None  # 心理安全需求
    ritual_behaviors: str | None = None  # 仪式行为
    memory_anchors: str | None = None  # 记忆锚点


@dataclass
class Understanding:
    """使命1：我的理解 (v4.0 - 简化验证)"""

    l1_deconstruction: L1ProblemDeconstruction  # L1 问题解构
    l2_motivations: List[L2MotivationDimension]  # L2 动机分析（v4.0: 全面扫描，输出所有score>=3的）
    l3_tension: L3CoreTension  # L3 核心张力
    l4_jtbd: L4JTBDDefinition  # L4 JTBD定义
    l5_sharpness: L5SharpnessTest  # L5 锐度测试
    human_dimensions: HumanDimensions | None = None  # 人性维度（如适用）
    comprehensive_summary: str = ""  # 综合总结
    research_dimensions: List[Dict[str, Any]] = field(default_factory=list)  # v4.0: L2.5 研究维度

    def __post_init__(self):
        """v4.0: 全面扫描模式 — 输出所有score>=3的动机（最多12个），移除summary长度限制"""
        if not 1 <= len(self.l2_motivations) <= 12:
            raise ValueError(f"Must have 1-12 motivations, got {len(self.l2_motivations)}")


@dataclass
class OutputBlockSubItem:
    """输出板块子项"""

    id: str  # 如 "1.1"
    name: str  # 子项名称
    description: str  # 具体内容说明


@dataclass
class OutputBlock:
    """输出板块 (v4.0 - 研究维度驱动，简化验证)"""

    id: str  # 如 "block_1"
    name: str  # 板块名称（研究维度标题）
    estimated_length: str = "待定"  # 预计字数/页数
    sub_items: List[OutputBlockSubItem] = field(default_factory=list)
    user_characteristics: List[str] = field(default_factory=list)  # 包含的用户特征关键词

    # v3.2 保留：核心主题定义
    core_theme: str | None = None  # 板块的单一核心主题（用于Step 1.5）
    theme_validation_passed: bool = True  # 是否通过主题验证

    # v4.0: 由 Stage 1 research_dimensions 直接填充
    search_focus: str | None = None  # 该板块的核心搜索焦点
    indicative_queries: List[str] = field(default_factory=list)  # 示范性搜索查询
    domain_knowledge_hints: str | None = None  # v4.0: 领域知识提示

    def __post_init__(self):
        """v4.0: 放宽验证 — 名称最小长度从10降为4，user_characteristics可选"""
        if len(self.name) < 4:
            raise ValueError(f"Block name must be at least 4 characters, got {len(self.name)}: '{self.name}'")
        # v4.0: user_characteristics 不再强制要求
        if not self.user_characteristics:
            self.user_characteristics = ["用户"]

        # v3.1 移除：硬编码的关键词验证已移除
        # 这些限制应该通过 prompt 引导实现，而非代码层面的硬限制
        # 如果用户明确问到施工、预算等工程落地问题，应该正面回应

    def _validate_searchability(self):
        """
        验证板块名称的可搜索性（已废弃）

        v7.333.2 变更说明：
        - 移除硬编码的禁止关键词检查
        - 原因：如果用户明确问到施工、预算等问题，应该正面回应
        - 引导偏好（偏向研究/分析而非工程落地）应在 prompt 层面实现
        """
        pass  # 不再执行硬限制验证


@dataclass
class ValidationCheck:
    """验证检查项"""

    name: str  # 检查项名称
    status: Literal["passed", "warning", "failed"]  # 检查状态
    message: str  # 检查消息
    details: str = ""  # 详细信息


@dataclass
class ValidationReport:
    """验证报告"""

    overall_status: Literal["passed", "warning", "failed"]  # 整体状态
    checks: List[ValidationCheck] = field(default_factory=list)  # 检查项列表
    timestamp: str = ""  # 验证时间戳


@dataclass
class OutputFramework:
    """输出结果框架 (v3.0 - 增强验证)"""

    core_objective: str  # 核心目标（一句话）
    deliverable_type: str  # 最终交付物类型
    blocks: List[OutputBlock] = field(default_factory=list)  # 2-7个板块
    quality_standards: List[str] = field(default_factory=list)
    validation_report: ValidationReport | None = None  # 验证报告

    def __post_init__(self):
        """验证输出框架"""
        # v7.510: 扩展板块数量上限从 7 到 12，支持更丰富的框架
        if not 1 <= len(self.blocks) <= 12:
            raise ValueError(f"Must have 1-12 blocks, got {len(self.blocks)}")


@dataclass
class DeepAnalysisResult:
    """Step 1 深度分析结果 (v3.0)"""

    understanding: Understanding  # 我的理解
    output_framework: OutputFramework  # 输出结果框架
    search_direction_hints: str  # 搜索方向提示
    validation_report: ValidationReport  # 完整验证报告
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Step 1.5: 搜索方向相关数据结构（中间层）
# ============================================================================


@dataclass
class SearchDirection:
    """搜索方向 - Step 1.5 中间层（介于板块和查询之间）"""

    id: str  # 如 "direction_1_1"
    block_id: str  # 服务的板块ID

    # 核心主题（单一焦点）
    core_theme: str  # 如 "Audrey Hepburn经典作品的色彩与设计语言分析"

    # 搜索范围说明
    search_scope: str  # 如 "提取电影服装、珠宝设计中的配色原则和设计元素"

    # 预期信息类型
    expected_info_types: List[str] = field(default_factory=list)  # 如 ["案例分析", "设计原则", "配色方案"]

    # 关键搜索维度
    key_dimensions: List[str] = field(default_factory=list)  # 如 ["色彩体系", "材质搭配", "设计语言"]

    # 用户特征关键词（继承自block）
    user_characteristics: List[str] = field(default_factory=list)  # 如 ["38岁", "独立女性", "Audrey Hepburn"]

    # 预期生成的查询数量
    expected_query_count: int = 2  # 1-3个

    # 优先级（继承自block的重要性）
    priority: int = 1  # 1/2/3

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证搜索方向"""
        if not self.core_theme:
            raise ValueError(f"SearchDirection {self.id} must have a core_theme")
        if not self.search_scope:
            raise ValueError(f"SearchDirection {self.id} must have a search_scope")
        if not 1 <= self.expected_query_count <= 3:
            raise ValueError(f"expected_query_count must be 1-3, got {self.expected_query_count}")


# ============================================================================
# Step 2: 搜索任务分解相关数据结构
# ============================================================================


@dataclass
class SearchQuery:
    """搜索查询 (v2.0 - 增强方向关联)"""

    id: str  # 如 "query_1_1"
    query: str  # 具体查询内容
    serves_blocks: List[str]  # 服务的输出板块ID列表（向后兼容）
    expected_output: str  # 预期输出说明
    search_keywords: List[str]  # 搜索关键词
    success_criteria: str  # 成功标准
    priority: int  # 优先级 1/2/3
    dependencies: List[str] = field(default_factory=list)  # 依赖的查询ID
    can_parallel_with: List[str] = field(default_factory=list)  # 可并行的查询ID
    status: str = "pending"  # pending/searching/completed/failed

    # v2.0 新增：方向关联
    direction_id: str | None = None  # 所属的搜索方向ID


@dataclass
class ExecutionStrategy:
    """搜索执行策略"""

    priority_1_queries: List[str] = field(default_factory=list)  # 第一优先级查询ID
    priority_2_queries: List[str] = field(default_factory=list)  # 第二优先级查询ID
    priority_3_queries: List[str] = field(default_factory=list)  # 第三优先级查询ID
    parallel_groups: List[List[str]] = field(default_factory=list)  # 可并行的查询组


@dataclass
class ExecutionAdvice:
    """执行建议"""

    overall_strategy: str  # 整体搜索策略说明
    key_success_factors: str  # 关键成功因素
    risk_alerts: str  # 风险提示


@dataclass
class SearchTaskList:
    """Step 2 搜索任务列表"""

    search_queries: List[SearchQuery] = field(default_factory=list)
    execution_strategy: ExecutionStrategy | None = None
    execution_advice: ExecutionAdvice | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Step 3: 搜索结果分析相关数据结构
# ============================================================================


class TriggerType(Enum):
    """补充查询触发类型"""

    NEW_DIRECTION = "new_direction"  # 发现新方向
    INSUFFICIENT_INFO = "insufficient_info"  # 信息不足
    CONTRADICTION = "contradiction"  # 发现矛盾
    RELATED_TOPIC = "related_topic"  # 发现关联主题
    USER_CHARACTERISTIC = "user_characteristic"  # 用户特征需要深化


class Priority(Enum):
    """优先级"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class QualityAssessment:
    """质量评估"""

    score: int  # 0-100分
    completeness: str  # high/medium/low
    relevance: str  # high/medium/low
    authority: str  # high/medium/low
    timeliness: str  # high/medium/low
    actionability: str  # high/medium/low
    issues: List[str] = field(default_factory=list)  # 主要问题


@dataclass
class Discovery:
    """关键发现"""

    type: TriggerType  # 发现类型
    description: str  # 发现描述
    importance: Priority  # 重要性


@dataclass
class SupplementaryQuery:
    """补充搜索查询"""

    id: str  # 如 "supp_query_1"
    query: str  # 具体查询内容
    reason: str  # 触发原因
    trigger_type: TriggerType  # 触发类型
    priority: Priority  # 优先级
    serves_blocks: List[str]  # 服务的输出板块ID列表
    expected_output: str  # 预期输出说明
    search_keywords: List[str]  # 搜索关键词
    success_criteria: str  # 成功标准
    parent_query_id: str | None = None  # 父查询ID
    status: str = "pending"  # pending/searching/completed/failed


@dataclass
class FrameworkAddition:
    """输出框架增补建议"""

    block_name: str  # 新板块名称
    reason: str  # 增补原因
    importance: Priority  # 重要性
    sub_items: List[str] = field(default_factory=list)  # 建议子项列表
    source: str = ""  # 信息来源


@dataclass
class SearchResultAnalysis:
    """Step 3 搜索结果分析"""

    current_query_id: str  # 当前查询ID
    quality_assessment: QualityAssessment  # 质量评估
    discoveries: List[Discovery] = field(default_factory=list)  # 关键发现
    supplementary_queries: List[SupplementaryQuery] = field(default_factory=list)  # 补充查询
    framework_additions: List[FrameworkAddition] = field(default_factory=list)  # 框架增补
    should_execute: bool = True  # 是否需要执行补充查询
    execution_order: List[str] = field(default_factory=list)  # 补充查询执行顺序
    expected_value: str = ""  # 预计补充查询能带来什么价值
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Step 4: 最终输出文档相关数据结构
# ============================================================================


@dataclass
class DocumentBlock:
    """文档板块"""

    id: str  # 板块ID
    name: str  # 板块名称
    content: str  # 板块内容（Markdown格式）
    word_count: int = 0  # 字数
    sub_items_count: int = 0  # 子项数量
    key_insights: List[str] = field(default_factory=list)  # 关键洞察
    source_references: List[int] = field(default_factory=list)  # 引用的来源编号


@dataclass
class SourceReference:
    """来源引用"""

    id: int  # 来源编号
    title: str  # 来源标题
    url: str  # 来源URL
    cited_count: int = 0  # 被引用次数


@dataclass
class InformationGap:
    """信息缺口"""

    topic: str  # 信息不足的主题
    reason: str  # 为什么重要
    suggestion: str  # 建议补充方式


@dataclass
class ImplementationAdvice:
    """实施建议"""

    how_to_apply: str  # 如何应用这些发现
    next_steps: str  # 下一步行动建议
    key_considerations: str  # 需要注意的关键点


@dataclass
class FrameworkAdjustments:
    """框架调整记录"""

    original_blocks: int  # 原始板块数
    final_blocks: int  # 最终板块数
    changes: List[str] = field(default_factory=list)  # 调整列表
    reason: str = ""  # 调整原因说明


@dataclass
class FinalOutputDocument:
    """Step 4 最终输出文档"""

    title: str  # 文档标题
    core_findings: str  # 核心发现与整体思路
    blocks: List[DocumentBlock] = field(default_factory=list)  # 文档板块
    key_takeaways: List[str] = field(default_factory=list)  # 核心要点总结
    implementation_advice: ImplementationAdvice | None = None  # 实施建议
    information_gaps: List[InformationGap] = field(default_factory=list)  # 信息补充说明
    sources: List[SourceReference] = field(default_factory=list)  # 参考来源
    framework_adjustments: FrameworkAdjustments | None = None  # 框架调整记录
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 搜索执行配置
# ============================================================================


@dataclass
class SearchExecutionConfig:
    """搜索执行配置"""

    max_supplementary_per_query: int = 3  # 每个查询最多3个补充
    max_total_queries_multiplier: float = 2.0  # 总查询数不超过原始的2倍
    auto_execute_priority: List[str] = field(default_factory=lambda: ["high", "medium"])  # 自动执行的优先级
    similarity_threshold: float = 0.8  # 相似度阈值（避免重复）
    max_search_duration_seconds: int = 300  # 最大搜索时长5分钟
    enable_dynamic_supplementary: bool = True  # 是否启用动态补充查询
    enable_framework_additions: bool = True  # 是否启用框架增补


# ============================================================================
# 4-Step Flow 完整状态
# ============================================================================


@dataclass
class FourStepFlowState:
    """4步骤流程完整状态 (v2.0 - 增加Step 1.5)"""

    # Step 1: 深度分析
    step1_deep_analysis: DeepAnalysisResult | None = None
    step1_completed: bool = False

    # Step 1.5: 搜索方向生成（新增）
    step1_5_search_directions: Dict[str, List[SearchDirection]] = field(default_factory=dict)  # block_id -> directions
    step1_5_completed: bool = False

    # Step 2: 搜索任务分解
    step2_task_list: SearchTaskList | None = None
    step2_user_approved: bool = False
    step2_completed: bool = False

    # Step 3: 搜索执行
    step3_executed_queries: List[str] = field(default_factory=list)  # 已执行的查询ID
    step3_search_results: Dict[str, Any] = field(default_factory=dict)  # 查询ID -> 搜索结果
    step3_supplementary_queries: List[SupplementaryQuery] = field(default_factory=list)  # 补充查询
    step3_framework_additions: List[FrameworkAddition] = field(default_factory=list)  # 框架增补
    step3_completed: bool = False

    # Step 4: 总结生成
    step4_final_document: FinalOutputDocument | None = None
    step4_completed: bool = False

    # 配置
    config: SearchExecutionConfig = field(default_factory=SearchExecutionConfig)

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 辅助函数
# ============================================================================


def create_search_query(
    query_id: str,
    query: str,
    serves_blocks: List[str],
    expected_output: str,
    search_keywords: List[str],
    success_criteria: str,
    priority: int = 1,
    dependencies: List[str] | None = None,
    can_parallel_with: List[str] | None = None,
) -> SearchQuery:
    """创建搜索查询对象"""
    return SearchQuery(
        id=query_id,
        query=query,
        serves_blocks=serves_blocks,
        expected_output=expected_output,
        search_keywords=search_keywords,
        success_criteria=success_criteria,
        priority=priority,
        dependencies=dependencies or [],
        can_parallel_with=can_parallel_with or [],
        status="pending",
    )


def create_supplementary_query(
    query_id: str,
    query: str,
    reason: str,
    trigger_type: TriggerType,
    priority: Priority,
    serves_blocks: List[str],
    expected_output: str,
    search_keywords: List[str],
    success_criteria: str,
    parent_query_id: str | None = None,
) -> SupplementaryQuery:
    """创建补充查询对象"""
    return SupplementaryQuery(
        id=query_id,
        query=query,
        reason=reason,
        trigger_type=trigger_type,
        priority=priority,
        serves_blocks=serves_blocks,
        expected_output=expected_output,
        search_keywords=search_keywords,
        success_criteria=success_criteria,
        parent_query_id=parent_query_id,
        status="pending",
    )


def create_framework_addition(
    block_name: str,
    reason: str,
    importance: Priority,
    sub_items: List[str],
    source: str = "",
) -> FrameworkAddition:
    """创建框架增补建议对象"""
    return FrameworkAddition(
        block_name=block_name,
        reason=reason,
        importance=importance,
        sub_items=sub_items,
        source=source,
    )
