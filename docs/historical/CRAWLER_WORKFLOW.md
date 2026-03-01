# 爬虫系统工作流程说明

## 📋 概述

新的爬虫系统采用**两阶段爬取**策略：
1. **第一阶段**：爬取项目列表，建立索引
2. **第二阶段**：从索引读取，逐一爬取详情

这种方式的优势：
- ✅ 支持断点续爬
- ✅ 支持增量更新
- ✅ 便于监控进度
- ✅ 避免重复爬取
- ✅ 便于定期更新计划

---

## 🗂️ 网站结构分析

### 1. 分析网站结构

首次使用前，先分析各网站的结构和分类：

```bash
python scripts/analyze_website_structures.py
```

输出：
- `data/website_structures.json` - 包含各网站的分类、URL模式等信息

分析结果示例：
```json
{
  "archdaily": {
    "categories": [...],  // 19个分类
    "pagination_type": "无限滚动或API",
    "list_url_patterns": [...]
  },
  "gooood": {
    "categories": [...],  // 29个分类（type+series）
    "pagination_type": "动态加载（Vue.js）",
    "list_url_patterns": [...]
  }
}
```

---

## 📊 第一阶段：爬取项目列表

### 2. 完整爬取所有分类列表

```bash
# 爬取所有网站的所有分类
python scripts/crawl_project_lists.py --source all --mode full --max-pages 20

# 只爬取Archdaily
python scripts/crawl_project_lists.py --source archdaily --mode full --max-pages 20

# 只爬取Gooood
python scripts/crawl_project_lists.py --source gooood --mode full --max-pages 30
```

参数说明：
- `--source`: archdaily | gooood | all
- `--mode`: full（完整爬取）| incremental（增量更新）
- `--max-pages`: 每个分类最多爬取多少页
- `--max-categories`: 限制爬取分类数（用于测试）

### 3. 测试爬取（少量分类）

```bash
# 只爬取前3个分类，每个分类5页
python scripts/crawl_project_lists.py --source gooood --mode full --max-categories 3 --max-pages 5
```

### 4. 增量爬取（定期更新）

只爬取首页的最新项目：

```bash
# 每天运行，爬取首页新项目
python scripts/crawl_project_lists.py --source all --mode incremental --max-pages 10
```

### 5. 查看索引统计

```bash
python scripts/crawl_project_lists.py --stats-only
```

输出示例：
```
项目索引统计
================================================================================
总项目数: 5234
已爬取: 1250
未爬取: 3984
爬取进度: 23.9%

按来源统计:
  ARCHDAILY:
    总数: 2500
    已爬: 800
    未爬: 1700
    进度: 32.0%

  GOOOOD:
    总数: 2734
    已爬: 450
    未爬: 2284
    进度: 16.5%
```

---

## 🕷️ 第二阶段：爬取项目详情

### 6. 从索引爬取详情

```bash
# 爬取所有未爬取的项目
python scripts/crawl_from_index.py --limit 100

# 只爬取Archdaily的项目
python scripts/crawl_from_index.py --source archdaily --limit 50

# 只爬取指定分类
python scripts/crawl_from_index.py --source gooood --category 建筑 --limit 30
```

参数说明：
- `--source`: archdaily | gooood
- `--category`: 指定分类名称
- `--limit`: 最多爬取数量
- `--retry-failed`: 重试之前失败的项目
- `--no-skip-errors`: 不跳过多次失败的项目

### 7. 重试失败的项目

```bash
# 重试失败的项目（之前失败次数<3）
python scripts/crawl_from_index.py --retry-failed --limit 50
```

---

## 📅 定期更新计划

### 每日增量更新

```bash
# 每天凌晨2点运行
# 1. 爬取首页新项目（10页）
python scripts/crawl_project_lists.py --source all --mode incremental --max-pages 10

# 2. 爬取新发现的项目详情
python scripts/crawl_from_index.py --limit 200
```

### 每周完整更新

```bash
# 每周日运行
# 1. 重新爬取所有分类列表（发现新项目）
python scripts/crawl_project_lists.py --source all --mode full --max-pages 20

# 2. 爬取新发现的项目
python scripts/crawl_from_index.py --limit 1000
```

### 每月质量检查

```bash
# 重试之前失败的项目
python scripts/crawl_from_index.py --retry-failed --limit 500
```

---

## 📂 数据存储

### 项目索引数据库

文件: `data/project_index.db`

表结构:
```sql
CREATE TABLE project_index (
  id INTEGER PRIMARY KEY,
  source VARCHAR(50),         -- archdaily, gooood
  source_id VARCHAR(200),     -- 源网站ID
  url VARCHAR(500) UNIQUE,    -- 项目完整URL
  category VARCHAR(100),      -- 分类
  sub_category VARCHAR(100),  -- 子分类
  discovered_at DATETIME,     -- 发现时间
  crawled_at DATETIME,        -- 爬取时间
  is_crawled BOOLEAN,         -- 是否已爬取
  crawl_attempts INTEGER,     -- 爬取尝试次数
  last_error TEXT,            -- 最后错误
  title VARCHAR(500),         -- 标题
  preview_image VARCHAR(500)  -- 预览图
);
```

索引：
- `idx_source_crawled`: (source, is_crawled)
- `idx_source_category`: (source, category)
- `idx_discovered_at`: (discovered_at)

### 项目详情数据库

文件: `data/projects.db`

表结构见 `DatabaseStorage` 类

---

## 🔍 监控和统计

### 查看爬取进度

```bash
# 查看索引统计
python scripts/crawl_project_lists.py --stats-only

# 查看数据库统计
python scripts/monitor_data_quality.py
```

### 检查数据质量

```bash
# 查看质量分布
python scripts/monitor_data_quality.py

# 查看失败项目
sqlite3 data/project_index.db "SELECT url, last_error, crawl_attempts FROM project_index WHERE is_crawled=0 AND crawl_attempts>0 LIMIT 10;"
```

---

## 🛠️ 常见场景

### 场景1: 首次完整爬取

```bash
# 1. 分析网站结构
python scripts/analyze_website_structures.py

# 2. 爬取所有列表（测试少量分类）
python scripts/crawl_project_lists.py --source all --mode full --max-categories 2 --max-pages 5

# 3. 查看统计
python scripts/crawl_project_lists.py --stats-only

# 4. 爬取详情（少量测试）
python scripts/crawl_from_index.py --limit 10

# 5. 确认无误后，完整爬取
python scripts/crawl_project_lists.py --source all --mode full --max-pages 50
python scripts/crawl_from_index.py --limit 5000
```

### 场景2: 增量更新

```bash
# 每天运行
python scripts/crawl_project_lists.py --source all --mode incremental --max-pages 10
python scripts/crawl_from_index.py --limit 200
```

### 场景3: 只爬取特定分类

```bash
# 1. 查看可用分类
cat data/website_structures.json | jq '.gooood.categories[].name'

# 2. 爬取特定分类列表（假设已经爬过列表）
# （列表已在索引中，直接爬详情）

# 3. 爬取该分类的详情
python scripts/crawl_from_index.py --source gooood --category 建筑 --limit 100
```

### 场景4: 断点续爬

```bash
# 如果上次爬取中断，直接继续：
python scripts/crawl_from_index.py --limit 1000

# 系统会自动从索引中读取未爬取的项目继续
```

---

## ⚙️ Celery 定时任务配置

### 配置文件

编辑 `intelligent_project_analyzer/external_data_system/celery_app.py`:

```python
# 增量更新任务
@app.task(name='sync.incremental_update')
def incremental_update():
    """每日增量更新"""
    # 1. 爬取首页新项目
    from scripts.crawl_project_lists import ListCrawler
    crawler = ListCrawler()
    crawler.crawl_homepage_lists("archdaily", max_pages=10)
    crawler.crawl_homepage_lists("gooood", max_pages=10)
    crawler.close()

    # 2. 爬取新项目详情
    from scripts.crawl_from_index import IndexBasedCrawler
    detail_crawler = IndexBasedCrawler()
    detail_crawler.crawl_from_index(limit=200)
    detail_crawler.close()

# 定时任务配置
app.conf.beat_schedule = {
    'daily-incremental-update': {
        'task': 'sync.incremental_update',
        'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点
    },
}
```

### 启动Celery

```bash
# Terminal 1: 启动Worker
celery -A intelligent_project_analyzer.external_data_system.celery_app worker -l info

# Terminal 2: 启动Beat（定时任务调度器）
celery -A intelligent_project_analyzer.external_data_system.celery_app beat -l info
```

---

## 📈 性能优化建议

1. **列表爬取**：
   - 每个分类20-50页足够（大多数项目在前几页）
   - 使用`--max-categories`测试少量分类
   - Gooood需要Playwright，速度慢，建议晚上运行

2. **详情爬取**：
   - 使用`--limit`控制每次爬取数量
   - Archdaily: 可以100个/次
   - Gooood: 建议30-50个/次（Playwright慢）

3. **增量更新**：
   - 首页10页足够捕获最新项目
   - 每天运行，保持数据新鲜

4. **错误处理**：
   - 失败3次的项目自动跳过
   - 使用`--retry-failed`定期重试
   - 检查`last_error`字段分析失败原因

---

## 🚀 快速开始

```bash
# 1. 测试爬取（5分钟）
python scripts/crawl_project_lists.py --source gooood --mode full --max-categories 1 --max-pages 2
python scripts/crawl_from_index.py --limit 3

# 2. 查看结果
python scripts/crawl_project_lists.py --stats-only
python scripts/monitor_data_quality.py

# 3. 满意后，完整爬取（数小时）
python scripts/crawl_project_lists.py --source all --mode full --max-pages 30
python scripts/crawl_from_index.py --limit 1000
```

---

## 📞 常见问题

**Q: 列表爬取很慢怎么办？**
A: Gooood使用Playwright，每页需要10-15秒。建议:
- 减少`--max-pages`（20页足够）
- 使用`--max-categories`测试少量分类
- 晚上运行完整爬取

**Q: 如何判断列表是否爬完整了？**
A: 检查`--stats-only`输出的项目总数，对比网站预期:
- Archdaily: 约10,000+
- Gooood: 约8,000-12,000

**Q: 爬取中断了怎么办？**
A: 直接继续运行相同命令，系统会:
- 列表爬取：跳过已存在的URL
- 详情爬取：只爬取`is_crawled=False`的项目

**Q: 如何清空索引重新开始？**
A: 删除索引数据库：
```bash
rm data/project_index.db
```

**Q: 增量更新会爬取重复项目吗？**
A: 不会，索引数据库的URL字段是UNIQUE约束，自动去重。
