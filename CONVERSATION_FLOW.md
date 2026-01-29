# 对话执行流程节点

## 节点分类清单

### 1. 安全验证（3个节点）
- `unified_input_validator_initial` - 初始输入验证
- `unified_input_validator_secondary` - 二次验证
- `input_rejected` - 拒绝终止

### 2. 需求收集（6个节点）
- `requirements_analyst` - 需求分析
- `feasibility_analyst` - 可行性分析
- `progressive_step1_core_task` - 问卷第1步：核心任务梳理
- `progressive_step3_gap_filling` - 问卷第2步：信息补全（实际step3）
- `progressive_step2_radar` - 问卷第3步：雷达图选择（实际step2）
- `requirements_confirmation` - 需求确认

### 3. 任务规划（5个节点）
- `project_director` - 项目总监（角色选择）
- `deliverable_id_generator` - 交付物ID生成
- `search_query_generator` - 搜索查询生成
- `role_task_unified_review` - 角色任务审核
- `quality_preflight` - 质量预检

### 4. 批次执行（5个节点）
- `batch_executor` - 批次执行器
- `agent_executor` - 智能体执行器（并行）
- `batch_aggregator` - 批次聚合器
- `batch_router` - 批次路由器
- `batch_strategy_review` - 批次策略审核

### 5. 审核检测（3个节点）
- `analysis_review` - 分析审核（多视角）
- `detect_challenges` - 挑战检测
- `manual_review` - 人工审核

### 6. 结果生成（4个节点）
- `result_aggregator` - 结果聚合
- `report_guard` - 报告审核
- `pdf_generator` - PDF生成
- `user_question` - 用户追问

## 主执行流程

```mermaid
graph LR
    A[输入验证] --> B[需求分析]
    B --> C[可行性分析]
    C --> D[二次验证]
    D --> E[问卷调查]
    E --> F[需求确认]
    F --> G[角色选择]
    G --> H[质量预检]
    H --> I[批次执行循环]
    I --> J[分析审核]
    J --> K[挑战检测]
    K --> L[结果聚合]
    L --> M[PDF生成]
```

## 关键循环路径

### 问卷循环
```
step1 核心任务 ↔ step3 信息补全 ↔ step2 雷达图
```

### 批次执行循环
```
batch_executor → agent_executor (并行) → batch_aggregator
→ batch_router → batch_strategy_review → batch_executor
```

### 审核重执行
```
analysis_review → batch_executor (特定专家重做)
```

### 挑战反馈
```
detect_challenges → requirements_analyst (需求澄清)
```

## 节点功能快速参考

| 节点名称 | 功能说明 | 关键输出 |
|---------|---------|---------|
| unified_input_validator_initial | 安全检测、领域分类、复杂度评估 | 通过/拒绝 |
| requirements_analyst | 提取核心需求 | requirements |
| feasibility_analyst | 后台可行性判断 | feasibility_score |
| progressive_step1 | 用户确认核心任务列表 | core_tasks |
| progressive_step3 | LLM生成补充问题 | gap_questions |
| progressive_step2 | 多维度雷达图选择 | selected_dimensions |
| requirements_confirmation | 用户确认完整需求 | final_requirements |
| project_director | 动态选择专家团队 | selected_roles, batches |
| deliverable_id_generator | 为每个任务生成ID | deliverable_metadata |
| quality_preflight | 预检质量约束 | quality_constraints |
| batch_executor | 准备当前批次 | batch_send_list |
| agent_executor | 执行单个专家（并行） | agent_results |
| batch_aggregator | 验证批次完成 | batch_complete |
| batch_router | 决定下一步 | 下一批次/审核/结束 |
| batch_strategy_review | 用户确认批次策略 | 批准/拒绝 |
| analysis_review | 红蓝对抗+评委裁决 | improvement_suggestions |
| detect_challenges | 检测专家协作冲突 | challenge_flags |
| manual_review | 严重问题人工裁决 | 继续/整改/终止 |
| result_aggregator | 整合所有专家成果 | final_report |
| report_guard | 审核报告内容 | cleaned_report |
| pdf_generator | 生成PDF文档 | pdf_path |
| user_question | 处理用户追问 | 继续/结束 |

## 条件分支说明

### unified_input_validator_initial
- 安全通过 → requirements_analyst
- 安全拒绝 → input_rejected

### unified_input_validator_secondary
- 领域一致 → progressive_step1
- 领域漂移 → requirements_analyst

### requirements_confirmation
- 用户确认 → project_director
- 用户修改 → requirements_analyst

### batch_router
- 还有下批 → batch_strategy_review
- 全部完成 → analysis_review
- 重执行跳过审核 → detect_challenges

### detect_challenges
- 无挑战 → result_aggregator
- 需澄清 → requirements_analyst
- 严重问题 → manual_review

### pdf_generator
- 有追问 → user_question
- 直接结束 → END

## 并行执行机制

系统使用 LangGraph 的 **Send API** 实现批次内专家的并行执行：

```python
# 批次执行器创建多个Send对象
[Send("agent_executor", state_for_expert_1),
 Send("agent_executor", state_for_expert_2),
 Send("agent_executor", state_for_expert_3)]

# 所有agent_executor并行执行后汇聚到batch_aggregator
```

## 完整流程示例

正常无拒绝/修改的完整流程：

```
START
→ unified_input_validator_initial
→ requirements_analyst
→ feasibility_analyst
→ unified_input_validator_secondary
→ progressive_step1_core_task
→ progressive_step3_gap_filling
→ progressive_step2_radar
→ requirements_confirmation
→ project_director
→ deliverable_id_generator
→ search_query_generator
→ role_task_unified_review
→ quality_preflight
→ batch_executor
→ [并行] agent_executor × N (第1批次)
→ batch_aggregator
→ batch_router
→ batch_strategy_review
→ batch_executor
→ [并行] agent_executor × M (第2批次)
→ batch_aggregator
→ batch_router
→ analysis_review
→ detect_challenges
→ result_aggregator
→ report_guard
→ pdf_generator
→ END
```

## 参考文件

- 主工作流定义：[intelligent_project_analyzer/workflow/main_workflow.py](intelligent_project_analyzer/workflow/main_workflow.py)
- 问卷节点：[intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py](intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py)
