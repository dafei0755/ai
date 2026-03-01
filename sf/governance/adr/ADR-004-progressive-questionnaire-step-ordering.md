# ADR-004：问卷步骤实际执行顺序 Step1 → Step3 → Step2

**状态**：已决策，生效中，命名模糊问题待解决
**决策日期**：v7.80
**记录日期**：2026-02-28（v8.0.0 治理审计时补录）

---

## 背景

问卷追问系统引入了三个步骤节点：
- `progressive_step1_node`（Step1）：基础信息收集
- `progressive_step2_node`（Step2）：雷达图维度评估
- `progressive_step3_node`（Step3）：深度需求挖掘

从命名来看，直觉上的执行顺序应该是 **Step1 → Step2 → Step3**。

---

## 问题

Step2（雷达图维度评估）在设计上依赖两个前置输入：
1. Step1 的"基础信息"（用户提供的初始需求）
2. Step3 的"深度需求挖掘"结果（进一步明确的需求语境）

如果按命名顺序 Step1 → Step2 → Step3 执行，Step2 做雷达图评估时缺少 Step3 的深度挖掘输出，会导致雷达图维度评分不准确，质量明显下降。

---

## 决策

实际执行顺序定为 **Step1 → Step3 → Step2**：

```
Step1（基础信息收集）
  ↓
Step3（深度需求挖掘）
  ↓
Step2（雷达图维度评估，同时依赖 Step1 和 Step3 的输出）
```

LangGraph 节点注册和路由均按此顺序实现（`main_workflow.py` 中对应的 `add_edge` 调用顺序）。

---

## 后果

**积极后果**：
- 雷达图评估质量显著提升，因为获得了完整的需求上下文
- 工作流的实际行为符合业务逻辑

**消极后果（当前遗留问题）**：
- **命名顺序与执行顺序不一致**，造成持续的认知混淆
- 新维护者（包括 AI 辅助工具）阅读代码时，会错误地假设 Step1→Step2→Step3 的顺序
- 代码注释和文档中关于"步骤顺序"的说明相互矛盾

---

## 教训

**教训 1**：命名应该反映执行顺序。如果执行顺序是 1→3→2，节点应该命名为 Step1、Step2（原 Step3）、Step3（原 Step2），或更明确地用描述性名称（如 `basic_info_collection`、`deep_requirement_mining`、`radar_dimension_evaluation`）而非抽象的序号。

**教训 2**：当"命名无法修改"时（因为已有大量引用），必须在以下地方**明确文档化**实际执行顺序：
- 本 ADR（已完成）
- [MEMORY.md](../MEMORY.md)（已完成）
- 节点注册代码附近的注释

**建议的后续行动**：在 `main_workflow.py` 的步骤注册代码处，添加明确注释：

```python
# 注意：问卷步骤的执行顺序是 Step1 → Step3 → Step2（非命名顺序）
# Step2（雷达图）依赖 Step1 和 Step3 的输出，见 ADR-004
workflow.add_edge("progressive_step1_node", "progressive_step3_node")
workflow.add_edge("progressive_step3_node", "progressive_step2_node")
```

---

## 相关文件

- `intelligent_project_analyzer/workflow/main_workflow.py`（步骤节点注册和 add_edge 顺序）
- `intelligent_project_analyzer/interaction/`（问卷步骤实现）
