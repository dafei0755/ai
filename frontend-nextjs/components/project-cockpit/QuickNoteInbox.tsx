'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import type {
  QuickNote,
  QuickNoteTargetPage,
  CreateQuickNoteRequest,
  UpdateQuickNoteRequest,
  ListQuickNotesResponse,
} from '@/types/quick_note';

const QUICK_NOTE_API = '/api/quick-notes';
const TARGET_PAGE_OPTIONS: QuickNoteTargetPage[] = ['草池', '沉淀', '作品', '我'];
const CATEGORY_OPTIONS: Record<QuickNoteTargetPage, string[]> = {
  草池: ['待分类', '稍后判断', '临时备忘'],
  沉淀: ['习惯', '经验', '方法', '模板', '禁忌', '案例复盘'],
  作品: ['办公', '商业', '住宅', '酒店', '民宿', '文旅'],
  我: ['偏好', '优势', '盲区', '风格', '价值主张', '表达习惯'],
};

function relativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  return `${days}天前`;
}

function reviewLabel(note: QuickNote): string {
  if (note.review_status === 'reviewed') return '已复核';
  if (note.review_status === 'manual_review_required') return '待人工复核';
  return '未复核';
}

function promotionLabel(note: QuickNote): string {
  if (note.promotion_status === 'promoted') return '已提升';
  if (note.promotion_status === 'candidate_routed') return '候选路由';
  return '未提升';
}

export function QuickNoteInbox() {
  const [text, setText] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [notes, setNotes] = useState<QuickNote[]>([]);
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [editTargetPage, setEditTargetPage] = useState<QuickNoteTargetPage>('草池');
  const [editCategory, setEditCategory] = useState('待分类');
  const [editError, setEditError] = useState<string | null>(null);
  const [savingEditId, setSavingEditId] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const fetchNotes = useCallback(async () => {
    try {
      const res = await fetch(`${QUICK_NOTE_API}?hours=24&limit=20`);
      if (!res.ok) return;
      const data: ListQuickNotesResponse = await res.json();
      setNotes(data.items);
    } catch {
      // silent — list is best-effort
    }
  }, []);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  const handleSave = useCallback(async () => {
    const trimmed = text.trim();
    if (!trimmed || isSaving) return;

    setIsSaving(true);
    setSaveError(null);

    const optimisticNote: QuickNote = {
      quicknote_id: `optimistic-${Date.now()}`,
      raw_text: trimmed,
      created_at: new Date().toISOString(),
      source: 'web',
      status: 'raw',
      original_preserved: true,
      review_status: 'unreviewed',
      promotion_status: 'not_promoted',
      promoted_object_id: null,
    };

    setNotes((prev) => [optimisticNote, ...prev]);
    setText('');
    textareaRef.current?.focus();

    try {
      const body: CreateQuickNoteRequest = { raw_text: trimmed, source: 'web' };
      const res = await fetch(QUICK_NOTE_API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        throw new Error(`保存失败 (${res.status})`);
      }
      const saved = await res.json();
      setNotes((prev) =>
        prev.map((n) =>
          n.quicknote_id === optimisticNote.quicknote_id
            ? saved
            : n
        )
      );
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : '保存失败');
      setText(trimmed);
      setNotes((prev) => prev.filter((n) => n.quicknote_id !== optimisticNote.quicknote_id));
    } finally {
      setIsSaving(false);
    }
  }, [text, isSaving]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSave();
    }
  };

  const canSave = text.trim().length > 0 && !isSaving;

  const beginEdit = (note: QuickNote) => {
    const targetPage = note.target_page ?? '草池';
    setEditingNoteId(note.quicknote_id);
    setEditText(note.raw_text);
    setEditTargetPage(targetPage);
    setEditCategory(note.category || CATEGORY_OPTIONS[targetPage][0]);
    setEditError(null);
  };

  const cancelEdit = () => {
    setEditingNoteId(null);
    setEditText('');
    setEditTargetPage('草池');
    setEditCategory('待分类');
    setEditError(null);
  };

  const handleEditTargetChange = (targetPage: QuickNoteTargetPage) => {
    setEditTargetPage(targetPage);
    setEditCategory(CATEGORY_OPTIONS[targetPage][0]);
  };

  const handleUpdateNote = async () => {
    if (!editingNoteId || savingEditId) return;
    const trimmed = editText.trim();
    if (!trimmed) {
      setEditError('内容不能为空');
      return;
    }

    setSavingEditId(editingNoteId);
    setEditError(null);

    try {
      const body: UpdateQuickNoteRequest = {
        quicknote_id: editingNoteId,
        raw_text: trimmed,
        target_page: editTargetPage,
        category: editCategory,
      };
      const res = await fetch(QUICK_NOTE_API, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        throw new Error(`更新失败 (${res.status})`);
      }
      const updated: QuickNote = await res.json();
      setNotes((prev) => prev.map((note) => (note.quicknote_id === updated.quicknote_id ? updated : note)));
      cancelEdit();
    } catch (err) {
      setEditError(err instanceof Error ? err.message : '更新失败');
    } finally {
      setSavingEditId(null);
    }
  };

  return (
    <div className="flex-1 min-h-0 overflow-y-auto bg-[#f6f7fa] pl-20 pr-6 py-6">
      <section className="cockpit-card cockpit-card-accent-files bg-white p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-slate-800">速记</p>
            <p className="mt-1 text-xs text-slate-400">先保存原始想法，后续再分类、归档和沉淀。</p>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-medium text-slate-500">
            QuickNote Inbox
          </span>
        </div>

        <textarea
          ref={textareaRef}
          autoFocus
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="随手记一条想法…"
          rows={5}
          className="w-full resize-none rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 placeholder:text-slate-400 outline-none focus:border-slate-400 focus:bg-white transition-colors leading-relaxed"
        />

        <div className="mt-3 flex items-center justify-between">
          {saveError ? (
            <span className="text-xs text-red-500">{saveError}</span>
          ) : (
            <span className="text-xs text-slate-400">⌘ + Enter 快速保存</span>
          )}
          <button
            onClick={handleSave}
            disabled={!canSave}
            className="rounded-lg bg-slate-700 px-4 py-1.5 text-xs font-medium text-white transition hover:bg-slate-800 disabled:opacity-30"
          >
            {isSaving ? '保存中…' : '保存到草池'}
          </button>
        </div>
      </section>

      <section className="mt-5 cockpit-card bg-white p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-semibold text-slate-800">最近 24 小时</p>
            <p className="mt-1 text-xs text-slate-400">未分类内容先留在草池，不进入沉淀 / 作品 / 我。</p>
          </div>
          {notes.length > 0 && (
            <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-medium text-slate-500">
              {notes.length} 条
            </span>
          )}
        </div>

        {notes.length > 0 ? (
          <div className="space-y-0">
            <ul className="divide-y divide-slate-100">
              {notes.slice(0, 8).map((note) => (
                <li key={note.quicknote_id} className="group py-4 first:pt-0 last:pb-0">
                  {editingNoteId === note.quicknote_id ? (
                    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
                      <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        rows={3}
                        className="w-full resize-none rounded-md border border-slate-200 bg-white px-3 py-2 text-sm leading-relaxed text-slate-800 outline-none focus:border-slate-400"
                      />
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        {TARGET_PAGE_OPTIONS.map((page) => (
                          <button
                            key={page}
                            onClick={() => handleEditTargetChange(page)}
                            className={`h-7 rounded-full px-3 text-[11px] font-medium transition ${
                              editTargetPage === page
                                ? 'bg-slate-800 text-white'
                                : 'bg-white text-slate-500 hover:bg-slate-100'
                            }`}
                          >
                            {page}
                          </button>
                        ))}
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        {CATEGORY_OPTIONS[editTargetPage].map((category) => (
                          <button
                            key={category}
                            onClick={() => setEditCategory(category)}
                            className={`h-7 rounded-md px-2.5 text-[11px] font-medium transition ${
                              editCategory === category
                                ? 'bg-sky-100 text-sky-700'
                                : 'bg-white text-slate-500 hover:bg-slate-100'
                            }`}
                          >
                            {category}
                          </button>
                        ))}
                      </div>
                      <div className="mt-3 flex items-center justify-between gap-3">
                        {editError ? (
                          <span className="text-xs text-red-500">{editError}</span>
                        ) : (
                          <span className="text-xs text-slate-400">原文保留；分类只生成候选路由，不会自动入库或发布。</span>
                        )}
                        <div className="flex items-center gap-2">
                          <button
                            onClick={cancelEdit}
                            className="h-8 rounded-md border border-slate-200 bg-white px-3 text-xs text-slate-500 transition hover:bg-slate-100"
                          >
                            取消
                          </button>
                          <button
                            onClick={handleUpdateNote}
                            disabled={savingEditId === note.quicknote_id}
                            className="h-8 rounded-md bg-slate-800 px-3 text-xs font-medium text-white transition hover:bg-slate-900 disabled:opacity-40"
                          >
                            {savingEditId === note.quicknote_id ? '保存中...' : '保存分类'}
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <button onClick={() => beginEdit(note)} className="block w-full rounded-md p-1 text-left transition hover:bg-slate-50">
                      <p className="line-clamp-2 text-sm text-slate-700 leading-snug">{note.raw_text}</p>
                      <p className="mt-1 text-[10px] text-slate-400">
                        {relativeTime(note.created_at)} · {note.target_page ?? '草池'} · {note.category ?? '待分类'} · {reviewLabel(note)} · {promotionLabel(note)}
                      </p>
                    </button>
                  )}
                </li>
              ))}
            </ul>
            {notes.length > 8 && (
              <button className="mt-4 text-xs text-slate-400 hover:text-slate-600 transition-colors">
                查看全部草池 ({notes.length}) →
              </button>
            )}
          </div>
        ) : (
          <div className="flex h-40 flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50 text-center">
            <p className="text-sm font-medium text-slate-500">暂无速记</p>
            <p className="mt-1 text-xs text-slate-400">写半句话也可以，系统会先原样保存。</p>
          </div>
        )}
      </section>
    </div>
  );
}
