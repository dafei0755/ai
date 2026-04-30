# WordPress 原生登录弹窗集成 v2.5

## 更新日期
2025-12-13

## 更新内容

**v2.5**: 触发 WordPress 原生登录弹窗，替代简单的登录引导卡片

## 问题背景

### v2.3 的登录界面

当未登录用户访问 `https://www.ucppt.com/nextjs` 时，显示的是简单的橙色卡片式登录引导：

```
┌─────────────────────────────┐
│   [橙色圆形图标]            │
│                             │
│   需要登录                  │
│   请先登录以访问 AI 设计高参│
│                             │
│   [立即登录]  ← 跳转到登录页│
└─────────────────────────────┘
```

### 用户需求

用户希望登录界面样式与 WordPress 主题的原生登录弹窗保持一致（如截图2所示），提供更好的用户体验：

```
┌─────────────────────────────┐
│  [WordPress Logo]           │
│                             │
│  手机快捷登录 | 账号密码登录│
│  ─────────────              │
│  [手机号输入框]             │
│  [验证码输入框] [发送验证码]│
│  □ 记住我的登录状态         │
│                             │
│  [登录]                     │
│                             │
│  第三方账号登录             │
│  [微信图标]                 │
│                             │
│  还没有账号？ [立即注册]    │
└─────────────────────────────┘
```

## 解决方案 v2.5

### 核心改进

**将"立即登录"按钮从跳转链接改为触发器**：

1. **优先调用主题的登录弹窗 API**
   ```javascript
   if (window.ucpptLogin && window.ucpptLogin.showLoginModal) {
       window.ucpptLogin.showLoginModal();
   }
   ```

2. **次选方案：模拟点击导航栏登录按钮**
   ```javascript
   const loginLink = document.querySelector('header a:contains("登录")');
   loginLink.click();
   ```

3. **降级方案：跳转到 WordPress 登录页面**
   ```javascript
   window.location.href = 'https://www.ucppt.com/wp-login.php?redirect_to=...';
   ```

### 登录流程

#### 场景 A: WordPress 主题支持登录弹窗（理想）

```
用户访问 ucppt.com/nextjs（未登录）
    ↓
显示登录引导卡片
    ↓
用户点击"立即登录"
    ↓
检测到 window.ucpptLogin.showLoginModal ✅
    ↓
调用主题登录弹窗
    ↓
弹出登录框（手机快捷登录/账号密码登录）
    ↓
用户登录成功
    ↓
刷新页面 → WordPress 检测已登录
    ↓
加载 iframe，Next.js 自动 SSO 登录 ✅
```

#### 场景 B: 主题不支持弹窗，有导航栏登录链接

```
用户访问 ucppt.com/nextjs（未登录）
    ↓
显示登录引导卡片
    ↓
用户点击"立即登录"
    ↓
未检测到 ucpptLogin API ❌
    ↓
查找导航栏中的"登录"链接 ✅
    ↓
模拟点击导航栏登录链接
    ↓
触发 WordPress 原生登录流程
```

#### 场景 C: 降级方案（直接跳转登录页）

```
用户访问 ucppt.com/nextjs（未登录）
    ↓
显示登录引导卡片
    ↓
用户点击"立即登录"
    ↓
未检测到登录弹窗或导航链接 ❌
    ↓
跳转到 WordPress 登录页面
    ↓
登录成功后返回 ucppt.com/nextjs
```

## 代码实现

### 修改的文件

**`nextjs-sso-integration-v2.1-fixed.php`** (Line 843-893)

### 核心代码

```php
<button
    id="nextjs-login-button"
    type="button"
    style="...">
    立即登录
</button>

<script>
(function() {
    document.getElementById('nextjs-login-button').addEventListener('click', function() {
        // 方法 1: 调用主题登录弹窗 API
        if (typeof window.ucpptLogin !== 'undefined' && window.ucpptLogin.showLoginModal) {
            window.ucpptLogin.showLoginModal();
            return;
        }

        // 方法 2: 查找并点击登录链接
        const loginLinks = document.querySelectorAll('a[href*="login"], .login-link');
        if (loginLinks.length > 0) {
            loginLinks[0].click();
            return;
        }

        // 方法 3: 查找导航栏登录按钮
        const navLinks = document.querySelectorAll('nav a, header a');
        for (let link of navLinks) {
            if (link.textContent && link.textContent.includes('登录')) {
                link.click();
                return;
            }
        }

        // 方法 4: 降级 - 跳转到登录页面
        window.location.href = '<?php echo esc_url(wp_login_url(get_permalink())); ?>';
    });
})();
</script>
```

### 登录触发器优先级

1. **window.ucpptLogin.showLoginModal** - 主题自定义登录弹窗 API（最优先）
2. **a[href*="login"]** - 页面中的登录链接
3. **导航栏中文字包含"登录"的链接** - 导航栏登录按钮
4. **wp_login_url()** - WordPress 原生登录页面（降级方案）

## 部署步骤

### 1. 上传新版插件

**WordPress 后台操作**：
1. 插件 → 已安装插件
2. 停用并删除旧版 "Next.js SSO Integration"（v2.3 或更早版本）
3. 插件 → 安装插件 → 上传插件
4. 选择 `nextjs-sso-integration-v2.5.zip`
5. 上传并激活

### 2. 无需修改 WordPress 页面

`https://www.ucppt.com/nextjs` 页面内容保持不变：
```
[nextjs_app]
```

### 3. 测试登录流程

1. 在隐身窗口访问 `https://www.ucppt.com/nextjs`
2. 看到登录引导卡片
3. 点击"立即登录"
4. **预期结果**：
   - 如果主题支持，弹出登录弹窗（手机快捷登录/账号密码登录）
   - 如果主题不支持，模拟点击导航栏登录链接或跳转到登录页面

## 如何让主题支持登录弹窗 API

如果您的 WordPress 主题想要提供登录弹窗，需要在主题的 JavaScript 中暴露全局对象：

```javascript
window.ucpptLogin = {
    showLoginModal: function() {
        // 显示登录弹窗的逻辑
        document.getElementById('login-modal').style.display = 'block';
    },
    hideLoginModal: function() {
        // 隐藏登录弹窗的逻辑
        document.getElementById('login-modal').style.display = 'none';
    }
};
```

**推荐位置**：主题的 `footer.php` 或 `functions.php` 中添加 `wp_footer` 钩子。

## 调试技巧

### 浏览器开发者工具

打开浏览器控制台（F12），在未登录状态下访问 `ucppt.com/nextjs`，点击"立即登录"，查看日志：

```javascript
// 如果主题有登录弹窗 API
console.log('window.ucpptLogin:', window.ucpptLogin);
// 输出: {showLoginModal: ƒ, hideLoginModal: ƒ}

// 如果找到了导航栏登录链接
console.log('找到登录链接:', loginLinks);
// 输出: NodeList(1) [a.login-link]
```

### 手动测试登录弹窗

在控制台手动调用：

```javascript
// 测试主题登录弹窗
if (window.ucpptLogin) {
    window.ucpptLogin.showLoginModal();
}

// 查找页面中的所有登录相关链接
document.querySelectorAll('a[href*="login"], a[href*="注册"]');
```

## 故障排查

### 问题 1: 点击"立即登录"无反应

**排查**：
1. 打开浏览器控制台，看是否有 JavaScript 错误
2. 检查是否成功加载了插件的 JavaScript 代码
3. 检查 `window.ucpptLogin` 是否存在

**解决**:
- 如果控制台有错误，可能是主题 JavaScript 冲突
- 清除浏览器缓存，刷新页面

### 问题 2: 点击"立即登录"跳转到登录页面而不是弹窗

**原因**: 主题不支持登录弹窗 API，或者导航栏没有登录链接

**解决**:
- 这是正常的降级行为
- 如果想要弹窗，需要在主题中添加 `window.ucpptLogin` API
- 或者安装支持登录弹窗的 WordPress 插件

### 问题 3: 登录后没有自动刷新

**原因**: 需要手动刷新页面

**解决**:
- 在主题的登录成功回调中添加页面刷新：
  ```javascript
  window.location.reload();
  ```
- 或者重定向到 `https://www.ucppt.com/nextjs`

## 登录后跳转统一化

### 所有登录成功后统一跳转到 `https://www.ucppt.com/nextjs`

**WordPress 登录页面**:
```php
<?php echo wp_login_url('https://www.ucppt.com/nextjs'); ?>
```

**SSO 回调页面** (`ucppt.com/js`):
- 已在插件中配置，登录成功后跳转到 Next.js 回调页
- Next.js 验证 Token 后，主页自动重定向到 `ucppt.com/nextjs`

**主题登录弹窗**:
- 建议在登录成功后刷新当前页面：
  ```javascript
  window.location.reload();
  ```
- 或者重定向到：
  ```javascript
  window.location.href = 'https://www.ucppt.com/nextjs';
  ```

## 兼容性

### 支持的 WordPress 主题

- ✅ 主题提供 `window.ucpptLogin` API（最佳）
- ✅ 导航栏有登录链接（兼容）
- ✅ 使用 WordPress 原生登录页面（降级）

### 浏览器兼容性

- ✅ Chrome、Firefox、Edge、Safari（现代浏览器）
- ⚠️ IE11 可能需要 Polyfill（不推荐）

## 版本历史

- **v2.5** (2025-12-13): 触发 WordPress 原生登录弹窗，多种触发方式
- **v2.4** (2025-12-13): iframe 自动 SSO 登录
- **v2.3.1** (2025-12-13): 主页自动重定向到 WordPress 嵌入页面
- **v2.3** (2025-12-13): 新增 `[nextjs_app]` 短代码，支持 iframe 嵌入
- **v2.2** (2025-12-13): 登录/注册引导页优化
- **v2.1** (2025-12-12): JWT 密钥统一修复
- **v2.0** (2025-12-12): 初始 SSO 集成

## 下一步优化

1. **登录成功后自动刷新**: 在主题登录弹窗成功回调中添加页面刷新逻辑
2. **统一样式**: 将登录引导卡片的样式完全改为主题登录弹窗的样式
3. **手机端适配**: 确保登录弹窗在手机端正常显示
4. **记住登录状态**: 支持"记住我"功能，14 天免登录

## 成功标准 ✅

- [x] 未登录用户点击"立即登录"触发 WordPress 原生登录弹窗（如果主题支持）
- [x] 降级方案工作正常（跳转到登录页面）
- [x] 多种登录触发方式自动检测和切换
- [x] 登录后统一跳转到 `https://www.ucppt.com/nextjs`
- [x] iframe 自动 SSO 登录正常工作
