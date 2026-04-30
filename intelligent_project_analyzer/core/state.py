"""
核心状态管理

定义项目分析系统的状态结构和管理逻辑
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional

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


def replace_list(left: Optional[List[Any]], right: Optional[List[Any]]) -> List[Any]:
    """
    替换列表的reducer函数（最后写入者胜出）

    与 merge_lists 不同，此 reducer 不追加，而是完整替换。
    用于 confirmed_core_tasks / extracted_core_tasks 等"快照型"字段——
    每次写入都是完整列表，不应与旧值合并。

    ⚠️ v10.1 P0 修复: 之前使用 merge_lists 导致 LangGraph 重试 / gap 回流时
    任务可能重复累积。改用 replace_list 确保语义正确。

    Args:
        left: 左侧值(现有值)
        right: 右侧值(新值)

    Returns:
        right 非空时返回 right，否则保留 left
    """
    if right is None:
        return left or []
    return right


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

    # DSS: 设计师画像（前端传入，S1 注入上下文）
    designer_profile: Optional[Dict[str, Any]]

    #  v7.107: 分析模式
    analysis_mode: Optional[str]  # "normal"(深度思考) 或 "deep_thinking"(深度思考pro)，控制概念图生成数量

    # 用户输入和需求
    user_input: str
    structured_requirements: Optional[Dict[str, Any]]
    feasibility_assessment: Optional[Dict[str, Any]]  #  V1.5可行性分析结果（后台决策支持）
    project_type: Optional[
        str
    ]  #  项目类型（用于本体论注入）: "personal_residential" | "hybrid_residential_commercial" | "commercial_enterprise"

    #  阶段2统一分类出口（P0-轻量版，聚合5个分类系统的输出）
    detected_design_modes: Optional[List[Dict[str, Any]]]  # Mode Engine 检测结果（BUG2修复后同步至top-level）
    project_classification: Optional[Dict[str, Any]]
    """
    统一项目分类结果，由 _requirements_analyst_node 聚合各子分类器输出：
    {
        "project_type": str,            # 项目类型（来自 requirements_analyst）
        "primary_mode": str,            # 主设计模式 ID（来自 mode_detector）
        "secondary_modes": List[str],   # 次模式列表
        "mode_confidence": float,       # 主模式置信度
        "motivation_type": str,         # 设计动机类型（如可用）
        "detected_design_modes": list,  # 完整模式检测原始数据
    }
    所有下游组件应优先读取此字段，而非各自独立分类。
    """

    space_classification: Optional[Dict[str, Any]]

    # 分析策略和任务分派
    # 使用Annotated和reducer函数来处理并发更新
    strategic_analysis: Annotated[Optional[Dict[str, Any]], merge_agent_results]
    subagents: Annotated[Optional[Dict[str, str]], merge_agent_results]  # agent_id -> task_description
    # agents_to_execute 已移除（Fixed Mode 专用字段）
    # 使用Annotated和reducer函数来处理并发更新
    # 当多个智能体节点并行执行时,它们的结果会被自动合并
    agent_results: Annotated[Optional[Dict[str, Any]], merge_agent_results]
    agent_type: Optional[Any]  # 当前执行的智能体类型(用于Send API并行执行)

    #  交付物ID管理（v7.108）- 支持概念图精准关联
    deliverable_metadata: Annotated[Optional[Dict[str, Dict[str, Any]]], merge_agent_results]
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

    deliverable_owner_map: Annotated[Optional[Dict[str, List[str]]], merge_agent_results]
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

    # 🆕 v15.0: 交付物工作包 (DWP) — 桥接任务导向与角色导向
    deliverable_work_packages: Annotated[Optional[List[Dict[str, Any]]], replace_list]
    """
    交付物工作包列表（v15.0 DWP 架构）
    每个元素为 DeliverableWorkPackage 的字典形式:
    {
        "dwp_id": "DWP-001",
        "name": "品牌命名方案",
        "source_task_ids": ["CT-a1b2c3d4"],
        "owner_role_id": "3-1",
        "contributor_role_ids": ["4-1"],
        "depends_on": [],
        "success_criteria": [...],
        ...
    }
    由 project_director DWP 模式生成，供审批 UI 和执行层使用。
    """

    dwp_completion_map: Annotated[Optional[Dict[str, Any]], merge_agent_results]
    """
    DWP 完成度追踪映射（v15.0）
    格式: {
        "DWP-001": {
            "status": "completed",
            "deliverables": [...],
            "quality_score": 0.85
        }
    }
    由 result_aggregator 在聚合阶段构建。
    """

    # v10.0: DWP 覆盖率报告（原为隐式字段，现正式声明）
    dwp_coverage_report: Optional[Dict[str, Any]]
    """
    DWP 覆盖率验证报告（v10.0）
    格式: {
        "covered": bool,
        "coverage_rate": float,
        "covered_task_ids": [...],
        "uncovered_task_ids": [...],
        "details": str
    }
    由 project_director 在 DWP 构建后生成。
    """

    # 结果聚合和输出
    aggregated_results: Optional[Dict[str, Any]]
    final_report: Optional[Dict[str, Any]]  # 结构化报告字典（实际值来自 AnalysisResult.structured_data）
    pdf_path: Optional[str]  # 当前主字段（工作流与API完成判定读取）
    pdf_file_path: Optional[str]

    #  v9.1: 多维投射输出
    perspective_outputs: Optional[Dict[str, Any]]  # 各视角投射版本 {"design_professional": {...}, ...}
    meta_axis_scores: Optional[Dict[str, float]]  # 五轴元结构坐标 {"identity": 0.7, "power": 0.5, ...}
    active_projections: Optional[List[str]]  # 激活的投射视角ID列表
    detected_identity_modes: Optional[List[Dict[str, Any]]]  #  v10.x: 身份模式列表 [{id, label, spatial_need, trigger_scenes}]
    output_framework_signals: Optional[Dict[str, Any]]  #  v10.1: 通用输出框架信号 {scope, constraints, mandatory_dimensions, output_calibration, audience_needs, reasoning}
    output_intent_payload: Optional[Dict[str, Any]]  #  v10.2/v11.0已废弃，保留字段避免旧会话反序列化失败
    intent_changed: Optional[bool]  # 🆕 v11.0: 用户在 Step0 是否偏离 AI 推荐意图

    #  v7.64: 搜索引用集合（跨专家聚合）
    #  v7.164: 每个搜索结果现在包含唯一ID，格式: "{source_tool}_{hash}"
    search_references: Annotated[Optional[List[Dict[str, Any]]], merge_lists]
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
    human_feedback: Optional[Dict[str, Any]]

    # 流程控制
    current_stage: str  # AnalysisStage
    detail: Annotated[Optional[str], take_last]  # 当前节点的详细描述（用于前端实时显示，支持并发更新）
    # 使用Annotated和reducer函数来处理并发更新
    active_agents: Annotated[List[str], merge_lists]  # 当前活跃的智能体
    completed_agents: Annotated[List[str], merge_lists]  # 已完成的智能体
    failed_agents: Annotated[List[str], merge_lists]  # 失败的智能体

    #  流程跳过标志
    skip_unified_review: Optional[bool]  # 是否跳过统一审核
    skip_calibration: Optional[bool]  #  是否跳过校准问卷（中等复杂度任务）
    requirements_confirmed: Optional[bool]  # 需求是否已确认
    role_selection_approved: Optional[bool]  # 角色审核是否通过（统一审核通用）
    task_assignment_approved: Optional[bool]  # 任务分配审核是否通过（统一审核通用）
    unified_review_result: Optional[Dict[str, Any]]  # 统一审核结果摘要（通用）
    confirmed_persona_profile: Optional[Dict[str, Any]]  # [兼容保留] 人物审批通过后的画像快照
    persona_approval_status: Optional[str]  # [兼容保留] approved | rejected
    persona_change_log: Annotated[List[Dict[str, Any]], merge_lists]  # [兼容保留] 人物审批审计记录
    requirements_unified_review_status: Optional[str]  # approved | rejected
    requirements_unified_review_result: Optional[Dict[str, Any]]  # 需求侧统一审核结果
    requirements_unified_review_change_log: Annotated[List[Dict[str, Any]], merge_lists]  # 统一审核审计记录
    user_modification_processed: Optional[bool]  # 用户修改是否已处理
    modification_confirmation_round: Optional[int]  # 修改确认轮次

    #  问卷流程控制标志
    calibration_processed: Optional[bool]  # 是否已处理问卷（避免重复显示）
    calibration_skipped: Optional[bool]  # 是否跳过问卷（用户选择或系统判断）
    calibration_questionnaire: Optional[Dict[str, Any]]  # 生成的校准问卷
    calibration_answers: Optional[Dict[str, Any]]  # 问卷答案（兼容旧字段）
    questionnaire_responses: Optional[Dict[str, Any]]  # 问卷回答（包含答案和元数据）
    questionnaire_summary: Optional[Dict[str, Any]]  # 问卷精炼摘要（仅保留有效信息）
    interaction_history: Annotated[List[Dict[str, Any]], merge_lists]  # 交互历史记录
    post_completion_followup_completed: Optional[bool]  # 报告完成后的追问是否已结束

    #  v7.80+ 渐进式问卷状态（修复关键字段丢失问题）
    progressive_questionnaire_step: Optional[int]  # 当前步骤 (1, 2, 3)
    progressive_questionnaire_completed: Optional[bool]  # 是否完成

    # Step 1: 任务梳理
    # ⚠️ v10.1 P0: 改用 replace_list（快照型字段，每次写入是完整列表，不应追加合并）
    extracted_core_tasks: Annotated[Optional[List[Dict[str, Any]]], replace_list]
    confirmed_core_tasks: Annotated[Optional[List[Dict[str, Any]]], replace_list]
    core_task_summary: Optional[str]
    confirmed_core_task: Optional[str]  # 兼容旧字段
    extracted_core_task: Optional[str]  # 兼容旧字段
    poetic_metadata: Optional[Dict[str, Any]]
    special_scene_metadata: Optional[Dict[str, Any]]
    step1_boundary_check: Optional[Any]

    # 🆕 v13.0: 需求洞察复盘 — Step 1 基线快照 + 复盘对象
    step1_confirmed_tasks_snapshot: Annotated[Optional[List[Dict[str, Any]]], replace_list]  # Step 1 确认时的不可变基线
    task_calibration_review: Optional[Dict[str, Any]]  # 需求洞察复盘对象（增删优强 + 效果检验）

    info_status: Optional[str]                  # Phase1 输出的信息充足度: "sufficient" | "insufficient"

    # Step 2: 信息补全 (Gap Filling)
    gap_filling_answers: Optional[Dict[str, Any]]
    task_completeness_analysis: Optional[Dict[str, Any]]
    task_gap_filling_questionnaire: Optional[Dict[str, Any]]
    gap_filling_generation_source: Optional[str]
    gap_filling_error_code: Optional[str]

    # Step 3: 雷达图 (Radar)
    selected_dimensions: Annotated[
        Optional[List[Dict[str, Any]]], merge_lists
    ]  # 关键：questionnaire_summary 读取此字段 ( v7.151)
    selected_radar_dimensions: Optional[List[Dict[str, Any]]]  # Step 2 输出
    radar_dimension_values: Optional[Dict[str, Any]]
    radar_analysis_summary: Optional[Dict[str, Any]]
    dimension_weights: Optional[Dict[str, Any]]
    dimension_generation_method: Optional[str]  # v8.0: "project_specific" | "static"
    radar_generation_source: Optional[str]
    radar_error_code: Optional[str]

    # 🆕 v14.0: 雷达权重设计驱动化
    weight_interpretations: Optional[Dict[str, Any]]  # WeightSemanticTranslator 翻译结果
    weight_response_manifest: Optional[Dict[str, Any]]  # 全链路响应追溯清单

    # 任务依赖关系 - 新增字段
    execution_batch: Optional[str]  # 当前执行批次: "first" 或 "second" (旧字段，保留兼容)
    dependency_summary: Optional[Dict[str, Any]]  # 第一批专家的完成情况摘要

    #  批次调度字段（2025-11-18）- 支持动态批次调度
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

    #  执行模式配置（v3.6）- 控制批次确认行为
    execution_mode: Optional[str]  # 执行模式: "manual"（手动确认）, "automatic"（自动执行）, "preview"（显示后自动执行）

    completed_batches: Annotated[List[int], merge_lists]  # 已完成的批次编号列表
    """使用 reducer 支持并发更新"""

    # 第二批策略审核 - 新增字段
    second_batch_approved: Optional[bool]  # 第二批策略是否被批准
    second_batch_strategies: Optional[Dict[str, Any]]  # 第二批专家的工作策略

    #  多轮审核控制 - 循环控制字段
    review_round: int  # 当前审核轮次（从0开始）
    review_history: Annotated[List[Dict[str, Any]], merge_lists]  # 审核历史记录
    best_result: Optional[Dict[str, Any]]  # 历史最佳专家结果
    best_score: float  # 历史最佳评分
    review_feedback: Optional[Dict[str, Any]]  # 审核反馈（传递给专家用于改进）

    #  v2.0 递进式审核结果字段
    review_result: Optional[Dict[str, Any]]  # [DEPRECATED] 完整审核结果（红蓝评委甲方）- 已被role_quality_review_result替代
    final_ruling: Optional[str]  # [DEPRECATED] 最终裁定文档（甲方输出的可执行改进路线图）- 已废弃
    improvement_suggestions: Annotated[List[Dict[str, Any]], merge_lists]  # [DEPRECATED] 改进建议列表 - 已废弃
    skip_second_review: Optional[bool]  # [DEPRECATED] 整改后跳过第二次审核标记 - 已废弃

    #  v2.2 角色选择质量审核字段（2026-01-26）
    role_quality_review_result: Optional[Dict[str, Any]]  # 角色选择质量审核结果（红蓝对抗）
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
    role_quality_review_completed: Optional[bool]  # 角色选择质量审核是否完成
    pending_user_question: Optional[Dict[str, Any]]  # 待处理的用户问题（质量审核发现问题时）

    #  v7.280 前置质量控制字段（TaskGenerationGuard）
    task_guard_result: Optional[Dict[str, Any]]  # TaskGenerationGuard 评估结果
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
    auto_mitigations: Annotated[Optional[List[str]], merge_lists]  # 自动修正历史记录

    # 错误处理
    errors: List[Dict[str, Any]]
    retry_count: int

    #  输入拒绝字段（内容安全与领域过滤）
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

    #  v7.155: 多模态视觉参考（用户上传的参考图）
    uploaded_visual_references: Optional[List[Dict[str, Any]]]
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

    visual_style_anchor: Optional[str]
    """
    从上传图片提取的全局风格锚点
    用于确保全流程输出风格一致性
    格式: "Scandinavian minimalist, warm wood tones, natural lighting"
    """

    # 🆕 v12.0: 图片约束识别体系
    visual_constraints: Optional[Dict[str, Any]]
    """
    从约束源图片（平面图/现场照片等）提取的结构化约束。
    {
        "constraints_by_zone": {"整体": [...], "1F": [...], "厨房": [...]},
        "spatial_topologies": {"1F": {zones, fixed_elements, openings, ...}},
        "existing_conditions": {"厨房": {current_style, issues, improvable, ...}},
        "style_tendencies": {"prefer": [...], "avoid": [...]},
        "constraint_envelope": str  # 三段式约束信封文本
    }
    """

    extracted_spatial_zones: Optional[List[Dict[str, Any]]]
    """
    从用户描述中提取的空间区域列表。
    [{"id": "overall", "label": "整体", "source": "preset"}, ...]
    """

    # 🆕 v11.2: 用户在输出意图 Step1 主动填写的前置约束
    user_intent_constraints: Optional[List[Dict[str, Any]]]
    """
    用户在输出意图步骤主动输入的前置约束条件。
    [{"label": "风格偏好", "desc": "北欧简约风，避免繁复装饰"}, ...]
    """

    # 元数据
    metadata: Dict[str, Any]

    # ===========================================================================
    # v2.0 双态架构新增字段（2026-03-15）
    # 所有字段均为 Optional，不影响现有方案产出路径。
    # 旧字段（雷达图/DWP/专家结果等）完整保留，此处仅追加。
    # ===========================================================================

    # 顶层运行模式
    system_mode: Optional[str]  # "conversation" | "project"（SystemMode 枚举值）

    # 门禁产出
    gate_decision: Optional[Dict[str, Any]]  # GateDecision 序列化

    # 需求分析产出（冻结后只读）
    design_task_book: Optional[Dict[str, Any]]     # DesignTaskBook 序列化
    execution_blueprint: Optional[Dict[str, Any]]  # ExecutionBlueprint 序列化
    requirements_frozen: Optional[bool]            # S5 冻结标志

    # 实施执行产出
    delivery_bundle: Optional[Dict[str, Any]]  # DeliveryBundle 序列化

    # 增量派生
    is_delta_modification: Optional[bool]          # True → 走 Delta 不重走 S1-S5
    delta_router_state: Optional[Dict[str, Any]]   # DeltaRouter 当前状态
    impact_graph: Optional[Dict[str, Any]]         # ImpactGraph 最新快照
    parent_project_id: Optional[str]               # DerivedProject 时的父项目 ID

    # 对话态草稿对象
    conversation_drafts: Annotated[Optional[List[Dict[str, Any]]], merge_lists]
    """
    对话态草稿对象列表，每个元素为对应草稿对象的序列化 dict。
    支持 IntentSeed / ProblemFrameDraft / DirectionCandidatePack /
    ConflictPack / BoundaryDraft / ConsensusPack 等类型。
    draft_type 字段标识类型。
    """

    # 升级信号
    upgrade_signal: Optional[Dict[str, Any]]  # UpgradeSignal 序列化
    cognition_indicators: Optional[Dict[str, Any]]  # CognitionIndicators 快照

    # 交付后项目档案（注入对话态上下文）
    project_archive: Optional[Dict[str, Any]]  # ProjectArchive 序列化

    # ===========================================================================
    # 实时引导机制字段（2026-03-16）
    # ===========================================================================

    # 当前轮待下发的引导卡片（None = 本轮无引导卡）
    pending_guidance_card: Optional[Dict[str, Any]]  # GuidanceCard 序列化

    # 全局引导操作记录（GuidanceTrace 序列化列表，追加式写入）
    guidance_traces: Annotated[Optional[List[Dict[str, Any]]], merge_lists]

    # ===========================================================================
    # 高参协作协议 — S1 v1/v2/v3 快照 + 候选卡协作（2026-03-17）
    # 实现"系统先出牌，用户后校准"的 L2 协作层
    # ===========================================================================

    # S1 解构三版本快照
    s1_v1_snapshot: Optional[Dict[str, Any]]
    """S1 初次解构快照（S1InputDecomposeNode 产出，未经用户校准）"""

    s1_v2_snapshot: Optional[Dict[str, Any]]
    """S2 回填快照（含 Echo Card 用户覆盖，供 S3+ 消费）"""

    s1_v3_complete: Optional[bool]
    """缺口补全完成标志；True 后 S3 才允许推进"""

    # Echo Card（S1 输入归纳确认卡）
    echo_card: Optional[Dict[str, Any]]
    """当前 Echo Card 的 CandidateCard 序列化；用户校准后更新为 confirmed 状态"""

    # L2 协作层候选卡（当前批次，最多 7 张）
    candidate_cards: Optional[List[Dict[str, Any]]]
    """本阶段活跃的 CandidateCard 序列化列表（✅/❓/⚠️/🔒 状态实时可见）"""

    # 缺口补全轮次记录（append-only）
    gap_completion_rounds: Annotated[Optional[List[Dict[str, Any]]], merge_lists]
    """GapCompletionRound 序列化列表，每轮补全过程完整归档"""

    gap_completion_count: Optional[int]
    """已完成的补全轮次计数（用于 LangGraph 条件路由）"""


class StateManager:
    """状态管理器"""

    @staticmethod
    def create_initial_state(
        user_input: str,
        session_id: str,
        user_id: Optional[str] = None,
        analysis_mode: Optional[str] = "normal",  #  v7.107: 分析模式
        uploaded_visual_references: Optional[List[Dict[str, Any]]] = None,  #  v7.156: 多模态视觉参考
        visual_style_anchor: Optional[str] = None,  #  v7.156: 全局风格锚点
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
            pdf_path=None,
            pdf_file_path=None,
            # v9.1: 多维投射初始化
            perspective_outputs=None,
            meta_axis_scores=None,
            active_projections=None,
            # 交互历史
            conversation_history=[],
            human_feedback=None,
            #  问卷流程控制初始化
            skip_calibration=False,  #  是否跳过校准问卷
            role_selection_approved=None,
            task_assignment_approved=None,
            unified_review_result=None,
            confirmed_persona_profile=None,
            persona_approval_status=None,
            persona_change_log=[],
            requirements_unified_review_status=None,
            requirements_unified_review_result=None,
            requirements_unified_review_change_log=[],
            calibration_processed=False,
            calibration_skipped=False,
            calibration_questionnaire=None,
            calibration_answers=None,
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
            info_status=None,
            detected_design_modes=None,     #  阶段2: 统一分类出口初始化
            project_classification=None,    #  阶段2: 统一分类出口初始化
            space_classification=None,
            # 🆕 v15.0: DWP 架构初始化
            deliverable_work_packages=None,
            dwp_completion_map=None,
            gap_filling_answers=None,
            task_completeness_analysis=None,
            task_gap_filling_questionnaire=None,
            gap_filling_generation_source=None,
            gap_filling_error_code=None,
            selected_dimensions=None,
            selected_radar_dimensions=None,
            radar_dimension_values=None,
            radar_analysis_summary=None,
            dimension_weights=None,
            radar_generation_source=None,
            radar_error_code=None,
            #  追问对话历史初始化（v3.11新增）
            followup_history=[],
            followup_turn_count=0,
            #  v7.155→v7.156: 多模态视觉参考（从会话数据传入，不再硬编码为 None）
            uploaded_visual_references=uploaded_visual_references,
            visual_style_anchor=visual_style_anchor,
            # 🆕 v12.0: 图片约束识别体系
            visual_constraints=None,
            extracted_spatial_zones=None,
            # 🆕 v11.2: 输出意图前置约束
            user_intent_constraints=None,
            # 流程控制
            current_stage=AnalysisStage.INIT.value,
            active_agents=[],
            completed_agents=[],
            failed_agents=[],
            #  批次调度初始化（2025-11-18）
            execution_batches=[],  # 将由BatchScheduler计算（避免 None 触发下游 len(None)）
            current_batch=0,
            total_batches=0,
            completed_batches=[],
            #  多轮审核控制 - 初始化
            review_round=0,
            review_history=[],
            best_result=None,
            best_score=0.0,
            review_feedback=None,
            #  v2.0 递进式审核结果 - 初始化
            review_result=None,
            final_ruling=None,
            improvement_suggestions=[],
            skip_second_review=False,
            # 错误处理
            errors=[],
            retry_count=0,
            # 元数据
            metadata={},
            # 高参协作协议 — 候选卡协作系统（2026-03-17）
            s1_v1_snapshot=None,
            s1_v2_snapshot=None,
            s1_v3_complete=None,
            echo_card=None,
            candidate_cards=None,
            gap_completion_rounds=[],
            gap_completion_count=0,
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
        state: ProjectAnalysisState, error_type: str, error_message: str, agent_type: Optional[AgentType] = None
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
