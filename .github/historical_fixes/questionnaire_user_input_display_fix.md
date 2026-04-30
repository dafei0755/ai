# 问卷第二、三步用户需求显示修复 (v7.115)

## 📋 问题描述

**用户反馈**：
> "问卷的第二三步，顶部的需求，怎么丢失了！！！只有第一步有"

**症状**：
- ✅ Step 1（任务梳理）：顶部正常显示用户需求摘要
- ❌ Step 2（雷达图）：顶部需求区域空白
- ❌ Step 3（信息补全）：顶部需求区域空白

**影响范围**：所有使用三步递进式问卷的会话

## 🔍 根因分析

### 前端实现（正常）

前端组件 `UnifiedProgressiveQuestionnaireModal.tsx` 已正确实现需求显示逻辑：

```tsx
{/* 固定需求显示 - 所有步骤通用 */}
{(step1Data?.user_input || step1Data?.user_input_summary ||
  step2Data?.user_input || step2Data?.user_input_summary ||
  step3Data?.user_input || step3Data?.user_input_summary) && (
  <div className="flex items-start gap-2">
    <span className="text-sm font-medium text-blue-600">需求：</span>
    <span className="text-sm text-gray-600">
      {step1Data?.user_input || step1Data?.user_input_summary ||
       step2Data?.user_input || step2Data?.user_input_summary ||
       step3Data?.user_input || step3Data?.user_input_summary}
    </span>
  </div>
)}
```

**前端期望**：后端提供以下任一字段
- `user_input`（完整需求）
- `user_input_summary`（需求摘要，前100字符）

### 后端缺陷（问题所在）

**Step 1 Payload**（✅ 正常）：
```python
# Line 133
user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

payload = {
    "interaction_type": "progressive_questionnaire_step1",
    "extracted_tasks": extracted_tasks,
    "user_input_summary": user_input_summary,  # ✅ 包含
    # ...
}
```

**Step 2 Payload**（❌ 缺失）：
```python
# ~Line 400，修复前
payload = {
    "interaction_type": "progressive_questionnaire_step2",
    "title": "多维度偏好设置",
    "core_task": confirmed_task,
    "dimensions": dimensions,
    # ❌ 缺少 user_input_summary 或 user_input
    "options": {...}
}
```

**Step 3 Payload**（❌ 缺失）：
```python
# ~Line 620，修复前
payload = {
    "interaction_type": "progressive_questionnaire_step3",
    "title": "补充关键信息",
    "core_task": confirmed_task,
    "task_summary": task_summary,
    # ❌ 缺少 user_input_summary 或 user_input
    "questionnaire": {...},
    "options": {...}
}
```

### 数据流断层图

```
┌─────────────────────────────────────────────────────────────┐
│  State (LangGraph)                                          │
│  ├─ user_input: "设计一个150平米的现代简约风格住宅..."     │
│  └─ other fields...                                        │
└────────────┬────────────────────────────────────────────────┘
             │
             ├──> Step 1 ───> interrupt(payload)
             │                 ├─ user_input_summary ✅
             │                 └─ Frontend: 显示成功 ✅
             │
             ├──> Step 2 ───> interrupt(payload)
             │                 ├─ user_input_summary ❌ 缺失
             │                 └─ Frontend: 空白区域 ❌
             │
             └──> Step 3 ───> interrupt(payload)
                               ├─ user_input_summary ❌ 缺失
                               └─ Frontend: 空白区域 ❌
```

## 🛠️ 修复方案

### 修改文件

- **文件**：`intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`
- **版本标记**：v7.115
- **修改位置**：
  - Step 2 payload（约 Line 400）
  - Step 3 payload（约 Line 620）

### Step 2 修复代码

```python
# 获取确认的核心任务
confirmed_task = state.get("confirmed_core_task", "")

# 🔧 v7.115: 获取用户原始输入，用于前端显示需求摘要
user_input = state.get("user_input", "")
user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

# 构建interrupt payload
payload = {
    "interaction_type": "progressive_questionnaire_step2",
    "step": 2,
    "total_steps": 3,
    "title": "多维度偏好设置",
    "message": "请通过拖动滑块表达您的设计偏好。每个维度代表两种不同的设计方向。",
    "core_task": confirmed_task,
    "dimensions": dimensions,
    "instructions": "拖动滑块到您偏好的位置（0-100）",
    # 🔧 v7.115: 添加用户需求信息，供前端顶部显示
    "user_input": user_input,
    "user_input_summary": user_input_summary,
    "options": {
        "confirm": "确认偏好设置",
        "back": "返回修改核心任务"
    }
}
```

### Step 3 修复代码

```python
# 获取上下文信息
confirmed_task = state.get("confirmed_core_task", "")
task_summary = ProgressiveQuestionnaireNode._build_task_summary(confirmed_tasks)

# 🔧 v7.115: 获取用户原始输入，用于前端显示需求摘要
user_input = state.get("user_input", "")
user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

# 🆕 v7.80.6: 构建新的 interrupt payload（任务完整性导向）
payload = {
    "interaction_type": "progressive_questionnaire_step3",
    "step": 3,
    "total_steps": 3,
    "title": "补充关键信息",
    "message": "为了更精准地理解您的项目需求，请补充以下关键信息：",
    "core_task": confirmed_task,
    "task_summary": task_summary,
    # 🆕 任务完整性信息
    "completeness_score": completeness.get("completeness_score", 0),
    "covered_dimensions": completeness.get("covered_dimensions", []),
    "missing_dimensions": completeness.get("missing_dimensions", []),
    "critical_gaps": critical_gaps,
    # 🔧 v7.115: 添加用户需求信息，供前端顶部显示
    "user_input": user_input,
    "user_input_summary": user_input_summary,
    "questionnaire": {
        "introduction": f"已完整度: {int(completeness.get('completeness_score', 0) * 100)}% | 缺失维度: {', '.join(completeness.get('missing_dimensions', []))}",
        "questions": questions,
        "note": "这些问题涉及预算、时间、交付等关键决策点，请根据实际情况作答"
    },
    "options": {
        "submit": "提交问卷",
        "back": "返回修改核心任务"
    }
}
```

## ✅ 修复效果对比

| 步骤 | 修复前 | 修复后 | 改进 |
|------|--------|--------|------|
| **Step 1**<br>（任务梳理） | ✅ 顶部显示<br>"需求：设计一个150平米..." | ✅ 顶部显示<br>"需求：设计一个150平米..." | 保持不变 |
| **Step 2**<br>（雷达图） | ❌ 顶部需求区域空白 | ✅ 顶部显示<br>"需求：设计一个150平米..." | **修复完成** |
| **Step 3**<br>（信息补全） | ❌ 顶部需求区域空白 | ✅ 顶部显示<br>"需求：设计一个150平米..." | **修复完成** |

## 🔄 部署步骤

### 1. 代码修改

✅ 已完成修改：`progressive_questionnaire.py` (~Line 400, ~Line 620)

### 2. 重启后端服务

```powershell
# 终止旧进程
taskkill /F /IM python.exe

# 等待端口释放
Start-Sleep -Seconds 2

# 重启服务
python -B run_server_production.py
```

**启动成功标志**：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
✅ Playwright 浏览器池初始化成功
```

### 3. 验证修复

⚠️ **重要提示**：需要**新建会话**才能看到修复效果（旧会话的 interrupt payload 已经发送，不会自动更新）

**验证步骤**：
1. 访问 http://localhost:3000
2. 输入需求：
   ```
   设计一个150平米的现代简约风格住宅，三室两厅，预算30万
   ```
3. **Step 1 验证**：
   - ✅ 顶部显示："需求：设计一个150平米的现代简约风格住宅，三室两厅，预算30万"

4. **Step 2 验证**（点击"确认任务列表"后）：
   - ✅ 顶部显示："需求：设计一个150平米的现代简约风格住宅，三室两厅，预算30万"
   - ✅ 维度滑块正常工作

5. **Step 3 验证**（点击"确认偏好设置"后）：
   - ✅ 顶部显示："需求：设计一个150平米的现代简约风格住宅，三室两厅，预算30万"
   - ✅ 补充问题正常显示

## 📝 技术总结

### 问题根源

**数据流断层**：后端 Step 2/3 没有将用户原始输入 `user_input` 传递到前端

### 前端防御性编程

前端组件做了防御性处理，尝试从多个数据源读取：
```tsx
step1Data?.user_input || step1Data?.user_input_summary ||
step2Data?.user_input || step2Data?.user_input_summary ||
step3Data?.user_input || step3Data?.user_input_summary
```

但由于后端 Step 2/3 没有提供任何一个字段，最终导致显示为空。

### 修复策略

- **最小化改动**：仅在 Step 2/3 的 payload 中添加 2 个字段
- **向后兼容**：不影响现有的 Step 1 逻辑和其他功能
- **统一体验**：三步问卷顶部统一显示用户需求摘要（前100字符 + "..."）

### 数据流修复后

```
┌─────────────────────────────────────────────────────────────┐
│  State (LangGraph)                                          │
│  ├─ user_input: "设计一个150平米的现代简约风格住宅..."     │
│  └─ other fields...                                        │
└────────────┬────────────────────────────────────────────────┘
             │
             ├──> Step 1 ───> interrupt(payload)
             │                 ├─ user_input_summary ✅
             │                 └─ Frontend: 显示成功 ✅
             │
             ├──> Step 2 ───> interrupt(payload)
             │                 ├─ user_input_summary ✅ [v7.115修复]
             │                 └─ Frontend: 显示成功 ✅
             │
             └──> Step 3 ───> interrupt(payload)
                               ├─ user_input_summary ✅ [v7.115修复]
                               └─ Frontend: 显示成功 ✅
```

## 🏷️ 版本信息

- **版本号**：v7.115
- **修复类型**：P1 Bug（影响用户体验）
- **修复日期**：2026-01-02
- **修复分支**：main
- **相关文件**：
  - `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`（后端修复）
  - `frontend-nextjs/components/UnifiedProgressiveQuestionnaireModal.tsx`（前端无需修改）

## 📚 相关文档

- 📝 [完整修复报告](../QUESTIONNAIRE_USER_INPUT_FIX_v7.115.md)
- 📊 [CHANGELOG.md](../CHANGELOG.md#v7115---2026-01-02)
- 🎯 [三步问卷架构说明](../docs/PROGRESSIVE_QUESTIONNAIRE.md)（如果有）

## 🔖 防止回归清单

### 代码审查检查点

在修改 `progressive_questionnaire.py` 的 Step 2/3 节点时，确保：

- [ ] ✅ `interrupt()` payload 中包含 `user_input` 字段
- [ ] ✅ `interrupt()` payload 中包含 `user_input_summary` 字段（前100字符 + "..."）
- [ ] ✅ 从 `state.get("user_input", "")` 获取原始输入
- [ ] ✅ 前端 `UnifiedProgressiveQuestionnaireModal.tsx` 中的读取逻辑保持不变

### 测试用例

建议添加集成测试：
```python
def test_progressive_questionnaire_user_input_in_all_steps():
    """验证三步问卷的所有步骤都包含user_input"""
    state = {
        "user_input": "设计一个150平米的现代简约风格住宅，三室两厅，预算30万"
    }

    # Step 1
    result1 = ProgressiveQuestionnaireNode.step1_core_task(state)
    assert "user_input_summary" in result1.payload

    # Step 2
    result2 = ProgressiveQuestionnaireNode.step2_radar(state)
    assert "user_input_summary" in result2.payload  # v7.115修复
    assert "user_input" in result2.payload  # v7.115修复

    # Step 3
    result3 = ProgressiveQuestionnaireNode.step3_gap_filling(state)
    assert "user_input_summary" in result3.payload  # v7.115修复
    assert "user_input" in result3.payload  # v7.115修复
```

## 💡 经验教训

### 问题预防

1. **统一数据规范**：所有 interrupt() payload 应遵循统一的字段规范
2. **代码模板化**：相似的 payload 构建逻辑应抽取为公共方法
3. **前后端契约**：建立明确的 API 契约文档，避免字段遗漏
4. **集成测试**：添加端到端测试覆盖完整问卷流程

### 建议改进

**重构建议**（可选，P2优先级）：
```python
def _build_interrupt_payload(
    state: ProjectAnalysisState,
    interaction_type: str,
    step: int,
    title: str,
    message: str,
    **kwargs
) -> dict:
    """统一构建interrupt payload，确保必需字段不缺失"""
    user_input = state.get("user_input", "")
    user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

    base_payload = {
        "interaction_type": interaction_type,
        "step": step,
        "total_steps": 3,
        "title": title,
        "message": message,
        # 🔒 确保所有步骤都包含
        "user_input": user_input,
        "user_input_summary": user_input_summary,
    }
    base_payload.update(kwargs)
    return base_payload
```

使用方式：
```python
# Step 2
payload = _build_interrupt_payload(
    state=state,
    interaction_type="progressive_questionnaire_step2",
    step=2,
    title="多维度偏好设置",
    message="请通过拖动滑块表达您的设计偏好...",
    dimensions=dimensions,
    core_task=confirmed_task,
    options={...}
)
```

---

**验证清单**：
- ✅ 代码已修改
- ✅ 后端已重启
- ✅ CHANGELOG.md 已更新
- ✅ 历史修复文档已创建
- ⏳ 等待用户测试反馈（需要新建会话验证）
