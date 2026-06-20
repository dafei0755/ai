import { render, screen, within } from '@testing-library/react';
import type React from 'react';
import userEvent from '@testing-library/user-event';

import ConversationChat, { type ChatMessage } from './ConversationChat';

jest.mock('react-markdown', () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

jest.mock('remark-gfm', () => ({
  __esModule: true,
  default: () => null,
}));

describe('ConversationChat scheme advisor version card', () => {
  it('renders backend configured version names and price labels verbatim', async () => {
    const user = userEvent.setup();
    const onCardResponse = jest.fn();
    const messages: ChatMessage[] = [
      {
        id: 'assistant-version-selection-custom',
        role: 'assistant',
        content: 'Choose a version.',
        timestamp: '2026-06-10T00:00:00.000Z',
        guidance_card: {
          card_id: 'scheme-version-custom',
          card_type: 'scheme_version_selection',
          title: 'Version Selection',
          prompt_text: 'Use backend configured copy.',
          options: [],
          version_cards: [
            {
              id: 'standard',
              name: 'Backend Standard',
              subtitle: 'Backend subtitle',
              price_label: 'Configured Price',
              recommended: true,
              directory_preview: ['01 Backend module'],
            },
          ],
          recommended_version: 'standard',
        },
      },
    ];

    render(
      <ConversationChat
        sessionId="test-session"
        messages={messages}
        onSendMessage={jest.fn()}
        onCardResponse={onCardResponse}
      />
    );

    await user.click(within(screen.getByTestId('scheme-version-card')).getByRole('button'));

    expect(screen.getByText('Backend Standard')).toBeInTheDocument();
    expect(screen.getByText('Configured Price')).toBeInTheDocument();
    expect(screen.queryByText('Configured Price元')).not.toBeInTheDocument();

    const confirmButton = screen
      .getAllByRole('button', { name: /Backend Standard/ })
      .find((element) => element.tagName === 'BUTTON');
    if (!confirmButton) throw new Error('backend standard confirm button not found');
    await user.click(confirmButton);

    expect(onCardResponse).toHaveBeenCalledWith('scheme-version-custom', 'standard');
  });

  it('confirms the selected version without navigating to checkout', async () => {
    const user = userEvent.setup();
    const onCardResponse = jest.fn();
    const originalHref = window.location.href;
    const messages: ChatMessage[] = [
      {
        id: 'assistant-version-selection',
        role: 'assistant',
        content: '下面选择任务书版本。',
        timestamp: '2026-06-09T00:00:00.000Z',
        guidance_card: {
          card_id: 'scheme-version-001',
          card_type: 'scheme_version_selection',
          title: '选择任务书版本',
          prompt_text: '标准版解决经营约束对齐。',
          options: [],
          version_cards: [
            {
              id: 'basic',
              name: '基础版',
              subtitle: '解决能不能启动',
              price_label: '99元',
              directory_preview: ['01 项目基本信息'],
            },
            {
              id: 'standard',
              name: '标准版',
              subtitle: '解决能不能成立',
              price_label: '499元',
              recommended: true,
              directory_preview: ['01 项目基本信息'],
            },
          ],
          recommended_version: 'standard',
        },
      },
    ];

    render(
      <ConversationChat
        sessionId="test-session"
        messages={messages}
        onSendMessage={jest.fn()}
        onCardResponse={onCardResponse}
      />
    );

    await user.click(screen.getByRole('button', { name: /查看三档版本/ }));
    const dialog = screen.getByText('选择任务书版本').closest('.fixed');
    expect(dialog).not.toBeNull();

    const standardButton = within(dialog as HTMLElement)
      .getAllByRole('button', { name: /确认标准版/ })
      .find((element) => element.tagName === 'BUTTON');
    if (!standardButton) throw new Error('standard version confirm button not found');
    await user.click(standardButton);

    expect(onCardResponse).toHaveBeenCalledWith('scheme-version-001', 'standard');
    expect(window.location.href).toBe(originalHref);
  });
});

describe('ConversationChat demand reconstruction model status', () => {
  const baseMessage: ChatMessage = {
    id: 'assistant-demand-reconstruction',
    role: 'assistant',
    content: '## 需求重构',
    timestamp: '2026-06-18T00:00:00.000Z',
    guidance_card: {
      card_id: 'demand-reconstruction-001',
      card_type: 'demand_reconstruction_blueprint',
      title: '需求重构',
      prompt_text: '先判断真实需求。',
      options: [
        {
          id: 'continue_demand_reconstruction',
          label: '继续需求重构',
          description: '继续把问题想清楚。',
        },
      ],
      summary: {
        insight_source: 'semantic_pending_llm',
        llm_status: 'scheduled',
      },
    },
  };

  it('does not show a running model state for legacy pending demand reconstruction cards', () => {
    render(
      <ConversationChat
        sessionId="test-session"
        messages={[baseMessage]}
        onSendMessage={jest.fn()}
        onCardResponse={jest.fn()}
      />
    );

    expect(screen.queryByText('模型洞察中')).not.toBeInTheDocument();
  });

  it('does not show pending state from legacy semantic pending source', () => {
    render(
      <ConversationChat
        sessionId="test-session"
        messages={[
          {
            ...baseMessage,
            guidance_card: {
              ...baseMessage.guidance_card!,
              summary: {
                insight_source: 'semantic_pending_llm',
              },
            },
          },
        ]}
        onSendMessage={jest.fn()}
        onCardResponse={jest.fn()}
      />
    );

    expect(screen.queryByText('模型洞察中')).not.toBeInTheDocument();
  });

  it('does not expose model participation status after LLM fusion succeeds', () => {
    render(
      <ConversationChat
        sessionId="test-session"
        messages={[
          {
            ...baseMessage,
            guidance_card: {
              ...baseMessage.guidance_card!,
              summary: {
                insight_source: 'llm',
                llm_status: 'used',
              },
            },
          },
        ]}
        onSendMessage={jest.fn()}
        onCardResponse={jest.fn()}
      />
    );

    expect(screen.queryByText('模型洞察已介入')).not.toBeInTheDocument();
    expect(screen.queryByText('模型洞察失败')).not.toBeInTheDocument();
    expect(screen.queryByText('模型洞察未采纳')).not.toBeInTheDocument();
  });

  it('shows a user-facing synthesis waiting state while the first demand response is loading', () => {
    render(
      <ConversationChat
        sessionId="test-session"
        messages={[
          {
            id: 'user-project',
            role: 'user',
            content: '苏州昆曲老宅改造为教学故居，包含展陈、练声教学和小型交流，请先帮我重构需求。',
            timestamp: '2026-06-18T00:00:00.000Z',
          },
        ]}
        loading
        onSendMessage={jest.fn()}
        onCardResponse={jest.fn()}
      />
    );

    expect(screen.getByText('正在重构需求')).toBeInTheDocument();
    expect(screen.getByText('正在融合项目语义、关键约束和下一步判断。')).toBeInTheDocument();
    expect(screen.queryByText(/LLM|模型|规则蓝图|semantic|llm_status/i)).not.toBeInTheDocument();
  });

  it('uses a neutral waiting state for non-demand follow-up loading', () => {
    render(
      <ConversationChat
        sessionId="test-session"
        messages={[
          {
            id: 'user-follow-up',
            role: 'user',
            content: '把上面的第二点展开一下。',
            timestamp: '2026-06-18T00:00:00.000Z',
          },
        ]}
        loading
        onSendMessage={jest.fn()}
        onCardResponse={jest.fn()}
      />
    );

    expect(screen.getByText('正在整理回应')).toBeInTheDocument();
    expect(screen.queryByText('正在重构需求')).not.toBeInTheDocument();
  });

  it('renders demand reconstruction component intents as visible modules', () => {
    render(
      <ConversationChat
        sessionId="test-session"
        messages={[
          {
            ...baseMessage,
            guidance_card: {
              ...baseMessage.guidance_card!,
              summary: {
                insight_source: 'llm',
                llm_status: 'used',
                component_intent: [
                  {
                    type: 'conflict_check',
                    reason: 'main_tensions',
                    items: ['长期居住还是阶段性返乡'],
                    prompt: '先确认房子首先为谁服务',
                  },
                  {
                    type: 'data_checklist',
                    reason: 'missing_slots',
                    items: ['真实居住频率未知'],
                  },
                  {
                    type: 'insight_panel',
                    reason: 'default_reframe',
                    items: ['先收束项目成立条件'],
                  },
                ],
              },
            },
          },
        ]}
        onSendMessage={jest.fn()}
        onCardResponse={jest.fn()}
      />
    );

    const card = screen.getByTestId('guidance-card');
    expect(within(card).getByText('关键取舍')).toBeInTheDocument();
    expect(within(card).getByText('条件清单')).toBeInTheDocument();
    expect(within(card).getByText('洞察面板')).toBeInTheDocument();
    expect(within(card).getByText('长期居住还是阶段性返乡')).toBeInTheDocument();
    expect(within(card).getByText('先确认房子首先为谁服务')).toBeInTheDocument();
    expect(within(card).getByText('真实居住频率未知')).toBeInTheDocument();
    expect(within(card).getByText('先收束项目成立条件')).toBeInTheDocument();
  });
});
