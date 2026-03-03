# 前半链路 v7 语义对照矩阵

主项目：`D:\11-20\langgraph-design`

参考基线：`D:\11-20\langgraph-v7-0226-1000`

目标：保留当前 `langgraph-design` 的 mixin/graph 架构，仅恢复用户可见的 5 个节点步骤语义：

1. 输出意图确认
2. 任务梳理
3. 信息补全
4. 偏好雷达图
5. 需求洞察

## 对照结论

### 1. 输出意图确认

- 当前节点：`intelligent_project_analyzer/interaction/nodes/output_intent_detection.py`
- 前端映射：`output_intent_confirmation`
- 处理策略：保留当前独立节点，不回退
- 原因：该节点是当前架构中的 Step 0 主闸门，且前端已单独适配

### 2. 任务梳理

- 当前节点：`progressive_questionnaire_step1`
- 当前问题：节点内部存在 smart self-skip / fastpath 路由画像，会改变后续步骤顺序
- 回迁目标：固定进入“信息补全”，不允许直接跳雷达图或直接跳需求洞察
- 实施方式：`USE_V7_FRONTCHAIN_SEMANTICS=true` 时禁用节点内跳步路由

### 3. 信息补全

- 当前节点：`progressive_questionnaire_step2`
- 前端语义：第 2 步
- 后端实现位置：`step3_gap_filling()`，这是历史命名遗留
- 回迁目标：在 5 步 UI 语义下保持为固定第 3 节点中的“信息补全”
- 实施方式：保留现有 interrupt 类型 `progressive_questionnaire_step2`，只固定其来源和去向

### 4. 偏好雷达图

- 当前节点：`progressive_questionnaire_step3`
- 前端语义：第 4 个节点中的“偏好雷达图”
- 当前问题：节点内部允许因 smart self-skip 被跳过
- 回迁目标：信息补全后固定进入雷达图，雷达图完成后固定进入需求洞察
- 实施方式：`USE_V7_FRONTCHAIN_SEMANTICS=true` 时禁用雷达图跳过

### 5. 需求洞察

- 当前节点：`requirements_insight` / `questionnaire_summary`
- 处理策略：保留当前较新的需求洞察与需求确认合并节点
- 回迁内容：
  - 确保前置状态来自 5 步链路
  - 确保 Step1 快照与校正复盘字段可用
  - 确保确认/微调/重大修改三种分支仍可工作

## 本次代码改动范围

- `intelligent_project_analyzer/config/feature_flags.py`
- `intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py`

## 不在本次范围

- `quality_preflight`
- `batch_executor`
- `batch_aggregator`
- `batch_router`
- `detect_challenges`
- `result_aggregator`
- `projection_dispatcher`
- `pdf_generator`
