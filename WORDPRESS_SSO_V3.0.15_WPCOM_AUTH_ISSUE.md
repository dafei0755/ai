# WordPress SSO v3.0.15 - WPCOM 认证问题诊断

## 🔍 问题现象

**症状：**
- 用户在 `ucppt.com/account` 已登录（显示"宋词"，超级会员）
- 但访问 `localhost:3000` 时，WordPress REST API返回401
- 应用仍显示"请先登录"界面

**控制台日志：**
```
[AuthContext] 尝试通过 WordPress REST API 获取 Token...
❌ Failed to load resource: www.ucppt.com/wp-json/nextjs-sso/v1/get-token 401
[AuthContext] WordPress 未登录，将显示登录界面
```

---

## 🎯 根本原因分析

### 原因：WPCOM Member Pro 使用自定义认证系统

WPCOM Member Pro可能：
1. **不使用标准WordPress Cookie** (`wordpress_logged_in_*`)
2. **使用自己的Session/Token机制**
3. **Cookie的作用域限制** 导致跨域请求不带Cookie

---

## 🔧 诊断步骤

###步骤1: 检查浏览器Cookie

在 `ucppt.com/account` 页面：

1. 按 `F12` → Application/存储 → Cookies → `https://www.ucppt.com`
2. 查找以下Cookie：
   - `wordpress_logged_in_*` ← 标准WordPress登录Cookie
   - `wpcom_*` ← WPCOM自定义Cookie
   - `wp_*` ← 其他WordPress Cookie

**关键问题：**
- 如果**没有** `wordpress_logged_in_*` Cookie，说明WPCOM不使用标准认证
- 如果Cookie的**Domain**不是`.ucppt.com`，可能无法跨子域共享

### 步骤2: 测试WordPress标准登录

尝试使用WordPress标准登录：

1. 访问: `https://www.ucppt.com/wp-login.php`
2. 使用WordPress管理员账号登录（非WPCOM登录）
3. 登录后访问: `http://localhost:3000`
4. 观察是否能自动跳转

**如果标准登录可以工作：**
→ 证实问题在于WPCOM的认证兼容性

### 步骤3: 查看WordPress错误日志

在WordPress站点查看日志：

```bash
# WordPress调试日志通常在：
/wp-content/debug.log
```

查找以下日志：
```
[Next.js SSO v3.0.12] ✅ 通过 wp_get_current_user 获取到用户: xxx
[Next.js SSO v3.0.12] 🔍 尝试通过 Cookie 获取用户: xxx
[Next.js SSO v3.0] 所有权限检查失败
```

---

## 💡 解决方案

### 方案A: 修改WordPress插件以支持WPCOM认证（推荐）

需要修改 `nextjs_sso_v3_get_user_from_cookie()` 函数，添加WPCOM认证支持。

**实施步骤：**
1. 确定WPCOM Member Pro使用的Cookie名称/认证方式
2. 修改插件代码添加对应的检测逻辑
3. 重新测试

### 方案B: 使用WordPress标准登录系统

如果WPCOM Member Pro与WordPress REST API不兼容：

**临时方案：**
- 用户使用 `/wp-login.php` 登录
- 或使用WordPress标准会员插件

**长期方案：**
- 联系WPCOM Member Pro插件作者
- 请求添加标准WordPress认证支持

### 方案C: 直接在WPCOM插件中添加自定义端点

创建一个WPCOM专用的REST API端点：

```php
// 在WPCOM Member Pro中添加
add_action('rest_api_init', function() {
    register_rest_route('wpcom/v1', '/get-token', array(
        'methods' => 'GET',
        'callback' => function() {
            // 使用WPCOM的认证方式获取当前用户
            $user = wpcom_get_current_user(); // WPCOM的方法
            if ($user) {
                // 调用Next.js SSO插件生成Token
                $token = nextjs_sso_v3_generate_jwt_token($user);
                return array('success' => true, 'token' => $token, 'user' => $user);
            }
            return new WP_Error('not_logged_in', '未登录', array('status' => 401));
        }
    ));
});
```

然后修改Next.js AuthContext调用这个新端点。

---

## 🧪 临时测试方案（验证架构正确性）

### 使用Token URL参数测试（绕过Cookie问题）

1. **手动获取Token：**

   在 `ucppt.com/account` 控制台执行：
   ```javascript
   fetch('https://www.ucppt.com/wp-admin/admin-ajax.php?action=nextjs_sso_generate_token')
       .then(r => r.json())
       .then(data => {
           console.log('Token:', data.token);
           // 复制Token
       });
   ```

2. **使用Token访问应用：**
   ```
   http://localhost:3000?token=YOUR_TOKEN_HERE
   ```

3. **验证自动跳转：**
   如果应用能自动跳转到 `/analysis`，说明v3.0.15的逻辑是正确的，只是Cookie认证有问题。

---

## 📊 诊断清单

请检查以下项目并反馈结果：

- [ ] 浏览器Cookie中是否有 `wordpress_logged_in_*`
- [ ] WPCOM Member Pro使用什么Cookie名称
- [ ] Cookie的Domain是什么（`.ucppt.com` vs `ucppt.com`）
- [ ] 使用 `/wp-login.php` 标准登录能否工作
- [ ] WordPress `debug.log` 中有什么错误信息
- [ ] WPCOM Member Pro是否有API文档说明认证方式

---

## 🎯 下一步行动

**最快验证方法：**
1. 尝试使用 `https://www.ucppt.com/wp-login.php` 登录
2. 看标准WordPress登录能否让REST API返回200

**长期解决方案：**
- 需要了解WPCOM Member Pro的认证机制
- 修改WordPress插件添加WPCOM支持

---

**创建时间：** 2025-12-16
**问题状态：** 待确认WPCOM认证方式
**影响范围：** v3.0.15核心功能（自动登录检测）
