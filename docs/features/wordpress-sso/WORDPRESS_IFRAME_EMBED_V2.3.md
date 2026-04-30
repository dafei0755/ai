# WordPress 嵌入 Next.js 应用指南 v2.3

## 更新内容

**v2.3** (2025-12-13): 新增 `[nextjs_app]` 短代码，支持将 Next.js 应用嵌入 WordPress 页面

## 实现方式

### iframe 嵌入架构

```
WordPress 页面 (ucppt.com/ai1-01)
    │
    ├─ WordPress 导航栏（顶部）
    ├─ WordPress 页面内容
    ├─ [nextjs_app] 短代码
    │   ↓
    │   生成 iframe
    │   ↓
    │   <iframe src="http://localhost:3000">
    │       Next.js 应用运行在独立的 origin
    │   </iframe>
    │
    └─ WordPress 页脚
```

## 部署步骤

### 1. 更新 WordPress 插件

**操作**：
1. WordPress 后台 → 插件 → 已安装插件
2. 停用并删除旧版 "Next.js SSO Integration"
3. 插件 → 安装插件 → 上传插件
4. 选择 `nextjs-sso-integration-v2.3.zip`
5. 上传并激活

### 2. 配置 Next.js 应用 URL

**操作**：
1. WordPress 后台 → 设置 → Next.js SSO
2. 找到 "Next.js 应用 URL" 设置项
3. 配置 URL：
   - **开发环境**：`http://localhost:3000`
   - **生产环境**：`https://ai.ucppt.com`
4. 点击"保存更改"

### 3. 创建 WordPress 页面

**操作**：
1. WordPress 后台 → 页面 → 新建页面
2. 页面标题：例如 "AI 设计高参"
3. 页面内容：输入短代码
   ```
   [nextjs_app]
   ```
4. 设置固定链接：例如 `/ai1-01`
5. 发布页面

### 4. 访问嵌入的应用

**URL**: https://www.ucppt.com/ai1-01

**效果**：
- ✅ WordPress 导航栏显示在顶部
- ✅ Next.js 应用嵌入在页面中
- ✅ 滚动条在 iframe 内部
- ✅ WordPress 页脚显示在底部

## 短代码参数

### 基础用法

```php
[nextjs_app]
```

**默认效果**：
- iframe 高度：100vh（全屏高度）
- iframe src：http://localhost:3000/（应用首页）

### 自定义高度

```php
[nextjs_app height="800px"]
```

**效果**：iframe 高度固定为 800px

### 指定应用路径

```php
[nextjs_app url="/analysis/123"]
```

**效果**：iframe 加载 http://localhost:3000/analysis/123

### 组合参数

```php
[nextjs_app height="90vh" url="/report/456"]
```

**效果**：
- iframe 高度：90vh
- iframe src：http://localhost:3000/report/456

## 用户登录状态处理

### 已登录用户

```
用户访问 ucppt.com/ai1-01
    ↓
WordPress 检测用户已登录
    ↓
直接显示 iframe，嵌入 Next.js 应用
    ↓
iframe 加载 localhost:3000
    ↓
Next.js 检测无本地 Token
    ↓
跳转到 ucppt.com/js（SSO 登录引导页）
    ↓
自动生成 JWT Token
    ↓
跳转回 localhost:3000/auth/callback
    ↓
Token 验证成功，保存到 localStorage
    ↓
显示 Next.js 应用首页
```

### 未登录用户

```
未登录用户访问 ucppt.com/ai1-01
    ↓
WordPress 检测用户未登录
    ↓
显示登录引导界面（橙色卡片）
    ↓
"需要登录，请先登录以访问 AI 设计高参"
    ↓
点击"立即登录"按钮
    ↓
跳转到 WordPress 登录页
    ↓
登录成功后返回 ucppt.com/ai1-01
    ↓
显示 iframe，嵌入 Next.js 应用
```

## iframe 特性

### 1. 无边框

```css
border: none;
```

**效果**：iframe 与 WordPress 页面无缝集成

### 2. 自适应宽度

```css
width: 100%;
```

**效果**：iframe 宽度跟随 WordPress 内容区宽度

### 3. 允许剪贴板

```html
allow="clipboard-read; clipboard-write"
```

**效果**：Next.js 应用可以读取和写入剪贴板

### 4. 支持滚动

```html
scrolling="yes"
```

**效果**：iframe 内部可以滚动

## 安全限制

### iframe 消息通信

WordPress 页面只接受来自以下 origin 的消息：
- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `https://ai.ucppt.com`

**防护目的**：防止恶意脚本通过 postMessage 攻击

### CORS 配置

Next.js 应用需要配置允许在 iframe 中运行：

**next.config.mjs**:
```javascript
const nextConfig = {
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'ALLOW-FROM https://www.ucppt.com'
          },
          {
            key: 'Content-Security-Policy',
            value: "frame-ancestors 'self' https://www.ucppt.com http://localhost:* http://127.0.0.1:*"
          }
        ]
      }
    ]
  }
};
```

**注意**：需要重启 Next.js 服务后生效。

## iframe 高度自适应（可选）

### Next.js 端发送高度消息

**创建文件**: `frontend-nextjs/lib/iframe-messenger.ts`

```typescript
// 向父窗口发送高度调整消息
export function sendHeightToParent() {
  if (window.parent === window) {
    // 不在 iframe 中
    return;
  }

  const height = document.documentElement.scrollHeight;

  window.parent.postMessage({
    type: 'resize',
    height: height
  }, '*'); // 生产环境应指定具体 origin
}

// 监听内容变化，自动调整高度
export function setupIframeHeightSync() {
  if (typeof window === 'undefined' || window.parent === window) {
    return;
  }

  // 初始发送
  sendHeightToParent();

  // 监听窗口大小变化
  window.addEventListener('resize', sendHeightToParent);

  // 监听 DOM 变化
  const observer = new MutationObserver(sendHeightToParent);
  observer.observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true
  });
}
```

### 在 Next.js layout 中使用

**frontend-nextjs/app/layout.tsx**:
```typescript
'use client';

import { useEffect } from 'react';
import { setupIframeHeightSync } from '@/lib/iframe-messenger';

export default function RootLayout({ children }) {
  useEffect(() => {
    setupIframeHeightSync();
  }, []);

  return (
    <html>
      <body>{children}</body>
    </html>
  );
}
```

## 生产环境部署

### 1. 修改 WordPress 设置

**WordPress 后台 → 设置 → Next.js SSO**:
- Next.js 回调 URL: `https://ai.ucppt.com/auth/callback`
- Next.js 应用 URL: `https://ai.ucppt.com`

### 2. 更新 WordPress 页面短代码

**无需修改**，短代码会自动使用配置的 URL：
```php
[nextjs_app]
```

**渲染后的 iframe src**:
```html
<iframe src="https://ai.ucppt.com/"></iframe>
```

### 3. Next.js 生产部署

**部署到 ai.ucppt.com**：
```bash
cd frontend-nextjs
npm run build
npm run start
```

**Nginx 配置** (示例):
```nginx
server {
    listen 443 ssl;
    server_name ai.ucppt.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 测试清单

### 开发环境测试

- [ ] WordPress 安装并激活 v2.3 插件
- [ ] WordPress 设置中配置 `http://localhost:3000`
- [ ] Next.js 应用在 `localhost:3000` 运行
- [ ] 创建 WordPress 页面，添加 `[nextjs_app]` 短代码
- [ ] 访问 WordPress 页面，看到 iframe 嵌入的 Next.js 应用
- [ ] iframe 内可以正常操作（点击、输入、滚动）
- [ ] iframe 内的 SSO 登录流程正常工作

### 生产环境测试

- [ ] 修改 WordPress 设置为 `https://ai.ucppt.com`
- [ ] 访问 WordPress 页面，iframe src 指向生产环境
- [ ] 生产环境 Next.js 应用正常加载
- [ ] 跨域策略正确配置（iframe 可以加载）
- [ ] SSO 登录流程在生产环境正常工作

## 故障排查

### 问题 1: iframe 显示空白

**原因**：Next.js 应用未运行或 URL 配置错误

**排查**：
1. 检查 Next.js 是否在 localhost:3000 运行
2. 浏览器控制台查看 iframe src 是否正确
3. WordPress 设置 → Next.js SSO → 检查"Next.js 应用 URL"配置

### 问题 2: iframe 显示"拒绝连接"

**原因**：Next.js 的 X-Frame-Options 阻止 iframe 嵌入

**解决**：
1. 修改 `next.config.mjs` 添加 headers 配置（见上文）
2. 重启 Next.js 服务：`npm run dev`

### 问题 3: iframe 内无法登录

**原因**：SSO 流程跳转导致 iframe 页面跳转

**解决**：
- 目前 SSO 流程会跳转到 ucppt.com/js，这会导致 iframe 内容变化
- 建议使用独立窗口完成登录后，iframe 自动刷新
- 或实现 iframe 内消息通信，通知父窗口处理登录

### 问题 4: iframe 高度不正确

**原因**：默认高度为 100vh，可能超出 WordPress 内容区

**解决**：
1. 使用短代码参数指定高度：`[nextjs_app height="800px"]`
2. 或实现高度自适应（见上文 iframe-messenger）

## 版本历史

- **v2.3** (2025-12-13): 新增 `[nextjs_app]` 短代码，支持 iframe 嵌入
- **v2.2** (2025-12-13): 登录/注册引导页优化
- **v2.1** (2025-12-12): JWT 密钥统一修复
- **v2.0** (2025-12-12): 初始 SSO 集成

## 下一步优化方向

1. **iframe 内 SSO 优化**：避免 iframe 内跳转，改为弹出窗口登录
2. **高度自适应**：自动调整 iframe 高度适应内容
3. **加载状态**：显示 iframe 加载进度条
4. **错误处理**：iframe 加载失败时显示友好提示
5. **Token 共享**：WordPress 直接注入 Token 到 iframe（避免二次 SSO）

## 成功标准 ✅

- [x] WordPress 页面可以通过 `[nextjs_app]` 短代码嵌入 Next.js 应用
- [x] iframe 显示 WordPress 导航栏和页脚
- [x] Next.js 应用在 iframe 中正常运行
- [x] 未登录用户看到登录引导界面
- [x] 已登录用户直接看到 iframe 嵌入的应用
- [x] 支持自定义 iframe 高度和路径
- [x] WordPress 管理后台可配置 Next.js URL
