/**
 * DraftSidebar.tsx — v2.0 草稿侧边栏
 * Created by GitHub Copilot · 2026-03-22
 *
 * 展示对话态积累的所有草稿对象（IntentSeed / ProblemFrameDraft 等），
 * 支持：
 *   - 按草稿类型分组展示
 *   - 显示确认状态（已确认 / 待确认 / 已升级）
 *   - 「升级准备度」进度条
 *   - 立即升级按钮（upgrade_ready 全绿时激活）
 */

'use client';

import React, { useMemo } from 'react';

// ── 类型定义 ──────────────────────────────────────────────

export type DraftType =
  | 'intent_seed'
  | 'problem_frame'
  | 'direction_candidates'
  | 'conflict_pack'
  | 'boundary'
  | 'consensus';

export interface DraftMeta {
  source: string;
  user_confirmed: boolean;
  inferred: boolean;
  open_questions: string[];
  upgrade_ready: boolean;
}

export interface DraftObject {
  draft_id: string;
  draft_type: DraftType;
  summary: string;       // 展示用摘要（50字以内）
  meta: DraftMeta;
  created_at?: string;
}

export interface UpgradeReadiness {
  /** 0–100，100 时可升级 */
  score: number;
  /** 哪些草稿类型尚未齐全 */
  missing_types: DraftType[];
}

export interface DraftSidebarProps {
  drafts: DraftObject[];
  upgradeReadiness?: UpgradeReadiness;
  /** 「发起升级」按钮回调 */
  onUpgrade?: () => void;
  /** 载入中（骨架屏） */
  loading?: boolean;
  className?: string;
}

// ── 常量 ─────────────────────────────────────────────────

const DRAFT_LABELS: Record<DraftType, string> = {
  intent_seed:          '意图原点',
  problem_frame:        '问题框架',
  direction_candidates: '方向候选',
  conflict_pack:        '关键冲突',
  boundary:             '边界红线',
  consensus:            '阶段共识',
};

const DRAFT_ICONS: Record<DraftType, string> = {
  intent_seed:          '🌱',
  problem_frame:        '🗂️',
  direction_candidates: '🔀',
  conflict_pack:        '⚡',
  boundary:             '🚧',
  consensus:            '✅',
};

// ── 子组件：草稿卡片 ──────────────────────────────────────

function DraftCard({ draft }: { draft: DraftObject }) {
  const statusColor = draft.meta.user_confirmed
    ? 'border-green-300 bg-green-900/20'
    : draft.meta.upgrade_ready
    ? 'border-amber-300 bg-amber-900/20'
    : 'border-[var(--border-color)] bg-[var(--card-bg)]';

  return (
    <div
      className={`rounded-lg border px-3 py-2.5 mb-2 ${statusColor}`}
      data-testid="draft-card"
      data-draft-type={draft.draft_type}
    >
      <div className="flex items-start gap-2">
        <span className="text-base flex-shrink-0 mt-0.5">
          {DRAFT_ICONS[draft.draft_type]}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-medium text-[var(--foreground-secondary)]">
              {DRAFT_LABELS[draft.draft_type]}
            </span>
            {draft.meta.user_confirmed && (
              <span className="text-[10px] px-1.5 py-0.5 bg-green-100 text-green-700 rounded-full">
                已确认
              </span>
            )}
            {draft.meta.inferred && (
              <span className="text-[10px] px-1.5 py-0.5 bg-blue-100 text-blue-600 rounded-full">
                推断
              </span>
            )}
          </div>
          <p className="text-sm text-[var(--foreground)] mt-0.5 truncate">{draft.summary}</p>
          {draft.meta.open_questions.length > 0 && (
            <p className="text-[11px] text-orange-500 mt-1">
              ❓ {draft.meta.open_questions[0]}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── 骨架屏 ────────────────────────────────────────────────

function SidebarSkeleton() {
  return (
    <div className="space-y-2 px-4 animate-pulse">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-16 rounded-lg bg-[var(--sidebar-bg)]" />
      ))}
    </div>
  );
}

// ── 主组件 ────────────────────────────────────────────────

export default function DraftSidebar({
  drafts,
  upgradeReadiness,
  onUpgrade,
  loading = false,
  className = '',
}: DraftSidebarProps) {
  const draftsByType = useMemo(() => {
    const map = new Map<DraftType, DraftObject[]>();
    for (const d of drafts) {
      if (!map.has(d.draft_type)) map.set(d.draft_type, []);
      map.get(d.draft_type)!.push(d);
    }
    return map;
  }, [drafts]);

  const canUpgrade =
    (upgradeReadiness?.score ?? 0) >= 80 ||
    drafts.some((d) => d.meta.upgrade_ready);

  return (
    <aside
      className={`flex flex-col h-full border-l border-[var(--border-color)] bg-[var(--sidebar-bg)] ${className}`}
      aria-label="草稿侧边栏"
    >
      {/* 标题栏 */}
      <div className="px-4 py-3 border-b border-[var(--border-color)] flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">对话草稿</h3>
          <p className="text-[11px] text-[var(--foreground-secondary)] mt-0.5">
            {drafts.length} 个对象
          </p>
        </div>
        {upgradeReadiness && (
          <div className="text-right">
            <p className="text-[11px] text-[var(--foreground-secondary)]">
              升级准备度 {upgradeReadiness.score}%
            </p>
            <div className="w-20 h-1.5 bg-[var(--card-bg)] rounded-full mt-1 overflow-hidden">
              <div
                className="h-full bg-[var(--primary)] rounded-full transition-all"
                style={{ width: `${Math.min(upgradeReadiness.score, 100)}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* 草稿列表 */}
      <div className="flex-1 overflow-y-auto py-3 px-3">
        {loading ? (
          <SidebarSkeleton />
        ) : drafts.length === 0 ? (
          <div className="text-center text-[var(--foreground-secondary)] py-8 select-none">
            <div className="text-3xl mb-2">📝</div>
            <p className="text-sm">还没有草稿</p>
            <p className="text-xs mt-1">与 AI 对话后自动记录</p>
          </div>
        ) : (
          Array.from(draftsByType.entries()).map(([type, items]) => (
            <div key={type} className="mb-1">
              {items.map((d) => (
                <DraftCard key={d.draft_id} draft={d} />
              ))}
            </div>
          ))
        )}

        {/* 缺失草稿提示 */}
        {upgradeReadiness && upgradeReadiness.missing_types.length > 0 && (
          <div className="mt-2 px-1">
            <p className="text-[11px] text-[var(--foreground-secondary)] mb-1">还需要：</p>
            <div className="flex flex-wrap gap-1">
              {upgradeReadiness.missing_types.map((t) => (
                <span
                  key={t}
                  className="text-[10px] px-2 py-0.5 bg-[var(--card-bg)] text-[var(--foreground-secondary)] rounded-full border border-[var(--border-color)]"
                >
                  {DRAFT_LABELS[t] || t}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 升级按钮 */}
      <div className="px-3 pb-4 pt-2 border-t border-[var(--border-color)]">
        <button
          onClick={onUpgrade}
          disabled={!canUpgrade || loading}
          className="w-full py-2 rounded-xl text-sm font-medium transition-colors
            bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)]
            disabled:bg-[var(--sidebar-bg)] disabled:text-[var(--foreground-secondary)] disabled:cursor-not-allowed"
        >
          {canUpgrade ? '整理为正式项目 →' : '继续积累草稿…'}
        </button>
      </div>
    </aside>
  );
}
