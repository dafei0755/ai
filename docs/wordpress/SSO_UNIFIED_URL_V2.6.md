# SSO 登录统一到 WordPress 嵌入页面 v2.6

## 更新日期
2025-12-13

## 核心改进

**将所有 SSO 登录跳转统一到 `https://www.ucppt.com/nextjs`**，而不是之前的 `https://www.ucppt.com/js`。

## 变更原因

1. **简化URL结构**：只使用一个页面 (`/nextjs`) 来处理所有登录和嵌入场景
2. **统一用户体验**：用户始终看到相同的 WordPress 页面
3. **减少维护成本**：不需要同时维护 `/js` 和 `/nextjs` 两个页面

## 变更的文件

### Next.js 前端 (3个文件)

1. **`frontend-nextjs/contexts/AuthContext.tsx`** (Line 98-101)
   - 修改前：跳转到 `ucppt.com/js?redirect_url=...`
   - 修改后：跳转到 `ucppt.com/nextjs`

2. **`frontend-nextjs/app/auth/logout/page.tsx`** (Line 11-14)
   - 修改前：跳转到 `ucppt.com/js?redirect_url=...`
   - 修改后：跳转到 `ucppt.com/nextjs`

3. **`frontend-nextjs/app/auth/login/page.tsx`** (Line 12-18)
   - 修改前：跳转到 `ucppt.com/js?redirect_url=...`
   - 修改后：跳转到 `ucppt.com/nextjs`

### WordPress 后端

**无需修改**！WordPress 插件 v2.5 已经在 `ucppt.com/nextjs` 页面中实现了所有功能：
- ✅ 未登录用户显示登录引导
- ✅ 已登录用户自动加载 iframe
- ✅ iframe 内 Next.js 自动 SSO 登录

## 新的登录流程

### 场景 A: 未登录用户直接访问 Next.js

```
用户访问 http://localhost:3000/
    ↓
主页检测不在 iframe 中
    ↓
重定向到 https://www.ucppt.com/nextjs
    ↓
WordPress 检测未登录
    ↓
显示登录引导卡片（橙色）
    ↓
用户点击"立即登录"
    ↓
触发 WordPress 登录弹窗或跳转登录页
    ↓
登录成功，刷新页面
    ↓
WordPress 检测已登录 → 加载 iframe
    ↓
iframe 内 Next.js 自动获取 Token
    ↓
✅ 登录成功
```

### 场景 B: 已登录用户访问 Next.js

```
用户访问 http://localhost:3000/
    ↓
主页检测不在 iframe 中
    ↓
重定向到 https://www.ucppt.com/nextjs
    ↓
WordPress 检测已登录 → 直接加载 iframe
    ↓
iframe 内 Next.js 自动获取 Token
    ↓
✅ 登录成功（无需手动操作）
```

### 场景 C: 用户退出登录后重新登录

```
用户点击"退出登录"
    ↓
Next.js 清除本地 Token
    ↓
跳转到 /auth/logout 页面
    ↓
用户点击"重新登录应用"
    ↓
跳转到 https://www.ucppt.com/nextjs
    ↓
（进入场景 A 或 B）
```

### 场景 D: AuthContext 检测未登录（不在 iframe 中）

```
AuthContext 检测无 Token 且不在 iframe 中
    ↓
跳转到 https://www.ucppt.com/nextjs
    ↓
（进入场景 A 或 B）
```

## WordPress 页面配置

### 唯一需要的页面：`https://www.ucppt.com/nextjs`

**页面内容**：
```
[nextjs_app]
```

**固定链接**：`/nextjs`

**功能**：
1. **未登录用户**：显示登录引导卡片 → 触发登录弹窗
2. **已登录用户**：直接加载 iframe → 嵌入 Next.js 应用
3. **iframe 内 Next.js**：自动从 WordPress 获取 Token → SSO 登录成功

### 可选：删除旧页面 `https://www.ucppt.com/js`

如果您之前创建了 `/js` 页面（内容为 `[nextjs_sso_callback]`），可以选择：

**方案 1：保留但不使用**
- 保留 `/js` 页面，但所有链接都指向 `/nextjs`
- 优点：向后兼容，旧书签仍然有效
- 缺点：有两个重复功能的页面

**方案 2：删除旧页面**
- WordPress 后台 → 页面 → 找到 `/js` 页面 → 移至回收站
- 优点：简化结构，只有一个页面
- 缺点：旧书签会失效

**推荐**：保留但添加重定向

在 `/js` 页面中添加重定向脚本：
```html
<script>
window.location.href = 'https://www.ucppt.com/nextjs';
</script>
```

或者修改固定链接设置，将 `/js` 301 重定向到 `/nextjs`。

## 部署步骤

### 1. 重启 Next.js 服务

```bash
# 停止 Next.js (Ctrl+C)
cd frontend-nextjs
npm run dev
```

热重载应该会自动生效，但建议重启确保所有更改生效。

### 2. 测试登录流程

1. **清除浏览器缓存和 localStorage**：
   - 打开开发者工具（F12）
   - Application → Local Storage → 删除 `wp_jwt_token` 和 `wp_user`
   - 或者使用隐身窗口

2. **访问 `http://localhost:3000/`**：
   - 应该自动重定向到 `https://www.ucppt.com/nextjs`

3. **检查登录流程**：
   - 未登录：看到登录引导卡片
   - 已登录：直接看到 iframe 嵌入的应用

### 3. 无需更新 WordPress 插件

当前的 v2.5 插件已经支持所有功能，无需重新上传。

## 技术细节

### 环境变量

`frontend-nextjs/.env.local`:
```bash
NEXT_PUBLIC_WORDPRESS_EMBED_URL=https://www.ucppt.com/nextjs
```

所有代码都优先使用此环境变量，如果未设置则回退到硬编码的默认值。

### 代码示例

#### AuthContext.tsx（未登录且不在 iframe 中）

```typescript
else {
  // 不在 iframe 中：跳转到 WordPress 嵌入页面
  const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
  window.location.href = wordpressEmbedUrl;
  return;
}
```

#### logout/page.tsx（重新登录按钮）

```typescript
const handleRelogin = () => {
  // 跳转到 WordPress 嵌入页面
  window.location.href = 'https://www.ucppt.com/nextjs';
};
```

#### login/page.tsx（登录页面跳转）

```typescript
useEffect(() => {
  const wordpressEmbedUrl = 'https://www.ucppt.com/nextjs';
  window.location.href = wordpressEmbedUrl;
}, []);
```

## 与之前版本的对比

### v2.5 及之前

```
用户 → localhost:3000
    ↓ 检测未登录
    ↓ 跳转到 ucppt.com/js
    ↓ SSO 生成 Token
    ↓ 跳转到 localhost:3000/auth/callback?token=...
    ↓ 验证 Token
    ↓ 跳转到 localhost:3000/
    ↓ 主页检测不在 iframe 中
    ↓ 重定向到 ucppt.com/nextjs
    ↓ 加载 iframe（又要验证一次！）
```

**问题**：多次跳转，用户体验不佳。

### v2.6 (当前)

```
用户 → localhost:3000
    ↓ 检测不在 iframe 中
    ↓ 重定向到 ucppt.com/nextjs（一步到位）
    ↓ WordPress 检测登录状态
    ├─ 未登录 → 显示登录引导
    └─ 已登录 → 加载 iframe → 自动 SSO
```

**优势**：减少跳转次数，统一入口。

## 故障排查

### 问题 1: 重定向循环

**症状**: 页面不断刷新，URL 在 `localhost:3000` 和 `ucppt.com/nextjs` 之间跳转

**原因**: iframe 检测失败或 localStorage 未清除

**解决**:
1. 清除 localStorage
2. 检查浏览器控制台错误
3. 确认 iframe 检测逻辑：`window.self !== window.top`

### 问题 2: 仍然跳转到 `/js` 页面

**原因**: 代码未更新或缓存问题

**解决**:
1. 确认 Next.js 服务已重启
2. 清除浏览器缓存（Ctrl + Shift + R）
3. 检查代码是否正确更新（查看源码）

### 问题 3: WordPress 登录后未加载 iframe

**原因**: WordPress 插件版本过旧（< v2.5）

**解决**:
1. 确认插件版本为 v2.5.0
2. 重新上传 `nextjs-sso-integration-v2.5-clean.zip`
3. 清除 WordPress OPcache

## 成功标准 ✅

- [x] 直接访问 `localhost:3000` 自动重定向到 `ucppt.com/nextjs`
- [x] 未登录用户看到登录引导卡片
- [x] 已登录用户直接看到 iframe 嵌入应用
- [x] 退出登录后点击"重新登录"跳转到 `ucppt.com/nextjs`
- [x] 所有代码中不再出现 `ucppt.com/js`（除了文档）

## 版本历史

- **v2.6** (2025-12-13): SSO 登录统一到 `ucppt.com/nextjs`
- **v2.5** (2025-12-13): 触发 WordPress 原生登录弹窗
- **v2.4** (2025-12-13): iframe 自动 SSO 登录
- **v2.3.1** (2025-12-13): 主页自动重定向
- **v2.3** (2025-12-13): iframe 嵌入支持
- **v2.2** (2025-12-13): 登录/注册引导页
- **v2.1** (2025-12-12): JWT 密钥统一
- **v2.0** (2025-12-12): 初始 SSO 集成
