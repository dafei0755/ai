# Agent 写入与运行卡顿治理协议

> 版本：v1.0
> 固化日期：2026-06-20
> 适用范围：本仓库内 Codex/Agent 执行任务时的文件写入、运行排查、长命令输出与异常卡顿处理。

## 1. 本次排查结论

最近任务卡顿不是单一业务代码问题，而是多个执行层因素叠加：

1. 写入工具路径不稳定：历史上大 `apply_patch` 卡住；本次一个很小的 `apply_patch` 也卡住约 259 秒并被中断，且未产生半写入。
2. 工作树过脏：当前存在大量 `M` 与 `??` 文件，Agent 每次写入前都需要额外判断归属，不能直接创建全量 checkpoint，也不能安全地 `git add .`。
3. Git 权限噪声：`git status --short` 持续报 `C:\Users\SF/.config/git/ignore` 读取权限问题。
4. 目录权限异常：`frontend-nextjs/.pytest_cache/` 无法被 Git 打开，`Get-Acl` 也返回未授权。
5. Windows 编码风险：历史上 `Set-Content -Encoding utf8` 引入 BOM 与尾部空行噪声，中文文档尤其容易出现非内容 diff。
6. 进程现场复杂：当前存在多个 `node`、`node_repl`、`powershell` 进程，任务运行慢时必须先区分“服务仍在跑”“工具卡住”“命令输出过大”。
7. 工具环境曾失效：历史记录中出现过 `codex-windows-sandbox-setup.exe` helper 启动失败，表现为所有读命令都失败；这类问题应归为执行环境故障，不应误判为仓库故障。
8. 输出规模过大：宽泛 `rg`、全量 diff、全量 status 在当前工作树下容易产生巨大输出，增加等待和误判概率。
9. CodeGraph 不是当前瓶颈：本次 `codegraph status .` 显示索引 up to date，适合继续作为结构查询入口。

## 2. 根因矩阵与根治动作

| 编号 | 问题 | 当前证据 | 根因判断 | 根治动作 | 验证方式 |
|---|---|---|---|---|---|
| R1 | `apply_patch` 卡住 | 历史大 patch 卡住；本次小 patch 也卡住约 259 秒 | 当前会话的 patch 写入通道不可靠，不能作为唯一写入路径 | 任何 patch 超过 60 秒无结果，立即停止；改为更小 hunk 或受控 BOM-free 原子写入 | 写后 `Get-Content` 精确读回；`git diff -- <path>` |
| R2 | 脏工作树拖慢判断 | `git status --short` 大量 `M`/`??` | 多任务混杂，回退边界不清 | 大改前先做状态审计；只按任务边界 checkpoint；禁止 `git add .` | `git status --short -- <paths>` |
| R3 | Git ignore 权限警告 | `unable to access C:\Users\SF/.config/git/ignore` | 用户级 ignore 路径不可读或 Git 在 sandbox 中映射异常 | 修复该文件 ACL，或设置仓库级 `core.excludesfile` 指向可读文件 | `git status --short` 不再出现该警告 |
| R4 | `.pytest_cache` 权限异常 | Git 无法打开目录；`Get-Acl` 未授权 | 缓存目录 ACL 损坏或由异常上下文创建 | 将该目录作为缓存处理：用户确认后删除重建，或修复 ACL；不要纳入版本控制 | `Get-Acl frontend-nextjs/.pytest_cache` 成功；`git status` 无该警告 |
| R5 | Windows 编码/BOM 噪声 | 历史 `Set-Content` 引入 BOM/空行噪声 | Windows PowerShell 5 的 UTF-8 默认行为不稳定 | 中文/Markdown 大段写入使用 `System.Text.UTF8Encoding($false)`；写后检查 BOM 与尾部空行 | 字节检查前三字节不是 `EF BB BF`；diff 只含预期内容 |
| R6 | 进程残留干扰运行判断 | 多个 `node/node_repl/powershell` 进程 | 任务、前端、浏览器验证、REPL 会并存 | 卡顿时先列进程与端口；只清理确认属于本任务的进程 | `Get-Process`、`netstat -ano`、项目脚本 `--status` |
| R7 | sandbox/helper 环境失效 | 历史 helper missing 导致读命令全失败 | Codex 执行环境问题，不是项目报错 | 先修执行环境或切换可用执行路径，再做仓库诊断 | 简单 `Get-Location`、`git status --short` 能成功 |
| R8 | 输出过大导致等待 | 宽泛 `rg` 输出曾超过万 token | 命令范围过宽，诊断粒度不够 | 默认限制路径和 `max_output_tokens`；先 `rg -n pattern <narrow-path>` | 输出可读、可定位、无需反复中断 |
| R9 | CodeGraph transport/索引漂移 | 历史 install 后 `Transport closed`；本次 status OK | install/refresh 会重置 MCP transport | 安装或刷新后重启会话；写后等索引同步或查 live 文件 | `codegraph status .` 为 up to date |

## 3. 以后任务的强制执行顺序

### 3.1 卡顿排查顺序

1. 确认命令是否仍在运行，避免误判：查看当前 shell/session 状态。
2. 查最小现场：`git status --short -- <target-path>`，不要先跑全仓库大输出。
3. 查进程与端口：只看相关 `node/python/powershell/git/codegraph` 进程。
4. 查权限：如果 Git 报 `Permission denied`，优先解决权限噪声。
5. 查 CodeGraph：结构问题用 `codegraph status .` 和 CodeGraph；字面值用 live 文件。
6. 查最近改动：只读目标文件 diff，不读全仓库 diff。

### 3.2 写文件顺序

1. 小改优先使用小 hunk patch。
2. patch 超过 60 秒无响应，立即换方法，不继续等待。
3. 大文档新增或整段机械插入，使用 BOM-free 原子写入：先写临时文件，再同目录替换。
4. 每次只写一个文件或一个小段。
5. 写后立刻读回目标段落。
6. 写后只看目标路径 diff。
7. 如果目标文件本来是脏的，必须在最终说明中区分“已有改动”和“本次改动”。

### 3.3 命令输出控制

1. 不在脏工作树下先跑全量 `git diff`。
2. 不用宽泛 `rg` 扫整个仓库，除非先限定模式和输出预算。
3. 长命令必须有明确验证目的；没有目的的全量扫描视为卡顿风险。
4. 对于中文路径，命令前设置 UTF-8 代码页或使用 API 读写。

## 4. 需要用户或系统层处理的项目

以下问题无法只靠 Agent 文档彻底根治，需要在机器或仓库配置层修复：

1. 修复 `C:\Users\SF\.config\git\ignore` 的读取权限，或设置仓库级可读 excludesfile。
2. 修复或删除重建 `frontend-nextjs/.pytest_cache/` 的异常 ACL。
3. 如果再次出现 `codex-windows-sandbox-setup.exe` helper failure，先修 Codex/VS Code 执行环境，不继续做仓库诊断。
4. 当前工作树需要一次状态审计，给大量 `M` 与 `??` 文件分组，否则后续所有大改都会继续受回退边界不清影响。

## 5. 可直接使用的验证命令

```powershell
# 最小 Git 现场
git status --short -- <path>

# 检查 CodeGraph 是否健康
codegraph status .

# 检查权限异常目录
Get-Acl frontend-nextjs/.pytest_cache

# 检查 Git 用户 ignore 来源
git config --show-origin --get core.excludesfile

# 检查 BOM，返回 True 表示有 BOM
$bytes = [System.IO.File]::ReadAllBytes('<path>')
($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)

# 只看目标文件 diff
git diff -- <path>
```

## 6. 一句话规则

卡顿时先缩小现场，写入时先缩小补丁；任何单一路径超过 60 秒无响应，就换成更小、更可验证的路径。