"""
领域对象层 — 双态架构核心产物定义

Copilot 生成（2026-03-15）
本文件定义双态架构（对话态常驻底态 + 项目态 4 节点主链）中的
所有正式领域对象（Pydantic BaseModel）。

设计原则：
- 纯数据对象，无业务逻辑
- 全部可序列化为 dict，兼容 LangGraph state 字段存储
- 与现有 state.py 中的旧字段共存，不冲突
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------


class InteractionState(str, Enum):
    """当前交互态"""

    CONVERSATION = "conversation"
    PROJECT = "project"


class GateStatus(str, Enum):
    """门禁放行结论"""

    CONTINUE = "continue"                              # 进入项目态主链
    CONVERSATION = "conversation"                      # 路由到对话态
    CONDITIONAL_CONTINUE = "conditional_continue"      # 有条件继续
    REJECT = "reject"                                  # 拒绝
    NEED_MORE_PREREQUISITE = "need_more_prerequisite"  # 需要补前提


class DraftStatus(str, Enum):
    """草稿对象生命周期"""

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    UPGRADED = "upgraded"  # 已编译进项目态


class SystemMode(str, Enum):
    """系统顶层运行模式"""

    CONVERSATION = "conversation"
    PROJECT = "project"


# ---------------------------------------------------------------------------
# 项目态主链对象
# ---------------------------------------------------------------------------


class RawBriefPacket(BaseModel):
    """用户输入节点产出——原始 Brief 包"""

    raw_user_prompt: str
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    initial_context: Dict[str, Any] = Field(default_factory=dict)
    session_or_project_stub: Optional[str] = None
    # 升级编译时携带的草稿预填充信号
    prefill_from_drafts: Dict[str, Any] = Field(default_factory=dict)


class GapDiagnosis(BaseModel):
    """门禁诊断出的硬缺口（最多 3 条）"""

    gap_index: int
    description: str
    severity: Literal["blocker", "major", "minor"] = "major"


class ExtremeOption(BaseModel):
    """极端条件发散时的两条路径之一"""

    label: str          # "A 极省" / "B 极好"
    description: str
    trade_offs: List[str] = Field(default_factory=list)


class GateDecision(BaseModel):
    """门禁节点产出——放行结论"""

    status: GateStatus
    reason: str
    boundary_notes: List[str] = Field(default_factory=list)
    required_preconditions: List[str] = Field(default_factory=list)
    interaction_state: InteractionState = InteractionState.CONVERSATION
    # 首诊结果
    gap_diagnosis: List[GapDiagnosis] = Field(default_factory=list)
    extreme_options: List[ExtremeOption] = Field(default_factory=list)


class StrategyZone(BaseModel):
    """DesignTaskBook 中的战略分区（四区标注）"""

    frozen: List[str] = Field(default_factory=list)       # 冻结区
    expanded: List[str] = Field(default_factory=list)     # 展开区
    traced: List[str] = Field(default_factory=list)       # 留痕区
    escalated: List[str] = Field(default_factory=list)    # 上行区


class DesignTaskBook(BaseModel):
    """需求分析 S5 产出——设计任务书（冻结对象）"""

    project_intent: str
    core_proposition: str
    strategy_zones: StrategyZone = Field(default_factory=StrategyZone)
    boundaries_and_redlines: List[str] = Field(default_factory=list)
    risk_and_rationale: Dict[str, Any] = Field(default_factory=dict)
    frozen: bool = False  # True 后不可原址覆写


class DAGNode(BaseModel):
    """ExecutionBlueprint 交付物 DAG 中的单节点"""

    node_id: str
    name: str
    owner_role: str
    depends_on: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)


class ReviewGate(BaseModel):
    """执行蓝图中的审阅门"""

    gate_id: str
    after_node_id: str
    gate_type: Literal["quality", "redline", "human_confirm"] = "quality"
    description: str = ""


class ExecutionBlueprint(BaseModel):
    """需求分析 S5 产出——执行蓝图（冻结对象）"""

    deliverable_dag: List[DAGNode] = Field(default_factory=list)
    task_chain_skeleton: List[str] = Field(default_factory=list)
    expert_responsibility: Dict[str, List[str]] = Field(default_factory=dict)
    review_gates: List[ReviewGate] = Field(default_factory=list)
    dependency_and_reflow_rules: Dict[str, Any] = Field(default_factory=dict)
    budget_guard: Dict[str, int] = Field(default_factory=dict)  # skill -> max_calls
    frozen: bool = False


class DeliveryBundle(BaseModel):
    """实施执行节点产出——交付包"""

    final_deliverables: List[Dict[str, Any]] = Field(default_factory=list)
    stage_deliverables: List[Dict[str, Any]] = Field(default_factory=list)
    insight_records: List[Dict[str, Any]] = Field(default_factory=list)
    risk_summary: Dict[str, Any] = Field(default_factory=dict)
    version_lineage: List[str] = Field(default_factory=list)   # ["v1", "v1.1", "v1.2"]
    explanation_materials: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 增量派生对象
# ---------------------------------------------------------------------------


class DeltaDelivery(BaseModel):
    """局部修订产物（不触碰 S3/S4 战略层）"""

    delta_target: str               # 修改目标描述
    original_ref: str               # 引用的原交付物 ID
    modified_fields: List[str] = Field(default_factory=list)
    impact_scope: List[str] = Field(default_factory=list)
    delta_result: Dict[str, Any] = Field(default_factory=dict)


class DerivedProject(BaseModel):
    """改轴派生项目（触碰战略红线，开辟新项目态）"""

    parent_project_id: str
    inheritance_mode: Literal["full", "partial", "soft"] = "partial"
    diverge_point: str              # 从哪个决策点分叉
    new_brief_packet: Optional[RawBriefPacket] = None
    new_session_id: Optional[str] = None


class ImpactGraph(BaseModel):
    """字段变动时计算的影响图谱"""

    changed_field: str
    dependencies: List[str] = Field(default_factory=list)
    affected_zones: List[str] = Field(default_factory=list)
    redline_alerts: List[str] = Field(default_factory=list)
    requires_derived_project: bool = False


# ---------------------------------------------------------------------------
# 高参协作协议 — 候选卡状态机（2026-03-17）
# ---------------------------------------------------------------------------


class CardStatus(str, Enum):
    """候选卡生命周期状态（L2 协作层）"""

    DRAFT = "draft"          # 草稿卡：系统内部生成，未出示
    CANDIDATE = "candidate"  # 候选卡：已出示，等待用户响应
    CONFIRMED = "confirmed"  # 确认卡：用户已处理（confirm/edit/add）
    FROZEN = "frozen"        # 冻结对象：已编译入任务书
    REVERTED = "reverted"    # 回退卡：用户从冻结状态申请重开讨论


class CardAction(str, Enum):
    """用户对候选卡的 4 种标准动作"""

    CONFIRM = "confirm"  # ✅ 接受系统预填
    EDIT = "edit"        # ✏️ 原地修改字段
    ADD = "add"          # ➕ 追加补充内容
    DEFER = "defer"      # ⏸ 暂时跳过（标注"暂无结论"）


class CandidateField(BaseModel):
    """候选卡中的单个可编辑字段"""

    field_id: str
    key: str                                    # 字段名称（如"使用面积"）
    value: str                                  # 系统预填值
    source_ref: str = ""                        # 来源依据文本（"基于你说的 XXX…"）
    inferred: bool = True                       # True=系统推断；False=用户明确表述
    user_value: Optional[str] = None            # 用户编辑后的值（None=未修改）


class CandidateCard(BaseModel):
    """候选卡（L2 协作层核心单元）

    状态机流转：草稿卡 → 候选卡 → 确认卡 → 冻结对象 → 回退卡
    """

    card_id: str
    card_type: Literal["echo", "gap"] = "gap"  # echo=输入归纳确认；gap=缺口补全
    title: str
    summary: str                               # 向用户展示的卡片说明
    fields: List[CandidateField] = Field(default_factory=list)
    status: CardStatus = CardStatus.CANDIDATE
    action: Optional[str] = None              # 用户执行的最终动作（CardAction 值）
    source_turns: List[str] = Field(default_factory=list)  # 生成依据的对话轮次 ID
    created_at: str = ""
    responded_at: Optional[str] = None
    # Defer 时的备注（由系统追加"基于推迟字段 X 的默认假设"）
    defer_note: str = ""


class S1Snapshot(BaseModel):
    """S1 输入解构快照（支持 v1 / v2 / v3 三版本）"""

    version: Literal["v1", "v2", "v3"]
    dimension_slices: Dict[str, str] = Field(default_factory=dict)
    open_gaps: List[str] = Field(default_factory=list)
    prefill_hints: Dict[str, Any] = Field(default_factory=dict)
    snapshot_at: str = ""
    # v2+ 追加：用户通过 Echo Card 覆盖的字段值
    user_overrides: Dict[str, str] = Field(default_factory=dict)


class GapCompletionRound(BaseModel):
    """缺口补全单轮记录（gap_completion_node 维护）"""

    round_index: int
    gap_descriptions: List[str] = Field(default_factory=list)
    candidate_card_id: Optional[str] = None
    completed: bool = False
    completed_at: Optional[str] = None


# ---------------------------------------------------------------------------
# 对话态草稿对象
# ---------------------------------------------------------------------------


class DraftObjectMeta(BaseModel):
    """草稿对象元数据（所有草稿对象均携带）"""

    source: str                     # 产生该草稿的对话轮次标识
    user_confirmed: bool = False
    inferred: bool = False          # 是否包含 AI 推断内容
    open_questions: List[str] = Field(default_factory=list)
    upgrade_ready: bool = False     # 是否可升级为正式输入


class IntentSeed(BaseModel):
    """意图原点：捕捉最初的想法和方向"""

    content: str
    keywords: List[str] = Field(default_factory=list)
    meta: DraftObjectMeta = Field(default_factory=lambda: DraftObjectMeta(source=""))


class ProblemFrameDraft(BaseModel):
    """问题框架草稿：初步组织问题结构"""

    problem_statement: str
    sub_problems: List[str] = Field(default_factory=list)
    meta: DraftObjectMeta = Field(default_factory=lambda: DraftObjectMeta(source=""))


class DirectionCandidatePack(BaseModel):
    """方向候选包：可能的策略方向集合"""

    candidates: List[Dict[str, str]] = Field(default_factory=list)
    meta: DraftObjectMeta = Field(default_factory=lambda: DraftObjectMeta(source=""))


class ConflictPack(BaseModel):
    """关键冲突包：已识别的矛盾与张力"""

    conflicts: List[str] = Field(default_factory=list)
    meta: DraftObjectMeta = Field(default_factory=lambda: DraftObjectMeta(source=""))


class BoundaryDraft(BaseModel):
    """边界与红线草稿：初步约束条件"""

    hard_constraints: List[str] = Field(default_factory=list)
    soft_preferences: List[str] = Field(default_factory=list)
    meta: DraftObjectMeta = Field(default_factory=lambda: DraftObjectMeta(source=""))


class ConsensusPack(BaseModel):
    """阶段性共识包：对话中已达成的共识"""

    agreed_items: List[str] = Field(default_factory=list)
    pending_items: List[str] = Field(default_factory=list)
    meta: DraftObjectMeta = Field(default_factory=lambda: DraftObjectMeta(source=""))


# ---------------------------------------------------------------------------
# 升级信号
# ---------------------------------------------------------------------------


class CognitionIndicators(BaseModel):
    """三大认知指标（用于对话态升级判定）"""

    freeze_readiness: float = 0.0    # 冻结准备度 [0, 1]
    cognitive_debt: float = 0.0      # 认知债务 [0, 1]
    diverge_fatigue: float = 0.0     # 发散疲劳度 [0, 1]

    @property
    def should_trigger_upgrade(self) -> bool:
        """满足以下任一条件时建议升级（软提示，不强切）：
        - 多轮渐进路径：三项指标同时过阈
        - 直接完整简报路径：freeze_readiness 极高（用户一次性给出完整 brief）
        """
        # 渐进路径：多轮对话积累后升级
        gradual = (
            self.freeze_readiness >= 0.7
            and self.cognitive_debt >= 0.6
            and self.diverge_fatigue >= 0.6
        )
        # 直接简报路径：首条消息即为完整项目 brief（富集度极高）
        direct_brief = self.freeze_readiness >= 0.85
        return gradual or direct_brief


class UpgradeSignal(BaseModel):
    """升级软提示信号"""

    indicators: CognitionIndicators = Field(default_factory=CognitionIndicators)
    suggestion_text: str = ""
    triggered: bool = False


# ---------------------------------------------------------------------------
# 项目档案（交付后注入对话态上下文）
# ---------------------------------------------------------------------------


class ProjectArchive(BaseModel):
    """项目态交付完成后注入对话态的完整档案"""

    project_id: str
    session_id: str
    delivery_bundle: Optional[DeliveryBundle] = None
    design_task_book: Optional[DesignTaskBook] = None
    execution_blueprint: Optional[ExecutionBlueprint] = None
    version_lineage: List[str] = Field(default_factory=list)
    decision_records: List[Dict[str, Any]] = Field(default_factory=list)
    review_traces: List[Dict[str, Any]] = Field(default_factory=list)
    risk_summary: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 实时引导机制：引导卡片对象（2026-03-16）
# ---------------------------------------------------------------------------


class GuidanceCardType(str, Enum):
    """引导卡片类型"""
    MIRROR = "mirror"          # 归纳镜像：反射用户已说内容，请确认
    FORK = "fork"              # 分叉选择：提供 2-4 个方向供选择
    GAP = "gap"                # 缺口补充：发现信息空白，请填写
    HYPOTHESIS = "hypothesis"  # 设想确认：系统生成的假设，请验证


class GuidanceCardOption(BaseModel):
    """引导卡片单个选项"""

    id: str                                  # 选项唯一 ID（a / b / c / d）
    label: str                               # 简短标签（≤8字）
    description: str = ""                    # 选项详细说明（UI 中始终展示）
    consequence_hint: Optional[str] = None  # Fork 卡专用：选此项的后续影响提示
    recommended: bool = False                # 是否为推荐选项


class GuidanceCardPage(BaseModel):
    """引导卡片单页（多页模式，每页独立问题与选项）"""

    page_title: str = ""                     # 本页小标题（显示在问题上方，可选）
    prompt_text: str                         # 本页问题文本
    options: List[GuidanceCardOption] = Field(default_factory=list)
    allow_freetext: bool = False


class GuidanceCard(BaseModel):
    """实时引导卡片（随 AI 回复一同下发，不中断对话流）"""

    card_id: str                                     # 唯一 ID，格式 gc-{uuid8}
    card_type: GuidanceCardType
    title: str = ""                                  # 卡片总标题（显示在 Header）
    prompt_text: str                                 # 单页模式：问题；多页模式：摘要
    options: List[GuidanceCardOption] = Field(default_factory=list)  # 单页选项
    allow_freetext: bool = False                     # 单页自由输入开关
    pages: List[GuidanceCardPage] = Field(default_factory=list)       # 多页问题列表
    source_turns: List[str] = Field(default_factory=list)            # 触发的对话轮次 ID
    rationale: str = ""                              # 内部使用：LLM生成理由，不下发前端


class GuidanceTrace(BaseModel):
    """用户对引导卡片的操作记录"""

    trace_id: str
    card_id: str
    card_type: GuidanceCardType
    user_action: Literal["select", "skip", "rewrite", "supplement"]
    selected_option_id: Optional[str] = None   # 选择的选项 ID（action=select 时）
    freetext_input: Optional[str] = None       # 自由输入内容（action=rewrite/supplement）
    captured_signal: str = ""                  # 从用户动作中提取的有效信号
    promoted_to_draft_type: Optional[str] = None  # 沉淀到的草稿对象类型
    timestamp: str = ""


# ---------------------------------------------------------------------------
# 平面图对象链（Node4.3 阶段）— Phase 1 实现
# ---------------------------------------------------------------------------


class SPGZone(BaseModel):
    """SPG 分区最小表示（供 FloorPlanIR 编译使用）"""

    zone_id: str
    name: str
    function: str = ""
    approx_area_m2: Optional[float] = None
    privacy_level: Literal["public", "semi_public", "private", "service"] = "semi_public"
    required_adjacencies: List[str] = Field(default_factory=list)   # zone_id 列表
    forbidden_adjacencies: List[str] = Field(default_factory=list)
    orientation_preference: Optional[str] = None  # "south" / "north" / "natural_light" 等


class SPGFlow(BaseModel):
    """SPG 流线定义"""

    flow_id: str
    name: str
    flow_type: Literal["main_entry", "public", "service", "emergency", "private"] = "public"
    from_zone: str   # zone_id
    to_zone: str     # zone_id
    min_width_mm: Optional[int] = None


class SpatialProgramGraph(BaseModel):
    """空间程序图谱（Node3 冻结产物真相源）

    Planned — 本实现为 Phase 1 最小字段集；
    字段来源：sf/2026.3.22/B 架构/08-系统架构分层与核心对象关系专题.md §3.4
    """

    spg_id: str = ""
    space_type: str = ""                       # 如 "民宿" / "住宅" / "办公"
    user_roles: List[str] = Field(default_factory=list)
    functional_modules: List[str] = Field(default_factory=list)
    zones: List[SPGZone] = Field(default_factory=list)
    flows: List[SPGFlow] = Field(default_factory=list)
    privacy_gradient: List[str] = Field(default_factory=list)  # 公→私顺序的 zone_id 列表
    strategy_scopes: Dict[str, Any] = Field(default_factory=dict)
    version: str = "v1.0"
    source_refs: List[str] = Field(default_factory=list)
    frozen: bool = False


class CoreConstraint(BaseModel):
    """固定构件约束（不可移动的物理边界）"""

    element: str                                     # "承重墙" / "管井" / "结构柱"
    location_description: str = ""
    zone_id: Optional[str] = None
    removable: bool = False
    level: Literal["immutable", "baseline"] = "immutable"


class Opening(BaseModel):
    """门洞 / 窗洞 / 开口"""

    opening_id: str
    opening_type: Literal["door", "window", "passage", "curtain_wall"] = "door"
    zone_id: str
    facing_zone: Optional[str] = None  # 门洞朝向另一个 zone
    width_mm: Optional[int] = None
    sill_height_mm: Optional[int] = None   # 窗台高度（窗才有意义）
    is_fixed: bool = False


class CirculationPath(BaseModel):
    """流线路径对象"""

    path_id: str
    flow_id: str                          # 对应 SPGFlow.flow_id
    zone_sequence: List[str] = Field(default_factory=list)  # zone_id 有序列表
    min_width_mm: int = 1200             # 规范下限：主通道 ≥1200mm
    is_main: bool = False


class FloorPlanGeometryPrimitive(BaseModel):
    """平面图基本几何单元（墙线 / 矩形 / 多边形 / 轴网）"""

    prim_id: str
    prim_type: Literal["wall_line", "rect", "polygon", "grid_line"] = "rect"
    zone_id: str                         # 归属分区
    points: List[List[float]] = Field(default_factory=list)  # [[x,y], ...] 相对坐标（mm）
    label: str = ""                      # SVG 标签文本
    layer: str = "ZONE"                  # WALL / OPENING / CIRCULATION / ZONE / ANNOTATION


class FloorPlanIR(BaseModel):
    """平面图中间表示（Platform-Invariant Representation）

    Planned — Phase 1 实现。
    职责：作为 SPG → 图片/SVG/CAD/3D 生成链的唯一真相中间层，
         消除各表现格式相互漂移。

    创建节点：Node4 步骤 4.3（任务实施）
    消费节点：FloorPlanGeneratorService（→ PNG / SVG / DXF）
    治理规则：
      - 所有 spaces / 墙线 / 流线 必须绑定有效 zone_id
      - version 与上游 spg_version 绑定，SPG 升版时重新编译
      - 不允许在本层修正 SPG 上游结构；若发现冲突，交由调用方回退 Node3
    """

    ir_id: str = ""
    spg_version: str = "v1.0"                          # 锁定消费的 SPG 版本
    session_id: str = ""

    # --- 几何基础 ---
    boundary: List[List[float]] = Field(default_factory=list)    # 外轮廓 [[x,y],...] mm
    total_area_m2: Optional[float] = None
    orientation_north_deg: float = 0.0                           # 北向偏角（0 = 图向上为北）

    # --- 分区与约束 ---
    spaces: List[SPGZone] = Field(default_factory=list)          # 来自 SPG.zones
    core_constraints: List[CoreConstraint] = Field(default_factory=list)
    openings: List[Opening] = Field(default_factory=list)

    # --- 关系图 ---
    adjacency_matrix: Dict[str, List[str]] = Field(default_factory=dict)  # zone_id → [相邻 zone_id]
    access_graph: Dict[str, List[str]] = Field(default_factory=dict)       # zone_id → [可达 zone_id]
    circulation_paths: List[CirculationPath] = Field(default_factory=list)

    # --- 尺度约束 ---
    size_ranges: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    # zone_id → {"min_area_m2": x, "target_area_m2": y, "min_width_mm": z}

    # --- 几何原语（用于 SVG/DXF 编译） ---
    geometry_primitives: List[FloorPlanGeometryPrimitive] = Field(default_factory=list)

    # --- 风格约束（注入图像生成） ---
    style_keywords: List[str] = Field(default_factory=list)
    avoid_patterns: List[str] = Field(default_factory=list)

    # --- 治理字段 ---
    version: str = "v1.0"
    frozen: bool = False
    validation_errors: List[str] = Field(default_factory=list)   # ContractValidator 输出
    validation_warnings: List[str] = Field(default_factory=list)


class FloorPlanGenerationResult(BaseModel):
    """FloorPlanGeneratorService 的最终交付包"""

    session_id: str
    ir: FloorPlanIR
    png_data_url: Optional[str] = None    # Base64 PNG 供前端展示
    svg_content: Optional[str] = None     # SVG 矢量平面草图（内嵌 zone_id 属性）
    json_payload: Optional[Dict[str, Any]] = None  # 供系统回写 InitialDesignPack
    validation_passed: bool = True
    generation_notes: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 平面推演对象链（Plan Sandbox / Layout Variant Engine）— Phase 0 契约
# ---------------------------------------------------------------------------


class FloorPlanFactElement(BaseModel):
    """从真实图纸或人工校正中得到的空间事实。

    与 LayoutIR 的设计建议分离：这里记录“已知/疑似存在”的建筑事实，
    不承载方案生成的价值判断。
    """

    element_id: str
    element_type: Literal[
        "boundary",
        "structural_wall",
        "partition_wall",
        "column",
        "core",
        "shaft",
        "stair",
        "elevator",
        "entry",
        "window",
        "opening",
        "view_edge",
    ]
    geometry: List[List[float]] = Field(default_factory=list)  # 归一化坐标 [[x,y], ...]
    locked: bool = False
    confidence: float = 0.5
    source: Literal["compiled", "manual", "llm_hint", "imported"] = "compiled"
    notes: List[str] = Field(default_factory=list)


class FloorPlanFacts(BaseModel):
    """平面推演的结构底座。

    目标是尽快进入“可推演状态”，而不是等到 Reviewed FloorPlanIR 完整通过。
    """

    facts_id: str = ""
    session_id: str = ""
    source_floor_plan_ir_id: Optional[str] = None
    coordinate_space: Literal["normalized", "main_plan_box", "mm"] = "normalized"
    scale_status: Literal["missing", "estimated", "confirmed"] = "estimated"
    boundary: List[List[float]] = Field(default_factory=list)
    immutable_elements: List[FloorPlanFactElement] = Field(default_factory=list)
    flexible_elements: List[FloorPlanFactElement] = Field(default_factory=list)
    review_flags: List[str] = Field(default_factory=list)


class DesignConstraint(BaseModel):
    """布局推演约束图中的一条约束。"""

    constraint_id: str
    constraint_type: Literal[
        "hard_lock",
        "adjacency",
        "forbidden_adjacency",
        "area",
        "orientation",
        "circulation",
        "privacy",
        "view",
        "cost",
        "strategy_bias",
    ]
    target_ids: List[str] = Field(default_factory=list)
    value: Dict[str, Any] = Field(default_factory=dict)
    priority: Literal["hard", "high", "medium", "low"] = "medium"
    source: Literal["user", "spg", "floor_plan_facts", "platform_method", "dss", "knowledge_base"] = "spg"


class DesignConstraintGraph(BaseModel):
    """用户目标、SPG、建筑事实与平台经验的统一约束图。"""

    graph_id: str = ""
    session_id: str = ""
    spg_id: str = ""
    facts_id: str = ""
    constraints: List[DesignConstraint] = Field(default_factory=list)
    locked_zone_ids: List[str] = Field(default_factory=list)
    preferred_objectives: List[str] = Field(default_factory=list)


class DesignIntent(BaseModel):
    """多版本布局的策略意图。

    LLM 后续应优先生成这个对象，而不是直接输出几何。
    """

    intent_id: str
    title: str
    strategy: Literal[
        "conservative_low_change",
        "functional_efficiency",
        "experience_value",
        "privacy_order",
        "view_priority",
        "family_gathering",
        "cost_control",
        "custom",
    ] = "custom"
    primary_axis: str = ""
    spatial_priorities: List[str] = Field(default_factory=list)
    accepted_tradeoffs: List[str] = Field(default_factory=list)
    source_experts: List[str] = Field(default_factory=list)
    rationale: str = ""


class LayoutSpace(BaseModel):
    """LayoutIR 中的可推演空间块。"""

    space_id: str
    name: str
    function: str = ""
    x: float = 0.0
    y: float = 0.0
    w: float = 0.0
    h: float = 0.0
    area_target_m2: Optional[float] = None
    privacy_level: Literal["public", "semi_public", "private", "service"] = "semi_public"
    locked: bool = False
    adjacent_to: List[str] = Field(default_factory=list)
    design_notes: List[str] = Field(default_factory=list)


class LayoutScore(BaseModel):
    """布局方案评分。评分用于比较，不替代用户裁决。"""

    functional_efficiency: int = 0
    privacy_order: int = 0
    view_resource: int = 0
    renovation_cost: int = 0
    project_fit: int = 0
    user_preference_fit: int = 0


class LayoutIR(BaseModel):
    """平面推演方案表示。

    与 FloorPlanFacts 区分：这里是“系统建议的布局”，不是图纸事实。
    """

    layout_id: str
    session_id: str = ""
    based_on_facts_id: str = ""
    based_on_spg_version: str = "v1.0"
    design_intent_id: str = ""
    strategy: str = ""
    spaces: List[LayoutSpace] = Field(default_factory=list)
    circulation: Dict[str, List[str]] = Field(default_factory=dict)
    open_boundaries: List[List[str]] = Field(default_factory=list)
    closed_boundaries: List[List[str]] = Field(default_factory=list)
    score: LayoutScore = Field(default_factory=LayoutScore)
    risks: List[str] = Field(default_factory=list)
    explanation: str = ""


class LayoutVariant(BaseModel):
    """一次生成结果中的一个候选版本。"""

    variant_id: str
    name: str
    intent: DesignIntent
    layout: LayoutIR
    status: Literal["candidate", "selected", "rejected", "frozen"] = "candidate"
    comparison_summary: str = ""


class LayoutOperation(BaseModel):
    """用户自然语言指令解析后的操作原语。"""

    operation_id: str
    operation_type: Literal[
        "lock_space",
        "move_space",
        "resize_space",
        "swap_space",
        "merge_spaces",
        "split_space",
        "add_buffer",
        "reduce_corridor",
        "increase_privacy",
        "improve_view",
        "shorten_path",
        "separate_flow",
        "open_boundary",
        "close_boundary",
        "merge_strategy",
        "reduce_cost",
    ]
    target_ids: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: Literal["hard", "high", "medium", "low"] = "medium"
    raw_instruction: str = ""


class LayoutVersionNode(BaseModel):
    """版本图谱中的一个布局节点。"""

    version_id: str
    layout_id: str
    parent_version_ids: List[str] = Field(default_factory=list)
    status: Literal["candidate", "selected", "rejected", "frozen"] = "candidate"
    user_instruction: Optional[str] = None
    operations: List[LayoutOperation] = Field(default_factory=list)
    decision_trace: List[str] = Field(default_factory=list)


class LayoutVersionGraph(BaseModel):
    """平面推演的版本图谱与平台沉淀载体。"""

    graph_id: str = ""
    session_id: str = ""
    nodes: List[LayoutVersionNode] = Field(default_factory=list)
    selected_version_id: Optional[str] = None
    frozen_version_id: Optional[str] = None
    rejected_reasons: Dict[str, str] = Field(default_factory=dict)


class LayoutGenerationPackage(BaseModel):
    """多版本平面推演的一次生成包。"""

    package_id: str
    session_id: str = ""
    facts: FloorPlanFacts = Field(default_factory=FloorPlanFacts)
    constraint_graph: DesignConstraintGraph = Field(default_factory=DesignConstraintGraph)
    variants: List[LayoutVariant] = Field(default_factory=list)
    version_graph: LayoutVersionGraph = Field(default_factory=LayoutVersionGraph)
    generation_notes: List[str] = Field(default_factory=list)
