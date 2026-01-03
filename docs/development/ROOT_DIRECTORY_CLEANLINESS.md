# 根目录清洁度保障指南

> 防止根目录再次堆积文件的完整解决方案

**版本**: v1.0
**最后更新**: 2026-01-02

---

## 🎯 目标

保持根目录整洁，只保留核心文档和配置文件：
- **Markdown 文件**: ≤ 10 个
- **总文件数**: ≤ 20 个
- **禁止**: 脚本文件、测试文件、临时文件

---

## 🛡️ 三层保障机制

### 1️⃣ 本地检查 (Pre-commit Hook)

**何时运行**: 每次 `git commit` 前自动执行

**首次设置**:
```bash
# 安装 pre-commit
pip install pre-commit

# 安装 git hooks
pre-commit install
```

**日常使用**:
```bash
# 自动运行（每次提交时）
git add .
git commit -m "your message"  # 会自动检查

# 手动运行
pre-commit run check-root-cleanliness --all-files
```

**检查项目**:
- ✅ Markdown 文件数量限制
- ✅ 禁止脚本文件 (.py/.sh/.bat)
- ✅ 禁止测试文件 (test_*.py)
- ✅ 禁止临时文件 (.log/.tmp)

---

### 2️⃣ CI 检查 (GitHub Actions)

**何时运行**: 每次 push 或 PR 时自动执行

**查看结果**:
1. 进入 GitHub 仓库
2. 点击 "Actions" 标签
3. 查看最新的 "CI" workflow
4. 查看 "check-root-directory" 任务

**失败处理**:
- 如果 CI 失败，查看报告中的违规文件
- 按照提示移动文件到正确位置
- 重新提交

---

### 3️⃣ 手动检查 (命令行工具)

**何时使用**:
- 📅 定期巡检（建议每周一次）
- 🔧 大量文件操作后
- 👥 团队成员未启用 pre-commit

**运行命令**:
```bash
# Windows
python scripts\check_root_cleanliness.py

# Linux/Mac
python scripts/check_root_cleanliness.py
```

**通过示例**:
```
======================================================================
🔍 根目录清洁度检查报告
======================================================================

✅ 白名单文件: 14 个
❗ 未归类 .md 文件: 0 个
❗ 脚本文件: 0 个
❗ 测试文件: 0 个
⚠️  临时文件: 0 个
⚠️  其他文件: 0 个

======================================================================
✅ 根目录清洁度检查通过！
======================================================================
```

**失败示例**:
```
======================================================================
⚠️  发现以下问题：
======================================================================

❌ 根目录发现 3 个未归类的 .md 文件（应为0）：
   → QUESTIONNAIRE_FIX.md
   → SEARCH_TOOL_UPDATE.md
   → PHASE_6_REPORT.md
   💡 应移动到: docs/ 下的对应模块目录

❌ 根目录发现 2 个脚本文件：
   → test_new_feature.py
   → run_temp_server.py
   💡 应移动到: scripts/ 目录

📋 解决方案：
1. 手动移动文件:
   - Markdown文档 → docs/
   - 脚本文件 → scripts/
   - 测试文件 → tests/

2. 查看文档规范:
   .github/DOCUMENTATION_RULES.md
```

---

## 📂 文件归类指南

### 允许在根目录的文件

**核心文档** (9个):
- `README.md` - 项目概览
- `QUICKSTART.md` - 快速启动
- `CONTRIBUTING.md` - 贡献指南
- `CHANGELOG.md` - 版本历史
- `EMERGENCY_RECOVERY.md` - 紧急恢复
- `BACKUP_GUIDE.md` - 备份指南
- `README_TESTING.md` - 测试概览
- `NEXT_STEPS.md` - 下一步计划
- `LICENSE` - 许可证

**配置文件** (6个):
- `.env` / `.env.example` - 环境变量
- `.gitignore` - Git 忽略规则
- `.pre-commit-config.yaml` - Pre-commit 配置
- `pytest.ini` - Pytest 配置
- `requirements.txt` - Python 依赖
- `Makefile` - Make 命令

### 其他文件应该放在哪里

| 文件类型 | 目标位置 | 示例 |
|---------|---------|------|
| **功能文档** | `docs/features/` | `docs/features/questionnaire/README.md` |
| **架构文档** | `docs/architecture/` | `docs/architecture/AGENT_ARCHITECTURE.md` |
| **开发文档** | `docs/development/` | `docs/development/API.md` |
| **修复记录** | `docs/archive/bugfixes/` | `docs/archive/bugfixes/questionnaire/fix_20260102.md` |
| **脚本文件** | `scripts/` | `scripts/run_server.py` |
| **测试文件** | `tests/` | `tests/test_questionnaire.py` |
| **配置代码** | `config/` | `config/settings.py` |
| **临时文件** | 删除或 `.gitignore` | `.log`, `.tmp`, `__pycache__` |

---

## 🔧 常见问题

### Q1: 我需要在根目录创建新的 .md 文件怎么办？

**A**: 优先考虑放在 `docs/` 下对应模块：

```bash
# ❌ 不推荐
touch README_NEW_FEATURE.md

# ✅ 推荐
touch docs/features/new-feature/README.md
```

如果确实需要在根目录（如重要的用户指南），请：
1. 在 `scripts/check_root_cleanliness.py` 中添加到白名单
2. 更新 [.github/DOCUMENTATION_RULES.md](../../.github/DOCUMENTATION_RULES.md)
3. 团队讨论确认必要性

### Q2: Pre-commit 检查失败，如何临时跳过？

**A**: 使用 `--no-verify` 参数（不推荐）：

```bash
git commit -m "emergency fix" --no-verify
```

**注意**:
- CI 仍会检查，最终需要修复
- 仅用于紧急情况
- 后续必须补充修复提交

### Q3: 如何添加白名单文件？

**A**: 编辑 `scripts/check_root_cleanliness.py`:

```python
ALLOWED_ROOT_FILES = {
    # 核心文档
    'README.md',
    'QUICKSTART.md',
    # ... 现有文件 ...

    # 新增文件（务必添加注释说明原因）
    'YOUR_NEW_FILE.md',  # 用户快速参考指南
}
```

**审查标准**:
- 是否是核心用户文档？
- 是否需要在克隆后立即可见？
- 能否移动到 `docs/` 子目录？
- 团队是否达成共识？

### Q4: 临时文件如何处理？

**A**: 添加到 `.gitignore`:

```gitignore
# 临时文件
*.log
*.tmp
*.bak
__pycache__/
nul

# 测试输出
test_output/
htmlcov/
```

### Q5: 检查脚本本身出错怎么办？

**A**:
1. 检查 Python 环境：`python --version`（需要 3.10+）
2. 查看详细错误：`python scripts\check_root_cleanliness.py`
3. 提交 Issue 或联系维护者

---

## 📊 效果对比

### 整理前（2025-12-31）
```
根目录文件统计:
- Markdown 文件: 75 个
- 测试文件: 19 个
- 脚本文件: 15 个
- 总文件数: 109 个
```

### 整理后（2026-01-02）
```
根目录文件统计:
- Markdown 文件: 9 个 ✅ (88% 减少)
- 测试文件: 0 个 ✅ (100% 清理)
- 脚本文件: 0 个 ✅ (100% 清理)
- 总文件数: 15 个 ✅ (86% 减少)
```

### 保障机制启用后
- ✅ 每次提交前自动检查（Pre-commit）
- ✅ 每次 push 时 CI 验证（GitHub Actions）
- ✅ 定期手动巡检（推荐每周）

---

## 🔗 相关文档

- [文档维护规范](../../.github/DOCUMENTATION_RULES.md)
- [贡献指南](../../CONTRIBUTING.md)
- [文档导航](../README.md)

---

## 📞 支持

- **问题反馈**: [GitHub Issues](https://github.com/dafei0755/ai/issues)
- **改进建议**: [GitHub Discussions](https://github.com/dafei0755/ai/discussions)

---

**维护者**: [@dafei0755](https://github.com/dafei0755)
**最后更新**: 2026-01-02
