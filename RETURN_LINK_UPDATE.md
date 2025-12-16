# 应用链接配置更新说明

**更新时间**: 2025-12-16
**版本**: v3.0.17+
**更新内容**: 修改"返回网站"链接指向

---

## 🔄 更新内容

### 修改的链接

**原链接**: `https://www.ucppt.com`
**新链接**: `https://www.ucppt.com/js`

### 修改位置

1. **登录界面左上角** - [frontend-nextjs/app/page.tsx](frontend-nextjs/app/page.tsx) 第423行
2. **应用主界面左上角** - [frontend-nextjs/app/page.tsx](frontend-nextjs/app/page.tsx) 第888行

### 按钮文案

**原文案**: `ucppt.com`
**新文案**: `返回网站`

---

## 📝 代码变更

### 变更1: 登录界面（未登录状态）

**文件**: `frontend-nextjs/app/page.tsx` (第420-429行)

**修改前**:
```tsx
<a
  href="https://www.ucppt.com"
  target="_blank"
  rel="noopener noreferrer"
  className="..."
  title="访问 ucppt.com 主站"
>
  <span>ucppt.com</span>
```

**修改后**:
```tsx
<a
  href="https://www.ucppt.com/js"
  target="_blank"
  rel="noopener noreferrer"
  className="..."
  title="返回 ucppt.com/js"
>
  <span>返回网站</span>
```

---

### 变更2: 应用主界面（已登录状态，独立模式）

**文件**: `frontend-nextjs/app/page.tsx` (第885-894行)

**修改前**:
```tsx
<a
  href="https://www.ucppt.com"
  target="_blank"
  rel="noopener noreferrer"
  className="..."
  title="访问 ucppt.com 主站"
>
  <span>ucppt.com</span>
```

**修改后**:
```tsx
<a
  href="https://www.ucppt.com/js"
  target="_blank"
  rel="noopener noreferrer"
  className="..."
  title="返回 ucppt.com/js"
>
  <span>返回网站</span>
```

---

## 🛠️ 新增配置文件

### 配置文件: `frontend-nextjs/lib/config.ts`

为了方便以后修改URL，创建了统一的配置文件。

**使用方法**:

```typescript
import { WORDPRESS_CONFIG } from '@/lib/config';

// 使用返回网站链接
<a href={WORDPRESS_CONFIG.RETURN_URL}>返回网站</a>

// 使用登录链接
<a href={WORDPRESS_CONFIG.LOGIN_URL}>登录</a>
```

**配置项说明**:

```typescript
export const WORDPRESS_CONFIG = {
  MAIN_URL: 'https://www.ucppt.com',           // 主站首页
  RETURN_URL: 'https://www.ucppt.com/js',      // 返回网站链接 ← 本次修改
  LOGIN_URL: 'https://www.ucppt.com/login',    // 登录页面
  LOGOUT_URL: '...',                            // 登出页面
  EMBED_URL: '...',                             // iframe入口
  ORDERS_URL: '...',                            // 订单管理
  REST_API_BASE: '...',                         // REST API基础URL
};
```

---

## ✅ 验证步骤

### 步骤1: 重启开发服务器

```bash
cd frontend-nextjs
npm run dev
```

### 步骤2: 测试未登录状态

1. 打开隐身窗口
2. 访问 `http://localhost:3000`
3. 查看左上角按钮
4. 点击"返回网站"按钮
5. 应该跳转到 `https://www.ucppt.com/js` ✅

### 步骤3: 测试已登录状态

1. 在正常窗口登录
2. 访问 `http://localhost:3000`
3. 进入应用主界面后，查看左上角按钮
4. 点击"返回网站"按钮
5. 应该跳转到 `https://www.ucppt.com/js` ✅

---

## 🔧 其他相关链接

### 仍然指向主站的链接（未修改）

以下链接仍然指向 `https://www.ucppt.com`，因为它们有特定用途：

1. **登录跳转** (`page.tsx` 第466行)
   ```typescript
   window.location.href = `https://www.ucppt.com/login?redirect_to=${callbackUrl}`;
   ```
   **用途**: WPCOM登录页面，登录后返回应用

2. **升级会员跳转** (`pricing/page.tsx` 第124行)
   ```typescript
   const wpUrl = 'https://www.ucppt.com/account/orders-list';
   ```
   **用途**: 跳转到WordPress订单管理页面

3. **登出成功页面** (`auth/logout/page.tsx` 第64行)
   ```typescript
   <a href="https://www.ucppt.com">返回设计知外主站</a>
   ```
   **用途**: 登出后返回主站首页

4. **登录重定向** (`auth/login/page.tsx` 第14行)
   ```typescript
   const wordpressEmbedUrl = 'https://www.ucppt.com/nextjs';
   ```
   **用途**: 跳转到WordPress嵌入页面（iframe入口）

---

## 📋 未来修改指南

### 如果需要再次修改"返回网站"链接

**方法1: 直接修改配置文件（推荐）**

编辑 `frontend-nextjs/lib/config.ts` 第10行:
```typescript
RETURN_URL: 'https://www.ucppt.com/your-new-path',
```

然后更新 `page.tsx` 使用配置文件:
```typescript
import { WORDPRESS_CONFIG } from '@/lib/config';

<a href={WORDPRESS_CONFIG.RETURN_URL}>返回网站</a>
```

**方法2: 直接修改源文件**

编辑 `frontend-nextjs/app/page.tsx`:
- 第423行: 修改 `href` 属性
- 第888行: 修改 `href` 属性

---

## 🎯 影响范围

### 受影响的页面

1. ✅ 登录界面（未登录状态）
2. ✅ 应用主界面（已登录状态，独立模式）

### 不受影响的功能

1. ✅ WordPress SSO登录流程
2. ✅ Token验证和刷新
3. ✅ 用户信息显示
4. ✅ 会员升级跳转
5. ✅ 登出功能

---

## 🚀 部署清单

- [x] 修改 `frontend-nextjs/app/page.tsx` 第423行
- [x] 修改 `frontend-nextjs/app/page.tsx` 第888行
- [x] 创建配置文件 `frontend-nextjs/lib/config.ts`
- [ ] 重启Next.js开发服务器
- [ ] 测试未登录状态的"返回网站"按钮
- [ ] 测试已登录状态的"返回网站"按钮
- [ ] 生产环境部署（`npm run build`）

---

**创建时间**: 2025-12-16
**更新人**: Claude Sonnet 4.5
**状态**: ✅ 开发完成，待测试
