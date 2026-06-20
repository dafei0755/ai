import {
  buildConversationMessagesFromHistory,
  hydrateMissingGuidanceCards,
} from './conversationHistoryAdapter';
import type { ChatMessage } from './types';

describe('conversationHistoryAdapter', () => {
  it('marks an assistant guidance card as responded from legacy card response history', () => {
    const messages = buildConversationMessagesFromHistory([
      {
        role: 'assistant',
        content: '请选择版本',
        timestamp: '2026-06-20T00:00:00.000Z',
        guidance_card: {
          card_id: 'version-card',
          card_type: 'scheme_version_selection',
          prompt_text: '选择版本',
          options: [],
          version_cards: [
            {
              id: 'standard',
              name: '标准版',
              subtitle: '解决能不能成立',
            },
          ],
        },
      },
      {
        role: 'user',
        content: '[card:standard]',
        timestamp: '2026-06-20T00:01:00.000Z',
      },
    ]);

    expect(messages).toHaveLength(1);
    expect(messages[0]).toMatchObject({
      card_responded: true,
      card_selection_label: '标准版：解决能不能成立',
    });
  });

  it('ignores unsupported roles and preserves ordinary user and assistant messages', () => {
    const messages = buildConversationMessagesFromHistory([
      { role: 'system', content: 'hidden', timestamp: '2026-06-20T00:00:00.000Z' },
      { role: 'user', content: '我要建返乡民居', timestamp: '2026-06-20T00:01:00.000Z' },
      { role: 'assistant', content: '先做需求洞察', timestamp: '2026-06-20T00:02:00.000Z' },
    ]);

    expect(messages.map((message) => message.content)).toEqual([
      '我要建返乡民居',
      '先做需求洞察',
    ]);
  });

  it('hydrates missing assistant guidance cards from initial messages in order', () => {
    const restoredMessages: ChatMessage[] = [
      {
        id: 'restored-assistant',
        role: 'assistant',
        content: '恢复消息',
        timestamp: '2026-06-20T00:00:00.000Z',
      },
    ];
    const initialMessages: ChatMessage[] = [
      {
        id: 'initial-assistant',
        role: 'assistant',
        content: '初始消息',
        timestamp: '2026-06-20T00:00:00.000Z',
        guidance_card: {
          card_id: 'initial-card',
          card_type: 'demand_reconstruction_blueprint',
          prompt_text: '需求重构',
          options: [],
        },
      },
    ];

    expect(hydrateMissingGuidanceCards(restoredMessages, initialMessages)[0].guidance_card?.card_id)
      .toBe('initial-card');
  });
});
