# 管理后台数据库监控指南

**版本**: v7.200.1
**日期**: 2026-01-10
**适用场景**: 生产环境数据库健康监控与维护

---

## 📊 功能概述

管理后台集成了完善的数据库监控与维护功能，可通过 Web 界面实时监控数据库健康状态，并执行维护操作。

### 核心功能

| 功能 | 端点 | 说明 |
|------|------|------|
| 实时统计 | `GET /api/admin/database/stats` | 查看数据库大小、记录数、平均大小 |
| 健康检查 | `GET /api/admin/database/health` | 获取健康状态 + 告警 + 维护建议 |
| VACUUM压缩 | `POST /api/admin/database/vacuum` | 释放未使用空间，优化性能 |
| 归档旧会话 | `POST /api/admin/database/archive` | 导出旧会话到冷存储 |

---

## 🔐 访问权限

所有数据库监控 API 需要管理员权限：

```http
Authorization: Bearer <admin_token>
```

获取管理员令牌：
```bash
# 登录管理员账号
POST /api/auth/login
{
  "username": "admin",
  "password": "<admin_password>"
}

# 返回 access_token
```

---

## 📈 健康状态阈值

| 状态 | 阈值 | 图标 | 说明 | 建议操作 |
|------|------|------|------|----------|
| **HEALTHY** | < 10 GB | 🟢 | 数据库健康 | 无需维护 |
| **WARNING** | 10 - 50 GB | 🟡 | 建议维护 | 归档旧会话、执行VACUUM |
| **CRITICAL** | > 50 GB | 🔴 | 严重警告 | **立即归档、压缩、清理** |

---

## 🔧 API 使用示例

### 1. 获取数据库统计信息

**请求**:
```bash
curl -X GET "http://localhost:8000/api/admin/database/stats" \
  -H "Authorization: Bearer <admin_token>"
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "file_size_mb": 1571.71,
    "total_records": 192,
    "status_distribution": {
      "completed": 180,
      "failed": 12
    },
    "avg_size_mb": 8.19,
    "health_status": "WARNING",
    "thresholds": {
      "healthy_max_mb": 10240,
      "warning_max_mb": 51200
    }
  },
  "timestamp": "2026-01-10T21:15:00Z"
}
```

### 2. 数据库健康检查

**请求**:
```bash
curl -X GET "http://localhost:8000/api/admin/database/health" \
  -H "Authorization: Bearer <admin_token>"
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "health_status": "WARNING",
    "file_size_mb": 1571.71,
    "total_records": 192,
    "alerts": [
      {
        "level": "warning",
        "message": "数据库大小为 1571.71 MB，已超过10GB，建议维护"
      }
    ],
    "recommendations": [
      "考虑归档90天前的旧会话",
      "定期执行VACUUM压缩"
    ],
    "thresholds": {
      "healthy": "< 10 GB",
      "warning": "10 GB - 50 GB",
      "critical": "> 50 GB"
    }
  },
  "timestamp": "2026-01-10T21:15:30Z"
}
```

### 3. 执行 VACUUM 压缩

**请求**:
```bash
curl -X POST "http://localhost:8000/api/admin/database/vacuum" \
  -H "Authorization: Bearer <admin_token>"
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "size_before_mb": 1571.71,
    "size_after_mb": 1420.35,
    "freed_mb": 151.36,
    "duration_seconds": 5.23,
    "improvement_percent": 9.63
  },
  "timestamp": "2026-01-10T21:20:00Z"
}
```

### 4. 归档旧会话（模拟运行）

**请求**:
```bash
curl -X POST "http://localhost:8000/api/admin/database/archive?days=90&dry_run=true" \
  -H "Authorization: Bearer <admin_token>"
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "sessions_found": 45,
    "sessions_archived": 0,
    "output_file": null,
    "dry_run": true,
    "message": "模拟运行完成，实际未删除任何数据"
  },
  "timestamp": "2026-01-10T21:25:00Z"
}
```

### 5. 归档旧会话（实际执行）

**请求**:
```bash
curl -X POST "http://localhost:8000/api/admin/database/archive?days=90&dry_run=false" \
  -H "Authorization: Bearer <admin_token>"
```

**响应**:
```json
{
  "status": "success",
  "data": {
    "sessions_found": 45,
    "sessions_archived": 45,
    "output_file": "data/cold_storage/archived_sessions_20260110_212500.json",
    "dry_run": false,
    "freed_space_mb": 367.55,
    "message": "归档完成，已导出到冷存储"
  },
  "timestamp": "2026-01-10T21:25:30Z"
}
```

---

## 🎨 前端集成示例

### React 组件示例

```tsx
import React, { useState, useEffect } from 'react';
import { Alert, Card, Button, Progress } from 'antd';

interface DatabaseHealth {
  health_status: 'HEALTHY' | 'WARNING' | 'CRITICAL';
  file_size_mb: number;
  total_records: number;
  alerts: Array<{ level: string; message: string }>;
  recommendations: string[];
}

const DatabaseMonitor: React.FC = () => {
  const [health, setHealth] = useState<DatabaseHealth | null>(null);
  const [loading, setLoading] = useState(false);

  // 获取数据库健康状态
  const fetchHealth = async () => {
    try {
      const response = await fetch('/api/admin/database/health', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('admin_token')}`
        }
      });
      const data = await response.json();
      setHealth(data.data);
    } catch (error) {
      console.error('获取数据库健康状态失败:', error);
    }
  };

  // 执行 VACUUM 压缩
  const handleVacuum = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/admin/database/vacuum', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('admin_token')}`
        }
      });
      const data = await response.json();
      alert(`压缩完成！释放空间: ${data.data.freed_mb.toFixed(2)} MB`);
      await fetchHealth(); // 刷新健康状态
    } catch (error) {
      console.error('VACUUM失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    // 每30秒自动刷新
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  if (!health) return <div>加载中...</div>;

  // 健康状态配置
  const statusConfig = {
    'HEALTHY': { color: 'success', icon: '🟢', percent: 100 },
    'WARNING': { color: 'warning', icon: '🟡', percent: 60 },
    'CRITICAL': { color: 'error', icon: '🔴', percent: 30 },
  };

  const config = statusConfig[health.health_status];

  return (
    <Card title="数据库健康监控">
      {/* 健康状态指示器 */}
      <div style={{ marginBottom: 20 }}>
        <h3>
          {config.icon} 健康状态: {health.health_status}
        </h3>
        <Progress
          percent={config.percent}
          status={config.color as any}
          format={() => `${health.file_size_mb.toFixed(2)} MB`}
        />
      </div>

      {/* 告警信息 */}
      {health.alerts.map((alert, index) => (
        <Alert
          key={index}
          type={alert.level as any}
          message={alert.message}
          style={{ marginBottom: 10 }}
        />
      ))}

      {/* 维护建议 */}
      {health.recommendations.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h4>维护建议：</h4>
          <ul>
            {health.recommendations.map((rec, index) => (
              <li key={index}>{rec}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 维护操作按钮 */}
      <div style={{ marginTop: 20 }}>
        <Button
          type="primary"
          onClick={handleVacuum}
          loading={loading}
          disabled={health.health_status === 'HEALTHY'}
        >
          执行 VACUUM 压缩
        </Button>
        <Button
          style={{ marginLeft: 10 }}
          onClick={() => window.location.href = '/admin/database/archive'}
        >
          归档旧会话
        </Button>
      </div>

      {/* 统计信息 */}
      <div style={{ marginTop: 20, fontSize: 12, color: '#888' }}>
        总记录数: {health.total_records} |
        数据库大小: {health.file_size_mb.toFixed(2)} MB
      </div>
    </Card>
  );
};

export default DatabaseMonitor;
```

### Vue 组件示例

```vue
<template>
  <div class="database-monitor">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>数据库健康监控</span>
          <el-button @click="refresh" :icon="Refresh" circle></el-button>
        </div>
      </template>

      <!-- 健康状态 -->
      <div class="health-status">
        <h3>
          {{ statusConfig[health.health_status].icon }}
          健康状态: {{ health.health_status }}
        </h3>
        <el-progress
          :percentage="statusConfig[health.health_status].percent"
          :status="statusConfig[health.health_status].color"
        />
        <p>数据库大小: {{ health.file_size_mb.toFixed(2) }} MB</p>
      </div>

      <!-- 告警信息 -->
      <el-alert
        v-for="(alert, index) in health.alerts"
        :key="index"
        :type="alert.level"
        :title="alert.message"
        :closable="false"
        style="margin-bottom: 10px"
      />

      <!-- 维护建议 -->
      <div v-if="health.recommendations.length > 0" class="recommendations">
        <h4>维护建议：</h4>
        <ul>
          <li v-for="(rec, index) in health.recommendations" :key="index">
            {{ rec }}
          </li>
        </ul>
      </div>

      <!-- 操作按钮 -->
      <div class="actions">
        <el-button
          type="primary"
          @click="handleVacuum"
          :loading="loading"
          :disabled="health.health_status === 'HEALTHY'"
        >
          执行 VACUUM 压缩
        </el-button>
        <el-button @click="handleArchive">归档旧会话</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Refresh } from '@element-plus/icons-vue';

interface DatabaseHealth {
  health_status: 'HEALTHY' | 'WARNING' | 'CRITICAL';
  file_size_mb: number;
  total_records: number;
  alerts: Array<{ level: string; message: string }>;
  recommendations: string[];
}

const health = ref<DatabaseHealth>({
  health_status: 'HEALTHY',
  file_size_mb: 0,
  total_records: 0,
  alerts: [],
  recommendations: []
});

const loading = ref(false);
let refreshInterval: number;

const statusConfig = {
  'HEALTHY': { color: 'success', icon: '🟢', percent: 100 },
  'WARNING': { color: 'warning', icon: '🟡', percent: 60 },
  'CRITICAL': { color: 'danger', icon: '🔴', percent: 30 },
};

const fetchHealth = async () => {
  try {
    const response = await fetch('/api/admin/database/health', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('admin_token')}`
      }
    });
    const data = await response.json();
    health.value = data.data;
  } catch (error) {
    ElMessage.error('获取数据库健康状态失败');
  }
};

const refresh = () => {
  fetchHealth();
  ElMessage.success('已刷新');
};

const handleVacuum = async () => {
  loading.value = true;
  try {
    const response = await fetch('/api/admin/database/vacuum', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('admin_token')}`
      }
    });
    const data = await response.json();
    ElMessage.success(`压缩完成！释放空间: ${data.data.freed_mb.toFixed(2)} MB`);
    await fetchHealth();
  } catch (error) {
    ElMessage.error('VACUUM失败');
  } finally {
    loading.value = false;
  }
};

const handleArchive = () => {
  // 跳转到归档页面或打开对话框
  window.location.href = '/admin/database/archive';
};

onMounted(() => {
  fetchHealth();
  // 每30秒自动刷新
  refreshInterval = setInterval(fetchHealth, 30000);
});

onUnmounted(() => {
  clearInterval(refreshInterval);
});
</script>

<style scoped>
.database-monitor {
  max-width: 800px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.health-status {
  margin-bottom: 20px;
}

.recommendations {
  margin-top: 20px;
  padding: 10px;
  background-color: #f5f5f5;
  border-radius: 4px;
}

.actions {
  margin-top: 20px;
}
</style>
```

---

## ⏰ 自动化监控

### 定时检查脚本

创建 `scripts/monitor_database_health.py`:

```python
"""
数据库健康监控脚本
定期检查数据库健康状态，并在超过阈值时发送告警
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from intelligent_project_analyzer.services.session_archive_manager import get_archive_manager
from loguru import logger


async def check_and_alert():
    """检查数据库健康状态并发送告警"""
    try:
        manager = get_archive_manager()
        stats = await manager.get_database_stats()

        health_status = stats["health_status"]
        file_size_mb = stats["file_size_mb"]

        logger.info(f"📊 数据库健康状态: {health_status} ({file_size_mb:.2f} MB)")

        if health_status == "CRITICAL":
            logger.error(
                f"🔴 数据库告警: 大小 {file_size_mb:.2f} MB 超过50GB阈值！\n"
                f"建议立即执行维护:\n"
                f"  1. 归档旧会话: python scripts/database_maintenance.py --archive --days 90\n"
                f"  2. 执行压缩: python scripts/database_maintenance.py --vacuum\n"
                f"  3. 清理失败: python scripts/database_maintenance.py --clean-failed --days 90"
            )

            # TODO: 发送邮件/Slack/钉钉通知
            # await send_alert_email(...)

        elif health_status == "WARNING":
            logger.warning(
                f"🟡 数据库警告: 大小 {file_size_mb:.2f} MB 超过10GB\n"
                f"建议近期维护"
            )

        else:
            logger.success(f"🟢 数据库健康")

    except Exception as e:
        logger.error(f"❌ 健康检查失败: {e}")


async def main():
    """主函数"""
    while True:
        await check_and_alert()
        # 每小时检查一次
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
```

### 使用 Cron 定时任务（Linux）

```bash
# 编辑 crontab
crontab -e

# 每小时检查一次数据库健康状态
0 * * * * cd /path/to/project && python scripts/monitor_database_health.py
```

### 使用 Windows 任务计划

```powershell
# 创建任务计划（每小时运行）
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "scripts\monitor_database_health.py" -WorkingDirectory "D:\11-20\langgraph-design"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "DatabaseHealthMonitor" -Action $action -Trigger $trigger -Description "监控数据库健康状态"
```

---

## 📧 告警集成

### Email 通知示例

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


async def send_alert_email(stats: dict):
    """发送数据库告警邮件"""
    try:
        # 配置邮件服务器
        smtp_server = "smtp.example.com"
        smtp_port = 587
        sender_email = "alerts@example.com"
        sender_password = "your_password"
        recipient_email = "admin@example.com"

        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"🔴 数据库告警: {stats['health_status']}"

        # 邮件内容
        body = f"""
        <html>
          <body>
            <h2>数据库健康状态: {stats['health_status']}</h2>
            <p>数据库大小: <strong>{stats['file_size_mb']:.2f} MB</strong></p>
            <p>总记录数: {stats['total_records']}</p>
            <p>平均大小: {stats['avg_size_mb']:.2f} MB/记录</p>

            <h3>建议操作:</h3>
            <ul>
              <li>立即归档旧会话</li>
              <li>执行VACUUM压缩</li>
              <li>清理失败会话</li>
            </ul>

            <p>请登录管理后台查看详情: <a href="http://localhost:8000/admin/database">管理后台</a></p>
          </body>
        </html>
        """

        msg.attach(MIMEText(body, 'html'))

        # 发送邮件
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)

        logger.success("✅ 告警邮件发送成功")

    except Exception as e:
        logger.error(f"❌ 发送邮件失败: {e}")
```

### Slack/钉钉 Webhook 通知

```python
import aiohttp


async def send_slack_alert(stats: dict):
    """发送 Slack 告警"""
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

    message = {
        "text": f"🔴 数据库告警",
        "attachments": [{
            "color": "danger",
            "fields": [
                {"title": "健康状态", "value": stats['health_status'], "short": True},
                {"title": "数据库大小", "value": f"{stats['file_size_mb']:.2f} MB", "short": True},
                {"title": "总记录数", "value": str(stats['total_records']), "short": True},
            ]
        }]
    }

    async with aiohttp.ClientSession() as session:
        await session.post(webhook_url, json=message)


async def send_dingtalk_alert(stats: dict):
    """发送钉钉告警"""
    webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"

    message = {
        "msgtype": "markdown",
        "markdown": {
            "title": "数据库告警",
            "text": f"""
### 🔴 数据库告警

- **健康状态**: {stats['health_status']}
- **数据库大小**: {stats['file_size_mb']:.2f} MB
- **总记录数**: {stats['total_records']}

**建议操作**: 立即归档、压缩、清理
            """
        }
    }

    async with aiohttp.ClientSession() as session:
        await session.post(webhook_url, json=message)
```

---

## 🔍 故障排查

### 问题1: API返回403 Forbidden

**原因**: 未提供管理员令牌或令牌无效

**解决**:
```bash
# 1. 重新登录获取令牌
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# 2. 使用新令牌
export ADMIN_TOKEN="<new_token>"
```

### 问题2: 健康检查返回500错误

**原因**: 数据库文件被锁定或损坏

**解决**:
```bash
# 1. 停止服务
pkill -f "uvicorn.*server:app"

# 2. 检查数据库完整性
sqlite3 data/archived_sessions.db "PRAGMA integrity_check;"

# 3. 重启服务
python -m intelligent_project_analyzer.api.server
```

### 问题3: VACUUM失败

**原因**: 磁盘空间不足

**解决**:
```bash
# 检查磁盘空间
df -h

# 清理临时文件
rm -rf data/cold_storage/*.tmp

# 归档旧会话释放空间
python scripts/database_maintenance.py --archive --days 90
```

---

## 📚 相关文档

- [数据库性能优化报告](DATABASE_PERFORMANCE_OPTIMIZATION_v7.200.md)
- [CHANGELOG v7.200](CHANGELOG.md#v7200)
- [快速开始指南](QUICKSTART.md)
- [维护脚本使用](scripts/database_maintenance.py)

---

**作者**: GitHub Copilot
**最后更新**: 2026-01-10
**状态**: ✅ 生产可用
