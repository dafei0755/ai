# WordPress iframe 自动 SSO 登录 v2.4

## 更新内容

**v2.4** (2025-12-13): iframe 环境中自动从 WordPress 获取 Token，无需跳转到 `ucppt.com/js` 登录引导页

## 问题背景

### v2.3 存在的问题

```
用户访问 ucppt.com/nextjs（WordPress 已登录）
    ↓
WordPress 检测已登录 → 加载 iframe
    ↓
iframe 内 Next.js 检测本地无 Token
    ↓
跳转到 ucppt.com/js  ❌ 问题：跳出了 iframe！
    ↓
用户离开了嵌入页面
    ↓
登录后回到 Next.js
    ↓
又被主页重定向到 ucppt.com/nextjs（循环）
```

**根本原因**：
- WordPress 用户已登录（Cookie 存在）
- Next.js 本地 Token 已清除（之前退出登录或首次访问）
- AuthContext 检测无 Token 后直接跳转到 `ucppt.com/js`
- 没有利用 WordPress 的登录状态

## 解决方案 v2.4

### 核心改进：iframe 环境检测 + 自动 SSO

修改 `AuthContext.tsx`，在 iframe 中运行时：

1. **检测 iframe 环境**：`window.self !== window.top`
2. **调用 WordPress API**：`GET /wp-json/nextjs-sso/v1/get-token`
3. **自动获取 Token**：利用 WordPress Cookie（`credentials: 'include'`）
4. **验证并保存**：调用 Python 后端验证，保存到 localStorage
5. **静默登录成功**：用户无感知，应用直接可用

### 新的登录流程

#### 场景 A: 在 iframe 中（WordPress 已登录）✅ 优化重点

```
用户访问 ucppt.com/nextjs（WordPress 已登录）
    ↓
WordPress 检测已登录 → 加载 iframe
    ↓
iframe 内 Next.js 检测本地无 Token
    ↓
检测到在 iframe 中 ✅
    ↓
调用 GET https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token
    ↓
WordPress 返回 Token（基于 Cookie 自动识别用户）
    ↓
Next.js 验证 Token → 保存到 localStorage
    ↓
✅ 自动登录成功！用户停留在 ucppt.com/nextjs
```

#### 场景 B: 在 iframe 中（WordPress 未登录）

```
用户访问 ucppt.com/nextjs（WordPress 未登录）
    ↓
WordPress 检测未登录 → 显示登录引导（橙色卡片）
    ↓
不加载 iframe ✅ 插件已实现
    ↓
用户点击"立即登录"
    ↓
WordPress 登录页面
    ↓
登录成功，返回 ucppt.com/nextjs
    ↓
WordPress 重新加载页面 → 加载 iframe
    ↓
（进入场景 A）自动获取 Token
```

#### 场景 C: 不在 iframe 中（直接访问 localhost:3000）

```
用户访问 http://localhost:3000/
    ↓
主页检测不在 iframe 中
    ↓
自动重定向到 https://www.ucppt.com/nextjs ✅ v2.3.1
    ↓
（进入场景 A 或 B）
```

#### 场景 D: 退出登录后重新登录

```
用户在 iframe 内点击"退出登录"
    ↓
Next.js 清除 localStorage Token
    ↓
跳转到 /auth/logout 页面
    ↓
用户点击"重新登录应用"
    ↓
跳转到 ucppt.com/js（传统 SSO 流程）
    ↓
生成 Token → 回到 Next.js callback
    ↓
验证成功 → 主页 → 重定向到 ucppt.com/nextjs
    ↓
（进入场景 A）iframe 自动登录
```

## 代码实现

### 修改的文件

**`frontend-nextjs/contexts/AuthContext.tsx`** (Line 38-111)

### 核心逻辑

```typescript
const checkAuth = async () => {
  const authenticated = isAuthenticated();
  const currentUser = getCurrentUser();

  if (authenticated && currentUser) {
    setUser(currentUser);
    setIsLoading(false);
  } else {
    // 未登录，尝试 SSO
    const isInIframe = window.self !== window.top;

    if (isInIframe) {
      // 🔥 在 iframe 中：自动从 WordPress 获取 Token
      try {
        const response = await fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
          method: 'GET',
          credentials: 'include', // 关键：发送 WordPress Cookie
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success && data.token) {
            // 验证 Token
            const verifyResponse = await fetch(`${API_URL}/api/auth/verify`, {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${data.token}`
              }
            });

            if (verifyResponse.ok) {
              const verifyData = await verifyResponse.json();
              // 保存 Token 和用户信息
              localStorage.setItem('wp_jwt_token', data.token);
              localStorage.setItem('wp_user', JSON.stringify(verifyData.user));
              setUser(verifyData.user);
              setIsLoading(false);
              return; // ✅ SSO 成功
            }
          }
        }

        // WordPress 未登录，不做任何操作（父页面会显示登录引导）
        setIsLoading(false);
      } catch (error) {
        console.error('自动 SSO 失败:', error);
        setIsLoading(false);
      }
    } else {
      // 不在 iframe 中：跳转到传统 SSO 流程
      window.location.href = ssoBridgeUrl;
    }
  }
};
```

### 关键技术点

#### 1. CORS 跨域请求

```typescript
fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
  credentials: 'include', // 发送跨域 Cookie
});
```

**注意**：需要 WordPress CORS 配置支持。

#### 2. iframe 检测

```typescript
const isInIframe = window.self !== window.top;
```

- **true**: 在 iframe 中（执行自动 SSO）
- **false**: 独立窗口（执行传统跳转）

#### 3. 双重验证

1. **第一步**：从 WordPress 获取 Token
2. **第二步**：调用 Python 后端验证 Token

确保 Token 的有效性和用户信息的正确性。

## WordPress 插件 API

### `/wp-json/nextjs-sso/v1/get-token`

**方法**: GET

**权限**: 需要 WordPress 登录（Cookie）

**响应**（成功）:
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGci...",
  "user": {
    "id": 1,
    "username": "songci",
    "email": "user@example.com",
    "display_name": "宋词"
  }
}
```

**响应**（未登录）:
```json
{
  "code": "not_logged_in",
  "message": "用户未登录",
  "data": {
    "status": 401
  }
}
```

**插件代码位置**：
- [nextjs-sso-integration-v2.1-fixed.php](d:\11-20\langgraph-design\nextjs-sso-integration-v2.1-fixed.php) Line 466-493

## CORS 配置（重要）

### WordPress 需要允许跨域请求

如果 Next.js 运行在 `localhost:3000`，WordPress 在 `www.ucppt.com`，需要配置 CORS：

**方式 1: 在插件中添加 CORS 头部**

修改 `nextjs-sso-integration-v2.1-fixed.php`，在 `nextjs_sso_rest_get_token` 函数中添加：

```php
function nextjs_sso_rest_get_token() {
    // 🔥 添加 CORS 头部（开发环境）
    header('Access-Control-Allow-Origin: http://localhost:3000');
    header('Access-Control-Allow-Credentials: true');

    $current_user = nextjs_sso_get_user_from_cookie();
    // ... 其余代码
}
```

**方式 2: 使用 WordPress 插件**

安装 "WP CORS" 插件，配置允许的 Origin。

**方式 3: Nginx 反向代理**（生产环境推荐）

```nginx
location /wp-json/nextjs-sso/ {
    add_header Access-Control-Allow-Origin https://ai.ucppt.com;
    add_header Access-Control-Allow-Credentials true;
    proxy_pass https://www.ucppt.com;
}
```

## 测试步骤

### 测试 1: iframe 自动登录（WordPress 已登录）

1. 在浏览器中访问 `https://www.ucppt.com/wp-login.php`
2. 登录 WordPress（用户名: `8pdwoxj8`）
3. 访问 `https://www.ucppt.com/nextjs`
4. **预期结果**：
   - WordPress 页面加载，显示导航栏
   - iframe 自动加载 Next.js 应用
   - 左下角显示正确的用户名和头像（无需手动登录）
   - 浏览器控制台无错误

### 测试 2: iframe 自动登录（WordPress 未登录）

1. 在隐身窗口访问 `https://www.ucppt.com/nextjs`
2. **预期结果**：
   - 显示橙色登录引导卡片
   - 不显示 iframe
   - 点击"立即登录"跳转到 WordPress 登录页
3. 登录后返回 `ucppt.com/nextjs`
4. **预期结果**：
   - iframe 自动加载
   - 应用自动登录成功

### 测试 3: 退出登录后重新登录

1. 在 iframe 内点击"退出登录"
2. 看到退出成功页面
3. 点击"重新登录应用"
4. **预期结果**：
   - 跳转到 `ucppt.com/js`
   - 自动生成 Token 并返回 Next.js
   - 回到主页后自动重定向到 `ucppt.com/nextjs`
   - iframe 内自动登录成功

### 测试 4: 直接访问 localhost:3000

1. 访问 `http://localhost:3000/`
2. **预期结果**：
   - 自动重定向到 `https://www.ucppt.com/nextjs`
   - （进入测试 1 或 2 的流程）

## 调试技巧

### 浏览器开发者工具

**Console 日志**:
```javascript
// 自动 SSO 成功
✅ SSO Token 验证成功 (WordPress SSO 格式): songci

// 自动 SSO 失败（WordPress 未登录）
自动 SSO 失败: Error: 401 Unauthorized
```

**Network 面板**:
- 检查 `get-token` 请求是否发送 Cookie
- 检查响应状态码（200 = 成功，401 = 未登录）
- 检查 CORS 头部是否正确

### 常见问题排查

#### 问题 1: CORS 错误

**错误信息**:
```
Access to fetch at 'https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token'
from origin 'http://localhost:3000' has been blocked by CORS policy
```

**解决**: 在 WordPress 插件中添加 CORS 头部（见上文）

#### 问题 2: 未发送 Cookie

**现象**: 请求返回 401，但 WordPress 确实已登录

**原因**: `credentials: 'include'` 未生效

**解决**:
1. 确认 fetch 请求包含 `credentials: 'include'`
2. 确认 WordPress 响应包含 `Access-Control-Allow-Credentials: true`
3. 浏览器安全策略可能阻止第三方 Cookie（Safari/Firefox 隐私模式）

#### 问题 3: iframe 内无限加载

**现象**: 显示"加载中..."转圈，永不结束

**排查**:
1. 打开浏览器控制台，检查是否有 JavaScript 错误
2. 检查 Network 面板，`get-token` 请求是否卡住
3. 检查 `setIsLoading(false)` 是否在所有分支都执行

**解决**: 在 `catch` 块中确保调用 `setIsLoading(false)`

#### 问题 4: Token 验证失败

**错误信息**: `Token 验证失败: invalid signature`

**原因**: JWT 密钥不一致

**解决**: 确认 WordPress `PYTHON_JWT_SECRET` 与 Python `.env` 中的 `JWT_SECRET_KEY` 完全一致

## 性能优化

### 1. 减少不必要的 API 调用

当前实现：每次 AuthContext 初始化都调用 `get-token`

**优化**（可选）：
```typescript
// 只在首次加载或 Token 过期时调用
if (!localStorage.getItem('wp_jwt_token')) {
  // 调用 get-token
}
```

### 2. 缓存 Token

**当前**: Token 存储在 localStorage，刷新页面不会重复调用 `get-token`

**未来优化**: 添加 Token 过期时间检查，过期前 5 分钟自动续期

## 安全考虑

### 1. CORS 配置

**开发环境**:
```php
Access-Control-Allow-Origin: http://localhost:3000
```

**生产环境**:
```php
Access-Control-Allow-Origin: https://ai.ucppt.com
```

**不要使用通配符** `*`，否则任何网站都可以获取用户 Token！

### 2. HTTPS 要求

**生产环境必须使用 HTTPS**：
- WordPress: `https://www.ucppt.com`
- Next.js: `https://ai.ucppt.com`

HTTP 环境下 Cookie 可能不会发送（浏览器安全策略）。

### 3. Token 有效期

**当前**: JWT Token 有效期 24 小时（插件默认）

**建议**: 生产环境缩短为 2-4 小时，增加安全性。

## 版本历史

- **v2.4** (2025-12-13): iframe 自动 SSO 登录，无需跳转到 `ucppt.com/js`
- **v2.3.1** (2025-12-13): 主页自动重定向到 WordPress 嵌入页面
- **v2.3** (2025-12-13): 新增 `[nextjs_app]` 短代码，支持 iframe 嵌入
- **v2.2** (2025-12-13): 登录/注册引导页优化
- **v2.1** (2025-12-12): JWT 密钥统一修复
- **v2.0** (2025-12-12): 初始 SSO 集成

## 下一步优化

1. **Token 自动续期**: 过期前 5 分钟自动刷新
2. **离线检测**: 网络断开时显示友好提示
3. **多标签页同步**: 一个标签页登录，其他标签页自动刷新
4. **WPCOM Member API 集成**: 获取会员等级、订单、钱包数据

## 成功标准 ✅

- [x] WordPress 已登录用户访问嵌入页面，iframe 自动登录成功
- [x] WordPress 未登录用户看到登录引导，登录后 iframe 自动加载
- [x] 不再跳转到 `ucppt.com/js`（除非用户手动点击"重新登录应用"）
- [x] 用户体验流畅，无感知登录
- [x] 直接访问 localhost:3000 自动重定向到 WordPress 嵌入页面
- [x] 退出登录流程正常工作
