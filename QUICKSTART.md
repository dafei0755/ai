# 🚀 快速启动指南

> 3分钟快速启动 Intelligent Project Analyzer

---

## 📋 前置要求

- **Python**: 3.10+ （推荐 3.13）
- **Node.js**: 18+
- **LLM API Key**: OpenAI/Anthropic/Google 任选其一

---

## ⚡ 一键启动（Windows 推荐）

```cmd
# 1. 克隆项目
git clone https://github.com/dafei0755/ai.git
cd ai

# 2. 配置环境变量
copy .env.example .env
# 编辑 .env 填写 OPENAI_API_KEY

# 3. 安装依赖
pip install -r requirements.txt
cd frontend-nextjs && npm install && cd ..

# 4. 一键启动
start_services.bat
```

✅ 访问 http://localhost:3001 开始使用！

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
copy .env.example .env
# 编辑 .env，必填: OPENAI_API_KEY=your_key
```

### 3. 启动服务

```bash
# 后端（Python 3.13 Windows）
taskkill /F /IM python.exe
python -B scripts\run_server_production.py

# 前端（新终端）
cd frontend-nextjs && npm run dev
```

### 4. 访问应用

- **前端**: http://localhost:3001
- **API 文档**: http://localhost:8000/docs

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
# Windows
taskkill /F /IM python.exe
Get-Process node | Stop-Process -Force

# 或修改端口
npm run dev -- -p 4000
```

### Q: Python 3.13 Windows 用户

⚠️ 必须使用 `scripts\run_server_production.py` 启动

详见 [Playwright修复文档](.github/historical_fixes/playwright_python313_windows_fix.md)

### Q: 切换 LLM 服务商

编辑 `.env` 文件：
```env
OPENAI_API_KEY=sk-xxx
# 或 ANTHROPIC_API_KEY / GOOGLE_API_KEY
```

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
