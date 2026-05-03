'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import type { QuickNote, CreateQuickNoteRequest, ListQuickNotesResponse } from '@/types/quick_note';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8001';

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

export function QuickNoteInbox() {
  const [text, setText] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [notes, setNotes] = useState<QuickNote[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const fetchNotes = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/v1/quick-notes?hours=24&limit=20`);
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
    };

    setNotes((prev) => [optimisticNote, ...prev]);
    setText('');
    textareaRef.current?.focus();

    try {
      const body: CreateQuickNoteRequest = { raw_text: trimmed, source: 'web' };
      const res = await fetch(`${API_BASE}/v1/quick-notes`, {
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
            ? { ...optimisticNote, quicknote_id: saved.quicknote_id, created_at: saved.created_at }
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

  return (
    <div className="border-b border-slate-200 bg-white px-6 py-4 shrink-0">
      <textarea
        ref={textareaRef}
        autoFocus
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="随手记一条想法…"
        rows={3}
        className="w-full resize-none rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 placeholder:text-slate-400 outline-none focus:border-slate-400 focus:bg-white transition-colors leading-relaxed"
      />

      <div className="mt-2 flex items-center justify-between">
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

      {notes.length > 0 && (
        <div className="mt-4 space-y-0">
          <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-slate-400">
            最近 24 小时
          </p>
          <ul className="space-y-2">
            {notes.slice(0, 5).map((note) => (
              <li key={note.quicknote_id} className="group">
                <p className="line-clamp-2 text-sm text-slate-700 leading-snug">{note.raw_text}</p>
                <p className="mt-0.5 text-[10px] text-slate-400">
                  {relativeTime(note.created_at)} · 草池 · 待分类
                </p>
              </li>
            ))}
          </ul>
          {notes.length > 5 && (
            <button className="mt-2 text-xs text-slate-400 hover:text-slate-600 transition-colors">
              查看全部速记 ({notes.length}) →
            </button>
          )}
        </div>
      )}
    </div>
  );
}
