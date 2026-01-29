# 问卷汇总节点 questionnaire_responses 空值错误修复 (v7.143)

## 📋 问题描述

**日期**: 2026-01-06
**版本**: v7.143
**问题**: 渐进式问卷（Progressive Questionnaire）三步流程完成后，问卷汇总节点（questionnaire_summary）报错：

```
AttributeError: 'NoneType' object has no attribute 'get'
File "questionnaire_summary.py", line 122, in _extract_questionnaire_data
    gap_filling = questionnaire_responses.get("gap_filling", {})
```

**影响**: 用户完成问卷三步（任务梳理 → 信息补全 → 雷达图）后，系统无法生成结构化需求文档，导致工作流中断。

---

## 🔍 根因分析

### 1. 数据流断裂

渐进式问卷的三个步骤节点**从未正确设置** `questionnaire_responses` 字段：

- **Step 1（任务梳理）**: 设置了 `confirmed_core_tasks`，但**未设置** `questionnaire_responses`（跳过场景除外）
- **Step 2（信息补全）**: 设置了 `gap_filling_answers` 和 `questionnaire_summary`，但**未同步到** `questionnaire_responses`
- **Step 3（雷达图）**: 设置了 `radar_dimension_values` 和 `radar_analysis_summary`，但**未设置** `questionnaire_responses`

### 2. 问卷汇总节点的期望

问卷汇总节点 `_extract_questionnaire_data` 方法尝试从 `questionnaire_responses` 字段提取数据：

```python
# Step2: 信息补全（可能在gap_filling_answers或questionnaire_responses中）
gap_filling = state.get("gap_filling_answers", {})
if not gap_filling:
    questionnaire_responses = state.get("questionnaire_responses", {})  # ❌ 返回 None
    gap_filling = questionnaire_responses.get("gap_filling", {})        # ❌ NoneType.get() 崩溃
```

由于 `questionnaire_responses` 为 `None`，调用 `.get()` 方法触发 `AttributeError`。

### 3. 旧问卷流程的对比

旧的 `calibration_questionnaire` 流程在 `calibration_node.py` 中正确设置了该字段：

```python
updated_state["questionnaire_responses"] = summary_payload
```

但新的渐进式问卷流程缺少对应的设置逻辑。

---

## ✅ 修复方案

### 修复 1: Step 2（信息补全）节点同步数据

**文件**: `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`
**位置**: `step3_gap_filling` 方法（约1135-1160行）

**修改**: 在返回的 `update_dict` 中添加 `questionnaire_responses` 字段，复用已生成的 `questionnaire_summary` 数据。

```python
# 🆕 v7.80.6: 保存任务完整性分析和补充答案
update_dict = {
    "task_completeness_analysis": completeness,
    "task_gap_filling_questionnaire": {...},
    "gap_filling_answers": answers,
    "progressive_questionnaire_step": 2,
    "questionnaire_summary": questionnaire_summary,  # 兼容旧字段
    "questionnaire_responses": questionnaire_summary,  # 🔧 v7.143: 同步到 questionnaire_responses
    "calibration_processed": True,
    "completeness_analysis": completeness,
}
```

**理由**: `questionnaire_summary` 已经包含了所有三步问卷的数据整合，直接复用避免重复构建。

---

### 修复 2: Step 3（雷达图）节点整合数据

**文件**: `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`
**位置**: `step2_radar` 方法（约774-795行）

**修改**: 在确认雷达图后，构建 `questionnaire_responses` 结构，整合前两步数据 + 雷达图数据。

```python
# 分析雷达图
analyzer = RadarGapAnalyzer()
analysis = analyzer.analyze(dimension_values, dimensions)

# 🔧 v7.143: 构建 questionnaire_responses 数据结构（修复问卷汇总节点空值错误）
existing_responses = state.get("questionnaire_responses") or {}
questionnaire_responses = {
    **existing_responses,  # 保留 Step 2 设置的数据
    "radar_dimensions": dimensions,
    "dimension_values": dimension_values,
    "analysis_summary": analysis,
    "radar_profile_label": analysis.get("profile_label", ""),
    "timestamp": datetime.now().isoformat(),
}

update_dict = {
    "selected_radar_dimensions": dimensions,
    "radar_dimension_values": dimension_values,
    "radar_analysis_summary": analysis,
    "progressive_questionnaire_step": 2,
    "questionnaire_responses": questionnaire_responses,  # 🔧 v7.143: 整合雷达图数据
}
```

**理由**: 确保最终的 `questionnaire_responses` 包含完整的三步问卷数据。

---

### 修复 3: 问卷汇总节点添加防御性代码

**文件**: `intelligent_project_analyzer/interaction/nodes/questionnaire_summary.py`
**位置**: `_extract_questionnaire_data` 方法（约122行）

**修改**: 添加 `or {}` 防御性代码，避免 `None.get()` 崩溃。

```python
# Step2: 信息补全（可能在gap_filling_answers或questionnaire_responses中）
gap_filling = state.get("gap_filling_answers", {})
if not gap_filling:
    # 🔧 v7.143: 添加防御性代码，避免 questionnaire_responses 为 None 时崩溃
    questionnaire_responses = state.get("questionnaire_responses") or {}
    gap_filling = questionnaire_responses.get("gap_filling", {})
```

**理由**: 提供最后一道防线，即使 `questionnaire_responses` 为 `None` 也不会崩溃。

---

## 🧪 测试验证

### 单元测试

创建了 `tests/test_questionnaire_responses_fix.py`，测试三种场景：

1. ✅ `questionnaire_responses` 为 `None` 时不崩溃
2. ✅ `questionnaire_responses` 有效数据时正常工作
3. ✅ 优先使用 `gap_filling_answers` 字段

```bash
$ python -m pytest tests/test_questionnaire_responses_fix.py -v
======================== 3 passed in 1.24s ========================
```

### 集成测试

用户场景验证：
1. 输入需求："让安藤忠雄为一个离家多年的50岁男士设计一座田园民居，四川广元农村、300平米，室内设计师职业。"
2. Step 1 确认 7 个核心任务 ✅
3. Step 2 回答 6 个补充问题 ✅
4. Step 3 确认 9 个雷达图维度 ✅
5. **问卷汇总节点成功生成结构化需求文档** ✅

---

## 📚 相关文档

- **State 字段定义**: `intelligent_project_analyzer/core/state.py` (Line 135+)
- **渐进式问卷节点**: `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`
- **问卷汇总节点**: `intelligent_project_analyzer/interaction/nodes/questionnaire_summary.py`
- **旧问卷流程参考**: `intelligent_project_analyzer/interaction/nodes/calibration_node.py`

---

## 🎯 影响范围

### ✅ 受益场景

1. **渐进式问卷流程**: 用户完成三步问卷后，系统能正常进入问卷汇总和需求生成环节
2. **向后兼容**: 旧的 `calibration_questionnaire` 流程不受影响（已正确设置 `questionnaire_responses`）
3. **数据完整性**: `questionnaire_responses` 包含完整的三步问卷数据，便于后续分析和调试

### ⚠️ 注意事项

1. **数据结构变更**: `questionnaire_responses` 现在包含两部分：
   - Step 2 设置的 `questionnaire_summary` 数据（完整结构）
   - Step 3 追加的雷达图数据（`radar_dimensions`, `dimension_values`, `analysis_summary`）

2. **历史会话**: 修复前创建的会话（`questionnaire_responses` 为 `None`）不受影响，因为防御性代码会处理该情况。

---

## 🔄 后续优化建议

### 1. 统一数据整合逻辑

当前 `questionnaire_responses` 数据由多个节点分步设置：
- Step 2 设置基础数据
- Step 3 追加雷达图数据

**建议**: 在 Step 3 完成后，调用一个统一的 `_build_final_questionnaire_responses` 方法，从 state 中提取所有三步数据，构建完整的 `questionnaire_responses` 结构。

### 2. 数据格式标准化

定义 `questionnaire_responses` 的标准格式（JSON Schema），确保：
- 所有节点遵循相同的数据结构
- 便于前端解析和展示
- 便于后续分析和报告生成

### 3. 迁移旧问卷流程

逐步将旧的 `calibration_questionnaire` 流程迁移到新的渐进式问卷框架，统一数据格式和工作流逻辑。

---

## 📝 总结

| 修复项 | 位置 | 影响 |
|--------|------|------|
| Step 2 同步数据 | `progressive_questionnaire.py:1135-1160` | 确保 `questionnaire_responses` 包含基础数据 |
| Step 3 整合数据 | `progressive_questionnaire.py:774-795` | 追加雷达图数据到 `questionnaire_responses` |
| 防御性代码 | `questionnaire_summary.py:122` | 避免 `None.get()` 崩溃，提供最后防线 |

**修复前**: 三步问卷完成 → 问卷汇总节点崩溃 (`AttributeError`) → 工作流中断
**修复后**: 三步问卷完成 → 问卷汇总节点正常执行 → 生成结构化需求文档 → 继续工作流

✅ 修复完成，测试通过，问题解决！
