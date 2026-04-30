# Redis 会话管理集成 - 实施指南

## 当前进度

✅ **已完成**:
1. 修改 `requirements.txt`，启用 Redis 依赖
2. 创建 `redis_session_manager.py` - 完整的会话管理器（支持 CRUD、TTL、分布式锁）
3. 创建 `redis_store.py` - LangGraph Store 适配器
4. 修改 `server.py` - 已添加 Redis Pub/Sub 订阅函数和广播逻辑

⏳ **待完成**:
1. 修改 `server.py` 中的所有会话访问逻辑（55 处 `sessions[session_id]` 需要替换）
2. 集成 Redis Checkpoint 到 `main_workflow.py`

---

## 第一步：修改 server.py 会话访问逻辑

### 需要修改的模式

#### 原代码模式 1：创建会话
```python
sessions[session_id] = {
    "session_id": session_id,
    "user_input": request.user_input,
    "status": "initializing",
    ...
}
```

#### 新代码模式 1：
```python
await session_manager.create(session_id, {
    "session_id": session_id,
    "user_input": request.user_input,
    "status": "initializing",
    ...
})
```

---

#### 原代码模式 2：更新单个字段
```python
sessions[session_id]["status"] = "running"
sessions[session_id]["progress"] = 0.1
```

#### 新代码模式 2：
```python
await session_manager.update(session_id, {
    "status": "running",
    "progress": 0.1
})
```

---

#### 原代码模式 3：读取会话
```python
session = sessions[session_id]
status = session["status"]
```

#### 新代码模式 3：
```python
session = await session_manager.get(session_id)
if not session:
    raise HTTPException(status_code=404, detail="会话不存在")
status = session["status"]
```

---

#### 原代码模式 4：检查会话存在性
```python
if session_id not in sessions:
    raise HTTPException(status_code=404, detail="会话不存在")
```

#### 新代码模式 4：
```python
if not await session_manager.exists(session_id):
    raise HTTPException(status_code=404, detail="会话不存在")
```

---

## 第二步：修改关键函数示例

### 1. `start_analysis` 函数（约第 685 行）

#### 原代码：
```python
@app.post("/api/analysis/start", response_model=SessionResponse)
async def start_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    session_id = f"api-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    # 初始化会话状态
    sessions[session_id] = {
        "session_id": session_id,
        "user_input": request.user_input,
        "mode": "dynamic",
        "status": "initializing",
        ...
    }
    
    background_tasks.add_task(run_workflow_async, session_id, request.user_input)
    
    return SessionResponse(...)
```

#### 新代码：
```python
@app.post("/api/analysis/start", response_model=SessionResponse)
async def start_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    session_id = f"api-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    
    # ✅ 使用 Redis 创建会话
    await session_manager.create(session_id, {
        "session_id": session_id,
        "user_input": request.user_input,
        "mode": "dynamic",
        "status": "initializing",
        "progress": 0.0,
        "events": [],
        "interrupt_data": None,
        "current_node": None,
        "error": None,
        "created_at": datetime.now().isoformat()
    })
    
    background_tasks.add_task(run_workflow_async, session_id, request.user_input)
    
    return SessionResponse(...)
```

---

### 2. `get_analysis_status` 函数（约第 735 行）

#### 原代码：
```python
@app.get("/api/analysis/status/{session_id}", response_model=AnalysisStatus)
async def get_analysis_status(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    session = sessions[session_id]
    
    return AnalysisStatus(
        session_id=session_id,
        status=session["status"],
        ...
    )
```

#### 新代码：
```python
@app.get("/api/analysis/status/{session_id}", response_model=AnalysisStatus)
async def get_analysis_status(session_id: str):
    # ✅ 使用 Redis 读取会话
    session = await session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    
    return AnalysisStatus(
        session_id=session_id,
        status=session["status"],
        current_stage=session.get("current_node"),
        detail=session.get("detail"),
        progress=session["progress"],
        interrupt_data=session.get("interrupt_data"),
        error=session.get("error"),
        traceback=session.get("traceback"),
        rejection_message=session.get("rejection_message")
    )
```

---

### 3. `run_workflow_async` 函数（约第 320 行起，最复杂）

这个函数需要将所有 `sessions[session_id][...]` 访问改为：

```python
async def run_workflow_async(session_id: str, user_input: str):
    try:
        # ✅ 批量更新状态
        await session_manager.update(session_id, {
            "status": "running",
            "progress": 0.1
        })
        
        # ... 工作流执行逻辑 ...
        
        # ✅ 更新当前节点和详情
        await session_manager.update(session_id, {
            "current_node": node_name,
            "detail": detail,
            "progress": progress
        })
        
        # ✅ 处理 interrupt
        await session_manager.update(session_id, {
            "status": "waiting_for_input",
            "interrupt_data": interrupt_value,
            "current_node": "interrupt"
        })
        
        # ✅ 完成时
        await session_manager.update(session_id, {
            "status": "completed",
            "progress": 1.0,
            "final_report": final_report,
            "pdf_path": pdf_path,
            "results": events
        })
        
    except Exception as e:
        await session_manager.update(session_id, {
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc()
        })
```

**注意**：由于 Redis 更新有网络开销，建议将多个字段合并为一次 `update` 调用，而不是每个字段单独调用。

---

## 第三步：修改 main_workflow.py 集成 Redis Checkpoint

### 位置：`intelligent_project_analyzer/workflow/main_workflow.py` 约第 72-73 行

#### 原代码：
```python
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver

class MainWorkflow:
    def __init__(self, llm_model: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
        # ...
        self.store = InMemoryStore()
        self.checkpointer = MemorySaver()
```

#### 新代码：
```python
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver
# ✅ 导入 Redis Store
from ..services.redis_store import RedisStore, get_redis_store

class MainWorkflow:
    def __init__(self, llm_model: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
        # ...
        
        # ✅ 尝试使用 Redis Store（失败时自动回退到内存）
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            self.store = loop.run_until_complete(get_redis_store())
            logger.info("✅ 使用 Redis Store")
        except Exception as e:
            logger.warning(f"⚠️ Redis Store 不可用，回退到内存模式: {e}")
            self.store = InMemoryStore()
        
        # ✅ Checkpoint 仍使用 MemorySaver（LangGraph 的 Redis Saver 需要单独安装）
        # 或者安装 `langgraph-checkpoint-redis` 后使用：
        # from langgraph.checkpoint.redis import RedisSaver
        # self.checkpointer = RedisSaver.from_conn_info(host="localhost", port=6379)
        self.checkpointer = MemorySaver()
```

**重要说明**：
- `langgraph-checkpoint-redis` 目前可能需要从源码安装或等待官方发布
- 当前实施中，Store 使用 Redis，Checkpoint 仍使用内存（已足够解决会话并发问题）
- 如果需要完整的 checkpoint 持久化，可以参考 LangGraph 文档实现自定义 RedisSaver

---

## 第四步：安装 Redis 并测试

### 1. 安装 Redis（Windows）

```bash
# 使用 Chocolatey
choco install redis-64

# 或下载 Redis for Windows
# https://github.com/microsoftarchive/redis/releases
```

### 2. 启动 Redis

```bash
redis-server
```

### 3. 安装 Python 依赖

```bash
pip install redis aioredis
```

### 4. 测试连接

```bash
# 进入 Python
python

# 测试代码
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
r.ping()  # 应该返回 True
```

---

## 第五步：验证功能

### 1. 启动后端服务

```bash
python intelligent_project_analyzer/api/server.py
```

**预期输出**：
```
✅ Redis 会话管理器已启动
✅ Redis Pub/Sub 已启动
✅ 服务器启动成功
```

### 2. 测试并发会话

打开 3 个浏览器窗口，同时提交不同的分析请求，观察：

- ✅ 所有会话都应该正常推进（不再"转圈圈"）
- ✅ 服务器重启后会话丢失（预期行为，TTL=1小时）
- ✅ WebSocket 消息正确推送到对应窗口

### 3. 检查 Redis 数据

```bash
# Redis CLI
redis-cli

# 查看所有会话键
keys session:*

# 查看某个会话数据
get session:api-20251128120000-abcd1234

# 查看过期时间
ttl session:api-20251128120000-abcd1234
```

---

## 常见问题

### Q: Redis 连接失败怎么办？
A: 系统会自动回退到内存模式，打印警告日志。适用于开发环境。

### Q: 需要修改前端吗？
A: 不需要！前端通过相同的 API 接口通信，完全透明。

### Q: 多实例部署如何配置？
A: 确保所有实例连接到同一个 Redis 服务器，WebSocket 消息会通过 Pub/Sub 自动同步。

### Q: 会话过期时间可以调整吗？
A: 可以！修改 `redis_session_manager.py` 中的 `SESSION_TTL` 常量（单位：秒）。

---

## 性能优化建议

1. **批量更新**：将多个字段合并为一次 `update()` 调用
2. **延长 TTL**：活跃会话调用 `session_manager.extend_ttl(session_id)` 续期
3. **清理过期连接**：定期调用 `session_manager.cleanup_expired()`（内存模式）
4. **Redis 持久化**：生产环境启用 RDB 或 AOF 持久化

---

## 下一步计划

1. 完成 `server.py` 所有 55 处会话访问的替换
2. 测试多窗口并发场景
3. 添加会话统计和监控（活跃会话数、平均TTL等）
4. 考虑添加会话恢复功能（检查 Redis 中的历史会话）

---

**开发者提示**：由于修改点较多，建议：
1. 先修改 3-5 个关键函数测试效果
2. 逐步替换其他函数
3. 运行前端测试每个修改点
4. 使用 `git diff` 检查所有修改

---

## 快速脚本：批量替换会话访问

可以使用以下正则表达式辅助查找替换：

### 查找模式：
```regex
sessions\[session_id\]\["(\w+)"\]\s*=\s*(.+)
```

### 替换为：
```python
await session_manager.update(session_id, {"$1": $2})
```

**警告**：正则替换可能不完美，建议手动检查每处修改！
