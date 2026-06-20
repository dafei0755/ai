# 功能版本链管理协议

版本：v1.0
日期：2026-06-20
状态：active guardrail

## 1. 目标

本协议用于管理重要功能、运行机制和系统合同的持续演进。它解决的问题不是“有没有备份”，而是每一次机制修改是否处在一条清晰、连续、可验证、可回退的版本链上。

对核心功能而言，备份分支、快照提交、实验分支、临时文档都不能单独证明“已实施”。已实施必须进入当前权威版本链。

## 2. 已实施定义

一个功能修改只有同时满足以下条件，才能称为已实施：

1. 基于明确的当前权威版本开始。
2. 使用明确的功能分支或受控 lane 推进。
3. 代码、文档、测试属于同一个功能目标。
4. 有守护测试、验收脚本或人工验收记录证明新机制生效。
5. 已提交到当前权威分支，或该功能分支被明确标记为新的权威候选。
6. 有清楚的上一个版本和回退方式。
7. 已更新 `docs/development/FEATURE_VERSION_LEDGER.md`。

不满足以上条件的状态，只能标记为：

- `draft`: 草稿或方案。
- `experiment`: 实验实现。
- `backup_only`: 已保存但不在权威链。
- `ready_to_promote`: 已验证，等待晋升。
- `implemented`: 已进入权威链。
- `deprecated`: 已被新版本取代。

## 3. 功能版本链

每个重要功能必须维护自己的版本链。版本号不要求复杂，但必须表达顺序和含义。

推荐格式：

```text
feature_id: demand-reconstruction
v1.0: 规则蓝图机制
v1.1: 强制需求重构入口
v1.2: LLM 参与洞察
v1.3: LLM-first 理解层
v1.4: typed 503 不可用合同
v1.5: 潜变量统一合同
```

每次修改必须回答：

```text
current_version:
target_version:
base_branch:
base_commit:
work_branch:
changed_runtime_paths:
changed_docs:
changed_tests:
verification:
rollback_target:
promotion_decision:
```

## 4. 分支语义

分支名称不能替代状态判断。状态以版本账本和验证结果为准。

```text
main / stable
  稳定版本或可发布版本。

feature/<feature-id>-v<target-version>
  针对某个功能版本的正式修改。

fix/<feature-id>-<issue>
  针对已知问题的修复，必须说明基于哪个功能版本。

experiment/<topic>
  可试错，不得直接宣称已实施。

backup/<date>-<purpose>
  只做保全，不代表实施，不作为长期开发主线。
```

`backup/*` 的唯一含义是保护现场。它不能作为“已实施”的证据，也不能在没有晋升记录的情况下替代功能分支。

## 5. 晋升规则

实验、备份或功能分支要成为权威版本，必须执行晋升流程：

1. 确认目标分支和基线提交。
2. 用 merge、cherry-pick 或重放补丁把变更纳入目标分支。
3. 检查高风险文件 diff，禁止整文件覆盖解决冲突。
4. 运行该功能的必需验证。
5. 更新功能版本账本。
6. 提交晋升 commit，或给出明确 tag。
7. 报告 `base_commit`、`head_commit`、`verification` 和 `rollback_target`。

没有完成晋升流程的内容，仍然是 `backup_only`、`experiment` 或 `ready_to_promote`。

## 6. 回退规则

每个功能版本都必须有回退目标。

允许的回退方式：

- `git revert <commit>`：优先用于已经提交到共享分支的变更。
- 回退到上一个 tag 或记录的 checkpoint。
- 逐文件恢复：只恢复明确路径，并人工确认不会覆盖后续有效修改。

禁止把以下动作当作普通回退手段：

```powershell
git reset --hard
git restore .
git checkout -- .
git clean -fd
git clean -fdx
```

这些命令只有在用户明确批准、且已确认不会丢失本地重要文件后才能执行。

## 7. 功能版本账本

所有重要功能版本必须登记到：

```text
docs/development/FEATURE_VERSION_LEDGER.md
```

账本不是说明文档，而是当前权威状态索引。它至少记录：

```text
feature_id:
current_authoritative_version:
authoritative_branch:
authoritative_commit:
status:
contract:
guard_tests:
rollback_target:
last_promotion:
notes:
```

当代码、测试或文档发生影响机制合同的变化时，账本必须同步更新。

## 8. 需求重构强规则

需求重构、LLM-first、项目类型检测、方案入口、知识资产治理属于高风险机制。任何修改这些机制的任务，必须同时遵守：

```text
docs/development/CHANGE_SAFETY_AND_ROLLBACK_PROTOCOL.md
docs/development/FEATURE_VERSION_LEDGER.md
```

对于需求重构 LLM-first，当前合同是：

```text
用户输入 -> DemandReconstructionService -> LLM Semantic Router -> asset/rule scan -> LLM Final Synthesis -> quality/alignment gates
```

当 `DEMAND_RECONSTRUCTION_USE_LLM=1` 时，不允许静默回退旧规则蓝图。理解或综合不可用必须返回 typed unavailability，并由路由映射为 HTTP 503。
