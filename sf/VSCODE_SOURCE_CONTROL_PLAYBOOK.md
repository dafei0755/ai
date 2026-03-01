# VS Code 源代码管理操作手册
# langgraph-design · 发布运维导向版

> **适用范围**：`langgraph-design` 主仓库 · Windows + VS Code · `main` 分支 · 远程 `origin` = `github.com/dafei0755/ai.git`
> **版本**：v1.0 · 2026-02-23
> **核心原则**：GUI 优先，高风险操作默认禁用，双仓误操作零容忍。

---

## 目录

1. [安全基线与适用声明](#1-安全基线与适用声明)
2. [界面认知：三层对象 + Graph](#2-界面认知三层对象--graph)
3. [仓库现状诊断与一次性清理](#3-仓库现状诊断与一次性清理)
4. [日常提交流程（GUI）](#4-日常提交流程gui)
5. [发布运维流程（GUI）](#5-发布运维流程gui)
6. [回退与恢复（GUI 优先）](#6-回退与恢复gui-优先)
7. [双仓误操作防护](#7-双仓误操作防护)
8. [常见故障处理矩阵](#8-常见故障处理矩阵)
9. [应急附录（默认禁用）](#9-应急附录默认禁用)
10. [发布前 3 分钟检查表](#10-发布前-3-分钟检查表)

---

## 1. 安全基线与适用声明

### 1.1 当前仓库状态（截至 2026-02-23）

| 项目 | 状态 | 风险等级 |
|------|------|--------|
| 活跃仓库 | `langgraph-design`（`main` 分支） | — |
| 远程 origin | `github.com/dafei0755/ai.git` | — |
| 本地超前提交 | 5↑（尚未推送） | ⚠️ 中 |
| 未提交变更数 | ~887 个（含子目录误追踪） | 🔴 高 |
| 子目录 `restored_19912` | 独立 git 仓库，未被主仓忽略 | 🔴 高 |

### 1.2 三条安全红线

> 违反任一条须立即停止操作，进入 [§9 应急附录](#9-应急附录默认禁用)。

1. **提交前确认左侧仓库名**：必须是 `langgraph-design`，不得误选 `langgraph-design_restored_19912`。
2. **不得一次性全量暂存 887 个变更**：禁止点击 Changes 旁的全局 `+` 按钮，必须按模块分批。
3. **不得在未理解的状态下执行推送**：Graph 视图须可解释当前 ahead/behind 后，方可 Push。

### 1.3 操作停止条件

出现以下任意情况，立即停止并备份工作区：

- 误将 `restored_19912` 内的文件暂存到主仓
- 冲突文件超过 5 个且无法逐一理解
- Stash 列表超过 10 条且已无法区分内容
- `git log` 显示历史线非线性且无法解释

---

## 2. 界面认知：三层对象 + Graph

### 2.1 Source Control 面板（Ctrl+Shift+G）

```
Source Control 面板
├── [仓库选择器]  ← 每次操作前核对仓库名
├── Staged Changes（已暂存）
│   ├── 文件 A  [M] ← 点击查看 diff，确认后才能提交
│   └── 文件 B  [A]
├── Changes（未暂存）
│   ├── 文件 C  [M]  ← 单击打开 diff；点 + 暂存单个文件
│   └── 文件夹/  ← 点 + 按目录批量暂存
└── [提交消息输入框]  ← 粘贴提交模板后填写
```

**图标含义**：`M` = 修改、`A` = 新增、`D` = 删除、`U` = 未追踪、`C` = 冲突

### 2.2 Graph 视图（内置 / Git Graph 插件）

- **打开方式**：Source Control 面板右上角 `...` → `View Git Graph`（需安装 Git Graph 插件）；或内置时点击底部状态栏分支名。
- **关键信息**：分支头位置、`origin/main` 标签位置、ahead（↑）/ behind（↓）数字。
- **发布前必做**：确认本地 `main` 与 `origin/main` 的关系线可解释。

### 2.3 仓库选择器规则

VS Code 左侧 Source Control 面板顶部会显示当前活跃仓库名。当工作区存在多个 git 仓库时，点击仓库名可切换。

**执行口诀**：提交前念一遍——"我在哪个仓库？我要提交到哪里？"

---

## 3. 仓库现状诊断与一次性清理

> 本章是**一次性操作**，完成后删除此章节或标注为"已完成"。887 个变更大部分是噪音，必须先清理才能恢复正常工作流。

### 3.1 根因诊断

| 噪音来源 | 文件数量估计 | 原因 |
|---------|------------|------|
| `langgraph-design_restored_19912/` 未被忽略 | ~400+ | 独立仓库目录未加入 `.gitignore` |
| `backup/`、`logs/`、`data/` 目录 | ~100+ | `.gitignore` 规则配置前已被追踪 |
| `frontend-nextjs/.next/`、`.swc/` | ~100+ | 构建产物未被忽略 |
| 根目录 `_*.py`、`_*.txt` 临时文件 | ~30 | 调试脚本未被忽略 |
| 真正的业务变更 | ~200 | 需要保留并分批提交 |

### 3.2 第一步：更新 `.gitignore`

在 VS Code 中打开 `.gitignore`，在文件**末尾追加**以下内容：

```gitignore
# ── 一次性补充（2026-02-23）──────────────────────────────

# 独立子仓库备份目录（只读参考，不纳入主仓追踪）
langgraph-design_restored_19912/

# 前端构建产物
frontend-nextjs/.next/
frontend-nextjs/.benchmarks/
frontend-nextjs/.swc/

# 后端基准测试
intelligent_project_analyzer/.benchmarks/
tests/integration/.benchmarks/

# 数据库文件
*.db

# 根目录调试临时脚本（_*.py 仅匹配根目录）
/_*.py
/_*.txt

# 大型运行时数据目录（如已追踪需配合 git rm --cached）
/backup/
/logs/
/data/
/reports/
/htmlcov/
```

保存后，Source Control 面板中的 `.gitignore` 会立即出现在 Changes 中——暂存并提交它（见下方流程）。

### 3.3 第二步：从索引中移除已追踪的噪音（需终端一次性执行）

> 此步骤仅执行一次。只移除 git 追踪记录，**不删除本地文件**。

在 VS Code 集成终端（`Ctrl+``）执行：

```powershell
# 移除子仓库目录的追踪
git rm -r --cached langgraph-design_restored_19912/ --quiet

# 移除构建产物追踪
git rm -r --cached frontend-nextjs/.next/ --quiet 2>$null
git rm -r --cached frontend-nextjs/.swc/ --quiet 2>$null

# 移除运行时目录追踪（如已被追踪）
git rm -r --cached backup/ logs/ data/ reports/ htmlcov/ --quiet 2>$null

# 确认剩余变更数量（应大幅减少）
git status --short | Measure-Object -Line
```

### 3.4 第三步：分批提交真正的业务变更

清理后剩余的业务变更按以下 5 组在 GUI 中分批提交：

| 提交批次 | 暂存目录/文件 | 提交消息示例 |
|---------|------------|------------|
| **Batch 1** 配置与环境 | `config/`、`.env.example`、`ONTOLOGY_ADMIN_QUICKSTART.md` | `chore: 补充系统配置与环境模板` |
| **Batch 2** 后端源码 | `intelligent_project_analyzer/services/`、`api/`、`agents/` | `feat: 添加后端服务层与 API 路由` |
| **Batch 3** 前端源码 | `frontend-nextjs/app/`、`components/`、`hooks/` | `feat: 添加前端页面与组件` |
| **Batch 4** 测试与脚本 | `tests/`、`scripts/` | `test: 添加 v8.0 测试套件与辅助脚本` |
| **Batch 5** 文档 | `docs/`、`sf/`、`*.md` | `docs: 补充项目文档与操作手册` |

**GUI 操作步骤**（每批次重复）：

1. Source Control 面板 → 确认仓库名为 `langgraph-design`
2. 在 Changes 中找到目标目录，点击目录名旁的 `+` 暂存整个目录
3. 逐一单击文件查看 diff，确认无敏感信息（API Key、密码）
4. 填写提交消息 → 点击 `✓ Commit`

---

## 4. 日常提交流程（GUI）

### 流程 A：单文件热修（小改动）

```
1. 打开修改的文件，Ctrl+S 保存
2. Source Control（Ctrl+Shift+G）→ 确认仓库名
3. 在 Changes 中点击文件名 → 查看 diff 确认内容
4. 点击文件旁的 [+] → 文件移到 Staged Changes
5. 提交消息框输入：fix: 修复 XX 问题
6. Ctrl+Enter 提交
```

### 流程 B：大改动分批提交

> 禁止一次性点击 Changes 旁的全局 `+` 提交所有修改。

```
1. 按功能模块列出本次修改的文件范围（脑中或纸上）
2. 先暂存第一个模块的文件（目录级 + 或逐文件 +）
3. 写提交消息，描述"这批提交做了什么"
4. Ctrl+Enter 提交
5. 重复步骤 2-4，完成所有模块
```

**提交消息规范**（Conventional Commits）：

```
feat:     新功能
fix:      缺陷修复
docs:     仅文档变更
refactor: 重构（无功能变化）
test:     测试相关
chore:    构建/配置/依赖
perf:     性能优化
```

示例：`feat: 添加项目特定维度生成器 v8.0`

### 流程 C：临时搁置（Stash）

> 适用场景：当前有未完成改动，需紧急切换任务。

**创建 Stash**：
1. Source Control `...` 菜单 → `Stash` → `Stash (Include Untracked)`
2. 命名格式：`YYYYMMDD-功能描述`（例：`20260223-雷达图重构中`）

**恢复 Stash**：
1. Source Control `...` 菜单 → `Stash` → `Pop Latest Stash` 或 `Apply Stash...`
2. 选择对应日期命名的 Stash
3. 若出现冲突，见 [§6.3 Stash 恢复冲突处理](#63-stash-恢复冲突处理)

**Stash 管控规则**：
- Stash 列表不超过 **5 条**；超过时必须先处理旧 Stash
- 超过 48 小时未恢复的 Stash，转为正式提交或放弃

### 流程 D：误操作撤销

| 场景 | GUI 操作 | 说明 |
|------|---------|------|
| 误暂存文件 | Staged Changes → 文件旁 `-` | 退回到 Changes，不丢失代码 |
| 误修改未暂存文件 | Changes → 文件右键 `Discard Changes` | ⚠️ 不可恢复，谨慎操作 |
| 撤销上一次提交（未推送） | Source Control `...` → `Undo Last Commit` | 提交退回工作区，代码保留 |
| 撤销上一次提交（已推送） | **禁止 GUI 操作** → 进入 [§9 应急附录](#9-应急附录默认禁用) | — |

---

## 5. 发布运维流程（GUI）

### 5.1 发布前工作区清洁确认

执行发布前，依次确认：

- [ ] Source Control 面板 Changes 为空（或仅有已知的"允许带入"文件）
- [ ] 无 Stash 堆积（列表清空或已命名可识别）
- [ ] Graph 视图中 `main` 分支头与 `origin/main` 关系可解释

### 5.2 同步远端（Pull with Rebase）

> **策略**：优先 Rebase，保持线性历史，减少无意义的 merge commit。

```
1. 确认工作区无未提交变更（或已 Stash）
2. Source Control `...` → `Pull` → 选择 `Pull (Rebase)`
   （首次若无此选项：`...` → `Pull From` → `origin main`，勾选 Rebase）
3. Graph 视图确认本地 main 已包含远端最新提交
4. 若出现冲突：
   a. 编辑器会高亮冲突块（<<<<<<< / ======= / >>>>>>>）
   b. 逐文件点击冲突标记，选择 Accept Current / Accept Incoming / 手动合并
   c. 解决所有冲突后，Source Control `...` → `Continue Rebase`
```

### 5.3 推送（Push）

> 主流程仅允许正常 Push。禁止 Force Push 进入此流程。

```
1. Pull (Rebase) 完成后，Graph 确认 ahead/behind 状态合理
2. Source Control `...` → `Push`
3. 推送完成后 Graph 刷新，确认 origin/main 标签已与本地 main 对齐
```

### 5.4 发布标记（Tag）

VS Code 内置 GUI 对 Tag 支持有限，建议安装 **Git Graph** 插件。

**Git Graph 中创建 Tag**：
1. 在 Graph 视图中右键目标提交
2. 选择 `Create Tag`
3. 命名格式：`v{major}.{minor}` 或 `release/YYYYMMDD`
4. 推送 Tag：`...` → `Push Tags`

> 若插件不可用，记录"需终端补充 tag 推送"，不在本流程展开。

---

## 6. 回退与恢复（GUI 优先）

### 6.1 撤销最近提交（未推送）

**场景**：刚提交，发现内容有误，需要修改后重新提交。

```
Source Control `...` → `Undo Last Commit`
```

代码保留在工作区，提交记录消失。修改后重新提交即可。

### 6.2 基于 Graph 的回退点选择

**场景**：需要回退到某个历史稳定点（已推送的提交）。

```
1. 打开 Git Graph 视图
2. 找到目标"已知稳定"提交（通常是有 release tag 或明确功能说明的）
3. 右键该提交 → `Revert...`
   ├── Revert（新增一个"撤销提交"，历史保留）← 推荐，安全
   └── Reset（移动分支头，有数据丢失风险）← 仅在未推送时使用
4. Revert 完成后推送
```

> ⚠️ Reset 到已推送提交 → 必须进入 [§9 应急附录](#9-应急附录默认禁用)，不走此流程。

### 6.3 Stash 恢复冲突处理

```
1. Pop Stash 出现冲突时，不要恐慌
2. 先将冲突文件复制一份到桌面备份（文件管理器操作）
3. 在编辑器中逐一处理冲突块（Accept 选择合适一侧）
4. 处理完所有冲突文件后，暂存 → 提交（可选）
5. 删除桌面备份
```

冲突无法收敛时：`Source Control` `...` → `Stash` → `Drop Stash`（丢弃该 stash，从桌面备份手动恢复）。

---

## 7. 双仓误操作防护

### 7.1 当前双仓风险

工作区同时存在两个 git 仓库：

| 仓库 | 角色 | 操作权限 |
|------|------|--------|
| `langgraph-design` | **主仓，唯一操作目标** | 读写 |
| `langgraph-design_restored_19912` | 只读历史备份 | ❌ 禁止提交/推送 |

### 7.2 防护固定动作（每次提交前）

```
✅ 步骤 1：看 Source Control 面板顶部仓库选择器 → 确认显示 "langgraph-design"
✅ 步骤 2：看 Changes 列表中的文件路径 → 确认无 "restored_19912" 路径前缀
✅ 步骤 3：提交完成后，看 Graph 视图 → 确认提交出现在正确仓库的 main 分支
✅ 步骤 4：Push 前 → 确认远端为 "origin" = github.com/dafei0755/ai.git
```

### 7.3 误在 `restored_19912` 提交后的补救

> 场景：不小心在 restored 仓库提交了真正的业务代码。

```
1. 打开 restored_19912 的 Git Graph → 记下误提交的文件列表和内容
2. 将这些文件手动复制到主仓对应路径（文件管理器操作）
3. 切换回主仓 → 按正常流程暂存、提交
4. 返回 restored_19912 → Git Graph → 右键误提交 → Reset to Here (Mixed)
   （仅在 restored 仓库无远程推送的前提下）
5. 验证：主仓已有正确提交，restored 仓库历史已还原
```

### 7.4 长期管控措施

完成 [§3.2 更新 `.gitignore`](#32-第一步更新-gitignore) 后，`restored_19912` 从主仓索引中移除，从根本上消除双仓混淆风险。

---

## 8. 常见故障处理矩阵

| 症状 | 可能原因 | GUI 处理步骤 | 升级条件 |
|------|---------|------------|--------|
| Source Control 面板看不到变更 | 文件被 `.gitignore` 忽略；或工作区未刷新 | 右键文件 → `Open in Source Control`；或重启 VS Code | 刷新后仍不显示 → 检查 `.gitignore` |
| 提交按钮灰色（无法点击） | 未写提交消息；或 Staged Changes 为空 | 检查提交消息框是否为空；确认有文件在 Staged | — |
| 冲突循环（解决后再次出现） | Rebase 进行中未 Continue；或冲突文件未正确保存 | `...` → `Abort Rebase` 退出；重新 Pull | 中断后状态混乱 → §9 应急 |
| Stash 过多难定位 | Stash 未命名、积累过久 | `...` → `Stash` → 逐条 `Show Stash`查看内容 | 超过 10 条 → 优先清理旧 Stash |
| ahead/behind 数字异常（如 ahead 50+） | 长期未推送；或分支存在分叉 | Graph 视图确认分支线；正常 Push（非 force） | 出现分叉线 → §9 应急 |
| 887 个变更无法处理 | `restored_19912` 未被 `.gitignore` 忽略 | 执行 §3 清理流程 | — |
| 推送失败（rejected） | 远端有本地没有的提交（分叉） | 先 Pull (Rebase)，再 Push | Rebase 冲突复杂 → §9 应急 |
| .env 文件出现在 Changes | `.gitignore` 未包含 `.env`；或已被追踪 | 立即 Discard；补充 `.gitignore`；检查是否曾推送过 | 曾推送过 → 立即进 §9 清理敏感历史 |

---

## 9. 应急附录（默认禁用）

> ⛔ **以下操作默认禁止执行。仅在满足全部前置条件后方可进行。**
> 执行前须完成：① 通知所有协作者停止操作；② 本地完整备份；③ 明确回滚方案；④ 确定操作窗口期。

### A-1：强制推送（Force Push）

**允许场景**：个人 feature 分支（非 main/20260104）发布前整理提交历史。

**禁止场景**：`main` 分支、任何已有他人拉取的分支。

**前置条件核查**：
- [ ] 目标分支为个人 feature 分支
- [ ] 已确认无其他人正在使用该分支
- [ ] 本地已备份当前状态（创建临时 Stash 或 Tag）

**后验证**：远端分支历史与预期一致；协作者重新 fetch 并 reset。

---

### A-2：历史重写（Interactive Rebase）

**允许场景**：本地未推送的提交需要合并/拆分/修改消息。

**操作路径**（Git Graph 插件）：
1. Graph 视图 → 右键基础提交 → `Rebase current branch on this commit (Interactive)`
2. 按需 squash / reword / drop
3. 完成后核对 Graph，再 Push

---

### A-3：清理敏感信息历史

**触发条件**：`.env`、API Key、密码已被推送到远端。

**必须立即执行的前置操作**：
1. 在 GitHub 撤销/重新生成泄露的密钥
2. 通知团队停止使用当前 clone
3. 准备新的 clone 作为推送后的干净环境

**操作工具**：`git filter-repo`（需终端，不在 GUI 覆盖范围）。

**后验证**：
- 远端历史不再包含敏感信息
- 所有协作者重新 clone
- 二次扫描：搜索 `secrets-scan.yml` CI 结果

---

## 10. 发布前 3 分钟检查表

> **打印版** — 每次发布前逐条确认，全部打勾方可 Push。

```
发布前检查 · langgraph-design · 日期：___________

仓库与分支
  [ ] Source Control 仓库选中：langgraph-design（非 restored_19912）
  [ ] 当前分支：main（或已明确的 feature 分支）
  [ ] Graph 中 origin/main 与本地 main 关系可解释

工作区状态
  [ ] Changes 为空（或仅有已知的"允许带入"项）
  [ ] Staged Changes 为空（无意外暂存的文件）
  [ ] Stash 列表清空或每条有可识别名称

提交质量
  [ ] 最近 5 条提交消息有意义（非"fix"、"update"等模糊描述）
  [ ] 无包含 .env、密码、API Key 的提交
  [ ] 提交粒度合理（每次提交解决一个明确问题）

同步状态
  [ ] 已执行 Pull (Rebase) 获取远端最新
  [ ] ahead 数字 ≤ 本次发布预期的提交数
  [ ] behind 数字 = 0（无未拉取的远端提交）

回退保障
  [ ] 存在一个可识别的"安全回退点"（Tag 或已知稳定提交）
  [ ] 知道如何用 Graph Revert 回到该点

全部 ✅ → 执行 Push
有任一 ❌ → 先处理问题，重新检查
```

---

*本手册基于仓库实际状态（2026-02-23）编制。仓库清理完成后，§3 可标注为"已完成"。*
*如发现操作步骤与实际 VS Code 版本 GUI 有出入，以实际界面为准，操作逻辑不变。*
