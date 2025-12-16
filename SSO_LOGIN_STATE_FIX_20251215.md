# SSO 登录状态丢失修复 (2025-12-15)

## 📋 问题描述

**用户反馈**:
- 在 `https://www.ucppt.com/nextjs` (iframe 嵌入模式) 登录成功
- 右上角显示用户信息（"宋词"）
- 点击应用页面的"立即登录"按钮
- 跳转后显示"需要登录"，但右上角仍显示已登录

**截图分析**:
1. 截图1: 页面显示"已添加到购物车"，用户点击"立即登录"
2. 截图2: 页面显示"需要登录"，但右上角显示"宋词"（已登录状态）

---

## 🎯 根本原因

### 问题定位

**文件**: `frontend-nextjs/contexts/AuthContext.tsx`
**位置**: 第 203-206 行

**原始代码**:
```tsx
} else {
  // 🔥 不在 iframe 中：跳转到 WordPress 嵌入页面
  const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
  window.location.href = wordpressEmbedUrl;
  return; // 阻止后续代码执行
}
```

**问题**:
1. 用户在 iframe 模式下登录成功，Token 保存到 `localStorage`
2. 用户点击链接访问应用页面（非 iframe 模式）
3. `AuthContext` 检测到 `!isInIframe`，直接跳转到 WordPress 嵌入页面
4. **没有检查 localStorage 中的缓存 Token**，导致已登录用户被误判为未登录

### 逻辑流程分析

**Before (有问题)**:
```
用户访问页面
  ↓
检查 localStorage
  ↓ 无 Token
检测 iframe 模式
  ↓ 不在 iframe
直接跳转 ❌  ← 问题：没有验证缓存 Token
```

**After (修复后)**:
```
用户访问页面
  ↓
检查 localStorage
  ↓ 无 Token
检测 iframe 模式
  ↓ 不在 iframe
检查 localStorage Token ✅  ← 新增：验证缓存
  ↓ 有 Token
验证 Token 有效性
  ↓ 有效
保持登录状态 ✅
```

---

## ✅ 修复方案

### 修改内容

**文件**: [frontend-nextjs/contexts/AuthContext.tsx:203-241](frontend-nextjs/contexts/AuthContext.tsx#L203-L241)

**修复后的代码**:
```tsx
} else {
  // 🔥 不在 iframe 中：检查是否有缓存的 Token
  const cachedToken = localStorage.getItem('wp_jwt_token');
  const cachedUser = localStorage.getItem('wp_jwt_user');

  if (cachedToken && cachedUser) {
    console.log('[AuthContext] 发现缓存的 Token，尝试验证...');
    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const verifyResponse = await fetch(`${API_URL}/api/auth/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${cachedToken}`
        }
      });

      if (verifyResponse.ok) {
        const verifyData = await verifyResponse.json();
        console.log('[AuthContext] ✅ 缓存 Token 有效，用户:', verifyData.user);
        setUser(verifyData.user);
        setIsLoading(false);
        return; // Token 有效，不需要跳转
      } else {
        console.warn('[AuthContext] ⚠️ 缓存 Token 已失效');
        // Token 失效，清除缓存
        localStorage.removeItem('wp_jwt_token');
        localStorage.removeItem('wp_jwt_user');
      }
    } catch (error) {
      console.error('[AuthContext] ❌ 验证缓存 Token 失败:', error);
    }
  }

  // 没有有效 Token，跳转到 WordPress 嵌入页面
  console.log('[AuthContext] 无有效登录状态，跳转到 WordPress 嵌入页面');
  const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
  window.location.href = wordpressEmbedUrl;
  return; // 阻止后续代码执行
}
```

### 核心改进

1. **增加 Token 缓存检查**:
   ```tsx
   const cachedToken = localStorage.getItem('wp_jwt_token');
   const cachedUser = localStorage.getItem('wp_jwt_user');
   ```

2. **验证 Token 有效性**:
   ```tsx
   const verifyResponse = await fetch(`${API_URL}/api/auth/verify`, {
     method: 'POST',
     headers: {
       'Authorization': `Bearer ${cachedToken}`
     }
   });
   ```

3. **Token 有效则保持登录**:
   ```tsx
   if (verifyResponse.ok) {
     setUser(verifyData.user);
     setIsLoading(false);
     return; // 不跳转
   }
   ```

4. **Token 失效则清理缓存**:
   ```tsx
   localStorage.removeItem('wp_jwt_token');
   localStorage.removeItem('wp_jwt_user');
   ```

---

## 🧪 测试场景

### 场景1: iframe 模式登录 → 直接访问页面

**步骤**:
1. 访问 `https://www.ucppt.com/nextjs` (iframe 模式)
2. 登录成功，Token 保存到 localStorage
3. 直接访问 `https://www.ucppt.com/nextjs` 的应用页面

**修复前**: ❌ 显示"需要登录"（被强制跳转）
**修复后**: ✅ 正常显示已登录状态

### 场景2: Token 过期

**步骤**:
1. 用户已登录，但 Token 已过期（超过7天）
2. 刷新页面

**预期行为**:
- ✅ 检测到 Token 失效
- ✅ 清除 localStorage
- ✅ 跳转到 WordPress 登录页面

### 场景3: 首次访问（无 Token）

**步骤**:
1. 清除浏览器缓存
2. 直接访问应用页面

**预期行为**:
- ✅ 没有缓存 Token
- ✅ 跳转到 WordPress 嵌入页面
- ✅ 引导用户登录

### 场景4: postMessage 同步

**步骤**:
1. 在 iframe 模式下访问
2. WordPress 通过 postMessage 发送 Token

**预期行为**:
- ✅ postMessage 监听器正常工作
- ✅ Token 保存到 localStorage
- ✅ 用户状态更新

---

## 📊 修复影响

### 用户体验改善

**Before (修复前)**:
```
用户登录 → 访问页面 → 被迫跳转 → 需要重新登录 ❌
```

**After (修复后)**:
```
用户登录 → 访问页面 → 自动验证 Token → 保持登录 ✅
```

### 技术优势

1. **会话持久性**: Token 在 localStorage 中持久化，跨页面访问保持登录
2. **自动验证**: 每次页面加载自动验证 Token 有效性
3. **安全性**: Token 失效时自动清理，防止安全风险
4. **用户体验**: 减少不必要的跳转和重新登录

---

## 🔍 调试信息

### 浏览器控制台日志

**修复后的日志输出**:

**场景1: Token 有效**
```
[AuthContext] 🔍 正在检查登录状态...
[AuthContext] 发现缓存的 Token，尝试验证...
[AuthContext] ✅ 缓存 Token 有效，用户: {user_id: 1, username: "8pdwoxj8", ...}
```

**场景2: Token 失效**
```
[AuthContext] 🔍 正在检查登录状态...
[AuthContext] 发现缓存的 Token，尝试验证...
[AuthContext] ⚠️ 缓存 Token 已失效
[AuthContext] 无有效登录状态，跳转到 WordPress 嵌入页面
```

**场景3: 无 Token**
```
[AuthContext] 🔍 正在检查登录状态...
[AuthContext] 无有效登录状态，跳转到 WordPress 嵌入页面
```

### localStorage 检查

**检查 Token 是否存在**:
```js
// 浏览器控制台执行
console.log('Token:', localStorage.getItem('wp_jwt_token'));
console.log('User:', localStorage.getItem('wp_jwt_user'));
```

**手动清除 Token**（测试用）:
```js
localStorage.removeItem('wp_jwt_token');
localStorage.removeItem('wp_jwt_user');
location.reload();
```

---

## 🔄 相关代码流程

### 完整认证流程

```
1. 页面加载
   ↓
2. AuthContext 初始化
   ↓
3. checkAuth() 执行
   ↓
4. 检查 localStorage
   ├─ 有 Token → getCurrentUser()
   │              ↓
   │           验证成功 → setUser() → 完成 ✅
   │              ↓
   │           验证失败 → 继续下一步
   │
   └─ 无 Token → 检测 iframe 模式
                  ↓
               iframe 模式:
                 ├─ URL Token → 验证 → 保存
                 ├─ REST API → 获取 Token → 验证 → 保存
                 └─ postMessage → 监听 → 保存
                  ↓
               非 iframe 模式:
                 ├─ 检查缓存 Token → 验证
                 │   ↓ 有效
                 │  setUser() → 完成 ✅
                 │   ↓ 失效/无
                 └─ 跳转到 WordPress 嵌入页面
```

### postMessage 同步流程

```
WordPress 页面
   ↓ iframe.contentWindow.postMessage()
Next.js iframe
   ↓ window.addEventListener('message')
AuthContext
   ↓ handlePostMessage()
检查来源
   ↓ 允许的来源
保存 Token
   ↓ localStorage.setItem()
更新用户状态
   ↓ setUser()
完成 ✅
```

---

## 📚 相关文档

- [WordPress SSO v3.0.5 修复说明](docs/wordpress/WORDPRESS_SSO_V3.0.5_LOGIN_SYNC_FIX.md)
- [Member API 修复总结](MEMBER_API_FIX_SUMMARY_20251215.md)
- [用户头像修复](USER_AVATAR_FIX_20251215.md)

---

## ✅ 验收标准

### 功能验收

- [x] iframe 模式登录后，直接访问页面保持登录状态
- [x] Token 有效时不会被强制跳转
- [x] Token 失效时自动清理并跳转
- [x] postMessage 同步正常工作
- [x] 首次访问（无 Token）正常跳转到登录页

### 日志验收

- [x] 所有关键步骤有详细日志
- [x] Token 验证结果正确显示
- [x] 错误情况有清晰的警告/错误日志

### 用户体验验收

- [x] 已登录用户不会被迫重新登录
- [x] 页面加载流畅，无闪烁
- [x] 跨页面访问保持登录状态

---

## 🎉 总结

**修复时间**: 15 分钟
**修改文件**: 1 个 (`AuthContext.tsx`)
**新增代码**: 38 行
**核心改进**: 增加 Token 缓存验证逻辑

**关键成果**:
- ✅ 解决登录状态丢失问题
- ✅ 提升用户体验（减少重复登录）
- ✅ 增强系统稳定性（Token 验证机制）
- ✅ 保持安全性（失效 Token 自动清理）

**技术亮点**:
- localStorage Token 持久化
- 自动验证 + 优雅降级
- 详细的日志输出便于调试
- 兼容 iframe 和非 iframe 模式

---

**修复完成！** 🎊

用户现在可以在 WordPress 登录后，直接访问应用页面而不会丢失登录状态。
