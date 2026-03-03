# 🚀 快速启动指南

> 3分钟快速启动 Intelligent Project Analyzer

---

## 📋 前置要求

- **Python**: 3.10+ （推荐 3.13）
- **Node.js**: 18+
- **LLM API Key**: OpenAI/Anthropic/Google 任选其一

---

## ⚡ 快速启动（Windows）

### 选项 A：使用 Conda 环境（推荐，适合已有 Anaconda）

```cmd
# 1. 克隆项目
git clone https://github.com/dafei0755/ai.git
cd ai

# 2. 配置环境变量
copy .env.example .env
# 编辑 .env 填写 OPENAI_API_KEY

# 3. 安装依赖
pip install -r requirements.txt
cd frontend-nextjs && npm install && cd ..

# 4. 启动后端（开启新终端）
python scripts\run_server_production.py

# 5. 启动前端（再开启新终端）
cd frontend-nextjs
npm run dev -- -p 3001
```

✅ 访问 http://localhost:3001 开始使用！

### 选项 B：使用虚拟环境（标准 Python 开发方式）

```cmd
# 1-2. 同上（克隆和配置）

# 3. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 4. 安装依赖
pip install -r requirements.txt
cd frontend-nextjs && npm install && cd ..

# 5. 使用批处理脚本启动（开启两个终端）
start_backend_main.bat     # 终端1: 后端 8000
start_frontend_main.bat    # 终端2: 前端 3001
```

✅ 访问 http://localhost:3001 开始使用！

---

## 🔧 分步启动

### 1. 安装依赖

```bash
# 后端
pip install -r requirements.txt

# 前端
cd frontend-nextjs && npm install
```

### 2. 配置环境变量

```bash
copy .env.example .env
# 编辑 .env，必填: OPENAI_API_KEY=your_key
```

### 3. 启动服务

#### 方式一：直接启动（适合 Conda 用户）

```bash
# 终端1: 启动后端
python scripts\run_server_production.py

# 终端2: 启动前端
cd frontend-nextjs
npm run dev -- -p 3001
```

#### 方式二：批处理脚本（需要 .venv 虚拟环境）

```bash
# ⚠️ 前提：已创建 .venv 虚拟环境
# python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt

start_backend_main.bat     # 后端 8000
start_frontend_main.bat    # 前端 3001
```

#### 方式三：多环境并行（灵活启动）

```bash
# 开发环境（默认）
python scripts\start_service.py --env development --service all

# 测试环境（与开发环境并行，互不干扰）
start_test_env.bat          # 后端 8100, 前端 3101

# 或单独启动某个服务
python scripts\start_service.py --env test --service backend
python scripts\start_service.py --env test --service frontend
```

> 💡 **提示**: v8.1+ 支持多环境并行运行，开发环境和测试环境可同时运行互不干扰

> `D:\11-20\langgraph-design` 保持主线端口：后端 `8000`、前端 `3001`。
> 如果要和 `D:\11-20\langgraph-v8.0.0-runtime` 并行运行，也可以直接使用 `start_backend_main.bat` 和 `start_frontend_main.bat`。

### 3.1 多环境并行验证（v8.1+ 新功能）🆕

**场景**: 修改代码后，想在不影响开发环境的情况下验证变更

**操作流程**:

```bash
# 1. 开发环境继续运行在 8000/3001
# （不需要停止）

# 2. 启动测试环境验证变更
start_test_env.bat  # 使用独立端口 8100/3101

# 3. 访问测试环境
# 前端：http://localhost:3101
# API：http://localhost:8100/docs

# 4. 验证通过后，停止测试环境（Ctrl+C）
# 5. 合并代码到主分支
```

**端口分配规则**:

| 环境 | 后端端口 | 前端端口 | 用途 |
|------|---------|---------|------|
| **Development** | 8000 | 3001 | 日常开发 |
| **Test** | 8100 | 3101 | 代码验证 |
| **Staging** | 8200 | 3201 | 预发布测试 |
| **Production** | 8000 | 3001 | 生产部署（固定端口）|

**配置隔离**:
- 数据库: `data/dev/` vs `data/test/`
- 日志: `logs/server.log` vs `logs/test_server.log`
- Redis: DB 0 vs DB 1

**端口管理工具**:

```bash
# 检查端口占用
python scripts/utils/port_manager.py check 8100

# 查看环境端口冲突
python scripts/utils/port_manager.py conflicts --env test

# 释放端口（安全，只释放Python进程）
python scripts/utils/port_manager.py release 8100
```

**版本管理最佳实践**（Git分支 + 多环境验证）:

```bash
# 1️⃣ 创建功能分支（避免直接修改主分支）
git checkout -b feature/your-task-name

# 2️⃣ 在开发环境编码（8000/3001 继续运行）
# 编辑代码...

# 3️⃣ 本地提交变更
git add .
git commit -m "feat: 添加新功能"

# 4️⃣ 启动测试环境验证（独立端口，不影响开发环境）
start_test_env.bat
# 访问 http://localhost:3101 测试变更

# 5️⃣ 验证通过后合并到主分支
git checkout main
git merge feature/your-task-name

# 6️⃣ 清理测试环境
# Ctrl+C 停止测试服务
```

> 💡 **为什么要这样做？**
> - **分支隔离**: 避免在主分支上直接改动导致"不知道改了哪里，版本混淆"
> - **环境隔离**: 测试环境使用独立数据和端口，避免破坏开发环境正在运行的服务
> - **安全回退**: 如果测试失败，直接删除分支 `git branch -D feature/your-task-name`，主分支不受影响

**紧急回退场景**:

```bash
# 场景1: 分支上的改动有问题，想回到修改前状态
git checkout main  # 切回主分支，所有改动消失

# 场景2: 已经合并到主分支，发现问题
git log --oneline -5  # 查看最近5次提交
git revert <commit-id>  # 安全回退（保留历史）
# 或 git reset --hard HEAD~1  # 彻底删除最后一次提交（谨慎）

# 场景3: 想保留改动但暂时不提交
git stash  # 暂存当前改动
git stash pop  # 稍后恢复改动
```

**进阶：多分支并行开发**:

```bash
# 同时维护多个功能分支
git checkout -b feature/task-a      # 在开发环境开发 (8000/3001)
git checkout -b bugfix/issue-123    # 在测试环境验证 (8100/3101)

# 使用不同环境端口互不干扰
python scripts/start_service.py --env development --service all  # 分支A
python scripts/start_service.py --env test --service all          # 分支B
```

**版本记录规范**（清晰的历史追溯）:

```bash
# ✅ 标准 Commit Message 格式（约定式提交）
git commit -m "类型(范围): 简短描述

详细说明（可选）
- 修改原因
- 影响范围

关联issue: #123"

# 常用类型：
# feat:     新功能
# fix:      修复bug
# docs:     文档更新
# style:    代码格式（不影响功能）
# refactor: 重构（不改变功能）
# test:     测试相关
# chore:    构建/工具配置

# 示例：
git commit -m "feat(api): 添加项目雷达图生成接口"
git commit -m "fix(frontend): 修复问卷跳过逻辑错误 #456"
git commit -m "docs: 更新多环境配置指南"
```

**创建版本里程碑**（重要节点标记）:

```bash
# 完成重要功能后打标签
git tag -a v8.1.0 -m "发布多环境验证功能"
git push origin v8.1.0

# 查看所有版本标签
git tag -l

# 查看特定版本的详情
git show v8.1.0

# 切换到特定版本查看代码
git checkout v8.0.0  # 回到v8.0状态
git checkout main    # 返回最新版本
```

**版本号规范**（语义化版本 SemVer）:

```
格式: v主版本.次版本.修订号
- 主版本: 不兼容的API修改（如 v8 → v9）
- 次版本: 向下兼容的功能新增（如 v8.0 → v8.1）
- 修订号: 向下兼容的bug修复（如 v8.1.0 → v8.1.1）

示例：
v8.0.0 - 初始版本
v8.1.0 - 添加多环境支持（新功能）
v8.1.1 - 修复端口冲突检测bug（修复）
v9.0.0 - 重构API架构（不兼容变更）
```

**查看版本历史**（追溯修改记录）:

```bash
# 查看提交历史（图形化）
git log --oneline --graph --all --decorate

# 查看某个文件的修改历史
git log --oneline -- intelligent_project_analyzer/settings.py

# 比较两个版本的差异
git diff v8.0.0..v8.1.0

# 查看谁修改了哪行代码（代码考古）
git blame intelligent_project_analyzer/settings.py

# 搜索历史提交（找到添加某功能的提交）
git log --all --grep="多环境"
```

**自动维护 CHANGELOG**:

```bash
# 手动记录版本变更（推荐）
# 编辑 CHANGELOG.md，记录每个版本的改动

# 或使用自动化工具（需要规范的commit message）
```

**推荐自动化工具**:

| 工具 | 功能 | 安装 | 适用场景 |
|------|------|------|---------|
| **gitchangelog** | 生成CHANGELOG | `pip install gitchangelog` | Python项目 |
| **conventional-changelog** | 约定式提交日志 | `npm install -g conventional-changelog-cli` | Node.js项目 |
| **commitizen** | 交互式规范提交 | `npm install -g commitizen` | 规范commit message |
| **standard-version** | 自动版本号+日志 | `npm install -g standard-version` | 自动化发版 |
| **commitlint** | Commit检查 | `npm install -g @commitlint/cli` | CI/CD钩子 |
| **semantic-release** | 全自动发版 | `npm install -g semantic-release` | 完全自动化 |

**1. gitchangelog（Python推荐）**:

```bash
# 安装
pip install gitchangelog

# 生成完整日志
gitchangelog > CHANGELOG.md

# 只看最后一个版本
gitchangelog $(git describe --tags --abbrev=0)..HEAD

# 自定义配置（项目根目录创建 .gitchangelog.rc）
# 示例配置：
cat > .gitchangelog.rc << 'EOF'
# 忽略的提交类型
ignore_regexps = [r'@minor', r'!minor', r'WIP']

# 按类型分组
section_regexps = [
    ('新功能', [r'^feat', r'^feature']),
    ('Bug修复', [r'^fix', r'^bugfix']),
    ('性能优化', [r'^perf']),
    ('文档', [r'^docs']),
    ('其他', None),
]

# 输出格式
output_engine = mustache("markdown")
EOF

gitchangelog > CHANGELOG.md
```

**2. conventional-changelog（Node.js推荐）**:

```bash
# 安装
npm install -g conventional-changelog-cli

# 生成日志（保留旧内容）
conventional-changelog -p angular -i CHANGELOG.md -s

# 从零生成
conventional-changelog -p angular -i CHANGELOG.md -s -r 0

# 与package.json集成
npm pkg set scripts.changelog="conventional-changelog -p angular -i CHANGELOG.md -s"
npm run changelog
```

**3. commitizen（规范提交助手）**:

```bash
# 安装
npm install -g commitizen

# 初始化（项目根目录）
commitizen init cz-conventional-changelog --save-dev --save-exact

# 使用（替代 git commit）
git add .
git cz  # 交互式选择类型、填写描述

# 示例交互：
# ? Select the type of change: feat
# ? What is the scope: api
# ? Write a short description: 添加雷达图端点
# ? Provide a longer description: (optional)
# ? Are there any breaking changes?: No
# ? Does this change affect any open issues?: #123
```

**4. standard-version（自动版本号+标签）**:

```bash
# 安装
npm install -g standard-version

# 首次发版
standard-version --first-release

# 后续发版（自动判断版本号）
standard-version  # 根据commit自动选择 major/minor/patch

# 强制指定版本类型
standard-version --release-as major  # 8.1.0 → 9.0.0
standard-version --release-as minor  # 8.1.0 → 8.2.0
standard-version --release-as patch  # 8.1.0 → 8.1.1

# 预发布版本
standard-version --prerelease alpha  # 8.1.0 → 8.1.1-alpha.0

# 干运行（查看会发生什么）
standard-version --dry-run

# 与package.json集成
npm pkg set scripts.release="standard-version"
npm run release
```

**5. commitlint（提交检查）**:

```bash
# 安装
npm install -g @commitlint/cli @commitlint/config-conventional

# 配置（项目根目录创建 commitlint.config.js）
cat > commitlint.config.js << 'EOF'
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [2, 'always', [
      'feat', 'fix', 'docs', 'style', 'refactor', 
      'test', 'chore', 'perf', 'ci', 'build', 'revert'
    ]],
    'subject-max-length': [2, 'always', 100],
  }
};
EOF

# 检查最后一次提交
echo "feat: test" | commitlint

# Git钩子集成（需要husky）
npm install -g husky
npx husky install
npx husky add .husky/commit-msg 'npx --no -- commitlint --edit "$1"'
# 之后每次 git commit 都会自动检查
```

**6. semantic-release（全流程自动化）**:

```bash
# 安装
npm install -g semantic-release

# 配置（项目根目录创建 .releaserc.json）
cat > .releaserc.json << 'EOF'
{
  "branches": ["main"],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    "@semantic-release/changelog",
    "@semantic-release/npm",
    "@semantic-release/github",
    "@semantic-release/git"
  ]
}
EOF

# 运行（需要CI/CD环境变量：GH_TOKEN）
semantic-release

# 自动完成：
# 1. 分析commit判断版本号
# 2. 生成CHANGELOG
# 3. 创建Git标签
# 4. 发布到GitHub Releases
# 5. 发布npm包（如适用）
```

**快速选择建议**:

```bash
# 个人项目/简单场景 → gitchangelog
pip install gitchangelog
gitchangelog > CHANGELOG.md

# 团队协作/规范提交 → commitizen + commitlint
npm install -g commitizen @commitlint/cli
git cz  # 每次提交用这个

# 半自动发版 → standard-version
npm install -g standard-version
standard-version  # 自动更新版本号和CHANGELOG

# 完全自动化/大型项目 → semantic-release（CI/CD集成）
# 需要配置GitHub Actions/GitLab CI
```

**实战示例（Python项目推荐组合）**:

```bash
# 1. 安装工具
pip install gitchangelog
npm install -g commitizen cz-conventional-changelog

# 2. 配置commitizen
echo '{"path": "cz-conventional-changelog"}' > .czrc

# 3. 日常工作流
git checkout -b feature/new-radar
# 编辑代码...
git add .
git cz  # 交互式提交（而非 git commit）

# 4. 发版前生成日志
gitchangelog > CHANGELOG.md
git add CHANGELOG.md
git commit -m "chore: update changelog for v8.2.0"

# 5. 打标签发布
git tag -a v8.2.0 -m "Release v8.2.0"
git push origin main --tags
```

**实用查询命令**:

```bash
# 我在哪个分支？当前版本是什么？
git branch  # 查看所有分支，*号标记当前分支
git describe --tags  # 显示最近的标签

# 这次改动影响了哪些文件？
git status  # 查看工作区状态
git diff --stat  # 查看修改统计

# 最近3天的提交记录
git log --since="3 days ago" --oneline

# 找到引入bug的提交（二分查找）
git bisect start
git bisect bad  # 当前版本有bug
git bisect good v8.0.0  # v8.0.0版本正常
# Git会自动切换到中间版本，测试后标记 good/bad
# 最终定位到问题提交
```

> 💡 **最佳实践建议**:
> - 每次提交前用 `git diff` 检查改动，避免提交无关文件
> - 小步提交（每个功能点独立提交），方便回退
> - 重要节点打标签（如发版、重大功能完成）
> - 定期查看 `git log`，了解团队改动

> 📚 **详细指南**: 参见 [MULTI_ENV_GUIDE.md](docs/MULTI_ENV_GUIDE.md)



### 3.2 Smart Nodes Self-Skip 灰度开关（可选）

在 `.env` 中按阶段开启：

```env
# Phase A: 影子模式（只记录，不跳步）
ENABLE_SMART_NODE_SELF_SKIP=false
ENABLE_SMART_NODE_SELF_SKIP_SHADOW=true

# Phase B: 小流量实跳（开启自跳步）
# ENABLE_SMART_NODE_SELF_SKIP=true
# ENABLE_SMART_NODE_SELF_SKIP_SHADOW=false
```

观测建议（后端启动后执行）：

```bash
python scripts/analysis/analyze_smart_skip_logs.py --file logs/server.log --last-hours 24
```

可选：缩短窗口快速看最近波动（例如 6 小时）：

```bash
python scripts/analysis/analyze_smart_skip_logs.py --file logs/server.log --last-hours 6
```

脚本输出包括：
- 决策日志条数、Shadow 条数、Step2/Step3 跳过次数、粗略跳过率
- `flow` 分布、`goto` 分布、Top reason codes

建议阈值（首版）：
- Shadow 阶段：只看分布稳定性，不以跳过率做决策
- 实跳阶段：若粗略跳过率 > 35% 或 `strategy_light_flow` 占比异常抬升，优先回滚

### 4. 访问应用

- **前端**: http://localhost:3001
- **API 文档**: http://localhost:8000/docs

---

## 🎯 基础使用

1. 打开 http://localhost:3001
2. 输入设计项目需求（如：150平米现代简约住宅设计）
   
   💡 **输入质量提示**（提高分析准确度）：
   - ✅ 项目类型和面积（如：350㎡别墅、25㎡单间）
   - ✅ 用户身份和特殊需求（如：企业家、自闭症家庭、电竞选手）
   - ✅ 预算范围和时间约束（如：50万预算、3个月完成）
   - ✅ 设计偏好或参考案例（如：北欧风格、对标XX项目）
   
   详细输入可跳过问卷环节，直达深度分析（当前系统34%场景可实现）

3. 回答校准问卷（可跳过）
4. 输出意图确认（不可跳过，需确认后继续）
5. 确认需求分析（会展示需求分析师判断与后续路由步骤）
6. 查看专家协作报告

---

## ❓ 常见问题

### Q: 执行 .bat 文件时提示"找不到路径"？

**原因**: 批处理文件依赖 `.venv\Scripts\python.exe`，但您的环境中不存在。

**解决方案**（三选一）：

1. **直接使用 Python 命令**（推荐）
   ```cmd
   python scripts\run_server_production.py
   ```

2. **创建 .venv 虚拟环境**
   ```cmd
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   start_backend_main.bat
   ```

3. **修改批处理文件**
   
   编辑 [start_backend_main.bat](start_backend_main.bat)，将第6行改为：
   ```bat
   call python scripts\run_server_production.py
   ```

---

### Q: 端口被占用？

```bash
# Windows
# 仅释放后端端口（推荐，避免误杀其它任务）
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
   Select-Object -ExpandProperty OwningProcess -Unique |
   ForEach-Object {
      $p = Get-Process -Id $_ -ErrorAction SilentlyContinue
      if ($p -and ($p.ProcessName -in @('python', 'uvicorn'))) { taskkill /F /PID $_ }
   }

# 如需释放前端端口（默认 3001）
Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue |
   Select-Object -ExpandProperty OwningProcess -Unique |
   ForEach-Object { taskkill /F /PID $_ }

# 或修改端口
npm run dev -- -p 4000
```

### Q: Python 3.13 Windows 用户

⚠️ 必须使用 `scripts\run_server_production.py` 启动

详见 [Playwright修复文档](.github/historical_fixes/playwright_python313_windows_fix.md)

### Q: 切换 LLM 服务商

编辑 `.env` 文件：
```env
OPENAI_API_KEY=sk-xxx
# 或 ANTHROPIC_API_KEY / GOOGLE_API_KEY
```

### Q: 需求分析的Fallback模式是什么？

**背景**: 当前Windows环境下OpenAI API存在emoji编码问题，系统采用智能Fallback机制保障服务稳定性。

**性能表现** (v7.620优化版):
- ✅ **稳定性**: 100%成功率，零崩溃
- ✅ **智能分析**: 34%场景可直接进入深度分析（跳过问卷）
- ✅ **隐含推断**: 自动识别高净值用户、特殊需求场景

**优化建议**:
- 提供详细输入可提升分析质量（见上方"输入质量提示"）
- 长期方案：迁移到Claude API或Docker Linux环境

**详细报告**: 参见 [FALLBACK_OPTIMIZATION_REPORT_v7.620.md](FALLBACK_OPTIMIZATION_REPORT_v7.620.md)

---

## 📚 进阶文档

- 📖 [完整文档](docs/README.md) - 架构设计、API 文档
- 🔧 [开发规范](.github/DEVELOPMENT_RULES_CORE.md) - 修改代码前必读
- 🎯 [本体论管理控制台](ONTOLOGY_ADMIN_QUICKSTART.md) - 管理员后台使用指南 🆕
- 🐛 [问题反馈](https://github.com/dafei0755/ai/issues)
- 💬 [讨论区](https://github.com/dafei0755/ai/discussions)

---

**祝你使用愉快！** 🎉
