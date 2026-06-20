import type {
  AdvisorSceneInsightView,
  AdvisorScenePrimaryNav,
  AdvisorSceneProjectSection,
} from './advisorSceneContext';

export type AdvisorPrimaryNavItem = {
  key: AdvisorScenePrimaryNav;
  title: string;
};

export type AdvisorProjectSectionItem = {
  key: AdvisorSceneProjectSection;
  title: string;
};

export type AdvisorInsightViewItem = {
  key: AdvisorSceneInsightView;
  label: string;
  desc: string;
};

export const ADVISOR_PRIMARY_NAV_ITEMS: AdvisorPrimaryNavItem[] = [
  { key: 'project', title: '项目底盘' },
  { key: 'knowledge', title: '我的硅基分身' },
];

export const ADVISOR_PROJECT_SECTION_ITEMS: AdvisorProjectSectionItem[] = [
  { key: 'sandbox', title: '平面推演' },
  { key: 'board', title: '方案画布' },
];

export const ADVISOR_INSIGHT_VIEWS: AdvisorInsightViewItem[] = [
  { key: 'main', label: '项目全景关系图', desc: '主图：项目脑图谱（全局关系）。' },
  { key: 'space', label: '空间程序结构图', desc: '副图：空间骨架与模块层级。' },
  { key: 'flow', label: '动线关系图', desc: '副图：主人/访客/服务动线镜像。' },
  { key: 'emotion', label: '情绪体验曲线图', desc: '副图：心理旅程与节奏峰谷。' },
  { key: 'time', label: '时间状态图', desc: '副图：时段与季节切片对比。' },
];
