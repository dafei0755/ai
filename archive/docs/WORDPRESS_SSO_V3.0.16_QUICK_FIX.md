# v3.0.16 快速诊断清单 - 3分钟排查

## 🚨 关键发现

**症状**: debug.log中没有 `[Next.js SSO v3.0.16]` 日志
**结论**: WordPress在插件代码执行之前就返回了401

---

## ⚡ 3步快速修复

### ✅ 步骤1: 检查permission_callback（1分钟）

**打开文件：** `wp-content/plugins/nextjs-sso-integration-v3/nextjs-sso-integration-v3.php`

**找到第85-95行：**
```php
register_rest_route('nextjs-sso/v1', '/get-token', array(
    'methods' => 'GET',
    'callback' => 'nextjs_sso_v3_get_token',
    'permission_callback' => '__return_true', // ← 第91行，检查这里！
));
```

**检查第91行是否为：**
```php
'permission_callback' => '__return_true',  // ✅ 正确
```

**如果是以下任何一种，都需要修改：**
```php
'permission_callback' => 'is_user_logged_in',    // ❌ 错误1
'permission_callback' => array($this, 'check'),  // ❌ 错误2
'permission_callback' => 'wp_verify_nonce',      // ❌ 错误3
```

**修改为：**
```php
'permission_callback' => '__return_true',
```

**保存文件后立即测试。**

---

### ✅ 步骤2: 验证修复（1分钟）

**浏览器访问：**
```
https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token
```

**预期响应（任何一种都说明修复成功）：**

**情况A: 未登录（200 OK）**
```json
{
  "success": false,
  "message": "未登录"
}
```

**情况B: 已登录（200 OK）**
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "username": "宋词",
    "email": "..."
  }
}
```

**如果还是401错误：** 继续步骤3

---

### ✅ 步骤3: 检查debug.log（1分钟）

**打开文件：** `wp-content/debug.log`

**访问 `https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token` 后，立即查看最后20行**

**应该看到：**
```
[Next.js SSO v3.0.16] 🔍 开始获取用户...
[Next.js SSO v3.0.16] 当前所有Cookies: wordpress_..., wpcom_...
[Next.js SSO v3.0.16] 🎯 检测到WPCOM Member Pro插件
```

**如果仍然没有日志：**
- 插件未正确安装 → 重新上传ZIP
- WP_DEBUG未启用 → 检查 `wp-config.php`

---

## 🛠️ 如果步骤1-3都无效

### 方案A: 重新安装插件

```
1. WordPress后台 → 插件 → Next.js SSO Integration v3 → 停用
2. 插件 → Next.js SSO Integration v3 → 删除
3. 插件 → 安装插件 → 上传插件 → nextjs-sso-integration-v3.0.16.zip
4. 立即安装 → 启用插件
```

### 方案B: 使用诊断工具

**打开文件：** [test-v3.0.16-rest-api.html](test-v3.0.16-rest-api.html)

**操作：**
1. 在 `ucppt.com/account` 登录
2. 同一浏览器打开HTML文件
3. 点击"运行完整诊断"
4. 复制报告

---

## 📊 诊断工具位置

- **故障排除完整指南**: [WORDPRESS_SSO_V3.0.16_TROUBLESHOOTING.md](WORDPRESS_SSO_V3.0.16_TROUBLESHOOTING.md)
- **PowerShell日志分析器**: [diagnose-v3.0.16.ps1](diagnose-v3.0.16.ps1)
- **浏览器REST API测试**: [test-v3.0.16-rest-api.html](test-v3.0.16-rest-api.html)
- **Playwright自动化测试**: `e2e-tests/` 目录

---

## 🎯 最可能的问题

**95%概率**: `permission_callback` 设置错误（第91行）
**4%概率**: 插件未正确加载或启用
**1%概率**: PHP语法错误或版本不兼容

---

## ✅ 修复后的验证步骤

### 1. debug.log应该显示

```
[Next.js SSO v3.0.16] 🔍 开始获取用户...
[Next.js SSO v3.0.16] ✅ 通过WPCOM API获取到会员: 宋词
```

### 2. 浏览器访问 localhost:3000 应该

- 自动跳转到 `/analysis`
- 控制台显示 `[AuthContext] ✅ REST API Token 验证成功`

---

**最后更新**: 2025-12-16
**状态**: 等待用户执行步骤1（检查permission_callback）
