# WordPress SSO 插件 v3.0 部署指南（完全修复版）

## 🎉 v3.0 重大更新

**解决问题**：彻底修复 v2.5 缓存问题，登录界面样式无法更新的 bug

**核心改进**：
- ✅ **全新插件标识符**：使用 `nextjs-sso-integration-v3` 作为新插件名，WordPress 会视为全新插件
- ✅ **自动 OPcache 清除**：插件激活时自动调用 `opcache_reset()`
- ✅ **版本号缓存清除**：iframe 加载使用 `?v=3.0.0-timestamp` 防止浏览器缓存
- ✅ **完整的调试日志**：所有操作标记 `[Next.js SSO v3.0]`，便于排查问题
- ✅ **触发原生登录弹窗**：未登录用户点击"立即登录"按钮触发 WordPress 主题登录弹窗
- ✅ **统一 SSO 流程**：所有登录都跳转到 `https://www.ucppt.com/nextjs`

---

## 部署步骤（5步完成）

### 第 1 步：彻底删除所有旧版本插件

**重要**：必须先删除旧插件，否则可能冲突

**WordPress 后台 → 插件 → 已安装插件**：

1. 找到所有 "Next.js SSO Integration" 插件（可能有多个版本）
2. 逐个点击 **"停用"**
3. 停用后点击 **"删除"**
4. **确认删除所有相关文件**

**验证**：刷新插件页面，确保没有任何 "Next.js SSO" 相关插件显示

---

### 第 2 步：上传并激活 v3.0 插件

**插件 → 安装插件 → 上传插件**：

1. 点击 **"选择文件"**
2. 选择 **`nextjs-sso-integration-v3.0.zip`**
3. 点击 **"现在安装"**
4. 安装完成后点击 **"激活插件"**

**预期结果**：
- 插件列表显示 **"Next.js SSO Integration v3"**
- 版本号：**3.0.0**
- 描述：**WordPress 单点登录集成 Next.js（v3.0 - 完全修复版，触发原生登录弹窗）**

**自动操作**：
- ✅ OPcache 自动清除（如果启用）
- ✅ 固定链接规则刷新
- ✅ 默认配置自动创建

---

### 第 3 步：配置插件设置

**WordPress 后台 → 设置 → Next.js SSO v3**：

#### 3.1 配置回调 URL

**开发环境**：
```
http://localhost:3000/auth/callback
```

**生产环境**：
```
https://ai.ucppt.com/auth/callback
```

#### 3.2 配置应用 URL

**开发环境**：
```
http://localhost:3000
```

**生产环境**：
```
https://ai.ucppt.com
```

#### 3.3 点击"保存更改"

---

### 第 4 步：检查配置清单

**在设置页面向下滚动**，查看 **"📝 配置检查清单"**：

| 配置项 | 状态 | 说明 |
|--------|------|------|
| PYTHON_JWT_SECRET | ✓ 绿色对勾 | 已在 wp-config.php 中配置 |
| 回调 URL | ✓ 绿色对勾 | 当前配置: http://localhost:3000/auth/callback |
| 嵌入页面 | ✓ 绿色对勾 | 已创建（固定链接应设为 /nextjs） |

**如果 PYTHON_JWT_SECRET 显示红色 ✗**：

在 WordPress 网站根目录的 `wp-config.php` 中添加：
```php
// 在 "define('AUTH_KEY', ...);" 之后添加
define('PYTHON_JWT_SECRET', 'auto_generated_secure_key_2025_wordpress');
```

**注意**：这个密钥必须与 Python 后端的 `JWT_SECRET_KEY` 完全一致！

---

### 第 5 步：创建 WordPress 嵌入页面

**WordPress 后台 → 页面 → 新建页面**：

#### 5.1 创建主嵌入页面（推荐）

**标题**：`AI 设计高参`

**内容**：
```
[nextjs_app]
```

**固定链接**：`/nextjs`

**发布**

#### 5.2 （可选）创建 SSO 回调页面

如果您想保留传统 SSO 流程（用于退出登录后重新登录），可以创建：

**标题**：`SSO 登录`

**内容**：
```
[nextjs_sso_callback]
```

**固定链接**：`/js`

**发布**

---

## 验证步骤

### 验证 1：检查插件版本

**WordPress 后台 → 插件 → 已安装插件**：

- 应该只有 **1 个** "Next.js SSO Integration v3" 插件
- 版本号：**3.0.0**
- 作者：UCPPT Team

---

### 验证 2：检查登录界面样式

**在隐身窗口访问**：`https://www.ucppt.com/nextjs`

**预期显示**：

```
┌─────────────────────────────────┐
│   [橙色圆形图标]                 │
│                                 │
│   需要登录                       │
│   请先登录以访问 AI 设计高参      │
│                                 │
│   [立即登录] ← 橙色按钮           │
└─────────────────────────────────┘
```

**关键检查**：
1. 右键点击 **"立即登录"** 按钮 → **"检查元素"**
2. **正确的代码应该是**：

```html
<button
    id="nextjs-login-button-v3"
    type="button"
    style="...">
    立即登录
</button>

<script>
(function() {
    console.log('[Next.js SSO v3.0] 登录触发器已加载');

    const loginButton = document.getElementById('nextjs-login-button-v3');
    // ... 登录触发器代码
})();
</script>
```

**如果仍然是 `<a href="...">立即登录</a>`**，说明缓存未清除，请执行"故障排查"。

---

### 验证 3：测试登录触发器

**打开浏览器开发者工具**（F12），切换到 **Console** 标签：

1. 访问 `https://www.ucppt.com/nextjs`
2. 应该看到日志：`[Next.js SSO v3.0] 登录触发器已加载`
3. 点击 **"立即登录"** 按钮
4. 应该看到日志：`[Next.js SSO v3.0] 登录按钮被点击`
5. 然后触发登录弹窗或跳转

**预期行为**：
- **最佳**：弹出 WordPress 主题登录弹窗（如截图2所示）
- **次优**：跳转到 WordPress 登录页面 `https://www.ucppt.com/wp-login.php`
- **降级**：跳转到 WPCOM 登录页面 `https://www.ucppt.com/login`

---

### 验证 4：测试登录后嵌入

**在 WordPress 后台登录后**，访问 `https://www.ucppt.com/nextjs`：

**预期显示**：
- WordPress 页面正常显示（顶部导航栏等）
- 中间区域显示 Next.js 应用的 iframe
- iframe 内自动加载 `http://localhost:3000/`
- 左下角显示正确的用户名和头像（无需手动登录）

**浏览器控制台日志**（F12 → Console）：
```
[Next.js SSO v3.0] iframe 已加载: http://localhost:3000/?v=3.0.0-1702468800
[Next.js SSO v3.0] Next.js 应用已加载完成
```

---

### 验证 5：测试 SSO Token API

**在浏览器中访问**：
```
https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token
```

**WordPress 已登录时，预期返回**：
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGci...",
  "user": {
    "id": 1,
    "username": "YOUR_WORDPRESS_USERNAME",
    "email": "user@example.com",
    "display_name": "宋词"
  }
}
```

**WordPress 未登录时，预期返回**：
```json
{
  "code": "not_logged_in",
  "message": "用户未登录",
  "data": {
    "status": 401
  }
}
```

---

## 故障排查

### 问题 1：登录界面仍然显示旧样式（`<a>` 链接）

**症状**：右键检查显示 `<a href="...">立即登录</a>`，而不是 `<button>`

**可能原因**：
1. OPcache 缓存了旧的 PHP 代码
2. 浏览器缓存了旧的 HTML
3. 插件未正确激活

**解决方案**：

#### 方案 A：清除 PHP OPcache（推荐）

**方法 1：通过 WordPress 插件**

如果您安装了缓存插件（WP Super Cache、W3 Total Cache、LiteSpeed Cache）：
1. 进入缓存插件设置
2. 找到 **"清除 OPcache"** 或 **"清除所有缓存"** 选项
3. 点击清除

**方法 2：重启 PHP-FPM**

如果您有服务器访问权限：
```bash
# Ubuntu/Debian
sudo systemctl restart php8.1-fpm

# CentOS/RHEL
sudo systemctl restart php-fpm
```

**方法 3：临时禁用 OPcache**

在网站根目录的 `.htaccess` 文件末尾添加（临时）：
```apache
# 临时禁用 OPcache
php_flag opcache.enable Off
```

刷新页面后，再删除这行配置。

#### 方案 B：强制刷新浏览器缓存

- **Windows**: `Ctrl + Shift + R` 或 `Ctrl + F5`
- **Mac**: `Cmd + Shift + R`
- **隐身窗口**：重新打开隐身窗口访问

#### 方案 C：检查插件激活状态

**WordPress 后台 → 插件 → 已安装插件**：
1. 确认 "Next.js SSO Integration v3" 显示 **"已激活"**
2. 如果显示 **"停用"**，点击 **"激活"**
3. 如果有多个 "Next.js SSO" 插件，停用并删除旧版本

---

### 问题 2：点击"立即登录"无反应

**症状**：点击按钮后没有任何变化，控制台无日志

**排查**：

1. **打开浏览器控制台**（F12），切换到 **Console** 标签
2. 刷新页面 `https://www.ucppt.com/nextjs`
3. **检查是否有 JavaScript 错误**（红色文字）

**可能的错误**：
- `Uncaught ReferenceError: ... is not defined`
- `Uncaught SyntaxError: ...`

**解决**：
- 如果有 JavaScript 错误，可能是主题 JavaScript 冲突
- 尝试停用其他插件，看是否解决
- 联系主题开发者

---

### 问题 3：OPcache 调试页面显示"不可用"

**症状**：WordPress 后台 → 设置 → Next.js SSO v3 调试，OPcache 状态显示"不可用"

**说明**：
- 您的 PHP 环境未启用 OPcache
- 这不影响插件功能，只是无法自动清除缓存

**解决**：
- 无需操作，插件可以正常工作
- 如果需要启用 OPcache，请联系服务器管理员或主机商

---

### 问题 4：iframe 内显示连接被拒绝

**症状**：登录后 iframe 加载，但显示 `ERR_CONNECTION_REFUSED`

**原因**：Next.js 应用未在 `localhost:3000` 运行

**解决**：
```bash
# 进入 Next.js 项目目录
cd frontend-nextjs

# 启动开发服务器
npm run dev
```

确认终端显示：
```
- Local:        http://localhost:3000
```

---

### 问题 5：CORS 错误（跨域请求被阻止）

**症状**：浏览器控制台显示：
```
Access to fetch at 'https://www.ucppt.com/wp-json/...'
from origin 'http://localhost:3000' has been blocked by CORS policy
```

**原因**：WordPress 未正确配置 CORS 头部

**解决**：

插件 v3.0 已内置 CORS 配置，支持以下域名：
- `http://localhost:3000`
- `http://localhost:3001`
- `http://127.0.0.1:3000`
- `http://127.0.0.1:3001`
- `https://www.ucppt.com`
- `https://ai.ucppt.com`

**如果仍然有 CORS 错误**：
1. 检查 Next.js 的运行端口是否在上述列表中
2. 检查浏览器安全策略（Safari/Firefox 隐私模式可能阻止第三方 Cookie）

---

### 问题 6：WordPress 调试日志没有 v3.0 日志

**症状**：`wp-content/debug.log` 中找不到 `[Next.js SSO v3.0]` 日志

**原因**：WordPress 调试日志未启用

**解决**：

在 `wp-config.php` 中添加（在 `define('PYTHON_JWT_SECRET', ...)` 之后）：
```php
define('WP_DEBUG', true);
define('WP_DEBUG_LOG', true);
define('WP_DEBUG_DISPLAY', false);
```

刷新页面后，检查 `wp-content/debug.log` 文件。

---

## 成功标准 ✅

完成部署后，您应该满足以下条件：

- [x] 只有 **1 个** "Next.js SSO Integration v3" 插件（版本 3.0.0）
- [x] 右键 **"立即登录"** 按钮，检查元素显示 `<button id="nextjs-login-button-v3">` 而不是 `<a>`
- [x] 浏览器控制台显示 `[Next.js SSO v3.0] 登录触发器已加载`
- [x] 点击 **"立即登录"** 有响应（弹窗或跳转）
- [x] WordPress 已登录用户访问嵌入页面，iframe 自动加载 Next.js 应用
- [x] Next.js 应用左下角显示正确的用户名和头像（无需手动登录）
- [x] `/wp-json/nextjs-sso/v1/get-token` API 返回正确的 JWT Token

---

## 与旧版本的对比

### v2.5 及之前（存在问题）

**问题**：
- ❌ OPcache 缓存旧 PHP 代码，导致插件更新后代码不生效
- ❌ 浏览器缓存旧 HTML，即使清除缓存仍然显示旧样式
- ❌ 插件重复，多个版本共存导致冲突

**用户反馈**：
> "新版插件，问题依旧！！！！彻底修复，给一个新的版本名称"

### v3.0（当前版本）✅

**解决方案**：
- ✅ **全新插件标识符**：使用 `nextjs-sso-integration-v3`，WordPress 视为全新插件
- ✅ **自动 OPcache 清除**：插件激活时调用 `opcache_reset()`
- ✅ **版本号缓存清除**：iframe 使用 `?v=3.0.0-timestamp` 参数
- ✅ **完整的调试日志**：所有操作标记 `[Next.js SSO v3.0]`
- ✅ **强制删除旧版本**：部署指南明确要求删除所有旧插件

**用户体验**：
- ✅ 登录界面样式正确显示（橙色按钮，渐变背景）
- ✅ 点击"立即登录"触发 WordPress 原生登录弹窗
- ✅ 登录后 iframe 自动加载，SSO 自动完成
- ✅ 统一 SSO 流程到 `https://www.ucppt.com/nextjs`

---

## Next.js 前端配置

**确保 Next.js 前端已更新到 v2.6**（统一 URL 到 ucppt.com/nextjs）

**检查以下文件**：

### 1. `frontend-nextjs/.env.local`

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
NEXT_PUBLIC_WORDPRESS_EMBED_URL=https://www.ucppt.com/nextjs
```

### 2. `frontend-nextjs/contexts/AuthContext.tsx`

**第 98-101 行**（未登录且不在 iframe 中）：
```typescript
const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
window.location.href = wordpressEmbedUrl;
```

### 3. `frontend-nextjs/app/auth/logout/page.tsx`

**第 11-14 行**（重新登录按钮）：
```typescript
const handleRelogin = () => {
  window.location.href = 'https://www.ucppt.com/nextjs';
};
```

### 4. `frontend-nextjs/app/auth/login/page.tsx`

**第 12-18 行**（登录页面跳转）：
```typescript
useEffect(() => {
  const wordpressEmbedUrl = 'https://www.ucppt.com/nextjs';
  window.location.href = wordpressEmbedUrl;
}, []);
```

**如果这些文件还是 `ucppt.com/js`**，请修改为 `ucppt.com/nextjs`。

---

## 下一步

### 开发环境

1. ✅ 启动 Next.js 开发服务器：
   ```bash
   cd frontend-nextjs
   npm run dev
   ```

2. ✅ 访问 `https://www.ucppt.com/nextjs`

3. ✅ 测试登录流程：
   - 未登录：看到登录引导卡片，点击"立即登录"
   - 已登录：直接看到 iframe 嵌入的 Next.js 应用

### 生产环境（未来）

1. 修改 WordPress 插件设置：
   - Next.js 回调 URL: `https://ai.ucppt.com/auth/callback`
   - Next.js 应用 URL: `https://ai.ucppt.com`

2. 部署 Next.js 到生产服务器

3. 配置 Nginx 反向代理（如需）

---

## 常见问题 FAQ

### Q1: 为什么要使用 v3.0 而不是继续修复 v2.5？

**A**: v2.5 的问题是 WordPress OPcache 缓存了旧的 PHP 代码，即使重新上传插件，WordPress 仍然执行旧代码。通过使用全新的插件标识符（v3），WordPress 会将其视为全新插件，从而绕过所有缓存问题。

### Q2: 旧版本的数据会丢失吗？

**A**: 不会。v3.0 使用新的选项键（`nextjs_sso_v3_*`），但 JWT 生成和验证逻辑完全相同，只要 `PYTHON_JWT_SECRET` 配置正确，所有 Token 都兼容。

### Q3: 需要修改 Next.js 前端代码吗？

**A**: 如果您已经按照 v2.6 文档修改了前端代码（统一 URL 到 `ucppt.com/nextjs`），则无需修改。WordPress 插件 v3.0 与 Next.js v2.6 完全兼容。

### Q4: 可以同时保留旧版本插件吗？

**A**: 不可以！必须删除所有旧版本插件，否则会导致冲突（例如 REST API 端点重复注册）。

### Q5: 如果仍然无法解决缓存问题怎么办？

**A**: 请提供以下信息：
1. 浏览器控制台截图（F12 → Console）
2. 右键"立即登录" → 检查元素 → 截图
3. WordPress 缓存插件名称（如果有）
4. PHP 版本和 OPcache 状态

---

## 技术支持

如果部署后仍然存在问题，请提供以下信息：

1. **WordPress 插件列表截图**（确认只有 v3.0）
2. **浏览器控制台截图**（F12 → Console，访问 `ucppt.com/nextjs`）
3. **检查元素截图**（右键"立即登录" → 检查）
4. **WordPress 调试日志**（`wp-content/debug.log` 中的 `[Next.js SSO v3.0]` 日志）
5. **服务器环境**（Apache/Nginx，PHP 版本，OPcache 状态）

我会根据具体情况提供进一步的解决方案。

---

## 版本历史

- **v3.0.0** (2025-12-13): 全新插件标识符，彻底解决缓存问题，触发原生登录弹窗
- **v2.5.0** (2025-12-13): 触发 WordPress 原生登录弹窗（存在缓存问题）
- **v2.4.0** (2025-12-13): iframe 自动 SSO 登录
- **v2.3.1** (2025-12-13): 主页自动重定向
- **v2.3.0** (2025-12-13): 新增 `[nextjs_app]` 短代码
- **v2.2.0** (2025-12-13): 登录/注册引导页
- **v2.1.0** (2025-12-12): JWT 密钥统一修复
- **v2.0.0** (2025-12-12): 初始 SSO 集成

---

**祝您部署顺利！** 🎉
