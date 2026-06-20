import {
  ADVISOR_EXPERT_SUMMON_OPTIONS,
  type AdvisorExpertSummonOption,
} from './advisorExpertSummonOptions';

describe('advisorExpertSummonOptions', () => {
  it('keeps the expert summon option order stable', () => {
    expect(ADVISOR_EXPERT_SUMMON_OPTIONS).toEqual([
      '召集全部',
      '空间总控',
      '用户研究',
      '商业运营',
      '实施边界',
      '风险总控',
    ]);
  });

  it('exposes a typed summon option union', () => {
    const target: AdvisorExpertSummonOption = '空间总控';

    expect(ADVISOR_EXPERT_SUMMON_OPTIONS).toContain(target);
  });
});
