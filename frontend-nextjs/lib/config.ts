// 应用配置文件 - 统一管理外部链接和URL

/**
 * WordPress主站配置
 */
export const WORDPRESS_CONFIG = {
  // WordPress主站URL
  MAIN_URL: 'https://www.ucppt.com',

  // 返回网站链接（应用左上角"返回网站"按钮）
  RETURN_URL: 'https://www.ucppt.com/js',

  // 登录页面（WPCOM自定义登录，支持微信和手机短信登录）
  LOGIN_URL: 'https://www.ucppt.com/login',

  // 登出页面
  LOGOUT_URL: 'https://www.ucppt.com/account?action=logout',

  // WordPress嵌入页面（iframe入口）
  EMBED_URL: 'https://www.ucppt.com/nextjs',

  // 用户订单管理页面
  ORDERS_URL: 'https://www.ucppt.com/account/orders-list',

  // REST API基础URL
  REST_API_BASE: 'https://www.ucppt.com/wp-json/nextjs-sso/v1',
};

/**
 * API端点配置
 */
export const API_CONFIG = {
  // WordPress REST API端点
  WORDPRESS_GET_TOKEN: `${WORDPRESS_CONFIG.REST_API_BASE}/get-token`,
  WORDPRESS_VERIFY_TOKEN: `${WORDPRESS_CONFIG.REST_API_BASE}/verify`,
  WORDPRESS_CHECK_LOGIN: `${WORDPRESS_CONFIG.REST_API_BASE}/check-login`,

  // Python后端API端点
  PYTHON_BASE: process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000',
  PYTHON_VERIFY: '/api/auth/verify',
  PYTHON_ANALYSIS: '/api/analysis',
};

/**
 * 应用配置
 */
export const APP_CONFIG = {
  // 应用名称
  NAME: '极致概念 设计高参',

  // 应用描述
  DESCRIPTION: 'AI驱动的智能设计分析平台',

  // 版本号
  VERSION: '3.0.20',

  // 是否启用调试模式
  DEBUG: process.env.NODE_ENV === 'development',
};

/**
 * 获取带回调的登录URL
 * @param callbackUrl - 登录后返回的URL（默认为当前页面）
 */
export function getLoginUrl(callbackUrl?: string): string {
  const callback = callbackUrl || (typeof window !== 'undefined' ? window.location.href : '');
  return `${WORDPRESS_CONFIG.LOGIN_URL}?redirect_to=${encodeURIComponent(callback)}`;
}

/**
 * 获取带Token的应用URL
 * @param token - SSO Token
 * @param path - 应用路径（默认为根路径）
 */
export function getAppUrlWithToken(token: string, path: string = '/'): string {
  const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';
  return `${baseUrl}${path}?sso_token=${token}`;
}

export default {
  WORDPRESS: WORDPRESS_CONFIG,
  API: API_CONFIG,
  APP: APP_CONFIG,
  getLoginUrl,
  getAppUrlWithToken,
};
