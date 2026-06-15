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
