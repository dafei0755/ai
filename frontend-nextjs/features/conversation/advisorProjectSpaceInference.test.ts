import {
  PLAN_SANDBOX_SPACE_OPTIONS,
  collectProjectOverviewText,
  inferProjectDefaultSpace,
} from './advisorProjectSpaceInference';

describe('advisorProjectSpaceInference', () => {
  it('keeps the sandbox space option order stable', () => {
    expect(PLAN_SANDBOX_SPACE_OPTIONS).toEqual(['大堂', '餐厅', '客房', '公区', '连廊', '后勤']);
  });

  it('collects project overview text from all inference fields', () => {
    expect(
      collectProjectOverviewText({
        name: '山地民宿',
        oneLiner: '面向家庭房与景观客房',
        confirmedItems: ['入口需要接待前厅'],
        gapItems: ['后勤补给待确认'],
        mainContradiction: {
          sides: ['运营效率', '度假体验'],
          advisorNote: '连廊需要控制雨雾影响',
        },
      }),
    ).toBe('山地民宿 面向家庭房与景观客房 入口需要接待前厅 后勤补给待确认 运营效率 度假体验 连廊需要控制雨雾影响');
  });

  it('infers the best matching project default space from overview text', () => {
    expect(
      inferProjectDefaultSpace({
        name: '城市更新项目',
        oneLiner: '社区入口和游客市场需要形成公共停留界面',
        confirmedItems: ['街区商业外摆'],
        gapItems: [],
        mainContradiction: {
          sides: ['公共开放', '运营秩序'],
          advisorNote: '公区需要承担导流',
        },
      }),
    ).toBe('公区');
  });

  it('returns null when overview has no useful text', () => {
    expect(inferProjectDefaultSpace(null)).toBeNull();
    expect(
      inferProjectDefaultSpace({
        name: '',
        confirmedItems: [],
        gapItems: [],
      }),
    ).toBeNull();
  });
});
