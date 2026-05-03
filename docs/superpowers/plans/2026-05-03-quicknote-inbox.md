# QuickNote Inbox (硅基分身速记入口) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a zero-friction quick-capture area (速记草池) to the 硅基分身 section, backed by a SQLite REST API — Phase A only (save + list, no AI).

**Architecture:** Add `QuickNoteRow` to the existing SQLAlchemy `Base` in `database.py`, new `quick_note_routes.py` with two endpoints (POST create, GET list), register the router in `server.py`, then build a self-contained `QuickNoteInbox.tsx` React component and mount it inside `CockpitPanel.tsx`'s `case 'knowledge':` branch.

**Tech Stack:** Python SQLAlchemy/SQLite, FastAPI, React 18, TypeScript, Tailwind CSS

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `intelligent_project_analyzer/advisor/database.py` | Add `QuickNoteRow` class + import `Boolean` |
| Create | `intelligent_project_analyzer/api/quick_note_routes.py` | POST /v1/quick-notes, GET /v1/quick-notes |
| Modify | `intelligent_project_analyzer/api/server.py` | Register quick_note_router |
| Create | `tests/advisor/test_quick_note_api.py` | API tests |
| Create | `frontend-nextjs/types/quick_note.ts` | TS types |
| Create | `frontend-nextjs/components/project-cockpit/QuickNoteInbox.tsx` | Capture UI component |
| Modify | `frontend-nextjs/components/CockpitPanel.tsx` | Mount QuickNoteInbox in knowledge branch |

---

## Task 1: Add QuickNoteRow to the database model

**Files:**
- Modify: `intelligent_project_analyzer/advisor/database.py:6` (sqlalchemy import line)
- Modify: `intelligent_project_analyzer/advisor/database.py` (add class after AuditLogRow)

- [ ] **Step 1: Write the failing test**

Create `tests/advisor/test_quick_note_api.py`:

```python
import pytest
from sqlalchemy import create_engine, inspect
from intelligent_project_analyzer.advisor.database import Base


def test_quick_note_table_exists_in_metadata():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    assert "quick_notes" in inspector.get_table_names()


def test_quick_note_table_has_required_columns():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("quick_notes")}
    assert "quicknote_id" in columns
    assert "raw_text" in columns
    assert "created_at" in columns
    assert "source" in columns
    assert "status" in columns
    assert "original_preserved" in columns
```

- [ ] **Step 2: Run test to verify it fails**

```
cd d:\11-20\2026.2.25\langgraph-design
python -m pytest tests/advisor/test_quick_note_api.py::test_quick_note_table_exists_in_metadata -v
```

Expected: FAIL — `AssertionError: assert 'quick_notes' in ...`

- [ ] **Step 3: Add Boolean to the sqlalchemy import in database.py**

In `intelligent_project_analyzer/advisor/database.py`, line 6, change:

```python
from sqlalchemy import create_engine, Column, String, DateTime, Text, Engine
```

to:

```python
from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean, Engine
```

- [ ] **Step 4: Add QuickNoteRow class after AuditLogRow in database.py**

After the `AuditLogRow` class (around line 82), add:

```python
class QuickNoteRow(Base):
    __tablename__ = "quick_notes"
    quicknote_id = Column(String, primary_key=True)
    raw_text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
    source = Column(String, nullable=False, default="web")
    status = Column(String, nullable=False, default="raw")
    original_preserved = Column(Boolean, nullable=False, default=True)
```

- [ ] **Step 5: Run tests to verify they pass**

```
python -m pytest tests/advisor/test_quick_note_api.py -v
```

Expected: 2 PASSED

- [ ] **Step 6: Commit**

```
git add intelligent_project_analyzer/advisor/database.py tests/advisor/test_quick_note_api.py
git commit -m "feat: 新增 QuickNoteRow 数据表模型"
```

---

## Task 2: Create quick_note_routes.py

**Files:**
- Create: `intelligent_project_analyzer/api/quick_note_routes.py`
- Modify: `tests/advisor/test_quick_note_api.py` (add API tests)

- [ ] **Step 1: Write the failing API tests**

Append to `tests/advisor/test_quick_note_api.py`:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient
from intelligent_project_analyzer.api.quick_note_routes import router

api_app = FastAPI()
api_app.include_router(router)
client = TestClient(api_app)


def test_create_quick_note_returns_201():
    response = client.post("/v1/quick-notes", json={"raw_text": "测试速记内容"})
    assert response.status_code == 201
    data = response.json()
    assert "quicknote_id" in data
    assert data["status"] == "raw"
    assert "created_at" in data


def test_create_quick_note_empty_text_returns_400():
    response = client.post("/v1/quick-notes", json={"raw_text": "   "})
    assert response.status_code == 400


def test_create_quick_note_missing_text_returns_422():
    response = client.post("/v1/quick-notes", json={})
    assert response.status_code == 422


def test_list_quick_notes_returns_200():
    response = client.get("/v1/quick-notes")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)


def test_list_quick_notes_includes_just_created():
    client.post("/v1/quick-notes", json={"raw_text": "列表测试内容"})
    response = client.get("/v1/quick-notes?hours=24&limit=20")
    texts = [item["raw_text"] for item in response.json()["items"]]
    assert "列表测试内容" in texts
```

- [ ] **Step 2: Run tests to verify they fail**

```
python -m pytest tests/advisor/test_quick_note_api.py::test_create_quick_note_returns_201 -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'intelligent_project_analyzer.api.quick_note_routes'`

- [ ] **Step 3: Create quick_note_routes.py**

Create `intelligent_project_analyzer/api/quick_note_routes.py`:

```python
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import desc

from intelligent_project_analyzer.advisor.database import init_db, get_session, QuickNoteRow

router = APIRouter()
_engine = init_db()


class CreateQuickNoteRequest(BaseModel):
    raw_text: str
    source: str = "web"


@router.post("/v1/quick-notes", status_code=201)
async def create_quick_note(req: CreateQuickNoteRequest):
    if not req.raw_text.strip():
        raise HTTPException(status_code=400, detail="raw_text cannot be empty")
    note_id = str(uuid.uuid4())
    now = datetime.utcnow()
    row = QuickNoteRow(
        quicknote_id=note_id,
        raw_text=req.raw_text,
        created_at=now,
        source=req.source,
        status="raw",
        original_preserved=True,
    )
    with get_session(_engine) as session:
        session.add(row)
    return {"quicknote_id": note_id, "created_at": now.isoformat() + "Z", "status": "raw"}


@router.get("/v1/quick-notes")
async def list_quick_notes(hours: int = 24, limit: int = 20):
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    with get_session(_engine) as session:
        rows = (
            session.query(QuickNoteRow)
            .filter(QuickNoteRow.created_at >= cutoff)
            .order_by(desc(QuickNoteRow.created_at))
            .limit(limit)
            .all()
        )
        items = [
            {
                "quicknote_id": r.quicknote_id,
                "raw_text": r.raw_text,
                "created_at": r.created_at.isoformat() + "Z",
                "source": r.source,
                "status": r.status,
            }
            for r in rows
        ]
    return {"items": items}
```

- [ ] **Step 4: Run all API tests**

```
python -m pytest tests/advisor/test_quick_note_api.py -v
```

Expected: 7 PASSED (2 model tests + 5 API tests)

- [ ] **Step 5: Commit**

```
git add intelligent_project_analyzer/api/quick_note_routes.py tests/advisor/test_quick_note_api.py
git commit -m "feat: 新增速记草池 REST 端点 POST/GET /v1/quick-notes"
```

---

## Task 3: Register router in server.py

**Files:**
- Modify: `intelligent_project_analyzer/api/server.py` (after advisor_routes block, ~line 1017)

- [ ] **Step 1: Find the advisor_routes block in server.py**

```
grep -n "advisor_routes\|Advisor API" intelligent_project_analyzer/api/server.py
```

Expected output includes lines like:
```
1010: #  Phase A: Advisor API 路由
1012:     from intelligent_project_analyzer.api.advisor_routes import router as advisor_router
1014:     app.include_router(advisor_router)
1015:     logger.info("✅ Advisor API 路由已注册 ...")
1017:     logger.warning(f"⚠️ Advisor API 路由加载失败: {e}")
```

- [ ] **Step 2: Add quick_note_router registration after the advisor block**

After line 1017 (the `except` of the advisor block), add:

```python
#  Phase A: QuickNote 草池路由
try:
    from intelligent_project_analyzer.api.quick_note_routes import router as quick_note_router

    app.include_router(quick_note_router)
    logger.info("✅ QuickNote 草池路由已注册 (POST/GET /v1/quick-notes)")
except Exception as e:
    logger.warning(f"⚠️ QuickNote 草池路由加载失败: {e}")
```

- [ ] **Step 3: Verify routes are visible (server must be running)**

If the backend server is running:

```
curl http://127.0.0.1:8001/docs | grep -i quick
```

Or open `http://127.0.0.1:8001/docs` in a browser and search for `quick-notes`.

Expected: Two entries — `POST /v1/quick-notes` and `GET /v1/quick-notes`.

If server is not running, skip this step and verify after Task 6.

- [ ] **Step 4: Commit**

```
git add intelligent_project_analyzer/api/server.py
git commit -m "feat: 注册 QuickNote 草池路由到主服务"
```

---

## Task 4: Create frontend TypeScript types

**Files:**
- Create: `frontend-nextjs/types/quick_note.ts`

- [ ] **Step 1: Create the types file**

Create `frontend-nextjs/types/quick_note.ts`:

```typescript
export type QuickNoteSource = 'web' | 'qclaw_wechat' | 'mobile';
export type QuickNoteStatus = 'raw' | 'tagged' | 'suggested' | 'routed' | 'archived';

export interface QuickNote {
  quicknote_id: string;
  raw_text: string;
  created_at: string;
  source: QuickNoteSource;
  status: QuickNoteStatus;
}

export interface CreateQuickNoteRequest {
  raw_text: string;
  source?: QuickNoteSource;
}

export interface ListQuickNotesResponse {
  items: QuickNote[];
}
```

- [ ] **Step 2: Verify no TypeScript errors**

```
cd frontend-nextjs
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors related to `quick_note.ts`

- [ ] **Step 3: Commit**

```
git add frontend-nextjs/types/quick_note.ts
git commit -m "feat: 新增 QuickNote TypeScript 类型定义"
```

---

## Task 5: Create QuickNoteInbox component

**Files:**
- Create: `frontend-nextjs/components/project-cockpit/QuickNoteInbox.tsx`

- [ ] **Step 1: Create the component**

Create `frontend-nextjs/components/project-cockpit/QuickNoteInbox.tsx`:

```tsx
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
```

- [ ] **Step 2: Verify TypeScript compiles**

```
cd frontend-nextjs
npx tsc --noEmit 2>&1 | grep -i "quick_note\|QuickNote"
```

Expected: no output (no errors)

- [ ] **Step 3: Commit**

```
git add frontend-nextjs/components/project-cockpit/QuickNoteInbox.tsx
git commit -m "feat: 新增 QuickNoteInbox 速记草池组件"
```

---

## Task 6: Mount QuickNoteInbox in CockpitPanel

**Files:**
- Modify: `frontend-nextjs/components/CockpitPanel.tsx`

- [ ] **Step 1: Find the exact insertion point**

```
grep -n "可滚动内容区\|flex-1 min-h-0 overflow-y-auto" frontend-nextjs/components/CockpitPanel.tsx
```

Expected output:
```
9796:              {/* 可滚动内容区：上方气泡图 + 下方左列表/右洞察 */}
9797:              <div className="flex-1 min-h-0 overflow-y-auto">
```

The insertion point is **between line 9794 (closing `</div>` of the header) and line 9796 (comment before scrollable content)**.

- [ ] **Step 2: Add the import at the top of CockpitPanel.tsx**

Find the last import line in CockpitPanel.tsx:

```
grep -n "^import" frontend-nextjs/components/CockpitPanel.tsx | tail -5
```

After the last import statement, add:

```tsx
import { QuickNoteInbox } from '@/components/project-cockpit/QuickNoteInbox';
```

- [ ] **Step 3: Insert QuickNoteInbox between header and scrollable content**

In `CockpitPanel.tsx`, find the comment `{/* 可滚动内容区：上方气泡图 + 下方左列表/右洞察 */}` and the line just before it (which is a `</div>` closing the header). Insert `<QuickNoteInbox />` between them:

Find this exact block (around line 9793–9797):

```tsx
					</div>
				</div>

				{/* 可滚动内容区：上方气泡图 + 下方左列表/右洞察 */}
				<div className="flex-1 min-h-0 overflow-y-auto">
```

Replace with:

```tsx
					</div>
				</div>

				<QuickNoteInbox />

				{/* 可滚动内容区：上方气泡图 + 下方左列表/右洞察 */}
				<div className="flex-1 min-h-0 overflow-y-auto">
```

- [ ] **Step 4: Verify TypeScript compiles**

```
cd frontend-nextjs
npx tsc --noEmit 2>&1 | head -30
```

Expected: no new errors (ignore pre-existing errors if any)

- [ ] **Step 5: Verify in browser**

1. Start the backend server (if not running): `python intelligent_project_analyzer/api/server.py`
2. Start the frontend: `npm run dev` in `frontend-nextjs/`
3. Open `http://localhost:3001/analysis/demo`
4. Click "我的硅基分身" in the left nav
5. Verify: speed record text box appears at top, below the header tabs
6. Type a note and click "保存到草池" — verify the text box clears and the note appears in the list below
7. Type another note and press ⌘+Enter (or Ctrl+Enter) — verify it saves

- [ ] **Step 6: Commit**

```
git add frontend-nextjs/components/CockpitPanel.tsx
git commit -m "feat: 在硅基分身首屏挂载速记草池入口"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by task |
|-----------------|----------------|
| 速记入口常驻首屏，高于3 Tab | Task 6 — mounted between header and scrollable content |
| 文本框 C 位，autoFocus | Task 5 — `autoFocus` on textarea |
| 保存按钮文案"保存到草池" | Task 5 |
| ⌘+Enter / Ctrl+Enter 快速保存 | Task 5 — `handleKeyDown` |
| 保存后清空文本框，焦点留在框内 | Task 5 — `setText('')` + `textareaRef.current?.focus()` |
| 乐观更新（不等 GET 刷新） | Task 5 — `setNotes(prev => [optimisticNote, ...prev])` |
| 最近 24h 条目展示 | Task 5 — renders `notes.slice(0, 5)` |
| 相对时间显示 | Task 5 — `relativeTime()` |
| "草池 · 待分类"状态标签 | Task 5 |
| L0 保存（不调 Advisor） | Task 2 — route calls only SQLAlchemy, no LangGraph |
| raw_text 只读（无 UPDATE 端点） | Task 2 — only POST (create) and GET (list) |
| source 字段存储 | Task 1 + Task 2 |
| status 字段初始为 raw | Task 2 — hardcoded `status="raw"` |
| original_preserved 恒为 true | Task 1 + Task 2 |
| 后端 SQLite 存储 | Task 1 + Task 2 |
| 路由注册到主服务 | Task 3 |
| TypeScript 类型定义 | Task 4 |

**Placeholder scan:** None found.

**Type consistency:** `QuickNote` defined in Task 4, imported in Task 5. `QuickNoteInbox` defined in Task 5, imported in Task 6. All field names consistent across tasks.
