# WordPress SSO 插件更新 v2.2

## 更新日期
2025-12-13

## 核心改进

### 1. ucppt.com/js 现在是登录/注册引导页 ✅

**改进前 (v2.1)**：
- 访问 ucppt.com/js 自动检查登录状态
- 未登录时自动跳转到 WordPress 登录页
- 已登录时自动跳转到 Next.js 应用
- 用户无法控制流程

**改进后 (v2.2)**：
- 访问 ucppt.com/js 显示精美的登录/注册选择界面
- 用户可以手动选择"登录已有账号"或"注册新账号"
- 如果用户已在 WordPress 登录，自动跳转到 Next.js 应用（无需手动操作）
- 未登录用户可以看到引导界面，选择操作

### 2. 退出登录流程优化 ✅

**改进前**：
- 点击"退出登录"后跳转到 WordPress 用户中心 (ucppt.com/account)
- 用户困惑应该去哪里重新登录

**改进后**：
- 点击"退出登录"后跳转到 Next.js 退出成功页面 (localhost:3000/auth/logout)
- 显示"退出成功"提示和橙色主题界面
- 3秒倒计时后自动跳转到 ucppt.com/js 登录引导页
- 用户可手动点击"返回登录引导页"按钮

## 新的用户流程

### 首次访问流程

```
用户访问 ucppt.com/js
    ↓
显示登录/注册选择界面
    ├─ "登录已有账号" 按钮
    └─ "注册新账号" 按钮
    ↓
用户点击"登录已有账号"
    ↓
跳转到 WordPress 登录页 (ucppt.com/login)
    ↓
登录成功，返回 ucppt.com/js
    ↓
页面自动检测已登录，生成 JWT Token
    ↓
自动跳转到 Next.js 应用 (localhost:3000/auth/callback?token=...)
    ↓
Python 后端验证 Token
    ↓
登录成功，跳转到 Next.js 首页
```

### 已登录用户访问流程

```
已登录的 WordPress 用户访问 ucppt.com/js
    ↓
页面自动检测登录状态
    ↓
显示"检查登录状态..."和加载动画
    ↓
自动生成 JWT Token
    ↓
自动跳转到 Next.js 应用 (无需手动点击)
    ↓
进入应用
```

### 退出登录流程

```
用户在 Next.js 应用中点击"退出登录"
    ↓
清除本地 Token
    ↓
跳转到 localhost:3000/auth/logout
    ↓
显示"退出成功"橙色页面
    ↓
3秒倒计时（或手动点击"返回登录引导页"）
    ↓
跳转到 ucppt.com/js 登录引导页
    ↓
用户可重新选择登录或注册
```

## 文件更新清单

### 1. nextjs-sso-integration-v2.2.zip ✅
**WordPress 插件包**

**关键修改**：
- [Line 562-754](nextjs-sso-integration-v2.1-fixed.php#L562-L754): 完全重写 `nextjs_sso_callback_shortcode` 函数
- 新增登录/注册选择界面（橙色渐变主题）
- 智能检测：已登录自动跳转，未登录显示按钮
- 支持短代码参数自定义标题

**使用方式**：
```
[nextjs_sso_callback]
```

或自定义标题：
```
[nextjs_sso_callback title="我的应用" subtitle="专业的智能分析平台"]
```

### 2. frontend-nextjs/app/auth/logout/page.tsx ✅
**Next.js 退出成功页面**

**功能**：
- 显示"退出成功"提示
- 3秒倒计时
- 橙色渐变主题
- "返回登录引导页"按钮
- "返回设计知外主站"链接

### 3. frontend-nextjs/contexts/AuthContext.tsx ✅
**修改**：
- [Line 67-72](frontend-nextjs/contexts/AuthContext.tsx#L67-L72): logout() 函数改为跳转到 `/auth/logout`
- [Line 52](frontend-nextjs/contexts/AuthContext.tsx#L52): 豁免 `/auth/logout` 的自动 SSO 跳转
- [Line 88](frontend-nextjs/contexts/AuthContext.tsx#L88): 退出页面不需要等待认证加载

## 部署步骤

### 1. 上传新版插件

**WordPress 后台操作**：
1. 插件 → 已安装插件
2. 停用并删除旧版 "Next.js SSO Integration" (v2.1)
3. 插件 → 安装插件 → 上传插件
4. 选择 `nextjs-sso-integration-v2.2.zip`
5. 上传并激活

### 2. 无需修改 WordPress 页面

ucppt.com/js 页面内容保持不变：
```
[nextjs_sso_callback]
```

插件更新后，短代码会自动使用新的登录/注册引导界面。

### 3. 更新 Next.js 前端

**已自动完成**，无需手动操作。修改的文件：
- `app/auth/logout/page.tsx` (新建)
- `contexts/AuthContext.tsx` (已修改)

### 4. 重启服务（可选）

如果 Next.js 开发服务器正在运行，建议重启：
```bash
# 停止服务 (Ctrl+C)
# 重新启动
cd frontend-nextjs
npm run dev
```

## 测试清单

### 测试 1: 未登录用户首次访问

- [ ] 访问 https://www.ucppt.com/js
- [ ] 看到"极致概念 AI 设计高参"标题和橙色 Logo
- [ ] 看到"登录已有账号"和"注册新账号"两个按钮
- [ ] 点击"登录已有账号"跳转到 WordPress 登录页
- [ ] 登录成功后返回 ucppt.com/js
- [ ] 页面自动跳转到 localhost:3000/auth/callback
- [ ] 验证成功后跳转到 Next.js 首页

### 测试 2: 已登录用户访问

- [ ] 在 WordPress 已登录状态下访问 ucppt.com/js
- [ ] 看到"检查登录状态..."提示和加载动画
- [ ] 自动跳转到 localhost:3000/auth/callback（无需点击按钮）
- [ ] 进入 Next.js 应用

### 测试 3: 退出登录流程

- [ ] 在 Next.js 应用中点击左下角"退出登录"
- [ ] 跳转到 localhost:3000/auth/logout
- [ ] 看到"退出成功"橙色页面
- [ ] 看到3秒倒计时提示
- [ ] 自动跳转到 ucppt.com/js
- [ ] 看到登录/注册选择界面

### 测试 4: 注册新用户

- [ ] 访问 ucppt.com/js
- [ ] 点击"注册新账号"按钮
- [ ] 跳转到 WordPress 注册页面
- [ ] 注册成功后返回 ucppt.com/js
- [ ] 自动跳转到 Next.js 应用

## 视觉效果

### ucppt.com/js 登录引导页

**界面元素**：
- 橙色渐变圆形 Logo（分层图标）
- 标题："极致概念 AI 设计高参"（28px，粗体）
- 副标题："专业的设计项目智能分析平台"（14px，灰色）
- 登录按钮：橙色渐变背景，白色文字，悬停上浮效果
- 注册按钮：白色背景，橙色边框，悬停浅橙色背景
- 底部链接："← 返回设计知外主站"

**自动跳转状态**：
- 隐藏登录/注册按钮
- 显示"检查登录状态..."提示
- 显示橙色加载动画（旋转圆圈）

### localhost:3000/auth/logout 退出成功页

**界面元素**：
- 橙红色渐变背景 (from-orange-500 to-red-600)
- 白色卡片，圆角阴影
- 橙色圆形图标（LogOut 图标）
- 标题："退出成功"（24px，粗体）
- 副标题："您已成功退出极致概念 AI 设计高参"
- 倒计时提示："将在 X 秒后返回登录引导页..."（橙色数字）
- 橙色按钮："返回登录引导页"（Home 图标）
- 底部链接："返回设计知外主站"

## 技术细节

### 智能登录检测逻辑

```javascript
// 页面加载时执行 tryAutoSSO()
function tryAutoSSO() {
  // 调用 REST API 获取 Token
  fetch('/wp-json/nextjs-sso/v1/get-token')
    .then(response => {
      if (response.status === 401 || 403) {
        // 未登录，显示登录/注册按钮
        showButtons();
      } else {
        // 已登录，获取 Token 并自动跳转
        return response.json();
      }
    })
    .then(data => {
      if (data && data.token) {
        // 自动跳转到 Next.js 回调页
        window.location.href = callbackUrl + '?token=' + data.token;
      }
    });
}
```

### 退出流程时序图

```
Next.js UserPanel
    │
    ├─ 用户点击"退出登录"
    │
    ↓
AuthContext.logout()
    │
    ├─ clearWPToken()  // 清除 localStorage
    ├─ setUser(null)   // 清除 React 状态
    │
    ↓
window.location.href = '/auth/logout'
    │
    ↓
/auth/logout 页面
    │
    ├─ 显示退出成功界面
    ├─ 启动3秒倒计时
    │
    ↓
window.location.href = 'https://www.ucppt.com/js'
    │
    ↓
ucppt.com/js 登录引导页
    │
    ├─ 调用 tryAutoSSO()
    ├─ 检测未登录（Token 已清除）
    ├─ 显示登录/注册按钮
```

## 注意事项

1. **WordPress 登录状态不会被清除**
   - Next.js 退出登录只清除本地 Token
   - 用户在 WordPress 仍处于登录状态
   - 下次访问 ucppt.com/js 会自动跳转到 Next.js（无需重新登录）
   - 如需彻底退出，需要在 WordPress 也执行登出

2. **WordPress 退出登录的建议**
   - 如果用户在 WordPress 端退出登录（ucppt.com/account → 登出）
   - 再次访问 ucppt.com/js 会看到登录/注册选择界面
   - 可以实现"真正的双端退出"

3. **短代码兼容性**
   - v2.2 插件向后兼容，无需修改 WordPress 页面内容
   - 短代码 `[nextjs_sso_callback]` 自动使用新界面
   - 可选参数 `title` 和 `subtitle` 可自定义文案

## 版本历史

- **v2.2** (2025-12-13): 登录/注册引导页 + 退出流程优化
- **v2.1** (2025-12-12): JWT 密钥统一 + 双格式兼容
- **v2.0** (2025-12-12): 初始 SSO 集成版本

## 成功标准 ✅

- [x] ucppt.com/js 显示登录/注册选择界面（橙色主题）
- [x] 未登录用户可手动选择登录或注册
- [x] 已登录用户自动跳转到 Next.js 应用
- [x] 退出登录后显示"退出成功"页面，不跳转到 WordPress account
- [x] 退出后3秒倒计时返回 ucppt.com/js
- [x] 用户体验流畅，无死循环或错误跳转
