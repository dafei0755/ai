# 🚀 快速启动指南

> 5分钟快速启动 Intelligent Project Analyzer

---

## 📋 前置要求

- **Python**: 3.10+ （推荐 3.11 或 3.13）
- **Node.js**: 18+
- **Git**: 用于克隆项目

---

## ⚡ 方式一：一键启动（Windows，推荐）

```cmd
# 克隆项目
git clone https://github.com/dafei0755/ai.git
cd ai

# 配置环境变量（所有设置统一在.env文件中管理）
copy .env.example .env
# 编辑 .env 填写 OPENAI_API_KEY
# 可选：SERPER_API_KEY (推荐，搜索质量更稳定，免费2500次/月)

# 安装依赖
pip install -r requirements.txt
cd frontend-nextjs && npm install && cd ..

# 一键启动（后端+前端）
start_services.bat
```

访问 http://localhost:3001 即可使用！

> ⚠️ **端口说明**: 前端使用 **3001端口**（3000端口已被Milvus Attu管理界面占用）

---

## 🔧 方式二：分步启动

### 1. 安装后端依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

> 🎯 **配置集中化**：所有系统配置统一在 `.env` 文件中管理，无需修改代码文件。

```bash
# 复制配置模板
copy .env.example .env

# 编辑 .env 文件，所有配置项都在此文件中设置：
# OPENAI_API_KEY=your_api_key_here

# 环境配置（可选，默认为 dev）
# ENVIRONMENT=dev  # 可选值: dev/development, staging/test, prod/production

# 可选：搜索工具配置（推荐启用博查+Tavily）
# BOCHA_ENABLED=true
# BOCHA_API_KEY=your_bocha_api_key  # 获取: https://open.bochaai.com/ (中文AI搜索)
# TAVILY_API_KEY=your_tavily_key  # 备用国际搜索工具
# SERPER_ENABLED=false  # 中国网络环境可能不稳定，默认禁用
# SERPER_API_KEY=your_serper_api_key_here  # 获取: https://serper.dev/

# 可选：博查AI Search增强模式（v7.161新增，v7.275切换为OpenAI）
# BOCHA_AI_SEARCH_ENABLED=true  # 启用AI Search（OpenAI推理）
# BOCHA_IMAGE_SEARCH_ENABLED=false  # 禁用图片搜索
# BOCHA_AI_SEARCH_MODEL=gpt-4o  # 可选：指定推理模型（默认gpt-4o）

# 可选：雷达图动态维度配置（v7.142新增）
# USE_DYNAMIC_GENERATION=true  # 启用智能维度生成（默认启用，+5-10秒）
# ENABLE_DIMENSION_LEARNING=false  # 历史数据学习（默认禁用，避免延迟）

# 可选：智能问卷生成配置（v7.142新增）
# USE_LLM_GAP_QUESTIONS=true  # 启用LLM智能问卷（默认启用，+3-5秒）
# ENABLE_EXPERT_FORESIGHT=true  # 专家视角风险预判（默认启用，+2-3秒）

# 完整配置列表详见 .env.example 文件
```

> 🔧 **配置管理说明**：
> - **统一配置文件**：所有系统设置（API密钥、功能开关、性能参数）统一在 `.env` 文件中管理
> - **Pydantic Settings**：系统使用Pydantic Settings 2.x自动加载和验证环境变量
> - **热重载支持**：部分配置支持运行时热重载，无需重启服务（通过HotReloadConfigManager）
> - **嵌套配置**：支持使用双下划线分隔符（如 `LLM__MAX_TOKENS=8000`）设置嵌套配置
> - **环境隔离**：开发/测试/生产环境可使用不同的 `.env` 文件进行隔离

> 💡 **智能问卷生成说明（v7.142）**:
> - 系统现已启用**LLM智能问卷生成**，问题会根据您的具体需求动态定制
> - **Step 1（任务梳理）**: 从用户需求中提取核心任务，支持编辑和补充
> - **Step 2（信息补全）**: 根据缺失信息生成针对性问题（预算、时间、交付要求等）
> - **Step 3（雷达图）**: 智能选择或生成定制化维度，反映设计偏好
> - 如需使用硬编码问题模板（更快但通用），可设置 `USE_LLM_GAP_QUESTIONS=false`

> 💡 **雷达图动态维度说明（v7.142）**:
> - **USE_DYNAMIC_GENERATION=true（默认）**: 系统会智能分析用户需求，自动生成定制化维度，响应时间增加5-10秒
> - **USE_DYNAMIC_GENERATION=false**: 仅使用静态维度库（文化归属轴、美学方向轴等），响应时间<1秒
> - **ENABLE_DIMENSION_LEARNING=false（默认）**: 禁用历史数据学习，避免30-70秒延迟，推荐保持关闭
> - 系统会根据用户输入自动判断是否需要生成新维度，避免不必要的LLM调用

> 💡 **搜索工具说明（中国网络环境优化）**:
> - **博查 Bocha（推荐）**: 中文AI搜索，国内稳定，适合中文内容
>   - 官网: https://open.bochaai.com/
>   - API域名: api.bochaai.com（v7.161统一更新）
> - **博查 AI Search（v7.161新增，v7.275升级）**: 独立搜索页面，支持OpenAI推理
>   - 访问: http://localhost:3001/search
>   - 使用已配置的 OPENAI_API_KEY（无需额外配置）
> - **Tavily**: 国际搜索补充，多引擎聚合，免费额度1000次/月
> - **Serper**: 基于Google搜索，中国网络可能遇到SSL问题，默认禁用
> - 系统降级策略：博查 → Tavily → Milvus知识库

> 💡 **雷达图动态维度说明（v7.142）**:
> - 系统现已启用**智能维度生成**，会根据用户需求自动生成定制化维度
> - 默认配置平衡了性能和智能化：动态生成启用（+5-10秒），历史学习禁用
> - 如需最快响应速度，可在 `.env` 设置 `USE_DYNAMIC_GENERATION=false`
> - 如需极致智能化，可设置 `ENABLE_DIMENSION_LEARNING=true`（+30-70秒）

### 3. 启动后端服务

```bash
# Python 3.13 Windows用户（推荐）
taskkill /F /IM python.exe
python -B scripts\run_server_production.py

# Python 3.10-3.12用户
python -B scripts\run_server.py

# 或使用 uvicorn 直接启动
python -B -m uvicorn intelligent_project_analyzer.api.server:app --host 0.0.0.0 --port 8000 --reload
```

> 💡 **首次启动后，建议配置自动修复记录系统**：
> ```bash
> python .github\scripts\install_hooks.py
> ```
> 配置完成后，每次提交修复代码时会自动提醒记录到知识库。

**成功标志**：
```
✅ Playwright 浏览器池初始化成功
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 4. 启动前端服务

```bash
cd frontend-nextjs
npm run dev
```

**成功标志**：
```
✓ Ready in 1846ms
- Local:        http://localhost:3001
```

> ⚠️ **端口说明**: 前端使用 **3001端口**（3000端口被Milvus Attu管理界面占用）

### 5. 访问应用

- **前端界面**: http://localhost:3001
- **用户中心**: http://localhost:3001/user/dashboard （会员信息、配额管理、知识库）
- **管理后台**: http://localhost:3001/admin
  - **知识库管理**: http://localhost:3001/admin/knowledge-base （Milvus向量库管理）
  - **搜索过滤器管理**: http://localhost:3001/admin/search-filters （黑白名单配置）
  - **能力边界监控**: http://localhost:3001/admin/capability-boundary （交付物能力约束监控）
  - **数据库监控**: http://localhost:3001/admin/database （会话数据库健康状态与维护）
  - **系统监控**: http://localhost:3001/admin/monitoring
  - **会话管理**: http://localhost:3001/admin/sessions
- **Milvus管理界面**: http://localhost:3000 （Attu可视化管理）
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

> 💡 **管理后台功能**:
> - **知识库管理**: 管理 Milvus 知识库（公共/私有/团队文档，支持共享和配额管理）
> - **搜索过滤器**: 配置黑名单（屏蔽低质量站点）和白名单（优先搜索推荐权威媒体）
> - **能力边界监控**: 监控交付物能力约束违规情况，防止用户选择超出系统能力范围的交付物（CAD施工图、3D效果图、精确清单等）
> - **数据库监控**: 实时查看会话数据库健康状态（大小、记录数、告警），执行 VACUUM 压缩和会话归档
> - **系统监控**: 实时查看系统状态、性能指标、错误日志
> - **会话管理**: 管理用户会话、查看历史记录、导出数据

> 💡 **用户中心功能** (v7.141.4):
> - **概览**: 会员等级、配额使用情况可视化（文档数量、存储空间进度条）
> - **知识库管理**: 查看和管理个人知识库文档
> - **账户设置**: 用户信息显示和管理
> - **帮助中心**: 服务条款、隐私政策、使用指南

---

## 🎯 基础使用流程

1. **访问系统**：打开 http://localhost:3001
2. **输入需求**：描述你的设计项目需求
   ```
   示例：我需要设计一个150平米的现代简约风格住宅，
   三室两厅，预算30万，希望注重收纳和采光。
   ```
3. **渐进式问卷**：完成三步智能问卷（v7.143优化）
   - **Step 1（任务梳理）**: 从需求中提取核心任务，支持编辑和补充
   - **Step 2（信息补全）**: 根据缺失信息生成针对性问题（预算、时间、交付要求等）
   - **Step 3（雷达图）**: 智能选择或生成定制化维度，反映设计偏好
4. **确认需求**：审核系统分析的需求理解（**v7.143: 展示13个完整维度**）
   - 📋 项目目标（主要目标、次要目标、成功标准）
   - 💰 约束条件（预算、时间、空间独立展示）
   - ⭐ 设计重点（完整9个雷达图维度，而非前3个）
   - ⚡ 核心张力（主要张力 + 详细矛盾点）
   - 🔧 特殊需求、⚠️ 风险识别、🤖 AI洞察、📦 交付物期望、📝 执行摘要
5. **专家协作**：系统自动选择专家团队并生成分析
6. **查看报告**：获取完整的项目分析报告

> ⚠️ **系统能力边界说明（v7.130）**:
> - **系统定位**: 策略规划与概念设计工具，提供设计思路、方案建议和专业指导
> - **✅ 支持的交付物**: 设计策略文档、空间概念描述、材料选择指导、预算框架、分析报告
> - **❌ 不支持的交付物**: CAD施工图、3D效果图、精确材料清单、精确预算清单（需要专业工具和现场测量）
> - 系统会自动将超出能力范围的需求转换为可执行的策略性指导

---

## 🐳 方式三：Docker 部署

```bash
# 1. 确保配置文件存在
copy .env.example .env
# 编辑 .env 文件填写必要配置

# 2. 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## ❓ 常见问题

### Q: 端口被占用怎么办？

```bash
# 终止旧进程
taskkill /F /IM python.exe
Get-Process node | Stop-Process -Force

# 或修改端口
PORT=3001 npm run dev  # 前端
uvicorn ... --port 8001  # 后端
```

### Q: Python 3.13 Windows 用户必看

⚠️ 必须使用 `scripts\run_server_production.py` 启动，否则 Playwright PDF 生成功能会失败。

详见 [Playwright Python 3.13 修复文档](.github/historical_fixes/playwright_python313_windows_fix.md)

### Q: Windows终端乱码怎么办？

部分功能（如动态维度生成）需要UTF-8编码环境：

```cmd
# 临时设置（当前终端）
chcp 65001

# 永久设置（推荐）
# 1. Win+R → 输入 intl.cpl → 管理 → 更改系统区域设置
# 2. 勾选"Beta: 使用 Unicode UTF-8 提供全球语言支持"
# 3. 重启电脑
```

### Q: 所有配置都在哪里管理？

✅ **统一配置管理**：所有系统配置都集中在 `.env` 文件中，包括：
- **API密钥配置**：OpenAI、Anthropic、Google、博查、Tavily等
- **功能开关**：搜索工具、智能问卷、动态维度等
- **性能参数**：并发数、超时时间、缓存设置等
- **数据库配置**：Redis、Milvus等连接参数
- **日志配置**：日志级别、输出格式等

```bash
# 查看所有可配置项
cat .env.example

# 验证当前配置
python -c "from intelligent_project_analyzer.settings import settings; print(settings)"
```

**配置修改生效方式**：
- 大部分配置：重启服务后生效
- 部分配置：支持热重载（如日志级别）

### Q: 如何切换 LLM 服务商？

所有LLM配置都在 `.env` 文件中管理：
```env
# 使用 OpenAI
OPENAI_API_KEY=sk-xxx

# 或使用 Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-xxx

# 或使用 Google Gemini
GOOGLE_API_KEY=xxx
```

### Q: 系统日志在哪里？如何快速定位问题？

系统日志统一存储在 `logs/` 目录，不同模式共享同一套日志系统：

```powershell
# 查看实时主日志（所有模式）
Get-Content logs\server.log -Wait -Tail 100 -Encoding UTF8

# 搜索深度思考模式日志
Get-Content logs\server.log | Select-String "深度思考|deep_thinking"

# 查看搜索任务的工具调用记录
Get-Content logs\tool_calls.jsonl -Tail 20

# 搜索特定会话ID的日志
Get-Content logs\server.log | Select-String "YOUR_SESSION_ID"
```

**日志文件说明**：
- `logs/server.log` - 主日志（普通/深度思考/搜索任务共享）
- `logs/errors.log` - 仅错误日志（保留30天）
- `logs/tool_calls.jsonl` - 工具调用记录（搜索/ArXiv等）
- `logs/auth.log` - 认证相关日志
- `data/archived_sessions.db` - 会话归档数据库

**详细指南**：📖 [LOGGING_QUICKSTART.md](LOGGING_QUICKSTART.md#-日志定位速查表)

### Q: archived_sessions.db 数据库文件很大，如何优化？

**v7.200 性能优化已实施**，包含以下自动优化：

✅ **已自动启用**：
- **WAL 模式**：并发性能提升 2-5x，读写不互相阻塞
- **连接池优化**：10个连接，最大30个并发
- **查询优化**：大字段延迟加载，索引覆盖

🛠️ **维护工具**（需要手动执行）：

```powershell
# 1. 查看数据库统计信息
python scripts/database_maintenance.py --stats

# 2. 执行 VACUUM 压缩（回收空间）
python scripts/database_maintenance.py --vacuum

# 3. 归档30天前的会话到冷存储
python scripts/database_maintenance.py --archive --days 30

# 4. 清理90天前的失败会话
python scripts/database_maintenance.py --clean-failed --days 90

# 5. 执行完整维护流程
python scripts/database_maintenance.py --all
```

📅 **建议定期维护**：

```powershell
# Windows 任务计划程序（每周日凌晨2点自动维护）
schtasks /create /tn "LangGraph数据库维护" /tr "python D:\11-20\langgraph-design\scripts\auto_archive_scheduler.py --once" /sc weekly /d SUN /st 02:00
```

**健康阈值**：
- 🟢 正常：< 10GB
- 🟡 警告：10-50GB（建议执行维护）
- 🔴 严重：> 50GB（立即执行维护）

**详细说明**：📖 [数据库性能优化文档](#)

### Q: 为什么某些角色没有搜索引用数据？

**原因**: 系统设计遵循真实企业层级结构，不同角色有不同的工具权限：

- **V2（设计总监）**: 高层决策者，**仅使用知识库搜索**（Milvus），不使用外部搜索引擎
- **V3（叙事与体验专家）**: 专业执行角色，**启用搜索工具**（博查/Tavily、ArXiv、Milvus等）
- **V4（设计研究员）**: 专业执行角色，**启用搜索工具**（博查/Tavily、ArXiv、Milvus知识库）
- **V5（场景与行业专家）**: 专业执行角色，**启用搜索工具**（博查/Tavily、ArXiv、Milvus知识库）
- **V6（专业总工程师）**: 专业执行角色，**启用搜索工具**（博查/Tavily、ArXiv、Milvus知识库）
- **V7（情感洞察专家）**: 心理与情感分析角色，**启用搜索工具**（博查/Tavily、ArXiv、Milvus知识库）

**建议**:
- 测试搜索功能时，使用 **V4角色**（拥有全部搜索工具）
- 优先使用博查处理中文内容，Tavily补充国际内容
- 查看诊断脚本：`python scripts/diagnose_search_tools.py`

---

## � 配置管理详细说明

### 统一配置架构

本项目采用**单一配置文件**架构，所有系统设置都集中在 `.env` 文件中管理：

```
📁 项目根目录/
├── .env                    # 👈 主配置文件（所有设置在此）
├── .env.example           # 配置模板文件
├── settings.py            # Pydantic配置类（代码中读取.env）
└── config_manager.py      # 热重载管理器
```

### 配置分类

**🔑 认证配置**：
```env
# LLM API密钥（至少配置一个）
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
DEEPSEEK_API_KEY=sk-xxx

# 搜索工具API密钥
BOCHA_API_KEY=your_bocha_key
TAVILY_API_KEY=your_tavily_key
SERPER_API_KEY=your_serper_key
```

**⚙️ 功能开关**：
```env
# 环境配置
ENVIRONMENT=dev  # 可选: dev/development, staging/test, prod/production

# 搜索工具开关
BOCHA_ENABLED=true
BOCHA_AI_SEARCH_ENABLED=true
BOCHA_IMAGE_SEARCH_ENABLED=false

# 智能功能开关
USE_DYNAMIC_GENERATION=true
USE_LLM_GAP_QUESTIONS=true
ENABLE_EXPERT_FORESIGHT=true
```

**🗄️ 数据库配置**：
```env
# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Milvus配置
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

**📊 性能参数**：
```env
# 并发配置
MAX_CONCURRENT_REQUESTS=10
SEARCH_TIMEOUT=30

# 缓存配置
ENABLE_REDIS_CACHE=true
CACHE_TTL_HOURS=24
```

### 配置验证

```bash
# 验证配置是否正确加载
python -c "
from intelligent_project_analyzer.settings import settings
print('✅ 配置加载成功')
print(f'当前LLM提供商: {settings.llm.provider}')
print(f'搜索工具状态: 博查={settings.bocha.enabled}, Tavily={bool(settings.tavily.api_key)}')
"
```

### 环境隔离

支持多环境配置文件：
```bash
# 开发环境
cp .env.development.example .env

# 生产环境
cp .env.production.example .env

# 测试环境
cp .env.testing.example .env
```

---

## �📚 下一步

- 📖 [完整文档](docs/README.md) - 架构设计、API 文档
- 🔧 [开发规范](.github/DEVELOPMENT_RULES_CORE.md) - 修改代码前必读
- 🐛 [问题反馈](https://github.com/dafei0755/ai/issues) - 遇到问题？提交 Issue
- 💬 [讨论区](https://github.com/dafei0755/ai/discussions) - 交流使用经验
- 🤖 [自动修复记录系统](.github/AUTOMATED_FIX_RECORDING_SYSTEM.md) - 避免重复错误的知识库
- 📊 [v7.122 数据流优化](.github/historical_fixes/data_flow_optimization_v7.122.md) - 问卷→搜索→概念图数据流优化

---

## 📞 需要帮助？

- **文档**: [docs/](docs/)
- **Issues**: https://github.com/dafei0755/ai/issues
- **Discussions**: https://github.com/dafei0755/ai/discussions

**祝你使用愉快！** 🎉
