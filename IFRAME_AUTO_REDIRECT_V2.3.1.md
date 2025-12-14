# Next.js 自动重定向到 WordPress 嵌入页面 v2.3.1

## 更新内容

**v2.3.1** (2025-12-13): Next.js 主页自动检测 iframe，非 iframe 访问时重定向到 WordPress 嵌入页面

## 问题背景

用户希望当直接访问 `http://localhost:3000/` 时，自动跳转到 WordPress 嵌入页面 `https://www.ucppt.com/nextjs`，确保用户始终通过 WordPress 页面访问应用（保持 WordPress 导航栏的一致性）。

## 实现方式

### 1. iframe 检测逻辑

在 Next.js 主页 (`app/page.tsx`) 添加 `useEffect` hook 检测是否在 iframe 中运行：

```typescript
useEffect(() => {
  // 检测是否在 iframe 中
  const isInIframe = window.self !== window.top;

  // 如果不在 iframe 中，重定向到 WordPress 嵌入页面
  if (!isInIframe) {
    const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
    window.location.href = wordpressEmbedUrl;
  }
}, []);
```

### 2. 环境变量配置

在 `.env.local` 中添加 WordPress 嵌入页面 URL：

```bash
# WordPress 嵌入页面 URL
NEXT_PUBLIC_WORDPRESS_EMBED_URL=https://www.ucppt.com/nextjs
```

## 用户访问流程

### 场景 A: 直接访问 Next.js URL（新流程）

```
用户访问 http://localhost:3000/
    ↓
Next.js 主页加载
    ↓
检测 window.self !== window.top
    ↓
发现不在 iframe 中 ❌
    ↓
自动重定向到 https://www.ucppt.com/nextjs
    ↓
WordPress 页面加载，嵌入 Next.js iframe
    ↓
iframe 内部加载 http://localhost:3000/
    ↓
检测 window.self !== window.top
    ↓
发现在 iframe 中 ✅
    ↓
正常显示 Next.js 应用
```

### 场景 B: 通过 WordPress 嵌入页面访问（正常流程）

```
用户访问 https://www.ucppt.com/nextjs
    ↓
WordPress 页面加载
    ↓
iframe 嵌入 http://localhost:3000/
    ↓
Next.js 主页在 iframe 中加载
    ↓
检测 window.self !== window.top
    ↓
发现在 iframe 中 ✅
    ↓
正常显示 Next.js 应用
```

### 场景 C: 深层链接访问（分析页面、报告页面等）

```
用户访问 http://localhost:3000/analysis/abc123
    ↓
分析页面直接加载（无重定向）
    ↓
正常显示分析流程
```

**注意**：深层链接不做重定向检测，允许用户通过直接链接访问特定页面（便于分享和书签）。

## 代码变更

### 修改的文件 (2个)

#### 1. `frontend-nextjs/app/page.tsx`

**新增代码**（Line 39-50）：

```typescript
// 🔥 检测是否在 iframe 中运行，如果不是则重定向到 WordPress 嵌入页面
useEffect(() => {
  // 检测是否在 iframe 中
  const isInIframe = window.self !== window.top;

  // 如果不在 iframe 中，重定向到 WordPress 嵌入页面
  if (!isInIframe) {
    // 开发环境和生产环境的 WordPress 嵌入页面 URL
    const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
    window.location.href = wordpressEmbedUrl;
  }
}, []);
```

#### 2. `frontend-nextjs/.env.local`

**新增配置**：

```bash
# WordPress 嵌入页面 URL
NEXT_PUBLIC_WORDPRESS_EMBED_URL=https://www.ucppt.com/nextjs
```

## 部署步骤

### 开发环境

1. **无需重启服务**（Next.js 热重载会自动生效）
2. 如果修改了 `.env.local`，需要重启服务：
   ```bash
   # 停止 Next.js (Ctrl+C)
   cd frontend-nextjs
   npm run dev
   ```

### 测试步骤

1. **测试直接访问 Next.js**：
   - 在新的浏览器标签页打开 `http://localhost:3000/`
   - 应该自动重定向到 `https://www.ucppt.com/nextjs`
   - WordPress 页面显示，iframe 中嵌入 Next.js 应用

2. **测试通过 WordPress 访问**：
   - 直接访问 `https://www.ucppt.com/nextjs`
   - 应该正常显示 WordPress 页面 + iframe 嵌入应用
   - 无额外跳转

3. **测试深层链接**：
   - 访问 `http://localhost:3000/analysis/xxx`（某个实际的会话ID）
   - 应该直接显示分析页面（不重定向）

## 生产环境配置

### 方式 1: 使用环境变量（推荐）

创建 `.env.production` 文件：

```bash
# WordPress 嵌入页面 URL
NEXT_PUBLIC_WORDPRESS_EMBED_URL=https://www.ucppt.com/nextjs
```

### 方式 2: 硬编码默认值

如果不配置环境变量，代码中的默认值会生效：
```typescript
const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
```

## iframe 检测原理

### JavaScript Window 对象

- **`window.self`**: 当前窗口的引用
- **`window.top`**: 最顶层窗口的引用

### 检测逻辑

```javascript
const isInIframe = window.self !== window.top;
```

- **在 iframe 中**: `window.self !== window.top` 返回 `true`（当前窗口不是顶层窗口）
- **不在 iframe 中**: `window.self === window.top` 返回 `true`（当前窗口是顶层窗口）

## 优势与限制

### ✅ 优势

1. **用户体验一致**: 确保用户始终看到 WordPress 导航栏
2. **自动化**: 无需用户手动输入 WordPress URL
3. **灵活配置**: 通过环境变量支持不同环境的 URL
4. **不影响深层链接**: 允许直接访问分析页面、报告页面等

### ⚠️ 限制

1. **循环重定向风险**: 如果 WordPress 嵌入页面本身也重定向，可能形成循环（当前设计避免了此问题）
2. **跨域限制**: 部分浏览器可能阻止 `window.top` 访问（通过 try-catch 可优化）
3. **SEO 影响**: 直接访问会被重定向，可能影响搜索引擎收录（如需 SEO，建议移除重定向）

## 可选优化：处理跨域限制

如果担心某些浏览器阻止访问 `window.top`，可以添加 try-catch：

```typescript
useEffect(() => {
  let isInIframe = false;

  try {
    isInIframe = window.self !== window.top;
  } catch (e) {
    // 跨域限制导致无法访问 window.top
    // 假定在 iframe 中
    isInIframe = true;
  }

  if (!isInIframe) {
    const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
    window.location.href = wordpressEmbedUrl;
  }
}, []);
```

## 故障排查

### 问题 1: 重定向后仍然跳回 localhost:3000

**原因**: iframe 内部的 Next.js 应用也在执行重定向逻辑

**排查**:
1. 打开浏览器开发者工具 → Console
2. 检查是否有 `window.self !== window.top` 的日志
3. 如果在 iframe 中仍显示 `false`，说明检测逻辑有误

**解决**: 确认代码中的条件是 `if (!isInIframe)` 而不是 `if (isInIframe)`

### 问题 2: 环境变量未生效

**原因**: `.env.local` 修改后未重启服务

**解决**:
```bash
# 停止 Next.js 服务 (Ctrl+C)
cd frontend-nextjs
npm run dev
```

### 问题 3: WordPress 页面无法加载 iframe

**原因**: CORS 或 CSP 策略阻止

**解决**: 参考 `WORDPRESS_IFRAME_EMBED_V2.3.md` 配置 Next.js headers

## 与 v2.3 的关系

**v2.3.1 是 v2.3 的扩展**：

- **v2.3**: 实现 `[nextjs_app]` 短代码，支持 iframe 嵌入
- **v2.3.1**: 添加主页自动重定向逻辑，确保用户始终通过 WordPress 访问

两者配合使用，提供完整的 WordPress 嵌入体验。

## 版本历史

- **v2.3.1** (2025-12-13): 主页自动重定向到 WordPress 嵌入页面
- **v2.3** (2025-12-13): 新增 `[nextjs_app]` 短代码，支持 iframe 嵌入
- **v2.2** (2025-12-13): 登录/注册引导页优化
- **v2.1** (2025-12-12): JWT 密钥统一修复
- **v2.0** (2025-12-12): 初始 SSO 集成

## 成功标准 ✅

- [x] 直接访问 `http://localhost:3000/` 自动重定向到 `https://www.ucppt.com/nextjs`
- [x] WordPress 页面正常嵌入 Next.js 应用（iframe）
- [x] iframe 内部的 Next.js 不再重定向（检测到在 iframe 中）
- [x] 深层链接正常访问（不触发重定向）
- [x] 环境变量支持生产环境配置
