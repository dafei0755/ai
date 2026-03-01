# 🔧 BUG FIX v7.351: Step 1 → Step 2 数据对应可视化

**修复日期**: 2026-02-05
**问题类型**: 数据流透明度、调试增强
**修复目标**: 让用户和开发者清楚看到 Step 1（深度分析）和 Step 2（任务清单）的对应关系

---

## 🐛 问题描述

用户反馈："步骤1的搜索框架应该和步骤2的任务清单对应才对"

**现象**:
- Step 1 生成了分析板块（blocks），但 UI 上看不到与 Step 2 任务清单的对应关系
- 日志缺少关键的数据流追踪信息
- 无法快速判断转换是否成功

---

## ✅ 修复方案

### 1️⃣ 后端日志增强（ucppt_search_engine.py）

**位置**: `intelligent_project_analyzer/services/ucppt_search_engine.py`

**修改点 1**: Step 1 完成时记录 blocks 数量
```python
# v7.351: 添加详细日志追踪 Step 1 输出
blocks_data = output_framework.get("blocks", [])
logger.info(f"📋 [v7.351] Step 1 完成 | blocks数量: {len(blocks_data)}")
if blocks_data:
    for idx, block in enumerate(blocks_data[:3]):  # 只显示前3个
        block_name = block.get("name", "未命名")
        logger.info(f"  - 板块{idx+1}: {block_name[:50]}")
else:
    logger.warning("⚠️ [v7.351] Step 1 未生成任何 blocks，Step 2 可能失败")
```

**修改点 2**: 转换时记录结果
```python
# v7.351: 记录转换结果
if step2_framework:
    logger.info(f"✅ [v7.351] Step 1 → Step 2 转换成功")
else:
    logger.error(f"❌ [v7.351] Step 1 → Step 2 转换失败 | blocks数量: {len(blocks_data)}")
```

**修改点 3**: Step 2 完成时显示对应关系
```python
# v7.351: 记录板块与任务的对应关系
logger.info(f"✅ [v7.351] Step 2 完成 | {len(blocks_data)} 个板块 → {len(search_queries)} 个搜索任务")
if len(search_queries) == 0 and len(blocks_data) > 0:
    logger.warning(f"⚠️ [v7.351] 有 {len(blocks_data)} 个板块但未生成任何搜索任务，请检查 Step 2 逻辑")
```

**修改点 4**: 在 SSE 事件中传递 blocks 数量
```python
yield {
    "type": "task_decomposition_complete",
    "data": {
        "search_queries": search_queries,
        "execution_strategy": event_data.get("execution_strategy"),
        "execution_advice": event_data.get("execution_advice"),
        # 📊 v7.351: 传递 blocks 数量到前端
        "source_blocks_count": len(blocks_data),
    },
}
```

### 2️⃣ 前端可视化增强

#### A. 过渡提示卡片（page.tsx）

**位置**: `frontend-nextjs/app/search/[session_id]/page.tsx`

**效果**: 在 Step 1 完成后显示板块数量
```tsx
{/* 📊 v7.351: 显示 Step 1 板块数量 */}
{searchState.fourMissionsResult?.blocks && (
  <div className="mt-2 text-xs text-gray-600 bg-blue-50 px-3 py-1.5 rounded-lg inline-block">
    📋 基于 <span className="font-semibold text-blue-700">
      {searchState.fourMissionsResult.blocks.length}
    </span> 个分析板块生成任务
  </div>
)}
```

#### B. 任务清单头部（Step2TaskListEditor.tsx）

**位置**: `frontend-nextjs/components/search/Step2TaskListEditor.tsx`

**效果**: 在任务清单头部显示对应关系
```tsx
{/* 📊 v7.351: 显示与 Step 1 的对应关系 */}
{plan.source_blocks_count !== undefined && plan.source_blocks_count > 0 && (
  <p className="text-xs text-blue-600 mt-0.5">
    💡 基于 {plan.source_blocks_count} 个分析板块智能生成
  </p>
)}
```

#### C. 类型定义（types/index.ts）

**位置**: `frontend-nextjs/types/index.ts`

**添加字段**:
```typescript
export interface Step2SearchPlan {
  // ... 其他字段

  // 📊 v7.351: 源板块数量（用于显示对应关系）
  source_blocks_count?: number;
}
```

---

## 🎯 修复效果

### 后端日志示例
```
📋 [v7.351] Step 1 完成 | blocks数量: 5
  - 板块1: 市场定位与竞争分析
  - 板块2: 产品体验设计策略
  - 板块3: 技术实现路径规划
✅ [v7.351] Step 1 → Step 2 转换成功
✅ [v7.351] Step 2 完成 | 5 个板块 → 12 个搜索任务
```

### 前端 UI 显示
1. **过渡卡片**: "📋 基于 **5** 个分析板块生成任务"
2. **任务清单头部**: "💡 基于 5 个分析板块智能生成"

---

## 📊 数据流确认

```
Step 1 (深度分析)
  ↓
output_framework.blocks (板块列表)
  ↓
_convert_to_step2_output_framework (转换函数)
  ↓
Step 2 Executor
  ↓
search_queries (搜索任务)
  ↓
task_decomposition_complete 事件
  ↓
前端显示 (Step2TaskListEditor)
```

---

## 🧪 验证方法

### 1. 查看后端日志
```powershell
Get-Content logs\server.log -Tail 50 | Select-String "v7.351"
```

**期望输出**:
- `📋 [v7.351] Step 1 完成 | blocks数量: X`
- `✅ [v7.351] Step 1 → Step 2 转换成功`
- `✅ [v7.351] Step 2 完成 | X 个板块 → Y 个搜索任务`

### 2. 检查前端显示

启动搜索任务后，检查：
- ✅ 过渡卡片显示板块数量
- ✅ 任务清单头部显示"基于 X 个分析板块智能生成"
- ✅ 任务数量与板块数量合理对应（1 板块 → 1-3 任务）

---

## 🔄 相关文档

- 📖 [STEP1_STEP2_MAPPING_DIAGNOSIS.md](STEP1_STEP2_MAPPING_DIAGNOSIS.md) - 完整诊断分析
- 📖 [4-STEP-FLOW-README.md](4-STEP-FLOW-README.md) - 4步工作流详细说明
- 📖 [BUG_FIX_v7.333_STEP2_EVENT_MISMATCH.md](BUG_FIX_v7.333_STEP2_EVENT_MISMATCH.md) - Step 2 事件处理修复

---

## 📝 技术细节

### 修改文件清单
1. ✅ `intelligent_project_analyzer/services/ucppt_search_engine.py` (3处日志增强 + 1处数据传递)
2. ✅ `frontend-nextjs/app/search/[session_id]/page.tsx` (过渡卡片 + 事件处理)
3. ✅ `frontend-nextjs/components/search/Step2TaskListEditor.tsx` (头部显示)
4. ✅ `frontend-nextjs/types/index.ts` (类型定义)

### 版本标记
所有修改使用 `v7.351` 标记，方便后续追踪和回滚。

---

**修复状态**: ✅ 已完成
**测试状态**: ⏳ 待用户验证
**回滚方法**: `git log --grep="v7.351"` 查找提交，使用 `git revert` 回滚
