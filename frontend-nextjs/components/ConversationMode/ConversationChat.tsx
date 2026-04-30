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

import { ArrowUp, ChevronDown, Plus } from 'lucide-react';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import GuidanceCardWidget from './GuidanceCard';
import CandidateCard, { type CandidateCardData, type CandidateCardResponse } from './CandidateCard';

// ── 类型定义 ────────────────────────────────────

export type MessageRole = 'user' | 'assistant' | 'system';

/** 引导卡片选项 */
export interface GuidanceCardOptionData {
  id: string;
  label: string;
  description: string;
  consequence_hint?: string;
  recommended?: boolean;
}

/** 引导卡片单页（多页模式）*/
export interface GuidanceCardPage {
  page_title?: string;
  prompt_text: string;
  options: GuidanceCardOptionData[];
  allow_freetext?: boolean;
}

/** 引导卡片数据（与后端 GuidanceCard 对应） */
export interface GuidanceCardData {
  card_id: string;
  card_type: 'mirror' | 'fork' | 'gap' | 'hypothesis' | 'candidate';
  /** 卡片总标题，显示在 Header */
  title?: string;
  prompt_text: string;
  options: GuidanceCardOptionData[];
  allow_freetext?: boolean;
  /** 多页模式：非空时以 pages 为准 */
  pages?: GuidanceCardPage[];
  source_turns?: string[];
  // 候选卡扩展字段（card_type="candidate" 时生效）
  candidate_fields?: CandidateCardData['candidate_fields'];
  card_status?: CandidateCardData['card_status'];
  gap_round?: boolean;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  /** 是否含有草稿对象（如 IntentSeed）*/
  has_draft?: boolean;
  draft_type?: string;
  /** 引导卡片（None 表示本条无卡） */
  guidance_card?: GuidanceCardData;
  /** 该条消息的微卧希拟卡片是否已经被操作 */
  card_responded?: boolean;
  /** 用户选择结果摘要（用于确认后留痕显示） */
  card_selection_label?: string;
}

export interface AdvisorSceneContext {
  key: string;
  label: string;
  suggestion: string;
  sceneRef: string;
}

export interface ConversationChatProps {
  sessionId: string;
  messages: ChatMessage[];
  activeExpertPerspective?: string;
  expertPerspectiveOptions?: readonly string[];
  onExpertPerspectiveChange?: (next: string) => void;
  summonOptions?: readonly string[];
  onSummonExpert?: (target: string) => void;
  visualBriefContext?: {
    space: string;
    status: string;
    summary: string;
    visualPrompt: string;
    appliedTags: string[];
    lockedTags: string[];
    negativeConstraints: string[];
    customNote?: string;
    sourceTitles: string[];
  } | null;
  onVisualBriefPromptChange?: (prompt: string) => void;
  onVisualBriefNoteChange?: (note: string) => void;
  advisorSceneContext?: AdvisorSceneContext | null;
  /** 发送新消息的回调 */
  onSendMessage: (text: string) => void;
  /** 是否正在等待 AI 响应 */
  loading?: boolean;
  /** 输入框占位文本 */
  placeholder?: string;
  /** 是否显示升级提示横幅 */
  showUpgradeBanner?: boolean;
  /** 升级横幅「确认升级」回调 */
  onUpgradeConfirm?: () => void;
  /** 升级横幅「暂不升级」回调 */
  onUpgradeDismiss?: () => void;
  /**
   * 用户对引导卡片的操作回调。
   * @param cardId 卡片 ID
   * @param optionId 选择的选项 ID（跳过时为 undefined）
   * @param freetext 用户自由输入内容
   */
  onCardResponse?: (cardId: string, optionId?: string, freetext?: string) => void;
  /**
   * 候选卡（candidate 类型）操作回调。
   * @param response CandidateCardResponse 对象
   */
  onCandidateCardResponse?: (response: CandidateCardResponse) => void;
  /** 外部预填充输入提示（如 @引用），id 变化时追加一次 */
  prefillHint?: { id: number; text: string } | null;
  className?: string;
}

// ── 子组件：单条消息气泡 ────────────────────────────────────

function MessageBubble({
  message,
  onCardResponse,
  onCandidateCardResponse,
}: {
  message: ChatMessage;
  onCardResponse?: (cardId: string, optionId?: string, freetext?: string) => void;
  onCandidateCardResponse?: (response: CandidateCardResponse) => void;
}) {
  const isUser = message.role === 'user';

  // ── 用户消息：右对齐圆角底纹气泡，无头像 ──
  if (isUser) {
    return (
      <div className="flex justify-end mb-5" data-testid="message-bubble">
        <div className="ui-type-body max-w-[min(78%,54rem)] px-5 py-3.5 rounded-[1.5rem] bg-[var(--card-bg)] text-[var(--foreground)]">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  const gc = message.guidance_card;
  const isCandidateCard = gc?.card_type === 'candidate';

  // ── AI 消息：纯文本，无气泡，无头像 ──
  return (
    <div className="mb-6" data-testid="message-bubble">
      {/* 正文 — markdown 渲染 */}
      <div className="ui-type-body text-[var(--foreground)] prose-conv">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => <h1 className="ui-type-title font-bold mt-5 mb-2 first:mt-0">{children}</h1>,
            h2: ({ children }) => <h2 className="ui-type-subtitle font-bold mt-5 mb-2 first:mt-0">{children}</h2>,
            h3: ({ children }) => <h3 className="ui-type-subtitle font-semibold mt-4 mb-2 first:mt-0">{children}</h3>,
            strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
            p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
            br: () => <br />,
            ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1.5">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1.5">{children}</ol>,
            li: ({ children }) => <li>{children}</li>,
            hr: () => <hr className="my-3 border-[var(--border-color)]" />,
            code: ({ children }) => <code className="px-1.5 py-0.5 rounded bg-[var(--border-color)] text-[0.85em] font-mono">{children}</code>,
          }}
        >
          {message.content}
        </ReactMarkdown>
      </div>

      {/* 已确认草稿/阶段成果强调卡 */}
      {message.has_draft && message.draft_type && (
        <div className="ui-type-meta mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border-l-2 border-indigo-400 bg-indigo-500/10 text-indigo-400">
          <span>📎</span>
          <span>已记录 · <span className="font-medium">{message.draft_type}</span></span>
        </div>
      )}

      {/* 候选卡（高参协作协议 L2 层）— 未响应时可交互 */}
      {gc && isCandidateCard && !message.card_responded && onCandidateCardResponse && gc.candidate_fields && (
        <div className="mt-4 max-w-[88%]">
          <CandidateCard
            card={{
              card_id: gc.card_id,
              card_type: (gc.card_type === 'candidate'
                ? (gc.gap_round ? 'gap' : 'echo')
                : 'echo') as 'echo' | 'gap',
              title: gc.title ?? gc.prompt_text,
              summary: gc.prompt_text,
              candidate_fields: gc.candidate_fields,
              card_status: gc.card_status ?? 'candidate',
              gap_round: gc.gap_round,
            }}
            onRespond={onCandidateCardResponse}
          />
        </div>
      )}

      {/* 候选卡留痕 — 已响应后 */}
      {gc && isCandidateCard && message.card_responded && gc.candidate_fields && (
        <div className="mt-4 max-w-[88%]">
          <CandidateCard
            card={{
              card_id: gc.card_id,
              card_type: (gc.gap_round ? 'gap' : 'echo') as 'echo' | 'gap',
              title: gc.title ?? gc.prompt_text,
              summary: gc.prompt_text,
              candidate_fields: gc.candidate_fields,
              card_status: gc.card_status ?? 'confirmed',
              gap_round: gc.gap_round,
            }}
            initialResponded
            respondedSummary={message.card_selection_label}
            onRespond={() => {}}
          />
        </div>
      )}

      {/* 普通引导卡片（mirror/fork/gap/hypothesis）— 未响应时可交互 */}
      {gc && !isCandidateCard && !message.card_responded && onCardResponse && (
        <div className="mt-4 max-w-[88%]">
          <GuidanceCardWidget
            card={gc}
            onRespond={(optionId, freetext) =>
              onCardResponse(gc.card_id, optionId, freetext)
            }
          />
        </div>
      )}

      {/* 普通引导卡片留痕 — 已响应后的卡片历史 */}
      {gc && !isCandidateCard && message.card_responded && (
        <div className="mt-4 max-w-[88%]">
          <GuidanceCardWidget
            card={gc}
            initialResponded
            respondedSummary={message.card_selection_label}
            onRespond={() => {}}
          />
        </div>
      )}
    </div>
  );
}

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
  const [inputText, setInputText] = useState('');
  const [briefExpanded, setBriefExpanded] = useState(false);
  const [briefPinnedOpen, setBriefPinnedOpen] = useState(false);
  const [contextExpanded, setContextExpanded] = useState(false);
  const [contextPinnedOpen, setContextPinnedOpen] = useState(false);
  const [showSummonMenu, setShowSummonMenu] = useState(false);
  const [contextPanePercent, setContextPanePercent] = useState(() => {
    // 从 sessionStorage 中恢复上次保存的比例（页面会话级别）
    if (typeof window === 'undefined') return 42;
    try {
      const stored = sessionStorage.getItem(`context_pane_percent_${sessionId}`);
      return stored ? Math.min(72, Math.max(24, parseInt(stored, 10))) : 42;
    } catch {
      return 42;
    }
  });
  const [isContextResizing, setIsContextResizing] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const splitPaneRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const summonMenuRef = useRef<HTMLDivElement>(null);
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

  // 接收外部引用注入（如 @用户需求）
  useEffect(() => {
    if (!prefillHint?.text) return;
    setInputText((prev) => {
      if (prev.includes(prefillHint.text)) return prev;
      return `${prev} ${prefillHint.text}`.trim();
    });
    textareaRef.current?.focus();
  }, [prefillHint?.id, prefillHint?.text]);

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
      const pane = splitPaneRef.current;
      if (!pane) return;
      const rect = pane.getBoundingClientRect();
      const nextPercent = ((event.clientY - rect.top) / rect.height) * 100;
      const validPercent = Math.min(72, Math.max(24, nextPercent));
      setContextPanePercent(validPercent);
    };

    const handleMouseUp = () => {
      setIsContextResizing(false);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      // 保存拖动后的比例
      try {
        sessionStorage.setItem(`context_pane_percent_${sessionId}`, String(Math.round(contextPanePercent)));
      } catch (e) {
        console.warn('Failed to save context pane percent:', e);
      }
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
  }, [isContextResizing, sessionId, contextPanePercent]);

  const handleSend = useCallback(() => {
    const trimmed = inputText.trim();
    if (!trimmed || loading) return;
    onSendMessage(trimmed);
    setInputText('');
    textareaRef.current?.focus();
  }, [inputText, loading, onSendMessage]);

  const useAdvisorPrompt = useCallback(
    (intent: 'deep-dive' | 'action-list') => {
      if (!advisorSceneContext) return;
      const prompt =
        intent === 'deep-dive'
          ? `@${advisorSceneContext.sceneRef}\n请基于左侧当前场景继续深挖：先指出关键矛盾，再给出风险判断、设计取舍和可验证的下一步。`
          : `@${advisorSceneContext.sceneRef}\n请把左侧当前场景转成行动清单：按优先级列出今天能推进的判断、资料缺口、方案动作和验证方式。`;
      setInputText(prompt);
      textareaRef.current?.focus();
    },
    [advisorSceneContext]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

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
        <div className="flex-shrink-0 border-b border-[var(--border-color)] px-4 pb-3 pt-1">
          <div className="mx-auto max-w-[1260px] xl:max-w-none">
            <div
              className="rounded-none border border-[var(--border-color)] bg-[var(--card-bg)] px-4 py-3"
              onMouseEnter={() => setBriefExpanded(true)}
              onMouseLeave={() => {
                if (!briefPinnedOpen) setBriefExpanded(false);
              }}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="ui-type-meta font-semibold text-[#1fa2df]">
                      空间 VisualBrief · {visualBriefContext.space}
                    </span>
                    <span className="ui-type-meta rounded-full border border-[var(--border-color)] px-2.5 py-1 text-[var(--foreground-secondary)]">
                      {visualBriefContext.status === 'auto'
                        ? '系统自动'
                        : visualBriefContext.status === 'locked'
                          ? '已锁定'
                          : visualBriefContext.status === 'stale'
                            ? '待同步'
                            : '用户已修改'}
                    </span>
                  </div>
                  <div className="ui-type-meta mt-1 line-clamp-1 text-[var(--foreground-secondary)]">
                    {visualBriefContext.summary}
                  </div>
                  <div className="ui-type-meta mt-1 line-clamp-2 text-[var(--foreground-secondary)]">
                    {visualBriefContext.visualPrompt}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setBriefPinnedOpen((prev) => {
                      const nextPinned = !prev;
                      setBriefExpanded(nextPinned);
                      return nextPinned;
                    });
                  }}
                  className="shrink-0 inline-flex h-8 w-8 items-center justify-center rounded-full border border-[var(--border-color)] text-[var(--foreground-secondary)] transition hover:text-[var(--foreground)]"
                  aria-label={briefPinnedOpen ? '手动折叠 VisualBrief' : '固定展开 VisualBrief'}
                  title={briefPinnedOpen ? '手动折叠' : briefExpanded ? '固定展开' : '查看详情'}
                >
                  <ChevronDown className={`h-4 w-4 transition-transform ${briefExpanded ? 'rotate-180' : ''}`} />
                </button>
              </div>

              {!briefExpanded && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {visualBriefContext.appliedTags.slice(0, 8).map((tag) => (
                    <span key={`chat-brief-tag-${tag}`} className="ui-type-meta rounded-full bg-[var(--background)] px-2.5 py-1 text-[var(--foreground-secondary)]">
                      {tag}
                    </span>
                  ))}
                  {visualBriefContext.lockedTags.slice(0, 3).map((tag) => (
                    <span key={`chat-brief-locked-${tag}`} className="ui-type-meta rounded-full bg-emerald-500/10 px-2.5 py-1 text-emerald-400">
                      锁 {tag}
                    </span>
                  ))}
                </div>
              )}

              {briefExpanded && (
                <div
                  className="mt-3 flex flex-col gap-3 overflow-hidden border-t border-[var(--border-color)] pt-3"
                  style={{ height: '50vh', maxHeight: '50vh' }}
                >
                  <label className="block">
                    <div className="ui-type-meta mb-2 text-[var(--foreground-secondary)]">生图基线提示词</div>
                    <textarea
                      value={visualBriefContext.visualPrompt}
                      onChange={(event) => onVisualBriefPromptChange?.(event.target.value)}
                      className="ui-type-meta h-[34vh] min-h-[260px] w-full resize-none rounded-none border border-[var(--border-color)] bg-[var(--background)] px-3 py-2 leading-6 text-[var(--foreground)] outline-none focus:border-[var(--foreground-secondary)]"
                    />
                  </label>
                  <label className="block">
                    <div className="ui-type-meta mb-2 text-[var(--foreground-secondary)]">本轮补充备注</div>
                    <textarea
                      value={visualBriefContext.customNote ?? ''}
                      onChange={(event) => onVisualBriefNoteChange?.(event.target.value)}
                      rows={3}
                      placeholder="例如：本轮更强调黄昏抵达感，降低社交密度。"
                      className="ui-type-meta w-full rounded-none border border-[var(--border-color)] bg-[var(--background)] px-3 py-2 leading-6 text-[var(--foreground)] outline-none placeholder:text-[var(--foreground-secondary)] focus:border-[var(--foreground-secondary)]"
                    />
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {visualBriefContext.sourceTitles.slice(0, 5).map((title) => (
                      <span key={`chat-brief-source-${title}`} className="ui-type-meta rounded-full bg-[var(--background)] px-2.5 py-1 text-[var(--foreground-secondary)]">
                        来源：{title}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {false && advisorSceneContext && visibleMessages.length > 0 && (
        <div className="flex-shrink-0 border-b border-white/8 px-4 py-3">
          <div className="mx-auto max-w-[1260px] xl:max-w-none">
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
                  onClick={() => useAdvisorPrompt('deep-dive')}
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
      {/* 上下文窗口（基于当前页面动态，样式与 VisualBrief 一致） */}
      {advisorSceneContext && (
        <>
          <div
            className="flex-shrink-0 border-b border-[var(--border-color)] px-4 pb-3 pt-1 overflow-y-auto"
            style={{ height: `${contextPanePercent}%` }}
          >
            <div className="mx-auto max-w-[1260px] xl:max-w-none">
              <div
                className="rounded-none border border-[var(--border-color)] bg-[var(--card-bg)] px-4 py-3"
                onMouseEnter={() => setContextExpanded(true)}
                onMouseLeave={() => {
                  if (!contextPinnedOpen) setContextExpanded(false);
                }}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="ui-type-meta font-semibold text-[#1fa2df]">
                        {advisorSceneContext.label}
                      </span>
                    </div>
                    <div className="ui-type-meta mt-1 line-clamp-2 text-[var(--foreground-secondary)]">
                      {advisorSceneContext.suggestion}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setContextPinnedOpen((prev) => {
                        const nextPinned = !prev;
                        setContextExpanded(nextPinned);
                        return nextPinned;
                      });
                    }}
                    className="shrink-0 inline-flex h-8 w-8 items-center justify-center rounded-full border border-[var(--border-color)] text-[var(--foreground-secondary)] transition hover:text-[var(--foreground)]"
                    aria-label={contextPinnedOpen ? '手动折叠上下文' : '固定展开上下文'}
                    title={contextPinnedOpen ? '手动折叠' : contextExpanded ? '固定展开' : '查看详情'}
                  >
                    <ChevronDown className={`h-4 w-4 transition-transform ${contextExpanded ? 'rotate-180' : ''}`} />
                  </button>
                </div>

                {!contextExpanded && advisorInsightLines.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {advisorInsightLines.slice(0, 5).map((line) => (
                      <span
                        key={`advisor-context-${advisorSceneContext.key}-${line}`}
                        className="ui-type-meta rounded-full bg-[var(--background)] px-2.5 py-1 text-[var(--foreground-secondary)]"
                      >
                        {line.replace(/^\d+[.、]\s*/, '')}
                      </span>
                    ))}
                  </div>
                )}

                {contextExpanded && advisorInsightLines.length > 0 && (
                  <div className="mt-3 flex flex-col gap-2 border-t border-[var(--border-color)] pt-3">
                    {advisorInsightLines.map((line) => (
                      <div
                        key={`advisor-expanded-${advisorSceneContext.key}-${line}`}
                        className="ui-type-meta text-[var(--foreground-secondary)] leading-6"
                      >
                        {line}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
          <button
            type="button"
            onMouseDown={(event) => {
              event.preventDefault();
              setIsContextResizing(true);
            }}
            className="group flex h-5 flex-shrink-0 cursor-row-resize items-center justify-center border-t border-[var(--border-color)] bg-transparent transition"
            aria-label="拖动调整上下文和聊天窗口高度"
            title="拖动调整高度"
          >
            <span className="h-1 w-12 rounded-full bg-slate-300" />
          </button>
        </>
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
          <div className="w-full max-w-[1260px] xl:max-w-none mx-auto py-4" style={{ paddingInline: '2px' }}>
            {visibleMessages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} onCardResponse={onCardResponse} onCandidateCardResponse={onCandidateCardResponse} />
            ))}
            {loading && <TypingIndicator />}
          </div>
        )}
      </div>
      </div>

      {/* 浮动输入框（ChatGPT 暗色风格） */}
      <div className="absolute bottom-0 left-0 right-0 pb-4 pt-8 bg-gradient-to-t from-[var(--background)] via-[var(--background)] to-transparent pointer-events-none" style={{ paddingInline: adaptiveChatGutter }}>
      <div className="mx-auto pointer-events-auto max-w-[1260px] xl:max-w-none" style={{ width: 'calc(100% + 4px)', marginLeft: '-2px' }}>
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
