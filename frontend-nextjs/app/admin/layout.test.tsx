import { render, screen, waitFor } from '@testing-library/react';

import AdminLayout from './layout';

const mockUseAuth = jest.fn();

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

const MOJIBAKE_PATTERN = /鍛|绠|閰|鏃|鐭|浼|锔|馃|鈿|�/;

describe('AdminLayout', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({
      isLoading: false,
      isAuthenticated: true,
      logout: jest.fn(),
    });
  });

  afterEach(() => {
    mockUseAuth.mockReset();
    window.localStorage.clear();
  });

  it('does not expose crawler, log viewer, or system config management in the admin nav', async () => {
    render(
      <AdminLayout>
        <div>admin content</div>
      </AdminLayout>,
    );

    await waitFor(() => expect(screen.getByText('admin content')).toBeInTheDocument());

    expect(screen.queryByText('外部数据管理')).not.toBeInTheDocument();
    expect(screen.queryByText('日志查看')).not.toBeInTheDocument();
    expect(screen.queryByText('配置管理')).not.toBeInTheDocument();
    expect(document.querySelector('a[href="/admin/crawler-monitor"]')).not.toBeInTheDocument();
    expect(document.querySelector('a[href="/admin/external-data"]')).not.toBeInTheDocument();
    expect(document.querySelector('a[href="/admin/logs"]')).not.toBeInTheDocument();
    expect(document.querySelector('a[href="/admin/config"]')).not.toBeInTheDocument();
  });

  it('renders active admin navigation in readable Chinese', async () => {
    render(
      <AdminLayout>
        <div>admin content</div>
      </AdminLayout>,
    );

    await waitFor(() => expect(screen.getByText('admin content')).toBeInTheDocument());

    expect(screen.getByRole('heading', { name: '管理后台' })).toBeInTheDocument();
    expect(screen.getByText('仪表板')).toBeInTheDocument();
    expect(screen.getByText('数据库监控')).toBeInTheDocument();
    expect(screen.getByText('治理复核中心')).toBeInTheDocument();
    expect(screen.getByText('空间分类')).toBeInTheDocument();
    expect(screen.getByText('本体论扩展审核')).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(MOJIBAKE_PATTERN);
  });
});
