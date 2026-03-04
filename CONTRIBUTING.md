# 🤝 贡献指南

> 感谢你考虑为 Intelligent Project Analyzer 做出贡献！

---

## 📋 开始之前

### ⚠️ 必读文档

在修改代码前，**必须**阅读以下文档：

1. 🔥 **[核心开发规范](.github/DEVELOPMENT_RULES_CORE.md)** - v4.0，AI工具优先加载
   - 📝 **v2.1**: 任务列表化执行规则 + "继续"指令快速响应
   - 🌿 **v4.0 新增**: Git 分支规范 — 任何代码改动必须在独立分支完成
2. 📚 [完整开发规范](.github/DEVELOPMENT_RULES.md) - 深度查阅特定章节
3. ✅ [变更检查清单](.github/PRE_CHANGE_CHECKLIST.md) - 修改前强制流程
4. 📖 [历史修复记录](.github/historical_fixes/) - 5+ 精选 bug 修复案例

### 🔄 强制开发流程

```
诊断问题 → 查阅历史 → 报告方案 → 获得批准 → 执行修改 → 更新文档
```

**为什么这么严格？**

- 避免重复犯错（77+ 历史修复案例的教训）
- 保持代码质量（80%+ 测试覆盖率）
- 确保文档同步（避免文档与代码脱节）

---

## 🛠️ 贡献流程

### 1. 创建工作分支（强制）

> ⚠️ **核心原则（v4.0）：任何代码改动必须在独立分支完成，绝不在 main 直接修改**

#### 分支命名规则

| 改动类型 | 前缀 | 示例 |
|---------|------|------|
| 缺陷修复 | `fix/` | `fix/settings-import-safety` |
| 重构优化 | `refactor/` | `refactor/remove-server-proxy` |
| 新功能 | `feature/` | `feature/event-bus` |
| 清理工作 | `chore/` | `chore/cleanup-dead-code` |
| 架构整改 | `arch/` | `arch/server-slim-p1` |

```bash
# 从最新 main 切出分支（单一职责，不超过 1 周生命周期）
git checkout main && git pull
git checkout -b fix/your-fix-name

# 多个独立子系统改动 → 拆为多个分支，按依赖顺序合并
# 示例：fix/A（先合并）→ refactor/B（依赖 A）→ chore/C（独立）
```

#### 禁止事项

- ❌ 禁止一个分支承载互不依赖的多个子系统改动
- ❌ 禁止跳过测试验证直接合并
- ❌ 禁止长生命周期大分支（>1 周未合并须拆分）

#### 合并前验收门槛（强制）

```bash
# 底线：收集零错误
pytest --collect-only -q        # 期望：0 errors

# 单元测试绿色
pytest tests/unit/ -q           # 期望：无 FAILED
```

### 2. 设置开发环境

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows

# 安装依赖（包含开发工具）
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 如果存在

# 安装前端依赖
cd frontend-nextjs
npm install
cd ..
```

### 3. 遵循代码规范

#### Python 代码规范

- **格式化**: Black（行长度 88）
- **导入排序**: isort
- **代码检查**: Flake8
- **类型提示**: 尽可能使用 Type Hints

```bash
# 格式化代码
black intelligent_project_analyzer/

# 排序导入
isort intelligent_project_analyzer/

# 代码检查
flake8 intelligent_project_analyzer/
```

#### TypeScript/React 代码规范

- **格式化**: Prettier
- **代码检查**: ESLint
- **组件规范**: 函数式组件 + Hooks

```bash
cd frontend-nextjs
npm run lint
npm run format
```

#### 提交信息规范（Conventional Commits）

遵循 [约定式提交](https://www.conventionalcommits.org/zh-hans/)：

```
<type>(<scope>): <描述（中文可）>
```

**type 与 scope 白名单**：

| type | 含义 | 常用 scope |
|------|------|----------|
| `fix` | 缺陷修复 | `settings`, `api`, `workflow`, `state` |
| `feat` | 新功能 | `search`, `questionnaire`, `image` |
| `refactor` | 重构（不改行为） | `server`, `deps`, `api` |
| `chore` | 清理/工具/配置 | `dead-code`, `deps`, `ci` |
| `arch` | 架构级改动 | `server`, `workflow`, `state` |
| `docs` | 文档 | `rules`, `api`, `readme` |
| `test` | 测试 | `unit`, `integration`, `e2e` |

**提交示例**：
```bash
# 缺陷修复
git commit -m "fix(settings): 添加 DEBUG 字段 bool 容错 validator，防止导入期崩溃"

# 重构
git commit -m "refactor(api): 消除 7 个文件的 _ServerProxy 反向依赖模式"

# 清理
git commit -m "chore(dead-code): 删除 5 个冻结 feature flag 和 12 个备份文件"

# 架构
git commit -m "arch(server): 将 31 个 Pydantic 模型迁移至 api/models.py"
```

**禁止**：`git commit -m "fix"`、`git commit -m "update"` 等无信息提交

### 4. 添加测试

**测试覆盖率要求**: ≥ 80%

```bash
# 运行所有测试
pytest

# 查看覆盖率
pytest --cov=intelligent_project_analyzer --cov-report=html

# 只运行快速测试（跳过 LLM 调用）
pytest -m "not llm"
```

**测试文件位置**：
- 后端测试: `intelligent_project_analyzer/tests/`
- 前端测试: `frontend-nextjs/__tests__/`

**测试类型**：
- ✅ 单元测试 - 测试单个函数/类
- ✅ 集成测试 - 测试组件交互
- ✅ 端到端测试 - 测试完整流程

---

### 4.1 🗂️ 测试文件生命周期管理（强制规范）

> **背景教训**：v8.1.0 发布后，发现 v8.0.0 历史快照中遗留了 40 个失败测试文件（290 个失败用例），全部是针对已废弃接口 / 未实现功能的"设计愿景测试"。每次 `pytest` 都触发干扰，严重污染 CI 信噪比。

#### 📐 测试文件四象限分类

```
                   |  接口存在  |  接口不存在/已废弃
-------------------+----------+-------------------
 测试通过           |  ✅ 正常  |  ⚠️  立即清查原因
 测试失败           |  🔴 必修  |  📦  归档到 _archive
```

#### 📋 测试文件生命周期规则

**规则 1：测试与实现必须同步发布**

```
✅ 正确：功能实现 → 测试通过 → 一起提交
❌ 禁止：测试通过，功能 TODO → 长期堆积"设计愿景测试"
```

如果需要 TDD 先写测试，**必须**在文件头部加声明：

```python
"""
⚠️  TDD ASPIRATIONAL TEST — 功能尚未实现
实现目标：<简述功能>
计划版本：vX.Y
若超过 2 个迭代未实现，执行归档（移至 tests/_archive/）
"""
import pytest
pytestmark = pytest.mark.skip(reason="aspirational: 功能尚未实现，待 vX.Y 落地")
```

---

**规则 2：架构重构后立即审查测试文件**

每次完成以下操作后，**必须**在当次 PR 中审查并处理受影响的测试：

| 操作类型 | 需要审查的测试范围 |
|---------|----------------|
| 删除模块/函数/类 | 所有 import 该符号的测试文件 |
| 重命名接口 | 所有调用旧接口名的测试文件 |
| 合并/拆分 Node | 所有引用该 node 名的测试文件 |
| 修改 State 字段 | 所有依赖该字段的集成/端到端测试 |
| 冻结 Feature Flag | 依赖该 flag 为 False 的分支测试 |

检查命令（例：删除了 `step3_radar` 方法）：
```bash
grep -r "step3_radar" tests/ --include="*.py" -l
```

---

**规则 3：失败测试不得带入主分支**

```
PR 合并前检查：pytest tests/ --tb=no -q | tail -1
结果必须为：X passed, Y skipped（0 failed, 0 errors）
```

对于**无法立即修复**的失败测试，必须二选一：

| 选项 | 操作 | 适用场景 |
|------|------|---------|
| **归档** | `git mv tests/xxx.py tests/_archive/xxx.py` | 测试针对已废弃功能，永久失效 |
| **跳过** | 在测试函数加 `@pytest.mark.skip(reason="...")` | 功能暂时不可用，后续会修复 |

---

**规则 4：`tests/_archive/` 目录管理**

```
tests/
├── unit/            ← 活跃测试（必须全过）
├── integration/     ← 活跃测试（必须全过）
├── regression/      ← 活跃测试（必须全过）
├── e2e/             ← 活跃测试（允许 @slow 标记）
└── _archive/        ← 历史归档（pytest 不收集此目录）
    ├── unit/
    ├── integration/
    └── regression/
```

`_archive/` 规则：
- `pytest.ini` 中 `norecursedirs` 已排除，**不会被自动运行**
- 文件**不得删除**，保留为历史查阅依据
- 每个归档文件的第一行应有注释说明归档原因和日期：
  ```python
  # ARCHIVED: 2026-03-04 — 针对 v8.0 aspirational TDD，接口从未实现
  ```

---

**规则 5：定期清理（每季度）**

执行以下命令扫描潜在失效测试：
```bash
# 1. 收集所有测试但不运行，发现 import 错误
pytest tests/ --collect-only -q 2>&1 | grep "ERROR"

# 2. 统计按文件分组的失败数
pytest tests/ --tb=no -q 2>&1 | grep "FAILED" | cut -d: -f1 | sort | uniq -c | sort -rn

# 3. 检查测试是否引用了已不存在的符号
grep -r "from intelligent_project_analyzer" tests/ --include="*.py" | \
  python -c "import sys; [print(l.strip()) for l in sys.stdin if 'DEPRECATED' in l]"
```

若发现批量失败（同一文件 ≥ 3 个用例失败），**优先归档，不得在 CI 中反复触发**。

---

#### 🚨 典型反模式（禁止）

```python
# ❌ 反模式1：注释掉失败断言，假装通过
def test_new_feature():
    result = new_function()
    # assert result["key"] == "value"  # TODO: 等功能实现再打开
    pass  # 这个测试没有任何意义

# ❌ 反模式2：用 try/except 吞掉所有失败
def test_something():
    try:
        assert risky_function() == expected
    except:
        pass  # 永远"通过"，毫无价值

# ❌ 反模式3：测试文件堆积但不清理
# 重构后旧函数已删除，但测试文件仍保留在 tests/unit/ 中
# 结果：每次 pytest 触发 ImportError，污染输出
```

#### ✅ 正确模式

```python
# ✅ 正模式1：功能已废弃，测试归档
# git mv tests/unit/test_old_feature.py tests/_archive/unit/test_old_feature.py
# 在文件头加上：# ARCHIVED: 2026-03-04 — old_feature 已被 new_feature 替代

# ✅ 正模式2：功能暂未实现，明确跳过
@pytest.mark.skip(reason="aspirational: _generate_rule_based_tasks 待 v8.2 实现")
def test_rule_engine_enabled():
    ...

# ✅ 正模式3：接口重命名，同步更新测试
# 重构时：step3_radar → step2_radar
# 当次 PR 必须同步替换所有测试文件中的旧方法名
```



### 5. 更新文档

修改以下内容时，**必须**同步更新文档：

- **配置文件** → 更新 `docs/getting-started/CONFIGURATION.md`
- **API 接口** → 更新 `docs/development/API.md`
- **核心逻辑** → 更新代码注释和相关文档
- **新功能** → 在 `CHANGELOG.md` 添加条目

**文档位置规范**：

| 文档类型 | 位置 |
|---------|------|
| 入门指南 | `docs/getting-started/` |
| 架构设计 | `docs/architecture/` |
| 部署运维 | `docs/deployment/` |
| 功能文档 | `docs/features/{feature}/` |
| 开发指南 | `docs/development/` |
| 版本发布 | `docs/releases/vX.Y/` |
| 历史归档 | `docs/archive/` |

**⚠️ 禁止**：在根目录创建新的 .md 文件（除非获得批准）

### 6. 提交 Pull Request

```bash
# 合并前同步 main 的最新提交
git fetch origin main
git rebase origin/main

# 推送分支
git push origin fix/your-fix-name
```

在 GitHub 上创建 Pull Request：

1. **标题**: 遵循 Conventional Commits 格式（`fix(scope): 描述`）
2. **描述**: 包含以下内容：
   - 变更原因和背景
   - 实现方案
   - 测试结果（`pytest --collect-only -q` 输出截图）
   - 分支特定验证命令的执行结果
3. **合并前检查清单**（必须全部通过）：
   - [ ] `pytest --collect-only -q` → **0 errors**
   - [ ] `pytest tests/unit/ -q` → **0 failed**
   - [ ] 分支对应的验收命令通过（见核心开发规范 v4.0）
   - [ ] 代码覆盖率 ≥ 80%
   - [ ] 遵循代码规范（black / isort）
   - [ ] 更新相关文档
   - [ ] 通过 CI/CD 检查

---

## 🐛 报告 Bug

使用 [GitHub Issues](https://github.com/dafei0755/ai/issues/new) 报告 Bug：

### Bug 报告模板

```markdown
### Bug 描述
清晰描述 Bug 的表现

### 复现步骤
1. 打开 '...'
2. 点击 '...'
3. 滚动到 '...'
4. 看到错误

### 期望行为
描述你期望的正确行为

### 实际行为
描述实际发生的行为

### 环境信息
- 操作系统: [如 Windows 11]
- Python 版本: [如 3.11]
- Node.js 版本: [如 18.17]
- 浏览器: [如 Chrome 120]

### 截图
如果适用，添加截图帮助解释问题

### 额外信息
添加任何其他相关信息
```

---

## 💡 提出新功能

使用 [GitHub Discussions](https://github.com/dafei0755/ai/discussions) 讨论新功能：

1. **搜索现有讨论** - 避免重复提议
2. **描述用例** - 解释为什么需要这个功能
3. **提供方案** - 如果有想法，描述实现方案
4. **等待反馈** - 等待维护者和社区反馈

---

## 📝 文档贡献

文档改进同样重要！

### 文档类型

- **修正错误** - 修复拼写、语法、代码示例错误
- **补充内容** - 添加缺失的说明、示例
- **新文档** - 创建新的教程、指南

### 文档标准

- **清晰简洁** - 避免冗长和模糊
- **代码示例** - 提供可运行的代码示例
- **链接正确** - 确保内部链接有效
- **格式一致** - 遵循现有文档风格

---

## 🔍 代码审查流程

### 审查标准

维护者会检查以下方面：

1. **功能性** - 是否解决了问题/实现了功能
2. **代码质量** - 是否遵循规范，是否易读易维护
3. **测试覆盖** - 是否有足够的测试
4. **性能影响** - 是否影响系统性能
5. **文档完整性** - 是否更新了相关文档

### 审查时间

- **小型改动** - 1-2 天
- **中型改动** - 3-5 天
- **大型改动** - 1-2 周

### 审查反馈

- **请求修改** - 根据反馈修改代码
- **讨论方案** - 如有不同意见，友好讨论
- **持续改进** - 审查是学习和改进的机会

---

## 🏆 贡献者认可

- **首次贡献者** - 在 README 中列出
- **活跃贡献者** - 在 CONTRIBUTORS.md 中特别感谢
- **核心贡献者** - 可能被邀请成为维护者

---

## 📜 行为准则

### 我们的承诺

为了营造开放和友好的环境，我们承诺：

- ✅ 尊重所有贡献者
- ✅ 保持友善和专业
- ✅ 提供建设性反馈
- ✅ 接受不同观点
- ✅ 关注对社区最有利的事情

### 不可接受的行为

- ❌ 使用性别化语言或图像
- ❌ 人身攻击或政治攻击
- ❌ 公开或私下骚扰
- ❌ 未经许可发布他人私人信息
- ❌ 其他不道德或不专业的行为

### 执行

违反行为准则的行为将被警告或禁止参与项目。

---

## ❓ 需要帮助？

- 📖 [文档](docs/README.md)
- 💬 [讨论区](https://github.com/dafei0755/ai/discussions)
- 🐛 [Issues](https://github.com/dafei0755/ai/issues)

---

## 📄 许可证

贡献的代码将采用项目的 [MIT 许可证](LICENSE)。

---

**感谢你的贡献！** 🙏

你的帮助让这个项目变得更好！
