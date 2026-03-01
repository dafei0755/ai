# 数据库架构优化方案

## 📊 现状评估

### 当前问题
1. ⚠️ **多个 `declarative_base()` 实例**：导致模型管理混乱
   - `session_archive_manager.py` 有独立 Base
   - `taxonomy_models.py` 有独立 Base
   - `external_projects.py` 有独立 Base

2. ⚠️ **SQLite 性能瓶颈**：主业务使用 SQLite，不适合生产环境
   - 无并发写入支持
   - 无网络访问能力
   - 缺乏高级索引（如向量索引）

3. ✅ **爬虫系统已分离**：正确做法，应保持

### 目标架构

```
生产环境数据库布局：

┌─── 主业务数据库 (PostgreSQL) ────────────────────┐
│ DATABASE_URL=postgresql://...5432/ipa_main        │
│                                                    │
│ 📁 用户模块                                        │
│ ├─ users (用户表)                                 │
│ ├─ user_sessions (会话表)                        │
│ └─ device_sessions (设备会话)                    │
│                                                    │
│ 📁 分析模块                                        │
│ ├─ archived_search_sessions (搜索历史)           │
│ ├─ archived_analysis_sessions (分析历史)         │
│ ├─ project_analysis_results (分析结果)           │
│ └─ image_metadata (图片元数据)                   │
│                                                    │
│ 📁 学习模块                                        │
│ ├─ taxonomy_extended_types (扩展维度)            │
│ ├─ taxonomy_emerging_types (新兴标签)            │
│ └─ dimension_usage_stats (维度使用统计)          │
└────────────────────────────────────────────────────┘

┌─── 外部数据仓库 (PostgreSQL + pgvector) ─────────┐
│ EXTERNAL_DB_URL=postgresql://...5432/ipa_external │
│                                                    │
│ 📁 爬虫数据（10万+项目）                           │
│ ├─ external_projects (建筑案例)                  │
│ ├─ external_project_images (案例图片)            │
│ ├─ sync_history (同步历史)                       │
│ └─ quality_issues (质量问题)                     │
│                                                    │
│ 特性：                                             │
│ ✅ pgvector 向量索引（语义搜索）                   │
│ ✅ 独立备份策略（每周全量，每日增量）              │
│ ✅ 可独立扩展（大数据量不影响主库）                │
└────────────────────────────────────────────────────┘

┌─── 缓存层 (Redis) ────────────────────────────────┐
│ REDIS_URL=redis://localhost:6379                  │
│                                                    │
│ DB 0: 会话缓存 (TTL=7天)                          │
│ DB 1: 搜索缓存 (TTL=1小时)                        │
│ DB 2: Celery 任务队列                             │
│ DB 3: 限流计数器                                  │
└────────────────────────────────────────────────────┘
```

## 🎯 实施计划

### Phase 1: 统一数据库模型管理（高优先级）

**目标**：解决多个 `declarative_base()` 问题

**操作步骤**：

1. **创建统一的模型基类**

```python
# intelligent_project_analyzer/models/base.py
from sqlalchemy.ext.declarative import declarative_base

# 主业务数据库 Base
MainBase = declarative_base()

# 外部数据库 Base（已有）
ExternalBase = declarative_base()
```

2. **迁移现有模型**

```python
# session_archive_manager.py
from intelligent_project_analyzer.models.base import MainBase as Base

class ArchivedSearchSession(Base):
    __tablename__ = "archived_search_sessions"
    # ...

# taxonomy_models.py
from intelligent_project_analyzer.models.base import MainBase as Base

class TaxonomyExtendedType(Base):
    __tablename__ = "taxonomy_extended_types"
    # ...

# external_projects.py (已分离，保持独立)
from intelligent_project_analyzer.models.base import ExternalBase as Base

class ExternalProject(Base):
    __tablename__ = "external_projects"
    # ...
```

3. **创建统一的数据库管理器**

```python
# intelligent_project_analyzer/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from intelligent_project_analyzer.models.base import MainBase, ExternalBase
import os

class DatabaseManager:
    """统一数据库管理器"""

    def __init__(self):
        # 主业务数据库
        self.main_url = os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:password@localhost:5432/ipa_main'
        )
        self.main_engine = create_engine(self.main_url, pool_size=20)
        self.MainSession = sessionmaker(bind=self.main_engine)

        # 外部数据仓库
        self.external_url = os.getenv(
            'EXTERNAL_DB_URL',
            'postgresql://postgres:password@localhost:5432/ipa_external'
        )
        self.external_engine = create_engine(self.external_url, pool_size=10)
        self.ExternalSession = sessionmaker(bind=self.external_engine)

    def create_all_tables(self):
        """创建所有表"""
        MainBase.metadata.create_all(self.main_engine)
        ExternalBase.metadata.create_all(self.external_engine)

    def get_main_session(self):
        """获取主业务会话"""
        return self.MainSession()

    def get_external_session(self):
        """获取外部数据会话"""
        return self.ExternalSession()

# 全局实例
db_manager = DatabaseManager()
```

### Phase 2: 主业务数据库迁移到 PostgreSQL（中优先级）

**当前**：SQLite (`sqlite:///./data/archived_sessions.db`)
**目标**：PostgreSQL (`postgresql://localhost/ipa_main`)

**迁移脚本**：

```python
# scripts/migrate_sqlite_to_postgresql.py
import sqlite3
import psycopg2
from sqlalchemy import create_engine, MetaData, Table
from loguru import logger

def migrate_database():
    """将 SQLite 数据迁移到 PostgreSQL"""

    # 连接 SQLite
    sqlite_conn = sqlite3.connect('./data/archived_sessions.db')
    sqlite_cursor = sqlite_conn.cursor()

    # 连接 PostgreSQL
    pg_conn = psycopg2.connect(
        host='localhost',
        database='ipa_main',
        user='postgres',
        password='password'
    )
    pg_cursor = pg_conn.cursor()

    # 获取所有表
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in sqlite_cursor.fetchall()]

    for table in tables:
        logger.info(f"正在迁移表: {table}")

        # 读取 SQLite 数据
        sqlite_cursor.execute(f"SELECT * FROM {table}")
        rows = sqlite_cursor.fetchall()

        # 获取列名
        columns = [desc[0] for desc in sqlite_cursor.description]

        # 批量插入 PostgreSQL
        if rows:
            placeholders = ','.join(['%s'] * len(columns))
            insert_sql = f"""
                INSERT INTO {table} ({','.join(columns)})
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """
            pg_cursor.executemany(insert_sql, rows)
            pg_conn.commit()

        logger.info(f"✅ 表 {table} 迁移完成: {len(rows)} 条记录")

    sqlite_conn.close()
    pg_conn.close()
    logger.info("🎉 数据库迁移完成")

if __name__ == '__main__':
    migrate_database()
```

**执行命令**：

```bash
# 1. 创建 PostgreSQL 数据库
createdb -U postgres ipa_main

# 2. 运行迁移脚本
python scripts/migrate_sqlite_to_postgresql.py

# 3. 验证数据
psql -U postgres -d ipa_main -c "SELECT COUNT(*) FROM archived_search_sessions"

# 4. 更新 .env 配置
# DATABASE_URL=postgresql://postgres:password@localhost:5432/ipa_main

# 5. 重启服务
```

### Phase 3: 优化查询性能（低优先级）

1. **添加数据库索引**

```sql
-- 主业务数据库索引
CREATE INDEX idx_search_user_time ON archived_search_sessions(user_id, created_at DESC);
CREATE INDEX idx_analysis_session_time ON archived_analysis_sessions(session_id, created_at DESC);
CREATE INDEX idx_taxonomy_dimension_usage ON taxonomy_extended_types(dimension, usage_count DESC);

-- 外部数据库索引
CREATE INDEX idx_external_source_quality ON external_projects(source, quality_score DESC);
CREATE INDEX idx_external_year_category ON external_projects(year, primary_category);

-- 向量索引（需要 pgvector 扩展）
CREATE INDEX idx_description_vector ON external_projects
USING ivfflat (description_vector vector_cosine_ops)
WITH (lists = 100);
```

2. **配置连接池**

```python
# settings.py
class DatabaseSettings:
    # 主业务数据库（高并发）
    MAIN_DB_POOL_SIZE = 20
    MAIN_DB_MAX_OVERFLOW = 40

    # 外部数据库（批量查询）
    EXTERNAL_DB_POOL_SIZE = 10
    EXTERNAL_DB_MAX_OVERFLOW = 20

    # 连接超时
    DB_POOL_TIMEOUT = 30
    DB_POOL_RECYCLE = 3600  # 1小时回收
```

## 📋 环境变量配置

### 开发环境 (.env.development)

```bash
# 主业务数据库（开发可用 SQLite）
DATABASE_URL=sqlite:///./data/main.db

# 外部数据仓库（开发建议用 PostgreSQL）
EXTERNAL_DB_URL=postgresql://postgres:password@localhost:5432/external_dev

# Redis
REDIS_URL=redis://localhost:6379/0
```

### 生产环境 (.env.production)

```bash
# 主业务数据库（生产必须用 PostgreSQL）
DATABASE_URL=postgresql://postgres:SecurePassword@db.example.com:5432/ipa_main

# 外部数据仓库（独立服务器）
EXTERNAL_DB_URL=postgresql://postgres:SecurePassword@db-external.example.com:5432/ipa_external

# Redis（哨兵模式）
REDIS_URL=redis://redis.example.com:6379/0
REDIS_SENTINEL_HOSTS=sentinel1:26379,sentinel2:26379,sentinel3:26379
```

## 🔒 安全建议

1. **数据库用户权限分离**

```sql
-- 创建只读用户（用于分析查询）
CREATE USER ipa_readonly WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE ipa_main TO ipa_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ipa_readonly;

-- 创建应用用户（正常读写）
CREATE USER ipa_app WITH PASSWORD 'app_password';
GRANT ALL PRIVILEGES ON DATABASE ipa_main TO ipa_app;

-- 创建爬虫用户（只能访问外部库）
CREATE USER ipa_crawler WITH PASSWORD 'crawler_password';
GRANT ALL PRIVILEGES ON DATABASE ipa_external TO ipa_crawler;
```

2. **数据库备份策略**

```bash
# 主业务数据库：每日全量备份
0 2 * * * pg_dump -U postgres ipa_main | gzip > /backup/main_$(date +\%Y\%m\%d).sql.gz

# 外部数据库：每周全量 + 每日增量
0 3 * * 0 pg_dump -U postgres ipa_external | gzip > /backup/external_full_$(date +\%Y\%m\%d).sql.gz
0 3 * * 1-6 pg_dump -U postgres --format=custom --file=/backup/external_inc_$(date +\%Y\%m\%d).dump ipa_external
```

## 📊 性能对比

| 指标 | SQLite | PostgreSQL | 提升 |
|------|--------|------------|------|
| 并发读取 | 无限制 | 无限制 | - |
| 并发写入 | ❌ 串行 | ✅ 并行 | **100倍+** |
| 连接数 | 单连接 | 100+ | - |
| 查询优化 | 简单 | 高级（CTE, 窗口函数） | **5-10倍** |
| 全文搜索 | 基础 | ✅ 强大（tsvector） | **10倍+** |
| 向量搜索 | ❌ 不支持 | ✅ pgvector | **∞** |
| JSON查询 | 基础 | ✅ JSONB索引 | **20倍+** |
| 网络访问 | ❌ | ✅ | - |
| 数据量级 | <10GB | >1TB | - |

## ✅ 验收标准

### 功能验收
- [ ] 所有模型使用统一的 Base
- [ ] 主业务数据库可连接并创建表
- [ ] 外部数据库独立运行
- [ ] 数据迁移完整无丢失
- [ ] API接口正常响应

### 性能验收
- [ ] 并发100用户无死锁
- [ ] 查询响应时间 < 100ms (P95)
- [ ] 写入吞吐量 > 1000 TPS

### 安全验收
- [ ] 敏感信息不在日志中
- [ ] 数据库密码使用环境变量
- [ ] 备份脚本可正常运行

## 🔄 回滚计划

如果迁移失败：

```bash
# 1. 恢复 .env 配置
DATABASE_URL=sqlite:///./data/archived_sessions.db

# 2. 从备份恢复 SQLite
cp ./data/archived_sessions.db.backup ./data/archived_sessions.db

# 3. 重启服务
systemctl restart ipa-backend
```

## 📞 技术支持

遇到问题查看：
- PostgreSQL 日志：`tail -f /var/log/postgresql/postgresql-14-main.log`
- 应用日志：`tail -f logs/backend.log`
- 连接池监控：访问 `/api/health/database`

## 📝 变更记录

| 日期 | 版本 | 变更内容 | 负责人 |
|------|------|----------|--------|
| 2026-02-17 | v1.0 | 初始方案 | AI Team |
| | | |

**审批人**：待定
**预计完成日期**：2026-02-24
