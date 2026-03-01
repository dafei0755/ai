# 外部数据系统快速启动指南

## 🚀 Phase 1-2已完成：基础架构+爬虫框架

### ✅ 已实施的核心组件

#### 1. 数据库模型 (PostgreSQL)
- **文件**: `intelligent_project_analyzer/models/external_projects.py`
- **表结构**:
  - `external_projects`: 项目主表（支持pgvector向量搜索）
  - `external_project_images`: 项目图片表
  - `sync_history`: 同步历史记录
  - `quality_issues`: 数据质量问题
- **功能**:
  - 向量嵌入支持（OpenAI Embeddings）
  - JSONB灵活元数据存储
  - 质量评分系统

#### 2. 统一爬虫框架
- **文件**: `intelligent_project_analyzer/crawlers/base_spider.py`
- **BaseSpider基类**:
  - Playwright浏览器管理
  - 请求重试+限速（防封禁）
  - Cookie持久化
  - User-Agent轮换
  - 统一数据结构（ProjectData）

#### 3. Archdaily爬虫
- **文件**: `intelligent_project_analyzer/crawlers/archdaily_spider.py`
- **功能**:
  - 8个功能分类爬取
  - 完整项目解析（title、description、images、architects等）
  - 自动翻页
  - URL去重

#### 4. 爬虫管理器
- **文件**: `intelligent_project_analyzer/crawlers/spider_manager.py`
- **SpiderManager功能**:
  - 爬虫注册与调度
  - 数据存储到数据库
  - 同步历史记录
  - 质量评分计算（0-1分数）
  - 统计查询（数据源统计、同步历史）

#### 5. Celery异步任务
- **文件**: `intelligent_project_analyzer/tasks/external_data_tasks.py`
- **任务**:
  - `sync_external_source`: 数据源同步任务
  - `generate_embeddings_task`: 向量嵌入生成
  - `quality_check_task`: 质量检查
- **定时任务**:
  - 每天凌晨2点增量同步
  - 每周日全量同步

#### 6. API路由（已增强）
- **文件**: `intelligent_project_analyzer/api/external_data_routes.py`
- **端点**:
  - `GET /api/external/sync-history` - 同步历史（✅ 已连接数据库）
  - `GET /api/external/source-stats` - 数据源统计（✅ 已连接数据库）
  - `GET /api/external/quality-issues` - 质量问题
  - `POST /api/external/trigger-sync` - 触发同步（✅ 支持Celery）
  - `GET /api/external/project/{id}` - 项目详情

---

## 📋 环境配置

### 1. 安装依赖

```bash
# 核心依赖
pip install sqlalchemy psycopg2-binary pgvector
pip install playwright
pip install celery redis
pip install openai

# Playwright浏览器
playwright install chromium
```

### 2. PostgreSQL配置

```bash
# 安装PostgreSQL + pgvector扩展
# Windows: https://www.postgresql.org/download/windows/

# 连接到PostgreSQL
psql -U postgres

# 创建数据库
CREATE DATABASE external_projects;

# 启用pgvector扩展
\c external_projects
CREATE EXTENSION vector;
```

### 3. 环境变量（.env文件）

```bash
# 数据库连接
EXTERNAL_DB_URL=postgresql://postgres:password@localhost:5432/external_projects

# Redis（Celery）
REDIS_URL=redis://localhost:6379/0

# OpenAI API（向量嵌入）
OPENAI_API_KEY=sk-your-api-key
```

### 4. 初始化数据库

```python
# Python脚本
from intelligent_project_analyzer.models.external_projects import get_external_db

db = get_external_db()
db.create_tables()  # 创建所有表和索引
```

---

## 🎯 使用示例

### 示例1: 手动同步Archdaily

```python
from intelligent_project_analyzer.crawlers import get_spider_manager

# 获取管理器
manager = get_spider_manager()

# 同步单个分类
manager.sync_source(
    source="archdaily",
    category="居住建筑",
    max_pages=5,
    mode='incremental'
)

# 同步所有分类
manager.sync_source(
    source="archdaily",
    max_pages=20,
    mode='full'
)
```

### 示例2: 使用Celery异步任务

```bash
# 启动Celery Worker
celery -A intelligent_project_analyzer.tasks.external_data_tasks worker --loglevel=info

# 启动Celery Beat（定时任务）
celery -A intelligent_project_analyzer.tasks.external_data_tasks beat --loglevel=info

# 手动触发任务
python
>>> from intelligent_project_analyzer.tasks.external_data_tasks import sync_external_source
>>> task = sync_external_source.delay('archdaily', mode='incremental')
>>> print(task.id)
```

### 示例3: 查询数据

```python
from intelligent_project_analyzer.models.external_projects import get_external_db, ExternalProject

db = get_external_db()

with db.get_session() as session:
    # 查询所有Archdaily项目
    projects = session.query(ExternalProject).filter(
        ExternalProject.source == 'archdaily'
    ).limit(10).all()

    for p in projects:
        print(f"{p.title} - {p.year} - {p.quality_score}")
```

### 示例4: 向量搜索（需要pgvector）

```python
from openai import OpenAI
client = OpenAI()

# 生成查询向量
query = "现代主义住宅设计"
response = client.embeddings.create(
    model="text-embedding-3-small",
    input=query
)
query_vector = response.data[0].embedding

# 向量搜索（最相似的10个项目）
with db.get_session() as session:
    from sqlalchemy import text

    results = session.execute(text("""
        SELECT id, title, description,
               1 - (description_vector <=> :query_vector) AS similarity
        FROM external_projects
        WHERE description_vector IS NOT NULL
        ORDER BY description_vector <=> :query_vector
        LIMIT 10
    """), {"query_vector": str(query_vector)}).fetchall()

    for r in results:
        print(f"{r.title} - 相似度: {r.similarity:.2f}")
```

---

## 🔧 前端集成

### 监控页面已创建
- **路径**: `/admin/external-data`
- **文件**: `frontend-nextjs/app/admin/external-data/page.tsx`
- **功能**:
  - 数据源统计卡片
  - 同步历史表格（✅ 已连接后端API）
  - 质量问题表格
  - 手动触发同步（✅ 支持Celery）

### API调用示例

```typescript
// 获取同步历史
const response = await fetch('/api/external/sync-history?limit=10');
const data = await response.json();
console.log(data.history);

// 触发同步
await fetch('/api/external/trigger-sync', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    source: 'archdaily',
    category: '居住建筑',
    mode: 'incremental'
  })
});
```

---

## 📊 系统监控

### Celery Flower（任务监控）

```bash
# 安装Flower
pip install flower

# 启动Web监控界面
celery -A intelligent_project_analyzer.tasks.external_data_tasks flower

# 访问 http://localhost:5555
```

### 数据库监控

```sql
-- 查看数据源统计
SELECT source, COUNT(*) as total, AVG(quality_score) as avg_quality
FROM external_projects
GROUP BY source;

-- 查看同步历史
SELECT * FROM sync_history
ORDER BY started_at DESC
LIMIT 10;

-- 查看质量问题
SELECT issue_type, severity, COUNT(*) as count
FROM quality_issues
WHERE resolved_at IS NULL
GROUP BY issue_type, severity;
```

---

## 🚧 下一步实施（Phase 3-7）

### Phase 3: 数据处理（2周）
- [ ] 数据标准化Pipeline
- [ ] 批量向量化（OpenAI Embeddings）
- [ ] 自动标注系统（GPT-4分析）

### Phase 4: 索引层（1周）
- [ ] Qdrant向量数据库部署
- [ ] Elasticsearch全文索引
- [ ] PostgreSQL FTS配置

### Phase 5: 应用层API（3周）
- [ ] 语义搜索API（基于向量）
- [ ] 推荐引擎（协同过滤+内容推荐）
- [ ] RAG上下文提供器（LangGraph集成）
- [ ] 趋势分析API（时间序列）

### Phase 6: 调度与运维（1周）
- [ ] Celery Beat定时任务完善
- [ ] Prometheus + Grafana监控
- [ ] 日志聚合（ELK Stack）
- [ ] 备份恢复策略

### Phase 7: 前端集成（2周）
- [ ] 案例浏览器页面
- [ ] 推荐卡片组件
- [ ] 趋势分析仪表板
- [ ] 概念图参考库

---

## 📚 相关文档

- [大规模架构设计](./LARGE_SCALE_EXTERNAL_DATA_ARCHITECTURE.md) - 完整系统架构
- [数据存储指南](./EXTERNAL_DATA_STORAGE_GUIDE.md) - 数据结构说明
- [监控面板指南](./EXTERNAL_DATA_MONITORING_GUIDE.md) - 前端使用说明

---

## ⚠️ 注意事项

1. **限速**: Archdaily爬取建议设置`request_delay=2.0`（每个请求间隔2秒）
2. **Cookie**: 首次运行会保存Cookie到`data/cookies/`目录
3. **数据库**: PostgreSQL需要安装pgvector扩展才能使用向量搜索
4. **Celery**: 建议使用Redis作为Broker和Backend
5. **OpenAI**: 向量嵌入需要消耗API配额（text-embedding-3-small: $0.02/1M tokens）

---

## 🎉 快速启动命令

```bash
# 1. 初始化数据库
python -c "from intelligent_project_analyzer.models.external_projects import get_external_db; get_external_db().create_tables()"

# 2. 启动后端API
uvicorn intelligent_project_analyzer.api.server:app --reload

# 3. 启动Celery Worker（新终端）
celery -A intelligent_project_analyzer.tasks.external_data_tasks worker --loglevel=info

# 4. 启动前端（新终端）
cd frontend-nextjs
npm run dev

# 5. 访问监控页面
# http://localhost:3000/admin/external-data
```

---

**系统状态**: Phase 1-2 ✅ 已完成
**预计总耗时**: 13周（Phase 1-7全部完成）
**当前进度**: 4周/13周（30.77%）
