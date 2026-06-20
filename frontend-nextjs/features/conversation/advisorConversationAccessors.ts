import type { SetStateAction } from 'react';

import type { AdvisorConversationMessagesByScene } from './conversationLocalPersistence';
import type { ChatMessage } from './types';

export function buildAdvisorConversationKey({
  sessionId,
  sceneKey,
}: {
  sessionId: string;
  sceneKey: string;
}): string {
  return `${sessionId}::${sceneKey}`;
}

export function getAdvisorConversationMessages({
  messagesByScene,
  activeKey,
  emptyFallback,
}: {
  messagesByScene: AdvisorConversationMessagesByScene;
  activeKey: string;
  emptyFallback: ChatMessage[];
}): ChatMessage[] {
  return messagesByScene[activeKey] ?? emptyFallback;
}

export function updateAdvisorConversationMessages({
  messagesByScene,
  activeKey,
  updater,
}: {
  messagesByScene: AdvisorConversationMessagesByScene;
  activeKey: string;
  updater: SetStateAction<ChatMessage[]>;
}): AdvisorConversationMessagesByScene {
  const current = messagesByScene[activeKey] ?? [];
  const nextMessages = typeof updater === 'function'
    ? (updater as (value: ChatMessage[]) => ChatMessage[])(current)
    : updater;
  return {
    ...messagesByScene,
    [activeKey]: nextMessages,
  };
}
