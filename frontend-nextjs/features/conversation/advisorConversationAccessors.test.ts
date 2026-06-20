import {
  buildAdvisorConversationKey,
  getAdvisorConversationMessages,
  updateAdvisorConversationMessages,
} from './advisorConversationAccessors';
import type { AdvisorConversationMessagesByScene } from './conversationLocalPersistence';
import type { ChatMessage } from './types';

const userMessage: ChatMessage = {
  id: 'user-1',
  role: 'user',
  content: 'hometown house',
  timestamp: '2026-06-20T00:00:00.000Z',
};

describe('advisorConversationAccessors', () => {
  it('builds the active advisor conversation key from session and scene', () => {
    expect(buildAdvisorConversationKey({
      sessionId: 'conv-123',
      sceneKey: 'project::board',
    })).toBe('conv-123::project::board');
  });

  it('returns active conversation messages or the provided empty fallback', () => {
    const messagesByScene: AdvisorConversationMessagesByScene = {
      'conv-123::project::board': [userMessage],
    };
    const emptyFallback: ChatMessage[] = [];

    expect(getAdvisorConversationMessages({
      messagesByScene,
      activeKey: 'conv-123::project::board',
      emptyFallback,
    })).toEqual([userMessage]);
    expect(getAdvisorConversationMessages({
      messagesByScene,
      activeKey: 'conv-123::missing',
      emptyFallback,
    })).toBe(emptyFallback);
  });

  it('updates the active conversation with a function updater', () => {
    const messagesByScene: AdvisorConversationMessagesByScene = {
      'conv-123::project::board': [userMessage],
      'conv-123::project::files': [],
    };

    expect(updateAdvisorConversationMessages({
      messagesByScene,
      activeKey: 'conv-123::project::board',
      updater: (current) => [
        ...current,
        {
          id: 'assistant-1',
          role: 'assistant',
          content: 'start from belonging',
          timestamp: '2026-06-20T00:01:00.000Z',
        },
      ],
    })).toEqual({
      'conv-123::project::board': [
        userMessage,
        {
          id: 'assistant-1',
          role: 'assistant',
          content: 'start from belonging',
          timestamp: '2026-06-20T00:01:00.000Z',
        },
      ],
      'conv-123::project::files': [],
    });
  });

  it('updates the active conversation with a direct messages array', () => {
    expect(updateAdvisorConversationMessages({
      messagesByScene: {},
      activeKey: 'conv-123::project::board',
      updater: [userMessage],
    })).toEqual({
      'conv-123::project::board': [userMessage],
    });
  });
});
