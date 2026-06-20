import type { AdvisorSceneContext } from './types';

export type AdvisorScenePrimaryNav = 'project' | 'assets' | 'knowledge';
export type AdvisorSceneCockpitModule =
  | 'files'
  | 'assets'
  | 'inspiration'
  | 'board'
  | 'experts'
  | 'insight'
  | 'knowledge'
  | 'geo';
export type AdvisorSceneProjectSection = 'space' | 'sandbox' | 'board';
export type AdvisorSceneInsightView = 'main' | 'space' | 'flow' | 'emotion' | 'time';

export const SCENE_PERSPECTIVE_PRESETS = {
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

export type ExpertPerspectiveOption =
  (typeof SCENE_PERSPECTIVE_PRESETS)[keyof typeof SCENE_PERSPECTIVE_PRESETS][number];

export type AdvisorSceneContextParams = {
  activePrimaryNav: AdvisorScenePrimaryNav;
  activeCockpitModule: AdvisorSceneCockpitModule;
  activeProjectSection: AdvisorSceneProjectSection;
  activeBoardSpace: string;
  activeDssPage: string;
  activeInsightView: AdvisorSceneInsightView;
};

const INSIGHT_VIEW_LABELS: Record<AdvisorSceneInsightView, string> = {
  main: '项目全景关系图',
  space: '空间程序结构图',
  flow: '动线关系图',
  emotion: '情绪体验曲线图',
  time: '时间状态图',
};

export function getScenePerspectiveOptions(params: AdvisorSceneContextParams): readonly ExpertPerspectiveOption[] {
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
}

export function buildAdvisorSceneContext(params: AdvisorSceneContextParams): AdvisorSceneContext {
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

  if (activePrimaryNav === 'project' && activeCockpitModule === 'files') {
    const label = '项目底盘 · 智能决策中枢';
    return {
      key: sceneRef,
      label,
      sceneRef,
      suggestion: [
        '已同步左侧场景：项目底盘。',
        '',
        '当前判断：品牌气质和地点约束已明确；主要缺口是面积分布、房间数量和平面图。补齐后平面推演可正式启动。',
        '',
        '深度思考建议：',
        '1. 先识别主矛盾（HAY 克制感 vs 山地在地性 vs 运营效率），确认哪个是当前设计决策的优先约束。',
        '2. 再建立先决条件清单：补齐面积 / 房型 / 平面图这三个缺口，才能推进空间推演。',
        '3. 最后保存项目方向草案，冻结当前判断，为下一步平面推演提供稳定基线。',
        '',
        '补充面积 / 房间数量 / 平面图，或先保存项目方向草案。',
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

  if (activeCockpitModule === 'geo') {
    const label = '地理工作台 · L1 场所分析';
    return {
      key: sceneRef,
      label,
      sceneRef,
      suggestion: [
        '已同步地理工作台。',
        '',
        '当前左侧为地理坐标工作台，正在加载地块周边数据。',
        '',
        'L1 场所分析建议：',
        '1. 识别地块自然禀赋（地形 / 气候 / 景观面 / 生态边界）',
        '2. 分析在地文化与历史脉络',
        '3. 研究市场机会与竞品格局',
        '4. 评估交通可达性与客源结构',
        '5. 梳理约束性条件（政策 / 地质 / 基础设施）',
        '6. 推导业态选型与经营模型',
        '',
        '点击左侧面板的「注入高参·生成 L1 场所清单」，或直接告诉我项目地点，我将为你生成完整的 L1 场所要素清单。',
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
    const pageLabel =
      activeDssPage === 'profile'
        ? '我的画像'
        : activeDssPage === 'portfolio'
        ? '作品'
        : '沉淀';
    const label = `我的硅基分身 · ${pageLabel}`;
    return {
      key: sceneRef,
      label,
      sceneRef,
      suggestion: [
        `已同步左侧场景：${label}。`,
        '',
        '深度思考建议：',
        '1. 先快速保存原文，不在输入瞬间强迫分类。',
        '2. 再把速记分流为习惯、方法、模板、禁忌或案例复盘。',
        '3. 最后把可复用内容转译为当前项目可执行动作与检查点。',
        '',
        '我可以基于你的硅基分身，给出当前项目的个性化决策清单。',
      ].join('\n'),
    };
  }

  const label = `项目洞察 · ${INSIGHT_VIEW_LABELS[activeInsightView] ?? '全景'}`;
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
}
