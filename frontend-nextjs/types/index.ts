// types/index.ts
// 定义所有前后端交互的数据类型

// 会话状态枚举
export type SessionStatus =
  | 'initializing' // 初始化中
  | 'running' // 运行中
  | 'waiting_for_input' // 等待用户输入（阶段 2）
  | 'waiting_for_interaction' // 兼容旧字段
  | 'completed' // 已完成
  | 'failed' // 运行失败
  | 'rejected' // 输入被拒绝
  | 'started' // 会话已创建
  | 'error'; // 兼容旧状态

// ==================== 🆕 v7.155: 多模态视觉参考类型 ====================

/** 结构化视觉特征 */
export interface StructuredVisualFeatures {
  dominant_colors: string[];      // 主色调
  style_keywords: string[];       // 风格关键词
  materials: string[];            // 材质
  spatial_layout: string;         // 空间布局描述
  mood_atmosphere: string;        // 氛围描述
  design_elements: string[];      // 设计元素
}

/** 视觉参考类型 */
export type VisualReferenceType = 'style' | 'layout' | 'color' | 'general';

// ==================== 🆕 v7.157: 文件分类标签系统 ====================

/** 图片参考类型（8种） */
export type ImageCategory =
  | 'color'       // 色彩参考
  | 'style'       // 风格参考
  | 'material'    // 材质参考
  | 'layout'      // 平面布局
  | 'environment' // 环境参考
  | 'mood'        // 格调参考
  | 'item'        // 单品参考
  | 'lighting';   // 光线参考

/** 文档类型（6种） */
export type DocumentCategory =
  | 'requirements'   // 需求文档
  | 'reference'      // 参考资料
  | 'specification'  // 技术规范
  | 'budget'         // 预算清单
  | 'contract'       // 合同协议
  | 'other';         // 其他

/** 上传文件元数据 */
export interface UploadedFileMetadata {
  file: File;
  id: string;                                         // 唯一标识
  categories: ImageCategory[] | DocumentCategory[];   // 选中的标签
  customDescription: string;                          // 自定义描述
  previewUrl?: string;                                // 图片预览URL
  isImage: boolean;                                   // 是否为图片
}

/** 分类配置项 */
export interface CategoryConfig {
  label: string;
  icon: string;
  color: string;
  description: string;
}

/** 视觉参考 */
export interface VisualReference {
  file_path: string;                              // 文件路径
  width: number;
  height: number;
  format: string;
  vision_analysis: string;                        // Vision API文本分析
  structured_features: StructuredVisualFeatures;  // 结构化视觉特征
  user_description?: string;                      // 用户追加描述
  reference_type: VisualReferenceType;            // 参考类型
}

// ==================== 启动分析请求/响应 ====================

// 启动分析请求
export interface StartAnalysisRequest {
  user_id: string;
  user_input: string;
  // 🆕 v7.158: 分析模式 - normal(普通思考) / search(搜索) / deep_thinking(深度思考)
  analysis_mode?: 'normal' | 'search' | 'deep_thinking';
}

// 启动分析响应
export interface StartAnalysisResponse {
  session_id: string;
  status: SessionStatus;
  message: string;
}

// 会话状态
export interface AnalysisStatus {
  session_id: string;
  status: SessionStatus;
  current_stage?: string;
  progress?: number;
  active_agents?: string[];
  error?: string;
  detail?: string;
  history?: Array<{node: string; detail: string; time: string}>;
  interrupt_data?: any;
  traceback?: string;
  rejection_reason?: string;  // 拒绝原因
  rejection_message?: string;  // 拒绝消息（详细说明）
  final_report?: string;
  // 🆕 v7.155: 多模态视觉参考
  visual_references?: VisualReference[];
  visual_style_anchor?: string;
}

// 🔥 v7.109: 会话列表项类型（增强状态枚举和错误字段）
export interface SessionListItem {
  session_id: string;
  status: 'running' | 'waiting_for_input' | 'completed' | 'failed' | 'rejected';  // 明确状态枚举
  mode: string;
  created_at: string;
  user_input: string;
  pinned?: boolean;
  // v7.107: 分析模式和进度
  analysis_mode?: 'normal' | 'deep_thinking';
  progress?: number;        // 0.0-1.0
  current_stage?: string;
  // v7.109: 错误字段（后端已返回，为未来功能预留）
  error?: string;
  rejection_message?: string;
  rejection_reason?: string;
}

// ==================== 🆕 v7.270: UCPPT搜索模式 - 解题思路类型 ====================

/** 解题步骤 - v7.290 增强为可执行搜索任务 */
export interface SolutionStep {
  step_id: string;           // S1, S2, ...
  action: string;            // 具体行动
  purpose: string;           // 目的
  expected_output: string;   // 预期产出
  // v7.290 新增搜索执行字段
  search_keywords?: string[];           // 搜索关键词（2-5个）
  expected_sources?: string[];          // 期望信息来源
  success_criteria?: string;            // 成功标准
  priority?: 'high' | 'medium' | 'low'; // 优先级
  task_type?: 'research' | 'analysis' | 'design' | 'output'; // 任务类型
}

/** MECE 覆盖校验 - v7.290 新增 */
export interface CoverageCheck {
  covered_points: string[];              // 已覆盖的信息点
  potentially_missing: string[];         // 可能遗漏的信息点
  user_entities: string[];               // 用户提到的实体
  entity_coverage: Record<string, string>; // 实体-步骤映射
}

/** 关键突破口 */
export interface BreakthroughPoint {
  point: string;             // 突破口要点
  why_key: string;           // 为什么关键
  how_to_leverage: string;   // 如何利用
}

/** 预期交付物 */
export interface ExpectedDeliverable {
  format: string;            // report/list/comparison/recommendation/plan
  sections: string[];        // 必须包含的章节
  key_elements: string[];    // 关键交付物
  quality_criteria: string[]; // 质量标准
}

/** 解题思路（Problem Solving Approach）- v7.290 增强 */
export interface ProblemSolvingApproach {
  task_type: string;                      // research/design/decision/exploration/verification
  task_type_description: string;          // 任务类型详细描述
  complexity_level: string;               // simple/moderate/complex/highly_complex
  required_expertise: string[];           // 所需专业知识（3-5个）
  solution_steps: SolutionStep[];         // 解题步骤（5-8步）
  breakthrough_points: BreakthroughPoint[]; // 关键突破口（1-3个）
  expected_deliverable: ExpectedDeliverable; // 预期产出形态
  original_requirement: string;           // 用户原始需求
  refined_requirement: string;            // 结构化需求
  confidence_score: number;               // 置信度 (0-1)
  alternative_approaches: string[];       // 备选路径
  plain_text?: string;                    // 纯文本格式（可选）
  // v7.290 新增 MECE 覆盖校验
  coverage_check?: CoverageCheck;         // 覆盖校验
}

/** Step2 上下文 */
export interface Step2Context {
  core_question: string;                  // 核心问题
  answer_goal: string;                    // 回答目标
  solution_steps_summary: string[];       // 解题步骤摘要
  breakthrough_tensions: string[];        // 关键张力
}

// ==================== 🆕 v7.280: 深度分析维度类型 ====================

/** L1 实体 - 品牌 */
export interface BrandEntity {
  name: string;                           // 品牌名称
  positioning: string;                    // 品牌定位
  product_lines?: string[];               // 产品线
  designers?: string[];                   // 知名设计师
  color_system?: string[];                // 品牌色系
  brand_story?: string;                   // 品牌故事
}

/** L1 实体 - 地点 */
export interface LocationEntity {
  name: string;                           // 地点名称
  type: string;                           // 类型（城市/区域/具体场所）
  climate?: string;                       // 气候特征
  altitude?: string;                      // 海拔
  local_materials?: string[];             // 当地材料
  cultural_notes?: string;                // 文化背景
}

/** L1 实体 - 人物 */
export interface PersonEntity {
  name: string;                           // 人物名称/角色
  role: string;                           // 角色定位
  age_range?: string;                     // 年龄段
  characteristics?: string[];             // 特征
  needs?: string[];                       // 需求
}

/** L1 实体 - 物品 */
export interface ItemEntity {
  name: string;                           // 物品名称
  category: string;                       // 类别
  specifications?: Record<string, string>; // 规格参数
  usage_context?: string;                 // 使用场景
}

/** L1 实体 - 事件 */
export interface EventEntity {
  name: string;                           // 事件名称
  type: string;                           // 事件类型
  timeline?: string;                      // 时间线
  participants?: string[];                // 参与者
  significance?: string;                  // 重要性
}

/** L1 实体 - 概念 */
export interface ConceptEntity {
  name: string;                           // 概念名称
  definition: string;                     // 定义
  related_concepts?: string[];            // 相关概念
  application?: string;                   // 应用场景
}

/** L1 事实层完整结构 */
export interface L1FactsLayer {
  brands: BrandEntity[];
  locations: LocationEntity[];
  persons: PersonEntity[];
  items: ItemEntity[];
  events: EventEntity[];
  concepts: ConceptEntity[];
}

/** L2 视角分析 */
export interface PerspectiveAnalysis {
  perspective_id: string;                 // 视角ID（如 aesthetic, functional）
  perspective_name: string;               // 视角名称
  weight: number;                         // 权重 (0-1)
  analysis: string;                       // 分析内容
  key_considerations: string[];           // 关键考量点
  recommendations: string[];              // 建议
}

/** L3 核心张力 */
export interface CoreTension {
  tension_statement: string;              // 张力陈述
  conflicting_goals: string[];            // 冲突目标
  resolution_strategy: string;            // 解决策略
  trade_offs?: string[];                  // 权衡点
}

/** L4 用户任务 */
export interface UserTask {
  jtbd_statement: string;                 // Jobs-to-be-Done 陈述
  functional_job: string;                 // 功能性任务
  emotional_job: string;                  // 情感性任务
  social_job: string;                     // 社会性任务
  success_criteria: string[];             // 成功标准
}

/** L5 锐度评估 */
export interface SharpnessAssessment {
  score: number;                          // 锐度分数 (0-10)
  specificity: string;                    // 具体性评价
  actionability: string;                  // 可操作性评价
  depth: string;                          // 深度评价
  improvement_suggestions: string[];      // 改进建议
}

/** 人性化维度 */
export interface HumanDimensions {
  emotion_map?: {
    primary_emotions: string[];           // 主要情绪
    emotional_triggers: string[];         // 情绪触发点
    emotional_goals: string[];            // 情绪目标
  };
  spiritual_pursuit?: {
    core_values: string[];                // 核心价值观
    meaning_sources: string[];            // 意义来源
    aspirations: string[];                // 精神追求
  };
  psychological_safety?: {
    comfort_factors: string[];            // 舒适因素
    anxiety_sources: string[];            // 焦虑来源
    safety_needs: string[];               // 安全需求
  };
  ritual_behaviors?: {
    daily_rituals: string[];              // 日常仪式
    significance: string;                 // 仪式意义
    design_implications: string[];        // 设计启示
  };
  memory_anchors?: {
    key_memories: string[];               // 关键记忆
    emotional_objects: string[];          // 情感物品
    nostalgic_elements: string[];         // 怀旧元素
  };
}

/** 深度分析完整结果 */
export interface DeepAnalysisResult {
  l1_facts: L1FactsLayer;                 // L1 事实层
  l2_perspectives: PerspectiveAnalysis[]; // L2 多视角分析
  l3_core_tension: CoreTension;           // L3 核心张力
  l4_user_task: UserTask;                 // L4 用户任务
  l5_sharpness: SharpnessAssessment;      // L5 锐度评估
  human_dimensions?: HumanDimensions;     // 人性化维度（可选）
  motivation_type?: string;               // 识别的动机类型
  motivation_confidence?: number;         // 动机识别置信度
  problem_solving_approach?: ProblemSolvingApproach; // 解题思路
}

// ==================== 结构化报告类型 ====================

/** 执行摘要 */
export interface ExecutiveSummary {
  project_overview: string;
  key_findings: string[];
  key_recommendations: string[];
  success_factors: string[];
}

/** 报告章节 */
export interface ReportSection {
  section_id: string;
  title: string;
  content: string;
  confidence: number;
}

/** 综合分析 */
export interface ComprehensiveAnalysis {
  cross_domain_insights: string[];
  integrated_recommendations: string[];
  risk_assessment: string[];
  implementation_roadmap: string[];
}

/** 结论 */
export interface Conclusions {
  project_analysis_summary: string;
  next_steps: string[];
  success_metrics: string[];
}

/** 审核反馈项 */
export interface ReviewFeedbackItem {
  issue_id: string;
  reviewer: string;
  issue_type: string;
  description: string;
  response: string;
  status: string;
  priority: string;
}

/** 审核反馈 */
export interface ReviewFeedback {
  red_team_challenges: ReviewFeedbackItem[];
  blue_team_validations: ReviewFeedbackItem[];
  judge_rulings: ReviewFeedbackItem[];
  client_decisions: ReviewFeedbackItem[];
  iteration_summary: string;
}

/** 审核轮次数据 */
export interface ReviewRoundData {
  round_number: number;
  red_score: number;
  blue_score: number;
  judge_score: number;
  issues_found: number;
  issues_resolved: number;
  timestamp: string;
}

/** 审核可视化 */
export interface ReviewVisualization {
  rounds: ReviewRoundData[];
  final_decision: string;
  total_rounds: number;
  improvement_rate: number;
}

/** 挑战项 */
export interface ChallengeItem {
  expert_id: string;
  expert_name: string;
  challenged_item: string;
  challenge_type: string;
  severity: 'must-fix' | 'should-fix';
  rationale: string;
  proposed_alternative: string;
  design_impact: string;
  decision: string;
}

/** 挑战检测结果 */
export interface ChallengeDetection {
  has_challenges: boolean;
  total_count: number;
  must_fix_count: number;
  should_fix_count: number;
  challenges: ChallengeItem[];
  handling_summary: string;
}

/** 🔥 Phase 1.4+ 新增：需求洞察区块（LLM综合） */
export interface InsightsSection {
  key_insights: string[];
  cross_domain_connections: string[];
  user_needs_interpretation: string;
}

/** 🆕 需求分析结果（需求分析师原始输出）
 *
 * 融合用户修改后的最终版本，包含11个核心字段：
 * 1. project_overview - 项目概览：项目的整体描述和背景
 * 2. core_objectives - 核心目标：项目的主要目标列表
 * 3. project_tasks - 项目任务：需要完成的具体任务
 * 4. narrative_characters - 叙事角色：项目中的人物角色描述
 * 5. physical_contexts - 物理环境：项目的物理场景和环境
 * 6. constraints_opportunities - 约束与机遇：项目的限制条件和发展机会
 * 7. emotional_landscape - 情绪地图：从入口到核心空间的情绪转化路径
 * 8. spiritual_aspirations - 精神追求：基于马斯洛需求层次的精神目标
 * 9. psychological_safety_needs - 心理安全需求：安全基地需求和恐惧对抗策略
 * 10. ritual_behaviors - 仪式行为：日常仪式感行为及其心理意义
 * 11. memory_anchors - 记忆锚点：承载情感记忆的物品和元素
 */
export interface RequirementsAnalysis {
  project_overview: string;
  core_objectives: string[];
  project_tasks: string[];
  narrative_characters: string[];
  physical_contexts: string[];
  constraints_opportunities: Record<string, any>;

  // 🆕 v7.141.5: 人性维度字段（情感洞察）
  emotional_landscape?: string;
  spiritual_aspirations?: string;
  psychological_safety_needs?: string;
  ritual_behaviors?: string;
  memory_anchors?: string;
}

/** 🔥 Phase 1.4+ 新增：推敲过程区块 */
export interface DeliberationProcess {
  inquiry_architecture: string;
  reasoning: string;
  role_selection: string[];
  strategic_approach: string;
}

/** 🔥 Phase 1.4+ 新增：单条建议（V2升级 - 五维度分类） */
export interface RecommendationItem {
  content: string;
  dimension: 'critical' | 'difficult' | 'overlooked' | 'risky' | 'ideal';
  reasoning: string;
  source_expert: string;
  estimated_effort?: string;
  dependencies: string[];
}

/** 🔥 Phase 1.4+ 新增：建议提醒区块（V2升级 - 五维度分类） */
export interface RecommendationsSection {
  recommendations: RecommendationItem[];
  summary: string;
}

/** 🔥 Phase 1.4+ 新增：执行元数据汇总 */
export interface ExecutionMetadata {
  total_experts: number;
  inquiry_architecture: string;
  analysis_duration?: string;
  total_tokens_used?: number;
  confidence_average?: number;
  review_rounds?: number;
  // 🆕 v7.4 新增字段
  total_batches?: number;
  complexity_level?: string;
  questionnaire_answered?: number;
  expert_distribution?: Record<string, number>;
  generated_at?: string;
}

/** 🔥 Phase 1.4+ 新增：核心答案区块（向后兼容版） */
export interface CoreAnswer {
  question: string;
  answer: string;
  deliverables: string[];
  timeline: string;
  budget_range: string;
  // 🆕 v7.0 字段（可选，用于多交付物支持）
  deliverable_answers?: DeliverableAnswer[];
  expert_support_chain?: ExpertSupportChain[];
}

/** 🆕 v7.0: 单个交付物的责任者答案 */
export interface DeliverableAnswer {
  deliverable_id: string;
  deliverable_name: string;
  deliverable_type?: string;
  owner_role: string;
  owner_answer: string;
  answer_summary?: string;
  supporters: string[];
  quality_score?: number | null;
}

/** 🆕 v7.0: 专家支撑链 */
export interface ExpertSupportChain {
  role_id: string;
  role_name: string;
  contribution_type: string;
  contribution_summary: string;
  related_deliverables: string[];
}

/** 🔥 Phase 1.4+ 新增：问卷回答项 */
export interface QuestionnaireResponseItem {
  question_id: string;
  question: string;
  answer: string;
  context: string;
}

/** 🔥 Phase 1.4+ 新增：问卷回答数据 */
export interface QuestionnaireResponsesData {
  responses: QuestionnaireResponseItem[];
  timestamp: string;
  notes?: string;
  analysis_insights?: string;
}

/** 🆕 v7.147: 需求洞察 - 重构需求文档类型 */
/** 🔧 v7.151: 升级为需求洞察，新增深度分析字段 */
export interface RestructuredRequirements {
  metadata: {
    document_version: string;
    generated_at: string;
    generation_method: string;
    data_sources: string[];
    llm_enhanced?: boolean;  // 🆕 v7.151
  };
  project_objectives: {
    primary_goal: string;
    primary_goal_source: string;
    secondary_goals: string[];
    success_criteria: string[];
    // 🆕 v7.151: 用户表达 vs AI理解对比
    understanding_comparison?: {
      user_expression: string;
      ai_understanding: string;
      alignment_note: string;
    };
  };
  constraints: {
    budget?: {
      total: string;
      breakdown?: Record<string, string>;
      flexibility?: string;
    };
    timeline?: {
      duration: string;
      milestones?: string[];
      urgency?: string;
    };
    space?: {
      area: string;
      layout?: string;
      limitations?: string[];
    };
  };
  design_priorities: Array<{
    dimension_id: string;
    label: string;
    weight: number;
    tendency: string;
    rationale: string;
  }>;
  core_tension: {
    tension_statement: string;
    conflicting_goals: string[];
    resolution_strategy: string;
    // 🆕 v7.151: LLM生成的个性化策略
    strategic_options?: Array<{
      stance: string;
      approach: string;
      risk: string;
      benefit?: string;
    }>;
  };
  special_requirements: string[];
  identified_risks: Array<{
    risk_id: string;
    description?: string;  // 可选，兼容两种格式
    risk?: string;         // 可选，兼容两种格式
    severity: 'high' | 'medium' | 'low';
    mitigation: string;
  }>;
  insight_summary: {
    L1_key_facts: string[];
    L2_user_profile: Record<string, any>;
    L3_core_tension: string;
    L4_project_task_jtbd: string;
    L5_sharpness_score: number;
    L5_sharpness_note: string;
    _status?: 'pending' | 'completed' | 'failed';  // 🔧 v7.152: 状态标记
  };
  deliverable_expectations: string[];
  executive_summary: {
    one_sentence: string;
    what: string;
    why: string;
    how: string;
    constraints_summary: string;
  };
  // 🆕 v7.151: 深度洞察字段
  project_essence?: string;
  implicit_requirements?: Array<{
    requirement: string;
    evidence: string;
    priority: 'high' | 'medium' | 'low';
  }>;
  key_conflicts?: Array<{
    conflict: string;
    sides: string[];
    recommended_approach: string;
    trade_off: string;
  }>;
}

/** 结构化报告 */
export interface StructuredReport {
  inquiry_architecture: string;

  // 🔥 Phase 1.4+ 新增字段
  insights?: InsightsSection | null;
  requirements_analysis?: RequirementsAnalysis | null;  // 🆕 需求分析结果
  core_answer?: CoreAnswer | null;
  deliberation_process?: DeliberationProcess | null;
  recommendations?: RecommendationsSection | null;
  questionnaire_responses?: QuestionnaireResponsesData | null;
  execution_metadata?: ExecutionMetadata | null;

  // 🆕 v7.120: 搜索引用功能
  search_references?: SearchReference[];

  // 🔥 v7.39 概念图字段
  generated_images?: string[];  // 普通模式 - 集中式图片URL列表
  generated_images_by_expert?: Record<string, {
    expert_name: string;
    images: ExpertGeneratedImage[];
  }>;  // 深度思考模式 - 按专家分组的图片

  // 原有字段
  executive_summary: ExecutiveSummary;
  sections: ReportSection[];
  comprehensive_analysis: ComprehensiveAnalysis;
  conclusions: Conclusions;
  expert_reports: Record<string, string>;
  review_feedback?: ReviewFeedback | null;
  review_visualization?: ReviewVisualization | null;
  challenge_detection?: ChallengeDetection | null;
}

// 报告数据
export interface AnalysisReport {
  session_id: string;
  report_text: string;
  report_pdf_path?: string;
  created_at: string;
  user_input?: string;  // 用户原始输入
  suggestions?: string[];
  structured_report?: StructuredReport | null;
  analysis_mode?: 'normal' | 'deep_thinking';  // 🆕 分析模式
}

// ==================== 🔥 v7.39 概念图功能类型 ====================

/** 图片宽高比选项 */
export type AspectRatio = '16:9' | '1:1' | '9:16' | '4:3' | '21:9';

/** 图片风格类型 */
export type StyleType = 'interior' | 'architecture' | 'product' | 'branding' | 'conceptual';

/** 专家生成的概念图 */
export interface ExpertGeneratedImage {
  id?: string;                   // v7.109: 唯一标识符（8位UUID，可选）
  image_url?: string;            // v7.109: 完整HTTP URL（可选）
  prompt?: string;               // v7.109: 生成提示词（可选）
  prompt_used?: string;          // v7.109: 实际使用的提示词（可选）
  aspect_ratio?: AspectRatio;    // v7.109: 图片宽高比（可选）
  style_type?: StyleType;        // v7.109: 视觉风格（可选）
  created_at?: string;           // v7.109: ISO时间戳（可选）
  expert_name?: string;          // 生成此图的专家名称（可选）
}

/** 图片对话单轮记录 */
export interface ImageChatTurn {
  turn_id?: string;                           // v7.109: 轮次ID（可选）
  type?: 'user' | 'assistant';                // v7.109: 消息类型（可选）
  timestamp?: string;                          // v7.109: 时间戳（可选）
  user_prompt?: string;                       // 用户提示词（可选）
  prompt?: string;                            // v7.109: 提示词别名（兼容）
  generated_image?: ExpertGeneratedImage;     // 生成的图片（可选）
  image?: ExpertGeneratedImage;               // v7.109: 图片别名（兼容）
  reference_image?: string;                   // 参考图片URL（可选）
  reference_image_url?: string;               // v7.109: 参考图片URL别名（兼容）
  aspect_ratio?: AspectRatio;                 // 此轮使用的宽高比
  style_type?: StyleType;                     // 此轮使用的风格
  isLoading?: boolean;                        // v7.109: 加载状态（前端UI用）
  error?: string;                             // v7.109: 错误信息（前端UI用）
}

/** 图片对话历史 */
export interface ImageChatHistory {
  turns: ImageChatTurn[];   // 对话轮次列表
  session_id: string;       // 关联的分析会话ID
  expert_name: string;      // 专家名称
}

/** 图片生成参数 */
export interface ImageGenerationParams {
  prompt: string;                     // 生成提示词
  aspect_ratio?: AspectRatio;         // 宽高比
  style_type?: StyleType;             // 风格类型
  reference_image_url?: string;       // 参考图片URL
}

/** 建议的提示词 */
export interface SuggestedPrompt {
  text: string;      // 提示词文本
  category: string;  // 分类（如：空间布局、色彩方案）
}

/** 图片重新生成请求 */
export interface RegenerateImageRequest {
  expert_name: string;              // 专家名称
  prompt: string;                   // 新的生成提示词
  reference_image_url?: string;     // 参考图片URL（可选）
  aspect_ratio?: AspectRatio;       // 宽高比（默认16:9）
  style_type?: StyleType;           // 风格类型（默认interior）
  save_as_copy?: boolean;           // 是否保存为副本（默认false=覆盖）
}

// ==================== 🔥 v7.108.2 追问图片功能类型 ====================

/** 追问对话附件（图片） */
export interface FollowupAttachment {
  type: 'image';
  original_filename: string;
  stored_filename?: string;
  thumbnail_filename?: string;
  url: string;
  thumbnail_url: string;
  width: number;
  height: number;
  format: string;
  file_size_bytes?: number;
  vision_analysis?: string;
  upload_timestamp?: string;
}

/** 追问对话单轮 */
export interface FollowupTurn {
  turn_id: number;
  question: string;
  answer: string;
  intent?: string;
  referenced_sections?: string[];
  attachments?: FollowupAttachment[];
  timestamp: string;
}

/** 追问历史响应 */
export interface FollowupHistoryResponse {
  session_id: string;
  total_turns: number;
  history: FollowupTurn[];
}

// ==================== 🔥 v7.120 搜索引用功能类型 ====================

/** 搜索引用 - 专家使用的搜索工具结果 */
export interface SearchReference {
  id: string;                         // 🆕 v7.164: 唯一标识符，格式: "{source_tool}_{hash}"
  source_tool: 'tavily' | 'bocha' | 'arxiv' | 'ragflow' | 'milvus' | 'serper';  // 搜索工具来源
  title: string;                      // 结果标题
  url?: string;                       // 结果URL（可选）
  snippet?: string;                   // 摘要（可选）
  score?: number;                     // 相关性得分（可选）
  relevance_score?: number;           // 相关性分数（可选，兼容）
  quality_score?: number;             // 质量分数（可选）
  query?: string;                     // 搜索查询（可选）
  expert_name?: string;               // 使用该引用的专家（可选）
}

// ==================== 🆕 v7.141.5 情感洞察专家输出类型 ====================

/** V7情感洞察专家输出 - 人性维度分析 */
export interface EmotionalInsightExpertOutput {
  output_mode: 'targeted' | 'comprehensive';
  user_question_focus: string;
  confidence: number;
  design_rationale: string;

  // Comprehensive模式字段
  emotional_landscape?: {
    entry_emotion: string;
    transition_path: string;
    core_emotion: string;
    design_triggers: string[];
  };
  spiritual_aspirations?: string;
  psychological_safety_needs?: {
    fear_source: string;
    safety_strategy: string;
    refuge_space: string;
  };
  ritual_behaviors?: Array<{
    behavior_name: string;
    psychological_meaning: string;
    space_requirements: string;
    trigger_conditions?: string;
  }>;
  memory_anchors?: Array<{
    item_name: string;
    emotional_value: string;
    memory_type: string;
    spatial_treatment: string;
  }>;

  // Targeted模式字段
  targeted_analysis?: Record<string, any>;

  // v3.5协议字段
  expert_handoff_response?: Record<string, any>;
  challenge_flags?: Array<{
    flag: string;
    reason: string;
  }>;
}

// ==================== v7.300: 4步工作流类型定义 ====================

/** v7.300: 可编辑的搜索步骤 */
export interface EditableSearchStep {
  id: string;                    // 步骤ID (S1, S2, ...)
  step_number: number;           // 显示顺序
  task_description: string;      // 任务描述
  expected_outcome: string;      // 期望结果
  search_keywords: string[];     // 搜索关键词
  priority: 'high' | 'medium' | 'low';  // 优先级
  can_parallel: boolean;         // 是否可并行
  status: 'pending' | 'searching' | 'complete';  // 状态
  completion_score: number;      // 完成度

  // 执行追踪
  executed_queries?: string[];
  round_count?: number;

  // 用户编辑标记
  is_user_added?: boolean;
  is_user_modified?: boolean;

  // UI 状态
  isEditing?: boolean;
  isNew?: boolean;
}

/** v7.300: 第1步分析输出 - 复用 L0-L5 框架 */
export interface Step1AnalysisOutput {
  // L0: 用户画像
  l0_user_profile: {
    identity: string;
    occupation: string;
    implicit_needs: string[];
    decision_stage: string;
  };

  // L1: 事实层 - 关键实体
  l1_facts: {
    brands?: Array<{ name: string; positioning?: string; relevance?: string }>;
    locations?: Array<{ name: string; type?: string; characteristics?: string }>;
    persons?: Array<{ name: string; role?: string }>;
    items?: Array<{ name: string; description?: string }>;
    events?: Array<{ name: string; context?: string }>;
    concepts?: Array<{ name: string; definition?: string }>;
  };

  // L2: 多视角分析
  l2_perspectives: Array<{
    perspective_name: string;
    weight: number;
    analysis: string;
    key_considerations?: string[];
  }>;

  // L3: 核心张力
  l3_core_tension: {
    tension_statement: string;
    conflicting_goals?: string[];
    resolution_strategy: string;
  };

  // L4: 用户任务 JTBD
  l4_user_task: {
    jtbd_statement: string;
    functional_job?: string;
    emotional_job?: string;
    social_job?: string;
  };

  // L5: 锐度评估
  l5_sharpness: {
    score: number;
    specificity: string;
    actionability: string;
    depth: string;
    improvement_suggestions?: string[];
  };

  // 新增: 搜索方向规划（从 L0-L5 推导）
  search_directions: Array<{
    direction_id: string;
    direction: string;
    derived_from: string;  // L0/L1/L2/L3/L4
    what_to_search: string;
    why_search: string;
    expected_insights: string;
    search_keywords: string[];
    can_parallel: boolean;
    priority: 'P0' | 'P1' | 'P2';
  }>;

  // 新增: 回答框架预设
  answer_framework: {
    core_question: string;
    answer_goal: string;
    sections: string[];
    focus_points: string[];
    completeness_criteria: string[];
  };

  // 元数据
  dialogue_content: string;
  confidence_score: number;
  analysis_depth: string;
}

/** v7.300: 第2步可编辑搜索计划 */
export interface Step2SearchPlan {
  session_id: string;
  query: string;
  core_question: string;
  answer_goal: string;

  // 可编辑的搜索步骤
  search_steps: EditableSearchStep[];

  // 执行配置
  max_rounds_per_step: number;
  quality_threshold: number;

  // 用户修改追踪
  user_added_steps: string[];
  user_deleted_steps: string[];
  user_modified_steps: string[];

  // 分页
  current_page: number;
  total_pages: number;

  // 状态
  is_confirmed: boolean;
  confirmed_at?: string;
}

/** v7.300: 4步工作流状态 */
export interface SearchState4Step {
  // 当前步骤 (1-4)
  currentStep: 1 | 2 | 3 | 4;

  // 第1步: 分析
  step1Status: 'idle' | 'analyzing' | 'complete';
  step1Output: Step1AnalysisOutput | null;
  step1StreamContent: string;  // 流式分析内容

  // 第2步: 任务分解（可编辑）
  step2Status: 'idle' | 'generating' | 'editing' | 'confirmed';
  step2Plan: Step2SearchPlan | null;
  awaitingUserConfirmation: boolean;

  // 第3步: 搜索执行
  step3Status: 'idle' | 'searching' | 'complete';
  currentSearchStep: string | null;
  parallelStepsInProgress: string[];

  // 第4步: 结果输出
  step4Status: 'idle' | 'generating' | 'complete';
  finalAnswer: string;
  answerStreamContent: string;

  // 全局
  sources: any[];  // SourceCard[]
  executionTime: number;
  error: string | null;
}

/** v7.300: 智能补充建议 */
export interface SearchPlanSuggestion {
  direction: string;
  what_to_search: string;
  why_important: string;
  priority: 'P0' | 'P1' | 'P2';
  derived_from: string;
}
