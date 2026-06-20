import {
  buildAdvisorSceneContext,
  getScenePerspectiveOptions,
} from './advisorSceneContext';

describe('advisorSceneContext', () => {
  it('returns implementation-focused perspectives for logistics sandbox scenes', () => {
    const options = getScenePerspectiveOptions({
      activePrimaryNav: 'project',
      activeCockpitModule: 'files',
      activeProjectSection: 'sandbox',
      activeBoardSpace: '后勤',
      activeDssPage: 'sediment',
      activeInsightView: 'main',
    });

    expect(options).toEqual(['实施边界视角', '动线效率视角', '风险总控视角', '平衡推进视角']);
  });

  it('returns room-focused perspectives for guest-room board scenes', () => {
    const options = getScenePerspectiveOptions({
      activePrimaryNav: 'project',
      activeCockpitModule: 'board',
      activeProjectSection: 'board',
      activeBoardSpace: '客房',
      activeDssPage: 'sediment',
      activeInsightView: 'main',
    });

    expect(options).toEqual(['叙事表达视角', '灯光情绪视角', '运营弹性视角', '落地可建视角', '平衡推进视角']);
  });

  it('builds a stable advisor scene context for insight views', () => {
    const context = buildAdvisorSceneContext({
      activePrimaryNav: 'project',
      activeCockpitModule: 'insight',
      activeProjectSection: 'space',
      activeBoardSpace: '全部',
      activeDssPage: 'sediment',
      activeInsightView: 'flow',
    });

    expect(context.key).toBe('场景/project/insight/space/全局/sediment/flow');
    expect(context.label).toBe('项目洞察 · 动线关系图');
    expect(context.sceneRef).toBe(context.key);
    expect(context.suggestion).toContain('已同步左侧场景：项目洞察 · 动线关系图。');
    expect(context.suggestion).toContain('先识别关键矛盾');
  });
});
