# 🎯 管理后台监控面板修复指南

## 问题诊断

### 1. 仪表板显示全 0 数据
**原因**：`performance_monitor.py` 缺少 `get_stats_summary()` 方法

**已修复**：✅ 添加了完整的统计方法：
- `get_stats_summary()` - 获取摘要统计（总请求数、平均响应时间等）
- `get_slow_requests()` - 获取慢请求列表
- `get_detailed_stats()` - 获取详细性能统计

### 2. Grafana 监控面板无法访问
**原因**：Docker Compose 日志服务未启动

**解决方案**：运行启动脚本

---

## 🚀 快速修复步骤

### 步骤 1：启动 Grafana 日志监控服务

```cmd
# 运行启动脚本（一键启动所有服务）
start_grafana.bat
```

**或手动启动：**
```cmd
cd docker
docker-compose -f docker-compose.logging.yml up -d
```

**验证服务状态：**
```cmd
docker-compose -f docker-compose.logging.yml ps
```

应该看到 3 个服务运行中：
- ✅ loki (端口 3100)
- ✅ promtail
- ✅ grafana (端口 3200)

---

### 步骤 2：重启后端服务器

```cmd
# Ctrl+C 停止旧服务，然后重新启动
python -B scripts\run_server_production.py
```

**验证修复**：
- 启动后访问几个 API 接口（如主页、会话列表等）
- 后端日志应显示：
  ```
  ✅ CPU: 15.2%
  ✅ 内存: 45.6%
  ✅ 磁盘: 60.3%
  ✅ 活跃会话: 11
  ✅ 性能统计: {'total_requests': 42, ...}
  ```

---

### 步骤 3：访问管理后台

1. **访问仪表板**：http://localhost:3000/admin/dashboard
   - 应该看到实时的 CPU、内存、磁盘使用率
   - 性能指标显示请求数、响应时间等

2. **访问 Grafana 监控**：http://localhost:3000/admin/monitoring
   - 应该看到嵌入的 Grafana 面板
   - 可以点击"打开 Grafana"访问完整 UI

---

## 📊 功能说明

### 系统监控仪表板 (`/admin/dashboard`)
显示实时系统指标：
- **系统资源**：CPU、内存、磁盘使用率
- **会话统计**：活跃会话数
- **性能指标**：总请求数、平均响应时间、请求/分钟、错误数
- **自动刷新**：每 60 秒自动更新数据

### Grafana 监控面板 (`/admin/monitoring`)
提供专业日志分析和可视化：
- **API 性能监控**：请求量、响应时间趋势图
- **LLM 调用统计**：模型调用次数、Token 消耗
- **完整 Grafana UI**：支持自定义仪表板、查询日志

---

## 🔧 配置文件

### Grafana 匿名访问配置
文件：`docker/docker-compose.logging.yml`

```yaml
grafana:
  environment:
    # ✅ 已启用匿名访问和嵌入
    - GF_AUTH_ANONYMOUS_ENABLED=true
    - GF_AUTH_ANONYMOUS_ORG_NAME=Main Org.
    - GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer
    - GF_SECURITY_ALLOW_EMBEDDING=true
    - GF_SECURITY_X_FRAME_OPTIONS=SAMEORIGIN
```

### 环境变量
文件：`frontend-nextjs/.env.local`（可选）

```env
# Grafana URL（默认值）
NEXT_PUBLIC_GRAFANA_URL=http://localhost:3200
```

---

## ❓ 常见问题

### Q1: 仪表板数据仍然为 0？
**检查后端日志**：
- 如果看到 `⚠️ CPU监控失败: SystemError`，说明 `psutil` 在 Windows/Python 3.13 上有兼容性问题
- 解决方案：升级 `psutil` 或降级 Python 版本

```cmd
pip install --upgrade psutil
```

### Q2: Grafana 面板显示"连接被拒绝"？
**确认服务状态**：
```cmd
docker ps | findstr grafana
```

如果未运行，执行：
```cmd
start_grafana.bat
```

### Q3: 如何访问 Grafana 管理员账号？
**默认凭据**：
- URL: http://localhost:3200
- 用户名: `admin`
- 密码: `admin123`

首次登录会提示修改密码（可跳过）。

### Q4: 如何查看应用日志？
**方法 1：直接访问日志文件**
```
logs/performance_metrics.jsonl  # API 性能日志
logs/llm_metrics.jsonl          # LLM 调用日志
```

**方法 2：通过 Grafana Explore**
1. 访问 http://localhost:3200
2. 点击左侧"Explore"图标
3. 选择数据源"Loki"
4. 输入查询：`{job="intelligent-project-analyzer"}`

---

## 🎉 验收标准

修复成功的标志：

✅ **仪表板页面**：
- CPU、内存、磁盘显示实际百分比（非 0%）
- 活跃会话数显示正确数量
- 总请求数随着使用递增
- 平均响应时间显示为毫秒值（如 45.23ms）

✅ **Grafana 监控页面**：
- "API 性能监控"面板显示图表（非空白）
- "LLM 调用统计"面板显示图表
- 点击"打开 Grafana"能成功跳转

✅ **后端日志**：
- 访问仪表板 API 时显示 `✅ CPU: XX%` 等成功日志
- 无 `SystemError` 或 `AttributeError`

---

## 📚 相关文档

- [Grafana 快速入门](../docs/GRAFANA_QUICK_START.md)
- [日志系统配置](../docs/LOGGING_VERIFICATION_GUIDE.md)
- [性能监控最佳实践](../docs/LOGGING_ADVANCED_FEATURES.md)

---

**最后更新**：2026-01-03
**适用版本**：v7.130+
