import { render, screen, waitFor } from '@testing-library/react';
import axios from 'axios';

import OntologyBrowserPage from './page';

jest.mock('axios');

const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('OntologyBrowserPage', () => {
  beforeEach(() => {
    window.localStorage.setItem('app_auth_token', 'test-token');
    mockedAxios.get.mockImplementation((url) => {
      if (url === '/api/admin/ontology/frameworks') {
        return Promise.resolve({
          data: [
            {
              id: 'commercial_dining',
              name: '餐饮/夜生活空间',
              categories: ['operation'],
              total_dimensions: 3,
            },
          ],
        });
      }
      if (url === '/api/admin/ontology/diagnostics') {
        return Promise.resolve({
          data: {
            schema_version: 'ontology_diagnostics.v1',
            status: 'ok',
            summary: {
              framework_count: 17,
              dimension_count: 9,
              project_type_framework_mapping_count: 32,
              spatial_layer_dimension_mapping_count: 4,
              approved_card_dimension_count: 4,
              blocking_issue_count: 0,
              warning_issue_count: 2,
            },
            frameworks: [
              {
                framework_id: 'commercial_dining',
                project_type_ids: ['commercial_dining'],
                activation_pack_ids: ['tea_drink_store_pack'],
              },
            ],
            dimensions: [
              {
                dimension_id: 'E6_operation_system',
                name_cn: '运营系统与服务流程',
                spatial_layer_ids: ['interior_layer'],
                activation_pack_ids: ['tea_drink_store_pack'],
                approved_card_count: 2,
              },
            ],
            issues: {
              missing_project_type_framework_mappings: [],
              unknown_framework_refs: [],
              unknown_dimension_refs: [],
              unused_frameworks: [],
              dimensions_without_approved_cards: ['E1_spatial_order'],
            },
          },
        });
      }
      return Promise.reject(new Error(`unexpected url: ${url}`));
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('renders ontology diagnostics from the admin endpoint', async () => {
    render(<OntologyBrowserPage />);

    await waitFor(() => {
      expect(screen.getByText('Ontology 健康')).toBeInTheDocument();
    });

    expect(screen.getByText('17')).toBeInTheDocument();
    expect(screen.getByText('E6_operation_system')).toBeInTheDocument();
    expect(screen.getAllByText('commercial_dining').length).toBeGreaterThan(0);
    expect(screen.getByText(/缺少知识卡支撑/)).toBeInTheDocument();
  });
});
