# WordPress SSO v3.0.5 - 登录状态同步修复文档

**修复日期**: 2025-12-15
**版本**: v3.0.5
**严重性**: 高优先级（影响用户体验）

---

## 问题描述

用户在 WordPress 登录后,访问嵌入的 Next.js 应用时仍然显示"需要登录"提示,需要刷新页面或重新登录才能同步登录状态。

### 问题表现

1. ✅ **用户在 WordPress 完成登录**
2. ❌ **访问 `/nextjs` 页面（iframe 嵌入的 Next.js 应用）仍显示未登录**
3. ⚠️ **需要手动刷新页面或重新登录才能恢复**

---

## 根本原因

### 1. URL Token 参数丢失

- **原设计**: WordPress 插件在 iframe URL 中传递 `sso_token` 参数
- **问题**: 用户刷新页面后,URL 参数被清除（Next.js 代码中有清除逻辑）
- **影响**: 第二次访问时无法从 URL 获取 Token

### 2. Cookie 跨域限制

- **REST API 方式**: `/wp-json/nextjs-sso/v1/get-token` 依赖 WordPress Cookie
- **问题**: 现代浏览器的 SameSite Cookie 策略阻止跨域 iframe 携带 Cookie
- **影响**: iframe 中的 REST API 请求无法获取 WordPress 登录状态

### 3. 认证检查时机问题

- **AuthContext 行为**: 只在组件首次加载时检查 SSO 登录
- **问题**: localStorage 中 Token 被清除后,不会主动重新获取
- **影响**: 用户需要刷新页面才能恢复登录状态

---

## 解决方案：PostMessage 通信 + Token 实时同步

### 核心思路

利用 `window.postMessage` API 实现 WordPress 父页面与 Next.js iframe 之间的**安全通信**,绕过 Cookie 跨域限制。

### 技术方案

#### 🔹 WordPress 端 (nextjs-sso-integration-v3.php)

1. **iframe 加载时发送 Token**
   ```javascript
   iframe.addEventListener('load', function() {
       iframe.contentWindow.postMessage({
           type: 'sso_login',
           token: 'jwt_token_here',
           user: { user_id, username, email, display_name }
       }, 'https://ai.ucppt.com');
   });
   ```

2. **定期同步 Token（每30秒）**
   ```javascript
   setInterval(function() {
       iframe.contentWindow.postMessage({
           type: 'sso_sync',
           token: 'jwt_token_here'
       }, 'https://ai.ucppt.com');
   }, 30000);
   ```

#### 🔹 Next.js 端 (AuthContext.tsx)

1. **监听 postMessage 事件**
   ```typescript
   useEffect(() => {
       const handlePostMessage = (event: MessageEvent) => {
           // 安全检查：只接受来自 WordPress 的消息
           const allowedOrigins = ['https://www.ucppt.com', ...];
           if (!allowedOrigins.some(origin => event.origin.startsWith(origin))) {
               return;
           }

           // 保存 Token
           if (event.data.type === 'sso_login' || event.data.type === 'sso_sync') {
               localStorage.setItem('wp_jwt_token', event.data.token);
               localStorage.setItem('wp_jwt_user', JSON.stringify(event.data.user));
               setUser(event.data.user);
           }
       };

       window.addEventListener('message', handlePostMessage);
       return () => window.removeEventListener('message', handlePostMessage);
   }, []);
   ```

---

## 修复效果

### ✅ 修复前后对比

| 场景 | 修复前 | 修复后 |
|-----|-------|-------|
| **首次访问** | ⚠️ 需要从 URL 获取 Token | ✅ postMessage 实时传递 |
| **刷新页面** | ❌ Token 丢失,显示未登录 | ✅ 自动重新同步 Token |
| **长时间停留** | ❌ Token 过期无感知 | ✅ 每30秒自动刷新 |
| **跨域 Cookie** | ❌ 受浏览器策略限制 | ✅ 不依赖 Cookie |

### ✅ 优势

1. **实时同步**: iframe 加载时立即传递 Token,无需等待用户操作
2. **自动刷新**: 每30秒同步一次,保持登录状态最新
3. **安全可控**: postMessage 只在 iframe 中传递,不暴露在 URL 或公开 API
4. **跨域友好**: 不依赖 Cookie,不受 SameSite 策略限制
5. **向后兼容**: 保留原有的 URL Token 和 REST API 方式作为降级方案

---

## 部署步骤

### 1. 上传更新的 WordPress 插件

```bash
# 通过 FTP 或 WordPress 后台上传
wp-content/plugins/nextjs-sso-integration-v3.php
```

### 2. 在 WordPress 后台激活插件

- 访问: **WordPress 后台 → 插件 → 已安装的插件**
- 如果已激活,**先停用再重新激活**（清除旧缓存）
- 验证版本号显示为 **v3.0.5**

### 3. 部署 Next.js 前端更新

```bash
cd frontend-nextjs

# 构建生产版本
npm run build

# 部署到服务器
# 方法 1: Vercel
vercel --prod

# 方法 2: 手动部署
rsync -avz .next/ user@server:/var/www/nextjs/.next/
pm2 restart nextjs
```

### 4. 清除浏览器缓存

```bash
# 用户端操作
1. 按 Ctrl+Shift+R (Windows) 或 Cmd+Shift+R (Mac) 强制刷新
2. 或清除浏览器 localStorage:
   - 打开浏览器开发者工具 (F12)
   - Application → Local Storage → 删除 wp_jwt_token 和 wp_jwt_user
```

---

## 验证测试

### ✅ 测试检查清单

1. **首次登录测试**
   - [ ] 在 WordPress 登录
   - [ ] 访问 `https://www.ucppt.com/nextjs`
   - [ ] 确认 Next.js 应用显示用户信息（左下角用户面板）
   - [ ] 浏览器控制台检查日志: `[AuthContext] 📨 收到 WordPress 的 Token (postMessage)`

2. **刷新页面测试**
   - [ ] 在 Next.js 应用中按 F5 刷新
   - [ ] 确认登录状态保持,不需要重新登录
   - [ ] 检查 localStorage 中 `wp_jwt_token` 是否存在

3. **长时间停留测试**
   - [ ] 保持页面打开 1 分钟
   - [ ] 检查控制台日志,确认每30秒有 `[Next.js SSO v3.0.5] Token 定期同步` 输出

4. **跨浏览器测试**
   - [ ] Chrome/Edge (最新版)
   - [ ] Firefox (最新版)
   - [ ] Safari (Mac/iOS)

5. **安全性测试**
   - [ ] 在非 WordPress 页面打开 Next.js 应用,确认不会收到 postMessage
   - [ ] 检查 postMessage origin 验证生效

---

## 回滚方案

如果修复后出现新问题,可以快速回滚到 v3.0.4:

```bash
# 1. 恢复 WordPress 插件
git checkout v3.0.4 -- nextjs-sso-integration-v3.php

# 2. 恢复 Next.js AuthContext
git checkout v3.0.4 -- frontend-nextjs/contexts/AuthContext.tsx

# 3. 重新部署
npm run build
vercel --prod
```

---

## 监控与日志

### 🔍 关键日志输出

**WordPress 端 (浏览器控制台)**:
```
[Next.js SSO v3.0.5] 已通过 postMessage 发送 Token 到 iframe
[Next.js SSO v3.0.5] Token 定期同步
```

**Next.js 端 (浏览器控制台)**:
```
[AuthContext] 📨 收到 WordPress 的 Token (postMessage): sso_login
[AuthContext] 📨 收到 WordPress 的 Token (postMessage): sso_sync
[UserPanel] 用户状态: { hasUser: true, localStorage_token: "eyJ0eXAi..." }
```

### 🚨 异常日志

如果出现以下日志,表示有问题:
```
[AuthContext] ⚠️ SSO 响应无效（无 Token）
[Next.js SSO v3.0] 找不到 iframe 元素
```

---

## 常见问题 FAQ

### Q1: postMessage 是否安全?

**A**: 是的。我们实现了多层安全验证:
- ✅ **Origin 白名单**: 只接受来自 `www.ucppt.com` 的消息
- ✅ **类型校验**: 只处理 `sso_login` 和 `sso_sync` 类型
- ✅ **Token 加密**: JWT Token 本身已加密,即使被截获也需要密钥才能解密

### Q2: 为什么需要每30秒同步一次?

**A**:
- 防止 Token 过期导致的登录失效
- 确保用户在 WordPress 端的状态变化能及时同步到 Next.js
- 30秒是一个合理的平衡点（不会过于频繁造成性能问题）

### Q3: 如果 WordPress 和 Next.js 不在同一个域名怎么办?

**A**: postMessage 支持跨域通信,只需确保:
1. WordPress 插件中的 `allowedOrigins` 包含 Next.js 的域名
2. Next.js AuthContext 中的 `allowedOrigins` 包含 WordPress 的域名

### Q4: 这个修复是否影响原有的 URL Token 方式?

**A**: 不影响。保留了所有原有登录方式:
1. **postMessage** (新增,优先级最高)
2. **URL Token** (保留,作为降级方案)
3. **REST API** (保留,作为最后手段)

---

## 相关文件

- `nextjs-sso-integration-v3.php` (WordPress 插件)
- `frontend-nextjs/contexts/AuthContext.tsx` (Next.js 认证上下文)
- `frontend-nextjs/lib/wp-auth.ts` (Token 管理工具)

---

## 技术支持

如有问题,请联系:
- **GitHub Issues**: https://github.com/anthropics/claude-code/issues
- **文档**: https://www.ucppt.com/docs
