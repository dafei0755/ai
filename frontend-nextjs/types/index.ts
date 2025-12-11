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

// 启动分析请求
export interface StartAnalysisRequest {
  user_id: string;
  user_input: string;
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
 * 融合用户修改后的最终版本，包含6个核心字段：
 * 1. project_overview - 项目概览：项目的整体描述和背景
 * 2. core_objectives - 核心目标：项目的主要目标列表
 * 3. project_tasks - 项目任务：需要完成的具体任务
 * 4. narrative_characters - 叙事角色：项目中的人物角色描述
 * 5. physical_contexts - 物理环境：项目的物理场景和环境
 * 6. constraints_opportunities - 约束与机遇：项目的限制条件和发展机会
 */
export interface RequirementsAnalysis {
  project_overview: string;
  core_objectives: string[];
  project_tasks: string[];
  narrative_characters: string[];
  physical_contexts: string[];
  constraints_opportunities: Record<string, any>;
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
}
