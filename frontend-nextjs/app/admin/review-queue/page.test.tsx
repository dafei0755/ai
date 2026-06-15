import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';

import GovernanceReviewQueuePage from './page';

jest.mock('axios');

const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('GovernanceReviewQueuePage', () => {
  beforeEach(() => {
    window.localStorage.setItem('app_auth_token', 'test-token');
    mockedAxios.get.mockResolvedValue({
      data: {
        schema_version: 'governance_review_queue.v1',
        summary: {
          total_pending: 1,
          by_module: {
            type_alias: 1,
          },
        },
        items: [
          {
            id: 'type_alias:冷启动复合屋',
            module: 'type_alias',
            object_type: 'alias_candidate',
            object_id: '冷启动复合屋',
            title: '冷启动复合屋 -> 复合空间',
            review_status: 'pending',
            source: 'taxonomy_learning_correction',
            risk: 'P1',
            target_admin_path: '/admin/space-classification',
            metadata: {
              detected_type: 'personal_residential',
              confirmed_type: 'hybrid_residential_commercial',
            },
          },
        ],
      },
    });
  });

  afterEach(() => {
    mockedAxios.get.mockReset();
    mockedAxios.post.mockReset();
    window.localStorage.clear();
  });

  it('renders a visible governance review queue for pending candidates', async () => {
    render(<GovernanceReviewQueuePage />);

    expect(await screen.findByText('治理复核中心')).toBeInTheDocument();

    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledWith(
        'http://127.0.0.1:8001/api/admin/governance/review-queue',
        { headers: { Authorization: 'Bearer test-token' } },
      );
    });

    expect(screen.getByText('待复核事项')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('冷启动复合屋 -> 复合空间')).toBeInTheDocument();
    expect(screen.getByText('type_alias')).toBeInTheDocument();
    expect(screen.getByText((text) => text.includes('taxonomy_learning_correction'))).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '打开治理页' })).toHaveAttribute(
      'href',
      '/admin/space-classification',
    );
  });

  it('approves a knowledge asset draft and reloads the review queue', async () => {
    mockedAxios.get
      .mockResolvedValueOnce({
        data: {
          schema_version: 'governance_review_queue.v1',
          summary: {
            total_pending: 1,
            by_module: {
              knowledge_asset: 1,
            },
          },
          items: [
            {
              id: 'knowledge_asset:draft-api-approve-1',
              module: 'knowledge_asset',
              object_type: 'asset_draft',
              object_id: 'draft-api-approve-1',
              title: 'API approved card',
              review_status: 'pending',
              source: 'knowledge_asset_draft',
              risk: 'P0',
              target_admin_path: '/admin/knowledge-base',
              tenant_id: 'tenant-a',
              workspace_id: 'workspace-a',
              metadata: {
                source_ref: { source_type: 'document' },
              },
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        data: {
          schema_version: 'governance_review_queue.v1',
          summary: {
            total_pending: 0,
            by_module: {},
          },
          items: [],
        },
      });
    mockedAxios.post.mockResolvedValue({
      data: {
        schema_version: 'governance_review_approval.v1',
        module: 'knowledge_asset',
        result: {
          draft_id: 'draft-api-approve-1',
          card_id: 'CARD-API-APPROVED',
          review_status: 'approved',
        },
      },
    });

    render(<GovernanceReviewQueuePage />);

    expect(await screen.findByText('API approved card')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '批准入库' }));

    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        'http://127.0.0.1:8001/api/admin/governance/review-queue/knowledge_asset/draft-api-approve-1/approve',
        {
          tenant_id: 'tenant-a',
          workspace_id: 'workspace-a',
          reviewer_id: 'admin',
        },
        { headers: { Authorization: 'Bearer test-token' } },
      );
    });
    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledTimes(2);
    });
  });

  it('loads DB-backed review items for a selected tenant and workspace scope', async () => {
    mockedAxios.get
      .mockResolvedValueOnce({
        data: {
          schema_version: 'governance_review_queue.v1',
          summary: {
            total_pending: 0,
            by_module: {},
          },
          items: [],
        },
      })
      .mockResolvedValueOnce({
        data: {
          schema_version: 'governance_review_queue.v1',
          summary: {
            total_pending: 1,
            by_module: {
              knowledge_asset: 1,
            },
          },
          items: [],
        },
      });

    render(<GovernanceReviewQueuePage />);

    await screen.findByText('治理复核中心');
    await userEvent.type(screen.getByLabelText('租户 ID'), 'tenant-a');
    await userEvent.type(screen.getByLabelText('工作区 ID'), 'workspace-a');
    await userEvent.click(screen.getByRole('button', { name: '刷新' }));

    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenLastCalledWith(
        'http://127.0.0.1:8001/api/admin/governance/review-queue?tenant_id=tenant-a&workspace_id=workspace-a',
        { headers: { Authorization: 'Bearer test-token' } },
      );
    });
  });
});
