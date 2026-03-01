# 系统治理知识库

**版本基线**：v8.0.0（2026-02-28）
**用途**：跨会话持久化知识库，提供治理现状、行动计划、架构决策记录和开发规范。

---

## 快速索引

| 场景 | 文档 |
|------|------|
| 想知道系统现在健康状况 | [GOVERNANCE_REPORT.md](GOVERNANCE_REPORT.md) |
| 想执行具体修复任务 | [ACTION_PLAN.md](ACTION_PLAN.md) |
| 想了解开发规范/版本管理/回滚 | [DEV_WORKFLOW.md](DEV_WORKFLOW.md) |
| 想理解"系统为什么是现在这个样子" | [RETROSPECTIVE.md](RETROSPECTIVE.md) |
| AI 辅助工具快速检索关键知识点 | [MEMORY.md](MEMORY.md) |
| 查阅具体架构决策的来龙去脉 | [adr/](adr/) |

## ADR 索引

| 编号 | 标题 | 版本 | 一句话摘要 |
|------|------|------|------------|
| [ADR-001](adr/ADR-001-analysis-review-deprecation.md) | 废弃 analysis_review 节点 | v2.2 | 质量审核前置化，废弃后置节点，但路由函数未同步清理，遗留 P0 死代码 |
| [ADR-002](adr/ADR-002-true-parallel-asyncio-gather.md) | asyncio.gather 真并行 | v7.502 | 绕过 Send API 实现真并行，速度提升 67%，但引入了无并发上限的新风险 |
| [ADR-003](adr/ADR-003-quality-control-frontloading.md) | 质量控制前置化 | v7.280 | 将质量审核从后置合并到任务分派阶段，减少专家白做 |
| [ADR-004](adr/ADR-004-progressive-questionnaire-step-ordering.md) | 问卷步骤实际执行顺序 | v7.80 | 执行顺序 Step1→Step3→Step2，命名顺序≠执行顺序 |
| [ADR-005](adr/ADR-005-version-governance-ssot.md) | 版本治理 SSOT | v8.0.0 | VERSION 文件作为唯一版本源，SemVer 规范，应该在 v7.0 就建立 |

## 目录说明

```
sf/governance/
├── README.md              ← 本文件（索引）
├── GOVERNANCE_REPORT.md   ← 体检报告（代码行号溯源）
├── ACTION_PLAN.md         ← 可执行修复路线图（P0/P1/P2/P3）
├── DEV_WORKFLOW.md        ← 稳定开发工作流规范（版本管理/回滚/职责界面）
├── RETROSPECTIVE.md       ← 演进复盘备忘录
├── MEMORY.md              ← 跨会话知识库（精简，<80行）
└── adr/                   ← 架构决策记录（5个）
```
