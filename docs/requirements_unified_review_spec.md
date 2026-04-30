# 需求侧三合一统一审核（Requirements Unified Review）功能需求

> 日期：2026-03-10  
> 适用位置：`requirements_insight -> requirements_unified_review -> project_director`

## 1. 目标

在“需求洞察”之后、`project_director` 之前，增加一层**统一人工审核**，审核对象为：

- 任务（Task）
- 交付物（Deliverable）
- 角色建议（Role Hint）

该节点不再使用“人物审批”命名，统一称为：**三合一统一审核**。

## 2. 交互契约（与前端兼容）

中断类型统一使用：`interaction_type = role_and_task_unified_review`。

为兼容现有 `RoleTaskReviewModal`，payload 至少包含：

- `role_selection.selected_roles`
- `task_assignment.task_list`
- `plan_view.work_packages`（可选）
- `options`（包含 approve/modify_roles/modify_tasks/edit_deliverables/change_strategy/reject）
- `close_previous_modal = true`

## 3. 动作语义

- `approve/confirm`：确认通过，进入 `project_director`
- `modify_roles`：记录 `role_modification_request`，进入 `project_director`
- `modify_tasks`：记录 `task_modification_request`，进入 `project_director`
- `edit_deliverables`：记录 `deliverable_work_packages` 更新，进入 `project_director`
- `change_strategy`：记录 `requested_strategy` + `retry_reason`，进入 `project_director`
- `reject/modify`：回到 `requirements_analyst`，并写入 `retry_reason`

## 4. 状态字段

### 4.1 新增字段（需求侧统一审核）

- `requirements_unified_review_status`: `approved | rejected`
- `requirements_unified_review_result`: 审核摘要（approved/timestamp/has_user_modifications）
- `requirements_unified_review_change_log`: 审计日志列表

### 4.2 通用统一审核字段（兼容后段统一审核）

- `role_selection_approved`
- `task_assignment_approved`
- `unified_review_result`

## 5. 非功能要求

- 不改变后段 `role_task_unified_review` 的节点语义与行为
- 保持 WebSocket interrupt 分发逻辑不变（复用现有 modal）
- 失败时降级到 `requirements_analyst`，不得中断整个工作流

## 6. 验收标准

1. 从 `questionnaire_summary` 确认后跳转到 `requirements_unified_review`
2. 前端可正常弹出统一审核 Modal（非空角色/任务内容）
3. approve 与 modify_* 能进入正确路由并写入对应 state 字段
4. 现有问卷链路定向测试通过
