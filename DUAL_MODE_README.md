# WordPress SSO 双模式架构实现 (v3.0.9)

## 📋 项目概述

实现了Next.js应用与WordPress单点登录(SSO)集成的**双模式架构**，允许用户在**iframe嵌入模式**和**独立页面模式**之间自由选择和切换。

---

## 🎯 核心功能

### 1. 三种访问模式

| 模式 | 访问方式 | 适用场景 |
|-----|---------|---------|
| **模式选择** | `http://localhost:3000` | 首次访问，引导用户选择喜欢的模式 |
| **iframe嵌入模式** | `https://www.ucppt.com/nextjs` | 在WordPress页面中使用，统一登录状态 |
| **独立页面模式** | `http://localhost:3000?mode=standalone` | 独立访问应用，不依赖WordPress页面 |

### 2. 模式切换

- ✅ iframe模式 → 独立模式（新窗口打开）
- ✅ 独立模式 → iframe模式（页面跳转）
- ✅ 模式选择 → 任意模式
- ✅ 已登录状态下统一体验

### 3. 认证安全

- ✅ 未登录时隐藏应用界面，只显示登录提示
- ✅ JWT Token认证
- ✅ 自动Token同步（WordPress ↔ Next.js）
- ✅ 退出登录状态同步
- ✅ 防止会话泄露

---

## 🚀 快速开始

### 前置要求

- Node.js 18+
- WordPress 5.8+
- Redis（可选，用于会话管理）

### 1. 启动前端开发服务器

```bash
cd frontend-nextjs
npm install
npm run dev
```

访问: `http://localhost:3000`

### 2. 安装WordPress插件

```bash
# 上传插件
WordPress后台 → 插件 → 安装插件 → 上传插件
选择: nextjs-sso-integration-v3.0.8.zip
启用插件
```

### 3. 配置WordPress页面

```bash
# 创建WordPress页面
1. 新建页面，标题: "Next.js App"
2. 内容添加短代码: [nextjs-sso-app-v3]
3. 发布页面
4. 访问页面URL（例如: https://www.ucppt.com/nextjs）
```

### 4. 测试验证

按照 [DUAL_MODE_QUICK_TEST_GUIDE.md](DUAL_MODE_QUICK_TEST_GUIDE.md) 执行测试。

---

## 📖 文档索引

### 技术文档

1. **[DUAL_MODE_ARCHITECTURE_IMPLEMENTATION.md](DUAL_MODE_ARCHITECTURE_IMPLEMENTATION.md)**
   - 完整的架构设计和实现细节
   - 代码解析和工作原理
   - 技术亮点和设计模式

2. **[DUAL_MODE_QUICK_TEST_GUIDE.md](DUAL_MODE_QUICK_TEST_GUIDE.md)**
   - 5分钟快速测试指南
   - 详细测试场景（A-E）
   - 常见问题排查

3. **[DUAL_MODE_DEPLOYMENT_GUIDE.md](DUAL_MODE_DEPLOYMENT_GUIDE.md)**
   - 完整部署步骤
   - 生产环境配置
   - 部署后检查清单

### 历史修复文档

4. **[UNAUTHENTICATED_UI_HIDE_FIX_20251215.md](UNAUTHENTICATED_UI_HIDE_FIX_20251215.md)**
   - 未登录用户隐藏应用界面
   - 单一登录入口原则
   - 移除重复登录逻辑

5. **[SSO_LOGIN_SYNC_FIX_20251215.md](SSO_LOGIN_SYNC_FIX_20251215.md)**
   - WordPress登录后自动同步到Next.js
   - 5秒状态检测 + 自动页面刷新
   - postMessage通信机制

6. **[SECURITY_FIX_SESSION_LEAK_20251215.md](SECURITY_FIX_SESSION_LEAK_20251215.md)**
   - 修复未登录用户可访问会话列表的安全漏洞
   - 后端API强制JWT认证
   - 前端UI安全防护

7. **[USER_AVATAR_FIX_20251215.md](USER_AVATAR_FIX_20251215.md)**
   - 用户头像显示优化
   - 首字母头像生成
   - 邮箱智能截断

---

## 🏗️ 架构图

### 三种访问模式

```
┌─────────────────────────────────────────────────────────────┐
│                    用户访问应用                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  检测访问上下文        │
              │  - iframe检测         │
              │  - URL参数检测        │
              └──────────┬─────────────┘
                         │
            ┌────────────┼────────────┐
            │            │            │
            ▼            ▼            ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ iframe   │  │ 独立模式  │  │ 模式选择  │
    │ 嵌入模式  │  │          │  │          │
    └──────────┘  └──────────┘  └──────────┘
         │             │             │
         │             │             │
         └─────────────┴─────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  用户登录认证   │
              └────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  完整应用界面   │
              └────────────────┘
```

### 认证流程

```
未登录访问
  ↓
显示登录提示（三种模式不同提示）
  ↓
用户登录（WordPress或独立模式）
  ↓
Token生成 + 保存到localStorage
  ↓
AuthContext验证Token
  ↓
setUser(userData)
  ↓
页面重新渲染为完整应用界面
```

---

## 🔧 关键文件

### 前端代码

```
frontend-nextjs/
├── app/
│   └── page.tsx                    # 主页面（双模式逻辑）lines 412-528
├── contexts/
│   └── AuthContext.tsx             # 认证上下文，Token同步
├── components/layout/
│   ├── UserPanel.tsx               # 用户面板
│   └── MembershipCard.tsx          # 会员信息卡片
└── lib/
    ├── api.ts                      # API客户端（JWT拦截器）
    └── wp-auth.ts                  # WordPress认证工具
```

### WordPress插件

```
nextjs-sso-integration-v3.php       # WordPress插件（v3.0.8）
└── 功能:
    ├── JWT Token生成
    ├── REST API端点（/wp-json/nextjs-sso/v1/get-token）
    ├── 登录状态检测（5秒轮询）
    ├── postMessage通信
    └── WordPress短代码 [nextjs-sso-app-v3]
```

---

## 🧪 测试场景

### 场景1: 模式选择 → iframe模式

1. 访问 `http://localhost:3000`
2. 点击 "📱 WordPress 嵌入模式（推荐）"
3. ✅ 跳转到 `https://www.ucppt.com/nextjs`
4. ✅ iframe内显示登录提示

### 场景2: 模式选择 → 独立模式

1. 访问 `http://localhost:3000`
2. 点击 "🖥️ 独立页面模式"
3. ✅ URL变为 `http://localhost:3000?mode=standalone`
4. ✅ 显示独立登录界面

### 场景3: iframe → 独立（模式切换）

1. 访问 `https://www.ucppt.com/nextjs`（未登录）
2. iframe内点击 "或在新窗口中打开（独立模式）→"
3. ✅ 新标签页打开独立模式
4. ✅ 原WordPress页面保持不变

### 场景4: 独立模式登录流程

1. 访问 `http://localhost:3000?mode=standalone`
2. 点击 "使用 WordPress 账号登录"
3. ✅ 跳转到WordPress登录页
4. 输入用户名密码，登录
5. ✅ 自动返回 `http://localhost:3000?mode=standalone`
6. ✅ 显示完整应用界面

### 场景5: 已登录统一体验

前置条件: 已在任意模式登录成功

1. 访问 `http://localhost:3000` → ✅ 直接显示应用界面
2. 访问 `http://localhost:3000?mode=standalone` → ✅ 直接显示应用界面
3. 访问 `https://www.ucppt.com/nextjs` → ✅ iframe内直接显示应用界面

---

## 📊 版本历史

### v3.0.9 (2025-12-15) - 双模式架构

**新增功能**:
- ✅ 支持iframe嵌入模式
- ✅ 支持独立页面模式
- ✅ 支持模式选择界面
- ✅ 模式间可互相切换

**优化改进**:
- ✅ 三态UI设计（模式选择、iframe提示、独立登录）
- ✅ 上下文自动检测（iframe + URL参数）
- ✅ 统一的认证体验
- ✅ 清晰的用户引导

### v3.0.8 (2025-12-15) - 登录同步优化 + 应用界面隐藏

**修复内容**:
- ✅ WordPress登录后自动同步到Next.js（5秒检测 + 页面刷新）
- ✅ 未登录时Next.js隐藏应用界面，只显示登录提示
- ✅ 统一使用WordPress右上角登录/退出按钮（单一入口原则）
- ✅ 移除应用内重复的登录按钮

### v3.0.7 (2025-12-15) - 退出登录同步

**修复内容**:
- ✅ WordPress退出登录时自动通知Next.js清除Token
- ✅ 双重检测机制（退出链接点击 + 状态轮询）
- ✅ postMessage安全通信

### v3.0.6 (2025-12-15) - 始终渲染iframe

**修复内容**:
- ✅ 始终渲染iframe（不再检测WordPress登录状态）
- ✅ 让Next.js应用自己处理登录逻辑（支持Token缓存）
- ✅ 解决WordPress未登录时无法使用Token缓存的问题

### v3.0.5 (2025-12-15) - 会话安全修复

**修复内容**:
- ✅ 修复未登录用户可访问会话列表的安全漏洞
- ✅ 后端API强制JWT认证
- ✅ 前端UI安全防护

---

## 🔒 安全特性

1. **JWT Token认证**
   - 所有API请求自动携带Bearer Token
   - Token存储在localStorage（客户端安全）
   - Token有过期时间（TTL: 72小时）

2. **后端API保护**
   ```python
   @router.get("/api/sessions")
   async def get_sessions(user: User = Depends(get_current_user)):
       # 强制JWT认证，未登录返回401
   ```

3. **前端UI防护**
   ```typescript
   // 未登录时隐藏应用界面
   if (!authLoading && !user) {
     return <LoginPrompt />;
   }
   ```

4. **跨域安全**
   - postMessage白名单验证
   - CORS正确配置
   - HTTPS强制（生产环境）

---

## 💡 技术亮点

### 1. 三态UI设计

```typescript
if (!authLoading && !user) {
  // 未登录状态
  if (isInIframe) return <IframeLoginPrompt />;
  else if (standaloneMode) return <StandaloneLoginPrompt />;
  else return <ModeSelection />;
}
// 已登录状态
return <FullAppUI />;
```

### 2. 上下文检测

```typescript
// iframe检测
const isInIframe = window.self !== window.top;

// URL参数检测
const urlParams = new URLSearchParams(window.location.search);
const standaloneMode = urlParams?.get('mode') === 'standalone';
```

### 3. 状态驱动UI

```
Token变化 → AuthContext.setUser() → useAuth().user → 页面重新渲染
```

### 4. postMessage通信

```javascript
// WordPress → Next.js
iframe.contentWindow.postMessage({
  type: 'sso_login',
  token: 'xxx',
  user: {...}
}, appBaseUrl);

// Next.js接收
window.addEventListener('message', (event) => {
  if (event.data.type === 'sso_login') {
    localStorage.setItem('wp_jwt_token', event.data.token);
    setUser(event.data.user);
  }
});
```

---

## 🐛 常见问题

### Q1: 为什么有三种模式？

**A**:
- **模式选择**: 首次访问时引导用户选择喜欢的方式
- **iframe嵌入模式**: 在WordPress页面中使用，统一登录状态（推荐）
- **独立页面模式**: 独立访问应用，不依赖WordPress页面（备用方案）

### Q2: iframe模式登录不同步怎么办？

**A**: 检查以下几点：
1. WordPress插件版本是否为 v3.0.8+
2. 清除WordPress缓存（WP Super Cache）
3. 清除浏览器缓存（Ctrl + Shift + R）
4. 检查浏览器控制台是否有JavaScript错误
5. 使用独立模式作为备用方案

### Q3: 如何在两种模式之间切换？

**A**:
- **iframe → 独立**: 点击 "或在新窗口中打开（独立模式）→"
- **独立 → iframe**: 点击 "← 返回 WordPress 嵌入模式"
- **任意模式 → 模式选择**: 访问 `http://localhost:3000`

### Q4: 独立模式如何登录？

**A**: 点击 "使用 WordPress 账号登录"，会跳转到WordPress登录页面，登录成功后自动返回应用。

### Q5: 已登录状态下访问模式选择界面会怎样？

**A**: 直接显示完整应用界面，不会显示模式选择界面（认证优先于模式检测）。

---

## 📞 支持和反馈

如有问题或建议，请：
1. 查看相关文档（见"文档索引"章节）
2. 检查"常见问题"章节
3. 查看浏览器控制台日志
4. 联系技术支持

---

## 📜 许可证

Copyright © 2025 UCPPT Team. All rights reserved.

---

**双模式架构实现完成！** 🎉

现在用户可以自由选择和切换访问模式，享受灵活的应用体验！
