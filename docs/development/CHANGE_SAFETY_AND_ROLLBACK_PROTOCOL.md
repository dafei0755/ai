# 变更安全与回退规范

> 版本：v1.0
> 固化日期：2026-06-19
> 适用范围：本仓库所有代码、文档、配置、测试与资料库修改

## 1. 目标

本规范解决的不是“如何多复制一份文件”，而是让每次修改都满足三个条件：

1. 修改前有可恢复基线。
2. 修改中可审计、可分辨责任范围。
3. 修改后能按文件、代码块、提交或任务边界回退。

默认策略：**Git checkpoint 为主，补充备份为辅，分支或 worktree 用于隔离大改。**

## 2. 修改前强制协议

每次修改前必须先执行：

```powershell
git status --short
```

然后判断：

1. 当前工作区是否干净。
2. 目标文件是否已有修改。
3. 已有修改是否可能来自用户、历史任务或其他并行线程。
4. 本次任务是否跨模块、跨前后端、涉及核心链路或大量文件。
5. 是否存在重要的未跟踪文件。

如果工作区不干净，不能直接把所有脏改动视为本次任务的一部分。

## 3. Checkpoint 规则

重要改动前优先建立 Git checkpoint。

适用场景：

- 跨前端、后端、测试、配置的联动改动。
- 重构核心服务、入口服务、输出规划、运行时协议。
- 修改多个调用方或调整接口契约。
- 当前工作区已经有较多既有修改。
- 用户明确担心错误修改后无法回退。

推荐方式：

```powershell
git add <本次要保护的文件>
git commit -m "checkpoint: before <task>"
```

如果只是阶段性保护，也可以使用：

```powershell
git commit -m "wip: checkpoint before <task>"
```

禁止为了方便而执行 `git add .`。暂存必须按任务边界选择文件。

## 4. 未跟踪文件保护

Git 不会保护 `??` 文件。重要未跟踪文件必须先处理，否则不能假设它可回退。

处理方式：

1. 应进入项目历史的文件：加入 checkpoint。
2. 重要但不适合入 Git 的文件：建立本地备份和清单。
3. 可再生成的临时文件：加入 `.gitignore` 或留待清理。
4. 不确定的文件：先列入待确认清单，不删除。

特别注意：

- `docs/`、`sf/`、测试文件、registry、schema、activation pack、knowledge package 通常不是普通临时文件。
- `git diff` 默认看不到未跟踪文件正文，不能只靠 diff 判断它是否重要。

## 5. 分支与 Worktree

大改不应直接压在复杂脏工作区上。

推荐使用独立分支：

```powershell
git switch -c work/<task-name>
```

当当前工作区已经承载其他任务现场，优先使用独立 worktree 隔离：

```powershell
git worktree add ../<repo>-<task-name> -b work/<task-name>
```

是否使用 worktree 取决于当前树是否可安全切分；不能为了创建干净环境而丢弃现有修改。

## 6. 修改中纪律

执行修改时必须遵守：

1. 只改任务范围内文件。
2. 不顺手修无关问题。
3. 不覆盖已有用户改动。
4. 对已有脏文件，先理解 diff 再修改。
5. 每个阶段用 `git diff -- <paths>` 复核。

如果中途发现新问题，应记录为后续任务，而不是混入当前改动。

## 7. 回退规则

回退必须按粒度选择。

### 7.1 未提交改动

只允许针对明确路径或 hunk 回退，并确认不包含用户改动：

```powershell
git restore <file>
git restore -p <file>
```

### 7.2 已提交但未共享改动

可以按需要修正、拆分或回退，但要保留可解释历史。

常见方式：

```powershell
git revert <commit>
git reset --soft HEAD~1
```

### 7.3 已提交并可能被他人使用的改动

优先使用 `git revert <commit>`，生成反向提交，不改写历史。

## 8. 禁止动作

没有用户明确授权，禁止执行：

```powershell
git add .
git reset --hard
git checkout -- .
git clean -fd
git clean -fdx
git stash -u
git stash --all
```

这些命令可能混合、隐藏或删除不同批次的工作，尤其会影响未跟踪文件和被忽略文件。

## 9. Agent 执行协议

Agent 在本仓库修改文件前必须执行：

```text
1. 查看 git status。
2. 识别已有脏改动。
3. 说明是否需要 checkpoint。
4. 若涉及已有脏文件，先确认不会覆盖用户改动。
5. 只编辑任务范围文件。
6. 修改后报告 diff 摘要。
7. 运行与影响面匹配的验证。
8. 不擅自 reset、checkout、clean、stash 或删除文件。
```

如果当前工作区已经混有大量既有修改，Agent 不应擅自创建“包含全部文件”的 checkpoint commit。正确做法是先做状态审计，再由用户确认分批策略。

## 10. 当前仓库执行基线

截至 2026-06-19，本仓库已出现大量已修改文件和未跟踪文件。后续大改前应先做一次状态审计：

```text
应保留：
应提交：
应忽略：
应备份但不入 Git：
应清理：
需要用户确认：
```

在完成审计和 checkpoint 之前，任何新改动都应尽量小范围、可审计、可单独回退。



## 11. 脏工作树治理

当工作树存在大量 `M`、`??` 或跨前端、后端、测试、文档、资料库的混合改动时，不能只依赖本规范中的一般 checkpoint 规则。必须先执行专项脏工作树治理：

```text
docs/development/DIRTY_WORKTREE_GOVERNANCE_PROTOCOL.md
```

强制补充规则：

1. 先按 `G0-G4` 判定脏工作树等级，再决定继续小改、checkpoint、分支或 worktree。
2. 先按意图桶分类，再暂存、提交、回退或清理。
3. G3/G4 状态下禁止全量暂存、全量 stash、全量 clean、全量 restore。
4. 未跟踪的重要文档、测试、schema、registry、activation pack、knowledge package 和 `sf/` 资料必须先归类，不能当临时文件处理。
5. 新任务若要触碰已有脏文件，必须确认它与目标任务属于同一桶；否则应改用新文件、worktree 或等待用户确认。
## 12. 写入与运行卡顿治理

本规范只解决变更可恢复性；Agent 写入卡顿、长命令输出、Windows 编码、权限噪声和执行环境故障，统一按以下专项规范执行：

```text
docs/development/AGENT_WRITE_AND_RUN_RELIABILITY_PROTOCOL.md
```

强制补充规则：

1. 单个写入路径超过 60 秒无响应，必须停止等待并切换为更小、更可验证的写入方式。
2. 大文档或大范围机械改写必须拆分为小段，逐段读回和 diff。
3. 中文 Markdown 写入必须避免 BOM 和尾部空行噪声。
4. Git、缓存目录或 sandbox helper 出现权限/环境错误时，先修执行环境，不把它误判为业务代码错误。
5. 宽泛搜索和全量 diff 必须让位于目标路径、目标符号、目标错误的窄范围诊断。
## 13. 一句话原则

**Git checkpoint 负责可恢复，任务边界负责可审计，测试验证负责可交付；备份只补 Git 尚未保护的空白。**
