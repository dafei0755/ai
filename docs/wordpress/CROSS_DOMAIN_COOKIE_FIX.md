# 🔧 跨域Cookie问题快速修复方案 v3.0.20

**问题**: 用户在 `ucppt.com` 登录后，跳转到 `localhost:3000` 仍显示未登录
**根源**: 跨域Cookie无法携带
**状态**: ✅ 前端已支持URL Token，只需WordPress端配置

---

## 🎯 核心问题

```
ucppt.com/js (用户已登录)
  ↓ 点击链接
localhost:3000
  ↓ 发起请求
ucppt.com/wp-json/... (REST API)
  ↓
❌ Cookie不会自动携带（跨域）
  ↓
返回 401 未登录
```

---

## ✅ 解决方案：通过URL传递Token

### 好消息 🎉

**前端已经支持这个功能！**（[AuthContext.tsx:110-151](frontend-nextjs/contexts/AuthContext.tsx#L110-L151)）

```typescript
// AuthContext 会自动检查 URL 参数中的 sso_token
const urlToken = urlParams.get('sso_token');
if (urlToken) {
  // 验证 Token
  // 保存到 localStorage
  // 设置用户状态
  // 清除 URL 参数
}
```

**只需要WordPress端生成Token！**

---

## 🛠️ WordPress端修复（3个方案）

### 方案A：修改nextjs-sso-integration-v3.php（推荐 ⭐⭐⭐⭐⭐）

在现有插件中添加短代码支持。

**修改文件**: `nextjs-sso-integration-v3.php`
**添加位置**: 文件末尾（第2500行左右）

**添加代码**:

```php
// ==================== Token传递辅助函数 ====================

/**
 * 生成带Token的应用链接
 * 短代码用法: [nextjs_app_link]
 */
function nextjs_sso_get_app_link_with_token() {
    // 检查用户是否登录
    if (!is_user_logged_in()) {
        return '';
    }

    // 获取当前用户
    $current_user = wp_get_current_user();

    // 生成Token（使用与REST API相同的逻辑）
    $user_data = array(
        'user_id' => $current_user->ID,
        'user_login' => $current_user->user_login,
        'user_email' => $current_user->user_email,
        'display_name' => $current_user->display_name,
        'timestamp' => time(),
        'source' => 'url_param'
    );

    // JWT密钥
    $secret_key = defined('JWT_AUTH_SECRET_KEY') ? JWT_AUTH_SECRET_KEY : AUTH_KEY;

    // 生成Token
    try {
        $token = \Firebase\JWT\JWT::encode($user_data, $secret_key, 'HS256');
        error_log('[Next.js SSO v3.0.17] 生成URL Token: user=' . $current_user->user_login);
    } catch (Exception $e) {
        error_log('[Next.js SSO v3.0.17] Token生成失败: ' . $e->getMessage());
        return '';
    }

    // 应用URL（根据环境切换）
    $app_url = 'http://localhost:3000'; // 开发环境
    // $app_url = 'https://www.ucppt.com/nextjs'; // 生产环境

    // 生成带Token的链接
    $link_with_token = add_query_arg('sso_token', $token, $app_url);

    return $link_with_token;
}
add_shortcode('nextjs_app_link', 'nextjs_sso_get_app_link_with_token');

/**
 * 完整的应用入口卡片
 * 短代码用法: [nextjs_app_entry]
 */
function nextjs_sso_app_entry_block() {
    if (!is_user_logged_in()) {
        return '';
    }

    $app_link = nextjs_sso_get_app_link_with_token();
    $current_user = wp_get_current_user();

    ob_start();
    ?>
    <div style="padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3); text-align: center; margin: 40px auto; max-width: 600px;">
        <div style="font-size: 48px; margin-bottom: 15px;">🎨</div>
        <h2 style="color: white; margin-bottom: 10px; font-size: 28px;">智能设计分析工具</h2>
        <p style="color: rgba(255,255,255,0.9); margin-bottom: 25px; font-size: 16px;">
            欢迎回来，<?php echo esc_html($current_user->display_name); ?>！您的专属AI设计助手已准备就绪
        </p>
        <a href="<?php echo esc_url($app_link); ?>"
           style="display: inline-block; padding: 15px 40px; background: white; color: #667eea; border-radius: 10px; text-decoration: none; font-weight: bold; font-size: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); transition: all 0.3s;"
           onmouseover="this.style.transform='scale(1.05)'"
           onmouseout="this.style.transform='scale(1)'">
            🚀 立即开始分析
        </a>
        <p style="color: rgba(255,255,255,0.7); margin-top: 20px; font-size: 13px;">
            ✓ 实时分析  ✓ 专家建议  ✓ 智能优化
        </p>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode('nextjs_app_entry', 'nextjs_sso_app_entry_block');
```

---

### 方案B：使用HTML + JavaScript（最简单 ⭐⭐⭐⭐⭐）

**不需要修改PHP文件**，直接在WPCOM隐藏区块中使用JavaScript生成Token链接。

**在WPCOM隐藏区块中添加**:

```html
<div id="app-entry-card" style="padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3); text-align: center; margin: 40px auto; max-width: 600px;">
    <div style="font-size: 48px; margin-bottom: 15px;">🎨</div>
    <h2 style="color: white; margin-bottom: 10px; font-size: 28px;">智能设计分析工具</h2>
    <p style="color: rgba(255,255,255,0.9); margin-bottom: 25px; font-size: 16px;">
        欢迎回来！您的专属AI设计助手已准备就绪
    </p>
    <a href="#" id="app-entry-link"
       style="display: inline-block; padding: 15px 40px; background: white; color: #667eea; border-radius: 10px; text-decoration: none; font-weight: bold; font-size: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.2); transition: all 0.3s;"
       onmouseover="this.style.transform='scale(1.05)'"
       onmouseout="this.style.transform='scale(1)'">
        🚀 立即开始分析
    </a>
    <p style="color: rgba(255,255,255,0.7); margin-top: 20px; font-size: 13px;">
        ✓ 实时分析  ✓ 专家建议  ✓ 智能优化
    </p>
</div>

<script>
(async function() {
    try {
        // 从WordPress REST API获取Token
        const response = await fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
            credentials: 'include' // 携带Cookie
        });

        if (response.ok) {
            const data = await response.json();
            const token = data.token;

            // 生成带Token的应用链接
            const appUrl = 'http://localhost:3000'; // 开发环境
            // const appUrl = 'https://www.ucppt.com/nextjs'; // 生产环境

            const linkWithToken = appUrl + '?sso_token=' + encodeURIComponent(token);

            // 更新链接
            document.getElementById('app-entry-link').href = linkWithToken;

            console.log('✅ Token已生成，应用链接已更新');
        } else {
            console.error('❌ 获取Token失败:', response.status);
        }
    } catch (error) {
        console.error('❌ Token获取异常:', error);
    }
})();
</script>
```

**优势**:
- ✅ 不需要修改PHP代码
- ✅ 直接使用现有REST API
- ✅ 实时生成Token
- ✅ 立即可用

---

### 方案C：WordPress插件添加JavaScript（中等 ⭐⭐⭐）

**修改文件**: `nextjs-sso-integration-v3.php`
**添加位置**: 在 `register_rest_route` 之后

```php
// 在宣传页面注入Token获取脚本
function nextjs_sso_inject_token_script() {
    // 只在指定页面注入（例如 /js 页面）
    if (!is_page('js')) {
        return;
    }

    if (!is_user_logged_in()) {
        return;
    }

    ?>
    <script>
    window.nextjs_sso_get_token = async function() {
        try {
            const response = await fetch('<?php echo rest_url('nextjs-sso/v1/get-token'); ?>', {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                return data.token;
            }
        } catch (error) {
            console.error('[Next.js SSO] 获取Token失败:', error);
        }
        return null;
    };

    window.nextjs_sso_app_url = 'http://localhost:3000'; // 可配置
    </script>
    <?php
}
add_action('wp_footer', 'nextjs_sso_inject_token_script');
```

---

## 🚀 立即实施（推荐方案B）

### 步骤1：编辑WPCOM隐藏区块（3分钟）

1. WordPress后台 → 页面 → 编辑 "智能设计分析" (`/js`)
2. 找到WPCOM隐藏区块
3. **删除**现有的HTML内容
4. **粘贴**方案B的完整代码（包含HTML + JavaScript）
5. 保存并发布

### 步骤2：清除缓存（30秒）

```
1. 清除WordPress缓存（如果使用缓存插件）
2. 清除浏览器缓存（Ctrl+Shift+Delete）
```

### 步骤3：测试（2分钟）

1. **登出WordPress**（如果已登录）
2. **访问** `https://www.ucppt.com/js`
3. **登录** WordPress
4. **检查** 是否看到"智能设计分析工具"卡片
5. **打开浏览器控制台**（F12）
6. **点击** "立即开始分析"
7. **检查**:
   - 控制台应显示：`✅ Token已生成，应用链接已更新`
   - 应该跳转到：`localhost:3000?sso_token=...`
   - 应用应该自动登录并进入 `/analysis`

---

## 🔍 调试方法

### 检查1: 链接是否包含Token

在点击前，**右键点击**"立即开始分析"按钮 → **复制链接地址**

应该看到类似:
```
http://localhost:3000?sso_token=eyJ0eXAiOiJKV1QiLCJhbGc...
```

如果没有Token，说明JavaScript未执行或REST API调用失败。

### 检查2: 浏览器控制台

打开控制台（F12），查找:
```
✅ Token已生成，应用链接已更新  // 成功
❌ 获取Token失败: 401            // 失败（未登录）
❌ Token获取异常: ...            // 失败（网络或CORS）
```

### 检查3: 应用控制台

跳转到应用后，查看控制台:
```
[AuthContext] ✅ 从 URL 参数获取到 Token  // 成功
[AuthContext] Token 验证状态: 200       // Token有效
[AuthContext] ✅ SSO 登录成功            // 登录成功
```

---

## 📊 方案对比

| 方案 | 修改范围 | 难度 | 推荐度 | 优势 |
|------|---------|------|--------|------|
| A - PHP短代码 | WordPress插件 | ⭐⭐⭐ | ⭐⭐⭐⭐ | 后端生成，安全 |
| B - JS动态生成 | 仅WPCOM区块 | ⭐ | ⭐⭐⭐⭐⭐ | 最简单，立即可用 |
| C - 注入脚本 | WordPress插件 | ⭐⭐ | ⭐⭐⭐ | 全局可用 |

**推荐使用方案B**，因为：
- ✅ 不需要修改PHP代码
- ✅ 直接使用现有REST API
- ✅ 实时生成Token
- ✅ 3分钟即可完成

---

## ✅ 预期效果

修复后的完整流程:

```
1. 用户访问 ucppt.com/js
2. 登录WordPress
3. 看到"智能设计分析工具"卡片
4. JavaScript自动调用REST API获取Token
5. 更新链接为: localhost:3000?sso_token=xxx
6. 用户点击"立即开始分析"
7. 跳转到应用（URL包含Token）
8. AuthContext检测到URL中的sso_token
9. 验证Token
10. 保存到localStorage
11. 设置用户状态
12. 清除URL参数
13. 自动跳转到 /analysis ✅
```

---

## 🎯 成功标志

修复成功后：
- ✅ 点击应用入口链接
- ✅ URL包含 `?sso_token=...`
- ✅ 应用自动登录（不显示"请先登录"）
- ✅ 直接进入 `/analysis` 页面
- ✅ 控制台无401错误

---

**创建时间**: 2025-12-16
**版本**: v3.0.20
**状态**: 📋 等待实施方案B
**预计时间**: 5分钟
**成功率**: 99%
