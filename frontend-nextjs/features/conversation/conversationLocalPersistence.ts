import type { ChatMessage } from './types';

export const ADVISOR_CONVERSATION_STORAGE_KEY = 'analysis.advisor.conversations.v1';

export type AdvisorConversationMessagesByScene = Record<string, ChatMessage[]>;

type ConversationStorage = Pick<Storage, 'getItem' | 'setItem'>;

export function restoreAdvisorConversationMessages({
  storage,
  onError,
}: {
  storage: ConversationStorage;
  onError?: (error: unknown) => void;
}): AdvisorConversationMessagesByScene | null {
  try {
    const raw = storage.getItem(ADVISOR_CONVERSATION_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
    return parsed as AdvisorConversationMessagesByScene;
  } catch (error) {
    onError?.(error);
    return null;
  }
}

export function persistAdvisorConversationMessages({
  storage,
  messagesByScene,
  onError,
}: {
  storage: ConversationStorage;
  messagesByScene: AdvisorConversationMessagesByScene;
  onError?: (error: unknown) => void;
}): void {
  try {
    storage.setItem(ADVISOR_CONVERSATION_STORAGE_KEY, JSON.stringify(messagesByScene));
  } catch (error) {
    onError?.(error);
  }
}
