import { fireEvent, render, screen, within } from '@testing-library/react';
import { SessionSidebar } from '@/components/SessionSidebar';

const pushMock = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

describe('SessionSidebar navigation', () => {
  beforeEach(() => {
    pushMock.mockClear();
    jest.spyOn(window, 'open').mockImplementation(() => null);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('uses in-place navigation for analysis sessions when requested', () => {
    render(
      <SessionSidebar
        navigationMode="in-place"
        sessions={[
          {
            session_id: 'session-2',
            status: 'completed',
            created_at: new Date().toISOString(),
            user_input: '历史方案',
            display_name: '历史方案',
          },
        ]}
      />
    );

    fireEvent.click(screen.getByTitle('历史方案'));

    expect(pushMock).toHaveBeenCalledWith('/analysis/session-2');
    expect(window.open).not.toHaveBeenCalled();
  });

  it('keeps the default completed-session navigation in a new report tab', () => {
    render(
      <SessionSidebar
        sessions={[
          {
            session_id: 'session-3',
            status: 'completed',
            created_at: new Date().toISOString(),
            user_input: '默认历史方案',
            display_name: '默认历史方案',
          },
        ]}
      />
    );

    fireEvent.click(screen.getByTitle('默认历史方案'));

    expect(window.open).toHaveBeenCalledWith('/report/session-3', '_blank');
    expect(pushMock).not.toHaveBeenCalled();
  });

  it('does not render analysis-mode suffixes after timestamps', () => {
    render(
      <SessionSidebar
        sessions={[
          {
            session_id: 'session-no-suffix',
            status: 'completed',
            created_at: new Date().toISOString(),
            user_input: '不需要后缀的历史记录',
            display_name: '不需要后缀的历史记录',
            analysis_mode: 'deep_thinking',
          },
        ]}
      />
    );

    expect(screen.queryByText(/\[深度思考/)).not.toBeInTheDocument();
  });

  it('renders history titles with primary text color while keeping timestamps muted', () => {
    render(
      <SessionSidebar
        sessions={[
          {
            session_id: 'session-color',
            status: 'completed',
            created_at: new Date().toISOString(),
            user_input: '深圳市南山区来福士广场，负一楼，30平米商铺',
            display_name: '深圳市南山区来福士广场',
          },
        ]}
      />
    );

    expect(screen.getByTitle('深圳市南山区来福士广场')).toHaveClass('text-[var(--foreground)]');
    expect(screen.getByText(/\d+\/\d+/)).toHaveClass('text-[var(--foreground-secondary)]');
  });

  it('lets the title row use the available sidebar width', () => {
    render(
      <SessionSidebar
        sessions={[
          {
            session_id: 'session-wide-title',
            status: 'completed',
            created_at: new Date().toISOString(),
            user_input: '深圳市南山区来福士广场负一楼30平米奶茶店，半年回本。',
            display_name: '深圳市南山区来福士广场',
          },
        ]}
      />
    );

    expect(screen.getByText('深圳市南山区来福士广场负一楼30平米奶茶店，半年回本。')).toHaveClass('truncate');
    expect(screen.getByText('深圳市南山区来福士广场负一楼30平米奶茶店，半年回本。')).not.toHaveClass('pr-6');
  });

  it('renders quick actions above history groups and opens history search locally', () => {
    render(
      <SessionSidebar
        navigationMode="in-place"
        sessions={[
          {
            session_id: 'session-4',
            status: 'completed',
            created_at: new Date().toISOString(),
            user_input: '今天的历史',
            display_name: '今天的历史',
          },
          {
            session_id: 'session-5',
            status: 'completed',
            created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
            user_input: '老家建房讨论',
            display_name: '老家建房讨论',
          },
        ]}
      />
    );

    const newChat = screen.getByRole('button', { name: '新对话' });
    const searchChat = screen.getByRole('button', { name: '搜索对话' });
    const today = screen.getByText('今天');

    expect(newChat.compareDocumentPosition(today) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(searchChat.compareDocumentPosition(today) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    fireEvent.click(newChat);
    expect(pushMock).toHaveBeenCalledWith('/');

    fireEvent.click(searchChat);
    expect(pushMock).not.toHaveBeenCalledWith('/search');

    const dialog = screen.getByRole('dialog', { name: '搜索对话' });
    expect(dialog).toBeInTheDocument();
    const searchDialog = within(dialog);

    fireEvent.change(screen.getByPlaceholderText('搜索对话...'), {
      target: { value: '老家' },
    });

    expect(searchDialog.getByRole('button', { name: /老家建房讨论/ })).toBeInTheDocument();
    expect(searchDialog.queryByRole('button', { name: /今天的历史/ })).not.toBeInTheDocument();

    fireEvent.click(searchDialog.getByRole('button', { name: /老家建房讨论/ }));
    expect(pushMock).toHaveBeenCalledWith('/analysis/session-5');
  });
});
