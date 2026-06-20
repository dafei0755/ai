# 脏工作树治理协议

> 版本：v1.0
> 固化日期：2026-06-20
> 适用范围：本仓库出现大量 `M`、`??`、跨前后端/文档/资料库混合变更时的 Git 分组、checkpoint、提交、回退与 Agent 执行策略。

## 1. 问题定义

脏工作树不是简单的“有改动”。本仓库的风险在于多条任务线长期叠加：前端、后端、测试、docs、sf 资料、CodeGraph、运行脚本和本地缓存可能同时出现。此时如果继续按普通开发习惯执行 `git add .`、全量 stash、全量 clean、整文件覆盖或无边界提交，会导致三个问题：

1. 误提交：把无关任务、临时文件、缓存或资料库混入同一个提交。
2. 误回退：为了撤销某个改动，顺手丢掉用户或其他任务的工作。
3. 难验证：提交无法对应单一测试或单一回滚路径，后续出错时无法定位。

截至本协议制定时，当前工作树快照为：

```text
M: 50
??: 34
主要目录：frontend-nextjs 30, intelligent_project_analyzer 17, tests 17, docs 11
当前分支：fix/scheme-advisor-question-root-cause-20260616
HEAD: 6981ae4
```

该快照只作为本次制定协议的证据；未来执行时必须重新运行状态审计。

## 2. 治理目标

本协议要让 Git 机制变得更清晰、智能、安全、稳定：

1. 清晰：任何改动都能归入明确任务桶。
2. 智能：根据风险自动选择继续小改、checkpoint、分支、worktree 或暂停整理。
3. 安全：任何清理或回退都不覆盖未知来源改动。
4. 稳定：状态审计、暂存、提交、验证和回退都有固定命令与固定门禁。

## 3. 脏工作树分级

| 等级 | 判定 | 允许动作 | 禁止动作 |
|---|---|---|---|
| G0 干净 | `git status --short` 无输出 | 正常开发；任务前建分支可选 | 无 |
| G1 轻微 | 1-5 个文件，且同一任务 | 可继续小改；提交前按路径暂存 | `git add .` |
| G2 中等 | 6-20 个文件，或跨 2-3 个目录 | 先分桶；本次只处理一个桶；必要时 checkpoint | 全量 diff、全量 stash |
| G3 严重 | 超过 20 个文件，或同时含 `M` 与大量 `??` | 必须状态审计；优先分支/worktree；只做窄范围改动 | 大范围重构、无清单提交 |
| G4 冻结 | 存在删除、冲突、权限错误、未知大文件、资料库混杂 | 停止功能开发；先做恢复边界与清单 | reset/clean/checkout/stash-all |

当前快照属于 G3。若后续发现删除文件、冲突、权限错误或无法解释的大文件，升级为 G4。

## 4. 状态审计命令

每次治理前先生成最小审计：

```powershell
git status --short
```

再生成分布统计：

```powershell
$lines = git status --short
$rows = foreach ($line in $lines) {
  if ($line.Length -lt 4) { continue }
  $status = $line.Substring(0,2)
  $path = $line.Substring(3)
  $top = ($path -replace '^"','' -split '[\\/]')[0]
  [pscustomobject]@{Status=$status; Top=$top; Path=$path}
}
$rows | Group-Object Status | Sort-Object Name
$rows | Group-Object Top | Sort-Object Count -Descending
```

对目标任务只看目标路径：

```powershell
git status --short -- <path1> <path2>
git diff -- <path1> <path2>
```

不得在 G3/G4 状态下先跑全量 `git diff` 作为主要依据。

## 5. 分桶规则

脏工作树必须按“意图桶”分类，而不是按文件后缀或目录机械分类。

固定桶如下：

| 桶 | 典型路径 | 处理策略 |
|---|---|---|
| B1 Git/Agent 治理 | `.gitignore`, `AGENTS.md`, `docs/development/*PROTOCOL.md` | 可先收敛，属于基础设施桶 |
| B2 启动与文档入口 | `README.md`, `QUICKSTART.md`, `docs/README.md` | 单独提交，验证命令可轻量 |
| B3 方案高参需求重构运行时 | `intelligent_project_analyzer/services/demand_reconstruction*`, entry/context/output planner | 必须配套后端测试 |
| B4 前端会话与项目界面 | `frontend-nextjs/app`, `components`, `lib`, 前端测试 | 必须配套前端测试或 smoke |
| B5 治理后台/知识资产 | `admin_routes`, `knowledge_governance_store`, review queue tests | 单独验证 API 与后台测试 |
| B6 测试与 smoke 工具 | `tests/*`, `scripts/smoke_*` | 必须说明服务代码依赖，不单独混入无关桶 |
| B7 产品定义与资料库 | `sf/`, `docs/mechanism-reviews/` | 资料桶单独确认，不与代码混提交 |
| B8 本地/缓存/索引 | `.codegraph/`, `.pytest_cache`, `.next`, logs | 默认忽略或本地处理，不进入提交 |
| B9 待确认 | 来源不明、跨桶、删除、大文件、压缩包 | 暂不提交，列清单问用户 |

一个文件只能进入一个提交桶；如果一个文件确实被两个任务共同修改，必须在提交说明中明确它服务的主任务，并把另一个任务列为后续风险。

## 6. 决策树

### 6.1 是否可以继续当前任务

```text
目标文件无既有修改 -> 可以小范围修改。
目标文件已有修改且属于同一任务桶 -> 可以继续，但先读 diff。
目标文件已有修改但来源不明 -> 暂停，先列为 B9。
目标文件跨多个任务桶 -> 不继续叠加，先拆桶或建 worktree。
```

### 6.2 是否需要 checkpoint

必须 checkpoint 的情况：

1. G3/G4 状态下继续任何跨模块工作。
2. 目标文件已经有用户或历史任务改动。
3. 新增重要 `??` 文档、测试、schema、registry、activation pack、knowledge package。
4. 即将执行生成、格式化、批量替换、目录移动或删除。

不允许直接 checkpoint 全工作树。必须按桶暂存：

```powershell
git add <B1 文件1> <B1 文件2>
git commit -m "chore: checkpoint git governance protocol"
```

### 6.3 是否使用 worktree

使用 worktree 的条件：

1. 当前工作树 G3/G4，且新任务需要修改 B3/B4/B5 中的核心文件。
2. 当前分支承载历史现场，不能安全切换或提交。
3. 需要做大范围 refactor 或长测试矩阵。

推荐命令：

```powershell
git worktree add ../langgraph-design-<task> -b work/<task>
```

禁止为了创建 worktree 而先清理、reset 或 stash 当前现场。

## 7. 暂存与提交规则

### 7.1 暂存

只允许按桶暂存：

```powershell
git add .gitignore AGENTS.md docs/development/DIRTY_WORKTREE_GOVERNANCE_PROTOCOL.md
```

禁止：

```powershell
git add .
git add -A
```

除非用户明确要求并且已经完成全量审计。

### 7.2 提交

提交信息必须包含桶意图：

```text
chore: add dirty worktree governance protocol
docs: update quickstart startup notes
feat: harden demand reconstruction runtime
fix: repair review queue admin route
```

提交后必须能回答：

1. 属于哪个桶？
2. 跑了什么验证？
3. 回退这个提交会影响哪些功能？

## 8. 回退与清理

G3/G4 状态下的回退必须按路径或 hunk：

```powershell
git restore -p <file>
git restore -- <file>
```

只有确认文件完全属于当前任务，才允许整文件恢复。

未跟踪文件处理顺序：

1. 重要且应共享：纳入对应桶提交。
2. 重要但不入 Git：写入本地保留清单。
3. 可再生成：加入 `.gitignore`。
4. 来源不明：列为 B9，不能删除。

禁止未经确认执行：

```powershell
git clean -fd
git clean -fdx
git stash -u
git stash --all
git reset --hard
git checkout -- .
```

## 9. 智能化执行规则

Agent 在 G2-G4 工作树中必须自动执行以下策略：

1. 默认先跑窄范围状态，不先读全量 diff。
2. 发现目标文件已有改动，先判断它是否同桶。
3. 如果同桶，继续并报告“已有改动 + 本次改动”。
4. 如果不同桶或来源不明，停止写该文件，改为新文件方案或请求确认。
5. 任何新增正式文档、测试、schema、registry 都视为重要 `??`，不能当临时文件处理。
6. 对 `.codegraph/`、`.pytest_cache/`、`.next/`、logs、coverage 等生成物优先忽略或本地清理，不入提交。
7. 如果 Git 输出出现权限警告，先修权限或忽略规则，再判断工作树状态。
8. 对跨 B3/B4/B5 的改动，默认建议 worktree 或分支隔离。

## 10. 当前仓库建议收敛顺序

基于 2026-06-20 快照，建议按以下顺序收敛：

1. B1 Git/Agent 治理：`.gitignore`、`AGENTS.md`、`docs/development/*PROTOCOL.md`。
2. B2 启动与入口文档：`README.md`、`QUICKSTART.md`、`docs/README.md`。
3. B3/B6 需求重构后端与对应测试：服务、路由、smoke、unit/API tests。
4. B4 前端会话与项目界面：页面、组件、前端测试。
5. B5 治理后台/知识资产：review queue、governance store、admin API。
6. B7 机制评审与 `sf/` 资料：单独资料桶，不与代码提交混合。
7. B8 生成物与索引：确认 `.codegraph/` 是否只本地保留；缓存目录不入 Git。
8. B9 待确认：任何压缩包、大文件、删除、来源不明项。

## 11. 验证清单

每次执行脏工作树治理后，至少验证：

```powershell
# 1. 看目标桶状态
git status --short -- <bucket-paths>

# 2. 看目标桶 diff
git diff -- <bucket-paths>

# 3. 检查是否还有权限噪声
git status --short --untracked-files=no

# 4. 检查新增文档编码
$bytes = [System.IO.File]::ReadAllBytes('<path>')
($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)
```

验证通过的标准：

1. 目标桶文件清单符合本次任务。
2. diff 只包含本次意图。
3. 无 Git 权限噪声。
4. 新增/修改 Markdown 无 UTF-8 BOM。
5. 未跟踪重要文件已被归类，不再处于“未知重要性”状态。

## 12. 一句话规则

脏工作树下不追求一次清干净；先分桶，再 checkpoint，再小步提交。任何无法归桶的文件，都不能被提交、删除或回退。