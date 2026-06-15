const TITLE_VISIBLE_CHARS = 14;
const MIN_SUMMARY_CHARS = 8;

type TitleKeywordRule = {
  keywords: string[];
  label: string;
};

const LOCATION_RULES: TitleKeywordRule[] = [
  { keywords: ['深圳蛇口'], label: '深圳蛇口' },
  { keywords: ['蛇口'], label: '蛇口' },
  { keywords: ['苏州黄桥'], label: '苏州黄桥' },
  { keywords: ['黄桥'], label: '黄桥' },
  { keywords: ['茶市街'], label: '茶市街' },
  { keywords: ['华大基因'], label: '华大基因' },
  { keywords: ['七里坪'], label: '七里坪' },
  { keywords: ['峨眉山'], label: '峨眉' },
  { keywords: ['深圳'], label: '深圳' },
  { keywords: ['杭州'], label: '杭州' },
  { keywords: ['苏州'], label: '苏州' },
  { keywords: ['上海'], label: '上海' },
  { keywords: ['北京'], label: '北京' },
  { keywords: ['广州'], label: '广州' },
  { keywords: ['成都'], label: '成都' },
  { keywords: ['南京'], label: '南京' },
  { keywords: ['西安'], label: '西安' },
];

const SPACE_RULES: TitleKeywordRule[] = [
  { keywords: ['菜市场'], label: '菜市场' },
  { keywords: ['茶市场'], label: '茶市场' },
  { keywords: ['茶市街'], label: '市场' },
  { keywords: ['资源雷达'], label: '资源雷达' },
  { keywords: ['空间分类'], label: '空间分类' },
  { keywords: ['平面推演', '平面图'], label: '平面推演' },
  { keywords: ['方案画布', '概念画布'], label: '方案画布' },
  { keywords: ['AI Agent', 'Agent工作流', 'Agent'], label: 'Agent工作流' },
  { keywords: ['工作流', '流程'], label: '工作流程' },
  { keywords: ['架构'], label: '架构' },
  { keywords: ['市场'], label: '市场' },
  { keywords: ['街区'], label: '街区' },
  { keywords: ['入口'], label: '入口' },
  { keywords: ['公区'], label: '公区' },
  { keywords: ['大堂'], label: '大堂' },
  { keywords: ['餐厅'], label: '餐厅' },
  { keywords: ['客房'], label: '客房' },
  { keywords: ['连廊', '走廊'], label: '连廊' },
  { keywords: ['展厅'], label: '展厅' },
  { keywords: ['办公室', '办公'], label: '办公' },
  { keywords: ['商业'], label: '商业' },
  { keywords: ['民宿'], label: '民宿' },
  { keywords: ['酒店'], label: '酒店' },
  { keywords: ['社区'], label: '社区' },
];

const MOTIVE_RULES: TitleKeywordRule[] = [
  { keywords: ['重复', '去重', '重叠'], label: '重复问题处理' },
  { keywords: ['问题处理', '修复', '错误', 'bug', 'Bug'], label: '问题修复' },
  { keywords: ['更新改造', '改造'], label: '更新改造' },
  { keywords: ['优化建议', '优化'], label: '优化建议' },
  { keywords: ['可行性分析', '可行性'], label: '可行性' },
  { keywords: ['分类'], label: '分类' },
  { keywords: ['选址'], label: '选址' },
  { keywords: ['对比', '对照'], label: '对比分析' },
  { keywords: ['分析'], label: '分析建议' },
  { keywords: ['方案', '概念'], label: '方案建议' },
  { keywords: ['推演'], label: '推演' },
  { keywords: ['动线'], label: '动线' },
  { keywords: ['预算', '成本'], label: '预算' },
  { keywords: ['落地'], label: '落地' },
  { keywords: ['表达'], label: '表达' },
  { keywords: ['设计'], label: '设计' },
];

const normalizeTitleSource = (input: string) =>
  input
    .replace(/\s+/g, '')
    .replace(/[，。！？、；：,.!?;:"“”'‘’（）()【】\[\]{}<>《》]/g, '');

const normalizeTitleSegment = (input: string) =>
  input
    .replace(/\s+/g, '')
    .replace(/[。！？!?；;]/g, '，')
    .replace(/[：:]/g, '，')
    .split(/[，,、]/)
    .map((part) => part.trim())
    .filter(Boolean);

const findRuleLabel = (source: string, rules: TitleKeywordRule[]) =>
  rules.find((rule) => rule.keywords.some((keyword) => source.includes(keyword)))?.label ?? '';

const charLength = (value: string) => Array.from(value).length;

const extractAreaLabel = (source: string) => {
  const match = source.match(/(\d{4,})\s*(㎡|平米|平方米)/);
  if (!match) return '';
  const numeric = Number(match[1]);
  if (!Number.isFinite(numeric)) return '';
  if (numeric >= 10000) {
    const compact = numeric % 10000 === 0 ? `${numeric / 10000}` : `${Number((numeric / 10000).toFixed(1))}`;
    return `${compact}万㎡`;
  }
  return `${numeric}㎡`;
};

const limitChars = (value: string, max = TITLE_VISIBLE_CHARS) => {
  const chars = Array.from(value);
  if (chars.length <= max) return value;
  return `${chars.slice(0, max).join('')}…`;
};

export const limitSessionTitle = (title: string) => limitChars(normalizeTitleSource(title), TITLE_VISIBLE_CHARS);

const expandShortSummary = (summary: string, fallbackPhrase: string) => {
  const normalizedFallback = normalizeTitleSource(fallbackPhrase);
  if (charLength(summary) >= MIN_SUMMARY_CHARS) return summary;
  if (charLength(normalizedFallback) >= MIN_SUMMARY_CHARS) return normalizedFallback;

  if (summary === '预算') return '项目预算策略梳理';
  if (summary === '方案建议') return '项目方案建议梳理';
  if (summary === '优化建议') return '项目优化建议梳理';
  if (summary === '分析建议') return '项目分析建议梳理';
  if (summary === '资源雷达') return '资源雷达优化建议';
  if (summary === '空间分类') return '空间分类优化分析';
  if (summary === '平面推演') return '平面推演优化建议';
  if (summary === '方案画布') return '方案画布优化建议';
  if (summary.endsWith('方案建议')) return `${summary.replace(/方案建议$/, '')}项目方案建议梳理`;
  if (summary.endsWith('优化建议')) return `${summary}梳理`;
  if (summary.endsWith('分析建议')) return `${summary}梳理`;
  if (summary) return `${summary}需求摘要`;
  return normalizedFallback || '未命名项目';
};

const isWeakExplicitTitle = (title: string) => {
  const normalized = normalizeTitleSource(title);
  if (!normalized) return true;
  if (charLength(normalized) < MIN_SUMMARY_CHARS) return true;
  return /^(深圳|商业|空间|资源|预算|方案|项目)?(方案建议|优化建议|分析建议|预算|设计|分类)$/.test(normalized);
};

export const deriveSessionTitle = (input: string): string => {
  const source = normalizeTitleSource(input);
  if (!source) return '未命名项目';

  const location = findRuleLabel(source, LOCATION_RULES);
  const area = extractAreaLabel(source);
  const space = findRuleLabel(source, SPACE_RULES);
  const motive = findRuleLabel(source, MOTIVE_RULES);

  const summary = [location, area, space, motive]
    .filter(Boolean)
    .reduce<string[]>((parts, part) => (parts.includes(part) ? parts : [...parts, part]), [])
    .join('');
  const fallbackPhrase = normalizeTitleSegment(input)[0] ?? source;
  if (summary) return limitChars(expandShortSummary(summary, fallbackPhrase), TITLE_VISIBLE_CHARS);

  return limitChars(fallbackPhrase, TITLE_VISIBLE_CHARS);
};

export const resolveSessionTitle = (rawInput: string, displayName?: string | null): string => {
  const explicit = displayName?.trim() ?? '';
  if (explicit && !isWeakExplicitTitle(explicit)) return limitSessionTitle(explicit);
  return deriveSessionTitle(rawInput || explicit);
};
