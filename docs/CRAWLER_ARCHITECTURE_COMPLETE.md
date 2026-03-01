# 🕷️ 外部项目爬虫系统 - 完整架构文档

> **版本**: v2.1
> **更新时间**: 2026-02-26
> **状态**: ✅ 生产就绪

---

## 📋 目录

1. [系统概览](#系统概览)
2. [数据源配置](#数据源配置)
3. [爬取机制](#爬取机制)
4. [调度策略](#调度策略)
5. [翻译处理](#翻译处理)
6. [存储架构](#存储架构)
7. [并行方案](#并行方案)
8. [监控运维](#监控运维)
9. [使用指南](#使用指南)
10. [查看爬取成果](#查看爬取成果)

---

## 🎯 系统概览

### 架构全景

```
┌─────────────────────────────────────────────────────────────────┐
│                     外部项目爬虫系统 v2.0                          │
└─────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌─────────┐  ┌─────────┐  ┌─────────┐
              │Archdaily│  │ Gooood  │  │ Dezeen  │
              │（英文）  │  │（中文）  │  │（英文）  │
              └─────────┘  └─────────┘  └─────────┘
                    │            │            │
                    └────────────┼────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │   索引发现（Index）       │
                    │  - 列表页爬取             │
                    │  - URL去重               │
                    │  - 分类标记               │
                    └─────────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   详情爬取（Detail）      │
                    │  - 内容提取               │
                    │  - 图片下载               │
                    │  - 质量评分               │
                    └─────────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
          ┌──────────────┐ ┌──────────┐ ┌──────────┐
          │英文项目翻译   │ │中文项目   │ │图片存储   │
          │Deepseek API  │ │直接入库   │ │MinIO/S3  │
          └──────────────┘ └──────────┘ └──────────┘
                    │            │            │
                    └────────────┼────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │   PostgreSQL数据库        │
                    │  - 双语存储               │
                    │  - 向量索引               │
                    │  - 质量元数据             │
                    └─────────────────────────┘
```

### 核心组件

| 组件 | 文件路径 | 功能 |
|------|---------|------|
| **Spider（爬虫）** | `spiders/{source}_spider.py` | 网站内容提取 |
| **IndexManager（索引）** | `project_index.py` | URL管理和去重 |
| **Translator（翻译）** | `translation/translator.py` | 英文→中文翻译 |
| **Database（数据库）** | `models/external_projects.py` | 数据持久化 |
| **Scheduler（调度）** | `celery_app.py` | 定时任务配置 |
| **RateLimiter（限流）** | `utils/rate_limiter.py` | 访问频率控制 |

---

## 📊 数据源配置

### 1. Archdaily（建筑日报）

**网站**: https://www.archdaily.com
**语言**: 英文
**更新频率**: 每日 8-15 篇
**内容质量**: ⭐⭐⭐⭐⭐（国际一流）

**爬取范围**:
- 建筑分类：住宅、商业、文化、公共建筑
- 项目年份：2015-2026
- 预计总量：8万+ 项目

**爬虫配置**:
```python
# spiders/archdaily_spider.py
class ArchdailySpider(BaseSpider):
    base_url = "https://www.archdaily.com"
    rate_limit = 1.5  # 每1.5秒一次请求
    timeout = 30

    # 分类映射
    categories = {
        "houses": "住宅",
        "apartments": "公寓",
        "offices": "办公",
        "cultural": "文化",
        # ... 20+ 分类
    }
```

**爬取策略**:
- **首次爬取**: 从2015年开始，每天爬50页（约500项目/天）
- **增量更新**: 每周一凌晨爬取最新7天内容
- **并行配置**: 单线程（避免封IP）

---

### 2. Gooood（谷德设计网）

**网站**: https://www.gooood.cn
**语言**: 中文
**更新频率**: 每日 5-10 篇
**内容质量**: ⭐⭐⭐⭐（国内优质）

**爬取范围**:
- 建筑分类：住宅、商业、景观、室内
- 项目年份：2010-2026
- 预计总量：3万+ 项目

**爬虫配置**:
```python
# spiders/gooood_spider.py
class GoooodSpider(BaseSpider):
    base_url = "https://www.gooood.cn"
    rate_limit = 2.0  # 每2秒一次请求
    use_playwright = True  # 需要JavaScript渲染

    # 中文项目无需翻译
    needs_translation = False
```

**爬取策略**:
- **首次爬取**: 从2010年开始，每天爬100项目
- **增量更新**: 每周二凌晨爬取最新7天内容
- **并行配置**: 单线程（网站较慢）

---

### 3. Dezeen（设计月刊）

**网站**: https://www.dezeen.com
**语言**: 英文
**更新频率**: 每日 10-20 篇
**内容质量**: ⭐⭐⭐⭐⭐（设计媒体权威）

**爬取范围**:
- 建筑分类：建筑、室内、设计、技术
- 项目年份：2015-2026
- 预计总量：5万+ 项目

**爬虫配置**:
```python
# spiders/dezeen_spider.py
class DezeenSpider(BaseSpider):
    base_url = "https://www.dezeen.com"
    rate_limit = 1.0  # 每1秒一次请求
    timeout = 30

    # 当前状态
    index_projects = 46  # 已索引
    crawled_projects = 1  # 已爬取
    quality_score = 0.81  # 质量评分
```

**爬取策略**:
- **首次爬取**: 从索引列表爬取（46个URL已发现）
- **增量更新**: 每周三凌晨爬取最新7天内容
- **并行配置**: 单线程

---

## 🔄 爬取机制

### 两阶段爬取

#### 阶段1：索引发现（Index Discovery）

**目标**: 发现所有项目URL，建立索引库

```python
# 1. 爬取列表页
for page in range(1, max_pages):
    projects = spider.fetch_list_page(page)

    # 2. 提取URL并保存到索引
    for project in projects:
        index_manager.add_project(
            source="archdaily",
            url=project.url,
            title=project.title,
            category=project.category
        )

# 3. 索引统计
stats = index_manager.get_statistics()
# {
#   "total": 50000,
#   "crawled": 0,
#   "uncrawled": 50000,
#   "by_source": {...}
# }
```

**输出**: `data/project_index.db`（SQLite索引库）

**优势**:
- ✅ URL去重（避免重复爬取）
- ✅ 断点续传（爬取失败可恢复）
- ✅ 优先级排序（按发布时间）
- ✅ 统计分析（爬取进度监控）

---

#### 阶段2：详情爬取（Detail Crawling）

**目标**: 爬取项目完整信息并保存到数据库

```python
# 1. 从索引获取待爬取项目
uncrawled = index_manager.get_uncrawled_projects(
    source="archdaily",
    limit=100
)

# 2. 逐个爬取详情
for project_idx in uncrawled:
    # 2.1 爬取项目页面
    project_data = spider.parse_project_page(project_idx.url)

    # 2.2 英文项目自动翻译
    if project_data.language == "en" and auto_translate:
        translation = translator.translate_project(project_data)
        project_data.title_zh = translation['title_zh']
        project_data.description_zh = translation['description_zh']

    # 2.3 保存到数据库
    db_project = ExternalProject(
        source=project_data.source,
        url=project_data.url,
        title=project_data.title,
        title_en=project_data.title,
        title_zh=project_data.title_zh,
        description_en=project_data.description,
        description_zh=project_data.description_zh,
        translation_engine='deepseek',
        translation_quality=translation['quality'],
        # ... 其他字段
    )
    db.save(db_project)

    # 2.4 标记为已爬取
    index_manager.mark_as_crawled(project_idx.url, success=True)
```

**输出**: PostgreSQL数据库（双语存储）

---

### 质量控制

#### 内容质量评分（0-1分）

```python
def calculate_quality_score(project: ProjectData) -> float:
    score = 0.0
    factors = {}

    # 1. 描述长度（30%）
    desc_len = len(project.description)
    if desc_len > 2000:
        score += 0.3
    elif desc_len > 1000:
        score += 0.2
    else:
        score += 0.1
    factors['description_length'] = desc_len

    # 2. 图片数量（25%）
    img_count = len(project.images)
    if img_count >= 10:
        score += 0.25
    elif img_count >= 5:
        score += 0.15
    else:
        score += 0.05
    factors['image_count'] = img_count

    # 3. 元数据完整性（25%）
    meta_score = 0
    if project.architects: meta_score += 0.08
    if project.location: meta_score += 0.08
    if project.year: meta_score += 0.05
    if project.area_sqm: meta_score += 0.04
    score += meta_score
    factors['metadata_completeness'] = meta_score / 0.25

    # 4. 结构化标签（20%）
    if len(project.tags) >= 10: score += 0.2
    elif len(project.tags) >= 5: score += 0.1
    factors['tags_count'] = len(project.tags)

    return score, factors
```

**质量分级**:
- 🌟 优秀（0.8-1.0）：完整项目，适合展示
- 🌟 良好（0.6-0.8）：内容充实，可以入库
- 🌟 一般（0.4-0.6）：基本可用，需人工审核
- 🌟 较差（<0.4）：内容不足，建议丢弃

---

## ⏰ 调度策略

### Celery Beat定时任务

**配置文件**: `intelligent_project_analyzer/external_data_system/celery_app.py`

```python
app.conf.beat_schedule = {
    # ========== 增量更新（生产环境） ==========

    # 1. Archdaily增量（每周一凌晨2点）
    'weekly-sync-archdaily': {
        'task': 'sync_archdaily_incremental',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),
        'kwargs': {
            'days': 7,  # 爬取最近7天
            'max_projects': 200,
            'auto_translate': True,
            'translation_engine': 'deepseek'
        }
    },

    # 2. Gooood增量（每周二凌晨2点）
    'weekly-sync-gooood': {
        'task': 'sync_gooood_incremental',
        'schedule': crontab(hour=2, minute=0, day_of_week=2),
        'kwargs': {
            'days': 7,
            'max_projects': 100,
            'auto_translate': False  # 中文项目无需翻译
        }
    },

    # 3. Dezeen增量（每周三凌晨2点）
    'weekly-sync-dezeen': {
        'task': 'sync_dezeen_incremental',
        'schedule': crontab(hour=2, minute=0, day_of_week=3),
        'kwargs': {
            'days': 7,
            'max_projects': 150,
            'auto_translate': True,
            'translation_engine': 'deepseek'
        }
    },

    # ========== 数据处理任务 ==========

    # 4. 向量嵌入生成（每天凌晨3点）
    'daily-batch-embeddings': {
        'task': 'batch_generate_embeddings_task',
        'schedule': crontab(hour=3, minute=0),
        'kwargs': {
            'batch_size': 100,
            'only_missing': True  # 只处理未生成向量的项目
        }
    },

    # 5. 质量复查（每天凌晨4点）
    'daily-quality-check': {
        'task': 'batch_quality_check_task',
        'schedule': crontab(hour=4, minute=0),
        'kwargs': {
            'batch_size': 200,
            'recalculate_all': False
        }
    },

    # ========== 数据库维护 ==========

    # 6. 清理历史记录（每周日凌晨5点）
    'weekly-database-cleanup': {
        'task': 'cleanup_old_sync_history',
        'schedule': crontab(hour=5, minute=0, day_of_week=0),
        'kwargs': {
            'days': 90  # 清理90天前的同步历史
        }
    }
}
```

### 更新频率建议

| 网站 | 日更新量 | 周更新量 | 建议频率 | 原因 |
|------|---------|---------|---------|------|
| Archdaily | 10-15篇 | 70-100篇 | 每周一次 | 内容稳定，更新规律 |
| Gooood | 5-10篇 | 35-70篇 | 每周一次 | 更新较少，无需高频 |
| Dezeen | 15-20篇 | 105-140篇 | 每周一次 | 内容丰富，但质量需筛选 |

**总计**: 每周约 **210-310** 个新项目

---

## 🌐 翻译处理

### 翻译策略

**触发条件**:
- ✅ 网站语言为英文（Archdaily、Dezeen）
- ✅ `--auto-translate` 参数开启
- ❌ 网站语言为中文（Gooood）→ 跳过翻译

### Deepseek API配置

**引擎**: Deepseek Chat (deepseek-chat)
**成本**: ¥0.004/篇，¥4-6/千篇
**速度**: 10-15秒/篇
**质量**: 0.6-0.85 平均分

```python
# 翻译器配置
translator = ProjectTranslator(
    engine='deepseek',
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url='https://api.deepseek.com',
    temperature=0.3,  # 低温度保证翻译稳定
    max_tokens=8000  # 支持长文本（~3000字描述）
)
```

### 专业术语处理

**术语词典**（50+专业术语）:

```python
TERMINOLOGY = {
    # 结构类
    'facade': '立面',
    'cantilever': '悬臂',
    'atrium': '中庭',
    'courtyard': '庭院',

    # 材料类
    'concrete': '混凝土',
    'timber': '木材',
    'steel': '钢材',

    # 风格类
    'minimalist': '极简主义',
    'brutalist': '粗野主义',
    'contemporary': '当代',

    # 功能类
    'residential': '住宅',
    'commercial': '商业',
    'cultural': '文化',
    'mixed-use': '混合用途'
}
```

### 翻译规则

1. **人名保留英文**: "Sou Fujimoto" → "Sou Fujimoto"（不翻译）
2. **事务所保留**: "Foster + Partners" → "Foster + Partners"
3. **地名使用官方**: "Abu Dhabi" → "阿布扎比"
4. **专业术语标注**: "Facade" → "立面（Facade）"首次出现时
5. **段落结构保持**: 用 `\n\n` 分隔段落
6. **数字单位保留**: "77 homes", "1,536 m²" 不翻译

### 质量评分（0-1分）

```python
def evaluate_translation_quality(original, translation) -> float:
    score = 0.0

    # 1. 长度比例（30%）- 中文字符数约为英文的30-60%
    ratio = len(translation['description_zh']) / len(original.description)
    if 0.3 <= ratio <= 0.8:
        score += 0.30
    elif 0.2 <= ratio < 0.3:
        score += 0.20

    # 2. 人名保留（25%）- 建筑师名字应保留
    preserved_names = 0
    for architect in original.architects:
        if architect in translation['description_zh']:
            preserved_names += 1
    score += 0.25 * (preserved_names / max(len(original.architects), 1))

    # 3. 术语正确性（25%）- 检查关键术语翻译
    term_score = check_terminology_accuracy(translation['description_zh'])
    score += 0.25 * term_score

    # 4. 内容完整性（20%）- 段落数匹配
    orig_paras = original.description.count('\n\n') + 1
    trans_paras = translation['description_zh'].count('\n\n') + 1
    completeness = min(trans_paras / orig_paras, 1.0)
    score += 0.20 * completeness

    return score
```

**质量分级**:
- 🌟 优秀（≥0.8）：自动通过
- 🌟 良好（0.7-0.8）：自动通过
- ⚠️ 待审核（0.6-0.7）：标记 `is_human_reviewed=False`
- ❌ 不合格（<0.6）：重新翻译或人工处理

### 翻译成本预估

| 场景 | 项目数 | 单篇成本 | 总成本 | 时间 |
|-----|--------|---------|--------|------|
| 单篇测试 | 1 | ¥0.004 | ¥0.004 | 10秒 |
| 每周增量 | 200 | ¥0.004 | ¥0.8 | 30分钟 |
| 首次爬取 | 50,000 | ¥0.004 | ¥200 | 140小时 |

**月度成本**: ¥3.2（每周200篇 × 4周）

---

## 💾 存储架构

### 数据库设计

**主表**: `external_projects`（项目主表）

```sql
CREATE TABLE external_projects (
    -- 主键
    id BIGSERIAL PRIMARY KEY,

    -- 数据源标识
    source VARCHAR(50) NOT NULL,           -- 'archdaily', 'gooood', 'dezeen'
    source_id VARCHAR(200) NOT NULL,       -- 网站内部ID
    url TEXT NOT NULL UNIQUE,              -- 项目URL

    -- 基本信息（双语存储）
    title TEXT NOT NULL,                   -- 标题（向后兼容）
    title_en TEXT,                         -- 英文标题
    title_zh TEXT,                         -- 中文标题

    description TEXT,                      -- 描述（向后兼容）
    description_en TEXT,                   -- 英文描述
    description_zh TEXT,                   -- 中文描述
    description_vector vector(1536),       -- OpenAI Embeddings向量

    -- 翻译元数据
    translation_engine VARCHAR(50),        -- 'deepseek', 'gpt4', 'claude', 'human'
    translation_quality FLOAT,             -- 翻译质量评分 0-1
    translated_at TIMESTAMP,               -- 翻译时间
    is_human_reviewed BOOLEAN DEFAULT FALSE, -- 人工审核标志

    -- 元数据（JSON格式）
    architects JSONB,                      -- [{"name": "xxx", "firm": "xxx"}]
    location JSONB,                        -- {"country": "xxx", "city": "xxx"}
    area_sqm FLOAT,                        -- 面积（平方米）
    year INTEGER,                          -- 年份
    cost JSONB,                            -- {"currency": "USD", "amount": 1000000}

    -- 分类与标签
    primary_category VARCHAR(100),         -- 主分类
    sub_categories JSON,                   -- 子分类数组
    tags JSON,                             -- 标签数组

    -- 社交数据
    views INTEGER DEFAULT 0,               -- 浏览量
    likes INTEGER DEFAULT 0,               -- 点赞数
    shares INTEGER DEFAULT 0,              -- 分享数

    -- 质量评分
    quality_score FLOAT,                   -- 内容质量评分 0-1
    quality_factors JSONB,                 -- 质量因子详情

    -- 时间戳
    publish_date TIMESTAMP,                -- 发布时间
    crawled_at TIMESTAMP DEFAULT NOW(),    -- 爬取时间
    updated_at TIMESTAMP DEFAULT NOW(),    -- 更新时间

    -- 索引
    CONSTRAINT uq_source_id UNIQUE(source, source_id)
);

-- 索引优化
CREATE INDEX idx_source_publish_date ON external_projects(source, publish_date);
CREATE INDEX idx_quality_score_desc ON external_projects(quality_score DESC);
CREATE INDEX idx_is_crawled ON external_projects(source, crawled_at);
CREATE INDEX idx_translation_quality ON external_projects(translation_quality) WHERE translation_quality IS NOT NULL;

-- 向量索引（需要pgvector扩展）
CREATE INDEX ON external_projects USING ivfflat (description_vector vector_cosine_ops);
```

**关联表**: `external_project_images`（图片表）

```sql
CREATE TABLE external_project_images (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES external_projects(id) ON DELETE CASCADE,

    url TEXT NOT NULL,                     -- 图片URL
    caption TEXT,                          -- 图片说明
    width INTEGER,                         -- 宽度
    height INTEGER,                        -- 高度
    file_size INTEGER,                     -- 文件大小（字节）
    storage_path TEXT,                     -- MinIO/S3存储路径
    order_index INTEGER DEFAULT 0,         -- 显示顺序
    is_cover BOOLEAN DEFAULT FALSE,        -- 是否为封面图

    -- 索引
    CREATE INDEX idx_project_id ON external_project_images(project_id),
    CREATE INDEX idx_is_cover ON external_project_images(is_cover)
);
```

### 数据示例

```json
{
  "id": 12345,
  "source": "archdaily",
  "url": "https://www.archdaily.com/...",

  "title_en": "Sou Fujimoto unveils first residential project in UAE",
  "title_zh": "Sou Fujimoto 公布其在阿联酋的首个住宅项目",

  "description_en": "Japanese architect Sou Fujimoto has revealed...",
  "description_zh": "日本建筑师 Sou Fujimoto 公布了他位于阿联酋的首个住宅项目...",

  "translation_engine": "deepseek",
  "translation_quality": 0.81,
  "translated_at": "2026-02-17T21:12:08",

  "architects": ["Sou Fujimoto"],
  "location": {
    "country": "United Arab Emirates",
    "city": "Abu Dhabi",
    "district": "Saadiyat Island"
  },
  "area_sqm": 15000,
  "year": 2026,

  "primary_category": "residential",
  "tags": ["luxury", "high-rise", "waterfront", "minimalist"],

  "quality_score": 0.85,
  "quality_factors": {
    "description_length": 3764,
    "image_count": 14,
    "metadata_completeness": 0.9,
    "tags_count": 20
  },

  "publish_date": "2026-02-10T00:00:00",
  "crawled_at": "2026-02-17T21:11:54"
}
```

---

## ⚡ 并行方案

### 问题：能否多网站并行？

**回答：可以！** 有三种方案：

### 方案1：Celery多Worker并行（推荐）

**原理**: 启动多个Celery Worker进程，每个处理不同网站

```bash
# 启动3个Worker，每个绑定不同队列
celery -A intelligent_project_analyzer.external_data_system.celery_app worker \
    --queue=archdaily --concurrency=1 --hostname=archdaily@%h

celery -A intelligent_project_analyzer.external_data_system.celery_app worker \
    --queue=gooood --concurrency=1 --hostname=gooood@%h

celery -A intelligent_project_analyzer.external_data_system.celery_app worker \
    --queue=dezeen --concurrency=1 --hostname=dezeen@%h
```

**配置修改**:

```python
# celery_app.py
app.conf.beat_schedule = {
    # 同时调度（并行开始）
    'parallel-sync-archdaily': {
        'task': 'sync_archdaily_incremental',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),
        'options': {'queue': 'archdaily'}  # 指定队列
    },

    'parallel-sync-gooood': {
        'task': 'sync_gooood_incremental',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),  # 同时间！
        'options': {'queue': 'gooood'}
    },

    'parallel-sync-dezeen': {
        'task': 'sync_dezeen_incremental',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),  # 同时间！
        'options': {'queue': 'dezeen'}
    }
}
```

**优势**:
- ✅ 真正并行（3个网站同时爬）
- ✅ 资源隔离（每个Worker独立内存）
- ✅ 错误隔离（一个挂了不影响其他）
- ✅ 易于监控（Flower监控面板）

**时间节省**:
- 串行：90分钟（30分钟/网站 × 3）
- 并行：30分钟（最慢的那个）
- **节省60分钟**

---

### 方案2：ThreadPoolExecutor并发（简单）

**原理**: 在单个进程内用多线程并发爬取

```python
# scripts/crawl_parallel.py
from concurrent.futures import ThreadPoolExecutor, as_completed

def crawl_source(source: str, **kwargs):
    """爬取单个数据源"""
    crawler = IndexBasedCrawler(
        auto_translate=kwargs.get('auto_translate', True),
        translation_engine=kwargs.get('translation_engine', 'deepseek')
    )

    return crawler.crawl_from_index(
        source=source,
        limit=kwargs.get('limit')
    )

def crawl_all_parallel():
    """并行爬取所有数据源"""
    sources = [
        {'source': 'archdaily', 'limit': 100, 'auto_translate': True},
        {'source': 'gooood', 'limit': 50, 'auto_translate': False},
        {'source': 'dezeen', 'limit': 80, 'auto_translate': True}
    ]

    with ThreadPoolExecutor(max_workers=3) as executor:
        # 提交所有任务
        futures = {
            executor.submit(crawl_source, **config): config['source']
            for config in sources
        }

        # 等待完成
        for future in as_completed(futures):
            source = futures[future]
            try:
                result = future.result()
                logger.success(f"✅ {source} 完成: {result}")
            except Exception as e:
                logger.error(f"❌ {source} 失败: {e}")

# 使用
if __name__ == "__main__":
    crawl_all_parallel()
```

**运行**:
```bash
python scripts/crawl_parallel.py
```

**优势**:
- ✅ 简单易用（单文件脚本）
- ✅ 无需Celery（适合小规模）
- ✅ 可控并发数（避免资源耗尽）

**劣势**:
- ❌ 单进程瓶颈（Python GIL）
- ❌ 无法跨机器分布
- ❌ 错误影响范围大

---

### 方案3：多进程Pool（适中）

**原理**: 用多进程绕过Python GIL限制

```python
from multiprocessing import Pool

def crawl_worker(config):
    """Worker进程"""
    source = config['source']
    logger.info(f"🚀 启动 {source} 爬取")

    crawler = IndexBasedCrawler(
        auto_translate=config['auto_translate'],
        translation_engine='deepseek'
    )

    return crawler.crawl_from_index(
        source=source,
        limit=config['limit']
    )

if __name__ == "__main__":
    sources = [
        {'source': 'archdaily', 'limit': 100, 'auto_translate': True},
        {'source': 'gooood', 'limit': 50, 'auto_translate': False},
        {'source': 'dezeen', 'limit': 80, 'auto_translate': True}
    ]

    with Pool(processes=3) as pool:
        results = pool.map(crawl_worker, sources)

    for result in results:
        print(result)
```

---

### 并行限制和注意事项

#### 1. Rate Limit（频率限制）

每个网站有独立的rate limit，不冲突：

```python
# RateLimiter实例按source隔离
class RateLimiter:
    _instances = {}  # 每个source一个实例

    @classmethod
    def get_instance(cls, source: str, rate_limit: float):
        if source not in cls._instances:
            cls._instances[source] = cls(rate_limit)
        return cls._instances[source]
```

- Archdaily: 1.5秒/请求
- Gooood: 2.0秒/请求
- Dezeen: 1.0秒/请求

**并行OK**: ✅ 互不影响

---

#### 2. 数据库并发写入

PostgreSQL支持并发写入：

```python
# 每个worker有独立数据库连接
db = get_external_db()  # 线程安全的连接池
db.save(project)  # ACID事务保证
```

**注意事项**:
- ✅ 主键冲突自动处理（`url` UNIQUE约束）
- ✅ 使用连接池（避免连接耗尽）
- ⚠️ 避免死锁（尽量单条插入）

---

#### 3. 翻译API并发

Deepseek API支持并发：

```python
# 翻译器实例可并发调用
translator = get_translator('deepseek')

# 每个请求独立
translation = translator.translate_project(project)
# API服务端处理并发，客户端无需担心
```

**并发限制**:
- Deepseek: 无官方限制（建议<20 QPM）
- 成本线性增长（0.004元/篇 × 并发数）

---

#### 4. 内存占用

每个爬虫实例约50-100MB内存：

- **单进程3线程**: 200MB
- **3进程**: 300MB
- **Celery 3 Worker**: 450MB

**建议配置**:
- 内存 < 4GB: 方案2（ThreadPoolExecutor）
- 内存 ≥ 4GB: 方案1（Celery多Worker）

---

### 并行方案对比

| 方案 | 并发度 | 复杂度 | 时间 | 适用场景 |
|------|--------|--------|------|----------|
| **串行（当前）** | 1 | ⭐ | 90分钟 | 测试阶段 |
| **ThreadPool** | 3 | ⭐⭐ | 30分钟 | 小规模（<1000篇/周）|
| **MultiProcess** | 3 | ⭐⭐⭐ | 30分钟 | 中规模（<5000篇/周）|
| **Celery** | 3+ | ⭐⭐⭐⭐ | 30分钟 | 生产环境（任意规模）|

**推荐**: **Celery多Worker方案**（生产级）

---

## 📈 监控运维

### 实时监控

#### 1. Celery Flower监控面板

```bash
# 启动Flower
celery -A intelligent_project_analyzer.external_data_system.celery_app flower \
    --port=5555 --broker=redis://localhost:6379/0

# 访问
http://localhost:5555
```

**功能**:
- ✅ Worker状态（在线/离线）
- ✅ 任务队列长度
- ✅ 任务执行时间分布
- ✅ 成功/失败率统计

---

#### 2. 爬取进度查询

```python
# scripts/check_crawl_status.py
from intelligent_project_analyzer.external_data_system.project_index import ProjectIndexManager

index_mgr = ProjectIndexManager()
stats = index_mgr.get_statistics()

print(f"""
📊 爬取进度统计

总计: {stats['total']} 个项目
已爬取: {stats['crawled']} 个
未爬取: {stats['uncrawled']} 个
完成率: {stats['crawled'] / stats['total'] * 100:.1f}%

按来源分布:
  Archdaily: {stats['by_source']['archdaily']['crawled']}/{stats['by_source']['archdaily']['total']} ({stats['by_source']['archdaily']['crawled']/stats['by_source']['archdaily']['total']*100:.1f}%)
  Gooood:    {stats['by_source']['gooood']['crawled']}/{stats['by_source']['gooood']['total']}
  Dezeen:    {stats['by_source']['dezeen']['crawled']}/{stats['by_source']['dezeen']['total']}
""")
```

---

#### 3. 翻译质量报告

```sql
-- 翻译质量分布
SELECT
    CASE
        WHEN translation_quality >= 0.8 THEN '优秀(≥0.8)'
        WHEN translation_quality >= 0.7 THEN '良好(0.7-0.8)'
        WHEN translation_quality >= 0.6 THEN '待审核(0.6-0.7)'
        ELSE '不合格(<0.6)'
    END as quality_tier,
    COUNT(*) as count,
    ROUND(AVG(translation_quality), 3) as avg_quality
FROM external_projects
WHERE translation_quality IS NOT NULL
GROUP BY quality_tier
ORDER BY avg_quality DESC;

-- 结果示例:
-- quality_tier       | count | avg_quality
-- -------------------+-------+-------------
-- 优秀(≥0.8)         | 1500  | 0.845
-- 良好(0.7-0.8)      | 800   | 0.752
-- 待审核(0.6-0.7)    | 200   | 0.651
-- 不合格(<0.6)       | 50    | 0.520
```

---

### 日志系统

**日志配置**: `loguru`

```python
from loguru import logger

logger.add(
    "logs/crawler_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # 每天午夜轮换
    retention="30 days",  # 保留30天
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
)
```

**关键日志**:
```
2026-02-17 21:11:42 | INFO  | dezeen_spider:fetch_project_detail:285 - 📖 爬取项目详情: https://...
2026-02-17 21:11:54 | SUCCESS | dezeen_spider:fetch_project_detail:339 - ✅ 项目爬取成功: Sou Fujimoto...
2026-02-17 21:12:08 | SUCCESS | translator:translate_project:137 - 翻译完成，质量评分: 0.60
```

---

### 错误处理

#### 常见错误和解决方案

| 错误类型 | 原因 | 解决方案 |
|---------|------|---------|
| **RequestException** | 网络超时 | 重试3次（exponential backoff）|
| **ParseError** | HTML结构变化 | 通知管理员，人工检查 |
| **TranslationAPIError** | API限流 | 降低并发，增加延迟 |
| **DatabaseError** | 唯一约束冲突 | 跳过已存在项目 |
| **RateLimitExceeded** | 请求过快 | 自动等待（RateLimiter）|

**重试策略**:
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(requests.RequestException)
)
def fetch_with_retry(url):
    return requests.get(url, timeout=30)
```

---

## 📖 使用指南

### 快速开始

#### 1. 环境准备

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量（.env）
DEEPSEEK_API_KEY=sk-xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com
DATABASE_URL=postgresql://user:pass@localhost/dbname
REDIS_URL=redis://localhost:6379/0

# 3. 初始化数据库
python scripts/setup_database.py
```

---

#### 2. 单次手动爬取

```bash
# 爬取Dezeen最新10篇（带翻译）
python scripts/crawl_from_index.py \
    --source dezeen \
    --limit 10 \
    --auto-translate \
    --translation-engine deepseek

# 爬取Gooood最新20篇（中文无需翻译）
python scripts/crawl_from_index.py \
    --source gooood \
    --limit 20

# 查看进度
python scripts/check_crawl_status.py
```

---

#### 3. 启动定时任务

```bash
# 1. 启动Redis
redis-server

# 2. 启动Celery Worker
celery -A intelligent_project_analyzer.external_data_system.celery_app worker \
    --loglevel=info \
    --concurrency=2

# 3. 启动Celery Beat（调度器）
celery -A intelligent_project_analyzer.external_data_system.celery_app beat \
    --loglevel=info

# 4. 启动Flower监控（可选）
celery -A intelligent_project_analyzer.external_data_system.celery_app flower \
    --port=5555
```

---

#### 4. 并行爬取（生产环境）

```bash
# 方案1: 启动3个独立Worker（每个处理一个网站）
# Terminal 1
celery -A intelligent_project_analyzer.external_data_system.celery_app worker \
    --queue=archdaily --concurrency=1 --hostname=archdaily@%h

# Terminal 2
celery -A intelligent_project_analyzer.external_data_system.celery_app worker \
    --queue=gooood --concurrency=1 --hostname=gooood@%h

# Terminal 3
celery -A intelligent_project_analyzer.external_data_system.celery_app worker \
    --queue=dezeen --concurrency=1 --hostname=dezeen@%h

# Terminal 4: Beat调度器
celery -A intelligent_project_analyzer.external_data_system.celery_app beat
```

---

### 高级配置

#### 自定义翻译质量阈值

```python
# translation/translator.py
class ProjectTranslator:
    def __init__(self, quality_threshold: float = 0.7):
        self.quality_threshold = quality_threshold

    def translate_project(self, project):
        # ... 翻译逻辑
        if result['quality'] < self.quality_threshold:
            logger.warning(f"⚠️ 翻译质量低于阈值: {result['quality']}")
            # 标记为需要人工审核
            result['needs_review'] = True
        return result
```

---

#### 批量翻译历史项目

```python
# scripts/batch_translate_existing.py
from intelligent_project_analyzer.external_data_system import get_external_db
from intelligent_project_analyzer.external_data_system.translation import get_translator

db = get_external_db()
translator = get_translator('deepseek')

# 查找未翻译的英文项目
projects = db.query(ExternalProject).filter(
    ExternalProject.source.in_(['archdaily', 'dezeen']),
    ExternalProject.description_zh.is_(None)
).limit(100).all()

for project in projects:
    logger.info(f"翻译项目: {project.url}")

    # 翻译
    translation = translator.translate_project(project)

    # 更新数据库
    project.title_zh = translation['title_zh']
    project.description_zh = translation['description_zh']
    project.translation_quality = translation['quality']
    project.translation_engine = 'deepseek'
    project.translated_at = datetime.now()

    db.commit()
```

---

## 🔍 查看爬取成果

爬取完成后，可通过以下方式查看和检索已入库的项目数据。

### 1. 前端管理面板（推荐）

| 页面 | URL | 说明 |
|------|-----|------|
| **爬虫监控** | http://localhost:3001/admin/crawler-monitor | 统计概览、分类进度、实时日志、WebSocket 监控 |
| **案例展示** | http://localhost:3001/showcase | 面向用户的精选案例浏览 |

管理面板展示 4 个核心指标：
- **DB 项目数** — 数据库中该数据源已入库的项目总数
- **站点估算** — 该网站预估的总项目数（所有分类之和）
- **Checkpoint** — 已保存断点的分类数 / 总分类数（用于断点续爬）
- **最后同步** — 上次同步完成的时间

### 2. REST API 查询

后端服务运行后，可通过 Swagger UI（http://localhost:8000/docs）交互式调用。

#### 统计接口

```bash
# 爬取统计（总数、按来源分组）
GET /api/crawler/stats

# 各数据源详细状态（DB项目数、站点估算、Checkpoint、最后同步时间）
GET /api/crawler/schedule/source-status?source=gooood

# 数据源统计
GET /api/external/source-stats
```

#### 搜索与推荐接口

```bash
# 语义搜索项目
POST /api/external/search/semantic
Body: {"query": "现代简约住宅设计", "limit": 10}

# 查找相似项目
GET /api/external/search/similar/{project_id}

# 基于偏好推荐项目
POST /api/external/search/recommend
Body: {"preferences": {"style": "现代", "type": "住宅"}}

# 热门趋势项目
GET /api/external/search/trending

# 高质量项目展示
GET /api/external/search/showcase
```

### 3. 命令行脚本（直连数据库）

```bash
# 终端逐条打印所有已爬取项目（标题、URL、分类、面积等）
python _show_crawl_data.py

# 导出完整爬取数据到文件（含描述和同步历史）
python _dump_crawl_data.py
# → 输出到 _crawl_full_data.txt

# 查看爬虫调度状态
python scripts/crawl_scheduler.py status
```

### 4. VS Code 任务快捷入口

在 VS Code 中按 `Ctrl+Shift+P` → "运行任务"，可快速执行：

| 任务名称 | 说明 |
|----------|------|
| 🕷️ 爬虫状态查看 | 运行 `crawl_scheduler.py status` 查看调度状态 |
| 🕷️ 启动爬虫调度器 | 后台启动定时调度守护进程 |
| 🕷️ 爬虫全量 gooood | 触发谷德设计网全量爬取 |
| 🕷️ 爬虫全量 archdaily_cn | 触发 ArchDaily 中文站全量爬取 |

---

## 🎯 总结

### 当前状态（v2.0）

| 指标 | 状态 | 数值 |
|------|------|------|
| **支持网站** | ✅ 生产就绪 | 3个（Archdaily, Gooood, Dezeen）|
| **数据总量** | 🟡 少量测试 | ~50篇 |
| **翻译系统** | ✅ 已完成 | Deepseek集成完毕 |
| **并行能力** | ✅ 支持 | Celery多Worker |
| **调度配置** | ✅ 已配置 | 每周自动更新 |
| **监控系统** | ✅ 可用 | Flower + Loguru |

---

### 下一步计划

#### 短期（1-2周）
1. ✅ **修复翻译质量评分**（长度比例阈值优化）
2. ✅ **增加max_tokens到8000**（支持长文本）
3. 🔲 **首次全量爬取**（Dezeen 46篇 → 5000篇）
4. 🔲 **测试并行爬取**（3个Worker同时运行）
5. 🔲 **翻译成本监控**（统计API调用费用）

#### 中期（1-2月）
1. 🔲 **Archdaily全量爬取**（目标5000篇）
2. 🔲 **Gooood全量爬取**（目标3000篇）
3. 🔲 **图片下载和存储**（MinIO/S3集成）
4. 🔲 **向量化索引**（OpenAI Embeddings）
5. 🔲 **语义搜索API**（基于向量相似度）

#### 长期（3-6月）
1. 🔲 **新增数据源**（Architizer, ArchDaily中文版）
2. 🔲 **智能推荐系统**（基于用户偏好）
3. 🔲 **前端展示页面**（项目浏览和搜索）
4. 🔲 **用户收藏功能**（个人项目库）
5. 🔲 **多语言支持**（增加日语、韩语）

---

### 关键决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| **翻译引擎** | Deepseek | 成本低（¥4/千篇 vs GPT-4 ¥120）|
| **存储方案** | 双语存储 | 避免重复翻译，查询快速 |
| **调度方案** | Celery Beat | 生产级，支持分布式 |
| **并行方案** | 多Worker | 真并行，易扩展 |
| **数据库** | PostgreSQL | 支持向量索引，JSON查询 |
| **更新频率** | 每周一次 | 平衡新鲜度与成本 |

---

## 📞 联系和支持

- **技术负责人**: [您的名字]
- **文档版本**: v2.0
- **最后更新**: 2026-02-17
- **维护状态**: 🟢 活跃维护中

---

**🎉 祝爬取顺利！**
