"""
核心状态管理

定义项目分析系统的状态结构和管理逻辑
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Dict, List

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from typing_extensions import TypedDict


class AnalysisStage(Enum):
    """分析阶段枚举"""

    INIT = "init"
    REQUIREMENT_COLLECTION = "requirement_collection"
    REQUIREMENT_CONFIRMATION = "requirement_confirmation"
    STRATEGIC_ANALYSIS = "strategic_analysis"
    ROLE_SELECTION = "role_selection"  #  v2.2: 角色选择质量审核阶段
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


def merge_agent_results(left: Dict[str, Any] | None, right: Dict[str, Any] | None) -> Dict[str, Any]:
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


def merge_lists(left: List[Any] | None, right: List[Any] | None) -> List[Any]:
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
    except Exception:
        # 如果解析失败，默认取右侧值（最新更新）
        return right


def take_last(left: str | None, right: str | None) -> str | None:
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
    user_id: str | None
    created_at: Annotated[str, take_max_timestamp]
    updated_at: Annotated[str, take_max_timestamp]

    #  v7.107: 分析模式
    analysis_mode: str | None  # "normal"(深度思考) 或 "deep_thinking"(深度思考pro)，控制概念图生成数量

    # 用户输入和需求
    user_input: str
    structured_requirements: Dict[str, Any] | None
    feasibility_assessment: Dict[str, Any] | None  #  V1.5可行性分析结果（后台决策支持）
    project_type: str | None  #  项目类型（用于本体论注入）: "personal_residential" | "hybrid_residential_commercial" | "commercial_enterprise"

    # 分析策略和任务分派
    # 使用Annotated和reducer函数来处理并发更新
    strategic_analysis: Annotated[Dict[str, Any] | None, merge_agent_results]
    subagents: Annotated[Dict[str, str] | None, merge_agent_results]  # agent_id -> task_description
    # agents_to_execute 已移除（Fixed Mode 专用字段）
    # 使用Annotated和reducer函数来处理并发更新
    # 当多个智能体节点并行执行时,它们的结果会被自动合并
    agent_results: Annotated[Dict[str, Any] | None, merge_agent_results]
    agent_type: Any | None  # 当前执行的智能体类型(用于Send API并行执行)

    #  交付物ID管理（v7.108）- 支持概念图精准关联
    deliverable_metadata: Annotated[Dict[str, Dict[str, Any]] | None, merge_agent_results]
    """
    交付物元数据索引，键为交付物ID，值为元数据字典
    格式: {
        "deliverable_id": {
            "id": "2-1_1_143022_abc",
            "name": "空间功能分区方案",
            "description": "...",
            "keywords": ["现代", "简约"],
            "constraints": {...},
            "owner_role": "2-1",
            "created_at": "2025-12-29T14:30:22"
        }
    }
    通过 deliverable_id_generator_node 在 project_director 之后生成
    """

    deliverable_owner_map: Annotated[Dict[str, List[str]] | None, merge_agent_results]
    """
    角色到交付物ID的映射，用于快速查询某角色负责的交付物
    格式: {
        "2-1": ["2-1_1_143022_abc", "2-1_2_143023_def"],
        "3-1": ["3-1_1_143024_ghi"]
    }
    """

    # 专业分析结果
    # 注意：系统现在使用 Dynamic Mode，专家结果存储在 agent_results 字段中
    # 旧的 v2-v6 固定字段已移除

    # 结果聚合和输出
    aggregated_results: Dict[str, Any] | None
    final_report: str | None

    #  v7.64: 搜索引用集合（跨专家聚合）
    #  v7.164: 每个搜索结果现在包含唯一ID，格式: "{source_tool}_{hash}"
    search_references: Annotated[List[Dict[str, Any]] | None, merge_lists]
    """
    所有专家工具调用产生的搜索引用集合（v7.64+）
    用于在PDF报告末尾生成统一的参考文献章节
    每个元素为 SearchReference 的字典形式:
    {
        "id": "tavily_a1b2c3d4e5f6",  #  v7.164: 唯一标识符
        "source_tool": "tavily",
        "title": "...",
        "url": "...",
        "snippet": "...",
        ...
    }
    """

    # 交互和历史
    conversation_history: Annotated[List[BaseMessage], add_messages]
    human_feedback: Dict[str, Any] | None

    # 流程控制
    current_stage: str  # AnalysisStage
    detail: Annotated[str | None, take_last]  # 当前节点的详细描述（用于前端实时显示，支持并发更新）
    # 使用Annotated和reducer函数来处理并发更新
    active_agents: Annotated[List[str], merge_lists]  # 当前活跃的智能体
    completed_agents: Annotated[List[str], merge_lists]  # 已完成的智能体
    failed_agents: Annotated[List[str], merge_lists]  # 失败的智能体

    #  流程跳过标志
    skip_unified_review: bool | None  # 是否跳过统一审核
    skip_calibration: bool | None  #  是否跳过校准问卷（中等复杂度任务）
    requirements_confirmed: bool | None  # 需求是否已确认
    user_modification_processed: bool | None  # 用户修改是否已处理
    modification_confirmation_round: int | None  # 修改确认轮次

    #  问卷流程控制标志
    calibration_processed: bool | None  # 是否已处理问卷（避免重复显示）
    calibration_skipped: bool | None  # 是否跳过问卷（用户选择或系统判断）
    calibration_questionnaire: Dict[str, Any] | None  # 生成的校准问卷
    # LT-3: calibration_answers 已合并到 questionnaire_responses["answers"]（删除独立字段）
    questionnaire_responses: Dict[str, Any] | None  # 问卷回答（含 answers/entries/gap_filling_answers 等子键）
    questionnaire_summary: Dict[str, Any] | None  # 问卷精炼摘要（仅保留有效信息）
    interaction_history: Annotated[List[Dict[str, Any]], merge_lists]  # 交互历史记录
    post_completion_followup_completed: bool | None  # 报告完成后的追问是否已结束

    #  v7.80+ 渐进式问卷状态（修复关键字段丢失问题）
    progressive_questionnaire_step: int | None  # 当前步骤 (1, 2, 3)
    progressive_questionnaire_completed: bool | None  # 是否完成

    # Step 1: 任务梳理
    extracted_core_tasks: Annotated[List[Dict[str, Any]] | None, merge_lists]
    confirmed_core_tasks: Annotated[List[Dict[str, Any]] | None, merge_lists]
    core_task_summary: str | None
    confirmed_core_task: str | None  # 兼容旧字段
    extracted_core_task: str | None  # 兼容旧字段
    poetic_metadata: Dict[str, Any] | None
    special_scene_metadata: Dict[str, Any] | None
    step1_boundary_check: Any | None

    # Step 2: 信息补全 (Gap Filling)
    # LT-3: gap_filling_answers 已合并到 questionnaire_responses["gap_filling_answers"]（删除独立字段）
    task_completeness_analysis: Dict[str, Any] | None
    task_gap_filling_questionnaire: Dict[str, Any] | None

    # Step 3: 雷达图 (Radar)
    selected_dimensions: Annotated[
        List[Dict[str, Any]] | None, merge_lists
    ]  # 关键：questionnaire_summary 读取此字段 ( v7.151)
    selected_radar_dimensions: List[Dict[str, Any]] | None  # Step 2 输出
    radar_dimension_values: Dict[str, Any] | None
    radar_analysis_summary: Dict[str, Any] | None
    dimension_weights: Dict[str, Any] | None

    # 任务依赖关系 - 新增字段
    execution_batch: str | None  # 当前执行批次: "first" 或 "second" (旧字段，保留兼容)
    dependency_summary: Dict[str, Any] | None  # 第一批专家的完成情况摘要

    #  批次调度字段（2025-11-18）- 支持动态批次调度
    execution_batches: List[List[str]] | None  # 批次列表，每个批次是一个角色 ID 列表
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

    #  执行模式配置（v3.6）- 控制批次确认行为
    execution_mode: str | None  # 执行模式: "manual"（手动确认）, "automatic"（自动执行）, "preview"（显示后自动执行）

    completed_batches: Annotated[List[int], merge_lists]  # 已完成的批次编号列表
    """使用 reducer 支持并发更新"""

    # ─────────────────────────────────────────────────────────────────────────
    #  v8.2: 批次执行详情（前端动态步骤条）
    # ─────────────────────────────────────────────────────────────────────────
    batch_execution_detail: Dict[str, Any] | None
    """批次执行详情（前端展开用）
    结构：
    {
        "current_batch": 2,
        "total_batches": 5,
        "batch_agents": ["V5_场景专家_5-1", "V4_设计研究员_4-1"],
        "completed_agents": ["V5_场景专家_5-1"],
        "active_agent": "V4_设计研究员_4-1",
        "batch_progress": 0.5  # 0.0-1.0
    }
    """

    # 第二批策略审核 - 新增字段
    second_batch_approved: bool | None  # 第二批策略是否被批准
    second_batch_strategies: Dict[str, Any] | None  # 第二批专家的工作策略

    #  多轮审核控制 - 循环控制字段
    review_round: int  # 当前审核轮次（从0开始）
    review_history: Annotated[List[Dict[str, Any]], merge_lists]  # 审核历史记录
    best_result: Dict[str, Any] | None  # 历史最佳专家结果
    best_score: float  # 历史最佳评分
    review_feedback: Dict[str, Any] | None  # 审核反馈（传递给专家用于改进）

    # ─────────────────────────────────────────────────────────────────────
    #  v2.0 流程控制残留字段（仍在主路径使用，计划在下一主版本删除）
    #
    #    skip_second_review   → workflow/nodes/aggregation_nodes.py:471
    #                           interaction/nodes/manual_review.py:155,185
    #    迁移目标: 废弃后删除 manual_review → aggregation_nodes 的跳过逻辑
    # ─────────────────────────────────────────────────────────────────────
    skip_second_review: bool | None  # 整改后跳过第二次审核标记（仍在活跃主路径使用，暂不删除）

    #  v2.2 角色选择质量审核字段（2026-01-26）
    role_quality_review_result: Dict[str, Any] | None  # 角色选择质量审核结果（红蓝对抗）
    """
    角色选择质量审核结果，包含：
    {
        "critical_issues": [...],  # 关键问题（阻塞流程）
        "warnings": [...],         # 警告（不阻塞）
        "strengths": [...],        # 优势
        "overall_assessment": "...",  # 总体评估
        "red_review": {...},       # 红队原始审核
        "blue_review": {...}       # 蓝队原始审核
    }
    """
    role_quality_review_completed: bool | None  # 角色选择质量审核是否完成
    pending_user_question: Dict[str, Any] | None  # 待处理的用户问题（质量审核发现问题时）

    #  v7.280 前置质量控制字段（TaskGenerationGuard）
    task_guard_result: Dict[str, Any] | None  # TaskGenerationGuard 评估结果
    """
    前置质量控制评估结果，包含：
    {
        "risks": [...],           # 识别的风险点
        "auto_mitigations": [...], # 自动应用的修正措施
        "role_adjustments": {...}, # 角色优化调整
        "confidence_score": 75,    # 整体置信度
        "high_risk_roles": [...],  # 高风险角色列表
        "evaluation_summary": "..."  # 评估摘要
    }
    """
    auto_mitigations: Annotated[List[str] | None, merge_lists]  # 自动修正历史记录

    # 错误处理
    errors: List[Dict[str, Any]]
    retry_count: int

    #  需求分析显式失败状态（消除静默降级到 Step 1 的问题）
    requirements_analysis_status: str | None  # "failed" | None
    requirements_analysis_error: str | None  # 异常摘要，前端可通过状态接口读取

    #  输入拒绝字段（内容安全与领域过滤）
    rejection_reason: str | None  # 拒绝原因代码
    rejection_message: str | None  # 用户友好的拒绝提示消息
    domain_risk_flag: bool | None  # 领域风险标记
    domain_risk_details: Dict[str, Any] | None  # 领域风险详情

    # 统一输入验证字段（v7.3 - 合并 input_guard 和 domain_validator）
    initial_validation_passed: bool | None  # 初始验证是否通过
    domain_classification: Dict[str, Any] | None  # 领域分类结果
    safety_check_passed: bool | None  # 内容安全检测是否通过
    domain_confidence: float | None  # 初始领域置信度
    needs_secondary_validation: bool | None  # 是否需要二次验证
    # 移除: task_complexity, suggested_workflow, suggested_experts, estimated_duration
    # 移除: complexity_reasoning, complexity_confidence
    # 原因: 复杂度判断已整合到项目总监，由LLM自主决策
    secondary_validation_passed: bool | None  # 二次验证是否通过
    secondary_domain_confidence: float | None  # 二次验证置信度
    domain_drift_detected: bool | None  # 是否检测到领域漂移
    domain_user_confirmed: bool | None  # 用户是否手动确认领域
    confidence_delta: float | None  # 置信度变化量
    validated_confidence: float | None  # 最终验证置信度
    secondary_validation_skipped: bool | None  # 是否跳过二次验证
    secondary_validation_reason: str | None  # 跳过二次验证的原因
    trust_initial_judgment: bool | None  # 是否信任初始判断

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

    #  v7.155: 多模态视觉参考（用户上传的参考图）
    uploaded_visual_references: List[Dict[str, Any]] | None
    """
    用户上传的视觉参考图列表，每个元素包含：
    {
        "file_path": str,           # 文件路径（用于按需加载原始图片）
        "width": int,
        "height": int,
        "format": str,
        "vision_analysis": str,     # Vision API文本分析
        "structured_features": {    # 结构化视觉特征（轻量数据，直接存储）
            "dominant_colors": List[str],      # 主色调
            "style_keywords": List[str],       # 风格关键词
            "materials": List[str],            # 材质
            "spatial_layout": str,             # 空间布局描述
            "mood_atmosphere": str,            # 氛围描述
            "design_elements": List[str],      # 设计元素
        },
        "user_description": Optional[str],  # 用户追加描述
        "reference_type": str,      # 参考类型: "style" | "layout" | "color" | "general"
    }

    性能优化说明：
    - base64_data 不存储在 state 中，避免 Redis 内存压力
    - 通过 file_path 按需加载原始图片（概念图生成时）
    - structured_features 为轻量数据（约几KB），直接存储
    """

    visual_style_anchor: str | None
    """
    从上传图片提取的全局风格锚点
    用于确保全流程输出风格一致性
    格式: "Scandinavian minimalist, warm wood tones, natural lighting"
    """

    # ─────────────────────────────────────────────────────────────────────────
    # v8.1: 动机信号链（Step 0 修复 design_modes 死路 + Step 1 新增动机字段）
    # ─────────────────────────────────────────────────────────────────────────

    detected_design_modes: List[Dict[str, Any]] | None
    """
    设计模式检测结果（Step 0 修复：原字段从未写入，projection_dispatcher 的 when_modes 永远空转）
    由 requirements_nodes._requirements_analyst_node() 调用 detect_design_modes() 写入
    格式: [{"mode": "M1_concept_driven", "confidence": 0.7, "reason": "..."}, ...]
    """

    project_motivation: Dict[str, Any] | None
    """
    项目级动机识别结果（12 类：cultural/commercial/wellness 等）
    由 Phase1 LLM 推断，经 requirements_nodes 写入主 state
    格式: {
        "primary": "commercial",
        "secondary": "cultural",
        "scores": {"commercial": 0.75, "cultural": 0.50, ...},
        "confidence": 0.75,
        "reasoning": "用户提到竞标和坪效"
    }
    """

    designer_behavioral_motivation: Dict[str, Any] | None
    """
    设计师行为动机识别结果（D1-D6）
    回答"设计师为什么这样发问"，而非"项目要什么"
    由 Phase1 LLM 推断，经 requirements_nodes 写入主 state
    格式: {
        "primary": "D2_competitive_winning",
        "primary_label": "竞争制胜型",
        "confidence": 0.75,
        "scores": {"D1": 0.3, "D2": 0.75, "D3": 0.5, "D4": 0.2, "D5": 0.3, "D6": 0.4},
        "detection_signals": ["用户提到竞标", "对比性语气"],
        "secondary": "D3_breakthrough_innovation",
        "conflict_flag": false
    }
    """

    motivation_trace: Annotated[List[str] | None, merge_lists]
    """
    动机识别与传导追踪日志（调试用，支持并发 merge）
    例: ["[Phase1] D=D2_competitive_winning conf=0.75", "[ProjectDirector] 动机注入", "[Dispatcher] power+0.12"]
    """

    # ─────────────────────────────────────────────────────────────────────────
    # 半动态路由画像（Smart Nodes Self-Skip）
    # ─────────────────────────────────────────────────────────────────────────
    task_intent_profile: Dict[str, Any] | None
    """任务意图画像（如 project_design_task/strategy_thinking/mixed_project_strategy）。"""

    flow_route_name: str | None
    """命中的流程名，如 project_full_progressive_flow / strategy_light_flow。"""

    flow_route_decision: Dict[str, Any] | None
    """节点自跳步决策快照（布尔开关 + 命中原因）。"""

    flow_route_reason_codes: Annotated[List[str] | None, merge_lists]
    """路由原因码（可并发合并），用于可解释性和回放。"""

    routing_scores: Dict[str, float] | None
    """统一路由评分，如 info_completeness/ambiguity/risk/symbolic_density。"""

    active_steps: Annotated[List[str] | None, merge_lists]
    """当前会话激活步骤列表（前端动态步骤条来源）。"""

    motivation_routing_profile: Dict[str, Any] | None
    """动机聚合画像，供路由与内容偏置统一消费。"""

    # ── v8.0 投射调度字段 ──────────────────────────────────────────────────────
    active_projections: List[str] | None
    """激活的投射视角 ID 列表，由 output_intent_detection 写入，最多3个。"""

    meta_axis_scores: Dict[str, float] | None
    """五轴坐标评分 {identity, power, operation, emotion, civilization}，由 projection_dispatcher 计算。"""

    perspective_outputs: Dict[str, Any] | None
    """各视角投射版本原始输出，格式 {proj_id: {status, content, sections, ...}}。"""

    projection_reports: Dict[str, Any] | None
    """最终已完成的投射报告字典，由 result_aggregator 组装写入。"""

    output_intent_confirmed: bool | None
    """输出意图是否已确认。"""

    # 元数据
    metadata: Dict[str, Any]


class StateManager:
    """状态管理器"""

    @staticmethod
    def create_initial_state(
        user_input: str,
        session_id: str,
        user_id: str | None = None,
        analysis_mode: str | None = "normal",  #  v7.107: 分析模式
        uploaded_visual_references: List[Dict[str, Any]] | None = None,  #  v7.156: 多模态视觉参考
        visual_style_anchor: str | None = None,  #  v7.156: 全局风格锚点
    ) -> ProjectAnalysisState:
        """创建初始状态

        Args:
            user_input: 用户输入
            session_id: 会话ID
            user_id: 用户ID
            analysis_mode: 分析模式
            uploaded_visual_references: 用户上传的多模态视觉参考图片列表
            visual_style_anchor: 从视觉参考中提取的全局风格锚点描述
        """
        now = datetime.now().isoformat()

        return ProjectAnalysisState(
            # 基础信息
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
            #  v7.107: 分析模式
            analysis_mode=analysis_mode,
            # 用户输入
            user_input=user_input,
            structured_requirements=None,
            feasibility_assessment=None,  #  V1.5可行性分析结果初始化,
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
            # 交互历史
            conversation_history=[],
            human_feedback=None,
            #  问卷流程控制初始化
            skip_calibration=False,  #  是否跳过校准问卷
            calibration_processed=False,
            calibration_skipped=False,
            calibration_questionnaire=None,
            # LT-3: calibration_answers 已删除，合并到 questionnaire_responses["answers"]
            questionnaire_responses=None,
            questionnaire_summary=None,
            interaction_history=[],
            post_completion_followup_completed=False,
            #  v7.80+ 渐进式问卷初始化
            progressive_questionnaire_step=0,
            progressive_questionnaire_completed=False,
            extracted_core_tasks=None,
            confirmed_core_tasks=None,
            core_task_summary=None,
            confirmed_core_task=None,
            extracted_core_task=None,
            poetic_metadata=None,
            special_scene_metadata=None,
            step1_boundary_check=None,
            # LT-3: gap_filling_answers 已删除，合并到 questionnaire_responses["gap_filling_answers"]
            task_completeness_analysis=None,
            task_gap_filling_questionnaire=None,
            selected_dimensions=None,
            selected_radar_dimensions=None,
            radar_dimension_values=None,
            radar_analysis_summary=None,
            dimension_weights=None,
            #  追问对话历史初始化（v3.11新增）
            followup_history=[],
            followup_turn_count=0,
            #  v7.155→v7.156: 多模态视觉参考（从会话数据传入，不再硬编码为 None）
            uploaded_visual_references=uploaded_visual_references,
            visual_style_anchor=visual_style_anchor,
            # 半动态路由画像初始化
            task_intent_profile=None,
            flow_route_name="project_full_progressive_flow",
            flow_route_decision=None,
            flow_route_reason_codes=[],
            routing_scores=None,
            active_steps=["step1_core_task", "step2_info_gap", "step3_radar", "requirements_insight"],
            motivation_routing_profile=None,
            output_intent_confirmed=False,
            # v8.0 投射调度字段初始化
            active_projections=None,
            meta_axis_scores=None,
            perspective_outputs=None,
            projection_reports=None,
            # 流程控制
            current_stage=AnalysisStage.INIT.value,
            active_agents=[],
            completed_agents=[],
            failed_agents=[],
            #  批次调度初始化（2025-11-18）
            execution_batches=None,  # 将由BatchScheduler计算
            current_batch=0,
            total_batches=0,
            completed_batches=[],
            batch_execution_detail=None,  #  v8.2: 批次执行详情
            #  多轮审核控制 - 初始化
            review_round=0,
            review_history=[],
            best_result=None,
            best_score=0.0,
            review_feedback=None,
            #  v2.0 流程控制 - 初始化
            skip_second_review=False,
            # 错误处理
            errors=[],
            retry_count=0,
            # 元数据
            metadata={},
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
        return {"current_stage": new_stage.value, "updated_at": datetime.now().isoformat()}

    @staticmethod
    def add_agent_result(state: ProjectAnalysisState, agent_type: AgentType, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        添加智能体分析结果

         已修复: 移除对已删除的V2-V6枚举值的引用
        现在使用agent_results字典存储所有智能体结果
        """
        update = {"updated_at": datetime.now().isoformat()}

        #  修复: 不再使用已删除的V2-V6枚举值
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
        state: ProjectAnalysisState, error_type: str, error_message: str, agent_type: AgentType | None = None
    ) -> Dict[str, Any]:
        """添加错误信息"""
        error_info = {
            "type": error_type,
            "message": error_message,
            "timestamp": datetime.now().isoformat(),
            "agent": agent_type.value if agent_type else None,
        }

        errors = state.get("errors", []).copy()
        errors.append(error_info)

        failed_agents = state.get("failed_agents", []).copy()
        if agent_type and agent_type.value not in failed_agents:
            failed_agents.append(agent_type.value)

        return {"errors": errors, "failed_agents": failed_agents, "updated_at": datetime.now().isoformat()}

    @staticmethod
    def is_analysis_complete(state: ProjectAnalysisState) -> bool:
        """
        检查分析是否完成

         已修复: 移除对已删除的V2-V6枚举值的引用
        现在基于动态分派的智能体列表判断完成状态
        """
        completed_agents = state.get("completed_agents", [])
        subagents = state.get("subagents", {})

        #  修复: 基于动态分派的智能体判断完成状态
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
            "current_stage": state.get("current_stage", AnalysisStage.INIT.value),
        }
