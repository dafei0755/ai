# 搜索框架清单数据流分析报告

> v7.280 - 2026-01-25

## 📋 概述

本报告详细分析**搜索框架清单(FrameworkChecklist)**与前后步骤的数据传递关系，以及搜索执行中的贯彻机制。

---

## 🏗️ 核心数据结构

### 1. SearchFramework（搜索框架）- 主体结构

```python
@dataclass
class SearchFramework:
    # === 问题锚点 ===
    original_query: str           # 原始用户问题
    core_question: str            # 问题一句话本质
    answer_goal: str              # 回答目标
    boundary: str                 # 搜索边界（不搜什么）

    # === 搜索目标列表 ===
    targets: List[SearchTarget]   # ⭐ 核心：实际执行的搜索任务

    # === 深度分析结果 ===
    l1_facts: List[str]           # L1 事实解构
    l2_models: Dict[str, str]     # L2 多视角建模
    l3_tension: str               # L3 核心张力
    l4_jtbd: str                  # L4 用户任务
    l5_sharpness: Dict[str, Any]  # L5 锐度评估

    # === v7.240: 框架清单 ===
    framework_checklist: Optional[FrameworkChecklist]  # 📋 前端展示用
```

### 2. SearchTarget（搜索目标）- 执行单元

```python
@dataclass
class SearchTarget:
    id: str                       # 目标ID (T1, T2, ...)

    # === v7.236: 语义明确字段 ===
    question: str                 # 要回答什么问题？（问句形式）
    search_for: str               # 具体搜索什么内容
    why_need: str                 # 找到后对回答有什么帮助
    success_when: List[str]       # 什么情况算搜索成功

    # === 进度追踪 ===
    status: str                   # pending/searching/complete
    completion_score: float       # 完成度 0.0-1.0
    collected_info: List[str]     # 已收集的信息
```

### 3. FrameworkChecklist（框架清单）- 展示层

```python
@dataclass
class FrameworkChecklist:
    core_summary: str             # 核心问题摘要
    main_directions: List[Dict]   # 搜索主线方向（用于前端展示）
    boundaries: List[str]         # 搜索边界
    answer_goal: str              # 回答目标

    # === v7.260 深度分析摘要 ===
    user_context: Dict            # 用户画像
    key_entities: List[Dict]      # 关键实体
    analysis_perspectives: List   # 分析视角
    core_tension: Dict            # 核心张力
    user_task: Dict               # 用户任务（JTBD）
```

---

## 🔄 数据流向图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Step 1: 需求理解与深度分析                      │
│  用户问题 → L0对话 → L1-L5深度分析 → 生成 SearchFramework                 │
│                                           │                              │
│                                           ▼                              │
│                              framework.targets (主体)                    │
│                              framework.framework_checklist (展示)        │
└─────────────────────────────────────────────────────────────────────────┘
                                           │
                                           │ SSE: search_framework_ready
                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           前端接收与展示                                  │
│                                                                          │
│   FrameworkChecklistCard ← framework_checklist (仅展示)                  │
│   SearchTaskListCard ← targets → 转换为 SearchMasterLine (展示)          │
│                                                                          │
│   ⚠️ 关键问题：checklist 编辑不影响实际 targets                           │
└─────────────────────────────────────────────────────────────────────────┘
                                           │
                                           │ 搜索开始（自动）
                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Step 2: 渐进式搜索                              │
│                                                                          │
│   while current_round < max_rounds:                                      │
│       target = framework.get_target_for_round(current_round)             │
│       # 执行搜索...                                                       │
│       # 更新 target.completion_score                                      │
│       # 可能触发动态延展                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📍 关键数据节点分析

### 节点 1: 框架生成 (Step 1 完成时)

**文件**: `ucppt_search_engine.py`
**位置**: `_execute_step1_analysis()` 或 `_execute_combined_step1_step2()`

```python
# 生成搜索框架（包含 targets）
framework = SearchFramework(
    original_query=query,
    core_question=data.get("core_question", ""),
    answer_goal=data.get("answer_goal", ""),
    targets=[...],  # ⭐ 从 LLM 响应解析
)

# 生成框架清单（从 framework 派生）
framework_checklist = self._generate_framework_checklist(framework, analysis_data)
framework.framework_checklist = framework_checklist

# 发送 SSE 事件
yield {
    "type": "search_framework_ready",
    "data": {
        "targets": [t.to_dict() for t in framework.targets],
        "framework_checklist": framework_checklist.to_dict(),
    },
    "_internal_framework": framework,  # ⭐ 后续搜索使用此对象
}
```

### 节点 2: 前端接收与展示

**文件**: `page.tsx`
**位置**: SSE 事件处理 `handleSSEEvent()`

```typescript
case 'search_framework_ready':
    // 转换 targets 为 tasks 格式（用于 SearchTaskListCard）
    const tasks = targets.map((t) => ({...}));

    // 提取框架清单（用于 FrameworkChecklistCard）
    const frameworkChecklist = data.framework_checklist ? {...} : null;

    setSearchState(prev => ({
        ...prev,
        searchMasterLine: masterLine,      // 任务列表展示
        frameworkChecklist: frameworkChecklist,  // 框架清单展示
        awaitingConfirmation: true,        // v7.280: 允许编辑
    }));
```

**⚠️ 当前问题**:
- `frameworkChecklist` 仅用于前端展示
- 用户编辑 `frameworkChecklist` 不会同步到后端的 `framework.targets`
- 实际搜索使用的是 `_internal_framework`，不受前端编辑影响

### 节点 3: 搜索执行循环

**文件**: `ucppt_search_engine.py`
**位置**: `ucppt_search()` 主循环

```python
while current_round < max_rounds:
    # v7.245: 轮换策略选择目标
    target = framework.get_target_for_round(current_round)

    if target:
        # 生成搜索查询
        query = await self._generate_search_query(target, framework, ...)

        # 执行搜索
        sources = await self._search_web(query)

        # 更新目标状态
        target.collected_info.extend([...])
        target.completion_score = ...
```

### 节点 4: 动态延展机制

**触发条件**:
1. 阶段检查点（checkpoint_rounds = [2, 4, 6]）
2. 完成度评估不足
3. 发现新的关键实体

**延展流程**:
```python
# v7.246: 动态延展评估
if framework.get_extension_count() < MAX_EXTENSION_ROUNDS:
    needs_extension, extension_points = await self._evaluate_extension_need(
        framework, all_sources, current_round
    )
    if needs_extension:
        new_targets = await self._add_extension_targets(
            framework, extension_points, current_round
        )
        # 新目标直接添加到 framework.targets
        framework.targets.append(ext_target)
```

---

## 🔗 FrameworkChecklist 与 Targets 的关系

### 生成关系（单向派生）

```
SearchFramework.targets (执行层)
         │
         ▼ _generate_framework_checklist()
FrameworkChecklist.main_directions (展示层)
```

**转换逻辑**:
```python
def _generate_framework_checklist(self, framework, analysis_data):
    # 从 targets 生成 main_directions
    main_directions = []
    for i, target in enumerate(framework.targets, 1):
        main_directions.append({
            "id": f"D{i}",
            "direction": target.question or target.name,
            "purpose": target.why_need or target.purpose,
            "priority": target.priority,
        })

    return FrameworkChecklist(
        core_summary=framework.core_question,
        main_directions=main_directions,
        boundaries=[framework.boundary],
        answer_goal=framework.answer_goal,
    )
```

### 使用关系（互不干扰）

| 组件 | 数据源 | 用途 |
|------|--------|------|
| **搜索执行** | `framework.targets` | 实际搜索逻辑 |
| **FrameworkChecklistCard** | `frameworkChecklist` | 用户展示 |
| **SearchTaskListCard** | `searchMasterLine` (从 targets 转换) | 用户展示 |

**⚠️ 当前实现的问题**:
- 用户编辑 `FrameworkChecklistCard` 只修改了前端 state
- 后端搜索仍使用原始的 `_internal_framework`
- 编辑结果不会反馈到搜索执行

---

## 🎯 如何贯彻搜索框架清单

### 当前机制：Prompt 层面指导

框架清单通过构建在思考提示词中来指导搜索方向：

```python
def _build_thinking_prompt(self, framework, ...):
    # v7.240: 构建框架清单上下文
    framework_checklist_section = ""
    if framework.framework_checklist:
        checklist = framework.framework_checklist
        framework_checklist_section = f"""
## 🎯 搜索框架清单（始终遵循）

**核心问题**: {checklist.core_summary}

**搜索主线**:
"""
        for i, d in enumerate(checklist.main_directions, 1):
            framework_checklist_section += f"{i}. {d.get('direction', '')}: {d.get('purpose', '')}\n"

        if checklist.boundaries:
            framework_checklist_section += f"\n**不涉及**: {', '.join(checklist.boundaries)}\n"

    prompt = f"""...
{framework_checklist_section}
..."""
```

### 轮换选择机制

```python
def get_target_for_round(self, round_number: int) -> Optional[SearchTarget]:
    """
    按轮次轮换获取搜索目标 - v7.245

    策略：每轮搜索不同的主线，确保覆盖所有搜索方向
    - 第1轮选第1个目标
    - 第2轮选第2个目标
    - ...
    - 超过目标数量后循环
    """
    if not self.targets:
        return None
    sorted_targets = sorted(self.targets, key=lambda t: t.priority)
    index = (round_number - 1) % len(sorted_targets)
    return sorted_targets[index]
```

---

## 🔄 动态延展机制

### 触发时机

1. **阶段检查点** (checkpoint_rounds = [2, 4, 6])
   ```python
   if search_master_line.should_checkpoint(current_round):
       checkpoint_event = await self._generate_phase_checkpoint(...)
   ```

2. **实体发现补充** (v7.251)
   ```python
   # 检查品牌实体覆盖
   for brand in l1_facts.get("brand_entities", []):
       if brand_name not in covered_text:
           new_targets.append(SearchTarget(...))

   # 检查地理位置覆盖
   for location in l1_facts.get("location_mentions", []):
       if loc_name not in covered_text:
           new_targets.append(SearchTarget(...))

   # 张力验证任务
   if l3_tension and l3_tension not in covered_text:
       new_targets.append(SearchTarget(...))
   ```

3. **完成度不足时** (v7.246)
   ```python
   if framework.get_extension_count() < MAX_EXTENSION_ROUNDS:
       needs_extension, extension_points = await self._evaluate_extension_need(
           framework, all_sources, current_round
       )
   ```

### 延展任务处理

```python
async def _add_extension_targets(self, framework, extension_points, current_round):
    new_targets = []
    for i, ext_point in enumerate(extension_points):
        ext_target = SearchTarget(
            id=f"ext_{current_round}_{i+1}",
            name=ext_point.get("name"),
            description=ext_point.get("description"),
            priority=3,  # 延展任务优先级较低
            category="延展",
        )
        framework.targets.append(ext_target)  # ⭐ 直接添加到主列表
        new_targets.append(ext_target)
    return new_targets
```

---

## 💾 数据持久化机制

### 会话级持久化

```python
# 发送 SSE 事件时携带完整数据
yield {
    "type": "search_framework_ready",
    "data": {
        "targets": [t.to_dict() for t in framework.targets],
        "framework_checklist": framework_checklist.to_dict(),
    },
    "_internal_framework": framework,
}
```

### 前端状态保存

```typescript
// 搜索完成后自动保存
useEffect(() => {
    if (searchState.status === 'done' && searchState.answerContent) {
        saveSession(sessionId, {
            query: searchState.query,
            frameworkChecklist: searchState.frameworkChecklist,
            searchMasterLine: searchState.searchMasterLine,
            rounds: searchState.rounds,
            answerContent: searchState.answerContent,
            // ...
        });
    }
}, [searchState.status]);
```

### 会话恢复

```typescript
// 从已保存会话恢复
if (existingSession.status === 'done') {
    setSearchState({
        frameworkChecklist: session.frameworkChecklist || null,
        searchMasterLine: session.searchMasterLine || null,
        // ...
    });
}
```

---

## ⚠️ 当前实现的问题与改进建议

### 问题 1: 编辑断层

**现状**: 用户编辑 `FrameworkChecklistCard` 不影响实际搜索

**原因**:
- 前端编辑只修改 `searchState.frameworkChecklist`
- 后端搜索使用独立的 `_internal_framework` 对象
- SSE 流是单向的，编辑结果无法回传

**建议方案**:
```
方案A: 分阶段确认模式（推荐）
1. Step 1 完成后暂停，发送 framework 供编辑
2. 用户确认后，POST 编辑后的 directions 到新端点
3. 后端重建 framework.targets，继续 Step 2

方案B: 预处理模式
1. 在开始搜索前展示 AI 生成的框架
2. 用户编辑确认后再启动 SSE 流
3. 框架作为请求参数传入
```

### 问题 2: 展示与执行不同步

**现状**: `FrameworkChecklistCard` 显示的方向数量可能与实际 `targets` 数量不一致

**原因**:
- `_generate_framework_checklist()` 可能有过滤/聚合逻辑
- 动态延展的 targets 不会反向更新 checklist

**建议**:
- 在 `round_start` 事件中同步更新 checklist
- 或者前端直接从 `searchMasterLine.tasks` 派生展示

### 问题 3: 检查点触发依赖旧结构

**现状**: `should_checkpoint()` 依赖 `SearchMasterLine`，而新流程使用 `SearchFramework`

**建议**:
- 将检查点逻辑迁移到 `SearchFramework`
- 或在 `SearchFramework` 中添加 `checkpoint_rounds` 字段

---

## 🛠️ v7.280 已实现的改进

### 前端编辑控制

1. **编辑时机控制**
   - `awaitingConfirmation: true` → 可编辑
   - 收到 `round_start` 或用户点击确认 → 只读

2. **条件化传递编辑回调**
   ```typescript
   onUpdateChecklist={searchState.awaitingConfirmation ? (updated) => {
       setSearchState(prev => ({...prev, frameworkChecklist: updated}));
   } : undefined}
   ```

3. **确认按钮**
   ```typescript
   {searchState.awaitingConfirmation && (
       <button onClick={handleConfirmAndStartSearch}>
           确认并开始搜索
       </button>
   )}
   ```

### 待实现: 后端同步机制

如需让用户编辑真正影响搜索执行，需要：

1. **新增 API 端点**
   ```python
   @app.post("/api/search/ucppt/confirm-framework")
   async def confirm_framework(
       session_id: str,
       edited_directions: List[Dict],
   ):
       # 根据编辑后的方向重建 targets
       # 恢复 SSE 流，继续 Step 2
   ```

2. **拆分 SSE 流**
   - Phase 1: Step 1 分析 → 返回框架 → 等待确认
   - Phase 2: 接收确认 → Step 2 搜索 → 最终答案

3. **会话状态管理**
   - 保存中间状态（Step 1 完成、等待确认）
   - 支持断点续传

---

## 📊 数据流追踪表

| 阶段 | 事件/操作 | 数据流向 | 数据结构 |
|------|-----------|----------|----------|
| Step 1 | LLM 分析完成 | LLM → `SearchFramework` | `framework.targets[]` |
| Step 1 | 生成清单 | `targets` → `FrameworkChecklist` | `checklist.main_directions[]` |
| SSE | `search_framework_ready` | 后端 → 前端 | `{targets, framework_checklist}` |
| 前端 | 状态更新 | SSE 数据 → React State | `searchState.frameworkChecklist` |
| 用户 | 编辑方向 | UI → React State | `searchState.frameworkChecklist` (仅前端) |
| 用户 | 点击确认 | React State → (无同步) | 无后端更新 |
| Step 2 | 轮次循环 | `_internal_framework` | `framework.get_target_for_round()` |
| Step 2 | 动态延展 | 评估结果 → `framework.targets` | `framework.targets.append()` |
| 完成 | 保存会话 | 前端 → 后端 DB | `session.frameworkChecklist` |

---

## 🎯 结论

1. **FrameworkChecklist 是展示层抽象**
   - 从 `SearchFramework.targets` 派生
   - 用于前端友好展示
   - 编辑不影响实际执行

2. **搜索执行使用 targets**
   - `framework.get_target_for_round()` 驱动轮次
   - 动态延展直接操作 `targets` 列表
   - Prompt 注入 checklist 内容作为指导

3. **改进方向**
   - 如需编辑影响执行，需后端配合
   - 分阶段确认模式是最可行方案
   - 当前实现的编辑仅用于"备注/记录"用途
