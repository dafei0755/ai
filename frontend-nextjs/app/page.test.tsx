import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import HomePage from './page';
import { api } from '@/lib/api';
import { useWorkflowStore } from '@/store/useWorkflowStore';

const mockRouterPush = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockRouterPush,
    replace: jest.fn(),
    prefetch: jest.fn(),
    back: jest.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { user_id: 9999, username: 'dev_user', roles: ['administrator'] },
    isLoading: false,
  }),
}));

const setSessionsMock = jest.fn();

jest.mock('@/contexts/SessionContext', () => ({
  useSession: () => ({
    sessions: [],
    setSessions: setSessionsMock,
    loadMoreTriggerRef: { current: null },
    handleRenameSession: jest.fn(),
    handlePinSession: jest.fn(),
    handleShareSession: jest.fn(),
    handleDeleteSession: jest.fn(),
    dedupeSessions: (sessions: unknown[]) => sessions,
  }),
}));

jest.mock('@/components/SessionSidebar', () => ({
  SessionSidebar: () => <div data-testid="session-sidebar" />,
}));

jest.mock('@/components/layout/UserPanel', () => ({
  UserPanel: () => <div data-testid="user-panel" />,
}));

jest.mock('@/lib/api', () => ({
  api: {
    sendConversationMessage: jest.fn(),
    updateSession: jest.fn(),
  },
}));

const mockedApi = api as jest.Mocked<typeof api>;

describe('HomePage submit behavior', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRouterPush.mockClear();
    useWorkflowStore.getState().reset();
  });

  it('does not request retired demo app config on the home page', async () => {
    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('输入你的想法、问题或设计需求，先做需求重构...')).toBeInTheDocument();
    });

    expect(global.fetch).not.toHaveBeenCalledWith(expect.stringContaining('/api/app-config'));
  });

  it('shows a clear submitting state after the send button is clicked', async () => {
    const user = userEvent.setup();
    mockedApi.sendConversationMessage.mockImplementation(() => new Promise(() => {}));

    render(<HomePage />);

    await user.type(
      screen.getByPlaceholderText('输入你的想法、问题或设计需求，先做需求重构...'),
      '深圳市南山区来福士广场负一楼30平米奶茶店，半年回本。',
    );
    await user.click(screen.getByRole('button', { name: '发送' }));

    expect(await screen.findByText('正在创建会话...')).toBeInTheDocument();
  });

  it('opens the design taskbook conversation in analysis instead of the project cockpit prototype', async () => {
    const user = userEvent.setup();
    mockedApi.sendConversationMessage.mockResolvedValue({
      session_id: 'session-taskbook-001',
      reply: 'ok',
    } as any);
    mockedApi.updateSession.mockResolvedValue(undefined as any);

    render(<HomePage />);

    await user.type(
      screen.getByRole('textbox'),
      '深圳市南山区来福士广场，负一楼，30平米奶茶店，半年回本。',
    );

    const submitButton = document.querySelector<HTMLButtonElement>('button[type="submit"]');
    expect(submitButton).toBeTruthy();
    await user.click(submitButton!);

    await waitFor(() => {
      expect(mockRouterPush).toHaveBeenCalledWith('/analysis/session-taskbook-001');
    });
    expect(mockRouterPush).not.toHaveBeenCalledWith(expect.stringContaining('/project-cockpit'));
  });
});
