/**
 * ConversationChat.tsx — v2.0 对话态聊天面板
 * Created by GitHub Copilot · 2026-03-22
 *
 * 对话态常驻底态的主聊天界面，支持：
 *   - 多轮对话消息列表（用户 / AI）
 *   - 草稿侧边栏收纳指示
 *   - 升级提示横幅联动
 *   - 发送输入框（回车 / 按钮提交）
 */

'use client';

import React, { useEffect, useRef } from 'react';
import { AdvisorContextPanel } from '@/features/conversation/components/AdvisorContextPanel';
import { ComposerShell } from '@/features/conversation/components/ComposerShell';
import { MessageListShell } from '@/features/conversation/components/MessageListShell';
import { UpgradeBanner } from '@/features/conversation/components/UpgradeBanner';
import { VisualBriefPanel } from '@/features/conversation/components/VisualBriefPanel';
import { useAdvisorContextDerivation } from '@/features/conversation/hooks/useAdvisorContextDerivation';
import { useConversationComposer } from '@/features/conversation/hooks/useConversationComposer';
import { useConversationLayoutState } from '@/features/conversation/hooks/useConversationLayoutState';
import type {
  ChatMessage,
  ConversationChatProps,
} from '@/features/conversation/types';

export type {
  AdvisorSceneContext,
  ChatMessage,
  ConversationChatProps,
  GuidanceCardData,
  GuidanceCardOptionData,
  GuidanceCardPage,
  GuidanceCardSectionData,
  GuidanceCardStructuredResponse,
  MessageRole,
  SchemeVersionCardData,
} from '@/features/conversation/types';

// ── 主组件 ────────────────────────────────────────────────

export default function ConversationChat({
  sessionId,
  messages,
  visualBriefContext = null,
  onVisualBriefPromptChange,
  onVisualBriefNoteChange,
  advisorSceneContext = null,
  onSendMessage,
  loading = false,
  placeholder = '输入你的想法、问题或设计需求…',
  showUpgradeBanner = false,
  onUpgradeConfirm,
  onUpgradeDismiss,
  onCardResponse,
  onCandidateCardResponse,
  prefillHint = null,
  className = '',
}: ConversationChatProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const splitPaneRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const {
    inputText,
    setInputText,
    handleSend,
    handleKeyDown,
  } = useConversationComposer({
    loading,
    onSendMessage,
    textareaRef,
    prefillHint,
    advisorSceneContext,
  });
  const {
    briefExpanded,
    setBriefExpanded,
    briefPinnedOpen,
    toggleBriefPinnedOpen,
    collapseBriefAfterHover,
    contextExpanded,
    setContextExpanded,
    contextPinnedOpen,
    toggleContextPinnedOpen,
    collapseContextAfterHover,
    contextPanePercent,
    isContextResizing,
    startContextResize,
    finishContextResize,
    updateContextPanePercentFromPointer,
  } = useConversationLayoutState({
    sessionId,
    splitPaneRef,
  });
  const adaptiveChatGutter = 'clamp(12px, 2vw, 32px)';
  const { advisorInsightLines } = useAdvisorContextDerivation({ advisorSceneContext });
  const visibleMessages = messages.filter((message) => !message.id.startsWith('scene-sync-'));

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  useEffect(() => {
    if (!isContextResizing) return;

    const handleMouseMove = (event: MouseEvent) => {
      updateContextPanePercentFromPointer(event.clientY);
    };

    const handleMouseUp = () => {
      finishContextResize();
    };

    document.body.style.cursor = 'row-resize';
    document.body.style.userSelect = 'none';
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [finishContextResize, isContextResizing, updateContextPanePercentFromPointer]);

  return (
    <div
      className={`relative flex flex-col h-full bg-[var(--background)] ${className}`}
      data-session-id={sessionId}
    >
      {showUpgradeBanner && (
        <UpgradeBanner
          adaptiveChatGutter={adaptiveChatGutter}
          onUpgradeConfirm={onUpgradeConfirm}
          onUpgradeDismiss={onUpgradeDismiss}
        />
      )}

      {visualBriefContext && (
        <VisualBriefPanel
          visualBriefContext={visualBriefContext}
          expanded={briefExpanded}
          pinnedOpen={briefPinnedOpen}
          onExpand={() => setBriefExpanded(true)}
          onCollapseAfterHover={collapseBriefAfterHover}
          onTogglePinnedOpen={toggleBriefPinnedOpen}
          onVisualBriefPromptChange={onVisualBriefPromptChange}
          onVisualBriefNoteChange={onVisualBriefNoteChange}
        />
      )}

      <div ref={splitPaneRef} className="flex-1 min-h-0 pb-28 flex flex-col">
      {advisorSceneContext && (
        <AdvisorContextPanel
          advisorSceneContext={advisorSceneContext}
          advisorInsightLines={advisorInsightLines}
          contextExpanded={contextExpanded}
          contextPinnedOpen={contextPinnedOpen}
          contextPanePercent={contextPanePercent}
          onExpand={() => setContextExpanded(true)}
          onCollapseAfterHover={collapseContextAfterHover}
          onTogglePinnedOpen={toggleContextPinnedOpen}
          onStartResize={startContextResize}
        />
      )}
      <MessageListShell
        scrollRef={scrollRef}
        visibleMessages={visibleMessages}
        loading={loading}
        adaptiveChatGutter={adaptiveChatGutter}
        onCardResponse={onCardResponse}
        onCandidateCardResponse={onCandidateCardResponse}
      />
      </div>

      <ComposerShell
        adaptiveChatGutter={adaptiveChatGutter}
        textareaRef={textareaRef}
        inputText={inputText}
        setInputText={setInputText}
        handleKeyDown={handleKeyDown}
        handleSend={handleSend}
        placeholder={placeholder}
        loading={loading}
      />
    </div>
  );
}
