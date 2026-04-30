
---

# 并发冲突修复总结 (2025-11-25)

## 问题根源

LangGraph 的 InvalidUpdateError 是因为**同一个 step 内多个节点同时写入同一个字段**。

## 修复原则

 **只有工作流包装器节点可以更新 current_stage**
- 例如: _requirements_analyst_node, _batch_executor_node

 **交互节点不应更新 current_stage**
- 例如: calibration_questionnaire, equirements_confirmation
- 原因: 交互节点通常会通过 Command(goto=...) 路由到其他节点

## 已修复的节点

| 节点 | 文件 | 修复内容 | 状态 |
|------|------|---------|------|
| calibration_questionnaire | interaction/nodes/calibration_questionnaire.py | 移除 Line 133 的 current_stage 更新 |  已修复 |
| requirements_confirmation | interaction/nodes/requirements_confirmation.py | 移除 Line 96 的 current_stage 更新 |  已修复 |

## 需要注意的节点

| 节点 | 文件 | 状态 | 备注 |
|------|------|------|------|
| final_review | interaction/nodes/final_review.py |  潜在问题 | 当前被注释，启用时需检查 |
| manual_review | interaction/nodes/manual_review.py |  潜在问题 | 如果与其他节点同步执行需检查 |
| analysis_review | interaction/nodes/analysis_review.py |  已修复 | Line 350 已注释 |

## 测试验证

### 测试场景1: 问卷提交 + 需求重新分析
```
用户提交问卷  calibration_questionnaire (不更新stage)
   Command(goto=\"requirements_analyst\")
   requirements_analyst (更新stage)
 无冲突
```

### 测试场景2: 需求修改 + 重新分析
```
用户修改需求  requirements_confirmation (不更新stage)
   Command(goto=\"requirements_analyst\")
   requirements_analyst (更新stage)
 无冲突
```

## 预防措施

### 代码规范
1. 交互节点只负责收集用户输入和路由决策
2. 状态更新由目标节点负责（谁执行谁更新）
3. 使用 Command(update={...}, goto=...) 时，update 只包含交互历史等非关键字段

### 检查清单
- [ ] 节点是否会通过 Command 路由到其他节点？
- [ ] 如果是，是否移除了 current_stage 更新？
- [ ] 目标节点是否会更新 current_stage？
- [ ] 是否在同一 step 内有多个节点写入同一字段？

## 相关文档

- LangGraph 错误文档: https://docs.langchain.com/oss/python/langgraph/errors/INVALID_CONCURRENT_GRAPH_UPDATE
- 问卷优化文档: QUESTIONNAIRE_ENHANCEMENT_SUMMARY.md

