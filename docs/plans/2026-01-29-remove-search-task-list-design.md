# Design: Remove SearchTaskListCard and Consolidate into FrameworkChecklistCard

**Date**: 2026-01-29
**Status**: Implementation Ready
**Context**: User feedback indicates that SearchTaskListCard and FrameworkChecklistCard display redundant information

## Problem Statement

Currently, the search page displays two separate components:

1. **FrameworkChecklistCard** - Shows search framework with main directions, boundaries, and answer goals
2. **SearchTaskListCard** - Shows task list with progress tracking, priority labels, and completion status

These two components display overlapping information:
- Both show search directions/tasks
- Both indicate what needs to be searched
- Both display the core question/summary

This creates visual clutter and confuses users about which component to focus on.

## Analysis

### Current Data Flow

```
Backend (ucppt_search_engine.py)
├── SearchFramework (execution layer)
│   ├── targets: List[SearchTarget]  ← Used for actual search execution
│   └── framework_checklist: FrameworkChecklist  ← Generated for display
│
└── SSE Events
    ├── search_framework_ready
    │   ├── targets → converted to SearchMasterLine (for SearchTaskListCard)
    │   └── framework_checklist → FrameworkChecklist (for FrameworkChecklistCard)
    │
    └── task_progress → Updates SearchTaskListCard progress bars
```

### Component Comparison

| Feature | FrameworkChecklistCard | SearchTaskListCard |
|---------|----------------------|-------------------|
| **Data Source** | `frameworkChecklist` | `searchMasterLine` (converted from targets) |
| **Display** | Main directions with purpose | Tasks with progress tracking |
| **Editable** | ✅ Yes (before search starts) | ❌ No |
| **Progress** | ❌ No | ✅ Yes (completion scores, status icons) |
| **Priority** | ❌ No | ✅ Yes (P1/P2/P3 labels) |
| **Boundaries** | ✅ Yes | ❌ No |
| **Answer Goal** | ✅ Yes | ❌ No |
| **Deep Analysis** | ✅ Yes (user context, entities, tension) | ❌ No |

### Key Insight

According to [FRAMEWORK_CHECKLIST_DATA_FLOW_ANALYSIS.md](../../FRAMEWORK_CHECKLIST_DATA_FLOW_ANALYSIS.md):

> **FrameworkChecklist is the display layer abstraction**
> - Derived from `SearchFramework.targets`
> - Used for frontend-friendly display
> - Editing does not affect actual execution (currently)

The SearchTaskListCard was introduced in v7.208 as a "macro-level task tracker" but creates redundancy with FrameworkChecklistCard introduced in v7.240.

## Decision

**Remove SearchTaskListCard entirely and enhance FrameworkChecklistCard to include progress tracking.**

### Rationale

1. **Single Source of Truth**: FrameworkChecklistCard already contains all the search directions
2. **Better UX**: One unified component is clearer than two overlapping ones
3. **Editability**: FrameworkChecklistCard supports editing (v7.285), SearchTaskListCard doesn't
4. **Rich Context**: FrameworkChecklistCard includes boundaries, answer goals, and deep analysis
5. **Simpler Codebase**: Removes ~200 lines of redundant code

## Implementation Plan

### Phase 1: Frontend Cleanup ✅

**Files to Modify:**
- `frontend-nextjs/app/search/[session_id]/page.tsx`

**Changes:**

1. **Remove Type Definitions** (lines 95-115)
   ```typescript
   // DELETE: SearchTask interface
   // DELETE: SearchMasterLine interface
   // DELETE: TaskProgress interface
   ```

2. **Remove SearchTaskListCard Component** (lines 457-575)
   ```typescript
   // DELETE: Entire SearchTaskListCard component definition
   ```

3. **Remove State Variables** (line 1656)
   ```typescript
   // DELETE: const [taskListExpanded, setTaskListExpanded] = useState(true);
   ```

4. **Remove from SearchState Interface** (lines 255-256)
   ```typescript
   // DELETE: searchMasterLine: SearchMasterLine | null;
   // DELETE: taskProgress: Record<string, TaskProgress>;
   ```

5. **Remove State Initialization** (lines 1625-1626)
   ```typescript
   // DELETE: searchMasterLine: null,
   // DELETE: taskProgress: {},
   ```

6. **Remove SSE Event Handlers**
   - Line 2816-2823: `search_master_line_ready` event
   - Line 2827-2893: `search_framework_ready` event (simplify, remove masterLine conversion)
   - Line 2974-2988: `task_progress` event

7. **Remove Rendering** (lines 4267-4275)
   ```typescript
   // DELETE: SearchTaskListCard rendering block
   ```

8. **Remove from Session Save/Restore**
   - Line 1721: Remove `searchMasterLine` from save
   - Line 1838-1839: Remove from restore
   - Line 2165-2166: Remove from reset

### Phase 2: Backend Cleanup (Optional)

**Note**: Backend SearchMasterLine is marked as DEPRECATED (v7.282) but kept for compatibility. We can optionally remove:

**Files to Consider:**
- `intelligent_project_analyzer/services/ucppt_search_engine.py`

**Deprecated Code** (lines 1769-2034):
- `SearchTask` class
- `SearchMasterLine` class
- `SearchMasterLine.from_dict()` method
- `SearchFramework.to_master_line()` method (line 918-955)

**SSE Event Generation:**
- Remove `master_line` field from `search_framework_ready` event
- Remove `search_master_line_ready` event emission
- Remove `task_progress` event emission

**Decision**: Keep backend code for now to maintain API compatibility with older frontend versions. Mark for removal in v8.0.

### Phase 3: Documentation Updates

**Files to Update:**
- `CHANGELOG.md` - Add removal notice
- `IMPLEMENTATION_v7.208_SEARCH_TASK_LIST.md` - Mark as deprecated
- `BUG_FIX_v7.290_SEARCH_PAGE_ARCHITECTURE.md` - Update architecture diagram

## Migration Guide

### For Users

No action required. The search functionality remains the same, just with a cleaner interface.

### For Developers

If you have custom code that references:
- `SearchTaskListCard` component → Use `FrameworkChecklistCard` instead
- `searchMasterLine` state → Use `frameworkChecklist.main_directions` instead
- `taskProgress` state → Progress tracking will be added to FrameworkChecklistCard in future

## Future Enhancements

After removing SearchTaskListCard, we can enhance FrameworkChecklistCard with:

1. **Progress Indicators** - Add completion status icons to each direction
2. **Priority Labels** - Show P1/P2/P3 priority for each direction
3. **Real-time Updates** - Update completion scores as search progresses
4. **Collapsible Sections** - Allow expanding/collapsing individual directions

These enhancements can be added incrementally without affecting the core functionality.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Users miss progress tracking | Medium | Add progress indicators to FrameworkChecklistCard |
| Breaking change for API consumers | Low | Backend keeps compatibility layer |
| Loss of task-level granularity | Low | FrameworkChecklist already has same granularity |

## Success Criteria

- ✅ SearchTaskListCard component removed from codebase
- ✅ No visual regression in search page
- ✅ FrameworkChecklistCard displays all necessary information
- ✅ No console errors or warnings
- ✅ Existing search sessions load correctly

## References

- [FRAMEWORK_CHECKLIST_DATA_FLOW_ANALYSIS.md](../../FRAMEWORK_CHECKLIST_DATA_FLOW_ANALYSIS.md)
- [IMPLEMENTATION_v7.208_SEARCH_TASK_LIST.md](../../IMPLEMENTATION_v7.208_SEARCH_TASK_LIST.md)
- [IMPLEMENTATION_REPORT_v7.300_COMPLETE.md](../../IMPLEMENTATION_REPORT_v7.300_COMPLETE.md)
