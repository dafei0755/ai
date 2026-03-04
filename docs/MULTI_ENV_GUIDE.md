# 🌐 多环境开发指南 (v8.1+)

> 支持开发、测试、预发布环境并行运行，代码变更零风险验证

---

## 📋 目录

- [快速开始](#快速开始)
- [环境配置](#环境配置)
- [典型工作流](#典型工作流)
- [端口管理](#端口管理)
- [数据隔离](#数据隔离)
- [故障排查](#故障排查)
- [最佳实践](#最佳实践)

---

## 🚀 快速开始

### 场景: 修改代码后想验证，但不想停止开发环境

```bash
# 1. 开发环境继续运行 (8000/3001)
# 无需任何操作

# 2. 启动测试环境验证变更
start_test_env.bat

# 3. 测试完成后停止（Ctrl+C）
# 开发环境不受影响
```

---

## ⚙️ 环境配置

### 环境类型

| 环境 | 用途 | 后端端口 | 前端端口 | 配置文件 |
|------|------|----------|----------|---------|
| **Development** | 日常开发 | 8000 | 3001 | `.env.development` |
| **Test** | 代码验证 | 8100 | 3101 | `.env.test` |
| **Staging** | 预发布测试 | 8200 | 3201 | `.env.staging` |
| **Production** | 生产部署 | 8000 | 3001 | `.env.production` |

### 配置文件创建

```bash
# 1. 复制示例配置
copy .env.development.example .env.development
copy .env.test.example .env.test
copy .env.production.example .env.production

# 2. 编辑配置文件填写API密钥
# 每个环境可以使用不同的LLM模型/API密钥
```

### 配置优先级

```
环境变量 > .env.{APP_ENV} > .env > 代码默认值
```

示例:
```bash
# 设置环境变量（最高优先级）
set APP_ENV=test
set API_PORT=8100

# 启动服务（会使用上述环境变量）
python scripts\start_service.py --env test
```

---

## 🔄 典型工作流

### 工作流 1: Bug 修复验证

```bash
# 场景: 修复了需求分析模块的bug

# 1. 开发环境正在运行（8000/3001）
# 2. 创建功能分支
git checkout -b bugfix/requirement-analysis-fix

# 3. 修改代码
# intelligent_project_analyzer/agents/requirement_analyst.py

# 4. 启动测试环境验证
start_test_env.bat  # 自动使用 8100/3101

# 5. 访问 http://localhost:3101 测试修复
# 6. 验证通过，提交代码
git add .
git commit -m "fix: requirement analysis logic"

# 7. 停止测试环境（Ctrl+C）
# 8. 合并到主分支
git checkout main
git merge bugfix/requirement-analysis-fix
```

### 工作流 2: 新功能开发

```bash
# 场景: 开发新的搜索功能

# 1. 创建功能分支
git checkout -b feature/new-search-engine

# 2. 在开发环境开发（8000/3001）
# 3. 阶段性验证：启动测试环境
python scripts\start_service.py --env test --service all

# 4. 测试环境验证新功能
# 5. 反复迭代：修改代码 → 重启测试环境 → 验证
# 6. 开发环境持续运行，可随时切回调试

# 7. 功能完成，运行完整测试套件
python -m pytest tests/

# 8. 提交PR，等待CI/CD验证
# 9. 合并主分支
```

### 工作流 3: A/B 对比测试

```bash
# 场景: 测试两个LLM模型的效果差异

# 1. 开发环境使用 GPT-4o-mini（8000）
# 编辑 .env.development:
OPENAI_DEFAULT_MODEL=gpt-4o-mini

# 2. 测试环境使用 GPT-4o（8100）
# 编辑 .env.test:
OPENAI_DEFAULT_MODEL=gpt-4o

# 3. 同时启动两个环境
start_backend_main.bat    # 终端1: 8000
start_test_env.bat         # 终端2: 8100

# 4. 浏览器打开两个标签页
# Tab 1: http://localhost:3001  (GPT-4o-mini)
# Tab 2: http://localhost:3101  (GPT-4o)

# 5. 同时输入相同需求，对比结果质量
```

---

## 🔌 端口管理

### 自动端口释放

启动脚本会自动检测并释放端口（仅释放 Python/Uvicorn/Node 进程）：

```bash
# 自动释放端口并启动（推荐）
python scripts\start_service.py --env test --service all

# 禁用自动释放（手动管理端口）
python scripts\start_service.py --env test --service all --no-auto-release
```

### 手动端口管理

```bash
# 检查端口是否可用
python scripts/utils/port_manager.py check 8100

# 查看环境端口冲突
python scripts/utils/port_manager.py conflicts --env test

# 释放端口（安全，只释放指定进程）
python scripts/utils/port_manager.py release 8100

# 强制释放（危险，会终止所有占用端口的进程）
python scripts/utils/port_manager.py release 8100 --force

# 为环境分配端口
python scripts/utils/port_manager.py allocate --env test
```

### 端口被占用时的自动降级

如果默认端口被占用，系统会自动分配同范围内的其他端口：

```
Test环境默认: 8100 → 被占用
自动降级: 8101, 8102, ..., 8109
```

---

## 💾 数据隔离

### 数据库隔离

每个环境使用独立的数据库文件：

```
data/
├── dev/
│   └── archived_sessions.db  # 开发环境数据
├── test/
│   └── archived_sessions.db  # 测试环境数据（或内存模式）
└── archived_sessions.db       # 生产环境数据
```

**配置** (`.env.test`):
```env
DATABASE_URL=sqlite:///./data/test/archived_sessions.db
# 或使用内存模式（推荐测试环境）
# DATABASE_URL=sqlite:///:memory:
```

### Redis 隔离

每个环境使用不同的 Redis DB 索引：

```env
# 开发环境 (.env.development)
REDIS_DB=0

# 测试环境 (.env.test)
REDIS_DB=1

# 预发布环境 (.env.staging)
REDIS_DB=2

# 或启用内存模式（仅测试环境）
REDIS_MEMORY_ONLY=true
```

### 日志隔离

每个环境使用独立的日志文件：

```
logs/
├── server.log           # 开发环境
├── test_server.log      # 测试环境
└── production.log       # 生产环境
```

**配置** (`.env.test`):
```env
LOG_FILE_PATH=logs/test_server.log
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true  # JSON格式，便于自动化测试解析
```

---

## 🔧 故障排查

### 问题 1: 端口已被占用

**症状**: 启动失败，提示 "Port 8100 is already in use"

**排查**:
```bash
# 1. 检查占用端口的进程
python scripts/utils/port_manager.py check 8100

# 2. 释放端口
python scripts/utils/port_manager.py release 8100

# 3. 或使用自动释放模式启动
python scripts\start_service.py --env test --service all
```

### 问题 2: 配置文件不存在

**症状**: 启动时提示 "Environment config file not found: .env.test"

**解决**:
```bash
# 复制示例配置
copy .env.test.example .env.test

# 编辑配置文件
notepad .env.test
```

### 问题 3: 前端无法连接后端

**症状**: 前端页面显示 "Network Error"

**排查**:
```bash
# 1. 确认后端已启动
python scripts/utils/port_manager.py check 8100

# 2. 检查前端环境变量配置
# 确保 NEXT_PUBLIC_API_BASE_URL 正确
# .env.test: NEXT_PUBLIC_API_BASE_URL=http://localhost:8100

# 3. 访问后端健康检查
# 浏览器打开: http://localhost:8100/docs
```

### 问题 4: 测试环境数据污染开发环境

**症状**: 测试数据出现在开发环境

**原因**: 数据库路径配置错误

**解决**:
```env
# .env.test 中确保配置
DATABASE_URL=sqlite:///./data/test/archived_sessions.db
REDIS_DB=1  # 不要使用 0
```

### 问题 5: Python 导入错误

**症状**: `ModuleNotFoundError: No module named 'scripts.utils'`

**解决**:
```bash
# 确保从项目根目录运行
cd d:\11-20\langgraph-design

# 或使用绝对路径
python d:\11-20\langgraph-design\scripts\start_service.py --env test
```

---

## ✅ 最佳实践

### 1. 环境隔离原则

✅ **推荐**:
```bash
# 开发环境：日常开发，数据可以乱
# 测试环境：验证变更，使用内存模式或独立DB
# 生产环境：真实数据，绝不混用
```

❌ **避免**:
```bash
# 所有环境共用一个数据库
# 测试环境修改生产配置
# 开发环境使用生产API密钥
```

### 2. Git 工作流集成

每次修改代码前：

```bash
# Step 1: 创建功能分支
git checkout -b feature/your-feature

# Step 2: 修改代码

# Step 3: 测试环境验证
start_test_env.bat

# Step 4: 运行测试套件
python -m pytest tests/

# Step 5: 提交并创建PR
git add .
git commit -m "feat: your feature"
git push origin feature/your-feature
```

### 3. 配置管理

```bash
# ✅ 推荐：环境配置文件分离
.env.development  # 开发配置
.env.test         # 测试配置
.env.production   # 生产配置

# ✅ 推荐：敏感信息使用环境变量
export OPENAI_API_KEY=sk-xxx
export DATABASE_URL=postgresql://...

# ❌ 避免：硬编码敏感信息
# OPENAI_API_KEY=sk-abc123...  # 不要提交到Git
```

### 4. 端口规划

预留端口范围，避免冲突：

```
Development: 8000-8009 (后端), 3001-3009 (前端)
Test:        8100-8109 (后端), 3101-3109 (前端)
Staging:     8200-8209 (后端), 3201-3209 (前端)
Production:  8000 (固定), 3001 (固定)
```

### 5. 日志管理

```env
# Development: 详细日志，便于调试
LOG_LEVEL=DEBUG
STRUCTURED_LOGGING=false
LOG_SAMPLE_RATE=1.0

# Test: 结构化日志，便于自动化解析
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true
LOG_SAMPLE_RATE=1.0

# Production: 精简日志，采样记录
LOG_LEVEL=WARNING
STRUCTURED_LOGGING=true
LOG_SAMPLE_RATE=0.1
```

### 6. 性能优化

测试环境可以使用更便宜的模型：

```env
# .env.test
OPENAI_DEFAULT_MODEL=gpt-4o-mini  # 便宜30倍
DIMENSION_LLM_MODEL=gpt-4o-mini
REDIS_MEMORY_ONLY=true            # 避免I/O开销
```

---

## 📚 相关文档

- [QUICKSTART.md](QUICKSTART.md) - 快速启动指南
- [DEVELOPMENT_RULES_CORE.md](.github/DEVELOPMENT_RULES_CORE.md) - 开发规范
- [README_TESTING.md](README_TESTING.md) - 测试指南
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南

---

## 🆘 获取帮助

遇到问题？

1. 查看 [故障排查](#故障排查) 章节
2. 运行端口管理工具诊断: `python scripts/utils/port_manager.py conflicts --env test`
3. 提交 Issue: [GitHub Issues](https://github.com/dafei0755/ai/issues)
4. 讨论区: [GitHub Discussions](https://github.com/dafei0755/ai/discussions)

---

**Happy Coding! 🎉**
