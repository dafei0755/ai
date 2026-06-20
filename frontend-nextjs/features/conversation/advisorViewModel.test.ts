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

import { getAdvisorViewModel } from './advisorViewModel';

describe('advisorViewModel', () => {
  it('selects the resource radar model for asset scenes', () => {
    expect(
      getAdvisorViewModel({
        primaryNav: 'assets',
        cockpitModule: 'files',
        isSandbox: false,
        dssPage: 'sediment',
      }),
    ).toBe(MOCK_ADVISOR_VIEW_MODEL_RESOURCE_RADAR);
  });

  it('selects the silicon avatar model variants for knowledge scenes', () => {
    expect(
      getAdvisorViewModel({
        primaryNav: 'knowledge',
        cockpitModule: 'files',
        isSandbox: false,
        dssPage: 'portfolio',
      }),
    ).toBe(MOCK_ADVISOR_VIEW_MODEL_SILICON_PORTFOLIO);
    expect(
      getAdvisorViewModel({
        primaryNav: 'knowledge',
        cockpitModule: 'files',
        isSandbox: false,
        dssPage: 'sediment',
      }),
    ).toBe(MOCK_ADVISOR_VIEW_MODEL_SILICON_SEDIMENT);
    expect(
      getAdvisorViewModel({
        primaryNav: 'knowledge',
        cockpitModule: 'files',
        isSandbox: false,
        dssPage: 'profile',
      }),
    ).toBe(MOCK_ADVISOR_VIEW_MODEL_SILICON_PROFILE);
    expect(
      getAdvisorViewModel({
        primaryNav: 'knowledge',
        cockpitModule: 'files',
        isSandbox: false,
        dssPage: 'unknown',
      }),
    ).toBe(MOCK_ADVISOR_VIEW_MODEL_SILICON_AVATAR);
  });

  it('selects project models by board and sandbox state', () => {
    expect(
      getAdvisorViewModel({
        primaryNav: 'project',
        cockpitModule: 'board',
        isSandbox: false,
        dssPage: 'sediment',
      }),
    ).toBe(MOCK_ADVISOR_VIEW_MODEL_SCHEME_CANVAS);
    expect(
      getAdvisorViewModel({
        primaryNav: 'project',
        cockpitModule: 'files',
        isSandbox: true,
        dssPage: 'sediment',
      }),
    ).toBe(MOCK_ADVISOR_VIEW_MODEL_FLOOR_PLAN);
    expect(
      getAdvisorViewModel({
        primaryNav: 'project',
        cockpitModule: 'files',
        isSandbox: false,
        dssPage: 'sediment',
      }),
    ).toBe(MOCK_ADVISOR_VIEW_MODEL);
  });
});
