# 🔐 WordPress SSO 单点登录配置指南

## 📋 概述

本指南帮助您将 Next.js 应用与 WordPress 主站（ucppt.com）的登录系统集成，实现单点登录（SSO）。

> ✅ 现状说明（2025-12-13）：WPCOM 用户中心不触发标准 WordPress 登录重定向 Hook。
> 旧的 `wp-login.php?redirect_to=...` + Hook 注入方式在 WPCOM 场景下不可用。
> 当前推荐使用“回调页 + REST API 获取 token”的插件方案（见下文）。

---

## ✅ 前置条件

1. ✅ WordPress 可访问（https://www.ucppt.com）
2. ✅ Next.js 应用已部署或运行在 `http://localhost:3000`（若 3000 被占用可能是 `http://localhost:3001`）
3. ✅ 已准备一个 WordPress 页面作为 SSO 回调页（示例：`https://www.ucppt.com/js`）
4. （可选/旧方案）Simple JWT Login 插件：旧方案依赖该插件与 Hook（已弃用，仅保留历史参考）

---

## 🚀 实施步骤

### ✅ 当前推荐方案（WPCOM 兼容）：回调页 + REST API 获取 token

### 步骤 1：安装 Next.js SSO 插件（v2.0.2）

1. WordPress 后台 → 插件 → 安装插件 → 上传插件
2. 选择仓库根目录的压缩包：`nextjs-sso-integration-v2.0.2.zip`
3. 安装并启用

### 步骤 2：创建/确认回调页面（示例：/js）

1. WordPress 后台 → 页面 → 新建页面
2. 标题例如：`js`（或 `SSO 回调`）
3. 页面内容添加短代码：`[nextjs_sso_callback]`
4. 发布并确认 URL 形如：`https://www.ucppt.com/js`

### 步骤 3：配置 WPCOM 用户中心“登录后跳转”

在 WPCOM 用户中心把“登录后跳转”设置为：

- `https://www.ucppt.com/js`

该回调页会在浏览器内调用 WordPress REST API 获取 token，然后重定向回本机：

- `http://localhost:3000/auth/callback?token=...` 或 `http://localhost:3001/auth/callback?token=...`

### 步骤 4：联调验证

1. 确认本机 Next.js 已启动（以终端输出端口为准，常见 3000/3001）
2. 在已登录 `www.ucppt.com` 的同一浏览器中访问 `https://www.ucppt.com/js`
3. 应自动跳转到本机 `/auth/callback?token=...`，并完成登录

---

### 🧾 未完成任务（忠实记录）

1. 将前端自动跳转逻辑的 `redirect_to` 目标与上述 `/js` token 获取链路对齐（当前自动跳转指向 Next.js 的 `/auth/callback`，但 token 链路依赖 `/js`）。
2. 从本机联调（localhost）切换到生产域名（ai.ucppt.com）回调，并完成端到端回归。

---

### 📚 旧方案（历史参考，WPCOM 场景已弃用）

### 步骤 1：安装 WordPress SSO 插件

#### 方式A：创建自定义插件（推荐）

1. 在 WordPress 目录创建插件文件夹：
   ```bash
   wp-content/plugins/nextjs-sso-integration/
   ```

2. 将 `wordpress-sso-plugin.php` 文件上传到该文件夹

3. 在 WordPress 后台 **插件 → 已安装的插件** 中激活：
   - **Next.js SSO Integration**

#### 方式B：添加到主题 functions.php（快速测试）

1. 打开主题的 `functions.php` 文件
2. 将 `wordpress-sso-plugin.php` 的代码（除了插件头部注释）复制到文件末尾
3. 保存文件

---

### 步骤 2：配置 Simple JWT Login 插件

1. 进入 WordPress 后台：**设置 → Simple JWT Login**

2. **General 页面**：
   - Route Namespace: `simple-jwt-login/v1/`
   - JWT Decryption Key: 已配置 ✅

3. **Authentication 页面**：
   - ✅ 勾选 **Allow Authentication**

4. **Hooks 页面**（新增）：
   - ✅ 启用 **Login Redirect Hook**
   - 这将允许我们自定义登录后的重定向逻辑

---

### 步骤 3：测试 SSO 登录流程

#### 测试流程：

1. **清除浏览器缓存和 localStorage**
   ```javascript
   // 在浏览器控制台执行
   localStorage.clear();
   ```

2. **访问 Next.js 应用**
   ```
   http://localhost:3000
   ```
   → 应该自动跳转到 `/auth/login`

3. **点击"使用 ucppt.com 账号登录"**
   → 跳转到 WordPress 登录页面：
   ```
   https://www.ucppt.com/wp-login.php?redirect_to=http://localhost:3000/auth/callback
   ```

4. **在 WordPress 输入用户名和密码**
   → 登录成功后自动跳转：
   ```
   http://localhost:3000/auth/callback?token=eyJhbGciOiJIUzI1NiIs...
   ```

5. **Next.js 处理回调**
   → 保存 Token → 跳转到首页
   → 左下角显示用户信息 ✅

---

## 🔍 故障排查

### 问题 1：登录后未跳转回 Next.js

**症状**：登录成功后停留在 WordPress 后台

**解决方案**：
1. 检查 `wordpress-sso-plugin.php` 是否正确加载
2. 在插件中添加调试日志：
   ```php
   error_log('Redirect To: ' . $requested_redirect_to);
   error_log('Generated Token: ' . $token);
   ```
3. 查看 WordPress 错误日志：`wp-content/debug.log`

---

### 问题 2：Token 生成失败

**症状**：回调 URL 包含 `?error=Token+生成失败`

**解决方案**：
1. 确认 Simple JWT Login 插件已激活
2. 检查 JWT Key 配置是否正确
3. 尝试手动调用 Simple JWT Login API：
   ```bash
   curl -X POST https://www.ucppt.com/wp-json/simple-jwt-login/v1/auth \
     -H "Content-Type: application/json" \
     -d '{"username": "8pdwoxj8", "password": "YOUR_PASSWORD"}'
   ```

---

### 问题 3：CORS 跨域错误

**症状**：浏览器控制台显示 CORS 错误

**解决方案**：
1. 确认 `nextjs_sso_cors_headers` 函数已添加
2. 检查 Next.js 回调 URL 是否在白名单中：
   ```php
   header('Access-Control-Allow-Origin: http://localhost:3000');
   ```
3. 生产环境需要修改为实际域名：
   ```php
   header('Access-Control-Allow-Origin: https://app.ucppt.com');
   ```

---

### 问题 4：Token 验证失败

**症状**：回调页面显示"Token 验证失败"

**解决方案**：
1. 确认 Token 格式正确（Base64 编码的 JWT）
2. 检查 Token 是否过期
3. 手动验证 Token：
   ```bash
   curl -X POST http://localhost:3000/api/auth/verify \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

---

## 🎯 高级配置

### 自定义 Token 过期时间

修改 `wordpress-sso-plugin.php` 第 45 行：
```php
'exp' => time() + (7 * 24 * 60 * 60) // 7天 → 修改为所需天数
```

### 添加更多用户字段

修改 `user_data` 数组（第 39-47 行）：
```php
$user_data = array(
    'user_id' => $user->ID,
    'username' => $user->user_login,
    'email' => $user->user_email,
    'name' => $user->display_name,
    'roles' => $user->roles,
    'phone' => get_user_meta($user->ID, 'phone', true), // 🔥 新增字段
    'avatar_url' => get_avatar_url($user->ID),          // 🔥 新增头像
    'iat' => time(),
    'exp' => time() + (7 * 24 * 60 * 60)
);
```

### 限制允许的重定向域名

生产环境添加到白名单（`nextjs_sso_allowed_redirect_hosts` 函数）：
```php
$hosts[] = 'app.ucppt.com';
$hosts[] = 'design-assistant.ucppt.com';
```

---

## 📊 完整流程图

```
┌─────────────────────────────────────────────────────────────┐
│ 用户访问 Next.js 应用                                       │
│ http://localhost:3000                                       │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ AuthContext 检测：未登录                                    │
│ 自动跳转 → /auth/login                                     │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 登录页面：两种选择                                         │
│ 1. 手动输入用户名密码（直接调用后端 API）                │
│ 2. 点击"使用 ucppt.com 账号登录"（SSO）                  │
└────────────┬────────────────────────────────────────────────┘
             │ （选择 SSO）
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 跳转到 WordPress 登录页面                                  │
│ https://www.ucppt.com/wp-login.php?redirect_to=...         │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 用户在 WordPress 输入用户名和密码                          │
│ WordPress 验证凭证                                         │
└────────────┬────────────────────────────────────────────────┘
             │ ✅ 验证成功
             ▼
┌─────────────────────────────────────────────────────────────┐
│ WordPress SSO 插件执行：                                   │
│ 1. 生成 JWT Token（包含用户信息）                         │
│ 2. 重定向回 Next.js 回调页面                              │
│    http://localhost:3000/auth/callback?token=xxx           │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ Next.js 回调页面（/auth/callback）                         │
│ 1. 提取 URL 参数中的 Token                                │
│ 2. 验证 Token（调用后端 /api/auth/verify）               │
│ 3. 保存 Token 和用户信息到 localStorage                   │
│ 4. 跳转到首页                                             │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│ 首页（/）                                                  │
│ ✅ 显示用户信息（左下角用户面板）                          │
│ ✅ 所有功能正常可用                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 安全建议

1. **HTTPS 强制**：生产环境必须使用 HTTPS
   ```php
   if (!is_ssl() && !is_local()) {
       wp_redirect('https://' . $_SERVER['HTTP_HOST'] . $_SERVER['REQUEST_URI']);
       exit;
   }
   ```

2. **Token 加密存储**：考虑使用 httpOnly Cookie 而非 localStorage
3. **白名单验证**：严格限制允许的重定向域名
4. **Token 刷新机制**：实现 Refresh Token 避免频繁登录

---

## 📞 技术支持

如遇到问题，请提供以下信息：
1. WordPress 版本
2. Simple JWT Login 插件版本
3. 浏览器控制台错误日志
4. WordPress 错误日志（`wp-content/debug.log`）

---

**最后更新**：2025-12-13
**版本**：v1.0.0
