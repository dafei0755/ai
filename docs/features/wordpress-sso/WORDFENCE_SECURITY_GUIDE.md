# 🛡️ Wordfence 安全配置指南

> **专为 WordPress + Next.js SSO 集成优化**
> **更新日期**: 2025-12-15
> **适用版本**: Wordfence 7.11+

---

## 📋 配置概览

### 当前状态诊断

根据截图，您的当前配置：

| 防火墙组件 | 当前状态 | 目标状态 | 优先级 |
|-----------|---------|---------|--------|
| Web 应用防火墙 | 学习模式 (55%) | 启用并保护 (100%) | 🔴 高 |
| 防火墙规则：社区 | 70% | 100% | 🟡 中 |
| 实时 IP 黑名单 | 启用 (0%) | 启用 (100%) | 🟢 低 |
| 强力防护 | 100% ✅ | 100% | ✅ 已优化 |

---

## 1️⃣ Web 应用防火墙（WAF）

### 推荐设置

**学习模式 → 保护模式切换策略**:

```
阶段1: 学习模式（7-14天）
  ↓ 监控并调整白名单
阶段2: 启用并保护（生产环境）
  ↓ 持续监控误报
阶段3: 定期审查（每月）
```

### 切换清单

- [ ] **运行学习模式至少 7 天**
- [ ] **检查"实时流量"中的误拦截记录**
- [ ] **配置 Next.js API 白名单**（见第 3 节）
- [ ] **测试 SSO 登录流程完整性**
- [ ] **备份当前 Wordfence 设置**
- [ ] **切换到"启用并保护"**
- [ ] **测试所有关键功能（登录、分析、文件上传）**

---

## 2️⃣ 高级防火墙选项

### ✅ 推荐启用的选项

#### 密码与用户安全

```yaml
✅ 强制使用密码强度: 启用
   理由: 防止弱密码攻击
   影响: 用户注册/修改密码时强制复杂度要求

✅ 禁用 WordPress 在登录错误时显示用户名: 启用
   理由: 防止用户名枚举
   影响: 登录失败时不显示"用户名不存在"

✅ 屏蔽用户注册 [admin] 用户名: 启用
   理由: 防止攻击者注册 admin/administrator 等敏感账户
   影响: 注册时禁止使用 admin 相关用户名

✅ 防止遮蔽 [/author-N] 挂钩，oEmbed API，WordPress REST API 和 WordPress XML 站点地图发现用户名: 启用
   理由: 阻止通过 REST API 和 URL 泄露用户名
   影响: 限制某些 REST API 端点（需测试兼容性）
```

#### REST API 安全

```yaml
⚠️ 防止遮蔽 REST API（需谨慎）:
   建议: 🔴 不要完全阻止，使用自定义规则
   原因: Next.js SSO 依赖 /wp-json/nextjs-sso/v1/* 端点

   解决方案: 添加白名单路径（见第 3 节）
```

#### 应用程序密码

```yaml
✅ 禁用 WordPress 应用程序密码: 启用
   前提: 如果您不使用 WordPress 移动应用或第三方 App
   影响: 禁用 Application Passwords 功能

   ⚠️ 如果使用移动应用，请保持禁用此选项
```

#### XML-RPC 防护

```yaml
✅ 禁用 XML-RPC（pingbacks/trackbacks）:
   推荐: 启用禁用（除非需要远程发布）
   理由: XML-RPC 是常见攻击向量
   影响: 禁止 pingback、trackback 和远程发布功能
```

---

### ⚠️ 需要谨慎配置的选项

#### 用户代理/Referer 验证

```yaml
❌ 屏蔽虚假 Google 蜘蛛: 不推荐
   理由: 可能误杀合法搜索引擎

   替代方案: 使用 Wordfence 的爬虫速率限制
```

---

## 3️⃣ SSO 集成专项配置

### 🔥 关键：白名单 Next.js API 路径

**问题**: Wordfence 可能拦截 SSO Token 验证请求

**解决方案**: 添加白名单规则

#### 步骤1: 添加白名单路径

在"高级防火墙选项" → "允许屏蔽访问的 URL 或 IP" 中添加：

```
# Next.js SSO API 端点
/wp-json/nextjs-sso/v1/get-token
/wp-json/nextjs-sso/v1/verify-user

# Next.js 回调页面
/js

# 可选：如果需要保护 WordPress 管理后台访问
/wp-admin/admin-ajax.php
```

**格式示例**:

```
路径: /wp-json/nextjs-sso/v1/get-token
Param Type: URL Path
参数名称: （留空）
操作: 添加
```

#### 步骤2: 添加 Next.js 服务器 IP 白名单

如果 Next.js 运行在固定 IP（生产环境），添加到白名单：

```
服务器 IP: 你的Next.js服务器IP
原因: Next.js SSO 集成
操作: 立即解除阻止并添加到白名单
```

**本地开发环境**:
```
127.0.0.1/24
::1 (IPv6 本地)
```

#### 步骤3: 测试 SSO 流程

完成白名单配置后，测试以下流程：

- [ ] WordPress 用户登录 → 跳转到 `/js` → 获取 Token
- [ ] Next.js 调用 `/wp-json/nextjs-sso/v1/get-token` → 返回 200
- [ ] Next.js 调用 `/wp-json/nextjs-sso/v1/verify-user` → 返回用户信息
- [ ] 检查 Wordfence "实时流量" → 确认无误拦截

---

## 4️⃣ 强力防护（Brute Force Protection）

### 当前配置（100% ✅）

从截图看，强力防护已启用。以下是推荐配置：

```yaml
✅ 启用强力防护: 开启

在登录失败次数达到: 20
  推荐: 10-20（过低会误锁正常用户）

在登录失败次数达到后封锁: 20
  推荐: 20-30（防止短时间内大量尝试）

在多长时间内的达到失败次数: 4 小时
  推荐: 1-4 小时

用户被锁定的时长: 4 小时
  推荐: 4-24 小时（根据业务需求）

✅ 防止使用被已泄漏密码的密码登录: 启用
  理由: 阻止使用已知泄露密码（如 123456）

✅ 立即锁定无效用户名: 启用
  理由: 用户名不存在直接封锁（防止枚举）
  ⚠️ 需确保不影响正常用户输错用户名

❌ 立即解除管理员对其密码的锁定: 不推荐
  理由: 管理员账户应遵守锁定规则
```

### 🔥 重要：排除 SSO 相关 IP

如果 Next.js 服务器频繁调用 API，可能触发速率限制：

**解决方案**: 在强力防护中排除 Next.js 服务器 IP

```
立即解除管理员对其密码的锁定: 启用
按 Enter 键添加用户名: （留空，不使用用户名白名单）

立即解除密码锁定的用户的 IP: 启用
按 Enter 键添加用户名: （输入 Next.js 服务器 IP）
```

---

## 5️⃣ 速率限制（Rate Limiting）

### 推荐配置

在"强力防护" → "速率限制"中：

```yaml
✅ 如果任何人单次访问某个页面或帖子的次数过快就将其阻止: 启用

在登录失败次数达到: 20
  推荐: 根据业务调整

  # API 密集型应用建议更宽松
  - 普通网站: 10-20
  - API 应用: 30-50
  - Next.js SSO: 50-100（因为频繁验证 Token）

在多长时间内的达到失败次数: 4 小时
  推荐: 1-5 分钟

用户被锁定的时长: 4 小时
  推荐: 5-30 分钟（短期封锁）
```

### 🔥 API 端点速率限制豁免

**问题**: SSO Token 验证可能触发速率限制

**解决方案**: 创建自定义规则

在"允许的 URL" 或 "Web 应用防火墙" → "Rules" 中添加：

```
规则类型: 速率限制豁免
路径: /wp-json/nextjs-sso/v1/*
描述: Next.js SSO API 豁免
```

---

## 6️⃣ 黑名单与白名单

### IP 黑名单管理

**当前**: 实时 IP 黑名单启用 (0%)

```yaml
✅ 如果访问者被实时 IP 黑名单列出，就不允许其访问: 启用
  理由: 利用 Wordfence 全球威胁情报网络

✅ 防止使用代理服务器的访问者: 谨慎启用
  ⚠️ 可能误杀使用 VPN 的正常用户
  推荐: 仅在遭受攻击时临时启用
```

### 列入白名单的服务

从截图中看到您已勾选：

```yaml
✅ Sucuri
✅ Facebook
✅ Uptime Robot
✅ StatusCake
✅ Seznam Search Engine
✅ Google Search Engine

建议补充:
□ ManageWP (如果使用远程管理)
□ 您自己的监控服务 IP
```

### 自定义白名单

**场景1: 本地开发环境**

```
立即解除屏蔽访问的 URL 或 IP:

# 本地开发
127.0.0.1
::1
localhost

# Next.js 开发服务器端口
127.0.0.1:3000
127.0.0.1:3001
```

**场景2: 生产环境**

```
# Next.js 生产服务器
你的服务器公网IP

# 团队成员 IP（可选）
办公室固定IP/32
```

---

## 7️⃣ 规则管理

### 查看现有规则

在截图底部"规则"部分，您已启用的规则：

```
✅ whitelist - Whitelisted URL
✅ lfi - Slider Revolution <= 4.1.4 - Directory Traversal
✅ sqli - SQL Injection
✅ xss - XSS: Cross Site Scripting
✅ file_upload - Malicious File Upload
✅ traversal - Directory Traversal
✅ lfi - LFI: Local File Inclusion
✅ xxe - XXE: External Entity Expansion
✅ xss - DZS Video Gallery <= 8.60 - Reflected Cross-Site Scripting
```

**建议**: 保持所有规则启用（✅ 推荐）

### 手动添加新规则

**场景**: 保护 SSO 端点免受暴力破解

**步骤**:

1. 进入 Wordfence → Firewall → Manage Firewall
2. 点击 "手动添加新规则"
3. 添加自定义规则：

```yaml
规则名称: Protect SSO Token Endpoint
规则类型: Rate Limiting
路径匹配: /wp-json/nextjs-sso/v1/get-token
限制: 100 requests per 1 minute per IP
动作: Block 403
描述: 防止 SSO Token 端点被暴力破解
```

---

## 8️⃣ 其他杂项选项

### 推荐配置

```yaml
✅ 强制使用密码: 启用
   推荐强度: 强密码或更好（推荐）

✅ 不要让 WordPress 在登录错误时显示用户名: 启用

✅ 屏蔽用户注册 [admin] 用户名: 启用

✅ 禁用 WordPress 应用程序密码: 启用
   前提: 不使用移动应用

✅ 检查配置文件中讨论新密码强度: 启用

✅ 参与实时 Wordfence 安全网络: 启用
   理由: 共享威胁情报，提升全球防护
```

### 高级选项

```yaml
✅ 是否将全部选项还原至生产默认: 保持关闭
   理由: 避免覆盖自定义配置

✅ 检查配置更新时讨论新密码强度: 启用
```

---

## 9️⃣ 监控与告警

### 实时流量监控

**路径**: Wordfence → Tools → Live Traffic

**监控重点**:

1. **被阻止的请求**
   - 检查是否有误拦截的 SSO 请求
   - 查看被阻止的 IP 是否为合法用户

2. **人工访问**
   - 监控登录尝试
   - 识别异常访问模式

3. **爬虫/机器人**
   - 识别恶意爬虫
   - 白名单合法搜索引擎

### 告警配置

**路径**: Wordfence → Options → Alerts

**推荐启用的告警**:

```yaml
✅ 当有人被锁定时发送邮件: 启用
   收件人: 管理员邮箱

✅ 发现新文件时告警: 启用
   理由: 检测恶意文件上传

✅ 核心文件被修改时告警: 启用
   理由: 检测后门植入

⚠️ 每次登录失败都发邮件: 不推荐
   理由: 邮件轰炸，建议设置阈值（如 5 次失败）
```

---

## 🔟 性能优化

### 扫描调度

```yaml
推荐配置:
- 完整扫描: 每周一次（凌晨 3:00）
- 快速扫描: 每日一次（凌晨 2:00）
- 避免高峰时段扫描
```

### 缓存排除

**问题**: Wordfence 可能缓存 SSO Token 响应

**解决方案**:

在"高级防火墙选项" → "允许某页面被 Wordfence 缓存" 中排除：

```
排除路径:
/wp-json/nextjs-sso/v1/*
/js
```

---

## 📋 配置检查清单

### 上线前必检项

- [ ] **WAF 切换到"启用并保护"模式**
- [ ] **SSO API 路径已添加白名单**
- [ ] **Next.js 服务器 IP 已白名单**
- [ ] **强力防护启用且配置合理（10-20 次失败）**
- [ ] **速率限制已排除 SSO 端点**
- [ ] **测试完整 SSO 登录流程**
- [ ] **检查"实时流量"无误拦截**
- [ ] **邮件告警配置完成**
- [ ] **备份 Wordfence 配置**

### 日常维护

- [ ] **每周检查被阻止的请求**
- [ ] **每月审查白名单/黑名单**
- [ ] **每季度更新防火墙规则**
- [ ] **及时更新 Wordfence 插件**

---

## 🚨 故障排查

### 问题1: SSO Token 验证失败

**症状**: 前端报 401 或 403 错误

**排查步骤**:

1. **检查 Wordfence 实时流量**
   - 路径: Wordfence → Tools → Live Traffic
   - 搜索: `/wp-json/nextjs-sso/v1/get-token`
   - 查看是否被阻止

2. **检查防火墙规则**
   - 路径: Wordfence → Firewall → Manage Firewall
   - 确认 SSO 路径在白名单中

3. **临时禁用 WAF 测试**
   ```
   Wordfence → Firewall → Disable
   测试 SSO → 如果成功，说明是 WAF 问题
   重新启用 WAF → 调整白名单
   ```

### 问题2: 正常用户被误锁

**症状**: 用户报告无法登录，提示"账户已锁定"

**解决方案**:

1. **立即解锁**
   ```
   Wordfence → Tools → Blocking
   搜索用户 IP → 点击"Unlock"
   ```

2. **调整强力防护阈值**
   ```
   失败次数: 20 → 30（放宽）
   时间窗口: 4 小时 → 6 小时
   ```

3. **排除特定用户 IP**
   ```
   强力防护 → 立即解除密码锁定的用户的 IP
   输入用户 IP → 添加
   ```

### 问题3: 性能下降

**症状**: 网站加载变慢

**排查**:

1. **检查扫描调度**
   - 避免高峰时段扫描
   - 降低扫描频率

2. **优化防火墙规则**
   - 禁用不必要的规则
   - 使用白名单减少检查

3. **检查实时流量日志大小**
   ```
   Wordfence → Tools → Diagnostics
   清理旧日志
   ```

---

## 📚 参考资源

- **Wordfence 官方文档**: https://www.wordfence.com/help/
- **WAF 配置指南**: https://www.wordfence.com/help/firewall/
- **速率限制最佳实践**: https://www.wordfence.com/help/firewall/rate-limiting/
- **白名单配置**: https://www.wordfence.com/help/firewall/whitelisting/

---

## 🎯 下一步行动

1. **立即执行**（优先级：高）
   - [ ] 添加 SSO API 路径白名单
   - [ ] 配置 Next.js 服务器 IP 白名单
   - [ ] 测试 SSO 完整流程

2. **本周完成**（优先级：中）
   - [ ] 调整强力防护阈值
   - [ ] 配置邮件告警
   - [ ] 运行完整安全扫描

3. **持续优化**（优先级：低）
   - [ ] 监控实时流量 7 天
   - [ ] 切换 WAF 到保护模式
   - [ ] 创建自定义防火墙规则

---

**文档版本**: v1.0
**维护者**: AI Assistant
**适用环境**: WordPress + Next.js SSO Integration
**最后更新**: 2025-12-15
