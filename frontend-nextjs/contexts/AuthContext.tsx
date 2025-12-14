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
          // 🔥 检测是否在 iframe 中
          const isInIframe = window.self !== window.top;

          if (isInIframe) {
            // 🔥 在 iframe 中：尝试从 URL 参数或 WordPress SSO 端点获取 Token
            try {
              console.log('[AuthContext] 🔍 正在尝试 SSO 登录...');

              // 🆕 v3.0.1: 优先从 URL 参数读取 Token（WordPress 插件直接传递）
              const urlParams = new URLSearchParams(window.location.search);
              const urlToken = urlParams.get('sso_token');

              if (urlToken) {
                console.log('[AuthContext] ✅ 从 URL 参数获取到 Token，正在验证...');

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
                  console.log('[AuthContext] ✅ SSO 登录成功（URL Token），用户:', verifyData.user);

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
            // 🔥 不在 iframe 中：跳转到 WordPress 嵌入页面
            const wordpressEmbedUrl = process.env.NEXT_PUBLIC_WORDPRESS_EMBED_URL || 'https://www.ucppt.com/nextjs';
            window.location.href = wordpressEmbedUrl;
            return; // 阻止后续代码执行
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
