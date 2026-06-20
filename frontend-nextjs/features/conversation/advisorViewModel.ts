import {
  MOCK_ADVISOR_VIEW_MODEL,
  MOCK_ADVISOR_VIEW_MODEL_FLOOR_PLAN,
  MOCK_ADVISOR_VIEW_MODEL_RESOURCE_RADAR,
  MOCK_ADVISOR_VIEW_MODEL_SCHEME_CANVAS,
  MOCK_ADVISOR_VIEW_MODEL_SILICON_AVATAR,
  MOCK_ADVISOR_VIEW_MODEL_SILICON_PORTFOLIO,
  MOCK_ADVISOR_VIEW_MODEL_SILICON_PROFILE,
  MOCK_ADVISOR_VIEW_MODEL_SILICON_SEDIMENT,
} from '@/components/project-cockpit/mock/mockData';
import type { AdvisorViewModel } from '@/types/advisor';

import type {
  AdvisorSceneCockpitModule,
  AdvisorScenePrimaryNav,
} from './advisorSceneContext';

export type AdvisorViewModelParams = {
  primaryNav: AdvisorScenePrimaryNav;
  cockpitModule: AdvisorSceneCockpitModule;
  isSandbox: boolean;
  dssPage: string;
};

export function getAdvisorViewModel(params: AdvisorViewModelParams): AdvisorViewModel {
  const { primaryNav, cockpitModule, isSandbox, dssPage } = params;

  if (primaryNav === 'assets') return MOCK_ADVISOR_VIEW_MODEL_RESOURCE_RADAR;

  if (primaryNav === 'knowledge') {
    if (dssPage === 'portfolio') return MOCK_ADVISOR_VIEW_MODEL_SILICON_PORTFOLIO;
    if (dssPage === 'sediment') return MOCK_ADVISOR_VIEW_MODEL_SILICON_SEDIMENT;
    if (dssPage === 'profile') return MOCK_ADVISOR_VIEW_MODEL_SILICON_PROFILE;
    return MOCK_ADVISOR_VIEW_MODEL_SILICON_AVATAR;
  }

  if (cockpitModule === 'board') return MOCK_ADVISOR_VIEW_MODEL_SCHEME_CANVAS;
  if (isSandbox) return MOCK_ADVISOR_VIEW_MODEL_FLOOR_PLAN;
  return MOCK_ADVISOR_VIEW_MODEL;
}
