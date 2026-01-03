# 🤝 贡献指南

> 感谢你考虑为 Intelligent Project Analyzer 做出贡献！

---

## 📋 开始之前

### ⚠️ 必读文档

在修改代码前，**必须**阅读以下文档：

1. 🔥 **[核心开发规范](.github/DEVELOPMENT_RULES_CORE.md)** - 200行精简版，AI工具优先加载
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

### 1. Fork 项目并创建分支

```bash
# Fork 项目到你的 GitHub 账号
# 克隆你的 Fork
git clone https://github.com/你的用户名/ai.git
cd ai

# 添加上游仓库
git remote add upstream https://github.com/dafei0755/ai.git

# 创建功能分支
git checkout -b feature/your-feature-name
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

#### 提交信息规范

遵循 [约定式提交](https://www.conventionalcommits.org/zh-hans/)：

```
<类型>(<范围>): <简短描述>

<详细描述>（可选）

<关联 Issue>（可选）
```

**类型示例**：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响逻辑）
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建/工具配置

**提交示例**：
```bash
git commit -m "fix(questionnaire): 修复Step3用户输入显示缺失问题

- 添加 user_input 和 user_input_summary 字段到后端 payload
- 更新前端组件以显示用户原始需求摘要
- 添加单元测试覆盖新功能

Fixes #123"
```

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
# 同步上游更新
git fetch upstream
git rebase upstream/main

# 推送到你的 Fork
git push origin feature/your-feature-name
```

在 GitHub 上创建 Pull Request：

1. **标题**: 清晰描述变更内容
2. **描述**: 包含以下内容：
   - 变更原因和背景
   - 实现方案
   - 测试结果截图
   - 关联的 Issue
3. **检查清单**: 确保以下项目已完成
   - [ ] 通过所有测试
   - [ ] 代码覆盖率 ≥ 80%
   - [ ] 遵循代码规范
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
