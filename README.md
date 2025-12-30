# 🎨 Intelligent Project Analyzer

> 基于 LangGraph 的多智能体设计项目分析系统  
> 智能化设计项目需求分析 | 多专家协作 | 全流程质量保障

[![Version](https://img.shields.io/badge/version-v7.104-blue.svg)](CHANGELOG.md)
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
- 📖 [历史修复记录](.github/historical_fixes/) - 77+ bug修复案例

**强制流程**：诊断问题 → 查阅历史 → 报告方案 → 获得批准 → 执行修改 → 更新文档

---

## 📋 项目简介

**Intelligent Project Analyzer** 是一个专为设计项目（室内设计、产品设计、品牌设计等）打造的智能分析系统。系统采用 **LangGraph 多智能体协作**架构，结合大语言模型（LLM）的推理能力，实现从需求分析到专家协作、质量审核的全流程自动化。

### ✨ 核心特性

#### 🤖 智能体系统
- **动态多智能体协作** - 根据项目需求自动选择 5-10 位专业角色
- **六大核心 Agent** - LangGraph StateGraph 架构（v7.16+）
  - RequirementsAnalyst（需求分析师）
  - ProjectDirector（项目总监）
  - ExpertCollaboration（专家协作）
  - QualityReview（质量审核）
  - ReportGeneration（报告生成）
  - FollowupAgent（追问系统）

#### 💬 人机交互
- **智能校准问卷** - 动态生成 3-5 个关键问题
- **需求确认环节** - 确保理解一致，避免返工
- **任务审批机制** - 用户控制分析进度和深度
- **追问系统** - 基于 LLM 的智能追问推荐

#### 🛡️ 质量保障
- **四阶段质量审核**
  1. 红队批判（Red Team）- 发现潜在问题
  2. 蓝队辩护（Blue Team）- 论证可行性
  3. 评委裁决（Judge）- 独立评估打分
  4. 甲方终审（Client Review）- 最终确认
- **自动化测试覆盖率 80%+**

#### ⚡ 性能优化
- **实时进度推送** - WebSocket，延迟降低 40 倍（vs 轮询）
- **性能监控系统** - PerformanceMonitor 自动记录
- **Redis 缓存** - 会话管理，响应速度提升 60%
- **并发处理** - Celery 异步任务队列

#### 🔌 扩展能力
- **多模态输入** - 支持文本、PDF、图片（OCR）
- **外部工具集成** - Tavily 搜索、Arxiv 学术检索
- **WordPress SSO** - 单点登录，无缝集成现有系统
- **RAGFlow 知识库**（可选）- 专业知识增强

### 🎯 适用场景

- **室内设计项目** - 住宅、办公、商业空间设计需求分析
- **产品设计项目** - 用户需求挖掘、功能规划、设计方向
- **品牌设计项目** - 品牌定位、视觉策略、传播方案
- **咨询服务** - 设计顾问、项目管理、可行性分析

### 🏆 项目优势

- ✅ **降低沟通成本** - 自动化需求分析，减少反复沟通
- ✅ **提升专业度** - 多角色专家协作，覆盖全方位视角
- ✅ **保障质量** - 四阶段审核机制，确保方案可行性
- ✅ **提高效率** - 从 2-3 天缩短至 30 分钟完成初步分析
- ✅ **可追溯性** - 完整的分析过程记录和日志系统

### 最新版本

**v7.104 (2025-12-29)** - Config目录优化 + 性能监控系统
- ✅ Config目录全面对齐v7.19专家工厂（8个配置文件升级）
- ✅ 6个核心节点升级为LangGraph StateGraph Agent
- ✅ 性能监控系统（PerformanceMonitor）
- 📝 [完整更新日志](CHANGELOG.md) | [v7.16架构文档](docs/V716_AGENT_STATE_GRAPHS.md)

---

## 🚀 快速启动

### 方式一：一键启动（Windows，推荐）

```cmd
# 同时启动后端和前端
start_services.bat
```

### 方式二：分步启动

#### 1. 启动后端服务

```bash
# 方法1: 使用增强版启动脚本（推荐，完整日志）
start_backend_enhanced.bat

# 方法2: 直接启动
python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000 --reload

# 方法3: 生产环境
uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000 --workers 4
```

**后端启动成功标志**：
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

访问 API 文档：http://localhost:8000/docs

#### 2. 启动前端服务

```bash
cd frontend-nextjs

# 开发模式
npm run dev

# 生产构建
npm run build
npm run start
```

**前端启动成功标志**：
```
- Local:        http://localhost:3000
- Network:      http://192.168.x.x:3000
```

#### 3. 访问应用

- **前端界面**: http://localhost:3000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

> 💡 **提示**：端口占用时会自动切换（前端 3000→3001，后端保持 8000）

### 方式三：Docker 部署（推荐生产环境）

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 使用示例

#### 基础使用流程

1. **访问系统**：打开 http://localhost:3000
2. **输入需求**：描述你的设计项目需求
   ```
   示例：我需要设计一个150平米的现代简约风格住宅，
   三室两厅，预算30万，希望注重收纳和采光。
   ```
3. **校准问卷**：回答 3-5 个关键问题（可跳过）
4. **确认需求**：审核系统分析的需求理解
5. **专家协作**：系统自动选择专家团队并生成分析
6. **查看报告**：获取完整的项目分析报告

#### API 调用示例

```python
import requests

# 创建分析会话
response = requests.post(
    "http://localhost:8000/api/v1/sessions",
    json={
        "user_input": "设计一个现代咖啡馆，面积120平米",
        "user_id": "user_001"
    }
)
session_id = response.json()["session_id"]

# 获取分析结果
result = requests.get(f"http://localhost:8000/api/v1/sessions/{session_id}")
print(result.json())
```

更多 API 示例参见 [API 文档](docs/API.md)

### 日志查看与调试

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

### 环境要求

- **Python**: 3.10+ （推荐 3.11）
- **Node.js**: 18+ （前端需要）
- **Git**: 用于版本管理
- **可选**: Redis（生产环境推荐）

### 后端依赖

```bash
# 克隆项目
git clone https://github.com/dafei0755/ai.git
cd ai

# 创建虚拟环境（推荐）
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑 .env 文件，填写必需的 API Keys
```

**必需的环境变量**：
```env
# OpenAI API（或兼容的其他服务）
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1

# 可选：其他 LLM 服务
ANTHROPIC_API_KEY=your_key
GOOGLE_API_KEY=your_key

# 外部工具（可选）
TAVILY_API_KEY=your_key  # 网络搜索
ARXIV_API_KEY=your_key   # 学术检索

# 数据库（可选，默认使用 SQLite）
REDIS_URL=redis://localhost:6379
```

### 前端依赖

```bash
cd frontend-nextjs

# 安装依赖
npm install
# 或使用 yarn
yarn install

# 配置环境变量
copy .env.local.example .env.local
# 编辑 .env.local 设置后端 API 地址
```

**前端环境变量**：
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### 数据库初始化

```bash
# SQLite（默认，无需额外配置）
# 首次运行会自动创建数据库

# Redis（可选，用于会话管理）
# Windows: 使用 WSL 或 Docker
docker run -d -p 6379:6379 redis:alpine

# PostgreSQL（可选，生产环境推荐）
# 创建数据库后在 .env 中配置
DATABASE_URL=postgresql://user:password@localhost/dbname
```

### 可选服务

- **Redis**（会话管理，推荐生产环境）
- **Celery**（异步任务队列，多用户并发）
- **RAGFlow**（知识库检索，暂未启用）

---

## � 项目结构

```
langgraph-design/
├── intelligent_project_analyzer/    # 后端核心代码
│   ├── agents/                     # 智能体实现
│   │   ├── requirements_analyst.py # 需求分析师
│   │   ├── project_director.py     # 项目总监
│   │   └── ...
│   ├── api/                        # FastAPI 接口
│   │   ├── server.py              # 主服务器
│   │   └── routes/                # 路由模块
│   ├── core/                       # 核心功能
│   │   ├── state.py               # 状态管理
│   │   ├── prompt_manager.py      # 提示词管理
│   │   └── ...
│   ├── workflow/                   # 工作流定义
│   │   └── main_workflow.py       # LangGraph 工作流
│   ├── services/                   # 业务服务
│   ├── utils/                      # 工具函数
│   └── tests/                      # 单元测试
├── frontend-nextjs/                # Next.js 前端
│   ├── components/                 # React 组件
│   ├── app/                        # 页面路由
│   ├── lib/                        # 工具库
│   └── public/                     # 静态资源
├── docs/                           # 文档目录
│   ├── DEPLOYMENT.md              # 部署指南
│   ├── AGENT_ARCHITECTURE.md      # 架构设计
│   └── ...
├── scripts/                        # 脚本工具
├── .github/                        # GitHub 配置
│   ├── workflows/                 # CI/CD 配置
│   └── DEVELOPMENT_RULES.md       # 开发规范
├── requirements.txt                # Python 依赖
├── CHANGELOG.md                    # 更新日志
└── README.md                       # 本文件
```

---

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_integration.py

# 查看覆盖率
pytest --cov=intelligent_project_analyzer --cov-report=html

# 只运行快速测试（跳过 LLM 调用）
pytest -m "not llm"
```

### 测试分类

- **单元测试** - 测试单个函数/类
- **集成测试** - 测试组件交互
- **端到端测试** - 测试完整流程

---

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI 0.115+
- **工作流**: LangGraph 0.2.57+
- **LLM**: LangChain + OpenAI/Anthropic/Google
- **数据库**: SQLite (默认) / PostgreSQL / Redis
- **任务队列**: Celery (可选)

### 前端
- **框架**: Next.js 15
- **UI**: React 18 + TypeScript
- **样式**: Tailwind CSS
- **状态管理**: Zustand
- **通信**: Axios + WebSocket

### DevOps
- **容器**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **监控**: 自研 PerformanceMonitor
- **日志**: Python logging + 文件日志

---

## �📚 详细文档

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

我们欢迎所有形式的贡献！在开始之前，请：

### 贡献流程

1. **Fork 项目**并创建功能分支
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **遵循代码规范**
   - Python: Black + isort + Flake8
   - TypeScript: ESLint + Prettier
   - 提交信息: [约定式提交](https://www.conventionalcommits.org/)

3. **添加测试**
   - 确保测试覆盖率 ≥ 80%
   - 新功能必须包含测试用例

4. **更新文档**
   - 修改配置/核心逻辑时同步更新文档
   - 添加必要的注释和文档字符串

5. **提交 Pull Request**
   - 描述清楚变更内容和原因
   - 附上测试结果截图
   - 确保 CI/CD 检查通过

### 开发规范

⚠️ **强制流程**：修改前必须阅读
- 🔥 [核心开发规范](.github/DEVELOPMENT_RULES_CORE.md) - 200 行精简版
- 📚 [完整开发规范](.github/DEVELOPMENT_RULES.md) - 详细指南
- ✅ [变更检查清单](.github/PRE_CHANGE_CHECKLIST.md) - 修改前检查
- 📖 [历史修复记录](.github/historical_fixes/) - 77+ bug 修复案例

**标准流程**：
```
诊断问题 → 查阅历史 → 报告方案 → 获得批准 → 执行修改 → 更新文档
```

### 行为准则

- 尊重所有贡献者
- 保持友善和专业
- 提供建设性反馈
- 遵守项目许可证

---

## ❓ 常见问题

### Q: 如何切换 LLM 服务商？

A: 在 `.env` 中配置相应的 API Key：
```env
# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.openai.com/v1

# 或使用 Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-xxx

# 或使用 Google Gemini
GOOGLE_API_KEY=xxx
```

### Q: 端口被占用怎么办？

A: 修改启动端口：
```bash
# 后端
uvicorn ... --port 8001

# 前端
PORT=3001 npm run dev
```

### Q: Redis 连接失败？

A: 检查 Redis 服务是否启动，或在 `.env` 中禁用 Redis：
```env
USE_REDIS=false
```

### Q: 分析速度慢？

A: 可能的优化：
1. 使用更快的 LLM 模型（如 GPT-4o-mini）
2. 启用 Redis 缓存
3. 调整并发参数
4. 使用本地部署的 LLM

### Q: 如何自定义专家角色？

A: 编辑配置文件：
```
intelligent_project_analyzer/config/roles/
```

更多问题参见 [FAQ 文档](docs/FAQ.md)

---

## 🔒 安全性

- ✅ 内容安全检查（敏感词过滤）
- ✅ API 密钥加密存储
- ✅ HTTPS 传输（生产环境）
- ✅ CORS 跨域保护
- ✅ 输入验证和清理
- ✅ SQL 注入防护

详见 [安全指南](docs/SECURITY_SETUP_GUIDE.md)

---

## 📊 性能指标

- **分析速度**: 30 秒 - 5 分钟（取决于项目复杂度）
- **并发支持**: 10+ 用户同时使用（单机）
- **内存占用**: 500MB - 2GB（含 LLM 服务）
- **响应时间**: API < 100ms，WebSocket < 50ms
- **测试覆盖率**: 80%+

---

## 🗺️ 路线图

### 近期计划（2025 Q1）
- [ ] 完善 GitHub Actions CI/CD
- [ ] 增加更多 LLM 服务商支持
- [ ] 优化前端 UI/UX
- [ ] 添加多语言支持（英文）
- [ ] 性能优化（响应速度提升 30%）

### 中期计划（2025 Q2-Q3）
- [ ] 移动端适配
- [ ] 团队协作功能
- [ ] 版本管理和对比
- [ ] 导出 PPT/Word 格式
- [ ] 插件市场

### 长期愿景
- [ ] 云服务化（SaaS）
- [ ] AI 训练优化
- [ ] 行业定制版本
- [ ] 开放 API 生态

---

## 💡 致谢

感谢以下开源项目：
- [LangChain](https://github.com/langchain-ai/langchain) & [LangGraph](https://github.com/langchain-ai/langgraph)
- [FastAPI](https://github.com/tiangolo/fastapi)
- [Next.js](https://github.com/vercel/next.js)

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 🔗 相关链接

- 📺 [在线演示](https://ai.ucppt.com)（需 WordPress 登录）
- 🐛 [问题反馈](https://github.com/dafei0755/ai/issues)
- 📝 [更新日志](CHANGELOG.md)
- 📖 [完整文档](docs/)
- 💬 [讨论区](https://github.com/dafei0755/ai/discussions)

---

## 📮 联系方式

- **GitHub**: [@dafei0755](https://github.com/dafei0755)
- **Issues**: [提交问题](https://github.com/dafei0755/ai/issues/new)
- **邮箱**: 通过 GitHub Issues 联系

---

<div align="center">

**当前版本**: v7.104 | **最后更新**: 2025-12-30

⭐ 如果这个项目对你有帮助，请给我们一个 Star！

Made with ❤️ by AI Assistant & Contributors

</div>
