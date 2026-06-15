import { render, screen, waitFor } from '@testing-library/react';

import KnowledgeAssetsPage from './page';

const mockFetch = jest.fn();

function jsonResponse(data: unknown) {
  return Promise.resolve({
    ok: true,
    json: () => Promise.resolve(data),
  });
}

describe('KnowledgeAssetsPage', () => {
  beforeEach(() => {
    window.localStorage.setItem('app_auth_token', 'test-token');
    mockFetch.mockImplementation((input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes('/api/admin/knowledge-assets/stats')) {
        return jsonResponse({
          candidates: 0,
          needs_review: 0,
          approved: 0,
          rejected: 0,
          needs_revision: 0,
          consumption_events: 0,
          settlement_events: 0,
        });
      }
      if (url.includes('/api/admin/knowledge-assets/candidates')) {
        return jsonResponse({ items: [] });
      }
      if (url.includes('/api/admin/knowledge-assets/approved')) {
        return jsonResponse({ items: [] });
      }
      if (url.includes('/api/admin/knowledge-assets/consumption-events')) {
        return jsonResponse({ items: [] });
      }
      if (url.includes('/api/admin/knowledge-assets/settlement-events')) {
        return jsonResponse({ items: [] });
      }
      if (url.includes('/api/admin/knowledge-assets/golden-review/status')) {
        return jsonResponse({
          status: 'success',
          review_status: 'needs_human_review',
          next_action: 'fill_required_gold_fields',
          completion: {
            total_rows: 29,
            complete_rows: 0,
            incomplete_rows: 29,
          },
          quality_gate: {
            gate_status: 'fail',
            required_items: 28,
          },
          terminal_copy_guardrail: {
            guardrail_scope: 'terminal_user_visible_copy',
            violation_policy: 'fail_review',
            summary: {
              forbidden_term_count: 10,
              violation_count: 0,
            },
            violations: [],
          },
          suggestions: {
            summary: {
              total: 29,
              ready_for_fast_review: 3,
              needs_human_decision: 26,
            },
            items: [
              {
                id: 2,
                review_priority: 'P1',
                remediation_family: '住宅身份/家庭关系/情绪修复',
                suggestion_decision: 'ready_for_fast_review',
                suggested_gold_expected_project_type: 'personal_residential',
                suggested_gold_expected_spatial_extent: '住宅/单项目级',
                suggested_gold_expected_project_stage: '概念方案',
                suggested_gold_expected_core_tension: '成就表达、家族传承与日常安住的平衡',
                suggested_gold_expected_output_depth: '通用方法论级：可给空间逻辑，需声明非专科覆盖',
                prompt_excerpt: '项目位于深圳湾一线海景别墅区，业主为第一代创业者。',
              },
            ],
          },
          systemic_remediation: {
            summary: {
              systemic_actions: 8,
              must_not_hardcode_cases: true,
            },
            principles: ['不把单个案例写成固定规则；只沉淀跨样本成立的机制。'],
            items: [
              {
                id: 'R01',
                priority: 'P0',
                module: 'SpaceClassificationService',
                governance_mode: 'algorithmic_rule',
                risk: '空间主轴识别偏移会把用户问题导向错误专题。',
                mechanism: '建立空间主轴判定算法。',
                verification_gate: '用 190 条 golden baseline 回归。',
                evidence_count: 73,
              },
              {
                id: 'R04',
                priority: 'P0',
                module: 'FrontendHumanLanguageMapping',
                governance_mode: 'ui_mapping',
                risk: '英文内部字段和工程术语暴露给终端用户，降低可信度和理解效率。',
                mechanism: '建立内部枚举到人话标签的映射层。',
                verification_gate: '前端截图和 DOM 文本检查不得出现内部英文字段。',
                evidence_count: 190,
                ui_guardrail: {
                  scope: 'terminal_user_visible_copy',
                  violation_policy: 'fail_review',
                  forbidden_terms: ['heritage value', 'preservation grade', 'core_tension'],
                  required_action: '用中文业务标签替换内部字段名。',
                },
              },
            ],
          },
        });
      }
      throw new Error(`Unexpected fetch url: ${url}`);
    });
    global.fetch = mockFetch as unknown as typeof fetch;
  });

  afterEach(() => {
    mockFetch.mockReset();
    window.localStorage.clear();
  });

  it('renders the read-only Scheme Advisor golden review status', async () => {
    render(<KnowledgeAssetsPage />);

    expect(await screen.findByText('知识资产审核系统')).toBeInTheDocument();

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/admin/knowledge-assets/golden-review/status',
        { headers: { Authorization: 'Bearer test-token' } },
      );
    });

    expect(screen.getByText('方案高参 Golden 复核')).toBeInTheDocument();
    expect(screen.getByText('需人工复核')).toBeInTheDocument();
    expect(screen.getByText('29')).toBeInTheDocument();
    expect(screen.getByText('3 条可快速复核')).toBeInTheDocument();
    expect(screen.getByText('26 条需人工裁决')).toBeInTheDocument();
    expect(screen.getByText('终端文案扫描')).toBeInTheDocument();
    expect(screen.getByText('通过')).toBeInTheDocument();
    expect(screen.getByText('成就表达、家族传承与日常安住的平衡')).toBeInTheDocument();
    expect(screen.getByText('系统性整改清单')).toBeInTheDocument();
    expect(screen.getByText('禁止个案硬编码')).toBeInTheDocument();
    expect(screen.getByText('空间主轴识别偏移会把用户问题导向错误专题。')).toBeInTheDocument();
    expect(screen.getByText('禁用术语检查')).toBeInTheDocument();
    expect(screen.getByText('heritage value、preservation grade、core_tension')).toBeInTheDocument();
    expect(screen.queryByText('批准 Golden')).not.toBeInTheDocument();
  });
});
