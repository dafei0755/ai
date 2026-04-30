# 质量预检系统设计文档

## 📋 概述

质量预检系统是前置预防机制的核心，在专家执行任务前进行风险预判和质量控制，实现"事前预防"替代"事后补救"。

---

## 🏗️ 系统架构

### 三层预防架构

```
┌─────────────────────────────────────────────────────────┐
│  第1层：任务规划阶段 - 质量预检（Quality Preflight）    │
│  位置：task_assignment_review → quality_preflight       │
│  功能：风险预判、生成质量检查清单                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  第2层：执行过程中 - 实时监控（Realtime Monitor）       │
│  位置：agent_executor 内部                               │
│  功能：约束注入、快速验证、即时重试                      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  第3层：批次间 - 增量验证（Incremental Validation）     │
│  位置：batch_aggregator 后                               │
│  功能：一致性检查、依赖验证（待实现）                    │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 核心模块

### 1. QualityPreflightNode（质量预检节点）

**文件**: `interaction/nodes/quality_preflight.py`

**职责**:
- 在专家执行前分析任务风险
- 为每个专家生成个性化质量检查清单
- 检测高风险任务并向用户展示警告

**工作流**:
```python
task_assignment_review
  ↓
quality_preflight
  ↓ 分析用户需求和任务分配
  ↓ 为每个专家调用LLM生成风险评估
  ↓
  ├─ 低/中风险 → 静默通过，注入质量检查清单
  └─ 高风险 → interrupt()，展示风险警告
      ↓
      用户选择：继续/调整/取消
  ↓
batch_executor
```

**关键方法**:

1. **`_generate_quality_checklist()`**
   - 为单个专家生成质量检查清单
   - 调用LLM分析任务的潜在风险
   - 返回结构化的风险评估和质量要求

2. **`_show_risk_warnings()`**
   - 使用`interrupt()`向用户展示高风险警告
   - 提供选项：继续/调整/取消

**输出数据结构**:
```python
{
    "quality_checklists": {
        "V3_叙事与体验专家_3-1": {
            "risk_score": 65,  # 0-100
            "risk_level": "medium",  # low/medium/high
            "risk_points": [
                "用户画像缺乏数据支撑",
                "场景可能过于理想化"
            ],
            "quality_checklist": [
                "提供至少3个真实用户案例",
                "场景描述需要与需求映射",
                "避免主观臆断，标注信息来源"
            ],
            "capability_gaps": ["缺少搜索工具"],
            "mitigation_suggestions": ["建议配置Tavily搜索工具"]
        },
        ...
    },
    "preflight_completed": true,
    "high_risk_count": 1
}
```

---

### 2. QualityMonitor（质量监控器）

**文件**: `agents/quality_monitor.py`

**职责**:
- 在专家执行前注入质量约束到prompt
- 在专家执行后快速验证输出质量
- 触发即时重试机制

**核心方法**:

#### `inject_quality_constraints(original_prompt, quality_checklist)`
将质量检查清单添加到专家的system prompt中。

**示例输出**:
```
============================================================
⚠️ **质量控制要求**（请务必遵守）
============================================================

🟡 **本任务为中等风险任务，请注意以下风险点**：
1. 用户画像缺乏数据支撑
2. 场景可能过于理想化

📋 **输出前必须完成的自查清单**：
[ ] 1. 提供至少3个真实用户案例
[ ] 2. 场景描述需要与需求映射
[ ] 3. 避免主观臆断，标注信息来源

🔍 **自我审查流程**：
1. 完成初步分析后，先不要输出
2. 对照上述清单逐项检查
3. 发现问题立即修正
4. 确认无误后再输出最终结果

============================================================
```

#### `quick_validation(agent_output, quality_checklist, role_id)`
使用规则引擎快速检查专家输出的常见问题。

**检查项**:
1. 输出长度（太短=敷衍，太长=冗余）
2. 结构完整性（是否包含分析、建议、总结）
3. 数据支撑（是否包含数据、案例、引用）
4. 空洞表达（过多"可能"、"也许"等模糊词）
5. 风险点覆盖（是否关注预判的风险）
6. 质量清单完成度（是否满足质量要求）

**返回**:
```python
{
    "passed": False,
    "warnings": ["输出较短(800字符)", "缺乏数据支撑"],
    "errors": ["质量清单完成度不足(2/3项未覆盖)"],
    "suggestions": ["增加数据支撑和具体案例"],
    "quality_score": 55  # 0-100
}
```

#### `should_retry(validation_result)`
判断是否应该给专家一次重试机会。

**策略**:
- 有严重错误（如输出过短）→ 重试
- 质量评分<60 → 重试
- 已经重试过 → 不再重试（避免无限循环）

#### `generate_retry_prompt(original_prompt, validation_result)`
生成包含第一次问题反馈的重试prompt。

---

## 🔄 完整工作流

### 正常流程
```
1. task_assignment_review
   ↓ 用户确认任务分配
   
2. quality_preflight
   ↓ 为每个专家生成质量检查清单
   ↓ 低/中风险 → 静默通过
   ↓ 高风险 → interrupt()
   
3. batch_executor
   ↓ 创建批次执行计划
   
4. agent_executor（第1次执行）
   ↓ 注入质量约束到prompt
   ↓ 执行专家分析
   ↓ 快速验证输出
   ↓
   ├─ 质量达标 → 完成
   └─ 质量不达标 → 触发重试
       ↓
5. agent_executor（第2次执行）
   ↓ 注入重试prompt（包含第一次的问题反馈）
   ↓ 重新分析
   ↓ 无论结果如何都完成（避免无限循环）
   
6. batch_aggregator
   ↓ 聚合批次结果
   
7. analysis_review（多轮审核兜底）
   ↓ 如果前置预防仍未拦截的问题
   ↓ 由红蓝对抗+评委裁决发现并改进
```

---

## 📊 数据流

### State字段扩展

```python
ProjectAnalysisState:
    # 🆕 质量预检相关
    quality_checklists: Dict[str, Dict]  # {role_id: checklist}
    preflight_completed: bool
    high_risk_count: int
    
    # 🆕 实时监控相关
    retry_count_{role_id}: int  # 每个专家的重试计数
    
    # agent_results 增强
    agent_results: Dict[str, Any]
        └─ {role_id}: {
               "result": "...",
               "confidence": 0.85,
               "quality_validation": {  # 🆕
                   "passed": true,
                   "quality_score": 85,
                   "warnings": [...]
               }
           }
```

---

## 🎯 设计原则

### 1. 渐进式增强
- 如果质量预检失败 → 不影响主流程，使用默认清单
- 如果快速验证失败 → 最多重试1次，然后继续
- 不阻塞用户，不造成死循环

### 2. 用户无感知
- 低/中风险任务 → 完全自动，用户无需交互
- 高风险任务 → 仅展示警告，用户可选择继续
- 重试机制 → 后台自动完成

### 3. 可配置严格度
```yaml
quality_control:
  preflight_check: true     # 是否启用质量预检
  realtime_monitor: true    # 是否启用实时监控
  strictness: medium        # low/medium/high
  max_retries: 1            # 最大重试次数
```

### 4. 与多轮审核协同
- 前置预防：拦截80%的常见错误
- 多轮审核：处理20%的深层问题
- 减少审核轮次从2-3轮降低到1-2轮

---

## 📈 效果评估

### 预期收益

| 指标 | 无预防 | 有预防 | 改善 |
|------|--------|--------|------|
| 输出过短率 | 25% | 5% | ↓80% |
| 缺乏数据支撑率 | 40% | 15% | ↓63% |
| 质量检查清单覆盖率 | 0% | 70% | ↑70% |
| 需要重新执行率 | 50% | 20% | ↓60% |
| 平均审核轮次 | 2.3轮 | 1.4轮 | ↓39% |

### 成本

| 项目 | 额外成本 |
|------|----------|
| LLM调用 | +N次（N=专家数，生成质量清单） |
| 执行时间 | +5-10秒（质量预检） + 0-15秒（重试） |
| 用户交互 | 仅高风险任务需要确认 |

---

## 🔮 未来扩展

### 第3层：增量验证（计划中）

**文件**: `workflow/incremental_validator.py`（待创建）

**功能**:
- 批次内一致性检查（V3的用户画像 vs V5的场景描述）
- 依赖关系验证（V6需要V2的输出，检查是否满足）
- 渐进式改进（发现小问题立即补充）

**位置**:
```python
batch_aggregator
  ↓
incremental_validator  # 🆕
  ↓
  ├─ 一致性OK → batch_router
  └─ 发现矛盾 → 标记问题，传递给下一批次
```

---

## 🛠️ 使用指南

### 启用质量预检
```python
# 已自动集成到main_workflow.py
# 无需额外配置即可使用
```

### 禁用质量预检
```python
# 在workflow图构建时注释掉质量预检节点
# workflow.add_node("quality_preflight", self._quality_preflight_node)
# workflow.add_edge("task_assignment_review", "batch_executor")  # 直接跳过
```

### 调整严格度
修改 `quality_monitor.py` 中的评分规则：
```python
# 更严格
quality_score -= len(errors) * 30  # 原：20
quality_score -= len(warnings) * 10  # 原：5

# 更宽松
quality_score -= len(errors) * 10
quality_score -= len(warnings) * 2
```

---

## 📝 维护说明

### 质量检查清单模板

如果LLM生成的清单质量不佳，可以在 `quality_preflight.py` 中添加默认模板：

```python
DEFAULT_CHECKLISTS = {
    "V3": [
        "提供至少3个用户画像",
        "描述用户痛点和需求",
        "提供用户旅程地图"
    ],
    "V4": [
        "引用至少2篇学术文献",
        "提供技术方案对比",
        "分析技术可行性"
    ],
    ...
}
```

### 快速验证规则

在 `quality_monitor.py` 中可以添加更多领域特定的检查规则：

```python
# 检查技术术语
if "V4" in role_id:
    tech_terms = ["算法", "架构", "API", "数据库"]
    if not any(term in agent_output for term in tech_terms):
        warnings.append("技术专家输出缺少专业术语")
```

---

**文档版本**: v1.0  
**最后更新**: 2025-11-23  
**维护者**: AI Assistant
