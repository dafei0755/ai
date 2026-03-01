# 爬虫网站清单与频率控制策略

**版本**: v1.0
**日期**: 2026-02-17
**状态**: 实施中

---

## 📋 爬虫网站清单

### 1. Archdaily（已实现）
- **网站**: https://www.archdaily.com
- **状态**: ✅ 已实现爬虫
- **预计项目数**: 10,000+
- **数据质量**: ⭐⭐⭐⭐⭐ (优秀)
- **更新频率**: 每日发布 20-30 个新项目
- **爬虫文件**: `archdaily_spider.py`

**数据结构**:
- 标题、描述、建筑师、位置、年份、面积
- 高质量图片（10-30张/项目）
- 完整的项目详情（材料、技术、设计理念）
- 分类标签（住宅、商业、文化等）

### 2. Gooood（待实现）
- **网站**: https://www.gooood.cn
- **状态**: 🔄 待实现
- **预计项目数**: 5,000+
- **数据质量**: ⭐⭐⭐⭐⭐ (优秀，中文内容丰富)
- **更新频率**: 每日发布 10-15 个新项目
- **优先级**: 高（中文项目案例库）

**特点**:
- 中英双语内容
- 中国及亚洲项目为主
- 深度案例解析
- 高质量摄影

### 3. Dezeen（待实现）
- **网站**: https://www.dezeen.com
- **状态**: 🔄 待实现
- **预计项目数**: 8,000+
- **数据质量**: ⭐⭐⭐⭐⭐ (优秀)
- **更新频率**: 每日发布 15-25 个新项目
- **优先级**: 高（国际知名度高）

**特点**:
- 全球视野
- 设计趋势前沿
- 包含产品设计、室内设计
- 新闻性强

### 4. Architizer（未来扩展）
- **网站**: https://architizer.com
- **状态**: ⏳ 未来扩展
- **预计项目数**: 15,000+
- **数据质量**: ⭐⭐⭐⭐
- **优先级**: 中（需付费数据）

### 5. ArchDaily CN（未来扩展）
- **网站**: https://www.archdaily.cn
- **状态**: ⏳ 未来扩展
- **预计项目数**: 5,000+
- **数据质量**: ⭐⭐⭐⭐
- **优先级**: 低（与Archdaily重复度高）

---

## ⏱️ 爬虫频率控制策略

### 第一轮完整爬取（冷启动期）

**目标**: 建立初始项目库（20,000-25,000个项目）

#### Archdaily 策略
```
阶段: 冷启动
时间: 7-10天
策略:
  - 并发数: 2-3个任务
  - 请求间隔: 3-5秒（随机）
  - 每批次: 50个项目
  - 失败重试: 最多3次
  - 代理轮换: 可选（如被封则启用）

进度计划:
  Day 1-3: 爬取前 3,000 个项目（测试稳定性）
  Day 4-7: 爬取中间 5,000 个项目（批量处理）
  Day 8-10: 爬取剩余 2,000+ 项目（查漏补缺）
```

#### Gooood 策略
```
阶段: 冷启动
时间: 5-7天
策略:
  - 并发数: 2个任务
  - 请求间隔: 4-6秒（随机）
  - 每批次: 30个项目
  - 失败重试: 最多3次
  - User-Agent轮换: 必须

进度计划:
  Day 1-2: 爬取前 1,000 个项目（测试）
  Day 3-5: 爬取中间 3,000 个项目
  Day 6-7: 查漏补缺
```

#### Dezeen 策略
```
阶段: 冷启动
时间: 5-7天
策略:
  - 并发数: 2个任务
  - 请求间隔: 4-6秒（随机）
  - 每批次: 40个项目
  - 失败重试: 最多3次
  - 反爬虫措施: 启用JS渲染

进度计划:
  Day 1-2: 爬取前 1,500 个项目
  Day 3-5: 爬取中间 5,000 个项目
  Day 6-7: 查漏补缺
```

### 防封策略

**多层防护机制**:

1. **请求频率控制**
   ```python
   import random
   import time

   def smart_delay():
       """智能延迟"""
       base_delay = 3.0  # 基础延迟3秒
       jitter = random.uniform(0, 2.0)  # 随机抖动0-2秒
       time.sleep(base_delay + jitter)
   ```

2. **User-Agent 轮换**
   ```python
   USER_AGENTS = [
       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0",
       "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1",
       "Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0",
       # ... 更多
   ]
   ```

3. **代理IP池（可选）**
   ```python
   # 如果频繁被封，启用代理
   PROXY_POOL = [
       "http://proxy1.example.com:8080",
       "http://proxy2.example.com:8080",
   ]
   ```

4. **请求头模拟**
   ```python
   HEADERS = {
       "Accept": "text/html,application/xhtml+xml,...",
       "Accept-Language": "en-US,en;q=0.9",
       "Accept-Encoding": "gzip, deflate, br",
       "Referer": "https://www.google.com/",
       "DNT": "1",
   }
   ```

5. **错误处理**
   ```python
   # 429 Too Many Requests -> 指数退避
   # 403 Forbidden -> 切换代理/UA
   # 503 Service Unavailable -> 暂停1小时
   ```

---

## 🔄 增量更新策略（每周一次）

### 定时任务配置

**Celery Beat 配置**:
```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # 每周一凌晨2点更新 Archdaily
    'weekly-archdaily-sync': {
        'task': 'external_data_system.tasks.sync_archdaily_incremental',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),
    },

    # 每周二凌晨2点更新 Gooood
    'weekly-gooood-sync': {
        'task': 'external_data_system.tasks.sync_gooood_incremental',
        'schedule': crontab(hour=2, minute=0, day_of_week=2),
    },

    # 每周三凌晨2点更新 Dezeen
    'weekly-dezeen-sync': {
        'task': 'external_data_system.tasks.sync_dezeen_incremental',
        'schedule': crontab(hour=2, minute=0, day_of_week=3),
    },
}
```

### 增量更新逻辑

```python
def incremental_sync(source: str, days: int = 7):
    """
    增量同步：只爬取最近N天的新项目

    Args:
        source: 数据源名称
        days: 回溯天数
    """
    # 1. 获取最新爬取时间
    last_sync = get_last_sync_time(source)

    # 2. 爬取新项目（按发布日期筛选）
    new_projects = spider.fetch_recent_projects(
        since=last_sync,
        days=days
    )

    # 3. 去重（URL去重）
    unique_projects = deduplicate_by_url(new_projects)

    # 4. 保存到数据库
    for project in unique_projects:
        save_or_update_project(project)

    # 5. 记录同步历史
    log_sync_history(source, len(unique_projects))
```

### 更新频率参数

| 网站 | 每周更新日 | 预计新增 | 爬取时长 | 并发数 |
|------|-----------|----------|----------|--------|
| Archdaily | 周一 02:00 | 150-200项目 | 30-60分钟 | 2 |
| Gooood | 周二 02:00 | 70-100项目 | 20-40分钟 | 2 |
| Dezeen | 周三 02:00 | 100-150项目 | 30-50分钟 | 2 |

**安全措施**:
- 凌晨时段执行（网站流量低）
- 分散到不同日期（避免同时爬取）
- 失败自动重试（最多3次）
- 邮件告警（失败超过5个项目）

---

## 📊 数据完整性验证

### 自动化测试清单

**每个爬虫必须通过的测试**:

```python
def test_spider_completeness(spider_name: str):
    """测试爬虫数据完整性"""

    # 1. 基础字段完整性
    assert project.title is not None
    assert project.url is not None
    assert project.source_id is not None

    # 2. 关键元数据存在率 >= 80%
    metadata_fields = ['architects', 'location', 'year', 'area_sqm']
    completeness = sum(1 for f in metadata_fields if getattr(project, f)) / len(metadata_fields)
    assert completeness >= 0.8

    # 3. 图片数量 >= 3
    assert len(project.images) >= 3

    # 4. 描述长度 >= 100字符
    assert len(project.description) >= 100

    # 5. 分类不为空
    assert project.primary_category is not None
```

### 人工抽查机制

**抽查频率**: 每1000个项目抽查10个

**抽查维度**:
- 标题准确性
- 描述完整性
- 图片链接有效性
- 建筑师信息准确性
- 分类标签合理性

### 质量监控仪表板

**实时指标**:
- 爬取成功率（目标 >= 95%）
- 数据完整度（目标 >= 0.8）
- 图片有效率（目标 >= 90%）
- 平均响应时间（目标 < 3秒）

---

## 🛡️ 封禁应对策略

### 被封识别

**判断标准**:
```python
if response.status_code in [403, 429]:
    logger.warning(f"可能被封: {response.status_code}")
    return "BLOCKED"

if "captcha" in response.text.lower():
    logger.warning("检测到验证码")
    return "CAPTCHA"

if response.elapsed.total_seconds() > 10:
    logger.warning("响应超时")
    return "TIMEOUT"
```

### 解封方案

**Level 1: 温和措施**
- 增加请求间隔（翻倍）
- 轮换 User-Agent
- 添加 Referer

**Level 2: 代理方案**
- 启用代理IP池
- 使用住宅IP代理
- 轮换代理（每50个请求）

**Level 3: 暂停策略**
- 暂停24小时
- 人工介入检查
- 考虑API方案（付费）

### 白名单申请

**长期方案**:
- 联系网站管理员
- 说明爬虫目的（学术研究）
- 申请白名单IP
- 遵守robots.txt

---

## 📈 进度跟踪

### 第一轮爬取进度表

| 网站 | 目标数量 | 已完成 | 进度 | 预计完成日期 |
|------|---------|--------|------|-------------|
| Archdaily | 10,000 | 0 | 0% | 2026-02-27 |
| Gooood | 5,000 | 0 | 0% | 2026-03-06 |
| Dezeen | 8,000 | 0 | 0% | 2026-03-13 |
| **总计** | **23,000** | **0** | **0%** | **2026-03-13** |

### 每日报告

**自动生成报告**（每晚23:00）:
```
📊 爬虫日报 - 2026-02-17
========================
Archdaily:
  - 今日新增: 120 个项目
  - 成功率: 96.5%
  - 平均质量分: 0.82
  - 失败原因: 5个超时, 2个解析错误

系统状态:
  - 数据库容量: 25.3GB / 100GB
  - Redis内存: 512MB / 2GB
  - 待处理队列: 15 个任务
```

---

## 🚀 快速启动命令

### 首次完整爬取
```bash
# 1. Archdaily（10天）
python scripts/crawl_archdaily_full.py --max-projects 10000 --batch-size 50

# 2. Gooood（7天）
python scripts/crawl_gooood_full.py --max-projects 5000 --batch-size 30

# 3. Dezeen（7天）
python scripts/crawl_dezeen_full.py --max-projects 8000 --batch-size 40
```

### 周更新任务（Celery）
```bash
# 启动 Celery Worker
celery -A intelligent_project_analyzer.external_data_system.tasks worker -l info

# 启动 Celery Beat（定时任务调度）
celery -A intelligent_project_analyzer.external_data_system.tasks beat -l info
```

### 手动触发增量更新
```bash
# Archdaily增量更新（最近7天）
python scripts/sync_archdaily_incremental.py --days 7

# 所有网站增量更新
python scripts/sync_all_incremental.py
```

---

## 📝 总结

**阶段划分**:
1. **冷启动期**（2-3周）：完整爬取 23,000 个项目
2. **稳定期**（长期）：每周增量更新 300-450 个新项目

**关键指标**:
- 爬取成功率: >= 95%
- 数据完整度: >= 0.8
- 平均响应时间: < 3秒
- 封禁概率: < 5%

**下一步**:
1. 实现 Gooood 和 Dezeen 爬虫
2. 配置 Celery Beat 定时任务
3. 部署监控告警系统
4. 启动第一轮完整爬取
