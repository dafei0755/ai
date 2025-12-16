# 双模式架构部署指南

## 📦 部署包清单

### 前端代码（已完成）

- ✅ [frontend-nextjs/app/page.tsx](frontend-nextjs/app/page.tsx) - 主页面（双模式逻辑）
- ✅ [frontend-nextjs/contexts/AuthContext.tsx](frontend-nextjs/contexts/AuthContext.tsx) - 认证上下文
- ✅ [frontend-nextjs/components/layout/UserPanel.tsx](frontend-nextjs/components/layout/UserPanel.tsx) - 用户面板

### WordPress插件

- ✅ [nextjs-sso-integration-v3.0.8.zip](nextjs-sso-integration-v3.0.8.zip) - WordPress插件包（14 KB）

### 文档

- ✅ [DUAL_MODE_ARCHITECTURE_IMPLEMENTATION.md](DUAL_MODE_ARCHITECTURE_IMPLEMENTATION.md) - 完整技术文档
- ✅ [DUAL_MODE_QUICK_TEST_GUIDE.md](DUAL_MODE_QUICK_TEST_GUIDE.md) - 快速测试指南
- ✅ [UNAUTHENTICATED_UI_HIDE_FIX_20251215.md](UNAUTHENTICATED_UI_HIDE_FIX_20251215.md) - 未登录界面隐藏
- ✅ [SSO_LOGIN_SYNC_FIX_20251215.md](SSO_LOGIN_SYNC_FIX_20251215.md) - 登录同步修复

---

## 🚀 部署步骤

### 步骤1: 部署前端代码（开发环境）

#### 1.1 检查代码版本

确认以下文件包含最新代码：

**frontend-nextjs/app/page.tsx** (检查 lines 412-528):
```typescript
// 🔒 v3.0.8: 未登录时显示登录提示，不显示应用界面
// 支持两种模式：iframe嵌入模式 + 独立页面模式
if (!authLoading && !user) {
  const isInIframe = typeof window !== 'undefined' && window.self !== window.top;
  const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
  const standaloneMode = urlParams?.get('mode') === 'standalone';

  // 三态UI逻辑...
}
```

**frontend-nextjs/contexts/AuthContext.tsx** (检查 lines 248-252):
```typescript
// 🔥 v3.0.8: 不在 iframe 中且没有有效 Token
// 不再自动跳转，让 app/page.tsx 显示登录提示界面
console.log('[AuthContext] 无有效登录状态，将显示登录提示界面');
setIsLoading(false);
return; // 停止执行，不跳转
```

**frontend-nextjs/components/layout/UserPanel.tsx** (检查 lines 59-63):
```typescript
// 🔒 v3.0.8: 未登录状态不显示用户面板
// 用户只能通过 WordPress 右上角的登录/退出按钮控制
if (!user) {
  return null;
}
```

#### 1.2 检查环境变量

确认 `.env` 文件包含正确的配置：

```bash
# WordPress嵌入页面URL
NEXT_PUBLIC_WORDPRESS_EMBED_URL=https://www.ucppt.com/nextjs

# API服务器地址
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

# 或生产环境API地址
# NEXT_PUBLIC_API_URL=https://api.ucppt.com
```

#### 1.3 重启开发服务器

```bash
cd frontend-nextjs
npm run dev
```

**预期输出**：
```
  ▲ Next.js 14.x.x
  - Local:        http://localhost:3000
  - Network:      http://192.168.x.x:3000

 ✓ Ready in 2.5s
```

#### 1.4 验证前端启动成功

访问 `http://localhost:3000`，应该看到：
- ✅ 模式选择界面（如果未登录）
- ✅ 完整应用界面（如果已登录）

**如果看到错误**：
- 检查控制台（F12）是否有JavaScript错误
- 检查 `npm run dev` 终端输出是否有编译错误

---

### 步骤2: 更新WordPress插件

#### 2.1 备份现有插件（可选）

在更新前，建议备份当前插件：

```bash
# WordPress后台
1. 插件 → Next.js SSO Integration v3
2. 查看当前版本号
3. 如果不是 v3.0.8，继续更新步骤
```

#### 2.2 停用旧插件

```bash
# WordPress后台
1. 插件 → 已安装的插件
2. 找到 "Next.js SSO Integration v3"
3. 点击 "停用"
```

#### 2.3 上传新插件

**方式1: WordPress后台上传**

```bash
1. 插件 → 安装插件 → 上传插件
2. 选择文件: nextjs-sso-integration-v3.0.8.zip
3. 点击 "现在安装"
4. 安装完成后点击 "启用插件"
```

**方式2: FTP上传**

```bash
# 通过FTP/SFTP上传
1. 解压 nextjs-sso-integration-v3.0.8.zip
2. 上传 nextjs-sso-integration-v3.php 到:
   /wp-content/plugins/
3. WordPress后台 → 插件 → 启用 "Next.js SSO Integration v3"
```

#### 2.4 验证插件版本

```bash
# WordPress后台
1. 插件 → 已安装的插件
2. 找到 "Next.js SSO Integration v3"
3. 确认版本号显示: "3.0.8"
4. 确认描述包含: "v3.0.8 - 登录同步优化 + 应用界面隐藏"
```

#### 2.5 配置插件设置

```bash
# WordPress后台
1. 设置 → Next.js SSO v3
2. 确认配置项:
   - Next.js App URL: http://localhost:3000 (开发) 或 https://app.ucppt.com (生产)
   - WordPress Shortcode: [nextjs-sso-app-v3]
3. 保存设置
```

---

### 步骤3: 清除所有缓存

#### 3.1 清除WordPress缓存

**WP Super Cache**:
```bash
# WordPress后台
1. 设置 → WP Super Cache
2. 点击 "删除缓存"
3. 等待缓存清除完成
```

**其他缓存插件**:
- W3 Total Cache: Performance → Purge All Caches
- WP Rocket: 清空缓存
- Cloudflare: 清除缓存（如果使用CDN）

#### 3.2 清除OPcache（如果使用）

```bash
# 方式1: WordPress后台（如果有OPcache管理插件）
工具 → OPcache Reset

# 方式2: 服务器命令行
sudo systemctl reload php-fpm
# 或
sudo service php7.4-fpm reload
```

#### 3.3 清除浏览器缓存

**强制刷新**:
```bash
Ctrl + Shift + R (Windows/Linux)
Cmd + Shift + R (Mac)
```

**或使用无痕模式**:
```bash
Ctrl + Shift + N (Chrome)
Ctrl + Shift + P (Firefox)
```

#### 3.4 清除localStorage

```javascript
// 浏览器控制台（F12）执行:
localStorage.removeItem('wp_jwt_token');
localStorage.removeItem('wp_jwt_user');
location.reload();
```

---

### 步骤4: 验证部署

按照 [DUAL_MODE_QUICK_TEST_GUIDE.md](DUAL_MODE_QUICK_TEST_GUIDE.md) 执行所有测试场景。

#### 4.1 快速验证（5分钟）

**Test 1: 模式选择界面**
```bash
访问: http://localhost:3000
预期: 显示两个按钮（WordPress嵌入模式 + 独立页面模式）
```

**Test 2: iframe嵌入模式**
```bash
访问: https://www.ucppt.com/nextjs
预期: iframe内显示 "请使用页面右上角的登录按钮登录"
```

**Test 3: 独立模式**
```bash
访问: http://localhost:3000?mode=standalone
预期: 显示 "独立模式 - 请选择登录方式"
```

#### 4.2 完整验证（20分钟）

执行 [DUAL_MODE_QUICK_TEST_GUIDE.md](DUAL_MODE_QUICK_TEST_GUIDE.md) 中的所有测试场景（A-E）。

---

## 🔍 部署后检查清单

### 功能检查

- [ ] 直接访问显示模式选择界面
- [ ] WordPress嵌入页面显示iframe登录提示
- [ ] 独立模式显示独立登录界面
- [ ] iframe可以打开独立模式（新窗口）
- [ ] 独立模式可以返回iframe模式
- [ ] 独立模式登录流程正常
- [ ] 已登录状态下任意模式显示应用界面

### 日志检查

打开浏览器控制台（F12），检查日志：

**正常日志示例**:
```javascript
// 未登录访问模式选择界面
[AuthContext] 🔍 检查 localStorage Token
[AuthContext] ❌ 未找到 Token
[HomePage] 用户未登录，清空会话列表

// iframe模式
[Next.js SSO v3.0.8] iframe 已加载
[AuthContext] 🔍 正在尝试 SSO 登录...

// 独立模式登录成功
[AuthContext] ✅ 找到缓存的 Token
[AuthContext] ✅ Token 验证成功
[AuthContext] 👤 设置用户信息: {username: "xxx", ...}
[HomePage] 获取会话列表成功: N个
```

**错误日志排查**:
```javascript
// 如果看到这些错误，需要排查:

// ❌ JavaScript语法错误
Uncaught SyntaxError: Unexpected token

// ❌ 模块导入失败
Module not found: Can't resolve '@/...'

// ❌ API连接失败
[AuthContext] ❌ SSO 请求失败: 401
[HomePage] ❌ 获取会话列表失败: Network Error

// ❌ WordPress插件未启用
[Next.js SSO v3.0.8] 检测到 WordPress 未登录
```

### 性能检查

- [ ] 页面加载时间 < 3秒
- [ ] 模式切换响应 < 1秒
- [ ] 登录流程完成 < 5秒
- [ ] 无明显UI卡顿

### 安全检查

- [ ] Token不在URL中暴露（已在SSO登录后清除URL参数）
- [ ] localStorage Token有过期时间
- [ ] HTTPS连接（生产环境）
- [ ] 跨域策略正确配置

---

## ⚠️ 常见部署问题

### 问题1: 前端启动失败

**症状**:
```bash
npm run dev
Error: Cannot find module '@/...'
```

**解决**:
```bash
# 重新安装依赖
cd frontend-nextjs
rm -rf node_modules package-lock.json
npm install
npm run dev
```

---

### 问题2: WordPress插件上传失败

**症状**:
```
上传的文件超过 php.ini 中定义的 upload_max_filesize 值。
```

**解决**:
```bash
# 修改 php.ini
upload_max_filesize = 64M
post_max_size = 64M

# 重启PHP服务
sudo systemctl restart php-fpm
```

---

### 问题3: 缓存未清除

**症状**: 更新后仍然看到旧版本界面

**解决**:
1. 清除WordPress缓存（WP Super Cache）
2. 清除浏览器缓存（Ctrl + Shift + R）
3. 清除OPcache（`sudo systemctl reload php-fpm`）
4. 使用无痕模式测试
5. 检查Cloudflare等CDN缓存

---

### 问题4: 模式检测失败

**症状**: URL有 `?mode=standalone` 但显示模式选择界面

**解决**:
```bash
# 检查前端代码是否最新
cd frontend-nextjs
git status
git pull  # 如果使用Git

# 重启开发服务器
npm run dev
```

---

### 问题5: iframe模式登录不同步

**症状**: WordPress右上角已登录，但iframe内仍显示登录提示

**解决**:
```bash
# 1. 确认WordPress插件版本为 v3.0.8
# 2. 检查WordPress插件JavaScript是否执行:
#    打开 WordPress 页面，F12控制台查看是否有:
#    [Next.js SSO v3.0.8] iframe 已加载

# 3. 如果没有日志，清除WordPress缓存
# 4. 如果有日志但登录不同步，检查postMessage:
#    控制台应该显示:
#    [Next.js SSO v3.0.8] 已通过 postMessage 发送 Token 到 iframe

# 5. 如果postMessage未发送，检查Token生成:
#    访问: https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token
#    应该返回JSON: {"success": true, "token": "...", "user": {...}}
```

---

## 📊 部署前后对比

### Before (v3.0.8 without dual-mode)

| 访问方式 | 显示内容 | 问题 |
|---------|---------|------|
| localhost:3000 | 自动重定向 | ❌ 无法直接使用 |
| www.ucppt.com/nextjs | iframe登录提示 | ⚠️ 登录不同步 |

### After (v3.0.9 with dual-mode)

| 访问方式 | 显示内容 | 状态 |
|---------|---------|------|
| localhost:3000 | 模式选择界面 | ✅ 友好引导 |
| localhost:3000?mode=standalone | 独立登录界面 | ✅ 可独立使用 |
| www.ucppt.com/nextjs | iframe登录提示 | ✅ 可切换模式 |

---

## 🎯 部署成功标准

**全部通过以下检查，即表示部署成功**:

1. ✅ 前端服务正常运行（`npm run dev`）
2. ✅ WordPress插件版本为 v3.0.8
3. ✅ 所有缓存已清除
4. ✅ 三种UI状态显示正确
5. ✅ 模式切换功能正常
6. ✅ 独立模式登录流程完整
7. ✅ 控制台无JavaScript错误
8. ✅ 日志输出正常

---

## 🚀 生产环境部署

### 前端生产构建

```bash
cd frontend-nextjs

# 构建生产版本
npm run build

# 启动生产服务器
npm start

# 或使用PM2管理进程
pm2 start npm --name "nextjs-app" -- start
pm2 save
```

### 环境变量（生产）

```bash
# .env.production
NEXT_PUBLIC_WORDPRESS_EMBED_URL=https://www.ucppt.com/nextjs
NEXT_PUBLIC_API_URL=https://api.ucppt.com
```

### NGINX配置示例

```nginx
server {
    listen 80;
    server_name app.ucppt.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### HTTPS配置

```bash
# 使用 Let's Encrypt 获取SSL证书
sudo certbot --nginx -d app.ucppt.com

# 自动续期
sudo certbot renew --dry-run
```

---

## 📚 相关文档

- [DUAL_MODE_ARCHITECTURE_IMPLEMENTATION.md](DUAL_MODE_ARCHITECTURE_IMPLEMENTATION.md) - 完整技术文档
- [DUAL_MODE_QUICK_TEST_GUIDE.md](DUAL_MODE_QUICK_TEST_GUIDE.md) - 快速测试指南
- [UNAUTHENTICATED_UI_HIDE_FIX_20251215.md](UNAUTHENTICATED_UI_HIDE_FIX_20251215.md) - 未登录界面隐藏
- [SSO_LOGIN_SYNC_FIX_20251215.md](SSO_LOGIN_SYNC_FIX_20251215.md) - 登录同步修复

---

## 🎉 部署完成

**恭喜！双模式架构已部署完成！**

用户现在可以：
- 🚀 在WordPress嵌入模式下使用应用（推荐）
- 🚀 在独立模式下直接访问应用
- 🚀 随时在两种模式之间切换
- 🚀 享受统一的认证体验

**下一步**: 根据用户反馈持续优化和改进。
