# 📋 后端日志系统使用指南

> **快速定位问题，高效调试 SSO 和系统错误**

---

## 📁 日志文件说明

### 日志目录：`logs/`

| 文件 | 内容 | 大小限制 | 保留时间 | 推荐场景 |
|------|------|---------|---------|---------|
| **`server.log`** | 所有服务器日志（INFO及以上） | 10 MB | 10 天 | ✅ 全局追踪、性能分析 |
| **`auth.log`** | 认证/SSO/Token 相关（DEBUG级别） | 5 MB | 7 天 | 🔐 **SSO调试首选** |
| **`errors.log`** | 仅错误日志（ERROR及以上） | 5 MB | 30 天 | ❌ 问题排查、事故分析 |
| `backend_*.log` | 启动脚本完整输出 | 无限制 | 手动清理 | 📝 完整终端记录 |

---

## 🚀 快速开始

### 1. VS Code 查看（推荐 - 无乱码）

```
文件 → 打开文件 → 选择 logs/auth.log
```

**优势**：
- ✅ 自动 UTF-8 编码，中文正常显示
- ✅ 语法高亮（安装 Log File Highlighter 插件）
- ✅ 搜索功能强大（Ctrl+F）

---

### 2. PowerShell 实时监控

#### 方式A：主日志（所有内容）
```powershell
# 设置 UTF-8 编码（避免乱码）
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 实时查看最新100行
Get-Content logs\server.log -Wait -Tail 100 -Encoding UTF8
```

#### 方式B：SSO 调试日志（推荐）
```powershell
# 只看认证相关
Get-Content logs\auth.log -Wait -Tail 50 -Encoding UTF8
```

#### 方式C：错误日志
```powershell
# 只看错误
Get-Content logs\errors.log -Tail 50 -Encoding UTF8
```

---

## 🔍 常见调试场景

### 场景1：SSO 登录失败

**问题**：用户无法登录或 Token 验证失败

**调试步骤**：
```powershell
# 1. 查看认证日志
Get-Content logs\auth.log -Tail 100 -Encoding UTF8

# 2. 搜索用户名
Get-Content logs\auth.log | Select-String "username" -Context 3

# 3. 查看 Token 验证过程
Get-Content logs\auth.log | Select-String "Token|验证" -Context 2
```

**关键日志示例**：
```log
🔐 开始验证 Token (前20字符): eyJhbGciOiJIUzI1NiIsI...
📦 Token payload 结构: ['iss', 'iat', 'exp', 'data']
✅ SSO Token 验证成功 (WordPress SSO 格式): YOUR_WORDPRESS_USERNAME
📋 用户数据: ID=123, Email=user@example.com, Roles=['subscriber']
```

---

### 场景2：系统启动失败

**问题**：后端无法启动或组件初始化失败

**调试步骤**：
```powershell
# 1. 查看完整启动日志
Get-Content logs\server.log | Select-String "初始化|启动|失败" -Encoding UTF8

# 2. 查看错误日志
Get-Content logs\errors.log -Tail 50 -Encoding UTF8

# 3. 查看 Redis 连接状态
Get-Content logs\server.log | Select-String "Redis" -Context 2
```

**关键日志示例**：
```log
✅ Redis 连接成功: redis://localhost:6379/0
✅ FollowupHistoryManager 已初始化
✅ Playwright 浏览器池初始化成功
❌ WPCOM Member 会员信息路由加载失败: cannot import name...
```

---

### 场景3：API 调用异常

**问题**：前端请求返回 500 错误

**调试步骤**：
```powershell
# 1. 查看错误日志（包含堆栈信息）
Get-Content logs\errors.log | Select-String "API|Traceback" -Context 5

# 2. 查看最近1小时的错误
$now = Get-Date
$oneHourAgo = $now.AddHours(-1).ToString("yyyy-MM-dd HH:")
Get-Content logs\errors.log | Select-String $oneHourAgo -Context 3

# 3. 按请求路径筛选
Get-Content logs\server.log | Select-String "/api/auth/verify" -Context 2
```

---

## 📊 日志级别说明

| 级别 | 图标 | 含义 | 记录位置 |
|------|------|------|---------|
| **DEBUG** | 🔍 | 调试信息（Token payload、参数详情） | `auth.log` |
| **INFO** | ✅ | 正常操作成功 | `server.log` |
| **WARNING** | ⚠️ | 非致命问题（可选功能加载失败） | `server.log` |
| **ERROR** | ❌ | 错误需关注 | `server.log` + `errors.log` |

---

## 🛠️ 高级技巧

### 1. 按时间段筛选

```powershell
# 查看今天下午8点30-40分的日志
Get-Content logs\server.log | Select-String "2025-12-13 20:3[0-9]"

# 查看最近5分钟的日志
$time = (Get-Date).AddMinutes(-5).ToString("yyyy-MM-dd HH:mm")
Get-Content logs\server.log | Select-String $time -Context 5
```

### 2. 多关键词组合搜索

```powershell
# SSO 相关的错误
Get-Content logs\server.log | Select-String "SSO|Token|认证" | Select-String "ERROR|❌"

# 特定用户的操作
Get-Content logs\auth.log | Select-String "YOUR_WORDPRESS_USERNAME"
```

### 3. 导出筛选结果

```powershell
# 导出今天所有错误到文件
Get-Content logs\errors.log | Out-File "debug_errors_$(Get-Date -Format 'yyyyMMdd').txt"

# 导出 SSO 相关日志
Get-Content logs\auth.log | Select-String "SSO" | Out-File "sso_debug.txt"
```

### 4. 实时彩色输出（需要插件）

```powershell
# 安装 PSColor 模块
Install-Module PSColor -Scope CurrentUser

# 彩色显示日志
Get-Content logs\server.log -Wait -Tail 50 | Out-Host
```

---

## 🐛 故障排查流程

### SSO 登录问题

1. **检查 WordPress 插件状态**
   - 查看 `server.log` 中的 `WordPress JWT 认证路由已注册`
   - 确认无加载失败警告

2. **验证 Token 签发**
   - 查看 `auth.log` 中的 `开始验证 Token`
   - 检查 `Token payload 结构`

3. **确认用户数据格式**
   - 查看 `WordPress SSO 格式` 或 `Python 格式`
   - 确认 `用户数据` 日志包含正确的 ID/Email

4. **排查验证失败**
   - 查看 `errors.log` 中的 `Token 验证失败`
   - 检查是否有 JWT 签名错误

---

## 📌 最佳实践

### 开发时

1. **启动后端前清空旧日志**
   ```powershell
   Clear-Content logs\server.log
   Clear-Content logs\auth.log
   Clear-Content logs\errors.log
   ```

2. **开启实时监控**
   ```powershell
   # 新开 PowerShell 窗口
   Get-Content logs\auth.log -Wait -Tail 100 -Encoding UTF8
   ```

3. **测试后检查日志**
   - 成功：确认有 `✅` 标记
   - 失败：查找 `❌` 标记和堆栈信息

### 生产环境

1. **定期检查错误日志**
   ```bash
   # 每天检查是否有新错误
   tail -n 100 logs/errors.log
   ```

2. **监控日志大小**
   ```powershell
   Get-ChildItem logs\*.log | Select-Object Name, @{Name="Size(MB)";Expression={[Math]::Round($_.Length/1MB,2)}}
   ```

3. **备份重要日志**
   ```powershell
   # 每月备份
   Compress-Archive -Path logs\*.log -DestinationPath "logs_backup_$(Get-Date -Format 'yyyyMM').zip"
   ```

---

## ❓ 常见问题

### Q1：PowerShell 显示乱码怎么办？

**A**：在查看日志前执行以下命令设置 UTF-8 编码：
```powershell
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

或直接在 VS Code 中打开日志文件（推荐）。

---

### Q2：如何查看更详细的调试信息？

**A**：修改 `intelligent_project_analyzer/api/server.py` 的日志级别：
```python
logger.add(..., level="DEBUG")  # 改为 DEBUG
```

重启后端，所有 `logger.debug()` 信息都会记录。

---

### Q3：日志文件太大怎么办？

**A**：系统会自动轮转（10MB/5MB），但可以手动清理：
```powershell
# 只保留最新1000行
Get-Content logs\server.log -Tail 1000 | Set-Content logs\server.log
```

---

### Q4：如何关闭某个日志文件？

**A**：注释掉 `server.py` 中对应的 `logger.add()` 行并重启后端。

---

## 🔗 相关文档

- [README.md](README.md) - 项目主文档
- [SSO_DEPLOYMENT_FAILURE.md](SSO_DEPLOYMENT_FAILURE.md) - SSO 部署失败报告
- [DEVELOPMENT_RULES.md](.github/DEVELOPMENT_RULES.md) - 开发规范

---

**维护者**：AI Assistant  
**最后更新**：2025-12-13
