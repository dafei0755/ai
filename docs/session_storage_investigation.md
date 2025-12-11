# 历史记录会话保存机制调查报告

**调查时间**: 2025-11-29
**问题描述**: 历史记录会话不稳定，有时只有最近1条，有时有多条

---

## 一、当前保存机制

### 1.1 存储架构

**使用Redis作为会话存储**:
- 文件: [redis_session_manager.py](d:\11-20\langgraph-design\intelligent_project_analyzer\services\redis_session_manager.py)
- 连接配置: `redis://localhost:6379/0` (默认)
- 支持内存回退模式（Redis不可用时）

**键命名规则**:
```python
SESSION_PREFIX = "session:"        # 会话数据: session:{session_id}
LOCK_PREFIX = "lock:session:"      # 分布式锁: lock:session:{session_id}
WEBSOCKET_PREFIX = "ws:session:"   # WebSocket: ws:session:{session_id}
```

### 1.2 会话TTL（过期时间）

**关键配置** (Line 60):
```python
SESSION_TTL = 3600  # 会话过期时间：1小时
```

**TTL机制**:
1. **创建会话时** (Line 158-162):
   ```python
   await self.redis_client.setex(
       key,
       self.SESSION_TTL,  # 1小时后自动过期
       json.dumps(sanitized_data, ...)
   )
   ```

2. **更新会话时** (Line 248-253):
   ```python
   await self.redis_client.setex(
       key,
       self.SESSION_TTL,  # 刷新TTL到1小时
       json.dumps(sanitized_session, ...)
   )
   ```

3. **手动延长TTL** (Line 318-342):
   ```python
   async def extend_ttl(self, session_id: str, ttl: Optional[int] = None):
       """延长会话过期时间（用于活跃会话续期）"""
       ttl = ttl or self.SESSION_TTL
       await self.redis_client.expire(key, ttl)
   ```

---

## 二、问题根因分析

### 2.1 会话自动过期

**现象**: 有时候只有最近1条历史记录

**原因**:
- ✅ **TTL设置为1小时** - 超过1小时未活动的会话会被Redis自动删除
- ✅ **Redis自动清理过期键** - 不需要手动清理

**证据**:
```python
# redis_session_manager.py:60
SESSION_TTL = 3600  # 1小时 = 3600秒
```

**影响**:
- 用户在1小时后打开应用，之前的会话已被清理
- 只剩下最近创建的会话（最近1小时内）

### 2.2 Redis连接不稳定

**现象**: 有时有多条，有时只有1条（不稳定）

**可能原因**:
1. **Redis服务未启动或重启**:
   - Redis重启后所有内存数据丢失（非持久化配置）
   - 系统回退到内存模式，会话只保存在进程内存中

2. **Redis连接超时/失败**:
   - Line 88-116: 连接失败时自动回退到内存模式
   - 内存模式下，服务器重启会丢失所有会话

3. **API服务器重启**:
   - 如果使用内存回退模式，服务器重启会清空所有会话
   - Redis模式下不受影响（数据持久化在Redis）

**日志证据**:
```python
# Line 102-103: 成功连接
logger.info(f"✅ Redis 连接成功: {self.redis_url}")

# Line 107-110: 连接失败，回退内存模式
logger.warning(f"⚠️ Redis 连接失败: {e}")
logger.warning("🔄 回退到内存模式（仅适用于开发环境）")
```

### 2.3 会话列表获取逻辑

**API端点**: `/api/sessions` (Line 1190-1219)

**获取逻辑** (Line 1199):
```python
all_sessions = await session_manager.get_all_sessions()
```

**实现细节** (redis_session_manager.py:402-435):
```python
async def get_all_sessions(self) -> List[Dict[str, Any]]:
    # Redis模式 - 扫描所有会话键
    async for key in self.redis_client.scan_iter(match=f"{self.SESSION_PREFIX}*", count=100):
        data = await self.redis_client.get(key)
        if data:
            session = json.loads(data)
            sessions.append(session)

    # 按创建时间倒序排序（最新的在前面）
    sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return sessions
```

**潜在问题**:
- ❌ **SCAN操作可能遗漏键** - 如果在扫描过程中有键过期
- ❌ **无分页支持** - 如果会话数量很多（虽然有TTL限制）
- ✅ **已按时间排序** - 最新的在前面

---

## 三、不稳定的具体表现

### 场景1: 只有最近1条
**原因**: TTL过期清理
- 用户上次使用时间 > 1小时前
- 旧会话已被Redis自动删除
- 只剩下最近创建的会话

**解决方案**: 延长TTL或添加持久化

### 场景2: 数量不一致（随机）
**原因**: Redis连接状态切换
- **稳定时**: Redis正常，返回所有未过期会话
- **不稳定时**: Redis连接失败，回退内存模式，返回内存中的会话（可能为空或只有部分）

**日志表现**:
```
# 成功时
✅ Redis 连接成功: redis://localhost:6379/0
[Redis] 获取所有会话: 5个

# 失败时
⚠️ Redis 连接失败: Connection refused
🔄 回退到内存模式（仅适用于开发环境）
[内存] 获取所有会话: 0个（服务器刚重启）或 1个（只有当前会话）
```

### 场景3: 服务器重启后会话丢失
**原因**:
- **内存模式**: 服务器重启，所有会话丢失
- **Redis模式**:
  - 如果Redis配置了持久化（RDB/AOF）→ 数据不丢失
  - 如果Redis未配置持久化 → Redis重启后数据丢失

---

## 四、Redis持久化配置检查

### 4.1 Redis配置状态

**需要检查的Redis配置**:
```bash
# 连接到Redis
redis-cli

# 检查持久化配置
CONFIG GET save           # RDB快照配置
CONFIG GET appendonly     # AOF持久化配置
CONFIG GET dir            # 数据目录

# 查看当前数据库大小
DBSIZE

# 查看会话键数量
KEYS session:*
```

**典型问题**:
- ❌ Redis默认配置可能未启用持久化
- ❌ Redis以Docker方式运行时，数据可能未挂载到主机
- ❌ Redis内存不足时可能驱逐键（eviction policy）

### 4.2 推荐的Redis配置

**RDB持久化** (redis.conf):
```conf
# 每900秒（15分钟）如果至少1个key改变，则保存
save 900 1
# 每300秒（5分钟）如果至少10个key改变，则保存
save 300 10
# 每60秒如果至少10000个key改变，则保存
save 60 10000
```

**AOF持久化** (更安全):
```conf
appendonly yes
appendfsync everysec  # 每秒同步一次
```

---

## 五、解决方案

### 方案1: 延长会话TTL ⭐ **快速修复**

**问题**: 1小时TTL太短，用户隔天打开应用会话已清空

**修改** (redis_session_manager.py:60):
```python
# 当前
SESSION_TTL = 3600  # 1小时

# 修改为
SESSION_TTL = 86400  # 24小时 = 1天
# 或
SESSION_TTL = 604800  # 7天 = 1周
```

**优势**:
- ✅ 立即生效，无需配置Redis
- ✅ 用户可以看到历史会话
- ⚠️ 会占用更多Redis内存

### 方案2: 启用Redis持久化 ⭐ **推荐**

**修改Redis配置**:
```bash
# 编辑redis.conf
appendonly yes
appendfsync everysec
save 900 1
save 300 10
save 60 10000

# 重启Redis
redis-server /path/to/redis.conf
```

**优势**:
- ✅ 数据不会因Redis重启而丢失
- ✅ 支持数据恢复
- ⚠️ 略微影响性能（但可接受）

### 方案3: 实现会话归档机制

**设计思路**:
1. **活跃会话** (Redis) - TTL = 1小时
2. **归档会话** (数据库) - 永久保存（或很长TTL）

**实现**:
```python
# 新增归档管理器
class SessionArchiveManager:
    """会话归档管理器 - 持久化到数据库"""

    async def archive_session(self, session_id: str):
        """将会话归档到数据库"""
        session = await session_manager.get(session_id)
        if session:
            # 保存到SQLite/PostgreSQL
            await db.save_archived_session(session)

    async def get_archived_sessions(self, limit: int = 50):
        """获取归档会话列表"""
        return await db.query_archived_sessions(limit=limit)

# API修改
@app.get("/api/sessions")
async def list_sessions(include_archived: bool = False):
    # 获取活跃会话（Redis）
    active_sessions = await session_manager.get_all_sessions()

    if include_archived:
        # 获取归档会话（数据库）
        archived_sessions = await archive_manager.get_archived_sessions()
        all_sessions = active_sessions + archived_sessions
    else:
        all_sessions = active_sessions

    return {"sessions": all_sessions}
```

**优势**:
- ✅ 分离热数据（Redis）和冷数据（数据库）
- ✅ 支持历史查询和统计
- ✅ Redis内存可控
- ⚠️ 实现较复杂

### 方案4: 添加会话续期机制

**自动续期** - 对活跃会话延长TTL:
```python
# 在API调用时自动续期
@app.get("/api/analysis/status/{session_id}")
async def get_status(session_id: str):
    # 获取会话
    session = await session_manager.get(session_id)

    # 自动续期（活跃会话）
    await session_manager.extend_ttl(session_id)

    return session
```

**优势**:
- ✅ 活跃会话不会过期
- ✅ 不活跃会话自动清理
- ✅ 无需修改TTL配置

### 方案5: 检查并修复Redis连接

**添加健康检查**:
```python
@app.get("/api/debug/redis")
async def check_redis_connection():
    """检查Redis连接状态"""
    try:
        if session_manager._memory_mode:
            return {
                "mode": "memory",
                "warning": "Redis不可用，使用内存模式",
                "sessions_in_memory": len(session_manager._memory_sessions)
            }

        # 测试Redis连接
        await session_manager.redis_client.ping()
        session_count = len(await session_manager.list_all_sessions())

        return {
            "mode": "redis",
            "status": "connected",
            "redis_url": session_manager.redis_url,
            "session_count": session_count
        }
    except Exception as e:
        return {
            "mode": "error",
            "error": str(e)
        }
```

---

## 六、推荐实施方案

### 立即实施（快速修复）:
1. ✅ **延长TTL到24小时或7天** (方案1)
2. ✅ **添加Redis健康检查端点** (方案5)
3. ✅ **添加自动续期机制** (方案4)

### 短期实施（本周）:
4. ✅ **启用Redis持久化** (方案2)
5. ✅ **测试Redis连接稳定性**

### 长期优化（未来）:
6. 🔮 **实现会话归档机制** (方案3)
7. 🔮 **添加会话搜索和过滤功能**
8. 🔮 **实现会话标签和分类**

---

## 七、验证清单

修复后需要验证：

- [ ] 检查Redis是否正常运行
  ```bash
  redis-cli ping  # 应返回 PONG
  ```

- [ ] 检查持久化配置
  ```bash
  redis-cli CONFIG GET save
  redis-cli CONFIG GET appendonly
  ```

- [ ] 测试会话保存和过期
  ```bash
  # 创建会话
  curl -X POST http://localhost:8000/api/analysis/start

  # 等待2小时

  # 检查会话是否仍存在
  curl http://localhost:8000/api/sessions
  ```

- [ ] 测试服务器重启后会话恢复
  ```bash
  # 创建会话
  # 重启API服务器
  # 检查会话是否仍在Redis中
  ```

- [ ] 检查会话数量稳定性
  ```bash
  # 多次调用，检查返回数量是否一致
  curl http://localhost:8000/api/sessions
  ```

---

## 八、当前配置建议

**立即修改** (redis_session_manager.py):
```python
# Line 60: 延长TTL
SESSION_TTL = 604800  # 7天（从1小时改为7天）
```

**Redis配置建议** (redis.conf 或 docker-compose.yml):
```yaml
redis:
  command: redis-server --appendonly yes --appendfsync everysec
  volumes:
    - ./redis_data:/data  # 持久化数据
```

---

**调查者**: Claude (Droid)
**调查时间**: 2025-11-29
**结论**: 会话不稳定主要因为1小时TTL太短 + Redis可能未配置持久化
