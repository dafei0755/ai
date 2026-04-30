/**
 * CandidateCard.tsx — 候选卡片组件（高参协作协议 L2 层）
 * Created by GitHub Copilot · 2026-03-17
 *
 * 实现"系统先出牌，用户后校准"的卡片渲染器。
 * 支持 4 种标准动作：Confirm / Edit / Add / Defer
 * 每个字段显示来源依据（source_ref），推断字段标注 ⚠️
 */

'use client';

import React, { useState } from 'react';
import { Check, Edit2, Plus, Clock, ChevronDown, ChevronUp } from 'lucide-react';

// ── 类型定义 ──────────────────────────────────────────────

export interface CandidateFieldData {
  field_id: string;
  key: string;
  value: string;
  source_ref: string;
  inferred: boolean;
  user_value?: string | null;
}

export interface CandidateCardData {
  card_id: string;
  card_type: 'echo' | 'gap';
  title: string;
  summary: string;
  candidate_fields: CandidateFieldData[];
  card_status: 'draft' | 'candidate' | 'confirmed' | 'frozen' | 'reverted';
  gap_round?: boolean;
}

export interface CandidateCardResponse {
  card_id: string;
  action: 'confirm' | 'edit' | 'add' | 'defer';
  field_edits: Record<string, string>;  // field_id → new value
  freetext?: string;
}

interface CandidateCardProps {
  card: CandidateCardData;
  initialResponded?: boolean;
  respondedSummary?: string;
  onRespond: (response: CandidateCardResponse) => void;
}

// ── 动作配置 ──────────────────────────────────────────────

const ACTION_META = {
  confirm: { label: '全部确认', icon: Check,  color: 'bg-emerald-500 hover:bg-emerald-600 text-white' },
  edit:    { label: '已修改，保存', icon: Edit2, color: 'bg-blue-500 hover:bg-blue-600 text-white' },
  add:     { label: '追加补充', icon: Plus,  color: 'bg-violet-500 hover:bg-violet-600 text-white' },
  defer:   { label: '先跳过', icon: Clock, color: 'bg-zinc-200 hover:bg-zinc-300 text-zinc-700 dark:bg-zinc-600 dark:hover:bg-zinc-500 dark:text-zinc-100' },
};

const CARD_TYPE_META = {
  echo: { badge: '归纳确认', borderColor: 'border-blue-200 dark:border-blue-800',   bg: 'bg-blue-50/60 dark:bg-blue-950/30' },
  gap:  { badge: '信息补全', borderColor: 'border-amber-200 dark:border-amber-800', bg: 'bg-amber-50/60 dark:bg-amber-950/30' },
};

// ── 主组件 ────────────────────────────────────────────────

export default function CandidateCard({
  card,
  initialResponded = false,
  respondedSummary,
  onRespond,
}: CandidateCardProps) {
  const [editValues, setEditValues] = useState<Record<string, string>>({});
  const [editingId, setEditingId] = useState<string | null>(null);
  const [addText, setAddText] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [responded, setResponded] = useState(initialResponded);
  const [expandedSource, setExpandedSource] = useState<string | null>(null);

  const typeMeta = CARD_TYPE_META[card.card_type];
  const hasEdits = Object.keys(editValues).length > 0;
  const hasAdd = addText.trim().length > 0;

  // ── 已响应态（留痕显示）──────────────────────────────────
  if (responded) {
    const summary = respondedSummary ?? '已处理';
    return (
      <div className="flex items-center gap-2 py-1 text-xs text-[var(--foreground-tertiary,#888)]">
        <span className="text-emerald-500 flex-shrink-0">◆</span>
        <span className="opacity-70">{typeMeta.badge}</span>
        <span className="opacity-40 mx-1">·</span>
        <span className="italic">{summary}</span>
      </div>
    );
  }

  // ── 字段行 ───────────────────────────────────────────────
  const renderField = (f: CandidateFieldData) => {
    const isEditing = editingId === f.field_id;
    const currentVal = editValues[f.field_id] ?? f.value;
    const isSourceOpen = expandedSource === f.field_id;

    return (
      <div
        key={f.field_id}
        className="border border-zinc-200 dark:border-zinc-700 rounded-lg overflow-hidden"
      >
        {/* 字段头部 */}
        <div className="flex items-center justify-between px-3 py-2 bg-white dark:bg-zinc-800">
          <div className="flex items-center gap-2 min-w-0">
            {f.inferred && (
              <span
                title="系统推断，请核实"
                className="text-amber-500 text-xs flex-shrink-0"
              >
                ⚠️
              </span>
            )}
            <span className="text-xs font-medium text-zinc-600 dark:text-zinc-400 flex-shrink-0">
              {f.key}
            </span>
            <span className="text-xs text-zinc-400 dark:text-zinc-500 mx-1">·</span>
            {isEditing ? (
              <input
                autoFocus
                className="flex-1 text-sm bg-transparent border-b border-blue-400 outline-none text-zinc-800 dark:text-zinc-100 min-w-0"
                value={currentVal}
                onChange={(e) =>
                  setEditValues((prev) => ({ ...prev, [f.field_id]: e.target.value }))
                }
                onBlur={() => setEditingId(null)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') setEditingId(null);
                  if (e.key === 'Escape') {
                    setEditValues((prev) => {
                      const next = { ...prev };
                      delete next[f.field_id];
                      return next;
                    });
                    setEditingId(null);
                  }
                }}
              />
            ) : (
              <span
                className={`text-sm flex-1 min-w-0 truncate ${
                  editValues[f.field_id]
                    ? 'text-blue-600 dark:text-blue-400 font-medium'
                    : 'text-zinc-800 dark:text-zinc-100'
                }`}
                title={currentVal}
              >
                {currentVal || <span className="opacity-40 italic">（请填写）</span>}
              </span>
            )}
          </div>
          {/* 编辑图标 */}
          {!isEditing && (
            <button
              onClick={() => setEditingId(f.field_id)}
              className="flex-shrink-0 ml-2 p-1 rounded text-zinc-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-950 transition-colors"
              title="编辑此字段"
            >
              <Edit2 size={12} />
            </button>
          )}
        </div>

        {/* 来源依据（折叠） */}
        {f.source_ref && (
          <button
            onClick={() =>
              setExpandedSource(isSourceOpen ? null : f.field_id)
            }
            className="w-full flex items-center gap-1 px-3 py-1 text-xs text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-100 dark:border-zinc-800 transition-colors"
          >
            {isSourceOpen ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
            <span>来源依据</span>
            {!isSourceOpen && (
              <span className="ml-1 truncate opacity-70">{f.source_ref.slice(0, 35)}…</span>
            )}
          </button>
        )}
        {isSourceOpen && f.source_ref && (
          <div className="px-3 py-2 text-xs text-zinc-500 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-100 dark:border-zinc-800 italic">
            {f.source_ref}
          </div>
        )}
      </div>
    );
  };

  // ── 提交逻辑 ─────────────────────────────────────────────
  const handleConfirm = () => {
    const action = hasEdits ? 'edit' : 'confirm';
    const response: CandidateCardResponse = {
      card_id: card.card_id,
      action,
      field_edits: editValues,
    };
    setResponded(true);
    onRespond(response);
  };

  const handleAdd = () => {
    const response: CandidateCardResponse = {
      card_id: card.card_id,
      action: 'add',
      field_edits: editValues,
      freetext: addText.trim(),
    };
    setResponded(true);
    onRespond(response);
  };

  const handleDefer = () => {
    const response: CandidateCardResponse = {
      card_id: card.card_id,
      action: 'defer',
      field_edits: {},
    };
    setResponded(true);
    onRespond(response);
  };

  // ── 渲染 ─────────────────────────────────────────────────
  return (
    <div
      className={`ui-card-shell rounded-xl ${typeMeta.bg} overflow-hidden`}
    >
      {/* 卡头 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-inherit">
        <div className="flex items-center gap-2">
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              card.card_type === 'echo'
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                : 'bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300'
            }`}
          >
            {typeMeta.badge}
          </span>
          <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-100">
            {card.title}
          </h3>
        </div>
      </div>

      {/* 说明文字 */}
      <p className="px-4 pt-3 pb-1 text-xs text-zinc-500 dark:text-zinc-400">
        {card.summary}
      </p>

      {/* 字段列表 */}
      <div className="px-4 pb-3 space-y-2 mt-2">
        {card.candidate_fields.map(renderField)}
      </div>

      {/* 追加补充区 */}
      {showAdd ? (
        <div className="px-4 pb-3">
          <textarea
            autoFocus
            rows={2}
            placeholder="请补充系统遗漏的信息…"
            className="w-full text-sm border border-violet-300 dark:border-violet-700 rounded-lg px-3 py-2 bg-white dark:bg-zinc-800 text-zinc-800 dark:text-zinc-100 outline-none resize-none focus:ring-2 focus:ring-violet-400"
            value={addText}
            onChange={(e) => setAddText(e.target.value)}
          />
        </div>
      ) : (
        <div className="px-4 pb-2">
          <button
            onClick={() => setShowAdd(true)}
            className="flex items-center gap-1 text-xs text-zinc-400 hover:text-violet-500 transition-colors"
          >
            <Plus size={12} />
            <span>系统遗漏了什么？追加补充</span>
          </button>
        </div>
      )}

      {/* 操作按钮 */}
      <div className="px-4 pb-4 flex flex-wrap gap-2 border-t border-inherit pt-3">
        {/* 主动作：Confirm / Edit after editing */}
        <button
          onClick={handleConfirm}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
            ACTION_META[hasEdits ? 'edit' : 'confirm'].color
          }`}
        >
          {hasEdits ? (
            <Edit2 size={12} />
          ) : (
            <Check size={12} />
          )}
          {hasEdits ? ACTION_META.edit.label : ACTION_META.confirm.label}
        </button>

        {/* Add 动作（仅在已展开追加区时显示） */}
        {showAdd && (
          <button
            onClick={handleAdd}
            disabled={!hasAdd}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              hasAdd
                ? ACTION_META.add.color
                : 'bg-zinc-100 text-zinc-400 cursor-not-allowed dark:bg-zinc-800 dark:text-zinc-600'
            }`}
          >
            <Plus size={12} />
            {ACTION_META.add.label}
          </button>
        )}

        {/* Defer */}
        <button
          onClick={handleDefer}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${ACTION_META.defer.color}`}
        >
          <Clock size={12} />
          {ACTION_META.defer.label}
        </button>
      </div>
    </div>
  );
}
