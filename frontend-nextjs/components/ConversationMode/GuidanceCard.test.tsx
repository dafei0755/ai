import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import GuidanceCardWidget from './GuidanceCard';
import { type GuidanceCardData } from './ConversationChat';

describe('GuidanceCardWidget', () => {
  it('renders demand reconstruction cards without formal intake wording', async () => {
    const user = userEvent.setup();
    const onRespond = jest.fn();
    const card: GuidanceCardData = {
      card_id: 'demand_reconstruction-blueprint-homecoming',
      card_type: 'demand_reconstruction_blueprint',
      title: '需求重构',
      prompt_text: '这不是一个民居风格问题，而是返乡身份与空间关系的问题。',
      options: [
        {
          id: 'continue_demand_reconstruction',
          label: '继续需求重构',
          description: '继续把这个问题想清楚，不进入正式任务书。',
        },
        {
          id: 'handoff_to_brief',
          label: '整理成设计任务书草稿',
          description: '把当前行动蓝图带入正式任务书问诊。',
          recommended: true,
        },
      ],
      allow_freetext: true,
    };

    render(<GuidanceCardWidget card={card} onRespond={onRespond} />);

    expect(screen.getAllByText('需求重构').length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText('行动蓝图')).not.toBeInTheDocument();
    expect(screen.getByText('继续需求重构')).toBeInTheDocument();
    expect(screen.queryByText('关键确认')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /提交首轮判断/ })).not.toBeInTheDocument();

    await user.click(screen.getByText('整理成设计任务书草稿'));
    await user.click(screen.getByRole('button', { name: /确认方向/ }));

    expect(onRespond).toHaveBeenCalledWith(
      'handoff_to_brief',
      undefined,
      expect.objectContaining({
        pages: [
          expect.objectContaining({
            selected_option_id: 'handoff_to_brief',
          }),
        ],
      }),
    );
  });

  it('renders dynamic demand reconstruction blueprint sections', () => {
    const onRespond = jest.fn();
    const card: GuidanceCardData = {
      card_id: 'demand_reconstruction-blueprint-dynamic',
      card_type: 'demand_reconstruction_blueprint',
      title: '需求重构',
      prompt_text: '这不是直接给方案的问题，而是先判断项目命门。',
      options: [],
      sections: [
        {
          title: '身份与生活结构',
          body: '先判断这栋房子要承接哪一种人生位置。',
          items: ['职业身份会推动设计表达。', '作品化风险会压过真实使用。'],
          emphasis: 'high',
        },
        {
          title: '路径分流',
          body: '三条路会导向不同任务书重心。',
          items: ['生活优先型', '生活+工作混合型', '作品化住宅型'],
          emphasis: 'medium',
        },
      ],
      allow_freetext: true,
    };

    render(<GuidanceCardWidget card={card} onRespond={onRespond} />);

    expect(screen.getByText('身份与生活结构')).toBeInTheDocument();
    expect(screen.getByText('先判断这栋房子要承接哪一种人生位置。')).toBeInTheDocument();
    expect(screen.getByText('作品化风险会压过真实使用。')).toBeInTheDocument();
    expect(screen.getByText('路径分流')).toBeInTheDocument();
    expect(screen.getByText('生活+工作混合型')).toBeInTheDocument();
  });

  it('renders demand reconstruction insight packets as a visible reasoning module without model wording', () => {
    const onRespond = jest.fn();
    const card: GuidanceCardData = {
      card_id: 'demand_reconstruction-blueprint-insight',
      card_type: 'demand_reconstruction_blueprint',
      title: '需求重构',
      prompt_text: '先判断这是不是一个单纯风格问题。',
      options: [],
      summary: {
        insight_packet: {
          chosen_hypothesis: '阶段性返乡与身份重建混合型',
          core_tension: '作品冲动与长期生活之间的冲突',
          hypotheses: ['作品化住宅', '长期生活基地'],
        },
      },
      allow_freetext: true,
    };

    render(<GuidanceCardWidget card={card} onRespond={onRespond} />);

    expect(screen.getByText('判断依据')).toBeInTheDocument();
    expect(screen.queryByText('模型洞察')).not.toBeInTheDocument();
    expect(screen.getByText('阶段性返乡与身份重建混合型')).toBeInTheDocument();
    expect(screen.getByText(/作品冲动与长期生活之间的冲突/)).toBeInTheDocument();
    expect(screen.getByText('作品化住宅')).toBeInTheDocument();
    expect(screen.getByText('长期生活基地')).toBeInTheDocument();
  });

  it('renders structured core tension from insight packets without leaking diagnostics', () => {
    const onRespond = jest.fn();
    const card: GuidanceCardData = {
      card_id: 'demand_reconstruction-blueprint-structured-insight',
      card_type: 'demand_reconstruction_blueprint',
      title: '需求重构',
      prompt_text: '先判断这个项目的主矛盾。',
      options: [],
      summary: {
        insight_source: 'llm',
        llm_status: 'used',
        quality_report: {
          accepted_fields: ['insight_packet'],
        },
        governance_signals: [
          { code: 'coverage_gap', review_queue: 'space_registry_review' },
          { code: 'semantic_alignment_rejection', review_queue: 'wrong_domain_output_review' },
        ],
        insight_packet: {
          chosen_hypothesis: '康复训练与家庭日常混合型',
          core_tension: {
            a: '复健训练',
            b: '家庭日常',
            why_it_matters: '两者会决定通道尺度、器械停放和照护动线。',
          },
          hypotheses: ['康复优先', '日常优先'],
        },
      },
      allow_freetext: true,
    };

    render(<GuidanceCardWidget card={card} onRespond={onRespond} />);

    expect(screen.getByText('判断依据')).toBeInTheDocument();
    expect(screen.getByText(/复健训练与家庭日常：两者会决定通道尺度、器械停放和照护动线。/)).toBeInTheDocument();
    expect(screen.queryByText('llm')).not.toBeInTheDocument();
    expect(screen.queryByText('used')).not.toBeInTheDocument();
    expect(screen.queryByText('quality_report')).not.toBeInTheDocument();
    expect(screen.queryByText('coverage_gap')).not.toBeInTheDocument();
    expect(screen.queryByText('space_registry_review')).not.toBeInTheDocument();
    expect(screen.queryByText('semantic_alignment_rejection')).not.toBeInTheDocument();
    expect(screen.queryByText('wrong_domain_output_review')).not.toBeInTheDocument();
  });

  it('renders demand reconstruction coverage level as a visible boundary module', () => {
    const onRespond = jest.fn();
    const card: GuidanceCardData = {
      card_id: 'demand_reconstruction-blueprint-coverage',
      card_type: 'demand_reconstruction_blueprint',
      title: '需求重构',
      prompt_text: '这个项目需要先判断知识覆盖边界。',
      options: [],
      summary: {
        coverage_level: 'general_method_only',
      },
      allow_freetext: true,
    };

    render(<GuidanceCardWidget card={card} onRespond={onRespond} />);

    expect(screen.getByText('覆盖边界')).toBeInTheDocument();
    expect(screen.getByText('通用方法论')).toBeInTheDocument();
    expect(screen.getByText('当前只能先按通用方法论重构，不应伪装成专科判断。')).toBeInTheDocument();
  });

  it.each(['methodology_framework', 'l0', 'low', 'limited'])(
    'renders backend low-coverage level %s as a visible boundary module',
    (coverageLevel) => {
      const onRespond = jest.fn();
      const card: GuidanceCardData = {
        card_id: `demand_reconstruction-blueprint-${coverageLevel}`,
        card_type: 'demand_reconstruction_blueprint',
        title: '需求重构',
        prompt_text: '这个项目需要先判断知识覆盖边界。',
        options: [],
        summary: {
          coverage_level: coverageLevel,
        },
        allow_freetext: true,
      };

      render(<GuidanceCardWidget card={card} onRespond={onRespond} />);

      expect(screen.getByText('覆盖边界')).toBeInTheDocument();
      expect(screen.getByText('通用方法论')).toBeInTheDocument();
      expect(screen.getByText('当前只能先按通用方法论重构，不应伪装成专科判断。')).toBeInTheDocument();
    },
  );

  it('renders user-facing labels for context packet missing-slot pages', async () => {
    const user = userEvent.setup();
    const onRespond = jest.fn();
    const card: GuidanceCardData = {
      card_id: 'scheme-round-1-context-packet',
      card_type: 'scheme_round_1',
      title: '首轮判断',
      prompt_text: '需要补齐关键条件。',
      options: [],
      pages: [
        {
          page_title: '先确认硬约束',
          prompt_text: '这些条件不清楚时，我只能给条件级判断。',
          helper_text: '请先确认设备和上下水边界。',
          source: 'context_packet.missing_slots',
          missing_slot_action: 'certainty_ceiling',
          missing_slot_names: ['back_of_house_equipment_scope', 'water_drainage_point'],
          response_mode: 'confirmation_status',
          options: [
            {
              id: 'back_of_house_equipment_scope_known',
              label: '设备范围已明确',
              description: '已经知道后厨设备和吧台设备边界。',
            },
          ],
        },
        {
          page_title: '补齐经营事实',
          prompt_text: '这些信息会改变判断分支。',
          source: 'context_packet.missing_slots',
          missing_slot_action: 'branch_answer_plus_followup',
          missing_slot_names: ['store_model', 'peak_order_volume'],
          response_mode: 'fact_status',
          options: [
            {
              id: 'store_model_known',
              label: '店型已明确',
              description: '已经确认堂食、外带和出杯压力。',
            },
          ],
        },
      ],
    };

    render(<GuidanceCardWidget card={card} onRespond={onRespond} />);

    expect(screen.getByText('现实边界缺口')).toBeInTheDocument();
    expect(screen.getByText('请先确认设备和上下水边界。')).toBeInTheDocument();
    expect(screen.getByText('设备范围已明确')).toBeInTheDocument();

    await user.click(screen.getByText('设备范围已明确'));
    await user.click(screen.getByRole('button', { name: /下一问/ }));

    expect(screen.getByText('经营事实缺口')).toBeInTheDocument();
    expect(screen.getByText('店型已明确')).toBeInTheDocument();
  });

  it('submits multi-page scheme answers as structured selections', async () => {
    const user = userEvent.setup();
    const onRespond = jest.fn();
    const card: GuidanceCardData = {
      card_id: 'scheme-round-1-market',
      card_type: 'scheme_round_1',
      title: '首轮判断',
      prompt_text: '确认公共市场更新判断。',
      options: [],
      pages: [
        {
          page_title: '先确认市场更新优先保住什么',
          prompt_text: '这个项目最不能牺牲哪两件事？',
          response_mode: 'multi_select',
          max_select: 2,
          allow_freetext: true,
          options: [
            { id: 'resident_daily_buying', label: '居民日常买菜', description: '保住老居民的可达性和菜价感知。' },
            { id: 'visitor_experience', label: '访客体验', description: '让游客愿意停留和理解蛇口文化。' },
          ],
        },
        {
          page_title: '再确认后勤底线',
          prompt_text: '哪些条件必须先说清？',
          response_mode: 'priority_pick',
          max_select: 2,
          allow_freetext: true,
          options: [
            { id: 'cold_chain', label: '冷链', description: '影响生鲜品质和后场组织。' },
            { id: 'drainage', label: '排水排污', description: '影响卫生、气味和日常维护。' },
          ],
        },
      ],
    };

    render(<GuidanceCardWidget card={card} onRespond={onRespond} />);

    await user.click(screen.getByText('居民日常买菜'));
    await user.click(screen.getByText('访客体验'));
    await user.click(screen.getByRole('button', { name: /下一问/ }));
    await user.click(screen.getByText('排水排污'));
    await user.click(screen.getByText('冷链'));
    await user.click(screen.getByRole('button', { name: /提交首轮判断/ }));

    expect(onRespond).toHaveBeenCalledWith(
      undefined,
      '居民日常买菜、访客体验; 优先级：排水排污 > 冷链',
      {
        pages: [
          {
            page_index: 0,
            page_title: '先确认市场更新优先保住什么',
            response_mode: 'multi_select',
            selected_option_ids: ['resident_daily_buying', 'visitor_experience'],
            selected_options: [
              { id: 'resident_daily_buying', label: '居民日常买菜' },
              { id: 'visitor_experience', label: '访客体验' },
            ],
          },
          {
            page_index: 1,
            page_title: '再确认后勤底线',
            response_mode: 'priority_pick',
            selected_option_ids: ['drainage', 'cold_chain'],
            selected_options: [
              { id: 'drainage', label: '排水排污', priority: 1 },
              { id: 'cold_chain', label: '冷链', priority: 2 },
            ],
          },
        ],
      },
    );
  });
});
