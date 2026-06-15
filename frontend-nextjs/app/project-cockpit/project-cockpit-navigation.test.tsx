import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import ProjectCockpitPage from './[projectId]/page';

const mockRouterPush = jest.fn();

jest.mock('next/navigation', () => ({
  useParams: () => ({ projectId: 'demo' }),
  useRouter: () => ({
    push: mockRouterPush,
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
  }),
}));

jest.mock('@/components/project-cockpit/AdvisorPanel', () => ({
  AdvisorPanel: ({ viewModel }: { viewModel: { traceId: string } }) => (
    <aside data-testid="advisor-panel" data-trace-id={viewModel.traceId} />
  ),
}));

jest.mock('@/components/project-cockpit/ProjectGrowthCanvasView', () => ({
  ProjectGrowthCanvasView: () => <main data-testid="project-growth-canvas" />,
}));

describe('ProjectCockpitPage capsule navigation', () => {
  beforeEach(() => {
    mockRouterPush.mockClear();
  });

  it('routes left capsule navigation to the existing analysis workbench modules', async () => {
    const user = userEvent.setup();
    render(<ProjectCockpitPage />);

    await user.click(screen.getByTitle(/平面推演/));

    expect(mockRouterPush).toHaveBeenLastCalledWith('/analysis/demo?module=floor_plan');

    await user.click(screen.getByTitle(/方案画布/));

    expect(mockRouterPush).toHaveBeenLastCalledWith('/analysis/demo?module=scheme_canvas');

    await user.click(screen.getByTitle('地理工作台'));

    expect(mockRouterPush).toHaveBeenLastCalledWith('/analysis/demo?module=geo');

    await user.click(screen.getByTitle('我的硅基分身'));

    expect(mockRouterPush).toHaveBeenLastCalledWith('/analysis/demo?module=silicon_avatar');
  });
});
