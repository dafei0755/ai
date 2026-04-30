# 专题复盘项目动机

> **导航提示：** 建议先读 [README](README.md) 与 [01-需求分析主流程与武器协作-2026-03-11.md]；本文更适合作为“需求分析阶段如何被重新组织成 6 大节点表达”的补充说明。

## 目标

在不改动代码与主链拓扑的前提下，**降低系统理解与协作成本**。

把「可运行」升级为「可解释、可协作、可复用」。

---

## 核心矛盾与方向

| 矛盾 | 方向 |
|---|---|
| 系统复杂度 vs 对外可理解性 | 用 6 大节点重组认知层表达 |
| 运行层精确性 vs 文档传播性 | 概念层与运行层显式分层 |
| 长期演进 vs 冻结约束稳定性 | 不变量守住，演进方向分批排期 |

---

## 非目标

- 不新增/删除运行时节点
- 不改主链拓扑与路由实现
- 不修复追问不可达等后半程问题

---

## 成功判据

1. 6 大节点职责一眼可读
2. 概念层到运行层可无损映射
3. 冻结不变量全部保留
4. 评审聚焦问题本身，不在术语定义上兜圈

---

## 关键代码锚点

| 内容 | 代码位置 |
|---|---|
| 主链与冻结约束 | workflow/workflow_contract.py、workflow/main_workflow.py |
| M18/M19 字段定义 | `agents/requirements_analyst_schema.py` |
| 动机写入与路由 | workflow/nodes/requirements_nodes.py |
| 门禁与快路径 | workflow/nodes/security_nodes.py |
| 回归测试 | `tests/unit/test_requirements_method_contracts.py` |
