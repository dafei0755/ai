# 🔍 应用自动跳转到登录页问题分析 v3.0.24

**报告日期：** 2025-12-17
**版本：** v3.0.24
**状态：** 🔍 问题分析中

---

## 🐛 问题描述

**用户反馈：**
1. "图1页面，点击会员升级后，会自动变为图2"
2. "补充，在应用页面，过一会也会自动跳转到登录页面"

**澄清后的问题：**
- 不是点击"升级会员"按钮导致的跳转
- 而是在应用页面（任何页面）待着，**过一会（约10秒）自动跳转到登录提示页面**

**复现步骤：**
1. 访问应用任何页面（如首页、分析页面）
2. 等待约10秒
3. 页面自动变成登录提示界面

---

## 🔍 根本原因分析

### 原因：WordPress未登录触发SSO同步清除Token

**时序流程：**

```
0秒:    用户访问应用（可能有过期Token或WordPress已退出）
        ↓
1秒:    应用加载，显示正常界面（基于本地Token）
        ↓
10秒:   SSO同步检测运行（checkSSOStatus）
        ↓
        GET https://www.ucppt.com/wp-json/nextjs-sso/v1/sync-status
        返回: {"logged_in": false, "user_id": 0}
        ↓
        检测到WordPress未登录，且本地有用户Token
        Token年龄 > 30秒 → 清除Token ✅
        ↓
        localStorage.removeItem('wp_jwt_token')
        localStorage.removeItem('wp_jwt_user')
        setUser(null)
        ↓
        HomePage检测到 !user → 显示登录提示界面
```

### 验证：WordPress登录状态

**当前WordPress登录状态：**
```bash
$ curl -s "https://www.ucppt.com/wp-json/nextjs-sso/v1/sync-status"
{
  "logged_in": false,
  "user_id": 0,
  "timestamp": 1765949934
}
```

**结论：** 用户确实没有在WordPress登录。

---

## 📋 相关代码分析

### 1. AuthContext SSO同步逻辑

**文件：** `frontend-nextjs/contexts/AuthContext.tsx`

**Lines 104-122：清除Token逻辑**
```typescript
// 情况2：WordPress已退出，但本地仍有用户 → 清除Token
// 🔥 v3.0.23修复：增加时间窗口保护，避免在初始登录阶段误清除Token
if (!data.logged_in && localUserId) {
  // 检查Token设置时间，如果是最近30秒内设置的，可能是初始登录中，不清除
  const tokenTimestamp = localStorage.getItem('wp_jwt_token_timestamp');
  const now = Date.now();
  const tokenAge = tokenTimestamp ? now - parseInt(tokenTimestamp) : Infinity;

  if (tokenAge > 30000) {
    // Token已存在超过30秒，确实是退出登录
    console.log('[AuthContext v3.0.23] ✅ 检测到WordPress已退出，清除本地Token');
    localStorage.removeItem('wp_jwt_token');
    localStorage.removeItem('wp_jwt_user');
    localStorage.removeItem('wp_jwt_token_timestamp');
    setUser(null);  // ← 这里触发了登录提示
    return;
  }
}
```

**触发条件：**
1. WordPress返回 `logged_in: false`
2. 本地有用户Token（`localUserId`存在）
3. Token年龄 > 30秒

**效果：** 清除Token，`user`变成`null`

---

### 2. HomePage登录提示逻辑

**文件：** `frontend-nextjs/app/page.tsx`

**Lines 417-419：未登录时显示登录界面**
```typescript
// 🎯 v3.0.15: 未登录时显示简化登录界面
if (!authLoading && !user) {
  return (
    <div className="flex h-screen bg-[var(--background)] text-[var(--foreground)] items-center justify-center p-4 relative">
      {/* 登录提示界面 */}
      <div className="...">
        <h1>请先登录</h1>
        <a href="https://www.ucppt.com/login">立即登录</a>
      </div>
    </div>
  );
}
```

**触发条件：**
1. 认证加载完成（`!authLoading`）
2. 用户未登录（`!user`）

**效果：** 显示登录提示界面，隐藏应用内容

---

## 🎯 期望行为 vs 实际行为

### 场景1：用户在WordPress已登录

| 时间点 | 期望行为 | 实际行为 | 状态 |
|-------|---------|---------|-----|
| 访问应用 | 正常使用 | 正常使用 | ✅ 正确 |
| 10秒后SSO检测 | 保持登录 | 保持登录 | ✅ 正确 |
| 使用应用 | 持续可用 | 持续可用 | ✅ 正确 |

---

### 场景2：用户在WordPress未登录（当前问题场景）

| 时间点 | 期望行为 | 实际行为 | 状态 |
|-------|---------|---------|-----|
| 访问应用（有过期Token） | ？ | 短暂显示应用 | ❓ 待定义 |
| 10秒后SSO检测 | ？ | 清除Token → 显示登录提示 | ❓ 待定义 |

**关键问题：** 应用在用户WordPress未登录时，应该如何表现？

**选项A：强制要求登录（当前行为）**
- ✅ 确保所有用户都经过身份验证
- ✅ SSO同步保持一致性
- ❌ 用户体验差：突然跳转，打断操作

**选项B：允许部分功能无需登录**
- ✅ 更好的用户体验
- ✅ 公开页面（如pricing）可正常访问
- ❌ 需要明确定义哪些功能需要登录
- ❌ 增加权限管理复杂度

---

## 💡 解决方案

### 方案1：用户在WordPress登录（推荐，最简单）

**操作步骤：**
1. 访问 https://www.ucppt.com/login
2. 输入用户名和密码登录
3. 登录成功后，应用会在10秒内自动同步
4. 应用恢复正常使用

**优点：**
- ✅ 无需修改代码
- ✅ 符合SSO设计初衷
- ✅ 确保用户身份验证

**缺点：**
- ❌ 需要用户手动登录

---

### 方案2：修改HomePage，允许未登录用户查看部分内容

**修改：** `frontend-nextjs/app/page.tsx`

**Lines 417-419改为：**
```typescript
// 🔧 v3.0.24修复：允许未登录用户查看应用（但限制部分功能）
if (!authLoading && !user) {
  // 不再强制显示登录提示，允许继续使用应用
  // 但某些功能（如启动分析）需要登录
  console.log('[HomePage] 用户未登录，允许查看但限制功能');
}

// 在启动分析按钮处检查登录状态
const handleSubmit = () => {
  if (!user) {
    // 提示用户登录
    alert('请先登录后再启动分析');
    window.location.href = 'https://www.ucppt.com/login';
    return;
  }
  // 继续分析...
};
```

**优点：**
- ✅ 用户可以浏览应用界面
- ✅ 公开内容（如历史会话列表、定价页面）可访问
- ✅ 仅在需要时才提示登录

**缺点：**
- ⚠️ 需要明确定义权限边界
- ⚠️ 增加代码复杂度

---

### 方案3：延长SSO检测间隔，减少打断频率

**修改：** `frontend-nextjs/contexts/AuthContext.tsx`

**将检测间隔从10秒改为60秒：**
```typescript
// 每60秒检查一次SSO状态（之前是10秒）
const intervalId = setInterval(checkSSOStatus, 60000);
```

**优点：**
- ✅ 减少打断频率
- ✅ 降低服务器请求量

**缺点：**
- ❌ 延迟同步时间（用户在WordPress登录后，最多等待60秒才同步）
- ❌ 不解决根本问题

---

### 方案4：首次访问立即检测，避免"突然跳转"

**修改：** 在应用加载时立即运行SSO检测，而不是等待10秒

```typescript
useEffect(() => {
  // 立即执行一次检测
  checkSSOStatus();

  // 然后每10秒检查一次
  const intervalId = setInterval(checkSSOStatus, 10000);
  return () => clearInterval(intervalId);
}, []);
```

**优点：**
- ✅ 避免"先显示应用，突然跳转"的体验问题
- ✅ 用户第一时间知道需要登录

**缺点：**
- ❌ 如果用户WordPress已登录但Cookie同步慢，可能误判

---

## 🤔 需要用户决策

**问题1：应用的核心功能是否必须登录？**
- [ ] 是 → 保持当前行为，引导用户登录WordPress
- [ ] 否 → 修改HomePage，允许未登录访问

**问题2：如果允许未登录访问，哪些功能需要登录？**
- [ ] 启动分析
- [ ] 查看历史会话
- [ ] 查看会员信息
- [ ] 查看定价页面（已修复为公开访问）

**问题3：SSO检测间隔是否合理？**
- [ ] 10秒（当前）- 及时同步，但可能频繁打断
- [ ] 30秒 - 平衡
- [ ] 60秒 - 减少打断，但同步延迟

---

## 📝 当前状态

**WordPress登录状态：** 未登录（`logged_in: false`）

**应用行为：**
1. 用户访问应用 → 短暂显示（1-10秒）
2. SSO检测发现WordPress未登录 → 清除Token
3. HomePage检测到`!user` → 显示登录提示

**符合设计：** ✅ 是的，这是v3.0.23的SSO同步机制正确工作

**用户体验：** ❌ "突然跳转"让用户感到困惑

---

## 🚀 推荐行动

**短期方案（立即可用）：**
1. **用户在WordPress登录**（最简单）
   - 访问 https://www.ucppt.com/login
   - 登录后应用自动恢复

**长期方案（需要开发）：**
2. **修改HomePage，改善未登录体验**
   - 允许查看应用界面
   - 在操作时才提示登录
   - 避免"突然跳转"

**配置优化：**
3. **首次访问立即检测SSO状态**
   - 避免"先显示，后跳转"的体验问题
   - 用户第一时间知道需要登录

---

## 📋 待用户确认

1. **是否愿意在WordPress登录？** 如果是，问题立即解决
2. **是否希望应用支持"未登录浏览"？** 如果是，需要明确功能权限
3. **SSO检测间隔是否需要调整？** 当前10秒，可改为30秒或60秒

---

**分析者：** Claude Code
**分析时间：** 2025-12-17
**下一步：** 等待用户决策
