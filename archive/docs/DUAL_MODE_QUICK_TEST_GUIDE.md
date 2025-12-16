# 双模式架构快速测试指南

## 🚀 快速开始

### 前置条件

1. ✅ Next.js开发服务器运行中：`npm run dev`
2. ✅ WordPress插件版本：v3.0.8 或更高
3. ✅ 清除localStorage Token

```javascript
// 浏览器控制台执行
localStorage.removeItem('wp_jwt_token');
localStorage.removeItem('wp_jwt_user');
```

---

## 📋 5分钟快速测试

### Test 1: 模式选择界面 (1分钟)

**访问**: `http://localhost:3000`

**预期结果**:
```
✅ 显示 AI Logo
✅ 显示 "极致概念 设计高参"
✅ 显示 "请选择使用模式"
✅ 显示两个按钮:
   - "📱 WordPress 嵌入模式（推荐）"（蓝紫渐变）
   - "🖥️ 独立页面模式"（灰色）
✅ 显示提示: "两种模式功能完全相同，可随时切换"
```

**截图对比**:
- ❌ 看到完整应用界面（侧边栏、输入框）
- ❌ 看到自动跳转
- ❌ 看到错误提示

---

### Test 2: iframe嵌入模式 (1分钟)

**访问**: `https://www.ucppt.com/nextjs`

**预期结果**:
```
✅ WordPress页面正常加载
✅ iframe内显示 AI Logo
✅ iframe内显示 "请使用页面右上角的登录按钮登录"
✅ iframe内显示 "登录后即可使用设计高参服务"
✅ iframe内显示 "或在新窗口中打开（独立模式）→"（蓝色文字按钮）
✅ WordPress右上角显示 "登录" 或 "您好，用户名"
```

**点击测试**:
点击 "或在新窗口中打开（独立模式）→"
→ ✅ 新标签页打开 `http://localhost:3000?mode=standalone`（或生产域名）
→ ✅ 显示独立模式登录界面

---

### Test 3: 独立模式 (1分钟)

**访问**: `http://localhost:3000?mode=standalone`

**预期结果**:
```
✅ 显示 AI Logo
✅ 显示 "独立模式 - 请选择登录方式"
✅ 显示 "使用 WordPress 账号登录"（蓝紫渐变大按钮）
✅ 显示 "登录后将自动返回本页面"
✅ 显示 "← 返回 WordPress 嵌入模式"（灰色文字按钮）
```

**点击测试**:
点击 "← 返回 WordPress 嵌入模式"
→ ✅ 跳转到 `https://www.ucppt.com/nextjs`
→ ✅ WordPress页面加载，iframe内显示登录提示

---

### Test 4: 独立模式登录流程 (2分钟)

**访问**: `http://localhost:3000?mode=standalone`

**步骤**:
1. 点击 "使用 WordPress 账号登录"
   → ✅ 跳转到 `https://www.ucppt.com/wp-login.php?redirect_to=...`

2. 输入WordPress用户名密码，登录
   → ✅ 登录成功

3. WordPress自动重定向
   → ✅ 返回 `http://localhost:3000?mode=standalone`

4. 应用界面检查
   → ✅ 显示完整应用界面（侧边栏、输入框）
   → ✅ 左下角显示用户头像和名称
   → ✅ 侧边栏显示历史会话

**控制台日志检查**:
```javascript
[AuthContext] 🔍 正在验证身份...
[AuthContext] ✅ 找到缓存的 Token
[AuthContext] ✅ Token 验证成功
[AuthContext] 👤 设置用户信息
[HomePage] 获取会话列表成功
```

---

## 🔍 详细测试场景

### 场景A: 模式切换 - iframe → 独立

**起点**: `https://www.ucppt.com/nextjs`（未登录，iframe内显示登录提示）

**步骤**:
1. 点击 "或在新窗口中打开（独立模式）→"
2. 检查新标签页URL: `?mode=standalone`
3. 检查新标签页显示: 独立模式登录界面
4. 检查原WordPress页面: 保持不变

**通过标准**: ✅ 新窗口打开，原窗口不变

---

### 场景B: 模式切换 - 独立 → iframe

**起点**: `http://localhost:3000?mode=standalone`（未登录，显示独立登录界面）

**步骤**:
1. 点击 "← 返回 WordPress 嵌入模式"
2. 检查URL: `https://www.ucppt.com/nextjs`
3. 检查显示: WordPress页面 + iframe内登录提示

**通过标准**: ✅ 页面跳转，显示WordPress嵌入模式

---

### 场景C: 模式选择 - 选择iframe

**起点**: `http://localhost:3000`（未登录，显示模式选择）

**步骤**:
1. 点击 "📱 WordPress 嵌入模式（推荐）"
2. 检查URL: `https://www.ucppt.com/nextjs`
3. 检查显示: WordPress页面 + iframe内登录提示

**通过标准**: ✅ 跳转到WordPress嵌入页面

---

### 场景D: 模式选择 - 选择独立

**起点**: `http://localhost:3000`（未登录，显示模式选择）

**步骤**:
1. 点击 "🖥️ 独立页面模式"
2. 检查URL: `http://localhost:3000?mode=standalone`
3. 检查显示: 独立模式登录界面

**通过标准**: ✅ URL添加参数，显示独立登录界面

---

### 场景E: 已登录访问任意模式

**前置条件**: 已在独立模式登录成功

**步骤**:
1. 访问 `http://localhost:3000`
   → ✅ 直接显示完整应用界面（跳过模式选择）

2. 访问 `http://localhost:3000?mode=standalone`
   → ✅ 直接显示完整应用界面（跳过独立登录界面）

3. 访问 `https://www.ucppt.com/nextjs`（WordPress也已登录）
   → ✅ iframe内直接显示完整应用界面（跳过登录提示）

**通过标准**: ✅ 已登录状态下，任意模式都直接显示应用界面

---

## ❌ 常见问题排查

### 问题1: 模式选择界面显示后自动跳转

**症状**: 看到模式选择界面一闪而过，然后跳转到WordPress页面

**原因**: AuthContext中可能还有旧的重定向逻辑

**检查**:
```typescript
// frontend-nextjs/contexts/AuthContext.tsx
// 应该是这样（已修复）:
console.log('[AuthContext] 无有效登录状态，将显示登录提示界面');
setIsLoading(false);
return; // ✅ 不跳转

// 不应该是这样:
window.location.href = wordpressEmbedUrl; // ❌ 会自动跳转
```

**解决**: 确认 `AuthContext.tsx` 版本是最新的，应该在 line 248-252 没有 `window.location.href`

---

### 问题2: iframe模式没有"或在新窗口中打开"按钮

**症状**: iframe内只显示 "请使用页面右上角的登录按钮登录"，没有切换按钮

**原因**: `app/page.tsx` 代码可能不是最新的

**检查**:
```typescript
// frontend-nextjs/app/page.tsx
// 应该有这段代码（lines 443-453）:
<div className="border-t border-[var(--border-color)] pt-4 mt-4">
  <button
    onClick={() => {
      window.open(window.location.origin + '?mode=standalone', '_blank');
    }}
    className="text-sm text-blue-500 hover:text-blue-600 transition-colors"
  >
    或在新窗口中打开（独立模式）→
  </button>
</div>
```

**解决**: 确认 `app/page.tsx` 是最新版本，重启 `npm run dev`

---

### 问题3: 独立模式登录后显示登录提示

**症状**: 在独立模式登录WordPress成功，回调后还是显示登录界面

**原因**: WordPress Cookie没有正确传递，或Token未生成

**检查**:
1. WordPress登录是否真的成功（访问 `https://www.ucppt.com/wp-admin`）
2. localStorage中是否有Token:
   ```javascript
   console.log(localStorage.getItem('wp_jwt_token'));
   console.log(localStorage.getItem('wp_jwt_user'));
   ```
3. 控制台日志是否有Token验证失败信息

**解决**:
- 检查WordPress JWT插件是否启用
- 检查 `.env` 中 `NEXT_PUBLIC_API_URL` 是否正确
- 尝试在WordPress嵌入模式登录（iframe模式），看是否能拿到Token

---

### 问题4: 点击模式切换按钮没反应

**症状**: 点击按钮后页面没有任何变化

**原因**: JavaScript报错或按钮事件未绑定

**检查**:
1. 打开浏览器控制台（F12），查看是否有JavaScript错误
2. 检查按钮是否有 `onClick` 事件:
   ```typescript
   <button onClick={() => { ... }}>
   ```

**解决**: 查看控制台报错信息，根据错误提示修复

---

### 问题5: 独立模式URL没有 ?mode=standalone 参数

**症状**: 访问 `http://localhost:3000?mode=standalone` 显示的是模式选择界面

**原因**: URL参数解析失败

**检查**:
```typescript
// frontend-nextjs/app/page.tsx
// 应该有这段代码:
const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
const standaloneMode = urlParams?.get('mode') === 'standalone';

console.log('standaloneMode:', standaloneMode); // 添加调试日志
```

**解决**:
- 确认浏览器地址栏确实有 `?mode=standalone`
- 确认代码中URL参数解析逻辑正确
- 重启 `npm run dev`，清除浏览器缓存

---

## 📊 测试清单

### 功能测试

- [ ] 直接访问 `localhost:3000` 显示模式选择
- [ ] WordPress嵌入页面显示iframe登录提示
- [ ] 独立模式显示独立登录界面
- [ ] iframe可以打开独立模式（新窗口）
- [ ] 独立模式可以返回iframe模式（页面跳转）
- [ ] 模式选择可以选择iframe模式
- [ ] 模式选择可以选择独立模式
- [ ] 独立模式登录流程正常
- [ ] 已登录状态下任意模式显示应用界面

### UI测试

- [ ] Logo显示正确
- [ ] 标题文字正确
- [ ] 按钮样式正确（主要 vs 次要）
- [ ] 提示文字清晰易懂
- [ ] 响应式设计正常（移动端）
- [ ] 深色模式支持

### 日志测试

- [ ] iframe检测日志正常
- [ ] URL参数检测日志正常
- [ ] 模式切换日志正常
- [ ] 登录流程日志正常

---

## 🎯 成功标准

**全部通过以下测试，即表示双模式架构实现成功**:

1. ✅ 三种UI状态（模式选择、iframe提示、独立登录）显示正确
2. ✅ 模式切换按钮功能正常
3. ✅ 独立模式登录流程完整
4. ✅ 已登录状态下统一体验
5. ✅ 无JavaScript错误
6. ✅ 控制台日志清晰

---

## 🚀 快速命令

### 重启服务

```bash
# 重启Next.js开发服务器
cd frontend-nextjs
npm run dev
```

### 清除缓存

```bash
# 浏览器强制刷新
Ctrl + Shift + R

# 或使用无痕模式
Ctrl + Shift + N
```

### 清除Token

```javascript
// 浏览器控制台执行
localStorage.removeItem('wp_jwt_token');
localStorage.removeItem('wp_jwt_user');
location.reload();
```

### 调试日志

```javascript
// 检查Token
console.log('Token:', localStorage.getItem('wp_jwt_token'));
console.log('User:', localStorage.getItem('wp_jwt_user'));

// 检查iframe
console.log('isInIframe:', window.self !== window.top);

// 检查URL参数
console.log('URL:', window.location.href);
console.log('mode:', new URLSearchParams(window.location.search).get('mode'));
```

---

**测试愉快！** 🎉

如果遇到任何问题，请参考"常见问题排查"章节或查看详细文档 [DUAL_MODE_ARCHITECTURE_IMPLEMENTATION.md](DUAL_MODE_ARCHITECTURE_IMPLEMENTATION.md)。
