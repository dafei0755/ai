# 📊 Grafana 日志监控快速上手指南

## 🎯 访问地址

- **URL**: http://localhost:3200
- **用户名**: `admin`
- **密码**: `admin123`

---

## 1️⃣ 查询日志（Explore 页面）

### 步骤
1. 点击左侧菜单的 **🔍 Explore** 图标
2. 确认数据源选择为 **Loki**
3. 在查询框输入 LogQL 语句
4. 点击右上角 **Run Query** 按钮

### 📝 常用 LogQL 查询示例

#### 基础查询

```logql
# 1. 查看所有日志（最近5分钟）
{job="intelligent_project_analyzer"}

# 2. 查看指定时间范围的日志
{job="intelligent_project_analyzer"} [1h]

# 3. 过滤包含特定关键词的日志
{job="intelligent_project_analyzer"} |= "error"
{job="intelligent_project_analyzer"} |= "SSO"
```

#### 按日志类型查询

```logql
# 1. 认证相关日志（SSO 调试推荐）
{job="intelligent_project_analyzer", log_type="auth"}

# 2. 错误日志
{job="intelligent_project_analyzer", log_type="errors"}

# 3. 性能日志（API 请求耗时）
{job="intelligent_project_analyzer", log_type="performance"}

# 4. LLM 调用日志
{job="intelligent_project_analyzer", log_type="llm_metrics"}

# 5. 告警日志
{job="intelligent_project_analyzer", log_type="alerts"}
```

#### 高级过滤

```logql
# 1. 查看 SSO Token 验证相关日志
{job="intelligent_project_analyzer", log_type="auth"} |= "Token" |= "验证"

# 2. 查看慢请求（超过 1 秒）
{job="intelligent_project_analyzer", log_type="performance"} | json | duration > 1000

# 3. 查看特定 API 路径的日志
{job="intelligent_project_analyzer"} |= "/api/auth/verify"

# 4. 排除某些日志（不包含 "健康检查"）
{job="intelligent_project_analyzer"} != "健康检查"

# 5. 正则表达式匹配
{job="intelligent_project_analyzer"} |~ "ERROR|CRITICAL"
```

#### LLM 性能分析

```logql
# 1. 查看 LLM 调用失败的情况
{job="intelligent_project_analyzer", log_type="llm_metrics"} | json | success = "false"

# 2. 查看特定模型的调用
{job="intelligent_project_analyzer", log_type="llm_metrics"} | json | model = "gpt-4o-2024-11-20"

# 3. 统计 LLM 平均响应时间（最近 5 分钟）
avg_over_time({job="intelligent_project_analyzer", log_type="llm_metrics"} | json | unwrap duration [5m])
```

#### 实时监控

```logql
# 1. 实时查看错误日志（自动刷新）
{job="intelligent_project_analyzer", log_type="errors"}
# 点击右上角的 "Live" 按钮启用实时刷新

# 2. 查看最近 10 条日志
{job="intelligent_project_analyzer"} | limit 10
```

---

## 2️⃣ 创建仪表板（Dashboard）

### 步骤
1. 点击左侧菜单的 **+ 图标** → **Dashboard**
2. 点击 **Add visualization**
3. 选择数据源 **Loki**
4. 输入查询语句
5. 选择可视化类型（表格、图表、统计等）
6. 点击 **Apply** 保存

### 📈 推荐仪表板面板

#### Panel 1: API 请求数量趋势

**查询**:
```logql
count_over_time({job="intelligent_project_analyzer", log_type="performance"}[5m])
```

**可视化**: Time series（时间序列图）

**用途**: 监控 API 请求量，发现流量峰值

---

#### Panel 2: 错误率统计

**查询**:
```logql
sum(rate({job="intelligent_project_analyzer", log_type="errors"}[5m]))
```

**可视化**: Stat（统计）

**用途**: 实时显示错误率，超过阈值时告警

---

#### Panel 3: 慢请求 Top 10

**查询**:
```logql
topk(10, 
  avg_over_time({job="intelligent_project_analyzer", log_type="performance"} 
  | json 
  | unwrap duration [5m]) by (path)
)
```

**可视化**: Bar chart（柱状图）

**用途**: 识别性能瓶颈 API

---

#### Panel 4: SSO 认证成功率

**查询成功**:
```logql
count_over_time({job="intelligent_project_analyzer", log_type="auth"} |= "Token验证成功" [5m])
```

**查询失败**:
```logql
count_over_time({job="intelligent_project_analyzer", log_type="auth"} |= "Token无效" [5m])
```

**可视化**: Time series（时间序列图，叠加两条曲线）

**用途**: 监控 SSO 登录健康度

---

#### Panel 5: 最近错误日志列表

**查询**:
```logql
{job="intelligent_project_analyzer", log_type="errors"}
```

**可视化**: Logs（日志面板）

**配置**: 显示最近 50 条，按时间倒序

**用途**: 快速查看最新错误

---

## 3️⃣ 时间范围选择

右上角的时间选择器可以设置查询范围：

- **Last 5 minutes** - 最近 5 分钟
- **Last 15 minutes** - 最近 15 分钟
- **Last 1 hour** - 最近 1 小时
- **Last 6 hours** - 最近 6 小时
- **Last 24 hours** - 最近 24 小时
- **Custom range** - 自定义时间段（精确到秒）

**提示**: 点击时间范围后可以使用日历选择具体时间段

---

## 4️⃣ 告警配置（Alert Rules）

### 创建告警规则

1. **进入告警页面**: 左侧菜单 → Alerting → Alert rules
2. **新建规则**: 点击 **New alert rule**
3. **配置条件**:
   - **名称**: `高错误率告警`
   - **查询**: 
     ```logql
     sum(rate({job="intelligent_project_analyzer", log_type="errors"}[5m]))
     ```
   - **条件**: `当值 > 5`（每分钟超过 5 个错误）
   - **持续时间**: `5m`（持续 5 分钟）
4. **通知渠道**: 配置邮件/Slack/钉钉等

### 常用告警场景

| 告警名称 | 查询条件 | 阈值 |
|---------|---------|------|
| API 异常高失败率 | `sum(rate({log_type="errors"}[5m]))` | > 10/min |
| 慢请求过多 | `count_over_time({log_type="performance"} \| json \| duration > 3000 [5m])` | > 20 |
| SSO 认证失败率 | `count_over_time({log_type="auth"} \|= "Token无效" [5m])` | > 5 |
| LLM 调用失败 | `count_over_time({log_type="llm_metrics"} \| json \| success = "false" [5m])` | > 3 |

---

## 5️⃣ 数据源配置（已自动配置）

Loki 数据源已通过 `grafana-datasources.yaml` 自动加载：

```yaml
apiVersion: 1
datasources:
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    isDefault: true
```

**验证数据源**:
1. 左侧菜单 → Configuration → Data sources
2. 确认 Loki 显示为绿色 ✅
3. 点击 **Test** 按钮，应显示 "Data source is working"

---

## 6️⃣ 实用技巧

### 🔍 快速过滤

在 Explore 页面的日志列表中：
- **点击字段值**: 自动添加到查询条件
- **点击字段前的 `=` 图标**: 精确匹配
- **点击字段前的 `≠` 图标**: 排除匹配

### 📊 切换可视化类型

查询结果右上角可以切换：
- **Logs**: 日志列表（默认）
- **Table**: 表格
- **Time series**: 时间序列图
- **Bar chart**: 柱状图

### ⏱️ 实时刷新

- 点击右上角的 **🔴 Live** 按钮启用实时刷新
- 或设置自动刷新间隔（5s / 10s / 30s / 1m）

### 💾 保存常用查询

1. 在 Explore 页面右上角点击 **⭐ Add to dashboard**
2. 选择目标仪表板
3. 下次直接打开仪表板查看

### 🔗 分享查询结果

1. 点击右上角的 **分享** 图标
2. 复制链接（包含查询和时间范围）
3. 发送给团队成员

---

## 7️⃣ 常见问题排查

### 问题1: 看不到日志数据

**原因**: Promtail 可能未正确采集日志

**解决**:
```bash
# 检查 Promtail 状态
docker logs promtail --tail 50

# 确认日志文件路径挂载正确
docker inspect promtail | grep -A 5 "Mounts"
```

### 问题2: 查询很慢

**原因**: 时间范围太大或日志量过多

**解决**:
- 缩小时间范围（从 24h → 1h）
- 添加更多过滤条件（log_type, 关键词）
- 使用 `| limit 100` 限制结果数量

### 问题3: Grafana 无法访问

**解决**:
```bash
# 检查容器状态
docker ps | grep grafana

# 重启容器
docker restart grafana

# 查看错误日志
docker logs grafana --tail 100
```

---

## 8️⃣ 快速调试 SSO 登录问题

**场景**: 用户反馈登录失败

**步骤**:

1. **查看认证日志**（Explore 页面）:
   ```logql
   {job="intelligent_project_analyzer", log_type="auth"} |= "SSO" [15m]
   ```

2. **过滤特定用户**:
   ```logql
   {job="intelligent_project_analyzer", log_type="auth"} |= "user_id=user123"
   ```

3. **查看 Token 验证详情**:
   ```logql
   {job="intelligent_project_analyzer", log_type="auth"} |= "Token验证"
   ```

4. **检查 API 调用链**:
   ```logql
   {job="intelligent_project_analyzer"} |= "/api/auth/verify" [15m]
   ```

**分析日志**:
- ✅ "Token验证成功" → 登录正常
- ❌ "Token无效" → 检查 JWT_SECRET 配置
- ❌ "Token已过期" → 检查 Token 有效期
- ❌ "用户不存在" → 检查 WordPress 用户数据

---

## 9️⃣ 性能监控最佳实践

### 创建性能监控仪表板

**步骤**:
1. 新建 Dashboard，命名为 "系统性能监控"
2. 添加以下面板：

**Panel 1: API 请求量趋势**
```logql
rate({job="intelligent_project_analyzer", log_type="performance"}[5m])
```

**Panel 2: 平均响应时间**
```logql
avg_over_time({job="intelligent_project_analyzer", log_type="performance"} | json | unwrap duration [5m])
```

**Panel 3: P95 响应时间**
```logql
quantile_over_time(0.95, {job="intelligent_project_analyzer", log_type="performance"} | json | unwrap duration [5m])
```

**Panel 4: 慢请求统计**
```logql
count_over_time({job="intelligent_project_analyzer", log_type="performance"} | json | duration > 1000 [5m])
```

**Panel 5: 错误率**
```logql
sum(rate({job="intelligent_project_analyzer", log_type="errors"}[5m])) 
/ 
sum(rate({job="intelligent_project_analyzer", log_type="performance"}[5m]))
```

---

## 🔟 导入预配置仪表板

### 使用官方模板

1. 点击左侧 **+ 图标** → **Import**
2. 输入仪表板 ID（从 https://grafana.com/grafana/dashboards/ 查找）
3. 推荐 ID:
   - **13639** - Loki Dashboard
   - **12611** - Loki & Promtail
4. 选择 Loki 数据源
5. 点击 **Import**

---

## 📚 参考资料

- **LogQL 官方文档**: https://grafana.com/docs/loki/latest/logql/
- **Grafana 仪表板示例**: https://grafana.com/grafana/dashboards/
- **Loki 最佳实践**: https://grafana.com/docs/loki/latest/best-practices/

---

## 🎯 下一步

- [x] 启动 Grafana（已完成）
- [ ] 创建第一个仪表板
- [ ] 配置告警规则
- [ ] 分享仪表板给团队成员
- [ ] 定期查看性能趋势

---

**文档版本**: v1.0  
**更新日期**: 2025-12-15  
**维护者**: AI Assistant
