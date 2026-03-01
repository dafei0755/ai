# ADR-002：asyncio.gather 真并行（含遗留的并发失控问题）

**状态**：已决策（v7.502）；遗留并发上限问题需后续修复
**决策日期**：v7.502 P0 性能修复
**记录日期**：2026-02-28（v8.0.0 治理审计时补录）

---

## 背景

系统的多专家并行处理最初通过 LangGraph 的 Send API 实现。然而在性能压测中发现：**LangGraph Send API 并不真正并行**——它在运行时实际上是顺序调度多个节点，并不产生真正的 asyncio 并发。

在 v7.502 的 P0 性能修复中，测量数据如下：

| 方案 | Batch1 执行时间 |
|------|----------------|
| LangGraph Send API（原方案） | ~10s |
| `asyncio.gather` 真并行（新方案） | ~3.3s |

性能提升 **67%**，已在生产环境验证。

---

## 决策

在 `_execute_agents_batch_node` 节点内部（`main_workflow.py` L1792 附近），绕过 LangGraph Send API，直接使用 `asyncio.gather` 并行执行所有专家 Agent 的 `asyncio.create_task`：

```python
# 决策后的实现（约 main_workflow.py L1792）
results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
```

同时，`asyncio.gather(return_exceptions=True)` 的语义是：任意 task 异常不终止其他 task，失败的 task 返回异常对象而非抛出。失败专家被打上 `confidence: 0.0` 标记后静默继续。

---

## 引入的新问题（P0 待修复）

**并发上限缺失**：当前实现没有任何 `asyncio.Semaphore` 限制。

- 批次规模：10-15 个专家
- tenacity 重试配置：最多 3 次
- 峰值并发 HTTP 连接：**45+**

在高负载（多用户并发会话）下，这会导致：
1. LLM 提供商触发限流（HTTP 429）
2. 连接池耗尽
3. 整体会话超时

**已下达的修复任务**：ACTION_PLAN.md QW-2（添加 `LLMConcurrencyManager` + `asyncio.Semaphore`）。

---

## 后果

**积极后果**：
- Batch1 执行时间从 10s 降至 3.3s，用户等待时间显著减少
- 代码简单，不依赖 LangGraph 内部调度机制

**消极后果（待修复）**：
- 无并发上限，高负载下系统稳定性下降
- `return_exceptions=True` 吞掉异常，失败的专家静默降级为 `confidence: 0.0`，问题难以察觉

---

## 教训

**教训 1**：框架提供的"并行" API 不等于底层真并行。在性能敏感场景，必须实测，不能假设框架行为。

**教训 2**：性能优化和稳定性是对立统一的。引入真并行提升了速度，但也引入了并发失控的风险。每次性能优化后，需要同步评估新的稳定性风险并制定预案。

**教训 3**：`return_exceptions=True` 提高了韧性，但也掩盖了问题。正确做法是：允许部分失败（return_exceptions=True）+ 在聚合节点检测 errors 字段 + 通过节点守卫（ADR 未命名，见 ST-3）上报失败事件。

---

## 相关文件

- `intelligent_project_analyzer/workflow/main_workflow.py` L1787-1800（决策实现位置）
- [ACTION_PLAN.md](../ACTION_PLAN.md)（QW-2：添加并发 Semaphore；ST-3：节点 Fallback 守卫）
