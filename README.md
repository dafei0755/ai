# 🎨 Intelligent Project Analyzer

> 基于 LangGraph 的多智能体设计项目分析系统
> 智能化设计项目需求分析 | 多专家协作 | 全流程质量保障

[![Version](https://img.shields.io/badge/version-v7.122-blue.svg)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![CI/CD](https://github.com/dafei0755/ai/actions/workflows/ci.yml/badge.svg)](https://github.com/dafei0755/ai/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/dafei0755/ai/branch/main/graph/badge.svg)](https://codecov.io/gh/dafei0755/ai)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.57+-orange.svg)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)

---

## ⚠️ 开发者必读

**修改代码前必须阅读**：
- 🔥 **[核心开发规范](.github/DEVELOPMENT_RULES_CORE.md)** - 200行精简版，AI工具优先加载
- 📚 [完整开发规范](.github/DEVELOPMENT_RULES.md) - 深度查阅特定章节
- ✅ [变更检查清单](.github/PRE_CHANGE_CHECKLIST.md) - 修改前强制流程
- 📖 [历史修复记录](.github/historical_fixes/) - 5+ 精选bug修复案例

**强制流程**：诊断问题 → 查阅历史 → 报告方案 → 获得批准 → 执行修改 → 更新文档

---

## 📋 项目简介

**Intelligent Project Analyzer** 是一个专为设计项目打造的智能分析系统。系统采用 **LangGraph 多智能体协作**架构，结合大语言模型（LLM）的推理能力，实现从需求分析到专家协作、质量审核的全流程自动化。

### ✨ 核心特性

- **🤖 动态多智能体协作** - 6大核心Agent（需求分析、项目总监、专家协作、质量审核、报告生成、追问系统）
- **💬 智能人机交互** - 校准问卷、需求确认、任务审批、雷达图维度混合策略（70%固定+30%LLM动态）
- **🔍 外部搜索工具集成** - 4种搜索工具（Tavily网络搜索、Bocha中文AI、ArXiv学术论文、RAGFlow知识库）v7.122 数据流优化：问卷→搜索→概念图
- **🛡️ 四阶段质量审核** - 红队批判 → 蓝队辩护 → 评委裁决 → 甲方终审
- **⚡ 性能优化** - WebSocket实时推送（延迟↓40倍）、Redis缓存（响应↑60%）、性能监控系统
- **🎨 双模式分析** - 普通模式（快速验证）& 深度思考模式（多角度可视化）v7.110 配置驱动架构
- **🔌 扩展能力** - 多模态输入（文本/PDF/图片OCR）、WordPress SSO

### 🎯 适用场景

室内设计 | 产品设计 | 品牌设计 | 咨询服务

### 🏆 项目优势

- ✅ **降低沟通成本** - 自动化需求分析
- ✅ **提升专业度** - 多角色专家协作
- ✅ **保障质量** - 四阶段审核机制
- ✅ **提高效率** - 2-3天缩短至30分钟
- ✅ **可追溯性** - 完整过程记录

---

## 🚀 快速启动

📖 **详细安装指南**: [QUICKSTART.md](QUICKSTART.md)

### 一键启动（Windows）

```cmd
# 配置 .env 文件后直接运行
start_services.bat
```

### 分步启动

```bash
# 1. 后端服务
python -B scripts\run_server_production.py  # Python 3.13+ Windows
python -B scripts\run_server.py  # 开发模式（热重载）
python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000 --reload  # Python 3.10-3.12

# 2. 前端服务
cd frontend-nextjs && npm run dev

# 访问
# 前端: http://localhost:3000
# API: http://localhost:8000/docs
```

### Docker 部署

```bash
docker-compose up -d
```

---

## 📚 完整文档

| 类别 | 文档 | 说明 |
|------|------|------|
| **入门** | [QUICKSTART.md](QUICKSTART.md) | 5分钟快速启动 |
| **贡献** | [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南和开发规范 |
| **架构** | [docs/README.md](docs/README.md) | 完整文档导航 |
| **更新** | [CHANGELOG.md](CHANGELOG.md) | 版本历史 |
| **紧急** | [EMERGENCY_RECOVERY.md](EMERGENCY_RECOVERY.md) | 快速恢复到历史版本 |
| **备份** | [BACKUP_GUIDE.md](BACKUP_GUIDE.md) | 多版本备份系统 |
| **测试** | [README_TESTING.md](README_TESTING.md) | 测试指南 |

### 核心开发文档

- 🔥 [核心开发规范](.github/DEVELOPMENT_RULES_CORE.md) - AI工具优先加载
- 📚 [完整开发规范](.github/DEVELOPMENT_RULES.md) - 详细指南
- ✅ [变更检查清单](.github/PRE_CHANGE_CHECKLIST.md) - 修改前强制流程
- 📖 [历史修复案例](.github/historical_fixes/) - 5+ 精选修复记录

### 功能文档

- [WordPress SSO集成](docs/features/wordpress-sso/) - 单点登录完整指南
- [问卷系统](docs/archive/bugfixes/questionnaire/) - 校准问卷实现
- [搜索引用功能](docs/V7.120_SEARCH_REFERENCES_RELEASE.md) - v7.120 外部搜索工具集成
- [搜索查询数据利用优化](docs/V7.121_SEARCH_QUERY_DATA_UTILIZATION.md) - v7.121 充分利用用户输入和问卷数据 🆕
- [性能优化](docs/archive/bugfixes/backend/) - 性能监控与优化

---

## 🛠️ 技术栈

**后端**: FastAPI 0.115+ | LangGraph 0.2.57+ | LangChain | SQLite/PostgreSQL/Redis
**前端**: Next.js 15 | React 18 | TypeScript | Tailwind CSS
**DevOps**: Docker | GitHub Actions | PerformanceMonitor

---

## 🧪 测试

```bash
pytest                      # 运行所有测试
pytest --cov=intelligent_project_analyzer --cov-report=html  # 覆盖率报告
pytest -m "not llm"         # 跳过LLM调用测试
```

测试覆盖率: 80%+

---

## ❓ 常见问题

### Q: Python 3.13 Windows 用户启动失败？
A: 必须使用 `run_server_production.py`，详见 [Playwright修复文档](.github/historical_fixes/playwright_python313_windows_fix.md)

### Q: 端口被占用？
```bash
taskkill /F /IM python.exe  # 终止后端
Get-Process node | Stop-Process -Force  # 终止前端
```

### Q: 如何切换LLM服务商？
编辑 `.env` 文件配置 `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY`

更多问题参见 [FAQ](docs/getting-started/FAQ.md)

---

## 🤝 贡献

我们欢迎所有贡献！请先阅读 [贡献指南](CONTRIBUTING.md)。

**贡献流程**: Fork → 创建分支 → 遵循规范 → 添加测试 → 更新文档 → 提交PR

---

## 🗺️ 路线图

**近期（2025 Q1）**: CI/CD完善 | 更多LLM支持 | 前端优化 | 多语言支持
**中期（2025 Q2-Q3）**: 移动端 | 团队协作 | 版本对比 | 导出PPT/Word
**长期愿景**: SaaS化 | AI训练优化 | 行业定制 | 开放API生态

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

## 🔗 相关链接

- 📺 [在线演示](https://ai.ucppt.com)（需 WordPress 登录）
- 🐛 [问题反馈](https://github.com/dafei0755/ai/issues)
- 💬 [讨论区](https://github.com/dafei0755/ai/discussions)
- 📖 [完整文档](docs/README.md)

---

<div align="center">

**当前版本**: v7.116.1 | **最后更新**: 2026-01-02

⭐ 如果这个项目对你有帮助，请给我们一个 Star！

Made with ❤️ by AI Assistant & Contributors

</div>
