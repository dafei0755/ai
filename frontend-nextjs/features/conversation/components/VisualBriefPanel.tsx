'use client';

import { ChevronDown } from 'lucide-react';

import type { ConversationChatProps } from '@/features/conversation/types';

type VisualBriefContext = NonNullable<ConversationChatProps['visualBriefContext']>;

interface VisualBriefPanelProps {
  visualBriefContext: VisualBriefContext;
  expanded: boolean;
  pinnedOpen: boolean;
  onExpand: () => void;
  onCollapseAfterHover: () => void;
  onTogglePinnedOpen: () => void;
  onVisualBriefPromptChange?: (prompt: string) => void;
  onVisualBriefNoteChange?: (note: string) => void;
}

const getVisualBriefStatusLabel = (status: string) => {
  if (status === 'auto') return '系统自动';
  if (status === 'locked') return '已锁定';
  if (status === 'stale') return '待同步';
  return '用户已修改';
};

export function VisualBriefPanel({
  visualBriefContext,
  expanded,
  pinnedOpen,
  onExpand,
  onCollapseAfterHover,
  onTogglePinnedOpen,
  onVisualBriefPromptChange,
  onVisualBriefNoteChange,
}: VisualBriefPanelProps) {
  return (
    <div className="flex-shrink-0 border-b border-[var(--border-color)] px-4 pb-3 pt-1">
      <div className="advisor-chat-column mx-auto">
        <div
          className="rounded-none border border-[var(--border-color)] bg-[var(--card-bg)] px-4 py-3"
          onMouseEnter={onExpand}
          onMouseLeave={onCollapseAfterHover}
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="ui-type-meta font-semibold text-[#1fa2df]">
                  空间 VisualBrief · {visualBriefContext.space}
                </span>
                <span className="ui-type-meta rounded-full border border-[var(--border-color)] px-2.5 py-1 text-[var(--foreground-secondary)]">
                  {getVisualBriefStatusLabel(visualBriefContext.status)}
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
              onClick={onTogglePinnedOpen}
              className="shrink-0 inline-flex h-8 w-8 items-center justify-center rounded-full border border-[var(--border-color)] text-[var(--foreground-secondary)] transition hover:text-[var(--foreground)]"
              aria-label={pinnedOpen ? '手动折叠 VisualBrief' : '固定展开 VisualBrief'}
              title={pinnedOpen ? '手动折叠' : expanded ? '固定展开' : '查看详情'}
            >
              <ChevronDown className={`h-4 w-4 transition-transform ${expanded ? 'rotate-180' : ''}`} />
            </button>
          </div>

          {!expanded && (
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

          {expanded && (
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
  );
}
