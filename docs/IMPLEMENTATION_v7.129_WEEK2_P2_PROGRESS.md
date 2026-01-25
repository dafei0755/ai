# Week 2 P2 实施进度报告 - LLM重试机制

## ✅ 当前进度：任务1完成

**完成时间**: 2026-01-04
**状态**: 🟢 LLM重试机制已实现

---

## 🎯 已完成：任务1 - LLM重试机制

### 实现概述

创建了 `execute_expert_with_retry` 函数，为V4/V6角色提供智能重试机制，确保搜索工具被正确调用。

### 技术实现

**文件**: `intelligent_project_analyzer/agents/task_oriented_expert_factory.py`
**位置**: Lines 573-701（新增129行代码）

#### 核心功能

```python
async def execute_expert_with_retry(
    self,
    role_object: Dict[str, Any],
    context: str,
    state: ProjectAnalysisState,
    tools: Optional[List[Any]] = None,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    🆕 v7.129 Week2 P2: 带重试机制的专家执行包装函数

    如果V4/V6角色未使用工具，将增强prompt并重试
    """
```

#### 重试策略

**1. 角色检测**
- ✅ V4 (设计研究员) - 需要搜索工具
- ✅ V6 (总工程师) - 需要搜索工具
- ⏭️ V2/V3/V5 - 不强制检查

**2. 渐进式Prompt增强**

| 尝试次数 | 策略 | Prompt增强内容 |
|---------|------|---------------|
| 第1次 | 正常执行 | 无增强（使用原始prompt） |
| 第2次 | 温和提醒 | ⚠️ IMPORTANT: 请务必使用搜索工具，至少调用3个不同的工具 |
| 第3次 | 强烈要求 | 🔴 CRITICAL: 你必须调用至少5次搜索工具，每个deliverable都需要外部搜索支持 |

**3. 工具使用检查**

```python
# 检查 structured_output.protocol_execution.tools_used
structured_output = result.get("structured_output", {})
protocol_exec = structured_output.get("protocol_execution", {})
tools_used = protocol_exec.get("tools_used", [])

if len(tools_used) == 0:
    # 未使用工具 → 触发重试
    logger.warning(f"⚠️ {role_id} 第{attempt}次尝试未使用任何工具")
    continue  # 进入下一次重试
else:
    # 成功使用工具 → 退出循环
    logger.info(f"✅ {role_id} 成功使用了工具: {tools_used}")
    break
```

**4. 失败处理**

如果3次尝试后仍未使用工具：
- ✅ 添加警告标记到结果
- ✅ 降低confidence至0.6
- ✅ 记录详细日志供后续分析

```python
result["warnings"].append({
    "type": "missing_tool_usage",
    "message": f"角色{role_id}应使用搜索工具但未执行，已尝试{max_retries}次",
    "impact": "结果可能缺乏外部验证和最新信息"
})
result["confidence"] = min(0.6, result.get("confidence", 1.0))
```

### 日志示例

#### 成功场景（第1次就使用工具）
```log
2026-01-04 10:30:15.123 | INFO | [8pdwoxj8-a3f2c1b4] | 🔄 [v7.129 Retry] V4-1 开始执行（最多3次重试）
2026-01-04 10:30:15.124 | INFO | [8pdwoxj8-a3f2c1b4] |    需要搜索工具: 是
2026-01-04 10:30:15.125 | INFO | [8pdwoxj8-a3f2c1b4] | 📍 [v7.129 Retry] V4-1 第 1/3 次尝试
2026-01-04 10:30:35.678 | INFO | [8pdwoxj8-a3f2c1b4] | ✅ [v7.129 Retry] V4-1 第1次尝试成功使用了工具: ['tavily_search', 'arxiv_search']
2026-01-04 10:30:35.679 | INFO | [8pdwoxj8-a3f2c1b4] | 🏁 [v7.129 Retry] V4-1 执行完成（共1次尝试）
```

#### 重试场景（第2次成功）
```log
2026-01-04 10:30:15.123 | INFO | [8pdwoxj8-a3f2c1b4] | 🔄 [v7.129 Retry] V6-1 开始执行（最多3次重试）
2026-01-04 10:30:15.124 | INFO | [8pdwoxj8-a3f2c1b4] |    需要搜索工具: 是
2026-01-04 10:30:15.125 | INFO | [8pdwoxj8-a3f2c1b4] | 📍 [v7.129 Retry] V6-1 第 1/3 次尝试
2026-01-04 10:30:35.678 | WARN | [8pdwoxj8-a3f2c1b4] | ⚠️ [v7.129 Retry] V6-1 第1次尝试未使用任何工具
2026-01-04 10:30:35.679 | INFO | [8pdwoxj8-a3f2c1b4] | 🔄 [v7.129 Retry] V6-1 准备重试...
2026-01-04 10:30:35.680 | INFO | [8pdwoxj8-a3f2c1b4] | 📍 [v7.129 Retry] V6-1 第 2/3 次尝试
2026-01-04 10:30:35.681 | INFO | [8pdwoxj8-a3f2c1b4] | 🔧 [v7.129 Retry] V6-1 增强prompt（第2次尝试）
2026-01-04 10:30:55.234 | INFO | [8pdwoxj8-a3f2c1b4] | ✅ [v7.129 Retry] V6-1 第2次尝试成功使用了工具: ['bocha_search', 'tavily_search', 'arxiv_search']
2026-01-04 10:30:55.235 | INFO | [8pdwoxj8-a3f2c1b4] | 🏁 [v7.129 Retry] V6-1 执行完成（共2次尝试）
```

#### 失败场景（3次都未使用）
```log
2026-01-04 10:30:15.123 | INFO | [8pdwoxj8-a3f2c1b4] | 🔄 [v7.129 Retry] V4-1 开始执行（最多3次重试）
2026-01-04 10:30:15.124 | INFO | [8pdwoxj8-a3f2c1b4] |    需要搜索工具: 是
2026-01-04 10:30:15.125 | INFO | [8pdwoxj8-a3f2c1b4] | 📍 [v7.129 Retry] V4-1 第 1/3 次尝试
2026-01-04 10:30:35.678 | WARN | [8pdwoxj8-a3f2c1b4] | ⚠️ [v7.129 Retry] V4-1 第1次尝试未使用任何工具
2026-01-04 10:30:35.679 | INFO | [8pdwoxj8-a3f2c1b4] | 📍 [v7.129 Retry] V4-1 第 2/3 次尝试
2026-01-04 10:30:35.680 | INFO | [8pdwoxj8-a3f2c1b4] | 🔧 [v7.129 Retry] V4-1 增强prompt（第2次尝试）
2026-01-04 10:30:55.234 | WARN | [8pdwoxj8-a3f2c1b4] | ⚠️ [v7.129 Retry] V4-1 第2次尝试未使用任何工具
2026-01-04 10:30:55.235 | INFO | [8pdwoxj8-a3f2c1b4] | 📍 [v7.129 Retry] V4-1 第 3/3 次尝试
2026-01-04 10:30:55.236 | INFO | [8pdwoxj8-a3f2c1b4] | 🔧 [v7.129 Retry] V4-1 增强prompt（第3次尝试）
2026-01-04 10:31:15.789 | WARN | [8pdwoxj8-a3f2c1b4] | ⚠️ [v7.129 Retry] V4-1 第3次尝试未使用任何工具
2026-01-04 10:31:15.790 | ERROR | [8pdwoxj8-a3f2c1b4] | ❌ [v7.129 Retry] V4-1 已达最大重试次数，但仍未使用工具
2026-01-04 10:31:15.791 | INFO | [8pdwoxj8-a3f2c1b4] | 🏁 [v7.129 Retry] V4-1 执行完成（共3次尝试）
```

### 集成点（待完成）

**当前状态**: 函数已实现，但尚未集成到workflow

**下一步集成位置**:
- `intelligent_project_analyzer/workflow/main_workflow.py`
- 在调用 `factory.execute_expert()` 的地方替换为 `factory.execute_expert_with_retry()`

**预计影响**:
- ✅ V4/V6角色的工具使用率将提升至 >80%
- ✅ 搜索引用数量将增加至平均30-50条/会话
- ⚠️ 每个专家执行时间可能增加（如需重试）
  - 第1次成功: 无影响
  - 第2次成功: +20-30秒
  - 第3次成功: +40-60秒

---

## 🔄 进行中：任务2 - 搜索降级策略

### 设计方案

如果LLM连续3次重试都未使用工具，自动触发后备搜索机制：

```python
# 伪代码
if len(tools_used) == 0 and attempt == max_retries:
    logger.warning("触发搜索降级策略")
    # 自动执行Tavily搜索
    fallback_results = await execute_fallback_search(
        role_object, context, state
    )
    # 将结果注入到structured_output
    result["structured_output"]["fallback_search_results"] = fallback_results
```

### 实现计划

1. ✅ 在`execute_expert_with_retry`中检测工具未使用场景
2. ⏳ 实现 `execute_fallback_search` 函数
3. ⏳ 调用ToolFactory创建Tavily工具
4. ⏳ 执行搜索并提取结果
5. ⏳ 将结果添加到search_references

---

## ⏸️ 待开始：任务3 - 工具使用告警集成

### 计划

集成已实现的 `ToolUsageAlert` 系统到workflow中：

```python
# 在 agent_executor_node 完成后
from ..monitoring.tool_alert import ToolUsageAlert

await ToolUsageAlert.check_and_alert(
    session_id=state["session_id"],
    role_id=role_id,
    tools_used=tools_used
)
```

---

## 📊 整体进度

| 任务 | 状态 | 完成度 |
|------|------|--------|
| 1. LLM重试机制 | ✅ 完成 | 100% |
| 2. 搜索降级策略 | 🔄 进行中 | 30% |
| 3. 工具告警集成 | ⏸️ 待开始 | 0% |

**Week 2 P2总进度**: 43% (1/3 + 0.3/3)

---

**最后更新**: 2026-01-04
**下一步**: 实现execute_fallback_search函数
