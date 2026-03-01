# 大规模外部数据系统架构设计

> **规模**: 10,000+ 项目
> **数据源**: 多网站（Archdaily, Gooood, Dezeen, Architizer等）
> **更新**: 定期自动同步
> **应用**: 多角度、多可能性
> **日期**: 2026-02-17
> **版本**: v8.120.0

---

## 🎯 系统目标

### 核心目标
1. **大规模数据采集**：10,000+ 建筑设计项目
2. **多源数据整合**：5-10个主流设计网站
3. **自动化同步**：每日增量更新，无人值守
4. **智能应用**：语义搜索、案例推荐、LLM增强、趋势分析
5. **高可用性**：99.9%可用性，数据完整性保障

### 业务价值
- **提升设计质量**：真实案例支撑（vs 空洞建议）
- **节省时间成本**：自动推荐（vs 手动搜索）
- **挖掘深度洞察**：数据分析（设计趋势、建筑师影响力）
- **驱动创新**：跨领域案例启发（住宅 → 商业空间）

---

## 🏗️ 系统架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                    外部数据生态系统                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [爬虫层] ──────────────────────────────────────────────────    │
│    │                                                             │
│    ├─ Archdaily Spider (核心，8个分类)                          │
│    ├─ Gooood Spider (中文设计网)                                │
│    ├─ Dezeen Spider (国际设计)                                  │
│    ├─ Architizer Spider (A+ Awards)                             │
│    ├─ ArchDaily USA/Brazil (多语言)                             │
│    └─ 自定义 Spider (可扩展)                                     │
│         ↓                                                        │
│  [调度层] ──────────────────────────────────────────────────    │
│    │                                                             │
│    ├─ APScheduler (定时任务)                                    │
│    ├─ Celery (分布式任务队列)                                   │
│    ├─ Redis (任务队列 + 去重)                                   │
│    └─ Monitoring (Prometheus + Grafana)                         │
│         ↓                                                        │
│  [存储层] ──────────────────────────────────────────────────    │
│    │                                                             │
│    ├─ PostgreSQL (结构化数据 + pgvector)                        │
│    ├─ MongoDB (原始HTML + 灵活Schema)                           │
│    ├─ Redis (缓存 + Session)                                    │
│    ├─ MinIO/S3 (图片存储)                                       │
│    └─ Elasticsearch (全文搜索)                                  │
│         ↓                                                        │
│  [索引层] ──────────────────────────────────────────────────    │
│    │                                                             │
│    ├─ Vector Index (OpenAI Embeddings + Qdrant)                 │
│    ├─ Full-Text Index (Elasticsearch)                           │
│    ├─ Graph Index (Neo4j - 建筑师关系网)                        │
│    └─ Time-Series Index (InfluxDB - 趋势分析)                   │
│         ↓                                                        │
│  [应用层] ──────────────────────────────────────────────────    │
│    │                                                             │
│    ├─ Semantic Search API (语义搜索)                            │
│    ├─ Recommendation Engine (推荐系统)                          │
│    ├─ LLM Context Provider (上下文增强)                          │
│    ├─ Analytics Dashboard (数据分析)                            │
│    ├─ Trend Analyzer (趋势预测)                                 │
│    └─ Visual Inspiration API (视觉灵感)                         │
│         ↓                                                        │
│  [集成层] ──────────────────────────────────────────────────    │
│    │                                                             │
│    └─ LangGraph Workflow (智能设计助手)                         │
│         ↓                                                        │
│  [用户界面] ────────────────────────────────────────────────    │
│    │                                                             │
│    ├─ Next.js Frontend (Web应用)                                │
│    ├─ Mobile App (React Native)                                 │
│    └─ API Client (第三方集成)                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📡 爬虫层设计（多网站统一框架）

### 3.1 统一爬虫接口

```python
# intelligent_project_analyzer/crawlers/base_spider.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class UnifiedProjectData:
    """统一的项目数据结构（跨网站）"""

    # 必填字段
    source: str                          # archdaily/gooood/dezeen
    source_id: str                       # 网站内部ID
    url: str                             # 项目URL
    title: str                           # 标题
    description: str                     # 描述（核心）

    # 元数据（可选但重要）
    architects: Optional[List[str]] = None      # 建筑师（支持多个）
    location: Optional[Dict[str, str]] = None   # {country, city, address}
    area: Optional[float] = None                # 面积（统一为平方米）
    year: Optional[int] = None                  # 年份（统一为整数）
    cost: Optional[Dict[str, float]] = None     # {currency, amount}

    # 媒体资源
    images: List[Dict[str, Any]] = None         # [{url, caption, width, height}]
    videos: List[str] = None                    # 视频URL
    drawings: List[str] = None                  # 图纸URL

    # 分类与标签
    primary_category: Optional[str] = None      # 主分类（住宅/文化/商业）
    sub_categories: List[str] = None            # 子分类
    tags: List[str] = None                      # 标签

    # 社交数据
    views: Optional[int] = None
    likes: Optional[int] = None
    shares: Optional[int] = None

    # 时间戳
    publish_date: Optional[datetime] = None
    crawled_at: datetime = None

    # 原始数据（调试用）
    raw_html: Optional[str] = None

    # 质量评分（后处理）
    quality_score: Optional[float] = None       # 0-1，综合评分

    def __post_init__(self):
        """数据验证与标准化"""
        if not self.crawled_at:
            self.crawled_at = datetime.now()

        # 标准化面积（转换为平方米）
        if self.area:
            self.area = self._normalize_area(self.area)

        # 标准化位置
        if self.location and isinstance(self.location, str):
            self.location = self._parse_location(self.location)

    def _normalize_area(self, area_str: str) -> float:
        """统一面积单位"""
        # 实现：m² / ft² / sqm 等转换
        pass

    def _parse_location(self, location_str: str) -> Dict[str, str]:
        """解析位置字符串"""
        # 实现：从"济州市,韩国" → {city: "济州市", country: "韩国"}
        pass


class BaseSpider(ABC):
    """爬虫基类（统一接口）"""

    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.session = None
        self.stats = {"success": 0, "failed": 0, "skipped": 0}

    @abstractmethod
    def get_source_name(self) -> str:
        """返回数据源名称"""
        pass

    @abstractmethod
    def crawl_list_page(self, url: str) -> List[str]:
        """爬取列表页，返回项目URL列表"""
        pass

    @abstractmethod
    def crawl_project_page(self, url: str) -> UnifiedProjectData:
        """爬取项目详情页"""
        pass

    @abstractmethod
    def validate_data(self, data: UnifiedProjectData) -> bool:
        """验证数据完整性"""
        pass

    def crawl_category(self, category_url: str, max_pages: int = 20) -> List[UnifiedProjectData]:
        """通用爬取流程"""
        projects = []

        for page in range(1, max_pages + 1):
            try:
                # 1. 爬取列表页
                project_urls = self.crawl_list_page(f"{category_url}?page={page}")

                # 2. 爬取详情页
                for url in project_urls:
                    try:
                        project = self.crawl_project_page(url)

                        # 3. 验证数据
                        if self.validate_data(project):
                            projects.append(project)
                            self.stats["success"] += 1
                        else:
                            self.stats["skipped"] += 1

                    except Exception as e:
                        logger.error(f"❌ 爬取失败: {url} - {e}")
                        self.stats["failed"] += 1

                # 4. 限速
                time.sleep(self.config.request_delay)

            except Exception as e:
                logger.error(f"❌ 列表页失败: {category_url}?page={page} - {e}")
                break

        return projects
```

---

### 3.2 多网站爬虫实现

#### 3.2.1 Archdaily Spider（已实现）

```python
class ArchdailySpider(BaseSpider):
    """Archdaily爬虫"""

    def get_source_name(self) -> str:
        return "archdaily"

    def crawl_project_page(self, url: str) -> UnifiedProjectData:
        # 当前已实现逻辑
        # ...
        return UnifiedProjectData(
            source="archdaily",
            source_id=extract_id_from_url(url),
            url=url,
            title=title,
            description=description,  # 已修复，1000+字符
            architects=[architects],
            location={"city": city, "country": country},
            area=parse_area(area_str),
            year=int(year_str.replace("年", "").strip()),
            images=images,
            tags=tags,
            views=views,
            publish_date=publish_date
        )
```

#### 3.2.2 Gooood Spider（谷德设计网）

```python
class GoooodSpider(BaseSpider):
    """谷德设计网爬虫"""

    BASE_URL = "http://www.gooood.cn"

    def get_source_name(self) -> str:
        return "gooood"

    def crawl_list_page(self, url: str) -> List[str]:
        """爬取列表页"""
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        # Gooood特定选择器
        project_links = soup.select("div.post-item a.post-title")

        return [self.BASE_URL + link["href"] for link in project_links]

    def crawl_project_page(self, url: str) -> UnifiedProjectData:
        """爬取项目详情"""
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        # 提取数据（Gooood特定DOM结构）
        title = soup.select_one("h1.entry-title").get_text(strip=True)

        # 描述（多段落）
        content_div = soup.select_one("div.entry-content")
        paragraphs = content_div.find_all("p")
        description = "\n\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 10])

        # 建筑师（从meta或文本提取）
        architects_text = soup.select_one("div.project-info div.architect")
        architects = [architects_text.get_text(strip=True)] if architects_text else []

        # 位置
        location_text = soup.select_one("div.project-info div.location")
        location = self._parse_location(location_text.get_text(strip=True)) if location_text else None

        # 图片
        images = []
        for img in soup.select("div.entry-content img"):
            images.append({
                "url": img["src"],
                "caption": img.get("alt", ""),
                "width": img.get("width"),
                "height": img.get("height")
            })

        return UnifiedProjectData(
            source="gooood",
            source_id=self._extract_id(url),
            url=url,
            title=title,
            description=description,
            architects=architects,
            location=location,
            images=images,
            publish_date=self._extract_publish_date(soup)
        )

    def _extract_id(self, url: str) -> str:
        """从URL提取ID"""
        # http://www.gooood.cn/project-name-12345.htm → 12345
        return url.split("-")[-1].replace(".htm", "")
```

#### 3.2.3 Dezeen Spider（国际设计网）

```python
class DezeenSpider(BaseSpider):
    """Dezeen爬虫（英文，国际案例）"""

    BASE_URL = "https://www.dezeen.com"

    def get_source_name(self) -> str:
        return "dezeen"

    def crawl_list_page(self, url: str) -> List[str]:
        """爬取列表页"""
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        # Dezeen特定选择器
        project_cards = soup.select("article.dezeen-article a.dezeen-article__link")

        return [link["href"] for link in project_cards]

    def crawl_project_page(self, url: str) -> UnifiedProjectData:
        """爬取项目详情"""
        response = self.session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.select_one("h1.article-title").get_text(strip=True)

        # 描述（英文，多段落）
        content_div = soup.select_one("div.article-body")
        paragraphs = content_div.find_all("p")
        description = "\n\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 20])

        # 建筑师（从byline提取）
        byline = soup.select_one("div.article-byline")
        architects = [byline.get_text(strip=True).replace("by ", "")] if byline else []

        # 图片
        images = []
        for img in soup.select("figure.article-image img"):
            images.append({
                "url": img["src"],
                "caption": img.get("alt", ""),
                "width": img.get("width"),
                "height": img.get("height")
            })

        return UnifiedProjectData(
            source="dezeen",
            source_id=self._extract_id(url),
            url=url,
            title=title,
            description=description,
            architects=architects,
            images=images,
            primary_category=self._extract_category(soup),
            publish_date=self._extract_publish_date(soup)
        )
```

#### 3.2.4 Architizer Spider（A+ Awards）

```python
class ArchitizerSpider(BaseSpider):
    """Architizer爬虫（获奖项目，高质量）"""

    BASE_URL = "https://architizer.com"

    def get_source_name(self) -> str:
        return "architizer"

    def crawl_list_page(self, url: str) -> List[str]:
        """爬取列表页"""
        # Architizer使用React SPA，需要Playwright或Selenium
        page = self.playwright_page
        page.goto(url)
        page.wait_for_selector("div.project-card")

        project_links = page.query_selector_all("div.project-card a")

        return [self.BASE_URL + link.get_attribute("href") for link in project_links]

    def crawl_project_page(self, url: str) -> UnifiedProjectData:
        """爬取项目详情"""
        page = self.playwright_page
        page.goto(url)
        page.wait_for_selector("div.project-details")

        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        # 提取数据（Architizer特定结构）
        title = soup.select_one("h1.project-title").get_text(strip=True)
        description = soup.select_one("div.project-description").get_text(strip=True)

        # 建筑师（多个）
        architect_divs = soup.select("div.firm-info")
        architects = [div.get_text(strip=True) for div in architect_divs]

        # 奖项信息（Architizer特色）
        awards = []
        award_badges = soup.select("div.award-badge")
        for badge in award_badges:
            awards.append({
                "name": badge.select_one("span.award-name").get_text(strip=True),
                "year": badge.select_one("span.award-year").get_text(strip=True),
                "category": badge.select_one("span.award-category").get_text(strip=True)
            })

        return UnifiedProjectData(
            source="architizer",
            source_id=self._extract_id(url),
            url=url,
            title=title,
            description=description,
            architects=architects,
            images=self._extract_images(soup),
            tags=self._extract_tags(soup),
            # 额外字段
            extra_data={
                "awards": awards,  # Architizer特有
                "firm_size": self._extract_firm_size(soup),
                "project_status": self._extract_status(soup)
            }
        )
```

---

### 3.3 爬虫管理器（统一调度）

```python
# intelligent_project_analyzer/crawlers/spider_manager.py

from typing import Dict, List, Type
from loguru import logger

class SpiderManager:
    """爬虫管理器（统一调度多个爬虫）"""

    def __init__(self):
        self.spiders: Dict[str, BaseSpider] = {}
        self._register_builtin_spiders()

    def _register_builtin_spiders(self):
        """注册内置爬虫"""
        self.register_spider("archdaily", ArchdailySpider)
        self.register_spider("gooood", GoooodSpider)
        self.register_spider("dezeen", DezeenSpider)
        self.register_spider("architizer", ArchitizerSpider)

    def register_spider(self, name: str, spider_class: Type[BaseSpider]):
        """注册爬虫"""
        config = CrawlerConfig(
            max_retries=3,
            request_delay=2.0,
            days_back=30
        )
        self.spiders[name] = spider_class(config)
        logger.info(f"✅ 注册爬虫: {name}")

    def crawl_all_sources(self, target_count: int = 10000) -> List[UnifiedProjectData]:
        """爬取所有数据源（智能分配）"""

        # 1. 计算每个源的配额
        quotas = self._calculate_quotas(target_count)

        all_projects = []

        # 2. 并发爬取
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}

            for source_name, quota in quotas.items():
                spider = self.spiders[source_name]
                future = executor.submit(
                    self._crawl_source,
                    spider,
                    quota
                )
                futures[future] = source_name

            # 3. 收集结果
            for future in as_completed(futures):
                source_name = futures[future]
                try:
                    projects = future.result()
                    all_projects.extend(projects)
                    logger.success(f"✅ {source_name}: {len(projects)} 个项目")
                except Exception as e:
                    logger.error(f"❌ {source_name} 失败: {e}")

        return all_projects

    def _calculate_quotas(self, target_count: int) -> Dict[str, int]:
        """智能分配爬取配额"""

        # 策略：按网站权重分配
        weights = {
            "archdaily": 0.35,   # 35% (中文+英文，高质量)
            "gooood": 0.25,      # 25% (中文，本土案例)
            "dezeen": 0.25,      # 25% (英文，国际案例)
            "architizer": 0.15   # 15% (获奖项目，高质量)
        }

        quotas = {}
        for source, weight in weights.items():
            quotas[source] = int(target_count * weight)

        logger.info(f"📊 配额分配: {quotas}")
        return quotas

    def _crawl_source(self, spider: BaseSpider, quota: int) -> List[UnifiedProjectData]:
        """爬取单个数据源"""

        source_name = spider.get_source_name()
        logger.info(f"🚀 开始爬取: {source_name} (目标: {quota})")

        projects = []

        # 获取分类列表
        categories = self._get_categories(source_name)

        # 平均分配到各分类
        per_category = quota // len(categories)

        for category_name, category_url in categories.items():
            try:
                category_projects = spider.crawl_category(
                    category_url,
                    max_pages=per_category // 20  # 假设每页20个项目
                )
                projects.extend(category_projects[:per_category])

                if len(projects) >= quota:
                    break

            except Exception as e:
                logger.error(f"❌ {source_name}/{category_name} 失败: {e}")
                continue

        logger.success(f"✅ {source_name} 完成: {len(projects)}/{quota}")
        return projects

    def _get_categories(self, source_name: str) -> Dict[str, str]:
        """获取数据源的分类列表"""

        # 从配置文件或数据库加载
        categories_config = {
            "archdaily": {
                "居住建筑": "https://www.archdaily.cn/search/cn/projects/categories/ju-zhu-jian-zhu",
                "文化建筑": "https://www.archdaily.cn/search/cn/projects/categories/wen-hua-jian-zhu",
                # ... 8个分类
            },
            "gooood": {
                "住宅": "http://www.gooood.cn/category/architecture/residential",
                "文化": "http://www.gooood.cn/category/architecture/cultural",
                # ...
            },
            "dezeen": {
                "Residential": "https://www.dezeen.com/architecture/residential/",
                "Cultural": "https://www.dezeen.com/architecture/cultural/",
                # ...
            },
            "architizer": {
                "Residential": "https://architizer.com/projects/category/residential/",
                "Cultural": "https://architizer.com/projects/category/cultural/",
                # ...
            }
        }

        return categories_config.get(source_name, {})
```

---

## 🗄️ 存储层设计（混合架构）

### 4.1 PostgreSQL（主数据库）

```sql
-- 项目表（核心）
CREATE TABLE projects (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,              -- archdaily/gooood/dezeen/architizer
    source_id VARCHAR(200) NOT NULL,           -- 网站内部ID
    url TEXT UNIQUE NOT NULL,                  -- 项目URL
    title TEXT NOT NULL,                       -- 标题
    description TEXT,                          -- 描述（核心，全文索引）
    description_vector VECTOR(1536),           -- 描述向量（OpenAI Embeddings）

    -- 元数据
    architects JSONB,                          -- [{name, firm, website}]
    location JSONB,                            -- {country, city, address, lat, lng}
    area_sqm DECIMAL(10, 2),                   -- 面积（统一为平方米）
    year INTEGER,                              -- 年份
    cost JSONB,                                -- {currency, amount}

    -- 分类
    primary_category VARCHAR(100),             -- 主分类
    sub_categories TEXT[],                     -- 子分类数组

    -- 社交数据
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,

    -- 质量评分
    quality_score DECIMAL(3, 2),               -- 0-1
    quality_factors JSONB,                     -- {description_length, image_count, ...}

    -- 时间戳
    publish_date TIMESTAMP,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- 索引
    INDEX idx_source (source),
    INDEX idx_publish_date (publish_date DESC),
    INDEX idx_year (year DESC),
    INDEX idx_location ((location->>'country'), (location->>'city')),
    INDEX idx_quality_score (quality_score DESC),
    INDEX idx_views (views DESC),

    -- 全文索引（PostgreSQL FTS）
    INDEX idx_description_fts USING GIN (to_tsvector('english', description)),

    -- 向量索引（pgvector，用于语义搜索）
    INDEX idx_description_vector USING ivfflat (description_vector vector_cosine_ops)
      WITH (lists = 100),

    -- 唯一约束
    CONSTRAINT unique_source_url UNIQUE (source, source_id)
);

-- 图片表
CREATE TABLE project_images (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    caption TEXT,
    width INTEGER,
    height INTEGER,
    file_size INTEGER,                         -- 字节
    storage_path TEXT,                         -- MinIO/S3路径
    order_index INTEGER DEFAULT 0,
    is_cover BOOLEAN DEFAULT FALSE,

    INDEX idx_project_id (project_id),
    INDEX idx_is_cover (is_cover)
);

-- 标签表（多对多）
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    name_en VARCHAR(100),                      -- 英文翻译
    category VARCHAR(50),                      -- 标签分类（material/style/function）
    usage_count INTEGER DEFAULT 0,

    INDEX idx_name (name),
    INDEX idx_usage_count (usage_count DESC)
);

CREATE TABLE project_tags (
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    confidence DECIMAL(3, 2) DEFAULT 1.0,       -- 标签置信度（LLM自动标注）

    PRIMARY KEY (project_id, tag_id),
    INDEX idx_tag_id (tag_id)
);

-- 建筑师表（独立管理）
CREATE TABLE architects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) UNIQUE NOT NULL,
    name_en VARCHAR(200),
    firm VARCHAR(200),
    country VARCHAR(100),
    website TEXT,
    bio TEXT,
    project_count INTEGER DEFAULT 0,
    total_views INTEGER DEFAULT 0,
    influence_score DECIMAL(5, 2),              -- 影响力评分

    INDEX idx_influence_score (influence_score DESC),
    INDEX idx_country (country)
);

CREATE TABLE project_architects (
    project_id BIGINT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    architect_id INTEGER NOT NULL REFERENCES architects(id) ON DELETE CASCADE,
    role VARCHAR(50),                           -- lead/partner/consultant

    PRIMARY KEY (project_id, architect_id)
);

-- 同步历史表
CREATE TABLE sync_history (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    category VARCHAR(100),
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(20) NOT NULL,                -- running/completed/failed
    projects_total INTEGER DEFAULT 0,
    projects_new INTEGER DEFAULT 0,
    projects_updated INTEGER DEFAULT 0,
    projects_failed INTEGER DEFAULT 0,
    error_message TEXT,

    INDEX idx_source_started (source, started_at DESC)
);

-- 数据质量监控表
CREATE TABLE quality_issues (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT REFERENCES projects(id) ON DELETE CASCADE,
    issue_type VARCHAR(50) NOT NULL,            -- missing_description/low_quality/...
    severity VARCHAR(20) NOT NULL,              -- low/medium/high/critical
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,

    INDEX idx_project_id (project_id),
    INDEX idx_issue_type (issue_type),
    INDEX idx_severity (severity)
);
```

---

### 4.2 MongoDB（原始数据+灵活字段）

```javascript
// projects_raw collection（原始爬取数据）
{
  _id: ObjectId("..."),
  source: "archdaily",
  source_id: "1037243",
  url: "https://www.archdaily.cn/cn/1037243/...",

  // 原始HTML（用于重新解析）
  raw_html: "<!DOCTYPE html>...",
  raw_html_compressed: BinData,  // gzip压缩

  // 原始提取数据（未标准化）
  raw_data: {
    title: "伊丹十三纪念馆 / Itm Yooehwa Architects",
    description: "这座艺术博物馆...",
    architects: "Itm Yooehwa Architects",  // 原始字符串
    location: "济州市,韩国",
    area: "674m²",
    year: "2022 年",
    images: [...],
    tags: [...]
  },

  // 网站特定字段（不同网站不同）
  site_specific: {
    // Archdaily特有
    archdaily_views: 18,
    archdaily_saves: 5,

    // 或 Architizer特有
    awards: [...],
    firm_size: "1-10 employees",

    // 或 Dezeen特有
    editor_picks: true,
    featured: false
  },

  // 爬取元信息
  crawl_metadata: {
    crawled_at: ISODate("2026-02-17T16:50:00Z"),
    crawler_version: "v8.120.0",
    parse_version: "v1.0",
    parse_errors: [],
    retry_count: 0
  },

  // 处理状态
  processing: {
    normalized: true,          // 是否已标准化到PostgreSQL
    normalized_at: ISODate("2026-02-17T17:00:00Z"),
    vectorized: true,          // 是否已向量化
    vectorized_at: ISODate("2026-02-17T17:05:00Z"),
    indexed: true              // 是否已索引到ES
  }
}

// 索引
db.projects_raw.createIndex({ "source": 1, "source_id": 1 }, { unique: true })
db.projects_raw.createIndex({ "url": 1 }, { unique: true })
db.projects_raw.createIndex({ "crawl_metadata.crawled_at": -1 })
db.projects_raw.createIndex({ "processing.normalized": 1 })
```

---

### 4.3 Redis（缓存+去重）

```python
# 去重集合（URL哈希）
# Key: crawl:seen_urls:{source}
# Type: Set
# TTL: 30天
redis.sadd("crawl:seen_urls:archdaily", url_hash)

# 分布式锁（防止重复爬取）
# Key: lock:crawl:{source}:{source_id}
# Type: String
# TTL: 10分钟
redis.set("lock:crawl:archdaily:1037243", "worker-1", ex=600, nx=True)

# 任务队列（Celery）
# Key: celery:queue:crawl_projects
# Type: List
redis.lpush("celery:queue:crawl_projects", json.dumps({
    "source": "archdaily",
    "url": "https://..."
}))

# 热点数据缓存（项目详情）
# Key: cache:project:{id}
# Type: Hash
# TTL: 1小时
redis.hset("cache:project:1037243", mapping={
    "title": "...",
    "description": "...",
    "architects": "...",
    # ...
})
redis.expire("cache:project:1037243", 3600)

# 统计缓存（降低DB压力）
# Key: stats:daily:{date}
# Type: Hash
redis.hincrby("stats:daily:2026-02-17", "projects_crawled", 1)
redis.hincrby("stats:daily:2026-02-17", f"{source}_count", 1)
```

---

### 4.4 Elasticsearch（全文搜索）

```json
// projects index（全文搜索优化）
{
  "mappings": {
    "properties": {
      "id": { "type": "long" },
      "source": { "type": "keyword" },
      "url": { "type": "keyword" },

      "title": {
        "type": "text",
        "fields": {
          "keyword": { "type": "keyword" },
          "en": { "analyzer": "english" },
          "zh": { "analyzer": "ik_max_word" }
        }
      },

      "description": {
        "type": "text",
        "fields": {
          "en": { "analyzer": "english" },
          "zh": { "analyzer": "ik_max_word" }
        },
        "term_vector": "with_positions_offsets"
      },

      "architects": {
        "type": "nested",
        "properties": {
          "name": { "type": "text" },
          "firm": { "type": "text" }
        }
      },

      "location": {
        "properties": {
          "country": { "type": "keyword" },
          "city": { "type": "keyword" },
          "coordinates": { "type": "geo_point" }
        }
      },

      "tags": { "type": "keyword" },
      "primary_category": { "type": "keyword" },
      "year": { "type": "integer" },
      "quality_score": { "type": "float" },
      "views": { "type": "integer" },
      "publish_date": { "type": "date" }
    }
  },

  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "analysis": {
      "analyzer": {
        "ik_max_word": {
          "type": "custom",
          "tokenizer": "ik_max_word"
        }
      }
    }
  }
}
```

---

## ⏰ 调度层设计（自动同步）

### 5.1 分布式任务队列（Celery + Redis）

```python
# intelligent_project_analyzer/tasks/crawl_tasks.py

from celery import Celery, Task
from celery.schedules import crontab
from kombu import Queue
import logging

# 创建Celery应用
app = Celery(
    'external_data_crawler',
    broker='redis://localhost:6379/1',
    backend='redis://localhost:6379/2'
)

# 配置
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,

    # 任务队列（按优先级）
    task_routes={
        'tasks.crawl_category': {'queue': 'crawl'},
        'tasks.crawl_project_detail': {'queue': 'detail'},
        'tasks.process_images': {'queue': 'media'},
        'tasks.vectorize_descriptions': {'queue': 'ml'},
    },

    # 并发控制
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,

    # 重试策略
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # 定时任务
    beat_schedule={
        # 每天凌晨2点同步Archdaily
        'sync-archdaily-daily': {
            'task': 'tasks.sync_source',
            'schedule': crontab(hour=2, minute=0),
            'args': ('archdaily',),
            'kwargs': {'mode': 'incremental'}
        },

        # 每天凌晨3点同步Gooood
        'sync-gooood-daily': {
            'task': 'tasks.sync_source',
            'schedule': crontab(hour=3, minute=0),
            'args': ('gooood',),
            'kwargs': {'mode': 'incremental'}
        },

        # 每周一凌晨4点全量同步Dezeen
        'sync-dezeen-weekly': {
            'task': 'tasks.sync_source',
            'schedule': crontab(hour=4, minute=0, day_of_week=1),
            'args': ('dezeen',),
            'kwargs': {'mode': 'full'}
        },

        # 每小时检查数据质量
        'check-quality-hourly': {
            'task': 'tasks.check_data_quality',
            'schedule': crontab(minute=0),
        },

        # 每天凌晨5点更新向量索引
        'update-vectors-daily': {
            'task': 'tasks.update_vector_index',
            'schedule': crontab(hour=5, minute=0),
        },

        # 每周统计报告
        'weekly-stats-report': {
            'task': 'tasks.generate_weekly_report',
            'schedule': crontab(hour=9, minute=0, day_of_week=1),
        }
    }
)


@app.task(bind=True, max_retries=3, default_retry_delay=300)
def sync_source(self, source: str, mode: str = 'incremental'):
    """同步单个数据源"""

    logger.info(f"🚀 开始同步: {source} (模式: {mode})")

    try:
        # 1. 记录同步开始
        sync_record = SyncHistory.create(
            source=source,
            status='running'
        )

        # 2. 获取爬虫
        spider = SpiderManager().get_spider(source)

        # 3. 确定爬取范围
        if mode == 'incremental':
            # 增量：只爬取最近30天
            spider.config.days_back = 30
            target_count = 500
        else:
            # 全量：爬取所有
            spider.config.days_back = 365 * 5  # 5年
            target_count = 5000

        # 4. 执行爬取
        projects = spider.crawl_all(target_count=target_count)

        # 5. 保存数据
        stats = save_projects_batch(projects, source)

        # 6. 更新同步记录
        sync_record.update(
            status='completed',
            projects_total=len(projects),
            projects_new=stats['new'],
            projects_updated=stats['updated'],
            projects_failed=stats['failed']
        )

        logger.success(f"✅ 同步完成: {source} - {stats}")
        return stats

    except Exception as e:
        # 记录错误
        sync_record.update(
            status='failed',
            error_message=str(e)
        )

        logger.error(f"❌ 同步失败: {source} - {e}")

        # 重试
        raise self.retry(exc=e)


@app.task
def crawl_project_detail(url: str, source: str):
    """爬取单个项目详情（并行任务）"""

    spider = SpiderManager().get_spider(source)

    try:
        project = spider.crawl_project_page(url)
        save_project(project)
        return {"success": True, "url": url}

    except Exception as e:
        logger.error(f"❌ 爬取失败: {url} - {e}")
        return {"success": False, "url": url, "error": str(e)}


@app.task(rate_limit='100/m')  # 限速：每分钟100个
def vectorize_description(project_id: int):
    """向量化项目描述（ML任务）"""

    from intelligent_project_analyzer.ml.embeddings import OpenAIEmbedder

    project = get_project(project_id)

    if not project.description:
        logger.warning(f"⚠️ 项目无描述: {project_id}")
        return {"success": False, "reason": "no_description"}

    embedder = OpenAIEmbedder()
    vector = embedder.embed(project.description)

    # 保存向量到PostgreSQL
    update_project_vector(project_id, vector)

    logger.info(f"✅ 向量化完成: {project_id}")
    return {"success": True, "project_id": project_id}


@app.task
def check_data_quality():
    """数据质量检查"""

    issues = []

    # 1. 检查缺失描述
    missing_desc = db.query(Project).filter(
        Project.description.is_(None)
    ).count()

    if missing_desc > 0:
        issues.append({
            "type": "missing_description",
            "count": missing_desc,
            "severity": "high"
        })

    # 2. 检查低质量描述（<100字符）
    low_quality = db.query(Project).filter(
        func.length(Project.description) < 100
    ).count()

    if low_quality > 0:
        issues.append({
            "type": "low_quality_description",
            "count": low_quality,
            "severity": "medium"
        })

    # 3. 检查缺失图片
    missing_images = db.query(Project).outerjoin(ProjectImage).filter(
        ProjectImage.id.is_(None)
    ).count()

    # 4. 发送告警（如果有问题）
    if issues:
        send_alert_email(issues)

    logger.info(f"📊 质量检查: {len(issues)} 个问题")
    return issues
```

---

### 5.2 启动服务

```bash
# 启动Celery Worker（爬虫队列）
celery -A intelligent_project_analyzer.tasks.crawl_tasks worker \
  --loglevel=info \
  --queues=crawl,detail \
  --concurrency=4 \
  --max-tasks-per-child=1000 \
  --hostname=crawler-worker@%h

# 启动Celery Worker（ML队列）
celery -A intelligent_project_analyzer.tasks.crawl_tasks worker \
  --loglevel=info \
  --queues=ml \
  --concurrency=2 \
  --hostname=ml-worker@%h

# 启动Celery Beat（定时调度）
celery -A intelligent_project_analyzer.tasks.crawl_tasks beat \
  --loglevel=info

# 启动Flower（监控界面）
celery -A intelligent_project_analyzer.tasks.crawl_tasks flower \
  --port=5555
```

访问监控面板：http://localhost:5555

---

## 🔍 索引层设计（多模态）

### 6.1 向量索引（Qdrant + OpenAI Embeddings）

```python
# intelligent_project_analyzer/ml/vector_index.py

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import OpenAI
from typing import List, Dict, Any

class VectorIndexManager:
    """向量索引管理器（语义搜索）"""

    def __init__(self):
        self.qdrant = QdrantClient(host="localhost", port=6333)
        self.openai = OpenAI()
        self.collection_name = "projects"

        # 创建集合
        self._create_collection()

    def _create_collection(self):
        """创建向量集合"""
        try:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=1536,  # OpenAI text-embedding-3-small
                    distance=Distance.COSINE
                )
            )
            logger.success("✅ 创建向量集合")
        except Exception:
            logger.info("向量集合已存在")

    def embed_text(self, text: str) -> List[float]:
        """文本向量化"""
        response = self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    def index_project(self, project: UnifiedProjectData):
        """索引单个项目"""

        # 1. 构建搜索文本（多字段融合）
        search_text = f"""
        {project.title}

        {project.description}

        建筑师：{', '.join(project.architects or [])}
        位置：{project.location.get('city', '')} {project.location.get('country', '')}
        标签：{', '.join(project.tags or [])}
        """

        # 2. 向量化
        vector = self.embed_text(search_text)

        # 3. 构建负载（元数据）
        payload = {
            "id": project.source_id,
            "source": project.source,
            "url": project.url,
            "title": project.title,
            "architects": project.architects,
            "location": project.location,
            "primary_category": project.primary_category,
            "tags": project.tags,
            "year": project.year,
            "quality_score": project.quality_score,
            "views": project.views
        }

        # 4. 插入Qdrant
        self.qdrant.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=self._generate_id(project),
                    vector=vector,
                    payload=payload
                )
            ]
        )

    def search(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """语义搜索"""

        # 1. 向量化查询
        query_vector = self.embed_text(query)

        # 2. 构建过滤条件（可选）
        query_filter = None
        if filters:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            conditions = []

            if "source" in filters:
                conditions.append(
                    FieldCondition(key="source", match=MatchValue(value=filters["source"]))
                )

            if "year_range" in filters:
                from qdrant_client.models import Range
                conditions.append(
                    FieldCondition(key="year", range=Range(
                        gte=filters["year_range"][0],
                        lte=filters["year_range"][1]
                    ))
                )

            if conditions:
                query_filter = Filter(must=conditions)

        # 3. 搜索
        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=top_k
        )

        # 4. 格式化结果
        return [
            {
                "id": hit.id,
                "score": hit.score,
                **hit.payload
            }
            for hit in results
        ]
```

---

### 6.2 全文索引（Elasticsearch）

```python
# intelligent_project_analyzer/search/elasticsearch_manager.py

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from typing import List, Dict, Any

class ElasticsearchManager:
    """全文搜索管理器"""

    def __init__(self):
        self.es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
        self.index_name = "projects"

        # 创建索引
        self._create_index()

    def _create_index(self):
        """创建索引（带中英文分词器）"""

        mapping = {
            "settings": {
                "number_of_shards": 3,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "ik_max_word": {
                            "type": "custom",
                            "tokenizer": "ik_max_word"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "id": {"type": "long"},
                    "source": {"type": "keyword"},
                    "url": {"type": "keyword"},

                    "title": {
                        "type": "text",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "zh": {"type": "text", "analyzer": "ik_max_word"},
                            "en": {"type": "text", "analyzer": "english"}
                        }
                    },

                    "description": {
                        "type": "text",
                        "fields": {
                            "zh": {"type": "text", "analyzer": "ik_max_word"},
                            "en": {"type": "text", "analyzer": "english"}
                        }
                    },

                    "architects": {"type": "text", "analyzer": "ik_max_word"},
                    "location": {
                        "properties": {
                            "country": {"type": "keyword"},
                            "city": {"type": "keyword"}
                        }
                    },

                    "tags": {"type": "keyword"},
                    "primary_category": {"type": "keyword"},
                    "year": {"type": "integer"},
                    "quality_score": {"type": "float"},
                    "publish_date": {"type": "date"}
                }
            }
        }

        if not self.es.indices.exists(index=self.index_name):
            self.es.indices.create(index=self.index_name, body=mapping)
            logger.success("✅ 创建ES索引")

    def index_project(self, project: UnifiedProjectData):
        """索引单个项目"""

        doc = {
            "id": project.source_id,
            "source": project.source,
            "url": project.url,
            "title": project.title,
            "description": project.description,
            "architects": project.architects,
            "location": project.location,
            "tags": project.tags,
            "primary_category": project.primary_category,
            "year": project.year,
            "quality_score": project.quality_score,
            "publish_date": project.publish_date
        }

        self.es.index(
            index=self.index_name,
            id=f"{project.source}_{project.source_id}",
            body=doc
        )

    def search(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        size: int = 20
    ) -> List[Dict[str, Any]]:
        """全文搜索（支持中英文）"""

        # 1. 构建查询
        must_clauses = [
            {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title.zh^3",      # 标题中文，权重3
                        "title.en^3",      # 标题英文，权重3
                        "description.zh^2", # 描述中文，权重2
                        "description.en^2", # 描述英文，权重2
                        "architects^1"      # 建筑师，权重1
                    ],
                    "type": "best_fields"
                }
            }
        ]

        # 2. 添加过滤条件
        filter_clauses = []

        if filters:
            if "source" in filters:
                filter_clauses.append({"term": {"source": filters["source"]}})

            if "category" in filters:
                filter_clauses.append({"term": {"primary_category": filters["category"]}})

            if "year_range" in filters:
                filter_clauses.append({
                    "range": {
                        "year": {
                            "gte": filters["year_range"][0],
                            "lte": filters["year_range"][1]
                        }
                    }
                })

        # 3. 执行搜索
        body = {
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": filter_clauses
                }
            },
            "size": size,
            "highlight": {
                "fields": {
                    "description.zh": {},
                    "description.en": {}
                }
            }
        }

        results = self.es.search(index=self.index_name, body=body)

        # 4. 格式化结果
        return [
            {
                "id": hit["_id"],
                "score": hit["_score"],
                "highlight": hit.get("highlight", {}),
                **hit["_source"]
            }
            for hit in results["hits"]["hits"]
        ]
```

---

## 🎯 应用层设计（多角度利用）

### 7.1 应用场景总览

| 应用 | 使用场景 | 数据来源 | 技术栈 | 优先级 |
|------|---------|---------|--------|--------|
| **1. 语义搜索** | 用户问："找相似的博物馆设计" | 向量索引 | Qdrant + OpenAI | ⭐⭐⭐⭐⭐ |
| **2. 案例推荐** | 查看项目A → 推荐相似项目B/C | 协同过滤 + 向量 | Surprise + Qdrant | ⭐⭐⭐⭐ |
| **3. LLM增强** | 设计建议时引用真实案例 | PostgreSQL | LangChain | ⭐⭐⭐⭐⭐ |
| **4. 趋势分析** | "2024年最流行的材料是什么？" | 时序数据 | Pandas + Plotly | ⭐⭐⭐ |
| **5. 建筑师排名** | "影响力最大的10位建筑师" | 图数据库 | Neo4j | ⭐⭐⭐ |
| **6. 地域热图** | "全球项目分布热力图" | 地理数据 | Mapbox | ⭐⭐ |
| **7. 概念图生成** | 基于案例生成视觉参考 | 图片+描述 | DALL·E 3 | ⭐⭐⭐⭐ |
| **8. 智能问答** | "这个设计的创新点是什么？" | RAG | LangChain + pgvector | ⭐⭐⭐⭐ |
| **9. 自动标注** | 为项目智能打标签 | 分类模型 | OpenAI | ⭐⭐⭐ |
| **10. 质量评分** | 评估项目数据质量 | 规则引擎 | Python | ⭐⭐⭐ |

---

### 7.2 应用1：语义搜索API

```python
# intelligent_project_analyzer/api/external_search.py

from fastapi import APIRouter, Query
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/external/search", tags=["外部数据搜索"])

class SearchRequest(BaseModel):
    """搜索请求"""
    query: str                                    # 查询文本
    sources: Optional[List[str]] = None           # 数据源过滤
    categories: Optional[List[str]] = None        # 分类过滤
    year_range: Optional[List[int]] = None        # 年份范围
    location: Optional[str] = None                # 位置过滤
    min_quality: Optional[float] = 0.0            # 最低质量分
    top_k: int = 10                               # 返回数量
    mode: str = "semantic"                        # semantic/fulltext/hybrid

class SearchResult(BaseModel):
    """搜索结果"""
    id: str
    source: str
    url: str
    title: str
    description: str
    architects: List[str]
    location: dict
    images: List[str]
    tags: List[str]
    score: float                                  # 相似度分数
    highlight: Optional[dict] = None              # 高亮片段

@router.post("/", response_model=List[SearchResult])
async def search_projects(request: SearchRequest):
    """
    🔍 外部项目语义搜索

    支持3种搜索模式：
    - semantic: 语义相似度（向量搜索）
    - fulltext: 全文匹配（关键词）
    - hybrid: 混合模式（语义+全文）
    """

    # 1. 构建过滤条件
    filters = {}
    if request.sources:
        filters["source"] = request.sources
    if request.year_range:
        filters["year_range"] = request.year_range
    if request.location:
        filters["location"] = request.location

    # 2. 执行搜索
    if request.mode == "semantic":
        # 语义搜索（Qdrant）
        vector_manager = VectorIndexManager()
        results = vector_manager.search(
            query=request.query,
            filters=filters,
            top_k=request.top_k
        )

    elif request.mode == "fulltext":
        # 全文搜索（Elasticsearch）
        es_manager = ElasticsearchManager()
        results = es_manager.search(
            query=request.query,
            filters=filters,
            size=request.top_k
        )

    elif request.mode == "hybrid":
        # 混合搜索（RRF融合）
        vector_results = vector_manager.search(request.query, filters, top_k=20)
        fulltext_results = es_manager.search(request.query, filters, size=20)

        # Reciprocal Rank Fusion（互惠排名融合）
        results = reciprocal_rank_fusion(vector_results, fulltext_results, k=60)
        results = results[:request.top_k]

    # 3. 过滤低质量结果
    if request.min_quality > 0:
        results = [r for r in results if r.get("quality_score", 0) >= request.min_quality]

    # 4. 补充完整信息（从PostgreSQL）
    enriched_results = []
    for result in results:
        project = get_project_by_id(result["id"])
        enriched_results.append(SearchResult(
            id=project.id,
            source=project.source,
            url=project.url,
            title=project.title,
            description=project.description[:500],  # 截断
            architects=project.architects,
            location=project.location,
            images=[img.url for img in project.images[:3]],  # 前3张
            tags=project.tags,
            score=result["score"],
            highlight=result.get("highlight")
        ))

    return enriched_results


def reciprocal_rank_fusion(
    results1: List[dict],
    results2: List[dict],
    k: int = 60
) -> List[dict]:
    """
    互惠排名融合（RRF）

    公式：RRF(d) = Σ 1 / (k + rank_i(d))
    """
    scores = {}

    # 计算RRF分数
    for rank, result in enumerate(results1, start=1):
        doc_id = result["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)

    for rank, result in enumerate(results2, start=1):
        doc_id = result["id"]
        scores[doc_id] = scores.get(doc_id, 0) + 1 / (k + rank)

    # 合并结果（保留所有元数据）
    all_results = {r["id"]: r for r in results1 + results2}

    # 按RRF分数排序
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return [
        {**all_results[doc_id], "score": score}
        for doc_id, score in ranked
    ]
```

---

### 7.3 应用2：智能推荐引擎

```python
# intelligent_project_analyzer/recommendation/engine.py

from typing import List, Dict, Any
from collections import defaultdict
import numpy as np

class ProjectRecommendationEngine:
    """项目推荐引擎（多策略融合）"""

    def __init__(self):
        self.strategies = [
            CollaborativeFilteringStrategy(),    # 协同过滤
            ContentBasedStrategy(),               # 内容推荐
            PopularityBasedStrategy(),            # 热度推荐
            DiversityStrategy()                   # 多样性推荐
        ]

    def recommend(
        self,
        project_id: int,
        user_preferences: Dict[str, Any] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        为项目推荐相似案例

        Args:
            project_id: 当前项目ID
            user_preferences: 用户偏好（可选）
            top_k: 返回数量

        Returns:
            推荐结果列表
        """

        # 1. 获取当前项目
        current_project = get_project(project_id)

        # 2. 多策略推荐
        all_candidates = []

        for strategy in self.strategies:
            candidates = strategy.recommend(
                current_project,
                user_preferences,
                top_k=50  # 每个策略返回50个候选
            )
            all_candidates.extend(candidates)

        # 3. 去重+融合
        final_results = self._merge_and_rank(all_candidates, top_k)

        # 4. 多样性重排（避免Over-Specialization）
        final_results = self._diversify(final_results, current_project)

        return final_results[:top_k]

    def _merge_and_rank(
        self,
        candidates: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """融合多个策略的结果"""

        # 按project_id分组，累加分数
        scores = defaultdict(lambda: {"score": 0.0, "count": 0, "data": None})

        for candidate in candidates:
            pid = candidate["project_id"]
            scores[pid]["score"] += candidate["score"]
            scores[pid]["count"] += 1
            if not scores[pid]["data"]:
                scores[pid]["data"] = candidate

        # 计算平均分数（+策略数量加权）
        for pid in scores:
            scores[pid]["final_score"] = (
                scores[pid]["score"] / scores[pid]["count"] *
                np.log(1 + scores[pid]["count"])  # 多个策略都推荐的项目加权
            )

        # 排序
        ranked = sorted(
            scores.values(),
            key=lambda x: x["final_score"],
            reverse=True
        )

        return [item["data"] for item in ranked]

    def _diversify(
        self,
        results: List[Dict[str, Any]],
        anchor_project: Project
    ) -> List[Dict[str, Any]]:
        """多样性重排（MMR算法）"""

        # Maximal Marginal Relevance
        # 在保持相关性的同时，增加多样性

        selected = [results[0]]  # 第一个（最相关）
        remaining = results[1:]

        while remaining and len(selected) < len(results):
            # 计算与已选项目的最小相似度
            max_mmr = -float('inf')
            best_idx = 0

            for i, candidate in enumerate(remaining):
                relevance = candidate["score"]

                # 与已选项目的最大相似度
                max_similarity = max([
                    self._similarity(candidate, selected_proj)
                    for selected_proj in selected
                ])

                # MMR = λ * Relevance - (1-λ) * Similarity
                mmr = 0.7 * relevance - 0.3 * max_similarity

                if mmr > max_mmr:
                    max_mmr = mmr
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected


class CollaborativeFilteringStrategy:
    """协同过滤策略（用户行为）"""

    def recommend(self, project, user_preferences, top_k):
        """
        基于用户行为：
        - 看过项目A的用户还看过项目B/C/D
        """

        # 从用户行为日志中查询
        # SELECT project_id, COUNT(*) as co_views
        # FROM user_views
        # WHERE user_id IN (
        #   SELECT user_id FROM user_views WHERE project_id = ?
        # ) AND project_id != ?
        # GROUP BY project_id
        # ORDER BY co_views DESC
        # LIMIT ?

        pass


class ContentBasedStrategy:
    """内容推荐策略（相似度）"""

    def recommend(self, project, user_preferences, top_k):
        """
        基于内容相似度：
        1. 语义相似（description向量）
        2. 标签重叠（tags Jaccard）
        3. 建筑师相同
        4. 地域相近
        """

        candidates = []

        # 1. 语义相似
        vector_manager = VectorIndexManager()
        semantic_results = vector_manager.search(
            query=project.description,
            filters={"source": project.source},  # 同源优先
            top_k=top_k * 2
        )

        for result in semantic_results:
            candidates.append({
                "project_id": result["id"],
                "score": result["score"] * 1.0,  # 权重1.0
                "reason": "语义相似"
            })

        # 2. 相同建筑师
        if project.architects:
            same_architect_projects = db.query(Project).filter(
                Project.architects.overlap(project.architects),
                Project.id != project.id
            ).limit(top_k).all()

            for proj in same_architect_projects:
                candidates.append({
                    "project_id": proj.id,
                    "score": 0.8,  # 权重0.8
                    "reason": "相同建筑师"
                })

        # 3. 相似标签（Jaccard系数）
        if project.tags:
            tag_similar = db.query(Project).join(ProjectTag).filter(
                ProjectTag.tag_id.in_(project.tag_ids),
                Project.id != project.id
            ).all()

            for proj in tag_similar:
                jaccard = len(set(proj.tags) & set(project.tags)) / len(set(proj.tags) | set(project.tags))
                candidates.append({
                    "project_id": proj.id,
                    "score": jaccard * 0.6,  # 权重0.6
                    "reason": "标签相似"
                })

        return candidates
```

---

### 7.4 应用3：LLM上下文增强（RAG）

```python
# intelligent_project_analyzer/rag/context_provider.py

from typing import List, Dict, Any
from langchain.schema import Document

class ExternalContextProvider:
    """外部数据上下文提供器（RAG）"""

    def __init__(self):
        self.vector_manager = VectorIndexManager()
        self.es_manager = ElasticsearchManager()

    def get_context_for_query(
        self,
        user_query: str,
        user_requirements: Dict[str, Any],
        top_k: int = 3
    ) -> List[Document]:
        """
        为用户查询获取相关案例上下文

        使用场景：
        - 用户问："如何设计适合济州岛气候的博物馆？"
        - 系统查询外部数据库 → 伊丹十三纪念馆
        - 作为Few-Shot示例传递给LLM
        """

        # 1. 提取关键信息
        location = user_requirements.get("location", "")
        project_type = user_requirements.get("project_type", "")
        scale = user_requirements.get("scale", "")

        # 2. 构建搜索查询
        search_query = f"{user_query} {location} {project_type}"

        # 3. 语义搜索
        results = self.vector_manager.search(
            query=search_query,
            filters={
                "primary_category": project_type if project_type else None,
                "location": location if location else None
            },
            top_k=top_k
        )

        # 4. 格式化为LangChain Document
        documents = []

        for result in results:
            # 获取完整项目数据
            project = get_project_by_id(result["id"])

            # 构建Document
            content = f"""
## 参考案例：{project.title}

**建筑师**: {', '.join(project.architects or [])}
**位置**: {project.location.get('city', '')}, {project.location.get('country', '')}
**面积**: {project.area_sqm} m²
**年份**: {project.year}
**类型**: {project.primary_category}

**设计理念**:
{project.description}

**关键设计手法**:
{self._extract_design_strategies(project)}

**材料与技术**:
{self._extract_materials(project)}

**环境适应**:
{self._extract_environmental_strategies(project)}

**图片**: {len(project.images)} 张
**浏览量**: {project.views}
**质量评分**: {project.quality_score:.2f}/1.0

来源: {project.url}
"""

            documents.append(Document(
                page_content=content,
                metadata={
                    "source": project.source,
                    "project_id": project.id,
                    "url": project.url,
                    "relevance_score": result["score"],
                    "architects": project.architects,
                    "location": project.location,
                    "year": project.year
                }
            ))

        return documents

    def _extract_design_strategies(self, project: Project) -> str:
        """从描述中提取设计策略"""

        # 使用LLM提取关键设计手法
        prompt = f"""
从以下项目描述中提取3-5个关键设计策略（简洁的要点）：

{project.description}

格式：
- 策略1
- 策略2
- 策略3
"""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )

        return response.choices[0].message.content

    def _extract_materials(self, project: Project) -> str:
        """提取材料信息"""

        # 从描述中提取材料关键词
        materials = []

        material_keywords = [
            "混凝土", "concrete", "木材", "wood", "玻璃", "glass",
            "钢", "steel", "石材", "stone", "砖", "brick"
        ]

        for keyword in material_keywords:
            if keyword in project.description.lower():
                materials.append(keyword)

        return ", ".join(materials) if materials else "未明确说明"
```

---

### 7.5 应用4：趋势分析仪表板

```python
# intelligent_project_analyzer/analytics/trend_analyzer.py

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any

class TrendAnalyzer:
    """趋势分析器"""

    def analyze_design_trends(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        分析设计趋势

        返回：
        - 最流行的标签/风格
        - 材料使用趋势
        - 地域热点
        - 建筑师排名
        """

        # 1. 最流行的标签
        popular_tags = db.query(
            Tag.name,
            func.count(ProjectTag.project_id).label("count")
        ).join(ProjectTag).join(Project).filter(
            Project.publish_date.between(start_date, end_date)
        ).group_by(Tag.name).order_by("count desc").limit(20).all()

        # 2. 材料趋势（从描述中提取）
        materials = self._extract_material_trends(start_date, end_date)

        # 3. 地域热点
        location_stats = db.query(
            Project.location["country"].label("country"),
            func.count(Project.id).label("count")
        ).filter(
            Project.publish_date.between(start_date, end_date)
        ).group_by("country").order_by("count desc").limit(20).all()

        # 4. 建筑师排名（按影响力）
        top_architects = db.query(
            Architect.name,
            Architect.influence_score,
            func.count(ProjectArchitect.project_id).label("project_count"),
            func.sum(Project.views).label("total_views")
        ).join(ProjectArchitect).join(Project).filter(
            Project.publish_date.between(start_date, end_date)
        ).group_by(Architect.id).order_by("influence_score desc").limit(20).all()

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "popular_tags": [
                {"name": tag.name, "count": tag.count}
                for tag in popular_tags
            ],
            "materials": materials,
            "location_hotspots": [
                {"country": loc.country, "count": loc.count}
                for loc in location_stats
            ],
            "top_architects": [
                {
                    "name": arch.name,
                    "influence_score": float(arch.influence_score),
                    "project_count": arch.project_count,
                    "total_views": arch.total_views
                }
                for arch in top_architects
            ]
        }

    def predict_future_trends(self, months_ahead: int = 6) -> Dict[str, Any]:
        """
        预测未来趋势（时序分析）

        使用Prophet或ARIMA模型
        """

        # 1. 获取历史数据
        historical_data = self._get_historical_tag_usage()

        # 2. 时序预测（Prophet）
        from prophet import Prophet

        predictions = {}

        for tag_name, time_series in historical_data.items():
            df = pd.DataFrame({
                "ds": time_series["dates"],
                "y": time_series["counts"]
            })

            model = Prophet()
            model.fit(df)

            future = model.make_future_dataframe(periods=months_ahead, freq="M")
            forecast = model.predict(future)

            predictions[tag_name] = {
                "current": time_series["counts"][-1],
                "predicted": forecast["yhat"].iloc[-1],
                "trend": "上升" if forecast["trend"].iloc[-1] > 0 else "下降"
            }

        return predictions
```

---

## 📊 监控与运维

### 8.1 监控指标

```python
# intelligent_project_analyzer/monitoring/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# 爬虫指标
crawl_requests_total = Counter(
    'crawl_requests_total',
    'Total spider requests',
    ['source', 'status']
)

crawl_duration_seconds = Histogram(
    'crawl_duration_seconds',
    'Spider crawl duration',
    ['source']
)

# 数据指标
projects_total = Gauge(
    'projects_total',
    'Total projects in database',
    ['source']
)

projects_quality_score = Histogram(
    'projects_quality_score',
    'Project quality score distribution',
    ['source']
)

# API指标
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status']
)

api_latency_seconds = Histogram(
    'api_latency_seconds',
    'API request latency',
    ['endpoint']
)
```

---

### 8.2 告警规则（Prometheus + Alertmanager）

```yaml
# prometheus/alerts.yml

groups:
  - name: external_data_alerts
    rules:
      # 爬虫失败率告警
      - alert: HighCrawlFailureRate
        expr: |
          (
            sum(rate(crawl_requests_total{status="failed"}[5m])) by (source) /
            sum(rate(crawl_requests_total[5m])) by (source)
          ) > 0.1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "{{ $labels.source }} 爬虫失败率过高"
          description: "失败率: {{ $value | humanizePercentage }}"

      # 数据质量告警
      - alert: LowDataQuality
        expr: |
          avg(projects_quality_score{source="archdaily"}) < 0.6
        for: 1h
        labels:
          severity: critical
        annotations:
          summary: "数据质量下降"
          description: "平均质量分: {{ $value }}"

      # 同步延迟告警
      - alert: SyncDelayed
        expr: |
          time() - max(sync_history_completed_at) > 86400
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "数据同步延迟超过24小时"
```

---

## 🚀 实施路线图

### Phase 1: 基础设施（2周）
- [ ] PostgreSQL + pgvector安装配置
- [ ] Redis + Celery部署
- [ ] Qdrant向量数据库部署
- [ ] Elasticsearch部署（可选）
- [ ] 监控系统（Prometheus + Grafana）

### Phase 2: 爬虫框架（2周）
- [ ] 统一爬虫接口（BaseSpider）
- [ ] Archdaily Spider完善
- [ ] Gooood Spider开发
- [ ] Dezeen Spider开发
- [ ] 爬虫管理器（SpiderManager）

### Phase 3: 数据处理（2周）
- [ ] 数据标准化Pipeline
- [ ] 向量化Pipeline（OpenAI Embeddings）
- [ ] 质量评分引擎
- [ ] 自动标注系统

### Phase 4: 索引层（1周）
- [ ] 向量索引（Qdrant）
- [ ] 全文索引（Elasticsearch）
- [ ] PostgreSQL FTS配置

### Phase 5: 应用层（3周）
- [ ] 语义搜索API
- [ ] 推荐引擎
- [ ] LLM上下文提供器（RAG）
- [ ] 趋势分析仪表板

### Phase 6: 调度与运维（1周）
- [ ] Celery定时任务
- [ ] 监控告警
- [ ] 日志系统
- [ ] 备份恢复

### Phase 7: 前端集成（2周）
- [ ] 案例浏览器页面
- [ ] 推荐卡片组件
- [ ] 趋势分析页面
- [ ] 概念图参考库

---

## 📝 总结

这是一个**企业级大规模外部数据系统**的完整架构，支持：
- ✅ **10,000+ 项目**（可扩展到100,000+）
- ✅ **5+ 数据源**（Archdaily/Gooood/Dezeen/Architizer/...）
- ✅ **自动化同步**（每日增量，无人值守）
- ✅ **多角度应用**（语义搜索/推荐/LLM增强/趋势分析/...）
- ✅ **高可用性**（分布式架构，99.9%可用性）

**核心技术栈**：
- **爬虫**: Playwright + BeautifulSoup
- **存储**: PostgreSQL + MongoDB + Redis
- **索引**: Qdrant（向量） + Elasticsearch（全文）
- **调度**: Celery + Redis
- **应用**: FastAPI + LangChain
- **监控**: Prometheus + Grafana

**下一步建议**：
1. **快速验证**：先完成Archdaily大规模爬取（2500个项目）
2. **数据库设计**：实现PostgreSQL Schema
3. **向量化**：OpenAI Embeddings批量处理
4. **API开发**：语义搜索API（优先级最高）
5. **前端集成**：案例浏览器

---

**作者**: AI Architecture Team
**维护者**: Claude Code
**版本**: v8.120.0
**日期**: 2026-02-17
