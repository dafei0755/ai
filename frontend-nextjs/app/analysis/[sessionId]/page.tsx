'use client';

import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
	Loader2,
	WifiOff,
	X,
	Network,
	Plus,
	CheckCircle2,
	AlertCircle,
	PanelLeft,
	Edit2,
	Pin,
	Share2,
	Trash2,
	ArrowLeft,
	SendHorizontal
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
import ConversationChat, { type ChatMessage } from '@/components/ConversationMode/ConversationChat';
import UpgradePromptBanner from '@/components/ConversationMode/UpgradePromptBanner';
import { KnowledgeGraphCanvas } from '@/components/KnowledgeGraphCanvas';
import { CockpitPanel, formatBoardVisualBriefForPrompt, type BoardCanvasSpace, type BoardVisualBrief } from '@/components/CockpitPanel';
import { PlanSandboxPanel } from '@/components/PlanSandboxPanel';
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

type CockpitModuleKey = 'files' | 'assets' | 'inspiration' | 'board' | 'experts' | 'insight' | 'knowledge';
type PrimaryNavKey = 'project' | 'assets' | 'knowledge';
type ProjectSectionKey = 'space' | 'sandbox' | 'board';
type InsightViewKey = 'main' | 'space' | 'flow' | 'emotion' | 'time';
type LayoutMode = 'split' | 'left-focus' | 'right-focus';
type CockpitCard = {
	title: string;
	desc: string;
	badge?: string;
	highlights?: string[];
	accent?: string;
	size?: 'sm' | 'md' | 'lg';
};

type AdvisorHistoryRecord = {
	sessionId: string;
	title: string;
	createdAt: string;
	updatedAt: string;
	modeLabel: string;
};

const EMPTY_CHAT_MESSAGES: ChatMessage[] = [];

const ADVISOR_HISTORY_STORAGE_KEY = 'analysis.advisor.history.v1';
const ADVISOR_CONVERSATION_STORAGE_KEY = 'analysis.advisor.conversations.v1';

const PRIMARY_NAV_ITEMS: Array<{ key: PrimaryNavKey; title: string }> = [
	{ key: 'project', title: '项目底盘' },
	{ key: 'assets', title: '资源雷达' },
	{ key: 'knowledge', title: '我的硅基分身' },
];

const SCENE_PERSPECTIVE_PRESETS = {
	projectSandbox: ['空间总控视角', '动线效率视角', '结构机电视角', '实施边界视角', '风险总控视角', '平衡推进视角'],
	projectBoard: ['叙事表达视角', '品牌一致视角', '空间构图视角', '灯光情绪视角', '落地可建视角', '平衡推进视角'],
	assetsMarket: ['平衡视角', '品质优先视角', '捡漏视角', '交付稳健视角', '替代优化视角'],
	assetsInspiration: ['灵感拓展视角', '风格一致视角', '可落地图谱视角', '成本敏感视角'],
	knowledgeSediment: ['方法论沉淀视角', '可复用规则视角', '反例校验视角', '决策压缩视角'],
	knowledgePortfolio: ['作品迁移视角', '个人风格校准视角', '商业转化视角', '复盘抽象视角', '叙事表达视角'],
	knowledgeProfile: ['用户洞察视角', '关系经营视角', '价值定位视角', '增长策略视角'],
	insightMain: ['主矛盾视角', '先决条件视角', '最小闭环视角', '系统耦合视角'],
	insightSpace: ['空间程序视角', '节点优先级视角', '动线冲突视角', '实施边界视角', '最小闭环视角'],
	insightFlow: ['动线效率视角', '体验节奏视角', '运营摩擦视角', '风险总控视角'],
	insightEmotion: ['情绪曲线视角', '品牌感知视角', '用户心智视角', '灯光情绪视角'],
	insightTime: ['时间切片视角', '季节适配视角', '运营弹性视角', '风险总控视角'],
} as const;

type ExpertPerspectiveOption =
	(typeof SCENE_PERSPECTIVE_PRESETS)[keyof typeof SCENE_PERSPECTIVE_PRESETS][number];

const getScenePerspectiveOptions = (params: {
	activePrimaryNav: PrimaryNavKey;
	activeCockpitModule: CockpitModuleKey;
	activeProjectSection: ProjectSectionKey;
	activeBoardSpace: BoardCanvasSpace;
	activeDssPage: 'sediment' | 'portfolio' | 'profile';
	activeInsightView: InsightViewKey;
}): readonly ExpertPerspectiveOption[] => {
	const {
		activePrimaryNav,
		activeCockpitModule,
		activeProjectSection,
		activeBoardSpace,
		activeDssPage,
		activeInsightView,
	} = params;

	if (activePrimaryNav === 'project' && activeCockpitModule === 'files' && activeProjectSection === 'sandbox') {
		if (activeBoardSpace === '后勤') {
			return ['实施边界视角', '动线效率视角', '风险总控视角', '平衡推进视角'];
		}
		return SCENE_PERSPECTIVE_PRESETS.projectSandbox;
	}

	if (activePrimaryNav === 'project' && activeCockpitModule === 'board') {
		if (activeBoardSpace === '客房') {
			return ['叙事表达视角', '灯光情绪视角', '运营弹性视角', '落地可建视角', '平衡推进视角'];
		}
		return SCENE_PERSPECTIVE_PRESETS.projectBoard;
	}

	if (activePrimaryNav === 'assets') {
		if (activeCockpitModule === 'inspiration') {
			return SCENE_PERSPECTIVE_PRESETS.assetsInspiration;
		}
		return SCENE_PERSPECTIVE_PRESETS.assetsMarket;
	}

	if (activePrimaryNav === 'knowledge') {
		if (activeDssPage === 'portfolio') return SCENE_PERSPECTIVE_PRESETS.knowledgePortfolio;
		if (activeDssPage === 'profile') return SCENE_PERSPECTIVE_PRESETS.knowledgeProfile;
		return SCENE_PERSPECTIVE_PRESETS.knowledgeSediment;
	}

	if (activeInsightView === 'space') return SCENE_PERSPECTIVE_PRESETS.insightSpace;
	if (activeInsightView === 'flow') return SCENE_PERSPECTIVE_PRESETS.insightFlow;
	if (activeInsightView === 'emotion') return SCENE_PERSPECTIVE_PRESETS.insightEmotion;
	if (activeInsightView === 'time') return SCENE_PERSPECTIVE_PRESETS.insightTime;
	return SCENE_PERSPECTIVE_PRESETS.insightMain;
};

const EXPERT_SUMMON_OPTIONS = ['召集全部', '空间总控', '用户研究', '商业运营', '实施边界', '风险总控'] as const;

const PROJECT_SECTION_ITEMS: Array<{ key: ProjectSectionKey; title: string }> = [
	{ key: 'sandbox', title: '平面推演' },
	{ key: 'board', title: '方案画布' },
];

const PLAN_SANDBOX_SPACE_OPTIONS: Exclude<BoardCanvasSpace, '全部'>[] = ['大堂', '餐厅', '客房', '公区', '连廊', '后勤'];

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

const buildAdvisorSceneContext = (params: {
	activePrimaryNav: PrimaryNavKey;
	activeCockpitModule: CockpitModuleKey;
	activeProjectSection: ProjectSectionKey;
	activeBoardSpace: BoardCanvasSpace;
	activeDssPage: 'sediment' | 'portfolio' | 'profile';
	activeInsightView: InsightViewKey;
}): { key: string; label: string; suggestion: string; sceneRef: string } => {
	const {
		activePrimaryNav,
		activeCockpitModule,
		activeProjectSection,
		activeBoardSpace,
		activeDssPage,
		activeInsightView,
	} = params;

	const currentSpace = activeBoardSpace === '全部' ? '全局' : activeBoardSpace;
	const sceneRef = `场景/${activePrimaryNav}/${activeCockpitModule}/${activeProjectSection}/${currentSpace}/${activeDssPage}/${activeInsightView}`;

	if (activePrimaryNav === 'project' && activeCockpitModule === 'files' && activeProjectSection === 'sandbox') {
		const label = `项目底盘 · 平面推演 · ${currentSpace}`;
		return {
			key: sceneRef,
			label,
			sceneRef,
			suggestion: [
				`已同步左侧场景：${label}。`,
				'',
				'深度思考建议：',
				'1. 先做动线冲突扫描：识别住客动线、服务动线与消防疏散是否互相干扰。',
				'2. 再做功能密度校准：核对高频停留区是否被结构柱网、门洞和设备井切碎。',
				'3. 最后做落地性反推：把每个优化动作映射到施工复杂度、预算增量与运营收益。',
				'',
				'如果你愿意，我可以直接给出这个空间的三套平面优化策略（保守/平衡/激进）与取舍表。',
			].join('\n'),
		};
	}

	if (activePrimaryNav === 'project' && activeCockpitModule === 'board') {
		const label = `项目底盘 · 方案画布 · ${currentSpace}`;
		return {
			key: sceneRef,
			label,
			sceneRef,
			suggestion: [
				`已同步左侧场景：${label}。`,
				'',
				'深度思考建议：',
				'1. 先锁定一句话视觉命题：明确“这个空间最先被记住的感受”是什么。',
				'2. 再做品牌语义到材料/光线/尺度的三层映射，避免只有风格词没有设计动作。',
				'3. 同步建立反例边界：明确哪些元素会削弱项目识别度，提前排除。',
				'',
				'我可以继续输出该空间的 VisualBrief 增强版（关键词、负面约束、出图优先级）。',
			].join('\n'),
		};
	}

	if (activePrimaryNav === 'assets') {
		const label = activeCockpitModule === 'inspiration' ? '资源雷达 · 灵感池' : '资源雷达 · 市场智能匹配';
		return {
			key: sceneRef,
			label,
			sceneRef,
			suggestion: [
				`已同步左侧场景：${label}。`,
				'',
				'深度思考建议：',
				'1. 按“不可替代核心件 / 可替代优化件 / 成本压缩件”三层筛选资源。',
				'2. 把每个候选资源绑定到具体空间节点，避免“好看但无落点”的素材堆积。',
				'3. 评估供应链风险：交付周期、维护成本与替代方案是否可闭环。',
				'',
				'我可以进一步生成一份资源取舍清单（必须保留、可替换、可删除）。',
			].join('\n'),
		};
	}

	if (activePrimaryNav === 'knowledge') {
		const pageLabel = activeDssPage === 'profile' ? '我的画像' : activeDssPage === 'portfolio' ? '作品' : '沉淀';
		const label = `我的硅基分身 · ${pageLabel}`;
		return {
			key: sceneRef,
			label,
			sceneRef,
			suggestion: [
				`已同步左侧场景：${label}。`,
				'',
				'深度思考建议：',
				'1. 从“个人偏好”提炼为“可复用判断规则”，用于约束当前项目决策。',
				'2. 识别经验盲区：哪些结论来自惯性而非证据，哪些需要反例验证。',
				'3. 建立迁移路径：把过往成功经验转译为本项目可执行动作与检查点。',
				'',
				'我可以基于你的硅基分身，给出当前项目的个性化决策清单。',
			].join('\n'),
		};
	}

	const label = `项目洞察 · ${INSIGHT_VIEWS.find((item) => item.key === activeInsightView)?.label ?? '全景'}`;
	return {
		key: sceneRef,
		label,
		sceneRef,
		suggestion: [
			`已同步左侧场景：${label}。`,
			'',
			'深度思考建议：',
			'1. 先识别关键矛盾（品牌表达、运营效率、成本边界）谁是当前主矛盾。',
			'2. 再建立“先决条件清单”，明确哪些前提不成立就不能推进方案。',
			'3. 最后定义下一步最小闭环动作，优先验证高不确定项。',
		].join('\n'),
	};
};

export default function AnalysisPage() {
	const params = useParams();
	const router = useRouter();
	const sessionId = params.sessionId as string;
	const advisorRightTargetRatio = 0.32;
	const splitLeftFixedRatio = 1 - advisorRightTargetRatio;
	const adaptiveLeftDockGutter = 'clamp(44px, 3.2vw, 72px)';
	const adaptiveLeftCardPadding = 'clamp(10px, 1.2vw, 20px)';
	const adaptiveRightContentGutter = 'clamp(12px, 2vw, 32px)';
	const [viewportWidth, setViewportWidth] = useState(1440);

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
	const [conversationMessagesByScene, setConversationMessagesByScene] = useState<Record<string, ChatMessage[]>>({});
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
	const [activeDssPage, setActiveDssPage] = useState<'sediment' | 'portfolio' | 'profile'>('portfolio');
	const [portfolioYearHeightScale, setPortfolioYearHeightScale] = useState(1);
	const [activeInsightView, setActiveInsightView] = useState<InsightViewKey>('main');
	const [cockpitContextRefs, setCockpitContextRefs] = useState<string[]>([]);
	const [conversationPrefill, setConversationPrefill] = useState<{ id: number; text: string } | null>(null);

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
	const preferredFileViewMode = '统一视图';
	const isSandboxSectionActive = activeProjectSection === 'sandbox';
	const activeSandboxSpace: Exclude<BoardCanvasSpace, '全部'> = activeBoardSpace === '全部' ? '大堂' : activeBoardSpace;
	const activeSplitLeftPanelWidth = useMemo(() => {
		const width = Number.isFinite(viewportWidth) ? viewportWidth : 1440;
		return `${Math.round(width * splitLeftFixedRatio)}px`;
	}, [splitLeftFixedRatio, viewportWidth]);
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
	const activeAdvisorConversationKey = `${sessionId}::${advisorSceneContext.key}`;
	const conversationMessages = conversationMessagesByScene[activeAdvisorConversationKey] ?? EMPTY_CHAT_MESSAGES;
	const setConversationMessages = useCallback(
		(updater: React.SetStateAction<ChatMessage[]>) => {
			setConversationMessagesByScene((prev) => {
				const current = prev[activeAdvisorConversationKey] ?? [];
				const nextMessages = typeof updater === 'function'
					? (updater as (value: ChatMessage[]) => ChatMessage[])(current)
					: updater;
				return {
					...prev,
					[activeAdvisorConversationKey]: nextMessages,
				};
			});
		},
		[activeAdvisorConversationKey]
	);
	const leftPanelWidth = isLeftCollapsed
		? '0px'
		: isRightCollapsed
		? '100%'
		: activeSplitLeftPanelWidth;
	const advisorHistoryGroups = useMemo(() => {
		const now = new Date();
		const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
		const sevenDaysAgo = today - 7 * 24 * 60 * 60 * 1000;
		const thirtyDaysAgo = today - 30 * 24 * 60 * 60 * 1000;
		const groups = {
			today: [] as AdvisorHistoryRecord[],
			last7Days: [] as AdvisorHistoryRecord[],
			last30Days: [] as AdvisorHistoryRecord[],
		};

		advisorHistoryRecords.forEach((record) => {
			const dayStart = new Date(record.updatedAt);
			const normalized = new Date(dayStart.getFullYear(), dayStart.getMonth(), dayStart.getDate()).getTime();
			if (normalized >= today) {
				groups.today.push(record);
				return;
			}
			if (normalized >= sevenDaysAgo) {
				groups.last7Days.push(record);
				return;
			}
			if (normalized >= thirtyDaysAgo) {
				groups.last30Days.push(record);
			}
		});

		return groups;
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
		try {
			const raw = window.localStorage.getItem(ADVISOR_HISTORY_STORAGE_KEY);
			if (!raw) return;
			const parsed = JSON.parse(raw) as AdvisorHistoryRecord[];
			setAdvisorHistoryRecords(Array.isArray(parsed) ? parsed : []);
		} catch (error) {
			console.error('[analysis] failed to restore advisor history:', error);
		}
	}, []);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		try {
			const raw = window.localStorage.getItem(ADVISOR_CONVERSATION_STORAGE_KEY);
			if (!raw) return;
			const parsed = JSON.parse(raw) as Record<string, ChatMessage[]>;
			if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return;
			setConversationMessagesByScene(parsed);
		} catch (error) {
			console.error('[analysis] failed to restore advisor conversations:', error);
		}
	}, []);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		try {
			window.localStorage.setItem(ADVISOR_HISTORY_STORAGE_KEY, JSON.stringify(advisorHistoryRecords));
		} catch (error) {
			console.error('[analysis] failed to persist advisor history:', error);
		}
	}, [advisorHistoryRecords]);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		try {
			window.localStorage.setItem(ADVISOR_CONVERSATION_STORAGE_KEY, JSON.stringify(conversationMessagesByScene));
		} catch (error) {
			console.error('[analysis] failed to persist advisor conversations:', error);
		}
	}, [conversationMessagesByScene]);

	useEffect(() => {
		const firstUserMessage = conversationMessages.find((message) => message.role === 'user')?.content?.trim();
		const titleSource = userInput.trim() || firstUserMessage || '未命名会话';
		const nextTitle = titleSource.replace(/\s+/g, ' ').slice(0, 36);
		if (!nextTitle) return;
		const nextModeLabel = systemMode === 'project' ? '方案高参' : '深度思考';

		setAdvisorHistoryRecords((prev) => {
			const now = new Date().toISOString();
			const existing = prev.find((item) => item.sessionId === sessionId);
			if (existing && existing.title === nextTitle && existing.modeLabel === nextModeLabel) {
				return prev;
			}
			const nextRecord: AdvisorHistoryRecord = {
				sessionId,
				title: nextTitle,
				createdAt: existing?.createdAt ?? now,
				updatedAt: now,
				modeLabel: nextModeLabel,
			};
			return [nextRecord, ...prev.filter((item) => item.sessionId !== sessionId)].slice(0, 30);
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
		const fetchInitialStatus = async (retryCount = 0) => {
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
				// 对话态（conv-）：从 sessionStorage 恢复首页提交的初始对话
				if (sessionId.startsWith('conv-')) {
					const initRaw = sessionStorage.getItem(`conv_init_${sessionId}`);
					if (initRaw) {
						try {
							const { userMessage, aiReply, guidance_card } = JSON.parse(initRaw);
							setConversationMessages([
								{ id: 'user-init', role: 'user', content: userMessage, timestamp: new Date().toISOString() },
								{ id: 'ai-init', role: 'assistant', content: aiReply, timestamp: new Date().toISOString(), guidance_card: guidance_card ?? undefined },
							]);
						} catch (_) { /* ignore parse errors */ }
						sessionStorage.removeItem(`conv_init_${sessionId}`);
					}
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
					const initRaw = sessionStorage.getItem(`conv_init_${sessionId}`);
					if (initRaw) {
						try {
							const { userMessage, aiReply, guidance_card } = JSON.parse(initRaw);
							setConversationMessages([
								{ id: 'user-init', role: 'user', content: userMessage, timestamp: new Date().toISOString() },
								{ id: 'ai-init', role: 'assistant', content: aiReply, timestamp: new Date().toISOString(), guidance_card: guidance_card ?? undefined },
							]);
						} catch (_) { /* ignore parse errors */ }
						sessionStorage.removeItem(`conv_init_${sessionId}`);
					}
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

		const wsUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
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
	}, [navigateToReport, sessionId]);

	const handleNodeClick = (nodeId: string) => {
		setSelectedNode(nodeId);
	};

	const closeNodeDetail = () => {
		setSelectedNode(null);
	};

	const handleCycleLayoutMode = useCallback(() => {
		setLayoutMode((prev) => {
			if (prev === 'split') return 'left-focus';
			if (prev === 'left-focus') return 'right-focus';
			return 'split';
		});
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

	const handleProjectSectionChange = useCallback((section: ProjectSectionKey) => {
		setActiveProjectSection(section);
		if (section === 'sandbox') {
			if (activeBoardSpace === '全部') {
				setActiveBoardSpace('大堂');
			}
			setActiveCockpitModule('files');
			return;
		}
		if (section === 'board') {
			setActiveCockpitModule('board');
			return;
		}
		setActiveCockpitModule('files');
	}, [activeBoardSpace]);

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
		const msg: ChatMessage = { id: `user-${Date.now()}`, role: 'user', content: text, timestamp: new Date().toISOString() };
		setConversationMessages(prev => [...prev, msg]);
		try {
			const perspectivePrefix = `[专家视角设定]\n当前场景：${advisorSceneContext.label}\n当前指定视角：${activeExpertPerspective}\n回答时请围绕该视角深挖关键判断、风险取舍与执行动作。\n\n`;
			const briefPrefix = shouldShowBoardVisualBrief && activeBoardVisualBrief
				? `[方案画布空间 VisualBrief]\n${formatBoardVisualBriefForPrompt(activeBoardVisualBrief)}\n\n[用户本轮指令]\n`
				: '';
			const scenePrefix = `[当前左侧场景]\n场景：${advisorSceneContext.label}\n引用：${advisorSceneContext.sceneRef}\n系统上下文判断：\n${advisorSceneContext.suggestion}\n\n[用户本轮指令]\n`;
			const res = await api.sendConversationMessage(
				sessionId,
				`${perspectivePrefix}${scenePrefix}${briefPrefix}${text}`,
				undefined,
				{ expert_perspective: activeExpertPerspective }
			);
			// AI 回复追加到对话流，携带引导卡片（如有）
			if (res.reply) {
				const aiMsg: ChatMessage = {
					id: `ai-${Date.now()}`,
					role: 'assistant',
					content: res.reply,
					timestamp: new Date().toISOString(),
					guidance_card: res.guidance_card as ChatMessage['guidance_card'] | undefined,
				};
				setConversationMessages(prev => [...prev, aiMsg]);
			}
			// 升级建议信号
			if (res.upgrade_suggested && res.upgrade_signal) {
				const sig = res.upgrade_signal as any;
				if (sig?.indicators) setUpgradeIndicators(sig.indicators);
				if (sig?.suggestion_text) setUpgradeSuggestionText(sig.suggestion_text);
				setShowUpgradeBanner(true);
			}
		} catch (err) {
			console.error('[conv] send failed:', err);
		}
	}, [activeBoardVisualBrief, activeExpertPerspective, advisorSceneContext, sessionId, shouldShowBoardVisualBrief, setConversationMessages]);

	// v2.0 引导卡片响应 handler
	const handleConvCardResponse = useCallback(async (cardId: string, optionId?: string, freetext?: string) => {
		// 立即标记对应消息的 card_responded = true，并记录选择摘要
		setConversationMessages(prev =>
			prev.map(m => {
				if (m.guidance_card?.card_id !== cardId) return m;
				// 计算选择摘要文本（含完整描述）
				let selectionLabel = freetext;
				if (!selectionLabel && optionId) {
					const allOptions = [
						...(m.guidance_card.options ?? []),
						...(m.guidance_card.pages ?? []).flatMap(p => p.options ?? []),
					];
					const opt = allOptions.find(o => o.id === optionId);
					if (opt) {
						selectionLabel = opt.description
							? `${opt.label}：${opt.description}`
							: opt.label;
					} else {
						selectionLabel = optionId;
					}
				}
				return { ...m, card_responded: true, card_selection_label: selectionLabel || undefined };
			})
		);
		// 发送卡片响应（freetext 作为 message，携带 in_response_to_card_id + selected_option_id）
		const text = freetext || (optionId ? `[card:${optionId}]` : '[skip]');
		try {
			const perspectivePrefix = `[专家视角设定]\n当前场景：${advisorSceneContext.label}\n当前指定视角：${activeExpertPerspective}\n回答时请围绕该视角深挖关键判断、风险取舍与执行动作。\n\n`;
			const res = await api.sendConversationMessage(
				sessionId,
				`${perspectivePrefix}${text}`,
				{
					in_response_to_card_id: cardId,
					selected_option_id: optionId,
				},
				{ expert_perspective: activeExpertPerspective }
			);
			if (res.reply) {
				const aiMsg: ChatMessage = {
					id: `ai-${Date.now()}`,
					role: 'assistant',
					content: res.reply,
					timestamp: new Date().toISOString(),
					guidance_card: res.guidance_card as ChatMessage['guidance_card'] | undefined,
				};
				setConversationMessages(prev => [...prev, aiMsg]);
			}
		} catch (err) {
			console.error('[conv] card response failed:', err);
		}
	}, [activeExpertPerspective, advisorSceneContext.label, sessionId]);

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

	const collapsedReadableWidth = 'min(1180px, calc(100vw - 64px))';
	const rightPanelReadableWidth = isLeftCollapsed ? collapsedReadableWidth : '100%';
	const shellToggleButtonClass =
		'pointer-events-auto inline-flex h-8 w-8 items-center justify-center rounded-full bg-[#383838] text-white transition-colors duration-150 hover:bg-[#4a4a4a]';
	const shellToggleIconClass = 'h-[14px] w-[14px] shrink-0 translate-y-px';
	const layoutCycleMeta =
		layoutMode === 'split'
			? { label: '切换到驾驶舱全屏', title: '切换到驾驶舱全屏' }
			: layoutMode === 'left-focus'
			? { label: '切换到方案高参全屏', title: '切换到方案高参全屏' }
			: { label: '恢复分栏布局', title: '恢复分栏布局' };

	return (
		<div className="flex h-screen bg-[var(--background)] text-[var(--foreground)] overflow-hidden">
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
			{/* 左侧：驾驶舱面板 */}
			<div
				className="shrink-0 overflow-hidden border-r border-[var(--border-color)]"
				style={{ width: leftPanelWidth }}
			>
				<div className={`h-full w-full flex overflow-hidden relative ${activeCockpitModule === 'files' && !isSandboxSectionActive ? 'bg-[#f5f5f7]' : 'bg-[var(--sidebar-bg)]'}`}>
					{/* 多页面内容面板 - 铺满整个左侧区域 */}
					<div className={`flex-1 min-w-0 min-h-0 overflow-hidden w-full ${isRightCollapsed ? 'pr-16' : ''}`}>
						{isSandboxSectionActive ? (
							<PlanSandboxPanel
								sessionId={sessionId}
								activeSpace={activeSandboxSpace}
								spaceOptions={PLAN_SANDBOX_SPACE_OPTIONS}
								onActiveSpaceChange={handleSandboxSpaceChange}
								onEnterBoardSpace={handleEnterBoardSpace}
								onInjectReference={injectReferenceToRight}
								className="w-full h-full"
							/>
						) : (
							<CockpitPanel
								key={`cockpit-${activeProjectSection}`}
								moduleKey={activeCockpitModule}
								preferredFileViewMode={preferredFileViewMode}
								sessionId={sessionId}
								projectLabel={sessionId}
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
								title="项目底盘"
							>
								<div className="flex flex-col items-center leading-none text-[13px] font-semibold tracking-0">
									{'项目底盘'.split('').map((char, index) => (
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
									<div className="absolute left-1/2 top-3 bottom-3 w-px -translate-x-1/2 bg-slate-400/60" />
									<input
										type="range"
										min={1}
										max={3}
										step={0.1}
										value={portfolioYearHeightScale}
										onChange={(e) => setPortfolioYearHeightScale(Number(e.target.value))}
										aria-label="年度高度"
										className="portfolio-height-slider absolute left-1/2 top-1/2 h-[126px] w-[24px] -translate-x-1/2 -translate-y-1/2 cursor-pointer appearance-none bg-transparent"
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
			{!isRightCollapsed && (
			<div
				className="relative flex-1 overflow-hidden border-l border-[var(--border-color)]"
			>
				<aside
					className={`absolute inset-y-0 left-0 z-20 w-[280px] border-r border-[var(--border-color)] bg-[#232323] transition-transform duration-300 ${
						advisorHistoryOpen ? 'translate-x-0' : '-translate-x-full'
					}`}
				>
					<div className="flex h-full flex-col">
						<div className="flex items-center gap-3 border-b border-white/10 px-4 py-4">
							<div className="flex items-center gap-3">
								<div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#2e67ff] text-white">
									<Network className="h-5 w-5" />
								</div>
								<div className="ui-type-subtitle font-semibold text-white">方案高参</div>
							</div>
						</div>
						<div className="px-4 pt-4">
							<button
								onClick={() => {
									setAdvisorHistoryOpen(false);
									router.push('/');
								}}
								className="flex w-full items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/8 px-4 py-3 text-sm font-medium text-white transition hover:bg-white/12"
							>
								<Plus className="h-4 w-4" />
								<span>开启新对话</span>
							</button>
						</div>
						<div className="flex-1 overflow-y-auto px-4 py-5 text-white/78">
							{[
								{ label: '今天', items: advisorHistoryGroups.today },
								{ label: '7天内', items: advisorHistoryGroups.last7Days },
								{ label: '30天内', items: advisorHistoryGroups.last30Days },
							].map((group) =>
								group.items.length > 0 ? (
									<div key={group.label} className="mb-8">
										<div className="ui-type-meta mb-4 text-white/42">{group.label}</div>
										<div className="space-y-3">
											{group.items.map((record) => (
												<button
													key={record.sessionId}
													onClick={() => {
														setAdvisorHistoryOpen(false);
														if (record.sessionId !== sessionId) {
															router.push(`/analysis/${record.sessionId}`);
														}
													}}
													className={`block w-full text-left transition ${
														record.sessionId === sessionId ? 'text-white' : 'text-white/72 hover:text-white'
													}`}
												>
													<div className="ui-type-body line-clamp-2 font-medium">{record.title}</div>
													<div className="ui-type-meta mt-1 flex items-center gap-2 text-white/38">
														<span>
															{new Date(record.updatedAt).toLocaleString('zh-CN', {
																month: 'numeric',
																day: 'numeric',
																hour: '2-digit',
																minute: '2-digit',
															})}
														</span>
														<span className="text-[#4d8dff]">[{record.modeLabel}]</span>
													</div>
												</button>
											))}
										</div>
									</div>
								) : null
							)}
						</div>
					</div>
				</aside>

				<div
					className={`absolute inset-0 flex flex-col transition-transform duration-300 ${
						advisorHistoryOpen ? 'translate-x-[280px]' : 'translate-x-0'
					}`}
				>
		<header className="absolute top-0 left-0 right-0 z-20 pointer-events-none">
			<div className="flex flex-wrap items-start justify-between gap-y-2 px-4 py-3 pr-16 pointer-events-auto">
				<div className="flex items-start gap-3">
					<button
						onClick={() => setAdvisorHistoryOpen((prev) => !prev)}
						className={`${shellToggleButtonClass} self-start`}
						aria-label={advisorHistoryOpen ? '折叠历史记录' : '展开历史记录'}
						title={advisorHistoryOpen ? '折叠历史记录' : '展开历史记录'}
					>
						<ArrowLeft className={`${shellToggleIconClass} transition-transform duration-300 ${advisorHistoryOpen ? 'rotate-180' : ''}`} strokeWidth={2} />
					</button>
					<h1 className="ui-type-title self-start pt-0.5 font-semibold">
						{sessionId.includes('-followup-') ? '💬 追问分析中...' : '方案高参'}
					</h1>
				</div>
				<div className="flex w-full justify-end sm:w-auto">
					{!wsConnected && (
						<div className="ui-type-meta flex items-center gap-2 rounded-full border border-red-900/30 bg-red-900/20 px-3 py-1.5 text-red-400 backdrop-blur-sm">
							<WifiOff className="h-3 w-3" />
							<span>网络异常，正在重连...</span>
						</div>
					)}
				</div>
			</div>
		</header>

				{/* 统一对话布局（对话态 + 项目态） */}
				<div className="flex flex-1 overflow-hidden min-h-0 pt-14">
					{/* 主对话区 */}
					<div
						className="flex-1 flex flex-col overflow-hidden min-h-0 relative"
					>
						{/* 升级横幅（仅对话态） */}
						{systemMode === 'conversation' && showUpgradeBanner && (
							<div className="border-b border-[var(--border-color)] flex-shrink-0 px-6 lg:px-10 xl:px-14 py-3">
								<div className="w-full h-full max-w-[95%] lg:max-w-[1200px] mx-auto xl:max-w-none px-0 xl:px-8">
									<UpgradePromptBanner
										triggered={showUpgradeBanner}
										indicators={upgradeIndicators}
										suggestion_text={upgradeSuggestionText}
										onConfirm={handleUpgradeConfirm}
										onDismiss={() => setShowUpgradeBanner(false)}
									/>
								</div>
							</div>
						)}

						{systemMode === 'conversation' ? (
							/* ── 对话态：使用 ConversationChat 组件 ── */
							<div
								className={`flex-1 min-h-0 overflow-hidden ${isLeftCollapsed ? 'mx-auto pr-16' : 'w-full'}`}
								style={isLeftCollapsed ? { width: collapsedReadableWidth } : undefined}
							>
								<ConversationChat
									sessionId={sessionId}
									messages={conversationMessages}
									activeExpertPerspective={activeExpertPerspective}
									expertPerspectiveOptions={sceneExpertPerspectiveOptions}
									onExpertPerspectiveChange={(nextPerspective) => {
										setActiveExpertPerspective(nextPerspective as ExpertPerspectiveOption);
									}}
									summonOptions={EXPERT_SUMMON_OPTIONS}
									onSummonExpert={(target) => handleSummonExpert(target as (typeof EXPERT_SUMMON_OPTIONS)[number])}
									visualBriefContext={visualBriefChatContext}
									onVisualBriefPromptChange={updateActiveBoardVisualBriefPrompt}
									onVisualBriefNoteChange={updateActiveBoardVisualBriefNote}
									advisorSceneContext={advisorSceneContext}
									placeholder={`围绕 ${advisorSceneContext.label} 提问，或让方案高参继续深挖…`}
									prefillHint={conversationPrefill}
									onSendMessage={handleConvSendMessage}
									onCardResponse={handleConvCardResponse}
									loading={!status}
									showUpgradeBanner={false}
									onUpgradeConfirm={handleUpgradeConfirm}
									onUpgradeDismiss={() => setShowUpgradeBanner(false)}
									className="w-full h-full"
								/>
							</div>
						) : (
							/* ── 项目态：ChatGPT 风格滚动对话流 ── */
							<div
								className="flex-1 overflow-y-auto p-0"
								style={{
									paddingInline: adaptiveRightContentGutter,
									paddingRight: isLeftCollapsed
										? `calc(${adaptiveRightContentGutter} + 56px)`
										: adaptiveRightContentGutter,
								}}
							>
								<div className="w-full py-6 flex flex-col gap-4 mx-auto" style={{ width: rightPanelReadableWidth, paddingBottom: '8px' }}>
									{/* 用户原始问题 */}
									{userInput && (
										<div className="flex justify-end items-end gap-2">
											<div className="ui-type-body max-w-[75%] px-5 py-3.5 rounded-none bg-[var(--primary)] text-white">
												<p className="whitespace-pre-wrap">{userInput}</p>
											</div>
											<div className="w-7 h-7 rounded-full bg-[var(--card-bg)] border border-[var(--border-color)] flex items-center justify-center text-xs flex-shrink-0 text-[var(--foreground-secondary)]">
												我
											</div>
										</div>
									)}

									{/* 加载中 */}
									{!status && !error && (
										<div className="flex items-end gap-2">
											<div className="w-7 h-7 rounded-full bg-[var(--primary)] flex items-center justify-center text-white text-xs flex-shrink-0">AI</div>
											<div className="ui-card-shell bg-[var(--card-bg)] rounded-none px-4 py-3">
												<div className="flex gap-1.5 items-center">
													<span className="w-2 h-2 rounded-full bg-[var(--foreground-secondary)] animate-bounce [animation-delay:-0.3s]" />
													<span className="w-2 h-2 rounded-full bg-[var(--foreground-secondary)] animate-bounce [animation-delay:-0.15s]" />
													<span className="w-2 h-2 rounded-full bg-[var(--foreground-secondary)] animate-bounce" />
												</div>
											</div>
										</div>
									)}

									{/* 错误 */}
									{error && (
										<div className="flex items-start gap-2">
											<div className="w-7 h-7 rounded-full bg-[var(--primary)] flex items-center justify-center text-white text-xs flex-shrink-0 mt-1">AI</div>
											<div className="ui-card-shell flex-1 bg-[var(--card-bg)] rounded-none p-4">
												<p className="ui-type-body text-red-400 mb-3">
													{error.includes('LLM服务连接异常')
														? 'AI分析服务暂时不可用，请刷新页面后继续，您的进度已自动保存。'
														: error}
												</p>
												<div className="flex gap-2 flex-wrap">
													<button onClick={() => router.push('/')} className="ui-type-meta px-3 py-1.5 bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white rounded-lg transition-colors">返回首页</button>
													<button onClick={() => { sessionStorage.setItem(`force_resume_${sessionId}`, '1'); window.location.reload(); }} className="ui-type-meta px-3 py-1.5 bg-[var(--card-bg)] border border-[var(--border-color)] text-[var(--foreground)] rounded-lg hover:bg-[var(--sidebar-bg)] transition-colors">
														{error.includes('LLM服务连接异常') ? '刷新后继续' : error.includes('已中断') ? '尝试继续执行' : '重新加载'}
													</button>
												</div>
											</div>
										</div>
									)}

									{/* 被拒绝 */}
									{!error && status?.status === 'rejected' && (
										<div className="flex items-start gap-2">
											<div className="w-7 h-7 rounded-full bg-[var(--primary)] flex items-center justify-center text-white text-xs flex-shrink-0 mt-1">AI</div>
											<div className="ui-card-shell flex-1 bg-[var(--card-bg)] rounded-none p-4">
												<p className="text-red-400 font-medium mb-2">该需求暂时无法受理</p>
												{status.rejection_reason && (
													<p className="ui-type-meta text-[var(--foreground-secondary)] mb-2">
														原因：{status.rejection_reason === 'content_safety_violation' ? '内容安全违规' : status.rejection_reason === 'not_design_related' ? '非设计领域问题' : status.rejection_reason}
													</p>
												)}
												{status.rejection_message && (
													<p className="ui-type-body text-[var(--foreground)] mb-3 whitespace-pre-wrap">{status.rejection_message}</p>
												)}
												<button onClick={() => router.push('/')} className="ui-type-meta px-3 py-1.5 bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white rounded-lg transition-colors">返回首页</button>
											</div>
										</div>
									)}

									{/* 执行进度气泡 */}
									{!error && status && status.status !== 'rejected' && status.status !== 'completed' && (
										<div className="flex items-start gap-2">
											<div className="w-7 h-7 rounded-full bg-[var(--primary)] flex items-center justify-center text-white text-xs flex-shrink-0 mt-1">AI</div>
											<div className="ui-card-shell flex-1 bg-[var(--card-bg)] rounded-none px-4 py-3">
												<div className="flex items-center gap-2 mb-2">
													<span className="ui-type-subtitle font-medium text-[var(--foreground)]">
														{(() => {
															const stageName = formatNodeName(status.current_stage);
															const detailName = status.detail ? formatNodeName(status.detail) : null;
															if (detailName && detailName !== '准备中...' && detailName !== status.detail) return detailName;
															return stageName;
														})()}
													</span>
													{status.status === 'running' && <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--primary)]" />}
												</div>
												{status.progress !== undefined && (
													<div className="space-y-1 mb-2">
														<div className="ui-type-meta flex justify-between text-[var(--foreground-secondary)]">
															<span>进度</span>
															<span>{Math.round(status.progress * 100)}%</span>
														</div>
														<div className="w-full bg-[var(--sidebar-bg)] rounded-full h-1.5 overflow-hidden">
															<div className="bg-[var(--primary)] h-full rounded-full transition-all duration-500 ease-out" style={{ width: `${status.progress * 100}%` }} />
														</div>
													</div>
												)}
												{nodeHistory.length > 0 && (
													<details className="group">
														<summary className="ui-type-meta text-[var(--foreground-secondary)] cursor-pointer select-none hover:text-[var(--foreground)] transition-colors list-none flex items-center gap-1">
															<span className="group-open:rotate-90 transition-transform inline-block">▶</span>
															执行步骤（{nodeHistory.length} 条）
														</summary>
														<div className="mt-2 space-y-1 max-h-36 overflow-y-auto pr-1">
															{nodeHistory.slice(-30).map((entry, idx) => (
																<div key={idx} className="ui-type-meta flex items-center gap-2 text-[var(--foreground-secondary)]">
																	<span className="w-1.5 h-1.5 rounded-full bg-[var(--primary)] flex-shrink-0" />
																	<span className="flex-1">{formatNodeName(entry.node)}</span>
																	<span className="font-mono flex-shrink-0">{entry.time}</span>
																</div>
															))}
														</div>
													</details>
												)}
											</div>
										</div>
									)}

									{/* 意图确认气泡（step 1）*/}
									{currentProgressiveStep === 1 && (
												<div className="flex items-start gap-2">
													<div className="w-7 h-7 rounded-full bg-[var(--primary)] flex items-center justify-center text-white text-xs flex-shrink-0 mt-1">AI</div>
													<div className="ui-card-shell flex-1 bg-[var(--card-bg)] rounded-none p-4 space-y-3">
														{progressiveStepData?.requirements_review?.breakthrough_insight && (
															<p className="ui-type-body text-[var(--foreground)] italic">
																&ldquo;{progressiveStepData.requirements_review.breakthrough_insight}&rdquo;
															</p>
														)}
														{(() => {
															const deliveries: any[] = (progressiveStepData?.delivery_types?.options ?? []).filter((o: any) => o.recommended);
															if (!deliveries.length) return null;
															return (
																<div>
																	<p className="ui-type-meta text-[var(--foreground-secondary)] mb-1.5">建议输出：</p>
																	<div className="flex flex-wrap gap-1.5">
																		{deliveries.map((o: any) => (
																			<span key={o.id} className="ui-type-meta px-2.5 py-1 rounded-full bg-[var(--primary)]/15 text-[var(--primary)] border border-[var(--primary)]/30">{o.label}</span>
																		))}
																	</div>
																</div>
															);
														})()}
														<div className="flex gap-2 pt-1">
															<button
																onClick={() => {
																	const dOpts: any[] = progressiveStepData?.delivery_types?.options ?? [];
																	const mOpts: any[] = progressiveStepData?.identity_modes?.options ?? [];
																	const cOpts: any[] = progressiveStepData?.recommended_constraints?.options ?? [];
																	handleProgressiveStepConfirm({
																		selected_deliveries: dOpts.filter((o: any) => o.recommended).map((o: any) => o.id),
																		selected_modes: mOpts.filter((o: any) => o.recommended).map((o: any) => o.id),
																		confirmed_constraints: cOpts.filter((o: any) => o.recommended).map((o: any) => ({ id: o.id, label: o.label, desc: o.desc, source: 'ai_recommended' })),
																	});
																}}
																className="ui-type-meta px-4 py-2 bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white rounded-lg transition-colors font-medium flex items-center gap-1.5"
															>
																<CheckCircle2 className="w-4 h-4" />
																确认，开始分析
															</button>
														</div>
													</div>
												</div>
									)}

									{/* 已完成 */}
									{!error && status?.status === 'completed' && (
										<div className="flex items-start gap-2">
											<div className="w-7 h-7 rounded-full bg-[var(--primary)] flex items-center justify-center text-white text-xs flex-shrink-0 mt-1">AI</div>
											<div className="ui-card-shell flex-1 bg-[var(--card-bg)] rounded-none p-4">
												<div className="flex items-center gap-2 mb-3">
													<CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
													<span className="font-medium text-[var(--foreground)]">分析已完成</span>
												</div>
												<div className="flex gap-2 flex-wrap">
													<button onClick={() => router.push(`/report/${sessionId}`)} className="ui-type-meta px-4 py-2 bg-[var(--primary)] hover:bg-[var(--primary-hover)] text-white rounded-lg transition-colors font-medium">查看分析报告</button>
													<button onClick={() => router.push('/')} className="ui-type-meta px-4 py-2 bg-[var(--card-bg)] border border-[var(--border-color)] text-[var(--foreground)] rounded-lg hover:bg-[var(--sidebar-bg)] transition-colors">返回首页</button>
												</div>
											</div>
										</div>
									)}

									{/* 滚动锚点 */}
									<div ref={projectChatEndRef} />
								</div>
							</div>
						)}

						{/* 项目态浮窗交互（步骤2+/确认/预检，悬浮于输入栏上方） */}
						{systemMode === 'project' && (currentProgressiveStep > 1 || showRoleTaskReview || showQualityPreflight || showQuestionnaire || (showConfirmation && confirmationData?.interaction_type !== 'role_and_task_unified_review')) && (
							<div className="absolute bottom-[72px] left-0 right-0 z-20 pb-2 flex justify-center pointer-events-none">
								<div className="w-full pointer-events-auto">
									<div className="ui-card-shell ui-card-shell-strong bg-[var(--card-bg)] rounded-none overflow-auto max-h-[60vh]">
										{currentProgressiveStep > 1 ? (
											<UnifiedProgressiveQuestionnaireModal inline={true} isOpen={true} currentStep={currentProgressiveStep} stepData={progressiveStepData} onConfirm={handleProgressiveStepConfirm} onSkip={handleProgressiveStepSkip} sessionId={sessionId as string} userInput={userInput} />
										) : showRoleTaskReview ? (
											<RoleTaskReviewModal inline={true} isOpen={true} data={roleTaskReviewData} onConfirm={handleRoleTaskReview} />
										) : showQualityPreflight ? (
											<QualityPreflightModal inline={true} isOpen={true} data={qualityPreflightData} onConfirm={handleQualityPreflightConfirm} onCancel={handleQualityPreflightCancel} />
										) : showQuestionnaire ? (
											<QuestionnaireModal inline={true} isOpen={true} questionnaire={questionnaireData} onSubmit={handleQuestionnaireSubmit} />
										) : (
											<ConfirmationModal inline={true} isOpen={true} title={'确认'} message={confirmationData?.message || '请确认以下信息'} summary={confirmationData?.requirements_summary || confirmationData} onConfirm={handleConfirmation} />
										)}
									</div>
								</div>
							</div>
						)}

						{/* UserQuestion 追问提示卡 */}
						{systemMode === 'project' && showUserQuestion && userQuestionData && (
							<div className="absolute bottom-[72px] left-0 right-0 z-20 pb-2 flex justify-center pointer-events-none">
								<div className="w-full pointer-events-auto">
									<div className="ui-card-shell ui-card-shell-strong bg-[var(--card-bg)] rounded-none px-5 py-4">
										<p className="ui-type-meta font-semibold text-[var(--primary)] mb-1.5">AI 追问</p>
										<p className="ui-type-body text-[var(--foreground)]">{userQuestionData.question || '请补充说明'}</p>
									</div>
								</div>
							</div>
						)}

						{/* 项目态常驻底部输入栏 */}
						{systemMode === 'project' && (
							<div
								className="flex-shrink-0 border-t border-[var(--border-color)] bg-[color:rgba(24,24,27,0.96)] backdrop-blur-md shadow-[0_-14px_32px_rgba(0,0,0,0.28)]"
								style={{ paddingInline: adaptiveRightContentGutter, paddingTop: '8px', paddingBottom: '8px' }}
							>
								<div className="flex gap-2 items-end w-full mx-auto" style={{ width: rightPanelReadableWidth }}>
									<textarea
										value={projectInputValue}
										onChange={(e) => setProjectInputValue(e.target.value)}
										onKeyDown={(e) => {
											if (e.key === 'Enter' && !e.shiftKey && showUserQuestion) {
												e.preventDefault();
												if (projectInputValue.trim()) {
													handleUserQuestionSubmit({ question: projectInputValue.trim(), requiresAnalysis: false });
													setProjectInputValue('');
												}
											}
										}}
										disabled={!showUserQuestion || userQuestionSubmitting}
										placeholder={
											showUserQuestion
												? '回复 AI 的追问...'
												: status?.status === 'running' ? '正在分析中，请稍候...'
												: status?.status === 'waiting_for_input' ? '请在上方弹窗中操作'
												: status?.status === 'completed' ? '分析已完成'
												: '等待响应...'
										}
										rows={1}
										className="ui-type-body flex-1 min-h-[46px] bg-[var(--card-bg)] border border-[var(--border-color)] rounded-xl px-4 py-2.5 text-[var(--foreground)] resize-none focus:outline-none focus:border-[var(--primary)] disabled:opacity-50 disabled:cursor-not-allowed placeholder:text-[var(--foreground-secondary)]"
									/>
									<button
										disabled={!showUserQuestion || !projectInputValue.trim() || userQuestionSubmitting}
										onClick={() => {
											if (!projectInputValue.trim() || !showUserQuestion) return;
											handleUserQuestionSubmit({ question: projectInputValue.trim(), requiresAnalysis: false });
											setProjectInputValue('');
										}}
										className="p-2.5 bg-[var(--primary)] hover:bg-[var(--primary-hover)] disabled:opacity-30 disabled:cursor-not-allowed text-white rounded-xl transition-colors flex-shrink-0"
									>
										<SendHorizontal className="w-4 h-4" />
									</button>
								</div>
							</div>
						)}

					</div>
				</div>
			</div>
			</div>
			)}
			<div
					className={`fixed inset-y-0 right-0 w-96 bg-[var(--card-bg)] border-l border-[var(--border-color)] shadow-2xl transform transition-transform duration-300 ease-in-out z-50 ${
						selectedNode ? 'translate-x-0' : 'translate-x-full'
					}`}
				>
					<div className="h-full flex flex-col">
						<div className="p-4 border-b border-[var(--border-color)] flex items-center justify-between">
							<h3 className="ui-type-subtitle font-semibold">节点详情</h3>
							<button
								onClick={closeNodeDetail}
								className="p-2 text-gray-400 hover:text-white hover:bg-[var(--sidebar-bg)] rounded-lg"
							>
								<X className="w-5 h-5" />
							</button>
						</div>

						<div className="flex-1 overflow-y-auto p-4 space-y-6">
							<div>
								<div className="ui-type-meta text-gray-500 uppercase tracking-wider mb-1">节点 ID</div>
								<div className="ui-type-meta font-mono bg-[var(--sidebar-bg)] p-2 rounded border border-[var(--border-color)]">
									{selectedNode}
								</div>
							</div>

							{selectedNode && nodeDetails[selectedNode] && (
								<div>
									<div className="ui-type-meta text-gray-500 uppercase tracking-wider mb-1">当前状态</div>
									<div
										className={`ui-type-meta inline-flex px-2 py-1 rounded font-medium border ${
											nodeDetails[selectedNode].status === 'completed'
												? 'bg-green-900/20 text-green-400 border-green-900/30'
												: nodeDetails[selectedNode].status === 'running'
												? 'bg-blue-900/20 text-blue-400 border-blue-900/30'
												: nodeDetails[selectedNode].status === 'error'
												? 'bg-red-900/20 text-red-400 border-red-900/30'
												: 'bg-gray-800 text-gray-400 border-gray-700'
										}`}
									>
										{nodeDetails[selectedNode].status}
									</div>
								</div>
							)}

							{selectedNodeData.length > 0 && (
								<div>
									<div className="ui-type-meta text-gray-500 uppercase tracking-wider mb-2">执行记录</div>
									<div className="space-y-3">
										{selectedNodeData.map((record, index) => (
											<div key={index} className="bg-[var(--sidebar-bg)] rounded-lg p-3 border border-[var(--border-color)]">
												<div className="ui-type-meta text-gray-500 mb-1 font-mono">{record.time}</div>
												<div className="ui-type-body text-gray-300">{record.detail || '无详细信息'}</div>
											</div>
										))}
									</div>
								</div>
							)}
						</div>
					</div>
				</div>

				{selectedNode && (
					<div
						className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
						onClick={closeNodeDetail}
					/>
				)}
		</div>
	);
}
