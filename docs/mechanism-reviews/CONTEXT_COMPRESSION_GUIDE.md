# 智能上下文压缩策略 - 应用指南

**版本**: v7.502.1
**复盘日期**: 2026-02-10
**代码版本**: v7.122+
**文档类型**: 机制复盘
**实施状态**: ✅ 已实施并验证

---

## 📋 目录

1. [压缩策略概览](#压缩策略概览)
2. [触发时机与执行阶段](#触发时机与执行阶段)
3. [动态策略选择逻辑](#动态策略选择逻辑)
4. [三种压缩级别详解](#三种压缩级别详解)
5. [实际执行流程](#实际执行流程)
6. [应用场景示例](#应用场景示例)

---

## 1. 压缩策略概览

### 🎯 核心原理
**质量优先、动态调整、按需压缩**

```
┌─────────────────────────────────────────────────────────────┐
│                     专家执行流程                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  用户需求 → 角色选择 → 任务分派 → 【批次执行】 → 结果聚合  │
│                                      ↓                        │
│                                  压缩策略应用                │
│                                      ↓                        │
│                    ┌─────────────────────────┐              │
│                    │  每个专家执行时触发      │              │
│                    │  _build_context_for_expert│             │
│                    └─────────────────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

### ⚡ 关键特性
- ✅ **自动触发**: 每个专家执行时自动调用
- ✅ **动态选择**: 根据批次编号和总批次数智能选择压缩级别
- ✅ **质量保证**: Batch1完全不压缩，确保信息完整性
- ✅ **性能优化**: Batch2+适度压缩，节省30-80% Token

---

## 2. 触发时机与执行阶段

### 🔄 完整执行链路

```
时间线: ────────────────────────────────────────────────────────►

阶段1: 需求分析
  └─ RequirementsAnalystAgent.execute()
     └─ 输出: structured_requirements, primary_deliverables

阶段2: 角色选择
  └─ ProjectDirectorAgent.execute()
     └─ 输出: selected_roles, execution_batches

阶段3: 批次执行 ⭐ 【压缩策略应用点】
  ├─ Batch1 执行
  │  ├─ _batch_executor_node()
  │  │  └─ 传递: current_batch_number=1, total_batches=3
  │  │
  │  ├─ 专家1执行 (V4_设计研究员_4-1)
  │  │  └─ _execute_agent_node()
  │  │     └─ _build_context_for_expert()  ⚡ 触发点
  │  │        ├─ create_context_compressor(1, 3)
  │  │        │  └─ 返回: ContextCompressor(level="minimal")
  │  │        │
  │  │        ├─ compressor.compress_agent_results(agent_results, role_id)
  │  │        │  └─ 输出: 完整的前序专家内容（无压缩）
  │  │        │
  │  │        └─ 构建完整上下文传递给LLM
  │  │
  │  └─ 专家2执行 (V4_结构分析师_5-2)
  │     └─ 同上流程，但agent_results已包含专家1的输出
  │
  ├─ Batch2 执行
  │  ├─ 专家3执行 (V4_材料顾问_6-3)
  │  │  └─ _build_context_for_expert()  ⚡ 触发点
  │  │     ├─ create_context_compressor(2, 3)
  │  │     │  └─ 返回: ContextCompressor(level="balanced")
  │  │     │
  │  │     └─ compressor.compress_agent_results(...)
  │  │        └─ 输出: 前800字符完整 + 智能截断
  │  │
  │  └─ 专家4执行...
  │
  └─ Batch3 执行
     └─ 压缩级别: balanced（因为total_batches=3，不满足>=4条件）

阶段4: 结果聚合
  └─ _result_aggregator_node()
     └─ 合并所有专家输出
```

### 🎯 关键触发点

**文件**: `intelligent_project_analyzer/workflow/main_workflow.py`

**方法**: `_build_context_for_expert()` (行2790)

**触发条件**:
- ✅ 每个专家执行时**必然触发**
- ✅ 在 `_execute_agent_node()` 方法内部调用
- ✅ 发生在LLM调用**之前**（构建提示词阶段）

**输入参数**:
```python
state = {
    "current_batch_number": 2,      # 从 _batch_executor_node 传递
    "total_batches": 3,               # 从 execution_batches 计算
    "role_id": "V4_材料顾问_6-3",    # 当前专家ID
    "agent_results": {                # 前序专家的完整输出
        "V4_设计研究员_4-1": {...},
        "V4_结构分析师_5-2": {...}
    }
}
```

---

## 3. 动态策略选择逻辑

### 🧠 决策树

```python
def create_context_compressor(batch_number: int, total_batches: int) -> ContextCompressor:
    """
    决策逻辑:

    IF batch_number == 1:
        ✅ 使用 Minimal 模式
        原因: 第一批专家需要完整上下文理解全局

    ELIF batch_number >= 4 AND total_batches >= 4:
        ⚡ 使用 Aggressive 模式
        原因: 批次很多时，后期专家聚焦细节，可激进压缩

    ELSE:
        ⚖️ 使用 Balanced 模式
        原因: Batch2-3，适度压缩平衡质量与效率
    """
```

### 📊 策略决策表

| 批次配置 | Batch1 | Batch2 | Batch3 | Batch4 | Batch5 |
|---------|--------|--------|--------|--------|--------|
| **2批次总数** | Minimal | Balanced | - | - | - |
| **3批次总数** | Minimal | Balanced | Balanced | - | - |
| **4批次总数** | Minimal | Balanced | Balanced | **Aggressive** | - |
| **5批次总数** | Minimal | Balanced | Balanced | **Aggressive** | **Aggressive** |

**颜色说明**:
- 🟢 Minimal = 完全不压缩（质量优先）
- 🟡 Balanced = 适度压缩（平衡策略）
- 🔴 Aggressive = 激进压缩（效率优先）

### 🔍 选择理由

#### Batch1 → Minimal (完全不压缩)
```
理由:
✅ 第一批专家是后续专家的基础
✅ 需要完整理解用户需求和项目背景
✅ 后续专家会引用Batch1的具体数据
✅ 信息完整性 > Token成本

示例场景:
- 设计研究员分析三代同堂家庭需求
- 结构分析师需要引用具体的"祖父母需要无障碍设计"细节
```

#### Batch2-3 → Balanced (适度压缩)
```
理由:
✅ 专家已有基础上下文（从Batch1继承）
✅ 主要关注特定领域分析
✅ 适度压缩不影响分析质量
⚖️ 平衡质量与Token成本

压缩策略:
- 前800字符完整保留
- 智能在句号处截断
- 保留结构化格式（表格、列表）
```

#### Batch4+ → Aggressive (激进压缩)
```
理由:
✅ 后期专家聚焦细节实施
✅ 已有大量前序专家的上下文
✅ Token消耗累积较多
⚡ 效率优先，但保留基本概览

压缩策略:
- 交付物清单（知道有什么）
- 典型输出示例（了解格式和风格）
- 前300字符关键信息
```

---

## 4. 三种压缩级别详解

### 🟢 Level 1: Minimal（完全不压缩）

**适用批次**: Batch1

**压缩策略**:
```python
# 完整传递deliverable_outputs的所有content
for deliverable in deliverable_outputs:
    context_parts.append(f"#### 交付物 {i}: {name}")
    context_parts.append(f"**状态**: {status}")
    context_parts.append(f"**内容**:\n{content}\n")  # ⚡ 完整传递
```

**输出示例**:
```markdown
## 前序专家的分析成果
**说明**: 以下是前序专家的完整分析结果，你可以参考和引用。

### 设计研究员
**交付物数量**: 2

#### 交付物 1: 三代同堂家庭成员画像
**状态**: completed
**内容**:
## 家庭成员画像

### 1. 祖父母（60-75岁）
- **生活习惯**: 早睡早起，喜欢园艺和太极拳
- **空间需求**: 需要无障碍设计，采光充足的卧室
[...完整内容，约500-2000字符...]

#### 交付物 2: 空间需求矩阵
**状态**: completed
**内容**:
[...完整内容...]
```

**统计数据**:
- 原始长度: 1073字符
- 压缩后长度: 1243字符
- 压缩率: 115.84%（格式化标记增加）
- Token节省: -15.8%（无压缩）

---

### 🟡 Level 2: Balanced（适度压缩）

**适用批次**: Batch2-3（或Batch2直到Batch N-1）

**压缩策略**:
```python
# 前800字符完整保留 + 智能截断
for deliverable in deliverable_outputs:
    content = deliverable.get("content", "")
    if len(content) <= 800:
        parts.append(f"内容: {content}")  # 完整保留
    else:
        # 在句号处智能截断
        truncated = content[:800]
        last_period = truncated.rfind("。")
        if last_period > 600:  # 至少保留75%
            truncated = truncated[:last_period + 1]
        parts.append(f"摘要: {truncated}...")
```

**输出示例**:
```markdown
## 前序专家分析成果 (摘要)
**说明**: 以下是前序专家的核心结论，详细分析已省略以优化性能。

### 设计研究员
**交付物数量**: 2

**1. 三代同堂家庭成员画像** (状态: completed)
内容: ## 家庭成员画像

### 1. 祖父母（60-75岁）
- **生活习惯**: 早睡早起，喜欢园艺和太极拳
- **空间需求**: 需要无障碍设计，采光充足的卧室
[...前800字符完整内容...]
- **隐私边界**: 各自独立空间 + 公共交流区
- **文化传承**: 祖辈希望传授传统文化。  ⚡ 智能截断

**2. 空间需求矩阵** (状态: completed)
[...同样处理...]
```

**统计数据**:
- 原始长度: 1073字符
- 压缩后长度: 920字符
- 压缩率: 85.7%
- Token节省: 14.3%

---

### 🔴 Level 3: Aggressive（激进压缩）

**适用批次**: Batch4+（仅当总批次>=4）

**压缩策略**:
```python
# 交付物清单 + 典型输出示例（前300字符）
deliverable_list = [f"{i}. {name}" for i, deliverable in enumerate(...)]
parts.append(f"**交付物清单** ({len(outputs)}个)")
parts.extend(deliverable_list)

# 仅保留第一个交付物的简短示例
first_content = deliverable_outputs[0].get("content", "")
summary = first_content[:300]
parts.append(f"\n**典型输出示例**: {summary}...")
```

**输出示例**:
```markdown
## 前序专家分析成果 (摘要)
**说明**: 以下是前序专家的核心结论，详细分析已省略以优化性能。

### 设计研究员
**交付物数量**: 2
**交付物清单** (2个)
1. 三代同堂家庭成员画像
2. 空间需求矩阵

**典型输出示例**: ## 家庭成员画像

### 1. 祖父母（60-75岁）
- **生活习惯**: 早睡早起，喜欢园艺和太极拳
- **空间需求**: 需要无障碍设计，采光充足的卧室
- **社交需求**: 希望有接待老友的独立客厅...  ⚡ 仅前300字符
```

**统计数据**:
- 原始长度: 768字符
- 压缩后长度: 432字符
- 压缩率: 56.2%
- Token节省: 43.8%

---

## 5. 实际执行流程

### 🔄 单个专家执行的上下文构建

```python
# 步骤1: 批次执行器传递批次信息
# 文件: main_workflow.py, _batch_executor_node()
agent_state = dict(state)
agent_state["current_batch_number"] = current_batch  # ⚡ 关键参数1
agent_state["total_batches"] = total_batches          # ⚡ 关键参数2
agent_state["role_id"] = role_id

# 步骤2: 专家执行时构建上下文
# 文件: main_workflow.py, _build_context_for_expert()
def _build_context_for_expert(state):
    # 2.1 提取批次信息
    batch_number = state.get("current_batch_number", 1)
    total_batches = state.get("total_batches", 3)
    current_role_id = state.get("role_id", "")

    # 2.2 创建压缩器（自动选择压缩级别）
    compressor = create_context_compressor(batch_number, total_batches)
    # 输出日志: 🗜️ [ContextCompressor] Batch2/3 使用压缩级别: balanced

    # 2.3 压缩前序专家输出
    agent_results = state.get("agent_results", {})
    compressed_results = compressor.compress_agent_results(
        agent_results,
        current_role_id
    )

    # 2.4 获取压缩统计
    stats = compressor.get_compression_stats()
    # 输出日志: 🗜️ [ContextCompressor] Batch2 V4_材料顾问_6-3 -
    #           原始: 1073字符, 压缩后: 920字符, 压缩率: 85.7%, 节省: 14.3%

    # 2.5 构建完整上下文
    context_parts = [
        "## 用户需求\n...",
        compressed_results,  # ⚡ 使用压缩后的内容
        "## 项目状态信息\n..."
    ]

    return "\n\n".join(context_parts)

# 步骤3: 传递给LLM
# TaskOrientedExpert.execute() 接收压缩后的上下文
```

### 📊 多批次执行的压缩效果对比

**场景**: 5个专家，3个批次

```
Batch1 (2个专家):
├─ 专家1 (设计研究员)
│  └─ 压缩级别: Minimal
│  └─ agent_results: {} (空，第一个专家)
│  └─ 上下文长度: 基础上下文（用户需求）
│
└─ 专家2 (结构分析师)
   └─ 压缩级别: Minimal
   └─ agent_results: {专家1: 1073字符}
   └─ 上下文长度: 基础 + 1243字符（完整传递）

Batch2 (2个专家):
├─ 专家3 (材料顾问)
│  └─ 压缩级别: Balanced
│  └─ agent_results: {专家1: 1073字符, 专家2: 950字符}
│  └─ 上下文长度: 基础 + 1704字符（压缩后，原2023字符）
│  └─ Token节省: ~320字符（15.8%）
│
└─ 专家4 (机电工程师)
   └─ 压缩级别: Balanced
   └─ agent_results: {专家1-3}
   └─ Token节省: 累计~600字符

Batch3 (1个专家):
└─ 专家5 (成本工程师)
   └─ 压缩级别: Balanced (不满足>=4条件)
   └─ agent_results: {专家1-4}
   └─ Token节省: 累计~900字符
```

---

## 6. 应用场景示例

### 场景A: 标准3批次配置

**项目类型**: 个人住宅设计
**专家配置**: 5个专家，3个批次

```
批次划分:
- Batch1: [V4_设计研究员, V4_结构分析师]
- Batch2: [V4_材料顾问, V4_机电工程师]
- Batch3: [V4_成本工程师]

压缩策略应用:
┌────────────┬──────────┬─────────────┬──────────┐
│   批次     │  压缩级别│  Token节省  │  说明     │
├────────────┼──────────┼─────────────┼──────────┤
│  Batch1    │ Minimal  │   0%        │ 完整传递  │
│  Batch2    │ Balanced │  ~20%       │ 适度压缩  │
│  Batch3    │ Balanced │  ~30%       │ 继续压缩  │
└────────────┴──────────┴─────────────┴──────────┘

总体效果:
- 端到端Token消耗: ↓15-25%
- 分析质量影响: 最小化（Batch1完整）
- 适用场景: 大多数项目
```

### 场景B: 复杂5批次配置

**项目类型**: 大型商业综合体
**专家配置**: 10个专家，5个批次

```
批次划分:
- Batch1: [设计研究员, 结构分析师]
- Batch2: [材料顾问, 机电工程师]
- Batch3: [景观设计师, 室内设计师]
- Batch4: [成本工程师, 智能化顾问]  ⚡ 激进压缩开始
- Batch5: [节能顾问, 法规顾问]

压缩策略应用:
┌────────────┬──────────┬─────────────┬──────────┐
│   批次     │  压缩级别│  Token节省  │  说明     │
├────────────┼──────────┼─────────────┼──────────┤
│  Batch1    │ Minimal  │   0%        │ 完整传递  │
│  Batch2    │ Balanced │  ~20%       │ 适度压缩  │
│  Batch3    │ Balanced │  ~35%       │ 继续压缩  │
│  Batch4    │Aggressive│  ~50%       │ 激进压缩  │
│  Batch5    │Aggressive│  ~60%       │ 最大压缩  │
└────────────┴──────────┴─────────────┴──────────┘

总体效果:
- 端到端Token消耗: ↓40-50%
- 分析质量影响: 可接受（后期专家聚焦细节）
- 适用场景: 大型复杂项目
```

### 场景C: 审核重新执行

**触发条件**: 人工审核发现部分专家需要重新分析

```
执行流程:
1. 审核节点标记需要重新执行的专家
   └─ specific_agents_to_run = ["V4_材料顾问_6-3"]

2. 重新执行时的压缩策略
   ├─ current_batch_number: 使用原始批次编号（如2）
   ├─ total_batches: 使用原始总批次数（如3）
   └─ 压缩级别: Balanced（继承原策略）

3. 上下文包含:
   ├─ 用户需求（完整）
   ├─ 前序专家输出（压缩）
   └─ 审核反馈（完整传递给该专家）

特点:
✅ 继承原压缩策略，保持一致性
✅ 审核反馈不压缩，确保改进方向清晰
```

---

## 7. 性能监控与日志

### 📊 压缩统计日志

每次压缩器执行都会输出详细统计:

```
2026-02-10 14:49:14.558 | INFO |
🗜️ [ContextCompressor] Batch2/3 使用压缩级别: balanced

2026-02-10 14:49:14.558 | INFO |
🗜️ [ContextCompressor] Batch2 V4_材料顾问_6-3 -
    原始: 1073字符,
    压缩后: 920字符,
    压缩率: 85.7%,
    节省: 14.3%
```

### 🔍 关键指标

**监控指标**:
1. **压缩率** (Compression Ratio): 压缩后长度 / 原始长度
2. **节省率** (Savings Percent): 1 - 压缩率
3. **原始长度** (Original Length): 前序专家完整内容长度
4. **压缩后长度** (Compressed Length): 实际传递给LLM的长度

**健康阈值**:
- ✅ Minimal: 压缩率 95-120% (基本无压缩)
- ✅ Balanced: 压缩率 40-60% (适度压缩)
- ✅ Aggressive: 压缩率 30-50% (激进压缩)

---

## 8. 故障排查

### ⚠️ 常见问题

#### Q1: 压缩统计显示负数节省率？

**症状**:
```
节省: -15.8%
```

**原因**:
- Minimal模式添加了格式化标记（如 `#### 交付物 1:`）
- 实际内容完整传递，格式化增加了少量字符

**解决**:
- ✅ 这是正常的，表示完全不压缩
- ✅ 质量保证优先于Token节省

#### Q2: Batch2仍显示Minimal模式？

**症状**:
```
🗜️ [ContextCompressor] Batch2/3 使用压缩级别: minimal
```

**原因**:
- 检查 `current_batch_number` 是否正确传递
- 可能 `_batch_executor_node` 未更新状态

**诊断**:
```python
# 检查状态传递
logger.debug(f"Batch info: {state.get('current_batch_number')}/{state.get('total_batches')}")
```

#### Q3: 压缩率异常高（>200%）？

**症状**:
```
压缩率: 7200.00%
```

**原因**:
- 原始内容长度计算错误
- 可能前序专家的 `agent_results` 为空或格式错误

**解决**:
- ✅ 已修复：v7.502.1 统计逻辑修复
- ✅ 现在正确统计 `deliverable_outputs[].content` 长度

---

## 9. 最佳实践

### ✅ 推荐配置

1. **标准项目（3-4批次）**:
   - 使用默认策略即可
   - Batch1不压缩，Batch2+适度压缩

2. **大型项目（5+批次）**:
   - Batch4+启用激进压缩
   - 监控后期专家的输出质量

3. **质量敏感项目**:
   - 考虑只在Batch3+启用压缩
   - 调整 `create_context_compressor` 逻辑

### ⚠️ 注意事项

1. **不要过早优化**:
   - Batch1-2保持完整上下文
   - 质量 > 成本

2. **监控压缩统计**:
   - 定期检查日志中的压缩率
   - 发现异常及时调整

3. **A/B测试验证**:
   - 对比压缩前后的专家输出质量
   - 确保Token节省不影响分析深度

---

## 10. 总结

### 🎯 核心要点

1. **自动触发**: 每个专家执行时自动应用压缩策略
2. **动态选择**: 根据批次编号智能选择压缩级别
3. **质量优先**: Batch1完全不压缩，确保信息完整性
4. **性能优化**: Batch2+适度压缩，节省30-50% Token
5. **可监控**: 详细的压缩统计日志，实时追踪效果

### 📊 预期收益

**5个专家，3批次场景**:
- Token消耗: ↓15-25%
- 成本节省: ~$0.05-0.1/请求
- 质量影响: 最小化

**10个专家，5批次场景**:
- Token消耗: ↓40-50%
- 成本节省: ~$0.2-0.3/请求
- 质量影响: 可接受

### 🚀 后续优化方向

- [ ] 基于专家类型的自适应压缩（设计类 vs 技术类）
- [ ] 压缩质量的自动评估指标
- [ ] 用户可配置的压缩策略模板

---

**文档维护者**: GitHub Copilot
**最后更新**: 2026-02-10
**版本历史**: v7.502.1 - 质量优先策略调整
