# ❓ 常见问题解答（FAQ）

> 本文档收集了 Intelligent Project Analyzer 使用过程中的常见问题及解决方案

---

## 📑 目录

- [安装与配置](#安装与配置)
- [运行问题](#运行问题)
- [功能使用](#功能使用)
- [性能优化](#性能优化)
- [故障排查](#故障排查)
- [开发相关](#开发相关)

---

## 🔧 安装与配置

### Q1: 安装依赖时出现错误怎么办？

**A:** 常见原因和解决方案：

1. **Python 版本不兼容**
   ```bash
   # 检查 Python 版本
   python --version
   # 需要 Python 3.10+
   ```

2. **pip 版本过旧**
   ```bash
   # 升级 pip
   python -m pip install --upgrade pip
   ```

3. **网络问题**
   ```bash
   # 使用国内镜像
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

4. **权限问题**
   ```bash
   # 使用 --user 标志
   pip install --user -r requirements.txt
   ```

### Q2: 如何配置 .env 文件？

**A:** 按照以下步骤配置：

1. 复制模板文件：
   ```bash
   copy .env.example .env
   ```

2. 编辑 `.env` 文件，填入必需的配置：
   ```env
   # 必需配置
   OPENAI_API_KEY=sk-your-key-here
   OPENAI_API_BASE=https://api.openai.com/v1
   
   # 可选配置
   REDIS_URL=redis://localhost:6379
   TAVILY_API_KEY=your-tavily-key
   ```

3. 验证配置：
   ```bash
   python -c "from dotenv import load_dotenv; load_dotenv(); import os; print('✓' if os.getenv('OPENAI_API_KEY') else '✗ Missing OPENAI_API_KEY')"
   ```

### Q3: 支持哪些 LLM 服务商？

**A:** 目前支持以下 LLM 服务商：

| 服务商 | 配置项 | 说明 |
|--------|--------|------|
| OpenAI | `OPENAI_API_KEY` | 支持 GPT-3.5/4/4o 系列 |
| Anthropic | `ANTHROPIC_API_KEY` | 支持 Claude 系列 |
| Google | `GOOGLE_API_KEY` | 支持 Gemini 系列 |
| 自定义 | `OPENAI_API_BASE` | 兼容 OpenAI API 的服务 |

配置示例：
```env
# 使用 OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.openai.com/v1

# 或使用国内中转服务
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://your-proxy.com/v1
```

### Q4: 前端环境变量如何配置？

**A:** 在 `frontend-nextjs/` 目录下：

1. 创建 `.env.local` 文件：
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   NEXT_PUBLIC_WS_URL=ws://localhost:8000
   ```

2. 重启前端服务使其生效

---

## 🚀 运行问题

### Q5: 端口被占用怎么办？

**A:** 解决方案：

1. **后端端口（8000）被占用**
   ```bash
   # 方法1: 修改启动端口
   uvicorn intelligent_project_analyzer.api.server:app --port 8001
   
   # 方法2: 查找并关闭占用进程
   netstat -ano | findstr :8000
   taskkill /PID <进程ID> /F
   ```

2. **前端端口（3000）被占用**
   ```bash
   # Next.js 会自动尝试 3001, 3002...
   # 或手动指定端口
   PORT=3001 npm run dev
   ```

### Q6: Redis 连接失败？

**A:** 检查和解决步骤：

1. **确认 Redis 是否安装并运行**
   ```bash
   # Windows (使用 WSL 或 Docker)
   docker run -d -p 6379:6379 redis:alpine
   
   # 测试连接
   redis-cli ping
   # 应该返回 PONG
   ```

2. **临时禁用 Redis**（开发环境）
   ```env
   # 在 .env 中添加
   USE_REDIS=false
   ```

3. **检查 Redis 配置**
   ```env
   REDIS_URL=redis://localhost:6379
   REDIS_DB=0
   ```

### Q7: 启动后端时出现 ModuleNotFoundError？

**A:** 解决步骤：

1. **确认在项目根目录**
   ```bash
   cd d:\11-20\langgraph-design
   ```

2. **激活虚拟环境**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **重新安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **检查 Python 路径**
   ```bash
   python -c "import sys; print('\n'.join(sys.path))"
   ```

### Q8: 前端无法连接后端？

**A:** 检查清单：

1. ✅ 后端服务是否启动（访问 http://localhost:8000/docs）
2. ✅ 前端配置是否正确（`.env.local` 中的 API_URL）
3. ✅ 浏览器控制台是否有 CORS 错误
4. ✅ 防火墙是否阻止了连接

解决 CORS 问题：
```python
# intelligent_project_analyzer/api/server.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 💡 功能使用

### Q9: 如何跳过校准问卷？

**A:** 两种方式：

1. **UI 界面**：点击"跳过问卷"按钮

2. **API 调用**：
   ```python
   response = requests.post(
       "http://localhost:8000/api/v1/sessions",
       json={
           "user_input": "你的需求",
           "skip_questionnaire": True
       }
   )
   ```

### Q10: 如何自定义专家角色？

**A:** 步骤如下：

1. 编辑角色配置文件：
   ```
   intelligent_project_analyzer/config/roles/
   ```

2. 创建新的角色 YAML 文件：
   ```yaml
   # custom_expert.yaml
   role_id: "V10_custom_expert"
   display_name: "自定义专家"
   description: "专门负责..."
   core_capabilities:
     - 能力1
     - 能力2
   typical_tasks:
     - 任务类型1
     - 任务类型2
   ```

3. 重启后端服务

### Q11: 如何导出分析报告？

**A:** 支持多种格式：

1. **PDF 格式**（推荐）
   ```python
   # API 调用
   response = requests.post(
       f"http://localhost:8000/api/v1/sessions/{session_id}/export",
       json={"format": "pdf"}
   )
   ```

2. **Markdown 格式**
   ```python
   response = requests.post(
       f"http://localhost:8000/api/v1/sessions/{session_id}/export",
       json={"format": "markdown"}
   )
   ```

3. **JSON 格式**（原始数据）
   ```python
   response = requests.get(f"http://localhost:8000/api/v1/sessions/{session_id}")
   ```

### Q12: 如何查看分析历史记录？

**A:** 方法：

1. **通过 API**：
   ```python
   # 获取所有会话
   response = requests.get(
       "http://localhost:8000/api/v1/sessions",
       params={"user_id": "your_user_id"}
   )
   ```

2. **使用 Redis CLI**（如果启用了 Redis）：
   ```bash
   redis-cli
   > KEYS session:*
   > GET session:your-session-id
   ```

3. **查看 SQLite 数据库**：
   ```bash
   sqlite3 data/sessions.db
   > SELECT * FROM sessions;
   ```

---

## ⚡ 性能优化

### Q13: 分析速度太慢怎么办？

**A:** 优化建议：

1. **使用更快的 LLM 模型**
   ```env
   # 使用 GPT-4o-mini 而不是 GPT-4
   OPENAI_MODEL=gpt-4o-mini
   ```

2. **启用 Redis 缓存**
   ```env
   USE_REDIS=true
   REDIS_URL=redis://localhost:6379
   ```

3. **调整并发参数**
   ```python
   # intelligent_project_analyzer/settings.py
   MAX_CONCURRENT_AGENTS = 5  # 增加并发数
   ```

4. **使用本地部署的 LLM**（最快）
   ```env
   OPENAI_API_BASE=http://localhost:11434/v1
   ```

### Q14: 内存占用过高？

**A:** 解决方案：

1. **限制最大会话数**
   ```python
   # settings.py
   MAX_ACTIVE_SESSIONS = 10
   ```

2. **定期清理旧会话**
   ```bash
   # 使用清理脚本
   python scripts/cleanup_old_sessions.py
   ```

3. **减少 Agent 数量**
   ```env
   MAX_AGENTS_PER_SESSION=5
   ```

### Q15: WebSocket 连接不稳定？

**A:** 优化措施：

1. **增加心跳间隔**
   ```javascript
   // frontend
   const ws = new WebSocket('ws://localhost:8000/ws');
   setInterval(() => ws.send('ping'), 30000);
   ```

2. **启用自动重连**
   ```javascript
   function connectWebSocket() {
       const ws = new WebSocket('ws://localhost:8000/ws');
       ws.onclose = () => setTimeout(connectWebSocket, 3000);
   }
   ```

---

## 🔍 故障排查

### Q16: 日志在哪里查看？

**A:** 日志位置和查看方法：

1. **主日志**：`logs/server.log`
   ```bash
   # 实时查看
   Get-Content logs\server.log -Wait -Tail 100 -Encoding UTF8
   ```

2. **错误日志**：`logs/errors.log`
   ```bash
   Get-Content logs\errors.log -Tail 50 -Encoding UTF8
   ```

3. **SSO 日志**：`logs/auth.log`

4. **性能日志**：`logs/performance.log`

### Q17: 如何调试 Agent 行为？

**A:** 调试技巧：

1. **启用详细日志**
   ```env
   LOG_LEVEL=DEBUG
   ```

2. **查看 Agent 执行轨迹**
   ```python
   # 在代码中添加
   import logging
   logger = logging.getLogger(__name__)
   logger.debug(f"Agent state: {state}")
   ```

3. **使用 LangGraph 调试工具**
   ```python
   from langgraph.debug import print_graph
   print_graph(workflow.graph)
   ```

### Q18: 数据库损坏如何恢复？

**A:** 恢复步骤：

1. **SQLite 数据库**
   ```bash
   # 检查完整性
   sqlite3 data/sessions.db "PRAGMA integrity_check;"
   
   # 导出并重建
   sqlite3 data/sessions.db ".dump" > backup.sql
   sqlite3 new_sessions.db < backup.sql
   ```

2. **Redis 数据**
   ```bash
   # 使用 Redis 持久化
   redis-cli SAVE
   
   # 从备份恢复
   redis-cli --rdb dump.rdb
   ```

### Q19: API 返回 500 错误？

**A:** 诊断步骤：

1. **查看详细错误信息**
   ```bash
   # 访问 API 文档
   http://localhost:8000/docs
   
   # 查看实时日志
   Get-Content logs\errors.log -Wait
   ```

2. **检查环境变量**
   ```python
   python -c "from intelligent_project_analyzer.settings import settings; print(settings)"
   ```

3. **验证 LLM API**
   ```python
   python -c "from intelligent_project_analyzer.services.llm_factory import LLMFactory; llm = LLMFactory.create_llm(); print(llm.invoke('test'))"
   ```

---

## 👨‍💻 开发相关

### Q20: 如何添加新的 Agent？

**A:** 步骤：

1. 创建 Agent 类：
   ```python
   # intelligent_project_analyzer/agents/my_agent.py
   from .base import BaseAgent
   
   class MyAgent(BaseAgent):
       def execute(self, state, config, store=None):
           # 实现逻辑
           pass
   ```

2. 注册到工作流：
   ```python
   # workflow/main_workflow.py
   from ..agents.my_agent import MyAgent
   
   def _build_workflow_graph(self):
       # 添加节点
       graph.add_node("my_agent", self._my_agent_node)
   ```

3. 添加测试：
   ```python
   # tests/test_my_agent.py
   def test_my_agent():
       agent = MyAgent()
       result = agent.execute(state)
       assert result is not None
   ```

### Q21: 如何运行测试？

**A:** 测试命令：

```bash
# 运行所有测试
pytest

# 运行特定文件
pytest tests/test_integration.py

# 查看覆盖率
pytest --cov=intelligent_project_analyzer --cov-report=html

# 只运行单元测试
pytest -m unit

# 跳过慢速测试
pytest -m "not slow"

# 详细输出
pytest -v -s
```

### Q22: 如何贡献代码？

**A:** 贡献流程：

1. Fork 项目
2. 创建功能分支：`git checkout -b feature/my-feature`
3. 遵循代码规范（Black + isort + Flake8）
4. 添加测试（覆盖率 ≥ 80%）
5. 提交代码：`git commit -m "feat: add my feature"`
6. 推送分支：`git push origin feature/my-feature`
7. 创建 Pull Request

详见：[贡献指南](../README.md#贡献指南)

### Q23: 如何更新依赖？

**A:** 更新步骤：

```bash
# 查看过期的包
pip list --outdated

# 更新所有包（谨慎）
pip install --upgrade -r requirements.txt

# 更新特定包
pip install --upgrade langgraph langchain

# 导出新的依赖
pip freeze > requirements.txt
```

---

## 📞 获取帮助

如果以上答案无法解决你的问题：

1. 📖 查看[完整文档](../README.md)
2. 🐛 [提交 Issue](https://github.com/dafei0755/ai/issues)
3. 💬 [参与讨论](https://github.com/dafei0755/ai/discussions)
4. 📧 通过 GitHub Issues 联系维护者

---

**最后更新**: 2025-12-30  
**文档版本**: 1.0.0
