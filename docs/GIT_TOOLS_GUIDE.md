# Git 版本管理工具使用指南

> gitchangelog + commitizen 组合实践

---

## 📦 已安装工具

### 1. **gitchangelog** (Python)
- **功能**: 自动生成 CHANGELOG.md
- **位置**: `C:\Users\SF\AppData\Roaming\Python\Python313\Scripts\gitchangelog.exe`
- **配置**: `.gitchangelog.rc`
- **包装脚本**: `scripts/generate_changelog.py`（解决 Windows 编码问题）

### 2. **commitizen** (npm 全局)
- **功能**: 交互式规范化提交
- **命令**: `git cz`
- **配置**: `.czrc`

---

## 🚀 快速开始

### 日常提交流程

```bash
# 1. 修改代码
# 编辑文件...

# 2. 添加到暂存区
git add .

# 3. 使用 commitizen 提交（替代 git commit）
git cz

# 交互式选择：
# ? Select the type of change:
#   ❯ feat:     新功能（A new feature）
#     fix:      修复Bug（A bug fix）
#     docs:     文档更新（Documentation only changes）
#     ...
# ? What is the scope: api  # 可选，如 api, frontend, core
# ? Write a short description: 添加雷达图生成接口
# ? Provide a longer description: (可选，按回车跳过)
# ? Are there any breaking changes?: No
# ? Does this change affect any open issues?: (可选，如 #123)

# 提交完成！格式自动规范化为：feat(api): 添加雷达图生成接口
```

### 生成 CHANGELOG

```bash
# 方法1: 使用包装脚本（推荐，解决编码问题）
python scripts/generate_changelog.py CHANGELOG.md

# 方法2: 只查看最近版本的变更
python scripts/generate_changelog.py CHANGELOG_LATEST.md

# 方法3: 直接使用 gitchangelog（可能有编码问题）
C:\Users\SF\AppData\Roaming\Python\Python313\Scripts\gitchangelog.exe > CHANGELOG.md
```

---

## 📝 Commit 类型说明

| 类型 | 说明 | 示例 |
|------|------|------|
| **feat** | 新功能 | `feat(api): 添加雷达图生成接口` |
| **fix** | Bug修复 | `fix(frontend): 修复问卷跳过逻辑错误` |
| **docs** | 文档更新 | `docs: 更新多环境配置指南` |
| **style** | 代码格式（不影响功能） | `style: 格式化代码缩进` |
| **refactor** | 重构 | `refactor(core): 简化路由逻辑` |
| **perf** | 性能优化 | `perf(search): 优化查询缓存` |
| **test** | 测试相关 | `test: 添加单元测试` |
| **build** | 构建系统或依赖变更 | `build: 升级依赖版本` |
| **ci** | CI 配置修改 | `ci: 添加GitHub Actions` |
| **chore** | 其他修改 | `chore: 清理临时文件` |
| **revert** | 回退提交 | `revert: 撤销上次提交` |

---

## 🎯 实际场景示例

### 场景1: 添加新功能

```bash
# 1. 创建功能分支
git checkout -b feature/radar-chart

# 2. 开发功能
# 编辑代码...

# 3. 使用 commitizen 提交
git add .
git cz
# 选择: feat
# Scope: api
# 描述: 添加雷达图生成接口

# 4. 推送到远程
git push origin feature/radar-chart

# 5. 合并到主分支后生成 CHANGELOG
git checkout main
git merge feature/radar-chart
python scripts/generate_changelog.py CHANGELOG.md
git add CHANGELOG.md
git commit -m "chore: update changelog for v8.2.0"
git tag -a v8.2.0 -m "Release v8.2.0"
```

### 场景2: 修复 Bug

```bash
# 1. 创建修复分支
git checkout -b bugfix/port-conflict

# 2. 修复代码
# 编辑文件...

# 3. 提交
git add .
git cz
# 选择: fix
# Scope: utils
# 描述: 修复端口冲突检测逻辑
# Breaking changes: No
# Issues: #123  # 关联issue号

# 提交信息自动生成: fix(utils): 修复端口冲突检测逻辑 #123
```

### 场景3: 发版前生成完整 CHANGELOG

```bash
# 1. 确保在主分支
git checkout main

# 2. 拉取最新代码
git pull origin main

# 3. 生成 CHANGELOG
python scripts/generate_changelog.py CHANGELOG.md

# 4. 查看生成的内容
cat CHANGELOG.md

# 5. 提交 CHANGELOG
git add CHANGELOG.md
git commit -m "chore: update changelog for v8.2.0"

# 6. 打标签
git tag -a v8.2.0 -m "Release v8.2.0"
git push origin main --tags
```

---

## ⚙️ 配置说明

### .czrc（Commitizen 配置）

```json
{
  "path": "cz-conventional-changelog",
  "types": {
    "feat": {
      "description": "新功能（A new feature）",
      "title": "Features"
    },
    // ... 其他类型
  }
}
```

### .gitchangelog.rc（CHANGELOG 生成规则）

```python
# 忽略的提交模式
ignore_regexps = [
    r'@minor',
    r'!minor',
    r'^\s*WIP',
    r'^\s*Merge ',
]

# 按类型分组
section_regexps = [
    ('New Features', [r'^feat', r'^feature']),
    ('Bug Fixes', [r'^fix', r'^bugfix']),
    ('Performance', [r'^perf']),
    # ...
]
```

---

## 🛠️ 常见问题

### Q1: commitizen 提示找不到命令？

```bash
# 检查是否安装
npm list -g commitizen

# 重新安装
npm install -g commitizen cz-conventional-changelog
```

### Q2: gitchangelog 编码错误？

**解决方案**: 使用包装脚本 `scripts/generate_changelog.py`

```bash
# ✅ 推荐方式
python scripts/generate_changelog.py CHANGELOG.md

# ❌ 直接调用可能出错（Windows 编码问题）
gitchangelog > CHANGELOG.md
```

### Q3: 如何只生成最近一个版本的 CHANGELOG？

```bash
# 获取最后一个标签
git describe --tags --abbrev=0  # 假设是 v8.1.0

# 生成该标签到当前的变更
python scripts/generate_changelog.py CHANGELOG_LATEST.md v8.1.0..HEAD
```

### Q4: 提交信息写错了怎么办？

```bash
# 修改最后一次提交（未Push）
git commit --amend

# 修改历史提交（危险操作）
git rebase -i HEAD~3  # 编辑最近3次提交
```

### Q5: 想在 CHANGELOG 中添加中文怎么办？

**不推荐**: CHANGELOG 作为标准文档建议使用英文。

**替代方案**: 在 `.gitchangelog.rc` 中自定义 `section_regexps` 的标题：

```python
section_regexps = [
    ('新功能 (New Features)', [r'^feat']),
    ('Bug修复 (Bug Fixes)', [r'^fix']),
]
```

---

## 📊 版本号规范

### 语义化版本 (SemVer)

```
v主版本.次版本.修订号

示例：
v8.0.0  - 初始版本
v8.1.0  - 添加多环境支持（新功能）
v8.1.1  - 修复端口检测bug（修复）
v9.0.0  - 重构API架构（不兼容变更）
```

### 提交类型与版本号对应

| Commit类型 | 影响版本号 | 示例 |
|-----------|----------|------|
| `feat:` | 次版本 +1 | 8.1.0 → 8.2.0 |
| `fix:`, `perf:`, `refactor:` | 修订号 +1 | 8.1.0 → 8.1.1 |
| `feat!:`, `BREAKING CHANGE` | 主版本 +1 | 8.1.0 → 9.0.0 |
| `docs:`, `chore:`, `style:` | 不影响 | - |

---

## 🔗 相关文档

- [QUICKSTART.md](QUICKSTART.md) - 项目快速启动
- [MULTI_ENV_GUIDE.md](docs/MULTI_ENV_GUIDE.md) - 多环境开发指南
- [CHANGELOG.md](CHANGELOG.md) - 项目变更历史（自动生成）

---

## 💡 最佳实践

1. **小步提交**: 每次提交只做一件事，方便回滚
2. **描述清晰**: Commit message 简洁明确，说明"做了什么"而非"怎么做"
3. **及时更新**: 发版前必须更新 CHANGELOG.md
4. **规范标签**: 使用 `v` 前缀 + 语义化版本号（如 v8.1.0）
5. **定期维护**: 每周查看 `git log`，了解团队改动

**日常工作流**:

```bash
git checkout -b feature/xxx    # 创建分支
# 开发...
git add .
git cz                          # 规范提交
git push origin feature/xxx
# PR 合并后
python scripts/generate_changelog.py CHANGELOG.md  # 更新日志
git tag -a v8.2.0 -m "Release v8.2.0"              # 打标签
```

---

**Happy Committing! 🎉**
