# 🔧 BUG_FIX v7.340: 智能搜索任务清单 - 版块动态分解与按版块分页

**修复日期**: 2026-02-05
**版本**: v7.340
**类型**: 功能增强 + UI优化
**优先级**: ⭐⭐⭐⭐ 高优先级

---

## 📋 问题描述

**核心需求**：
1. 搜索任务清单与步骤1的版块对应，每个版块一个分页
2. 版块需要二次分解为5-10个具体搜索任务（智能化）
3. 用户修改任务后，在第三步搜索前智能重新分配到版块
4. UI简化为扁平列表，点击编辑，悬停删除，每页末尾添加"+"按钮

**设计决策**：
- ✅ 根据版块复杂度动态生成5-10个任务（使用LLM判断）
- ✅ 严格保持步骤1的版块结构
- ✅ 如果LLM无法判断任务归属，归入"其他任务"版块（`block_id="B_other"`）
- ✅ 任务数量不均衡是正常现象，不用干预
- ✅ LLM调用失败时使用固定规则（每版块固定8个任务）

---

## 🛠️ 实施方案

### 1. 后端：智能任务分解（5-10个任务）

**文件**: `intelligent_project_analyzer/services/ucppt_search_engine.py`

#### 1.1 新增智能分解函数

```python
async def _decompose_block_to_tasks(
    self, block: OutputBlock, block_index: int, original_query: str
) -> List[Dict[str, Any]]:
    """
    智能分解：将版块（方向）分解为5-10个具体搜索任务

    v7.340 新增：智能任务分解
    - 根据版块复杂度动态生成5-10个任务
    - LLM失败时降级到固定规则（每版块8个任务）
    - 每个任务包含block_id关联原始版块
    """
```

**特性**：
- 调用LLM分析版块复杂度（基于`sub_items`数量）
- 动态决定任务数量：`min(10, max(5, sub_items_count + 3))`
- 每个任务包含：
  - `task_description`: 任务描述（15-30字）
  - `search_keywords`: 搜索关键词列表（3-5个）
  - `expected_outcome`: 期望获得的信息（15-30字）
  - `priority`: 优先级（high/medium/low）
  - `block_id`: 关联的版块ID（如`B1`, `B2`）

#### 1.2 固定规则降级策略

```python
def _decompose_block_to_tasks_fixed(
    self, block: OutputBlock, block_index: int
) -> List[Dict[str, Any]]:
    """
    固定规则：将版块分解为8个任务（LLM失败时的降级方案）

    v7.340 新增：固定分解规则
    - 每个版块固定生成8个任务
    - 基于sub_items均匀分配
    - 任务数量不足时重复使用sub_items
    """
```

#### 1.3 修改blocks → targets转换逻辑

**位置**: `_rebuild_targets_from_framework_data` 函数

**变更**：
```python
# 旧逻辑：每个block转换为1个target
# v7.333: 优先从 output_framework.blocks 重建 targets（Step 1 v3.0 格式）
for i, block in enumerate(blocks, 1):
    target = SearchTarget(
        id=f"T{i}",
        question=block_name,
        search_for=block_name,
        ...
    )

# 新逻辑：每个block智能分解为5-10个targets
# v7.340: 优先从 output_framework.blocks 智能分解 targets
for i, block in enumerate(blocks, 1):
    tasks = await self._decompose_block_to_tasks(block_obj, i, original_query)
    for task in tasks:
        target = SearchTarget(
            id=task.get("id", ""),
            question=task.get("task_description", ""),
            metadata={"block_id": task.get("block_id", "")},  # 保存版块关联
            ...
        )
```

---

### 2. 后端：智能任务重分配

**文件**: `intelligent_project_analyzer/services/ucppt_search_engine.py`

```python
async def _reallocate_edited_tasks(
    self,
    main_directions: List[Dict[str, Any]],
    blocks: List[Dict[str, Any]],
    original_query: str
) -> List[Dict[str, Any]]:
    """
    智能任务重分配：将用户编辑的任务重新分配到最合适的版块

    v7.340 新增：智能任务重分配
    - 严格保持原始版块结构
    - 使用LLM判断任务归属
    - 无法归属的任务归入"其他任务"版块（block_id="B_other"）
    - LLM失败时降级：所有无明确block_id的任务归入B_other
    """
```

**调用时机**：
- 用户点击"开始搜索"按钮时（Step 2 → Step 3）
- 仅重分配标记为`is_user_modified`或`is_user_added`的任务
- 保留第二步的原始列表，仅更新`block_id`字段

---

### 3. 后端：main_directions数据结构更新

**文件**: `intelligent_project_analyzer/services/ucppt_search_engine.py`

**修改位置**: `generate_framework_checklist_streaming` 函数

```python
# v7.340: 提取block_id（版块关联）
block_id = target.metadata.get("block_id", "") if hasattr(target, "metadata") and target.metadata else ""

# v7.340: 每个任务作为独立的 direction，带版块关联
direction = {
    "direction": direction_name,
    "purpose": target.why_need or target.purpose or "",
    "expected_outcome": expected_outcome,
    "sub_tasks": sub_tasks_list,
    "motivation_tag": motivation_type.label_zh if motivation_type else "",
    "motivation_id": motivation_id,
    "motivation_color": motivation_type.color if motivation_type else "#808080",
    "priority": target.priority,
    "target_id": target.id,
    "block_id": block_id,  # v7.340: 版块关联
}
```

---

### 4. 前端：按版块分页显示任务清单

**文件**: `frontend-nextjs/app/search/[session_id]/page.tsx`

#### 4.1 新增版块分组逻辑

```typescript
// v7.340: 按版块分组任务
const groupTasksByBlock = () => {
  const grouped: { [key: string]: any[] } = {};

  checklist.main_directions.forEach((direction) => {
    const blockId = direction.block_id || 'B_other';
    if (!grouped[blockId]) {
      grouped[blockId] = [];
    }
    grouped[blockId].push(direction);
  });

  return grouped;
};

const groupedTasks = groupTasksByBlock();
const blockIds = Object.keys(groupedTasks).sort(); // B1, B2, B3, ..., B_other
const [currentBlockIndex, setCurrentBlockIndex] = React.useState(0);
const currentBlockId = blockIds[currentBlockIndex] || 'B1';
const currentTasks = groupedTasks[currentBlockId] || [];
```

#### 4.2 版块导航UI

```tsx
{/* 版块导航 */}
{blockIds.length > 1 && (
  <div className="flex items-center gap-2 mb-4">
    <button onClick={() => setCurrentBlockIndex(Math.max(0, currentBlockIndex - 1))}>
      <ChevronLeft />
    </button>
    <div className="flex-1 text-center">
      <span>
        {currentBlockId === 'B_other' ? '其他任务' : `版块${currentBlockIndex + 1}`}
        ({currentTasks.length}个任务)
      </span>
    </div>
    <button onClick={() => setCurrentBlockIndex(Math.min(blockIds.length - 1, currentBlockIndex + 1))}>
      <ChevronRight />
    </button>
  </div>
)}
```

#### 4.3 简化任务列表UI

**设计改进**：
- ❌ 移除：卡片装饰、多行字段（目的、期望结果）
- ✅ 保留：序号 + 任务描述
- ✅ 交互：点击任务进入编辑模式，悬停显示删除按钮
- ✅ 新增：每页末尾"+"按钮添加任务到当前版块

```tsx
{/* 任务列表 - v7.340: 扁平化显示，点击编辑 */}
<div className="space-y-2">
  {currentTasks.map((direction, localIndex) => {
    const globalIndex = checklist.main_directions.indexOf(direction);
    return (
      <div key={globalIndex} className="group relative flex items-center gap-3 px-4 py-3 bg-white border rounded-lg hover:border-indigo-300">
        {/* 序号 */}
        <span className="text-sm font-medium text-gray-400">{localIndex + 1}</span>

        {/* 任务描述 - 可点击编辑 */}
        <div className="flex-1 min-w-0">
          {editingIndex === globalIndex ? (
            <input type="text" value={editValue} ... />
          ) : (
            <div onClick={() => handleStartEdit(globalIndex, 'direction', direction.direction)}>
              {direction.direction || '未命名任务'}
            </div>
          )}
        </div>

        {/* 删除按钮 */}
        <button onClick={() => handleDelete(globalIndex)} className="opacity-0 group-hover:opacity-100">
          <Trash2 />
        </button>
      </div>
    );
  })}
</div>

{/* 添加新任务按钮 - v7.340: 在当前版块末尾 */}
<button onClick={() => setIsAddingNew(true)}>
  <Plus /> 添加新任务到当前版块
</button>
```

---

## ✅ 验证清单

### 后端验证

- [x] `_decompose_block_to_tasks` 智能分解函数正常工作
- [x] LLM调用失败时正确降级到`_decompose_block_to_tasks_fixed`
- [x] 每个版块生成5-10个任务（数量不均衡正常）
- [x] 每个任务包含`block_id`字段
- [x] `_reallocate_edited_tasks` 智能重分配函数正常工作
- [x] 无法归属的任务正确归入`B_other`版块
- [x] `main_directions`数据结构包含`block_id`字段

### 前端验证

- [ ] 任务按版块分组显示
- [ ] 版块导航按钮（左/右箭头）正常工作
- [ ] 显示版块名称和任务数量（如"版块1 (8个任务)"）
- [ ] 任务列表扁平化显示（仅序号+任务描述）
- [ ] 点击任务进入编辑模式
- [ ] 悬停显示删除按钮
- [ ] 每页末尾"+"按钮添加任务到当前版块
- [ ] 新增任务自动标记当前`block_id`和`is_user_added`

---

## 📊 数据流图

```
Step 1: 深度分析
  ↓
  output_framework.blocks (2-7个版块)
    ↓
    [智能分解] _decompose_block_to_tasks
      ↓
      每个版块 → 5-10个任务 (带block_id)
        ↓
        SearchTarget[] → main_directions[]
          ↓
          前端：FrameworkChecklistCard（按版块分页）
            ↓
            用户编辑/新增任务
              ↓
              [智能重分配] _reallocate_edited_tasks
                ↓
                更新block_id（保留原始版块结构）
                  ↓
                  无法归属 → block_id="B_other"
                    ↓
                    Step 3: 开始搜索（按版块顺序执行）
```

---

## 🔍 测试场景

### 场景1：正常智能分解

**输入**：
- 版块1："Tiffany品牌传承"，sub_items: 6个
- 版块2："日常生活便利性"，sub_items: 4个

**预期输出**：
- 版块1：9个任务（6 + 3）
- 版块2：7个任务（4 + 3）
- 每个任务包含：`task_description`, `search_keywords`, `expected_outcome`, `priority`, `block_id`

### 场景2：LLM失败降级

**输入**：
- 版块1："Tiffany品牌传承"
- LLM调用超时/失败

**预期输出**：
- 版块1：8个任务（固定规则）
- 任务描述格式："搜索Tiffany品牌传承相关的{sub_item}信息"

### 场景3：用户编辑后智能重分配

**输入**：
- 用户新增任务："研究峨眉山地区的气候特点"
- 原始版块：B1（Tiffany品牌）, B2（日常生活）

**预期输出**：
- LLM判断该任务与B2更相关
- 任务`block_id`更新为`B2`

### 场景4：无法归属任务

**输入**：
- 用户新增任务："研究量子计算的应用"
- 原始版块：B1（Tiffany品牌）, B2（日常生活）

**预期输出**：
- LLM判断该任务与所有版块无关
- 任务`block_id`设置为`B_other`
- 前端显示"其他任务"版块

---

## 🚀 后续优化建议

1. **性能优化**：
   - 并行调用LLM分解多个版块
   - 缓存版块分解结果（避免重复调用）

2. **用户体验**：
   - 添加版块切换动画
   - 支持拖拽排序任务
   - 批量删除任务功能

3. **智能化增强**：
   - 学习用户编辑模式，优化分解策略
   - 自动建议任务优先级
   - 智能合并相似任务

---

## 📝 相关文档

- [4-Step Flow 完整实现计划](docs/4-STEP-FLOW-IMPLEMENTATION.md)
- [搜索任务清单用户需求](QUICKSTART.md)
- [版块分解设计文档](docs/plans/2026-02-01-4-step-complete.md)

---

**修复完成**: ✅ 已实施（待前端测试验证）
**文档更新**: ✅ 已记录到修复历史
