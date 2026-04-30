/**
 * GuidanceCard.tsx — 实时引导卡片组件（多页版）
 * Created by GitHub Copilot · 2026-03-16
 * Updated by GitHub Copilot · 2026-03-20 — 多页翻页 + 卡片标题 + 单选 + 描述始终可见
 *
 * 四种卡片类型（mirror / fork / gap / hypothesis）的统一渲染器。
 * - 支持多页（pages 字段）：Header 显示 "X of Y" + ❮ ❯ 导航
 * - 每个选项始终展示 description 在 label 下方
 * - 操作后本地锁定（responded=true），不可重复提交
 */

'use client';

import React, { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { type GuidanceCardData, type GuidanceCardPage } from './ConversationChat';

// ── 卡片类型元信息 ────────────────────────────────────────

const CARD_META: Record<
  GuidanceCardData['card_type'],
  { label: string; color: string; borderColor: string; badgeBg: string; accentBorder: string }
> = {
  mirror: {
    label: '归纳确认',
    color: 'text-blue-700',
    borderColor: 'border-blue-200',
    badgeBg: 'bg-blue-50 text-blue-600',
    accentBorder: 'border-blue-400',
  },
  fork: {
    label: '方向选择',
    color: 'text-violet-700',
    borderColor: 'border-violet-200',
    badgeBg: 'bg-violet-50 text-violet-600',
    accentBorder: 'border-violet-400',
  },
  gap: {
    label: '信息补全',
    color: 'text-amber-700',
    borderColor: 'border-amber-200',
    badgeBg: 'bg-amber-50 text-amber-600',
    accentBorder: 'border-amber-400',
  },
  hypothesis: {
    label: '设想确认',
    color: 'text-emerald-700',
    borderColor: 'border-emerald-200',
    badgeBg: 'bg-emerald-50 text-emerald-600',
    accentBorder: 'border-emerald-400',
  },
  candidate: {
    label: '候选方案',
    color: 'text-cyan-700',
    borderColor: 'border-cyan-200',
    badgeBg: 'bg-cyan-50 text-cyan-600',
    accentBorder: 'border-cyan-400',
  },
};

// ── 内部类型 ──────────────────────────────────────────────

interface PageSelection {
  optionId?: string;
  freetext?: string;
}

// ── Props ────────────────────────────────────────────────

interface GuidanceCardWidgetProps {
  card: GuidanceCardData;
  /**
   * 初始状态已响应（历史消息中的卡片展示用）
   */
  initialResponded?: boolean;
  /**
   * 已确认时的选择摘要文本，用于留痕显示。
   * 不传时从 selections state 中自动推算（仅当前会话有效）。
   */
  respondedSummary?: string;
  /**
   * 用户操作回调。
   * @param optionId  选择的选项 ID；undefined 表示跳过或纯文本输入
   * @param freetext  自由输入内容（多页时为分号拼接的汇总）
   */
  onRespond: (optionId?: string, freetext?: string) => void;
}

// ── 组件 ─────────────────────────────────────────────────

export default function GuidanceCardWidget({ card, initialResponded = false, respondedSummary, onRespond }: GuidanceCardWidgetProps) {
  // 将单页/多页统一为 allPages
  const allPages: GuidanceCardPage[] =
    card.pages && card.pages.length > 0
      ? card.pages
      : [
          {
            page_title: '',
            prompt_text: card.prompt_text,
            options: card.options,
            allow_freetext: card.allow_freetext,
          },
        ];

  const totalPages = allPages.length;

  const [pageIdx, setPageIdx] = useState(0);
  const [selections, setSelections] = useState<Record<number, PageSelection>>({});
  const [freetextValue, setFreetextValue] = useState('');
  const [responded, setResponded] = useState(initialResponded);

  const meta = CARD_META[card.card_type] ?? CARD_META.mirror;
  const currentPage = allPages[pageIdx];
  const currentSelection = selections[pageIdx];
  const isLastPage = pageIdx === totalPages - 1;

  // 当前页是否可继续（选了选项或填了自由输入）
  const canProceed =
    !!currentSelection?.optionId || !!(freetextValue.trim()) || !!currentSelection?.freetext;

  const handleSelectOption = (optionId: string) => {
    if (responded) return;
    setSelections((prev) => ({ ...prev, [pageIdx]: { optionId } }));
  };

  const handleNext = () => {
    if (responded) return;
    // 保存当前页自由输入（若已有 optionId 则不覆盖 freetext）
    const ft = freetextValue.trim();
    if (ft && !currentSelection?.optionId) {
      setSelections((prev) => ({ ...prev, [pageIdx]: { freetext: ft } }));
    }
    setFreetextValue('');
    setPageIdx((i) => Math.min(i + 1, totalPages - 1));
  };

  const handleSubmit = () => {
    if (responded) return;
    // 先保存最后一页的自由输入
    const ft = freetextValue.trim();
    const finalSelections = { ...selections };
    if (ft && !currentSelection?.optionId) {
      finalSelections[pageIdx] = { freetext: ft };
    }

    // 汇总所有页的信号
    const signals: string[] = allPages.map((page, i) => {
      const sel = finalSelections[i];
      if (!sel) return '';
      if (sel.optionId) {
        const opt = page.options.find((o) => o.id === sel.optionId);
        return opt ? opt.label : sel.optionId;
      }
      return sel.freetext ?? '';
    }).filter(Boolean);

    setResponded(true);

    if (totalPages === 1) {
      // 单页：走原来逻辑
      const sel = finalSelections[0];
      onRespond(sel?.optionId, sel?.freetext);
    } else {
      // 多页：freetext 汇总形式传递
      onRespond(undefined, signals.join('; '));
    }
  };

  const handleSkip = () => {
    if (responded) return;
    setResponded(true);
    onRespond(undefined, undefined);
  };

  const handlePrevPage = () => {
    if (pageIdx > 0) {
      setFreetextValue('');
      setPageIdx((i) => i - 1);
    }
  };

  const handleNextPage = () => {
    handleNext();
  };

  // ── 已响应：脱离卡片，纯文本留痕 ────────────────────────────
  if (responded) {
    // 优先用外部传入的摘要（历史消息），其次从当前会话 selections 推算
    const displayText: string = respondedSummary ?? (() => {
      const labels = allPages.map((page, i) => {
        const sel = selections[i];
        if (!sel) return '';
        if (sel.optionId) {
          const opt = page.options.find((o) => o.id === sel.optionId);
          return opt?.label ?? sel.optionId;
        }
        return sel.freetext ?? '';
      }).filter(Boolean);
      return labels.join(' / ');
    })();

    return (
      <div className="flex items-start gap-2 py-0.5 text-xs text-[var(--foreground-secondary)]">
        <span className={`flex-shrink-0 mt-0.5 ${meta.color}`}>◆</span>
        <span>
          <span className="opacity-60">{meta.label}</span>
          <span className="opacity-40 mx-1.5">·</span>
          {displayText ? (
            <span className="text-[var(--foreground)]">{displayText}</span>
          ) : (
            <span className="opacity-60">已确认</span>
          )}
        </span>
      </div>
    );
  }

  // ── 激活态卡片 ────────────────────────────────────────────
  return (
    <div
      className="ui-card-shell rounded-xl bg-[#252526] text-sm overflow-hidden"
      data-testid="guidance-card"
      data-card-id={card.card_id}
      data-card-type={card.card_type}
    >
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#3a3f4b]">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`flex-shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${meta.badgeBg}`}>
            {meta.label}
          </span>
          {card.title && (
            <span className="text-sm font-semibold text-[var(--foreground)] truncate">{card.title}</span>
          )}
        </div>
        {totalPages > 1 && (
          <div className="flex items-center gap-1 flex-shrink-0 ml-2">
            <button
              onClick={handlePrevPage}
              disabled={pageIdx === 0}
              className="p-0.5 rounded disabled:opacity-30 text-[var(--foreground-secondary)] hover:text-[var(--foreground)] transition-colors"
              aria-label="上一页"
            >
              <ChevronLeft size={14} />
            </button>
            <span className="text-xs text-[var(--foreground-secondary)] select-none px-0.5">
              {pageIdx + 1} of {totalPages}
            </span>
            <button
              onClick={handleNextPage}
              disabled={isLastPage || !canProceed}
              className="p-0.5 rounded disabled:opacity-30 text-[var(--foreground-secondary)] hover:text-[var(--foreground)] transition-colors"
              aria-label="下一页"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        )}
      </div>

      {/* ── 页面内容 ── */}
      <div className="px-4 pt-3 pb-2">
        {currentPage.page_title && (
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--foreground-secondary)] opacity-60 mb-1.5">
            {currentPage.page_title}
          </p>
        )}
        <p className="text-[var(--foreground)] leading-relaxed mb-3">
          {currentPage.prompt_text}
        </p>

        {/* 编号选项列表 */}
        {currentPage.options && currentPage.options.length > 0 && (
          <div className="flex flex-col gap-1">
            {currentPage.options.map((opt, i) => {
              const selected = currentSelection?.optionId === opt.id;
              return (
                <button
                  key={opt.id}
                  onClick={() => handleSelectOption(opt.id)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg flex items-start gap-3 transition-colors border
                    ${selected
                      ? 'bg-[#1f3a5f] border-[#3b6bc7]'
                      : 'border-transparent hover:bg-[#2a2d2e]'
                    }`}
                >
                  <span className={`flex-shrink-0 text-xs w-5 text-right mt-0.5 tabular-nums select-none
                    ${selected ? 'text-[#4fc3f7]' : 'text-[var(--foreground-secondary)]'}`}>
                    {i + 1}.
                  </span>
                  <span className="flex flex-col gap-0.5 min-w-0">
                    <span className={`font-medium leading-snug ${selected ? 'text-white' : 'text-[var(--foreground)]'}`}>
                      {opt.label}
                      {opt.recommended && (
                        <span className="ml-2 text-[10px] font-normal text-[#4fc3f7]">(Recommended)</span>
                      )}
                    </span>
                    {opt.description && (
                      <span className="text-xs text-[var(--foreground-secondary)] leading-relaxed">
                        {opt.description}
                      </span>
                    )}
                    {selected && opt.consequence_hint && (
                      <span className="text-xs opacity-60 italic mt-0.5">{opt.consequence_hint}</span>
                    )}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        {/* 自由输入框 */}
        {currentPage.allow_freetext && (
          <div className="mt-2">
            <input
              type="text"
              value={freetextValue}
              onChange={(e) => setFreetextValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  if (isLastPage) handleSubmit();
                  else handleNext();
                }
              }}
              placeholder="或直接输入你的想法…"
              className="w-full px-3 py-1.5 text-xs border border-[#3a3f4b] rounded-lg bg-[#1e1e1e] text-[var(--foreground)] outline-none focus:border-[#3b6bc7] transition-colors placeholder:text-[var(--foreground-secondary)] placeholder:opacity-50"
            />
          </div>
        )}
      </div>

      {/* ── Footer ── */}
      <div className="flex items-center justify-between px-4 py-2.5 border-t border-[#3a3f4b]">
        <button
          onClick={handleSkip}
          className="text-xs text-[var(--foreground-secondary)] opacity-50 hover:opacity-90 transition-opacity"
        >
          忽略 ESC
        </button>
        {isLastPage ? (
          <button
            onClick={handleSubmit}
            disabled={!canProceed}
            className="px-4 py-1.5 text-xs font-semibold rounded-full bg-[#1a6fcf] text-white hover:bg-[#1660b8] disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
          >
            提交 <span className="opacity-70">↵</span>
          </button>
        ) : (
          <button
            onClick={handleNext}
            disabled={!canProceed}
            className="px-4 py-1.5 text-xs font-semibold rounded-full bg-[#1a6fcf] text-white hover:bg-[#1660b8] disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
          >
            下一步 <ChevronRight size={12} />
          </button>
        )}
      </div>
    </div>
  );
}
