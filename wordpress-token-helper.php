<?php
/*
Plugin Name: Next.js SSO Integration v3 - Token Generation Helper
Description: 为WPCOM隐藏区块提供Token生成短代码
Version: 1.0
*/

// 添加短代码：生成带Token的应用链接
function nextjs_sso_generate_app_link() {
    // 检查用户是否登录
    if (!is_user_logged_in()) {
        return ''; // 未登录不显示
    }

    // 获取当前用户
    $current_user = wp_get_current_user();

    // 生成Token（使用与REST API相同的逻辑）
    $user_data = array(
        'user_id' => $current_user->ID,
        'user_login' => $current_user->user_login,
        'user_email' => $current_user->user_email,
        'display_name' => $current_user->display_name,
        'timestamp' => time()
    );

    // JWT密钥（与插件中的一致）
    $secret_key = defined('JWT_AUTH_SECRET_KEY') ? JWT_AUTH_SECRET_KEY : AUTH_KEY;

    // 生成Token
    try {
        $token = \Firebase\JWT\JWT::encode($user_data, $secret_key, 'HS256');
    } catch (Exception $e) {
        error_log('[Next.js SSO] Token生成失败: ' . $e->getMessage());
        return '';
    }

    // 应用URL（开发/生产环境）
    $app_url = 'http://localhost:3000'; // 开发环境
    // $app_url = 'https://www.ucppt.com/nextjs'; // 生产环境

    // 生成带Token的链接
    $link_with_token = add_query_arg('sso_token', $token, $app_url);

    return $link_with_token;
}
add_shortcode('nextjs_app_link', 'nextjs_sso_generate_app_link');

// 添加短代码：完整的应用入口HTML
function nextjs_sso_app_entry_block() {
    if (!is_user_logged_in()) {
        return ''; // 未登录不显示
    }

    $app_link = nextjs_sso_generate_app_link();

    ob_start();
    ?>
    <div style="padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 16px; box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3); text-align: center; margin: 40px auto; max-width: 600px;">
        <div style="font-size: 48px; margin-bottom: 15px;">🎨</div>
        <h2 style="color: white; margin-bottom: 10px; font-size: 28px;">智能设计分析工具</h2>
        <p style="color: rgba(255,255,255,0.9); margin-bottom: 25px; font-size: 16px;">
            欢迎回来！您的专属AI设计助手已准备就绪
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
?>
