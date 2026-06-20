import { render, screen } from '@testing-library/react';

import { SessionSidebar } from '@/components/SessionSidebar';

const pushMock = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

describe('SessionSidebar', () => {
  beforeEach(() => {
    pushMock.mockClear();
  });

  it('renders history timestamps without analysis mode suffix labels', () => {
    render(
      <SessionSidebar
        currentSessionId="analysis-session"
        sessions={[
          {
            session_id: 'analysis-session',
            status: 'conversation_active',
            created_at: '2026-06-20T10:38:00.000Z',
            user_input: '50岁男性室内设计师',
            analysis_mode: 'deep_thinking',
            session_type: 'analysis',
          },
          {
            session_id: 'search-session',
            status: 'completed',
            created_at: '2026-06-20T10:35:00.000Z',
            user_input: '崇明岛市民农场访客中心',
            session_type: 'search',
          },
        ]}
      />,
    );

    expect(screen.getByText('50岁男性室内设计师')).toBeInTheDocument();
    expect(screen.queryByText('[深度思考]')).not.toBeInTheDocument();
    expect(screen.queryByText('[深度思考pro]')).not.toBeInTheDocument();
    expect(screen.queryByText('[深度搜索]')).not.toBeInTheDocument();
  });

  it('keeps history titles at the main foreground color while timestamps stay muted', () => {
    const { container } = render(
      <SessionSidebar
        currentSessionId="analysis-session"
        sessions={[
          {
            session_id: 'analysis-session',
            status: 'conversation_active',
            created_at: '2026-06-20T10:38:00.000Z',
            user_input: '50岁男性室内设计师',
            session_type: 'analysis',
          },
        ]}
      />,
    );

    expect(screen.getByText('50岁男性室内设计师')).toHaveClass('text-[var(--foreground)]');
    expect(container.querySelector('.text-xs.text-gray-500')).toBeInTheDocument();
  });
});
