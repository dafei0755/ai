/**
 * UpgradePromptBanner.tsx — v2.0 升级提示横幅
 * Created by GitHub Copilot · 2026-03-22
 *
 * 当认知指标（freeze_readiness / cognitive_debt / diverge_fatigue）触发阈值时，
 * 向用户展示「建议升级为项目态」的横幅，包含：
 *   - 三大认知指标进度条
 *   - AI 建议文本
 *   - 确认升级 / 暂不升级 按钮
 */

'use client';

import React from 'react';

// ── 类型定义 ──────────────────────────────────────────────

export interface CognitionIndicators {
  /** 0–1：冻结就绪度（高 = 意图已稳定） */
  freeze_readiness: number;
  /** 0–1：认知债务（高 = 积累太多上下文，需要固化） */
  cognitive_debt: number;
  /** 0–1：发散疲劳度（高 = 讨论反复，需结构化） */
  diverge_fatigue: number;
}

export interface UpgradePromptBannerProps {
  /** 是否处于触发状态（true 时横幅突出高亮） */
  triggered: boolean;
  indicators: CognitionIndicators;
  /** AI 生成的建议文案 */
  suggestion_text: string;
  onConfirm: () => void;
  onDismiss: () => void;
  className?: string;
}

// ── 工具函数 ──────────────────────────────────────────────

/** 将 0-1 的值转换为百分比颜色 class */
function indicatorColor(value: number): string {
  if (value >= 0.8) return 'bg-[var(--primary)]';
  if (value >= 0.5) return 'bg-amber-400';
  return 'bg-[var(--sidebar-bg)]';
}

function formatPercent(v: number): string {
  return `${Math.round(v * 100)}%`;
}

// ── 单条指标行 ────────────────────────────────────────────

interface IndicatorRowProps {
  label: string;
  hint: string;
  value: number;
}

function IndicatorRow({ label, hint, value }: IndicatorRowProps) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 flex-shrink-0 text-right">
        <span className="text-xs text-[var(--foreground-secondary)]" title={hint}>{label}</span>
      </div>
      <div className="flex-1 h-2 bg-[var(--sidebar-bg)] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${indicatorColor(value)}`}
          style={{ width: `${Math.min(value * 100, 100)}%` }}
          aria-valuenow={Math.round(value * 100)}
          aria-valuemin={0}
          aria-valuemax={100}
          role="progressbar"
        />
      </div>
      <span className="text-xs tabular-nums text-[var(--foreground-secondary)] w-9 text-right">
        {formatPercent(value)}
      </span>
    </div>
  );
}

// ── 主组件 ────────────────────────────────────────────────

export default function UpgradePromptBanner({
  triggered,
  indicators,
  suggestion_text,
  onConfirm,
  onDismiss,
  className = '',
}: UpgradePromptBannerProps) {
  const containerClass = triggered
    ? 'border-[var(--primary)] bg-[var(--card-bg)] shadow-md'
    : 'border-[var(--border-color)] bg-[var(--card-bg)] shadow-sm';

  return (
    <div
      role="alert"
      aria-live="polite"
      data-triggered={triggered}
      className={`rounded-2xl border p-4 transition-all duration-300 ${containerClass} ${className}`}
    >
      {/* 标题行 */}
      <div className="mb-3">
        <div className="ui-note">
        <span className="text-base leading-none">{triggered ? '🚀' : '📝'}</span>
        <h4 className="ui-type-meta font-medium text-[var(--foreground-secondary)]">
          {triggered ? '建议·升级为正式项目' : '备注·认知状态监测'}
        </h4>
        </div>
      </div>

      {/* 建议文本 */}
      {suggestion_text && (
        <p className="ui-type-body mb-3 text-[var(--foreground-secondary)]">
          {suggestion_text}
        </p>
      )}

      {/* 三大指标 */}
      <div className="space-y-2 mb-4">
        <IndicatorRow
          label="意图稳定"
          hint="freeze_readiness：越高说明意图已收束"
          value={indicators.freeze_readiness}
        />
        <IndicatorRow
          label="认知债务"
          hint="cognitive_debt：越高说明上下文积累多，需要固化"
          value={indicators.cognitive_debt}
        />
        <IndicatorRow
          label="发散疲劳"
          hint="diverge_fatigue：越高说明对话反复，需结构化"
          value={indicators.diverge_fatigue}
        />
      </div>

      {/* 操作按钮 */}
      {triggered && (
        <div className="flex gap-2 justify-end">
          <button
            onClick={onDismiss}
            className="px-4 py-1.5 rounded-xl text-xs text-[var(--foreground-secondary)]
              border border-[var(--border-color)] hover:bg-[var(--sidebar-bg)] transition-colors"
          >
            暂不升级
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-1.5 rounded-xl text-xs font-medium text-white
              bg-[var(--primary)] hover:bg-[var(--primary-hover)] transition-colors"
          >
            确认升级 →
          </button>
        </div>
      )}
    </div>
  );
}
