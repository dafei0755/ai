# 🚀 日志聚合系统启动指南

## 📋 快速开始

### 1. 启动 Loki 日志聚合栈

```bash
# 进入配置目录
cd docker

# 启动所有服务（Loki + Promtail + Grafana）
docker-compose -f docker-compose.logging.yml up -d

# 查看服务状态
docker-compose -f docker-compose.logging.yml ps

# 查看日志
docker-compose -f docker-compose.logging.yml logs -f
```

### 2. 访问 Grafana 可视化界面

- **地址**: http://localhost:3200
- **用户名**: `admin`
- **密码**: `admin123`

### 3. 配置日志查询

Grafana 会自动加载 Loki 数据源，可直接查询日志：

#### 查询示例

```logql
# 查询所有日志
{job="intelligent_project_analyzer"}

# 查询错误日志
{job="intelligent_project_analyzer", log_type="errors"}

# 查询认证相关日志
{job="intelligent_project_analyzer", log_type="auth"} |= "SSO"

# 查询特定模块的日志
{job="intelligent_project_analyzer"} |= "auth_routes"

# 查询慢请求（>1秒）
{job="intelligent_project_analyzer", log_type="performance"} | json | duration > 1000

# 查询 LLM 调用失败
{job="intelligent_project_analyzer", log_type="llm_metrics"} | json | success = false

# 查询告警日志
{job="intelligent_project_analyzer", log_type="alerts"}
```

### 4. 创建常用仪表板

#### 性能监控仪表板

1. 进入 Grafana → Dashboards → New → New Dashboard
2. 添加 Panel：
   - **API 响应时间**:
     ```logql
     avg_over_time({job="intelligent_project_analyzer", log_type="performance"} | json | unwrap duration [1m])
     ```
   - **慢请求数量**:
     ```logql
     count_over_time({job="intelligent_project_analyzer", log_type="performance"} | json | duration > 1000 [5m])
     ```
   - **LLM 调用耗时**:
     ```logql
     avg_over_time({job="intelligent_project_analyzer", log_type="llm_metrics"} | json | unwrap duration [1m]) by (model)
     ```

#### 错误监控仪表板

1. 添加 Panel：
   - **错误率**:
     ```logql
     sum(rate({job="intelligent_project_analyzer", log_type="errors"}[5m]))
     ```
   - **告警数量**:
     ```logql
     count_over_time({job="intelligent_project_analyzer", log_type="alerts"}[1h])
     ```

#### SSO 认证监控仪表板

1. 添加 Panel：
   - **认证请求数**:
     ```logql
     count_over_time({job="intelligent_project_analyzer", log_type="auth"} |= "get-token"[5m])
     ```
   - **认证失败数**:
     ```logql
     count_over_time({job="intelligent_project_analyzer", log_type="auth"} |= "Token无效"[5m])
     ```

---

## 📊 Loki 架构说明

```
项目日志文件
    ↓
Promtail (日志采集器)
    ↓
Loki (日志聚合服务器)
    ↓
Grafana (可视化查询界面)
```

### 组件说明

| 组件 | 端口 | 功能 | 数据持久化 |
|------|------|------|------------|
| Loki | 3100 | 日志聚合和查询 | `/loki` (Docker Volume) |
| Promtail | 9080 | 日志采集和推送 | 无状态 |
| Grafana | 3200 | 可视化界面 | `/var/lib/grafana` (Docker Volume) |

### 日志采集配置

Promtail 监听以下日志文件（只读模式）：
- `logs/server.log` → `{log_type="server"}`
- `logs/auth.log` → `{log_type="auth"}`
- `logs/errors.log` → `{log_type="errors"}`
- `logs/performance_metrics.jsonl` → `{log_type="performance"}`
- `logs/llm_metrics.jsonl` → `{log_type="llm_metrics"}`
- `logs/alerts.log` → `{log_type="alerts"}`

---

## 🛠️ 高级配置

### 修改日志保留期

编辑 `docker/loki-config.yaml`:

```yaml
limits_config:
  retention_period: 720h  # 默认 30 天，可修改为需要的时长
```

### 修改 Grafana 端口

编辑 `docker/docker-compose.logging.yml`:

```yaml
services:
  grafana:
    ports:
      - "3200:3000"  # 修改左侧端口号（宿主机端口）
```

### 添加告警通知

在 Grafana 中配置告警通知渠道：
1. Alerting → Contact points → New contact point
2. 选择通知方式：
   - Email
   - Webhook（钉钉/企业微信）
   - Slack
   - Discord

---

## 🔧 故障排查

### Promtail 无法连接 Loki

```bash
# 检查网络连通性
docker exec promtail curl http://loki:3100/ready

# 检查 Promtail 日志
docker-compose -f docker-compose.logging.yml logs promtail
```

### Grafana 无法看到日志

1. 检查 Loki 数据源状态：
   - Configuration → Data sources → Loki → Test
2. 检查 Promtail 是否正常推送：
   ```bash
   docker-compose -f docker-compose.logging.yml logs promtail | grep "push"
   ```

### 日志未被采集

1. 检查日志文件路径是否正确：
   ```bash
   docker exec promtail ls -la /var/log/app/
   ```
2. 检查 Promtail 配置中的 `__path__` 是否匹配

---

## 📈 性能优化

### 1. 限制日志采集频率

编辑 `docker/promtail-config.yaml`，为高频日志添加采样：

```yaml
scrape_configs:
  - job_name: performance
    pipeline_stages:
      - match:
          selector: '{log_type="performance"}'
          stages:
            - sampling:
                rate: 0.1  # 只采集 10%
```

### 2. 增加 Loki 内存限制

编辑 `docker/docker-compose.logging.yml`:

```yaml
services:
  loki:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

---

## 🚀 生产环境建议

### 1. 使用外部存储

将 Loki 数据存储到 S3/MinIO：

```yaml
storage_config:
  aws:
    s3: s3://your-bucket/loki
    region: us-east-1
```

### 2. 启用认证

```yaml
auth_enabled: true
```

### 3. 配置反向代理

使用 Nginx/Traefik 为 Grafana 添加 HTTPS 和域名：

```nginx
server {
    listen 443 ssl;
    server_name grafana.yourdomain.com;
    location / {
        proxy_pass http://localhost:3200;
    }
}
```

---

## 📚 相关文档

- **Loki 官方文档**: https://grafana.com/docs/loki/latest/
- **Promtail 配置参考**: https://grafana.com/docs/loki/latest/clients/promtail/configuration/
- **LogQL 查询语言**: https://grafana.com/docs/loki/latest/logql/

---

## 🆘 常见问题

### Q: Docker 启动失败，提示端口已被占用？

**A**: 修改 `docker-compose.logging.yml` 中的端口号，避免与其他服务冲突。

### Q: 日志文件路径如何配置？

**A**: 修改 `docker/promtail-config.yaml` 中的 `__path__` 字段，使用绝对路径或相对于容器内的路径。

### Q: 如何查看 Promtail 是否正常工作？

**A**: 
```bash
# 查看 Promtail 日志
docker-compose -f docker-compose.logging.yml logs promtail

# 检查 Promtail 状态
curl http://localhost:9080/ready
```

### Q: Grafana 仪表板可以导入导出吗？

**A**: 可以。在 Grafana 中：
- 导出：Dashboard → Settings → JSON Model → Copy to Clipboard
- 导入：Dashboards → Import → Paste JSON

---

**维护者**: AI Assistant  
**最后更新**: 2025-12-14
