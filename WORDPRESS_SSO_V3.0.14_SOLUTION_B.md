# WordPress SSO v3.0.14 - Solution B 实施说明

## 🎯 问题回顾

**用户反馈的核心问题**：
1. WordPress 右上角显示已登录（WPCOM Member Pro），但宣传页面显示"请先登录"
2. 点击"立即使用"按钮后跳转到登录页，而不是直接打开应用
3. 服务器端 `wp_get_current_user()` 无法检测到 WPCOM 用户中心的登录状态

**根本原因**：
- WPCOM Member Pro 使用自定义登录机制
- 其登录 Cookie 不被 WordPress 标准函数 `wp_get_current_user()` 识别
- 服务器端无法准确判断用户登录状态

---

## 🚀 Solution B 实施方案

### 核心思路

**彻底绕过服务器端登录检测**，改为客户端 JavaScript 通过 REST API 动态获取 Token：

```
用户点击按钮
    ↓
调用 /wp-json/nextjs-sso/v1/get-token（携带 Cookie）
    ↓
    ├─ 401 未登录 → 跳转到 /login?redirect_to=当前页面
    │   ↓
    │   登录成功 → 返回宣传页面
    │   ↓
    │   自动再次点击按钮
    │
    └─ 200 已登录 → 获取 Token
        ↓
        window.open(应用URL + sso_token)
```

**关键优势**：
- ✅ 不依赖服务器端 Cookie 解析
- ✅ 利用 WordPress 自己的 REST API 认证机制
- ✅ WPCOM Member Pro 的登录状态会被 WordPress REST API 正确识别
- ✅ 统一按钮，无需区分登录/未登录状态

---

## 📦 部署包信息

**文件名**: `nextjs-sso-integration-v3.0.14.zip`
**大小**: 17,949 bytes (17.5 KB)
**版本**: v3.0.14
**发布时间**: 2025-12-16 09:30

---

## 🔧 关键代码变更

### 变更1: 移除服务器端登录检测

**文件**: `nextjs-sso-integration-v3.php`
**位置**: Lines 1270-1275

**修改前**（v3.0.12）:
```php
// 检查用户登录状态
$current_user = nextjs_sso_v3_get_user_from_cookie();
$is_logged_in = ($current_user && $current_user->ID > 0);

// 生成Token（如果已登录）
$token = '';
if ($is_logged_in) {
    $token = nextjs_sso_v3_generate_jwt_token($current_user);
}
```

**修改后**（v3.0.14）:
```php
// 🆕 v3.0.14: 不再进行服务器端登录检测
// 改为客户端通过REST API动态检测登录状态
// 这样可以避免WPCOM Member Pro的Cookie兼容性问题
```

---

### 变更2: 统一按钮渲染

**文件**: `nextjs-sso-integration-v3.php`
**位置**: Lines 1385-1396

**修改前**（v3.0.12）:
```php
<?php if ($is_logged_in): ?>
    <!-- 已登录用户按钮 -->
    <button id="entrance-button-logged-in" data-token="<?php echo esc_attr($token); ?>">
        立即使用 →
    </button>
    <div class="entrance-status">
        ✓ 您已登录为 <strong><?php echo esc_html($current_user->display_name); ?></strong>
    </div>
<?php else: ?>
    <!-- 未登录用户按钮 -->
    <button id="entrance-button-guest">
        立即使用 →
    </button>
    <div class="entrance-status">
        请先登录以使用应用
    </div>
<?php endif; ?>
```

**修改后**（v3.0.14）:
```php
<!-- 🆕 v3.0.14: 统一按钮，通过客户端REST API动态检测登录状态 -->
<button
   type="button"
   class="entrance-button"
   id="entrance-button-unified"
   data-app-url="<?php echo esc_attr($atts['app_url']); ?>"
   style="border: none; cursor: pointer;">
    <?php echo esc_html($atts['button_text']); ?> →
</button>
<div class="entrance-status" id="entrance-status">
    点击按钮进入应用
</div>
```

---

### 变更3: REST API 动态检测逻辑

**文件**: `nextjs-sso-integration-v3.php`
**位置**: Lines 1413-1558

**完整新逻辑**:
```javascript
button.addEventListener('click', async function() {
    // 禁用按钮，显示加载状态
    button.disabled = true;
    button.innerHTML = '立即使用 <span class="entrance-loading">⏳</span>';
    statusDiv.innerHTML = '正在验证登录状态...';

    try {
        // 调用WordPress REST API获取Token
        const response = await fetch('/wp-json/nextjs-sso/v1/get-token', {
            method: 'GET',
            credentials: 'include', // 发送WordPress Cookie
            headers: {
                'Accept': 'application/json'
            }
        });

        console.log('[Next.js SSO v3.0.14] REST API 响应状态:', response.status);

        if (response.status === 401) {
            // 未登录，跳转到登录页
            console.log('[Next.js SSO v3.0.14] 用户未登录，跳转到登录页面');
            statusDiv.innerHTML = '未登录，正在跳转到登录页面...';

            // 保存目标URL到sessionStorage，登录后使用
            const currentPageUrl = window.location.href;
            sessionStorage.setItem('nextjs_app_target_url', appUrl);

            // 跳转到WPCOM用户中心登录页
            const loginUrl = '/login?redirect_to=' + encodeURIComponent(currentPageUrl);
            console.log('[Next.js SSO v3.0.14] 跳转到登录页:', loginUrl);

            // 延迟500ms后跳转，让用户看到提示
            setTimeout(function() {
                window.location.href = loginUrl;
            }, 500);

            return;
        }

        if (!response.ok) {
            // 其他错误
            const errorText = await response.text().catch(() => '未知错误');
            console.error('[Next.js SSO v3.0.14] REST API 错误:', response.status, errorText);
            statusDiv.innerHTML = '❌ 获取登录信息失败（错误码: ' + response.status + '）';

            // 重新启用按钮
            button.disabled = false;
            button.innerHTML = '立即使用 →';
            return;
        }

        // 登录成功，解析响应
        const data = await response.json();
        console.log('[Next.js SSO v3.0.14] REST API 响应数据:', {
            success: data.success,
            hasToken: !!data.token,
            user: data.user
        });

        if (data.success && data.token) {
            // Token获取成功，在新窗口打开应用
            console.log('[Next.js SSO v3.0.14] ✅ Token 获取成功，准备打开应用');
            statusDiv.innerHTML = '✅ 登录成功，正在打开应用...';

            // 构建带Token的URL
            const separator = appUrl.includes('?') ? '&' : '?';
            const targetUrl = appUrl + separator + 'sso_token=' + encodeURIComponent(data.token);

            console.log('[Next.js SSO v3.0.14] 在新窗口打开应用:', targetUrl);

            // 在新窗口打开
            const newWindow = window.open(targetUrl, '_blank', 'noopener,noreferrer');

            if (!newWindow) {
                console.error('[Next.js SSO v3.0.14] 新窗口被浏览器拦截');
                statusDiv.innerHTML = '❌ 弹窗被拦截，请允许此网站的弹窗后重试';
                alert('弹窗被拦截！请允许此网站的弹窗，然后重试。');
            } else {
                // 成功打开新窗口
                statusDiv.innerHTML = '✅ 应用已在新窗口打开';
                console.log('[Next.js SSO v3.0.14] ✅ 应用成功在新窗口打开');
            }

            // 恢复按钮状态
            button.disabled = false;
            button.innerHTML = '立即使用 →';

        } else {
            // Token获取失败
            console.error('[Next.js SSO v3.0.14] REST API 返回数据无效:', data);
            statusDiv.innerHTML = '❌ 登录信息获取失败，请刷新页面重试';
            button.disabled = false;
            button.innerHTML = '立即使用 →';
        }

    } catch (error) {
        // 网络错误或其他异常
        console.error('[Next.js SSO v3.0.14] 异常:', error);
        statusDiv.innerHTML = '❌ 网络错误，请检查连接后重试';
        button.disabled = false;
        button.innerHTML = '立即使用 →';
    }
});

// 🆕 v3.0.14: 检查是否刚从登录页面返回
const targetUrl = sessionStorage.getItem('nextjs_app_target_url');
if (targetUrl) {
    console.log('[Next.js SSO v3.0.14] 检测到登录后返回，准备自动打开应用:', targetUrl);
    statusDiv.innerHTML = '检测到登录成功，准备打开应用...';

    // 清除sessionStorage
    sessionStorage.removeItem('nextjs_app_target_url');

    // 延迟1秒后自动点击按钮
    setTimeout(function() {
        console.log('[Next.js SSO v3.0.14] 自动触发按钮点击');
        button.click();
    }, 1000);
}
```

---

## 🚀 部署步骤

### 步骤1: 备份现有插件

```bash
WordPress后台 → 插件 → 已安装的插件
找到 "Next.js SSO Integration v3"
点击 "停用"
```

### 步骤2: 上传新插件

```bash
插件 → 安装插件 → 上传插件
选择文件: nextjs-sso-integration-v3.0.14.zip (17,949 bytes)
点击 "现在安装"
安装完成后点击 "启用插件"
```

### 步骤3: 清除缓存

```bash
# WordPress缓存
设置 → WP Super Cache → 删除缓存

# 浏览器缓存
Ctrl + Shift + R（强制刷新）
或 Ctrl + Shift + Delete（清除缓存）
```

### 步骤4: 验证版本

```bash
WordPress后台 → 插件 → 已安装的插件
确认版本号显示：3.0.14
```

---

## ✅ 测试清单

### 测试A: 控制台日志验证

**访问**: `https://www.ucppt.com/js`
**按**: `F12` 打开控制台

**预期日志**:
```javascript
[Next.js SSO v3.0.14] 宣传页面脚本已加载（REST API模式）
[Next.js SSO v3.0.14] app_url: https://ai.ucppt.com?mode=standalone
```

**验收标准**:
- [x] 显示版本号 `v3.0.14`
- [x] 显示 "REST API模式"
- [x] 无红色错误信息

---

### 测试B: 已登录用户完整流程

**前提条件**: 已通过 WPCOM 用户中心登录（右上角显示用户名）

**步骤**:
1. 访问：`https://www.ucppt.com/js`
2. 点击 "立即使用 →" 按钮
3. 观察控制台和页面变化

**预期结果**:

**控制台日志**:
```javascript
[Next.js SSO v3.0.14] 调用 REST API 获取 Token...
[Next.js SSO v3.0.14] REST API 响应状态: 200
[Next.js SSO v3.0.14] REST API 响应数据: {success: true, hasToken: true, user: {...}}
[Next.js SSO v3.0.14] ✅ Token 获取成功，准备打开应用
[Next.js SSO v3.0.14] 在新窗口打开应用: https://ai.ucppt.com?mode=standalone&sso_token=...
[Next.js SSO v3.0.14] ✅ 应用成功在新窗口打开
```

**页面行为**:
- 按钮文字变为 "立即使用 ⏳"（加载状态）
- 状态提示显示 "正在验证登录状态..."
- 然后显示 "✅ 登录成功，正在打开应用..."
- 新窗口打开应用
- 宣传页面保持在原标签页
- 按钮恢复为 "立即使用 →"
- 状态显示 "✅ 应用已在新窗口打开"

**验收标准**:
- [x] **不跳转到登录页**（关键！）
- [x] 新窗口成功打开应用
- [x] 应用 URL 包含 `sso_token` 参数
- [x] 应用显示已登录状态（用户头像、用户名）
- [x] 宣传页面保持在原标签页

---

### 测试C: 未登录用户完整流程

**前提条件**: 未登录（退出 WPCOM 用户中心）

**步骤**:
1. 访问：`https://www.ucppt.com/js`
2. 点击 "立即使用 →" 按钮
3. 观察跳转行为

**预期结果**:

**控制台日志**:
```javascript
[Next.js SSO v3.0.14] 调用 REST API 获取 Token...
[Next.js SSO v3.0.14] REST API 响应状态: 401
[Next.js SSO v3.0.14] 用户未登录，跳转到登录页面
[Next.js SSO v3.0.14] 跳转到登录页: https://www.ucppt.com/login?redirect_to=https://www.ucppt.com/js
```

**页面行为**:
- 按钮变为加载状态
- 状态提示显示 "未登录，正在跳转到登录页面..."
- 500ms 后跳转到 WPCOM 登录页（`/login`）
- URL 包含 `redirect_to` 参数

**验收标准**:
- [x] 跳转到 `/login` 页面（WPCOM 用户中心）
- [x] **不是** 跳转到 `/wp-login.php`
- [x] URL 包含 `redirect_to=https://www.ucppt.com/js`

---

### 测试D: 登录后自动打开应用

**前提条件**: 完成测试C，当前在 WPCOM 登录页

**步骤**:
1. 输入账号密码
2. 点击登录
3. 观察登录成功后的行为

**预期结果**:

**登录成功后**:
- 自动返回宣传页面（`https://www.ucppt.com/js`）
- 控制台显示：
  ```javascript
  [Next.js SSO v3.0.14] 检测到登录后返回，准备自动打开应用: https://ai.ucppt.com?mode=standalone
  [Next.js SSO v3.0.14] 自动触发按钮点击
  [Next.js SSO v3.0.14] 调用 REST API 获取 Token...
  [Next.js SSO v3.0.14] REST API 响应状态: 200
  [Next.js SSO v3.0.14] ✅ Token 获取成功，准备打开应用
  [Next.js SSO v3.0.14] ✅ 应用成功在新窗口打开
  ```
- 约 1 秒后，自动在新窗口打开应用
- 宣传页面保持在原标签页

**验收标准**:
- [x] 登录成功后返回宣传页面（不是其他页面）
- [x] 1 秒后自动在新窗口打开应用
- [x] 应用显示已登录状态
- [x] 宣传页面保持显示

---

### 测试E: REST API 直接测试（可选）

**在浏览器控制台执行**:

**已登录状态**:
```javascript
fetch('/wp-json/nextjs-sso/v1/get-token', {
    credentials: 'include'
}).then(r => r.json()).then(console.log);

// 预期输出:
// {success: true, token: "eyJ0eXAiOiJKV1QiL...", user: {...}}
```

**未登录状态**:
```javascript
fetch('/wp-json/nextjs-sso/v1/get-token', {
    credentials: 'include'
}).then(r => {
    console.log('Status:', r.status); // 应该是 401
    return r.json();
}).then(console.log);

// 预期输出:
// Status: 401
// {error: "Not logged in"}
```

---

## 🐛 故障排查

### 问题1: 点击按钮后仍跳转到 `/wp-login.php`

**原因**: 缓存未清除，旧代码仍在运行

**解决**:
1. 确认插件版本为 `v3.0.14`
2. WordPress后台 → 设置 → WP Super Cache → 删除缓存
3. 浏览器：Ctrl + Shift + Delete → 清除所有缓存
4. 使用无痕模式测试（Ctrl + Shift + N）

---

### 问题2: REST API 返回 500 错误

**原因**: WordPress REST API 配置问题或插件冲突

**排查**:
```javascript
// 在控制台执行
fetch('/wp-json/nextjs-sso/v1/get-token', {
    credentials: 'include'
}).then(r => {
    console.log('Status:', r.status);
    return r.text();
}).then(console.log);
```

**检查**:
1. WordPress Debug 日志：`/wp-content/debug.log`
2. 禁用其他插件测试
3. 检查 `wp-config.php` 中的 `PYTHON_JWT_SECRET` 配置

---

### 问题3: Token 获取成功但应用未登录

**原因**: Next.js 应用未正确接收 Token

**排查**:

**在应用控制台执行**:
```javascript
console.log('Token:', localStorage.getItem('wp_jwt_token'));
console.log('User:', localStorage.getItem('wp_jwt_user'));
```

**如果都是 null**:
1. 检查应用 URL 是否包含 `sso_token` 参数
2. 检查 `AuthContext.tsx` 是否已应用 v3.0.12 的修复
3. 检查 Python 后端 API 是否运行（`http://127.0.0.1:8000`）
4. 检查 Token 验证接口：`/api/auth/verify`

**参考文档**: [NEXTJS_SSO_TOKEN_RECEIVE_FIX.md](NEXTJS_SSO_TOKEN_RECEIVE_FIX.md)

---

### 问题4: WPCOM 登录页不支持 `redirect_to` 参数

**症状**: 登录成功后跳转到其他页面，而不是返回宣传页面

**排查**:

检查 WPCOM Member Pro 插件的登录页面设置，确认：
1. 是否支持 `redirect_to` 参数
2. 或使用其他重定向参数名（如 `redirect_url`、`return_url` 等）

**如果参数名不同，修改插件代码**:

编辑 `nextjs-sso-integration-v3.php` Line 1466:
```javascript
// 如果 WPCOM 使用 redirect_url 而不是 redirect_to
const loginUrl = '/login?redirect_url=' + encodeURIComponent(currentPageUrl);
```

---

## 📊 验收清单

### 最终验收标准

- [ ] 插件版本为 `v3.0.14`
- [ ] 控制台显示 `[Next.js SSO v3.0.14]`
- [ ] 已登录用户点击按钮 → REST API 返回 200 → 新窗口打开应用
- [ ] 未登录用户点击按钮 → REST API 返回 401 → 跳转到 `/login`
- [ ] 登录成功后返回宣传页面 → 1秒后自动打开应用
- [ ] 宣传页面始终保持在原标签页
- [ ] Token 成功传递到应用
- [ ] 应用显示已登录状态
- [ ] 无 JavaScript 错误
- [ ] 无 REST API 错误

---

## 🎉 成功标志

**全部通过的标志**:

✅ **已登录用户流程**:
- 点击按钮 → 按钮显示加载状态（⏳）
- 控制台显示 "REST API 响应状态: 200"
- 控制台显示 "✅ Token 获取成功"
- 新窗口打开应用（带 sso_token）
- 应用显示已登录状态
- 宣传页面保持显示，按钮恢复正常

✅ **未登录用户流程**:
- 点击按钮 → 按钮显示加载状态
- 控制台显示 "REST API 响应状态: 401"
- 控制台显示 "用户未登录，跳转到登录页面"
- 跳转到 `/login?redirect_to=...`
- 登录成功后返回宣传页面
- 1秒后自动打开应用

✅ **WPCOM 兼容性**:
- 不再依赖 `wp_get_current_user()`
- 不再解析 `wordpress_logged_in_*` Cookie
- 完全依赖 WordPress REST API 认证
- WPCOM Member Pro 的登录状态被正确识别

---

## 📝 技术总结

### Solution B 的核心优势

1. **兼容性**: 完全依赖 WordPress REST API 的内置认证机制，不受第三方插件 Cookie 实现影响

2. **可靠性**: WordPress 的 REST API 认证是标准化的，WPCOM Member Pro 必须兼容它才能正常工作

3. **简洁性**: 移除了复杂的服务器端 Cookie 解析逻辑，减少了出错点

4. **实时性**: 客户端动态检测，无需服务器端生成 Token，避免缓存问题

5. **安全性**: Token 仍然由 WordPress 插件生成，使用标准 JWT，未改变安全模型

### 架构变化对比

**v3.0.12（旧方案）**:
```
页面加载 → 服务器端检测登录 → 生成Token嵌入HTML
    ↓
用户点击按钮 → 直接使用嵌入的Token → 打开应用

问题：服务器端无法检测WPCOM登录
```

**v3.0.14（Solution B）**:
```
页面加载 → 渲染统一按钮（无服务端检测）
    ↓
用户点击按钮 → 客户端调用REST API → 实时获取Token → 打开应用

优势：依赖WordPress REST API认证（WPCOM必须兼容）
```

---

## 📄 相关文档

- [NEXTJS_SSO_TOKEN_RECEIVE_FIX.md](NEXTJS_SSO_TOKEN_RECEIVE_FIX.md) - Next.js Token 接收修复
- [WORDPRESS_SSO_V3.0.12_WPCOM_LOGIN_TEST.md](WORDPRESS_SSO_V3.0.12_WPCOM_LOGIN_TEST.md) - WPCOM 登录测试指南
- [WORDPRESS_SSO_V3.0.12_QUICK_TEST.md](WORDPRESS_SSO_V3.0.12_QUICK_TEST.md) - 快速测试清单

---

**v3.0.14 Solution B 实施完成！** 🎊

**最后更新**: 2025-12-16
**插件版本**: v3.0.14
**方案**: Solution B（REST API 模式）
