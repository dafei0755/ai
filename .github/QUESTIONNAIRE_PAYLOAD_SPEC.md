# 三步问卷 Payload 规范 - 快速参考

> **目的**: 防止 Step 2/3 再次丢失 user_input 字段（v7.115修复）
> **适用文件**: `progressive_questionnaire.py`
> **最后更新**: 2026-01-02

---

## 🎯 黄金规则

**所有 `interrupt()` payload 必须包含以下字段：**

```python
# 🔒 必需字段（所有步骤通用）
"user_input": state.get("user_input", ""),           # 完整需求
"user_input_summary": user_input[:100] + "...",      # 前100字符摘要
```

---

## ✅ 标准模板

### Step 1: 任务梳理

```python
def step1_core_task(state: ProjectAnalysisState):
    user_input = state.get("user_input", "")
    user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

    payload = {
        "interaction_type": "progressive_questionnaire_step1",
        "step": 1,
        "total_steps": 3,
        "title": "任务梳理",
        "message": "...",
        # 🔒 必需字段
        "user_input": user_input,
        "user_input_summary": user_input_summary,
        # Step 1 特有字段
        "extracted_tasks": extracted_tasks,
        "options": {...}
    }

    user_response = interrupt(payload)
    # ...
```

### Step 2: 雷达图

```python
def step2_radar(state: ProjectAnalysisState):
    # 🔧 v7.115: 获取用户原始输入
    user_input = state.get("user_input", "")
    user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

    payload = {
        "interaction_type": "progressive_questionnaire_step2",
        "step": 2,
        "total_steps": 3,
        "title": "偏好雷达图",
        "message": "...",
        # 🔒 必需字段（v7.115修复）
        "user_input": user_input,
        "user_input_summary": user_input_summary,
        # Step 2 特有字段
        "dimensions": dimensions,
        "core_task": confirmed_task,
        "options": {...}
    }

    user_response = interrupt(payload)
    # ...
```

### Step 3: 信息补全

```python
def step3_gap_filling(state: ProjectAnalysisState):
    # 🔧 v7.115: 获取用户原始输入
    user_input = state.get("user_input", "")
    user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

    payload = {
        "interaction_type": "progressive_questionnaire_step3",
        "step": 3,
        "total_steps": 3,
        "title": "补充关键信息",
        "message": "...",
        # 🔒 必需字段（v7.115修复）
        "user_input": user_input,
        "user_input_summary": user_input_summary,
        # Step 3 特有字段
        "task_summary": task_summary,
        "questionnaire": {...},
        "options": {...}
    }

    user_response = interrupt(payload)
    # ...
```

---

## 🔍 前端依赖说明

### 前端组件

**文件**: `frontend-nextjs/components/UnifiedProgressiveQuestionnaireModal.tsx`

**读取逻辑**（Line ~1140）:
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

**前端期望**:
- 优先使用完整的 `user_input`
- 如果不存在，回退到 `user_input_summary`（前100字符）
- 如果当前步骤数据缺失，尝试从其他步骤读取

---

## 🚨 常见错误

### ❌ 错误示例 1: 忘记添加字段

```python
# ❌ 错误：缺少 user_input 和 user_input_summary
payload = {
    "interaction_type": "progressive_questionnaire_step2",
    "step": 2,
    "dimensions": dimensions,
    "options": {...}
}
```

**后果**: 前端顶部需求显示为空白

### ❌ 错误示例 2: 只添加一个字段

```python
# ❌ 错误：只添加 user_input_summary，没有 user_input
payload = {
    "interaction_type": "progressive_questionnaire_step2",
    "user_input_summary": user_input_summary,  # ⚠️ 不够完整
    "dimensions": dimensions,
}
```

**后果**: 前端可以显示摘要，但无法展开查看完整需求

### ❌ 错误示例 3: 字段名错误

```python
# ❌ 错误：字段名拼写错误
payload = {
    "interaction_type": "progressive_questionnaire_step2",
    "userInput": user_input,           # ❌ 应该是 user_input（下划线）
    "user_input_sumary": summary,      # ❌ 拼写错误（summary → sumary）
}
```

**后果**: 前端无法识别字段，显示为空白

---

## ✅ 自检清单

修改 `progressive_questionnaire.py` 后，确认：

- [ ] ✅ Step 1 payload 包含 `user_input` 和 `user_input_summary`
- [ ] ✅ Step 2 payload 包含 `user_input` 和 `user_input_summary`
- [ ] ✅ Step 3 payload 包含 `user_input` 和 `user_input_summary`
- [ ] ✅ 从 `state.get("user_input", "")` 获取原始输入
- [ ] ✅ user_input_summary 截取前100字符 + "..."
- [ ] ✅ 字段名使用下划线（`user_input_summary`，不是 `userInputSummary`）
- [ ] ✅ 重启后端服务（`python -B run_server_production.py`）
- [ ] ✅ 新建会话测试三步问卷，验证顶部需求显示

---

## 🔧 测试命令

### 单元测试（建议添加）

```python
# tests/test_progressive_questionnaire_payloads.py

import pytest
from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
    ProgressiveQuestionnaireNode
)

def test_all_steps_contain_user_input():
    """验证所有步骤的 interrupt payload 都包含 user_input 字段"""
    state = {
        "user_input": "设计一个150平米的现代简约风格住宅，三室两厅，预算30万"
    }

    # Step 1
    # ... 模拟调用 step1_core_task，验证 payload

    # Step 2
    # ... 模拟调用 step2_radar，验证 payload

    # Step 3
    # ... 模拟调用 step3_gap_filling，验证 payload
```

### 手动测试步骤

```bash
# 1. 重启后端
taskkill /F /IM python.exe
python -B run_server_production.py

# 2. 打开前端
# http://localhost:3000

# 3. 新建会话，输入需求
# "设计一个150平米的现代简约风格住宅"

# 4. 验证每一步顶部是否显示需求
# - Step 1: ✅ "需求：设计一个150平米..."
# - Step 2: ✅ "需求：设计一个150平米..."
# - Step 3: ✅ "需求：设计一个150平米..."
```

---

## 📚 相关文档

- 📝 [v7.115 完整修复报告](../QUESTIONNAIRE_USER_INPUT_FIX_v7.115.md)
- 🐛 [历史修复记录](.github/historical_fixes/questionnaire_user_input_display_fix.md)
- 📊 [CHANGELOG.md](../CHANGELOG.md#v7115---2026-01-02)
- 🎯 [前端组件源码](../frontend-nextjs/components/UnifiedProgressiveQuestionnaireModal.tsx)

---

## 💡 最佳实践

### 建议 1: 使用公共方法（可选优化）

```python
def _build_base_payload(state: ProjectAnalysisState) -> dict:
    """构建所有步骤通用的 payload 基础字段"""
    user_input = state.get("user_input", "")
    user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

    return {
        "user_input": user_input,
        "user_input_summary": user_input_summary,
    }

# 使用方式
def step2_radar(state: ProjectAnalysisState):
    base_payload = _build_base_payload(state)

    payload = {
        **base_payload,  # 🔒 自动包含 user_input 和 user_input_summary
        "interaction_type": "progressive_questionnaire_step2",
        "step": 2,
        "dimensions": dimensions,
        # ...
    }
```

### 建议 2: 代码审查要点

修改 `progressive_questionnaire.py` 的 PR 时，reviewer 应检查：
1. ✅ 所有 `interrupt()` 调用的 payload 是否包含 `user_input` 字段
2. ✅ 是否正确从 `state.get("user_input", "")` 获取
3. ✅ `user_input_summary` 的生成逻辑是否正确（前100字符）

---

**版本**: v1.0
**创建日期**: 2026-01-02
**维护者**: AI Assistant
**关联 Bug**: v7.115 问卷第二、三步需求显示缺失
