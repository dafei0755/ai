# 📝 文档维护规范

> Intelligent Project Analyzer 文档管理规则

**版本**: v1.0
**最后更新**: 2026-01-02

---

## 🎯 核心原则

### 1. 集中管理，分类清晰

- **所有文档必须归类到对应目录**，避免根目录堆积
- **使用索引导航**，而非在根目录创建大量 .md 文件
- **定期归档**，保持文档结构清爽

### 2. 命名规范统一

- **功能文档**: `{FEATURE}_{TOPIC}.md`（全大写，下划线分隔）
- **版本文档**: `v{X.Y}_RELEASE_NOTES.md`（小写v + 版本号）
- **归档文档**: `archive/{category}/{feature}_fix_{YYYYMMDD}.md`

### 3. 文档更新同步

- **修改配置/核心逻辑时必须同步更新文档**
- **新功能必须添加到 CHANGELOG.md**
- **修复记录必须归档到 `docs/archive/bugfixes/`**

---

## 📂 文档目录结构

```
langgraph-design/
├── README.md                       # 项目概览（精简至200-300行）
├── QUICKSTART.md                   # 快速启动（5分钟）
├── CONTRIBUTING.md                 # 贡献指南
├── CHANGELOG.md                    # 版本历史
├── EMERGENCY_RECOVERY.md           # 紧急恢复
├── BACKUP_GUIDE.md                 # 备份指南
├── README_TESTING.md               # 测试概览
├── NEXT_STEPS.md                   # 下一步计划
├── LICENSE                         # 许可证
│
├── docs/                          # 文档中心
│   ├── README.md                  # 文档导航索引
│   ├── getting-started/           # 入门指南
│   │   ├── INSTALLATION.md
│   │   ├── CONFIGURATION.md
│   │   └── FAQ.md
│   ├── architecture/              # 架构设计
│   │   ├── AGENT_ARCHITECTURE.md
│   │   ├── PROJECT_STRUCTURE.md
│   │   └── WORKFLOW_DESIGN.md
│   ├── deployment/                # 部署运维
│   │   ├── DEPLOYMENT.md
│   │   ├── SECURITY_SETUP_GUIDE.md
│   │   └── maintenance/
│   ├── features/                  # 功能文档
│   │   ├── wordpress-sso/
│   │   ├── questionnaire/
│   │   ├── search/
│   │   └── multimodal/
│   ├── development/               # 开发指南
│   │   ├── API.md
│   │   ├── TESTING_GUIDE.md
│   │   └── testing/
│   ├── releases/                  # 版本发布
│   │   ├── v7.115/
│   │   └── v7.113/
│   └── archive/                   # 历史归档
│       ├── phases/                # 阶段报告
│       ├── bugfixes/              # 临时修复
│       │   ├── questionnaire/
│       │   ├── search/
│       │   ├── frontend/
│       │   └── backend/
│       └── versions/              # 历史版本
│
└── .github/                       # 开发规范
    ├── DEVELOPMENT_RULES_CORE.md  # 核心规范（200行）
    ├── DEVELOPMENT_RULES.md       # 完整规范
    ├── PRE_CHANGE_CHECKLIST.md    # 变更检查清单
    ├── DOCUMENTATION_RULES.md     # 文档维护规范（本文件）
    └── historical_fixes/          # 精选历史修复（5-10个）
```

---

## 📝 新增文档流程

### 1. 确定文档类型和位置

| 文档类型 | 存放位置 | 文件名示例 |
|---------|---------|-----------|
| **入门教程** | `docs/getting-started/` | `INSTALLATION.md` |
| **架构设计** | `docs/architecture/` | `AGENT_ARCHITECTURE.md` |
| **部署运维** | `docs/deployment/` | `DEPLOYMENT.md` |
| **功能说明** | `docs/features/{feature}/` | `features/wordpress-sso/README.md` |
| **开发指南** | `docs/development/` | `API.md`, `TESTING_GUIDE.md` |
| **版本发布** | `docs/releases/vX.Y/` | `v7.115/RELEASE_NOTES.md` |
| **修复记录** | `docs/archive/bugfixes/{category}/` | `bugfixes/questionnaire/fix_20260102.md` |
| **开发规范** | `.github/` | `DEVELOPMENT_RULES_CORE.md` |
| **核心文档** | 根目录 | `README.md`, `CHANGELOG.md` |

### 2. 创建文档模板

#### 功能文档模板

```markdown
# 功能名称

> 简短描述

**版本**: vX.Y
**最后更新**: YYYY-MM-DD

---

## 概述

功能概述...

## 使用方法

使用说明...

## 配置

配置项说明...

## 常见问题

Q&A...

## 相关文档

- [相关文档1](link)
- [相关文档2](link)
```

#### 修复记录模板

```markdown
# Bug修复: 问题名称

**版本**: vX.Y
**日期**: YYYY-MM-DD
**分类**: questionnaire | search | frontend | backend

---

## 问题描述

描述问题现象...

## 根因分析

分析问题原因...

## 解决方案

描述修复方案...

## 测试验证

测试结果...

## 相关代码

- 文件1: [link](link)
- 文件2: [link](link)
```

### 3. 更新文档索引

新增文档后必须更新：

1. **`docs/README.md`** - 添加到相应分类
2. **`README.md`**（根目录）- 如果是重要文档，添加快速链接
3. **`CHANGELOG.md`** - 如果是功能文档，添加到版本记录

---

## 🗄️ 文档归档规则

### 归档时机

1. **修复记录**: 创建时直接放入 `docs/archive/bugfixes/`
2. **阶段报告**: 阶段结束后移至 `docs/archive/phases/`
3. **版本文档**: 新版本发布后，旧版本移至 `docs/archive/versions/`
4. **临时文档**: 3个月后归档或删除

### 归档流程

```bash
# 1. 确定归档分类
questionnaire | search | frontend | backend | phases | versions

# 2. 移动文件到归档目录
Move-Item -Path "QUESTIONNAIRE_FIX_v7.115.md" -Destination "docs/archive/bugfixes/questionnaire/"

# 3. 更新索引（如果需要）
# 从 docs/README.md 中移除或标记为已归档
```

### 归档清理策略

- **保留**: 近3个月的完整记录
- **精简**: 3-6个月前的记录提炼关键信息
- **删除**: 6个月以上无参考价值的临时文档
- **精选**: 重要修复案例提取到 `.github/historical_fixes/`

---

## 🚫 禁止行为

### 1. 禁止在根目录创建新 .md 文件

**除非满足以下条件之一**：
- 核心文档（README.md, CHANGELOG.md等）
- 紧急恢复文档（EMERGENCY_RECOVERY.md）
- 经团队审批的重要文档

**违规示例**：
```bash
# ❌ 错误：在根目录创建修复文档
NEW_FEATURE_FIX.md  # 应放在 docs/archive/bugfixes/

# ✅ 正确：在归档目录创建
docs/archive/bugfixes/backend/new_feature_fix_20260102.md
```

### 2. 禁止重复文档

**检查流程**：
1. 创建前搜索是否已存在类似文档
2. 如果存在，更新现有文档而非新建
3. 如果需要新建，确保内容不重复

### 3. 禁止随意修改文档结构

**变更文档结构需要**：
1. 提出 Issue 说明原因
2. 团队讨论和批准
3. 更新相关索引和链接
4. 通知所有贡献者

---

## ✅ 文档质量检查清单

### 新增文档检查

- [ ] 文档已归类到正确目录
- [ ] 文件命名符合规范
- [ ] 文档内容结构清晰
- [ ] 代码示例可运行
- [ ] 内部链接有效
- [ ] 已更新 `docs/README.md` 索引
- [ ] 已添加到 `CHANGELOG.md`（如适用）

### 更新文档检查

- [ ] 更新日期已修改
- [ ] 版本号已更新
- [ ] 旧内容已标记或删除
- [ ] 相关链接已更新
- [ ] 截图/示例已更新

---

## 🤖 自动化检查机制

### 三层保障体系

为防止根目录再次堆积文件，项目建立了三层自动化保障机制：

#### 1️⃣ 本地检查 - Pre-commit Hook

**触发时机**: 每次 `git commit` 前自动运行

**检查内容**:
- ✅ 根目录 .md 文件数 ≤ 10 个
- ✅ 无脚本文件（.py/.sh/.bat）
- ✅ 无测试文件（test_*.py）
- ✅ 无临时文件（.log/.tmp/.bak）
- ✅ 总文件数 ≤ 20 个

**配置文件**: `.pre-commit-config.yaml`

```yaml
# 根目录清洁度检查
- repo: local
  hooks:
    - id: check-root-cleanliness
      name: 检查根目录清洁度
      entry: python scripts/check_root_cleanliness.py
      language: system
      pass_filenames: false
      always_run: true
```

**使用方法**:
```bash
# 安装 pre-commit（首次）
pip install pre-commit
pre-commit install

# 手动运行检查
pre-commit run check-root-cleanliness --all-files

# 每次提交时自动运行
git commit -m "your message"
```

#### 2️⃣ 持续集成 - GitHub Actions CI

**触发时机**: 每次 push 或 pull request

**检查流程**:
```yaml
jobs:
  check-root-directory:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - name: Check root directory cleanliness
      run: python scripts/check_root_cleanliness.py
```

**配置文件**: `.github/workflows/ci.yml`

**查看结果**: GitHub → Actions → CI workflow

#### 3️⃣ 手动检查 - 命令行工具

**使用场景**:
- 定期巡检（建议每周一次）
- 大量文件操作后
- 团队成员未启用 pre-commit

**运行方法**:
```bash
# Windows
python scripts\check_root_cleanliness.py

# Linux/Mac
python scripts/check_root_cleanliness.py
```

**示例输出**:
```
======================================================================
🔍 根目录清洁度检查报告
======================================================================

✅ 白名单文件: 15 个
❗ 未归类 .md 文件: 0 个
❗ 脚本文件: 0 个
❗ 测试文件: 0 个
⚠️  临时文件: 0 个
⚠️  其他文件: 0 个

======================================================================
✅ 根目录清洁度检查通过！
======================================================================
```

### 违规处理

如果检查失败，脚本会提供详细的违规信息和解决方案：

```
❌ 根目录发现 3 个未归类的 .md 文件（应为0）：
   → QUESTIONNAIRE_FIX.md
   → SEARCH_TOOL_UPDATE.md
   → PHASE_6_REPORT.md
   💡 应移动到: docs/ 下的对应模块目录

📋 解决方案：
1. 运行清理脚本:
   python scripts/organize_root_files.py

2. 手动移动文件:
   - Markdown文档 → docs/
   - 脚本文件 → scripts/
   - 测试文件 → tests/

3. 查看文档规范:
   .github/DOCUMENTATION_RULES.md
```

### 白名单管理

如需添加允许的根目录文件，编辑 `scripts/check_root_cleanliness.py`:

```python
ALLOWED_ROOT_FILES = {
    # 核心文档
    'README.md',
    'QUICKSTART.md',
    'CONTRIBUTING.md',
    # ... 其他文件
    'YOUR_NEW_FILE.md',  # 添加新文件
}
```

**注意**: 添加前请确认该文件确实需要在根目录，避免破坏清洁度原则。

---

## 🤖 自动化检查（CI）

### 文档数量检查

```yaml
# .github/workflows/docs-check.yml
name: Documentation Check

on: [pull_request]

jobs:
  check-root-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check root directory .md files
        run: |
          # 统计根目录 .md 文件数量（排除核心文档）
          count=$(find . -maxdepth 1 -name "*.md" ! -name "README.md" ! -name "CHANGELOG.md" ! -name "QUICKSTART.md" ! -name "CONTRIBUTING.md" ! -name "EMERGENCY_RECOVERY.md" ! -name "BACKUP_GUIDE.md" ! -name "README_TESTING.md" ! -name "NEXT_STEPS.md" | wc -l)

          if [ $count -gt 0 ]; then
            echo "❌ 根目录有 $count 个非核心 .md 文件，请移至 docs/ 相应目录"
            exit 1
          else
            echo "✅ 根目录文档数量符合规范"
          fi
```

### 文档命名检查

```yaml
# 检查文档命名规范
- name: Check file naming convention
  run: |
    # 检查 docs/archive/bugfixes/ 下的文件命名
    python scripts/check_docs_naming.py
```

---

## 📊 文档统计

### 定期统计（每月）

```bash
# 统计文档数量
Get-ChildItem -Path . -Filter "*.md" -Recurse | Measure-Object

# 统计各目录文档分布
Get-ChildItem -Path docs -Directory | ForEach-Object {
    $count = (Get-ChildItem -Path $_.FullName -Filter "*.md" -Recurse).Count
    Write-Host "$($_.Name): $count 个文档"
}

# 统计归档目录大小
$archiveSize = (Get-ChildItem -Path docs\archive -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "归档目录大小: $([math]::Round($archiveSize, 2)) MB"
```

### 清理建议触发条件

- 根目录 .md 文件 > 10 个
- `docs/archive/bugfixes/` > 100 个文件
- 归档目录总大小 > 50 MB
- 6个月以上未更新的文档 > 50 个

---

## 🔄 文档审查流程

### 季度审查（每3个月）

**审查内容**：
1. 检查根目录文档数量
2. 清理 `docs/archive/bugfixes/` 过期文档
3. 更新 `docs/README.md` 索引
4. 检查文档链接有效性
5. 统计文档访问频率（如有分析工具）

**清理流程**：
```bash
# 1. 列出6个月以上未修改的归档文档
Get-ChildItem -Path docs\archive\bugfixes -Recurse -Filter "*.md" |
    Where-Object {$_.LastWriteTime -lt (Get-Date).AddMonths(-6)} |
    Select-Object FullName, LastWriteTime

# 2. 人工审查是否删除
# 3. 提取重要案例到 .github/historical_fixes/
# 4. 删除无价值文档
# 5. 更新索引
```

---

## 📞 联系与反馈

- **文档问题**: [提交 Issue](https://github.com/dafei0755/ai/issues)
- **改进建议**: [讨论区](https://github.com/dafei0755/ai/discussions)
- **紧急问题**: 联系项目维护者

---

## 📚 相关文档

- [核心开发规范](DEVELOPMENT_RULES_CORE.md)
- [变更检查清单](PRE_CHANGE_CHECKLIST.md)
- [贡献指南](../CONTRIBUTING.md)
- [文档导航](../docs/README.md)

---

**维护者**: [@dafei0755](https://github.com/dafei0755)
**最后更新**: 2026-01-02
