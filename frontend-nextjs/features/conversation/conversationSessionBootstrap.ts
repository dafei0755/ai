import {
  buildConversationMessagesFromHistory,
  hydrateMissingGuidanceCards,
  type ConversationHistoryEntry,
} from './conversationHistoryAdapter';
import type { ChatMessage } from './types';

type ConversationSessionStatus = {
  conversation_history_v2?: ConversationHistoryEntry[] | null;
};

type BootstrapPayload = {
  userMessage: string;
  aiReply: string;
  guidance_card?: ChatMessage['guidance_card'];
};

export type BootstrapConversationSessionOptions = {
  sessionId: string;
  storage: Pick<Storage, 'getItem' | 'removeItem'>;
  getStatus: (sessionId: string) => Promise<ConversationSessionStatus>;
  now?: () => string;
  onInitialMessages?: (messages: ChatMessage[]) => void;
  onRestoredMessages?: (messages: ChatMessage[]) => void;
  onRestoreError?: (error: unknown) => void;
};

export type BootstrapConversationSessionResult = {
  initialMessages: ChatMessage[];
  restoredMessages: ChatMessage[];
};

const buildInitialMessages = (
  payload: BootstrapPayload,
  timestamp: string,
): ChatMessage[] => [
  {
    id: 'user-init',
    role: 'user',
    content: payload.userMessage,
    timestamp,
  },
  {
    id: 'ai-init',
    role: 'assistant',
    content: payload.aiReply,
    timestamp,
    guidance_card: payload.guidance_card ?? undefined,
  },
];

export async function bootstrapConversationSession({
  sessionId,
  storage,
  getStatus,
  now = () => new Date().toISOString(),
  onInitialMessages,
  onRestoredMessages,
  onRestoreError,
}: BootstrapConversationSessionOptions): Promise<BootstrapConversationSessionResult> {
  let initialMessages: ChatMessage[] = [];
  const initKey = `conv_init_${sessionId}`;
  const initRaw = storage.getItem(initKey);

  if (initRaw) {
    try {
      const payload = JSON.parse(initRaw) as BootstrapPayload;
      initialMessages = buildInitialMessages(payload, now());
      onInitialMessages?.(initialMessages);
    } catch (_) {
      // Keep legacy behavior: invalid bootstrap payloads are ignored.
    }
    storage.removeItem(initKey);
  }

  try {
    const data = await getStatus(sessionId);
    const restoredMessages = hydrateMissingGuidanceCards(
      buildConversationMessagesFromHistory(data.conversation_history_v2 ?? undefined),
      initialMessages,
    );
    if (restoredMessages.length > 0) {
      onRestoredMessages?.(restoredMessages);
    }
    return {
      initialMessages,
      restoredMessages,
    };
  } catch (error) {
    onRestoreError?.(error);
    return {
      initialMessages,
      restoredMessages: [],
    };
  }
}
