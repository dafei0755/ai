# 🚀 快速启动指南

> 3分钟快速启动 Intelligent Project Analyzer

---

## 📋 前置要求

- **Python**: 3.10+ （推荐 3.13，暂不建议 3.14+）
- **Node.js**: 18+
- **LLM API Key**: OpenAI/Anthropic/Google 任选其一
- **Redis**: 推荐本地可用（未启动时系统会回退内存模式，仅适合开发调试）

---

## ⚡ Windows 推荐启动方式

```cmd
# 1. 克隆项目
git clone https://github.com/dafei0755/ai.git
cd ai

# 2. 配置环境变量
copy .env.example .env
# 编辑 .env 填写 OPENAI_API_KEY
# 若本机 8000 被 ComfyUI 等程序占用，建议同时设置：
# BACKEND_PORT=8001

# 3. 安装依赖
pip install -r requirements.txt
cd frontend-nextjs && npm install && cd ..

# 4. 确认 Redis 可用（终端 0，可选但强烈建议）
# 先检查 6379 是否已监听；若你在 Docker Desktop 已运行原程序容器，通常可直接复用
netstat -ano | findstr :6379

# 5. 启动后端（终端 1）
%CD%\.conda\python.exe -B scripts\run_server_production.py

# 6. 启动前端（终端 2，推荐安全启动）
cd frontend-nextjs && npm run dev:safe
```

若你使用 `BACKEND_PORT=8001`，请确保 `frontend-nextjs/.env.local` 中为：

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
```

✅ 访问 http://localhost:3001 开始使用！

> 说明：当前仓库 **不再提供** `start_services.bat`，请按上面的“双终端启动”方式运行。

---

## 🔧 分步启动

### 1. 安装依赖

```bash
# 后端
pip install -r requirements.txt

# 前端
cd frontend-nextjs && npm install
```

### 2. 配置环境变量

```bash
if not exist .env copy .env.example .env
# 编辑 .env，必填：OPENAI_API_KEY=your_key
# 若 8000 端口已被占用，补充：BACKEND_PORT=8001
```

### 3. 启动服务

```bash
# Redis（可选但强烈建议，避免会话仅保存在内存）
# 先检查是否已可用（尤其是 Docker Desktop 已运行原程序时）
netstat -ano | findstr :6379

# 后端（Python 3.13 Windows）
%CD%\.conda\python.exe -B scripts\run_server_production.py

# 前端（新终端，推荐安全启动）
cd frontend-nextjs && npm run dev:safe
```

若使用 8001，请确认前端 API 地址：

```env
# frontend-nextjs/.env.local
NEXT_PUBLIC_API_URL=http://127.0.0.1:8001
```

若 `6379` 已监听，可直接跳过 Redis 启动步骤。

若 `6379` 未监听，再按需启动 Redis（Docker 或本机服务均可）。

建议在 `.env` 中使用：

```env
REDIS_URL=redis://127.0.0.1:6379/0
```

> 不建议先执行 `taskkill /F /IM python.exe`。这会直接结束机器上**所有** Python 进程，容易误伤别的项目、测试或脚本。

💡 若看到 `WinError 10048`（8000 端口被占用）：

- 先访问 `http://localhost:8000/docs`，确认是否其实是当前项目后端已经在运行
- 若确实需要释放 8000 端口，请按 PID 精确结束对应进程，而不是直接结束全部 `python.exe`

```bash
# 查看 8000 端口占用
netstat -ano | findstr :8000

# 按 PID 精确结束（把 12345 替换成上一步查到的 PID）
taskkill /PID 12345 /F
```

### 4. 访问应用

- **前端**: http://localhost:3001
- **API 文档**: http://localhost:8000/docs（或你配置的 `BACKEND_PORT`，如 `http://localhost:8001/docs`）

---

## 🎯 基础使用

1. 打开 http://localhost:3001
2. 输入设计项目需求（如：150平米现代简约住宅设计）
   
   💡 **输入质量提示**（提高分析准确度）：
   - ✅ 项目类型和面积（如：350㎡别墅、25㎡单间）
   - ✅ 用户身份和特殊需求（如：企业家、自闭症家庭、电竞选手）
   - ✅ 预算范围和时间约束（如：50万预算、3个月完成）
   - ✅ 设计偏好或参考案例（如：北欧风格、对标XX项目）
   
   详细输入可跳过问卷环节，直达深度分析（当前系统34%场景可实现）

3. 回答校准问卷（可跳过）
4. 确认需求分析
5. 查看专家协作报告

---

## ❓ 常见问题

### Q: 端口被占用？

```bash
# 查看 8000 / 3001 端口占用
netstat -ano | findstr :8000
netstat -ano | findstr :3001

# 按 PID 精确结束对应进程（把 12345 替换成实际 PID）
taskkill /PID 12345 /F

# 或修改前端端口
npm run dev -- -p 4000
```

如果 `http://localhost:8000/docs` 或 `http://localhost:3001` 已可访问，通常说明服务已经在运行，无需重复启动。

### Q: Python 3.13 Windows 用户

⚠️ 必须使用 `scripts\run_server_production.py` 启动

建议显式使用项目环境解释器启动：
```bash
%CD%\.conda\python.exe -B scripts\run_server_production.py
```

如果本地没有项目内 `.conda` 解释器，也可以在已激活的 Python 环境中运行：
```bash
python -B scripts\run_server_production.py
```

若启动时报 `Form data requires "python-multipart"`，执行：
```bash
python -m pip install python-multipart
```

若日志提示 Chromium 未安装（仅影响 PDF 导出），执行：
```bash
python -m playwright install chromium
```

详见 [Playwright修复文档](.github/historical_fixes/playwright_python313_windows_fix.md)

### Q: 启动时看到 `Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater`？

这是 `langchain_core` 依赖链触发的上游兼容性告警：

- **现象**: 服务可能还能启动，但后续存在运行时兼容风险
- **原因**: Python 3.14+ 下，部分依赖仍引用 `pydantic.v1` 兼容层
- **建议**: 使用 Python 3.13 运行本项目（当前最稳妥）

可按以下方式重建环境（Windows + conda）：

```bash
conda create -p .conda python=3.13 -y
conda activate .\.conda
python -m pip install -r requirements.txt
python -B scripts\run_server_production.py
```

若你当前必须使用 3.14+，该告警可暂时观察，但不建议用于生产环境。

### Q: 切换 LLM 服务商

编辑 `.env` 文件：
```env
OPENAI_API_KEY=sk-xxx
# 或 ANTHROPIC_API_KEY / GOOGLE_API_KEY
```

### Q: 日志提示 `Redis 连接失败: Timeout connecting to server`？

这通常不是 Docker Desktop 程序本身故障，而是 **Redis 容器未运行** 或 **6379 未监听**。

```bash
# 查看 Redis 容器
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"

# 查看 6379 端口监听
netstat -ano | findstr :6379
```

若无 Redis 且你希望使用 Docker，可执行：

```bash
docker run -d --name ipa-redis -p 6379:6379 redis:7-alpine
```

若容器已存在但停止：

```bash
docker start ipa-redis
```

若服务确实不依赖 Redis（仅临时调试），可忽略该告警；系统会回退内存模式，但不建议长期使用。

### Q: 需求分析的Fallback模式是什么？

**背景**: 当前Windows环境下OpenAI API存在emoji编码问题，系统采用智能Fallback机制保障服务稳定性。

**性能表现** (v7.620优化版):
- ✅ **稳定性**: 100%成功率，零崩溃
- ✅ **智能分析**: 34%场景可直接进入深度分析（跳过问卷）
- ✅ **隐含推断**: 自动识别高净值用户、特殊需求场景

**优化建议**:
- 提供详细输入可提升分析质量（见上方"输入质量提示"）
- 长期方案：迁移到Claude API或Docker Linux环境

**详细报告**: 参见 [FALLBACK_OPTIMIZATION_REPORT_v7.620.md](FALLBACK_OPTIMIZATION_REPORT_v7.620.md)

---

## 📚 进阶文档

- 📖 [完整文档](docs/README.md) - 架构设计、API 文档
- 🔧 [开发规范](.github/DEVELOPMENT_RULES_CORE.md) - 修改代码前必读
- 🎯 [本体论管理控制台](ONTOLOGY_ADMIN_QUICKSTART.md) - 管理员后台使用指南 🆕
- 🐛 [问题反馈](https://github.com/dafei0755/ai/issues)
- 💬 [讨论区](https://github.com/dafei0755/ai/discussions)

---

**祝你使用愉快！** 🎉
