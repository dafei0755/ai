import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import axios from 'axios';

import SpaceClassificationAdminPage from './page';

jest.mock('axios');

const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('SpaceClassificationAdminPage', () => {
  beforeEach(() => {
    window.localStorage.setItem('app_auth_token', 'test-token');
    mockedAxios.get.mockImplementation((url) => {
      if (url === 'http://127.0.0.1:8001/api/admin/space-classification/registry-health') {
        return Promise.resolve({
          data: {
            schema_version: 'space_classification_registry_health.v1',
            status: 'ok',
            summary: {
              project_type_count: 32,
              ontology_dimension_count: 9,
              blocking_issue_count: 0,
              warning_issue_count: 1,
            },
            issues: {
              missing_project_type_framework_mappings: [],
              missing_type_operating_profiles: ['commercial_enterprise'],
              missing_activation_pack_files: [],
            },
          },
        });
      }
      if (url === 'http://127.0.0.1:8001/api/admin/space-classification/types') {
        return Promise.resolve({
          data: {
            schema_version: 'space_classification_types.v1',
            items: [
              {
                type_id: 'commercial_dining',
                display_name: '商业餐饮',
                name_en: '',
                description: '',
                status: 'active_mvp',
                review_status: 'approved',
                owner: 'core_team',
                parent_type: 'hospitality',
                ontology_framework_id: 'commercial_dining',
                priority: 8,
                keyword_count: 10,
                has_type_operating_profile: true,
                profile_id: 'commercial_dining_profile',
                type_operating_profile: {
                  profile_id: 'commercial_dining_profile',
                  ontology_framework: 'commercial_dining',
                  master_index_ontology_framework: 'commercial_dining',
                  framework_matches_master_index: true,
                  required_dimensions: [
                    'dining_concept_and_positioning',
                    'customer_flow_and_seating_capacity',
                  ],
                  knowledge_package_ids: ['kp.commercial_dining', 'kp.customer_flow'],
                  missing_knowledge_package_ids: [],
                  type_method_profile_id: 'method.type.commercial_dining.v1',
                  general_method_profile_id: 'method.general.dining_check.v1',
                  downstream_profiles: {
                    questionnaire_profile: 'commercial',
                    floorplan_profile: 'commercial_floorplan_reasoning',
                    visual_prompt_profile: 'commercial_visual_profile',
                    deliverable_profile: 'commercial_deliverable_profile',
                  },
                  issue_codes: [],
                },
                has_admin_override: false,
                editable_fields: [],
              },
              {
                type_id: 'hybrid_residential_commercial',
                display_name: '住商混合 / 复合业态空间',
                name_en: '',
                description: '',
                status: 'active_mvp',
                review_status: 'approved',
                owner: 'core_team',
                parent_type: 'residential',
                ontology_framework_id: 'hybrid_residential_commercial',
                priority: 8,
                keyword_count: 12,
                has_type_operating_profile: true,
                profile_id: 'hybrid_residential_commercial_profile',
                type_operating_profile: {
                  profile_id: 'hybrid_residential_commercial_profile',
                  ontology_framework: 'hybrid_residential_commercial',
                  master_index_ontology_framework: 'hybrid_residential_commercial',
                  framework_matches_master_index: true,
                  required_dimensions: ['program_role_hierarchy'],
                  knowledge_package_ids: ['kp.residential'],
                  missing_knowledge_package_ids: [],
                  type_method_profile_id: 'method.type.hybrid_residential_commercial.v1',
                  general_method_profile_id: 'method.general.hybrid_mixed_use_check.v1',
                  downstream_profiles: {
                    questionnaire_profile: 'hybrid_mixed_use',
                    floorplan_profile: 'hybrid_vertical_stack_reasoning',
                    visual_prompt_profile: 'hybrid_mixed_use_visual_profile',
                    deliverable_profile: 'hybrid_mixed_use_deliverable_profile',
                  },
                  issue_codes: [],
                },
                has_admin_override: false,
                editable_fields: [],
              },
            ],
            total: 1,
            override_count: 0,
          },
        });
      }
      if (url === 'http://127.0.0.1:8001/api/admin/space-classification/subdomains') {
        return Promise.resolve({
          data: {
            schema_version: 'space_classification_subdomains.v1',
            items: [
              {
                subdomain_id: 'tea_drink_store',
                name_cn: '茶饮店',
                name_en: 'tea drink store new tea',
                parent_project_type_id: 'commercial_dining',
                parent_project_type_name: '商业餐饮',
                ontology_framework_id: 'commercial_dining',
                activation_pack_id: 'tea_drink_store_pack',
                activation_pack_loaded: true,
                routing_binding_matched: true,
                has_runtime_detector_binding: true,
                has_yaml_registry_binding: true,
                has_master_index_pack_mapping: true,
                status: 'active_mvp',
                review_status: 'approved',
                owner: 'core_team',
                signal_keywords: ['茶饮店', '茶饮', '奶茶'],
                specialty_tag_assist: ['tea_bar'],
                knowledge_package_ids: ['kp.tea_drink_store'],
              },
              {
                subdomain_id: 'coffee_shop',
                name_cn: '咖啡馆',
                name_en: 'coffee shop specialty cafe',
                parent_project_type_id: 'commercial_dining',
                parent_project_type_name: '商业餐饮',
                ontology_framework_id: 'commercial_dining',
                activation_pack_id: 'coffee_shop_pack',
                activation_pack_loaded: true,
                routing_binding_matched: true,
                has_runtime_detector_binding: true,
                has_yaml_registry_binding: true,
                has_master_index_pack_mapping: true,
                status: 'reserved_light',
                review_status: 'approved',
                owner: 'core_team',
                signal_keywords: ['咖啡馆', '精品咖啡'],
                specialty_tag_assist: ['cafe'],
                knowledge_package_ids: [],
              },
            ],
            total: 2,
          },
        });
      }
      if (url === 'http://127.0.0.1:8001/api/admin/space-classification/subdomain-health') {
        return Promise.resolve({
          data: {
            schema_version: 'space_classification_subdomain_health.v1',
            status: 'ok',
            summary: {
              subdomain_count: 2,
              activation_pack_loaded_count: 2,
              blocking_issue_count: 0,
              warning_issue_count: 0,
            },
            issues: {
              subdomain_yaml_detector_drift: [],
              activation_pack_routing_mismatch: [],
            },
          },
        });
      }
      if (url === 'http://127.0.0.1:8001/api/admin/project-types/candidates?status=pending&limit=100') {
        return Promise.resolve({
          data: {
            items: [
              {
                id: 7,
                type_id_suggestion: 'pet_friendly_retail',
                name_zh: '宠物友好零售',
                name_en: 'pet friendly retail',
                description: '面向宠物和主人共同活动的零售空间。',
                source: 'manual',
                source_session_id: null,
                sample_inputs: ['想做一个允许宠物进入的集合店'],
                occurrence_count: 3,
                suggested_keywords: ['宠物友好', '宠物零售'],
                suggested_secondary_keywords: ['集合店'],
                confidence_score: 0.82,
                review_status: 'pending',
                created_at: '2026-06-08T10:00:00Z',
              },
            ],
            statistics: {
              pending: { count: 1, avg_confidence: 0.82 },
              approved: { count: 2 },
              rejected: { count: 1 },
            },
          },
        });
      }
      return Promise.reject(new Error(`unexpected url: ${url}`));
    });
    mockedAxios.post.mockResolvedValue({ data: {} });
    mockedAxios.patch.mockResolvedValue({
      data: {
        type_id: 'commercial_dining',
        display_name: '餐饮空间',
        name_en: '',
        description: '面向餐饮、茶饮和复合消费场景。',
        status: 'active_mvp',
        review_status: 'approved',
        owner: 'core_team',
        parent_type: 'hospitality',
        ontology_framework_id: 'commercial_dining',
        priority: 8,
        keyword_count: 10,
        has_admin_override: true,
        editable_fields: [],
      },
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
    window.localStorage.clear();
  });

  it('renders diagnostic input and registry health summary', async () => {
    render(<SpaceClassificationAdminPage />);

    expect(screen.getByText('空间分类')).toBeInTheDocument();
    expect(screen.getByLabelText('项目描述')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Registry 健康')).toBeInTheDocument();
      expect(screen.getByText('32')).toBeInTheDocument();
      expect(screen.getByText('9')).toBeInTheDocument();
      expect(screen.getByText('什么时候需要增加空间分类')).toBeInTheDocument();
      expect(screen.getByText('新增机制')).toBeInTheDocument();
      expect(screen.getByText('missing_type_operating_profiles')).toBeInTheDocument();
      expect(screen.getByText('commercial_enterprise')).toBeInTheDocument();
    });
  });

  it('lists and edits a space classification record', async () => {
    render(<SpaceClassificationAdminPage />);

    await waitFor(() => {
      expect(screen.getByText('商业餐饮')).toBeInTheDocument();
      expect(screen.getByText('住商混合 / 复合业态空间')).toBeInTheDocument();
      expect(screen.getAllByText('Profile').length).toBeGreaterThan(0);
      expect(screen.getAllByText('commercial_dining_profile').length).toBeGreaterThan(0);
      expect(screen.getByText('hybrid_residential_commercial_profile')).toBeInTheDocument();
      expect(screen.getByText('Type Operating Profile')).toBeInTheDocument();
      expect(screen.getByText('method.type.commercial_dining.v1')).toBeInTheDocument();
      expect(screen.getByText('dining_concept_and_positioning')).toBeInTheDocument();
      expect(screen.getAllByText('kp.commercial_dining').length).toBeGreaterThan(0);
      expect(screen.getByText('commercial_floorplan_reasoning')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: '编辑 commercial_dining' }));
    fireEvent.change(screen.getByLabelText('显示名称'), { target: { value: '餐饮空间' } });
    fireEvent.change(screen.getByLabelText('说明'), {
      target: { value: '面向餐饮、茶饮和复合消费场景。' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存空间分类' }));

    await waitFor(() => {
      expect(mockedAxios.patch).toHaveBeenCalledWith(
        'http://127.0.0.1:8001/api/admin/space-classification/types/commercial_dining',
        expect.objectContaining({
          display_name: '餐饮空间',
          description: '面向餐饮、茶饮和复合消费场景。',
        }),
        expect.any(Object)
      );
    });
  });

  it('renders subdomain registry governance and activation pack status', async () => {
    render(<SpaceClassificationAdminPage />);

    await waitFor(() => {
      expect(screen.getByText('子域 Subdomain')).toBeInTheDocument();
      expect(screen.getByText('tea_drink_store')).toBeInTheDocument();
      expect(screen.getByText('coffee_shop')).toBeInTheDocument();
      expect(screen.getAllByText('tea_drink_store_pack').length).toBeGreaterThan(0);
      expect(screen.getByText('coffee_shop_pack')).toBeInTheDocument();
      expect(screen.getAllByText('已加载').length).toBeGreaterThan(0);
      expect(screen.getAllByText('routing 匹配').length).toBeGreaterThan(0);
      expect(screen.getByText('茶饮')).toBeInTheDocument();
      expect(screen.getByText('精品咖啡')).toBeInTheDocument();
    });
  });

  it('surfaces candidate discovery and manual review in the space classification page', async () => {
    window.confirm = jest.fn(() => true);
    render(<SpaceClassificationAdminPage />);

    await waitFor(() => {
      expect(screen.getByText('候选发现')).toBeInTheDocument();
      expect(screen.getByText('人工复核')).toBeInTheDocument();
      expect(screen.getByText('pet_friendly_retail')).toBeInTheDocument();
      expect(screen.getByText('宠物友好零售')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: '拒绝候选 pet_friendly_retail' }));

    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        'http://127.0.0.1:8001/api/admin/project-types/candidates/7/reject',
        { reason: '管理员拒绝' },
        expect.any(Object)
      );
    });

    fireEvent.click(screen.getByRole('button', { name: '手动添加候选' }));
    fireEvent.change(screen.getByLabelText('建议英文 ID'), { target: { value: 'elderly_day_care' } });
    fireEvent.change(screen.getByLabelText('中文名'), { target: { value: '长者日间照护' } });
    fireEvent.change(screen.getByLabelText('建议关键词'), { target: { value: '长者照护, 日间照料' } });
    fireEvent.click(screen.getByRole('button', { name: '创建候选' }));

    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        'http://127.0.0.1:8001/api/admin/project-types/candidates',
        expect.objectContaining({
          type_id_suggestion: 'elderly_day_care',
          name_zh: '长者日间照护',
          suggested_keywords: ['长者照护', '日间照料'],
        }),
        expect.any(Object)
      );
    });
  });

  it('renders context packet summary after diagnosis', async () => {
    mockedAxios.post.mockImplementation((url) => {
      if (url === 'http://127.0.0.1:8001/api/admin/space-classification/diagnose') {
        return Promise.resolve({
          data: {
            schema_version: 'space_classification_diagnostic.v1',
            classification_output: {
              schema_version: 'classification_output.v1.8',
              project_type_id: 'commercial_dining',
              ontology_framework_id: 'commercial_dining',
              subdomain_id: 'tea_drink_store',
              activation_pack_id: 'tea_drink_store_pack',
              founding_type: 'operating_business',
              project_scale: 'interior_fitout',
              discipline_scope: ['interior', 'mep'],
              lead_discipline: 'interior',
              hard_constraint_discipline_ids: ['mep'],
              project_conditions: ['takeaway_priority'],
            },
            classification: {
              status: 'draft',
              project_type: 'commercial_dining',
              project_type_name: '商业餐饮',
              confidence: 0.86,
              primary_bucket: 'hospitality',
            },
            binding_summary: {
              ontology_framework_id: 'hybrid_residential_commercial',
              subdomain_id: undefined,
              activation_pack_id: undefined,
              secondary_activation_pack_ids: ['tea_drink_store_pack'],
              project_scale: 'building_renovation',
              spatial_layer_ids: ['building_layer', 'interior_layer'],
              ontology_dimension_ids: ['E6_operation_system'],
              knowledge_package_ids: ['kp.tea_drink_store', 'kp.residential'],
            },
            context_packet: {
              schema_version: 'context_packet.v3.3',
              classification: {
                project_type_id: 'hybrid_residential_commercial',
                subdomain: { primary_subdomain_id: undefined },
                founding_type_id: 'operating_business',
                project_scale: 'building_renovation',
              },
              context_vector: {
                primary_space_type: 'HybridResidentialCommercial',
                site_context: 'Unknown',
                service_mode: 'TakeawayPriority',
                investment_boundary: 'CostSensitive',
              },
              output_mode: {
                primary_output_mode: 'design_brief',
                user_visible_container: 'DesignBrief_2_0',
              },
              discipline_switch: {
                spatial_extent_level: 'interior',
                required_disciplines: ['interior', 'mep'],
                current_coverage: 'covered',
              },
              missing_slots: [
                {
                  name: 'water_drainage_point',
                  severity: 'high',
                  action: 'certainty_ceiling',
                  active_for_current_round: true,
                  deferred_by: '',
                  user_visible_note: '需要确认给排水点。',
                },
                {
                  name: 'peak_order_volume',
                  severity: 'high',
                  action: 'branch_answer_plus_followup',
                  active_for_current_round: false,
                  deferred_by: 'P1_physical_constraint_gate',
                  user_visible_note: '需要确认高峰订单量。',
                },
              ],
              activation_pack_coordination: {
                schema_version: 'activation_pack_coordination.v1',
                mode: 'composite_secondary_pack_merge',
                primary_pack_id: undefined,
                secondary_pack_ids: ['tea_drink_store_pack'],
                loaded_pack_ids: ['tea_drink_store_pack'],
                merge_policy: 'additive_no_primary_classification_override',
                secondary_packs: [
                  {
                    pack_id: 'tea_drink_store_pack',
                    subdomain_id: 'tea_drink_store',
                    parent_project_type_id: 'commercial_dining',
                    confidence: 0.3,
                    matched_keywords: ['茶饮'],
                    role: 'secondary_function_pack',
                  },
                ],
              },
              ontology_binding: {
                ontology_framework_id: 'commercial_dining',
                activation_pack_id: 'tea_drink_store_pack',
                secondary_activation_pack_ids: [],
                spatial_layer_ids: ['interior_layer'],
                ontology_dimension_ids: ['E6_operation_system'],
                priority_ontology_dimension_ids: ['E6_operation_system'],
              },
              knowledge_binding: {
                knowledge_package_ids: ['kp.tea_drink_store'],
                knowledge_card_weights: {},
              },
            },
            capability_plan: {
              schema_version: 'capability_plan.v1',
              registry: {
                schema_version: 'capability_registry.v1',
                status: 'ok',
                path: 'intelligent_project_analyzer/config/registries/capability_registry.yaml',
                issues: [],
              },
              status: 'degraded',
              maturity_ceiling: 'conditional_framework',
              output_mode: 'design_brief',
              required_disciplines: ['interior', 'mep'],
              discipline_coverage: 'covered',
              capability_nodes: [
                {
                  capability_group: 'Understanding',
                  name: '理解力',
                  status: 'active',
                  primary_principle: '先定位',
                  maturity_ceiling_rule: '',
                  evidence_requirement: '',
                  blocking_missing_slots: [],
                },
                {
                  capability_group: 'Generation',
                  name: '生成力',
                  status: 'degraded',
                  primary_principle: '结论封顶',
                  maturity_ceiling_rule: 'P1/P2 missing slots cap output certainty',
                  evidence_requirement: '',
                  blocking_missing_slots: ['water_drainage_point'],
                },
                {
                  capability_group: 'MemoryGovernance',
                  name: '沉淀力',
                  status: 'degraded',
                  primary_principle: '顺手记账',
                  maturity_ceiling_rule: 'missing hard facts can only create project notes, not reusable knowledge',
                  evidence_requirement: 'evidence_chain_required_before_promotion',
                  blocking_missing_slots: ['water_drainage_point'],
                },
              ],
            },
            normalization_trace: {
              schema_version: 'type_alias_normalization_trace.v1',
              original_text: '1楼艺术展厅，4楼KTV房。',
              normalized_text: '1楼美术馆厅,4楼ktv房。',
              changed: true,
              fullwidth_converted: true,
              replacements: [
                {
                  alias: '艺术展',
                  canonical: '美术馆',
                  source: 'static',
                  start: 2,
                  end: 5,
                },
                {
                  alias: 'KTV',
                  canonical: 'ktv',
                  source: 'static',
                  start: 10,
                  end: 13,
                },
              ],
            },
            coverage_gaps: [],
            health: { severity: 'ok', blocking_count: 0, warning_count: 0 },
            activation_pack_preview: { loaded: true },
            subdomain_signals: [
              {
                suggested_subdomain_id: 'tea_drink_store',
                activation_pack_id: 'tea_drink_store_pack',
                confidence: 0.8,
                matched_keywords: ['茶饮', '新茶饮'],
              },
            ],
            founding_type_candidates: [
              {
                founding_type_id: 'operating_business',
                confidence: 0.72,
                matched_keywords: {
                  primary: ['开店'],
                  secondary: ['高峰'],
                },
              },
            ],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    render(<SpaceClassificationAdminPage />);
    fireEvent.click(screen.getByRole('button', { name: '识别空间分类' }));

    await waitFor(() => {
      expect(screen.getByText('Context Packet')).toBeInTheDocument();
      expect(screen.getByText('Activation Pack Coordination')).toBeInTheDocument();
      expect(screen.getByText('Classification Output')).toBeInTheDocument();
      expect(screen.getByText('Subdomain Signals')).toBeInTheDocument();
      expect(screen.getByText('Founding Type Candidates')).toBeInTheDocument();
      expect(screen.getAllByText('tea_drink_store').length).toBeGreaterThan(0);
      expect(screen.getAllByText('tea_drink_store_pack').length).toBeGreaterThan(0);
      expect(screen.getByText('composite_secondary_pack_merge')).toBeInTheDocument();
      expect(screen.getByText('secondary_function_pack')).toBeInTheDocument();
      expect(screen.getByText('80%')).toBeInTheDocument();
      expect(screen.getByText('classification_output.v1.8')).toBeInTheDocument();
      expect(screen.getAllByText('operating_business').length).toBeGreaterThan(0);
      expect(screen.getByText('72%')).toBeInTheDocument();
      expect(screen.getByText('开店')).toBeInTheDocument();
      expect(screen.getByText('context_packet.v3.3')).toBeInTheDocument();
      expect(screen.getByText('Packet Governance')).toBeInTheDocument();
      expect(screen.getByText('Capability Plan')).toBeInTheDocument();
      expect(screen.getByText('capability_plan.v1')).toBeInTheDocument();
      expect(screen.getByText('Capability Registry')).toBeInTheDocument();
      expect(screen.getByText('capability_registry.v1')).toBeInTheDocument();
      expect(screen.getByText('intelligent_project_analyzer/config/registries/capability_registry.yaml')).toBeInTheDocument();
      expect(screen.getByText('conditional_framework')).toBeInTheDocument();
      expect(screen.getByText('Generation')).toBeInTheDocument();
      expect(screen.getByText('结论封顶')).toBeInTheDocument();
      expect(screen.getByText('P1/P2 missing slots cap output certainty')).toBeInTheDocument();
      expect(screen.getAllByText('commercial_dining').length).toBeGreaterThan(0);
      expect(screen.getAllByText('tea_drink_store_pack').length).toBeGreaterThan(0);
      expect(screen.getAllByText('kp.tea_drink_store').length).toBeGreaterThan(0);
      expect(screen.getByText('HybridResidentialCommercial')).toBeInTheDocument();
      expect(screen.getByText('TakeawayPriority')).toBeInTheDocument();
      expect(screen.getAllByText('design_brief').length).toBeGreaterThan(0);
      expect(screen.getAllByText('water_drainage_point').length).toBeGreaterThan(0);
      expect(screen.getByText('本轮追问')).toBeInTheDocument();
      expect(screen.getByText('后置')).toBeInTheDocument();
      expect(screen.getByText('P1_physical_constraint_gate')).toBeInTheDocument();
      expect(screen.getByText('关键词归一过程')).toBeInTheDocument();
      expect(screen.getByText('1楼美术馆厅,4楼ktv房。')).toBeInTheDocument();
      expect(screen.getByText('艺术展')).toBeInTheDocument();
      expect(screen.getByText('美术馆')).toBeInTheDocument();
      expect(screen.getByText('KTV')).toBeInTheDocument();
      expect(screen.getByText('ktv')).toBeInTheDocument();
    });
  });
});
