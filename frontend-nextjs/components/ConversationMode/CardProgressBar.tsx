/**
 * CardProgressBar.tsx — 卡片批次进度条
 * Created by GitHub Copilot · 2026-03-17
 *
 * 展示当前 L2 协作层一批候选卡的完成状态。
 * 每张卡用 ✅/❓/⚠️/🔒 图标标注，整体进度用进度条显示。
 */

'use client';

import React from 'react';

// ── 类型 ──────────────────────────────────────────────────

export type CardProgressStatus = 'confirmed' | 'candidate' | 'deferred' | 'frozen';

export interface CardProgressItem {
  card_id: string;
  title: string;
  status: CardProgressStatus;
}

interface CardProgressBarProps {
  items: CardProgressItem[];
  className?: string;
}

// ── 状态元信息 ─────────────────────────────────────────────

const STATUS_META: Record<CardProgressStatus, { icon: string; label: string; color: string }> = {
  confirmed: { icon: '✅', label: '已确认', color: 'text-emerald-600 dark:text-emerald-400' },
  candidate: { icon: '❓', label: '待处理', color: 'text-amber-500 dark:text-amber-400' },
  deferred:  { icon: '⚠️', label: '已推迟', color: 'text-orange-500 dark:text-orange-400' },
  frozen:    { icon: '🔒', label: '已冻结', color: 'text-zinc-400 dark:text-zinc-500' },
};

// ── 组件 ─────────────────────────────────────────────────

export default function CardProgressBar({ items, className = '' }: CardProgressBarProps) {
  if (!items.length) return null;

  const confirmedCount = items.filter(
    (i) => i.status === 'confirmed' || i.status === 'frozen'
  ).length;
  const total = items.length;
  const progressPct = Math.round((confirmedCount / total) * 100);

  return (
    <div className={`rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-800/50 px-3 py-2 ${className}`}>
      {/* 标题行 */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">
          本轮卡片进度
        </span>
        <span className="text-xs text-zinc-400 dark:text-zinc-500">
          {confirmedCount} / {total}
        </span>
      </div>

      {/* 进度条 */}
      <div className="h-1.5 rounded-full bg-zinc-100 dark:bg-zinc-700 overflow-hidden mb-2">
        <div
          className="h-full rounded-full bg-emerald-400 dark:bg-emerald-500 transition-all duration-500"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* 卡片状态列表 */}
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {items.map((item) => {
          const meta = STATUS_META[item.status];
          return (
            <div
              key={item.card_id}
              className={`flex items-center gap-1 text-xs ${meta.color}`}
              title={`${item.title} — ${meta.label}`}
            >
              <span>{meta.icon}</span>
              <span className="max-w-[120px] truncate opacity-80">{item.title}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
