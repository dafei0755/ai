import {
  ADVISOR_WORKSPACE_LAYOUT_STORAGE_KEY,
  ADVISOR_WORKSPACE_PANEL_DEFAULT_RATIO,
  ADVISOR_WORKSPACE_PANEL_MAX_RATIO,
  ADVISOR_WORKSPACE_PANEL_MIN_RATIO,
  clampAdvisorWorkspacePanelRatio,
  type AdvisorWorkspaceLayoutMode,
  type AdvisorWorkspaceResizePanel,
} from './advisorWorkspaceLayoutConfig';

describe('advisorWorkspaceLayoutConfig', () => {
  it('keeps workspace layout storage and panel ratios stable', () => {
    expect(ADVISOR_WORKSPACE_LAYOUT_STORAGE_KEY).toBe('analysis.workspace.layout.v2');
    expect(ADVISOR_WORKSPACE_PANEL_MIN_RATIO).toBe(0.18);
    expect(ADVISOR_WORKSPACE_PANEL_DEFAULT_RATIO).toBe(0.22);
    expect(ADVISOR_WORKSPACE_PANEL_MAX_RATIO).toBe(0.32);
  });

  it('clamps workspace panel ratios to the supported range', () => {
    expect(clampAdvisorWorkspacePanelRatio(0.1)).toBe(ADVISOR_WORKSPACE_PANEL_MIN_RATIO);
    expect(clampAdvisorWorkspacePanelRatio(0.24)).toBe(0.24);
    expect(clampAdvisorWorkspacePanelRatio(0.5)).toBe(ADVISOR_WORKSPACE_PANEL_MAX_RATIO);
  });

  it('exposes typed workspace layout modes and resize panels', () => {
    const mode: AdvisorWorkspaceLayoutMode = 'left-focus';
    const panel: AdvisorWorkspaceResizePanel = 'advisor';

    expect(mode).toBe('left-focus');
    expect(panel).toBe('advisor');
  });
});
