# 建筑项目资料库 - 系统性爬取方案

## 一、资料库核心目标

构建一个**多维度、可深度检索**的建筑项目资料库，重点关注：
- ✅ **项目文本内容**（最重要）：设计理念、灵感、概念、思路、材料说明
- ✅ **多维度分类**：功能、地区、建筑师、年份、材料
- ✅ **系统性覆盖**：全站爬取，不限于首页
- ✅ **自动更新**：增量爬取新项目

---

## 二、数据结构设计

### 2.1 完整项目数据模型

```python
@dataclass
class ArchProjectExtended:
    """扩展的建筑项目数据模型"""

    # 基础信息
    url: str                    # 项目URL（唯一标识）
    title: str                  # 项目标题
    source: str                 # 来源（archdaily/gooood）

    # 元数据
    architects: str             # 建筑师/事务所
    area: str                   # 面积
    year: str                   # 年份
    location: str               # 位置

    # 📝 文本内容（核心）
    description: str            # 完整项目描述
    design_concept: str         # 设计概念/理念
    inspiration: str            # 灵感来源
    design_strategy: str        # 设计策略/思路
    materials_info: str         # 材料说明
    technical_details: str      # 技术细节

    # 🏷️ 多维度分类
    categories: List[str]       # 功能分类 ["文化建筑", "图书馆"]
    regions: List[str]          # 地区分类 ["中国", "广东", "惠州"]
    tags: List[str]             # 标签

    # 图片
    images: List[str]           # 图片URL列表
    featured_image: str         # 特色图片

    # 爬取信息
    crawl_time: datetime        # 爬取时间
    update_time: datetime       # 更新时间
    views: int                  # 浏览量
    publish_date: datetime      # 发布日期
```

### 2.2 Archdaily分类体系（从截图分析）

#### 功能分类
```
文化建筑/
├── 科教建筑
├── 演艺建筑
├── 展陈建筑
├── 图书馆
├── 博物馆
└── ...

教育建筑/
├── 幼儿园
├── 小学
├── 宿舍
├── 科研建筑
└── ...

商业建筑/
居住建筑/
酒店建筑/
...
```

#### 地区分类
```
最受欢迎：
- 中国、美国、日本、西班牙、法国...

按字母：
- Norway、中国香港、乌干达、以色列...
```

#### 建筑师分类
```
最受欢迎：
- 扎哈·哈迪德建筑事务所
- OMA
- C.F. Møller
- Foster + Partners
...
```

#### 年份分类
```
2026, 2025, 2024, 2023, 2022...
```

---

## 三、系统性爬取策略

### 3.1 多维度URL映射

```python
class CategoryCrawler(PlaywrightCrawler):
    """多维度分类爬虫"""

    # 第一步：发现分类体系
    def discover_categories(self) -> Dict[str, List[str]]:
        """
        从Archdaily首页解析所有分类链接

        返回示例:
        {
            "functions": {
                "文化建筑": "/cn/search?category=文化建筑",
                "教育建筑": "/cn/search?category=教育建筑",
                ...
            },
            "regions": {
                "中国": "/cn/search?country=中国",
                "美国": "/cn/search?country=美国",
                ...
            },
            "architects": {
                "OMA": "/cn/office/oma",
                "扎哈": "/cn/office/zaha-hadid",
                ...
            },
            "years": {
                "2026": "/cn/search?year=2026",
                "2025": "/cn/search?year=2025",
                ...
            }
        }
        """
        # 解析导航栏分类
        # 提取分类链接模式
        pass

    # 第二步：按分类爬取
    def crawl_category(
        self,
        category_url: str,
        max_pages: int = 50
    ) -> List[str]:
        """
        爬取某个分类下的所有项目（支持翻页）

        Args:
            category_url: 分类URL（如 /cn/search?category=文化建筑）
            max_pages: 最大翻页数

        Returns:
            项目URL列表
        """
        project_urls = []
        page = 1

        while page <= max_pages:
            # 构建分页URL
            page_url = f"{category_url}&page={page}"

            # 爬取当前页项目链接
            page_projects = self._extract_project_links(page_url)

            if not page_projects:
                break  # 无更多项目

            project_urls.extend(page_projects)
            page += 1

        return project_urls

    # 第三步：全站爬取
    def crawl_all_categories(self) -> Dict[str, List[str]]:
        """
        遍历所有分类，系统性爬取全站

        返回:
        {
            "文化建筑": [url1, url2, ...],
            "教育建筑": [url3, url4, ...],
            "中国": [url5, url6, ...],
            "2025": [url7, url8, ...],
            ...
        }
        """
        categories = self.discover_categories()
        results = {}

        for dimension, category_dict in categories.items():
            for category_name, category_url in category_dict.items():
                logger.info(f"爬取分类: {dimension}/{category_name}")

                project_urls = self.crawl_category(category_url)
                results[category_name] = project_urls

                logger.info(f"  找到 {len(project_urls)} 个项目")

        return results
```

### 3.2 文本内容增强

```python
def parse_extended_content(self, soup: BeautifulSoup) -> Dict[str, str]:
    """
    深度解析项目文本内容

    目标:
    - 完整描述（不截断）
    - 设计概念/理念
    - 灵感来源
    - 材料说明
    - 技术细节
    """
    content = {}

    # 1. 完整描述（所有段落）
    desc_elem = soup.find("div", class_=re.compile("article-body|post-content"))
    if desc_elem:
        paragraphs = desc_elem.find_all("p")
        content["description"] = "\n\n".join([
            p.get_text(strip=True)
            for p in paragraphs
            if p.get_text(strip=True)
        ])

    # 2. 设计概念（通常在前几段）
    # 关键词：概念、理念、思考、策略
    concept_keywords = ["概念", "理念", "思考", "策略", "想法", "愿景"]
    for p in paragraphs[:5]:  # 前5段
        text = p.get_text()
        if any(kw in text for kw in concept_keywords):
            content["design_concept"] = text
            break

    # 3. 灵感来源
    inspiration_keywords = ["灵感", "启发", "源自", "受到", "借鉴"]
    for p in paragraphs:
        text = p.get_text()
        if any(kw in text for kw in inspiration_keywords):
            content["inspiration"] = text
            break

    # 4. 材料说明
    material_keywords = ["材料", "材质", "木材", "钢", "混凝土", "玻璃", "砖"]
    material_paragraphs = []
    for p in paragraphs:
        text = p.get_text()
        if any(kw in text for kw in material_keywords):
            material_paragraphs.append(text)

    if material_paragraphs:
        content["materials_info"] = "\n".join(material_paragraphs)

    # 5. 技术细节
    tech_keywords = ["技术", "结构", "系统", "施工", "工艺"]
    tech_paragraphs = []
    for p in paragraphs:
        text = p.get_text()
        if any(kw in text for kw in tech_keywords):
            tech_paragraphs.append(text)

    if tech_paragraphs:
        content["technical_details"] = "\n".join(tech_paragraphs)

    return content
```

### 3.3 去重机制

```python
class ProjectDeduplicator:
    """项目去重器"""

    def __init__(self):
        self.seen_urls = set()          # URL去重
        self.seen_titles = {}           # 标题去重（URL映射）
        self.url_normalize_cache = {}   # URL标准化缓存

    def normalize_url(self, url: str) -> str:
        """标准化URL（移除查询参数）"""
        if url in self.url_normalize_cache:
            return self.url_normalize_cache[url]

        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        self.url_normalize_cache[url] = base_url
        return base_url

    def is_duplicate(
        self,
        url: str,
        title: str = None
    ) -> Tuple[bool, str]:
        """
        判断项目是否重复

        Returns:
            (是否重复, 重复原因)
        """
        # URL去重
        normalized_url = self.normalize_url(url)
        if normalized_url in self.seen_urls:
            return True, f"URL重复: {normalized_url}"

        # 标题去重
        if title and title in self.seen_titles:
            existing_url = self.seen_titles[title]
            return True, f"标题重复: {title} (已存在: {existing_url})"

        # 标记为已见过
        self.seen_urls.add(normalized_url)
        if title:
            self.seen_titles[title] = normalized_url

        return False, ""
```

---

## 四、数据库设计

### 4.1 SQLite Schema

```sql
CREATE TABLE arch_projects (
    -- 主键
    url TEXT PRIMARY KEY,

    -- 基础信息
    title TEXT NOT NULL,
    source TEXT NOT NULL,  -- 'archdaily' or 'gooood'

    -- 元数据
    architects TEXT,
    area TEXT,
    year TEXT,
    location TEXT,

    -- 文本内容（核心）
    description TEXT,
    design_concept TEXT,
    inspiration TEXT,
    design_strategy TEXT,
    materials_info TEXT,
    technical_details TEXT,

    -- 分类（JSON格式）
    categories TEXT,  -- JSON: ["文化建筑", "图书馆"]
    regions TEXT,     -- JSON: ["中国", "广东", "惠州"]
    tags TEXT,        -- JSON: ["可持续", "材料创新"]

    -- 图片
    images TEXT,      -- JSON: ["url1", "url2", ...]
    featured_image TEXT,

    -- 爬取信息
    crawl_time TIMESTAMP,
    update_time TIMESTAMP,
    views INTEGER,
    publish_date TIMESTAMP,

    -- 索引
    FOREIGN KEY (source) REFERENCES sources(name)
);

-- 多维度检索索引
CREATE INDEX idx_categories ON arch_projects(categories);
CREATE INDEX idx_regions ON arch_projects(regions);
CREATE INDEX idx_year ON arch_projects(year);
CREATE INDEX idx_architects ON arch_projects(architects);
CREATE INDEX idx_publish_date ON arch_projects(publish_date);

-- 全文搜索索引（SQLite FTS5）
CREATE VIRTUAL TABLE arch_projects_fts USING fts5(
    title,
    description,
    design_concept,
    materials_info,
    content=arch_projects
);
```

### 4.2 多维度查询示例

```python
import sqlite3
import json

class ArchProjectDatabase:
    """建筑项目数据库"""

    def search_by_category(self, category: str) -> List[Dict]:
        """按功能分类查询"""
        query = """
        SELECT * FROM arch_projects
        WHERE categories LIKE ?
        ORDER BY publish_date DESC
        """
        return self.execute(query, (f'%"{category}"%',))

    def search_by_region(self, region: str) -> List[Dict]:
        """按地区查询"""
        query = """
        SELECT * FROM arch_projects
        WHERE regions LIKE ?
        ORDER BY publish_date DESC
        """
        return self.execute(query, (f'%"{region}"%',))

    def search_by_architect(self, architect: str) -> List[Dict]:
        """按建筑师查询"""
        query = """
        SELECT * FROM arch_projects
        WHERE architects LIKE ?
        ORDER BY publish_date DESC
        """
        return self.execute(query, (f'%{architect}%',))

    def search_by_year(self, year: str) -> List[Dict]:
        """按年份查询"""
        query = """
        SELECT * FROM arch_projects
        WHERE year = ?
        ORDER BY publish_date DESC
        """
        return self.execute(query, (year,))

    def full_text_search(self, keyword: str) -> List[Dict]:
        """全文搜索（描述、概念、材料）"""
        query = """
        SELECT * FROM arch_projects
        WHERE url IN (
            SELECT rowid FROM arch_projects_fts
            WHERE arch_projects_fts MATCH ?
        )
        ORDER BY publish_date DESC
        """
        return self.execute(query, (keyword,))

    def multi_dimension_search(
        self,
        category: str = None,
        region: str = None,
        year: str = None,
        architect: str = None,
        keyword: str = None
    ) -> List[Dict]:
        """多维度组合查询"""
        conditions = []
        params = []

        if category:
            conditions.append("categories LIKE ?")
            params.append(f'%"{category}"%')

        if region:
            conditions.append("regions LIKE ?")
            params.append(f'%"{region}"%')

        if year:
            conditions.append("year = ?")
            params.append(year)

        if architect:
            conditions.append("architects LIKE ?")
            params.append(f'%{architect}%')

        if keyword:
            conditions.append("""
                description LIKE ? OR
                design_concept LIKE ? OR
                materials_info LIKE ?
            """)
            params.extend([f'%{keyword}%'] * 3)

        query = f"""
        SELECT * FROM arch_projects
        WHERE {' AND '.join(conditions)}
        ORDER BY publish_date DESC
        """

        return self.execute(query, params)
```

---

## 五、增量更新策略

### 5.1 更新检测

```python
class IncrementalCrawler(CategoryCrawler):
    """增量爬取器"""

    def __init__(self, db: ArchProjectDatabase):
        super().__init__()
        self.db = db
self.last_crawl_time = db.get_last_crawl_time()

    def crawl_new_projects_only(self) -> List[ProjectData]:
        """
        只爬取新项目（增量更新）

        策略:
        1. 爬取首页（最新项目）
        2. 按发布日期过滤（> last_crawl_time）
        3. 检查URL是否已在数据库
        4. 只抓取新项目
        """
        # 爬取首页
        homepage_projects = self.fetch_project_list()

        new_projects = []
        for url in homepage_projects:
            # 数据库检查
            if self.db.project_exists(url):
                logger.info(f"项目已存在，跳过: {url}")
                continue

            # 爬取项目详情
            project = self.parse_project_page(url)

            # 发布日期过滤
            if project.publish_date > self.last_crawl_time:
                new_projects.append(project)
                logger.info(f"新项目: {project.title}")
            else:
                logger.info(f"项目过旧，停止: {project.title}")
                break  # 按时间排序，后续都是旧项目

        return new_projects

    def schedule_auto_update(
        self,
        interval: str = "daily",
        time: str = "03:00"
    ):
        """
        定时自动更新

        Args:
            interval: 'daily', 'weekly', 'monthly'
            time: 执行时间（如 "03:00"）
        """
        import schedule

        def job():
            logger.info("🔄 开始增量更新...")
            new_projects = self.crawl_new_projects_only()
            self.db.insert_projects(new_projects)
            logger.info(f"✅ 增量更新完成: {len(new_projects)} 个新项目")

        if interval == "daily":
            schedule.every().day.at(time).do(job)
        elif interval == "weekly":
            schedule.every().monday.at(time).do(job)
        elif interval == "monthly":
            # 每月1号执行
            schedule.every().month.at(time).do(job)

        logger.info(f"📅 已设置自动更新: {interval} at {time}")

        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
```

---

## 六、实施步骤

### Phase 1: 分类发现（1-2天）
1. ✅ 创建CategoryCrawler类
2. ✅ 实现discover_categories()
3. ✅ 测试：打印所有分类URL
4. ✅ 验证：确认URL模式正确

### Phase 2: 分类爬取（2-3天）
1. ✅ 实现crawl_category()（支持翻页）
2. ✅ 实现去重机制
3. ✅ 测试：爬取"文化建筑"分类（所有页）
4. ✅ 验证：检查重复项

### Phase 3: 文本增强（1-2天）
1. ✅ 实现parse_extended_content()
2. ✅ 提取设计概念、灵感、材料
3. ✅ 测试：对比原始描述vs增强内容
4. ✅ 验证：文本完整性

### Phase 4: 数据库设计（1天）
1. ✅ 创建SQLite数据库
2. ✅ 实现ArchProjectDatabase类
3. ✅ 创建多维度索引
4. ✅ 测试：多维度查询

### Phase 5: 全站爬取（1周）
1. ✅ 实现crawl_all_categories()
2. ✅ 配置爬取参数（延迟、线程）
3. ✅ 运行：系统性爬取全站
4. ✅ 验证：数据完整性

### Phase 6: 增量更新（1-2天）
1. ✅ 实现IncrementalCrawler
2. ✅ 配置定时任务
3. ✅ 测试：增量更新逻辑
4. ✅ 部署：自动更新

---

## 七、使用示例

### 7.1 系统性爬取全站

```bash
# 第一次全量爬取（可能需要几天）
python scripts/crawl_full_site.py \
    --source archdaily \
    --max-pages 50 \
    --delay 3
```

### 7.2 增量更新

```bash
# 每日增量更新
python scripts/crawl_incremental.py \
    --source archdaily \
    --schedule daily \
    --time "03:00"
```

### 7.3 多维度查询

```python
from database import ArchProjectDatabase

db = ArchProjectDatabase("arch_projects.db")

# 1. 查询"中国"的"文化建筑"
projects = db.multi_dimension_search(
    category="文化建筑",
    region="中国"
)

# 2. 查询"2025年"使用"木材"的项目
projects = db.multi_dimension_search(
    year="2025",
    keyword="木材"
)

# 3. 查询"OMA"的所有项目
projects = db.search_by_architect("OMA")

# 4. 全文搜索"可持续设计"
projects = db.full_text_search("可持续设计")
```

---

## 八、预期成果

### 8.1 数据规模
- ✅ **项目数量**: 10,000+ 个项目（Archdaily全站）
- ✅ **文本内容**: 平均每项目 1000+ 字符
- ✅ **图片数量**: 平均每项目 10-20 张
- ✅ **分类维度**: 功能、地区、建筑师、年份、材料

### 8.2 检索能力
- ✅ **多维度组合查询**
- ✅ **全文搜索**
- ✅ **按时间排序**
- ✅ **按浏览量排序**

### 8.3 自动更新
- ✅ **每日增量更新**
- ✅ **新项目自动入库**
- ✅ **数据库自动维护**

---

## 九、风险与对策

### 9.1 反爬虫
- **风险**: 请求频繁被封IP
- **对策**:
  - 增加延迟（3-5秒）
  - 使用代理池
  - User-Agent轮换

### 9.2 存储空间
- **风险**: 全站爬取占用大量空间
- **对策**:
  - 图片存储外链（不下载）
  - 定期清理旧数据
  - 压缩数据库

### 9.3 数据质量
- **风险**: 文本提取不完整
- **对策**:
  - 人工抽检
  - 自动化验证脚本
  - 定期更新解析逻辑

---

## 十、总结

这套方案将实现：
1. ✅ **系统性爬取**：覆盖Archdaily全站所有分类
2. ✅ **文本为中心**：完整提取设计理念、灵感、材料等
3. ✅ **多维度检索**：按功能、地区、建筑师、年份等查询
4. ✅ **自动更新**：增量爬取新项目

**下一步建议**：
1. 先实现Phase 1（分类发现）
2. 测试爬取1-2个分类
3. 验证文本提取效果
4. 逐步扩展到全站
