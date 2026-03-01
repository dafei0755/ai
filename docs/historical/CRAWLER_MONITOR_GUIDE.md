# 智能爬虫调度&监控系统

## 📋 功能特性

### ✨ 核心功能

1. **智能调度**
   - 同一网站串行爬取（避免并发触发反爬）
   - 分批次执行，每批自动休息
   - 随机延迟模拟人类行为
   - 支持断点续爬

2. **反爬虫策略**
   - 请求间隔：2-5秒随机
   - 批次休息：60秒（±20%波动）
   - 工作时段：9:00-22:00
   - 限速：500请求/小时，5000请求/天

3. **实时监控**
   - WebSocket实时推送进度
   - 任务状态可视化
   - 实时日志流
   - 成功率&性能统计

4. **管理功能**
   - 暂停/恢复/停止任务
   - 动态调整配置
   - 多任务管理
   - 错误自动重试

## 🚀 快速开始

### 1. 启动后端服务

```bash
# 启动FastAPI后端
python -m uvicorn intelligent_project_analyzer.api.server:app --reload --host 0.0.0.0 --port 8000
```

### 2. 打开监控控制台

在浏览器中打开：
```
file:///D:/11-20/langgraph-design/crawler_monitor.html
```

或者使用http服务器：
```bash
# 使用Python自带的http服务器
cd D:\11-20\langgraph-design
python -m http.server 8080

# 然后访问
http://localhost:8080/crawler_monitor.html
```

### 3. 启动爬取任务

在控制台点击按钮，或通过API：

```bash
# 启动Gooood爬取
curl -X POST "http://localhost:8000/api/crawler/start" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "gooood",
    "limit": 1000,
    "resume": true,
    "auto_translate": false
  }'

# 启动Archdaily爬取（带翻译）
curl -X POST "http://localhost:8000/api/crawler/start" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "archdaily",
    "limit": 500,
    "resume": true,
    "auto_translate": true,
    "translation_engine": "deepseek"
  }'
```

## 📊 监控界面

### 仪表板指标

- **活跃任务**: 当前运行中的任务数量
- **累计爬取**: 已成功爬取的项目总数
- **成功率**: 成功/总数的百分比
- **平均耗时**: 每个项目的平均爬取时间

### 任务列表

每个任务显示：
- 任务ID和状态(running/paused/stopped)
- 进度条和百分比
- 详细统计(成功/失败/批次)
- 当前爬取URL
- 错误信息（如有）

### 实时日志

- 显示最近200条日志
- 按级别着色（INFO/WARNING/ERROR）
- 自动滚动到最新
- 可清空

## 🔧 API接口

### WebSocket

```javascript
// 连接监控WebSocket
const ws = new WebSocket('ws://localhost:8000/api/crawler/ws/monitor');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'progress') {
    // 进度更新
    console.log('Progress:', data.data);
  } else if (data.type === 'log') {
    // 日志消息
    console.log('Log:', data.data);
  }
};
```

### REST API

#### 启动任务
```
POST /api/crawler/start
Body: {
  "source": "gooood|archdaily|dezeen",
  "category": "optional",
  "limit": 1000,
  "auto_translate": true,
  "translation_engine": "deepseek",
  "resume": true
}
```

#### 暂停任务
```
POST /api/crawler/pause/{task_id}
```

#### 恢复任务
```
POST /api/crawler/resume/{task_id}
```

#### 停止任务
```
POST /api/crawler/stop/{task_id}
```

#### 查询进度
```
GET /api/crawler/progress/{task_id}
GET /api/crawler/progress  # 所有任务
```

#### 查询统计
```
GET /api/crawler/stats
```

#### 获取配置
```
GET /api/crawler/config
```

#### 更新配置
```
PATCH /api/crawler/config
Body: {
  "batch_size": 50,
  "min_delay": 2.0,
  "max_delay": 5.0,
  "batch_rest": 60.0,
  "max_requests_per_hour": 500,
  "max_requests_per_day": 5000
}
```

## ⚙️ 配置说明

### 批次配置（BatchConfig）

```python
batch_size = 50                    # 每批数量
min_delay = 2.0                    # 最小请求间隔（秒）
max_delay = 5.0                    # 最大请求间隔（秒）
batch_rest = 60.0                  # 批次间休息（秒）
error_retry_delay = 300.0          # 错误重试延迟（秒）
max_retries = 3                    # 最大重试次数

# 时段控制
work_hours = [9, 10, ..., 21]      # 工作时段 9:00-22:00
weekend_enabled = True             # 是否在周末运行

# 限速
max_requests_per_hour = 500        # 每小时最大请求数
max_requests_per_day = 5000        # 每天最大请求数
```

### 修改配置

#### 方法1：通过API动态修改
```bash
curl -X PATCH "http://localhost:8000/api/crawler/config" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_size": 30,
    "max_requests_per_hour": 300
  }'
```

#### 方法2：代码中修改
```python
from intelligent_project_analyzer.external_data_system.crawler_scheduler import (
    IntelligentCrawlerScheduler,
    BatchConfig
)

# 自定义配置
config = BatchConfig(
    batch_size=30,
    min_delay=3.0,
    max_delay=8.0,
    batch_rest=120.0,  # 2分钟
    max_requests_per_hour=300
)

scheduler = IntelligentCrawlerScheduler(config)
```

## 📁 数据存储

### 断点文件
位置：`data/crawler_state/{task_id}.checkpoint`

格式：
```json
{
  "task_id": "gooood_20260217_143022",
  "position": 256,
  "timestamp": "2026-02-17T14:35:12"
}
```

### 项目索引
数据库：`data/project_index.db`

表：`project_index`
- source: 数据源
- source_id: 源ID
- url: 项目URL
- category: 分类
- discovered_at: 发现时间
- crawled_at: 爬取时间
- is_crawled: 是否已爬
- crawl_attempts: 爬取尝试次数
- last_error: 最后错误

### 项目详情
数据库：`data/external_projects.db`

表：`external_projects`（双语字段）
- source, source_id, url
- title_en, title_zh
- description_en, description_zh
- architects, location, year, area_sqm
- categories, tags
- translation_metadata

## 🔄 推荐工作流

### 阶段1：建立索引（已完成）
```bash
# 各网站索引已运行
python scripts/crawl_project_lists.py --source gooood --max-pages 999
python scripts/crawl_project_lists.py --source archdaily --max-pages 999
python scripts/crawl_project_lists.py --source dezeen --max-pages 999
```

### 阶段2：分批爬取详情（当前）

#### 方案A：自动分批（推荐）
```bash
# 启动监控控制台
# 打开 crawler_monitor.html
# 点击"启动 Gooood"按钮

# 系统会自动：
# - 每批50个项目
# - 每批后休息60秒
# - 每个请求延迟2-5秒
# - 非工作时段自动暂停
# - 触发限速自动等待
```

#### 方案B：手动分批
```python
# 脚本分批执行
for i in range(0, 5000, 500):
    # 爬取500个
    start_crawl(source='gooood', limit=500, resume=True)

    # 休息10分钟
    time.sleep(600)
```

#### 方案C：时段分批
```
上午 9:00-12:00: Gooood (500个)
下午14:00-17:00: Archdaily (300个)
晚上19:00-22:00: Dezeen (200个)
```

### 阶段3：质量检查
```bash
# 检查爬取统计
curl http://localhost:8000/api/crawler/stats

# 检查质量问题
curl http://localhost:8000/api/external-data/quality-issues
```

## 🛡️ 反爬虫策略

### 已实现的防护

1. **请求频率控制**
   - 单次请求随机延迟2-5秒
   - 每50个项目休息60秒
   - 每小时最多500请求
   - 每天最多5000请求

2. **行为模拟**
   - 延迟时间随机波动
   - 批次休息时间±20%波动
   - 使用真实User-Agent
   - 禁用自动化检测特征

3. **智能调度**
   - 工作时段限制（9:00-22:00）
   - 可选周末休息
   - 错误自动重试（间隔5分钟）
   - 失败3次自动跳过

4. **资源保护**
   - 单网站串行（不并发）
   - 限制图片数量（最多10张）
   - 超时控制（30秒）
   - 自动断点保存

### 建议的保守策略

对于特别重要的网站：
```python
config = BatchConfig(
    batch_size=20,          # 减小批次
    min_delay=5.0,          # 增加延迟
    max_delay=10.0,
    batch_rest=180.0,       # 3分钟休息
    max_requests_per_hour=200,  # 降低限速
    work_hours=[10, 11, 14, 15, 16, 19, 20]  # 避开高峰
)
```

## 📈 性能预估

### 正常模式（当前配置）
- 单项耗时: ~3.5秒（请求+解析）
- 批次休息: 60秒
- 每批: 50个项目
- **每小时**: ~450个项目
- **每天**: ~3600个项目（8小时工作时段）

### 保守模式
- 单项耗时: ~7.5秒
- 批次休息: 180秒
- 每批: 20个项目
- **每小时**: ~120个项目
- **每天**: ~960个项目

### 完成预估

假设索引总量：
- Gooood: 5000个
- Archdaily: 3000个
- Dezeen: 2000个
- **总计: 10000个**

**正常模式**: 10000 / 3600 ≈ **3天**
**保守模式**: 10000 / 960 ≈ **10天**

## 🐛 故障排查

### WebSocket连接失败
1. 检查后端是否启动
2. 确认端口8000可访问
3. 查看浏览器控制台错误

### 任务无法启动
1. 检查索引是否有数据: `GET /api/crawler/stats`
2. 确认数据源名称正确: `gooood`, `archdaily`, `dezeen`
3. 查看后端日志

### 爬取速度过慢
1. 检查是否处于非工作时段
2. 确认是否触发限速
3. 查看任务详情中的`avg_response_time`
4. 考虑调整`batch_rest`和`delay`参数

### 高失败率
1. 检查网络连接
2. 查看错误日志
3. 确认目标网站可访问
4. 可能需要更新选择器（网站改版）

## 📞 技术支持

遇到问题？
1. 查看控制台日志
2. 检查后端日志
3. 查看数据库状态
4. 提交issue

---

**版本**: v8.200
**最后更新**: 2026-02-17
