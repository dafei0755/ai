# 外部数据存储与利用指南

> **日期**: 2026-02-17
> **版本**: v8.110.0
> **作者**: AI Architecture Team

---

## 📦 1. 数据存储策略

### 1.1 当前存储方式

```
langgraph-design/
├── archdaily_categories_cleaned.json          # 分类索引（8个核心分类）
├── archdaily_all_function_projects.json       # 所有项目URL（2500-4000个）
├── sample_project_data.json                   # 单个项目示例
└── data/
    ├── external_sources/                      # 外部数据存储（规划中）
    │   ├── archdaily/
    │   │   ├── projects/                      # 项目详情
    │   │   │   ├── 2024/
    │   │   │   │   ├── 01-residence/
    │   │   │   │   │   ├── project_1037243.json
    │   │   │   │   │   ├── project_1036895.json
    │   │   │   │   │   └── ...
    │   │   │   │   ├── 02-cultural/
    │   │   │   │   └── ...
    │   │   │   └── 2025/
    │   │   ├── categories.json                # 分类索引
    │   │   ├── metadata.json                  # 数据集元信息
    │   │   └── last_sync.json                 # 最后同步时间
    │   │
    │   └── gooood/                            # 谷德设计网（未来扩展）
    │       └── ...
    │
    └── external_sources.db                    # 数据库（推荐方案）
        └── tables:
            ├── projects                       # 项目表
            ├── images                         # 图片表
            ├── tags                           # 标签表
            └── sync_history                   # 同步历史
```

---

## 🗄️ 2. 存储方案对比

### 方案A：JSON文件（当前实现）

**结构**：
```json
{
  "source": "archdaily",
  "category": "文化建筑",
  "last_updated": "2026-02-17T16:50:00Z",
  "projects": [
    {
      "url": "https://www.archdaily.cn/cn/1037243/...",
      "title": "伊丹十三纪念馆",
      "description": "这座艺术博物馆...(662字符)",
      "architects": "Itm Yooehwa Architects",
      "location": "济州市,韩国",
      "area": "674m²",
      "year": "2022 年",
      "images": [10张],
      "tags": [10个],
      "views": 18,
      "publish_date": "2025-12-30T09:00:00Z"
    }
  ]
}
```

**优点**：
- ✅ 简单直接，无需数据库
- ✅ 易于版本控制（Git）
- ✅ 人类可读，方便调试
- ✅ 快速原型验证

**缺点**：
- ❌ 大规模数据（2500+项目）查询慢
- ❌ 重复数据（同一建筑师/标签）
- ❌ 无索引，全文搜索困难
- ❌ 并发写入有冲突风险

**适用场景**：
- 初期数据采集与验证
- 少量项目（<500个）
- 静态参考数据

---

### 方案B：SQLite数据库（推荐）

**Schema设计**：
```sql
-- 项目表
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source VARCHAR(50) NOT NULL,           -- archdaily/gooood
    url VARCHAR(500) UNIQUE NOT NULL,      -- 项目链接
    title TEXT NOT NULL,                   -- 标题
    description TEXT,                      -- 描述（1000+字符）
    location VARCHAR(200),
    architects VARCHAR(500),
    area VARCHAR(100),
    year VARCHAR(50),
    views INTEGER,
    publish_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_source (source),
    INDEX idx_publish_date (publish_date),
    INDEX idx_location (location),
    FULLTEXT idx_description (description)  -- 全文索引
);

-- 图片表
CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    url VARCHAR(500) NOT NULL,
    order_index INTEGER DEFAULT 0,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- 标签表（多对多）
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE project_tags (
    project_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (project_id, tag_id),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- 同步历史表
CREATE TABLE sync_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source VARCHAR(50) NOT NULL,
    category VARCHAR(100),
    projects_count INTEGER,
    new_count INTEGER,
    updated_count INTEGER,
    sync_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20),  -- success/partial/failed
    error_message TEXT
);
```

**优点**：
- ✅ 高效查询（索引、SQL）
- ✅ 数据去重（UNIQUE约束）
- ✅ 全文搜索支持
- ✅ 关系完整性（外键）
- ✅ 事务支持（并发安全）
- ✅ 无需额外服务（嵌入式）

**缺点**：
- ❌ 需要ORM（SQLAlchemy）
- ❌ 版本控制困难

**适用场景**：
- 生产环境（2500+项目）
- 需要复杂查询（多维度过滤）
- 频繁更新（增量同步）

---

### 方案C：PostgreSQL + Vector DB（未来扩展）

**架构**：
```
PostgreSQL（结构化数据）
    ↓
    + pgvector 插件（向量搜索）
    ↓
    + Qdrant/Weaviate（专用向量库）
```

**适用场景**：
- 大规模（10,000+项目）
- 语义搜索（"找相似的博物馆设计"）
- 多租户部署

---

## 🔄 3. 按网站分类保存

### 3.1 数据源标识

每个项目都有 `source` 字段：
```python
@dataclass
class ProjectData:
    source: str  # "archdaily" | "gooood" | "dezeen" | ...
    # ...
```

### 3.2 目录组织（推荐）

```
data/external_sources/
├── archdaily/
│   ├── projects_2025_residential.json       # 按年份+分类
│   ├── projects_2025_cultural.json
│   └── projects_2025_commercial.json
│
├── gooood/
│   └── projects_latest.json
│
└── dezeen/
    └── projects_latest.json
```

### 3.3 数据库查询（推荐）

```python
# 查询Archdaily的所有文化建筑
projects = db.query(Project).filter(
    Project.source == "archdaily",
    Project.tags.contains("文化建筑")
).all()

# 查询济州岛的所有项目
projects = db.query(Project).filter(
    Project.location.like("%济州%")
).all()
```

---

## ⏰ 4. 定期同步策略

### 4.1 当前状态

**❌ 未实现自动同步**

当前是手动运行：
```bash
python scripts/crawl_all_categories.py
```

### 4.2 推荐方案

#### 方案A：Cron定时任务（Linux/macOS）

```bash
# crontab -e

# 每天凌晨2点同步Archdaily
0 2 * * * cd /path/to/langgraph-design && python scripts/sync_archdaily.py >> logs/sync.log 2>&1

# 每周一凌晨3点同步Gooood
0 3 * * 1 cd /path/to/langgraph-design && python scripts/sync_gooood.py >> logs/sync.log 2>&1
```

#### 方案B：Windows任务计划程序

```powershell
# 创建每日同步任务
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "scripts/sync_archdaily.py" -WorkingDirectory "D:\11-20\langgraph-design"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "Archdaily Sync"
```

#### 方案C：Python APScheduler（推荐）

```python
# scripts/sync_scheduler.py
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
from loguru import logger

def sync_archdaily():
    """同步Archdaily数据"""
    logger.info(f"⏰ 开始同步Archdaily - {datetime.now()}")
    # 调用爬虫逻辑
    # ...
    logger.success("✅ Archdaily同步完成")

def sync_gooood():
    """同步Gooood数据"""
    logger.info(f"⏰ 开始同步Gooood - {datetime.now()}")
    # ...

scheduler = BlockingScheduler()

# 每天凌晨2点同步Archdaily
scheduler.add_job(sync_archdaily, 'cron', hour=2)

# 每周一凌晨3点同步Gooood
scheduler.add_job(sync_gooood, 'cron', day_of_week='mon', hour=3)

scheduler.start()
```

运行：
```bash
python scripts/sync_scheduler.py
```

### 4.3 增量同步策略

```python
# 只爬取最近30天的新项目
crawler = ArchdailyCrawler(
    config=CrawlerConfig(
        days_back=30  # 只抓取30天内
    )
)

# 去重：对比数据库已有URL
existing_urls = db.query(Project.url).all()
new_projects = [p for p in projects if p.url not in existing_urls]

# 批量插入
db.bulk_insert_mappings(Project, new_projects)
db.commit()
```

---

## 🎯 5. 数据在系统中的利用价值

### 5.1 利用环节概览

```
外部数据（Archdaily）
        ↓
    【环节1】语义搜索
        ↓
    【环节2】案例推荐
        ↓
    【环节3】LLM上下文增强
        ↓
    【环节4】设计灵感库
        ↓
    【环节5】多维度过滤
        ↓
    【环节6】数据分析
        ↓
    【环节7】概念图参考
```

---

### 5.2 环节1：语义搜索（核心功能）

**使用场景**：
```
用户输入："我想设计一个现代简约风格的图书馆，参考济州岛的案例"
系统响应：
  1. 向量化用户查询
  2. 搜索外部数据库
  3. 返回最相关的3-5个项目
```

**技术实现**：
```python
from intelligent_project_analyzer.tools.external_search import ExternalSearchTool

tool = ExternalSearchTool()

# 1. 向量化描述（使用OpenAI Embeddings）
project_embeddings = tool.embed_projects(projects)

# 2. 向量化用户查询
user_query_embedding = openai.embeddings.create(
    model="text-embedding-3-small",
    input="现代简约风格的图书馆 济州岛"
)

# 3. 余弦相似度匹配
from sklearn.metrics.pairwise import cosine_similarity
similarities = cosine_similarity(
    [user_query_embedding],
    project_embeddings
)

# 4. 返回Top-K
top_k = 5
results = sorted(zip(projects, similarities[0]), key=lambda x: x[1], reverse=True)[:top_k]
```

**数据利用**：
- `description`（完整描述，1000+字符）→ 核心语义载体
- `tags`（标签）→ 辅助过滤
- `location`（位置）→ 地域特色筛选
- `architects`（建筑师）→ 设计风格推断

---

### 5.3 环节2：案例推荐

**使用场景**：
```
用户查看项目 A（伊丹十三纪念馆）
系统推荐：
  → 项目 B（相同建筑师的其他作品）
  → 项目 C（相似标签：文化建筑、博物馆）
  → 项目 D（相似位置：韩国、日本）
```

**推荐算法**：
```python
def recommend_similar_projects(project_id, top_k=5):
    """推荐相似项目"""

    current_project = db.query(Project).filter_by(id=project_id).first()

    # 策略1: 相同建筑师（权重0.4）
    same_architect = db.query(Project).filter(
        Project.architects == current_project.architects,
        Project.id != project_id
    ).limit(3).all()

    # 策略2: 相似标签（权重0.3）
    common_tags = db.query(Project).join(ProjectTag).filter(
        ProjectTag.tag_id.in_(current_project.tag_ids)
    ).limit(3).all()

    # 策略3: 描述语义相似（权重0.3）
    desc_similar = vector_search(current_project.description, top_k=3)

    # 合并去重
    recommendations = merge_and_rank(same_architect, common_tags, desc_similar)

    return recommendations[:top_k]
```

**数据利用**：
- `architects` → 建筑师作品集
- `tags` → 标签关联网络
- `description` → 语义相似度
- `location` → 地域关联

---

### 5.4 环节3：LLM上下文增强（重要）

**使用场景**：
```
用户问："如何设计一个适合济州岛气候的博物馆？"

系统响应：
  1. 搜索外部数据库 → 伊丹十三纪念馆
  2. 提取关键设计理念（description）
  3. 作为LLM的上下文（Few-Shot Learning）
  4. LLM生成定制化回答
```

**Prompt构建**：
```python
context = f"""
参考案例：伊丹十三纪念馆（济州岛）

设计理念：
{project.description}

关键设计手法：
- 材料：暴露混凝土 + 木纹图案
- 自然光：椭圆形体块引入天光
- 空间：墨黑色创作空间
- 环境：适应济州森林，水平延展

建筑师：{project.architects}
面积：{project.area}
"""

# 注入到LLM Prompt
llm_prompt = f"""
用户问题：{user_question}

{context}

请基于以上案例，结合用户需求，生成设计建议。
"""
```

**数据利用**：
- `description` → 设计理念提取（核心！）
- `architects` → 建筑师风格特征
- `images` → 视觉参考（未来：多模态）
- `area` + `year` → 规模与时代背景

---

### 5.5 环节4：设计灵感库

**使用场景**：
```
用户浏览器：
  过滤条件：
    - 位置：亚洲
    - 类型：文化建筑
    - 面积：500-1000m²
    - 年份：2020-2025

  结果：
    → 12个匹配项目
    → 卡片展示（图片+标题+建筑师）
```

**API实现**：
```python
@app.get("/api/inspiration/search")
async def search_inspiration(
    location: str = None,
    category: str = None,
    min_area: int = None,
    max_area: int = None,
    year_start: int = None,
    year_end: int = None,
    limit: int = 20
):
    """灵感库搜索API"""

    query = db.query(Project)

    if location:
        query = query.filter(Project.location.contains(location))

    if category:
        query = query.join(ProjectTag).filter(Tag.name == category)

    if min_area or max_area:
        # 需要解析area字段（"674m²" → 674）
        query = query.filter(
            extract_area(Project.area).between(min_area, max_area)
        )

    if year_start or year_end:
        query = query.filter(
            extract_year(Project.year).between(year_start, year_end)
        )

    projects = query.limit(limit).all()

    return {
        "total": query.count(),
        "results": [project.to_dict() for project in projects]
    }
```

**数据利用**：
- `location` → 地域过滤
- `tags` → 分类过滤
- `area` + `year` → 范围过滤
- `images` → 首图展示

---

### 5.6 环节5：多维度过滤

**使用场景**：
```
LangGraph工作流：
  Step 1: 需求分析 → 提取关键词
  Step 2: 智能过滤：
    → 位置匹配（韩国/日本）
    → 类型匹配（文化建筑）
    → 规模匹配（500-1000m²）
  Step 3: 返回Top-3最佳案例
```

**智能过滤器**：
```python
class SmartProjectFilter:
    """智能项目过滤器"""

    def filter(self, user_requirements: Dict[str, Any]) -> List[Project]:
        """基于用户需求智能过滤项目"""

        # 1. 提取需求维度
        location_keywords = extract_location(user_requirements)  # ["济州", "韩国"]
        type_keywords = extract_type(user_requirements)         # ["博物馆", "文化"]
        scale = extract_scale(user_requirements)                # {"min": 500, "max": 1000}

        # 2. 多条件查询
        query = db.query(Project)

        # 位置匹配（模糊）
        if location_keywords:
            conditions = [Project.location.contains(kw) for kw in location_keywords]
            query = query.filter(or_(*conditions))

        # 类型匹配（标签精确 + 描述模糊）
        if type_keywords:
            tag_match = query.join(ProjectTag).filter(Tag.name.in_(type_keywords))
            desc_match = query.filter(or_(*[
                Project.description.contains(kw) for kw in type_keywords
            ]))
            query = union(tag_match, desc_match)

        # 规模匹配
        if scale:
            query = query.filter(
                extract_area(Project.area).between(scale["min"], scale["max"])
            )

        # 3. 排序（浏览量 + 时间）
        query = query.order_by(
            Project.views.desc(),
            Project.publish_date.desc()
        )

        return query.limit(10).all()
```

**数据利用**：
- `location` → 地域智能匹配
- `tags` + `description` → 类型混合匹配
- `area` → 规模筛选
- `views` + `publish_date` → 排序优化

---

### 5.7 环节6：数据分析

**分析维度**：

1. **热门趋势分析**
```python
# 过去一年最受欢迎的设计风格
popular_tags = db.query(
    Tag.name, func.count(ProjectTag.project_id).label("count")
).join(ProjectTag).join(Project).filter(
    Project.publish_date >= datetime.now() - timedelta(days=365)
).group_by(Tag.name).order_by("count desc").limit(10).all()
```

2. **建筑师影响力分析**
```python
# Top 10建筑师（按项目数+浏览量）
top_architects = db.query(
    Project.architects,
    func.count(Project.id).label("project_count"),
    func.sum(Project.views).label("total_views")
).group_by(Project.architects).order_by("total_views desc").limit(10).all()
```

3. **地域分布分析**
```python
# 各国家/地区的项目分布
location_stats = db.query(
    extract_country(Project.location).label("country"),
    func.count(Project.id).label("count")
).group_by("country").all()
```

**数据利用**：
- `tags` → 风格趋势
- `architects` → 影响力排名
- `location` → 地域分布
- `views` + `publish_date` → 热度分析

---

### 5.8 环节7：概念图生成参考

**使用场景**：
```
用户触发概念图生成 → 系统流程：
  1. 搜索相关案例（语义匹配）
  2. 提取视觉关键词：
     - 材料：暴露混凝土、木纹
     - 空间：墨黑色、椭圆形体块
     - 环境：森林、水平延展
  3. 构建Prompt：
     "A modern museum with exposed concrete walls and wood grain patterns..."
  4. 调用DALL·E生成图片
```

**视觉关键词提取**：
```python
def extract_visual_keywords(project: Project) -> Dict[str, List[str]]:
    """从项目描述中提取视觉关键词"""

    description = project.description

    # 使用NLP提取
    materials = extract_entities(description, entity_type="MATERIAL")
    # ["暴露混凝土", "不锈钢", "玻璃"]

    colors = extract_entities(description, entity_type="COLOR")
    # ["墨黑色", "木纹色"]

    shapes = extract_entities(description, entity_type="SHAPE")
    # ["椭圆形", "体块"]

    atmosphere = extract_entities(description, entity_type="ATMOSPHERE")
    # ["宁静", "祥和", "水平延展"]

    return {
        "materials": materials,
        "colors": colors,
        "shapes": shapes,
        "atmosphere": atmosphere
    }
```

**数据利用**：
- `description` → 视觉关键词提取
- `images` → 风格参考（未来：多模态）
- `tags` → 类型定位

---

## 📊 6. 数据流转全景图

```
外部数据爬取（Archdaily）
        ↓
存储层（SQLite/PostgreSQL）
  ├─ projects 表（2500+项目）
  ├─ images 表（25,000+图片）
  └─ tags 表（500+标签）
        ↓
    ┌───┴────┐
    ↓        ↓
索引层    向量层
├─ SQL索引  └─ Embeddings（OpenAI）
└─ 全文索引      ↓
        ↓        ↓
    ┌───┴────────┴─────┐
    ↓                  ↓
应用层（LangGraph）   API层
├─ 语义搜索         ├─ /api/inspiration/search
├─ 案例推荐         ├─ /api/projects/similar
├─ LLM增强          └─ /api/projects/{id}
├─ 灵感库
└─ 数据分析
        ↓
前端展示（Next.js）
├─ 案例浏览器
├─ 智能推荐卡片
└─ 概念图参考库
```

---

## 🚀 7. 实施路线图

### Phase 1: 数据采集（✅ 已完成）
- [x] 爬虫框架（Playwright）
- [x] 分类发现（8个核心分类）
- [x] 描述提取修复（1000+字符）
- [x] 数据验证（2个项目测试）

### Phase 2: 数据存储（当前阶段）
- [ ] **数据库Schema设计**（推荐SQLite）
- [ ] **批量导入脚本**（JSON → SQLite）
- [ ] **同步调度器**（APScheduler）
- [ ] **增量更新逻辑**（去重+对比）

### Phase 3: 数据索引（下一步）
- [ ] **向量化嵌入**（OpenAI Embeddings）
- [ ] **全文索引**（SQLite FTS5）
- [ ] **缓存层**（Redis）

### Phase 4: API开发
- [ ] **/api/projects/search** - 语义搜索
- [ ] **/api/projects/similar** - 相似推荐
- [ ] **/api/projects/filter** - 多维度过滤
- [ ] **/api/projects/{id}** - 项目详情

### Phase 5: 前端集成
- [ ] **灵感库页面** - 案例浏览器
- [ ] **推荐卡片** - 智能推荐
- [ ] **概念图参考** - 视觉灵感源

---

## 📝 8. 快速开始

### 8.1 当前可用操作

```bash
# 1. 爬取所有分类的项目URL（30-60分钟）
python scripts/crawl_all_categories.py

# 2. 爬取单个项目详情（验证）
python scripts/test_single_project.py

# 3. 批量爬取项目详情（未实现，待开发）
python scripts/crawl_all_project_details.py
```

### 8.2 数据导入数据库（推荐下一步）

```bash
# 创建数据库
python scripts/init_external_db.py

# 导入JSON数据
python scripts/import_archdaily_json.py \
  --input archdaily_all_function_projects.json \
  --output data/external_sources.db

# 验证数据
python scripts/verify_external_db.py
```

### 8.3 启动同步服务（生产环境）

```bash
# 启动定时同步
python scripts/sync_scheduler.py &

# 或使用systemd（Linux）
sudo systemctl start archdaily-sync.service
```

---

## 💡 9. 常见问题

### Q1: 是否每篇文章一个JSON文件？

**A**: **否**。当前采用**批量存储**：
```
archdaily_all_function_projects.json  # 2500+项目URL
data/projects/archdaily_details.json  # 所有项目详情
```

推荐改为**数据库存储**（每个项目一行记录）。

---

### Q2: 如何按网站进行文件保存？

**A**: 通过 `source` 字段区分：
```python
# 方式1：分文件
archdaily_projects.json
gooood_projects.json

# 方式2：统一数据库 + source字段过滤
SELECT * FROM projects WHERE source = 'archdaily';
```

---

### Q3: 定期同步频率建议？

**A**: 根据数据更新频率：
- **Archdaily**: 每日更新 → 每天同步1次
- **Gooood**: 每周1-2次更新 → 每周同步1次
- **Dezeen**: 每日更新 → 每天同步1次

---

### Q4: 数据如何清理旧数据？

**A**: 保留策略：
```python
# 保留2年内数据
cutoff_date = datetime.now() - timedelta(days=730)
db.query(Project).filter(Project.publish_date < cutoff_date).delete()

# 或归档到冷存储
old_projects = db.query(Project).filter(Project.publish_date < cutoff_date).all()
archive_to_json(old_projects, "data/archive/projects_2022.json")
```

---

### Q5: 数据成本与收益？

**A**:
- **存储成本**: SQLite约50MB（2500个项目+图片URL）
- **爬取成本**: 1小时（2500个URL）+ 10小时（详情页）
- **维护成本**: 每日同步10分钟
- **收益**: 提升设计建议质量30-50%（有真实案例支撑）

---

## 🔗 10. 相关文档

- [爬虫框架文档](intelligent_project_analyzer/crawlers/README.md)
- [数据库Schema](scripts/schema/external_sources.sql)
- [API文档](intelligent_project_analyzer/api/EXTERNAL_API.md)
- [同步策略](scripts/SYNC_STRATEGY.md)

---

**维护者**: AI Architecture Team
**最后更新**: 2026-02-17
