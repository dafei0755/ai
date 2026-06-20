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

    fireEvent.click(screen.getByRole('button', { name: '关闭侧边栏' }));
    expect(onSidebarOpenChange).toHaveBeenCalledWith(false);
  });
});
