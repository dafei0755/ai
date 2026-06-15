'use client';

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import type { PointerEvent, WheelEvent } from 'react';
import { getWheelZoomFactor, zoomCanvasViewAt, type CanvasViewTransform } from '@/lib/canvasViewport';
import type { ProjectOverview } from './mock/mockData';
import BubbleZoningDiagram, { type BubbleSelectionInfo } from './BubbleZoningDiagram';
import PlanWorkbenchOverlay from './PlanWorkbenchOverlay';
import { GeoAnchorCard } from '@/components/geo/GeoAnchorCard';
import { GeoScorePanel } from '@/components/geo/GeoScorePanel';
import { GeoThesisCard } from '@/components/geo/GeoThesisCard';
import { useGeoStore } from '@/store/useGeoStore';
import { Check, ChevronDown, ChevronRight, Layers, ListTree, TriangleAlert, X } from 'lucide-react';

interface ProjectGrowthCanvasViewProps {
  overview: ProjectOverview;
  projectLabel?: string;
  tabs?: { key: string; label: string; active: boolean; badge?: string; onClick: () => void }[];
  onAdvisorPrefill?: (text: string) => void;
  /** 会话 id — 用于在平面推演悬浮工作台中挂载 PlanSandboxPanel（需要 sessionId 才能存取草案数据）。 */
  sessionId?: string;
  /** 打开地理工作台回调 */
  onOpenGeoWorkspace?: () => void;
}

type StackLayerId = 'base_conditions' | 'project_definition' | 'spatial_structure' | 'strategy_organization' | 'output_results';
type StackNodeStatus = 'confirmed' | 'draft' | 'hypothesis' | 'blocked' | 'frozen' | 'dismissed';
type StackNodePriority = 'critical';
type PropositionState = 'confirmed' | 'pending' | 'dismissed';
type DragMode = 'pan' | 'tilt';
type PanelSelectionMode = 'layer' | 'node';
type RehearsalScopeStatus = 'confirmed' | 'draft' | 'gap' | 'blocked' | 'frozen';

interface StackLayer {
  id: StackLayerId;
  index: number;
  title: string;
  subtitle: string;
  advisorLine: string;
  maturity: number;
  color: string;
  fill: string;
  sourceObject: string;
}

interface StackNodeDetail {
  heading: string;
  body: string;
}
interface StackNode {
  id: string;
  layerId: StackLayerId;
  label: string;
  x: number;
  y: number;
  size: number;
  status: StackNodeStatus;
  sourceObject: string;
  sourceVersion: string;
  description: string;
  showLabel?: boolean;
  priority?: StackNodePriority;
  /** 子类别 — 一层之内的进一步切分（如 L1 任务侧 / 位置侧 / 对账） */
  category?: string;
  /** 结构化详情 — 该节点对应文档的关键条目 */
  details?: StackNodeDetail[];
  /** 资料 / 对标 / 案例引用 */
  references?: string[];
}

interface RehearsalScope {
  id: string;
  label: string;
  shortLabel: string;
  kind: 'site' | 'zone' | 'building' | 'floor' | 'service';
  x: number;
  y: number;
  w: number;
  h: number;
  color: string;
  maturity: number;
  status: RehearsalScopeStatus;
  buildingIds: string[];
  note: string;
}

interface RehearsalBuilding {
  id: string;
  label: string;
  subtitle: string;
  scopeId: string;
  floors: Array<{
    id: string;
    label: string;
    summary: string;
    maturity: number;
    status: RehearsalScopeStatus;
  }>;
}

interface ProjectedPoint {
  x: number;
  y: number;
}

interface ProjectedLine {
  from: ProjectedPoint;
  to: ProjectedPoint;
}

interface ProjectedNode extends StackNode {
  screen: ProjectedPoint;
}

interface LayerLabelOverlay {
  layer: StackLayer;
  x: number;
  y: number;
  anchorX: number;
  anchorY: number;
  isActive: boolean;
}

interface NodeLabelOverlay {
  node: ProjectedNode;
  label: string;
  x: number;
  y: number;
  isActiveLayer: boolean;
  detailLevel: 'compact' | 'normal' | 'rail' | 'list';
}

interface LabelBox {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

interface LabelCandidate {
  dx: number;
  dy: number;
  anchor: 'left' | 'right' | 'center';
}

const VIEW_W = 1600;
const VIEW_H = 920;
const PLANE_SIZE = 540;        // 扩大平面尺寸，使堆栈在画布中占更大比例（原 390）
const PLANE_PROJECT_SCALE = 0.72;
const OVERVIEW_CENTER_X = 800; // 居中于 1600-wide viewBox（原 690，偏左）
const OVERVIEW_BASE_Y = 980;
const FOCUSED_UPPER_LAYER_GAP = 194;
const MIN_CANVAS_ZOOM = 0.50;  // 允许更大范围缩小（原 0.68）
const MAX_CANVAS_ZOOM = 3.52;
const DEFAULT_ACTIVE_LAYER_ID: StackLayerId = 'project_definition';
const TWO_D_NODE_ROWS_PER_COLUMN = 5;
const TWO_D_NODE_ROW_GAP = 40;
const TWO_D_NODE_COLUMN_GAP = 220;
const TWO_D_NODE_LABEL_WIDTH = 180;
const TWO_D_NODE_LABEL_HEIGHT = 26;
const TWO_D_NODE_LABEL_OFFSET_X = 16;
const PROJECT_STACK_3D_LABEL_RAIL_WIDTH = 220;
const PROJECT_STACK_3D_LABEL_RAIL_HEIGHT = 28;
const PROJECT_STACK_3D_LABEL_RAIL_ROW_GAP = 38;
const PROJECT_STACK_3D_LABEL_RAIL_COLUMN_GAP = 292;
const PROJECT_STACK_3D_LABEL_RAIL_INSET_X = 52;
const PROJECT_STACK_3D_LABEL_MAX_CHARS = 14;
const TWO_D_NODE_START_OFFSET_X = -320;
const TWO_D_NODE_START_OFFSET_Y = 38;
const TWO_D_LAYER_TOP_Y = 20;
const TWO_D_LAYER_GAP = 220;
const PROJECT_STACK_LEFT_INSET = 80;
const PROJECT_STACK_LAYER_LABEL_WIDTH = 180;
const PROJECT_STACK_LABEL_TO_CONTENT_GAP = 48;
const PROJECT_STACK_FIXED_LABEL_SCALE = 1.12;
const PROJECT_STACK_SVG_LAYER_METER_WIDTH = PROJECT_STACK_LAYER_LABEL_WIDTH / PROJECT_STACK_FIXED_LABEL_SCALE;
const INITIAL_STACK_CANVAS_ZOOM = 0.92;
const INITIAL_STACK_CANVAS_Y = 0;
const PROJECT_STACK_PLANE_LEFT_X = OVERVIEW_CENTER_X - PLANE_SIZE * PLANE_PROJECT_SCALE;
const INITIAL_STACK_CANVAS_VIEW: CanvasViewTransform = { x: 132, y: INITIAL_STACK_CANVAS_Y, zoom: INITIAL_STACK_CANVAS_ZOOM };
const INITIAL_STACK_VIEW_PADDING = {
  left: PROJECT_STACK_LEFT_INSET,
  right: 18,
  top: 86,
  bottom: 54,
};
const NODE_LABEL_SAFE_AREA = {
  left: PROJECT_STACK_LEFT_INSET,
  top: 82,
  right: 26,
  bottom: 76,
};
const NODE_LABEL_CANDIDATES: LabelCandidate[] = [
  { dx: 28, dy: -18, anchor: 'left' },
  { dx: 28, dy: 6, anchor: 'left' },
  { dx: -28, dy: -18, anchor: 'right' },
  { dx: -28, dy: 6, anchor: 'right' },
  { dx: 0, dy: -38, anchor: 'center' },
  { dx: 0, dy: 28, anchor: 'center' },
  { dx: 34, dy: -40, anchor: 'left' },
  { dx: -34, dy: -40, anchor: 'right' },
];
const REHEARSAL_ZONE = {
  x: 1220, // 右移以避免与扩大后的平面（右边界约 1189）重叠（原 1120）
  y: 140,
  w: 760,
  h: 1400,
};

// ── 项目认知五层模型（v1.2，2026-05-07 裁决）──────────────────────────────
//   旧"底层条件 / 项目定义 / 空间结构 / 策略组织 / 输出成果"已正式废弃。
//   新五层不是流程标签，而是项目认知操作系统：
//     L1 让项目落在地方，L2 让项目落在建筑，L3 让项目落在人和经营，
//     L4 让项目落在设计语言，L5 让项目落在推演、表达、回写和交付闭环。
//   一句话：L1 是问，L2 是约，L3 是人，L4 是译，L5 是投。
//
//   id 字段保持原英文 key（base_conditions / project_definition / ...）以兼容
//   既有路由和持久化数据；用户可见命名全部更新。
const STACK_LAYERS: StackLayer[] = [
  {
    id: 'base_conditions',
    index: 0,
    title: 'L1 场所与任务',
    subtitle: '需求预判',
    advisorLine: '任务与位置对账',
    maturity: 0.66,
    color: '#4fb38a',
    fill: 'rgba(79,179,138,0.46)',
    sourceObject: 'DemandSnapshot + SiteContext',
  },
  {
    id: 'project_definition',
    index: 1,
    title: 'L2 建筑与边界',
    subtitle: '建筑承载',
    advisorLine: '建筑客观约束',
    maturity: 0.72,
    color: '#6aa8ff',
    fill: 'rgba(106,168,255,0.46)',
    sourceObject: 'FloorPlanAsset + FloorPlanIR',
  },
  {
    id: 'spatial_structure',
    index: 2,
    title: 'L3 人群与场景',
    subtitle: '行为运营',
    advisorLine: '人群体流与体验设定',
    maturity: 0.44,
    color: '#f0b35a',
    fill: 'rgba(240,179,90,0.48)',
    sourceObject: 'ActorScenarioOperation',
  },
  {
    id: 'strategy_organization',
    index: 3,
    title: 'L4 策略与语言',
    subtitle: '设计转化',
    advisorLine: '空间组织与落地控制',
    maturity: 0.58,
    color: '#df6fa6',
    fill: 'rgba(223,111,166,0.46)',
    sourceObject: 'DesignTranslationStrategy',
  },
  {
    id: 'output_results',
    index: 4,
    title: 'L5 推演与成果',
    subtitle: '决策汇总',
    advisorLine: '推演结果与文档归档',
    maturity: 0.36,
    color: '#b59cff',
    fill: 'rgba(181,156,255,0.46)',
    sourceObject: 'PSC + FFL + BubblePlanLogic + LayoutScopeIndex',
  },
];
const PROJECT_STACK_CONFIRMED_COLOR = 'rgb(74, 222, 128)';

const getTwoDLayerPoint = (layer: StackLayer): ProjectedPoint => ({
  x: OVERVIEW_CENTER_X,
  y: TWO_D_LAYER_TOP_Y + (STACK_LAYERS.length - 1 - layer.index) * TWO_D_LAYER_GAP,
});

function getInitialStackCanvasView(svgViewScale: number, svgViewOffsetX = 0): CanvasViewTransform {
  const targetContentLeft =
    (PROJECT_STACK_LEFT_INSET + PROJECT_STACK_LAYER_LABEL_WIDTH + PROJECT_STACK_LABEL_TO_CONTENT_GAP - svgViewOffsetX) /
    Math.max(svgViewScale, 0.001);

  return {
    x: targetContentLeft - PROJECT_STACK_PLANE_LEFT_X * INITIAL_STACK_CANVAS_ZOOM,
    y: INITIAL_STACK_CANVAS_Y,
    zoom: INITIAL_STACK_CANVAS_ZOOM,
  };
}

// ── 项目认知五层 demo 节点（HAY 七里坪山地民宿）────────────────────────────
//   每个节点 = 一份设计资料库里的具体文档 / 判断 / 索引。
//   依据文档：《01-项目底盘的输入.md v0.2》《05-07-五层模型交叉校验 v1.0》
//   demo 项目：HAY 气质 × 峨眉山七里坪 × 山地轻度假民宿（约 2,400㎡ · 12 客房）
//   各层语义：
//     L1 任务 × 位置耦合（Demand × Supply 对账）
//     L2 建筑事实 / 不可改约束 / 硫酸纸底层
//     L3 人群 · 行为 · 运营 · 空间剧本
//     L4 L4a 空间组织 + L4b 表达策略 + L4c 落地控制 三轨
//     L5 推演接口 / 投射动作 / 集成状态 / 回写闸门
const STACK_NODES: StackNode[] = [
  // ══════════════════════════════════════════════════════════════════════
  // L1 场所与任务（base_conditions）— 8 节点：3 任务 + 3 位置 + 2 对账
  // ══════════════════════════════════════════════════════════════════════
  {
    id: 'demand_program', layerId: 'base_conditions',
    label: '业态 · 山地轻度假民宿',
    x: -220, y: -78, size: 19, status: 'confirmed',
    sourceObject: 'DemandSnapshot.program', sourceVersion: 'brief_v0.2',
    description: 'HAY 气质 × 山地轻度假 × 周末市场。约 2,400㎡，12 客房目标，单房经营效率敏感。',
    showLabel: true,
    category: '任务侧 · 业态目标',
    details: [
      { heading: '类型定位', body: '中端山地民宿（房价 800-1,500 元区间），主打周末短住与轻社交。' },
      { heading: '核心 KPI', body: '入住率 60%+ / 客单价 1,100 / NPS 45+ / 复购 35%。' },
      { heading: '差异化主张', body: '不做网红打卡，做"耐看、可经营"的山地停留。' },
    ],
    references: ['HAY 设计语言案例集', '莫干山轻度假民宿对标 ×12'],
  },
  {
    id: 'demand_operation', layerId: 'base_conditions',
    label: '经营模型 · 自营轻团队',
    x: -228, y: -10, size: 16, status: 'draft',
    sourceObject: 'DemandSnapshot.operation', sourceVersion: 'brief_v0.2',
    description: '业主自营 · 4-6 人小团队 · 季节性运营。重餐饮配套 + 轻社交活动。',
    category: '任务侧 · 经营意图',
    details: [
      { heading: '运营形态', body: '自营，未来不排除托管。前台非常驻，管家轮值。' },
      { heading: '餐饮配置', body: '早餐自助 + 简餐 + 山野下午茶；不做正餐。' },
      { heading: '团队结构', body: '主理 1 + 管家 2 + 厨房 1 + 维护 1 + 兼职 1-2。' },
    ],
    references: ['同尺度自营民宿运营成本结构 (CASE_07)'],
  },
  {
    id: 'demand_budget_time', layerId: 'base_conditions',
    label: '预算与时间窗口',
    x: -210, y: 48, size: 15, status: 'draft',
    sourceObject: 'DemandSnapshot.constraints', sourceVersion: 'brief_v0.2',
    description: '总投资 800-1,200 万浮动 · 工期目标 12 个月 · 雨季施工避让 · 旺季前开业。',
    category: '任务侧 · 资源约束',
    details: [
      { heading: '改造强度倾向', body: '允许局部重点投入，整体保守低改造。' },
      { heading: '预算敏感度', body: '中-高（业主反复说"不能失控"）。' },
      { heading: '时间窗口', body: '次年 4 月开业（雨季前）；可分阶段实施。' },
    ],
    references: ['项目底盘输入 v0.2 §8.4 资源与限制'],
  },
  {
    id: 'site_geo', layerId: 'base_conditions',
    label: '七里坪地理坐标',
    x: 218, y: -82, size: 20, status: 'confirmed',
    sourceObject: 'SiteContext.geo.coordinates', sourceVersion: 'site_v0.2',
    description: '峨眉山七里坪 · 海拔 1,300m · 川西山地。位置不可移动，是项目最稀缺资产。',
    showLabel: true,
    priority: 'critical',
    category: '位置侧 · GeoContext',
    details: [
      { heading: '坐标精度', body: '场地级（地图点选 + 边界标注完整）。' },
      { heading: '地形分类', body: 'mid_mountain · terrain=mountain · slope_terrain' },
      { heading: '可达性', body: '自驾 3.5h（成都），高铁 2h + 区间车 1h。无机场。' },
    ],
    references: ['ProjectContextCompiler v0.2', 'GeoContext schema'],
  },
  {
    id: 'site_natural', layerId: 'base_conditions',
    label: '山地自然环境',
    x: 232, y: -18, size: 18, status: 'confirmed',
    sourceObject: 'SiteContext.geo.environment', sourceVersion: 'site_v0.2',
    description: '高湿亚热带山林 · 雨季 4-9 月 · 平均湿度 78% · 主景观面金顶方向（南偏东 25°）。',
    category: '位置侧 · 自然维度',
    details: [
      { heading: '气候带', body: '亚热带山地湿润季风气候 · 凉夏 · 多雾。' },
      { heading: '景观资源', body: '南向金顶视野 · 北向坡地森林 · 东西向村落屋顶。' },
      { heading: '约束风险', body: '高湿 → 防潮材料、除湿设备、气味与维护成本。' },
    ],
    references: ['项目底盘输入 v0.2 §5.1 GeoContext'],
  },
  {
    id: 'site_culture_market', layerId: 'base_conditions',
    label: '在地文化与市场',
    x: 200, y: 50, size: 16, status: 'draft',
    sourceObject: 'SiteContext.culture+market', sourceVersion: 'site_v0.2',
    description: '川西山地民俗 + 峨眉佛教文化背景。5km 内 27 家民宿，价格段 400-2,000，竞品偏景观主题。',
    category: '位置侧 · 人文 + 市场',
    details: [
      { heading: '在地文化锚点', body: '峨眉佛教 · 川西山居 · 茶山叙事 · 木作工艺。' },
      { heading: '周边竞品扫描', body: '中端 12 家 / 高端 5 家 / 营地 4 家 / 民宿改造 6 家。' },
      { heading: '客流来源', body: '成渝双城 65% · 武汉/西安 18% · 北上深 12% · 其它 5%。' },
    ],
    references: ['川西山地民宿市场调研 2026Q1', '峨眉文旅政策汇编'],
  },
  {
    id: 'coherence_matrix', layerId: 'base_conditions',
    label: '任务×位置 对账',
    x: -10, y: -45, size: 22, status: 'draft',
    sourceObject: 'BriefSiteCoherence.matrix', sourceVersion: 'coherence_v0.1',
    description: 'L1 真正产物 — 列出匹配项 / 张力项 / 冲突项 / 原始气质。当前对账覆盖率 72%。',
    showLabel: true,
    category: '对账 · 项目机会陈述',
    details: [
      { heading: '匹配项 (3)', body: '山地资产 × HAY 克制感 / 周末客群 × 自驾可达 / 中端定价 × 市场缺口。' },
      { heading: '张力项 (2)', body: '北欧轻盈 vs 山地厚重 / 自营轻量 vs 餐饮配套要求。' },
      { heading: '冲突项 (1)', body: '⚠ 高湿气候对 HAY 功能主义浅色材料构成根本约束。' },
    ],
    references: ['五层模型裁决 v1.0 §2.1', 'Brief-Site Coherence schema'],
  },
  {
    id: 'project_temperament', layerId: 'base_conditions',
    label: '原始气质浮现',
    x: 12, y: 30, size: 16, status: 'hypothesis',
    sourceObject: 'BriefSiteCoherence.temperament', sourceVersion: 'coherence_v0.1',
    description: '从对账浮现的项目第一画面：山林克制 + 木作温度 + 不喧哗的设计感。',
    category: '对账 · 第一画面',
    details: [
      { heading: '关键词', body: '山林 / 克制 / 木作 / 茶山 / 安静 / 耐看。' },
      { heading: '排除项', body: '不做"网红"、不做"度假酒店"、不做"民俗主题"。' },
    ],
  },
  {
    id: 'dismissed_web_hotspot', layerId: 'base_conditions',
    label: '网红打卡主题民宿',
    x: 88, y: 76, size: 12, status: 'dismissed',
    sourceObject: 'AssumptionRegister.rejected.web_hotspot', sourceVersion: 'deliberation_log_v0.1',
    description: '早期曾讨论用强拍照点制造传播，但与 HAY 克制感、山地耐看和低维护目标冲突，已被用户否定。保留为推敲记录。可在品牌传播目标改变时二次启用为待确认。',
    category: '否定记录 · 定位排除',
    details: [
      { heading: '否定原因', body: '传播效率高，但会推高装置成本、维护成本，并削弱山地停留的安静气质。' },
      { heading: '二次启用条件', body: '若运营目标转向短视频传播，且能限定为可拆卸小尺度装置，可恢复为待确认。' },
    ],
    references: ['AssumptionRegister v0.1', '方案高参推敲记录 #A-03'],
  },

  // ══════════════════════════════════════════════════════════════════════
  // L2 建筑与边界（project_definition）— 8 节点：3 建筑事实 + 3 环境约束 + 2 边界
  // ══════════════════════════════════════════════════════════════════════
  {
    id: 'arch_existing', layerId: 'project_definition',
    label: '既有山地坡顶建筑',
    x: -225, y: -70, size: 19, status: 'draft',
    sourceObject: 'FloorPlanAsset.shell', sourceVersion: 'survey_v0.1',
    description: '改造项目 · 3 栋坡顶单体 + 1 栋后勤 · 砖木混合结构 · 现状基本完好，部分屋面老化。',
    showLabel: true,
    category: '建筑事实',
    details: [
      { heading: '建筑数量', body: '主楼 1 栋（公共功能）+ 客房 2 栋（A/B 组团）+ 后勤 1 栋。' },
      { heading: '建造年代', body: '原建于 2008，2018 年简单翻修，本次为深度改造。' },
      { heading: '资料状态', body: 'CAD 已上传 · 现场照片 32 组 · DWG 含部分错位。' },
    ],
    references: ['FloorPlanAsset 上传记录 #2026-04', '现场踏勘报告 v0.1'],
  },
  {
    id: 'arch_dimensions', layerId: 'project_definition',
    label: '总面积 ~2,400㎡',
    x: -225, y: -10, size: 17, status: 'confirmed',
    sourceObject: 'FloorPlanIR.dimensions', sourceVersion: 'survey_v0.1',
    description: '建筑面积 2,380㎡ · 套内 1,920㎡ · 净高 2.7-3.4m · 含 12 间客房与 280㎡ 公共区。',
    category: '建筑事实 · 体量参数',
    details: [
      { heading: '面积分布', body: '主楼 880㎡ / 客房 A 720㎡ / 客房 B 640㎡ / 后勤 140㎡。' },
      { heading: '层高', body: '主楼一层 3.4m · 客房 2.85m · 后勤 2.7m。' },
      { heading: '层数', body: '全部 1-2 层（坡顶建筑限高）。' },
    ],
  },
  {
    id: 'arch_structure', layerId: 'project_definition',
    label: '砖木混合结构',
    x: -210, y: 48, size: 16, status: 'draft',
    sourceObject: 'FloorPlanIR.structure', sourceVersion: 'survey_v0.1',
    description: '主体砖墙承重 + 木屋架 + 部分钢筋混凝土过梁。可改墙面有限，木屋架可暴露。',
    category: '建筑事实 · 结构类型',
    details: [
      { heading: '可改墙体', body: '内隔墙基本可拆 · 外墙不可动 · 部分内承重墙需结构复核。' },
      { heading: '柱网', body: '不规则；主楼 4.2-5.4m · 客房 3.3-3.6m。' },
      { heading: '管井位置', body: '已标注 6 处现有竖井，其中 2 处可保留。' },
    ],
  },
  {
    id: 'env_orientation', layerId: 'project_definition',
    label: '景观面 · 朝向',
    x: -10, y: -50, size: 22, status: 'confirmed',
    sourceObject: 'FloorPlanIR.envelope.orientation', sourceVersion: 'survey_v0.1',
    description: '主朝向南偏东 25° · 景观面正对金顶。北侧坡地不可压，是首要边界条件。',
    showLabel: true,
    category: '环境约束 · 朝向景观',
    details: [
      { heading: '主景观面', body: '南偏东 25°，开窗连续 38m，正对金顶（晴日可见）。' },
      { heading: '次景观面', body: '北侧坡地林海 · 东侧村落屋顶 · 西侧茶山。' },
      { heading: '不可压方向', body: '北坡地形保护 · 现有古树 4 株（直径 > 80cm）需保留。' },
    ],
    references: ['卫星图分析 #2026-04', '现场朝向实测 ±2°'],
  },
  {
    id: 'env_humidity', layerId: 'project_definition',
    label: '高湿气候约束',
    x: 8, y: 22, size: 17, status: 'confirmed',
    sourceObject: 'FloorPlanIR.envelope.climate', sourceVersion: 'survey_v0.1',
    description: '年均湿度 78% · 雨季 4-9 月 · 现有建筑已有局部霉变痕迹 · 防潮系统是必选项。',
    category: '环境约束 · 气候',
    details: [
      { heading: '湿度数据', body: '年均 78% · 雨季峰值 92% · 干季最低 55%。' },
      { heading: '防潮要求', body: '地面架空 + 墙体呼吸层 + 主动除湿（公区/客房）。' },
      { heading: '设备增量', body: '中央除湿 ≈80 万 · 含设备机房改造。' },
    ],
  },
  {
    id: 'env_lighting', layerId: 'project_definition',
    label: '采光与通风',
    x: 235, y: -78, size: 15, status: 'draft',
    sourceObject: 'FloorPlanIR.envelope.lighting', sourceVersion: 'survey_v0.1',
    description: '南向采光优 · 部分客房存在采光死角 · 山间湿气需通风梯度配合。',
    category: '环境约束 · 采光通风',
    details: [
      { heading: '采光等级', body: '南向 A · 东西向 B · 北向 C（仅借光）。' },
      { heading: '通风死角', body: '客房 B-3、B-5 存在单向通风（建议增设高侧窗）。' },
    ],
  },
  {
    id: 'boundary_red_line', layerId: 'project_definition',
    label: '红线 / 物业 / 消防',
    x: 230, y: -10, size: 16, status: 'draft',
    sourceObject: 'FloorPlanIR.boundary', sourceVersion: 'survey_v0.1',
    description: '用地红线 4,800㎡ · 退界北 6m / 南 4m · 消防通道现有 2 条，需保留。物业有外立面色彩限制。',
    category: '边界 · 合规约束',
    details: [
      { heading: '退界要求', body: '北 6m / 南 4m / 东西 3m。当前 3 处临界。' },
      { heading: '消防', body: '环形消防车道完整 · 客房与公区疏散需双向通道。' },
      { heading: '物业限制', body: '外立面色彩需按景区管委会色卡（限 8 色）。' },
    ],
    references: ['消防初审意见 #2026-03-15', '景区管委会立面色卡'],
  },
  {
    id: 'boundary_survey_gap', layerId: 'project_definition',
    label: '⚠ 测绘缺口 · Gate failed',
    x: 215, y: 50, size: 17, status: 'blocked',
    sourceObject: 'FloorPlanIR.gates.measurement', sourceVersion: 'gate_failed',
    description: 'Coordinate Gate 0/100 · 净高、电气、给排水缺补充测绘。平面推演硬阻断。',
    category: '边界 · IR 编译门',
    details: [
      { heading: '缺失项', body: '客房 B 整体净高 · 主楼电气竖井 · 给排水汇总表。' },
      { heading: '门状态', body: 'Contract ✓78 · Coordinate ✗0 · Structure ✓100 · Geometry ✓87 · System ✓64' },
      { heading: '解锁动作', body: '安排 2 天补测 · 上传后 IR 重新编译。' },
    ],
    references: ['IR 编译日志 #2026-05-04'],
  },

  // ══════════════════════════════════════════════════════════════════════
  // L3 人群与场景（spatial_structure）— 9 节点：3 人群 + 3 行为 + 3 运营
  // ══════════════════════════════════════════════════════════════════════
  {
    id: 'persona_primary', layerId: 'spatial_structure',
    label: '核心客群 · 周末轻度假',
    x: -228, y: -75, size: 19, status: 'draft',
    sourceObject: 'ActorScenarioOperation.persona.primary', sourceVersion: 'persona_draft',
    description: '一线城市 28-38 岁 · 2-4 人组队 · 周五晚到周日中午 · 重看山停留与轻社交。',
    showLabel: true,
    category: '人群主体',
    details: [
      { heading: '画像维度', body: '年龄 28-38 / 月入 25k+ / 已婚或情侣 / 设计敏感度高。' },
      { heading: '行为偏好', body: '看山 + 茶 + 阅读 + 轻社交，不要 KTV / 不要团建。' },
      { heading: '决策路径', body: '小红书种草 → 携程比价 → 直订或微信咨询。' },
    ],
    references: ['客群访谈 #2026-04 ×8 组', '小红书声量分析'],
  },
  {
    id: 'persona_secondary', layerId: 'spatial_structure',
    label: '次级客群 · 亲子短住',
    x: -240, y: -10, size: 14, status: 'hypothesis',
    sourceObject: 'ActorScenarioOperation.persona.secondary', sourceVersion: 'persona_draft',
    description: '工作日带娃家庭 · 1-2 晚 · 重早餐与户外活动空间。占比 20-25%。',
    category: '人群主体 · 辅助',
    details: [
      { heading: '次要画像', body: '32-42 岁带娃 · 周中错峰 · 房价敏感度中。' },
      { heading: '空间需求', body: '需要 2 间相邻客房 + 户外可活动场地。' },
    ],
  },
  {
    id: 'persona_owner_team', layerId: 'spatial_structure',
    label: '业主自营团队',
    x: -215, y: 48, size: 14, status: 'draft',
    sourceObject: 'ActorScenarioOperation.persona.operator', sourceVersion: 'persona_draft',
    description: '4-6 人轮值 · 主理人本地驻场 · 后勤需照顾团队居住与周转。',
    category: '人群主体 · 运营方',
    details: [
      { heading: '团队居住', body: '需 2 间员工房 + 1 个团队休息室。' },
      { heading: '动线诉求', body: '客人面前后勤动线必须低感知，但不能完全隐藏。' },
    ],
  },
  {
    id: 'scene_arrival', layerId: 'spatial_structure',
    label: '到达流线 · 自驾→停车→步行',
    x: -10, y: -62, size: 17, status: 'hypothesis',
    sourceObject: 'ActorScenarioOperation.behavior.arrival', sourceVersion: 'scenario_draft',
    description: '车行至公共停车 → 步行 80m 山间小径 → 抵达主楼前厅。仪式感来自步行。',
    category: '行为场景 · 到达',
    details: [
      { heading: '关键节点', body: '停车坪 → 雨棚 → 山径 → 茶水接待 → 客房分配。' },
      { heading: '风险', body: '雨天行李运输 · 老人小孩步行 80m · 行李辅助系统。' },
    ],
  },
  {
    id: 'scene_living', layerId: 'spatial_structure',
    label: '看山停留 + 轻社交',
    x: -5, y: -10, size: 22, status: 'confirmed',
    sourceObject: 'ActorScenarioOperation.behavior.living', sourceVersion: 'scenario_draft',
    description: '空间剧本核心 · 公共客厅是项目主角，非大堂。看山 + 茶 + 阅读 + 邻里轻聊。',
    showLabel: true,
    category: '行为场景 · 公共时段',
    details: [
      { heading: '高峰时段', body: '17:00-21:00 山色 + 灯光转场 + 晚茶。客厅承载 12-18 人。' },
      { heading: '低峰时段', body: '工作时段独处 + 远程会议（少量）。' },
      { heading: '附属场景', body: '下午茶 / 桌游夜 / 山色阅读 / 私人聚会。' },
    ],
  },
  {
    id: 'scene_room_morning', layerId: 'spatial_structure',
    label: '客房独处 + 早餐',
    x: -10, y: 38, size: 15, status: 'draft',
    sourceObject: 'ActorScenarioOperation.behavior.room', sourceVersion: 'scenario_draft',
    description: '夜间客房独处 · 晨起山间散步 · 早餐分时段 7:30-10:00 自助。',
    category: '行为场景 · 客房+早餐',
    details: [
      { heading: '客房需求', body: '看山落地窗 · 独立浴缸 · 茶台 · 工作位（小）。' },
      { heading: '早餐配置', body: '简餐 + 山野食材 · 不做正餐 · 公区错峰复用。' },
    ],
  },
  {
    id: 'ops_revenue', layerId: 'spatial_structure',
    label: '入住率与定价模型',
    x: 215, y: -78, size: 17, status: 'draft',
    sourceObject: 'ActorScenarioOperation.operation.revenue', sourceVersion: 'ops_draft',
    description: '12 间 × 平均 1,100/晚 · 入住率目标 60% · 年营收 ~290 万。需配套低预订率应对。',
    category: '运营现实 · 商业模型',
    details: [
      { heading: '价格分层', body: '标准 800-1,000 / 景观 1,200-1,500 / 套房 1,800-2,200。' },
      { heading: '入住率目标', body: '旺季 80% / 平季 55% / 淡季 35%。' },
      { heading: '预算占比', body: '改造 70% · 软装 18% · 启动 8% · 储备 4%。' },
    ],
    references: ['同尺度民宿财务模型对标 ×3', '本项目 5 年现金流模型'],
  },
  {
    id: 'ops_seasonal', layerId: 'spatial_structure',
    label: '雨季维护风险',
    x: 232, y: -10, size: 16, status: 'blocked',
    sourceObject: 'ActorScenarioOperation.operation.seasonal', sourceVersion: 'ops_draft',
    description: '雨季 4-9 月 · 维护成本高 · 高湿引发的家具/软装更换周期短 · 团队压力大。',
    category: '运营现实 · 季节性',
    details: [
      { heading: '高维护项', body: '布草 / 木家具 / 软装 / 户外平台。' },
      { heading: '替换周期', body: '布草 1 季 · 软装 2 年 · 户外漆 1 年。' },
      { heading: '风险预算', body: '建议年度维护预算占营收 8%（vs 行业 5%）。' },
    ],
  },
  {
    id: 'ops_backstage_flow', layerId: 'spatial_structure',
    label: '后勤动线效率',
    x: 215, y: 50, size: 15, status: 'draft',
    sourceObject: 'ActorScenarioOperation.operation.backstage', sourceVersion: 'ops_draft',
    description: '小团队 → 后勤动线必须支持多角色复用 · 客人低感知但不完全隐藏。',
    category: '运营现实 · 动线',
    details: [
      { heading: '关键路径', body: '到货 → 储 → 餐厨 → 客房布草 → 垃圾出口。' },
      { heading: '复用要求', body: '同一通道工作日 3-4 角色复用，需时段错峰。' },
    ],
  },
  {
    id: 'dismissed_group_building', layerId: 'spatial_structure',
    label: '团建客群作为主客群',
    x: 88, y: 76, size: 12, status: 'dismissed',
    sourceObject: 'AssumptionRegister.rejected.group_building', sourceVersion: 'deliberation_log_v0.1',
    description: '曾考虑承接公司团建以提升淡季入住，但会放大噪音、餐饮和活动组织压力，与轻度假客群体验冲突，已从主客群中删除。',
    category: '否定记录 · 客群排除',
    details: [
      { heading: '否定原因', body: '团建需要大餐饮、会议、声量管理和更强运营团队，超出自营轻团队能力边界。' },
      { heading: '二次启用条件', body: '若后续新增独立活动楼或托管运营团队，可作为低频包场客群重新评估。' },
    ],
    references: ['客群访谈 #2026-04', '方案高参推敲记录 #C-02'],
  },

  // ══════════════════════════════════════════════════════════════════════
  // L4 策略与语言（strategy_organization）— 10 节点：3 L4a + 4 L4b + 3 L4c
  // ══════════════════════════════════════════════════════════════════════
  {
    id: 'l4a_skeleton', layerId: 'strategy_organization',
    label: 'L4a · 公共客厅为骨架',
    x: -225, y: -75, size: 20, status: 'draft',
    sourceObject: 'DesignTranslationStrategy.spatial.skeleton', sourceVersion: 'l4a_draft',
    description: '公共客厅是项目主角，客房为侧翼，景观面被所有公共动线共享。',
    showLabel: true,
    category: 'L4a · 空间组织',
    details: [
      { heading: '骨架原则', body: '主楼=客厅+前厅+早餐 · 客房 A/B 翼展 · 后勤独立。' },
      { heading: '邻接关系', body: '客厅 ↔ 前厅 ↔ 早餐区(共享) · 客房至客厅步行 ≤ 60s。' },
      { heading: '景观共享', body: '三种公共功能均有南向景观面，无背山功能。' },
    ],
  },
  {
    id: 'l4a_separation', layerId: 'strategy_organization',
    label: 'L4a · 后勤独立动线',
    x: -228, y: -10, size: 16, status: 'confirmed',
    sourceObject: 'DesignTranslationStrategy.spatial.separation', sourceVersion: 'l4a_draft',
    description: '后勤入口与客人动线物理分离 · 服务路径不穿越客厅 · 客人低感知但保留生活感。',
    category: 'L4a · 空间分离',
    details: [
      { heading: '客人动线', body: '主入口 → 前厅 → 客厅 → 客房（不接触后勤）。' },
      { heading: '后勤动线', body: '货车口 → 储 → 餐厨 → 客房布草通道。' },
    ],
  },
  {
    id: 'l4a_scale', layerId: 'strategy_organization',
    label: 'L4a · 尺度与视线',
    x: -210, y: 50, size: 15, status: 'draft',
    sourceObject: 'DesignTranslationStrategy.spatial.scale', sourceVersion: 'l4a_draft',
    description: '客厅净高 4m+ · 客房 2.85m · 视线对景金顶 · 公共空间不做隔墙。',
    category: 'L4a · 尺度策略',
    details: [
      { heading: '尺度梯度', body: '入口低（仪式压低）→ 客厅高（释放）→ 客房中（亲密）。' },
      { heading: '视线设计', body: '主景观面贯穿轴 · 早餐位看山 · 茶台坐看山。' },
    ],
  },
  {
    id: 'l4b_palette', layerId: 'strategy_organization',
    label: 'L4b · 90% 安静 + 10% 记忆',
    x: -10, y: -65, size: 22, status: 'confirmed',
    sourceObject: 'DesignTranslationStrategy.expression.color', sourceVersion: 'l4b_draft',
    description: '色彩策略：90% 安静（场地原色 + 木 + 灰）+ 10% HAY 记忆色小剂量点缀。',
    showLabel: true,
    category: 'L4b · 表达策略',
    details: [
      { heading: '安静底色', body: '原木色 / 灰白 / 山林绿 / 茶褐。占视觉面积 90%。' },
      { heading: '记忆色', body: 'HAY 黄(Mustard) / 砖红(Brick) / 蓝(Atlantic)。点缀型。' },
      { heading: '禁忌', body: '禁高饱和大面积 / 禁纯白冷光 / 禁仿古红木。' },
    ],
  },
  {
    id: 'l4b_material', layerId: 'strategy_organization',
    label: 'L4b · 木·灰·土 材料底色',
    x: -10, y: -10, size: 17, status: 'draft',
    sourceObject: 'DesignTranslationStrategy.expression.material', sourceVersion: 'l4b_draft',
    description: '主材料：本地杉木 + 水洗灰 + 黑铸铁 + 浅夯土。在地工艺为主。',
    category: 'L4b · 材料语言',
    details: [
      { heading: '本地材料', body: '杉木（屋架/家具）/ 青砖（墙）/ 夯土（部分内墙）。' },
      { heading: '工业元素', body: '黑铸铁（楼梯/灯具）/ 水洗灰水泥（地面）。' },
      { heading: '替换弹性', body: '高频损耗部位（地面/坐具）选可替换模块。' },
    ],
  },
  {
    id: 'l4b_lighting', layerId: 'strategy_organization',
    label: 'L4b · 暖光 + 山色对景',
    x: -8, y: 30, size: 15, status: 'draft',
    sourceObject: 'DesignTranslationStrategy.expression.lighting', sourceVersion: 'l4b_draft',
    description: '主光暖（2700K）· 重点光（3000K）· 应急冷光禁用。山色随时段是主视觉。',
    category: 'L4b · 灯光策略',
    details: [
      { heading: '色温分区', body: '客厅 2700K · 早餐区 3000K · 客房可调 2400-2800K。' },
      { heading: '禁忌', body: '禁筒灯阵列 · 禁冷白光 · 禁色光泛光。' },
    ],
  },
  {
    id: 'l4b_softgoods', layerId: 'strategy_organization',
    label: 'L4b · HAY 软装小剂量点缀',
    x: 15, y: 55, size: 14, status: 'confirmed',
    sourceObject: 'DesignTranslationStrategy.expression.softgoods', sourceVersion: 'l4b_draft',
    description: 'HAY 椅 / 灯 / 织物 在客厅与客房关键触点出现。占整体软装 30%。',
    category: 'L4b · 软装定调',
    details: [
      { heading: 'HAY 触点', body: '主椅（About a Chair）/ 灯（PC Pendant）/ 抱枕。' },
      { heading: '本地协奏', body: '本地手工织物 + 茶器 + 干花。占软装 70%。' },
    ],
  },
  {
    id: 'l4c_budget_split', layerId: 'strategy_organization',
    label: 'L4c · 60/40 预算分配',
    x: 215, y: -78, size: 17, status: 'draft',
    sourceObject: 'DesignTranslationStrategy.delivery.budget', sourceVersion: 'l4c_draft',
    description: '60% 在地定制（耐候/大面积）· 40% 品牌原品（高频触点）。',
    category: 'L4c · 落地控制',
    details: [
      { heading: '在地定制 60%', body: '木作 / 砖墙 / 夯土 / 钢结构 / 灯具基础。' },
      { heading: '品牌原品 40%', body: 'HAY 主椅 / 灯具 / 软装 / 部分卫浴五金。' },
      { heading: '决策原则', body: '高频触点选品牌（视觉记忆点）· 大面积选在地（成本+可维护）。' },
    ],
  },
  {
    id: 'l4c_phasing', layerId: 'strategy_organization',
    label: 'L4c · 雨季施工避让',
    x: 232, y: -15, size: 15, status: 'draft',
    sourceObject: 'DesignTranslationStrategy.delivery.phasing', sourceVersion: 'l4c_draft',
    description: '主结构 + 屋面 10-3 月 · 内装 + 软装 11-2 月 · 雨季前完工。',
    category: 'L4c · 阶段实施',
    details: [
      { heading: '阶段一 (10-12 月)', body: '主体加固 + 屋面修复 + 室外平台。' },
      { heading: '阶段二 (12-2 月)', body: '内隔墙 + 设备 + 木作 + 软装。' },
      { heading: '阶段三 (3 月)', body: '验收 + 试营业 + 优化。' },
    ],
  },
  {
    id: 'l4c_maintenance', layerId: 'strategy_organization',
    label: 'L4c · 维护友好选型',
    x: 220, y: 50, size: 14, status: 'hypothesis',
    sourceObject: 'DesignTranslationStrategy.delivery.maintenance', sourceVersion: 'l4c_draft',
    description: '所有家具与五金优先模块化 · 单一磨损部件可独立更换，不动整体。',
    category: 'L4c · 维护策略',
    details: [
      { heading: '模块化原则', body: '坐垫可洗 / 灯泡可换 / 五金标准化 / 木地板可分块翻新。' },
      { heading: '替换周期表', body: '布草 1 季 / 软装 2 年 / 户外漆 1 年 / 木地板 5 年。' },
    ],
  },
  {
    id: 'dismissed_all_hay_originals', layerId: 'strategy_organization',
    label: '大面积 HAY 原品采购',
    x: 88, y: 76, size: 12, status: 'dismissed',
    sourceObject: 'AssumptionRegister.rejected.hay_originals', sourceVersion: 'deliberation_log_v0.1',
    description: '曾把品牌原品作为主要视觉策略，但预算、损耗、山地维护和在地性都不成立，已否定为非主线方案。',
    category: '否定记录 · 表达排除',
    details: [
      { heading: '否定原因', body: '品牌记忆点过强会压过山地场地，且公共区高频损耗会带来持续替换成本。' },
      { heading: '二次启用条件', body: '只可作为 10% 记忆点或关键触点恢复，不建议恢复为大面积策略。' },
    ],
    references: ['DesignTranslationStrategy.excluded', '方案高参推敲记录 #L4B-05'],
  },

  // ══════════════════════════════════════════════════════════════════════
  // L5 推演与成果（output_results）— 7 节点：3 推演接口 + 2 投射 + 2 集成/回写
  // ══════════════════════════════════════════════════════════════════════
  {
    id: 'l5_psc', layerId: 'output_results',
    label: 'PSC 空间组成 · 草案',
    x: -228, y: -75, size: 18, status: 'draft',
    sourceObject: 'PSC.composition', sourceVersion: 'psc_v0.1',
    description: 'L4a 投射产物 · 7 节点：到达 / 公共客厅 / 早餐 / 客房 A / 客房 B / 后勤 / 景观步道。',
    showLabel: true,
    category: '推演接口 · 空间结构',
    details: [
      { heading: '节点清单', body: '7 个 PSC 节点 · 7 条邻接关系（5 实线 + 2 虚线）。' },
      { heading: '当前状态', body: '草案级 · 已生成 BubblePlanLogic · 待 L2 IR 通过后冻结。' },
      { heading: '已识别冲突', body: '客房 B 净高与套房定位错配 · 待 L2 测绘补齐校验。' },
    ],
    references: ['PSC schema v1.0', 'BubblePlanLogic v0.1'],
  },
  {
    id: 'l5_ffl', layerId: 'output_results',
    label: 'FFL 平面功能 · 待覆盖',
    x: -225, y: -10, size: 15, status: 'hypothesis',
    sourceObject: 'FFL.coverage', sourceVersion: 'ffl_pending',
    description: '5/7 关键作用域已挂载草案 FFL · 客房 B 与景观步道未挂载。',
    category: '推演接口 · 作用域',
    details: [
      { heading: '已挂载', body: '到达 / 客厅 / 早餐 / 客房 A / 后勤。' },
      { heading: '未挂载', body: '客房 B（待 L2 测绘）/ 景观步道（待场地踏勘）。' },
    ],
  },
  {
    id: 'l5_bubble_logic', layerId: 'output_results',
    label: 'BubblePlanLogic · 已生成',
    x: -210, y: 50, size: 15, status: 'draft',
    sourceObject: 'BubblePlanLogic.view', sourceVersion: 'bubble_v0.1',
    description: 'PSC + FFL 关系视图 · 已生成 · 邻接箭头与流线可视化。',
    category: '推演接口 · 关系视图',
    details: [
      { heading: '视图组件', body: '泡泡逻辑预演区（项目底盘内置）。' },
      { heading: '可交互层级', body: 'L1 空间节点 / L2 区域平面 / L3 房间 — 三层联动。' },
    ],
  },
  {
    id: 'l5_floor_plan', layerId: 'output_results',
    label: '⚠ 平面推演入口',
    x: -10, y: -55, size: 19, status: 'blocked',
    sourceObject: 'LayoutScopeIndex.entry.floor_plan', sourceVersion: 'index_pending',
    description: 'L2 IR Coordinate Gate 0/100 阻断 · 平面推演只能预览，不能正式推演与回写。',
    showLabel: true,
    category: '投射动作 · 平面推演',
    details: [
      { heading: '阻断原因', body: 'L2 测绘缺口（净高 / 电气 / 给排水）。' },
      { heading: '解锁路径', body: '补测 → IR 重编译 → 五门通过 → 平面推演正式启动。' },
      { heading: '当前可做', body: '预览模式（只读 schematic），不可保存版本。' },
    ],
  },
  {
    id: 'l5_scheme_canvas', layerId: 'output_results',
    label: '方案画布入口',
    x: 12, y: 30, size: 16, status: 'hypothesis',
    sourceObject: 'LayoutScopeIndex.entry.scheme_canvas', sourceVersion: 'index_pending',
    description: 'L4b 表达策略已成型 · 可进入概念画布；完整方案画布需 PSC 冻结后启动。',
    category: '投射动作 · 方案画布',
    details: [
      { heading: '当前可达', body: '概念画布（色彩/材料/家具气质方向）。' },
      { heading: '待解锁', body: '完整方案画布（需 PSC + L2 IR 双冻结）。' },
    ],
  },
  {
    id: 'l5_conflict_log', layerId: 'output_results',
    label: '跨层冲突清单',
    x: 218, y: -78, size: 16, status: 'draft',
    sourceObject: 'AlignmentCanvas.conflicts', sourceVersion: 'alignment_v0.1',
    description: '当前已识别 4 项跨层冲突 · 1 项已闭环 · 3 项待裁决。',
    category: '集成状态 · 跨层对账',
    details: [
      { heading: '已闭环 (1)', body: 'L1 高湿冲突 ↔ L4b 材料 → 选浅夯土+木+灰底色。' },
      { heading: '待裁决 (3)', body: '①L1 自营 vs L3 餐饮配置 / ②L2 净高 vs L3 套房 / ③L4c 预算 vs L4b 软装。' },
    ],
    references: ['AlignmentCanvas 协商记录 v0.1'],
  },
  {
    id: 'l5_patch_queue', layerId: 'output_results',
    label: 'ProjectBasePatch · 待确认',
    x: 232, y: -10, size: 15, status: 'draft',
    sourceObject: 'ProjectBasePatch.pending', sourceVersion: 'patch_v0.1',
    description: '下游产生 3 条补丁待回写底盘 · 用户确认后入链升版。',
    category: '回写闸门 · 补丁队列',
    details: [
      { heading: '补丁 #1', body: '泡泡推演发现客厅面积应 +30㎡（来自 L4a→L1 经营回流）。' },
      { heading: '补丁 #2', body: '现场踏勘发现古树 4 株需保留（更新 L2 boundary）。' },
      { heading: '补丁 #3', body: '客群访谈调整次级客群权重至 25%（更新 L3 persona）。' },
    ],
  },
  {
    id: 'l5_freeze_status', layerId: 'output_results',
    label: '阶段冻结状态',
    x: 215, y: 50, size: 15, status: 'hypothesis',
    sourceObject: 'ProjectFreeze.stage', sourceVersion: 'freeze_pending',
    description: '当前阶段：L1 草案 / L2 阻断 / L3 草案 / L4 草案 / L5 待启动。整体未冻结。',
    category: '集成状态 · 冻结',
    details: [
      { heading: '冻结门槛', body: 'L1-L4 全部 ≥ 70% 成熟度 + 跨层冲突全部闭环。' },
      { heading: '当前差距', body: 'L2 阻断 + L3 仅 44% + 3 项冲突未闭环。' },
    ],
  },
];

const REHEARSAL_SCOPES: RehearsalScope[] = [
  {
    id: 'arrival',
    label: '到达与入口',
    shortLabel: '入口',
    kind: 'zone',
    x: 1298,
    y: 292,
    w: 118,
    h: 58,
    color: '#7dd3fc',
    maturity: 0.58,
    status: 'draft',
    buildingIds: ['lobby_building'],
    note: '入口、停车、接待前场需要先确认到达顺序。',
  },
  {
    id: 'lobby_building',
    label: '大堂楼',
    shortLabel: '大堂',
    kind: 'building',
    x: 1440,
    y: 256,
    w: 138,
    h: 72,
    color: '#8bd3c7',
    maturity: 0.72,
    status: 'confirmed',
    buildingIds: ['lobby_building'],
    note: '接待、公共客厅、咖啡和景观停留应作为核心公共节点。',
  },
  {
    id: 'dining_building',
    label: '餐饮楼',
    shortLabel: '餐饮',
    kind: 'building',
    x: 1600,
    y: 318,
    w: 126,
    h: 66,
    color: '#f2c879',
    maturity: 0.52,
    status: 'gap',
    buildingIds: ['dining_building'],
    note: '厨房、排烟、送货和客人流线仍需与真实边界对账。',
  },
  {
    id: 'guest_cluster_a',
    label: '客房组团 A',
    shortLabel: '客房 A',
    kind: 'building',
    x: 1436,
    y: 392,
    w: 164,
    h: 80,
    color: '#b59cff',
    maturity: 0.66,
    status: 'draft',
    buildingIds: ['guest_a'],
    note: '三层客房逻辑已成形，房型数量和服务点仍待平面校准。',
  },
  {
    id: 'guest_cluster_b',
    label: '客房组团 B',
    shortLabel: '客房 B',
    kind: 'building',
    x: 1242,
    y: 412,
    w: 142,
    h: 70,
    color: '#9bbcf9',
    maturity: 0.48,
    status: 'draft',
    buildingIds: ['guest_b'],
    note: '适合作为安静组团，需验证与公区噪声的距离。',
  },
  {
    id: 'service_zone',
    label: '后勤与服务',
    shortLabel: '后勤',
    kind: 'service',
    x: 1666,
    y: 246,
    w: 98,
    h: 52,
    color: '#cbd5e1',
    maturity: 0.38,
    status: 'blocked',
    buildingIds: ['service_zone'],
    note: '布草、清洁、补货和垃圾回收路径缺口明显。',
  },
  {
    id: 'landscape_loop',
    label: '景观步道',
    shortLabel: '步道',
    kind: 'zone',
    x: 1312,
    y: 502,
    w: 156,
    h: 48,
    color: '#a7f3d0',
    maturity: 0.42,
    status: 'gap',
    buildingIds: ['landscape_loop'],
    note: '步道既是交通也是体验节奏，需建立雨天替代路径。',
  },
];

const REHEARSAL_BUILDINGS: RehearsalBuilding[] = [
  {
    id: 'lobby_building',
    label: '大堂楼',
    subtitle: '接待 / 公共客厅 / 咖啡',
    scopeId: 'lobby_building',
    floors: [
      { id: 'lobby_1f', label: '1F', summary: '接待、等候、公共客厅', maturity: 0.72, status: 'confirmed' },
    ],
  },
  {
    id: 'dining_building',
    label: '餐饮楼',
    subtitle: '早餐 / 厨房 / 外摆',
    scopeId: 'dining_building',
    floors: [
      { id: 'dining_2f', label: '2F', summary: '轻餐、景观位', maturity: 0.44, status: 'gap' },
      { id: 'dining_1f', label: '1F', summary: '厨房、备餐、仓储', maturity: 0.52, status: 'gap' },
    ],
  },
  {
    id: 'guest_a',
    label: '客房 A 栋',
    subtitle: '三层 / 景观客房',
    scopeId: 'guest_cluster_a',
    floors: [
      { id: 'guest_a_3f', label: '3F', summary: '景观房、布草点', maturity: 0.62, status: 'draft' },
      { id: 'guest_a_2f', label: '2F', summary: '标准房、家庭房', maturity: 0.66, status: 'draft' },
      { id: 'guest_a_1f', label: '1F', summary: '无障碍房、服务入口', maturity: 0.54, status: 'gap' },
    ],
  },
  {
    id: 'guest_b',
    label: '客房 B 栋',
    subtitle: '两层 / 安静组团',
    scopeId: 'guest_cluster_b',
    floors: [
      { id: 'guest_b_2f', label: '2F', summary: '情侣房、观景位', maturity: 0.46, status: 'draft' },
      { id: 'guest_b_1f', label: '1F', summary: '标准房、设备点', maturity: 0.42, status: 'draft' },
    ],
  },
  {
    id: 'service_zone',
    label: '后勤区',
    subtitle: '布草 / 清洁 / 补货',
    scopeId: 'service_zone',
    floors: [
      { id: 'service_1f', label: '1F', summary: '布草间、垃圾暂存', maturity: 0.38, status: 'blocked' },
    ],
  },
];

const STATUS_META: Record<StackNodeStatus, { label: string; fill: string; stroke: string; text: string }> = {
  confirmed: { label: '已确认', fill: '#e8f8f0', stroke: '#58c28d', text: '#166534' },
  draft: { label: '草案', fill: '#eef6ff', stroke: '#6aa8ff', text: '#1d4ed8' },
  hypothesis: { label: '待验证', fill: '#fff7df', stroke: '#f0b35a', text: '#92400e' },
  blocked: { label: '阻断', fill: '#fff0f0', stroke: '#ef6351', text: '#b91c1c' },
  frozen: { label: '已冻结', fill: '#ffffff', stroke: '#f8fafc', text: '#0f172a' },
  dismissed: { label: '已否定', fill: '#f1f5f9', stroke: '#94a3b8', text: '#64748b' },
};

const REHEARSAL_STATUS_META: Record<RehearsalScopeStatus, { label: string; fill: string; stroke: string }> = {
  confirmed: { label: '已确认', fill: 'rgba(52,211,153,0.24)', stroke: '#6ee7b7' },
  draft: { label: '草案', fill: 'rgba(96,165,250,0.22)', stroke: '#93c5fd' },
  gap: { label: '待补', fill: 'rgba(245,158,11,0.22)', stroke: '#fbbf24' },
  blocked: { label: '阻断', fill: 'rgba(239,99,81,0.22)', stroke: '#fb7185' },
  frozen: { label: '已冻结', fill: 'rgba(248,250,252,0.22)', stroke: '#f8fafc' },
};

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function easeOutCubic(t: number) {
  return 1 - Math.pow(1 - t, 3);
}

function useAnimatedNumber(target: number, duration = 240) {
  const [value, setValue] = useState(target);
  const valueRef = useRef(target);

  useEffect(() => {
    const start = valueRef.current;
    const delta = target - start;
    if (Math.abs(delta) < 0.001) {
      valueRef.current = target;
      setValue(target);
      return;
    }

    let frameId = 0;
    const startTime = performance.now();
    const tick = (now: number) => {
      const progress = clamp((now - startTime) / duration, 0, 1);
      const next = start + delta * easeOutCubic(progress);
      valueRef.current = next;
      setValue(next);
      if (progress < 1) frameId = requestAnimationFrame(tick);
    };

    frameId = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId);
  }, [duration, target]);

  return value;
}

function layerById(id: StackLayerId) {
  return STACK_LAYERS.find(layer => layer.id === id) ?? STACK_LAYERS[0];
}

function getPropositionState(status: StackNodeStatus): PropositionState {
  if (status === 'dismissed') return 'dismissed';
  return status === 'confirmed' || status === 'frozen' ? 'confirmed' : 'pending';
}

function isDismissedNode(node: StackNode) {
  return getPropositionState(node.status) === 'dismissed';
}

function compareStackNodesByState(a: StackNode, b: StackNode) {
  const stateRank: Record<PropositionState, number> = {
    confirmed: 0,
    pending: 1,
    dismissed: 2,
  };
  const aState = getPropositionState(a.status);
  const bState = getPropositionState(b.status);
  if (stateRank[aState] !== stateRank[bState]) return stateRank[aState] - stateRank[bState];
  return 0;
}

function sortStackNodesByState(nodes: StackNode[]) {
  return nodes.map((node, index) => ({ node, index })).sort((a, b) => {
    const stateOrder = compareStackNodesByState(a.node, b.node);
    return stateOrder || a.index - b.index;
  }).map(item => item.node);
}

function getLayerCompletion(layerId: StackLayerId, nodes: StackNode[]) {
  const activeNodes = nodes.filter(node => node.layerId === layerId && !isDismissedNode(node));
  const confirmedCount = activeNodes.filter(node => getPropositionState(node.status) === 'confirmed').length;
  const totalCount = activeNodes.length;
  return {
    confirmedCount,
    totalCount,
    ratio: totalCount > 0 ? confirmedCount / totalCount : 0,
  };
}

function getPropositionStateLabel(status: StackNodeStatus) {
  const state = getPropositionState(status);
  if (state === 'confirmed') return '已确认';
  if (state === 'dismissed') return '已否定';
  return '待确认';
}

function getNodePriorityClass(node: StackNode, classPrefix: string) {
  return node.priority ? `${classPrefix}-priority-${node.priority}` : '';
}

function getNodePriorityLabel(node: StackNode) {
  if (node.priority === 'critical') return '锚点';
  return null;
}

function getStackRailLabel(label: string) {
  const chars = Array.from(label);
  return chars.length > PROJECT_STACK_3D_LABEL_MAX_CHARS
    ? `${chars.slice(0, PROJECT_STACK_3D_LABEL_MAX_CHARS).join('')}...`
    : label;
}

function PropositionStateIcon({
  state,
  className,
}: {
  state: PropositionState;
  className?: string;
}) {
  if (state === 'confirmed') {
    return <Check className={className} strokeWidth={3.4} aria-hidden="true" />;
  }
  if (state === 'dismissed') {
    return <X className={className} strokeWidth={3.5} aria-hidden="true" />;
  }
  return <TriangleAlert className={className} strokeWidth={3.1} aria-hidden="true" />;
}

function getNodeAdvisorPrompt(node: StackNode) {
  const state = getPropositionState(node.status);
  if (state === 'confirmed') {
    return `「${node.label}」是项目底盘里的已确认判断命题。请说明它的依据、对后续推演的影响，以及可复用的判断结论。`;
  }
  if (state === 'dismissed') {
    return `「${node.label}」是项目底盘里的已否定判断命题。请说明它当时被否定或删除的原因、保留为推敲记录的价值，以及什么条件下可以二次启用为待确认。`;
  }
  return `「${node.label}」是项目底盘里的待确认判断命题。请说明当前推断依据、缺口、风险，以及需要用户确认的下一步动作。`;
}

function getNodeLabelLod(zoom: number) {
  if (zoom < 0.92) return 0;
  if (zoom < 1.12) return 1;
  if (zoom < 1.62) return 2;
  return 3;
}

function getNodeLabelLimit(lod: number) {
  if (lod <= 0) return 0;
  if (lod === 1) return 4;
  if (lod === 2) return 7;
  return 12;
}

function getNodeLabelPriority(node: StackNode, activeLayerId: StackLayerId, selectedNodeId: string) {
  const statusScore: Record<StackNodeStatus, number> = {
    blocked: 160,
    confirmed: 80,
    frozen: 80,
    draft: 40,
    hypothesis: 20,
    dismissed: -40,
  };
  return (
    (node.id === selectedNodeId ? 1000 : 0) +
    (node.layerId === activeLayerId ? 300 : 0) +
    (node.showLabel ? 180 : 0) +
    (node.priority === 'critical' ? 120 : 0) +
    statusScore[node.status]
  );
}

function shouldConsiderNodeLabel(node: StackNode, lod: number, activeLayerId: StackLayerId, selectedNodeId: string, hasQuery: boolean) {
  if (lod <= 0 && !hasQuery) return false;
  if (node.id === selectedNodeId) return true;
  if (node.layerId !== activeLayerId) return false;
  if (hasQuery) return true;
  if (lod <= 0) return Boolean(node.showLabel);
  if (lod === 1) return Boolean(node.showLabel) || node.status === 'blocked';
  if (lod === 2) return Boolean(node.showLabel) || node.status === 'confirmed' || node.status === 'blocked';
  return true;
}

function estimateNodeLabelBox(label: string, detailLevel: NodeLabelOverlay['detailLevel']) {
  if (detailLevel === 'rail') {
    return { width: PROJECT_STACK_3D_LABEL_RAIL_WIDTH, height: PROJECT_STACK_3D_LABEL_RAIL_HEIGHT };
  }
  const width = clamp(32 + label.length * (detailLevel === 'compact' ? 14 : 15), 96, detailLevel === 'compact' ? 188 : 220);
  const height = detailLevel === 'compact' ? 30 : 32;
  return { width, height };
}

function makeNodeLabelBox(x: number, y: number, width: number, height: number): LabelBox {
  return { left: x, top: y, right: x + width, bottom: y + height };
}

function labelBoxesIntersect(a: LabelBox, b: LabelBox) {
  return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
}

function labelBoxFitsCanvas(box: LabelBox) {
  return (
    box.left >= NODE_LABEL_SAFE_AREA.left &&
    box.top >= NODE_LABEL_SAFE_AREA.top &&
    box.right <= VIEW_W - NODE_LABEL_SAFE_AREA.right &&
    box.bottom <= VIEW_H - NODE_LABEL_SAFE_AREA.bottom
  );
}

function getCandidateLabelPosition(anchorX: number, anchorY: number, candidate: LabelCandidate, width: number, height: number) {
  let x = anchorX + candidate.dx;
  if (candidate.anchor === 'right') x -= width;
  if (candidate.anchor === 'center') x -= width / 2;
  return {
    x,
    y: anchorY + candidate.dy - height / 2,
  };
}

function getLayerStackContentBounds(
  positions: Map<StackLayerId, { x: number; y: number; opacity: number }>,
  pitch: number
) {
  const xs: number[] = [];
  const ys: number[] = [];

  STACK_LAYERS.forEach(layer => {
    const position = positions.get(layer.id) ?? { x: OVERVIEW_CENTER_X, y: OVERVIEW_BASE_Y, opacity: 1 };
    const planePoints = makePlanePoints(position.x, position.y, pitch);
    planePoints.forEach(point => {
      xs.push(point.x);
      ys.push(point.y);
    });

    const anchorPoint = planePoints.reduce((leftMost, point) => (point.x < leftMost.x ? point : leftMost), planePoints[0]);
    xs.push(anchorPoint.x - 230, anchorPoint.x + 18);
    ys.push(position.y - 38, position.y + 34);
  });

  return {
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
}

function projectPlanePoint(cx: number, cy: number, localX: number, localY: number, pitch: number): ProjectedPoint {
  return {
    x: cx + (localX + localY) * PLANE_PROJECT_SCALE,
    y: cy + (localY - localX) * PLANE_PROJECT_SCALE * pitch,
  };
}

function projectNodePoint(cx: number, cy: number, node: StackNode & { bypassClamp?: boolean }, pitch: number): ProjectedPoint {
  const safeHalf = PLANE_SIZE / 2 - node.size - 22;
  return projectPlanePoint(
    cx,
    cy,
    node.bypassClamp ? node.x : clamp(node.x, -safeHalf, safeHalf),
    node.bypassClamp ? node.y : clamp(node.y, -safeHalf, safeHalf),
    pitch
  );
}

function makePlanePoints(cx: number, cy: number, pitch: number): ProjectedPoint[] {
  const half = PLANE_SIZE / 2;
  return [
    projectPlanePoint(cx, cy, half, -half, pitch),
    projectPlanePoint(cx, cy, half, half, pitch),
    projectPlanePoint(cx, cy, -half, half, pitch),
    projectPlanePoint(cx, cy, -half, -half, pitch),
  ];
}

function makePlaneTextureLines(cx: number, cy: number, pitch: number, step = 28): ProjectedLine[] {
  const half = PLANE_SIZE / 2;
  const lines: ProjectedLine[] = [];
  for (let offset = -half + step; offset < half; offset += step) {
    lines.push({
      from: projectPlanePoint(cx, cy, offset, -half, pitch),
      to: projectPlanePoint(cx, cy, offset, half, pitch),
    });
    lines.push({
      from: projectPlanePoint(cx, cy, -half, offset, pitch),
      to: projectPlanePoint(cx, cy, half, offset, pitch),
    });
  }
  return lines;
}

function pointsAttribute(points: ProjectedPoint[]) {
  return points.map(point => `${point.x},${point.y}`).join(' ');
}

function pointInPolygon(point: ProjectedPoint, polygon: ProjectedPoint[]) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x;
    const yi = polygon[i].y;
    const xj = polygon[j].x;
    const yj = polygon[j].y;
    const intersects = yi > point.y !== yj > point.y && point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi;
    if (intersects) inside = !inside;
  }
  return inside;
}

export function ProjectGrowthCanvasView({
  overview,
  projectLabel,
  tabs,
  onAdvisorPrefill,
  sessionId,
  onOpenGeoWorkspace,
}: ProjectGrowthCanvasViewProps) {
  const geoThesis = useGeoStore(state => state.geoThesis);
  const thesisLoading = useGeoStore(state => state.thesisLoading);

  const viewportRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const canvasAnimationRef = useRef<number | null>(null);
  const modeTransitionTimeoutRef = useRef<number | null>(null);
  const twoDOverlayFrameRef = useRef<number | null>(null);
  const hasUserAdjustedCanvasViewRef = useRef(false);
  const canvasViewRef = useRef<CanvasViewTransform>(INITIAL_STACK_CANVAS_VIEW);
  const [canvasView, setCanvasView] = useState<CanvasViewTransform>(INITIAL_STACK_CANVAS_VIEW);
  const [svgViewScale, setSvgViewScale] = useState(1);
  const [interactivePitch, setPitch] = useState(0.58);
  const [viewMode, setViewMode] = useState<'3d' | '2d'>('3d');
  const [isModeTransitioning, setIsModeTransitioning] = useState(false);
  const [isTwoDOverlayMounted, setIsTwoDOverlayMounted] = useState(false);
  const [isTwoDOverlayVisible, setIsTwoDOverlayVisible] = useState(false);
  const flatteningProgress = useAnimatedNumber(viewMode === '3d' ? 0 : 1, 300);
  const pitch = interactivePitch * (1 - flatteningProgress);
  const [layerSpacing, setLayerSpacing] = useState(190); // 层间距收紧以适应更大平面尺寸（原 225）
  const [dragStart, setDragStart] = useState<{
    x: number;
    y: number;
    startView: CanvasViewTransform;
    startPitch: number;
    mode: DragMode;
  } | null>(null);
  const [selectedLayerId, setSelectedLayerId] = useState<StackLayerId | null>(DEFAULT_ACTIVE_LAYER_ID);
  const [focusedLayerAnchor, setFocusedLayerAnchor] = useState<{ layerId: StackLayerId; y: number } | null>(null);
  // 初始默认选中 L1 任务×位置对账节点（项目第一判断）
  const [selectedNodeId, setSelectedNodeId] = useState<string>('coherence_matrix');
  const [panelSelectionMode, setPanelSelectionMode] = useState<PanelSelectionMode>('node');
  const [nodeStatusOverrides, setNodeStatusOverrides] = useState<Record<string, StackNodeStatus>>({});
  const [dismissedExpandedLayers, setDismissedExpandedLayers] = useState<Partial<Record<StackLayerId, boolean>>>({});
  const [query, setQuery] = useState('');
  const [isRehearsalOpen, setIsRehearsalOpen] = useState(false);
  const [selectedScopeId, setSelectedScopeId] = useState('guest_cluster_a');
  const [bubbleSelection, setBubbleSelection] = useState<BubbleSelectionInfo>({ level: null, bubble: null, zone: null, room: null, adjacencies: [], navigate: () => {} });
  // 平面推演悬浮工作台 — 每个 tile 自己的 portal，点击携带 zone 上下文打开
  const [planOverlayOpen, setPlanOverlayOpen] = useState(false);
  const [planOverlayCtx, setPlanOverlayCtx] = useState<{
    zoneId: string;
    zoneLabel: string;
    sublabel: string;
    maturity: number;
    bindingState: 'unbound' | 'candidate' | 'bound';
  } | null>(null);

  // hover 不联动右侧白色面板内容；面板仅响应 click 选中
  const effectiveStackNodes = useMemo(
    () => STACK_NODES.map(node => (nodeStatusOverrides[node.id] ? { ...node, status: nodeStatusOverrides[node.id] } : node)),
    [nodeStatusOverrides]
  );
  const layerCompletionById = useMemo(
    () =>
      new Map(
        STACK_LAYERS.map(layer => [layer.id, getLayerCompletion(layer.id, effectiveStackNodes)] as const)
      ),
    [effectiveStackNodes]
  );
  const panelNodeId = selectedNodeId;
  const selectedNodeLayerId = layerById(effectiveStackNodes.find(node => node.id === selectedNodeId)?.layerId ?? DEFAULT_ACTIVE_LAYER_ID).id;
  const activeLayerId = selectedLayerId ?? selectedNodeLayerId;
  const activeLayer = layerById(activeLayerId);
  const selectedScope = REHEARSAL_SCOPES.find(scope => scope.id === selectedScopeId) ?? REHEARSAL_SCOPES[0];
  const selectedScopeBuildingIds = new Set(selectedScope.buildingIds);
  const fixedNodeScale = 1 / Math.sqrt(Math.max(canvasView.zoom, 0.001));
  const nodePerspectiveYScale = clamp(pitch, 0.36, 0.82);
  const animatedFocusSpread = useAnimatedNumber(selectedLayerId ? FOCUSED_UPPER_LAYER_GAP : 0, 260);
  const animatedLayerSpacing = useAnimatedNumber(layerSpacing, 180);
  const labelScreenScale = PROJECT_STACK_FIXED_LABEL_SCALE / Math.max(canvasView.zoom * svgViewScale, 0.001);
  const layerLabelWorldGap = PROJECT_STACK_LABEL_TO_CONTENT_GAP / Math.max(canvasView.zoom * svgViewScale, 0.001);

  useEffect(() => {
    canvasViewRef.current = canvasView;
  }, [canvasView]);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;

    const updateScale = () => {
      const rect = svg.getBoundingClientRect();
      if (rect.width <= 0) return;
      const screenMatrix = svg.getScreenCTM();
      const nextScale = screenMatrix?.a && screenMatrix.a > 0
        ? screenMatrix!.a
        : Math.min(rect.width / VIEW_W, rect.height / VIEW_H);
      setSvgViewScale(nextScale);
      if (!hasUserAdjustedCanvasViewRef.current && screenMatrix?.a && screenMatrix.a > 0) {
        const initialView = getInitialStackCanvasView(nextScale, screenMatrix.e - rect.left);
        canvasViewRef.current = initialView;
        setCanvasView(initialView);
      }
    };

    updateScale();
    const frameId = requestAnimationFrame(updateScale);
    const observer = new ResizeObserver(updateScale);
    observer.observe(svg);
    return () => {
      cancelAnimationFrame(frameId);
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    return () => {
      if (canvasAnimationRef.current) cancelAnimationFrame(canvasAnimationRef.current);
      if (twoDOverlayFrameRef.current) cancelAnimationFrame(twoDOverlayFrameRef.current);
      if (modeTransitionTimeoutRef.current) window.clearTimeout(modeTransitionTimeoutRef.current);
    };
  }, []);

  // Clear rehearsal-zone bubble selection when user navigates away from L5/output_results
  useEffect(() => {
    if (selectedLayerId && selectedLayerId !== 'output_results' && bubbleSelection.bubble) {
      bubbleSelection.navigate(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedLayerId, bubbleSelection.bubble]);

  const animateCanvasViewTo = useCallback((target: CanvasViewTransform, duration = 420) => {
    if (canvasAnimationRef.current) cancelAnimationFrame(canvasAnimationRef.current);
    const start = canvasViewRef.current;
    const delta = {
      x: target.x - start.x,
      y: target.y - start.y,
      zoom: target.zoom - start.zoom,
    };
    if (Math.abs(delta.x) + Math.abs(delta.y) + Math.abs(delta.zoom) < 0.01) {
      setCanvasView(target);
      return;
    }

    const startTime = performance.now();
    const tick = (now: number) => {
      const progress = clamp((now - startTime) / duration, 0, 1);
      const eased = easeOutCubic(progress);
      const next = {
        x: start.x + delta.x * eased,
        y: start.y + delta.y * eased,
        zoom: start.zoom + delta.zoom * eased,
      };
      canvasViewRef.current = next;
      setCanvasView(next);
      if (progress < 1) canvasAnimationRef.current = requestAnimationFrame(tick);
    };
    canvasAnimationRef.current = requestAnimationFrame(tick);
  }, []);

  const requestViewMode = useCallback((nextMode: '3d' | '2d') => {
    if (nextMode === viewMode && !isModeTransitioning) return;
    if (modeTransitionTimeoutRef.current) {
      window.clearTimeout(modeTransitionTimeoutRef.current);
      modeTransitionTimeoutRef.current = null;
    }
    if (twoDOverlayFrameRef.current) {
      cancelAnimationFrame(twoDOverlayFrameRef.current);
      twoDOverlayFrameRef.current = null;
    }

    if (nextMode === '2d') {
      setIsTwoDOverlayVisible(false);
      setIsTwoDOverlayMounted(true);
      setIsModeTransitioning(true);
      setViewMode('2d');
      modeTransitionTimeoutRef.current = window.setTimeout(() => {
        twoDOverlayFrameRef.current = requestAnimationFrame(() => {
          setIsTwoDOverlayVisible(true);
          twoDOverlayFrameRef.current = null;
        });
        modeTransitionTimeoutRef.current = window.setTimeout(() => {
          setIsModeTransitioning(false);
          modeTransitionTimeoutRef.current = null;
        }, 190);
      }, 190);
      return;
    }

    setIsTwoDOverlayVisible(false);
    setIsModeTransitioning(true);
    setViewMode('3d');
    modeTransitionTimeoutRef.current = window.setTimeout(() => {
      setIsTwoDOverlayMounted(false);
      setIsModeTransitioning(false);
      modeTransitionTimeoutRef.current = null;
    }, 360);
  }, [isModeTransitioning, viewMode]);

  const layerPositions = useMemo(() => {
    const activeIndex = activeLayer.index;
    const naturalActiveY = OVERVIEW_BASE_Y - activeIndex * animatedLayerSpacing;
    const anchorOffset =
      focusedLayerAnchor?.layerId === activeLayerId ? focusedLayerAnchor.y - naturalActiveY : 0;
    return new Map(
      STACK_LAYERS.map(layer => {
        const focusSpread = layer.index > activeIndex ? animatedFocusSpread : 0;
        return [
          layer.id,
          {
            x: OVERVIEW_CENTER_X,
            y: OVERVIEW_BASE_Y + anchorOffset - layer.index * animatedLayerSpacing - focusSpread,
            opacity: layer.id === activeLayerId ? 1 : 0.84,
          },
        ];
      })
    );
  }, [activeLayer.index, activeLayerId, animatedFocusSpread, animatedLayerSpacing, focusedLayerAnchor]);

  const displayLayerPositions = useMemo(() => {
    return new Map(
      STACK_LAYERS.map(layer => {
        const position = layerPositions.get(layer.id) ?? { x: OVERVIEW_CENTER_X, y: OVERVIEW_BASE_Y, opacity: 1 };
        const twoDPoint = getTwoDLayerPoint(layer);
        return [
          layer.id,
          {
            x: position.x * (1 - flatteningProgress) + twoDPoint.x * flatteningProgress,
            y: position.y * (1 - flatteningProgress) + twoDPoint.y * flatteningProgress,
            opacity: position.opacity,
          },
        ];
      })
    );
  }, [flatteningProgress, layerPositions]);

  const projectedNodes = useMemo(() => {
    const lowerQuery = query.trim().toLowerCase();
    const layerNodeCounts = new Map<string, number>();
    const layerNodeIndex = new Map<string, number>();
    const activeNodes = sortStackNodesByState(effectiveStackNodes.filter(node => !isDismissedNode(node)));
    activeNodes.forEach(node => {
      layerNodeCounts.set(node.layerId, (layerNodeCounts.get(node.layerId) || 0) + 1);
    });

    const nodes = activeNodes.map(node => {
      const idx = layerNodeIndex.get(node.layerId) ?? 0;
      layerNodeIndex.set(node.layerId, idx + 1);

      const layer = layerById(node.layerId);
      const position = layerPositions.get(node.layerId) ?? { x: OVERVIEW_CENTER_X, y: OVERVIEW_BASE_Y, opacity: 1 };
      
      const screen3D = projectNodePoint(position.x, position.y, node, pitch);

      const twoDLayerPoint = getTwoDLayerPoint(layer);
      const columnIndex = Math.floor(idx / TWO_D_NODE_ROWS_PER_COLUMN);
      const rowIndex = idx % TWO_D_NODE_ROWS_PER_COLUMN;
      const targetScreenX = twoDLayerPoint.x + TWO_D_NODE_START_OFFSET_X + columnIndex * TWO_D_NODE_COLUMN_GAP;
      const targetScreenY = twoDLayerPoint.y + TWO_D_NODE_START_OFFSET_Y + rowIndex * TWO_D_NODE_ROW_GAP;

      const screen = {
        x: screen3D.x * (1 - flatteningProgress) + targetScreenX * flatteningProgress,
        y: screen3D.y * (1 - flatteningProgress) + targetScreenY * flatteningProgress
      };

      return { ...node, screen };
    });

    if (!lowerQuery) return nodes;
    return nodes.filter(node => {
      const layer = layerById(node.layerId);
      return `${node.label} ${node.description} ${layer.title} ${node.sourceObject}`.toLowerCase().includes(lowerQuery);
    });
  }, [effectiveStackNodes, layerPositions, pitch, query, flatteningProgress]);

  const allProjectedNodes = useMemo(() => {
    return effectiveStackNodes.map(node => {
      const position = layerPositions.get(node.layerId) ?? { x: OVERVIEW_CENTER_X, y: OVERVIEW_BASE_Y, opacity: 1 };
      return {
        ...node,
        screen: projectNodePoint(position.x, position.y, node, pitch),
      };
    });
  }, [effectiveStackNodes, layerPositions, pitch]);

  const nodeById = useMemo(() => new Map(allProjectedNodes.map(node => [node.id, node])), [allProjectedNodes]);
  const selectedNode = nodeById.get(panelNodeId) ?? null;
  const selectedLayer = selectedNode ? layerById(selectedNode.layerId) : activeLayer;
  const selectedLayerNodes = useMemo(
    () => effectiveStackNodes.filter(node => node.layerId === selectedLayer.id),
    [effectiveStackNodes, selectedLayer.id]
  );
  const selectedLayerActiveNodes = useMemo(
    () => sortStackNodesByState(selectedLayerNodes.filter(node => !isDismissedNode(node))),
    [selectedLayerNodes]
  );
  const selectedLayerDismissedNodes = useMemo(
    () => selectedLayerNodes.filter(isDismissedNode),
    [selectedLayerNodes]
  );
  const selectedLayerCompletion = layerCompletionById.get(selectedLayer.id) ?? { confirmedCount: 0, totalCount: 0, ratio: 0 };
  const dismissedNodesByLayer = useMemo(() => {
    const map = new Map<StackLayerId, StackNode[]>();
    effectiveStackNodes.filter(isDismissedNode).forEach(node => {
      const nodes = map.get(node.layerId) ?? [];
      nodes.push(node);
      map.set(node.layerId, nodes);
    });
    return map;
  }, [effectiveStackNodes]);

  const layerLabelOverlays = useMemo<LayerLabelOverlay[]>(() => {
    return STACK_LAYERS.map(layer => {
      const position = displayLayerPositions.get(layer.id) ?? { x: OVERVIEW_CENTER_X, y: OVERVIEW_BASE_Y, opacity: 1 };
      const planePoints = makePlanePoints(position.x, position.y, pitch);
      const anchorPoint = planePoints.reduce((leftMost, point) => (point.x < leftMost.x ? point : leftMost), planePoints[0]);
      return {
        layer,
        x: anchorPoint.x - layerLabelWorldGap,
        y: position.y,
        anchorX: anchorPoint.x,
        anchorY: anchorPoint.y,
        isActive: layer.id === activeLayerId,
      };
    });
  }, [activeLayerId, displayLayerPositions, layerLabelWorldGap, pitch]);

  const nodeLabelOverlays = useMemo<NodeLabelOverlay[]>(() => {
    const upperPlaneByLayer = new Map(
      STACK_LAYERS.map(layer => {
        const position = displayLayerPositions.get(layer.id) ?? { x: OVERVIEW_CENTER_X, y: OVERVIEW_BASE_Y, opacity: 1 };
        return [layer.id, makePlanePoints(position.x, position.y, pitch)] as const;
      })
    );
    const lod = getNodeLabelLod(canvasView.zoom);
    const labelLimit = getNodeLabelLimit(lod);
    const hasQuery = Boolean(query.trim());
    const placedBoxes: LabelBox[] = [];
    const overlays: NodeLabelOverlay[] = [];

    if (flatteningProgress <= 0.5) {
      const activeLayerPosition = displayLayerPositions.get(activeLayerId) ?? { x: OVERVIEW_CENTER_X, y: OVERVIEW_BASE_Y, opacity: 1 };
      const activePlanePoints = upperPlaneByLayer.get(activeLayerId) ?? makePlanePoints(activeLayerPosition.x, activeLayerPosition.y, pitch);
      const planeLeft = Math.min(...activePlanePoints.map(point => point.x));
      const planeCenterY = activeLayerPosition.y;
      const railStartX = canvasView.x + (planeLeft + PROJECT_STACK_3D_LABEL_RAIL_INSET_X) * canvasView.zoom;
      const activeLayerNodes = projectedNodes
        .filter(node => node.layerId === activeLayerId)
        .sort((a, b) => {
          const stateOrder = compareStackNodesByState(a, b);
          if (stateOrder !== 0) return stateOrder;
          return getNodeLabelPriority(b, activeLayerId, selectedNodeId) - getNodeLabelPriority(a, activeLayerId, selectedNodeId);
        });
      const visibleLimit = hasQuery
        ? activeLayerNodes.length
        : lod <= 0
          ? Math.max(1, Math.min(labelLimit || 3, activeLayerNodes.length))
          : lod === 1
            ? Math.min(6, activeLayerNodes.length)
            : activeLayerNodes.length;
      const visibleNodes = activeLayerNodes.slice(0, visibleLimit);
      const selectedActiveNode = activeLayerNodes.find(node => node.id === selectedNodeId);
      if (selectedActiveNode && !visibleNodes.some(node => node.id === selectedActiveNode.id)) {
        visibleNodes.push(selectedActiveNode);
      }
      const rowsPerColumn = Math.max(1, Math.ceil(visibleNodes.length / 2));
      const railBlockHeight =
        PROJECT_STACK_3D_LABEL_RAIL_HEIGHT +
        (rowsPerColumn - 1) * PROJECT_STACK_3D_LABEL_RAIL_ROW_GAP;
      const railStartY = canvasView.y + planeCenterY * canvasView.zoom - railBlockHeight / 2;

      visibleNodes.forEach((node, index) => {
        const columnIndex = Math.floor(index / rowsPerColumn);
        const rowIndex = index % rowsPerColumn;
        overlays.push({
          node,
          label: getStackRailLabel(node.label),
          x: railStartX + columnIndex * PROJECT_STACK_3D_LABEL_RAIL_COLUMN_GAP,
          y: railStartY + rowIndex * PROJECT_STACK_3D_LABEL_RAIL_ROW_GAP,
          isActiveLayer: true,
          detailLevel: 'rail',
        });
      });

      return overlays;
    }

    projectedNodes
      .map(node => {
        const nodeLayer = layerById(node.layerId);
        const isActiveLayer = node.layerId === activeLayerId;
        const isCoveredByUpperLayer = flatteningProgress > 0.5 ? false : !isActiveLayer && STACK_LAYERS.some(layer => {
            if (layer.index <= nodeLayer.index) return false;
            const upperPlane = upperPlaneByLayer.get(layer.id);
            return upperPlane ? pointInPolygon(node.screen, upperPlane) : false;
          });
        return {
          node,
          x: node.screen.x + (1 - flatteningProgress) * 22 * fixedNodeScale,
            y: node.screen.y + (1 - flatteningProgress) * (node.size * 0.54 * fixedNodeScale * -1),
          isActiveLayer,
          isCoveredByUpperLayer,
          priority: getNodeLabelPriority(node, activeLayerId, selectedNodeId),
        };
      })
      .filter(overlay => !overlay.isCoveredByUpperLayer)
      .filter(overlay => flatteningProgress > 0.5 ? true : shouldConsiderNodeLabel(overlay.node, lod, activeLayerId, selectedNodeId, hasQuery))
      .sort((a, b) => b.priority - a.priority)
      .some(overlay => {
        if (flatteningProgress <= 0.5 && overlays.length >= labelLimit && overlay.node.id !== selectedNodeId) return false;

        const detailLevel: NodeLabelOverlay['detailLevel'] = flatteningProgress > 0.5 ? 'list' : lod <= 1 ? 'compact' : 'normal';
        const label = overlay.node.label;
        const estimatedBox = estimateNodeLabelBox(label, detailLevel === 'list' ? 'normal' : detailLevel);
        const width = detailLevel === 'list' ? TWO_D_NODE_LABEL_WIDTH : estimatedBox.width;
        const height = detailLevel === 'list' ? TWO_D_NODE_LABEL_HEIGHT : estimatedBox.height;
        const anchorX = canvasView.x + overlay.x * canvasView.zoom;
        const anchorY = canvasView.y + overlay.y * canvasView.zoom;

        if (flatteningProgress > 0.5) {
          const position = {
            x: anchorX + TWO_D_NODE_LABEL_OFFSET_X,
            y: anchorY - height / 2,
          };
          overlays.push({
            node: overlay.node,
            label,
            x: position.x,
            y: position.y,
            isActiveLayer: overlay.isActiveLayer,
            detailLevel,
          });
          return false;
        }
        for (const candidate of NODE_LABEL_CANDIDATES) {
          const position = getCandidateLabelPosition(anchorX, anchorY, candidate, width, height);
          const box = makeNodeLabelBox(position.x, position.y, width, height);
          if (!labelBoxFitsCanvas(box)) continue;
          if (placedBoxes.some(placedBox => labelBoxesIntersect(box, placedBox))) continue;
          placedBoxes.push(box);
          overlays.push({
            node: overlay.node,
            label,
            x: position.x,
            y: position.y,
            isActiveLayer: overlay.isActiveLayer,
            detailLevel,
          });
          break;
        }
        return false;
      });

    return overlays;
  }, [activeLayerId, canvasView.x, canvasView.y, canvasView.zoom, fixedNodeScale, displayLayerPositions, pitch, projectedNodes, query, selectedNodeId, flatteningProgress]);

  const zoomCanvasAt = (clientX: number, clientY: number, factor: number) => {
    hasUserAdjustedCanvasViewRef.current = true;
    const rect = viewportRef.current?.getBoundingClientRect();
    if (!rect) {
      setCanvasView(view => ({ ...view, zoom: clamp(view.zoom * factor, MIN_CANVAS_ZOOM, MAX_CANVAS_ZOOM) }));
      return;
    }
    const pointerX = ((clientX - rect.left) / rect.width) * VIEW_W;
    const pointerY = ((clientY - rect.top) / rect.height) * VIEW_H;
    setCanvasView(view =>
      zoomCanvasViewAt(view, { left: 0, top: 0 }, pointerX, pointerY, factor, { minZoom: MIN_CANVAS_ZOOM, maxZoom: MAX_CANVAS_ZOOM })
    );
  };

  const focusLayerInViewport = (layerY: number) => {
    const rect = viewportRef.current?.getBoundingClientRect();
    const leftSafe = PROJECT_STACK_LEFT_INSET;
    const rightSafe = VIEW_W - 64;
    const availableWidth = Math.max(360, rightSafe - leftSafe);
    const planePoints = makePlanePoints(OVERVIEW_CENTER_X, layerY, pitch);
    const minX = Math.min(...planePoints.map(point => point.x));
    const maxX = Math.max(...planePoints.map(point => point.x));
    const minY = Math.min(...planePoints.map(point => point.y));
    const maxY = Math.max(...planePoints.map(point => point.y));
    const planeWidth = Math.max(maxX - minX, 1);
    const targetZoom = clamp((availableWidth / planeWidth) * 0.86, MIN_CANVAS_ZOOM, MAX_CANVAS_ZOOM);
    const targetCenterX = leftSafe + availableWidth * 0.56;
    const targetCenterY = VIEW_H * 0.5;
    animateCanvasViewTo({
      x: targetCenterX - ((minX + maxX) / 2) * targetZoom,
      y: targetCenterY - ((minY + maxY) / 2) * targetZoom,
      zoom: targetZoom,
    });
  };

  const focusRehearsalZone = useCallback(() => {
    const rect = viewportRef.current?.getBoundingClientRect();
    const leftSafe = PROJECT_STACK_LEFT_INSET;
    const rightSafe = VIEW_W - 64;
    const availableWidth = Math.max(480, rightSafe - leftSafe);
    const availableHeight = VIEW_H * 0.84;
    const targetZoom = clamp(
      Math.min((availableWidth / REHEARSAL_ZONE.w) * 0.94, (availableHeight / REHEARSAL_ZONE.h) * 0.98),
      MIN_CANVAS_ZOOM,
      MAX_CANVAS_ZOOM
    );
    const targetCenterX = leftSafe + availableWidth * 0.56;
    const targetCenterY = VIEW_H * 0.5;
    animateCanvasViewTo(
      {
        x: targetCenterX - (REHEARSAL_ZONE.x + REHEARSAL_ZONE.w / 2) * targetZoom,
        y: targetCenterY - (REHEARSAL_ZONE.y + REHEARSAL_ZONE.h / 2) * targetZoom,
        zoom: targetZoom,
      },
      560
    );
  }, [animateCanvasViewTo]);

  const handleWheel = (event: WheelEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (isModeTransitioning) return;
    hasUserAdjustedCanvasViewRef.current = true;
    if (viewMode === '2d' && !event.ctrlKey && !event.metaKey) {
      setCanvasView(view => ({
        ...view,
        x: view.x - event.deltaX,
        y: view.y - event.deltaY,
      }));
      return;
    }
    if (event.shiftKey) {
      setLayerSpacing(current => clamp(current - event.deltaY * 0.18, 130, 280));
      return;
    }
    zoomCanvasAt(event.clientX, event.clientY, getWheelZoomFactor(event.deltaY));
  };

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (isModeTransitioning) return;
    hasUserAdjustedCanvasViewRef.current = true;
    const mode: DragMode = event.altKey || event.button === 2 ? 'tilt' : 'pan';
    setDragStart({
      x: event.clientX,
      y: event.clientY,
      startView: canvasView,
      startPitch: pitch,
      mode,
    });
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!dragStart) return;
    if (dragStart.mode === 'tilt') {
      setPitch(clamp(dragStart.startPitch + (event.clientY - dragStart.y) * 0.0028, 0.28, 0.82));
      return;
    }
    const rect = viewportRef.current?.getBoundingClientRect();
    const scaleX = rect ? VIEW_W / rect.width : 1;
    const scaleY = rect ? VIEW_H / rect.height : 1;
    setCanvasView({
      ...dragStart.startView,
      x: dragStart.startView.x + (event.clientX - dragStart.x) * scaleX,
      y: dragStart.startView.y + (event.clientY - dragStart.y) * scaleY,
    });
  };

  const stopDragging = (event: PointerEvent<HTMLDivElement>) => {
    setDragStart(null);
    try {
      event.currentTarget.releasePointerCapture(event.pointerId);
    } catch {
      // pointer may already be released
    }
  };

  const handleLayerFocus = (layerId: StackLayerId) => {
    hasUserAdjustedCanvasViewRef.current = true;
    const firstNode = effectiveStackNodes.find(node => node.layerId === layerId && !isDismissedNode(node));
    if (viewMode === '2d') {
      setFocusedLayerAnchor(null);
      setSelectedLayerId(layerId);
      if (firstNode) setSelectedNodeId(firstNode.id);
      setPanelSelectionMode('layer');
      return;
    }

    const fallbackY = OVERVIEW_BASE_Y - layerById(layerId).index * animatedLayerSpacing;
    const anchorY = layerPositions.get(layerId)?.y ?? fallbackY;
    setFocusedLayerAnchor({ layerId, y: anchorY });
    setSelectedLayerId(layerId);
    if (layerId === 'output_results') {
      setIsRehearsalOpen(true);
      setSelectedScopeId(current => current || 'guest_cluster_a');
      focusRehearsalZone();
      onAdvisorPrefill?.('进入泡泡逻辑预演区：先确认项目空间组成、楼栋楼层和泡泡关系，再生成 LayoutScopeIndex。');
    } else {
      focusLayerInViewport(anchorY);
    }
    if (firstNode) setSelectedNodeId(firstNode.id);
    setPanelSelectionMode('layer');
  };

  const handleNodeClick = (node: StackNode) => {
    setSelectedNodeId(node.id);
    setSelectedLayerId(node.layerId);
    setPanelSelectionMode('node');
    onAdvisorPrefill?.(getNodeAdvisorPrompt(node));
  };

  const toggleDismissedLayer = (layerId: StackLayerId) => {
    setDismissedExpandedLayers(current => ({ ...current, [layerId]: !current[layerId] }));
  };

  const reactivateDismissedNode = (node: StackNode) => {
    setNodeStatusOverrides(current => ({ ...current, [node.id]: 'draft' }));
    setSelectedNodeId(node.id);
    setSelectedLayerId(node.layerId);
    setPanelSelectionMode('node');
    onAdvisorPrefill?.(`请把「${node.label}」从已否定记录中二次启用为待确认命题，并重新列出需要验证的依据、风险和确认动作。`);
  };

  return (
    <div
      className="cockpit-project-growth-canvas cockpit-immersive-canvas-root flex overflow-hidden min-h-0"
      style={{
        '--project-stack-left-inset': `${PROJECT_STACK_LEFT_INSET}px`,
        '--project-stack-layer-label-width': `${PROJECT_STACK_LAYER_LABEL_WIDTH}px`,
        '--project-stack-label-to-content-gap': `${PROJECT_STACK_LABEL_TO_CONTENT_GAP}px`,
      } as CSSProperties}
      onContextMenu={event => event.preventDefault()}
    >
      <div
        ref={viewportRef}
        className={`project-workspace-main-column project-workspace-canvas-column project-growth-canvas-stage cockpit-canvas-viewport relative h-full flex-1 min-w-0 overflow-hidden ${
          dragStart?.mode === 'tilt' ? 'cursor-ns-resize' : 'cursor-grab active:cursor-grabbing'
        }`}
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={stopDragging}
        onPointerCancel={stopDragging}
      >
        <svg
          ref={svgRef}
          className="h-full w-full"
          viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
          role="img"
          aria-label="Project Stack Canvas 项目结构堆栈画布"
        >
          <defs>
            <filter id="stack-shadow" x="-80%" y="-80%" width="260%" height="260%">
              <feDropShadow dx="0" dy="32" stdDeviation="24" floodColor="#000000" floodOpacity="1.0" />
            </filter>
            <pattern id="rehearsal-grid" width="18" height="18" patternUnits="userSpaceOnUse">
              <path d="M18 0H0V18" fill="none" stroke="rgba(255,255,255,0.16)" strokeWidth="1" />
            </pattern>
            <pattern id="rehearsal-diagonal" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="12" stroke="rgba(255,255,255,0.24)" strokeWidth="3" />
            </pattern>
            <marker id="rehearsal-arrow" markerWidth="9" markerHeight="9" refX="7.5" refY="4.5" orient="auto">
              <path d="M0 0L9 4.5L0 9Z" fill="rgba(226,232,240,0.72)" />
            </marker>
          </defs>

          <g transform={`translate(${canvasView.x} ${canvasView.y}) scale(${canvasView.zoom})`}>
          {[...STACK_LAYERS].sort((a, b) => a.index - b.index).map(layer => {
            const position = displayLayerPositions.get(layer.id) ?? { x: OVERVIEW_CENTER_X, y: OVERVIEW_BASE_Y, opacity: 1 };
            const isActiveLayer = layer.id === activeLayerId;
            const planePoints = makePlanePoints(position.x, position.y, pitch);
            const planeFill = isActiveLayer ? layer.fill : 'rgba(100, 116, 139, 0.26)';
            const planeStroke = isActiveLayer ? layer.color : 'rgba(203, 213, 225, 0.58)';
            const textureLines = makePlaneTextureLines(position.x, position.y, pitch, layer.index === 0 ? 22 : 30);
            return (
              <g
                key={layer.id}
                opacity={position.opacity}
                style={{ transition: 'opacity 180ms ease' }}
                onPointerDown={event => event.stopPropagation()}
                onClick={() => handleLayerFocus(layer.id)}
                className="cursor-pointer"
              >
                <polygon
                  points={pointsAttribute(planePoints)}
                  fill="var(--canvas-bg)"
                  stroke="none"
                />
                <polygon
                  points={pointsAttribute(planePoints)}
                  fill={planeFill}
                  stroke={isActiveLayer ? '#ffffff' : planeStroke}
                  strokeWidth={isActiveLayer ? 2.4 : 1.2}
                  vectorEffect="non-scaling-stroke"
                  filter="url(#stack-shadow)"
                  style={{ transition: 'fill 180ms ease, stroke 180ms ease, stroke-width 180ms ease' }}
                />
                <g opacity={isActiveLayer ? 0.16 : 0.08} pointerEvents="none">
                  {textureLines.map((line, index) => (
                    <line
                      key={`texture-${layer.id}-${index}`}
                      x1={line.from.x}
                      y1={line.from.y}
                      x2={line.to.x}
                      y2={line.to.y}
                      stroke="rgba(255,255,255,0.74)"
                      strokeWidth="0.75"
                      vectorEffect="non-scaling-stroke"
                    />
                  ))}
                </g>
                <polygon
                  points={pointsAttribute(planePoints)}
                  fill="none"
                  stroke={isActiveLayer ? 'rgba(255,255,255,0.16)' : 'rgba(255,255,255,0.08)'}
                  strokeWidth="1"
                  strokeDasharray={flatteningProgress > 0.5 ? "none" : "7 7"}
                  vectorEffect="non-scaling-stroke"
                  style={{ transition: 'stroke 180ms ease' }}
                />

              </g>
            );
          })}
          {isRehearsalOpen && (
            <g
              onPointerDown={event => event.stopPropagation()}
              className="cursor-default"
            >
              <rect
                x={REHEARSAL_ZONE.x}
                y={REHEARSAL_ZONE.y}
                width={REHEARSAL_ZONE.w}
                height={REHEARSAL_ZONE.h}
                fill="rgba(23, 29, 35, 0.72)"
                stroke="rgba(148,163,184,0.28)"
                strokeWidth="1"
                vectorEffect="non-scaling-stroke"
              />
              <text x={REHEARSAL_ZONE.x + 28} y={REHEARSAL_ZONE.y + 42} fill="#f8fafc" fontSize="22" fontWeight="800">
                泡泡逻辑预演区
              </text>
              <text x={REHEARSAL_ZONE.x + 28} y={REHEARSAL_ZONE.y + 68} fill="#94a3b8" fontSize="13">
                PSC 项目空间组成 + FFL 平面功能描述 / 生成 LayoutScopeIndex 前的空间彩排
              </text>

              <foreignObject
                x={REHEARSAL_ZONE.x}
                y={REHEARSAL_ZONE.y + 88}
                width={REHEARSAL_ZONE.w}
                height={REHEARSAL_ZONE.h - 88}
              >
                {/* @ts-expect-error xmlns required by foreignObject spec */}
                <div xmlns="http://www.w3.org/1999/xhtml" style={{ width: '100%', height: '100%' }}>
                  <BubbleZoningDiagram
                    onSelectionChange={setBubbleSelection}
                    zoom={canvasView.zoom}
                    onOpenPlan={(ctx) => {
                      setPlanOverlayCtx(ctx);
                      setPlanOverlayOpen(true);
                    }}
                  />
                </div>
              </foreignObject>
            </g>
          )}

          {!isTwoDOverlayVisible && (
          <g className="project-stack-layer-labels">
            
          {layerLabelOverlays.map(({ layer, x, y, isActive }) => {
            const completion = layerCompletionById.get(layer.id) ?? { confirmedCount: 0, totalCount: 0, ratio: 0 };
            return (
              <g key={`layer-label-svg-${layer.id}`} pointerEvents="auto">
                <g
                  transform={`translate(${x} ${y}) scale(${labelScreenScale})`}
                  onPointerDown={event => event.stopPropagation()}
                  onClick={() => handleLayerFocus(layer.id)}
                  className="cursor-pointer"
                >
                  <text
                    x={0}
                    y={-7}
                    textAnchor="end"
                    fill={isActive ? '#ffffff' : '#cbd5e1'}
                    fontSize={13}
                    fontWeight={800}
                    letterSpacing={0}
                    style={{ textShadow: '0 1px 6px rgba(0,0,0,0.82)' }}
                  >
                    {layer.title}
                  </text>
                  <text
                    x={0}
                    y={9}
                    textAnchor="end"
                    fill={isActive ? 'rgba(255,255,255,0.72)' : 'rgba(203,213,225,0.68)'}
                    fontSize={11}
                    fontWeight={650}
                    letterSpacing={0}
                    style={{ textShadow: '0 1px 5px rgba(0,0,0,0.72)' }}
                  >
                    {layer.subtitle}
                  </text>
                  <line
                    x1={-PROJECT_STACK_SVG_LAYER_METER_WIDTH}
                    y1={18}
                    x2={0}
                    y2={18}
                    stroke="rgba(255,255,255,0.12)"
                    strokeWidth={3}
                    strokeLinecap="round"
                    vectorEffect="non-scaling-stroke"
                  />
                  <line
                    x1={-PROJECT_STACK_SVG_LAYER_METER_WIDTH}
                    y1={18}
                    x2={-PROJECT_STACK_SVG_LAYER_METER_WIDTH + PROJECT_STACK_SVG_LAYER_METER_WIDTH * completion.ratio}
                    y2={18}
                    stroke={PROJECT_STACK_CONFIRMED_COLOR}
                    strokeWidth={3}
                    strokeLinecap="round"
                    vectorEffect="non-scaling-stroke"
                  />
                </g>
              </g>
            );
          })}
          </g>
          )}

          {!isTwoDOverlayVisible && (
          <g className="project-stack-node-labels">
            {nodeLabelOverlays.map(({ node, label, x, y, isActiveLayer, detailLevel }) => {
              const isSelected = selectedNodeId === node.id;
              const propositionState = getPropositionState(node.status);
              const priorityLabel = detailLevel === 'list' ? getNodePriorityLabel(node) : null;
              const worldX = (x - canvasView.x) / Math.max(canvasView.zoom, 0.001);
              const worldY = (y - canvasView.y) / Math.max(canvasView.zoom, 0.001);
              const labelWidth = detailLevel === 'list'
                ? TWO_D_NODE_LABEL_WIDTH
                : detailLevel === 'rail'
                  ? PROJECT_STACK_3D_LABEL_RAIL_WIDTH
                  : detailLevel === 'compact'
                    ? 188
                    : 220;
              const labelHeight = detailLevel === 'list'
                ? TWO_D_NODE_LABEL_HEIGHT
                : detailLevel === 'rail'
                  ? PROJECT_STACK_3D_LABEL_RAIL_HEIGHT
                  : detailLevel === 'compact'
                    ? 32
                    : 36;
              const leaderTargetY = worldY + (labelHeight * labelScreenScale) / 2;
              return (
                <g key={`node-label-svg-${node.id}`}>
                  {detailLevel === 'rail' && (
                    <line
                      x1={node.screen.x}
                      y1={node.screen.y}
                      x2={worldX - 8 * labelScreenScale}
                      y2={leaderTargetY}
                      stroke={propositionState === 'confirmed' ? 'rgba(74,222,128,0.34)' : 'rgba(226,232,240,0.22)'}
                      strokeWidth={1}
                      strokeDasharray="3 5"
                      vectorEffect="non-scaling-stroke"
                      pointerEvents="none"
                    />
                  )}
                  <g transform={`translate(${worldX} ${worldY}) scale(${labelScreenScale})`}>
                    <foreignObject
                      x={0}
                      y={0}
                      width={labelWidth}
                      height={labelHeight}
                      overflow="visible"
                    >
                      {/* @ts-expect-error xmlns required by foreignObject spec */}
                      <div xmlns="http://www.w3.org/1999/xhtml">
                        <button
                          type="button"
                          onPointerDown={event => event.stopPropagation()}
                          onClick={() => handleNodeClick(node)}
                          className={`project-stack-node-label ${
                            detailLevel === 'compact' ? 'project-stack-node-label-compact' : ''
                          } ${
                            detailLevel === 'rail' ? 'project-stack-node-label-rail' : ''
                          } ${
                            detailLevel === 'list' ? 'project-stack-node-label-list' : ''
                          } ${isActiveLayer ? 'project-stack-node-label-current-layer' : ''} ${
                            isSelected ? 'project-stack-node-label-active' : ''
                          } project-stack-node-label-${propositionState} ${getNodePriorityClass(node, 'project-stack-node-label')}`}
                          aria-label={`${label}，${getPropositionStateLabel(node.status)}`}
                        >
                          <PropositionStateIcon state={propositionState} className="project-stack-node-status-icon" />
                          <span className="project-stack-node-label-text">{label}</span>
                          {priorityLabel && (
                            <span className="project-stack-node-priority-badge">{priorityLabel}</span>
                          )}
                        </button>
                      </div>
                    </foreignObject>
                  </g>
                </g>
              );
            })}
          </g>
          )}

          {viewMode === '3d' && flatteningProgress < 0.5 && (
            <g className="project-stack-dismissed-overlays">
              {STACK_LAYERS.map(layer => {
                const dismissedNodes = dismissedNodesByLayer.get(layer.id) ?? [];
                if (dismissedNodes.length === 0 || layer.id !== activeLayerId) return null;
                const isExpanded = Boolean(dismissedExpandedLayers[layer.id]);
                const position = displayLayerPositions.get(layer.id) ?? { x: OVERVIEW_CENTER_X, y: OVERVIEW_BASE_Y, opacity: 1 };
                const panelHeight = isExpanded ? 48 + dismissedNodes.length * 30 : 36;
                return (
                  <g
                    key={`dismissed-layer-${layer.id}`}
                    transform={`translate(${position.x + 310} ${position.y + 122}) scale(${labelScreenScale})`}
                    opacity={position.opacity}
                  >
                    <foreignObject x={0} y={0} width={292} height={panelHeight} overflow="visible">
                      {/* @ts-expect-error xmlns required by foreignObject spec */}
                      <div xmlns="http://www.w3.org/1999/xhtml">
                        <div className="project-stack-dismissed-panel" onPointerDown={event => event.stopPropagation()}>
                          <button
                            type="button"
                            className="project-stack-dismissed-toggle"
                            onClick={() => toggleDismissedLayer(layer.id)}
                            aria-expanded={isExpanded}
                          >
                            {isExpanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                            <span>已否定命题</span>
                            <span className="project-stack-dismissed-count">{dismissedNodes.length}</span>
                          </button>
                          {isExpanded && (
                            <div className="project-stack-dismissed-list">
                              {dismissedNodes.map(node => (
                                <button
                                  key={`dismissed-node-${node.id}`}
                                  type="button"
                                  className={`project-stack-dismissed-node ${selectedNodeId === node.id ? 'project-stack-dismissed-node-active' : ''}`}
                                  onClick={() => handleNodeClick(node)}
                                  title={`${node.label} · 已否定`}
                                >
                                  <PropositionStateIcon state="dismissed" className="project-stack-dismissed-node-icon" />
                                  <span className="project-stack-dismissed-node-text">{node.label}</span>
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </foreignObject>
                  </g>
                );
              })}
            </g>
          )}
          </g>
        </svg>
        {isTwoDOverlayMounted && (
          <div
            className={`project-stack-2d-overlay ${isTwoDOverlayVisible ? 'project-stack-2d-overlay-visible' : ''} ${
              isTwoDOverlayVisible && !isModeTransitioning ? 'project-stack-2d-overlay-interactive' : ''
            }`}
            onPointerDown={event => event.stopPropagation()}
            onWheel={event => event.stopPropagation()}
          >
            <div className="project-stack-2d-content">
              {[...STACK_LAYERS].sort((a, b) => b.index - a.index).map(layer => {
                const layerNodes = sortStackNodesByState(effectiveStackNodes.filter(node => node.layerId === layer.id && !isDismissedNode(node)));
                const dismissedNodes = effectiveStackNodes.filter(node => node.layerId === layer.id && isDismissedNode(node));
                const isActiveLayer = layer.id === activeLayerId;
                const isDismissedExpanded = Boolean(dismissedExpandedLayers[layer.id]);
                const completion = layerCompletionById.get(layer.id) ?? { confirmedCount: 0, totalCount: 0, ratio: 0 };
                return (
                  <section
                    key={`stack-2d-layer-${layer.id}`}
                    className={`project-stack-2d-layer ${isActiveLayer ? 'project-stack-2d-layer-active' : ''}`}
                  >
                    <button
                      type="button"
                      className="project-stack-2d-layer-label"
                      onClick={() => handleLayerFocus(layer.id)}
                    >
                      <span className="project-stack-2d-layer-title">{layer.title}</span>
                      <span className="project-stack-2d-layer-subtitle">{layer.subtitle}</span>
                      <span className="project-stack-2d-layer-meter">
                        <span style={{ width: `${Math.round(completion.ratio * 100)}%` }} />
                      </span>
                    </button>
                    <div className="project-stack-2d-node-grid">
                      {layerNodes.map(node => {
                        const isSelected = selectedNodeId === node.id;
                        const propositionState = getPropositionState(node.status);
                        const priorityLabel = getNodePriorityLabel(node);
                        return (
                          <button
                            key={`stack-2d-node-${node.id}`}
                            type="button"
                            className={`project-stack-2d-node project-stack-2d-node-${propositionState} ${getNodePriorityClass(node, 'project-stack-2d-node')} ${isSelected ? 'project-stack-2d-node-active' : ''}`}
                            title={`${node.label} · ${getPropositionStateLabel(node.status)}`}
                            aria-label={`${node.label}，${getPropositionStateLabel(node.status)}`}
                            onClick={() => handleNodeClick(node)}
                          >
                            <PropositionStateIcon state={propositionState} className="project-stack-2d-node-icon" />
                            <span className="project-stack-2d-node-text">{node.label}</span>
                            {priorityLabel && (
                              <span className="project-stack-2d-node-priority-badge">{priorityLabel}</span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                    {dismissedNodes.length > 0 && (
                      <div className="project-stack-2d-dismissed project-stack-2d-dismissed-inline-group">
                        <button
                          type="button"
                          className="project-stack-2d-node project-stack-2d-node-pending project-stack-2d-dismissed-toggle-inline"
                          onClick={() => toggleDismissedLayer(layer.id)}
                          aria-expanded={isDismissedExpanded}
                        >
                          {isDismissedExpanded ? <ChevronDown className="project-stack-2d-node-icon" strokeWidth={3} /> : <ChevronRight className="project-stack-2d-node-icon" strokeWidth={3} />}
                          <span className="project-stack-2d-node-text">已否定命题 {dismissedNodes.length}</span>
                        </button>
                        {isDismissedExpanded && (
                          <div className="project-stack-2d-dismissed-grid">
                            {dismissedNodes.map(node => (
                              <button
                                key={`stack-2d-dismissed-node-${node.id}`}
                                type="button"
                                className={`project-stack-2d-node project-stack-2d-node-dismissed project-stack-2d-dismissed-node-inline ${selectedNodeId === node.id ? 'project-stack-2d-node-active' : ''}`}
                                title={`${node.label} · 已否定`}
                                aria-label={`${node.label}，已否定`}
                                onClick={() => handleNodeClick(node)}
                              >
                                <PropositionStateIcon state="dismissed" className="project-stack-2d-node-icon" />
                                <span className="project-stack-2d-node-text">{node.label}</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                      )}
                  </section>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <div className="cockpit-immersive-canvas-header">
        <div className="cockpit-immersive-canvas-header-inner flex items-center justify-between" onPointerDown={event => event.stopPropagation()} style={{ width: '100%', paddingRight: '20px' }}>
          <div className="flex items-center gap-4">
            <button
              type="button"
              className="cockpit-immersive-canvas-title text-left shrink-0"
              title={projectLabel || overview.name}
              onClick={() => onAdvisorPrefill?.('用项目结构堆栈画布解释当前项目底盘的成熟度、阻断项和下一步。')}
            >
              {projectLabel || overview.name}
            </button>
            <button
              type="button"
              className="project-stack-mode-toggle"
              onClick={() => requestViewMode(viewMode === '3d' ? '2d' : '3d')}
              data-transitioning={isModeTransitioning ? 'true' : 'false'}
              aria-label={viewMode === '2d' ? '返回图层表达' : '切换到文字列表'}
              title={viewMode === '2d' ? '返回图层表达' : '切换到文字列表'}
            >
              {viewMode === '2d' ? <Layers className="h-4 w-4" /> : <ListTree className="h-4 w-4" />}
            </button>
            
          </div>
        </div>
      </div>

      <div className="cockpit-canvas-side-panel-wrap project-workspace-middle-column cursor-default">
        <div
          className="workspace-info-panel cockpit-canvas-side-panel cursor-default"
          onPointerDown={event => event.stopPropagation()}
          onWheel={event => event.stopPropagation()}
        >
          {!bubbleSelection.bubble && !selectedLayerId && (
            <div className="cockpit-canvas-side-panel-header">
              {tabs && (
                <div className="cockpit-canvas-view-tabs">
                  {tabs.map(tab => (
                    <button
                      key={`canvas-view-tab-${tab.key}`}
                      type="button"
                      onClick={tab.onClick}
                      className={`cockpit-canvas-view-tab ${tab.active ? 'cockpit-canvas-view-tab-active' : ''}`}
                    >
                      <span>{tab.label}</span>
                      {tab.badge && <span className="cockpit-canvas-view-tab-badge">{tab.badge}</span>}
                    </button>
                  ))}
                </div>
              )}
              <input
                value={query}
                onChange={event => setQuery(event.target.value)}
                placeholder="搜索堆栈节点（例：SPG、材料、平面入口）"
                className="cockpit-canvas-search"
              />
              <div className="cockpit-canvas-source-tabs">
                {[
                  { key: 'overview', label: selectedLayerId ? '当前层' : '总览' },
                  { key: 'evidence', label: '来源绑定' },
                  { key: 'outputs', label: '输出链' },
                ].map((tab, index) => (
                  <button
                    key={`stack-source-tab-${tab.key}`}
                    type="button"
                    onClick={() => {
                      if (tab.key === 'overview') {
                        setSelectedLayerId(null);
                        setFocusedLayerAnchor(null);
                      }
                    }}
                    className={`cockpit-canvas-source-tab ${index === 0 ? 'cockpit-canvas-source-tab-active' : ''}`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="cockpit-canvas-side-panel-body">
            {bubbleSelection.bubble ? (
              /* ═══════════ 选择视图 — 面包屑 + 仅当前层细分 ═══════════ */
              <div className="space-y-3">
                {/* 头部 — 索引标识 + 面包屑 + 清除 */}
                <div className="border border-sky-300 bg-sky-50/60 px-3 py-2.5">
                  <div className="flex items-center justify-between">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-sky-700">
                      项目底盘索引 · 已选
                    </div>
                    <button
                      type="button"
                      onClick={() => bubbleSelection.navigate(null)}
                      className="text-[11px] text-slate-400 hover:text-slate-700"
                    >
                      清除选择
                    </button>
                  </div>
                  <div className="mt-1.5 flex items-center flex-wrap gap-x-1 text-[12px] leading-5">
                    <button type="button" onClick={() => bubbleSelection.navigate(null)}
                      className="text-slate-500 hover:text-slate-800">项目底盘</button>
                    <span className="text-slate-300">›</span>
                    <button type="button" onClick={() => bubbleSelection.navigate('L1')}
                      className={bubbleSelection.level === 'L1'
                        ? 'text-sky-700 font-semibold'
                        : 'text-slate-500 hover:text-slate-800'}>
                      {bubbleSelection.bubble.name}
                    </button>
                    {bubbleSelection.zone && (
                      <>
                        <span className="text-slate-300">›</span>
                        <button type="button" onClick={() => bubbleSelection.navigate('L2')}
                          className={bubbleSelection.level === 'L2'
                            ? 'text-sky-700 font-semibold'
                            : 'text-slate-500 hover:text-slate-800'}>
                          {bubbleSelection.zone.label}
                        </button>
                      </>
                    )}
                    {bubbleSelection.room && (
                      <>
                        <span className="text-slate-300">›</span>
                        <button type="button" onClick={() => bubbleSelection.navigate('L3')}
                          className={bubbleSelection.level === 'L3'
                            ? 'text-sky-700 font-semibold'
                            : 'text-slate-500 hover:text-slate-800'}>
                          {bubbleSelection.room.label}
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* 当前层卡 — L1 · 空间节点 */}
                {bubbleSelection.level === 'L1' && (
                <div className="border border-slate-200 bg-white px-4 py-3">
                  <div className="text-[10px] font-semibold tracking-[0.16em] text-slate-400">L1 · 空间节点</div>
                  <div className="mt-1.5 flex items-center gap-2">
                    <span className="text-[15px] font-semibold text-slate-950">{bubbleSelection.bubble.name}</span>
                    <span className="text-[10px] font-medium px-1.5 py-0.5 border border-slate-300 text-slate-500">
                      {bubbleSelection.bubble.group}
                    </span>
                  </div>
                  <div className="mt-0.5 text-[11px] text-slate-500">
                    面积 · {bubbleSelection.bubble.area ?? '—'}
                  </div>

                  {bubbleSelection.adjacencies.length > 0 && (
                    <div className="mt-3">
                      <div className="text-[10px] font-semibold text-slate-500">邻接关系（{bubbleSelection.adjacencies.length}）</div>
                      <ul className="mt-1.5 space-y-1">
                        {bubbleSelection.adjacencies.map(adj => (
                          <li key={adj.id} className="flex items-center justify-between text-[11px]">
                            <span className="text-slate-700">
                              <span className="text-slate-400 mr-1.5">·</span>
                              {adj.name}
                              {adj.bidir && <span className="ml-1 text-slate-400">⇆</span>}
                              {adj.tag && <span className="ml-1.5 text-[10px] text-slate-400">{adj.tag}</span>}
                            </span>
                            <span className={`text-[10px] ${adj.relation === '已确认' ? 'text-emerald-600' : 'text-amber-600'}`}>
                              {adj.relation}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="mt-3 pt-2 border-t border-dashed border-slate-200 text-[10px] leading-4 text-slate-400">
                    真相源 · PSC.node[{bubbleSelection.bubble.id}]
                  </div>
                </div>
                )}

                {/* 当前层卡 — L2 · 区域平面 */}
                {bubbleSelection.level === 'L2' && (
                  bubbleSelection.zone ? (
                    <div className="border border-slate-200 bg-white px-4 py-3">
                      <div className="text-[10px] font-semibold tracking-[0.16em] text-slate-400">L2 · 区域平面</div>
                      <div className="mt-1.5 text-[15px] font-semibold text-slate-950">{bubbleSelection.zone.label}</div>
                      <div className="mt-0.5 text-[11px] text-slate-500">
                        {bubbleSelection.zone.sublabel} · 房间 {bubbleSelection.zone.roomCount} 个
                      </div>
                      <div className="mt-2 flex items-center gap-2">
                        <div className="flex-1 h-1 bg-slate-100 overflow-hidden">
                          <div className="h-full bg-sky-500" style={{ width: `${Math.round(bubbleSelection.zone.maturity * 100)}%` }} />
                        </div>
                        <span className="text-[10px] font-semibold text-slate-500">{Math.round(bubbleSelection.zone.maturity * 100)}%</span>
                      </div>

                      <div className="mt-3">
                        <div className="text-[10px] font-semibold text-slate-500">房间清单</div>
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {bubbleSelection.zone.rooms.map((r, i) => (
                            <span key={i}
                              className="text-[10px] px-1.5 py-0.5 border border-slate-200 bg-slate-50 text-slate-600"
                            >
                              {r.label}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="mt-3 pt-2 border-t border-dashed border-slate-200 text-[10px] leading-4 text-slate-400">
                        真相源 · FFL.zone[{bubbleSelection.zone.id}]
                      </div>
                    </div>
                  ) : (
                    <div className="border border-dashed border-slate-300 bg-slate-50 px-4 py-3">
                      <div className="text-[10px] font-semibold tracking-[0.16em] text-slate-400">L2 · 区域平面</div>
                      <div className="mt-1.5 text-[12px] text-slate-400">暂无明细</div>
                      <div className="mt-0.5 text-[11px] leading-5 text-slate-400">该空间未挂载 FFL，房间数据待补充</div>
                    </div>
                  )
                )}

                {/* 当前层卡 — L3 · 房间细节 */}
                {bubbleSelection.level === 'L3' && bubbleSelection.room && (
                  <div className="border border-slate-200 bg-white px-4 py-3">
                    <div className="text-[10px] font-semibold tracking-[0.16em] text-slate-400">L3 · 房间细节</div>
                    <div className="mt-1.5 text-[15px] font-semibold text-slate-950">{bubbleSelection.room.label}</div>
                    {bubbleSelection.room.func && (
                      <div className="mt-1 text-[11px] leading-5 text-slate-600">{bubbleSelection.room.func}</div>
                    )}
                    {bubbleSelection.room.texture && bubbleSelection.room.texture !== 'none' && (
                      <div className="mt-2 text-[10px] text-slate-500">
                        填充类型 · {({
                          stipple: '点纹（公共到达）',
                          hatch:   '斜纹（社交功能）',
                          xhatch:  '交叉纹（核心功能）',
                          hlines:  '横线（居住单元）',
                          vlines:  '竖线（服务后勤）',
                        } as Record<string, string>)[bubbleSelection.room.texture] ?? bubbleSelection.room.texture}
                      </div>
                    )}
                    <div className="mt-3 pt-2 border-t border-dashed border-slate-200 text-[10px] leading-4 text-slate-400">
                      真相源 · FFL.zone[{bubbleSelection.zone?.id}].room[{bubbleSelection.room.label}]
                    </div>
                  </div>
                )}

                {/* 下游动作 */}
                <div className="flex flex-col gap-1.5 pt-1">
                  <button
                    type="button"
                    onClick={() => onAdvisorPrefill?.(`分析「${bubbleSelection.bubble?.name}」的空间组成、邻接关系和下游解锁缺口。`)}
                    className="text-[11px] font-semibold text-sky-600 hover:text-sky-800 text-left"
                  >
                    → 让方案高参分析此空间
                  </button>
                  {bubbleSelection.zone && (
                    <button
                      type="button"
                      onClick={() => onAdvisorPrefill?.(`进入「${bubbleSelection.zone?.label}」的平面推演。`)}
                      className="text-[11px] font-semibold text-sky-600 hover:text-sky-800 text-left"
                    >
                      → 进入此区域的平面推演
                    </button>
                  )}
                </div>
              </div>
            ) : panelSelectionMode === 'layer' ? (
              /* ═══════════ 图层视图 — 只显示当前图层和本层锚点 ═══════════ */
              <div className="space-y-3">
                <div className="border border-slate-200 bg-white px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">当前图层</div>
                      <div className="mt-1.5 text-[15px] font-semibold text-slate-950">{selectedLayer.title}</div>
                      <p className="mt-1 text-[12px] leading-5 text-slate-500">{selectedLayer.advisorLine}</p>
                    </div>
                    <span className="text-[11px] font-semibold text-emerald-500">
                      {selectedLayerCompletion.confirmedCount}/{selectedLayerCompletion.totalCount}
                    </span>
                  </div>
                  <div className="mt-3 h-1.5 overflow-hidden bg-slate-100">
                    <div className="h-full bg-emerald-400" style={{ width: `${Math.round(selectedLayerCompletion.ratio * 100)}%` }} />
                  </div>
                  <div className="mt-3 rounded bg-slate-50 px-3 py-2 text-[11px] leading-5 text-slate-500">
                    <div className="font-semibold text-slate-700">图层对象绑定</div>
                    <div>{selectedLayer.sourceObject}</div>
                  </div>
                </div>

                <div className="border border-slate-200 bg-white px-4 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-xs font-semibold text-slate-900">本层锚点</div>
                    <span className="text-[11px] text-slate-400">{selectedLayerActiveNodes.length} 项</span>
                  </div>
                  <div className="mt-3 space-y-2">
                    {selectedLayerActiveNodes.map(node => {
                      const propositionState = getPropositionState(node.status);
                      return (
                        <button
                          key={`layer-node-${node.id}`}
                          type="button"
                          onClick={() => handleNodeClick(node)}
                          className="w-full border border-slate-200 bg-slate-50 px-3 py-2 text-left transition hover:border-sky-200 hover:bg-sky-50"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div className="flex min-w-0 items-center gap-2">
                              <PropositionStateIcon
                                state={propositionState}
                                className={`h-3.5 w-3.5 shrink-0 ${propositionState === 'confirmed' ? 'text-emerald-500' : 'text-slate-400'}`}
                              />
                              <div className={`min-w-0 truncate text-[12px] font-semibold ${propositionState === 'confirmed' ? 'text-slate-800' : 'text-slate-500'}`}>
                                {node.label}
                              </div>
                            </div>
                            <span className="shrink-0 text-[10px] font-semibold text-slate-400">{getPropositionStateLabel(node.status)}</span>
                          </div>
                          <div className="mt-1 text-[11px] leading-4 text-slate-500 line-clamp-2">
                            {node.category ?? node.sourceObject}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                  {selectedLayerDismissedNodes.length > 0 && (
                    <div className="mt-3 border-t border-slate-200 pt-2">
                      <button
                        type="button"
                        className="flex w-full items-center justify-between gap-2 px-1 py-1 text-left text-[11px] font-semibold text-slate-500 transition hover:text-slate-800"
                        onClick={() => toggleDismissedLayer(selectedLayer.id)}
                        aria-expanded={Boolean(dismissedExpandedLayers[selectedLayer.id])}
                      >
                        <span className="inline-flex items-center gap-1.5">
                          {dismissedExpandedLayers[selectedLayer.id] ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                          已否定命题
                        </span>
                        <span>{selectedLayerDismissedNodes.length}</span>
                      </button>
                      {dismissedExpandedLayers[selectedLayer.id] && (
                        <div className="mt-2 space-y-2">
                          {selectedLayerDismissedNodes.map(node => (
                            <button
                              key={`layer-dismissed-node-${node.id}`}
                              type="button"
                              onClick={() => handleNodeClick(node)}
                              className="w-full border border-slate-200 bg-slate-50 px-3 py-2 text-left opacity-80 transition hover:border-slate-300 hover:bg-white hover:opacity-100"
                            >
                              <div className="flex min-w-0 items-center gap-2">
                                <PropositionStateIcon state="dismissed" className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                                <div className="min-w-0 truncate text-[12px] font-semibold text-slate-500 line-through decoration-slate-300">
                                  {node.label}
                                </div>
                              </div>
                              <div className="mt-1 text-[11px] leading-4 text-slate-400 line-clamp-2">
                                {node.category ?? node.sourceObject}
                              </div>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              /* ═══════════ 锚点视图 — 只显示当前锚点自身信息 ═══════════ */
              <div className="space-y-3">
                {selectedNode && selectedLayer && (
                  selectedNode.id === 'site_geo' ? (
                    <div className="flex flex-col gap-4">
                      <GeoAnchorCard onOpenGeoWorkspace={onOpenGeoWorkspace} />
                      
                      {geoThesis && (
                        <div className="flex flex-col gap-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                          <GeoScorePanel scores={geoThesis.scores} loading={thesisLoading} />
                          <GeoThesisCard thesis={geoThesis} loading={thesisLoading} />
                        </div>
                      )}
                      
                      {!geoThesis && thesisLoading && (
                        <div className="flex flex-col gap-4">
                          <GeoScorePanel scores={null as any} loading={true} />
                          <GeoThesisCard thesis={null as any} loading={true} />
                        </div>
                      )}

                      <div className="rounded bg-white px-3 py-2 text-[11px] leading-5 text-slate-500 border border-slate-200">
                        <div className="font-semibold text-slate-700">真相源绑定</div>
                        <div>{selectedNode.sourceObject}</div>
                      </div>
                    </div>
                  ) : (
                    <div className="border border-slate-200 bg-white px-4 py-3">
                      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                        当前锚点 · {selectedLayer.title}
                      </div>
                      <div className="mt-1.5 text-[15px] font-semibold text-slate-950">{selectedNode.label}</div>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                        {getPropositionState(selectedNode.status) === 'confirmed' ? (
                          <PropositionStateIcon state="confirmed" className="h-3.5 w-3.5 text-emerald-500" />
                        ) : getPropositionState(selectedNode.status) === 'dismissed' ? (
                          <PropositionStateIcon state="dismissed" className="h-3.5 w-3.5 text-slate-400" />
                        ) : (
                          <PropositionStateIcon state="pending" className="h-3.5 w-3.5 text-slate-400" />
                        )}
                        <span>{getPropositionStateLabel(selectedNode.status)}</span>
                        <span>·</span>
                        <span>{STATUS_META[selectedNode.status].label}</span>
                        <span>·</span>
                        <span>{selectedNode.sourceVersion}</span>
                      </div>
                      <p className="mt-3 text-[12px] leading-5 text-slate-600">{selectedNode.description}</p>
                      {getPropositionState(selectedNode.status) === 'dismissed' && (
                        <div className="mt-3 border border-slate-200 bg-slate-50 px-3 py-2">
                          <div className="text-[11px] font-semibold text-slate-700">推敲记录</div>
                          <p className="mt-1 text-[11px] leading-5 text-slate-500">
                            该命题已被用户否定或从当前方案中删除，保留为方案推敲记录。可二次启用后回到待确认状态。
                          </p>
                          <button
                            type="button"
                            className="mt-2 border border-slate-300 bg-white px-2.5 py-1 text-[11px] font-semibold text-slate-700 transition hover:border-slate-500 hover:text-slate-950"
                            onClick={() => reactivateDismissedNode(selectedNode)}
                          >
                            重新启用为待确认
                          </button>
                        </div>
                      )}

                      {selectedNode.details && selectedNode.details.length > 0 && (
                        <div className="mt-3 space-y-2">
                          {selectedNode.details.map(detail => (
                            <div key={`${selectedNode.id}-${detail.heading}`} className="border-t border-slate-100 pt-2">
                              <div className="text-[11px] font-semibold text-slate-700">{detail.heading}</div>
                              <div className="mt-1 text-[11px] leading-5 text-slate-500">{detail.body}</div>
                            </div>
                          ))}
                        </div>
                      )}

                      {selectedNode.references && selectedNode.references.length > 0 && (
                        <div className="mt-3 border-t border-slate-100 pt-2">
                          <div className="text-[11px] font-semibold text-slate-700">资料引用</div>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {selectedNode.references.map(reference => (
                              <span key={`${selectedNode.id}-${reference}`} className="border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] text-slate-500">
                                {reference}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="mt-3 rounded bg-slate-50 px-3 py-2 text-[11px] leading-5 text-slate-500">
                        <div className="font-semibold text-slate-700">真相源绑定</div>
                        <div>{selectedNode.sourceObject}</div>
                      </div>
                    </div>
                  )
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── 平面推演 · 半透明覆盖层悬浮工作台 ───────────────────────────────
          · 仅在用户点击"平面穿透窗"后打开
          · 渲染在最外层（脱离 canvas SVG），使用 fixed positioning 覆盖整个视口
          · 关闭后底盘焦点完全保留（bubbleSelection 状态不变）       */}
      <PlanWorkbenchOverlay
        open={planOverlayOpen}
        context={{
          /* 优先使用 tile 点击时携带的 zone 上下文，回退到当前 bubbleSelection */
          bubbleName: bubbleSelection.bubble?.name,
          zoneLabel:  planOverlayCtx?.zoneLabel ?? bubbleSelection.zone?.label,
          zoneId:     planOverlayCtx?.zoneId    ?? bubbleSelection.zone?.id,
          roomLabel:  bubbleSelection.room?.label,
          bindingState: planOverlayCtx?.bindingState
            ?? (!bubbleSelection.zone
              ? 'unbound'
              : bubbleSelection.zone.maturity < 0.50 ? 'candidate' : 'bound'),
        }}
        onClose={() => setPlanOverlayOpen(false)}
        sessionId={sessionId}
        projectLabel={projectLabel}
        projectOverview={overview}
      />

    </div>
  );
}
