# 贡献指南

这是 Intelligent Project Analyzer 的开发入口文档。  
无论是修复 bug、开发功能还是改进文档，请从这里开始。

---

## 开发规范文档

在动手之前，先了解这个项目如何运作：

| 文档 | 内容 |
|------|------|
| [核心原则](docs/dev/principles.md) | 为什么这样开发、决策背后的理由 |
| [标准开发流程](docs/dev/workflow.md) | 从需求到合并的五个阶段 |
| [代码质量标准](docs/dev/quality.md) | 什么样的代码可以合并 |
| [测试规范](docs/dev/testing.md) | 如何写测试、测试分层策略 |

AI 工具使用规范（Copilot / Cursor 等）见 [.github/DEVELOPMENT_RULES_CORE.md](.github/DEVELOPMENT_RULES_CORE.md)。

---

## 快速上手

### 1. 环境搭建

```bash
# 后端
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 前端
cd frontend-nextjs
npm install
```

### 2. 创建工作分支

```bash
git checkout main && git pull
git checkout -b fix/your-issue-name   # 或 feature/ refactor/ arch/ chore/
```

**一个分支只解决一个问题。** 分支命名体现目的，不超过 1 周生命周期。

### 3. 开发与验证

```bash
# 运行快速测试（跳过 LLM / slow）
pytest -m "not llm and not slow" -q

# 代码质量检查
make lint          # ruff + mypy
make format        # 自动格式化

# 合并前完整验证
pytest --collect-only -q    # 必须 0 errors
pytest tests/unit/ -q       # 必须 0 failed
```

---

## 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/)：

```
<type>(<scope>): <描述>
```

**type 白名单**：`fix` / `feat` / `refactor` / `arch` / `chore` / `docs` / `test`

```bash
# 示例
git commit -m "fix(settings): 为 DEBUG 字段添加 bool 容错，防止导入期崩溃"
git commit -m "feat(search): 接入 Bocha 搜索工具"
git commit -m "refactor(api): 将 Pydantic 模型迁移至 api/models.py"
```

禁止无信息量的提交：`fix`、`update`、`修改`。

---

## 合并前检查清单

- [ ] `pytest --collect-only -q` → 0 errors
- [ ] `pytest tests/unit/ -q` → 0 failed
- [ ] 代码质量检查无新增 Error 级违规
- [ ] 相关文档已同步更新
- [ ] `CHANGELOG.md` 已记录（功能性变更）

---

## 问题反馈

- Bug 报告：[GitHub Issues](https://github.com/dafei0755/ai/issues)
- 功能讨论：[GitHub Discussions](https://github.com/dafei0755/ai/discussions)

