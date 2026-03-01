# 爬虫监控系统使用指南

## ✅ 系统已部署完成

### 📦 已创建的文件

1. **intelligent_project_analyzer/external_data_system/crawler_scheduler.py**
   - 智能爬虫调度器
   - 分批、分时、串行策略
   - 断点续爬支持
   - 实时进度&日志回调

2. **intelligent_project_analyzer/api/routes/crawler_monitor_routes.py**
   - WebSocket实时监控
   - REST API管理接口
   - 任务控制（启动/暂停/恢复/停止）
   - 配置动态调整

3. **crawler_monitor.html**
   - 可视化监控控制台
   - 实时进度展示
   - 日志流显示
   - 任务管理按钮

4. **scripts/test_crawler_scheduler.py**
   - 调度器测试脚本
   - 模拟爬取流程
   - 索引统计查询

5. **CRAWLER_MONITOR_GUIDE.md**
   - 完整使用文档
   - API参考
   - 配置说明
   - 故障排查

### 🚀 立即使用

#### Step 1: 启动后端服务

```bash
python -m uvicorn intelligent_project_analyzer.api.server:app --reload --host 0.0.0.0 --port 8000
```

确认看到：
```
✅ 爬虫监控管理路由已注册
```

#### Step 2: 打开监控控制台

方法A - 直接打开HTML文件：
```
D:\11-20\langgraph-design\crawler_monitor.html
```

方法B - 使用HTTP服务器：
```bash
cd D:\11-20\langgraph-design
python -m http.server 8080

# 浏览器访问
http://localhost:8080/crawler_monitor.html
```

#### Step 3: 启动爬取任务

在监控控制台点击按钮启动：
- **启动 Gooood**: 爬取中文项目（无需翻译）
- **启动 Archdaily**: 爬取英文项目（自动翻译）
- **启动 Dezeen**: 爬取英文项目（自动翻译）

或使用API：
```bash
curl -X POST "http://localhost:8000/api/crawler/start" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "gooood",
    "limit": 100,
    "resume": true,
    "auto_translate": false
  }'
```

### 📊 当前索引状态

根据查询结果：
```
总计: 61个项目
- Archdaily: 53个（未爬53）
- Gooood: 8个（已爬3，未爬5）
- Dezeen: 0个
```

**说明**: 索引任务可能仍在运行中，总数会继续增长。

### ⚙️ 调度策略（默认配置）

#### 反爬虫保护

- **请求间隔**: 2-5秒随机
- **批次大小**: 50个项目
- **批次休息**: 60秒（±20%波动）
- **错误重试**: 3次，间隔5分钟
- **最大重试次数**: 3次

#### 限速保护

- **每小时**: 最多500请求
- **每天**: 最多5000请求
- **工作时段**: 9:00-22:00
- **周末工作**: 启用

#### 同网站串行

✅ **核心特性**: 同一个网站的任务**绝不并行**
- Gooood任务运行时，不会启动另一个Gooood任务
- 不同网站可以并行（Gooood + Archdaily同时运行）
- 由TaskID自动管理，无需手动控制

### 🔍 实时监控功能

#### 仪表板指标

- **活跃任务**: 当前运行中的任务数
- **累计爬取**: 已成功的项目总数
- **成功率**: 实时计算百分比
- **平均耗时**: 每个项目的平均时间

#### 任务详情

每个任务显示：
```
✓ 任务ID: gooood_20260217_231145
✓ 状态: running/paused/stopped/error
✓ 进度条: 256/1000 (25.6%)
✓ 统计: 成功/失败/批次/请求数
✓ 当前URL: https://...
✓ 错误信息: (如有)
```

#### 实时日志

```
[23:11:52] INFO  开始爬取: gooood, 共 1000 项
[23:11:53] INFO  批次1完成，休息60秒...
[23:12:54] INFO  批次2开始
[23:13:15] ERROR 爬取失败: timeout
[23:13:20] INFO  重试成功
```

### 🎯 推荐工作流

#### 场景1: 小规模测试（前100个）

```bash
# 启动Gooood测试爬取
curl -X POST "http://localhost:8000/api/crawler/start" \
  -d '{"source": "gooood", "limit": 100, "resume": true}'

# 观察监控控制台
# 预计耗时: ~10分钟（100项 × 3.5秒 + 2批 × 60秒休息）
```

#### 场景2: 中规模爬取（500-1000个）

```bash
# 上午启动Gooood
curl -X POST "http://localhost:8000/api/crawler/start" \
  -d '{"source": "gooood", "limit": 1000, "resume": true}'

# 下午启动Archdaily
curl -X POST "http://localhost:8000/api/crawler/start" \
  -d '{"source": "archdaily", "limit": 500, "resume": true, "auto_translate": true}'

# 监控控制台实时查看进度
# Gooood预计: ~1.5小时
# Archdaily预计: ~50分钟
```

#### 场景3: 全量爬取（10000+）

**分阶段执行**（避免长时间连续爬取）：

```python
# 方案A: 每天分批
Day 1: Gooood (2000个) - 上午+下午
Day 2: Gooood (2000个)
Day 3: Gooood (1000个) + Archdaily (1000个)
Day 4: Archdaily (2000个)
Day 5: Dezeen (2000个)

# 方案B: 时段分批
9:00-12:00: 第一批 (450个)
14:00-17:00: 第二批 (450个)
19:00-22:00: 第三批 (450个)

每天约1350个，完成10000个需要8天
```

### 🛠️ 任务管理

#### 暂停任务

```bash
# API方式
curl -X POST "http://localhost:8000/api/crawler/pause/gooood_20260217_231145"

# 或在监控控制台点击"暂停全部"按钮
```

#### 恢复任务

```bash
# 从断点恢复
curl -X POST "http://localhost:8000/api/crawler/resume/gooood_20260217_231145"

# 断点信息保存在
# data/crawler_state/gooood_20260217_231145.checkpoint
```

#### 停止任务

```bash
# 彻底停止（不可恢复）
curl -X POST "http://localhost:8000/api/crawler/stop/gooood_20260217_231145"
```

#### 查询进度

```bash
# 单个任务
curl "http://localhost:8000/api/crawler/progress/gooood_20260217_231145"

# 所有任务
curl "http://localhost:8000/api/crawler/progress"

# 统计信息
curl "http://localhost:8000/api/crawler/stats"
```

### ⚡ 性能调优

#### 提速（谨慎使用）

```bash
# 减少延迟和休息时间
curl -X PATCH "http://localhost:8000/api/crawler/config" \
  -d '{
    "min_delay": 1.0,
    "max_delay": 2.0,
    "batch_rest": 30.0,
    "batch_size": 100
  }'

# 风险: 可能触发反爬虫
```

#### 保守模式（重要网站）

```bash
# 增加延迟和休息时间
curl -X PATCH "http://localhost:8000/api/crawler/config" \
  -d '{
    "min_delay": 5.0,
    "max_delay": 10.0,
    "batch_rest": 180.0,
    "batch_size": 20,
    "max_requests_per_hour": 200
  }'

# 更安全，但速度慢3倍
```

### 📈 数据查看

#### 爬取统计

```bash
# 总体统计
curl "http://localhost:8000/api/crawler/stats"

# 返回示例:
{
  "database": {
    "total_projects": 256,
    "by_source": {
      "gooood": 156,
      "archdaily": 100,
      "dezeen": 0
    }
  },
  "index": {
    "total": 10256,
    "crawled": 256,
    "uncrawled": 10000
  }
}
```

#### 索引进度

```bash
python -c "
from intelligent_project_analyzer.external_data_system.project_index import ProjectIndexManager
mgr = ProjectIndexManager()
stats = mgr.get_statistics()
print(f'总索引: {stats[\"total\"]}')
print(f'已爬取: {stats[\"crawled\"]}')
print(f'待爬取: {stats[\"uncrawled\"]}')
print(f'进度: {stats[\"crawled\"]/stats[\"total\"]*100:.1f}%')
"
```

### 🐛 常见问题

#### Q: WebSocket连接失败？

**A**: 检查步骤
1. 后端是否启动: `http://localhost:8000/docs`
2. 路由是否注册: 查看启动日志 "✅ 爬虫监控管理路由已注册"
3. 端口是否正确: 默认8000
4. 浏览器F12查看控制台错误

#### Q: 任务无法启动？

**A**: 可能原因
1. 索引为空: 运行 `python scripts/crawl_project_lists.py`
2. 数据源名称错误: 必须是 `gooood`, `archdaily`, `dezeen`
3. 权限问题: 确保有管理员权限（API需要）

#### Q: 爬取速度太慢？

**A**: 正常情况
- 每项3.5秒（包括延迟）
- 每50项休息60秒
- 每小时约450项
- 这是**故意的**（避免触发反爬虫）
- 如需提速，参考"性能调优"章节

#### Q: 高失败率？

**A**: 排查步骤
1. 查看错误日志（监控控制台）
2. 检查网络连接
3. 验证目标网站可访问
4. 可能是选择器失效（网站改版）
5. 考虑降低速度（反爬虫触发）

#### Q: 如何停止所有任务？

**A**: 三种方法
1. 监控控制台: 点击"停止全部"
2. API循环调用: 对每个task_id调用 `/stop/{task_id}`
3. 直接停止后端服务: Ctrl+C

### 📞 技术支持

**文档**: `CRAWLER_MONITOR_GUIDE.md`
**测试**: `python scripts/test_crawler_scheduler.py`
**API文档**: `http://localhost:8000/docs` (Swagger UI)

---

## 🎉 开始使用

```bash
# 1. 启动后端
python -m uvicorn intelligent_project_analyzer.api.server:app --reload

# 2. 打开监控控制台
# crawler_monitor.html

# 3. 点击"启动 Gooood"开始爬取

# 4. 实时观察进度和日志
```

**提示**: 首次运行建议设置 `limit=100` 进行测试，观察效果后再进行大规模爬取。

---

**版本**: v8.200
**创建时间**: 2026-02-17 23:11
