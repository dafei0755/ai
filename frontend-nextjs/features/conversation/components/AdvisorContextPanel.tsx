'use client';

import { ChevronDown } from 'lucide-react';

import type { AdvisorSceneContext } from '@/features/conversation/types';

interface AdvisorContextPanelProps {
  advisorSceneContext: AdvisorSceneContext;
  advisorInsightLines: string[];
  contextExpanded: boolean;
  contextPinnedOpen: boolean;
  contextPanePercent: number;
  onExpand: () => void;
  onCollapseAfterHover: () => void;
  onTogglePinnedOpen: () => void;
  onStartResize: () => void;
}

const formatAdvisorInsightLine = (line: string) => line.replace(/^\d+[.、]\s*/, '');

export function AdvisorContextPanel({
  advisorSceneContext,
  advisorInsightLines,
  contextExpanded,
  contextPinnedOpen,
  contextPanePercent,
  onExpand,
  onCollapseAfterHover,
  onTogglePinnedOpen,
  onStartResize,
}: AdvisorContextPanelProps) {
  return (
    <>
      <div
        className="flex-shrink-0 border-b border-[var(--border-color)] px-4 pb-3 pt-1 overflow-y-auto"
        style={{ height: `${contextPanePercent}%` }}
      >
        <div className="mx-auto max-w-[960px]">
          <div
            className="rounded-none border border-[var(--border-color)] bg-[var(--card-bg)] px-4 py-3"
            onMouseEnter={onExpand}
            onMouseLeave={onCollapseAfterHover}
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
                onClick={onTogglePinnedOpen}
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
                    {formatAdvisorInsightLine(line)}
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
          onStartResize();
        }}
        className="group flex h-5 flex-shrink-0 cursor-row-resize items-center justify-center border-t border-[var(--border-color)] bg-transparent transition"
        aria-label="拖动调整上下文和聊天窗口高度"
        title="拖动调整高度"
      >
        <span className="h-1 w-12 rounded-full bg-slate-300" />
      </button>
    </>
  );
}
