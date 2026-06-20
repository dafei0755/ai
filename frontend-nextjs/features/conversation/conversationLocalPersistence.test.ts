import {
  ADVISOR_CONVERSATION_STORAGE_KEY,
  persistAdvisorConversationMessages,
  restoreAdvisorConversationMessages,
} from './conversationLocalPersistence';
import type { ChatMessage } from './types';

const createStorage = (initial: Record<string, string> = {}) => {
  const values = new Map(Object.entries(initial));

  return {
    getItem: jest.fn((key: string) => values.get(key) ?? null),
    setItem: jest.fn((key: string, value: string) => {
      values.set(key, value);
    }),
  };
};

describe('conversationLocalPersistence', () => {
  it('restores advisor conversation messages by scene from local storage', () => {
    const messages: Record<string, ChatMessage[]> = {
      'session::scene': [
        {
          id: 'user-1',
          role: 'user',
          content: 'return home',
          timestamp: '2026-06-20T00:00:00.000Z',
        },
      ],
    };
    const storage = createStorage({
      [ADVISOR_CONVERSATION_STORAGE_KEY]: JSON.stringify(messages),
    });

    expect(restoreAdvisorConversationMessages({ storage })).toEqual(messages);
    expect(storage.getItem).toHaveBeenCalledWith(ADVISOR_CONVERSATION_STORAGE_KEY);
  });

  it('ignores invalid advisor conversation payloads and reports parse errors', () => {
    const storage = createStorage({
      [ADVISOR_CONVERSATION_STORAGE_KEY]: '{bad json',
    });
    const onError = jest.fn();

    expect(restoreAdvisorConversationMessages({ storage, onError })).toBeNull();
    expect(onError).toHaveBeenCalled();

    const arrayStorage = createStorage({
      [ADVISOR_CONVERSATION_STORAGE_KEY]: JSON.stringify([]),
    });

    expect(restoreAdvisorConversationMessages({ storage: arrayStorage })).toBeNull();
  });

  it('persists advisor conversation messages by scene to local storage', () => {
    const storage = createStorage();
    const messages: Record<string, ChatMessage[]> = {
      'session::scene': [
        {
          id: 'assistant-1',
          role: 'assistant',
          content: 'start from belonging',
          timestamp: '2026-06-20T00:01:00.000Z',
        },
      ],
    };

    persistAdvisorConversationMessages({
      storage,
      messagesByScene: messages,
    });

    expect(storage.setItem).toHaveBeenCalledWith(
      ADVISOR_CONVERSATION_STORAGE_KEY,
      JSON.stringify(messages),
    );
  });
});
