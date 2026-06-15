/**
 * 左侧导航内容组件
 * 根据不同的胶囊模块渲染对应内容
 */
'use client';

import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent, type MouseEvent as ReactMouseEvent, type ReactNode, type WheelEvent as ReactWheelEvent } from 'react';
import { ChevronDown, ChevronLeft, ChevronRight, Eye, LayoutGrid, Link2, Rows3, ThumbsUp, X } from 'lucide-react';
import { createPortal } from 'react-dom';
import { Chart as ChartJS, RadarController, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend } from 'chart.js';
import { Radar } from 'react-chartjs-2';
import { KnowledgeGraphCanvas } from '@/components/KnowledgeGraphCanvas';
import { clampCanvasZoom, getWheelZoomFactor, zoomCanvasViewAt as zoomSharedCanvasViewAt } from '@/lib/canvasViewport';
import { describeArcPath, getDxfStroke, getDxfTextFill, parseDxfPreviewGeometry } from '@/lib/dxfPreview';
import type { DxfPreviewArc, DxfPreviewGeometry } from '@/lib/dxfPreview';
import type { ExpertGeneratedImage } from '@/types';
import { DecisionView } from '@/components/project-cockpit/DecisionView';
import { GeoIntelligencePanel } from '@/components/geo/GeoIntelligencePanel';
import { EMPTY_PROJECT_OVERVIEW, MOCK_PROJECT_OVERVIEW, MOCK_STAGES, type ViewKey } from '@/components/project-cockpit/mock/mockData';

ChartJS.register(RadarController, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

/* DSS 七维视角中文标签 */
const DSS_PERSPECTIVE_LABELS: Record<keyof DSSPerspectiveWeights, string> = {
	aesthetic: '美学',
	functional: '功能',
	operational: '运营',
	cost: '成本',
	risk: '风险',
	cultural: '文化',
	temporal: '时间',
};

/* DSS 九维本体中文标签 */
const DSS_NINE_DIM_LABELS: Record<keyof DSSNineDimSensitivity, string> = {
	people: '人',
	place: '地',
	space: '空间',
	function: '功能',
	flow: '动线',
	emotion: '情绪',
	culture: '文化',
	constraint: '约束',
	time: '时间',
};

/* DSS 预设枚举 */
const DSS_ARCHETYPES = ['民宿', '酒店', '办公', '商业', '展陈', '餐饮', '住宅', '文旅'] as const;
const DSS_GEO_TYPES = ['山地', '城市', '水滨', '乡村'] as const;

/* DSS 行业市场需求基准（Phase 1 静态，值越高需求越旺） */
const DSS_MARKET_DEMAND: Record<string, Record<string, number>> = {
	'民宿': { '山地': 9, '城市': 4, '水滨': 7, '乡村': 6 },
	'酒店': { '山地': 3, '城市': 8, '水滨': 6, '乡村': 2 },
	'办公': { '山地': 1, '城市': 9, '水滨': 2, '乡村': 1 },
	'商业': { '山地': 2, '城市': 9, '水滨': 4, '乡村': 3 },
	'展陈': { '山地': 2, '城市': 7, '水滨': 3, '乡村': 2 },
	'餐饮': { '山地': 4, '城市': 8, '水滨': 5, '乡村': 3 },
	'住宅': { '山地': 3, '城市': 9, '水滨': 4, '乡村': 5 },
	'文旅': { '山地': 7, '城市': 5, '水滨': 8, '乡村': 7 },
};

/* DSS 九维行业中位数基准（0-10） */
const DSS_NINE_DIM_INDUSTRY_MEDIAN: DSSNineDimSensitivity = {
	people: 5, place: 4, space: 7, function: 7, flow: 5, emotion: 4, culture: 3, constraint: 3, time: 3,
};

const DSS_NINE_DIM_DEMO_FALLBACK: DSSNineDimSensitivity = {
	people: 6, place: 5, space: 8, function: 7, flow: 6, emotion: 7, culture: 4, constraint: 5, time: 4,
};

const clampRadarScore = (value: number) => Math.min(100, Math.max(0, Math.round(value)));

const getNineDimRadarScore = (
	key: keyof DSSNineDimSensitivity,
	sensitivity: Partial<DSSNineDimSensitivity> | undefined,
	fallback: DSSNineDimSensitivity = DSS_NINE_DIM_DEMO_FALLBACK
) => {
	const raw = Number(sensitivity?.[key]);
	const normalized = Number.isFinite(raw) && raw > 0 ? raw : fallback[key];
	return clampRadarScore(normalized * 10);
};

export type CockpitModuleKey = 'files' | 'assets' | 'inspiration' | 'board' | 'experts' | 'insight' | 'knowledge' | 'geo';
export type BoardCanvasSpace = '全部' | Exclude<ProjectFileCard['spaceScope'], '全局'>;
export type DssPage = 'sediment' | 'portfolio' | 'profile';
type BoardCanvasMode = '综合' | '色彩' | '材料' | '家具' | '氛围' | '反例';

interface CockpitPanelProps {
	moduleKey: CockpitModuleKey;
	preferredFileViewMode?: FileViewMode;
	sessionId?: string;
	projectLabel?: string;
	onProjectLabelChange?: (currentTitle: string) => void;
	projectOverview?: import('./project-cockpit/mock/mockData').ProjectOverview;
	activeBoardSpace?: BoardCanvasSpace;
	onActiveBoardSpaceChange?: (space: BoardCanvasSpace) => void;
	onEnterBoardSpace?: (space: Exclude<ProjectFileCard['spaceScope'], '全局'>) => void;
	onEnterSandboxSpace?: (space: Exclude<ProjectFileCard['spaceScope'], '全局'>) => void;
	onOpenInspirationLibrary?: () => void;
	onBackToAssets?: () => void;
	onBoardVisualBriefChange?: (brief: BoardVisualBrief | null) => void;
	onBoardZoomChange?: (zoom: number) => void;
	portfolioYearHeightScale?: number;
	onDssPageChange?: (page: DssPage) => void;
	onNodeClick?: (nodeId: string, label: string) => void;
	onCardClick?: (title: string) => void;
	onSwitchModule?: (target: 'floor_plan' | 'scheme_canvas') => void;
	onOpenGeoWorkspace?: () => void;
	className?: string;
}

type FlowCategory =
	| '项目锚点'
	| '外部认知'
	| '决策约束'
	| '空间策略'
	| '表达系统'
	| '评审定版';

type StageTag = 'S1 意图显影' | 'S2 分析扩展' | 'S3 审阅裁决' | 'S4 定向收束' | 'S5 缺口补全' | 'S6 定版冻结';

type FileStatus = '进行中' | '待审' | '已审' | '已冻结' | '待验证';
type SortMode = '相关性优先' | '引用热度' | '最近更新' | '标题 A-Z';
type FileViewMode = '统一视图' | '思维参谋';
type FilePresentationMode = '卡片模式' | '文档索引';
type KnowledgeEntryType = '待分类' | '习惯' | '经验' | '方法' | '模板' | '禁忌' | '案例复盘' | '作品';
type KnowledgeEntryStatus = '草稿' | '已整理' | '已验证' | '可复用';
type KnowledgeEntryScope = 'personal' | 'project';
type KnowledgePublishLevel = '草稿' | '已整理' | '团队发布' | '公开发布';

interface PortfolioProject {
	year: number;
	month?: number;
	spaceType: string;
	designFee: number;
	designArea: number;
	city?: string;
	clientType?: string;
}

interface PersonalKnowledgeEntry {
	id: string;
	title: string;
	type: KnowledgeEntryType;
	status: KnowledgeEntryStatus;
	summary: string;
	content: string;
	tags: string[];
	sourceContext?: string;
	updatedAt: string;
	/** 归属：个人 vs 项目级（Phase 1 默认 personal） */
	scope?: KnowledgeEntryScope;
	/** 发布级别（Phase 1 仅 草稿/已整理） */
	publishLevel?: KnowledgePublishLevel;
	/** 关联的项目/对话 ID（证据链） */
	evidenceLinks?: string[];
	/** 作品项目元数据（type === '作品' 时使用） */
	portfolio?: PortfolioProject;
}

/* ─── 硅基分身：设计师画像（DSS Phase 1） ─── */

interface DSSSpecialtyEntry {
	archetype: string;
	geoType: string;
	brandPositioning: string;
	projectCount: number;
	role: '主创' | '深化' | '项目管理' | '全案';
	confidenceLevel: 'done' | 'familiar' | 'heard_of';
}

interface DSSPerspectiveWeights {
	aesthetic: number;
	functional: number;
	operational: number;
	cost: number;
	risk: number;
	cultural: number;
	temporal: number;
}

interface DSSNineDimSensitivity {
	people: number;
	place: number;
	space: number;
	function: number;
	flow: number;
	emotion: number;
	culture: number;
	constraint: number;
	time: number;
}

interface DesignerProfile {
	id: string;
	displayName: string;
	yearsOfExperience: number;
	city: string;
	teamSize: '独立' | '小团队(2-5)' | '中型(6-20)' | '大型(20+)';
	companyType: '独立设计师' | '设计事务所' | '地产内部' | '设计公司';
	specialtyMatrix: DSSSpecialtyEntry[];
	perspectiveWeights: DSSPerspectiveWeights;
	nineDimSensitivity: DSSNineDimSensitivity;
	decisionStyle: {
		primaryApproach: string;
		riskTolerance: 'conservative' | 'moderate' | 'aggressive';
	};
	createdAt: string;
	updatedAt: string;
	dataSource: 'manual' | 'auto_extracted' | 'hybrid';
	evidenceCount: number;
}

interface ProjectFileCard {
	title: string;
	desc: string;
	badge: string;
	legacyCategory: string;
	objectAnchor: 'AlignedBrief' | 'SPG' | 'InitialDesignPack' | 'EvidenceOnly';
	flowCategory: FlowCategory;
	stage: StageTag;
	status: FileStatus;
	spaceScope: '全局' | '大堂' | '餐厅' | '客房' | '公区' | '后勤' | '连廊';
	primaryTopic: '用户' | '市场' | '竞品' | '空间' | '动线' | '预算' | '品牌' | '色彩' | '材料' | '灯光' | '家具';
	domainTags: string[];
	updatedAt: string;
	refCount: number;
}

type ResourceCategory = '家具' | '灯光' | '材料' | '工艺' | '配色' | '参考';
type ResourceSpace = '全局' | '大堂' | '餐厅' | '客房' | '公区' | '连廊' | '后勤';
type ResourceBudgetBand = '经济型' | '均衡型' | '高配型';
type ResourceRisk = '低' | '中' | '高';
type ResourceSourceType = 'system' | 'user';
type ResourceAnchorType = '产品点' | '材料点' | '构造点' | '体验点' | '氛围点' | '运营点';
type ResourceEntityType = 'project' | 'image' | 'anchor' | 'insight';
type ResourceAnchorMode = 'object' | 'relation';
type ResourceInsightType = 'observation' | 'action' | 'risk';
type ResourceEvidenceLevel = 'strong' | 'medium' | 'weak';
type AnchorOrigin = 'system' | 'user' | 'derived';
type AssetDetailAnchorPanelMode = 'expanded' | 'compact';

type PublicPictureCollection = 'default' | 'advisor-avatar' | 'furniture-1' | 'furniture-2';

interface ResourceItem {
	id: string;
	title: string;
	brand: string;
	series: string;
	category: ResourceCategory;
	imageSrc: string;
	fallbackImageSrc: string;
	localPictureName?: string;
	desc: string;
	space: ResourceSpace;
	budgetBand: ResourceBudgetBand;
	leadTimeDays: number;
	risk: ResourceRisk;
	tags: string[];
	alternatives: string[];
	sourceType?: ResourceSourceType;
	sourceName?: string;
	sourceAvatar?: string;
	recommendCount?: number;
	favoriteQuoteCount?: number;
	quoteCount?: number;
	imageCollection?: PublicPictureCollection;
	imageNames?: string[];
}

interface ResourceSeriesImage {
	id: string;
	name: string;
	src: string;
	fallbackSrc: string;
}

interface ResourceSourceTrace {
	projectId: string;
	imageId?: string;
	anchorId?: string;
	insightId?: string;
}

interface ResourceAnchorInsight {
	id: string;
	type: ResourceInsightType;
	title: string;
	summary: string;
	actionHint?: string;
	riskHint?: string;
	evidenceLevel: ResourceEvidenceLevel;
}

interface ResourceImageAnchor {
	id: string;
	resourceId: string;
	imageId: string;
	x: number;
	y: number;
	type: ResourceAnchorType;
	title: string;
	summary: string;
	tags: string[];
	space: ResourceSpace;
	topic: string;
	quotedReason: string;
	anchorMode: ResourceAnchorMode;
	evidenceLevel: ResourceEvidenceLevel;
	insights: ResourceAnchorInsight[];
	origin?: AnchorOrigin;
}

interface ResourceCardItem extends ResourceItem {
	coverImageSrc: string;
	imageSeries: ResourceSeriesImage[];
}

interface BasketSelectionItem {
	id: string;
	resourceId: string;
	resourceTitle: string;
	imageId: string;
	imageName: string;
	imageSrc: string;
	risk: ResourceRisk;
	leadTimeDays: number;
	anchorId?: string;
	anchorTitle?: string;
	anchorType?: ResourceAnchorType;
}

interface BoardCollectionItem {
	id: string;
	resourceId: string;
	resourceTitle: string;
	resourceCategory: ResourceCategory;
	imageId: string;
	imageName: string;
	imageSrc: string;
	space: string;
	sourceSpace: ResourceSpace;
	customTitle: string;
	note: string;
	tags: string[];
	desc: string;
	addedAt: string;
}

interface BoardCollectionDraft {
	resourceId: string;
	imageId: string;
	customTitle: string;
	note: string;
	tagsInput: string;
	space: string;
	useCustomSpace: boolean;
	newSpace: string;
}

interface InspirationLibraryItem {
	id: string;
	entityType?: ResourceEntityType;
	sourceTrace?: ResourceSourceTrace;
	title: string;
	imageSrc: string;
	fallbackImageSrc: string;
	desc: string;
	category: string;
	tags: string[];
	source: 'market' | 'upload';
	sourceLabel: string;
	resourceId?: string;
	imageId?: string;
	itemType?: 'image' | 'anchor' | 'insight';
	resourceTitle?: string;
	imageName?: string;
	anchorId?: string;
	anchorType?: ResourceAnchorType;
	anchorSummary?: string;
	anchorMode?: ResourceAnchorMode;
	evidenceLevel?: ResourceEvidenceLevel;
	insightId?: string;
	insightType?: ResourceInsightType;
	insightTitle?: string;
	insightSummary?: string;
	anchorX?: number;
	anchorY?: number;
	anchorOrigin?: AnchorOrigin;
	addedAt: string;
}

interface InspirationLibraryDraft {
	id?: string;
	entityType?: ResourceEntityType;
	sourceTrace?: ResourceSourceTrace;
	title: string;
	imageSrc: string;
	fallbackImageSrc: string;
	desc: string;
	category: string;
	tagsInput: string;
	source: 'market' | 'upload';
	sourceLabel: string;
	resourceId?: string;
	imageId?: string;
	itemType?: 'image' | 'anchor' | 'insight';
	resourceTitle?: string;
	imageName?: string;
	anchorId?: string;
	anchorType?: ResourceAnchorType;
	anchorSummary?: string;
	anchorMode?: ResourceAnchorMode;
	evidenceLevel?: ResourceEvidenceLevel;
	insightId?: string;
	insightType?: ResourceInsightType;
	insightTitle?: string;
	insightSummary?: string;
	anchorX?: number;
	anchorY?: number;
	anchorOrigin?: AnchorOrigin;
}

interface DetailDiscussionEntry {
	id: string;
	author: string;
	date: string;
	content: string;
	replyLabel?: string;
	avatarTone: string;
}

type BoardSourceTab = 'radar' | 'inspiration' | 'history' | 'generated';
type BoardDeepBrowseTab = Exclude<BoardSourceTab, 'generated'>;
type BoardLibraryNavKey =
	| 'soft'
	| 'furniture'
	| 'kitchen'
	| 'bath'
	| 'lighting'
	| 'decor'
	| 'storage'
	| 'smart'
	| 'outdoor'
	| 'plants'
	| 'materials'
	| 'scene';
interface BoardLibraryNavChild {
	label: string;
	keywords: string[];
}
interface BoardLibraryNavItem {
	key: BoardLibraryNavKey;
	label: string;
	keywords: string[];
	children: BoardLibraryNavChild[];
}
type BoardCanvasSourceType = 'radar' | 'inspiration' | 'history' | 'generated';
type BoardGeneratedStatus = 'generated' | 'shortlisted' | 'collaged' | 'adopted' | 'archived';
type BoardGeneratedRoundFilter = '本轮' | '最近' | '全部';
type InspirationEntityView = '全部条目' | '项目包' | '单图' | '锚点' | '解读';
type BoardVisualBriefStatus = 'auto' | 'edited' | 'locked' | 'stale';
type BoardReferenceKind = 'project_pack' | 'scene_card' | 'detail_card' | 'relation_card';
type BoardReferenceScope = 'global' | 'scene' | 'detail' | 'relation';
type BoardReferenceWeight = 'low' | 'medium' | 'high';
type PlanFeatureKind = 'entrance' | 'circulation' | 'view' | 'fixed' | 'flexible';
type PlanAnnotationKind = PlanFeatureKind | 'forbidden';

interface BoardReferenceControl {
	kind: BoardReferenceKind;
	scope: BoardReferenceScope;
	label: string;
	primaryRole: string;
	secondaryRole?: string;
	mustHave: string[];
	negative: string[];
	bindTo?: string;
	relationshipLogic?: string;
	weight: BoardReferenceWeight;
	structuredSummary: string;
}

export interface BoardVisualBrief {
	space: Exclude<BoardCanvasSpace, '全部'>;
	status: BoardVisualBriefStatus;
	summary: string;
	designIntent: string;
	visualPrompt: string;
	mustKeep: string[];
	styleKeywords: string[];
	materialKeywords: string[];
	lightingKeywords: string[];
	negativeConstraints: string[];
	sourceRefs: Array<{
		title: string;
		section: string;
		status: FileStatus;
		excerpt: string;
	}>;
	disabledTags: string[];
	lockedTags: string[];
	customNote: string;
	lastCompiledAt: string;
}

interface PlanFeature {
	id: string;
	label: string;
	kind: PlanFeatureKind;
	x: number;
	y: number;
	w?: number;
	h?: number;
	description: string;
}

interface PlanAnnotation {
	id: string;
	label: string;
	kind: PlanAnnotationKind;
	x: number;
	y: number;
	createdAt: string;
}

type FloorPlanReconstructionStatus = 'raw' | 'normalized' | 'traced' | 'zoned' | 'aligned' | 'height_ready';
type FloorPlanObjectType = 'wall' | 'door' | 'window' | 'column' | 'fixed_furniture' | 'loose_furniture' | 'north_arrow';
type FloorPlanElementKind = 'analysis_region' | 'space_boundary' | 'function_zone' | 'wall_trace' | 'door' | 'window' | 'height_marker';
type FloorPlanGeometryType = 'rect' | 'polygon' | 'path';
type FloorPlanPoint = { x: number; y: number };

interface FloorPlanElement {
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
}

interface FloorPlanReconstruction {
	status: FloorPlanReconstructionStatus;
	irVersion: string;
	sourceFormat: SpacePlanTopicState['sourceType'];
	coordinateSystem: {
		unit: 'mm' | 'm' | 'px';
		scaleStatus: 'uncalibrated' | 'estimated' | 'confirmed';
		northStatus: 'missing' | 'detected' | 'confirmed';
	};
	objectCounts: Record<FloorPlanObjectType, number>;
	spaceBoundaryCount: number;
	functionZoneCount: number;
	alignment: {
		matchedSpace: Exclude<BoardCanvasSpace, '全部'>;
		confidence: number;
		status: 'candidate' | 'confirmed' | 'conflict';
	};
	heightProfile: {
		ceilingHeight?: number;
		beamBottomHeight?: number;
		doorHeight?: number;
		windowSillHeight?: number;
		status: 'missing' | 'estimated' | 'confirmed';
	};
	scaleCalibration?: {
		mmPerPixel?: number;
		source: 'pdf_text' | 'fallback' | 'manual';
		samples: number;
	};
	elements: FloorPlanElement[];
	pendingIssues: string[];
	updatedAt: string;
}

interface SpacePlanView {
	space: Exclude<BoardCanvasSpace, '全部'>;
	floorId: string;
	spgVersion: string;
	irVersion: string;
	status: 'auto' | 'edited' | 'locked' | 'stale' | 'missing';
	overallPlanRef: {
		title: string;
		highlightZoneIds: string[];
		adjacentZoneIds: string[];
	};
	detailPlanRef: {
		title: string;
		zoneIds: string[];
		moduleIds: string[];
	};
	planBrief: {
		spatialRole: string;
		adjacency: string[];
		entrances: string[];
		mainCirculation: string[];
		viewDirection: string[];
		fixedConstraints: string[];
		flexibleZones: string[];
		cameraSuggestions: string[];
		negativeConstraints: string[];
	};
	features: PlanFeature[];
}

interface SpacePlanTopicState {
	space: Exclude<BoardCanvasSpace, '全部'>;
	status: 'missing' | 'uploaded' | 'parsed' | 'bound' | 'synced' | 'stale';
	sourceType: 'cad' | 'dxf' | 'pdf' | 'image' | 'manual';
	uploadedFileName?: string;
	uploadedFileUrl?: string;
	uploadedFileSize?: number;
	mimeType?: string;
	parseMessage?: string;
	parsedLayers?: string[];
	parsedEntityCounts?: Record<string, number>;
	annotations?: PlanAnnotation[];
	reconstruction?: FloorPlanReconstruction;
	updatedAt?: string;
	viewChain: Array<'project' | 'building' | 'floor' | 'space' | 'module'>;
}

interface BoardCanvasItem {
	id: string;
	sourceType: BoardCanvasSourceType;
	sourceId: string;
	entityType?: ResourceEntityType;
	sourceTrace?: ResourceSourceTrace;
	referenceControl?: BoardReferenceControl;
	anchorIds?: string[];
	anchorX?: number;
	anchorY?: number;
	anchorSummary?: string;
	title: string;
	imageSrc: string;
	fallbackImageSrc: string;
	desc?: string;
	meta?: string;
	x: number;
	y: number;
	width: number;
	aspectRatio?: number;
	disabled?: boolean;
	addedAt: string;
}

interface BoardSourceItem {
	id: string;
	sourceType: BoardCanvasSourceType;
	sourceId: string;
	entityType?: ResourceEntityType;
	sourceTrace?: ResourceSourceTrace;
	referenceControl?: BoardReferenceControl;
	anchorIds?: string[];
	anchorX?: number;
	anchorY?: number;
	anchorSummary?: string;
	title: string;
	imageSrc: string;
	fallbackImageSrc: string;
	desc: string;
	meta: string;
	generation?: {
		status: BoardGeneratedStatus;
		round: number;
		createdAt: string;
		promptSummary: string;
		sourceContext: string;
		space: Exclude<BoardCanvasSpace, '全部'>;
		topicScope: BoardCanvasMode;
		expertName: string;
	};
}

interface BoardGeneratedItem {
	id: string;
	sessionId: string;
	space: Exclude<BoardCanvasSpace, '全部'>;
	topicScope: BoardCanvasMode;
	generationRound: number;
	createdAt: string;
	promptSummary: string;
	sourceContext: string;
	status: BoardGeneratedStatus;
	title: string;
	imageSrc: string;
	fallbackImageSrc: string;
	expertName: string;
	sourceImageId?: string;
}

type BoardResizeHandle = 'nw' | 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w';

type BoardCanvasInteraction =
	| {
			mode: 'pan';
			startClientX: number;
			startClientY: number;
			startX: number;
			startY: number;
	  }
	| {
			mode: 'move-item';
			itemId: string;
			offsetX: number;
			offsetY: number;
	  }
	| {
			mode: 'resize-item';
			itemId: string;
			handle: BoardResizeHandle;
			anchorX: number;
			anchorY: number;
	  };

type ResourceTaskKey = '替代优先' | '空间搭配' | '预算压缩' | '缺失补全';

const FLOW_ORDER: FlowCategory[] = ['项目锚点', '外部认知', '决策约束', '空间策略', '表达系统', '评审定版'];
const SPACE_ORDER: ProjectFileCard['spaceScope'][] = ['全局', '大堂', '餐厅', '客房', '公区', '连廊', '后勤'];
const SPACE_VIEW_ORDER: Exclude<ProjectFileCard['spaceScope'], '全局'>[] = ['大堂', '餐厅', '客房', '公区', '连廊', '后勤'];
const ASSET_CATEGORY_OPTIONS: string[] = ['全部分类', '家具', '灯光', '材料', '工艺', '配色', '参考'];
const ASSET_SPACE_OPTIONS: string[] = ['全部空间', '全局', '大堂', '餐厅', '客房', '公区', '连廊', '后勤'];
const ASSET_BUDGET_OPTIONS: string[] = ['全部预算', '经济型', '均衡型', '高配型'];
const ALL_FLOW = '全部流程';
const ALL_SPACE = '全部空间';
const ALL_STAGE = '全部阶段';
const ALL_STATUS = '全部状态';
const ALL_ANCHOR = '全部锚点';
const ALL_TOPIC = '全部专题';
const BOARD_DEEP_BROWSE_TABS: Array<{ key: BoardDeepBrowseTab; label: string; desc: string }> = [
	{ key: 'radar', label: '资源雷达', desc: '从资源库里连续浏览可加入画布的素材。' },
	{ key: 'inspiration', label: '灵感收藏', desc: '查看已收藏的图片、锚点和解读。' },
	{ key: 'history', label: '历史项目素材', desc: '复用历史项目沉淀出的方案素材。' },
];
const ALL_BOARD_LIBRARY_SUBCATEGORY = '全部';
const BOARD_LIBRARY_NAV_ITEMS: BoardLibraryNavItem[] = [
	{
		key: 'soft',
		label: '窗帘和软帘',
		keywords: ['窗帘', '软帘', '软装', '布艺', '纺织', '地毯', '织物'],
		children: [
			{ label: '窗帘', keywords: ['窗帘', '软帘', '遮光'] },
			{ label: '地毯', keywords: ['地毯', '织物', '毯'] },
			{ label: '布艺', keywords: ['布艺', '纺织', '软装'] },
			{ label: '靠包', keywords: ['靠包', '抱枕', '坐垫'] },
		],
	},
	{
		key: 'furniture',
		label: '家具和陈设',
		keywords: ['家具', '陈设', '沙发', '椅', '桌', '柜', '床', '茶几'],
		children: [
			{ label: '沙发', keywords: ['沙发', '座椅', '休闲椅'] },
			{ label: '桌几', keywords: ['桌', '茶几', '餐桌', '边几'] },
			{ label: '柜体', keywords: ['柜', '收纳柜', '木作'] },
			{ label: '床榻', keywords: ['床', '榻', '卧室'] },
		],
	},
	{
		key: 'kitchen',
		label: '整体厨房和电器',
		keywords: ['厨房', '橱柜', '电器', '吧台', '台面', '餐厨'],
		children: [
			{ label: '橱柜', keywords: ['橱柜', '厨房柜', '收纳'] },
			{ label: '台面', keywords: ['台面', '石材', '水槽'] },
			{ label: '电器', keywords: ['电器', '冰箱', '烤箱', '灶'] },
			{ label: '吧台', keywords: ['吧台', '餐厨', '高脚椅'] },
		],
	},
	{
		key: 'bath',
		label: '浴室家具和家居',
		keywords: ['浴室', '卫浴', '洗手台', '洁具', '五金', '水龙头'],
		children: [
			{ label: '洗手台', keywords: ['洗手台', '台盆', '水槽'] },
			{ label: '卫浴柜', keywords: ['浴室柜', '卫浴柜', '收纳'] },
			{ label: '镜柜', keywords: ['镜柜', '镜子', '浴镜'] },
			{ label: '五金', keywords: ['五金', '水龙头', '花洒'] },
		],
	},
	{
		key: 'lighting',
		label: '灯具照明',
		keywords: ['灯光', '灯具', '照明', '吊灯', '壁灯', '灯带', '光'],
		children: [
			{ label: '吊灯', keywords: ['吊灯', '悬挂灯'] },
			{ label: '壁灯', keywords: ['壁灯', '墙灯'] },
			{ label: '灯带', keywords: ['灯带', '线性灯'] },
			{ label: '氛围光', keywords: ['氛围', '光影', '间接照明'] },
		],
	},
	{
		key: 'decor',
		label: '装饰品',
		keywords: ['装饰', '摆件', '花瓶', '画框', '镜子', '香氛', '艺术'],
		children: [
			{ label: '花瓶和装饰盘', keywords: ['花瓶', '装饰盘', '器皿'] },
			{ label: '图片和框架', keywords: ['画框', '图片', '挂画'] },
			{ label: '镜子', keywords: ['镜子', '镜面'] },
			{ label: '香氛', keywords: ['香氛', '香薰'] },
		],
	},
	{
		key: 'storage',
		label: '清洁及收纳用品',
		keywords: ['清洁', '收纳', '储物', '整理', '篮', '盒'],
		children: [
			{ label: '储物篮', keywords: ['篮', '储物篮', '收纳篮'] },
			{ label: '收纳盒', keywords: ['盒', '收纳盒', '整理盒'] },
			{ label: '墙面收纳', keywords: ['墙面收纳', '挂架', '层架'] },
			{ label: '清洁用品', keywords: ['清洁', '清扫'] },
		],
	},
	{
		key: 'smart',
		label: '智能家居',
		keywords: ['智能', '控制', '设备', '传感', '系统'],
		children: [
			{ label: '智能照明', keywords: ['智能照明', '灯光控制'] },
			{ label: '控制面板', keywords: ['控制面板', '开关', '系统'] },
			{ label: '传感设备', keywords: ['传感', '感应'] },
			{ label: '影音设备', keywords: ['影音', '音响', '投影'] },
		],
	},
	{
		key: 'outdoor',
		label: '户外产品',
		keywords: ['户外', '庭院', '露台', '阳台', '景观', '花园'],
		children: [
			{ label: '庭院家具', keywords: ['庭院家具', '户外家具'] },
			{ label: '露台', keywords: ['露台', '阳台'] },
			{ label: '景观灯', keywords: ['景观灯', '户外灯'] },
			{ label: '遮阳', keywords: ['遮阳', '廊架'] },
		],
	},
	{
		key: 'plants',
		label: '花盆和植物',
		keywords: ['植物', '绿植', '花盆', '花艺', '盆栽'],
		children: [
			{ label: '植物和花', keywords: ['植物', '绿植', '花'] },
			{ label: '花盆', keywords: ['花盆', '盆栽'] },
			{ label: '花艺', keywords: ['花艺', '插花'] },
			{ label: '景观植物', keywords: ['景观植物', '庭院植物'] },
		],
	},
	{
		key: 'materials',
		label: '材料和工艺',
		keywords: ['材料', '工艺', '木作', '石材', '金属', '玻璃', '收口', '饰面'],
		children: [
			{ label: '木作', keywords: ['木作', '木饰面', '木色'] },
			{ label: '石材', keywords: ['石材', '岩板', '水磨石'] },
			{ label: '金属', keywords: ['金属', '不锈钢', '铜'] },
			{ label: '收口工艺', keywords: ['收口', '节点', '工艺'] },
		],
	},
	{
		key: 'scene',
		label: '空间场景',
		keywords: ['场景', '空间', '大堂', '餐厅', '客房', '公区', '连廊', '参考'],
		children: [
			{ label: '大堂', keywords: ['大堂', '入口', '接待'] },
			{ label: '餐厅', keywords: ['餐厅', '餐饮'] },
			{ label: '客房', keywords: ['客房', '卧室'] },
			{ label: '公区', keywords: ['公区', '公共区', '社交'] },
		],
	},
];
const getBoardLibrarySearchText = (item: BoardSourceItem) =>
	[
		item.title,
		item.desc,
		item.meta,
		item.anchorSummary,
		item.referenceControl?.label,
		item.referenceControl?.scope,
		item.referenceControl?.structuredSummary,
		item.referenceControl?.mustHave.join(' '),
		item.referenceControl?.negative.join(' '),
	].filter(Boolean).join(' ').toLowerCase();
const boardLibraryItemMatchesKeywords = (item: BoardSourceItem, keywords: string[]) => {
	if (keywords.length === 0) return true;
	const text = getBoardLibrarySearchText(item);
	return keywords.some((keyword) => text.includes(keyword.toLowerCase()));
};
const VIEW_MODES: FileViewMode[] = ['统一视图', '思维参谋'];
const FILE_VIEW_PREFS_KEY = 'ipa.files.view.prefs.v1';
const INSPIRATION_LIBRARY_STORAGE_KEY = 'ipa.inspiration.library.v1';
const PERSONAL_KNOWLEDGE_STORAGE_KEY = 'ipa.dss.knowledge.v2';
const PERSONAL_KNOWLEDGE_LEGACY_KEY = 'ipa.knowledge.private.v1';
const PERSONAL_KNOWLEDGE_DEMO_VERSION_KEY = 'ipa.dss.knowledge.demo-version';
const PERSONAL_KNOWLEDGE_DEMO_VERSION = 'v3-14-dss';
const DSS_PROFILE_STORAGE_KEY = 'ipa.dss.profile.v1';
const RESOURCE_ANCHOR_STORAGE_KEY = 'ipa.resource.anchors.v1';
const BOARD_CANVAS_STORAGE_KEY = 'ipa.board.canvas.v2';
const BOARD_CANVAS_VIEW_STORAGE_KEY = 'ipa.board.canvas.view.v2';
const BOARD_GENERATION_BELT_STORAGE_KEY = 'ipa.board.generated-belt.v1';
const BOARD_VISUAL_BRIEF_STORAGE_KEY = 'ipa.board.visual-brief.v1';
const SPACE_PLAN_TOPIC_STORAGE_KEY = 'ipa.space.plan-topic.v1';
const COLLECTION_SPACE_OPTIONS: string[] = [...SPACE_ORDER];
const DEFAULT_BOARD_ITEM_ASPECT_RATIO = 1 / 0.72;
const MIN_BOARD_ITEM_WIDTH = 160;
const BOARD_RESIZE_HANDLES: BoardResizeHandle[] = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'];
const BOARD_CANVAS_SPACE_OPTIONS: BoardCanvasSpace[] = ['全部', ...SPACE_VIEW_ORDER];
const BOARD_CANVAS_MODES: BoardCanvasMode[] = ['综合', '色彩', '材料', '家具', '氛围', '反例'];
const DEFAULT_BOARD_CANVAS_VIEW = { x: 180, y: 110, zoom: 1 };
const BOARD_GENERATION_EVENT = 'cockpit:board-generated-image';
const MAX_BOARD_CANVAS_HISTORY_STEPS = 5;
const KNOWLEDGE_ENTRY_TYPES: KnowledgeEntryType[] = ['待分类', '习惯', '经验', '方法', '模板', '禁忌', '案例复盘'];
const KNOWLEDGE_ENTRY_STATUS: KnowledgeEntryStatus[] = ['草稿', '已整理', '已验证', '可复用'];

const PORTFOLIO_SPACE_TYPES = ['民宿', '酒店', '办公', '商业', '展陈', '餐饮', '住宅', '文旅'] as const;
type PortfolioSpaceType = typeof PORTFOLIO_SPACE_TYPES[number];
const PORTFOLIO_DEMO_HIDDEN_SPACE_TYPES: PortfolioSpaceType[] = ['餐饮', '展陈'];

const PORTFOLIO_SPACE_COLORS: Record<PortfolioSpaceType, string> = {
	'民宿': '#4e9af1',
	'酒店': '#7c6af7',
	'办公': '#f59e0b',
	'商业': '#ef4444',
	'展陈': '#10b981',
	'餐饮': '#f97316',
	'住宅': '#06b6d4',
	'文旅': '#84cc16',
};
type PortfolioBubbleSizeMode = 'fee' | 'feePerArea';

const createInitialKnowledgeEntries = (): PersonalKnowledgeEntry[] => {
	const now = new Date().toISOString();
	const entries: PersonalKnowledgeEntry[] = [
		{
			id: 'knowledge-demo-01',
			title: '项目启动默认检查顺序',
			type: '方法',
			status: '已整理',
			summary: '先锁终局目标与约束，再进入风格和视觉表达。',
			content: '终局目标、预算边界、工期边界、运营边界四项先锁定，再做概念推导。',
			tags: ['启动', '方法', '约束优先'],
			sourceContext: '我的硅基分身 Demo',
			updatedAt: now,
		},
		{
			id: 'knowledge-demo-02',
			title: '民宿酒店类项目常见风险提醒',
			type: '经验',
			status: '草稿',
			summary: '后勤流线与维护周期常被忽略，前期需先预警。',
			content: '需提前做材料替代表和维护周期规划，不要在后期才修补。',
			tags: ['风险', '项目类型', '后勤流线'],
			sourceContext: '我的硅基分身 Demo',
			updatedAt: now,
		},
		{
			id: 'knowledge-demo-03',
			title: '客房动线压缩模板',
			type: '模板',
			status: '已整理',
			summary: '单廊双向冲突时，优先重排清扫与布草回收的时段。',
			content: '把高峰入住、清扫、补给拆为三段，先排冲突时间，再排空间节点。',
			tags: ['客房', '动线', '运营'],
			sourceContext: '我的硅基分身 Demo',
			updatedAt: now,
		},
		{
			id: 'knowledge-demo-04',
			title: '大堂首屏氛围校准法',
			type: '方法',
			status: '已整理',
			summary: '先定照度对比，再定材质反射，最后补充软装饱和度。',
			content: '首屏不看单件，先看光比、反射、色块分布，再看局部陈设。',
			tags: ['大堂', '灯光', '氛围'],
			sourceContext: '我的硅基分身 Demo',
			updatedAt: now,
		},
		{
			id: 'knowledge-demo-05',
			title: '预算超支预警阈值',
			type: '习惯',
			status: '已整理',
			summary: '主材+机电累计超过 62% 时，必须触发替代方案会。',
			content: '每周滚动预算盘点时，对高波动项做 A/B 备选和冻结条件。',
			tags: ['预算', '预警', '替代'],
			sourceContext: '我的硅基分身 Demo',
			updatedAt: now,
		},
		{
			id: 'knowledge-demo-06',
			title: '餐厅噪声管理清单',
			type: '模板',
			status: '草稿',
			summary: '硬反射面超过 55% 时，先补顶面与软装吸声。',
			content: '对话区优先优化背景噪声，再处理局部设备声和回声。',
			tags: ['餐厅', '声学', '体验'],
			sourceContext: '我的硅基分身 Demo',
			updatedAt: now,
		},
		{
			id: 'knowledge-demo-07',
			title: '材料替代三步法',
			type: '方法',
			status: '已整理',
			summary: '性能对齐、触感对齐、维护对齐，三项都过才替代。',
			content: '不要只看单价，必须把维护成本和可得性放进总成本。',
			tags: ['材料', '替代', '成本'],
			sourceContext: '我的硅基分身 Demo',
			updatedAt: now,
		},
		{
			id: 'knowledge-demo-08',
			title: '样板间验收拍照位',
			type: '经验',
			status: '已整理',
			summary: '固定 6 个机位复拍，才能客观比较迭代前后变化。',
			content: '机位固定后，才有可比较的证据链，避免主观争议。',
			tags: ['验收', '样板间', '证据'],
			sourceContext: '我的硅基分身 Demo',
			updatedAt: now,
		},
		{
			id: 'knowledge-demo-09',
			title: '施工交底禁区词',
			type: '习惯',
			status: '草稿',
			summary: '避免“差不多”“看现场再说”这类不可执行表达。',
			content: '所有要求都要有尺寸、材料、节点和验收口径。',
			tags: ['施工', '交底', '标准化'],
			sourceContext: '我的硅基分身 Demo',
			updatedAt: now,
		},
		{
			id: 'knowledge-demo-10',
			title: '夜间场景灯光回路模板',
			type: '模板',
			status: '已整理',
			summary: '迎宾、运营、清洁三组回路必须独立，避免互相牵制。',
			content: '灯光回路与运营场景绑定后，切换效率和能耗更可控。',
			tags: ['灯光', '夜景', '运营'],
			sourceContext: '我的硅基分身 Demo',
			updatedAt: now,
		},
		{
			id: 'knowledge-demo-11',
			title: '公区导视一致性检查',
			type: '方法',
			status: '已整理',
			summary: '文案口吻、箭头逻辑、层级色彩必须一次性校准。',
			content: '导视不是后置贴标，需与动线节点同步设计。',
			tags: ['导视', '公区', '一致性'],
			sourceContext: '我的硅基分身 Demo',
			updatedAt: now,
		},
		{
			id: 'knowledge-demo-12',
			title: '复盘会议输出模板',
			type: '模板',
			status: '草稿',
			summary: '结论、证据、行动人、截止时间四栏缺一不可。',
			content: '复盘不做情绪总结，必须落到可验证的改进项。',
			tags: ['复盘', '模板', '执行'],
			sourceContext: '我的硅基分身 Demo',
			updatedAt: now,
		},
		{
			id: 'knowledge-demo-13',
			title: '绝对不做无终局方案',
			type: '禁忌',
			status: '已整理',
			summary: '方案必须先定义终局目标，否则不启动概念推导。',
			content: '没有终局定义的项目会在风格讨论中无限发散，消耗团队信任和预算。任何项目开始前必须回答"做成了是什么样"。',
			tags: ['终局', '禁忌', '方案启动'],
			sourceContext: '我的硅基分身 Demo',
			updatedAt: now,
		},
		{
			id: 'knowledge-demo-14',
			title: '某民宿动线复盘',
			type: '案例复盘',
			status: '草稿',
			summary: '后勤动线与住客动线交叉导致清洁效率下降 40%。',
			content: '项目交付后运营 3 个月发现：因后勤通道与客房走廊共用一段，清扫车与住客在 8:00-10:00 高频交叉。教训：后勤流线必须在平面阶段独立验证，不能只看"能走通"。',
			tags: ['动线', '复盘', '民宿', '后勤'],
			sourceContext: '我的硅基分身 Demo',
			updatedAt: now,
		},
		// ── 作品索引 Demo ──
		// ── 2019 ──
		{ id: 'pf-01', title: '莫干山隐溪民宿', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2019, month: 3, spaceType: '民宿', designFee: 38, designArea: 1200 } },
		{ id: 'pf-02', title: '安吉竹林山居', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2019, month: 3, spaceType: '民宿', designFee: 25, designArea: 800 } },
		{ id: 'pf-03', title: '北京望京餐厅', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2019, month: 5, spaceType: '餐饮', designFee: 32, designArea: 600 } },
		{ id: 'pf-04', title: '上海某创意办公', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2019, month: 11, spaceType: '办公', designFee: 0, designArea: 900 } },
		// ── 2020 ──
		{ id: 'pf-05', title: '成都麓湖精品酒店', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2020, month: 2, spaceType: '酒店', designFee: 120, designArea: 6800 } },
		{ id: 'pf-06', title: '三亚海棠湾酒店', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2020, month: 2, spaceType: '酒店', designFee: 85, designArea: 4200 } },
		{ id: 'pf-07', title: '北京某律所办公', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2020, month: 5, spaceType: '办公', designFee: 55, designArea: 1200 } },
		{ id: 'pf-08', title: '深圳南山联合办公', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2020, month: 9, spaceType: '办公', designFee: 78, designArea: 2200 } },
		{ id: 'pf-09', title: '广州天河办公楼', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2020, month: 9, spaceType: '办公', designFee: 42, designArea: 1500 } },
		{ id: 'pf-10', title: '大理洱海民宿', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2020, month: 12, spaceType: '住宅', designFee: 29, designArea: 750 } },
		// ── 2021 ──
		{ id: 'pf-11', title: '上海静安嘉里餐厅', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2021, month: 4, spaceType: '餐饮', designFee: 68, designArea: 800 } },
		{ id: 'pf-12', title: '成都宽窄巷餐厅', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2021, month: 4, spaceType: '餐饮', designFee: 45, designArea: 550 } },
		{ id: 'pf-13', title: '杭州西湖边茶餐厅', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2021, month: 4, spaceType: '餐饮', designFee: 0, designArea: 400 } },
		{ id: 'pf-14', title: '大理古城品牌民宿', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2021, month: 7, spaceType: '住宅', designFee: 42, designArea: 980 } },
		{ id: 'pf-15', title: '丽江束河民宿', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2021, month: 8, spaceType: '住宅', designFee: 35, designArea: 860 } },
		{ id: 'pf-16', title: '深圳科技园总部', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2021, month: 9, spaceType: '办公', designFee: 210, designArea: 3000 } },
		{ id: 'pf-17', title: '北京金融街办公', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2021, month: 10, spaceType: '办公', designFee: 135, designArea: 1800 } },
		// ── 2022 ──
		{ id: 'pf-18', title: '杭州西溪文旅综合体', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2022, month: 1, spaceType: '文旅', designFee: 380, designArea: 8000 } },
		{ id: 'pf-19', title: '三亚亚特兰蒂斯翻新', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2022, month: 3, spaceType: '酒店', designFee: 195, designArea: 560 } },
		{ id: 'pf-20', title: '上海外滩精品酒店', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2022, month: 6, spaceType: '酒店', designFee: 260, designArea: 3200 } },
		{ id: 'pf-21', title: '成都IFS展陈', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2022, month: 6, spaceType: '展陈', designFee: 88, designArea: 380 } },
		{ id: 'pf-22', title: '深圳设计周展览', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2022, month: 9, spaceType: '展陈', designFee: 52, designArea: 220 } },
		{ id: 'pf-23', title: '上海浦东豪宅精装', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2022, month: 9, spaceType: '住宅', designFee: 145, designArea: 680 } },
		{ id: 'pf-24', title: '北京顺义别墅全案', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2022, month: 11, spaceType: '住宅', designFee: 98, designArea: 520 } },
		{ id: 'pf-25', title: '广州天河商业餐饮区', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2022, month: 7, spaceType: '餐饮', designFee: 175, designArea: 2800 } },
		{ id: 'pf-26', title: '成都太古里餐厅', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2022, month: 11, spaceType: '餐饮', designFee: 92, designArea: 1100 } },
		{ id: 'pf-27', title: '苏州园区科技办公', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2022, month: 7, spaceType: '办公', designFee: 0, designArea: 2400 } },
		// ── 2023 ──
		{ id: 'pf-28', title: '西藏林芝民宿集群', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2023, month: 2, spaceType: '住宅', designFee: 95, designArea: 2800 } },
		{ id: 'pf-29', title: '云南泸沽湖民宿', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2023, month: 5, spaceType: '住宅', designFee: 72, designArea: 1800 } },
		{ id: 'pf-30', title: '贵州山地民宿', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2023, month: 5, spaceType: '住宅', designFee: 48, designArea: 1100 } },
		{ id: 'pf-31', title: '北京798展馆', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2023, month: 3, spaceType: '展陈', designFee: 128, designArea: 1600 } },
		{ id: 'pf-32', title: '上海当代艺术中心', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2023, month: 9, spaceType: '展陈', designFee: 185, designArea: 2400 } },
		{ id: 'pf-33', title: '广州天河餐饮区', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2023, month: 4, spaceType: '餐饮', designFee: 260, designArea: 4200 } },
		{ id: 'pf-34', title: '深圳南头古城餐厅', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2023, month: 8, spaceType: '餐饮', designFee: 55, designArea: 650 } },
		{ id: 'pf-35', title: '上海徐汇商业体', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2023, month: 6, spaceType: '商业', designFee: 320, designArea: 5500 } },
		{ id: 'pf-36', title: '杭州滨江办公园区', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2023, month: 4, spaceType: '办公', designFee: 188, designArea: 4000 } },
		{ id: 'pf-37', title: '成都天府新区办公', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2023, month: 10, spaceType: '办公', designFee: 142, designArea: 2600 } },
		{ id: 'pf-38', title: '北京朝阳联合办公', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2023, month: 10, spaceType: '办公', designFee: 0, designArea: 1800 } },
		// ── 2024 ──
		{ id: 'pf-39', title: '苏州太湖高端民宿', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2024, month: 4, spaceType: '民宿', designFee: 165, designArea: 3200 } },
		{ id: 'pf-40', title: '杭州余杭民宿', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2024, month: 9, spaceType: '住宅', designFee: 88, designArea: 1600 } },
		{ id: 'pf-41', title: '上海陆家嘴金融办公', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2024, month: 2, spaceType: '办公', designFee: 320, designArea: 1800 } },
		{ id: 'pf-42', title: '北京中关村科技园', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2024, month: 5, spaceType: '办公', designFee: 245, designArea: 3500 } },
		{ id: 'pf-43', title: '深圳前海总部基地', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2024, month: 5, spaceType: '办公', designFee: 198, designArea: 2800 } },
		{ id: 'pf-44', title: '云南香格里拉文旅中心', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2024, month: 3, spaceType: '办公', designFee: 420, designArea: 5500 } },
		{ id: 'pf-45', title: '广州南沙文旅小镇', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2024, month: 11, spaceType: '办公', designFee: 285, designArea: 6200 } },
		{ id: 'pf-46', title: '上海新天地餐厅', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2024, month: 1, spaceType: '餐饮', designFee: 115, designArea: 1200 } },
		{ id: 'pf-47', title: '北京三里屯餐厅', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2024, month: 8, spaceType: '餐饮', designFee: 88, designArea: 900 } },
		{ id: 'pf-48', title: '成都东村餐厅', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2024, month: 11, spaceType: '餐饮', designFee: 0, designArea: 700 } },
		// ── 2025 ──
		{ id: 'pf-49', title: '上海徐汇餐厅A', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 1, spaceType: '餐饮', designFee: 92, designArea: 880 } },
		{ id: 'pf-50', title: '广州珠江餐厅', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 1, spaceType: '餐饮', designFee: 68, designArea: 720 } },
		{ id: 'pf-51', title: '北京望京办公A', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 1, spaceType: '办公', designFee: 175, designArea: 2200 } },
		{ id: 'pf-52', title: '深圳湾科技办公', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 1, spaceType: '办公', designFee: 145, designArea: 1800 } },
		{ id: 'pf-53', title: '丽江束河品牌民宿', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 1, spaceType: '住宅', designFee: 0, designArea: 1200 } },
		{ id: 'pf-54', title: '杭州余杭商业中心', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 3, spaceType: '商业', designFee: 460, designArea: 8800 } },
		{ id: 'pf-55', title: '成都高新区办公B', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 3, spaceType: '办公', designFee: 280, designArea: 3600 } },
		{ id: 'pf-56', title: '上海浦东办公C', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 3, spaceType: '办公', designFee: 220, designArea: 2800 } },
		{ id: 'pf-57', title: '北京朝阳办公D', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 3, spaceType: '办公', designFee: 0, designArea: 2100 } },
		{ id: 'pf-58', title: '武汉光谷展陈', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 3, spaceType: '展陈', designFee: 135, designArea: 1400 } },
		{ id: 'pf-59', title: '重庆两江餐厅B', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 3, spaceType: '餐饮', designFee: 78, designArea: 850 } },
		{ id: 'pf-60', title: '云南大理民宿A', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 5, spaceType: '住宅', designFee: 118, designArea: 2200 } },
		{ id: 'pf-61', title: '厦门鼓浪屿民宿', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 5, spaceType: '住宅', designFee: 88, designArea: 1600 } },
		{ id: 'pf-62', title: '青岛海边精品酒店', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 5, spaceType: '酒店', designFee: 340, designArea: 5800 } },
		{ id: 'pf-63', title: '贵州茅台文旅小镇', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 5, spaceType: '办公', designFee: 0, designArea: 7200 } },
		{ id: 'pf-64', title: '上海新天地商业B', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 7, spaceType: '商业', designFee: 520, designArea: 9500 } },
		{ id: 'pf-65', title: '深圳南山商业街', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 7, spaceType: '商业', designFee: 380, designArea: 6800 } },
		{ id: 'pf-66', title: '北京三里屯餐厅C', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 7, spaceType: '餐饮', designFee: 155, designArea: 1600 } },
		{ id: 'pf-67', title: '成都锦里餐厅D', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 7, spaceType: '餐饮', designFee: 110, designArea: 1200 } },
		{ id: 'pf-68', title: '杭州西溪住宅', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 7, spaceType: '住宅', designFee: 245, designArea: 1100 } },
		{ id: 'pf-69', title: '上海浦东住宅B', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 7, spaceType: '住宅', designFee: 0, designArea: 880 } },
		{ id: 'pf-70', title: '广州海珠展陈B', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 9, spaceType: '展陈', designFee: 195, designArea: 2800 } },
		{ id: 'pf-71', title: '北京798展馆B', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 9, spaceType: '展陈', designFee: 158, designArea: 2100 } },
		{ id: 'pf-72', title: '四川稻城文旅中心', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 9, spaceType: '办公', designFee: 580, designArea: 11000 } },
		{ id: 'pf-73', title: '西安大唐不夜城商业', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 11, spaceType: '商业', designFee: 420, designArea: 7500 } },
		{ id: 'pf-74', title: '苏州工业园办公E', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 11, spaceType: '办公', designFee: 265, designArea: 3200 } },
		{ id: 'pf-75', title: '南京河西民宿B', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2025, month: 11, spaceType: '住宅', designFee: 0, designArea: 1500 } },
		// ── 2026 ──
		{ id: 'pf-76', title: '北京国贸办公F', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 1, spaceType: '办公', designFee: 310, designArea: 4200 } },
		{ id: 'pf-77', title: '上海虹桥办公G', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 1, spaceType: '办公', designFee: 255, designArea: 3100 } },
		{ id: 'pf-78', title: '广州珠江新城餐厅E', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 1, spaceType: '餐饮', designFee: 125, designArea: 1300 } },
		{ id: 'pf-79', title: '深圳福田餐厅F', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 1, spaceType: '餐饮', designFee: 0, designArea: 980 } },
		{ id: 'pf-80', title: '武夷山隐居民宿', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 2, spaceType: '民宿', designFee: 195, designArea: 2800 } },
		{ id: 'pf-81', title: '海南清水湾文旅', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 2, spaceType: '文旅', designFee: 650, designArea: 12000 } },
		{ id: 'pf-82', title: '上海黄浦商业C', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 3, spaceType: '商业', designFee: 540, designArea: 9200 } },
		{ id: 'pf-83', title: '成都大源商业D', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 3, spaceType: '商业', designFee: 385, designArea: 6600 } },
		{ id: 'pf-84', title: '杭州未来科技城办公H', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 3, spaceType: '办公', designFee: 445, designArea: 5500 } },
		{ id: 'pf-85', title: '北京丰台办公I', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 3, spaceType: '办公', designFee: 320, designArea: 4100 } },
		{ id: 'pf-86', title: '深圳龙华办公J', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 3, spaceType: '办公', designFee: 0, designArea: 3200 } },
		{ id: 'pf-87', title: '莫干山新山居民宿', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 3, spaceType: '住宅', designFee: 225, designArea: 3500 } },
		{ id: 'pf-88', title: '北京798新展馆', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 4, spaceType: '展陈', designFee: 240, designArea: 3200 } },
		{ id: 'pf-89', title: '上海西岸餐厅G', type: '作品', status: '已整理', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 4, spaceType: '餐饮', designFee: 168, designArea: 1800 } },
		{ id: 'pf-90', title: '广州天河餐厅H', type: '作品', status: '草稿', summary: '', content: '', tags: [], updatedAt: now, portfolio: { year: 2026, month: 4, spaceType: '餐饮', designFee: 0, designArea: 1100 } },
	];

	// 将作品demo重排为“进入→发展→高峰→退出”的错峰轨迹，避免各空间齐头并进
	const lifecycleBySpace: Record<PortfolioSpaceType, Array<{ year: number; month: number; feeScale: number }>> = {
		办公: [
			{ year: 2019, month: 11, feeScale: 0.45 }, // 进入
			{ year: 2021, month: 9, feeScale: 0.75 }, // 发展
			{ year: 2023, month: 7, feeScale: 1.15 }, // 抬升
			{ year: 2024, month: 5, feeScale: 1.35 }, // 高峰
			{ year: 2025, month: 4, feeScale: 0.95 }, // 回落
			{ year: 2026, month: 3, feeScale: 0.60 }, // 退出
		],
		餐饮: [
			{ year: 2019, month: 8, feeScale: 0.40 },
			{ year: 2021, month: 6, feeScale: 0.75 },
			{ year: 2023, month: 5, feeScale: 1.25 },
			{ year: 2024, month: 4, feeScale: 1.35 },
			{ year: 2025, month: 3, feeScale: 0.95 },
			{ year: 2026, month: 2, feeScale: 0.65 },
		],
		民宿: [
			{ year: 2019, month: 10, feeScale: 0.55 },
			{ year: 2020, month: 8, feeScale: 0.85 },
			{ year: 2021, month: 6, feeScale: 1.35 },
			{ year: 2023, month: 4, feeScale: 0.70 },
		],
		展陈: [
			{ year: 2022, month: 10, feeScale: 0.60 },
			{ year: 2023, month: 8, feeScale: 0.90 },
			{ year: 2025, month: 6, feeScale: 1.30 },
			{ year: 2026, month: 5, feeScale: 0.80 },
		],
		商业: [
			{ year: 2023, month: 10, feeScale: 0.60 },
			{ year: 2024, month: 8, feeScale: 0.90 },
			{ year: 2025, month: 6, feeScale: 1.35 },
			{ year: 2026, month: 5, feeScale: 0.95 },
		],
		文旅: [
			{ year: 2023, month: 9, feeScale: 1.25 },
			{ year: 2026, month: 4, feeScale: 0.70 },
		],
		酒店: [
			{ year: 2020, month: 10, feeScale: 0.70 },
			{ year: 2021, month: 8, feeScale: 0.95 },
			{ year: 2022, month: 6, feeScale: 1.35 },
			{ year: 2023, month: 5, feeScale: 1.20 },
			{ year: 2025, month: 4, feeScale: 0.65 },
		],
		住宅: [
			{ year: 2020, month: 9, feeScale: 0.45 },
			{ year: 2022, month: 8, feeScale: 0.75 },
			{ year: 2024, month: 6, feeScale: 1.00 },
			{ year: 2025, month: 5, feeScale: 1.25 },
			{ year: 2026, month: 4, feeScale: 1.35 },
		],
	};

	const lifecycleDynamicsBySpace: Record<PortfolioSpaceType, { gamma: number; monthPattern: number[] }> = {
		办公: { gamma: 1.18, monthPattern: [0, 1, -1, 2, -2, 0, 1, -1] },
		餐饮: { gamma: 0.92, monthPattern: [0, -1, 1, -2, 2, 0, -1, 1] },
		民宿: { gamma: 0.85, monthPattern: [0, 1, 2, -1, 0, 1] },
		展陈: { gamma: 1.05, monthPattern: [0, -1, 1, 0, 2, -2] },
		商业: { gamma: 1.28, monthPattern: [0, 2, -1, 1, -2, 0] },
		文旅: { gamma: 1.45, monthPattern: [0, 1, -1, 0] },
		酒店: { gamma: 0.95, monthPattern: [0, -2, 1, -1, 2, 0] },
		住宅: { gamma: 1.35, monthPattern: [0, 1, -1, 2, 0, -2, 1] },
	};
	const portfolioBySpace = new Map<PortfolioSpaceType, PersonalKnowledgeEntry[]>();
	for (const entry of entries) {
		if (entry.type !== '作品' || !entry.portfolio) continue;
		const st = entry.portfolio.spaceType as PortfolioSpaceType;
		if (!portfolioBySpace.has(st)) portfolioBySpace.set(st, []);
		portfolioBySpace.get(st)!.push(entry);
	}

	portfolioBySpace.forEach((list, spaceType) => {
		const typedSpaceType = spaceType as PortfolioSpaceType;
		const phases = lifecycleBySpace[typedSpaceType] ?? [{ year: 2024, month: 6, feeScale: 1 }];
		const dynamics = lifecycleDynamicsBySpace[typedSpaceType] ?? { gamma: 1, monthPattern: [0] };
		const denominator = Math.max(1, list.length - 1);
		list
			.sort((a, b) => a.id.localeCompare(b.id, undefined, { numeric: true }))
			.forEach((entry, index) => {
				const progress = index / denominator;
				const curvedProgress = Math.pow(progress, dynamics.gamma);
				const phaseIndex = Math.round(curvedProgress * (phases.length - 1));
				const phase = phases[Math.min(phases.length - 1, Math.max(0, phaseIndex))];
				const jitter = dynamics.monthPattern[index % dynamics.monthPattern.length] ?? 0;
				const month = Math.max(1, Math.min(12, phase.month + jitter));

				const p = entry.portfolio!;
				const stageRatio = phases.length > 1 ? phaseIndex / (phases.length - 1) : 0;
				const stageWave = 1 + Math.sin(stageRatio * Math.PI) * 0.08;
				const scaledFee = p.designFee > 0 ? Math.max(8, Math.round(p.designFee * phase.feeScale * stageWave)) : 0;
				entry.portfolio = {
					...p,
					year: phase.year,
					month,
					designFee: scaledFee,
				};
			});
	});

	return entries;
};

const toDisplaySpaceName = (space: ProjectFileCard['spaceScope'] | string) => (space === '全局' ? '跨空间' : space);
const buildBoardCanvasStorageKey = (sessionId: string, space: Exclude<BoardCanvasSpace, '全部'>) =>
	`${BOARD_CANVAS_STORAGE_KEY}.${sessionId}.${space}`;
const buildBoardCanvasViewStorageKey = (sessionId: string, space: Exclude<BoardCanvasSpace, '全部'>) =>
	`${BOARD_CANVAS_VIEW_STORAGE_KEY}.${sessionId}.${space}`;
const buildBoardGenerationBeltStorageKey = (sessionId: string) => `${BOARD_GENERATION_BELT_STORAGE_KEY}.${sessionId}`;
const buildBoardVisualBriefStorageKey = (sessionId: string, space: Exclude<BoardCanvasSpace, '全部'>) =>
	`${BOARD_VISUAL_BRIEF_STORAGE_KEY}.${sessionId}.${space}`;
const buildSpacePlanTopicStorageKey = (sessionId: string) => `${SPACE_PLAN_TOPIC_STORAGE_KEY}.${sessionId}`;
const getBoardCanvasItemAspectRatio = (item: Pick<BoardCanvasItem, 'aspectRatio'>) =>
	item.aspectRatio && item.aspectRatio > 0 ? item.aspectRatio : DEFAULT_BOARD_ITEM_ASPECT_RATIO;
const getBoardCanvasItemHeight = (item: Pick<BoardCanvasItem, 'width' | 'aspectRatio'>) =>
	item.width / getBoardCanvasItemAspectRatio(item);
const RESOURCE_ANCHOR_POSITION_PRESETS: Array<Array<{ x: number; y: number }>> = [
	[
		{ x: 0.22, y: 0.24 },
		{ x: 0.74, y: 0.36 },
		{ x: 0.42, y: 0.78 },
	],
	[
		{ x: 0.28, y: 0.18 },
		{ x: 0.68, y: 0.48 },
		{ x: 0.56, y: 0.82 },
	],
	[
		{ x: 0.18, y: 0.34 },
		{ x: 0.62, y: 0.24 },
		{ x: 0.78, y: 0.74 },
	],
];

const buildResourceSourceTrace = (trace: ResourceSourceTrace): ResourceSourceTrace => trace;

const createAnchorInsights = (
	resource: Pick<ResourceItem, 'title' | 'space'>,
	blueprint: Pick<ResourceImageAnchor, 'title' | 'summary' | 'topic' | 'quotedReason'>,
	index: number
): ResourceAnchorInsight[] => [
	{
		id: `insight-observation-${index}`,
		type: 'observation',
		title: `${blueprint.title} · 观察`,
		summary: blueprint.summary,
		evidenceLevel: 'strong',
	},
	{
		id: `insight-action-${index}`,
		type: 'action',
		title: `${blueprint.title} · 执行动作`,
		summary: `建议优先把这条信息转成 ${toDisplaySpaceName(resource.space)} 里的可执行动作，而不是只停留在参考图层。`,
		actionHint: blueprint.quotedReason,
		evidenceLevel: 'medium',
	},
	{
		id: `insight-risk-${index}`,
		type: 'risk',
		title: `${blueprint.title} · 风险提醒`,
		summary: `引用 ${resource.title} 时，需额外核查 ${blueprint.topic} 与实际项目约束是否一致，避免局部借用后语义跑偏。`,
		riskHint: `核查 ${toDisplaySpaceName(resource.space)} 的真实约束、预算和维护边界。`,
		evidenceLevel: 'medium',
	},
];

const normalizeResourceAnchor = (
	anchor: ResourceImageAnchor,
	baseAnchor?: ResourceImageAnchor | null
): ResourceImageAnchor => ({
	...baseAnchor,
	...anchor,
	anchorMode: anchor.anchorMode ?? baseAnchor?.anchorMode ?? 'object',
	evidenceLevel: anchor.evidenceLevel ?? baseAnchor?.evidenceLevel ?? 'medium',
	insights: anchor.insights ?? baseAnchor?.insights ?? [],
});

const getResourceAnchorBlueprint = (
	resource: Pick<ResourceItem, 'category' | 'space' | 'tags' | 'desc' | 'title'>
): Array<Pick<ResourceImageAnchor, 'type' | 'title' | 'summary' | 'topic' | 'quotedReason' | 'anchorMode' | 'evidenceLevel'>> => {
	const primaryTag = resource.tags[0] ?? resource.category;
	const secondaryTag = resource.tags[1] ?? resource.space;

	switch (resource.category) {
		case '家具':
			return [
				{
					type: '产品点',
					title: `${toDisplaySpaceName(resource.space)}家具主体`,
					summary: `适合拆出体量、落地姿态与停留方式，判断是否能作为 ${toDisplaySpaceName(resource.space)} 的核心陈设锚点。`,
					topic: '家具',
					quotedReason: `用于确认 ${toDisplaySpaceName(resource.space)} 的家具气质与停留关系。`,
					anchorMode: 'object',
					evidenceLevel: 'strong',
				},
				{
					type: '体验点',
					title: `${primaryTag}停留触点`,
					summary: `重点看人与物的距离、停驻姿势和可达性，比整图更适合进入项目体验判断。`,
					topic: '体验',
					quotedReason: `用于拆解停留方式与用户行为路径。`,
					anchorMode: 'relation',
					evidenceLevel: 'medium',
				},
				{
					type: '运营点',
					title: `${secondaryTag}维护判断`,
					summary: `从拼接、面料与边角处理里判断清洁、搬运和高频使用下的耐久风险。`,
					topic: '运营',
					quotedReason: `用于提前判断运营维护成本。`,
					anchorMode: 'relation',
					evidenceLevel: 'medium',
				},
			];
		case '材料':
			return [
				{
					type: '材料点',
					title: `${toDisplaySpaceName(resource.space)}表面材质`,
					summary: `聚焦表面纹理、反射度和触感表达，适合进入材料板与替代比选。`,
					topic: '材料',
					quotedReason: `用于沉淀可复用的材料证据点。`,
					anchorMode: 'object',
					evidenceLevel: 'strong',
				},
				{
					type: '体验点',
					title: `${secondaryTag}触感判断`,
					summary: `从近距离局部判断湿度、脚感、手感和耐污性，更适合客房与高频触达区引用。`,
					topic: '体验',
					quotedReason: `用于把材质证据转成体验判断。`,
					anchorMode: 'relation',
					evidenceLevel: 'medium',
				},
			];
		case '灯光':
			return [
				{
					type: '氛围点',
					title: `${toDisplaySpaceName(resource.space)}光氛围`,
					summary: `聚焦主照、辅照和背景光的层次关系，用于判断整体语气是否稳定。`,
					topic: '灯光',
					quotedReason: `用于定调空间光氛围与品牌语气。`,
					anchorMode: 'relation',
					evidenceLevel: 'strong',
				},
				{
					type: '产品点',
					title: `${primaryTag}灯具载体`,
					summary: `把灯具体量、出光方式和安装位置单独抽出来，便于替代与选型。`,
					topic: '灯具',
					quotedReason: `用于沉淀具体灯具与安装方式。`,
					anchorMode: 'object',
					evidenceLevel: 'strong',
				},
				{
					type: '运营点',
					title: `${secondaryTag}维护与眩光`,
					summary: `同时记录更换难度、清洁频率和眩光风险，让灯光证据能直接进入落地判断。`,
					topic: '运营',
					quotedReason: `用于提前标注维护与眩光风险。`,
					anchorMode: 'relation',
					evidenceLevel: 'medium',
				},
			];
		case '工艺':
			return [
				{
					type: '运营点',
					title: `${primaryTag}使用风险`,
					summary: `拆解碰撞、松动、异响与维护频率，让工艺点能被项目直接判断。`,
					topic: '风险',
					quotedReason: `用于进入项目风险评估。`,
					anchorMode: 'relation',
					evidenceLevel: 'medium',
				},
				{
					type: '体验点',
					title: `${secondaryTag}静音体感`,
					summary: `把收口质量对安静感和触感的影响显性化，方便客房和夜间场景引用。`,
					topic: '体验',
					quotedReason: `用于建立体验与工艺的直接关系。`,
					anchorMode: 'relation',
					evidenceLevel: 'strong',
				},
			];
		case '配色':
			return [
				{
					type: '氛围点',
					title: `${toDisplaySpaceName(resource.space)}色彩锚点`,
					summary: `把综合色板拆成可引用的局部色彩关系，便于跨空间传递。`,
					topic: '色彩',
					quotedReason: `用于沉淀可复用的色彩锚点。`,
					anchorMode: 'relation',
					evidenceLevel: 'strong',
				},
				{
					type: '材料点',
					title: `${primaryTag}材色关系`,
					summary: `同时看颜色和材质的搭配关系，避免只记住颜色而忘记表面气质。`,
					topic: '材料',
					quotedReason: `用于建立色彩与材质关系。`,
					anchorMode: 'relation',
					evidenceLevel: 'medium',
				},
				{
					type: '体验点',
					title: `${secondaryTag}情绪温度`,
					summary: `用局部点来记录色温、明度和饱和度带来的情绪倾向。`,
					topic: '体验',
					quotedReason: `用于把色彩证据传给体验判断。`,
					anchorMode: 'relation',
					evidenceLevel: 'medium',
				},
			];
		default:
			return [
				{
					type: '体验点',
					title: `${toDisplaySpaceName(resource.space)}体验触点`,
					summary: `把整张参考图拆成可以讨论的具体触点，避免信息停留在情绪层。`,
					topic: '体验',
					quotedReason: `用于把案例图转成项目可引用证据。`,
					anchorMode: 'relation',
					evidenceLevel: 'medium',
				},
				{
					type: '产品点',
					title: `${primaryTag}关键物件`,
					summary: `把真正值得收藏的单点物件提取出来，支持替代与对标。`,
					topic: '产品',
					quotedReason: `用于拆出可替代的物件层信息。`,
					anchorMode: 'object',
					evidenceLevel: 'strong',
				},
				{
					type: '运营点',
					title: `${secondaryTag}落地提醒`,
					summary: `${resource.desc}`,
					topic: '运营',
					quotedReason: `用于把案例转成落地提醒。`,
					anchorMode: 'relation',
					evidenceLevel: 'medium',
				},
			];
	}
};

const getBoardResizeAnchor = (item: BoardCanvasItem, handle: BoardResizeHandle) => {
	const width = item.width;
	const height = getBoardCanvasItemHeight(item);
	const centerX = item.x + width / 2;
	const centerY = item.y + height / 2;

	switch (handle) {
		case 'nw':
			return { x: item.x + width, y: item.y + height };
		case 'n':
			return { x: centerX, y: item.y + height };
		case 'ne':
			return { x: item.x, y: item.y + height };
		case 'e':
			return { x: item.x, y: centerY };
		case 'se':
			return { x: item.x, y: item.y };
		case 's':
			return { x: centerX, y: item.y };
		case 'sw':
			return { x: item.x + width, y: item.y };
		case 'w':
			return { x: item.x + width, y: centerY };
	}
};

const getBoardResizeCursor = (handle: BoardResizeHandle) => {
	switch (handle) {
		case 'nw':
		case 'se':
			return 'nwse-resize';
		case 'ne':
		case 'sw':
			return 'nesw-resize';
		case 'n':
		case 's':
			return 'ns-resize';
		case 'e':
		case 'w':
			return 'ew-resize';
	}
};

interface PdfPlanCanvasProps {
	src: string;
	zoom: number;
	className?: string;
	onWheel: (event: ReactWheelEvent<HTMLDivElement>) => void;
	children?: ReactNode;
}

const PdfPlanCanvas = ({ src, zoom, className, onWheel, children }: PdfPlanCanvasProps) => {
	const canvasRef = useRef<HTMLCanvasElement | null>(null);
	const renderTaskRef = useRef<{ cancel: () => void } | null>(null);
	const [renderError, setRenderError] = useState<string | null>(null);

	useEffect(() => {
		let cancelled = false;
		const canvas = canvasRef.current;
		if (!canvas || !src) return undefined;

		const renderPdf = async () => {
			try {
				setRenderError(null);
				const pdfjsLib = await import('pdfjs-dist/legacy/build/pdf');
				pdfjsLib.GlobalWorkerOptions.workerSrc = '/api/pdf-worker';
				renderTaskRef.current?.cancel();
				const loadingTask = pdfjsLib.getDocument({
					url: src,
					useSystemFonts: true,
					useWorkerFetch: false,
				});
				const pdf = await loadingTask.promise;
				if (cancelled) return;
				const page = await pdf.getPage(1);
				if (cancelled) return;
				const viewport = page.getViewport({ scale: zoom });
				const outputScale = window.devicePixelRatio || 1;
				const context = canvas.getContext('2d');
				if (!context) return;
				canvas.width = Math.floor(viewport.width * outputScale);
				canvas.height = Math.floor(viewport.height * outputScale);
				canvas.style.width = `${viewport.width}px`;
				canvas.style.height = `${viewport.height}px`;
				context.setTransform(outputScale, 0, 0, outputScale, 0, 0);
				context.clearRect(0, 0, viewport.width, viewport.height);
				const renderTask = page.render({ canvasContext: context, viewport });
				renderTaskRef.current = renderTask;
				await renderTask.promise;
			} catch (error) {
				if (!cancelled && (error as { name?: string }).name !== 'RenderingCancelledException') {
					console.error('[CockpitPanel] PDF render failed:', error);
					const message = error instanceof Error ? error.message : String(error);
					setRenderError(`PDF 渲染失败：${message}`);
				}
			}
		};

		void renderPdf();
		return () => {
			cancelled = true;
			renderTaskRef.current?.cancel();
		};
	}, [src, zoom]);

	return (
		<div className={`relative mx-auto w-fit bg-white ${className ?? ''}`} onWheel={onWheel}>
			<canvas ref={canvasRef} className="block" />
			{children}
			{renderError && (
				<div className="absolute inset-0 flex items-center justify-center bg-black/70 p-6 text-center text-sm leading-6 text-white/72">
					{renderError}
				</div>
			)}
		</div>
	);
};

interface DxfPlanCanvasProps {
	src: string;
	zoom: number;
	className?: string;
	onWheel: (event: ReactWheelEvent<HTMLDivElement>) => void;
	children?: ReactNode;
}

const DxfPlanCanvas = ({ src, zoom, className, onWheel, children }: DxfPlanCanvasProps) => {
	const [geometry, setGeometry] = useState<DxfPreviewGeometry | null>(null);
	const [renderError, setRenderError] = useState<string | null>(null);

	useEffect(() => {
		let cancelled = false;
		const loadDxf = async () => {
			try {
				setRenderError(null);
				setGeometry(null);
				const response = await fetch(src);
				if (!response.ok) throw new Error(`DXF 读取失败：${response.status}`);
				const text = await response.text();
				if (cancelled) return;
				const next = parseDxfPreviewGeometry(text);
				setGeometry(next);
				if (next.entityCount === 0) setRenderError('DXF 未读取到可显示的 LINE / POLYLINE / CIRCLE / ARC 实体。');
			} catch (error) {
				if (!cancelled) {
					const message = error instanceof Error ? error.message : String(error);
					setRenderError(message);
				}
			}
		};
		void loadDxf();
		return () => {
			cancelled = true;
		};
	}, [src]);

	const width = Math.max(520, (geometry?.width ?? 1400) * zoom);
	const height = Math.max(360, (geometry?.height ?? 780) * zoom);

	return (
		<div className={`relative mx-auto w-fit bg-[var(--canvas-bg)] ${className ?? ''}`} onWheel={onWheel}>
			<svg
				className="block"
				width={width}
				height={height}
				viewBox={`0 0 ${geometry?.width ?? 1400} ${geometry?.height ?? 780}`}
				role="img"
				aria-label="DXF 图纸预览"
			>
				<rect x="0" y="0" width={geometry?.width ?? 1400} height={geometry?.height ?? 780} fill="#020403" />
				{geometry?.lines.map((line, index) => (
					<line
						key={`dxf-line-${index}`}
						x1={line.x1}
						y1={line.y1}
						x2={line.x2}
						y2={line.y2}
						stroke={getDxfStroke(line)}
						strokeWidth="1"
						vectorEffect="non-scaling-stroke"
						strokeLinecap="square"
					/>
				))}
				{geometry?.circles.map((circle, index) => (
					<circle
						key={`dxf-circle-${index}`}
						cx={circle.cx}
						cy={circle.cy}
						r={circle.r}
						fill="none"
						stroke={getDxfStroke(circle)}
						strokeWidth="1"
						vectorEffect="non-scaling-stroke"
					/>
				))}
				{geometry?.arcs.map((arc, index) => (
					<path
						key={`dxf-arc-${index}`}
						d={describeArcPath(arc)}
						fill="none"
						stroke={getDxfStroke(arc)}
						strokeWidth="1"
						vectorEffect="non-scaling-stroke"
					/>
				))}
				{geometry?.texts.map((text, index) => (
					<text
						key={`dxf-text-${index}`}
						x={text.x}
						y={text.y}
						fill={getDxfTextFill(text)}
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
			{children}
			{renderError && (
				<div className="absolute inset-0 flex items-center justify-center bg-black/70 p-6 text-center text-sm leading-6 text-white/72">
					{renderError}
				</div>
			)}
		</div>
	);
};

const PROJECT_FILE_CARDS: ProjectFileCard[] = [
	{
		title: '用户需求',
		desc: '围绕品牌定位气质，梳理项目目标客群、预算区间、空间优先级与体验期待。重点关注在自然景观、度假属性与品牌识别度之间的平衡关系。',
		badge: '核心输入',
		legacyCategory: '分析项目',
		objectAnchor: 'AlignedBrief',
		flowCategory: '项目锚点',
		stage: 'S1 意图显影',
		status: '已审',
		spaceScope: '全局',
		primaryTopic: '用户',
		domainTags: ['用户', '目标', '品牌'],
		updatedAt: '2026-03-30',
		refCount: 23,
	},
	{
		title: '市场分析',
		desc: '分析项目周边同类业态的客群画像、消费价格带与审美变化趋势，校准项目在区域中的价值锚点。同步比较本地度假型住宿与城市型精品酒店在社交属性和停留时长上的差异。',
		badge: '外部环境',
		legacyCategory: '分析项目',
		objectAnchor: 'AlignedBrief',
		flowCategory: '外部认知',
		stage: 'S2 分析扩展',
		status: '已审',
		spaceScope: '全局',
		primaryTopic: '市场',
		domainTags: ['市场', '客群', '定价'],
		updatedAt: '2026-03-29',
		refCount: 18,
	},
	{
		title: '竞品策略',
		desc: '拆解标杆民宿和设计酒店在公区氛围、客房尺度、材料表达与品牌传播上的差异点，识别可借鉴与应规避的策略。进一步提炼体验缺口、品牌错位和定价机会，作为后续概念切入依据。',
		badge: '对标拆解',
		legacyCategory: '分析项目',
		objectAnchor: 'EvidenceOnly',
		flowCategory: '外部认知',
		stage: 'S2 分析扩展',
		status: '待审',
		spaceScope: '全局',
		primaryTopic: '竞品',
		domainTags: ['竞品', '体验', '品牌'],
		updatedAt: '2026-03-31',
		refCount: 16,
	},
	{
		title: '色彩策略',
		desc: '定义主辅色、材质映射与情绪目标，构建符合项目定位的色彩体系。通过自然色调与材质细节建立统一语气，避免空间在自然语境中显得过度商业化。',
		badge: '氛围语言',
		legacyCategory: '分析项目',
		objectAnchor: 'InitialDesignPack',
		flowCategory: '表达系统',
		stage: 'S4 定向收束',
		status: '进行中',
		spaceScope: '公区',
		primaryTopic: '色彩',
		domainTags: ['色彩', '情绪', '品牌'],
		updatedAt: '2026-03-31',
		refCount: 12,
	},
	{
		title: '空间功能清单',
		desc: '梳理客房、公区、接待、餐饮与后勤等功能模块的面积占比和优先顺序，明确哪些区域承担品牌展示、停留社交和运营效率。同步界定高价值空间与可压缩空间，避免后期概念泛化。',
		badge: '功能配置',
		legacyCategory: '规划文件',
		objectAnchor: 'SPG',
		flowCategory: '空间策略',
		stage: 'S4 定向收束',
		status: '已审',
		spaceScope: '全局',
		primaryTopic: '空间',
		domainTags: ['功能', '空间', '运营'],
		updatedAt: '2026-03-28',
		refCount: 20,
	},
	{
		title: '动线组织草案',
		desc: '建立主人、住客、服务与补给四类动线的基础组织逻辑，确保抵达体验、入住效率与后勤流线互不干扰。特别关注场地中入口高差、景观面朝向与夜间照明对动线选择的影响。',
		badge: '流线',
		legacyCategory: '规划文件',
		objectAnchor: 'SPG',
		flowCategory: '空间策略',
		stage: 'S5 缺口补全',
		status: '待验证',
		spaceScope: '连廊',
		primaryTopic: '动线',
		domainTags: ['动线', '入口', '后勤'],
		updatedAt: '2026-03-31',
		refCount: 15,
	},
	{
		title: '场地约束条件',
		desc: '归纳场地高差、采光朝向、消防疏散、结构限制和气候条件对空间组织的影响，为概念方案建立现实边界。优先识别需要在早期就锁定的限制条件，避免后期出现大规模推翻。',
		badge: '约束',
		legacyCategory: '规划文件',
		objectAnchor: 'AlignedBrief',
		flowCategory: '决策约束',
		stage: 'S2 分析扩展',
		status: '已冻结',
		spaceScope: '全局',
		primaryTopic: '空间',
		domainTags: ['场地', '消防', '结构'],
		updatedAt: '2026-03-27',
		refCount: 24,
	},
	{
		title: '预算分配表',
		desc: '给出硬装、软装、灯光、家具与设备的预算比例建议，帮助项目在品牌表达与实际落地之间建立合理分配。重点列出可高配与可替代部分，防止预算被单一环节吞噬。',
		badge: '预算',
		legacyCategory: '规划文件',
		objectAnchor: 'InitialDesignPack',
		flowCategory: '决策约束',
		stage: 'S4 定向收束',
		status: '进行中',
		spaceScope: '全局',
		primaryTopic: '预算',
		domainTags: ['预算', '成本', '取舍'],
		updatedAt: '2026-03-30',
		refCount: 17,
	},
	{
		title: '品牌语义板',
		desc: '围绕项目品牌气质提炼可转译为空间语言的关键词与反关键词。通过情绪语义、品牌语境与消费心理交叉校准，避免气质模糊的表达。',
		badge: '品牌',
		legacyCategory: '指导文件',
		objectAnchor: 'InitialDesignPack',
		flowCategory: '表达系统',
		stage: 'S4 定向收束',
		status: '待审',
		spaceScope: '全局',
		primaryTopic: '品牌',
		domainTags: ['品牌', '语义', '识别度'],
		updatedAt: '2026-03-31',
		refCount: 19,
	},
	{
		title: '材料样本册',
		desc: '收录墙、地、顶及家具触感材料的搭配方向、耐用等级与替代层级，明确概念表达与运营维护之间的平衡。优先筛选适合项目环境条件、但不失细腻触感和品牌质感的材料组合。',
		badge: '材料',
		legacyCategory: '指导文件',
		objectAnchor: 'InitialDesignPack',
		flowCategory: '表达系统',
		stage: 'S5 缺口补全',
		status: '进行中',
		spaceScope: '客房',
		primaryTopic: '材料',
		domainTags: ['材料', '耐用性', '触感'],
		updatedAt: '2026-03-29',
		refCount: 14,
	},
	{
		title: '灯光场景表',
		desc: '梳理白天、傍晚、夜间及社交时段的照明层级与色温变化，建立一套兼顾情绪与运营的灯光场景表。强调公共空间的氛围转换与客房私密感的细微区别，避免一套照明走到底。',
		badge: '灯光',
		legacyCategory: '指导文件',
		objectAnchor: 'InitialDesignPack',
		flowCategory: '表达系统',
		stage: 'S5 缺口补全',
		status: '待验证',
		spaceScope: '大堂',
		primaryTopic: '灯光',
		domainTags: ['灯光', '氛围', '色温'],
		updatedAt: '2026-03-28',
		refCount: 11,
	},
	{
		title: '家具选型方向',
		desc: '明确床、沙发、椅凳、边几等重点家具的风格、尺寸与比例基准，避免不同供应渠道带来的视觉断裂。优先建立“轻、薄、功能明确”的家具轮廓，同时保留局部温润感。',
		badge: '家具',
		legacyCategory: '指导文件',
		objectAnchor: 'InitialDesignPack',
		flowCategory: '表达系统',
		stage: 'S5 缺口补全',
		status: '待审',
		spaceScope: '客房',
		primaryTopic: '家具',
		domainTags: ['家具', '比例', '风格'],
		updatedAt: '2026-03-30',
		refCount: 13,
	},
	{
		title: '大堂到店体验脚本',
		desc: '梳理从落客、迎宾、办入住到首段停留的体验链条，明确大堂在品牌第一印象中的节奏设计与关键触点，减少高峰时段拥堵与情绪落差。',
		badge: '到店体验',
		legacyCategory: '规划文件',
		objectAnchor: 'SPG',
		flowCategory: '空间策略',
		stage: 'S4 定向收束',
		status: '待审',
		spaceScope: '大堂',
		primaryTopic: '动线',
		domainTags: ['大堂', '入口', '体验'],
		updatedAt: '2026-03-31',
		refCount: 10,
	},
	{
		title: '餐厅运营动线卡',
		desc: '建立餐厅高峰与非高峰两套服务流线，明确备餐、上菜、回收、清洁与住客动线的交错边界，平衡运营效率与就餐体验。',
		badge: '餐饮运营',
		legacyCategory: '规划文件',
		objectAnchor: 'InitialDesignPack',
		flowCategory: '空间策略',
		stage: 'S5 缺口补全',
		status: '进行中',
		spaceScope: '餐厅',
		primaryTopic: '空间',
		domainTags: ['餐厅', '运营', '动线'],
		updatedAt: '2026-03-31',
		refCount: 9,
	},
	{
		title: '客房睡眠灯光子策略',
		desc: '细化客房“入睡-夜起-晨起”三段灯光场景，控制照度、色温与眩光，兼顾睡眠质量与路径安全，避免与公共区照明逻辑混用。',
		badge: '客房灯光',
		legacyCategory: '指导文件',
		objectAnchor: 'InitialDesignPack',
		flowCategory: '表达系统',
		stage: 'S5 缺口补全',
		status: '待验证',
		spaceScope: '客房',
		primaryTopic: '灯光',
		domainTags: ['客房', '睡眠', '照明'],
		updatedAt: '2026-03-30',
		refCount: 8,
	},
	{
		title: '公区社交家具组合',
		desc: '针对短停留与长停留两类社交场景定义公区家具组合与尺度关系，提升自由社交概率，同时保证通行效率与视觉秩序。',
		badge: '公区家具',
		legacyCategory: '指导文件',
		objectAnchor: 'InitialDesignPack',
		flowCategory: '表达系统',
		stage: 'S4 定向收束',
		status: '进行中',
		spaceScope: '公区',
		primaryTopic: '家具',
		domainTags: ['公区', '社交', '家具'],
		updatedAt: '2026-03-31',
		refCount: 9,
	},
	{
		title: '后勤补给流线校核',
		desc: '校核布草、清洁、补货、垃圾回收等后勤路径在不同时段的冲突点，保证后勤效率同时降低对住客主要动线的干扰。',
		badge: '后勤流线',
		legacyCategory: '规划文件',
		objectAnchor: 'SPG',
		flowCategory: '空间策略',
		stage: 'S5 缺口补全',
		status: '待审',
		spaceScope: '后勤',
		primaryTopic: '动线',
		domainTags: ['后勤', '补给', '效率'],
		updatedAt: '2026-03-31',
		refCount: 7,
	},
	{
		title: '项目启动会纪要',
		desc: '汇总甲方对品牌调性、目标房价、首期开放区域、试营业时间与样板优先级的口径，明确“先形成可试住样板，再放大到全项目”的推进策略，并记录品牌方对过度装饰与过度商业化表达的明确限制。',
		badge: '会议纪要',
		legacyCategory: '分析项目',
		objectAnchor: 'AlignedBrief',
		flowCategory: '项目锚点',
		stage: 'S1 意图显影',
		status: '已审',
		spaceScope: '全局',
		primaryTopic: '用户',
		domainTags: ['纪要', '目标', '节点'],
		updatedAt: '2026-03-26',
		refCount: 21,
	},
	{
		title: '目标客群入住画像与停留时段',
		desc: '将周末短住情侣、轻商务结伴、度假家庭三类核心客群拆成入住动机、到店时段、停留强度和社交偏好，明确大堂、公区、餐厅与客房在不同时间段承担的情绪任务和服务重点。',
		badge: '用户研究',
		legacyCategory: '分析项目',
		objectAnchor: 'AlignedBrief',
		flowCategory: '项目锚点',
		stage: 'S1 意图显影',
		status: '已审',
		spaceScope: '全局',
		primaryTopic: '用户',
		domainTags: ['用户画像', '入住', '停留'],
		updatedAt: '2026-03-30',
		refCount: 17,
	},
	{
		title: '场地踏勘照片整理与问题标注',
		desc: '整理入口高差、现状挡墙、屋檐压低、景观朝向、设备暴露面和临时施工通道等踏勘照片，并对影响首轮方案判断的现场问题做编号，方便后续设计、施工与机电同步校核。',
		badge: '现场踏勘',
		legacyCategory: '分析项目',
		objectAnchor: 'EvidenceOnly',
		flowCategory: '决策约束',
		stage: 'S2 分析扩展',
		status: '待审',
		spaceScope: '全局',
		primaryTopic: '空间',
		domainTags: ['踏勘', '现场', '问题'],
		updatedAt: '2026-03-28',
		refCount: 14,
	},
	{
		title: '竞品房价带与公区配置对照表',
		desc: '对比周边同类项目的房价带、房间面积、公区座位数、到店体验配置和餐饮模式，识别高感知价值但低投入的配置项，避免在错误环节投入过高成本。',
		badge: '竞品对照',
		legacyCategory: '分析项目',
		objectAnchor: 'EvidenceOnly',
		flowCategory: '外部认知',
		stage: 'S2 分析扩展',
		status: '已审',
		spaceScope: '全局',
		primaryTopic: '竞品',
		domainTags: ['竞品', '房价', '配置'],
		updatedAt: '2026-03-30',
		refCount: 15,
	},
	{
		title: '大堂首屏体验与服务台关系草图',
		desc: '定义住客进入大堂后 8 秒内可感知的品牌信息、主景别、服务台视线和等候落点，避免前台过强、景观过弱或导向不足导致的体验断点，并同步标注高峰时段排队缓冲区。',
		badge: '首屏体验',
		legacyCategory: '规划文件',
		objectAnchor: 'SPG',
		flowCategory: '空间策略',
		stage: 'S4 定向收束',
		status: '进行中',
		spaceScope: '大堂',
		primaryTopic: '动线',
		domainTags: ['大堂', '首屏', '服务台'],
		updatedAt: '2026-03-31',
		refCount: 12,
	},
	{
		title: '客房样板间问题清单',
		desc: '基于样板间首轮评审，记录床头开关位置、行李摆放、窗帘遮光、夜起照明、插座可达性与卫浴收纳等问题，并按“必须修正 / 试住观察 / 可后置优化”三档排序。',
		badge: '问题清单',
		legacyCategory: '规划文件',
		objectAnchor: 'SPG',
		flowCategory: '评审定版',
		stage: 'S5 缺口补全',
		status: '待验证',
		spaceScope: '客房',
		primaryTopic: '空间',
		domainTags: ['客房', '样板间', '问题'],
		updatedAt: '2026-03-31',
		refCount: 11,
	},
	{
		title: '餐厅早餐与晚间酒饮双场景切换表',
		desc: '梳理餐厅在早餐、下午茶、晚间酒饮三种运营场景下的家具布置、灯光亮度、服务动线与台面陈列切换逻辑，确保同一空间在不同营运时段仍保持统一气质。',
		badge: '场景切换',
		legacyCategory: '指导文件',
		objectAnchor: 'InitialDesignPack',
		flowCategory: '空间策略',
		stage: 'S5 缺口补全',
		status: '进行中',
		spaceScope: '餐厅',
		primaryTopic: '空间',
		domainTags: ['餐厅', '早餐', '酒饮'],
		updatedAt: '2026-03-30',
		refCount: 8,
	},
	{
		title: '公区软装首轮配置清单',
		desc: '罗列沙发、休闲椅、边几、地毯、落地灯、艺术装饰与绿植的首轮配置数量、预算档位与替代优先级，帮助判断哪些单品承担品牌识别，哪些单品承担氛围补位。',
		badge: '软装清单',
		legacyCategory: '指导文件',
		objectAnchor: 'InitialDesignPack',
		flowCategory: '表达系统',
		stage: 'S4 定向收束',
		status: '待审',
		spaceScope: '公区',
		primaryTopic: '家具',
		domainTags: ['公区', '软装', '配置'],
		updatedAt: '2026-03-31',
		refCount: 10,
	},
	{
		title: '机电点位与天花净高复核表',
		desc: '将空调风口、喷淋、烟感、检修口、线性灯、音响与投影设备点位叠合到天花方案上，核查净高、对称关系与主景别完整性，提前识别会破坏品牌感的设备暴露问题。',
		badge: '机电复核',
		legacyCategory: '规划文件',
		objectAnchor: 'EvidenceOnly',
		flowCategory: '决策约束',
		stage: 'S5 缺口补全',
		status: '待审',
		spaceScope: '大堂',
		primaryTopic: '灯光',
		domainTags: ['机电', '天花', '复核'],
		updatedAt: '2026-03-31',
		refCount: 13,
	},
	{
		title: '夜间归房路径照明与导视策略',
		desc: '定义从大堂、电梯厅、连廊到客房门口的夜间照明层级、脚下引导、门牌显隐与安全感阈值，控制眩光和迷失感，保证雨雾天气下仍具备清晰的归房路径。',
		badge: '夜间导视',
		legacyCategory: '指导文件',
		objectAnchor: 'InitialDesignPack',
		flowCategory: '表达系统',
		stage: 'S5 缺口补全',
		status: '待验证',
		spaceScope: '连廊',
		primaryTopic: '灯光',
		domainTags: ['夜间', '导视', '归房'],
		updatedAt: '2026-03-29',
		refCount: 9,
	},
	{
		title: '施工样板段验收标准',
		desc: '针对木饰面拼缝、石材收口、门套转角、灯槽阴影、五金表面和墙地交接等高敏感细节建立样板段验收标准，明确“可接受误差 / 必须返工 / 可后续修补”的判断依据。',
		badge: '样板验收',
		legacyCategory: '规划文件',
		objectAnchor: 'SPG',
		flowCategory: '评审定版',
		stage: 'S6 定版冻结',
		status: '待审',
		spaceScope: '全局',
		primaryTopic: '材料',
		domainTags: ['施工', '样板', '验收'],
		updatedAt: '2026-03-31',
		refCount: 18,
	},
	{
		title: '风险项跟踪与冻结清单',
		desc: '汇总目前仍影响排期和预算的高风险事项，包括场地排水、设备降噪、定制家具交期、进口灯具替代、样板段返修和消防审图反馈，并标记责任方、处理时点与冻结状态。',
		badge: '风险跟踪',
		legacyCategory: '规划文件',
		objectAnchor: 'EvidenceOnly',
		flowCategory: '评审定版',
		stage: 'S6 定版冻结',
		status: '进行中',
		spaceScope: '全局',
		primaryTopic: '预算',
		domainTags: ['风险', '冻结', '排期'],
		updatedAt: '2026-03-31',
		refCount: 16,
	},
];

const uniqueList = (items: Array<string | undefined | null>, limit = 8) =>
	Array.from(
		new Set(
			items
				.map((item) => item?.trim())
				.filter((item): item is string => Boolean(item))
		)
	).slice(0, limit);

const SPACE_VISUAL_BRIEF_PRESETS: Record<
	Exclude<BoardCanvasSpace, '全部'>,
	Pick<BoardVisualBrief, 'mustKeep' | 'styleKeywords' | 'materialKeywords' | 'lightingKeywords' | 'negativeConstraints'>
> = {
	大堂: {
		mustKeep: ['抵达首屏', '服务台关系', '等候落点', '自然景观联系', '低密度停留'],
		styleKeywords: ['克制', '自然', '自然质感', '轻松感', '非过度商业'],
		materialKeywords: ['木质顶面', '石材地面', '深色体块', '低饱和织物'],
		lightingKeywords: ['低照度暖光', '傍晚迎宾', '层次照明', '控制眩光'],
		negativeConstraints: ['商务酒店感', '奢华金色', '网红打卡感', '拥挤排队', '前台过强'],
	},
	餐厅: {
		mustKeep: ['早餐与晚间切换', '服务动线边界', '住客停留舒适度', '统一空间气质'],
		styleKeywords: ['松弛', '清爽', '度假', '运营友好'],
		materialKeywords: ['耐用桌面', '温润木色', '易维护软装', '局部绿植'],
		lightingKeywords: ['早餐自然光', '晚间暖光', '餐桌重点照明', '场景切换'],
		negativeConstraints: ['餐饮卖场感', '过度拥挤', '冷白强光', '服务流线暴露'],
	},
	客房: {
		mustKeep: ['睡眠质量', '行李落点', '夜起路径', '窗景参与', '私密感'],
		styleKeywords: ['安静', '克制', '温润', '轻薄家具', '真实可住'],
		materialKeywords: ['低饱和木色', '亲肤织物', '耐用墙地面', '柔和五金'],
		lightingKeywords: ['入睡灯光', '夜起低位光', '晨起自然光', '无眩光'],
		negativeConstraints: ['样板房空壳感', '过度装饰', '冷硬商务感', '插座不可达'],
	},
	公区: {
		mustKeep: ['自由社交', '通行效率', '家具组合秩序', '空间识别感'],
		styleKeywords: ['开放', '低密度社交', '轻度度假', '功能明确'],
		materialKeywords: ['可移动家具', '织物软装', '落地灯', '绿植'],
		lightingKeywords: ['分区照明', '停留角落暖光', '自然漫射光'],
		negativeConstraints: ['会所感过强', '家具堆砌', '动线堵塞', '杂乱陈列'],
	},
	连廊: {
		mustKeep: ['归房路径', '导视清晰', '脚下安全', '低光可识别'],
		styleKeywords: ['连续', '安定', '自然质感', '低干扰'],
		materialKeywords: ['防滑地面', '耐候墙面', '门牌节点', '压低屋檐'],
		lightingKeywords: ['低位引导光', '门牌显隐', '夜间安全阈值', '无眩光'],
		negativeConstraints: ['迷失感', '过暗死角', '冷白走廊感', '设备暴露'],
	},
	后勤: {
		mustKeep: ['补给效率', '清洁路径', '垃圾回收', '住客动线隔离'],
		styleKeywords: ['清晰', '耐用', '低干扰', '运营优先'],
		materialKeywords: ['耐磨地面', '易清洁墙面', '收纳系统', '防撞边角'],
		lightingKeywords: ['均匀工作照明', '安全照度', '维护可见性'],
		negativeConstraints: ['后勤外露', '路径冲突', '维护死角', '临时堆放'],
	},
};

const SPACE_PLAN_VIEW_PRESETS: Record<Exclude<BoardCanvasSpace, '全部'>, SpacePlanView> = {
	大堂: {
		space: '大堂',
		floorId: 'floor_1',
		spgVersion: 'SPG v1.2',
		irVersion: 'FloorPlanIR v0.1',
		status: 'auto',
		overallPlanRef: {
			title: '1F 总平关系视图',
			highlightZoneIds: ['z_lobby'],
			adjacentZoneIds: ['z_entry', 'z_outdoor', 'z_guest_corridor', 'z_service'],
		},
		detailPlanRef: {
			title: '大堂分平焦点视图',
			zoneIds: ['z_lobby'],
			moduleIds: ['m_entry', 'm_reception', 'm_waiting', 'm_window_view'],
		},
		planBrief: {
			spatialRole: '到达、迎宾、停留、转场。',
			adjacency: ['入口', '室外连接', '客房通道', '服务后台'],
			entrances: ['主入口', '室外通道侧入口'],
			mainCirculation: ['入口至前台保持清晰通行', '前台后侧服务动线与住客动线分离'],
			viewDirection: ['入口进入后视线引向室外景观', '等候区面向窗景和服务台'],
			fixedConstraints: ['入口开口不可改变', '现有结构主墙体位置不可改变', '主通道不可被大体量家具阻断'],
			flexibleZones: ['等候家具', '低位灯光', '软装陈设', '艺术摆件'],
			cameraSuggestions: ['入口看向室外连接', '前台斜向视角', '窗边停留区视角'],
			negativeConstraints: ['堵塞主通道', '改变门窗位置', '把大堂做成纯摆拍空间'],
		},
		features: [
			{ id: 'lobby-entry', label: '主入口', kind: 'entrance', x: 0.1, y: 0.72, description: '主入口和抵达首屏，生成时保留进入感。' },
			{ id: 'lobby-route', label: '主通道', kind: 'circulation', x: 0.36, y: 0.68, w: 0.5, h: 0.12, description: '入口到前台的清晰通行带。' },
			{ id: 'lobby-view', label: '室外景观视线', kind: 'view', x: 0.72, y: 0.3, description: '入口视线引导到室外景观方向。' },
			{ id: 'lobby-fixed', label: '固定墙体', kind: 'fixed', x: 0.48, y: 0.18, w: 0.36, h: 0.1, description: '结构主墙体不作为可拆软装处理。' },
			{ id: 'lobby-flex', label: '等候区', kind: 'flexible', x: 0.58, y: 0.58, w: 0.24, h: 0.18, description: '家具、地毯、落地灯可作为本轮方案变量。' },
		],
	},
	餐厅: {
		space: '餐厅',
		floorId: 'floor_1',
		spgVersion: 'SPG v1.2',
		irVersion: 'FloorPlanIR v0.1',
		status: 'auto',
		overallPlanRef: { title: '1F 总平关系视图', highlightZoneIds: ['z_dining'], adjacentZoneIds: ['z_lobby', 'z_kitchen', 'z_outdoor'] },
		detailPlanRef: { title: '餐厅分平焦点视图', zoneIds: ['z_dining'], moduleIds: ['m_breakfast', 'm_service', 'm_window_tables'] },
		planBrief: {
			spatialRole: '早餐、晚间轻餐、社交停留。',
			adjacency: ['大堂', '厨房后场', '室外'],
			entrances: ['大堂侧入口', '服务侧入口'],
			mainCirculation: ['住客动线与上菜动线错开', '餐桌之间保持运营通行宽度'],
			viewDirection: ['优先面向室外景观或窗景', '避免视线直冲后场'],
			fixedConstraints: ['后场入口不可暴露为主视觉', '主要服务路径不可被卡座阻断'],
			flexibleZones: ['餐桌组合', '早餐台', '局部绿植', '吊灯节奏'],
			cameraSuggestions: ['窗边餐桌视角', '早餐台看向就餐区', '晚间暖光版本'],
			negativeConstraints: ['餐饮卖场感', '桌椅过密', '冷白强光'],
		},
		features: [
			{ id: 'dining-guest', label: '住客入口', kind: 'entrance', x: 0.12, y: 0.45, description: '从大堂进入餐厅的首要视角。' },
			{ id: 'dining-service', label: '服务动线', kind: 'circulation', x: 0.72, y: 0.55, w: 0.14, h: 0.34, description: '上菜与回收路径需保持清晰。' },
			{ id: 'dining-view', label: '窗景面', kind: 'view', x: 0.52, y: 0.18, description: '餐桌布置优先借窗景。' },
			{ id: 'dining-fixed', label: '后场界面', kind: 'fixed', x: 0.78, y: 0.24, w: 0.12, h: 0.25, description: '后场门和设备区不作为视觉中心。' },
			{ id: 'dining-flex', label: '餐桌区', kind: 'flexible', x: 0.38, y: 0.55, w: 0.34, h: 0.28, description: '桌椅、吊灯、织物可参与方案生成。' },
		],
	},
	客房: {
		space: '客房',
		floorId: 'floor_2',
		spgVersion: 'SPG v1.2',
		irVersion: 'FloorPlanIR v0.1',
		status: 'auto',
		overallPlanRef: { title: '2F 总平关系视图', highlightZoneIds: ['z_guestroom'], adjacentZoneIds: ['z_corridor', 'z_balcony', 'z_service_core'] },
		detailPlanRef: { title: '客房分平焦点视图', zoneIds: ['z_guestroom'], moduleIds: ['m_sleep', 'm_luggage', 'm_window', 'm_bath_entry'] },
		planBrief: {
			spatialRole: '睡眠、收纳、窗景停留、夜间安全。',
			adjacency: ['连廊', '阳台或窗景面', '卫浴入口'],
			entrances: ['连廊侧入户门'],
			mainCirculation: ['入户至床侧和卫浴入口保持夜间可达', '行李落点不阻塞通行'],
			viewDirection: ['床侧和窗边停留区优先面向自然景观或窗景'],
			fixedConstraints: ['卫生间湿区位置不可被视觉改写', '入户门和窗洞位置保留'],
			flexibleZones: ['床头背景', '窗边坐榻', '行李架', '阅读灯'],
			cameraSuggestions: ['入户看向窗景', '床头斜向', '窗边停留区'],
			negativeConstraints: ['样板房空壳感', '夜起路径不清', '插座不可达'],
		},
		features: [
			{ id: 'room-entry', label: '入户', kind: 'entrance', x: 0.12, y: 0.8, description: '客房进入点，控制首屏与收纳关系。' },
			{ id: 'room-route', label: '夜起路径', kind: 'circulation', x: 0.34, y: 0.68, w: 0.42, h: 0.1, description: '床侧到卫浴的安全低位路径。' },
			{ id: 'room-view', label: '窗景', kind: 'view', x: 0.78, y: 0.22, description: '窗景是客房主体验锚点。' },
			{ id: 'room-fixed', label: '湿区', kind: 'fixed', x: 0.16, y: 0.24, w: 0.2, h: 0.26, description: '卫浴边界不可被软装参考图改写。' },
			{ id: 'room-flex', label: '床头', kind: 'flexible', x: 0.52, y: 0.5, w: 0.3, h: 0.18, description: '床头背景、灯光、织物可参与生成。' },
		],
	},
	公区: {
		space: '公区',
		floorId: 'floor_1',
		spgVersion: 'SPG v1.2',
		irVersion: 'FloorPlanIR v0.1',
		status: 'auto',
		overallPlanRef: { title: '1F 总平关系视图', highlightZoneIds: ['z_public'], adjacentZoneIds: ['z_lobby', 'z_dining', 'z_courtyard'] },
		detailPlanRef: { title: '公区分平焦点视图', zoneIds: ['z_public'], moduleIds: ['m_social', 'm_reading', 'm_transition'] },
		planBrief: {
			spatialRole: '自由社交、阅读、转场和低密度停留。',
			adjacency: ['大堂', '餐厅', '庭院', '连廊'],
			entrances: ['大堂侧入口', '庭院侧入口'],
			mainCirculation: ['保持穿行路径可见', '停留家具不截断公共通行'],
			viewDirection: ['停留点看向庭院或内景焦点'],
			fixedConstraints: ['主通行带和消防疏散方向不可遮挡'],
			flexibleZones: ['沙发组', '书架', '落地灯', '活动家具'],
			cameraSuggestions: ['低密度社交角', '阅读停留区', '穿行视角'],
			negativeConstraints: ['会所化过强', '家具堆砌', '动线堵塞'],
		},
		features: [
			{ id: 'public-entry', label: '转场口', kind: 'entrance', x: 0.14, y: 0.5, description: '从大堂进入公区的转场节点。' },
			{ id: 'public-route', label: '公共通行', kind: 'circulation', x: 0.38, y: 0.62, w: 0.48, h: 0.12, description: '公共通行带需保持连续。' },
			{ id: 'public-view', label: '庭院方向', kind: 'view', x: 0.76, y: 0.28, description: '社交区视线应有自然焦点。' },
			{ id: 'public-fixed', label: '固定界面', kind: 'fixed', x: 0.18, y: 0.24, w: 0.22, h: 0.12, description: '固定界面保持完整，不被陈设遮蔽。' },
			{ id: 'public-flex', label: '社交组团', kind: 'flexible', x: 0.5, y: 0.48, w: 0.28, h: 0.2, description: '沙发、边几、灯光可形成多版本。' },
		],
	},
	连廊: {
		space: '连廊',
		floorId: 'floor_2',
		spgVersion: 'SPG v1.2',
		irVersion: 'FloorPlanIR v0.1',
		status: 'auto',
		overallPlanRef: { title: '2F 总平关系视图', highlightZoneIds: ['z_corridor'], adjacentZoneIds: ['z_guestroom', 'z_stair', 'z_public'] },
		detailPlanRef: { title: '连廊分平焦点视图', zoneIds: ['z_corridor'], moduleIds: ['m_wayfinding', 'm_doorplate', 'm_low_light'] },
		planBrief: {
			spatialRole: '归房路径、导视、安全和雨雾识别。',
			adjacency: ['客房', '楼梯', '公区'],
			entrances: ['楼梯侧入口', '客房门列'],
			mainCirculation: ['连续归房路径不可被陈设打断', '门前缓冲保持清晰'],
			viewDirection: ['导视和门牌应在低照度下可辨识'],
			fixedConstraints: ['走廊宽度和门洞位置不可改变', '设备点位尽量弱化'],
			flexibleZones: ['门牌节点', '低位灯', '墙面材质节奏'],
			cameraSuggestions: ['低位引导光视角', '门牌节点近景', '雨雾归房路径'],
			negativeConstraints: ['过暗死角', '冷白走廊感', '迷失感'],
		},
		features: [
			{ id: 'corridor-entry', label: '楼梯口', kind: 'entrance', x: 0.12, y: 0.5, description: '进入连廊的方向锚点。' },
			{ id: 'corridor-route', label: '归房路径', kind: 'circulation', x: 0.18, y: 0.48, w: 0.68, h: 0.08, description: '连续、安全、低干扰的通行路径。' },
			{ id: 'corridor-view', label: '导视视线', kind: 'view', x: 0.72, y: 0.42, description: '导视和门牌需要可被提前识别。' },
			{ id: 'corridor-fixed', label: '客房门列', kind: 'fixed', x: 0.52, y: 0.26, w: 0.42, h: 0.08, description: '门洞和结构节奏不可随意改变。' },
			{ id: 'corridor-flex', label: '低位灯', kind: 'flexible', x: 0.5, y: 0.62, w: 0.42, h: 0.08, description: '低位引导光和墙面细节可深化。' },
		],
	},
	后勤: {
		space: '后勤',
		floorId: 'floor_1',
		spgVersion: 'SPG v1.2',
		irVersion: 'FloorPlanIR v0.1',
		status: 'auto',
		overallPlanRef: { title: '1F 总平关系视图', highlightZoneIds: ['z_backstage'], adjacentZoneIds: ['z_dining', 'z_service', 'z_waste'] },
		detailPlanRef: { title: '后勤分平焦点视图', zoneIds: ['z_backstage'], moduleIds: ['m_storage', 'm_cleaning', 'm_delivery'] },
		planBrief: {
			spatialRole: '补给、清洁、回收和服务效率。',
			adjacency: ['餐厅后场', '服务入口', '垃圾暂存'],
			entrances: ['服务入口', '餐厅后场门'],
			mainCirculation: ['清洁、补给、回收路径分离', '临时堆放不得占用通行'],
			viewDirection: ['住客视线内尽量不暴露后勤动作'],
			fixedConstraints: ['设备点位、排水和服务门位置不可随意变化'],
			flexibleZones: ['收纳系统', '防撞边角', '标识和照明'],
			cameraSuggestions: ['收纳墙近景', '清洁路径视角', '服务入口视角'],
			negativeConstraints: ['后勤外露', '路径冲突', '维护死角'],
		},
		features: [
			{ id: 'back-entry', label: '服务入口', kind: 'entrance', x: 0.14, y: 0.68, description: '服务与补给的进入点。' },
			{ id: 'back-route', label: '补给路径', kind: 'circulation', x: 0.28, y: 0.62, w: 0.5, h: 0.1, description: '补给路径应与清洁回收分离。' },
			{ id: 'back-view', label: '住客避让', kind: 'view', x: 0.78, y: 0.28, description: '减少住客视线内的后勤暴露。' },
			{ id: 'back-fixed', label: '设备点位', kind: 'fixed', x: 0.18, y: 0.22, w: 0.28, h: 0.18, description: '排水、设备和服务门位置不轻易改动。' },
			{ id: 'back-flex', label: '收纳系统', kind: 'flexible', x: 0.54, y: 0.48, w: 0.28, h: 0.2, description: '柜体、标识和照明可优化。' },
		],
	},
};

const createDefaultFloorPlanReconstruction = (
	space: Exclude<BoardCanvasSpace, '全部'>,
	sourceFormat: SpacePlanTopicState['sourceType'] = 'manual'
): FloorPlanReconstruction => ({
	status: 'raw',
	irVersion: 'FloorPlanIR draft',
	sourceFormat,
	coordinateSystem: {
		unit: sourceFormat === 'image' ? 'px' : 'mm',
		scaleStatus: sourceFormat === 'cad' || sourceFormat === 'dxf' ? 'estimated' : 'uncalibrated',
		northStatus: 'missing',
	},
	objectCounts: {
		wall: 0,
		door: 0,
		window: 0,
		column: 0,
		fixed_furniture: 0,
		loose_furniture: 0,
		north_arrow: 0,
	},
	spaceBoundaryCount: 0,
	functionZoneCount: 0,
	alignment: {
		matchedSpace: space,
		confidence: 0.62,
		status: 'candidate',
	},
	heightProfile: {
		status: 'missing',
	},
	scaleCalibration: {
		source: 'fallback',
		samples: 0,
	},
	elements: [],
	pendingIssues: ['待校准比例', '待确认北向', '待补充高度'],
	updatedAt: new Date().toISOString().slice(0, 10),
});

const createDefaultSpacePlanTopicStates = (): Record<Exclude<BoardCanvasSpace, '全部'>, SpacePlanTopicState> =>
	SPACE_VIEW_ORDER.reduce<Record<Exclude<BoardCanvasSpace, '全部'>, SpacePlanTopicState>>((acc, space) => {
		const planView = SPACE_PLAN_VIEW_PRESETS[space];
		acc[space] = {
			space,
			status: 'synced',
			sourceType: 'manual',
			uploadedFileName: undefined,
			updatedAt: new Date().toISOString().slice(0, 10),
			viewChain: space === '客房' || space === '连廊'
				? ['project', 'floor', 'space']
				: ['floor', 'space'],
			reconstruction: createDefaultFloorPlanReconstruction(space, 'manual'),
		};
		return acc;
	}, {} as Record<Exclude<BoardCanvasSpace, '全部'>, SpacePlanTopicState>);

const createSystemVisualBrief = (space: Exclude<BoardCanvasSpace, '全部'>): BoardVisualBrief => {
	const globalCards = PROJECT_FILE_CARDS
		.filter((card) => card.spaceScope === '全局')
		.sort((a, b) => b.refCount - a.refCount)
		.slice(0, 4);
	const spaceCards = PROJECT_FILE_CARDS
		.filter((card) => card.spaceScope === space)
		.sort((a, b) => b.refCount - a.refCount)
		.slice(0, 5);
	const sourceCards = uniqueList([...globalCards, ...spaceCards].map((card) => card.title), 9)
		.map((title) => PROJECT_FILE_CARDS.find((card) => card.title === title))
		.filter(Boolean) as ProjectFileCard[];
	const preset = SPACE_VISUAL_BRIEF_PRESETS[space];
	const strongestSpaceCard = spaceCards[0];
	const strongestGlobalCard = globalCards[0];

	const designIntent =
		strongestSpaceCard?.desc ??
		`以项目整体调性为底座，为${space}建立可生图、可追溯、可迭代的空间视觉基线。`;
	const mustKeep = uniqueList([
		...preset.mustKeep,
		...spaceCards.flatMap((card) => card.domainTags),
		strongestSpaceCard?.badge,
	], 8);
	const styleKeywords = uniqueList([
		...preset.styleKeywords,
		'功能主义',
		...globalCards.flatMap((card) => card.domainTags),
	], 8);
	const negativeConstraints = uniqueList([
		...preset.negativeConstraints,
		'过度商业化',
	], 8);
	const sourceRefs = sourceCards.map((card) => ({
		title: card.title,
		section: `${card.objectAnchor} / ${card.stage}`,
		status: card.status,
		excerpt: card.desc,
	}));
	const visualPrompt = [
		`场景主题：${space}空间的建筑室内效果图，服务于本项目的方案画布生图。`,
		`项目总调性：克制、自然、功能主义；整体应保持真实感和非过度商业化表达。`,
		`当前空间命题：${designIntent}`,
		`画面必须体现：${mustKeep.join('、')}。这些内容是空间分析底稿中的方向约束，不应被参考图或临时对话轻易冲掉。`,
		`空间与构成：采用真实人尺度视角，画面需要有清晰的空间层次、主次关系和可停留区域；避免只生成漂亮材质拼贴，必须能看出人在空间中如何抵达、停留、转向或被引导。`,
		`材料与细部：重点表达 ${preset.materialKeywords.join('、')}；材料需要真实可落地，表面质感细腻但不过度奢华，适合项目的长期运营和维护。`,
		`光线与时间：重点表达 ${preset.lightingKeywords.join('、')}；光线应有层次，避免全场均质打亮，保留阴影、漫反射和局部重点照明。`,
		`人物与活动：画面可出现少量使用者或服务人员，密度低，动作自然，服务于空间尺度判断；人物不能成为商业广告主体。`,
		`镜头建议：建筑摄影感，24-35mm 人眼高度视角，构图稳定，展示入口关系、停留节点、材料转折和景观联系；不要夸张广角、不要舞台化灯效。`,
		`参考图使用原则：参考图只作为视觉证据，优先借用构图、灯光、材质、家具比例或局部氛围；不得覆盖本空间的项目基线和负向约束。`,
		`负向提示：避免 ${negativeConstraints.join('、')}；不要科幻感、不要样板间空壳感、不要拥挤人群、不要失真的文字标识。`,
	].join('\n');

	return {
		space,
		status: 'auto',
		summary: `${space} · ${preset.styleKeywords.slice(0, 4).join(' / ')} · 来源于项目底盘自动综合`,
		designIntent,
		visualPrompt,
		mustKeep,
		styleKeywords,
		materialKeywords: preset.materialKeywords,
		lightingKeywords: preset.lightingKeywords,
		negativeConstraints,
		sourceRefs,
		disabledTags: [],
		lockedTags: strongestGlobalCard ? [strongestGlobalCard.domainTags[0], preset.styleKeywords[0]].filter(Boolean) : [preset.styleKeywords[0]],
		customNote: '',
		lastCompiledAt: new Date().toISOString(),
	};
};

const getVisualBriefTags = (brief: BoardVisualBrief) =>
	uniqueList([
		...brief.styleKeywords,
		...brief.mustKeep,
		...brief.materialKeywords,
		...brief.lightingKeywords,
		...brief.negativeConstraints.map((item) => `避免:${item}`),
	], 18);

const getBoardReferenceLabel = (kind?: BoardReferenceKind) => {
	switch (kind) {
		case 'project_pack':
			return '项目参考包';
		case 'scene_card':
			return '场景参考图';
		case 'detail_card':
			return '局部锚点卡';
		case 'relation_card':
			return '关系参考组';
		default:
			return '参考素材';
	}
};

const inferReferenceRoles = (values: string[]) => {
	const text = values.join(' ');
	if (/灯|光|照明|色温|氛围/.test(text)) return { primaryRole: '灯光', secondaryRole: '氛围' };
	if (/材料|木|石|织物|肌理|工艺|收口/.test(text)) return { primaryRole: '材质', secondaryRole: '细部' };
	if (/家具|沙发|椅|桌|坐|停留/.test(text)) return { primaryRole: '家具', secondaryRole: '停留关系' };
	if (/动线|入口|路径|导视|关系|首屏/.test(text)) return { primaryRole: '空间关系', secondaryRole: '构图' };
	if (/色彩|配色|颜色/.test(text)) return { primaryRole: '色彩', secondaryRole: '氛围' };
	return { primaryRole: '氛围', secondaryRole: '构图' };
};

const buildReferenceControlFromSource = (
	source: {
		sourceType?: BoardCanvasSourceType;
		entityType?: ResourceEntityType;
		title: string;
		desc?: string;
		meta?: string;
	},
	options?: {
		anchorMode?: ResourceAnchorMode;
		tags?: string[];
		space?: string;
	}
): BoardReferenceControl => {
	const { primaryRole, secondaryRole } = inferReferenceRoles([
		source.title,
		source.desc ?? '',
		source.meta ?? '',
		...(options?.tags ?? []),
	]);
	const entityType = source.entityType ?? 'image';
	const isRelation = entityType === 'anchor' && options?.anchorMode === 'relation';
	const kind: BoardReferenceKind =
		entityType === 'project'
			? 'project_pack'
			: isRelation || entityType === 'insight'
				? 'relation_card'
				: entityType === 'anchor'
					? 'detail_card'
					: 'scene_card';
	const scope: BoardReferenceScope =
		kind === 'project_pack' ? 'global' : kind === 'relation_card' ? 'relation' : kind === 'detail_card' ? 'detail' : 'scene';
	const negative = uniqueList([
		primaryRole === '灯光' ? '强眩光' : undefined,
		primaryRole === '材质' ? '廉价贴图感' : undefined,
		primaryRole === '家具' ? '家具堆砌' : undefined,
		'照搬原图',
		'脱离当前空间基线',
	], 4);
	const mustHave = uniqueList([
		primaryRole,
		secondaryRole,
		...(options?.tags ?? []),
	], 5);
	const label = getBoardReferenceLabel(kind);
	const bindTo = kind === 'detail_card' ? `${options?.space ?? '当前空间'}.${primaryRole}` : undefined;
	const relationshipLogic = kind === 'relation_card'
		? `参考 ${source.title} 中多个局部之间的组合关系，优先保留顺序、主次和空间叙事，不把锚点拆成互不相关的装饰。`
		: undefined;

	return {
		kind,
		scope,
		label,
		primaryRole,
		secondaryRole,
		mustHave,
		negative,
		bindTo,
		relationshipLogic,
		weight: kind === 'detail_card' || kind === 'relation_card' ? 'high' : 'medium',
		structuredSummary:
			kind === 'project_pack'
				? `作为全局偏置参考整体调性、品牌语法和禁区，不直接复制具体对象。`
				: kind === 'scene_card'
					? `作为本轮场景参考，主参考 ${primaryRole}${secondaryRole ? `，次参考 ${secondaryRole}` : ''}。`
					: kind === 'detail_card'
						? `作为局部可执行动作，绑定 ${bindTo}，只影响该细节槽位。`
						: relationshipLogic ?? `作为关系模板参考局部组合逻辑。`,
	};
};

const formatReferenceControlForPrompt = (control: BoardReferenceControl) =>
	[
		`${control.label} / ${control.scope} / weight=${control.weight}`,
		`主参考: ${control.primaryRole}${control.secondaryRole ? `；次参考: ${control.secondaryRole}` : ''}`,
		control.bindTo ? `绑定目标: ${control.bindTo}` : '',
		control.relationshipLogic ? `关系逻辑: ${control.relationshipLogic}` : '',
		`必须保留: ${control.mustHave.join('、')}`,
		`禁止带入: ${control.negative.join('、')}`,
	].filter(Boolean).join('\n');

export const formatBoardVisualBriefForPrompt = (brief: BoardVisualBrief): string => {
	const disabled = new Set(brief.disabledTags);
	const enabledTags = getVisualBriefTags(brief).filter((tag) => !disabled.has(tag));
	const locked = brief.lockedTags.filter((tag) => !disabled.has(tag));
	return [
		`当前空间: ${brief.space}`,
		`状态: ${brief.status}`,
		`空间意图: ${brief.designIntent}`,
		`生图基线提示词:\n${brief.visualPrompt}`,
		`已应用标签: ${enabledTags.join(' / ')}`,
		locked.length > 0 ? `锁定约束: ${locked.join(' / ')}` : '',
		brief.customNote ? `用户修订: ${brief.customNote}` : '',
		`负向约束: ${brief.negativeConstraints.filter((item) => !disabled.has(`避免:${item}`)).join(' / ')}`,
		`来源: ${brief.sourceRefs.slice(0, 4).map((ref) => ref.title).join(' / ')}`,
	].filter(Boolean).join('\n');
};

const formatSpacePlanViewForPrompt = (planView: SpacePlanView): string =>
	[
		`PlanBrief · ${planView.space}`,
		`来源: ${planView.overallPlanRef.title} + ${planView.detailPlanRef.title} / ${planView.spgVersion} / ${planView.irVersion}`,
		`空间角色: ${planView.planBrief.spatialRole}`,
		`总平关系: 相邻 ${planView.planBrief.adjacency.join('、')}；高亮 ${planView.overallPlanRef.highlightZoneIds.join('、')}；弱显 ${planView.overallPlanRef.adjacentZoneIds.join('、')}。`,
		`入口: ${planView.planBrief.entrances.join('、')}`,
		`主通行: ${planView.planBrief.mainCirculation.join('；')}`,
		`视线方向: ${planView.planBrief.viewDirection.join('；')}`,
		`硬约束: ${planView.planBrief.fixedConstraints.join('；')}`,
		`可变区: ${planView.planBrief.flexibleZones.join('、')}`,
		`镜头建议: ${planView.planBrief.cameraSuggestions.join('、')}`,
		`禁止: ${planView.planBrief.negativeConstraints.join('、')}`,
	].join('\n');

const formatPlanAnnotationsForPrompt = (annotations?: PlanAnnotation[]): string => {
	if (!annotations || annotations.length === 0) return '';
	return [
		'图纸标注:',
		...annotations.map((annotation, index) => {
			const tone = getPlanAnnotationTone(annotation.kind);
			return `${String(index + 1).padStart(2, '0')}. ${tone.label} ${annotation.label} @ ${Math.round(annotation.x * 100)}%/${Math.round(annotation.y * 100)}%`;
		}),
	].join('\n');
};

const formatFloorPlanReconstructionForPrompt = (reconstruction?: FloorPlanReconstruction): string => {
	if (!reconstruction) return '';
	const counts = Object.entries(reconstruction.objectCounts)
		.filter(([, count]) => count > 0)
		.map(([type, count]) => `${type}:${count}`)
		.join(' / ');
	const height = reconstruction.heightProfile.status === 'missing'
		? '高度待补充'
		: [
			reconstruction.heightProfile.ceilingHeight ? `层高 ${reconstruction.heightProfile.ceilingHeight}mm` : '',
			reconstruction.heightProfile.beamBottomHeight ? `梁底 ${reconstruction.heightProfile.beamBottomHeight}mm` : '',
			reconstruction.heightProfile.doorHeight ? `门高 ${reconstruction.heightProfile.doorHeight}mm` : '',
			reconstruction.heightProfile.windowSillHeight ? `窗台 ${reconstruction.heightProfile.windowSillHeight}mm` : '',
		].filter(Boolean).join('；');
	return [
		`FloorPlanIR: ${reconstruction.irVersion} / ${reconstruction.status}`,
		`坐标: ${reconstruction.coordinateSystem.unit} / 比例 ${reconstruction.coordinateSystem.scaleStatus} / 北向 ${reconstruction.coordinateSystem.northStatus}`,
		counts ? `识别对象: ${counts}` : '',
		`空间边界: ${reconstruction.spaceBoundaryCount}；功能分区: ${reconstruction.functionZoneCount}`,
		`空间对齐: ${reconstruction.alignment.matchedSpace} / ${Math.round(reconstruction.alignment.confidence * 100)}% / ${reconstruction.alignment.status}`,
		`高度: ${height}`,
		reconstruction.pendingIssues.length ? `待确认: ${reconstruction.pendingIssues.join('、')}` : '',
	].filter(Boolean).join('\n');
};

const getPlanFeatureTone = (kind: PlanFeatureKind) => {
	switch (kind) {
		case 'entrance':
			return { label: '入口', color: '#38bdf8', bg: 'rgba(56,189,248,0.18)' };
		case 'circulation':
			return { label: '动线', color: '#facc15', bg: 'rgba(250,204,21,0.18)' };
		case 'view':
			return { label: '视线', color: '#34d399', bg: 'rgba(52,211,153,0.18)' };
		case 'fixed':
			return { label: '固定', color: '#f87171', bg: 'rgba(248,113,113,0.18)' };
		case 'flexible':
			return { label: '可变', color: '#c084fc', bg: 'rgba(192,132,252,0.18)' };
		default:
			return { label: '节点', color: '#e5e7eb', bg: 'rgba(229,231,235,0.18)' };
	}
};

const getPlanAnnotationTone = (kind: PlanAnnotationKind) => {
	if (kind === 'forbidden') return { label: '禁改', color: '#fb7185', bg: 'rgba(251,113,133,0.18)' };
	return getPlanFeatureTone(kind);
};

const PLAN_ANNOTATION_TOOLS: Array<{ kind: 'select' | PlanAnnotationKind; label: string }> = [
	{ kind: 'select', label: '选择' },
	{ kind: 'entrance', label: '入口' },
	{ kind: 'circulation', label: '动线' },
	{ kind: 'view', label: '视线' },
	{ kind: 'fixed', label: '固定' },
	{ kind: 'flexible', label: '可变' },
	{ kind: 'forbidden', label: '禁改' },
];

const RESOURCE_ITEMS: ResourceItem[] = [
	{
		id: 'sofa-hay-mags',
		title: 'MAGS 模块沙发（原型）',
		brand: 'HAY',
		series: 'MAGS',
		category: '家具',
		imageSrc: '',
		fallbackImageSrc: '/resource-images/public-furniture.svg',
		imageCollection: 'default',
		imageNames: [
			'@gardehvalsoe Photo by Gaggenau Official on May 15, 2023. 未提供相片說明。..jpg',
			'Poltrona现代沙发茶几组合SU模型下载【ID1118504278】.jpg',
			'收藏到 muebles.jpg',
			'收藏到 住みたい家.jpg',
		],
		desc: '低轮廓、可拼接，适合公区与大堂自由社交布局。',
		space: '公区',
		budgetBand: '高配型',
		leadTimeDays: 35,
		risk: '中',
		tags: ['北欧', '社交', '可重组'],
		alternatives: ['sofa-local-modular', 'sofa-compact-fabric'],
		sourceType: 'system',
		sourceName: '设计知外',
		recommendCount: 52,
		favoriteQuoteCount: 885,
	},
	{
		id: 'sofa-local-modular',
		title: '本地替代模块沙发 A',
		brand: '本地工厂',
		series: '模块沙发 A',
		category: '家具',
		imageSrc: '',
		fallbackImageSrc: '/resource-images/public-furniture.svg',
		imageCollection: 'default',
		imageNames: [
			'收藏到 住みたい家.jpg',
			'收藏到 For the Home.jpg',
			'收藏到 H海派.jpg',
			'孙建亚的家丨上海 · 西郊1100平米的野奢园林别墅.jpg',
		],
		desc: '体量接近，交期更短，适合预算控制项目。',
		space: '公区',
		budgetBand: '均衡型',
		leadTimeDays: 14,
		risk: '低',
		tags: ['替代', '快交付', '性价比'],
		alternatives: ['sofa-hay-mags'],
		sourceType: 'user',
		sourceName: 'Warizay Visual',
		recommendCount: 55,
		favoriteQuoteCount: 503,
	},
	{
		id: 'lamp-lobby-layer',
		title: '大堂分层照明组',
		brand: '定制灯光',
		series: '分层照明组',
		category: '灯光',
		imageSrc: '',
		fallbackImageSrc: '/resource-images/lobby-light.svg',
		imageCollection: 'default',
		imageNames: [
			'YINJISPACE - LDH Design x Qu Yard Plus.jpg',
			'Villa Awasi - Rent Villa Awasi at Tampah Hills Lombok.jpg',
			'Sight Villa, Karaj, Iran by UFO StudioVisualization.jpg',
			'收藏到 A2 - 餐厅 Restaurant.jpg',
		],
		desc: '主照 + 洗墙 + 装饰灯，支持到店体验节奏。',
		space: '大堂',
		budgetBand: '均衡型',
		leadTimeDays: 10,
		risk: '低',
		tags: ['到店体验', '分层照明', '可调光'],
		alternatives: ['lamp-lobby-soft'],
	},
	{
		id: 'lamp-lobby-soft',
		title: '大堂暖感照明替代组',
		brand: '基础灯光',
		series: '暖感照明组',
		category: '灯光',
		imageSrc: '',
		fallbackImageSrc: '/resource-images/lobby-light.svg',
		imageCollection: 'default',
		imageNames: [
			'Villa Awasi - Rent Villa Awasi at Tampah Hills Lombok.jpg',
			'CASE 5.0  APER.jpg',
			'YINJISPACE - LDH Design x Qu Yard Plus.jpg',
			'收藏到 a faire.jpg',
		],
		desc: '强调低照度舒适性，降低眩光和维护成本。',
		space: '大堂',
		budgetBand: '经济型',
		leadTimeDays: 8,
		risk: '低',
		tags: ['暖感', '低眩光', '替代'],
		alternatives: ['lamp-lobby-layer'],
	},
	{
		id: 'mat-room-antiwet',
		title: '客房防潮木饰面系统',
		brand: '定制木作',
		series: '防潮木饰面',
		category: '材料',
		imageSrc: '',
		fallbackImageSrc: '/resource-images/guestroom-material.svg',
		imageCollection: 'default',
		imageNames: [
			'Picture background-1.jpg',
			'Picture background-2.jpg',
			'Picture background-3.jpg',
			'Jutakutokushu September Issue.jpg',
		],
		desc: '针对山地潮湿环境优化，兼顾触感与耐久。',
		space: '客房',
		budgetBand: '均衡型',
		leadTimeDays: 18,
		risk: '中',
		tags: ['客房', '防潮', '木饰面'],
		alternatives: ['mat-room-laminate'],
	},
	{
		id: 'mat-room-laminate',
		title: '客房木纹复合替代板',
		brand: '国产复合板',
		series: '木纹复合板',
		category: '材料',
		imageSrc: '',
		fallbackImageSrc: '/resource-images/guestroom-material.svg',
		imageCollection: 'default',
		imageNames: [
			'Picture background-2.jpg',
			'Picture background-3.jpg',
			'造梦空间SIILI基里木作郑州展厅MOOITIMELESS2024中国河南.jpg',
			'收藏到 things to build.jpg',
		],
		desc: '外观接近，预算更友好，适合压缩成本。',
		space: '客房',
		budgetBand: '经济型',
		leadTimeDays: 7,
		risk: '低',
		tags: ['替代', '预算优化'],
		alternatives: ['mat-room-antiwet'],
	},
	{
		id: 'craft-joint-silent',
		title: '静音节点收口工艺',
		brand: '节点工艺',
		series: '静音收口',
		category: '工艺',
		imageSrc: '',
		fallbackImageSrc: '/resource-images/craft-detail.svg',
		imageCollection: 'default',
		imageNames: [
			'收藏到 Portes.jpg',
			'收藏到 architektur.jpg',
			'收藏到 走廊、端景、玄关、通道、.jpg',
			'收藏到 Arsitektur.jpg',
		],
		desc: '优化夜间脚步与碰撞噪声，提升客房静谧性。',
		space: '客房',
		budgetBand: '均衡型',
		leadTimeDays: 5,
		risk: '中',
		tags: ['节点', '静音', '施工标准'],
		alternatives: ['craft-standard-joint'],
	},
	{
		id: 'palette-hay-mountain',
		title: 'HAY 山地低饱和色板',
		brand: 'HAY',
		series: '山地低饱和',
		category: '配色',
		imageSrc: '',
		fallbackImageSrc: '/resource-images/color-palette.svg',
		imageCollection: 'default',
		imageNames: [
			'@audemarspiguet Photo by Audemars Piguet on January 29, 2024..jpg',
			'@audemarspiguet Photo by Audemars Piguet on October 14, 2024..jpg',
			'@audemarspiguet Photo by Audemars Piguet on September 10, 2025. May be.jpg',
			'Slider-Template-3.jpg',
		],
		desc: '灰绿 + 木色 + 暖白，适配自然语境与品牌识别。',
		space: '全局',
		budgetBand: '均衡型',
		leadTimeDays: 1,
		risk: '低',
		tags: ['品牌一致', '低饱和', '跨空间'],
		alternatives: ['palette-neutral-warm'],
	},
	{
		id: 'ref-hotel-arrival',
		title: '山地酒店到店体验参考包',
		brand: '山地酒店案例',
		series: '到店体验',
		category: '参考',
		imageSrc: '',
		fallbackImageSrc: '/resource-images/arrival-reference.svg',
		imageCollection: 'default',
		imageNames: [
			'收藏到 A2 - 餐厅 Restaurant.jpg',
			'Sight Villa, Karaj, Iran by UFO StudioVisualization.jpg',
			'cathaypacificbringsaredesignedloungeexperiencetothebridgeathongkongint.jpg',
			'收藏到 Casa de Campo.jpg',
		],
		desc: '包含入口、落客、迎宾与首停留的动线案例。',
		space: '大堂',
		budgetBand: '经济型',
		leadTimeDays: 1,
		risk: '低',
		tags: ['案例', '到店体验', '动线'],
		alternatives: [],
	},
	{
		id: 'furniture-reference-set-1',
		title: '家具 1 参考组',
		brand: '方案高参',
		series: '家具1',
		category: '家具',
		imageSrc: '',
		fallbackImageSrc: '/resource-images/public-furniture.svg',
		desc: '来自 D:\\1 方案高参\\家具1 的家具参考图组，适合在资源雷达中做家具方向筛选与连续比对。',
		space: '全局',
		budgetBand: '均衡型',
		leadTimeDays: 1,
		risk: '低',
		tags: ['家具', '参考组', '资源扩充'],
		alternatives: ['furniture-reference-set-2'],
		imageCollection: 'furniture-1',
		imageNames: [
			'2ee6ca242090981.69663230da048.webp',
			'6f53af242090981.696632321200d.webp',
			'93c534242090981.6966323210f41.webp',
			'acfbe6242090981.696632320fc5e.webp',
			'ed4c53242090981.6966302a9fc52.webp',
		],
	},
	{
		id: 'furniture-reference-set-2',
		title: '家具 2 参考组',
		brand: '方案高参',
		series: '家具2',
		category: '家具',
		imageSrc: '',
		fallbackImageSrc: '/resource-images/public-furniture.svg',
		desc: '来自 D:\\1 方案高参\\家具2 的家具参考图组，用于补充资源雷达中的家具备选与风格比较。',
		space: '全局',
		budgetBand: '均衡型',
		leadTimeDays: 1,
		risk: '低',
		tags: ['家具', '方案参考', '资源扩充'],
		alternatives: ['furniture-reference-set-1'],
		imageCollection: 'furniture-2',
		imageNames: [
			'46d461239484557.692afeaf51408.webp',
			'5a672d239484557.6929f6fa03d17.webp',
			'88889b239484557.692afdf42baaf.webp',
			'c1a5cb239484557.692b015a920df.webp',
			'c7fb3f239484557.6929f92f18018.webp',
			'd9f0a9239484557.6929f6fa04bba.webp',
			'dfc036239484557.6929f6fa05293.webp',
			'e2bb89239484557.692afdf42ce73.webp',
		],
	},
];

const buildPublicPictureUrl = (name: string, collection: PublicPictureCollection = 'default') =>
	collection === 'default'
		? `/api/public-pictures?name=${encodeURIComponent(name)}`
		: `/api/public-pictures?collection=${encodeURIComponent(collection)}&name=${encodeURIComponent(name)}`;
const buildAdvisorAvatarUrl = (name: string) =>
	`/api/public-pictures?collection=advisor-avatar&name=${encodeURIComponent(name)}`;
const isExternalImageSrc = (src?: string) => Boolean(src && /^https?:\/\//i.test(src));
const isSystemManagedResourceSrc = (src?: string) =>
	Boolean(src && (src.startsWith('/resource-images/') || src.startsWith('/api/public-pictures?collection=')));
const isResourceRadarSourceLabel = (label?: string) => typeof label === 'string' && label.startsWith('资源雷达');
const BOARD_GENERATION_DEMO_IMAGE_NAMES = [
	'0fe15bc486cd39de2deb231a1f0c3ce3.jpg',
	'15c4059b5bf06ecb8391e6256fa6a8cc.jpg',
	'18a4a85a2825b88ff509b842d4f1dc04.jpg',
	'2ecd774071b3aa7a229888b0a58a05ac.jpg',
	'5279319d9a1fc9f70467adf05f16fb36.jpg',
	'689e19076d2e9ffc5c4ba7a24204cf3c.jpg',
] as const;
const buildBoardGenerationDemoImageUrl = (name: string) => `/demo-generated/${encodeURIComponent(name)}`;
const hydrateBoardGeneratedMockSources = (items: BoardGeneratedItem[], fallbackImageSrc = '') =>
	items.map((item, index) => {
		if (!item.id.startsWith('board-generated-mock-')) return item;
		const demoImageName = BOARD_GENERATION_DEMO_IMAGE_NAMES[index % BOARD_GENERATION_DEMO_IMAGE_NAMES.length];
		const imageSrc = buildBoardGenerationDemoImageUrl(demoImageName);
		return {
			...item,
			imageSrc,
			fallbackImageSrc: fallbackImageSrc || imageSrc,
		};
	});
const mergeBoardGeneratedItemsWithMockSeeds = (items: BoardGeneratedItem[], mockItems: BoardGeneratedItem[]) => {
	const merged = [...items];
	for (const mockItem of mockItems) {
		if (!merged.some((item) => item.id === mockItem.id)) {
			merged.push(mockItem);
		}
	}
	return merged;
};

const MOCK_BOARD_GENERATION_SEEDS: Array<{
	space: Exclude<BoardCanvasSpace, '全部'>;
	topicScope: BoardCanvasMode;
	generationRound: number;
	status: BoardGeneratedStatus;
	title: string;
	promptSummary: string;
	sourceContext: string;
}> = [];



const getPublicPictureSeries = (pictureNames: string[], startIndex: number, desiredCount = 5) => {
	if (pictureNames.length === 0) return [];

	const count = Math.min(desiredCount, pictureNames.length);
	const result: string[] = [];
	for (let offset = 0; offset < pictureNames.length && result.length < count; offset += 1) {
		const name = pictureNames[(startIndex + offset) % pictureNames.length];
		if (!result.includes(name)) result.push(name);
	}
	return result;
};

type ExpertWorkspaceKey = 'assembly' | 'tasks' | 'reports' | 'review';

interface ExpertTeamRoleItem {
	id: string;
	title: string;
	shortName: string;
	avatarName: string;
	summary: string;
	status: '当前激活' | '储备位';
	duty: string;
	trigger: string;
	source: string;
	tags: string[];
	featured?: boolean;
}

interface ExpertTaskItem {
	id: string;
	order: number;
	title: string;
	mission: string;
	status: '已完成' | '执行中' | '待触发';
	team: string[];
	outputs: string[];
	checks: string[];
	featured?: boolean;
}

interface ExpertReportItem {
	id: string;
	title: string;
	summary: string;
	lead: string;
	partners: string[];
	sourceTask: string;
	points: string[];
	featured?: boolean;
}

interface ExpertReviewItem {
	id: string;
	title: string;
	summary: string;
	group: string;
	checks: string[];
	source: string;
	featured?: boolean;
}

type ExpertDetailSelection =
	| { kind: 'role'; id: string }
	| { kind: 'task'; id: string }
	| { kind: 'report'; id: string }
	| { kind: 'review'; id: string };

const EXPERT_WORKSPACE_TABS: Array<{ key: ExpertWorkspaceKey; label: string; desc: string }> = [
	{ key: 'assembly', label: '团队组建', desc: '按工作地图确定当前激活位，方向锁定后再启用储备位。' },
	{ key: 'tasks', label: '任务安排', desc: '先锁 1-5，再推进 6-9，最后封装 10。' },
	{ key: 'reports', label: '专题汇报', desc: '对色彩、家具、尺度、公区四专题做汇总确认。' },
	{ key: 'review', label: '成果审阅', desc: '最终一致性复核与冻结，不在这里重新发散。' },
];

const EXPERT_VIEW_SUMMARY: Record<ExpertWorkspaceKey, string> = {
	assembly: '所有角色都必须对应明确工作责任；没有责任映射的角色不进当前列表。',
	tasks: '4.2 不做设计定案，只确认任务顺序、输入输出、依赖和校验标准。',
	reports: '4.3 是按任务清单执行后的专题确认，不是再次开题。',
	review: '4.4 只做最终一致性复核、治理检查与冻结说明。',
};

const EXPERT_TEAM_SECTIONS: Array<{ id: string; label: string; eyebrow: string; items: ExpertTeamRoleItem[] }> = [
	{
		id: 'assembly-space',
		label: '空间与实施主线',
		eyebrow: '当前激活',
		items: [
			{
				id: 'role-space-director',
				title: '空间设计总统筹',
				shortName: '空间总控',
				avatarName: '未标题-1.png',
				summary: '统筹项目级方向框架、尺度主线与四专题收口。',
				status: '当前激活',
				duty: '绑定任务 4 / 5 / 8 / 10，负责方向基线与尺度总口径。',
				trigger: '3.S.2 工作地图完成后立即激活。',
				source: '来自 SPG 主骨架与方向框架定义。',
				tags: ['方向框架', '尺度控制', '深化入口'],
				featured: true,
			},
			{
				id: 'role-boundary-advisor',
				title: '实施边界顾问',
				shortName: '边界顾问',
				avatarName: '未标题-2.png',
				summary: '提前界定哪些判断能落，哪些判断要留作待确认项。',
				status: '当前激活',
				duty: '绑定任务 4 / 7 / 8，负责实施边界、结构风险与家具落地接口。',
				trigger: '方向框架与家具策略定义阶段全程在线。',
				source: '来自工作地图中的实施约束主线。',
				tags: ['实施边界', '结构预警', '家具策略'],
				featured: true,
			},
			{
				id: 'role-interface-advisor',
				title: '建筑-景观室内接口顾问',
				shortName: '接口顾问',
				avatarName: '未标题-3.png',
				summary: '处理建筑、景观、室内之间的边界与开口冲突。',
				status: '当前激活',
				duty: '绑定任务 1 / 8，负责场地接口、开口策略与连贯体验。',
				trigger: '项目底板建立时激活，后续跟随尺度专题复核。',
				source: '来自 SPG 分区与流线结构校验。',
				tags: ['接口边界', '开口策略', '场地参数'],
			},
		],
	},
	{
		id: 'assembly-user',
		label: '用户与体验主线',
		eyebrow: '当前激活',
		items: [
			{
				id: 'role-user-researcher',
				title: '用户研究专家',
				shortName: '用户研究',
				avatarName: '未标题-4.png',
				summary: '把客群动机、支付逻辑和复购线索显性化。',
				status: '当前激活',
				duty: '绑定任务 1 / 2，负责项目底板中的用户侧证据与成功条件。',
				trigger: '项目底板和核心目标锁定阶段优先激活。',
				source: '来自三驱动力中的用户关系驱动力。',
				tags: ['用户动机', '成功条件', '复购线索'],
				featured: true,
			},
			{
				id: 'role-vacation-journey',
				title: '轻度假旅程研究员',
				shortName: '旅程研究',
				avatarName: '未标题-5.png',
				summary: '把周末短住的行为顺序拆成可设计的节点脚本。',
				status: '当前激活',
				duty: '绑定任务 2 / 9，负责四时段行为剧本和公区节点组织。',
				trigger: '方向基线明确后进入公区专题时持续激活。',
				source: '来自人因序列与 SPG 公区结构。',
				tags: ['四时段剧本', '节点组织', '旅程序列'],
				featured: true,
			},
			{
				id: 'role-social-psychology',
				title: '社交心理研究员',
				shortName: '社交心理',
				avatarName: '未标题-6.png',
				summary: '控制公区社交密度，保证可见但不强制。',
				status: '当前激活',
				duty: '绑定任务 9，负责情侣 / 亲子 / 单人三类客群的公区分层。',
				trigger: '公共社交专题排程与专题确认阶段激活。',
				source: '来自 HumanContextLayer 的私密梯度约束。',
				tags: ['社交密度', '私密梯度', '客群分层'],
			},
		],
	},
	{
		id: 'assembly-brand',
		label: '品牌与生活方式转译',
		eyebrow: '当前激活',
		items: [
			{
				id: 'role-brand-research',
				title: '品牌语法研究专家',
				shortName: '品牌研究',
				avatarName: '未标题-7.png',
				summary: '把品牌气质转成方法，不做表面贴皮。',
				status: '当前激活',
				duty: '绑定任务 3 / 6，负责品牌语义、色彩入口与关键触点识别。',
				trigger: '品牌与在地依据建立时优先激活。',
				source: '来自品牌转译与方法语法约束。',
				tags: ['品牌语法', '色彩入口', '关键触点'],
				featured: true,
			},
			{
				id: 'role-nordic-lifestyle',
				title: '北欧生活方式研究员',
				shortName: '北欧方式',
				avatarName: '未标题-8.png',
				summary: '把年轻、克制、功能主义翻成日常使用方式。',
				status: '当前激活',
				duty: '绑定任务 3 / 4，负责生活方式语气与总体气质基线。',
				trigger: '方向框架定义前完成品牌语义翻译。',
				source: '来自品牌参照与生活方式映射。',
				tags: ['总体气质', '功能主义', '日常使用'],
			},
			{
				id: 'role-local-lifestyle',
				title: '在地生活方式研究员',
				shortName: '在地方式',
				avatarName: '未标题-9.png',
				summary: '把在地节律转成色彩、节奏和停留感。',
				status: '当前激活',
				duty: '绑定任务 3 / 6，负责场地提取色、四季氛围和专题 1 主提。',
				trigger: '色彩专题定义与专题汇报阶段持续激活。',
				source: '来自 GeoCoordinateBaseline 与 TemporalBaseline。',
				tags: ['场地提取色', '四季节律', '专题主提'],
				featured: true,
			},
		],
	},
	{
		id: 'assembly-support',
		label: '专题支撑与经营风险',
		eyebrow: '当前激活',
		items: [
			{
				id: 'role-color-light',
				title: '色彩情绪与光环境系统专家',
				shortName: '色光系统',
				avatarName: '未标题-10.png',
				summary: '把色彩与日夜光环境作为同一系统处理。',
				status: '当前激活',
				duty: '绑定任务 6，负责色温策略、季节调节和情绪曲线。',
				trigger: '色彩专题任务卡启动时激活。',
				source: '来自 TemporalBaseline 的日夜节律要求。',
				tags: ['色温管理', '情绪曲线', '季节调节'],
				featured: true,
			},
			{
				id: 'role-ffe-lead',
				title: '家具软装系统统筹专家（FF&E）',
				shortName: 'FF&E统筹',
				avatarName: '未标题-11.png',
				summary: '统筹原品、在地定制、触点强化与保养逻辑。',
				status: '当前激活',
				duty: '绑定任务 7，负责家具语法、耐候策略与触点分配。',
				trigger: '家具专题任务卡启动时激活。',
				source: '来自家具策略与供应可得性检查。',
				tags: ['家具语法', '耐候策略', '触点分配'],
				featured: true,
			},
			{
				id: 'role-investment-agent',
				title: '经营与投资视角代理人',
				shortName: '经营代理',
				avatarName: '未标题-12.png',
				summary: '从经营模型反看哪些选择值得花钱，哪些只会加重负担。',
				status: '当前激活',
				duty: '绑定任务 2 / 7，负责目标优先级、投入产出与关键触点投资。',
				trigger: '核心目标锁定后持续参与家具和专题确认。',
				source: '来自盈利质量驱动力与投资边界。',
				tags: ['投入产出', '经营视角', '关键触点'],
			},
			{
				id: 'role-operation-temporal',
				title: '运营时序顾问',
				shortName: '时序顾问',
				avatarName: '未标题-13.png',
				summary: '把淡旺季、日夜节律和开业时序传导到专题参数里。',
				status: '当前激活',
				duty: '绑定任务 2 / 6 / 9，负责时段策略、淡旺季切换与开业窗口提醒。',
				trigger: '目标锁定后全流程跟进 6-9 专题。',
				source: '来自 TemporalBaseline 的经营时序约束。',
				tags: ['淡旺季', '日夜节律', '开业时序'],
				featured: true,
			},
			{
				id: 'role-risk-controller',
				title: '风险分析员（总控）',
				shortName: '风险总控',
				avatarName: '未标题-14.png',
				summary: '把高风险材料、供应链与结构变更集中挂账。',
				status: '当前激活',
				duty: '绑定任务 5 / 10，负责风险清单、待确认项和冻结前复核。',
				trigger: '方向锁定检查点与深化入口准备阶段激活。',
				source: '来自 Failure-First 清单与冻结治理。',
				tags: ['风险清单', '挂账治理', '冻结前复核'],
			},
		],
	},
	{
		id: 'assembly-reserve',
		label: '方向锁定后可启用的储备位',
		eyebrow: '储备位',
		items: [
			{
				id: 'role-natural-light',
				title: '自然光感顾问',
				shortName: '自然光感',
				avatarName: '未标题-1.png',
				summary: '在方向锁定后进一步优化自然采光与低位见山策略。',
				status: '储备位',
				duty: '用于补强开口、窗台和白天光感的微调判断。',
				trigger: '任务 5 完成后，如需深化自然采光体验时启用。',
				source: '来自尺度专题的后置优化位。',
				tags: ['自然采光', '低位见山', '后置优化'],
			},
			{
				id: 'role-soundscape',
				title: '户外声景编辑',
				shortName: '户外声景',
				avatarName: '未标题-2.png',
				summary: '在晚间与户外节点补强声环境体验。',
				status: '储备位',
				duty: '用于公区与户外廊的声景节奏编辑。',
				trigger: '任务 9 进入晚间场景细化后启用。',
				source: '来自公区专题的时段体验补位。',
				tags: ['声景节奏', '晚间体验', '户外廊'],
			},
			{
				id: 'role-service-script',
				title: '服务剧本策划',
				shortName: '服务剧本',
				avatarName: '未标题-3.png',
				summary: '把运营人员动作和空间使用脚本进一步对齐。',
				status: '储备位',
				duty: '用于把服务节奏回写到入口缓冲、早餐与晚间场景。',
				trigger: '任务 10 进入深化入口封装时启用。',
				source: '来自后续深化设计入口准备。',
				tags: ['服务节奏', '运营脚本', '深化入口'],
			},
		],
	},
];

const EXPERT_TASK_SECTIONS: Array<{ id: string; label: string; eyebrow: string; items: ExpertTaskItem[] }> = [
	{
		id: 'tasks-baseline',
		label: '基线与方向锁定',
		eyebrow: '任务 1-5',
		items: [
			{
				id: 'task-1',
				order: 1,
				title: '项目底板建立',
				mission: '先把项目类型、场地、目标客群、交付边界和成功条件站稳。',
				status: '已完成',
				team: ['用户研究专家', '建筑-景观室内接口顾问', '项目总控'],
				outputs: ['项目底板卡', '成功条件摘要', '待确认项挂账'],
				checks: ['是否形成唯一项目定义', '是否列出 In / Out 边界', '是否保留待确认项索引'],
				featured: true,
			},
			{
				id: 'task-2',
				order: 2,
				title: '核心目标与阶段范围锁定',
				mission: '先裁品牌纯粹度与经营可行性的优先级，再锁本轮范围。',
				status: '已完成',
				team: ['用户研究专家', '经营与投资视角代理人', '运营时序顾问'],
				outputs: ['目标优先级卡', '阶段范围锁定单', '三驱动力映射'],
				checks: ['是否写清买单前 / 中 / 后链条', '是否显式处理时间维度', '是否明确本轮不做什么'],
				featured: true,
			},
			{
				id: 'task-3',
				order: 3,
				title: '品牌与在地依据建立',
				mission: '把品牌语法和在地依据同时站稳，避免风格贴皮。',
				status: '已完成',
				team: ['品牌语法研究专家', '北欧生活方式研究员', '在地生活方式研究员'],
				outputs: ['品牌依据卡', '在地依据卡', '冲突项说明'],
				checks: ['是否是方法语法而非样式拼贴', '是否形成在地提取规则', '是否可回写到四专题'],
			},
			{
				id: 'task-4',
				order: 4,
				title: '项目级方向框架定义',
				mission: '先定方向底色，再定总体气质和体验-运营重心。',
				status: '已完成',
				team: ['空间设计总统筹', '北欧生活方式研究员', '经营与投资视角代理人'],
				outputs: ['方向基线卡', '身份认同锚点', '原创独特锚点'],
				checks: ['是否形成唯一方向基线', '是否能映射四专题', '是否回答用户为何来 / 选 / 复购 / 传播'],
				featured: true,
			},
			{
				id: 'task-5',
				order: 5,
				title: '方向基线锁定检查点',
				mission: '未锁基线，不进专题。',
				status: '已完成',
				team: ['空间设计总统筹', '风险分析员（总控）', '各专题负责人'],
				outputs: ['方向锁定确认单', '专题启动条件', '风险挂账更新'],
				checks: ['是否形成唯一方向', '是否完成专题映射', '是否保留结构与成本预警项'],
				featured: true,
			},
		],
	},
	{
		id: 'tasks-topics',
		label: '专题任务定义与排程',
		eyebrow: '任务 6-9',
		items: [
			{
				id: 'task-6',
				order: 6,
				title: '色彩专题任务卡',
				mission: '定义色彩系统的输入依据、输出格式、启动条件与校验标准。',
				status: '执行中',
				team: ['色彩情绪与光环境系统专家', '品牌语法研究专家', '运营时序顾问'],
				outputs: ['基础底色', '场地提取色规则', '日夜色温管理', '季节调节策略'],
				checks: ['是否同时响应品牌语法与在地色', '是否处理白天 / 夜间双方案', '是否避免淡季冷清负向情绪'],
				featured: true,
			},
			{
				id: 'task-7',
				order: 7,
				title: '家具专题任务卡',
				mission: '明确家具语法边界、原品 / 定制分工与耐候校验方式。',
				status: '执行中',
				team: ['家具软装系统统筹专家（FF&E）', '实施边界顾问', '经营与投资视角代理人'],
				outputs: ['原品 / 定制分工', '关键触点清单', '四季保养约束'],
				checks: ['是否验证高湿与冻融耐候', '是否兼容情侣 / 亲子两类姿势', '是否挂高风险材料校验项'],
			},
			{
				id: 'task-8',
				order: 8,
				title: '尺度专题任务卡',
				mission: '明确公区、客房、过渡空间的尺度阈值与开口策略。',
				status: '执行中',
				team: ['空间设计总统筹', '建筑-景观室内接口顾问', '实施边界顾问'],
				outputs: ['尺度阈值', '窗台与开口策略', '结构与成本预警'],
				checks: ['是否验证夏季通风与冬季保温', '是否分别审查昼 / 夜采光状态', '是否保留结构验证入口'],
			},
			{
				id: 'task-9',
				order: 9,
				title: '公区专题任务卡',
				mission: '明确公共空间组织方式与“可见不强制”的行为剧本。',
				status: '执行中',
				team: ['轻度假旅程研究员', '社交心理研究员', '运营时序顾问'],
				outputs: ['四节点结构', '四时段行为剧本', '客群分层策略', '淡旺季切换'],
				checks: ['是否覆盖晨 / 白 / 晚 / 夜四时段', '是否兼容情侣 / 亲子 / 单人三类客群', '是否定义淡季低客流激活方式'],
				featured: true,
			},
		],
	},
	{
		id: 'tasks-entry',
		label: '后续分支入口准备',
		eyebrow: '任务 10',
		items: [
			{
				id: 'task-10',
				order: 10,
				title: '深化设计入口准备',
				mission: '封装方向基线、四专题任务卡与风险清单，准备进入后续分支。',
				status: '待触发',
				team: ['空间设计总统筹', '风险分析员（总控）', '各专题负责人'],
				outputs: ['深化设计入口说明', '三驱动力证据链', '继续 / 自行执行 / 返回修改触发条件'],
				checks: ['是否汇总方向基线与四专题', '是否标注风险与待确认项', '是否写清下一回合触发条件'],
				featured: true,
			},
		],
	},
];

const EXPERT_REPORT_ITEMS: ExpertReportItem[] = [
	{
		id: 'report-color',
		title: '专题 1 · 色彩系统',
		summary: '底色克制，提取色唯一，日夜与冬季情绪要能切换。',
		lead: '在地生活方式研究员',
		partners: ['品牌语法研究专家', '运营时序顾问'],
		sourceTask: '来自任务 6 · 色彩专题任务卡',
		points: ['暖白 / 浅灰 / 深炭为底', '苔藓绿为唯一场地提取色', '夜间以暖光激活深炭与苔藓绿对比', '冬季可引入暖米色调辅助暖场', '避免淡季冷白造成空旷凉意'],
		featured: true,
	},
	{
		id: 'report-furniture',
		title: '专题 2 · 家具策略',
		summary: '在地定制为主，原品只强化关键触点，耐候与人因一起验证。',
		lead: '实施边界顾问',
		partners: ['经营与投资视角代理人', '运营时序顾问'],
		sourceTask: '来自任务 7 · 家具专题任务卡',
		points: ['语法五条：比例 / 座高 / 密度 / 材温 / 工艺', '在地定制为主，原品用于关键触点', '高湿与冬季冻融下须验证耐候', '淡季需有低成本易操作的保养方案', '同时适配夫妻阅读与亲子短停两类姿势'],
		featured: true,
	},
	{
		id: 'report-scale',
		title: '专题 3 · 尺度控制',
		summary: '公区高、客房稳、过渡低，开口与采光必须在夏冬和昼夜两条线上都成立。',
		lead: '空间设计总统筹',
		partners: ['实施边界顾问', '运营时序顾问'],
		sourceTask: '来自任务 8 · 尺度专题任务卡',
		points: ['公区高、客房稳、过渡低', '窗台低位见山', '结构与成本预警保留为待决项', '夏季重通风观景，冬季补冷桥验证', '昼间自然采光与夜间灯光接管需分别复核'],
		featured: true,
	},
	{
		id: 'report-public',
		title: '专题 4 · 公共社交组织',
		summary: '四节点组织，偶遇而非聚众，四时段和三类客群都要有落位。',
		lead: '轻度假旅程研究员',
		partners: ['社交心理研究员', '运营时序顾问'],
		sourceTask: '来自任务 9 · 公区专题任务卡',
		points: ['四节点：入口缓冲 / 早餐轻食 / 阅读独处 / 户外过渡廊', '可见不强制，偶遇而非聚众', '晨 / 白 / 晚 / 夜四时段各有照明与动线预设', '情侣 / 亲子 / 单人三类客群同时容纳', '淡季通过暖场灯光与局部启用维持活性'],
		featured: true,
	},
];

const EXPERT_REVIEW_ITEMS: ExpertReviewItem[] = [
	{
		id: 'review-pack',
		title: '任务书预览',
		summary: '命题说明、专题拆解、优先级与红线、待确认项、回溯索引必须完整露出。',
		group: '成果结构',
		checks: ['命题说明是否绑定 3.1 基线与 4.3 锁定方向', '四专题参数是否能独立回看', 'P0 / P1 / P2 与不可跨越红线是否显式', '待确认项是否带来源与后续检查点'],
		source: '对应 4.4 的任务书预览面板',
		featured: true,
	},
	{
		id: 'review-governance',
		title: '运行时治理',
		summary: '跨阶段推进、越权改写、结构变更未做影响分析时都要阻断。',
		group: '治理约束',
		checks: ['Gate Guardian：缺前置冻结 ID 时阻断', 'ContractValidator：缺 source_frozen_id 或越权改写时阻断', 'Impact Enforcer：结构变更未附影响分析时阻断'],
		source: '对应 4.4 的运行时治理提示',
		featured: true,
	},
	{
		id: 'review-method',
		title: '方法论一致性复核',
		summary: '冻结前最后 30 秒，确认终局目标、关键变量、动作顺序、失败点和回写路径都没跑偏。',
		group: '最终复核',
		checks: ['是否回答项目最终要什么', '是否写清关键变量 / 关键约束', '是否明确先后顺序与失败位置', '是否保留待确认项与回写路径', '是否解释用户为何来 / 选 / 复购 / 传播', '是否完成时间维度与人因维度验证'],
		source: '对应 3.S.1 前置审阅门与 4.4 复核联动',
		featured: true,
	},
	{
		id: 'review-freeze',
		title: '冻结边界与可回溯索引',
		summary: '哪些能直接改，哪些必须回到前一步，冻结后都要能回看来源与裁决过程。',
		group: '冻结说明',
		checks: ['核心命题与主要取舍不可直接改', '专题关键参数不可直接改', '文字表述、标签、缺口优先级可内联微调', '每条结论都要附来源阶段 / 主提 / 联提 / 用户确认轮次'],
		source: '对应 InitialDesignPack 冻结说明与可回溯索引',
		featured: true,
	},
];

export function CockpitPanel({
	moduleKey,
	preferredFileViewMode,
	sessionId,
	projectLabel,
	onProjectLabelChange,
	projectOverview,
	activeBoardSpace,
	onActiveBoardSpaceChange,
	onEnterBoardSpace,
	onEnterSandboxSpace,
	onOpenInspirationLibrary,
	onBackToAssets,
	onBoardVisualBriefChange,
	onBoardZoomChange,
	portfolioYearHeightScale = 1,
	onDssPageChange,
	onNodeClick,
	onCardClick,
	onSwitchModule,
	onOpenGeoWorkspace,
	className = '',
}: CockpitPanelProps) {
	const [decisionActiveView, setDecisionActiveView] = useState<ViewKey>('overview');
	const [fileQuery, setFileQuery] = useState('');
	const [fileViewMode, setFileViewMode] = useState<FileViewMode>('统一视图');
	const [activeFlow, setActiveFlow] = useState<string>(ALL_FLOW);
	const [activeSpace, setActiveSpace] = useState<string>(ALL_SPACE);
	const [activeAnchor, setActiveAnchor] = useState<string>(ALL_ANCHOR);
	const [activeTopic, setActiveTopic] = useState<string>(ALL_TOPIC);
	const [activeStage, setActiveStage] = useState<string>(ALL_STAGE);
	const [activeStatus, setActiveStatus] = useState<string>(ALL_STATUS);
	const [sortMode, setSortMode] = useState<SortMode>('相关性优先');
	const [pinnedTitles, setPinnedTitles] = useState<string[]>([]);
	const [fileDetailOpen, setFileDetailOpen] = useState(false);
	const [selectedFileTitle, setSelectedFileTitle] = useState<string>('');
	const [assetQuery, setAssetQuery] = useState('');
	const [assetCategory, setAssetCategory] = useState<string>('全部分类');
	const [assetSpace, setAssetSpace] = useState<string>('全部空间');
	const [assetBudget, setAssetBudget] = useState<string>('全部预算');
	const [assetTask, setAssetTask] = useState<ResourceTaskKey | '全部'>('全部');
	const [selectedAssetId, setSelectedAssetId] = useState<string>('');
	const [relatedAssetsOffset, setRelatedAssetsOffset] = useState(0);
	const [assetBasketSelections, setAssetBasketSelections] = useState<BasketSelectionItem[]>([]);
	const [inspirationLibraryItems, setInspirationLibraryItems] = useState<InspirationLibraryItem[]>([]);
	const [inspirationQuery, setInspirationQuery] = useState('');
	const [inspirationCategory, setInspirationCategory] = useState<string>('全部分类');
	const [inspirationEntityView, setInspirationEntityView] = useState<InspirationEntityView>('全部条目');
	const [filePresentationMode, setFilePresentationMode] = useState<FilePresentationMode>('卡片模式');
	const [boardCollections, setBoardCollections] = useState<BoardCollectionItem[]>([]);
	const [boardQuery, setBoardQuery] = useState('');
	const [boardSourceTab, setBoardSourceTab] = useState<BoardSourceTab>('radar');
	const [boardDeepBrowseTab, setBoardDeepBrowseTab] = useState<BoardDeepBrowseTab | null>(null);
	const [boardLibraryNavKey, setBoardLibraryNavKey] = useState<BoardLibraryNavKey | null>(null);
	const [boardLibrarySubcategory, setBoardLibrarySubcategory] = useState(ALL_BOARD_LIBRARY_SUBCATEGORY);
	const [boardDeepBrowseSizeLevel, setBoardDeepBrowseSizeLevel] = useState(3);
	const [boardCanvasItems, setBoardCanvasItems] = useState<BoardCanvasItem[]>([]);
	const [boardCanvasView, setBoardCanvasView] = useState(DEFAULT_BOARD_CANVAS_VIEW);
	const [boardCanvasBrightImageMap, setBoardCanvasBrightImageMap] = useState<Record<string, boolean>>({});
	const [boardCanvasMode, setBoardCanvasMode] = useState<BoardCanvasMode>('综合');
	const [boardGeneratedItems, setBoardGeneratedItems] = useState<BoardGeneratedItem[]>([]);
	const [boardGeneratedUnseenCount, setBoardGeneratedUnseenCount] = useState(0);
	const [boardGeneratedRoundFilter, setBoardGeneratedRoundFilter] = useState<BoardGeneratedRoundFilter>('全部');
	const [boardGeneratedTopicFilter, setBoardGeneratedTopicFilter] = useState<'全部专题' | BoardCanvasMode>('全部专题');
	const [boardSourceDetailItemId, setBoardSourceDetailItemId] = useState<string | null>(null);
	const [boardSourceDetailImageAspect, setBoardSourceDetailImageAspect] = useState<number | null>(null);
	const [boardSourceDetailImageBackdrop, setBoardSourceDetailImageBackdrop] = useState('#020617');
	const [boardVisualBriefs, setBoardVisualBriefs] = useState<Record<Exclude<BoardCanvasSpace, '全部'>, BoardVisualBrief>>(() =>
		SPACE_VIEW_ORDER.reduce<Record<Exclude<BoardCanvasSpace, '全部'>, BoardVisualBrief>>((acc, space) => {
			acc[space] = createSystemVisualBrief(space);
			return acc;
		}, {} as Record<Exclude<BoardCanvasSpace, '全部'>, BoardVisualBrief>)
	);
	const [spacePlanTopics, setSpacePlanTopics] = useState<Record<Exclude<BoardCanvasSpace, '全部'>, SpacePlanTopicState>>(() =>
		createDefaultSpacePlanTopicStates()
	);
	const [expandedBoardVisualBrief, setExpandedBoardVisualBrief] = useState(false);
	const [expandedBoardPlanBase, setExpandedBoardPlanBase] = useState(false);
	const [showBoardPlanOverlay, setShowBoardPlanOverlay] = useState(true);
	const [selectedBoardCanvasItemId, setSelectedBoardCanvasItemId] = useState<string | null>(null);
	const [expandedBoardSourceItemId, setExpandedBoardSourceItemId] = useState<string | null>(null);
	const [referenceEditDraft, setReferenceEditDraft] = useState<{
		target: 'source' | 'canvas';
		sourceId?: string;
		canvasItemId?: string;
		control: BoardReferenceControl;
	} | null>(null);
	const [boardSpaceItemCounts, setBoardSpaceItemCounts] = useState<Record<Exclude<BoardCanvasSpace, '全部'>, number>>({
		大堂: 0,
		餐厅: 0,
		客房: 0,
		公区: 0,
		连廊: 0,
		后勤: 0,
	});
	const [boardSpacePreviewItems, setBoardSpacePreviewItems] = useState<Record<Exclude<BoardCanvasSpace, '全部'>, { imageSrc: string; fallbackImageSrc: string; title: string } | null>>({
		大堂: null,
		餐厅: null,
		客房: null,
		公区: null,
		连廊: null,
		后勤: null,
	});
	const [boardHeaderHovered, setBoardHeaderHovered] = useState(false);
	const [fileHeaderCollapsed, setFileHeaderCollapsed] = useState(true);
	const [assetHeaderCollapsed, setAssetHeaderCollapsed] = useState(true);
	const [fileHeaderHovered, setFileHeaderHovered] = useState(false);
	const [assetHeaderHovered, setAssetHeaderHovered] = useState(false);
	const [spaceViewSectionCollapsed, setSpaceViewSectionCollapsed] = useState(false);
	const [otherViewSectionCollapsed, setOtherViewSectionCollapsed] = useState(false);
	const [inspirationModalOpen, setInspirationModalOpen] = useState(false);
	const [inspirationDraft, setInspirationDraft] = useState<InspirationLibraryDraft | null>(null);
	const [knowledgeEntries, setKnowledgeEntries] = useState<PersonalKnowledgeEntry[]>([]);
	const [knowledgeQuery, setKnowledgeQuery] = useState('');
	const [selectedKnowledgeEntryId, setSelectedKnowledgeEntryId] = useState<string>('');
	const [knowledgeDetailOpen, setKnowledgeDetailOpen] = useState(false);
	const [knowledgeTypeFilter, setKnowledgeTypeFilter] = useState<KnowledgeEntryType | '全部'>('全部');
	const [portfolioBubbleSizeMode, setPortfolioBubbleSizeMode] = useState<PortfolioBubbleSizeMode>('fee');
	const [portfolioChartWidth, setPortfolioChartWidth] = useState(0);
	const [designerProfile, setDesignerProfile] = useState<DesignerProfile | null>(null);
	const [dssProfileOpen, setDssProfileOpen] = useState(false);
	const [dssPage, setDssPage] = useState<DssPage>('sediment');
	const [dssQuickText, setDssQuickText] = useState('');
	const [dssQuickNewId, setDssQuickNewId] = useState<string | null>(null);
	const [boardCollectModalOpen, setBoardCollectModalOpen] = useState(false);
	const [boardCollectionDraft, setBoardCollectionDraft] = useState<BoardCollectionDraft | null>(null);
	const [assetDetailOpen, setAssetDetailOpen] = useState(false);
	const [selectedDetailImageId, setSelectedDetailImageId] = useState<string>('');
	const portfolioChartShellRef = useRef<HTMLDivElement | null>(null);
	const svgHeadingTextStyle = { fontFamily: 'inherit', fontSize: 16 };
	const svgBodyTextStyle = { fontFamily: 'inherit', fontSize: 13 };
	const svgLabelTextStyle = { fontFamily: 'inherit', fontSize: 13 };

	useEffect(() => {
		onDssPageChange?.(dssPage);
	}, [dssPage, onDssPageChange]);

	useEffect(() => {
		if (dssPage !== 'portfolio') return;
		const el = portfolioChartShellRef.current;
		if (!el || typeof ResizeObserver === 'undefined') return;
		const update = () => {
			const rectWidth = el.getBoundingClientRect().width;
			const nextWidth = Math.round(Math.max(el.clientWidth, rectWidth));
			if (nextWidth > 0) setPortfolioChartWidth(nextWidth);
		};
		update();
		const frameOne = window.requestAnimationFrame(update);
		const frameTwo = window.requestAnimationFrame(() => window.requestAnimationFrame(update));
		const observer = new ResizeObserver(() => update());
		observer.observe(el);
		return () => {
			window.cancelAnimationFrame(frameOne);
			window.cancelAnimationFrame(frameTwo);
			observer.disconnect();
		};
	}, [dssPage]);
	const [selectedDetailAnchorId, setSelectedDetailAnchorId] = useState<string>('');
	const [assetDetailAnchorPanelMode, setAssetDetailAnchorPanelMode] = useState<AssetDetailAnchorPanelMode>('expanded');
	const [assetAnchorEditMode, setAssetAnchorEditMode] = useState(false);
	const [resourceAnchorStore, setResourceAnchorStore] = useState<Record<string, ResourceImageAnchor[]> | null>(null);
	const [resourceAnchorDirty, setResourceAnchorDirty] = useState(false);
	const [draggingAnchorState, setDraggingAnchorState] = useState<{ imageId: string; anchorId: string } | null>(null);
	const [assetDetailAnchorRailStyle, setAssetDetailAnchorRailStyle] = useState<React.CSSProperties>({});
	const [assetDetailAnchorRailVisible, setAssetDetailAnchorRailVisible] = useState(false);
	const [assetDetailAnchorPanelStyle, setAssetDetailAnchorPanelStyle] = useState<React.CSSProperties>({});
	const [assetDetailWideViewport, setAssetDetailWideViewport] = useState(false);
	const [publicPictureNames, setPublicPictureNames] = useState<string[]>([]);
	const [isClient, setIsClient] = useState(false);
	const inspirationUploadInputRef = useRef<HTMLInputElement>(null);
	const assetDetailImageSectionRefs = useRef<Record<string, HTMLElement | null>>({});
	const assetDetailImageContainerRefs = useRef<Record<string, HTMLDivElement | null>>({});
	const assetDetailAnchorPanelRef = useRef<HTMLDivElement | null>(null);
	const assetDetailOverlayRef = useRef<HTMLDivElement | null>(null);
	const assetDetailImageFocusLockRef = useRef<{ imageId: string; expiresAt: number } | null>(null);
	const planUploadInputRef = useRef<HTMLInputElement | null>(null);
	const planViewerCanvasRef = useRef<HTMLDivElement | null>(null);
	const boardCanvasViewportRef = useRef<HTMLDivElement>(null);
	const boardCanvasItemsRef = useRef<BoardCanvasItem[]>(boardCanvasItems);
	const boardCanvasViewRef = useRef(boardCanvasView);
	const boardCanvasInteractionRef = useRef<BoardCanvasInteraction | null>(null);
	const boardCanvasClipboardRef = useRef<Omit<BoardCanvasItem, 'id' | 'addedAt'> | null>(null);
	const boardCanvasUndoStackRef = useRef<BoardCanvasItem[][]>([]);
	const boardCanvasRedoStackRef = useRef<BoardCanvasItem[][]>([]);
	const [expertView, setExpertView] = useState<ExpertWorkspaceKey>('assembly');
	const [expertQuery, setExpertQuery] = useState('');
	const [expertHeaderCollapsed, setExpertHeaderCollapsed] = useState(true);
	const [expertHeaderHovered, setExpertHeaderHovered] = useState(false);
	const [showExpertAdvanced, setShowExpertAdvanced] = useState(false);
	const [selectedExpertDetail, setSelectedExpertDetail] = useState<ExpertDetailSelection | null>(null);
	const [expertOnlyKeyItems, setExpertOnlyKeyItems] = useState(false);
	const [expertShowReserve, setExpertShowReserve] = useState(true);
	const [pendingPlanUploadSpace, setPendingPlanUploadSpace] = useState<Exclude<BoardCanvasSpace, '全部'> | null>(null);
	const [planUploadBusySpace, setPlanUploadBusySpace] = useState<Exclude<BoardCanvasSpace, '全部'> | null>(null);
	const [planViewerSpace, setPlanViewerSpace] = useState<Exclude<BoardCanvasSpace, '全部'> | null>(null);
	const [planViewerZoom, setPlanViewerZoom] = useState(1);
	const [planViewerTool, setPlanViewerTool] = useState<'select' | PlanAnnotationKind>('select');
	const [selectedPlanElementId, setSelectedPlanElementId] = useState<string | null>(null);
	const [planElementDrawMode, setPlanElementDrawMode] = useState<FloorPlanElementKind | null>(null);
	const [planDrawGeometryMode, setPlanDrawGeometryMode] = useState<FloorPlanGeometryType>('rect');
	const [planElementDraft, setPlanElementDraft] = useState<{ startX: number; startY: number; x: number; y: number; w: number; h: number } | null>(null);
	const [planPolygonDraftPoints, setPlanPolygonDraftPoints] = useState<FloorPlanPoint[]>([]);
	const [planPathDraftPoints, setPlanPathDraftPoints] = useState<FloorPlanPoint[]>([]);
	const [planAutoTraceBusy, setPlanAutoTraceBusy] = useState(false);
	const [planAutoTraceError, setPlanAutoTraceError] = useState<string | null>(null);

	const fileHeaderExpanded = !fileHeaderCollapsed || fileHeaderHovered;
	const assetHeaderExpanded = !assetHeaderCollapsed || assetHeaderHovered;
	const expertHeaderExpanded = !expertHeaderCollapsed || expertHeaderHovered;
	const boardLeftInsetClass = 'pl-[108px]';
	const anchorSummaryTextShadow = '0 1px 1px rgba(0,0,0,0.92), 0 1px 3.5px rgba(0,0,0,0.55)';
	const anchorSummaryBodyTextShadow = '0 1px 1px rgba(0,0,0,0.95), 0 2px 5px rgba(0,0,0,0.75)';
	const resolvedBoardSessionId = sessionId ?? 'global';
	const currentBoardSpace = activeBoardSpace ?? '全部';
	const isBoardOverview = currentBoardSpace === '全部';
	const resolvedProjectLabel = projectLabel ?? sessionId ?? '当前项目';
	const activeBoardVisualBrief = !isBoardOverview ? boardVisualBriefs[currentBoardSpace] : null;
	const activeSpacePlanView = !isBoardOverview ? SPACE_PLAN_VIEW_PRESETS[currentBoardSpace] : null;
	const activeSpacePlanTopic = !isBoardOverview ? spacePlanTopics[currentBoardSpace] : null;

	useEffect(() => {
		setIsClient(true);
		return () => setIsClient(false);
	}, []);

	useEffect(() => {
		if (!isClient || typeof window === 'undefined') return;
		const nextBriefs = SPACE_VIEW_ORDER.reduce<Record<Exclude<BoardCanvasSpace, '全部'>, BoardVisualBrief>>((acc, space) => {
			const systemBrief = createSystemVisualBrief(space);
			try {
				const raw = window.localStorage.getItem(buildBoardVisualBriefStorageKey(resolvedBoardSessionId, space));
				if (raw) {
					const parsed = JSON.parse(raw) as Partial<BoardVisualBrief>;
					acc[space] = {
						...systemBrief,
						...parsed,
						space,
						visualPrompt: typeof parsed.visualPrompt === 'string' && parsed.visualPrompt.trim() ? parsed.visualPrompt : systemBrief.visualPrompt,
						sourceRefs: Array.isArray(parsed.sourceRefs) && parsed.sourceRefs.length > 0 ? parsed.sourceRefs as BoardVisualBrief['sourceRefs'] : systemBrief.sourceRefs,
						mustKeep: Array.isArray(parsed.mustKeep) ? parsed.mustKeep : systemBrief.mustKeep,
						styleKeywords: Array.isArray(parsed.styleKeywords) ? parsed.styleKeywords : systemBrief.styleKeywords,
						materialKeywords: Array.isArray(parsed.materialKeywords) ? parsed.materialKeywords : systemBrief.materialKeywords,
						lightingKeywords: Array.isArray(parsed.lightingKeywords) ? parsed.lightingKeywords : systemBrief.lightingKeywords,
						negativeConstraints: Array.isArray(parsed.negativeConstraints) ? parsed.negativeConstraints : systemBrief.negativeConstraints,
						disabledTags: Array.isArray(parsed.disabledTags) ? parsed.disabledTags : [],
						lockedTags: Array.isArray(parsed.lockedTags) ? parsed.lockedTags : systemBrief.lockedTags,
					};
					return acc;
				}
			} catch (error) {
				console.error('[CockpitPanel] failed to restore visual brief:', error);
			}
			acc[space] = systemBrief;
			return acc;
		}, {} as Record<Exclude<BoardCanvasSpace, '全部'>, BoardVisualBrief>);

		setBoardVisualBriefs(nextBriefs);
	}, [isClient, resolvedBoardSessionId]);

	useEffect(() => {
		if (!isClient || typeof window === 'undefined') return;
		try {
			const raw = window.localStorage.getItem(buildSpacePlanTopicStorageKey(resolvedBoardSessionId));
			if (!raw) {
				setSpacePlanTopics(createDefaultSpacePlanTopicStates());
				return;
			}
			const parsed = JSON.parse(raw) as Partial<Record<Exclude<BoardCanvasSpace, '全部'>, SpacePlanTopicState>>;
			setSpacePlanTopics({
				...createDefaultSpacePlanTopicStates(),
				...parsed,
			});
		} catch (error) {
			console.error('[CockpitPanel] failed to restore space plan topics:', error);
			setSpacePlanTopics(createDefaultSpacePlanTopicStates());
		}
	}, [isClient, resolvedBoardSessionId]);

	useEffect(() => {
		if (!isClient || typeof window === 'undefined') return;
		window.localStorage.setItem(buildSpacePlanTopicStorageKey(resolvedBoardSessionId), JSON.stringify(spacePlanTopics));
	}, [isClient, resolvedBoardSessionId, spacePlanTopics]);

	useEffect(() => {
		if (!isClient || typeof window === 'undefined') return;
		for (const space of SPACE_VIEW_ORDER) {
			try {
				window.localStorage.setItem(
					buildBoardVisualBriefStorageKey(resolvedBoardSessionId, space),
					JSON.stringify(boardVisualBriefs[space])
				);
			} catch (error) {
				console.error('[CockpitPanel] failed to persist visual brief:', error);
			}
		}
	}, [boardVisualBriefs, isClient, resolvedBoardSessionId]);

	useEffect(() => {
		if (!isClient || typeof window === 'undefined') return;

		const updateViewportFlag = () => {
			setAssetDetailWideViewport(window.innerWidth >= 1280);
		};

		updateViewportFlag();
		window.addEventListener('resize', updateViewportFlag);
		return () => window.removeEventListener('resize', updateViewportFlag);
	}, [isClient]);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		try {
			const raw = window.localStorage.getItem(INSPIRATION_LIBRARY_STORAGE_KEY);
			if (!raw) return;
			const parsed = JSON.parse(raw) as InspirationLibraryItem[];
			if (Array.isArray(parsed)) {
				setInspirationLibraryItems(parsed);
			}
		} catch (error) {
			console.error('[CockpitPanel] failed to restore inspiration library:', error);
		}
	}, []);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		try {
			/* 旧键迁移：v1 → v2 (DSS 命名空间) */
			const legacyRaw = window.localStorage.getItem(PERSONAL_KNOWLEDGE_LEGACY_KEY);
			if (legacyRaw && !window.localStorage.getItem(PERSONAL_KNOWLEDGE_STORAGE_KEY)) {
				window.localStorage.setItem(PERSONAL_KNOWLEDGE_STORAGE_KEY, legacyRaw);
				window.localStorage.removeItem(PERSONAL_KNOWLEDGE_LEGACY_KEY);
			}
			/* 旧 demo-version 键迁移 */
			const legacyDemoKey = 'ipa.knowledge.private.demo-version';
			const legacyDemoVer = window.localStorage.getItem(legacyDemoKey);
			if (legacyDemoVer) {
				window.localStorage.removeItem(legacyDemoKey);
			}

			const demoVersion = window.localStorage.getItem(PERSONAL_KNOWLEDGE_DEMO_VERSION_KEY);
			if (demoVersion !== PERSONAL_KNOWLEDGE_DEMO_VERSION) {
				const initial = createInitialKnowledgeEntries();
				setKnowledgeEntries(initial);
				setSelectedKnowledgeEntryId(initial[0]?.id ?? '');
				window.localStorage.setItem(PERSONAL_KNOWLEDGE_STORAGE_KEY, JSON.stringify(initial));
				window.localStorage.setItem(PERSONAL_KNOWLEDGE_DEMO_VERSION_KEY, PERSONAL_KNOWLEDGE_DEMO_VERSION);
				return;
			}

			const raw = window.localStorage.getItem(PERSONAL_KNOWLEDGE_STORAGE_KEY);
			if (!raw) {
				const initial = createInitialKnowledgeEntries();
				setKnowledgeEntries(initial);
				setSelectedKnowledgeEntryId(initial[0]?.id ?? '');
				window.localStorage.setItem(PERSONAL_KNOWLEDGE_DEMO_VERSION_KEY, PERSONAL_KNOWLEDGE_DEMO_VERSION);
				return;
			}
			const parsed = JSON.parse(raw) as PersonalKnowledgeEntry[];
			if (Array.isArray(parsed) && parsed.length > 0) {
				setKnowledgeEntries(parsed);
				setSelectedKnowledgeEntryId(parsed[0]?.id ?? '');
				window.localStorage.setItem(PERSONAL_KNOWLEDGE_DEMO_VERSION_KEY, PERSONAL_KNOWLEDGE_DEMO_VERSION);
				return;
			}
			const initial = createInitialKnowledgeEntries();
			setKnowledgeEntries(initial);
			setSelectedKnowledgeEntryId(initial[0]?.id ?? '');
			window.localStorage.setItem(PERSONAL_KNOWLEDGE_DEMO_VERSION_KEY, PERSONAL_KNOWLEDGE_DEMO_VERSION);
		} catch (error) {
			console.error('[CockpitPanel] failed to restore personal knowledge:', error);
			const initial = createInitialKnowledgeEntries();
			setKnowledgeEntries(initial);
			setSelectedKnowledgeEntryId(initial[0]?.id ?? '');
			window.localStorage.setItem(PERSONAL_KNOWLEDGE_DEMO_VERSION_KEY, PERSONAL_KNOWLEDGE_DEMO_VERSION);
		}
	}, []);

	/* DSS: 加载设计师画像 */
	useEffect(() => {
		if (typeof window === 'undefined') return;
		try {
			const raw = window.localStorage.getItem(DSS_PROFILE_STORAGE_KEY);
			if (raw) {
				const parsed = JSON.parse(raw) as DesignerProfile;
				if (parsed && parsed.id) setDesignerProfile(parsed);
			}
		} catch (error) {
			console.error('[DSS] failed to restore designer profile:', error);
		}
	}, []);

	/* DSS: 持久化设计师画像 */
	useEffect(() => {
		if (typeof window === 'undefined' || !designerProfile) return;
		try {
			window.localStorage.setItem(DSS_PROFILE_STORAGE_KEY, JSON.stringify(designerProfile));
		} catch (error) {
			console.error('[DSS] failed to persist designer profile:', error);
		}
	}, [designerProfile]);

	useEffect(() => {
		if (typeof window === 'undefined') return;
		try {
			window.localStorage.setItem(PERSONAL_KNOWLEDGE_STORAGE_KEY, JSON.stringify(knowledgeEntries));
		} catch (error) {
			console.error('[CockpitPanel] failed to persist personal knowledge:', error);
		}
	}, [knowledgeEntries]);

	useEffect(() => {
		if (!isClient) return;
		try {
			window.localStorage.setItem(INSPIRATION_LIBRARY_STORAGE_KEY, JSON.stringify(inspirationLibraryItems));
		} catch (error) {
			console.error('[CockpitPanel] failed to persist inspiration library:', error);
		}
	}, [inspirationLibraryItems, isClient]);

	useEffect(() => {
		if (!isClient || typeof window === 'undefined') return;
		try {
			window.localStorage.setItem(
				buildBoardGenerationBeltStorageKey(resolvedBoardSessionId),
				JSON.stringify(boardGeneratedItems)
			);
		} catch (error) {
			console.error('[CockpitPanel] failed to persist generation belt:', error);
		}
	}, [boardGeneratedItems, isClient, resolvedBoardSessionId]);

	useEffect(() => {
		if (boardSourceTab === 'generated') {
			setBoardGeneratedUnseenCount(0);
		}
	}, [boardSourceTab]);

	useEffect(() => {
		boardCanvasItemsRef.current = boardCanvasItems;
	}, [boardCanvasItems]);

	useEffect(() => {
		boardCanvasViewRef.current = boardCanvasView;
	}, [boardCanvasView]);

	useEffect(() => {
		if (!preferredFileViewMode) return;
		setFileViewMode((prev) => (prev === preferredFileViewMode ? prev : preferredFileViewMode));
	}, [preferredFileViewMode]);

	useEffect(() => {
		if (typeof window === 'undefined' || !isClient) return;
		boardCanvasUndoStackRef.current = [];
		boardCanvasRedoStackRef.current = [];
		if (isBoardOverview) {
			setBoardCanvasItems([]);
			setBoardCanvasView(DEFAULT_BOARD_CANVAS_VIEW);
			setSelectedBoardCanvasItemId(null);
			return;
		}
		try {
			const rawItems = window.localStorage.getItem(
				buildBoardCanvasStorageKey(resolvedBoardSessionId, currentBoardSpace)
			);
			if (rawItems) {
				const parsedItems = JSON.parse(rawItems) as BoardCanvasItem[];
				setBoardCanvasItems(Array.isArray(parsedItems) ? parsedItems : []);
			} else {
				setBoardCanvasItems([]);
			}

			const rawView = window.localStorage.getItem(
				buildBoardCanvasViewStorageKey(resolvedBoardSessionId, currentBoardSpace)
			);
			if (rawView) {
				const parsedView = JSON.parse(rawView) as Partial<{ x: number; y: number; zoom: number }>;
				if (
					typeof parsedView?.x === 'number' &&
					typeof parsedView?.y === 'number' &&
					typeof parsedView?.zoom === 'number'
				) {
					setBoardCanvasView({
						x: parsedView.x,
						y: parsedView.y,
						zoom: parsedView.zoom,
					});
				} else {
					setBoardCanvasView(DEFAULT_BOARD_CANVAS_VIEW);
				}
			} else {
				setBoardCanvasView(DEFAULT_BOARD_CANVAS_VIEW);
			}
			setSelectedBoardCanvasItemId(null);
		} catch (error) {
			console.error('[CockpitPanel] failed to restore board canvas:', error);
		}
	}, [currentBoardSpace, isBoardOverview, isClient, resolvedBoardSessionId]);

	useEffect(() => {
		if (!isClient || isBoardOverview) return;
		try {
			window.localStorage.setItem(
				buildBoardCanvasStorageKey(resolvedBoardSessionId, currentBoardSpace),
				JSON.stringify(boardCanvasItems)
			);
			window.localStorage.setItem(
				buildBoardCanvasViewStorageKey(resolvedBoardSessionId, currentBoardSpace),
				JSON.stringify(boardCanvasView)
			);
		} catch (error) {
			console.error('[CockpitPanel] failed to persist board canvas:', error);
		}
	}, [boardCanvasItems, boardCanvasView, currentBoardSpace, isBoardOverview, isClient, resolvedBoardSessionId]);

	useEffect(() => {
		if (!isClient || typeof window === 'undefined') return;
		const nextCounts = BOARD_CANVAS_SPACE_OPTIONS.filter((space): space is Exclude<BoardCanvasSpace, '全部'> => space !== '全部')
			.reduce<Record<Exclude<BoardCanvasSpace, '全部'>, number>>((acc, space) => {
				try {
					const rawItems = window.localStorage.getItem(buildBoardCanvasStorageKey(resolvedBoardSessionId, space));
					const parsedItems = rawItems ? (JSON.parse(rawItems) as BoardCanvasItem[]) : [];
					acc[space] = Array.isArray(parsedItems) ? parsedItems.length : 0;
				} catch {
					acc[space] = 0;
				}
				return acc;
			}, { 大堂: 0, 餐厅: 0, 客房: 0, 公区: 0, 连廊: 0, 后勤: 0 });

		if (!isBoardOverview) {
			nextCounts[currentBoardSpace] = boardCanvasItems.length;
		}
		setBoardSpaceItemCounts(nextCounts);
	}, [boardCanvasItems, currentBoardSpace, isBoardOverview, isClient, resolvedBoardSessionId]);

	useEffect(() => {
		setSelectedExpertDetail(null);
	}, [expertOnlyKeyItems, expertQuery, expertShowReserve, expertView]);

	useEffect(() => {
		let cancelled = false;

		const loadPublicPictures = async () => {
			try {
				const response = await fetch('/api/public-pictures', { cache: 'no-store' });
				if (!response.ok) {
					throw new Error(`Failed to load public pictures: ${response.status}`);
				}

				const payload = (await response.json()) as { files?: string[] };
				if (!cancelled) {
					setPublicPictureNames(Array.isArray(payload.files) ? payload.files : []);
				}
			} catch (error) {
				console.error('[CockpitPanel] failed to load public pictures:', error);
				if (!cancelled) {
					setPublicPictureNames([]);
				}
			}
		};

		void loadPublicPictures();

		return () => {
			cancelled = true;
		};
	}, []);

	useEffect(() => {
		try {
			const raw = localStorage.getItem(FILE_VIEW_PREFS_KEY);
			if (!raw) return;
			const parsed = JSON.parse(raw) as Partial<{
				fileViewMode: FileViewMode | '综合视图' | '空间视图';
				filePresentationMode: FilePresentationMode;
				activeFlow: string;
				activeSpace: string;
				activeAnchor: string;
				activeTopic: string;
				activeStage: string;
				activeStatus: string;
				sortMode: SortMode;
				pinnedTitles: string[];
			}>;

			if (!preferredFileViewMode && parsed.fileViewMode) {
				if (parsed.fileViewMode === '综合视图' || parsed.fileViewMode === '空间视图') {
					setFileViewMode('统一视图');
				} else if (VIEW_MODES.includes(parsed.fileViewMode)) {
					setFileViewMode(parsed.fileViewMode);
				}
			}
			if (parsed.filePresentationMode && (['卡片模式', '文档索引'] as FilePresentationMode[]).includes(parsed.filePresentationMode)) {
				setFilePresentationMode(parsed.filePresentationMode);
			}
			if (parsed.activeFlow) setActiveFlow(parsed.activeFlow);
			if (parsed.activeSpace) setActiveSpace(parsed.activeSpace);
			if (parsed.activeAnchor) setActiveAnchor(parsed.activeAnchor);
			if (parsed.activeTopic) setActiveTopic(parsed.activeTopic);
			if (parsed.activeStage) setActiveStage(parsed.activeStage);
			if (parsed.activeStatus) setActiveStatus(parsed.activeStatus);
			if (parsed.sortMode && (['相关性优先', '引用热度', '最近更新', '标题 A-Z'] as SortMode[]).includes(parsed.sortMode)) {
				setSortMode(parsed.sortMode);
			}
			if (parsed.pinnedTitles && Array.isArray(parsed.pinnedTitles)) setPinnedTitles(parsed.pinnedTitles);
		} catch {
			// ignore invalid persisted state
		}
		if (preferredFileViewMode) {
			setFileViewMode(preferredFileViewMode);
		}
	}, [preferredFileViewMode]);

	useEffect(() => {
		try {
			localStorage.setItem(
				FILE_VIEW_PREFS_KEY,
				JSON.stringify({
					fileViewMode,
					filePresentationMode,
					activeFlow,
					activeSpace,
					activeAnchor,
					activeTopic,
					activeStage,
					activeStatus,
					sortMode,
					pinnedTitles,
				})
			);
		} catch {
			// ignore storage failure
		}
	}, [fileViewMode, filePresentationMode, activeFlow, activeSpace, activeAnchor, activeTopic, activeStage, activeStatus, sortMode, pinnedTitles]);

	const filteredFileCards = useMemo(() => {
		const query = fileQuery.trim().toLowerCase();
		const tokens = query.split(/\s+/).filter(Boolean);

		const scoreCard = (card: ProjectFileCard): number => {
			if (!query) return 0;
			const searchable = [
				card.title,
				card.desc,
				card.badge,
				card.flowCategory,
				card.stage,
				card.status,
				...card.domainTags,
			]
				.join(' ')
				.toLowerCase();

			let score = 0;
			if (card.title.toLowerCase().includes(query)) score += 20;
			if (searchable.includes(query)) score += 10;
			for (const token of tokens) {
				if (card.title.toLowerCase().includes(token)) score += 6;
				else if (searchable.includes(token)) score += 3;
			}
			return score;
		};

		return PROJECT_FILE_CARDS
			.map((card) => ({ card, score: scoreCard(card) }))
			.filter(({ card, score }) => {
				if (fileViewMode === '统一视图') {
					if (activeSpace !== ALL_SPACE && card.spaceScope !== activeSpace) return false;
					if (activeFlow !== ALL_FLOW && card.flowCategory !== activeFlow) return false;
					if (activeAnchor !== ALL_ANCHOR && card.objectAnchor !== activeAnchor) return false;
					if (activeTopic !== ALL_TOPIC && card.primaryTopic !== activeTopic) return false;
				}
				if (activeStage !== ALL_STAGE && card.stage !== activeStage) return false;
				if (activeStatus !== ALL_STATUS && card.status !== activeStatus) return false;
				if (query && score <= 0) return false;
				return true;
			})
			.sort((a, b) => {
				if (sortMode === '引用热度') return b.card.refCount - a.card.refCount;
				if (sortMode === '最近更新') return b.card.updatedAt.localeCompare(a.card.updatedAt);
				if (sortMode === '标题 A-Z') return a.card.title.localeCompare(b.card.title, 'zh-CN');
				if (query) {
					if (b.score !== a.score) return b.score - a.score;
					if (b.card.refCount !== a.card.refCount) return b.card.refCount - a.card.refCount;
				}
				return FLOW_ORDER.indexOf(a.card.flowCategory) - FLOW_ORDER.indexOf(b.card.flowCategory);
			})
			.map(({ card }) => card);
	}, [activeFlow, activeSpace, activeAnchor, activeTopic, activeStage, activeStatus, fileQuery, fileViewMode, sortMode]);

	const groupedCardsByView = useMemo(() => {
		const groups = new Map<string, ProjectFileCard[]>();
		const addToGroup = (key: string, card: ProjectFileCard) => {
			if (!groups.has(key)) groups.set(key, []);
			groups.get(key)?.push(card);
		};

		for (const card of filteredFileCards) {
			if (fileViewMode === '统一视图') {
				if (card.spaceScope === '全局') addToGroup(card.stage, card);
				else addToGroup(card.spaceScope, card);
			} else {
				addToGroup(card.status, card);
			}
		}

		const orderedKeys =
			fileViewMode === '统一视图'
				? [...SPACE_VIEW_ORDER, 'S1 意图显影', 'S2 分析扩展', 'S3 审阅裁决', 'S4 定向收束', 'S5 缺口补全', 'S6 定版冻结']
				: ['进行中', '待审', '已审', '已冻结', '待验证'];

		const result: Array<{ label: string; cards: ProjectFileCard[] }> = [];
		for (const key of orderedKeys) {
			const cards = groups.get(key);
			if (cards && cards.length > 0) result.push({ label: key, cards });
		}
		for (const [key, cards] of groups.entries()) {
			if (!orderedKeys.includes(key) && cards.length > 0) result.push({ label: key, cards });
		}
		return result;
	}, [fileViewMode, filteredFileCards]);

	const groupedSpaceCards = useMemo(
		() => groupedCardsByView.filter((group) => SPACE_VIEW_ORDER.includes(group.label as Exclude<ProjectFileCard['spaceScope'], '全局'>)),
		[groupedCardsByView]
	);

	const groupedOtherCards = useMemo(
		() => groupedCardsByView.filter((group) => !SPACE_VIEW_ORDER.includes(group.label as Exclude<ProjectFileCard['spaceScope'], '全局'>)),
		[groupedCardsByView]
	);

	const filteredKnowledgeEntries = useMemo(() => {
		const query = knowledgeQuery.trim().toLowerCase();
		return knowledgeEntries.filter((entry) => {
			if (knowledgeTypeFilter !== '全部' && entry.type !== knowledgeTypeFilter) return false;
			if (!query) return true;
			const haystack = [entry.title, entry.summary, entry.content, entry.type, entry.status, ...(entry.tags ?? [])].join(' ').toLowerCase();
			return haystack.includes(query);
		});
	}, [knowledgeEntries, knowledgeQuery, knowledgeTypeFilter]);

	const selectedKnowledgeEntry = useMemo(
		() => knowledgeEntries.find((entry) => entry.id === selectedKnowledgeEntryId) ?? null,
		[knowledgeEntries, selectedKnowledgeEntryId]
	);

	const upsertSelectedKnowledgeEntry = useCallback(
		(patch: Partial<PersonalKnowledgeEntry>) => {
			if (!selectedKnowledgeEntryId) return;
			setKnowledgeEntries((prev) =>
				prev.map((entry) =>
					entry.id === selectedKnowledgeEntryId
						? {
							...entry,
							...patch,
							updatedAt: new Date().toISOString(),
						}
						: entry
				)
			);
		},
		[selectedKnowledgeEntryId]
	);

	const handleCreateKnowledgeEntry = useCallback(() => {
		const next: PersonalKnowledgeEntry = {
			id: `knowledge-${Date.now()}`,
			title: '未命名知识',
			type: '经验',
			status: '草稿',
			summary: '',
			content: '',
			tags: [],
			sourceContext: '手动创建',
			updatedAt: new Date().toISOString(),
			scope: 'personal',
			publishLevel: '草稿',
			evidenceLinks: [],
		};
		setKnowledgeEntries((prev) => [next, ...prev]);
		setSelectedKnowledgeEntryId(next.id);
		setKnowledgeDetailOpen(true);
	}, []);

	const handleCaptureSedimentQuickNote = useCallback(() => {
		const title = dssQuickText.trim();
		if (!title) return;
		const id = `knowledge-${Date.now()}`;
		const entry: PersonalKnowledgeEntry = {
			id,
			title,
			type: '待分类',
			status: '草稿',
			summary: '',
			content: title,
			tags: [],
			sourceContext: '沉淀速记',
			updatedAt: new Date().toISOString(),
			scope: 'personal',
			publishLevel: '草稿',
			evidenceLinks: [],
		};
		setKnowledgeEntries((prev) => [entry, ...prev]);
		setDssQuickNewId(id);
		setDssQuickText('');
		setTimeout(() => setDssQuickNewId(null), 3000);
	}, [dssQuickText]);

	const handleDeleteKnowledgeEntry = useCallback(() => {
		if (!selectedKnowledgeEntryId) return;
		setKnowledgeEntries((prev) => {
			const next = prev.filter((entry) => entry.id !== selectedKnowledgeEntryId);
			setSelectedKnowledgeEntryId(next[0]?.id ?? '');
			if (next.length === 0) {
				setKnowledgeDetailOpen(false);
			}
			return next;
		});
	}, [selectedKnowledgeEntryId]);

	const matchesExpertQuery = useCallback(
		(values: Array<string | string[] | undefined>) => {
			const tokens = expertQuery.trim().toLowerCase().split(/\s+/).filter(Boolean);
			if (tokens.length === 0) return true;
			const haystack = values
				.flatMap((value) => (Array.isArray(value) ? value : [value]))
				.filter(Boolean)
				.join(' ')
				.toLowerCase();
			return tokens.every((token) => haystack.includes(token));
		},
		[expertQuery]
	);

	const expertTeamSections = useMemo(
		() =>
			EXPERT_TEAM_SECTIONS.map((section) => ({
				...section,
				items: section.items.filter((item) => {
					if (!expertShowReserve && item.status === '储备位') return false;
					if (expertOnlyKeyItems && !item.featured) return false;
					return matchesExpertQuery([item.title, item.summary, item.duty, item.trigger, item.source, item.status, item.tags]);
				}),
			})).filter((section) => section.items.length > 0),
		[expertOnlyKeyItems, expertShowReserve, matchesExpertQuery]
	);

	const expertTaskSections = useMemo(
		() =>
			EXPERT_TASK_SECTIONS.map((section) => ({
				...section,
				items: section.items.filter((item) => {
					if (expertOnlyKeyItems && !item.featured) return false;
					return matchesExpertQuery([item.title, item.mission, item.status, item.team, item.outputs, item.checks]);
				}),
			})).filter((section) => section.items.length > 0),
		[expertOnlyKeyItems, matchesExpertQuery]
	);

	const expertReportItems = useMemo(
		() =>
			EXPERT_REPORT_ITEMS.filter((item) => {
				if (expertOnlyKeyItems && !item.featured) return false;
				return matchesExpertQuery([item.title, item.summary, item.lead, item.partners, item.sourceTask, item.points]);
			}),
		[expertOnlyKeyItems, matchesExpertQuery]
	);

	const expertReviewItems = useMemo(
		() =>
			EXPERT_REVIEW_ITEMS.filter((item) => {
				if (expertOnlyKeyItems && !item.featured) return false;
				return matchesExpertQuery([item.title, item.summary, item.group, item.source, item.checks]);
			}),
		[expertOnlyKeyItems, matchesExpertQuery]
	);

	const expertSummary = useMemo(
		() => ({
			activeRoles: EXPERT_TEAM_SECTIONS.flatMap((section) => section.items).filter((item) => item.status === '当前激活').length,
			reserveRoles: EXPERT_TEAM_SECTIONS.flatMap((section) => section.items).filter((item) => item.status === '储备位').length,
			tasks: EXPERT_TASK_SECTIONS.flatMap((section) => section.items).length,
			reports: EXPERT_REPORT_ITEMS.length,
			review: EXPERT_REVIEW_ITEMS.length,
		}),
		[]
	);

	const expertRoleLookup = useMemo(
		() =>
			new Map(
				EXPERT_TEAM_SECTIONS.flatMap((section) => section.items).map((item) => [item.id, item] as const)
			),
		[]
	);
	const expertTaskLookup = useMemo(
		() =>
			new Map(
				EXPERT_TASK_SECTIONS.flatMap((section) => section.items).map((item) => [item.id, item] as const)
			),
		[]
	);
	const expertReportLookup = useMemo(() => new Map(EXPERT_REPORT_ITEMS.map((item) => [item.id, item] as const)), []);
	const expertReviewLookup = useMemo(() => new Map(EXPERT_REVIEW_ITEMS.map((item) => [item.id, item] as const)), []);
	const selectedExpertDetailData = useMemo(() => {
		if (!selectedExpertDetail) return null;
		if (selectedExpertDetail.kind === 'role') return expertRoleLookup.get(selectedExpertDetail.id) ?? null;
		if (selectedExpertDetail.kind === 'task') return expertTaskLookup.get(selectedExpertDetail.id) ?? null;
		if (selectedExpertDetail.kind === 'report') return expertReportLookup.get(selectedExpertDetail.id) ?? null;
		return expertReviewLookup.get(selectedExpertDetail.id) ?? null;
	}, [expertReportLookup, expertReviewLookup, expertRoleLookup, expertTaskLookup, selectedExpertDetail]);
	const expertDetailViewModel = useMemo(() => {
		if (!selectedExpertDetail || !selectedExpertDetailData) return null;

		if (selectedExpertDetail.kind === 'role') {
			const item = selectedExpertDetailData as ExpertTeamRoleItem;
			return {
				title: item.title,
				eyebrow: '团队角色详情',
				summary: item.summary,
				primaryMeta: [
					{ label: '当前状态', value: item.status },
					{ label: '触发时机', value: item.trigger },
					{ label: '来源', value: item.source },
				],
				sections: [
					{ title: '核心职责', items: [item.duty] },
					{ title: '标签', items: item.tags },
				],
				actionLabel: '插入当前项目',
			};
		}

		if (selectedExpertDetail.kind === 'task') {
			const item = selectedExpertDetailData as ExpertTaskItem;
			return {
				title: item.title,
				eyebrow: `任务 ${item.order}`,
				summary: item.mission,
				primaryMeta: [
					{ label: '执行状态', value: item.status },
					{ label: '责任团队', value: item.team.join(' · ') },
				],
				sections: [
					{ title: '输出物', items: item.outputs },
					{ title: '校验标准', items: item.checks },
				],
				actionLabel: '插入当前项目',
			};
		}

		if (selectedExpertDetail.kind === 'report') {
			const item = selectedExpertDetailData as ExpertReportItem;
			return {
				title: item.title,
				eyebrow: '专题策略确认',
				summary: item.summary,
				primaryMeta: [
					{ label: '主提', value: item.lead },
					{ label: '联提', value: item.partners.join(' · ') },
					{ label: '来源任务', value: item.sourceTask },
				],
				sections: [{ title: '确认要点', items: item.points }],
				actionLabel: '写入当前项目',
			};
		}

		const item = selectedExpertDetailData as ExpertReviewItem;
		return {
			title: item.title,
			eyebrow: item.group,
			summary: item.summary,
			primaryMeta: [
				{ label: '分组', value: item.group },
				{ label: '来源', value: item.source },
			],
			sections: [{ title: '冻结检查项', items: item.checks }],
			actionLabel: '查看冻结项',
		};
	}, [selectedExpertDetail, selectedExpertDetailData]);

	const activeExpertResultCount = useMemo(() => {
		if (expertView === 'assembly') return expertTeamSections.reduce((sum, section) => sum + section.items.length, 0);
		if (expertView === 'tasks') return expertTaskSections.reduce((sum, section) => sum + section.items.length, 0);
		if (expertView === 'reports') return expertReportItems.length;
		return expertReviewItems.length;
	}, [expertReportItems.length, expertReviewItems.length, expertTaskSections, expertTeamSections, expertView]);

	const currentWorkset = useMemo(() => {
		const pinnedCards = pinnedTitles
			.map((title) => PROJECT_FILE_CARDS.find((item) => item.title === title))
			.filter(Boolean) as ProjectFileCard[];
		const topReferenced = [...filteredFileCards].sort((a, b) => b.refCount - a.refCount).slice(0, 2);
		const frozen = filteredFileCards.find((item) => item.status === '已冻结');
		const activeStageCard = filteredFileCards.find((item) => activeStage !== ALL_STAGE && item.stage === activeStage);
		const merged = [...pinnedCards, activeStageCard, frozen, ...topReferenced].filter(Boolean) as ProjectFileCard[];
		return Array.from(new Map(merged.map((item) => [item.title, item])).values()).slice(0, 4);
	}, [activeStage, filteredFileCards, pinnedTitles]);

	const togglePin = (title: string) => {
		setPinnedTitles((prev) => (prev.includes(title) ? prev.filter((item) => item !== title) : [...prev, title]));
	};

	const applyWorksetFilter = (title: string) => {
		setFileQuery(title);
	};

	const usablePublicPictureNames = useMemo(() => {
		const nonSvg = publicPictureNames.filter((name) => !name.toLowerCase().endsWith('.svg'));
		return nonSvg.length > 0 ? nonSvg : publicPictureNames;
	}, [publicPictureNames]);

	const fallbackPublicPictureSrc = useMemo(() => {
		const firstPublicPicture = usablePublicPictureNames[0];
		return firstPublicPicture ? buildPublicPictureUrl(firstPublicPicture) : '';
	}, [usablePublicPictureNames]);
	const boardGenerationDemoImageNames = BOARD_GENERATION_DEMO_IMAGE_NAMES as readonly string[];

	const mockBoardGeneratedItems = useMemo<BoardGeneratedItem[]>(() => {
		if (boardGenerationDemoImageNames.length === 0 && usablePublicPictureNames.length === 0 && !fallbackPublicPictureSrc) {
			return [];
		}

		return hydrateBoardGeneratedMockSources(
			MOCK_BOARD_GENERATION_SEEDS.map((seed, index) => {
			const pictureName = usablePublicPictureNames[index % Math.max(usablePublicPictureNames.length, 1)];
			const imageSrc = pictureName
					? buildPublicPictureUrl(pictureName)
					: fallbackPublicPictureSrc;
			const createdAt = new Date(Date.now() - (index + 1) * 1000 * 60 * 37).toISOString();

			return {
				id: `board-generated-mock-${seed.space}-${seed.generationRound}-${index}`,
				sessionId: resolvedBoardSessionId,
				space: seed.space,
				topicScope: seed.topicScope,
				generationRound: seed.generationRound,
				createdAt,
				promptSummary: seed.promptSummary,
				sourceContext: seed.sourceContext,
				status: seed.status,
				title: seed.title,
				imageSrc,
				fallbackImageSrc: fallbackPublicPictureSrc || imageSrc,
				expertName: '方案高参',
				sourceImageId: `mock-image-${index}`,
			};
			}),
			fallbackPublicPictureSrc
		);
	}, [fallbackPublicPictureSrc, resolvedBoardSessionId, usablePublicPictureNames]);

	useEffect(() => {
		if (typeof window === 'undefined' || !isClient) return;
		try {
			const raw = window.localStorage.getItem(buildBoardGenerationBeltStorageKey(resolvedBoardSessionId));
			if (!raw) {
				setBoardGeneratedItems(mockBoardGeneratedItems);
				return;
			}
			const parsed = JSON.parse(raw) as BoardGeneratedItem[];
			if (!Array.isArray(parsed) || parsed.length === 0) {
				setBoardGeneratedItems(mockBoardGeneratedItems);
				return;
			}
			setBoardGeneratedItems(
				mergeBoardGeneratedItemsWithMockSeeds(
					hydrateBoardGeneratedMockSources(parsed, fallbackPublicPictureSrc),
					mockBoardGeneratedItems
				)
			);
		} catch (error) {
			console.error('[CockpitPanel] failed to restore generation belt:', error);
			setBoardGeneratedItems(mockBoardGeneratedItems);
		}
	}, [fallbackPublicPictureSrc, isClient, mockBoardGeneratedItems, resolvedBoardSessionId]);

	const resourceItems = useMemo<ResourceCardItem[]>(
		() =>
			RESOURCE_ITEMS.map((item, index) => {
				const configuredImageNames = item.imageNames ?? [];
				const imageCollection = item.imageCollection ?? 'default';
				const hasExplicitSystemPictureSeries = configuredImageNames.length > 0;
				const localPictureSrc = item.localPictureName ? buildPublicPictureUrl(item.localPictureName) : '';
				const normalizedSourceType: ResourceSourceType = item.sourceType ?? (index % 3 === 0 ? 'system' : 'user');
				const normalizedSourceName =
					item.sourceName ?? (normalizedSourceType === 'system' ? '设计知外' : `用户 ${String(index + 1).padStart(2, '0')}`);
				const normalizedRecommendCount = item.recommendCount ?? 20 + ((index * 17) % 180);
				const normalizedFavoriteQuoteCount = item.favoriteQuoteCount ?? 80 + ((index * 73) % 2400);
				const normalizedQuoteCount = item.quoteCount ?? 10 + ((index * 29) % 520);
				const imageSeries: ResourceSeriesImage[] = hasExplicitSystemPictureSeries
					? configuredImageNames.map((name, pictureIndex) => ({
						id: `${item.id}-series-${pictureIndex}`,
						name,
						src: buildPublicPictureUrl(name, imageCollection),
						fallbackSrc: item.fallbackImageSrc || buildPublicPictureUrl(name, imageCollection),
					}))
					: [
						{
							id: `${item.id}-cover`,
							name: item.title,
							src: localPictureSrc || (isSystemManagedResourceSrc(item.imageSrc) ? item.imageSrc : item.fallbackImageSrc),
							fallbackSrc: localPictureSrc || item.fallbackImageSrc,
						},
					];

				return {
					...item,
					sourceType: normalizedSourceType,
					sourceName: normalizedSourceName,
					recommendCount: normalizedRecommendCount,
					favoriteQuoteCount: normalizedFavoriteQuoteCount,
					quoteCount: normalizedQuoteCount,
					coverImageSrc: imageSeries[0]?.src ?? item.fallbackImageSrc,
					imageSeries,
				};
			}),
		[]
	);

	const resourceAnchorsByImageId = useMemo<Record<string, ResourceImageAnchor[]>>(
		() =>
			resourceItems.reduce<Record<string, ResourceImageAnchor[]>>((acc, resource, resourceIndex) => {
				const blueprint = getResourceAnchorBlueprint(resource);
				resource.imageSeries.forEach((image, imageIndex) => {
					const positions = RESOURCE_ANCHOR_POSITION_PRESETS[(resourceIndex + imageIndex) % RESOURCE_ANCHOR_POSITION_PRESETS.length];
					acc[image.id] = blueprint.map((entry, anchorIndex) => ({
						id: `${image.id}-anchor-${anchorIndex}`,
						resourceId: resource.id,
						imageId: image.id,
						x: positions[anchorIndex]?.x ?? 0.5,
						y: positions[anchorIndex]?.y ?? 0.5,
						type: entry.type,
						title: entry.title,
						summary: entry.summary,
						tags: resource.tags.slice(anchorIndex, anchorIndex + 3).concat(resource.category).slice(0, 4),
						space: resource.space,
						topic: entry.topic,
						quotedReason: entry.quotedReason,
						anchorMode: entry.anchorMode,
						evidenceLevel: entry.evidenceLevel,
						insights: createAnchorInsights(resource, entry, anchorIndex),
						origin: 'system',
					}));
				});
				return acc;
			}, {}),
		[resourceItems]
	);

	const activeResourceAnchorsByImageId = resourceAnchorStore ?? resourceAnchorsByImageId;

	useEffect(() => {
		if (!isClient) return;

		setInspirationLibraryItems((prev) => {
			let changed = false;
			const next = prev.map((item) => {
				if (!isResourceRadarSourceLabel(item.sourceLabel) || !item.resourceId) return item;

				const resource = resourceItems.find((entry) => entry.id === item.resourceId);
				if (!resource) return item;

				const fallbackImage =
					resource.imageSeries.find((image) => image.id === item.imageId) ??
					resource.imageSeries[0] ??
					null;
				if (!fallbackImage) return item;

				const nextImage =
					(item.imageId ? resource.imageSeries.find((image) => image.id === item.imageId) : null) ??
					fallbackImage;
				const nextAnchor =
					item.anchorId && item.imageId
						? (activeResourceAnchorsByImageId[item.imageId] ?? []).find((anchor) => anchor.id === item.anchorId) ?? null
						: null;
				const nextInsight =
					item.insightId && nextAnchor
						? nextAnchor.insights.find((insight) => insight.id === item.insightId) ?? null
						: null;
				const nextTitle =
					item.itemType === 'insight'
						? nextInsight?.title ?? item.title
						: item.itemType === 'anchor'
							? nextAnchor?.title ?? item.title
							: `${resource.title} · ${nextImage.name}`;
				const nextDesc =
					item.itemType === 'insight'
						? nextInsight
							? `${nextInsight.summary}${nextInsight.actionHint ? `\n\n执行建议：${nextInsight.actionHint}` : ''}${nextInsight.riskHint ? `\n\n风险提醒：${nextInsight.riskHint}` : ''}`
							: item.desc
						: item.itemType === 'anchor'
							? nextAnchor
								? `${nextAnchor.summary}\n\n引用理由：${nextAnchor.quotedReason}`
								: item.desc
							: resource.desc;
				const nextCategory =
					item.itemType === 'insight'
						? `${resource.category} / ${nextAnchor?.type ?? item.anchorType ?? '锚点'} / ${nextInsight?.type ?? item.insightType ?? '解读'}`
						: item.itemType === 'anchor'
							? `${resource.category} / ${nextAnchor?.type ?? item.anchorType ?? '锚点'}`
							: resource.category;
				const nextTags =
					item.itemType === 'insight'
						? [...(nextAnchor?.tags ?? item.tags), nextInsight?.type ?? item.insightType ?? '解读'].slice(0, 6)
						: item.itemType === 'anchor'
							? nextAnchor?.tags ?? item.tags
							: resource.tags;

				const migratedItem: InspirationLibraryItem = {
					...item,
					entityType:
						item.itemType === 'insight' ? 'insight' : item.itemType === 'anchor' ? 'anchor' : 'image',
					sourceTrace: buildResourceSourceTrace({
						projectId: resource.id,
						imageId: nextImage.id,
						anchorId: nextAnchor?.id ?? item.anchorId,
						insightId: nextInsight?.id ?? item.insightId,
					}),
					title: nextTitle,
					imageId: nextImage.id,
					imageName: nextImage.name,
					imageSrc: nextImage.src,
					fallbackImageSrc: nextImage.fallbackSrc,
					desc: nextDesc,
					category: nextCategory,
					tags: nextTags,
					resourceTitle: resource.title,
					anchorType: nextAnchor?.type ?? item.anchorType,
					anchorSummary: nextAnchor?.summary ?? item.anchorSummary,
					anchorMode: nextAnchor?.anchorMode ?? item.anchorMode,
					anchorX: nextAnchor?.x ?? item.anchorX,
					anchorY: nextAnchor?.y ?? item.anchorY,
					anchorOrigin: nextAnchor?.origin ?? item.anchorOrigin,
					evidenceLevel: nextInsight?.evidenceLevel ?? nextAnchor?.evidenceLevel ?? item.evidenceLevel,
					insightId: nextInsight?.id ?? item.insightId,
					insightType: nextInsight?.type ?? item.insightType,
					insightTitle: nextInsight?.title ?? item.insightTitle,
					insightSummary: nextInsight?.summary ?? item.insightSummary,
				};

				if (JSON.stringify(migratedItem) !== JSON.stringify(item)) {
					changed = true;
					return migratedItem;
				}

				return item;
			});

			return changed ? next : prev;
		});
	}, [activeResourceAnchorsByImageId, isClient, resourceItems]);

	useEffect(() => {
		if (!isClient || typeof window === 'undefined') return;
		const nextPreviews = BOARD_CANVAS_SPACE_OPTIONS.filter((space): space is Exclude<BoardCanvasSpace, '全部'> => space !== '全部')
			.reduce<Record<Exclude<BoardCanvasSpace, '全部'>, { imageSrc: string; fallbackImageSrc: string; title: string } | null>>((acc, space) => {
				let preview: { imageSrc: string; fallbackImageSrc: string; title: string } | null = null;
				try {
					const rawItems = window.localStorage.getItem(buildBoardCanvasStorageKey(resolvedBoardSessionId, space));
					const parsedItems = rawItems ? (JSON.parse(rawItems) as BoardCanvasItem[]) : [];
					if (Array.isArray(parsedItems) && parsedItems.length > 0) {
						preview = {
							imageSrc: parsedItems[0].imageSrc,
							fallbackImageSrc: parsedItems[0].fallbackImageSrc,
							title: parsedItems[0].title,
						};
					}
				} catch {
					preview = null;
				}

				if (!preview) {
					const resourcePreview =
						resourceItems.find((item) => item.space === space) ??
						resourceItems.find((item) => item.space === '全局') ??
						null;
					if (resourcePreview) {
						preview = {
							imageSrc: resourcePreview.coverImageSrc,
							fallbackImageSrc: resourcePreview.fallbackImageSrc,
							title: resourcePreview.title,
						};
					}
				}

				acc[space] = preview;
				return acc;
			}, { 大堂: null, 餐厅: null, 客房: null, 公区: null, 连廊: null, 后勤: null });

		if (!isBoardOverview && boardCanvasItems.length > 0) {
			nextPreviews[currentBoardSpace] = {
				imageSrc: boardCanvasItems[0].imageSrc,
				fallbackImageSrc: boardCanvasItems[0].fallbackImageSrc,
				title: boardCanvasItems[0].title,
			};
		}

		setBoardSpacePreviewItems(nextPreviews);
	}, [boardCanvasItems, currentBoardSpace, isBoardOverview, isClient, resolvedBoardSessionId, resourceItems]);

	useEffect(() => {
		if (!isClient || typeof window === 'undefined') return;
		try {
			const raw = window.localStorage.getItem(RESOURCE_ANCHOR_STORAGE_KEY);
			if (!raw) {
				setResourceAnchorStore(resourceAnchorsByImageId);
				return;
			}
			const parsed = JSON.parse(raw) as Record<string, ResourceImageAnchor[]>;
			const normalized = Object.fromEntries(
				Object.entries(parsed).map(([imageId, anchors]) => [
					imageId,
					(anchors ?? []).map((anchor) =>
						normalizeResourceAnchor(
							anchor,
							(resourceAnchorsByImageId[imageId] ?? []).find((entry) => entry.id === anchor.id) ?? null
						)
					),
				])
			) as Record<string, ResourceImageAnchor[]>;
			setResourceAnchorStore({
				...resourceAnchorsByImageId,
				...normalized,
			});
		} catch {
			setResourceAnchorStore(resourceAnchorsByImageId);
		}
	}, [isClient, resourceAnchorsByImageId]);

	const filteredAssets = useMemo(() => {
		const query = assetQuery.trim().toLowerCase();
		return resourceItems.filter((item) => {
			if (assetCategory !== '全部分类' && item.category !== assetCategory) return false;
			if (assetSpace !== '全部空间' && item.space !== assetSpace) return false;
			if (assetBudget !== '全部预算' && item.budgetBand !== assetBudget) return false;
			if (!query) return true;
			const haystack = [item.title, item.brand, item.series, item.desc, item.category, item.space, item.budgetBand, ...item.tags].join(' ').toLowerCase();
			return haystack.includes(query);
		});
	}, [assetBudget, assetCategory, assetQuery, assetSpace, resourceItems]);

	const selectedFileCard = useMemo(
		() => PROJECT_FILE_CARDS.find((item) => item.title === selectedFileTitle) ?? null,
		[selectedFileTitle]
	);

	useEffect(() => {
		if (!filteredAssets.length) {
			setSelectedAssetId('');
			return;
		}
		if (!selectedAssetId || !filteredAssets.some((item) => item.id === selectedAssetId)) {
			setSelectedAssetId(filteredAssets[0].id);
		}
	}, [filteredAssets, selectedAssetId]);

	const selectedAsset = useMemo(() => resourceItems.find((item) => item.id === selectedAssetId) ?? null, [resourceItems, selectedAssetId]);

	useEffect(() => {
		if (!selectedAsset) {
			setSelectedDetailImageId('');
			return;
		}

		if (!selectedDetailImageId || !selectedAsset.imageSeries.some((image) => image.id === selectedDetailImageId)) {
			setSelectedDetailImageId(selectedAsset.imageSeries[0]?.id ?? '');
		}
	}, [selectedAsset, selectedDetailImageId]);

	useEffect(() => {
		if (!assetDetailOpen || !selectedAsset || typeof window === 'undefined') return;

		const sectionEntries = selectedAsset.imageSeries
			.map((image) => ({
				imageId: image.id,
				element: assetDetailImageSectionRefs.current[image.id],
			}))
			.filter((entry): entry is { imageId: string; element: HTMLElement } => Boolean(entry.element));

		if (sectionEntries.length === 0) return;

		const observer = new window.IntersectionObserver(
			(entries) => {
				const visibleEntries = entries
					.filter((entry) => entry.isIntersecting)
					.sort((a, b) => b.intersectionRatio - a.intersectionRatio);

				const topEntry = visibleEntries[0];
				if (!topEntry) return;

				const nextImageId = sectionEntries.find((entry) => entry.element === topEntry.target)?.imageId;
				if (nextImageId) {
					const focusLock = assetDetailImageFocusLockRef.current;
					if (focusLock) {
						if (focusLock.expiresAt <= Date.now()) {
							assetDetailImageFocusLockRef.current = null;
						} else if (focusLock.imageId !== nextImageId) {
							return;
						}
					}
					setSelectedDetailImageId((current) => (current === nextImageId ? current : nextImageId));
				}
			},
			{
				root: null,
				threshold: [0.35, 0.55, 0.75],
				rootMargin: '-18% 0px -18% 0px',
			}
		);

		for (const entry of sectionEntries) {
			observer.observe(entry.element);
		}

		return () => observer.disconnect();
	}, [assetDetailOpen, selectedAsset]);

	const assetBasisTone = (risk: ResourceRisk) => {
		if (risk === '高') return 'bg-rose-50 border-rose-100 text-rose-700';
		if (risk === '中') return 'bg-amber-50 border-amber-100 text-amber-700';
		return 'bg-emerald-50 border-emerald-100 text-emerald-700';
	};

	const handleResourceImageError = (event: React.SyntheticEvent<HTMLImageElement>) => {
		const fallbackSrc = event.currentTarget.dataset.fallbackSrc;
		if (!fallbackSrc || event.currentTarget.src.endsWith(fallbackSrc)) return;
		event.currentTarget.src = fallbackSrc;
	};

	const assetHoverTone = () => 'bg-black/18';

	const basketItems = useMemo(
		() => assetBasketSelections,
		[assetBasketSelections]
	);

	const basketSummary = useMemo(() => {
		const highRiskCount = basketItems.filter((item) => item.risk === '高').length;
		const avgLeadTime = basketItems.length
			? Math.round(basketItems.reduce((sum, item) => sum + item.leadTimeDays, 0) / basketItems.length)
			: 0;
		return { highRiskCount, avgLeadTime };
	}, [basketItems]);

	const inspirationCategoryOptions = useMemo(() => {
		const categories = Array.from(new Set(inspirationLibraryItems.map((item) => item.category.trim()).filter(Boolean)));
		return ['全部分类', ...categories];
	}, [inspirationLibraryItems]);

	const inspirationEntityCounts = useMemo(() => {
		return inspirationLibraryItems.reduce(
			(acc, item) => {
				const entityType = item.entityType ?? (item.itemType === 'insight' ? 'insight' : item.itemType === 'anchor' ? 'anchor' : 'image');
				acc.全部条目 += 1;
				if (entityType === 'project') acc.项目包 += 1;
				if (entityType === 'image') acc.单图 += 1;
				if (entityType === 'anchor') acc.锚点 += 1;
				if (entityType === 'insight') acc.解读 += 1;
				return acc;
			},
			{ 全部条目: 0, 项目包: 0, 单图: 0, 锚点: 0, 解读: 0 } as Record<InspirationEntityView, number>
		);
	}, [inspirationLibraryItems]);

	const filteredInspirationLibraryItems = useMemo(() => {
		const query = inspirationQuery.trim().toLowerCase();
		return [...inspirationLibraryItems]
			.filter((item) => {
				const entityType = item.entityType ?? (item.itemType === 'insight' ? 'insight' : item.itemType === 'anchor' ? 'anchor' : 'image');
				if (inspirationCategory !== '全部分类' && item.category !== inspirationCategory) return false;
				if (
					(inspirationEntityView === '项目包' && entityType !== 'project') ||
					(inspirationEntityView === '单图' && entityType !== 'image') ||
					(inspirationEntityView === '锚点' && entityType !== 'anchor') ||
					(inspirationEntityView === '解读' && entityType !== 'insight')
				) {
					return false;
				}
				if (!query) return true;
				const haystack = [
					item.title,
					item.desc,
					item.category,
					item.sourceLabel,
					item.anchorSummary,
					item.insightSummary,
					item.insightTitle,
					item.insightType,
					...item.tags,
				]
					.join(' ')
					.toLowerCase();
				return haystack.includes(query);
			})
			.sort((a, b) => b.addedAt.localeCompare(a.addedAt));
	}, [inspirationCategory, inspirationEntityView, inspirationLibraryItems, inspirationQuery]);

	const openFileDetail = useCallback((card: ProjectFileCard) => {
		setSelectedFileTitle(card.title);
		setFileDetailOpen(true);
	}, []);

	const closeFileDetail = useCallback(() => {
		setFileDetailOpen(false);
	}, []);

	const openExpertDetail = useCallback((detail: ExpertDetailSelection) => {
		setSelectedExpertDetail(detail);
	}, []);

	const closeExpertDetail = useCallback(() => {
		setSelectedExpertDetail(null);
	}, []);

	const selectedDetailImage = useMemo(
		() => selectedAsset?.imageSeries.find((image) => image.id === selectedDetailImageId) ?? selectedAsset?.imageSeries[0] ?? null,
		[selectedAsset, selectedDetailImageId]
	);

	const selectedDetailImageIndex = useMemo(() => {
		if (!selectedAsset || !selectedDetailImage) return -1;
		return selectedAsset.imageSeries.findIndex((image) => image.id === selectedDetailImage.id);
	}, [selectedAsset, selectedDetailImage]);

	const selectedDetailAnchors = useMemo(
		() => (selectedDetailImage ? activeResourceAnchorsByImageId[selectedDetailImage.id] ?? [] : []),
		[activeResourceAnchorsByImageId, selectedDetailImage]
	);

	useEffect(() => {
		if (selectedDetailAnchors.length === 0) {
			setSelectedDetailAnchorId('');
			setAssetDetailAnchorPanelMode('expanded');
			return;
		}
		if (!selectedDetailAnchorId || !selectedDetailAnchors.some((anchor) => anchor.id === selectedDetailAnchorId)) {
			setSelectedDetailAnchorId(selectedDetailAnchors[0]?.id ?? '');
			setAssetDetailAnchorPanelMode('expanded');
		}
	}, [selectedDetailAnchorId, selectedDetailAnchors]);

	const selectedDetailAnchor = useMemo(
		() => selectedDetailAnchors.find((anchor) => anchor.id === selectedDetailAnchorId) ?? selectedDetailAnchors[0] ?? null,
		[selectedDetailAnchorId, selectedDetailAnchors]
	);

	const assetDetailReadableGroupStyle = useMemo<React.CSSProperties | undefined>(() => {
		if (!assetDetailWideViewport || selectedDetailAnchors.length === 0) return undefined;
		return {
			maxWidth: 'calc(var(--cockpit-modal-max-width) + 360px)',
			paddingRight: '360px',
		};
	}, [assetDetailWideViewport, selectedDetailAnchors.length]);

	useEffect(() => {
		if (!isClient || !assetDetailOpen || !selectedDetailImage || typeof window === 'undefined') {
			setAssetDetailAnchorRailVisible(false);
			return;
		}

		const updateAnchorRailPosition = () => {
			const imageContainer = assetDetailImageContainerRefs.current[selectedDetailImage.id];
			if (!imageContainer) {
				setAssetDetailAnchorRailVisible(false);
				return;
			}
			const rect = imageContainer.getBoundingClientRect();
			const shouldShowRail = assetDetailWideViewport && selectedDetailAnchors.length > 0 && rect.height > 0;
			setAssetDetailAnchorRailVisible(shouldShowRail);
			if (!shouldShowRail) return;
			const railWidth = 280;
			const gap = 36;
			const viewportPadding = 16;
			const maxLeft = Math.max(viewportPadding, window.innerWidth - railWidth - viewportPadding);
			const nextLeft = Math.min(maxLeft, rect.right + gap);
			const nextTop = Math.min(
				Math.max(92, rect.top + 8),
				Math.max(92, window.innerHeight - 240)
			);
			const maxHeight = Math.max(220, window.innerHeight - nextTop - 32);
			setAssetDetailAnchorRailStyle({
				left: `${nextLeft}px`,
				top: `${nextTop}px`,
				maxHeight: `${maxHeight}px`,
			});
		};

		updateAnchorRailPosition();
		window.addEventListener('scroll', updateAnchorRailPosition, true);
		window.addEventListener('resize', updateAnchorRailPosition);
		return () => {
			window.removeEventListener('scroll', updateAnchorRailPosition, true);
			window.removeEventListener('resize', updateAnchorRailPosition);
			setAssetDetailAnchorRailVisible(false);
		};
	}, [assetDetailOpen, assetDetailWideViewport, isClient, selectedDetailAnchors.length, selectedDetailImage]);

	useEffect(() => {
		if (!isClient || !assetDetailOpen || !selectedDetailImage || !selectedDetailAnchor || typeof window === 'undefined') {
			return;
		}

		let timerId: number | null = null;
		let attempt = 0;
		const syncAnchorPanelVisibility = () => {
			const panel = assetDetailAnchorPanelRef.current;
			const overlay = assetDetailOverlayRef.current;
			const container = assetDetailImageContainerRefs.current[selectedDetailImage.id];
			if (!overlay || !container) {
				if (attempt < 8) {
					attempt += 1;
					timerId = window.setTimeout(syncAnchorPanelVisibility, 60);
				}
				return;
			}

			const overlayRect = overlay.getBoundingClientRect();
			const safeTop = overlayRect.top + 92;
			const safeBottom = overlayRect.bottom - 28;
			const containerRect = container.getBoundingClientRect();
			const anchorViewportY = containerRect.top + selectedDetailAnchor.y * containerRect.height;

			let nextDelta = 0;
			if (anchorViewportY < safeTop + 48) {
				nextDelta = anchorViewportY - (safeTop + 96);
			} else if (anchorViewportY > safeBottom - 48) {
				nextDelta = anchorViewportY - (safeBottom - 96);
			}

			if (panel) {
				const panelRect = panel.getBoundingClientRect();
				if (panelRect.height > 0) {
					if (panelRect.top < safeTop) {
						nextDelta = Math.min(nextDelta || 0, panelRect.top - safeTop);
					} else if (panelRect.bottom > safeBottom) {
						nextDelta = Math.max(nextDelta || 0, panelRect.bottom - safeBottom);
					}
				}
			}

			if (Math.abs(nextDelta) >= 2) {
				overlay.scrollBy({
					top: nextDelta,
					behavior: attempt === 0 ? 'auto' : 'smooth',
				});
			}

			if (attempt < 8) {
				attempt += 1;
				timerId = window.setTimeout(syncAnchorPanelVisibility, 80);
			}
		};

		timerId = window.setTimeout(syncAnchorPanelVisibility, 0);
		return () => {
			if (timerId !== null) {
				window.clearTimeout(timerId);
			}
		};
	}, [assetDetailAnchorPanelStyle, assetDetailOpen, isClient, selectedDetailAnchor, selectedDetailImage]);

	useEffect(() => {
		if (!isClient || !assetDetailOpen || !selectedDetailImage || !selectedDetailAnchor || typeof window === 'undefined') {
			setAssetDetailAnchorPanelStyle({});
			return;
		}

		let frameId = 0;
		const updateAnchorPanelStyle = () => {
			const panel = assetDetailAnchorPanelRef.current;
			const container = assetDetailImageContainerRefs.current[selectedDetailImage.id];
			if (!panel || !container) return;

			const containerWidth = container.clientWidth;
			const containerHeight = container.clientHeight;
			const panelWidth = panel.offsetWidth;
			const panelHeight = panel.offsetHeight;
			if (!containerWidth || !containerHeight || !panelWidth || !panelHeight) return;

			const edgePadding = 16;
			const gap = 24;
			const anchorX = selectedDetailAnchor.x * containerWidth;
			const anchorY = selectedDetailAnchor.y * containerHeight;

			let left = anchorX + gap;
			if (left + panelWidth > containerWidth - edgePadding) {
				left = anchorX - gap - panelWidth;
			}
			left = Math.min(containerWidth - panelWidth - edgePadding, Math.max(edgePadding, left));

			let top = anchorY - 16;
			if (top + panelHeight > containerHeight - edgePadding) {
				top = anchorY - gap - panelHeight;
			}
			top = Math.min(containerHeight - panelHeight - edgePadding, Math.max(edgePadding, top));

			setAssetDetailAnchorPanelStyle({
				left: `${left}px`,
				top: `${top}px`,
			});
		};

		frameId = window.requestAnimationFrame(() => {
			frameId = window.requestAnimationFrame(updateAnchorPanelStyle);
		});

		window.addEventListener('resize', updateAnchorPanelStyle);
		return () => {
			window.cancelAnimationFrame(frameId);
			window.removeEventListener('resize', updateAnchorPanelStyle);
		};
	}, [assetDetailOpen, isClient, selectedDetailAnchor, selectedDetailImage]);

	const updateResourceAnchor = useCallback((imageId: string, anchorId: string, patch: Partial<ResourceImageAnchor>) => {
		setResourceAnchorStore((prev) => {
			const base = prev ?? resourceAnchorsByImageId;
			return {
				...base,
				[imageId]: (base[imageId] ?? []).map((anchor) => (anchor.id === anchorId ? { ...anchor, ...patch } : anchor)),
			};
		});
		setResourceAnchorDirty(true);
	}, [resourceAnchorsByImageId]);

	const removeResourceAnchor = useCallback((imageId: string, anchorId: string) => {
		setResourceAnchorStore((prev) => {
			const base = prev ?? resourceAnchorsByImageId;
			return {
				...base,
				[imageId]: (base[imageId] ?? []).filter((anchor) => anchor.id !== anchorId),
			};
		});
		setResourceAnchorDirty(true);
	}, [resourceAnchorsByImageId]);

	const createResourceAnchorAtPosition = useCallback((image: ResourceSeriesImage, resource: ResourceCardItem, x = 0.5, y = 0.5) => {
		const nextAnchor: ResourceImageAnchor = {
			id: `${image.id}-anchor-custom-${Date.now()}`,
			resourceId: resource.id,
			imageId: image.id,
			x,
			y,
			type: '体验点',
			title: '新锚点',
			summary: '补充这个局部为什么值得收藏、引用或传递。',
			tags: resource.tags.slice(0, 3),
			space: resource.space,
			topic: resource.category,
			quotedReason: '用于补充管理员定义的系统锚点。',
			anchorMode: 'object',
			evidenceLevel: 'medium',
			insights: [],
			origin: 'system',
		};
		setResourceAnchorStore((prev) => {
			const base = prev ?? resourceAnchorsByImageId;
			return {
				...base,
				[image.id]: [...(base[image.id] ?? []), nextAnchor],
			};
		});
		setSelectedDetailAnchorId(nextAnchor.id);
		setResourceAnchorDirty(true);
	}, [resourceAnchorsByImageId]);

	const addResourceAnchor = useCallback(() => {
		if (!selectedAsset || !selectedDetailImage) return;
		createResourceAnchorAtPosition(selectedDetailImage, selectedAsset);
	}, [createResourceAnchorAtPosition, selectedAsset, selectedDetailImage]);

	const saveResourceAnchors = useCallback(() => {
		if (typeof window === 'undefined' || !resourceAnchorStore) return;
		window.localStorage.setItem(RESOURCE_ANCHOR_STORAGE_KEY, JSON.stringify(resourceAnchorStore));
		setResourceAnchorDirty(false);
		setAssetAnchorEditMode(false);
	}, [resourceAnchorStore]);

	const resetCurrentImageAnchors = useCallback(() => {
		if (!selectedDetailImage) return;
		setResourceAnchorStore((prev) => {
			const base = prev ?? resourceAnchorsByImageId;
			return {
				...base,
				[selectedDetailImage.id]: resourceAnchorsByImageId[selectedDetailImage.id] ?? [],
			};
		});
		setSelectedDetailAnchorId((resourceAnchorsByImageId[selectedDetailImage.id] ?? [])[0]?.id ?? '');
		setResourceAnchorDirty(true);
	}, [resourceAnchorsByImageId, selectedDetailImage]);

	const createCustomAnchorFromDraft = useCallback(() => {
		if (!inspirationDraft) return;
		setInspirationDraft((prev) => {
			if (!prev) return prev;
			const derived = prev.itemType === 'anchor' && prev.anchorOrigin === 'system';
			return {
				...prev,
				entityType: 'anchor',
				itemType: 'anchor',
				anchorOrigin: derived ? 'derived' : 'user',
				anchorType: prev.anchorType ?? '体验点',
				title: prev.itemType === 'anchor' ? prev.title : `${prev.title} · 我的锚点`,
				sourceLabel: '灵感仓库 · 我的锚点',
				anchorSummary: prev.anchorSummary ?? '用户在灵感仓库中补充的自定义锚点。',
				insightId: undefined,
				insightType: undefined,
				insightTitle: undefined,
				insightSummary: undefined,
				anchorX: prev.anchorX ?? 0.5,
				anchorY: prev.anchorY ?? 0.5,
			};
		});
	}, [inspirationDraft]);

	const detailArticleSections = useMemo(() => {
		if (!selectedAsset) return [];

		return selectedAsset.imageSeries.map((image, index) => ({
			image,
			eyebrow: index === 0 ? '项目封面' : `章节 ${String(index + 1).padStart(2, '0')}`,
			title:
				index === 0
					? `${selectedAsset.title} · 系列开篇`
					: `${selectedAsset.series} · ${selectedAsset.space === '全局' ? '跨空间' : selectedAsset.space} 场景 ${index + 1}`,
			body:
				index === 0
					? `${selectedAsset.desc} 这组资源来自 ${selectedAsset.brand} 的 ${selectedAsset.series}，适合在方案阶段做方向判断、风格校准和替代比选。`
					: `这一张重点展示 ${selectedAsset.category} 在${selectedAsset.space === '全局' ? '不同空间' : `${selectedAsset.space}场景`}中的使用气质。可结合 ${selectedAsset.tags.join(' / ')} 做材质、灯光或陈设层级推演。`,
			caption:
				index === 0
					? `首图建议作为项目封面或情绪定调图，适合直接引用到右侧对话继续分析。`
					: `当前图可单独收藏到灵感仓库、加入方案栏，或写入方案画布作为具体参考节点。`,
		}));
	}, [selectedAsset]);

	const detailDiscussionEntries = useMemo<DetailDiscussionEntry[]>(() => {
		if (!selectedAsset) return [];

		return [
			{
				id: `${selectedAsset.id}-comment-1`,
				author: '空间策略组',
				date: '2026-04-02',
				content: `这组 ${selectedAsset.category} 的调性比较稳，适合先作为 ${selectedAsset.space === '全局' ? '全局' : selectedAsset.space} 方向锚点，再往下拆预算梯度。`,
				replyLabel: '回复',
				avatarTone: 'from-slate-900 via-slate-700 to-slate-500',
			},
			{
				id: `${selectedAsset.id}-comment-2`,
				author: '方案画布',
				date: '2026-04-01',
				content: `建议优先对比 ${selectedAsset.alternatives.length > 0 ? '同系列替代项' : '相邻分类资源'}，方便快速判断交期和风险差异。`,
				replyLabel: '回复',
				avatarTone: 'from-emerald-500 via-cyan-500 to-sky-600',
			},
			{
				id: `${selectedAsset.id}-comment-3`,
				author: selectedAsset.brand,
				date: '2026-03-30',
				content: `如果这张图要进入正式方案，推荐同时记录 ${selectedAsset.tags.join('、')} 这些关键词，后续检索和复用会更快。`,
				replyLabel: '回复',
				avatarTone: 'from-fuchsia-500 via-violet-500 to-amber-400',
			},
		];
	}, [selectedAsset]);

	const toggleAssetBasketSelection = (resource: ResourceCardItem, image: ResourceSeriesImage, anchor?: ResourceImageAnchor | null) => {
		const selectionId = anchor ? `${image.id}::${anchor.id}` : image.id;
		setAssetBasketSelections((prev) => {
			const exists = prev.some((item) => item.id === selectionId);
			if (exists) return prev.filter((item) => item.id !== selectionId);

			return [
				...prev,
				{
					id: selectionId,
					resourceId: resource.id,
					resourceTitle: resource.title,
					imageId: image.id,
					imageName: anchor ? `${image.name} · ${anchor.title}` : image.name,
					imageSrc: image.src,
					risk: resource.risk,
					leadTimeDays: resource.leadTimeDays,
					anchorId: anchor?.id,
					anchorTitle: anchor?.title,
					anchorType: anchor?.type,
				},
			];
		});
	};

	const isImageInBasket = (imageId: string, anchorId?: string) =>
		basketItems.some((item) => item.id === (anchorId ? `${imageId}::${anchorId}` : imageId));

	const removeBasketSelection = (selectionId: string) => {
		setAssetBasketSelections((prev) => prev.filter((item) => item.id !== selectionId));
	};

	const closeInspirationModal = useCallback(() => {
		setInspirationModalOpen(false);
		setInspirationDraft(null);
	}, []);

	const openInspirationModalFromResource = useCallback((
		resource: ResourceCardItem,
		image: ResourceSeriesImage,
		anchor?: ResourceImageAnchor | null,
		insight?: ResourceAnchorInsight | null
	) => {
		const existing = inspirationLibraryItems.find(
			(item) =>
				item.resourceId === resource.id &&
				item.imageId === image.id &&
				(item.anchorId ?? '') === (anchor?.id ?? '') &&
				(item.insightId ?? '') === (insight?.id ?? '')
		);
		setInspirationDraft({
			id: existing?.id,
			entityType: insight ? 'insight' : anchor ? 'anchor' : 'image',
			sourceTrace: buildResourceSourceTrace({
				projectId: resource.id,
				imageId: image.id,
				anchorId: anchor?.id,
				insightId: insight?.id,
			}),
			title: existing?.title ?? (insight ? insight.title : anchor ? anchor.title : `${resource.title} · ${image.name}`),
			imageSrc: image.src,
			fallbackImageSrc: image.fallbackSrc,
			desc:
				existing?.desc ??
				(insight
					? `${insight.summary}${insight.actionHint ? `\n\n执行建议：${insight.actionHint}` : ''}${insight.riskHint ? `\n\n风险提醒：${insight.riskHint}` : ''}`
					: anchor
						? `${anchor.summary}\n\n引用理由：${anchor.quotedReason}`
						: resource.desc),
			category:
				existing?.category ??
				(insight
					? `${resource.category} / ${anchor?.type ?? '锚点'} / ${insight.type}`
					: anchor
						? `${resource.category} / ${anchor.type}`
						: resource.category),
			tagsInput:
				existing
					? existing.tags.join(', ')
					: insight
						? [...anchor?.tags ?? [], insight.type].join(', ')
						: anchor
							? anchor.tags.join(', ')
							: resource.tags.join(', '),
			source: 'market',
			sourceLabel: insight ? '资源雷达 · 锚点解读' : anchor ? '资源雷达 · 系统锚点' : '资源雷达',
			resourceId: resource.id,
			imageId: image.id,
			itemType: insight ? 'insight' : anchor ? 'anchor' : 'image',
			resourceTitle: resource.title,
			imageName: image.name,
			anchorId: anchor?.id,
			anchorType: anchor?.type,
			anchorSummary: anchor?.summary,
			anchorMode: anchor?.anchorMode,
			anchorX: anchor?.x,
			anchorY: anchor?.y,
			evidenceLevel: insight?.evidenceLevel ?? anchor?.evidenceLevel,
			insightId: insight?.id,
			insightType: insight?.type,
			insightTitle: insight?.title,
			insightSummary: insight?.summary,
			anchorOrigin: anchor ? 'system' : undefined,
		});
		setInspirationModalOpen(true);
	}, [inspirationLibraryItems]);

	const isImageCollectedToInspiration = useCallback(
		(resourceId: string, imageId: string, anchorId?: string) =>
			inspirationLibraryItems.some(
				(item) => item.resourceId === resourceId && item.imageId === imageId && (item.anchorId ?? '') === (anchorId ?? '')
			),
		[inspirationLibraryItems]
	);

	const handleInspirationUploadChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
		const file = event.target.files?.[0];
		if (!file) return;
		const reader = new FileReader();
		reader.onload = () => {
			const src = typeof reader.result === 'string' ? reader.result : '';
			if (!src) return;
			setInspirationDraft({
				title: file.name.replace(/\.[^.]+$/, ''),
				imageSrc: src,
				fallbackImageSrc: src,
				desc: '',
				category: '未分类',
				tagsInput: '',
				source: 'upload',
				sourceLabel: '本地上传',
			});
			setInspirationModalOpen(true);
			event.target.value = '';
		};
		reader.readAsDataURL(file);
	}, []);

	const saveInspirationItem = useCallback(() => {
		if (!inspirationDraft) return;
		const normalizedCategory = inspirationDraft.category.trim() || '未分类';
		const tags = inspirationDraft.tagsInput
			.split(/[，,\n]/)
			.map((tag) => tag.trim())
			.filter(Boolean)
			.slice(0, 12);
		const nextItem: InspirationLibraryItem = {
			id: inspirationDraft.id ?? `inspiration-${Date.now()}`,
			entityType:
				inspirationDraft.entityType ??
				(inspirationDraft.itemType === 'insight' ? 'insight' : inspirationDraft.itemType === 'anchor' ? 'anchor' : 'image'),
			sourceTrace:
				inspirationDraft.sourceTrace ??
				(inspirationDraft.resourceId
					? buildResourceSourceTrace({
						projectId: inspirationDraft.resourceId,
						imageId: inspirationDraft.imageId,
						anchorId: inspirationDraft.anchorId,
						insightId: inspirationDraft.insightId,
					})
					: undefined),
			title: inspirationDraft.title.trim() || '未命名灵感',
			imageSrc: inspirationDraft.imageSrc,
			fallbackImageSrc: inspirationDraft.fallbackImageSrc,
			desc: inspirationDraft.desc.trim(),
			category: normalizedCategory,
			tags,
			source: inspirationDraft.source,
			sourceLabel: inspirationDraft.sourceLabel,
			resourceId: inspirationDraft.resourceId,
			imageId: inspirationDraft.imageId,
			itemType: inspirationDraft.itemType ?? 'image',
			resourceTitle: inspirationDraft.resourceTitle,
			imageName: inspirationDraft.imageName,
			anchorId: inspirationDraft.anchorId,
			anchorType: inspirationDraft.anchorType,
			anchorSummary: inspirationDraft.anchorSummary,
			anchorMode: inspirationDraft.anchorMode,
			anchorX: inspirationDraft.anchorX,
			anchorY: inspirationDraft.anchorY,
			evidenceLevel: inspirationDraft.evidenceLevel,
			insightId: inspirationDraft.insightId,
			insightType: inspirationDraft.insightType,
			insightTitle: inspirationDraft.insightTitle,
			insightSummary: inspirationDraft.insightSummary,
			anchorOrigin: inspirationDraft.anchorOrigin,
			addedAt: new Date().toISOString(),
		};
		setInspirationLibraryItems((prev) => {
			const index = prev.findIndex((item) => item.id === nextItem.id);
			if (index === -1) return [nextItem, ...prev];
			const next = [...prev];
			next[index] = nextItem;
			return next;
		});
		closeInspirationModal();
	}, [closeInspirationModal, inspirationDraft]);

	const deleteInspirationItem = useCallback(() => {
		if (!inspirationDraft?.id) return;
		setInspirationLibraryItems((prev) => prev.filter((item) => item.id !== inspirationDraft.id));
		closeInspirationModal();
	}, [closeInspirationModal, inspirationDraft?.id]);

	const openInspirationEditModal = useCallback((item: InspirationLibraryItem) => {
		setInspirationDraft({
			id: item.id,
			entityType: item.entityType,
			sourceTrace: item.sourceTrace,
			title: item.title,
			imageSrc: item.imageSrc,
			fallbackImageSrc: item.fallbackImageSrc,
			desc: item.desc,
			category: item.category,
			tagsInput: item.tags.join(', '),
			source: item.source,
			sourceLabel: item.sourceLabel,
			resourceId: item.resourceId,
			imageId: item.imageId,
			itemType: item.itemType,
			resourceTitle: item.resourceTitle,
			imageName: item.imageName,
			anchorId: item.anchorId,
			anchorType: item.anchorType,
			anchorSummary: item.anchorSummary,
			anchorMode: item.anchorMode,
			anchorX: item.anchorX,
			anchorY: item.anchorY,
			evidenceLevel: item.evidenceLevel,
			insightId: item.insightId,
			insightType: item.insightType,
			insightTitle: item.insightTitle,
			insightSummary: item.insightSummary,
			anchorOrigin: item.anchorOrigin,
		});
		setInspirationModalOpen(true);
	}, []);

	const openBoardCollectionModal = (resource: ResourceCardItem, image: ResourceSeriesImage) => {
		const existing = boardCollections.find((item) => item.imageId === image.id);
		const isCustomSpace = existing ? !COLLECTION_SPACE_OPTIONS.includes(existing.space) : false;

		setBoardCollectionDraft({
			resourceId: resource.id,
			imageId: image.id,
			customTitle: existing?.customTitle ?? resource.title,
			note: existing?.note ?? resource.desc,
			tagsInput: existing?.tags.join(', ') ?? resource.tags.join(', '),
			space: existing?.space ?? resource.space,
			useCustomSpace: isCustomSpace,
			newSpace: isCustomSpace ? existing?.space ?? '' : '',
		});
		setBoardCollectModalOpen(true);
	};

	const closeBoardCollectionModal = useCallback(() => {
		setBoardCollectModalOpen(false);
		setBoardCollectionDraft(null);
	}, []);

	const updateBoardCollectionDraft = (patch: Partial<BoardCollectionDraft>) => {
		setBoardCollectionDraft((prev) => (prev ? { ...prev, ...patch } : prev));
	};

	const saveBoardCollection = () => {
		if (!boardCollectionDraft) return;

		const resource = resourceItems.find((item) => item.id === boardCollectionDraft.resourceId);
		const image = resource?.imageSeries.find((item) => item.id === boardCollectionDraft.imageId);
		if (!resource || !image) return;

		const resolvedSpace = (boardCollectionDraft.useCustomSpace ? boardCollectionDraft.newSpace : boardCollectionDraft.space).trim() || resource.space;
		const normalizedTags = Array.from(
			new Set(
				boardCollectionDraft.tagsInput
					.split(/[，,\n]/)
					.map((item) => item.trim())
					.filter(Boolean)
			)
		);

		setBoardCollections((prev) => {
			const nextItem: BoardCollectionItem = {
				id: `board-${image.id}`,
				resourceId: resource.id,
				resourceTitle: resource.title,
				resourceCategory: resource.category,
				imageId: image.id,
				imageName: image.name,
				imageSrc: image.src,
				space: resolvedSpace,
				sourceSpace: resource.space,
				customTitle: boardCollectionDraft.customTitle.trim() || resource.title,
				note: boardCollectionDraft.note.trim() || resource.desc,
				tags: normalizedTags,
				desc: resource.desc,
				addedAt: new Date().toLocaleString('zh-CN', {
					month: '2-digit',
					day: '2-digit',
					hour: '2-digit',
					minute: '2-digit',
				}),
			};

			const others = prev.filter((item) => item.imageId !== image.id);
			return [nextItem, ...others];
		});

		closeBoardCollectionModal();
	};

	const isImageCollectedToBoard = (imageId: string) => boardCollections.some((item) => item.imageId === imageId);

	const toggleBoardCollection = (resource: ResourceCardItem, image: ResourceSeriesImage) => {
		if (isImageCollectedToBoard(image.id)) {
			removeBoardCollection(image.id);
			return;
		}

		openBoardCollectionModal(resource, image);
	};

	const removeBoardCollection = (imageId: string) => {
		setBoardCollections((prev) => prev.filter((item) => item.imageId !== imageId));
	};

	const clampBoardCanvasZoom = useCallback((zoom: number) => clampCanvasZoom(zoom, 0.3, 4), []);
	const clampBoardCanvasItemWidth = useCallback((width: number) => Math.min(960, Math.max(MIN_BOARD_ITEM_WIDTH, width)), []);

	const toBoardCanvasPoint = useCallback((clientX: number, clientY: number) => {
		const rect = boardCanvasViewportRef.current?.getBoundingClientRect();
		const view = boardCanvasViewRef.current;
		if (!rect) return { x: 0, y: 0 };
		return {
			x: (clientX - rect.left - view.x) / view.zoom,
			y: (clientY - rect.top - view.y) / view.zoom,
		};
	}, []);

	const zoomBoardCanvasAt = useCallback(
		(clientX: number, clientY: number, factor: number) => {
			const rect = boardCanvasViewportRef.current?.getBoundingClientRect();
			if (!rect) return;

			setBoardCanvasView((prev) => {
				return zoomSharedCanvasViewAt(prev, rect, clientX, clientY, factor, { minZoom: 0.3, maxZoom: 4 });
			});
		},
		[]
	);

	const updateBoardGeneratedItemStatus = useCallback((itemId: string, status: BoardGeneratedStatus) => {
		setBoardGeneratedItems((prev) =>
			prev.map((item) =>
				item.id === itemId
					? {
							...item,
							status,
					  }
					: item
			)
		);
	}, []);

	const openReferenceEditModal = useCallback((target: 'source' | 'canvas', control: BoardReferenceControl, ids: { sourceId?: string; canvasItemId?: string }) => {
		setReferenceEditDraft({
			target,
			sourceId: ids.sourceId,
			canvasItemId: ids.canvasItemId,
			control: {
				...control,
				mustHave: [...control.mustHave],
				negative: [...control.negative],
			},
		});
	}, []);

	const updateReferenceEditControl = useCallback((patch: Partial<BoardReferenceControl>) => {
		setReferenceEditDraft((prev) =>
			prev
				? {
						...prev,
						control: {
							...prev.control,
							...patch,
						},
				  }
				: prev
		);
	}, []);


	const appendBoardGeneratedItem = useCallback(
		(image: ExpertGeneratedImage, options?: { round?: number; status?: BoardGeneratedStatus; sourceContext?: string }) => {
			if (!image.image_url || isBoardOverview) return;

			const createdAt = image.created_at ?? new Date().toISOString();
			const promptSummary = image.prompt_used ?? image.prompt ?? `${currentBoardSpace} 方案生成`;
			const nextRound =
				options?.round ??
				(boardGeneratedItems.reduce((maxRound, item) => Math.max(maxRound, item.generationRound), 0) + 1);
			const nextItem: BoardGeneratedItem = {
				id: image.id ?? `board-generated-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
				sessionId: resolvedBoardSessionId,
				space: currentBoardSpace,
				topicScope: boardCanvasMode,
				generationRound: nextRound,
				createdAt,
				promptSummary,
				sourceContext:
					options?.sourceContext ??
					`${resolvedProjectLabel} / ${currentBoardSpace} / ${boardCanvasMode} / 方案高参`,
				status: options?.status ?? 'generated',
				title: `${currentBoardSpace} · 生成候选`,
				imageSrc: image.image_url,
				fallbackImageSrc: image.image_url,
				expertName: image.expert_name ?? '方案高参',
				sourceImageId: image.id,
			};

			setBoardGeneratedItems((prev) => [nextItem, ...prev.filter((item) => item.id !== nextItem.id)]);

			const activeElement = typeof document !== 'undefined' ? document.activeElement : null;
			const isUserBusy =
				Boolean(boardCanvasInteractionRef.current) ||
				activeElement instanceof HTMLInputElement ||
				activeElement instanceof HTMLTextAreaElement;

			if (isUserBusy) {
				setBoardGeneratedUnseenCount((prev) => prev + 1);
				return;
			}

			setBoardSourceTab('generated');
			setBoardGeneratedUnseenCount(0);
		},
		[
			boardCanvasMode,
			boardGeneratedItems,
			currentBoardSpace,
			isBoardOverview,
			resolvedBoardSessionId,
			resolvedProjectLabel,
		]
	);

	useEffect(() => {
		if (typeof window === 'undefined') return;

		const handleGeneratedImageEvent = (event: Event) => {
			const customEvent = event as CustomEvent<{
				image?: ExpertGeneratedImage;
				round?: number;
				sourceContext?: string;
				status?: BoardGeneratedStatus;
			}>;
			if (!customEvent.detail?.image) return;
			appendBoardGeneratedItem(customEvent.detail.image, {
				round: customEvent.detail.round,
				sourceContext: customEvent.detail.sourceContext,
				status: customEvent.detail.status,
			});
		};

		window.addEventListener(BOARD_GENERATION_EVENT, handleGeneratedImageEvent as EventListener);
		return () => window.removeEventListener(BOARD_GENERATION_EVENT, handleGeneratedImageEvent as EventListener);
	}, [appendBoardGeneratedItem]);

	const snapshotBoardCanvasItems = useCallback(
		(items: BoardCanvasItem[]) => items.map((item) => ({ ...item })),
		[]
	);

	const pushBoardCanvasUndoSnapshot = useCallback(
		(snapshot: BoardCanvasItem[]) => {
			boardCanvasUndoStackRef.current = [
				...boardCanvasUndoStackRef.current.slice(-(MAX_BOARD_CANVAS_HISTORY_STEPS - 1)),
				snapshotBoardCanvasItems(snapshot),
			];
			boardCanvasRedoStackRef.current = [];
		},
		[snapshotBoardCanvasItems]
	);

	const addBoardCanvasItem = useCallback((source: BoardSourceItem) => {
		const rect = boardCanvasViewportRef.current?.getBoundingClientRect();
		const view = boardCanvasViewRef.current;
		pushBoardCanvasUndoSnapshot(boardCanvasItemsRef.current);

		setBoardCanvasItems((prev) => {
			const scatter = prev.length % 6;
			const baseX = rect ? (rect.width * 0.42 - view.x) / view.zoom : 320;
			const baseY = rect ? (rect.height * 0.3 - view.y) / view.zoom : 220;
			const nextItem: BoardCanvasItem = {
				id: `board-canvas-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
				sourceType: source.sourceType,
				sourceId: source.sourceId,
				entityType: source.entityType,
				sourceTrace: source.sourceTrace,
				referenceControl: source.referenceControl,
				anchorIds: source.anchorIds,
				anchorX: source.anchorX,
				anchorY: source.anchorY,
				anchorSummary: source.anchorSummary,
				title: source.title,
				imageSrc: source.imageSrc,
				fallbackImageSrc: source.fallbackImageSrc,
				desc: source.desc,
				meta: source.meta,
				x: baseX + scatter * 32,
				y: baseY + scatter * 26,
				width: source.entityType === 'insight' ? 280 : source.sourceType === 'history' ? 260 : 320,
				aspectRatio: DEFAULT_BOARD_ITEM_ASPECT_RATIO,
				addedAt: new Date().toISOString(),
			};
			setSelectedBoardCanvasItemId(nextItem.id);
			return [...prev, nextItem];
		});

	}, [pushBoardCanvasUndoSnapshot]);

	const addBoardCanvasItemWithReference = useCallback((source: BoardSourceItem, referenceControl?: BoardReferenceControl) => {
		addBoardCanvasItem(referenceControl ? { ...source, referenceControl } : source);
	}, [addBoardCanvasItem]);

	const bringBoardCanvasItemToFront = useCallback((itemId: string) => {
		setBoardCanvasItems((prev) => {
			const item = prev.find((entry) => entry.id === itemId);
			if (!item) return prev;
			return [...prev.filter((entry) => entry.id !== itemId), item];
		});
	}, []);

	const removeBoardCanvasItem = useCallback((itemId: string) => {
		pushBoardCanvasUndoSnapshot(boardCanvasItemsRef.current);
		setBoardCanvasItems((prev) => prev.filter((item) => item.id !== itemId));
		setSelectedBoardCanvasItemId((prev) => (prev === itemId ? null : prev));
	}, [pushBoardCanvasUndoSnapshot]);

	const copyBoardCanvasItem = useCallback((item: BoardCanvasItem | null | undefined) => {
		if (!item) return false;
		const { id: _id, addedAt: _addedAt, ...snapshot } = item;
		void _id;
		void _addedAt;
		boardCanvasClipboardRef.current = snapshot;
		return true;
	}, []);

	const pasteBoardCanvasItem = useCallback(() => {
		const snapshot = boardCanvasClipboardRef.current;
		if (!snapshot) return false;
		pushBoardCanvasUndoSnapshot(boardCanvasItemsRef.current);

		const nextItem: BoardCanvasItem = {
			...snapshot,
			id: `board-canvas-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
			x: snapshot.x + 28,
			y: snapshot.y + 28,
			addedAt: new Date().toISOString(),
		};

		boardCanvasClipboardRef.current = {
			...snapshot,
			x: nextItem.x,
			y: nextItem.y,
		};

		setBoardCanvasItems((prev) => [...prev, nextItem]);
		setSelectedBoardCanvasItemId(nextItem.id);
		return true;
	}, [pushBoardCanvasUndoSnapshot]);

	const toggleBoardCanvasItemDisabled = useCallback((itemId: string) => {
		pushBoardCanvasUndoSnapshot(boardCanvasItemsRef.current);
		setBoardCanvasItems((prev) =>
			prev.map((item) =>
				item.id === itemId
					? {
							...item,
							disabled: !item.disabled,
					  }
					: item
			)
		);
	}, [pushBoardCanvasUndoSnapshot]);

	const resetBoardCanvasView = useCallback(() => {
		setBoardCanvasView({ x: 180, y: 110, zoom: 1 });
	}, []);

	const fitBoardCanvasView = useCallback(() => {
		const rect = boardCanvasViewportRef.current?.getBoundingClientRect();
		if (!rect || boardCanvasItems.length === 0) return;

		const bounds = boardCanvasItems.reduce(
			(acc, item) => {
				const estimatedHeight = getBoardCanvasItemHeight(item);
				return {
					minX: Math.min(acc.minX, item.x),
					minY: Math.min(acc.minY, item.y),
					maxX: Math.max(acc.maxX, item.x + item.width),
					maxY: Math.max(acc.maxY, item.y + estimatedHeight),
				};
			},
			{ minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity }
		);

		const contentWidth = Math.max(320, bounds.maxX - bounds.minX);
		const contentHeight = Math.max(240, bounds.maxY - bounds.minY);
		const nextZoom = clampBoardCanvasZoom(
			Math.min((rect.width * 0.86) / contentWidth, (rect.height * 0.82) / contentHeight)
		);

		setBoardCanvasView({
			x: rect.width / 2 - (bounds.minX + contentWidth / 2) * nextZoom,
			y: rect.height / 2 - (bounds.minY + contentHeight / 2) * nextZoom,
			zoom: nextZoom,
		});
	}, [boardCanvasItems, clampBoardCanvasZoom]);

	const handleBoardCanvasWheel = useCallback(
		(event: React.WheelEvent<HTMLDivElement>) => {
			event.preventDefault();
			const factor = getWheelZoomFactor(event.deltaY);
			zoomBoardCanvasAt(event.clientX, event.clientY, factor);
		},
		[zoomBoardCanvasAt]
	);

	const handleBoardCanvasMouseDown = useCallback(
		(event: React.MouseEvent<HTMLDivElement>) => {
			if (event.button !== 0 && event.button !== 1) return;
			if (event.button === 1) {
				event.preventDefault();
				event.stopPropagation();
			}
			setSelectedBoardCanvasItemId(null);
			const view = boardCanvasViewRef.current;
			boardCanvasInteractionRef.current = {
				mode: 'pan',
				startClientX: event.clientX,
				startClientY: event.clientY,
				startX: view.x,
				startY: view.y,
			};
		},
		[]
	);

	const handleBoardItemMouseDown = useCallback(
		(event: React.MouseEvent<HTMLDivElement>, item: BoardCanvasItem) => {
			if (event.button !== 0) return;
			event.stopPropagation();
			setSelectedBoardCanvasItemId(item.id);
			bringBoardCanvasItemToFront(item.id);
			pushBoardCanvasUndoSnapshot(boardCanvasItemsRef.current);
			const point = toBoardCanvasPoint(event.clientX, event.clientY);
			boardCanvasInteractionRef.current = {
				mode: 'move-item',
				itemId: item.id,
				offsetX: point.x - item.x,
				offsetY: point.y - item.y,
			};
		},
		[bringBoardCanvasItemToFront, pushBoardCanvasUndoSnapshot, toBoardCanvasPoint]
	);

	const handleBoardItemResizeMouseDown = useCallback(
		(event: React.MouseEvent<HTMLSpanElement>, item: BoardCanvasItem, handle: BoardResizeHandle) => {
			if (event.button !== 0) return;
			event.stopPropagation();
			event.preventDefault();
			setSelectedBoardCanvasItemId(item.id);
			bringBoardCanvasItemToFront(item.id);
			pushBoardCanvasUndoSnapshot(boardCanvasItemsRef.current);
			const anchor = getBoardResizeAnchor(item, handle);
			boardCanvasInteractionRef.current = {
				mode: 'resize-item',
				itemId: item.id,
				handle,
				anchorX: anchor.x,
				anchorY: anchor.y,
			};
		},
		[bringBoardCanvasItemToFront, pushBoardCanvasUndoSnapshot]
	);

	const handleBoardCanvasImageLoad = useCallback((itemId: string, event: React.SyntheticEvent<HTMLImageElement>) => {
		const { naturalWidth, naturalHeight } = event.currentTarget;
		if (!naturalWidth || !naturalHeight) return;
		const aspectRatio = naturalWidth / naturalHeight;
		let isBrightImage = false;
		try {
			const sampleCanvas = document.createElement('canvas');
			sampleCanvas.width = 24;
			sampleCanvas.height = 24;
			const ctx = sampleCanvas.getContext('2d');
			if (ctx) {
				ctx.drawImage(event.currentTarget, 0, 0, 24, 24);
				const { data } = ctx.getImageData(0, 0, 24, 24);
				let luminanceTotal = 0;
				for (let i = 0; i < data.length; i += 4) {
					const r = data[i] ?? 0;
					const g = data[i + 1] ?? 0;
					const b = data[i + 2] ?? 0;
					luminanceTotal += 0.2126 * r + 0.7152 * g + 0.0722 * b;
				}
				const avgLuminance = luminanceTotal / (data.length / 4);
				isBrightImage = avgLuminance >= 165;
			}
		} catch {
			// 跨域或取样失败时走保守策略，确保亮底图上文字可读
			isBrightImage = true;
		}

		setBoardCanvasBrightImageMap((prev) => {
			if (prev[itemId] === isBrightImage) return prev;
			return {
				...prev,
				[itemId]: isBrightImage,
			};
		});

		setBoardCanvasItems((prev) =>
			prev.map((item) => {
				if (item.id !== itemId) return item;
				if (Math.abs(getBoardCanvasItemAspectRatio(item) - aspectRatio) < 0.01) return item;
				return { ...item, aspectRatio };
			})
		);
	}, []);

	useEffect(() => {
		const validItemIds = new Set(boardCanvasItems.map((item) => item.id));
		setBoardCanvasBrightImageMap((prev) => {
			let changed = false;
			const next: Record<string, boolean> = {};
			for (const [key, value] of Object.entries(prev)) {
				if (validItemIds.has(key)) {
					next[key] = value;
				} else {
					changed = true;
				}
			}
			return changed ? next : prev;
		});
	}, [boardCanvasItems]);

	useEffect(() => {
		const handlePointerMove = (event: MouseEvent) => {
			const interaction = boardCanvasInteractionRef.current;
			if (!interaction) return;

			if (interaction.mode === 'pan') {
				setBoardCanvasView((prev) => ({
					...prev,
					x: interaction.startX + (event.clientX - interaction.startClientX),
					y: interaction.startY + (event.clientY - interaction.startClientY),
				}));
				return;
			}

			if (interaction.mode === 'resize-item') {
				const point = toBoardCanvasPoint(event.clientX, event.clientY);
				setBoardCanvasItems((prev) =>
					prev.map((item) => {
						if (item.id !== interaction.itemId) return item;

						const aspectRatio = getBoardCanvasItemAspectRatio(item);
						const rawDx = point.x - interaction.anchorX;
						const rawDy = point.y - interaction.anchorY;
						const dx = Math.abs(rawDx);
						const dy = Math.abs(rawDy);
						const handle = interaction.handle;

						let nextWidth = item.width;
						if (handle === 'n' || handle === 's') {
							nextWidth = dy * aspectRatio;
						} else if (handle === 'e' || handle === 'w') {
							nextWidth = dx;
						} else {
							nextWidth = Math.max(dx, dy * aspectRatio);
						}

						const width = clampBoardCanvasItemWidth(nextWidth);
						const height = width / aspectRatio;
						let x = item.x;
						let y = item.y;

						switch (handle) {
							case 'nw':
								x = interaction.anchorX - width;
								y = interaction.anchorY - height;
								break;
							case 'n':
								x = interaction.anchorX - width / 2;
								y = interaction.anchorY - height;
								break;
							case 'ne':
								x = interaction.anchorX;
								y = interaction.anchorY - height;
								break;
							case 'e':
								x = interaction.anchorX;
								y = interaction.anchorY - height / 2;
								break;
							case 'se':
								x = interaction.anchorX;
								y = interaction.anchorY;
								break;
							case 's':
								x = interaction.anchorX - width / 2;
								y = interaction.anchorY;
								break;
							case 'sw':
								x = interaction.anchorX - width;
								y = interaction.anchorY;
								break;
							case 'w':
								x = interaction.anchorX - width;
								y = interaction.anchorY - height / 2;
								break;
						}

						return { ...item, width, x, y };
					})
				);
				return;
			}

			const point = toBoardCanvasPoint(event.clientX, event.clientY);
			setBoardCanvasItems((prev) =>
				prev.map((item) =>
					item.id === interaction.itemId
						? {
								...item,
								x: point.x - interaction.offsetX,
								y: point.y - interaction.offsetY,
						  }
						: item
				)
			);
		};

		const handlePointerUp = () => {
			boardCanvasInteractionRef.current = null;
		};

		window.addEventListener('mousemove', handlePointerMove);
		window.addEventListener('mouseup', handlePointerUp);
		return () => {
			window.removeEventListener('mousemove', handlePointerMove);
			window.removeEventListener('mouseup', handlePointerUp);
		};
	}, [clampBoardCanvasItemWidth, toBoardCanvasPoint]);

	const applyAssetTask = (task: ResourceTaskKey) => {
		setAssetTask(task);
		if (task === '替代优先') {
			setAssetQuery('替代');
			setAssetBudget('全部预算');
			setAssetCategory('全部分类');
			return;
		}
		if (task === '空间搭配') {
			setAssetQuery('');
			setAssetSpace(currentBoardSpace === '全部' ? '全部空间' : currentBoardSpace);
			setAssetBudget('均衡型');
			return;
		}
		if (task === '预算压缩') {
			setAssetQuery('');
			setAssetBudget('经济型');
			return;
		}
		if (task === '缺失补全') {
			setAssetQuery('参考');
			setAssetCategory('参考');
		}
	};

	const lockAssetDetailImageFocus = useCallback((imageId: string, durationMs = 1600) => {
		assetDetailImageFocusLockRef.current = {
			imageId,
			expiresAt: Date.now() + durationMs,
		};
	}, []);

	const toggleAssetDetailAnchorPresentation = useCallback(
		(imageId: string, anchorId: string) => {
			lockAssetDetailImageFocus(imageId);
			setSelectedDetailImageId(imageId);
			const isSameAnchor = selectedDetailImageId === imageId && selectedDetailAnchorId === anchorId;
			setSelectedDetailAnchorId(anchorId);
			setAssetDetailAnchorPanelMode((currentMode) => (isSameAnchor ? (currentMode === 'expanded' ? 'compact' : 'expanded') : 'expanded'));
		},
		[lockAssetDetailImageFocus, selectedDetailAnchorId, selectedDetailImageId]
	);

	const openAssetDetail = useCallback((id: string) => {
		setSelectedAssetId(id);
		setAssetDetailOpen(true);
	}, []);

	const closeAssetDetail = useCallback(() => {
		setAssetDetailOpen(false);
		setAssetDetailAnchorPanelMode('expanded');
	}, []);

	const showPrevDetailImage = useCallback(() => {
		if (!selectedAsset || selectedAsset.imageSeries.length <= 1) return;
		const currentIndex = selectedDetailImageIndex >= 0 ? selectedDetailImageIndex : 0;
		const prevIndex = (currentIndex - 1 + selectedAsset.imageSeries.length) % selectedAsset.imageSeries.length;
		const nextImageId = selectedAsset.imageSeries[prevIndex]?.id ?? '';
		if (nextImageId) {
			lockAssetDetailImageFocus(nextImageId);
		}
		setSelectedDetailImageId(nextImageId);
	}, [lockAssetDetailImageFocus, selectedAsset, selectedDetailImageIndex]);

	const showNextDetailImage = useCallback(() => {
		if (!selectedAsset || selectedAsset.imageSeries.length <= 1) return;
		const currentIndex = selectedDetailImageIndex >= 0 ? selectedDetailImageIndex : 0;
		const nextIndex = (currentIndex + 1) % selectedAsset.imageSeries.length;
		const nextImageId = selectedAsset.imageSeries[nextIndex]?.id ?? '';
		if (nextImageId) {
			lockAssetDetailImageFocus(nextImageId);
		}
		setSelectedDetailImageId(nextImageId);
	}, [lockAssetDetailImageFocus, selectedAsset, selectedDetailImageIndex]);

	useEffect(() => {
		if (!fileDetailOpen) return;

		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Escape') {
				closeFileDetail();
			}
		};

		window.addEventListener('keydown', handleKeyDown);
		return () => window.removeEventListener('keydown', handleKeyDown);
	}, [closeFileDetail, fileDetailOpen]);

	useEffect(() => {
		if (!selectedExpertDetail) return;

		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Escape') {
				closeExpertDetail();
			}
		};

		window.addEventListener('keydown', handleKeyDown);
		return () => window.removeEventListener('keydown', handleKeyDown);
	}, [closeExpertDetail, selectedExpertDetail]);

	useEffect(() => {
		if (!assetDetailOpen) return;

		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Escape') {
				event.preventDefault();
				closeAssetDetail();
				return;
			}

			if (event.key === 'ArrowLeft') {
				event.preventDefault();
				showPrevDetailImage();
				return;
			}

			if (event.key === 'ArrowRight') {
				event.preventDefault();
				showNextDetailImage();
			}
		};

		window.addEventListener('keydown', handleKeyDown);
		return () => window.removeEventListener('keydown', handleKeyDown);
	}, [assetDetailOpen, closeAssetDetail, showNextDetailImage, showPrevDetailImage]);

	useEffect(() => {
		if (!draggingAnchorState || !assetAnchorEditMode) return;

		const handleMouseMove = (event: MouseEvent) => {
			const container = assetDetailImageContainerRefs.current[draggingAnchorState.imageId];
			if (!container) return;
			const rect = container.getBoundingClientRect();
			const nextX = Math.min(0.96, Math.max(0.04, (event.clientX - rect.left) / rect.width));
			const nextY = Math.min(0.96, Math.max(0.04, (event.clientY - rect.top) / rect.height));
			updateResourceAnchor(draggingAnchorState.imageId, draggingAnchorState.anchorId, {
				x: Number(nextX.toFixed(4)),
				y: Number(nextY.toFixed(4)),
			});
		};

		const handleMouseUp = () => setDraggingAnchorState(null);

		window.addEventListener('mousemove', handleMouseMove);
		window.addEventListener('mouseup', handleMouseUp);
		return () => {
			window.removeEventListener('mousemove', handleMouseMove);
			window.removeEventListener('mouseup', handleMouseUp);
		};
	}, [assetAnchorEditMode, draggingAnchorState, updateResourceAnchor]);

	useEffect(() => {
		if (!inspirationModalOpen) return;

		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Escape') {
				event.preventDefault();
				closeInspirationModal();
			}
		};

		window.addEventListener('keydown', handleKeyDown);
		return () => window.removeEventListener('keydown', handleKeyDown);
	}, [closeInspirationModal, inspirationModalOpen]);

	useEffect(() => {
		if (!boardCollectModalOpen) return;

		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.key === 'Escape') {
				event.preventDefault();
				closeBoardCollectionModal();
			}
		};

		window.addEventListener('keydown', handleKeyDown);
		return () => window.removeEventListener('keydown', handleKeyDown);
	}, [boardCollectModalOpen, closeBoardCollectionModal]);

	useEffect(() => {
		if (moduleKey !== 'board') return;

		const handleKeyDown = (event: KeyboardEvent) => {
			const target = event.target;
			if (target instanceof HTMLElement) {
				const tagName = target.tagName.toLowerCase();
				if (
					tagName === 'input' ||
					tagName === 'textarea' ||
					tagName === 'select' ||
					target.isContentEditable
				) {
					return;
				}
			}

			const shortcutKey = event.key.toLowerCase();
			const hasModifier = event.metaKey || event.ctrlKey;
			const canUndo = boardCanvasUndoStackRef.current.length > 0;
			const canRedo = boardCanvasRedoStackRef.current.length > 0;

			if (hasModifier && shortcutKey === 'z' && !event.shiftKey) {
				if (!canUndo) return;
				event.preventDefault();
				const previousSnapshot = boardCanvasUndoStackRef.current.pop();
				if (!previousSnapshot) return;
				boardCanvasRedoStackRef.current = [
					...boardCanvasRedoStackRef.current.slice(-(MAX_BOARD_CANVAS_HISTORY_STEPS - 1)),
					snapshotBoardCanvasItems(boardCanvasItemsRef.current),
				];
				setBoardCanvasItems(snapshotBoardCanvasItems(previousSnapshot));
				setSelectedBoardCanvasItemId((prev) =>
					prev && previousSnapshot.some((item) => item.id === prev) ? prev : null
				);
				return;
			}

			if (hasModifier && (shortcutKey === 'y' || (shortcutKey === 'z' && event.shiftKey))) {
				if (!canRedo) return;
				event.preventDefault();
				const nextSnapshot = boardCanvasRedoStackRef.current.pop();
				if (!nextSnapshot) return;
				boardCanvasUndoStackRef.current = [
					...boardCanvasUndoStackRef.current.slice(-(MAX_BOARD_CANVAS_HISTORY_STEPS - 1)),
					snapshotBoardCanvasItems(boardCanvasItemsRef.current),
				];
				setBoardCanvasItems(snapshotBoardCanvasItems(nextSnapshot));
				setSelectedBoardCanvasItemId((prev) =>
					prev && nextSnapshot.some((item) => item.id === prev) ? prev : null
				);
				return;
			}

			if (hasModifier && shortcutKey === 'c') {
				const selectedItem = boardCanvasItems.find((item) => item.id === selectedBoardCanvasItemId);
				if (!selectedItem) return;
				event.preventDefault();
				copyBoardCanvasItem(selectedItem);
				return;
			}

			if (hasModifier && shortcutKey === 'x') {
				const selectedItem = boardCanvasItems.find((item) => item.id === selectedBoardCanvasItemId);
				if (!selectedItem) return;
				event.preventDefault();
				copyBoardCanvasItem(selectedItem);
				removeBoardCanvasItem(selectedItem.id);
				return;
			}

			if (hasModifier && shortcutKey === 'v') {
				if (!boardCanvasClipboardRef.current) return;
				event.preventDefault();
				pasteBoardCanvasItem();
				return;
			}

			if ((event.key !== 'Delete' && event.key !== 'Backspace') || hasModifier || event.altKey) return;
			if (!selectedBoardCanvasItemId) return;

			event.preventDefault();
			removeBoardCanvasItem(selectedBoardCanvasItemId);
		};

		window.addEventListener('keydown', handleKeyDown);
		return () => window.removeEventListener('keydown', handleKeyDown);
	}, [boardCanvasItems, copyBoardCanvasItem, moduleKey, pasteBoardCanvasItem, removeBoardCanvasItem, selectedBoardCanvasItemId, snapshotBoardCanvasItems]);

	useEffect(() => {
		if (moduleKey !== 'board') return;
		onBoardZoomChange?.(boardCanvasView.zoom);
	}, [boardCanvasView.zoom, moduleKey, onBoardZoomChange]);

	const relatedAssets = useMemo(() => {
		if (!selectedAsset) return [];

		const score = (item: ResourceCardItem) => {
			let points = 0;
			if (item.category === selectedAsset.category) points += 4;
			if (item.space === selectedAsset.space) points += 3;
			if (selectedAsset.alternatives.includes(item.id)) points += 5;
			if (item.budgetBand === selectedAsset.budgetBand) points += 2;
			return points;
		};

		return resourceItems
			.filter((item) => item.id !== selectedAsset.id)
			.map((item) => ({ item, points: score(item) }))
			.sort((a, b) => b.points - a.points)
			.slice(0, 12)
			.map(({ item }) => item);
	}, [resourceItems, selectedAsset]);

	const RELATED_ASSETS_PAGE_SIZE = 4;

	useEffect(() => {
		setRelatedAssetsOffset(0);
	}, [selectedAssetId]);

	const relatedAssetPages = useMemo(() => {
		const pages: Array<(typeof relatedAssets)[number][]> = [];
		for (let index = 0; index < relatedAssets.length; index += RELATED_ASSETS_PAGE_SIZE) {
			pages.push(relatedAssets.slice(index, index + RELATED_ASSETS_PAGE_SIZE));
		}
		return pages;
	}, [relatedAssets]);

	const relatedAssetsPageIndex = Math.floor(relatedAssetsOffset / RELATED_ASSETS_PAGE_SIZE);

	const canShowPreviousRelatedAssets = relatedAssetsOffset > 0;
	const canShowNextRelatedAssets = relatedAssetsOffset + RELATED_ASSETS_PAGE_SIZE < relatedAssets.length;

	const showPreviousRelatedAssets = useCallback(() => {
		setRelatedAssetsOffset((prev) => Math.max(0, prev - RELATED_ASSETS_PAGE_SIZE));
	}, []);

	const showNextRelatedAssets = useCallback(() => {
		setRelatedAssetsOffset((prev) =>
			Math.min(Math.max(0, relatedAssets.length - RELATED_ASSETS_PAGE_SIZE), prev + RELATED_ASSETS_PAGE_SIZE)
		);
	}, [relatedAssets.length]);

	const selectedBoardDraftResource = useMemo(
		() => resourceItems.find((item) => item.id === boardCollectionDraft?.resourceId) ?? null,
		[boardCollectionDraft?.resourceId, resourceItems]
	);

	const selectedBoardDraftImage = useMemo(
		() => selectedBoardDraftResource?.imageSeries.find((item) => item.id === boardCollectionDraft?.imageId) ?? null,
		[selectedBoardDraftResource, boardCollectionDraft?.imageId]
	);

	const radarBoardSourceItems = useMemo<BoardSourceItem[]>(
		() => {
			const scopedResources = resourceItems.filter(
				(resource) => !isBoardOverview && (resource.space === '全局' || resource.space === currentBoardSpace)
			);
			const resourcesForBoard =
				isBoardOverview || boardCanvasItems.length === 0 || scopedResources.length === 0
					? resourceItems
					: scopedResources;

			return resourcesForBoard.flatMap((resource) =>
				resource.imageSeries.map((image) => {
					const source = {
						id: `board-source-radar-${image.id}`,
						sourceType: 'radar' as const,
						sourceId: image.id,
						entityType: 'image' as const,
						sourceTrace: buildResourceSourceTrace({ projectId: resource.id, imageId: image.id }),
						title: `${resource.title} · ${image.name}`,
						imageSrc: image.src,
						fallbackImageSrc: image.fallbackSrc,
						desc: resource.desc,
						meta: `${resource.category} · ${toDisplaySpaceName(resource.space)}`,
					};
					return {
						...source,
						referenceControl: buildReferenceControlFromSource(source, {
							tags: resource.tags,
							space: toDisplaySpaceName(resource.space),
						}),
					};
				})
			);
		},
		[boardCanvasItems.length, currentBoardSpace, isBoardOverview, resourceItems]
	);

	const radarBoardSourceMode = useMemo<'matched' | 'empty_canvas' | 'no_space_match' | 'browse_all'>(() => {
		if (isBoardOverview) return 'browse_all';
		if (boardCanvasItems.length === 0) return 'empty_canvas';
		const hasScopedResources = resourceItems.some((resource) => resource.space === '全局' || resource.space === currentBoardSpace);
		return hasScopedResources ? 'matched' : 'no_space_match';
	}, [boardCanvasItems.length, currentBoardSpace, isBoardOverview, resourceItems]);

	const inspirationBoardSourceItems = useMemo<BoardSourceItem[]>(
		() =>
			inspirationLibraryItems.map((item) => {
				const curatedImageSrc = isExternalImageSrc(item.imageSrc)
					? (isExternalImageSrc(item.fallbackImageSrc) ? fallbackPublicPictureSrc : item.fallbackImageSrc)
					: item.imageSrc;
				const curatedFallbackImageSrc = isExternalImageSrc(item.fallbackImageSrc)
					? (fallbackPublicPictureSrc || curatedImageSrc)
					: item.fallbackImageSrc;
				const source = {
					id: `board-source-inspiration-${item.id}`,
					sourceType: 'inspiration' as const,
					sourceId: item.id,
					entityType: item.entityType,
					sourceTrace: item.sourceTrace,
					anchorIds: item.anchorId ? [item.anchorId] : undefined,
					anchorX: item.anchorX,
					anchorY: item.anchorY,
					anchorSummary: item.anchorSummary,
					title: item.title,
					imageSrc: curatedImageSrc || fallbackPublicPictureSrc,
					fallbackImageSrc: curatedFallbackImageSrc || fallbackPublicPictureSrc,
					desc: item.desc || item.anchorSummary || item.insightSummary || '来自灵感仓库的可复用素材。',
					meta:
						item.itemType === 'insight'
							? `${item.insightType ?? '解读'} · ${item.anchorType ?? '锚点'} · ${item.sourceLabel}`
							: item.itemType === 'anchor'
								? `${item.anchorType ?? '锚点'} · ${item.sourceLabel}`
								: `${item.category} · ${item.sourceLabel}`,
				};
				return {
					...source,
					referenceControl: buildReferenceControlFromSource(source, {
						anchorMode: item.anchorMode,
						tags: item.tags,
						space: currentBoardSpace,
					}),
				};
			}),
		[currentBoardSpace, fallbackPublicPictureSrc, inspirationLibraryItems]
	);

	const historyBoardSourceItems = useMemo<BoardSourceItem[]>(
		() =>
			usablePublicPictureNames.slice(0, 48).map((name, index) => {
				const src = buildPublicPictureUrl(name);
				return {
					id: `board-source-history-${name}-${index}`,
					sourceType: 'history',
					sourceId: name,
					entityType: 'image',
					title: name.replace(/\.[^.]+$/, '').replace(/[-_]+/g, ' '),
					imageSrc: src,
					fallbackImageSrc: fallbackPublicPictureSrc || src,
					desc: '历史项目素材，可直接拖入或加入当前画布继续编排。',
					meta: '历史项目素材',
					referenceControl: buildReferenceControlFromSource({
						sourceType: 'history',
						entityType: 'image',
						title: name.replace(/\.[^.]+$/, '').replace(/[-_]+/g, ' '),
						desc: '历史项目素材，可直接拖入或加入当前画布继续编排。',
						meta: '历史项目素材',
					}, { space: currentBoardSpace }),
				};
		}),
		[currentBoardSpace, fallbackPublicPictureSrc, usablePublicPictureNames]
	);

	const activeBoardGenerationRound = useMemo(
		() => boardGeneratedItems.reduce((maxRound, item) => Math.max(maxRound, item.generationRound), 0),
		[boardGeneratedItems]
	);

	const generatedBoardSourceItems = useMemo<BoardSourceItem[]>(() => {
		return boardGeneratedItems
			.filter((item) => item.status !== 'archived')
			.filter((item) => {
				if (currentBoardSpace !== '全部' && item.space !== currentBoardSpace) return false;
				if (boardGeneratedTopicFilter !== '全部专题' && item.topicScope !== boardGeneratedTopicFilter) return false;
				if (boardGeneratedRoundFilter === '本轮' && item.generationRound !== activeBoardGenerationRound) return false;
				if (boardGeneratedRoundFilter === '最近') {
					const recentRounds = new Set(
						boardGeneratedItems
							.map((entry) => entry.generationRound)
							.sort((a, b) => b - a)
							.slice(0, 3)
					);
					if (!recentRounds.has(item.generationRound)) return false;
				}
				return true;
			})
			.sort((a, b) => b.createdAt.localeCompare(a.createdAt))
			.map((item) => ({
				id: `board-source-generated-${item.id}`,
				sourceType: 'generated',
				sourceId: item.id,
				entityType: 'image',
				title: item.title,
				imageSrc: item.imageSrc,
				fallbackImageSrc: item.fallbackImageSrc,
				desc: item.promptSummary,
				meta: `${item.space} · ${item.topicScope} · 第 ${item.generationRound} 轮`,
				referenceControl: buildReferenceControlFromSource({
					sourceType: 'generated',
					entityType: 'image',
					title: item.title,
					desc: item.promptSummary,
					meta: `${item.space} · ${item.topicScope} · 第 ${item.generationRound} 轮`,
				}, { space: item.space }),
				generation: {
					status: item.status,
					round: item.generationRound,
					createdAt: item.createdAt,
					promptSummary: item.promptSummary,
					sourceContext: item.sourceContext,
					space: item.space,
					topicScope: item.topicScope,
					expertName: item.expertName,
				},
			}));
	}, [
		activeBoardGenerationRound,
		boardGeneratedItems,
		boardGeneratedRoundFilter,
		boardGeneratedTopicFilter,
		currentBoardSpace,
	]);

	const boardActiveSourceItems = useMemo(() => {
		if (boardSourceTab === 'inspiration') return inspirationBoardSourceItems;
		if (boardSourceTab === 'history') return historyBoardSourceItems;
		if (boardSourceTab === 'generated') return generatedBoardSourceItems;
		return radarBoardSourceItems;
	}, [boardSourceTab, generatedBoardSourceItems, historyBoardSourceItems, inspirationBoardSourceItems, radarBoardSourceItems]);

	const boardDeepBrowseColumnCount = 9 - boardDeepBrowseSizeLevel;

	const boardDeepBrowseSourceItems = useMemo(() => {
		if (!boardDeepBrowseTab) return [];
		if (boardDeepBrowseTab === 'inspiration') return inspirationBoardSourceItems;
		if (boardDeepBrowseTab === 'history') return historyBoardSourceItems;
		return radarBoardSourceItems;
	}, [boardDeepBrowseTab, historyBoardSourceItems, inspirationBoardSourceItems, radarBoardSourceItems]);

	const visibleBoardLibraryNavItems = useMemo<BoardLibraryNavItem[]>(() => {
		if (!boardDeepBrowseTab || boardDeepBrowseTab === 'history') return [];
		return BOARD_LIBRARY_NAV_ITEMS.reduce<BoardLibraryNavItem[]>((acc, item) => {
			const children = item.children.filter((child) =>
				boardDeepBrowseSourceItems.some((source) => boardLibraryItemMatchesKeywords(source, child.keywords))
			);
			const categoryKeywords = [
				...item.keywords,
				...item.children.flatMap((child) => child.keywords),
			];
			const hasContent = boardDeepBrowseSourceItems.some((source) =>
				boardLibraryItemMatchesKeywords(source, categoryKeywords)
			);
			if (hasContent) acc.push({ ...item, children });
			return acc;
		}, []);
	}, [boardDeepBrowseSourceItems, boardDeepBrowseTab]);

	const currentBoardLibraryNav = useMemo(
		() => visibleBoardLibraryNavItems.find((item) => item.key === boardLibraryNavKey) ?? null,
		[boardLibraryNavKey, visibleBoardLibraryNavItems]
	);

	useEffect(() => {
		if (!boardDeepBrowseTab || boardDeepBrowseTab === 'history') return;
		if (boardLibraryNavKey && !currentBoardLibraryNav) {
			setBoardLibraryNavKey(null);
			setBoardLibrarySubcategory(ALL_BOARD_LIBRARY_SUBCATEGORY);
			return;
		}
		if (
			currentBoardLibraryNav &&
			boardLibrarySubcategory !== ALL_BOARD_LIBRARY_SUBCATEGORY &&
			!currentBoardLibraryNav.children.some((child) => child.label === boardLibrarySubcategory)
		) {
			setBoardLibrarySubcategory(ALL_BOARD_LIBRARY_SUBCATEGORY);
		}
	}, [boardDeepBrowseTab, boardLibraryNavKey, boardLibrarySubcategory, currentBoardLibraryNav]);

	const boardSpaceOverviewCards = useMemo(
		() =>
			BOARD_CANVAS_SPACE_OPTIONS.filter((space): space is Exclude<BoardCanvasSpace, '全部'> => space !== '全部').map((space) => ({
				space,
				count: boardSpaceItemCounts[space] ?? 0,
			})),
		[boardSpaceItemCounts]
	);

	const filteredBoardSourceItems = useMemo(() => {
		if (boardSourceTab === 'generated') return boardActiveSourceItems;
		const query = boardQuery.trim().toLowerCase();
		if (!query) return boardActiveSourceItems;
		return boardActiveSourceItems.filter((item) =>
			[item.title, item.desc, item.meta].join(' ').toLowerCase().includes(query)
		);
	}, [boardActiveSourceItems, boardQuery, boardSourceTab]);

	const boardSourceDetailItems = useMemo(() => {
		const items = new Map<string, BoardSourceItem>();
		[
			...radarBoardSourceItems,
			...inspirationBoardSourceItems,
			...historyBoardSourceItems,
			...generatedBoardSourceItems,
		].forEach((item) => items.set(item.id, item));
		return Array.from(items.values());
	}, [generatedBoardSourceItems, historyBoardSourceItems, inspirationBoardSourceItems, radarBoardSourceItems]);

	const boardSourceDetailItem = useMemo(
		() => boardSourceDetailItems.find((item) => item.id === boardSourceDetailItemId) ?? null,
		[boardSourceDetailItems, boardSourceDetailItemId]
	);

	const boardSourceDetailShellStyle = useMemo<React.CSSProperties>(() => {
		const aspect = boardSourceDetailImageAspect && Number.isFinite(boardSourceDetailImageAspect)
			? Math.min(1.35, Math.max(0.34, boardSourceDetailImageAspect))
			: 1.08;
		return {
			gridTemplateColumns: `clamp(240px, calc(max(76vh, 560px) * ${aspect}), 752px) minmax(560px, 664px)`,
		};
	}, [boardSourceDetailImageAspect]);

	const boardSourceDetailImageStyle = useMemo<React.CSSProperties>(
		() => ({ backgroundColor: boardSourceDetailImageBackdrop }),
		[boardSourceDetailImageBackdrop]
	);

	const updateBoardSourceDetailImageMetrics = useCallback((image: HTMLImageElement) => {
		if (image.naturalWidth > 0 && image.naturalHeight > 0) {
			setBoardSourceDetailImageAspect(image.naturalWidth / image.naturalHeight);
		}

		try {
			const sampleSize = 32;
			const canvas = document.createElement('canvas');
			canvas.width = sampleSize;
			canvas.height = sampleSize;
			const context = canvas.getContext('2d', { willReadFrequently: true });
			if (!context) throw new Error('Canvas context unavailable');

			context.drawImage(image, 0, 0, sampleSize, sampleSize);
			const pixels = context.getImageData(0, 0, sampleSize, sampleSize).data;
			let red = 0;
			let green = 0;
			let blue = 0;
			let count = 0;

			for (let index = 0; index < pixels.length; index += 4) {
				const alpha = pixels[index + 3];
				if (alpha < 128) continue;
				const r = pixels[index];
				const g = pixels[index + 1];
				const b = pixels[index + 2];
				red += r;
				green += g;
				blue += b;
				count += 1;
			}

			if (count === 0) {
				setBoardSourceDetailImageBackdrop('#020617');
				return;
			}

			const nextRed = Math.round(red / count);
			const nextGreen = Math.round(green / count);
			const nextBlue = Math.round(blue / count);
			setBoardSourceDetailImageBackdrop(`rgb(${nextRed}, ${nextGreen}, ${nextBlue})`);
		} catch {
			setBoardSourceDetailImageBackdrop('#020617');
		}
	}, []);

	useEffect(() => {
		if (!boardSourceDetailItem) return;

		const handleKeyDown = (event: KeyboardEvent) => {
			if (event.key !== 'Escape') return;
			event.preventDefault();
			setBoardSourceDetailItemId(null);
		};

		window.addEventListener('keydown', handleKeyDown);
		return () => window.removeEventListener('keydown', handleKeyDown);
	}, [boardSourceDetailItem]);

	const boardDeepBrowseItems = useMemo(() => {
		if (!boardDeepBrowseTab) return [];
		const categoryFilteredItems =
			boardDeepBrowseTab === 'history' || !currentBoardLibraryNav
				? boardDeepBrowseSourceItems
				: boardDeepBrowseSourceItems.filter((item) => {
						if (boardLibrarySubcategory === ALL_BOARD_LIBRARY_SUBCATEGORY) {
							const categoryKeywords = [
								...currentBoardLibraryNav.keywords,
								...currentBoardLibraryNav.children.flatMap((child) => child.keywords),
							];
							return boardLibraryItemMatchesKeywords(item, categoryKeywords);
						}
						const activeChild = currentBoardLibraryNav.children.find((child) => child.label === boardLibrarySubcategory);
						return activeChild ? boardLibraryItemMatchesKeywords(item, activeChild.keywords) : true;
				  });
		const query = boardQuery.trim().toLowerCase();
		if (!query) return categoryFilteredItems;
		return categoryFilteredItems.filter((item) =>
			getBoardLibrarySearchText(item).includes(query)
		);
	}, [
		boardDeepBrowseTab,
		boardDeepBrowseSourceItems,
		boardLibrarySubcategory,
		boardQuery,
		currentBoardLibraryNav,
	]);

	useEffect(() => {
		if (!expandedBoardSourceItemId) return;
		if (!filteredBoardSourceItems.some((item) => item.id === expandedBoardSourceItemId)) {
			setExpandedBoardSourceItemId(null);
		}
	}, [expandedBoardSourceItemId, filteredBoardSourceItems]);

	useEffect(() => {
		if (!boardSourceDetailItemId) return;
		setBoardSourceDetailImageAspect(null);
		setBoardSourceDetailImageBackdrop('#020617');
		if (!boardSourceDetailItem) setBoardSourceDetailItemId(null);
	}, [boardSourceDetailItem, boardSourceDetailItemId]);

	const saveReferenceEditDraft = useCallback(() => {
		if (!referenceEditDraft) return;
		if (referenceEditDraft.target === 'canvas' && referenceEditDraft.canvasItemId) {
			setBoardCanvasItems((prev) =>
				prev.map((item) =>
					item.id === referenceEditDraft.canvasItemId
						? {
								...item,
								referenceControl: referenceEditDraft.control,
						  }
						: item
				)
			);
		}
		if (referenceEditDraft.target === 'source' && referenceEditDraft.sourceId) {
			const source = filteredBoardSourceItems.find((item) => item.id === referenceEditDraft.sourceId);
			if (source) addBoardCanvasItemWithReference(source, referenceEditDraft.control);
		}
		setReferenceEditDraft(null);
	}, [addBoardCanvasItemWithReference, filteredBoardSourceItems, referenceEditDraft]);

	const selectedBoardCanvasItem = useMemo(
		() => boardCanvasItems.find((item) => item.id === selectedBoardCanvasItemId) ?? null,
		[boardCanvasItems, selectedBoardCanvasItemId]
	);
	const getCanvasItemReferenceControl = useCallback(
		(item: BoardCanvasItem): BoardReferenceControl =>
			item.referenceControl ??
			buildReferenceControlFromSource(
				{
					sourceType: item.sourceType,
					entityType: item.entityType ?? (item.sourceTrace?.anchorId ? 'anchor' : 'image'),
					title: item.title,
					desc: item.desc,
					meta: item.meta,
				},
				{ space: currentBoardSpace }
			),
		[currentBoardSpace]
	);
	const selectedBoardCanvasReferenceControl = useMemo(
		() => (selectedBoardCanvasItem ? getCanvasItemReferenceControl(selectedBoardCanvasItem) : null),
		[getCanvasItemReferenceControl, selectedBoardCanvasItem]
	);
	const getCanvasItemIncludedAnchorIds = useCallback(
		(item: BoardCanvasItem, referenceControl: BoardReferenceControl, anchors: ResourceImageAnchor[]): string[] => {
			if (item.anchorIds && item.anchorIds.length > 0) return item.anchorIds;
			const anchorId = item.sourceTrace?.anchorId;
			if (referenceControl.kind === 'relation_card') {
				const relationAnchorIds = anchors.filter((anchor) => anchor.anchorMode === 'relation').map((anchor) => anchor.id);
				if (relationAnchorIds.length > 0) return relationAnchorIds;
			}
			if (anchorId) return [anchorId];
			return [];
		},
		[]
	);
	const getCanvasItemImageSeries = useCallback(
		(item: BoardCanvasItem): { resource: ResourceCardItem; images: ResourceSeriesImage[]; currentIndex: number } | null => {
			const projectId = item.sourceTrace?.projectId;
			if (!projectId) return null;
			const resource = resourceItems.find((entry) => entry.id === projectId);
			if (!resource || resource.imageSeries.length <= 0) return null;
			const currentImageId = item.sourceTrace?.imageId ?? item.sourceId;
			const currentIndex = Math.max(0, resource.imageSeries.findIndex((image) => image.id === currentImageId));
			return {
				resource,
				images: resource.imageSeries,
				currentIndex,
			};
		},
		[resourceItems]
	);
	const getCanvasItemAnchorMarkers = useCallback(
		(item: BoardCanvasItem, referenceControl: BoardReferenceControl): Array<{ id: string; x: number; y: number; summary?: string; title?: string; type?: ResourceAnchorType; topic?: string; included: boolean; primary?: boolean }> => {
			const imageId = item.sourceTrace?.imageId;
			const anchorId = item.sourceTrace?.anchorId;
			if ((referenceControl.kind === 'relation_card' || referenceControl.kind === 'scene_card') && imageId) {
				const anchors = activeResourceAnchorsByImageId[imageId] ?? [];
				if (anchors.length > 0) {
					const includedAnchorIds = new Set(getCanvasItemIncludedAnchorIds(item, referenceControl, anchors));
					return anchors.map((anchor) => ({
						id: anchor.id,
						x: anchor.x,
						y: anchor.y,
						title: anchor.title,
						type: anchor.type,
						topic: anchor.topic,
						summary: anchor.summary,
						included: referenceControl.kind === 'scene_card' ? true : includedAnchorIds.has(anchor.id),
						primary: anchor.id === anchorId,
					}));
				}
			}
			if (typeof item.anchorX === 'number' && typeof item.anchorY === 'number') {
				return [{
					id: anchorId ?? item.id,
					x: item.anchorX,
					y: item.anchorY,
					summary: item.anchorSummary,
					title: item.title,
					included: true,
					primary: true,
				}];
			}
			if (!anchorId || !imageId) return [];
			const anchor = (activeResourceAnchorsByImageId[imageId] ?? []).find((entry) => entry.id === anchorId);
			if (!anchor) return [];
			return [{
				id: anchor.id,
				x: anchor.x,
				y: anchor.y,
				title: anchor.title,
				type: anchor.type,
				topic: anchor.topic,
				summary: anchor.summary,
				included: true,
				primary: true,
			}];
		},
		[activeResourceAnchorsByImageId, getCanvasItemIncludedAnchorIds]
	);
	const selectedBoardCanvasAnchorMarkers = useMemo(
		() =>
			selectedBoardCanvasItem && selectedBoardCanvasReferenceControl
				? getCanvasItemAnchorMarkers(selectedBoardCanvasItem, selectedBoardCanvasReferenceControl)
				: [],
		[getCanvasItemAnchorMarkers, selectedBoardCanvasItem, selectedBoardCanvasReferenceControl]
	);
	const selectedBoardCanvasAnchorPanelStyle = useMemo<React.CSSProperties>(() => {
		if (!selectedBoardCanvasItem) return {};
		const imageHeight = getBoardCanvasItemHeight(selectedBoardCanvasItem) * boardCanvasView.zoom;
		const panelHeight = Math.max(320, imageHeight);
		return {
			left: `${boardCanvasView.x + (selectedBoardCanvasItem.x + selectedBoardCanvasItem.width) * boardCanvasView.zoom + 24}px`,
			top: '50%',
			height: `min(${panelHeight}px, calc(100% - 96px))`,
			transform: 'translateY(-50%)',
		};
	}, [boardCanvasView, selectedBoardCanvasItem]);
	const toggleBoardCanvasAnchorSelection = useCallback((itemId: string, anchorId: string) => {
		pushBoardCanvasUndoSnapshot(boardCanvasItemsRef.current);
		setSelectedBoardCanvasItemId(itemId);
		setBoardCanvasItems((prev) =>
			prev.map((item) => {
				if (item.id !== itemId) return item;
				const referenceControl = getCanvasItemReferenceControl(item);
				const imageId = item.sourceTrace?.imageId;
				const anchors = imageId ? activeResourceAnchorsByImageId[imageId] ?? [] : [];
				const currentIds = getCanvasItemIncludedAnchorIds(item, referenceControl, anchors);
				const hasAnchor = currentIds.includes(anchorId);
				if (hasAnchor && currentIds.length <= 1) return item;
				return {
					...item,
					anchorIds: hasAnchor ? currentIds.filter((id) => id !== anchorId) : uniqueList([...currentIds, anchorId]),
				};
			})
		);
	}, [activeResourceAnchorsByImageId, getCanvasItemIncludedAnchorIds, getCanvasItemReferenceControl, pushBoardCanvasUndoSnapshot]);
	const turnBoardCanvasSceneImage = useCallback((itemId: string, direction: -1 | 1) => {
		pushBoardCanvasUndoSnapshot(boardCanvasItemsRef.current);
		setSelectedBoardCanvasItemId(itemId);
		setBoardCanvasItems((prev) =>
			prev.map((item) => {
				if (item.id !== itemId) return item;
				const imageSeries = getCanvasItemImageSeries(item);
				if (!imageSeries || imageSeries.images.length <= 1) return item;
				const nextIndex = (imageSeries.currentIndex + direction + imageSeries.images.length) % imageSeries.images.length;
				const nextImage = imageSeries.images[nextIndex];
				const source = {
					sourceType: item.sourceType,
					entityType: 'image' as const,
					title: `${imageSeries.resource.title} · ${nextImage.name}`,
					desc: imageSeries.resource.desc,
					meta: `${imageSeries.resource.category} · ${toDisplaySpaceName(imageSeries.resource.space)}`,
				};
				return {
					...item,
					sourceId: nextImage.id,
					entityType: 'image',
					sourceTrace: buildResourceSourceTrace({ projectId: imageSeries.resource.id, imageId: nextImage.id }),
					referenceControl: buildReferenceControlFromSource(source, {
						tags: imageSeries.resource.tags,
						space: toDisplaySpaceName(imageSeries.resource.space),
					}),
					anchorIds: undefined,
					anchorX: undefined,
					anchorY: undefined,
					anchorSummary: undefined,
					title: source.title,
					imageSrc: nextImage.src,
					fallbackImageSrc: nextImage.fallbackSrc,
					desc: source.desc,
					meta: source.meta,
				};
			})
		);
	}, [getCanvasItemImageSeries, pushBoardCanvasUndoSnapshot]);
	const formatCanvasItemAnchorSelectionForPrompt = useCallback(
		(item: BoardCanvasItem, referenceControl: BoardReferenceControl) => {
			if (referenceControl.kind !== 'relation_card' && referenceControl.kind !== 'detail_card') return '';
			const imageId = item.sourceTrace?.imageId;
			const anchors = imageId ? activeResourceAnchorsByImageId[imageId] ?? [] : [];
			const includedIds = new Set(getCanvasItemIncludedAnchorIds(item, referenceControl, anchors));
			const includedAnchors = anchors.filter((anchor) => includedIds.has(anchor.id));
			if (includedAnchors.length === 0) {
				return item.anchorSummary ? `采用锚点: ${item.anchorSummary}` : '';
			}
			return `采用锚点: ${includedAnchors.map((anchor) => `${anchor.title}(${anchor.summary})`).join('；')}`;
		},
		[activeResourceAnchorsByImageId, getCanvasItemIncludedAnchorIds]
	);
	const boardReferencePackSummary = useMemo(() => {
		const activeItems = boardCanvasItems.filter((item) => !item.disabled);
		return {
			projectPack: activeItems.filter((item) => getCanvasItemReferenceControl(item).kind === 'project_pack').length,
			sceneCard: activeItems.filter((item) => getCanvasItemReferenceControl(item).kind === 'scene_card').length,
			detailCard: activeItems.filter((item) => getCanvasItemReferenceControl(item).kind === 'detail_card').length,
			relationCard: activeItems.filter((item) => getCanvasItemReferenceControl(item).kind === 'relation_card').length,
			prompt: activeItems
				.slice(0, 8)
				.map((item) => {
					const referenceControl = getCanvasItemReferenceControl(item);
					return `${item.title}\n${formatReferenceControlForPrompt(referenceControl)}${formatCanvasItemAnchorSelectionForPrompt(item, referenceControl) ? `\n${formatCanvasItemAnchorSelectionForPrompt(item, referenceControl)}` : ''}`;
				})
				.join('\n\n'),
		};
	}, [boardCanvasItems, formatCanvasItemAnchorSelectionForPrompt, getCanvasItemReferenceControl]);

	useEffect(() => {
		if (!activeBoardVisualBrief) {
			onBoardVisualBriefChange?.(null);
			return;
		}
		const hasReferencePack =
			boardReferencePackSummary.projectPack +
			boardReferencePackSummary.sceneCard +
			boardReferencePackSummary.detailCard +
			boardReferencePackSummary.relationCard > 0;
		const planAnnotationPrompt = formatPlanAnnotationsForPrompt(activeSpacePlanTopic?.annotations);
		const planReconstructionPrompt = formatFloorPlanReconstructionForPrompt(activeSpacePlanTopic?.reconstruction);
		const planPrompt = activeSpacePlanView
			? `\n\nPlan Base:\n${formatSpacePlanViewForPrompt(activeSpacePlanView)}${planReconstructionPrompt ? `\n${planReconstructionPrompt}` : ''}${planAnnotationPrompt ? `\n${planAnnotationPrompt}` : ''}`
			: '';
		const referencePrompt = hasReferencePack
			? `\n\nReference Pack:\n项目参考包 ${boardReferencePackSummary.projectPack} / 场景参考图 ${boardReferencePackSummary.sceneCard} / 局部锚点卡 ${boardReferencePackSummary.detailCard} / 关系参考组 ${boardReferencePackSummary.relationCard}\n${boardReferencePackSummary.prompt}`
			: '';
		onBoardVisualBriefChange?.({
			...activeBoardVisualBrief,
			visualPrompt: `${activeBoardVisualBrief.visualPrompt}${planPrompt}${referencePrompt}`,
		});
	}, [activeBoardVisualBrief, activeSpacePlanTopic?.annotations, activeSpacePlanTopic?.reconstruction, activeSpacePlanView, boardReferencePackSummary, onBoardVisualBriefChange]);
	const activeBoardVisualBriefTags = useMemo(
		() => (activeBoardVisualBrief ? getVisualBriefTags(activeBoardVisualBrief) : []),
		[activeBoardVisualBrief]
	);

	const updateActiveBoardVisualBrief = useCallback(
		(updater: (brief: BoardVisualBrief) => BoardVisualBrief) => {
			if (isBoardOverview) return;
			const space = currentBoardSpace as Exclude<BoardCanvasSpace, '全部'>;
			setBoardVisualBriefs((prev) => ({
				...prev,
				[space]: updater(prev[space] ?? createSystemVisualBrief(space)),
			}));
		},
		[currentBoardSpace, isBoardOverview]
	);

	const toggleVisualBriefTag = useCallback(
		(tag: string) => {
			updateActiveBoardVisualBrief((brief) => {
				const disabled = new Set(brief.disabledTags);
				if (disabled.has(tag)) disabled.delete(tag);
				else disabled.add(tag);
				return {
					...brief,
					status: brief.status === 'locked' ? 'locked' : 'edited',
					disabledTags: Array.from(disabled),
				};
			});
		},
		[updateActiveBoardVisualBrief]
	);

	const toggleVisualBriefTagLock = useCallback(
		(tag: string) => {
			updateActiveBoardVisualBrief((brief) => {
				const locked = new Set(brief.lockedTags);
				if (locked.has(tag)) locked.delete(tag);
				else locked.add(tag);
				return {
					...brief,
					status: 'edited',
					lockedTags: Array.from(locked),
				};
			});
		},
		[updateActiveBoardVisualBrief]
	);

	const updateVisualBriefCustomNote = useCallback(
		(note: string) => {
			updateActiveBoardVisualBrief((brief) => ({
				...brief,
				status: brief.status === 'locked' ? 'locked' : 'edited',
				customNote: note,
			}));
		},
		[updateActiveBoardVisualBrief]
	);

	const updateVisualBriefPrompt = useCallback(
		(prompt: string) => {
			updateActiveBoardVisualBrief((brief) => ({
				...brief,
				status: brief.status === 'locked' ? 'locked' : 'edited',
				visualPrompt: prompt,
			}));
		},
		[updateActiveBoardVisualBrief]
	);

	const resetActiveVisualBrief = useCallback(() => {
		if (isBoardOverview) return;
		const space = currentBoardSpace as Exclude<BoardCanvasSpace, '全部'>;
		setBoardVisualBriefs((prev) => ({
			...prev,
			[space]: createSystemVisualBrief(space),
		}));
	}, [currentBoardSpace, isBoardOverview]);

	const toggleActiveVisualBriefLock = useCallback(() => {
		updateActiveBoardVisualBrief((brief) => ({
			...brief,
			status: brief.status === 'locked' ? 'edited' : 'locked',
		}));
	}, [updateActiveBoardVisualBrief]);

	const renderBoardInformationWhiteboard = () => {
		if (!activeBoardVisualBrief) return null;

		const disabledTags = new Set(activeBoardVisualBrief.disabledTags);
		const visibleTags = activeBoardVisualBriefTags.filter((tag) => !disabledTags.has(tag));
		const statusLabel: Record<BoardVisualBriefStatus, string> = {
			auto: '自动综合',
			edited: '已编辑',
			locked: '已锁定',
			stale: '待刷新',
		};

		return (
			<section className="shrink-0 border-b border-slate-200 bg-white px-4 py-4">
				<div className="flex items-start justify-between gap-3">
					<div className="min-w-0">
						<div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Information Board</div>
						<h3 className="mt-1 text-base font-semibold text-slate-950">信息白板 · {activeBoardVisualBrief.space}</h3>
						<p className="mt-1 text-[12px] leading-5 text-slate-500">{activeBoardVisualBrief.summary}</p>
					</div>
					<span
						className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
							activeBoardVisualBrief.status === 'locked'
								? 'border-emerald-200 bg-emerald-50 text-emerald-700'
								: activeBoardVisualBrief.status === 'stale'
									? 'border-amber-200 bg-amber-50 text-amber-700'
									: 'border-slate-200 bg-slate-50 text-slate-600'
						}`}
					>
						{statusLabel[activeBoardVisualBrief.status]}
					</span>
				</div>

				<div className="mt-3 border-l-2 border-slate-200 pl-3 text-[13px] leading-6 text-slate-700">
					{activeBoardVisualBrief.designIntent}
				</div>

				<div className="mt-3 flex flex-wrap gap-1.5">
					{activeBoardVisualBriefTags.slice(0, expandedBoardVisualBrief ? 32 : 12).map((tag) => {
						const disabled = disabledTags.has(tag);
						const locked = activeBoardVisualBrief.lockedTags.includes(tag);
						return (
							<button
								key={`board-visual-brief-tag-${tag}`}
								type="button"
								onClick={() => toggleVisualBriefTag(tag)}
								onDoubleClick={() => toggleVisualBriefTagLock(tag)}
								className={`rounded-full border px-2.5 py-1 text-[11px] font-medium transition ${
									disabled
										? 'border-slate-200 bg-slate-50 text-slate-300 line-through'
										: locked
											? 'border-sky-200 bg-sky-50 text-sky-700'
											: tag.startsWith('避免:')
												? 'border-rose-200 bg-rose-50 text-rose-700'
												: 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
								}`}
								title={locked ? '已锁定，双击可解除锁定' : '点击启用/停用，双击锁定'}
							>
								{locked ? '锁 ' : ''}{tag}
							</button>
						);
					})}
				</div>

				<div className="mt-3 grid grid-cols-3 gap-2">
					<button onClick={toggleActiveVisualBriefLock} className="rounded-full border border-slate-200 px-3 py-1.5 text-[12px] font-medium text-slate-600 hover:bg-slate-50">
						{activeBoardVisualBrief.status === 'locked' ? '解除锁定' : '锁定白板'}
					</button>
					<button onClick={() => setExpandedBoardVisualBrief((prev) => !prev)} className="rounded-full border border-slate-200 px-3 py-1.5 text-[12px] font-medium text-slate-600 hover:bg-slate-50">
						{expandedBoardVisualBrief ? '收起详情' : '展开详情'}
					</button>
					<button onClick={resetActiveVisualBrief} className="rounded-full border border-slate-200 px-3 py-1.5 text-[12px] font-medium text-slate-600 hover:bg-slate-50">
						重置
					</button>
				</div>

				<label className="mt-3 block">
					<div className="mb-1 text-[11px] font-medium text-slate-400">本空间备注</div>
					<textarea
						value={activeBoardVisualBrief.customNote}
						onChange={(event) => updateVisualBriefCustomNote(event.target.value)}
						placeholder="补充这个空间的气质、材料或出图注意事项"
						rows={2}
						className="w-full resize-none rounded-none border border-slate-200 bg-slate-50 px-3 py-2 text-[12px] leading-5 text-slate-700 outline-none focus:border-sky-300 focus:bg-white"
					/>
				</label>

				{expandedBoardVisualBrief && (
					<div className="mt-3 space-y-3">
						<label className="block">
							<div className="mb-1 text-[11px] font-medium text-slate-400">生图基线提示词</div>
							<textarea
								value={activeBoardVisualBrief.visualPrompt}
								onChange={(event) => updateVisualBriefPrompt(event.target.value)}
								rows={5}
								className="w-full resize-y rounded-none border border-slate-200 bg-white px-3 py-2 text-[12px] leading-5 text-slate-700 outline-none focus:border-sky-300"
							/>
						</label>
						<div>
							<div className="mb-1 text-[11px] font-medium text-slate-400">来源绑定</div>
							<div className="space-y-1.5">
								{activeBoardVisualBrief.sourceRefs.slice(0, 4).map((ref) => (
									<div key={`board-visual-brief-source-${ref.title}`} className="border border-slate-200 bg-slate-50 px-3 py-2">
										<div className="truncate text-[12px] font-medium text-slate-800">{ref.title}</div>
										<div className="mt-0.5 truncate text-[11px] text-slate-400">{ref.section} · {ref.status}</div>
									</div>
								))}
							</div>
						</div>
					</div>
				)}

				{visibleTags.length === 0 && (
					<div className="mt-2 text-[12px] text-amber-600">当前标签都被停用，建议恢复至少一个风格或材料约束。</div>
				)}
			</section>
		);
	};

	const stageOptions: string[] = [
		ALL_STAGE,
		'S1 意图显影',
		'S2 分析扩展',
		'S3 审阅裁决',
		'S4 定向收束',
		'S5 缺口补全',
		'S6 定版冻结',
	];

	const statusOptions: string[] = [ALL_STATUS, '进行中', '待审', '已审', '已冻结', '待验证'];
	const anchorOptions: string[] = [ALL_ANCHOR, 'AlignedBrief', 'SPG', 'InitialDesignPack', 'EvidenceOnly'];
	const topicOptions: string[] = [ALL_TOPIC, '用户', '市场', '竞品', '空间', '动线', '预算', '品牌', '色彩', '材料', '灯光', '家具'];

	const getCardDisplayTitle = (card: ProjectFileCard) => {
		if (fileViewMode === '统一视图') {
			if (card.spaceScope !== '全局') return `${toDisplaySpaceName(card.spaceScope)} · ${card.title}`;
			return `${card.stage} · ${card.title}`;
		}
		return card.title;
	};

	const openPlanUploadPicker = useCallback((space: Exclude<BoardCanvasSpace, '全部'>) => {
		setPendingPlanUploadSpace(space);
		planUploadInputRef.current?.click();
	}, []);

	const handleOpenPlanViewer = useCallback((space: Exclude<BoardCanvasSpace, '全部'>) => {
		setPlanViewerSpace(space);
		setPlanViewerZoom(1);
		setPlanViewerTool('select');
		setSelectedPlanElementId(null);
		setPlanElementDrawMode(null);
		setPlanDrawGeometryMode('rect');
		setPlanElementDraft(null);
		setPlanPolygonDraftPoints([]);
		setPlanPathDraftPoints([]);
	}, []);

	const handlePlanUploadChange = useCallback(async (event: ChangeEvent<HTMLInputElement>) => {
		const file = event.target.files?.[0];
		const space = pendingPlanUploadSpace;
		if (!file || !space) return;
		const lowerName = file.name.toLowerCase();
		const sourceType: SpacePlanTopicState['sourceType'] =
			lowerName.endsWith('.dwg') ? 'cad' :
			lowerName.endsWith('.dxf') ? 'dxf' :
			lowerName.endsWith('.pdf') ? 'pdf' :
			'image';
		setPlanUploadBusySpace(space);
		try {
			const formData = new FormData();
			formData.append('file', file);
			formData.append('sessionId', resolvedBoardSessionId);
			formData.append('space', space);
			const response = await fetch('/api/plan-drawings', {
				method: 'POST',
				body: formData,
			});
			if (!response.ok) throw new Error(`Upload failed: ${response.status}`);
			const result = await response.json() as {
				url: string;
				mimeType: string;
				size: number;
				parseResult?: {
					status?: 'uploaded' | 'parsed' | 'needs_conversion';
					message?: string;
					layers?: string[];
					entityCounts?: Record<string, number>;
				};
			};
			const nextStatus: SpacePlanTopicState['status'] = result.parseResult?.status === 'parsed' ? 'parsed' : 'uploaded';
			setSpacePlanTopics((prev) => ({
				...prev,
				[space]: {
					...(prev[space] ?? createDefaultSpacePlanTopicStates()[space]),
					space,
					status: nextStatus,
					sourceType,
					uploadedFileName: file.name,
					uploadedFileUrl: result.url,
					uploadedFileSize: result.size,
					mimeType: result.mimeType,
					parseMessage: result.parseResult?.message,
					parsedLayers: result.parseResult?.layers,
					parsedEntityCounts: result.parseResult?.entityCounts,
					reconstruction: createDefaultFloorPlanReconstruction(space, sourceType),
					updatedAt: new Date().toLocaleString('zh-CN', {
						month: '2-digit',
						day: '2-digit',
						hour: '2-digit',
						minute: '2-digit',
					}),
					viewChain: sourceType === 'image' || sourceType === 'pdf' ? ['floor', 'space'] : ['project', 'floor', 'space'],
				},
			}));
			handleOpenPlanViewer(space);
		} catch (error) {
			console.error('[CockpitPanel] plan upload failed:', error);
			setSpacePlanTopics((prev) => ({
				...prev,
				[space]: {
					...(prev[space] ?? createDefaultSpacePlanTopicStates()[space]),
					space,
					status: 'stale',
					sourceType,
					uploadedFileName: file.name,
					parseMessage: '上传失败，请检查文件格式或服务端写入权限。',
				},
			}));
		} finally {
			event.target.value = '';
			setPendingPlanUploadSpace(null);
			setPlanUploadBusySpace(null);
		}
	}, [handleOpenPlanViewer, pendingPlanUploadSpace, resolvedBoardSessionId]);

	const handlePlanViewerZoom = useCallback((delta: number) => {
		setPlanViewerZoom((current) => Math.min(3, Math.max(0.35, Number((current + delta).toFixed(2)))));
	}, []);

	const handlePlanViewerWheel = useCallback((event: ReactWheelEvent<Element>) => {
		event.preventDefault();
		event.stopPropagation();
		const viewport = planViewerCanvasRef.current ?? event.currentTarget;
		const rect = viewport.getBoundingClientRect();
		const nextZoom = Math.min(3, Math.max(0.35, Number((planViewerZoom + (event.deltaY > 0 ? -0.12 : 0.12)).toFixed(2))));
		const focusX = (viewport.scrollLeft + event.clientX - rect.left) / planViewerZoom;
		const focusY = (viewport.scrollTop + event.clientY - rect.top) / planViewerZoom;
		setPlanViewerZoom(nextZoom);
		requestAnimationFrame(() => {
			viewport.scrollLeft = focusX * nextZoom - (event.clientX - rect.left);
			viewport.scrollTop = focusY * nextZoom - (event.clientY - rect.top);
		});
	}, [planViewerZoom]);

	const addPlanAnnotation = useCallback((space: Exclude<BoardCanvasSpace, '全部'>, event: ReactMouseEvent<HTMLDivElement>) => {
		if (planViewerTool === 'select') return;
		const rect = event.currentTarget.getBoundingClientRect();
		const x = Math.min(0.98, Math.max(0.02, (event.clientX - rect.left) / rect.width));
		const y = Math.min(0.98, Math.max(0.02, (event.clientY - rect.top) / rect.height));
		const tone = getPlanAnnotationTone(planViewerTool);
		setSpacePlanTopics((prev) => {
			const current = prev[space] ?? createDefaultSpacePlanTopicStates()[space];
			const annotations = current.annotations ?? [];
			return {
				...prev,
				[space]: {
					...current,
					status: 'bound',
					parseMessage: current.parseMessage ?? '已在图纸上建立空间标注，可同步到方案画布 Plan Base。',
					annotations: [
						...annotations,
						{
							id: `plan-annotation-${Date.now()}-${annotations.length + 1}`,
							label: `${tone.label} ${annotations.length + 1}`,
							kind: planViewerTool,
							x,
							y,
							createdAt: new Date().toLocaleString('zh-CN', {
								month: '2-digit',
								day: '2-digit',
								hour: '2-digit',
								minute: '2-digit',
							}),
						},
					],
				},
			};
		});
	}, [planViewerTool]);

	const removePlanAnnotation = useCallback((space: Exclude<BoardCanvasSpace, '全部'>, annotationId: string) => {
		setSpacePlanTopics((prev) => {
			const current = prev[space] ?? createDefaultSpacePlanTopicStates()[space];
			return {
				...prev,
				[space]: {
					...current,
					status: 'bound',
					annotations: (current.annotations ?? []).filter((annotation) => annotation.id !== annotationId),
				},
			};
		});
	}, []);

	const updatePlanElement = useCallback((
		space: Exclude<BoardCanvasSpace, '全部'>,
		elementId: string,
		patch: Partial<FloorPlanElement>
	) => {
		setSpacePlanTopics((prev) => {
			const current = prev[space] ?? createDefaultSpacePlanTopicStates()[space];
			const reconstruction = current.reconstruction ?? createDefaultFloorPlanReconstruction(space, current.sourceType);
			return {
				...prev,
				[space]: {
					...current,
					status: 'bound',
					reconstruction: {
						...reconstruction,
						elements: (reconstruction.elements ?? []).map((element) =>
							element.id === elementId ? { ...element, ...patch, status: 'edited' } : element
						),
						updatedAt: new Date().toLocaleString('zh-CN', {
							month: '2-digit',
							day: '2-digit',
							hour: '2-digit',
							minute: '2-digit',
						}),
					},
				},
			};
		});
	}, []);

	const deletePlanElement = useCallback((space: Exclude<BoardCanvasSpace, '全部'>, elementId: string) => {
		setSpacePlanTopics((prev) => {
			const current = prev[space] ?? createDefaultSpacePlanTopicStates()[space];
			const reconstruction = current.reconstruction ?? createDefaultFloorPlanReconstruction(space, current.sourceType);
			const nextElements = (reconstruction.elements ?? []).filter((element) => element.id !== elementId);
			const nextObjectCounts = {
				...reconstruction.objectCounts,
				wall: nextElements.filter((element) => element.kind === 'wall_trace').length,
				door: nextElements.filter((element) => element.kind === 'door').length,
				window: nextElements.filter((element) => element.kind === 'window').length,
			};
			return {
				...prev,
				[space]: {
					...current,
					status: 'bound',
					parseMessage: '已删除重构对象，请继续校正 FloorPlanIR。',
					reconstruction: {
						...reconstruction,
						elements: nextElements,
						objectCounts: nextObjectCounts,
						spaceBoundaryCount: nextElements.filter((element) => element.kind === 'space_boundary').length,
						functionZoneCount: nextElements.filter((element) => element.kind === 'function_zone').length,
					},
				},
			};
		});
		setSelectedPlanElementId((current) => current === elementId ? null : current);
	}, []);

	const resetPlanReconstruction = useCallback((space: Exclude<BoardCanvasSpace, '全部'>) => {
		setSpacePlanTopics((prev) => {
			const current = prev[space] ?? createDefaultSpacePlanTopicStates()[space];
			return {
				...prev,
				[space]: {
					...current,
					status: current.uploadedFileUrl ? 'uploaded' : 'synced',
					parseMessage: '已重置重构对象，原图保留为底图参考。',
					reconstruction: createDefaultFloorPlanReconstruction(space, current.sourceType),
				},
			};
		});
		setSelectedPlanElementId(null);
		setPlanElementDrawMode(null);
		setPlanDrawGeometryMode('rect');
		setPlanElementDraft(null);
		setPlanPolygonDraftPoints([]);
		setPlanPathDraftPoints([]);
	}, []);

	const getFloorPlanPointsBounds = useCallback((points: FloorPlanPoint[]) => {
		const xs = points.map((point) => point.x);
		const ys = points.map((point) => point.y);
		const x = Math.min(...xs);
		const y = Math.min(...ys);
		const right = Math.max(...xs);
		const bottom = Math.max(...ys);
		return { x, y, w: right - x, h: bottom - y };
	}, []);

	const getFloorPlanPolygonArea = useCallback((points: FloorPlanPoint[]) => {
		if (points.length < 3) return 0;
		const sum = points.reduce((total, point, index) => {
			const next = points[(index + 1) % points.length];
			return total + point.x * next.y - next.x * point.y;
		}, 0);
		return Math.abs(sum) / 2;
	}, []);

	const addPlanElement = useCallback((
		space: Exclude<BoardCanvasSpace, '全部'>,
		kind: FloorPlanElementKind,
		rect: { x: number; y: number; w: number; h: number },
		options?: { geometryType?: FloorPlanGeometryType; points?: FloorPlanPoint[] }
	) => {
		setSpacePlanTopics((prev) => {
			const current = prev[space] ?? createDefaultSpacePlanTopicStates()[space];
			const reconstruction = current.reconstruction ?? createDefaultFloorPlanReconstruction(space, current.sourceType);
			const elements = reconstruction.elements ?? [];
			const index = elements.filter((element) => element.kind === kind).length + 1;
			const mmPerNormalizedX = reconstruction.scaleCalibration?.mmPerPixel ? reconstruction.scaleCalibration.mmPerPixel * 1000 : 21000;
			const mmPerNormalizedY = reconstruction.scaleCalibration?.mmPerPixel ? reconstruction.scaleCalibration.mmPerPixel * 1000 : 15000;
			const widthMm = Math.max(100, Math.round(rect.w * mmPerNormalizedX));
			const depthMm = Math.max(100, Math.round(rect.h * mmPerNormalizedY));
			const normalizedArea = options?.points && options.points.length >= 3 ? getFloorPlanPolygonArea(options.points) : rect.w * rect.h;
			const areaSqm = Number(((normalizedArea * mmPerNormalizedX * mmPerNormalizedY) / 1000000).toFixed(1));
			const label =
				kind === 'analysis_region' ? `有效识别区 ${index}` :
				kind === 'space_boundary' ? `${space}边界` :
				kind === 'function_zone' ? `功能区 ${index}` :
				kind === 'wall_trace' ? `墙线 ${index}` :
				kind === 'door' ? `门洞 ${index}` :
				kind === 'window' ? `窗/开口 ${index}` :
				`高度标记 ${index}`;
			const nextElement: FloorPlanElement = {
				id: `floor-ir-${kind}-${Date.now()}`,
				kind,
				label,
				geometryType: options?.geometryType ?? 'rect',
				...rect,
				points: options?.points,
				widthMm,
				depthMm,
				areaSqm: kind === 'space_boundary' || kind === 'function_zone' || kind === 'analysis_region' ? areaSqm : undefined,
				confidence: 1,
				status: 'edited',
			};
			const nextElements = [...elements, nextElement];
			const nextObjectCounts = {
				...reconstruction.objectCounts,
				wall: nextElements.filter((element) => element.kind === 'wall_trace').length,
				door: nextElements.filter((element) => element.kind === 'door').length,
				window: nextElements.filter((element) => element.kind === 'window').length,
			};
			return {
				...prev,
				[space]: {
					...current,
					status: 'bound',
					parseMessage: '已基于原图手动生成重构对象，请继续校准尺寸、面积和空间对齐。',
					reconstruction: {
						...reconstruction,
						status: reconstruction.status === 'raw' ? 'traced' : reconstruction.status,
						elements: nextElements,
						objectCounts: nextObjectCounts,
						spaceBoundaryCount: nextElements.filter((element) => element.kind === 'space_boundary').length,
						functionZoneCount: nextElements.filter((element) => element.kind === 'function_zone').length,
						pendingIssues: ['请确认对象边界与尺寸', '待校准比例尺'],
						updatedAt: new Date().toLocaleString('zh-CN', {
							month: '2-digit',
							day: '2-digit',
							hour: '2-digit',
							minute: '2-digit',
						}),
					},
				},
			};
		});
	}, [getFloorPlanPolygonArea]);

	const getPlanElementPointer = useCallback((event: ReactMouseEvent<Element>) => {
		const rect = event.currentTarget.getBoundingClientRect();
		return {
			x: Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)),
			y: Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height)),
		};
	}, []);

	const handlePlanElementPointerDown = useCallback((event: ReactMouseEvent<Element>) => {
		if (!planElementDrawMode) return;
		if (planDrawGeometryMode === 'polygon') return;
		event.preventDefault();
		event.stopPropagation();
		const point = getPlanElementPointer(event);
		setSelectedPlanElementId(null);
		setPlanViewerTool('select');
		if (planDrawGeometryMode === 'path') {
			setPlanPathDraftPoints([point]);
			return;
		}
		setPlanElementDraft({ startX: point.x, startY: point.y, x: point.x, y: point.y, w: 0, h: 0 });
	}, [getPlanElementPointer, planDrawGeometryMode, planElementDrawMode]);

	const handlePlanElementPointerMove = useCallback((event: ReactMouseEvent<Element>) => {
		if (!planElementDrawMode) return;
		event.preventDefault();
		const point = getPlanElementPointer(event);
		if (planDrawGeometryMode === 'path') {
			setPlanPathDraftPoints((current) => {
				const last = current[current.length - 1];
				if (last && Math.hypot(last.x - point.x, last.y - point.y) < 0.006) return current;
				return [...current, point].slice(-260);
			});
			return;
		}
		if (!planElementDraft) return;
		setPlanElementDraft({
			...planElementDraft,
			x: Math.min(planElementDraft.startX, point.x),
			y: Math.min(planElementDraft.startY, point.y),
			w: Math.abs(point.x - planElementDraft.startX),
			h: Math.abs(point.y - planElementDraft.startY),
		});
	}, [getPlanElementPointer, planDrawGeometryMode, planElementDraft, planElementDrawMode]);

	const handlePlanElementPointerUp = useCallback((event: ReactMouseEvent<Element>) => {
		if (!planViewerSpace || !planElementDrawMode) return;
		event.preventDefault();
		event.stopPropagation();
		if (planDrawGeometryMode === 'path') {
			if (planPathDraftPoints.length >= 4) {
				const bounds = getFloorPlanPointsBounds(planPathDraftPoints);
				addPlanElement(planViewerSpace, planElementDrawMode, bounds, {
					geometryType: 'path',
					points: planPathDraftPoints,
				});
			}
			setPlanPathDraftPoints([]);
			return;
		}
		if (!planElementDraft) return;
		if (planElementDraft.w > 0.005 && planElementDraft.h > 0.005) {
			addPlanElement(planViewerSpace, planElementDrawMode, {
				x: planElementDraft.x,
				y: planElementDraft.y,
				w: planElementDraft.w,
				h: planElementDraft.h,
			});
		}
		setPlanElementDraft(null);
	}, [addPlanElement, getFloorPlanPointsBounds, planDrawGeometryMode, planElementDraft, planElementDrawMode, planPathDraftPoints, planViewerSpace]);

	const finishPlanPolygonDraft = useCallback(() => {
		if (!planViewerSpace || !planElementDrawMode || planPolygonDraftPoints.length < 3) return;
		const bounds = getFloorPlanPointsBounds(planPolygonDraftPoints);
		addPlanElement(planViewerSpace, planElementDrawMode, bounds, {
			geometryType: 'polygon',
			points: planPolygonDraftPoints,
		});
		setPlanPolygonDraftPoints([]);
	}, [addPlanElement, getFloorPlanPointsBounds, planElementDrawMode, planPolygonDraftPoints, planViewerSpace]);

	const handlePlanElementClick = useCallback((event: ReactMouseEvent<Element>) => {
		if (!planElementDrawMode || planDrawGeometryMode !== 'polygon') return;
		event.preventDefault();
		event.stopPropagation();
		const point = getPlanElementPointer(event);
		setSelectedPlanElementId(null);
		setPlanViewerTool('select');
		setPlanPolygonDraftPoints((current) => [...current, point]);
	}, [getPlanElementPointer, planDrawGeometryMode, planElementDrawMode]);

	const handlePlanElementDoubleClick = useCallback((event: ReactMouseEvent<Element>) => {
		if (!planElementDrawMode || planDrawGeometryMode !== 'polygon') return;
		event.preventDefault();
		event.stopPropagation();
		finishPlanPolygonDraft();
	}, [finishPlanPolygonDraft, planDrawGeometryMode, planElementDrawMode]);

	const getPlanTopicStatusLabel = (status: SpacePlanTopicState['status']) => {
		switch (status) {
			case 'missing':
				return '缺失';
			case 'uploaded':
				return '已上传';
			case 'parsed':
				return '已解析';
			case 'bound':
				return '已绑定';
			case 'stale':
				return '待同步';
			case 'synced':
			default:
				return '已同步';
		}
	};

	const getReconstructionStatusLabel = (status?: FloorPlanReconstructionStatus) => {
		switch (status) {
			case 'normalized':
				return '已标准化';
			case 'traced':
				return '已描边';
			case 'zoned':
				return '已分区';
			case 'aligned':
				return '已对齐';
			case 'height_ready':
				return '高度已补全';
			case 'raw':
			default:
				return '原始图纸';
		}
	};

	const updatePlanReconstruction = useCallback((
		space: Exclude<BoardCanvasSpace, '全部'>,
		step: 'normalize' | 'trace' | 'zone' | 'align' | 'height'
	) => {
		setSpacePlanTopics((prev) => {
			const current = prev[space] ?? createDefaultSpacePlanTopicStates()[space];
			const base = current.reconstruction ?? createDefaultFloorPlanReconstruction(space, current.sourceType);
			const updatedAt = new Date().toLocaleString('zh-CN', {
				month: '2-digit',
				day: '2-digit',
				hour: '2-digit',
				minute: '2-digit',
			});
			const next: FloorPlanReconstruction =
				step === 'normalize' ? {
					...base,
					status: 'normalized',
					irVersion: 'FloorPlanIR draft v0.2',
					coordinateSystem: {
						...base.coordinateSystem,
						scaleStatus: base.sourceFormat === 'image' || base.sourceFormat === 'pdf' ? 'estimated' : base.coordinateSystem.scaleStatus,
					},
					pendingIssues: ['待自动描边', '待功能分区', '待补充高度'],
					updatedAt,
				} :
				step === 'trace' ? {
					...base,
					status: 'traced',
					irVersion: 'FloorPlanIR draft v0.2',
					objectCounts: {
						...base.objectCounts,
					},
					spaceBoundaryCount: (base.elements ?? []).filter((element) => element.kind === 'space_boundary').length,
					elements: base.elements ?? [],
					coordinateSystem: { ...base.coordinateSystem, northStatus: 'detected' },
					pendingIssues: ['无真实解析结果，请在左侧手动框选空间边界', '待功能分区', '待补充高度'],
					updatedAt,
				} :
				step === 'zone' ? {
					...base,
					status: 'zoned',
					functionZoneCount: (base.elements ?? []).filter((element) => element.kind === 'function_zone').length,
					elements: base.elements ?? [],
					pendingIssues: (base.elements ?? []).some((element) => element.kind === 'space_boundary')
						? ['待与项目空间树对齐', '待补充高度']
						: ['请先手动框选空间边界，再划分功能区'],
					updatedAt,
				} :
				step === 'align' ? {
					...base,
					status: 'aligned',
					alignment: { matchedSpace: space, confidence: 0.92, status: 'confirmed' },
					elements: (base.elements ?? []).map((element) => ({ ...element, status: element.status === 'candidate' ? 'confirmed' : element.status })),
					pendingIssues: ['待补充高度'],
					updatedAt,
				} :
				{
					...base,
					status: 'height_ready',
					heightProfile: {
						ceilingHeight: base.heightProfile.ceilingHeight ?? 3200,
						beamBottomHeight: base.heightProfile.beamBottomHeight ?? 2700,
						doorHeight: base.heightProfile.doorHeight ?? 2300,
						windowSillHeight: base.heightProfile.windowSillHeight ?? 450,
						status: 'estimated',
					},
					elements: base.elements ?? [],
					pendingIssues: [],
					updatedAt,
				};

			return {
				...prev,
				[space]: {
					...current,
					status: next.status === 'height_ready' ? 'synced' : 'bound',
					parseMessage: `已生成统一重构对象：${getReconstructionStatusLabel(next.status)}。`,
					reconstruction: next,
				},
			};
		});
	}, []);

	const autoTraceRenderedPlan = useCallback(async (space: Exclude<BoardCanvasSpace, '全部'>) => {
		const viewport = planViewerCanvasRef.current;
		const current = spacePlanTopics[space] ?? createDefaultSpacePlanTopicStates()[space];
		if (!viewport || !current.uploadedFileUrl) {
			setPlanAutoTraceError('请先打开已上传的图纸，再执行自动识别。');
			return;
		}

		setPlanAutoTraceBusy(true);
		setPlanAutoTraceError(null);
		try {
			await new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
			const reconstructionForRegion = current.reconstruction ?? createDefaultFloorPlanReconstruction(space, current.sourceType);
			const effectiveRegion =
				(reconstructionForRegion.elements ?? []).find((element) => element.kind === 'analysis_region' && element.status !== 'candidate') ??
				(reconstructionForRegion.elements ?? []).find((element) => element.kind === 'analysis_region');
			if (!effectiveRegion) {
				setPlanElementDrawMode('analysis_region');
				throw new Error('请先点击“框选有效区”，在左侧图纸上圈出需要识别的真实平面范围，再执行检查描边。');
			}
			setSpacePlanTopics((prev) => {
				const topic = prev[space] ?? createDefaultSpacePlanTopicStates()[space];
				const reconstruction = topic.reconstruction ?? createDefaultFloorPlanReconstruction(space, topic.sourceType);
				const preservedElements = (reconstruction.elements ?? []).filter((element) =>
					element.kind === 'analysis_region' || element.status === 'edited' || element.status === 'confirmed'
				);
				return {
					...prev,
					[space]: {
						...topic,
						status: 'bound',
						parseMessage: '正在调用 FloorPlanIR API 进行服务端矢量识别...',
						reconstruction: {
							...reconstruction,
							status: 'traced',
							irVersion: 'FloorPlanIR api tracing',
							elements: preservedElements,
							objectCounts: {
								...reconstruction.objectCounts,
								wall: preservedElements.filter((element) => element.kind === 'wall_trace').length,
								door: preservedElements.filter((element) => element.kind === 'door').length,
								window: preservedElements.filter((element) => element.kind === 'window').length,
							},
							functionZoneCount: preservedElements.filter((element) => element.kind === 'function_zone').length,
							spaceBoundaryCount: preservedElements.filter((element) => element.kind === 'space_boundary').length,
							pendingIssues: ['服务端识别中，旧自动候选已清理'],
						},
					},
				};
			});

			const apiResponse = await fetch('/api/floor-plan/trace', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					fileUrl: current.uploadedFileUrl,
					mimeType: current.mimeType,
					region: {
						x: effectiveRegion.x,
						y: effectiveRegion.y,
						w: effectiveRegion.w,
						h: effectiveRegion.h,
					},
				}),
			});
			if (apiResponse.ok) {
				const apiTrace = await apiResponse.json() as {
					status?: 'traced' | 'unsupported' | 'no_result' | string;
					compilerStatus?: 'candidate_ready' | 'gate_failed' | 'ir_ready' | string;
					message?: string;
					elements?: FloorPlanElement[];
					scaleCalibration?: { mmPerNormalized?: number; source?: string; samples?: number };
					issues?: string[];
					issueMessages?: string[];
					diagnostics?: {
						rawSegments?: number;
						scopedSegments?: number;
						wallSegments?: number;
						filteredOut?: number;
						dimensionsInRegion?: number;
						closedSpaces?: number;
						mode?: string;
						classCounts?: Partial<Record<'wall' | 'dimension' | 'hatch' | 'symbol' | 'noise', number>>;
					};
				};
				if ((apiTrace.status === 'traced' || apiTrace.compilerStatus === 'gate_failed' || apiTrace.compilerStatus === 'ir_ready') && Array.isArray(apiTrace.elements) && apiTrace.elements.length > 0) {
					const apiElements = apiTrace.elements;
					setSpacePlanTopics((prev) => {
						const topic = prev[space] ?? createDefaultSpacePlanTopicStates()[space];
						const reconstruction = topic.reconstruction ?? createDefaultFloorPlanReconstruction(space, topic.sourceType);
						const manualElements = (reconstruction.elements ?? []).filter((element) =>
							element.kind === 'analysis_region' || element.status === 'edited' || element.status === 'confirmed'
						);
						const nextElements = [...manualElements, ...apiElements.map((element) => ({
							...element,
							geometryType: element.geometryType ?? 'rect',
							status: 'candidate' as const,
						}))];
						return {
							...prev,
							[space]: {
								...topic,
								status: 'bound',
								parseMessage: apiTrace.message ?? `服务端已自动识别 ${apiElements.length} 个候选对象。`,
								reconstruction: {
									...reconstruction,
									status: 'traced',
									irVersion: 'FloorPlanIR api v0.1',
									elements: nextElements,
									objectCounts: {
										...reconstruction.objectCounts,
										wall: nextElements.filter((element) => element.kind === 'wall_trace').length,
										door: nextElements.filter((element) => element.kind === 'door').length,
										window: nextElements.filter((element) => element.kind === 'window').length,
									},
									spaceBoundaryCount: nextElements.filter((element) => element.kind === 'space_boundary').length,
									functionZoneCount: nextElements.filter((element) => element.kind === 'function_zone').length,
									coordinateSystem: {
										...reconstruction.coordinateSystem,
										scaleStatus: apiTrace.scaleCalibration?.samples ? 'estimated' : reconstruction.coordinateSystem.scaleStatus,
										northStatus: reconstruction.coordinateSystem.northStatus === 'confirmed' ? 'confirmed' : 'detected',
									},
									scaleCalibration: {
										mmPerPixel: apiTrace.scaleCalibration?.mmPerNormalized ? apiTrace.scaleCalibration.mmPerNormalized / 1000 : reconstruction.scaleCalibration?.mmPerPixel,
										source: apiTrace.scaleCalibration?.source?.startsWith('pdf_text') ? 'pdf_text' : 'fallback',
										samples: apiTrace.scaleCalibration?.samples ?? 0,
									},
									pendingIssues: [
										...(apiTrace.issueMessages?.length ? apiTrace.issueMessages : apiTrace.issues?.length ? apiTrace.issues : ['请复核服务端识别候选对象', '请框选/确认空间边界']),
										apiTrace.diagnostics
											? `诊断: 原始${apiTrace.diagnostics.rawSegments ?? 0} / 有效区${apiTrace.diagnostics.scopedSegments ?? 0} / 墙线${apiTrace.diagnostics.wallSegments ?? 0} / 过滤${apiTrace.diagnostics.filteredOut ?? 0} / 闭合空间${apiTrace.diagnostics.closedSpaces ?? 0} / 模式${apiTrace.diagnostics.mode ?? 'strict'}`
											: '',
										apiTrace.diagnostics?.classCounts
											? `分类: wall ${apiTrace.diagnostics.classCounts.wall ?? 0}, dim ${apiTrace.diagnostics.classCounts.dimension ?? 0}, hatch ${apiTrace.diagnostics.classCounts.hatch ?? 0}, symbol ${apiTrace.diagnostics.classCounts.symbol ?? 0}, noise ${apiTrace.diagnostics.classCounts.noise ?? 0}`
											: '',
									].filter(Boolean),
									updatedAt: new Date().toLocaleString('zh-CN', {
										month: '2-digit',
										day: '2-digit',
										hour: '2-digit',
										minute: '2-digit',
									}),
								},
							},
						};
					});
					setPlanElementDrawMode(null);
					setPlanViewerTool('select');
					return;
				}
				if (current.sourceType === 'pdf' || current.sourceType === 'dxf') {
					const message = apiTrace.message ?? '服务端未返回可用矢量识别结果。';
					setSpacePlanTopics((prev) => {
						const topic = prev[space] ?? createDefaultSpacePlanTopicStates()[space];
						const reconstruction = topic.reconstruction ?? createDefaultFloorPlanReconstruction(space, topic.sourceType);
						const preservedElements = (reconstruction.elements ?? []).filter((element) =>
							element.kind === 'analysis_region' || element.status === 'edited' || element.status === 'confirmed'
						);
						return {
							...prev,
							[space]: {
								...topic,
								status: 'bound',
								parseMessage: `${message} 旧自动候选已清理，请调整有效区或检查图纸是否为可解析矢量。`,
								reconstruction: {
									...reconstruction,
									status: 'traced',
									irVersion: 'FloorPlanIR api no-result',
									elements: preservedElements,
									objectCounts: {
										...reconstruction.objectCounts,
										wall: preservedElements.filter((element) => element.kind === 'wall_trace').length,
										door: preservedElements.filter((element) => element.kind === 'door').length,
										window: preservedElements.filter((element) => element.kind === 'window').length,
									},
									functionZoneCount: preservedElements.filter((element) => element.kind === 'function_zone').length,
									spaceBoundaryCount: preservedElements.filter((element) => element.kind === 'space_boundary').length,
									pendingIssues: [
										...(apiTrace.issueMessages?.length ? apiTrace.issueMessages : apiTrace.issues?.length ? apiTrace.issues : ['API 未识别到稳定墙线', '没有回退到粗放像素识别']),
										apiTrace.diagnostics
											? `诊断: 原始${apiTrace.diagnostics.rawSegments ?? 0} / 有效区${apiTrace.diagnostics.scopedSegments ?? 0} / 墙线${apiTrace.diagnostics.wallSegments ?? 0} / 过滤${apiTrace.diagnostics.filteredOut ?? 0} / 闭合空间${apiTrace.diagnostics.closedSpaces ?? 0} / 模式${apiTrace.diagnostics.mode ?? 'none'}`
											: '',
										apiTrace.diagnostics?.classCounts
											? `分类: wall ${apiTrace.diagnostics.classCounts.wall ?? 0}, dim ${apiTrace.diagnostics.classCounts.dimension ?? 0}, hatch ${apiTrace.diagnostics.classCounts.hatch ?? 0}, symbol ${apiTrace.diagnostics.classCounts.symbol ?? 0}, noise ${apiTrace.diagnostics.classCounts.noise ?? 0}`
											: '',
									].filter(Boolean),
								},
							},
						};
					});
					setPlanElementDrawMode('analysis_region');
					setPlanViewerTool('select');
					return;
				}
			} else if (current.sourceType === 'pdf' || current.sourceType === 'dxf') {
				const message = await apiResponse.text();
				throw new Error(`FloorPlanIR API 调用失败：${apiResponse.status} ${message.slice(0, 160)}`);
			}

			const source = viewport.querySelector('canvas, img') as HTMLCanvasElement | HTMLImageElement | null;
			if (!source) {
				throw new Error('服务端未返回可用识别结果，且未找到可回退的图纸渲染层。PDF 需要先完成页面渲染。');
			}

			const sourceWidth = source instanceof HTMLCanvasElement ? source.width : source.naturalWidth;
			const sourceHeight = source instanceof HTMLCanvasElement ? source.height : source.naturalHeight;
			if (!sourceWidth || !sourceHeight) throw new Error('图纸尺寸不可用，请等待图纸加载完成。');

			const maxRasterSize = 1100;
			const cropX = Math.max(0, Math.round(effectiveRegion.x * sourceWidth));
			const cropY = Math.max(0, Math.round(effectiveRegion.y * sourceHeight));
			const cropWidth = Math.max(1, Math.round(effectiveRegion.w * sourceWidth));
			const cropHeight = Math.max(1, Math.round(effectiveRegion.h * sourceHeight));
			const scale = Math.min(1, maxRasterSize / Math.max(cropWidth, cropHeight));
			const rasterWidth = Math.max(1, Math.round(cropWidth * scale));
			const rasterHeight = Math.max(1, Math.round(cropHeight * scale));
			const canvas = document.createElement('canvas');
			canvas.width = rasterWidth;
			canvas.height = rasterHeight;
			const context = canvas.getContext('2d', { willReadFrequently: true });
			if (!context) throw new Error('浏览器无法创建图纸识别画布。');
			context.fillStyle = '#fff';
			context.fillRect(0, 0, rasterWidth, rasterHeight);
			context.drawImage(source, cropX, cropY, cropWidth, cropHeight, 0, 0, rasterWidth, rasterHeight);

			const { data } = context.getImageData(0, 0, rasterWidth, rasterHeight);
			const mask = new Uint8Array(rasterWidth * rasterHeight);
			for (let i = 0; i < rasterWidth * rasterHeight; i += 1) {
				const r = data[i * 4];
				const g = data[i * 4 + 1];
				const b = data[i * 4 + 2];
				const a = data[i * 4 + 3];
				const luminance = r * 0.299 + g * 0.587 + b * 0.114;
				const saturation = Math.max(r, g, b) - Math.min(r, g, b);
				mask[i] = a > 24 && luminance < 135 && saturation < 92 ? 1 : 0;
			}

			type Segment = { x: number; y: number; w: number; h: number; axis: 'h' | 'v'; score: number };
			const horizontal: Segment[] = [];
			const vertical: Segment[] = [];
			const minRun = Math.max(24, Math.round(Math.min(rasterWidth, rasterHeight) * 0.045));
			const mergeRun = (segments: Segment[], next: Segment) => {
				const last = segments[segments.length - 1];
				if (
					last &&
					last.axis === next.axis &&
					Math.abs((last.axis === 'h' ? last.y : last.x) - (next.axis === 'h' ? next.y : next.x)) <= 2
				) {
					const overlapStart = Math.max(last.axis === 'h' ? last.x : last.y, next.axis === 'h' ? next.x : next.y);
					const overlapEnd = Math.min(
						(last.axis === 'h' ? last.x + last.w : last.y + last.h),
						(next.axis === 'h' ? next.x + next.w : next.y + next.h)
					);
					if (overlapEnd > overlapStart) {
						const x = Math.min(last.x, next.x);
						const y = Math.min(last.y, next.y);
						const right = Math.max(last.x + last.w, next.x + next.w);
						const bottom = Math.max(last.y + last.h, next.y + next.h);
						segments[segments.length - 1] = { ...last, x, y, w: right - x, h: bottom - y, score: last.score + next.score };
						return;
					}
				}
				segments.push(next);
			};

			for (let y = 0; y < rasterHeight; y += 1) {
				let x = 0;
				while (x < rasterWidth) {
					while (x < rasterWidth && !mask[y * rasterWidth + x]) x += 1;
					const start = x;
					while (x < rasterWidth && mask[y * rasterWidth + x]) x += 1;
					const length = x - start;
					if (length >= minRun) mergeRun(horizontal, { x: start, y, w: length, h: 1, axis: 'h', score: length });
				}
			}
			for (let x = 0; x < rasterWidth; x += 1) {
				let y = 0;
				while (y < rasterHeight) {
					while (y < rasterHeight && !mask[y * rasterWidth + x]) y += 1;
					const start = y;
					while (y < rasterHeight && mask[y * rasterWidth + x]) y += 1;
					const length = y - start;
					if (length >= minRun) mergeRun(vertical, { x, y: start, w: 1, h: length, axis: 'v', score: length });
				}
			}

			const normalizedSegments = [...horizontal, ...vertical]
				.map((segment) => ({
					...segment,
					w: Math.max(segment.w, segment.axis === 'v' ? 4 : segment.w),
					h: Math.max(segment.h, segment.axis === 'h' ? 4 : segment.h),
				}))
				.filter((segment) => {
					const normalizedLength = segment.axis === 'h' ? segment.w / rasterWidth : segment.h / rasterHeight;
					const normalizedThickness = segment.axis === 'h' ? segment.h / rasterHeight : segment.w / rasterWidth;
					return normalizedLength >= 0.035 && normalizedThickness <= 0.045;
				});

			const combineParallelSegments = (input: Segment[]) => {
				const sorted = [...input].sort((a, b) => {
					if (a.axis !== b.axis) return a.axis.localeCompare(b.axis);
					const aTrack = a.axis === 'h' ? a.y : a.x;
					const bTrack = b.axis === 'h' ? b.y : b.x;
					if (Math.abs(aTrack - bTrack) > 5) return aTrack - bTrack;
					return (a.axis === 'h' ? a.x : a.y) - (b.axis === 'h' ? b.x : b.y);
				});
				const combined: Segment[] = [];
				sorted.forEach((segment) => {
					const matchIndex = combined.findIndex((existing) => {
						if (existing.axis !== segment.axis) return false;
						const existingTrack = existing.axis === 'h' ? existing.y + existing.h / 2 : existing.x + existing.w / 2;
						const segmentTrack = segment.axis === 'h' ? segment.y + segment.h / 2 : segment.x + segment.w / 2;
						if (Math.abs(existingTrack - segmentTrack) > 7) return false;
						const existingStart = existing.axis === 'h' ? existing.x : existing.y;
						const existingEnd = existing.axis === 'h' ? existing.x + existing.w : existing.y + existing.h;
						const segmentStart = segment.axis === 'h' ? segment.x : segment.y;
						const segmentEnd = segment.axis === 'h' ? segment.x + segment.w : segment.y + segment.h;
						const gap = Math.max(segmentStart - existingEnd, existingStart - segmentEnd, 0);
						const overlap = Math.min(existingEnd, segmentEnd) - Math.max(existingStart, segmentStart);
						return gap <= 10 || overlap > 0;
					});
					if (matchIndex >= 0) {
						const existing = combined[matchIndex];
						const x = Math.min(existing.x, segment.x);
						const y = Math.min(existing.y, segment.y);
						const right = Math.max(existing.x + existing.w, segment.x + segment.w);
						const bottom = Math.max(existing.y + existing.h, segment.y + segment.h);
						combined[matchIndex] = { ...existing, x, y, w: right - x, h: bottom - y, score: existing.score + segment.score };
					} else {
						combined.push(segment);
					}
				});
				return combined;
			};

			const boxIou = (a: Segment, b: Segment) => {
				const left = Math.max(a.x, b.x);
				const top = Math.max(a.y, b.y);
				const right = Math.min(a.x + a.w, b.x + b.w);
				const bottom = Math.min(a.y + a.h, b.y + b.h);
				const intersection = Math.max(0, right - left) * Math.max(0, bottom - top);
				if (!intersection) return 0;
				const areaA = a.w * a.h;
				const areaB = b.w * b.h;
				return intersection / (areaA + areaB - intersection);
			};

			const suppressOverlaps = (input: Segment[]) => {
				const picked: Segment[] = [];
				[...input].sort((a, b) => b.score - a.score).forEach((segment) => {
					const duplicate = picked.some((existing) => {
						if (boxIou(existing, segment) > 0.28) return true;
						if (existing.axis !== segment.axis) return false;
						const existingTrack = existing.axis === 'h' ? existing.y + existing.h / 2 : existing.x + existing.w / 2;
						const segmentTrack = segment.axis === 'h' ? segment.y + segment.h / 2 : segment.x + segment.w / 2;
						if (Math.abs(existingTrack - segmentTrack) > 10) return false;
						const existingStart = existing.axis === 'h' ? existing.x : existing.y;
						const existingEnd = existing.axis === 'h' ? existing.x + existing.w : existing.y + existing.h;
						const segmentStart = segment.axis === 'h' ? segment.x : segment.y;
						const segmentEnd = segment.axis === 'h' ? segment.x + segment.w : segment.y + segment.h;
						const overlap = Math.max(0, Math.min(existingEnd, segmentEnd) - Math.max(existingStart, segmentStart));
						const minLength = Math.min(existingEnd - existingStart, segmentEnd - segmentStart);
						return minLength > 0 && overlap / minLength > 0.62;
					});
					if (!duplicate) picked.push(segment);
				});
				return picked;
			};

			const hasDarkPixelAround = (cx: number, cy: number, radius: number) => {
				let count = 0;
				for (let y = Math.max(0, cy - radius); y <= Math.min(rasterHeight - 1, cy + radius); y += 1) {
					for (let x = Math.max(0, cx - radius); x <= Math.min(rasterWidth - 1, cx + radius); x += 1) {
						count += mask[y * rasterWidth + x];
					}
				}
				return count;
			};

			const looksLikeDimensionText = (segment: Segment) => {
				const length = segment.axis === 'h' ? segment.w : segment.h;
				const thickness = segment.axis === 'h' ? segment.h : segment.w;
				const ratio = length / Math.max(1, thickness);
				if (ratio < 5) return true;
				const cx = Math.round(segment.x + segment.w / 2);
				const cy = Math.round(segment.y + segment.h / 2);
				const nearbyInk = hasDarkPixelAround(cx, cy, 9);
				const segmentArea = Math.max(1, segment.w * segment.h);
				return nearbyInk / segmentArea > 0.9 && length < Math.min(rasterWidth, rasterHeight) * 0.22;
			};

			const segments = suppressOverlaps(combineParallelSegments(normalizedSegments))
				.filter((segment) => !looksLikeDimensionText(segment))
				.sort((a, b) => b.score - a.score)
				.slice(0, 36);

			const extractPdfScaleCalibration = async () => {
				if (current.mimeType !== 'application/pdf' || !current.uploadedFileUrl) return { mmPerPixel: undefined as number | undefined, samples: 0 };
				try {
					const pdfjsLib = await import('pdfjs-dist/legacy/build/pdf');
					pdfjsLib.GlobalWorkerOptions.workerSrc = '/api/pdf-worker';
					const loadingTask = pdfjsLib.getDocument({ url: current.uploadedFileUrl });
					const pdf = await loadingTask.promise;
					const page = await pdf.getPage(1);
					const viewportAtOne = page.getViewport({ scale: 1 });
					const textContent = await page.getTextContent();
					const dimensionTexts = (textContent.items as Array<{ str?: string; transform?: number[] }>)
						.map((item) => {
							const raw = String(item.str ?? '').replace(/,/g, '').trim();
							const match = raw.match(/(?:^|\D)([1-9]\d{2,4})(?:\D|$)/);
							const value = match ? Number(match[1]) : 0;
							const transform = item.transform ?? [];
							if (!value || value < 500 || value > 30000 || transform.length < 6) return null;
							const point = viewportAtOne.convertToViewportPoint(transform[4], transform[5]);
							return {
								value,
								x: ((point[0] / viewportAtOne.width - effectiveRegion.x) / Math.max(0.001, effectiveRegion.w)) * rasterWidth,
								y: ((point[1] / viewportAtOne.height - effectiveRegion.y) / Math.max(0.001, effectiveRegion.h)) * rasterHeight,
							};
						})
						.filter((item): item is { value: number; x: number; y: number } =>
							item !== null &&
							item.x >= -20 &&
							item.x <= rasterWidth + 20 &&
							item.y >= -20 &&
							item.y <= rasterHeight + 20
						);
					const ratios: number[] = [];
					dimensionTexts.forEach((text) => {
						const candidates = segments
							.map((segment) => {
								const centerX = segment.x + segment.w / 2;
								const centerY = segment.y + segment.h / 2;
								const distance = Math.hypot(centerX - text.x, centerY - text.y);
								const length = segment.axis === 'h' ? segment.w : segment.h;
								const ratio = text.value / Math.max(1, length);
								return { distance, length, ratio };
							})
							.filter((candidate) =>
								candidate.distance <= Math.max(90, Math.min(rasterWidth, rasterHeight) * 0.16) &&
								candidate.ratio >= 3 &&
								candidate.ratio <= 220 &&
								candidate.length >= minRun
							)
							.sort((a, b) => a.distance - b.distance);
						if (candidates[0]) ratios.push(candidates[0].ratio);
					});
					if (ratios.length < 2) return { mmPerPixel: undefined, samples: ratios.length };
					const sortedRatios = ratios.sort((a, b) => a - b);
					const median = sortedRatios[Math.floor(sortedRatios.length / 2)];
					const stableRatios = sortedRatios.filter((ratio) => Math.abs(ratio - median) / median < 0.35);
					if (stableRatios.length < 2) return { mmPerPixel: median, samples: ratios.length };
					const stableMedian = stableRatios[Math.floor(stableRatios.length / 2)];
					return { mmPerPixel: stableMedian, samples: stableRatios.length };
				} catch {
					return { mmPerPixel: undefined, samples: 0 };
				}
			};

			const scaleCalibration = await extractPdfScaleCalibration();
			const fallbackMmPerPixel = 21000 / rasterWidth;
			const mmPerPixel = scaleCalibration.mmPerPixel ?? fallbackMmPerPixel;

			const elements: FloorPlanElement[] = segments.map((segment, index) => {
				const normalizedLength = segment.axis === 'h' ? segment.w / rasterWidth : segment.h / rasterHeight;
				const kind: FloorPlanElementKind =
					normalizedLength >= 0.16 ? 'wall_trace' :
					normalizedLength >= 0.07 ? 'window' :
					'door';
				const widthMm = Math.max(80, Math.round(segment.w * mmPerPixel));
				const depthMm = Math.max(40, Math.round(segment.h * mmPerPixel));
				return {
					id: `floor-ir-auto-${kind}-${Date.now()}-${index}`,
					kind,
					label:
						kind === 'wall_trace' ? `自动墙线 ${index + 1}` :
						kind === 'window' ? `自动窗/开口 ${index + 1}` :
						`自动门洞 ${index + 1}`,
					x: Math.max(0, Math.min(0.999, effectiveRegion.x + (segment.x / rasterWidth) * effectiveRegion.w)),
					y: Math.max(0, Math.min(0.999, effectiveRegion.y + (segment.y / rasterHeight) * effectiveRegion.h)),
					w: Math.max(0.003, Math.min(1, (segment.w / rasterWidth) * effectiveRegion.w)),
					h: Math.max(0.003, Math.min(1, (segment.h / rasterHeight) * effectiveRegion.h)),
					widthMm,
					depthMm,
					confidence: kind === 'wall_trace' ? 0.74 : 0.52,
					status: 'candidate',
				};
			});

			setSpacePlanTopics((prev) => {
				const topic = prev[space] ?? createDefaultSpacePlanTopicStates()[space];
				const reconstruction = topic.reconstruction ?? createDefaultFloorPlanReconstruction(space, topic.sourceType);
				const manualElements = (reconstruction.elements ?? []).filter((element) =>
					element.kind === 'analysis_region' || element.status === 'edited' || element.status === 'confirmed'
				);
				const nextElements = [...manualElements, ...elements];
				return {
					...prev,
					[space]: {
						...topic,
						status: 'bound',
						parseMessage: `已基于真实渲染图纸自动识别 ${elements.length} 个候选对象；${scaleCalibration.mmPerPixel ? `已从 ${scaleCalibration.samples} 个尺寸标注估算比例 ${scaleCalibration.mmPerPixel.toFixed(2)} mm/px。` : '未读取到稳定尺寸标注，暂用估算比例。'}请在左侧对齐校正，门窗候选需人工复核。`,
						reconstruction: {
							...reconstruction,
							status: 'traced',
							irVersion: 'FloorPlanIR draft v0.3',
							elements: nextElements,
							objectCounts: {
								...reconstruction.objectCounts,
								wall: nextElements.filter((element) => element.kind === 'wall_trace').length,
								door: nextElements.filter((element) => element.kind === 'door').length,
								window: nextElements.filter((element) => element.kind === 'window').length,
							},
							spaceBoundaryCount: nextElements.filter((element) => element.kind === 'space_boundary').length,
							functionZoneCount: nextElements.filter((element) => element.kind === 'function_zone').length,
							coordinateSystem: {
								...reconstruction.coordinateSystem,
								scaleStatus: reconstruction.coordinateSystem.scaleStatus === 'confirmed' ? 'confirmed' : 'estimated',
								northStatus: reconstruction.coordinateSystem.northStatus === 'confirmed' ? 'confirmed' : 'detected',
							},
							scaleCalibration: {
								mmPerPixel,
								source: scaleCalibration.mmPerPixel ? 'pdf_text' : 'fallback',
								samples: scaleCalibration.samples,
							},
							pendingIssues: elements.length > 0
				? [
									'请复核墙线、门窗候选',
									'请框选空间边界',
									'识别已限制在有效区内，尺寸标注仅用于比例校准',
									scaleCalibration.mmPerPixel ? '比例来自图中文字尺寸，请抽查确认' : '未读取到有效尺寸标注，请手动校准比例尺',
								]
								: ['未识别到足够线段，请提高图纸清晰度或手动框选'],
							updatedAt: new Date().toLocaleString('zh-CN', {
								month: '2-digit',
								day: '2-digit',
								hour: '2-digit',
								minute: '2-digit',
							}),
						},
					},
				};
			});
			setPlanElementDrawMode(elements.length > 0 ? null : 'space_boundary');
			setPlanViewerTool('select');
		} catch (error) {
			const message = error instanceof Error ? error.message : '自动识别失败。';
			setPlanAutoTraceError(message);
			if (current.sourceType === 'pdf' || current.sourceType === 'dxf') {
				setSpacePlanTopics((prev) => {
					const topic = prev[space] ?? createDefaultSpacePlanTopicStates()[space];
					const reconstruction = topic.reconstruction ?? createDefaultFloorPlanReconstruction(space, topic.sourceType);
					const preservedElements = (reconstruction.elements ?? []).filter((element) =>
						element.kind === 'analysis_region' || element.status === 'edited' || element.status === 'confirmed'
					);
					return {
						...prev,
						[space]: {
							...topic,
							status: 'bound',
							parseMessage: `${message} PDF/DXF 不再回退到粗放像素识别，旧自动候选已清理。`,
							reconstruction: {
								...reconstruction,
								status: 'traced',
								irVersion: 'FloorPlanIR api failed',
								elements: preservedElements,
								objectCounts: {
									...reconstruction.objectCounts,
									wall: preservedElements.filter((element) => element.kind === 'wall_trace').length,
									door: preservedElements.filter((element) => element.kind === 'door').length,
									window: preservedElements.filter((element) => element.kind === 'window').length,
								},
								functionZoneCount: preservedElements.filter((element) => element.kind === 'function_zone').length,
								spaceBoundaryCount: preservedElements.filter((element) => element.kind === 'space_boundary').length,
								pendingIssues: ['服务端矢量解析失败', '请重新框选有效区或上传 DXF', '未使用旧像素识别结果'],
							},
						},
					};
				});
			}
		} finally {
			setPlanAutoTraceBusy(false);
		}
	}, [spacePlanTopics]);

	const formatFileSize = (size?: number) => {
		if (!size) return '未知大小';
		if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
		return `${(size / (1024 * 1024)).toFixed(2)} MB`;
	};

	const planViewerTopic = planViewerSpace ? spacePlanTopics[planViewerSpace] : null;
	const planViewerPdfSrc =
		planViewerTopic?.uploadedFileUrl && planViewerTopic.mimeType === 'application/pdf'
			? planViewerTopic.uploadedFileUrl
			: '';
	const planViewerReconstruction =
		planViewerSpace && planViewerTopic
			? planViewerTopic.reconstruction ?? createDefaultFloorPlanReconstruction(planViewerSpace, planViewerTopic.sourceType)
			: null;
	const shouldShowPlanReconstructionOverlay = Boolean(planViewerReconstruction && planViewerReconstruction.status !== 'raw');

	const renderPlanReconstructionOverlay = () => {
		if (!planViewerReconstruction || (!shouldShowPlanReconstructionOverlay && !planElementDrawMode)) return null;
		const elements = planViewerReconstruction.elements ?? [];
		const toSvgPoints = (points: FloorPlanPoint[]) => points.map((point) => `${point.x * 100},${point.y * 100}`).join(' ');
		const toClosedPath = (points: FloorPlanPoint[]) => {
			if (points.length === 0) return '';
			if (points.length < 3) return `M ${points.map((point) => `${point.x * 100} ${point.y * 100}`).join(' L ')}`;
			const commands = [`M ${points[0].x * 100} ${points[0].y * 100}`];
			for (let index = 1; index < points.length; index += 1) {
				const prev = points[index - 1];
				const current = points[index];
				const midX = ((prev.x + current.x) / 2) * 100;
				const midY = ((prev.y + current.y) / 2) * 100;
				commands.push(`Q ${prev.x * 100} ${prev.y * 100} ${midX} ${midY}`);
			}
			const last = points[points.length - 1];
			const first = points[0];
			commands.push(`Q ${last.x * 100} ${last.y * 100} ${first.x * 100} ${first.y * 100} Z`);
			return commands.join(' ');
		};
		const getElementTone = (kind: FloorPlanElementKind) => {
			switch (kind) {
				case 'analysis_region':
					return { stroke: 'rgba(255,255,255,0.82)', fill: 'rgba(255,255,255,0.04)' };
				case 'space_boundary':
					return { stroke: 'rgba(56,189,248,0.95)', fill: 'rgba(56,189,248,0.12)' };
				case 'function_zone':
					return { stroke: 'rgba(14,165,233,0.8)', fill: 'rgba(14,165,233,0.22)' };
				case 'wall_trace':
					return { stroke: 'rgba(34,197,94,0.95)', fill: 'rgba(34,197,94,0.08)' };
				case 'door':
					return { stroke: 'rgba(250,204,21,0.95)', fill: 'rgba(250,204,21,0.1)' };
				case 'window':
					return { stroke: 'rgba(59,130,246,0.95)', fill: 'rgba(59,130,246,0.12)' };
				case 'height_marker':
					return { stroke: 'rgba(251,146,60,0.95)', fill: 'rgba(251,146,60,0.08)' };
				default:
					return { stroke: 'rgba(255,255,255,0.75)', fill: 'rgba(255,255,255,0.08)' };
			}
		};
		return (
			<svg
				className={`absolute inset-0 z-[8] h-full w-full ${planElementDrawMode ? 'cursor-crosshair' : ''}`}
				viewBox="0 0 100 100"
				preserveAspectRatio="none"
				onWheel={handlePlanViewerWheel}
				onMouseDown={handlePlanElementPointerDown}
				onMouseMove={handlePlanElementPointerMove}
				onMouseUp={handlePlanElementPointerUp}
				onClick={handlePlanElementClick}
				onDoubleClick={handlePlanElementDoubleClick}
			>
				<defs>
					<pattern id="standard-zone-hatch" width="3" height="3" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
						<line x1="0" y1="0" x2="0" y2="3" stroke="rgba(56,189,248,0.42)" strokeWidth="0.8" />
					</pattern>
				</defs>
				{elements.map((element) => {
					const tone = getElementTone(element.kind);
					const selected = element.id === selectedPlanElementId;
					const showElementLabel = selected || element.status !== 'candidate' || elements.length <= 18;
					const x = element.x * 100;
					const y = element.y * 100;
					const w = element.w * 100;
					const h = element.h * 100;
					const strokeWidth =
						selected ? 0.32 :
						element.kind === 'function_zone' || element.kind === 'space_boundary' || element.kind === 'analysis_region' ? 0.22 :
						0.14;
					const elementGeometry = element.geometryType ?? 'rect';
					return (
						<g
							key={`floor-ir-element-${element.id}`}
							className="cursor-pointer"
							onClick={(event) => {
								event.stopPropagation();
								setSelectedPlanElementId(element.id);
								setPlanViewerTool('select');
							}}
						>
							{elementGeometry === 'polygon' && element.points && element.points.length >= 3 ? (
								<polygon
									points={toSvgPoints(element.points)}
									fill={tone.fill}
									stroke={selected ? 'rgba(255,255,255,0.98)' : tone.stroke}
									strokeWidth={strokeWidth}
									strokeDasharray={element.status === 'candidate' ? '1.1 0.9' : undefined}
								/>
							) : elementGeometry === 'path' && element.points && element.points.length >= 3 ? (
								<path
									d={toClosedPath(element.points)}
									fill={tone.fill}
									stroke={selected ? 'rgba(255,255,255,0.98)' : tone.stroke}
									strokeWidth={strokeWidth}
									strokeDasharray={element.status === 'candidate' ? '1.1 0.9' : undefined}
								/>
							) : (
								<rect
									x={x}
									y={y}
									width={w}
									height={h}
									fill={tone.fill}
									stroke={selected ? 'rgba(255,255,255,0.98)' : tone.stroke}
									strokeWidth={strokeWidth}
									strokeDasharray={element.kind === 'analysis_region' || element.status === 'candidate' ? '1.1 0.9' : undefined}
								/>
							)}
							{showElementLabel && (
								<text x={x + 1.2} y={y + 3.2} fill="rgba(255,255,255,0.96)" fontWeight="700" style={svgLabelTextStyle}>
									{element.label}
								</text>
							)}
							{showElementLabel && (element.widthMm || element.depthMm || element.areaSqm) && (
								<text x={x + 1.2} y={y + 6.2} fill="rgba(255,255,255,0.84)" style={svgBodyTextStyle}>
									{element.widthMm && element.depthMm ? `${element.widthMm}x${element.depthMm}mm` : ''}
									{element.areaSqm ? ` ${element.areaSqm}㎡` : ''}
								</text>
							)}
							{selected && (
								<>
									<circle cx={x} cy={y} r="0.9" fill="rgba(255,255,255,0.98)" />
									<circle cx={x + w} cy={y} r="0.9" fill="rgba(255,255,255,0.98)" />
									<circle cx={x + w} cy={y + h} r="0.9" fill="rgba(255,255,255,0.98)" />
									<circle cx={x} cy={y + h} r="0.9" fill="rgba(255,255,255,0.98)" />
									{element.points?.map((point, index) => (
										<circle key={`${element.id}-point-${index}`} cx={point.x * 100} cy={point.y * 100} r="0.65" fill="rgba(14,165,233,0.98)" />
									))}
								</>
							)}
						</g>
					);
				})}
				{planPolygonDraftPoints.length > 0 && (
					<g>
						<polyline
							points={toSvgPoints(planPolygonDraftPoints)}
							fill="none"
							stroke="rgba(14,165,233,0.9)"
							strokeWidth="0.22"
							strokeDasharray="1.1 0.9"
						/>
						{planPolygonDraftPoints.map((point, index) => (
							<circle key={`polygon-draft-${index}`} cx={point.x * 100} cy={point.y * 100} r="0.75" fill="rgba(14,165,233,0.95)" />
						))}
					</g>
				)}
				{planPathDraftPoints.length > 1 && (
					<path
						d={toClosedPath(planPathDraftPoints)}
						fill="rgba(14,165,233,0.12)"
						stroke="rgba(14,165,233,0.9)"
						strokeWidth="0.22"
						strokeDasharray="1.1 0.9"
					/>
				)}
				{planElementDraft && (
					<rect
						x={planElementDraft.x * 100}
						y={planElementDraft.y * 100}
						width={planElementDraft.w * 100}
						height={planElementDraft.h * 100}
						fill="rgba(255,255,255,0.08)"
						stroke="rgba(255,255,255,0.92)"
						strokeWidth="0.55"
						strokeDasharray="1.2 1"
					/>
				)}
			</svg>
		);
	};

	const renderPlanReconstructionPanel = () => {
		if (!planViewerSpace || !planViewerTopic) return null;
		const reconstruction = planViewerTopic.reconstruction ?? createDefaultFloorPlanReconstruction(planViewerSpace, planViewerTopic.sourceType);
		const objectTotal = Object.values(reconstruction.objectCounts).reduce((sum, count) => sum + count, 0);
		const reconstructionElements = reconstruction.elements ?? [];
		const tracedObjectTotal = Math.max(objectTotal, reconstructionElements.length);
		const selectedElement = reconstructionElements.find((element) => element.id === selectedPlanElementId) ?? null;
		const updateSelectedElement = (patch: Partial<FloorPlanElement>) => {
			if (!selectedElement) return;
			if (selectedElement.points && selectedElement.points.length > 0 && (
				typeof patch.x === 'number' ||
				typeof patch.y === 'number' ||
				typeof patch.w === 'number' ||
				typeof patch.h === 'number'
			)) {
				const nextX = typeof patch.x === 'number' ? patch.x : selectedElement.x;
				const nextY = typeof patch.y === 'number' ? patch.y : selectedElement.y;
				const nextW = typeof patch.w === 'number' ? Math.max(0.001, patch.w) : selectedElement.w;
				const nextH = typeof patch.h === 'number' ? Math.max(0.001, patch.h) : selectedElement.h;
				const scaleX = nextW / Math.max(0.001, selectedElement.w);
				const scaleY = nextH / Math.max(0.001, selectedElement.h);
				updatePlanElement(planViewerSpace, selectedElement.id, {
					...patch,
					x: nextX,
					y: nextY,
					w: nextW,
					h: nextH,
					points: selectedElement.points.map((point) => ({
						x: Math.min(1, Math.max(0, nextX + (point.x - selectedElement.x) * scaleX)),
						y: Math.min(1, Math.max(0, nextY + (point.y - selectedElement.y) * scaleY)),
					})),
				});
				return;
			}
			updatePlanElement(planViewerSpace, selectedElement.id, patch);
		};
		return (
			<div className="mt-5 rounded-none border border-cyan-300/14 bg-cyan-300/[0.04] p-4">
				<div className="flex items-start justify-between gap-3">
					<div>
						<div className="text-sm font-semibold text-white">图纸重构 / FloorPlanIR</div>
						<div className="mt-1 text-[11px] text-cyan-100/55">{reconstruction.irVersion} · {getReconstructionStatusLabel(reconstruction.status)}</div>
					</div>
					<span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2 py-0.5 text-[11px] text-cyan-100">
						统一底座
					</span>
				</div>
				<div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-white/58">
					<div className="rounded-none border border-white/8 bg-black/18 p-2">
						<div className="text-white/38">坐标</div>
						<div className="mt-1 text-white/72">{reconstruction.coordinateSystem.unit} · 比例{reconstruction.coordinateSystem.scaleStatus}</div>
						{reconstruction.scaleCalibration?.mmPerPixel && (
							<div className="mt-1 text-[10px] text-cyan-100/55">
								{reconstruction.scaleCalibration.mmPerPixel.toFixed(2)} mm/px · {reconstruction.scaleCalibration.source === 'pdf_text' ? '尺寸标注' : '估算'}
							</div>
						)}
					</div>
					<div className="rounded-none border border-white/8 bg-black/18 p-2">
						<div className="text-white/38">朝向</div>
						<div className="mt-1 text-white/72">{reconstruction.coordinateSystem.northStatus}</div>
					</div>
					<div className="rounded-none border border-white/8 bg-black/18 p-2">
						<div className="text-white/38">描边对象</div>
						<div className="mt-1 text-white/72">{tracedObjectTotal} 个</div>
					</div>
					<div className="rounded-none border border-white/8 bg-black/18 p-2">
						<div className="text-white/38">分区/边界</div>
						<div className="mt-1 text-white/72">{reconstruction.functionZoneCount} / {reconstruction.spaceBoundaryCount}</div>
					</div>
				</div>
				<div className="mt-3 flex flex-wrap gap-1.5">
					{(['normalize', 'trace', 'zone', 'align', 'height'] as const).map((step) => {
						const label = step === 'normalize' ? '标准化' : step === 'trace' ? '检查描边' : step === 'zone' ? '功能分区' : step === 'align' ? '空间对齐' : '高度补全';
						return (
							<button
								key={`reconstruct-${step}`}
								onClick={() => {
									if (planAutoTraceBusy) return;
									if (step === 'trace') {
										void autoTraceRenderedPlan(planViewerSpace);
									} else {
										updatePlanReconstruction(planViewerSpace, step);
									}
									if (step === 'normalize') setPlanElementDrawMode('analysis_region');
									if (step === 'zone') {
										setPlanElementDrawMode('function_zone');
										setPlanDrawGeometryMode('polygon');
									}
									if (step === 'height') setPlanElementDrawMode('height_marker');
									setPlanViewerTool('select');
									setPlanElementDraft(null);
								}}
								disabled={planAutoTraceBusy}
								className={`rounded-full border border-white/12 px-3 py-1 text-[12px] font-medium text-white/68 hover:bg-white/8 hover:text-white ${planAutoTraceBusy ? 'cursor-wait opacity-55' : ''}`}
							>
								{label}
							</button>
						);
					})}
				</div>
				{planAutoTraceBusy && (
					<div className="mt-2 rounded-none border border-cyan-300/18 bg-cyan-300/8 p-2 text-[11px] leading-5 text-cyan-100/70">
						正在读取当前图纸像素并自动识别墙线、门窗候选...
					</div>
				)}
				{planAutoTraceError && (
					<div className="mt-2 rounded-none border border-rose-300/18 bg-rose-300/8 p-2 text-[11px] leading-5 text-rose-100/76">
						{planAutoTraceError}
					</div>
				)}
				<div className="mt-2 rounded-none border border-white/8 bg-black/16 p-2 text-[11px] leading-5 text-white/45">
					标准化：建立统一坐标与比例状态。检查描边：必须先框选有效区，只读取该区域内的真实图纸像素，尺寸标注仅用于比例校准。功能分区：应框成闭合区域，并以半透明色块表达。空间对齐：把对象绑定到当前空间。高度补全：补层高、梁底、门窗高等竖向信息。
				</div>
				<div className="mt-3 flex flex-wrap gap-1.5 border-t border-white/10 pt-3">
					{([
						['analysis_region', '框选有效区'],
						['space_boundary', '框选空间'],
						['function_zone', '框选功能区'],
						['wall_trace', '框选墙线'],
						['door', '框选门洞'],
						['window', '框选窗'],
						['height_marker', '标高度'],
					] as Array<[FloorPlanElementKind, string]>).map(([kind, label]) => (
						<button
							key={`draw-plan-element-${kind}`}
							onClick={() => {
								setPlanElementDrawMode((current) => current === kind ? null : kind);
								setPlanDrawGeometryMode('rect');
								setPlanViewerTool('select');
								setPlanElementDraft(null);
								setPlanPolygonDraftPoints([]);
								setPlanPathDraftPoints([]);
							}}
							className={`rounded-full border px-3 py-1 text-[12px] font-medium transition ${planElementDrawMode === kind && planDrawGeometryMode === 'rect' ? 'border-white/55 bg-white/16 text-white' : 'border-white/12 text-white/68 hover:bg-white/8 hover:text-white'}`}
						>
							{label}
						</button>
					))}
				</div>
				<div className="mt-2 flex flex-wrap gap-1.5">
					<button
						onClick={() => {
							setPlanElementDrawMode('function_zone');
							setPlanDrawGeometryMode('polygon');
							setPlanElementDraft(null);
							setPlanPathDraftPoints([]);
						}}
						className={`rounded-full border px-3 py-1 text-[12px] font-medium transition ${planElementDrawMode === 'function_zone' && planDrawGeometryMode === 'polygon' ? 'border-sky-200/70 bg-sky-300/16 text-sky-50' : 'border-white/12 text-white/68 hover:bg-white/8 hover:text-white'}`}
					>
						多边形分区
					</button>
					<button
						onClick={() => {
							setPlanElementDrawMode('function_zone');
							setPlanDrawGeometryMode('path');
							setPlanElementDraft(null);
							setPlanPolygonDraftPoints([]);
						}}
						className={`rounded-full border px-3 py-1 text-[12px] font-medium transition ${planElementDrawMode === 'function_zone' && planDrawGeometryMode === 'path' ? 'border-sky-200/70 bg-sky-300/16 text-sky-50' : 'border-white/12 text-white/68 hover:bg-white/8 hover:text-white'}`}
					>
						自由曲线分区
					</button>
					{planDrawGeometryMode === 'polygon' && planPolygonDraftPoints.length > 0 && (
						<>
							<button
								onClick={finishPlanPolygonDraft}
								disabled={planPolygonDraftPoints.length < 3}
								className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 text-[12px] font-medium text-emerald-100 hover:bg-emerald-300/16 disabled:cursor-not-allowed disabled:opacity-45"
							>
								完成多边形
							</button>
							<button
								onClick={() => setPlanPolygonDraftPoints((current) => current.slice(0, -1))}
								className="rounded-full border border-white/12 px-3 py-1 text-[12px] font-medium text-white/68 hover:bg-white/8 hover:text-white"
							>
								撤销点
							</button>
						</>
					)}
				</div>
				{planElementDrawMode && (
					<div className="mt-2 rounded-none border border-white/10 bg-black/18 p-2 text-[11px] leading-5 text-white/52">
						{planDrawGeometryMode === 'polygon'
							? '正在绘制多边形：在左侧图纸连续点击边界点，双击或点击“完成多边形”闭合。'
							: planDrawGeometryMode === 'path'
								? '正在绘制自由曲线：按住左侧图纸拖动圈出异形/弧形区域，松开后自动闭合。'
								: '正在手动绘制：按住左侧底图拖拽生成对象。生成后在下方编辑尺寸和面积。'}
					</div>
				)}
				<div className="mt-3 flex flex-wrap gap-1.5">
					<button
						onClick={() => resetPlanReconstruction(planViewerSpace)}
						className="rounded-full border border-rose-300/22 bg-rose-300/8 px-3 py-1 text-[12px] font-medium text-rose-100 hover:bg-rose-300/14"
					>
						重置重构
					</button>
					{selectedElement && (
						<button
							onClick={() => deletePlanElement(planViewerSpace, selectedElement.id)}
							className="rounded-full border border-white/12 px-3 py-1 text-[12px] font-medium text-white/68 hover:bg-white/8 hover:text-white"
						>
							删除选中
						</button>
					)}
				</div>
				<div className="mt-3 space-y-1.5 text-[11px] leading-5 text-white/52">
					<div>空间对齐：{reconstruction.alignment.matchedSpace} · {Math.round(reconstruction.alignment.confidence * 100)}% · {reconstruction.alignment.status}</div>
					<div>
						高度：{reconstruction.heightProfile.status === 'missing'
							? '待补充'
							: `层高 ${reconstruction.heightProfile.ceilingHeight} / 梁底 ${reconstruction.heightProfile.beamBottomHeight} / 门高 ${reconstruction.heightProfile.doorHeight}`}
					</div>
					{(reconstruction.pendingIssues ?? []).length > 0 && <div>待确认：{(reconstruction.pendingIssues ?? []).join('、')}</div>}
				</div>
				<div className="mt-4 border-t border-white/10 pt-4">
					<div className="flex items-center justify-between gap-3">
						<div className="text-sm font-semibold text-white">重构对象</div>
					<div className="text-[11px] text-white/42">{reconstructionElements.length} 个</div>
				</div>
				<div className="mt-2 max-h-40 space-y-1.5 overflow-y-auto pr-1">
						{reconstructionElements.length > 0 ? reconstructionElements.map((element) => (
							<button
								key={`reconstruction-element-row-${element.id}`}
								onClick={() => setSelectedPlanElementId(element.id)}
								className={`w-full rounded-none border px-2.5 py-2 text-left text-[12px] transition ${selectedElement?.id === element.id ? 'border-cyan-300/45 bg-cyan-300/12 text-white' : 'border-white/8 bg-black/16 text-white/58 hover:bg-white/8'}`}
							>
								<div className="flex items-center justify-between gap-2">
									<span className="font-semibold">{element.label}</span>
									<span className="text-[10px] text-white/40">{element.status}</span>
								</div>
								<div className="mt-1 text-[11px] text-white/45">
									{element.widthMm && element.depthMm ? `${element.widthMm} x ${element.depthMm}mm` : '尺寸待补'}
									{element.areaSqm ? ` · ${element.areaSqm}㎡` : ''}
								</div>
							</button>
						)) : (
							<div className="rounded-none border border-dashed border-white/12 p-3 text-[12px] leading-5 text-white/45">
								当前没有真实解析对象。请使用上方“框选空间/功能区/墙线/门窗”，直接在底图上拖拽生成重构对象。
							</div>
						)}
					</div>
					{selectedElement && (
						<div className="mt-3 rounded-none border border-white/10 bg-black/18 p-3">
							<div className="text-[12px] font-semibold text-white">编辑：{selectedElement.label}</div>
							<label className="mt-3 block">
								<div className="mb-1 text-[11px] text-white/42">名称</div>
								<input
									value={selectedElement.label}
									onChange={(event) => updateSelectedElement({ label: event.target.value })}
									className="w-full rounded-none border border-white/12 bg-black/28 px-2 py-1.5 text-[12px] text-white outline-none focus:border-cyan-300/45"
								/>
							</label>
							<div className="mt-3 grid grid-cols-4 gap-2">
								{(['x', 'y', 'w', 'h'] as const).map((key) => (
									<label key={`element-${selectedElement.id}-${key}`} className="block">
										<div className="mb-1 text-[10px] uppercase text-white/38">{key}%</div>
										<input
											type="number"
											min={0}
											max={100}
											value={Math.round((selectedElement[key] ?? 0) * 100)}
											onChange={(event) => {
												const value = Math.min(100, Math.max(0, Number(event.target.value))) / 100;
												updateSelectedElement({ [key]: value } as Partial<FloorPlanElement>);
											}}
											className="w-full rounded-none border border-white/12 bg-black/28 px-2 py-1.5 text-[12px] text-white outline-none focus:border-cyan-300/45"
										/>
									</label>
								))}
							</div>
							<div className="mt-3 grid grid-cols-3 gap-2">
								<label className="block">
									<div className="mb-1 text-[10px] text-white/38">宽 mm</div>
									<input type="number" value={selectedElement.widthMm ?? ''} onChange={(event) => updateSelectedElement({ widthMm: Number(event.target.value) || undefined })} className="w-full rounded-none border border-white/12 bg-black/28 px-2 py-1.5 text-[12px] text-white outline-none focus:border-cyan-300/45" />
								</label>
								<label className="block">
									<div className="mb-1 text-[10px] text-white/38">深 mm</div>
									<input type="number" value={selectedElement.depthMm ?? ''} onChange={(event) => updateSelectedElement({ depthMm: Number(event.target.value) || undefined })} className="w-full rounded-none border border-white/12 bg-black/28 px-2 py-1.5 text-[12px] text-white outline-none focus:border-cyan-300/45" />
								</label>
								<label className="block">
									<div className="mb-1 text-[10px] text-white/38">面积㎡</div>
									<input type="number" value={selectedElement.areaSqm ?? ''} onChange={(event) => updateSelectedElement({ areaSqm: Number(event.target.value) || undefined })} className="w-full rounded-none border border-white/12 bg-black/28 px-2 py-1.5 text-[12px] text-white outline-none focus:border-cyan-300/45" />
								</label>
							</div>
							<div className="mt-3 flex flex-wrap gap-1.5">
								<button onClick={() => updateSelectedElement({ x: Math.max(0, selectedElement.x - 0.01) })} className="rounded-full border border-white/12 px-2 py-1 text-[11px] text-white/62 hover:bg-white/8">左移</button>
								<button onClick={() => updateSelectedElement({ x: Math.min(0.98, selectedElement.x + 0.01) })} className="rounded-full border border-white/12 px-2 py-1 text-[11px] text-white/62 hover:bg-white/8">右移</button>
								<button onClick={() => updateSelectedElement({ y: Math.max(0, selectedElement.y - 0.01) })} className="rounded-full border border-white/12 px-2 py-1 text-[11px] text-white/62 hover:bg-white/8">上移</button>
								<button onClick={() => updateSelectedElement({ y: Math.min(0.98, selectedElement.y + 0.01) })} className="rounded-full border border-white/12 px-2 py-1 text-[11px] text-white/62 hover:bg-white/8">下移</button>
								<button onClick={() => updateSelectedElement({ status: 'confirmed' })} className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-2 py-1 text-[11px] text-emerald-100 hover:bg-emerald-300/16">确认</button>
								<button onClick={() => deletePlanElement(planViewerSpace, selectedElement.id)} className="rounded-full border border-rose-300/20 bg-rose-300/8 px-2 py-1 text-[11px] text-rose-100 hover:bg-rose-300/14">删除</button>
							</div>
						</div>
					)}
				</div>
			</div>
		);
	};

	const renderFileCard = (card: ProjectFileCard) => (
		<button
			key={card.title}
			onClick={() => openFileDetail(card)}
			className="cockpit-card cockpit-card-interactive cockpit-card-accent-files cockpit-file-card group flex flex-col p-6 text-left"
		>
			<div className="flex items-center justify-between gap-2 mb-2">
				<div className="ui-type-meta font-medium text-slate-400">{card.legacyCategory}</div>
				<span className="cockpit-card-chip">
					{card.stage}
				</span>
			</div>

			<h3 className="cockpit-card-title mb-2 text-slate-900 group-hover:text-sky-600">{getCardDisplayTitle(card)}</h3>

			<p
				className="cockpit-card-body text-slate-600 flex-1 mb-4"
				style={{
					display: '-webkit-box',
					WebkitLineClamp: 4,
					WebkitBoxOrient: 'vertical',
					overflow: 'hidden',
				}}
			>
				{card.desc}
			</p>

			<div className="flex flex-wrap items-center gap-1 mb-3">
				{card.domainTags.slice(0, 3).map((tag) => (
					<span key={tag} className="cockpit-card-chip cockpit-card-chip-accent">
						{tag}
					</span>
				))}
			</div>

			<div className="flex flex-wrap items-center gap-1 mb-3">
				<span className="cockpit-card-chip">
					锚点 {card.objectAnchor}
				</span>
				<span className="cockpit-card-chip">
					空间 {card.spaceScope}
				</span>
			</div>

			<div className="flex items-center justify-between pt-4 border-t border-slate-100">
				<div className="flex items-center gap-2">
					<span className="cockpit-card-chip cockpit-card-chip-accent">{card.badge}</span>
					<span className="cockpit-card-chip">{card.status}</span>
				</div>
				<div className="cockpit-meta-text text-slate-400 text-right">
					<div>引用 {card.refCount}</div>
					<div>{card.updatedAt}</div>
				</div>
			</div>
		</button>
	);

	const renderFileIndexRow = (card: ProjectFileCard) => (
		<button
			key={`file-index-${card.title}`}
			onClick={() => openFileDetail(card)}
			className="grid w-full grid-cols-[minmax(0,2.2fr)_120px_132px_100px_90px] items-center gap-4 border-t border-slate-100 px-4 py-3 text-left transition hover:bg-slate-50"
		>
			<div className="min-w-0">
				<div className="truncate text-sm font-semibold text-slate-900">{getCardDisplayTitle(card)}</div>
				<div className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">{card.desc}</div>
			</div>
			<div className="text-xs text-slate-500">{card.legacyCategory}</div>
			<div className="flex flex-wrap gap-1">
				<span className="cockpit-card-chip">锚点 {card.objectAnchor}</span>
				<span className="cockpit-card-chip">空间 {card.spaceScope}</span>
			</div>
			<div className="flex flex-wrap gap-1">
				<span className="cockpit-card-chip cockpit-card-chip-accent">{card.badge}</span>
				<span className="cockpit-card-chip">{card.status}</span>
			</div>
			<div className="text-right text-xs text-slate-400">
				<div>引用 {card.refCount}</div>
				<div>{card.updatedAt}</div>
			</div>
		</button>
	);

	const renderSpaceBoardIndexRow = (space: Exclude<ProjectFileCard['spaceScope'], '全局'>) => {
		const preview = boardSpacePreviewItems[space];
		const boardCount = boardSpaceItemCounts[space] ?? 0;
		return (
			<button
				key={`space-board-index-${space}`}
				onClick={() => {
					onEnterBoardSpace?.(space);
					onActiveBoardSpaceChange?.(space);
				}}
				className="grid w-full grid-cols-[minmax(0,2.2fr)_120px_132px_100px_90px] items-center gap-4 border-t border-slate-100 bg-sky-50/45 px-4 py-3 text-left transition hover:bg-sky-50"
			>
				<div className="min-w-0">
					<div className="truncate text-sm font-semibold text-slate-900">{toDisplaySpaceName(space)}·方案画布</div>
					<div className="mt-1 truncate text-xs text-slate-500">
						{preview?.title ?? `进入${toDisplaySpaceName(space)}空间画布，查看当前编排内容。`}
					</div>
				</div>
				<div className="text-xs text-slate-500">空间画布</div>
				<div className="flex flex-wrap gap-1">
					<span className="cockpit-card-chip">空间 {space}</span>
				</div>
				<div className="flex flex-wrap gap-1">
					<span className="cockpit-card-chip cockpit-card-chip-accent">已放入 {boardCount}</span>
				</div>
				<div className="text-right text-xs font-medium text-sky-600">进入画布</div>
			</button>
		);
	};

	const renderSpacePlanTopicIndexRow = (space: Exclude<ProjectFileCard['spaceScope'], '全局'>) => {
		const topic = spacePlanTopics[space] ?? createDefaultSpacePlanTopicStates()[space];
		const planView = SPACE_PLAN_VIEW_PRESETS[space];
		const enterSandbox = () => {
			if (onEnterSandboxSpace) {
				onEnterSandboxSpace(space);
				return;
			}
			handleOpenPlanViewer(space);
		};
		return (
			<div
				key={`space-plan-topic-index-${space}`}
				onClick={enterSandbox}
				onKeyDown={(event) => {
					if (event.key === 'Enter' || event.key === ' ') {
						event.preventDefault();
						enterSandbox();
					}
				}}
				role="button"
				tabIndex={0}
				className="grid w-full cursor-pointer grid-cols-[minmax(0,2.2fr)_120px_132px_100px_90px] items-center gap-4 border-t border-slate-100 bg-cyan-50/45 px-4 py-3 text-left transition hover:bg-cyan-50"
			>
				<div className="min-w-0">
					<div className="truncate text-sm font-semibold text-slate-900">{toDisplaySpaceName(space)}·平面推演</div>
					<div className="mt-1 truncate text-xs text-slate-500">
						{topic.uploadedFileName ?? `${planView.overallPlanRef.title} / ${planView.detailPlanRef.title}`}
					</div>
				</div>
				<div className="text-xs text-slate-500">平面推演</div>
				<div className="flex flex-wrap gap-1">
					<span className="cockpit-card-chip">空间 {space}</span>
					<span className="cockpit-card-chip">{topic.viewChain.join(' / ')}</span>
				</div>
				<div className="flex flex-wrap gap-1">
					<span className="cockpit-card-chip cockpit-card-chip-accent">{getPlanTopicStatusLabel(topic.status)}</span>
				</div>
				<div className="flex justify-end gap-2 text-xs font-medium">
					<button
						onClick={(event) => {
							event.stopPropagation();
							enterSandbox();
						}}
						className="text-slate-600 hover:text-slate-900"
					>
						进入沙盘
					</button>
				</div>
			</div>
		);
	};

	const renderSpaceBoardEntryCard = (space: Exclude<ProjectFileCard['spaceScope'], '全局'>) => {
		const preview = boardSpacePreviewItems[space];
		const boardCount = boardSpaceItemCounts[space] ?? 0;
		const previewSrc = preview?.imageSrc || fallbackPublicPictureSrc;
		const fallbackSrc = preview?.fallbackImageSrc || fallbackPublicPictureSrc;
		const representativeCard =
			filteredFileCards.find((card) => card.spaceScope === space) ??
			PROJECT_FILE_CARDS.find((card) => card.spaceScope === space) ??
			null;

		return (
			<div
				key={`space-board-entry-${space}`}
				className="cockpit-card cockpit-card-accent-assets cockpit-file-card group relative block w-full overflow-hidden text-left"
			>
				{previewSrc ? (
					<img
						src={previewSrc}
						alt={`${space} 方案画布`}
						className="absolute inset-0 block h-full w-full object-cover transition-[filter,transform] duration-300 group-hover:scale-[1.02] group-hover:brightness-[0.76]"
						loading="lazy"
						data-fallback-src={fallbackSrc}
						onError={handleResourceImageError}
					/>
				) : (
					<div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(14,23,54,0.82),rgba(26,86,164,0.42))]" />
				)}
				<div className={`absolute inset-0 z-[2] ${assetHoverTone()} opacity-10 transition-opacity duration-300 group-hover:opacity-100`} />
				<div className="absolute inset-x-0 top-0 z-[3] p-4">
					<span className="cockpit-asset-pill">空间画布</span>
				</div>
				<button
					type="button"
					onClick={() => {
						onEnterBoardSpace?.(space);
						onActiveBoardSpaceChange?.(space);
					}}
					className="absolute inset-0 z-[3] block text-left"
					aria-label={`进入${toDisplaySpaceName(space)}方案画布`}
				/>
				<div className="absolute inset-x-0 bottom-0 z-[4] p-4 text-white">
					<div className="cockpit-card-title line-clamp-2 text-white drop-shadow-sm">{toDisplaySpaceName(space)}·方案画布</div>
					<div className="mt-2 text-sm text-white/78">
						{representativeCard ? representativeCard.desc : '查看该空间的当前摘要与关联文件。'}
					</div>
					<div className="mt-2 flex flex-wrap gap-1.5">
						<span className="cockpit-asset-pill">已放入 {boardCount}</span>
						{preview && <span className="cockpit-asset-pill line-clamp-1 max-w-[11rem]">{preview.title}</span>}
					</div>
					<div className="mt-4 flex flex-wrap gap-2">
						<button
							type="button"
							onClick={() => {
								if (representativeCard) {
									openFileDetail(representativeCard);
								}
							}}
							className="cockpit-modal-action"
						>
							查看空间详情
						</button>
						<button
							type="button"
							onClick={() => onEnterBoardSpace?.(space)}
							className="cockpit-modal-action-active"
						>
							进入方案画布
						</button>
					</div>
				</div>
			</div>
		);
	};

	const renderSpacePlanTopicCard = (space: Exclude<ProjectFileCard['spaceScope'], '全局'>) => {
		const topic = spacePlanTopics[space] ?? createDefaultSpacePlanTopicStates()[space];
		const planView = SPACE_PLAN_VIEW_PRESETS[space];
		const statusLabel = getPlanTopicStatusLabel(topic.status);
		const enterSandbox = () => {
			if (onEnterSandboxSpace) {
				onEnterSandboxSpace(space);
				return;
			}
			handleOpenPlanViewer(space);
		};
		return (
			<div
				key={`space-plan-topic-${space}`}
				onClick={enterSandbox}
				onKeyDown={(event) => {
					if (event.key === 'Enter' || event.key === ' ') {
						event.preventDefault();
						enterSandbox();
					}
				}}
				role="button"
				tabIndex={0}
				className="cockpit-card cockpit-card-interactive cockpit-card-accent-files cockpit-file-card group flex h-[clamp(20rem,23vw,28rem)] cursor-pointer flex-col overflow-hidden p-0 text-left"
			>
				<div className="relative h-44 overflow-hidden bg-slate-950">
					<svg viewBox="0 0 420 176" className="h-full w-full">
						<rect width="420" height="176" fill="rgba(15,23,42,1)" />
						<rect x="34" y="28" width="352" height="116" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.25)" />
						<rect x="62" y="52" width="86" height="38" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.16)" />
						<rect x="172" y="52" width="92" height="38" fill="rgba(34,211,238,0.2)" stroke="rgba(34,211,238,0.75)" />
						<rect x="288" y="52" width="70" height="38" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.16)" />
						<rect x="62" y="104" width="118" height="28" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.16)" />
						<rect x="204" y="104" width="154" height="28" fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.16)" />
						<path d="M 70 132 C 128 112, 175 90, 218 72" stroke="rgba(250,204,21,0.7)" strokeWidth="5" fill="none" strokeLinecap="round" />
						<circle cx="218" cy="72" r="6" fill="rgb(34,211,238)" />
					</svg>
					<div className="absolute left-4 top-4 flex flex-wrap gap-2">
						<span className="cockpit-asset-pill">平面推演</span>
						<span className="cockpit-asset-pill">{statusLabel}</span>
					</div>
					<div className="absolute bottom-4 left-4 right-4 text-white">
						<div className="text-lg font-semibold">{toDisplaySpaceName(space)}·平面推演</div>
						<div className="mt-1 line-clamp-1 text-xs text-white/64">
							{topic.uploadedFileName ?? `${planView.overallPlanRef.title} / ${planView.detailPlanRef.title}`}
						</div>
					</div>
				</div>
				<div className="flex flex-1 flex-col justify-between p-5">
					<div>
						<p className="line-clamp-2 text-sm leading-6 text-slate-600">
							维护 {toDisplaySpaceName(space)} 的平面基线与 PlanBrief，进入沙盘继续推演并同步到方案画布。
						</p>
						<div className="mt-3 flex flex-wrap gap-1.5">
						<span className="cockpit-card-chip">视图链 {topic.viewChain.join(' / ')}</span>
						<span className="cockpit-card-chip">来源 {topic.sourceType.toUpperCase()}</span>
						{topic.uploadedFileSize && <span className="cockpit-card-chip">{formatFileSize(topic.uploadedFileSize)}</span>}
						</div>
						<div className="mt-3 text-xs text-slate-500">
							{topic.uploadedFileName ?? `${planView.overallPlanRef.title}`}
						</div>
					</div>
					<div className="mt-5 flex flex-wrap gap-2">
						<button
							type="button"
							onClick={(event) => { event.stopPropagation(); enterSandbox(); }}
							className={'cockpit-modal-action'}
						>
							进入平面推演
						</button>
					</div>
				</div>
			</div>
		);
	};

	const renderBoardGeneratedSourceCard = (item: BoardSourceItem, expanded: boolean) => {
		if (!item.generation) return null;

		const generationStatus = item.generation.status === 'collaged' ? 'generated' : item.generation.status;
		const isShortlisted = generationStatus === 'shortlisted';
		const isAdopted = generationStatus === 'adopted';
		const createdAtLabel = new Date(item.generation.createdAt).toLocaleString('zh-CN', {
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit',
		});

		return (
			<div key={item.id} className="group/card overflow-hidden rounded-none border border-white/70 bg-white shadow-[0_14px_36px_rgba(15,23,42,0.14)]">
				<div className="grid grid-cols-[1fr_1fr] gap-0">
					<div
						className="group/image relative overflow-hidden cursor-pointer"
						onClick={() => {
							addBoardCanvasItem(item);
						}}
						role="button"
						tabIndex={0}
						onKeyDown={(event) => {
							if (event.key === 'Enter' || event.key === ' ') {
								event.preventDefault();
								addBoardCanvasItem(item);
							}
						}}
						aria-label="点击图片加入画布"
					>
						<img
							src={item.imageSrc}
							alt={item.title}
							className="block h-full min-h-[188px] w-full object-cover transition-transform duration-300 group-hover/image:scale-110"
							data-fallback-src={item.fallbackImageSrc}
							onError={handleResourceImageError}
						/>
						<div className="pointer-events-none absolute inset-0 bg-black/0 transition duration-300 group-hover/image:bg-black/12" />
						<div className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-0 transition duration-200 group-hover/image:opacity-100">
							<span className="rounded-full bg-white/94 px-2.5 py-1 text-[10px] font-medium text-slate-900 shadow-sm">
								加入画布
							</span>
						</div>
					</div>
					<div className="flex min-w-0 min-h-[188px] flex-col justify-between p-3 text-slate-900">
						<div>
							<div className="truncate text-[15px] font-semibold leading-6">{item.title}</div>
							<div className="mt-1 line-clamp-2 text-[12px] leading-5 text-slate-500">{item.generation.promptSummary}</div>
							<div className="mt-3 flex flex-wrap items-center gap-3 text-[12px]">
								{item.referenceControl && (
									<span className="font-medium text-indigo-600 underline decoration-indigo-200 decoration-2 underline-offset-[5px]">
										{item.referenceControl.label}
									</span>
								)}
								<span className="font-medium text-sky-600 underline decoration-sky-200 decoration-2 underline-offset-[5px]">
									{item.generation.topicScope}
								</span>
								<span className="font-medium text-emerald-600 underline decoration-emerald-200 decoration-2 underline-offset-[5px]">
									{item.generation.space}
								</span>
							</div>
							{item.referenceControl && (
								<div className="mt-3 rounded-none border border-slate-200 bg-slate-50 px-3 py-2">
									<div className="text-[10px] uppercase tracking-[0.14em] text-slate-400">结构化引用</div>
									<div className="mt-1 line-clamp-2 text-[11px] leading-5 text-slate-600">
										{item.referenceControl.structuredSummary}
									</div>
									<div className="mt-2 flex flex-wrap gap-1.5">
										<span className="rounded-full bg-white px-2 py-0.5 text-[10px] text-slate-500">
											主参考 {item.referenceControl.primaryRole}
										</span>
										<span className="rounded-full bg-white px-2 py-0.5 text-[10px] text-slate-500">
											权重 {item.referenceControl.weight === 'high' ? '高' : item.referenceControl.weight === 'low' ? '低' : '中'}
										</span>
									</div>
								</div>
							)}
						</div>
						<div className="mt-4 space-y-2">
							<div className="min-h-[32px]">
								<div className="pointer-events-none flex flex-nowrap gap-1.5 opacity-0 transition duration-200 group-hover/card:pointer-events-auto group-hover/card:opacity-100">
									<button
										onClick={() =>
											updateBoardGeneratedItemStatus(
												item.sourceId,
												generationStatus === 'shortlisted' ? 'generated' : 'shortlisted'
											)
										}
										className={`rounded-full border px-2.5 py-1 text-[10px] font-medium transition ${
											isShortlisted
												? 'border-amber-200 bg-amber-100 text-amber-800'
												: 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
										}`}
									>
										{isShortlisted ? '候选' : '候选'}
									</button>
									<button
										onClick={() => updateBoardGeneratedItemStatus(item.sourceId, generationStatus === 'adopted' ? 'generated' : 'adopted')}
										className={`rounded-full border px-2.5 py-1 text-[10px] font-medium transition ${
											isAdopted
												? 'border-emerald-200 bg-emerald-100 text-emerald-800'
												: 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
										}`}
									>
										采纳
									</button>
									<button
										onClick={() => updateBoardGeneratedItemStatus(item.sourceId, 'archived')}
										className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-medium text-slate-500 hover:bg-slate-50"
									>
										归档
									</button>
									{item.referenceControl && (
										<button
											onClick={() => openReferenceEditModal('source', item.referenceControl!, { sourceId: item.id })}
											className="rounded-full border border-indigo-200 bg-white px-2.5 py-1 text-[10px] font-medium text-indigo-600 hover:bg-indigo-50"
										>
											引用详情
										</button>
									)}
								</div>
							</div>
							<div className="pb-1 text-left text-[11px] font-medium text-slate-500 whitespace-nowrap">
								第 {item.generation.round} 轮 · {createdAtLabel}
							</div>
						</div>
					</div>
				</div>
			</div>
		);
	};

	const renderExpertTeamCard = (item: ExpertTeamRoleItem) => {
		return (
			<div
				key={item.id}
				className="flex w-[8.5rem] flex-col items-center text-left"
			>
				<div className="flex flex-col items-center gap-3 text-center">
					<button
						onClick={() => openExpertDetail({ kind: 'role', id: item.id })}
						className="relative inline-flex h-[7.5rem] w-[7.5rem] shrink-0 items-center justify-center overflow-hidden rounded-full transition-transform hover:scale-[1.03]"
						aria-label={`查看 ${item.title} 详情`}
					>
						<img
							src={buildAdvisorAvatarUrl(item.avatarName)}
							alt={item.title}
							className="block h-full w-full rounded-full object-cover object-center"
						/>
						<span
							className={`absolute bottom-1 right-1 h-3.5 w-3.5 rounded-full border-2 border-white ${
								item.status === '当前激活' ? 'bg-emerald-400' : 'bg-slate-300'
							}`}
						/>
					</button>
					<div className="min-w-0 max-w-[7.5rem]">
						<div className="ui-type-meta font-medium leading-5 text-white break-words text-center whitespace-normal">
							{item.shortName}
						</div>
					</div>
				</div>
			</div>
		);
	};

	const renderExpertTaskCard = (item: ExpertTaskItem) => {
		return (
			<div
				key={item.id}
				className="cockpit-card cockpit-card-interactive cockpit-card-accent-experts bg-[#171717] text-left"
				onClick={() => openExpertDetail({ kind: 'task', id: item.id })}
				role="button"
				tabIndex={0}
				onKeyDown={(event) => {
					if (event.key === 'Enter' || event.key === ' ') {
						event.preventDefault();
						openExpertDetail({ kind: 'task', id: item.id });
					}
				}}
			>
				<div className="flex flex-col gap-4 p-4">
					<div className="flex items-start justify-between gap-3">
						<div className="min-w-0 flex-1">
							<div className="flex flex-wrap items-center gap-2">
								<span className="rounded-full border border-white/12 px-2.5 py-1 text-[10px] font-medium text-white/70">任务 {item.order}</span>
								<span className={`cockpit-card-chip ${item.status === '执行中' ? 'cockpit-card-chip-accent' : ''}`}>
									{item.status}
								</span>
							</div>
							<h4 className="ui-type-subtitle mt-3 font-semibold text-white">{item.title}</h4>
							<p className="ui-type-body mt-1 line-clamp-2 text-white/70">{item.mission}</p>
						</div>
						<div className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 text-white/55">
							<ChevronRight className="h-4 w-4" />
						</div>
					</div>

					<div className="flex items-center justify-between gap-3 border-t border-white/10 pt-3">
						<div className="ui-type-meta text-white/55">{item.team.join(' · ')}</div>
						<button onClick={(e) => { e.stopPropagation(); onCardClick?.(item.title); }} className="cockpit-card-action">
							插入当前项目
						</button>
					</div>
				</div>
			</div>
		);
	};

	const renderExpertReportCard = (item: ExpertReportItem) => {
		return (
			<div
				key={item.id}
				className="cockpit-card cockpit-card-interactive cockpit-card-accent-experts bg-[#171717] text-left"
				onClick={() => openExpertDetail({ kind: 'report', id: item.id })}
				role="button"
				tabIndex={0}
				onKeyDown={(event) => {
					if (event.key === 'Enter' || event.key === ' ') {
						event.preventDefault();
						openExpertDetail({ kind: 'report', id: item.id });
					}
				}}
			>
				<div className="flex flex-col gap-4 p-4">
					<div className="flex items-start justify-between gap-3">
						<div className="min-w-0 flex-1">
							<div className="flex flex-wrap items-center gap-2">
								<span className="rounded-full border border-white/12 px-2.5 py-1 text-[10px] font-medium text-white/70">专题确认</span>
								<span className="cockpit-card-chip cockpit-card-chip-accent">{item.lead}</span>
							</div>
							<h4 className="ui-type-subtitle mt-3 font-semibold text-white">{item.title}</h4>
							<p className="ui-type-body mt-1 line-clamp-2 text-white/70">{item.summary}</p>
						</div>
						<div className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 text-white/55">
							<ChevronRight className="h-4 w-4" />
						</div>
					</div>

					<div className="flex items-center justify-between gap-3 border-t border-white/10 pt-3">
						<div className="ui-type-meta text-white/55">{item.sourceTask}</div>
						<button onClick={(e) => { e.stopPropagation(); onCardClick?.(item.title); }} className="cockpit-card-action">
							写入当前项目
						</button>
					</div>
				</div>
			</div>
		);
	};

	const renderExpertReviewCard = (item: ExpertReviewItem) => {
		return (
			<div
				key={item.id}
				className="cockpit-card cockpit-card-interactive cockpit-card-accent-experts bg-[#171717] text-left"
				onClick={() => openExpertDetail({ kind: 'review', id: item.id })}
				role="button"
				tabIndex={0}
				onKeyDown={(event) => {
					if (event.key === 'Enter' || event.key === ' ') {
						event.preventDefault();
						openExpertDetail({ kind: 'review', id: item.id });
					}
				}}
			>
				<div className="flex flex-col gap-4 p-4">
					<div className="flex items-start justify-between gap-3">
						<div className="min-w-0 flex-1">
							<div className="flex flex-wrap items-center gap-2">
								<span className="rounded-full border border-white/12 px-2.5 py-1 text-[10px] font-medium text-white/70">{item.group}</span>
								<span className="cockpit-card-chip cockpit-card-chip-accent">冻结前必查</span>
							</div>
							<h4 className="ui-type-subtitle mt-3 font-semibold text-white">{item.title}</h4>
							<p className="ui-type-body mt-1 line-clamp-2 text-white/70">{item.summary}</p>
						</div>
						<div className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-white/10 text-white/55">
							<ChevronRight className="h-4 w-4" />
						</div>
					</div>

					<div className="flex items-center justify-between gap-3 border-t border-white/10 pt-3">
						<div className="ui-type-meta text-white/55">{item.source}</div>
						<button onClick={(e) => { e.stopPropagation(); onCardClick?.(item.title); }} className="cockpit-card-action">
							查看冻结项
						</button>
					</div>
				</div>
			</div>
		);
	};

	/* ─── 作品索引气泡图 ─── */
	const renderPortfolioBubbleChart = (
		entries: PersonalKnowledgeEntry[],
		sizeMode: PortfolioBubbleSizeMode,
		setSizeMode: (m: PortfolioBubbleSizeMode) => void,
		onClickBubble: (entry: PersonalKnowledgeEntry) => void,
		yearHeightScale = 1,
		availableWidth = 0,
	) => {
		const projects = entries.filter((e) => e.type === '作品' && e.portfolio);
		if (projects.length === 0) return null;

		// Y轴：年度（每年细分12个月）；X轴：空间类型
		const years = Array.from(new Set(projects.map((p) => p.portfolio!.year))).sort((a, b) => b - a);
		const spaceTypes = PORTFOLIO_SPACE_TYPES
			.filter((st) => projects.some((p) => p.portfolio!.spaceType === st))
			.sort((a, b) => {
				const countA = projects.filter((p) => p.portfolio!.spaceType === a).length;
				const countB = projects.filter((p) => p.portfolio!.spaceType === b).length;
				if (countB !== countA) return countB - countA;
				return PORTFOLIO_SPACE_TYPES.indexOf(a) - PORTFOLIO_SPACE_TYPES.indexOf(b);
			});

		const PAD_LEFT = 118;
		const YEAR_LABEL_X = 12;
		const PAD_TOP = 66; // 给列头与最近年份留出安全间距
		const PAD_RIGHT = 120;
		const PAD_BOTTOM = 12;
		const SCALE = Math.min(5, Math.max(1, yearHeightScale));
		// 压缩一半：每月 11px，按滑条放大年度间距
		const MONTH_H = 11 * SCALE;
		const YEAR_H = 12 * MONTH_H;
		const BASE_COL_W = 88;
		const COL_SIDE_GUTTER = 48;
		const MIN_R = 6.5, MAX_R = 23.4;
		const BUBBLE_SCALE = 1.2;
		// 气泡下方项目名预留高度
		const LABEL_H = 14;

		const getVal = (p: PortfolioProject) =>
			sizeMode === 'fee' ? p.designFee : p.designArea > 0 ? +(p.designFee / (p.designArea / 100)).toFixed(1) : 0;

		const paidProjects = projects.filter((e) => (e.portfolio?.designFee ?? 0) > 0);
		const allVals = paidProjects.map((e) => getVal(e.portfolio!));
		const minVal = allVals.length > 0 ? Math.min(...allVals) : 0;
		const maxVal = allVals.length > 0 ? Math.max(...allVals) : 1;
		const radiusOf = (v: number) => {
			if (maxVal === minVal) return (MIN_R + MAX_R) / 2;
			return MIN_R + ((v - minVal) / (maxVal - minVal)) * (MAX_R - MIN_R);
		};

		// 年的起始 Y
		const yearTopOf = (yi: number) => PAD_TOP + yi * YEAR_H;
		// 月份在年内的 Y（倒序：12月在上，1月在下；最近年份会在顶部保留未来月份空白）
		const monthCyOf = (yi: number, mo: number) => {
			const month = Math.min(12, Math.max(1, mo));
			return yearTopOf(yi) + (12 - month) * MONTH_H + MONTH_H / 2;
		};

		const baseChartW = PAD_LEFT + Math.max(0, spaceTypes.length - 1) * BASE_COL_W + PAD_RIGHT;
		const chartW = Math.max(baseChartW, availableWidth > 0 ? availableWidth : 0);
		const SLOT_W = spaceTypes.length > 1
			? Math.max(BASE_COL_W, (chartW - PAD_LEFT - PAD_RIGHT - COL_SIDE_GUTTER * 2) / (spaceTypes.length - 1))
			: BASE_COL_W;
		const spaceCxOf = (index: number) => {
			if (spaceTypes.length <= 1) return PAD_LEFT + (chartW - PAD_LEFT - PAD_RIGHT) / 2;
			return PAD_LEFT + COL_SIDE_GUTTER + index * SLOT_W;
		};
		const chartH = PAD_TOP + years.length * YEAR_H + PAD_BOTTOM + LABEL_H;

		const truncate = (s: string, max = 4) => s.length > max ? s.slice(0, max) + '…' : s;
		const placedLabelBoxes: Array<{ left: number; right: number; top: number; bottom: number }> = [];
		const LABEL_HEIGHT = 18;
		const LABEL_GAP = 4;
		const HEADER_SAFE_BOTTOM = PAD_TOP + 2;

		const overlaps = (a: { left: number; right: number; top: number; bottom: number }, b: { left: number; right: number; top: number; bottom: number }) =>
			a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;

		const buildLabelBox = (
			x: number,
			y: number,
			text: string,
			anchor: 'start' | 'middle' | 'end',
			baseline: 'auto' | 'middle' | 'hanging',
		) => {
			const textWidth = Math.max(32, text.length * 14);
			let left = x - textWidth / 2;
			let right = x + textWidth / 2;
			if (anchor === 'start') {
				left = x;
				right = x + textWidth;
			} else if (anchor === 'end') {
				left = x - textWidth;
				right = x;
			}

			let top = y - LABEL_HEIGHT;
			let bottom = y + 2;
			if (baseline === 'middle') {
				top = y - LABEL_HEIGHT / 2;
				bottom = y + LABEL_HEIGHT / 2;
			} else if (baseline === 'hanging') {
				top = y;
				bottom = y + LABEL_HEIGHT;
			}

			return {
				left: left - LABEL_GAP,
				right: right + LABEL_GAP,
				top: top - LABEL_GAP,
				bottom: bottom + LABEL_GAP,
			};
		};

		return (
			<div className="w-full overflow-visible rounded-2xl bg-white">

				<div className="overflow-x-auto overflow-y-visible [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
					<svg
						width={chartW}
						height={chartH}
						viewBox={`0 0 ${chartW} ${chartH}`}
						preserveAspectRatio="xMinYMin meet"
						className="select-none block max-w-none"
						style={{ display: 'block', fontFamily: 'inherit' }}
					>

						{/* 列头：空间类型 + 数量 + 金额（分行） */}
						{spaceTypes.map((st, si) => {
							const cx = spaceCxOf(si);
							const color = PORTFOLIO_SPACE_COLORS[st as PortfolioSpaceType] ?? '#94a3b8';
							const count = projects.filter((p) => p.portfolio!.spaceType === st).length;
							const totalFee = projects
								.filter((p) => p.portfolio!.spaceType === st)
								.reduce((sum, p) => sum + (p.portfolio?.designFee ?? 0), 0);
							return (
								<g key={st}>
									<text x={cx} y={PAD_TOP - 44} textAnchor="middle" fill={color} fontWeight="600" style={svgHeadingTextStyle}>{st}</text>
									<text x={cx} y={PAD_TOP - 26} textAnchor="middle" fill="#94a3b8" style={svgBodyTextStyle}>{count}个</text>
									<text x={cx} y={PAD_TOP - 10} textAnchor="middle" fill="#94a3b8" style={svgBodyTextStyle}>¥{totalFee}万</text>
									<circle cx={cx} cy={PAD_TOP + 6} r={2.5} fill={color} fillOpacity={0.95} />
								</g>
							);
						})}

						{/* 纵向虚线：每列从顶部连接空间业态，并贯穿到图表底部 */}
						{spaceTypes.map((st, si) => {
							const cx = spaceCxOf(si);
							const color = PORTFOLIO_SPACE_COLORS[st as PortfolioSpaceType] ?? '#94a3b8';
							const yFrom = PAD_TOP + 1;
							const yTo = PAD_TOP + years.length * YEAR_H;
							return (
								<line key={st} x1={cx} x2={cx} y1={yFrom} y2={yTo}
									stroke={color} strokeWidth={1.6} strokeOpacity={0.38} strokeDasharray="2 3" />
							);
						})}

						{/* Y轴：年度标签 */}
						{years.map((yr, yi) => {
							const yTop = yearTopOf(yi);
							return (
								<g key={yr}>
									{/* 年分隔线（去掉顶部首条，避免与空间业态横线重叠） */}
									{yi > 0 ? <line x1={PAD_LEFT - 8} x2={chartW - PAD_RIGHT} y1={yTop} y2={yTop} stroke="#e2e8f0" strokeWidth={1} /> : null}
									{/* 年份标签，居年段中 */}
									<text x={YEAR_LABEL_X} y={yTop + YEAR_H / 2 + 4} textAnchor="start" fill="#475569" fontWeight="600" style={svgBodyTextStyle}>{yr}</text>
								</g>
							);
						})}
						{/* 末尾分隔线 */}
						<line x1={PAD_LEFT - 8} x2={chartW - PAD_RIGHT} y1={PAD_TOP + years.length * YEAR_H} y2={PAD_TOP + years.length * YEAR_H} stroke="#e2e8f0" strokeWidth={1} />

						{/* 气泡 + 项目名（气泡正下方，黑色） */}
						{years.map((yr, yi) =>
							spaceTypes.map((st, si) => {
								const group = entries
									.filter((e) => e.type === '作品' && e.portfolio?.year === yr && e.portfolio?.spaceType === st)
									.sort((a, b) => (b.portfolio?.designFee ?? 0) - (a.portfolio?.designFee ?? 0));
								if (group.length === 0) return null;

								const cx = spaceCxOf(si);
								const color = PORTFOLIO_SPACE_COLORS[st as PortfolioSpaceType] ?? '#94a3b8';

								return (
									<g key={`${yr}-${st}`}>
										{group.map((entry, ei) => {
											const p = entry.portfolio!;
											const isPaid = p.designFee > 0;
											const val = getVal(p);
											const r = (isPaid ? radiusOf(val) : 6) * BUBBLE_SCALE;
											const mo = p.month ?? 6;
											// 同列同月多个气泡按索引错开（模拟小时偏移），间距 10px
											const groupSize = group.length;
											const offset = groupSize > 1 ? (ei - (groupSize - 1) / 2) * 10 : 0;
											const cy = monthCyOf(yi, mo) + offset;
											const sameMonthEntries = group.filter((g) => (g.portfolio?.month ?? 6) === mo);
											const sameMonthIndex = sameMonthEntries.findIndex((g) => g.id === entry.id);

											const labelText = truncate(entry.title || '未命名', 4);
											let labelX = cx;
											let labelY = cy + r + 9;
											let labelAnchor: 'start' | 'middle' | 'end' = 'middle';
											let labelBaseline: 'auto' | 'middle' | 'hanging' = 'auto';
											const baseIndex = sameMonthEntries.length > 1 && sameMonthIndex >= 0 ? sameMonthIndex : 0;
											const directionOrder = [
												{ mx: 0, my: 1 },
												{ mx: 1, my: 0 },
												{ mx: -1, my: 0 },
												{ mx: 0, my: -1 },
												{ mx: 0.75, my: 0.75 },
												{ mx: -0.75, my: 0.75 },
												{ mx: 0.75, my: -0.75 },
												{ mx: -0.75, my: -0.75 },
											];

											let placed = false;
											for (let tier = 0; tier < 6 && !placed; tier += 1) {
												const dist = r + 10 + tier * 10;
												for (let k = 0; k < directionOrder.length && !placed; k += 1) {
													const slot = (baseIndex + k) % directionOrder.length;
													const dir = directionOrder[slot];
													const candidateX = cx + dir.mx * dist;
													const candidateY = cy + dir.my * dist;
													const candidateAnchor: 'start' | 'middle' | 'end' = dir.mx > 0.2 ? 'start' : dir.mx < -0.2 ? 'end' : 'middle';
													const candidateBaseline: 'auto' | 'middle' | 'hanging' = dir.my > 0.2 ? 'hanging' : dir.my < -0.2 ? 'auto' : 'middle';
													const box = buildLabelBox(candidateX, candidateY, labelText, candidateAnchor, candidateBaseline);

													const inBounds = box.left >= PAD_LEFT - 30 && box.right <= chartW - PAD_RIGHT + 30 && box.top >= HEADER_SAFE_BOTTOM && box.bottom <= chartH - 2;
													const hasCollision = placedLabelBoxes.some((b) => overlaps(box, b));
													if (inBounds && !hasCollision) {
														labelX = candidateX;
														labelY = candidateY;
														labelAnchor = candidateAnchor;
														labelBaseline = candidateBaseline;
														placedLabelBoxes.push(box);
														placed = true;
													}
												}
											}

											if (!placed) {
												const fallbackBox = buildLabelBox(labelX, labelY, labelText, labelAnchor, labelBaseline);
												placedLabelBoxes.push(fallbackBox);
											}
											const tooltipText = `${entry.title}  ${yr}年${mo}月${isPaid ? `  ¥${val}万` : '  参与未收费'}`;

											return (
												<g key={entry.id} style={{ cursor: 'pointer' }} onClick={() => onClickBubble(entry)}>
													<title>{tooltipText}</title>
													{isPaid ? (
														<>
															<circle cx={cx} cy={cy} r={r} fill={color} fillOpacity={0.4} />
															<circle cx={cx} cy={cy} r={2} fill={color} fillOpacity={0.9} />
														</>
													) : (
														<>
															<circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={1.2} strokeDasharray="3 2" strokeOpacity={0.5} />
															<circle cx={cx} cy={cy} r={1.5} fill={color} fillOpacity={0.35} />
														</>
													)}
													{/* 项目名：气泡下方，黑色，居中 */}
													<text
														x={labelX}
														y={labelY}
														textAnchor={labelAnchor}
														dominantBaseline={labelBaseline}
														fill="#334155"
														style={{ ...svgLabelTextStyle, pointerEvents: 'none' }}
														>
														{labelText}
													</text>
												</g>
											);
										})}
									</g>
								);
							})
						)}
					</svg>
				</div>

			</div>
		);
	};

	const renderContent = () => {
		switch (moduleKey) {
			case 'knowledge':
				return (
					<div className="cockpit-panel-root w-full h-full flex flex-col overflow-hidden bg-[#f6f7fa]">
						<div className="cockpit-content-inset border-b border-slate-200 bg-white/90 backdrop-blur py-4">
							<div className="flex items-center gap-3">
								<h3 className="cockpit-panel-title text-slate-800">我的硅基分身</h3>
								<div className="ml-2 flex items-center gap-2">
									{[
										{ key: 'sediment' as const, label: '沉淀' },
										{ key: 'portfolio' as const, label: '作品' },
										{ key: 'profile' as const, label: '我' },
									].map((tab) => (
										<button
											key={tab.key}
											onClick={() => setDssPage(tab.key)}
											className={`h-8 rounded-full px-4 text-xs font-medium transition ${
												dssPage === tab.key
													? 'bg-slate-700 text-white shadow-sm'
													: 'bg-slate-300 text-slate-50 hover:bg-slate-400'
											}`}
										>
											{tab.label}
										</button>
									))}
								</div>
							</div>
							<div className={`flex flex-wrap items-center gap-1.5 mt-3 ${dssPage === 'sediment' ? '' : 'hidden'}`}>
								{(['全部', ...KNOWLEDGE_ENTRY_TYPES] as const).map((t) => (
									<button
										key={t}
										onClick={() => setKnowledgeTypeFilter(t as KnowledgeEntryType | '全部')}
										className={`cockpit-filter-pill ${knowledgeTypeFilter === t ? 'cockpit-filter-pill-active' : ''}`}
									>
										{t}
									</button>
								))}
							</div>
						</div>

						{/* 可滚动内容区：上方气泡图 + 下方左列表/右洞察 */}
						<div className="flex-1 min-h-0 overflow-y-auto">

						{/* ── 作品页：上部宽图，下部分析卡片 ── */}
						{dssPage === 'portfolio' ? (() => {
							const portfolioEntries = knowledgeEntries
								.filter((e) => e.type === '作品' && e.portfolio)
								.filter((e) => !PORTFOLIO_DEMO_HIDDEN_SPACE_TYPES.includes(e.portfolio!.spaceType as PortfolioSpaceType))
								.sort((a, b) => {
									const ay = a.portfolio!.year;
									const by = b.portfolio!.year;
									if (by !== ay) return by - ay;
									const am = a.portfolio!.month ?? 12;
									const bm = b.portfolio!.month ?? 12;
									return bm - am;
								});
							const totalProjects = portfolioEntries.length;
							const totalFee = portfolioEntries.reduce((sum, e) => sum + (e.portfolio?.designFee ?? 0), 0);
							const years = Array.from(new Set(portfolioEntries.map((e) => e.portfolio!.year))).sort((a, b) => a - b);
							const portfolioChartEntries = portfolioEntries;
							const spaceGroups = PORTFOLIO_SPACE_TYPES
								.map((space) => {
									const items = portfolioEntries.filter((e) => e.portfolio!.spaceType === space);
									const fee = items.reduce((sum, e) => sum + (e.portfolio?.designFee ?? 0), 0);
									const yearList = Array.from(new Set(items.map((e) => e.portfolio!.year))).sort((a, b) => a - b);
									const representative = items.slice(0, 3);
									const avgItemFee = items.length > 0 ? fee / items.length : 0;
									return {
										space,
										items,
										count: items.length,
										fee,
										yearList,
										representative,
										avgItemFee,
									};
								})
								.filter((group) => group.count > 0)
								.sort((a, b) => b.count - a.count || b.fee - a.fee);
							const leadingGroup = spaceGroups[0] ?? null;
							const avgFee = totalProjects > 0 ? (totalFee / totalProjects).toFixed(1) : '0.0';
							const avgPerSpace = spaceGroups.length > 0 ? (totalProjects / spaceGroups.length).toFixed(1) : '0.0';
							const overallConclusion = leadingGroup
								? `当前作品主要集中在${leadingGroup.space}方向，共${leadingGroup.count}个项目，累计收费约¥${leadingGroup.fee}万，说明你的项目重心更偏向这个空间类型。`
								: '录入作品后，这里会自动生成整体总结和分空间分析。';
							const makeSpaceInsight = (group: (typeof spaceGroups)[number]) => {
								const firstYear = group.yearList[0];
								const lastYear = group.yearList[group.yearList.length - 1];
								const period = firstYear && lastYear ? `${firstYear}–${lastYear}` : '时间待补充';
								const topProject = group.representative[0];
								const topProjectName = topProject?.title || '待补充项目';
								const projectShare = totalProjects > 0 ? Math.round((group.count / totalProjects) * 100) : 0;
								const feeShare = totalFee > 0 ? Math.round((group.fee / totalFee) * 100) : 0;
								const recentWindowStart = lastYear ? lastYear - 1 : undefined;
								const recentCount = recentWindowStart
									? group.items.filter((item) => item.portfolio!.year >= recentWindowStart).length
									: group.count;
								const recentRatio = group.count > 0 ? recentCount / group.count : 0;
								const recentTone = recentRatio >= 0.6 ? '近两年仍在加速' : recentRatio >= 0.4 ? '近两年保持活跃' : '近两年偏向收束';
								const makeTrendText = (space: PortfolioSpaceType) => {
									switch (space) {
										case '办公':
											return '趋势：从基础办公逐步走向总部、园区、金融/法务等高要求办公，后续更可能继续向“企业级解决方案”收束。';
										case '餐饮':
											return '趋势：从单店表达走向品牌化、连锁化和高频迭代，后续重点会转向标准化与复制能力。';
										case '住宅':
											return '趋势：从居住个案向更强的生活方式表达延伸，后续更适合沉淀为稳定的居住审美模板。';
										case '展陈':
											return '趋势：从事件型展陈走向品牌传播与内容叙事，后续需要补齐叙事结构和记忆点设计。';
										case '商业':
											return '趋势：从单点商业空间走向复合型商业场景，后续会更看重方法库复用和运营协同。';
										case '酒店':
											return '趋势：从氛围型酒店走向高端体验 + 运营效率并重的复合模型。';
										case '民宿':
											return '趋势：从轻量化单体民宿走向可复用的场景气质模型，强调个性与落地平衡。';
										case '文旅':
											return '趋势：从单点空间升级到目的地体验节点，后续会更强调系统整合与场景链路。';
										default:
											return '趋势：该空间类型仍处在持续积累阶段，后续可继续观察是否形成稳定的方法论。';
									}
								};
								const lens = (() => {
									switch (group.space as PortfolioSpaceType) {
										case '办公':
											return {
												core: '办公线已经不是单纯的数量堆积，而是在总部、园区、联合办公、法务/金融办公等不同语境里，逐步形成“组织效率 + 空间秩序”双主线。',
												market: `市场集中：当前办公项目约占全部作品的 ${projectShare}% ，收费贡献约 ${feeShare}% ，明显集中在企业扩张、组织升级和中高客单办公需求。`,
												competition: '竞争格局：办公赛道比拼的不只是效果，而是密度、效率、形象和成本控制的综合平衡，单纯拼风格的空间越来越少。',
												barrier: '核心壁垒：能同时处理组织动线、工位效率、接待形象和品牌秩序，且把复杂需求压成稳定方案的能力，是你最核心的优势。',
												change: `变化：办公项目跨年连续出现，${recentTone}，说明你已经从探索型项目进入可复用方法沉淀阶段。`,
												trend: '趋势：后续更适合继续往“企业级办公解决方案”方向收束，重点看你如何在形象、效率和成本之间建立稳定平衡。',
											};
										case '餐饮':
											return {
												core: '餐饮线体现的是高频试错与强场景表达，重点不是“做过多少”，而是你是否能把品牌气质、动线节奏和消费体验同时压住。',
												market: `市场集中：餐饮项目约占全部作品的 ${projectShare}% ，收费贡献约 ${feeShare}% ，主要集中在品牌餐饮、商场店和城市核心商业街区。`,
												competition: '竞争格局：餐饮竞争最激烈的是“第一眼识别 + 到店转化 + 高周转更新”，设计必须同时服务品牌和运营。',
												barrier: '核心壁垒：把品牌气质、动线节奏、座位效率和氛围记忆点一起打包的能力，是餐饮项目真正的壁垒。',
												change: `变化：餐饮项目更新快、分布密，${recentTone}，更像是你快速验证方法、迭代表达的试验场。`,
												trend: '趋势：后续如果继续累积餐饮项目，更值得看的是你能否从单店表达走向连锁化、标准化与品牌统一性的控制。',
											};
										case '住宅':
											return {
												core: '住宅线更偏生活方式与情绪尺度，判断重点不是商业效率，而是你是否在长期项目里形成了稳定的审美偏好和居住逻辑。',
												market: `市场集中：住宅项目约占全部作品的 ${projectShare}% ，收费贡献约 ${feeShare}% ，主要集中在改善型住宅、度假型居住和“民宿化生活方式”需求。`,
												competition: '竞争格局：住宅赛道比的是审美一致性、细节收口和长期居住体验，谁更懂生活、谁更能赢得高净值客户。',
												barrier: '核心壁垒：不是单纯做“好看”，而是能把材质、光线、尺度和居住气质统一起来，形成稳定的审美语言。',
												change: `变化：住宅项目跨年较长，${recentTone}，说明它更像是你持续打磨生活方式表达的积累线。`,
												trend: '趋势：如果继续往下做，住宅更适合向“居住气质模板”沉淀，而不是只停留在个案表达。',
											};
										case '展陈':
											return {
												core: '展陈线是叙事能力和节奏控制的试金石，空间本身不靠长期使用，而靠短时高密度的信息组织取胜。',
												market: `市场集中：展陈项目约占全部作品的 ${projectShare}% ，收费贡献约 ${feeShare}% ，集中在品牌传播、文化展示和节点事件类项目。`,
												competition: '竞争格局：展陈比拼的是内容转空间、空间转记忆的能力，核心不是堆装饰，而是讲清楚故事和节奏。',
												barrier: '核心壁垒：把叙事结构、动线组织和视觉记忆点串成一条完整体验链，是展陈赛道最重要的能力。',
												change: `变化：展陈项目通常围绕节点展开，${recentTone}，说明你在内容表达和空间叙事之间已经建立起稳定接口。`,
												trend: '趋势：后续若继续扩展，更值得补的是叙事结构、观展动线和视觉记忆点的系统化能力。',
											};
										case '商业':
											return {
												core: '商业线更看重转化效率和场景聚合能力，它不是单一空间，而是对人流、停留、识别和消费动机的综合响应。',
												market: `市场集中：商业项目约占全部作品的 ${projectShare}% ，收费贡献约 ${feeShare}% ，主要集中在商业体、街区更新和消费型场景。`,
												competition: '竞争格局：商业赛道竞争最直接，既比客流转化，也比空间吸引力和运营适配性，设计必须服务经营。',
												barrier: '核心壁垒：你真正的竞争力在于把目标客群、场景氛围和运营逻辑统一到一个空间方案里，而不是只做视觉包装。',
												change: `变化：商业项目往往体量更大、收费更高，${recentTone}，说明这条线正在从单点表达走向更强的场景整合。`,
												trend: '趋势：后续如果要继续加强，商业线应尽量从单点项目走向多类型复用的商业方法库。',
											};
										case '酒店':
											return {
												core: '酒店线最能体现系统能力，因为它既要处理品牌叙事，也要兼顾动线、体验、落位和运营细节，容错很低。',
												market: `市场集中：酒店项目约占全部作品的 ${projectShare}% ，收费贡献约 ${feeShare}% ，集中在精品酒店、度假酒店和高端住宿升级需求。`,
												competition: '竞争格局：酒店赛道不是拼单点效果，而是拼完整体验、品牌调性和运营效率，竞争门槛天然更高。',
												barrier: '核心壁垒：能把空间体验、服务动线、落位逻辑和成本控制同时落地，是酒店项目最关键的护城河。',
												change: `变化：酒店项目通常客单更高、尺度更完整，${recentTone}，说明你在高投入、高约束项目里有较强整体把控能力。`,
												trend: '趋势：后续可继续强化从“高端体验”到“运营效率”的双重平衡，避免只停留在氛围层面。',
											};
										case '民宿':
											return {
												core: '民宿线更像住宅与酒店之间的混合类型，它既要保留生活感，又要有商业转化和场景记忆点。',
												market: `市场集中：民宿项目约占全部作品的 ${projectShare}% ，收费贡献约 ${feeShare}% ，主要集中在景区周边、旅居度假和高品质私享空间。`,
												competition: '竞争格局：民宿竞争不在标准化，而在地域气质、情绪体验和“像当地、又超出当地”的能力。',
												barrier: '核心壁垒：选址判断、情绪表达、局部细节和低成本落地之间的平衡，是民宿设计最难复制的能力。',
												change: `变化：民宿项目通常依赖选址与情绪，${recentTone}，说明你在轻量化叙事上有一定手感。`,
												trend: '趋势：后续继续做民宿，重点不在复制同一风格，而在于形成一套可复用的场景气质模型。',
											};
										case '文旅':
											return {
												core: '文旅线更偏目的地逻辑，关注的不只是空间本身，而是空间如何成为一整套体验链路中的节点。',
												market: `市场集中：文旅项目约占全部作品的 ${projectShare}% ，收费贡献约 ${feeShare}% ，主要集中在目的地升级、文旅综合体和场景系统项目。`,
												competition: '竞争格局：文旅赛道的竞争不是单体设计，而是资源整合、空间叙事、运营协同和投资逻辑的综合比拼。',
												barrier: '核心壁垒：把单点空间做成体验链路的一环，并处理多方诉求和复杂协同，是文旅项目真正的高门槛能力。',
												change: `变化：文旅项目一般体量更大、综合性更强，${recentTone}，说明你已经开始触及从单体设计到场景系统的能力边界。`,
												trend: '趋势：后续如果持续发展，更适合向“目的地综合体验”继续深化，而不是只做单点装饰。',
											};
										default:
											return {
												core: `${group.space}线已经形成了较稳定的项目谱系，但还需要结合具体项目继续拆分它的阶段特征与方法倾向。`,
												market: `市场集中：当前 ${group.space} 项目约占全部作品的 ${projectShare}% ，收费贡献约 ${feeShare}% 。`,
												competition: '竞争格局：该空间类型的竞争逻辑仍可继续细分到客群、动线和体验层。',
												barrier: '核心壁垒：需要把已有项目进一步抽象为可复用的方法。',
												change: `变化：${recentTone}，说明这条线仍在持续演化。`,
												trend: '趋势：后续应继续积累代表性项目，以便把空间偏好进一步抽象成可复用的方法。',
											};
									}
								})();
								const action = (() => {
									switch (group.space as PortfolioSpaceType) {
										case '办公':
											return '建议继续向“企业级办公解决方案”收束，重点把总部、园区和效率型办公做成可复用模板。';
										case '餐饮':
											return '建议继续补强连锁化与标准化能力，让单店表达逐步变成品牌方法库。';
										case '住宅':
											return '建议继续沉淀生活方式模板，把住宅项目从个案美学推进到稳定的居住气质体系。';
										case '展陈':
											return '建议继续强化叙事结构和记忆点设计，把展陈项目做成可复制的内容转空间方法。';
										case '商业':
											return '建议继续围绕客群转化、场景氛围和运营逻辑形成多类型商业方案库。';
										case '酒店':
											return '建议继续平衡高端体验与运营效率，避免方案只停留在氛围层。';
										case '民宿':
											return '建议继续形成可复用的场景气质模型，让民宿从单点表达走向系列方法。';
										case '文旅':
											return '建议继续向目的地综合体验升级，补强资源整合与场景链路能力。';
										default:
											return '建议继续补充代表性项目，把当前偏好进一步抽象成方法论。';
									}
								})();
								return {
									core: lens.core,
									market: lens.market,
									competition: lens.competition,
									barrier: lens.barrier,
									change: lens.change,
									trend: lens.trend,
									next: action,
									meta: `${group.space}共${group.count}个项目，覆盖${period}。代表项目以${topProjectName}为首，累计收费约¥${group.fee}万，单项均值约¥${group.avgItemFee.toFixed(1)}万。`,
								};
							};

							const portfolioChartStableWidth = Math.max(portfolioChartWidth, portfolioChartShellRef.current?.clientWidth ?? 0, 1120);

							return (
								<div className="cockpit-content-inset space-y-5 py-5">
									<div ref={portfolioChartShellRef} className="cockpit-card cockpit-card-interactive cockpit-card-accent-files bg-white p-5">
										{(() => {
											const chart = renderPortfolioBubbleChart(
												portfolioChartEntries,
												portfolioBubbleSizeMode,
												setPortfolioBubbleSizeMode,
												(entry) => { setSelectedKnowledgeEntryId(entry.id); setKnowledgeDetailOpen(true); },
												portfolioYearHeightScale,
												Math.max(0, portfolioChartStableWidth - 2),
											);
											return chart ?? (
												<div className="flex h-56 flex-col items-center justify-center gap-2 text-sm text-slate-400">
													<span className="text-3xl">◎</span>
													<span>录入作品后显示索引图</span>
												</div>
											);
										})()}
									</div>

									<div className="cockpit-card cockpit-card-interactive cockpit-card-accent-files bg-white p-6">
										<div className="flex items-start justify-between gap-4">
											<div>
												<p className="text-sm font-semibold text-slate-800">职业生涯总结分析</p>
												<p className="text-xs text-slate-500">先看整体情况，再按空间细分</p>
											</div>
											{leadingGroup ? (
												<span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-medium text-slate-600">
													主力空间 {leadingGroup.space}
												</span>
											) : null}
										</div>
										<div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
											<div className="rounded-xl bg-slate-50 p-4">
												<p className="text-[11px] text-slate-500">项目总数</p>
												<p className="mt-1 text-lg font-semibold text-slate-800">{totalProjects}</p>
											</div>
											<div className="rounded-xl bg-slate-50 p-4">
												<p className="text-[11px] text-slate-500">时间跨度</p>
												<p className="mt-1 text-lg font-semibold text-slate-800">{years[0] ?? '—'} - {years[years.length - 1] ?? '—'}</p>
											</div>
											<div className="rounded-xl bg-slate-50 p-4">
												<p className="text-[11px] text-slate-500">总收费</p>
												<p className="mt-1 text-lg font-semibold text-slate-800">¥{totalFee} 万</p>
											</div>
											<div className="rounded-xl bg-slate-50 p-4">
												<p className="text-[11px] text-slate-500">平均单项</p>
												<p className="mt-1 text-lg font-semibold text-slate-800">¥{avgFee} 万</p>
											</div>
										</div>
										<div className="mt-5 rounded-xl bg-slate-50 p-5">
											<p className="text-xs font-semibold text-slate-700">整体结论</p>
											<p className="mt-2 text-sm leading-7 text-slate-700">{overallConclusion}</p>
											<ol className="mt-4 space-y-3 text-sm leading-7 text-slate-700">
												<li>1. 当前作品谱系覆盖 {spaceGroups.length} 类空间，平均每类 {avgPerSpace} 个项目。</li>
												<li>2. 平均单项收费约 ¥{avgFee} 万，说明你的经验积累已不是单点试验，而是有明确的空间偏向。</li>
												<li>3. 主力空间是 {leadingGroup?.space ?? '待形成'}，后续分析会围绕它展开对比和复盘。</li>
											</ol>
										</div>
									</div>

									<div className="columns-1 gap-4 xl:columns-2">
										{spaceGroups.map((group) => (
											<div key={group.space} className="cockpit-card cockpit-card-interactive cockpit-card-accent-files mb-6 inline-block w-full break-inside-avoid bg-white p-6">
												<div className="flex items-start justify-between gap-4">
													<div>
														<p className="text-sm font-semibold text-slate-500">空间分析</p>
														<p className="mt-1 text-lg font-semibold text-slate-800">{group.space}</p>
													</div>
													<div className="text-right">
														<p className="text-xs text-slate-500">作品数</p>
														<p className="text-sm font-semibold text-slate-800">{group.count} 个</p>
													</div>
												</div>

												<ol className="mt-5 space-y-5 text-sm leading-7 text-slate-700">
													<li>
														<p className="font-medium text-slate-800">1. 核心判断</p>
														<p className="mt-1">{makeSpaceInsight(group).core}</p>
													</li>
													<li>
														<p className="font-medium text-slate-800">2. 麦肯锡式维度诊断</p>
														<ul className="mt-3 space-y-3 text-slate-700">
															<li><span className="font-semibold text-slate-800">市场集中：</span>{makeSpaceInsight(group).market}</li>
															<li><span className="font-semibold text-slate-800">竞争格局：</span>{makeSpaceInsight(group).competition}</li>
															<li><span className="font-semibold text-slate-800">核心壁垒：</span>{makeSpaceInsight(group).barrier}</li>
															<li><span className="font-semibold text-slate-800">变化：</span>{makeSpaceInsight(group).change}</li>
															<li><span className="font-semibold text-slate-800">趋势：</span>{makeSpaceInsight(group).trend}</li>
														</ul>
													</li>
													<li>
														<p className="font-medium text-slate-800">3. 代表项目</p>
														<ul className="mt-3 space-y-3">
															{group.representative.map((item, idx) => (
																<li key={item.id} className="flex items-start gap-2">
																	<span className="mt-[3px] inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-100 text-[11px] font-medium text-slate-600">{idx + 1}</span>
																	<button
																		onClick={() => { setSelectedKnowledgeEntryId(item.id); setKnowledgeDetailOpen(true); }}
																		className="text-left text-slate-700 transition hover:text-slate-900"
																	>
																		{item.title || '未命名'} · {item.portfolio?.year ?? '—'}年
																	</button>
																</li>
															))}
														</ul>
													</li>
													<li>
														<p className="font-medium text-slate-800">4. 后续判断</p>
														<p className="mt-1">{makeSpaceInsight(group).next}</p>
													</li>
												</ol>
											</div>
										))}
									</div>
								</div>
							);
						})() : null}

						{/* ── 下部：左侧案例列表 + 右侧职业生涯洞察卡片（图2尺寸） ── */}
						<div className="cockpit-content-inset py-2">
						<div className={dssPage === 'profile' ? '' : 'hidden'}>
						{/* DSS: 职业生涯总结分析洞察卡片（右侧） */}
						{designerProfile ? (() => {
							/* ── KPI 计算 ── */
							const coveredCells = new Set(
								designerProfile.specialtyMatrix
									.filter((s) => s.confidenceLevel === 'done')
									.map((s) => `${s.archetype}|${s.geoType}`)
							);
							const totalCells = DSS_ARCHETYPES.length * DSS_GEO_TYPES.length;
							const coveragePct = totalCells > 0 ? Math.round((coveredCells.size / totalCells) * 100) : 0;

							const pwArr = Object.values(designerProfile.perspectiveWeights);
							const biasIndex = pwArr.length > 0 ? ((Math.max(...pwArr) - Math.min(...pwArr)) / 10).toFixed(2) : '0';

							let blindSpots = 0;
							for (const arch of DSS_ARCHETYPES) {
								for (const geo of DSS_GEO_TYPES) {
									const demand = DSS_MARKET_DEMAND[arch]?.[geo] ?? 0;
									if (demand >= 5 && !coveredCells.has(`${arch}|${geo}`)) blindSpots++;
								}
							}

							const ndKeys = Object.keys(DSS_NINE_DIM_LABELS) as (keyof DSSNineDimSensitivity)[];
							const ndSens = designerProfile.nineDimSensitivity ?? DSS_NINE_DIM_INDUSTRY_MEDIAN;
							const ndSorted = [...ndKeys].sort((a, b) => (ndSens[b] ?? 0) - (ndSens[a] ?? 0));
							const ndStrong = ndSorted.slice(0, 2).map((k) => DSS_NINE_DIM_LABELS[k]);
							const ndWeak = ndSorted.slice(-2).map((k) => DSS_NINE_DIM_LABELS[k]);
							const ndDiagnosis = `偏倚形状：${ndStrong.join('/')}维度饱满，${ndWeak.join('/')}维度较低。同类项目中对${ndWeak[0]}的主动思考明显低于中位。`;

							const pwTotal = pwArr.reduce((s, v) => s + v, 0) || 1;
							const pwKeys = Object.keys(DSS_PERSPECTIVE_LABELS) as (keyof DSSPerspectiveWeights)[];
							const pwPcts = pwKeys.map((k) => ({
								key: k,
								label: DSS_PERSPECTIVE_LABELS[k],
								pct: Math.round((designerProfile.perspectiveWeights[k] / pwTotal) * 100),
								val: designerProfile.perspectiveWeights[k],
							})).sort((a, b) => b.pct - a.pct);
							const spectrumColors = ['#4b83c4', '#5b7fb8', '#7b88aa', '#9b92a0', '#b89c96', '#d4a68c', '#e8b080'];

							return (
								<div className="space-y-px">
									{/* 名片 + 编辑入口 */}
									<div className="bg-slate-800 text-white px-5 py-4 rounded-t-xl flex items-center justify-between">
										<div className="flex items-center gap-3">
											<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-sky-600 text-white text-lg font-bold">{designerProfile.displayName?.[0] || '我'}</div>
											<div>
												<div className="flex items-center gap-2">
													<span className="font-semibold">{designerProfile.displayName || '未命名设计师'}</span>
													<span className="text-xs text-slate-400">· {designerProfile.companyType}</span>
												</div>
												<p className="text-xs text-slate-400">从业 {designerProfile.yearsOfExperience} 年 · {designerProfile.city || '—'} · {designerProfile.specialtyMatrix.filter(s => s.confidenceLevel === 'done').map(s => s.archetype).filter(Boolean).slice(0, 2).join('与') || '—'}方向</p>
											</div>
										</div>
										<button onClick={() => setDssProfileOpen(true)} className="text-xs text-slate-400 border border-slate-600 rounded px-3 py-1.5 hover:bg-slate-700 hover:text-slate-200 transition">编辑画像</button>
									</div>

									{/* L0: KPI 卡片 */}
									<div className="grid grid-cols-4 gap-px bg-slate-100">
										{[
											{ label: '版图覆盖度', value: `${coveragePct}%`, sub: `${totalCells} 格中 ${coveredCells.size} 格有经验`, accent: coveragePct >= 30 },
											{ label: '七维偏倚指数', value: biasIndex, sub: `偏${pwPcts[0]?.label ?? '—'}维度`, accent: Number(biasIndex) > 0.3 },
											{ label: '盲区机会数', value: `${blindSpots}`, sub: '匹配当前市场', accent: blindSpots >= 5 },
											{ label: '画像完整度', value: (() => { const f = [designerProfile.displayName, designerProfile.city, designerProfile.yearsOfExperience > 0, designerProfile.decisionStyle.primaryApproach, designerProfile.specialtyMatrix.length > 0].filter(Boolean).length; return `${Math.round((f / 5) * 100)}%`; })(), sub: '基础字段', accent: false },
										].map((kpi) => (
											<div key={kpi.label} className="bg-white px-4 py-3">
												<p className="text-[11px] text-slate-500 mb-0.5">{kpi.label}</p>
												<p className={`text-xl font-bold ${kpi.accent ? 'text-sky-600' : 'text-slate-800'}`}>{kpi.value}</p>
												<p className="text-[10px] text-slate-400">{kpi.sub}</p>
											</div>
										))}
									</div>

									{/* L1: 九维雷达 + 版图矩阵 */}
									<div className="grid grid-cols-2 items-stretch gap-px bg-slate-100">
										{/* 九维敏感度雷达 */}
										<div className="bg-white p-4 flex min-h-[460px] flex-col">
											<div className="flex items-center gap-2 mb-2">
												<h5 className="text-xs font-semibold text-slate-800">九维敏感度雷达</h5>
												<span className="text-[9px] text-slate-400">实线·你 &nbsp; 灰线·行业中位</span>
											</div>
											<div className="mt-1 flex-1 min-h-[360px]">
												<Radar
													data={{
														labels: ndKeys.map((k) => DSS_NINE_DIM_LABELS[k]),
														datasets: [
															{
																label: '你',
																data: ndKeys.map((k) => getNineDimRadarScore(k, ndSens)),
																backgroundColor: 'rgba(99, 102, 241, 0.12)',
																borderColor: 'rgb(99, 102, 241)',
																borderWidth: 2,
																fill: true,
																showLine: true,
																pointBackgroundColor: 'rgb(99, 102, 241)',
																pointBorderColor: '#fff',
																pointRadius: 3,
															},
															{
																label: '行业中位',
																data: ndKeys.map((k) => clampRadarScore(DSS_NINE_DIM_INDUSTRY_MEDIAN[k] * 10)),
																backgroundColor: 'transparent',
																borderColor: 'rgba(148, 163, 184, 0.5)',
																borderWidth: 1.5,
																fill: false,
																showLine: true,
																pointRadius: 0,
															},
															{
																label: '成长期望',
																data: ndKeys.map((k) => clampRadarScore(Math.max(getNineDimRadarScore(k, ndSens), DSS_NINE_DIM_INDUSTRY_MEDIAN[k] * 10) + 16)),
																backgroundColor: 'rgba(245, 158, 11, 0.1)',
																borderColor: 'rgb(245, 158, 11)',
																borderWidth: 1.5,
																fill: true,
																showLine: true,
																pointBackgroundColor: 'rgb(245, 158, 11)',
																pointRadius: 2,
															},
															{
																label: '项目证据',
																data: ndKeys.map((k) => clampRadarScore(Math.max(18, getNineDimRadarScore(k, ndSens) * 0.72 + coveragePct * 0.28 + (k === 'space' || k === 'function' || k === 'flow' ? 12 : 0)))),
																backgroundColor: 'rgba(20, 184, 166, 0.08)',
																borderColor: 'rgb(20, 184, 166)',
																borderWidth: 1.5,
																fill: true,
																showLine: true,
																pointBackgroundColor: 'rgb(20, 184, 166)',
																pointRadius: 2,
															},
														],
													}}
													options={{
														responsive: true,
														maintainAspectRatio: false,
														scales: {
															r: {
																min: 0,
																max: 100,
																ticks: { stepSize: 33, display: true, font: { size: 8 }, color: 'rgba(148,163,184,0.5)', backdropColor: 'transparent' },
																pointLabels: { font: { size: 10, weight: 'bold' as const }, color: 'rgb(71, 85, 105)' },
																grid: { color: 'rgba(148, 163, 184, 0.2)' },
																angleLines: { color: 'rgba(148, 163, 184, 0.2)' },
															},
														},
														plugins: {
															legend: { display: true, position: 'bottom' as const, labels: { boxWidth: 10, boxHeight: 10, font: { size: 10 }, color: 'rgb(71, 85, 105)' } },
															tooltip: { enabled: true },
														},
													}}
												/>
											</div>
											<p className="text-[10px] text-slate-500 mt-1 leading-relaxed">{ndDiagnosis}</p>
										</div>

										{/* 业态×地理 版图 */}
										<div className="bg-white p-4 flex min-h-[460px] flex-col">
											<div className="flex items-center gap-2 mb-2">
												<h5 className="text-xs font-semibold text-slate-800">业态 × 地理 版图</h5>
												<span className="text-[9px] text-slate-400">蓝·项目密度 &nbsp; 橙框·机会盲区</span>
											</div>
											<div className="overflow-x-auto flex-1">
												<table className="w-full border-collapse text-[10px]">
													<thead>
														<tr>
															<th className="w-10" />
															{DSS_GEO_TYPES.map((geo) => (
																<th key={geo} className="px-1.5 py-1 text-center font-medium text-slate-600">{geo}</th>
															))}
														</tr>
													</thead>
													<tbody>
														{DSS_ARCHETYPES.map((arch) => (
															<tr key={arch}>
																<td className="pr-1.5 py-0.5 text-right font-medium text-slate-600 whitespace-nowrap">{arch}</td>
																{DSS_GEO_TYPES.map((geo) => {
																	const entries = designerProfile.specialtyMatrix.filter(
																		(s) => s.archetype === arch && s.geoType === geo
																	);
																	const done = entries.filter((s) => s.confidenceLevel === 'done');
																	const familiar = entries.filter((s) => s.confidenceLevel === 'familiar');
																	const count = done.length;
																	const demand = DSS_MARKET_DEMAND[arch]?.[geo] ?? 0;
																	const isBlindSpot = count === 0 && demand >= 5;
																	const hasFamiliar = familiar.length > 0 && count === 0;
																	return (
																		<td key={geo} className="p-0.5">
																			<div
																				className={`h-8 flex items-center justify-center rounded-sm text-[10px] font-bold transition-colors ${
																					count > 0
																						? count >= 5 ? 'bg-sky-500 text-white' : count >= 2 ? 'bg-sky-300 text-sky-900' : 'bg-sky-100 text-sky-700'
																						: hasFamiliar ? 'bg-sky-50 text-sky-400' : 'bg-slate-50 text-slate-300'
																				} ${isBlindSpot ? 'ring-2 ring-amber-400 ring-inset' : ''}`}
																				title={isBlindSpot ? `市场需求 ${demand}/10，你未覆盖` : count > 0 ? `${count} 个项目` : ''}
																			>
																				{count > 0 ? count : hasFamiliar ? '·' : ''}
																			</div>
																		</td>
																	);
																})}
															</tr>
														))}
													</tbody>
												</table>
											</div>
											<div className="flex gap-3 mt-1.5">
												{[
													['bg-sky-500', '深耕'],
													['bg-sky-100', '少量'],
													['bg-slate-50 ring-2 ring-amber-400 ring-inset', '盲区'],
												].map(([cls, label]) => (
													<span key={label} className="flex items-center gap-1 text-[9px] text-slate-500">
														<span className={`inline-block w-2.5 h-2.5 rounded-sm ${cls}`} />{label}
													</span>
												))}
											</div>
											<p className="text-[10px] text-slate-500 mt-1 leading-relaxed">
												{blindSpots > 0
													? `主战场：${designerProfile.specialtyMatrix.filter(s => s.confidenceLevel === 'done').map(s => `${s.geoType}${s.archetype}`).slice(0, 2).join('、') || '—'}。${blindSpots} 个盲区匹配市场高需求。`
													: '添加业态经验后显示版图诊断。'}
											</p>
										</div>
									</div>

									{/* 七视角决策光谱 */}
									<div className="bg-white p-4 rounded-b-xl">
										<div className="flex items-center gap-2 mb-2">
											<h5 className="text-xs font-semibold text-slate-800">七视角决策光谱</h5>
											<span className="text-[9px] text-slate-400">各视角在决策中的发声占比</span>
										</div>
										<div className="flex mb-0.5">
											{pwPcts.map((p, i) => (
												<div key={p.key} className="text-center text-[9px] font-semibold" style={{ width: `${Math.max(p.pct, 3)}%`, color: spectrumColors[i] ?? '#999' }}>
													{p.label}
												</div>
											))}
										</div>
										<div className="flex h-6 rounded-sm overflow-hidden">
											{pwPcts.map((p, i) => (
												<div
													key={p.key}
													className="h-full flex items-center justify-center text-white text-[9px] font-bold transition-all"
													style={{ width: `${Math.max(p.pct, 3)}%`, backgroundColor: spectrumColors[i] ?? '#999' }}
													title={`${p.label}: ${p.pct}% (权重 ${p.val})`}
												/>
											))}
										</div>
										<div className="flex mt-0.5">
											{pwPcts.map((p) => (
												<div key={p.key} className="text-center text-[9px] text-slate-500" style={{ width: `${Math.max(p.pct, 3)}%` }}>
													{p.pct}%
												</div>
											))}
										</div>
										<p className="text-[10px] text-slate-500 mt-2 leading-relaxed">
											{pwPcts[0] && pwPcts[pwPcts.length - 1]
												? `${pwPcts[0].label}与${pwPcts[1]?.label ?? ''}视角过载，${pwPcts[pwPcts.length - 1].label}与${pwPcts[pwPcts.length - 2]?.label ?? ''}视角失声。`
												: '填写七视角权重后显示光谱诊断。'}
										</p>
									</div>
								</div>
							);
						})() : (
							<div className="pb-1">
								<button
									onClick={() => setDssProfileOpen(true)}
									className="flex w-full items-center gap-3 rounded-xl border border-dashed border-sky-200 bg-sky-50/50 p-4 text-left transition hover:border-sky-300 hover:bg-sky-50"
								>
									<div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-sky-100 text-sky-500">
										<Eye className="h-5 w-5" />
									</div>
									<div>
										<p className="text-sm font-medium text-sky-700">开始构建你的硅基分身</p>
										<p className="text-xs text-sky-500 mt-0.5">创建设计师画像，让 AI 更懂你的判断习惯与专业优势</p>
									</div>
								</button>
							</div>
						)}
						</div>

						<div className={`${dssPage === 'sediment' ? '' : 'hidden'}`}>
							{/* ── 快录区 ── */}
							<div className="sticky top-0 z-10 bg-[#f6f7fa] pt-5 pb-3 border-b border-slate-100">
								<div className="flex min-h-[64px] items-center gap-3 rounded-xl border border-slate-300 bg-white px-4 py-3 shadow-[0_10px_28px_rgba(15,23,42,0.08)] ring-1 ring-white">
									<span className="shrink-0 rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white">速记</span>
									<input
										value={dssQuickText}
										onChange={(e) => setDssQuickText(e.target.value)}
										onKeyDown={(e) => {
											if (e.key === 'Enter' && dssQuickText.trim()) {
												handleCaptureSedimentQuickNote();
											}
										}}
										placeholder="随手记一条想法，回车先保存原文，稍后再分类"
										className="h-10 flex-1 min-w-0 bg-transparent text-base text-slate-900 placeholder:text-slate-400 outline-none"
									/>
									<button
										onClick={handleCaptureSedimentQuickNote}
										disabled={!dssQuickText.trim()}
										className="h-10 shrink-0 rounded-lg bg-slate-900 px-5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-30"
									>保存</button>
								</div>
							</div>
							{/* ── 卡片区（分组渲染）── */}
							{(() => {
								const sedimentEntries = filteredKnowledgeEntries.filter(e => e.type !== '作品');
								if (sedimentEntries.length === 0) {
									return (
										<div>
											<div className="flex flex-col items-center justify-center py-20 text-slate-400 gap-2">
												<span className="text-3xl">◎</span>
												<span className="text-sm">速记你的第一条经验资产</span>
												<span className="text-xs text-slate-300">先原样保存，稍后再归入习惯、方法、禁忌或复盘</span>
											</div>
										</div>
									);
								}
								const typeColorMap: Record<string, { bg: string; chip: string }> = {
									'待分类': { bg: 'bg-white border-b border-slate-100', chip: 'bg-slate-100 text-slate-400' },
									'习惯': { bg: 'bg-white border-b border-slate-100', chip: 'bg-slate-100 text-slate-600' },
									'经验': { bg: 'bg-white border-b border-slate-100', chip: 'bg-slate-100 text-slate-600' },
									'方法': { bg: 'bg-white border-b border-slate-100', chip: 'bg-slate-100 text-slate-600' },
									'模板': { bg: 'bg-white border-b border-slate-100', chip: 'bg-slate-100 text-slate-600' },
									'禁忌': { bg: 'bg-white border-b border-slate-100', chip: 'bg-slate-100 text-slate-600' },
									'案例复盘': { bg: 'bg-white border-b border-slate-100', chip: 'bg-slate-100 text-slate-600' },
								};
								const statusStyleMap: Record<string, string> = {
									'草稿': 'bg-slate-100 text-slate-400',
									'已整理': 'bg-slate-100 text-slate-500',
									'已验证': 'bg-slate-100 text-slate-500',
									'可复用': 'bg-slate-100 text-slate-500',
								};
								const draftEntries = sedimentEntries.filter(e => e.status === '草稿');
								const readyEntries = sedimentEntries.filter(e => e.status !== '草稿');
								const renderEntry = (entry: PersonalKnowledgeEntry) => {
									const tc = typeColorMap[entry.type] ?? { bg: 'bg-white', chip: 'cockpit-card-chip-accent' };
									const sc = statusStyleMap[entry.status] ?? 'bg-slate-100 text-slate-400';
									return (
										<div key={entry.id} className={`cockpit-masonry-item ${dssQuickNewId === entry.id ? 'ring-2 ring-sky-400 ring-offset-1 rounded-xl' : ''}`}>
											<button
												onClick={() => { setSelectedKnowledgeEntryId(entry.id); setKnowledgeDetailOpen(true); }}
												className="cockpit-card cockpit-card-interactive cockpit-asset-card group block w-full overflow-hidden text-left"
											>
												<div className={`h-20 px-4 pt-4 ${tc.bg}`}>
													<div className="flex items-center justify-between gap-2">
														<span className={`cockpit-card-chip ${tc.chip}`}>{entry.type}</span>
														<span className={`cockpit-card-chip ${sc}`}>{entry.status}</span>
													</div>
												</div>
												<div className="px-4 pb-4 pt-3">
													<h3 className="cockpit-card-title mb-1.5 text-slate-900 group-hover:text-sky-600">{entry.title || '未命名知识'}</h3>
													{entry.summary ? <p className="cockpit-card-body text-slate-600">{entry.summary}</p> : null}
													{entry.content && !entry.summary ? <p className="cockpit-card-body text-slate-500">{entry.content}</p> : null}
													<div className="mt-3 flex flex-wrap gap-1.5">
														{(entry.tags ?? []).slice(0, 4).map((tag) => (
															<span key={`${entry.id}-${tag}`} className="cockpit-card-chip">{tag}</span>
														))}
													</div>
												</div>
											</button>
										</div>
									);
								};
								return (
									<div className="pb-6">
										{draftEntries.length > 0 && (
											<div className="mb-5 pt-4">
												<p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">待完善 · {draftEntries.length}</p>
												<div className="cockpit-masonry-grid cockpit-masonry-knowledge">{draftEntries.map(renderEntry)}</div>
											</div>
										)}
										{readyEntries.length > 0 && (
											<div className={draftEntries.length > 0 ? 'pt-2' : 'pt-4'}>
												{draftEntries.length > 0 && <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">最近录入 · {readyEntries.length}</p>}
												<div className="cockpit-masonry-grid cockpit-masonry-knowledge">{readyEntries.map(renderEntry)}</div>
											</div>
										)}
									</div>
								);
							})()}
						</div>
						</div>{/* ── 下部双列结束 ── */}
						</div>{/* ── 上下布局容器结束 ── */}

						{isClient && knowledgeDetailOpen && selectedKnowledgeEntry ? (
							<div className="cockpit-readable-overlay z-[2147483646]" onClick={() => setKnowledgeDetailOpen(false)}>
								<div onClick={(e) => e.stopPropagation()} className="cockpit-readable-overlay-shell p-8">
									<div className="mx-auto w-full max-w-3xl bg-white p-6 shadow-2xl">
										<div className="mb-4 flex items-center justify-between gap-3">
											<input
												value={selectedKnowledgeEntry.title}
												onChange={(e) => upsertSelectedKnowledgeEntry({ title: e.target.value })}
												className="ui-type-subtitle flex-1 font-semibold text-slate-900 border-none outline-none bg-transparent focus:border-b focus:border-slate-300"
												placeholder="知识条目标题"
											/>
											<button
												onClick={() => setKnowledgeDetailOpen(false)}
												className="inline-flex h-8 items-center justify-center rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-700 hover:border-slate-300"
											>
												关闭
											</button>
										</div>
										<div className="mb-3 flex flex-wrap items-center gap-2">
											<label className="text-xs text-slate-500">类型</label>
											{KNOWLEDGE_ENTRY_TYPES.map((t) => (
												<button
													key={t}
													onClick={() => upsertSelectedKnowledgeEntry({ type: t })}
													className={`cockpit-filter-pill text-xs ${selectedKnowledgeEntry.type === t ? 'cockpit-filter-pill-active' : ''}`}
												>
													{t}
												</button>
											))}
											<span className="mx-2 text-slate-300">|</span>
											<label className="text-xs text-slate-500">状态</label>
											{KNOWLEDGE_ENTRY_STATUS.map((s) => (
												<button
													key={s}
													onClick={() => upsertSelectedKnowledgeEntry({ status: s })}
													className={`cockpit-filter-pill text-xs ${selectedKnowledgeEntry.status === s ? 'cockpit-filter-pill-active' : ''}`}
												>
													{s}
												</button>
											))}
										</div>
										<input
											value={selectedKnowledgeEntry.summary}
											onChange={(e) => upsertSelectedKnowledgeEntry({ summary: e.target.value })}
											className="mb-3 w-full border border-slate-200 px-3 py-2 text-sm text-slate-700 outline-none focus:border-slate-400"
											placeholder="摘要（一句话概括）"
										/>
										<textarea
											value={selectedKnowledgeEntry.content}
											onChange={(e) => upsertSelectedKnowledgeEntry({ content: e.target.value })}
											rows={12}
											className="ui-type-body w-full rounded-none border border-slate-200 px-3 py-2 text-slate-800 outline-none focus:border-slate-400"
											placeholder="详细内容..."
										/>
										<div className="mt-4 flex flex-wrap items-center gap-2">
											<button
												onClick={() => onCardClick?.(`[我的硅基分身] ${selectedKnowledgeEntry.title}`)}
												className="cockpit-card-action-solid"
											>
												引用到右侧
											</button>
											<button
												onClick={handleDeleteKnowledgeEntry}
												className="inline-flex h-8 items-center justify-center rounded-none border border-rose-200 bg-rose-50 px-3 text-sm text-rose-600 transition hover:bg-rose-100"
											>
												删除
											</button>
										</div>
									</div>
								</div>
							</div>
						) : null}

						{/* DSS: 设计师画像仪表盘 */}
						{isClient && dssProfileOpen ? (
							<div className="cockpit-readable-overlay z-[2147483646]" onClick={() => setDssProfileOpen(false)}>
								<div onClick={(e) => e.stopPropagation()} className="cockpit-readable-overlay-shell p-6" style={{ maxHeight: '92vh', overflowY: 'auto' }}>
									<div className="mx-auto w-full max-w-5xl bg-white shadow-2xl">

										{designerProfile ? (() => {
											/* ── KPI 计算 ── */
											const coveredCells = new Set(
												designerProfile.specialtyMatrix
													.filter((s) => s.confidenceLevel === 'done')
													.map((s) => `${s.archetype}|${s.geoType}`)
											);
											const totalCells = DSS_ARCHETYPES.length * DSS_GEO_TYPES.length;
											const coveragePct = totalCells > 0 ? Math.round((coveredCells.size / totalCells) * 100) : 0;

											const pwArr = Object.values(designerProfile.perspectiveWeights);
											const biasIndex = pwArr.length > 0 ? ((Math.max(...pwArr) - Math.min(...pwArr)) / 10).toFixed(2) : '0';

											let blindSpots = 0;
											for (const arch of DSS_ARCHETYPES) {
												for (const geo of DSS_GEO_TYPES) {
													const demand = DSS_MARKET_DEMAND[arch]?.[geo] ?? 0;
													if (demand >= 5 && !coveredCells.has(`${arch}|${geo}`)) blindSpots++;
												}
											}

											/* ── 九维诊断文字 ── */
											const ndKeys = Object.keys(DSS_NINE_DIM_LABELS) as (keyof DSSNineDimSensitivity)[];
											const ndSens = designerProfile.nineDimSensitivity ?? DSS_NINE_DIM_INDUSTRY_MEDIAN;
											const ndSorted = [...ndKeys].sort((a, b) => (ndSens[b] ?? 0) - (ndSens[a] ?? 0));
											const ndStrong = ndSorted.slice(0, 2).map((k) => DSS_NINE_DIM_LABELS[k]);
											const ndWeak = ndSorted.slice(-2).map((k) => DSS_NINE_DIM_LABELS[k]);
											const ndDiagnosis = `偏倚形状：${ndStrong.join('/')}维度饱满，${ndWeak.join('/')}维度较低。同类项目中对${ndWeak[0]}的主动思考明显低于中位。`;

											/* ── 七视角占比 ── */
											const pwTotal = pwArr.reduce((s, v) => s + v, 0) || 1;
											const pwKeys = Object.keys(DSS_PERSPECTIVE_LABELS) as (keyof DSSPerspectiveWeights)[];
											const pwPcts = pwKeys.map((k) => ({
												key: k,
												label: DSS_PERSPECTIVE_LABELS[k],
												pct: Math.round((designerProfile.perspectiveWeights[k] / pwTotal) * 100),
												val: designerProfile.perspectiveWeights[k],
											})).sort((a, b) => b.pct - a.pct);
											const spectrumColors = ['#4b83c4', '#5b7fb8', '#7b88aa', '#9b92a0', '#b89c96', '#d4a68c', '#e8b080'];

											return (
												<>
													{/* ── 头部名片 ── */}
													<div className="bg-slate-800 text-white px-6 py-5">
														<div className="flex items-center justify-between">
															<div className="flex items-center gap-4">
																<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-sky-600 text-white text-lg font-bold">
																	{designerProfile.displayName?.[0] || '我'}
																</div>
																<div>
																	<div className="flex items-center gap-2">
																		<span className="text-lg font-semibold">{designerProfile.displayName || '未命名设计师'}</span>
																		<span className="text-xs text-slate-400">· {designerProfile.companyType}</span>
																	</div>
																	<p className="text-sm text-slate-400">从业 {designerProfile.yearsOfExperience} 年 · {designerProfile.city || '—'} · {designerProfile.specialtyMatrix.filter(s => s.confidenceLevel === 'done').map(s => s.archetype).filter(Boolean).slice(0, 2).join('与') || '—'}方向</p>
																</div>
															</div>
															<div className="flex items-center gap-3">
																<span className="text-[10px] text-slate-500 border border-slate-600 rounded px-2 py-0.5">硅基分身 v1.3</span>
																<button
																	onClick={() => setDssProfileOpen(false)}
																	className="inline-flex h-8 items-center justify-center rounded-md border border-slate-600 bg-slate-700 px-3 text-sm text-slate-300 hover:bg-slate-600"
																>
																	关闭
																</button>
															</div>
														</div>
													</div>

													{/* ── L0: KPI 卡片带 ── */}
													<div className="grid grid-cols-4 gap-px bg-slate-100">
														{[
															{ label: '版图覆盖度', value: `${coveragePct}%`, sub: `${totalCells} 格中 ${coveredCells.size} 格有经验`, accent: coveragePct >= 30 },
															{ label: '七维偏倚指数', value: biasIndex, sub: `中位 0.18 · 偏${pwPcts[0]?.label ?? '—'}维度`, accent: Number(biasIndex) > 0.3 },
															{ label: '盲区机会数', value: `${blindSpots}`, sub: '匹配当前市场', accent: blindSpots >= 5 },
															{ label: '画像完整度', value: (() => { const f = [designerProfile.displayName, designerProfile.city, designerProfile.yearsOfExperience > 0, designerProfile.decisionStyle.primaryApproach, designerProfile.specialtyMatrix.length > 0].filter(Boolean).length; return `${Math.round((f / 5) * 100)}%`; })(), sub: '基础字段填写率', accent: false },
														].map((kpi) => (
															<div key={kpi.label} className="bg-white px-5 py-4">
																<p className="text-[11px] text-slate-500 mb-1">{kpi.label}</p>
																<p className={`text-2xl font-bold ${kpi.accent ? 'text-sky-600' : 'text-slate-800'}`}>{kpi.value}</p>
																<p className="text-[10px] text-slate-400 mt-0.5">{kpi.sub}</p>
															</div>
														))}
													</div>

													{/* ── L1: 主看板 ── */}
													<div className="grid grid-cols-2 items-stretch gap-px bg-slate-100 mt-px">
														{/* 九维敏感度雷达 */}
														<div className="bg-white p-5 flex min-h-[520px] flex-col">
															<div className="flex items-center gap-2 mb-3">
																<h5 className="text-sm font-semibold text-slate-800">九维敏感度雷达</h5>
																<span className="text-[10px] text-slate-400">实线·你 &nbsp; 灰线·行业中位</span>
															</div>
															<div className="mt-1 flex-1 min-h-[400px]">
																<Radar
																	data={{
																		labels: ndKeys.map((k) => DSS_NINE_DIM_LABELS[k]),
																		datasets: [
																			{
																				label: '你',
																				data: ndKeys.map((k) => getNineDimRadarScore(k, ndSens)),
																				backgroundColor: 'rgba(99, 102, 241, 0.12)',
																				borderColor: 'rgb(99, 102, 241)',
																				borderWidth: 2,
																				fill: true,
																				showLine: true,
																				pointBackgroundColor: 'rgb(99, 102, 241)',
																				pointBorderColor: '#fff',
																				pointRadius: 3,
																			},
																			{
																				label: '行业中位',
																				data: ndKeys.map((k) => clampRadarScore(DSS_NINE_DIM_INDUSTRY_MEDIAN[k] * 10)),
																				backgroundColor: 'transparent',
																				borderColor: 'rgba(148, 163, 184, 0.5)',
																				borderWidth: 1.5,
																				fill: false,
																				showLine: true,
																pointRadius: 0,
															},
															{
																label: '成长期望',
																data: ndKeys.map((k) => clampRadarScore(Math.max(getNineDimRadarScore(k, ndSens), DSS_NINE_DIM_INDUSTRY_MEDIAN[k] * 10) + 16)),
																backgroundColor: 'rgba(245, 158, 11, 0.1)',
																borderColor: 'rgb(245, 158, 11)',
																borderWidth: 1.5,
																fill: true,
																showLine: true,
																pointBackgroundColor: 'rgb(245, 158, 11)',
																pointRadius: 2,
															},
															{
																label: '项目证据',
																data: ndKeys.map((k) => clampRadarScore(Math.max(18, getNineDimRadarScore(k, ndSens) * 0.72 + coveragePct * 0.28 + (k === 'space' || k === 'function' || k === 'flow' ? 12 : 0)))),
																backgroundColor: 'rgba(20, 184, 166, 0.08)',
																borderColor: 'rgb(20, 184, 166)',
																borderWidth: 1.5,
																fill: true,
																showLine: true,
																pointBackgroundColor: 'rgb(20, 184, 166)',
																pointRadius: 2,
															},
														],
																	}}
																	options={{
																		responsive: true,
																		maintainAspectRatio: false,
																		scales: {
																			r: {
																				min: 0,
																				max: 100,
																				ticks: { stepSize: 33, display: true, font: { size: 8 }, color: 'rgba(148,163,184,0.5)', backdropColor: 'transparent' },
																				pointLabels: { font: { size: 11, weight: 'bold' as const }, color: 'rgb(71, 85, 105)' },
																				grid: { color: 'rgba(148, 163, 184, 0.2)' },
																				angleLines: { color: 'rgba(148, 163, 184, 0.2)' },
																			},
																		},
																		plugins: {
																			legend: { display: true, position: 'bottom' as const, labels: { boxWidth: 10, boxHeight: 10, font: { size: 10 }, color: 'rgb(71, 85, 105)' } },
																			tooltip: { enabled: true },
																		},
																	}}
																/>
															</div>
															<p className="text-[10px] text-slate-500 mt-2 leading-relaxed">{ndDiagnosis}</p>
														</div>

														{/* 业态×地理 版图 */}
														<div className="bg-white p-5 flex min-h-[520px] flex-col">
															<div className="flex items-center gap-2 mb-3">
																<h5 className="text-sm font-semibold text-slate-800">业态 × 地理 版图</h5>
																<span className="text-[10px] text-slate-400">蓝色·你的项目密度 &nbsp; 橙框·市场机会盲区</span>
															</div>
															<div className="overflow-x-auto flex-1">
																<table className="w-full border-collapse text-[11px]">
																	<thead>
																		<tr>
																			<th className="w-12" />
																			{DSS_GEO_TYPES.map((geo) => (
																				<th key={geo} className="px-2 py-1.5 text-center font-medium text-slate-600">{geo}</th>
																			))}
																		</tr>
																	</thead>
																	<tbody>
																		{DSS_ARCHETYPES.map((arch) => (
																			<tr key={arch}>
																				<td className="pr-2 py-1 text-right font-medium text-slate-600 whitespace-nowrap">{arch}</td>
																				{DSS_GEO_TYPES.map((geo) => {
																					const entries = designerProfile.specialtyMatrix.filter(
																						(s) => s.archetype === arch && s.geoType === geo
																					);
																					const done = entries.filter((s) => s.confidenceLevel === 'done');
																					const familiar = entries.filter((s) => s.confidenceLevel === 'familiar');
																					const count = done.length;
																					const demand = DSS_MARKET_DEMAND[arch]?.[geo] ?? 0;
																					const isBlindSpot = count === 0 && demand >= 5;
																					const hasFamiliar = familiar.length > 0 && count === 0;
																					return (
																						<td key={geo} className="p-0.5">
																							<div
																								className={`h-10 flex items-center justify-center rounded-sm text-xs font-bold transition-colors ${
																									count > 0
																										? count >= 5 ? 'bg-sky-500 text-white' : count >= 2 ? 'bg-sky-300 text-sky-900' : 'bg-sky-100 text-sky-700'
																										: hasFamiliar ? 'bg-sky-50 text-sky-400' : 'bg-slate-50 text-slate-300'
																								} ${isBlindSpot ? 'ring-2 ring-amber-400 ring-inset' : ''}`}
																								title={isBlindSpot ? `市场需求 ${demand}/10，你未覆盖` : count > 0 ? `${count} 个项目` : ''}
																							>
																								{count > 0 ? count : hasFamiliar ? '·' : ''}
																								{isBlindSpot && <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-amber-400" />}
																							</div>
																						</td>
																					);
																				})}
																			</tr>
																		))}
																	</tbody>
																</table>
															</div>
															<div className="flex gap-4 mt-2">
																{[
																	['bg-sky-500', '深耕'],
																	['bg-sky-100', '少量'],
																	['bg-slate-50 ring-2 ring-amber-400 ring-inset', '机会盲区'],
																].map(([cls, label]) => (
																	<span key={label} className="flex items-center gap-1 text-[9px] text-slate-500">
																		<span className={`inline-block w-3 h-3 rounded-sm ${cls}`} />{label}
																	</span>
																))}
															</div>
															<p className="text-[10px] text-slate-500 mt-2 leading-relaxed">
																{blindSpots > 0
																	? `主战场明确在${designerProfile.specialtyMatrix.filter(s => s.confidenceLevel === 'done').map(s => `${s.geoType}${s.archetype}`).slice(0, 2).join('、') || '—'}。${blindSpots} 个盲区机会匹配当前市场需求高而你未涉足，是可开拓的相邻域。`
																	: '添加更多业态经验后，此处将显示版图诊断。'}
															</p>
														</div>
													</div>

													{/* 七视角决策光谱 */}
													<div className="bg-white mt-px p-5">
														<div className="flex items-center gap-2 mb-3">
															<h5 className="text-sm font-semibold text-slate-800">七视角决策光谱</h5>
															<span className="text-[10px] text-slate-400">你的决策回写中，各视角的发声占比 &nbsp; ▼ 行业理想分布参考点</span>
														</div>
														{/* 标签行 */}
														<div className="flex mb-1">
															{pwPcts.map((p, i) => (
																<div key={p.key} className="text-center text-[10px] font-semibold" style={{ width: `${Math.max(p.pct, 3)}%`, color: spectrumColors[i] ?? '#999' }}>
																	{p.label}
																</div>
															))}
														</div>
														{/* 堆叠条 */}
														<div className="flex h-8 rounded-sm overflow-hidden">
															{pwPcts.map((p, i) => (
																<div
																	key={p.key}
																	className="h-full flex items-center justify-center text-white text-[10px] font-bold transition-all"
																	style={{ width: `${Math.max(p.pct, 3)}%`, backgroundColor: spectrumColors[i] ?? '#999' }}
																	title={`${p.label}: ${p.pct}% (权重 ${p.val})`}
																/>
															))}
														</div>
														{/* 百分比行 */}
														<div className="flex mt-1">
															{pwPcts.map((p, i) => (
																<div key={p.key} className="text-center text-[10px] text-slate-500" style={{ width: `${Math.max(p.pct, 3)}%` }}>
																	{p.pct}%
																</div>
															))}
														</div>
														<p className="text-[10px] text-slate-500 mt-3 leading-relaxed">
															{pwPcts[0] && pwPcts[pwPcts.length - 1]
																? `${pwPcts[0].label}与${pwPcts[1]?.label ?? ''}视角明显过载，${pwPcts[pwPcts.length - 1].label}与${pwPcts[pwPcts.length - 2]?.label ?? ''}视角长期失声。一个项目 20 条决策回写里，能看到${pwPcts[pwPcts.length - 1].label}判断的不到 1 条。`
																: '填写七视角权重后，此处显示决策光谱诊断。'}
														</p>
													</div>

													{/* ── 编辑区（折叠） ── */}
													<details className="bg-white mt-px">
														<summary className="px-5 py-3 text-sm font-medium text-slate-700 cursor-pointer hover:bg-slate-50 select-none">
															▸ 编辑画像数据
														</summary>
														<div className="px-5 pb-5 space-y-4">
															<div className="grid grid-cols-3 gap-4">
																<div>
																	<label className="text-xs text-slate-500 mb-1 block">姓名 / 昵称</label>
																	<input value={designerProfile.displayName} onChange={(e) => setDesignerProfile((p) => p ? { ...p, displayName: e.target.value, updatedAt: new Date().toISOString() } : p)} className="w-full border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400" />
																</div>
																<div>
																	<label className="text-xs text-slate-500 mb-1 block">所在城市</label>
																	<input value={designerProfile.city} onChange={(e) => setDesignerProfile((p) => p ? { ...p, city: e.target.value, updatedAt: new Date().toISOString() } : p)} className="w-full border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400" />
																</div>
																<div>
																	<label className="text-xs text-slate-500 mb-1 block">从业年限</label>
																	<input type="number" min={0} max={50} value={designerProfile.yearsOfExperience} onChange={(e) => setDesignerProfile((p) => p ? { ...p, yearsOfExperience: Number(e.target.value) || 0, updatedAt: new Date().toISOString() } : p)} className="w-full border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400" />
																</div>
															</div>
															<div className="grid grid-cols-2 gap-4">
																<div>
																	<label className="text-xs text-slate-500 mb-1 block">团队规模</label>
																	<div className="flex flex-wrap gap-1.5">
																		{(['独立', '小团队(2-5)', '中型(6-20)', '大型(20+)'] as const).map((size) => (
																			<button key={size} onClick={() => setDesignerProfile((p) => p ? { ...p, teamSize: size, updatedAt: new Date().toISOString() } : p)} className={`cockpit-filter-pill text-xs ${designerProfile.teamSize === size ? 'cockpit-filter-pill-active' : ''}`}>{size}</button>
																		))}
																	</div>
																</div>
																<div>
																	<label className="text-xs text-slate-500 mb-1 block">公司类型</label>
																	<div className="flex flex-wrap gap-1.5">
																		{(['独立设计师', '设计事务所', '地产内部', '设计公司'] as const).map((ct) => (
																			<button key={ct} onClick={() => setDesignerProfile((p) => p ? { ...p, companyType: ct, updatedAt: new Date().toISOString() } : p)} className={`cockpit-filter-pill text-xs ${designerProfile.companyType === ct ? 'cockpit-filter-pill-active' : ''}`}>{ct}</button>
																		))}
																	</div>
																</div>
															</div>
															<div className="grid grid-cols-2 gap-4">
																<div>
																	<label className="text-xs text-slate-500 mb-1 block">决策风格</label>
																	<input value={designerProfile.decisionStyle.primaryApproach} onChange={(e) => setDesignerProfile((p) => p ? { ...p, decisionStyle: { ...p.decisionStyle, primaryApproach: e.target.value }, updatedAt: new Date().toISOString() } : p)} placeholder="例：先定终局目标，再推导空间策略" className="w-full border border-slate-200 px-3 py-2 text-sm outline-none focus:border-slate-400" />
																</div>
																<div>
																	<label className="text-xs text-slate-500 mb-1 block">风险偏好</label>
																	<div className="flex gap-1.5 pt-1">
																		{([['conservative', '保守型'], ['moderate', '稳健型'], ['aggressive', '激进型']] as const).map(([val, label]) => (
																			<button key={val} onClick={() => setDesignerProfile((p) => p ? { ...p, decisionStyle: { ...p.decisionStyle, riskTolerance: val }, updatedAt: new Date().toISOString() } : p)} className={`cockpit-filter-pill text-xs ${designerProfile.decisionStyle.riskTolerance === val ? 'cockpit-filter-pill-active' : ''}`}>{label}</button>
																		))}
																	</div>
																</div>
															</div>

															{/* 九维敏感度滑块 */}
															<div className="border-t border-slate-100 pt-3">
																<label className="text-xs text-slate-500 mb-2 block">九维本体敏感度（拖动调整，实时联动雷达图）</label>
																<div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
																	{ndKeys.map((dim) => (
																		<div key={dim} className="flex items-center gap-2">
																			<span className="w-8 text-right text-xs text-slate-600 font-medium">{DSS_NINE_DIM_LABELS[dim]}</span>
																			<input type="range" min={0} max={10} step={1} value={ndSens[dim] ?? 5}
																				onChange={(e) => setDesignerProfile((p) => p ? { ...p, nineDimSensitivity: { ...(p.nineDimSensitivity ?? DSS_NINE_DIM_INDUSTRY_MEDIAN), [dim]: Number(e.target.value) }, updatedAt: new Date().toISOString() } : p)}
																				className="flex-1 h-1.5 accent-indigo-500 cursor-pointer" />
																			<span className={`w-5 text-center text-xs font-bold ${(ndSens[dim] ?? 5) >= 7 ? 'text-indigo-600' : (ndSens[dim] ?? 5) >= 4 ? 'text-slate-600' : 'text-slate-400'}`}>{ndSens[dim] ?? 5}</span>
																		</div>
																	))}
																</div>
															</div>

															{/* 七视角权重滑块 */}
															<div className="border-t border-slate-100 pt-3">
																<label className="text-xs text-slate-500 mb-2 block">七视角决策权重（拖动调整，实时联动光谱条）</label>
																<div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
																	{pwKeys.map((dim) => (
																		<div key={dim} className="flex items-center gap-2">
																			<span className="w-8 text-right text-xs text-slate-600 font-medium">{DSS_PERSPECTIVE_LABELS[dim]}</span>
																			<input type="range" min={0} max={10} step={1} value={designerProfile.perspectiveWeights[dim]}
																				onChange={(e) => setDesignerProfile((p) => p ? { ...p, perspectiveWeights: { ...p.perspectiveWeights, [dim]: Number(e.target.value) }, updatedAt: new Date().toISOString() } : p)}
																				className="flex-1 h-1.5 accent-sky-500 cursor-pointer" />
																			<span className={`w-5 text-center text-xs font-bold ${designerProfile.perspectiveWeights[dim] >= 7 ? 'text-sky-600' : designerProfile.perspectiveWeights[dim] >= 4 ? 'text-slate-600' : 'text-slate-400'}`}>{designerProfile.perspectiveWeights[dim]}</span>
																		</div>
																	))}
																</div>
															</div>

															{/* 业态能力矩阵编辑 */}
															<div className="border-t border-slate-100 pt-3">
																<div className="flex items-center justify-between mb-2">
																	<label className="text-xs text-slate-500">业态能力矩阵（编辑后版图自动更新）</label>
																	<button onClick={() => setDesignerProfile((p) => p ? { ...p, specialtyMatrix: [...p.specialtyMatrix, { archetype: '', geoType: '', brandPositioning: '', projectCount: 0, role: '主创', confidenceLevel: 'done' }], updatedAt: new Date().toISOString() } : p)} className="text-xs text-sky-600 hover:text-sky-800 transition">+ 添加业态</button>
																</div>
																{designerProfile.specialtyMatrix.length === 0 ? (
																	<p className="text-xs text-slate-400 py-2">暂无业态记录，点击「添加业态」开始积累</p>
																) : (
																	<div className="space-y-2 max-h-48 overflow-y-auto">
																		{designerProfile.specialtyMatrix.map((entry, idx) => (
																			<div key={idx} className="grid grid-cols-[1fr_1fr_auto_auto_auto] gap-2 items-center">
																				<select value={entry.archetype} onChange={(e) => { const next = [...designerProfile.specialtyMatrix]; next[idx] = { ...next[idx], archetype: e.target.value }; setDesignerProfile((p) => p ? { ...p, specialtyMatrix: next, updatedAt: new Date().toISOString() } : p); }} className="border border-slate-200 px-2 py-1 text-xs outline-none focus:border-slate-400">
																					<option value="">选择业态</option>
																					{DSS_ARCHETYPES.map((a) => <option key={a} value={a}>{a}</option>)}
																				</select>
																				<select value={entry.geoType} onChange={(e) => { const next = [...designerProfile.specialtyMatrix]; next[idx] = { ...next[idx], geoType: e.target.value }; setDesignerProfile((p) => p ? { ...p, specialtyMatrix: next, updatedAt: new Date().toISOString() } : p); }} className="border border-slate-200 px-2 py-1 text-xs outline-none focus:border-slate-400">
																					<option value="">选择地理</option>
																					{DSS_GEO_TYPES.map((g) => <option key={g} value={g}>{g}</option>)}
																				</select>
																				<select value={entry.confidenceLevel} onChange={(e) => { const next = [...designerProfile.specialtyMatrix]; next[idx] = { ...next[idx], confidenceLevel: e.target.value as DSSSpecialtyEntry['confidenceLevel'] }; setDesignerProfile((p) => p ? { ...p, specialtyMatrix: next, updatedAt: new Date().toISOString() } : p); }} className="border border-slate-200 px-2 py-1 text-xs outline-none focus:border-slate-400">
																					<option value="done">真做过</option>
																					<option value="familiar">熟悉</option>
																					<option value="heard_of">听说过</option>
																				</select>
																				<input type="number" min={0} max={99} value={entry.projectCount} onChange={(e) => { const next = [...designerProfile.specialtyMatrix]; next[idx] = { ...next[idx], projectCount: Number(e.target.value) || 0 }; setDesignerProfile((p) => p ? { ...p, specialtyMatrix: next, updatedAt: new Date().toISOString() } : p); }} className="w-12 border border-slate-200 px-2 py-1 text-xs outline-none text-center" title="项目数" />
																				<button onClick={() => { const next = designerProfile.specialtyMatrix.filter((_, i) => i !== idx); setDesignerProfile((p) => p ? { ...p, specialtyMatrix: next, updatedAt: new Date().toISOString() } : p); }} className="text-xs text-rose-400 hover:text-rose-600 px-1">✕</button>
																			</div>
																		))}
																	</div>
																)}
															</div>

															<div className="border-t border-slate-100 pt-3">
																<p className="text-xs text-slate-400">
																	画像数据默认私有，仅用于 AI 上下文注入。证据来源：{designerProfile.evidenceCount} 条 · 数据源：{designerProfile.dataSource === 'manual' ? '手动填写' : designerProfile.dataSource === 'auto_extracted' ? '自动提取' : '混合'}
																</p>
															</div>
														</div>
													</details>
												</>
											);
										})() : (
											<div className="p-6 space-y-4">
												<h4 className="ui-type-subtitle font-semibold text-slate-900">设计师画像</h4>
												<p className="text-sm text-slate-600">创建你的设计师画像，让「方案高参」在每次项目中更懂你的判断习惯与专业优势。</p>
												<p className="text-xs text-slate-400">画像数据默认私有，仅用于项目上下文注入，不会公开展示。</p>
												<button
													onClick={() => {
														const now = new Date().toISOString();
														setDesignerProfile({
															id: `dss-${Date.now()}`,
															displayName: '',
															yearsOfExperience: 0,
															city: '',
															teamSize: '独立',
															companyType: '独立设计师',
															specialtyMatrix: [],
															perspectiveWeights: {
																aesthetic: 5,
																functional: 5,
																operational: 3,
																cost: 3,
																risk: 3,
																cultural: 4,
																temporal: 3,
															},
															nineDimSensitivity: {
																people: 5, place: 4, space: 6, function: 6,
																flow: 5, emotion: 5, culture: 3, constraint: 3, time: 3,
															},
															decisionStyle: {
																primaryApproach: '',
																riskTolerance: 'moderate',
															},
															createdAt: now,
															updatedAt: now,
															dataSource: 'manual',
															evidenceCount: 0,
														});
													}}
													className="inline-flex h-9 items-center justify-center rounded-lg border border-sky-200 bg-sky-50 px-4 text-sm font-medium text-sky-700 transition hover:border-sky-300 hover:bg-sky-100"
												>
													开始创建画像
												</button>
											</div>
										)}
									</div>
								</div>
							</div>
						) : null}
					</div>
				);

			case 'insight':
				return (
					<div className="w-full h-full flex flex-col gap-2">
						<KnowledgeGraphCanvas
							className="flex-1"
							onNodeClick={(id, label) => {
								console.log('📊 点击知识图谱节点:', label);
								onNodeClick?.(id, label);
							}}
						/>
					</div>
				);

			case 'geo':
				return <GeoIntelligencePanel />;

			case 'files':
				return (
					<DecisionView
						overview={projectOverview ?? EMPTY_PROJECT_OVERVIEW}
						projectLabel={resolvedProjectLabel}
						onProjectLabelChange={onProjectLabelChange}
						stages={MOCK_STAGES}
						activeView={decisionActiveView}
						onViewChange={setDecisionActiveView}
						onAction={(label) => onCardClick?.(label)}
						onCapabilityClick={(key) => onSwitchModule?.(key)}
						onAdvisorPrefill={(text) => onCardClick?.(text)}
						onSwitchModule={onSwitchModule}
						sessionId={sessionId}
						onOpenGeoWorkspace={onOpenGeoWorkspace}
					/>
				);

			case 'assets':
				return (
					<div className="cockpit-panel-root w-full h-full flex flex-col overflow-hidden bg-slate-50">
						<div className="border-b border-slate-200 bg-white/90 backdrop-blur pl-20 pr-6 py-4">
							<div
								className="flex flex-col gap-3"
								onMouseEnter={() => setAssetHeaderHovered(true)}
								onMouseLeave={() => setAssetHeaderHovered(false)}
							>
								<div className="cockpit-header-row">
									<div className="cockpit-header-main">
										<h3 className="cockpit-panel-title text-slate-800">资源雷达</h3>
										<span className="cockpit-header-note">市场智能匹配</span>
										<button
											onClick={() => setAssetHeaderCollapsed((prev) => !prev)}
											className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition hover:border-slate-300 hover:text-slate-800"
											aria-label={assetHeaderCollapsed ? '持续展开头部功能' : '收起头部功能'}
											title={assetHeaderCollapsed ? '持续展开头部功能' : '收起头部功能'}
										>
											<ChevronDown className={`h-4 w-4 transition-transform ${assetHeaderExpanded ? 'rotate-180' : ''}`} />
										</button>
									</div>
									<div className="flex w-full max-w-[780px] items-center gap-2">
										<input
											value={assetQuery}
											onChange={(e) => setAssetQuery(e.target.value)}
											placeholder="搜索资源（例：替代、客房、防潮、到店体验）"
											className="cockpit-search-input cockpit-header-search"
										/>
										<button
											onClick={() => onOpenInspirationLibrary?.()}
											className="cockpit-card-action shrink-0"
										>
											查看灵感收藏
										</button>
									</div>
								</div>

								<div
									className={`grid overflow-hidden transition-[grid-template-rows,opacity,transform] duration-200 ease-out ${
										assetHeaderExpanded ? 'grid-rows-[1fr] opacity-100 translate-y-0' : 'pointer-events-none grid-rows-[0fr] -translate-y-1 opacity-0'
									}`}
								>
									<div className="space-y-3 overflow-hidden pt-2">
								<div className="flex flex-wrap items-center gap-2">
									{(['替代优先', '空间搭配', '预算压缩', '缺失补全'] as ResourceTaskKey[]).map((task) => (
										<button
											key={task}
											onClick={() => applyAssetTask(task)}
											className={`cockpit-filter-pill ${
												assetTask === task ? 'cockpit-filter-pill-active' : ''
											}`}
										>
											{task}
										</button>
									))}
								</div>

								<div className="flex flex-wrap items-center gap-2">
									<select
										value={assetCategory}
										onChange={(e) => setAssetCategory(e.target.value)}
										aria-label="资源分类筛选"
										className="cockpit-select"
									>
										{ASSET_CATEGORY_OPTIONS.map((category) => (
											<option key={category} value={category}>
												分类：{category}
											</option>
										))}
									</select>
									<select
										value={assetSpace}
										onChange={(e) => setAssetSpace(e.target.value)}
										aria-label="适用空间筛选"
										className="cockpit-select"
									>
										{ASSET_SPACE_OPTIONS.map((space) => (
											<option key={space} value={space}>
												空间：{space}
											</option>
										))}
									</select>
									<select
										value={assetBudget}
										onChange={(e) => setAssetBudget(e.target.value)}
										aria-label="预算带筛选"
										className="cockpit-select"
									>
										{ASSET_BUDGET_OPTIONS.map((budget) => (
											<option key={budget} value={budget}>
												预算：{budget}
											</option>
										))}
									</select>
								</div>
									</div>
								</div>
							</div>
						</div>

						<div className="flex-1 min-h-0 overflow-y-auto pl-20 pr-6 py-6">
							<input
								ref={inspirationUploadInputRef}
								type="file"
								accept="image/*"
								className="hidden"
								onChange={handleInspirationUploadChange}
							/>
							<div className="space-y-4">
								<div className="flex items-center justify-between">
									<h4 className="ui-type-subtitle font-semibold text-slate-700">推荐资源</h4>
									<span className="ui-type-meta text-slate-400">{filteredAssets.length} 条</span>
								</div>

								{filteredAssets.length === 0 ? (
								<div className="cockpit-empty p-6">
										暂无匹配资源，试试放宽预算或切换任务入口。
									</div>
								) : (
									<div className="cockpit-masonry-grid cockpit-masonry-gallery">
										{filteredAssets.map((item) => {
											const selected = item.id === selectedAssetId;
											return (
												<div key={item.id} className="cockpit-masonry-item">
													<button
														onClick={() => openAssetDetail(item.id)}
														className={`cockpit-card cockpit-card-interactive cockpit-card-accent-assets cockpit-asset-card group block w-full overflow-hidden text-left ${
														selected ? 'cockpit-card-selected' : ''
														}`}
														data-expanded={selected ? 'true' : 'false'}
													>
													<div className="relative overflow-hidden">
														<img
															src={item.coverImageSrc}
															alt={item.title}
															className="block h-auto w-full transition-[filter] duration-300 group-hover:brightness-[0.76]"
															loading="lazy"
															data-fallback-src={item.fallbackImageSrc}
															onError={handleResourceImageError}
														/>
														<div className={`absolute inset-0 z-[2] ${assetHoverTone()} opacity-0 transition-opacity duration-300 group-hover:opacity-100`} />
														<div className="absolute inset-x-0 top-0 z-[3] p-4 opacity-0 transition-opacity duration-300 group-hover:opacity-100 pointer-events-none">
															<div className="w-full text-white">
																<div className="cockpit-card-title line-clamp-3 max-w-[85%] text-white">{item.desc}</div>
																<div className="mt-3 flex flex-wrap gap-1.5">
																	<span className="cockpit-asset-pill">{item.category}</span>
																	<span className="cockpit-asset-pill">{item.space}</span>
																	<span className="cockpit-asset-pill">预算 {item.budgetBand}</span>
																	<span className="cockpit-asset-pill">交期 {item.leadTimeDays} 天</span>
																	<span className="cockpit-asset-pill">风险 {item.risk}</span>
																</div>
															</div>
														</div>
													</div>
													<div className="px-4 pb-4 pt-3">
														<div className="cockpit-card-title line-clamp-2 text-slate-900">{item.title}</div>
														<div className="mt-2 flex items-center justify-between gap-3 text-[12px] text-slate-500">
																<div className="min-w-0 truncate text-slate-700">
																	{item.sourceName ?? (item.sourceType === 'user' ? '用户贡献' : '设计知外')}
																</div>
															<div className="shrink-0 flex items-center gap-3 text-slate-500">
																<span className="inline-flex items-center gap-1"><ThumbsUp className="h-3.5 w-3.5" />{item.recommendCount ?? 0}</span>
																<span className="inline-flex items-center gap-1"><Eye className="h-3.5 w-3.5" />{item.favoriteQuoteCount ?? 0}</span>
																<span className="inline-flex items-center gap-1"><Link2 className="h-3.5 w-3.5" />{item.quoteCount ?? 0}</span>
															</div>
														</div>
													</div>
													</button>
												</div>
											);
										})}
									</div>
								)}

								{isClient && assetDetailOpen && selectedAsset && createPortal(
									<div
										ref={assetDetailOverlayRef}
										className="cockpit-readable-overlay z-[2147483647]"
										onClick={closeAssetDetail}
									>
									<div
										onClick={(e) => e.stopPropagation()}
										className="cockpit-readable-overlay-shell"
									>
										<button
											onClick={closeAssetDetail}
											className="cockpit-readable-overlay-close"
											aria-label="关闭详情"
										>
											<X className="h-5 w-5" />
										</button>

										<div className="flex min-h-screen flex-col">
											<div className="bg-[#161616] px-6 py-5 text-white lg:px-10">
												<div className="cockpit-modal-readable mx-auto pr-14" style={assetDetailReadableGroupStyle}>
													<div className="ui-type-meta text-white/55">资源雷达 · 连续阅览详情</div>
													<div className="mt-2 flex flex-wrap items-end gap-x-4 gap-y-2">
														<h4 className="text-[30px] font-semibold tracking-[-0.03em] text-white">{selectedAsset.title}</h4>
														<div className="text-sm text-white/55">{selectedAsset.brand} · {selectedAsset.series}</div>
													</div>
													<p className="ui-type-body mt-3 max-w-3xl text-white/72">
														{selectedAsset.desc} 现在改成纵向滚动阅览，滚动到哪一张，左上角操作就作用于当前图。
													</p>
												</div>
											</div>

											<div className="flex-1">
													<div className="cockpit-modal-readable mx-auto flex w-full flex-col gap-8 px-0 pb-12 pt-8 lg:pb-16" style={assetDetailReadableGroupStyle}>
													<div className="grid gap-4 bg-white px-5 py-5 text-slate-700 lg:grid-cols-[minmax(0,1fr)_220px] lg:px-6 lg:py-6">
														<div>
															<div className="ui-type-meta text-slate-500">阅读提示</div>
															<p className="ui-type-body mt-2 text-slate-600">
																共 {selectedAsset.imageSeries.length} 张图，适合像看 Behance 项目一样连续下滚浏览。
																{selectedDetailImage ? ` 当前焦点：${selectedDetailImage.name}。` : ''}
															</p>
														</div>
													<div className="flex flex-wrap content-start gap-2 text-[11px] text-slate-600 lg:justify-end">
															<span className="cockpit-card-chip">品牌 {selectedAsset.brand}</span>
															<span className="cockpit-card-chip">系列 {selectedAsset.series}</span>
															<span className="cockpit-card-chip">分类 {selectedAsset.category}</span>
															<span className="cockpit-card-chip">预算 {selectedAsset.budgetBand}</span>
															<span className="cockpit-card-chip">交期 {selectedAsset.leadTimeDays} 天</span>
															<button
																onClick={() => setAssetAnchorEditMode((prev) => !prev)}
																className={assetAnchorEditMode ? 'cockpit-modal-action-active' : 'cockpit-modal-action'}
															>
																管理员锚点编辑
															</button>
															{assetAnchorEditMode && (
																<>
																	<button onClick={addResourceAnchor} className="cockpit-modal-action">新增锚点</button>
																	<button onClick={saveResourceAnchors} className={resourceAnchorDirty ? 'cockpit-modal-action-active' : 'cockpit-modal-action'}>保存锚点</button>
																	<button onClick={resetCurrentImageAnchors} className="cockpit-modal-action">重置本图</button>
																</>
															)}
														</div>
													</div>

													{detailArticleSections.map((section, index) => {
														const image = section.image;
														const isCurrent = image.id === selectedDetailImageId;
														return (
															<section
																key={image.id}
																ref={(node) => {
																	assetDetailImageSectionRefs.current[image.id] = node;
																}}
																className={`relative border-y bg-white transition ${
																	isCurrent ? 'border-slate-900/16' : 'border-black/8'
																}`}
															>
																<div className="bg-[#ece5d8] px-0 pb-0 pt-0">
																	<div
																		ref={(node) => {
																			assetDetailImageContainerRefs.current[image.id] = node;
																		}}
																		className={`relative ${assetAnchorEditMode ? 'cursor-crosshair' : ''}`}
																		onClick={(event) => {
																			if (!assetAnchorEditMode) return;
																			const target = event.target;
																			if (target instanceof HTMLElement && target.closest('.cockpit-image-anchor')) return;
																			if (!selectedAsset) return;
																			const rect = event.currentTarget.getBoundingClientRect();
																			const nextX = Math.min(0.96, Math.max(0.04, (event.clientX - rect.left) / rect.width));
																			const nextY = Math.min(0.96, Math.max(0.04, (event.clientY - rect.top) / rect.height));
																			createResourceAnchorAtPosition(
																				image,
																				selectedAsset,
																				Number(nextX.toFixed(4)),
																				Number(nextY.toFixed(4))
																			);
																		}}
																	>
																		<img
																			src={image.src}
																			alt={image.name}
																			className="w-full bg-[#f7f3ec] object-contain"
																			data-fallback-src={image.fallbackSrc}
																			onError={handleResourceImageError}
																		/>
																		{(activeResourceAnchorsByImageId[image.id] ?? []).map((anchor) => {
																			const active = anchor.id === selectedDetailAnchor?.id;
																			return (
																					<button
																						key={anchor.id}
																						type="button"
																						onClick={() => {
																							toggleAssetDetailAnchorPresentation(image.id, anchor.id);
																						}}
																					onMouseDown={(event) => {
																						if (!assetAnchorEditMode) return;
																						event.preventDefault();
																						event.stopPropagation();
																						setDraggingAnchorState({ imageId: image.id, anchorId: anchor.id });
																					}}
																					className={`cockpit-image-anchor ${active ? 'is-active cockpit-image-anchor-selected' : ''}`}
																					style={{ left: `${anchor.x * 100}%`, top: `${anchor.y * 100}%` }}
																					aria-label={`查看锚点：${anchor.title}`}
																				>
																					<span className="cockpit-image-anchor-dot" />
																					{!active && (
																						<span className="cockpit-image-anchor-card">
																							<span className="cockpit-image-anchor-card-type">{anchor.type}</span>
																							<span className="cockpit-image-anchor-card-title">{anchor.title}</span>
																							<span className="cockpit-image-anchor-card-summary">{anchor.summary}</span>
																						</span>
																					)}
																				</button>
																			);
																		})}
																		{isCurrent && selectedDetailAnchor && (
																			<div
																				ref={(node) => {
																					assetDetailAnchorPanelRef.current = node;
																				}}
																				className="cockpit-image-anchor-panel"
																				style={{
																					...assetDetailAnchorPanelStyle,
																					width: assetDetailAnchorPanelMode === 'compact' ? 'min(320px, calc(100% - 28px))' : 'min(440px, calc(100% - 28px))',
																				}}
																				onClick={(event) => event.stopPropagation()}
																			>
																				<div className="flex items-start justify-between gap-3">
																					<div className="min-w-0">
																						<div className="cockpit-image-anchor-panel-title">{selectedDetailAnchor.title}</div>
																					</div>
																					<div className="flex shrink-0 flex-wrap gap-2">
																						<button
																							onClick={() => openInspirationModalFromResource(selectedAsset, image, selectedDetailAnchor)}
																							className="cockpit-unified-pill"
																						>
																							收藏这个点
																						</button>
																						<button
																							onClick={() => toggleAssetBasketSelection(selectedAsset, image, selectedDetailAnchor)}
																							className="cockpit-unified-pill"
																						>
																							加入方案
																						</button>
																					</div>
																				</div>
																				<p className="cockpit-image-anchor-panel-summary">{selectedDetailAnchor.summary}</p>
																				<div className="mt-3 flex flex-wrap gap-2">
																					<span className="cockpit-chip-anchor">{selectedDetailAnchor.anchorMode === 'relation' ? '关系点' : '对象点'}</span>
																					<span className="cockpit-card-chip">证据 {selectedDetailAnchor.evidenceLevel === 'strong' ? '强' : selectedDetailAnchor.evidenceLevel === 'medium' ? '中' : '弱'}</span>
																					{selectedDetailAnchor.tags.slice(0, assetDetailAnchorPanelMode === 'compact' ? 3 : selectedDetailAnchor.tags.length).map((tag) => (
																						<span key={`${selectedDetailAnchor.id}-${tag}`} className="cockpit-card-chip">
																							#{tag}
																						</span>
																					))}
																				</div>
																				<p className="ui-type-meta mt-3 text-slate-500">引用建议：{selectedDetailAnchor.quotedReason}</p>
																				{assetDetailAnchorPanelMode === 'expanded' && (selectedDetailAnchor.insights?.length ?? 0) > 0 && (
																					<div className="mt-4 space-y-3">
																						<div className="ui-type-meta text-slate-500">锚点解读</div>
																						{(selectedDetailAnchor.insights ?? []).map((insight) => (
																							<div key={insight.id} className="rounded-2xl border border-slate-200 bg-slate-50/90 p-3">
																								<div className="flex items-start justify-between gap-3">
																									<div className="min-w-0">
																										<div className="flex flex-wrap gap-2">
																											<span className="cockpit-card-chip">{insight.type === 'observation' ? '观察' : insight.type === 'action' ? '动作' : '风险'}</span>
																											<span className="cockpit-card-chip">证据 {insight.evidenceLevel === 'strong' ? '强' : insight.evidenceLevel === 'medium' ? '中' : '弱'}</span>
																										</div>
																										<div className="mt-2 text-sm font-semibold text-slate-900">{insight.title}</div>
																									</div>
																									<button
																										onClick={() => openInspirationModalFromResource(selectedAsset, image, selectedDetailAnchor, insight)}
																										className="cockpit-unified-pill shrink-0"
																									>
																										收藏解读
																									</button>
																								</div>
																								<p className="mt-2 text-sm text-slate-600">{insight.summary}</p>
																								{insight.actionHint && <p className="ui-type-meta mt-2 text-slate-500">执行建议：{insight.actionHint}</p>}
																								{insight.riskHint && <p className="ui-type-meta mt-1 text-slate-500">风险提醒：{insight.riskHint}</p>}
																							</div>
																						))}
																					</div>
																				)}
																				{assetAnchorEditMode && (
																					<div className="mt-4 grid gap-3 md:grid-cols-2">
																						<label className="block">
																							<div className="ui-type-meta mb-1 text-slate-500">标题</div>
																							<input
																								value={selectedDetailAnchor.title}
																								onChange={(e) => updateResourceAnchor(image.id, selectedDetailAnchor.id, { title: e.target.value })}
																								className="cockpit-search-input"
																							/>
																						</label>
																						<label className="block">
																							<div className="ui-type-meta mb-1 text-slate-500">类型</div>
																							<select
																								value={selectedDetailAnchor.type}
																								onChange={(e) => updateResourceAnchor(image.id, selectedDetailAnchor.id, { type: e.target.value as ResourceAnchorType })}
																								className="cockpit-select"
																							>
																								{(['产品点', '材料点', '体验点', '氛围点', '运营点'] as ResourceAnchorType[]).map((type) => (
																									<option key={type} value={type}>{type}</option>
																								))}
																							</select>
																						</label>
																						<label className="block md:col-span-2">
																							<div className="ui-type-meta mb-1 text-slate-500">摘要</div>
																							<textarea
																								value={selectedDetailAnchor.summary}
																								onChange={(e) => updateResourceAnchor(image.id, selectedDetailAnchor.id, { summary: e.target.value })}
																								className="min-h-[88px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-sky-400"
																							/>
																						</label>
																						<label className="block">
																							<div className="ui-type-meta mb-1 text-slate-500">专题</div>
																							<input
																								value={selectedDetailAnchor.topic}
																								onChange={(e) => updateResourceAnchor(image.id, selectedDetailAnchor.id, { topic: e.target.value })}
																								className="cockpit-search-input"
																							/>
																						</label>
																						<label className="block">
																							<div className="ui-type-meta mb-1 text-slate-500">标签</div>
																							<input
																								value={selectedDetailAnchor.tags.join(', ')}
																								onChange={(e) =>
																									updateResourceAnchor(image.id, selectedDetailAnchor.id, {
																										tags: e.target.value.split(/[，,\n]/).map((tag) => tag.trim()).filter(Boolean).slice(0, 8),
																									})
																								}
																								className="cockpit-search-input"
																							/>
																						</label>
																						<label className="block md:col-span-2">
																							<div className="ui-type-meta mb-1 text-slate-500">引用建议</div>
																							<textarea
																								value={selectedDetailAnchor.quotedReason}
																								onChange={(e) => updateResourceAnchor(image.id, selectedDetailAnchor.id, { quotedReason: e.target.value })}
																								className="min-h-[72px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-sky-400"
																							/>
																						</label>
																						<div className="md:col-span-2 flex justify-end">
																							<button
																								onClick={() => removeResourceAnchor(image.id, selectedDetailAnchor.id)}
																								className="cockpit-card-action text-rose-600 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700"
																							>
																								删除锚点
																							</button>
																						</div>
																					</div>
																				)}
																			</div>
																		)}
																	</div>
																</div>

																<div className="px-5 pb-6 pt-5 lg:px-6">
																	<div className="space-y-4">
																		<div className="flex flex-wrap gap-2">
																			<button
																				onClick={() => onCardClick?.(`${selectedAsset.title} · ${image.name}`)}
																				className="cockpit-unified-pill"
																			>
																				引用
																			</button>
																			<button
																				onClick={() => openInspirationModalFromResource(selectedAsset, image)}
																				className="cockpit-unified-pill"
																			>
																				灵感收藏
																			</button>
																			<button
																				onClick={() => toggleAssetBasketSelection(selectedAsset, image)}
																				className="cockpit-unified-pill"
																			>
																				加入方案
																			</button>
																			<button
																				onClick={() => openBoardCollectionModal(selectedAsset, image)}
																				className="cockpit-unified-pill"
																			>
																				方案画布
																			</button>
																		</div>

																		<div className="space-y-3">
																		<div className="ui-type-meta text-slate-500">{section.eyebrow}</div>
																		<h5 className="text-[24px] font-semibold tracking-[-0.03em] text-slate-900">{section.title}</h5>
																		<p className="ui-type-body text-slate-600">{section.body}</p>
																		<p className="ui-type-meta text-slate-500">{section.caption}</p>
																		</div>
																	</div>
																</div>
															</section>
														);
													})}

													<section className="bg-[#171717] px-5 py-6 text-white lg:px-6">
														<div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
															<div className="ui-type-subtitle font-semibold text-white">相近资源</div>
															<div className="flex items-center gap-3">
																<div className="text-sm text-white/50">
																	{relatedAssets.length === 0
																		? '暂无相近条目'
																		: `${Math.min(relatedAssetsOffset + 1, relatedAssets.length)}-${Math.min(relatedAssetsOffset + RELATED_ASSETS_PAGE_SIZE, relatedAssets.length)} / ${relatedAssets.length}`}
																</div>
																{relatedAssets.length > RELATED_ASSETS_PAGE_SIZE && (
																	<div className="flex items-center gap-2">
																		<button
																			onClick={showPreviousRelatedAssets}
																			disabled={!canShowPreviousRelatedAssets}
																			className="cockpit-unified-pill-icon"
																			aria-label="查看上一组相近资源"
																		>
																			<ChevronLeft className="h-[14px] w-[14px]" />
																		</button>
																		<button
																			onClick={showNextRelatedAssets}
																			disabled={!canShowNextRelatedAssets}
																			className="cockpit-unified-pill-icon"
																			aria-label="查看下一组相近资源"
																		>
																			<ChevronRight className="h-[14px] w-[14px]" />
																		</button>
																	</div>
																)}
															</div>
														</div>
														<div
															className="cockpit-related-assets-viewport mt-5 overflow-hidden"
														>
															<div
																className="cockpit-related-assets-track"
																style={{ transform: `translateX(-${relatedAssetsPageIndex * 100}%)` }}
															>
																{relatedAssetPages.map((pageItems, pageIndex) => (
																	<div
																		key={`related-page-${pageIndex}`}
																		className="cockpit-related-assets-page grid gap-4 md:grid-cols-2 xl:grid-cols-4"
																	>
																		{pageItems.map((item) => (
																<button
																	key={`related-${item.id}`}
																	onClick={() => {
																		setSelectedAssetId(item.id);
																		setSelectedDetailImageId('');
																	}}
																	className="cockpit-related-assets-card overflow-hidden border border-white/10 bg-white/6 text-left transition hover:border-white/25 hover:bg-white/10"
																>
																	<img
																		src={item.coverImageSrc}
																		alt={item.title}
																		className="h-44 w-full object-cover"
																		data-fallback-src={item.fallbackImageSrc}
																		onError={handleResourceImageError}
																	/>
																	<div className="space-y-2 px-4 py-4">
																		<div className="text-sm font-semibold text-white">{item.title}</div>
																		<div className="text-xs text-white/55">{item.brand} · {item.series}</div>
																		<div className="line-clamp-2 text-xs text-white/62">{item.desc}</div>
																	</div>
																</button>
																		))}
																	</div>
																))}
															</div>
														</div>
													</section>

													<div className="grid gap-6 lg:grid-cols-[minmax(0,1.3fr)_minmax(280px,0.7fr)]">
														<section className="border border-black/6 bg-white px-5 py-6 lg:px-6">
															<div className="border-b border-slate-200 pb-6">
																<div className="flex gap-4">
																	<div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-fuchsia-500 via-amber-300 to-violet-500 text-lg text-white shadow-sm">
																		✎
																	</div>
																	<div className="min-w-0 flex-1">
																		<div className="rounded-sm border border-slate-300 bg-white px-4 py-3 text-base text-slate-400">
																			您对此项目有什么看法?
																		</div>
																		<div className="mt-4 flex justify-end">
																			<button className="cockpit-unified-pill" disabled>
																				发表评论
																			</button>
																		</div>
																	</div>
																</div>
															</div>
															<div className="mt-2 space-y-0">
																{detailDiscussionEntries.map((entry) => (
																	<div key={entry.id} className="flex gap-4 border-b border-slate-200 py-7 last:border-b-0">
																		<div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-gradient-to-br ${entry.avatarTone} text-sm font-semibold text-white`}>
																			{entry.author.slice(0, 1)}
																		</div>
																		<div className="min-w-0 flex-1">
																			<div className="flex flex-wrap items-center gap-1 text-sm">
																				<span className="font-semibold text-slate-900">{entry.author}</span>
																				<span className="text-slate-400">· {entry.date}</span>
																				<span className="text-slate-400">· {entry.replyLabel ?? '回复'}</span>
																			</div>
																			<p className="mt-2 max-w-3xl text-[15px] leading-8 text-slate-700">{entry.content}</p>
																		</div>
																	</div>
																))}
															</div>
														</section>

														<section className="border border-black/6 bg-white px-5 py-6 lg:px-6">
															<div className="ui-type-meta text-slate-500">品牌 / 作者</div>
															<h5 className="mt-2 text-[28px] font-semibold tracking-[-0.03em] text-slate-900">{selectedAsset.brand}</h5>
															<div className="mt-4 space-y-4 text-sm text-slate-600">
																<p>{selectedAsset.brand} 当前被归档为 {selectedAsset.category} 方向资源，系列名为 {selectedAsset.series}，适合在 {selectedAsset.space === '全局' ? '全局策略' : `${selectedAsset.space}方案`} 中做连续参考。</p>
																<div className="bg-slate-50 px-4 py-4">
																	<div className="ui-type-meta text-slate-400">项目信息</div>
																	<div className="mt-3 space-y-2">
																		<div>风险等级：{selectedAsset.risk}</div>
																		<div>交付周期：{selectedAsset.leadTimeDays} 天</div>
																		<div>标签：{selectedAsset.tags.join(' / ')}</div>
																		<div>当前系列图数：{selectedAsset.imageSeries.length}</div>
																	</div>
																</div>
																<div className="bg-slate-900 px-4 py-4 text-slate-100">
																	<div className="ui-type-meta text-white/45">当前阅读焦点</div>
																	<div className="mt-2 text-sm leading-7 text-white/82">
																		{selectedDetailImage ? `${selectedDetailImage.name} 正在作为当前操作对象。` : '滚动到任意图片即可切换当前操作对象。'}
																	</div>
																</div>
															</div>
														</section>
													</div>
												</div>
											</div>
										</div>
									</div>
									{selectedDetailImage && assetDetailAnchorRailVisible && (
										<div
											className="pointer-events-none fixed z-[2147483647] hidden w-[280px] xl:block"
											style={assetDetailAnchorRailStyle}
										>
											<div className="pointer-events-auto space-y-3 overflow-y-auto pr-2 text-white/88" style={{ maxHeight: assetDetailAnchorRailStyle.maxHeight }}>
												{selectedDetailAnchors.length === 0 ? (
													<div className="text-xs leading-6 text-white/35">当前图片还没有锚点。</div>
												) : (
													<div className="space-y-4">
														{selectedDetailAnchors.map((anchor, anchorIndex) => (
															<button
																type="button"
																key={`${selectedDetailImage.id}-anchor-external-${anchor.id}`}
																onClick={(event) => {
																	event.preventDefault();
																	event.stopPropagation();
																	toggleAssetDetailAnchorPresentation(selectedDetailImage.id, anchor.id);
																}}
																className={`block w-full border-l pl-4 text-left transition ${
																	selectedDetailAnchorId === anchor.id
																		? 'border-sky-400 text-white'
																		: 'border-white/18 text-white/72 hover:border-sky-300 hover:text-white'
																}`}
															>
																<div className="flex items-center gap-2">
																	<span className="ui-type-meta text-white/35">{String(anchorIndex + 1).padStart(2, '0')}</span>
																	<span className="text-sm font-medium">{anchor.title}</span>
																</div>
																<div className="mt-1 flex flex-wrap gap-2 text-[11px] text-white/35">
																	<span>{anchor.type}</span>
																	<span>{anchor.topic}</span>
																</div>
																<div className="mt-1 line-clamp-2 text-xs leading-5 text-white/52">{anchor.summary}</div>
															</button>
														))}
													</div>
												)}
											</div>
										</div>
									)}
									</div>,
									document.body
								)}

									{isClient && inspirationModalOpen && inspirationDraft && createPortal(
										<div
											className="cockpit-shared-overlay z-[2147483648] flex items-center justify-center p-6 backdrop-blur-sm"
											onClick={closeInspirationModal}
										>
											<div
												onClick={(e) => e.stopPropagation()}
												className="cockpit-modal-shell cockpit-modal-width cockpit-modal-split-preview"
											>
												<div className="cockpit-modal-side border-b p-5 lg:border-b-0 lg:border-r">
													<div className="sticky top-0 space-y-4">
														<div className="ui-type-meta font-medium uppercase tracking-[0.2em] text-slate-500">灵感预览</div>
														<div
															className="relative"
															onClick={(event) => {
																if (inspirationDraft.itemType !== 'anchor' && inspirationDraft.itemType !== 'insight') return;
																const rect = event.currentTarget.getBoundingClientRect();
																const nextX = Math.min(0.96, Math.max(0.04, (event.clientX - rect.left) / rect.width));
																const nextY = Math.min(0.96, Math.max(0.04, (event.clientY - rect.top) / rect.height));
																setInspirationDraft((prev) =>
																	prev
																		? {
																				...prev,
																				anchorX: Number(nextX.toFixed(4)),
																				anchorY: Number(nextY.toFixed(4)),
																		  }
																		: prev
																);
															}}
														>
															<img
																src={inspirationDraft.imageSrc}
																alt={inspirationDraft.title}
																className={`h-72 w-full rounded-none object-cover ${inspirationDraft.itemType === 'anchor' || inspirationDraft.itemType === 'insight' ? 'cursor-crosshair' : ''}`}
																data-fallback-src={inspirationDraft.fallbackImageSrc}
																onError={handleResourceImageError}
															/>
															{(inspirationDraft.itemType === 'anchor' || inspirationDraft.itemType === 'insight') && inspirationDraft.anchorX !== undefined && inspirationDraft.anchorY !== undefined && (
																<div
																	className="cockpit-image-anchor is-active"
																	style={{ left: `${inspirationDraft.anchorX * 100}%`, top: `${inspirationDraft.anchorY * 100}%` }}
																>
																	<span className="cockpit-image-anchor-dot" />
																</div>
															)}
														</div>
														<div className="cockpit-modal-card">
															<div className="ui-type-subtitle font-semibold text-slate-900">{inspirationDraft.title || '未命名灵感'}</div>
															<div className="ui-type-meta mt-1 text-slate-500">{inspirationDraft.sourceLabel}</div>
															{(inspirationDraft.itemType === 'anchor' || inspirationDraft.itemType === 'insight') && (
																<div className="ui-type-meta mt-2 text-slate-500">
																	{inspirationDraft.itemType === 'insight' ? '锚点解读' : '锚点颗粒'} · {inspirationDraft.anchorType} · {inspirationDraft.anchorOrigin === 'derived' ? '派生自系统锚点' : inspirationDraft.anchorOrigin === 'user' ? '自定义锚点' : inspirationDraft.resourceTitle}
																</div>
															)}
														</div>
														<div className="flex flex-wrap gap-2 text-[11px] text-slate-500">
															<span className="cockpit-card-chip">{inspirationDraft.source === 'market' ? '来源 资源雷达' : '来源 本地上传'}</span>
															{(inspirationDraft.itemType === 'anchor' || inspirationDraft.itemType === 'insight') && inspirationDraft.anchorType && <span className="cockpit-card-chip">{inspirationDraft.anchorType}</span>}
															{inspirationDraft.itemType === 'insight' && inspirationDraft.insightType && <span className="cockpit-card-chip">{inspirationDraft.insightType}</span>}
															{inspirationDraft.evidenceLevel && <span className="cockpit-card-chip">证据 {inspirationDraft.evidenceLevel === 'strong' ? '强' : inspirationDraft.evidenceLevel === 'medium' ? '中' : '弱'}</span>}
															<span className="cockpit-card-chip">跨项目可复用</span>
														</div>
													</div>
												</div>

												<div className="cockpit-modal-side max-h-[80vh] overflow-y-auto p-6">
													<div className="mb-6 flex items-start justify-between gap-4">
														<div>
															<div className="ui-type-meta font-medium uppercase tracking-[0.2em] text-emerald-600">灵感仓库</div>
															<h4 className="ui-type-title mt-2 font-semibold text-slate-900">保存这张可复用灵感</h4>
															<p className="ui-type-body mt-2 text-slate-500">支持自由分类、标签整理和跨项目长期复用。</p>
														</div>
														<button
															onClick={closeInspirationModal}
															className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition hover:border-slate-300 hover:text-slate-800"
															aria-label="关闭灵感仓库弹窗"
														>
															<X className="h-5 w-5" />
														</button>
													</div>

													<div className="space-y-5">
														<div className="flex flex-wrap gap-2">
															{inspirationDraft.itemType !== 'anchor' ? (
																<button onClick={createCustomAnchorFromDraft} className="cockpit-modal-action">
																	新增我的锚点
																</button>
															) : inspirationDraft.anchorOrigin === 'system' ? (
																<button onClick={createCustomAnchorFromDraft} className="cockpit-modal-action">
																	复制为我的锚点
																</button>
															) : null}
														</div>
														<label className="block">
															<div className="ui-type-meta mb-2 text-slate-500">标题</div>
															<input
																value={inspirationDraft.title}
																onChange={(e) => setInspirationDraft((prev) => (prev ? { ...prev, title: e.target.value } : prev))}
																placeholder="为这张灵感命名"
																className="cockpit-search-input"
															/>
														</label>

														<div className="grid gap-4 md:grid-cols-2">
															<label className="block">
																<div className="ui-type-meta mb-2 text-slate-500">自定义分类</div>
																<input
																	value={inspirationDraft.category}
																	onChange={(e) => setInspirationDraft((prev) => (prev ? { ...prev, category: e.target.value } : prev))}
																	placeholder="例：客房 / 木作 / 日式侘寂"
																	className="cockpit-search-input"
																/>
															</label>
															<label className="block">
																<div className="ui-type-meta mb-2 text-slate-500">标签</div>
																<input
																	value={inspirationDraft.tagsInput}
																	onChange={(e) => setInspirationDraft((prev) => (prev ? { ...prev, tagsInput: e.target.value } : prev))}
																	placeholder="用逗号分隔多个标签"
																className="cockpit-search-input"
															/>
														</label>
															{(inspirationDraft.itemType === 'anchor' || inspirationDraft.itemType === 'insight') && (
																<label className="block">
																	<div className="ui-type-meta mb-2 text-slate-500">锚点类型</div>
																	<select
																		value={inspirationDraft.anchorType ?? '体验点'}
																		onChange={(e) => setInspirationDraft((prev) => (prev ? { ...prev, anchorType: e.target.value as ResourceAnchorType } : prev))}
																		className="cockpit-select"
																	>
																		{(['产品点', '材料点', '体验点', '氛围点', '运营点'] as ResourceAnchorType[]).map((type) => (
																			<option key={type} value={type}>{type}</option>
																		))}
																	</select>
																</label>
															)}
														</div>
														{inspirationDraft.itemType === 'insight' && (
															<div className="grid gap-4 md:grid-cols-2">
																<label className="block">
																	<div className="ui-type-meta mb-2 text-slate-500">解读类型</div>
																	<select
																		value={inspirationDraft.insightType ?? 'observation'}
																		onChange={(e) => setInspirationDraft((prev) => (prev ? { ...prev, insightType: e.target.value as ResourceInsightType } : prev))}
																		className="cockpit-select"
																	>
																		<option value="observation">observation</option>
																		<option value="action">action</option>
																		<option value="risk">risk</option>
																	</select>
																</label>
																<label className="block">
																	<div className="ui-type-meta mb-2 text-slate-500">证据强度</div>
																	<select
																		value={inspirationDraft.evidenceLevel ?? 'medium'}
																		onChange={(e) => setInspirationDraft((prev) => (prev ? { ...prev, evidenceLevel: e.target.value as ResourceEvidenceLevel } : prev))}
																		className="cockpit-select"
																	>
																		<option value="strong">strong</option>
																		<option value="medium">medium</option>
																		<option value="weak">weak</option>
																	</select>
																</label>
															</div>
														)}

														<label className="block">
															<div className="ui-type-meta mb-2 text-slate-500">说明</div>
															<textarea
																value={inspirationDraft.desc}
																onChange={(e) => setInspirationDraft((prev) => (prev ? { ...prev, desc: e.target.value } : prev))}
																placeholder="记录为什么收藏它、适合什么场景、后续如何复用"
																className="min-h-[140px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-sky-400"
															/>
														</label>
														{(inspirationDraft.itemType === 'anchor' || inspirationDraft.itemType === 'insight') && (
															<p className="ui-type-meta text-slate-500">点击左侧预览图可重新定位你的锚点。</p>
														)}
													</div>

													<div className="mt-6 flex flex-wrap items-center justify-between gap-3">
														<div className="flex items-center gap-2">
															<button
																onClick={saveInspirationItem}
																className="inline-flex min-w-[172px] items-center justify-center rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(15,23,42,0.24)] transition hover:bg-slate-800"
															>
																{inspirationDraft.id ? '更新灵感' : '保存到灵感仓库'}
															</button>
														</div>
														{inspirationDraft.id && (
															<button
																onClick={deleteInspirationItem}
																className="cockpit-card-action text-rose-600 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700"
															>
																删除这条灵感
															</button>
														)}
													</div>
												</div>
											</div>
										</div>,
										document.body
									)}

									{isClient && boardCollectModalOpen && boardCollectionDraft && selectedBoardDraftResource && selectedBoardDraftImage && createPortal(
										<div
											className="cockpit-shared-overlay z-[2147483648] flex items-center justify-center p-6 backdrop-blur-sm"
											onClick={closeBoardCollectionModal}
										>
											<div
												onClick={(e) => e.stopPropagation()}
											className="cockpit-modal-shell cockpit-modal-width cockpit-modal-split-preview"
											>
												<div className="cockpit-modal-side border-b p-5 lg:border-b-0 lg:border-r">
													<div className="sticky top-0 space-y-4">
														<div className="ui-type-meta font-medium uppercase tracking-[0.2em] text-slate-500">收藏预览</div>
														<img
															src={selectedBoardDraftImage.src}
															alt={selectedBoardDraftImage.name}
															className="h-64 w-full rounded-none object-cover"
															data-fallback-src={selectedBoardDraftImage.fallbackSrc}
															onError={handleResourceImageError}
														/>
														<div className="cockpit-modal-card">
															<div className="ui-type-subtitle font-semibold text-slate-900">{selectedBoardDraftResource.title}</div>
															<div className="ui-type-meta mt-1 text-slate-500">{selectedBoardDraftImage.name}</div>
														</div>
														<div className="flex flex-wrap gap-2 text-[11px] text-slate-500">
															<span className="cockpit-card-chip">原始空间：{toDisplaySpaceName(selectedBoardDraftResource.space)}</span>
															<span className="cockpit-card-chip">{selectedBoardDraftResource.category}</span>
														</div>
													</div>
												</div>

												<div className="cockpit-modal-side max-h-[80vh] overflow-y-auto p-6">
													<div className="mb-6 flex items-start justify-between gap-4">
														<div>
															<div className="ui-type-meta font-medium uppercase tracking-[0.2em] text-sky-600">方案画布收藏</div>
															<h4 className="ui-type-title mt-2 font-semibold text-slate-900">像 Eagle 一样整理这张图</h4>
															<p className="ui-type-body mt-2 text-slate-500">你可以在收藏时直接改名称、写注释、打标签，并决定它应该落在哪个空间；如果现有空间不够，还能在这里马上新建。</p>
														</div>
														<button
															onClick={closeBoardCollectionModal}
															className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 text-slate-500 hover:border-slate-300 hover:text-slate-700"
															aria-label="关闭收藏弹窗"
														>
															<X className="h-5 w-5" />
														</button>
													</div>

													<div className="space-y-5">
														<div>
															<label className="ui-type-meta mb-2 block font-medium text-slate-800">自定义名称</label>
															<input
																value={boardCollectionDraft.customTitle}
																onChange={(e) => updateBoardCollectionDraft({ customTitle: e.target.value })}
																placeholder="给这张图起一个更适合项目语境的名字"
																className="ui-type-body h-11 w-full rounded-xl border border-slate-200 px-3 text-slate-700 outline-none focus:border-sky-400"
															/>
														</div>

														<div>
															<label className="ui-type-meta mb-2 block font-medium text-slate-800">注释</label>
															<textarea
																value={boardCollectionDraft.note}
																onChange={(e) => updateBoardCollectionDraft({ note: e.target.value })}
																placeholder="例如：适合大堂入口的暖调木质氛围，可作为到店体验第一视觉参考。"
																rows={4}
																className="ui-type-body w-full rounded-xl border border-slate-200 px-3 py-3 text-slate-700 outline-none focus:border-sky-400"
															/>
														</div>

														<div>
															<label className="ui-type-meta mb-2 block font-medium text-slate-800">标签</label>
															<input
																value={boardCollectionDraft.tagsInput}
																onChange={(e) => updateBoardCollectionDraft({ tagsInput: e.target.value })}
																placeholder="用逗号分隔：到店体验, 木色, 低饱和, 入口"
																className="ui-type-body h-11 w-full rounded-xl border border-slate-200 px-3 text-slate-700 outline-none focus:border-sky-400"
															/>
															<div className="mt-2 flex flex-wrap gap-2">
																<span className="cockpit-chip-anchor">构造点</span>
																{boardCollectionDraft.tagsInput
																	.split(/[，,\n]/)
																	.map((tag) => tag.trim())
																	.filter(Boolean)
																	.slice(0, 8)
																	.map((tag) => (
																		<span key={tag} className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] text-slate-600">#{tag}</span>
																	))}
															</div>
														</div>

														<div className="cockpit-modal-card">
															<div className="mb-3 flex items-center justify-between gap-3">
																<div>
																	<div className="ui-type-subtitle font-medium text-slate-800">保存位置</div>
																	<div className="ui-type-meta mt-1 text-slate-500">优先沿用项目底盘里的空间口径；如果不够用，可以现场新建一个空间。</div>
																</div>
																<button
																	onClick={() => updateBoardCollectionDraft({ useCustomSpace: !boardCollectionDraft.useCustomSpace })}
																	className="cockpit-card-action"
																>
																	{boardCollectionDraft.useCustomSpace ? '改回项目空间' : '新建空间'}
																</button>
															</div>

															{boardCollectionDraft.useCustomSpace ? (
																<input
																	value={boardCollectionDraft.newSpace}
																	onChange={(e) => updateBoardCollectionDraft({ newSpace: e.target.value })}
																	placeholder="例如：到店前厅 / SPA 前区 / 会客壁炉角"
																	className="ui-type-body h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-slate-700 outline-none focus:border-sky-400"
																/>
															) : (
																<select
																	value={boardCollectionDraft.space}
																	onChange={(e) => updateBoardCollectionDraft({ space: e.target.value })}
																	className="ui-type-body h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-slate-700 outline-none focus:border-sky-400"
																>
																	{COLLECTION_SPACE_OPTIONS.map((space) => (
																		<option key={`collect-space-${space}`} value={space}>
																			{toDisplaySpaceName(space)}
																		</option>
																	))}
																</select>
															)}
														</div>

														<div className="flex items-center justify-end gap-3 pt-2">
															<button
																onClick={saveBoardCollection}
																className="ui-type-meta rounded-full bg-slate-900 px-5 py-2 font-medium text-white hover:bg-slate-800"
															>
																{isImageCollectedToBoard(boardCollectionDraft.imageId) ? '更新收藏' : '保存到方案画布'}
															</button>
														</div>
													</div>
												</div>
											</div>
										</div>,
										document.body
									)}

							</div>
						</div>
					</div>
				);

			case 'inspiration':
				return (
					<div className="cockpit-panel-root w-full h-full flex flex-col overflow-hidden bg-slate-50">
						<div className="border-b border-slate-200 bg-white/90 backdrop-blur pl-20 pr-6 py-4">
							<div className="flex flex-col gap-3">
								<div className="cockpit-header-row">
									<div className="cockpit-header-main">
										<h3 className="cockpit-panel-title text-slate-800">灵感仓库</h3>
										<span className="cockpit-header-note">跨项目复用素材仓</span>
									</div>
									<div className="flex w-full max-w-[720px] flex-col gap-2 md:flex-row">
										<input
											value={inspirationQuery}
											onChange={(e) => setInspirationQuery(e.target.value)}
											placeholder="搜索灵感仓库（例：客房、木作、到店体验）"
											className="cockpit-search-input flex-1"
										/>
										<select
											value={inspirationCategory}
											onChange={(e) => setInspirationCategory(e.target.value)}
											aria-label="灵感仓库分类筛选"
											className="cockpit-select md:w-[200px]"
										>
											{inspirationCategoryOptions.map((category) => (
												<option key={`inspiration-page-category-${category}`} value={category}>
													分类：{category}
												</option>
											))}
										</select>
										<button
											onClick={() => onBackToAssets?.()}
											className="cockpit-card-action md:min-w-[132px]"
										>
											返回资源雷达
										</button>
									</div>
								</div>

								<div className="grid grid-cols-1 gap-3 md:grid-cols-3">
									<div className="cockpit-stat">
										<div className="cockpit-stat-label">仓库总数</div>
										<div className="cockpit-stat-value">{inspirationLibraryItems.length}</div>
									</div>
									<div className="cockpit-stat">
										<div className="cockpit-stat-label">当前筛选命中</div>
										<div className="cockpit-stat-value">{filteredInspirationLibraryItems.length}</div>
									</div>
									<div className="cockpit-stat">
										<div className="cockpit-stat-label">来源覆盖</div>
										<div className="ui-type-subtitle mt-1 font-semibold text-slate-900">
											{inspirationEntityView} · {inspirationEntityCounts[inspirationEntityView]} 项
										</div>
									</div>
								</div>
								<div className="mt-4 flex flex-wrap gap-2">
									{(['全部条目', '项目包', '单图', '锚点', '解读'] as InspirationEntityView[]).map((view) => {
										const active = inspirationEntityView === view;
										return (
											<button
												key={`inspiration-entity-view-${view}`}
												onClick={() => setInspirationEntityView(view)}
												className={`rounded-full px-4 py-2 text-sm transition ${
													active
														? 'bg-slate-950 text-white shadow-[0_10px_24px_rgba(15,23,42,0.18)]'
														: 'border border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900'
												}`}
											>
												{view} {inspirationEntityCounts[view] > 0 ? `· ${inspirationEntityCounts[view]}` : ''}
											</button>
										);
									})}
								</div>
							</div>
						</div>

						<div className="flex-1 min-h-0 overflow-y-auto pl-20 pr-6 py-6">
							<input
								ref={inspirationUploadInputRef}
								type="file"
								accept="image/*"
								className="hidden"
								onChange={handleInspirationUploadChange}
							/>

							{filteredInspirationLibraryItems.length === 0 ? (
								<div className="cockpit-empty">
									灵感仓库还是空的。先去“资源雷达”做灵感收藏。
								</div>
							) : (
								<div className="space-y-4 pb-4">
									<div className="flex items-center justify-between">
										<h4 className="ui-type-subtitle font-semibold text-slate-700">{inspirationEntityView === '全部条目' ? '仓库内容' : `${inspirationEntityView} 视图`}</h4>
										<span className="ui-type-meta text-slate-400">{filteredInspirationLibraryItems.length} 项</span>
									</div>
									<div className="cockpit-masonry-grid cockpit-masonry-gallery">
										{filteredInspirationLibraryItems.map((item) => (
											<div key={item.id} className="cockpit-masonry-item">
												<button
													onClick={() => openInspirationEditModal(item)}
													className="cockpit-card cockpit-card-interactive cockpit-card-accent-assets cockpit-asset-card group block w-full overflow-hidden text-left"
												>
												<div className="relative overflow-hidden">
													<img
														src={item.imageSrc}
														alt={item.title}
														className="block h-auto w-full transition-[filter] duration-300 group-hover:brightness-[0.76]"
														loading="lazy"
														data-fallback-src={item.fallbackImageSrc}
														onError={handleResourceImageError}
													/>
													<div className={`absolute inset-0 z-[2] ${assetHoverTone()} opacity-0 transition-opacity duration-300 group-hover:opacity-100`} />
													<div className="absolute inset-x-0 bottom-0 z-[3] p-4 text-white">
														<div className="flex flex-wrap gap-1.5">
															<span className="cockpit-asset-pill">
																{item.entityType === 'insight' ? '解读' : item.entityType === 'anchor' ? '锚点' : item.entityType === 'project' ? '项目包' : '单图'}
															</span>
															<span className="cockpit-asset-pill">{item.category}</span>
															<span className="cockpit-asset-pill">{item.sourceLabel}</span>
															{item.itemType === 'anchor' && item.anchorType && <span className="cockpit-asset-pill">{item.anchorType}</span>}
															{item.itemType === 'insight' && item.insightType && <span className="cockpit-asset-pill">{item.insightType}</span>}
														</div>
													</div>
													<div className="absolute inset-x-0 top-0 z-[3] p-4 opacity-0 transition-opacity duration-300 group-hover:opacity-100 pointer-events-none">
														<div className="w-full text-white">
															<div className="cockpit-card-title line-clamp-3 max-w-[88%] text-white">
																{item.desc || '点击后可编辑标题、分类、标签与说明。'}
															</div>
															{item.tags.length > 0 && (
																<div className="mt-3 flex flex-wrap gap-1.5">
																	{item.tags.slice(0, 4).map((tag) => (
																		<span key={`${item.id}-${tag}`} className="cockpit-asset-pill">
																			#{tag}
																		</span>
																	))}
																</div>
															)}
														</div>
													</div>
												</div>
												<div className="px-4 pb-4 pt-3">
													<div className="cockpit-card-title line-clamp-2 text-slate-900">{item.title}</div>
													{(item.itemType === 'anchor' || item.itemType === 'insight') && (
														<div className="mt-2 space-y-1 text-xs text-slate-500">
															<div>{item.resourceTitle ?? '资源雷达'} · {item.imageName ?? '当前图'}</div>
															{item.anchorSummary && <div className="line-clamp-2">{item.anchorSummary}</div>}
															{item.itemType === 'insight' && item.insightSummary && <div className="line-clamp-2">{item.insightSummary}</div>}
														</div>
													)}
												</div>
												</button>
											</div>
										))}
									</div>
								</div>
							)}
						</div>

						{isClient && inspirationModalOpen && inspirationDraft && createPortal(
							<div
								className="cockpit-shared-overlay z-[2147483648] flex items-center justify-center p-6 backdrop-blur-sm"
								onClick={closeInspirationModal}
							>
								<div
									onClick={(e) => e.stopPropagation()}
									className="cockpit-modal-shell cockpit-modal-width cockpit-modal-split-preview"
								>
									<div className="cockpit-modal-side border-b p-5 lg:border-b-0 lg:border-r">
										<div className="sticky top-0 space-y-4">
											<div className="ui-type-meta font-medium uppercase tracking-[0.2em] text-slate-500">灵感预览</div>
											<img
												src={inspirationDraft.imageSrc}
												alt={inspirationDraft.title}
												className="h-72 w-full rounded-none object-cover"
												data-fallback-src={inspirationDraft.fallbackImageSrc}
												onError={handleResourceImageError}
											/>
											<div className="cockpit-modal-card">
												<div className="ui-type-subtitle font-semibold text-slate-900">{inspirationDraft.title || '未命名灵感'}</div>
												<div className="ui-type-meta mt-1 text-slate-500">{inspirationDraft.sourceLabel}</div>
											</div>
											<div className="flex flex-wrap gap-2 text-[11px] text-slate-500">
												<span className="cockpit-card-chip">{inspirationDraft.source === 'market' ? '来源 资源雷达' : '来源 本地上传'}</span>
												<span className="cockpit-card-chip">跨项目可复用</span>
											</div>
										</div>
									</div>

									<div className="cockpit-modal-side max-h-[80vh] overflow-y-auto p-6">
										<div className="mb-6 flex items-start justify-between gap-4">
											<div>
												<div className="ui-type-meta font-medium uppercase tracking-[0.2em] text-emerald-600">灵感仓库</div>
												<h4 className="ui-type-title mt-2 font-semibold text-slate-900">保存这张可复用灵感</h4>
												<p className="ui-type-body mt-2 text-slate-500">支持自由分类、标签整理和跨项目长期复用。</p>
											</div>
											<button
												onClick={closeInspirationModal}
												className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition hover:border-slate-300 hover:text-slate-800"
												aria-label="关闭灵感仓库弹窗"
											>
												<X className="h-5 w-5" />
											</button>
										</div>

										<div className="space-y-5">
											<label className="block">
												<div className="ui-type-meta mb-2 text-slate-500">标题</div>
												<input
													value={inspirationDraft.title}
													onChange={(e) => setInspirationDraft((prev) => (prev ? { ...prev, title: e.target.value } : prev))}
													placeholder="为这张灵感命名"
													className="cockpit-search-input"
												/>
											</label>

											<div className="grid gap-4 md:grid-cols-2">
												<label className="block">
													<div className="ui-type-meta mb-2 text-slate-500">自定义分类</div>
													<input
														value={inspirationDraft.category}
														onChange={(e) => setInspirationDraft((prev) => (prev ? { ...prev, category: e.target.value } : prev))}
														placeholder="例：客房 / 木作 / 日式侘寂"
														className="cockpit-search-input"
													/>
												</label>
												<label className="block">
													<div className="ui-type-meta mb-2 text-slate-500">标签</div>
													<input
														value={inspirationDraft.tagsInput}
														onChange={(e) => setInspirationDraft((prev) => (prev ? { ...prev, tagsInput: e.target.value } : prev))}
														placeholder="用逗号分隔多个标签"
														className="cockpit-search-input"
													/>
												</label>
											</div>

											<label className="block">
												<div className="ui-type-meta mb-2 text-slate-500">说明</div>
												<textarea
													value={inspirationDraft.desc}
													onChange={(e) => setInspirationDraft((prev) => (prev ? { ...prev, desc: e.target.value } : prev))}
													placeholder="记录为什么收藏它、适合什么场景、后续如何复用"
													className="min-h-[140px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-sky-400"
												/>
											</label>
										</div>

										<div className="mt-6 flex flex-wrap items-center justify-between gap-3">
											<div className="flex items-center gap-2">
												<button
													onClick={saveInspirationItem}
													className="inline-flex min-w-[172px] items-center justify-center rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white shadow-[0_12px_28px_rgba(15,23,42,0.24)] transition hover:bg-slate-800"
												>
													{inspirationDraft.id ? '更新灵感' : '保存到灵感仓库'}
												</button>
											</div>
											{inspirationDraft.id && (
												<button
													onClick={deleteInspirationItem}
													className="cockpit-card-action text-rose-600 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700"
												>
													删除这条灵感
												</button>
											)}
										</div>
									</div>
								</div>
							</div>,
							document.body
						)}
					</div>
				);

			case 'board':
				return (
					<div className="cockpit-panel-root cockpit-immersive-canvas-root">
						<div className="absolute inset-0 flex overflow-hidden">
							<div className="cockpit-immersive-canvas-header">
								<div
									className="cockpit-immersive-canvas-header-inner"
									onMouseEnter={() => setBoardHeaderHovered(true)}
									onMouseLeave={() => setBoardHeaderHovered(false)}
								>
									<div className="cockpit-immersive-canvas-title">
										{resolvedProjectLabel}
									</div>
									<div className={`cockpit-immersive-canvas-pills transition-opacity ${boardHeaderHovered ? 'opacity-100' : 'opacity-88'}`}>
										{BOARD_CANVAS_SPACE_OPTIONS.map((space) => {
											const active = currentBoardSpace === space;
											return (
												<button
													key={`board-space-${space}`}
													onClick={() => onActiveBoardSpaceChange?.(space)}
													className={`cockpit-immersive-canvas-pill ${active ? 'cockpit-immersive-canvas-pill-active' : ''}`}
												>
													<span>{space}</span>
												</button>
											);
										})}
									</div>
								</div>
							</div>

							<div className="relative flex h-full min-w-0 flex-1 overflow-hidden">
								{isBoardOverview ? (
									<div className={`h-full overflow-y-auto pr-6 pb-6 pt-24 text-white ${boardLeftInsetClass}`}>
										<div className="grid gap-4 lg:grid-cols-[minmax(300px,420px)_1fr]">
											<div className="rounded-none border border-white/8 bg-black/18 p-6 backdrop-blur-sm">
												<div className="text-[18px] font-semibold text-white">全部空间总览</div>
												<p className="mt-2 text-sm leading-6 text-white/66">
													这里只做项目级概览，不做混合编辑。进入具体空间后，打开的是该空间唯一的方案画布实例。
												</p>
												<div className="mt-5 grid grid-cols-2 gap-3">
													<div className="rounded-none border border-white/8 bg-white/6 p-4">
														<div className="text-[11px] uppercase tracking-[0.14em] text-white/42">空间数</div>
														<div className="mt-2 text-3xl font-semibold text-white">{boardSpaceOverviewCards.length}</div>
													</div>
													<div className="rounded-none border border-white/8 bg-white/6 p-4">
														<div className="text-[11px] uppercase tracking-[0.14em] text-white/42">画布素材</div>
														<div className="mt-2 text-3xl font-semibold text-white">
															{boardSpaceOverviewCards.reduce((sum, item) => sum + item.count, 0)}
														</div>
													</div>
												</div>
											</div>

											<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
												{boardSpaceOverviewCards.map((item) => {
													const hasCanvas = item.count > 0;
													return (
														<button
															key={`board-overview-${item.space}`}
															onClick={() => {
																onEnterBoardSpace?.(item.space);
																onActiveBoardSpaceChange?.(item.space);
															}}
															className="rounded-none border border-white/10 bg-white/[0.05] p-5 text-left transition hover:border-white/20 hover:bg-white/[0.08]"
														>
															<div className="flex items-center justify-between gap-3">
																<div>
																	<div className="text-[18px] font-semibold text-white">{item.space}</div>
																	<div className="mt-1 text-sm text-white/50">
																		{hasCanvas ? '已有空间画布' : '尚未开始编排'}
																	</div>
																</div>
																<span className={`h-2.5 w-2.5 rounded-full ${hasCanvas ? 'bg-emerald-400' : 'bg-white/22'}`} />
															</div>
															<div className="mt-6 flex items-end justify-between gap-4">
																<div>
																	<div className="text-[11px] uppercase tracking-[0.14em] text-white/38">已放入素材</div>
																	<div className="mt-2 text-4xl font-semibold text-white">{item.count}</div>
																</div>
																<div className="rounded-full border border-white/12 px-3 py-1.5 text-[12px] font-medium text-white/74">
																	进入画布
																</div>
															</div>
														</button>
													);
												})}
											</div>
										</div>
									</div>
								) : (
									<>
							<div
								ref={boardCanvasViewportRef}
								onMouseDown={handleBoardCanvasMouseDown}
								onWheel={handleBoardCanvasWheel}
								onAuxClick={(event) => {
									if (event.button !== 1) return;
									event.preventDefault();
									event.stopPropagation();
								}}
									className="project-workspace-main-column project-workspace-canvas-column cockpit-canvas-viewport relative h-full min-w-0 flex-1 overflow-hidden cursor-grab active:cursor-grabbing"
							>
								<div
									className="absolute inset-0"
									style={{
										transform: `translate(${boardCanvasView.x}px, ${boardCanvasView.y}px) scale(${boardCanvasView.zoom})`,
										transformOrigin: '0 0',
									}}
								>
									{activeSpacePlanView && showBoardPlanOverlay && (
										<div
											className="pointer-events-none absolute overflow-hidden border border-cyan-300/20 bg-cyan-950/[0.08] text-white/70"
											style={{ left: 72, top: 82, width: 760, height: 430 }}
										>
											{activeSpacePlanTopic?.uploadedFileUrl && activeSpacePlanTopic.mimeType?.startsWith('image/') ? (
												<img
													src={activeSpacePlanTopic.uploadedFileUrl}
													alt={activeSpacePlanTopic.uploadedFileName ?? `${activeSpacePlanView.space} 平面图`}
													className="absolute inset-0 h-full w-full object-contain opacity-90"
												/>
											) : activeSpacePlanTopic?.uploadedFileUrl && activeSpacePlanTopic.mimeType === 'application/pdf' ? (
												<iframe
													src={activeSpacePlanTopic.uploadedFileUrl}
													title={activeSpacePlanTopic.uploadedFileName ?? `${activeSpacePlanView.space} PDF 平面图`}
													className="absolute inset-0 h-full w-full bg-white opacity-90"
												/>
											) : activeSpacePlanTopic?.uploadedFileUrl && activeSpacePlanTopic.sourceType === 'dxf' ? (
												<div className="absolute inset-0 overflow-hidden bg-white opacity-90">
													<DxfPlanCanvas
														src={activeSpacePlanTopic.uploadedFileUrl}
														zoom={0.32}
														onWheel={(event) => event.preventDefault()}
														className="origin-top-left"
													/>
												</div>
											) : (
											<svg viewBox="0 0 760 430" className="h-full w-full">
												<defs>
													<pattern id={`plan-grid-${activeSpacePlanView.space}`} width="38" height="38" patternUnits="userSpaceOnUse">
														<path d="M 38 0 L 0 0 0 38" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
													</pattern>
												</defs>
												<rect width="760" height="430" fill={`url(#plan-grid-${activeSpacePlanView.space})`} />
												<rect x="52" y="54" width="656" height="322" fill="rgba(15,23,42,0.18)" stroke="rgba(255,255,255,0.34)" strokeWidth="2" />
												<path d="M 92 330 L 640 330" stroke="rgba(250,204,21,0.42)" strokeWidth="18" strokeLinecap="round" />
												<path d="M 126 318 C 250 220, 430 188, 590 116" stroke="rgba(52,211,153,0.4)" strokeWidth="4" strokeDasharray="10 8" fill="none" />
												{activeSpacePlanView.features.map((feature) => {
													const tone = getPlanFeatureTone(feature.kind);
													const x = feature.x * 760;
													const y = feature.y * 430;
													const w = (feature.w ?? 0.06) * 760;
													const h = (feature.h ?? 0.06) * 430;
													if (feature.w || feature.h) {
														return (
															<g key={`plan-overlay-${feature.id}`}>
																<rect
																	x={x - w / 2}
																	y={y - h / 2}
																	width={w}
																	height={h}
																	rx="8"
																	fill={tone.bg}
																	stroke={tone.color}
																	strokeWidth="2"
																	strokeDasharray={feature.kind === 'flexible' ? '7 6' : undefined}
																/>
																<text x={x - w / 2 + 10} y={y - h / 2 + 22} fill="rgba(255,255,255,0.78)" fontWeight="600" style={svgBodyTextStyle}>
																	{feature.label}
																</text>
															</g>
														);
													}
													return (
														<g key={`plan-overlay-${feature.id}`}>
															<circle cx={x} cy={y} r="13" fill={tone.bg} stroke={tone.color} strokeWidth="2" />
															<circle cx={x} cy={y} r="4" fill={tone.color} />
															<text x={x + 16} y={y + 4} fill="rgba(255,255,255,0.78)" fontWeight="600" style={svgBodyTextStyle}>
																{feature.label}
															</text>
														</g>
													);
												})}
											</svg>
											)}
											<div className="absolute left-4 top-3 rounded-full border border-white/12 bg-black/48 px-3 py-1 text-[11px] font-medium text-white/72 backdrop-blur-sm">
												{activeSpacePlanTopic?.uploadedFileUrl ? '真实图纸' : '示意底图'} · {activeSpacePlanTopic?.uploadedFileName ?? activeSpacePlanView.detailPlanRef.title}
											</div>
											{(activeSpacePlanTopic?.annotations ?? []).map((annotation, index) => {
												const tone = getPlanAnnotationTone(annotation.kind);
												const zoomSafe = Math.max(boardCanvasView.zoom, 0.2);
												return (
													<div
														key={`plan-base-annotation-${annotation.id}`}
														className="absolute inline-flex items-center justify-center rounded-full border-2 bg-black/68 text-[10px] font-semibold"
														style={{
															left: `${annotation.x * 100}%`,
															top: `${annotation.y * 100}%`,
															width: `${26 / zoomSafe}px`,
															height: `${26 / zoomSafe}px`,
															borderColor: tone.color,
															color: tone.color,
															transform: 'translate(-50%, -50%)',
														}}
														title={`${tone.label} · ${annotation.label}`}
													>
														{index + 1}
													</div>
												);
											})}
										</div>
									)}
									{boardCanvasItems.map((item) => {
										const selected = item.id === selectedBoardCanvasItemId;
										const disabled = Boolean(item.disabled);
										const referenceControl = getCanvasItemReferenceControl(item);
										const anchorMarkers =
											referenceControl.kind === 'detail_card' || referenceControl.kind === 'relation_card' || referenceControl.kind === 'scene_card'
												? getCanvasItemAnchorMarkers(item, referenceControl)
												: [];
										const itemImageSeries = getCanvasItemImageSeries(item);
										const canTurnSceneImage = referenceControl.kind === 'scene_card' && Boolean(itemImageSeries && itemImageSeries.images.length > 1);
											const shouldHideCanvasText = boardCanvasView.zoom < 0.8;
											const isBrightCanvasImage = boardCanvasBrightImageMap[item.id] ?? false;
										const entityLabel =
											referenceControl
												? referenceControl.label
												: item.entityType === 'insight'
												? '解读卡'
												: item.entityType === 'anchor'
													? '锚点卡'
													: item.entityType === 'project'
														? '项目包'
														: '单图';
										return (
											<div
												key={item.id}
												data-board-item="true"
												onMouseDown={(event) => handleBoardItemMouseDown(event, item)}
												onDoubleClick={() => onCardClick?.(item.title)}
												className="absolute overflow-visible text-left"
												style={{
													left: `${item.x}px`,
													top: `${item.y}px`,
													width: `${item.width}px`,
												}}
											>
												<div className="relative">
													<img
														src={item.imageSrc}
														alt={item.title}
														className={`block w-full bg-[#232323] object-contain transition-[filter,opacity] duration-200 ${
															disabled ? 'grayscale opacity-55 saturate-0' : ''
														}`}
														data-fallback-src={item.fallbackImageSrc}
														onError={handleResourceImageError}
														onLoad={(event) => handleBoardCanvasImageLoad(item.id, event)}
														draggable={false}
													/>
													{isBrightCanvasImage && !shouldHideCanvasText && (
														<div className="pointer-events-none absolute inset-0 z-[1] bg-gradient-to-t from-black/60 via-black/35 to-black/48" />
													)}
													{!shouldHideCanvasText && (
													<div className="pointer-events-none absolute inset-x-0 top-0 z-[2] flex items-start justify-between gap-3 p-3">
																<span
																className={`rounded-full bg-black/78 px-3 py-1 font-medium tracking-[0.04em] text-white ${selected ? 'text-sm' : 'text-xs'}`}
																	style={{
																		transform: `scale(${1 / Math.max(boardCanvasView.zoom, 0.2)})`,
																		transformOrigin: 'left top',
																	}}
																>
																	{entityLabel}
																</span>
														{item.meta && (
																	<span
																	className={`max-w-[60%] truncate rounded-full bg-black/68 px-3 py-1 text-white/88 ${selected ? 'text-sm' : 'text-xs'}`}
																		style={{
																			transform: `scale(${1 / Math.max(boardCanvasView.zoom, 0.2)})`,
																			transformOrigin: 'right top',
																		}}
																	>
																{item.meta}
															</span>
														)}
													</div>
													)}
													{canTurnSceneImage && selected && (
														<div className="absolute inset-0 z-[5] pointer-events-none">
															<button
																type="button"
																onMouseDown={(event) => {
																	event.stopPropagation();
																	setSelectedBoardCanvasItemId(item.id);
																}}
																onClick={(event) => {
																	event.stopPropagation();
																	turnBoardCanvasSceneImage(item.id, -1);
																}}
																className="pointer-events-auto absolute inset-y-0 left-0 flex w-1/4 items-center justify-start pl-3"
																aria-label="上一张场景参考图"
															>
																<span
																	className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/16 bg-black/54 text-[16px] font-medium leading-none text-white/86 backdrop-blur-sm hover:bg-black/72"
																	style={{
																		transform: `scale(${1 / boardCanvasView.zoom})`,
																		transformOrigin: 'left center',
																	}}
																>
																	‹
																</span>
															</button>
															<button
																type="button"
																onMouseDown={(event) => {
																	event.stopPropagation();
																	setSelectedBoardCanvasItemId(item.id);
																}}
																onClick={(event) => {
																	event.stopPropagation();
																	turnBoardCanvasSceneImage(item.id, 1);
																}}
																className="pointer-events-auto absolute inset-y-0 right-0 flex w-1/4 items-center justify-end pr-3"
																aria-label="下一张场景参考图"
															>
																<span
																	className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/16 bg-black/54 text-[16px] font-medium leading-none text-white/86 backdrop-blur-sm hover:bg-black/72"
																	style={{
																		transform: `scale(${1 / boardCanvasView.zoom})`,
																		transformOrigin: 'right center',
																	}}
																>
																	›
																</span>
															</button>
														</div>
													)}
													{!shouldHideCanvasText && anchorMarkers.map((marker) => {
														const activeMarker = selected && marker.included && (marker.primary || anchorMarkers.length === 1);
														const canToggleAnchor = referenceControl.kind === 'relation_card';
														return (
															<button
																type="button"
																key={`${item.id}-anchor-${marker.id}`}
																onMouseDown={(event) => {
																	event.stopPropagation();
																	setSelectedBoardCanvasItemId(item.id);
																}}
																onClick={(event) => {
																	event.stopPropagation();
																	if (canToggleAnchor) toggleBoardCanvasAnchorSelection(item.id, marker.id);
																}}
																className={`cockpit-image-anchor ${canToggleAnchor ? 'pointer-events-auto cursor-pointer' : 'pointer-events-none'} ${marker.included ? '' : 'is-muted'} ${activeMarker ? 'is-active cockpit-image-anchor-selected' : ''}`}
																style={{
																	left: `${Math.max(4, Math.min(96, marker.x * 100))}%`,
																	top: `${Math.max(4, Math.min(96, marker.y * 100))}%`,
																	transform: `translate(-50%, -50%) scale(${1 / boardCanvasView.zoom})`,
																	transformOrigin: 'center',
																}}
																title={`${marker.included ? '已采用，点击移除' : '未采用，点击加入'}${marker.title ? `：${marker.title}` : ''}`}
															>
																<span className="cockpit-image-anchor-dot" />
															</button>
														);
													})}
															{!shouldHideCanvasText && (
															<div className="pointer-events-none absolute inset-x-0 bottom-0 z-[2] bg-gradient-to-t from-black/86 via-black/52 to-transparent px-4 pb-4 pt-10">
																<div
																	style={{
																		transform: `scale(${1 / Math.max(boardCanvasView.zoom, 0.2)})`,
																		transformOrigin: 'left bottom',
																		width: `${Math.max(boardCanvasView.zoom, 0.2) * 100}%`,
																		textShadow: '0 1px 2px rgba(0,0,0,0.92), 0 4px 14px rgba(0,0,0,0.55)',
																	}}
																>
																	<div className={`${selected ? 'text-xl' : 'text-lg'} font-semibold text-white`}>{item.title}</div>
																	{referenceControl && (
																		<div className="mt-1 flex flex-wrap gap-1.5">
																			<span className={`rounded-full bg-sky-400/20 px-2 py-0.5 text-sky-100 ${selected ? 'text-xs' : 'text-[11px]'}`}>
																				主参考 {referenceControl.primaryRole}
																			</span>
																			<span className={`rounded-full bg-white/12 px-2 py-0.5 text-white/72 ${selected ? 'text-xs' : 'text-[11px]'}`}>
																				权重 {referenceControl.weight === 'high' ? '高' : referenceControl.weight === 'low' ? '低' : '中'}
																			</span>
																		</div>
																	)}
																	{item.desc && (
																		<div className={`mt-1 line-clamp-3 text-white/78 ${selected ? 'text-base leading-7' : 'text-sm leading-6'}`}>
																			{item.desc}
																		</div>
																	)}
																</div>
															</div>
															)}
													{disabled && (
														<div className="pointer-events-none absolute inset-0 bg-slate-950/18" />
													)}
													{selected && (
														<>
																	<div
																		className="pointer-events-none absolute inset-0 border border-sky-400"
																		style={{ borderWidth: `${2 / Math.max(boardCanvasView.zoom, 0.2)}px` }}
																	/>
															{BOARD_RESIZE_HANDLES.map((handle) => {
																const zoomSafe = Math.max(boardCanvasView.zoom, 0.2);
																const handleSize = 12 / zoomSafe;
																const handleOffset = 6 / zoomSafe;
																const handleBorderWidth = 1 / zoomSafe;
																const positions: Record<BoardResizeHandle, React.CSSProperties> = {
																	nw: { left: `${-handleOffset}px`, top: `${-handleOffset}px` },
																	n: { left: '50%', top: `${-handleOffset}px`, transform: 'translateX(-50%)' },
																	ne: { right: `${-handleOffset}px`, top: `${-handleOffset}px` },
																	e: { right: `${-handleOffset}px`, top: '50%', transform: 'translateY(-50%)' },
																	se: { right: `${-handleOffset}px`, bottom: `${-handleOffset}px` },
																	s: { left: '50%', bottom: `${-handleOffset}px`, transform: 'translateX(-50%)' },
																	sw: { left: `${-handleOffset}px`, bottom: `${-handleOffset}px` },
																	w: { left: `${-handleOffset}px`, top: '50%', transform: 'translateY(-50%)' },
																};

																return (
																	<span
																		key={`${item.id}-${handle}`}
																		onMouseDown={(event) => handleBoardItemResizeMouseDown(event, item, handle)}
																		className="absolute rounded-full border border-sky-200 bg-sky-400 shadow-[0_0_0_2px_rgba(15,23,42,0.46)]"
																		style={{
																			width: `${handleSize}px`,
																			height: `${handleSize}px`,
																			borderWidth: `${handleBorderWidth}px`,
																			cursor: getBoardResizeCursor(handle),
																			...positions[handle],
																		}}
																	/>
																);
															})}
															{!shouldHideCanvasText && (
															<div className={`pointer-events-none absolute inset-x-0 -bottom-7 truncate text-center font-medium tracking-[0.04em] text-white/80 ${selected ? 'text-sm' : 'text-xs'}`}>
																{item.title}
															</div>
															)}
														</>
													)}
													{disabled && (
														<div className="pointer-events-none absolute left-3 top-3 rounded-full border border-white/16 bg-black/72 px-2.5 py-1 text-[11px] font-medium tracking-[0.08em] text-white/78">
															已停用
														</div>
													)}
												</div>
											</div>
										);
									})}
								</div>

								{boardCanvasItems.length === 0 && (
									<div
										className={`absolute inset-0 flex items-center justify-center p-8 text-center ${boardLeftInsetClass}`}
									>
										<div className="max-w-md rounded-none border border-white/8 bg-black/20 px-8 py-7 text-white/70 backdrop-blur-sm">
											<div className="text-base font-semibold text-white">{currentBoardSpace}空白画布</div>
											<p className="mt-2 text-sm leading-6">
												从右侧输入源把与{currentBoardSpace}相关的素材加入进来，再继续摆放、停用和筛选。
											</p>
										</div>
									</div>
								)}

								{activeSpacePlanView && (
									<div className="pointer-events-auto absolute left-[108px] top-24 z-30 w-[360px] border border-white/12 bg-black/58 p-4 text-white shadow-[0_20px_70px_rgba(0,0,0,0.36)] backdrop-blur-xl">
										<div className="flex items-start justify-between gap-3">
											<div>
												<div className="text-[11px] uppercase tracking-[0.16em] text-cyan-200/58">Plan Base</div>
												<div className="mt-1 text-sm font-semibold text-white">图纸基线 · {activeSpacePlanView.space}</div>
												<div className="mt-1 text-[11px] text-white/42">来自项目底盘 · 平面图与空间关系</div>
											</div>
											<span className={`rounded-full border px-2.5 py-1 text-[11px] ${
												activeSpacePlanTopic?.status === 'stale'
													? 'border-amber-300/20 text-amber-100'
													: 'border-emerald-300/20 text-emerald-100'
											}`}>
												{activeSpacePlanTopic ? getPlanTopicStatusLabel(activeSpacePlanTopic.status) : '已同步'}
											</span>
										</div>
										<div className="mt-3 grid grid-cols-1 gap-3">
											<div className="relative h-[88px] overflow-hidden border border-white/10 bg-white/[0.04]">
												<div className="absolute left-[15%] top-[20%] h-[22%] w-[28%] border border-white/18 bg-white/8" />
												<div className="absolute left-[48%] top-[20%] h-[22%] w-[30%] border border-white/18 bg-white/8" />
												<div className="absolute left-[15%] top-[52%] h-[26%] w-[26%] border border-white/18 bg-white/8" />
												<div className="absolute left-[48%] top-[52%] h-[26%] w-[30%] border border-cyan-300 bg-cyan-300/22 shadow-[0_0_18px_rgba(34,211,238,0.25)]" />
												<div className="absolute bottom-2 left-2 rounded-full bg-black/50 px-2 py-0.5 text-[10px] text-white/62">总平关系</div>
											</div>
											<div className="min-w-0 text-xs leading-5 text-white/68">
												<div className="truncate">{activeSpacePlanView.overallPlanRef.title}</div>
												<div className="truncate">{activeSpacePlanView.detailPlanRef.title}</div>
												{activeSpacePlanTopic?.uploadedFileName && (
													<div className="truncate text-cyan-100/70">{activeSpacePlanTopic.uploadedFileName}</div>
												)}
												{activeSpacePlanTopic?.parseMessage && (
													<div className="line-clamp-1 text-cyan-100/56">{activeSpacePlanTopic.parseMessage}</div>
												)}
												<div className="mt-1 truncate text-white/42">{activeSpacePlanView.spgVersion} · {activeSpacePlanView.irVersion}</div>
											</div>
										</div>
										<div className="mt-3 flex flex-wrap gap-2">
											<button
												onClick={() => openPlanUploadPicker(activeSpacePlanView.space)}
												className="rounded-full border border-white/12 px-3 py-1.5 text-[11px] font-medium text-white/72 hover:bg-white/8"
											>
												{planUploadBusySpace === activeSpacePlanView.space ? '上传中...' : '上传图纸'}
											</button>
											<button
												onClick={() => handleOpenPlanViewer(activeSpacePlanView.space)}
												disabled={!activeSpacePlanTopic?.uploadedFileUrl}
												className={`rounded-full border px-3 py-1.5 text-[11px] font-medium ${
													activeSpacePlanTopic?.uploadedFileUrl
														? 'border-white/12 text-white/72 hover:bg-white/8'
														: 'cursor-not-allowed border-white/8 text-white/28'
												}`}
											>
												查看图纸
											</button>
											<button
												onClick={() => setShowBoardPlanOverlay((prev) => !prev)}
												className={`rounded-full border px-3 py-1.5 text-[11px] font-medium ${
													showBoardPlanOverlay
														? 'border-cyan-300/24 bg-cyan-300/12 text-cyan-100'
														: 'border-white/12 text-white/62 hover:bg-white/8'
												}`}
											>
												{showBoardPlanOverlay ? '隐藏分平底图' : '显示分平底图'}
											</button>
											<button
												onClick={() => setExpandedBoardPlanBase((prev) => !prev)}
												className="rounded-full border border-white/12 px-3 py-1.5 text-[11px] font-medium text-white/72 hover:bg-white/8"
											>
												{expandedBoardPlanBase ? '收起约束' : '查看约束'}
											</button>
										</div>
										{expandedBoardPlanBase && (
											<div className="mt-3 max-h-[300px] overflow-y-auto border-t border-white/10 pt-3 text-xs leading-5 text-white/66">
												<div className="font-semibold text-white/86">空间角色</div>
												<div>{activeSpacePlanView.planBrief.spatialRole}</div>
												<div className="mt-2 font-semibold text-white/86">总平关系</div>
												<div>{activeSpacePlanView.planBrief.adjacency.join(' / ')}</div>
												<div className="mt-2 font-semibold text-white/86">主通行</div>
												<div>{activeSpacePlanView.planBrief.mainCirculation.join('；')}</div>
												<div className="mt-2 font-semibold text-white/86">不可突破条件</div>
												<div>{activeSpacePlanView.planBrief.fixedConstraints.join('；')}</div>
												<div className="mt-2 font-semibold text-white/86">镜头建议</div>
												<div>{activeSpacePlanView.planBrief.cameraSuggestions.join(' / ')}</div>
												<div className="mt-3 flex flex-wrap gap-1.5">
													{activeSpacePlanView.features.map((feature) => {
														const tone = getPlanFeatureTone(feature.kind);
														return (
															<span
																key={`plan-feature-chip-${feature.id}`}
																className="rounded-full border px-2 py-0.5 text-[10px]"
																style={{ borderColor: `${tone.color}55`, color: tone.color, background: tone.bg }}
															>
																{tone.label} · {feature.label}
															</span>
														);
													})}
												</div>
											</div>
										)}
									</div>
								)}

								{selectedBoardCanvasItem && selectedBoardCanvasAnchorMarkers.length > 0 && (
													<div
														className="pointer-events-auto absolute z-30 w-[min(340px,calc(100%-2rem))] border-l border-white/24 bg-black/82 px-4 py-4 text-white shadow-[0_24px_80px_rgba(0,0,0,0.4)] backdrop-blur-xl"
														style={{
															...selectedBoardCanvasAnchorPanelStyle,
															textShadow: anchorSummaryTextShadow,
														}}
										onMouseDown={(event) => event.stopPropagation()}
										onWheel={(event) => {
											event.stopPropagation();
										}}
									>
										<div className="flex items-start justify-between gap-3">
															<div style={{ textShadow: anchorSummaryBodyTextShadow }}>
												<div className="text-[11px] uppercase tracking-[0.14em] text-white/38">锚点摘要</div>
																<div className="mt-1 text-lg font-semibold text-white" style={{ textShadow: anchorSummaryBodyTextShadow }}>{selectedBoardCanvasItem.title}</div>
											</div>
															<span className="rounded-full border border-white/12 px-2.5 py-1 text-sm text-white/58" style={{ textShadow: anchorSummaryBodyTextShadow }}>
												{selectedBoardCanvasAnchorMarkers.filter((marker) => marker.included).length}/{selectedBoardCanvasAnchorMarkers.length}
											</span>
										</div>
														<div className="mt-4 space-y-3 overflow-y-auto pr-2" style={{ height: 'calc(100% - 78px)' }}>
											{selectedBoardCanvasAnchorMarkers.map((marker, markerIndex) => {
												const canToggleAnchor = selectedBoardCanvasReferenceControl?.kind === 'relation_card';
												const markerUsageLabel = selectedBoardCanvasReferenceControl?.kind === 'scene_card'
													? '图内锚点'
													: marker.included
														? '已用于方案'
														: '可加入方案';
												return (
													<button
														type="button"
														key={`selected-board-anchor-${marker.id}`}
														onClick={() => {
															if (canToggleAnchor) toggleBoardCanvasAnchorSelection(selectedBoardCanvasItem.id, marker.id);
														}}
														className={`w-full border-l py-1.5 pl-4 pr-2 text-left transition ${
															marker.included
																? 'border-sky-300 text-white hover:bg-white/6'
																: 'border-white/10 text-white/42 hover:border-white/24 hover:bg-white/5 hover:text-white/66'
														}`}
													>
														<div className="flex items-start justify-between gap-3">
															<div className="min-w-0">
																<div className="flex items-center gap-2">
																	<span className="ui-type-meta text-white/35">{String(markerIndex + 1).padStart(2, '0')}</span>
																			<span className="truncate text-lg font-medium" style={{ textShadow: anchorSummaryBodyTextShadow }}>{marker.title ?? '锚点'}</span>
																</div>
																			<div className="mt-1 flex flex-wrap gap-1.5 text-xs text-white/58" style={{ textShadow: anchorSummaryBodyTextShadow }}>
																	{marker.type && <span>{marker.type}</span>}
																	{marker.topic && <span>{marker.topic}</span>}
																	<span>{markerUsageLabel}</span>
																</div>
															</div>
															{canToggleAnchor && (
																<span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] ${
																	marker.included ? 'bg-white/14 text-white/70' : 'bg-white/8 text-white/42'
																}`}>
																	{marker.included ? '移除' : '加入'}
																</span>
															)}
														</div>
																{marker.summary && (
																			<div className="mt-2 text-base leading-7 text-white/78" style={{ textShadow: anchorSummaryBodyTextShadow }}>{marker.summary}</div>
																)}
													</button>
												);
											})}
										</div>
									</div>
								)}
							</div>

							<div className="cockpit-canvas-side-panel-wrap cockpit-board-canvas-side-panel-wrap project-workspace-middle-column cursor-default">
								<div
									className={`workspace-info-panel cockpit-canvas-side-panel cursor-default ${
										boardSourceTab === 'generated'
											? 'border-sky-200/60 !bg-[#1fa2df] !text-white'
											: ''
									}`}
								>
									{renderBoardInformationWhiteboard()}
									<div className={`cockpit-canvas-side-panel-header ${boardSourceTab === 'generated' ? '!border-white/18' : ''}`}>
										{boardSourceTab !== 'generated' && (
											<input
												value={boardQuery}
												onChange={(e) => setBoardQuery(e.target.value)}
												placeholder={`搜索${currentBoardSpace}输入源（例：木作、灯光、历史项目）`}
												className="cockpit-canvas-search"
											/>
										)}
										<div className={`${boardSourceTab === 'generated' ? '!mt-0' : ''} cockpit-canvas-source-tabs`}>
											{([
												{ key: 'radar', label: '资源雷达' },
												{ key: 'inspiration', label: '灵感收藏' },
												{ key: 'history', label: '历史项目素材' },
												{
													key: 'generated',
													label:
														boardGeneratedUnseenCount > 0
															? `生成带（${boardGeneratedUnseenCount}）`
															: '生成带',
												},
											] as Array<{ key: BoardSourceTab; label: string }>).map((tab) => (
												<button
													key={`board-source-tab-${tab.key}`}
													onClick={() => setBoardSourceTab(tab.key)}
													className={`cockpit-canvas-source-tab ${
														boardSourceTab === tab.key
															? boardSourceTab === 'generated'
																? 'bg-white/84 text-sky-900 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)] backdrop-blur-sm'
																: 'cockpit-canvas-source-tab-active'
															: boardSourceTab === 'generated'
																? 'border border-white/18 bg-white/10 text-white/82 hover:bg-white/18 hover:text-white'
																: ''
													}`}
												>
													{tab.label}
												</button>
											))}
											{boardSourceTab !== 'generated' && (
												<button
													onClick={() => {
														setBoardDeepBrowseTab(boardSourceTab as BoardDeepBrowseTab);
														if (boardSourceTab === 'history') {
															setBoardLibraryNavKey(null);
															setBoardLibrarySubcategory(ALL_BOARD_LIBRARY_SUBCATEGORY);
														}
													}}
													className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-500 transition hover:border-slate-300 hover:bg-white hover:text-slate-900"
													aria-label="全屏浏览当前素材来源"
													title="全屏浏览当前素材来源"
												>
													<LayoutGrid className="h-3.5 w-3.5" />
												</button>
											)}
										</div>
										{boardSourceTab === 'generated' && (
											<div className="mt-3 flex flex-nowrap gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
												{(['本轮', '最近', '全部'] as BoardGeneratedRoundFilter[]).map((filter) => (
													<button
														key={`board-generated-round-${filter}`}
														onClick={() => setBoardGeneratedRoundFilter(filter)}
														className={`shrink-0 rounded-full px-3 py-1.5 text-[11px] font-medium transition ${
															boardGeneratedRoundFilter === filter
																? 'bg-white text-sky-900 shadow-sm'
																: 'bg-white/14 text-white/78 hover:bg-white/24 hover:text-white'
														}`}
													>
														{filter}
													</button>
												))}
												{(['全部专题', ...BOARD_CANVAS_MODES] as Array<'全部专题' | BoardCanvasMode>).map((filter) => (
													<button
														key={`board-generated-topic-${filter}`}
														onClick={() => setBoardGeneratedTopicFilter(filter)}
														className={`shrink-0 rounded-full px-3 py-1.5 text-[11px] font-medium transition ${
															boardGeneratedTopicFilter === filter
																? 'bg-white text-sky-900 shadow-sm'
																: 'bg-white/14 text-white/78 hover:bg-white/24 hover:text-white'
														}`}
													>
														{filter}
													</button>
												))}
											</div>
										)}
									</div>

									<div className="cockpit-canvas-side-panel-body">
										{boardSourceTab === 'radar' && radarBoardSourceMode !== 'matched' && (
											<div className="mb-3 rounded-none border border-slate-200/80 bg-slate-50 px-4 py-3 text-[12px] leading-5 text-slate-500">
												{radarBoardSourceMode === 'empty_canvas'
													? '左侧画布暂无方案内容，当前没有匹配输出；下面先展示资源库，方便先逛街收藏。'
													: radarBoardSourceMode === 'no_space_match'
														? '当前空间暂无匹配输出；下面展示资源库全部素材。'
														: '全部空间总览模式：展示资源库全部素材。'}
											</div>
										)}
										<div className={boardSourceTab === 'generated' ? 'space-y-3' : 'columns-2 gap-3 [column-fill:_balance]'}>
											{filteredBoardSourceItems.length === 0 ? (
												<div
													className={`rounded-none border px-4 py-6 text-sm ${
														boardSourceTab === 'generated'
															? 'border-white/20 bg-white/14 text-white/78 backdrop-blur-sm'
															: 'border-slate-200/80 bg-white/55 text-slate-500'
													}`}
												>
													{boardSourceTab === 'generated'
														? '当前空间还没有生成结果。'
														: '当前空间没有匹配素材，试试切换来源或放宽关键词。'}
												</div>
											) : (
												filteredBoardSourceItems.map((item) => {
													const expanded = expandedBoardSourceItemId === item.id;
													const referenceControl = item.referenceControl;
													if (item.sourceType === 'generated') {
														return renderBoardGeneratedSourceCard(item, expanded);
													}
													return (
													<div key={item.id} className="mb-3 break-inside-avoid">
														<div
															onClick={() => setBoardSourceDetailItemId(item.id)}
															className="group block cursor-pointer overflow-hidden bg-transparent text-left"
														>
															<div className="relative overflow-hidden">
																<img
																	src={item.imageSrc}
																	alt={item.title}
																	className="block h-auto w-full transition-[filter] duration-300 group-hover:brightness-[0.72]"
																	data-fallback-src={item.fallbackImageSrc}
																	onError={handleResourceImageError}
																/>
																<div className="absolute inset-0 bg-black/0 transition-colors duration-300 group-hover:bg-black/34" />
																<div className="absolute inset-x-0 top-0 z-[3] p-3 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
																	<div className="line-clamp-3 text-sm font-semibold leading-5 text-white [text-shadow:0_1px_4px_rgba(0,0,0,0.58)]">
																		{item.title}
																	</div>
																</div>
															</div>
														</div>
													</div>
													);
												})
											)}
										</div>
									</div>
								</div>
							</div>

							{isClient && boardSourceDetailItem && createPortal(
									<div
										className="fixed inset-0 z-[2147483647] flex items-center justify-center overflow-hidden bg-[var(--cockpit-overlay-backdrop)] px-6 py-8 text-slate-100 backdrop-blur-xl"
										onClick={() => setBoardSourceDetailItemId(null)}
									>
									<div
										className="grid h-[76vh] min-h-[560px] w-fit max-w-[calc(100vw-3rem)] overflow-hidden bg-white text-slate-950 shadow-[0_30px_90px_rgba(0,0,0,0.42)]"
										style={boardSourceDetailShellStyle}
										onClick={(event) => event.stopPropagation()}
									>
										<div className="min-h-0 overflow-hidden transition-colors duration-300" style={boardSourceDetailImageStyle}>
											<img
												src={boardSourceDetailItem.imageSrc}
												alt={boardSourceDetailItem.title}
												className="block h-full w-full object-contain object-left"
												data-fallback-src={boardSourceDetailItem.fallbackImageSrc}
												onLoad={(event) => updateBoardSourceDetailImageMetrics(event.currentTarget)}
												onError={handleResourceImageError}
											/>
										</div>
										<div className="min-h-0 min-w-0 overflow-x-hidden overflow-y-auto p-8 [overflow-wrap:anywhere] [word-break:break-word]">
											<div className="flex items-start justify-between gap-6">
												<div className="min-w-0">
													<div className="text-[11px] uppercase tracking-[0.16em] text-slate-400">{boardSourceDetailItem.meta}</div>
													<h3 className="mt-3 break-words text-2xl font-semibold leading-tight text-slate-950 [overflow-wrap:anywhere]">{boardSourceDetailItem.title}</h3>
												</div>
												<button
													onClick={() => setBoardSourceDetailItemId(null)}
													className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-500 transition hover:bg-slate-200 hover:text-slate-900"
													aria-label="关闭素材详情"
												>
													<X className="h-4 w-4" />
												</button>
											</div>
											<p className="mt-5 text-sm leading-7 text-slate-600">{boardSourceDetailItem.desc}</p>
											{boardSourceDetailItem.referenceControl && (
												<div className="mt-6 rounded-none bg-slate-50 p-5 text-sm leading-6 text-slate-600">
													<div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">结构化引用</div>
													<div className="mt-3 font-medium text-slate-950">{boardSourceDetailItem.referenceControl.label}</div>
													<div className="mt-2">{boardSourceDetailItem.referenceControl.structuredSummary}</div>
													<div className="mt-3 grid gap-2 text-xs text-slate-500">
														<div>作用域：{boardSourceDetailItem.referenceControl.scope} · 权重：{boardSourceDetailItem.referenceControl.weight}</div>
														<div>必须保留：{boardSourceDetailItem.referenceControl.mustHave.join('、')}</div>
														<div>禁止带入：{boardSourceDetailItem.referenceControl.negative.join('、')}</div>
													</div>
												</div>
											)}
											<div className="mt-8 flex flex-wrap gap-3">
												<button
													onClick={() => {
														addBoardCanvasItem(boardSourceDetailItem);
														setBoardSourceDetailItemId(null);
													}}
													className="rounded-full bg-slate-950 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800"
												>
													加入画布
												</button>
												{boardSourceDetailItem.referenceControl && (
													<button
														onClick={() => {
															const referenceControl = boardSourceDetailItem.referenceControl;
															if (!referenceControl) return;
															setBoardSourceDetailItemId(null);
															openReferenceEditModal('source', referenceControl, { sourceId: boardSourceDetailItem.id });
														}}
														className="rounded-full bg-slate-100 px-5 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-200 hover:text-slate-950"
													>
														引用详情
													</button>
												)}
												<button
													onClick={() => onCardClick?.(boardSourceDetailItem.title)}
													className="rounded-full bg-slate-100 px-5 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-200 hover:text-slate-950"
												>
													引用
												</button>
											</div>
										</div>
									</div>
								</div>,
								document.body
							)}

							{isClient && boardDeepBrowseTab && createPortal(
								<div
									className="fixed inset-0 z-[2147483646] bg-[var(--cockpit-overlay-backdrop)] text-slate-100 backdrop-blur-xl"
									onClick={() => setBoardDeepBrowseTab(null)}
								>
									<div
										className="flex h-full flex-col"
										onClick={(event) => event.stopPropagation()}
									>
										<div className="group/boardBrowseHeader shrink-0 border-b border-white/10 bg-slate-950/88 px-6 py-4 lg:px-10">
											<div className="mx-auto flex max-w-[1680px] flex-col gap-3">
												<div className="flex flex-col gap-3 lg:flex-row lg:items-center">
													<div className="flex shrink-0 flex-wrap gap-2">
														{BOARD_DEEP_BROWSE_TABS.map((tab) => (
															<button
																key={`board-deep-tab-${tab.key}`}
																onClick={() => {
																	setBoardSourceTab(tab.key);
																	setBoardDeepBrowseTab(tab.key);
																	if (tab.key === 'history') {
																		setBoardLibraryNavKey(null);
																		setBoardLibrarySubcategory(ALL_BOARD_LIBRARY_SUBCATEGORY);
																	}
																}}
																className={`h-9 rounded-full px-4 text-[12px] font-medium transition ${
																	boardDeepBrowseTab === tab.key
																		? 'bg-white text-slate-950'
																		: 'bg-[rgba(255,255,255,0.14)] text-white/78 hover:bg-[rgba(255,255,255,0.22)] hover:text-white [text-shadow:0_1px_4px_rgba(0,0,0,0.48)]'
																}`}
															>
																{tab.label}
															</button>
														))}
													</div>
													<div className="ml-10 flex shrink-0 select-none items-center gap-2 text-white/62 [caret-color:transparent] lg:ml-16">
														<button
															onMouseDown={(event) => event.preventDefault()}
															onClick={() => setBoardDeepBrowseSizeLevel((prev) => Math.max(0, prev - 1))}
															onPointerUp={(event) => event.currentTarget.blur()}
															className="inline-flex h-7 w-5 items-center justify-center text-lg leading-none transition hover:text-white [text-shadow:0_1px_4px_rgba(0,0,0,0.48)]"
															aria-label="缩小卡片，显示更多列"
															title="缩小卡片，显示更多列"
														>
															-
														</button>
														<input
															type="range"
															min={0}
															max={6}
															step={1}
															value={boardDeepBrowseSizeLevel}
															onChange={(event) => setBoardDeepBrowseSizeLevel(Number(event.target.value))}
															onPointerUp={(event) => {
																event.currentTarget.blur();
																window.getSelection()?.removeAllRanges();
															}}
															onTouchEnd={(event) => {
																event.currentTarget.blur();
																window.getSelection()?.removeAllRanges();
															}}
															className="cockpit-density-range w-36 cursor-pointer"
															aria-label="调整素材卡片大小"
															title={`${boardDeepBrowseColumnCount} 列`}
															style={{
																'--density-track': `linear-gradient(to right, rgba(255,255,255,0.96) 0%, rgba(255,255,255,0.96) ${(boardDeepBrowseSizeLevel / 6) * 100}%, rgba(72,72,78,0.78) ${(boardDeepBrowseSizeLevel / 6) * 100}%, rgba(72,72,78,0.78) 100%)`,
															} as React.CSSProperties}
														/>
														<button
															onMouseDown={(event) => event.preventDefault()}
															onClick={() => setBoardDeepBrowseSizeLevel((prev) => Math.min(6, prev + 1))}
															onPointerUp={(event) => event.currentTarget.blur()}
															className="inline-flex h-7 w-5 items-center justify-center text-lg leading-none transition hover:text-white [text-shadow:0_1px_4px_rgba(0,0,0,0.48)]"
															aria-label="放大卡片，显示更少列"
															title="放大卡片，显示更少列"
														>
															+
														</button>
													</div>
													<div className="flex min-w-0 flex-1 items-center gap-3 lg:justify-end">
														<input
															value={boardQuery}
															onChange={(event) => setBoardQuery(event.target.value)}
															placeholder="搜索素材、空间、材料、灯光或项目关键词"
															className="h-11 min-w-0 flex-1 rounded-full border border-white/12 bg-white/8 px-4 text-sm text-white outline-none placeholder:text-white/32 focus:border-white/28 lg:max-w-xl"
														/>
														<div className="shrink-0 text-sm text-white/45">{boardDeepBrowseItems.length} 项</div>
														<button
															onClick={() => setBoardDeepBrowseTab(null)}
															className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white/12 text-white/76 transition hover:bg-white/20 hover:text-white"
															aria-label="关闭全屏浏览"
														>
															<X className="h-5 w-5" />
														</button>
													</div>
												</div>
												<div className="max-h-0 overflow-hidden opacity-0 transition-all duration-300 ease-out group-hover/boardBrowseHeader:max-h-64 group-hover/boardBrowseHeader:opacity-100">
													<div className="space-y-3 pt-1">
														{(boardDeepBrowseTab === 'radar' || boardDeepBrowseTab === 'inspiration') && (
															<div className="flex flex-wrap gap-2">
																{visibleBoardLibraryNavItems.map((item) => {
																	const isActive = boardLibraryNavKey === item.key;
																	return (
																		<button
																			key={`board-library-nav-${item.key}`}
																			onClick={() => {
																				setBoardLibraryNavKey((prev) => (prev === item.key ? null : item.key));
																				setBoardLibrarySubcategory(ALL_BOARD_LIBRARY_SUBCATEGORY);
																			}}
																			className={`h-8 rounded-full px-3 text-[11px] font-medium transition ${
																				isActive
																					? 'bg-white text-slate-950'
																					: 'bg-[rgba(255,255,255,0.14)] text-white/78 hover:bg-[rgba(255,255,255,0.22)] hover:text-white [text-shadow:0_1px_4px_rgba(0,0,0,0.48)]'
																			}`}
																		>
																			{item.label}
																		</button>
																	);
																})}
															</div>
														)}
														{currentBoardLibraryNav && (
															<div className="rounded-none bg-white/10 px-4 py-3 shadow-[0_12px_28px_rgba(0,0,0,0.18)]">
																<div className="flex flex-wrap items-center gap-x-4 gap-y-2">
																	{[
																		{ label: ALL_BOARD_LIBRARY_SUBCATEGORY, keywords: currentBoardLibraryNav.keywords },
																		...currentBoardLibraryNav.children,
																	].map((child) => {
																		const isActive = boardLibrarySubcategory === child.label;
																		return (
																			<button
																				key={`board-library-subnav-${currentBoardLibraryNav.key}-${child.label}`}
																				onClick={() => setBoardLibrarySubcategory(child.label)}
																				className={`px-1 py-1 text-[12px] font-medium transition ${
																					isActive
																						? 'text-white underline underline-offset-4 [text-shadow:0_1px_4px_rgba(0,0,0,0.54)]'
																						: 'text-white/62 hover:text-white [text-shadow:0_1px_4px_rgba(0,0,0,0.48)]'
																				}`}
																			>
																				{child.label === ALL_BOARD_LIBRARY_SUBCATEGORY ? '全部' : child.label}
																			</button>
																		);
																	})}
																</div>
															</div>
														)}
														{boardDeepBrowseTab === 'radar' && radarBoardSourceMode !== 'matched' && (
															<div className="rounded-none bg-white/6 px-4 py-2 text-sm leading-6 text-white/58 [text-shadow:0_1px_4px_rgba(0,0,0,0.45)]">
																{radarBoardSourceMode === 'empty_canvas'
																	? '左侧画布暂无方案内容，当前没有匹配输出；这里展示资源库，方便先逛街收藏。'
																	: radarBoardSourceMode === 'no_space_match'
																		? '当前空间暂无匹配输出；这里展示资源库全部素材。'
																		: '全部空间总览模式：展示资源库全部素材。'}
															</div>
														)}
													</div>
												</div>
											</div>
										</div>

										<div className="min-h-0 flex-1 overflow-y-auto px-6 py-6 lg:px-10">
											<div className="mx-auto max-w-[1680px]">
												{boardDeepBrowseItems.length === 0 ? (
													<div className="rounded-none border border-white/10 bg-white/6 px-6 py-10 text-center text-sm text-white/55">
														当前筛选下没有素材，试试清空搜索词或切换页面。
													</div>
												) : (
													<div
														className="[column-fill:_balance]"
														style={{
															columnCount: boardDeepBrowseColumnCount,
															columnGap: boardDeepBrowseColumnCount >= 7 ? 12 : 20,
														}}
													>
														{boardDeepBrowseItems.map((item) => {
															const isCompactDeepCard = boardDeepBrowseColumnCount >= 7;
															return (
																<div
																	key={`board-deep-${item.id}`}
																	role="button"
																	tabIndex={0}
																	aria-label={`查看 ${item.title} 详情`}
																	onClick={() => setBoardSourceDetailItemId(item.id)}
																	onKeyDown={(event) => {
																		if (event.key !== 'Enter' && event.key !== ' ') return;
																		event.preventDefault();
																		setBoardSourceDetailItemId(item.id);
																	}}
																	className={`mb-5 break-inside-avoid cursor-pointer overflow-hidden bg-white text-slate-900 shadow-[0_22px_60px_rgba(0,0,0,0.24)] transition hover:shadow-[0_26px_72px_rgba(0,0,0,0.32)] ${boardDeepBrowseColumnCount >= 7 ? 'mb-3' : 'mb-5'}`}
																>
																	<div className="bg-slate-100">
																		<img
																			src={item.imageSrc}
																			alt={item.title}
																			className="block h-auto w-full"
																			data-fallback-src={item.fallbackImageSrc}
																			onError={handleResourceImageError}
																		/>
																	</div>
																	<div className={isCompactDeepCard ? 'p-2' : 'p-3'}>
																		<div
																			className={`font-semibold text-slate-950 ${
																				isCompactDeepCard
																					? 'overflow-hidden text-[12px] leading-4 [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:2]'
																					: 'text-[15px] leading-6'
																			}`}
																		>
																			{item.title}
																		</div>
																		{!isCompactDeepCard && (
																			<div className="mt-1 line-clamp-1 text-[11px] leading-4 text-slate-400">{item.meta}</div>
																		)}
																	</div>
																</div>
															);
														})}
													</div>
												)}
											</div>
										</div>
									</div>
								</div>,
								document.body
							)}

							{selectedBoardCanvasItem && (
								<div className="pointer-events-none absolute z-30" style={{
									left: `${boardCanvasView.x + selectedBoardCanvasItem.x * boardCanvasView.zoom + (selectedBoardCanvasItem.width * boardCanvasView.zoom) / 2}px`,
									top: `${boardCanvasView.y + (selectedBoardCanvasItem.y + getBoardCanvasItemHeight(selectedBoardCanvasItem)) * boardCanvasView.zoom}px`,
									transform: 'translate(-50%, 18px)',
								}}>
									<div className="pointer-events-auto inline-flex min-w-[260px] max-w-[420px] flex-col gap-2 rounded-[18px] bg-black px-4 py-3 shadow-[0_14px_40px_rgba(0,0,0,0.36)]">
										<div className="flex flex-wrap items-center justify-center gap-2">
											<button
												onClick={() => removeBoardCanvasItem(selectedBoardCanvasItem.id)}
												className="rounded-full border border-rose-400/20 px-3 py-1.5 text-[12px] font-medium text-rose-200 hover:bg-rose-400/10"
											>
												移除
											</button>
											<button className="rounded-full border border-white/12 px-3 py-1.5 text-[12px] font-medium text-white/82 hover:bg-white/8">
												裁切
											</button>
											<button className="rounded-full border border-white/12 px-3 py-1.5 text-[12px] font-medium text-white/82 hover:bg-white/8">
												蒙版
											</button>
											<button
												onClick={() => toggleBoardCanvasItemDisabled(selectedBoardCanvasItem.id)}
												className={`rounded-full border px-3 py-1.5 text-[12px] font-medium ${
													selectedBoardCanvasItem.disabled
														? 'border-emerald-400/20 text-emerald-200 hover:bg-emerald-400/10'
														: 'border-amber-300/20 text-amber-100 hover:bg-amber-300/10'
												}`}
											>
												{selectedBoardCanvasItem.disabled ? '启用' : '停用'}
											</button>
										</div>
										<button
											onClick={() => {
												if (!selectedBoardCanvasReferenceControl) return;
												openReferenceEditModal('canvas', selectedBoardCanvasReferenceControl, { canvasItemId: selectedBoardCanvasItem.id });
											}}
											className="w-full rounded-full border border-sky-300/20 px-3 py-1.5 text-center text-[12px] font-medium text-sky-100 hover:bg-sky-300/10"
										>
											引用详情
										</button>
										<div className="text-center text-[11px] leading-5 text-white/62">
											<div>
												{selectedBoardCanvasReferenceControl?.label ?? (selectedBoardCanvasItem.entityType === 'insight' ? '锚点解读' : selectedBoardCanvasItem.entityType === 'anchor' ? '锚点卡' : selectedBoardCanvasItem.entityType === 'project' ? '项目包' : '单图卡')}
												{selectedBoardCanvasItem.meta ? ` · ${selectedBoardCanvasItem.meta}` : ''}
											</div>
											{selectedBoardCanvasReferenceControl && (
												<div>主参考 {selectedBoardCanvasReferenceControl.primaryRole} · {selectedBoardCanvasReferenceControl.scope}</div>
											)}
										</div>
									</div>
								</div>
							)}
							{isClient && planViewerSpace && planViewerTopic && createPortal(
								<div
									className="cockpit-shared-overlay z-[2147483647] flex items-stretch justify-stretch p-0 backdrop-blur-sm"
									onClick={() => setPlanViewerSpace(null)}
								>
									<div onClick={(event) => event.stopPropagation()} className="relative flex h-screen w-screen flex-col overflow-hidden border-0 bg-[#111] text-white shadow-[0_28px_90px_rgba(0,0,0,0.45)]">
										<div className="pointer-events-none absolute right-4 top-4 z-20 flex justify-end">
											<div className="hidden">
												<div className="text-[11px] uppercase tracking-[0.16em] text-cyan-200/58">Drawing Viewer</div>
												<div className="mt-1 text-lg font-semibold">{toDisplaySpaceName(planViewerSpace)}·平面图与空间关系</div>
												<div className="mt-1 text-sm text-white/50">{planViewerTopic.uploadedFileName ?? '尚未上传图纸'} · {planViewerTopic.sourceType.toUpperCase()} · {formatFileSize(planViewerTopic.uploadedFileSize)}</div>
											</div>
											<button onClick={() => setPlanViewerSpace(null)} className="pointer-events-auto inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/12 bg-black/44 text-white/62 backdrop-blur hover:bg-white/8 hover:text-white" aria-label="关闭图纸查看器">
												<X className="h-4 w-4" />
											</button>
										</div>
										<div className="grid min-h-0 flex-1" style={{ gridTemplateColumns: 'minmax(0, 1fr) 380px' }}>
											<div ref={planViewerCanvasRef} className="min-w-0 overflow-auto bg-[var(--canvas-bg)] p-4" onWheel={handlePlanViewerWheel}>
												<div className={`relative mx-auto min-h-[calc(100vh-32px)] w-fit ${planViewerTool === 'select' ? 'cursor-default' : 'cursor-crosshair'}`}>
													<div className="relative mx-auto w-fit transition-[width,height]">
												{planViewerTopic.uploadedFileUrl && planViewerTopic.mimeType?.startsWith('image/') ? (
													<img
														src={planViewerTopic.uploadedFileUrl}
														alt={planViewerTopic.uploadedFileName ?? '上传图纸'}
														className={`mx-auto max-w-none object-contain ${shouldShowPlanReconstructionOverlay ? 'opacity-38 grayscale' : ''}`}
														style={{
															width: `calc((100vw - 460px) * ${planViewerZoom})`,
															maxHeight: `calc((100vh - 32px) * ${Math.max(planViewerZoom, 1)})`,
														}}
													/>
												) : planViewerTopic.uploadedFileUrl && planViewerTopic.mimeType === 'application/pdf' ? (
													<PdfPlanCanvas
														src={planViewerPdfSrc}
														zoom={planViewerZoom}
														onWheel={handlePlanViewerWheel}
														className={shouldShowPlanReconstructionOverlay ? 'opacity-45 grayscale' : ''}
													/>
												) : planViewerTopic.uploadedFileUrl && planViewerTopic.sourceType === 'dxf' ? (
													<DxfPlanCanvas
														src={planViewerTopic.uploadedFileUrl}
														zoom={planViewerZoom}
														onWheel={handlePlanViewerWheel}
														className={shouldShowPlanReconstructionOverlay ? 'opacity-45 grayscale' : ''}
													/>
												) : (
													<div className="flex h-full min-h-[520px] items-center justify-center text-center">
														<div className="max-w-md">
															<div className="text-lg font-semibold text-white">{planViewerTopic.sourceType === 'cad' ? 'DWG 已保存，等待转换' : '暂无可预览图纸'}</div>
															<p className="mt-3 text-sm leading-6 text-white/56">{planViewerTopic.parseMessage ?? '上传图片、PDF 或 DXF 后可直接预览；DWG 需要转换。'}</p>
															{planViewerTopic.uploadedFileUrl && <a href={planViewerTopic.uploadedFileUrl} target="_blank" rel="noreferrer" className="mt-5 inline-flex rounded-full border border-white/16 px-4 py-2 text-sm font-medium text-white/82 hover:bg-white/8">打开原文件</a>}
														</div>
													</div>
												)}
														{renderPlanReconstructionOverlay()}
														<div className={`absolute inset-0 z-10 ${planViewerTool === 'select' ? 'pointer-events-none' : ''}`} onClick={(event) => addPlanAnnotation(planViewerSpace, event)} onWheel={handlePlanViewerWheel} aria-label="图纸标注层">
															{(planViewerTopic.annotations ?? []).map((annotation, index) => {
																const tone = getPlanAnnotationTone(annotation.kind);
																return (
																	<button
																		key={annotation.id}
																		onClick={(event) => event.stopPropagation()}
																		className="absolute inline-flex h-7 w-7 items-center justify-center rounded-full border-2 bg-black/65 text-[10px] font-semibold shadow-[0_0_0_4px_rgba(0,0,0,0.2)]"
																		style={{
																			left: `${annotation.x * 100}%`,
																			top: `${annotation.y * 100}%`,
																			borderColor: tone.color,
																			color: tone.color,
																			transform: 'translate(-50%, -50%)',
																		}}
																		title={`${tone.label} · ${annotation.label}`}
																	>
																		{index + 1}
																	</button>
																);
															})}
														</div>
													</div>
												</div>
											</div>
											<div className="min-h-0 overflow-y-auto border-l border-white/10 p-5">
												<div className="mb-5 flex items-start justify-between gap-3">
													<div>
														<div className="text-[11px] uppercase tracking-[0.16em] text-cyan-200/58">Drawing Viewer</div>
														<div className="mt-1 text-lg font-semibold">{toDisplaySpaceName(planViewerSpace)}·平面图与空间关系</div>
														<div className="mt-1 text-sm text-white/50">{planViewerTopic.uploadedFileName ?? '尚未上传图纸'} · {planViewerTopic.sourceType.toUpperCase()} · {formatFileSize(planViewerTopic.uploadedFileSize)}</div>
													</div>
												</div>
												<div className="mb-5 space-y-3">
													<div className="text-sm font-semibold">图纸工具</div>
													<div className="flex flex-wrap gap-1.5">
														{PLAN_ANNOTATION_TOOLS.map((tool) => (
															<button
																key={`board-viewer-side-tool-${tool.kind}`}
																onClick={() => setPlanViewerTool(tool.kind)}
																className={`rounded-full border px-3 py-1 text-[12px] font-medium transition ${planViewerTool === tool.kind ? 'border-cyan-200/60 bg-cyan-300/16 text-cyan-50' : 'border-white/12 text-white/58 hover:bg-white/8 hover:text-white'}`}
															>
																{tool.label}
															</button>
														))}
													</div>
													<div className="flex items-center gap-1.5">
														<button onClick={() => handlePlanViewerZoom(-0.15)} className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-white/12 text-white/62 hover:bg-white/8">-</button>
														<button onClick={() => setPlanViewerZoom(1)} className="rounded-full border border-white/12 px-3 py-1 text-[12px] text-white/62 hover:bg-white/8">适配 {Math.round(planViewerZoom * 100)}%</button>
														<button onClick={() => handlePlanViewerZoom(0.15)} className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-white/12 text-white/62 hover:bg-white/8">+</button>
													</div>
													<div className="text-[11px] leading-5 text-white/42">左侧图纸区滚动鼠标可按鼠标位置放大缩小。</div>
												</div>
												{renderPlanReconstructionPanel()}
												<div className="text-sm font-semibold">解析状态</div>
												<div className="mt-2 rounded-none border border-white/10 bg-white/[0.04] p-3 text-sm leading-6 text-white/64">{planViewerTopic.parseMessage ?? '当前图纸已作为空间图纸资产保存。'}</div>
												<div className="mt-5 flex items-center justify-between gap-3">
													<div className="text-sm font-semibold">图纸标注</div>
													<div className="text-[11px] text-white/42">{(planViewerTopic.annotations ?? []).length} 个</div>
												</div>
												<div className="mt-2 space-y-2">
													{(planViewerTopic.annotations ?? []).length > 0 ? (planViewerTopic.annotations ?? []).map((annotation, index) => {
														const tone = getPlanAnnotationTone(annotation.kind);
														return (
															<div key={`board-viewer-annotation-${annotation.id}`} className="rounded-none border border-white/10 bg-white/[0.04] p-3">
																<div className="flex items-start justify-between gap-2">
																	<div>
																		<div className="text-[12px] font-semibold text-white">{String(index + 1).padStart(2, '0')} {annotation.label}</div>
																		<div className="mt-1 text-[11px] text-white/45">{tone.label} · x {Math.round(annotation.x * 100)}% / y {Math.round(annotation.y * 100)}%</div>
																	</div>
																	<button onClick={() => removePlanAnnotation(planViewerSpace, annotation.id)} className="rounded-full border border-white/12 px-2 py-0.5 text-[11px] text-white/52 hover:bg-white/8">删除</button>
																</div>
															</div>
														);
													}) : (
														<div className="rounded-none border border-dashed border-white/12 p-3 text-[12px] leading-5 text-white/45">选择上方工具后，在图纸上点击即可添加空间点位。标注会随该空间保存，并作为 Plan Base 的图纸依据。</div>
													)}
												</div>
												{planViewerTopic.parsedLayers && planViewerTopic.parsedLayers.length > 0 && (
													<>
														<div className="mt-5 text-sm font-semibold">DXF 图层</div>
														<div className="mt-2 flex max-h-40 flex-wrap gap-1.5 overflow-y-auto">
															{planViewerTopic.parsedLayers.map((layer) => <span key={`board-viewer-layer-${layer}`} className="rounded-full bg-white/8 px-2 py-0.5 text-[11px] text-white/62">{layer}</span>)}
														</div>
													</>
												)}
												{planViewerTopic.parsedEntityCounts && Object.keys(planViewerTopic.parsedEntityCounts).length > 0 && (
													<div className="mt-5 space-y-1.5 text-xs text-white/62">
														{Object.entries(planViewerTopic.parsedEntityCounts).map(([type, count]) => (
															<div key={`board-viewer-entity-${type}`} className="flex justify-between border-b border-white/8 pb-1"><span>{type}</span><span>{count}</span></div>
														))}
													</div>
												)}
												<div className="mt-6 flex flex-wrap gap-2">
													<button onClick={() => openPlanUploadPicker(planViewerSpace)} className="rounded-full border border-white/14 px-3 py-1.5 text-[12px] font-medium text-white/74 hover:bg-white/8">替换图纸</button>
												</div>
											</div>
										</div>
									</div>
								</div>,
								document.body
							)}
							{isClient && referenceEditDraft && createPortal(
								<div
									className="cockpit-shared-overlay z-[2147483648] flex items-center justify-center p-6 backdrop-blur-sm"
									onClick={() => setReferenceEditDraft(null)}
								>
									<div onClick={(event) => event.stopPropagation()} className="cockpit-modal-shell cockpit-modal-width">
										<div className="max-h-[84vh] overflow-y-auto p-6">
											<div className="mb-6 flex items-start justify-between gap-4">
												<div>
													<div className="ui-type-meta font-medium uppercase tracking-[0.2em] text-sky-600">Reference Control</div>
													<h4 className="ui-type-title mt-2 font-semibold text-slate-900">{referenceEditDraft.control.label}</h4>
													<p className="ui-type-body mt-2 text-slate-500">这些文字会作为图片参考的控制层进入方案画布生图上下文。</p>
												</div>
												<button
													onClick={() => setReferenceEditDraft(null)}
													className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 text-slate-500 hover:border-slate-300 hover:text-slate-700"
													aria-label="关闭引用详情"
												>
													<X className="h-5 w-5" />
												</button>
											</div>
											<div className="grid gap-4 md:grid-cols-2">
												<label className="block">
													<div className="ui-type-meta mb-2 text-slate-500">类型</div>
													<select
														value={referenceEditDraft.control.kind}
														onChange={(event) => {
															const kind = event.target.value as BoardReferenceKind;
															updateReferenceEditControl({
																kind,
																scope: kind === 'project_pack' ? 'global' : kind === 'scene_card' ? 'scene' : kind === 'detail_card' ? 'detail' : 'relation',
																label: getBoardReferenceLabel(kind),
															});
														}}
														className="cockpit-search-input"
													>
														<option value="project_pack">项目参考包</option>
														<option value="scene_card">场景参考图</option>
														<option value="detail_card">局部锚点卡</option>
														<option value="relation_card">关系参考组</option>
													</select>
												</label>
												<label className="block">
													<div className="ui-type-meta mb-2 text-slate-500">权重</div>
													<select value={referenceEditDraft.control.weight} onChange={(event) => updateReferenceEditControl({ weight: event.target.value as BoardReferenceWeight })} className="cockpit-search-input">
														<option value="low">低</option>
														<option value="medium">中</option>
														<option value="high">高</option>
													</select>
												</label>
												<label className="block">
													<div className="ui-type-meta mb-2 text-slate-500">主参考</div>
													<input value={referenceEditDraft.control.primaryRole} onChange={(event) => updateReferenceEditControl({ primaryRole: event.target.value })} className="cockpit-search-input" />
												</label>
												<label className="block">
													<div className="ui-type-meta mb-2 text-slate-500">次参考</div>
													<input value={referenceEditDraft.control.secondaryRole ?? ''} onChange={(event) => updateReferenceEditControl({ secondaryRole: event.target.value })} className="cockpit-search-input" />
												</label>
											</div>
											<div className="mt-4 grid gap-4 md:grid-cols-2">
												<label className="block">
													<div className="ui-type-meta mb-2 text-slate-500">必须保留</div>
													<textarea value={referenceEditDraft.control.mustHave.join('、')} onChange={(event) => updateReferenceEditControl({ mustHave: uniqueList(event.target.value.split(/[，,、\n]/), 10) })} rows={4} className="min-h-[112px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-sky-400" />
												</label>
												<label className="block">
													<div className="ui-type-meta mb-2 text-slate-500">禁止带入</div>
													<textarea value={referenceEditDraft.control.negative.join('、')} onChange={(event) => updateReferenceEditControl({ negative: uniqueList(event.target.value.split(/[，,、\n]/), 10) })} rows={4} className="min-h-[112px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-sky-400" />
												</label>
											</div>
											<label className="mt-4 block">
												<div className="ui-type-meta mb-2 text-slate-500">结构化说明</div>
												<textarea value={referenceEditDraft.control.structuredSummary} onChange={(event) => updateReferenceEditControl({ structuredSummary: event.target.value })} rows={4} className="min-h-[120px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-sky-400" />
											</label>
											<label className="mt-4 block">
												<div className="ui-type-meta mb-2 text-slate-500">绑定目标 / 关系逻辑</div>
												<textarea
													value={referenceEditDraft.control.relationshipLogic ?? referenceEditDraft.control.bindTo ?? ''}
													onChange={(event) => {
														if (referenceEditDraft.control.kind === 'relation_card') updateReferenceEditControl({ relationshipLogic: event.target.value });
														else updateReferenceEditControl({ bindTo: event.target.value });
													}}
													rows={3}
													className="min-h-[96px] w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-sky-400"
												/>
											</label>
											<div className="mt-6 flex flex-wrap justify-end gap-3">
												<button onClick={() => setReferenceEditDraft(null)} className="ui-type-meta rounded-full border border-slate-200 px-5 py-2 font-medium text-slate-600 hover:bg-slate-50">取消</button>
												<button onClick={saveReferenceEditDraft} className="ui-type-meta rounded-full bg-slate-900 px-5 py-2 font-medium text-white hover:bg-slate-800">
													{referenceEditDraft.target === 'source' ? '保存并加入画布' : '保存引用详情'}
												</button>
											</div>
										</div>
									</div>
								</div>,
								document.body
							)}
									</>
								)}
							</div>
						</div>
					</div>
				);

			case 'experts':
				return (
					<div className="cockpit-panel-root w-full h-full flex flex-col overflow-hidden bg-[#226fc0] text-white">
						<div className="border-b border-black/8 bg-[#226fc0]/96 backdrop-blur pl-20 pr-6 py-4">
							<div
								className="flex flex-col gap-3"
								onMouseEnter={() => setExpertHeaderHovered(true)}
								onMouseLeave={() => setExpertHeaderHovered(false)}
							>
								<div className="cockpit-header-row">
									<div className="cockpit-header-main">
										<h3 className="cockpit-panel-title text-white">梦幻团队</h3>
										<span className="cockpit-header-note text-slate-300">超级智囊团</span>
										<button
											onClick={() => setExpertHeaderCollapsed((prev) => !prev)}
											className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-white/15 bg-white/5 text-white/65 transition hover:border-white/30 hover:text-white"
											aria-label={expertHeaderCollapsed ? '持续展开头部功能' : '收起头部功能'}
											title={expertHeaderCollapsed ? '持续展开头部功能' : '收起头部功能'}
										>
											<ChevronDown className={`h-4 w-4 transition-transform ${expertHeaderExpanded ? 'rotate-180' : ''}`} />
										</button>
									</div>
									<input
										value={expertQuery}
										onChange={(e) => setExpertQuery(e.target.value)}
										placeholder="搜索角色、任务、专题或冻结检查项"
										className="cockpit-search-input cockpit-header-search"
									/>
								</div>

								<div
									className={`grid overflow-hidden transition-[grid-template-rows,opacity,transform] duration-200 ease-out ${
										expertHeaderExpanded ? 'grid-rows-[1fr] opacity-100 translate-y-0' : 'pointer-events-none grid-rows-[0fr] -translate-y-1 opacity-0'
									}`}
								>
									<div className="space-y-3 overflow-hidden pt-2">
										<div className="max-w-3xl">
											<p className="ui-type-body text-white/60">
												根据项目高参旅程脚本，把高参过程收成四段：团队组建、任务安排、专题汇报、成果审阅。
											</p>
										</div>

										<div className="flex flex-wrap items-center gap-2">
											<span className="cockpit-card-chip cockpit-card-chip-accent">
												{EXPERT_WORKSPACE_TABS.find((tab) => tab.key === expertView)?.label}
											</span>
										</div>

										<div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
											<div className="flex items-center gap-2">
												<button
													onClick={() => onCardClick?.('创建自定义角色')}
													className="cockpit-card-action ui-type-meta px-4 py-2"
												>
													创建自定义角色
												</button>
												<button
													onClick={() => setShowExpertAdvanced((prev) => !prev)}
													className="cockpit-card-action inline-flex items-center gap-2 self-start xl:self-auto"
												>
													高级操作
													<ChevronDown className={`h-4 w-4 transition-transform ${showExpertAdvanced ? 'rotate-180' : ''}`} />
												</button>
											</div>
										</div>

										<div className="flex flex-wrap items-center gap-2">
											{EXPERT_WORKSPACE_TABS.map((tab) => (
												<button
													key={tab.key}
													onClick={() => setExpertView(tab.key)}
													className={`cockpit-filter-pill ${
														expertView === tab.key
															? 'cockpit-filter-pill-active'
															: ''
													}`}
													title={tab.desc}
												>
													{tab.label}
												</button>
											))}
										</div>

										<div className="rounded-none border border-white/10 bg-white/5 px-4 py-3">
											<div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
												<div>
													<div className="ui-type-meta text-white/45">当前流程段</div>
													<div className="ui-type-subtitle mt-1 font-medium text-white">
														{EXPERT_WORKSPACE_TABS.find((tab) => tab.key === expertView)?.label}
													</div>
												</div>
												<div className="ui-type-body text-white/65">{EXPERT_VIEW_SUMMARY[expertView]}</div>
											</div>
										</div>

										{showExpertAdvanced && (
											<div className="rounded-none border border-white/10 bg-white/5 px-4 py-4">
												<div className="mt-4 flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
													<div className="ui-type-body text-white/65">
														<span className="font-medium text-white">显示控制</span>
														<span className="mx-2 text-white/20">/</span>
														默认只露出必要操作，额外筛选都收在这里。
													</div>
													<div className="flex flex-wrap items-center gap-2">
														<button
															onClick={() => setExpertOnlyKeyItems((prev) => !prev)}
															className={`cockpit-filter-pill cockpit-card-accent-experts ${expertOnlyKeyItems ? 'cockpit-filter-pill-accent' : ''}`}
														>
															只看关键项
														</button>
														<button
															onClick={() => setExpertShowReserve((prev) => !prev)}
															className={`cockpit-filter-pill cockpit-card-accent-experts ${expertShowReserve ? 'cockpit-filter-pill-accent' : ''}`}
														>
															显示储备位
														</button>
													</div>
												</div>
											</div>
										)}
									</div>
								</div>
							</div>
						</div>

						<div className="flex-1 min-h-0 overflow-y-auto pl-20 pr-6 py-6">
							<div className="space-y-6 pb-4">
								{expertView === 'assembly' && (
									<>
										{expertTeamSections.length === 0 ? (
											<div className="cockpit-empty">当前筛选下没有可显示的团队角色。</div>
										) : (
											expertTeamSections.map((section) => (
												<section key={section.id} className="space-y-3">
													<div className="flex items-center justify-between">
														<div>
															<div className="ui-type-meta text-white/45">{section.eyebrow}</div>
															<h4 className="ui-type-subtitle mt-1 font-semibold text-white">{section.label}</h4>
														</div>
													</div>
													<div className="flex flex-wrap gap-x-6 gap-y-8">
														{section.items.map((item) => renderExpertTeamCard(item))}
													</div>
												</section>
											))
										)}
									</>
								)}

								{expertView === 'tasks' && (
									expertTaskSections.length === 0 ? (
										<div className="cockpit-empty">当前筛选下没有任务卡。</div>
									) : (
										expertTaskSections.map((section) => (
											<section key={section.id} className="space-y-3">
												<div className="flex items-center justify-between">
													<div>
														<div className="ui-type-meta text-white/45">{section.eyebrow}</div>
														<h4 className="ui-type-subtitle mt-1 font-semibold text-white">{section.label}</h4>
													</div>
												</div>
												<div className="cockpit-adaptive-grid cockpit-grid-experts">
													{section.items.map((item) => renderExpertTaskCard(item))}
												</div>
											</section>
										))
									)
								)}

								{expertView === 'reports' && (
									expertReportItems.length === 0 ? (
										<div className="cockpit-empty">当前筛选下没有专题汇报内容。</div>
									) : (
										<section className="space-y-3">
											<div className="flex items-center justify-between">
												<div>
													<div className="ui-type-meta text-white/45">4.3 汇总确认</div>
													<h4 className="ui-type-subtitle mt-1 font-semibold text-white">专题策略确认</h4>
												</div>
											</div>
											<div className="cockpit-adaptive-grid cockpit-grid-experts">
												{expertReportItems.map((item) => renderExpertReportCard(item))}
											</div>
										</section>
									)
								)}

								{expertView === 'review' && (
									expertReviewItems.length === 0 ? (
										<div className="cockpit-empty">当前筛选下没有成果审阅内容。</div>
									) : (
										<section className="space-y-3">
											<div className="flex items-center justify-between">
												<div>
													<div className="ui-type-meta text-white/45">4.4 最终复核</div>
													<h4 className="ui-type-subtitle mt-1 font-semibold text-white">成果审阅与冻结</h4>
												</div>
											</div>
											<div className="cockpit-adaptive-grid cockpit-grid-experts">
												{expertReviewItems.map((item) => renderExpertReviewCard(item))}
											</div>
										</section>
									)
								)}
							</div>
						</div>

						{isClient && selectedExpertDetail && selectedExpertDetailData && expertDetailViewModel && createPortal(
							<div
								className="cockpit-readable-overlay z-[2147483646]"
								onClick={closeExpertDetail}
							>
								<div
									onClick={(e) => e.stopPropagation()}
									className="cockpit-readable-overlay-shell"
								>
									<button
										onClick={closeExpertDetail}
										className="cockpit-readable-overlay-close"
										aria-label="关闭详情"
									>
										<X className="h-5 w-5" />
									</button>

									<div className="flex min-h-screen flex-col">
										<div className="bg-[#161616] px-6 py-5 text-white lg:px-10">
											<div className="cockpit-modal-readable mx-auto pr-14">
												<div className="ui-type-meta text-white/55">{expertDetailViewModel.eyebrow} · Esc 可退出</div>
												<h4 className="mt-3 text-[30px] font-semibold tracking-[-0.03em] text-white">{expertDetailViewModel.title}</h4>
												<p className="ui-type-body mt-3 max-w-3xl text-white/72">{expertDetailViewModel.summary}</p>
											</div>
										</div>

										<div className="flex-1">
											<div className="cockpit-modal-readable mx-auto grid w-full gap-6 px-0 pb-12 pt-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)] lg:pb-16">
												<div className="space-y-6">
													<div className="border border-white/10 bg-white p-6">
														{'avatarName' in selectedExpertDetailData && (
															<div className="mb-6">
																<img
																	src={buildAdvisorAvatarUrl(selectedExpertDetailData.avatarName)}
																	alt={selectedExpertDetailData.title}
																	className="h-32 w-32 rounded-full object-cover object-center"
																/>
															</div>
														)}

														<div className="grid gap-4 md:grid-cols-2">
															{expertDetailViewModel.primaryMeta.map((meta) => (
																<div key={`${expertDetailViewModel.title}-${meta.label}`} className="cockpit-modal-card">
																	<div className="ui-type-meta text-slate-500">{meta.label}</div>
																	<div className="ui-type-subtitle mt-2 font-semibold text-slate-900">{meta.value}</div>
																</div>
															))}
														</div>
													</div>

													<div className="space-y-5">
														{expertDetailViewModel.sections.map((section) => (
															<div key={`${expertDetailViewModel.title}-${section.title}`} className="border border-white/10 bg-white p-6">
																<div className="ui-type-subtitle font-semibold text-slate-900">{section.title}</div>
																<div className="ui-type-body mt-3 space-y-2 text-slate-600">
																	{section.items.map((entry) => (
																		<div key={`${section.title}-${entry}`}>{entry}</div>
																	))}
																</div>
															</div>
														))}
													</div>
												</div>

												<div className="space-y-6">
													<div className="border border-white/10 bg-white p-6">
														<div className="ui-type-meta text-slate-500">当前流程段</div>
														<div className="ui-type-subtitle mt-2 font-semibold text-slate-900">
															{EXPERT_WORKSPACE_TABS.find((tab) => tab.key === expertView)?.label}
														</div>
														<div className="mt-6 ui-type-meta text-slate-500">详情类型</div>
														<div className="ui-type-subtitle mt-2 font-semibold text-slate-900">
															{selectedExpertDetail.kind === 'role'
																? '团队角色'
																: selectedExpertDetail.kind === 'task'
																	? '任务安排'
																	: selectedExpertDetail.kind === 'report'
																		? '专题汇报'
																		: '成果审阅'}
														</div>
													</div>

													<div className="border border-white/10 bg-white p-6">
														<div className="ui-type-meta text-slate-500">动作</div>
														<div className="mt-4 flex flex-wrap gap-2">
															<button
																onClick={() => onCardClick?.(expertDetailViewModel.title)}
																className="cockpit-card-action"
															>
																{expertDetailViewModel.actionLabel}
															</button>
														</div>
													</div>
												</div>
											</div>
										</div>
									</div>
								</div>
							</div>,
							document.body
						)}
					</div>
				);

			default:
				return <div className="ui-type-body p-4 text-[var(--foreground-secondary)]">选择一个模块查看内容</div>;
		}
	};

	return <div className={`w-full h-full flex flex-col overflow-hidden bg-[var(--background)] ${className}`}>{renderContent()}</div>;
}
