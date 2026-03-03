# 🎯 多环境体系快速开始

> 5分钟快速配置并使用多环境隔离验证功能

---

## 第一步：创建测试环境配置 (2分钟)

```bash
# 1. 复制配置模板
copy .env.test.example .env.test

# 2. 编辑配置文件
notepad .env.test
```

**必填项**:
```env
OPENAI_API_KEY=sk-your-actual-key  # 填写你的API密钥
```

**可选调整**:
```env
# 测试环境可使用更便宜的模型
OPENAI_DEFAULT_MODEL=gpt-4o-mini

# 使用内存模式避免数据残留
REDIS_MEMORY_ONLY=true
DATABASE_URL=sqlite:///:memory:
```

---

## 第二步：验证配置 (1分钟)

```bash
# 验证测试环境配置是否正确
python scripts/verify_env_config.py --env test --quick
```

**预期输出**:
```
✓ Passed: 10+
⚠ Warnings: 0-3 (可忽略)
✗ Errors: 0

✅ All checks passed! Environment is ready.
```

如果有错误，按照提示修复后重新验证。

---

## 第三步：启动测试环境 (2分钟)

```bash
# 方式一：双击批处理文件（推荐）
start_test_env.bat

# 方式二：命令行启动
python scripts\start_service.py --env test --service all
```

**启动过程**:
1. 自动检测并释放端口（如果被占用）
2. 后端启动在 `8100` 端口
3. 前端启动在 `3101` 端口
4. 显示访问地址

**访问测试环境**:
- **前端**: http://localhost:3101
- **API文档**: http://localhost:8100/docs

---

## 第四步：验证代码变更 (实际使用)

### 场景示例：修复了需求分析模块的Bug

```bash
# 1. 开发环境继续运行 (8000/3001) - 无需停止

# 2. 创建功能分支
git checkout -b bugfix/requirement-analysis-fix

# 3. 修改代码
# 编辑: intelligent_project_analyzer/agents/requirement_analyst.py

# 4. 启动测试环境验证修复
start_test_env.bat  # 使用 8100/3101

# 5. 在测试环境测试修复
# 访问 http://localhost:3101
# 输入测试用例，验证bug是否修复

# 6. 验证通过，停止测试环境
# 按 Ctrl+C停止

# 7. 提交代码
git add .
git commit -m "fix: requirement analysis null pointer"

# 8. 合并主分支
git checkout main
git merge bugfix/requirement-analysis-fix
```

---

## 常用命令速查

### 端口管理

```bash
# 检查端口是否可用
python scripts/utils/port_manager.py check 8100

# 查看测试环境端口冲突
python scripts/utils/port_manager.py conflicts --env test

# 手动释放端口
python scripts/utils/port_manager.py release 8100
```

### 环境切换

```bash
# 开发环境（8000/3001）
start_backend_main.bat
start_frontend_main.bat

# 测试环境（8100/3101）
start_test_env.bat

# 或使用统一脚本
python scripts\start_service.py --env development --service all
python scripts\start_service.py --env test --service all
```

### 配置验证

```bash
# 验证单个环境
python scripts/verify_env_config.py --env test

# 验证所有环境
python scripts/verify_env_config.py --all
```

---

## 端口分配表

| 环境名称 | 后端端口 | 前端端口 | 启动脚本 |
|---------|---------|---------|---------|
| Development | 8000 | 3001 | `start_backend_main.bat` |
| Test | 8100 | 3101 | `start_test_env.bat` |
| Staging | 8200 | 3201 | `python scripts\start_service.py --env staging --service all` |
| Production | 8000 | 3001 | `python scripts\start_service.py --env production --service all` |

---

## 常见问题

### Q1: 端口被占用怎么办？

**自动处理**:
```bash
# 启动脚本会自动释放Python/Uvicorn进程占用的端口
start_test_env.bat
```

**手动处理**:
```bash
# 检查占用
python scripts/utils/port_manager.py check 8100

# 释放端口
python scripts/utils/port_manager.py release 8100
```

### Q2: 如何确认当前运行的是哪个环境？

**检查端口**:
- 开发环境: http://localhost:3001
- 测试环境: http://localhost:3101

**检查日志**:
```bash
# 开发环境日志
logs/server.log

# 测试环境日志
logs/test_server.log
```

**检查数据库**:
```bash
# 开发环境数据
data/dev/archived_sessions.db

# 测试环境数据
data/test/archived_sessions.db
```

### Q3: 测试环境数据会污染开发环境吗？

**不会！** 三层隔离保证数据安全：

1. **数据库隔离**: `data/dev/` vs `data/test/`
2. **Redis隔离**: DB 0 vs DB 1（或内存模式）
3. **日志隔离**: `logs/server.log` vs `logs/test_server.log`

### Q4: 如何同时运行开发和测试环境？

```bash
# 终端1: 启动开发环境
start_backend_main.bat

# 终端2: 启动测试环境
start_test_env.bat

# 浏览器
# Tab1: http://localhost:3001  (开发环境)
# Tab2: http://localhost:3101  (测试环境)
```

---

## 高级案例：A/B 模型对比

**场景**: 对比 GPT-4o-mini 和 GPT-4o 的效果差异

```bash
# 1. 配置开发环境使用 mini 模型
# 编辑 .env.development:
OPENAI_DEFAULT_MODEL=gpt-4o-mini

# 2. 配置测试环境使用完整模型
# 编辑 .env.test:
OPENAI_DEFAULT_MODEL=gpt-4o

# 3. 同时启动两个环境
start_backend_main.bat    # 终端1
start_test_env.bat         # 终端2

# 4. 浏览器打开两个窗口并排
# 左侧: http://localhost:3001  (gpt-4o-mini)
# 右侧: http://localhost:3101  (gpt-4o)

# 5. 输入相同的需求，对比输出质量和响应时间
```

---

## 下一步

- 📖 **完整指南**: 查看 [docs/MULTI_ENV_GUIDE.md](docs/MULTI_ENV_GUIDE.md)
- 🔧 **工作流示例**: [docs/MULTI_ENV_GUIDE.md#典型工作流](docs/MULTI_ENV_GUIDE.md#典型工作流)
- 🐛 **故障排查**: [docs/MULTI_ENV_GUIDE.md#故障排查](docs/MULTI_ENV_GUIDE.md#故障排查)
- 🎯 **最佳实践**: [docs/MULTI_ENV_GUIDE.md#最佳实践](docs/MULTI_ENV_GUIDE.md#最佳实践)

---

**配置完成后，就可以安全地验证代码变更了！** 🎉
