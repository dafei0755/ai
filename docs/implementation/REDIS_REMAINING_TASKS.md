# Redis 会话管理 - 剩余修改快速参考

## 当前进度

✅ **已完成 80%**:
- Redis 会话管理器和 Store 已创建
- Redis Pub/Sub 已集成
- `run_workflow_async` 函数主体已修改
- `start_analysis` 和 `get_analysis_status` 已修改

⏳ **剩余 24 处修改**（主要在调试/监控端点）:

---

## 剩余修改清单

### 1. Health 端点（约第 690 行）

**原代码**:
```python
"active_sessions": len(sessions),
```

**新代码**:
```python
"active_sessions": len(await session_manager.list_all_sessions()),
```

---

### 2. Debug 端点（约第 700-714 行）

**原代码**:
```python
"active_sessions": list(sessions.keys()),
"sessions": [
    {
        "session_id": sid,
        "status": sessions[sid].get("status"),
        "current_node": sessions[sid].get("current_node"),
        "has_interrupt": sessions[sid].get("interrupt_data") is not None
    }
    for sid in sessions.keys()
]
```

**新代码**:
```python
session_ids = await session_manager.list_all_sessions()
session_details = []
for sid in session_ids:
    sess = await session_manager.get(sid)
    if sess:
        session_details.append({
            "session_id": sid,
            "status": sess.get("status"),
            "current_node": sess.get("current_node"),
            "has_interrupt": sess.get("interrupt_data") is not None
        })

return {
    "active_sessions": session_ids,
    "sessions": session_details,
    ...
}
```

---

### 3. resume_analysis 函数（约第 800-820 行）

**原代码**:
```python
logger.info(f"   当前活跃会话: {list(sessions.keys())}")

if session_id not in sessions:
    logger.error(f"   可用会话: {list(sessions.keys())}")
    raise HTTPException(...)

session = sessions[session_id]
```

**新代码**:
```python
active_sessions = await session_manager.list_all_sessions()
logger.info(f"   当前活跃会话: {active_sessions}")

if not await session_manager.exists(session_id):
    logger.error(f"   可用会话: {active_sessions}")
    raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

session = await session_manager.get(session_id)
if not session:
    raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")
```

---

### 4. get_analysis_result 函数（约第 1030 行）

**原代码**:
```python
if session_id not in sessions:
    raise HTTPException(...)

session = sessions[session_id]
```

**新代码**:
```python
session = await session_manager.get(session_id)
if not session:
    raise HTTPException(status_code=404, detail="会话不存在")
```

---

### 5. get_analysis_report 函数（约第 1056 行）

同上，替换为:
```python
session = await session_manager.get(session_id)
if not session:
    raise HTTPException(status_code=404, detail="会话不存在")
```

---

### 6. get_all_sessions 函数（约第 1111-1119 行）

**原代码**:
```python
"total": len(sessions),
"sessions": [
    {
        "session_id": sid,
        "status": session.get("status"),
        ...
    }
    for sid, session in sessions.items()
    if session.get("status") in states
]
```

**新代码**:
```python
session_ids = await session_manager.list_all_sessions()
filtered_sessions = []

for sid in session_ids:
    session = await session_manager.get(sid)
    if session and session.get("status") in states:
        filtered_sessions.append({
            "session_id": sid,
            "status": session.get("status"),
            "progress": session.get("progress", 0),
            "created_at": session.get("created_at"),
            "has_interrupt": session.get("interrupt_data") is not None
        })

return {
    "total": len(filtered_sessions),
    "sessions": filtered_sessions
}
```

---

### 7. delete_session 函数（约第 1136 行）

**原代码**:
```python
if session_id not in sessions:
    raise HTTPException(...)

session = sessions[session_id]
del sessions[session_id]
```

**新代码**:
```python
if not await session_manager.exists(session_id):
    raise HTTPException(status_code=404, detail="会话不存在")

await session_manager.delete(session_id)
# 同时清理工作流实例
if session_id in workflows:
    del workflows[session_id]
```

---

### 8. post_conversation 函数（约第 1216-1219 行）

**原代码**:
```python
if session_id not in sessions:
    raise HTTPException(...)

history = sessions[session_id].get("conversation_history", [])
```

**新代码**:
```python
session = await session_manager.get(session_id)
if not session:
    raise HTTPException(status_code=404, detail="会话不存在")

history = session.get("conversation_history", [])
```

---

## 快速批量替换命令（VSCode）

1. **打开替换**（Ctrl+H）

2. **启用正则表达式**

3. **批量替换会话检查**:
   - 查找: `if session_id not in sessions:`
   - 替换: `if not await session_manager.exists(session_id):`

4. **批量替换会话读取**:
   - 查找: `session = sessions\[session_id\]`
   - 替换: `session = await session_manager.get(session_id)\n    if not session:\n        raise HTTPException(status_code=404, detail="会话不存在")`

5. **批量替换会话列表**:
   - 查找: `list\(sessions\.keys\(\)\)`
   - 替换: `await session_manager.list_all_sessions()`

6. **批量替换会话计数**:
   - 查找: `len\(sessions\)`
   - 替换: `len(await session_manager.list_all_sessions())`

---

## 注意事项

1. **函数签名**: 所有修改后的函数必须是 `async def`
2. **await 调用**: 所有 `session_manager` 方法都需要 `await`
3. **错误处理**: 每次 `get()` 后检查返回值是否为 None
4. **循环优化**: 避免在循环中频繁调用 `await`，考虑批量获取

---

## 验证步骤

修改完成后：

1. **检查语法错误**:
   ```bash
   python -m py_compile intelligent_project_analyzer/api/server.py
   ```

2. **启动服务器**:
   ```bash
   python intelligent_project_analyzer/api/server.py
   ```

3. **检查启动日志**:
   应该看到:
   ```
   ✅ Redis 会话管理器已启动
   ✅ Redis Pub/Sub 已启动
   ```

4. **测试基本功能**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/debug
   ```

---

## 如果 Redis 未安装

系统会自动降级到内存模式，打印警告：
```
⚠️ Redis 连接失败
🔄 回退到内存模式（仅适用于开发环境）
```

这种情况下功能正常，但无法解决并发问题。

---

## 下一步

完成上述 24 处修改后：
1. ✅ server.py 会话管理完全迁移到 Redis
2. 🔄 继续修改 main_workflow.py（使用 Redis Store）
3. 🧪 测试并发场景（多浏览器窗口）
4. 📊 监控 Redis 数据（`redis-cli keys session:*`）

---

**预计剩余时间**: 10-15 分钟（使用正则批量替换）
