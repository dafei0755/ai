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
import { VisualBriefPanel } from '@/features/conversation/components/VisualBriefPanel';
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
  activeExpertPerspective = '默认综合',
  expertPerspectiveOptions = [],
  onExpertPerspectiveChange,
  summonOptions = [],
  onSummonExpert,
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
    handleAdvisorPrompt,
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
  const advisorSuggestionLines = (advisorSceneContext?.suggestion ?? '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean);
  const advisorInsightLines = advisorSuggestionLines.filter((line) => /^\d+[.、]/.test(line)).slice(0, 3);
  const advisorClosingLine = advisorSuggestionLines[advisorSuggestionLines.length - 1];
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
      {/* 升级提示横幅 */}
      {showUpgradeBanner && (
        <div className="ui-type-meta mt-3 p-3.5 bg-amber-50 border border-amber-300 rounded-xl flex items-center gap-3 flex-shrink-0" style={{ marginInline: adaptiveChatGutter }}>
          <span className="text-amber-500 text-lg flex-shrink-0">✨</span>
          <span className="text-amber-800 flex-1">
            对话已积累足够上下文，可以整理为正式项目
          </span>
          <button
            onClick={onUpgradeConfirm}
            className="ui-type-meta px-3 py-1.5 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors flex-shrink-0"
          >
            立即整理
          </button>
          <button
            onClick={onUpgradeDismiss}
            className="ui-type-meta text-amber-400 hover:text-amber-600 flex-shrink-0"
          >
            稍后
          </button>
        </div>
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

      {false && advisorSceneContext && visibleMessages.length > 0 && (
        <div className="flex-shrink-0 border-b border-white/8 px-4 py-3">
          <div className="mx-auto max-w-[960px]">
            <div className="rounded-2xl border border-white/10 bg-white/[0.045] px-4 py-3 text-white/82">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="ui-type-meta mb-1 text-white/46">系统上下文</div>
                  <div className="ui-type-body truncate font-medium text-white/88">
                    {advisorSceneContext!.label}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleAdvisorPrompt('deep-dive')}
                  className="ui-type-meta shrink-0 rounded-full border border-white/12 bg-white/8 px-3 py-1.5 text-white/78 transition hover:bg-white/12"
                >
                  继续深挖
                </button>
              </div>
              {advisorInsightLines.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {advisorInsightLines.slice(0, 2).map((line) => (
                    <span
                      key={`advisor-context-${advisorSceneContext!.key}-${line}`}
                      className="ui-type-meta rounded-full bg-black/20 px-3 py-1.5 text-white/58"
                    >
                      {line.replace(/^\d+[.、]\s*/, '')}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
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
        activeExpertPerspective={activeExpertPerspective}
        expertPerspectiveOptions={expertPerspectiveOptions}
        onExpertPerspectiveChange={onExpertPerspectiveChange}
        summonOptions={summonOptions}
        onSummonExpert={onSummonExpert}
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
