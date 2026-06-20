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
import { Check, ChevronLeft, ChevronRight } from 'lucide-react';
import { type GuidanceCardData, type GuidanceCardPage, type GuidanceCardStructuredResponse } from '@/features/conversation/types';

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
  demand_reconstruction_blueprint: {
    label: '需求重构',
    color: 'text-emerald-700',
    borderColor: 'border-emerald-200',
    badgeBg: 'bg-emerald-50 text-emerald-600',
    accentBorder: 'border-emerald-400',
  },
  scheme_round_1: {
    label: '关键确认',
    color: 'text-cyan-700',
    borderColor: 'border-cyan-200',
    badgeBg: 'bg-cyan-50 text-cyan-600',
    accentBorder: 'border-cyan-400',
  },
  scheme_round_2: {
    label: '决策确认',
    color: 'text-violet-700',
    borderColor: 'border-violet-200',
    badgeBg: 'bg-violet-50 text-violet-600',
    accentBorder: 'border-violet-400',
  },
  scheme_stage_conclusion: {
    label: '阶段结论',
    color: 'text-emerald-700',
    borderColor: 'border-emerald-200',
    badgeBg: 'bg-emerald-50 text-emerald-600',
    accentBorder: 'border-emerald-400',
  },
  scheme_version_selection: {
    label: '版本选择',
    color: 'text-cyan-700',
    borderColor: 'border-cyan-200',
    badgeBg: 'bg-cyan-50 text-cyan-600',
    accentBorder: 'border-cyan-400',
  },
};

// ── 内部类型 ──────────────────────────────────────────────

interface PageSelection {
  optionId?: string;
  optionIds?: string[];
  freetext?: string;
}

const MISSING_SLOT_ACTION_META: Record<string, { label: string; className: string }> = {
  certainty_ceiling: {
    label: '现实边界缺口',
    className: 'border-amber-400/40 bg-amber-400/10 text-amber-200',
  },
  branch_answer_plus_followup: {
    label: '经营事实缺口',
    className: 'border-cyan-400/40 bg-cyan-400/10 text-cyan-100',
  },
  option_menu: {
    label: '路径选择',
    className: 'border-violet-400/40 bg-violet-400/10 text-violet-100',
  },
};

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
   * @param structuredResponse 多页/多选/排序场景的结构化选择结果
   */
  onRespond: (optionId?: string, freetext?: string, structuredResponse?: GuidanceCardStructuredResponse) => void;
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
  const [historyExpanded, setHistoryExpanded] = useState(false);

  const meta = CARD_META[card.card_type] ?? CARD_META.mirror;
  const currentPage = allPages[pageIdx];
  const currentSelection = selections[pageIdx];
  const responseMode = currentPage.response_mode ?? 'single_select';
  const isMultiMode = responseMode === 'multi_select' || responseMode === 'priority_pick';
  const maxSelect = currentPage.max_select ?? (responseMode === 'priority_pick' ? 3 : undefined);
  const isLastPage = pageIdx === totalPages - 1;
  const isSchemeInquiry = card.card_type === 'scheme_round_1' || card.card_type === 'scheme_round_2';
  const currentQuestionTitle = currentPage.page_title || `问题 ${pageIdx + 1}`;
  const nextQuestionTitle = allPages[pageIdx + 1]?.page_title || `问题 ${pageIdx + 2}`;
  const missingSlotMeta =
    currentPage.source === 'context_packet.missing_slots' && currentPage.missing_slot_action
      ? MISSING_SLOT_ACTION_META[currentPage.missing_slot_action]
      : undefined;
  const submitLabel =
    card.card_type === 'demand_reconstruction_blueprint'
      ? '确认方向'
      : card.card_type === 'scheme_round_1'
      ? '提交首轮判断'
      : card.card_type === 'scheme_round_2'
        ? '提交决策判断'
        : '提交';
  const demandReconstructionSections = card.card_type === 'demand_reconstruction_blueprint' ? (card.sections ?? []) : [];

  // 当前页是否可继续（选了选项或填了自由输入）
  const canProceed =
    !!currentSelection?.optionId ||
    !!currentSelection?.optionIds?.length ||
    !!(freetextValue.trim()) ||
    !!currentSelection?.freetext;

  const handleSelectOption = (optionId: string) => {
    if (responded) return;
    if (isMultiMode) {
      setSelections((prev) => {
        const existing = prev[pageIdx]?.optionIds ?? [];
        const selected = existing.includes(optionId);
        const nextIds = selected
          ? existing.filter((id) => id !== optionId)
          : maxSelect && existing.length >= maxSelect
            ? [...existing.slice(0, maxSelect - 1), optionId]
            : [...existing, optionId];
        const next = { ...prev, [pageIdx]: { optionIds: nextIds } };
        if (isSchemeInquiry) {
          Object.keys(next).forEach((key) => {
            if (Number(key) > pageIdx) delete next[Number(key)];
          });
        }
        return next;
      });
      return;
    }
    setSelections((prev) => {
      const next = { ...prev, [pageIdx]: { optionId } };
      if (isSchemeInquiry) {
        Object.keys(next).forEach((key) => {
          if (Number(key) > pageIdx) delete next[Number(key)];
        });
      }
      return next;
    });
  };

  const handleNext = () => {
    if (responded) return;
    // 保存当前页自由输入（若已有 optionId 则不覆盖 freetext）
    const ft = freetextValue.trim();
    if (ft && !currentSelection?.optionId && !currentSelection?.optionIds?.length) {
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
    if (ft && !currentSelection?.optionId && !currentSelection?.optionIds?.length) {
      finalSelections[pageIdx] = { freetext: ft };
    }

    const structuredResponse: GuidanceCardStructuredResponse = {
      pages: allPages.map((page, i) => {
        const sel = finalSelections[i];
        const responseMode = page.response_mode ?? 'single_select';
        const selectedOptionIds = sel?.optionId
          ? [sel.optionId]
          : sel?.optionIds ?? [];
        const selectedOptions = selectedOptionIds.map((id, order) => {
          const opt = page.options.find((option) => option.id === id);
          return {
            id,
            label: opt?.label ?? id,
            ...(responseMode === 'priority_pick' ? { priority: order + 1 } : {}),
          };
        });
        return {
          page_index: i,
          page_title: page.page_title || `问题 ${i + 1}`,
          response_mode: responseMode,
          ...(sel?.optionId ? { selected_option_id: sel.optionId } : {}),
          ...(selectedOptionIds.length ? { selected_option_ids: selectedOptionIds } : {}),
          ...(selectedOptions.length ? { selected_options: selectedOptions } : {}),
          ...(sel?.freetext ? { freetext: sel.freetext } : {}),
        };
      }).filter((page) =>
        Boolean(page.selected_option_id) ||
        Boolean(page.selected_option_ids?.length) ||
        Boolean(page.freetext)
      ),
    };

    // 汇总所有页的信号
    const signals: string[] = allPages.map((page, i) => {
      const sel = finalSelections[i];
      if (!sel) return '';
      if (sel.optionId) {
        const opt = page.options.find((o) => o.id === sel.optionId);
        return opt ? opt.label : sel.optionId;
      }
      if (sel.optionIds?.length) {
        const labels = sel.optionIds.map((id) => page.options.find((o) => o.id === id)?.label ?? id);
        return page.response_mode === 'priority_pick'
          ? `优先级：${labels.join(' > ')}`
          : labels.join('、');
      }
      return sel.freetext ?? '';
    }).filter(Boolean);

    setResponded(true);

    if (totalPages === 1) {
      // 单页：走原来逻辑
      const sel = finalSelections[0];
      onRespond(sel?.optionId, sel?.freetext, structuredResponse);
    } else {
      // 多页：保留人类可读摘要，同时传出结构化选择
      onRespond(undefined, signals.join('; '), structuredResponse);
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
        if (sel.optionIds?.length) {
          const labels = sel.optionIds.map((id) => page.options.find((o) => o.id === id)?.label ?? id);
          return page.response_mode === 'priority_pick'
            ? `优先级：${labels.join(' > ')}`
            : labels.join('、');
        }
        return sel.freetext ?? '';
      }).filter(Boolean);
      return labels.join(' / ');
    })();
    const historyDetails = buildReadOnlyHistoryDetails(allPages, selections, respondedSummary);

    return (
      <div className="py-0.5 text-xs text-[var(--foreground-secondary)]">
        <button
          type="button"
          onClick={() => setHistoryExpanded((value) => !value)}
          className="flex items-start gap-2 text-left transition hover:text-[var(--foreground)]"
          aria-expanded={historyExpanded}
        >
          <span className={`flex-shrink-0 mt-0.5 ${meta.color}`}>◆</span>
          <span>
            <span className="opacity-60">{meta.label}</span>
            <span className="opacity-40 mx-1.5">·</span>
            {displayText ? (
              <span className="text-[var(--foreground)]">{displayText}</span>
            ) : (
              <span className="opacity-60">已确认</span>
            )}
            <span className="ml-2 opacity-50">{historyExpanded ? '收起' : '查看'}</span>
          </span>
        </button>
        {historyExpanded && (
          <div className="mt-2 rounded-lg border border-[#3a3f4b] bg-[#252526] p-3">
            <div className="mb-2 text-[11px] text-[var(--foreground-secondary)]">历史记录只读，如需修改请在当前问诊中重新校准。</div>
            <div className="space-y-2">
              {historyDetails.map((item, index) => (
                <div key={`${item.title}-${index}`} className="rounded-md bg-black/10 px-3 py-2">
                  <div className="text-[11px] font-semibold text-[var(--foreground)]">{item.title}</div>
                  <div className="mt-1 text-[11px] leading-5 text-[var(--foreground-secondary)]">{item.answer || '已确认'}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── 激活态卡片 ────────────────────────────────────────────
  return (
    <div
      className="guidance-card"
      data-testid="guidance-card"
      data-card-id={card.card_id}
      data-card-type={card.card_type}
    >
      {/* ── Header ── */}
      <div className="px-4 py-2.5 border-b border-[#3a3f4b]">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <span className={`flex-shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${meta.badgeBg}`}>
              {meta.label}
            </span>
            <span className="text-sm font-semibold text-[var(--foreground)] truncate">
              {isSchemeInquiry && totalPages > 1
                ? currentQuestionTitle
                : card.title}
            </span>
          </div>
          {totalPages > 1 && !isSchemeInquiry && (
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

        {isSchemeInquiry && totalPages > 1 && (
          <div className="mt-3 grid gap-2" style={{ gridTemplateColumns: `repeat(${totalPages}, minmax(0, 1fr))` }}>
            {allPages.map((page, index) => {
              const completed = index < pageIdx || Boolean(selections[index]);
              const active = index === pageIdx;
              return (
                <button
                  key={`${page.page_title || 'question'}-${index}`}
                  type="button"
                  onClick={() => {
                    if (index <= pageIdx || selections[index]) {
                      setFreetextValue('');
                      setPageIdx(index);
                    }
                  }}
                  className={`flex min-w-0 items-center gap-2 rounded-lg border px-2.5 py-2 text-left transition-colors ${
                    active
                      ? 'border-[#3b6bc7] bg-[#1f3a5f]'
                      : completed
                        ? 'border-emerald-500/30 bg-emerald-500/8'
                        : 'border-[#3a3f4b] bg-black/10'
                  }`}
                  aria-label={`第 ${index + 1} 问：${page.page_title || `问题 ${index + 1}`}`}
                >
                  <span
                    className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
                      completed
                        ? 'bg-emerald-400 text-black'
                        : active
                          ? 'bg-cyan-300 text-black'
                          : 'bg-[#3a3f4b] text-[var(--foreground-secondary)]'
                    }`}
                  >
                    {completed ? <Check size={12} /> : index + 1}
                  </span>
                  <span className="min-w-0">
                    <span className={`block truncate text-xs font-semibold ${active ? 'text-white' : 'text-[var(--foreground)]'}`}>
                      {page.page_title || `问题 ${index + 1}`}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ── 页面内容 ── */}
      <div className="px-4 pt-3 pb-2">
        {currentPage.page_title && !isSchemeInquiry && (
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--foreground-secondary)] opacity-60 mb-1.5">
            {currentPage.page_title}
          </p>
        )}
        {missingSlotMeta && (
          <div className="mb-2 flex items-center gap-2">
            <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${missingSlotMeta.className}`}>
              {missingSlotMeta.label}
            </span>
            {currentPage.missing_slot_names?.length ? (
              <span className="truncate text-[11px] text-[var(--foreground-secondary)]">
                {currentPage.missing_slot_names.length} 项待确认
              </span>
            ) : null}
          </div>
        )}
        <p className="text-[var(--foreground)] leading-relaxed mb-3">
          {currentPage.prompt_text}
        </p>
        {demandReconstructionSections.length > 0 && (
          <div className="mb-3 space-y-2">
            {demandReconstructionSections.map((section, index) => {
              const emphasisClass =
                section.emphasis === 'high'
                  ? 'border-emerald-400/40 bg-emerald-400/10'
                  : section.emphasis === 'medium'
                    ? 'border-cyan-400/30 bg-cyan-400/8'
                    : 'border-[#3a3f4b] bg-black/10';
              return (
                <section
                  key={`${section.title}-${index}`}
                  className={`rounded-lg border px-3 py-2.5 ${emphasisClass}`}
                >
                  <h4 className="text-xs font-semibold text-[var(--foreground)]">
                    {section.title}
                  </h4>
                  {section.body && (
                    <p className="mt-1 text-xs leading-5 text-[var(--foreground-secondary)]">
                      {section.body}
                    </p>
                  )}
                  {section.items && section.items.length > 0 && (
                    <ul className="mt-2 space-y-1 text-xs leading-5 text-[var(--foreground-secondary)]">
                      {section.items.map((item, itemIndex) => (
                        <li key={`${section.title}-${itemIndex}`} className="flex gap-2">
                          <span className="mt-0.5 text-[var(--foreground)] opacity-50">-</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              );
            })}
          </div>
        )}
        {currentPage.helper_text && (
          <p className="mb-3 text-xs leading-5 text-[var(--foreground-secondary)]">
            {currentPage.helper_text}
          </p>
        )}

        {/* 编号选项列表 */}
        {currentPage.options && currentPage.options.length > 0 && (
          <div className="flex flex-col gap-1">
            {currentPage.options.map((opt, i) => {
              const selectedIds = currentSelection?.optionIds ?? [];
              const selected = currentSelection?.optionId === opt.id || selectedIds.includes(opt.id);
              const priorityIndex = responseMode === 'priority_pick' ? selectedIds.indexOf(opt.id) : -1;
              return (
                <button
                  key={opt.id}
                  onClick={() => handleSelectOption(opt.id)}
                  className={`guidance-card-option ${selected ? 'guidance-card-option-active' : ''}`}
                >
                  <span className={`flex-shrink-0 text-xs w-5 text-right mt-0.5 tabular-nums select-none
                    ${selected ? 'text-[#4fc3f7]' : 'text-[var(--foreground-secondary)]'}`}>
                    {priorityIndex >= 0 ? priorityIndex + 1 : `${i + 1}.`}
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
          可跳过
        </button>
        {isLastPage ? (
          <button
            onClick={handleSubmit}
            disabled={!canProceed}
            className="px-4 py-1.5 text-xs font-semibold rounded-full bg-[#1a6fcf] text-white hover:bg-[#1660b8] disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
          >
            {submitLabel} <span className="opacity-70">↵</span>
          </button>
        ) : (
          <button
            onClick={handleNext}
            disabled={!canProceed}
            className="px-4 py-1.5 text-xs font-semibold rounded-full bg-[#1a6fcf] text-white hover:bg-[#1660b8] disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
          >
            下一问：{nextQuestionTitle} <ChevronRight size={12} />
          </button>
        )}
      </div>
    </div>
  );
}

function buildReadOnlyHistoryDetails(
  pages: GuidanceCardPage[],
  selections: Record<number, PageSelection>,
  respondedSummary?: string
): Array<{ title: string; answer: string }> {
  const summaryParts = respondedSummary
    ? respondedSummary
        .split(/[;；/]/)
        .map((part) => part.trim())
        .filter(Boolean)
    : [];

  return pages.map((page, index) => {
    const sel = selections[index];
    let answer = summaryParts[index] ?? '';

    if (sel?.optionId) {
      answer = page.options.find((option) => option.id === sel.optionId)?.label ?? sel.optionId;
    } else if (sel?.optionIds?.length) {
      const labels = sel.optionIds.map((id) => page.options.find((option) => option.id === id)?.label ?? id);
      answer = page.response_mode === 'priority_pick'
        ? labels.map((label, order) => `${order + 1}. ${label}`).join('；')
        : labels.join('、');
    } else if (sel?.freetext) {
      answer = sel.freetext;
    }

    return {
      title: page.page_title || `问题 ${index + 1}`,
      answer,
    };
  });
}
