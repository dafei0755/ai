'use client';

import { useEffect, useState, useRef, useCallback, useMemo, type CSSProperties, type PointerEvent as ReactPointerEvent } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import {
	Loader2,
	WifiOff,
	X,
	Network,
	Plus,
	CheckCircle2,
	AlertCircle,
	PanelLeft,
	PanelRight,
	Edit2,
	Pin,
	Share2,
	Trash2,
	ArrowLeft,
	SendHorizontal,
	Sparkles
} from 'lucide-react';
import { api } from '@/lib/api';
import { WebSocketClient, type WebSocketMessage } from '@/lib/websocket';
import { QuestionnaireModal } from '@/components/QuestionnaireModal';
import { ConfirmationModal } from '@/components/ConfirmationModal';
import { RoleTaskReviewModal } from '@/components/RoleTaskReviewModal';
import { UserQuestionModal } from '@/components/UserQuestionModal';
import { UnifiedProgressiveQuestionnaireModal } from '@/components/UnifiedProgressiveQuestionnaireModal';
import type { OutputIntentConfirmPayload } from '@/components/UnifiedProgressiveQuestionnaireModal';
import { QualityPreflightModal } from '@/components/QualityPreflightModal';
import { ObserverPanel } from '@/components/ObserverPanel';
import { useGraphStore } from '@/store/graphStore';
import type { ObserverResult } from '@/store/graphStore';
import { extractConceptsFromInterruptData } from '@/lib/conceptExtractor';
// 🔄 v10.x: OutputIntentConfirmationModal 已整合到 UnifiedProgressiveQuestionnaireModal
import { UserQuestionCard } from '@/components/UserQuestionCard';
import type { AnalysisStatus, SessionStatus } from '@/types';
import type { NodeStatus } from '@/types/workflow';
// v2.0 双态架构组件
import ConversationChat, { type ChatMessage, type GuidanceCardStructuredResponse } from '@/components/ConversationMode/ConversationChat';
import UpgradePromptBanner from '@/components/ConversationMode/UpgradePromptBanner';
import { KnowledgeGraphCanvas } from '@/components/KnowledgeGraphCanvas';
import { CockpitPanel, formatBoardVisualBriefForPrompt, type BoardCanvasSpace, type BoardVisualBrief, type DssPage } from '@/components/CockpitPanel';
import { AdvisorPanel } from '@/components/project-cockpit/AdvisorPanel';
import type { ProjectOverview } from '@/components/project-cockpit/mock/mockData';
import type { ActionChip, AdvisorViewModel } from '@/types/advisor';
import { PlanSandboxPanel } from '@/components/PlanSandboxPanel';
import { GeoCanvasView } from '@/components/geo/GeoCanvasView';
import { useGeoStore } from '@/store/useGeoStore';
import { useSession } from '@/contexts/SessionContext';
import { AppSessionShell } from '@/components/layout/AppSessionShell';
import { deriveSessionTitle, resolveSessionTitle } from '@/lib/sessionTitle';
import { EMPTY_CHAT_MESSAGES } from '@/features/conversation/conversationHistoryAdapter';
import { bootstrapConversationSession } from '@/features/conversation/conversationSessionBootstrap';
import {
	respondToGuidanceCardAction,
	sendConversationMessageAction,
} from '@/features/conversation/conversationActionHandlers';
import {
	persistAdvisorConversationMessages,
	restoreAdvisorConversationMessages,
	type AdvisorConversationMessagesByScene,
} from '@/features/conversation/conversationLocalPersistence';
import {
	persistAdvisorHistoryRecords,
	restoreAdvisorHistoryRecords,
	type AdvisorHistoryRecord,
} from '@/features/conversation/advisorHistoryPersistence';
import {
	deriveAdvisorHistoryTitle,
	upsertAdvisorHistoryRecord,
} from '@/features/conversation/advisorHistoryDerivation';
import { groupAdvisorHistoryRecords } from '@/features/conversation/advisorHistoryGrouping';
import {
	buildAdvisorConversationKey,
	getAdvisorConversationMessages,
	updateAdvisorConversationMessages,
} from '@/features/conversation/advisorConversationAccessors';
import {
	buildAdvisorSceneContext,
	getScenePerspectiveOptions,
	type ExpertPerspectiveOption,
} from '@/features/conversation/advisorSceneContext';
import { getAdvisorViewModel } from '@/features/conversation/advisorViewModel';
// v7.290: 分析页面改为独立体验，移除侧边栏组件

// 节点名称中文映射
const NODE_NAME_MAP: Record<string, string> = {
	// 输入验证阶段
	input_guard: '安全内容检测',
	unified_input_validator_initial: '初始输入验证',
	unified_input_validator_secondary: '二次输入验证',
	domain_validator: '领域适配性验证',

	// 需求分析阶段
	requirements_analyst: '用户需求分析',
	requirement_collection: '需求信息收集',
	feasibility_analyst: '可行性分析',
	calibration_questionnaire: '战略校准问卷',
	requirements_confirmation: '需求确认 (已废弃 v7.151)',  // 🔧 仅用于旧会话显示
	requirement_confirmation: '需求确认 (已废弃 v7.151)',   // 别名兼容
	// 🆕 v9.3: v11.0 新增节点映射（防止控制台"未映射的英文节点名"警告）
	output_intent_detection: '输出意图检测',
	questionnaire_summary: '需求洞察',
	progressive_questionnaire: '递进式问卷',
	progressive_step1_task_decompose: '任务拆解',
	progressive_step2_gap_filling: '信息补全',
	progressive_step2_radar: '维度调节',

	// 任务规划阶段
	role_task_unified_review: '任务审批',
	quality_preflight: '质量预检',
	project_director: '项目拆分',
	strategic_analysis: '战略分析',
	deliverable_id_generator: '交付物拆解',
	search_query_generator: '搜索策略生成',

	// 专家执行阶段
	batch_execution: '专家团队分析',
	batch_executor: '准备专家分析',
	agent_executor: '专家分析执行中',
	batch_router: '分析进度汇总',
	batch_aggregator: '专家成果整合',
	batch_strategy_review: '方案策略评审',
	parallel_analysis: '专家并行分析',

	// 审核阶段
	result_aggregator: '生成分析报告',
	result_aggregation: '结果聚合',
	analysis_review: '质量审核',
	manual_review: '人工审核',
	conduct_red_review: '红队审核',
	conduct_blue_review: '蓝队审核',
	conduct_judge_review: '评委裁决',
	conduct_client_review: '甲方审核',
	detect_challenges: '挑战检测',
	final_review: '最终审核',
	result_review: '结果审核',
	report_guard: '报告安全审核',  // 🔥 v7.21: 添加缺失的节点
	projection_dispatcher: '多维投射调度',

	// 完成阶段
	pdf_generator: '生成PDF文档',
	pdf_generation: 'PDF生成中',
	user_question: '解答用户追问',
	interrupt: '等待用户输入',
	completed: '分析已完成',
	waiting_for_input: '等待用户输入',

	// 🔥 v7.7: 状态值映射
	init: '初始化中',
	error: '发生错误',
	running: '运行中',
	processing: '处理中',
	failed: '执行失败',

	// 英文描述映射（后端可能返回的英文描述）
	'Initial input validation': '初始输入验证',
	'Secondary input validation': '二次输入验证',
	'Domain validation': '领域验证',
	'Requirements analysis': '需求分析',
	'Feasibility analysis': '可行性分析',
	'Calibration questionnaire': '战略校准问卷',
	'Requirements confirmation': '需求确认',
	'Project director': '项目拆分',
	'Quality preflight': '质量预检',
	'Batch execution': '批次执行',
	'Result aggregation': '结果聚合',
	'PDF generation': 'PDF生成',
	'Completed': '已完成',
	'Waiting for input': '等待输入',
	'User requirements analysis': '用户需求分析'
};

const unmappedNodeWarned = new Set<string>();

// 格式化节点名称：优先使用中文映射，支持模糊匹配
const formatNodeName = (nodeName: string | undefined): string => {
	// 🔥 状态对齐修复: 空字符串也视为无值
	if (!nodeName || nodeName.trim() === '') return '准备中...';

	// 1. 精确匹配
	if (NODE_NAME_MAP[nodeName]) {
		return NODE_NAME_MAP[nodeName];
	}

	// 2. 小写匹配
	const lowerName = nodeName.toLowerCase();
	if (NODE_NAME_MAP[lowerName]) {
		return NODE_NAME_MAP[lowerName];
	}

	// 3. 下划线转换匹配（如 requirement_collection -> RequirementCollection）
	for (const [key, value] of Object.entries(NODE_NAME_MAP)) {
		if (key.toLowerCase() === lowerName ||
		    key.toLowerCase().replace(/_/g, '') === lowerName.replace(/_/g, '').replace(/ /g, '')) {
			return value;
		}
	}

	// 4. 如果还是英文，尝试返回一个友好的格式
	// 将 snake_case 转换为标题格式，但标记为未翻译
	if (/^[a-z_]+$/.test(nodeName)) {
		if (!unmappedNodeWarned.has(nodeName)) {
			console.warn(`[formatNodeName] 未映射的英文节点名: ${nodeName}`);
			unmappedNodeWarned.add(nodeName);
		}
	}

	return NODE_NAME_MAP[nodeName] || nodeName;
};

type CockpitModuleKey = 'files' | 'assets' | 'inspiration' | 'board' | 'experts' | 'insight' | 'knowledge' | 'geo';
type PrimaryNavKey = 'project' | 'assets' | 'knowledge';
type ProjectSectionKey = 'space' | 'sandbox' | 'board';
type InsightViewKey = 'main' | 'space' | 'flow' | 'emotion' | 'time';
type LayoutMode = 'split' | 'left-focus' | 'right-focus';
type AnalysisModuleQuery = 'project_base' | 'floor_plan' | 'scheme_canvas' | 'geo' | 'silicon_avatar';

const ANALYSIS_MODULE_QUERY_VALUES = new Set<string>([
	'project_base',
	'floor_plan',
	'scheme_canvas',
	'geo',
	'silicon_avatar',
]);

const parseAnalysisModuleQuery = (value: string | null): AnalysisModuleQuery | null => {
	if (!value || !ANALYSIS_MODULE_QUERY_VALUES.has(value)) return null;
	return value as AnalysisModuleQuery;
};
type CockpitCard = {
	title: string;
	desc: string;
	badge?: string;
	highlights?: string[];
	accent?: string;
	size?: 'sm' | 'md' | 'lg';
};

const WORKSPACE_LAYOUT_STORAGE_KEY = 'analysis.workspace.layout.v2';
const WORKSPACE_PANEL_MIN_RATIO = 0.18;
const WORKSPACE_PANEL_DEFAULT_RATIO = 0.22;
const WORKSPACE_PANEL_MAX_RATIO = 0.32;

type WorkspaceResizePanel = 'middle' | 'advisor';

const clampWorkspacePanelRatio = (value: number) =>
	Math.min(WORKSPACE_PANEL_MAX_RATIO, Math.max(WORKSPACE_PANEL_MIN_RATIO, value));

const PRIMARY_NAV_ITEMS: Array<{ key: PrimaryNavKey; title: string }> = [
	{ key: 'project', title: '项目底盘' },
	{ key: 'knowledge', title: '我的硅基分身' },
];

const EXPERT_SUMMON_OPTIONS = ['召集全部', '空间总控', '用户研究', '商业运营', '实施边界', '风险总控'] as const;

const PROJECT_SECTION_ITEMS: Array<{ key: ProjectSectionKey; title: string }> = [
	{ key: 'sandbox', title: '平面推演' },
	{ key: 'board', title: '方案画布' },
];

type ConcreteBoardCanvasSpace = Exclude<BoardCanvasSpace, '全部'>;

const PLAN_SANDBOX_SPACE_OPTIONS: ConcreteBoardCanvasSpace[] = ['大堂', '餐厅', '客房', '公区', '连廊', '后勤'];

const PROJECT_SPACE_INFERENCE_KEYWORDS: Record<ConcreteBoardCanvasSpace, string[]> = {
	大堂: ['大堂', '前厅', '前台', '接待', '迎宾', '酒店入口', '到达'],
	餐厅: ['餐厅', '餐饮', '厨房', '早餐', '茶饮', '咖啡', '用餐'],
	客房: ['客房', '住宿', '房型', '睡眠', '卫浴', '行李'],
	公区: ['公区', '公共', '入口', '市场', '街区', '商业', '社区', '广场', '更新', '改造', '文旅', '游客', '茶市街'],
	连廊: ['连廊', '走廊', '通道', '动线', '路径', '廊', '导视'],
	后勤: ['后勤', '仓储', '补给', '设备', '清洁', '垃圾', '服务后台'],
};

const collectProjectOverviewText = (overview: ProjectOverview | null): string =>
	[
		overview?.name,
		overview?.oneLiner,
		...(overview?.confirmedItems ?? []),
		...(overview?.gapItems ?? []),
		...(overview?.mainContradiction?.sides ?? []),
		overview?.mainContradiction?.advisorNote,
	]
		.filter((item): item is string => Boolean(item && item.trim()))
		.join(' ');

const getFirstUserMessage = (history: Array<{ role?: string; content?: string }> | undefined): string =>
	history?.find((entry) => entry.role === 'user' && entry.content?.trim())?.content?.trim() ?? '';

const inferProjectDefaultSpace = (overview: ProjectOverview | null): ConcreteBoardCanvasSpace | null => {
	const text = collectProjectOverviewText(overview);
	if (!text) return null;

	let bestSpace: ConcreteBoardCanvasSpace | null = null;
	let bestScore = 0;
	for (const space of PLAN_SANDBOX_SPACE_OPTIONS) {
		let score = text.includes(space) ? 12 : 0;
		for (const keyword of PROJECT_SPACE_INFERENCE_KEYWORDS[space]) {
			if (text.includes(keyword)) score += keyword.length >= 3 ? 3 : 2;
		}
		if (score > bestScore) {
			bestScore = score;
			bestSpace = space;
		}
	}
	return bestScore > 0 ? bestSpace : null;
};

const COCKPIT_CARDS: Record<Exclude<CockpitModuleKey, 'insight' | 'knowledge'>, CockpitCard[]> = {
	files: [
		{
			title: '用户需求',
			desc: '围绕丹麦家居品牌 HAY 的年轻、克制、功能主义气质，梳理项目目标客群、预算区间、空间优先级与体验期待。重点关注山地民宿在自然景观、轻度度假属性与品牌识别度之间的平衡关系。',
			badge: '核心输入',
			highlights: ['品牌气质', '轻度度假感', '公私边界'],
			accent: 'from-sky-500/22 via-sky-500/8 to-transparent',
			size: 'lg',
		},
		{
			title: '市场分析',
			desc: '分析峨眉山周边山地民宿市场的客群画像、消费价格带与审美变化趋势，校准项目在区域中的价值锚点。同步比较本地度假型住宿与城市型精品酒店在社交属性和停留时长上的差异。',
			badge: '外部环境',
			highlights: ['在地客群', '度假消费', '审美趋势'],
			accent: 'from-violet-500/18 via-violet-500/8 to-transparent',
			size: 'md',
		},
		{
			title: '竞品策略',
			desc: '拆解标杆民宿和设计酒店在公区氛围、客房尺度、材料表达与品牌传播上的差异点，识别可借鉴与应规避的策略。进一步提炼体验缺口、品牌错位和定价机会，作为后续概念切入依据。',
			badge: '对标拆解',
			highlights: ['体验缺口', '品牌错位', '定价机会'],
			accent: 'from-amber-400/18 via-amber-300/10 to-transparent',
			size: 'sm',
		},
		{
			title: '色彩策略',
			desc: '定义主辅色、材质映射与情绪目标，构建适合山地民宿的低饱和色彩体系。通过山地灰绿、低饱和木色与暖感金属细节建立统一语气，避免空间在自然语境中显得过度商业化。',
			badge: '氛围语言',
			highlights: ['山地灰绿', '低饱和木色', '暖感光泽'],
			accent: 'from-emerald-400/18 via-emerald-400/8 to-transparent',
			size: 'md',
		},
		{
			title: '空间功能清单',
			desc: '梳理客房、公区、接待、餐饮与后勤等功能模块的面积占比和优先顺序，明确哪些区域承担品牌展示、停留社交和运营效率。同步界定高价值空间与可压缩空间，避免后期概念泛化。',
			badge: '功能配置',
			size: 'md',
		},
		{
			title: '动线组织草案',
			desc: '建立主人、住客、服务与补给四类动线的基础组织逻辑，确保抵达体验、入住效率与后勤流线互不干扰。特别关注山地场地中入口高差、景观面朝向与夜间照明对动线选择的影响。',
			badge: '流线',
			size: 'sm',
		},
		{
			title: '场地约束条件',
			desc: '归纳山地高差、采光朝向、消防疏散、结构限制和雨雾气候对空间组织的影响，为概念方案建立现实边界。优先识别需要在早期就锁定的限制条件，避免后期出现大规模推翻。',
			badge: '约束',
			size: 'md',
		},
		{
			title: '预算分配表',
			desc: '给出硬装、软装、灯光、家具与设备的预算比例建议，帮助项目在品牌表达与实际落地之间建立合理分配。重点列出可高配与可替代部分，防止预算被单一环节吞噬。',
			badge: '预算',
			size: 'sm',
		},
		{
			title: '品牌语义板',
			desc: '围绕 HAY 的年轻、克制、功能主义气质提炼可转译为空间语言的关键词与反关键词。通过情绪语义、品牌语境与消费心理交叉校准，避免“像北欧但没有品牌辨识”的模糊表达。',
			badge: '品牌',
			size: 'md',
		},
		{
			title: '材料样本册',
			desc: '收录墙、地、顶及家具触感材料的搭配方向、耐用等级与替代层级，明确概念表达与运营维护之间的平衡。优先筛选适合潮湿山地环境、但不失细腻触感和品牌质感的材料组合。',
			badge: '材料',
			size: 'md',
		},
		{
			title: '灯光场景表',
			desc: '梳理白天、傍晚、夜间及社交时段的照明层级与色温变化，建立一套兼顾情绪与运营的灯光场景表。强调公共空间的氛围转换与客房私密感的细微区别，避免一套照明走到底。',
			badge: '灯光',
			size: 'sm',
		},
		{
			title: '家具选型方向',
			desc: '明确床、沙发、椅凳、边几等重点家具的风格、尺寸与比例基准，避免不同供应渠道带来的视觉断裂。优先建立“轻、薄、功能明确”的家具轮廓，同时保留局部温润感。',
			badge: '家具',
			size: 'md',
		},
		{
			title: '公区社交策略',
			desc: '定义前厅、餐吧、壁炉区、共享客厅与景观停留点之间的组织关系，打造兼具品牌展示与真实停留价值的社交场景。重点研究公共空间如何形成“轻社交”而非强打卡，以提高复访体验。',
			badge: '公区',
			size: 'lg',
		},
		{
			title: '客房分型建议',
			desc: '为标准间、家庭房、景观房等房型建立差异化体验逻辑与配置原则，使不同客群能获得明确而非模糊的入住价值。同步控制家具尺度、卫浴配置与景观界面，避免房型差异只停留在数量。',
			badge: '客房',
			size: 'md',
		},
		{
			title: '收纳系统表',
			desc: '整理行李、布草、清洁、备品与后勤收纳的模块化处理方式，确保住客使用体验与运营管理同步高效。重点标注住客可见收纳与服务型收纳的边界，以维持整体空间整洁度。',
			badge: '收纳',
			size: 'sm',
		},
		{
			title: '设备清单草稿',
			desc: '列出暖通、新风、热水与智能控制系统的配置范围与优先级建议，帮助团队在早期识别设备预算与安装条件。同步提示对天花高度、墙面机电点位和后期维护影响较大的重点系统。',
			badge: '设备',
			size: 'md',
		},
		{
			title: '软装氛围说明',
			desc: '说明织物、挂画、器皿与装饰物在整体空间中的语气比例与克制度，确保软装不会掩盖空间本体。强调以层次和触感建立记忆点，而不是依赖堆砌装饰营造所谓“高级感”。',
			badge: '软装',
			size: 'sm',
		},
		{
			title: '施工节点提醒',
			desc: '梳理木作、机电、照明与定制安装之间的关键工序衔接点，帮助团队提前规避返工风险。重点标出易被忽略但影响观感的接口，如灯槽、收口、五金与电气点位对齐。',
			badge: '施工',
			size: 'md',
		},
		{
			title: '阶段交付目录',
			desc: '梳理概念方案、深化方案与落地执行三个阶段的交付物清单，使团队清楚每个节点需要完成的输出类型与深度。同步区分对内工作文件与对外展示文件，避免交付口径混乱。',
			badge: '交付',
			size: 'sm',
		},
		{
			title: '风险与机会清单',
			desc: '汇总预算波动、工期压力、景观资源利用与品牌传播机会，为后续决策提供优先级参考。把可控风险、不可控风险和高价值机会分层呈现，帮助团队更早形成取舍判断。',
			badge: '风险机会',
			size: 'md',
		},
	],
	assets: [
		{ title: '宋式家具样本', desc: '含规格、厂家、交期与替代建议。', badge: '资源' },
		{ title: '灯具供应清单', desc: '3000K 层级照明与可落地组合。', badge: '资源' },
		{ title: '地材替代方案', desc: '超预算时同风格替代路径。', badge: '资源' },
	],
	inspiration: [
		{ title: '跨项目木作库', desc: '承接资源收藏、上传图和长期复用素材。', badge: '仓库' },
		{ title: '风格分类组', desc: '按风格、空间、材料自由归档。', badge: '分类' },
		{ title: '上传暂存组', desc: '自有参考图、现场照片、竞品截图统一收口。', badge: '上传' },
	],
	board: [
		{ title: '意向图组 A', desc: '静谧、克制、自然光优先。', badge: '参考' },
		{ title: '意向图组 B', desc: '材质对比、点状暖光。', badge: '参考' },
		{ title: '构图参考组', desc: '入口-中景-终景镜头节奏。', badge: '参考' },
	],
	geo: [
		{ title: '地理坐标锚点', desc: '项目经纬度、行政区划、地址和场地边界的统一入口。', badge: 'Geo' },
		{ title: '规划图层', desc: '承载地块红线、用地性质、容积率、限高和退线等规划证据。', badge: '图层' },
		{ title: '市场圈层', desc: '围绕项目场地汇总竞品、POI、交通可达和客源洞察。', badge: '洞察' },
	],
	experts: [
		{ title: '成本顾问', desc: '预算可落地评分与风险提示。', badge: '顾问' },
		{ title: '灯光顾问', desc: '情绪曲线与照明分层校准。', badge: '顾问' },
		{ title: '动线顾问', desc: '主客/服务动线冲突扫描。', badge: '顾问' },
	],
};

const INSIGHT_VIEWS: Array<{ key: InsightViewKey; label: string; desc: string }> = [
	{ key: 'main', label: '项目全景关系图', desc: '主图：项目脑图谱（全局关系）。' },
	{ key: 'space', label: '空间程序结构图', desc: '副图：空间骨架与模块层级。' },
	{ key: 'flow', label: '动线关系图', desc: '副图：主人/访客/服务动线镜像。' },
	{ key: 'emotion', label: '情绪体验曲线图', desc: '副图：心理旅程与节奏峰谷。' },
	{ key: 'time', label: '时间状态图', desc: '副图：时段与季节切片对比。' },
];

const CONTEXT_STORAGE_KEY = 'advisor_context_by_scene';
const CONTEXT_PANE_PERCENT_KEY = 'advisor_context_pane_percent';

// 场景-特定上下文持久化存储
const getStoredContextPercent = (): number => {
	if (typeof window === 'undefined') return 42;
	try {
		const stored = window.localStorage.getItem(CONTEXT_PANE_PERCENT_KEY);
		const parsed = stored ? parseInt(stored, 10) : 42;
		return Math.min(72, Math.max(24, parsed));
	} catch {
		return 42;
	}
};

const saveContextPercent = (percent: number) => {
	if (typeof window === 'undefined') return;
	try {
		window.localStorage.setItem(CONTEXT_PANE_PERCENT_KEY, String(Math.round(percent)));
	} catch (e) {
		console.warn('Failed to save context pane percent:', e);
	}
};

export default function AnalysisPage() {
	const params = useParams();
	const router = useRouter();
	const searchParams = useSearchParams();
	const sessionId = params.sessionId as string;
	const {
		sessions,
		loadMoreTriggerRef,
		handleRenameSession,
		handlePinSession,
		handleShareSession,
		handleDeleteSession,
	} = useSession();
	const isDemoSession = sessionId === 'demo';
	const appliedInitialModuleRef = useRef<string | null>(null);
	const adaptiveLeftDockGutter = 'clamp(44px, 3.2vw, 72px)';
	const adaptiveLeftCardPadding = 'clamp(10px, 1.2vw, 20px)';
	const adaptiveRightContentGutter = 'clamp(12px, 2vw, 32px)';
	const [viewportWidth, setViewportWidth] = useState(1440);
	const [workspaceMiddleTargetRatio, setWorkspaceMiddleTargetRatio] = useState(WORKSPACE_PANEL_DEFAULT_RATIO);
	const [advisorRightTargetRatio, setAdvisorRightTargetRatio] = useState(WORKSPACE_PANEL_DEFAULT_RATIO);
	const [workspaceLayoutPrefsLoaded, setWorkspaceLayoutPrefsLoaded] = useState(false);
	const [resizingWorkspacePanel, setResizingWorkspacePanel] = useState<WorkspaceResizePanel | null>(null);
	const [isSessionSidebarOpen, setIsSessionSidebarOpen] = useState(true);

	const [status, setStatus] = useState<AnalysisStatus | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [wsConnected, setWsConnected] = useState<boolean>(false);
	const [userInput, setUserInput] = useState<string>(''); // v7.290: 用户输入（用于显示用户问题卡片）
	const [nodeHistory, setNodeHistory] = useState<Array<{ node: string; detail: string; time: string }>>([]);
	const [nodeDetails, setNodeDetails] = useState<Record<string, { status: NodeStatus; detail?: string }>>({});

	// 问卷状态
	const [showQuestionnaire, setShowQuestionnaire] = useState<boolean>(false);
	const [questionnaireData, setQuestionnaireData] = useState<any>(null);

	// 需求确认状态
	const [showConfirmation, setShowConfirmation] = useState<boolean>(false);
	const [confirmationData, setConfirmationData] = useState<any>(null);

	// 用户追问状态
	const [showUserQuestion, setShowUserQuestion] = useState<boolean>(false);
	const [userQuestionData, setUserQuestionData] = useState<any>(null);
	const [userQuestionSubmitting, setUserQuestionSubmitting] = useState<boolean>(false);

	// 角色任务审核状态
	const [roleTaskReviewData, setRoleTaskReviewData] = useState<any>(null);
	const [showRoleTaskReview, setShowRoleTaskReview] = useState(false);

	// 🆕 v7.130: 三步递进式问卷 - 统一状态管理
	// currentProgressiveStep: 0=关闭, 1=意图确认, 2=任务梳理, 3=信息补全, 4=雷达图, 5=需求洞察
	const [currentProgressiveStep, setCurrentProgressiveStep] = useState<number>(0);
	const [progressiveStepData, setProgressiveStepData] = useState<any>(null);

	// 🆕 v7.119: 质量预检警告状态
	const [qualityPreflightData, setQualityPreflightData] = useState<any>(null);
	const [showQualityPreflight, setShowQualityPreflight] = useState(false);

	// v2.0 双态架构状态
	const [systemMode, setSystemMode] = useState<'conversation' | 'project'>('conversation');
	const [conversationMessagesByScene, setConversationMessagesByScene] = useState<AdvisorConversationMessagesByScene>({});
	const [upgradeIndicators, setUpgradeIndicators] = useState({ freeze_readiness: 0, cognitive_debt: 0, diverge_fatigue: 0 });
	const [showUpgradeBanner, setShowUpgradeBanner] = useState(false);
	const [upgradeSuggestionText, setUpgradeSuggestionText] = useState('');
	// 项目态需求分析区折叠状态（任务完成后自动折叠）
	const [requirementsCollapsed, setRequirementsCollapsed] = useState(false);
	// 项目态底部输入栏（UserQuestion 追问时启用）
	const [projectInputValue, setProjectInputValue] = useState('');
	const [activeCockpitModule, setActiveCockpitModule] = useState<CockpitModuleKey>('files');
	const [activeProjectSection, setActiveProjectSection] = useState<ProjectSectionKey>('space');
	const [activeBoardSpace, setActiveBoardSpace] = useState<BoardCanvasSpace>('全部');
	const [activeBoardVisualBrief, setActiveBoardVisualBrief] = useState<BoardVisualBrief | null>(null);
	const [boardCanvasZoom, setBoardCanvasZoom] = useState(1);
	const [activeDssPage, setActiveDssPage] = useState<DssPage>('sediment');
	const [portfolioYearHeightScale, setPortfolioYearHeightScale] = useState(1);
	const [activeInsightView, setActiveInsightView] = useState<InsightViewKey>('main');
	const [cockpitContextRefs, setCockpitContextRefs] = useState<string[]>([]);
	const [conversationPrefill, setConversationPrefill] = useState<{ id: number; text: string } | null>(null);
	const [graphViewMode, setGraphViewMode] = useState<'grouped' | 'free'>('grouped');

	// 地理工作台
	const geoAnchor = useGeoStore((s) => s.geoAnchor);

	// 🔄 v10.2 Path B: 输出意图由 step1 payload 的 output_intent 子字段携带，Modal 内部管理

	// 图谱 store
	const { ingestText: ingestGraphText, promoteToPending, promoteAllPendingToStable, resetForSession, ingestObserverResult } = useGraphStore();

	// 观察屏同步：broad cast channel
	const graphBroadcastRef = useRef<BroadcastChannel | null>(null);
	useEffect(() => {
		const ch = new BroadcastChannel('scheme-graph-sync');
		graphBroadcastRef.current = ch;
		ch.onmessage = (e: MessageEvent) => {
			if (e.data?.type === 'OBSERVER_READY') {
				// 观察屏就绪后立即推送当前状态
				const { stable, stableEdges } = useGraphStore.getState();
				ch.postMessage({
					type: 'FULL_SYNC',
					payload: { nodes: [...stable.values()], edges: [...stableEdges.values()] },
				});
			} else if (e.data?.type === 'OBSERVER_CLOSED') {
				// 观察屏关闭 → 自动恢复左侧面板
				setLayoutMode((prev) => (prev === 'right-focus' ? 'split' : prev));
			}
		};
		return () => ch.close();
	}, []);

	// 广播当前 stable 图谱状态到观察屏
	const broadcastGraphState = useCallback(() => {
		if (!graphBroadcastRef.current) return;
		const { stable, stableEdges } = useGraphStore.getState();
		graphBroadcastRef.current.postMessage({
			type: 'FULL_SYNC',
			payload: { nodes: [...stable.values()], edges: [...stableEdges.values()] },
		});
	}, []);

	// session 切换时重置图谱（保证各 session 图谱隔离，不跨会话混入）
	useEffect(() => { resetForSession(sessionId); }, [sessionId, resetForSession]);

	// 项目底盘真实数据（来自 /api/sessions/{id}/project-definition）
	const [projectOverview, setProjectOverview] = useState<ProjectOverview | null>(null);
	const [projectTitleSource, setProjectTitleSource] = useState('');
	const [projectDisplayName, setProjectDisplayName] = useState('');

	useEffect(() => {
		if (!sessionId || isDemoSession) return;
		let cancelled = false;
		api.getSession(sessionId)
			.then((session) => {
				if (cancelled) return;
				const rawTitleSource = session.user_input?.trim() || getFirstUserMessage(session.conversation_history_v2) || '';
				const resolvedTitle = resolveSessionTitle(rawTitleSource, session.display_name);
				setProjectTitleSource(rawTitleSource);
				setProjectDisplayName(resolvedTitle);
				if (resolvedTitle && session.display_name !== resolvedTitle) {
					void api.updateSession(sessionId, { display_name: resolvedTitle }).catch((error) => {
						console.warn('[analysis] persist normalized project title failed:', error);
					});
				}
			})
			.catch((error) => {
				console.warn('[analysis] load session title failed:', error);
			});
		return () => {
			cancelled = true;
		};
	}, [isDemoSession, sessionId]);

	useEffect(() => {
		if (!sessionId || isDemoSession) return;
		fetch(`/api/sessions/${sessionId}/project-definition`)
			.then((r) => r.ok ? r.json() : null)
			.then((data) => {
				if (!data) return;
				// 将后端返回数据映射为前端 ProjectOverview 结构
				const overview: ProjectOverview = {
					name: data.project_name || sessionId,
					oneLiner: data.one_liner || '',
					stage: {
						key: data.stage_key || 'project_definition',
						label: data.stage_key === 'space_inference' ? '空间推演' : '项目定义',
						status: 'active',
						hint: data.stage_key === 'space_inference' ? '' : '补充面积与平面图后可进入空间推演',
					},
					confirmedItems: data.confirmed_items || [],
					gapItems: data.gap_items || [],
					mainContradiction: {
						sides: data.main_contradiction?.sides || [],
						advisorNote: data.main_contradiction?.advisor_note || '',
					},
					readiness: [
						{
							label: '项目方向草案',
							systemName: 'AlignedBrief / ProjectBasePatch',
							level: (data.confirmed_items?.length >= 3 ? 'sufficient' : data.confirmed_items?.length >= 1 ? 'concept_only' : 'not_started') as 'sufficient' | 'concept_only' | 'not_started',
							progressPct: Math.min(100, (data.confirmed_items?.length || 0) * 20),
							statusLabel: data.one_liner ? '可以形成项目方向建议' : '待补充信息',
							upgradeHint: '补充预算档位 → 提升可执行性',
						},
						{
							label: '空间结构框架',
							systemName: 'SPG',
							level: 'not_started' as const,
							progressPct: 0,
							statusLabel: '还缺平面和面积',
							upgradeHint: '补充面积 / 平面图 → 提升准确度',
						},
						{
							label: '执行任务书',
							systemName: 'ExecutionPlan',
							level: 'not_started' as const,
							progressPct: 0,
							statusLabel: '尚不具备启动条件',
							upgradeHint: '需先完成空间结构框架',
						},
					],
					recommendedActions: data.gap_items?.length
						? [
							{
								label: `补充 ${data.gap_items.length} 个关键信息`,
								benefit: '我可以把当前判断从"初步方向"推进到"可形成草案"',
								isPrimary: true,
							},
							{
								label: '保存为项目方向草案',
								benefit: '保存为可编辑草案，不会冻结正式任务书',
								isPrimary: false,
							},
						]
						: [
							{
								label: '预览平面推演',
								benefit: '当前信息已足够生成初步平面逻辑',
								isPrimary: true,
							},
						],
					capabilities: [
						{
							key: 'project_base',
							label: '项目底盘',
							statusLabel: '进行中',
							state: 'active',
						},
						{
							key: 'floor_plan',
							label: '平面推演',
							statusLabel: '可先预览，有图更准',
							state: 'preview_only',
							actionLabel: '预览平面推演',
						},
						{
							key: 'scheme_canvas',
							label: '方案画布',
							statusLabel: '概念可用，落位待条件',
							state: 'concept_available',
							actionLabel: '生成概念画布',
						},
					],
				};
				setProjectOverview(overview);
			})
			.catch(() => {/* 网络异常：保持 null，CockpitPanel 内部 fallback 到 mock */});
	}, [isDemoSession, sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

	// 节点详情面板状态
	const [selectedNode, setSelectedNode] = useState<string | null>(null);
	const [layoutMode, setLayoutMode] = useState<LayoutMode>('split');
	const [advisorHistoryOpen, setAdvisorHistoryOpen] = useState(false);
	const [advisorHistoryRecords, setAdvisorHistoryRecords] = useState<AdvisorHistoryRecord[]>([]);
	const [activeExpertPerspective, setActiveExpertPerspective] =
		useState<ExpertPerspectiveOption>('平衡推进视角');
	const wsClientRef = useRef<WebSocketClient | null>(null);
	const hasRedirectedRef = useRef<boolean>(false);
	// 项目态对话流底部锚点（自动滚动）
	const projectChatEndRef = useRef<HTMLDivElement>(null);
	const isLeftCollapsed = layoutMode === 'right-focus';
	const isRightCollapsed = layoutMode === 'left-focus';
	const projectActivated = Boolean(sessionId);
	const activePrimaryNav: PrimaryNavKey =
		activeCockpitModule === 'assets' || activeCockpitModule === 'inspiration'
			? 'assets'
			: activeCockpitModule === 'knowledge'
			? 'knowledge'
			: 'project';
	const isKnowledgeTwoColumnLayout = activePrimaryNav === 'knowledge';
	const effectiveWorkspaceMiddleTargetRatio = isKnowledgeTwoColumnLayout ? 0 : workspaceMiddleTargetRatio;
	const splitLeftFixedRatio = 1 - advisorRightTargetRatio;
	const workspaceMainTargetRatio = 1 - advisorRightTargetRatio - effectiveWorkspaceMiddleTargetRatio;
	const preferredFileViewMode = '统一视图';
	const isSandboxSectionActive = activeProjectSection === 'sandbox';
	const isProjectGraphShellActive =
		activePrimaryNav === 'project' &&
		activeCockpitModule === 'files' &&
		!isSandboxSectionActive;
	const projectGraphColumnRatio = useMemo(() => {
		if (!isProjectGraphShellActive) return 1;
		if (splitLeftFixedRatio <= 0) return 0.72;
		return Math.max(0.6, Math.min(0.85, workspaceMainTargetRatio / splitLeftFixedRatio));
	}, [isProjectGraphShellActive, splitLeftFixedRatio, workspaceMainTargetRatio]);
	const projectWhiteboardColumnRatio = 1 - projectGraphColumnRatio;
	const advisorPanelViewModel = useMemo((): AdvisorViewModel => {
		const base = getAdvisorViewModel({
			primaryNav: activePrimaryNav,
			cockpitModule: activeCockpitModule,
			isSandbox: isSandboxSectionActive,
			dssPage: activeDssPage,
		});
		// 无真实数据时直接返回 mock（资源雷达、硅基分身模块不覆盖）
		if (!projectOverview || activePrimaryNav !== 'project') return base;

		const projectName = projectDisplayName || projectOverview.name;
		const gapCount = projectOverview.gapItems?.length ?? 0;
		const confirmedCount = projectOverview.confirmedItems?.length ?? 0;
		const oneLiner = projectOverview.oneLiner;

		// 方案画布
		if (activeCockpitModule === 'board') {
			const boardJudgment = oneLiner
				? `概念方向已有基础。${oneLiner}。建议先完成空间排布后再深化方案表达。`
				: `概念画布已可启动。落位精度依赖平面推演完成，建议先完成空间排布后再推进方案表达。`;
			return {
				...base,
				sceneContext: { ...base.sceneContext, sessionId },
				boundObjectLabel: `${projectName} · 概念画布`,
				judgment: { ...base.judgment, content: boardJudgment },
				actionChips: [
					{
						type: 'ask',
						label: '生成概念方向草案',
						isPrimary: true,
						payload: { question: `基于"${projectName}"的定位，帮我生成 3 个概念方向草案，各附一句设计主张。` },
					},
					{
						type: 'navigate',
						label: '先完成平面推演',
						isPrimary: false,
						payload: { target: 'floor_plan' },
					},
				] as ActionChip[],
			};
		}

		// 平面推演
		if (isSandboxSectionActive) {
			let sandboxJudgment: string;
			if (gapCount > 0) {
				sandboxJudgment = `平面推演处于预览模式。${projectName} 还有 ${gapCount} 个关键信息待补充，推演精度偏低。补齐项目底盘后可生成更准确的空间方案。`;
			} else if (confirmedCount > 0) {
				sandboxJudgment = `项目信息已基本完整，可以生成平面推演草案。上传底图后精度将大幅提升。`;
			} else {
				sandboxJudgment = `平面推演处于预览模式。补充面积、功能分区等信息后可生成更准确的空间排布方案。`;
			}
			return {
				...base,
				sceneContext: { ...base.sceneContext, sessionId },
				boundObjectLabel: `${projectName} · 平面推演`,
				judgment: { ...base.judgment, content: sandboxJudgment },
				actionChips: [
					{
						type: 'ask',
						label: gapCount > 0 ? `补充 ${gapCount} 个关键信息` : '告诉我建筑面积和功能分区',
						isPrimary: true,
						payload: {
							question: gapCount > 0
								? `请补充以下关键信息：${projectOverview.gapItems.slice(0, 3).join('、')}`
								: `请提供"${projectName}"的总建筑面积（㎡）和主要功能分区？`,
						},
					},
					{
						type: 'navigate',
						label: '返回项目底盘补充',
						isPrimary: false,
						payload: { target: 'project_base' },
					},
				] as ActionChip[],
			};
		}

		// 项目底盘（默认）
		let judgmentContent = base.judgment.content;
		if (gapCount > 0) {
			judgmentContent = `已确认 ${confirmedCount} 条信息；还有 ${gapCount} 个关键缺口待补充。补齐后可推进到下一阶段。`;
		} else if (confirmedCount > 0) {
			judgmentContent = `项目信息已基本完整（${confirmedCount} 条已确认），可以推进到空间推演阶段。`;
		} else if (oneLiner) {
			judgmentContent = oneLiner;
		}

		const actionChips: ActionChip[] = gapCount > 0
			? [
				{
					type: 'ask',
					label: `补充 ${gapCount} 个关键信息`,
					isPrimary: true,
					payload: { question: `请补充以下关键信息：${projectOverview.gapItems.slice(0, 3).join('、')}` },
				},
				{
					type: 'navigate',
					label: '预览平面推演',
					isPrimary: false,
					payload: { target: 'floor_plan' },
				},
				{
					type: 'fill',
					label: '保存项目方向草案',
					isPrimary: false,
					payload: { formId: 'project-base-draft' },
				},
			]
			: [
				{
					type: 'navigate',
					label: '预览平面推演',
					isPrimary: true,
					payload: { target: 'floor_plan' },
				},
			];

		return {
			...base,
			sceneContext: { ...base.sceneContext, sessionId },
			boundObjectLabel: projectName,
			judgment: { ...base.judgment, content: judgmentContent },
			actionChips,
		};
	}, [activePrimaryNav, activeCockpitModule, isSandboxSectionActive, activeDssPage, projectDisplayName, projectOverview, sessionId]);
	const inferredProjectSpace = useMemo(() => inferProjectDefaultSpace(projectOverview), [projectOverview]);
	const projectDefaultSpace = inferredProjectSpace ?? (activeBoardSpace !== '全部' ? activeBoardSpace : PLAN_SANDBOX_SPACE_OPTIONS[0]);
	const activeSandboxSpace: ConcreteBoardCanvasSpace = activeBoardSpace === '全部' ? projectDefaultSpace : activeBoardSpace;
	const fallbackProjectTitleSource = useMemo(
		() => projectTitleSource || collectProjectOverviewText(projectOverview) || sessionId,
		[projectOverview, projectTitleSource, sessionId]
	);
	const displayProjectTitle = useMemo(
		() => projectDisplayName || deriveSessionTitle(fallbackProjectTitleSource),
		[fallbackProjectTitleSource, projectDisplayName]
	);
	useEffect(() => {
		if (projectDisplayName || !fallbackProjectTitleSource || fallbackProjectTitleSource === sessionId) return;
		const resolvedTitle = deriveSessionTitle(fallbackProjectTitleSource);
		setProjectDisplayName(resolvedTitle);
		void api.updateSession(sessionId, { display_name: resolvedTitle }).catch((error) => {
			console.warn('[analysis] persist derived project title failed:', error);
		});
	}, [fallbackProjectTitleSource, projectDisplayName, sessionId]);

	const handleProjectLabelChange = useCallback((currentTitle: string) => {
		const nextRawTitle = window.prompt('修改项目摘要标题（显示前14字，超出自动省略）:', currentTitle);
		if (!nextRawTitle?.trim()) return;
		const nextTitle = deriveSessionTitle(nextRawTitle);
		setProjectTitleSource(nextRawTitle.trim());
		setProjectDisplayName(nextTitle);
		void api.updateSession(sessionId, { display_name: nextTitle }).catch((error) => {
			console.error('[analysis] update project title failed:', error);
			window.alert('项目摘要更新失败，请重试');
		});
	}, [sessionId]);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		try {
			const raw = window.localStorage.getItem(WORKSPACE_LAYOUT_STORAGE_KEY);
			if (raw) {
				const parsed = JSON.parse(raw) as Partial<{ middleRatio: number; advisorRatio: number }>;
				if (Number.isFinite(parsed.middleRatio)) {
					setWorkspaceMiddleTargetRatio(clampWorkspacePanelRatio(Number(parsed.middleRatio)));
				}
				if (Number.isFinite(parsed.advisorRatio)) {
					setAdvisorRightTargetRatio(clampWorkspacePanelRatio(Number(parsed.advisorRatio)));
				}
			}
		} catch (error) {
			console.warn('[analysis] load workspace layout failed:', error);
		} finally {
			setWorkspaceLayoutPrefsLoaded(true);
		}
	}, []);

	useEffect(() => {
		if (!workspaceLayoutPrefsLoaded || typeof window === 'undefined') return;
		try {
			window.localStorage.setItem(
				WORKSPACE_LAYOUT_STORAGE_KEY,
				JSON.stringify({
					middleRatio: workspaceMiddleTargetRatio,
					advisorRatio: advisorRightTargetRatio,
				}),
			);
		} catch (error) {
			console.warn('[analysis] persist workspace layout failed:', error);
		}
	}, [advisorRightTargetRatio, workspaceLayoutPrefsLoaded, workspaceMiddleTargetRatio]);

	useEffect(() => {
		if (!resizingWorkspacePanel || typeof window === 'undefined') return;
		if (isKnowledgeTwoColumnLayout && resizingWorkspacePanel === 'middle') {
			setResizingWorkspacePanel(null);
			return;
		}

		const previousCursor = document.body.style.cursor;
		const previousUserSelect = document.body.style.userSelect;
		document.body.style.cursor = 'col-resize';
		document.body.style.userSelect = 'none';

		const handlePointerMove = (event: PointerEvent) => {
			const width = window.innerWidth || viewportWidth || 1440;
			if (resizingWorkspacePanel === 'middle') {
				const nextMiddleRatio = 1 - advisorRightTargetRatio - event.clientX / width;
				setWorkspaceMiddleTargetRatio(clampWorkspacePanelRatio(nextMiddleRatio));
				return;
			}

			const nextAdvisorRatio = (width - event.clientX) / width;
			setAdvisorRightTargetRatio(clampWorkspacePanelRatio(nextAdvisorRatio));
		};

		const handlePointerUp = () => {
			setResizingWorkspacePanel(null);
		};

		window.addEventListener('pointermove', handlePointerMove);
		window.addEventListener('pointerup', handlePointerUp);
		window.addEventListener('pointercancel', handlePointerUp);

		return () => {
			window.removeEventListener('pointermove', handlePointerMove);
			window.removeEventListener('pointerup', handlePointerUp);
			window.removeEventListener('pointercancel', handlePointerUp);
			document.body.style.cursor = previousCursor;
			document.body.style.userSelect = previousUserSelect;
		};
	}, [advisorRightTargetRatio, isKnowledgeTwoColumnLayout, resizingWorkspacePanel, viewportWidth]);

	const handleWorkspaceResizeStart = useCallback((panel: WorkspaceResizePanel) => (event: ReactPointerEvent<HTMLDivElement>) => {
		if (layoutMode !== 'split') return;
		if (isKnowledgeTwoColumnLayout && panel === 'middle') return;
		event.preventDefault();
		event.stopPropagation();
		setResizingWorkspacePanel(panel);
	}, [isKnowledgeTwoColumnLayout, layoutMode]);

	const activeSplitLeftPanelWidth = useMemo(() => {
		const width = Number.isFinite(viewportWidth) ? viewportWidth : 1440;
		return `${Math.round(width * splitLeftFixedRatio)}px`;
	}, [splitLeftFixedRatio, viewportWidth]);
	const workspaceColumnVars = useMemo(
		() => ({
			'--workspace-main-column-width': `${workspaceMainTargetRatio * 100}vw`,
			'--workspace-middle-column-width': `${effectiveWorkspaceMiddleTargetRatio * 100}vw`,
			'--workspace-advisor-column-width': `${advisorRightTargetRatio * 100}vw`,
			'--workspace-left-compound-width': `${splitLeftFixedRatio * 100}vw`,
		}) as CSSProperties,
		[advisorRightTargetRatio, effectiveWorkspaceMiddleTargetRatio, splitLeftFixedRatio, workspaceMainTargetRatio],
	);
	const advisorSceneContext = useMemo(
		() =>
			buildAdvisorSceneContext({
				activePrimaryNav,
				activeCockpitModule,
				activeProjectSection,
				activeBoardSpace,
				activeDssPage,
				activeInsightView,
			}),
		[
			activePrimaryNav,
			activeCockpitModule,
			activeProjectSection,
			activeBoardSpace,
			activeDssPage,
			activeInsightView,
		]
	);
	const sceneExpertPerspectiveOptions = useMemo(
		() =>
			getScenePerspectiveOptions({
				activePrimaryNav,
				activeCockpitModule,
				activeProjectSection,
				activeBoardSpace,
				activeDssPage,
				activeInsightView,
			}),
		[
			activePrimaryNav,
			activeCockpitModule,
			activeProjectSection,
			activeBoardSpace,
			activeDssPage,
			activeInsightView,
		]
	);

	useEffect(() => {
		if (sceneExpertPerspectiveOptions.includes(activeExpertPerspective)) return;
		setActiveExpertPerspective(sceneExpertPerspectiveOptions[0]);
	}, [sceneExpertPerspectiveOptions, activeExpertPerspective]);
	const activeAdvisorConversationKey = buildAdvisorConversationKey({
		sessionId,
		sceneKey: advisorSceneContext.key,
	});
	const conversationMessages = getAdvisorConversationMessages({
		messagesByScene: conversationMessagesByScene,
		activeKey: activeAdvisorConversationKey,
		emptyFallback: EMPTY_CHAT_MESSAGES,
	});
	const setConversationMessages = useCallback(
		(updater: React.SetStateAction<ChatMessage[]>) => {
			setConversationMessagesByScene((prev) =>
				updateAdvisorConversationMessages({
					messagesByScene: prev,
					activeKey: activeAdvisorConversationKey,
					updater,
				})
			);
		},
		[activeAdvisorConversationKey]
	);
	const leftPanelWidth = isLeftCollapsed
		? '0px'
		: isRightCollapsed
		? 'calc(100% - 32px)'
		: activeSplitLeftPanelWidth;
	const advisorHistoryGroups = useMemo(() => {
		return groupAdvisorHistoryRecords({ records: advisorHistoryRecords });
	}, [advisorHistoryRecords]);

	useEffect(() => {
		if (layoutMode === 'left-focus') {
			setSelectedNode(null);
		}
	}, [layoutMode]);

	const lastAdvisorSceneRef = useRef<string>('');
	useEffect(() => {
		if (!advisorSceneContext.key || lastAdvisorSceneRef.current === advisorSceneContext.key) return;
		lastAdvisorSceneRef.current = advisorSceneContext.key;

		setCockpitContextRefs((prev) => {
			if (prev.includes(advisorSceneContext.sceneRef)) return prev;
			const next = [...prev, advisorSceneContext.sceneRef];
			return next.length > 5 ? next.slice(next.length - 5) : next;
		});

		if (systemMode === 'conversation') {
			return;
		}

		setProjectInputValue((prev) => {
			const token = `@${advisorSceneContext.sceneRef}`;
			if (prev.includes(token)) return prev;
			return `${prev} ${token}`.trim();
		});
	}, [advisorSceneContext, systemMode]);

	useEffect(() => {
		setLayoutMode('split');
		setAdvisorHistoryOpen(false);
	}, [sessionId]);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		const updateViewportMetrics = () => {
			setViewportWidth(window.innerWidth);
		};

		updateViewportMetrics();
		window.addEventListener('resize', updateViewportMetrics);
		window.addEventListener('orientationchange', updateViewportMetrics);
		return () => {
			window.removeEventListener('resize', updateViewportMetrics);
			window.removeEventListener('orientationchange', updateViewportMetrics);
		};
	}, []);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		const restored = restoreAdvisorHistoryRecords({
			storage: window.localStorage,
			onError: (error) => console.error('[analysis] failed to restore advisor history:', error),
		});
		if (restored.length > 0) setAdvisorHistoryRecords(restored);
	}, []);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		const restored = restoreAdvisorConversationMessages({
			storage: window.localStorage,
			onError: (error) => console.error('[analysis] failed to restore advisor conversations:', error),
		});
		if (restored) setConversationMessagesByScene(restored);
	}, []);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		persistAdvisorHistoryRecords({
			storage: window.localStorage,
			records: advisorHistoryRecords,
			onError: (error) => console.error('[analysis] failed to persist advisor history:', error),
		});
	}, [advisorHistoryRecords]);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		persistAdvisorConversationMessages({
			storage: window.localStorage,
			messagesByScene: conversationMessagesByScene,
			onError: (error) => console.error('[analysis] failed to persist advisor conversations:', error),
		});
	}, [conversationMessagesByScene]);

	useEffect(() => {
		const nextTitle = deriveAdvisorHistoryTitle({
			userInput,
			messages: conversationMessages,
		});
		if (!nextTitle) return;

		setAdvisorHistoryRecords((prev) => {
			return upsertAdvisorHistoryRecord({
				records: prev,
				sessionId,
				title: nextTitle,
				systemMode,
			});
		});
	}, [conversationMessages, sessionId, systemMode, userInput]);

	useEffect(() => {
		if (isRightCollapsed) {
			setAdvisorHistoryOpen(false);
		}
	}, [isRightCollapsed]);

	const navigateToReport = useCallback(() => {
		if (hasRedirectedRef.current) {
			return;
		}
		hasRedirectedRef.current = true;
		router.push(`/report/${sessionId}`);
	}, [router, sessionId]);

    // 图谱：当 userInput 加载后摄入用户任务书文本，提取概念词条
    useEffect(() => {
        if (userInput) { ingestGraphText(userInput); broadcastGraphState(); }
    }, [userInput, ingestGraphText, broadcastGraphState]);
	// 统一 interrupt 类型分发，所有 interrupt_data 处理均走此函数
	const applyInterruptDispatch = useCallback((interruptData: any) => {
		if (!interruptData) return;
		// 后端发来 interrupt 意味着项目分析正在进行，切到项目态
		setSystemMode('project');
		const type = interruptData.interaction_type;
		if (type === 'calibration_questionnaire') {
			setQuestionnaireData(interruptData.questionnaire);
			setShowQuestionnaire(true);
			console.log('📋 [interrupt dispatch] calibration_questionnaire');
		} else if (type === 'role_and_task_unified_review') {
			// 防回归守卫：requirements_pre_director 是已废弃的占位审核，自动批准跳过
			if (interruptData.review_scope === 'requirements_pre_director') {
				console.warn('⚠️ [interrupt dispatch] 收到废弃的 requirements_pre_director 占位审核，自动批准跳过');
				api.resumeAnalysis(sessionId, 'approve').catch((err: any) => {
					console.error('❌ 自动批准 requirements_pre_director 失败:', err);
				});
				return;
			}
			// 始终关闭问卷 Modal（Step 5 骨架屏可能仍在显示）
			setCurrentProgressiveStep(0);
			setProgressiveStepData(null);
			setRoleTaskReviewData(interruptData);
			setShowRoleTaskReview(true);
			console.log('📋 [interrupt dispatch] role_and_task_unified_review');
		} else if (type === 'user_question') {
			setUserQuestionData(interruptData);
			setShowUserQuestion(true);
			console.log('📋 [interrupt dispatch] user_question');
		} else if (type === 'batch_confirmation') {
			// 自动批准批次，无需用户交互
			console.log('📦 [interrupt dispatch] batch_confirmation - 自动批准');
			api.resumeAnalysis(sessionId, 'approve').catch((err: any) => {
				console.error('❌ 自动批准批次失败:', err);
			});
		} else if (type === 'progressive_questionnaire_step1') {
			setProgressiveStepData(interruptData);
			setCurrentProgressiveStep(2);
			// 🔄 v10.2 Path B: output_intent 由 stepData 携带，Modal 自行判断是否展示 Step 1
			console.log('📋 [interrupt dispatch] progressive_step1 → step2', interruptData.output_intent ? '(含输出意图)' : '');
		} else if (type === 'progressive_questionnaire_step2') {
			setProgressiveStepData(interruptData);
			setCurrentProgressiveStep(3);
			console.log('📋 [interrupt dispatch] progressive_step2 → step3');
		} else if (type === 'progressive_questionnaire_step3') {
			setProgressiveStepData(interruptData);
			setCurrentProgressiveStep(4);
			console.log('📋 [interrupt dispatch] progressive_step3 → step4');
		} else if (type === 'progressive_questionnaire_step4' || type === 'requirements_insight') {
			setProgressiveStepData(interruptData);
			setCurrentProgressiveStep(5);
			console.log('📋 [interrupt dispatch] progressive_step4 / requirements_insight → step5');
		} else if (type === 'quality_preflight_warning') {
			setQualityPreflightData(interruptData);
			setShowQualityPreflight(true);
			console.log('⚠️ [interrupt dispatch] quality_preflight_warning');
		} else if (type === 'output_intent_confirmation') {
			// 🆕 v11.0: Step1 独立 interrupt，设置到 progressive step 1
			console.log('🎯 [interrupt dispatch] output_intent_confirmation → step1');
			setProgressiveStepData(interruptData);
			setCurrentProgressiveStep(1);
		} else {
			// 兜底：未知类型，展示通用确认框避免静默卡死
			console.warn('⚠️ [interrupt dispatch] 未知 interrupt 类型，走兜底确认:', type);
			setConfirmationData(interruptData);
			setShowConfirmation(true);
		}
	}, [sessionId]);

	// 使用 WebSocket 实时更新状态
	useEffect(() => {
		if (isDemoSession) {
			setSystemMode('project');
			setStatus(null);
			setError(null);
			setWsConnected(false);
			return;
		}

			const fetchInitialStatus = async (retryCount = 0) => {
				if (sessionId.startsWith('conv-')) {
					setSystemMode('conversation');
					setStatus(null);
					await bootstrapConversationSession({
						sessionId,
						storage: sessionStorage,
						getStatus: api.getStatus,
						onInitialMessages: setConversationMessages,
						onRestoredMessages: setConversationMessages,
						onRestoreError: (err) => console.warn('[analysis] restore conversation history failed:', err),
					});
					return;
				}

			try {
				console.log(`🔍 开始获取初始状态 (尝试 ${retryCount + 1}/3), sessionId:`, sessionId);
				const data = await api.getStatus(sessionId);
				console.log('✅ 获取初始状态成功:', data);

				// ── 方案三：后端状态驱动，彻底移除 localStorage 时间戳阻断 ──
				// waiting_for_input / completed / failed → 直接用后端真实状态渲染，无需检测新旧
				// running → 方案一（forceResume flag）优先；否则方案二（10分钟兜底）

				// 方案一：用户主动点击"尝试继续执行"时设置的 flag，绕过所有超时检测
				const forceResume = sessionStorage.getItem(`force_resume_${sessionId}`);
				if (forceResume) {
					sessionStorage.removeItem(`force_resume_${sessionId}`);
					console.log('🔄 forceResume flag 生效，跳过旧会话检测，直接恢复');
				}

				const isWaitingInput = data.status === 'waiting_for_input';
				const isRunning = data.status === 'running';

				// waiting_for_input / completed / failed：直接渲染，无需检测
				if (!isRunning || forceResume || isWaitingInput) {
					if (isWaitingInput) console.log('🔄 恢复交互界面:', data.interrupt_data?.interaction_type);
					// 继续执行，setStatus(data) 正常渲染
				}
				setStatus(data);
				// 若会话已在运行/等待/完成，说明是项目分析任务，切到项目态
					if (data.status === 'running' || data.status === 'waiting_for_input' || data.status === 'completed') {
						setSystemMode('project');
					}

					if (data.history && data.history.length > 0) {
					console.log('📜 恢复执行历史:', data.history);
					setNodeHistory(data.history);

					const details: Record<string, { status: NodeStatus; detail?: string }> = {};
					data.history.forEach((entry) => {
						details[entry.node] = {
							status: 'completed',
							detail: entry.detail
						};
					});

					if (data.current_stage && (data.status === 'running' || data.status === 'waiting_for_input')) {
						details[data.current_stage] = {
							status: 'running',
							detail: data.detail
						};
					}

					setNodeDetails((prev) => ({ ...prev, ...details }));
				}

				if (data.status === 'waiting_for_input' && data.interrupt_data) {
					console.log('🔄 恢复 interrupt UI:', data.interrupt_data?.interaction_type);
					applyInterruptDispatch(data.interrupt_data);
				}

					if (data.status === 'completed') {
						console.log('✅ 检测到会话已完成');
					}
				} catch (err: any) {
					// 🔥 检测是否为追问会话
					const isFollowupSession = sessionId.includes('-followup-');
					console.error(`获取初始状态失败 (尝试 ${retryCount + 1}/3):`, err);				// 🔧 修复：对于 404 错误，如果是追问会话且重试次数少于3，则重试
				if (err?.response?.status === 404 && sessionId.includes('-followup-') && retryCount < 2) {
					console.log(`⏳ 追问会话可能还在创建中，2秒后重试...`);
					setTimeout(() => {
						fetchInitialStatus(retryCount + 1);
					}, 2000);
					return;
				}

					if (err?.response?.status === 404 && sessionId.startsWith('conv-')) {
						// 对话态会话：保持 conversation 模式，并恢复初始对话（兜底路径）
						console.log('🗨️ 对话态会话，跳过旧状态接口，保持 conversation 模式');
						setSystemMode('conversation');
						await bootstrapConversationSession({
							sessionId,
							storage: sessionStorage,
							getStatus: api.getStatus,
							onInitialMessages: setConversationMessages,
							onRestoredMessages: setConversationMessages,
							onRestoreError: (restoreErr) => console.warn('[analysis] restore conversation history failed:', restoreErr),
						});
						return;
					} else if (err?.response?.status === 404) {
					setError('会话已过期或不存在，请重新开始分析');
				} else if (err?.response?.status === 410) {
					setError('工作流已失效，请重新开始分析');
				} else if (err?.response?.status === 500) {
					setError('服务器内部错误，请稍后重试');
				} else if (err?.message?.includes('Network Error') || err?.message?.includes('timeout')) {
					setError('网络连接失败，请检查后端服务是否运行');
				} else {
					setError(err?.response?.data?.detail || err.message || '获取会话状态失败');
				}
			}
		};

		fetchInitialStatus();

		// 🔥 检测是否为追问会话（用于显示友好文案）
		const isFollowupSession = sessionId.includes('-followup-');

		const wsUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';
		console.log('🔌 准备连接 WebSocket:', { wsUrl, sessionId, isFollowup: isFollowupSession });

		wsClientRef.current = new WebSocketClient({
			url: wsUrl,
			sessionId,
			onOpen: async () => {
				// 对话态会话（conv-xxx）不走旧状态接口
				if (sessionId.startsWith('conv-')) {
					console.log('🗨️ 对话态会话 WS 连接，跳过旧状态同步');
					return;
				}
				// 🔧 v7.118: 重连后同步最新状态并恢复 interrupt UI
				console.log('✅ WebSocket 已连接，同步最新状态...');
				try {
					const response = await api.getStatus(sessionId);
					if (response) {
						setStatus({
							session_id: sessionId,
							status: response.status,
							progress: response.progress ?? 0,
							error: response.error,
							current_stage: response.current_stage,
							detail: response.detail,
							interrupt_data: response.interrupt_data
						});
						console.log('✅ 状态同步完成:', response);
						// 重连后恢复 interrupt UI
						if (response.status === 'waiting_for_input' && response.interrupt_data) {
							console.log('🔄 重连后恢复 interrupt UI:', response.interrupt_data?.interaction_type);
							applyInterruptDispatch(response.interrupt_data);
						}
					}
				} catch (error) {
					console.error('⚠️ 状态同步失败:', error);
				}
			},
			onMessage: (message: WebSocketMessage) => {
				console.log('📩 收到 WebSocket 消息 [' + message.type + ']:', message);				switch (message.type) {
					case 'initial_status':
						setStatus((prev) => ({
							...prev!,
							status: message.status as SessionStatus,
							progress: message.progress,
							current_stage: message.current_node || prev?.current_stage,
							detail: message.detail || prev?.detail
						}));
						setWsConnected(true);
						break;

					case 'status_update':
						console.log('📨 收到状态更新:', message);
						setStatus((prev) => {
							// 🔥 防止进度回退：只有新进度 ≥ 旧进度时才更新
							const newProgress = message.progress;
							const oldProgress = prev?.progress ?? 0;
							const validatedProgress = newProgress !== undefined && newProgress >= oldProgress
								? newProgress
								: oldProgress;

							if (newProgress !== undefined && newProgress < oldProgress) {
								console.warn(`⚠️ [status_update] 检测到进度回退: ${Math.round(oldProgress * 100)}% → ${Math.round(newProgress * 100)}%，已忽略`);
							}

							return {
								...prev!,
								status: message.status as SessionStatus,
								progress: validatedProgress,
								error: message.error,
								rejection_message: message.rejection_message,
								final_report: message.final_report,
								current_stage: message.current_node || prev?.current_stage,
								// 🔥 状态对齐修复: || 替代 ??，空字符串也回退到之前有效值
								detail: message.detail || prev?.detail
							};
						});

						if (message.current_node) {
							const currentNode = message.current_node;
							setNodeDetails((prev) => {
								const updated = { ...prev };
								Object.keys(updated).forEach((key) => {
									if (key !== currentNode && updated[key].status === 'running') {
										updated[key] = { ...updated[key], status: 'completed' };
									}
								});

							const previousDetail = updated[currentNode]?.detail;
							updated[currentNode] = {
								status: message.status === 'completed' ? 'completed' : 'running',
								detail: message.detail ?? previousDetail
							};
							return updated;
						});

						setNodeHistory((prev) => {
							const lastEntry = prev[prev.length - 1];
							if (lastEntry?.node === currentNode) {
								return prev;
							}
							// 🆕 P3修复: 限制历史记录最多100条，避免内存溢出
							const newHistory = [
								...prev,
								{
									node: currentNode,
									detail: message.detail || '',
									time: new Date().toLocaleTimeString()
								}
							];
							return newHistory.length > 100 ? newHistory.slice(-100) : newHistory;
						});
					}

						if (message.status === 'completed') {
							console.log('✅ 分析完成！');
							setStatus((prev) => ({
								...prev!,
								current_stage: 'completed',
								detail: '分析完成'
							}));

							setNodeDetails((prev) => {
								const updated = { ...prev };
								Object.keys(updated).forEach((key) => {
									updated[key] = { ...updated[key], status: 'completed' };
								});
								return updated;
							});
						}

						if (message.status === 'failed') {
							console.error('❌ 分析失败:', message.error);
						}
						break;

					case 'status':
					console.log('📨 收到 status 消息:', message);
					setStatus((prev) => {
						// 防止进度回退：只有新进度≥旧进度时才更新
						const newProgress = (message as any).progress;
						const oldProgress = prev?.progress ?? 0;
						const validatedProgress = newProgress !== undefined && newProgress >= oldProgress
							? newProgress
							: oldProgress;

						if (newProgress !== undefined && newProgress < oldProgress) {
							console.warn(`⚠️ 检测到进度回退: ${oldProgress} → ${newProgress}，已忽略`);
						}

						return {
							...prev!,
							status: (message as any).status as SessionStatus,
							progress: validatedProgress,
							error: (message as any).error,
							final_report: (message as any).final_report
						};
					});						if ((message as any).status === 'completed') {
							console.log('✅ 分析完成！进度 100%');
							setStatus((prev) => ({
								...prev!,
								progress: 1.0,
								current_stage: 'completed',
								detail: '分析完成'
							}));
						}
						break;

					case 'node_update':
						// ✅ 统一使用 current_node 字段，兼容旧的 node_name
						const nodeName = message.current_node || message.node_name;
						if (!nodeName) {
							console.warn('⚠️ 节点更新缺少节点名称，已忽略');
							break;
						}
						console.log('📊 节点更新:', nodeName, '-', message.detail);
						setStatus((prev) => ({
							...prev!,
							current_stage: nodeName,
							detail: message.detail,
							status: 'running'
						}));

						setNodeDetails((prev) => {
							const updated = { ...prev };
							Object.keys(updated).forEach((key) => {
								if (key !== nodeName && updated[key].status === 'running') {
									updated[key] = { ...updated[key], status: 'completed' };
								}
							});

							const previousDetail = updated[nodeName]?.detail;
							updated[nodeName] = {
								status: 'running',
								detail: message.detail || previousDetail
							};

							return updated;
						});

						setNodeHistory((prev) => [
							...prev,
							{
								node: nodeName,
								detail: message.detail,
								time: new Date(message.timestamp).toLocaleTimeString()
							}
						]);
						// node_update.detail 是流程状态字符串，不质入图谱（会引入「游朿」「分析」等污染词）
						break;

						case 'interrupt':
						setStatus((prev) => ({
							...prev!,
							status: message.status as SessionStatus,
							interrupt_data: message.interrupt_data
						}));
						applyInterruptDispatch(message.interrupt_data);
						// 图谱：从结构化 interrupt 数据中提取待确认概念节点
						if (message.interrupt_data) {
							const interruptConcepts = extractConceptsFromInterruptData(message.interrupt_data);
							interruptConcepts.forEach((c) => promoteToPending(c.id, c));
							// 同时将 interrupt 富文本（突破洞察 + 张力 + 已识别维度）质入图谱
							const id = message.interrupt_data as any;
							const textParts: string[] = [];
							const insight = id?.requirements_review?.breakthrough_insight;
							if (insight) textParts.push(String(insight));
							const tensions: any[] = Array.isArray(id?.core_tensions) ? id.core_tensions : [];
							tensions.forEach((t: any) => {
								const name = typeof t === 'string' ? t : (t?.name ?? t?.tension ?? '');
								if (name) textParts.push(String(name));
							});
							const dims: any[] = Array.isArray(id?.already_identified) ? id.already_identified : [];
							dims.forEach((d: any) => {
								const label = typeof d === 'string' ? d : (d?.name ?? d?.dimension ?? '');
								if (label) textParts.push(String(label));
							});
							if (textParts.length > 0) { ingestGraphText(textParts.join('。')); broadcastGraphState(); }

							// Observer Intelligence Layer：异步调用，不阻塞主流程
							const _capturedSessionId = sessionId;
							const _capturedInterruptData = message.interrupt_data;
							const _capturedStage = (message.interrupt_data as any)?.interaction_type ?? 'interrupt';
							;(async () => {
								try {
									const res = await fetch(`/api/sessions/${_capturedSessionId}/observe`, {
										method: 'POST',
										headers: { 'Content-Type': 'application/json' },
										body: JSON.stringify({
											interrupt_data: _capturedInterruptData,
											stage: _capturedStage,
										}),
									});
									if (res.ok) {
										const result: ObserverResult = await res.json();
										ingestObserverResult(result);
										broadcastGraphState();
										console.log('[Observer] 图谱已更新 nodes=', result.nodes.length, 'insight=', result.main_insight?.slice(0, 60));
									}
								} catch (err) {
									console.warn('[Observer] observe 调用失败，降级继续', err);
								}
							})();
						}
						break;

					case 'tool_permissions_initialized':
						// 🆕 v7.129 Week2 P1: 工具权限初始化通知
						console.log('🔧 收到工具权限初始化消息:', message);

						// 显示toast通知用户工具权限已配置
						import('sonner').then(({ toast }) => {
							// 统计启用搜索的角色数量
							const toolSettings = message.tool_settings || {};
							const rolesWithSearch = Object.entries(toolSettings)
								.filter(([_, settings]: [string, any]) => settings.enable_search)
								.map(([roleType, _]) => roleType);

							const allRoles = Object.keys(toolSettings);

							toast.success(
								`工具权限系统已初始化`,
								{
									description: `已配置 ${allRoles.length} 个角色，其中 ${rolesWithSearch.length} 个角色启用搜索工具 (${rolesWithSearch.join(', ')})`,
									duration: 5000,
								}
							);

							console.log('📡 工具权限配置:', {
								allRoles,
								rolesWithSearch,
								settings: toolSettings
							});
						});
						break;

					// v2.0 双态架构事件
					case 'dual_mode_upgrade_signal':
						setUpgradeIndicators(message.indicators);
						setUpgradeSuggestionText(message.suggestion_text);
						if (message.triggered) setShowUpgradeBanner(true);
						break;
					case 'dual_mode_mode_change':
						setSystemMode(message.to_mode);
						break;
					case 'dual_mode_draft_saved':
						console.log('[dual_mode] draft_saved:', message.draft_type, message.draft_summary);
						break;
					case 'dual_mode_gate_result':
						console.log('[dual_mode] gate_result:', message.gate_status);
						break;
					case 'dual_mode_delta_routed':
						console.log('[dual_mode] delta_routed:', message.route);
						break;
				}
			},
			onError: (event) => {
				console.error('❌ WebSocket 错误:', event);
				setWsConnected(false);
			},
			onClose: () => {
				console.log('🔌 WebSocket 连接关闭');
				setWsConnected(false);
			}
		});

		wsClientRef.current.connect();

		return () => {
			wsClientRef.current?.close();
		};
	}, [isDemoSession, navigateToReport, sessionId]);

	const handleNodeClick = (nodeId: string) => {
		setSelectedNode(nodeId);
	};

	const closeNodeDetail = () => {
		setSelectedNode(null);
	};

	const handleCycleLayoutMode = useCallback(() => {
		setLayoutMode((prev) => (prev === 'split' ? 'left-focus' : 'split'));
	}, []);

	const handlePrimaryNavChange = useCallback((nav: PrimaryNavKey) => {
		if (nav === 'assets') {
			setActiveProjectSection('space');
			setActiveCockpitModule('assets');
			return;
		}
		if (nav === 'knowledge') {
			setActiveProjectSection('space');
			setActiveCockpitModule('knowledge');
			return;
		}
		setActiveProjectSection('space');
		setActiveCockpitModule('files');
	}, []);

	const handleOpenGeoWorkspace = useCallback(() => {
		setActiveProjectSection('space');
		setActiveCockpitModule('geo');
	}, []);

	const handleProjectSectionChange = useCallback((section: ProjectSectionKey) => {
		setActiveProjectSection(section);
		if (section === 'sandbox') {
			if (activeBoardSpace === '全部') {
				setActiveBoardSpace(projectDefaultSpace);
			}
			setActiveCockpitModule('files');
			return;
		}
		if (section === 'board') {
			setActiveCockpitModule('board');
			return;
		}
		setActiveCockpitModule('files');
	}, [activeBoardSpace, projectDefaultSpace]);

	const handleEnterBoardSpace = useCallback((space: Exclude<BoardCanvasSpace, '全部'>) => {
		setActiveProjectSection('board');
		setActiveCockpitModule('board');
		setActiveBoardSpace(space);
	}, []);

	const handleEnterSandboxSpace = useCallback((space: Exclude<BoardCanvasSpace, '全部'>) => {
		setActiveProjectSection('sandbox');
		setActiveCockpitModule('files');
		setActiveBoardSpace(space);
	}, []);

	const handleSandboxSpaceChange = useCallback((space: Exclude<BoardCanvasSpace, '全部'>) => {
		setActiveBoardSpace(space);
	}, []);

	useEffect(() => {
		const moduleParam = searchParams.get('module') ?? '';
		const requestedModule = parseAnalysisModuleQuery(moduleParam);
		if (!requestedModule || appliedInitialModuleRef.current === moduleParam) return;

		appliedInitialModuleRef.current = moduleParam;
		setSystemMode('project');

		if (requestedModule === 'project_base') {
			setActiveProjectSection('space');
			setActiveCockpitModule('files');
			return;
		}

		if (requestedModule === 'floor_plan') {
			handleEnterSandboxSpace(projectDefaultSpace);
			return;
		}

		if (requestedModule === 'scheme_canvas') {
			handleEnterBoardSpace(projectDefaultSpace);
			return;
		}

		if (requestedModule === 'geo') {
			handleOpenGeoWorkspace();
			return;
		}

		setActiveProjectSection('space');
		setActiveCockpitModule('knowledge');
		setActiveDssPage('sediment');
	}, [
		handleEnterBoardSpace,
		handleEnterSandboxSpace,
		handleOpenGeoWorkspace,
		projectDefaultSpace,
		searchParams,
	]);

	const injectReferenceToRight = useCallback((label: string) => {
		const token = `@${label}`;
		setCockpitContextRefs((prev) => {
			if (prev.includes(label)) return prev;
			const next = [...prev, label];
			return next.length > 5 ? next.slice(next.length - 5) : next;
		});

		if (systemMode === 'conversation') {
			setConversationPrefill({ id: Date.now(), text: token });
			return;
		}

		setProjectInputValue((prev) => {
			if (prev.includes(token)) return prev;
			return `${prev} ${token}`.trim();
		});
	}, [systemMode]);

		const handleSummonExpert = useCallback(
			(target: (typeof EXPERT_SUMMON_OPTIONS)[number]) => {
				injectReferenceToRight(target === '召集全部' ? '@召集团队：全体专家' : `@召集团队：${target}`);
			},
			[injectReferenceToRight]
		);

	const removeReference = useCallback((label: string) => {
		setCockpitContextRefs((prev) => prev.filter((item) => item !== label));
		const token = `@${label}`;
		setProjectInputValue((prev) => prev.replace(token, '').replace(/\s+/g, ' ').trim());
	}, []);

	const handleQuestionnaireSubmit = async (answers: any) => {
		try {
			await api.resumeAnalysis(sessionId, JSON.stringify(answers));
			setShowQuestionnaire(false);
			setQuestionnaireData(null);
			console.log('✅ 问卷已提交');
		} catch (err: any) {
			console.error('❌ 问卷提交失败:', err);
			if (err?.response?.status === 410) {
				alert('工作流已失效，请重新开始分析');
				router.push('/');
			} else {
				alert('问卷提交失败,请重试');
			}
		}
	};

	const handleQuestionnaireSkip = async () => {
		try {
			await api.resumeAnalysis(sessionId, 'skip');
			setShowQuestionnaire(false);
			setQuestionnaireData(null);
			console.log('⏭️ 已跳过问卷');
		} catch (err: any) {
			console.error('❌ 跳过问卷失败:', err);
			if (err?.response?.status === 410) {
				alert('工作流已失效，请重新开始分析');
				router.push('/');
			} else {
				alert('操作失败,请重试');
			}
		}
	};

	const handleConfirmation = async (editedData?: any) => {
		try {
			console.log('🚀 开始提交确认...', editedData);

			let payload: any;

			if (editedData && Array.isArray(editedData)) {
				const modifications: Record<string, string> = {};
				const originalSummary = confirmationData?.requirements_summary || [];

				editedData.forEach((editedItem: any, index: number) => {
					const originalItem = originalSummary[index];
					if (originalItem) {
						if (editedItem.label !== originalItem.label) {
							console.log(`📝 检测到标签修改: ${originalItem.key}`);
						}
						const originalContent = (originalItem.content || '').trim();
						const editedContent = (editedItem.content || '').trim();
						if (editedContent !== originalContent) {
							modifications[editedItem.key || originalItem.key] = editedContent;
							console.log(`📝 检测到内容修改: ${editedItem.key || originalItem.key}`);
						}
					}
				});

				if (Object.keys(modifications).length > 0) {
					payload = {
						intent: 'approve',
						modifications
					};
					console.log(`📝 提交 ${Object.keys(modifications).length} 个字段修改`);
				} else {
					payload = 'confirm';
					console.log('✅ 未检测到修改，直接确认');
				}
			} else {
				payload = 'confirm';
			}

			await api.resumeAnalysis(sessionId, payload);
			setShowConfirmation(false);
			setConfirmationData(null);

			const lastNode = nodeHistory.length > 0 ? nodeHistory[nodeHistory.length - 1].node : null;
			const processingText = lastNode ? `${formatNodeName(lastNode)} (处理中...)` : '工作流继续执行中...';

			setStatus((prev) => ({
				...prev!,
				status: 'running' as SessionStatus,
				detail: payload !== 'confirm' ? '正在根据您的修改重新分析...' : processingText
			}));

			console.log('✅ 确认完成,工作流继续执行');
		} catch (err) {
			console.error('❌ 确认失败:', err);
			alert('确认失败,请重试');
		}
	};

	const handleRoleTaskReview = async (action: string, modifications?: any) => {
		try {
			console.log('🚀 开始提交任务审批...', { action, modifications });

			let payload: any;

			if (action === 'modify_tasks' && modifications && Object.keys(modifications).length > 0) {
				// 修改任务分配
				payload = {
					action: 'modify_tasks',
					modifications
				};
				console.log(`📝 提交 ${Object.keys(modifications).length} 个角色的任务修改`);
			} else if (action === 'modify_roles') {
				// 请求重新拆分项目
				payload = {
					action: 'modify_roles'
				};
				console.log('🔄 请求重新拆分项目');
			} else if (action === 'approve') {
				// 直接批准，无修改
				payload = {
					action: 'approve'
				};
				console.log('✅ 批准项目拆分和任务分配');
			} else if (action === 'edit_deliverables' && modifications) {
				// v15.1: 编辑交付物工作包
				payload = {
					action: 'edit_deliverables',
					work_packages: modifications
				};
				console.log(`📦 提交 ${Array.isArray(modifications) ? modifications.length : 0} 个交付物工作包编辑`);
			} else {
				// 其他动作
				payload = { action };
				console.log(`📤 提交动作: ${action}`);
			}

			await api.resumeAnalysis(sessionId, payload);
			setShowRoleTaskReview(false);
			setRoleTaskReviewData(null);

			const lastNode = nodeHistory.length > 0 ? nodeHistory[nodeHistory.length - 1].node : null;
			const processingText =
				action === 'modify_roles'
					? '正在重新拆分项目...'
					: action === 'edit_deliverables'
					? '正在根据您的修改更新交付物工作包...'
					: action === 'modify_tasks'
					? '正在根据您的修改重新分配任务...'
					: lastNode
					? `${formatNodeName(lastNode)} (处理中...)`
					: '工作流继续执行中...';

			setStatus((prev) => ({
				...prev!,
				status: 'running' as SessionStatus,
				detail: processingText
			}));

			console.log('✅ 任务审批完成,工作流继续执行');
		} catch (err) {
			console.error('❌ 任务审批失败:', err);
			alert('审批失败,请重试');
		}
	};

	const handleUserQuestionSubmit = async ({ question, requiresAnalysis }: { question: string; requiresAnalysis: boolean }) => {
		try {
			setUserQuestionSubmitting(true);
			const payload = {
				question: question.trim(),
				requires_analysis: requiresAnalysis
			};
			await api.resumeAnalysis(sessionId, payload);
			setShowUserQuestion(false);
			setUserQuestionData(null);
			setStatus((prev) => (prev
				? {
						...prev,
						status: 'running' as SessionStatus,
						detail: '继续处理用户追问...',
						interrupt_data: null
				  }
				: null
			));
			console.log('✅ 用户追问提交成功');
		} catch (err) {
			console.error('❌ 追问提交失败:', err);
			alert('提交失败，请重试');
		} finally {
			setUserQuestionSubmitting(false);
		}
	};

	const handleUserQuestionSkip = async () => {
		try {
			await api.resumeAnalysis(sessionId, { skip: true });
			setShowUserQuestion(false);
			setUserQuestionData(null);
			setStatus((prev) => (prev ? { ...prev, status: 'running' as SessionStatus } : null));
			console.log('✅ 跳过用户追问');
		} catch (err) {
			console.error('❌ 跳过失败:', err);
			alert('跳过失败，请重试');
		}
	};

	// 🆕 v7.119: 质量预检处理函数
	const handleQualityPreflightConfirm = async () => {
		try {
			console.log('✅ 用户确认继续执行高风险任务');
			await api.resumeAnalysis(sessionId, { action: 'approve' });
			setShowQualityPreflight(false);
			setQualityPreflightData(null);

			setStatus((prev) => ({
				...prev!,
				status: 'running' as SessionStatus,
				detail: '专家团队开始执行分析...'
			}));

			console.log('✅ 质量预检确认完成，工作流继续执行');
		} catch (err) {
			console.error('❌ 质量预检确认失败:', err);
			alert('确认失败，请重试');
		}
	};

	const handleQualityPreflightCancel = async () => {
		try {
			console.log('❌ 用户取消执行，请求修改需求');
			await api.resumeAnalysis(sessionId, { action: 'reject_and_revise' });
			setShowQualityPreflight(false);
			setQualityPreflightData(null);

			setStatus((prev) => ({
				...prev!,
				status: 'running' as SessionStatus,
				detail: '正在重新分析需求...'
			}));

			console.log('✅ 用户取消，工作流重新开始');
		} catch (err) {
			console.error('❌ 取消失败:', err);
			alert('取消失败，请重试');
		}
	};

	// 🆕 v7.130: 统一问卷处理函数
	const handleProgressiveStepConfirm = async (stepData?: any) => {
		const step = currentProgressiveStep;
		try {
			console.log(`✅ 第${step}步 - 用户确认:`, stepData);

			let payload: any = { action: 'confirm' };
			if (step === 1) {
				// 🆕 v11.0: output_intent_confirmation 步骤（Step1），直接将选择结果发送给后端
				payload = stepData ?? {};
				// 立即显示 Step 2（任务梳理）加载状态
				setCurrentProgressiveStep(2);
				setProgressiveStepData({
					isLoading: true,
					interaction_type: 'progressive_questionnaire_step1',
					step: 2,
					total_steps: 5,
					title: '任务梳理',
					message: '正在按您确认的意图生成任务列表...'
				});
			} else if (step === 2 && stepData?.extracted_tasks) {
				payload.confirmed_tasks = stepData.extracted_tasks;
			} else if (step === 3 && stepData?.answers) {
				payload.answers = stepData.answers;
			} else if (step === 4 && stepData?.dimension_values) {
				payload.dimension_values = stepData.dimension_values;
			}

			// 立即切屏：各步骤确认后立即跳到下一步骨架屏，不等待后端响应
			if (step === 2) {
				console.log('🚀 [UX优化] Step 2确认，立即显示Step 3（信息补全）加载状态');
				setCurrentProgressiveStep(3);
				setProgressiveStepData({
					isLoading: true,
					interaction_type: 'progressive_questionnaire_step2',
					step: 3,
					total_steps: 5,
					title: '信息补全',
					message: '正在分析缺失的信息项...'
				});
			} else if (step === 3) {
				console.log('🚀 [UX优化] Step 3确认，立即显示Step 4（偏好雷达图）加载状态');
				setCurrentProgressiveStep(4);
				setProgressiveStepData({
					isLoading: true,
					interaction_type: 'progressive_questionnaire_step3',
					step: 4,
					total_steps: 5,
					title: '偏好雷达图',
					message: '正在生成偏好维度...'
				});
			} else if (step === 4) {
				console.log('🚀 [UX优化] Step 4确认，立即显示Step 5（需求洞察）加载状态');
				setCurrentProgressiveStep(5);
				setProgressiveStepData({
					isLoading: true,
					interaction_type: 'progressive_questionnaire_step4',
					step: 5,
					total_steps: 5,
					title: '需求洞察',
					message: '正在生成需求洞察...'
				});
			} else if (step === 5) {
				console.log('🚀 [UX优化] Step 5确认，显示任务分配过渡状态');
				// step=6 > 5，stepper 中所有 5 步都标记为已完成（✓ + 绿色连接线）
				setCurrentProgressiveStep(6);
				setProgressiveStepData({
					isLoading: true,
					interaction_type: 'requirements_insight',
					step: 6,
					total_steps: 5,
					title: '任务分配',
					message: '需求洞察完成，正在分配专家角色和任务...'
				});
			}

			await api.resumeAnalysis(sessionId, payload);

			// 图谱：用户每次确认后，将所有 pending 概念升为 stable
			promoteAllPendingToStable();

			// 🔧 v7.130: 不关闭 Modal，让 WebSocket 消息自动触发下一步
			setStatus((prev) => ({
				...prev!,
				status: 'running' as SessionStatus,
				detail: '正在处理您的输入...'
			}));

			// 🔧 Step 5（需求洞察）确认后，保持骨架屏直到任务审批 interrupt 到达
			// 不关闭 Modal，由 applyInterruptDispatch 中 role_and_task_unified_review 统一关闭

			console.log(`✅ 第${step}步确认完成`);
		} catch (err) {
			console.error(`❌ 第${step}步确认失败:`, err);
			alert('确认失败,请重试');
			// API调用失败时回退原步骤，清除loading状态
			if (step === 2) {
				setCurrentProgressiveStep(2);
				setProgressiveStepData((prev: any) => ({ ...prev, isLoading: false }));
			} else if (step === 3) {
				setCurrentProgressiveStep(3);
				setProgressiveStepData((prev: any) => ({ ...prev, isLoading: false }));
			} else if (step === 4) {
				setCurrentProgressiveStep(4);
				setProgressiveStepData((prev: any) => ({ ...prev, isLoading: false }));
			} else if (step === 5) {
				setCurrentProgressiveStep(5);
				setProgressiveStepData((prev: any) => ({ ...prev, isLoading: false }));
			}
		}
	};

	const handleProgressiveStepSkip = async () => {
		const step = currentProgressiveStep;
		if (step === 3) return; // 信息补全阶段不允许跳过
		try {
			console.log(`⏭️ 第${step}步 - 用户选择跳过问卷`);
			await api.resumeAnalysis(sessionId, { action: 'skip' });
			setCurrentProgressiveStep(0);
			setProgressiveStepData(null);
			setStatus((prev) => ({
				...prev!,
				status: 'running' as SessionStatus,
				detail: '跳过问卷，继续分析流程...'
			}));
			console.log(`⏭️ 第${step}步跳过成功`);
		} catch (err) {
			console.error(`❌ 第${step}步跳过失败:`, err);
			alert('操作失败,请重试');
		}
	};

	// 🔄 v10.2 Path B: handleOutputIntentConfirm / handleOutputIntentSkip 已移除
	// 输出意图确认在 Modal 内部完成（本地切换），最终随 Step 1 一并提交

	// 断线状态轮询兜底：WebSocket 断连且会话 running/waiting_for_input 时作为安全网
	useEffect(() => {
		if (wsConnected) return; // WS 正常时不轮询
		const currentStatus = status?.status;
		if (currentStatus !== 'running' && currentStatus !== 'waiting_for_input') return;

		console.log('🔄 WebSocket 断连，开始轮询状态 (每 5s)');
		const timer = setInterval(async () => {
			try {
				const response = await api.getStatus(sessionId);
				if (!response) return;
				setStatus((prev) => (prev ? { ...prev, ...response } : response));
				if (response.status === 'waiting_for_input' && response.interrupt_data) {
					console.log('🔄 轮询发现 interrupt，恢复 UI:', response.interrupt_data?.interaction_type);
					applyInterruptDispatch(response.interrupt_data);
				}
				if (response.status === 'completed') {
					console.log('✅ 轮询检测到完成');
				}
			} catch (e) {
				console.warn('⚠️ 轮询失败:', e);
			}
		}, 5000);

		return () => clearInterval(timer);
	}, [wsConnected, status?.status, sessionId, applyInterruptDispatch, navigateToReport]);

	// 项目态：内容更新时自动滚动到底部
	useEffect(() => {
		if (systemMode !== 'project') return;
		projectChatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
	}, [systemMode, status?.status, nodeHistory.length, currentProgressiveStep, showConfirmation, showQuestionnaire, showRoleTaskReview, showQualityPreflight, showUserQuestion]);

	// v7.290: 移除侧边栏，独立分析体验

	const selectedNodeData = selectedNode ? nodeHistory.filter((h) => h.node === selectedNode) : [];
	const shouldShowBoardVisualBrief = activeCockpitModule === 'board' && activeBoardSpace !== '全部';
	const visualBriefChatContext = useMemo(() => {
		if (!shouldShowBoardVisualBrief || !activeBoardVisualBrief) return null;
		const disabled = new Set(activeBoardVisualBrief.disabledTags);
		const appliedTags = Array.from(
			new Set([
				...activeBoardVisualBrief.styleKeywords,
				...activeBoardVisualBrief.mustKeep,
				...activeBoardVisualBrief.materialKeywords,
				...activeBoardVisualBrief.lightingKeywords,
			])
		).filter((tag) => !disabled.has(tag));
		return {
			space: activeBoardVisualBrief.space,
			status: activeBoardVisualBrief.status,
			summary: activeBoardVisualBrief.summary,
			visualPrompt: activeBoardVisualBrief.visualPrompt,
			appliedTags,
			lockedTags: activeBoardVisualBrief.lockedTags.filter((tag) => !disabled.has(tag)),
			negativeConstraints: activeBoardVisualBrief.negativeConstraints.filter((tag) => !disabled.has(`避免:${tag}`)),
			customNote: activeBoardVisualBrief.customNote,
			sourceTitles: activeBoardVisualBrief.sourceRefs.map((ref) => ref.title),
		};
	}, [activeBoardVisualBrief, shouldShowBoardVisualBrief]);

	const updateActiveBoardVisualBriefPrompt = useCallback((prompt: string) => {
		setActiveBoardVisualBrief((prev) =>
			prev
				? {
						...prev,
						status: prev.status === 'locked' ? 'locked' : 'edited',
						visualPrompt: prompt,
				  }
				: prev
		);
	}, []);

	const updateActiveBoardVisualBriefNote = useCallback((note: string) => {
		setActiveBoardVisualBrief((prev) =>
			prev
				? {
						...prev,
						status: prev.status === 'locked' ? 'locked' : 'edited',
						customNote: note,
				  }
				: prev
		);
	}, []);

	// v2.0 对话态 handlers
	const handleConvSendMessage = useCallback(async (text: string) => {
		await sendConversationMessageAction({
			sessionId,
			text,
			systemMode,
			activeExpertPerspective,
			advisorSceneContext,
			boardVisualBriefPrompt: systemMode !== 'conversation' && shouldShowBoardVisualBrief && activeBoardVisualBrief
				? formatBoardVisualBriefForPrompt(activeBoardVisualBrief)
				: null,
			setMessages: setConversationMessages,
			sendConversationMessage: api.sendConversationMessage,
			setUpgradeIndicators,
			setUpgradeSuggestionText,
			setShowUpgradeBanner,
			onError: (err) => console.error('[conv] send failed:', err),
		});
	}, [activeBoardVisualBrief, activeExpertPerspective, advisorSceneContext, sessionId, shouldShowBoardVisualBrief, systemMode, setConversationMessages]);

	// v2.0 引导卡片响应 handler
	const handleConvCardResponse = useCallback(async (cardId: string, optionId?: string, freetext?: string, structuredResponse?: GuidanceCardStructuredResponse) => {
		await respondToGuidanceCardAction({
			sessionId,
			cardId,
			optionId,
			freetext,
			structuredResponse,
			systemMode,
			activeExpertPerspective,
			advisorSceneContext,
			setMessages: setConversationMessages,
			sendConversationMessage: api.sendConversationMessage,
			onError: (err) => console.error('[conv] card response failed:', err),
		});
	}, [activeExpertPerspective, advisorSceneContext, sessionId, systemMode, setConversationMessages]);

	const handleUpgradeConfirm = useCallback(async () => {
		try {
			await api.resumeAnalysis(sessionId, { action: 'upgrade_to_project' });
			setShowUpgradeBanner(false);
			setSystemMode('project');
			setCurrentProgressiveStep(1);
		} catch (err) {
			console.error('[dual_mode] upgrade failed:', err);
		}
	}, [sessionId]);

	const handleAdvisorChipAction = useCallback((chip: ActionChip) => {
		if (chip.type === 'navigate') {
			console.log('[advisor] navigate chip:', chip.label);
		}
	}, []);

	const handleAdvisorAsk = useCallback((text: string) => {
		handleConvSendMessage(text);
	}, [handleConvSendMessage]);

	const collapsedReadableWidth = 'min(1180px, calc(100vw - 64px))';
	const rightPanelReadableWidth = isLeftCollapsed ? collapsedReadableWidth : '100%';
	const shellToggleButtonClass =
		'pointer-events-auto inline-flex h-8 w-8 items-center justify-center rounded-full bg-[#383838] text-white transition-colors duration-150 hover:bg-[#4a4a4a]';
	const shellToggleIconClass = 'h-[14px] w-[14px] shrink-0 translate-y-px';
	const layoutCycleMeta =
		layoutMode === 'split'
			? { label: '折叠方案高参', title: '折叠方案高参' }
			: { label: '展开方案高参', title: '展开方案高参' };

	if (systemMode === 'conversation') {
		return (
			<AppSessionShell
				isSidebarOpen={isSessionSidebarOpen}
				onSidebarOpenChange={setIsSessionSidebarOpen}
				sessions={sessions}
				currentSessionId={sessionId}
				sidebarNavigationMode="in-place"
				onRenameSession={handleRenameSession}
				onPinSession={handlePinSession}
				onShareSession={handleShareSession}
				onDeleteSession={handleDeleteSession}
				loadMoreTriggerRef={loadMoreTriggerRef}
				showExternalLink
			>
				<div className="min-h-0 flex-1">
					<ConversationChat
						sessionId={sessionId}
						messages={conversationMessages}
						advisorSceneContext={null}
						onSendMessage={handleConvSendMessage}
						loading={false}
						placeholder="继续补充项目目标、约束或取舍..."
						showUpgradeBanner={showUpgradeBanner}
						onUpgradeConfirm={handleUpgradeConfirm}
						onUpgradeDismiss={() => setShowUpgradeBanner(false)}
						onCardResponse={handleConvCardResponse}
						prefillHint={conversationPrefill}
						className="w-full"
					/>
				</div>
			</AppSessionShell>
		);
	}

	return (
		<AppSessionShell
			isSidebarOpen={isSessionSidebarOpen}
			onSidebarOpenChange={setIsSessionSidebarOpen}
			sessions={sessions}
			currentSessionId={sessionId}
			sidebarNavigationMode="in-place"
			onRenameSession={handleRenameSession}
			onPinSession={handlePinSession}
			onShareSession={handleShareSession}
			onDeleteSession={handleDeleteSession}
			loadMoreTriggerRef={loadMoreTriggerRef}
			showExternalLink
		>
		<div
			className="relative flex h-screen overflow-hidden bg-[var(--background)] text-[var(--foreground)]"
			style={workspaceColumnVars}
		>
			{!isRightCollapsed && (
				<div className="pointer-events-none absolute right-4 top-3 z-30">
					<button
						onClick={handleCycleLayoutMode}
						className={shellToggleButtonClass}
						title={layoutCycleMeta.title}
						aria-label={layoutCycleMeta.label}
					>
						<PanelLeft className={shellToggleIconClass} strokeWidth={2} />
					</button>
				</div>
			)}
			{layoutMode === 'split' && (
				<>
					{!isKnowledgeTwoColumnLayout && (
					<div
						role="separator"
						aria-orientation="vertical"
						aria-label="调整信息白板宽度"
						title="拖动调整信息白板宽度"
						className={`workspace-resize-divider ${resizingWorkspacePanel === 'middle' ? 'workspace-resize-divider-active' : ''}`}
						style={{ left: 'var(--workspace-main-column-width)' }}
						onPointerDown={handleWorkspaceResizeStart('middle')}
					/>
					)}
					<div
						role="separator"
						aria-orientation="vertical"
						aria-label="调整方案高参宽度"
						title="拖动调整方案高参宽度"
						className={`workspace-resize-divider ${resizingWorkspacePanel === 'advisor' ? 'workspace-resize-divider-active' : ''}`}
						style={{ left: 'var(--workspace-left-compound-width)' }}
						onPointerDown={handleWorkspaceResizeStart('advisor')}
					/>
				</>
			)}
			{/* 左侧：驾驶舱面板 */}
			<div
				className={`shrink-0 overflow-hidden border-r border-[var(--border-color)] ${resizingWorkspacePanel ? '' : 'transition-[width] duration-300 ease-in-out'}`}
				style={{ width: leftPanelWidth }}
			>
				<div className={`h-full w-full flex overflow-hidden relative ${isProjectGraphShellActive ? 'bg-[#11161f]' : activeCockpitModule === 'files' && !isSandboxSectionActive ? 'bg-[#f5f5f7]' : activeCockpitModule === 'geo' ? 'bg-[#f0f4f0]' : 'bg-[var(--sidebar-bg)]'}`}>
					{/* 多页面内容面板 - 铺满整个左侧区域 */}
					<div className="flex-1 min-w-0 min-h-0 overflow-hidden w-full">
						{isSandboxSectionActive ? (
							<PlanSandboxPanel
								sessionId={sessionId}
								projectLabel={displayProjectTitle}
								projectOverview={projectOverview ?? undefined}
								activeSpace={activeSandboxSpace}
								spaceOptions={PLAN_SANDBOX_SPACE_OPTIONS}
								onActiveSpaceChange={handleSandboxSpaceChange}
								onEnterBoardSpace={handleEnterBoardSpace}
								onInjectReference={injectReferenceToRight}
								className="w-full h-full"
							/>
						) : activeCockpitModule === 'geo' ? (
							<GeoCanvasView
								onInjectToAdvisor={(text) => {
									setConversationPrefill({ id: Date.now(), text });
									handleAdvisorAsk(text);
								}}
								className="w-full h-full"
							/>
						) : isProjectGraphShellActive ? (
							<div className="flex h-full w-full">
								<div
									className="min-w-0 h-full border-r border-[#1f2733] relative"
									style={{ width: `${projectGraphColumnRatio * 100}%` }}
								>
									<div className="absolute right-3 top-3 z-10">
										<button
											onClick={() => setGraphViewMode((prev) => (prev === 'grouped' ? 'free' : 'grouped'))}
											className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-[#2d3748] bg-[rgba(17,24,39,0.78)] text-[#cbd5e1] backdrop-blur-sm transition hover:bg-[rgba(30,41,59,0.92)] hover:text-white"
											title={graphViewMode === 'grouped' ? '当前分组网络态，点击切换为自由网络态' : '当前自由网络态，点击切换为分组网络态'}
											aria-label={graphViewMode === 'grouped' ? '切换到自由网络态' : '切换到分组网络态'}
										>
											<Network className="h-4 w-4" strokeWidth={2} />
										</button>
									</div>
									<KnowledgeGraphCanvas
										className="w-full h-full"
										onNodeClick={(nodeId, _label) => {
											handleNodeClick(nodeId);
										}}
									/>
								</div>
								<div
									className="h-full overflow-y-auto bg-[#f4f5f7] text-[#1f2937]"
									style={{ width: `${projectWhiteboardColumnRatio * 100}%` }}
								>
									<div className="h-full p-4">
										<div className="rounded-xl border border-[#dde1e7] bg-white p-4 shadow-sm">
											<div className="text-[12px] font-semibold tracking-[0.08em] text-[#6b7280]">项目图谱</div>
											<div className="mt-2 text-[18px] font-semibold text-[#111827]">{displayProjectTitle}</div>
											{projectOverview?.oneLiner ? (
												<div className="mt-2 text-[13px] leading-6 text-[#4b5563]">{projectOverview.oneLiner}</div>
											) : (
												<div className="mt-2 text-[13px] leading-6 text-[#6b7280]">当前处于项目图谱工作面。左侧浏览认知关系，右侧白栏承接节点详情与操作。</div>
											)}
										</div>

										<div className="mt-4 rounded-xl border border-[#dde1e7] bg-white p-4 shadow-sm">
											<div className="flex items-center justify-between">
												<div className="text-[12px] font-semibold tracking-[0.08em] text-[#6b7280]">节点白板</div>
												{selectedNode && (
													<button
														onClick={closeNodeDetail}
														className="rounded-md border border-[#d1d5db] px-2 py-1 text-[12px] text-[#4b5563] hover:bg-[#f8fafc]"
													>
														清除焦点
													</button>
												)}
											</div>
											{selectedNode ? (
												<div className="mt-2 text-[13px] leading-6 text-[#111827]">
													<div className="font-medium">节点 ID: {selectedNode}</div>
													<div className="mt-1 text-[#4b5563]">当前状态: {nodeDetails[selectedNode]?.status ?? 'pending'}</div>
													{selectedNodeData.length > 0 ? (
														<div className="mt-3 space-y-2">
															<div className="text-[12px] font-semibold tracking-[0.08em] text-[#6b7280]">执行记录</div>
															{selectedNodeData.slice(-5).reverse().map((record, index) => (
																<div key={`${record.time}-${index}`} className="rounded-md bg-[#f8fafc] px-3 py-2">
																	<div className="text-[11px] text-[#6b7280]">{record.time}</div>
																	<div className="mt-1 text-[12px] text-[#374151]">{record.detail || '无详细信息'}</div>
																</div>
															))}
														</div>
													) : (
														<div className="mt-2 text-[12px] text-[#6b7280]">暂无执行记录</div>
													)}
												</div>
											) : (
												<div className="mt-2 text-[13px] leading-6 text-[#6b7280]">点击图谱节点后，这里展示节点详情（不再使用独立详情抽屉）。</div>
											)}
										</div>

										<div className="mt-4 rounded-xl border border-[#dde1e7] bg-white p-4 shadow-sm">
											<div className="text-[12px] font-semibold tracking-[0.08em] text-[#6b7280]">待补信息</div>
											<ul className="mt-2 space-y-2 text-[13px] leading-5 text-[#374151]">
												{(projectOverview?.gapItems?.slice(0, 3) ?? []).map((item) => (
													<li key={item} className="rounded-md bg-[#f8fafc] px-3 py-2">{item}</li>
												))}
												{!(projectOverview?.gapItems?.length) && (
													<li className="rounded-md bg-[#f8fafc] px-3 py-2 text-[#6b7280]">暂无缺口项</li>
												)}
											</ul>
										</div>
									</div>
								</div>
							</div>
						) : (
							<CockpitPanel
								key={`cockpit-${activeProjectSection}`}
								moduleKey={activeCockpitModule}
								preferredFileViewMode={preferredFileViewMode}
								sessionId={sessionId}
								projectLabel={displayProjectTitle}
								onProjectLabelChange={handleProjectLabelChange}
								projectOverview={projectOverview ?? undefined}
								activeBoardSpace={activeBoardSpace}
								onActiveBoardSpaceChange={setActiveBoardSpace}
								onEnterBoardSpace={handleEnterBoardSpace}
								onEnterSandboxSpace={handleEnterSandboxSpace}
								onBoardVisualBriefChange={setActiveBoardVisualBrief}
								onBoardZoomChange={setBoardCanvasZoom}
								portfolioYearHeightScale={portfolioYearHeightScale}
								onDssPageChange={setActiveDssPage}
								onOpenInspirationLibrary={() => setActiveCockpitModule('inspiration')}
								onBackToAssets={() => setActiveCockpitModule('assets')}
								onSwitchModule={(target) => {
									if (target === 'floor_plan') handleEnterSandboxSpace(projectDefaultSpace);
									else handleEnterBoardSpace(projectDefaultSpace);
								}}
								onOpenGeoWorkspace={handleOpenGeoWorkspace}
								onNodeClick={(nodeId, label) => {
									console.log('📊 模块点击:', label);
								}}
								onCardClick={(title) => {
									console.log('📄 卡片点击:', title);
									injectReferenceToRight(title);
								}}
								className="w-full h-full"
							/>
						)}
					</div>

					{/* 左侧一级 / 二级胶囊导航 */}
					<div className="absolute top-4 left-3 z-20 flex flex-col items-start gap-3">
						<div className={`w-[32px] overflow-hidden rounded-[18px] border shadow-[0_14px_32px_rgba(15,23,42,0.22)] backdrop-blur-md transition-all duration-300 ${
							activePrimaryNav === 'project'
								? 'border-sky-300/80 bg-[#1fa2df] text-white'
								: 'border-slate-300 bg-[rgba(204,209,216,0.96)] text-slate-800'
						}`}>
								<button
									onClick={() => handlePrimaryNavChange('project')}
								className="flex w-full min-h-[112px] items-center justify-center px-0 py-5 text-center"
								title="项目图谱"
							>
								<div className="flex flex-col items-center leading-none text-[13px] font-semibold tracking-0">
									{'项目图谱'.split('').map((char, index) => (
										<span key={`project-nav-${index}`}>{char}</span>
									))}
								</div>
							</button>

							{projectActivated && (
								<div className="grid border-t border-white/9 bg-transparent">
									{PROJECT_SECTION_ITEMS.map((item) => {
										const active =
											activePrimaryNav === 'project' &&
											((item.key === 'sandbox' && activeCockpitModule === 'files' && activeProjectSection === 'sandbox') ||
												(item.key === 'board' && activeCockpitModule === 'board'));

										return (
											<button
												key={item.key}
												onClick={() => handleProjectSectionChange(item.key)}
												className={`w-full border-t border-white/7 px-0 py-3 text-center text-[12px] font-medium transition first:border-t-0 ${
													active
														? 'border-white/40 bg-[rgba(255,255,255,0.46)] text-slate-950 backdrop-blur-2xl shadow-[inset_0_1px_0_rgba(255,255,255,0.5),inset_0_-1px_0_rgba(255,255,255,0.16),0_8px_20px_rgba(15,23,42,0.14)]'
														: 'bg-transparent text-slate-800 hover:bg-black/5'
												}`}
											>
												<div className="flex flex-col items-center leading-none tracking-[0.04em]">
													{item.title.split('').map((char, index) => (
														<span key={`${item.key}-char-${index}`}>{char}</span>
													))}
												</div>
											</button>
										);
									})}
								</div>
							)}
						</div>

						{/* 地理工作台入口 */}
						<button
							onClick={handleOpenGeoWorkspace}
							className={`w-[32px] rounded-[18px] border px-0 py-5 text-center text-[13px] font-semibold tracking-0 shadow-[0_12px_26px_rgba(15,23,42,0.18)] backdrop-blur-md transition-all duration-300 ${
								activeCockpitModule === 'geo'
									? `border-teal-300/75 ${geoAnchor ? 'bg-emerald-500/95 text-white' : 'bg-orange-400/95 text-white'}`
									: 'border-slate-300 bg-[rgba(204,209,216,0.94)] text-slate-800 hover:bg-[rgba(194,200,208,0.98)]'
							}`}
							title={`地理工作台${geoAnchor ? '' : '（未设置坐标锚点）'}`}
						>
							<div className="flex flex-col items-center leading-none">
								{'地理'.split('').map((char, index) => (
									<span key={`geo-nav-${index}`}>{char}</span>
								))}
							</div>
						</button>

						{PRIMARY_NAV_ITEMS.filter((item) => item.key !== 'project').map((item) => {
							const active = activePrimaryNav === item.key;
							const activeClass =
								item.key === 'assets'
									? 'border-emerald-200/75 bg-emerald-400/95 text-black'
									: item.key === 'knowledge'
									? 'border-amber-200/75 bg-amber-300/95 text-black'
									: 'border-teal-300/75 bg-teal-500/95 text-white';

							return (
								<button
									key={item.key}
									onClick={() => handlePrimaryNavChange(item.key)}
									className={`w-[32px] rounded-[18px] border px-0 py-5 text-center text-[13px] font-semibold tracking-0 shadow-[0_12px_26px_rgba(15,23,42,0.18)] backdrop-blur-md transition-all duration-300 ${
										active
											? activeClass
											: 'border-slate-300 bg-[rgba(204,209,216,0.94)] text-slate-800 hover:bg-[rgba(194,200,208,0.98)]'
									}`}
									title={item.title}
								>
									<div className="flex flex-col items-center leading-none">
										{item.title.split('').map((char, index) => (
											<span key={`${item.key}-primary-${index}`}>{char}</span>
										))}
									</div>
								</button>
							);
						})}

						{activeCockpitModule === 'knowledge' && activeDssPage === 'portfolio' && (
							<div className="mt-6 flex w-[32px] justify-center">
								<div className="relative h-[126px] w-[24px]">
									<input
										type="range"
										min={1}
										max={3}
										step={0.1}
										value={portfolioYearHeightScale}
										onChange={(e) => setPortfolioYearHeightScale(Number(e.target.value))}
										aria-label="年度高度"
										className="portfolio-height-slider absolute left-1/2 top-1/2 h-[126px] w-[24px] -translate-x-1/2 -translate-y-1/2 cursor-pointer appearance-none bg-transparent"
										style={{
											'--portfolio-height-track': `linear-gradient(to top, rgba(72,72,78,0.39) 0%, rgba(72,72,78,0.39) ${((portfolioYearHeightScale - 1) / 2) * 100}%, rgba(72,72,78,0.78) ${((portfolioYearHeightScale - 1) / 2) * 100}%, rgba(72,72,78,0.78) 100%)`,
										} as CSSProperties}
									/>
								</div>
							</div>
						)}

						{activeCockpitModule === 'board' && (
							<div className="pointer-events-none mt-[15px] w-[32px] text-center text-[11px] font-medium text-white/78">
								{Math.round(boardCanvasZoom * 100)}%
							</div>
						)}
					</div>
				</div>
			</div>
			{/* 右侧：生产窗口 */}
			{isRightCollapsed ? (
				<div
					className="shrink-0 cursor-pointer relative bg-[#161616] transition-colors"
					style={{ width: '32px' }}
					onClick={handleCycleLayoutMode}
					title="展开方案高参"
				>
					<div className="absolute top-3 inset-x-0 h-8 flex items-center justify-center">
						<PanelRight className="h-[14px] w-[14px] text-white" strokeWidth={2} />
					</div>
				</div>
			) : (
			<div
				className="project-workspace-advisor-column relative shrink-0 border-l border-[var(--border-color)]"
			>
				<AdvisorPanel
					viewModel={advisorPanelViewModel}
					onChipAction={handleAdvisorChipAction}
					onAsk={handleAdvisorAsk}
				/>
			</div>
			)}
		</div>
		</AppSessionShell>
	);
}
