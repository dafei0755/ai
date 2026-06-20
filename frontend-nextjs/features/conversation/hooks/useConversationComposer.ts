'use client';

import { useCallback, useEffect, useState, type KeyboardEvent, type RefObject } from 'react';

import type { AdvisorSceneContext, ConversationChatProps } from '@/features/conversation/types';

export interface UseConversationComposerParams {
  loading?: boolean;
  onSendMessage: ConversationChatProps['onSendMessage'];
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  prefillHint?: ConversationChatProps['prefillHint'];
  advisorSceneContext?: AdvisorSceneContext | null;
}

export function useConversationComposer({
  loading = false,
  onSendMessage,
  textareaRef,
  prefillHint = null,
  advisorSceneContext = null,
}: UseConversationComposerParams) {
  const [inputText, setInputText] = useState('');

  useEffect(() => {
    if (!prefillHint?.text) return;
    setInputText((prev) => {
      if (prev.includes(prefillHint.text)) return prev;
      return `${prev} ${prefillHint.text}`.trim();
    });
    textareaRef.current?.focus();
  }, [prefillHint?.id, prefillHint?.text, textareaRef]);

  const handleSend = useCallback(() => {
    const trimmed = inputText.trim();
    if (!trimmed || loading) return;
    onSendMessage(trimmed);
    setInputText('');
    textareaRef.current?.focus();
  }, [inputText, loading, onSendMessage, textareaRef]);

  const handleAdvisorPrompt = useCallback(
    (intent: 'deep-dive' | 'action-list') => {
      if (!advisorSceneContext) return;
      const prompt =
        intent === 'deep-dive'
          ? `@${advisorSceneContext.sceneRef}\n请基于左侧当前场景继续深挖：先指出关键矛盾，再给出风险判断、设计取舍和可验证的下一步。`
          : `@${advisorSceneContext.sceneRef}\n请把左侧当前场景转成行动清单：按优先级列出今天能推进的判断、资料缺口、方案动作和验证方式。`;
      setInputText(prompt);
      textareaRef.current?.focus();
    },
    [advisorSceneContext, textareaRef],
  );

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  return {
    inputText,
    setInputText,
    handleSend,
    handleAdvisorPrompt,
    handleKeyDown,
  };
}
