# 会话归档功能文档 (v3.6)

**功能**: 永久保存会话数据到数据库，突破Redis 7天TTL限制

**实现时间**: 2025-11-29

---

## 一、功能概述

### 1.1 设计目标

- **永久保存**: 突破Redis 7天TTL限制，将会话数据永久保存到数据库
- **自动归档**: 分析完成后自动归档，无需手动操作
- **灵活管理**: 支持重命名、置顶、标签等元数据管理
- **高效检索**: 支持分页、过滤、统计等查询功能

### 1.2 数据流

```
┌─────────────────┐
│   用户提交分析   │
└────────┬────────┘
         │
         v
┌─────────────────────────┐
│  Redis (7天热数据)      │
│  - 活跃会话             │
│  - 实时状态更新         │
│  - TTL: 604800秒        │
└────────┬────────────────┘
         │ 分析完成
         v
┌─────────────────────────┐
│  SQLite/PostgreSQL      │
│  (永久归档)             │
│  - 完整会话数据         │
│  - 元数据管理           │
│  - 无过期时间           │
└─────────────────────────┘
```

---

## 二、核心组件

### 2.1 SessionArchiveManager

**文件**: [intelligent_project_analyzer/services/session_archive_manager.py](d:\11-20\langgraph-design\intelligent_project_analyzer\services\session_archive_manager.py)

**主要方法**:
- `archive_session()` - 归档会话到数据库
- `get_archived_session()` - 获取归档会话
- `list_archived_sessions()` - 列出归档会话（支持分页）
- `update_metadata()` - 更新元数据（重命名、置顶、标签）
- `delete_archived_session()` - 删除归档会话
- `count_archived_sessions()` - 统计归档会话数量

### 2.2 ArchivedSession 数据模型

**表结构**:
```sql
CREATE TABLE archived_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    user_input TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,
    mode VARCHAR(20) DEFAULT 'api',

    created_at DATETIME NOT NULL,
    archived_at DATETIME NOT NULL,
    completed_at DATETIME,

    session_data TEXT NOT NULL,  -- 完整会话状态（JSON）
    final_report TEXT,

    progress INTEGER DEFAULT 0,
    current_stage VARCHAR(100),

    -- 用户管理字段
    display_name VARCHAR(200),
    pinned BOOLEAN DEFAULT FALSE,
    tags VARCHAR(500),

    -- 索引优化
    INDEX idx_created_at_status (created_at, status),
    INDEX idx_pinned_created_at (pinned, created_at),
    INDEX idx_status (status),
    INDEX idx_pinned (pinned)
);
```

### 2.3 API端点

#### 归档操作

**1. 手动归档会话**
```http
POST /api/sessions/{session_id}/archive?force=false
```

**2. 列出归档会话**
```http
GET /api/sessions/archived?limit=50&offset=0&status=completed&pinned_only=false
```

**3. 获取归档会话详情**
```http
GET /api/sessions/archived/{session_id}
```

**4. 更新归档会话元数据**
```http
PATCH /api/sessions/archived/{session_id}
Content-Type: application/json

{
  "display_name": "重要项目分析",
  "pinned": true,
  "tags": ["建筑设计", "高优先级"]
}
```

**5. 删除归档会话**
```http
DELETE /api/sessions/archived/{session_id}
```

**6. 获取归档统计**
```http
GET /api/sessions/archived/stats
```

---

## 三、使用示例

### 3.1 自动归档（默认行为）

分析完成后，系统会自动归档会话：

```python
# server.py:687-701
# 🆕 v3.6新增: 自动归档完成的会话（永久保存）
if archive_manager:
    try:
        final_session = await session_manager.get(session_id)
        if final_session:
            await archive_manager.archive_session(
                session_id=session_id,
                session_data=final_session,
                force=False  # 仅归档completed状态的会话
            )
            logger.info(f"📦 会话已自动归档（永久保存）: {session_id}")
    except Exception as archive_error:
        logger.warning(f"⚠️ 自动归档失败（不影响主流程）: {archive_error}")
```

**日志输出**:
```
✅ 会话归档管理器已启动（永久保存功能已启用）
...
📦 会话已自动归档（永久保存）: api-20251129102622-d5509e65
```

### 3.2 手动归档（强制归档）

如果需要归档未完成的会话（例如调试或备份）：

```bash
curl -X POST "http://localhost:8000/api/sessions/api-20251129102622-d5509e65/archive?force=true"
```

**响应**:
```json
{
  "success": true,
  "session_id": "api-20251129102622-d5509e65",
  "message": "会话已成功归档到数据库（永久保存）"
}
```

### 3.3 列出归档会话

**获取所有归档会话（最近50个）**:
```bash
curl "http://localhost:8000/api/sessions/archived?limit=50&offset=0"
```

**响应**:
```json
{
  "total": 125,
  "limit": 50,
  "offset": 0,
  "sessions": [
    {
      "session_id": "api-20251129102622-d5509e65",
      "user_input": "为一位处于事业转型期的前金融律师...",
      "status": "completed",
      "display_name": "金融律师转型项目",
      "pinned": true,
      "tags": ["建筑设计", "高优先级"],
      "created_at": "2025-11-29T10:26:22",
      "archived_at": "2025-11-29T12:15:30",
      "progress": 100
    },
    ...
  ]
}
```

**仅显示置顶会话**:
```bash
curl "http://localhost:8000/api/sessions/archived?pinned_only=true"
```

**按状态过滤**:
```bash
curl "http://localhost:8000/api/sessions/archived?status=completed"
```

### 3.4 更新元数据

**重命名会话**:
```bash
curl -X PATCH "http://localhost:8000/api/sessions/archived/api-20251129102622-d5509e65" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "重要项目 - 金融律师转型"}'
```

**置顶会话**:
```bash
curl -X PATCH "http://localhost:8000/api/sessions/archived/api-20251129102622-d5509e65" \
  -H "Content-Type: application/json" \
  -d '{"pinned": true}'
```

**添加标签**:
```bash
curl -X PATCH "http://localhost:8000/api/sessions/archived/api-20251129102622-d5509e65" \
  -H "Content-Type: application/json" \
  -d '{"tags": ["建筑设计", "住宅项目", "高优先级"]}'
```

### 3.5 获取统计信息

```bash
curl "http://localhost:8000/api/sessions/archived/stats"
```

**响应**:
```json
{
  "total": 125,
  "by_status": {
    "completed": 110,
    "failed": 10,
    "rejected": 5
  },
  "pinned": 15,
  "updated_at": "2025-11-29T19:30:00"
}
```

---

## 四、配置说明

### 4.1 数据库配置

**默认配置** (SQLite):
```python
# session_archive_manager.py
data_dir = Path(__file__).parent.parent.parent / "data"
database_url = f"sqlite:///{data_dir / 'archived_sessions.db'}"
```

**数据库文件位置**:
```
d:\11-20\langgraph-design\
  data/
    archived_sessions.db  # 归档数据库
```

**切换到PostgreSQL** (可选):
```python
# settings.py
archive_database_url = "postgresql://user:password@localhost:5432/project_analyzer_archive"

# session_archive_manager.py
archive_manager = SessionArchiveManager(database_url=settings.archive_database_url)
```

### 4.2 初始化流程

**服务器启动时** (server.py:109-115):
```python
# ✅ v3.6新增: 初始化会话归档管理器
try:
    archive_manager = SessionArchiveManager()
    print("✅ 会话归档管理器已启动（永久保存功能已启用）")
except Exception as e:
    logger.error(f"❌ 会话归档管理器启动失败: {e}")
    print("⚠️ 会话归档管理器启动失败（无法使用永久保存功能）")
```

**启动日志**:
```
============================================================
  🤖 智能项目分析系统 - API 服务器
============================================================

✅ Redis 会话管理器已启动
✅ 会话归档管理器已启动（永久保存功能已启用）
✅ Redis Pub/Sub 已启动
✅ 服务器启动成功
📍 API 文档: http://localhost:8000/docs
📍 健康检查: http://localhost:8000/health
```

---

## 五、数据管理策略

### 5.1 双层存储架构

**Redis (热数据 - 7天)**:
- 存储活跃会话
- 实时状态更新
- 快速查询
- 自动过期清理

**SQLite/PostgreSQL (冷数据 - 永久)**:
- 归档完成的会话
- 历史记录查询
- 长期统计分析
- 无过期时间

### 5.2 自动归档触发点

1. **分析完成后** (run_workflow_async):
   - 检测到 `status == "completed"`
   - 自动调用 `archive_manager.archive_session()`
   - 日志: `📦 会话已自动归档（永久保存）: {session_id}`

2. **恢复完成后** (resume_analysis -> continue_workflow):
   - 检测到 `status == "completed"`
   - 自动调用 `archive_manager.archive_session()`

### 5.3 重复归档保护

**防重复归档机制** (session_archive_manager.py:104-109):
```python
# 检查是否已存在
existing = db.query(ArchivedSession).filter(
    ArchivedSession.session_id == session_id
).first()

if existing and not force:
    logger.warning(f"⚠️ 会话已归档，跳过: {session_id}")
    return False  # 已存在，跳过归档
```

---

## 六、API端点详细说明

### 6.1 POST /api/sessions/{session_id}/archive

**描述**: 归档会话到数据库（永久保存）

**参数**:
- `session_id` (路径参数) - 会话ID
- `force` (查询参数, 可选) - 是否强制归档（默认: false）

**返回**:
```json
{
  "success": true,
  "session_id": "api-20251129102622-d5509e65",
  "message": "会话已成功归档到数据库（永久保存）"
}
```

**错误**:
- `404` - 会话不存在
- `400` - 会话归档失败（可能已归档或状态不允许）
- `503` - 归档功能未启用

---

### 6.2 GET /api/sessions/archived

**描述**: 列出归档会话（支持分页、过滤）

**参数**:
- `limit` (查询参数, 可选) - 每页数量（默认: 50）
- `offset` (查询参数, 可选) - 偏移量（默认: 0）
- `status` (查询参数, 可选) - 过滤状态（completed/failed/rejected）
- `pinned_only` (查询参数, 可选) - 是否只显示置顶会话（默认: false）

**返回**:
```json
{
  "total": 125,
  "limit": 50,
  "offset": 0,
  "sessions": [
    {
      "session_id": "api-20251129102622-d5509e65",
      "user_input": "为一位处于事业转型期的前金融律师...",
      "status": "completed",
      "display_name": "金融律师转型项目",
      "pinned": true,
      "tags": ["建筑设计", "高优先级"],
      "created_at": "2025-11-29T10:26:22",
      "archived_at": "2025-11-29T12:15:30",
      "progress": 100,
      "current_stage": "pdf_generator"
    }
  ]
}
```

---

### 6.3 GET /api/sessions/archived/{session_id}

**描述**: 获取归档会话详情

**参数**:
- `session_id` (路径参数) - 会话ID

**返回**:
```json
{
  "session_id": "api-20251129102622-d5509e65",
  "user_input": "为一位处于事业转型期的前金融律师...",
  "status": "completed",
  "mode": "api",
  "created_at": "2025-11-29T10:26:22",
  "archived_at": "2025-11-29T12:15:30",
  "completed_at": "2025-11-29T12:15:15",
  "session_data": "{...}",  # 完整会话状态（JSON）
  "final_report": "# 项目分析报告...",
  "progress": 100,
  "current_stage": "pdf_generator",
  "display_name": "金融律师转型项目",
  "pinned": true,
  "tags": "建筑设计,住宅项目,高优先级"
}
```

---

### 6.4 PATCH /api/sessions/archived/{session_id}

**描述**: 更新归档会话元数据（重命名、置顶、标签）

**参数**:
- `session_id` (路径参数) - 会话ID

**请求体**:
```json
{
  "display_name": "重要项目 - 金融律师转型",
  "pinned": true,
  "tags": ["建筑设计", "住宅项目", "高优先级"]
}
```

**返回**:
```json
{
  "success": true,
  "session_id": "api-20251129102622-d5509e65",
  "message": "元数据更新成功"
}
```

---

### 6.5 DELETE /api/sessions/archived/{session_id}

**描述**: 删除归档会话

**参数**:
- `session_id` (路径参数) - 会话ID

**返回**:
```json
{
  "success": true,
  "session_id": "api-20251129102622-d5509e65",
  "message": "归档会话删除成功"
}
```

**错误**:
- `404` - 归档会话不存在

---

### 6.6 GET /api/sessions/archived/stats

**描述**: 获取归档会话统计信息

**返回**:
```json
{
  "total": 125,
  "by_status": {
    "completed": 110,
    "failed": 10,
    "rejected": 5
  },
  "pinned": 15,
  "updated_at": "2025-11-29T19:30:00"
}
```

---

## 七、前端集成指南

### 7.1 历史记录页面

**数据获取**:
```typescript
// 获取归档会话列表
async function getArchivedSessions(page: number = 1, limit: number = 20) {
  const offset = (page - 1) * limit;
  const response = await fetch(
    `http://localhost:8000/api/sessions/archived?limit=${limit}&offset=${offset}`
  );
  return await response.json();
}

// 仅显示置顶会话
async function getPinnedSessions() {
  const response = await fetch(
    `http://localhost:8000/api/sessions/archived?pinned_only=true`
  );
  return await response.json();
}
```

**显示逻辑**:
```typescript
interface ArchivedSession {
  session_id: string;
  user_input: string;
  status: 'completed' | 'failed' | 'rejected';
  display_name?: string;
  pinned: boolean;
  tags?: string[];
  created_at: string;
  archived_at: string;
  progress: number;
}

function HistoryList({ sessions }: { sessions: ArchivedSession[] }) {
  return (
    <div>
      {sessions.map(session => (
        <div key={session.session_id}>
          {session.pinned && <span>📌</span>}
          <h3>{session.display_name || session.user_input.slice(0, 50)}</h3>
          <p>状态: {session.status}</p>
          <p>创建时间: {new Date(session.created_at).toLocaleString()}</p>
          {session.tags && (
            <div>
              {session.tags.map(tag => <span key={tag} className="tag">{tag}</span>)}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

### 7.2 会话管理操作

**重命名会话**:
```typescript
async function renameSession(sessionId: string, newName: string) {
  const response = await fetch(
    `http://localhost:8000/api/sessions/archived/${sessionId}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: newName })
    }
  );
  return await response.json();
}
```

**置顶/取消置顶**:
```typescript
async function togglePin(sessionId: string, pinned: boolean) {
  const response = await fetch(
    `http://localhost:8000/api/sessions/archived/${sessionId}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pinned })
    }
  );
  return await response.json();
}
```

**添加标签**:
```typescript
async function updateTags(sessionId: string, tags: string[]) {
  const response = await fetch(
    `http://localhost:8000/api/sessions/archived/${sessionId}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tags })
    }
  );
  return await response.json();
}
```

**删除会话**:
```typescript
async function deleteSession(sessionId: string) {
  const response = await fetch(
    `http://localhost:8000/api/sessions/archived/${sessionId}`,
    { method: 'DELETE' }
  );
  return await response.json();
}
```

### 7.3 统计仪表板

```typescript
async function getArchiveStats() {
  const response = await fetch(
    'http://localhost:8000/api/sessions/archived/stats'
  );
  return await response.json();
}

function StatsDashboard() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    getArchiveStats().then(setStats);
  }, []);

  if (!stats) return <div>Loading...</div>;

  return (
    <div>
      <h2>归档统计</h2>
      <p>总会话数: {stats.total}</p>
      <p>已完成: {stats.by_status.completed}</p>
      <p>失败: {stats.by_status.failed}</p>
      <p>已拒绝: {stats.by_status.rejected}</p>
      <p>置顶会话: {stats.pinned}</p>
    </div>
  );
}
```

---

## 八、维护和优化

### 8.1 数据库维护

**查看数据库大小**:
```bash
# SQLite
ls -lh data/archived_sessions.db

# PostgreSQL
SELECT pg_size_pretty(pg_database_size('project_analyzer_archive'));
```

**清理旧归档** (可选):
```sql
-- 删除1年前的失败会话
DELETE FROM archived_sessions
WHERE status = 'failed'
  AND archived_at < datetime('now', '-1 year');

-- 删除2年前的已拒绝会话
DELETE FROM archived_sessions
WHERE status = 'rejected'
  AND archived_at < datetime('now', '-2 years');
```

### 8.2 性能优化

**索引优化** (已实现):
```python
Index('idx_created_at_status', 'created_at', 'status'),
Index('idx_pinned_created_at', 'pinned', 'created_at'),
```

**查询优化建议**:
- 使用分页查询（`limit` + `offset`）
- 按索引字段过滤（`status`, `pinned`, `created_at`）
- 避免全表扫描

**缓存策略** (可选):
```python
# 缓存统计数据（Redis）
@cache(ttl=300)  # 缓存5分钟
async def get_archive_stats():
    # ...
```

### 8.3 备份策略

**SQLite备份**:
```bash
# 定期备份数据库文件
cp data/archived_sessions.db backups/archived_sessions_$(date +%Y%m%d).db

# 使用cron定时备份（每天凌晨2点）
0 2 * * * cd /path/to/project && cp data/archived_sessions.db backups/archived_sessions_$(date +\%Y\%m\%d).db
```

**PostgreSQL备份**:
```bash
# 使用pg_dump备份
pg_dump -U user -d project_analyzer_archive -F c -f backups/archive_$(date +%Y%m%d).dump

# 定期备份（每天凌晨2点）
0 2 * * * pg_dump -U user -d project_analyzer_archive -F c -f /path/to/backups/archive_$(date +\%Y\%m\%d).dump
```

---

## 九、故障排查

### 9.1 常见问题

**问题1: 归档功能未启用**

**症状**:
```
⚠️ 会话归档管理器启动失败（无法使用永久保存功能）
```

**原因**:
- 数据目录权限不足
- SQLAlchemy未安装
- 数据库连接失败

**解决方案**:
```bash
# 检查数据目录权限
ls -ld data/
chmod 755 data/

# 确认SQLAlchemy已安装
pip install sqlalchemy

# 检查数据库文件
ls -l data/archived_sessions.db
```

---

**问题2: 自动归档失败**

**症状**:
```
⚠️ 自动归档失败（不影响主流程）: [Errno 13] Permission denied
```

**原因**:
- 数据库文件权限不足
- 磁盘空间不足

**解决方案**:
```bash
# 检查磁盘空间
df -h

# 修复权限
chmod 644 data/archived_sessions.db
```

---

**问题3: 重复归档**

**症状**:
```
⚠️ 会话已归档，跳过: api-20251129102622-d5509e65
```

**说明**: 这是正常行为，防止重复归档保护机制生效

**强制重新归档** (如果需要):
```bash
curl -X POST "http://localhost:8000/api/sessions/api-20251129102622-d5509e65/archive?force=true"
```

---

**问题4: 查询性能慢**

**症状**: 归档会话列表加载缓慢

**诊断**:
```sql
-- 检查索引是否存在
SELECT * FROM sqlite_master WHERE type='index' AND tbl_name='archived_sessions';

-- 分析查询计划
EXPLAIN QUERY PLAN SELECT * FROM archived_sessions WHERE status = 'completed' ORDER BY created_at DESC LIMIT 50;
```

**优化**:
```python
# 确保使用索引字段排序和过滤
sessions = await archive_manager.list_archived_sessions(
    limit=50,
    offset=0,
    status="completed"  # 使用索引字段
)
```

---

## 十、总结

### 10.1 功能特性

✅ **永久保存**: 突破Redis 7天TTL限制，会话数据永久存储
✅ **自动归档**: 分析完成后自动归档，无需手动操作
✅ **灵活管理**: 支持重命名、置顶、标签等元数据管理
✅ **高效检索**: 支持分页、过滤、统计等查询功能
✅ **前端友好**: 提供完整的RESTful API接口
✅ **性能优化**: 数据库索引、分页查询、防重复归档
✅ **故障隔离**: 归档失败不影响主流程

### 10.2 应用场景

1. **历史记录查询**: 查看所有历史分析结果
2. **项目管理**: 重命名、置顶、标签管理重要项目
3. **统计分析**: 查看完成率、失败率等统计数据
4. **数据备份**: 永久保存重要分析结果
5. **审计跟踪**: 记录所有分析活动

### 10.3 版本信息

- **版本**: v3.6
- **实现时间**: 2025-11-29
- **实现者**: Claude (Droid)
- **相关文档**:
  - [session_storage_investigation.md](d:\11-20\langgraph-design\docs\session_storage_investigation.md) - 会话存储机制调查
  - [session_storage_fix_test_report.md](d:\11-20\langgraph-design\docs\session_storage_fix_test_report.md) - 会话存储修复测试报告
  - [redis_persistence_setup.md](d:\11-20\langgraph-design\docs\redis_persistence_setup.md) - Redis持久化配置指南

---

**文档作者**: Claude (Droid)
**创建时间**: 2025-11-29
**最后更新**: 2025-11-29
