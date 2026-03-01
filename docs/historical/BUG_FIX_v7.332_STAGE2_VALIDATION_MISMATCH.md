# Bug修复报告: v7.332 Stage 2 验证规则不匹配

## 问题描述

**现象**: "多轮多次输出问题" - Stage 2 输出后出现3次重试，最终报错 "Must have 1-7 blocks, got 0"

**错误日志**:
```
[Stage 2] 尝试 1/3 → 验证失败: ['缺少必需部分: 您的核心需求']
[Stage 2] 尝试 2/3 → 验证失败: ['缺少必需部分: 您的核心需求']
[Stage 2] 尝试 3/3 → 验证失败: ['缺少必需部分: 您的核心需求']
❌ 深度分析失败: Must have 1-7 blocks, got 0
```

## 根因分析

1. **验证规则与prompt模板不匹配**：
   - `step1_deep_analysis_v3.yaml` 的验证规则要求输出包含 `"您的核心需求"`
   - 但 Stage 2 的 prompt 模板实际生成的标题是 `"我们如何理解您的需求"`
   - 导致验证始终失败，触发3次重试

2. **四步流程协调器中的硬编码规则**：
   - `_validate_output` 函数中有硬编码的 `required_sections`，要求 `"【接下来的搜索计划】"`
   - 但 v3.0 架构中，"接下来的搜索计划" 是 Step 2 的功能，Step 1 不应包含

3. **重复检测markers过时**：
   - `_trim_duplicate_output` 中的 markers 包含 `"您的核心需求："`
   - 需要更新为与 prompt 模板一致的格式

## 修复内容

### 1. step1_deep_analysis_v3.yaml (line 998-1000)

**修改前**:
```yaml
required_sections:
  - "您的核心需求"
  - "您将获得什么"
```

**修改后**:
```yaml
required_sections:
  - "我们如何理解您的需求"
  - "您将获得什么"
```

### 2. four_step_flow_orchestrator.py - `_validate_output` (line 1036-1038)

**修改前**:
```python
# 1. 检查是否包含必需的3个部分 (v2.0 格式)
required_sections = ["【您将获得什么】", "【我们如何理解您的需求】", "【接下来的搜索计划】"]
```

**修改后**:
```python
# 1. 检查是否包含必需的2个部分 (v3.0 格式)
# 注意："接下来的搜索计划" 是 Step 2 的内容，Step 1 不需要
required_sections = ["我们如何理解您的需求", "您将获得什么"]
```

### 3. four_step_flow_orchestrator.py - `_trim_duplicate_output` markers (line 145-156)

**修改前**:
```python
markers = [
    "方案高参来帮您",
    "【您将获得什么】",
    "**【您将获得什么】",
    "您的核心需求：",
    "您面临的挑战：",
    ...
]
```

**修改后**:
```python
markers = [
    "方案高参来帮您",
    "【您将获得什么】",
    "**【您将获得什么】",
    "【我们如何理解您的需求】",
    "**【我们如何理解您的需求】**",
    "您面临的挑战：",
    ...
]
```

## 影响范围

- **Step 1 深度分析**: 验证逻辑现在与 prompt 模板一致
- **重复检测**: markers 与当前输出格式匹配
- **无需更新其他 Step**: Step 2-4 不受影响

## 验证方法

运行以下测试确认修复有效：
```bash
cd intelligent_project_analyzer
python -m pytest tests/test_step1_integration_v3.py -v
```

或手动测试搜索功能，确认 Stage 2 输出不再触发重复重试。

## 版本信息

- **版本**: v7.332
- **修复日期**: 2025-01-08
- **相关文件**:
  - [step1_deep_analysis_v3.yaml](intelligent_project_analyzer/config/prompts/step1_deep_analysis_v3.yaml)
  - [four_step_flow_orchestrator.py](intelligent_project_analyzer/services/four_step_flow_orchestrator.py)
