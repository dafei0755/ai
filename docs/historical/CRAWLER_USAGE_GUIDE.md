# 外部爬虫使用指南

**版本**: v8.110.0
**状态**: 实验阶段

---

## 📦 安装依赖

```bash
# 安装爬虫依赖
pip install -r requirements-crawler.txt

# 可选：安装Playwright（应对JavaScript动态加载）
playwright install chromium
```

---

## 🚀 快速开始

### 1. 手动运行爬虫

```bash
cd intelligent_project_analyzer/scripts
python crawl_external_layer2.py
```

**输出**:
- `intelligent_project_analyzer/data/external_layer2_cache.json` - 爬取结果缓存（30天有效期）

### 2. 测试单个爬虫

```python
from intelligent_project_analyzer.crawlers import ArchdailyCrawler, CrawlerConfig

# 配置
config = CrawlerConfig(
    max_projects=5,        # 仅爬5个项目（测试）
    request_delay=3.0,     # 3秒延迟
    days_back=30,
)

# 爬取
crawler = ArchdailyCrawler(config=config, category="residential")
projects = crawler.fetch()

# 查看结果
for p in projects:
    print(f"{p.title} - {p.url}")
```

---

## 🛠️ 爬虫配置

### CrawlerConfig参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_retries` | int | 3 | 最大重试次数 |
| `request_delay` | float | 2.0 | 请求间隔（秒） |
| `timeout` | int | 30 | 请求超时（秒） |
| `days_back` | int | 30 | 抓取多少天内的内容 |
| `min_views` | int | 5000 | 最小浏览量（筛选标准） |
| `max_projects` | int | 50 | 最多抓取项目数 |
| `use_proxy` | bool | False | 是否使用代理 |
| `proxy_list` | List[str] | None | 代理列表 |

### 修改配置

编辑 `crawl_external_layer2.py`:

```python
config = CrawlerConfig(
    max_retries=5,         # 增加重试次数
    request_delay=5.0,     # 加大延迟（更安全）
    max_projects=30,       # 增加爬取数量
    use_proxy=True,        # 启用代理
    proxy_list=[
        "http://proxy1:port",
        "http://proxy2:port",
    ]
)
```

---

## 📊 支持的数据源

### 1. Archdaily中国区

**URL**: https://www.archdaily.cn/cn
**分类**:
- `residential` - 住宅
- `commercial` - 办公/商业
- `cultural` - 文化建筑
- `hotel` - 酒店

**示例**:
```python
crawler = ArchdailyCrawler(config=config, category="cultural")
```

### 2. Gooood

**URL**: https://www.gooood.cn
**分类**:
- `residential` - 住宅
- `commercial` - 商业
- `cultural` - 文化
- `landscape` - 景观

**示例**:
```python
crawler = GoooodCrawler(config=config, category="landscape")
```

---

## 🔄 定时任务

### Windows任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务
   - 名称: `Layer2外部爬虫`
   - 触发器: 每月第1天，上午2:00
   - 操作: 启动程序
     - 程序: `python.exe`
     - 参数: `crawl_external_layer2.py`
     - 起始于: `D:\11-20\langgraph-design\intelligent_project_analyzer\scripts`

### Linux Cron

```bash
# 编辑crontab
crontab -e

# 添加定时任务（每月1日凌晨2点）
0 2 1 * * cd /path/to/project && python intelligent_project_analyzer/scripts/crawl_external_layer2.py >> /var/log/layer2_crawler.log 2>&1
```

---

## ⚠️ 注意事项

### 1. 反爬虫策略

**当前实施**:
- User-Agent轮换（5个常见浏览器）
- 请求延迟（2-3秒）
- 失败重试（指数退避）

**如果被封禁**:
1. 增加`request_delay`到5-10秒
2. 减少`max_projects`
3. 启用代理池
4. 降低爬取频率（每月→每季度）

### 2. 数据质量

**自动过滤**:
- 描述长度<100字符 → 丢弃
- 发布日期>30天 → 丢弃
- 浏览量<5000 → 丢弃

**人工审核**:
- 建议每月抽查前10个项目
- 检查描述准确性
- 验证图片有效性

### 3. 网站结构变化

**风险**: 目标网站改版可能导致爬虫失效

**应对**:
- 爬虫使用多种选择器（容错）
- 定期测试（每月1次）
- 失败时回退到人工策展池

### 4. 法律合规

**重要**:
- 仅用于研究学习目的
- 遵守网站robots.txt
- 不进行商业用途
- 数据不公开分发
- 尊重原作者版权

---

## 🧪 测试爬虫

### 快速测试（仅爬1个项目）

```bash
cd intelligent_project_analyzer/scripts

# 创建测试脚本
cat > test_crawler.py << 'EOF'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from intelligent_project_analyzer.crawlers import ArchdailyCrawler, CrawlerConfig

config = CrawlerConfig(
    max_projects=1,
    request_delay=2.0,
)

crawler = ArchdailyCrawler(config=config)
projects = crawler.fetch()

if projects:
    p = projects[0]
    print(f"\n✅ 测试成功！")
    print(f"标题: {p.title}")
    print(f"URL: {p.url}")
    print(f"描述长度: {len(p.description)} 字符")
else:
    print("\n❌ 测试失败：未爬取到项目")
EOF

# 运行测试
python test_crawler.py
```

### 验证缓存文件

```bash
# 查看缓存
cat intelligent_project_analyzer/data/external_layer2_cache.json | head -50

# 统计候选数量
python -c "import json; data=json.load(open('intelligent_project_analyzer/data/external_layer2_cache.json')); print(f'候选数量: {data[\"total_selected\"]}')"
```

---

## 🐛 故障排查

### 问题1: 请求超时

**症状**: `RequestException: timeout`

**解决**:
```python
config = CrawlerConfig(
    timeout=60,           # 增加超时时间
    max_retries=5,        # 增加重试次数
)
```

### 问题2: 未找到项目链接

**症状**: `找到 0 个项目链接`

**原因**: 网站结构变化

**解决**:
1. 手动访问目标网站，检查页面结构
2. 使用浏览器开发者工具查看HTML
3. 更新爬虫选择器：

```python
# 在archdaily_crawler.py中修改
articles = soup.find_all("article", class_="新的class名")
```

### 问题3: 描述过短

**症状**: `项目描述过短 (XX字符)`

**原因**: 描述元素选择器错误

**解决**:
```python
# 添加更多备用选择器
desc_selectors = [
    ("div", {"class": "新的描述class"}),
    ("section", {"id": "新的描述id"}),
]
```

### 问题4: 被封禁

**症状**: 连续请求失败，HTTP 403/429

**解决**:
1. 立即停止爬虫
2. 等待24小时
3. 增加延迟：
   ```python
   config = CrawlerConfig(request_delay=10.0)
   ```
4. 启用代理

---

## 📈 性能优化

### 当前性能

| 指标 | 数值 |
|------|------|
| **爬取速度** | 20项目/分钟 |
| **单项目耗时** | 3秒（含延迟） |
| **总耗时（40项目）** | 约2分钟 |

### 优化方案

**并发爬取**（慎用，容易被封）:
```python
import concurrent.futures

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(crawler.parse_project_page, url) for url in urls]
    projects = [f.result() for f in futures if f.result()]
```

**缓存复用**:
- 30天内不重复爬取同一URL
- 检查缓存是否过期

---

## 🔗 集成到主流程

### 1. 自动加载外部候选

```python
# 在few_shot_selector_v2.py中
def load_external_layer2():
    cache_path = Path("data/external_layer2_cache.json")

    if not cache_path.exists():
        return []

    with open(cache_path) as f:
        data = json.load(f)

    # 检查过期（30天）
    crawl_time = datetime.fromisoformat(data["crawl_time"])
    if (datetime.now() - crawl_time).days > 30:
        logger.warning("⚠️ 外部缓存已过期")
        return []

    return data["candidates"]
```

### 2. 融合到多源匹配

详见 `LAYER2_MULTI_SOURCE_ARCHITECTURE.md`

---

## 📝 下一步TODO

- [ ] 集成真实LLM特征提取（替换模拟版本）
- [ ] 实现代理池管理
- [ ] 添加Playwright支持（应对JS渲染）
- [ ] 实现增量爬取（只爬新项目）
- [ ] 添加数据质量评分
- [ ] 监控爬虫健康状态
- [ ] 构建爬虫Dashboard

---

**创建时间**: 2026-02-17
**维护者**: AI Architecture Team
