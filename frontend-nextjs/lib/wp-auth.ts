// frontend-nextjs/lib/wp-auth.ts
/**
 * WordPress JWT 认证工具库
 * 处理登录、Token 管理、HTTP 请求附加认证信息
 */

const JWT_TOKEN_KEY = 'wp_jwt_token';
const JWT_USER_KEY = 'wp_jwt_user';
const TOKEN_EXPIRY_KEY = 'wp_jwt_expiry';

interface User {
  user_id: number;
  username: string;
  email?: string;
  name?: string;
  display_name?: string;
  avatar_url?: string;
  roles?: string[];
}

interface AuthResponse {
  status: 'success' | 'error';
  token?: string;
  user?: User;
  message?: string;
}

/**
 * 登录用户
 */
export async function loginWithWordPress(
  username: string,
  password: string
): Promise<AuthResponse> {
  try {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json();

    if (response.ok && data.token) {
      // 保存 Token 到本地存储
      setWPToken(data.token, data.user);
      return { status: 'success', token: data.token, user: data.user };
    }

    return {
      status: 'error',
      message: data.message || '登录失败，请检查用户名和密码',
    };
  } catch (error) {
    console.error('❌ 登录请求异常:', error);
    return { status: 'error', message: '网络连接失败' };
  }
}

/**
 * 保存 JWT Token 和用户信息
 */
export function setWPToken(token: string, user?: User): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(JWT_TOKEN_KEY, token);
    if (user) {
      localStorage.setItem(JWT_USER_KEY, JSON.stringify(user));
    }
    // 保存过期时间（7天后）
    const expiry = new Date().getTime() + 7 * 24 * 60 * 60 * 1000;
    localStorage.setItem(TOKEN_EXPIRY_KEY, expiry.toString());
  }
}

/**
 * 获取 JWT Token
 */
export function getWPToken(): string | null {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem(JWT_TOKEN_KEY);
    const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY);

    // 检查 Token 是否过期
    if (token && expiry && new Date().getTime() > parseInt(expiry)) {
      clearWPToken();
      return null;
    }

    return token;
  }
  return null;
}

/**
 * 获取当前用户信息
 */
export function getCurrentUser(): User | null {
  if (typeof window !== 'undefined') {
    const userJson = localStorage.getItem(JWT_USER_KEY);
    if (userJson) {
      try {
        return JSON.parse(userJson);
      } catch {
        return null;
      }
    }
  }
  return null;
}

/**
 * 检查用户是否已登录
 */
export function isAuthenticated(): boolean {
  return getWPToken() !== null;
}

/**
 * 清除 Token 和用户信息（登出）
 */
export function clearWPToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(JWT_TOKEN_KEY);
    localStorage.removeItem(JWT_USER_KEY);
    localStorage.removeItem(TOKEN_EXPIRY_KEY);
  }
}

/**
 * 刷新 Token
 */
export async function refreshWPToken(): Promise<boolean> {
  try {
    const token = getWPToken();
    if (!token) return false;

    const response = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await response.json();

    if (response.ok && data.token) {
      setWPToken(data.token, data.user);
      return true;
    }

    return false;
  } catch (error) {
    console.error('❌ Token 刷新失败:', error);
    return false;
  }
}

/**
 * 添加认证信息到 API 请求头
 */
export function getAuthHeaders(): Record<string, string> {
  const token = getWPToken();
  if (!token) {
    return {};
  }

  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

/**
 * 发送已认证的 API 请求（自动附加 Token）
 */
export async function authorizedFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers = {
    ...getAuthHeaders(),
    ...options.headers,
  };

  return fetch(url, {
    ...options,
    headers,
  });
}

/**
 * 使用 Token 刷新进行重试（如果 Token 过期）
 */
export async function fetchWithAuth(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  let response = await authorizedFetch(url, options);

  // 如果 401，尝试刷新 Token 并重试
  if (response.status === 401) {
    const refreshed = await refreshWPToken();
    if (refreshed) {
      response = await authorizedFetch(url, options);
    }
  }

  return response;
}
