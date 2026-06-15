import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import GuidanceCardWidget from './GuidanceCard';
import { type GuidanceCardData } from './ConversationChat';

describe('GuidanceCardWidget', () => {
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
});
