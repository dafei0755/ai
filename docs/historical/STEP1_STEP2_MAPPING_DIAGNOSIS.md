# Step 1 与 Step 2 数据对应关系诊断

## 问题描述

用户反馈："步骤1的搜索框架应该和步骤2的任务清单对应才对，一个搜索框架，对应一个搜索任务清单页面"

## 当前架构

### Step 1：深度分析（输出框架）

**数据结构**：`output_framework`
```json
{
  "core_objective": "核心目标",
  "deliverable_type": "最终交付物类型",
  "blocks": [
    {
      "name": "板块1：XXX",
      "sub_items": [
        "子项1.1：XXX",
        "子项1.2：XXX"
      ],
      "estimated_length": "预估长度",
      "priority": "优先级"
    },
    {
      "name": "板块2：YYY",
      "sub_items": [...]
    }
  ],
  "quality_standards": ["标准1", "标准2"],
  "search_hints": "搜索方向提示"
}
```

### Step 2：任务分解（搜索任务清单）

**数据结构**：`search_queries`（映射自 `output_framework.blocks`）
```json
[
  {
    "id": "S1",
    "query": "基于板块1生成的搜索查询",
    "task_description": "搜索任务描述",
    "expected_output": "期望输出",
    "priority": "medium",
    "can_parallel": true
  },
  {
    "id": "S2",
    "query": "基于板块2生成的搜索查询",
    ...
  }
]
```

## 对应关系流程

```
用户输入
  ↓
Step 1：深度分析 (execute_step1_only_v3)
  ↓
生成 output_framework
  - core_objective（核心目标）
  - blocks（板块列表）
    - block.name（板块名称）
    - block.sub_items（子项列表）
  ↓
Step 2：任务分解 (step2_executor.execute)
  ↓
转换 output_framework → Step2OutputFramework
  (_convert_to_step2_output_framework)
  ↓
生成 search_queries
  - 每个 block → 1-N 个 search_query
  - 根据 block.name 和 sub_items 生成具体搜索任务
  ↓
前端显示
  - fourMissionsResult（Step 1 展示）
  - step2Plan.search_steps（Step 2 任务清单）
```

## 验证点

### 1. Step 1 输出验证
**文件**：`ucppt_search_engine.py` line ~7690
```python
yield {"event": "step1_complete",
       "message": "深度分析完成",
       "output_framework": output_framework}
```

**检查**：
- ✅ `output_framework` 是否包含完整的 blocks？
- ✅ 每个 block 是否有清晰的 name 和 sub_items？

### 2. Step 2 转换验证
**文件**：`ucppt_search_engine.py` line ~4750-4850
```python
def _convert_to_step2_output_framework(
    self,
    output_framework_dict: Dict[str, Any],
) -> Optional["Step2OutputFramework"]:
```

**检查**：
- ✅ blocks 数据是否正确提取？
- ✅ sub_items 是否完整转换？
- ⚠️ **可能的问题**：某些 block 数据格式不符合预期导致转换失败

### 3. Step 2 生成验证
**文件**：`ucppt_search_engine.py` line ~4495-4530
```python
async for step2_event in self.step2_executor.execute(
    user_input=query,
    output_framework=step2_framework,
    stream=True,
):
```

**检查**：
- ✅ step2_executor 是否成功执行？
- ✅ search_queries 数量是否与 blocks 对应？
- ⚠️ **可能的问题**：
  - Step2Executor 未初始化（STEP2_EXECUTOR_AVAILABLE=False）
  - 转换后的 step2_framework 格式不正确
  - LLM 生成任务失败

### 4. 前端展示验证
**文件**：`frontend-nextjs/app/search/[session_id]/page.tsx` line ~3082-3130
```tsx
case 'task_decomposition_complete':
  const searchSteps = searchQueries.map((item, idx) => ({
    id: item.id || `S${idx + 1}`,
    task_description: item.query || item.task_description || '',
    expected_outcome: item.expected_output || item.expected_outcome || '',
    ...
  }));
  setStep2Plan(plan);
```

**检查**：
- ✅ task_decomposition_complete 事件是否收到？
- ✅ searchSteps 数量是否正确？
- ⚠️ **可能的问题**：
  - 事件未触发（后端 Step 2 失败）
  - searchQueries 数据结构不匹配

## 诊断步骤

### 1. 检查 Step 2 是否正常执行

在后端日志中搜索：
```bash
Get-Content logs\server.log | Select-String "Step 2"
```

预期日志：
```
🔍 [v7.333] 开始执行 Step 2 搜索任务分解...
✅ [v7.333] Step 2 完成，生成 X 个搜索查询
```

如果看到警告：
```
⚠️ [v7.333] 无法转换 output_framework 格式，跳过 Step 2
⚠️ [v7.333] Step 2 搜索任务分解失败，使用简化模式
```
→ 说明 **Step 2 未执行**或**转换失败**

### 2. 检查前端是否收到事件

在浏览器控制台搜索：
```javascript
task_decomposition_complete
```

预期日志：
```
✅ [v7.333] Step 2 任务分解完成: {search_queries: [...]}
📋 [v7.333] 生成 X 个搜索查询
```

如果没有日志：
→ 说明 **后端未发送事件**或**事件类型不匹配**

### 3. 对比 blocks 和 search_queries 数量

**Step 1 输出**（后端日志）：
```
output_framework.blocks: 5 个板块
```

**Step 2 输出**（前端控制台）：
```
step2Plan.search_steps: 12 个任务
```

**预期关系**：
- 1 个 block → 1-3 个 search_query（根据复杂度）
- 如果 blocks 很多但 search_queries 很少 → 转换不完整
- 如果 blocks 很少但 search_queries 很多 → 可能 LLM 额外生成了任务

## 潜在问题及解决方案

### 问题 1：Step 2 Executor 未初始化
**症状**：日志显示 "Step2 类型未可用"

**原因**：
```python
if not STEP2_EXECUTOR_AVAILABLE or not Step2OutputFramework:
    logger.warning("⚠️ [v7.333] Step2 类型未可用")
    return None
```

**解决方案**：
检查 `services/four_step_flow/step2_task_decomposition_executor.py` 是否正确导入

### 问题 2：output_framework 格式不符合预期
**症状**：日志显示 "无法转换 output_framework 格式"

**原因**：
- `core_objective` 或 `blocks` 字段缺失
- blocks 数据结构不正确（不是 list 或 dict）

**解决方案**：
在 `_convert_to_step2_output_framework` 添加详细日志：
```python
logger.info(f"📋 [DEBUG] output_framework keys: {output_framework_dict.keys()}")
logger.info(f"📋 [DEBUG] blocks count: {len(blocks_data)}")
```

### 问题 3：fourMissionsResult 与 output_framework 不同步
**症状**：Step 1 显示 fourMissionsResult，但 Step 2 基于 output_framework

**原因**：
- 旧版流程使用 `fourMissionsResult`
- 新版流程使用 `output_framework`
- 两者数据结构不一致

**解决方案**：
统一数据源，确保前端展示的 Step 1 结果与 Step 2 的输入源一致：
```tsx
// 选项 1：统一使用 output_framework
{step1OutputFramework && <Step1OutputFramework framework={step1OutputFramework} />}

// 选项 2：从 fourMissionsResult 提取 blocks 用于 Step 2
const blocks = extractBlocksFromFourMissions(fourMissionsResult);
```

## 建议的修复步骤

### 短期修复（立即可用）
1. **添加详细日志**：在关键转换点添加日志，确认数据流
2. **前端显示对应**：在 UI 上明确标注"基于 X 个板块生成 Y 个搜索任务"
3. **错误处理**：当 Step 2 失败时，提供降级方案（手动添加任务）

### 中期优化（1-2天）
1. **统一数据结构**：确保 Step 1 和 Step 2 使用相同的框架定义
2. **验证机制**：在 Step 1 完成后验证 output_framework 完整性
3. **可视化对应**：在 UI 上展示 block → task 的映射关系

### 长期改进（1周+）
1. **端到端测试**：添加自动化测试验证 Step 1 → Step 2 数据流
2. **配置化映射**：允许配置 1个block生成多少个task
3. **用户反馈**：允许用户调整 block 和 task 的对应关系

## 调试命令

```powershell
# 1. 查看 Step 1 输出
Get-Content logs\server.log | Select-String "output_framework" -Context 2

# 2. 查看 Step 2 执行
Get-Content logs\server.log | Select-String "Step 2|step2" -Context 2

# 3. 查看转换过程
Get-Content logs\server.log | Select-String "convert.*output_framework" -Context 2

# 4. 查看搜索查询生成
Get-Content logs\server.log | Select-String "search_queries|搜索查询" -Context 2
```

## 结论

**核心对应关系**：
```
Step 1: output_framework.blocks (板块列表)
   ↓ (转换)
Step 2: search_queries (搜索任务清单)
```

**关键验证点**：
1. ✅ Step 1 生成完整的 blocks
2. ✅ Step 2 正确转换 blocks
3. ✅ Step 2 LLM 生成合理的任务
4. ✅ 前端正确显示对应关系

**下一步行动**：
1. 运行诊断命令确认问题根源
2. 根据日志输出定位具体失败点
3. 应用对应的解决方案
