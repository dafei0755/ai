# WordPress SSO v3.0.12 - WPCOM登录修复测试指南

## 🐛 问题描述（用户反馈）

1. **已登录状态下点击按钮仍跳转到登录页**
   - 页面右上角显示已登录
   - 点击"立即使用"按钮后，却进入登录页面
   - 预期：直接在新窗口打开应用

2. **登录方式错误**
   - 跳转到WordPress标准登录页（`/wp-login.php`）
   - 应该跳转到WPCOM用户中心登录页（`/login`）

3. **需要使用WPCOM用户中心高级版登录**
   - 不是WordPress后台账号登录
   - 需要WPCOM Member Pro插件的用户登录

---

## 🔧 修复内容

### 修复1: 更改登录URL (Line 1456)

**修改前**：
```javascript
const loginUrl = '<?php echo esc_js(wp_login_url()); ?>?redirect_to=' + encodeURIComponent(currentPageUrl);
// 跳转到: /wp-login.php?redirect_to=...
```

**修改后**：
```javascript
const loginUrl = '<?php echo esc_js(home_url('/login')); ?>?redirect_to=' + encodeURIComponent(currentPageUrl);
// 跳转到: /login?redirect_to=...
```

**作用**：
- 使用WPCOM用户中心登录页（`/login`）
- 而不是WordPress标准登录页（`/wp-login.php`）
- 登录后使用 `redirect_to` 参数返回宣传页面

### 修复2: 添加详细的登录状态调试日志 (Lines 1403-1408)

```javascript
console.log('[Next.js SSO v3.0.12] 服务器端登录状态: <?php echo $is_logged_in ? "已登录" : "未登录"; ?>');
<?php if ($is_logged_in): ?>
console.log('[Next.js SSO v3.0.12] 当前用户: <?php echo esc_js($current_user->user_login); ?> (ID: <?php echo $current_user->ID; ?>)');
console.log('[Next.js SSO v3.0.12] Token已生成: <?php echo !empty($token) ? "是" : "否"; ?>');
<?php endif; ?>
```

**作用**：
- 在浏览器控制台显示服务器端检测到的登录状态
- 显示当前用户名和ID（如果已登录）
- 显示Token是否成功生成
- 帮助快速诊断登录状态误判问题

---

## 📦 部署文件

**文件名**: `nextjs-sso-integration-v3.0.12-final.zip`
**大小**: 16,981 bytes (17 KB)
**版本**: v3.0.12 (WPCOM登录修复版)
**发布时间**: 2025-12-16 09:06

---

## 🚀 快速部署（2分钟）

### 步骤1: 上传插件

```bash
WordPress后台 → 插件 → 已安装的插件
找到 "Next.js SSO Integration v3" → 停用

插件 → 安装插件 → 上传插件
选择: nextjs-sso-integration-v3.0.12-final.zip
安装 → 启用插件
```

### 步骤2: 清除所有缓存

```bash
# WordPress缓存
设置 → WP Super Cache → 删除缓存

# 浏览器缓存
Ctrl + Shift + Delete → 清除缓存
或 Ctrl + Shift + R（强制刷新）
```

### 步骤3: 测试验证

按照下面的"测试清单"执行完整测试。

---

## ✅ 测试清单（必须全部通过）

### 测试A: 控制台登录状态检测

**前提条件**：
- 确保已在WPCOM用户中心登录
- WordPress右上角显示用户头像和用户名

**操作步骤**：
1. 访问：`https://www.ucppt.com/js`
2. 按 `F12` 打开浏览器控制台
3. 切换到 `Console` 标签
4. 查看日志输出

**预期结果**：
```javascript
[Next.js SSO v3.0.12] 宣传页面脚本已加载
[Next.js SSO v3.0.12] 服务器端登录状态: 已登录
[Next.js SSO v3.0.12] 当前用户: your_username (ID: 123)
[Next.js SSO v3.0.12] Token已生成: 是
[Next.js SSO v3.0.12] 已找到已登录用户按钮
[Next.js SSO v3.0.12] app_url: https://ai.ucppt.com?mode=standalone
```

**验收标准**：
- [x] 显示 "服务器端登录状态: 已登录"
- [x] 显示 "当前用户: xxx (ID: xxx)"
- [x] 显示 "Token已生成: 是"
- [x] 显示 "已找到已登录用户按钮"
- [x] **没有** 显示 "已找到未登录用户按钮"

**如果显示 "服务器端登录状态: 未登录"**：
- ❌ **失败** - 服务器端未检测到登录状态
- 可能原因：
  1. WPCOM用户中心的登录Cookie未被WordPress识别
  2. Cookie作用域问题
  3. Session未正确建立
- 继续下一步诊断

---

### 测试B: 页面UI状态检查

**操作步骤**：
1. 访问：`https://www.ucppt.com/js`
2. 查看页面显示的登录状态文字

**预期结果**：
- 按钮下方显示：
  ```
  ✓ 您已登录为 [用户名]，点击按钮直接进入应用
  ```

**验收标准**：
- [x] 显示 "✓ 您已登录为..."
- [x] **不显示** "请先登录以使用应用"
- [x] 用户名与控制台日志中的一致

**如果显示 "请先登录以使用应用"**：
- ❌ **失败** - 服务器端判断为未登录状态
- 问题根源：`nextjs_sso_v3_get_user_from_cookie()` 函数未能获取到用户
- 需要排查WPCOM用户中心的登录机制

---

### 测试C: 已登录用户点击按钮（关键测试）

**前提条件**：
- 测试A和测试B都显示已登录状态

**操作步骤**：
1. 访问：`https://www.ucppt.com/js`
2. 点击 "立即使用 →" 按钮
3. 观察浏览器行为

**预期结果**：
- **立即在新标签页打开应用**（不是跳转到登录页）
- 控制台显示：
  ```javascript
  [Next.js SSO v3.0.12] 在新窗口打开应用: https://ai.ucppt.com?mode=standalone&sso_token=...
  ```
- 宣传页面保持在原标签页
- 应用显示已登录状态

**验收标准**：
- [x] **没有** 跳转到登录页
- [x] 新窗口打开应用
- [x] 应用URL包含 `sso_token` 参数
- [x] 应用显示已登录状态（用户头像、用户名）

**如果仍然跳转到登录页**：
- ❌ **严重错误** - 登录状态检测失败
- 检查控制台日志是否显示 "已登录"
- 如果日志显示 "未登录"，说明WPCOM登录Cookie未被识别

---

### 测试D: 未登录用户跳转到WPCOM登录页

**前提条件**：
- 退出WPCOM用户中心登录
- 确保完全未登录状态

**操作步骤**：
1. WPCOM用户中心退出登录
2. 访问：`https://www.ucppt.com/js`
3. 点击 "立即使用 →" 按钮
4. 观察跳转的URL

**预期结果**：
- 跳转到：`https://www.ucppt.com/login?redirect_to=https://www.ucppt.com/js`
- **不是** 跳转到：`/wp-login.php`
- 控制台显示：
  ```javascript
  [Next.js SSO v3.0.12] 服务器端登录状态: 未登录
  [Next.js SSO v3.0.12] 已找到未登录用户按钮
  [Next.js SSO v3.0.12] 跳转到WPCOM登录页: https://www.ucppt.com/login?redirect_to=...
  ```

**验收标准**：
- [x] 跳转到 `/login` 页面（WPCOM用户中心）
- [x] **不是** 跳转到 `/wp-login.php`（WordPress标准登录）
- [x] URL包含 `redirect_to` 参数，值为宣传页面URL
- [x] 控制台显示 "跳转到WPCOM登录页"

**如果跳转到 `/wp-login.php`**：
- ❌ **失败** - 旧代码仍在运行，缓存未清除
- 解决：清除所有缓存，强制刷新

---

### 测试E: WPCOM用户中心登录后自动跳转

**前提条件**：
- 测试D已通过（跳转到WPCOM登录页）

**操作步骤**：
1. 在WPCOM登录页面输入账号密码
2. 点击登录按钮
3. 观察登录成功后的跳转

**预期结果**：
- 登录成功后自动返回宣传页面（`https://www.ucppt.com/js`）
- 宣传页面显示：
  ```
  ✓ 您已登录为 [用户名]，点击按钮直接进入应用
  ```
- 约1秒后，自动在新窗口打开应用
- 宣传页面保持在原标签页

**验收标准**：
- [x] 登录成功后返回宣传页面（不是跳转到其他页面）
- [x] 宣传页面显示已登录状态
- [x] 1秒后自动在新窗口打开应用
- [x] 应用显示已登录状态

---

### 测试F: Token传递验证

**前提条件**：
- 测试C或测试E已通过（应用已在新窗口打开）

**操作步骤**：
1. 在应用标签页按 `F12` 打开控制台
2. 执行以下命令：
   ```javascript
   console.log('Token:', localStorage.getItem('wp_jwt_token'));
   console.log('User:', localStorage.getItem('wp_jwt_user'));
   ```

**预期结果**：
```javascript
Token: eyJ0eXAiOiJKV1QiLCJhbGc...（长字符串）
User: {"user_id":123,"username":"xxx",...}
```

**验收标准**：
- [x] Token有值（不是null）
- [x] User有值（包含用户信息的JSON）
- [x] Token格式正确（JWT格式，三段式，用.分隔）
- [x] User包含必要字段（user_id, username, email等）

---

### 测试G: 多次打开应用

**操作步骤**：
1. 以已登录状态访问宣传页面
2. 点击 "立即使用" 按钮（第1次）
3. 等待应用打开后，返回宣传页面标签页
4. 再次点击 "立即使用" 按钮（第2次）
5. 再次点击（第3次）

**预期结果**：
- 每次点击都在新标签页打开应用
- 可以同时打开多个应用标签页
- 宣传页面始终保持在原标签页

**验收标准**：
- [x] 可以多次点击按钮
- [x] 每次都在新窗口打开
- [x] 宣传页面不会消失
- [x] 每个应用标签页都有Token

---

## 🐛 问题诊断

### 问题1: 控制台显示 "服务器端登录状态: 未登录"，但右上角显示已登录

**症状**：
- WordPress右上角显示用户头像和用户名
- 控制台日志显示 "未登录"
- 点击按钮跳转到登录页

**原因**：
- WPCOM用户中心的登录Cookie未被 `nextjs_sso_v3_get_user_from_cookie()` 函数识别
- 可能WPCOM使用自定义的登录机制，不是标准WordPress Cookie

**排查步骤**：

#### 1. 检查Cookie名称

在宣传页面（`https://www.ucppt.com/js`）的控制台执行：

```javascript
console.log('所有Cookies:', document.cookie.split('; ').filter(c => c.includes('logged') || c.includes('user') || c.includes('login') || c.includes('wordpress')));
```

**寻找**：
- `wordpress_logged_in_*` - 标准WordPress登录Cookie
- `wpcom_*` - WPCOM自定义Cookie
- 其他可能的登录标识Cookie

#### 2. 检查WordPress用户状态

在WordPress后台（或任何WordPress页面）的浏览器控制台执行：

```javascript
fetch('/wp-json/nextjs-sso/v1/check-login', {
    credentials: 'include'
}).then(r => r.json()).then(console.log);
```

**预期输出**：
```javascript
{
    logged_in: true,
    user_id: 123
}
```

如果返回 `logged_in: false`，说明问题在服务器端。

#### 3. 检查WordPress插件是否获取到用户

在 `nextjs-sso-integration-v3.php` 的 `nextjs_sso_v3_get_user_from_cookie()` 函数中（Line 512），添加更多调试日志：

```php
function nextjs_sso_v3_get_user_from_cookie() {
    error_log('[Next.js SSO v3.0.12 DEBUG] === 开始检测用户登录状态 ===');

    // 方法1: wp_get_current_user
    $current_user = wp_get_current_user();
    error_log('[Next.js SSO v3.0.12 DEBUG] wp_get_current_user: ID=' . ($current_user ? $current_user->ID : 'null'));
    if ($current_user && $current_user->ID > 0) {
        error_log('[Next.js SSO v3.0] 通过 wp_get_current_user 获取到用户: ' . $current_user->user_login);
        return $current_user;
    }

    // 方法2: Cookie解析
    error_log('[Next.js SSO v3.0.12 DEBUG] 开始遍历 Cookies...');
    foreach ($_COOKIE as $cookie_name => $cookie_value) {
        error_log('[Next.js SSO v3.0.12 DEBUG] Cookie: ' . $cookie_name);
        if (strpos($cookie_name, 'wordpress_logged_in_') === 0) {
            error_log('[Next.js SSO v3.0] 尝试通过 Cookie 获取用户: ' . $cookie_name);
            // ... 现有逻辑 ...
        }
    }

    error_log('[Next.js SSO v3.0.12 DEBUG] 所有方式都无法获取用户');
    error_log('[Next.js SSO v3.0.12 DEBUG] === 登录状态检测结束 ===');
    return null;
}
```

然后查看WordPress错误日志：`/wp-content/debug.log`

---

### 问题2: 跳转到 `/wp-login.php` 而不是 `/login`

**症状**：
- 点击按钮后跳转到 `/wp-login.php`
- 控制台日志显示 "跳转到登录页: /wp-login.php?..."

**原因**：
- 缓存问题，旧代码仍在运行

**解决方法**：
```bash
1. 确认插件版本为 v3.0.12
2. WordPress后台 → 设置 → WP Super Cache → 删除缓存
3. 浏览器：Ctrl + Shift + Delete → 清除所有缓存
4. 使用无痕模式测试（Ctrl + Shift + N）
5. 如果仍然失败，清除服务器端缓存（Nginx/CDN）
```

---

### 问题3: WPCOM登录页不接受 `redirect_to` 参数

**症状**：
- 跳转到 `/login` 成功
- 但登录后没有返回宣传页面，而是跳转到其他页面

**原因**：
- WPCOM用户中心可能使用不同的重定向参数名

**排查步骤**：

检查WPCOM用户中心插件的登录页面代码，查找重定向参数名：
- 可能是 `redirect_to`
- 也可能是 `redirect_url`、`return_url`、`callback` 等

**修改方法**（如果参数名不同）：

编辑 `nextjs-sso-integration-v3.php` Line 1456：

```javascript
// 如果WPCOM使用 redirect_url 而不是 redirect_to
const loginUrl = '<?php echo esc_js(home_url('/login')); ?>?redirect_url=' + encodeURIComponent(currentPageUrl);
```

---

## 📝 测试报告模板

复制以下模板，填写测试结果：

```markdown
# WordPress SSO v3.0.12-final 测试报告

**测试日期**: 2025-12-16
**测试环境**: 生产环境 (https://www.ucppt.com)
**测试人员**: [您的名字]

## 测试A: 控制台登录状态检测
- [ ] 通过 / [ ] 失败
- 服务器端登录状态: [已登录/未登录]
- 当前用户: [用户名]
- Token已生成: [是/否]
- 备注:

## 测试B: 页面UI状态检查
- [ ] 通过 / [ ] 失败
- 显示文字: [实际显示的内容]
- 备注:

## 测试C: 已登录用户点击按钮
- [ ] 通过 / [ ] 失败
- 行为: [跳转到登录页 / 新窗口打开应用]
- 控制台日志:
- 备注:

## 测试D: 未登录用户跳转URL
- [ ] 通过 / [ ] 失败
- 跳转URL: [实际跳转的URL]
- 是否为WPCOM登录页: [是/否]
- 备注:

## 测试E: 登录后自动跳转
- [ ] 通过 / [ ] 失败
- 登录后返回页面: [实际返回的URL]
- 是否自动打开应用: [是/否]
- 备注:

## 测试F: Token传递验证
- [ ] 通过 / [ ] 失败
- Token存在: [是/否]
- User存在: [是/否]
- 备注:

## 测试G: 多次打开应用
- [ ] 通过 / [ ] 失败
- 备注:

## 总结
**全部通过**: [是/否]
**失败测试**: [测试编号]
**主要问题**:
**建议**:
```

---

## 🔧 下一步行动

### 如果所有测试通过 ✅
- 标记为生产就绪
- 部署到生产环境
- 监控实际用户反馈

### 如果测试A失败（服务器端未检测到登录）❌
- 重点排查WPCOM用户中心的登录机制
- 可能需要修改 `nextjs_sso_v3_get_user_from_cookie()` 函数
- 添加WPCOM特定的Cookie检测逻辑

### 如果测试D失败（跳转到错误的登录页）❌
- 确认缓存已完全清除
- 确认插件版本为 v3.0.12
- 使用无痕模式重新测试

---

**测试指南最后更新**: 2025-12-16
**对应插件版本**: v3.0.12-final
**插件文件名**: nextjs-sso-integration-v3.0.12-final.zip
