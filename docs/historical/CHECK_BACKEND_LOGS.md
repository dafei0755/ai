# 后端日志检查清单

## 问题：任务数量只有6个且质量差

请在后端日志中查找以下关键信息：

---

## 1. 复杂度分析结果

查找日志行：
```
[TaskComplexityAnalyzer] 复杂度=X.XX, 建议任务数=X-X
```

**期望值**：
- 简单项目：复杂度 < 0.12，建议 8-13个
- 中等项目：复杂度 0.12-0.25，建议 18-23个
- 复杂项目：复杂度 0.25-0.45，建议 28-36个
- 超大型：复杂度 > 0.45，建议 40-52个

**如果复杂度过低**：说明输入信息不足，需要增加详细度

---

## 2. LLM生成的任务数量

查找日志行：
```
[CoreTaskDecomposer] 成功解析 X 个任务
```

**如果数量 < 推荐最小值**：
- 应该看到警告：`⚠️ LLM生成了X个任务，少于推荐最小值Y（缺少Z个）`
- 应该看到补充：`🔄 强制请求LLM补充生成Z个额外任务...`
- 应该看到结果：`✅ 补充生成X个任务` 或 `❌ 补充任务失败`

---

## 3. JSON解析错误

查找日志行：
```
[CoreTaskDecomposer] JSON 解析失败
[CoreTaskDecomposer] 使用回退策略提取任务
```

**如果出现解析错误**：
- LLM返回的格式不正确
- 可能是BOM字符、双花括号等问题影响了LLM输出

---

## 4. LLM原始响应（Debug级别）

查找日志行：
```
[CoreTaskDecomposer] LLM 原始响应 (前500字符): ...
```

**检查内容**：
- 是否包含完整的JSON结构
- 是否有格式错误（如双花括号 `{{`）
- 任务数量是否正确

---

## 5. Few-shot示例注入

查找日志行：
```
[Few-shot v7.999.5] 已注入示例: XXX (Y任务) - 目标: X-X任务
```

**检查内容**：
- 是否成功注入Few-shot示例
- 目标任务数是否正确

---

## 6. 混合策略（v7.999.4）

查找日志行：
```
[混合策略 v7.999.4] 任务分配: LLM=X-X个 + 规则补充最多Y个
```

**检查内容**：
- LLM任务数范围是否正确
- 是否启用了规则补充

---

## 快速诊断命令

在后端运行目录执行：

```bash
# 查找最近的任务分解日志
grep -A 5 "TaskComplexityAnalyzer" logs/app.log | tail -50

# 查找任务解析结果
grep "成功解析.*个任务" logs/app.log | tail -10

# 查找补充任务日志
grep "少于推荐最小值\|补充生成" logs/app.log | tail -20

# 查找JSON解析错误
grep "JSON 解析失败\|回退策略" logs/app.log | tail -20
```

---

## 临时解决方案

如果日志显示复杂度过低，可以临时降低阈值：

### 方案A：修改阈值（临时）

编辑 `intelligent_project_analyzer/services/core_task_decomposer.py`，第150-161行：

```python
# 原始阈值
if complexity_score < 0.12:
    recommended_min = 8
    recommended_max = 13
elif complexity_score < 0.25:
    recommended_min = 18
    recommended_max = 23

# 临时降低阈值（让更多项目进入中等范围）
if complexity_score < 0.08:  # 从0.12降到0.08
    recommended_min = 8
    recommended_max = 13
elif complexity_score < 0.20:  # 从0.25降到0.20
    recommended_min = 18
    recommended_max = 23
```

### 方案B：强制最小任务数（临时）

在第150行前添加：

```python
# 🔧 临时修复：强制最小任务数为18
if complexity_score < 0.50:  # 除了超大型项目，都至少18个
    recommended_min = max(18, recommended_min)
```

---

## 下一步

请提供：
1. 你的实际输入内容
2. 后端日志中的上述关键信息
3. 是否看到任何错误或警告

这样我可以精确定位问题并给出针对性修复方案。
