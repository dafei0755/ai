# BUGFIX v7.129: 问卷Step 3自动跳过问题修复 + 禁止跳过所有步骤

**创建时间**: 2026-01-04
**版本**: v7.129
**问题会话**: `8pdwoxj8-20260104105835-146b8fdd`
**状态**: ✅ 已修复

---

## 🆕 用户需求变更

**用户明确要求**: "问卷3个步骤，都不可以跳过"

**修复策略调整**:
- ~~方案A: 调整过滤逻辑（降低跳过概率）~~
- ✅ **方案B: 完全禁止跳过 + 最小问题兜底机制**

---

## 问题描述

**用户报告**: "问卷，第二步信息补全，自动跳过了，并一直转圈圈"

**症状**:
1. **第1步** (任务梳理) 完成 → 用户点击确认
2. **第2步** (信息补全) **被自动跳过**（应该显示问卷但没有）
3. 前端显示**无限加载转圈**，没有进入 **第3步** (雷达图)

---

## 📋 v7.128 问卷顺序说明

| 实际顺序 | 函数名 | 功能 | 用户看到的步骤 |
|---------|--------|------|--------------|
| **第1步** | `progressive_step1_core_task` | 任务梳理 | step: 1/3 |
| **第2步** | `progressive_step3_gap_filling` | 信息补全 | step: 2/3 |
| **第3步** | `progressive_step2_radar` | 雷达图 | step: 3/3 |

**注意**: 函数名保留历史命名（step1/step2/step3），但执行顺序为 **1 → 3 → 2** (v7.128调整)

---

## 根本原因

### 原因1: TaskCompletenessAnalyzer 过滤逻辑过于激进 (v7.107.1)

**问题代码**: `task_completeness_analyzer.py` Line 172-190

```python
# v7.107.1 原逻辑
if dimension == "时间节点":
    design_focus_keywords = [
        "如何", "怎样", "怎么", "方案", "策略",
        "体面感", "价值感", "氛围", "调性", "格调",  # ⚠️ 这些是常见词！
        "设计手法", "设计方向", "视觉", "空间"
    ]
    # ⚠️ 只要包含任意1个关键词，就返回 None（非关键）
    if any(kw in all_text for kw in design_focus_keywords):
        return None
```

**触发条件**:
- 用户输入包含 `"如何、怎样、方案、策略、氛围、空间"` 等**常见词汇** → `时间节点` 维度被过滤
- `基本信息` 和 `核心目标` 维度 → **始终**被过滤
- 如果 `预算约束`、`交付要求`、`特殊需求` 也被识别为已覆盖 → `critical_gaps = []`
- **结果**: **第2步**（信息补全）被跳过，直接跳转到 **第3步**（雷达图）

---

## 修复方案

### ✅ 最终方案: 完全禁止跳过 + 最小问题兜底机制

**文件**: `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`

**核心修改**: Line 694-720

#### 修改1: 删除跳过逻辑

```python
# 🔥 删除以下代码（Line 696-700，原跳过逻辑）
# if not critical_gaps:
#     logger.info("✅ 任务信息完整，无需补充，跳过第2步（信息补全）")
#     logger.info("🔄 准备跳转到第3步（雷达图）...")
#     update_dict = {...}
#     return Command(update=update_dict, goto="progressive_step2_radar")
```

#### 修改2: 添加最小问题兜底机制

```python
# 🆕 v7.129: 禁止跳过第2步（信息补全） - 即使无关键缺失，也生成最小问题集
# 用户需求：问卷3个步骤都不可以跳过
MIN_QUESTIONS = 2  # 至少生成2个基础问题

# 🆕 v7.129: 根据 critical_gaps 是否为空，调整问题生成策略
if not critical_gaps:
    # 无关键缺失 - 生成基础通用问题（兜底机制）
    logger.info("⚠️ [第2步] 无关键缺失，生成基础通用问题（最小问题集）")
    questions = analyzer.generate_gap_questions(
        missing_dimensions=completeness.get("missing_dimensions", []),
        critical_gaps=[],
        confirmed_tasks=confirmed_tasks,
        existing_info_summary=existing_info_summary,
        target_count=MIN_QUESTIONS,  # 只生成2个基础问题
    )
    logger.info(f"📝 [基础问题集] 生成 {len(questions)} 个通用问题")

elif enable_llm_generation:
    # 有关键缺失 - 使用LLM智能生成（原逻辑）
    ...
```

#### 修改3: 动态调整问卷文案

```python
# 🆕 v7.129: 根据是否有关键缺失，调整问卷文案
if not critical_gaps:
    # 无关键缺失 - 友好提示
    title = "补充基础信息"
    message = "您的需求信息已基本完整！以下是一些补充问题，帮助我们提供更精准的方案："
    introduction = f"信息完整度: {int(completeness.get('completeness_score', 0) * 100)}% | 以下问题为选填，可帮助优化方案"
    note = "这些问题均为选填，您可以根据实际情况选择性回答"
else:
    # 有关键缺失 - 原文案
    title = "补充关键信息"
    message = "为了更精准地理解您的项目需求，请补充以下关键信息："
    introduction = f"已完整度: {int(completeness.get('completeness_score', 0) * 100)}% | 缺失维度: {', '.join(completeness.get('missing_dimensions', []))}"
    note = "这些问题涉及预算、时间、交付等关键决策点，请根据实际情况作答"
```

---

### 辅助修复: 调整过滤逻辑（已保留）

**文件**: `intelligent_project_analyzer/services/task_completeness_analyzer.py`

**修改位置**: Line 167-184（已在方案A中完成）

```python
# 🔧 v7.129: 提高触发阈值，避免过度过滤
if dimension == "时间节点":
    design_focus_keywords = ["设计手法", "设计方向"]  # 只保留2个特定词
    matched_count = sum(1 for kw in design_focus_keywords if kw in all_text)
    if matched_count >= 2:  # 至少匹配2个才过滤
        return None
```

**说明**: 虽然现在即使被过滤也会生成基础问题，但保留此修复可减少误过滤。

---

## 验证方法

### 1. 检查后端日志

**正常情况应该看到**:
```
❓ [v7.80.6 第2步] 核心任务信息完整性查漏补缺
⏱️ [第2步] 完整性分析耗时: 0.05秒
📊 任务信息完整性评分: 0.65
   已覆盖维度: ['基本信息', '核心目标']
   缺失维度: ['预算约束', '时间节点', '交付要求']
   ⚠️ 关键缺失点: [{'dimension': '预算约束', ...}, {'dimension': '时间节点', ...}] (count=2)
🛑 [第2步] 即将调用 interrupt()，等待用户输入...
```

**如果被跳过（修复前）**:
```
⚠️ 关键缺失点: [] (count=0)  ⚠️ 空列表！
✅ 任务信息完整，无需补充，跳过第2步（信息补全）
🔄 准备跳转到第3步（雷达图）...
```

**如果被跳过（修复后 - 应该很少发生）**:
```
🔍 [过滤] 时间节点维度降级：匹配2个设计方法论关键词
⚠️ 关键缺失点: [] (count=0)
⚠️ [第2步] 无关键缺失，生成基础通用问题（最小问题集）
📝 [基础问题集] 生成 2 个通用问题
🛑 [第2步] 即将调用 interrupt()，等待用户输入...
```

---

### 2. 测试案例

**案例1: 普通设计需求（应该正常进入第2步）**
- 用户输入: "我想设计一个现代简约风格的办公室，希望空间氛围专业而舒适"
- 修复前: 包含 "空间"、"氛围" → 时间节点被过滤 → 可能跳过第2步
- 修复后: 不匹配 "设计手法" 或 "设计方向" → **正常进入第2步** ✅

**案例2: 设计方法论研究（触发最小问题兜底）**
- 用户输入: "研究现代设计手法和设计方向的演变趋势"
- 修复前: 包含 "设计手法"、"设计方向" → 跳过第2步
- 修复后: 匹配2个关键词 → `critical_gaps = []` → **触发最小问题兜底（显示2个基础问题）** ✅

---

## 影响范围

**受影响的模块**:
- ✅ `task_completeness_analyzer.py` - 核心过滤逻辑
- ✅ `progressive_questionnaire.py` - 第2步（信息补全）节点日志

**不影响**:
- 第1步 (任务梳理)
- 第3步 (雷达图)
- 其他维度的过滤逻辑（预算约束、交付要求等保持不变）

---

## 相关文档

- **问题排查计划**: `C:\Users\SF\.claude\plans\immutable-wiggling-hinton.md`
- **性能优化修复**: `docs/BUGFIX_v7.129_STEP2_PERFORMANCE.md` (第一个问题)
- **问卷系统架构**: `docs/IMPLEMENTATION_v7.129_QUESTIONNAIRE_ARCHITECTURE.md`

---

## 版本历史

- **v7.107.1**: 引入智能降级逻辑（初衷是减少不必要的时间节点问题）
- **v7.129**: 修复过度跳过问题，提高触发阈值，增强日志
