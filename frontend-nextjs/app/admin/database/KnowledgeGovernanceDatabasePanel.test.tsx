import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { KnowledgeGovernanceDatabasePanel } from './KnowledgeGovernanceDatabasePanel';

describe('KnowledgeGovernanceDatabasePanel', () => {
  beforeEach(() => {
    window.localStorage.setItem('app_auth_token', 'test-token');
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          schema_version: 'knowledge_governance_database_health.v1',
          status: 'healthy',
          backend: 'sqlite',
          table_counts: {
            knowledge_asset_drafts: 2,
            approved_knowledge_cards: 1,
            governance_review_items: 1,
            learning_candidates: 0,
            audit_events: 3,
          },
          connection_pool: {
            pool_pre_ping: true,
            pool_size: 10,
            max_overflow: 20,
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          schema_version: 'knowledge_governance_audit_events.v1',
          events: [
            {
              event_id: 1,
              action: 'approve_asset_draft',
              object_type: 'knowledge_asset_draft',
              object_id: 'draft-1',
              created_at: '2026-06-10T10:00:00',
            },
          ],
        }),
      }) as jest.Mock;
  });

  afterEach(() => {
    jest.resetAllMocks();
    window.localStorage.clear();
  });

  it('loads scoped knowledge governance database health and audit events', async () => {
    render(<KnowledgeGovernanceDatabasePanel apiBase="http://127.0.0.1:8001" />);

    await userEvent.type(screen.getByLabelText('知识治理租户 ID'), 'tenant-a');
    await userEvent.type(screen.getByLabelText('知识治理工作区 ID'), 'workspace-a');
    await userEvent.click(screen.getByRole('button', { name: '查看知识治理 DB' }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenNthCalledWith(
        1,
        'http://127.0.0.1:8001/api/admin/knowledge-governance/database-health?tenant_id=tenant-a&workspace_id=workspace-a',
        { headers: { Authorization: 'Bearer test-token' } },
      );
    });
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      'http://127.0.0.1:8001/api/admin/knowledge-governance/audit-events?tenant_id=tenant-a&workspace_id=workspace-a&limit=20',
      { headers: { Authorization: 'Bearer test-token' } },
    );

    expect(await screen.findByText('knowledge_asset_drafts')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('approve_asset_draft')).toBeInTheDocument();
    expect(screen.getByText((text) => text.includes('draft-1'))).toBeInTheDocument();
  });
});
