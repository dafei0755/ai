# Bug Fix v7.270.1: Search Mainline Blank Content

## Problem Description

The search mainline (搜索主线) was displaying numbered items (1, 2, 3...) but with blank content. Users could see the numbers but not the actual task descriptions.

**Affected Session**: `search-20260125-b8919ca6d418`

## Root Cause

Data structure mismatch between backend and frontend:

### Backend Generated (v7.270 Fallback Path)
```json
{
  "main_directions": [
    {
      "id": "T1",
      "name": "如何将HAY的About A Chair系列融入峨眉山七里坪的室内设计",
      "description": "",
      "priority": 2
    }
  ]
}
```

### Frontend Expected
```typescript
{
  "main_directions": [
    {
      "direction": "...",
      "purpose": "...",
      "expected_outcome": "..."
    }
  ]
}
```

The backend's v7.270 fallback method (`_generate_framework_checklist()` at line 11020) was generating the old data structure with `id`, `name`, `description` fields, while the frontend was looking for `direction`, `purpose`, `expected_outcome` fields.

## Solution

### 1. Backend Fix (Primary)
**File**: `intelligent_project_analyzer/services/ucppt_search_engine.py`
**Lines**: 11032-11067

Updated the fallback method to generate the correct data structure:

```python
# Before (wrong):
direction = {
    "id": t.id,
    "name": t.name or t.question,
    "description": t.search_for or t.description,
    "priority": t.priority,
}

# After (correct):
direction = {
    "direction": t.name or t.question or t.search_for or "未命名任务",
    "purpose": t.why_need or t.purpose or t.description or "",
    "expected_outcome": ", ".join(t.success_when[:2]) if hasattr(t, 'success_when') and t.success_when else "",
    "sub_tasks": [],
    "motivation_tag": "",
    "motivation_id": None,
    "motivation_color": "#808080",
    "priority": t.priority,
    "target_id": t.id,
}
```

### 2. Frontend Fix (Backward Compatibility)
**File**: `frontend-nextjs/app/search/[session_id]/page.tsx`

#### TypeScript Interface Update (Lines 85-96)
Added optional fields for backward compatibility:

```typescript
interface FrameworkChecklist {
  core_summary: string;
  main_directions: Array<{
    direction?: string;
    purpose?: string;
    expected_outcome?: string;
    // 向后兼容字段
    name?: string;
    description?: string;
  }>;
  // ...
}
```

#### Display Logic Update (Lines 579-584)
Added fallback logic to handle both old and new data structures:

```typescript
<div className="text-sm font-medium text-gray-800 dark:text-gray-200">
  {direction.direction || direction.name || "未命名任务"}
</div>
{(direction.purpose || direction.description) && (
  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
    <span className="text-indigo-500 dark:text-indigo-400">目的:</span>
    {direction.purpose || direction.description}
  </div>
)}
```

## Impact

- **Fixed**: New search sessions will generate correct data structure
- **Backward Compatible**: Old sessions with legacy data structure will still display correctly
- **Consistent**: Both v7.263 enhanced path and v7.270 fallback path now generate the same structure

## Testing

1. ✅ Backend generates correct data structure with all required fields
2. ✅ Frontend displays both new and old data structures correctly
3. ✅ TypeScript types updated to support both formats

## Files Modified

1. `intelligent_project_analyzer/services/ucppt_search_engine.py` (Lines 11032-11067)
2. `frontend-nextjs/app/search/[session_id]/page.tsx` (Lines 85-96, 579-584)

## Version

- **Version**: v7.270.1
- **Date**: 2026-01-25
- **Type**: Bug Fix
- **Priority**: High (User-facing display issue)

## Related Issues

- Session `search-20260125-b8919ca6d418` exhibited this issue
- Issue started appearing recently when v7.270 fallback path was used
- v7.263 enhanced path was working correctly
