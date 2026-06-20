import type { BoardCanvasSpace } from '@/components/CockpitPanel';
import type { ProjectOverview } from '@/components/project-cockpit/mock/mockData';

export type ConcreteBoardCanvasSpace = Exclude<BoardCanvasSpace, '全部'>;
export type ProjectSpaceInferenceOverview = Partial<
  Pick<ProjectOverview, 'name' | 'oneLiner' | 'confirmedItems' | 'gapItems' | 'mainContradiction'>
>;

export const PLAN_SANDBOX_SPACE_OPTIONS: ConcreteBoardCanvasSpace[] = [
  '大堂',
  '餐厅',
  '客房',
  '公区',
  '连廊',
  '后勤',
];

export const PROJECT_SPACE_INFERENCE_KEYWORDS: Record<ConcreteBoardCanvasSpace, string[]> = {
  大堂: ['大堂', '前厅', '前台', '接待', '迎宾', '酒店入口', '到达'],
  餐厅: ['餐厅', '餐饮', '厨房', '早餐', '茶饮', '咖啡', '用餐'],
  客房: ['客房', '住宿', '房型', '睡眠', '卫浴', '行李'],
  公区: ['公区', '公共', '入口', '市场', '街区', '商业', '社区', '广场', '更新', '改造', '文旅', '游客', '茶市街'],
  连廊: ['连廊', '走廊', '通道', '动线', '路径', '廊', '导视'],
  后勤: ['后勤', '仓储', '补给', '设备', '清洁', '垃圾', '服务后台'],
};

export const collectProjectOverviewText = (overview: ProjectSpaceInferenceOverview | null): string =>
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

export const inferProjectDefaultSpace = (overview: ProjectSpaceInferenceOverview | null): ConcreteBoardCanvasSpace | null => {
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
