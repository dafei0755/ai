import { render, screen, waitFor } from '@testing-library/react';
import { MembershipCard } from '@/components/layout/MembershipCard';
import { useAuth } from '@/contexts/AuthContext';

// Mock AuthContext
jest.mock('@/contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('MembershipCard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorageMock.clear();
    global.fetch = jest.fn();
  });

  it('should not render when user is not logged in', () => {
    (useAuth as jest.Mock).mockReturnValue({ user: null });

    const { container } = render(<MembershipCard />);
    expect(container.firstChild).toBeNull();
  });

  it('should show loading state initially', () => {
    (useAuth as jest.Mock).mockReturnValue({
      user: { user_id: 1, username: 'test_user' },
    });
    localStorageMock.setItem('wp_jwt_token', 'test-token');

    (global.fetch as jest.Mock).mockImplementation(() =>
      new Promise(() => {}) // Never resolves to keep loading state
    );

    render(<MembershipCard />);

    const loadingElement = screen.getByRole('generic', {
      hidden: true,
    });
    expect(loadingElement).toHaveClass('animate-pulse');
  });

  it('should display membership info for VIP user', async () => {
    (useAuth as jest.Mock).mockReturnValue({
      user: { user_id: 1, username: 'test_user' },
    });
    localStorageMock.setItem('wp_jwt_token', 'test-token');

    const mockMembership = {
      level: 2,
      level_name: 'VIP 2',
      expire_date: '2025-12-31',
      is_expired: false,
      wallet_balance: 100,
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockMembership,
    });

    render(<MembershipCard />);

    await waitFor(() => {
      expect(screen.getByText('VIP 2')).toBeInTheDocument();
      expect(screen.getByText('有效')).toBeInTheDocument();
    });
  });

  it('should show expired badge for expired membership', async () => {
    (useAuth as jest.Mock).mockReturnValue({
      user: { user_id: 1, username: 'test_user' },
    });
    localStorageMock.setItem('wp_jwt_token', 'test-token');

    const mockMembership = {
      level: 1,
      level_name: 'VIP 1',
      expire_date: '2023-01-01',
      is_expired: true,
      wallet_balance: 0,
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockMembership,
    });

    render(<MembershipCard />);

    await waitFor(() => {
      expect(screen.getByText('已过期')).toBeInTheDocument();
    });
  });

  it('should show upgrade button for non-premium users', async () => {
    (useAuth as jest.Mock).mockReturnValue({
      user: { user_id: 1, username: 'test_user' },
    });
    localStorageMock.setItem('wp_jwt_token', 'test-token');

    const mockMembership = {
      level: 1,
      level_name: 'VIP 1',
      expire_date: '2025-12-31',
      is_expired: false,
      wallet_balance: 50,
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockMembership,
    });

    render(<MembershipCard />);

    await waitFor(() => {
      expect(screen.getByText('升级会员')).toBeInTheDocument();
    });
  });

  it('should not show upgrade button for premium users (level >= 2)', async () => {
    (useAuth as jest.Mock).mockReturnValue({
      user: { user_id: 1, username: 'test_user' },
    });
    localStorageMock.setItem('wp_jwt_token', 'test-token');

    const mockMembership = {
      level: 2,
      level_name: 'VIP 2',
      expire_date: '2025-12-31',
      is_expired: false,
      wallet_balance: 100,
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockMembership,
    });

    render(<MembershipCard />);

    await waitFor(() => {
      expect(screen.queryByText('升级会员')).not.toBeInTheDocument();
    });
  });

  it('should display error message when API fails', async () => {
    (useAuth as jest.Mock).mockReturnValue({
      user: { user_id: 1, username: 'test_user' },
    });
    localStorageMock.setItem('wp_jwt_token', 'test-token');

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    render(<MembershipCard />);

    await waitFor(() => {
      expect(screen.getByText('获取会员信息失败')).toBeInTheDocument();
    });
  });

  it('should apply correct color for different membership levels', async () => {
    const levels = [
      { level: 0, expectedColor: 'text-gray-400' },
      { level: 1, expectedColor: 'text-blue-400' },
      { level: 2, expectedColor: 'text-purple-400' },
      { level: 3, expectedColor: 'text-amber-400' },
    ];

    for (const { level, expectedColor } of levels) {
      (useAuth as jest.Mock).mockReturnValue({
        user: { user_id: 1, username: 'test_user' },
      });
      localStorageMock.setItem('wp_jwt_token', 'test-token');

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          level,
          level_name: `VIP ${level}`,
          expire_date: '2025-12-31',
          is_expired: false,
          wallet_balance: 0,
        }),
      });

      const { container, unmount } = render(<MembershipCard />);

      await waitFor(() => {
        const crownIcon = container.querySelector('.lucide-crown');
        expect(crownIcon).toHaveClass(expectedColor);
      });

      unmount();
      jest.clearAllMocks();
    }
  });
});
