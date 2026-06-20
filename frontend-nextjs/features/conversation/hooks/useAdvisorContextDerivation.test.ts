import { renderHook } from '@testing-library/react';

import { useAdvisorContextDerivation } from './useAdvisorContextDerivation';

describe('useAdvisorContextDerivation', () => {
  it('extracts trimmed numbered advisor insight lines from scene context', () => {
    const { result } = renderHook(() =>
      useAdvisorContextDerivation({
        advisorSceneContext: {
          key: 'return-home-house',
          label: '返乡民居需求洞察',
          sceneRef: 'advisor-context',
          suggestion: [
            '  1. 50岁意味着人生阶段和功成名就后的回望  ',
            '',
            '2、背井离乡意味着故土怀念和衣锦还乡',
            '普通总结句',
            '3. 民居不仅是居住属性，更是身心安放',
            '4. 第四条暂不进入面板',
          ].join('\n'),
        },
      }),
    );

    expect(result.current.advisorInsightLines).toEqual([
      '1. 50岁意味着人生阶段和功成名就后的回望',
      '2、背井离乡意味着故土怀念和衣锦还乡',
      '3. 民居不仅是居住属性，更是身心安放',
    ]);
  });

  it('returns no insight lines when scene context is missing', () => {
    const { result } = renderHook(() =>
      useAdvisorContextDerivation({
        advisorSceneContext: null,
      }),
    );

    expect(result.current.advisorInsightLines).toEqual([]);
  });
});
