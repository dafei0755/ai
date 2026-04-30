# 📊 日志系统高级功能快速验证

> **目的**: 快速验证4个高级日志功能是否正常工作  
> **预计时间**: 5-10分钟

---

## ✅ 验证清单

### 1. 日志压缩 ✅

**验证方法**:
```bash
# 手动触发日志轮转（模拟日志文件达到10MB）
# 方法1: 向日志文件写入大量数据
for i in {1..100000}; do echo "Test log entry $i" >> logs/server.log; done

# 方法2: 检查已有的压缩文件
ls -lh logs/*.zip
```

**预期结果**:
- 存在 `server.log.2025-12-14_10-30-45.zip` 类似的压缩文件
- 压缩文件大小约为原文件的 20-30%

**验证命令**:
```powershell
# Windows PowerShell
Get-ChildItem logs/*.zip | Select-Object Name, Length
```

---

### 2. 性能监控 ✅

**验证方法**:
```bash
# 发送几个测试请求
curl http://localhost:8000/api/analysis/start -X POST -H "Content-Type: application/json" -d '{"user_input": "测试"}'

# 查看性能日志
tail -20 logs/performance_metrics.jsonl
```

**预期结果**:
```json
{"timestamp": "2025-12-14T10:30:45.123456", "path": "/api/analysis/start", "method": "POST", "duration": 234.56, "status_code": 200}
```

**验证API**:
```bash
# 查询性能统计
curl http://localhost:8000/api/metrics/performance/summary?hours=1

# 预期响应
{
  "total_requests": 5,
  "avg_duration": 234.56,
  "max_duration": 500.00,
  "min_duration": 100.00,
  "slow_requests": 0,
  "error_rate": 0,
  "time_range_hours": 1
}
```

**验证慢请求检测**:
```bash
# 发送一个慢请求（访问耗时较长的端点）
curl http://localhost:8000/api/analysis/report/long_session_id

# 查看日志是否有慢请求警告
tail -f logs/server.log | grep "慢请求"

# 预期输出
⚠️ 慢请求: GET /api/analysis/report/long_session_id - 1234.56ms
```

---

### 3. 告警系统 ✅

**验证方法（手动触发错误）**:

#### 方法1: Python 脚本
```python
# test_alert.py
from loguru import logger

# 配置日志（与 server.py 相同）
logger.add("logs/errors.log", level="ERROR", encoding="utf-8")

# 触发15次错误（超过1分钟10次阈值）
for i in range(15):
    logger.error(f"测试告警系统 - 错误 {i+1}")
    import time
    time.sleep(0.1)
```

```bash
python test_alert.py
```

#### 方法2: API 端点（如果有测试端点）
```bash
# 多次调用错误端点
for i in {1..15}; do
  curl http://localhost:8000/api/test-error
  sleep 0.1
done
```

**预期结果**:

1. **告警日志** (`logs/alerts.log`):
```json
{"timestamp": "2025-12-14T10:35:00", "message": "🚨 告警: 1分钟内出现10次错误", "error_detail": "测试告警系统 - 错误 10"}
```

2. **主日志** (`logs/server.log`):
```
2025-12-14 10:35:00 | ERROR | alert_monitor:_trigger_alert:123 - 🚨 告警: 1分钟内出现10次错误
```

3. **Webhook 通知**（如果已配置）:
- 钉钉/企业微信收到消息

**验证API**:
```bash
# 查询告警统计
curl http://localhost:8000/api/metrics/alerts/stats?hours=1

# 预期响应
{
  "total_alerts": 1,
  "alerts_per_hour": 1.0,
  "recent_trend": [0, 0, 0, ..., 1, 0],
  "time_range_hours": 1
}

# 查询最近告警
curl http://localhost:8000/api/metrics/alerts/recent?limit=5
```

---

### 4. Loki 日志聚合 ✅

**验证方法**:

#### 步骤1: 启动 Loki 栈
```bash
cd docker
docker-compose -f docker-compose.logging.yml up -d

# 等待启动完成（约30秒）
sleep 30

# 检查服务状态
docker-compose -f docker-compose.logging.yml ps
```

**预期输出**:
```
NAME         IMAGE                    STATUS
grafana      grafana/grafana:10.2.3   Up
loki         grafana/loki:2.9.3       Up
promtail     grafana/promtail:2.9.3   Up
```

#### 步骤2: 检查 Promtail 采集
```bash
# 查看 Promtail 日志
docker-compose -f docker-compose.logging.yml logs promtail | grep "push"

# 预期看到推送日志
level=info msg="Successfully sent batch" entries=50
```

#### 步骤3: 访问 Grafana
1. 打开浏览器访问: http://localhost:3200
2. 登录:
   - 用户名: `admin`
   - 密码: `admin123`
3. 进入 Explore 页面
4. 选择 Loki 数据源
5. 输入查询:
   ```logql
   {job="intelligent_project_analyzer"}
   ```
6. 点击 Run Query

**预期结果**:
- 看到项目的日志记录
- 可以按 `log_type` 标签过滤（server、auth、errors 等）

#### 步骤4: 测试查询

```logql
# 查询错误日志
{job="intelligent_project_analyzer", log_type="errors"}

# 查询性能指标
{job="intelligent_project_analyzer", log_type="performance"} | json

# 查询慢请求
{job="intelligent_project_analyzer", log_type="performance"} | json | duration > 1000

# 查询告警
{job="intelligent_project_analyzer", log_type="alerts"}
```

---

## 🔍 综合验证场景

### 场景: 完整流程测试

**步骤1**: 启动后端和 Loki
```bash
# 终端1: 启动后端
python intelligent_project_analyzer/api/server.py

# 终端2: 启动 Loki
cd docker
docker-compose -f docker-compose.logging.yml up -d
```

**步骤2**: 生成一些活动
```bash
# 发送正常请求
curl http://localhost:8000/api/analysis/start -X POST -H "Content-Type: application/json" -d '{"user_input": "设计一个智能家居系统"}'

# 发送一些错误请求（触发告警）
for i in {1..15}; do
  curl http://localhost:8000/api/invalid-endpoint
  sleep 0.1
done
```

**步骤3**: 查看结果

1. **性能日志**:
```bash
tail -20 logs/performance_metrics.jsonl
```

2. **告警日志**:
```bash
tail -10 logs/alerts.log
```

3. **Grafana 查询**:
   - 访问 http://localhost:3200
   - 查询: `{job="intelligent_project_analyzer"}`

4. **API 统计**:
```bash
# 性能统计
curl http://localhost:8000/api/metrics/performance/summary?hours=1 | jq

# LLM 统计
curl http://localhost:8000/api/metrics/llm/summary?hours=1 | jq

# 告警统计
curl http://localhost:8000/api/metrics/alerts/stats?hours=1 | jq
```

**预期结果**:
- ✅ 性能日志记录所有请求
- ✅ 告警系统触发（1分钟10次错误）
- ✅ Grafana 显示所有日志
- ✅ API 返回正确统计数据

---

## 🚨 常见问题

### Q1: 性能日志为空？

**可能原因**:
- 中间件未正确加载
- 没有发送请求

**解决方法**:
```bash
# 检查中间件是否加载
tail -f logs/server.log | grep "performance_monitoring_middleware"

# 发送测试请求
curl http://localhost:8000/docs
```

### Q2: 告警未触发？

**可能原因**:
- 错误数量未达到阈值
- `alert_monitor` 未启动

**解决方法**:
```bash
# 检查告警监控线程
tail -f logs/server.log | grep "告警监控"

# 手动触发更多错误
for i in {1..20}; do
  python -c "from loguru import logger; logger.add('logs/errors.log', level='ERROR'); logger.error('测试')"
done
```

### Q3: Promtail 无法采集日志？

**可能原因**:
- 日志文件路径不正确
- 容器卷挂载失败

**解决方法**:
```bash
# 检查容器内路径
docker exec promtail ls -la /var/log/app/

# 检查 Promtail 日志
docker-compose -f docker-compose.logging.yml logs promtail | grep "error"

# 重启 Promtail
docker-compose -f docker-compose.logging.yml restart promtail
```

---

## ✅ 验证完成标准

**所有功能正常的标志**:

- [ ] `logs/*.zip` 存在压缩文件
- [ ] `logs/performance_metrics.jsonl` 有请求记录
- [ ] `logs/llm_metrics.jsonl` 有 LLM 调用记录（如果有 LLM 请求）
- [ ] `logs/alerts.log` 有告警记录（触发错误后）
- [ ] Grafana 可以查询到日志
- [ ] `/api/metrics/performance/summary` 返回统计数据
- [ ] `/api/metrics/alerts/stats` 返回告警统计

**全部通过 → 日志系统高级功能部署成功！** 🎉

---

**维护者**: AI Assistant  
**最后更新**: 2025-12-14
