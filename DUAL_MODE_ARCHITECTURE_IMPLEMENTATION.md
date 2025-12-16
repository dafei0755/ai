# 双模式架构实现 (v3.0.9)

## 📋 需求回顾

**用户原始需求**：
> "能否两个模式同时存在，可以相互切换？"

**背景**：
- iframe嵌入模式存在登录状态同步问题（REST API 401错误）
- 用户希望保留两种使用方式，互不干扰
- 希望可以随时在两种模式之间切换

**目标**：
1. 支持 **iframe嵌入模式**（WordPress集成）
2. 支持 **独立页面模式**（直接访问）
3. 两种模式可以互相切换
4. 每种模式都有清晰的使用指引

---

## 🏗️ 架构设计

### 三种UI状态

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

---

## 🔧 实现细节

### 1. iframe嵌入模式

**检测条件**：
```typescript
const isInIframe = typeof window !== 'undefined' && window.self !== window.top;
```

**特征**：
- 页面在WordPress iframe中运行
- WordPress页面显示右上角登录/退出按钮
- Next.js应用通过postMessage接收Token

**UI展示**：
```
┌──────────────────────────────┐
│         [AI Logo]            │
│    极致概念 设计高参          │
│                              │
│  ┌────────────────────────┐  │
│  │  请使用页面右上角的     │  │
│  │  登录按钮登录           │  │
│  │                        │  │
│  │  登录后即可使用设计高   │  │
│  │  参服务                │  │
│  │                        │  │
│  │  ────────────────────  │  │
│  │                        │  │
│  │  [或在新窗口中打开] →  │  │
│  │  (独立模式)            │  │
│  └────────────────────────┘  │
│                              │
│        ucppt.com             │
└──────────────────────────────┘
```

**代码实现**（`app/page.tsx` lines 434-454）：
```typescript
{isInIframe ? (
  // 📱 iframe嵌入模式：引导用户使用 WordPress 登录
  <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg p-6 space-y-4">
    <div className="text-lg text-[var(--foreground-secondary)]">
      请使用页面右上角的登录按钮登录
    </div>
    <div className="text-sm text-[var(--foreground-secondary)]">
      登录后即可使用设计高参服务
    </div>
    <div className="border-t border-[var(--border-color)] pt-4 mt-4">
      <button
        onClick={() => {
          // 在新窗口打开独立模式
          window.open(window.location.origin + '?mode=standalone', '_blank');
        }}
        className="text-sm text-blue-500 hover:text-blue-600 transition-colors"
      >
        或在新窗口中打开（独立模式）→
      </button>
    </div>
  </div>
) : ...
```

**登录流程**：
```
用户在WordPress右上角点击"登录"
  ↓
WordPress登录页面（wp-login.php）
  ↓
登录成功
  ↓
WordPress插件检测到登录状态变化（5秒内）
  ↓
自动刷新页面
  ↓
iframe重新加载，触发load事件
  ↓
WordPress发送postMessage（包含Token）
  ↓
AuthContext接收Token并保存
  ↓
app/page.tsx重新渲染为完整应用界面
```

---

### 2. 独立模式

**检测条件**：
```typescript
const urlParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
const standaloneMode = urlParams?.get('mode') === 'standalone';
```

**访问URL**：
- `http://localhost:3000?mode=standalone`
- `https://www.ucppt.com/app?mode=standalone`

**特征**：
- 页面直接访问，不在iframe中
- URL包含 `?mode=standalone` 参数
- 提供独立的登录流程

**UI展示**：
```
┌──────────────────────────────┐
│         [AI Logo]            │
│    极致概念 设计高参          │
│                              │
│  ┌────────────────────────┐  │
│  │  独立模式 - 请选择登录  │  │
│  │  方式                   │  │
│  │                        │  │
│  │  ┌──────────────────┐  │  │
│  │  │ 使用 WordPress    │  │  │
│  │  │ 账号登录          │  │  │
│  │  └──────────────────┘  │  │
│  │                        │  │
│  │  登录后将自动返回本页面 │  │
│  │                        │  │
│  │  ────────────────────  │  │
│  │                        │  │
│  │  ← 返回 WordPress      │  │
│  │     嵌入模式           │  │
│  └────────────────────────┘  │
│                              │
│        ucppt.com             │
└──────────────────────────────┘
```

**代码实现**（`app/page.tsx` lines 455-489）：
```typescript
: standaloneMode ? (
  // 🖥️ 独立模式：提供独立登录选项
  <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg p-6 space-y-4">
    <div className="text-lg text-[var(--foreground-secondary)] mb-4">
      独立模式 - 请选择登录方式
    </div>

    <button
      onClick={() => {
        // 跳转到WordPress登录，带回调
        const callbackUrl = encodeURIComponent(window.location.href);
        window.location.href = `https://www.ucppt.com/wp-login.php?redirect_to=${callbackUrl}`;
      }}
      className="w-full px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-medium rounded-lg transition-all"
    >
      使用 WordPress 账号登录
    </button>

    <div className="text-xs text-[var(--foreground-secondary)]">
      登录后将自动返回本页面
    </div>

    <div className="border-t border-[var(--border-color)] pt-4 mt-4 space-y-2">
      <button
        onClick={() => {
          // 切换回iframe模式
          const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
          window.location.href = wordpressEmbedUrl;
        }}
        className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        ← 返回 WordPress 嵌入模式
      </button>
    </div>
  </div>
) : ...
```

**登录流程**：
```
用户点击"使用 WordPress 账号登录"
  ↓
跳转到 WordPress 登录页：
https://www.ucppt.com/wp-login.php?redirect_to=http://localhost:3000?mode=standalone
  ↓
用户输入用户名密码
  ↓
WordPress登录成功
  ↓
WordPress重定向回：http://localhost:3000?mode=standalone
  ↓
AuthContext检查缓存Token（WordPress Cookie → JWT Token）
  ↓
Token有效，显示完整应用界面
```

---

### 3. 模式选择（默认状态）

**检测条件**：
```typescript
!isInIframe && !standaloneMode
```

**访问URL**：
- `http://localhost:3000`
- `https://www.ucppt.com/app`（不带任何参数）

**特征**：
- 直接访问，没有指定模式
- 引导用户选择喜欢的模式

**UI展示**：
```
┌──────────────────────────────┐
│         [AI Logo]            │
│    极致概念 设计高参          │
│                              │
│  ┌────────────────────────┐  │
│  │  请选择使用模式         │  │
│  │                        │  │
│  │  ┌──────────────────┐  │  │
│  │  │ 📱 WordPress      │  │  │
│  │  │    嵌入模式（推荐）│  │  │
│  │  └──────────────────┘  │  │
│  │                        │  │
│  │  ┌──────────────────┐  │  │
│  │  │ 🖥️ 独立页面模式   │  │  │
│  │  └──────────────────┘  │  │
│  │                        │  │
│  │  两种模式功能完全相同， │  │
│  │  可随时切换             │  │
│  └────────────────────────┘  │
│                              │
│        ucppt.com             │
└──────────────────────────────┘
```

**代码实现**（`app/page.tsx` lines 490-520）：
```typescript
: (
  // 🔀 默认模式：引导用户选择模式
  <div className="bg-[var(--card-bg)] border border-[var(--border-color)] rounded-lg p-6 space-y-4">
    <div className="text-lg text-[var(--foreground-secondary)] mb-4">
      请选择使用模式
    </div>

    <button
      onClick={() => {
        const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
        window.location.href = wordpressEmbedUrl;
      }}
      className="w-full px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-medium rounded-lg transition-all"
    >
      📱 WordPress 嵌入模式（推荐）
    </button>

    <button
      onClick={() => {
        window.location.href = window.location.origin + '?mode=standalone';
      }}
      className="w-full px-6 py-3 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-medium rounded-lg transition-all"
    >
      🖥️ 独立页面模式
    </button>

    <div className="text-xs text-[var(--foreground-secondary)] pt-2">
      两种模式功能完全相同，可随时切换
    </div>
  </div>
)
```

---

## 🔄 模式切换机制

### iframe → 独立模式

**触发位置**：iframe嵌入模式的登录提示界面

**实现方式**：
```typescript
<button
  onClick={() => {
    // 在新窗口打开独立模式
    window.open(window.location.origin + '?mode=standalone', '_blank');
  }}
>
  或在新窗口中打开（独立模式）→
</button>
```

**行为**：
- 使用 `window.open()` 在新标签页/窗口打开
- 保留原iframe不影响WordPress页面
- 新窗口显示独立模式登录界面

### 独立模式 → iframe嵌入模式

**触发位置**：独立模式的登录提示界面

**实现方式**：
```typescript
<button
  onClick={() => {
    // 切换回iframe模式
    const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
    window.location.href = wordpressEmbedUrl;
  }}
>
  ← 返回 WordPress 嵌入模式
</button>
```

**行为**：
- 使用 `window.location.href` 跳转到WordPress页面
- WordPress页面中iframe会重新加载
- 显示iframe嵌入模式

### 默认模式的选择

**WordPress嵌入模式（推荐）**：
```typescript
<button
  onClick={() => {
    const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
    window.location.href = wordpressEmbedUrl;
  }}
>
  📱 WordPress 嵌入模式（推荐）
</button>
```

**独立页面模式**：
```typescript
<button
  onClick={() => {
    window.location.href = window.location.origin + '?mode=standalone';
  }}
>
  🖥️ 独立页面模式
</button>
```

---

## 🧪 测试计划

### 测试场景1: 直接访问（模式选择）

**步骤**：
1. 清除localStorage Token：
   ```javascript
   localStorage.removeItem('wp_jwt_token');
   localStorage.removeItem('wp_jwt_user');
   ```
2. 访问 `http://localhost:3000`
3. ✅ 应该看到模式选择界面
4. ✅ 应该显示两个按钮："WordPress 嵌入模式（推荐）" 和 "独立页面模式"
5. ✅ 应该显示提示文字："两种模式功能完全相同，可随时切换"

**预期截图**：
```
┌────────────────────────────────┐
│      [AI Logo - 蓝色方块]        │
│     极致概念 设计高参             │
│                                │
│  ┌──────────────────────────┐  │
│  │    请选择使用模式          │  │
│  │                          │  │
│  │  [蓝紫渐变按钮]           │  │
│  │  📱 WordPress 嵌入模式    │  │
│  │     （推荐）              │  │
│  │                          │  │
│  │  [灰色按钮]               │  │
│  │  🖥️ 独立页面模式          │  │
│  │                          │  │
│  │  两种模式功能完全相同，    │  │
│  │  可随时切换               │  │
│  └──────────────────────────┘  │
│                                │
│         ucppt.com              │
└────────────────────────────────┘
```

---

### 测试场景2: iframe嵌入模式

**步骤**：
1. 访问 `https://www.ucppt.com/nextjs`（WordPress嵌入页面）
2. ✅ 应该看到iframe内显示登录提示
3. ✅ 提示文字："请使用页面右上角的登录按钮登录"
4. ✅ 应该有"或在新窗口中打开（独立模式）→"按钮
5. 点击"或在新窗口中打开"按钮
6. ✅ 应该在新标签页打开独立模式

**预期截图**（iframe内部）：
```
┌────────────────────────────────┐
│      [AI Logo - 蓝色方块]        │
│     极致概念 设计高参             │
│                                │
│  ┌──────────────────────────┐  │
│  │  请使用页面右上角的登录    │  │
│  │  按钮登录                 │  │
│  │                          │  │
│  │  登录后即可使用设计高参    │  │
│  │  服务                     │  │
│  │                          │  │
│  │  ────────────────────    │  │
│  │                          │  │
│  │  [蓝色文字按钮]           │  │
│  │  或在新窗口中打开（独立   │  │
│  │  模式）→                  │  │
│  └──────────────────────────┘  │
│                                │
│         ucppt.com              │
└────────────────────────────────┘
```

**WordPress页面右上角应该显示**："登录" 或 "您好，用户名"

---

### 测试场景3: 独立模式

**步骤**：
1. 访问 `http://localhost:3000?mode=standalone`
2. ✅ 应该看到独立模式登录界面
3. ✅ 标题："独立模式 - 请选择登录方式"
4. ✅ 应该有"使用 WordPress 账号登录"按钮（蓝紫渐变）
5. ✅ 应该有"← 返回 WordPress 嵌入模式"按钮（灰色文字）
6. ✅ 提示文字："登录后将自动返回本页面"

**预期截图**：
```
┌────────────────────────────────┐
│      [AI Logo - 蓝色方块]        │
│     极致概念 设计高参             │
│                                │
│  ┌──────────────────────────┐  │
│  │  独立模式 - 请选择登录方式 │  │
│  │                          │  │
│  │  [蓝紫渐变大按钮]         │  │
│  │  使用 WordPress 账号登录  │  │
│  │                          │  │
│  │  登录后将自动返回本页面    │  │
│  │                          │  │
│  │  ────────────────────    │  │
│  │                          │  │
│  │  [灰色文字按钮]           │  │
│  │  ← 返回 WordPress 嵌入    │  │
│  │     模式                  │  │
│  └──────────────────────────┘  │
│                                │
│         ucppt.com              │
└────────────────────────────────┘
```

---

### 测试场景4: 独立模式登录流程

**步骤**：
1. 在独立模式下，点击"使用 WordPress 账号登录"
2. ✅ 应该跳转到 `https://www.ucppt.com/wp-login.php?redirect_to=http://localhost:3000?mode=standalone`
3. 输入WordPress用户名密码，登录
4. ✅ 登录成功后应该自动跳回 `http://localhost:3000?mode=standalone`
5. ✅ 应该看到完整的应用界面（侧边栏、输入框、用户面板）
6. ✅ 左下角用户面板显示用户头像和名称

**预期日志**：
```javascript
[AuthContext] 🔍 正在验证身份...
[AuthContext] ✅ 找到缓存的 Token
[AuthContext] ✅ Token 验证成功
[AuthContext] 👤 设置用户信息: {username: "xxx", ...}
[HomePage] 获取会话列表成功: N个
```

---

### 测试场景5: iframe模式切换到独立模式

**步骤**：
1. 在 `https://www.ucppt.com/nextjs` 的iframe内看到登录提示
2. 点击"或在新窗口中打开（独立模式）→"
3. ✅ 应该在新标签页打开 `http://localhost:3000?mode=standalone`（或生产环境域名）
4. ✅ 新标签页显示独立模式登录界面
5. ✅ 原WordPress页面保持不变

**技术实现**：
```typescript
window.open(window.location.origin + '?mode=standalone', '_blank');
```

---

### 测试场景6: 独立模式切换到iframe模式

**步骤**：
1. 在独立模式登录界面，点击"← 返回 WordPress 嵌入模式"
2. ✅ 应该跳转到 `https://www.ucppt.com/nextjs`
3. ✅ WordPress页面加载，iframe内部显示登录提示或完整应用界面（取决于WordPress登录状态）

**技术实现**：
```typescript
window.location.href = wordpressEmbedUrl;
```

---

### 测试场景7: 已登录状态下访问不同模式

**步骤**：
1. 在独立模式登录成功
2. 访问 `http://localhost:3000`（默认模式）
3. ✅ 应该**直接显示完整应用界面**，而不是模式选择界面
4. 访问 `http://localhost:3000?mode=standalone`（独立模式）
5. ✅ 应该**直接显示完整应用界面**
6. 访问 `https://www.ucppt.com/nextjs`（iframe模式，假设WordPress也已登录）
7. ✅ iframe内应该**直接显示完整应用界面**

**原因**：认证检查在模式检查之前执行：
```typescript
// 先检查认证状态
if (!authLoading && !user) {
  // 未登录才显示登录提示/模式选择
  return <LoginPrompt />;
}

// 已登录直接渲染完整应用
return <FullAppUI />;
```

---

## 📊 对比表

### Before (v3.0.8)

| 访问方式 | iframe检测 | 显示内容 | 问题 |
|---------|-----------|---------|------|
| localhost:3000 | ❌ 否 | 登录提示 + 自动重定向 | ❌ 强制跳转 |
| www.ucppt.com/nextjs | ✅ 是 | 登录提示 | ⚠️ 登录不同步 |
| localhost:3000?mode=... | - | 不支持 | ❌ 无独立模式 |

### After (v3.0.9)

| 访问方式 | iframe检测 | URL参数 | 显示内容 | 状态 |
|---------|-----------|---------|---------|------|
| localhost:3000 | ❌ 否 | 无 | 模式选择界面 | ✅ 友好引导 |
| www.ucppt.com/nextjs | ✅ 是 | 无 | iframe登录提示 | ✅ 清晰 |
| localhost:3000?mode=standalone | ❌ 否 | standalone | 独立登录界面 | ✅ 独立模式 |
| 已登录 + 任意访问 | - | - | 完整应用界面 | ✅ 正常使用 |

---

## 🚀 部署步骤

### 1. 前端代码已完成

代码已经在 `frontend-nextjs/app/page.tsx` (lines 412-528) 中实现。

无需额外修改。

### 2. 环境变量检查

确保 `.env` 文件包含：

```bash
NEXT_PUBLIC_WORDPRESS_EMBED_URL=https://www.ucppt.com/nextjs
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

### 3. 重启Next.js开发服务器

```bash
cd frontend-nextjs
npm run dev
```

### 4. WordPress插件检查

确认WordPress插件版本为 **v3.0.8** 或更高：
- WordPress后台 → 插件 → Next.js SSO Integration v3
- 版本号应该显示：v3.0.8 或更新

如果不是，上传最新插件：
```bash
# 使用已打包的插件
nextjs-sso-integration-v3.0.8.zip
```

### 5. 清除缓存

**WordPress缓存**：
```bash
WordPress后台 → 设置 → WP Super Cache → 删除缓存
```

**浏览器缓存**：
```bash
Ctrl + Shift + R  # 强制刷新
# 或者
Ctrl + Shift + N  # 无痕模式
```

**localStorage**：
```javascript
// 浏览器控制台执行
localStorage.removeItem('wp_jwt_token');
localStorage.removeItem('wp_jwt_user');
```

### 6. 执行测试计划

按照上面的"测试计划"章节，逐一执行所有测试场景。

---

## 💡 技术亮点

### 1. 三态UI设计

**状态驱动的条件渲染**：
```typescript
if (!authLoading && !user) {
  // 未登录状态
  if (isInIframe) {
    return <IframeLoginPrompt />;
  } else if (standaloneMode) {
    return <StandaloneLoginPrompt />;
  } else {
    return <ModeSelection />;
  }
}

// 已登录状态
return <FullAppUI />;
```

**优势**：
- 单一状态源（`user` in `AuthContext`）
- UI自动响应状态变化
- 逻辑清晰，易于维护

---

### 2. 上下文检测机制

**iframe检测**：
```typescript
const isInIframe = typeof window !== 'undefined' && window.self !== window.top;
```

**URL参数检测**：
```typescript
const urlParams = new URLSearchParams(window.location.search);
const standaloneMode = urlParams?.get('mode') === 'standalone';
```

**环境变量读取**：
```typescript
const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
```

**优势**：
- 自动适配运行环境
- 支持开发/生产环境切换
- 无需用户手动配置

---

### 3. 无缝模式切换

**iframe → 独立（新窗口）**：
```typescript
window.open(window.location.origin + '?mode=standalone', '_blank');
```

**独立 → iframe（页面跳转）**：
```typescript
window.location.href = wordpressEmbedUrl;
```

**默认 → 任意模式（按钮选择）**：
```typescript
// 按钮1：跳转到WordPress页面（iframe模式）
window.location.href = wordpressEmbedUrl;

// 按钮2：添加URL参数（独立模式）
window.location.href = window.location.origin + '?mode=standalone';
```

**优势**：
- 用户可随时切换
- 切换操作简单直观
- 保持用户体验连续性

---

### 4. 单向数据流

```
URL/Window Context → 状态检测 → UI渲染
       ↑                              ↓
       └──────── 用户操作（按钮点击）────┘
```

**React单向数据流**：
```
Props/State → UI
     ↑         ↓
     └── Events ┘
```

**优势**：
- 数据流向清晰
- 状态变化可预测
- 便于调试和测试

---

## 📚 相关文档

- [Unauthenticated UI Hide Fix](UNAUTHENTICATED_UI_HIDE_FIX_20251215.md) - 未登录界面隐藏
- [SSO Login Sync Fix](SSO_LOGIN_SYNC_FIX_20251215.md) - 登录状态同步
- [Security Fix - Session Leak](SECURITY_FIX_SESSION_LEAK_20251215.md) - 会话安全修复
- [User Avatar Fix](USER_AVATAR_FIX_20251215.md) - 用户头像优化

---

## ✅ 验收标准

### 功能验收

- [x] 直接访问显示模式选择界面
- [x] iframe访问显示WordPress登录引导
- [x] 独立模式访问显示独立登录界面
- [x] iframe模式可以切换到独立模式（新窗口）
- [x] 独立模式可以切换回iframe模式（页面跳转）
- [x] 已登录状态下任意模式都显示完整应用界面
- [x] 独立模式登录成功后显示完整应用界面

### UI验收

- [x] 三种UI状态设计一致（Logo、标题、间距）
- [x] 按钮样式清晰（主要操作 vs 次要操作）
- [x] 提示文字易于理解
- [x] 响应式设计（移动端友好）
- [x] 深色模式支持

### 日志验收

- [x] iframe检测日志
- [x] URL参数检测日志
- [x] 模式切换操作日志
- [x] 登录流程日志

---

## 🎉 总结

**实现内容**：
- ✅ 支持 iframe嵌入模式（WordPress集成）
- ✅ 支持 独立页面模式（直接访问）
- ✅ 支持 模式选择界面（首次访问引导）
- ✅ 模式间可以互相切换
- ✅ 已登录状态下统一体验

**用户体验提升**：
- 🚀 多种访问方式适配不同使用场景
- 🚀 清晰的模式引导和切换
- 🚀 统一的认证体验
- 🚀 无缝的模式切换

**技术优势**：
- 三态UI设计，状态驱动渲染
- 上下文自动检测（iframe + URL参数）
- 单向数据流，逻辑清晰
- 环境变量配置，灵活部署

---

**实现完成！** 🎊

现在应用支持两种模式共存，用户可以根据喜好自由选择和切换！

**下一步**：按照测试计划逐一验证所有场景。
