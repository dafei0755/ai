import { bootstrapConversationSession } from './conversationSessionBootstrap';
import type { ChatMessage } from './types';

const createStorage = (initial: Record<string, string> = {}) => {
  const values = new Map(Object.entries(initial));

  return {
    getItem: jest.fn((key: string) => values.get(key) ?? null),
    removeItem: jest.fn((key: string) => values.delete(key)),
  };
};

describe('conversationSessionBootstrap', () => {
  it('restores initial conversation bootstrap messages and hydrated history', async () => {
    const card: NonNullable<ChatMessage['guidance_card']> = {
      card_id: 'demand-card',
      card_type: 'demand_reconstruction_blueprint',
      prompt_text: 'Demand reconstruction',
      options: [],
    };
    const storage = createStorage({
      'conv_init_conv-123': JSON.stringify({
        userMessage: 'I want to build a hometown house',
        aiReply: 'Start from return and belonging',
        guidance_card: card,
      }),
    });
    const onInitialMessages = jest.fn();
    const onRestoredMessages = jest.fn();

    const result = await bootstrapConversationSession({
      sessionId: 'conv-123',
      storage,
      getStatus: jest.fn(async () => ({
        conversation_history_v2: [
          {
            role: 'user',
            content: 'I want to build a hometown house',
            timestamp: '2026-06-20T00:00:00.000Z',
          },
          {
            role: 'assistant',
            content: 'Start from return and belonging',
            timestamp: '2026-06-20T00:01:00.000Z',
          },
        ],
      })),
      now: () => '2026-06-20T00:02:00.000Z',
      onInitialMessages,
      onRestoredMessages,
    });

    expect(storage.getItem).toHaveBeenCalledWith('conv_init_conv-123');
    expect(storage.removeItem).toHaveBeenCalledWith('conv_init_conv-123');
    expect(onInitialMessages).toHaveBeenCalledWith([
      {
        id: 'user-init',
        role: 'user',
        content: 'I want to build a hometown house',
        timestamp: '2026-06-20T00:02:00.000Z',
      },
      {
        id: 'ai-init',
        role: 'assistant',
        content: 'Start from return and belonging',
        timestamp: '2026-06-20T00:02:00.000Z',
        guidance_card: card,
      },
    ]);
    expect(onRestoredMessages).toHaveBeenCalledWith([
      expect.objectContaining({
        role: 'user',
        content: 'I want to build a hometown house',
      }),
      expect.objectContaining({
        role: 'assistant',
        content: 'Start from return and belonging',
        guidance_card: card,
      }),
    ]);
    expect(result.restoredMessages[1].guidance_card?.card_id).toBe('demand-card');
  });

  it('ignores invalid bootstrap payloads and reports restore errors', async () => {
    const storage = createStorage({
      'conv_init_conv-bad': '{bad json',
    });
    const restoreError = new Error('status unavailable');
    const onInitialMessages = jest.fn();
    const onRestoredMessages = jest.fn();
    const onRestoreError = jest.fn();

    const result = await bootstrapConversationSession({
      sessionId: 'conv-bad',
      storage,
      getStatus: jest.fn(async () => {
        throw restoreError;
      }),
      onInitialMessages,
      onRestoredMessages,
      onRestoreError,
    });

    expect(storage.removeItem).toHaveBeenCalledWith('conv_init_conv-bad');
    expect(onInitialMessages).not.toHaveBeenCalled();
    expect(onRestoredMessages).not.toHaveBeenCalled();
    expect(onRestoreError).toHaveBeenCalledWith(restoreError);
    expect(result).toEqual({
      initialMessages: [],
      restoredMessages: [],
    });
  });
});
