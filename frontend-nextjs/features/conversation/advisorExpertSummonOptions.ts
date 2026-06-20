export const ADVISOR_EXPERT_SUMMON_OPTIONS = [
  '召集全部',
  '空间总控',
  '用户研究',
  '商业运营',
  '实施边界',
  '风险总控',
] as const;

export type AdvisorExpertSummonOption = (typeof ADVISOR_EXPERT_SUMMON_OPTIONS)[number];
