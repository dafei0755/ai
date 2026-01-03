# WordPress SSO 退出登录循环问题修复 v2.2.1

## 问题描述

**v2.2 版本存在的自动循环问题**：

```
用户点击"退出登录"
    ↓
跳转到 localhost:3000/auth/logout
    ↓
3秒倒计时后自动跳转到 ucppt.com/js
    ↓
ucppt.com/js 检测到 WordPress 仍处于登录状态
    ↓
自动生成 JWT Token 并跳转到 Next.js
    ↓
用户又回到了登录状态（死循环！）
```

**根本原因**：
- Next.js 退出登录只清除了本地 localStorage 中的 Token
- WordPress 的登录会话 (Cookie) 仍然有效
- 访问 ucppt.com/js 时自动检测到 WordPress 登录状态，自动重新登录

## 解决方案 v2.2.1

### 修改内容

**文件**: [frontend-nextjs/app/auth/logout/page.tsx](frontend-nextjs/app/auth/logout/page.tsx)

### 关键修改

1. **移除自动倒计时跳转**
   - ❌ 删除了 `useState(5)` 倒计时状态
   - ❌ 删除了 `useEffect` 自动跳转逻辑
   - ✅ 用户必须手动点击按钮才能跳转

2. **新增两个操作按钮**

   **按钮 1: "重新登录应用"** (橙色主按钮)
   - 点击后跳转到 `ucppt.com/js`
   - WordPress 已登录用户会自动跳转回 Next.js
   - WordPress 未登录用户会看到登录/注册选择界面

   **按钮 2: "在 WordPress 也退出登录"** (白色次按钮)
   - 点击后跳转到 `ucppt.com/wp-login.php?action=logout`
   - 彻底退出 WordPress 登录会话
   - 下次访问 ucppt.com/js 需要重新登录

3. **新增提示信息**
   - 蓝色背景提示框
   - 说明用户已退出 Next.js 应用
   - 提示如需彻底退出，需在 WordPress 也执行登出

### 新的退出流程

#### 场景 A: 只退出 Next.js 应用（默认）

```
用户点击"退出登录"
    ↓
跳转到 localhost:3000/auth/logout
    ↓
显示"退出成功"页面（停留，不自动跳转）
    ↓
用户看到两个选择：
    ├─ "重新登录应用" → 跳转到 ucppt.com/js → 自动登录回 Next.js
    └─ "在 WordPress 也退出登录" → 跳转到 WordPress 登出页
```

#### 场景 B: 彻底退出（双端退出）

```
用户点击"退出登录"
    ↓
跳转到 localhost:3000/auth/logout
    ↓
用户点击"在 WordPress 也退出登录"
    ↓
跳转到 ucppt.com/wp-login.php?action=logout
    ↓
WordPress 登出成功，跳转到 WordPress 登录页
    ↓
用户在 WordPress 和 Next.js 都已退出登录
```

#### 场景 C: 退出后重新登录

```
用户点击"退出登录"
    ↓
跳转到 localhost:3000/auth/logout
    ↓
用户点击"重新登录应用"
    ↓
跳转到 ucppt.com/js
    ↓
检测到 WordPress 仍登录 → 自动跳转回 Next.js（无需重新输入密码）
    ↓
用户重新登录成功
```

## 界面优化

### 退出成功页面布局

```
┌─────────────────────────────────────┐
│   [橙色圆形图标 - LogOut]           │
│                                     │
│   退出成功                          │
│   您已成功退出极致概念 AI 设计高参  │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 您已退出 Next.js 应用           │ │  ← 蓝色提示框
│ │ 如需彻底退出，请在 WordPress 也 │ │
│ │ 执行登出操作                    │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [重新登录应用] ← 橙色渐变主按钮     │
│                                     │
│ [在 WordPress 也退出登录] ← 白色边框│
│                                     │
│ 返回设计知外主站 ← 灰色小字链接     │
└─────────────────────────────────────┘
```

### 按钮样式

**主按钮**（重新登录应用）:
- 橙色渐变背景 (`bg-orange-600`)
- 白色文字
- Home 图标
- 悬停时变深色 (`hover:bg-orange-700`)

**次按钮**（在 WordPress 也退出登录）:
- 白色背景，灰色边框
- 灰色文字
- ExternalLink 图标
- 悬停时浅灰背景 (`hover:bg-gray-50`)

## 代码变更对比

### 删除的代码

```typescript
// ❌ 删除倒计时状态
const [countdown, setCountdown] = useState(5);

// ❌ 删除自动跳转逻辑
useEffect(() => {
  const timer = setInterval(() => {
    setCountdown((prev) => {
      if (prev <= 1) {
        clearInterval(timer);
        window.location.href = 'https://www.ucppt.com/js';
        return 0;
      }
      return prev - 1;
    });
  }, 1000);

  return () => clearInterval(timer);
}, []);

// ❌ 删除倒计时提示
<div className="bg-gray-50 rounded-lg p-4 mb-6">
  <p className="text-sm text-gray-600">
    {countdown > 0 ? (
      <>将在 <span className="font-bold text-orange-600">{countdown}</span> 秒后返回登录引导页...</>
    ) : (
      '正在跳转...'
    )}
  </p>
</div>
```

### 新增的代码

```typescript
// ✅ 新增 WordPress 登出函数
const handleWordPressLogout = () => {
  window.location.href = 'https://www.ucppt.com/wp-login.php?action=logout';
};

// ✅ 新增蓝色提示框
<div className="bg-blue-50 rounded-lg p-4 mb-6">
  <p className="text-sm text-blue-800">
    您已退出 Next.js 应用
  </p>
  <p className="text-xs text-blue-600 mt-1">
    如需彻底退出，请在 WordPress 也执行登出操作
  </p>
</div>

// ✅ 新增 WordPress 退出按钮
<button
  onClick={handleWordPressLogout}
  className="w-full bg-white hover:bg-gray-50 text-gray-700 border border-gray-300 font-medium py-3 px-6 rounded-lg transition-colors flex items-center justify-center space-x-2"
>
  <ExternalLink className="w-5 h-5" />
  <span>在 WordPress 也退出登录</span>
</button>

// ✅ 新增 ExternalLink 图标导入
import { LogOut, Home, ExternalLink } from 'lucide-react';
```

## 用户体验优化

### 优化前（v2.2）
- ❌ 自动倒计时跳转，用户无法控制
- ❌ 退出后自动循环回到登录状态
- ❌ 无法彻底退出 WordPress 登录
- ❌ 用户困惑为什么退出了又自动登录

### 优化后（v2.2.1）
- ✅ 用户完全控制跳转时机
- ✅ 提供两种退出选项（仅 Next.js / 双端退出）
- ✅ 清晰的提示信息，解释退出状态
- ✅ 灵活的重新登录方式（自动 SSO / 手动登录）

## 测试清单

### 测试 1: 仅退出 Next.js

- [ ] 在 Next.js 应用中点击"退出登录"
- [ ] 跳转到 localhost:3000/auth/logout
- [ ] 看到"退出成功"橙色页面
- [ ] 看到蓝色提示框："您已退出 Next.js 应用"
- [ ] 看到两个按钮："重新登录应用" 和 "在 WordPress 也退出登录"
- [ ] 页面**不自动跳转**（停留在退出成功页）

### 测试 2: 重新登录（WordPress 仍登录）

- [ ] 在退出成功页点击"重新登录应用"
- [ ] 跳转到 ucppt.com/js
- [ ] 页面自动检测 WordPress 登录状态
- [ ] 自动生成 Token 并跳转到 localhost:3000/auth/callback
- [ ] 验证成功，跳转到 Next.js 首页
- [ ] 用户重新登录成功（无需输入密码）

### 测试 3: 彻底退出（双端退出）

- [ ] 在退出成功页点击"在 WordPress 也退出登录"
- [ ] 跳转到 ucppt.com/wp-login.php?action=logout
- [ ] WordPress 提示"您确定要登出吗？"
- [ ] 点击确认后，WordPress 登出成功
- [ ] 访问 ucppt.com/js，看到登录/注册选择界面（未自动登录）
- [ ] 点击"登录已有账号"，需要重新输入用户名和密码

### 测试 4: 返回主站链接

- [ ] 在退出成功页点击"返回设计知外主站"
- [ ] 跳转到 https://www.ucppt.com
- [ ] WordPress 主页显示正常

## 部署步骤

### 无需更新 WordPress 插件

此次修复仅涉及 Next.js 前端代码，WordPress 插件保持 v2.2 不变。

### 更新 Next.js 前端

**方式 1: 自动热重载（开发环境）**

如果 `npm run dev` 正在运行，文件修改会自动生效，无需重启。

**方式 2: 重启服务（推荐）**

```bash
# 停止 Next.js 服务 (Ctrl+C)
# 重新启动
cd frontend-nextjs
npm run dev
```

### 验证更新

1. 访问 http://localhost:3000
2. 登录应用
3. 点击左下角"退出登录"
4. 应该看到新的退出成功页面（无自动倒计时）
5. 页面停留，不自动跳转 ✅

## 技术细节

### 为什么会产生循环？

**WordPress Cookie 机制**:
- WordPress 登录后在 `ucppt.com` 域下设置 Cookie
- Cookie 名称: `wordpress_logged_in_*`
- 过期时间: 默认 14 天（或"记住我"勾选后）

**Next.js localStorage 机制**:
- Next.js 应用在 `localhost:3000` 域下存储 Token
- 存储位置: `localStorage.setItem('wp_jwt_token', token)`
- 清除方式: `localStorage.removeItem('wp_jwt_token')`

**循环形成原因**:
1. Next.js 退出只清除了 `localhost:3000` 的 localStorage
2. WordPress Cookie 仍存在于 `ucppt.com` 域下
3. 访问 `ucppt.com/js` 时，WordPress 认为用户已登录
4. 自动生成新 Token 并跳转回 Next.js
5. 形成死循环

### 解决方案设计原则

1. **不自动跳转**: 让用户主动控制流程
2. **提供选择**: 部分退出 vs 完全退出
3. **清晰提示**: 解释当前状态和操作后果
4. **灵活恢复**: 支持快速重新登录（利用 WordPress Session）

## 版本历史

- **v2.2.1** (2025-12-13): 修复退出登录自动循环问题
- **v2.2** (2025-12-13): 登录/注册引导页 + 退出流程优化
- **v2.1** (2025-12-12): JWT 密钥统一 + 双格式兼容
- **v2.0** (2025-12-12): 初始 SSO 集成版本

## 常见问题 FAQ

### Q1: 为什么退出后还能自动登录？

**A**: 因为您只退出了 Next.js 应用，WordPress 仍处于登录状态。访问 ucppt.com/js 时，WordPress 会自动识别您的登录状态并重新生成 Token。

### Q2: 如何彻底退出登录？

**A**: 在退出成功页点击"在 WordPress 也退出登录"按钮，会同时清除 WordPress 的登录会话。

### Q3: 退出后不想跳转到登录页怎么办？

**A**: 现在退出成功页不会自动跳转，您可以：
- 点击"重新登录应用"手动跳转
- 点击"返回设计知外主站"回到 WordPress 主页
- 关闭浏览器标签页

### Q4: WordPress 退出登录后会跳转到哪里？

**A**: 点击"在 WordPress 也退出登录"后，WordPress 会：
1. 显示确认对话框："您确定要登出吗？"
2. 登出成功后跳转到 WordPress 登录页 (`wp-login.php`)
3. 可以从登录页重新登录或返回主站

### Q5: 如何快速重新登录？

**A**: 如果您只是想"切换账号"或"重新刷新登录状态"：
1. 点击"退出登录"
2. 在退出成功页点击"重新登录应用"
3. 自动跳转回 Next.js（无需输入密码）

这利用了 WordPress 的 Session 持久化机制，提供快速重新登录体验。

## 成功标准 ✅

- [x] 退出登录后页面不自动跳转
- [x] 用户可手动选择"重新登录"或"彻底退出"
- [x] 提供清晰的状态提示（蓝色提示框）
- [x] 两个按钮样式区分明显（主次按钮）
- [x] 不再形成自动循环
- [x] 用户体验流畅，无困惑
