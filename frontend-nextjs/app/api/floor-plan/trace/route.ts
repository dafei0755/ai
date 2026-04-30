import { promises as fs } from 'fs';
import path from 'path';
import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

type FloorPlanElementKind = 'wall_trace' | 'door' | 'window' | 'curtain_wall' | 'function_zone' | 'column';
type TracePoint = { x: number; y: number };

// ─── 柱识别：类型系统 ────────────────────────────────────────────────────
type ColumnType =
	| 'primary_structural_column'       // 主结构柱（框架柱、独立柱）
	| 'masonry_reinforcement_pier'      // 砌体加强柱 / 构造柱 / 墙体加强构件
	| 'shear_wall_edge_pier'            // 剪力墙边缘暗柱 / 墙肢式节点
	| 'encased_or_interior_column'      // 室内包柱 / 装饰包覆后的柱
	| 'column_candidate_unverified';    // 未验证候选

type ColumnShape = 'square' | 'rect' | 'circular' | 'l_shape' | 't_shape' | 'irregular';

type ColumnRemovability =
	| 'non_removable'
	| 'likely_removable'
	| 'conditional'
	| 'unknown';

type StructuralPriority = 'primary' | 'secondary' | 'interior_only' | 'unknown';

type ColumnCandidateSource =
	| 'rect_closure_structured'
	| 'rect_closure_raw'
	| 'filled_rect_blob'
	| 'wall_thickness_bump'
	| 'wall_joint_probe';

type ColumnReviewFlag =
	| 'near_text_region'
	| 'weak_wall_binding'
	| 'size_outlier'
	| 'possible_false_positive'
	| 'type_conflict'
	| 'needs_structural_review';

interface ColumnVerification {
	columnType: ColumnType;
	shape: ColumnShape;
	removability: ColumnRemovability;
	structuralPriority: StructuralPriority;
	/** 位置角色：独立柱 / 嵌墙柱 / 边带柱（基于与墙脊线关系的两步分类） */
	positionRole: 'isolated' | 'embedded' | 'perimeter' | 'unknown';
	confidence: number;
	evidence: {
		geometry: number;
		wallRelation: number;
		repetition: number;
		jointProximity: number;
		gridIntersection: number;
	};
	sourceMethod: ColumnCandidateSource[];
	reviewFlags: ColumnReviewFlag[];
}

// ─── 墙識別：类型系统 ────────────────────────────────────────────────────
type WallStructuralRole =
	| 'primary_structural_wall'         // 承重墙（含砖混/砌体主力墙）
	| 'shear_wall'                      // 剪力墙（RC 核心筒/抗侧力）— v1 合并到 primary, v2 升格
	| 'enclosure_wall'                  // 外墙 / 围护墙
	| 'partition_wall'                  // 普通隔墙（砌体/板材）
	| 'light_partition'                 // 轻质隔断（轻钢龙骨/玻璃/可移动）
	| 'parapet_wall'                    // 女儿墙 / 矮墙（外墙顶部短墙）
	| 'railing_line'                    // 栏杆线（阳台/露台护栏）
	| 'wall_candidate_unverified';      // 未验证候选

type WallRemovability =
	| 'non_removable'
	| 'likely_removable'
	| 'conditional'
	| 'unknown';

type InteriorActionHint =
	| 'wrap'
	| 'embed_storage'
	| 'limited_opening_only'
	| 'avoid_demolition'
	| 'can_repartition'
	| 'needs_structural_review';

type WallReviewFlag =
	| 'wall_type_unresolved'
	| 'annotation_contamination'
	| 'thickness_outlier'
	| 'grid_inconsistent'
	| 'dangling_no_joint'
	| 'needs_structural_review';

interface WallVerification {
	structuralRole: WallStructuralRole;
	removability: WallRemovability;
	interiorActionHints: InteriorActionHint[];
	confidence: number;
	evidence: {
		thickness: number;
		connectivity: number;
		axisAlignment: number;
		envelope: number;
		lineWidth: number;
		continuity: number;
	};
	reviewFlags: WallReviewFlag[];
}

// ─── 開口識別：类型系统 ────────────────────────────────────────────────────
type OpeningType =
	| 'swing_door'                      // 单平开门（弧 + 门扇直线 + 铰点验证）
	| 'double_swing_door'               // 双平开门（对称弧配对）
	| 'sliding_door'                    // 推拉门（墙 gap + 沿墙 dashPattern 段）
	| 'void_passage'                    // 无门扇门洞（纯墙 gap，无附属符号）
	| 'opening_candidate_unverified';   // 未验证候选

type SwingDirection =
	| 'left_inward' | 'right_inward'
	| 'left_outward' | 'right_outward'
	| 'unknown';

type OpeningRemovability =
	| 'relocatable'          // 可移位（隔墙上的门）
	| 'width_adjustable'     // 可加宽（围护墙，需审批）
	| 'type_changeable'      // 可改门型但洞口不可动（承重墙）
	| 'fixed'                // 不可调整（消防门 / 结构关键位置）
	| 'unknown';

type OpeningReviewFlag =
	| 'arc_quality_low'
	| 'no_leaf_binding'
	| 'host_wall_unbound'
	| 'size_non_compliant'
	| 'type_conflict'
	| 'possible_false_positive'
	| 'needs_manual_review';

interface OpeningVerification {
	openingType: OpeningType;
	swingDirection: SwingDirection;
	removability: OpeningRemovability;
	hostWallId?: string;
	hostWallRole?: WallStructuralRole;
	confidence: number;
	evidence: {
		arcQuality: number;
		leafBinding: number;
		wallBinding: number;
		sizeCompliance: number;
		symmetry: number;
		gapEvidence: number;
	};
	reviewFlags: OpeningReviewFlag[];
}

// ─── 窗户識別：类型系统 ────────────────────────────────────────────────────
type WindowType =
	| 'fixed_window'                    // 固定窗（纯玻璃线无弧段）
	| 'casement_window'                 // 平开窗（弧段 + 玻璃线共存于墙内）
	| 'sliding_window'                  // 推拉窗（交错平行线模式）
	| 'ribbon_window'                   // 带形窗（连续玻璃线跨度 > 2400mm）
	| 'window_candidate_unverified';    // 未验证候选

type WindowRemovability =
	| 'replaceable'          // 可更换窗型（普通窗在非承重墙/围护墙上）
	| 'frame_adjustable'     // 可调整窗框尺寸（隔墙上的窗）
	| 'type_changeable'      // 可换型（固定→推拉）
	| 'fixed'                // 不可改动（幕墙段、承重墙上）
	| 'unknown';

type WindowReviewFlag =
	| 'glass_line_quality_low'
	| 'host_wall_unbound'
	| 'size_non_compliant'
	| 'curtain_wall_conflict'
	| 'possible_false_positive'
	| 'needs_manual_review';

interface WindowVerification {
	windowType: WindowType;
	removability: WindowRemovability;
	hostWallId?: string;
	hostWallRole?: WallStructuralRole;
	confidence: number;
	evidence: {
		glassLineQuality: number;    // 玻璃线组质量（线数、平行度、间距一致性）
		wallBinding: number;         // 宿主墙绑定精度
		sizeCompliance: number;      // 宽度在合理范围内
		arcPresence: number;         // 开启弧段存在（平开窗正信号）
		overlapPattern: number;      // 交错重叠模式（推拉窗正信号）
		curtainWallExclusion: number; // 幕墙排除分（越高越不像幕墙 → 越像窗）
	};
	reviewFlags: WindowReviewFlag[];
}

// ─── 幕墙識別：类型系统 ────────────────────────────────────────────────────
type CurtainWallType =
	| 'frame_curtain_wall'              // 框架式幕墙（竖挺+横挺分格明显）
	| 'full_glass_curtain_wall'         // 全玻幕墙 / 大面玻璃（无明显竖挺）
	| 'curtain_wall_candidate_unverified'; // 未验证候选

type CurtainWallReviewFlag =
	| 'low_repetition'
	| 'narrow_span'
	| 'host_wall_ambiguous'
	| 'needs_manual_review';

interface CurtainWallVerification {
	curtainWallType: CurtainWallType;
	confidence: number;
	hasOperablePanels: boolean;
	evidence: {
		envelopeContinuity: number;   // 围护连续性（跨度宽度/玻璃线连续度）
		mullionRepetition: number;    // 竖挺重复模式（等间距短线段）
		hostWallIndependence: number; // 宿主墙独立性（该区域无厚墙 → 高分）
		spanWidth: number;            // 跨度分（> 3m → 高分）
	};
	reviewFlags: CurtainWallReviewFlag[];
}

// ─── 空间区域识别：类型系统（电梯/楼梯/管井/设备间/核心筒）──────────────
type ZoneType =
	| 'elevator'                     // 客梯
	| 'freight_elevator'             // 货梯
	| 'fire_staircase'               // 消防楼梯 / 防烟楼梯
	| 'building_staircase'           // 建筑楼梯（结构楼梯）
	| 'interior_staircase'           // 室内楼梯（可修改）
	| 'plumbing_shaft'               // 水管井
	| 'electrical_shaft'             // 强/弱电井
	| 'ventilation_shaft'            // 风井
	| 'general_shaft'                // 综合管井
	| 'electrical_room'              // 配电间
	| 'mechanical_room'              // 机房 / 水泵房
	| 'general_equipment_room'       // 设备间（通用）
	| 'balcony'                      // 封闭阳台（单房间延伸）
	| 'open_balcony'                 // 开放阳台（三面护栏）
	| 'terrace'                      // 露台 / 平台（大面积、可多房间共享）
	| 'zone_candidate_unverified';   // 未验证

type StairOrigin =
	| 'architectural_stair'          // 建筑楼梯（结构，不可移动）
	| 'secondary_fitout_stair'       // 二次装修楼梯（可调整）
	| 'fire_stair'                   // 消防楼梯（强制固定）
	| 'unknown';

type ZoneRemovability =
	| 'hard_fixed'                   // 不可移动（消防楼梯、电梯）
	| 'constrained'                  // 受限（建筑楼梯、主管井）
	| 'adjustable'                   // 可调整（设备间位置）
	| 'interior_wrappable'           // 可包裹装饰（室内楼梯）
	| 'unknown';

type ZoneReviewFlag =
	| 'text_binding_weak'
	| 'size_non_compliant'
	| 'diagonal_cross_ambiguous'
	| 'step_pattern_weak'
	| 'stair_origin_conflict'
	| 'enclosure_incomplete'
	| 'possible_false_positive'
	| 'balcony_partial_enclosure_weak'
	| 'terrace_size_ambiguous'
	| 'needs_manual_review';

interface ZoneVerification {
	zoneType: ZoneType;
	stairOrigin?: StairOrigin;
	removability: ZoneRemovability;
	confidence: number;
	evidence: {
		// 电梯：4 维
		diagonalCross?: number;
		shaftEnclosure?: number;
		// 楼梯：5 维
		stepLinePattern?: number;
		foldbackPresence?: number;
		arrowPresence?: number;
		// 阳台/露台：5 维
		exteriorWallProximity?: number;
		partialEnclosure?: number;
		openingAttachment?: number;
		// 通用
		sizeCompliance: number;
		textBinding: number;
		wallEnclosure?: number;
	};
	textLabel?: string;
	reviewFlags: ZoneReviewFlag[];
}

interface TraceRegion {
	x: number;
	y: number;
	w: number;
	h: number;
}

type TraceCoordSpace = 'page' | 'content' | 'main_plan_box' | 'ir';

interface CoordinateProvenance {
	coordSpace: TraceCoordSpace;
	referenceBoxId: string;
	sourceContentBBox?: [number, number, number, number];
	sourcePageBBox?: [number, number, number, number];
	mainPlanBBox: [number, number, number, number];
	renderBBox?: [number, number, number, number];
}

interface TraceElement {
	id: string;
	kind: FloorPlanElementKind;
	label: string;
	geometryType: 'rect' | 'polygon' | 'path';
	x: number;
	y: number;
	w: number;
	h: number;
	points?: TracePoint[];
	widthMm?: number;
	depthMm?: number;
	areaSqm?: number;
	confidence: number;
	status: 'candidate';
	coordinateProvenance?: CoordinateProvenance;
	/** 柱专属：验证后的类型信息 */
	columnVerification?: ColumnVerification;
	/** 墙专属：验证后的类型信息 */
	wallVerification?: WallVerification;
	/** 开口专属：验证后的类型信息 */
	openingVerification?: OpeningVerification;
	/** 窗户专属：验证后的类型信息 */
	windowVerification?: WindowVerification;
	/** 幕墙专属：验证后的类型信息 */
	curtainWallVerification?: CurtainWallVerification;
	/** 空间区域专属：验证后的类型信息 */
	zoneVerification?: ZoneVerification;
}

interface TraceIssue {
	id: string;
	type:
		| 'scale_unconfirmed'
		| 'room_not_closed'
		| 'opening_unbound'
		| 'low_wall_confidence'
		| 'unsupported_source'
		| 'no_wall_candidates';
	severity: 'info' | 'warning' | 'error';
	targetIds: string[];
	message: string;
	suggestedAction: string;
}

interface FloorPlanIRWall {
	id: string;
	levelId: string;
	p1: [number, number];
	p2: [number, number];
	thickness: number;
	height: number;
	structuralRole: WallStructuralRole;
	removability: WallRemovability;
	interiorActionHints?: InteriorActionHint[];
	confidence: number;
	evidence?: {
		thickness: number;
		connectivity: number;
		axisAlignment: number;
		envelope: number;
		lineWidth: number;
		continuity: number;
	};
	source: {
		bbox: [number, number, number, number];
		method: string;
	};
	reviewFlags?: WallReviewFlag[];
}

interface FloorPlanIRRoom {
	id: string;
	name: string;
	usage: string;
	polygon: Array<[number, number]>;
	area: number;
	boundaryWallIds: string[];
	confidence: number;
	zoneType?: ZoneType;
	stairOrigin?: StairOrigin;
	removability?: ZoneRemovability;
	textLabel?: string;
	zoneEvidence?: ZoneVerification['evidence'];
}

interface FloorPlanIRCoreZone {
	id: string;
	seedElementId: string;
	memberIds: string[];
	bbox: [number, number, number, number];
	containsElevator: boolean;
	containsFireStair: boolean;
	confidence: number;
}

interface FloorPlanIRColumn {
	id: string;
	polygon: Array<[number, number]>;
	size: [number, number];
	type: ColumnType;
	shape: ColumnShape;
	removability: ColumnRemovability;
	structuralPriority: StructuralPriority;
	confidence: number;
	evidence?: {
		geometry: number;
		wallRelation: number;
		repetition: number;
		jointProximity: number;
	};
	attachedWalls?: string[];
	sourceMethod?: ColumnCandidateSource[];
	reviewFlags?: ColumnReviewFlag[];
}

interface FloorPlanIROpening {
	id: string;
	kind: 'door' | 'window';
	openingType?: OpeningType;
	windowType?: WindowType;
	swingDirection?: SwingDirection;
	wallId?: string;
	hostWallRole?: WallStructuralRole;
	removability?: OpeningRemovability | WindowRemovability;
	position: [number, number];
	width: number;
	height: number;
	confidence: number;
	evidence?: {
		arcQuality: number;
		leafBinding: number;
		wallBinding: number;
		sizeCompliance: number;
		symmetry: number;
		gapEvidence: number;
	};
	windowEvidence?: {
		glassLineQuality: number;
		wallBinding: number;
		sizeCompliance: number;
		arcPresence: number;
		overlapPattern: number;
		curtainWallExclusion: number;
	};
	source: {
		bbox: [number, number, number, number];
		method: string[];
	};
	reviewFlags?: (OpeningReviewFlag | WindowReviewFlag)[];
}

interface FloorPlanIRCurtainWall {
	id: string;
	curtainWallType: CurtainWallType;
	position: [number, number];
	spanWidth: number;
	spanHeight: number;
	hasOperablePanels: boolean;
	confidence: number;
	evidence: {
		envelopeContinuity: number;
		mullionRepetition: number;
		hostWallIndependence: number;
		spanWidth: number;
	};
	source: {
		bbox: [number, number, number, number];
		method: string[];
	};
	reviewFlags?: CurtainWallReviewFlag[];
}

interface FloorPlanIRDraft {
	version: 'floorplan_ir_v0.1';
	irId: string;
	source: {
		fileName: string;
		sourceType: 'dxf' | 'pdf';
		page: number;
		recognitionBbox: [number, number, number, number];
	};
	coordinateSystem: {
		unit: 'mm';
		origin: 'top_left';
		scale: number;
		scaleStatus: 'estimated' | 'uncalibrated';
		rotation: number;
	};
	levels: Array<{
		id: string;
		name: string;
		elevation: number;
		floorHeight: number;
	}>;
	walls: FloorPlanIRWall[];
	openings: FloorPlanIROpening[];
	curtainWalls: FloorPlanIRCurtainWall[];
	rooms: FloorPlanIRRoom[];
	coreZones: FloorPlanIRCoreZone[];
	columns: FloorPlanIRColumn[];
	texts: unknown[];
	dimensions: DimensionMark[];
	issues: TraceIssue[];
	stats: {
		wallCount: number;
		openingCount: number;
		curtainWallCount: number;
		roomCount: number;
		coreZoneCount: number;
		columnCount: number;
		issueCount: number;
	};
}

interface PrimitiveRef {
	id: string;
	kind: string;
	bbox: [number, number, number, number];
	confidence: number;
}

interface GateIssue {
	id: string;
	severity: 'info' | 'warning' | 'error';
	message: string;
	targetIds: string[];
}

interface GateResult {
	status: 'passed' | 'failed';
	score: number;
	issues: GateIssue[];
	metrics: Record<string, number>;
}

interface ReviewIssue {
	id: string;
	type: 'wall_fragment' | 'dangling_wall' | 'suspected_missing_column' | 'unbound_opening' | 'scale_issue' | 'low_confidence_space'
		| 'wall_type_unresolved' | 'wall_grid_inconsistent' | 'wall_thickness_outlier'
		| 'opening_type_unresolved' | 'opening_host_unbound' | 'opening_false_positive'
		| 'window_type_unresolved' | 'window_host_unbound' | 'window_false_positive' | 'window_curtain_wall_conflict'
		| 'curtain_wall_type_unresolved' | 'curtain_wall_low_confidence'
		| 'zone_type_unresolved' | 'zone_low_confidence' | 'zone_elevator_ambiguous' | 'zone_stair_origin_conflict' | 'core_zone_incomplete'
		| 'parapet_railing_ambiguous' | 'balcony_low_confidence' | 'terrace_vs_balcony_conflict';
	severity: 'info' | 'warning' | 'error';
	message: string;
	targetIds: string[];
}

interface WallGraphDraft {
	walls: Array<{
		wallId: string;
		centerline: [TracePoint, TracePoint];
		thickness: number;
		confidence: number;
		joints: string[];
		sourceRefs: string[];
	}>;
	joints: Array<{ jointId: string; point: TracePoint; wallIds: string[]; type: 'L' | 'T' | 'cross' | 'endpoint' }>;
	thicknessClusters: number[];
	danglingWallIds: string[];
	fragmentGroups: string[][];
}

interface FloorPlanCompileResult {
	status: 'candidate_ready' | 'gate_failed' | 'ir_ready';
	baseline: {
		inputType: 'dxf' | 'pdf' | 'raster' | 'scan';
		pageBox: TraceRegion;
		contentBox: TraceRegion;
		recognitionBox: TraceRegion;
		mainPlanBox: TraceRegion;
		mainPlanBoxSource: 'detected_plan_frame' | 'user_roi' | 'fallback_recognition_region';
		rotationDeg: number;
		scaleStatus: 'known' | 'estimated' | 'missing';
		unitGuess: 'mm' | 'px';
		noiseRegions: TraceRegion[];
		confidence: number;
	};
	detectionLayers: {
		structureLines: PrimitiveRef[];
		wallCandidates: TraceElement[];
		columnCandidates: TraceElement[];
		openingCandidates: TraceElement[];
		textRegions: PrimitiveRef[];
		dimensionRegions: PrimitiveRef[];
		gridRegions: PrimitiveRef[];
		symbolRegions: PrimitiveRef[];
		regionScopedLines?: PrimitiveRef[];
		classifiedWallLines?: PrimitiveRef[];
		focusedWallLines?: PrimitiveRef[];
		strictMergedLines?: PrimitiveRef[];
		pairedWallLines?: PrimitiveRef[];
		relaxedCandidateLines?: PrimitiveRef[];
		relaxedMergedLines?: PrimitiveRef[];
		projectionOutlines?: PrimitiveRef[];
	};
	wallGraph: WallGraphDraft;
	columns: TraceElement[];
	carrierBaseline?: CarrierBaselineIR;
	gates: {
		parser?: GateResult;
		scale?: GateResult;
		carrier?: GateResult;
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
		wallTypeIssues: ReviewIssue[];
		openingTypeIssues: ReviewIssue[];
		windowTypeIssues: ReviewIssue[];
		curtainWallIssues: ReviewIssue[];
		zoneTypeIssues: ReviewIssue[];
		coreZoneIssues: ReviewIssue[];
		edgeIssues: ReviewIssue[];
	};
	floorPlanIR?: FloorPlanIRDraft;
	formalPromotionAllowed?: boolean;
	promotionBlockers?: string[];
}

interface TraceSegment {
	x1: number;
	y1: number;
	x2: number;
	y2: number;
	score: number;
	source: 'dxf' | 'pdf';
	layer?: string;
	lineWidth?: number;
	pathKind?: 'line' | 'curve' | 'rect' | 'filledRect' | 'filledPolygon';
	/** filledPolygon 时的原始顶点列表（归一化坐标） */
	polygonPoints?: { x: number; y: number }[];
	dashPattern?: 'solid' | 'dashed' | 'dash_dot' | 'dotted';
	wallThicknessNorm?: number;
	classification?: 'wall' | 'dimension' | 'hatch' | 'symbol' | 'opening_symbol' | 'noise' | 'projection';
}

// ─── 文字分类系统 ────────────────────────────────────────────────────
type TextSemanticRole =
	| 'dimension'
	| 'axis_label'
	| 'room_name'
	| 'elevation'
	| 'scale_text'
	| 'title_block'
	| 'unknown';

interface ClassifiedText {
	text: string;
	role: TextSemanticRole;
	x: number;
	y: number;
	width: number;
	height: number;
	confidence: number;
}

// ─── 闭合圆检测 ────────────────────────────────────────────────────
interface DetectedCircle {
	center: [number, number];
	radiusNorm: number;
	radiusMm: number;
	closureGap: number;
	segmentIndices: number[];
	/** 根据半径推断的用途 */
	probableRole: 'axis_label_circle' | 'index_circle' | 'north_arrow_circle' | 'unknown_circle';
}

// ─── 轴线 / Grid Prior 系统 ────────────────────────────────────────
type GridAxisDirection = 'horizontal' | 'vertical';

interface GridAxis {
	id: string;
	direction: GridAxisDirection;
	line: [[number, number], [number, number]];
	label?: string;
	confidence: number;
}

interface GridIntersection {
	id: string;
	point: [number, number];
	axisIds: [string, string];
	confidence: number;
}

interface GridSpacingCluster {
	direction: GridAxisDirection;
	spacingMm: number;
	count: number;
}

interface ProbableColumnNode {
	point: [number, number];
	source: 'axis_intersection' | 'repeat_pattern';
	linkedIntersectionId?: string;
	confidence: number;
}

interface WallAlignmentBand {
	axisId: string;
	direction: GridAxisDirection;
	offsetNorm: number;
	confidence: number;
}

interface GridPriorOutput {
	dominantDirections: number[];
	axes: GridAxis[];
	intersections: GridIntersection[];
	spacingClusters: GridSpacingCluster[];
	probableColumnNodes: ProbableColumnNode[];
	wallAlignmentBands: WallAlignmentBand[];
}

interface DimensionMark {
	value: number;
	x: number;
	y: number;
}

interface TraceParseResult {
	segments: TraceSegment[];
	dimensions: DimensionMark[];
	contentBox?: TraceRegion;
	classifiedTexts?: ClassifiedText[];
	detectedCircles?: DetectedCircle[];
	/**
	 * Y轴物理比例 / X轴物理比例。
	 * 坐标系对 X 用 viewport.width、对 Y 用 viewport.height 分别归一化，
	 * 导致同一段 mmPerNormalized（来自水平标注）不能直接用于 Y 方向尺寸。
	 * 应用：depthMm_correct = depthMm × pageAspectYX
	 */
	pageAspectYX?: number;
	/** PDF 解析诊断数据（仅 DEBUG 用，不进 IR） */
	parserDiag?: {
		pathFillSetSize: number;
		paintSolidColorImageMaskCount: number;
		operatorListLength: number;
		filledRectTotal: number;
		filledRectNormSizeCount: number; // 尺寸在柱范围内
		filledRectOversizeCount: number; // 超大（合并块）
	};
}

const UPLOAD_DIR = path.join(process.cwd(), '.uploads', 'plan-drawings');
const TRACE_SUPPORTED_EXTENSIONS = new Set(['.dxf', '.pdf']);
const MAX_TRACE_FILE_BYTES = 100 * 1024 * 1024;

const isRecord = (value: unknown): value is Record<string, unknown> =>
	typeof value === 'object' && value !== null;

const getSafeFileName = (fileUrl: string) => {
	const url = new URL(fileUrl, 'http://local');
	const file = url.searchParams.get('file') ?? path.basename(url.pathname);
	if (!file) throw new Error('Missing drawing file reference.');
	// Decode URL-encoded characters (especially for Chinese characters)
	const decodedFile = decodeURIComponent(file);
	const safeName = path.basename(decodedFile);
	if (safeName !== decodedFile) throw new Error('Invalid drawing file reference.');
	return safeName;
};

const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value));
const finiteNumber = (value: unknown, fallback: number) => {
	const parsed = Number(value);
	return Number.isFinite(parsed) ? parsed : fallback;
};
const isUnitFullRegion = (region: TraceRegion, epsilon = 1e-6) =>
	Math.abs(region.x) <= epsilon &&
	Math.abs(region.y) <= epsilon &&
	Math.abs(region.w - 1) <= epsilon &&
	Math.abs(region.h - 1) <= epsilon;

const normalizeRegion = (region?: Partial<TraceRegion>): TraceRegion => ({
	x: clamp(finiteNumber(region?.x, 0)),
	y: clamp(finiteNumber(region?.y, 0)),
	w: clamp(finiteNumber(region?.w, 1), 0.001, 1),
	h: clamp(finiteNumber(region?.h, 1), 0.001, 1),
});

const traceIssueMessages = (issues: TraceIssue[]) => issues.map((issue) => issue.message);

const inRegion = (segment: TraceSegment, region: TraceRegion) => {
	const cx = (segment.x1 + segment.x2) / 2;
	const cy = (segment.y1 + segment.y2) / 2;
	return cx >= region.x && cx <= region.x + region.w && cy >= region.y && cy <= region.y + region.h;
};

const dimensionInRegion = (mark: DimensionMark, region: TraceRegion) => (
	mark.x >= region.x &&
	mark.x <= region.x + region.w &&
	mark.y >= region.y &&
	mark.y <= region.y + region.h
);

const expandRegion = (region: TraceRegion, padding: number): TraceRegion => ({
	x: region.x - padding,
	y: region.y - padding,
	w: region.w + padding * 2,
	h: region.h + padding * 2,
});

const selectScaleEvidenceDimensions = (dimensions: DimensionMark[], recognitionRegion: TraceRegion, mainPlanRegion: TraceRegion) => {
	const inMainPlan = dimensions.filter((mark) => dimensionInRegion(mark, mainPlanRegion));
	if (inMainPlan.length > 0) return { dimensions: inMainPlan, source: isUnitFullRegion(mainPlanRegion) || (
		Math.abs(mainPlanRegion.x - recognitionRegion.x) < 1e-6 &&
		Math.abs(mainPlanRegion.y - recognitionRegion.y) < 1e-6 &&
		Math.abs(mainPlanRegion.w - recognitionRegion.w) < 1e-6 &&
		Math.abs(mainPlanRegion.h - recognitionRegion.h) < 1e-6
	) ? 'roi' as const : 'main_plan' as const };
	const inMainPlanMargin = dimensions.filter((mark) => dimensionInRegion(mark, expandRegion(mainPlanRegion, 0.16)));
	if (inMainPlanMargin.length > 0) return { dimensions: inMainPlanMargin, source: 'main_plan_margin' as const };
	const inRecognition = dimensions.filter((mark) => dimensionInRegion(mark, recognitionRegion));
	if (inRecognition.length > 0) return { dimensions: inRecognition, source: 'roi' as const };
	const inRecognitionMargin = dimensions.filter((mark) => dimensionInRegion(mark, expandRegion(recognitionRegion, 0.16)));
	if (inRecognitionMargin.length > 0) return { dimensions: inRecognitionMargin, source: 'roi_margin' as const };
	return { dimensions: [] as DimensionMark[], source: 'missing' as const };
};

const buildVectorScaleGuess = (segments: TraceSegment[], mainPlanRegion: TraceRegion): DimensionMark[] => {
	const structuralLengths = segments
		.map(segmentLength)
		.filter((length) => Number.isFinite(length) && length >= 0.045 && length <= 0.42)
		.sort((a, b) => a - b);
	if (structuralLengths.length < 4) return [];
	const medianLength = structuralLengths[Math.floor(structuralLengths.length / 2)];
	return [{
		value: Math.round(medianLength * 21000),
		x: mainPlanRegion.x + mainPlanRegion.w / 2,
		y: mainPlanRegion.y + mainPlanRegion.h + 0.02,
	}];
};

const segmentLength = (segment: TraceSegment) => Math.hypot(segment.x2 - segment.x1, segment.y2 - segment.y1);

// ═══════════════════════════════════════════════════════════════════════
// ─── 同轴连贯墙体组装（建筑原则实现）───────────────────────────────────
// 原则：
//   1. 同一轴线上的墙段合并为单一全跨连贯墙体（厚度一致，轨迹统一）
//   2. 门/窗洞口（间距 ≤ OPENING_GAP_MAX）是"嵌入开口"，不打断墙体
//   3. 结果墙元素的 bbox 覆盖洞口位置 → host_wall 绑定成功
// ═══════════════════════════════════════════════════════════════════════
const assembleWallStrips = (walls: TraceElement[], mmPerNormalized: number): TraceElement[] => {
	const ORIENT_RATIO = 1.5;
	const hWalls = walls.filter(w => w.w >= w.h * ORIENT_RATIO);
	const vWalls = walls.filter(w => w.h >= w.w * ORIENT_RATIO);
	const squareWalls = walls.filter(w => w.w < w.h * ORIENT_RATIO && w.h < w.w * ORIENT_RATIO);
	const TRACK_TOL = Math.max(0.010, 200 / mmPerNormalized);
	const OPENING_GAP_MAX = Math.max(0.10, 3500 / mmPerNormalized); // ≤ 3500mm 为门窗洞口

	const assembleAxisGroup = (group: TraceElement[], horiz: boolean): TraceElement[] => {
		if (group.length === 0) return [];
		const trackGroups: TraceElement[][] = [];
		[...group]
			.sort((a, b) => (horiz ? (a.y + a.h / 2) - (b.y + b.h / 2) : (a.x + a.w / 2) - (b.x + b.w / 2)))
			.forEach(w => {
				const wTrack = horiz ? w.y + w.h / 2 : w.x + w.w / 2;
				const match = trackGroups.find(g => Math.abs((horiz ? g[0].y + g[0].h / 2 : g[0].x + g[0].w / 2) - wTrack) <= TRACK_TOL);
				if (match) match.push(w); else trackGroups.push([w]);
			});
		const result: TraceElement[] = [];
		trackGroups.forEach((tg, tgIdx) => {
			const sorted = [...tg].sort((a, b) => (horiz ? a.x - b.x : a.y - b.y));
			// 代表性厚度：中位数（保证同轴厚度一致）
			const thickArr = sorted.map(w => (horiz ? w.h : w.w)).sort((a, b) => a - b);
			const medThick = thickArr[Math.floor(thickArr.length / 2)];
			// 代表性轨迹：长度加权平均（保证位置一致）
			let tLen = 0, tTrack = 0;
			sorted.forEach(w => { const l = horiz ? w.w : w.h; const t = horiz ? w.y + w.h / 2 : w.x + w.w / 2; tLen += l; tTrack += t * l; });
			const avgTrack = tLen > 0 ? tTrack / tLen : (horiz ? sorted[0].y + sorted[0].h / 2 : sorted[0].x + sorted[0].w / 2);
			let sStart = horiz ? sorted[0].x : sorted[0].y;
			let sEnd   = horiz ? sorted[0].x + sorted[0].w : sorted[0].y + sorted[0].h;
			let sConf  = sorted[0].confidence;
			let segIdx = 0;
			const flush = () => {
				const len = sEnd - sStart;
				if (len < 0.005) return;
				result.push({
					id: `wall-strip-${tgIdx}-${segIdx++}`,
					kind: 'wall_trace' as const,
					label: sConf >= 0.8 ? '结构墙' : '推断墙',
					geometryType: 'rect' as const,
					x: horiz ? sStart : avgTrack - medThick / 2,
					y: horiz ? avgTrack - medThick / 2 : sStart,
					w: horiz ? len : medThick,
					h: horiz ? medThick : len,
					widthMm: Math.round(len * mmPerNormalized),
					depthMm: Math.round(medThick * mmPerNormalized),
					confidence: sConf,
					status: 'candidate' as const,
				});
			};
			for (let i = 1; i < sorted.length; i++) {
				const w = sorted[i];
				const wStart = horiz ? w.x : w.y;
				const wEnd   = horiz ? w.x + w.w : w.y + w.h;
				const gap = wStart - sEnd;
				if (gap <= OPENING_GAP_MAX) {
					sEnd  = Math.max(sEnd, wEnd);
					sConf = Math.max(sConf, w.confidence);
				} else {
					flush();
					sStart = wStart; sEnd = wEnd; sConf = w.confidence;
				}
			}
			flush();
		});
		return result;
	};

	return [...assembleAxisGroup(hWalls, true), ...assembleAxisGroup(vWalls, false), ...squareWalls];
};

const segmentToElement = (segment: TraceSegment, index: number, mmPerNormalized = 21000): TraceElement => {
	const horizontal = isHorizontal(segment);
	const thickness = Math.max(0.0015, Math.min(0.03, segment.wallThicknessNorm ?? 0.004));
	const rawX = Math.min(segment.x1, segment.x2);
	const rawY = Math.min(segment.y1, segment.y2);
	const rawW = Math.abs(segment.x2 - segment.x1);
	const rawH = Math.abs(segment.y2 - segment.y1);
	const x = horizontal ? rawX : rawX - thickness / 2;
	const y = horizontal ? rawY - thickness / 2 : rawY;
	const w = horizontal ? Math.max(0.001, rawW) : Math.max(thickness, rawW);
	const h = horizontal ? Math.max(thickness, rawH) : Math.max(0.001, rawH);
	const kind: FloorPlanElementKind = 'wall_trace';
	const widthMm = Math.max(40, Math.round(w * mmPerNormalized));
	const depthMm = Math.max(40, Math.round(h * mmPerNormalized));
	return {
		id: `floor-ir-api-${kind}-${index}`,
		kind,
		label: `API墙线 ${index + 1}`,
		geometryType: 'rect',
		x: clamp(x),
		y: clamp(y),
		w: clamp(w, 0.001, 1),
		h: clamp(h, 0.001, 1),
		widthMm,
		depthMm,
		confidence: segment.source === 'dxf' ? 0.86 : 0.72,
		status: 'candidate',
	};
};

const rectIntersects = (a: TraceElement, b: TraceElement) => {
	const ax2 = a.x + a.w;
	const ay2 = a.y + a.h;
	const bx2 = b.x + b.w;
	const by2 = b.y + b.h;
	return Math.max(0, Math.min(ax2, bx2) - Math.max(a.x, b.x)) > 0 &&
		Math.max(0, Math.min(ay2, by2) - Math.max(a.y, b.y)) > 0;
};

const rectEdgeDistance = (a: TraceElement, b: TraceElement) => {
	const ax2 = a.x + a.w;
	const ay2 = a.y + a.h;
	const bx2 = b.x + b.w;
	const by2 = b.y + b.h;
	const dx = Math.max(0, Math.max(b.x - ax2, a.x - bx2));
	const dy = Math.max(0, Math.max(b.y - ay2, a.y - by2));
	return Math.hypot(dx, dy);
};

const isHorizontal = (segment: TraceSegment) => Math.abs(segment.y2 - segment.y1) <= Math.abs(segment.x2 - segment.x1);

const isDimensionLayer = (layer?: string) => /dim|尺寸|标注|axis|grid|轴|text|文字|title|图框|border/.test((layer ?? '').toLowerCase());
const isHatchLayer = (layer?: string) => /hatch|填充|剖面/.test((layer ?? '').toLowerCase());

const classifySegment = (segment: TraceSegment, dimensions: DimensionMark[], medianLineWidth?: number) => {
	const layer = (segment.layer ?? '').toLowerCase();
	const length = segmentLength(segment);
	if (isDimensionLayer(layer)) return 'dimension' as const;
	if (isHatchLayer(layer)) return 'hatch' as const;
	if (/wall|墙|a-wall/.test(layer)) return 'wall' as const;
	// dashPattern：点划线（轴线/剖切线）和点线统一归入 dimension，不参与墙配对
	if (segment.dashPattern === 'dash_dot') return 'dimension' as const;
	if (segment.dashPattern === 'dotted') return 'dimension' as const;
	// 虚线：中等长度（0.08~0.30）可能是阳台/露台投影轮廓线，保留为 projection；
	// 长虚线（>0.30）是标注引线/剖切线，归入 dimension
	if (segment.dashPattern === 'dashed') {
		if (length >= 0.02 && length <= 0.30) return 'projection' as const;
		return 'dimension' as const;
	}
	if (segment.pathKind === 'curve') return 'opening_symbol' as const;
	// rect/filledRect/filledPolygon 是显式矩形/多边形路径（柱轮廓或填充柱），不参与墙线配对检测
	if (segment.pathKind === 'rect' || segment.pathKind === 'filledRect' || segment.pathKind === 'filledPolygon') return 'symbol' as const;
	if (length < 0.006) return 'noise' as const;
	// PDF 自适应线宽：基于中位线宽判断，比固定阈值更健壮
	if (segment.source === 'pdf' && medianLineWidth !== undefined && medianLineWidth > 0) {
		const lw = segment.lineWidth ?? 0;
		if (lw > 0 && lw < medianLineWidth * 0.55 && length < 0.20) return 'dimension' as const;
		// 矢量PDF粗线：去掉旧上限 0.65，外墙可达 20m+（归一化 1.2+）不受长度截断
		if (lw >= medianLineWidth * 1.5 && length >= 0.010) return 'wall' as const;
		// 中等线宽（接近中位数）的极短线 → 尺寸标注/延伸线/门窗符号，不是墙
		// 适用于"全实线、无虚线、无尺寸文字"的 CAD→PDF（如 median=6 时捕获 lw∈[3.9,7.8] 且 len<0.012）
		if (lw > 0 && lw >= medianLineWidth * 0.65 && lw < medianLineWidth * 1.3 && length < 0.012) return 'dimension' as const;
	}
	// 硬截断上限提高到 0.85（≈14m @ 16667 mm/norm）；原 0.62 会把 10m 外墙全杀
	if (length > 0.85) return 'dimension' as const;
	// 线宽截断阈值降至 0.18mm：只杀真正的维度细线（0.13~0.18mm）；0.25/0.35mm 是标准墙线宽
	if (length > 0.42 && Number(segment.lineWidth ?? 0) <= 0.18) return 'dimension' as const;
	const dx = Math.abs(segment.x2 - segment.x1);
	const dy = Math.abs(segment.y2 - segment.y1);
	const maxAxis = Math.max(dx, dy);
	const minAxis = Math.min(dx, dy);
	const orthogonalRatio = minAxis / Math.max(0.0001, maxAxis);
	if (orthogonalRatio > 0.12) return length < 0.32 ? 'hatch' as const : 'symbol' as const;
	const cx = (segment.x1 + segment.x2) / 2;
	const cy = (segment.y1 + segment.y2) / 2;
	const nearDimensionText = dimensions.some((mark) => Math.hypot(mark.x - cx, mark.y - cy) < 0.045);
	if (nearDimensionText && length < 0.08) return 'dimension' as const;
	return 'wall' as const;
};

const orthogonalizeSegment = (segment: TraceSegment): TraceSegment => {
	const horizontal = isHorizontal(segment);
	return horizontal
		? { ...segment, y2: segment.y1, score: segmentLength(segment) }
		: { ...segment, x2: segment.x1, score: segmentLength(segment) };
};

const mergeCollinearSegments = (
	segments: TraceSegment[],
	options: { trackTolerance: number; gapTolerance: number; minLength: number; duplicateTolerance: number; duplicateOverlap: number; limit: number }
) => {
	const scoped = segments
		.filter((segment) => segmentLength(segment) >= 0.003)
		.map((segment): TraceSegment => {
			return orthogonalizeSegment(segment);
		})
		.sort((a, b) => b.score - a.score);

	const merged: TraceSegment[] = [];
	scoped.forEach((segment) => {
		const horizontal = isHorizontal(segment);
		const index = merged.findIndex((existing) => {
			if (horizontal !== isHorizontal(existing)) return false;
			const trackA = horizontal ? segment.y1 : segment.x1;
			const trackB = horizontal ? existing.y1 : existing.x1;
			if (Math.abs(trackA - trackB) > options.trackTolerance) return false;
			const aStart = horizontal ? Math.min(segment.x1, segment.x2) : Math.min(segment.y1, segment.y2);
			const aEnd = horizontal ? Math.max(segment.x1, segment.x2) : Math.max(segment.y1, segment.y2);
			const bStart = horizontal ? Math.min(existing.x1, existing.x2) : Math.min(existing.y1, existing.y2);
			const bEnd = horizontal ? Math.max(existing.x1, existing.x2) : Math.max(existing.y1, existing.y2);
			const overlap = Math.max(0, Math.min(aEnd, bEnd) - Math.max(aStart, bStart));
			const gap = Math.max(aStart - bEnd, bStart - aEnd, 0);
			return overlap > 0 || gap <= options.gapTolerance;
		});
		if (index >= 0) {
			const existing = merged[index];
			const track = horizontal
				? (existing.y1 * existing.score + segment.y1 * segment.score) / Math.max(0.0001, existing.score + segment.score)
				: (existing.x1 * existing.score + segment.x1 * segment.score) / Math.max(0.0001, existing.score + segment.score);
			const start = Math.min(
				horizontal ? existing.x1 : existing.y1,
				horizontal ? existing.x2 : existing.y2,
				horizontal ? segment.x1 : segment.y1,
				horizontal ? segment.x2 : segment.y2
			);
			const end = Math.max(
				horizontal ? existing.x1 : existing.y1,
				horizontal ? existing.x2 : existing.y2,
				horizontal ? segment.x1 : segment.y1,
				horizontal ? segment.x2 : segment.y2
			);
			merged[index] = horizontal
				? { ...existing, x1: start, x2: end, y1: track, y2: track, score: end - start }
				: { ...existing, x1: track, x2: track, y1: start, y2: end, score: end - start };
		} else {
			merged.push(segment);
		}
	});
	const picked: TraceSegment[] = [];
	merged
		.filter((segment) => segmentLength(segment) >= options.minLength)
		.sort((a, b) => b.score - a.score)
		.forEach((segment) => {
			const horizontal = isHorizontal(segment);
			const duplicate = picked.some((existing) => {
				if (horizontal !== isHorizontal(existing)) return false;
				const trackA = horizontal ? segment.y1 : segment.x1;
				const trackB = horizontal ? existing.y1 : existing.x1;
				if (Math.abs(trackA - trackB) > options.duplicateTolerance) return false;
				const aStart = horizontal ? Math.min(segment.x1, segment.x2) : Math.min(segment.y1, segment.y2);
				const aEnd = horizontal ? Math.max(segment.x1, segment.x2) : Math.max(segment.y1, segment.y2);
				const bStart = horizontal ? Math.min(existing.x1, existing.x2) : Math.min(existing.y1, existing.y2);
				const bEnd = horizontal ? Math.max(existing.x1, existing.x2) : Math.max(existing.y1, existing.y2);
				const overlap = Math.max(0, Math.min(aEnd, bEnd) - Math.max(aStart, bStart));
				const minLength = Math.min(aEnd - aStart, bEnd - bStart);
				return minLength > 0 && overlap / minLength > options.duplicateOverlap;
			});
			if (!duplicate) picked.push(segment);
		});
	return picked.slice(0, options.limit);
};

const segmentBounds = (segment: TraceSegment) => {
	const minX = Math.min(segment.x1, segment.x2);
	const maxX = Math.max(segment.x1, segment.x2);
	const minY = Math.min(segment.y1, segment.y2);
	const maxY = Math.max(segment.y1, segment.y2);
	return { minX, maxX, minY, maxY };
};

const boundsIntersect = (
	a: { minX: number; maxX: number; minY: number; maxY: number },
	b: { minX: number; maxX: number; minY: number; maxY: number },
	padding = 0
) => (
	a.maxX + padding >= b.minX &&
	b.maxX + padding >= a.minX &&
	a.maxY + padding >= b.minY &&
	b.maxY + padding >= a.minY
);

const mergeBounds = (
	a: { minX: number; maxX: number; minY: number; maxY: number },
	b: { minX: number; maxX: number; minY: number; maxY: number }
) => ({
	minX: Math.min(a.minX, b.minX),
	maxX: Math.max(a.maxX, b.maxX),
	minY: Math.min(a.minY, b.minY),
	maxY: Math.max(a.maxY, b.maxY),
});

const focusPrimaryPlanCluster = (segments: TraceSegment[], region: TraceRegion) => {
	if (segments.length < 48) return { segments, focused: false, componentCount: 1 };
	const probe = mergeCollinearSegments(segments, {
		trackTolerance: 0.006,
		gapTolerance: 0.025,
		minLength: 0.012,
		duplicateTolerance: 0.004,
		duplicateOverlap: 0.88,
		limit: 260,
	});
	if (probe.length < 24) return { segments, focused: false, componentCount: 1 };
	const boxes = probe.map(segmentBounds);
	const visited = new Array(probe.length).fill(false);
	const components: Array<{ indices: number[]; bounds: ReturnType<typeof segmentBounds>; length: number; h: number; v: number; score: number }> = [];
	for (let i = 0; i < probe.length; i += 1) {
		if (visited[i]) continue;
		const queue = [i];
		visited[i] = true;
		const indices: number[] = [];
		let bounds = boxes[i];
		let length = 0;
		let h = 0;
		let v = 0;
		while (queue.length > 0) {
			const current = queue.shift()!;
			indices.push(current);
			bounds = mergeBounds(bounds, boxes[current]);
			length += segmentLength(probe[current]);
			if (isHorizontal(probe[current])) h += 1;
			else v += 1;
			for (let j = 0; j < probe.length; j += 1) {
				if (visited[j]) continue;
				if (!boundsIntersect(boxes[current], boxes[j], 0.014)) continue;
				visited[j] = true;
				queue.push(j);
			}
		}
		const width = bounds.maxX - bounds.minX;
		const height = bounds.maxY - bounds.minY;
		const area = width * height;
		const balance = Math.min(h, v) / Math.max(1, Math.max(h, v));
		const countScore = Math.log1p(indices.length);
		const areaScore = Math.sqrt(Math.max(0.0001, area));
		const score = length * (0.65 + balance) * countScore * areaScore;
		if (indices.length >= 4 && area >= 0.0015 && width >= region.w * 0.08 && height >= region.h * 0.08) {
			components.push({ indices, bounds, length, h, v, score });
		}
	}
	if (components.length < 2) return { segments, focused: false, componentCount: components.length || 1 };
	const best = components.sort((a, b) => b.score - a.score)[0];
	const focusPadding = Math.max(0.08, Math.min(0.16, Math.max(region.w, region.h) * 0.14));
	const focusBounds = {
		minX: Math.max(region.x, best.bounds.minX - focusPadding),
		maxX: Math.min(region.x + region.w, best.bounds.maxX + focusPadding),
		minY: Math.max(region.y, best.bounds.minY - focusPadding),
		maxY: Math.min(region.y + region.h, best.bounds.maxY + focusPadding),
	};
	const focusedSegments = segments.filter((segment) => {
		const cx = (segment.x1 + segment.x2) / 2;
		const cy = (segment.y1 + segment.y2) / 2;
		return cx >= focusBounds.minX && cx <= focusBounds.maxX && cy >= focusBounds.minY && cy <= focusBounds.maxY;
	});
	return focusedSegments.length >= 16 && focusedSegments.length < segments.length * 0.92
		? { segments: focusedSegments, focused: true, componentCount: components.length, focusBounds }
		: { segments, focused: false, componentCount: components.length, focusBounds };
};

const buildParallelWallCenters = (segments: TraceSegment[], mmPerNormalized = 21000, limit = 160) => {
	// 关键修复：trackTolerance 与 gapTolerance 均基于物理 mm，防止高 mmPerNorm 时把双线墙两面
	// 合并进同一轨道（原 0.006 在 55567mm/norm 时 = 333mm，超过典型墙厚，消灭可配对线对）
	const mergeTrackTol = Math.max(0.0015, Math.min(0.006, 55 / mmPerNormalized));  // ≈55mm 物理
	const mergeGapTol   = Math.min(0.025, Math.max(0.010, 450 / mmPerNormalized));  // ≈300–525mm 物理
	const normalized = mergeCollinearSegments(segments, {
		trackTolerance: mergeTrackTol,
		gapTolerance: mergeGapTol,
		minLength: 0.015,
		duplicateTolerance: 0.0015,
		duplicateOverlap: 0.92,
		limit: 220,
	});
	const centers: TraceSegment[] = [];
	const groups = [
		normalized.filter(isHorizontal),
		normalized.filter((segment) => !isHorizontal(segment)),
	];
	groups.forEach((group) => {
		for (let i = 0; i < group.length; i += 1) {
			for (let j = i + 1; j < group.length; j += 1) {
				const a = group[i];
				const b = group[j];
				const horizontal = isHorizontal(a);
				const trackA = horizontal ? a.y1 : a.x1;
				const trackB = horizontal ? b.y1 : b.x1;
				const distance = Math.abs(trackA - trackB);
				// 配对距离基于实际比例尺（内墙最薄 80mm，外墙最厚 400mm）
				// 注：上限收缩至 400mm 以防止装修完成面线（距结构线 20-50mm）被误配对为超厚墙
				const minWallThickness = 80 / mmPerNormalized;
				const maxWallThickness = 400 / mmPerNormalized;
				if (distance < minWallThickness || distance > maxWallThickness) continue;
				const aStart = horizontal ? Math.min(a.x1, a.x2) : Math.min(a.y1, a.y2);
				const aEnd = horizontal ? Math.max(a.x1, a.x2) : Math.max(a.y1, a.y2);
				const bStart = horizontal ? Math.min(b.x1, b.x2) : Math.min(b.y1, b.y2);
				const bEnd = horizontal ? Math.max(b.x1, b.x2) : Math.max(b.y1, b.y2);
				const start = Math.max(aStart, bStart);
				const end = Math.min(aEnd, bEnd);
				const length = end - start;
				if (length < 0.018) continue;
				const overlapRatio = length / Math.max(0.001, Math.min(aEnd - aStart, bEnd - bStart));
				// 宽松重叠率：0.25 允许门洞两侧短墙段（门宽打断后重叠仅约30%）成功配对
				if (overlapRatio < 0.25) continue;
				const track = (trackA + trackB) / 2;
				centers.push(horizontal
					? { ...a, x1: start, x2: end, y1: track, y2: track, score: length, classification: 'wall', wallThicknessNorm: distance }
					: { ...a, x1: track, x2: track, y1: start, y2: end, score: length, classification: 'wall', wallThicknessNorm: distance });
			}
		}
	});
	if (centers.length === 0) return centers;
	// ── 装修完成面抑制 ──────────────────────────────────────────────────────────
	// 中国建筑平面图特有：结构墙外侧紧贴装修完成面线（间距 20-60mm），两者会被误配对为"超薄墙"。
	// 抑制规则：若一个配对中心线的间距 < 80mm（疑似完成面层），
	// 且在平行方向 120mm 内存在间距 ≥ 80mm 的更厚配对中心线 → 压制该薄配对，保留厚配对。
	const finishSurfaceThresholdMm = 80;
	const finishSurfaceThresholdNorm = finishSurfaceThresholdMm / mmPerNormalized;
	const finishSurfaceLookupNorm = 120 / mmPerNormalized;  // 完成面到结构墙的最大横向距离
	const suppressedFinish = new Set<number>();
	if (mmPerNormalized > 3000) { // 只在有意义的比例尺下执行
		for (let ci = 0; ci < centers.length; ci++) {
			const c = centers[ci];
			if ((c.wallThicknessNorm ?? 1) >= finishSurfaceThresholdNorm) continue; // 厚度合理，跳过
			// 判断是否存在同向、更厚的配对线在附近
			const cH = isHorizontal(c);
			const cTrack = cH ? c.y1 : c.x1;
			const hasNearStructural = centers.some((other, oi) => {
				if (oi === ci) return false;
				if (isHorizontal(other) !== cH) return false;
				const oThick = other.wallThicknessNorm ?? 1;
				if (oThick < finishSurfaceThresholdNorm) return false; // other 也是薄的，不算结构
				const oTrack = cH ? other.y1 : other.x1;
				return Math.abs(oTrack - cTrack) <= finishSurfaceLookupNorm;
			});
			if (hasNearStructural) suppressedFinish.add(ci);
		}
	}
	const filteredCenters = suppressedFinish.size > 0
		? centers.filter((_, ci) => !suppressedFinish.has(ci))
		: centers;
	if (filteredCenters.length === 0) return filteredCenters;
	// ── 等间距短线簇抑制（楼梯踏步/家具线误配对为墙）──────────────────────────
	// 判断：若 ≥4 条配对中心线，沿单轴等间距、间距偏差 < 25%，且每段长度 < 典型开间 10% → 非墙
	const stairSuppressionMin = 4;
	const stairSpacingTol = 0.25;
	const stairLenMax = Math.max(0.04, 1200 / mmPerNormalized); // 约 1.2m 为楼梯踏步最大宽度
	const suppressedStair = new Set<string>();
	const hCenters = filteredCenters.filter(isHorizontal);
	const vCenters = filteredCenters.filter((s) => !isHorizontal(s));
	for (const group of [hCenters, vCenters]) {
		if (group.length < stairSuppressionMin) continue;
		// 按起止坐标分桶（同 track 的线）
		const byTrack = new Map<string, typeof group>();
		group.forEach((s) => {
			const tk = Math.round((isHorizontal(s) ? s.y1 : s.x1) * 2000) / 2000;
			const key = String(tk);
			if (!byTrack.has(key)) byTrack.set(key, []);
			byTrack.get(key)!.push(s);
		});
		byTrack.forEach((trackGroup) => {
			if (trackGroup.length < stairSuppressionMin) return;
			// 都是短段
			if (!trackGroup.every((s) => segmentLength(s) < stairLenMax)) return;
			const sorted = [...trackGroup].sort((a, b) => (isHorizontal(a) ? a.x1 - b.x1 : a.y1 - b.y1));
			const gaps = sorted.slice(1).map((s, i) => {
				const h = isHorizontal(s);
				return (h ? s.x1 : s.y1) - (h ? sorted[i].x2 : sorted[i].y2);
			});
			if (gaps.length === 0) return;
			const medGap = [...gaps].sort((a, b) => a - b)[Math.floor(gaps.length / 2)];
			if (medGap <= 0.001) return;
			const isEquallySpaced = gaps.every((g) => Math.abs(g - medGap) / medGap < stairSpacingTol);
			if (isEquallySpaced) trackGroup.forEach((s) => suppressedStair.add(`${s.x1.toFixed(4)},${s.y1.toFixed(4)}`));
		});
	}
	const deStairedCenters = suppressedStair.size > 0
		? filteredCenters.filter((s) => !suppressedStair.has(`${s.x1.toFixed(4)},${s.y1.toFixed(4)}`))
		: filteredCenters;
	return mergeCollinearSegments(deStairedCenters, {
		trackTolerance: mergeTrackTol,
		gapTolerance: Math.min(0.030, Math.max(0.012, 550 / mmPerNormalized)),
		minLength: Math.max(0.012, 650 / mmPerNormalized),
		duplicateTolerance: 0.012,
		duplicateOverlap: 0.82,
		limit,
	});
};

const snapWallGraphSegments = (segments: TraceSegment[]) => {
	const tolerance = 0.018;
	const snapped = segments.map((segment) => ({ ...segment }));
	const horizontal = snapped.filter(isHorizontal);
	const vertical = snapped.filter((segment) => !isHorizontal(segment));
	const extendToNearest = (segment: TraceSegment, atStart: boolean) => {
		const horizontalSegment = isHorizontal(segment);
		const fixedTrack = horizontalSegment ? segment.y1 : segment.x1;
		const current = horizontalSegment
			? (atStart ? Math.min(segment.x1, segment.x2) : Math.max(segment.x1, segment.x2))
			: (atStart ? Math.min(segment.y1, segment.y2) : Math.max(segment.y1, segment.y2));
		const candidates = (horizontalSegment ? vertical : horizontal)
			.map((other) => {
				const otherTrack = horizontalSegment ? other.x1 : other.y1;
				const otherStart = horizontalSegment ? Math.min(other.y1, other.y2) : Math.min(other.x1, other.x2);
				const otherEnd = horizontalSegment ? Math.max(other.y1, other.y2) : Math.max(other.x1, other.x2);
				if (fixedTrack < otherStart - tolerance || fixedTrack > otherEnd + tolerance) return null;
				const distance = Math.abs(otherTrack - current);
				if (distance > tolerance) return null;
				return { track: otherTrack, distance };
			})
			.filter((item): item is { track: number; distance: number } => item !== null)
			.sort((a, b) => a.distance - b.distance);
		return candidates[0]?.track ?? current;
	};
	return snapped.map((segment) => {
		const horizontalSegment = isHorizontal(segment);
		const start = extendToNearest(segment, true);
		const end = extendToNearest(segment, false);
		return horizontalSegment
			? { ...segment, x1: Math.min(start, end), x2: Math.max(start, end), score: Math.abs(end - start) }
			: { ...segment, y1: Math.min(start, end), y2: Math.max(start, end), score: Math.abs(end - start) };
	});
};

const compileWallGraphSegments = (segments: TraceSegment[], limit = 96) => {
	const snapped = snapWallGraphSegments(segments);
	return mergeCollinearSegments(snapped, {
		trackTolerance: 0.012,
		gapTolerance: 0.024,
		minLength: 0.018,
		duplicateTolerance: 0.014,
		duplicateOverlap: 0.76,
		limit,
	});
};

const isRelaxedStructuralSegment = (segment: TraceSegment, dimensions: DimensionMark[]) => {
	if (isDimensionLayer(segment.layer) || isHatchLayer(segment.layer)) return false;
	// 虚线（阳台轮廓/轴线/标注引线）不参与 relaxed 墙配对
	if (segment.dashPattern === 'dashed' || segment.dashPattern === 'dash_dot' || segment.dashPattern === 'dotted') return false;
	const length = segmentLength(segment);
	if (length < 0.004) return false;
	const dx = Math.abs(segment.x2 - segment.x1);
	const dy = Math.abs(segment.y2 - segment.y1);
	const maxAxis = Math.max(dx, dy);
	const minAxis = Math.min(dx, dy);
	const orthogonalRatio = minAxis / Math.max(0.0001, maxAxis);
	if (orthogonalRatio > 0.35) return false;
	const cx = (segment.x1 + segment.x2) / 2;
	const cy = (segment.y1 + segment.y2) / 2;
	const nearDimensionText = dimensions.some((mark) => Math.hypot(mark.x - cx, mark.y - cy) < 0.035);
	return !(nearDimensionText && length < 0.035);
};

const mergeAndFilterSegments = (segments: TraceSegment[], region: TraceRegion, dimensions: DimensionMark[], mmPerNormalized = 21000) => {
	const classCounts = { wall: 0, dimension: 0, hatch: 0, symbol: 0, opening_symbol: 0, noise: 0, projection: 0 };
	const regionScoped = segments.filter((segment) => inRegion(segment, region));
	const regionInsufficient = regionScoped.length < 16 && segments.length >= 16;
	const scopedAll = regionScoped;
	const emptyPipelineStats = {
		regionScoped: regionScoped.length,
		classifiedWall: 0,
		strictCandidates: 0,
		focusedStrictCandidates: 0,
		strictMerged: 0,
		pairedWalls: 0,
		relaxedScope: 0,
		relaxedCandidates: 0,
		relaxedMerged: 0,
		selectedSegments: 0,
		selectedPipeline: 'roi-insufficient',
	};
	const emptyDebugSegments = {
		regionScoped,
		classifiedWall: [] as TraceSegment[],
		focusedWall: [] as TraceSegment[],
		strictMerged: [] as TraceSegment[],
		pairedWalls: [] as TraceSegment[],
		relaxedCandidates: [] as TraceSegment[],
		relaxedMerged: [] as TraceSegment[],
	};
	if (regionInsufficient) {
		return {
			segments: [] as TraceSegment[],
			zoneSegments: [] as TraceSegment[],
			classCounts,
			mode: 'roi-insufficient',
			scopedSegments: regionScoped.length,
			regionFallback: false,
			regionInsufficient: true,
			focus: { segments: [] as TraceSegment[], focused: false, componentCount: 0 },
			pipelineStats: emptyPipelineStats,
			debugSegments: emptyDebugSegments,
		};
	}
	// 计算 PDF 中位线宽，用于自适应分类（DXF 无此字段则 undefined）
	const pdfLws = scopedAll.filter((s) => s.source === 'pdf' && (s.lineWidth ?? 0) > 0).map((s) => s.lineWidth!);
	const medianLineWidth = pdfLws.length > 4 ? [...pdfLws].sort((a, b) => a - b)[Math.floor(pdfLws.length / 2)] : undefined;
	const strictCandidates = scopedAll
		.map((segment) => ({ ...segment, classification: classifySegment(segment, dimensions, medianLineWidth) }))
		.filter((segment) => {
			classCounts[segment.classification ?? 'noise'] += 1;
			return segment.classification === 'wall';
		});
	const focus = focusPrimaryPlanCluster(strictCandidates, region);
	const focusedStrictCandidates = focus.segments;
	// Bug 5 修复：limit 从 64 升至 192，酒店大层平面真实墙线数 120-200 条，64 会截断近一半。
	const strict = mergeCollinearSegments(focusedStrictCandidates, {
		trackTolerance: 0.008,
		gapTolerance: 0.018,
		minLength: 0.025,
		duplicateTolerance: 0.012,
		duplicateOverlap: 0.72,
		limit: 192,
	});
	// P2: pairedWalls 输入前剔除极短线段
	// 阈值采用物理值（500mm），避免高 mmPerNorm 时 0.025 对应 1389mm 把大量短墙全部过滤掉
	const minPairedInputLen = Math.max(0.010, 500 / mmPerNormalized);
	const pairedWallsInput = focusedStrictCandidates.filter((s) => segmentLength(s) >= minPairedInputLen);
	const pairedWalls = buildParallelWallCenters(pairedWallsInput, mmPerNormalized, 160);
	const basePipelineStats = {
		regionScoped: scopedAll.length,
		classifiedWall: strictCandidates.length,
		strictCandidates: strictCandidates.length,
		focusedStrictCandidates: focusedStrictCandidates.length,
		strictMerged: strict.length,
		pairedWalls: pairedWalls.length,
		relaxedScope: 0,
		relaxedCandidates: 0,
		relaxedMerged: 0,
		selectedSegments: 0,
		selectedPipeline: 'none',
	};
	const baseDebugSegments = {
		regionScoped,
		classifiedWall: strictCandidates,
		focusedWall: focusedStrictCandidates,
		strictMerged: strict,
		pairedWalls,
		relaxedCandidates: [] as TraceSegment[],
		relaxedMerged: [] as TraceSegment[],
	};
	if (pairedWalls.length >= 8) {
		// Bug 3 修复：pairedWalls 管道不再丢弃 strict 中的单线墙。
		// 原逻辑：仅返回 pairedWalls（双线配对中心线），单线承重墙/隔墙全部丢失。
		// 新逻辑：以 pairedWalls 为主（已是中心线），补充 strict 中未被配对覆盖的墙线。
		// 判断"已被覆盖"：strict 线段中心点在任一 pairedWall 的 trackTolerance 带内且有重叠。
		const PAIRED_COVER_TRACK_TOL = 0.014; // ≈ 配对容差的 1.5× 归一化值
		const PAIRED_COVER_OVERLAP_MIN = 0.5;
		const uncoveredStrict = strict.filter((s) => {
			const sH = isHorizontal(s);
			const sTrack = sH ? s.y1 : s.x1;
			const sStart = sH ? Math.min(s.x1, s.x2) : Math.min(s.y1, s.y2);
			const sEnd   = sH ? Math.max(s.x1, s.x2) : Math.max(s.y1, s.y2);
			return !pairedWalls.some((p) => {
				if (isHorizontal(p) !== sH) return false;
				const pTrack = sH ? p.y1 : p.x1;
				if (Math.abs(pTrack - sTrack) > PAIRED_COVER_TRACK_TOL) return false;
				const pStart = sH ? Math.min(p.x1, p.x2) : Math.min(p.y1, p.y2);
				const pEnd   = sH ? Math.max(p.x1, p.x2) : Math.max(p.y1, p.y2);
				const overlap = Math.max(0, Math.min(sEnd, pEnd) - Math.max(sStart, pStart));
				return overlap / Math.max(0.001, sEnd - sStart) >= PAIRED_COVER_OVERLAP_MIN;
			});
		});
		// 建筑原则：单线不是墙（轴线/参考线/家具线均为单线）
		// 当双线配对管道（pairedWalls）数量充足时，仅使用双线配对中心线作为墙体，
		// 放弃 uncoveredStrict 单线补充，避免大量轴线/边框线被误判为墙
		const blendedSegments = [...pairedWalls];
		return {
			segments: blendedSegments,
			zoneSegments: strict,
			classCounts,
			mode: focus.focused ? 'primary-cluster-paired-wall-centerline' : 'paired-wall-centerline',
			scopedSegments: scopedAll.length,
			regionFallback: false,
			regionInsufficient: false,
			focus,
			pipelineStats: { ...basePipelineStats, selectedSegments: blendedSegments.length, selectedPipeline: 'pairedWalls+strict' },
			debugSegments: baseDebugSegments,
		};
	}
	if (strict.length >= 8) return {
		segments: strict,
		zoneSegments: strict,
		classCounts,
		mode: focus.focused ? 'primary-cluster-strict' : 'strict',
		scopedSegments: scopedAll.length,
		regionFallback: false,
		regionInsufficient: false,
		focus,
		pipelineStats: { ...basePipelineStats, selectedSegments: strict.length, selectedPipeline: 'strictMerged' },
		debugSegments: baseDebugSegments,
	};

	const relaxedScope = focus.focused && focus.focusBounds
		? scopedAll.filter((segment) => {
			const cx = (segment.x1 + segment.x2) / 2;
			const cy = (segment.y1 + segment.y2) / 2;
			return cx >= focus.focusBounds!.minX && cx <= focus.focusBounds!.maxX && cy >= focus.focusBounds!.minY && cy <= focus.focusBounds!.maxY;
		})
		: scopedAll;
	const relaxedCandidates = relaxedScope
		.filter((segment) => isRelaxedStructuralSegment(segment, dimensions));
	// Bug 5 同步：relaxed 管道上限也从 96 升至 192，与 strict 保持一致。
	const relaxed = mergeCollinearSegments(relaxedCandidates, {
		trackTolerance: 0.018,
		gapTolerance: 0.05,
		minLength: 0.012,
		duplicateTolerance: 0.02,
		duplicateOverlap: 0.86,
		limit: 192,
	});
	const pipelineStats = {
		...basePipelineStats,
		relaxedScope: relaxedScope.length,
		relaxedCandidates: relaxedCandidates.length,
		relaxedMerged: relaxed.length,
	};
	const debugSegments = {
		...baseDebugSegments,
		relaxedCandidates,
		relaxedMerged: relaxed,
	};
	if (relaxed.length > strict.length) return {
		segments: relaxed,
		zoneSegments: relaxed,
		classCounts,
		mode: focus.focused ? 'primary-cluster-relaxed-vector' : 'relaxed-vector',
		scopedSegments: scopedAll.length,
		regionFallback: false,
		regionInsufficient: false,
		focus,
		pipelineStats: { ...pipelineStats, selectedSegments: relaxed.length, selectedPipeline: 'relaxedMerged' },
		debugSegments,
	};
	return {
		segments: strict,
		zoneSegments: strict,
		classCounts,
		mode: strict.length > 0 ? (focus.focused ? 'primary-cluster-strict-minimal' : 'strict-minimal') : 'none',
		scopedSegments: scopedAll.length,
		regionFallback: false,
		regionInsufficient: false,
		focus,
		pipelineStats: { ...pipelineStats, selectedSegments: strict.length, selectedPipeline: strict.length > 0 ? 'strictMinimal' : 'none' },
		debugSegments,
	};
};

const buildClosedSpaceZones = (segments: TraceSegment[], mmPerNormalized: number): TraceElement[] => {
	const horizontal = segments.filter(isHorizontal);
	const vertical = segments.filter((segment) => !isHorizontal(segment));
	const zones: TraceElement[] = [];
	const tolerance = 0.018;
	const clusterTracks = (values: number[], minGap = 0.018) => {
		const sorted = [...values].sort((a, b) => a - b);
		const clusters: number[][] = [];
		sorted.forEach((value) => {
			const last = clusters[clusters.length - 1];
			if (!last || Math.abs(value - last[last.length - 1]) > minGap) clusters.push([value]);
			else last.push(value);
		});
		return clusters
			.map((cluster) => cluster.reduce((sum, value) => sum + value, 0) / cluster.length)
			.filter((value, index, array) => index === 0 || Math.abs(value - array[index - 1]) > minGap);
	};
	const covers = (segment: TraceSegment, start: number, end: number, track: number) => {
		const horizontalSegment = isHorizontal(segment);
		const segmentTrack = horizontalSegment ? segment.y1 : segment.x1;
		if (Math.abs(segmentTrack - track) > tolerance) return false;
		const a = horizontalSegment ? Math.min(segment.x1, segment.x2) : Math.min(segment.y1, segment.y2);
		const b = horizontalSegment ? Math.max(segment.x1, segment.x2) : Math.max(segment.y1, segment.y2);
		return a <= start + tolerance && b >= end - tolerance;
	};
	const xTracks = clusterTracks(vertical.flatMap((segment) => [segment.x1, segment.x2]), 0.016);
	const yTracks = clusterTracks(horizontal.flatMap((segment) => [segment.y1, segment.y2]), 0.016);
	for (let xi = 0; xi < xTracks.length - 1; xi += 1) {
		for (let yi = 0; yi < yTracks.length - 1; yi += 1) {
			const leftX = xTracks[xi];
			const rightX = xTracks[xi + 1];
			const y1 = yTracks[yi];
			const y2 = yTracks[yi + 1];
			const area = (rightX - leftX) * (y2 - y1);
			if (rightX - leftX < 0.035 || y2 - y1 < 0.035 || area < 0.0025 || area > 0.28) continue;
			const topWall = horizontal.some((segment) => covers(segment, leftX, rightX, y1));
			const bottomWall = horizontal.some((segment) => covers(segment, leftX, rightX, y2));
			const leftWall = vertical.some((segment) => covers(segment, y1, y2, leftX));
			const rightWall = vertical.some((segment) => covers(segment, y1, y2, rightX));
			if (![topWall, bottomWall, leftWall, rightWall].every(Boolean)) continue;
			const duplicate = zones.some((zone) => {
				const overlapX = Math.max(0, Math.min(zone.x + zone.w, rightX) - Math.max(zone.x, leftX));
				const overlapY = Math.max(0, Math.min(zone.y + zone.h, y2) - Math.max(zone.y, y1));
				const overlapArea = overlapX * overlapY;
				return overlapArea / Math.min(area, zone.w * zone.h) > 0.7;
			});
			if (duplicate) continue;
			zones.push({
				id: `floor-ir-api-room-${zones.length}`,
				kind: 'function_zone',
				label: `闭合房间 ${zones.length + 1}`,
				geometryType: 'polygon',
				x: leftX,
				y: y1,
				w: rightX - leftX,
				h: y2 - y1,
				points: [
					{ x: leftX, y: y1 },
					{ x: rightX, y: y1 },
					{ x: rightX, y: y2 },
					{ x: leftX, y: y2 },
				],
				widthMm: Math.round((rightX - leftX) * mmPerNormalized),
				depthMm: Math.round((y2 - y1) * mmPerNormalized),
				areaSqm: Number(((area * mmPerNormalized * mmPerNormalized) / 1000000).toFixed(1)),
				confidence: 0.78,
				status: 'candidate',
			});
			if (zones.length >= 24) return zones;
		}
	}
	for (let i = 0; i < horizontal.length; i += 1) {
		for (let j = i + 1; j < horizontal.length; j += 1) {
			const top = horizontal[i].y1 < horizontal[j].y1 ? horizontal[i] : horizontal[j];
			const bottom = top === horizontal[i] ? horizontal[j] : horizontal[i];
			const y1 = top.y1;
			const y2 = bottom.y1;
			if (Math.abs(y2 - y1) < 0.05) continue;
			const leftX = Math.max(Math.min(top.x1, top.x2), Math.min(bottom.x1, bottom.x2));
			const rightX = Math.min(Math.max(top.x1, top.x2), Math.max(bottom.x1, bottom.x2));
			if (rightX - leftX < 0.06) continue;
			const leftWall = vertical.find((segment) => {
				const x = segment.x1;
				const startY = Math.min(segment.y1, segment.y2);
				const endY = Math.max(segment.y1, segment.y2);
				return Math.abs(x - leftX) <= tolerance && startY <= y1 + tolerance && endY >= y2 - tolerance;
			});
			const rightWall = vertical.find((segment) => {
				const x = segment.x1;
				const startY = Math.min(segment.y1, segment.y2);
				const endY = Math.max(segment.y1, segment.y2);
				return Math.abs(x - rightX) <= tolerance && startY <= y1 + tolerance && endY >= y2 - tolerance;
			});
			if (!leftWall || !rightWall) continue;
			const area = (rightX - leftX) * (y2 - y1);
			if (area < 0.006 || area > 0.5) continue;
			const duplicate = zones.some((zone) => {
				const overlapX = Math.max(0, Math.min(zone.x + zone.w, rightX) - Math.max(zone.x, leftX));
				const overlapY = Math.max(0, Math.min(zone.y + zone.h, y2) - Math.max(zone.y, y1));
				const overlapArea = overlapX * overlapY;
				return overlapArea / Math.min(area, zone.w * zone.h) > 0.62;
			});
			if (duplicate) continue;
			zones.push({
				id: `floor-ir-api-zone-${zones.length}`,
				kind: 'function_zone',
				label: `闭合空间 ${zones.length + 1}`,
				geometryType: 'polygon',
				x: leftX,
				y: y1,
				w: rightX - leftX,
				h: y2 - y1,
				points: [
					{ x: leftX, y: y1 },
					{ x: rightX, y: y1 },
					{ x: rightX, y: y2 },
					{ x: leftX, y: y2 },
				],
				widthMm: Math.round((rightX - leftX) * mmPerNormalized),
				depthMm: Math.round((y2 - y1) * mmPerNormalized),
				areaSqm: Number(((area * mmPerNormalized * mmPerNormalized) / 1000000).toFixed(1)),
				confidence: 0.68,
				status: 'candidate',
			});
			if (zones.length >= 16) return zones;
		}
	}
	return zones;
};

// ═══════════════════════════════════════════════════════════════════════
// ─── Zone Text Binding：将 room_name 文字绑定到闭合空间 ──────────────
// ═══════════════════════════════════════════════════════════════════════

const ZONE_TEXT_MAP: Record<string, ZoneType> = {
	'电梯': 'elevator', '客梯': 'elevator', '电梯间': 'elevator', '电梯厅': 'elevator', '电梯井': 'elevator',
	'货梯': 'freight_elevator',
	'消防楼梯': 'fire_staircase', '防烟楼梯': 'fire_staircase', '疏散楼梯': 'fire_staircase',
	'室内楼梯': 'interior_staircase',
	'楼梯': 'building_staircase', '楼梯间': 'building_staircase',
	'管井': 'general_shaft', '管道井': 'general_shaft',
	'水井': 'plumbing_shaft', '给水井': 'plumbing_shaft', '排水井': 'plumbing_shaft',
	'风井': 'ventilation_shaft',
	'强电井': 'electrical_shaft', '弱电井': 'electrical_shaft', '电气井': 'electrical_shaft',
	'强电间': 'electrical_room', '弱电间': 'electrical_room', '配电间': 'electrical_room', '配电房': 'electrical_room',
	'机房': 'mechanical_room', '水泵房': 'mechanical_room',
	'设备间': 'general_equipment_room', '设备房': 'general_equipment_room',
	'阳台': 'balcony', '封闭阳台': 'balcony', '生活阳台': 'balcony', '景观阳台': 'balcony', '观景阳台': 'balcony',
	'开放阳台': 'open_balcony', '半开放阳台': 'open_balcony',
	'露台': 'terrace', '平台': 'terrace', '屋顶花园': 'terrace', '空中花园': 'terrace',
};

const bindTextsToZones = (
	classifiedTexts: ClassifiedText[],
	spaceElements: TraceElement[]
): void => {
	const roomNameTexts = classifiedTexts.filter((t) => t.role === 'room_name');
	for (const space of spaceElements) {
		const sx = space.x;
		const sy = space.y;
		const sw = space.w;
		const sh = space.h;
		for (const text of roomNameTexts) {
			if (text.x >= sx && text.x <= sx + sw && text.y >= sy && text.y <= sy + sh) {
				space.label = text.text;
				break;
			}
		}
	}
};

const buildColumnCandidates = (segments: TraceSegment[], mmPerNormalized: number): TraceElement[] => {
	const horizontal = segments.filter(isHorizontal);
	const vertical = segments.filter((segment) => !isHorizontal(segment));
	const candidates: TraceElement[] = [];
	const tolerance = 0.012;
	const minSide = 0.008;
	const maxSide = 0.06;
	const covers = (segment: TraceSegment, start: number, end: number, track: number) => {
		const horizontalSegment = isHorizontal(segment);
		const segmentTrack = horizontalSegment ? segment.y1 : segment.x1;
		if (Math.abs(segmentTrack - track) > tolerance) return false;
		const a = horizontalSegment ? Math.min(segment.x1, segment.x2) : Math.min(segment.y1, segment.y2);
		const b = horizontalSegment ? Math.max(segment.x1, segment.x2) : Math.max(segment.y1, segment.y2);
		return a <= start + tolerance && b >= end - tolerance;
	};
	horizontal.forEach((top) => {
		horizontal.forEach((bottom) => {
			if (bottom.y1 <= top.y1) return;
			const y1 = top.y1;
			const y2 = bottom.y1;
			const h = y2 - y1;
			if (h < minSide || h > maxSide) return;
			const leftX = Math.max(Math.min(top.x1, top.x2), Math.min(bottom.x1, bottom.x2));
			const rightX = Math.min(Math.max(top.x1, top.x2), Math.max(bottom.x1, bottom.x2));
			const w = rightX - leftX;
			if (w < minSide || w > maxSide) return;
			const left = vertical.some((segment) => covers(segment, y1, y2, leftX));
			const right = vertical.some((segment) => covers(segment, y1, y2, rightX));
			// 3-edge fallback：嵌墙柱可能有一侧与墙线重合而缺失 → 允许仅一侧
			// 但两侧均缺失（无任何垂直边）则跳过
			if (!left && !right) return;
			const hasBothSides = left && right;
			const candidate: TraceElement = {
				id: `floor-ir-api-column-${candidates.length}`,
				kind: 'column',
				label: `结构柱 ${candidates.length + 1}`,
				geometryType: 'rect',
				x: leftX,
				y: y1,
				w,
				h,
				points: [
					{ x: leftX, y: y1 },
					{ x: rightX, y: y1 },
					{ x: rightX, y: y2 },
					{ x: leftX, y: y2 },
				],
				widthMm: Math.round(w * mmPerNormalized),
				depthMm: Math.round(h * mmPerNormalized),
				// 4边完整 → 0.62，3边（嵌墙） → 0.46（后续门禁仍会综合打分）
				confidence: hasBothSides ? 0.62 : 0.46,
				status: 'candidate',
			};
			if (!candidates.some((existing) => rectIntersects(existing, candidate))) candidates.push(candidate);
		});
	});
	return candidates.slice(0, 48);
};

/**
 * 基于原始线段（分类前）检测结构柱。
 * 主路径：直接识别 pathKind==='filledRect' 的填充矩形（PDF 柱通常是填充黑色矩形，无描边）。
 * 回退路径：从 pathKind==='rect' 的描边矩形 4 条边重建闭合矩形（少数 PDF 用描边矩形表示柱）。
 */
/**
 * StructuralKernel：所有深色填充区域的几何事实汇总（不含建筑语义）。
 * 包含 filledRect（轴对齐矩形）和 filledPolygon（异型填充）。
 * 后续分类为 isolated / embedded / perimeter 三类柱。
 */
const collectStructuralKernels = (rawSegments: TraceSegment[]): TraceSegment[] => {
	return rawSegments.filter(
		(s) => s.pathKind === 'filledRect' || s.pathKind === 'filledPolygon'
	);
};

const buildColumnCandidatesFromRaw = (rawSegments: TraceSegment[], mmPerNormalized: number, trustedScale = true): TraceElement[] => {
	// 动态阈值：基于物理 mm，防止高 mmPerNorm（如 55567）时 0.006 = 333mm 过滤掉 250-300mm 小柱
	const minSide = Math.max(0.003, 130 / mmPerNormalized);   // ≈130mm 物理下限
	const maxSide = Math.max(minSide * 3, (trustedScale ? 1200 : 1800) / mmPerNormalized);  // soft cap：常规柱优先尺寸
	const hardMaxSide = Math.max(maxSide * 3, (trustedScale ? 3600 : 5200) / mmPerNormalized);  // large-column cap：允许大柱进入候选
	const hardMaxAreaMm2 = trustedScale ? 7_500_000 : 12_000_000;  // 约 7.5m² / 12m²，继续排除整块填充或大面积误检
	const maxAspect = 3.0;   // 最大长宽比
	const candidates: TraceElement[] = [];
	const _dbg = process.env.NODE_ENV !== 'production';

	// ── 诊断：原始 filledRect 统计 ──
	const allFilledRects = rawSegments.filter((s) => s.pathKind === 'filledRect');
	if (_dbg && allFilledRects.length > 0) {
		const szs = allFilledRects.slice(0, 20).map((s) => {
			const w = Math.abs(s.x2 - s.x1);
			const h = Math.abs(s.y2 - s.y1);
			return `${Math.round(w*mmPerNormalized)}x${Math.round(h*mmPerNormalized)}mm`;
		});
		console.log('[A2-raw诊断] filledRect总数:', allFilledRects.length, '尺寸样本(前20):', szs.join(', '));
	}

	// ── 主路径A：直接从填充矩形提取柱（轴对齐矩形）──────────────────────────────────
	rawSegments
		.filter((s) => s.pathKind === 'filledRect')
		.forEach((s) => {
			const w = Math.abs(s.x2 - s.x1);
			const h = Math.abs(s.y2 - s.y1);
			const areaMm2 = w * h * mmPerNormalized * mmPerNormalized;
			// 尺寸过滤
			if (w < minSide || h < minSide) return;
			if (w > hardMaxSide || h > hardMaxSide) return;
			if (areaMm2 > hardMaxAreaMm2) return;
			if (Math.max(w, h) / Math.min(w, h) > maxAspect) return;
			const left = Math.min(s.x1, s.x2);
			const top = Math.min(s.y1, s.y2);
			const right = left + w;
			const bottom = top + h;
			const candidate: TraceElement = {
				id: `floor-ir-api-col-raw-${candidates.length}`,
				kind: 'column',
				label: `结构柱 ${candidates.length + 1}`,
				geometryType: 'rect',
				x: clamp(left),
				y: clamp(top),
				w: clamp(w, 0.001, 1),
				h: clamp(h, 0.001, 1),
				points: [
					{ x: left, y: top },
					{ x: right, y: top },
					{ x: right, y: bottom },
					{ x: left, y: bottom },
				],
				widthMm: Math.round(w * mmPerNormalized),
				depthMm: Math.round(h * mmPerNormalized),
				confidence: (w > maxSide || h > maxSide) ? 0.82 : 0.88,   // 大柱放宽接入，但略降先验
				status: 'candidate',
			};
			if (!candidates.some((existing) => rectIntersects(existing, candidate))) candidates.push(candidate);
		});
	if (_dbg) console.log('[A2-raw诊断] 主路径A(filledRect):', candidates.length, '个候选');

	// ── 回退路径：从描边矩形 4 条边重建柱（仅对无填充柱 PDF 生效）──────────────
	const tolerance = 0.006;  // 顶点对齐容差（0.004→0.006：容纳 PDF 导出时的微小顶点偏移）
	// 注意：rect 段不使用 lineWidth 过滤（lineWidth 为描边宽度，填充矩形无意义）
	// ── 诊断：rect 路径候选的过滤统计 ──
	const allHSegs = rawSegments.filter((s) => s.pathKind === 'rect' && isHorizontal(s));
	const allVSegs = rawSegments.filter((s) => s.pathKind === 'rect' && !isHorizontal(s));
	const tooSmallH = allHSegs.filter((s) => { const l = segmentLength(s); return l < minSide; });
	const tooLargeH = allHSegs.filter((s) => { const l = segmentLength(s); return l > hardMaxSide; });
	const tooSmallV = allVSegs.filter((s) => { const l = segmentLength(s); return l < minSide; });
	const tooLargeV = allVSegs.filter((s) => { const l = segmentLength(s); return l > hardMaxSide; });
	
	if (_dbg && (tooLargeH.length > 0 || tooLargeV.length > 0)) {
		const largeHSizes = tooLargeH.slice(0, 5).map((s) => Math.round(segmentLength(s) * mmPerNormalized));
		const largeVSizes = tooLargeV.slice(0, 5).map((s) => Math.round(segmentLength(s) * mmPerNormalized));
		console.log('[A2-raw诊断] rect路径被超大尺寸过滤: 横向', tooLargeH.length, '条(样本mm):', largeHSizes, '竖向', tooLargeV.length, '条(样本mm):', largeVSizes);
	}
	
	const hSegs = rawSegments.filter((s) => s.pathKind === 'rect' && isHorizontal(s) && (() => { const l = segmentLength(s); return l >= minSide && l <= hardMaxSide; })());
	const vSegs = rawSegments.filter((s) => s.pathKind === 'rect' && !isHorizontal(s) && (() => { const l = segmentLength(s); return l >= minSide && l <= hardMaxSide; })());
	for (let i = 0; i < hSegs.length; i += 1) {
		const top = hSegs[i];
		const topY = top.y1;
		const topLeft = Math.min(top.x1, top.x2);
		const topRight = Math.max(top.x1, top.x2);
		const topW = topRight - topLeft;
		for (let j = i + 1; j < hSegs.length; j += 1) {
			const bot = hSegs[j];
			if (Math.abs(Math.min(bot.x1, bot.x2) - topLeft) > tolerance) continue;
			if (Math.abs(Math.max(bot.x1, bot.x2) - topRight) > tolerance) continue;
			const h = Math.abs(bot.y1 - topY);
			const areaMm2 = topW * h * mmPerNormalized * mmPerNormalized;
			if (h < minSide || h > hardMaxSide) continue;
			if (areaMm2 > hardMaxAreaMm2) continue;
			if (Math.max(topW, h) / Math.min(topW, h) > maxAspect) continue;
			const y1 = Math.min(topY, bot.y1);
			const y2 = Math.max(topY, bot.y1);
			const hasLeft = vSegs.some((v) => {
				const vX = v.x1;
				const vTop = Math.min(v.y1, v.y2);
				const vBot = Math.max(v.y1, v.y2);
				return Math.abs(vX - topLeft) <= tolerance && vTop <= y1 + tolerance && vBot >= y2 - tolerance;
			});
			if (!hasLeft) continue;
			const hasRight = vSegs.some((v) => {
				const vX = v.x1;
				const vTop = Math.min(v.y1, v.y2);
				const vBot = Math.max(v.y1, v.y2);
				return Math.abs(vX - topRight) <= tolerance && vTop <= y1 + tolerance && vBot >= y2 - tolerance;
			});
			if (!hasRight) continue;
			const candidate: TraceElement = {
				id: `floor-ir-api-col-raw-${candidates.length}`,
				kind: 'column',
				label: `结构柱 ${candidates.length + 1}`,
				geometryType: 'rect',
				x: clamp(topLeft),
				y: clamp(y1),
				w: clamp(topW, 0.001, 1),
				h: clamp(h, 0.001, 1),
				points: [
					{ x: topLeft, y: y1 },
					{ x: topRight, y: y1 },
					{ x: topRight, y: y2 },
					{ x: topLeft, y: y2 },
				],
				widthMm: Math.round(topW * mmPerNormalized),
				depthMm: Math.round(h * mmPerNormalized),
				confidence: (topW > maxSide || h > maxSide) ? 0.70 : 0.74,
				status: 'candidate',
			};
			if (!candidates.some((existing) => rectIntersects(existing, candidate))) candidates.push(candidate);
		}
	}

	// ── 主路径B：从 filledPolygon（非轴对齐填充多边形）提取 StructuralKernel ──
	// 典型场景：L型嵌墙柱、边带周期性加厚柱、CAD导出时用多段封闭路径表示的异形柱
	rawSegments
		.filter((s) => s.pathKind === 'filledPolygon' && s.polygonPoints && s.polygonPoints.length >= 3)
		.forEach((s) => {
			const pts = s.polygonPoints!;
			const xs = pts.map((p) => p.x);
			const ys = pts.map((p) => p.y);
			const left = Math.min(...xs); const right = Math.max(...xs);
			const top = Math.min(...ys); const bottom = Math.max(...ys);
			const w = right - left; const h = bottom - top;
			// 尺寸过滤：使用比矩形柱稍宽松的阈值（异形柱可能bbox较大）
			if (w < minSide || h < minSide) return;
			if (w > maxSide * 2.5 || h > maxSide * 2.5) return; // 极大区域排除（楼梯填充/剖面填充等）
			// 面积估算：多边形面积用 bbox 面积的 0.25~0.95 范围过滤（太空洞或太满的不是柱）
			const bboxArea = w * h;
			// Shoelace 面积
			let polyArea = 0;
			for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
				polyArea += (pts[j].x + pts[i].x) * (pts[j].y - pts[i].y);
			}
			polyArea = Math.abs(polyArea) / 2;
			const fillRatio = polyArea / Math.max(bboxArea, 1e-9);
			if (fillRatio < 0.20 || fillRatio > 1.02) return; // 排除空洞型或错误多边形

			const candidate: TraceElement = {
				id: `floor-ir-api-col-poly-${candidates.length}`,
				kind: 'column',
				label: `结构柱(异形) ${candidates.length + 1}`,
				geometryType: 'rect', // bbox近似，后续可精化为polygon
				x: clamp(left),
				y: clamp(top),
				w: clamp(w, 0.001, 1),
				h: clamp(h, 0.001, 1),
				points: pts,
				widthMm: Math.round(w * mmPerNormalized),
				depthMm: Math.round(h * mmPerNormalized),
				confidence: 0.72, // 异形柱置信度略低，需后续门禁确认
				status: 'candidate',
			};
			if (!candidates.some((existing) => rectIntersects(existing, candidate))) candidates.push(candidate);
		});
	
	// ── 第三路 fallback：从 line 型段做四线闭合矩形重建（已禁用）──────────────
	// 禁用原因：对含 20000+ 条线段的 CAD-PDF，此路径在墙角/门框/家具等大量交叉点
	// 生成假柱（16+ 假阳性），严重干扰 Geometry Gate。
	// 正确解决方向：通过 flushFillSubPath / paintSolidColorImageMask 修复填充路径解析。
	// if (candidates.length === 0) { ... }

	if (_dbg) console.log('[A2-raw诊断] buildColumnCandidatesFromRaw最终输出:', candidates.length, '个候选 (minSide=', Math.round(minSide * mmPerNormalized), 'mm, softMaxSide=', Math.round(maxSide * mmPerNormalized), 'mm, hardMaxSide=', Math.round(hardMaxSide * mmPerNormalized), 'mm, maxAspect=', maxAspect, ')');
	return candidates.slice(0, 80); // 上限从 60 提升至 80 以容纳异形柱
};

// ─── 柱识别：墙厚突变候选检测 ───────────────────────────────────────────
// 沿墙中心线采样，找局部"鼓包"（厚度突变）→ 可能是构造柱/墙包柱
const detectWallThicknessBumpColumns = (
	walls: TraceElement[],
	rawSegments: TraceSegment[],
	mmPerNormalized: number
): TraceElement[] => {
	const candidates: TraceElement[] = [];
	const minBump = 0.006;   // 最小鼓包尺寸（~126mm）
	const maxBump = 0.045;   // 最大鼓包（~945mm）
	// 只看水平墙且长度 > 最小两段柱宽；同理竖直墙
	const longWalls = walls.filter((w) => Math.max(w.w, w.h) > 0.08);
	// 对每面长墙，找原始 filledRect / rect 段在其厚度延伸范围内、且宽度 << 墙长的矩形
	longWalls.forEach((wall) => {
		const horizontal = wall.w >= wall.h;
		const wallTrack = horizontal ? wall.y + wall.h / 2 : wall.x + wall.w / 2;
		const wallThick = horizontal ? wall.h : wall.w;
		const wallStart = horizontal ? wall.x : wall.y;
		const wallEnd = horizontal ? wall.x + wall.w : wall.y + wall.h;
		// 寻找在墙体延长线上、贴墙但比墙厚的实体块
		rawSegments
			.filter((s) => s.pathKind === 'filledRect')
			.forEach((s) => {
				const left = Math.min(s.x1, s.x2);
				const right = Math.max(s.x1, s.x2);
				const top = Math.min(s.y1, s.y2);
				const bottom = Math.max(s.y1, s.y2);
				const rw = right - left;
				const rh = bottom - top;
				// 必须近似方形/矩形，且尺寸在柱范围
				const shortSide = Math.min(rw, rh);
				const longSide = Math.max(rw, rh);
				if (shortSide < minBump || longSide > maxBump) return;
				if (longSide / shortSide > 3.0) return;
				// 必须贴墙：矩形中心在墙延长线范围内，且与墙轨道距离 <= 墙厚+柱宽
				const rcx = (left + right) / 2;
				const rcy = (top + bottom) / 2;
				if (horizontal) {
					if (rcx < wallStart - 0.002 || rcx > wallEnd + 0.002) return;
					if (Math.abs(rcy - wallTrack) > wallThick / 2 + longSide) return;
				} else {
					if (rcy < wallStart - 0.002 || rcy > wallEnd + 0.002) return;
					if (Math.abs(rcx - wallTrack) > wallThick / 2 + longSide) return;
				}
				// 柱比墙厚的方向至少鼓出 minBump（不是墙线本身）
				const bumpExtent = horizontal
					? (rh - wallThick)
					: (rw - wallThick);
				if (bumpExtent < minBump * 0.3) return;
				const candidate: TraceElement = {
					id: `floor-ir-api-col-bump-${candidates.length}`,
					kind: 'column',
					label: `墙厚突变柱 ${candidates.length + 1}`,
					geometryType: 'rect',
					x: clamp(left),
					y: clamp(top),
					w: clamp(rw, 0.001, 1),
					h: clamp(rh, 0.001, 1),
					points: [
						{ x: left, y: top },
						{ x: right, y: top },
						{ x: right, y: bottom },
						{ x: left, y: bottom },
					],
					widthMm: Math.round(rw * mmPerNormalized),
					depthMm: Math.round(rh * mmPerNormalized),
					confidence: 0.62,
					status: 'candidate',
				};
				if (!candidates.some((e) => rectIntersects(e, candidate))) candidates.push(candidate);
			});
	});
	return candidates.slice(0, 24);
};

// ─── 柱识别：WallGraph Joint 节点探测候选 ──────────────────────────────
// 在墙图 T/L/cross 交点附近探测缺失的柱（从 filledRect 补充）
const detectJointProbeColumns = (
	joints: WallGraphDraft['joints'],
	existingColumns: TraceElement[],
	rawSegments: TraceSegment[],
	mmPerNormalized: number
): TraceElement[] => {
	const candidates: TraceElement[] = [];
	const minSide = 0.006;
	const maxSide = 0.055;
	// 大 filledRect 裁剪窗口：大结构柱与邻墙填充合并成的宽块，以节点为中心裁剪出柱尺寸
	// 窗口 = 最大合理柱径（约 1200mm）
	const clipHalfSize = Math.min(maxSide, 1200 / mmPerNormalized);
	const filledRects = rawSegments.filter((s) => s.pathKind === 'filledRect');
	joints.forEach((joint) => {
		// 跳过已有柱覆盖的节点
		const alreadyCovered = existingColumns.some((col) => {
			const cx = col.x + col.w / 2;
			const cy = col.y + col.h / 2;
			return Math.hypot(cx - joint.point.x, cy - joint.point.y) <= 0.04;
		});
		if (alreadyCovered) return;
		// 在节点附近搜索 filledRect 候选（扩大搜索半径，允许合并块的中心偏移）
		const probeRadius = 0.07;
		const nearbyRects = filledRects.filter((s) => {
			// 判断节点是否落在或接近 filledRect 内部
			const left = Math.min(s.x1, s.x2); const right = Math.max(s.x1, s.x2);
			const top = Math.min(s.y1, s.y2); const bottom = Math.max(s.y1, s.y2);
			const jx = joint.point.x; const jy = joint.point.y;
			// 节点在矩形内（允许小 pad）
			const inside = jx >= left - 0.005 && jx <= right + 0.005 && jy >= top - 0.005 && jy <= bottom + 0.005;
			// 或节点中心与矩形中心较近
			const cx = (left + right) / 2; const cy = (top + bottom) / 2;
			const near = Math.hypot(cx - jx, cy - jy) <= probeRadius;
			return inside || near;
		});
		nearbyRects.forEach((s) => {
			const left = Math.min(s.x1, s.x2);
			const right = Math.max(s.x1, s.x2);
			const top = Math.min(s.y1, s.y2);
			const bottom = Math.max(s.y1, s.y2);
			const rw = right - left;
			const rh = bottom - top;
			// 若矩形本身在合理尺寸内，直接用
			let colLeft = left; let colRight = right; let colTop = top; let colBottom = bottom;
			let colW = rw; let colH = rh;
			if (rw > maxSide || rh > maxSide) {
				// 大矩形：以节点坐标为中心，裁剪到 clipHalfSize 窗口
				// 方向参考：取实际矩形在节点处的交叉切面，而非简单中心
				const jx = joint.point.x; const jy = joint.point.y;
				colLeft = Math.max(left, jx - clipHalfSize);
				colRight = Math.min(right, jx + clipHalfSize);
				colTop = Math.max(top, jy - clipHalfSize);
				colBottom = Math.min(bottom, jy + clipHalfSize);
				colW = colRight - colLeft;
				colH = colBottom - colTop;
			}
			if (colW < minSide || colH < minSide) return;
			if (Math.max(colW, colH) / Math.min(colW, colH) > 3.5) return;
			const candidate: TraceElement = {
				id: `floor-ir-api-col-joint-${candidates.length}`,
				kind: 'column',
				label: `节点柱 ${candidates.length + 1}`,
				geometryType: 'rect',
				x: clamp(colLeft),
				y: clamp(colTop),
				w: clamp(colW, 0.001, 1),
				h: clamp(colH, 0.001, 1),
				points: [
					{ x: colLeft, y: colTop },
					{ x: colRight, y: colTop },
					{ x: colRight, y: colBottom },
					{ x: colLeft, y: colBottom },
				],
				widthMm: Math.round(colW * mmPerNormalized),
				depthMm: Math.round(colH * mmPerNormalized),
				confidence: rw > maxSide || rh > maxSide ? 0.72 : 0.68, // 裁剪后置信度稍高（主动定位）
				status: 'candidate',
			};
			if (!candidates.some((e) => rectIntersects(e, candidate)) &&
				!existingColumns.some((e) => rectIntersects(e, candidate))) {
				candidates.push(candidate);
			}
		});

		// ── A4b：filledRect 未出现时，从 line 段矩形重建嵌墙柱 ──────────────────
		// 只对 T/cross 节点（嵌墙柱信号最强），且该节点未被现有候选覆盖
		const isStructuralJoint = joint.type === 'T' || joint.type === 'cross';
		const alreadyHasCandidate = candidates.some((c) => {
			const ccx = c.x + c.w / 2; const ccy = c.y + c.h / 2;
			return Math.hypot(ccx - joint.point.x, ccy - joint.point.y) <= maxSide;
		}) || existingColumns.some((c) => {
			const ccx = c.x + c.w / 2; const ccy = c.y + c.h / 2;
			return Math.hypot(ccx - joint.point.x, ccy - joint.point.y) <= maxSide;
		});
		if (isStructuralJoint && !alreadyHasCandidate) {
			// 在 joint 极近范围（1.2×maxSide）内找短 line 段，严格避免误判
			const tightRadius = maxSide * 1.2;
			const nearLines = rawSegments.filter((s) => {
				if (s.pathKind !== 'line') return false;
				const len = segmentLength(s);
				if (len < minSide || len > maxSide * 1.1) return false;
				// 线段中点到 joint 的距离
				const scx = (s.x1 + s.x2) / 2; const scy = (s.y1 + s.y2) / 2;
				return Math.hypot(scx - joint.point.x, scy - joint.point.y) <= tightRadius;
			});
			if (nearLines.length >= 2) {
				const tolerance2 = 0.006;
				const hSegs = nearLines.filter(isHorizontal);
				const vSegs = nearLines.filter((s) => !isHorizontal(s));
				const covers2 = (seg: TraceSegment, start: number, end: number, track: number): boolean => {
					const segH = isHorizontal(seg);
					const segTrack = segH ? seg.y1 : seg.x1;
					if (Math.abs(segTrack - track) > tolerance2) return false;
					const a = segH ? Math.min(seg.x1, seg.x2) : Math.min(seg.y1, seg.y2);
					const b = segH ? Math.max(seg.x1, seg.x2) : Math.max(seg.y1, seg.y2);
					return a <= start + tolerance2 && b >= end - tolerance2;
				};
				for (let ti = 0; ti < hSegs.length; ti++) {
					const top2 = hSegs[ti];
					for (let bi = ti + 1; bi < hSegs.length; bi++) {
						const bot2 = hSegs[bi];
						const h2 = Math.abs(bot2.y1 - top2.y1);
						if (h2 < minSide || h2 > maxSide) continue;
						const oLeft  = Math.max(Math.min(top2.x1, top2.x2), Math.min(bot2.x1, bot2.x2));
						const oRight = Math.min(Math.max(top2.x1, top2.x2), Math.max(bot2.x1, bot2.x2));
						const w2 = oRight - oLeft;
						if (w2 < minSide || w2 > maxSide) continue;
						if (Math.max(w2, h2) / Math.min(w2, h2) > 2.5) continue;
						const hasL = vSegs.some((v) => covers2(v, top2.y1, bot2.y1, oLeft));
						const hasR = vSegs.some((v) => covers2(v, top2.y1, bot2.y1, oRight));
						if (!hasL && !hasR) continue;
						// 候选中心须仍在 tightRadius 内
						const ccx = oLeft + w2 / 2; const ccy = top2.y1 + h2 / 2;
						if (Math.hypot(ccx - joint.point.x, ccy - joint.point.y) > tightRadius * 1.3) continue;
						const lineCandidate: TraceElement = {
							id: `floor-ir-api-col-jl-${candidates.length}`,
							kind: 'column',
							label: `节点线柱 ${candidates.length + 1}`,
							geometryType: 'rect',
							x: clamp(oLeft), y: clamp(top2.y1),
							w: clamp(w2, 0.001, 1), h: clamp(h2, 0.001, 1),
							points: [
								{ x: oLeft, y: top2.y1 }, { x: oRight, y: top2.y1 },
								{ x: oRight, y: bot2.y1 }, { x: oLeft, y: bot2.y1 },
							],
							widthMm: Math.round(w2 * mmPerNormalized),
							depthMm: Math.round(h2 * mmPerNormalized),
							// 有两侧边→0.52，单侧→0.40；低于 filledRect，需验证器二次确认
							confidence: (hasL && hasR) ? 0.52 : 0.40,
							status: 'candidate',
						};
						if (!candidates.some((e) => rectIntersects(e, lineCandidate)) &&
							!existingColumns.some((e) => rectIntersects(e, lineCandidate))) {
							candidates.push(lineCandidate);
							break; // 每个 joint 只取第一个匹配矩形，防止重复
						}
					}
					if (candidates.some((c) => c.id.startsWith('floor-ir-api-col-jl-') &&
						Math.hypot((c.x + c.w / 2) - joint.point.x, (c.y + c.h / 2) - joint.point.y) <= tightRadius)) break;
				}
			}
		}
	});
	return candidates.slice(0, 36); // 扩大容量（复杂平面柱多）
};

// ─── 柱识别：尺寸簇 / 重复性分析 ─────────────────────────────────────
const buildColumnSizeClusters = (columns: TraceElement[], mmPerNormalized: number): number[][] => {
	const sizes = columns.map((col) => {
		const w = Math.round(col.w * mmPerNormalized);
		const h = Math.round(col.h * mmPerNormalized);
		return [Math.min(w, h), Math.max(w, h)] as [number, number];
	});
	// 按尺寸聚类：两个柱尺寸差 < 80mm 算同一簇
	const clusters: number[][] = [];
	const visited = new Set<number>();
	sizes.forEach((size, i) => {
		if (visited.has(i)) return;
		const cluster = [i];
		visited.add(i);
		for (let j = i + 1; j < sizes.length; j += 1) {
			if (visited.has(j)) continue;
			if (Math.abs(sizes[j][0] - size[0]) < 80 && Math.abs(sizes[j][1] - size[1]) < 80) {
				cluster.push(j);
				visited.add(j);
			}
		}
		clusters.push(cluster);
	});
	return clusters;
};

const isExplicitColumnGeometryCandidate = (col: TraceElement) => (
	col.id.includes('floor-ir-api-col-raw-') || col.id.includes('floor-ir-api-column-')
);

// ─── 柱识别：共线抑制辅助 ──────────────────────────────────────────
// 判断候选矩形是否为「墙端截面」而非真柱：
//   候选长轴与所有附着墙同向（无垂直墙附着）且中心落在墙轨道上 → 墙端截面，应被抑制
// 豁免条件：
//   ① 接近方形（w ≈ h）：方柱也可能贴墙端，不应被误排除
//   ② 高置信度 filledRect 来源（confidence ≥ 0.80）：最直接的柱信号，不做抑制
//   ③ 无附着墙：孤立柱（大厅/走廊），不做抑制
const isWallSectionNotColumn = (
	col: TraceElement,
	walls: TraceElement[],
	attachedWallIds: string[],
): boolean => {
	// ① 长宽比 < 1.8 的近似方形柱（含 400×600 等常见结构柱截面）→ 豁免
	//    原来用 abs(w-h)<0.003 只保护 ~165mm 以内差值，400×600 柱（diff≈0.0036）会被误判
	const _colAspect = Math.max(col.w, col.h) / Math.max(Math.min(col.w, col.h), 0.0001);
	if (_colAspect < 1.8) return false;                         // ① 长宽比<1.8，豁免
	if (col.confidence >= 0.80) return false;                    // ② filledRect 高置信，豁免
	if (attachedWallIds.length === 0) return false;              // ③ 无附着墙，豁免
	const colIsH = col.w > col.h + 0.002;
	const cx = col.x + col.w / 2;
	const cy = col.y + col.h / 2;
	const attachedWalls = walls.filter((w) => attachedWallIds.includes(w.id));
	const perpCount = attachedWalls.filter((w) => (w.w >= w.h) !== colIsH).length;
	// 若存在垂直方向附着墙 → 候选在 L/T/cross 节点处，可能是真柱，不抑制
	if (perpCount > 0) return false;
	// 所有附着墙均与候选长轴同向 → 校验候选中心是否落在墙轨道上
	const parallelWalls = attachedWalls.filter((w) => (w.w >= w.h) === colIsH);
	return parallelWalls.some((wall) => {
		const wallThick = wall.w >= wall.h ? wall.h : wall.w;
		const wallTrack = wall.w >= wall.h ? wall.y + wall.h / 2 : wall.x + wall.w / 2;
		const colTrack = colIsH ? cy : cx;
		return Math.abs(wallTrack - colTrack) <= wallThick * 0.9;
	});
};

// ─── 柱识别：等宽砌体件检测（构造柱 / 门垛排除依据） ──────────────────────
// 判断候选是否「薄边 ≈ 宿主墙厚」：
//   若最小边尺寸与任一附近墙体的厚度相差 ≤25%，且候选中心落在该墙的中心轨道上
//   → 形态为与墙面齐平的填充块（砌体构造柱/门垛），不属于独立结构柱序列
const isWallFlushMasonryPier = (
	col: TraceElement,
	walls: TraceElement[],
): boolean => {
	const colMinSide = Math.min(col.w, col.h);
	const cx = col.x + col.w / 2;
	const cy = col.y + col.h / 2;
	const proximityThreshold = Math.max(col.w, col.h) * 3.0;
	return walls.some((wall) => {
		if (nearestWallDistance(col, wall) > proximityThreshold) return false;
		const wallThick = wall.w >= wall.h ? wall.h : wall.w;
		// 薄边与墙厚误差 ≤25%（允许 PDF 光栅化偏差）
		if (Math.abs(colMinSide - wallThick) > wallThick * 0.25) return false;
		// 候选中心落在墙中心轨道上（±1.0倍墙厚）
		const wallIsH = wall.w >= wall.h;
		const wallTrack = wallIsH ? wall.y + wall.h / 2 : wall.x + wall.w / 2;
		const colTrack = wallIsH ? cy : cx;
		return Math.abs(colTrack - wallTrack) <= wallThick * 1.0;
	});
};

// ─── 柱识别：验证器（核心）──────────────────────────────────────────
// 对每个柱候选做多证据打分，并判定类型（主结构柱 vs 砌体加强柱）
const verifyAndClassifyColumn = (
	col: TraceElement,
	walls: TraceElement[],
	wallGraph: WallGraphDraft,
	sizeClusters: number[][],
	colIndex: number,
	allCandidates: TraceElement[],
	mmPerNormalized: number,
	gridPrior?: GridPriorOutput
): ColumnVerification => {
	const cx = col.x + col.w / 2;
	const cy = col.y + col.h / 2;
	const colCenter: TracePoint = { x: cx, y: cy };
	const colW = Math.round(col.w * mmPerNormalized);
	const colH = Math.round(col.h * mmPerNormalized);
	const colMaxSide = Math.max(col.w, col.h);
	const colMinSide = Math.min(col.w, col.h);
	const isSquare = Math.abs(col.w - col.h) < 0.003;
	const explicitGeometryCandidate = isExplicitColumnGeometryCandidate(col);
	const reviewFlags: ColumnReviewFlag[] = [];

	// 推断来源方法
	const sourceMethod: ColumnCandidateSource[] = [];
	if (col.id.includes('col-raw')) sourceMethod.push('rect_closure_raw');
	else if (col.id.includes('col-bump')) sourceMethod.push('wall_thickness_bump');
	else if (col.id.includes('col-joint')) sourceMethod.push('wall_joint_probe');
	else if (col.id.includes('column-')) sourceMethod.push('rect_closure_structured');
	if (col.confidence >= 0.85) sourceMethod.push('filled_rect_blob');

	// ── 几何分 ──
	let geometryScore = 0.5;
	// 闭合完整（has points = 4 corners）
	if (col.points && col.points.length === 4) geometryScore += 0.15;
	// 尺寸合理性：200mm~900mm 常见结构柱
	const sizeFit = (colW >= 150 && colW <= 1000 && colH >= 150 && colH <= 1000) ? 0.2 : -0.1;
	geometryScore += sizeFit;
	// 正方形加分
	if (isSquare) geometryScore += 0.1;
	geometryScore = Math.max(0, Math.min(1, geometryScore));

	// ── 墙关系分 ──
	let wallRelationScore = 0;
	// 邻接墙数量
	const attachedWallIds: string[] = [];
	const wallProximityThreshold = colMaxSide * 2.5;
	walls.forEach((wall) => {
		const dist = nearestWallDistance(col, wall);
		if (dist <= wallProximityThreshold || rectIntersects(col, wall)) {
			attachedWallIds.push(wall.id);
		}
	});
	const attachedCount = attachedWallIds.length;

	// ── 共线抑制：墙端截面早退出 ──
	// 弱推断候选（bump/joint）仍允许墙关系否决；显式矩形候选只打复核标记，不再一票否决。
	const looksLikeWallSection = isWallSectionNotColumn(col, walls, attachedWallIds);
	if (!explicitGeometryCandidate && looksLikeWallSection) {
		reviewFlags.push('possible_false_positive');
		return {
			columnType: 'column_candidate_unverified',
			shape: isSquare ? 'square' : 'rect',
			removability: 'unknown',
			structuralPriority: 'unknown',
			positionRole: 'unknown',
			confidence: Math.min(col.confidence * 0.35, 0.28),
			evidence: { geometry: 0, wallRelation: 0.1, repetition: 0, jointProximity: 0, gridIntersection: 0 },
			sourceMethod,
			reviewFlags,
		};
	}
	if (explicitGeometryCandidate && looksLikeWallSection) reviewFlags.push('possible_false_positive');

	if (attachedCount >= 3) wallRelationScore = 0.95;
	else if (attachedCount >= 2) wallRelationScore = 0.80;
	else if (attachedCount === 1) {
		if (explicitGeometryCandidate) wallRelationScore = 0.55;
		else {
			const hasFilledRectSource = col.confidence >= 0.85;
			wallRelationScore = hasFilledRectSource ? 0.40 : 0.18;
		}
	}
	else {
		wallRelationScore = explicitGeometryCandidate ? 0.45 : 0.15;
		if (!explicitGeometryCandidate) reviewFlags.push('weak_wall_binding');
	}

	// ── 是否在墙端/墙转角/洞口边（砌体加强柱信号） ──
	let wallBoundScore = 0;
	let atWallEnd = false;
	walls.forEach((wall) => {
		const horizontal = wall.w >= wall.h;
		const wallStart: TracePoint = horizontal
			? { x: wall.x, y: wall.y + wall.h / 2 }
			: { x: wall.x + wall.w / 2, y: wall.y };
		const wallEnd: TracePoint = horizontal
			? { x: wall.x + wall.w, y: wall.y + wall.h / 2 }
			: { x: wall.x + wall.w / 2, y: wall.y + wall.h };
		// 柱在墙端附近
		if (Math.hypot(cx - wallStart.x, cy - wallStart.y) < colMaxSide * 2.0 ||
			Math.hypot(cx - wallEnd.x, cy - wallEnd.y) < colMaxSide * 2.0) {
			atWallEnd = true;
			wallBoundScore += 0.3;
		}
	});
	wallBoundScore = Math.min(1, wallBoundScore);

	// ── Joint 邻近分 ──
	let jointProximityScore = 0;
	const nearestJoint = wallGraph.joints.reduce((best, joint) => {
		const dist = Math.hypot(joint.point.x - cx, joint.point.y - cy);
		return dist < best.dist ? { dist, joint } : best;
	}, { dist: Number.POSITIVE_INFINITY, joint: undefined as WallGraphDraft['joints'][0] | undefined });
	if (nearestJoint.dist <= 0.02) jointProximityScore = 1.0;
	else if (nearestJoint.dist <= 0.04) jointProximityScore = 0.7;
	else if (nearestJoint.dist <= 0.06) jointProximityScore = 0.4;

	// ── 重复性分 ──
	let repetitionScore = 0;
	const clusterIndex = sizeClusters.findIndex((cluster) => cluster.includes(colIndex));
	const clusterSize = clusterIndex >= 0 ? sizeClusters[clusterIndex].length : 1;
	if (clusterSize >= 6) repetitionScore = 1.0;
	else if (clusterSize >= 3) repetitionScore = 0.7;
	else if (clusterSize >= 2) repetitionScore = 0.4;
	if (clusterSize <= 1) reviewFlags.push('size_outlier');

	// ── 框架网判定分（是否成列/成阵）──
	let frameGridScore = 0;
	// 检查横向/纵向是否有多个同尺寸柱成列（track 接近）
	const sameClusterCols = clusterIndex >= 0
		? sizeClusters[clusterIndex].map((i) => allCandidates[i]).filter(Boolean)
		: [];
	if (sameClusterCols.length >= 2) {
		// 按 x 坐标排序，检查等间距
		const xSorted = [...sameClusterCols].sort((a, b) => a.x - b.x);
		const ySorted = [...sameClusterCols].sort((a, b) => a.y - b.y);
		const xGaps = xSorted.slice(1).map((c, i) => Math.abs(c.x - xSorted[i].x));
		const yGaps = ySorted.slice(1).map((c, i) => Math.abs(c.y - ySorted[i].y));
		// 如果有 >= 2 个等间距柱，框架网分高
		const hasRegularX = xGaps.length >= 2 && xGaps.some((g) => xGaps.filter((g2) => Math.abs(g2 - g) < 0.02).length >= 2);
		const hasRegularY = yGaps.length >= 2 && yGaps.some((g) => yGaps.filter((g2) => Math.abs(g2 - g) < 0.02).length >= 2);
		if (hasRegularX || hasRegularY) frameGridScore = 0.8;
		else if (sameClusterCols.length >= 3) frameGridScore = 0.4;
	}

	// ── Grid Prior 轴交点分 ──
	let gridIntersectionScore = 0;
	if (gridPrior && gridPrior.probableColumnNodes.length > 0) {
		const nearestNode = gridPrior.probableColumnNodes.reduce((best, node) => {
			const dist = Math.hypot(node.point[0] - cx, node.point[1] - cy);
			return dist < best.dist ? { dist, node } : best;
		}, { dist: Number.POSITIVE_INFINITY, node: undefined as ProbableColumnNode | undefined });
		const distMm = nearestNode.dist * mmPerNormalized;
		if (distMm <= 30) gridIntersectionScore = 1.0;
		else if (distMm <= 60) gridIntersectionScore = 0.7;
		else if (distMm <= 100) gridIntersectionScore = 0.4;
		else if (distMm <= 200) gridIntersectionScore = 0.15;
	}

	// ── 类型判定：主结构柱 vs 砌体加强柱 ──
	// 核心逻辑：frameGridScore 高 → 主结构柱，wallBoundScore 高且 frameGridScore 低 → 砌体加强柱
	let columnType: ColumnType;
	let removability: ColumnRemovability;
	let structuralPriority: StructuralPriority;

	// 综合分（含 Grid Prior 加权）
	const hasGridPrior = gridPrior && gridPrior.probableColumnNodes.length > 0;
	const totalScore = hasGridPrior
		? geometryScore * 0.15 + wallRelationScore * 0.20 + jointProximityScore * 0.15
			+ repetitionScore * 0.15 + frameGridScore * 0.15 + gridIntersectionScore * 0.20
		: geometryScore * 0.20 + wallRelationScore * 0.25 + jointProximityScore * 0.20
			+ repetitionScore * 0.20 + frameGridScore * 0.15;

	if (totalScore < 0.30) {
		columnType = 'column_candidate_unverified';
		removability = 'unknown';
		structuralPriority = 'unknown';
		reviewFlags.push('possible_false_positive');
	} else if (gridIntersectionScore >= 0.7 || frameGridScore >= 0.5 || (repetitionScore >= 0.6 && jointProximityScore >= 0.5)) {
		// 独立框架柱信号强（含轴交点匹配）
		columnType = 'primary_structural_column';
		removability = 'non_removable';
		structuralPriority = 'primary';
	} else if (wallBoundScore >= 0.4 && atWallEnd && frameGridScore < 0.3 && gridIntersectionScore < 0.3) {
		// 墙端/转角加强柱信号（不在轴交点附近）
		columnType = 'masonry_reinforcement_pier';
		removability = 'conditional';
		structuralPriority = 'secondary';
		reviewFlags.push('needs_structural_review');
	} else if (nearestJoint.dist <= 0.03 && nearestJoint.joint?.type === 'T') {
		// T 形节点边柱
		columnType = 'shear_wall_edge_pier';
		removability = 'non_removable';
		structuralPriority = 'primary';
	} else if (attachedCount >= 2) {
		// 有墙连接但无法明确分类 → 暂判主结构柱
		columnType = 'primary_structural_column';
		removability = 'non_removable';
		structuralPriority = 'primary';
	} else {
		columnType = 'column_candidate_unverified';
		removability = 'unknown';
		structuralPriority = 'unknown';
		reviewFlags.push('needs_structural_review');
	}

	// 更新置信度：综合打分
	const confidence = Math.max(0.25, Math.min(0.98, col.confidence * 0.4 + totalScore * 0.6));


	// two-step position role classification
	let positionRole: ColumnVerification['positionRole'] = 'unknown';
	if (attachedCount === 0) {
		positionRole = 'isolated';
	} else if (attachedCount >= 3) {
		positionRole = 'embedded';
	} else {
		const wallCenters = walls.map((w) => ({ x: w.x + w.w / 2, y: w.y + w.h / 2 }));
		if (wallCenters.length >= 4) {
			const minX = Math.min(...wallCenters.map((p) => p.x));
			const maxX = Math.max(...wallCenters.map((p) => p.x));
			const minY = Math.min(...wallCenters.map((p) => p.y));
			const maxY = Math.max(...wallCenters.map((p) => p.y));
			const margin = colMaxSide * 3;
			const onEdge = cx <= minX + margin || cx >= maxX - margin || cy <= minY + margin || cy >= maxY - margin;
			positionRole = onEdge ? 'perimeter' : 'embedded';
		} else {
			positionRole = attachedCount >= 1 ? 'embedded' : 'isolated';
		}
	}

	return {
		columnType,
		shape: isSquare ? 'square' : 'rect',
		removability,
		structuralPriority,
		positionRole,
		confidence,
		evidence: {
			geometry: Math.round(geometryScore * 100) / 100,
			wallRelation: Math.round(wallRelationScore * 100) / 100,
			repetition: Math.round(repetitionScore * 100) / 100,
			jointProximity: Math.round(jointProximityScore * 100) / 100,
			gridIntersection: Math.round(gridIntersectionScore * 100) / 100,
		},
		sourceMethod,
		reviewFlags,
	};

};
// ═══════════════════════════════════════════════════════════════════════
// ─── Grid Prior Engine：轴线/柱网结构先验系统 ─────────────────────────
// ═══════════════════════════════════════════════════════════════════════

/** 检测图面主方向（返回角度，度，0=水平 90=垂直） */
const detectDominantDirections = (segments: TraceSegment[]): number[] => {
	// 统计水平 vs 垂直线段的长度加权
	let hLen = 0;
	let vLen = 0;
	for (const s of segments) {
		if (s.pathKind === 'rect' || s.pathKind === 'filledRect' || s.pathKind === 'curve') continue;
		const dx = Math.abs(s.x2 - s.x1);
		const dy = Math.abs(s.y2 - s.y1);
		const len = Math.hypot(dx, dy);
		if (len < 0.008) continue;
		const angle = Math.atan2(dy, dx) * 180 / Math.PI;
		if (angle <= 5) hLen += len;
		else if (angle >= 85) vLen += len;
	}
	const dirs: number[] = [];
	if (hLen > 0) dirs.push(0);
	if (vLen > 0) dirs.push(90);
	return dirs;
};

/** 从 dash_dot 线段和贯通长线中检测轴线 */
const detectAxisLines = (
	segments: TraceSegment[],
	classifiedTexts: ClassifiedText[],
	circles: DetectedCircle[],
	focusBounds: { minX: number; maxX: number; minY: number; maxY: number } | undefined,
	mmPerNormalized: number
): GridAxis[] => {
	const axes: GridAxis[] = [];
	const axisLabelCircles = circles.filter((c) => c.probableRole === 'axis_label_circle');
	const axisLabelTexts = classifiedTexts.filter((t) => t.role === 'axis_label');

	// 候选来源 1：dash_dot 线段（最可靠的轴线特征）
	const dashDotLines = segments.filter((s) =>
		s.dashPattern === 'dash_dot' &&
		s.pathKind === 'line' &&
		segmentLength(s) > 0.05
	);

	// 候选来源 2：贯通长线（跨越焦点域 >70% 的细线）
	const focusW = focusBounds ? (focusBounds.maxX - focusBounds.minX) : 1;
	const focusH = focusBounds ? (focusBounds.maxY - focusBounds.minY) : 1;
	const throughLines = segments.filter((s) => {
		if (s.pathKind !== 'line' || s.dashPattern === 'dashed') return false;
		const dx = Math.abs(s.x2 - s.x1);
		const dy = Math.abs(s.y2 - s.y1);
		const len = Math.hypot(dx, dy);
		const angle = Math.atan2(Math.min(dx, dy), Math.max(dx, dy)) * 180 / Math.PI;
		if (angle > 3) return false; // 非正交
		if (dx > dy) return len > focusW * 0.70; // 水平贯通
		return len > focusH * 0.70; // 垂直贯通
	});

	// 合并候选
	const candidates = [...dashDotLines, ...throughLines];
	// 去重：相同 track ± 0.005 的合并
	const used = new Set<number>();
	for (let i = 0; i < candidates.length; i++) {
		if (used.has(i)) continue;
		const s = candidates[i];
		const dx = Math.abs(s.x2 - s.x1);
		const dy = Math.abs(s.y2 - s.y1);
		const isH = dx > dy;
		const track = isH ? (s.y1 + s.y2) / 2 : (s.x1 + s.x2) / 2;
		const direction: GridAxisDirection = isH ? 'horizontal' : 'vertical';

		// 合并同 track 的候选
		for (let j = i + 1; j < candidates.length; j++) {
			if (used.has(j)) continue;
			const s2 = candidates[j];
			const isH2 = Math.abs(s2.x2 - s2.x1) > Math.abs(s2.y2 - s2.y1);
			if (isH2 !== isH) continue;
			const track2 = isH2 ? (s2.y1 + s2.y2) / 2 : (s2.x1 + s2.x2) / 2;
			if (Math.abs(track2 - track) < 0.005) used.add(j);
		}

		// 关联轴号：检查轴线端点附近是否有轴号圆 + 轴号文字
		let label: string | undefined;
		const endpoints = [
			[Math.min(s.x1, s.x2), (s.y1 + s.y2) / 2],
			[Math.max(s.x1, s.x2), (s.y1 + s.y2) / 2],
			[(s.x1 + s.x2) / 2, Math.min(s.y1, s.y2)],
			[(s.x1 + s.x2) / 2, Math.max(s.y1, s.y2)],
		] as [number, number][];
		for (const ep of endpoints) {
			// 找最近的轴号圆
			const nearCircle = axisLabelCircles.find((c) =>
				Math.hypot(c.center[0] - ep[0], c.center[1] - ep[1]) < 0.04
			);
			if (nearCircle) {
				// 找圆内/圆旁的轴号文字
				const nearText = axisLabelTexts.find((t) =>
					Math.hypot(t.x - nearCircle.center[0], t.y - nearCircle.center[1]) < nearCircle.radiusNorm * 2.5
				);
				if (nearText) { label = nearText.text; break; }
			}
		}

		const confidence = s.dashPattern === 'dash_dot' ? 0.90 : (label ? 0.80 : 0.55);
		const line: [[number, number], [number, number]] = isH
			? [[Math.min(s.x1, s.x2), track], [Math.max(s.x1, s.x2), track]]
			: [[track, Math.min(s.y1, s.y2)], [track, Math.max(s.y1, s.y2)]];

		axes.push({ id: `axis-${axes.length + 1}`, direction, line, label, confidence });
	}

	return axes.slice(0, 60);
};

/** 构建轴交点 */
const buildGridIntersections = (axes: GridAxis[]): GridIntersection[] => {
	const intersections: GridIntersection[] = [];
	const hAxes = axes.filter((a) => a.direction === 'horizontal');
	const vAxes = axes.filter((a) => a.direction === 'vertical');
	for (const h of hAxes) {
		const hy = h.line[0][1];
		const hx1 = Math.min(h.line[0][0], h.line[1][0]);
		const hx2 = Math.max(h.line[0][0], h.line[1][0]);
		for (const v of vAxes) {
			const vx = v.line[0][0];
			const vy1 = Math.min(v.line[0][1], v.line[1][1]);
			const vy2 = Math.max(v.line[0][1], v.line[1][1]);
			// 交点在两条轴线范围内
			if (vx >= hx1 - 0.01 && vx <= hx2 + 0.01 && hy >= vy1 - 0.01 && hy <= vy2 + 0.01) {
				intersections.push({
					id: `grid-int-${intersections.length + 1}`,
					point: [vx, hy],
					axisIds: [h.id, v.id],
					confidence: Math.min(h.confidence, v.confidence),
				});
			}
		}
	}
	return intersections;
};

/** 构建轴间距聚类 */
const buildGridSpacingClusters = (axes: GridAxis[], mmPerNormalized: number): GridSpacingCluster[] => {
	const clusters: GridSpacingCluster[] = [];
	for (const dir of ['horizontal', 'vertical'] as GridAxisDirection[]) {
		const dirAxes = axes.filter((a) => a.direction === dir);
		if (dirAxes.length < 2) continue;
		const tracks = dirAxes.map((a) => dir === 'horizontal' ? a.line[0][1] : a.line[0][0]).sort((a, b) => a - b);
		const spacings: number[] = [];
		for (let i = 1; i < tracks.length; i++) {
			spacings.push(Math.round((tracks[i] - tracks[i - 1]) * mmPerNormalized));
		}
		// 聚类：tolerance 200mm
		const seen = new Map<number, number>();
		for (const sp of spacings) {
			const bucket = Math.round(sp / 200) * 200;
			seen.set(bucket, (seen.get(bucket) ?? 0) + 1);
		}
		for (const [spacingMm, count] of seen) {
			if (count >= 1 && spacingMm >= 1500 && spacingMm <= 15000) {
				clusters.push({ direction: dir, spacingMm, count });
			}
		}
	}
	return clusters.sort((a, b) => b.count - a.count);
};

/** 从轴交点推断高概率柱位 */
const inferProbableColumnNodes = (
	intersections: GridIntersection[],
	axes: GridAxis[],
	spacingClusters: GridSpacingCluster[]
): ProbableColumnNode[] => {
	const nodes: ProbableColumnNode[] = [];
	// 来源 A：每个轴交点 → probableColumnNode
	for (const inter of intersections) {
		nodes.push({
			point: inter.point,
			source: 'axis_intersection',
			linkedIntersectionId: inter.id,
			confidence: inter.confidence * 0.9,
		});
	}
	// 来源 B：沿轴线等间距重复点（当轴交点不足时补充）
	if (intersections.length < 4 && spacingClusters.length > 0) {
		for (const axis of axes) {
			const perpClusters = spacingClusters.filter((c) => c.direction !== axis.direction);
			if (perpClusters.length === 0) continue;
			const spacing = perpClusters[0].spacingMm;
			const isH = axis.direction === 'horizontal';
			const track = isH ? axis.line[0][1] : axis.line[0][0];
			const start = isH ? Math.min(axis.line[0][0], axis.line[1][0]) : Math.min(axis.line[0][1], axis.line[1][1]);
			const end = isH ? Math.max(axis.line[0][0], axis.line[1][0]) : Math.max(axis.line[0][1], axis.line[1][1]);
			const stepNorm = spacing / 21000; // approximate
			for (let pos = start + stepNorm; pos < end - stepNorm * 0.3; pos += stepNorm) {
				const pt: [number, number] = isH ? [pos, track] : [track, pos];
				if (!nodes.some((n) => Math.hypot(n.point[0] - pt[0], n.point[1] - pt[1]) < stepNorm * 0.3)) {
					nodes.push({ point: pt, source: 'repeat_pattern', confidence: 0.45 });
				}
			}
		}
	}
	return nodes.slice(0, 200);
};

/** 推断墙对齐带 */
const inferWallAlignmentBands = (axes: GridAxis[]): WallAlignmentBand[] => {
	const bands: WallAlignmentBand[] = [];
	for (const axis of axes) {
		// 轴中心带：偏移 0
		bands.push({ axisId: axis.id, direction: axis.direction, offsetNorm: 0, confidence: axis.confidence * 0.8 });
		// 常见偏移带：± 半墙厚（约 100–150mm ≈ 0.005–0.007 normalized）
		for (const offset of [0.005, 0.007, 0.010]) {
			bands.push({ axisId: axis.id, direction: axis.direction, offsetNorm: offset, confidence: axis.confidence * 0.5 });
			bands.push({ axisId: axis.id, direction: axis.direction, offsetNorm: -offset, confidence: axis.confidence * 0.5 });
		}
	}
	return bands;
};

/** Grid Prior Engine 总入口 */
const runGridPriorEngine = (
	rawSegments: TraceSegment[],
	classifiedTexts: ClassifiedText[],
	circles: DetectedCircle[],
	focusBounds: { minX: number; maxX: number; minY: number; maxY: number } | undefined,
	mmPerNormalized: number
): GridPriorOutput => {
	const dominantDirections = detectDominantDirections(rawSegments);
	const axes = detectAxisLines(rawSegments, classifiedTexts, circles, focusBounds, mmPerNormalized);
	const intersections = buildGridIntersections(axes);
	const spacingClusters = buildGridSpacingClusters(axes, mmPerNormalized);
	const probableColumnNodes = inferProbableColumnNodes(intersections, axes, spacingClusters);
	const wallAlignmentBands = inferWallAlignmentBands(axes);
	return { dominantDirections, axes, intersections, spacingClusters, probableColumnNodes, wallAlignmentBands };
};

// ─── 柱识别：模块总入口 ──────────────────────────────────────────────
const runColumnDetectionPipeline = (
	structuredSegments: TraceSegment[],
	focusedRawSegments: TraceSegment[],
	walls: TraceElement[],
	wallGraph: WallGraphDraft,
	mmPerNormalized: number,
	gridPrior?: GridPriorOutput,
	trustedScale = true,
	pageAspectYX = 1.0
): { columns: TraceElement[]; reviewIssues: ReviewIssue[] } => {
	const _dbg = process.env.NODE_ENV !== 'production';
	// A1: 结构化矩形闭合候选
	const rectStructured = buildColumnCandidates(structuredSegments, mmPerNormalized);
	if (_dbg) console.log('[柱诊断] A1 structuredRect:', rectStructured.length);
	// A2: 原始线段候选（含 filledRect 主路径 + rect 回退路径）
	const rectRawAll = buildColumnCandidatesFromRaw(focusedRawSegments, mmPerNormalized, trustedScale);
	const rectRaw = rectRawAll.filter((rc) => !rectStructured.some((ec) => rectIntersects(ec, rc)));
	if (_dbg) console.log('[柱诊断] A2 raw:', rectRawAll.length, '→去重后:', rectRaw.length,
		'| filledRect来源:', rectRaw.filter((c) => c.confidence >= 0.85).length,
		'| rect来源:', rectRaw.filter((c) => c.confidence < 0.85).length);
	// 合并并用墙邻近过滤明显噪声
	let allCandidates = [...rectStructured, ...rectRaw];
	const beforeWallFilter = allCandidates.length;
	if (walls.length > 0) {
		const removed: string[] = [];
		allCandidates = allCandidates.filter((col) => {
			// 柱是第一性结构证据：A1/A2 显式矩形候选不能由墙检测结果决定生死。
			if (isExplicitColumnGeometryCandidate(col) || col.confidence >= 0.85) return true;
			const maxDist = Math.max(col.w, col.h) * 4.0;
			const keep = walls.some((wall) => nearestWallDistance(col, wall) <= maxDist);
			if (!keep && _dbg) removed.push(`${Math.round(col.w*mmPerNormalized)}x${Math.round(col.h*mmPerNormalized)}mm@(${col.x.toFixed(3)},${col.y.toFixed(3)})`);
			return keep;
		});
		if (_dbg) console.log('[柱诊断] 墙邻近过滤:', beforeWallFilter, '→', allCandidates.length,
			'| 移除低置信候选:', removed.length, removed.length > 0 ? removed : '');
	}
	// A3: 墙厚突变候选
	const bumpCandidates = detectWallThicknessBumpColumns(walls, focusedRawSegments, mmPerNormalized)
		.filter((bc) => !allCandidates.some((ec) => rectIntersects(ec, bc)));
	if (_dbg) console.log('[柱诊断] A3 bump:', bumpCandidates.length);
	allCandidates.push(...bumpCandidates);
	// A4: WallGraph Joint 节点探测（后 buildWallGraphDraft，此处需提前构建临时 wallGraph）
	// 这里 wallGraph 由调用方传入
	const jointCandidates = detectJointProbeColumns(wallGraph.joints, allCandidates, focusedRawSegments, mmPerNormalized);
	if (_dbg) console.log('[柱诊断] A4 joint:', jointCandidates.length);
	allCandidates.push(...jointCandidates);

	// A5: 伪柱抑制——密集等间距小块（楼梯踏步 / 符号重复）
	// 判断：若有 ≥4 个候选，沿单轴等间距（间距偏差 < 20%），且尺寸极小（两边均 < 150mm），判为楼梯踏步，全组排除
	const stairTreadMaxSideMm = 150;
	const stairTreadMinCount = 4;
	const stairSpacingTolerance = 0.20; // 允许间距偏差 20%
	const suppressedIds = new Set<string>();
	// 按 x 轴方向扫描：找 x 坐标近似等差、y 坐标一致的小块组
	const tinyMm = stairTreadMaxSideMm / mmPerNormalized;
	const smallCandidates = allCandidates.filter((c) => c.w < tinyMm && c.h < tinyMm);
	if (smallCandidates.length >= stairTreadMinCount) {
		// 按 cy 分组（同一水平带），再看 cx 是否等间距
		const byCy = new Map<number, typeof smallCandidates>();
		smallCandidates.forEach((c) => {
			const cy = Math.round((c.y + c.h / 2) * 500) / 500; // 精度到 0.002
			if (!byCy.has(cy)) byCy.set(cy, []);
			byCy.get(cy)!.push(c);
		});
		byCy.forEach((group) => {
			if (group.length < stairTreadMinCount) return;
			const sorted = [...group].sort((a, b) => a.x - b.x);
			const gaps = sorted.slice(1).map((c, i) => (c.x + c.w / 2) - (sorted[i].x + sorted[i].w / 2));
			const medGap = gaps.sort((a, b) => a - b)[Math.floor(gaps.length / 2)];
			const isEquallySpaced = medGap > 0.002 && gaps.every((g) => Math.abs(g - medGap) / medGap < stairSpacingTolerance);
			if (isEquallySpaced) group.forEach((c) => suppressedIds.add(c.id));
		});
		// 同理按 cx 分组（同一垂直带）
		const byCx = new Map<number, typeof smallCandidates>();
		smallCandidates.forEach((c) => {
			const cx = Math.round((c.x + c.w / 2) * 500) / 500;
			if (!byCx.has(cx)) byCx.set(cx, []);
			byCx.get(cx)!.push(c);
		});
		byCx.forEach((group) => {
			if (group.length < stairTreadMinCount) return;
			const sorted = [...group].sort((a, b) => a.y - b.y);
			const gaps = sorted.slice(1).map((c, i) => (c.y + c.h / 2) - (sorted[i].y + sorted[i].h / 2));
			const medGap = gaps.sort((a, b) => a - b)[Math.floor(gaps.length / 2)];
			const isEquallySpaced = medGap > 0.002 && gaps.every((g) => Math.abs(g - medGap) / medGap < stairSpacingTolerance);
			if (isEquallySpaced) group.forEach((c) => suppressedIds.add(c.id));
		});
	}
	if (suppressedIds.size > 0) {
		if (_dbg) console.log('[柱诊断] A5 stair抑制:', suppressedIds.size);
		allCandidates = allCandidates.filter((c) => !suppressedIds.has(c.id));
	}
	if (_dbg) console.log('[柱诊断] 验证前总候选:', allCandidates.length,
		'| filledRect:', allCandidates.filter(c => c.confidence >= 0.85).length,
		'| mm范围:', allCandidates.slice(0,3).map(c => `${Math.round(c.w*mmPerNormalized)}x${Math.round(c.h*mmPerNormalized)}`));

	// 尺寸簇分析
	const sizeClusters = buildColumnSizeClusters(allCandidates, mmPerNormalized);

	// 验证 + 分类
	const reviewIssues: ReviewIssue[] = [];
	const verified = allCandidates.map((col, i) => {
		const verification = verifyAndClassifyColumn(col, walls, wallGraph, sizeClusters, i, allCandidates, mmPerNormalized, gridPrior);
		// 更新 label 和 confidence
		const typeLabel: Record<ColumnType, string> = {
			'primary_structural_column': '主结构柱',
			'masonry_reinforcement_pier': '构造柱',
			'shear_wall_edge_pier': '剪力墙边柱',
			'encased_or_interior_column': '室内包柱',
			'column_candidate_unverified': '未验证柱候选',
		};
		const updated: TraceElement = {
			...col,
			label: `${typeLabel[verification.columnType]} ${i + 1}`,
			confidence: verification.confidence,
			columnVerification: verification,
		};
		// 生成 review issues
		if (verification.reviewFlags.includes('possible_false_positive')) {
			reviewIssues.push({
				id: `review-col-fp-${col.id}`,
				type: 'suspected_missing_column',
				severity: 'info',
				message: `柱候选 ${col.id} 综合得分偏低，可能为误判。`,
				targetIds: [col.id],
			});
		}
		if (verification.reviewFlags.includes('type_conflict')) {
			reviewIssues.push({
				id: `review-col-type-${col.id}`,
				type: 'suspected_missing_column',
				severity: 'warning',
				message: `柱候选 ${col.id} 类型判定存在冲突，需人工复核。`,
				targetIds: [col.id],
			});
		}
		return updated;
	});

	// 过滤掉极低置信度候选
	const confFiltered = verified.filter((col) => col.confidence >= 0.35);
	if (_dbg) {
		const dropped = verified.filter((col) => col.confidence < 0.35);
		console.log('[柱诊断] 验证后:', verified.length, '→ conf≥0.35:', confFiltered.length,
			'| 被过滤(conf<0.35):', dropped.length,
			dropped.length > 0 ? dropped.map(c => `conf=${c.confidence.toFixed(2)} ${Math.round(c.w*mmPerNormalized)}x${Math.round(c.h*mmPerNormalized)}mm`) : '');
	}

	// ── §结构柱形态硬过滤（矢量PDF误判根治，以长宽比为主判据）──────────────────────
	// 实测数据（酒店建筑矢量PDF）：
	//   误判墙垛/门垛：minSide ≈ 317mm，aspect ≈ 2.6~2.7（细长条，与墙方向平行）
	//   真实结构柱   ：minSide ≈ 400~600mm，aspect ≈ 1.0~1.5（近方形）
	// 矢量PDF 中 wall.h 默认值 ≈ 0.004（~67mm），不能用于"等宽比较"；
	// 正确判据是形态比例：
	//   • aspect ≥ 2.2 → 细长条，无论 minSide 多大均为墙体嵌入件，排除
	//   • aspect < 2.2 且 minSide < 150mm → 极小噪声，排除
	// 豁免：轴交点得分 ≥ 0.5，或 repetitionScore ≥ 0.65（成列重复 = 框架柱阵）
	const COLUMN_MAX_ASPECT = 2.2;   // 结构柱允许最大长宽比
	const COLUMN_MIN_SIDE_MM = 150;  // 极小噪声下限（mm）
	const finalColumns = confFiltered.filter((col) => {
		const cv = col.columnVerification;
		// 豁免1：轴网交点强证据
		if ((cv?.evidence.gridIntersection ?? 0) >= 0.5) return true;
		// 豁免2：成列重复性强（确认为框架柱阵）
		if ((cv?.evidence.repetition ?? 0) >= 0.65) return true;
		// 使用物理 mm 计算：Y 轴需乘以 pageAspectYX 修正（非正方形页面归一化补偿）
		const colWidthMm = col.w * mmPerNormalized;
		const colDepthMm = col.h * mmPerNormalized * pageAspectYX;
		const colMinMm = Math.min(colWidthMm, colDepthMm);
		const colAspect = Math.max(colWidthMm, colDepthMm) / Math.max(Math.min(colWidthMm, colDepthMm), 1);
		// 极小噪声：排除
		if (colMinMm < COLUMN_MIN_SIDE_MM) {
			if (_dbg) console.log('[柱诊断] 极小噪声排除:', col.label, `minMm=${Math.round(colMinMm)}`);
			return false;
		}
		// 细长条（aspect ≥ 2.2）→ 墙体嵌入件/门垛，排除
		if (colAspect >= COLUMN_MAX_ASPECT) {
			if (_dbg) console.log('[柱诊断] 细长件排除(墙垛/门垛):', col.label,
				`${Math.round(colWidthMm)}x${Math.round(colDepthMm)}mm aspect=${colAspect.toFixed(2)}`);
			return false;
		}
		return true;
	});
	if (_dbg && finalColumns.length !== confFiltered.length) {
		console.log('[柱诊断] 形态过滤:', confFiltered.length, '→', finalColumns.length);
	}

	return { columns: finalColumns, reviewIssues };
};

const nearestWallDistance = (element: TraceElement, wall: TraceElement) => {
	const cx = element.x + element.w / 2;
	const cy = element.y + element.h / 2;
	const horizontal = wall.w >= wall.h;
	if (horizontal) {
		const x1 = wall.x;
		const x2 = wall.x + wall.w;
		const projection = clamp(cx, x1, x2);
		return Math.hypot(cx - projection, cy - (wall.y + wall.h / 2));
	}
	const y1 = wall.y;
	const y2 = wall.y + wall.h;
	const projection = clamp(cy, y1, y2);
	return Math.hypot(cx - (wall.x + wall.w / 2), cy - projection);
};

const distancePointToSegment = (point: TracePoint, a: TracePoint, b: TracePoint) => {
	const dx = b.x - a.x;
	const dy = b.y - a.y;
	const lengthSq = dx * dx + dy * dy;
	if (lengthSq <= 0.0000001) return Math.hypot(point.x - a.x, point.y - a.y);
	const t = clamp(((point.x - a.x) * dx + (point.y - a.y) * dy) / lengthSq);
	const px = a.x + t * dx;
	const py = a.y + t * dy;
	return Math.hypot(point.x - px, point.y - py);
};

const distancePointToWallElement = (point: TracePoint, wall: TraceElement) => {
	const [a, b] = wallElementCenterline(wall);
	return distancePointToSegment(point, a, b);
};

const bindOpeningToNearestWall = (opening: TraceElement, walls: TraceElement[]) => {
	let best: { wall?: TraceElement; distance: number } = { distance: Number.POSITIVE_INFINITY };
	walls.forEach((wall) => {
		const distance = nearestWallDistance(opening, wall);
		if (distance < best.distance) best = { wall, distance };
	});
	if (best.distance > 0.035) return undefined;
	const hostWall = best.wall;
	if (!hostWall) return undefined;
	// 优先返回拥有 logicalWallId 的墙（连续逻辑墙），以确保 hostWallId 指向完整墙体
	const logicalId = (hostWall as TraceElement & { logicalWallId?: string }).logicalWallId;
	if (logicalId) {
		// 找逻辑墙中距离最近的主段（ID不变，但附带 logicalWallId 供验证管道消费）
		return hostWall;
	}
	return hostWall;
};

const buildDoorCandidates = (segments: TraceSegment[], walls: TraceElement[], mmPerNormalized: number): TraceElement[] => {
	const curveSegments = segments.filter((segment) => segment.pathKind === 'curve' && segmentLength(segment) >= 0.008 && segmentLength(segment) <= 0.12);
	// 用于检测门扇直线（门弧 + 门扇直线 = 平开门；仅门弧 = 弧形/推拉门符号）
	const leafCandidateSegs = segments.filter((s) =>
		s.pathKind !== 'curve' && s.pathKind !== 'rect' && s.pathKind !== 'filledRect' &&
		segmentLength(s) >= 0.008 && segmentLength(s) <= 0.12
	);
	const doors: TraceElement[] = [];
	curveSegments.forEach((segment) => {
		const x = Math.min(segment.x1, segment.x2);
		const y = Math.min(segment.y1, segment.y2);
		const w = Math.abs(segment.x2 - segment.x1);
		const h = Math.abs(segment.y2 - segment.y1);
		const size = Math.max(w, h);
		if (size < 0.012 || size > 0.09) return;
		// E1: 弧质量过滤 — 门弧应近似 90° 四分之一圆（bbox 宽高比接近 1:1）
		const arcAspect = Math.min(w, h) / Math.max(w, h);
		if (arcAspect < 0.35) return; // 过度扁平弧段，非门弧
		// 检测门扇直线：是否存在一条直线与弧端点重合且长度相近（平开门特征）
		const arcDiag = segmentLength(segment);
		const arcStart = { x: segment.x1, y: segment.y1 };
		const arcEnd = { x: segment.x2, y: segment.y2 };
		const leafTol = arcDiag * 0.28;
		const hasLeaf = leafCandidateSegs.some((ls) => {
			const lsLen = segmentLength(ls);
			if (lsLen < arcDiag * 0.65 || lsLen > arcDiag * 1.45) return false;
			const p1 = { x: ls.x1, y: ls.y1 };
			const p2 = { x: ls.x2, y: ls.y2 };
			return (
				Math.hypot(p1.x - arcStart.x, p1.y - arcStart.y) < leafTol ||
				Math.hypot(p1.x - arcEnd.x, p1.y - arcEnd.y) < leafTol ||
				Math.hypot(p2.x - arcStart.x, p2.y - arcStart.y) < leafTol ||
				Math.hypot(p2.x - arcEnd.x, p2.y - arcEnd.y) < leafTol
			);
		});
		const candidate: TraceElement = {
			id: `floor-ir-api-door-${doors.length}`,
			kind: 'door',
			label: hasLeaf ? `平开门 ${doors.length + 1}` : `弧门 ${doors.length + 1}`,
			geometryType: 'rect',
			x: clamp(x),
			y: clamp(y),
			w: clamp(Math.max(0.006, w), 0.001, 1),
			h: clamp(Math.max(0.006, h), 0.001, 1),
			widthMm: Math.round(size * mmPerNormalized),
			confidence: hasLeaf ? 0.82 : 0.65,
			status: 'candidate',
		};
		const wall = bindOpeningToNearestWall(candidate, walls);
		if (!wall) return;
		const horizontalWall = wall.w >= wall.h;
		const cx = candidate.x + candidate.w / 2;
		const cy = candidate.y + candidate.h / 2;
		const widthNorm = clamp(size, 0.012, 0.09);
		const normalized: TraceElement = horizontalWall
			? { ...candidate, x: clamp(cx - widthNorm / 2), y: clamp(wall.y), w: widthNorm, h: Math.max(0.006, wall.h * 1.8) }
			: { ...candidate, x: clamp(wall.x), y: clamp(cy - widthNorm / 2), w: Math.max(0.006, wall.w * 1.8), h: widthNorm };
		if (!doors.some((existing) => rectIntersects(existing, normalized))) doors.push(normalized);
	});

	// ── E2: 双平开门配对 ──
	// 扫描弧门候选，寻找对称弧对合并为双开门
	const arcDoorIndices = doors.map((d, i) => (d.label?.startsWith('平开门') || d.label?.startsWith('弧门')) ? i : -1).filter((i) => i >= 0);
	const pairedDoorIds = new Set<string>();
	const doubleDoors: TraceElement[] = [];
	for (let ai = 0; ai < arcDoorIndices.length; ai++) {
		const d1 = doors[arcDoorIndices[ai]];
		if (pairedDoorIds.has(d1.id)) continue;
		for (let aj = ai + 1; aj < arcDoorIndices.length; aj++) {
			const d2 = doors[arcDoorIndices[aj]];
			if (pairedDoorIds.has(d2.id)) continue;
			const isH1 = d1.w >= d1.h, isH2 = d2.w >= d2.h;
			if (isH1 !== isH2) continue;
			const sizeRatio = Math.min(isH1 ? d1.w : d1.h, isH1 ? d2.w : d2.h) / Math.max(isH1 ? d1.w : d1.h, isH1 ? d2.w : d2.h);
			if (sizeRatio < 0.7) continue;
			const c1 = isH1 ? d1.x + d1.w / 2 : d1.y + d1.h / 2;
			const c2 = isH1 ? d2.x + d2.w / 2 : d2.y + d2.h / 2;
			const span = isH1 ? d1.w + d2.w : d1.h + d2.h;
			if (Math.abs(c1 - c2) > span * 0.85) continue;
			pairedDoorIds.add(d1.id);
			pairedDoorIds.add(d2.id);
			const mx = Math.min(d1.x, d2.x), my = Math.min(d1.y, d2.y);
			const mxe = Math.max(d1.x + d1.w, d2.x + d2.w), mye = Math.max(d1.y + d1.h, d2.y + d2.h);
			doubleDoors.push({
				id: `floor-ir-api-door-${doors.length + doubleDoors.length}`,
				kind: 'door',
				label: `双开门 ${doubleDoors.length + 1}`,
				geometryType: 'rect',
				x: clamp(mx), y: clamp(my),
				w: clamp(mxe - mx, 0.001, 1), h: clamp(mye - my, 0.001, 1),
				widthMm: Math.round(Math.max(mxe - mx, mye - my) * mmPerNormalized),
				confidence: Math.min(d1.confidence, d2.confidence) * 0.92,
				status: 'candidate',
			});
			break;
		}
	}
	const remainingDoors = doors.filter((d) => !pairedDoorIds.has(d.id));
	doors.length = 0;
	doors.push(...remainingDoors, ...doubleDoors);

	// 门洞检测：在墙中线上寻找同轨道连续墙端点之间的"缺口"（无弧、仅为开口）
	// E3: 同时检测推拉门信号（gap 附近的虚线段 = 推拉轨道/门板收纳区）
	const dashedSegs = segments.filter((s) => s.dashPattern === 'dashed' && s.pathKind !== 'curve' && segmentLength(s) >= 0.01);
	const doorOpeningSize = { min: 0.018, max: 0.09 };
	walls.forEach((wall) => {
		const horizontal = wall.w >= wall.h;
		const track = horizontal ? wall.y + wall.h / 2 : wall.x + wall.w / 2;
		const wallStart = horizontal ? wall.x : wall.y;
		const wallEnd = horizontal ? wall.x + wall.w : wall.y + wall.h;
		walls.forEach((other) => {
			if (other === wall) return;
			const isHor = other.w >= other.h;
			if (isHor !== horizontal) return;
			const otherTrack = horizontal ? other.y + other.h / 2 : other.x + other.w / 2;
			if (Math.abs(otherTrack - track) > 0.016) return;
			const otherStart = horizontal ? other.x : other.y;
			const otherEnd = horizontal ? other.x + other.w : other.y + other.h;
			const gap1 = otherStart - wallEnd;
			const gap2 = wallStart - otherEnd;
			const gap = Math.max(gap1, gap2);
			if (gap < doorOpeningSize.min || gap > doorOpeningSize.max) return;
			const gapStart = gap1 > 0 ? wallEnd : otherEnd;
			const gapCx = gapStart + gap / 2;
			const gapCy = track;
			const alreadyCovered = doors.some((d) => {
				const dCenter = horizontal ? d.x + d.w / 2 : d.y + d.h / 2;
				return Math.abs(dCenter - gapCx) < gap * 0.6;
			});
			if (alreadyCovered) return;
			// E3: 推拉门检测 — gap 附近是否有沿墙方向的虚线段
			const slidingTrackTol = 0.025;
			const hasSlidingTrack = dashedSegs.some((ds) => {
				const dsH = Math.abs(ds.x2 - ds.x1) >= Math.abs(ds.y2 - ds.y1);
				if (dsH !== horizontal) return false;
				const dsTrack = horizontal ? (ds.y1 + ds.y2) / 2 : (ds.x1 + ds.x2) / 2;
				if (Math.abs(dsTrack - track) > slidingTrackTol) return false;
				const dsStart = horizontal ? Math.min(ds.x1, ds.x2) : Math.min(ds.y1, ds.y2);
				const dsEnd = horizontal ? Math.max(ds.x1, ds.x2) : Math.max(ds.y1, ds.y2);
				// 虚线段应与 gap 区域有重叠或紧邻
				return dsEnd >= gapStart - gap * 0.3 && dsStart <= gapStart + gap + gap * 0.3;
			});
			const isSliding = hasSlidingTrack;
			const opening: TraceElement = horizontal
				? {
					id: `floor-ir-api-door-${doors.length}`,
					kind: 'door',
					label: isSliding ? `推拉门 ${doors.length + 1}` : `门洞 ${doors.length + 1}`,
					geometryType: 'rect',
					x: clamp(gapStart),
					y: clamp(wall.y),
					w: clamp(gap, 0.001, 1),
					h: Math.max(0.006, wall.h * 1.8),
					widthMm: Math.round(gap * mmPerNormalized),
					confidence: isSliding ? 0.68 : 0.60,
					status: 'candidate',
				}
				: {
					id: `floor-ir-api-door-${doors.length}`,
					kind: 'door',
					label: isSliding ? `推拉门 ${doors.length + 1}` : `门洞 ${doors.length + 1}`,
					geometryType: 'rect',
					x: clamp(wall.x),
					y: clamp(gapStart),
					w: Math.max(0.006, wall.w * 1.8),
					h: clamp(gap, 0.001, 1),
					widthMm: Math.round(gap * mmPerNormalized),
					confidence: isSliding ? 0.68 : 0.60,
					status: 'candidate',
				};
			if (!doors.some((existing) => rectIntersects(existing, opening))) doors.push(opening);
		});
	});

	return doors.slice(0, 60);
};

const buildWindowCandidates = (segments: TraceSegment[], walls: TraceElement[], mmPerNormalized: number, curtainWallZones: TraceElement[] = []): TraceElement[] => {
	const lineSegments = segments
		// 排除弧段（门弧）和矩形路径段（柱填充/轮廓），只保留纯直线
		.filter((segment) => segment.pathKind !== 'curve' && segment.pathKind !== 'rect' && segment.pathKind !== 'filledRect')
		// dashPattern 过滤：仅保留实线（玻璃线为实线，虚线是隐藏线/推拉门轨迹）
		.filter((segment) => !segment.dashPattern || segment.dashPattern === 'solid')
		.map((segment) => orthogonalizeSegment(segment))
		.filter((segment) => {
			const length = segmentLength(segment);
			// 窗洞玻璃线应屏蔽过长线段（尺寸线），同时排除过短纷头
			return length >= 0.012 && length <= 0.14;
		});
	const windows: TraceElement[] = [];
	walls.forEach((wall) => {
		const horizontalWall = wall.w >= wall.h;
		const wallTrack = horizontalWall ? wall.y + wall.h / 2 : wall.x + wall.w / 2;
		const wallStart = horizontalWall ? wall.x : wall.y;
		const wallEnd = horizontalWall ? wall.x + wall.w : wall.y + wall.h;
		const matching = lineSegments.filter((segment) => {
			if (isHorizontal(segment) !== horizontalWall) return false;
			const track = horizontalWall ? segment.y1 : segment.x1;
			const distance = Math.abs(track - wallTrack);
			// 窗洞玻璃线必须在墙体内部，最大偷移 9mm（归一化）≈ 189mm，远小于尺寸线至墙的距离
			if (distance > 0.009) return false;
			const start = horizontalWall ? Math.min(segment.x1, segment.x2) : Math.min(segment.y1, segment.y2);
			const end = horizontalWall ? Math.max(segment.x1, segment.x2) : Math.max(segment.y1, segment.y2);
			return end >= wallStart && start <= wallEnd;
		});
		const groups: TraceSegment[][] = [];
		matching.sort((a, b) => {
			const av = horizontalWall ? Math.min(a.x1, a.x2) : Math.min(a.y1, a.y2);
			const bv = horizontalWall ? Math.min(b.x1, b.x2) : Math.min(b.y1, b.y2);
			return av - bv;
		}).forEach((segment) => {
			const start = horizontalWall ? Math.min(segment.x1, segment.x2) : Math.min(segment.y1, segment.y2);
			const last = groups[groups.length - 1];
			const lastEnd = last
				? Math.max(...last.map((item) => horizontalWall ? Math.max(item.x1, item.x2) : Math.max(item.y1, item.y2)))
				: undefined;
			if (!last || lastEnd === undefined || start - lastEnd > 0.010) groups.push([segment]);
			else last.push(segment);
		});
		groups.forEach((group) => {
			if (group.length < 2) return;
			const start = Math.min(...group.map((segment) => horizontalWall ? Math.min(segment.x1, segment.x2) : Math.min(segment.y1, segment.y2)));
			const end = Math.max(...group.map((segment) => horizontalWall ? Math.max(segment.x1, segment.x2) : Math.max(segment.y1, segment.y2)));
			const size = end - start;
			// 窗宽限制：600mm – 4000mm（含带形窗）建筑窗常规尺度
			if (size < 0.014 || size > 0.19) return;
			// 幕墙排斥：候选中心落入幕墙 zone 则跳过
			const groupCenterX = horizontalWall ? (start + end) / 2 : wall.x + wall.w / 2;
			const groupCenterY = horizontalWall ? wall.y + wall.h / 2 : (start + end) / 2;
			const inCurtainWallZone = curtainWallZones.some((cw) =>
				groupCenterX >= cw.x && groupCenterX <= cw.x + cw.w && groupCenterY >= cw.y && groupCenterY <= cw.y + cw.h);
			if (inCurtainWallZone) return;
			const candidate: TraceElement = horizontalWall
				? {
					id: `floor-ir-api-window-${windows.length}`,
					kind: 'window',
					label: `窗洞 ${windows.length + 1}`,
					geometryType: 'rect',
					x: clamp(start),
					y: clamp(wall.y),
					w: clamp(size, 0.001, 1),
					h: Math.max(0.006, wall.h * 1.4),
					widthMm: Math.round(size * mmPerNormalized),
					confidence: 0.58,
					status: 'candidate',
				}
				: {
					id: `floor-ir-api-window-${windows.length}`,
					kind: 'window',
					label: `窗洞 ${windows.length + 1}`,
					geometryType: 'rect',
					x: clamp(wall.x),
					y: clamp(start),
					w: Math.max(0.006, wall.w * 1.4),
					h: clamp(size, 0.001, 1),
					widthMm: Math.round(size * mmPerNormalized),
					confidence: 0.58,
					status: 'candidate',
				};
			if (!windows.some((existing) => rectIntersects(existing, candidate))) windows.push(candidate);
		});
	});
	return windows.slice(0, 60);
};

// ═══════════════════════════════════════════════════════════════════════
// ─── Curtain Wall Detection：独立幕墙段识别（建筑外围护玻璃幕墙） ────
// ═══════════════════════════════════════════════════════════════════════

const detectCurtainWallSegments = (
	segments: TraceSegment[],
	walls: TraceElement[],
	mmPerNormalized: number
): TraceElement[] => {
	const minSpanNorm = 3000 / mmPerNormalized; // 幕墙最小跨度 3000mm
	const mullionMinNorm = 600 / mmPerNormalized;
	const mullionMaxNorm = 1800 / mmPerNormalized;

	// 仅保留实线直线段，排除弧段/矩形/虚线
	const lineSegments = segments
		.filter((s) => s.pathKind !== 'curve' && s.pathKind !== 'rect' && s.pathKind !== 'filledRect')
		.filter((s) => !s.dashPattern || s.dashPattern === 'solid')
		.map((s) => orthogonalizeSegment(s))
		.filter((s) => {
			const len = segmentLength(s);
			return len >= 0.012 && len <= 0.5;
		});

	const hLines = lineSegments.filter((s) => isHorizontal(s));
	const vLines = lineSegments.filter((s) => !isHorizontal(s));

	const findLongLineChains = (lines: TraceSegment[], isHoriz: boolean) => {
		// 按轨道分组
		const trackBuckets: { track: number; segs: TraceSegment[] }[] = [];
		lines.forEach((s) => {
			const track = isHoriz ? s.y1 : s.x1;
			const bucket = trackBuckets.find((b) => Math.abs(b.track - track) <= 0.003);
			if (bucket) bucket.segs.push(s);
			else trackBuckets.push({ track, segs: [s] });
		});

		const results: { segs: TraceSegment[]; isHoriz: boolean; track: number; start: number; end: number; span: number; mullionCount: number; mullionRegularity: number }[] = [];

		trackBuckets.forEach(({ track, segs }) => {
			segs.sort((a, b) => {
				const av = isHoriz ? Math.min(a.x1, a.x2) : Math.min(a.y1, a.y2);
				const bv = isHoriz ? Math.min(b.x1, b.x2) : Math.min(b.y1, b.y2);
				return av - bv;
			});
			// 链式聚合：间断 > 0.015 拆分
			const chains: TraceSegment[][] = [];
			segs.forEach((s) => {
				const sStart = isHoriz ? Math.min(s.x1, s.x2) : Math.min(s.y1, s.y2);
				const last = chains[chains.length - 1];
				const lastEnd = last ? Math.max(...last.map((item) => isHoriz ? Math.max(item.x1, item.x2) : Math.max(item.y1, item.y2))) : undefined;
				if (!last || lastEnd === undefined || sStart - lastEnd > 0.015) chains.push([s]);
				else last.push(s);
			});

			chains.forEach((chain) => {
				const start = Math.min(...chain.map((s) => isHoriz ? Math.min(s.x1, s.x2) : Math.min(s.y1, s.y2)));
				const end = Math.max(...chain.map((s) => isHoriz ? Math.max(s.x1, s.x2) : Math.max(s.y1, s.y2)));
				const span = end - start;
				if (span < minSpanNorm) return;

				// 宿主墙重叠检查：幕墙区域不应与厚墙大比例重叠
				const wallOverlap = walls.some((wall) => {
					const wHoriz = wall.w >= wall.h;
					if (wHoriz !== isHoriz) return false;
					const wallTrack = isHoriz ? wall.y + wall.h / 2 : wall.x + wall.w / 2;
					if (Math.abs(wallTrack - track) > 0.015) return false;
					const wStart = isHoriz ? wall.x : wall.y;
					const wEnd = isHoriz ? wall.x + wall.w : wall.y + wall.h;
					const oStart = Math.max(start, wStart);
					const oEnd = Math.min(end, wEnd);
					return oEnd > oStart && (oEnd - oStart) / span > 0.5;
				});
				if (wallOverlap) return;

				// 竖挺/横挺计数：垂直方向短线段落入幕墙区域
				const perpLines = (isHoriz ? vLines : hLines).filter((s) => {
					const sCenter = isHoriz ? (s.x1 + s.x2) / 2 : (s.y1 + s.y2) / 2;
					const sPerp = isHoriz ? (s.y1 + s.y2) / 2 : (s.x1 + s.x2) / 2;
					return sCenter >= start && sCenter <= end && Math.abs(sPerp - track) <= 0.012;
				});

				let mullionRegularity = 0;
				if (perpLines.length >= 2) {
					const positions = perpLines.map((s) => isHoriz ? (s.x1 + s.x2) / 2 : (s.y1 + s.y2) / 2).sort((a, b) => a - b);
					const gaps = positions.slice(1).map((p, i) => p - positions[i]);
					const validGaps = gaps.filter((g) => g >= mullionMinNorm && g <= mullionMaxNorm);
					mullionRegularity = gaps.length > 0 ? validGaps.length / gaps.length : 0;
				}

				results.push({ segs: chain, isHoriz, track, start, end, span, mullionCount: perpLines.length, mullionRegularity });
			});
		});
		return results;
	};

	const allChains = [...findLongLineChains(hLines, true), ...findLongLineChains(vLines, false)];

	// 配对平行轨道（幕墙至少需双平行线表示玻璃面）
	const curtainWalls: TraceElement[] = [];
	const used = new Set<number>();

	allChains.forEach((c, i) => {
		if (used.has(i)) return;
		const partnerIdx = allChains.findIndex((other, j) => {
			if (j <= i || used.has(j) || c.isHoriz !== other.isHoriz) return false;
			const trackDist = Math.abs(c.track - other.track);
			if (trackDist < 0.002 || trackDist > 0.015) return false;
			const oStart = Math.max(c.start, other.start);
			const oEnd = Math.min(c.end, other.end);
			return oEnd - oStart > Math.min(c.span, other.span) * 0.5;
		});

		const hasPartner = partnerIdx !== -1;
		if (hasPartner) used.add(partnerIdx);
		used.add(i);
		// 无配对且无竖挺 → 不足以形成幕墙证据
		if (!hasPartner && c.mullionCount < 2) return;

		const partner = hasPartner ? allChains[partnerIdx] : undefined;
		const spanStart = partner ? Math.min(c.start, partner.start) : c.start;
		const spanEnd = partner ? Math.max(c.end, partner.end) : c.end;
		const trackMin = partner ? Math.min(c.track, partner.track) : c.track - 0.003;
		const trackMax = partner ? Math.max(c.track, partner.track) : c.track + 0.003;
		const spanNorm = spanEnd - spanStart;
		const spanMm = spanNorm * mmPerNormalized;
		const confidence = Math.min(0.88, 0.40
			+ (hasPartner ? 0.15 : 0)
			+ Math.min(0.15, (c.mullionCount + (partner?.mullionCount ?? 0)) * 0.03)
			+ Math.min(0.10, c.mullionRegularity * 0.10)
			+ (spanMm > 6000 ? 0.08 : 0));

		const elem: TraceElement = c.isHoriz
			? { id: `floor-ir-api-curtain-wall-${curtainWalls.length}`, kind: 'curtain_wall', label: `幕墙 ${curtainWalls.length + 1}`, geometryType: 'rect', x: clamp(spanStart), y: clamp(trackMin), w: clamp(spanNorm, 0.001, 1), h: Math.max(0.004, trackMax - trackMin), widthMm: Math.round(spanMm), confidence, status: 'candidate' }
			: { id: `floor-ir-api-curtain-wall-${curtainWalls.length}`, kind: 'curtain_wall', label: `幕墙 ${curtainWalls.length + 1}`, geometryType: 'rect', x: clamp(trackMin), y: clamp(spanStart), w: Math.max(0.004, trackMax - trackMin), h: clamp(spanNorm, 0.001, 1), widthMm: Math.round(spanMm), confidence, status: 'candidate' };

		if (!curtainWalls.some((existing) => rectIntersects(existing, elem))) curtainWalls.push(elem);
	});

	return curtainWalls.slice(0, 20);
};

const pointToMm = (point: { x: number; y: number }, mmPerNormalized: number): [number, number] => [
	Math.round(point.x * mmPerNormalized),
	Math.round(point.y * mmPerNormalized),
];

const elementRectToMm = (element: TraceElement, mmPerNormalized: number): [number, number, number, number] => [
	Math.round(element.x * mmPerNormalized),
	Math.round(element.y * mmPerNormalized),
	Math.round((element.x + element.w) * mmPerNormalized),
	Math.round((element.y + element.h) * mmPerNormalized),
];

const buildIssues = (elements: TraceElement[], scaleSamples: number): TraceIssue[] => {
	const wallCount = elements.filter((element) => element.kind === 'wall_trace').length;
	const roomCount = elements.filter((element) => element.kind === 'function_zone').length;
	const openingCount = elements.filter((element) => element.kind === 'door' || element.kind === 'window').length;
	const issues: TraceIssue[] = [];
	if (scaleSamples <= 0) {
		issues.push({
			id: 'issue-scale-unconfirmed',
			type: 'scale_unconfirmed',
			severity: 'warning',
			targetIds: [],
			message: '未从识别区内读取到可靠尺寸标注，当前比例尺为估算值。',
			suggestedAction: 'calibrate_scale',
		});
	}
	if (wallCount === 0) {
		issues.push({
			id: 'issue-no-wall-candidates',
			type: 'no_wall_candidates',
			severity: 'error',
			targetIds: [],
			message: '未提取到稳定墙体候选，无法生成可用 FloorPlanIR。',
			suggestedAction: 'reselect_region',
		});
	} else if (wallCount < 8) {
		issues.push({
			id: 'issue-low-wall-confidence',
			type: 'low_wall_confidence',
			severity: 'warning',
			targetIds: elements.filter((element) => element.kind === 'wall_trace').map((element) => element.id),
			message: '墙体候选数量偏少，可能只识别到图纸局部或线段被过滤。',
			suggestedAction: 'relax_wall_filter_or_reselect_region',
		});
	}
	if (roomCount === 0 && wallCount > 0) {
		issues.push({
			id: 'issue-room-not-closed',
			type: 'room_not_closed',
			severity: 'warning',
			targetIds: elements.filter((element) => element.kind === 'wall_trace').slice(0, 12).map((element) => element.id),
			message: '已识别墙线，但尚未形成闭合空间。',
			suggestedAction: 'snap_wall_endpoints',
		});
	}
	if (openingCount === 0) {
		issues.push({
			id: 'issue-openings-pending',
			type: 'opening_unbound',
			severity: 'info',
			targetIds: [],
			message: '门窗洞口未形成稳定候选，建议切换到门窗校正模式逐个确认。',
			suggestedAction: 'detect_openings',
		});
	}
	return issues;
};

const buildQualityScore = (elements: TraceElement[], scaleSamples: number, issues: TraceIssue[]) => {
	const wallCount = elements.filter((element) => element.kind === 'wall_trace').length;
	const roomCount = elements.filter((element) => element.kind === 'function_zone').length;
	const openingCount = elements.filter((element) => element.kind === 'door' || element.kind === 'window').length;
	const scale = scaleSamples > 0 ? 20 : 8;
	const wallConnectivity = Math.min(25, Math.round(wallCount * 0.9));
	const roomClosure = roomCount > 0 ? Math.min(25, 8 + roomCount * 4) : 0;
	const openingBinding = openingCount > 0 ? Math.min(15, openingCount * 2) : 0;
	const ocrMatch = Math.min(10, scaleSamples);
	const issuePenalty = Math.min(12, issues.filter((issue) => issue.severity !== 'info').length * 4);
	const score = Math.max(0, Math.min(100, scale + wallConnectivity + roomClosure + openingBinding + ocrMatch - issuePenalty));
	return {
		score,
		breakdown: {
			scale,
			wallConnectivity,
			roomClosure,
			openingBinding,
			ocrMatch,
			issuePenalty: -issuePenalty,
		},
	};
};

const buildFloorPlanIR = (
	fileName: string,
	source: 'dxf' | 'pdf',
	region: TraceRegion,
	elements: TraceElement[],
	dimensions: DimensionMark[],
	mmPerNormalized: number,
	issues: TraceIssue[],
	coreZones: FloorPlanIRCoreZone[] = []
): FloorPlanIRDraft => {
	const walls = elements.filter((element) => element.kind === 'wall_trace').map((element): FloorPlanIRWall => {
		const horizontal = element.w >= element.h;
		const start = horizontal
			? { x: element.x, y: element.y + element.h / 2 }
			: { x: element.x + element.w / 2, y: element.y };
		const end = horizontal
			? { x: element.x + element.w, y: element.y + element.h / 2 }
			: { x: element.x + element.w / 2, y: element.y + element.h };
		const thickness = Math.max(80, Math.round(Math.min(element.w, element.h) * mmPerNormalized));
		const wv = element.wallVerification;
		return {
			id: element.id,
			levelId: 'L1',
			p1: pointToMm(start, mmPerNormalized),
			p2: pointToMm(end, mmPerNormalized),
			thickness,
			height: 2800,
			structuralRole: wv?.structuralRole ?? 'wall_candidate_unverified',
			removability: wv?.removability ?? 'unknown',
			interiorActionHints: wv?.interiorActionHints,
			confidence: wv?.confidence ?? element.confidence,
			evidence: wv?.evidence,
			source: {
				bbox: elementRectToMm(element, mmPerNormalized),
				method: 'vector_line_trace',
			},
			reviewFlags: wv?.reviewFlags,
		};
	});
	const rooms = elements.filter((element) => element.kind === 'function_zone').map((element): FloorPlanIRRoom => {
		const zv = element.zoneVerification;
		return {
			id: element.id,
			name: element.label,
			usage: zv && zv.zoneType !== 'zone_candidate_unverified' ? zv.zoneType : 'unknown',
			polygon: (element.points ?? []).map((point) => pointToMm(point, mmPerNormalized)),
			area: element.areaSqm ?? 0,
			boundaryWallIds: [],
			confidence: zv?.confidence ?? element.confidence,
			zoneType: zv?.zoneType,
			stairOrigin: zv?.stairOrigin,
			removability: zv?.removability,
			textLabel: zv?.textLabel,
			zoneEvidence: zv?.evidence,
		};
	});
	const columns = elements.filter((element) => element.kind === 'column').map((element): FloorPlanIRColumn => {
		const v = element.columnVerification;
		return {
			id: element.id,
			polygon: (element.points ?? [
				{ x: element.x, y: element.y },
				{ x: element.x + element.w, y: element.y },
				{ x: element.x + element.w, y: element.y + element.h },
				{ x: element.x, y: element.y + element.h },
			]).map((point) => pointToMm(point, mmPerNormalized)),
			size: [Math.round(element.w * mmPerNormalized), Math.round(element.h * mmPerNormalized)],
			type: v?.columnType ?? 'column_candidate_unverified',
			shape: v?.shape ?? (Math.abs(element.w - element.h) < 0.003 ? 'square' : 'rect'),
			removability: v?.removability ?? 'unknown',
			structuralPriority: v?.structuralPriority ?? 'unknown',
			confidence: element.confidence,
			evidence: v?.evidence,
			sourceMethod: v?.sourceMethod,
			reviewFlags: v?.reviewFlags,
		};
	});
	const wallElements = elements.filter((element) => element.kind === 'wall_trace');
	const openings = elements
		.filter((element): element is TraceElement & { kind: 'door' | 'window' } => element.kind === 'door' || element.kind === 'window')
		.map((element): FloorPlanIROpening => {
		const wall = bindOpeningToNearestWall(element, wallElements);
		const ov = element.openingVerification;
		const wv = element.windowVerification;
		const hostWall = wall ? wallElements.find((w) => w.id === wall.id) : undefined;
		return {
			id: element.id,
			kind: element.kind,
			openingType: ov?.openingType,
			windowType: wv?.windowType,
			swingDirection: ov?.swingDirection,
			wallId: wv?.hostWallId ?? ov?.hostWallId ?? wall?.id,
			hostWallRole: wv?.hostWallRole ?? ov?.hostWallRole ?? hostWall?.wallVerification?.structuralRole,
			removability: wv?.removability ?? ov?.removability,
			position: pointToMm({ x: element.x + element.w / 2, y: element.y + element.h / 2 }, mmPerNormalized),
			width: Math.max(300, Math.round(Math.max(element.w, element.h) * mmPerNormalized)),
			height: element.kind === 'door' ? 2100 : 1500,
			confidence: wv?.confidence ?? ov?.confidence ?? element.confidence,
			evidence: ov?.evidence,
			windowEvidence: wv?.evidence,
			source: {
				bbox: elementRectToMm(element, mmPerNormalized),
				method: [element.kind === 'door' ? 'door_arc_wall_binding' : 'parallel_window_line_binding'],
			},
			reviewFlags: [...(ov?.reviewFlags ?? []), ...(wv?.reviewFlags ?? [])],
		};
	});
	return {
		version: 'floorplan_ir_v0.1',
		irId: `ir_${Date.now()}`,
		source: {
			fileName,
			sourceType: source,
			page: 1,
			recognitionBbox: [region.x, region.y, region.w, region.h],
		},
		coordinateSystem: {
			unit: 'mm',
			origin: 'top_left',
			scale: mmPerNormalized,
			scaleStatus: dimensions.length > 0 ? 'estimated' : 'uncalibrated',
			rotation: 0,
		},
		levels: [{ id: 'L1', name: '1F', elevation: 0, floorHeight: 2800 }],
		walls,
		openings,
		curtainWalls: elements.filter((e) => e.kind === 'curtain_wall').map((element): FloorPlanIRCurtainWall => {
			const cv = element.curtainWallVerification;
			return {
				id: element.id,
				curtainWallType: cv?.curtainWallType ?? 'curtain_wall_candidate_unverified',
				position: pointToMm({ x: element.x + element.w / 2, y: element.y + element.h / 2 }, mmPerNormalized),
				spanWidth: Math.round(Math.max(element.w, element.h) * mmPerNormalized),
				spanHeight: 2800,
				hasOperablePanels: cv?.hasOperablePanels ?? false,
				confidence: cv?.confidence ?? element.confidence,
				evidence: cv?.evidence ?? { envelopeContinuity: 0, mullionRepetition: 0, hostWallIndependence: 0, spanWidth: 0 },
				source: { bbox: elementRectToMm(element, mmPerNormalized), method: ['long_span_glass_line_detection'] },
				reviewFlags: cv?.reviewFlags,
			};
		}),
		rooms,
		coreZones,
		columns,
		texts: [],
		dimensions,
		issues,
		stats: {
			wallCount: walls.length,
			openingCount: openings.length,
			curtainWallCount: elements.filter((e) => e.kind === 'curtain_wall').length,
			roomCount: rooms.length,
			coreZoneCount: coreZones.length,
			columnCount: columns.length,
			issueCount: issues.length,
		},
	};
};

const parseDxfNumber = (pairs: Array<[string, string]>, startIndex: number, code: string) => {
	for (let i = startIndex; i < pairs.length; i += 1) {
		if (pairs[i][0] === '0') break;
		if (pairs[i][0] === code) return Number(pairs[i][1]);
	}
	return undefined;
};

const parseDxfString = (pairs: Array<[string, string]>, startIndex: number, code: string) => {
	for (let i = startIndex; i < pairs.length; i += 1) {
		if (pairs[i][0] === '0') break;
		if (pairs[i][0] === code) return pairs[i][1];
	}
	return undefined;
};

const parseDxfSegments = (content: string): TraceSegment[] => {
	const raw = content.split(/\r?\n/).map((line) => line.trim());
	const pairs: Array<[string, string]> = [];
	for (let i = 0; i < raw.length - 1; i += 2) pairs.push([raw[i], raw[i + 1]]);
	const segments: TraceSegment[] = [];
	for (let i = 0; i < pairs.length; i += 1) {
		const [code, value] = pairs[i];
		if (code !== '0') continue;
		if (value === 'LINE') {
			const layer = parseDxfString(pairs, i + 1, '8');
			const x1 = parseDxfNumber(pairs, i + 1, '10');
			const y1 = parseDxfNumber(pairs, i + 1, '20');
			const x2 = parseDxfNumber(pairs, i + 1, '11');
			const y2 = parseDxfNumber(pairs, i + 1, '21');
			if ([x1, y1, x2, y2].every((n) => typeof n === 'number' && Number.isFinite(n))) {
				segments.push({ x1: x1!, y1: y1!, x2: x2!, y2: y2!, score: Math.hypot(x2! - x1!, y2! - y1!), source: 'dxf', layer, pathKind: 'line' });
			}
		}
		if (value === 'LWPOLYLINE' || value === 'POLYLINE') {
			const layer = parseDxfString(pairs, i + 1, '8');
			const points: Array<{ x: number; y: number }> = [];
			for (let j = i + 1; j < pairs.length && pairs[j][0] !== '0'; j += 1) {
				if (pairs[j][0] === '10') {
					const x = Number(pairs[j][1]);
					const yPair = pairs.slice(j + 1, Math.min(j + 4, pairs.length)).find((pair) => pair[0] === '20');
					const y = yPair ? Number(yPair[1]) : NaN;
					if (Number.isFinite(x) && Number.isFinite(y)) points.push({ x, y });
				}
			}
			for (let j = 0; j < points.length - 1; j += 1) {
				const a = points[j];
				const b = points[j + 1];
				segments.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y, score: Math.hypot(b.x - a.x, b.y - a.y), source: 'dxf', layer, pathKind: 'line' });
			}
		}
	}
	if (segments.length === 0) return [];
	const xs = segments.flatMap((segment) => [segment.x1, segment.x2]);
	const ys = segments.flatMap((segment) => [segment.y1, segment.y2]);
	const minX = Math.min(...xs);
	const maxX = Math.max(...xs);
	const minY = Math.min(...ys);
	const maxY = Math.max(...ys);
	const width = Math.max(1, maxX - minX);
	const height = Math.max(1, maxY - minY);
	return segments.map((segment) => ({
		...segment,
		x1: (segment.x1 - minX) / width,
		x2: (segment.x2 - minX) / width,
		y1: 1 - (segment.y1 - minY) / height,
		y2: 1 - (segment.y2 - minY) / height,
		score: segment.score / Math.max(width, height),
	}));
};

// ─── P0-C: 闭合圆检测 ──────────────────────────────────────────────
// 从 curve 段序列中检测近似闭合圆弧（轴号圆、索引圆、指北针圆）
const detectClosedCirclesFromSegments = (segments: TraceSegment[], mmPerNormalized: number): DetectedCircle[] => {
	const curveIndices: number[] = [];
	segments.forEach((s, i) => { if (s.pathKind === 'curve') curveIndices.push(i); });
	if (curveIndices.length < 3) return [];

	const circles: DetectedCircle[] = [];
	// 滑动窗口：3–8 连续 curve 段
	for (let wi = 0; wi < curveIndices.length; wi++) {
		for (let windowSize = 3; windowSize <= Math.min(8, curveIndices.length - wi); windowSize++) {
			const windowIndices = curveIndices.slice(wi, wi + windowSize);
			// 必须是连续索引（相邻 curve 段来自同一路径）
			let continuous = true;
			for (let k = 1; k < windowIndices.length; k++) {
				if (windowIndices[k] - windowIndices[k - 1] > 2) { continuous = false; break; }
			}
			if (!continuous) break;

			const firstSeg = segments[windowIndices[0]];
			const lastSeg = segments[windowIndices[windowIndices.length - 1]];
			const closureGap = Math.hypot(lastSeg.x2 - firstSeg.x1, lastSeg.y2 - firstSeg.y1);
			// 所有端点
			const points: Array<[number, number]> = [];
			for (const idx of windowIndices) {
				points.push([segments[idx].x1, segments[idx].y1]);
				points.push([segments[idx].x2, segments[idx].y2]);
			}
			const cx = points.reduce((s, p) => s + p[0], 0) / points.length;
			const cy = points.reduce((s, p) => s + p[1], 0) / points.length;
			const radii = points.map((p) => Math.hypot(p[0] - cx, p[1] - cy));
			const avgR = radii.reduce((s, r) => s + r, 0) / radii.length;
			if (avgR < 0.002 || avgR > 0.06) continue; // 太小或太大
			const stdR = Math.sqrt(radii.reduce((s, r) => s + (r - avgR) ** 2, 0) / radii.length);
			// 闭合性：起终点距 < 半径*0.5；圆度：std < 0.20*avg
			if (closureGap > avgR * 0.5) continue;
			if (stdR > avgR * 0.20) continue;

			const radiusMm = avgR * mmPerNormalized;
			let probableRole: DetectedCircle['probableRole'] = 'unknown_circle';
			if (radiusMm >= 3 && radiusMm <= 10) probableRole = 'axis_label_circle';
			else if (radiusMm > 10 && radiusMm <= 18) probableRole = 'index_circle';
			else if (radiusMm > 18 && radiusMm <= 40) probableRole = 'north_arrow_circle';

			// 去重：如果已有圆中心很近，跳过
			if (circles.some((c) => Math.hypot(c.center[0] - cx, c.center[1] - cy) < avgR * 0.5)) continue;

			circles.push({
				center: [cx, cy],
				radiusNorm: avgR,
				radiusMm,
				closureGap,
				segmentIndices: windowIndices,
				probableRole,
			});
		}
	}
	return circles.slice(0, 120);
};

const parsePdfSegments = async (buffer: Buffer): Promise<TraceParseResult> => {
	const pdfjsLib = await import('pdfjs-dist/legacy/build/pdf');
	pdfjsLib.GlobalWorkerOptions.workerSrc = path.join(process.cwd(), 'node_modules', 'pdfjs-dist', 'legacy', 'build', 'pdf.worker.js');
	const loadingTask = pdfjsLib.getDocument({ data: new Uint8Array(buffer), disableWorker: true } as any);
	const pdf = await loadingTask.promise;
	const page = await pdf.getPage(1);
	const viewport = page.getViewport({ scale: 1 });
	const operatorList = await page.getOperatorList();
	const ops = pdfjsLib.OPS;
	const segments: TraceSegment[] = [];
	let current: { x: number; y: number } | null = null;
	let currentLineWidth = 1;
	let currentDashPattern: TraceSegment['dashPattern'] = 'solid';
	let currentTransform: [number, number, number, number, number, number] = [1, 0, 0, 1, 0, 0];
	const transformStack: Array<[number, number, number, number, number, number]> = [];
	const dashStack: Array<TraceSegment['dashPattern']> = [];
	const multiplyTransform = (
		a: [number, number, number, number, number, number],
		b: [number, number, number, number, number, number]
	): [number, number, number, number, number, number] => [
		a[0] * b[0] + a[2] * b[1],
		a[1] * b[0] + a[3] * b[1],
		a[0] * b[2] + a[2] * b[3],
		a[1] * b[2] + a[3] * b[3],
		a[0] * b[4] + a[2] * b[5] + a[4],
		a[1] * b[4] + a[3] * b[5] + a[5],
	];
	const applyTransform = (matrix: [number, number, number, number, number, number], x: number, y: number) => ({
		x: matrix[0] * x + matrix[2] * y + matrix[4],
		y: matrix[1] * x + matrix[3] * y + matrix[5],
	});
	const convert = (x: number, y: number) => {
		const transformed = applyTransform(currentTransform, x, y);
		const [vx, vy] = viewport.convertToViewportPoint(transformed.x, transformed.y);
		return { x: vx / viewport.width, y: vy / viewport.height };
	};
	// 预扫描：确定每个 constructPath 后续的绘制操作（填充 or 描边）
	// 若后续是 fill/fillStroke → 路径被填充（柱多为填充黑色矩形，无描边）
	const pathFillSet = new Set<number>();
	operatorList.fnArray.forEach((fn: number, pi: number) => {
		if (fn !== ops.constructPath) return;
		// 扩大 lookahead 到 20：CAD 导出时颜色设置 (setGraphicsState/setFillColor) 可能
		// 在 constructPath 和 fill 之间插入多个 op，lookahead=8 会漏掉部分填充路径
		for (let pj = pi + 1; pj < Math.min(pi + 20, operatorList.fnArray.length); pj++) {
			const nfn = operatorList.fnArray[pj];
			if (nfn === ops.fill || nfn === ops.eoFill || nfn === ops.fillStroke || nfn === ops.eoFillStroke) {
				pathFillSet.add(pi); break;
			}
			if (nfn === ops.stroke || nfn === ops.closeStroke || nfn === ops.constructPath) break;
		}
	});
	// [§0诊断] pathFillSet 大小 = 被 fill 操作跟随的 constructPath 数 → 判断 PDF 是否有填充路径
	if (process.env.NODE_ENV !== 'production') {
		const paintMaskCount = operatorList.fnArray.filter((f: number) => f === ops.paintSolidColorImageMask).length;
		console.log('[PDF §0] pathFillSet.size =', pathFillSet.size, '| paintSolidColorImageMask =', paintMaskCount, '| operatorList.length =', operatorList.fnArray.length);
	}
	operatorList.fnArray.forEach((fn: number, index: number) => {
		if (fn === ops.save) {
			transformStack.push([...currentTransform]);
			dashStack.push(currentDashPattern);
			return;
		}
		if (fn === ops.restore) {
			currentTransform = transformStack.pop() ?? [1, 0, 0, 1, 0, 0];
			currentDashPattern = dashStack.pop() ?? 'solid';
			return;
		}
		if (fn === ops.transform) {
			const args = operatorList.argsArray[index] as number[] | undefined;
			if (args && args.length >= 6) {
				currentTransform = multiplyTransform(currentTransform, [args[0], args[1], args[2], args[3], args[4], args[5]]);
			}
			return;
		}
		if (fn === ops.setLineWidth) {
			const args = operatorList.argsArray[index] as number[] | undefined;
			currentLineWidth = Number(args?.[0] ?? currentLineWidth);
			return;
		}
		if (fn === ops.setDash) {
			const args = operatorList.argsArray[index] as [number[], number] | undefined;
			const dashArray = args?.[0] ?? [];
			if (!dashArray.length || dashArray.every((v: number) => v === 0)) {
				currentDashPattern = 'solid';
			} else if (dashArray.length >= 4) {
				// [长, 短, 点, 短] → 点划线 (dash_dot); 典型建筑轴线
				const sorted = [...dashArray].sort((a, b) => a - b);
				currentDashPattern = sorted[0] < sorted[sorted.length - 1] * 0.35 ? 'dash_dot' : 'dashed';
			} else if (dashArray.length >= 2) {
				currentDashPattern = dashArray[0] < 1.5 && dashArray[1] < 1.5 ? 'dotted' : 'dashed';
			} else {
				currentDashPattern = dashArray[0] < 1.5 ? 'dotted' : 'dashed';
			}
			return;
		}
		if (fn === ops.paintSolidColorImageMask) {
			// pdfjs 将某些实心填充矩形优化为 paintSolidColorImageMask（op=90）
			// currentTransform 将单位矩形 [0,1]×[0,1] 映射到实际绘制区域 → 还原为 filledRect
			const corners = [[0, 0], [1, 0], [1, 1], [0, 1]].map(([cx, cy]) => convert(cx, cy));
			const xs = corners.map((c) => c.x);
			const ys = corners.map((c) => c.y);
			const left = Math.min(...xs); const right = Math.max(...xs);
			const top = Math.min(...ys); const bottom = Math.max(...ys);
			const w = right - left; const h = bottom - top;
			if (w > 0.001 && h > 0.001) {
				segments.push({ x1: left, y1: top, x2: right, y2: bottom, score: (w + h) / 2, source: 'pdf', lineWidth: currentLineWidth, pathKind: 'filledRect', dashPattern: currentDashPattern });
			}
			return;
		}
		if (fn !== ops.constructPath) return;
		const args = operatorList.argsArray[index] as [number[], number[]] | undefined;
		const commands = args?.[0] ?? [];
		const coords = args?.[1] ?? [];
		let cursor = 0;
		const isFillPath = pathFillSet.has(index);
		// fill 路径：每个 sub-path 独立收集点，在 moveTo/closePath/结束时 flush
		// 修复：原先 fillPathPoints 跨 moveTo 累积，导致多柱路径的32+点无法通过矩形检测
		let subPathPoints: { x: number; y: number }[] = [];
		let subPathHasCurve = false;
		const flushFillSubPath = () => {
			if (isFillPath && !subPathHasCurve && subPathPoints.length >= 3) {
				const xs = subPathPoints.map((p) => p.x);
				const ys = subPathPoints.map((p) => p.y);
				const left = Math.min(...xs); const right = Math.max(...xs);
				const top = Math.min(...ys); const bottom = Math.max(...ys);
				const w = right - left; const h = bottom - top;
				const isAxisAligned = w > 0.001 && h > 0.001 && subPathPoints.every((p) =>
					(Math.abs(p.x - left) < 0.003 || Math.abs(p.x - right) < 0.003) &&
					(Math.abs(p.y - top) < 0.003 || Math.abs(p.y - bottom) < 0.003)
				);
				if (isAxisAligned) {
					// 轴对齐矩形：用 filledRect 编码（向后兼容）
					segments.push({ x1: left, y1: top, x2: right, y2: bottom, score: (w + h) / 2, source: 'pdf', lineWidth: currentLineWidth, pathKind: 'filledRect', dashPattern: currentDashPattern });
				} else if (w > 0.001 && h > 0.001) {
					// 非轴对齐填充多边形（L型柱、异型嵌墙柱等）：保留为 filledPolygon
					// CarrierBaselineIR 阶段的 StructuralKernel 提取会消费此类对象
					segments.push({
						x1: left, y1: top, x2: right, y2: bottom,
						score: (w + h) / 2,
						source: 'pdf',
						lineWidth: currentLineWidth,
						pathKind: 'filledPolygon',
						polygonPoints: [...subPathPoints],
						dashPattern: currentDashPattern,
					});
				}
			}
			subPathPoints = [];
			subPathHasCurve = false;
		};
		// 连续 curveTo 积累：将多段贝塞尔曲线还原为完整门弧线段
		let arcPathStart: { x: number; y: number } | null = null;
		let arcSegCount = 0;
		const flushArc = () => {
			if (arcPathStart && arcSegCount >= 2 && current) {
				segments.push({
					x1: arcPathStart.x, y1: arcPathStart.y, x2: current.x, y2: current.y,
					score: Math.hypot(current.x - arcPathStart.x, current.y - arcPathStart.y) * 0.9,
					source: 'pdf', lineWidth: currentLineWidth, pathKind: 'curve', dashPattern: currentDashPattern,
				});
			}
			arcPathStart = null;
			arcSegCount = 0;
		};
		commands.forEach((command) => {
			if (command !== ops.curveTo) flushArc();
			if (command === ops.moveTo) {
				// 新 sub-path 开始：先 flush 上一个 sub-path
				if (isFillPath && subPathPoints.length > 0) flushFillSubPath();
				const point = convert(coords[cursor], coords[cursor + 1]);
				current = point;
				if (isFillPath) subPathPoints.push(point);
				cursor += 2;
			} else if (command === ops.lineTo) {
				const point = convert(coords[cursor], coords[cursor + 1]);
				if (isFillPath) {
					subPathPoints.push(point);
				} else if (current) {
					segments.push({ x1: current.x, y1: current.y, x2: point.x, y2: point.y, score: Math.hypot(point.x - current.x, point.y - current.y), source: 'pdf', lineWidth: currentLineWidth, pathKind: 'line', dashPattern: currentDashPattern });
				}
				current = point;
				cursor += 2;
			} else if (command === ops.curveTo) {
				if (isFillPath) subPathHasCurve = true;
				const point = convert(coords[cursor + 4], coords[cursor + 5]);
				if (current) {
					segments.push({ x1: current.x, y1: current.y, x2: point.x, y2: point.y, score: Math.hypot(point.x - current.x, point.y - current.y) * 0.75, source: 'pdf', lineWidth: currentLineWidth, pathKind: 'curve', dashPattern: currentDashPattern });
					if (!arcPathStart) arcPathStart = current;
					arcSegCount += 1;
				}
				current = point;
				cursor += 6;
			} else if (command === ops.rectangle) {
				const rx = coords[cursor];
				const ry = coords[cursor + 1];
				const rw = coords[cursor + 2];
				const rh = coords[cursor + 3];
				const ra = convert(rx, ry);
				const rb = convert(rx + rw, ry + rh);
				const left = Math.min(ra.x, rb.x);
				const right = Math.max(ra.x, rb.x);
				const top = Math.min(ra.y, rb.y);
				const bottom = Math.max(ra.y, rb.y);
				if (isFillPath) {
					// 填充矩形：用单个 filledRect 段编码整个矩形（避免 4 条边进入墙线检测）
					// 后续 buildColumnCandidatesFromRaw 会直接将满足尺寸要求的 filledRect 转为柱
					segments.push({ x1: left, y1: top, x2: right, y2: bottom, score: (right - left + bottom - top) / 2, source: 'pdf', lineWidth: currentLineWidth, pathKind: 'filledRect', dashPattern: currentDashPattern });
				} else {
					// 描边矩形：4 条描边轮廓线（用于检测描边柱/特殊符号）
					segments.push({ x1: left, y1: top, x2: right, y2: top, score: right - left, source: 'pdf', lineWidth: currentLineWidth, pathKind: 'rect', dashPattern: currentDashPattern });
					segments.push({ x1: right, y1: top, x2: right, y2: bottom, score: bottom - top, source: 'pdf', lineWidth: currentLineWidth, pathKind: 'rect', dashPattern: currentDashPattern });
					segments.push({ x1: right, y1: bottom, x2: left, y2: bottom, score: right - left, source: 'pdf', lineWidth: currentLineWidth, pathKind: 'rect', dashPattern: currentDashPattern });
					segments.push({ x1: left, y1: bottom, x2: left, y2: top, score: bottom - top, source: 'pdf', lineWidth: currentLineWidth, pathKind: 'rect', dashPattern: currentDashPattern });
				}
				cursor += 4;
			} else if (command === ops.closePath) {
				// closePath 是 sub-path 结束信号（CAD 常用 moveTo+3xlineTo+closePath+fill 画柱）
				if (isFillPath) flushFillSubPath();
			}
		});
		flushArc();
		// forEach 结束后 flush 最后一个未被 closePath 关闭的 sub-path
		flushFillSubPath();
	});
	const textContent = await page.getTextContent();
	const dimensions = (textContent.items as Array<{ str?: string; transform?: number[] }>)
		.map((item) => {
			// 捕获建筑尺寸标注：
			// - 整数 mm 格式：800–60000（覆盖酒店大跨度：柱距 8400、开间 4800、总宽 36000 等）
			// - 小数 m 格式：0.8m–60m（如 "6.0"、"8.4"，乘以 1000 转为 mm）
			// - 过滤：纯轴号（A/B/1/2）、图名编号、高程标注已在 classifiedTexts 中处理
			const rawStr = String(item.str ?? '').trim().replace(/,/g, '').replace(/\s+/g, '');
			const transform = item.transform ?? [];
			if (transform.length < 6) return null;

			let value = NaN;
			// 整数 mm：3–5 位数字（800-60000）
			const mmMatch = rawStr.match(/^([1-9]\d{2,4})([+.].*)?$/);
			if (mmMatch) {
				const candidate = Number(mmMatch[1]);
				if (candidate >= 800 && candidate <= 60000) value = candidate;
			}
			// 小数 m：形如 "6.0" "8.40" "12.000"（转为 mm，范围 0.8m-60m）
			if (isNaN(value)) {
				const mMatch = rawStr.match(/^(\d{1,2}\.\d{1,3})$/);
				if (mMatch) {
					const candidate = Math.round(Number(mMatch[1]) * 1000);
					if (candidate >= 800 && candidate <= 60000) value = candidate;
				}
			}
			if (isNaN(value) || value === 0) return null;
			const [x, y] = viewport.convertToViewportPoint(transform[4], transform[5]);
			return { value, x: x / viewport.width, y: y / viewport.height };
		})
		.filter((mark): mark is DimensionMark => mark !== null)
		.slice(0, 120);
	// ─── P0-B: 文字分类提取（多通道）───────────────────────────────────
	const ROOM_NAME_RE = /^(客厅|卧室|主卧|次卧|厨房|卫生间|阳台|生活阳台|景观阳台|观景阳台|开放阳台|半开放阳台|露台|平台|屋顶花园|空中花园|封闭阳台|餐厅|书房|玄关|走廊|储藏|衣帽间|儿童房|起居室|门厅|楼梯间|电梯厅|电梯间|电梯|电梯井|货梯|设备间|设备房|过道|入户|花园|露台|保姆间|健身房|影音室|车库|地下室|杂物间|洗衣房|公卫|主卫|工人房|佣人房|南卧|北卧|消防楼梯|防烟楼梯|疏散楼梯|楼梯|管井|管道井|水井|风井|强电井|弱电井|电气井|配电间|配电房|机房|水泵房|核心筒|前室|合用前室|弱电间|强电间)/;
	const AXIS_LABEL_RE = /^([A-Z]|[①-⑳]|[1-9]\d?)$/;
	const ELEVATION_RE = /^[±＋]?\d+\.\d{2,3}$/;
	const SCALE_RE = /^1\s*[:：]\s*\d{1,4}$/;
	const classifiedTexts: ClassifiedText[] = (textContent.items as Array<{ str?: string; transform?: number[]; width?: number; height?: number }>)
		.map((item): ClassifiedText | null => {
			const rawStr = String(item.str ?? '').trim();
			if (!rawStr || rawStr.length > 40) return null;
			const transform = item.transform ?? [];
			if (transform.length < 6) return null;
			const [tx, ty] = viewport.convertToViewportPoint(transform[4], transform[5]);
			const nx = tx / viewport.width;
			const ny = ty / viewport.height;
			const fontSize = Math.abs(transform[3]) || Math.abs(transform[0]) || 12;
			const estW = (rawStr.length * fontSize * 0.6) / viewport.width;
			const estH = fontSize / viewport.height;
			let role: TextSemanticRole = 'unknown';
			let confidence = 0.4;
			const cleaned = rawStr.replace(/[\s,，]/g, '');
			if (/^[1-9]\d{2,4}([+.].*)?$/.test(cleaned) && Number(cleaned.match(/^(\d+)/)?.[1]) >= 800 && Number(cleaned.match(/^(\d+)/)?.[1]) <= 12000) {
				role = 'dimension'; confidence = 0.85;
			} else if (ROOM_NAME_RE.test(cleaned)) {
				role = 'room_name'; confidence = 0.90;
			} else if (AXIS_LABEL_RE.test(cleaned)) {
				role = 'axis_label'; confidence = 0.75;
			} else if (ELEVATION_RE.test(cleaned)) {
				role = 'elevation'; confidence = 0.80;
			} else if (SCALE_RE.test(cleaned)) {
				role = 'scale_text'; confidence = 0.85;
			}
			return { text: rawStr, role, x: nx, y: ny, width: estW, height: estH, confidence };
		})
		.filter((t): t is ClassifiedText => t !== null)
		.slice(0, 300);
	if (segments.length === 0) return { segments, dimensions, classifiedTexts, detectedCircles: [] };
	const lengths = segments.map(segmentLength).filter((length) => Number.isFinite(length) && length > 0);
	const medianLength = lengths.length > 0 ? [...lengths].sort((a, b) => a - b)[Math.floor(lengths.length / 2)] : 0;
	const usableSegments = segments.filter((segment) => {
		const values = [segment.x1, segment.y1, segment.x2, segment.y2];
		if (!values.every((value) => Number.isFinite(value))) return false;
		const length = segmentLength(segment);
		return length > 0 && (!medianLength || length <= medianLength * 80);
	});
	const sourceForBounds = usableSegments.length >= 16 ? usableSegments : segments;
	const percentile = (values: number[], ratio: number) => {
		const sorted = values.filter(Number.isFinite).sort((a, b) => a - b);
		if (sorted.length === 0) return 0;
		return sorted[Math.min(sorted.length - 1, Math.max(0, Math.floor(sorted.length * ratio)))];
	};
	const xs = sourceForBounds.flatMap((segment) => [segment.x1, segment.x2]);
	const ys = sourceForBounds.flatMap((segment) => [segment.y1, segment.y2]);
	const rawMinX = percentile(xs, 0.01);
	const rawMaxX = percentile(xs, 0.99);
	const rawMinY = percentile(ys, 0.01);
	const rawMaxY = percentile(ys, 0.99);
	const padX = (rawMaxX - rawMinX) * 0.015;
	const padY = (rawMaxY - rawMinY) * 0.015;
	const minX = rawMinX - padX;
	const maxX = rawMaxX + padX;
	const minY = rawMinY - padY;
	const maxY = rawMaxY + padY;
	const width = maxX - minX;
	const height = maxY - minY;
	if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return { segments, dimensions };
	const contentBox = {
		x: clamp(minX),
		y: clamp(minY),
		w: clamp(width, 0.001, 1),
		h: clamp(height, 0.001, 1),
	};
	const normalizedSegments = usableSegments
		.filter((segment) => {
			const x1 = Math.min(segment.x1, segment.x2);
			const x2 = Math.max(segment.x1, segment.x2);
			const y1 = Math.min(segment.y1, segment.y2);
			const y2 = Math.max(segment.y1, segment.y2);
			return x2 >= minX && x1 <= maxX && y2 >= minY && y1 <= maxY;
		})
		.map((segment) => ({
			...segment,
			x1: (segment.x1 - minX) / width,
			x2: (segment.x2 - minX) / width,
			y1: (segment.y1 - minY) / height,
			y2: (segment.y2 - minY) / height,
			score: segmentLength(segment) / Math.max(width, height),
		}));
	const normalizedDimensions = dimensions.map((mark) => ({
		...mark,
		x: (mark.x - minX) / width,
		y: (mark.y - minY) / height,
	})).filter((mark) => mark.x >= -0.05 && mark.x <= 1.05 && mark.y >= -0.05 && mark.y <= 1.05);
	// 文字坐标也归一化到 contentBox 空间
	const normalizedTexts = classifiedTexts.map((t) => ({
		...t,
		x: (t.x - minX) / width,
		y: (t.y - minY) / height,
		width: t.width / width,
		height: t.height / height,
	})).filter((t) => t.x >= -0.1 && t.x <= 1.1 && t.y >= -0.1 && t.y <= 1.1);
	// ─── P0-C: 闭合圆检测（从 curve 段中检测近似闭合圆弧序列）───
	const detectedCircles = detectClosedCirclesFromSegments(normalizedSegments, 21000);
	// 计算 parserDiag（对 API 响应可见，不依赖 console）
	const paintMaskCnt = operatorList.fnArray.filter((f: number) => f === ops.paintSolidColorImageMask).length;
	const frAll = normalizedSegments.filter((s) => s.pathKind === 'filledRect');
	const parserDiag: TraceParseResult['parserDiag'] = {
		pathFillSetSize: pathFillSet.size,
		paintSolidColorImageMaskCount: paintMaskCnt,
		operatorListLength: operatorList.fnArray.length,
		filledRectTotal: frAll.length,
		filledRectNormSizeCount: frAll.filter((s) => { const w = Math.abs(s.x2 - s.x1); const h = Math.abs(s.y2 - s.y1); return w >= 0.005 && h >= 0.005 && w <= 0.060 && h <= 0.060; }).length,
		filledRectOversizeCount: frAll.filter((s) => Math.abs(s.x2 - s.x1) > 0.060 || Math.abs(s.y2 - s.y1) > 0.060).length,
	};
	// Y轴物理比例 / X轴物理比例：坐标系对X除以viewport.width、对Y除以viewport.height，
	// 因此同一 mmPerNormalized（从水平尺寸标注校准）不能直接用于纵向尺寸。
	// 正确 depthMm = (h × mmPerNormX) × pageAspectYX
	const pageAspectYX = (height * viewport.height) / (width * viewport.width);
	return { segments: normalizedSegments, dimensions: normalizedDimensions, contentBox, classifiedTexts: normalizedTexts, detectedCircles, parserDiag, pageAspectYX };
};

const pageRegionToContentRegion = (region: TraceRegion, contentBox?: TraceRegion): TraceRegion => {
	if (!contentBox) return region;
	const x1 = (region.x - contentBox.x) / Math.max(0.001, contentBox.w);
	const y1 = (region.y - contentBox.y) / Math.max(0.001, contentBox.h);
	const x2 = (region.x + region.w - contentBox.x) / Math.max(0.001, contentBox.w);
	const y2 = (region.y + region.h - contentBox.y) / Math.max(0.001, contentBox.h);
	return normalizeRegion({
		x: Math.min(x1, x2),
		y: Math.min(y1, y2),
		w: Math.abs(x2 - x1),
		h: Math.abs(y2 - y1),
	});
};

const clampRegionToUnit = (box: TraceRegion): TraceRegion => {
	const x1 = clamp(box.x);
	const y1 = clamp(box.y);
	const x2 = clamp(box.x + box.w);
	const y2 = clamp(box.y + box.h);
	return normalizeRegion({
		x: Math.min(x1, x2),
		y: Math.min(y1, y2),
		w: Math.max(0.001, Math.abs(x2 - x1)),
		h: Math.max(0.001, Math.abs(y2 - y1)),
	});
};

const boundsToRegion = (bounds?: { minX: number; maxX: number; minY: number; maxY: number }, fallback?: TraceRegion): TraceRegion => {
	if (!bounds) return fallback ?? { x: 0, y: 0, w: 1, h: 1 };
	return clampRegionToUnit({
		x: bounds.minX,
		y: bounds.minY,
		w: bounds.maxX - bounds.minX,
		h: bounds.maxY - bounds.minY,
	});
};

const regionsNearlyEqual = (a: TraceRegion, b: TraceRegion, epsilon = 1e-6) => (
	Math.abs(a.x - b.x) <= epsilon &&
	Math.abs(a.y - b.y) <= epsilon &&
	Math.abs(a.w - b.w) <= epsilon &&
	Math.abs(a.h - b.h) <= epsilon
);

const shouldUseFocusAsMainPlanBox = (
	focusBox: TraceRegion | undefined,
	recognitionRegion: TraceRegion,
	hasRequestedRegion: boolean,
	focused?: boolean
) => {
	if (hasRequestedRegion || !focused || !focusBox) return false;
	if (regionsNearlyEqual(focusBox, recognitionRegion, 0.01)) return false;
	const focusArea = focusBox.w * focusBox.h;
	const recognitionArea = Math.max(0.001, recognitionRegion.w * recognitionRegion.h);
	const relativeCoverage = focusArea / recognitionArea;
	return focusBox.w >= 0.12 &&
		focusBox.h >= 0.12 &&
		focusArea >= 0.025 &&
		relativeCoverage >= 0.05 &&
		relativeCoverage <= 0.90;
};

const mapRegionBetweenBoxes = (box: TraceRegion, fromBox: TraceRegion, toBox: TraceRegion): TraceRegion => {
	const x1 = fromBox.x + box.x * fromBox.w;
	const y1 = fromBox.y + box.y * fromBox.h;
	const x2 = fromBox.x + (box.x + box.w) * fromBox.w;
	const y2 = fromBox.y + (box.y + box.h) * fromBox.h;
	return {
		x: (x1 - toBox.x) / Math.max(0.001, toBox.w),
		y: (y1 - toBox.y) / Math.max(0.001, toBox.h),
		w: Math.abs(x2 - x1) / Math.max(0.001, toBox.w),
		h: Math.abs(y2 - y1) / Math.max(0.001, toBox.h),
	};
};

const mapPointBetweenBoxes = (point: TracePoint, fromBox: TraceRegion, toBox: TraceRegion): TracePoint => ({
	x: clamp((fromBox.x + point.x * fromBox.w - toBox.x) / Math.max(0.001, toBox.w)),
	y: clamp((fromBox.y + point.y * fromBox.h - toBox.y) / Math.max(0.001, toBox.h)),
});

const regionToBBox = (region: TraceRegion): [number, number, number, number] => [
	region.x,
	region.y,
	region.x + region.w,
	region.y + region.h,
];

const bboxToRegion = (bbox: [number, number, number, number]): TraceRegion => ({
	x: bbox[0],
	y: bbox[1],
	w: bbox[2] - bbox[0],
	h: bbox[3] - bbox[1],
});

const rebaseElementsToMainPlan = (elements: TraceElement[], sourceBox: TraceRegion, mainPlanBox: TraceRegion) => (
	elements
		.map((element): TraceElement | null => {
			const mapped = mapRegionBetweenBoxes(element, sourceBox, mainPlanBox);
			if (mapped.x > 1 || mapped.y > 1 || mapped.x + mapped.w < 0 || mapped.y + mapped.h < 0) return null;
			const clipped = clampRegionToUnit(mapped);
			const sourceContentRegion: TraceRegion = {
				x: sourceBox.x + element.x * sourceBox.w,
				y: sourceBox.y + element.y * sourceBox.h,
				w: element.w * sourceBox.w,
				h: element.h * sourceBox.h,
			};
			return {
				...element,
				...clipped,
				points: element.points?.map((point) => mapPointBetweenBoxes(point, sourceBox, mainPlanBox)),
				coordinateProvenance: {
					coordSpace: 'main_plan_box',
					referenceBoxId: 'mainPlanBox',
					sourceContentBBox: regionToBBox(sourceContentRegion),
					mainPlanBBox: regionToBBox(clipped),
					renderBBox: regionToBBox(clipped),
				},
			};
		})
		.filter((element): element is TraceElement => element !== null && element.w > 0.0005 && element.h > 0.0005)
);

const regionFromContentToPage = (region: TraceRegion, contentBox: TraceRegion): TraceRegion => clampRegionToUnit({
	x: contentBox.x + region.x * contentBox.w,
	y: contentBox.y + region.y * contentBox.h,
	w: region.w * contentBox.w,
	h: region.h * contentBox.h,
});

const attachPageCoordinateProvenance = (elements: TraceElement[], contentBox: TraceRegion): TraceElement[] => (
	elements.map((element) => {
		const provenance = element.coordinateProvenance;
		const sourceContentBBox = provenance?.sourceContentBBox;
		if (!provenance || !sourceContentBBox) return element;
		const sourcePageRegion = regionFromContentToPage(bboxToRegion(sourceContentBBox), contentBox);
		return {
			...element,
			coordinateProvenance: {
				coordSpace: provenance.coordSpace,
				referenceBoxId: provenance.referenceBoxId,
				sourceContentBBox: provenance.sourceContentBBox,
				mainPlanBBox: provenance.mainPlanBBox,
				renderBBox: provenance.renderBBox,
				sourcePageBBox: regionToBBox(sourcePageRegion),
			},
		};
	})
);

const elementCenter = (element: TraceElement): TracePoint => ({
	x: element.x + element.w / 2,
	y: element.y + element.h / 2,
});

const wallElementCenterline = (wall: TraceElement): [TracePoint, TracePoint] => {
	const horizontal = wall.w >= wall.h;
	return horizontal
		? [{ x: wall.x, y: wall.y + wall.h / 2 }, { x: wall.x + wall.w, y: wall.y + wall.h / 2 }]
		: [{ x: wall.x + wall.w / 2, y: wall.y }, { x: wall.x + wall.w / 2, y: wall.y + wall.h }];
};

const clusterNumericValues = (values: number[], tolerance: number) => {
	const clusters: number[][] = [];
	[...values].filter((value) => Number.isFinite(value) && value > 0).sort((a, b) => a - b).forEach((value) => {
		const last = clusters[clusters.length - 1];
		if (!last || Math.abs(value - (last.reduce((sum, item) => sum + item, 0) / last.length)) > tolerance) clusters.push([value]);
		else last.push(value);
	});
	return clusters.map((cluster) => Math.round(cluster.reduce((sum, value) => sum + value, 0) / cluster.length));
};

const buildWallGraphDraft = (elements: TraceElement[], mmPerNormalized: number): WallGraphDraft => {
	const walls = elements.filter((element) => element.kind === 'wall_trace');
	const columns = elements.filter((element) => element.kind === 'column');
	// ── 直交约束：对与正交方向偏差 < 3° 的墙脊线强制修正 ─────────────────────
	const snapOrthogonal = (p1: TracePoint, p2: TracePoint): [TracePoint, TracePoint] => {
		const dx = p2.x - p1.x;
		const dy = p2.y - p1.y;
		const angle = Math.abs(Math.atan2(Math.abs(dy), Math.abs(dx)) * 180 / Math.PI);
		const SNAP_DEG = 3.0;
		if (angle <= SNAP_DEG) {
			const midY = (p1.y + p2.y) / 2;
			return [{ x: p1.x, y: midY }, { x: p2.x, y: midY }];
		}
		if (angle >= 90 - SNAP_DEG) {
			const midX = (p1.x + p2.x) / 2;
			return [{ x: midX, y: p1.y }, { x: midX, y: p2.y }];
		}
		return [p1, p2];
	};

	const wallGraphWalls = walls.map((wall) => {
		const rawCL = wallElementCenterline(wall);
		const snappedCL = snapOrthogonal(rawCL[0], rawCL[1]);
		return {
			wallId: wall.id,
			centerline: snappedCL,
			thickness: Math.max(40, Math.round(Math.min(wall.w, wall.h) * mmPerNormalized)),
			confidence: wall.confidence,
			joints: [] as string[],
			sourceRefs: [wall.id],
		};
	});
	const joints: WallGraphDraft['joints'] = [];
	// 真实BUG4 fix: 硬编码 0.035 与 mmPerNormalized 脱钩。
	// mmPerNorm=21000→≈0.007(150mm)，mmPerNorm=3000→0.030(capped,≈90mm)，mmPerNorm=55000→≈0.003(≈165mm 物理合理)
	const endpointTolerance = Math.min(0.030, Math.max(0.005, 150 / mmPerNormalized));
	const columnBindTolerance = Math.min(0.040, Math.max(0.008, 200 / mmPerNormalized));
	// 交叉容差：扩大到柱半身宽（约250mm），使墙在穿越柱区时仍能检测出 T/cross 节点
	const intersectionTolerance = Math.min(0.030, Math.max(0.010, 250 / mmPerNormalized));
	const addJointIfMissing = (point: TracePoint, wallIds: string[]) => {
		if (wallIds.length <= 1) return;
		const dedupWallIds = Array.from(new Set(wallIds));
		if (joints.some((joint) => {
			const sameWallSet = joint.wallIds.length === dedupWallIds.length && dedupWallIds.every((wallId) => joint.wallIds.includes(wallId));
			return sameWallSet && Math.hypot(joint.point.x - point.x, joint.point.y - point.y) <= endpointTolerance;
		})) return;
		joints.push({
			jointId: `joint-${joints.length + 1}`,
			point,
			wallIds: dedupWallIds,
			type: dedupWallIds.length >= 4 ? 'cross' : dedupWallIds.length === 3 ? 'T' : 'L',
		});
	};
	const endpointRefs = wallGraphWalls.flatMap((wall) => wall.centerline.map((point, endpointIndex) => ({ point, wallId: wall.wallId, endpointIndex })));
	const findEndpointConnections = (ref: { point: TracePoint; wallId: string }) => {
		const endpointWallIds = endpointRefs
			.filter((other) => other.wallId !== ref.wallId && Math.hypot(other.point.x - ref.point.x, other.point.y - ref.point.y) <= endpointTolerance)
			.map((item) => item.wallId);
		const segmentWallIds = wallGraphWalls
			.filter((wall) => wall.wallId !== ref.wallId)
			.filter((wall) => distancePointToSegment(ref.point, wall.centerline[0], wall.centerline[1]) <= endpointTolerance)
			.map((wall) => wall.wallId);
		return Array.from(new Set([ref.wallId, ...endpointWallIds, ...segmentWallIds]));
	};
	endpointRefs.forEach((ref) => {
		const wallIds = findEndpointConnections(ref);
		addJointIfMissing(ref.point, wallIds);
	});

	// ── 脊线交点拓扑：补齐非端点交汇（T/cross）────────────────────────────────
	for (let i = 0; i < wallGraphWalls.length; i += 1) {
		const a = wallGraphWalls[i];
		const aDx = Math.abs(a.centerline[1].x - a.centerline[0].x);
		const aDy = Math.abs(a.centerline[1].y - a.centerline[0].y);
		const aHorizontal = aDx >= aDy;
		for (let j = i + 1; j < wallGraphWalls.length; j += 1) {
			const b = wallGraphWalls[j];
			const bDx = Math.abs(b.centerline[1].x - b.centerline[0].x);
			const bDy = Math.abs(b.centerline[1].y - b.centerline[0].y);
			const bHorizontal = bDx >= bDy;
			if (aHorizontal === bHorizontal) continue;

			const h = aHorizontal ? a : b;
			const v = aHorizontal ? b : a;
			const hx1 = Math.min(h.centerline[0].x, h.centerline[1].x);
			const hx2 = Math.max(h.centerline[0].x, h.centerline[1].x);
			const hy = (h.centerline[0].y + h.centerline[1].y) / 2;
			const vx = (v.centerline[0].x + v.centerline[1].x) / 2;
			const vy1 = Math.min(v.centerline[0].y, v.centerline[1].y);
			const vy2 = Math.max(v.centerline[0].y, v.centerline[1].y);

			const onH = vx >= hx1 - intersectionTolerance && vx <= hx2 + intersectionTolerance;
			const onV = hy >= vy1 - intersectionTolerance && hy <= vy2 + intersectionTolerance;
			if (!onH || !onV) continue;

			const point: TracePoint = { x: vx, y: hy };
			const crossingWalls = wallGraphWalls
				.filter((wall) => distancePointToSegment(point, wall.centerline[0], wall.centerline[1]) <= endpointTolerance)
				.map((wall) => wall.wallId);
			addJointIfMissing(point, crossingWalls);
		}
	}
	wallGraphWalls.forEach((wall) => {
		wall.joints = joints.filter((joint) => joint.wallIds.includes(wall.wallId)).map((joint) => joint.jointId);
	});
	const wallElementById = new Map(walls.map((wall) => [wall.id, wall]));
	const hasColumnAnchor = (wallId: string) => {
		const wall = wallElementById.get(wallId);
		if (!wall) return false;
		return columns.some((column) => {
			if (rectIntersects(wall, column)) return true;
			if (distancePointToWallElement(elementCenter(column), wall) <= columnBindTolerance) return true;
			// 墙端点落在柱包围盒附近（覆盖墙截止在柱侧面的情形：柱心离墙端可达柱半宽≈250mm）
			const isHoriz = wall.w >= wall.h;
			const ep1 = isHoriz ? { x: wall.x, y: wall.y + wall.h / 2 } : { x: wall.x + wall.w / 2, y: wall.y };
			const ep2 = isHoriz ? { x: wall.x + wall.w, y: wall.y + wall.h / 2 } : { x: wall.x + wall.w / 2, y: wall.y + wall.h };
			const pad = Math.max(column.w, column.h) * 0.55; // ≈ 柱半身宽
			const cx1 = column.x - pad; const cx2 = column.x + column.w + pad;
			const cy1 = column.y - pad; const cy2 = column.y + column.h + pad;
			return (ep1.x >= cx1 && ep1.x <= cx2 && ep1.y >= cy1 && ep1.y <= cy2)
				|| (ep2.x >= cx1 && ep2.x <= cx2 && ep2.y >= cy1 && ep2.y <= cy2);
		});
	};
	const danglingWallIds = wallGraphWalls.filter((wall) => wall.joints.length === 0 && !hasColumnAnchor(wall.wallId)).map((wall) => wall.wallId);
	const wallLengths = wallGraphWalls.map((wall) => Math.hypot(wall.centerline[1].x - wall.centerline[0].x, wall.centerline[1].y - wall.centerline[0].y));
	const medianWallLength = wallLengths.length
		? [...wallLengths].sort((a, b) => a - b)[Math.floor(wallLengths.length / 2)]
		: 0.055;
	const shortThreshold = Math.min(0.055, Math.max(0.024, medianWallLength * 0.38));
	const fragmentGroups = wallGraphWalls
		.filter((wall) => {
			const length = Math.hypot(wall.centerline[1].x - wall.centerline[0].x, wall.centerline[1].y - wall.centerline[0].y);
			return length < shortThreshold && wall.joints.length === 0 && !hasColumnAnchor(wall.wallId);
		})
		.map((wall) => [wall.wallId]);
	return {
		walls: wallGraphWalls,
		joints,
		thicknessClusters: clusterNumericValues(wallGraphWalls.map((wall) => wall.thickness), 80),
		danglingWallIds,
		fragmentGroups,
	};
};

// ═══════════════════════════════════════════════════════════════════════
// ─── Wall Gap Detection：同轨道墙段间缺口扫描（开口候选来源） ──────────
// ═══════════════════════════════════════════════════════════════════════

interface WallGap {
	wallIdA: string;
	wallIdB: string;
	gapStart: number;
	gapEnd: number;
	gapWidthNorm: number;
	gapCenterPoint: TracePoint;
	isHorizontal: boolean;
	track: number;
}

const detectWallGaps = (wallGraph: WallGraphDraft, walls: TraceElement[], mmPerNormalized: number): WallGap[] => {
	const gaps: WallGap[] = [];
	const doorWidthMin = 600; // mm
	const doorWidthMax = 2400; // mm

	// 按轨道分组：水平/垂直 + 中心线位置
	interface TrackEntry { wallId: string; start: number; end: number; track: number; isHorizontal: boolean }
	const trackEntries: TrackEntry[] = walls.map((w) => {
		const isH = w.w >= w.h;
		return {
			wallId: w.id,
			start: isH ? w.x : w.y,
			end: isH ? w.x + w.w : w.y + w.h,
			track: isH ? w.y + w.h / 2 : w.x + w.w / 2,
			isHorizontal: isH,
		};
	});

	// T/cross joint 位置集合（用于排除结构节点处 gap）
	const jointPoints = wallGraph.joints.map((j) => j.point);
	const jointProximity = 0.02;

	// 分桶：取 track 值聚类
	const trackTolerance = 0.016;
	const buckets = new Map<string, TrackEntry[]>();
	trackEntries.forEach((entry) => {
		const key = `${entry.isHorizontal ? 'H' : 'V'}_${Math.round(entry.track * 1000)}`;
		let placed = false;
		for (const [bk, entries] of buckets) {
			if (bk.startsWith(entry.isHorizontal ? 'H' : 'V') && entries.length > 0 && Math.abs(entries[0].track - entry.track) <= trackTolerance) {
				entries.push(entry);
				placed = true;
				break;
			}
		}
		if (!placed) buckets.set(key, [entry]);
	});

	for (const [, entries] of buckets) {
		if (entries.length < 2) continue;
		entries.sort((a, b) => a.start - b.start);
		for (let i = 0; i < entries.length - 1; i++) {
			const a = entries[i];
			const b = entries[i + 1];
			const gapStart = a.end;
			const gapEnd = b.start;
			const gapWidthNorm = gapEnd - gapStart;
			if (gapWidthNorm <= 0) continue;
			const gapWidthMm = gapWidthNorm * mmPerNormalized;
			if (gapWidthMm < doorWidthMin || gapWidthMm > doorWidthMax) continue;

			const avgTrack = (a.track + b.track) / 2;
			const gapCenter = a.isHorizontal
				? { x: (gapStart + gapEnd) / 2, y: avgTrack }
				: { x: avgTrack, y: (gapStart + gapEnd) / 2 };

			// 排除 T/cross 节点处的缺口
			const nearJoint = jointPoints.some((jp) => Math.hypot(jp.x - gapCenter.x, jp.y - gapCenter.y) <= jointProximity);
			if (nearJoint) continue;

			gaps.push({
				wallIdA: a.wallId,
				wallIdB: b.wallId,
				gapStart,
				gapEnd,
				gapWidthNorm,
				gapCenterPoint: gapCenter,
				isHorizontal: a.isHorizontal,
				track: avgTrack,
			});
		}
	}
	return gaps;
};

// ═══════════════════════════════════════════════════════════════════════
// ─── Wall Verification：墙体类型验证与分类系统 ─────────────────────────
// ═══════════════════════════════════════════════════════════════════════

const verifyAndClassifyWall = (
	wall: TraceElement,
	wallGraph: WallGraphDraft,
	gridPrior: GridPriorOutput | undefined,
	mmPerNormalized: number,
	focusBounds?: { minX: number; maxX: number; minY: number; maxY: number }
): WallVerification => {
	const reviewFlags: WallReviewFlag[] = [];
	const wallThicknessMm = Math.max(40, Math.round(Math.min(wall.w, wall.h) * mmPerNormalized));
	const isHorizontal = wall.w >= wall.h;
	const graphWall = wallGraph.walls.find((w) => w.wallId === wall.id);
	const isDangling = wallGraph.danglingWallIds.includes(wall.id);
	const isFragment = wallGraph.fragmentGroups.some((group) => group.includes(wall.id));

	// ── 1. thicknessScore：厚度与聚类比较 ──
	let thicknessScore = 0.5;
	const clusters = wallGraph.thicknessClusters;
	if (clusters.length >= 2) {
		const maxCluster = Math.max(...clusters);
		const minCluster = Math.min(...clusters);
		if (maxCluster > minCluster) {
			thicknessScore = Math.max(0, Math.min(1, (wallThicknessMm - minCluster) / (maxCluster - minCluster)));
		}
		if (wallThicknessMm >= 200) thicknessScore = Math.max(thicknessScore, 0.8);
		else if (wallThicknessMm >= 150) thicknessScore = Math.max(thicknessScore, 0.6);
		else if (wallThicknessMm <= 100) thicknessScore = Math.min(thicknessScore, 0.35);
	} else {
		if (wallThicknessMm >= 200) thicknessScore = 0.85;
		else if (wallThicknessMm >= 150) thicknessScore = 0.6;
		else if (wallThicknessMm >= 100) thicknessScore = 0.4;
		else thicknessScore = 0.2;
	}
	if (wallThicknessMm < 60 || wallThicknessMm > 600) reviewFlags.push('thickness_outlier');

	// ── 2. connectivityScore：节点连接质量 ──
	let connectivityScore = 0;
	if (graphWall) {
		const jointCount = graphWall.joints.length;
		const wallJoints = wallGraph.joints.filter((j) => j.wallIds.includes(wall.id));
		const hasCross = wallJoints.some((j) => j.type === 'cross');
		const hasT = wallJoints.some((j) => j.type === 'T');
		if (hasCross) connectivityScore = 0.95;
		else if (hasT && jointCount >= 2) connectivityScore = 0.85;
		else if (hasT) connectivityScore = 0.7;
		else if (jointCount >= 3) connectivityScore = 0.9;
		else if (jointCount >= 2) connectivityScore = 0.65;
		else if (jointCount >= 1) connectivityScore = 0.45;
		else connectivityScore = 0.1;
	}
	if (isDangling) { connectivityScore = Math.min(connectivityScore, 0.15); reviewFlags.push('dangling_no_joint'); }
	if (isFragment) connectivityScore = Math.min(connectivityScore, 0.1);

	// ── 3. axisAlignmentScore：与轴网的对齐度 ──
	let axisAlignmentScore = 0;
	if (gridPrior && gridPrior.axes.length > 0) {
		const cx = wall.x + wall.w / 2;
		const cy = wall.y + wall.h / 2;
		const wallDir: GridAxisDirection = isHorizontal ? 'horizontal' : 'vertical';
		const parallelAxes = gridPrior.axes.filter((a) => a.direction === wallDir);
		if (parallelAxes.length > 0) {
			const wallTrack = isHorizontal ? cy : cx;
			const nearestAxisDist = Math.min(...parallelAxes.map((a) => {
				const axisTrack = a.direction === 'horizontal' ? a.line[0][1] : a.line[0][0];
				return Math.abs(axisTrack - wallTrack);
			}));
			const distMm = nearestAxisDist * mmPerNormalized;
			if (distMm <= 50) axisAlignmentScore = 1.0;
			else if (distMm <= 100) axisAlignmentScore = 0.75;
			else if (distMm <= 200) axisAlignmentScore = 0.45;
			else if (distMm <= 400) axisAlignmentScore = 0.2;
		}
		// 轴网对齐带加成
		for (const band of gridPrior.wallAlignmentBands) {
			if (band.direction !== (isHorizontal ? 'horizontal' : 'vertical')) continue;
			const axis = gridPrior.axes.find((a) => a.id === band.axisId);
			if (!axis) continue;
			const axisTrack = axis.direction === 'horizontal' ? axis.line[0][1] : axis.line[0][0];
			const bandTrack = axisTrack + band.offsetNorm;
			const wallTrack = isHorizontal ? (wall.y + wall.h / 2) : (wall.x + wall.w / 2);
			const distMm = Math.abs(bandTrack - wallTrack) * mmPerNormalized;
			if (distMm <= 60) { axisAlignmentScore = Math.max(axisAlignmentScore, 0.8); break; }
		}
	}
	if (axisAlignmentScore < 0.2 && gridPrior && gridPrior.axes.length > 0) reviewFlags.push('grid_inconsistent');

	// ── 4. envelopeScore：是否位于建筑外轮廓 ──
	let envelopeScore = 0;
	if (focusBounds) {
		const fbW = focusBounds.maxX - focusBounds.minX;
		const fbH = focusBounds.maxY - focusBounds.minY;
		const edgeTolerance = Math.min(fbW, fbH) * 0.05;
		const wallStart = isHorizontal
			? { x: wall.x, y: wall.y + wall.h / 2 }
			: { x: wall.x + wall.w / 2, y: wall.y };
		const wallEnd = isHorizontal
			? { x: wall.x + wall.w, y: wall.y + wall.h / 2 }
			: { x: wall.x + wall.w / 2, y: wall.y + wall.h };
		const nearEdge = (p: { x: number; y: number }) =>
			Math.abs(p.x - focusBounds.minX) <= edgeTolerance ||
			Math.abs(p.x - focusBounds.maxX) <= edgeTolerance ||
			Math.abs(p.y - focusBounds.minY) <= edgeTolerance ||
			Math.abs(p.y - focusBounds.maxY) <= edgeTolerance;
		if (nearEdge(wallStart) && nearEdge(wallEnd)) envelopeScore = 0.9;
		else if (nearEdge(wallStart) || nearEdge(wallEnd)) envelopeScore = 0.6;
		const cx = wall.x + wall.w / 2;
		const cy = wall.y + wall.h / 2;
		const relX = fbW > 0 ? (cx - focusBounds.minX) / fbW : 0.5;
		const relY = fbH > 0 ? (cy - focusBounds.minY) / fbH : 0.5;
		if (relX < 0.05 || relX > 0.95 || relY < 0.05 || relY > 0.95) {
			envelopeScore = Math.max(envelopeScore, 0.7);
		}
	}

	// ── 5. lineWidthScore：PDF 线宽（TraceElement 未携带，中性默认）──
	const lineWidthScore = 0.5;

	// ── 6. continuityScore：墙体连续长度 ──
	let continuityScore = 0.5;
	if (focusBounds) {
		const focusDim = Math.max(focusBounds.maxX - focusBounds.minX, focusBounds.maxY - focusBounds.minY);
		if (focusDim > 0) {
			const ratio = Math.max(wall.w, wall.h) / focusDim;
			if (ratio >= 0.3) continuityScore = 0.95;
			else if (ratio >= 0.15) continuityScore = 0.75;
			else if (ratio >= 0.08) continuityScore = 0.55;
			else if (ratio >= 0.04) continuityScore = 0.35;
			else continuityScore = 0.15;
		}
	}

	// ── 加权总分 ──
	const hasGrid = gridPrior && gridPrior.axes.length > 0;
	const totalScore = hasGrid
		? thicknessScore * 0.18 + connectivityScore * 0.18 + axisAlignmentScore * 0.20
			+ envelopeScore * 0.15 + lineWidthScore * 0.12 + continuityScore * 0.17
		: thicknessScore * 0.22 + connectivityScore * 0.22 + envelopeScore * 0.18
			+ lineWidthScore * 0.16 + continuityScore * 0.22;

	// ── 类型判定决策树 ──
	let structuralRole: WallStructuralRole;
	let removability: WallRemovability;
	const interiorActionHints: InteriorActionHint[] = [];

	if (axisAlignmentScore >= 0.7 && thicknessScore >= 0.6 && connectivityScore >= 0.5) {
		structuralRole = 'primary_structural_wall';
		removability = 'non_removable';
		interiorActionHints.push('avoid_demolition', 'wrap');
	} else if (envelopeScore >= 0.7) {
		structuralRole = 'enclosure_wall';
		removability = 'conditional';
		interiorActionHints.push('limited_opening_only', 'wrap');
	} else if (thicknessScore < 0.35 && connectivityScore < 0.3 && isDangling) {
		structuralRole = 'light_partition';
		removability = 'likely_removable';
		interiorActionHints.push('can_repartition');
	} else if (thicknessScore < 0.5 && envelopeScore < 0.3 && axisAlignmentScore < 0.3) {
		structuralRole = 'partition_wall';
		removability = 'likely_removable';
		interiorActionHints.push('can_repartition');
	} else if (connectivityScore >= 0.5 && thicknessScore >= 0.5) {
		structuralRole = 'primary_structural_wall';
		removability = 'non_removable';
		interiorActionHints.push('avoid_demolition', 'wrap');
	} else if (totalScore >= 0.55) {
		structuralRole = 'primary_structural_wall';
		removability = 'conditional';
		interiorActionHints.push('needs_structural_review');
		reviewFlags.push('wall_type_unresolved');
	} else {
		structuralRole = 'wall_candidate_unverified';
		removability = 'unknown';
		interiorActionHints.push('needs_structural_review');
		reviewFlags.push('wall_type_unresolved');
	}

	const confidence = Math.max(0.2, Math.min(0.95, wall.confidence * 0.35 + totalScore * 0.65));

	return {
		structuralRole,
		removability,
		interiorActionHints,
		confidence,
		evidence: {
			thickness: Math.round(thicknessScore * 100) / 100,
			connectivity: Math.round(connectivityScore * 100) / 100,
			axisAlignment: Math.round(axisAlignmentScore * 100) / 100,
			envelope: Math.round(envelopeScore * 100) / 100,
			lineWidth: Math.round(lineWidthScore * 100) / 100,
			continuity: Math.round(continuityScore * 100) / 100,
		},
		reviewFlags,
	};
};

const runWallVerificationPipeline = (
	wallElements: TraceElement[],
	wallGraph: WallGraphDraft,
	gridPrior: GridPriorOutput | undefined,
	mmPerNormalized: number,
	focusBounds?: { minX: number; maxX: number; minY: number; maxY: number }
): { walls: TraceElement[]; reviewIssues: ReviewIssue[] } => {
	const reviewIssues: ReviewIssue[] = [];
	for (const wall of wallElements) {
		wall.wallVerification = verifyAndClassifyWall(wall, wallGraph, gridPrior, mmPerNormalized, focusBounds);
	}
	const unverifiedWalls = wallElements.filter((w) => w.wallVerification?.structuralRole === 'wall_candidate_unverified');
	if (unverifiedWalls.length > wallElements.length * 0.5 && wallElements.length >= 6) {
		reviewIssues.push({
			id: 'review-wall-unverified-high',
			type: 'wall_type_unresolved',
			severity: 'warning',
			message: `超半数墙体(${unverifiedWalls.length}/${wallElements.length})未通过类型验证，墙类型检测质量偏低。`,
			targetIds: unverifiedWalls.map((w) => w.id),
		});
	}
	const gridInconsistentWalls = wallElements.filter((w) => w.wallVerification?.reviewFlags?.includes('grid_inconsistent'));
	if (gridInconsistentWalls.length > 3) {
		reviewIssues.push({
			id: 'review-wall-grid-inconsistent',
			type: 'wall_grid_inconsistent',
			severity: 'info',
			message: `${gridInconsistentWalls.length} 面墙与轴网不一致，可能为隔墙或标注污染。`,
			targetIds: gridInconsistentWalls.slice(0, 10).map((w) => w.id),
		});
	}
	const thicknessOutlierWalls = wallElements.filter((w) => w.wallVerification?.reviewFlags?.includes('thickness_outlier'));
	if (thicknessOutlierWalls.length > 0) {
		reviewIssues.push({
			id: 'review-wall-thickness-outlier',
			type: 'wall_thickness_outlier',
			severity: 'info',
			message: `${thicknessOutlierWalls.length} 面墙厚度异常(< 60mm 或 > 600mm)。`,
			targetIds: thicknessOutlierWalls.map((w) => w.id),
		});
	}

	// ── 女儿墙 / 栏杆后处理：在外墙外侧检测矮墙或薄线 ──
	// 判断标准：已识别为 enclosure_wall 的外墙的外侧，平行且紧邻的矮墙 → parapet_wall；
	// 极薄墙体（thickness < 100mm）紧贴外墙 → railing_line
	const enclosureWalls = wallElements.filter((w) => w.wallVerification?.structuralRole === 'enclosure_wall');
	for (const wall of wallElements) {
		const wv = wall.wallVerification;
		if (!wv || wv.structuralRole !== 'wall_candidate_unverified' && wv.structuralRole !== 'light_partition') continue;
		const thicknessMm = Math.min(wall.w, wall.h) * mmPerNormalized;
		const nearEnclosure = enclosureWalls.some((ew) => {
			const parallel = (wall.w >= wall.h) === (ew.w >= ew.h);
			const maxGap = 0.025; // 归一化坐标约 500mm
			return parallel && rectEdgeDistance(wall, ew) <= maxGap;
		});
		if (!nearEnclosure) continue;
		if (thicknessMm < 100) {
			wv.structuralRole = 'railing_line';
			wv.removability = 'likely_removable';
			wv.interiorActionHints = ['can_repartition'];
		} else if (thicknessMm >= 100 && thicknessMm <= 300) {
			wv.structuralRole = 'parapet_wall';
			wv.removability = 'non_removable';
			wv.interiorActionHints = ['wrap'];
		}
	}

	// ── 女儿墙/栏杆评审 ──
	const parapetWalls = wallElements.filter((w) => w.wallVerification?.structuralRole === 'parapet_wall');
	const railingWalls = wallElements.filter((w) => w.wallVerification?.structuralRole === 'railing_line');
	if (parapetWalls.length + railingWalls.length > 0 && parapetWalls.length + railingWalls.length > enclosureWalls.length * 0.8) {
		reviewIssues.push({
			id: 'review-wall-parapet-railing-excessive',
			type: 'parapet_railing_ambiguous',
			severity: 'info',
			message: `女儿墙/栏杆(${parapetWalls.length + railingWalls.length})相对外墙(${enclosureWalls.length})比例偏高，可能存在误判。`,
			targetIds: [...parapetWalls, ...railingWalls].map((w) => w.id),
		});
	}

	return { walls: wallElements, reviewIssues };
};

// ═══════════════════════════════════════════════════════════════════════
// ─── Opening Verification：开口类型验证与分类系统 ──────────────────────
// ═══════════════════════════════════════════════════════════════════════

const verifyAndClassifyOpening = (
	door: TraceElement,
	wallGraph: WallGraphDraft,
	wallGaps: WallGap[],
	dashedSegments: TraceSegment[],
	allWalls: TraceElement[],
	mmPerNormalized: number
): OpeningVerification => {
	const reviewFlags: OpeningReviewFlag[] = [];
	const cx = door.x + door.w / 2;
	const cy = door.y + door.h / 2;
	const doorCenter = { x: cx, y: cy };
	const doorWidthNorm = Math.max(door.w, door.h);
	const doorWidthMm = doorWidthNorm * mmPerNormalized;

	// ── 宿主墙绑定 ──
	// 优先策略：先精确距离匹配宿主墙段；若宿主墙属于逻辑墙（logicalWallId），
	// 则跨门洞的另一侧墙段可识别为同一逻辑墙，hostWallId 统一用 logicalWallId 表示单一逻辑墙体。
	let hostWall: TraceElement | undefined;
	let hostWallGraphEntry: WallGraphDraft['walls'][0] | undefined;
	let bestDist = 0.040; // 宽松到 40mm 对角距离，确保斜向门也能绑墙
	for (const w of allWalls) {
		const d = nearestWallDistance(door, w);
		if (d < bestDist) { bestDist = d; hostWall = w; }
	}
	if (hostWall) {
		hostWallGraphEntry = wallGraph.walls.find((gw) => gw.wallId === hostWall!.id);
	}
	const hostWallRole = hostWall?.wallVerification?.structuralRole;
	// 使用 logicalWallId 作为规范 hostWallId（若存在），使 openingVerification 指向完整逻辑墙
	const hostWallCanonicalId = hostWall
		? ((hostWall as TraceElement & { logicalWallId?: string }).logicalWallId ?? hostWall.id)
		: undefined;

	// ── 匹配墙缺口 ──
	const matchGapTol = doorWidthNorm * 0.5;
	const matchedGap = wallGaps.find((g) => Math.hypot(g.gapCenterPoint.x - cx, g.gapCenterPoint.y - cy) <= matchGapTol);

	// ── 弧段信号（from label + confidence）──
	const hasArcSignal = door.label?.includes('平开门') || door.label?.includes('弧门') || door.label?.includes('双开门');
	const hasLeafSignal = door.label?.includes('平开门');
	const isDoubleDoorLabel = door.label?.includes('双开门');
	const isSlidingLabel = door.label?.includes('推拉门');
	const isVoidLabel = door.label?.includes('门洞');

	// ═══════════════ 6-dim 评分 ═══════════════

	// 1. arcQuality: 弧跨角近 90°、bbox 近似正方形
	let arcQuality = 0;
	if (hasArcSignal) {
		const aspect = Math.min(door.w, door.h) / Math.max(door.w, door.h);
		arcQuality = clamp(aspect / 0.8, 0, 1); // aspect→1.0 = 满分
		if (arcQuality < 0.5) reviewFlags.push('arc_quality_low');
	}

	// 2. leafBinding: 门扇直线与弧铰点共享度
	let leafBinding = 0;
	if (hasLeafSignal) {
		leafBinding = 0.85; // label 已验证存在门扇
	} else if (hasArcSignal) {
		leafBinding = 0.3; // 有弧但无门扇
		reviewFlags.push('no_leaf_binding');
	}

	// 3. wallBinding: gap 对位 + 墙端对齐质量
	let wallBinding = 0;
	if (matchedGap) {
		const gapWidthRatio = matchedGap.gapWidthNorm / doorWidthNorm;
		wallBinding = clamp(1 - Math.abs(gapWidthRatio - 1) * 2, 0, 1); // gap 宽度 ≈ 门宽 → 高分
	} else if (hostWall) {
		// 无独立 gap 但绑定了宿主墙
		wallBinding = 0.4;
	}
	if (!hostWall) reviewFlags.push('host_wall_unbound');

	// 4. sizeCompliance: 宽度是否在合理范围 (600mm–2400mm)
	let sizeCompliance = 0;
	if (doorWidthMm >= 600 && doorWidthMm <= 2400) {
		if (doorWidthMm >= 750 && doorWidthMm <= 1200) sizeCompliance = 1.0; // 最佳范围
		else if (doorWidthMm >= 600 && doorWidthMm <= 900) sizeCompliance = 0.85;
		else sizeCompliance = 0.6;
	} else {
		sizeCompliance = 0.15;
		reviewFlags.push('size_non_compliant');
	}

	// 5. symmetry: 双开门对称弧信号
	let symmetry = 0;
	if (isDoubleDoorLabel) {
		symmetry = 0.85;
	}

	// 6. gapEvidence: 墙中断质量
	let gapEvidence = 0;
	if (matchedGap) {
		const gapWidthMm = matchedGap.gapWidthNorm * mmPerNormalized;
		gapEvidence = (gapWidthMm >= 600 && gapWidthMm <= 2400) ? 0.9 : 0.45;
	} else if (isVoidLabel || isSlidingLabel) {
		gapEvidence = 0.5; // 来自原始 gap 检测但未匹配 detectWallGaps
	}

	// ── 推拉门虚线轨道信号 ──
	const slidingTrackTol = 0.025;
	const hasDashedTrack = dashedSegments.some((ds) => {
		const dsH = Math.abs(ds.x2 - ds.x1) >= Math.abs(ds.y2 - ds.y1);
		const doorIsH = door.w >= door.h;
		if (dsH !== doorIsH) return false;
		const dsTrack = doorIsH ? (ds.y1 + ds.y2) / 2 : (ds.x1 + ds.x2) / 2;
		const doorTrack = doorIsH ? cy : cx;
		if (Math.abs(dsTrack - doorTrack) > slidingTrackTol) return false;
		const dsStart = doorIsH ? Math.min(ds.x1, ds.x2) : Math.min(ds.y1, ds.y2);
		const dsEnd = doorIsH ? Math.max(ds.x1, ds.x2) : Math.max(ds.y1, ds.y2);
		return dsEnd >= door.x - doorWidthNorm * 0.3 && dsStart <= door.x + doorWidthNorm + doorWidthNorm * 0.3;
	});

	// ═══════════════ 决策树 ═══════════════

	// 权重方案
	const hasArc = arcQuality >= 0.3;
	const wArc = hasArc ? 0.22 : 0;
	const wLeaf = hasArc ? 0.20 : 0;
	const wWall = hasArc ? 0.18 : 0.25;
	const wSize = hasArc ? 0.15 : 0.20;
	const wSym = hasArc ? 0.10 : 0;
	const wGap = hasArc ? 0.15 : 0.55;

	const confidence = clamp(
		wArc * arcQuality + wLeaf * leafBinding + wWall * wallBinding +
		wSize * sizeCompliance + wSym * symmetry + wGap * gapEvidence,
		0, 1
	);

	let openingType: OpeningType = 'opening_candidate_unverified';
	let swingDirection: SwingDirection = 'unknown';

	if (isDoubleDoorLabel && symmetry >= 0.7 && arcQuality >= 0.4) {
		openingType = 'double_swing_door';
	} else if ((isSlidingLabel || hasDashedTrack) && gapEvidence >= 0.4 && arcQuality < 0.3) {
		openingType = 'sliding_door';
	} else if (arcQuality >= 0.5 && leafBinding >= 0.6 && wallBinding >= 0.3) {
		openingType = 'swing_door';
		// 推测开向：基于门中心相对于宿主墙中心的偏移
		if (hostWall) {
			const wallCx = hostWall.x + hostWall.w / 2;
			const wallCy = hostWall.y + hostWall.h / 2;
			const isWallH = hostWall.w >= hostWall.h;
			if (isWallH) {
				swingDirection = cy < wallCy ? (cx < wallCx ? 'left_inward' : 'right_inward') : (cx < wallCx ? 'left_outward' : 'right_outward');
			} else {
				swingDirection = cx < wallCx ? (cy < wallCy ? 'left_inward' : 'right_inward') : (cy < wallCx ? 'left_outward' : 'right_outward');
			}
		}
	} else if (gapEvidence >= 0.6 && arcQuality < 0.2 && !hasDashedTrack) {
		openingType = 'void_passage';
	} else if (wallBinding >= 0.4 && arcQuality >= 0.3) {
		openingType = 'swing_door'; // 保守路径
	}

	if (openingType === 'opening_candidate_unverified') {
		reviewFlags.push('needs_manual_review');
	}

	// ── OpeningRemovability 从宿主墙推导 ──
	let removability: OpeningRemovability = 'unknown';
	if (hostWallRole === 'partition_wall' || hostWallRole === 'light_partition') {
		removability = 'relocatable';
	} else if (hostWallRole === 'enclosure_wall') {
		removability = 'width_adjustable';
	} else if (hostWallRole === 'primary_structural_wall' || hostWallRole === 'shear_wall') {
		removability = 'fixed';
	}
	if (openingType === 'sliding_door' || openingType === 'void_passage') {
		if (removability === 'relocatable') removability = 'type_changeable';
	}

	return {
		openingType,
		swingDirection,
		removability,
		hostWallId: hostWallCanonicalId,
		hostWallRole,
		confidence,
		evidence: { arcQuality, leafBinding, wallBinding, sizeCompliance, symmetry, gapEvidence },
		reviewFlags,
	};
};

// ═══════════════════════════════════════════════════════════════════════
// ─── Window Verification：窗户类型验证 + 6 维评分 ─────────────────────
// ═══════════════════════════════════════════════════════════════════════

const verifyAndClassifyWindow = (
	windowElement: TraceElement,
	segments: TraceSegment[],
	allWalls: TraceElement[],
	curtainWallZones: TraceElement[],
	mmPerNormalized: number
): WindowVerification => {
	const cx = windowElement.x + windowElement.w / 2;
	const cy = windowElement.y + windowElement.h / 2;
	const widthMm = (windowElement.widthMm ?? Math.max(windowElement.w, windowElement.h) * mmPerNormalized);
	const isHoriz = windowElement.w >= windowElement.h;
	const reviewFlags: WindowReviewFlag[] = [];

	// 1) glassLineQuality：窗洞范围内平行实线数量/密度
	const nearbyGlassLines = segments.filter((s) => {
		if (s.pathKind === 'curve' || s.pathKind === 'rect' || s.pathKind === 'filledRect') return false;
		if (s.dashPattern && s.dashPattern !== 'solid') return false;
		const seg = orthogonalizeSegment(s);
		if (isHorizontal(seg) !== isHoriz) return false;
		const sMid = isHoriz ? (seg.y1 + seg.y2) / 2 : (seg.x1 + seg.x2) / 2;
		const wTrack = isHoriz ? cy : cx;
		if (Math.abs(sMid - wTrack) > 0.012) return false;
		const sStart = isHoriz ? Math.min(seg.x1, seg.x2) : Math.min(seg.y1, seg.y2);
		const sEnd = isHoriz ? Math.max(seg.x1, seg.x2) : Math.max(seg.y1, seg.y2);
		const wStart = isHoriz ? windowElement.x : windowElement.y;
		const wEnd = isHoriz ? windowElement.x + windowElement.w : windowElement.y + windowElement.h;
		return sEnd >= wStart && sStart <= wEnd;
	});
	const glassLineQuality = Math.min(1, nearbyGlassLines.length >= 3 ? 0.9 : nearbyGlassLines.length >= 2 ? 0.7 : nearbyGlassLines.length === 1 ? 0.4 : 0.1);

	// 2) wallBinding：最近墙的距离 + 是否嵌入
	let hostWall: TraceElement | undefined;
	let hostWallDist = Infinity;
	allWalls.forEach((wall) => {
		const dist = distancePointToWallElement({ x: cx, y: cy }, wall);
		if (rectIntersects(windowElement, wall) && dist < hostWallDist) {
			hostWallDist = dist;
			hostWall = wall;
		} else if (!hostWall && dist < hostWallDist) {
			hostWallDist = dist;
			hostWall = wall;
		}
	});
	// 窗-墙绑定容差：rectIntersects 要求像素级重叠，外墙薄（约 12mm 归一化）时极易失效
	// 改为优先 rectIntersects，降级到 80mm 物理近邻容差
	const hostWallBindTolNorm = 80 / mmPerNormalized;
	const windowIntersectsHost = !!(hostWall && rectIntersects(windowElement, hostWall));
	const windowNearHost = !!(hostWall && hostWallDist < hostWallBindTolNorm);
	const wallBinding = windowIntersectsHost
		? Math.min(1, 0.7 + (1 - Math.min(1, hostWallDist / 0.03)) * 0.3)
		: windowNearHost ? 0.60
		: hostWallDist < 0.02 ? 0.40 : 0.15;

	// 3) sizeCompliance：窗宽在 600-4000mm 标准范围
	const sizeCompliance = widthMm >= 600 && widthMm <= 4000
		? (widthMm >= 800 && widthMm <= 2400 ? 0.9 : 0.6)
		: widthMm >= 400 && widthMm <= 5000 ? 0.3 : 0.05;

	// 4) arcPresence：窗洞附近弧段检测（平开窗开启弧）
	const searchRadius = Math.max(windowElement.w, windowElement.h) * 0.8;
	const nearbyArcs = segments.filter((s) => {
		if (s.pathKind !== 'curve') return false;
		const sMidX = (s.x1 + s.x2) / 2;
		const sMidY = (s.y1 + s.y2) / 2;
		return Math.abs(sMidX - cx) <= searchRadius && Math.abs(sMidY - cy) <= searchRadius;
	});
	const arcPresence = nearbyArcs.length >= 2 ? 0.85 : nearbyArcs.length === 1 ? 0.55 : 0.0;

	// 5) overlapPattern：交错平行线（推拉窗特征）
	const trackPositions = nearbyGlassLines.map((s) => {
		const seg = orthogonalizeSegment(s);
		return isHoriz ? seg.y1 : seg.x1;
	}).sort((a, b) => a - b);
	let overlapPattern = 0;
	if (trackPositions.length >= 3) {
		const uniqueTracks = [...new Set(trackPositions.map((t) => Math.round(t * 1000)))].length;
		overlapPattern = uniqueTracks >= 3 ? 0.75 : uniqueTracks >= 2 ? 0.4 : 0.1;
	}

	// 6) curtainWallExclusion：与幕墙区域的距离
	const inCurtainWall = curtainWallZones.some((cw) =>
		cx >= cw.x && cx <= cw.x + cw.w && cy >= cw.y && cy <= cw.y + cw.h);
	const curtainWallExclusion = inCurtainWall ? 0.1 : 1.0;

	// ── 综合置信度 ──
	const confidence = Math.min(0.92,
		glassLineQuality * 0.25
		+ wallBinding * 0.25
		+ sizeCompliance * 0.15
		+ curtainWallExclusion * 0.15
		+ Math.max(arcPresence, overlapPattern) * 0.10
		+ 0.10);

	// ── 类型决策树 ──
	let windowType: WindowType;
	if (arcPresence >= 0.6 && glassLineQuality >= 0.5 && wallBinding >= 0.4) {
		windowType = 'casement_window';
	} else if (overlapPattern >= 0.6 && glassLineQuality >= 0.5) {
		windowType = 'sliding_window';
	} else if (glassLineQuality >= 0.5 && sizeCompliance >= 0.5 && widthMm > 2400) {
		windowType = 'ribbon_window';
	} else if (glassLineQuality >= 0.5 && wallBinding >= 0.4 && arcPresence < 0.3) {
		windowType = 'fixed_window';
	} else if (wallBinding >= 0.3 && glassLineQuality >= 0.3) {
		windowType = 'fixed_window';
	} else {
		windowType = 'window_candidate_unverified';
	}

	// ── Review flags ──
	if (glassLineQuality < 0.4) reviewFlags.push('glass_line_quality_low');
	// 放宽绑定判定：rectIntersects OR 80mm 近邻均视为已绑定（防外墙窗 100% unbound）
	if (!windowIntersectsHost && !windowNearHost) reviewFlags.push('host_wall_unbound');
	if (sizeCompliance < 0.3) reviewFlags.push('size_non_compliant');
	if (curtainWallExclusion < 0.5) reviewFlags.push('curtain_wall_conflict');
	if (confidence < 0.35 && wallBinding < 0.3) reviewFlags.push('possible_false_positive');
	if (windowType === 'window_candidate_unverified') reviewFlags.push('needs_manual_review');

	// ── Removability 从宿主墙推导 ──
	const hostWallRole = hostWall?.wallVerification?.structuralRole;
	let removability: WindowRemovability = 'unknown';
	if (hostWallRole === 'partition_wall' || hostWallRole === 'light_partition') {
		removability = 'frame_adjustable';
	} else if (hostWallRole === 'enclosure_wall') {
		removability = 'replaceable';
	} else if (hostWallRole === 'primary_structural_wall' || hostWallRole === 'shear_wall') {
		removability = 'fixed';
	}
	// 同开口一样，使用 logicalWallId 作为规范 hostWallId
	const hostWallCanonicalIdW = hostWall
		? ((hostWall as TraceElement & { logicalWallId?: string }).logicalWallId ?? hostWall.id)
		: undefined;

	return {
		windowType,
		removability,
		hostWallId: hostWallCanonicalIdW,
		hostWallRole,
		confidence,
		evidence: { glassLineQuality, wallBinding, sizeCompliance, arcPresence, overlapPattern, curtainWallExclusion },
		reviewFlags,
	};
};

// ═══════════════════════════════════════════════════════════════════════
// ─── Curtain Wall Verification：幕墙类型验证 + 4 维评分 ──────────────
// ═══════════════════════════════════════════════════════════════════════

const verifyAndClassifyCurtainWall = (
	cwElement: TraceElement,
	segments: TraceSegment[],
	allWalls: TraceElement[],
	mmPerNormalized: number
): CurtainWallVerification => {
	const isHoriz = cwElement.w >= cwElement.h;
	const spanMm = (cwElement.widthMm ?? Math.max(cwElement.w, cwElement.h) * mmPerNormalized);
	const reviewFlags: CurtainWallReviewFlag[] = [];
	const mullionMinNorm = 600 / mmPerNormalized;
	const mullionMaxNorm = 1800 / mmPerNormalized;

	// 1) envelopeContinuity：玻璃线覆盖幕墙跨度的连续程度
	const cwStart = isHoriz ? cwElement.x : cwElement.y;
	const cwEnd = isHoriz ? cwElement.x + cwElement.w : cwElement.y + cwElement.h;
	const cwTrack = isHoriz ? cwElement.y + cwElement.h / 2 : cwElement.x + cwElement.w / 2;
	const coveringLines = segments.filter((s) => {
		if (s.pathKind === 'curve' || s.pathKind === 'rect' || s.pathKind === 'filledRect') return false;
		if (s.dashPattern && s.dashPattern !== 'solid') return false;
		const seg = orthogonalizeSegment(s);
		if (isHorizontal(seg) !== isHoriz) return false;
		const sMid = isHoriz ? seg.y1 : seg.x1;
		if (Math.abs(sMid - cwTrack) > 0.012) return false;
		const sStart = isHoriz ? Math.min(seg.x1, seg.x2) : Math.min(seg.y1, seg.y2);
		const sEnd = isHoriz ? Math.max(seg.x1, seg.x2) : Math.max(seg.y1, seg.y2);
		return sEnd >= cwStart && sStart <= cwEnd;
	});
	const totalCoverage = coveringLines.reduce((sum, s) => {
		const seg = orthogonalizeSegment(s);
		const sStart = Math.max(cwStart, isHoriz ? Math.min(seg.x1, seg.x2) : Math.min(seg.y1, seg.y2));
		const sEnd = Math.min(cwEnd, isHoriz ? Math.max(seg.x1, seg.x2) : Math.max(seg.y1, seg.y2));
		return sum + Math.max(0, sEnd - sStart);
	}, 0);
	const cwSpan = cwEnd - cwStart;
	const envelopeContinuity = cwSpan > 0 ? Math.min(1, totalCoverage / cwSpan) : 0;

	// 2) mullionRepetition：垂直方向竖挺的等间距重复
	const perpSegments = segments.filter((s) => {
		if (s.pathKind === 'curve' || s.pathKind === 'rect' || s.pathKind === 'filledRect') return false;
		const seg = orthogonalizeSegment(s);
		if (isHorizontal(seg) === isHoriz) return false;
		const sCenter = isHoriz ? (seg.x1 + seg.x2) / 2 : (seg.y1 + seg.y2) / 2;
		const sPerp = isHoriz ? (seg.y1 + seg.y2) / 2 : (seg.x1 + seg.x2) / 2;
		return sCenter >= cwStart && sCenter <= cwEnd && Math.abs(sPerp - cwTrack) <= 0.015;
	});
	let mullionRepetition = 0;
	if (perpSegments.length >= 2) {
		const positions = perpSegments.map((s) => {
			const seg = orthogonalizeSegment(s);
			return isHoriz ? (seg.x1 + seg.x2) / 2 : (seg.y1 + seg.y2) / 2;
		}).sort((a, b) => a - b);
		const gaps = positions.slice(1).map((p, i) => p - positions[i]);
		const validGaps = gaps.filter((g) => g >= mullionMinNorm && g <= mullionMaxNorm);
		mullionRepetition = gaps.length > 0 ? Math.min(1, validGaps.length / gaps.length) : 0;
	}

	// 3) hostWallIndependence：该区域无厚墙覆盖程度
	const overlappingWalls = allWalls.filter((wall) => rectIntersects(cwElement, wall));
	const wallCoverageRatio = overlappingWalls.reduce((sum, wall) => {
		const oStart = Math.max(cwStart, isHoriz ? wall.x : wall.y);
		const oEnd = Math.min(cwEnd, isHoriz ? wall.x + wall.w : wall.y + wall.h);
		return sum + Math.max(0, oEnd - oStart);
	}, 0) / (cwSpan || 1);
	const hostWallIndependence = Math.max(0, 1 - wallCoverageRatio);

	// 4) spanWidth：跨度宽度评分
	const spanWidth = spanMm >= 6000 ? 1.0 : spanMm >= 4000 ? 0.7 : spanMm >= 3000 ? 0.5 : 0.2;

	// ── 置信度 ──
	const confidence = Math.min(0.90,
		envelopeContinuity * 0.25
		+ mullionRepetition * 0.25
		+ hostWallIndependence * 0.30
		+ spanWidth * 0.20);

	// ── 类型判定 ──
	let curtainWallType: CurtainWallType;
	if (mullionRepetition >= 0.5 && envelopeContinuity >= 0.4) {
		curtainWallType = 'frame_curtain_wall';
	} else if (envelopeContinuity >= 0.6 && mullionRepetition < 0.3 && spanWidth >= 0.5) {
		curtainWallType = 'full_glass_curtain_wall';
	} else {
		curtainWallType = 'curtain_wall_candidate_unverified';
	}

	// ── Review flags ──
	if (mullionRepetition < 0.3) reviewFlags.push('low_repetition');
	if (spanWidth < 0.5) reviewFlags.push('narrow_span');
	if (hostWallIndependence < 0.5) reviewFlags.push('host_wall_ambiguous');
	if (curtainWallType === 'curtain_wall_candidate_unverified') reviewFlags.push('needs_manual_review');

	return {
		curtainWallType,
		confidence,
		hasOperablePanels: false, // v1 暂不检测可开启扇
		evidence: { envelopeContinuity, mullionRepetition, hostWallIndependence, spanWidth },
		reviewFlags,
	};
};

const runOpeningVerificationPipeline = (
	doorElements: TraceElement[],
	wallGraph: WallGraphDraft,
	wallGaps: WallGap[],
	segments: TraceSegment[],
	allWalls: TraceElement[],
	mmPerNormalized: number
): { doors: TraceElement[]; reviewIssues: ReviewIssue[] } => {
	const reviewIssues: ReviewIssue[] = [];
	const dashedSegments = segments.filter((s) => s.dashPattern === 'dashed' && s.pathKind !== 'curve');

	for (const door of doorElements) {
		door.openingVerification = verifyAndClassifyOpening(door, wallGraph, wallGaps, dashedSegments, allWalls, mmPerNormalized);
	}

	// 开口类统计级评审问题
	const unverified = doorElements.filter((d) => d.openingVerification?.openingType === 'opening_candidate_unverified');
	if (unverified.length > doorElements.length * 0.5 && doorElements.length >= 4) {
		reviewIssues.push({
			id: 'review-opening-unverified-high',
			type: 'opening_type_unresolved',
			severity: 'warning',
			message: `超半数开口(${unverified.length}/${doorElements.length})未通过类型验证。`,
			targetIds: unverified.map((d) => d.id),
		});
	}

	const unbound = doorElements.filter((d) => !d.openingVerification?.hostWallId);
	if (unbound.length > doorElements.length * 0.4 && doorElements.length >= 3) {
		reviewIssues.push({
			id: 'review-opening-unbound-high',
			type: 'opening_host_unbound',
			severity: 'warning',
			message: `${unbound.length} 个开口未绑定到宿主墙。`,
			targetIds: unbound.map((d) => d.id),
		});
	}

	const falsePositiveSuspect = doorElements.filter((d) => {
		const ev = d.openingVerification;
		return ev && ev.confidence < 0.35 && ev.evidence.wallBinding < 0.3;
	});
	if (falsePositiveSuspect.length > 0) {
		falsePositiveSuspect.forEach((d) => {
			d.openingVerification!.reviewFlags.push('possible_false_positive');
		});
		reviewIssues.push({
			id: 'review-opening-false-positive',
			type: 'opening_false_positive',
			severity: 'info',
			message: `${falsePositiveSuspect.length} 个开口疑似误判（低置信度 + 弱墙绑定）。`,
			targetIds: falsePositiveSuspect.map((d) => d.id),
		});
	}

	return { doors: doorElements, reviewIssues };
};

// ═══════════════════════════════════════════════════════════════════════
// ─── Window Verification Pipeline ─────────────────────────────────────
// ═══════════════════════════════════════════════════════════════════════

const runWindowVerificationPipeline = (
	windowElements: TraceElement[],
	segments: TraceSegment[],
	allWalls: TraceElement[],
	curtainWallZones: TraceElement[],
	mmPerNormalized: number
): { windows: TraceElement[]; reviewIssues: ReviewIssue[] } => {
	const reviewIssues: ReviewIssue[] = [];

	for (const win of windowElements) {
		win.windowVerification = verifyAndClassifyWindow(win, segments, allWalls, curtainWallZones, mmPerNormalized);
	}

	const unverified = windowElements.filter((w) => w.windowVerification?.windowType === 'window_candidate_unverified');
	if (unverified.length > windowElements.length * 0.5 && windowElements.length >= 4) {
		reviewIssues.push({
			id: 'review-window-unverified-high',
			type: 'window_type_unresolved',
			severity: 'warning',
			message: `超半数窗户(${unverified.length}/${windowElements.length})未通过类型验证。`,
			targetIds: unverified.map((w) => w.id),
		});
	}

	const unbound = windowElements.filter((w) => !w.windowVerification?.hostWallId);
	if (unbound.length > windowElements.length * 0.4 && windowElements.length >= 3) {
		reviewIssues.push({
			id: 'review-window-unbound-high',
			type: 'window_host_unbound',
			severity: 'warning',
			message: `${unbound.length} 个窗户未绑定到宿主墙。`,
			targetIds: unbound.map((w) => w.id),
		});
	}

	const conflict = windowElements.filter((w) => w.windowVerification?.reviewFlags.includes('curtain_wall_conflict'));
	if (conflict.length > 0) {
		reviewIssues.push({
			id: 'review-window-curtain-wall-conflict',
			type: 'window_curtain_wall_conflict',
			severity: 'info',
			message: `${conflict.length} 个窗户与幕墙区域存在重叠。`,
			targetIds: conflict.map((w) => w.id),
		});
	}

	const falsePositive = windowElements.filter((w) => {
		const ev = w.windowVerification;
		return ev && ev.confidence < 0.35 && ev.evidence.wallBinding < 0.3;
	});
	if (falsePositive.length > 0) {
		falsePositive.forEach((w) => { w.windowVerification!.reviewFlags.push('possible_false_positive'); });
		reviewIssues.push({
			id: 'review-window-false-positive',
			type: 'window_false_positive',
			severity: 'info',
			message: `${falsePositive.length} 个窗户疑似误判（低置信度 + 弱墙绑定）。`,
			targetIds: falsePositive.map((w) => w.id),
		});
	}

	return { windows: windowElements, reviewIssues };
};

// ═══════════════════════════════════════════════════════════════════════
// ─── Curtain Wall Verification Pipeline ───────────────────────────────
// ═══════════════════════════════════════════════════════════════════════

const runCurtainWallVerificationPipeline = (
	curtainWallElements: TraceElement[],
	segments: TraceSegment[],
	allWalls: TraceElement[],
	mmPerNormalized: number
): { curtainWalls: TraceElement[]; reviewIssues: ReviewIssue[] } => {
	const reviewIssues: ReviewIssue[] = [];

	for (const cw of curtainWallElements) {
		cw.curtainWallVerification = verifyAndClassifyCurtainWall(cw, segments, allWalls, mmPerNormalized);
	}

	const unverified = curtainWallElements.filter((c) => c.curtainWallVerification?.curtainWallType === 'curtain_wall_candidate_unverified');
	if (unverified.length > curtainWallElements.length * 0.5 && curtainWallElements.length >= 2) {
		reviewIssues.push({
			id: 'review-curtain-wall-unverified-high',
			type: 'curtain_wall_type_unresolved',
			severity: 'warning',
			message: `超半数幕墙(${unverified.length}/${curtainWallElements.length})未通过类型验证。`,
			targetIds: unverified.map((c) => c.id),
		});
	}

	const lowConf = curtainWallElements.filter((c) => (c.curtainWallVerification?.confidence ?? 0) < 0.35);
	if (lowConf.length > 0) {
		reviewIssues.push({
			id: 'review-curtain-wall-low-confidence',
			type: 'curtain_wall_low_confidence',
			severity: 'info',
			message: `${lowConf.length} 段幕墙置信度偏低，建议人工复核。`,
			targetIds: lowConf.map((c) => c.id),
		});
	}

	return { curtainWalls: curtainWallElements, reviewIssues };
};

// ═══════════════════════════════════════════════════════════════════════
// ─── Zone Verification：空间区域验证（电梯/楼梯/管井/设备间） ──────────
// ═══════════════════════════════════════════════════════════════════════

/** 检测空间内 X 对角线交叉（电梯井底层表达） */
const detectDiagonalCrossEvidence = (
	space: TraceElement,
	segments: TraceSegment[]
): number => {
	const pad = 0.005;
	const sx = space.x - pad;
	const sy = space.y - pad;
	const ex = space.x + space.w + pad;
	const ey = space.y + space.h + pad;
	const inside = segments.filter((s) => {
		if (s.pathKind === 'rect' || s.pathKind === 'filledRect') return false;
		const mx = (s.x1 + s.x2) / 2;
		const my = (s.y1 + s.y2) / 2;
		return mx >= sx && mx <= ex && my >= sy && my <= ey;
	});
	// 找近似对角线：起止点接近两个对角
	let hasDiag1 = false;
	let hasDiag2 = false;
	const tol = Math.max(space.w, space.h) * 0.25;
	for (const seg of inside) {
		const dx1 = Math.abs(seg.x1 - space.x) + Math.abs(seg.y1 - space.y);
		const dx2 = Math.abs(seg.x2 - (space.x + space.w)) + Math.abs(seg.y2 - (space.y + space.h));
		const dx3 = Math.abs(seg.x1 - (space.x + space.w)) + Math.abs(seg.y1 - space.y);
		const dx4 = Math.abs(seg.x2 - space.x) + Math.abs(seg.y2 - (space.y + space.h));
		if ((dx1 < tol && dx2 < tol) || (dx2 < tol && dx1 < tol)) hasDiag1 = true;
		if ((dx3 < tol && dx4 < tol) || (dx4 < tol && dx3 < tol)) hasDiag2 = true;
	}
	if (hasDiag1 && hasDiag2) return 0.95;
	if (hasDiag1 || hasDiag2) return 0.55;
	// 退化：检测多条与对角方向一致的非正交线段
	const diagAngleLines = inside.filter((s) => {
		const dx = Math.abs(s.x2 - s.x1);
		const dy = Math.abs(s.y2 - s.y1);
		return dx > 0.005 && dy > 0.005 && Math.abs(dx - dy) < Math.max(dx, dy) * 0.5;
	});
	return diagAngleLines.length >= 3 ? 0.4 : diagAngleLines.length >= 1 ? 0.2 : 0;
};

/** 检测空间内等距平行短线（楼梯踏步） */
const detectStepLineEvidence = (
	space: TraceElement,
	segments: TraceSegment[],
	mmPerNormalized: number
): { stepLinePattern: number; foldbackPresence: number; arrowPresence: number } => {
	const pad = 0.003;
	const sx = space.x - pad;
	const sy = space.y - pad;
	const ex = space.x + space.w + pad;
	const ey = space.y + space.h + pad;
	const inside = segments.filter((s) => {
		if (s.pathKind === 'curve' || s.pathKind === 'rect' || s.pathKind === 'filledRect') return false;
		const mx = (s.x1 + s.x2) / 2;
		const my = (s.y1 + s.y2) / 2;
		return mx >= sx && mx <= ex && my >= sy && my <= ey;
	});

	// 踏步检测：找水平或垂直短线的等间距序列
	const stepMaxMm = 350;
	const stepMinMm = 180;
	const stepMaxNorm = stepMaxMm / mmPerNormalized;
	const stepMinNorm = stepMinMm / mmPerNormalized;
	const horizShort = inside.filter((s) => {
		const seg = orthogonalizeSegment(s);
		const len = Math.abs(seg.x2 - seg.x1);
		return isHorizontal(seg) && len >= stepMinNorm && len <= space.w * 0.9;
	});
	const vertShort = inside.filter((s) => {
		const seg = orthogonalizeSegment(s);
		const len = Math.abs(seg.y2 - seg.y1);
		return !isHorizontal(seg) && len >= stepMinNorm && len <= space.h * 0.9;
	});

	const evaluateStepSequence = (lines: TraceSegment[], useY: boolean): number => {
		if (lines.length < 3) return 0;
		const tracks = lines.map((s) => useY ? (s.y1 + s.y2) / 2 : (s.x1 + s.x2) / 2).sort((a, b) => a - b);
		const gaps = tracks.slice(1).map((t, i) => t - tracks[i]);
		const validGaps = gaps.filter((g) => g >= stepMinNorm && g <= stepMaxNorm);
		if (validGaps.length < 2) return 0;
		const medianGap = [...validGaps].sort((a, b) => a - b)[Math.floor(validGaps.length / 2)];
		const consistent = validGaps.filter((g) => Math.abs(g - medianGap) < medianGap * 0.4).length;
		return Math.min(1, consistent / Math.max(3, gaps.length));
	};

	const horizStep = evaluateStepSequence(horizShort, true);
	const vertStep = evaluateStepSequence(vertShort, false);
	const stepLinePattern = Math.max(horizStep, vertStep);

	// 折返检测：空间内找U形布局的双组楼梯
	const midX = space.x + space.w / 2;
	const midY = space.y + space.h / 2;
	const leftSteps = horizShort.filter((s) => (s.x1 + s.x2) / 2 < midX);
	const rightSteps = horizShort.filter((s) => (s.x1 + s.x2) / 2 >= midX);
	const topSteps = vertShort.filter((s) => (s.y1 + s.y2) / 2 < midY);
	const bottomSteps = vertShort.filter((s) => (s.y1 + s.y2) / 2 >= midY);
	const foldbackPresence = (leftSteps.length >= 3 && rightSteps.length >= 3) || (topSteps.length >= 3 && bottomSteps.length >= 3) ? 0.8 : 0;

	// 箭头检测：方向指示（简化：检测短斜线对）
	const arrowPresence = inside.some((s) => {
		const dx = Math.abs(s.x2 - s.x1);
		const dy = Math.abs(s.y2 - s.y1);
		const len = Math.hypot(dx, dy);
		return len > 0.003 && len < 0.02 && dx > 0.001 && dy > 0.001;
	}) ? 0.4 : 0;

	return { stepLinePattern, foldbackPresence, arrowPresence };
};

/** 电梯区域验证 */
const verifyAndClassifyZone_Elevator = (
	space: TraceElement,
	segments: TraceSegment[],
	allWalls: TraceElement[],
	mmPerNormalized: number,
	textLabel?: string
): ZoneVerification => {
	const reviewFlags: ZoneReviewFlag[] = [];
	const areaSqm = space.areaSqm ?? 0;
	const widthMm = space.widthMm ?? space.w * mmPerNormalized;
	const depthMm = space.depthMm ?? space.h * mmPerNormalized;

	// 1) diagonalCross
	const diagonalCross = detectDiagonalCrossEvidence(space, segments);

	// 2) shaftEnclosure：四周墙体围合程度
	const wallBounds = allWalls.filter((w) => rectIntersects(space, w));
	const shaftEnclosure = Math.min(1, wallBounds.length >= 4 ? 0.9 : wallBounds.length >= 3 ? 0.65 : wallBounds.length >= 2 ? 0.35 : 0.1);

	// 3) sizeCompliance：客梯 1.4-3.0m²，货梯 2.5-8.0m²
	const isFreight = textLabel ? /货梯/.test(textLabel) : false;
	const sizeCompliance = isFreight
		? (areaSqm >= 2.5 && areaSqm <= 8.0 ? 0.9 : areaSqm >= 1.5 && areaSqm <= 12.0 ? 0.5 : 0.1)
		: (areaSqm >= 1.4 && areaSqm <= 3.0 ? 0.9 : areaSqm >= 0.8 && areaSqm <= 5.0 ? 0.5 : 0.1);

	// 4) textBinding
	const textBinding = textLabel ? (/电梯|客梯|货梯/.test(textLabel) ? 0.95 : 0.3) : 0;

	const confidence = Math.min(0.95,
		diagonalCross * 0.35 + shaftEnclosure * 0.20 + sizeCompliance * 0.20 + textBinding * 0.25);

	const zoneType: ZoneType = isFreight ? 'freight_elevator' : 'elevator';

	if (diagonalCross < 0.4) reviewFlags.push('diagonal_cross_ambiguous');
	if (sizeCompliance < 0.3) reviewFlags.push('size_non_compliant');
	if (textBinding < 0.3) reviewFlags.push('text_binding_weak');
	if (shaftEnclosure < 0.5) reviewFlags.push('enclosure_incomplete');
	if (confidence < 0.35) reviewFlags.push('possible_false_positive');

	return {
		zoneType,
		removability: 'hard_fixed',
		confidence,
		evidence: { diagonalCross, shaftEnclosure, sizeCompliance, textBinding },
		textLabel,
		reviewFlags,
	};
};

/** 楼梯区域验证 */
const verifyAndClassifyZone_Staircase = (
	space: TraceElement,
	segments: TraceSegment[],
	allWalls: TraceElement[],
	mmPerNormalized: number,
	textLabel?: string
): ZoneVerification => {
	const reviewFlags: ZoneReviewFlag[] = [];
	const areaSqm = space.areaSqm ?? 0;

	// 检测踏步/折返/箭头
	const { stepLinePattern, foldbackPresence, arrowPresence } = detectStepLineEvidence(space, segments, mmPerNormalized);

	// sizeCompliance：楼梯间 4-30m²
	const sizeCompliance = areaSqm >= 4 && areaSqm <= 30
		? (areaSqm >= 6 && areaSqm <= 20 ? 0.9 : 0.6)
		: areaSqm >= 2 && areaSqm <= 40 ? 0.3 : 0.05;

	// textBinding
	const textBinding = textLabel ? (/消防楼梯|防烟楼梯|疏散楼梯/.test(textLabel) ? 0.98 : /楼梯/.test(textLabel) ? 0.85 : 0.2) : 0;

	const confidence = Math.min(0.95,
		stepLinePattern * 0.30 + foldbackPresence * 0.10 + arrowPresence * 0.05
		+ sizeCompliance * 0.20 + textBinding * 0.25 + 0.10);

	// 楼梯来源分类
	let stairOrigin: StairOrigin = 'unknown';
	let zoneType: ZoneType = 'building_staircase';
	if (textLabel && /消防楼梯|防烟楼梯|疏散楼梯/.test(textLabel)) {
		stairOrigin = 'fire_stair';
		zoneType = 'fire_staircase';
	} else if (textLabel && /楼梯间/.test(textLabel)) {
		stairOrigin = 'architectural_stair';
		zoneType = 'building_staircase';
	} else if (areaSqm < 5 && !foldbackPresence) {
		stairOrigin = 'secondary_fitout_stair';
		zoneType = 'interior_staircase';
	} else {
		stairOrigin = 'architectural_stair';
	}

	// removability
	let removability: ZoneRemovability = 'constrained';
	if (stairOrigin === 'fire_stair') removability = 'hard_fixed';
	else if (stairOrigin === 'secondary_fitout_stair') removability = 'interior_wrappable';

	if (stepLinePattern < 0.3) reviewFlags.push('step_pattern_weak');
	if (sizeCompliance < 0.3) reviewFlags.push('size_non_compliant');
	if (textBinding < 0.3) reviewFlags.push('text_binding_weak');
	if (confidence < 0.35) reviewFlags.push('possible_false_positive');

	return {
		zoneType,
		stairOrigin,
		removability,
		confidence,
		evidence: { stepLinePattern, foldbackPresence, arrowPresence, sizeCompliance, textBinding },
		textLabel,
		reviewFlags,
	};
};

/** 管井区域验证（面积 0.2-4m²，高围合） */
const verifyAndClassifyZone_Shaft = (
	space: TraceElement,
	allWalls: TraceElement[],
	mmPerNormalized: number,
	textLabel?: string
): ZoneVerification => {
	const reviewFlags: ZoneReviewFlag[] = [];
	const areaSqm = space.areaSqm ?? 0;

	// sizeCompliance：管井 0.2-4m²
	const sizeCompliance = areaSqm >= 0.2 && areaSqm <= 4.0
		? (areaSqm >= 0.3 && areaSqm <= 2.5 ? 0.9 : 0.6)
		: areaSqm >= 0.1 && areaSqm <= 6.0 ? 0.3 : 0.05;

	// wallEnclosure
	const wallBounds = allWalls.filter((w) => rectIntersects(space, w));
	const wallEnclosure = Math.min(1, wallBounds.length >= 4 ? 0.95 : wallBounds.length >= 3 ? 0.7 : wallBounds.length >= 2 ? 0.4 : 0.1);

	// textBinding → 管井子类型
	let zoneType: ZoneType = 'general_shaft';
	const textBinding = textLabel ? 0.9 : 0;
	if (textLabel) {
		if (/水井|给水|排水/.test(textLabel)) zoneType = 'plumbing_shaft';
		else if (/风井/.test(textLabel)) zoneType = 'ventilation_shaft';
		else if (/强电|弱电|电气/.test(textLabel)) zoneType = 'electrical_shaft';
		else if (/管井|管道/.test(textLabel)) zoneType = 'general_shaft';
	}

	const confidence = Math.min(0.90,
		sizeCompliance * 0.35 + wallEnclosure * 0.35 + textBinding * 0.30);

	if (sizeCompliance < 0.3) reviewFlags.push('size_non_compliant');
	if (wallEnclosure < 0.5) reviewFlags.push('enclosure_incomplete');
	if (textBinding < 0.3) reviewFlags.push('text_binding_weak');
	if (confidence < 0.35) reviewFlags.push('possible_false_positive');

	return {
		zoneType,
		removability: 'constrained',
		confidence,
		evidence: { sizeCompliance, textBinding, wallEnclosure },
		textLabel,
		reviewFlags,
	};
};

/** 设备间区域验证（面积 4-50m²） */
const verifyAndClassifyZone_EquipmentRoom = (
	space: TraceElement,
	allWalls: TraceElement[],
	mmPerNormalized: number,
	textLabel?: string
): ZoneVerification => {
	const reviewFlags: ZoneReviewFlag[] = [];
	const areaSqm = space.areaSqm ?? 0;

	// sizeCompliance：设备间 4-50m²
	const sizeCompliance = areaSqm >= 4 && areaSqm <= 50
		? (areaSqm >= 6 && areaSqm <= 30 ? 0.9 : 0.6)
		: areaSqm >= 2 && areaSqm <= 80 ? 0.3 : 0.05;

	// wallEnclosure
	const wallBounds = allWalls.filter((w) => rectIntersects(space, w));
	const wallEnclosure = Math.min(1, wallBounds.length >= 4 ? 0.9 : wallBounds.length >= 3 ? 0.6 : wallBounds.length >= 2 ? 0.3 : 0.1);

	// textBinding → 设备间子类型
	let zoneType: ZoneType = 'general_equipment_room';
	const textBinding = textLabel ? 0.88 : 0;
	if (textLabel) {
		if (/配电|强电间|弱电间/.test(textLabel)) zoneType = 'electrical_room';
		else if (/机房|水泵/.test(textLabel)) zoneType = 'mechanical_room';
	}

	const confidence = Math.min(0.88,
		sizeCompliance * 0.30 + wallEnclosure * 0.30 + textBinding * 0.40);

	if (sizeCompliance < 0.3) reviewFlags.push('size_non_compliant');
	if (wallEnclosure < 0.5) reviewFlags.push('enclosure_incomplete');
	if (textBinding < 0.3) reviewFlags.push('text_binding_weak');
	if (confidence < 0.35) reviewFlags.push('possible_false_positive');

	return {
		zoneType,
		removability: 'adjustable',
		confidence,
		evidence: { sizeCompliance, textBinding, wallEnclosure },
		textLabel,
		reviewFlags,
	};
};

// ─── 阳台区域验证（5 维：textBinding, exteriorWallProximity, sizeCompliance, partialEnclosure, openingAttachment） ──
const verifyAndClassifyZone_Balcony = (
	space: TraceElement,
	allWalls: TraceElement[],
	mmPerNormalized: number,
	textLabel?: string
): ZoneVerification => {
	const reviewFlags: ZoneReviewFlag[] = [];
	const areaSqm = space.areaSqm ?? 0;

	// textBinding
	const textBinding = textLabel ? 0.90 : 0;

	// sizeCompliance：阳台 2-15m²（典型 3-8m²）
	const sizeCompliance = areaSqm >= 2 && areaSqm <= 15
		? (areaSqm >= 3 && areaSqm <= 8 ? 0.90 : 0.60)
		: areaSqm >= 1 && areaSqm <= 25 ? 0.30 : 0.05;

	// exteriorWallProximity：至少 1 面外墙紧邻
	const wallBounds = allWalls.filter((w) => rectIntersects(space, w));
	const enclosureWallBounds = wallBounds.filter((w) => w.wallVerification?.structuralRole === 'enclosure_wall');
	const exteriorWallProximity = enclosureWallBounds.length >= 1 ? Math.min(1, 0.5 + enclosureWallBounds.length * 0.2) : 0.10;

	// partialEnclosure：阳台通常 3 面墙（含 1 外墙）+ 1 面开放或护栏
	const parapetOrRailing = wallBounds.filter((w) => w.wallVerification?.structuralRole === 'parapet_wall' || w.wallVerification?.structuralRole === 'railing_line');
	const totalEnclosure = wallBounds.length + parapetOrRailing.length * 0.5;
	const partialEnclosure = totalEnclosure >= 3 ? 0.85 : totalEnclosure >= 2 ? 0.55 : 0.20;

	// openingAttachment：阳台应有门/窗通向室内（通过开口检测判断，v1 简化为外墙上是否有间隙）
	const openingAttachment = enclosureWallBounds.length >= 1 && wallBounds.length >= 2 ? 0.70 : 0.30;

	// 子类型判定：有护栏 → open_balcony，否则 → balcony（封闭阳台）
	let zoneType: ZoneType = 'balcony';
	if (textLabel && /开放|半开放/.test(textLabel)) {
		zoneType = 'open_balcony';
	} else if (parapetOrRailing.length > 0 && wallBounds.length <= 3) {
		zoneType = 'open_balcony';
	}

	const confidence = Math.min(0.88,
		textBinding * 0.25 + exteriorWallProximity * 0.25 + sizeCompliance * 0.20 + partialEnclosure * 0.15 + openingAttachment * 0.15);

	if (sizeCompliance < 0.3) reviewFlags.push('size_non_compliant');
	if (partialEnclosure < 0.4) reviewFlags.push('balcony_partial_enclosure_weak');
	if (exteriorWallProximity < 0.3) reviewFlags.push('possible_false_positive');
	if (textBinding < 0.3) reviewFlags.push('text_binding_weak');

	return {
		zoneType,
		removability: 'adjustable',
		confidence,
		evidence: { sizeCompliance, textBinding, exteriorWallProximity, partialEnclosure, openingAttachment },
		textLabel,
		reviewFlags,
	};
};

// ─── 露台区域验证（5 维：textBinding, exteriorWallProximity, sizeCompliance, partialEnclosure, openingAttachment） ──
const verifyAndClassifyZone_Terrace = (
	space: TraceElement,
	allWalls: TraceElement[],
	mmPerNormalized: number,
	textLabel?: string
): ZoneVerification => {
	const reviewFlags: ZoneReviewFlag[] = [];
	const areaSqm = space.areaSqm ?? 0;

	// textBinding
	const textBinding = textLabel ? 0.90 : 0;

	// sizeCompliance：露台 8-100m²（典型 15-50m²）；小于 8m² 更像阳台
	const sizeCompliance = areaSqm >= 8 && areaSqm <= 100
		? (areaSqm >= 15 && areaSqm <= 50 ? 0.90 : 0.60)
		: areaSqm >= 4 && areaSqm <= 200 ? 0.30 : 0.05;

	// exteriorWallProximity
	const wallBounds = allWalls.filter((w) => rectIntersects(space, w));
	const enclosureWallBounds = wallBounds.filter((w) => w.wallVerification?.structuralRole === 'enclosure_wall');
	const exteriorWallProximity = enclosureWallBounds.length >= 1 ? Math.min(1, 0.4 + enclosureWallBounds.length * 0.2) : 0.10;

	// partialEnclosure：露台可以多面开放
	const partialEnclosure = wallBounds.length >= 2 ? 0.70 : wallBounds.length >= 1 ? 0.45 : 0.15;

	// openingAttachment
	const openingAttachment = enclosureWallBounds.length >= 1 ? 0.65 : 0.25;

	const confidence = Math.min(0.85,
		textBinding * 0.30 + sizeCompliance * 0.25 + exteriorWallProximity * 0.20 + partialEnclosure * 0.15 + openingAttachment * 0.10);

	if (sizeCompliance < 0.3) reviewFlags.push('size_non_compliant');
	if (areaSqm < 10) reviewFlags.push('terrace_size_ambiguous');
	if (exteriorWallProximity < 0.3) reviewFlags.push('possible_false_positive');
	if (textBinding < 0.3) reviewFlags.push('text_binding_weak');

	return {
		zoneType: 'terrace',
		removability: 'adjustable',
		confidence,
		evidence: { sizeCompliance, textBinding, exteriorWallProximity, partialEnclosure, openingAttachment },
		textLabel,
		reviewFlags,
	};
};

// ═══════════════════════════════════════════════════════════════════════
// ─── Zone Verification Pipeline ───────────────────────────────────────
// ═══════════════════════════════════════════════════════════════════════

const resolveZoneTypeFromLabel = (label: string): ZoneType | null => {
	const cleaned = label.replace(/[\s\d#号]/g, '');
	for (const [key, value] of Object.entries(ZONE_TEXT_MAP).sort((a, b) => b[0].length - a[0].length)) {
		if (cleaned.includes(key)) return value;
	}
	return null;
};

const runZoneVerificationPipeline = (
	spaceElements: TraceElement[],
	segments: TraceSegment[],
	allWalls: TraceElement[],
	classifiedTexts: ClassifiedText[],
	mmPerNormalized: number
): { zones: TraceElement[]; reviewIssues: ReviewIssue[]; coreZones: FloorPlanIRCoreZone[] } => {
	const reviewIssues: ReviewIssue[] = [];

	// 1) 文字绑定
	bindTextsToZones(classifiedTexts, spaceElements);

	// 2) 对每个 function_zone 做验证
	for (const space of spaceElements) {
		const hint = resolveZoneTypeFromLabel(space.label);
		const textLabel = space.label !== `闭合房间 ${space.id.split('-').pop()}` && space.label !== `闭合空间 ${space.id.split('-').pop()}`
			? space.label : undefined;
		const areaSqm = space.areaSqm ?? 0;

		if (hint === 'elevator' || hint === 'freight_elevator' || (!hint && detectDiagonalCrossEvidence(space, segments) >= 0.5)) {
			space.zoneVerification = verifyAndClassifyZone_Elevator(space, segments, allWalls, mmPerNormalized, textLabel);
		} else if (hint === 'fire_staircase' || hint === 'building_staircase' || hint === 'interior_staircase') {
			space.zoneVerification = verifyAndClassifyZone_Staircase(space, segments, allWalls, mmPerNormalized, textLabel);
		} else if (!hint && detectStepLineEvidence(space, segments, mmPerNormalized).stepLinePattern >= 0.45) {
			space.zoneVerification = verifyAndClassifyZone_Staircase(space, segments, allWalls, mmPerNormalized, textLabel);
		} else if (hint === 'plumbing_shaft' || hint === 'electrical_shaft' || hint === 'ventilation_shaft' || hint === 'general_shaft') {
			space.zoneVerification = verifyAndClassifyZone_Shaft(space, allWalls, mmPerNormalized, textLabel);
		} else if (!hint && areaSqm > 0 && areaSqm <= 4.0 && allWalls.filter((w) => rectIntersects(space, w)).length >= 3) {
			space.zoneVerification = verifyAndClassifyZone_Shaft(space, allWalls, mmPerNormalized, textLabel);
		} else if (hint === 'electrical_room' || hint === 'mechanical_room' || hint === 'general_equipment_room') {
			space.zoneVerification = verifyAndClassifyZone_EquipmentRoom(space, allWalls, mmPerNormalized, textLabel);
		} else if (hint === 'balcony' || hint === 'open_balcony') {
			space.zoneVerification = verifyAndClassifyZone_Balcony(space, allWalls, mmPerNormalized, textLabel);
		} else if (hint === 'terrace') {
			space.zoneVerification = verifyAndClassifyZone_Terrace(space, allWalls, mmPerNormalized, textLabel);
		} else {
			// 未匹配到特定类型，保持 function_zone 原样
			space.zoneVerification = {
				zoneType: 'zone_candidate_unverified',
				removability: 'unknown',
				confidence: space.confidence,
				evidence: { sizeCompliance: 0.5, textBinding: 0 },
				reviewFlags: [],
			};
		}
	}

	// 3) 统计级评审
	const unverified = spaceElements.filter((s) => s.zoneVerification?.zoneType === 'zone_candidate_unverified');
	if (unverified.length > 0 && spaceElements.length >= 3) {
		reviewIssues.push({
			id: 'review-zone-unverified',
			type: 'zone_type_unresolved',
			severity: 'info',
			message: `${unverified.length} 个空间未识别为特定功能区域。`,
			targetIds: unverified.map((s) => s.id),
		});
	}

	const lowConf = spaceElements.filter((s) => s.zoneVerification && s.zoneVerification.zoneType !== 'zone_candidate_unverified' && s.zoneVerification.confidence < 0.4);
	if (lowConf.length > 0) {
		reviewIssues.push({
			id: 'review-zone-low-confidence',
			type: 'zone_low_confidence',
			severity: 'warning',
			message: `${lowConf.length} 个功能区域置信度偏低。`,
			targetIds: lowConf.map((s) => s.id),
		});
	}

	const elevatorAmbiguous = spaceElements.filter((s) => s.zoneVerification?.zoneType === 'elevator' && s.zoneVerification.reviewFlags.includes('diagonal_cross_ambiguous'));
	if (elevatorAmbiguous.length > 0) {
		reviewIssues.push({
			id: 'review-zone-elevator-ambiguous',
			type: 'zone_elevator_ambiguous',
			severity: 'info',
			message: `${elevatorAmbiguous.length} 个电梯候选 X 对角线证据不明确。`,
			targetIds: elevatorAmbiguous.map((s) => s.id),
		});
	}

	// 阳台/露台评审
	const balconyLowConf = spaceElements.filter((s) => (s.zoneVerification?.zoneType === 'balcony' || s.zoneVerification?.zoneType === 'open_balcony') && (s.zoneVerification?.confidence ?? 0) < 0.40);
	if (balconyLowConf.length > 0) {
		reviewIssues.push({
			id: 'review-zone-balcony-low-confidence',
			type: 'balcony_low_confidence',
			severity: 'info',
			message: `${balconyLowConf.length} 个阳台候选置信度偏低。`,
			targetIds: balconyLowConf.map((s) => s.id),
		});
	}
	const terraceSizeConflict = spaceElements.filter((s) => s.zoneVerification?.zoneType === 'terrace' && s.zoneVerification.reviewFlags.includes('terrace_size_ambiguous'));
	if (terraceSizeConflict.length > 0) {
		reviewIssues.push({
			id: 'review-zone-terrace-size-ambiguous',
			type: 'terrace_vs_balcony_conflict',
			severity: 'info',
			message: `${terraceSizeConflict.length} 个露台面积偏小，可能实为阳台。`,
			targetIds: terraceSizeConflict.map((s) => s.id),
		});
	}

	// 4) 核心筒推断（从电梯出发，8m 半径内聚合相邻核心元素）
	const coreZones = inferCoreZones(spaceElements, mmPerNormalized);
	if (coreZones.length === 0 && spaceElements.some((s) => s.zoneVerification?.zoneType === 'elevator' || s.zoneVerification?.zoneType === 'fire_staircase')) {
		reviewIssues.push({
			id: 'review-core-zone-incomplete',
			type: 'core_zone_incomplete',
			severity: 'info',
			message: '检测到电梯或消防楼梯，但未能形成完整核心筒聚类。',
			targetIds: [],
		});
	}

	return { zones: spaceElements, reviewIssues, coreZones };
};

/** 核心筒推断：从电梯种子扩展 */
const inferCoreZones = (
	spaceElements: TraceElement[],
	mmPerNormalized: number
): FloorPlanIRCoreZone[] => {
	const coreSeeds = spaceElements.filter((s) => {
		const zt = s.zoneVerification?.zoneType;
		return zt === 'elevator' || zt === 'freight_elevator';
	});
	if (coreSeeds.length === 0) return [];

	const radiusNorm = 8000 / mmPerNormalized; // 8m 半径
	const coreTypes: ZoneType[] = ['elevator', 'freight_elevator', 'fire_staircase', 'building_staircase',
		'plumbing_shaft', 'electrical_shaft', 'ventilation_shaft', 'general_shaft',
		'electrical_room', 'mechanical_room', 'general_equipment_room'];
	const used = new Set<string>();
	const result: FloorPlanIRCoreZone[] = [];

	for (const seed of coreSeeds) {
		if (used.has(seed.id)) continue;
		const cx = seed.x + seed.w / 2;
		const cy = seed.y + seed.h / 2;
		const members = spaceElements.filter((s) => {
			if (used.has(s.id)) return false;
			const zt = s.zoneVerification?.zoneType;
			if (!zt || !coreTypes.includes(zt)) return false;
			const sx = s.x + s.w / 2;
			const sy = s.y + s.h / 2;
			return Math.hypot(sx - cx, sy - cy) <= radiusNorm;
		});
		if (members.length < 2) continue;

		members.forEach((m) => used.add(m.id));
		const xs = members.flatMap((m) => [m.x, m.x + m.w]);
		const ys = members.flatMap((m) => [m.y, m.y + m.h]);
		const minX = Math.min(...xs);
		const minY = Math.min(...ys);
		const maxX = Math.max(...xs);
		const maxY = Math.max(...ys);

		result.push({
			id: `core-zone-${result.length + 1}`,
			seedElementId: seed.id,
			memberIds: members.map((m) => m.id),
			bbox: [
				Math.round(minX * mmPerNormalized),
				Math.round(minY * mmPerNormalized),
				Math.round(maxX * mmPerNormalized),
				Math.round(maxY * mmPerNormalized),
			],
			containsElevator: members.some((m) => m.zoneVerification?.zoneType === 'elevator' || m.zoneVerification?.zoneType === 'freight_elevator'),
			containsFireStair: members.some((m) => m.zoneVerification?.zoneType === 'fire_staircase'),
			confidence: members.reduce((sum, m) => sum + (m.zoneVerification?.confidence ?? 0), 0) / members.length,
		});
	}

	return result;
};

const mapPrimitiveRefBetweenBoxes = (ref: PrimitiveRef, fromBox: TraceRegion, toBox: TraceRegion): PrimitiveRef => {
	const region = clampRegionToUnit(mapRegionBetweenBoxes({
		x: ref.bbox[0],
		y: ref.bbox[1],
		w: ref.bbox[2] - ref.bbox[0],
		h: ref.bbox[3] - ref.bbox[1],
	}, fromBox, toBox));
	return {
		...ref,
		bbox: [region.x, region.y, region.x + region.w, region.y + region.h],
	};
};

const primitiveRefsFromSegments = (segments: TraceSegment[], limit = 120, fromBox?: TraceRegion, toBox?: TraceRegion): PrimitiveRef[] => segments.slice(0, limit).map((segment, index) => {
	const bounds = segmentBounds(segment);
	const ref: PrimitiveRef = {
		id: `primitive-${index + 1}`,
		kind: segment.classification ?? segment.pathKind ?? 'line',
		bbox: [bounds.minX, bounds.minY, bounds.maxX, bounds.maxY],
		confidence: Math.min(0.95, Math.max(0.25, segment.score * 5)),
	};
	return fromBox && toBox ? mapPrimitiveRefBetweenBoxes(ref, fromBox, toBox) : ref;
});

const classifyScopedSegmentsForLayers = (segments: TraceSegment[], dimensions: DimensionMark[]) => {
	const pdfLineWidths = segments.filter((segment) => segment.source === 'pdf' && (segment.lineWidth ?? 0) > 0).map((segment) => segment.lineWidth!);
	const medianLineWidth = pdfLineWidths.length > 4 ? [...pdfLineWidths].sort((a, b) => a - b)[Math.floor(pdfLineWidths.length / 2)] : undefined;
	return segments.map((segment) => ({ ...segment, classification: classifySegment(segment, dimensions, medianLineWidth) }));
};

const primitiveRefsByClassification = (
	segments: TraceSegment[],
	kinds: Array<NonNullable<TraceSegment['classification']>>,
	limit = 60,
	fromBox?: TraceRegion,
	toBox?: TraceRegion
) => primitiveRefsFromSegments(segments.filter((segment) => segment.classification && kinds.includes(segment.classification)), limit, fromBox, toBox);

// ─── Parser Gate ────────────────────────────────────────────────────────────
// 检查原语保真性：如果 PDF 存在填充操作但未产生填充路径对象，判定为保真失败。
// 这是"有声失败"的第一道防线：让后续系统知道柱数据可能丢失，而不是静默输出错误结果。
interface ParserGateInput {
	rawSegments: TraceSegment[];
	/** PDF pathFillSet 大小（填充操作数量）；DXF 传 0 */
	fillOperationCount: number;
	sourceType: 'pdf' | 'dxf';
}

const buildParserGate = ({ rawSegments, fillOperationCount, sourceType }: ParserGateInput): GateResult => {
	const issues: GateIssue[] = [];

	const filledRectCount = rawSegments.filter((s) => s.pathKind === 'filledRect').length;
	const filledPolyCount = rawSegments.filter((s) => s.pathKind === 'filledPolygon').length;
	const totalFilled = filledRectCount + filledPolyCount;

	// 规则1：PDF 有填充操作但一个填充路径都没保留 → Parser 失败
	if (sourceType === 'pdf' && fillOperationCount > 0 && totalFilled === 0) {
		issues.push({
			id: 'parser-filled-path-lost',
			severity: 'error',
			message: `图纸含 ${fillOperationCount} 个填充操作，但 Parser 输出中 filledRect/filledPolygon 均为 0。`
				+ ' 实心柱（FilledClosedPath）可能丢失，后续柱识别将仅靠回退路径（描边矩形重建），准确率大幅下降。'
				+ ' 请检查 flushFillSubPath / paintSolidColorImageMask 的 clip 路径和复合 path 处理逻辑。',
			targetIds: [],
		});
	}

	// 规则2：填充路径数量极少（<3）但填充操作数量多（>10）→ 疑似大量填充路径被静默丢弃
	if (sourceType === 'pdf' && fillOperationCount > 10 && totalFilled < 3) {
		issues.push({
			id: 'parser-filled-path-suspiciously-few',
			severity: 'warning',
			message: `图纸含 ${fillOperationCount} 个填充操作但只保留了 ${totalFilled} 个填充路径对象。`
				+ ' 疑似存在大量嵌套 clip 路径或复合填充路径未被正确解析，建议人工核对柱数量。',
			targetIds: [],
		});
	}

	// 规则3：原语总量过少（PDF解析几乎空）→ 严重解析失败
	const meaningfulSegments = rawSegments.filter((s) =>
		s.pathKind === 'line' || s.pathKind === 'filledRect' || s.pathKind === 'filledPolygon'
	).length;
	if (sourceType === 'pdf' && meaningfulSegments < 10) {
		issues.push({
			id: 'parser-near-empty',
			severity: 'error',
			message: `Parser 输出仅 ${meaningfulSegments} 个有效原语（line+filledRect+filledPolygon）。`
				+ ' 疑似 PDF 解析器未拿到矢量内容（可能是纯图像 PDF 或加密 PDF），所有下游识别结果不可信。',
			targetIds: [],
		});
	}

	const passed = !issues.some((i) => i.severity === 'error');
	return {
		status: passed ? 'passed' : 'failed',
		score: passed ? 1.0 : 0.0,
		issues,
		metrics: {
			fillOperationCount,
			filledRectCount,
			filledPolyCount,
			meaningfulSegmentCount: meaningfulSegments,
		},
	};
};

// ─── Scale Gate ────────────────────────────────────────────────────────────
// 三档比例尺治理：trusted / provisional / unknown
// - trusted：多源一致（OCR + 向量猜测），允许硬尺寸阈值
// - provisional：仅单源，差距可接受，降为软约束模式
// - unknown：无任何可信证据，禁止用mm值过滤大柱/厚墙
export type ScaleConfidenceTier = 'trusted' | 'provisional' | 'unknown';

interface ScaleGateInput {
	scaleEvidenceSource: string;
	scaleEvidenceDimensions: DimensionMark[];
	mmPerNormalized: number;
	prelimMmPerNorm: number;
}

const buildScaleGate = ({ scaleEvidenceSource, scaleEvidenceDimensions, mmPerNormalized, prelimMmPerNorm }: ScaleGateInput): GateResult & { tier: ScaleConfidenceTier } => {
	const issues: GateIssue[] = [];
	let tier: ScaleConfidenceTier;
	const hasExplicitCalibration = scaleEvidenceSource === 'manual'
		|| scaleEvidenceSource === 'roi'
		|| scaleEvidenceSource === 'main_plan'
		|| scaleEvidenceSource === 'main_plan_margin'
		|| scaleEvidenceSource === 'roi_margin';
	const requiresDimensionEvidence = scaleEvidenceSource !== 'manual';

	// 判断置信等级
	if (!hasExplicitCalibration || (requiresDimensionEvidence && scaleEvidenceDimensions.length === 0)) {
		tier = 'unknown';
		issues.push({
			id: 'scale-unknown',
			severity: 'error',
			message: '未完成比例尺校准。当前仅允许在存在明确尺寸证据或手动比例尺时进行识别与编译。'
				+ ` 当前比例尺来源=${scaleEvidenceSource}，mmPerNorm=${Math.round(mmPerNormalized)}。`
				+ ' 请先在前端手动校准比例尺，或提供可识别尺寸标注后再重新编译。',
			targetIds: [],
		});
	} else {
		// OCR来源（roi / main_plan / roi_margin 等）
		// 检查初步估算与最终值的偏差
		const deviation = Math.abs(mmPerNormalized - prelimMmPerNorm) / Math.max(prelimMmPerNorm, 1);
		if (deviation > 0.40) {
			tier = 'provisional';
			issues.push({
				id: 'scale-provisional-high-deviation',
				severity: 'warning',
				message: `比例尺两阶段估算偏差过大（初步=${Math.round(prelimMmPerNorm)}, 最终=${Math.round(mmPerNormalized)}, 偏差=${(deviation * 100).toFixed(1)}%）。`
					+ ' 可能存在多平面并排或尺寸标注误识别，降级为 provisional。',
				targetIds: [],
			});
		} else if (scaleEvidenceDimensions.length < 2) {
			tier = 'provisional';
			issues.push({
				id: 'scale-provisional-single-evidence',
				severity: 'info',
				message: `仅有1个尺寸证据（来源：${scaleEvidenceSource}，mmPerNorm=${Math.round(mmPerNormalized)}）。`
					+ ' 建议获取更多尺寸标注交叉验证后提升为 trusted。',
				targetIds: [],
			});
		} else {
			tier = 'trusted';
		}
	}

	const passed = tier !== 'unknown';
	return {
		status: passed ? 'passed' : 'failed',
		score: tier === 'trusted' ? 1.0 : tier === 'provisional' ? 0.6 : 0.0,
		issues,
		metrics: {
			tier: tier === 'trusted' ? 2 : tier === 'provisional' ? 1 : 0,
			mmPerNormalized: Math.round(mmPerNormalized),
			prelimMmPerNorm: Math.round(prelimMmPerNorm),
			evidenceCount: scaleEvidenceDimensions.length,
		},
		tier,
	};
};

const buildCoordinateConsistencyGate = (elements: TraceElement[]): GateResult => {
	const issues: GateIssue[] = [];
	const missingProvenance = elements.filter((element) => !element.coordinateProvenance);
	const outOfBounds = elements.filter((element) => {
		const bbox = element.coordinateProvenance?.mainPlanBBox ?? regionToBBox(element);
		return bbox.some((value) => !Number.isFinite(value)) ||
			bbox[0] < -0.002 ||
			bbox[1] < -0.002 ||
			bbox[2] > 1.002 ||
			bbox[3] > 1.002 ||
			bbox[2] <= bbox[0] ||
			bbox[3] <= bbox[1];
	});
	const renderDrift = elements.filter((element) => {
		const provenance = element.coordinateProvenance;
		if (!provenance?.renderBBox) return false;
		const expected = regionToBBox(element);
		return provenance.renderBBox.some((value, index) => Math.abs(value - expected[index]) > 0.004);
	});
	if (missingProvenance.length > 0) {
		issues.push({
			id: 'gate-coordinate-provenance-missing',
			severity: 'error',
			message: '部分候选对象缺少坐标来源框，不能升格为正式 FloorPlanIR。',
			targetIds: missingProvenance.map((element) => element.id),
		});
	}
	if (outOfBounds.length > 0) {
		issues.push({
			id: 'gate-coordinate-mainplan-out-of-bounds',
			severity: 'error',
			message: '部分候选对象映射到 mainPlanBox 外或 bbox 无效，存在坐标漂移风险。',
			targetIds: outOfBounds.map((element) => element.id),
		});
	}
	if (renderDrift.length > 0) {
		issues.push({
			id: 'gate-coordinate-render-drift',
			severity: 'error',
			message: '候选对象 render bbox 与 mainPlan bbox 不一致，渲染层和识别层坐标未闭环。',
			targetIds: renderDrift.map((element) => element.id),
		});
	}
	return {
		status: issues.every((issue) => issue.severity !== 'error') ? 'passed' : 'failed',
		score: Math.max(0, Math.min(100, 100 - missingProvenance.length * 8 - outOfBounds.length * 18 - renderDrift.length * 18)),
		issues,
		metrics: {
			total_objects: elements.length,
			missing_provenance: missingProvenance.length,
			out_of_bounds: outOfBounds.length,
			render_drift: renderDrift.length,
		},
	};
};

// ─── CarrierBaselineIR ──────────────────────────────────────────────────────
// 建筑载体基线层（Phase 1 最小版本）
// 只回答6个问题：外轮廓 / 墙脊线 / 结构核 / 核心筒暗区 / 开口锚点 / 不可改边界
// 不输出房间语义，不输出正式柱类型，不输出3D几何
// ─────────────────────────────────────────────────────────────────────────────

interface StructuralKernelRef {
	id: string;
	/** 归一化坐标 bbox */
	bbox: [number, number, number, number];
	/** 原始填充类型 */
	sourceKind: 'filledRect' | 'filledPolygon';
	/** 宽mm，unknown表示比例尺不可信 */
	widthMm: number | 'unknown';
	depthMm: number | 'unknown';
	/** 初步判断 - 可能是：isolated(独立柱) / embedded(嵌墙柱) / perimeter(边带柱) / unknown */
	presumedRole: 'isolated' | 'embedded' | 'perimeter' | 'unknown';
}

interface WallSpineRef {
	id: string;
	/** 归一化线段端点 */
	x1: number; y1: number; x2: number; y2: number;
	/** 方向 */
	orientation: 'horizontal' | 'vertical';
	/** 估计厚度（归一化，0表示未知） */
	thicknessNorm: number;
}

interface CarrierBaselineIR {
	/** 外轮廓（bbox，approximation） */
	outerBoundary?: [number, number, number, number];
	/** 主墙脊线候选列表 */
	wallSpines: WallSpineRef[];
	/** 结构核列表（所有深色填充区，未分类柱型） */
	structuralKernels: StructuralKernelRef[];
	/** 核心筒/楼梯暗区（大面积填充区，非柱） */
	coreZoneHints: Array<{ bbox: [number, number, number, number]; area: number }>;
	/** 开口锚点候选（弧线端点，门洞位置） */
	openingAnchors: Array<{ x: number; y: number; confidence: number }>;
	/** 诊断统计 */
	stats: {
		kernelCount: number;
		wallSpineCount: number;
		columnCandidateCount: number;
		filledRectCount: number;
		filledPolyCount: number;
		scaleConfidence: ScaleConfidenceTier;
	};
}

/**
 * buildCarrierBaselineIR
 * 从原始段和已识别元素构建 CarrierBaselineIR 最小版本。
 * 这是 Phase 1 止血版，目标：让结构底座先站稳。
 */
const buildCarrierBaselineIR = (
	rawSegments: TraceSegment[],
	wallElements: TraceElement[],
	columnCandidates: TraceElement[],
	mmPerNormalized: number,
	scaleConfidence: ScaleConfidenceTier,
): CarrierBaselineIR => {
	// ── 1. 结构核提取（全部填充区，不分类） ─────────────────────────────────
	const filledSegs = rawSegments.filter(
		(s) => s.pathKind === 'filledRect' || s.pathKind === 'filledPolygon'
	);
	const minKernelSide = scaleConfidence === 'unknown'
		? 0.003  // unknown时不能用mm值过滤，用极小相对值
		: Math.max(0.003, 80 / mmPerNormalized); // 80mm物理下限

	const kernels: StructuralKernelRef[] = [];
	const coreZoneHints: CarrierBaselineIR['coreZoneHints'] = [];

	filledSegs.forEach((s, i) => {
		const left = Math.min(s.x1, s.x2);
		const top = Math.min(s.y1, s.y2);
		const w = Math.abs(s.x2 - s.x1);
		const h = Math.abs(s.y2 - s.y1);
		if (w < minKernelSide || h < minKernelSide) return; // 极小噪声排除

		const widthMm = scaleConfidence !== 'unknown' ? Math.round(w * mmPerNormalized) : 'unknown' as const;
		const depthMm = scaleConfidence !== 'unknown' ? Math.round(h * mmPerNormalized) : 'unknown' as const;

		// 大面积填充区 → 核心筒/楼梯暗区（不是柱）
		const maxColumnSide = scaleConfidence !== 'unknown' ? 1800 / mmPerNormalized : 0.10;
		if (w > maxColumnSide || h > maxColumnSide) {
			coreZoneHints.push({ bbox: [left, top, left + w, top + h], area: w * h });
			return;
		}

		// 初步角色判断（粗粒度，仅基于几何）
		let presumedRole: StructuralKernelRef['presumedRole'] = 'unknown';
		const aspect = Math.max(w, h) / Math.max(Math.min(w, h), 1e-9);
		if (aspect <= 2.0) {
			presumedRole = 'isolated'; // 近方形 → 独立柱
		} else if (aspect <= 3.5) {
			presumedRole = 'embedded'; // 细长 → 嵌墙柱或构造柱
		} else {
			presumedRole = 'perimeter'; // 极细长 → 可能是边带柱或墙端加厚
		}

		kernels.push({
			id: `kernel-${i}`,
			bbox: [left, top, left + w, top + h],
			sourceKind: s.pathKind as 'filledRect' | 'filledPolygon',
			widthMm,
			depthMm,
			presumedRole,
		});
	});

	// ── 2. 墙脊线（从已识别的 wall_trace 元素提取） ──────────────────────
	const wallSpines: WallSpineRef[] = wallElements.slice(0, 200).map((w, i) => {
		const horiz = w.w > w.h;
		return {
			id: `spine-${i}`,
			x1: w.x,
			y1: horiz ? w.y + w.h / 2 : w.y,
			x2: horiz ? w.x + w.w : w.x,
			y2: horiz ? w.y + w.h / 2 : w.y + w.h,
			orientation: horiz ? 'horizontal' : 'vertical',
			thicknessNorm: horiz ? w.h : w.w,
		};
	});

	// ── 3. 外轮廓 bbox 估算（所有墙脊线的包络） ─────────────────────────
	let outerBoundary: CarrierBaselineIR['outerBoundary'];
	if (wallSpines.length > 0) {
		const xs = wallSpines.flatMap((s) => [s.x1, s.x2]);
		const ys = wallSpines.flatMap((s) => [s.y1, s.y2]);
		outerBoundary = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
	}

	// ── 4. 开口锚点（弧线的端点集合） ────────────────────────────────────
	const openingAnchors: CarrierBaselineIR['openingAnchors'] = rawSegments
		.filter((s) => s.pathKind === 'curve')
		.slice(0, 100)
		.map((s) => ({ x: (s.x1 + s.x2) / 2, y: (s.y1 + s.y2) / 2, confidence: 0.55 }));

	return {
		outerBoundary,
		wallSpines,
		structuralKernels: kernels,
		coreZoneHints,
		openingAnchors,
		stats: {
			kernelCount: kernels.length,
			wallSpineCount: wallSpines.length,
			columnCandidateCount: columnCandidates.length,
			filledRectCount: rawSegments.filter((s) => s.pathKind === 'filledRect').length,
			filledPolyCount: rawSegments.filter((s) => s.pathKind === 'filledPolygon').length,
			scaleConfidence,
		},
	};
};

const buildCarrierGate = (carrier: CarrierBaselineIR): GateResult => {
	const issues: GateIssue[] = [];
	const { kernelCount, wallSpineCount, columnCandidateCount, scaleConfidence } = carrier.stats;

	if (!carrier.outerBoundary) {
		issues.push({
			id: 'gate-carrier-missing-outer-boundary',
			severity: 'warning',
			message: '载体基线缺少外轮廓包络，后续边界判定将偏保守。',
			targetIds: [],
		});
	}
	if (wallSpineCount < 3 && kernelCount === 0) {
		issues.push({
			id: 'gate-carrier-structure-evidence-too-weak',
			severity: 'error',
			message: '载体结构证据过弱（墙脊线和结构核均不足），建议先回到解析/尺度阶段复核。',
			targetIds: [],
		});
	}
	if (scaleConfidence === 'unknown') {
		issues.push({
			id: 'gate-carrier-scale-unknown',
			severity: 'warning',
			message: '比例尺可信度未知，CarrierBaselineIR 仅可用于相对拓扑分析。',
			targetIds: [],
		});
	}

	const scoreRaw =
		(wallSpineCount >= 6 ? 45 : wallSpineCount >= 3 ? 28 : 10)
		+ (kernelCount >= 1 ? 30 : 0)
		+ (carrier.outerBoundary ? 15 : 0)
		+ (columnCandidateCount >= 2 ? 10 : 0);
	const score = Math.max(0, Math.min(100, scoreRaw));
	const status: GateResult['status'] = issues.some((i) => i.severity === 'error') ? 'failed' : 'passed';

	return {
		status,
		score,
		issues,
		metrics: {
			kernel_count: kernelCount,
			wall_spine_count: wallSpineCount,
			column_candidate_count: columnCandidateCount,
			scale_confidence: scaleConfidence === 'trusted' ? 2 : scaleConfidence === 'provisional' ? 1 : 0,
			has_outer_boundary: carrier.outerBoundary ? 1 : 0,
		},
	};
};

const buildStructureBackboneGate = (
	wallGraph: WallGraphDraft,
	elements: TraceElement[],
	gridPrior: GridPriorOutput | undefined,
	mmPerNormalized: number
): GateResult => {
	const walls = elements.filter((element) => element.kind === 'wall_trace');
	const columns = elements.filter((element) => element.kind === 'column');
	const wallFragmentationScore = walls.length ? wallGraph.fragmentGroups.length / walls.length : 1;
	const danglingWallRate = walls.length ? wallGraph.danglingWallIds.length / walls.length : 1;
	const pairedWallCount = walls.filter((wall) => Math.min(wall.w, wall.h) > 0.006).length;
	const wallPairingRate = walls.length ? pairedWallCount / walls.length : 0;
	const colBindTol = Math.min(0.040, Math.max(0.008, 200 / mmPerNormalized));
	const attachedColumnCount = columns.filter((column) => {
		const center = elementCenter(column);
		return walls.some((wall) => distancePointToWallElement(center, wall) <= colBindTol || rectIntersects(column, wall));
	}).length;
	const columnAttachmentRate = columns.length ? attachedColumnCount / columns.length : 1;
	const probableColumnNodes = gridPrior?.probableColumnNodes.length ?? 0;
	const gridIntersections = gridPrior?.intersections.length ?? 0;
	const issues: GateIssue[] = [];
	if (walls.length < 8) {
		issues.push({
			id: 'gate-structure-wall-backbone-too-few',
			severity: 'error',
			message: '结构主干墙数量不足，不能让门窗和房间升格为正式对象。',
			targetIds: walls.map((wall) => wall.id),
		});
	}
	if (wallFragmentationScore > 0.35 || danglingWallRate > 0.28) {
		issues.push({
			id: 'gate-structure-wallgraph-unstable',
			severity: 'error',
			message: 'WallGraph 碎片或悬空墙比例过高，结构主干未站稳。',
			targetIds: [...wallGraph.fragmentGroups.flat(), ...wallGraph.danglingWallIds],
		});
	}
	if (probableColumnNodes >= 3 && columns.length === 0) {
		issues.push({
			id: 'gate-structure-probable-columns-missing',
			severity: 'error',
			message: '轴网/重复节点显示存在柱位证据，但未形成柱候选，需先修复柱识别。',
			targetIds: [],
		});
	} else if (gridIntersections >= 4 && columns.length === 0 && walls.length >= 20) {
		issues.push({
			id: 'gate-structure-columns-missing-in-grid-plan',
			severity: 'warning',
			message: '疑似有轴网的平面未识别到柱，附属对象只能作为候选复核。',
			targetIds: [],
		});
	}
	if (columns.length > 0 && columnAttachmentRate < 0.5) {
		issues.push({
			id: 'gate-structure-column-attachment-low',
			severity: 'warning',
			message: '柱与墙图挂接率偏低，结构主干可信度不足。',
			targetIds: columns.map((column) => column.id),
		});
	}
	if (wallPairingRate < 0.25 && walls.length >= 12) {
		issues.push({
			id: 'gate-structure-wall-pairing-low',
			severity: 'warning',
			message: '厚墙/平行墙证据偏弱，墙体主干可能仍是碎线拼装。',
			targetIds: walls.map((wall) => wall.id),
		});
	}
	return {
		status: issues.every((issue) => issue.severity !== 'error') ? 'passed' : 'failed',
		score: Math.max(0, Math.min(100, Math.round(82 - wallFragmentationScore * 34 - danglingWallRate * 42 + wallPairingRate * 14 + columnAttachmentRate * 10 - (probableColumnNodes >= 3 && columns.length === 0 ? 28 : 0)))),
		issues,
		metrics: {
			wall_count: walls.length,
			column_count: columns.length,
			wall_fragmentation_score: wallFragmentationScore,
			dangling_wall_rate: danglingWallRate,
			wall_pairing_rate: wallPairingRate,
			column_attachment_rate: columnAttachmentRate,
			grid_intersections: gridIntersections,
			probable_column_nodes: probableColumnNodes,
		},
	};
};

const buildGateResult = (
	wallGraph: WallGraphDraft,
	elements: TraceElement[],
	dimensions: DimensionMark[],
	mainPlanBox: TraceRegion,
	traceMode: string,
	columnReviewIssues: ReviewIssue[] = [],
	wallReviewIssues: ReviewIssue[] = [],
	openingReviewIssues: ReviewIssue[] = [],
	windowReviewIssues: ReviewIssue[] = [],
	curtainWallReviewIssues: ReviewIssue[] = [],
	zoneReviewIssues: ReviewIssue[] = [],
	mmPerNormalized = 21000
): { contract: GateResult; geometry: GateResult; system: GateResult; reviewQueue: FloorPlanCompileResult['reviewQueue'] } => {
	const walls = elements.filter((element) => element.kind === 'wall_trace');
	const columns = elements.filter((element) => element.kind === 'column');
	const openings = elements.filter((element) => element.kind === 'door' || element.kind === 'window');
	const lowConfidenceSpaces = elements.filter((element) => element.kind === 'function_zone' && element.confidence < 0.7);
	const wallFragmentationScore = walls.length ? wallGraph.fragmentGroups.length / walls.length : 1;
	const danglingWallLimit = Math.max(3, Math.ceil(walls.length * 0.18));
	const danglingWallCount = wallGraph.danglingWallIds.length;
	const pairedWallCount = walls.filter((wall) => Math.min(wall.w, wall.h) > 0.006).length;
	const wallPairingRate = walls.length ? pairedWallCount / walls.length : 0;
	const gateColBindTol = Math.min(0.040, Math.max(0.008, 200 / mmPerNormalized));
	const attachedColumnCount = columns.filter((column) => {
		const center = elementCenter(column);
		return walls.some((wall) => distancePointToWallElement(center, wall) <= gateColBindTol || rectIntersects(column, wall));
	}).length;
	const columnAttachmentRate = columns.length ? attachedColumnCount / columns.length : 1;
	// ── 柱类型指标 ──
	const wallPrimaryStructural = walls.filter((w) => w.wallVerification?.structuralRole === 'primary_structural_wall').length;
	const wallEnclosure = walls.filter((w) => w.wallVerification?.structuralRole === 'enclosure_wall').length;
	const wallPartition = walls.filter((w) => w.wallVerification?.structuralRole === 'partition_wall').length;
	const wallLightPartition = walls.filter((w) => w.wallVerification?.structuralRole === 'light_partition').length;
	const wallUnverified = walls.filter((w) => !w.wallVerification || w.wallVerification.structuralRole === 'wall_candidate_unverified').length;
	const wallVerifiedRate = walls.length ? 1 - wallUnverified / walls.length : 0;
	// ── 开口类型指标 ──
	const openingSwingDoorCount = openings.filter((o) => o.openingVerification?.openingType === 'swing_door').length;
	const openingDoubleDoorCount = openings.filter((o) => o.openingVerification?.openingType === 'double_swing_door').length;
	const openingSlidingDoorCount = openings.filter((o) => o.openingVerification?.openingType === 'sliding_door').length;
	const openingVoidPassageCount = openings.filter((o) => o.openingVerification?.openingType === 'void_passage').length;
	const openingUnverifiedCount = openings.filter((o) => !o.openingVerification || o.openingVerification.openingType === 'opening_candidate_unverified').length;
	const openingVerifiedRate = openings.length ? 1 - openingUnverifiedCount / openings.length : 0;
	const openingBoundCount = openings.filter((o) => o.openingVerification?.hostWallId).length;
	const openingHostBindingRate = openings.length ? openingBoundCount / openings.length : 1;
	// ── 窗户类型指标 ──
	const windowElements = elements.filter((e) => e.kind === 'window');
	const windowFixedCount = windowElements.filter((w) => w.windowVerification?.windowType === 'fixed_window').length;
	const windowCasementCount = windowElements.filter((w) => w.windowVerification?.windowType === 'casement_window').length;
	const windowSlidingCount = windowElements.filter((w) => w.windowVerification?.windowType === 'sliding_window').length;
	const windowRibbonCount = windowElements.filter((w) => w.windowVerification?.windowType === 'ribbon_window').length;
	const windowUnverifiedCount = windowElements.filter((w) => !w.windowVerification || w.windowVerification.windowType === 'window_candidate_unverified').length;
	const windowVerifiedRate = windowElements.length ? 1 - windowUnverifiedCount / windowElements.length : 0;
	// ── 幕墙类型指标 ──
	const curtainWallElements = elements.filter((e) => e.kind === 'curtain_wall');
	const cwFrameCount = curtainWallElements.filter((c) => c.curtainWallVerification?.curtainWallType === 'frame_curtain_wall').length;
	const cwFullGlassCount = curtainWallElements.filter((c) => c.curtainWallVerification?.curtainWallType === 'full_glass_curtain_wall').length;
	const cwUnverifiedCount = curtainWallElements.filter((c) => !c.curtainWallVerification || c.curtainWallVerification.curtainWallType === 'curtain_wall_candidate_unverified').length;
	const primaryStructuralCount = columns.filter((c) => c.columnVerification?.columnType === 'primary_structural_column').length;
	const masonryPierCount = columns.filter((c) => c.columnVerification?.columnType === 'masonry_reinforcement_pier').length;
	const shearWallEdgePierCount = columns.filter((c) => c.columnVerification?.columnType === 'shear_wall_edge_pier').length;
	const unverifiedCount = columns.filter((c) => !c.columnVerification || c.columnVerification.columnType === 'column_candidate_unverified').length;
	const typeConflictCount = columns.filter((c) => c.columnVerification?.reviewFlags?.includes('type_conflict')).length;
	const scaleFromMainPlan = traceMode.includes('scale:roi') || traceMode.includes('scale:main_plan');
	const scaleScoreDelta = traceMode.includes('scale:vector_guess')
		? -18
		: dimensions.length > 0
			? (scaleFromMainPlan ? 10 : 4)
			: -12;
	const wallById = new Map(walls.map((wall) => [wall.id, wall]));
	const missingColumnNodeIssues = wallGraph.joints
		.filter((joint) => joint.wallIds.length >= 2)
		.filter((joint) => !columns.some((column) => Math.hypot(elementCenter(column).x - joint.point.x, elementCenter(column).y - joint.point.y) <= 0.04 || rectIntersects(column, {
			id: `joint-probe-${joint.jointId}`,
			kind: 'column',
			label: 'joint-probe',
			geometryType: 'rect',
			x: joint.point.x - 0.016,
			y: joint.point.y - 0.016,
			w: 0.032,
			h: 0.032,
			confidence: 0.1,
			status: 'candidate',
		})))
		.slice(0, 16)
		.map((joint, index): ReviewIssue => ({
			id: `review-column-node-${index + 1}`,
			type: 'suspected_missing_column',
			severity: 'info',
			message: '墙图结构节点附近没有柱候选，需复核黑色实体柱是否漏检。',
			targetIds: joint.wallIds.filter((wallId) => wallById.has(wallId)),
		}));
	const mainPlanCoverage = mainPlanBox.w * mainPlanBox.h;
	const geometryIssues: GateIssue[] = [];
	if (dimensions.length === 0) geometryIssues.push({ id: 'gate-geometry-scale-missing', severity: 'warning', message: '未校准比例尺，候选不得冻结为正式 FloorPlanIR。', targetIds: [] });
	if (traceMode.includes('scale:vector_guess')) geometryIssues.push({ id: 'gate-geometry-scale-vector-guess', severity: 'warning', message: '比例尺仅来自矢量几何估算，不得冻结为正式尺寸。', targetIds: [] });
	else if (dimensions.length > 0 && !scaleFromMainPlan) geometryIssues.push({ id: 'gate-geometry-scale-margin', severity: 'info', message: '比例尺来自主平面邻近标注，需人工确认后才能冻结。', targetIds: [] });
	if (traceMode.includes('mainplan:fallback_recognition_region')) geometryIssues.push({ id: 'gate-geometry-mainplan-fallback', severity: 'info', message: '主平面框暂以识别区作为坐标基准，focus cluster 仅作为调试候选。', targetIds: [] });
	if (walls.length < 8) geometryIssues.push({ id: 'gate-geometry-wall-too-few', severity: 'error', message: '墙图候选不足，无法形成稳定 WallGraph。', targetIds: walls.map((wall) => wall.id) });
	if (wallFragmentationScore > 0.35) geometryIssues.push({ id: 'gate-geometry-wall-fragmented', severity: 'error', message: '墙碎片率过高，需要先做共线合并和端点吸附。', targetIds: wallGraph.fragmentGroups.flat() });
	if (danglingWallCount > danglingWallLimit) geometryIssues.push({ id: 'gate-geometry-dangling-walls', severity: 'error', message: '悬空墙数量过多，墙图连续性不足。', targetIds: wallGraph.danglingWallIds });
	if (wallPairingRate < 0.35) geometryIssues.push({ id: 'gate-geometry-wall-pairing-low', severity: 'warning', message: '平行墙/厚墙证据不足，墙厚聚类不稳定。', targetIds: walls.map((wall) => wall.id) });
	if (columnAttachmentRate < 0.5) geometryIssues.push({ id: 'gate-geometry-column-unattached', severity: 'warning', message: '柱候选与墙图挂接率偏低。', targetIds: columns.map((column) => column.id) });
	if (typeConflictCount > 0) geometryIssues.push({ id: 'gate-geometry-column-type-conflict', severity: 'info', message: `${typeConflictCount} 根柱存在类型冲突标记，建议人工复核。`, targetIds: columns.filter((c) => c.columnVerification?.reviewFlags?.includes('type_conflict')).map((c) => c.id) });
	if (unverifiedCount > columns.length * 0.5 && columns.length >= 4) geometryIssues.push({ id: 'gate-geometry-column-unverified-high', severity: 'warning', message: '超半数柱未能通过类型验证，柱检测质量偏低。', targetIds: columns.filter((c) => !c.columnVerification || c.columnVerification.columnType === 'column_candidate_unverified').map((c) => c.id) });
	if (wallUnverified > walls.length * 0.5 && walls.length >= 6) geometryIssues.push({ id: 'gate-geometry-wall-unverified-high', severity: 'warning', message: `超半数墙体(${wallUnverified}/${walls.length})未通过类型验证。`, targetIds: walls.filter((w) => !w.wallVerification || w.wallVerification.structuralRole === 'wall_candidate_unverified').map((w) => w.id) });
	if (openingUnverifiedCount > openings.length * 0.5 && openings.length >= 4) geometryIssues.push({ id: 'gate-geometry-opening-unverified-high', severity: 'warning', message: `超半数开口(${openingUnverifiedCount}/${openings.length})未通过类型验证。`, targetIds: openings.filter((o) => !o.openingVerification || o.openingVerification.openingType === 'opening_candidate_unverified').map((o) => o.id) });
	if (openingHostBindingRate < 0.5 && openings.length >= 3) geometryIssues.push({ id: 'gate-geometry-opening-unbound-high', severity: 'warning', message: `开口寿主墙绑定率偏低(${Math.round(openingHostBindingRate * 100)}%)。`, targetIds: openings.filter((o) => !o.openingVerification?.hostWallId).map((o) => o.id) });
	if (windowUnverifiedCount > windowElements.length * 0.5 && windowElements.length >= 4) geometryIssues.push({ id: 'gate-geometry-window-unverified-high', severity: 'warning', message: `超半数窗户(${windowUnverifiedCount}/${windowElements.length})未通过类型验证。`, targetIds: windowElements.filter((w) => !w.windowVerification || w.windowVerification.windowType === 'window_candidate_unverified').map((w) => w.id) });
	if (cwUnverifiedCount > curtainWallElements.length * 0.5 && curtainWallElements.length >= 2) geometryIssues.push({ id: 'gate-geometry-curtain-wall-unverified-high', severity: 'info', message: `超半数幕墙(${cwUnverifiedCount}/${curtainWallElements.length})未通过类型验证。`, targetIds: curtainWallElements.filter((c) => !c.curtainWallVerification || c.curtainWallVerification.curtainWallType === 'curtain_wall_candidate_unverified').map((c) => c.id) });
	if (mainPlanCoverage < 0.04) geometryIssues.push({ id: 'gate-geometry-main-plan-local', severity: 'error', message: '主平面结构域过小，疑似只识别到局部详图。', targetIds: [] });

	// Bug 4 修复：source-draft 警告原为硬编码，每次必出现，与实际绑定状态无关。
	// 现改为条件判断：只有在未传入 buildingCarrierRef 时才推送该警告。
	// buildingCarrierRef 由调用方（PlanSandboxPanel）在绑定空间后随 traceMode 一起传入。
	const hasBuildingCarrierRef = traceMode.includes('carrier:bound');
	const contractIssues: GateIssue[] = hasBuildingCarrierRef ? [] : [
		{ id: 'gate-contract-source-draft', severity: 'warning', message: '当前来自外部底图 draft，尚未绑定正式 building_carrier_ref / spg_version。', targetIds: [] },
	];
	if (walls.length < 8) contractIssues.push({ id: 'gate-contract-minimum-wall-set', severity: 'error', message: '墙体对象不足，不能形成最小 FloorPlanIR 对象契约。', targetIds: walls.map((wall) => wall.id) });
	if (mainPlanCoverage < 0.04) contractIssues.push({ id: 'gate-contract-main-plan-too-small', severity: 'error', message: '主平面坐标域过小，不能绑定为正式对象契约。', targetIds: [] });
	if (traceMode.includes('mainplan:fallback_recognition_region')) contractIssues.push({ id: 'gate-contract-main-plan-fallback', severity: 'error', message: '主平面框仅来自默认识别区，请先由用户 ROI 或图框检测确认坐标域。', targetIds: [] });
	const systemIssues: GateIssue[] = [];
	if (columns.length === 0) systemIssues.push({ id: 'gate-system-columns-missing', severity: 'warning', message: '未形成稳定柱集，hard_fixed 结构节点不完整。', targetIds: [] });
	if (zoneReviewIssues.some((issue) => issue.type === 'core_zone_incomplete')) systemIssues.push({ id: 'gate-system-core-zone-incomplete', severity: 'warning', message: '核心筒对象链不完整，需复核电梯、楼梯、管井或前室组合。', targetIds: zoneReviewIssues.filter((issue) => issue.type === 'core_zone_incomplete').flatMap((issue) => issue.targetIds) });
	if (openingHostBindingRate < 0.5 && openings.length >= 3) systemIssues.push({ id: 'gate-system-opening-host-low', severity: 'warning', message: '门窗洞口与宿主墙系统绑定率偏低。', targetIds: openings.filter((opening) => !opening.openingVerification?.hostWallId && !opening.windowVerification?.hostWallId).map((opening) => opening.id) });
	if (windowElements.length >= 4 && windowVerifiedRate < 0.5) systemIssues.push({ id: 'gate-system-fenestration-low', severity: 'warning', message: '窗系统验证率偏低，需复核普通窗、带形窗与幕墙分流。', targetIds: windowElements.filter((window) => !window.windowVerification || window.windowVerification.windowType === 'window_candidate_unverified').map((window) => window.id) });
	if (wallReviewIssues.some((issue) => issue.type === 'parapet_railing_ambiguous')) systemIssues.push({ id: 'gate-system-edge-envelope-ambiguous', severity: 'info', message: '边界系统存在女儿墙/栏杆比例异常，需复核阳台、露台与外墙关系。', targetIds: wallReviewIssues.filter((issue) => issue.type === 'parapet_railing_ambiguous').flatMap((issue) => issue.targetIds) });
	const contractPassed = contractIssues.every((issue) => issue.severity !== 'error');
	// 第二层修复：geometryPassed 原本要求 dimensions.length > 0 且非 vector_guess，
	// 导致手动标定（scale:manual）时永远无法通过。现在接受 manual / roi / main_plan / llm（Layer 3）。
	const scaleIsCalibrated = traceMode.includes('scale:manual')
		|| traceMode.includes('scale:roi')
		|| traceMode.includes('scale:main_plan')
		|| traceMode.includes('scale:llm');
	const geometryPassed = geometryIssues.every((issue) => issue.severity !== 'error') && scaleIsCalibrated;
	const systemPassed = systemIssues.every((issue) => issue.severity !== 'error');
	const reviewQueue: FloorPlanCompileResult['reviewQueue'] = {
		wallFragments: [
			...wallGraph.fragmentGroups.map((group, index) => ({ id: `review-wall-fragment-${index + 1}`, type: 'wall_fragment' as const, severity: 'warning' as const, message: '短墙碎片需要合并或删除。', targetIds: group })),
			...wallGraph.danglingWallIds.map((wallId, index) => ({ id: `review-dangling-wall-${index + 1}`, type: 'dangling_wall' as const, severity: 'warning' as const, message: '墙段未接入 WallGraph 交点，需要端点吸附或判定为噪声。', targetIds: [wallId] })),
		],
		suspectedMissingColumns: [
			...(columnAttachmentRate < 0.75 ? [{ id: 'review-column-attachment-low', type: 'suspected_missing_column' as const, severity: 'warning' as const, message: '柱挂接率偏低，需检查黑色实体柱是否漏检。', targetIds: columns.map((column) => column.id) }] : []),
			...missingColumnNodeIssues,
			...columnReviewIssues,
		],
		unboundOpenings: openings.filter((opening) => !bindOpeningToNearestWall(opening, walls)).map((opening) => ({ id: `review-unbound-${opening.id}`, type: 'unbound_opening', severity: 'warning', message: '开口未绑定 host wall，不能进入正式 IR。', targetIds: [opening.id] })),
		lowConfidenceSpaces: lowConfidenceSpaces.map((space) => ({ id: `review-space-${space.id}`, type: 'low_confidence_space', severity: 'info', message: '空间候选置信度偏低，等待墙图稳定后重算。', targetIds: [space.id] })),
		scaleIssues: traceMode.includes('scale:manual')
			? []  // 手动标定：无需任何比例尺警告
			: traceMode.includes('scale:llm')
				? [{ id: 'review-scale-llm', type: 'scale_issue', severity: 'info', message: 'LLM 视觉比例估算已启用，精度优于纯几何推断，建议有尺寸标注时人工确认。', targetIds: [] }]
				: dimensions.length === 0
					? [{ id: 'review-scale-missing', type: 'scale_issue', severity: 'warning', message: '缺少比例尺校准，不能冻结尺寸。', targetIds: [] }]
					: traceMode.includes('scale:vector_guess')
						? [{ id: 'review-scale-vector-guess', type: 'scale_issue', severity: 'warning', message: '当前比例尺仅为矢量几何估算，需人工校准或读取尺寸标注。', targetIds: [] }]
						: (!scaleFromMainPlan ? [{ id: 'review-scale-margin', type: 'scale_issue', severity: 'info', message: '比例尺来自主平面邻近标注，建议人工确认。', targetIds: [] }] : []),
		wallTypeIssues: wallReviewIssues,
		openingTypeIssues: openingReviewIssues,
		windowTypeIssues: windowReviewIssues,
		curtainWallIssues: curtainWallReviewIssues,
		zoneTypeIssues: zoneReviewIssues.filter((i) => i.type !== 'core_zone_incomplete' && i.type !== 'balcony_low_confidence' && i.type !== 'terrace_vs_balcony_conflict'),
		coreZoneIssues: zoneReviewIssues.filter((i) => i.type === 'core_zone_incomplete'),
		edgeIssues: [
			...wallReviewIssues.filter((i) => i.type === 'parapet_railing_ambiguous'),
			...zoneReviewIssues.filter((i) => i.type === 'balcony_low_confidence' || i.type === 'terrace_vs_balcony_conflict'),
		],
	};
	return {
		contract: { status: contractPassed ? 'passed' : 'failed', score: contractPassed ? 78 : 35, issues: contractIssues, metrics: { source_refs: 1, formal_bindings: traceMode.includes('mainplan:fallback_recognition_region') ? 0 : 1, minimum_wall_set: walls.length >= 8 ? 1 : 0 } },
		geometry: {
			status: geometryPassed ? 'passed' : 'failed',
			score: Math.max(0, Math.min(100, Math.round(70 - wallFragmentationScore * 35 - Math.max(0, danglingWallCount - danglingWallLimit) * 4 + wallPairingRate * 18 + columnAttachmentRate * 12 + scaleScoreDelta))),
			issues: geometryIssues,
			metrics: { wall_count: walls.length, wall_fragmentation_score: wallFragmentationScore, dangling_wall_count: danglingWallCount, wall_pairing_rate: wallPairingRate, column_attachment_rate: columnAttachmentRate, primary_structural_columns: primaryStructuralCount, masonry_piers: masonryPierCount, shear_wall_edge_piers: shearWallEdgePierCount, column_unverified: unverifiedCount, column_type_conflicts: typeConflictCount, suspected_missing_column_nodes: missingColumnNodeIssues.length, main_plan_coverage: mainPlanCoverage, dimensions: dimensions.length, scale_vector_guess: traceMode.includes('scale:vector_guess') ? 1 : 0, mode_primary_cluster: traceMode.includes('primary') ? 1 : 0, wall_verified_rate: wallVerifiedRate, wall_primary_structural: wallPrimaryStructural, wall_enclosure: wallEnclosure, wall_partition: wallPartition, wall_light_partition: wallLightPartition, wall_unverified: wallUnverified, opening_verified_rate: openingVerifiedRate, opening_host_binding_rate: openingHostBindingRate, opening_swing_doors: openingSwingDoorCount, opening_double_doors: openingDoubleDoorCount, opening_sliding_doors: openingSlidingDoorCount, opening_void_passages: openingVoidPassageCount, opening_unverified: openingUnverifiedCount, window_verified_rate: windowVerifiedRate, window_fixed: windowFixedCount, window_casement: windowCasementCount, window_sliding: windowSlidingCount, window_ribbon: windowRibbonCount, window_unverified: windowUnverifiedCount, curtain_wall_count: curtainWallElements.length, curtain_wall_frame: cwFrameCount, curtain_wall_full_glass: cwFullGlassCount, curtain_wall_unverified: cwUnverifiedCount, zone_elevator_count: elements.filter((e) => e.zoneVerification?.zoneType === 'elevator' || e.zoneVerification?.zoneType === 'freight_elevator').length, zone_staircase_count: elements.filter((e) => e.zoneVerification?.zoneType === 'fire_staircase' || e.zoneVerification?.zoneType === 'building_staircase' || e.zoneVerification?.zoneType === 'interior_staircase').length, zone_shaft_count: elements.filter((e) => ['plumbing_shaft', 'electrical_shaft', 'ventilation_shaft', 'general_shaft'].includes(e.zoneVerification?.zoneType ?? '')).length, zone_equipment_room_count: elements.filter((e) => ['electrical_room', 'mechanical_room', 'general_equipment_room'].includes(e.zoneVerification?.zoneType ?? '')).length, zone_balcony_count: elements.filter((e) => e.zoneVerification?.zoneType === 'balcony' || e.zoneVerification?.zoneType === 'open_balcony').length, zone_terrace_count: elements.filter((e) => e.zoneVerification?.zoneType === 'terrace').length, wall_parapet_count: walls.filter((w) => w.wallVerification?.structuralRole === 'parapet_wall').length, wall_railing_count: walls.filter((w) => w.wallVerification?.structuralRole === 'railing_line').length, zone_unverified_count: elements.filter((e) => e.zoneVerification?.zoneType === 'zone_candidate_unverified').length },
		},
		system: {
			status: systemPassed ? 'passed' : 'failed',
			score: Math.max(0, Math.min(100, 72 - systemIssues.filter((issue) => issue.severity === 'warning').length * 8 - systemIssues.filter((issue) => issue.severity === 'error').length * 20)),
			issues: systemIssues,
			metrics: {
				columns: columns.length,
				hard_fixed_ready: columns.length > 0 ? 1 : 0,
				core_zone_issue_count: zoneReviewIssues.filter((issue) => issue.type === 'core_zone_incomplete').length,
				opening_host_binding_rate: openingHostBindingRate,
				window_verified_rate: windowVerifiedRate,
				edge_envelope_issue_count: wallReviewIssues.filter((issue) => issue.type === 'parapet_railing_ambiguous').length,
			},
		},
		reviewQueue,
	};
};

// ─── Layer 3: LLM 语义骨架识别 ──────────────────────────────────────────────
// Phase 1 of the two-phase pipeline: call Python LLM endpoint to get
// semantic skeleton (walls, openings, columns, scale hint) from the rendered PDF image.

interface LlmWallHint {
	x1: number; y1: number; x2: number; y2: number;
	thickness_mm?: number;
	wall_type?: string;
}
interface LlmOpeningHint {
	type: string;
	x: number; y: number;
	width_mm?: number;
	wall_direction?: string;
}
interface LlmColumnHint {
	cx: number; cy: number;
	width_mm?: number;
	depth_mm?: number;
}
interface LlmScaleHint {
	mm_per_normalized?: number;
	typical_room_width_mm?: number;
	typical_wall_thickness_mm?: number;
	confidence?: 'low' | 'medium' | 'high';
}
interface LlmSkeletonResult {
	status: 'success' | 'error' | 'no_vision_llm';
	spatial_zone: string;
	walls: LlmWallHint[];
	openings: LlmOpeningHint[];
	columns: LlmColumnHint[];
	scale_hint?: LlmScaleHint;
	error?: string;
}

/**
 * 尝试调用 Python LLM 骨架识别端点（Phase 1 two-phase pipeline）。
 *
 * 若 Python 服务不可用、超时、或返回错误，则静默返回 null，不影响后续几何分析。
 * 成功时返回 LlmSkeletonResult，其中 scale_hint 用于改善 mmPerNormalized 估算。
 */
async function tryCallLlmSkeleton(
	fileUrl: string,
	spatialZone: string,
): Promise<LlmSkeletonResult | null> {
	// Python 后端基地址（与 NEXT_PUBLIC_API_URL 对齐）
	const pyApiBase = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8001';
	const endpoint = `${pyApiBase}/api/v1/floor-plan/llm-skeleton`;

	try {
		const controller = new AbortController();
		// 整个 LLM 骨架识别给 70 秒超时（PDF 渲染 + LLM 调用）
		const timer = setTimeout(() => controller.abort(), 70_000);
		try {
			const resp = await fetch(endpoint, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ fileUrl, spatialZone, renderDpi: 150 }),
				signal: controller.signal,
			});
			if (!resp.ok) {
				const errText = await resp.text().catch(() => '');
				console.warn(`[llm-skeleton] HTTP ${resp.status}: ${errText.slice(0, 200)}`);
				return null;
			}
			const data = await resp.json() as LlmSkeletonResult;
			if (data.status === 'no_vision_llm') {
				console.warn('[llm-skeleton] Python Vision LLM 未初始化，跳过 Phase 1');
				return null;
			}
			console.log(
				`[llm-skeleton] ✅ Phase 1 完成: walls=${data.walls.length}` +
				` openings=${data.openings.length} columns=${data.columns.length}` +
				` scale_hint=${JSON.stringify(data.scale_hint)}`,
			);
			return data;
		} finally {
			clearTimeout(timer);
		}
	} catch (err: unknown) {
		const msg = err instanceof Error ? err.message : String(err);
		// AbortError → 超时静默
		const isAbort = err instanceof Error && err.name === 'AbortError';
		console.warn(`[llm-skeleton] ${isAbort ? '超时' : '调用失败'}: ${msg.slice(0, 120)}`);
		return null;
	}
}

/**
 * 从 LLM 骨架中推算 mmPerNormalized（每归一化单位对应的毫米数）。
 *
 * 算法：
 * 1. 若 LLM 直接给出 scale_hint.mm_per_normalized → 直接使用
 * 2. 否则：从水平墙线中位长度 + typical_room_width_mm 推算
 *    - 过滤"房间级"水平墙（长度 0.05~0.45 归一化单位，排除超长/超短噪声）
 *    - 取中位长度 roomWidthNorm
 *    - mmPerNorm = typical_room_width_mm / roomWidthNorm
 * 3. 最终限制在 [2000, 100000] 的合理范围内
 */
function deriveMmPerNormFromLlm(llm: LlmSkeletonResult): number | undefined {
	const sh = llm.scale_hint;
	if (!sh) return undefined;
	if (typeof sh.mm_per_normalized === 'number' && sh.mm_per_normalized > 500 && sh.mm_per_normalized < 200000) {
		return sh.mm_per_normalized;
	}
	const roomMm = sh.typical_room_width_mm;
	if (!roomMm || roomMm < 1000 || roomMm > 20000) return undefined;

	// 从 LLM 水平墙中找"房间宽度级"线段
	const horzWalls = llm.walls.filter((w) => {
		const dx = Math.abs(w.x2 - w.x1);
		const dy = Math.abs(w.y2 - w.y1);
		if (dx < dy * 3 && dy < dx * 3) return false; // 斜墙排除
		return dx >= 0.04 && dx <= 0.55; // 过滤太短/太长
	});
	if (horzWalls.length === 0) {
		// 退而求其次：用竖向墙
		const vertWalls = llm.walls.filter((w) => {
			const dy = Math.abs(w.y2 - w.y1);
			return dy >= 0.04 && dy <= 0.55;
		});
		if (vertWalls.length === 0) return undefined;
		const lens = vertWalls.map((w) => Math.abs(w.y2 - w.y1)).sort((a, b) => a - b);
		const roomWidthNorm = lens[Math.floor(lens.length / 2)];
		if (roomWidthNorm < 0.01) return undefined;
		return Math.max(2000, Math.min(100000, roomMm / roomWidthNorm));
	}
	const lens = horzWalls.map((w) => Math.abs(w.x2 - w.x1)).sort((a, b) => a - b);
	const roomWidthNorm = lens[Math.floor(lens.length / 2)];
	if (roomWidthNorm < 0.01) return undefined;
	return Math.max(2000, Math.min(100000, roomMm / roomWidthNorm));
}

export async function POST(request: NextRequest) {
	try {
		let parsedBody: unknown;
		try {
			parsedBody = await request.json();
		} catch {
			return NextResponse.json({ error: 'Invalid JSON body.' }, { status: 400 });
		}
		if (!isRecord(parsedBody)) return NextResponse.json({ error: 'Invalid request body.' }, { status: 400 });
		const fileUrl = typeof parsedBody.fileUrl === 'string' ? parsedBody.fileUrl.trim() : '';
		if (!fileUrl) return NextResponse.json({ error: 'Missing fileUrl.' }, { status: 400 });
		let safeName: string;
		try {
			safeName = getSafeFileName(fileUrl);
		} catch (error) {
			const message = error instanceof Error ? error.message : 'Invalid drawing file reference.';
			return NextResponse.json({ error: message }, { status: 400 });
		}
		const extension = path.extname(safeName).toLowerCase();
		if (!TRACE_SUPPORTED_EXTENSIONS.has(extension)) {
			const issues: TraceIssue[] = [{
				id: 'issue-unsupported-source',
				type: 'unsupported_source',
				severity: 'warning',
				targetIds: [],
				message: '该格式暂无服务端矢量识别，建议优先上传矢量 PDF 或 DXF。',
				suggestedAction: 'upload_vector_pdf_or_dxf',
			}];
			return NextResponse.json({
				status: 'unsupported',
				compilerStatus: 'candidate_ready',
				message: '该格式暂无服务端矢量识别，前端将回退到本地像素识别。',
				elements: [],
				issues,
				issueMessages: traceIssueMessages(issues),
				quality: buildQualityScore([], 0, issues),
			});
		}
		const filePath = path.join(UPLOAD_DIR, safeName);
		let fileStat;
		try {
			fileStat = await fs.stat(filePath);
		} catch {
			return NextResponse.json({ error: 'Drawing file not found.' }, { status: 404 });
		}
		if (fileStat.size > MAX_TRACE_FILE_BYTES) {
			return NextResponse.json({ error: 'Drawing file is too large for synchronous tracing.' }, { status: 413 });
		}
		const buffer = await fs.readFile(filePath);
		const rawRegion = isRecord(parsedBody.region) ? parsedBody.region as Partial<TraceRegion> : undefined;
		const region = normalizeRegion(rawRegion);
		const hasRegionKeys = !!rawRegion && ['x', 'y', 'w', 'h'].some((key) => Object.prototype.hasOwnProperty.call(rawRegion, key));
		const hasRequestedRegion = hasRegionKeys && !isUnitFullRegion(region);
		// 手动比例尺：用户通过前端输入精确 mm/norm 值时直接跳过 vector_guess
		const rawManualScale = parsedBody.manualScaleMmPerNorm;
		const manualScaleMmPerNorm: number | undefined =
			typeof rawManualScale === 'number' && Number.isFinite(rawManualScale) && rawManualScale > 500 && rawManualScale < 200000
				? rawManualScale
				: undefined;
		let recognitionRegion = region;
		let segments: TraceSegment[] = [];
		let dimensions: DimensionMark[] = [];
		let contentBox: TraceRegion | undefined;
		let classifiedTexts: ClassifiedText[] = [];
		let detectedCircles: DetectedCircle[] = [];
		let pdfParserDiag: TraceParseResult['parserDiag'] | undefined;
		/** Y轴比例修正因子：depthMm_correct = depthMm × pdfPageAspectYX（仅 PDF 来源时有值）*/
		let pdfPageAspectYX: number | undefined;
		const source: 'dxf' | 'pdf' = extension === '.dxf' ? 'dxf' : 'pdf';
		if (source === 'dxf') {
			segments = parseDxfSegments(buffer.toString('utf8'));
		} else {
			const result = await parsePdfSegments(buffer);
			segments = result.segments;
			dimensions = result.dimensions;
			contentBox = result.contentBox;
			classifiedTexts = result.classifiedTexts ?? [];
			detectedCircles = result.detectedCircles ?? [];
			pdfParserDiag = result.parserDiag;
			pdfPageAspectYX = result.pageAspectYX;
			recognitionRegion = pageRegionToContentRegion(region, contentBox);
			// ── 诊断日志 §1：PDF Parser 输出 ──────────────────────────────────────
			if (process.env.NODE_ENV !== 'production') {
				const pk = segments.reduce((acc, s) => { const k = s.pathKind ?? 'undefined'; acc[k] = (acc[k] ?? 0) + 1; return acc; }, {} as Record<string, number>);
				const dash = segments.reduce((acc, s) => { const k = s.dashPattern ?? 'undefined'; acc[k] = (acc[k] ?? 0) + 1; return acc; }, {} as Record<string, number>);
				const lwArr = segments.filter((s) => (s.lineWidth ?? 0) > 0).map((s) => s.lineWidth!).sort((a, b) => a - b);
				const lmed = lwArr.length > 0 ? lwArr[Math.floor(lwArr.length / 2)] : 0;
				// filledRect 尺寸分布（CAD柱通常 200-600mm 方形）
				const filledRects = segments.filter((s) => s.pathKind === 'filledRect');
				const frSizes = filledRects.map((s) => ({ w: Math.round(Math.abs(s.x2 - s.x1) * 21000), h: Math.round(Math.abs(s.y2 - s.y1) * 21000) }));
				const colCandidates = filledRects.filter((s) => { const w = Math.abs(s.x2 - s.x1); const h = Math.abs(s.y2 - s.y1); return w >= 0.006 && h >= 0.006 && w <= 0.055 && h <= 0.055 && Math.max(w, h) / Math.min(w, h) <= 3.0; });
				// 线段长度分布（判断墙线 vs 尺寸线比例）
				const lineLens = segments.filter((s) => s.pathKind === 'line').map(segmentLength).sort((a, b) => a - b);
				const llMed = lineLens.length > 0 ? lineLens[Math.floor(lineLens.length / 2)] : 0;
				// 强制 wall 条件命中数（lineWidth >= median*1.6）
				const forcedWall = segments.filter((s) => s.pathKind === 'line' && lmed > 0 && (s.lineWidth ?? 0) >= lmed * 1.6 && segmentLength(s) >= 0.010 && segmentLength(s) <= 0.65);
				console.log('\n========== [PDF诊断] §1 Parser 输出 ==========');
				console.log('  总线段:', segments.length, '| pathKind分布:', pk);
				console.log('  dashPattern分布:', dash);
				console.log('  lineWidth: 有值线段=', lwArr.length, '| min=', lwArr[0]?.toFixed(2) ?? 0, 'median=', lmed.toFixed(2), 'p75=', (lwArr[Math.floor(lwArr.length * 0.75)] ?? 0).toFixed(2), 'max=', (lwArr[lwArr.length - 1] ?? 0).toFixed(2));
				console.log('  line段长度: count=', lineLens.length, '| p10=', (lineLens[Math.floor(lineLens.length * 0.1)] ?? 0).toFixed(4), 'median=', llMed.toFixed(4), 'p90=', (lineLens[Math.floor(lineLens.length * 0.9)] ?? 0).toFixed(4));
				console.log('  强制wall条件命中:', forcedWall.length, '条');
				console.log('  filledRect 总数:', filledRects.length, '| 符合柱尺寸范围:', colCandidates.length);
				if (frSizes.length > 0) console.log('  filledRect 前10尺寸(估算mm@21000):', frSizes.slice(0, 10));
				console.log('  尺寸标注数:', dimensions.length, '| 值分布:', dimensions.slice(0, 8).map((m) => m.value));
				console.log('================================================\n');
			}
			// ── 诊断日志 §1 结束 ────────────────────────────────────────────────────
		}
		const scopedDimensions = dimensions.filter((mark) => dimensionInRegion(mark, recognitionRegion));

		// ── Layer 3 Phase 1: LLM 语义骨架识别 ────────────────────────────────────────
		// 仅在 PDF 来源、非手动标定时启用（手动标定已精确，不需要 LLM 补偿）
		// 使用 Promise.allSettled 并发：LLM 调用与后续同步计算可重叠
		const llmSkeletonPromise: Promise<LlmSkeletonResult | null> =
			source === 'pdf' && !manualScaleMmPerNorm
				? tryCallLlmSkeleton(
						fileUrl,
						// 空间区域上下文：从请求体读取，若无则默认"建筑平面图"
						typeof (parsedBody as Record<string, unknown>).spatialZone === 'string'
							? String((parsedBody as Record<string, unknown>).spatialZone)
							: '建筑平面图',
					)
				: Promise.resolve(null);

		// 用原始线段做粗估比例尺，解决 buildParallelWallCenters 配对窗口与比例尺脱钩问题
		const prelimScopedSegs = segments.filter((s) => inRegion(s, recognitionRegion));
		const prelimMedianLen = prelimScopedSegs.length > 4
			? [...prelimScopedSegs].map(segmentLength).sort((a, b) => a - b)[Math.floor(prelimScopedSegs.length / 2)]
			: undefined;
		const prelimMedianDim = scopedDimensions.length > 0
			? [...scopedDimensions].map((m) => m.value).sort((a, b) => a - b)[Math.floor(scopedDimensions.length / 2)]
			: undefined;

		// ── 等待 LLM 骨架结果（Phase 1 完成）────────────────────────────────────────
		const llmSkeleton = await llmSkeletonPromise;

		// ── Phase 2 前置：用 LLM 比例估算改善 prelimMmPerNorm ─────────────────────────
		// 优先级：manualScale > PDF 尺寸标注 > LLM 估算 > vector_guess 默认 21000
		const llmDerivedMmPerNorm = llmSkeleton ? deriveMmPerNormFromLlm(llmSkeleton) : undefined;
		if (llmDerivedMmPerNorm) {
			console.log(`[llm-skeleton] 采用 LLM 比例估算: ${Math.round(llmDerivedMmPerNorm)} mm/norm` +
				` (confidence=${llmSkeleton?.scale_hint?.confidence ?? 'unknown'})`);
		}

		const prelimMmPerNorm = manualScaleMmPerNorm
			?? ((prelimMedianDim && prelimMedianLen)
				? Math.max(1000, Math.min(80000, prelimMedianDim / Math.max(0.001, prelimMedianLen)))
				: (llmDerivedMmPerNorm ?? 21000));

		const traceResult = mergeAndFilterSegments(segments, recognitionRegion, scopedDimensions, prelimMmPerNorm);
		// ── 诊断日志 §2：mergeAndFilter 管道统计 ────────────────────────────────
		if (source === 'pdf' && process.env.NODE_ENV !== 'production') {
			const ps = traceResult.pipelineStats;
			console.log('\n========== [PDF诊断] §2 mergeAndFilter 管道 ==========');
			console.log('  mode:', traceResult.mode, '| focus.focused:', traceResult.focus?.focused);
			console.log('  regionScoped:', ps.regionScoped, '→ classifiedWall:', ps.classifiedWall, '→ focusedStrict:', ps.focusedStrictCandidates);
			console.log('  strictMerged:', ps.strictMerged, '| pairedWalls:', ps.pairedWalls, '→ selectedPipeline:', ps.selectedPipeline);
			console.log('  relaxedCandidates:', ps.relaxedCandidates, '| relaxedMerged:', ps.relaxedMerged);
			console.log('  classCounts:', traceResult.classCounts);
			console.log('  prelimMmPerNorm:', prelimMmPerNorm);
			console.log('======================================================\n');
		}
		// ── §2 结束 ──────────────────────────────────────────────────────────────
		const cleaned = compileWallGraphSegments(traceResult.segments, 160);
		const zoneSource = compileWallGraphSegments(traceResult.zoneSegments ?? cleaned, 128);
		const traceFocusBounds = traceResult.focus && 'focusBounds' in traceResult.focus ? traceResult.focus.focusBounds : undefined;
		const focusCandidateBoxInContent = traceFocusBounds ? boundsToRegion(traceFocusBounds, recognitionRegion) : undefined;
		const focusUsedAsMainPlanBox = shouldUseFocusAsMainPlanBox(
			focusCandidateBoxInContent,
			recognitionRegion,
			hasRequestedRegion,
			traceResult.focus?.focused
		);
		const contentSpaceMainPlanBox = focusUsedAsMainPlanBox && focusCandidateBoxInContent
			? focusCandidateBoxInContent
			: recognitionRegion;
		const mainPlanBoxSource = focusUsedAsMainPlanBox ? 'detected_plan_frame' as const : hasRequestedRegion ? 'user_roi' as const : 'fallback_recognition_region' as const;
		const initialScaleEvidence = selectScaleEvidenceDimensions(dimensions, recognitionRegion, contentSpaceMainPlanBox);
		let scaleEvidenceDimensions = initialScaleEvidence.dimensions;
		let scaleEvidenceSource: 'roi' | 'main_plan' | 'main_plan_margin' | 'roi_margin' | 'missing' | 'llm' = initialScaleEvidence.source;
		// BUG3 fix: buildVectorScaleGuess 是循环自证（恒等于 21000），移除后让 missing 如实上报，
		// 由 llmDerivedMmPerNorm ?? 21000 兜底，而非掩盖 scale_missing 事实。
		const medianDimension = scaleEvidenceDimensions.length > 0 ? [...scaleEvidenceDimensions].map((mark) => mark.value).sort((a, b) => a - b)[Math.floor(scaleEvidenceDimensions.length / 2)] : undefined;
		// BUG1 fix: 当 focusUsedAsMainPlanBox=true 时，mainPlanBox 是 recognitionRegion 的子集。
		// scaleEvidenceDimensions 来自 mainPlanBox 内部，但 cleaned 含整个 recognitionRegion 的线段，
		// 外围轴网短线拉低 medianLength → mmPerNormalized 系统性偏大。
		// 修复：focusUsed 时只取 mainPlanBox 范围内的线段计算中位长，保持分子分母空间一致。
		const cleanedForScale = (focusUsedAsMainPlanBox && focusCandidateBoxInContent)
			? cleaned.filter((s) => inRegion(s, contentSpaceMainPlanBox))
			: cleaned;
		const medianLength = cleanedForScale.length >= 4
			? [...cleanedForScale].map(segmentLength).sort((a, b) => a - b)[Math.floor(cleanedForScale.length / 2)]
			: (cleaned.length > 0 ? [...cleaned].map(segmentLength).sort((a, b) => a - b)[Math.floor(cleaned.length / 2)] : undefined);
		// 手动比例尺直接跳过估算，将 source 置为 'manual'，避免 vector_guess 固定值 21000 导致配对窗口错位
		if (manualScaleMmPerNorm) scaleEvidenceSource = 'manual' as typeof scaleEvidenceSource;
		// LLM 骨架比例：当 PDF 维度标注为空且有 LLM 中高置信度估算时，以 LLM 取代 missing
		if (!manualScaleMmPerNorm && scaleEvidenceSource === 'missing' && llmDerivedMmPerNorm) {
			const llmConf = llmSkeleton?.scale_hint?.confidence ?? 'low';
			if (llmConf === 'medium' || llmConf === 'high') {
				scaleEvidenceSource = 'llm' as typeof scaleEvidenceSource;
			}
		}
		const mmPerNormalized = manualScaleMmPerNorm
			?? (medianDimension && medianLength
				? Math.max(1000, Math.min(80000, medianDimension / Math.max(0.001, medianLength)))
				// LLM 比例优于默认 21000 猜测
				: (llmDerivedMmPerNorm ?? 21000));
		const earlyScaleGate = buildScaleGate({
			scaleEvidenceSource,
			scaleEvidenceDimensions,
			mmPerNormalized,
			prelimMmPerNorm,
		});
		if (earlyScaleGate.status !== 'passed') {
			const scaleBlockedMessage = '未校准比例尺，已禁止识别与编译候选。请先手动校准比例尺，或上传带可识别尺寸标注的图纸。';
			return NextResponse.json({
				status: 'no_result',
				compilerStatus: 'gate_failed',
				source,
				message: scaleBlockedMessage,
				elements: [],
				floorPlanIR: undefined,
				draftFloorPlanIR: undefined,
				compileResult: {
					status: 'gate_failed',
					formalPromotionAllowed: false,
					promotionBlockers: [scaleBlockedMessage],
					gates: {
						scale: earlyScaleGate,
					},
				},
				gates: {
					scale: earlyScaleGate,
				},
				formalPromotionAllowed: false,
				promotionBlockers: [scaleBlockedMessage],
				scaleCalibration: {
					mmPerNormalized,
					source: scaleEvidenceSource,
					samples: scaleEvidenceDimensions.length,
				},
				diagnostics: {
					rawSegments: segments.length,
					dimensionsInRegion: scopedDimensions.length,
					scaleEvidenceSource,
					scaleEvidenceSamples: scaleEvidenceDimensions.length,
					blockedBy: 'scale_calibration_required',
				},
				issues: [],
				issueMessages: earlyScaleGate.issues.map((issue) => issue.message),
			});
		}
		const wallElements = cleaned.map((segment, index) => segmentToElement(segment, index, mmPerNormalized));

		// ─── 门洞感知的逻辑墙桥接 ────────────────────────────────────────────────
		// 在 wallElements 上打 logicalWallId：同轨道的两段墙之间若存在 600-2400mm 的间距（门洞宽），
		// 则两侧墙段共享同一个 logicalWallId，供 buildDoorCandidates / detectWallGaps 使用。
		// 这解决"墙不连续"和"门/墙关系不明"两个问题。
		{
			const OPENING_GAP_MIN_MM = 500;
			const OPENING_GAP_MAX_MM = 2600;
			const OPENING_TRACK_TOL = 0.016; // 与 detectWallGaps 一致
			let logicalWallCounter = 0;
			// logicalWallId 存在 TraceElement.openingHostWallId（复用现有字段表示逻辑墙 ID）
			const assignLogicalId = (el: TraceElement, id: string) => {
				(el as TraceElement & { logicalWallId?: string }).logicalWallId = id;
			};
			const getLogicalId = (el: TraceElement): string | undefined =>
				(el as TraceElement & { logicalWallId?: string }).logicalWallId;

			for (let i = 0; i < wallElements.length; i++) {
				const a = wallElements[i];
				const aH = a.w >= a.h;
				const aTrack = aH ? a.y + a.h / 2 : a.x + a.w / 2;
				const aEnd = aH ? a.x + a.w : a.y + a.h;

				for (let j = i + 1; j < wallElements.length; j++) {
					const b = wallElements[j];
					const bH = b.w >= b.h;
					if (bH !== aH) continue;
					const bTrack = bH ? b.y + b.h / 2 : b.x + b.w / 2;
					if (Math.abs(bTrack - aTrack) > OPENING_TRACK_TOL) continue;
					const bStart = bH ? b.x : b.y;
					const bEnd = bH ? b.x + b.w : b.y + b.h;
					const aStart = aH ? a.x : a.y;

					// b 紧跟在 a 之后
					const gap = bStart - aEnd;
					if (gap <= 0) continue; // 重叠或相接，不是门洞
					const gapMm = gap * mmPerNormalized;
					if (gapMm < OPENING_GAP_MIN_MM || gapMm > OPENING_GAP_MAX_MM) continue;

					// 确保没有其他墙段挡在中间
					const blocked = wallElements.some((mid, mi) => {
						if (mi === i || mi === j) return false;
						const mH = mid.w >= mid.h;
						if (mH !== aH) return false;
						const mTrack = mH ? mid.y + mid.h / 2 : mid.x + mid.w / 2;
						if (Math.abs(mTrack - aTrack) > OPENING_TRACK_TOL) return false;
						const mStart = mH ? mid.x : mid.y;
						return mStart > aEnd && mStart < bStart;
					});
					if (blocked) continue;

					// 分配 / 共享逻辑墙 ID
					const existA = getLogicalId(a);
					const existB = getLogicalId(b);
					if (existA && !existB) {
						assignLogicalId(b, existA);
					} else if (!existA && existB) {
						assignLogicalId(a, existB);
					} else if (!existA && !existB) {
						const newId = `logical-wall-${logicalWallCounter++}`;
						assignLogicalId(a, newId);
						assignLogicalId(b, newId);
					}
					// 若两侧已有不同 ID，合并（用 a 的 ID 覆盖 b 的所有关联段）
					else if (existA !== existB) {
						const targetId = existA!;
						wallElements.forEach((el) => {
							if (getLogicalId(el) === existB) assignLogicalId(el, targetId);
						});
					}
				}
			}
		}

		const spaceElements = buildClosedSpaceZones(zoneSource, mmPerNormalized);

		// ─── 原始线段过滤：用主平面聚类 focus bounds 排除尺寸标注带 ───
		// focusCandidateBoxInContent 是 mergeAndFilterSegments 内 focusPrimaryPlanCluster 找到的主图聚类框
		// 在此基础上向外加一个小 pad，避免边缘柱漏检，同时阻止画框/标注列/轴网带的假柱
		const regionRawSegments = segments.filter((segment) => inRegion(segment, recognitionRegion));
		const classifiedRegionSegments = classifyScopedSegmentsForLayers(regionRawSegments, scopedDimensions);
		const focusedRawSegments = (focusCandidateBoxInContent && traceResult.focus?.focused)
			? (() => {
				const fb = focusCandidateBoxInContent;
				const padX = Math.max(0.010, fb.w * 0.08);
				const padY = Math.max(0.010, fb.h * 0.08);
				const minX = Math.max(0, fb.x - padX);
				const maxX = Math.min(1, fb.x + fb.w + padX);
				const minY = Math.max(0, fb.y - padY);
				const maxY = Math.min(1, fb.y + fb.h + padY);
				return regionRawSegments.filter((s) => {
					// filledRect / filledPolygon / rect 是柱检测的核心信号（尺寸有界，不会引入标注噪声）
					// 不对它们做 focus 裁剪，避免周边柱（中心点恰在 focus box 边缘外）被误删
					if (s.pathKind === 'filledRect' || s.pathKind === 'filledPolygon' || s.pathKind === 'rect') return true;
					// line / curve：用 focus box 过滤，防止标注带/图框内的长线段干扰墙/门窗检测
					const cx = (s.x1 + s.x2) / 2;
					const cy = (s.y1 + s.y2) / 2;
					return cx >= minX && cx <= maxX && cy >= minY && cy <= maxY;
				});
			})()
			: regionRawSegments;

		// ── 诊断日志 §3：比例尺 + 墙元素 ──────────────────────────────────────
		if (source === 'pdf' && process.env.NODE_ENV !== 'production') {
			console.log('\n========== [PDF诊断] §3 比例尺 & 墙 ==========');
			console.log('  scaleEvidenceSource:', scaleEvidenceSource, '| scaleEvidenceDimensions:', scaleEvidenceDimensions.length);
			console.log('  medianDimension:', medianDimension, '| medianLength:', medianLength?.toFixed(4));
			console.log('  mmPerNormalized:', mmPerNormalized, '(prelim:', prelimMmPerNorm, ')');
			console.log('  cleaned墙段:', cleaned.length, '| zoneSource:', zoneSource.length, '| wallElements:', wallElements.length);
			console.log('  focusCandidateBox:', focusCandidateBoxInContent ? `x=${focusCandidateBoxInContent.x.toFixed(3)} y=${focusCandidateBoxInContent.y.toFixed(3)} w=${focusCandidateBoxInContent.w.toFixed(3)} h=${focusCandidateBoxInContent.h.toFixed(3)}` : 'none');
			console.log('  focusedRawSegments:', (focusCandidateBoxInContent && traceResult.focus?.focused) ? 'focus-scoped' : 'full-region');
			// filledRect 在 focusedRaw 里的数量（关键：柱子能不能被柱管道拿到）
			const frInFocus = regionRawSegments.filter((s) => s.pathKind === 'filledRect');
			const frColSize = frInFocus.filter((s) => { const w = Math.abs(s.x2 - s.x1); const h = Math.abs(s.y2 - s.y1); return w >= 0.006 && h >= 0.006 && w <= 0.055 && h <= 0.055; });
			console.log('  regionRaw中filledRect:', frInFocus.length, '| 符合柱尺寸:', frColSize.length);
			if (frColSize.length > 0) console.log('  柱候选尺寸(mm):', frColSize.slice(0, 8).map((s) => `${Math.round(Math.abs(s.x2-s.x1)*mmPerNormalized)}x${Math.round(Math.abs(s.y2-s.y1)*mmPerNormalized)}`));
			console.log('===============================================\n');
		}
		// ── §3 结束 ──────────────────────────────────────────────────────────────
		// ─── 柱：四阶段管道（候选生成 → 墙厚突变 → 节点探测 → 验证分类）───
		// 先构建内容空间 wallGraph 用于柱验证（后面 rebase 后会再构建正式 wallGraph）
		const contentWallGraph = buildWallGraphDraft(wallElements, mmPerNormalized);

		// ─── Grid Prior Engine：利用 dashPattern / 文字 / 圆圈检测轴网先验 ───
		const focusRegionForGrid = focusCandidateBoxInContent ?? { x: 0, y: 0, w: 1, h: 1 };
		const focusBoundsForGrid = { minX: focusRegionForGrid.x, maxX: focusRegionForGrid.x + focusRegionForGrid.w, minY: focusRegionForGrid.y, maxY: focusRegionForGrid.y + focusRegionForGrid.h };
		const gridPrior = runGridPriorEngine(regionRawSegments, classifiedTexts, detectedCircles, focusBoundsForGrid, mmPerNormalized);

		// ─── 墙体验证管道：类型分类 + 评审问题 ───
		const wallPipeline = runWallVerificationPipeline(wallElements, contentWallGraph, gridPrior, mmPerNormalized, focusBoundsForGrid);

		const columnPipeline = runColumnDetectionPipeline(
			zoneSource,
			focusedRawSegments,
			wallElements,
			contentWallGraph,
			mmPerNormalized,
			gridPrior,
			// missing 时比例尺为默认字面量，对大结构柱使用宽松尺寸上限；有标注或 LLM 估算时视为已标定
			scaleEvidenceSource !== 'missing',
			pdfPageAspectYX ?? 1.0
		);

		// ── 诊断日志 §4：柱管道结果 ────────────────────────────────────────────
		if (source === 'pdf' && process.env.NODE_ENV !== 'production') {
			console.log('\n========== [PDF诊断] §4 柱管道 ==========');
			// 轴网先验
			console.log('  gridPrior: axes=', gridPrior?.axes.length ?? 0, '| intersections=', (gridPrior as any)?.intersections?.length ?? 0, '| probableColumnNodes=', gridPrior?.probableColumnNodes.length ?? 0);
			// WallGraph joints
			console.log('  wallGraph.joints:', contentWallGraph.joints.length, '| joints-type分布:', contentWallGraph.joints.reduce((a, j) => { a[j.type] = (a[j.type] ?? 0) + 1; return a; }, {} as Record<string, number>));
			// focusedRaw 中 filledRect
			const frFocus = focusedRawSegments.filter((s) => s.pathKind === 'filledRect');
			const frFocusBig = frFocus.filter((s) => { const w = Math.abs(s.x2-s.x1); const h = Math.abs(s.y2-s.y1); return w > 0.055 || h > 0.055; });
			const frFocusNorm = frFocus.filter((s) => { const w = Math.abs(s.x2-s.x1); const h = Math.abs(s.y2-s.y1); return w >= 0.006 && h >= 0.006 && w <= 0.055 && h <= 0.055; });
			console.log('  focusedRaw filledRect总数:', frFocus.length, '| 尺寸合规:', frFocusNorm.length, '| 超大(合并块):', frFocusBig.length);
			if (frFocusBig.length > 0) console.log('  超大filledRect前5尺寸:', frFocusBig.slice(0, 5).map((s) => `${Math.round(Math.abs(s.x2-s.x1)*mmPerNormalized)}x${Math.round(Math.abs(s.y2-s.y1)*mmPerNormalized)}mm`));
			// 柱结果
			console.log('  columnPipeline.columns:', columnPipeline.columns.length);
			if (columnPipeline.columns.length > 0) {
				console.log('  柱列表(前10):', columnPipeline.columns.slice(0, 10).map((c) => `${c.label} conf=${c.confidence.toFixed(2)} ${Math.round(c.w*mmPerNormalized)}x${Math.round(c.h*mmPerNormalized)}mm`));
			} else {
				console.log('  ⚠️  柱=0！检查上游 filledRect 是否进入 focusedRawSegments');
				console.log('  focusedRawSegments中filledRect:', focusedRawSegments.filter((s) => s.pathKind === 'filledRect').length);
			}
			console.log('  reviewIssues:', columnPipeline.reviewIssues.length);
			console.log('==========================================\n');
		}
		// ── §4 结束 ──────────────────────────────────────────────────────────────
		// ─── 幕墙检测：先于窗户，建立排斥区域 ───
		const curtainWallElements = detectCurtainWallSegments(focusedRawSegments, wallElements, mmPerNormalized);

		// ─── 门窗：均使用 focusedRawSegments，不再用 zoneSource（墙中心线不含窗格线）───
		const doorElements = buildDoorCandidates(focusedRawSegments, wallElements, mmPerNormalized);
		const windowElements = buildWindowCandidates(focusedRawSegments, wallElements, mmPerNormalized, curtainWallElements);

		// ─── 门垛（门栋）后置排除：aspect ≥ 2.2 的细长件若紧邻门弧则为门垛，移除 ────
		// 注意：aspect ≥ 2.2 的柱在前面的形态硬过滤中已被剔除，此处针对边界案例
		// （aspect 在 1.8~2.2 之间且其实就是门垛的情况）做额外兜底：
		//   近似方形（aspect < 1.8）→ 不管距门多近，属于框架结构柱，保留
		//   细长（aspect ≥ 1.8）且 与门弧距离 < 600mm → 门垛，排除
		const _doorPierProxNorm = 600 / mmPerNormalized; // 600mm 搜索半径（归一化）
		const columnElementsFiltered = columnPipeline.columns.filter((col) => {
			const colWidthMm2 = col.w * mmPerNormalized;
			const colDepthMm2 = col.h * mmPerNormalized * (pdfPageAspectYX ?? 1.0);
			const colAspect = Math.max(colWidthMm2, colDepthMm2) / Math.max(Math.min(colWidthMm2, colDepthMm2), 1);
			// 近似方形（aspect < 1.8）→ 结构柱，无论是否在门旁都保留
			if (colAspect < 1.8) return true;
			// 细长（aspect ≥ 1.8）→ 检查是否紧邻门弧
			const ccx = col.x + col.w / 2;
			const ccy = col.y + col.h / 2;
			const nearDoor = doorElements.some((door) => {
				const ddx = ccx - (door.x + door.w / 2);
				const ddy = ccy - (door.y + door.h / 2);
				return Math.hypot(ddx, ddy) < _doorPierProxNorm;
			});
			// 紧邻门弧 → 门垛，排除；否则保留（可能是非门口边的细长结构柱，如电梯井边柱）
			return !nearDoor;
		});

		// ─── 柱间推断墙（新架构核心）─────────────────────────────────────────────
		// 设计原则：
		//   1. 墙是连续的全跨元素（柱面→柱面），而非线段碎片集合
		//   2. 柱（框架结构锚点）定义墙的起始与终止节点
		//   3. 门窗是"开在墙上的洞"，必须先有墙才能绑定门窗
		// 解决问题：外墙线被 classifySegment 长度截断后大量缺失 → 29 个窗 100% host_wall_unbound
		// 此通道用已确认的柱对推断全跨墙体，补充到 effectiveWallElements 用于绑定验证
		const columnInferredWalls = (() => {
			if (columnElementsFiltered.length < 2) return [] as TraceElement[];
			const CI_TRACK_TOL = 200 / mmPerNormalized;   // 200mm 对齐容差
			const CI_MAX_SPAN  = 12000 / mmPerNormalized; // 最大开间 12m
			const CI_MIN_SPAN  = 150 / mmPerNormalized;   // 柱间净距 ≥ 150mm 才有墙
			const CI_THICK     = Math.max(0.008, 200 / mmPerNormalized); // 默认200mm墙厚
			const colData = columnElementsFiltered.map((c) => ({ el: c, cx: c.x + c.w / 2, cy: c.y + c.h / 2 }));
			const inferred: TraceElement[] = [];
			let ciIdx = 0;
			const tryAdd = (x: number, y: number, w: number, h: number, horiz: boolean) => {
				const span = horiz ? w : h;
				if (span < CI_MIN_SPAN || span > CI_MAX_SPAN) return;
				// 已有线路检测墙覆盖 > 60% → 跳过（不重复）
				const alreadyCovered = wallElements.some((ew) => {
					const ewH = ew.w >= ew.h * 1.5;
					if (horiz !== ewH) return false;
					if (horiz) {
						if (Math.abs((ew.y + ew.h / 2) - (y + h / 2)) > CI_TRACK_TOL) return false;
						const ov = Math.min(ew.x + ew.w, x + w) - Math.max(ew.x, x);
						return ov / w > 0.60;
					}
					if (Math.abs((ew.x + ew.w / 2) - (x + w / 2)) > CI_TRACK_TOL) return false;
					const ov = Math.min(ew.y + ew.h, y + h) - Math.max(ew.y, y);
					return ov / h > 0.60;
				});
				if (alreadyCovered) return;
				inferred.push({
					id: `col-inferred-wall-${ciIdx++}`,
					kind: 'wall_trace' as const,
					label: '柱间推断墙',
					geometryType: 'rect' as const,
					x, y, w, h,
					widthMm: Math.round(span * mmPerNormalized),
					depthMm: Math.round(CI_THICK * mmPerNormalized),
					confidence: 0.65,
					status: 'candidate' as const,
				});
			};
			// 水平对齐柱对 → 水平墙（柱右面到下一柱左面）
			const sortedByY = [...colData].sort((a, b) => a.cy - b.cy);
			const hRows: (typeof colData)[] = [];
			sortedByY.forEach((c) => {
				const row = hRows.find((r) => Math.abs(r[0].cy - c.cy) <= CI_TRACK_TOL);
				if (row) row.push(c); else hRows.push([c]);
			});
			hRows.forEach((row) => {
				row.sort((a, b) => a.cx - b.cx);
				for (let i = 0; i < row.length - 1; i++) {
					const a = row[i]; const b = row[i + 1];
					const wx = a.el.x + a.el.w;
					const ww = b.el.x - wx;
					tryAdd(wx, (a.cy + b.cy) / 2 - CI_THICK / 2, ww, CI_THICK, true);
				}
			});
			// 垂直对齐柱对 → 垂直墙（柱底面到下一柱顶面）
			const sortedByX = [...colData].sort((a, b) => a.cx - b.cx);
			const vCols: (typeof colData)[] = [];
			sortedByX.forEach((c) => {
				const vc = vCols.find((r) => Math.abs(r[0].cx - c.cx) <= CI_TRACK_TOL);
				if (vc) vc.push(c); else vCols.push([c]);
			});
			vCols.forEach((col) => {
				col.sort((a, b) => a.cy - b.cy);
				for (let i = 0; i < col.length - 1; i++) {
					const a = col[i]; const b = col[i + 1];
					const wy = a.el.y + a.el.h;
					const wh = b.el.y - wy;
					tryAdd((a.cx + b.cx) / 2 - CI_THICK / 2, wy, CI_THICK, wh, false);
				}
			});
			if (process.env.NODE_ENV !== 'production') {
				console.log(`[柱间推断墙] columns:${columnElementsFiltered.length} hRows:${hRows.length} vCols:${vCols.length} → inferred:${inferred.length}`);
			}
			return inferred;
		})();
		// effectiveWallElements = 线路检测墙 + 柱间推断墙，用于后续所有绑定验证
		const effectiveWallElements = columnInferredWalls.length > 0
			? [...wallElements, ...columnInferredWalls]
			: wallElements;

		// ─── 同轴连贯墙体组装 ────────────────────────────────────────────────────
		// 建筑原则：墙是连续全跨元素，门/窗是嵌入墙体的开口而非打断墙体的节点
		// assembleWallStrips 将同一轴线方向的墙段（含推断墙）合并为单一连贯矩形
		// 门窗洞口（间距 ≤ 3500mm）的空隙被"桥接"，结果墙 bbox 覆盖洞口位置
		const assembledWallElements = assembleWallStrips(effectiveWallElements, mmPerNormalized);
		if (process.env.NODE_ENV !== 'production') {
			console.log(`\n[墙体组装] effectiveWalls:${effectiveWallElements.length} → assembledStrips:${assembledWallElements.length}`);
		}

		// ─── 柱-墙融合：与墙等宽的构造柱/壁柱并入墙体 ─────────────────────────
		// 判定：elongated 柱（长短边比 > 1.8）且短边 ≈ 相邻墙厚（±45%）→ 并入墙体
		// 方形框架柱（比例接近 1:1）不吸收，保持独立显示
		const absorbedColumnIds = new Set<string>();
		if (assembledWallElements.length > 0) {
			assembledWallElements.forEach(wall => {
				const wallH = wall.w >= wall.h * 1.5;
				const wallThick = wallH ? wall.h : wall.w;
				const wallStart = wallH ? wall.x : wall.y;
				const wallEnd   = wallH ? wall.x + wall.w : wall.y + wall.h;
				const wallTrack = wallH ? wall.y + wall.h / 2 : wall.x + wall.w / 2;
				columnElementsFiltered.forEach(col => {
					if (absorbedColumnIds.has(col.id)) return;
					const colNarrow = Math.min(col.w, col.h);
					const colAspect = Math.max(col.w, col.h) / Math.max(colNarrow, 0.0001);
					if (colAspect < 1.8) return; // 方形框架柱不吸收
					if (colNarrow < wallThick * 0.55 || colNarrow > wallThick * 1.45) return;
					const colH = col.w >= col.h;
					if (colH !== wallH) return;
					const colTrack = wallH ? col.y + col.h / 2 : col.x + col.w / 2;
					if (Math.abs(colTrack - wallTrack) > wallThick * 1.5) return;
					const colStart = wallH ? col.x : col.y;
					const colEnd   = wallH ? col.x + col.w : col.y + col.h;
					if (colEnd < wallStart - wallThick || colStart > wallEnd + wallThick) return;
					absorbedColumnIds.add(col.id); // 壁柱/构造柱 → 吸收入墙
				});
			});
		}
		const columnElementsFinal = absorbedColumnIds.size > 0
			? columnElementsFiltered.filter(c => !absorbedColumnIds.has(c.id))
			: columnElementsFiltered;
		if (process.env.NODE_ENV !== 'production' && absorbedColumnIds.size > 0) {
			console.log(`[柱-墙融合] absorbed:${absorbedColumnIds.size} remaining:${columnElementsFinal.length}`);
		}

		// ─── 开口验证管道：类型分类 + 评审问题 ───
		const contentWallGaps = detectWallGaps(contentWallGraph, assembledWallElements, mmPerNormalized);
		const openingPipeline = runOpeningVerificationPipeline(doorElements, contentWallGraph, contentWallGaps, focusedRawSegments, assembledWallElements, mmPerNormalized);

		// ─── 窗户验证管道 ───
		const windowPipelineResult = runWindowVerificationPipeline(windowElements, focusedRawSegments, assembledWallElements, curtainWallElements, mmPerNormalized);

		// ─── 幕墙验证管道 ───
		const curtainWallPipeline = runCurtainWallVerificationPipeline(curtainWallElements, focusedRawSegments, assembledWallElements, mmPerNormalized);

		// ─── 空间区域验证管道（电梯/楼梯/管井/设备间/核心筒） ───
		const zonePipeline = runZoneVerificationPipeline(spaceElements, focusedRawSegments, assembledWallElements, classifiedTexts, mmPerNormalized);

		const rawElements = [...assembledWallElements, ...spaceElements, ...columnElementsFinal, ...doorElements, ...windowElements, ...curtainWallElements];
		const contentCoordinateBox = { x: 0, y: 0, w: 1, h: 1 };
		const sourceContentBox = contentBox ?? { x: 0, y: 0, w: 1, h: 1 };
		const elements = attachPageCoordinateProvenance(
			rebaseElementsToMainPlan(rawElements, contentCoordinateBox, contentSpaceMainPlanBox),
			sourceContentBox
		);
		// ── 页面宽高比修正：Y 轴归一化基数为 viewport.height，X 轴为 viewport.width，
		//    对非正方形 PDF 页 depthMm = h × mmPerNormX 会系统偏小/大。
		//    在输出前乘以 pageAspectYX 修正（不影响任何门禁/过滤逻辑，仅修正尺寸显示值）。
		if (pdfPageAspectYX && Number.isFinite(pdfPageAspectYX) && Math.abs(pdfPageAspectYX - 1) > 0.02) {
			for (const el of elements) {
				if (el.depthMm !== undefined && el.depthMm > 0) {
					el.depthMm = Math.round(el.depthMm * pdfPageAspectYX);
				}
			}
		}
		const rebasedDimensions = scaleEvidenceDimensions.map((mark) => ({ ...mark, ...mapPointBetweenBoxes(mark, contentCoordinateBox, contentSpaceMainPlanBox) }))
			.filter((mark) => mark.x >= 0 && mark.x <= 1 && mark.y >= 0 && mark.y <= 1);
		const issues = buildIssues(elements, rebasedDimensions.length);
		const quality = buildQualityScore(elements, rebasedDimensions.length, issues);
		const floorPlanIR = buildFloorPlanIR(safeName, source, { x: 0, y: 0, w: 1, h: 1 }, elements, scaleEvidenceDimensions, mmPerNormalized, issues, zonePipeline.coreZones);
		const mainPlanBox = source === 'pdf' ? regionFromContentToPage(contentSpaceMainPlanBox, sourceContentBox) : contentSpaceMainPlanBox;
		const recognitionBoxOnPage = source === 'pdf' ? regionFromContentToPage(recognitionRegion, sourceContentBox) : recognitionRegion;
		// 门禁几何判定使用重映射前的内容坐标，避免 main_plan_box 各轴独立归一化带来的横竖尺度漂移。
		const gateElements = rawElements;
		const wallGraph = buildWallGraphDraft(gateElements, mmPerNormalized);
		// carrier:bound 由前端传入 buildingCarrierRef 后拼入，用于 Bug4 的 source-draft 条件判断
		const carrierSegment = (typeof parsedBody.buildingCarrierRef === 'string' && parsedBody.buildingCarrierRef.trim())
			? 'carrier:bound'
			: 'carrier:draft';
		const compilerMode = `${traceResult.mode};scale:${scaleEvidenceSource};mainplan:${mainPlanBoxSource};${carrierSegment}`;
		const gateBundle = buildGateResult(wallGraph, gateElements, scaleEvidenceDimensions, contentSpaceMainPlanBox, compilerMode, columnPipeline.reviewIssues, wallPipeline.reviewIssues, openingPipeline.reviewIssues, windowPipelineResult.reviewIssues, curtainWallPipeline.reviewIssues, zonePipeline.reviewIssues, mmPerNormalized);
		const coordinateGate = buildCoordinateConsistencyGate(gateElements);
		const structureBackboneGate = buildStructureBackboneGate(wallGraph, gateElements, gridPrior, mmPerNormalized);

		// ── Parser Gate：原语保真检查 ─────────────────────────────────────────
		const parserGate = buildParserGate({
			rawSegments: regionRawSegments,
			fillOperationCount: source === 'pdf' ? (traceResult as any).pathFillSetSize ?? 0 : 0,
			sourceType: source as 'pdf' | 'dxf',
		});

		// ── Scale Gate：三档比例尺治理 ────────────────────────────────────────
		const scaleGate = buildScaleGate({
			scaleEvidenceSource,
			scaleEvidenceDimensions,
			mmPerNormalized,
			prelimMmPerNorm,
		});

		// ── CarrierBaselineIR：结构底座最小版本 ───────────────────────────────
		const carrierBaseline = buildCarrierBaselineIR(
			regionRawSegments,
			gateElements.filter((e) => e.kind === 'wall_trace'),
			gateElements.filter((e) => e.kind === 'column'),
			mmPerNormalized,
			(scaleGate as any).tier as ScaleConfidenceTier ?? 'unknown',
		);
		const carrierGate = buildCarrierGate(carrierBaseline);

		const promotionBlockers = [
			...(parserGate.status === 'passed' ? [] : ['Parser Gate 未通过（原语保真失败）']),
			...(carrierGate.status === 'passed' ? [] : ['Carrier Gate 未通过（结构底座证据不足）']),
			...(gateBundle.contract.status === 'passed' ? [] : ['Contract Gate 未通过']),
			...(coordinateGate.status === 'passed' ? [] : ['坐标一致性未通过']),
			...(structureBackboneGate.status === 'passed' ? [] : ['结构主干未通过']),
			...(gateBundle.geometry.status === 'passed' ? [] : ['Geometry Gate 未通过']),
			...(gateBundle.system.status === 'passed' ? [] : ['System Gate 未通过']),
			...(mainPlanBoxSource !== 'fallback_recognition_region' ? [] : ['mainPlanBox 仍为识别区回退']),
		];
		const formalPromotionAllowed = promotionBlockers.length === 0;
		const debugLayerRefs = {
			regionScoped: primitiveRefsFromSegments(traceResult.debugSegments?.regionScoped ?? [], 180, contentCoordinateBox, contentSpaceMainPlanBox),
			classifiedWall: primitiveRefsFromSegments(traceResult.debugSegments?.classifiedWall ?? [], 180, contentCoordinateBox, contentSpaceMainPlanBox),
			focusedWall: primitiveRefsFromSegments(traceResult.debugSegments?.focusedWall ?? [], 180, contentCoordinateBox, contentSpaceMainPlanBox),
			strictMerged: primitiveRefsFromSegments(traceResult.debugSegments?.strictMerged ?? [], 140, contentCoordinateBox, contentSpaceMainPlanBox),
			pairedWalls: primitiveRefsFromSegments(traceResult.debugSegments?.pairedWalls ?? [], 140, contentCoordinateBox, contentSpaceMainPlanBox),
			relaxedCandidates: primitiveRefsFromSegments(traceResult.debugSegments?.relaxedCandidates ?? [], 180, contentCoordinateBox, contentSpaceMainPlanBox),
			relaxedMerged: primitiveRefsFromSegments(traceResult.debugSegments?.relaxedMerged ?? [], 140, contentCoordinateBox, contentSpaceMainPlanBox),
			cleaned: primitiveRefsFromSegments(cleaned, 140, contentCoordinateBox, contentSpaceMainPlanBox),
		};
		const compileResult: FloorPlanCompileResult = {
			status: formalPromotionAllowed ? 'ir_ready' : 'gate_failed',
			baseline: {
				inputType: source,
				pageBox: { x: 0, y: 0, w: 1, h: 1 },
				contentBox: sourceContentBox,
				recognitionBox: recognitionBoxOnPage,
				mainPlanBox,
				mainPlanBoxSource,
				rotationDeg: 0,
				scaleStatus: (() => {
					const scaleKnown = scaleEvidenceDimensions.length >= 2
						&& (scaleEvidenceSource === 'roi' || scaleEvidenceSource === 'main_plan');
					return scaleKnown ? 'known' : scaleEvidenceDimensions.length > 0 ? 'estimated' : 'missing';
				})(),
				unitGuess: 'mm',
				noiseRegions: [],
				confidence: traceResult.focus?.focused ? 0.72 : 0.48,
			},
			detectionLayers: {
				structureLines: primitiveRefsFromSegments(cleaned, 120, contentCoordinateBox, contentSpaceMainPlanBox),
				wallCandidates: elements.filter((element) => element.kind === 'wall_trace'),
				columnCandidates: elements.filter((element) => element.kind === 'column'),
				openingCandidates: elements.filter((element) => element.kind === 'door' || element.kind === 'window'),
				textRegions: [],
				dimensionRegions: [
					...scaleEvidenceDimensions.map((mark, index) => {
						const mapped = mapPointBetweenBoxes(mark, contentCoordinateBox, contentSpaceMainPlanBox);
						return {
						id: `dimension-${index + 1}`,
							kind: `dimension_text_${scaleEvidenceSource}`,
							bbox: [mapped.x - 0.01, mapped.y - 0.01, mapped.x + 0.01, mapped.y + 0.01] as [number, number, number, number],
							confidence: scaleEvidenceSource === 'roi' || scaleEvidenceSource === 'main_plan' ? 0.68 : scaleEvidenceSource === 'missing' ? 0.25 : 0.52,
						};
					}),
					...primitiveRefsByClassification(classifiedRegionSegments, ['dimension'], 50, contentCoordinateBox, contentSpaceMainPlanBox),
				],
				gridRegions: primitiveRefsByClassification(classifiedRegionSegments, ['hatch'], 40, contentCoordinateBox, contentSpaceMainPlanBox),
				symbolRegions: primitiveRefsByClassification(classifiedRegionSegments, ['symbol', 'opening_symbol'], 80, contentCoordinateBox, contentSpaceMainPlanBox),
				regionScopedLines: debugLayerRefs.regionScoped,
				classifiedWallLines: debugLayerRefs.classifiedWall,
				focusedWallLines: debugLayerRefs.focusedWall,
				strictMergedLines: debugLayerRefs.strictMerged,
				pairedWallLines: debugLayerRefs.pairedWalls,
				relaxedCandidateLines: debugLayerRefs.relaxedCandidates,
				relaxedMergedLines: debugLayerRefs.relaxedMerged,
				projectionOutlines: primitiveRefsByClassification(classifiedRegionSegments, ['projection'], 60, contentCoordinateBox, contentSpaceMainPlanBox),
			},
			wallGraph,
			columns: elements.filter((element) => element.kind === 'column'),
			carrierBaseline,
			gates: {
				parser: parserGate,
				scale: scaleGate,
				carrier: carrierGate,
				contract: gateBundle.contract,
				coordinate: coordinateGate,
				structureBackbone: structureBackboneGate,
				geometry: gateBundle.geometry,
				system: gateBundle.system,
			},
			reviewQueue: gateBundle.reviewQueue,
			floorPlanIR: formalPromotionAllowed ? floorPlanIR : undefined,
			formalPromotionAllowed,
			promotionBlockers,
		};
		const issueMessages = Array.from(new Set([
			...traceIssueMessages(issues),
			...Object.values(compileResult.gates).filter((gate): gate is GateResult => Boolean(gate)).flatMap((gate) => gate.issues.map((issue) => issue.message)),
		]));
		return NextResponse.json({
			status: elements.length > 0 ? 'traced' : 'no_result',
			compilerStatus: compileResult.status,
			source,
			message: formalPromotionAllowed
				? `服务端已解析 ${source.toUpperCase()} 矢量线段 ${segments.length} 条，全部门禁通过，输出 Reviewed FloorPlanIR 候选。`
				: `服务端已解析 ${source.toUpperCase()} 矢量线段 ${segments.length} 条，已生成编译候选；${promotionBlockers[0] ?? '门禁未通过'}，暂不进入正式 FloorPlanIR。`,
			elements,
			floorPlanIR: formalPromotionAllowed ? floorPlanIR : undefined,
			draftFloorPlanIR: floorPlanIR,
			compileResult,
			gates: compileResult.gates,
			formalPromotionAllowed,
			promotionBlockers,
			reviewQueue: compileResult.reviewQueue,
			wallGraph,
			quality,
			scaleCalibration: {
				mmPerNormalized,
				source: scaleEvidenceDimensions.length > 0 ? `pdf_text_${scaleEvidenceSource}` : source,
				samples: scaleEvidenceDimensions.length,
				pageAspectYX: pdfPageAspectYX,
			},
			parserDiag: source === 'pdf' ? pdfParserDiag : undefined,
			// Layer 3: LLM 语义骨架摘要（调试 / 前端展示用）
			llmSkeleton: llmSkeleton ? {
				status: llmSkeleton.status,
				wallCount: llmSkeleton.walls.length,
				openingCount: llmSkeleton.openings.length,
				columnCount: llmSkeleton.columns.length,
				scaleHint: llmSkeleton.scale_hint,
				derivedMmPerNorm: llmDerivedMmPerNorm,
			} : undefined,
			normalization: {
				contentBox: sourceContentBox,
				recognitionRegion,
				recognitionBoxOnPage,
				mainPlanBox,
				mainPlanBoxInContent: contentSpaceMainPlanBox,
				mainPlanBoxSource,
				focusBounds: focusCandidateBoxInContent ? (source === 'pdf' ? regionFromContentToPage(focusCandidateBoxInContent, sourceContentBox) : focusCandidateBoxInContent) : undefined,
				focusBoundsInContent: focusCandidateBoxInContent,
				focusUsedAsMainPlanBox,
				coordinateSpace: 'main_plan_box',
			},
			sheetIR: {
				version: 'sheet_ir_v0.1',
				pageBox: { x: 0, y: 0, w: 1, h: 1 },
				contentBox: sourceContentBox,
				recognitionBox: recognitionBoxOnPage,
				mainPlanBox,
				mainPlanBoxInContent: contentSpaceMainPlanBox,
				transform: {
					elementSpace: 'main_plan_box',
					pageToMainPlan: {
						x: mainPlanBox.x,
						y: mainPlanBox.y,
						w: mainPlanBox.w,
						h: mainPlanBox.h,
					},
				},
				gridPrior: gridPrior ? {
					axisCount: gridPrior.axes.length,
					intersectionCount: gridPrior.intersections.length,
					probableColumnNodeCount: gridPrior.probableColumnNodes.length,
					spacingClusters: gridPrior.spacingClusters,
					dominantDirections: gridPrior.dominantDirections,
				} : undefined,
			},
			diagnostics: {
				rawSegments: segments.length,
				scopedSegments: traceResult.scopedSegments,
				wallSegments: elements.filter((element) => element.kind === 'wall_trace').length,
				doorCandidates: elements.filter((element) => element.kind === 'door').length,
				windowCandidates: elements.filter((element) => element.kind === 'window').length,
				columnCandidates: elements.filter((element) => element.kind === 'column').length,
				boundOpenings: floorPlanIR.stats.openingCount,
				filteredOut: Math.max(0, traceResult.scopedSegments - elements.length),
				dimensionsInRegion: scopedDimensions.length,
				scaleEvidenceSource,
				scaleEvidenceSamples: scaleEvidenceDimensions.length,
				pdfCoordinateTransform: source === 'pdf' ? 'ctm_applied' : 'not_applicable',
				closedSpaces: elements.filter((element) => element.kind === 'function_zone').length,
				classCounts: traceResult.classCounts,
				pipelineStats: traceResult.pipelineStats,
				debugLayers: debugLayerRefs,
				debugLayerCounts: Object.fromEntries(Object.entries(debugLayerRefs).map(([key, refs]) => [key, refs.length])),
				mode: traceResult.mode,
				regionFallback: traceResult.regionFallback,
				regionInsufficient: traceResult.regionInsufficient ?? false,
				formalPromotionAllowed,
				promotionBlockers,
				coordinateConsistency: {
					status: coordinateGate.status,
					score: coordinateGate.score,
					metrics: coordinateGate.metrics,
				},
				structureBackbone: {
					status: structureBackboneGate.status,
					score: structureBackboneGate.score,
					metrics: structureBackboneGate.metrics,
				},
				primaryCluster: {
					focused: traceResult.focus?.focused ?? false,
					componentCount: traceResult.focus?.componentCount ?? 1,
					focusBounds: traceFocusBounds,
					focusCandidateBoxInContent,
					focusCandidateBoxOnPage: focusCandidateBoxInContent ? (source === 'pdf' ? regionFromContentToPage(focusCandidateBoxInContent, sourceContentBox) : focusCandidateBoxInContent) : undefined,
					focusUsedAsMainPlanBox,
					mainPlanBoxSource,
				},
				gridPrior: gridPrior ? {
					axes: gridPrior.axes.length,
					intersections: gridPrior.intersections.length,
					probableColumnNodes: gridPrior.probableColumnNodes.length,
					wallAlignmentBands: gridPrior.wallAlignmentBands.length,
					spacingClusters: gridPrior.spacingClusters.length,
					classifiedTexts: classifiedTexts.length,
					detectedCircles: detectedCircles.length,
				} : undefined,
			},
			issues,
			issueMessages,
		});
	} catch (error) {
		console.error('[floor-plan/trace] failed:', error);
		const message = error instanceof Error ? error.message : 'Failed to trace floor plan.';
		return NextResponse.json({ error: message }, { status: 500 });
	}
}
