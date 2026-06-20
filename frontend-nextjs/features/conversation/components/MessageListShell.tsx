'use client';

import type React from 'react';

import { MessageCardRenderer } from '@/features/conversation/components/MessageCardRenderer';
import type { ChatMessage, GuidanceCardStructuredResponse } from '@/features/conversation/types';
import type { CandidateCardResponse } from '@/components/ConversationMode/CandidateCard';

interface MessageListShellProps {
  scrollRef: React.RefObject<HTMLDivElement | null>;
  visibleMessages: ChatMessage[];
  loading: boolean;
  adaptiveChatGutter: string;
  onCardResponse?: (
    cardId: string,
    optionId?: string,
    freetext?: string,
    structuredResponse?: GuidanceCardStructuredResponse,
  ) => void | Promise<void>;
  onCandidateCardResponse?: (response: CandidateCardResponse) => void;
}

function TypingIndicator() {
  return (
    <div className="mb-6 flex items-center gap-1.5" data-testid="typing-indicator">
      <span className="w-2 h-2 rounded-full bg-[var(--foreground-secondary)] animate-bounce [animation-delay:-0.3s]" />
      <span className="w-2 h-2 rounded-full bg-[var(--foreground-secondary)] animate-bounce [animation-delay:-0.15s]" />
      <span className="w-2 h-2 rounded-full bg-[var(--foreground-secondary)] animate-bounce" />
    </div>
  );
}

export function MessageListShell({
  scrollRef,
  visibleMessages,
  loading,
  adaptiveChatGutter,
  onCardResponse,
  onCandidateCardResponse,
}: MessageListShellProps) {
  return (
    <div ref={scrollRef} className="min-h-[140px] flex-1 overflow-y-auto" style={{ paddingInline: adaptiveChatGutter }}>
      {visibleMessages.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-center select-none">
          <div className="text-4xl mb-3">💬</div>
          <p className="ui-type-subtitle font-medium text-[var(--foreground)]">随时开始聊</p>
          <p className="ui-type-meta mt-1 text-[var(--foreground-secondary)]">分享你的想法、灵感或设计需求</p>
        </div>
      ) : (
        <div className="w-full max-w-[960px] mx-auto pt-4 pb-60" style={{ paddingInline: '2px' }}>
          {visibleMessages.map((message) => (
            <MessageCardRenderer
              key={message.id}
              message={message}
              onCardResponse={onCardResponse}
              onCandidateCardResponse={onCandidateCardResponse}
            />
          ))}
          {loading && <TypingIndicator />}
        </div>
      )}
    </div>
  );
}
