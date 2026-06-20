import { useMemo } from 'react';

import type { AdvisorSceneContext } from '@/features/conversation/types';

interface UseAdvisorContextDerivationOptions {
  advisorSceneContext: AdvisorSceneContext | null;
}

export function useAdvisorContextDerivation({
  advisorSceneContext,
}: UseAdvisorContextDerivationOptions) {
  return useMemo(() => {
    const advisorSuggestionLines = (advisorSceneContext?.suggestion ?? '')
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);

    const advisorInsightLines = advisorSuggestionLines
      .filter((line) => /^\d+[.、]/.test(line))
      .slice(0, 3);

    return { advisorInsightLines };
  }, [advisorSceneContext?.suggestion]);
}
