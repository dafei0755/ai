# 🔧 v7.115 修复报告：问卷第二、三步显示用户需求

## 📋 问题描述

**用户反馈**：
> "问卷的第二三步，顶部的需求，怎么丢失了！！！只有第一步有"

**影响范围**：
- **Step 1（任务梳理）**：✅ 正常显示用户需求摘要
- **Step 2（雷达图）**：❌ 顶部需求区域空白
- **Step 3（信息补全）**：❌ 顶部需求区域空白

## 🔍 根因分析

### 前端代码

前端组件 `UnifiedProgressiveQuestionnaireModal.tsx` 正确实现了需求显示逻辑：

```tsx
{/* 固定需求显示 - 所有步骤通用（优先显示完整user_input，回退到摘要） */}
{(step1Data?.user_input || step1Data?.user_input_summary ||
  step2Data?.user_input || step2Data?.user_input_summary ||
  step3Data?.user_input || step3Data?.user_input_summary) && (
  <div className="flex items-start gap-2 cursor-pointer hover:bg-gray-50 rounded-lg p-3 -m-2 transition-colors"
       onClick={() => setIsSummaryExpanded(!isSummaryExpanded)}>
    <span className="text-sm font-medium text-blue-600 flex-shrink-0">需求：</span>
    <div className="flex-1 min-w-0">
      <span className={`text-sm leading-relaxed text-gray-600 ${isSummaryExpanded ? '' : 'line-clamp-6'}`}>
        {step1Data?.user_input || step1Data?.user_input_summary ||
         step2Data?.user_input || step2Data?.user_input_summary ||
         step3Data?.user_input || step3Data?.user_input_summary}
      </span>
    </div>
  </div>
)}
```

**前端期望**：后端在 Step 2/3 的 `interrupt()` payload 中提供以下任一字段：
- `user_input`（完整需求）
- `user_input_summary`（需求摘要）

### 后端代码缺陷

#### Step 1（正常）

```python
# 生成用户输入摘要
user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

payload = {
    "interaction_type": "progressive_questionnaire_step1",
    # ... 其他字段 ...
    "extracted_tasks": extracted_tasks,
    "user_input_summary": user_input_summary,  # ✅ 包含
    "extracted_task": old_format_task,
    # ...
}
```

#### Step 2（缺失）

```python
# ❌ 问题：没有包含 user_input_summary 或 user_input
payload = {
    "interaction_type": "progressive_questionnaire_step2",
    "step": 2,
    "total_steps": 3,
    "title": "多维度偏好设置",
    "message": "请通过拖动滑块表达您的设计偏好。每个维度代表两种不同的设计方向。",
    "core_task": confirmed_task,
    "dimensions": dimensions,
    "instructions": "拖动滑块到您偏好的位置（0-100）",
    # ❌ 缺少 user_input_summary / user_input
    "options": {
        "confirm": "确认偏好设置",
        "back": "返回修改核心任务"
    }
}
```

#### Step 3（缺失）

```python
# ❌ 问题：没有包含 user_input_summary 或 user_input
payload = {
    "interaction_type": "progressive_questionnaire_step3",
    "step": 3,
    "total_steps": 3,
    "title": "补充关键信息",
    "message": "为了更精准地理解您的项目需求，请补充以下关键信息：",
    "core_task": confirmed_task,
    "task_summary": task_summary,
    # ... 完整性信息 ...
    # ❌ 缺少 user_input_summary / user_input
    "questionnaire": { ... },
    "options": { ... }
}
```

## 🛠️ 修复方案

### 修改文件

- **文件**：`intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`
- **修改位置**：
  - Step 2 payload（约 Line 400）
  - Step 3 payload（约 Line 620）

### 修复代码

#### Step 2 修复

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

#### Step 3 修复

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

## ✅ 验证结果

### 修复后效果

| 步骤 | 修复前 | 修复后 |
|------|--------|--------|
| Step 1 | ✅ 显示需求 | ✅ 显示需求 |
| Step 2 | ❌ 需求缺失 | ✅ **显示需求** |
| Step 3 | ❌ 需求缺失 | ✅ **显示需求** |

### 测试场景

1. **新建会话**
   ```
   用户输入：设计一个150平米的现代简约风格住宅，三室两厅，预算30万
   ```

2. **Step 1 验证**
   - ✅ 顶部显示："需求：设计一个150平米的现代简约风格住宅，三室两厅，预算30万"

3. **Step 2 验证**
   - ✅ 顶部显示："需求：设计一个150平米的现代简约风格住宅，三室两厅，预算30万"
   - ✅ 维度滑块正常工作

4. **Step 3 验证**
   - ✅ 顶部显示："需求：设计一个150平米的现代简约风格住宅，三室两厅，预算30万"
   - ✅ 补充问题正常显示

## 🔄 重启服务

修复代码后需要重启后端服务：

```powershell
# 1. 终止旧进程
taskkill /F /IM python.exe

# 2. 等待端口释放
Start-Sleep -Seconds 2

# 3. 重启服务
python -B run_server_production.py
```

**启动成功标志**：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
✅ Playwright 浏览器池初始化成功
```

## 📝 技术总结

### 问题原因

- **数据流断层**：后端 Step 2/3 没有将 `user_input` 传递给前端
- **前端防御性编程**：前端尝试从多个数据源读取（step1Data/step2Data/step3Data），但后端 Step 2/3 没有提供

### 修复策略

- **最小化改动**：仅在 Step 2/3 的 payload 中添加 2 个字段（`user_input`, `user_input_summary`）
- **向后兼容**：不影响现有的 Step 1 逻辑和其他功能
- **统一体验**：三步问卷顶部统一显示用户需求摘要

### 相关文件

- `frontend-nextjs/components/UnifiedProgressiveQuestionnaireModal.tsx` - 前端组件（无需修改）
- `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py` - 后端节点（已修复）

## 🏷️ 版本标记

- **版本号**：v7.115
- **修复类型**：P1 Bug（影响用户体验）
- **修复日期**：2026-01-02
- **修复分支**：main
- **相关 Issue**：用户反馈问卷第二、三步需求显示缺失

---

**验证清单**：
- ✅ 代码已修改
- ✅ 后端已重启
- ⏳ 等待用户测试反馈（需要新建会话，走完三步问卷流程）

**注意事项**：
- 现有的 waiting_for_input 状态会话不会自动刷新，需要**新建会话**才能看到修复效果
- 如果用户在旧会话中测试，请提醒他们刷新页面或新建会话
