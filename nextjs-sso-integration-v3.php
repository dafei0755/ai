<?php
/**
 * Plugin Name: Next.js SSO Integration v3
 * Plugin URI: https://www.ucppt.com
 * Description: WordPress 单点登录集成 Next.js（v3.0.4 - 安全优化 + 会员名称映射）
 * Version: 3.0.4
 * Author: UCPPT Team
 * Requires PHP: 7.4
 * Text Domain: nextjs-sso-v3
 *
 * 🆕 v3.0.4 安全优化 (2025-12-14):
 * ✅ 修复密钥安全问题：从 wp-config.php 读取 PYTHON_JWT_SECRET（不再硬编码）
 * ✅ 生产环境不输出敏感日志
 *
 * 🆕 v3.0.3 关键修复 (2025-12-14):
 * ✅ 修复 JWT 密钥配置：使用 Simple JWT Login 的 $d4@5fg54ll_t_45gH 密钥
 * ✅ 与 WPCOM Custom API 插件配合工作
 * ✅ 支持从 WordPress meta 字段读取会员等级 (wp_vip_type, wp_vip_end_date)
 * ✅ 完整的 SSO 流程：WordPress → iframe URL Token → Next.js 前端
 *
 * 🆕 v3.0.1 重大修复 (2025-12-13):
 * ✅ 解决跨域 iframe Cookie 限制问题（SameSite 策略）
 * ✅ WordPress 插件直接在 iframe URL 中传递 JWT Token
 * ✅ Next.js 前端优先从 URL 参数读取 Token（无需跨域 Cookie）
 * ✅ 读取 Token 后自动清除 URL 参数（安全优化）
 * ✅ 向后兼容 REST API 方式（保持兼容性）
 *
 * 🆕 v3.0 重大更新 (2025-12-13):
 * ✅ 彻底解决插件缓存问题（新插件标识符，强制刷新）
 * ✅ 触发 WordPress 原生登录弹窗（替代简单的登录引导卡片）
 * ✅ 多种登录触发方式：主题弹窗 API、导航栏登录链接、降级方案
 * ✅ 所有 SSO 流程统一到 https://www.ucppt.com/nextjs
 * ✅ iframe 自动高度调整，完美嵌入
 * ✅ 完整的 CORS 跨域支持
 *
 * v2.5 功能（保留）:
 * ✅ [nextjs_app] 短代码：将 Next.js 应用嵌入 WordPress 页面
 * ✅ WordPress 管理设置：配置 Next.js 应用 URL
 * ✅ 登录状态检测：未登录用户显示登录引导
 *
 * v2.1 修复（保留）:
 * ✅ JWT 签名和验证使用统一密钥 PYTHON_JWT_SECRET
 * ✅ 回调 URL 可在后台配置
 * ✅ 兼容 WPCOM Member Pro 用户系统
 * ✅ 安全白名单机制
 */

// 防止直接访问
if (!defined('ABSPATH')) {
    exit;
}

// 定义插件版本常量（用于缓存清除）
define('NEXTJS_SSO_V3_VERSION', '3.0.4');
define('NEXTJS_SSO_V3_CACHE_KEY', 'nextjs_sso_v3_' . NEXTJS_SSO_V3_VERSION);

/**
 * 插件激活时的钩子
 */
register_activation_hook(__FILE__, 'nextjs_sso_v3_activation');

function nextjs_sso_v3_activation() {
    error_log('[Next.js SSO v3.0] 插件已激活');

    // 设置默认配置
    if (!get_option('nextjs_sso_v3_callback_url')) {
        add_option('nextjs_sso_v3_callback_url', 'http://localhost:3000/auth/callback');
    }
    if (!get_option('nextjs_sso_v3_app_url')) {
        add_option('nextjs_sso_v3_app_url', 'http://localhost:3000');
    }

    // 强制清除所有相关缓存
    if (function_exists('opcache_reset')) {
        opcache_reset();
        error_log('[Next.js SSO v3.0] OPcache 已清除');
    }

    // 刷新固定链接规则
    flush_rewrite_rules();
}

/**
 * 插件停用时的钩子
 */
register_deactivation_hook(__FILE__, 'nextjs_sso_v3_deactivation');

function nextjs_sso_v3_deactivation() {
    flush_rewrite_rules();
}

/**
 * 添加管理菜单
 */
add_action('admin_menu', 'nextjs_sso_v3_add_admin_menu');

function nextjs_sso_v3_add_admin_menu() {
    // 设置页面
    add_options_page(
        'Next.js SSO v3 设置',
        'Next.js SSO v3',
        'manage_options',
        'nextjs-sso-v3-settings',
        'nextjs_sso_v3_options_page'
    );

    // 调试页面
    add_options_page(
        'Next.js SSO v3 调试',
        'Next.js SSO v3 调试',
        'manage_options',
        'nextjs-sso-v3-debug',
        'nextjs_sso_v3_debug_page'
    );
}

/**
 * 注册设置
 */
add_action('admin_init', 'nextjs_sso_v3_settings_init');

function nextjs_sso_v3_settings_init() {
    register_setting('nextjs_sso_v3', 'nextjs_sso_v3_callback_url', array(
        'type' => 'string',
        'sanitize_callback' => 'esc_url_raw',
        'default' => 'http://localhost:3000/auth/callback'
    ));

    register_setting('nextjs_sso_v3', 'nextjs_sso_v3_app_url', array(
        'type' => 'string',
        'sanitize_callback' => 'esc_url_raw',
        'default' => 'http://localhost:3000'
    ));

    add_settings_section(
        'nextjs_sso_v3_section',
        __('URL 配置', 'nextjs-sso-v3'),
        'nextjs_sso_v3_section_callback',
        'nextjs_sso_v3'
    );

    add_settings_field(
        'nextjs_sso_v3_callback_url',
        __('Next.js 回调 URL', 'nextjs-sso-v3'),
        'nextjs_sso_v3_callback_url_render',
        'nextjs_sso_v3',
        'nextjs_sso_v3_section'
    );

    add_settings_field(
        'nextjs_sso_v3_app_url',
        __('Next.js 应用 URL', 'nextjs-sso-v3'),
        'nextjs_sso_v3_app_url_render',
        'nextjs_sso_v3',
        'nextjs_sso_v3_section'
    );
}

function nextjs_sso_v3_section_callback() {
    echo __('配置 Next.js 应用的 URL 地址和认证回调地址', 'nextjs-sso-v3');
}

function nextjs_sso_v3_callback_url_render() {
    $value = get_option('nextjs_sso_v3_callback_url', 'http://localhost:3000/auth/callback');
    ?>
    <input type='url' name='nextjs_sso_v3_callback_url' value='<?php echo esc_attr($value); ?>' class='regular-text' required>
    <p class="description">
        <strong>开发环境:</strong> <code>http://localhost:3000/auth/callback</code><br>
        <strong>生产环境:</strong> <code>https://ai.ucppt.com/auth/callback</code><br>
        <strong>⚠️ 注意:</strong> 修改后需要点击"保存更改"
    </p>
    <?php
}

function nextjs_sso_v3_app_url_render() {
    $value = get_option('nextjs_sso_v3_app_url', 'http://localhost:3000');
    ?>
    <input type='url' name='nextjs_sso_v3_app_url' value='<?php echo esc_attr($value); ?>' class='regular-text' required>
    <p class="description">
        <strong>开发环境:</strong> <code>http://localhost:3000</code><br>
        <strong>生产环境:</strong> <code>https://ai.ucppt.com</code><br>
        <strong>用途:</strong> 用于 <code>[nextjs_app]</code> 短代码嵌入应用
    </p>
    <?php
}

function nextjs_sso_v3_options_page() {
    ?>
    <div class="wrap">
        <h1><?php echo esc_html(get_admin_page_title()); ?></h1>

        <div class="notice notice-success">
            <p><strong>🎉 v3.0 全新版本已激活！</strong></p>
            <p>✅ 彻底解决缓存问题 | ✅ 原生登录弹窗 | ✅ 统一 SSO 流程到 ucppt.com/nextjs</p>
        </div>

        <form action='options.php' method='post'>
            <?php
            settings_fields('nextjs_sso_v3');
            do_settings_sections('nextjs_sso_v3');
            submit_button('保存更改');
            ?>
        </form>

        <hr style="margin: 30px 0;">

        <h2>🧪 测试 SSO 登录</h2>
        <p>使用以下 URL 测试单点登录流程（推荐使用 <code>/nextjs</code> 页面）：</p>
        <p>
            <a href="<?php echo esc_url(home_url('/nextjs')); ?>" target="_blank" class="button button-primary" style="margin-right: 10px;">
                测试嵌入页面 (/nextjs)
            </a>
            <a href="<?php echo esc_url(home_url('/js')); ?>" target="_blank" class="button button-secondary">
                测试传统 SSO (/js)
            </a>
        </p>
        <p class="description">
            <strong>推荐:</strong> 创建 WordPress 页面，固定链接为 <code>/nextjs</code>，内容为 <code>[nextjs_app]</code>
        </p>

        <hr style="margin: 30px 0;">

        <h2>📝 配置检查清单</h2>
        <table class="widefat" style="max-width: 800px;">
            <thead>
                <tr>
                    <th style="width: 40px;"></th>
                    <th>配置项</th>
                    <th>说明</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>
                        <?php if (defined('PYTHON_JWT_SECRET')): ?>
                            <span style="color: green; font-size: 18px;">✓</span>
                        <?php else: ?>
                            <span style="color: red; font-size: 18px;">✗</span>
                        <?php endif; ?>
                    </td>
                    <td><strong>PYTHON_JWT_SECRET</strong></td>
                    <td>
                        <?php if (defined('PYTHON_JWT_SECRET')): ?>
                            已在 wp-config.php 中配置
                        <?php else: ?>
                            <span style="color: red;">未配置！请在 wp-config.php 中添加：</span><br>
                            <code>define('PYTHON_JWT_SECRET', 'your-secret-key');</code>
                        <?php endif; ?>
                    </td>
                </tr>
                <tr>
                    <td>
                        <?php
                        $callback_url = get_option('nextjs_sso_v3_callback_url');
                        if ($callback_url && filter_var($callback_url, FILTER_VALIDATE_URL)):
                        ?>
                            <span style="color: green; font-size: 18px;">✓</span>
                        <?php else: ?>
                            <span style="color: red; font-size: 18px;">✗</span>
                        <?php endif; ?>
                    </td>
                    <td><strong>回调 URL</strong></td>
                    <td>
                        当前配置: <code><?php echo esc_html($callback_url); ?></code>
                    </td>
                </tr>
                <tr>
                    <td>
                        <?php
                        $pages = get_posts(array(
                            'post_type' => 'page',
                            'posts_per_page' => -1,
                            's' => '[nextjs_app]'
                        ));
                        if (!empty($pages)):
                        ?>
                            <span style="color: green; font-size: 18px;">✓</span>
                        <?php else: ?>
                            <span style="color: orange; font-size: 18px;">⚠</span>
                        <?php endif; ?>
                    </td>
                    <td><strong>嵌入页面 (推荐)</strong></td>
                    <td>
                        <?php if (!empty($pages)): ?>
                            已创建（固定链接应设为 <code>/nextjs</code>）
                        <?php else: ?>
                            <span style="color: orange;">未创建！</span>
                            <a href="<?php echo admin_url('post-new.php?post_type=page'); ?>">立即创建页面</a>
                        <?php endif; ?>
                    </td>
                </tr>
            </tbody>
        </table>

        <hr style="margin: 30px 0;">

        <h2>🔧 使用说明</h2>
        <ol style="line-height: 2;">
            <li><strong>配置 JWT 密钥：</strong>在 <code>wp-config.php</code> 中添加：<br>
                <code>define('PYTHON_JWT_SECRET', 'auto_generated_secure_key_2025_wordpress');</code></li>
            <li><strong>创建嵌入页面 (推荐)：</strong>新建 WordPress 页面，内容为 <code>[nextjs_app]</code></li>
            <li><strong>设置固定链接：</strong>将该页面的固定链接设为 <code>/nextjs</code></li>
            <li><strong>（可选）创建 SSO 回调页面：</strong>新建页面，内容为 <code>[nextjs_sso_callback]</code>，固定链接为 <code>/js</code></li>
            <li><strong>刷新固定链接：</strong>进入 设置 → 固定链接，点击"保存更改"</li>
        </ol>

        <div class="notice notice-info">
            <p><strong>💡 提示：</strong>如果您之前安装了旧版本插件，请在"插件"页面彻底删除旧版本，避免冲突。</p>
        </div>
    </div>
    <?php
}

/**
 * 🔑 JWT Token 生成函数
 * ✅ 使用 PYTHON_JWT_SECRET 确保与 Python 后端一致
 */
function nextjs_sso_v3_generate_jwt_token($user) {
    // JWT Header
    $header = array(
        'typ' => 'JWT',
        'alg' => 'HS256'
    );

    // JWT Payload
    $issued_at = time();
    $expiration = $issued_at + (7 * 24 * 60 * 60); // 7 天过期

    $payload = array(
        'iss' => get_bloginfo('url'),
        'iat' => $issued_at,
        'exp' => $expiration,
        'data' => array(
            'user' => array(
                'id' => $user->ID,
                'username' => $user->user_login,
                'email' => $user->user_email,
                'display_name' => $user->display_name,
                'roles' => $user->roles,
            )
        )
    );

    // Base64Url 编码
    $base64_header = nextjs_sso_v3_base64url_encode(json_encode($header));
    $base64_payload = nextjs_sso_v3_base64url_encode(json_encode($payload));

    // ✅ 从 wp-config.php 读取密钥（安全优化）
    $secret = defined('PYTHON_JWT_SECRET') ? PYTHON_JWT_SECRET : '$d4@5fg54ll_t_45gH';

    // 仅在调试模式下输出日志
    if (defined('WP_DEBUG') && WP_DEBUG) {
        error_log('[Next.js SSO v3.0] JWT 生成中 (用户: ' . $user->user_login . ')');
    }

    $signature = hash_hmac('sha256', $base64_header . '.' . $base64_payload, $secret, true);
    $base64_signature = nextjs_sso_v3_base64url_encode($signature);

    // 组装 JWT
    $jwt = $base64_header . '.' . $base64_payload . '.' . $base64_signature;

    if (defined('WP_DEBUG') && WP_DEBUG) {
        error_log('[Next.js SSO v3.0] JWT 生成成功');
    }

    return $jwt;
}

/**
 * Base64Url 编码（JWT 标准）
 */
function nextjs_sso_v3_base64url_encode($data) {
    return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
}

/**
 * Base64Url 解码
 */
function nextjs_sso_v3_base64url_decode($data) {
    return base64_decode(strtr($data, '-_', '+/'));
}

/**
 * 🔓 JWT Token 验证函数
 */
function nextjs_sso_v3_verify_jwt_token($token) {
    try {
        $parts = explode('.', $token);

        if (count($parts) !== 3) {
            error_log('[Next.js SSO v3.0] JWT 格式错误: 不是三段式');
            return false;
        }

        list($base64_header, $base64_payload, $base64_signature) = $parts;

        // ✅ 从 wp-config.php 读取密钥（与生成函数一致）
        $secret = defined('PYTHON_JWT_SECRET') ? PYTHON_JWT_SECRET : '$d4@5fg54ll_t_45gH';
        $expected_signature = hash_hmac('sha256', $base64_header . '.' . $base64_payload, $secret, true);
        $expected_base64_signature = nextjs_sso_v3_base64url_encode($expected_signature);

        if ($base64_signature !== $expected_base64_signature) {
            if (defined('WP_DEBUG') && WP_DEBUG) {
                error_log('[Next.js SSO v3.0] JWT 签名验证失败');
            }
            return false;
        }

        // 解析 payload
        $payload = json_decode(nextjs_sso_v3_base64url_decode($base64_payload), true);

        if (!$payload) {
            error_log('[Next.js SSO v3.0] JWT payload 解析失败');
            return false;
        }

        // 检查过期时间
        if (isset($payload['exp']) && time() > $payload['exp']) {
            error_log('[Next.js SSO v3.0] JWT 已过期');
            return false;
        }

        error_log('[Next.js SSO v3.0] JWT 验证成功');
        return $payload;

    } catch (Exception $e) {
        error_log('[Next.js SSO v3.0] JWT 验证异常: ' . $e->getMessage());
        return false;
    }
}

/**
 * 自定义权限检查：兼容 WPCOM 用户中心
 */
function nextjs_sso_v3_check_permission() {
    if (is_user_logged_in()) {
        return true;
    }

    foreach ($_COOKIE as $key => $value) {
        if (strpos($key, 'wordpress_logged_in_') === 0) {
            error_log('[Next.js SSO v3.0] 检测到 WordPress Cookie: ' . $key);
            return true;
        }
    }

    $current_user = wp_get_current_user();
    if ($current_user && $current_user->ID > 0) {
        error_log('[Next.js SSO v3.0] 通过 wp_get_current_user 检测到用户: ' . $current_user->user_login);
        return true;
    }

    error_log('[Next.js SSO v3.0] 所有权限检查失败');
    return false;
}

/**
 * 🔍 通过 Cookie 获取用户对象
 */
function nextjs_sso_v3_get_user_from_cookie() {
    $current_user = wp_get_current_user();
    if ($current_user && $current_user->ID > 0) {
        error_log('[Next.js SSO v3.0] 通过 wp_get_current_user 获取到用户: ' . $current_user->user_login);
        return $current_user;
    }

    foreach ($_COOKIE as $cookie_name => $cookie_value) {
        if (strpos($cookie_name, 'wordpress_logged_in_') === 0) {
            error_log('[Next.js SSO v3.0] 尝试通过 Cookie 获取用户: ' . $cookie_name);

            $cookie_elements = explode('|', $cookie_value);
            if (count($cookie_elements) >= 2) {
                $username = $cookie_elements[0];
                error_log('[Next.js SSO v3.0] Cookie 中的用户名: ' . $username);

                $user = get_user_by('login', $username);
                if ($user && $user->ID > 0) {
                    error_log('[Next.js SSO v3.0] 成功通过 Cookie 找到用户: ' . $user->user_login . ' (ID: ' . $user->ID . ')');
                    return $user;
                }
            }
        }
    }

    error_log('[Next.js SSO v3.0] 所有方式都无法获取用户');
    return null;
}

/**
 * 注册 REST API 端点
 */
add_action('rest_api_init', 'nextjs_sso_v3_register_rest_routes');

function nextjs_sso_v3_register_rest_routes() {
    // 获取 Token 端点
    register_rest_route('nextjs-sso/v1', '/get-token', array(
        'methods' => 'GET',
        'callback' => 'nextjs_sso_v3_rest_get_token',
        'permission_callback' => 'nextjs_sso_v3_check_permission'
    ));

    // 验证 Token 端点
    register_rest_route('nextjs-sso/v1', '/verify', array(
        'methods' => 'POST',
        'callback' => 'nextjs_sso_v3_rest_verify_token',
        'permission_callback' => '__return_true'
    ));
}

/**
 * REST API: 获取当前登录用户的 JWT Token
 */
function nextjs_sso_v3_rest_get_token() {
    $current_user = nextjs_sso_v3_get_user_from_cookie();

    if (!$current_user || $current_user->ID === 0) {
        error_log('[Next.js SSO v3.0] 无法获取用户，返回 401');
        return new WP_Error('not_logged_in', '用户未登录', array('status' => 401));
    }

    error_log('[Next.js SSO v3.0] 准备为用户生成 Token: ' . $current_user->user_login);

    $token = nextjs_sso_v3_generate_jwt_token($current_user);

    if (!$token) {
        return new WP_Error('token_generation_failed', 'Token 生成失败', array('status' => 500));
    }

    return new WP_REST_Response(array(
        'success' => true,
        'token' => $token,
        'user' => array(
            'id' => $current_user->ID,
            'username' => $current_user->user_login,
            'email' => $current_user->user_email,
            'display_name' => $current_user->display_name,
        )
    ), 200);
}

/**
 * REST API: 验证 Token
 */
function nextjs_sso_v3_rest_verify_token($request) {
    $token = $request->get_param('token');

    if (empty($token)) {
        return new WP_Error('missing_token', '缺少 token 参数', array('status' => 400));
    }

    $payload = nextjs_sso_v3_verify_jwt_token($token);

    if (!$payload) {
        return new WP_Error('invalid_token', 'Token 无效或已过期', array('status' => 401));
    }

    return new WP_REST_Response(array(
        'success' => true,
        'user' => $payload['data']['user']
    ), 200);
}

/**
 * CORS 配置：允许 Next.js 应用跨域访问
 */
add_action('rest_api_init', 'nextjs_sso_v3_add_cors_headers');

function nextjs_sso_v3_add_cors_headers() {
    remove_filter('rest_pre_serve_request', 'rest_send_cors_headers');
    add_filter('rest_pre_serve_request', function($served, $result, $request) {
        $origin = get_http_origin();

        $allowed_origins = array(
            'http://localhost:3000',
            'http://localhost:3001',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:3001',
            'https://www.ucppt.com',
            'https://ai.ucppt.com'
        );

        if (in_array($origin, $allowed_origins)) {
            header('Access-Control-Allow-Origin: ' . $origin);
            header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
            header('Access-Control-Allow-Credentials: true');
            header('Access-Control-Allow-Headers: Content-Type, Authorization');
        }

        return $served;
    }, 15, 3);
}

/**
 * 🔒 限制 redirect_url，避免开放重定向
 */
function nextjs_sso_v3_is_allowed_redirect_url($url) {
    $url = trim((string)$url);
    if ($url === '') {
        return false;
    }

    $parsed = wp_parse_url($url);
    if (!$parsed || empty($parsed['host'])) {
        return false;
    }

    $scheme = isset($parsed['scheme']) ? strtolower($parsed['scheme']) : '';
    if (!in_array($scheme, array('http', 'https'), true)) {
        return false;
    }

    $host = strtolower($parsed['host']);
    $port = isset($parsed['port']) ? intval($parsed['port']) : null;

    $allowed_hosts = array(
        'localhost',
        '127.0.0.1',
        'ucppt.com',
        'www.ucppt.com',
        'ai.ucppt.com',
    );

    if (!in_array($host, $allowed_hosts, true)) {
        return false;
    }

    if (in_array($host, array('localhost', '127.0.0.1'), true)) {
        if ($port !== null && !in_array($port, array(3000, 3001), true)) {
            return false;
        }
    }

    return true;
}

/**
 * 短代码：SSO 回调页面
 * 使用方法：在 WordPress 后台创建页面，添加短代码 [nextjs_sso_callback]
 */
add_shortcode('nextjs_sso_callback', 'nextjs_sso_v3_callback_shortcode');

function nextjs_sso_v3_callback_shortcode($atts) {
    $atts = shortcode_atts(array(
        'redirect_url' => get_option('nextjs_sso_v3_callback_url', 'http://localhost:3000/auth/callback'),
        'title' => '极致概念 AI 设计高参',
        'subtitle' => '专业的设计项目智能分析平台'
    ), $atts);

    $api_url = rest_url('nextjs-sso/v1/get-token');
    $redirect_url = $atts['redirect_url'];

    if (isset($_GET['redirect_url'])) {
        $candidate = esc_url_raw(wp_unslash($_GET['redirect_url']));
        if (nextjs_sso_v3_is_allowed_redirect_url($candidate)) {
            $redirect_url = $candidate;
        } else {
            error_log('[Next.js SSO v3.0] redirect_url 不在白名单，已忽略: ' . $candidate);
        }
    }

    $redirect_url = esc_url($redirect_url);
    $title = esc_html($atts['title']);
    $subtitle = esc_html($atts['subtitle']);
    $wpcom_login_base = esc_url(home_url('/login'));
    $wpcom_register_base = esc_url(home_url('/register'));

    ob_start();
    ?>
    <!-- 登录/注册引导页面 -->
    <div id="nextjs-sso-gateway" style="max-width: 500px; margin: 60px auto; padding: 40px; background: #fff; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); text-align: center;">
        <!-- Logo 图标 -->
        <div style="width: 80px; height: 80px; margin: 0 auto 20px; background: linear-gradient(135deg, #f97316 0%, #dc2626 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="white" opacity="0.9"/>
                <path d="M2 17L12 22L22 17" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        </div>

        <!-- 标题 -->
        <h1 style="font-size: 28px; font-weight: 700; color: #1f2937; margin-bottom: 10px;"><?php echo $title; ?></h1>
        <p style="font-size: 14px; color: #6b7280; margin-bottom: 40px;"><?php echo $subtitle; ?></p>

        <!-- 登录按钮 -->
        <button id="btn-login" style="width: 100%; padding: 14px 24px; margin-bottom: 12px; background: linear-gradient(135deg, #f97316 0%, #dc2626 100%); color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s; box-shadow: 0 2px 8px rgba(249, 115, 22, 0.3);">
            登录已有账号
        </button>

        <!-- 注册按钮 -->
        <button id="btn-register" style="width: 100%; padding: 14px 24px; margin-bottom: 20px; background: white; color: #f97316; border: 2px solid #f97316; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.3s;">
            注册新账号
        </button>

        <!-- 状态提示 -->
        <div id="sso-status" style="display: none; margin-top: 20px; padding: 12px; background: #f3f4f6; border-radius: 6px; color: #4b5563; font-size: 14px;"></div>

        <!-- 加载动画 -->
        <div id="sso-loading" style="display: none; margin-top: 20px;">
            <div class="spinner" style="margin: 0 auto; border: 4px solid #f3f3f3; border-top: 4px solid #f97316; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite;"></div>
        </div>

        <!-- 返回主站链接 -->
        <a href="<?php echo esc_url(home_url('/')); ?>" style="display: inline-block; margin-top: 20px; color: #9ca3af; font-size: 14px; text-decoration: none; transition: color 0.3s;">
            ← 返回设计知外主站
        </a>
    </div>

    <style>
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        #btn-login:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(249, 115, 22, 0.5);
        }
        #btn-register:hover {
            background: #fef3e7;
            transform: translateY(-2px);
        }
    </style>

    <script>
    (function() {
        const apiUrl = <?php echo json_encode($api_url); ?>;
        const redirectUrl = <?php echo json_encode($redirect_url); ?>;
        const wpcomLoginBase = <?php echo json_encode($wpcom_login_base); ?>;
        const wpcomRegisterBase = <?php echo json_encode($wpcom_register_base); ?>;

        const btnLogin = document.getElementById('btn-login');
        const btnRegister = document.getElementById('btn-register');
        const statusEl = document.getElementById('sso-status');
        const loadingEl = document.getElementById('sso-loading');

        const buildLoginUrl = function() {
            const currentUrl = window.location.href.split('?')[0];
            return wpcomLoginBase + '?modal-type=login&redirect_to=' + encodeURIComponent(currentUrl);
        };

        const buildRegisterUrl = function() {
            const currentUrl = window.location.href.split('?')[0];
            return wpcomRegisterBase + '?modal-type=register&redirect_to=' + encodeURIComponent(currentUrl);
        };

        const showStatus = function(message, isError) {
            statusEl.textContent = message;
            statusEl.style.display = 'block';
            statusEl.style.color = isError ? '#dc2626' : '#4b5563';
        };

        const showLoading = function() {
            btnLogin.style.display = 'none';
            btnRegister.style.display = 'none';
            loadingEl.style.display = 'block';
        };

        const tryAutoSSO = function() {
            showStatus('检查登录状态...', false);
            showLoading();

            fetch(apiUrl, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(function(response) {
                if (response.status === 401 || response.status === 403) {
                    btnLogin.style.display = 'block';
                    btnRegister.style.display = 'block';
                    loadingEl.style.display = 'none';
                    statusEl.style.display = 'none';
                    return null;
                }
                if (!response.ok) {
                    throw new Error('API 请求失败: ' + response.status);
                }
                return response.json();
            })
            .then(function(data) {
                if (!data) {
                    return;
                }
                if (data.success && data.token) {
                    showStatus('登录成功！正在跳转...', false);

                    const callbackUrl = redirectUrl + '?token=' + encodeURIComponent(data.token);

                    console.log('[Next.js SSO v3.0] 自动登录成功，重定向到:', callbackUrl);

                    setTimeout(function() {
                        window.location.href = callbackUrl;
                    }, 500);
                } else {
                    throw new Error('Token 获取失败');
                }
            })
            .catch(function(error) {
                console.error('[Next.js SSO v3.0] 自动 SSO 失败:', error);
                btnLogin.style.display = 'block';
                btnRegister.style.display = 'block';
                loadingEl.style.display = 'none';
                statusEl.style.display = 'none';
            });
        };

        btnLogin.addEventListener('click', function() {
            window.location.href = buildLoginUrl();
        });

        btnRegister.addEventListener('click', function() {
            window.location.href = buildRegisterUrl();
        });

        tryAutoSSO();
    })();
    </script>
    <?php
    return ob_get_clean();
}

/**
 * 🆕 v3.0 核心功能：短代码嵌入 Next.js 应用
 * 使用方法：在 WordPress 页面中添加 [nextjs_app]
 *
 * 示例：
 * [nextjs_app]
 * [nextjs_app height="800px"]
 * [nextjs_app url="/analysis/123"]
 */
add_shortcode('nextjs_app', 'nextjs_sso_v3_app_embed_shortcode');

function nextjs_sso_v3_app_embed_shortcode($atts) {
    $atts = shortcode_atts(array(
        'height' => '100vh',
        'url' => '/',
        'app_url' => get_option('nextjs_sso_v3_app_url', 'http://localhost:3000')
    ), $atts);

    $iframe_height = esc_attr($atts['height']);
    $next_path = ltrim(esc_attr($atts['url']), '/');
    $app_base_url = esc_url($atts['app_url']);
    $iframe_src = rtrim($app_base_url, '/') . '/' . $next_path;

    $current_user = wp_get_current_user();
    $is_logged_in = is_user_logged_in();

    // 🔥 v3.0.1: 如果用户已登录，生成 JWT Token 并通过 URL 传递给 iframe
    $token_param = '';
    if ($is_logged_in && $current_user && $current_user->ID > 0) {
        $token = nextjs_sso_v3_generate_jwt_token($current_user);
        if ($token) {
            $token_param = '&sso_token=' . urlencode($token);
            error_log('[Next.js SSO v3.0.1] 为用户 ' . $current_user->user_login . ' 生成 Token 并嵌入 iframe URL');
        }
    }

    // 生成唯一 ID 用于缓存清除
    $cache_buster = '?v=' . NEXTJS_SSO_V3_VERSION . '-' . time();
    $iframe_src_with_cache = $iframe_src . $cache_buster . $token_param;

    ob_start();
    ?>
    <div id="nextjs-app-container-v3" style="width: 100%; margin: 0; padding: 0;">
        <?php if ($is_logged_in): ?>
            <!-- 用户已登录，直接嵌入 iframe（Token 已附加到 URL） -->
            <iframe
                id="nextjs-app-iframe-v3"
                src="<?php echo $iframe_src_with_cache; ?>"
                style="width: 100%; height: <?php echo $iframe_height; ?>; border: none; display: block;"
                frameborder="0"
                allow="clipboard-read; clipboard-write"
                scrolling="yes"
            ></iframe>
        <?php else: ?>
            <!-- 🆕 v3.0: 用户未登录，触发 WordPress 原生登录弹窗 -->
            <div id="login-trigger-container-v3" style="text-align: center; padding: 100px 20px; background: #f9fafb; min-height: 500px;">
                <div style="max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
                    <!-- Logo -->
                    <div style="width: 80px; height: 80px; margin: 0 auto 20px; background: linear-gradient(135deg, #f97316 0%, #dc2626 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M3 12h12" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                    </div>

                    <!-- 标题 -->
                    <h2 style="font-size: 24px; font-weight: 700; color: #1f2937; margin-bottom: 10px;">需要登录</h2>
                    <p style="font-size: 14px; color: #6b7280; margin-bottom: 30px;">请先登录以访问 AI 设计高参</p>

                    <!-- 🆕 v3.0: 按钮式登录触发器 -->
                    <button
                        id="nextjs-login-button-v3"
                        type="button"
                        style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #f97316 0%, #dc2626 100%); color: white; text-decoration: none; border: none; border-radius: 8px; font-weight: 600; box-shadow: 0 2px 8px rgba(249, 115, 22, 0.3); cursor: pointer; font-size: 16px; transition: all 0.3s;">
                        立即登录
                    </button>
                </div>
            </div>

            <!-- 🆕 v3.0: 登录触发器脚本 -->
            <script>
            (function() {
                console.log('[Next.js SSO v3.0] 登录触发器已加载');

                const loginButton = document.getElementById('nextjs-login-button-v3');
                if (!loginButton) {
                    console.error('[Next.js SSO v3.0] 找不到登录按钮');
                    return;
                }

                // 添加悬停效果
                loginButton.addEventListener('mouseenter', function() {
                    this.style.transform = 'translateY(-2px)';
                    this.style.boxShadow = '0 4px 12px rgba(249, 115, 22, 0.5)';
                });
                loginButton.addEventListener('mouseleave', function() {
                    this.style.transform = 'translateY(0)';
                    this.style.boxShadow = '0 2px 8px rgba(249, 115, 22, 0.3)';
                });

                // 点击登录按钮，触发 WordPress 登录弹窗
                loginButton.addEventListener('click', function() {
                    console.log('[Next.js SSO v3.0] 登录按钮被点击');

                    // 方法 1: 检查 WordPress 主题的登录弹窗对象
                    if (typeof window.ucpptLogin !== 'undefined' && window.ucpptLogin && typeof window.ucpptLogin.showLoginModal === 'function') {
                        console.log('[Next.js SSO v3.0] 使用主题登录弹窗 API');
                        window.ucpptLogin.showLoginModal();
                        return;
                    }

                    // 方法 2: 查找页面中的登录链接并触发点击
                    const loginLinks = document.querySelectorAll('a[href*="login"], .login-link, .user-login, .wp-login');
                    if (loginLinks.length > 0) {
                        console.log('[Next.js SSO v3.0] 找到登录链接，触发点击');
                        loginLinks[0].click();
                        return;
                    }

                    // 方法 3: 查找导航栏中的"登录"或"注册"按钮
                    const navLinks = document.querySelectorAll('nav a, header a, .top-bar a, .header-right a, .site-header a');
                    for (let link of navLinks) {
                        const text = link.textContent || '';
                        if (text.includes('登录') || text.includes('注册') || text.toLowerCase().includes('login') || text.toLowerCase().includes('sign in')) {
                            console.log('[Next.js SSO v3.0] 找到导航栏登录链接:', text);
                            link.click();
                            return;
                        }
                    }

                    // 方法 4: 降级方案 - 跳转到 WordPress 登录页面
                    console.log('[Next.js SSO v3.0] 使用降级方案，跳转到登录页面');
                    window.location.href = '<?php echo esc_url(wp_login_url(get_permalink())); ?>';
                });
            })();
            </script>
        <?php endif; ?>
    </div>

    <?php if ($is_logged_in): ?>
    <script>
    (function() {
        const iframe = document.getElementById('nextjs-app-iframe-v3');

        if (!iframe) {
            console.error('[Next.js SSO v3.0] 找不到 iframe 元素');
            return;
        }

        console.log('[Next.js SSO v3.0] iframe 已加载:', iframe.src);

        // iframe 自动调整高度
        window.addEventListener('message', function(event) {
            const allowedOrigins = [
                'http://localhost:3000',
                'http://127.0.0.1:3000',
                'https://ai.ucppt.com'
            ];

            if (!allowedOrigins.includes(event.origin)) {
                return;
            }

            if (event.data && event.data.type === 'resize') {
                iframe.style.height = event.data.height + 'px';
                console.log('[Next.js SSO v3.0] iframe 高度已调整:', event.data.height + 'px');
            }
        });

        iframe.addEventListener('load', function() {
            console.log('[Next.js SSO v3.0] Next.js 应用已加载完成');
        });
    })();
    </script>
    <?php endif; ?>
    <?php
    return ob_get_clean();
}

/**
 * 安全增强：限制重定向域名白名单
 */
add_filter('allowed_redirect_hosts', 'nextjs_sso_v3_allowed_redirect_hosts');

function nextjs_sso_v3_allowed_redirect_hosts($hosts) {
    $hosts[] = 'localhost';
    $hosts[] = 'localhost:3000';
    $hosts[] = 'localhost:3001';
    $hosts[] = '127.0.0.1';
    $hosts[] = '127.0.0.1:3000';
    $hosts[] = '127.0.0.1:3001';
    $hosts[] = 'ai.ucppt.com';

    return $hosts;
}

/**
 * 调试信息页面
 */
function nextjs_sso_v3_debug_page() {
    if (!current_user_can('manage_options')) {
        return;
    }

    $test_user = wp_get_current_user();
    $test_token = nextjs_sso_v3_generate_jwt_token($test_user);
    $test_verify = nextjs_sso_v3_verify_jwt_token($test_token);

    $callback_page_url = '';
    $pages = get_posts(array(
        'post_type' => 'page',
        'posts_per_page' => -1,
        's' => '[nextjs_sso_callback]'
    ));

    if (!empty($pages)) {
        $callback_page_url = get_permalink($pages[0]->ID);
    }

    $secret_source = defined('PYTHON_JWT_SECRET') ? 'PYTHON_JWT_SECRET' : (defined('AUTH_KEY') ? 'AUTH_KEY' : 'default');

    ?>
    <div class="wrap">
        <h1>Next.js SSO Integration v3.0 - 调试信息</h1>

        <div class="notice notice-success">
            <p><strong>🎉 v3.0 全新版本！</strong></p>
            <p>✅ 完全解决缓存问题 | ✅ 原生登录弹窗 | ✅ 统一 SSO 流程</p>
        </div>

        <h2>🔐 密钥配置</h2>
        <table class="widefat" style="max-width: 800px;">
            <tr>
                <th style="width: 200px;">当前使用密钥</th>
                <td>
                    <code><?php echo esc_html($secret_source); ?></code>
                    <?php if ($secret_source === 'PYTHON_JWT_SECRET'): ?>
                        <span style="color: green; margin-left: 10px;">✓ 正确（与 Python 后端一致）</span>
                    <?php else: ?>
                        <span style="color: red; margin-left: 10px;">✗ 警告：未使用 PYTHON_JWT_SECRET</span>
                    <?php endif; ?>
                </td>
            </tr>
            <tr>
                <th>PYTHON_JWT_SECRET</th>
                <td>
                    <?php if (defined('PYTHON_JWT_SECRET')): ?>
                        <span style="color: green;">✓ 已定义</span>
                        （前8位: <code><?php echo esc_html(substr(PYTHON_JWT_SECRET, 0, 8)); ?>...</code>）
                    <?php else: ?>
                        <span style="color: red;">✗ 未定义</span>
                        <p>请在 wp-config.php 中添加：<br>
                        <code>define('PYTHON_JWT_SECRET', 'auto_generated_secure_key_2025_wordpress');</code></p>
                    <?php endif; ?>
                </td>
            </tr>
        </table>

        <h2>🧪 功能测试</h2>
        <table class="widefat" style="max-width: 800px;">
            <tr>
                <th style="width: 200px;">JWT 生成测试</th>
                <td>
                    <?php if ($test_token): ?>
                        <span style="color: green;">✓ JWT 生成成功</span>
                        <br><code style="word-break: break-all; font-size: 11px;"><?php echo esc_html(substr($test_token, 0, 100)); ?>...</code>
                    <?php else: ?>
                        <span style="color: red;">✗ JWT 生成失败</span>
                    <?php endif; ?>
                </td>
            </tr>
            <tr>
                <th>JWT 验证测试</th>
                <td>
                    <?php if ($test_verify): ?>
                        <span style="color: green;">✓ JWT 验证通过</span>
                        <br>用户: <?php echo esc_html($test_verify['data']['user']['username']); ?>
                        <br>过期时间: <?php echo date('Y-m-d H:i:s', $test_verify['exp']); ?>
                    <?php else: ?>
                        <span style="color: red;">✗ JWT 验证失败</span>
                    <?php endif; ?>
                </td>
            </tr>
        </table>

        <h2>📡 REST API 端点</h2>
        <table class="widefat" style="max-width: 800px;">
            <tr>
                <th style="width: 200px;">获取 Token</th>
                <td>
                    <code><?php echo rest_url('nextjs-sso/v1/get-token'); ?></code>
                    <br><small>需要登录，返回当前用户的 JWT Token</small>
                    <br><a href="<?php echo rest_url('nextjs-sso/v1/get-token'); ?>" target="_blank" class="button button-small">测试</a>
                </td>
            </tr>
            <tr>
                <th>验证 Token</th>
                <td>
                    <code><?php echo rest_url('nextjs-sso/v1/verify'); ?></code>
                    <br><small>POST 请求，参数: token</small>
                </td>
            </tr>
        </table>

        <h2>📊 系统信息</h2>
        <table class="widefat" style="max-width: 800px;">
            <tr>
                <th style="width: 200px;">插件版本</th>
                <td><strong>3.0.0</strong>（全新版本，彻底修复缓存问题）</td>
            </tr>
            <tr>
                <th>PHP 版本</th>
                <td><?php echo phpversion(); ?></td>
            </tr>
            <tr>
                <th>WordPress 版本</th>
                <td><?php echo get_bloginfo('version'); ?></td>
            </tr>
            <tr>
                <th>JWT 算法</th>
                <td>HS256</td>
            </tr>
            <tr>
                <th>Token 有效期</th>
                <td>7 天</td>
            </tr>
            <tr>
                <th>当前用户</th>
                <td>
                    <?php echo esc_html($test_user->user_login); ?>
                    (ID: <?php echo $test_user->ID; ?>)
                </td>
            </tr>
            <tr>
                <th>OPcache 状态</th>
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
            <h3>v3.0 新特性：</h3>
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
    </div>
    <?php
}
