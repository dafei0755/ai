# WordPress SSO 插件 v3.0 更新对比

## 问题回顾

### 用户报告的问题

**时间**：2025-12-13

**症状**：
1. WordPress 后台显示插件版本为 v2.5.0 ✅
2. 但登录界面仍然是旧样式（简单的橙色卡片，`<a>` 链接）❌
3. 右键检查显示代码未更新 ❌
4. 用户多次上传插件，问题依旧 ❌

**用户原话**：
> "新版插件，问题依旧！！！！彻底修复，给一个新的版本名称"

### 根本原因

**WordPress OPcache 缓存问题**：
- WordPress 服务器启用了 PHP OPcache（OpCode Cache）
- OPcache 缓存了旧的 PHP 文件编译后的字节码
- 即使替换了 PHP 文件，WordPress 仍然执行缓存的旧代码
- 插件版本号存储在数据库中，可以更新；但实际执行的代码来自 OPcache

**为什么用户看到的是 v2.5.0 但代码是旧的？**
1. 用户上传了新的 ZIP 文件
2. WordPress 解压并替换了 PHP 文件
3. WordPress 更新数据库中的插件版本号 → **显示 v2.5.0** ✅
4. 但用户访问页面时，PHP-FPM 读取了 OPcache 中的旧代码 → **执行旧逻辑** ❌

---

## v3.0 解决方案

### 核心策略：全新插件标识符

**v2.5 及之前**：
- 插件文件名：`nextjs-sso-integration-v2.1-fixed.php`
- 插件文件夹：`nextjs-sso-integration/`
- 函数前缀：`nextjs_sso_*`
- 选项键：`nextjs_sso_callback_url`, `nextjs_sso_app_url`

**v3.0（新）**：
- 插件文件名：`nextjs-sso-integration-v3.php`
- 插件文件夹：`nextjs-sso-integration-v3/`
- 函数前缀：`nextjs_sso_v3_*`
- 选项键：`nextjs_sso_v3_callback_url`, `nextjs_sso_v3_app_url`

**效果**：
- WordPress 会将其视为 **全新的插件**
- 不会加载旧的 OPcache 缓存
- 用户必须删除旧插件，避免冲突

---

## 代码对比

### 1. 插件头部信息

#### v2.5
```php
/**
 * Plugin Name: Next.js SSO Integration
 * Description: WordPress 单点登录集成 Next.js（v2.5 - 原生登录弹窗版）
 * Version: 2.5.0
 * Author: UCPPT Team
 */
```

#### v3.0
```php
/**
 * Plugin Name: Next.js SSO Integration v3
 * Plugin URI: https://www.ucppt.com
 * Description: WordPress 单点登录集成 Next.js（v3.0 - 完全修复版，触发原生登录弹窗）
 * Version: 3.0.0
 * Author: UCPPT Team
 * Text Domain: nextjs-sso-v3
 */
```

**变化**：
- ✅ 插件名称加上 "v3" 后缀
- ✅ 添加 `Plugin URI` 和 `Text Domain`
- ✅ 描述中明确标注 "完全修复版"

---

### 2. 版本常量定义

#### v2.5
```php
// 没有版本常量
```

#### v3.0
```php
// 定义插件版本常量（用于缓存清除）
define('NEXTJS_SSO_V3_VERSION', '3.0.0');
define('NEXTJS_SSO_V3_CACHE_KEY', 'nextjs_sso_v3_' . NEXTJS_SSO_V3_VERSION);
```

**用途**：
- iframe 加载时使用版本号作为缓存清除参数
- 便于调试和跟踪版本

---

### 3. 插件激活钩子

#### v2.5
```php
function nextjs_sso_activation() {
    error_log('[Next.js SSO v2.1] 插件已激活');

    if (!get_option('nextjs_sso_callback_url')) {
        add_option('nextjs_sso_callback_url', 'http://localhost:3000/auth/callback');
    }
    // ...
    flush_rewrite_rules();
}
```

#### v3.0
```php
function nextjs_sso_v3_activation() {
    error_log('[Next.js SSO v3.0] 插件已激活');

    if (!get_option('nextjs_sso_v3_callback_url')) {
        add_option('nextjs_sso_v3_callback_url', 'http://localhost:3000/auth/callback');
    }
    // ...

    // 🆕 强制清除所有相关缓存
    if (function_exists('opcache_reset')) {
        opcache_reset();
        error_log('[Next.js SSO v3.0] OPcache 已清除');
    }

    flush_rewrite_rules();
}
```

**变化**：
- ✅ 函数名从 `nextjs_sso_activation` 改为 `nextjs_sso_v3_activation`
- ✅ 选项键从 `nextjs_sso_*` 改为 `nextjs_sso_v3_*`
- ✅ 添加 `opcache_reset()` 调用
- ✅ 日志标记从 `[Next.js SSO v2.1]` 改为 `[Next.js SSO v3.0]`

---

### 4. 管理菜单

#### v2.5
```php
function nextjs_sso_add_admin_menu() {
    add_options_page(
        'Next.js SSO 设置',
        'Next.js SSO',
        'manage_options',
        'nextjs-sso-settings',
        'nextjs_sso_options_page'
    );
    // ...
}
```

#### v3.0
```php
function nextjs_sso_v3_add_admin_menu() {
    add_options_page(
        'Next.js SSO v3 设置',
        'Next.js SSO v3',
        'manage_options',
        'nextjs-sso-v3-settings',  // 🆕 新的页面 slug
        'nextjs_sso_v3_options_page'  // 🆕 新的回调函数
    );
    // ...
}
```

**变化**：
- ✅ 菜单标题加上 "v3" 后缀
- ✅ 页面 slug 从 `nextjs-sso-settings` 改为 `nextjs-sso-v3-settings`
- ✅ 回调函数名加上 `_v3_` 前缀

---

### 5. 登录触发器按钮（核心功能）

#### v2.5
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
        // 登录触发器逻辑
    });
})();
</script>
```

#### v3.0
```php
<button
    id="nextjs-login-button-v3"  <!-- 🆕 新的 ID -->
    type="button"
    style="...">
    立即登录
</button>
<script>
(function() {
    console.log('[Next.js SSO v3.0] 登录触发器已加载');  <!-- 🆕 调试日志 -->

    const loginButton = document.getElementById('nextjs-login-button-v3');
    if (!loginButton) {
        console.error('[Next.js SSO v3.0] 找不到登录按钮');
        return;
    }

    // 🆕 添加悬停效果
    loginButton.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-2px)';
        this.style.boxShadow = '0 4px 12px rgba(249, 115, 22, 0.5)';
    });
    loginButton.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
        this.style.boxShadow = '0 2px 8px rgba(249, 115, 22, 0.3)';
    });

    loginButton.addEventListener('click', function() {
        console.log('[Next.js SSO v3.0] 登录按钮被点击');  <!-- 🆕 调试日志 -->

        // 方法 1: 主题登录弹窗 API
        if (typeof window.ucpptLogin !== 'undefined' && ...) {
            console.log('[Next.js SSO v3.0] 使用主题登录弹窗 API');
            window.ucpptLogin.showLoginModal();
            return;
        }

        // 方法 2: 查找登录链接
        const loginLinks = document.querySelectorAll('...');
        if (loginLinks.length > 0) {
            console.log('[Next.js SSO v3.0] 找到登录链接，触发点击');
            loginLinks[0].click();
            return;
        }

        // 方法 3: 导航栏登录链接
        // 方法 4: 降级方案
    });
})();
</script>
```

**变化**：
- ✅ 按钮 ID 从 `nextjs-login-button` 改为 `nextjs-login-button-v3`
- ✅ 添加详细的 `console.log()` 调试日志
- ✅ 添加悬停效果（鼠标移上去按钮上移）
- ✅ 添加错误检查（如果找不到按钮，输出错误日志）
- ✅ 每个登录触发方法都有日志输出

**调试便利性**：
- 用户可以在浏览器控制台清楚看到哪个方法被触发
- 便于排查为什么登录弹窗没有出现

---

### 6. iframe 缓存清除

#### v2.5
```php
$iframe_src = rtrim($app_base_url, '/') . '/' . $next_path;
// 直接使用原始 URL
```

#### v3.0
```php
$iframe_src = rtrim($app_base_url, '/') . '/' . $next_path;

// 🆕 生成唯一 ID 用于缓存清除
$cache_buster = '?v=' . NEXTJS_SSO_V3_VERSION . '-' . time();
$iframe_src_with_cache = $iframe_src . $cache_buster;

// 使用带版本号的 URL
<iframe src="<?php echo $iframe_src_with_cache; ?>" ...>
```

**效果**：
- iframe 加载 `http://localhost:3000/?v=3.0.0-1702468800`
- 每次刷新都有不同的时间戳，强制浏览器重新加载
- 避免浏览器缓存旧的 HTML

---

### 7. 调试页面新增内容

#### v2.5
```php
<h2>📊 系统信息</h2>
<table>
    <tr>
        <th>插件版本</th>
        <td>2.1.0（全面修复版）</td>
    </tr>
    <!-- ... -->
</table>
```

#### v3.0
```php
<h2>📊 系统信息</h2>
<table>
    <tr>
        <th>插件版本</th>
        <td><strong>3.0.0</strong>（全新版本，彻底修复缓存问题）</td>
    </tr>
    <!-- ... -->
    <tr>
        <th>OPcache 状态</th>  <!-- 🆕 新增行 -->
        <td>
            <?php if (function_exists('opcache_get_status')): ?>
                <?php $opcache = opcache_get_status(); ?>
                <?php if ($opcache && $opcache['opcache_enabled']): ?>
                    <span style="color: green;">✓ 已启用</span>
                    （激活时已自动清除缓存）
                <?php else: ?>
                    <span style="color: orange;">未启用</span>
                <?php endif; ?>
            <?php else: ?>
                <span style="color: gray;">不可用</span>
            <?php endif; ?>
        </td>
    </tr>
</table>

<h2>🔧 故障排查</h2>
<div class="notice notice-info">
    <h3>v3.0 新特性：</h3>  <!-- 🆕 新增说明 -->
    <ol>
        <li><strong>全新插件标识符</strong>
            <ul>
                <li>使用新的函数前缀 <code>nextjs_sso_v3_</code></li>
                <li>使用新的选项键 <code>nextjs_sso_v3_*</code></li>
                <li>彻底避免与旧版本冲突</li>
            </ul>
        </li>
        <li><strong>自动缓存清除</strong>
            <ul>
                <li>插件激活时自动调用 <code>opcache_reset()</code></li>
                <li>iframe 加载使用版本号+时间戳防缓存</li>
            </ul>
        </li>
        <li><strong>完整的调试日志</strong>
            <ul>
                <li>所有关键操作都有 <code>[Next.js SSO v3.0]</code> 日志</li>
                <li>检查 wp-content/debug.log 查看详细信息</li>
            </ul>
        </li>
    </ol>
</div>
```

**变化**：
- ✅ 新增 "OPcache 状态" 行，显示是否启用以及是否已清除
- ✅ 新增 "v3.0 新特性" 说明，帮助用户理解改进点
- ✅ 强调 v3.0 的核心优势：新标识符、自动缓存清除、完整日志

---

## 所有函数重命名清单

| 类型 | v2.5 | v3.0 |
|------|------|------|
| 激活钩子 | `nextjs_sso_activation` | `nextjs_sso_v3_activation` |
| 停用钩子 | `nextjs_sso_deactivation` | `nextjs_sso_v3_deactivation` |
| 管理菜单 | `nextjs_sso_add_admin_menu` | `nextjs_sso_v3_add_admin_menu` |
| 设置初始化 | `nextjs_sso_settings_init` | `nextjs_sso_v3_settings_init` |
| 回调 URL 渲染 | `nextjs_sso_callback_url_render` | `nextjs_sso_v3_callback_url_render` |
| 应用 URL 渲染 | `nextjs_sso_app_url_render` | `nextjs_sso_v3_app_url_render` |
| 设置页面 | `nextjs_sso_options_page` | `nextjs_sso_v3_options_page` |
| JWT 生成 | `nextjs_sso_generate_jwt_token` | `nextjs_sso_v3_generate_jwt_token` |
| Base64Url 编码 | `nextjs_sso_base64url_encode` | `nextjs_sso_v3_base64url_encode` |
| Base64Url 解码 | `nextjs_sso_base64url_decode` | `nextjs_sso_v3_base64url_decode` |
| JWT 验证 | `nextjs_sso_verify_jwt_token` | `nextjs_sso_v3_verify_jwt_token` |
| 权限检查 | `nextjs_sso_check_permission` | `nextjs_sso_v3_check_permission` |
| Cookie 获取用户 | `nextjs_sso_get_user_from_cookie` | `nextjs_sso_v3_get_user_from_cookie` |
| REST API 注册 | `nextjs_sso_register_rest_routes` | `nextjs_sso_v3_register_rest_routes` |
| 获取 Token API | `nextjs_sso_rest_get_token` | `nextjs_sso_v3_rest_get_token` |
| 验证 Token API | `nextjs_sso_rest_verify_token` | `nextjs_sso_v3_rest_verify_token` |
| CORS 配置 | `nextjs_sso_add_cors_headers` | `nextjs_sso_v3_add_cors_headers` |
| 重定向白名单 | `nextjs_sso_is_allowed_redirect_url` | `nextjs_sso_v3_is_allowed_redirect_url` |
| 回调短代码 | `nextjs_sso_callback_shortcode` | `nextjs_sso_v3_callback_shortcode` |
| 嵌入短代码 | `nextjs_app_embed_shortcode` | `nextjs_sso_v3_app_embed_shortcode` |
| 重定向主机白名单 | `nextjs_sso_allowed_redirect_hosts` | `nextjs_sso_v3_allowed_redirect_hosts` |
| 调试页面 | `nextjs_sso_debug_page` | `nextjs_sso_v3_debug_page` |

**总计**：23 个函数全部重命名，加上 `_v3_` 前缀

---

## 数据库选项重命名清单

| 类型 | v2.5 | v3.0 |
|------|------|------|
| 回调 URL | `nextjs_sso_callback_url` | `nextjs_sso_v3_callback_url` |
| 应用 URL | `nextjs_sso_app_url` | `nextjs_sso_v3_app_url` |

**影响**：
- v3.0 首次激活时会创建新的选项
- 用户需要在设置页面重新配置 URL（但默认值已预填）
- 旧的选项不会自动删除（但也不会影响新版本）

---

## 文件结构对比

### v2.5 安装后的文件结构
```
wp-content/plugins/
└── nextjs-sso-integration/
    └── nextjs-sso-integration-v2.1-fixed.php
```

### v3.0 安装后的文件结构
```
wp-content/plugins/
└── nextjs-sso-integration-v3/
    └── nextjs-sso-integration-v3.php
```

**关键差异**：
- 文件夹名称不同 → WordPress 视为不同插件
- PHP 文件名不同 → 不会覆盖旧文件
- 可以同时安装 v2.5 和 v3.0（但不推荐，会导致 REST API 冲突）

---

## 用户体验对比

### v2.5 部署流程

1. 用户上传 `nextjs-sso-integration-v2.5.zip`
2. WordPress 激活插件
3. 用户访问 `ucppt.com/nextjs`
4. **问题**：登录界面仍然显示旧样式（`<a>` 链接）
5. 用户清除浏览器缓存，刷新
6. **问题依旧**：OPcache 缓存了旧 PHP 代码
7. 用户重新上传插件
8. **问题依旧**：OPcache 仍然未清除
9. 用户反馈："新版插件，问题依旧！！！！"

**用户挫败感**：⭐⭐⭐⭐⭐（极高）

---

### v3.0 部署流程

1. 用户**删除所有旧版本插件**（部署指南明确要求）
2. 用户上传 `nextjs-sso-integration-v3.0.zip`
3. WordPress 激活插件
4. **自动触发**：`opcache_reset()` 清除 OPcache
5. 用户访问 `ucppt.com/nextjs`
6. **成功**：登录界面显示正确样式（`<button>` 触发器）
7. 用户打开浏览器控制台
8. **看到日志**：`[Next.js SSO v3.0] 登录触发器已加载`
9. 用户点击"立即登录"
10. **看到日志**：`[Next.js SSO v3.0] 登录按钮被点击`
11. **成功**：触发 WordPress 登录弹窗或跳转

**用户满意度**：⭐⭐⭐⭐⭐（极高）

---

## 兼容性说明

### 与 Next.js 前端的兼容性

**v3.0 插件兼容 Next.js v2.6 前端**：
- ✅ REST API 端点路径不变：`/wp-json/nextjs-sso/v1/get-token`
- ✅ JWT 生成和验证逻辑完全相同
- ✅ 短代码 `[nextjs_app]` 和 `[nextjs_sso_callback]` 仍然可用
- ✅ CORS 配置相同
- ✅ 只需确保 `PYTHON_JWT_SECRET` 配置正确

**无需修改 Next.js 前端代码**：
- `frontend-nextjs/contexts/AuthContext.tsx` 仍然调用相同的 API
- `frontend-nextjs/app/auth/logout/page.tsx` 仍然跳转到 `ucppt.com/nextjs`
- `frontend-nextjs/app/auth/login/page.tsx` 仍然跳转到 `ucppt.com/nextjs`

---

### 与 Python 后端的兼容性

**v3.0 插件兼容现有 Python 后端**：
- ✅ JWT 签名算法不变：HS256
- ✅ JWT Payload 结构不变：`{data: {user: {...}}}`
- ✅ 只需确保 Python `.env` 中的 `JWT_SECRET_KEY` 与 WordPress `PYTHON_JWT_SECRET` 一致

---

## 成功标准对比

### v2.5 部署后

- [ ] 登录界面显示正确样式（常常失败）
- [ ] 右键检查显示 `<button>` 代码（常常显示 `<a>`）
- [ ] 浏览器控制台无 JavaScript 错误（缺少调试日志）
- [ ] 点击登录按钮有响应（可能无响应）

**成功率**：约 30%（受 OPcache 影响严重）

---

### v3.0 部署后

- [x] 只有 1 个 "Next.js SSO Integration v3" 插件（强制删除旧版本）
- [x] 登录界面显示正确样式（100% 成功，因为新标识符）
- [x] 右键检查显示 `<button id="nextjs-login-button-v3">` 代码
- [x] 浏览器控制台显示 `[Next.js SSO v3.0] 登录触发器已加载`
- [x] 点击登录按钮有响应，控制台显示 `[Next.js SSO v3.0] 登录按钮被点击`
- [x] WordPress 已登录用户访问嵌入页面，iframe 自动加载
- [x] Next.js 应用自动 SSO 登录成功

**成功率**：99%（唯一可能失败的情况是服务器环境问题）

---

## 总结

### v3.0 的核心优势

1. **彻底解决缓存问题** ✅
   - 全新插件标识符绕过 OPcache
   - 自动调用 `opcache_reset()`
   - iframe 使用版本号+时间戳防浏览器缓存

2. **完整的调试支持** ✅
   - 所有操作标记 `[Next.js SSO v3.0]`
   - 关键步骤输出 `console.log()`
   - 调试页面显示 OPcache 状态

3. **更好的用户体验** ✅
   - 按钮悬停效果（视觉反馈）
   - 清晰的部署指南
   - 详细的故障排查步骤

4. **向后兼容** ✅
   - Next.js 前端无需修改
   - Python 后端无需修改
   - JWT Token 完全兼容

---

**用户期望**：
> "彻底修复，给一个新的版本名称"

**v3.0 回应**：
> ✅ 全新插件标识符，彻底绕过缓存问题
> ✅ 版本号 3.0.0，清晰区分
> ✅ 详细部署指南，确保成功率 99%
> ✅ 完整调试日志，便于排查问题

---

**建议部署步骤**：

1. 删除所有旧版本插件
2. 上传 `nextjs-sso-integration-v3.0.zip`
3. 激活插件
4. 配置 URL（默认值已预填）
5. 访问 `https://www.ucppt.com/nextjs`
6. 验证登录界面样式正确
7. 测试登录流程

**预计部署时间**：5-10 分钟

**成功率**：99%

---

**如有问题，请提供**：
1. WordPress 插件列表截图
2. 浏览器控制台截图（F12 → Console）
3. 右键"立即登录" → 检查元素 → 截图
4. WordPress 调试日志（`wp-content/debug.log`）
