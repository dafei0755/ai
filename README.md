# 🎨 Intelligent Project Analyzer

> 基于 LangGraph 的多智能体设计项目分析系统

[![Version](https://img.shields.io/badge/version-v7.104-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

---

## ⚠️ 开发者必读

**修改代码前必须阅读**：
- 🔥 **[核心开发规范](.github/DEVELOPMENT_RULES_CORE.md)** - 200行精简版，AI工具优先加载
- 📚 [完整开发规范](.github/DEVELOPMENT_RULES.md) - 深度查阅特定章节
- ✅ [变更检查清单](.github/PRE_CHANGE_CHECKLIST.md) - 修改前强制流程
- 📖 [历史修复记录](.github/historical_fixes/) - 77+ bug修复案例

**强制流程**：诊断问题 → 查阅历史 → 报告方案 → 获得批准 → 执行修改 → 更新文档

---

## 📋 项目简介

**Intelligent Project Analyzer** 专为设计项目（室内设计、产品设计、品牌设计等）打造的智能分析系统，采用 **LangGraph多智能体协作**架构，实现从需求分析到专家协作、质量审核的全流程自动化。

### 核心特性

- 🤖 **动态多智能体系统** - 自动选择5-10位专业角色协作
- 🔄 **人机交互设计** - 校准问卷、需求确认、任务审批
- 🛡️ **四阶段质量保障** - 红队批判 → 蓝队辩护 → 评委裁决 → 甲方终审
- ⚡ **实时进度推送** - WebSocket推送，延迟降低40倍（vs 轮询）
- 📊 **智能追问系统** - 基于LLM的追问推荐

### 最新版本

**v7.104 (2025-12-29)** - Config目录优化 + 性能监控系统
- ✅ Config目录全面对齐v7.19专家工厂（8个配置文件升级）
- ✅ 6个核心节点升级为LangGraph StateGraph Agent
- ✅ 性能监控系统（PerformanceMonitor）
- 📝 [完整更新日志](CHANGELOG.md) | [v7.16架构文档](docs/V716_AGENT_STATE_GRAPHS.md)

---

## 🚀 快速启动

### 一键启动（推荐）

```cmd
# 同时启动后端和前端
start_services.bat
```

### 分步启动

**后端服务**：
```cmd
# 推荐：使用增强版启动脚本（完整日志记录）
start_backend_enhanced.bat

# 或直接启动
cd d:\11-20\langgraph-design
python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000
```

**前端服务**：
```cmd
cd frontend-nextjs
npm run dev
```

**访问应用**：http://localhost:3000（端口占用时自动切换到3001）

### 日志查看

```powershell
# 实时监控主日志（推荐在 VS Code 中打开避免乱码）
Get-Content logs\server.log -Wait -Tail 100 -Encoding UTF8

# SSO调试日志
Get-Content logs\auth.log -Wait -Tail 50 -Encoding UTF8

# 错误日志
Get-Content logs\errors.log -Tail 50 -Encoding UTF8
```

---

## 📦 安装依赖

### 后端依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填写必需的 API Keys
```

### 前端依赖

```bash
cd frontend-nextjs
npm install
```

### 可选服务

- **Redis**（会话管理，推荐生产环境）
- **Celery**（异步任务队列，多用户并发）
- **RAGFlow**（知识库检索，暂未启用）

---

## 📚 详细文档

### 核心文档
- [项目架构](CLAUDE.md) - 完整系统架构说明
- [更新日志](CHANGELOG.md) - 完整版本历史
- [部署指南](docs/DEPLOYMENT.md) - 生产环境部署

### WordPress SSO集成
- ⭐ [快速开始](V3.0.20_QUICK_START.md) - 5分钟快速部署
- ⭐ [部署指南](WORDPRESS_SSO_V3.0.20_DEPLOYMENT_GUIDE.md) - 完整部署流程
- 📁 [技术文档](docs/wordpress/) - 跨域Cookie、架构设计等

### 开发指南
- [日志系统指南](LOGGING_GUIDE.md) - SSO调试、错误排查
- [备份指南](BACKUP_GUIDE.md) - 每天两次自动备份配置
- [测试指南](tests/README.md) - 单元测试、集成测试
- [API文档](docs/API.md) - RESTful API参考

---

## 🤝 贡献指南

1. Fork项目并创建功能分支
2. 遵循代码风格（Python: Black+isort，TypeScript: ESLint+Prettier）
3. 添加测试，确保覆盖率≥80%
4. 修改配置/核心逻辑时同步更新文档
5. 提交PR需附测试结果

**注意**：修改前务必遵循 [变更检查清单](.github/PRE_CHANGE_CHECKLIST.md) 强制流程！

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 🔗 相关链接

- [在线演示](https://ai.ucppt.com)（需WordPress登录）
- [问题反馈](https://github.com/your-repo/issues)
- [更新日志](CHANGELOG.md)

---

**当前版本**: v7.104 | **最后更新**: 2025-12-29
