# 每日 Git 工作树安全检查机制

> 版本：v1.0
> 固化日期：2026-06-20
> 适用范围：本仓库每日自动检查 Git 工作树状态、生成安全报告、提示分桶整理建议。

## 1. 目标

每日自动检查工作树是否从干净状态退化为 G1-G4，并生成报告。该机制默认只读，不自动提交、不删除文件、不回退文件、不 stash。

## 2. 文件

```text
scripts/daily_git_worktree_check.ps1
scripts/register_daily_git_worktree_check.ps1
docs/development/DAILY_GIT_WORKTREE_MAINTENANCE.md
```

报告输出到：

```text
reports/git-worktree-health/
```

`reports/` 已在 `.gitignore` 中忽略，因此日报不会污染工作树。

## 3. 手动运行

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/daily_git_worktree_check.ps1
```

输出内容包括：

1. 当前分支与 HEAD。
2. 工作树等级 `G0-G4`。
3. tracked / untracked 数量。
4. 按 B1-B9 分桶的文件清单。
5. `.codegraph` 等本地索引目录是否被忽略。
6. 下一步整理建议。

## 4. 注册每日任务

默认每天 09:20 执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/register_daily_git_worktree_check.ps1
```

指定时间：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/register_daily_git_worktree_check.ps1 -DailyAt 18:30
```

计划任务名称：

```text
LangGraphDesignDailyGitWorktreeCheck
```

## 5. 安全边界

每日任务只运行检查脚本。检查脚本不会执行：

```text
git add
git commit
git clean
git restore
git reset
git stash
```

如果报告显示 G2-G4，整理动作必须人工确认并按桶执行。禁止把每日任务升级成自动 reset、自动 clean、自动 stash 或自动提交。

## 6. 当前写入机制修正

本机制文件创建时再次复现了 `apply_patch` 卡住：新增三个小文件的 patch 超过 6 分钟没有完成并被中断，且没有半写入。此前大 patch 和小 patch 也出现过同类卡顿。

因此本仓库后续维护规则修正为：

1. `apply_patch` 只可用于很小且可立即返回的补丁。
2. 任意写入超过 60 秒无结果，必须停止等待并换路。
3. 新增文件、长文档、脚本类写入优先使用 BOM-free 原子写入。
4. 写后必须读回、检查 BOM、检查目标路径 `git status`。

## 7. 维护规则

1. 每次重要开发前先看最近一份日报。
2. 如果日报连续出现 G3/G4，应先做备份节点，再继续新任务。
3. 如果日报出现权限噪声，应先修 Git ignore、缓存目录或本地 exclude。
4. 如果日报出现大量 B9，应暂停提交，先确认文件来源。
5. 报告目录可以定期清理旧报告，但不应纳入 Git。