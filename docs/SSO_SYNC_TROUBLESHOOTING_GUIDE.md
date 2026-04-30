# 🔧 SSO同步故障排除指南 (v3.0.21)

**文档版本**: 1.0
**日期**: 2025-12-17
**状态**: 🔴 问题诊断中

---

## 🚨 问题描述

**现象**: WordPress用户切换后，NextJS应用显示的用户信息未同步更新

- **截图1**: WordPress后台显示用户ID 2751已登录
- **截图2**: NextJS应用仍然显示旧用户（宋词 42841287@qq.com）

**已实施的方案**:
- ✅ 方案2: 页面可见性检测 + REST API轮询
- ✅ 方案3: 事件驱动 + Cookie轮询

**当前状态**: 双机制已实施，但问题依旧

---

## 🔍 根本原因分析

### 问题1: Cookie跨域限制 (方案3失效的根本原因)

#### 技术背景

**浏览器同源策略 (Same-Origin Policy)**:
- Cookie只能在**同一域名**下共享
- `www.ucppt.com` 和 `localhost:3000` 是**不同的域**
- 浏览器**阻止跨域Cookie读写**

#### 具体表现

**WordPress PHP代码**（nextjs-sso-integration-v3.php Line 1600）:
```php
setcookie(
    'nextjs_sso_v3_login_event',
    $cookie_value,
    time() + 300,
    '/',
    parse_url(home_url(), PHP_URL_HOST),  // ⚠️ 域名: www.ucppt.com
    false,
    false
);
```

**Cookie实际设置**:
- 域名: `www.ucppt.com`
- 路径: `/`
- HttpOnly: `false`
- Secure: `false`

**NextJS JavaScript代码**（AuthContext.tsx Line 103-105）:
```typescript
const loginEventCookie = document.cookie
  .split('; ')
  .find(row => row.startsWith('nextjs_sso_v3_login_event='));
```

**问题**:
- NextJS运行在 `localhost:3000`
- `document.cookie` 只能读取 `localhost` 域的Cookie
- **无法读取** `www.ucppt.com` 域的Cookie
- **方案3完全失效**！

#### 验证方法

**在浏览器开发者工具中检查**:

1. 打开 `https://www.ucppt.com/`（WordPress站点）
2. F12 打开开发者工具 → Application/存储 → Cookies
3. 查看是否有 `nextjs_sso_v3_login_event` Cookie
4. 切换到 `http://localhost:3000`（NextJS站点）
5. 再次查看Cookies
6. **预期结果**: `localhost:3000` 下**看不到**WordPress的Cookie

---

### 问题2: 方案2可能的问题

方案2（REST API轮询）理论上应该工作，因为：
- ✅ REST API调用支持 `credentials: 'include'`（携带WordPress Cookie）
- ✅ WordPress CORS已配置（允许 `localhost:3000`）

但可能的问题：

#### 2.1 visibilitychange事件未触发

**原因**: 如果用户在同一个标签页内切换WordPress用户（没有切换到NextJS标签页），`visibilitychange` 事件不会触发。

**验证**:
```javascript
// 在NextJS控制台输入：
document.addEventListener('visibilitychange', () => {
  console.log('✅ visibilitychange触发:', document.visibilityState);
});
// 然后切换标签页，看是否输出日志
```

#### 2.2 WordPress REST API返回401

**原因**: 如果WordPress用户切换后，旧的Cookie失效，REST API可能返回401。

**验证**:
```bash
# 在浏览器控制台或命令行测试
curl -X GET 'https://www.ucppt.com/wp-json/nextjs-sso/v1/sync-status' \
  -H 'Cookie: wordpress_logged_in_xxx=...' \
  -v
```

**检查响应**:
- 200: 正常（应返回 `{logged_in: true, user_id: 2751, ...}`）
- 401: 未登录（Cookie已失效）

#### 2.3 CORS问题

**验证**:
```javascript
// 在NextJS控制台（localhost:3000）执行：
fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/sync-status', {
  method: 'GET',
  credentials: 'include'
})
.then(res => {
  console.log('✅ CORS正常，状态码:', res.status);
  return res.json();
})
.then(data => console.log('📥 响应数据:', data))
.catch(err => console.error('❌ CORS错误:', err));
```

**预期结果**:
- 正常: 返回 `{logged_in: true/false, ...}`
- 错误: `CORS policy` 或 `Network error`

---

## 🛠️ 解决方案

### 方案A: 使用方案2作为主要机制（推荐）

**原因**: 方案2（REST API）支持跨域，不依赖Cookie共享。

**优化方案2**:

#### 修改1: 增加轮询频率

**问题**: `visibilitychange` 只在页面切换时触发，如果用户在NextJS页面停留，无法检测到WordPress的登录变化。

**解决**: 添加定期轮询（每10秒检测一次）

**代码修改**（AuthContext.tsx）:

```typescript
// 🆕 增强版方案2: visibilitychange + 定期轮询
useEffect(() => {
  const checkSSOStatus = async () => {
    try {
      const response = await fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/sync-status', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });

      if (response.ok) {
        const data = await response.json();
        console.log('[AuthContext v3.0.21] 📥 SSO状态:', data);

        // 检测到登录事件
        if (data.event === 'user_login' && data.token) {
          console.log('[AuthContext v3.0.21] ✅ 检测到WordPress登录事件');
          localStorage.setItem('wp_jwt_token', data.token);
          localStorage.setItem('wp_jwt_user', JSON.stringify(data.user));
          setUser(data.user);
        }

        // 检测到退出事件
        if (data.event === 'user_logout') {
          console.log('[AuthContext v3.0.21] ✅ 检测到WordPress退出事件');
          localStorage.removeItem('wp_jwt_token');
          localStorage.removeItem('wp_jwt_user');
          setUser(null);
        }
      }
    } catch (error) {
      console.error('[AuthContext v3.0.21] ❌ SSO状态检测失败:', error);
    }
  };

  // 1. 页面可见性变化时检测（保留）
  const handleVisibilityChange = () => {
    if (document.visibilityState === 'visible') {
      console.log('[AuthContext v3.0.21] 📄 页面重新可见');
      checkSSOStatus();
    }
  };
  document.addEventListener('visibilitychange', handleVisibilityChange);

  // 2. 🆕 定期轮询（每10秒）
  const pollInterval = setInterval(checkSSOStatus, 10000);

  // 3. 初始检测
  checkSSOStatus();

  return () => {
    document.removeEventListener('visibilitychange', handleVisibilityChange);
    clearInterval(pollInterval);
  };
}, []);
```

**优点**:
- ✅ 不依赖Cookie跨域
- ✅ 定期检测（10秒）确保用户状态最终一致
- ✅ 页面切换时立即检测（<1秒）
- ✅ 支持跨域（WordPress和NextJS可以在不同域名）

**缺点**:
- ⚠️ 增加服务器请求（每10秒1次）
- ⚠️ 实时性略低（最多10秒延迟）

---

### 方案B: 生产环境部署到同域名（推荐）

**原因**: 如果NextJS部署到 `ai.ucppt.com`（与WordPress同一主域名），方案3（Cookie）就能正常工作。

**部署架构**:

```
WordPress:  https://www.ucppt.com
NextJS:     https://ai.ucppt.com
```

**Cookie域名设置**（修改PHP代码）:

```php
// nextjs-sso-integration-v3.php
setcookie(
    'nextjs_sso_v3_login_event',
    $cookie_value,
    time() + 300,
    '/',
    '.ucppt.com',  // 🔥 设置为主域名（带前缀点）
    true,          // 🔥 Secure=true（HTTPS下生效）
    false          // HttpOnly=false（允许JavaScript读取）
);
```

**效果**:
- ✅ Cookie在 `www.ucppt.com` 和 `ai.ucppt.com` 之间共享
- ✅ 方案3（Cookie轮询）正常工作
- ✅ 实时性 <2秒
- ✅ 跨标签页同步

**注意事项**:
- ⚠️ 仅在HTTPS环境下工作（`Secure=true`）
- ⚠️ 需要配置 `ai.ucppt.com` 的DNS和SSL证书
- ⚠️ NextJS需要重新构建和部署

---

### 方案C: 使用postMessage（备选）

**原因**: 如果NextJS通过iframe嵌入到WordPress页面，可以使用 `postMessage` 进行跨域通信。

**不推荐理由**:
- ❌ 用户已从iframe模式切换到独立窗口模式（v3.0.15）
- ❌ 增加架构复杂度
- ❌ 用户体验不如独立窗口

---

## 📋 诊断清单

### 步骤1: 检查WordPress Hooks是否触发

**操作**:
1. 在WordPress后台切换用户（或登录/退出）
2. 查看WordPress错误日志：`wp-content/debug.log`

**预期日志**:
```
[Next.js SSO v3.0.21] 📡 用户登录事件触发: testuser (ID: 2751)
[Next.js SSO v3.0.21] ✅ 登录事件Cookie已设置，NextJS应用将自动同步
```

**如果没有日志**:
- ❌ WordPress Hooks未触发
- **原因**: 插件未激活，或使用了第三方用户切换插件（绕过了 `wp_login` Hook）
- **解决**:
  1. 确认插件已激活：WordPress后台 → 插件 → 确认 "Next.js SSO Integration v3" 已启用
  2. 测试标准登录流程（退出后重新登录），而非"用户切换"插件

---

### 步骤2: 检查Cookie是否设置

**操作**:
1. 在WordPress后台登录/切换用户
2. F12 → Application → Cookies → `www.ucppt.com`
3. 查找 `nextjs_sso_v3_login_event` Cookie

**预期结果**:
- ✅ Cookie存在，值为JSON字符串：`{"event":"user_login","token":"eyJ...","user_id":2751,...}`

**如果Cookie不存在**:
- ❌ PHP `setcookie()` 失败
- **原因**:
  1. Cookie已被清除（5分钟过期）
  2. 域名设置错误
  3. PHP输出前已有内容（Headers already sent错误）
- **解决**:
  1. 立即登录后检查Cookie（5分钟内）
  2. 检查WordPress错误日志是否有 "Headers already sent" 错误
  3. 修改Cookie过期时间为60分钟（测试用）：`time() + 3600`

---

### 步骤3: 检查NextJS是否检测到Cookie

**操作**:
1. 打开 `http://localhost:3000`（NextJS应用）
2. F12 → Console
3. 查找日志：`[AuthContext v3.0.21]`

**预期日志**（方案3 - Cookie轮询）:
```
[AuthContext v3.0.21] 🎉 检测到WordPress登录事件（方案3）: {event: "user_login", token: "eyJ...", user_id: 2751}
[AuthContext v3.0.21] ✅ Token验证成功（方案3），用户: {user_id: 2751, username: "testuser"}
```

**如果没有日志**:
- ❌ NextJS无法读取Cookie（跨域问题）
- **确认**: 这是**预期行为**（`localhost:3000` 无法读取 `www.ucppt.com` 的Cookie）
- **解决**: 使用**方案A**（增强版方案2）

---

### 步骤4: 检查方案2（REST API）是否工作

**操作**:
1. 在NextJS控制台（`localhost:3000`）执行测试代码：

```javascript
fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/sync-status', {
  method: 'GET',
  credentials: 'include',
  headers: { 'Accept': 'application/json' }
})
.then(res => {
  console.log('✅ 状态码:', res.status);
  if (!res.ok) throw new Error('API返回错误');
  return res.json();
})
.then(data => {
  console.log('📥 SSO状态:', data);
  if (data.event === 'user_login') {
    console.log('✅ 检测到登录事件，Token:', data.token.substring(0, 20) + '...');
  } else if (data.logged_in) {
    console.log('✅ 用户已登录，但无新事件');
  } else {
    console.log('⚠️ 用户未登录');
  }
})
.catch(err => console.error('❌ 错误:', err));
```

**预期结果**:
- ✅ 状态码: 200
- ✅ 响应数据包含 `logged_in: true`, `user_id: 2751`, `event: "user_login"`

**如果返回401**:
- ❌ WordPress Cookie未携带或已失效
- **解决**:
  1. 确认在同一浏览器中登录了WordPress
  2. 检查CORS配置（`nextjs-sso-integration-v3.php` Lines 761-783）
  3. 检查是否设置了 `credentials: 'include'`

**如果CORS错误**:
- ❌ WordPress CORS配置问题
- **解决**: 确认 `$allowed_origins` 数组包含 `'http://localhost:3000'`

---

### 步骤5: 测试页面切换检测

**操作**:
1. 在WordPress后台登录新用户
2. 立即切换到NextJS标签页（触发 `visibilitychange`）
3. 查看NextJS控制台

**预期日志**:
```
[AuthContext v3.0.21] 📄 页面重新可见，检测SSO状态变化...
[AuthContext v3.0.21] 📥 SSO状态: {logged_in: true, user_id: 2751, event: "user_login", token: "eyJ..."}
[AuthContext v3.0.21] ✅ 检测到WordPress登录事件（方案2）
```

**如果没有日志**:
- ❌ `visibilitychange` 事件未触发或检测逻辑未执行
- **解决**:
  1. 确认NextJS应用已启动且AuthContext已加载
  2. 检查 `useEffect` 是否正确注册事件监听器
  3. 手动测试：在控制台输入 `document.visibilityState` 查看当前状态

---

## 🚀 快速修复（推荐方案）

### 立即可用：增强版方案2

**修改文件**: `frontend-nextjs/contexts/AuthContext.tsx`

**完整代码**（替换Lines 38-96）:

```typescript
// 🆕 v3.0.21增强版: 方案2 - REST API轮询（主要机制）
useEffect(() => {
  const checkSSOStatus = async () => {
    try {
      // 调用WordPress REST API检查SSO事件
      const response = await fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/sync-status', {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });

      if (response.ok) {
        const data = await response.json();

        // 静默检测（不输出过多日志）
        if (data.event === 'user_login' && data.token) {
          console.log('[AuthContext v3.0.21] ✅ 检测到WordPress登录事件（REST API）');
          console.log('[AuthContext v3.0.21] 新用户:', data.user);

          // 保存新Token
          localStorage.setItem('wp_jwt_token', data.token);
          localStorage.setItem('wp_jwt_user', JSON.stringify(data.user));
          setUser(data.user);

          // 可选：刷新页面以确保所有组件同步
          // window.location.reload();
        }

        // 检测到退出事件
        if (data.event === 'user_logout') {
          console.log('[AuthContext v3.0.21] ✅ 检测到WordPress退出事件（REST API）');

          // 清除本地Token
          localStorage.removeItem('wp_jwt_token');
          localStorage.removeItem('wp_jwt_user');
          setUser(null);

          // 可选：跳转到登录页面
          // window.location.href = '/';
        }
      }
    } catch (error) {
      console.error('[AuthContext v3.0.21] ❌ SSO状态检测失败:', error);
    }
  };

  // 1. 页面可见性变化时检测（即时响应）
  const handleVisibilityChange = () => {
    if (document.visibilityState === 'visible') {
      console.log('[AuthContext v3.0.21] 📄 页面重新可见，检测SSO状态');
      checkSSOStatus();
    }
  };
  document.addEventListener('visibilitychange', handleVisibilityChange);

  // 2. 🆕 定期轮询（每10秒，确保最终一致性）
  const pollInterval = setInterval(() => {
    // 静默轮询（不输出日志）
    checkSSOStatus();
  }, 10000);

  // 3. 初始检测
  checkSSOStatus();

  return () => {
    document.removeEventListener('visibilitychange', handleVisibilityChange);
    clearInterval(pollInterval);
  };
}, []);
```

**说明**:
- ✅ 移除方案3（Cookie轮询），因为跨域无法工作
- ✅ 保留并增强方案2（REST API轮询）
- ✅ 增加定期轮询（10秒），确保最终一致性
- ✅ 页面切换时立即检测（<1秒）

---

## 📊 预期效果对比

| 指标 | 原方案（方案2+3） | 增强版方案2 | 生产环境（同域名） |
|------|-----------------|------------|------------------|
| **开发环境工作** | ❌ 方案3不工作（跨域） | ✅ 完全工作 | ✅ 完全工作 |
| **实时性** | <2秒（理论） | <10秒 | <2秒 |
| **跨标签页同步** | ❌（跨域限制） | ✅（REST API） | ✅（Cookie共享） |
| **服务器请求** | 0次（理论） | 6次/分钟 | 0次 |
| **可靠性** | 低（跨域问题） | 高 | 极高 |

---

## 🎯 最终建议

### 短期方案（立即可用）

**使用增强版方案2**（上述代码）

**原因**:
- ✅ 开发环境（localhost）立即可用
- ✅ 无需修改WordPress代码
- ✅ 无需等待生产环境部署
- ✅ 可靠性高（不依赖Cookie）

**代价**:
- ⚠️ 实时性略低（最多10秒延迟）
- ⚠️ 增加服务器请求（每10秒1次）

---

### 长期方案（生产环境推荐）

**部署NextJS到同域名**（如 `ai.ucppt.com`）

**操作**:
1. 配置DNS：将 `ai.ucppt.com` 指向NextJS服务器
2. 配置SSL证书（Let's Encrypt）
3. 修改Cookie域名为 `.ucppt.com`（nextjs-sso-integration-v3.php Line 1600）
4. 重新构建和部署NextJS应用

**效果**:
- ✅ 方案3（Cookie轮询）正常工作
- ✅ 实时性 <2秒
- ✅ 跨标签页同步
- ✅ 无额外服务器请求

---

## 📝 检查清单

在继续排查前，请确认：

- [ ] WordPress插件已激活（v3.0.21）
- [ ] NextJS应用已重启（确保AuthContext最新代码生效）
- [ ] 浏览器已清除缓存（避免旧代码干扰）
- [ ] WordPress `debug.log` 已启用（`wp-config.php` 中 `WP_DEBUG=true`）
- [ ] 浏览器控制台已打开（查看日志输出）
- [ ] 测试使用标准登录流程（退出→登录），而非"用户切换"插件

---

## 🔗 相关文档

- [SSO_SYNC_DUAL_MECHANISM_V3.0.21.md](SSO_SYNC_DUAL_MECHANISM_V3.0.21.md) - 双机制实施完整文档
- [CROSS_DOMAIN_COOKIE_FIX.md](../CROSS_DOMAIN_COOKIE_FIX.md) - 跨域Cookie问题详细分析
- [WORDPRESS_SSO_V3.0.20_DEPLOYMENT_GUIDE.md](WORDPRESS_SSO_V3.0.20_DEPLOYMENT_GUIDE.md) - 部署指南

---

**实施者**: Claude Code
**最后更新**: 2025-12-17
**版本**: v3.0.21-troubleshooting
**状态**: 🔴 待用户反馈
