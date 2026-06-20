import { fireEvent, render, screen } from '@testing-library/react';
import { AppSessionShell } from '@/components/layout/AppSessionShell';

jest.mock('@/components/layout/UserPanel', () => ({
  UserPanel: () => <div data-testid="user-panel">Mock User Panel</div>,
}));

describe('AppSessionShell', () => {
  it('renders the shared session sidebar beside page content', () => {
    const onSidebarOpenChange = jest.fn();

    const { container } = render(
      <AppSessionShell
        isSidebarOpen={true}
        onSidebarOpenChange={onSidebarOpenChange}
        sessions={[
          {
            session_id: 'session-1',
            status: 'conversation_active',
            created_at: new Date().toISOString(),
            user_input: '测试会话',
            display_name: '测试会话',
          },
        ]}
        currentSessionId="session-1"
      >
        <div data-testid="conversation-main">Conversation content</div>
      </AppSessionShell>
    );

    expect(container.firstElementChild).toHaveClass('ucppt-advisor-shell');
    expect(screen.getByText('方案高参')).toBeInTheDocument();
    expect(screen.getByText('测试会话')).toBeInTheDocument();
    expect(screen.getByTestId('user-panel')).toBeInTheDocument();
    expect(screen.getByTestId('conversation-main')).toBeInTheDocument();
    expect(container.querySelector('aside')).toHaveClass('w-[310px]');
    expect(container.querySelector('aside > div')).toHaveClass('h-0', 'min-w-[310px]', 'pt-4');

    fireEvent.click(screen.getByRole('button', { name: '关闭侧边栏' }));
    expect(onSidebarOpenChange).toHaveBeenCalledWith(false);
  });

  it('keeps the conversation header in the document flow with a top mask', () => {
    render(
      <AppSessionShell
        isSidebarOpen={false}
        onSidebarOpenChange={jest.fn()}
        sessions={[]}
        showExternalLink={true}
      >
        <div data-testid="conversation-main">Conversation content</div>
      </AppSessionShell>
    );

    expect(screen.getByTestId('app-session-topbar')).toHaveClass('flex-shrink-0');
    expect(screen.getByTestId('app-session-topbar')).not.toHaveClass('absolute');
    expect(screen.getByTestId('app-session-top-mask')).toHaveClass('bg-gradient-to-b');
    expect(screen.getByTestId('app-session-content')).toHaveClass('min-h-0', 'flex-1', 'flex', 'flex-col');
    expect(screen.getByText('设计知外 ucppt.com')).toBeInTheDocument();
  });
});
