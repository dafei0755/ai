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

import { ArrowUp, Plus } from 'lucide-react';
import React, { useEffect, useRef, useState } from 'react';
import { AdvisorContextPanel } from '@/features/conversation/components/AdvisorContextPanel';
import { MessageCardRenderer } from '@/features/conversation/components/MessageCardRenderer';
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

// ── 打字指示器 ────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="mb-6 flex items-center gap-1.5">
      <span className="w-2 h-2 rounded-full bg-[var(--foreground-secondary)] animate-bounce [animation-delay:-0.3s]" />
      <span className="w-2 h-2 rounded-full bg-[var(--foreground-secondary)] animate-bounce [animation-delay:-0.15s]" />
      <span className="w-2 h-2 rounded-full bg-[var(--foreground-secondary)] animate-bounce" />
    </div>
  );
}

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
  const [showSummonMenu, setShowSummonMenu] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const splitPaneRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const summonMenuRef = useRef<HTMLDivElement>(null);
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
    if (!showSummonMenu) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (!summonMenuRef.current) return;
      if (!summonMenuRef.current.contains(event.target as Node)) {
        setShowSummonMenu(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowSummonMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [showSummonMenu]);

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
      {/* 消息列表（底部留空间给浮动输入栏） */}
      <div ref={scrollRef} className="min-h-[140px] flex-1 overflow-y-auto" style={{ paddingInline: adaptiveChatGutter }}>
        {visibleMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center select-none">
            <div className="text-4xl mb-3">💬</div>
            <p className="ui-type-subtitle font-medium text-[var(--foreground)]">随时开始聊</p>
            <p className="ui-type-meta mt-1 text-[var(--foreground-secondary)]">分享你的想法、灵感或设计需求</p>
          </div>
        ) : (
          <div className="w-full max-w-[960px] mx-auto pt-4 pb-60" style={{ paddingInline: '2px' }}>
      {visibleMessages.map((msg) => (
              <MessageCardRenderer key={msg.id} message={msg} onCardResponse={onCardResponse} onCandidateCardResponse={onCandidateCardResponse} />
            ))}
            {loading && <TypingIndicator />}
          </div>
        )}
      </div>
      </div>

      {/* 浮动输入框（ChatGPT 暗色风格） */}
      <div className="absolute bottom-0 left-0 right-0 pb-4 pt-8 bg-gradient-to-t from-[var(--background)] via-[var(--background)] to-transparent pointer-events-none" style={{ paddingInline: adaptiveChatGutter }}>
      <div className="mx-auto w-full max-w-[960px] pointer-events-auto">
          <div className="mb-2 flex items-center rounded-[1rem] border border-white/10 bg-black/35 px-3 py-2 text-xs text-white/88 backdrop-blur-sm">
            <div className="inline-flex items-center gap-2">
              <select
                value={activeExpertPerspective}
                onChange={(event) => onExpertPerspectiveChange?.(event.target.value)}
                className="ui-type-meta min-w-[132px] rounded-full border border-white/10 bg-black/45 px-2.5 py-1 text-white outline-none"
                aria-label="选择专家视角"
              >
                {expertPerspectiveOptions.map((option) => (
                  <option key={option} value={option} className="bg-[#1f1f1f] text-white">
                    {option}
                  </option>
                ))}
              </select>
              <div ref={summonMenuRef} className="relative">
                <button
                  type="button"
                  onClick={() => setShowSummonMenu((prev) => !prev)}
                  className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-white/10 bg-black/45 text-white transition hover:border-white/10 hover:bg-black/45"
                  aria-label="召集团队"
                  title="召集团队"
                >
                  <Plus className="h-3.5 w-3.5" />
                </button>
                {showSummonMenu && (
                  <div className="absolute left-0 bottom-[calc(100%+8px)] min-w-[150px] rounded-2xl border border-white/10 bg-[#1f1f1f]/98 p-1.5 shadow-[0_18px_38px_rgba(0,0,0,0.36)] backdrop-blur-sm">
                    {summonOptions.map((option) => (
                      <button
                        key={option}
                        type="button"
                        onClick={() => {
                          onSummonExpert?.(option);
                          setShowSummonMenu(false);
                        }}
                        className="ui-type-meta flex w-full items-center justify-start rounded-xl px-2.5 py-2 text-white/92 transition hover:bg-white/8"
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
          <div className="ui-card-shell ui-card-shell-strong rounded-[1.6rem] overflow-hidden bg-[var(--card-bg)]">
            <textarea
              ref={textareaRef}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              rows={2}
              className="ui-type-body w-full bg-transparent text-[var(--foreground)] px-5 pt-4 pb-2 outline-none resize-none max-h-32 overflow-y-auto placeholder:text-[var(--foreground-secondary)]"
              style={{ fieldSizing: 'content' } as React.CSSProperties}
            />
            <div className="flex items-center justify-end px-4 pb-3">
              <button
                onClick={handleSend}
                disabled={!inputText.trim() || loading}
                className={`p-2 rounded-full transition-all duration-300 ${
                  inputText.trim() && !loading
                    ? 'bg-[var(--foreground)] text-[var(--background)] hover:opacity-80 hover:scale-105'
                    : 'bg-[var(--border-color)] text-[var(--foreground-secondary)] cursor-not-allowed opacity-50'
                }`}
                aria-label="发送"
              >
                <ArrowUp className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
