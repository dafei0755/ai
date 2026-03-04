# 系统治理知识库

**版本基线**: v8.0.0  
**用途**: 持续沉淀系统治理、演进复盘、战略判断和执行路线，供主理人与维护者快速定位关键背景。

---

## 快速索引

| 场景 | 文档 |
|---|---|
| 想知道系统当前健康状况 | [GOVERNANCE_REPORT.md](GOVERNANCE_REPORT.md) |
| 想执行已识别的治理动作 | [ACTION_PLAN.md](ACTION_PLAN.md) |
| 想了解开发规范、版本治理和回滚原则 | [DEV_WORKFLOW.md](DEV_WORKFLOW.md) |
| 想理解系统为什么会演进成现在这样 | [RETROSPECTIVE.md](RETROSPECTIVE.md) |
| 想用普通用户能看懂的话理解这款工具到底想解决什么问题 | [FINAL_REFLECTION_STRATEGIC_THESIS.md](FINAL_REFLECTION_STRATEGIC_THESIS.md) |
| 想给普通用户解释产品是做什么的 | [../../docs/USER_PLAIN_LANGUAGE_OVERVIEW.md](../../docs/USER_PLAIN_LANGUAGE_OVERVIEW.md) |
| 想了解市场上已经有哪些替代方案，以及这款工具为什么还有价值 | [MARKET_AND_ALTERNATIVE_VALIDATION.md](MARKET_AND_ALTERNATIVE_VALIDATION.md) |
| 想理解为什么最后选择做这类产品 | [STRATEGIC_OPTION_SCORECARD.md](STRATEGIC_OPTION_SCORECARD.md) |
| 想跨会话快速找关键背景 | [MEMORY.md](MEMORY.md) |
| 想追溯具体架构决策 | [adr/](adr/) |

---

## 核心文档说明

### 治理与复盘

- [GOVERNANCE_REPORT.md](GOVERNANCE_REPORT.md)  
  当前系统体检报告，聚焦风险、债务和优先级。
- [ACTION_PLAN.md](ACTION_PLAN.md)  
  已识别治理任务的执行路线图。
- [DEV_WORKFLOW.md](DEV_WORKFLOW.md)  
  开发与治理规范，包括版本管理、回滚和职责边界。
- [RETROSPECTIVE.md](RETROSPECTIVE.md)  
  系统演进复盘，解释“为什么会变成现在这样”。
- [MEMORY.md](MEMORY.md)  
  面向后续会话的精简知识库。

### 战略与方向

- [FINAL_REFLECTION_STRATEGIC_THESIS.md](FINAL_REFLECTION_STRATEGIC_THESIS.md)  
  面向普通读者的产品说明，解释“这款工具到底想解决什么问题”。
- [MARKET_AND_ALTERNATIVE_VALIDATION.md](MARKET_AND_ALTERNATIVE_VALIDATION.md)  
  面向普通读者的市场对比说明，解释“市面上已经有什么，以及这款工具为什么仍然有价值”。
- [STRATEGIC_OPTION_SCORECARD.md](STRATEGIC_OPTION_SCORECARD.md)  
  面向普通读者的方向选择说明，解释“为什么最后选择做 AI 设计决策工具，而不是别的形态”。

### 架构决策

- [adr/ADR-001-analysis-review-deprecation.md](adr/ADR-001-analysis-review-deprecation.md)
- [adr/ADR-002-true-parallel-asyncio-gather.md](adr/ADR-002-true-parallel-asyncio-gather.md)
- [adr/ADR-003-quality-control-frontloading.md](adr/ADR-003-quality-control-frontloading.md)
- [adr/ADR-004-progressive-questionnaire-step-ordering.md](adr/ADR-004-progressive-questionnaire-step-ordering.md)
- [adr/ADR-005-version-governance-ssot.md](adr/ADR-005-version-governance-ssot.md)
- [adr/ADR-006-questionnaire-step-naming-debt.md](adr/ADR-006-questionnaire-step-naming-debt.md)

---

## 目录结构

```text
sf/governance/
├── README.md
├── GOVERNANCE_REPORT.md
├── ACTION_PLAN.md
├── DEV_WORKFLOW.md
├── RETROSPECTIVE.md
├── FINAL_REFLECTION_STRATEGIC_THESIS.md
├── MARKET_AND_ALTERNATIVE_VALIDATION.md
├── STRATEGIC_OPTION_SCORECARD.md
├── MEMORY.md
└── adr/
```

---

## 使用顺序建议

1. 先读 [RETROSPECTIVE.md](RETROSPECTIVE.md) 了解系统历史。
2. 再读 [GOVERNANCE_REPORT.md](GOVERNANCE_REPORT.md) 理解当前债务和风险。
3. 若要判断方向，直接读 [FINAL_REFLECTION_STRATEGIC_THESIS.md](FINAL_REFLECTION_STRATEGIC_THESIS.md)。
4. 若要核验证据，读 [MARKET_AND_ALTERNATIVE_VALIDATION.md](MARKET_AND_ALTERNATIVE_VALIDATION.md) 和 [STRATEGIC_OPTION_SCORECARD.md](STRATEGIC_OPTION_SCORECARD.md)。
5. 若要实施变更，再回到 [ACTION_PLAN.md](ACTION_PLAN.md) 和 [DEV_WORKFLOW.md](DEV_WORKFLOW.md)。
