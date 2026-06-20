# 并行对话任务 Git 协同与合并协议

> 版本：v1.0
> 固化日期：2026-06-20
> 适用范围：多个 Codex/AI 对话任务、人工编辑、VS Code 操作同时可能修改同一仓库代码时的任务隔离、文件占用、提交、合并和冲突处理。

## 1. 问题定义

并行对话任务的风险不是“多人同时写代码”本身，而是多个任务在同一工作树里无边界叠加：

1. 两个对话同时修改同一个服务、组件或测试，后完成的一方覆盖前一方。
2. 一个任务正在做运行时代码，另一个任务顺手改文档或测试，提交边界混乱。
3. 工作树脏时继续开新任务，无法判断哪些修改属于当前对话。
4. 合并时用整文件覆盖解决冲突，丢掉另一条线程的有效改动。
5. 备份、checkpoint、push、PR 不区分任务线，导致回退和审查成本升高。

本协议目标：允许多线程并行推进，但每条线程必须有清晰边界、可独立验证、可独立回退、可按顺序合并。

## 2. 基本模型

每个并行对话任务都必须被视为一个 Task Lane。

Task Lane 至少包含：

```text
lane_id: 简短唯一名，例如 lane-demand-runtime
owner: human / codex session / other
branch_or_worktree: 当前隔离位置
scope: 本任务要解决的问题
owned_paths: 本任务优先修改的路径
shared_paths: 可能与其他 lane 冲突的路径
verification: 本 lane 必跑验证
merge_target: 合并目标分支
status: planned / active / blocked / ready_to_merge / merged / abandoned
```

如果任务小到不值得建文档，也必须在提交说明或对话总结里给出这些字段的简版。

## 3. 隔离级别

| 级别 | 场景 | 机制 | 说明 |
|---|---|---|---|
| L0 单线程 | 当前只有一个小任务 | 当前分支 + 干净工作树 | 适合 1-5 个文件小改 |
| L1 轻并行 | 多个任务但路径不重叠 | 同分支按路径提交 | 每个任务必须单独提交 |
| L2 中并行 | 多个任务可能共享测试或文档 | 独立分支 | 合并前按任务验证 |
| L3 强并行 | 多个对话会改前后端核心链路 | 独立 worktree + 独立分支 | 默认推荐 |
| L4 高风险并行 | 共享核心服务、schema、registry、路由、状态管理 | 先建 lane 文档 + 文件锁表 | 未确认前不得并行写同一文件 |

默认规则：

- 当前工作树干净但要开多个 Codex 对话：至少 L2。
- 任何任务会修改 B3/B4/B5 核心路径：推荐 L3。
- 两个任务会触碰同一文件：升级 L4。

## 4. 文件占用与软锁

本仓库不使用强制锁文件阻止编辑，但必须使用软锁规则。

### 4.1 独占文件

以下文件一旦被一个 lane 修改，其他 lane 不得同时修改，除非先协调：

```text
intelligent_project_analyzer/api/server.py
intelligent_project_analyzer/api/dual_mode_routes.py
intelligent_project_analyzer/services/demand_reconstruction_service.py
intelligent_project_analyzer/services/demand_reconstruction_output_planner.py
intelligent_project_analyzer/services/demand_reconstruction_insight_protocol.py
intelligent_project_analyzer/services/knowledge_governance_store.py
frontend-nextjs/app/analysis/[sessionId]/page.tsx
frontend-nextjs/components/ConversationMode/ConversationChat.tsx
frontend-nextjs/lib/api.ts
frontend-nextjs/package.json
frontend-nextjs/package-lock.json
```

### 4.2 共享但高风险文件

可并行读，不应并行写：

```text
README.md
QUICKSTART.md
docs/README.md
docs/development/*.md
intelligent_project_analyzer/config/registries/*.yaml
sf/2026.5.23/*
tests/services/test_demand_reconstruction_service.py
```

### 4.3 文件锁表

当出现 L4 并行时，应新增或更新：

```text
docs/development/parallel-lanes/<date>-<topic>.md
```

该文件记录：

```text
lane_id:
owned_paths:
shared_paths:
locked_paths:
handoff_order:
merge_order:
```

没有锁表时，默认谁先开始写，谁拥有该文件；后来的 lane 必须改路径、等合并或请求确认。

## 5. 分支与 Worktree 规则

### 5.1 分支命名

```text
lane/<date>-<short-topic>
work/<date>-<short-topic>
backup/<date>-<snapshot-purpose>
```

示例：

```text
lane/2026-06-20-demand-runtime
lane/2026-06-20-frontend-shell
lane/2026-06-20-git-governance
```

### 5.2 Worktree 位置

项目本地 worktree 默认放在：

```text
.worktrees/<branch-name>
```

`.worktrees/` 必须被 `.gitignore` 忽略。

### 5.3 创建前检查

每个新 lane 开始前必须检查：

```powershell
git status --short
git branch --show-current
git log --oneline -5
```

如果当前工作树不是 G0/G1，不应直接开新任务；先创建备份节点或独立 worktree。

## 6. 提交规则

每个 lane 至少一个独立提交，不允许把多个 lane 合进一个提交。

提交信息格式：

```text
<type>(lane-id): <intent>
```

示例：

```text
feat(lane-demand-runtime): add governed LLM reconstruction path
test(lane-demand-runtime): cover fallback priority
chore(lane-git-governance): add daily worktree health check
```

如果 lane 产生多个提交，最后可以 squash，但 squash 后仍必须保留 lane-id 和验证信息。

## 7. 合并机制

### 7.1 合并前门禁

每条 lane 合并前必须满足：

1. `git status --short` 干净。
2. 只包含该 lane 范围内文件。
3. 与目标分支差异可解释。
4. 必跑验证已通过或明确记录未跑原因。
5. 如果触碰共享文件，已查看目标分支最新 diff。

### 7.2 合并顺序

按风险从低到高：

1. B1 Git/Agent 治理。
2. B2 文档入口。
3. B6 独立测试与 smoke 工具。
4. B3 后端运行时。
5. B4 前端界面。
6. B5 管理后台/治理队列。
7. B7 产品资料与机制评审。

原因：先合并基础治理和低耦合文件，减少后续冲突；核心运行时和前端界面必须在最新基线上验证。

### 7.3 合并命令

优先使用非快进合并保留 lane 边界：

```powershell
git switch <merge_target>
git merge --no-ff <lane_branch>
```

如果 lane 是小型治理提交，也可以 fast-forward，但必须确认历史仍清楚。

### 7.4 冲突处理

冲突处理顺序：

1. 先看双方提交意图，不先改文件。
2. 对冲突文件运行 `git diff --ours -- <file>` 与 `git diff --theirs -- <file>`。
3. 小 hunk 手工合并，禁止整文件覆盖。
4. 合并后运行该文件所属 lane 的验证。
5. 在合并提交说明里记录冲突文件和处理原则。

禁止：

```powershell
git checkout --ours .
git checkout --theirs .
git restore .
git reset --hard
```

除非用户明确授权并已确认不会丢改动。

## 8. 并行对话 Agent 规则

每个 Codex 对话开始改代码前必须执行：

1. 看当前分支和状态。
2. 判断是否已有 active lane。
3. 判断目标文件是否属于其他 lane 的 owned/locked 路径。
4. 如果冲突，先报告并提出三选一：等待、改用新 worktree、缩小范围。
5. 如果不冲突，建立 lane 边界并继续。
6. 修改后只提交该 lane 文件。
7. 结束时报告 lane 状态、提交、验证、待合并风险。

## 9. Handoff 摘要格式

每个并行任务结束时必须给出：

```text
lane_id:
branch:
base_commit:
head_commit:
status:
files_changed:
verification:
merge_target:
merge_risks:
next_action:
```

没有这个摘要，不应进入合并队列。

## 10. 当前项目推荐执行方式

对于本项目后续多对话并行：

1. 需求重构后端 lane、前端界面 lane、Git 治理 lane 分开。
2. 修改 `demand_reconstruction_service.py`、`ConversationChat.tsx`、`analysis/[sessionId]/page.tsx` 的任务默认使用独立 worktree。
3. 每天的 Git 工作树健康检查只报告，不自动合并或清理。
4. 任何备份分支先保留，不参与普通 PR 合并。
5. 合并顺序以 B1 -> B2 -> B6 -> B3 -> B4 -> B5 -> B7 为默认。

## 11. 一句话规则

并行不是同时写同一棵树；并行是每条任务有 lane、有边界、有验证、有合并顺序。