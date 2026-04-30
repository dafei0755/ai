'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ChangeEvent, SyntheticEvent } from 'react';
import { describeArcPath, getDxfFill, getDxfStroke, getDxfTextFill, parseDxfPreviewGeometry } from '@/lib/dxfPreview';
import type { DxfPreviewGeometry } from '@/lib/dxfPreview';
import {
	ArrowRight,
	CheckCircle2,
	GitBranch,
	Layers3,
	Lock,
	MessageSquareText,
	Minus,
	Plus,
	RefreshCcw,
	SendHorizontal,
	Upload,
	ZoomIn,
	ZoomOut,
} from 'lucide-react';

type PlanSandboxSpace = '大堂' | '餐厅' | '客房' | '公区' | '连廊' | '后勤';

type PlanVersion = {
	id: string;
	name: string;
	stage: 'baseline' | 'iterating' | 'frozen';
	note: string;
	updatedAt: string;
	basedOnBriefVersion: string;
	layoutId?: string;
	strategyId?: string;
	score?: number;
};

type PlanStrategy = {
	id: string;
	title: string;
	summary: string;
	tradeoff: string;
	score: number;
};

type SandboxMetric = {
	label: string;
	value: string;
	tone: 'good' | 'normal' | 'risk';
};

type SandboxParameter = {
	label: string;
	value: number;
	left: string;
	right: string;
};

type LayoutScore = {
	functional_efficiency?: number;
	privacy_order?: number;
	view_resource?: number;
	renovation_cost?: number;
	project_fit?: number;
	user_preference_fit?: number;
};

type LayoutSpace = {
	space_id: string;
	name: string;
	function?: string;
	x: number;
	y: number;
	w: number;
	h: number;
	area_target_m2?: number;
	privacy_level?: 'public' | 'semi_public' | 'private' | 'service';
	locked?: boolean;
	adjacent_to?: string[];
	design_notes?: string[];
};

type LayoutVariant = {
	variant_id: string;
	name: string;
	intent: {
		intent_id: string;
		title: string;
		strategy: string;
		primary_axis?: string;
		spatial_priorities?: string[];
		accepted_tradeoffs?: string[];
		source_experts?: string[];
		rationale?: string;
	};
	layout: {
		layout_id: string;
		strategy: string;
		spaces: LayoutSpace[];
		circulation?: Record<string, string[]>;
		open_boundaries?: string[][];
		closed_boundaries?: string[][];
		score?: LayoutScore;
		risks?: string[];
		explanation?: string;
	};
	status?: 'candidate' | 'selected' | 'rejected' | 'frozen';
	comparison_summary?: string;
};

type LayoutGenerationPackage = {
	package_id: string;
	session_id?: string;
	variants: LayoutVariant[];
	version_graph?: {
		graph_id?: string;
		nodes?: Array<{
			version_id: string;
			layout_id: string;
			status?: 'candidate' | 'selected' | 'rejected' | 'frozen';
			decision_trace?: string[];
		}>;
		selected_version_id?: string;
		frozen_version_id?: string;
	};
	generation_notes?: string[];
};

type PlanTopicState = {
	space?: string;
	status?: string;
	sourceType?: 'cad' | 'dxf' | 'pdf' | 'image' | 'manual';
	uploadedFileName?: string;
	uploadedFileUrl?: string;
	uploadedFileSize?: number;
	mimeType?: string;
	parseMessage?: string;
	parsedLayers?: string[];
	parsedEntityCounts?: Record<string, number>;
	reconstruction?: FloorPlanReconstruction;
	legacyReconstructionBackup?: FloorPlanReconstruction;
	legacyMigrationAt?: string;
	updatedAt?: string;
};

type FloorPlanElementKind = 'analysis_region' | 'space_boundary' | 'function_zone' | 'wall_trace' | 'door' | 'window' | 'column' | 'height_marker';
type FloorPlanGeometryType = 'rect' | 'polygon' | 'path';
type FloorPlanPoint = { x: number; y: number };
type FloorPlanRect = { x: number; y: number; w: number; h: number };
type FloorPlanLayerKey = 'baseMap' | 'region' | 'rooms' | 'walls' | 'columns' | 'doors' | 'windows' | 'labels';
type FloorPlanDebugLayerKey = 'none' | 'regionScopedLines' | 'classifiedWallLines' | 'focusedWallLines' | 'strictMergedLines' | 'pairedWallLines' | 'relaxedCandidateLines' | 'relaxedMergedLines' | 'structureLines';

type FloorPlanElement = {
	id: string;
	kind: FloorPlanElementKind;
	label: string;
	geometryType?: FloorPlanGeometryType;
	x: number;
	y: number;
	w: number;
	h: number;
	points?: FloorPlanPoint[];
	widthMm?: number;
	depthMm?: number;
	areaSqm?: number;
	confidence: number;
	status: 'candidate' | 'confirmed' | 'edited';
	coordinateProvenance?: CoordinateProvenance;
};

type FloorPlanIssue = {
	id: string;
	type: string;
	severity: 'info' | 'warning' | 'error';
	targetIds: string[];
	message: string;
	suggestedAction: string;
};

type FloorPlanQuality = {
	score: number;
	breakdown: {
		scale: number;
		wallConnectivity: number;
		roomClosure: number;
		openingBinding: number;
		ocrMatch: number;
		issuePenalty: number;
	};
};

type FloorPlanPrimitiveRef = {
	id: string;
	kind: string;
	bbox: [number, number, number, number];
	confidence: number;
};

type CoordinateProvenance = {
	coordSpace: 'page' | 'content' | 'main_plan_box' | 'ir';
	referenceBoxId: string;
	sourceContentBBox?: [number, number, number, number];
	sourcePageBBox?: [number, number, number, number];
	mainPlanBBox: [number, number, number, number];
	renderBBox?: [number, number, number, number];
};

type GateIssue = {
	id: string;
	severity: 'info' | 'warning' | 'error';
	message: string;
	targetIds: string[];
};

type GateResult = {
	status: 'passed' | 'failed';
	score: number;
	issues: GateIssue[];
	metrics: Record<string, number>;
};

type ReviewIssue = {
	id: string;
	type: string;
	severity: 'info' | 'warning' | 'error';
	message: string;
	targetIds: string[];
};

type FloorPlanCompileResult = {
	status: 'candidate_ready' | 'gate_failed' | 'ir_ready';
	detectionLayers?: {
		structureLines?: FloorPlanPrimitiveRef[];
		regionScopedLines?: FloorPlanPrimitiveRef[];
		classifiedWallLines?: FloorPlanPrimitiveRef[];
		focusedWallLines?: FloorPlanPrimitiveRef[];
		strictMergedLines?: FloorPlanPrimitiveRef[];
		pairedWallLines?: FloorPlanPrimitiveRef[];
		relaxedCandidateLines?: FloorPlanPrimitiveRef[];
		relaxedMergedLines?: FloorPlanPrimitiveRef[];
	};
	gates: {
		contract: GateResult;
		coordinate?: GateResult;
		structureBackbone?: GateResult;
		geometry: GateResult;
		system: GateResult;
	};
	reviewQueue: {
		wallFragments: ReviewIssue[];
		suspectedMissingColumns: ReviewIssue[];
		unboundOpenings: ReviewIssue[];
		lowConfidenceSpaces: ReviewIssue[];
		scaleIssues: ReviewIssue[];
	};
	formalPromotionAllowed?: boolean;
	promotionBlockers?: string[];
	wallGraph?: {
		walls: unknown[];
		joints: unknown[];
		danglingWallIds: string[];
		fragmentGroups: string[][];
		thicknessClusters: number[];
	};
};

type FloorPlanPipelineStats = {
	regionScoped?: number;
	classifiedWall?: number;
	strictCandidates?: number;
	focusedStrictCandidates?: number;
	strictMerged?: number;
	pairedWalls?: number;
	relaxedScope?: number;
	relaxedCandidates?: number;
	relaxedMerged?: number;
	selectedSegments?: number;
	selectedPipeline?: string;
};

type FloorPlanDiagnostics = {
	rawSegments?: number;
	scopedSegments?: number;
	wallSegments?: number;
	doorCandidates?: number;
	windowCandidates?: number;
	columnCandidates?: number;
	filteredOut?: number;
	dimensionsInRegion?: number;
	scaleEvidenceSource?: string;
	pdfCoordinateTransform?: string;
	classCounts?: Record<string, number>;
	pipelineStats?: FloorPlanPipelineStats;
	debugLayerCounts?: Record<string, number>;
	mode?: string;
	blockedBy?: string;
	regionFallback?: boolean;
	regionInsufficient?: boolean;
	formalPromotionAllowed?: boolean;
	promotionBlockers?: string[];
	coordinateConsistency?: { status?: string; score?: number; metrics?: Record<string, number> };
	structureBackbone?: { status?: string; score?: number; metrics?: Record<string, number> };
	primaryCluster?: {
		focused?: boolean;
		componentCount?: number;
		focusUsedAsMainPlanBox?: boolean;
		mainPlanBoxSource?: string;
	};
};

type FloorPlanReconstruction = {
	status: 'raw' | 'normalized' | 'traced' | 'zoned' | 'aligned' | 'height_ready';
	irVersion: string;
	sourceFormat?: PlanTopicState['sourceType'];
	coordinateSystem: {
		unit: 'mm' | 'm' | 'px';
		scaleStatus: 'uncalibrated' | 'estimated' | 'confirmed';
		northStatus: 'missing' | 'detected' | 'confirmed';
	};
	objectCounts: Record<string, number>;
	spaceBoundaryCount: number;
	functionZoneCount: number;
	alignment?: {
		matchedSpace?: string;
		confidence?: number;
		status?: 'candidate' | 'confirmed' | 'conflict';
	};
	heightProfile?: {
		ceilingHeight?: number;
		beamBottomHeight?: number;
		doorHeight?: number;
		windowSillHeight?: number;
		status: 'missing' | 'estimated' | 'confirmed';
	};
	scaleCalibration?: {
		mmPerPixel?: number;
		source: 'pdf_text' | 'fallback' | 'manual' | 'pdf' | 'dxf' | string;
		samples: number;
	};
	elements: FloorPlanElement[];
	pendingIssues: Array<string | FloorPlanIssue>;
	floorPlanIR?: unknown;
	draftFloorPlanIR?: unknown;
	compileResult?: FloorPlanCompileResult;
	gates?: FloorPlanCompileResult['gates'];
	reviewQueue?: FloorPlanCompileResult['reviewQueue'];
	quality?: FloorPlanQuality;
	sourceContentBox?: FloorPlanRect;
	mainPlanBox?: FloorPlanRect;
	mainPlanBoxSource?: 'detected_plan_frame' | 'user_roi' | 'fallback_recognition_region' | string;
	focusBounds?: FloorPlanRect;
	focusBoundsInContent?: FloorPlanRect;
	focusUsedAsMainPlanBox?: boolean;
	recognitionBoxOnPage?: FloorPlanRect;
	coordinateSpace?: 'page' | 'content' | 'main_plan_box';
	diagnostics?: FloorPlanDiagnostics;
	irSchemaVersion?: string;
	sheetIR?: unknown;
	updatedAt: string;
};

interface PlanSandboxPanelProps {
	sessionId: string;
	activeSpace: PlanSandboxSpace;
	spaceOptions: PlanSandboxSpace[];
	onActiveSpaceChange?: (space: PlanSandboxSpace) => void;
	onEnterBoardSpace?: (space: PlanSandboxSpace) => void;
	onInjectReference?: (label: string) => void;
	className?: string;
}

const nowLabel = () =>
	new Date().toLocaleString('zh-CN', {
		month: '2-digit',
		day: '2-digit',
		hour: '2-digit',
		minute: '2-digit',
	});

const buildStorageKey = (sessionId: string, activeSpace: string) => `analysis.planSandbox.versions.${sessionId}.${activeSpace}`;
const buildPlanTopicStorageKey = (sessionId: string) => `ipa.space.plan-topic.v1.${sessionId}`;
const PLAN_TOPICS_API_PATH = '/api/plan-topics';
const FLOOR_PLAN_IR_COORDINATE_SPACE = 'main_plan_box';
const FLOOR_PLAN_IR_SCHEMA_VERSION = 'sheetir-mainplan-v2';

const migratePlanTopics = (source: Record<string, PlanTopicState>) => {
	let changed = false;
	const topics = Object.fromEntries(Object.entries(source).map(([space, topic]) => {
		if (!topic?.reconstruction || (
			topic.reconstruction.coordinateSpace === FLOOR_PLAN_IR_COORDINATE_SPACE &&
			topic.reconstruction.irSchemaVersion === FLOOR_PLAN_IR_SCHEMA_VERSION
		)) return [space, topic];
		changed = true;
		return [space, {
			...topic,
			status: topic.uploadedFileUrl ? 'uploaded' : topic.status,
			parseMessage: '旧版 FloorPlanIR 坐标/主图域已失效，已备份旧结果，请重新生成。',
			legacyReconstructionBackup: topic.legacyReconstructionBackup ?? topic.reconstruction,
			legacyMigrationAt: topic.legacyMigrationAt ?? new Date().toISOString(),
			reconstruction: undefined,
		} satisfies PlanTopicState];
	})) as Record<string, PlanTopicState>;
	return { topics, changed };
};

const DEFAULT_LAYER_VISIBILITY: Record<FloorPlanLayerKey, boolean> = {
	baseMap: true,
	region: true,
	rooms: true,
	walls: true,
	columns: true,
	doors: true,
	windows: true,
	labels: true,
};

const DEBUG_LAYER_META: Record<FloorPlanDebugLayerKey, { label: string; stroke: string; fill: string }> = {
	none: { label: '关闭调试', stroke: 'transparent', fill: 'transparent' },
	regionScopedLines: { label: 'ROI 原始线', stroke: 'rgba(148,163,184,0.72)', fill: 'rgba(148,163,184,0.36)' },
	classifiedWallLines: { label: '分类墙线', stroke: 'rgba(56,189,248,0.9)', fill: 'rgba(56,189,248,0.45)' },
	focusedWallLines: { label: 'Focus 墙线', stroke: 'rgba(168,85,247,0.9)', fill: 'rgba(168,85,247,0.42)' },
	strictMergedLines: { label: '严格合并', stroke: 'rgba(34,197,94,0.92)', fill: 'rgba(34,197,94,0.46)' },
	pairedWallLines: { label: '平行墙中线', stroke: 'rgba(245,158,11,0.95)', fill: 'rgba(245,158,11,0.5)' },
	relaxedCandidateLines: { label: '宽松候选线', stroke: 'rgba(20,184,166,0.82)', fill: 'rgba(20,184,166,0.4)' },
	relaxedMergedLines: { label: '宽松合并', stroke: 'rgba(14,165,233,0.82)', fill: 'rgba(14,165,233,0.4)' },
	structureLines: { label: '最终清洁线', stroke: 'rgba(244,63,94,0.95)', fill: 'rgba(244,63,94,0.5)' },
};

const buildInitialVersion = (activeSpace: string): PlanVersion => ({
	id: 'v0',
	name: `FloorPlanIR_${activeSpace}_v0 基线`,
	stage: 'baseline',
	note: `从项目底盘读取 ${activeSpace} 的图纸、空间画像、约束与策略目标，形成可推演基线。`,
	updatedAt: nowLabel(),
	basedOnBriefVersion: 'AlignedBrief/SPG draft',
});

const SPACE_STRATEGY_MAP: Record<string, PlanStrategy[]> = {
	大堂: [
		{ id: 'A', title: '低干预更', summary: '保留空间秩序，优化接待、等候与导视关系', tradeoff: '展示冲击力较弱，但底盘匹配度最高', score: 91 },
		{ id: 'B', title: '到达体验强化', summary: '强化入口识别和第一停留节点，适合对外展示', tradeoff: '材料和灯光介入增加，改造强度升高', score: 84 },
		{ id: 'C', title: '运营效率优先', summary: '前置服务台并隐藏后勤动线，提升管理效率', tradeoff: '公共区松弛感略降，需要家具尺度缓冲', score: 87 },
	],
	餐厅: [
		{ id: 'A', title: '高翻台效', summary: '压缩服务路径，优化桌型组合与出餐半径', tradeoff: '社交停留感较弱，适合高峰运营', score: 88 },
		{ id: 'B', title: '社交停留优先', summary: '扩大共享餐桌和景观停留面，强化度假情绪', tradeoff: '坪效略降，需要控制桌距', score: 86 },
		{ id: 'C', title: '前后场分', summary: '分离客流、服务流和补给流，降低交叉干扰', tradeoff: '后场占比上升，需校核面积效率', score: 90 },
	],
	客房: [
		{ id: 'A', title: '景观面优', summary: '把停留、睡眠和泡浴节点尽量转向最佳景观面', tradeoff: '收纳与后勤补给路径需额外校核', score: 89 },
		{ id: 'B', title: '房效优先', summary: '稳定房型模块，提高复制效率和可施工性', tradeoff: '个性化体验较弱', score: 86 },
		{ id: 'C', title: '私密梯度强化', summary: '拉开入口、起居、睡眠、卫浴之间的私密层级', tradeoff: '动线略增长，但体验更完整', score: 92 },
	],
};

const DEFAULT_STRATEGIES: PlanStrategy[] = [
	{ id: 'A', title: '效率优先', summary: '压缩无效路径，强化核心功能邻接', tradeoff: '体验层次略少，但执行稳定', score: 86 },
	{ id: 'B', title: '体验优先', summary: '增加停留节点和空间节奏，提升使用舒适度', tradeoff: '面积效率下降，需要控制成本', score: 84 },
	{ id: 'C', title: '弹性优', summary: '保留可变模块，为后续运营和深化留余量', tradeoff: '初版表达不如单一策略强', score: 88 },
];

const buildParameters = (space: string): SandboxParameter[] => {
	if (space === '大堂') {
		return [
			{ label: '到达识别', value: 72, left: '克制', right: '强化' },
			{ label: '等候舒', value: 66, left: '基础', right: '舒' },
			{ label: '服务可达', value: 78, left: '隐藏', right: '高效' },
			{ label: '改造强', value: 38, left: '低干', right: '重构' },
		];
	}
	if (space === '餐厅') {
		return [
			{ label: '翻台效率', value: 76, left: '舒缓', right: '高效' },
			{ label: '社交停留', value: 64, left: '短停', right: '强停' },
			{ label: '前后场分', value: 82, left: '混合', right: '清晰' },
			{ label: '坪效强度', value: 70, left: '体验', right: '坪效' },
		];
	}
	return [
		{ label: '空间开放度', value: 62, left: '独立', right: '开' },
		{ label: '功能密度', value: 68, left: '舒展', right: '紧凑' },
		{ label: '动线效率', value: 74, left: '弱组', right: '高效' },
		{ label: '成本控制', value: 58, left: '弹', right: '严格' },
	];
};

const buildMetrics = (activeStrategy: PlanStrategy, activeVariant?: LayoutVariant): SandboxMetric[] => {
	const score = activeVariant?.layout.score;
	if (score) {
		const costScore = score.renovation_cost ?? 70;
		return [
			{ label: '底盘匹配', value: `${score.project_fit ?? activeStrategy.score}`, tone: (score.project_fit ?? 0) >= 88 ? 'good' : 'normal' },
			{ label: '动线效率', value: `${score.functional_efficiency ?? 0}`, tone: (score.functional_efficiency ?? 0) >= 80 ? 'good' : 'normal' },
			{ label: '空间秩序', value: `${score.privacy_order ?? 0}`, tone: (score.privacy_order ?? 0) >= 80 ? 'good' : 'normal' },
			{ label: '改造友好', value: `${costScore}`, tone: costScore >= 78 ? 'good' : costScore < 60 ? 'risk' : 'normal' },
			{ label: '实施风险', value: activeVariant.layout.risks?.length ? `${activeVariant.layout.risks.length}项` : '低', tone: activeVariant.layout.risks?.length ? 'normal' : 'good' },
		];
	}
	return [
		{ label: '底盘匹配', value: `${activeStrategy.score}`, tone: activeStrategy.score >= 88 ? 'good' : 'normal' },
		{ label: '动线效率', value: activeStrategy.id === 'C' ? '90' : '84', tone: 'good' },
		{ label: '空间识别', value: activeStrategy.id === 'B' ? '92' : '78', tone: activeStrategy.id === 'B' ? 'good' : 'normal' },
		{ label: '改造强度', value: activeStrategy.id === 'B' ? '高' : '低', tone: activeStrategy.id === 'B' ? 'risk' : 'good' },
		{ label: '实施风险', value: activeStrategy.id === 'B' ? '中低' : '低', tone: activeStrategy.id === 'B' ? 'normal' : 'good' },
	];
};

const mapVariantToStrategy = (variant: LayoutVariant, index: number): PlanStrategy => ({
	id: variant.variant_id,
	title: variant.name || variant.intent.title || `推演版本 ${index + 1}`,
	summary: variant.comparison_summary || variant.layout.explanation || variant.intent.primary_axis || '来自多版本平面推演引擎',
	tradeoff: variant.intent.accepted_tradeoffs?.[0] || variant.layout.risks?.[0] || '等待用户选择后进入下一轮校核',
	score: variant.layout.score?.project_fit ?? 76,
});

export function PlanSandboxPanel({
	sessionId,
	activeSpace,
	spaceOptions,
	onActiveSpaceChange,
	onEnterBoardSpace,
	onInjectReference,
	className,
}: PlanSandboxPanelProps) {
	const [isSpaceSyncing, setIsSpaceSyncing] = useState(false);
	const [spaceSyncedAt, setSpaceSyncedAt] = useState<string>(nowLabel());
	const [versions, setVersions] = useState<PlanVersion[]>([buildInitialVersion(activeSpace)]);
	const [activeVersionId, setActiveVersionId] = useState<string>('v0');
	const [headerHovered, setHeaderHovered] = useState(false);
	const [activeTab, setActiveTab] = useState<'project' | 'baseline' | 'versions' | 'export' | 'properties'>('project');
	const [canvasTransform, setCanvasTransform] = useState({ zoom: 1, x: 0, y: 0 });
	const [isCanvasPanning, setIsCanvasPanning] = useState(false);
	const [showBaseMap, setShowBaseMap] = useState(true);
	const [baseMapOpacity, setBaseMapOpacity] = useState(92); // 0-100
	const [baseMapTint, setBaseMapTint] = useState<string>(''); // '' = 原色, 否则叠色
	const [isTracingFloorPlan, setIsTracingFloorPlan] = useState(false);
	const [manualScaleMmPerNorm, setManualScaleMmPerNorm] = useState<number | null>(null);
	const [manualScaleMmPerPx, setManualScaleMmPerPx] = useState<number | null>(null);
	const [detectedMmPerNorm, setDetectedMmPerNorm] = useState<number | null>(null);
	// 比例尺标尺工具
	const [rulerActive, setRulerActive] = useState(false);
	const [rulerState, setRulerState] = useState<{ x0: number; y0: number; x1: number; y1: number; knownMm: number | null } | null>(null);
	const [rulerInputDraft, setRulerInputDraft] = useState<string>('');
	const [isRulerInputEditing, setIsRulerInputEditing] = useState(false);
	const rulerDragRef = useRef<{
		endpoint: 0 | 1 | 'body';
		pointerId: number;
		bodyStart?: { dragX: number; dragY: number; x0: number; y0: number; x1: number; y1: number };
	} | null>(null);
	const [isSelectingAnalysisRegion, setIsSelectingAnalysisRegion] = useState(false);
	const [analysisRegion, setAnalysisRegion] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
	const [analysisRegionDraft, setAnalysisRegionDraft] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
	const [selectedCandidateId, setSelectedCandidateId] = useState<string>('');
	const [hoveredCandidateId, setHoveredCandidateId] = useState<string>('');
	const [layerVisibility, setLayerVisibility] = useState<Record<FloorPlanLayerKey, boolean>>(DEFAULT_LAYER_VISIBILITY);
	const [planTopics, setPlanTopics] = useState<Record<string, PlanTopicState>>({});
	const [pdfPreviewDataUrl, setPdfPreviewDataUrl] = useState<string>('');
	const [dxfGeometry, setDxfGeometry] = useState<DxfPreviewGeometry | null>(null);
	const [dxfLoadError, setDxfLoadError] = useState<string | null>(null);
	const [baseMapAspect, setBaseMapAspect] = useState<number>(0.707);
	const [canvasSize, setCanvasSize] = useState({ width: 1, height: 1 });
	const [isUploadingPlan, setIsUploadingPlan] = useState(false);
	const [layoutPackage, setLayoutPackage] = useState<LayoutGenerationPackage | null>(null);
	const [isGeneratingLayoutVariants, setIsGeneratingLayoutVariants] = useState(false);
	const canvasViewportRef = useRef<HTMLDivElement | null>(null);
	const planUploadInputRef = useRef<HTMLInputElement | null>(null);
	const canvasPanDragRef = useRef<{
		pointerId: number;
		startX: number;
		startY: number;
		originX: number;
		originY: number;
	} | null>(null);
	const analysisRegionDragRef = useRef<{
		pointerId: number;
		startX: number;
		startY: number;
	} | null>(null);
	const baseStrategies = useMemo(() => SPACE_STRATEGY_MAP[activeSpace] ?? DEFAULT_STRATEGIES, [activeSpace]);
	const [activeStrategyId, setActiveStrategyId] = useState<string>(baseStrategies[0]?.id ?? 'A');
	const generatedStrategies = useMemo(
		() => layoutPackage?.variants?.map(mapVariantToStrategy) ?? [],
		[layoutPackage]
	);
	const strategies = generatedStrategies.length > 0 ? generatedStrategies : baseStrategies;
	const persistPlanTopicsToServer = useCallback(async (topics: Record<string, PlanTopicState>) => {
		try {
			await fetch(PLAN_TOPICS_API_PATH, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ sessionId, topics }),
			});
		} catch (error) {
			console.warn('[PlanSandboxPanel] persist plan topics to server failed:', error);
		}
	}, [sessionId]);

	useEffect(() => {
		setActiveStrategyId((SPACE_STRATEGY_MAP[activeSpace] ?? DEFAULT_STRATEGIES)[0].id);
		setLayoutPackage(null);
	}, [activeSpace]);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		setIsSpaceSyncing(true);
		try {
			const raw = window.localStorage.getItem(buildStorageKey(sessionId, activeSpace));
			if (!raw) {
				setVersions([buildInitialVersion(activeSpace)]);
				setActiveVersionId('v0');
				setSpaceSyncedAt(nowLabel());
				return;
			}
			const parsed = JSON.parse(raw) as { versions?: PlanVersion[]; activeVersionId?: string; layoutPackage?: LayoutGenerationPackage | null };
			if (Array.isArray(parsed?.versions) && parsed.versions.length > 0) {
				setVersions(parsed.versions);
				setActiveVersionId(parsed.activeVersionId ?? parsed.versions[0].id);
			}
			if (parsed.layoutPackage?.variants?.length) {
				setLayoutPackage(parsed.layoutPackage);
				setActiveStrategyId(parsed.activeVersionId ?? parsed.layoutPackage.variants[0].variant_id);
			}
			setSpaceSyncedAt(nowLabel());
		} catch (error) {
			console.error('[PlanSandboxPanel] restore versions failed:', error);
			setVersions([buildInitialVersion(activeSpace)]);
			setActiveVersionId('v0');
			setLayoutPackage(null);
		} finally {
			window.setTimeout(() => setIsSpaceSyncing(false), 180);
		}
	}, [activeSpace, sessionId]);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		try {
			window.localStorage.setItem(buildStorageKey(sessionId, activeSpace), JSON.stringify({ versions, activeVersionId, layoutPackage }));
		} catch (error) {
			console.error('[PlanSandboxPanel] persist versions failed:', error);
		}
	}, [activeSpace, activeVersionId, layoutPackage, sessionId, versions]);

	useEffect(() => {
		const viewport = canvasViewportRef.current;
		if (!viewport || typeof ResizeObserver === 'undefined') return;
		const updateSize = () => {
			const rect = viewport.getBoundingClientRect();
			setCanvasSize({
				width: Math.max(1, rect.width),
				height: Math.max(1, rect.height),
			});
		};
		updateSize();
		const observer = new ResizeObserver(updateSize);
		observer.observe(viewport);
		return () => observer.disconnect();
	}, []);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		let cancelled = false;
		const restorePlanTopics = async () => {
			try {
				const response = await fetch(`${PLAN_TOPICS_API_PATH}?sessionId=${encodeURIComponent(sessionId)}`);
				if (response.ok) {
					const payload = await response.json() as { topics?: Record<string, PlanTopicState> | null };
					if (payload.topics && typeof payload.topics === 'object') {
						const migrated = migratePlanTopics(payload.topics);
						if (!cancelled) setPlanTopics(migrated.topics);
						window.localStorage.setItem(buildPlanTopicStorageKey(sessionId), JSON.stringify(migrated.topics));
						if (migrated.changed) void persistPlanTopicsToServer(migrated.topics);
						return;
					}
				}

				const raw = window.localStorage.getItem(buildPlanTopicStorageKey(sessionId));
				if (!raw) {
					if (!cancelled) setPlanTopics({});
					return;
				}
				const parsed = JSON.parse(raw) as Record<string, PlanTopicState>;
				if (!parsed || typeof parsed !== 'object') {
					if (!cancelled) setPlanTopics({});
					return;
				}
				const migrated = migratePlanTopics(parsed);
				if (migrated.changed) {
					window.localStorage.setItem(buildPlanTopicStorageKey(sessionId), JSON.stringify(migrated.topics));
				}
				if (!cancelled) setPlanTopics(migrated.topics);
				void persistPlanTopicsToServer(migrated.topics);
			} catch (error) {
				console.error('[PlanSandboxPanel] restore real plan topics failed:', error);
				if (!cancelled) setPlanTopics({});
			}
		};
		void restorePlanTopics();
		const onStorage = (event: StorageEvent) => {
			if (event.key === buildPlanTopicStorageKey(sessionId)) void restorePlanTopics();
		};
		window.addEventListener('storage', onStorage);
		return () => {
			cancelled = true;
			window.removeEventListener('storage', onStorage);
		};
	}, [persistPlanTopicsToServer, sessionId]);

	const activeVersion = useMemo(
		() => versions.find((version) => version.id === activeVersionId) ?? versions[0],
		[activeVersionId, versions]
	);
	const activeLayoutVariant = useMemo(
		() => layoutPackage?.variants.find((variant) =>
			variant.variant_id === activeStrategyId ||
			variant.variant_id === activeVersionId ||
			variant.layout.layout_id === activeVersion?.layoutId
		),
		[activeStrategyId, activeVersion?.layoutId, activeVersionId, layoutPackage]
	);
	const activeStrategy = useMemo(
		() => strategies.find((strategy) => strategy.id === activeStrategyId) ?? strategies[0],
		[activeStrategyId, strategies]
	);
	const parameters = useMemo(() => buildParameters(activeSpace), [activeSpace]);
	const metrics = useMemo(() => buildMetrics(activeStrategy, activeLayoutVariant), [activeLayoutVariant, activeStrategy]);
	const activePlanTopic = planTopics[activeSpace];
	const hasRealPlan = Boolean(activePlanTopic?.uploadedFileUrl);
	const realPlanLabel = activePlanTopic?.uploadedFileName ?? `${activeSpace} 真实图纸`;
	const floorPlanIR = activePlanTopic?.reconstruction;
	const floorPlanElements = floorPlanIR?.elements ?? [];
	const activeLayoutSpaces = activeLayoutVariant?.layout.spaces ?? [];
	const floorPlanRooms = floorPlanElements.filter((element) => element.kind === 'function_zone' || element.kind === 'space_boundary');
	const floorPlanOpenings = floorPlanElements.filter((element) => element.kind === 'door' || element.kind === 'window');
	const floorPlanWalls = floorPlanElements.filter((element) => element.kind === 'wall_trace');
	const floorPlanDoors = floorPlanElements.filter((element) => element.kind === 'door');
	const floorPlanWindows = floorPlanElements.filter((element) => element.kind === 'window');
	const floorPlanColumns = floorPlanElements.filter((element) => element.kind === 'column');
	const floorPlanLocks = floorPlanElements.filter((element) => element.kind === 'wall_trace').length;
	const floorPlanIssues = floorPlanIR?.pendingIssues ?? [];
	const floorPlanQuality = floorPlanIR?.quality;
	const floorPlanDiagnostics = floorPlanIR?.diagnostics;
	const pipelineStats = floorPlanDiagnostics?.pipelineStats;
	const classCounts = floorPlanDiagnostics?.classCounts;
	const debugLayerCounts = floorPlanDiagnostics?.debugLayerCounts;
	const compileResult = floorPlanIR?.compileResult;
	const gates = floorPlanIR?.gates ?? compileResult?.gates;
	const reviewQueue = floorPlanIR?.reviewQueue ?? compileResult?.reviewQueue;
	const promotionBlockers = compileResult?.promotionBlockers ?? floorPlanDiagnostics?.promotionBlockers ?? [];
	const isFormalIRReady = compileResult?.formalPromotionAllowed ?? compileResult?.status === 'ir_ready';
	const reviewBuckets = useMemo(() => {
		if (!reviewQueue) return [];
		return [
			{ key: 'wallFragments', label: '墙碎片异', items: reviewQueue.wallFragments },
			{ key: 'suspectedMissingColumns', label: '疑似漏柱', items: reviewQueue.suspectedMissingColumns },
			{ key: 'unboundOpenings', label: '未绑定开', items: reviewQueue.unboundOpenings },
			{ key: 'lowConfidenceSpaces', label: '低置信空', items: reviewQueue.lowConfidenceSpaces },
			{ key: 'scaleIssues', label: '比例尺问题', items: reviewQueue.scaleIssues },
		].filter((bucket) => bucket.items.length > 0);
	}, [reviewQueue]);
	const floorPlanContentBox = floorPlanIR?.coordinateSpace === 'main_plan_box'
		? floorPlanIR.mainPlanBox ?? floorPlanIR.sourceContentBox ?? { x: 0, y: 0, w: 1, h: 1 }
		: floorPlanIR?.sourceContentBox ?? { x: 0, y: 0, w: 1, h: 1 };
	const recognitionBoxOnPage = floorPlanIR?.recognitionBoxOnPage ?? analysisRegion;
	const displayedRecognitionBox = analysisRegionDraft ?? recognitionBoxOnPage;
	const displayedMainPlanBox = floorPlanIR?.mainPlanBox;
	const displayedFocusBounds = floorPlanIR?.focusBounds;
	const displayedFocusIsMainPlan = Boolean(floorPlanIR?.focusUsedAsMainPlanBox);
	const mainPlanBoxSourceLabel = floorPlanIR?.mainPlanBoxSource === 'fallback_recognition_region'
		? '识别区回退'
		: floorPlanIR?.mainPlanBoxSource === 'detected_plan_frame'
			? '图框检测'
			: floorPlanIR?.mainPlanBoxSource === 'user_roi'
				? '用户确认'
				: floorPlanIR?.mainPlanBoxSource ?? '未生成';
	const selectedCandidate = floorPlanElements.find((element) => element.id === selectedCandidateId);
	const baseMapTintFilter = baseMapTint ? `sepia(1) saturate(4) hue-rotate(${baseMapTint})` : undefined;
	const dxfEntityAlpha = Math.max(0.08, Math.min(1, baseMapOpacity / 100));
	const PDF_TINT_COLOR_MAP: Record<string, string> = {
		'0deg': '#f97316',
		'180deg': '#06b6d4',
		'220deg': '#3b82f6',
		'280deg': '#a855f7',
		'90deg': '#22c55e',
	};
	const tintPdfSvg = (svgMarkup: string, tintKey: string) => {
		const tintColor = PDF_TINT_COLOR_MAP[tintKey];
		if (!tintColor) return svgMarkup;
		const isNeutral = (value: string) => {
			const v = value.trim().toLowerCase();
			return v === 'none' || v === 'transparent' || v === '#fff' || v === '#ffffff' || v === 'white' || v === 'rgb(255,255,255)' || v === 'rgb(100%,100%,100%)';
		};
		const recolorAttr = (attr: 'stroke' | 'fill', svg: string) =>
			svg.replace(new RegExp(`${attr}="([^"]+)"`, 'gi'), (full, raw) => {
				return isNeutral(String(raw)) ? full : `${attr}="${tintColor}"`;
			});
		return recolorAttr('fill', recolorAttr('stroke', svgMarkup));
	};
	// 校准态只认“用户手动确认”的比例尺，自动检测值仅作提示，不作为已校准状态
	const calibratedMmPerNorm = manualScaleMmPerNorm;
	const rulerMeasuredMm = useMemo(() => {
		if (!rulerState || !calibratedMmPerNorm) return null;
		const measureBox = floorPlanIR?.sourceContentBox ?? { x: 0, y: 0, w: 1, h: 1 };
		const mw = Math.max(1e-6, measureBox.w);
		const mh = Math.max(1e-6, measureBox.h);
		const ax = (rulerState.x0 - measureBox.x) / mw;
		const ay = (rulerState.y0 - measureBox.y) / mh;
		const bx = (rulerState.x1 - measureBox.x) / mw;
		const by = (rulerState.y1 - measureBox.y) / mh;
		const len = Math.hypot(bx - ax, by - ay);
		if (!(len > 0)) return null;
		return Math.max(1, Math.round(len * calibratedMmPerNorm));
	}, [calibratedMmPerNorm, floorPlanIR?.sourceContentBox, rulerState]);
	const scaleStatusLabel = !calibratedMmPerNorm
		? '待校准'
		: rulerMeasuredMm !== null
			? `${rulerMeasuredMm.toLocaleString()}mm`
			: `${Math.round(calibratedMmPerNorm).toLocaleString()}比例`;
	const mediaBox = useMemo(() => {
		const aspect = baseMapAspect > 0 ? baseMapAspect : 0.707;
		const viewportAspect = canvasSize.width / Math.max(1, canvasSize.height);
		if (viewportAspect > aspect) {
			const height = canvasSize.height;
			const width = height * aspect;
			return {
				left: (canvasSize.width - width) / 2,
				top: 0,
				width,
				height,
			};
		}
		const width = canvasSize.width;
		const height = width / aspect;
		return {
			left: 0,
			top: (canvasSize.height - height) / 2,
			width,
			height,
		};
	}, [baseMapAspect, canvasSize.height, canvasSize.width]);
	const mediaFrameStyle = useMemo(() => ({
		left: `${mediaBox.left}px`,
		top: `${mediaBox.top}px`,
		width: `${mediaBox.width}px`,
		height: `${mediaBox.height}px`,
	}), [mediaBox.height, mediaBox.left, mediaBox.top, mediaBox.width]);
	const floorPlanContentFrameStyle = useMemo(() => ({
		left: `${floorPlanContentBox.x * 100}%`,
		top: `${floorPlanContentBox.y * 100}%`,
		width: `${floorPlanContentBox.w * 100}%`,
		height: `${floorPlanContentBox.h * 100}%`,
	}), [floorPlanContentBox.h, floorPlanContentBox.w, floorPlanContentBox.x, floorPlanContentBox.y]);
	const layerRows = useMemo(() => [
		{ key: 'baseMap' as const, label: '底图', count: hasRealPlan ? 1 : 0, clearable: false },
		{ key: 'region' as const, label: '识别', count: recognitionBoxOnPage ? 1 : 0, clearable: true },
		{ key: 'rooms' as const, label: '空间', count: floorPlanRooms.length, clearable: true },
		{ key: 'walls' as const, label: '', count: floorPlanWalls.length, clearable: true },
		{ key: 'columns' as const, label: '', count: floorPlanColumns.length, clearable: true },
		{ key: 'doors' as const, label: '门洞', count: floorPlanDoors.length, clearable: true },
		{ key: 'windows' as const, label: '窗洞', count: floorPlanWindows.length, clearable: true },
		{ key: 'labels' as const, label: '序号', count: floorPlanElements.length, clearable: false },
	], [floorPlanColumns.length, floorPlanDoors.length, floorPlanElements.length, floorPlanRooms.length, floorPlanWalls.length, floorPlanWindows.length, hasRealPlan, recognitionBoxOnPage]);
	const handleBaseMapLoad = (event: SyntheticEvent<HTMLImageElement>) => {
		const image = event.currentTarget;
		if (image.naturalWidth > 0 && image.naturalHeight > 0) {
			setBaseMapAspect(image.naturalWidth / image.naturalHeight);
		}
	};
	const activeDxfUrl = activePlanTopic?.sourceType === 'dxf' && activePlanTopic?.mimeType !== 'application/pdf'
		? activePlanTopic.uploadedFileUrl
		: undefined;
	useEffect(() => {
		if (!activeDxfUrl) {
			setDxfGeometry(null);
			setDxfLoadError(null);
			return;
		}
		let cancelled = false;
		setDxfGeometry(null);
		setDxfLoadError(null);
		const loadDxf = async () => {
			try {
				const response = await fetch(activeDxfUrl);
				if (!response.ok) throw new Error(`DXF 读取失败：${response.status}`);
				const text = await response.text();
				if (cancelled) return;
				const next = parseDxfPreviewGeometry(text);
				setDxfGeometry(next);
				if (next.entityCount === 0) {
					setDxfLoadError('DXF 未读取到可显示的 LINE / POLYLINE / CIRCLE / ARC 实体');
				} else {
					setBaseMapAspect(next.width / next.height);
				}
			} catch (error) {
				if (!cancelled) {
					setDxfLoadError(error instanceof Error ? error.message : String(error));
				}
			}
		};
		void loadDxf();
		return () => { cancelled = true; };
	}, [activeDxfUrl]);
	const candidateGroups = useMemo(() => [
		{ key: 'wall', label: '', tone: 'bg-slate-900', items: floorPlanWalls },
		{ key: 'column', label: '', tone: 'bg-yellow-500', items: floorPlanColumns },
		{ key: 'door', label: '门洞', tone: 'bg-amber-500', items: floorPlanDoors },
		{ key: 'window', label: '窗洞', tone: 'bg-sky-500', items: floorPlanWindows },
	], [floorPlanColumns, floorPlanDoors, floorPlanWalls, floorPlanWindows]);
	const clampZoom = (value: number) => Math.min(10, Math.max(0.55, Number(value.toFixed(3))));
	const zoomCanvasAt = (clientX: number, clientY: number, scaleFactor: number) => {
		const viewport = canvasViewportRef.current;
		if (!viewport) return;
		const rect = viewport.getBoundingClientRect();
		const localX = clientX - rect.left;
		const localY = clientY - rect.top;
		setCanvasTransform((current) => {
			const nextZoom = clampZoom(current.zoom * scaleFactor);
			if (nextZoom === current.zoom) return current;
			const ratio = nextZoom / current.zoom;
			return {
				zoom: nextZoom,
				x: localX - (localX - current.x) * ratio,
				y: localY - (localY - current.y) * ratio,
			};
		});
	};
	const zoomCanvasAtViewportCenter = (scaleFactor: number) => {
		const viewport = canvasViewportRef.current;
		if (!viewport) return;
		const rect = viewport.getBoundingClientRect();
		zoomCanvasAt(rect.left + rect.width / 2, rect.top + rect.height / 2, scaleFactor);
	};
	const normalizedCanvasPoint = (clientX: number, clientY: number) => {
		const viewport = canvasViewportRef.current;
		if (!viewport) return { x: 0, y: 0 };
		const rect = viewport.getBoundingClientRect();
		const localX = (clientX - rect.left - canvasTransform.x) / Math.max(0.001, canvasTransform.zoom);
		const localY = (clientY - rect.top - canvasTransform.y) / Math.max(0.001, canvasTransform.zoom);
		return {
			x: Math.min(1, Math.max(0, (localX - mediaBox.left) / Math.max(1, mediaBox.width))),
			y: Math.min(1, Math.max(0, (localY - mediaBox.top) / Math.max(1, mediaBox.height))),
		};
	};
	const buildRegionFromPoints = (a: FloorPlanPoint, b: FloorPlanPoint) => {
		const x = Math.min(a.x, b.x);
		const y = Math.min(a.y, b.y);
		return {
			x,
			y,
			w: Math.max(0.001, Math.abs(a.x - b.x)),
			h: Math.max(0.001, Math.abs(a.y - b.y)),
		};
	};
	const stopCanvasPanning = (pointerId?: number) => {
		if (pointerId !== undefined && canvasPanDragRef.current?.pointerId !== pointerId) return;
		canvasPanDragRef.current = null;
		setIsCanvasPanning(false);
	};
	const stopAnalysisRegionSelection = (pointerId?: number) => {
		const drag = analysisRegionDragRef.current;
		if (!drag || (pointerId !== undefined && drag.pointerId !== pointerId)) return;
		analysisRegionDragRef.current = null;
		setAnalysisRegionDraft((draft) => {
			if (draft && draft.w > 0.02 && draft.h > 0.02) {
				setAnalysisRegion(draft);
				setIsSelectingAnalysisRegion(false);
			}
			return null;
		});
	};
	const persistPlanTopicPatch = (patch: Partial<PlanTopicState>) => {
		if (typeof window === 'undefined') return;
		setPlanTopics((prev) => {
			const next = {
				...prev,
				[activeSpace]: {
					...(prev[activeSpace] ?? { space: activeSpace, status: 'missing', sourceType: 'manual' }),
					...patch,
					space: activeSpace,
				},
			};
			window.localStorage.setItem(buildPlanTopicStorageKey(sessionId), JSON.stringify(next));
			void persistPlanTopicsToServer(next);
			return next;
		});
	};
	const rebuildReconstruction = (reconstruction: FloorPlanReconstruction, elements: FloorPlanElement[]): FloorPlanReconstruction => {
		const objectCounts = {
			...reconstruction.objectCounts,
			wall: elements.filter((element) => element.kind === 'wall_trace').length,
			door: elements.filter((element) => element.kind === 'door').length,
			window: elements.filter((element) => element.kind === 'window').length,
			column: elements.filter((element) => element.kind === 'column').length,
		};
		return {
			...reconstruction,
			objectCounts,
			spaceBoundaryCount: elements.filter((element) => element.kind === 'space_boundary').length,
			functionZoneCount: elements.filter((element) => element.kind === 'function_zone').length,
			elements,
			updatedAt: nowLabel(),
		};
	};
	const buildSandboxSpgPayload = () => {
		const zoneSets: Record<string, Array<{ zone_id: string; name: string; function: string; approx_area_m2: number; privacy_level: 'public' | 'semi_public' | 'private' | 'service'; required_adjacencies?: string[]; forbidden_adjacencies?: string[]; orientation_preference?: string }>> = {
			大堂: [
				{ zone_id: 'arrival', name: '入口到达', function: 'arrival', approx_area_m2: 18, privacy_level: 'public', required_adjacencies: ['reception', 'public_lounge'] },
				{ zone_id: 'reception', name: '接待服务', function: 'reception', approx_area_m2: 22, privacy_level: 'semi_public', required_adjacencies: ['arrival', 'service'] },
				{ zone_id: 'public_lounge', name: '等候公区', function: 'lounge', approx_area_m2: 42, privacy_level: 'public', orientation_preference: 'best_view' },
				{ zone_id: 'service', name: '后勤支持', function: 'service', approx_area_m2: 16, privacy_level: 'service', forbidden_adjacencies: ['public_lounge'] },
			],
			餐厅: [
				{ zone_id: 'dining_hall', name: '主餐区', function: 'dining', approx_area_m2: 68, privacy_level: 'public', required_adjacencies: ['service_pass'] },
				{ zone_id: 'view_tables', name: '景观餐位', function: 'view_dining', approx_area_m2: 28, privacy_level: 'semi_public', orientation_preference: 'best_view' },
				{ zone_id: 'service_pass', name: '服务通道', function: 'service_flow', approx_area_m2: 18, privacy_level: 'service', required_adjacencies: ['kitchen_buffer'] },
				{ zone_id: 'kitchen_buffer', name: '备餐缓冲', function: 'kitchen_buffer', approx_area_m2: 22, privacy_level: 'service' },
			],
			客房: [
				{ zone_id: 'entry_buffer', name: '入户缓冲', function: 'entry', approx_area_m2: 8, privacy_level: 'semi_public', required_adjacencies: ['sleeping'] },
				{ zone_id: 'sleeping', name: '睡眠区', function: 'sleeping', approx_area_m2: 24, privacy_level: 'private', orientation_preference: 'quiet_view' },
				{ zone_id: 'living_nook', name: '起居停留', function: 'living', approx_area_m2: 16, privacy_level: 'private', orientation_preference: 'best_view' },
				{ zone_id: 'bath_storage', name: '卫浴收纳', function: 'bath_storage', approx_area_m2: 12, privacy_level: 'service', required_adjacencies: ['sleeping'] },
			],
		};
		const zones = zoneSets[activeSpace] ?? [
			{ zone_id: 'public_core', name: `${activeSpace}公共核心`, function: 'public_core', approx_area_m2: 36, privacy_level: 'public' as const, orientation_preference: 'best_view' },
			{ zone_id: 'support', name: `${activeSpace}支持空间`, function: 'support', approx_area_m2: 18, privacy_level: 'service' as const },
			{ zone_id: 'private_zone', name: `${activeSpace}私密/弹性区`, function: 'private', approx_area_m2: 24, privacy_level: 'private' as const },
		];
		return {
			spg_id: `spg-${sessionId}-${activeSpace}`,
			space_type: activeSpace,
			zones,
			flows: [
				{ flow_id: 'main_path', name: '主使用动线', flow_type: 'public', from_zone: zones[0]?.zone_id ?? 'public_core', to_zone: zones[Math.max(0, zones.length - 1)]?.zone_id ?? 'private_zone' },
				...(zones.some((zone) => zone.privacy_level === 'service')
					? [{ flow_id: 'service_path', name: '服务动线', flow_type: 'service', from_zone: zones.find((zone) => zone.privacy_level === 'service')?.zone_id ?? zones[0].zone_id, to_zone: zones[0].zone_id }]
					: []),
			],
			privacy_gradient: zones.map((zone) => zone.zone_id),
			version: 'v1.0',
			source_refs: [hasRealPlan ? realPlanLabel : 'PlanSandbox manual baseline'],
			frozen: false,
		};
	};
	const buildSandboxFactsPayload = () => {
		const factFromElement = (element: FloorPlanElement) => ({
			element_id: element.id,
			element_type: element.kind === 'column'
				? 'column'
				: element.kind === 'wall_trace'
					? 'structural_wall'
					: element.kind === 'door'
						? 'opening'
						: element.kind === 'window'
							? 'window'
							: 'boundary',
			geometry: element.points?.map((point) => [point.x, point.y]) ?? [
				[element.x, element.y],
				[element.x + element.w, element.y],
				[element.x + element.w, element.y + element.h],
				[element.x, element.y + element.h],
			],
			locked: element.kind === 'column' || element.kind === 'wall_trace',
			confidence: element.confidence,
			source: element.status === 'edited' ? 'manual' : 'compiled',
			notes: [element.label],
		});
		const immutable = floorPlanElements
			.filter((element) => element.kind === 'column' || element.kind === 'wall_trace')
			.slice(0, 80)
			.map(factFromElement);
		const flexible = floorPlanElements
			.filter((element) => element.kind === 'door' || element.kind === 'window' || element.kind === 'space_boundary' || element.kind === 'function_zone')
			.slice(0, 80)
			.map(factFromElement);
		return {
			facts_id: `facts-${sessionId}-${activeSpace}`,
			session_id: sessionId,
			source_floor_plan_ir_id: floorPlanIR?.irVersion ?? undefined,
			coordinate_space: 'normalized',
			scale_status: floorPlanIR?.coordinateSystem.scaleStatus === 'confirmed' ? 'confirmed' : floorPlanIR?.coordinateSystem.scaleStatus === 'estimated' ? 'estimated' : 'missing',
			boundary: [[0, 0], [1, 0], [1, 1], [0, 1]],
			immutable_elements: immutable,
			flexible_elements: flexible,
			review_flags: promotionBlockers.slice(0, 5),
		};
	};
	const updateFloorPlanElements = (updater: (elements: FloorPlanElement[]) => FloorPlanElement[]) => {
		if (!floorPlanIR) return;
		const nextElements = updater(floorPlanIR.elements);
		persistPlanTopicPatch({
			reconstruction: rebuildReconstruction(floorPlanIR, nextElements),
			updatedAt: nowLabel(),
			parseMessage: 'FloorPlanIR 已人工校正，等待确认基线',
		});
	};
	const handleSelectCandidate = (element: FloorPlanElement) => {
		setSelectedCandidateId(element.id);
		setActiveTab('properties');
		const viewport = canvasViewportRef.current;
		if (!viewport) return;
		const rect = viewport.getBoundingClientRect();
		const centerX = mediaBox.left + floorPlanContentBox.x * mediaBox.width + (element.x + element.w / 2) * floorPlanContentBox.w * mediaBox.width;
		const centerY = mediaBox.top + floorPlanContentBox.y * mediaBox.height + (element.y + element.h / 2) * floorPlanContentBox.h * mediaBox.height;
		setCanvasTransform((current) => ({
			...current,
			x: rect.width / 2 - centerX * current.zoom,
			y: rect.height / 2 - centerY * current.zoom,
		}));
	};
	const handleConfirmCandidate = (id: string) => {
		updateFloorPlanElements((elements) => elements.map((element) => element.id === id ? { ...element, status: 'confirmed', confidence: Math.max(element.confidence, 0.82) } : element));
	};
	const handleDeleteCandidate = (id: string) => {
		updateFloorPlanElements((elements) => elements.filter((element) => element.id !== id));
		if (selectedCandidateId === id) setSelectedCandidateId('');
	};
	const handleUpdateCandidate = (id: string, patch: Partial<FloorPlanElement>) => {
		updateFloorPlanElements((elements) => elements.map((element) => element.id === id ? { ...element, ...patch, status: element.status === 'confirmed' ? 'confirmed' : 'edited' } : element));
	};
	const handleToggleLayer = (key: FloorPlanLayerKey) => {
		setLayerVisibility((current) => ({ ...current, [key]: !current[key] }));
	};
	const handleClearLayer = (key: FloorPlanLayerKey) => {
		if (key === 'region') {
			setAnalysisRegion(null);
			setAnalysisRegionDraft(null);
			if (floorPlanIR) {
				persistPlanTopicPatch({
					reconstruction: {
						...floorPlanIR,
						recognitionBoxOnPage: undefined,
						updatedAt: nowLabel(),
					},
					updatedAt: nowLabel(),
				});
			}
			return;
		}
		const kindMap: Partial<Record<FloorPlanLayerKey, FloorPlanElementKind[]>> = {
			rooms: ['function_zone', 'space_boundary'],
			walls: ['wall_trace'],
			columns: ['column'],
			doors: ['door'],
			windows: ['window'],
		};
		const kinds = kindMap[key];
		if (!kinds) return;
		updateFloorPlanElements((elements) => elements.filter((element) => !kinds.includes(element.kind)));
		if (selectedCandidate && kinds.includes(selectedCandidate.kind)) setSelectedCandidateId('');
	};
	const handleConfirmReviewedIR = () => {
		if (!floorPlanIR) return;
		if (floorPlanIR.compileResult?.status !== 'ir_ready') {
			onInjectReference?.(`平面推演@${activeSpace} · 当前仍是编译候选态，Gate 未通过，不能确认 Reviewed FloorPlanIR。`);
			return;
		}
		const elements = floorPlanIR.elements.map((element) => element.status === 'candidate' ? { ...element, status: 'confirmed' as const } : element);
		const reconstruction = rebuildReconstruction({
			...floorPlanIR,
			status: 'aligned',
			irVersion: `FloorPlanIR ${activeSpace} reviewed v0.1`,
			pendingIssues: [],
			alignment: {
				...(floorPlanIR.alignment ?? {}),
				matchedSpace: activeSpace,
				confidence: 0.86,
				status: 'confirmed',
			},
		}, elements);
		persistPlanTopicPatch({
			status: 'reviewed',
			parseMessage: '已确认 Reviewed FloorPlanIR，可注入方案高参',
			reconstruction,
			updatedAt: nowLabel(),
		});
		onInjectReference?.(`平面推演@${activeSpace} · Reviewed FloorPlanIR 已确认：墙 ${reconstruction.objectCounts.wall ?? 0}，柱 ${reconstruction.objectCounts.column ?? 0}，门 ${reconstruction.objectCounts.door ?? 0}，窗 ${reconstruction.objectCounts.window ?? 0}，闭合空间 ${reconstruction.functionZoneCount}`);
	};
	const handleGenerateFloorPlanIR = async () => {
		if (!activePlanTopic?.uploadedFileUrl || !activePlanTopic?.mimeType) {
			onInjectReference?.(`平面推演@${activeSpace} · 需要先上传真实底图，再编译墙柱候选`);
			return;
		}
		if (!manualScaleMmPerNorm || manualScaleMmPerNorm <= 0) {
			setRulerActive(true);
			setRulerInputDraft(detectedMmPerNorm ? String(Math.round(detectedMmPerNorm)) : '');
			setRulerState({ x0: 0.25, y0: 0.5, x1: 0.55, y1: 0.5, knownMm: detectedMmPerNorm ?? null });
			setIsRulerInputEditing(false);
			persistPlanTopicPatch({
				status: 'parsed',
				parseMessage: '请先完成比例尺校准后再生成 FloorPlanIR',
				updatedAt: nowLabel(),
			});
			onInjectReference?.(`平面推演@${activeSpace} · 当前未完成比例尺校准，已自动打开标尺。`);
			return;
		}
		setIsTracingFloorPlan(true);
		setShowBaseMap(true);
		setLayerVisibility((current) => ({ ...current, baseMap: true, region: true, walls: true, columns: true, doors: true, windows: true, labels: true }));
		try {
			const response = await fetch('/api/floor-plan/trace', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					fileUrl: activePlanTopic.uploadedFileUrl,
					mimeType: activePlanTopic.mimeType,
					region: analysisRegion ?? { x: 0, y: 0, w: 1, h: 1 },
					...(manualScaleMmPerNorm ? { manualScaleMmPerNorm } : {}),
				}),
			});
			const result = await response.json() as {
				status?: string;
				message?: string;
				elements?: FloorPlanElement[];
				scaleCalibration?: { mmPerNormalized?: number; source?: string; samples?: number };
				issues?: Array<string | FloorPlanIssue>;
				issueMessages?: string[];
				floorPlanIR?: unknown;
				draftFloorPlanIR?: unknown;
				compileResult?: FloorPlanCompileResult;
				gates?: FloorPlanCompileResult['gates'];
				formalPromotionAllowed?: boolean;
				promotionBlockers?: string[];
				reviewQueue?: FloorPlanCompileResult['reviewQueue'];
				quality?: FloorPlanQuality;
				normalization?: {
					contentBox?: FloorPlanRect;
					recognitionRegion?: FloorPlanRect;
					recognitionBoxOnPage?: FloorPlanRect;
					mainPlanBox?: FloorPlanRect;
					mainPlanBoxInContent?: FloorPlanRect;
					mainPlanBoxSource?: string;
					focusBounds?: FloorPlanRect;
					focusBoundsInContent?: FloorPlanRect;
					focusUsedAsMainPlanBox?: boolean;
					coordinateSpace?: 'main_plan_box';
				};
				sheetIR?: unknown;
				diagnostics?: FloorPlanDiagnostics;
				error?: string;
			};
			if (!response.ok) throw new Error(result.error ?? `trace failed: ${response.status}`);
			const sourceElements = result.elements ?? [];
			const blockedByScale = result.diagnostics?.blockedBy === 'scale_calibration_required';
			const nextUpdatedAt = nowLabel();
			setSelectedCandidateId('');
			const promotionAllowed = result.compileResult?.formalPromotionAllowed ?? result.compileResult?.status === 'ir_ready';
			setLayerVisibility((current) => ({
				...current,
				rooms: promotionAllowed,
				doors: promotionAllowed,
				windows: promotionAllowed,
				walls: true,
				columns: true,
				labels: true,
			}));
			const elements = sourceElements;
			const objectCounts = {
				wall: elements.filter((element) => element.kind === 'wall_trace').length,
				door: elements.filter((element) => element.kind === 'door').length,
				window: elements.filter((element) => element.kind === 'window').length,
				column: elements.filter((element) => element.kind === 'column').length,
				fixed_furniture: 0,
				loose_furniture: 0,
				north_arrow: 0,
			};
			const reconstruction: FloorPlanReconstruction = {
				status: elements.length > 0 ? 'traced' : 'raw',
				irVersion: result.compileResult?.status === 'ir_ready' ? `FloorPlanIR ${activeSpace} reviewed-candidate v0.1` : `FloorPlanCompiler ${activeSpace} candidate v0.1`,
				sourceFormat: activePlanTopic.sourceType,
				coordinateSystem: {
					unit: activePlanTopic.sourceType === 'image' ? 'px' : 'mm',
					scaleStatus: result.scaleCalibration?.samples ? 'estimated' : 'uncalibrated',
					northStatus: 'detected',
				},
				objectCounts,
				spaceBoundaryCount: elements.filter((element) => element.kind === 'space_boundary').length,
				functionZoneCount: elements.filter((element) => element.kind === 'function_zone').length,
				alignment: {
					matchedSpace: activeSpace,
					confidence: elements.length > 0 ? 0.72 : 0.38,
					status: elements.length > 0 ? 'candidate' : 'conflict',
				},
				heightProfile: { status: 'missing' },
				scaleCalibration: {
					mmPerPixel: result.scaleCalibration?.mmPerNormalized ? result.scaleCalibration.mmPerNormalized / 1000 : undefined,
					source: result.scaleCalibration?.source ?? 'fallback',
					samples: result.scaleCalibration?.samples ?? 0,
				},
				// save detected scale for UI hint
				...(() => { if (result.scaleCalibration?.mmPerNormalized) setDetectedMmPerNorm(result.scaleCalibration.mmPerNormalized); return {}; })(),
				elements,
				floorPlanIR: result.floorPlanIR,
				draftFloorPlanIR: result.draftFloorPlanIR,
				compileResult: result.compileResult,
				gates: result.gates,
				reviewQueue: result.reviewQueue,
				quality: result.quality,
				sourceContentBox: result.normalization?.contentBox,
				mainPlanBox: result.normalization?.mainPlanBox,
				mainPlanBoxSource: result.normalization?.mainPlanBoxSource,
				focusBounds: result.normalization?.focusBounds,
				focusBoundsInContent: result.normalization?.focusBoundsInContent,
				focusUsedAsMainPlanBox: result.normalization?.focusUsedAsMainPlanBox,
				recognitionBoxOnPage: result.normalization?.recognitionBoxOnPage,
				coordinateSpace: result.normalization?.coordinateSpace ?? FLOOR_PLAN_IR_COORDINATE_SPACE,
				diagnostics: result.diagnostics,
				irSchemaVersion: FLOOR_PLAN_IR_SCHEMA_VERSION,
				sheetIR: result.sheetIR,
				pendingIssues: result.issueMessages ?? result.issues ?? ['需人工确认闭合空间、门窗和比例'],
				updatedAt: nextUpdatedAt,
			};
			persistPlanTopicPatch({
				status: blockedByScale ? 'parsed' : elements.length > 0 ? 'bound' : 'uploaded',
				parseMessage: blockedByScale
					? (result.message ?? '未校准比例尺，请先使用比例尺标尺完成校准，再继续编译')
					: (result.message ?? '已完成 FloorPlanIR 生成尝试'),
				reconstruction,
				updatedAt: nextUpdatedAt,
			});
			if (blockedByScale && hasRealPlan && !manualScaleMmPerNorm) {
				setRulerActive(true);
				setRulerInputDraft(result.scaleCalibration?.mmPerNormalized ? String(Math.round(result.scaleCalibration.mmPerNormalized)) : '');
				setRulerState({ x0: 0.25, y0: 0.5, x1: 0.55, y1: 0.5, knownMm: result.scaleCalibration?.mmPerNormalized ?? null });
				setIsRulerInputEditing(false);
			}
			if (result.scaleCalibration?.mmPerNormalized) setDetectedMmPerNorm(result.scaleCalibration.mmPerNormalized);
			const gateText = blockedByScale
				? '比例尺未校准，已切换到标尺校准模式'
				: promotionAllowed ? 'Reviewed FloorPlanIR 候选已生成' : '编译候选已生成，正式升格门禁未通过';
			onInjectReference?.(`平面推演@${activeSpace} · ${gateText}：墙 ${objectCounts.wall}，柱 ${objectCounts.column}，门窗候选 ${objectCounts.door + objectCounts.window}，Geometry ${result.gates?.geometry.status ?? 'unknown'}`);
		} catch (error) {
			const message = error instanceof Error ? error.message : 'FloorPlanIR 生成失败';
			persistPlanTopicPatch({
				status: 'stale',
				parseMessage: message,
				updatedAt: nowLabel(),
			});
			onInjectReference?.(`平面推演@${activeSpace} · 生成失败：${message}`);
		} finally {
			setIsTracingFloorPlan(false);
		}
	};

	const handleOpenPlanUploadPicker = () => {
		if (isUploadingPlan) return;
		planUploadInputRef.current?.click();
	};

	const handlePlanUploadChange = async (event: ChangeEvent<HTMLInputElement>) => {
		const file = event.target.files?.[0];
		if (!file) return;
		const lowerName = file.name.toLowerCase();
		const sourceType: PlanTopicState['sourceType'] =
			lowerName.endsWith('.dwg') ? 'cad' :
			lowerName.endsWith('.dxf') ? 'dxf' :
			lowerName.endsWith('.pdf') ? 'pdf' :
			'image';

		setIsUploadingPlan(true);
		try {
			const formData = new FormData();
			formData.append('file', file);
			formData.append('sessionId', sessionId);
			formData.append('space', activeSpace);
			const response = await fetch('/api/plan-drawings', {
				method: 'POST',
				body: formData,
			});
			const result = await response.json() as {
				url?: string;
				mimeType?: string;
				size?: number;
				error?: string;
				parseResult?: {
					status?: 'uploaded' | 'parsed' | 'needs_conversion';
					message?: string;
					layers?: string[];
					entityCounts?: Record<string, number>;
				};
			};
			if (!response.ok || !result.url || !result.mimeType) {
				throw new Error(result.error ?? `上传失败: ${response.status}`);
			}

			setSelectedCandidateId('');
			setAnalysisRegion(null);
			setAnalysisRegionDraft(null);
			setRulerInputDraft('');
			setIsRulerInputEditing(false);
			setManualScaleMmPerNorm(null);
			setManualScaleMmPerPx(null);
			setDetectedMmPerNorm(null);
			setShowBaseMap(true);

			persistPlanTopicPatch({
				status: result.parseResult?.status === 'parsed' ? 'parsed' : 'uploaded',
				sourceType,
				uploadedFileName: file.name,
				uploadedFileUrl: result.url,
				uploadedFileSize: result.size,
				mimeType: result.mimeType,
				parseMessage: '图纸已上传，请先使用比例尺标尺完成校准，再进行后续操作',
				parsedLayers: result.parseResult?.layers,
				parsedEntityCounts: result.parseResult?.entityCounts,
				reconstruction: undefined,
				updatedAt: nowLabel(),
			});

			// 自动激活比例尺标尺，引导用户优先完成校准
			setRulerActive(true);
			setRulerState({ x0: 0.25, y0: 0.5, x1: 0.55, y1: 0.5, knownMm: null });

			onInjectReference?.(`平面推演@${activeSpace} · 图纸已上传：${file.name}，请先完成比例尺校准。`);
		} catch (error) {
			const message = error instanceof Error ? error.message : '上传失败，请稍后重试';
			persistPlanTopicPatch({
				status: 'stale',
				sourceType,
				uploadedFileName: file.name,
				parseMessage: message,
				updatedAt: nowLabel(),
			});
			onInjectReference?.(`平面推演@${activeSpace} · 图纸上传失败：${message}`);
		} finally {
			event.target.value = '';
			setIsUploadingPlan(false);
		}
	};

	useEffect(() => {
		let cancelled = false;
		const renderPdfPreview = async () => {
			if (!activePlanTopic?.uploadedFileUrl || activePlanTopic.mimeType !== 'application/pdf') {
				setPdfPreviewDataUrl('');
				return;
			}
			try {
				const pdfjsLib = await import('pdfjs-dist/legacy/build/pdf');
				pdfjsLib.GlobalWorkerOptions.workerSrc = '/api/pdf-worker';
				const loadingTask = pdfjsLib.getDocument({ url: activePlanTopic.uploadedFileUrl });
				const pdf = await loadingTask.promise;
				const page = await pdf.getPage(1);
				const viewport = page.getViewport({ scale: 1 });
				const opList = await page.getOperatorList();
				const svgGfx = new (pdfjsLib as any).SVGGraphics(page.commonObjs, page.objs);
				const svgElement = await svgGfx.getSVG(opList, viewport);
				const svgStr = new XMLSerializer().serializeToString(svgElement);
				const tintedSvg = tintPdfSvg(svgStr, baseMapTint);
				const dataUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(tintedSvg);
				if (!cancelled) setPdfPreviewDataUrl(dataUrl);
				await pdf.destroy();
			} catch (error) {
				console.error('[PlanSandboxPanel] pdf preview render failed:', error);
				if (!cancelled) setPdfPreviewDataUrl('');
			}
		};
		renderPdfPreview();
		return () => {
			cancelled = true;
		};
	}, [activePlanTopic?.mimeType, activePlanTopic?.uploadedFileUrl, baseMapTint]);

	const handleCreateIteration = async () => {
		if (isGeneratingLayoutVariants) return;
		setIsGeneratingLayoutVariants(true);
		try {
			const response = await fetch('/api/floor-plan/generate-variants', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					session_id: sessionId,
					spg: buildSandboxSpgPayload(),
					facts: buildSandboxFactsPayload(),
					variant_count: 3,
				}),
			});
			const result = await response.json() as LayoutGenerationPackage & { error?: string };
			if (!response.ok || !Array.isArray(result.variants)) {
				throw new Error(result.error ?? `推演失败: ${response.status}`);
			}
			const nextVersions: PlanVersion[] = result.variants.map((variant, index) => ({
				id: variant.variant_id,
				name: `${index === 0 ? 'A' : index === 1 ? 'B' : 'C'} · ${variant.name}`,
				stage: 'iterating',
				note: variant.comparison_summary || variant.layout.explanation || variant.intent.primary_axis || '已生成推演版本，等待用户选择。',
				updatedAt: nowLabel(),
				basedOnBriefVersion: 'AlignedBrief/SPG v1.0',
				layoutId: variant.layout.layout_id,
				strategyId: variant.intent.strategy,
				score: variant.layout.score?.project_fit,
			}));
			const baseline = versions.find((version) => version.stage === 'baseline') ?? buildInitialVersion(activeSpace);
			setLayoutPackage(result);
			setVersions([baseline, ...nextVersions]);
			setActiveVersionId(result.variants[0].variant_id);
			setActiveStrategyId(result.variants[0].variant_id);
			setActiveTab('versions');
			setLayerVisibility((current) => ({ ...current, rooms: true, labels: true }));
			onInjectReference?.(`平面推演@${activeSpace} · 已生成 ${result.variants.length} 套平面推演版本：${result.variants.map((variant) => variant.name).join(' / ')}`);
		} catch (error) {
			const message = error instanceof Error ? error.message : '平面推演失败';
			onInjectReference?.(`平面推演@${activeSpace} · 多版本推演失败：${message}`);
		} finally {
			setIsGeneratingLayoutVariants(false);
		}
	};

	const handleFreezeCurrent = () => {
		setVersions((prev) =>
			prev.map((version) =>
				version.id === activeVersionId
					? {
						...version,
						stage: 'frozen',
						note: `已冻结为 ${activeSpace} 的当前几何决策版本，可发往方案画布或回写底盘。`,
						updatedAt: nowLabel(),
					}
					: version
			)
		);
		onInjectReference?.(`平面推演@${activeSpace} · 冻结当前版本并生成回写建议`);
	};

	const handleWriteBack = () => {
		onInjectReference?.(`平面推演@${activeSpace} · 回写项目底盘：推荐方向「${activeStrategy.title}」，底盘匹配 ${activeStrategy.score}，关键代价：${activeStrategy.tradeoff}`);
	};

	const stageLabel = (stage: PlanVersion['stage']) => {
		if (stage === 'frozen') return '已冻结';
		if (stage === 'baseline') return '基线';
		return '推演';
	};

	const metricClass = (tone: SandboxMetric['tone']) => {
		if (tone === 'good') return 'border-emerald-200 bg-emerald-50 text-emerald-800';
		if (tone === 'risk') return 'border-amber-200 bg-amber-50 text-amber-800';
		return 'border-slate-200 bg-slate-50 text-slate-700';
	};
	const selectedKindLabel = selectedCandidate?.kind === 'wall_trace'
		? '墙体'
		: selectedCandidate?.kind === 'column'
			? '结构柱'
			: selectedCandidate?.kind === 'door'
				? '门洞'
				: selectedCandidate?.kind === 'window'
					? '窗洞'
					: selectedCandidate?.kind === 'function_zone' || selectedCandidate?.kind === 'space_boundary'
						? '空间'
						: '对象';

	const sourcePanelItems = [
		{ title: '图纸基线', meta: hasRealPlan ? realPlanLabel : '项目底盘', desc: hasRealPlan ? `已读取真实 ${activePlanTopic?.sourceType?.toUpperCase() ?? '图纸'}，作为当前沙盘底图。` : `${activeSpace} 原始图纸、空间边界、结构限制与开口信息。`, action: hasRealPlan ? '定位图纸' : '查看图纸' },
		{ title: '回写', meta: activeVersion?.name ?? 'FloorPlanIR_v0', desc: '冻结方向、指标、风险与下一步任务回写项目底盘', action: '生成回写' },
		{ title: '下游骨架', meta: 'Prompt Anchor', desc: '输出语义分区图、动线关系和方案画布控制骨架', action: '发往画布' },
	];
	const renderFloorPlanIRLayer = () => {
		if (!floorPlanElements.length && !activeLayoutSpaces.length) return null;
		const safeZoom = Math.max(0.001, canvasTransform.zoom);
		const pxToCanvas = (px: number) => px / safeZoom;
		const toPointString = (points?: FloorPlanPoint[]) => points?.map((point) => `${point.x * 1000},${point.y * 1000}`).join(' ') ?? '';
		const center = (element: FloorPlanElement) => ({
			x: (element.x + element.w / 2) * 1000,
			y: (element.y + element.h / 2) * 1000,
		});
		const getHighlightStroke = (selected: boolean, hovered: boolean) => {
			if (selected) return { color: 'rgba(37,99,235,1)', width: pxToCanvas(2.7), pad: pxToCanvas(1.9) };
			if (hovered) return { color: 'rgba(59,130,246,0.98)', width: pxToCanvas(2.0), pad: pxToCanvas(1.3) };
			return null;
		};
		return (
			<svg viewBox="0 0 1000 1000" preserveAspectRatio="none" className="pointer-events-none absolute inset-0 h-full w-full">
				<defs>
					<pattern id={`real-ir-hatch-${activeSpace}`} width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
						<line x1="0" y1="0" x2="0" y2="10" stroke="rgba(15,23,42,0.18)" strokeWidth="2" />
					</pattern>
				</defs>
				{layerVisibility.rooms && activeLayoutSpaces.map((space, index) => {
					const palette = [
						{ fill: 'rgba(14,165,233,0.20)', stroke: 'rgba(14,165,233,0.88)' },
						{ fill: 'rgba(34,197,94,0.18)', stroke: 'rgba(22,163,74,0.86)' },
						{ fill: 'rgba(245,158,11,0.18)', stroke: 'rgba(217,119,6,0.86)' },
						{ fill: 'rgba(168,85,247,0.16)', stroke: 'rgba(147,51,234,0.80)' },
					];
					const tone = palette[index % palette.length];
					return (
						<g key={`layout-space-${space.space_id}`}>
							<rect
								x={space.x * 1000}
								y={space.y * 1000}
								width={space.w * 1000}
								height={space.h * 1000}
								fill={tone.fill}
								stroke={tone.stroke}
								strokeWidth={pxToCanvas(2)}
								strokeDasharray={`${pxToCanvas(5)} ${pxToCanvas(3)}`}
								vectorEffect="non-scaling-stroke"
							/>
							<text
								x={space.x * 1000 + pxToCanvas(10)}
								y={space.y * 1000 + pxToCanvas(22)}
								fontSize={Math.max(pxToCanvas(11), 11)}
								fontWeight={800}
								fill="rgba(15,23,42,0.92)"
							>
								{space.name}
							</text>
						</g>
					);
				})}
				{layerVisibility.region && floorPlanElements.filter((element) => element.kind === 'analysis_region').map((element) => (
					<g key={`real-region-${element.id}`} style={{ pointerEvents: 'auto', cursor: 'pointer' }} onClick={(e) => { e.stopPropagation(); handleSelectCandidate(element); }}>
						<rect
							x={element.x * 1000}
							y={element.y * 1000}
							width={element.w * 1000}
							height={element.h * 1000}
							fill="rgba(250,204,21,0.06)"
							stroke="rgba(234,179,8,0.92)"
							strokeWidth="3"
							strokeDasharray="14 8"
						/>
						<text x={element.x * 1000 + 16} y={element.y * 1000 + 28} fill="rgba(133,77,14,0.95)" fontSize="16" fontWeight="800">
							{element.label}
						</text>
					</g>
				))}
				{layerVisibility.rooms && floorPlanElements.filter((element) => element.kind === 'function_zone' || element.kind === 'space_boundary').map((element, index) => {
					const pointString = toPointString(element.points);
					const c = center(element);
					const selected = element.id === selectedCandidateId;
					const hovered = !selected && element.id === hoveredCandidateId;
					const strokeColor = selected ? 'rgba(37,99,235,1)' : hovered ? 'rgba(59,130,246,0.98)' : 'rgba(5,150,105,0.7)';
					const strokeW = selected ? pxToCanvas(2.6) : hovered ? pxToCanvas(1.9) : pxToCanvas(1.2);
					const dash = (selected || hovered) ? undefined : '8 6';
					return (
						<g key={`real-zone-${element.id}`} style={{ pointerEvents: 'auto', cursor: 'pointer' }}
							onClick={(e) => { e.stopPropagation(); handleSelectCandidate(element); }}
							onMouseEnter={() => setHoveredCandidateId(element.id)}
							onMouseLeave={() => setHoveredCandidateId('')}>
							{pointString ? (
								<polygon points={pointString} fill={selected ? 'rgba(59,130,246,0.018)' : hovered ? 'rgba(96,165,250,0.012)' : 'rgba(16,185,129,0.10)'} stroke={strokeColor} strokeWidth={strokeW} vectorEffect="non-scaling-stroke" strokeDasharray={dash} />
							) : (
								<rect x={element.x * 1000} y={element.y * 1000} width={element.w * 1000} height={element.h * 1000} fill={selected ? 'rgba(59,130,246,0.018)' : hovered ? 'rgba(96,165,250,0.012)' : 'rgba(16,185,129,0.10)'} stroke={strokeColor} strokeWidth={strokeW} vectorEffect="non-scaling-stroke" strokeDasharray={dash} />
							)}
							<circle cx={c.x - 42} cy={c.y - 28} r="6" fill="rgba(5,150,105,0.95)" />
							<text x={c.x} y={c.y - 4} fill="rgba(15,23,42,0.92)" fontSize="18" fontWeight="800" textAnchor="middle">{element.label}</text>
							<text x={c.x} y={c.y + 20} fill="rgba(15,23,42,0.64)" fontSize="13" textAnchor="middle">
								{element.areaSqm ? `${element.areaSqm}m² · ` : ''}{element.id}
							</text>
							{layerVisibility.labels && (
								<text x={element.x * 1000 + 8} y={element.y * 1000 + 18} fill="rgba(5,150,105,0.95)" fontSize="18" fontWeight="900">
									R{index + 1}
								</text>
							)}
						</g>
					);
				})}
				{layerVisibility.walls && floorPlanElements.filter((element) => element.kind === 'wall_trace').map((element, index) => {
					const selected = element.id === selectedCandidateId;
					const hovered = !selected && element.id === hoveredCandidateId;
					const highlight = getHighlightStroke(selected, hovered);
					return (
					<g key={`real-wall-${element.id}`} style={{ pointerEvents: 'auto', cursor: 'pointer' }}
						onClick={(e) => { e.stopPropagation(); handleSelectCandidate(element); }}
						onMouseEnter={() => setHoveredCandidateId(element.id)}
						onMouseLeave={() => setHoveredCandidateId('')}>
						{/* 透明加粗命中区，让细墙也容易点击 */}
						<rect
							x={element.x * 1000 - 6}
							y={element.y * 1000 - 6}
							width={Math.max(14, element.w * 1000 + 12)}
							height={Math.max(14, element.h * 1000 + 12)}
							fill="transparent"
						/>
						<rect
							x={element.x * 1000}
							y={element.y * 1000}
							width={Math.max(1.8, element.w * 1000)}
							height={Math.max(1.8, element.h * 1000)}
							fill="rgba(15,23,42,0.82)"
							vectorEffect="non-scaling-stroke"
						/>
						{highlight && (
							<rect
								x={element.x * 1000 - highlight.pad}
								y={element.y * 1000 - highlight.pad}
								width={Math.max(1.8, element.w * 1000) + highlight.pad * 2}
								height={Math.max(1.8, element.h * 1000) + highlight.pad * 2}
								fill="none"
								stroke={highlight.color}
								strokeWidth={highlight.width}
								vectorEffect="non-scaling-stroke"
							/>
						)}
						{layerVisibility.labels && (
							<text x={(element.x + element.w / 2) * 1000} y={(element.y + element.h / 2) * 1000 - 6} fill="rgba(15,23,42,0.9)" fontSize="14" fontWeight="900" textAnchor="middle">
								W{index + 1}
							</text>
						)}
					</g>
				)})}
				{layerVisibility.columns && floorPlanElements.filter((element) => element.kind === 'column').map((element, index) => {
					const cw = Math.max(6, element.w * 1000);
					const ch = Math.max(6, element.h * 1000);
					const cx = element.x * 1000;
					const cy = element.y * 1000;
					const selected = element.id === selectedCandidateId;
					const hovered = !selected && element.id === hoveredCandidateId;
					const highlight = getHighlightStroke(selected, hovered);
					return (
						<g key={`real-column-${element.id}`} style={{ pointerEvents: 'auto', cursor: 'pointer' }}
							onClick={(e) => { e.stopPropagation(); handleSelectCandidate(element); }}
							onMouseEnter={() => setHoveredCandidateId(element.id)}
							onMouseLeave={() => setHoveredCandidateId('')}>
							<rect
								x={cx}
								y={cy}
								width={cw}
								height={ch}
								fill="rgba(2,6,23,0.9)"
								vectorEffect="non-scaling-stroke"
							/>
							{highlight && (
								<rect
									x={cx - highlight.pad}
									y={cy - highlight.pad}
									width={cw + highlight.pad * 2}
									height={ch + highlight.pad * 2}
									fill="none"
									stroke={highlight.color}
									strokeWidth={highlight.width}
									vectorEffect="non-scaling-stroke"
								/>
							)}
							{layerVisibility.labels && (
								<text x={cx + cw / 2} y={cy + ch / 2 + 5} fill="rgba(250,204,21,0.95)" fontSize="16" fontWeight="900" textAnchor="middle">
									C{index + 1}
								</text>
							)}
						</g>
					);
				})}
				{floorPlanElements.filter((element) => (element.kind === 'door' && layerVisibility.doors) || (element.kind === 'window' && layerVisibility.windows)).map((element, index) => {
					const ew = Math.max(4, element.w * 1000);
					const eh = Math.max(4, element.h * 1000);
					const ex = element.x * 1000;
					const ey = element.y * 1000;
					const selected = element.id === selectedCandidateId;
					const hovered = !selected && element.id === hoveredCandidateId;
					const highlight = getHighlightStroke(selected, hovered);
					const baseFill = element.kind === 'door' ? 'rgba(245,158,11,0.9)' : 'rgba(14,165,233,0.78)';
					return (
						<g key={`real-opening-${element.id}`} style={{ pointerEvents: 'auto', cursor: 'pointer' }}
							onClick={(e) => { e.stopPropagation(); handleSelectCandidate(element); }}
							onMouseEnter={() => setHoveredCandidateId(element.id)}
							onMouseLeave={() => setHoveredCandidateId('')}>
							{/* 透明加粗命中区 */}
							<rect
								x={ex - 6}
								y={ey - 6}
								width={Math.max(16, ew + 12)}
								height={Math.max(16, eh + 12)}
								fill="transparent"
							/>
							{/* 物理对象：选中/悬停时直接高亮 stroke */}
							<rect
								x={ex}
								y={ey}
								width={ew}
								height={eh}
								fill={baseFill}
								vectorEffect="non-scaling-stroke"
							/>
							{highlight && (
								<rect
									x={ex - highlight.pad}
									y={ey - highlight.pad}
									width={ew + highlight.pad * 2}
									height={eh + highlight.pad * 2}
									fill="none"
									stroke={highlight.color}
									strokeWidth={highlight.width}
									vectorEffect="non-scaling-stroke"
								/>
							)}
							{layerVisibility.labels && (
								<text x={ex + ew / 2} y={ey - 4} fill={element.kind === 'door' ? 'rgba(180,83,9,0.95)' : 'rgba(2,132,199,0.95)'} fontSize="15" fontWeight="900" textAnchor="middle">
									{element.kind === 'door' ? 'D' : 'N'}{index + 1}
								</text>
							)}
						</g>
					);
				})}
			</svg>
		);
	};

	return (
		<div className={`relative h-full w-full overflow-hidden bg-[#1f1f1f] text-white ${className ?? ''}`}>
			<input
				ref={planUploadInputRef}
				type="file"
				accept=".dwg,.dxf,.pdf,.png,.jpg,.jpeg,.webp"
				className="hidden"
				onChange={handlePlanUploadChange}
			/>
			<div
				className="absolute inset-0"
				style={{
					backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.05) 1px, transparent 0)',
					backgroundSize: '22px 22px',
					backgroundPosition: 'center center',
				}}
			/>

			<div className="pointer-events-none absolute inset-x-0 top-0 z-30 pl-[108px] pr-[460px] pt-7">
				<div
					className="pointer-events-auto inline-flex max-w-full flex-col gap-3"
					onMouseEnter={() => setHeaderHovered(true)}
					onMouseLeave={() => setHeaderHovered(false)}
				>
					<div className="text-[17px] font-semibold tracking-[0.02em] text-white">
						{sessionId} / {activeSpace}
					</div>
					{headerHovered && (
						<div className="flex flex-wrap gap-2">
							{spaceOptions.map((space) => {
								const active = space === activeSpace;
								return (
									<button
										key={`sandbox-space-${space}`}
										onClick={() => onActiveSpaceChange?.(space)}
										className={`inline-flex items-center rounded-full border px-4 py-[0.3rem] text-[12px] font-medium transition ${
											active
												? 'border-white/55 bg-white/24 text-white backdrop-blur-xl shadow-[inset_0_1px_0_rgba(255,255,255,0.26)]'
												: 'border-white/20 bg-white/12 text-white/86 backdrop-blur-lg hover:border-white/30 hover:bg-white/18 hover:text-white'
										}`}
									>
										{space}
									</button>
								);
							})}
						</div>
					)}
				</div>
			</div>

			<div
				ref={canvasViewportRef}
				className={`absolute inset-y-0 left-0 right-[420px] z-10 overflow-hidden overscroll-none select-none touch-none ${isCanvasPanning ? 'cursor-grabbing' : 'cursor-default'}`}
				onClick={() => {
					if (selectedCandidateId) {
						setSelectedCandidateId('');
						setActiveTab('baseline');
					}
				}}
				onWheel={(event) => {
					event.preventDefault();
					event.stopPropagation();
					zoomCanvasAt(event.clientX, event.clientY, event.deltaY > 0 ? 0.92 : 1.087);
				}}
				onPointerDown={(event) => {
					if (isSelectingAnalysisRegion && event.button === 0) {
						event.preventDefault();
						event.stopPropagation();
						event.currentTarget.setPointerCapture(event.pointerId);
						const start = normalizedCanvasPoint(event.clientX, event.clientY);
						analysisRegionDragRef.current = {
							pointerId: event.pointerId,
							startX: start.x,
							startY: start.y,
						};
						setAnalysisRegionDraft({ x: start.x, y: start.y, w: 0.001, h: 0.001 });
						return;
					}
					if (event.button !== 1) return;
					event.preventDefault();
					event.stopPropagation();
					event.currentTarget.setPointerCapture(event.pointerId);
					canvasPanDragRef.current = {
						pointerId: event.pointerId,
						startX: event.clientX,
						startY: event.clientY,
						originX: canvasTransform.x,
						originY: canvasTransform.y,
					};
					setIsCanvasPanning(true);
				}}
				onPointerMove={(event) => {
					const regionDrag = analysisRegionDragRef.current;
					if (regionDrag && regionDrag.pointerId === event.pointerId) {
						event.preventDefault();
						event.stopPropagation();
						const current = normalizedCanvasPoint(event.clientX, event.clientY);
						setAnalysisRegionDraft(buildRegionFromPoints({ x: regionDrag.startX, y: regionDrag.startY }, current));
						return;
					}
					const drag = canvasPanDragRef.current;
					if (!drag || drag.pointerId !== event.pointerId) return;
					event.preventDefault();
					event.stopPropagation();
					setCanvasTransform((current) => ({
						...current,
						x: drag.originX + event.clientX - drag.startX,
						y: drag.originY + event.clientY - drag.startY,
					}));
				}}
				onPointerUp={(event) => {
					stopAnalysisRegionSelection(event.pointerId);
					stopCanvasPanning(event.pointerId);
				}}
				onPointerCancel={(event) => {
					setAnalysisRegionDraft(null);
					analysisRegionDragRef.current = null;
					stopCanvasPanning(event.pointerId);
				}}
				onLostPointerCapture={() => {
					setAnalysisRegionDraft(null);
					analysisRegionDragRef.current = null;
					stopCanvasPanning();
				}}
				onAuxClick={(event) => {
					if (event.button !== 1) return;
					event.preventDefault();
					event.stopPropagation();
				}}
			>
				<div className="relative h-full w-full pl-[92px] pt-[100px]">
					<div
						className="absolute inset-0 overflow-hidden bg-cyan-950/[0.03] text-white/70"
						style={{
							transform: `translate3d(${canvasTransform.x}px, ${canvasTransform.y}px, 0) scale(${canvasTransform.zoom})`,
							transformOrigin: 'left top',
						}}
					>
						<div className="absolute overflow-hidden bg-white" style={mediaFrameStyle}>
							{hasRealPlan && showBaseMap && layerVisibility.baseMap && activePlanTopic?.mimeType?.startsWith('image/') && (
								<img
									src={activePlanTopic.uploadedFileUrl}
									alt={realPlanLabel}
									onLoad={handleBaseMapLoad}
									className="pointer-events-none absolute inset-0 h-full w-full object-fill"
									style={{ opacity: baseMapOpacity / 100 }}
								/>
							)}
							{hasRealPlan && showBaseMap && layerVisibility.baseMap && activePlanTopic?.mimeType === 'application/pdf' && pdfPreviewDataUrl && (
								<img
									src={pdfPreviewDataUrl}
									alt={realPlanLabel}
									onLoad={handleBaseMapLoad}
									className="pointer-events-none absolute inset-0 h-full w-full object-fill"
									style={{ opacity: baseMapOpacity / 100, filter: baseMapTintFilter }}
								/>
							)}
							{hasRealPlan && showBaseMap && layerVisibility.baseMap && activePlanTopic?.mimeType === 'application/pdf' && !pdfPreviewDataUrl && (
								<div className="absolute inset-0 flex items-center justify-center bg-white text-sm text-slate-500">
									正在渲染 PDF 平面...
								</div>
							)}
							{hasRealPlan && showBaseMap && layerVisibility.baseMap && activePlanTopic?.sourceType === 'dxf' && activePlanTopic?.mimeType !== 'application/pdf' && (
								<>
									{dxfGeometry && dxfGeometry.entityCount > 0 ? (
										<svg
											className="pointer-events-none absolute inset-0 h-full w-full"
											viewBox={`0 0 ${dxfGeometry.width} ${dxfGeometry.height}`}
											preserveAspectRatio="xMidYMid meet"
											style={{ background: '#050505', filter: baseMapTintFilter }}
											aria-label="DXF 图纸预览"
										>
											<rect x="0" y="0" width={dxfGeometry.width} height={dxfGeometry.height} fill="#050505" />
											{dxfGeometry.fills.filter((fill) => fill.source !== 'solid').map((fill, index) => (
												<polygon
													key={`dxf-fill-${index}`}
													points={fill.points.map((p) => `${p.x},${p.y}`).join(' ')}
													fill={getDxfFill(fill, dxfEntityAlpha * 0.45)}
													stroke="none"
												/>
											))}
											{dxfGeometry.lines.map((line, index) => (
												<line
													key={`dxf-line-${index}`}
													x1={line.x1} y1={line.y1} x2={line.x2} y2={line.y2}
													stroke={getDxfStroke(line, dxfEntityAlpha)}
													strokeWidth="1"
													vectorEffect="non-scaling-stroke"
													strokeLinecap="square"
												/>
											))}
											{dxfGeometry.circles.map((circle, index) => (
												<circle
													key={`dxf-circle-${index}`}
													cx={circle.cx} cy={circle.cy} r={circle.r}
													fill="none"
													stroke={getDxfStroke(circle, dxfEntityAlpha)}
													strokeWidth="1"
													vectorEffect="non-scaling-stroke"
												/>
											))}
											{dxfGeometry.arcs.map((arc, index) => (
												<path
													key={`dxf-arc-${index}`}
													d={describeArcPath(arc)}
													fill="none"
													stroke={getDxfStroke(arc, dxfEntityAlpha)}
													strokeWidth="1"
													vectorEffect="non-scaling-stroke"
												/>
											))}
											{dxfGeometry.texts.map((text, index) => (
												<text
													key={`dxf-text-${index}`}
													x={text.x} y={text.y}
													fill={getDxfTextFill(text, dxfEntityAlpha)}
													fontSize={Math.max(5, Math.min(text.height, 16))}
													fontFamily="Arial, 'Microsoft YaHei', sans-serif"
													textAnchor="middle"
													dominantBaseline="central"
													transform={text.rotation ? `rotate(${-text.rotation} ${text.x} ${text.y})` : undefined}
												>
													{text.text}
												</text>
											))}
										</svg>
									) : (
										<div className="absolute inset-0 flex items-center justify-center bg-slate-950 text-sm text-white/62">
											{dxfLoadError ?? 'DXF 已接入，正在解析矢量图形'}
										</div>
									)}
								</>
							)}
							<div className="absolute" style={floorPlanContentFrameStyle}>
								{renderFloorPlanIRLayer()}
							</div>
							{layerVisibility.region && displayedMainPlanBox && (
								<div
									className="pointer-events-none absolute border-2 border-emerald-500/90 bg-emerald-300/5"
									style={{
										left: `${displayedMainPlanBox.x * 100}%`,
										top: `${displayedMainPlanBox.y * 100}%`,
										width: `${displayedMainPlanBox.w * 100}%`,
										height: `${displayedMainPlanBox.h * 100}%`,
									}}
								>
									<div className="absolute -bottom-7 left-0 rounded-sm bg-emerald-500 px-2 py-1 text-[11px] font-semibold text-white">
										mainPlanBox · {mainPlanBoxSourceLabel}
									</div>
								</div>
							)}
							{layerVisibility.region && displayedFocusBounds && (
								<div
									className="pointer-events-none absolute border-2 border-dashed border-fuchsia-500/90 bg-fuchsia-300/8"
									style={{
										left: `${displayedFocusBounds.x * 100}%`,
										top: `${displayedFocusBounds.y * 100}%`,
										width: `${displayedFocusBounds.w * 100}%`,
										height: `${displayedFocusBounds.h * 100}%`,
									}}
								>
									<div className="absolute -top-7 right-0 rounded-sm bg-fuchsia-500 px-2 py-1 text-[11px] font-semibold text-white">
										focusBounds · {displayedFocusIsMainPlan ? '已作基准' : '不作基准'}
									</div>
								</div>
							)}
							{layerVisibility.region && displayedRecognitionBox && (
								<div
									className="pointer-events-none absolute border-2 border-dashed border-yellow-400/95 bg-yellow-300/10"
									style={{
										left: `${displayedRecognitionBox.x * 100}%`,
										top: `${displayedRecognitionBox.y * 100}%`,
										width: `${displayedRecognitionBox.w * 100}%`,
										height: `${displayedRecognitionBox.h * 100}%`,
									}}
								>
									<div className="absolute -top-7 left-0 rounded-sm bg-yellow-400 px-2 py-1 text-[11px] font-semibold text-slate-950">
										主平面识别区
									</div>
								</div>
							)}
						</div>
						{!floorPlanElements.length && (
							<div
								className="absolute left-[140px] top-[140px] max-w-[360px] border border-white/14 bg-black/62 p-4 text-white shadow-[0_16px_42px_rgba(0,0,0,0.28)] backdrop-blur-xl"
								onPointerDown={(event) => event.stopPropagation()}
							>
								<div className="text-sm font-semibold">{hasRealPlan ? '尚未生成真实 FloorPlanIR' : '暂无真实底图'}</div>
								<div className="mt-2 text-xs leading-5 text-white/64">
									{hasRealPlan
										? '当前已读取基准底图，但没有可用的编译候选。请先从真实底图编译墙柱候选'
										: '请先从项目底盘上传 PDF / DXF / 图片底图，再编译墙柱候选'}
								</div>
								{hasRealPlan && (
									<div className="mt-3 flex items-center gap-2">
										<label className="shrink-0 text-[10px] text-white/50">比例尺mm/norm</label>
										<input
											type="number"
											min={500}
											max={200000}
											step={500}
											placeholder={detectedMmPerNorm ? String(Math.round(detectedMmPerNorm)) : '自动'}
											value={manualScaleMmPerNorm ?? ''}
											onChange={(e) => {
												const v = parseFloat(e.target.value);
												setManualScaleMmPerNorm(Number.isFinite(v) && v > 0 ? v : null);
											}}
											className="w-24 rounded border border-white/18 bg-white/8 px-2 py-0.5 text-[11px] text-white/90 placeholder-white/30 focus:outline-none"
										/>
										{detectedMmPerNorm && (
											<span className="text-[10px] text-white/38">上次检测：{Math.round(detectedMmPerNorm)}</span>
										)}
									</div>
								)}
								<button
									onClick={handleGenerateFloorPlanIR}
									disabled={!hasRealPlan || isTracingFloorPlan}
									className="mt-4 rounded-full border border-cyan-200/40 bg-cyan-300/18 px-3 py-1.5 text-[11px] font-semibold text-cyan-50 disabled:cursor-not-allowed disabled:opacity-40"
								>
									{isTracingFloorPlan ? '编译中...' : '从底图编译候选'}
								</button>
							</div>
						)}
						<div className="absolute left-4 top-3 rounded-full border border-white/12 bg-black/48 px-3 py-1 text-[11px] font-medium text-white/72 backdrop-blur-sm">
							{hasRealPlan && showBaseMap ? '真实图纸 + 编译候选层' : '编译候选层'} · {hasRealPlan ? realPlanLabel : activeVersion?.name ?? '等待真实底图'}
						</div>
						<div className="absolute right-4 top-4 rounded-full border border-amber-200/40 bg-amber-300/18 px-3 py-1.5 text-xs text-amber-50">
							风险：入口识别依赖导视深度
						</div>
					</div>
				</div>
				{/* 比例尺 overlay：脱离缩放层，保持屏幕固定像素尺寸 */}
				{rulerActive && rulerState && (() => {
					const { x0, y0, x1, y1, knownMm } = rulerState;
					const zm = canvasTransform.zoom;
					const toLocal = (nx: number, ny: number) => ({
						lx: canvasTransform.x + (mediaBox.left + nx * mediaBox.width) * zm,
						ly: canvasTransform.y + (mediaBox.top + ny * mediaBox.height) * zm,
					});
					const { lx: ax, ly: ay } = toLocal(x0, y0);
					const { lx: bx, ly: by } = toLocal(x1, y1);
					const mx = (ax + bx) / 2;
					const my = (ay + by) / 2;
					const dxPx = (x1 - x0) * mediaBox.width;
					const dyPx = (y1 - y0) * mediaBox.height;
					const lenPx = Math.hypot(dxPx, dyPx);
					const isH = Math.abs(y1 - y0) <= Math.abs(x1 - x0);
					// 标尺长度必须映射到与后端 mmPerNormalized 一致的 content 坐标域，
					// 否则 page 留白会让纵向长度被压缩，出现“横准竖偏”的系统误差'
					const measureBox = floorPlanIR?.sourceContentBox ?? { x: 0, y: 0, w: 1, h: 1 };
					const toMeasureSpace = (nx: number, ny: number) => {
						const mw = Math.max(1e-6, measureBox.w);
						const mh = Math.max(1e-6, measureBox.h);
						return {
							x: (nx - measureBox.x) / mw,
							y: (ny - measureBox.y) / mh,
						};
					};
					const aMeasure = toMeasureSpace(x0, y0);
					const bMeasure = toMeasureSpace(x1, y1);
					const normLen = Math.hypot(bMeasure.x - aMeasure.x, bMeasure.y - aMeasure.y);
					const inferredMmPerNorm = knownMm && knownMm > 0 && normLen > 0.0001 ? Math.round(knownMm / normLen) : null;
					const inferredMmPerPx = knownMm && knownMm > 0 && lenPx > 0.5 ? knownMm / lenPx : null;
					const ratioForDisplay = manualScaleMmPerNorm ?? inferredMmPerNorm;
					const clampNorm = (value: number) => Math.min(1, Math.max(0, value));
					const effectiveMmPerNorm = manualScaleMmPerNorm;
					const effectiveMmPerPx = manualScaleMmPerPx;
					// "测得"必须只使用已生效全局比例，避免被当前输入 knownMm 锁死成恒定值'
					const measuredMm = effectiveMmPerPx && lenPx > 0
						? Math.max(1, Math.round(lenPx * effectiveMmPerPx))
						: (effectiveMmPerNorm && normLen > 0
							? Math.max(1, Math.round(normLen * effectiveMmPerNorm))
							: null);
					const sdx = bx - ax;
					const sdy = by - ay;
					const screenLen = Math.hypot(sdx, sdy);
					const perpX = screenLen > 1e-6 ? -sdy / screenLen : 0;
					const perpY = screenLen > 1e-6 ? sdx / screenLen : 1;
					const guideLen = Math.hypot(canvasSize.width, canvasSize.height) * 0.9;
					return (
						<>
							{/* SVG 主尺 + 垂线辅助 + 端刻度 */}
							<svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 50, overflow: 'visible' }}>
								{/* 辅助线始终垂直于标尺方向 */}
								<line x1={ax - perpX * guideLen} y1={ay - perpY * guideLen} x2={ax + perpX * guideLen} y2={ay + perpY * guideLen} stroke="rgba(255,31,31,0.92)" strokeWidth="1.8" strokeDasharray="12 8" strokeLinecap="round" />
								<line x1={bx - perpX * guideLen} y1={by - perpY * guideLen} x2={bx + perpX * guideLen} y2={by + perpY * guideLen} stroke="rgba(255,31,31,0.92)" strokeWidth="1.8" strokeDasharray="12 8" strokeLinecap="round" />
								{/* 主标尺线 */}
								<line x1={ax} y1={ay} x2={bx} y2={by} stroke="#38bdf8" strokeWidth="2" />
								{isH ? (<>
									<line x1={ax} y1={ay - 7} x2={ax} y2={ay + 7} stroke="#38bdf8" strokeWidth="2" />
									<line x1={bx} y1={by - 7} x2={bx} y2={by + 7} stroke="#38bdf8" strokeWidth="2" />
								</>) : (<>
									<line x1={ax - 7} y1={ay} x2={ax + 7} y2={ay} stroke="#38bdf8" strokeWidth="2" />
									<line x1={bx - 7} y1={by} x2={bx + 7} y2={by} stroke="#38bdf8" strokeWidth="2" />
								</>)}
							</svg>
							{/* 整体拖动透明命中区 */}
							<div
								style={isH ? {
									position: 'absolute', left: `${Math.min(ax, bx)}px`, top: `${my - 8}px`,
									width: `${Math.abs(bx - ax)}px`, height: 16, cursor: 'move', zIndex: 52, touchAction: 'none',
								} : {
									position: 'absolute', left: `${mx - 8}px`, top: `${Math.min(ay, by)}px`,
									width: 16, height: `${Math.abs(by - ay)}px`, cursor: 'move', zIndex: 52, touchAction: 'none',
								}}
								onPointerDown={(e) => {
									e.stopPropagation();
									(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
									const pt = normalizedCanvasPoint(e.clientX, e.clientY);
									rulerDragRef.current = { endpoint: 'body', pointerId: e.pointerId, bodyStart: { dragX: pt.x, dragY: pt.y, x0, y0, x1, y1 } };
								}}
								onPointerMove={(e) => {
									e.stopPropagation();
									if (!rulerDragRef.current || rulerDragRef.current.endpoint !== 'body' || rulerDragRef.current.pointerId !== e.pointerId) return;
									const bs = rulerDragRef.current.bodyStart!;
									const pt = normalizedCanvasPoint(e.clientX, e.clientY);
									const dx = pt.x - bs.dragX;
									const dy = pt.y - bs.dragY;
									setRulerState((prev) => prev ? {
										...prev,
										x0: clampNorm(bs.x0 + dx),
										y0: clampNorm(bs.y0 + dy),
										x1: clampNorm(bs.x1 + dx),
										y1: clampNorm(bs.y1 + dy),
									} : prev);
								}}
								onPointerUp={(e) => {
									e.stopPropagation();
									if (rulerDragRef.current?.pointerId === e.pointerId) rulerDragRef.current = null;
								}}
								onPointerCancel={(e) => {
									e.stopPropagation();
									if (rulerDragRef.current?.pointerId === e.pointerId) rulerDragRef.current = null;
								}}
								onLostPointerCapture={(e) => {
									if (rulerDragRef.current?.pointerId === e.pointerId) rulerDragRef.current = null;
								}}
							/>
							{/* 端点 handle */}
							{([0, 1] as const).map((ep) => {
								const px = ep === 0 ? ax : bx;
								const py = ep === 0 ? ay : by;
								return (
									<div key={ep} style={{
										position: 'absolute', left: `${px - 10}px`, top: `${py - 10}px`,
										width: 20, height: 20, borderRadius: '50%',
										background: 'rgba(255,255,255,0.70)',
										border: '2px solid rgba(56,189,248,0.95)',
										cursor: 'crosshair', zIndex: 54,
										boxShadow: '0 0 0 1px rgba(56,189,248,0.3)', touchAction: 'none',
									}}
									onPointerDown={(e) => {
										e.stopPropagation();
										e.currentTarget.setPointerCapture(e.pointerId);
										rulerDragRef.current = { endpoint: ep, pointerId: e.pointerId };
									}}
									onPointerMove={(e) => {
										e.stopPropagation();
										if (!rulerDragRef.current || rulerDragRef.current.endpoint !== ep || rulerDragRef.current.pointerId !== e.pointerId) return;
										const pt = normalizedCanvasPoint(e.clientX, e.clientY);
										setRulerState((prev) => {
											if (!prev) return prev;
											const fixedX = ep === 0 ? prev.x1 : prev.x0;
											const fixedY = ep === 0 ? prev.y1 : prev.y0;
											const adx = Math.abs(pt.x - fixedX);
											const ady = Math.abs(pt.y - fixedY);
											const snapX = adx >= ady ? clampNorm(pt.x) : fixedX;
											const snapY = adx >= ady ? fixedY : clampNorm(pt.y);
											return ep === 0 ? { ...prev, x0: snapX, y0: snapY } : { ...prev, x1: snapX, y1: snapY };
										});
									}}
									onPointerUp={(e) => {
										e.stopPropagation();
										if (rulerDragRef.current?.pointerId === e.pointerId) rulerDragRef.current = null;
									}}
									onPointerCancel={(e) => {
										e.stopPropagation();
										if (rulerDragRef.current?.pointerId === e.pointerId) rulerDragRef.current = null;
									}}
									onLostPointerCapture={(e) => {
										if (rulerDragRef.current?.pointerId === e.pointerId) rulerDragRef.current = null;
									}}
									/>
								);
							})}
							{/* 内联 popup：mm 输入 + 确认 */}
							<div style={{
								position: 'absolute', left: `${mx}px`, top: `${my}px`,
								transform: isH ? 'translate(-50%, 14px)' : 'translate(14px, -50%)',
								zIndex: 55, display: 'flex', alignItems: 'center', gap: 6,
								background: '#0c1a26f2', border: '1px solid #38bdf844', borderRadius: 8,
								padding: '5px 10px', whiteSpace: 'nowrap', pointerEvents: 'auto',
								boxShadow: '0 2px 12px #0008', fontSize: 13,
							}}>
								<input
									type="text"
									value={isRulerInputEditing
										? rulerInputDraft
										: (measuredMm !== null ? measuredMm.toLocaleString() : '待校')}
									placeholder="输入mm"
									onFocus={() => {
										setIsRulerInputEditing(true);
										setRulerInputDraft(knownMm && knownMm > 0 ? String(Math.round(knownMm)) : '');
									}}
									onChange={(e) => {
										if (!isRulerInputEditing) return;
										setRulerInputDraft(e.target.value);
										const v = parseFloat(e.target.value);
										setRulerState((prev) => prev ? { ...prev, knownMm: Number.isFinite(v) && v > 0 ? v : null } : prev);
									}}
									onBlur={() => {
										const v = parseFloat(rulerInputDraft);
										if (Number.isFinite(v) && v > 0) {
											setRulerState((prev) => prev ? { ...prev, knownMm: v } : prev);
										} else {
											setRulerState((prev) => prev ? { ...prev, knownMm: null } : prev);
											setRulerInputDraft('');
										}
										setIsRulerInputEditing(false);
									}}
									onKeyDown={(e) => {
										if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
										e.stopPropagation();
									}}
									style={{
										width: 68, background: '#1e3344', border: '1px solid #38bdf866',
										borderRadius: 5, color: '#e0f2fe', fontSize: 13, padding: '2px 6px', outline: 'none',
									}}
									onClick={(e) => e.stopPropagation()}
								/>
								<span style={{ color: '#7dd3fc', fontSize: 13 }}>mm</span>
								{ratioForDisplay && (
									<span style={{ color: '#94a3b8', fontSize: 11 }}>比例 {ratioForDisplay.toLocaleString()}</span>
								)}
								<button
									onClick={(e) => {
										e.stopPropagation();
										if (inferredMmPerNorm) setManualScaleMmPerNorm(inferredMmPerNorm);
										if (inferredMmPerPx) setManualScaleMmPerPx(inferredMmPerPx);
										setRulerActive(false);
										setRulerState(null);
										setRulerInputDraft('');
										setIsRulerInputEditing(false);
									}}
									disabled={!inferredMmPerNorm}
									style={{
										background: inferredMmPerNorm ? '#0284c7' : '#334155',
										color: '#fff', border: 'none', borderRadius: 5, padding: '3px 10px',
										fontSize: 12, cursor: inferredMmPerNorm ? 'pointer' : 'not-allowed', fontWeight: 600,
									}}
								>
									确认
								</button>
							</div>
						</>
					);
				})()}
			</div>

			<div className="pointer-events-auto absolute bottom-4 left-[92px] z-30 flex items-center gap-2 rounded-full border border-white/12 bg-black/58 px-3 py-2 text-white shadow-[0_12px_36px_rgba(0,0,0,0.28)] backdrop-blur-xl">
				<button
					onClick={() => zoomCanvasAtViewportCenter(0.9)}
					className="flex h-7 w-7 items-center justify-center rounded-full border border-white/12 bg-white/8 text-white/78 hover:bg-white/14"
					aria-label="缩小平面推演"
				>
					<ZoomOut className="h-3.5 w-3.5" />
				</button>
				<button
					onClick={() => {
						setCanvasTransform({ zoom: 1, x: 0, y: 0 });
					}}
					className="min-w-[54px] rounded-full border border-white/12 bg-white/8 px-2 py-1 text-[11px] font-semibold text-white/82 hover:bg-white/14"
				>
					{Math.round(canvasTransform.zoom * 100)}%
				</button>
				<button
					onClick={() => zoomCanvasAtViewportCenter(1.1)}
					className="flex h-7 w-7 items-center justify-center rounded-full border border-white/12 bg-white/8 text-white/78 hover:bg-white/14"
					aria-label="放大平面推演"
				>
					<ZoomIn className="h-3.5 w-3.5" />
				</button>
				<div className="h-5 w-px bg-white/12" />
				<span className="px-1 text-[11px] text-white/48">滚轮缩放</span>
				{hasRealPlan && (
					<>
						<div className="h-5 w-px bg-white/12" />
						<button
							onClick={() => setIsSelectingAnalysisRegion((current) => !current)}
							className={`rounded-full border px-3 py-1 text-[11px] font-semibold transition ${
								isSelectingAnalysisRegion
									? 'border-yellow-200/70 bg-yellow-300/24 text-yellow-50 hover:bg-yellow-300/30'
									: 'border-white/14 bg-white/8 text-white/66 hover:bg-white/14 hover:text-white'
							}`}
						>
							{isSelectingAnalysisRegion ? '正在框' : '框选识别区'}
						</button>
						<button
							onClick={() => setShowBaseMap((current) => !current)}
							className={`rounded-full border px-3 py-1 text-[11px] font-semibold transition ${
								showBaseMap
									? 'border-cyan-200/35 bg-cyan-300/16 text-cyan-50 hover:bg-cyan-300/22'
									: 'border-white/14 bg-white/8 text-white/66 hover:bg-white/14 hover:text-white'
							}`}
							aria-label={showBaseMap ? '关闭基准底图' : '显示基准底图'}
						>
							{showBaseMap ? '关闭底图' : '显示底图'}
						</button>
					{showBaseMap && (
						<>
							{/* 透明度滑杆 */}
							<div className="flex items-center gap-1">
								<span className="text-[10px] text-white/44">透明</span>
								<input type="range" min={10} max={100} step={5} value={baseMapOpacity} onChange={(e) => setBaseMapOpacity(Number(e.target.value))} style={{ width: 60, accentColor: '#38bdf8', cursor: 'pointer' }} />
								<span className="w-7 text-[10px] tabular-nums text-white/50">{baseMapOpacity}%</span>
							</div>
							{/* 单色叠色 */}
							<div className="flex items-center gap-1">
								{(['', '0deg', '180deg', '220deg', '280deg', '90deg'] as const).map((hue) => {
									const labels: Record<string, string> = { '': '原色', '0deg': '暖橙', '180deg': '', '220deg': '', '280deg': '', '90deg': '' };
									const swBg: Record<string, string> = { '': 'linear-gradient(135deg,#e0e0e0 50%,#bbb)', '0deg': '#f97316', '180deg': '#06b6d4', '220deg': '#3b82f6', '280deg': '#a855f7', '90deg': '#22c55e' };
									const active = baseMapTint === hue;
									return (
										<button
											key={hue}
											title={labels[hue]}
											onClick={() => setBaseMapTint(hue)}
											style={{
												width: 15, height: 15, borderRadius: '50%', flexShrink: 0,
												background: swBg[hue] ?? '#888', cursor: 'pointer',
												border: active ? '2px solid #fff' : '2px solid rgba(255,255,255,0.2)',
												boxShadow: active ? '0 0 0 1.5px #38bdf8' : 'none',
											}}
										/>
									);
								})}
							</div>
						</>
					)}
					</>
				)}
				<div className="h-5 w-px bg-white/12" />
				<button
					onClick={() => zoomCanvasAtViewportCenter(0.9)}
					className="flex h-7 w-7 items-center justify-center rounded-full border border-white/12 bg-white/8 text-white/78 hover:bg-white/14"
					aria-label="缩小"
				>
					<Minus className="h-3.5 w-3.5" />
				</button>
				<button
					onClick={() => zoomCanvasAtViewportCenter(1.1)}
					className="flex h-7 w-7 items-center justify-center rounded-full border border-white/12 bg-white/8 text-white/78 hover:bg-white/14"
					aria-label="放大"
				>
					<Plus className="h-3.5 w-3.5" />
				</button>
			</div>

			<div className="pointer-events-none absolute bottom-4 right-4 top-6 z-20 w-[420px]">
				<div className="pointer-events-auto flex h-full flex-col overflow-hidden rounded-none border border-white/50 bg-white text-slate-900 backdrop-blur-xl">
					<div className="border-b border-slate-200/80 p-4">
						<input
							readOnly
							value=""
							placeholder={`搜索${activeSpace}输入源（例：图纸、流线、历史项目）`}
							className="h-11 w-full rounded-full border border-slate-200/90 bg-white/72 px-4 text-sm text-slate-900 outline-none placeholder:text-slate-400"
						/>
						<div className="mt-3 flex flex-wrap gap-2">
							{[
								{ key: 'project', label: '项目驾驶' },
								{ key: 'baseline', label: '图纸基线' },
								{ key: 'versions', label: '版本' },
								{ key: 'export', label: '输出' },
								...(selectedCandidateId ? [{ key: 'properties', label: '对象属' }] : []),
							].map((tab) => (
								<button
									key={tab.key}
									onClick={() => setActiveTab(tab.key as typeof activeTab)}
									className={`rounded-full px-4 py-2 text-[12px] font-medium transition ${
										activeTab === tab.key ? 'bg-slate-900 text-white' : 'bg-slate-100/90 text-slate-600 hover:bg-slate-200/90 hover:text-slate-900'
									}`}
								>
									{tab.label}
								</button>
							))}
						</div>
					</div>

					<div className="flex-1 overflow-y-auto p-4">
						{activeTab === 'properties' && selectedCandidate && (
							// 属性编辑面板
							<div className="space-y-4">
								{/* 对象头部信息 */}
								<div className="border border-slate-200 bg-white p-4 shadow-sm">
									<div className="flex items-start justify-between gap-3">
										<div>
											<p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">{selectedKindLabel}</p>
											<h3 className="mt-2 text-lg font-semibold text-slate-950">{selectedCandidate.label}</h3>
											<p className="mt-2 text-xs leading-5 text-slate-500">
												置信度 {Math.round(selectedCandidate.confidence * 100)}% · 状态 {selectedCandidate.status}
											</p>
										</div>
										<button
											onClick={() => {
												setSelectedCandidateId('');
												setActiveTab('baseline');
											}}
											className="text-slate-400 hover:text-slate-600"
											title="关闭"
										>
											×
										</button>
									</div>
								</div>

								{/* 编辑表单 */}
								<div className="border border-slate-200 bg-white p-4 shadow-sm">
									<div className="mb-4 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">基本属性</div>
									<div className="space-y-3">
										<label className="block">
											<span className="text-xs font-semibold text-slate-700">名称</span>
											<input
												value={selectedCandidate.label}
												onChange={(e) => handleUpdateCandidate(selectedCandidate.id, { label: e.target.value })}
												className="mt-1 h-9 w-full rounded border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none focus:border-slate-400"
											/>
										</label>
										<label className="block">
											<span className="text-xs font-semibold text-slate-700">
												{selectedCandidate.kind === 'wall_trace' ? '墙厚' : selectedCandidate.kind === 'column' ? '宽度' : selectedCandidate.kind === 'door' ? '门宽' : selectedCandidate.kind === 'window' ? '窗宽' : '宽度'} (mm)
											</span>
											<input
												type="number"
												value={selectedCandidate.widthMm ?? 0}
												onChange={(e) => handleUpdateCandidate(selectedCandidate.id, { widthMm: Number(e.target.value) })}
												className="mt-1 h-9 w-full rounded border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none focus:border-slate-400"
											/>
										</label>
										<label className="block">
											<span className="text-xs font-semibold text-slate-700">
												{selectedCandidate.kind === 'column' ? '深度' : selectedCandidate.kind === 'function_zone' || selectedCandidate.kind === 'space_boundary' ? '面积 (m²)' : '高度 (mm)'}
											</span>
											<input
												type="number"
												value={(selectedCandidate.kind === 'function_zone' || selectedCandidate.kind === 'space_boundary') ? selectedCandidate.areaSqm ?? 0 : selectedCandidate.depthMm ?? 0}
												onChange={(e) => {
													const value = Number(e.target.value);
													handleUpdateCandidate(selectedCandidate.id, (selectedCandidate.kind === 'function_zone' || selectedCandidate.kind === 'space_boundary') ? { areaSqm: value } : { depthMm: value });
												}}
												className="mt-1 h-9 w-full rounded border border-slate-200 bg-white px-3 text-sm text-slate-900 outline-none focus:border-slate-400"
											/>
										</label>
										{(calibratedMmPerNorm ?? detectedMmPerNorm) != null && selectedCandidate.kind !== 'function_zone' && selectedCandidate.kind !== 'space_boundary' && (
											<p className="text-[11px] leading-5 text-slate-400">
												实测估算：{Math.round(selectedCandidate.w * (calibratedMmPerNorm ?? detectedMmPerNorm!))} × {Math.round(selectedCandidate.h * (calibratedMmPerNorm ?? detectedMmPerNorm!))} mm
												{!calibratedMmPerNorm && <span className="ml-1 text-amber-500">（比例尺未校准，仅供参考）</span>}
											</p>
										)}
									</div>
								</div>

								{/* 位置和坐标 */}
								<div className="border border-slate-200 bg-white p-4 shadow-sm">
									<div className="mb-4 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">位置坐标</div>
									<div className="grid grid-cols-3 gap-2">
										<label className="block">
											<span className="text-[11px] font-semibold text-slate-700">X</span>
											<input type="number" value={Number(selectedCandidate.x.toFixed(4))} step="0.0001" onChange={(e) => handleUpdateCandidate(selectedCandidate.id, { x: Number(e.target.value) })} className="mt-1 h-8 w-full rounded border border-slate-200 bg-white px-2 text-xs text-slate-900 outline-none focus:border-slate-400" />
										</label>
										<label className="block">
											<span className="text-[11px] font-semibold text-slate-700">Y</span>
											<input type="number" value={Number(selectedCandidate.y.toFixed(4))} step="0.0001" onChange={(e) => handleUpdateCandidate(selectedCandidate.id, { y: Number(e.target.value) })} className="mt-1 h-8 w-full rounded border border-slate-200 bg-white px-2 text-xs text-slate-900 outline-none focus:border-slate-400" />
										</label>
										<label className="block">
											<span className="text-[11px] font-semibold text-slate-700">W</span>
											<input type="number" value={Number(selectedCandidate.w.toFixed(4))} step="0.0001" onChange={(e) => handleUpdateCandidate(selectedCandidate.id, { w: Number(e.target.value) })} className="mt-1 h-8 w-full rounded border border-slate-200 bg-white px-2 text-xs text-slate-900 outline-none focus:border-slate-400" />
										</label>
										<label className="block col-span-full">
											<span className="text-[11px] font-semibold text-slate-700">H</span>
											<input type="number" value={Number(selectedCandidate.h.toFixed(4))} step="0.0001" onChange={(e) => handleUpdateCandidate(selectedCandidate.id, { h: Number(e.target.value) })} className="mt-1 h-8 w-full rounded border border-slate-200 bg-white px-2 text-xs text-slate-900 outline-none focus:border-slate-400" />
										</label>
									</div>
								</div>

								{/* 状态设置 */}
								<div className="border border-slate-200 bg-white p-4 shadow-sm">
									<div className="mb-4 text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">状态</div>
									<div className="flex items-center gap-2">
										<select
											value={selectedCandidate.status}
											onChange={(e) => handleUpdateCandidate(selectedCandidate.id, { status: e.target.value as any })}
											className="flex-1 rounded border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-400"
										>
											<option value="candidate">候选</option>
											<option value="confirmed">已确认</option>
											<option value="edited">已编辑</option>
										</select>
									</div>
									<div className="mt-3 text-[10px] text-slate-500">
										ID: <span className="font-mono">{selectedCandidate.id}</span>
									</div>
								</div>

								{/* 操作按钮 */}
								<div className="flex gap-2">
									<button
										onClick={() => {
											handleConfirmCandidate(selectedCandidate.id);
											onInjectReference?.(`对象 ${selectedCandidate.label} 已确认`);
										}}
										disabled={selectedCandidate.status === 'confirmed'}
										className="flex-1 rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-semibold text-emerald-700 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-40"
									>
										确认
									</button>
									<button
										onClick={() => {
											handleDeleteCandidate(selectedCandidate.id);
											setActiveTab('baseline');
											onInjectReference?.(`对象 ${selectedCandidate.label} 已删除`);
										}}
										className="flex-1 rounded-full border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-semibold text-red-700 hover:bg-red-100"
									>
										🗑 删除
									</button>
								</div>
							</div>
						)}
						{!(activeTab === 'properties' && selectedCandidate) && (
							// 原有内容（项目底盘、图纸基线等）
							<div className="space-y-3">
								<div className="border border-slate-200 bg-white p-4 shadow-sm">
								<div className="flex items-start justify-between gap-3">
									<div>
										<p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">计划基础</p>
										<h3 className="mt-1 text-base font-semibold text-slate-950">图纸基线 · {activeSpace}</h3>
										<p className="mt-1 text-xs leading-5 text-slate-500">来自项目底盘 · 平面图与空间关系</p>
									</div>
									<span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] text-emerald-700">
										{isSpaceSyncing ? '同步中' : '已同步'}
									</span>
								</div>
								<div className="mt-3 grid grid-cols-[112px_1fr] gap-3">
									<div className="relative h-[88px] overflow-hidden border border-slate-200 bg-white">
										<div className="absolute inset-0 bg-[linear-gradient(rgba(15,23,42,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(15,23,42,0.05)_1px,transparent_1px)] bg-[size:12px_12px]" />
										<div className="absolute left-[12%] top-[18%] h-[62%] w-[76%] border-[3px] border-slate-900" />
										<div className="absolute left-[30%] top-[18%] h-[62%] w-[2px] bg-slate-900" />
										<div className="absolute left-[49%] top-[18%] h-[62%] w-[2px] bg-slate-900" />
										<div className="absolute left-[12%] top-[46%] h-[2px] w-[76%] bg-slate-900" />
										<div className="absolute left-[55%] top-[52%] h-[18%] w-[28%] border border-cyan-500 bg-cyan-400/15" />
										<div className="absolute bottom-2 left-2 rounded-full bg-white/90 px-2 py-0.5 text-[10px] font-semibold text-slate-600">IR 工程稿</div>
									</div>
									<div className="min-w-0 text-xs leading-5 text-slate-600">
										<div className="truncate">{hasRealPlan ? realPlanLabel : `FloorPlanIR_${activeSpace}_v0 基线`}</div>
										<div className="truncate">{hasRealPlan ? `${activePlanTopic?.sourceType?.toUpperCase() ?? 'FILE'} · ${activePlanTopic?.status ?? 'uploaded'}` : 'AlignedBrief + SPG + 图纸'}</div>
										<div className="truncate text-sky-700">{activePlanTopic?.updatedAt ?? spaceSyncedAt}</div>
										<div className="mt-1 truncate text-slate-400">{activePlanTopic?.parseMessage ?? floorPlanIR?.irVersion ?? '尚未生成真实 FloorPlanIR'}</div>
									</div>
								</div>
								<div className="mt-3 grid grid-cols-3 gap-2 text-center">
									{[
										['识别质量', floorPlanQuality ? `${floorPlanQuality.score}` : '待生'],
										['比例', scaleStatusLabel],
										['闭合空间', floorPlanRooms.length],
										['门窗洞口', floorPlanOpenings.length],
										['墙线对象', floorPlanLocks],
										['结构', floorPlanColumns.length],
										['识别', recognitionBoxOnPage ? '已定' : '整图'],
									].map(([label, value]) => (
										<div key={`ir-data-${label}`} className="border border-slate-200 bg-slate-50 px-2 py-2">
											<div className="text-[10px] text-slate-400">{label}</div>
											<div className="mt-1 text-sm font-semibold text-slate-900">{value}</div>
										</div>
									))}
								</div>
								<div className="mt-3 flex flex-wrap gap-2">
									<button
										onClick={handleOpenPlanUploadPicker}
										disabled={isUploadingPlan}
										className="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
									>
										<Upload className="mr-1 inline h-3.5 w-3.5" />
										{isUploadingPlan ? '上传' : '上传图纸'}
									</button>
									<button onClick={() => onInjectReference?.(`平面推演@${activeSpace} · 查看 FloorPlanIR 基线`)} className="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50">
										查看基线
									</button>
									<button
										onClick={() => setIsSelectingAnalysisRegion((current) => !current)}
										disabled={!hasRealPlan}
										className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-[11px] font-medium text-amber-700 hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-40"
									>
										{recognitionBoxOnPage ? '重选识别区' : '框选识别区'}
									</button>
									<button
										onClick={() => {
											if (rulerActive) {
												setRulerActive(false);
												setRulerState(null);
												setRulerInputDraft('');
												setIsRulerInputEditing(false);
											} else {
												const initKnownMm = manualScaleMmPerNorm ?? detectedMmPerNorm;
												setRulerActive(true);
												setRulerInputDraft(initKnownMm ? String(Math.round(initKnownMm)) : '');
												setRulerState({ x0: 0.25, y0: 0.5, x1: 0.55, y1: 0.5, knownMm: initKnownMm ?? null });
												setIsRulerInputEditing(false);
											}
										}}
										disabled={!hasRealPlan}
										className={`rounded-full border px-3 py-1.5 text-[11px] font-medium disabled:cursor-not-allowed disabled:opacity-40 ${rulerActive ? 'border-sky-300 bg-sky-50 text-sky-700 hover:bg-sky-100' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'}`}
									>
										{rulerActive ? '关闭标尺' : '比例尺标'}
									</button>
									<button
										onClick={handleGenerateFloorPlanIR}
										disabled={!hasRealPlan || isTracingFloorPlan}
										title={!hasRealPlan ? '请先上传图纸' : (isTracingFloorPlan ? '正在生成' : '生成 FloorPlanIR')}
										className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-[11px] font-medium text-emerald-700 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-40"
									>
										{isTracingFloorPlan ? '生成' : '生成 FloorPlanIR'}
									</button>
									<button onClick={() => onInjectReference?.(`平面推演@${activeSpace} · 请方案高参解释当前基线`)} className="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50">
										注入高参
									</button>
								</div>
								{hasRealPlan && !rulerActive && manualScaleMmPerNorm && (
									<div className="mt-2 flex items-center gap-2 text-[10px] text-slate-400">
										<span>比例尺已校准: {manualScaleMmPerNorm.toLocaleString()} mm/norm</span>
										<button onClick={() => { setManualScaleMmPerNorm(null); setManualScaleMmPerPx(null); }} className="hover:text-slate-600">清除</button>
									</div>
								)}
								{gates && (
									<div className={`mt-3 border p-3 ${isFormalIRReady ? 'border-emerald-200 bg-emerald-50/70' : 'border-amber-200 bg-amber-50/70'}`}>
										<div className="flex items-center justify-between gap-3">
											<div>
												<div className={`text-xs font-semibold ${isFormalIRReady ? 'text-emerald-900' : 'text-amber-900'}`}>
													{isFormalIRReady ? 'Reviewed FloorPlanIR 候选' : '编译候选态，未进入正式 IR'}
												</div>
												<div className={`mt-1 text-[11px] leading-4 ${isFormalIRReady ? 'text-emerald-800' : 'text-amber-900'}`}>
													正式 IR 只展示通过 Contract / Coordinate / Structure / Geometry / System Gate 的对象
												</div>
												<div className="mt-1 text-[10px] leading-4 text-slate-500">
													坐标基准：{mainPlanBoxSourceLabel}；focus cluster {floorPlanIR?.focusUsedAsMainPlanBox ? '已用作基准' : '仅作调试'}
												</div>
												{!isFormalIRReady && promotionBlockers.length > 0 && (
													<div className="mt-1 text-[10px] leading-4 text-amber-900">
														阻断：{promotionBlockers.slice(0, 2).join(' / ')}
													</div>
												)}
											</div>
											<span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${isFormalIRReady ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-800'}`}>
												{compileResult?.status ?? 'gate_pending'}
											</span>
										</div>
										<div className="mt-3 grid grid-cols-2 gap-2 xl:grid-cols-5">
											{([
												{ label: 'Contract', gate: gates.contract },
												{ label: 'Coordinate', gate: gates.coordinate },
												{ label: 'Structure', gate: gates.structureBackbone },
												{ label: 'Geometry', gate: gates.geometry },
												{ label: 'System', gate: gates.system },
											]).filter((entry): entry is { label: string; gate: GateResult } => Boolean(entry.gate)).map(({ label, gate }) => (
												<div key={`gate-${label}`} className="border border-white/70 bg-white/70 p-2">
													<div className="text-[10px] text-slate-500">{label}</div>
													<div className={`mt-1 text-sm font-semibold ${gate.status === 'passed' ? 'text-emerald-700' : 'text-red-700'}`}>{gate.status === 'passed' ? '通过' : '未过'}</div>
													<div className="text-[10px] text-slate-400">{gate.score}/100</div>
												</div>
											))}
										</div>
										{reviewBuckets.length > 0 && (
											<div className="mt-3 space-y-1.5">
												{reviewBuckets.map((bucket) => (
													<div key={`review-bucket-${bucket.key}`} className="border border-white/70 bg-white/70 px-2 py-1.5 text-[11px]">
														<div className="flex items-center justify-between">
															<span className="font-medium text-slate-700">{bucket.label}</span>
															<span className="font-semibold text-amber-800">{bucket.items.length}</span>
														</div>
														{bucket.items.slice(0, 2).map((item) => (
															<div key={item.id} className="mt-1 truncate text-[10px] leading-4 text-slate-500">
																{item.message}
															</div>
														))}
													</div>
												))}
											</div>
										)}
									</div>
								)}
								{floorPlanDiagnostics && (
									<div className="mt-3 border border-slate-200 bg-white p-3">
										<div className="flex items-start justify-between gap-3">
											<div>
												<p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">编译中间层</p>
												<h3 className="mt-1 text-sm font-semibold text-slate-900">ROI / 分类 / 墙图流水线</h3>
												<p className="mt-1 text-[11px] leading-4 text-slate-500">
													用于排查候选对象在哪一层丢失或被错误聚类，不作为正式 IR
												</p>
											</div>
											<span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${floorPlanDiagnostics.regionInsufficient ? 'bg-red-50 text-red-700' : 'bg-slate-100 text-slate-600'}`}>
												{floorPlanDiagnostics.regionInsufficient ? 'ROI 不足' : floorPlanDiagnostics.mode ?? 'pending'}
											</span>
										</div>
										<div className="mt-3 grid grid-cols-3 gap-2 text-center">
											{[
												['原始线段', floorPlanDiagnostics.rawSegments ?? 0],
												['ROI 线段', floorPlanDiagnostics.scopedSegments ?? 0],
												['CTM', floorPlanDiagnostics.pdfCoordinateTransform ?? 'n/a'],
												['墙分', classCounts?.wall ?? 0],
												['开口符', classCounts?.opening_symbol ?? 0],
												['噪声', classCounts?.noise ?? 0],
												['严格候', pipelineStats?.strictCandidates ?? 0],
												['聚焦候', pipelineStats?.focusedStrictCandidates ?? 0],
												['平行', pipelineStats?.pairedWalls ?? 0],
												['严格合并', pipelineStats?.strictMerged ?? 0],
												['最终清', debugLayerCounts?.cleaned ?? 0],
												['选用链路', pipelineStats?.selectedPipeline ?? 'none'],
											].map(([label, value]) => (
												<div key={`pipeline-stat-${label}`} className="border border-slate-200 bg-slate-50 px-2 py-2">
													<div className="text-[10px] text-slate-400">{label}</div>
													<div className="mt-1 truncate text-xs font-semibold text-slate-900">{value}</div>
												</div>
											))}
										</div>
										<div className="mt-2 grid grid-cols-2 gap-2 text-[10px] leading-4 text-slate-500">
											<span>整页回退：{floorPlanDiagnostics.regionFallback ? '' : ''}</span>
											<span>主簇数量：{floorPlanDiagnostics.primaryCluster?.componentCount ?? 0}</span>
											<span>focus 参与：{floorPlanDiagnostics.primaryCluster?.focused ? '' : ''}</span>
											<span>focus 作基准：{floorPlanDiagnostics.primaryCluster?.focusUsedAsMainPlanBox ? '' : ''}</span>
											<span>坐标门：{floorPlanDiagnostics.coordinateConsistency?.status ?? 'n/a'} / {floorPlanDiagnostics.coordinateConsistency?.score ?? 0}</span>
											<span>主干门：{floorPlanDiagnostics.structureBackbone?.status ?? 'n/a'} / {floorPlanDiagnostics.structureBackbone?.score ?? 0}</span>
										</div>
									</div>
								)}
								{floorPlanQuality && (
									<div className="mt-3 border border-slate-200 bg-slate-50 p-3">
										<div className="flex items-center justify-between text-xs">
											<span className="font-semibold text-slate-800">候选质量分析</span>
											<span className="font-semibold text-slate-950">{floorPlanQuality.score}/100</span>
										</div>
										<div className="mt-2 h-1.5 rounded-full bg-slate-200">
											<div className="h-1.5 rounded-full bg-slate-900" style={{ width: `${floorPlanQuality.score}%` }} />
										</div>
										<div className="mt-2 grid grid-cols-3 gap-1 text-[10px] leading-4 text-slate-500">
											<span>比例 {floorPlanQuality.breakdown.scale}</span>
											<span>墙体 {floorPlanQuality.breakdown.wallConnectivity}</span>
											<span>闭合 {floorPlanQuality.breakdown.roomClosure}</span>
											<span>洞口 {floorPlanQuality.breakdown.openingBinding}</span>
											<span>OCR {floorPlanQuality.breakdown.ocrMatch}</span>
											<span>问题 {floorPlanQuality.breakdown.issuePenalty}</span>
										</div>
									</div>
								)}
								{floorPlanIssues.length > 0 && (
									<div className="mt-3 border border-amber-200 bg-amber-50/70 p-3">
										<div className="text-xs font-semibold text-amber-900">待校正问题</div>
										<div className="mt-2 space-y-1.5">
											{floorPlanIssues.slice(0, 4).map((issue, index) => {
												const message = typeof issue === 'string' ? issue : issue.message;
												const severity = typeof issue === 'string' ? 'warning' : issue.severity;
												return (
													<div key={`floorplan-issue-${index}`} className="flex items-start gap-2 text-[11px] leading-4 text-amber-900">
														<span className={`mt-1 h-1.5 w-1.5 flex-none rounded-full ${severity === 'error' ? 'bg-red-500' : severity === 'info' ? 'bg-sky-500' : 'bg-amber-500'}`} />
														<span>{message}</span>
													</div>
												);
											})}
										</div>
									</div>
								)}
							</div>

							{floorPlanElements.length > 0 && (
								<div className="border border-slate-200 bg-white p-4 shadow-sm">
									<div className="flex items-start justify-between gap-3">
										<div>
											<p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">图层控制</p>
											<h3 className="mt-1 text-base font-semibold text-slate-950">显示 / 清除</h3>
											<p className="mt-1 text-xs leading-5 text-slate-500">按图层显示、隐藏或清除候选对象，清除会写回当前 IR 草稿</p>
										</div>
										<div className="flex items-center gap-1.5">
											<button
												onClick={() => {
													// 一次 patch 清除所有可清除层，避免多次写入快照覆盖问题
													setAnalysisRegion(null);
													setAnalysisRegionDraft(null);
													const allClearKinds: FloorPlanElementKind[] = ['function_zone', 'space_boundary', 'wall_trace', 'column', 'door', 'window'];
													updateFloorPlanElements((elements) => elements.filter((el) => !allClearKinds.includes(el.kind)));
													setSelectedCandidateId('');
												}}
												className="rounded-full border border-red-200 bg-red-50 px-3 py-1.5 text-[11px] font-medium text-red-700 hover:bg-red-100"
											>
												全清
											</button>
											<button
												onClick={() => setLayerVisibility(DEFAULT_LAYER_VISIBILITY)}
												className="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
											>
												全显
											</button>
										</div>
									</div>
									<div className="mt-3 space-y-2">
										{layerRows.map((row, index) => (
											<div key={`layer-row-${row.key}`} className="flex items-center justify-between gap-2 border border-slate-200 bg-slate-50 px-3 py-2">
												<button onClick={() => handleToggleLayer(row.key)} className="flex min-w-0 items-center gap-2 text-left">
													<span className="w-5 text-[10px] font-semibold text-slate-400">{index + 1}</span>
													<span className={`h-2.5 w-2.5 rounded-full ${layerVisibility[row.key] ? 'bg-emerald-500' : 'bg-slate-300'}`} />
													<span className="text-xs font-semibold text-slate-800">{row.label}</span>
													<span className="text-[10px] text-slate-400">{row.count}</span>
												</button>
												<div className="flex items-center gap-1.5">
													<button onClick={() => handleToggleLayer(row.key)} className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[10px] text-slate-600 hover:bg-slate-100">
														{layerVisibility[row.key] ? '隐藏' : '显示'}
													</button>
													<button
														onClick={() => handleClearLayer(row.key)}
														disabled={!row.clearable || row.count === 0}
														className="rounded-full border border-red-200 bg-red-50 px-2 py-1 text-[10px] text-red-700 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-35"
													>
														清除
													</button>
												</div>
											</div>
										))}
									</div>
								</div>
							)}

							{floorPlanElements.length > 0 && (
								<div className="border border-slate-200 bg-white p-4 shadow-sm">
									<div className="flex items-start justify-between gap-3">
										<div>
											<p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">编译候选层</p>
											<h3 className="mt-1 text-base font-semibold text-slate-950">墙 / 柱 / 门窗候选</h3>
											<p className="mt-1 text-xs leading-5 text-slate-500">未通过 Gate 前只作为候选复核，不写入正式 FloorPlanIR</p>
										</div>
										<button
											onClick={() => onInjectReference?.(`平面推演@${activeSpace} · 请检查 FloorPlanIR 候选：墙 ${floorPlanWalls.length}，柱 ${floorPlanColumns.length}，门 ${floorPlanDoors.length}，窗 ${floorPlanWindows.length}，闭合空间 ${floorPlanRooms.length}`)}
											className="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
										>
											发给高参
										</button>
									</div>
									<div className="mt-3 grid grid-cols-4 gap-2">
										{candidateGroups.map((group) => {
											const lowConfidence = group.items.filter((item) => item.confidence < 0.65).length;
											return (
												<div key={`candidate-group-${group.key}`} className="border border-slate-200 bg-slate-50 p-2">
													<div className="flex items-center gap-1.5">
														<span className={`h-2 w-2 rounded-full ${group.tone}`} />
														<span className="text-[11px] text-slate-500">{group.label}</span>
													</div>
													<div className="mt-1 text-base font-semibold text-slate-950">{group.items.length}</div>
													<div className="text-[10px] text-slate-400">低置信 {lowConfidence}</div>
												</div>
											);
										})}
									</div>
									<div className="mt-3 space-y-2">
										{candidateGroups.flatMap((group) =>
											group.items.slice(0, 3).map((item) => ({ group, item }))
										).slice(0, 10).map(({ group, item }) => (
											<div key={`candidate-item-${item.id}`} className={`border px-3 py-2 ${selectedCandidateId === item.id ? 'border-rose-300 bg-rose-50' : 'border-slate-200 bg-white'}`}>
												<div className="flex items-center justify-between gap-3">
													<button onClick={() => handleSelectCandidate(item)} className="min-w-0 text-left">
														<div className="flex items-center gap-2">
															<span className={`h-2 w-2 rounded-full ${group.tone}`} />
															<span className="truncate text-xs font-semibold text-slate-800">{item.label}</span>
														</div>
														<div className="mt-0.5 text-[10px] text-slate-400">
															{item.widthMm ? `${item.widthMm}mm` : '宽度待定'} · {item.status === 'candidate' ? '候选' : item.status}
														</div>
													</button>
													<div className="flex items-center gap-2">
														<span className={`rounded-full px-2 py-0.5 text-[10px] ${item.confidence >= 0.72 ? 'bg-emerald-50 text-emerald-700' : item.confidence >= 0.6 ? 'bg-amber-50 text-amber-700' : 'bg-red-50 text-red-700'}`}>
															{Math.round(item.confidence * 100)}%
														</span>
													</div>
												</div>
												<div className="mt-2 flex flex-wrap gap-1.5">
													<button onClick={() => handleSelectCandidate(item)} className="rounded-full border border-slate-200 px-2 py-1 text-[10px] text-slate-600 hover:bg-slate-50">定位</button>
													<button onClick={() => handleConfirmCandidate(item.id)} disabled={item.status === 'confirmed'} className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-[10px] text-emerald-700 hover:bg-emerald-100 disabled:opacity-40">确认</button>
													<button onClick={() => handleDeleteCandidate(item.id)} className="rounded-full border border-red-200 bg-red-50 px-2 py-1 text-[10px] text-red-700 hover:bg-red-100">删除</button>
												</div>
											</div>
										))}
									</div>
									{selectedCandidate && (
										<div className="mt-3 border border-rose-200 bg-rose-50 p-3">
											<div className="flex items-start justify-between gap-3">
												<div>
													<div className="text-xs font-semibold text-rose-900">当前选中：{selectedKindLabel}</div>
													<div className="mt-1 text-[11px] leading-5 text-rose-800">
														{selectedCandidate.label} · 置信度 {Math.round(selectedCandidate.confidence * 100)}% · 状态 {selectedCandidate.status}
													</div>
												</div>
												<span className="rounded-full bg-white/70 px-2 py-0.5 text-[10px] text-rose-700">{selectedCandidate.id}</span>
											</div>
											<div className="mt-3 space-y-2">
												<label className="block">
													<span className="text-[10px] font-semibold text-rose-900">名称</span>
													<input
														value={selectedCandidate.label}
														onChange={(event) => handleUpdateCandidate(selectedCandidate.id, { label: event.target.value })}
														className="mt-1 h-8 w-full border border-rose-200 bg-white px-2 text-xs text-slate-900 outline-none"
													/>
												</label>
												<div className="grid grid-cols-2 gap-2">
													<label className="block">
														<span className="text-[10px] font-semibold text-rose-900">
															{selectedCandidate.kind === 'wall_trace' ? '墙长/宽度' : selectedCandidate.kind === 'column' ? '柱宽' : selectedCandidate.kind === 'door' ? '门洞' : selectedCandidate.kind === 'window' ? '窗洞' : '宽度'}
														</span>
														<input
															type="number"
															value={selectedCandidate.widthMm ?? 0}
															onChange={(event) => handleUpdateCandidate(selectedCandidate.id, { widthMm: Number(event.target.value) })}
															className="mt-1 h-8 w-full border border-rose-200 bg-white px-2 text-xs text-slate-900 outline-none"
														/>
													</label>
													<label className="block">
														<span className="text-[10px] font-semibold text-rose-900">
															{selectedCandidate.kind === 'column' ? '柱深' : selectedCandidate.kind === 'function_zone' || selectedCandidate.kind === 'space_boundary' ? '面积 m²' : '深度/高度'}
														</span>
														<input
															type="number"
															value={(selectedCandidate.kind === 'function_zone' || selectedCandidate.kind === 'space_boundary') ? selectedCandidate.areaSqm ?? 0 : selectedCandidate.depthMm ?? 0}
															onChange={(event) => {
																const value = Number(event.target.value);
																handleUpdateCandidate(selectedCandidate.id, (selectedCandidate.kind === 'function_zone' || selectedCandidate.kind === 'space_boundary') ? { areaSqm: value } : { depthMm: value });
															}}
															className="mt-1 h-8 w-full border border-rose-200 bg-white px-2 text-xs text-slate-900 outline-none"
														/>
													</label>
												</div>
												{(calibratedMmPerNorm ?? detectedMmPerNorm) != null && selectedCandidate.kind !== 'function_zone' && selectedCandidate.kind !== 'space_boundary' && (
													<p className="text-[11px] leading-5 text-rose-700/60">
														实测估算：{Math.round(selectedCandidate.w * (calibratedMmPerNorm ?? detectedMmPerNorm!))} × {Math.round(selectedCandidate.h * (calibratedMmPerNorm ?? detectedMmPerNorm!))} mm
														{!calibratedMmPerNorm && <span className="ml-1 text-amber-500">（未校准）</span>}
													</p>
												)}
												<div className="grid grid-cols-3 gap-2">
													<label className="block">
														<span className="text-[10px] font-semibold text-rose-900">X</span>
														<input type="number" value={Number(selectedCandidate.x.toFixed(3))} step="0.001" onChange={(event) => handleUpdateCandidate(selectedCandidate.id, { x: Number(event.target.value) })} className="mt-1 h-8 w-full border border-rose-200 bg-white px-2 text-xs text-slate-900 outline-none" />
													</label>
													<label className="block">
														<span className="text-[10px] font-semibold text-rose-900">Y</span>
														<input type="number" value={Number(selectedCandidate.y.toFixed(3))} step="0.001" onChange={(event) => handleUpdateCandidate(selectedCandidate.id, { y: Number(event.target.value) })} className="mt-1 h-8 w-full border border-rose-200 bg-white px-2 text-xs text-slate-900 outline-none" />
													</label>
													<label className="block">
														<span className="text-[10px] font-semibold text-rose-900">状态</span>
														<select value={selectedCandidate.status} onChange={(event) => handleUpdateCandidate(selectedCandidate.id, { status: event.target.value as FloorPlanElement['status'] })} className="mt-1 h-8 w-full border border-rose-200 bg-white px-2 text-xs text-slate-900 outline-none">
															<option value="candidate">候选</option>
															<option value="confirmed">确认</option>
															<option value="edited">已编辑</option>
														</select>
													</label>
												</div>
												{(selectedCandidate.kind === 'door' || selectedCandidate.kind === 'window') && (
													<div className="rounded-sm border border-rose-100 bg-white/70 p-2 text-[11px] leading-5 text-rose-800">
														{selectedCandidate.kind === 'door' ? '门洞设置：确认后将作为通行 opening 进入 Reviewed IR' : '窗洞设置：确认后将作为采光外窗 opening 进入 Reviewed IR'}
													</div>
												)}
											</div>
										</div>
									)}
									<div className="mt-3 flex flex-wrap gap-2">
										<button
											onClick={handleConfirmReviewedIR}
											disabled={!isFormalIRReady}
											className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-[11px] font-medium text-emerald-700 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-40"
										>
											确认 Reviewed IR
										</button>
										<button onClick={() => setSelectedCandidateId('')} className="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50">
											取消选中
										</button>
									</div>
								</div>
							)}

							<div className="border border-slate-200 bg-white p-4 shadow-sm">
								<div className="flex items-start justify-between gap-3">
									<div>
										<p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">方案控制台</p>
										<h3 className="mt-1 text-base font-semibold text-slate-950">{activeStrategy.title}</h3>
										<p className="mt-1 text-xs leading-5 text-slate-500">{activeStrategy.summary}</p>
										<p className="mt-1 text-xs leading-5 text-slate-400">代价：{activeStrategy.tradeoff}</p>
									</div>
									<span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] text-slate-500">
										{stageLabel(activeVersion?.stage ?? 'baseline')}
									</span>
								</div>

								<div className="mt-4 rounded-none border border-slate-200 bg-slate-50 p-3">
									<div className="mb-2 flex items-center gap-2 text-slate-800">
										<Lock className="h-4 w-4" />
										<p className="text-sm font-semibold">驾驶舱继承信息</p>
									</div>
									<div className="space-y-1 text-xs leading-5 text-slate-600">
										<p>项目：{sessionId}</p>
										<p>输入：AlignedBrief + SPG + 图纸 / 参考素材</p>
										<p>目标：轻量推演、可解释、可回写，不在沙盘内重复填写驾驶舱信息</p>
									</div>
								</div>
								{activeLayoutVariant && (
									<div className="mt-4 border border-cyan-200 bg-cyan-50/70 p-3">
										<div className="flex items-center justify-between gap-3">
											<p className="text-sm font-semibold text-cyan-950">后端推演版本</p>
											<span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-semibold text-cyan-700">{activeLayoutVariant.layout.spaces.length} 空间块</span>
										</div>
										<p className="mt-2 text-xs leading-5 text-cyan-900">{activeLayoutVariant.layout.explanation}</p>
										{activeLayoutVariant.intent.spatial_priorities?.length ? (
											<div className="mt-2 flex flex-wrap gap-1.5">
												{activeLayoutVariant.intent.spatial_priorities.slice(0, 4).map((priority) => (
													<span key={priority} className="rounded-full border border-cyan-200 bg-white px-2 py-0.5 text-[10px] text-cyan-800">{priority}</span>
												))}
											</div>
										) : null}
										{activeLayoutVariant.layout.risks?.length ? (
											<p className="mt-2 text-[11px] leading-4 text-amber-800">风险：{activeLayoutVariant.layout.risks.slice(0, 2).join(' / ')}</p>
										) : null}
									</div>
								)}

								<div className="mt-4">
									<div className="mb-2 flex items-center gap-2 text-slate-800">
										<Layers3 className="h-4 w-4" />
										<p className="text-sm font-semibold">参数权重</p>
									</div>
									<div className="space-y-3">
										{parameters.map((param) => (
											<div key={param.label}>
												<div className="mb-1 flex items-center justify-between text-xs text-slate-600">
													<span>{param.label}</span>
													<span>{param.value}</span>
												</div>
												<div className="h-1.5 rounded-full bg-slate-200">
													<div className="h-1.5 rounded-full bg-slate-900" style={{ width: `${param.value}%` }} />
												</div>
												<div className="mt-1 flex justify-between text-[11px] text-slate-400">
													<span>{param.left}</span>
													<span>{param.right}</span>
												</div>
											</div>
										))}
									</div>
								</div>

								<div className="mt-4">
									<p className="mb-2 text-sm font-semibold text-slate-800">指标摘要</p>
									<div className="grid grid-cols-2 gap-2">
										{metrics.map((metric) => (
											<div key={metric.label} className={`rounded-none border p-3 ${metricClass(metric.tone)}`}>
												<p className="text-[11px]">{metric.label}</p>
												<p className="mt-1 text-lg font-semibold">{metric.value}</p>
											</div>
										))}
									</div>
								</div>

								<div className="mt-4">
									<div className="mb-2 flex items-center gap-2 text-slate-800">
										<GitBranch className="h-4 w-4" />
										<p className="text-sm font-semibold">方案版本</p>
									</div>
									<div className="space-y-2">
										{strategies.map((strategy) => {
											const active = strategy.id === activeStrategyId;
											return (
												<button
													key={strategy.id}
													onClick={() => {
														setActiveStrategyId(strategy.id);
														if (layoutPackage?.variants.some((variant) => variant.variant_id === strategy.id)) {
															setActiveVersionId(strategy.id);
														}
													}}
													className={`w-full rounded-none border p-3 text-left transition ${
														active ? 'border-slate-900 bg-slate-950 text-white' : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
													}`}
												>
													<div className="flex items-center justify-between gap-3">
														<p className="text-sm font-semibold">{strategy.id} · {strategy.title}</p>
														<span className={active ? 'text-xs text-white/70' : 'text-xs text-slate-400'}>{strategy.score}</span>
													</div>
													<p className={active ? 'mt-1 text-xs text-white/70' : 'mt-1 text-xs text-slate-500'}>{strategy.summary}</p>
												</button>
											);
										})}
									</div>
								</div>

								<div className="mt-4 flex flex-wrap gap-2">
									<button
										onClick={handleCreateIteration}
										disabled={isGeneratingLayoutVariants}
										className="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-55"
									>
										<Plus className="mr-1 inline h-3.5 w-3.5" />
										{isGeneratingLayoutVariants ? '推演中...' : layoutPackage?.variants?.length ? '重新推演' : '新建推演'}
									</button>
									<button onClick={handleFreezeCurrent} className="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50">
										<RefreshCcw className="mr-1 inline h-3.5 w-3.5" />
										冻结版本
									</button>
									<button onClick={handleWriteBack} className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-[11px] font-medium text-emerald-700 hover:bg-emerald-100">
										<CheckCircle2 className="mr-1 inline h-3.5 w-3.5" />
										回写底盘
									</button>
									<button onClick={() => onInjectReference?.(`平面推演@${activeSpace} · 请方案高参解析 ${activeStrategy.title}`)} className="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50">
										<MessageSquareText className="mr-1 inline h-3.5 w-3.5" />
										注入高参
									</button>
									<button onClick={() => onEnterBoardSpace?.(activeSpace)} className="rounded-full border border-slate-200 px-3 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50">
										<SendHorizontal className="mr-1 inline h-3.5 w-3.5" />
										发往画布
									</button>
								</div>
							</div>

							<div className="grid grid-cols-2 gap-3">
								{sourcePanelItems.map((item) => (
									<div key={item.title} className="border border-slate-200 bg-white shadow-sm">
										<div className="relative h-24 overflow-hidden bg-slate-950">
											<div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.06)_1px,transparent_1px)] bg-[size:22px_22px]" />
											<div className="absolute left-[15%] top-[24%] h-[24%] w-[28%] border border-white/30 bg-white/10" />
											<div className="absolute left-[50%] top-[24%] h-[24%] w-[30%] border border-cyan-300/80 bg-cyan-300/20" />
											<div className="absolute bottom-3 left-3 rounded-full bg-black/50 px-2 py-0.5 text-[10px] text-white/72">{item.meta}</div>
										</div>
										<div className="p-3">
											<div className="text-sm font-semibold text-slate-900">{item.title}</div>
											<p className="mt-1 text-xs leading-5 text-slate-500">{item.desc}</p>
											<button
												onClick={() => {
													if (item.title === '下游骨架') onEnterBoardSpace?.(activeSpace);
													else if (item.title === '回写') handleWriteBack();
													else onInjectReference?.(`平面推演@${activeSpace} · ${item.title}`);
												}}
												className="mt-3 rounded-full border border-slate-200 px-3 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50"
											>
												{item.action}
											</button>
										</div>
									</div>
								))}
							</div>

							<div className="space-y-2">
								{versions.slice(0, 4).map((version) => (
									<button
										key={version.id}
										onClick={() => {
											setActiveVersionId(version.id);
											if (layoutPackage?.variants.some((variant) => variant.variant_id === version.id)) {
												setActiveStrategyId(version.id);
											}
										}}
										className="block w-full border border-slate-200 bg-white p-3 text-left shadow-sm hover:bg-slate-50"
									>
										<div className="flex items-center justify-between gap-2">
											<div className="text-sm font-semibold text-slate-900">{version.name}</div>
											<span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-500">{stageLabel(version.stage)}</span>
										</div>
										<p className="mt-1 text-xs leading-5 text-slate-500">{version.note}</p>
									</button>
								))}
							</div>
						</div>
						)}
				</div>
			</div>

		</div>
	</div>
	);
}
