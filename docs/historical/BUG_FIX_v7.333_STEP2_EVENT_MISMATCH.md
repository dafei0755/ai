# 🐛 Bug修复：v7.333 Step 2 搜索任务分解前端未显示问题

**日期**: 2026-02-04
**版本**: v7.333.4
**问题**: ucppt搜索模式下，Step 1（需求理解与深度分析）完成后，后端明确显示 [Step 2] 搜索任务分解完成，但前端无任何显示。

---

## 问题诊断

### 症状
- ✅ Step 1 完成后前端显示正常
- ❌ Step 2 任务分解后端日志显示完成，但前端无任何反馈
- ❌ 用户无法看到生成的搜索任务清单

### 根本原因

**事件名称不匹配**：

后端发送的事件（`ucppt_search_engine.py:4508-4527`）：
```python
# 后端发送
yield {
    "type": "task_decomposition_chunk",  # 流式输出
    "data": {"chunk": chunk},
}

yield {
    "type": "task_decomposition_complete",  # 完成事件
    "data": {
        "search_queries": search_queries,
        "execution_strategy": event_data.get("execution_strategy"),
        "execution_advice": event_data.get("execution_advice"),
    },
}
```

前端监听的事件（`page.tsx:2761`）：
```tsx
// 前端监听（错误）
case 'step2_plan_ready':  // ❌ 后端从未发送此事件
```

**结果**: 后端发送 `task_decomposition_complete`，前端监听 `step2_plan_ready`，事件被丢弃。

---

## 解决方案

### 修改文件

**`frontend-nextjs/app/search/[session_id]/page.tsx`**

在 `step2_complete` 事件处理后添加两个新的事件处理器：

```tsx
// 🆕 v7.333: Step 2 搜索任务分解流式输出
case 'task_decomposition_chunk':
  console.log('📝 [v7.333] Step 2 任务分解输出:', data);
  setSearchState(prev => {
    const currentContent = prev.statusMessage || '';
    const chunk = data.chunk || '';

    return {
      ...prev,
      statusMessage: currentContent + chunk,
    };
  });
  break;

// 🆕 v7.333: Step 2 搜索任务分解完成
case 'task_decomposition_complete':
  console.log('✅ [v7.333] Step 2 任务分解完成:', data);
  {
    const searchQueries = data.search_queries || [];
    console.log(`📋 [v7.333] 生成 ${searchQueries.length} 个搜索查询`);

    // 存储搜索查询数据
    setSearchState(prev => ({
      ...prev,
      statusMessage: `搜索任务已生成（${searchQueries.length}个查询）`,
    }));
  }
  break;
```

---

## 事件流梳理

### Step 1 → Step 2 完整流程

```
1. step1_complete
   ↓
2. task_decomposition (phase 事件)
   ↓
3. task_decomposition_chunk (流式输出，可多次)
   ↓
4. task_decomposition_complete (包含 search_queries)
   ↓
5. awaiting_confirmation (包含完整数据)
```

### 后端发送事件（ucppt_search_engine.py）

```python
# Line 4485-4495: Step 2 开始
yield {
    "type": "phase",
    "data": {
        "phase": "task_decomposition",
        "phase_name": "搜索任务分解",
        "message": "正在将分析结果转化为具体搜索任务...",
    },
}

# Line 4508-4513: 流式输出
yield {
    "type": "task_decomposition_chunk",
    "data": {"chunk": chunk},
}

# Line 4519-4527: 完成事件
yield {
    "type": "task_decomposition_complete",
    "data": {
        "search_queries": search_queries,
        "execution_strategy": event_data.get("execution_strategy"),
        "execution_advice": event_data.get("execution_advice"),
    },
}
```

---

## 测试验证

### 测试步骤
1. 启动后端服务：`python -B scripts\run_server_production.py`
2. 启动前端服务：`cd frontend-nextjs && npm run dev`
3. 访问 http://localhost:3001/search
4. 输入测试查询并选择"ucppt搜索模式"
5. 观察 Step 2 是否有流式输出和完成提示

### 预期结果
- ✅ Step 1 完成后显示"正在将分析结果转化为具体搜索任务..."
- ✅ Step 2 流式输出任务分解内容（累积到 statusMessage）
- ✅ Step 2 完成后显示"搜索任务已生成（N个查询）"
- ✅ 用户可以看到完整的任务分解流程

### 单元测试
运行测试验证事件处理逻辑：
```bash
cd frontend-nextjs
npm test -- __tests__/v7.333_step2_events.test.ts
```

测试覆盖：
- ✅ `task_decomposition_chunk` 累积显示
- ✅ `task_decomposition_complete` 数量统计
- ✅ 后端事件与前端监听器的映射关系
- ✅ 废弃事件的检测

---

## 相关文件

- **后端**: `intelligent_project_analyzer/services/ucppt_search_engine.py:4485-4527`
- **前端**: `frontend-nextjs/app/search/[session_id]/page.tsx:2761-2798`
- **执行器**: `intelligent_project_analyzer/services/four_step_flow_orchestrator.py:1142-1224`

---

## 总结

**问题**: 后端发送 `task_decomposition_complete`，前端监听 `step2_plan_ready`，导致 Step 2 完成数据丢失。

**修复**: 添加 `task_decomposition_chunk` 和 `task_decomposition_complete` 事件处理器。

**影响范围**: ucppt搜索模式的 Step 1 → Step 2 过渡流程。

**版本**: v7.333.4
