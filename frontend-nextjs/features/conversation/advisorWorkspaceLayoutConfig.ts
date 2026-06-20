export type AdvisorWorkspaceLayoutMode = 'split' | 'left-focus' | 'right-focus';
export type AdvisorWorkspaceResizePanel = 'middle' | 'advisor';

export const ADVISOR_WORKSPACE_LAYOUT_STORAGE_KEY = 'analysis.workspace.layout.v2';
export const ADVISOR_WORKSPACE_PANEL_MIN_RATIO = 0.18;
export const ADVISOR_WORKSPACE_PANEL_DEFAULT_RATIO = 0.22;
export const ADVISOR_WORKSPACE_PANEL_MAX_RATIO = 0.32;

export const clampAdvisorWorkspacePanelRatio = (value: number) =>
  Math.min(
    ADVISOR_WORKSPACE_PANEL_MAX_RATIO,
    Math.max(ADVISOR_WORKSPACE_PANEL_MIN_RATIO, value),
  );
