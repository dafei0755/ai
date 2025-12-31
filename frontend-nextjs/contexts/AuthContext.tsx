'use client';

/**
 * 全局认证上下文
 * 管理用户登录状态、Token、自动跳转等
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { getCurrentUser, isAuthenticated, clearWPToken } from '@/lib/wp-auth';

interface User {
  user_id: number;
  username: string;
  name?: string;
  email?: string;
  display_name?: string;
  avatar_url?: string;
  roles?: string[];
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  logout: () => void;
  refreshUser: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  // 🆕 v3.0.5: 监听来自 WordPress 父页面的 postMessage（Token 同步）
  useEffect(() => {
    const handlePostMessage = (event: MessageEvent) => {
      // 🔒 安全检查：只接受来自 WordPress 主站的消息
      const allowedOrigins = [
        'https://www.ucppt.com',
        'https://ucppt.com',
        'http://localhost',
        'http://127.0.0.1',
      ];

      const isAllowedOrigin = allowedOrigins.some(origin => event.origin.startsWith(origin));

      if (!isAllowedOrigin) {
        return;
      }

      // 处理 SSO 登录消息
      if (event.data && (event.data.type === 'sso_login' || event.data.type === 'sso_sync')) {
        const { token, user: ssoUser } = event.data;

        if (token) {
          console.log('[AuthContext] 📨 收到 WordPress 的 Token (postMessage):', event.data.type);

          // 保存 Token 和用户信息
          localStorage.setItem('wp_jwt_token', token);
          if (ssoUser) {
            localStorage.setItem('wp_jwt_user', JSON.stringify(ssoUser));
            setUser(ssoUser);
          }
          setIsLoading(false);
        }
      }

      // 🆕 v3.0.6: 处理 WordPress 退出登录消息
      if (event.data && event.data.type === 'sso_logout') {
        console.log('[AuthContext] 📨 收到 WordPress 退出登录通知 (postMessage)');

        // 清除本地Token和用户信息
        localStorage.removeItem('wp_jwt_token');
        localStorage.removeItem('wp_jwt_user');
        setUser(null);

        console.log('[AuthContext] ✅ 已清除 Token，用户已退出登录');
      }
    };

    // 添加 postMessage 监听器
    window.addEventListener('message', handlePostMessage);

    return () => {
      window.removeEventListener('message', handlePostMessage);
    };
  }, []);

  // 检查登录状态
  useEffect(() => {
    const checkAuth = async () => {
      setIsLoading(true);

      const authenticated = isAuthenticated();
      const currentUser = getCurrentUser();

      if (authenticated && currentUser) {
        setUser(currentUser);
        setIsLoading(false);
      } else {
        setUser(null);

        // 如果不在登录相关页面，尝试 SSO 登录
        if (pathname !== '/auth/login' && pathname !== '/auth/callback' && pathname !== '/auth/login/manual' && pathname !== '/auth/logout') {
          // 🆕 v3.0.12: 优先检查 URL 参数中的 sso_token（支持独立窗口模式）
          const urlParams = new URLSearchParams(window.location.search);
          const urlToken = urlParams.get('sso_token');

          if (urlToken) {
            console.log('[AuthContext] ✅ 从 URL 参数获取到 Token（独立模式），正在验证...');
            try {
              // 验证 Token
              const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
              const verifyResponse = await fetch(`${API_URL}/api/auth/verify`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${urlToken}`
                }
              });

              console.log('[AuthContext] Token 验证状态:', verifyResponse.status);

              if (verifyResponse.ok) {
                const verifyData = await verifyResponse.json();
                console.log('[AuthContext] ✅ SSO 登录成功（独立模式），用户:', verifyData.user);

                // 保存 Token 和用户信息
                localStorage.setItem('wp_jwt_token', urlToken);
                localStorage.setItem('wp_jwt_user', JSON.stringify(verifyData.user));
                setUser(verifyData.user);
                setIsLoading(false);

                // 🔥 清除 URL 参数，避免 Token 暴露在地址栏
                urlParams.delete('sso_token');
                const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
                window.history.replaceState({}, '', newUrl);

                return; // SSO 成功，停止执行
              } else {
                const errorData = await verifyResponse.json().catch(() => ({}));
                console.error('[AuthContext] ❌ Token 验证失败（独立模式）:', errorData);
              }
            } catch (error) {
              console.error('[AuthContext] ❌ Token 验证异常（独立模式）:', error);
            }
          }

          // 🔥 检测是否在 iframe 中
          const isInIframe = window.self !== window.top;

          if (isInIframe) {
            // 🔥 在 iframe 中：尝试从 URL 参数或 WordPress SSO 端点获取 Token
            try {
              console.log('[AuthContext] 🔍 正在尝试 SSO 登录（iframe模式）...');

              // 🆕 v3.0.1: 从 URL 参数读取 Token（WordPress 插件直接传递）
              const urlToken2 = urlParams.get('sso_token');

              if (urlToken2) {
                console.log('[AuthContext] ✅ 从 URL 参数获取到 Token（iframe模式），正在验证...');

                // 验证 Token
                const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
                const verifyResponse = await fetch(`${API_URL}/api/auth/verify`, {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${urlToken2}`
                  }
                });

                console.log('[AuthContext] Token 验证状态:', verifyResponse.status);

                if (verifyResponse.ok) {
                  const verifyData = await verifyResponse.json();
                  console.log('[AuthContext] ✅ SSO 登录成功（URL Token），用户:', verifyData.user);

                  // 保存 Token 和用户信息
                  localStorage.setItem('wp_jwt_token', urlToken2);
                  localStorage.setItem('wp_jwt_user', JSON.stringify(verifyData.user));
                  setUser(verifyData.user);
                  setIsLoading(false);

                  // 🔥 清除 URL 参数，避免 Token 暴露在地址栏
                  urlParams.delete('sso_token');
                  const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
                  window.history.replaceState({}, '', newUrl);

                  return; // SSO 成功，停止执行
                } else {
                  const errorData = await verifyResponse.json().catch(() => ({}));
                  console.error('[AuthContext] ❌ Token 验证失败（URL Token）:', errorData);
                }
              }

              // 🆕 v3.0.1: 如果 URL 没有 Token，回退到 REST API 方式（保持兼容性）
              console.log('[AuthContext] URL 无 Token，尝试 REST API 获取...');
              const response = await fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
                method: 'GET',
                credentials: 'include', // 发送 WordPress Cookie
              });

              console.log('[AuthContext] SSO 响应状态:', response.status);

              if (response.ok) {
                const data = await response.json();
                console.log('[AuthContext] SSO 响应数据:', { success: data.success, hasToken: !!data.token, user: data.user });

                if (data.success && data.token) {
                  // 验证并保存 Token
                  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
                  console.log('[AuthContext] 验证 Token 中...');
                  const verifyResponse = await fetch(`${API_URL}/api/auth/verify`, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      'Authorization': `Bearer ${data.token}`
                    }
                  });

                  console.log('[AuthContext] Token 验证状态:', verifyResponse.status);

                  if (verifyResponse.ok) {
                    const verifyData = await verifyResponse.json();
                    console.log('[AuthContext] ✅ SSO 登录成功（REST API），用户:', verifyData.user);

                    // ⚠️ 修复：使用正确的 localStorage key (wp_jwt_user 而不是 wp_user)
                    localStorage.setItem('wp_jwt_token', data.token);
                    localStorage.setItem('wp_jwt_user', JSON.stringify(verifyData.user));
                    setUser(verifyData.user);
                    setIsLoading(false);
                    return; // SSO 成功，停止执行
                  } else {
                    const errorData = await verifyResponse.json().catch(() => ({}));
                    console.error('[AuthContext] ❌ Token 验证失败（REST API）:', errorData);
                  }
                } else {
                  console.warn('[AuthContext] ⚠️ SSO 响应无效（无 Token）');
                }
              } else {
                const errorText = await response.text().catch(() => 'Unknown error');
                console.error('[AuthContext] ❌ SSO 请求失败:', response.status, errorText);
              }

              // 如果 API 返回 401，说明 WordPress 未登录
              // 不做任何操作，让父页面处理（WordPress 会显示登录引导）
              setIsLoading(false);
            } catch (error) {
              console.error('[AuthContext] ❌ 自动 SSO 异常:', error);
              setIsLoading(false);
            }
          } else {
            // 🔥 不在 iframe 中：检查是否有缓存的 Token
            const cachedToken = localStorage.getItem('wp_jwt_token');
            const cachedUser = localStorage.getItem('wp_jwt_user');

            if (cachedToken && cachedUser) {
              console.log('[AuthContext] 发现缓存的 Token，尝试验证...');
              try {
                const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
                const verifyResponse = await fetch(`${API_URL}/api/auth/verify`, {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${cachedToken}`
                  }
                });

                if (verifyResponse.ok) {
                  const verifyData = await verifyResponse.json();
                  console.log('[AuthContext] ✅ 缓存 Token 有效，用户:', verifyData.user);
                  setUser(verifyData.user);
                  setIsLoading(false);
                  return; // Token 有效，不需要跳转
                } else {
                  console.warn('[AuthContext] ⚠️ 缓存 Token 已失效');
                  // Token 失效，清除缓存
                  localStorage.removeItem('wp_jwt_token');
                  localStorage.removeItem('wp_jwt_user');
                }
              } catch (error) {
                console.error('[AuthContext] ❌ 验证缓存 Token 失败:', error);
              }
            }

            // 🆕 v3.0.15: 尝试通过 WordPress REST API 获取 Token
            // 如果用户已在 WordPress 登录，API 会返回 Token
            console.log('[AuthContext] 尝试通过 WordPress REST API 获取 Token...');
            try {
              const response = await fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
                method: 'GET',
                credentials: 'include', // 发送 WordPress Cookie
                headers: {
                  'Accept': 'application/json'
                }
              });

              if (response.ok) {
                const data = await response.json();
                if (data.success && data.token) {
                  console.log('[AuthContext] ✅ 通过 REST API 获取到 Token，验证中...');

                  // 验证 Token
                  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
                  const verifyResponse = await fetch(`${API_URL}/api/auth/verify`, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      'Authorization': `Bearer ${data.token}`
                    }
                  });

                  if (verifyResponse.ok) {
                    const verifyData = await verifyResponse.json();
                    console.log('[AuthContext] ✅ REST API Token 验证成功，用户:', verifyData.user);

                    // 保存 Token 和用户信息
                    localStorage.setItem('wp_jwt_token', data.token);
                    localStorage.setItem('wp_jwt_user', JSON.stringify(verifyData.user));
                    setUser(verifyData.user);
                    setIsLoading(false);

                    // 🎯 v3.0.15: 已登录用户自动跳转到分析页面
                    console.log('[AuthContext] 🔀 检测到已登录，跳转到分析页面');
                    router.push('/analysis');
                    return;
                  }
                }
              }

              // REST API 返回 401 或其他错误，说明未登录
              console.log('[AuthContext] WordPress 未登录，将显示登录界面');
            } catch (error) {
              console.error('[AuthContext] ❌ REST API 调用失败:', error);
            }

            // 🔥 v3.0.8: 不在 iframe 中且没有有效 Token
            // 不再自动跳转，让 app/page.tsx 显示登录提示界面
            console.log('[AuthContext] 无有效登录状态，将显示登录提示界面');
            setIsLoading(false);
            return; // 停止执行，不跳转
          }
        } else {
          setIsLoading(false);
        }
      }
    };

    checkAuth();
  }, [pathname, router]);

  const logout = () => {
    clearWPToken();
    setUser(null);
    // 退出登录后跳转到退出成功页面
    // 该页面不会触发自动 SSO，用户可以选择重新登录或彻底退出
    window.location.href = '/auth/logout';
  };

  const refreshUser = () => {
    const currentUser = getCurrentUser();
    setUser(currentUser);
  };

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    logout,
    refreshUser,
  };

  // 登录相关页面不需要等待加载（回调页面、手动登录页面、退出页面）
  if (pathname === '/auth/login' || pathname === '/auth/callback' || pathname === '/auth/login/manual' || pathname === '/auth/logout') {
    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
  }

  // 其他页面等待认证检查完成
  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--background)] flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-blue-500 border-r-transparent"></div>
          <p className="mt-4 text-[var(--foreground-secondary)]">加载中...</p>
        </div>
      </div>
    );
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
