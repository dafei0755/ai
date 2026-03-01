# External Architecture Data System

外部建筑数据采集系统 - 独立爬虫子包

## 📦 系统概述

这是一个模块化、可扩展的建筑项目数据采集系统，支持从多个建筑网站爬取高质量数据。

### 核心特性

- 🕷️ **多数据源支持**：Archdaily, Gooood, Dezeen等
- 🔄 **异步任务**：基于Celery的分布式爬取
- 💾 **向量存储**：PostgreSQL + pgvector支持语义搜索
- 📊 **质量评分**：自动评估数据完整性
- 🔌 **RESTful API**：标准化数据访问接口
- 🧪 **独立测试**：完整的测试覆盖

## 🏗️ 架构设计

```
external_data_system/
├── spiders/              # 爬虫实现
│   ├── base_spider.py    # 抽象基类
│   ├── archdaily_spider.py
│   ├── gooood_spider.py
│   └── spider_manager.py  # 爬虫编排器
├── models/               # 数据模型
│   ├── external_projects.py  # SQLAlchemy模型
│   └── schemas.py        # Pydantic schemas
├── tasks/                # Celery任务
│   ├── sync_tasks.py     # 同步任务
│   └── processing_tasks.py  # 数据处理任务
├── api/                  # FastAPI路由
│   └── routes.py
├── utils/                # 工具函数
│   ├── rate_limiter.py
│   └── proxy_manager.py
└── tests/                # 单元测试
```

## 🚀 快速开始

### 1. 数据库初始化

```bash
python scripts/init_external_database.py
```

### 2. 启动爬虫

```python
from intelligent_project_analyzer.external_data_system import get_spider_manager

manager = get_spider_manager()
manager.sync_source("archdaily", category="residential", max_pages=5)
```

### 3. API访问

```bash
# 查询同步历史
curl http://localhost:8000/api/external/sync-history?limit=10

# 触发同步任务
curl -X POST http://localhost:8000/api/external/trigger-sync \
  -H "Content-Type: application/json" \
  -d '{"source": "archdaily", "mode": "incremental"}'
```

## 🔧 配置说明

### 环境变量

```bash
# PostgreSQL数据库（必需）
EXTERNAL_DB_URL=postgresql://user:pass@localhost/external_db

# Redis（Celery broker，可选）
REDIS_URL=redis://localhost:6379/0

# OpenAI API（向量生成，可选）
OPENAI_API_KEY=sk-...
```

### Spider配置

每个Spider可以自定义以下参数：

```python
spider = ArchdailySpider(
    max_retries=3,          # 最大重试次数
    request_delay=2.0,      # 请求间隔（秒）
    timeout=30000,          # 超时时间（毫秒）
    headless=True,          # 无头模式
    proxy=None              # 代理配置
)
```

## 📊 数据质量评分

系统自动对每个项目进行质量评分（0-1分）：

| 维度 | 权重 | 满分标准 |
|------|------|----------|
| 描述长度 | 30% | ≥1000字符 |
| 图片数量 | 20% | ≥10张 |
| 元数据完整度 | 30% | 5个必填字段 |
| 标签数量 | 20% | ≥10个标签 |

**质量分级**：
- 🥇 优秀（0.8-1.0）：完整详实，可直接使用
- 🥈 良好（0.6-0.8）：较完整，少量缺失
- 🥉 一般（0.4-0.6）：基本完整，需补充
- ❌ 不合格（<0.4）：数据严重缺失

## 🧪 测试

```bash
# 运行所有测试
python scripts/test_external_data_system.py

# 测试单个爬虫
pytest external_data_system/tests/test_spiders.py -k archdaily

# 测试数据库连接
pytest external_data_system/tests/test_models.py
```

## 🔌 集成主项目

### 导入Spider

```python
from intelligent_project_analyzer.external_data_system import (
    get_spider_manager,
    ExternalProject,
    get_external_db,
)

# 获取爬虫管理器
manager = get_spider_manager()

# 查询数据库
db = get_external_db()
with db.session() as session:
    projects = session.query(ExternalProject).limit(10).all()
```

### 注册API路由

```python
from intelligent_project_analyzer.external_data_system import external_data_router

app.include_router(external_data_router, prefix="/api/external", tags=["external-data"])
```

## 📈 性能优化

### 并发爬取

Celery支持分布式爬取：

```python
# 同时爬取多个分类
from external_data_system.tasks import sync_external_source

tasks = [
    sync_external_source.delay("archdaily", category="residential"),
    sync_external_source.delay("archdaily", category="cultural"),
    sync_external_source.delay("gooood", category="commercial"),
]
```

### 增量更新

系统自动判断增量/全量模式：

- **增量模式**：只爬取新发布的项目（每日2AM）
- **全量模式**：重新爬取所有项目（每周日3AM）

## 🛡️ 反爬虫策略

系统内置多种反反爬虫措施：

1. **User-Agent轮换**：3个真实浏览器UA
2. **Cookie持久化**：自动保存登录状态
3. **请求延迟**：可配置请求间隔（默认2秒）
4. **代理支持**：可配置HTTP/SOCKS5代理
5. **Playwright渲染**：支持JavaScript动态内容

## 📝 添加新数据源

### Step 1: 创建Spider类

```python
# spiders/new_site_spider.py
from .base_spider import BaseSpider, ProjectData

class NewSiteSpider(BaseSpider):
    def get_name(self) -> str:
        return "newsite"

    async def parse_project_page(self, url: str) -> Optional[ProjectData]:
        page = await self.fetch_with_retry(url)
        # 解析逻辑
        return ProjectData(...)

    async def crawl_category(self, category: str, max_pages: int) -> List[str]:
        # 分类爬取逻辑
        return urls
```

### Step 2: 注册到Manager

```python
# spiders/__init__.py
from .new_site_spider import NewSiteSpider

def get_spider_manager():
    manager = SpiderManager()
    manager.register_spider(NewSiteSpider())
    return manager
```

### Step 3: 测试

```bash
python scripts/test_external_data_system.py
```

## 🚨 常见问题

### Q: 爬虫被封禁怎么办？

A: 检查以下设置：
1. 增加 `request_delay` 到 5-10秒
2. 启用代理池
3. 检查Cookie是否失效

### Q: 向量生成失败？

A: 确保配置了 `OPENAI_API_KEY`，或使用本地模型：

```python
# tasks/processing_tasks.py
# 改用本地Sentence-Transformers
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
```

### Q: Celery任务不执行？

A: 确保Redis已启动，并检查Celery worker状态：

```bash
celery -A intelligent_project_analyzer.tasks.external_data_tasks worker --loglevel=info
```

## 📚 相关文档

- [EXTERNAL_DATA_QUICKSTART.md](../../EXTERNAL_DATA_QUICKSTART.md) - 快速入门指南
- [LARGE_SCALE_EXTERNAL_DATA_ARCHITECTURE.md](../../LARGE_SCALE_EXTERNAL_DATA_ARCHITECTURE.md) - 完整架构设计
- [EXTERNAL_DATA_MONITORING_GUIDE.md](../../EXTERNAL_DATA_MONITORING_GUIDE.md) - 监控面板使用

## 🤝 贡献指南

欢迎提交新的数据源爬虫！请遵循以下规范：

1. 继承 `BaseSpider` 抽象类
2. 实现 `parse_project_page()` 和 `crawl_category()` 方法
3. 添加单元测试
4. 更新文档

## 📄 License

MIT License - 仅供学习研究使用，请遵守目标网站的robots.txt协议。
