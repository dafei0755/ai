# QuickNote Inbox (硅基分身速记入口) Implementation Spec

**Goal:** Add a zero-friction quick-capture area to the 硅基分身 section of the analysis page, backed by a SQLite REST API.

**Architecture:** New SQLModel table + 2 FastAPI endpoints + 1 React component wired into the analysis page's `knowledge` nav branch.

**Tech Stack:** Python SQLModel/SQLite, FastAPI, React/TypeScript, Tailwind CSS

**Source design doc:** `sf/2026.4.18/5 硅基分身/01-硅基分身速记入口设计-2026-05-03.md`

---

## Files

### New files
- `intelligent_project_analyzer/advisor/quick_note_models.py` — SQLModel table
- `intelligent_project_analyzer/api/quick_note_routes.py` — POST + GET endpoints
- `frontend-nextjs/types/quick_note.ts` — TS types
- `frontend-nextjs/components/project-cockpit/QuickNoteInbox.tsx` — capture UI component

### Modified files
- `intelligent_project_analyzer/api/server.py` — register new router
- `frontend-nextjs/app/analysis/[sessionId]/page.tsx` — mount QuickNoteInbox in knowledge view

---

## Backend

### QuickNote model (`quick_note_models.py`)

```python
from sqlmodel import SQLModel, Field
from datetime import datetime
import uuid

class QuickNote(SQLModel, table=True):
    __tablename__ = "quick_notes"
    quicknote_id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    raw_text: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(default="web")        # web | qclaw_wechat | mobile
    status: str = Field(default="raw")        # raw only in Phase A
    original_preserved: bool = Field(default=True)
```

Table created via `SQLModel.metadata.create_all(engine)` in the same `init_db()` call used by advisor routes. No migration tooling needed for Phase A.

### Routes (`quick_note_routes.py`)

**POST /v1/quick-notes**
- Request: `{ raw_text: str, source?: str = "web" }`
- Validates `raw_text` is non-empty (400 if empty)
- Writes one row, returns `{ quicknote_id, created_at, status: "raw" }`
- No AI, no background tasks — target latency < 50ms

**GET /v1/quick-notes**
- Query params: `hours: int = 24`, `limit: int = 20`
- Returns notes where `created_at >= now - hours`, ordered by `created_at DESC`
- Response: `{ items: QuickNote[] }`

### server.py change

```python
from intelligent_project_analyzer.api.quick_note_routes import router as quick_note_router
app.include_router(quick_note_router)
```

---

## Frontend

### Types (`quick_note.ts`)

```typescript
export interface QuickNote {
  quicknote_id: string;
  raw_text: string;
  created_at: string;       // ISO 8601
  source: 'web' | 'qclaw_wechat' | 'mobile';
  status: 'raw' | 'tagged' | 'suggested' | 'routed' | 'archived';
}

export interface CreateQuickNoteRequest {
  raw_text: string;
  source?: QuickNote['source'];
}
```

### QuickNoteInbox component

**Props:** none (self-contained, fetches own data)

**Layout:**
```
[textarea — autoFocus, placeholder="随手记一条想法…"]
                              [保存到草池]  (⌘+Enter)

── 最近 24 小时 ──────────────
· raw_text (truncated to 2 lines)
  2小时前 · 草池 · 待分类

· ...
```

**Behavior:**
- `autoFocus` on mount — user can type immediately
- Save button disabled when `raw_text.trim() === ''` or `isSaving === true`
- `Cmd+Enter` / `Ctrl+Enter` triggers save
- On save success: clear textarea, keep focus, **optimistic prepend** new item to list (no GET refetch)
- On save error: show inline error, restore text
- Fetch recent notes on mount via `GET /v1/quick-notes?hours=24&limit=20`
- Time display: relative ("2小时前") using `Intl.RelativeTimeFormat`
- Status badge: always "草池 · 待分类" in Phase A

### Analysis page integration

In the `primaryNav === 'knowledge'` render branch, add `<QuickNoteInbox />` above the existing DSS sub-tab content:

```tsx
{primaryNav === 'knowledge' && (
  <div className="flex flex-col h-full">
    <QuickNoteInbox />
    <div className="shrink-0 border-t border-white/8">
      {/* existing dssPage tab bar */}
    </div>
    <div className="flex-1 overflow-auto">
      {/* existing dssPage content */}
    </div>
  </div>
)}
```

---

## Phase boundary

This spec covers **Phase A only**:
- ✅ Save raw text, status=`raw`, source=`web`
- ✅ List recent 24h notes
- ❌ No AI tagging (Phase B)
- ❌ No background classification (Phase B)
- ❌ No QClaw source injection (Phase C)
- ❌ No Advisor consumption (Phase D)
- ❌ No 7-day archiving job (Phase C)

The `status` and `source` fields are stored now so Phase B/C can extend without schema breaking changes.

---

## Constraints

- `raw_text` is write-once. No UPDATE endpoint is provided.
- `original_preserved` is always `true` — hardcoded, not user-settable.
- Save latency must be < 200ms on localhost.
- The component must not import or call `AdvisorAgent` or any LangGraph workflow.
