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

# 配置环境变量
copy .env.example .env
# 编辑 .env 填写 OPENAI_API_KEY

# 安装依赖
pip install -r requirements.txt
cd frontend-nextjs && npm install && cd ..

# 一键启动（后端+前端）
start_services.bat
```

访问 http://localhost:3000 即可使用！

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

```bash
# 复制配置模板
copy .env.example .env

# 编辑 .env 文件，必填项：
# OPENAI_API_KEY=your_api_key_here
```

### 3. 启动后端服务

```bash
# Python 3.13 Windows用户（推荐）
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
- Local:        http://localhost:3000
```

### 5. 访问应用

- **前端界面**: http://localhost:3000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

---

## 🎯 基础使用流程

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

---

## 🐳 方式三：Docker 部署

```bash
# 构建并启动所有服务
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

### Q: 如何切换 LLM 服务商？

编辑 `.env` 文件：
```env
# 使用 OpenAI
OPENAI_API_KEY=sk-xxx

# 或使用 Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-xxx

# 或使用 Google Gemini
GOOGLE_API_KEY=xxx
```

---

## 📚 下一步

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
