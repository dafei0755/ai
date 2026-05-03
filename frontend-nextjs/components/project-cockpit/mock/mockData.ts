// Mock data for project-cockpit static prototype
// All data is static — replace with API calls in Sprint 2+

import type { AdvisorViewModel } from '@/types/advisor';

export type ObjectiveState = 'active' | 'preview_only' | 'concept_available' | 'callable';
export type ProjectStage = 'project_definition' | 'space_inference' | 'scheme_expression' | 'version_frozen';
export type ReadinessLevel = 'sufficient' | 'concept_only' | 'not_started';
export type ViewKey = 'overview' | 'spaces' | 'files' | 'history';
export type AdvisorFocus = 'global' | 'space' | 'card';

export interface StageInfo {
  key: ProjectStage;
  label: string;
  status: 'active' | 'pending' | 'available' | 'not_started';
  hint?: string;
}

export interface CapabilityStatus {
  key: 'project_base' | 'floor_plan' | 'scheme_canvas' | 'resource_radar' | 'silicon_avatar';
  label: string;
  statusLabel: string;
  state: ObjectiveState;
  actionLabel?: string;
}

export interface ReadinessItem {
  label: string;
  systemName: string; // shown on hover only
  level: ReadinessLevel;
  progressPct: number;
  statusLabel: string;
  upgradeHint: string;
}

export interface RecommendedAction {
  label: string;
  benefit: string;
  isPrimary: boolean;
}

export interface ProjectOverview {
  name: string;
  oneLiner: string;
  stage: StageInfo;
  confirmedItems: string[];
  gapItems: string[];
  mainContradiction: {
    sides: string[];
    advisorNote: string;
  };
  readiness: ReadinessItem[];
  recommendedActions: RecommendedAction[];
  capabilities: CapabilityStatus[];
}

// ── Empty project (new project, no data yet) ─────────────────────────────────
export const MOCK_EMPTY_PROJECT = {
  id: 'new',
  isEmpty: true,
};

// ── HAY 七里坪 demo project ───────────────────────────────────────────────────
export const MOCK_PROJECT_OVERVIEW: ProjectOverview = {
  name: 'HAY 气质七里坪山地民宿',
  oneLiner: '项目方向初步成立，核心矛盾需要在设计策略中化解，尚缺平面图和预算档位',
  stage: {
    key: 'project_definition',
    label: '项目定义',
    status: 'active',
    hint: '补充面积与平面图后可进入空间推演',
  },
  confirmedItems: [
    '地点：峨眉山七里坪',
    '类型：山地轻度假民宿',
    '品牌参照：HAY 功能主义',
  ],
  gapItems: [
    '大概面积是多少？',
    '客房数量？',
    '是否有平面图或现场照片？',
  ],
  mainContradiction: {
    sides: [
      'HAY 的年轻克制感',
      '峨眉山七里坪的山地自然与高湿环境',
      '轻度假民宿的运营效率与成本边界',
    ],
    advisorNote:
      '这个项目不能被简化成"北欧风民宿"，关键是用 HAY 的功能主义方法组织山地轻度假的真实停留体验。',
  },
  readiness: [
    {
      label: '项目方向草案',
      systemName: 'AlignedBrief / ProjectBasePatch',
      level: 'sufficient',
      progressPct: 80,
      statusLabel: '可以形成项目方向建议',
      upgradeHint: '补充预算档位 → 提升可执行性',
    },
    {
      label: '空间结构框架',
      systemName: 'SPG',
      level: 'concept_only',
      progressPct: 40,
      statusLabel: '还缺平面和面积',
      upgradeHint: '补充面积 / 平面图 → 提升准确度',
    },
    {
      label: '执行任务书',
      systemName: 'ExecutionPlan',
      level: 'not_started',
      progressPct: 0,
      statusLabel: '尚不具备启动条件',
      upgradeHint: '需先完成空间结构框架',
    },
    {
      label: '平面落位包',
      systemName: 'FloorPlanPack',
      level: 'not_started',
      progressPct: 0,
      statusLabel: '尚不具备启动条件',
      upgradeHint: '需上传平面图后启动',
    },
  ],
  recommendedActions: [
    {
      label: '补充 3 个关键信息',
      benefit: '我可以把当前判断从"初步方向"推进到"可形成草案"',
      isPrimary: true,
    },
    {
      label: '保存为项目方向草案',
      benefit: '保存为可编辑草案，不会冻结正式任务书',
      isPrimary: false,
    },
    {
      label: '生成概念画布预览',
      benefit: '先生成色彩、材料、家具气质方向，不做正式空间落位',
      isPrimary: false,
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

export const MOCK_STAGES: StageInfo[] = [
  { key: 'project_definition', label: '项目定义', status: 'active' },
  { key: 'space_inference', label: '空间推演', status: 'pending', hint: '补平面图后更准' },
  { key: 'scheme_expression', label: '方案表达', status: 'available', hint: '概念可用' },
  { key: 'version_frozen', label: '版本冻结', status: 'not_started' },
];

export const MOCK_VIEW_BADGES: Partial<Record<ViewKey, string>> = {
  spaces: '1 待确认',
  files: '12',
};

export const MOCK_ADVISOR_VIEW_MODEL: AdvisorViewModel = {
  traceId: 'trace-mock-001',
  generatedAt: '2026-05-03T10:00:00Z',
  sceneContext: {
    projectId: 'hay-qilipng',
    sessionId: 'local-session',
    module: 'project_base',
    userAction: 'view',
    dispatchLevel: 'L1',
  },
  boundObjectId: 'project-hay-qilipng',
  objectState: 'draft',
  objectVersion: '0.1.0',
  judgment: {
    content:
      '品牌气质和地点约束已明确；主要缺口是面积分布、房间数量和平面图。补齐后平面推演可正式启动。',
    confidence: 'medium',
    evidence: {
      evidenceClass: 'internal_reasoning',
      verificationState: 'unverified',
    },
    sourceParts: {
      ontology: '民宿类型 · 山地',
    },
    cannotDo: [
      {
        reason: '缺少面积和平面图，无法启动空间推演',
        blockedChipTypes: ['navigate'],
      },
    ],
  },
  evidenceStatus: 'internal_hint',
  activatedCapabilities: [
    {
      type: 'ontology',
      name: '本体论',
      status: 'placeholder',
      summary: 'Phase A2 接入后生效',
    },
    {
      type: 'methodology',
      name: '方法论',
      status: 'placeholder',
      summary: 'Phase A2 接入后生效',
    },
    {
      type: 'knowledge',
      name: '知识库',
      status: 'placeholder',
      summary: 'Phase A2 接入后生效',
    },
  ],
  actionChips: [
    {
      type: 'ask',
      label: '补充 3 个关键信息',
      isPrimary: true,
      payload: {
        question:
          '请问项目总建筑面积大概是多少？客房数量和房型组合是什么？是否有平面图或现场照片？',
      },
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
  ],
};

export const MOCK_ADVISOR_VIEW_MODEL_FLOOR_PLAN: AdvisorViewModel = {
  traceId: 'trace-mock-002',
  generatedAt: '2026-05-03T10:01:00Z',
  sceneContext: {
    projectId: 'hay-qilipng',
    sessionId: 'local-session',
    module: 'floor_plan',
    userAction: 'navigate_in',
    dispatchLevel: 'L2',
  },
  boundObjectId: 'floor-plan-hay-draft',
  objectState: 'draft',
  objectVersion: '0.0.1',
  judgment: {
    content:
      '平面推演处于预览模式。当前缺少建筑面积和房型数据，推演结论置信度低。补充面积分布后可生成有效的空间排布方案。',
    confidence: 'low',
    evidence: {
      evidenceClass: 'internal_reasoning',
      verificationState: 'unverified',
    },
    sourceParts: {
      methodology: '山地民宿空间模型 v1',
    },
    cannotDo: [
      {
        reason: '面积数据缺失，无法输出精确空间比例',
        blockedChipTypes: ['freeze'],
      },
    ],
  },
  evidenceStatus: 'none',
  activatedCapabilities: [
    {
      type: 'ontology',
      name: '本体论',
      status: 'placeholder',
      summary: 'Phase A2 接入后生效',
    },
    {
      type: 'methodology',
      name: '方法论',
      status: 'placeholder',
      summary: 'Phase A2 接入后生效',
    },
    {
      type: 'knowledge',
      name: '知识库',
      status: 'placeholder',
      summary: 'Phase A2 接入后生效',
    },
  ],
  actionChips: [
    {
      type: 'ask',
      label: '告诉我建筑面积和房型',
      isPrimary: true,
      payload: {
        question: '请提供总建筑面积（㎡）、客房数量，以及希望的主要房型（大床/双床/亲子等）比例？',
      },
    },
    {
      type: 'navigate',
      label: '返回项目底盘补充',
      isPrimary: false,
      payload: { target: 'project_base' },
    },
  ],
};

export const MOCK_ADVISOR_VIEW_MODEL_SCHEME_CANVAS: AdvisorViewModel = {
  traceId: 'trace-mock-003',
  generatedAt: '2026-05-03T10:02:00Z',
  sceneContext: {
    projectId: 'hay-qilipng',
    sessionId: 'local-session',
    module: 'scheme_canvas',
    userAction: 'navigate_in',
    dispatchLevel: 'L2',
  },
  boundObjectId: 'concept-canvas-hay-draft',
  objectState: 'pending_confirmation',
  objectVersion: '0.1.0',
  judgment: {
    content:
      '概念画布已可启动，品牌气质方向明确。但落位精度依赖平面推演完成，建议先完成空间排布后再推进方案表达。',
    confidence: 'medium',
    evidence: {
      evidenceClass: 'internal_reasoning',
      verificationState: 'unverified',
    },
    sourceParts: {
      ontology: '民宿品牌 · HAY 功能主义',
      methodology: '方案表达流程 v2',
    },
  },
  evidenceStatus: 'internal_hint',
  activatedCapabilities: [
    {
      type: 'ontology',
      name: '本体论',
      status: 'placeholder',
      summary: 'Phase A2 接入后生效',
    },
    {
      type: 'methodology',
      name: '方法论',
      status: 'placeholder',
      summary: 'Phase A2 接入后生效',
    },
    {
      type: 'knowledge',
      name: '知识库',
      status: 'placeholder',
      summary: 'Phase A2 接入后生效',
    },
  ],
  actionChips: [
    {
      type: 'ask',
      label: '生成概念方向草案',
      isPrimary: true,
      payload: {
        question: '基于 HAY 功能主义风格和山地轻度假场景，帮我生成 3 个概念方向草案，各附一句设计主张。',
      },
    },
    {
      type: 'navigate',
      label: '先完成平面推演',
      isPrimary: false,
      payload: { target: 'floor_plan' },
    },
  ],
};

export const MOCK_ADVISOR_VIEW_MODEL_RESOURCE_RADAR: AdvisorViewModel = {
  traceId: 'trace-mock-004',
  generatedAt: '2026-05-03T10:03:00Z',
  sceneContext: {
    projectId: 'hay-qilipng',
    sessionId: 'local-session',
    module: 'resource_radar',
    userAction: 'navigate_in',
    dispatchLevel: 'L2',
  },
  objectState: 'draft',
  judgment: {
    content:
      '资源雷达尚未激活。待项目底盘草案确认后，可自动匹配符合 HAY 功能主义风格的供应商、材料库和施工团队资源。',
    confidence: 'low',
    evidence: {
      evidenceClass: 'none',
      verificationState: 'unverified',
    },
    sourceParts: {},
    cannotDo: [
      {
        reason: '项目草案未确认，无法启动资源匹配',
        blockedChipTypes: ['fill', 'navigate'],
      },
    ],
  },
  evidenceStatus: 'none',
  activatedCapabilities: [
    { type: 'ontology',    name: '本体论', status: 'placeholder', summary: 'Phase A2 接入后生效' },
    { type: 'methodology', name: '方法论', status: 'placeholder', summary: 'Phase A2 接入后生效' },
    { type: 'knowledge',   name: '知识库', status: 'placeholder', summary: 'Phase A2 接入后生效' },
  ],
  actionChips: [
    {
      type: 'ask',
      label: '了解资源雷达能做什么',
      isPrimary: true,
      payload: {
        question: '资源雷达可以帮我找到哪些类型的供应商和材料？匹配逻辑是什么？',
      },
    },
    {
      type: 'navigate',
      label: '先完成项目底盘',
      isPrimary: false,
      payload: { target: 'project_base' },
    },
  ],
};

export const MOCK_ADVISOR_VIEW_MODEL_SILICON_AVATAR: AdvisorViewModel = {
  traceId: 'trace-mock-005',
  generatedAt: '2026-05-03T10:04:00Z',
  sceneContext: {
    projectId: 'hay-qilipng',
    sessionId: 'local-session',
    module: 'silicon_avatar',
    userAction: 'navigate_in',
    dispatchLevel: 'L2',
  },
  objectState: 'draft',
  judgment: {
    content:
      '硅基分身处于初始化状态。完成项目底盘和方案画布后，将基于你的决策记录和设计偏好，生成可代理日常沟通与方案解释的设计师分身。',
    confidence: 'low',
    evidence: {
      evidenceClass: 'none',
      verificationState: 'unverified',
    },
    sourceParts: {},
    cannotDo: [
      {
        reason: '需要足够的决策历史才能生成有效分身',
        blockedChipTypes: ['fill'],
      },
    ],
  },
  evidenceStatus: 'none',
  activatedCapabilities: [
    { type: 'ontology',    name: '本体论', status: 'placeholder', summary: 'Phase A2 接入后生效' },
    { type: 'methodology', name: '方法论', status: 'placeholder', summary: 'Phase A2 接入后生效' },
    { type: 'knowledge',   name: '知识库', status: 'placeholder', summary: 'Phase A2 接入后生效' },
  ],
  actionChips: [
    {
      type: 'ask',
      label: '了解硅基分身的能力边界',
      isPrimary: true,
      payload: {
        question: '硅基分身具体能代替我做哪些事情？它如何学习我的设计风格和决策偏好？',
      },
    },
    {
      type: 'navigate',
      label: '先完成方案画布',
      isPrimary: false,
      payload: { target: 'scheme_canvas' },
    },
  ],
};
