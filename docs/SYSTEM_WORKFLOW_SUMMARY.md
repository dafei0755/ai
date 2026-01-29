# 系统工作流快速参考

> 这是 [SYSTEM_WORKFLOW_COMPLETE_GUIDE.md](SYSTEM_WORKFLOW_COMPLETE_GUIDE.md) 的精简版本，用于快速查阅。
> **⚠️ v7.151 更新**: 需求确认流程已合并到问卷汇总（需求洞察）

## 🎯 核心数据

- **总节点数**: 30 个 (v7.151: 合并 requirements_confirmation)
- **执行阶段**: 9 个（0-8）
- **用户交互点**: 6 个 (v7.151: 优化交互流程)
- **自动化节点**: 24 个
- **平均执行时间**: 3-15 分钟（不含用户交互）

## 📊 9 大执行阶段 (v7.151 更新)

| 阶段 | 名称 | 节点数 | 用户交互 | 平均耗时 |
|------|------|--------|---------|---------|
| 0 | 安全验证层 | 2 | ❌ | < 1s |
| 1 | 需求收集与分析 | 3 | ❌ | 10-30s |
| 2 | 三步递进式问卷 | 4 | ✅ (4次，含需求洞察) | 用户决定 |
| ~~3~~ | ~~需求确认~~ | ~~1~~ | ~~✅~~ | ~~已合并到阶段2~~ |
| 3 | 战略规划 | 4 | ✅ | 15-45s |
| 4 | 质量预检 | 1 | ⚠️ (高风险时) | 5-15s |
| 5 | 动态批次执行 | 5 | ⚠️ (可选) | 2-10分钟 |
| 6 | 质量审核 | 3 | ⚠️ (严重问题时) | 30-90s |
| 7 | 报告生成 | 3 | ❌ | 20-60s |
| 8 | 后续跟进 | 1 | ✅ (可选) | 用户决定 |

## 🔄 关键节点速查 (v7.151 更新)

### 必经节点（所有流程）
1. `unified_input_validator_initial` - 安全检查
2. `requirements_analyst` - 需求分析
3. `progressive_step1_core_task` - 任务拆解 ✅
4. `progressive_step3_gap_filling` - 差距填补 ✅
5. `progressive_step2_radar` - 维度选择 ✅
6. `questionnaire_summary` - 需求洞察（合并需求确认）✅
7. ~~`requirements_confirmation`~~ - ~~需求确认~~ ❌ **已废弃 v7.151**
8. `project_director` - 专家选择
9. `role_task_unified_review` - 任务审核 ✅
10. `batch_executor` → `agent_executor` - 专家执行
11. `analysis_review` - 质量审核
12. `result_aggregator` - 结果聚合
13. `pdf_generator` - PDF 生成

### 条件节点（特定情况）
- `input_rejected` - 安全拒绝时
- `quality_preflight` - 高风险警告时 ⚠️
- `batch_strategy_review` - 批次预览时 ⚠️
- `manual_review` - 严重质量问题时 ⚠️
- `user_question` - 后续提问时 ✅

## 🎨 专家角色体系

| 角色 | 代号 | 批次 | 依赖 | 主要职责 |
|------|------|------|------|---------|
| 设计总监 | V2 | 2 | V3,V4,V5 | 空间概念、美学框架 |
| 叙事专家 | V3 | 1 | 无 | 角色原型、情感旅程 |
| 研究专家 | V4 | 1 | 无 | 案例研究、设计模式 |
| 场景专家 | V5 | 1 | 无 | 情境分析、用户生态 |
| 总工程师 | V6 | 2 | V2 | 可行性、系统集成 |
| 情感洞察 | V7 | 1 | 无 | 情绪地图、心理安全 |

## 🛡️ 质量控制三层

1. **Layer 1: 预检** (`quality_preflight`)
   - 执行前风险评估
   - 并行评估所有专家
   - 高风险任务警告

2. **Layer 2: 监控** (`agent_executor`)
   - 实时质量验证
   - 自动重试机制
   - WebSocket 进度推送

3. **Layer 3: 审核** (`analysis_review`)
   - 红队 (风险识别)
   - 蓝队 (验证优化)
   - 裁判 (优先级排序)
   - 客户 (最终决策)

## 🔀 关键路由逻辑

### 需求确认路由
```
批准 + 无修改 → project_director
批准 + 有修改 → requirements_analyst (重新分析)
拒绝 → requirements_analyst
```

### 批次执行路由
```
更多批次 → batch_strategy_review → batch_executor
全部完成 → analysis_review
```

### 质量审核路由
```
批准 → detect_challenges
重跑 (≤1轮) → batch_executor
重跑 (>1轮) → detect_challenges (达到最大轮次)
```

### 挑战检测路由
```
>3 must_fix → manual_review (人工介入)
需客户审核 → analysis_review
需反馈循环 → requirements_analyst
继续 → result_aggregator
```

## 📝 状态字段速查

### 核心字段
- `session_id`, `user_id` - 会话标识
- `user_input` - 用户原始输入
- `structured_requirements` - 结构化需求
- `active_agents` - 激活的专家列表
- `agent_results` - 专家执行结果
- `final_report` - 最终报告

### 问卷字段
- `extracted_core_tasks` - 提取的核心任务
- `confirmed_core_tasks` - 用户确认的任务
- `gap_filling_answers` - 差距填补答案
- `radar_dimension_values` - 雷达图维度值
- `restructured_requirements` - 重构后的需求

### 批次字段
- `execution_batches` - 批次列表
- `current_batch` - 当前批次
- `total_batches` - 总批次数
- `completed_batches` - 已完成批次

### 审核字段
- `review_round` - 审核轮次
- `review_history` - 审核历史
- `improvement_suggestions` - 改进建议
- `analysis_approved` - 分析是否批准

## 🚀 执行模式

| 模式 | 说明 | 用户交互 | 适用场景 |
|------|------|---------|---------|
| **Manual** | 手动确认每个批次 | 最多 | 重要项目、首次使用 |
| **Automatic** | 全自动执行 | 最少 | 快速验证、批量处理 |
| **Preview** | 预览后自动执行 | 中等 | 平衡透明度与效率 |

## 🔧 常见问题快速排查

| 问题 | 检查项 | 解决方案 |
|------|--------|---------|
| 工作流卡住 | Redis连接、checkpoint数据 | 重启Redis、检查日志 |
| 批次执行失败 | execution_batches格式、角色配置 | 验证YAML文件、检查API配置 |
| 并发更新冲突 | reducer函数、Annotated类型 | 确认状态定义正确 |
| LLM超时 | 网络连接、API配额 | 增加timeout、检查余额 |

## 📚 完整文档

详细信息请参阅：
- [SYSTEM_WORKFLOW_COMPLETE_GUIDE.md](SYSTEM_WORKFLOW_COMPLETE_GUIDE.md) - 完整工作流指南（532行）
- [AGENT_ARCHITECTURE.md](AGENT_ARCHITECTURE.md) - 智能体架构说明
- [main_workflow.py](../intelligent_project_analyzer/workflow/main_workflow.py) - 源代码实现

---

**最后更新**: 2026-01-07
**版本**: v7.150+
