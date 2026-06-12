# 2026-06-12 文件目录规范整理报告

## 处理目标

本次整理目标是降低根目录噪声，明确文件归属规则，并建立可重复执行的本地归档机制。

处理原则：

1. 不删除重要资料。
2. 不处理 `docs/`、`sf/`、源码目录、测试目录中的文件。
3. 根目录临时文件只移动到 `_archive/`，不物理删除。
4. 归档过程必须可追溯、可恢复。

## 已完成动作

### 1. 新增目录管理规则

新增：

- `docs/development/文件目录管理规则-file-directory-management-rules.md`

规则明确了：

- 根目录应该保留什么。
- `docs/`、`sf/`、`scripts/`、源码、测试、配置等目录的职责边界。
- 哪些文件必须 Git 跟踪。
- 哪些文件必须忽略。
- 哪些文件只适合本地保留。
- 自动归档脚本的执行规则。

### 2. 新增自动归档脚本

新增：

- `scripts/archive_workspace_files.py`

脚本特性：

- 默认 dry-run。
- 只处理根目录明确临时命名的文件。
- 跳过已被 Git 跟踪的文件。
- 跳过目录。
- 不处理 `docs/`、`sf/`、源码目录、测试目录。
- `--apply` 时只移动到 `_archive/`，不删除。

### 3. 归档根目录临时文件

已执行：

```bash
python scripts/archive_workspace_files.py --apply
```

结果：

- 归档文件数量：99
- 归档目录：`_archive/local-cleanup/2026-06-12/root-temp/`
- manifest：`_archive/local-cleanup/2026-06-12/archive-manifest.jsonl`

这些文件主要是历史调试脚本、一次性 patch 脚本、测试输出、扫描输出和日志文件。

### 4. 保护重要文档与资料目录

已从 stash 单独恢复并准备纳入 Git 跟踪：

- `docs/development/2026.6.11-下阶段开发进度安排.md`
- `sf/2026.5.23/`

原因：

- `docs/` 下正式开发计划属于团队协作资料。
- `sf/2026.5.23/` 是方案高参核心产品定义和知识体系资料。
- 这类文件不能长期处于 `??` 未跟踪状态，否则容易被 `stash -u` 或清理动作移走。

## 未处理范围

本次未处理：

- `node_modules/`
- `.conda/`
- `.cache/`
- `.pytest_cache/`
- `.playwright-cli/`
- `output/`
- `logs/`
- 本地数据库
- 压缩包
- `sf/` 其他目录
- 源码、测试、前端、后端业务文件

这些内容需要按后续批次单独确认，不在本次根目录临时文件归档范围内。

## 后续规则

以后进行目录整理时，先运行：

```bash
python scripts/archive_workspace_files.py
```

确认 dry-run 清单无误后，才允许执行：

```bash
python scripts/archive_workspace_files.py --apply
```

禁止用以下命令替代归档脚本：

```bash
git clean -fd
git clean -fdx
git stash -u
git stash --all
```

## 当前判断

本次整理属于“目录治理与本地归档机制”批次，不与业务功能修改混合。
