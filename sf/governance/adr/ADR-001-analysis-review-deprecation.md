# ADR-001：废弃 analysis_review 节点

**状态**：已决策（决策版本 v2.2），遗留清理工作未完成
**决策日期**：系统中期迭代（具体版本存档于 CHANGELOG.md）
**记录日期**：2026-02-28（v8.0.0 治理审计时补录）

---

## 背景

系统早期采用"后置四阶段质量审核"模式：专家完成分析后，再经由 `analysis_review` 节点进行四阶段质量检查。这导致专家大量计算资源已被消耗，质量问题才被发现，造成严重浪费。

v2.2 决策将质量审核前置（详见 ADR-003），`analysis_review` 节点的职责因此被替代，理论上应当同步废弃。

---

## 决策

废弃 `analysis_review` 节点，不再注册到 LangGraph 工作流图中。质量审核职责由前置的 `role_task_unified_review` 节点承担。

具体操作（当时执行的）：
- 注释掉 `workflow.add_node("analysis_review", self._analysis_review_node)` — `main_workflow.py` L229

---

## 遗留问题（未完成的清理工作）

**在 v8.0.0 代码审计中发现以下遗留项未清理**：

| 遗留项 | 位置 | 问题严重性 |
|--------|------|------------|
| 路由函数返回 `"analysis_review"` | `main_workflow.py` L2242 | **P0** — 路由到未注册节点，触发 LangGraph 崩溃 |
| `_route_after_analysis_review` 孤立函数 | `main_workflow.py` L2691 | P1 — 永远不会被调用的死代码 |
| 相关状态字段标记不一致 | `core/state.py` 多处 | P1 — 部分 DEPRECATED 标记不完整 |

**已下达的修复任务**：ACTION_PLAN.md QW-1（删除死代码路由）和 QW-3（删除孤立函数）。

---

## 后果

**积极后果**：
- 质量审核前置化（见 ADR-003），工作流效率显著提升

**消极后果（至今未处理）**：
- `requires_client_review == True` 场景下，工作流会路由到不存在的节点，导致 LangGraph `NodeNotFoundError` 崩溃
- 遗留代码在代码库中存活了多个 MINOR 版本，说明废弃流程存在系统性缺陷

---

## 教训与改进

### 教训
"先废弃，稍后清理路由"的操作方式直接导致了 P0 问题。废弃一个节点是一个原子性操作，必须一次性完成，不能分步拆开。

### 改进措施
建立"节点废弃 5 步清单"（见 [DEV_WORKFLOW.md](../DEV_WORKFLOW.md#节点废弃-5-步清单)），每次废弃节点时强制执行全部 5 步。

---

## 相关文件

- `intelligent_project_analyzer/workflow/main_workflow.py` L229（注释掉的 add_node），L2237-2243（P0 死代码路由），L2691（孤立函数）
- `intelligent_project_analyzer/core/state.py` L317-320（DEPRECATED 字段）
- [ADR-003](ADR-003-quality-control-frontloading.md)（质量控制前置化决策）
- [ACTION_PLAN.md](../ACTION_PLAN.md)（QW-1、QW-3 修复任务）
