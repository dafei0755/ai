'use client';

/**
 * 全局认证上下文
 * 管理用户登录状态、Token、自动跳转等
 * 
 * 🆕 v3.0.24: 支持设备绑定，限制多设备同时登录
 */

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
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

/**
 * 🆕 v3.0.24: 生成或获取设备唯一标识
 * 使用 localStorage 持久化，确保同一浏览器使用相同的设备 ID
 */
function getOrCreateDeviceId(): string {
  const DEVICE_ID_KEY = 'wp_device_id';
  let deviceId = localStorage.getItem(DEVICE_ID_KEY);
  
  if (!deviceId) {
    // 生成新的设备 ID：使用随机 UUID + 时间戳
    deviceId = `${crypto.randomUUID()}-${Date.now()}`;
    localStorage.setItem(DEVICE_ID_KEY, deviceId);
    console.log('[AuthContext v3.0.24] 🆕 生成新设备ID:', deviceId.substring(0, 16) + '...');
  }
  
  return deviceId;
}

/**
 * 🆕 v3.0.24: 获取设备信息（浏览器、操作系统）
 */
function getDeviceInfo(): string {
  const ua = navigator.userAgent;
  let browser = 'Unknown';
  let os = 'Unknown';
  
  // 检测浏览器
  if (ua.includes('Chrome')) browser = 'Chrome';
  else if (ua.includes('Firefox')) browser = 'Firefox';
  else if (ua.includes('Safari')) browser = 'Safari';
  else if (ua.includes('Edge')) browser = 'Edge';
  
  // 检测操作系统
  if (ua.includes('Windows')) os = 'Windows';
  else if (ua.includes('Mac')) os = 'macOS';
  else if (ua.includes('Linux')) os = 'Linux';
  else if (ua.includes('Android')) os = 'Android';
  else if (ua.includes('iPhone') || ua.includes('iPad')) os = 'iOS';
  
  return `${browser} on ${os}`;
}

/**
 * 辅助函数：保存Token并记录时间戳（v3.0.23新增）
 * 用于统一管理Token设置，避免时序冲突问题
 */
function saveTokenWithTimestamp(token: string, user: any) {
  localStorage.setItem('wp_jwt_token', token);
  localStorage.setItem('wp_jwt_user', JSON.stringify(user));
  localStorage.setItem('wp_jwt_token_timestamp', Date.now().toString());
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  // 🆕 v3.0.24: 检查设备是否被踢出
  const checkDeviceKicked = useCallback(async () => {
    const token = localStorage.getItem('wp_jwt_token');
    if (!token) return;
    
    const deviceId = getOrCreateDeviceId();
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    
    try {
      const response = await fetch(`${API_URL}/api/auth/check-device`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
          'X-Device-ID': deviceId
        },
        body: JSON.stringify({ device_id: deviceId })
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.status === 'kicked' || !data.valid) {
          console.log('[AuthContext v3.0.24] ⚠️ 设备已被踢出，跳转到被踢出页面');
          // 清除本地 Token
          localStorage.removeItem('wp_jwt_token');
          localStorage.removeItem('wp_jwt_user');
          localStorage.removeItem('wp_jwt_token_timestamp');
          setUser(null);
          // 跳转到被踢出提示页面
          router.push('/auth/kicked');
        }
      }
    } catch (error) {
      // 静默处理错误
      console.debug('[AuthContext v3.0.24] 设备检查失败:', error);
    }
  }, [router]);

  // 🆕 v3.0.24: 定期检查设备状态（每 30 秒）
  useEffect(() => {
    // 初始检查
    checkDeviceKicked();
    
    // 定期检查
    const interval = setInterval(checkDeviceKicked, 30000);
    
    return () => clearInterval(interval);
  }, [checkDeviceKicked]);

  // 🆕 v3.0.22增强版: 方案2 - REST API轮询（主要机制）+ 用户ID检测
  // 🔧 修复：移除方案3（Cookie轮询），因为localhost无法读取www.ucppt.com的Cookie（跨域限制）
  // 🔧 优化：增加定期轮询（每10秒），确保最终一致性
  // 🔥 v3.0.22新增：主动检测用户ID变化，即使没有event也能同步
  useEffect(() => {
    const checkSSOStatus = async () => {
      try {
        // 调用WordPress REST API检查SSO事件
        const response = await fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/sync-status', {
          method: 'GET',
          credentials: 'include',
          headers: { 'Accept': 'application/json' }
        });

        if (response.ok) {
          const data = await response.json();

          // 🔥 v3.0.22新增：检测用户ID是否变化（不依赖event字段）
          const localUserStr = localStorage.getItem('wp_jwt_user');
          const localUser = localUserStr ? JSON.parse(localUserStr) : null;
          const localUserId = localUser?.user_id;

          // 情况1：WordPress已登录，但本地用户ID不匹配 → 重新获取Token
          if (data.logged_in && data.user_id && localUserId !== data.user_id) {
            console.log('[AuthContext v3.0.22] ⚠️ 检测到用户切换');
            console.log('[AuthContext v3.0.22] 本地用户ID:', localUserId, '→ WordPress用户ID:', data.user_id);

            // 调用get-token API获取新Token
            try {
              const tokenResponse = await fetch('https://www.ucppt.com/wp-json/nextjs-sso/v1/get-token', {
                method: 'GET',
                credentials: 'include',
                headers: { 'Accept': 'application/json' }
              });

              if (tokenResponse.ok) {
                const tokenData = await tokenResponse.json();
                if (tokenData.token && tokenData.user) {
                  console.log('[AuthContext v3.0.23] ✅ 成功获取新用户Token');
                  console.log('[AuthContext v3.0.23] 新用户:', tokenData.user);

                  saveTokenWithTimestamp(tokenData.token, tokenData.user);
                  setUser(tokenData.user);

                  // 刷新页面以确保所有组件同步
                  window.location.reload();
                }
              }
            } catch (tokenError) {
              console.error('[AuthContext v3.0.22] ❌ 获取新Token失败:', tokenError);
            }
            return; // 已处理用户切换，跳过后续逻辑
          }

          // 情况2：WordPress已退出，但本地仍有用户 → 清除Token
          // 🔥 v3.0.23修复：增加时间窗口保护，避免在初始登录阶段误清除Token
          // 🔥 v3.0.24修复：跨域环境下跳过此检测（localhost无法正确发送Cookie到WordPress）
          if (!data.logged_in && localUserId) {
            // 🆕 v3.0.24: 检查是否在跨域开发环境
            const isLocalDev = window.location.hostname === 'localhost' || 
                               window.location.hostname === '127.0.0.1';
            
            if (isLocalDev) {
              // 在本地开发环境，跳过基于 sync-status 的退出检测
              // 因为跨域限制，WordPress Cookie 无法正确发送，API 始终返回 logged_in: false
              // 这会导致误清除 Token，用户被踢出登录
              console.log('[AuthContext v3.0.24] ⏳ 本地开发环境，跳过 WordPress 退出检测（跨域限制）');
              return;
            }
            
            // 检查Token设置时间，如果是最近30秒内设置的，可能是初始登录中，不清除
            const tokenTimestamp = localStorage.getItem('wp_jwt_token_timestamp');
            const now = Date.now();
            const tokenAge = tokenTimestamp ? now - parseInt(tokenTimestamp) : Infinity;

            if (tokenAge > 30000) {
              // Token已存在超过30秒，确实是退出登录
              console.log('[AuthContext v3.0.23] ✅ 检测到WordPress已退出，清除本地Token');
              localStorage.removeItem('wp_jwt_token');
              localStorage.removeItem('wp_jwt_user');
              localStorage.removeItem('wp_jwt_token_timestamp');
              setUser(null);
              return;
            } else {
              // Token是最近设置的，可能是初始登录中，忽略此次检测
              console.log('[AuthContext v3.0.23] ⏳ Token最近设置，跳过退出检测（防止误清除）');
            }
          }

          // 情况3：检测到登录事件（兼容旧逻辑）
          if (data.event === 'user_login' && data.token) {
            console.log('[AuthContext v3.0.23] ✅ 检测到WordPress登录事件（REST API）');
            console.log('[AuthContext v3.0.23] 新用户:', data.user);

            // 保存新Token
            saveTokenWithTimestamp(data.token, data.user);
            setUser(data.user);

            // 可选：刷新页面以确保所有组件同步
            // window.location.reload();
          }

          // 情况4：检测到退出事件（兼容旧逻辑）
          if (data.event === 'user_logout') {
            console.log('[AuthContext v3.0.22] ✅ 检测到WordPress退出事件（REST API）');

            // 清除本地Token
            localStorage.removeItem('wp_jwt_token');
            localStorage.removeItem('wp_jwt_user');
            setUser(null);

            // 可选：跳转到登录页面
            // window.location.href = '/';
          }
        }
      } catch (error) {
        // 静默处理错误（避免过多日志）
        if (error instanceof Error && error.message !== 'Failed to fetch') {
          console.error('[AuthContext v3.0.22] ❌ SSO状态检测失败:', error);
        }
      }
    };

    // 1. 页面可见性变化时检测（即时响应）
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        console.log('[AuthContext v3.0.21] 📄 页面重新可见，检测SSO状态');
        checkSSOStatus();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // 2. 定期轮询（每10秒，确保最终一致性）
    const pollInterval = setInterval(() => {
      // 静默轮询（不输出日志，避免控制台噪音）
      checkSSOStatus();
    }, 10000);

    // 3. 初始检测
    checkSSOStatus();

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      clearInterval(pollInterval);
    };
  }, []);

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
          console.log('[AuthContext v3.0.23] 📨 收到 WordPress 的 Token (postMessage):', event.data.type);

          // 保存 Token 和用户信息
          if (ssoUser) {
            saveTokenWithTimestamp(token, ssoUser);
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
        if (pathname !== '/auth/login' && pathname !== '/auth/callback' && pathname !== '/auth/login/manual' && pathname !== '/auth/logout' && pathname !== '/auth/kicked') {
          // 🆕 v3.0.12: 优先检查 URL 参数中的 sso_token（支持独立窗口模式）
          const urlParams = new URLSearchParams(window.location.search);
          const urlToken = urlParams.get('sso_token');

          if (urlToken) {
            console.log('[AuthContext] ✅ 从 URL 参数获取到 Token（独立模式），正在验证...');
            try {
              // 验证 Token
              const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
              // 🆕 v3.0.24: 发送设备信息
              const deviceId = getOrCreateDeviceId();
              const deviceInfo = getDeviceInfo();
              const verifyResponse = await fetch(`${API_URL}/api/auth/verify`, {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'Authorization': `Bearer ${urlToken}`,
                  'X-Device-ID': deviceId
                },
                body: JSON.stringify({ device_id: deviceId, device_info: deviceInfo })
              });

              console.log('[AuthContext] Token 验证状态:', verifyResponse.status);

              if (verifyResponse.ok) {
                const verifyData = await verifyResponse.json();
                console.log('[AuthContext v3.0.23] ✅ SSO 登录成功（独立模式），用户:', verifyData.user);

                // 保存 Token 和用户信息
                saveTokenWithTimestamp(urlToken, verifyData.user);
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
                // 🆕 v3.0.24: 发送设备信息
                const deviceId = getOrCreateDeviceId();
                const deviceInfo = getDeviceInfo();
                const verifyResponse = await fetch(`${API_URL}/api/auth/verify`, {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${urlToken2}`,
                    'X-Device-ID': deviceId
                  },
                  body: JSON.stringify({ device_id: deviceId, device_info: deviceInfo })
                });

                console.log('[AuthContext] Token 验证状态:', verifyResponse.status);

                if (verifyResponse.ok) {
                  const verifyData = await verifyResponse.json();
                  console.log('[AuthContext v3.0.23] ✅ SSO 登录成功（URL Token），用户:', verifyData.user);

                  // 保存 Token 和用户信息
                  saveTokenWithTimestamp(urlToken2, verifyData.user);
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
                  // 🆕 v3.0.24: 发送设备信息
                  const deviceId = getOrCreateDeviceId();
                  const deviceInfo = getDeviceInfo();
                  const verifyResponse = await fetch(`${API_URL}/api/auth/verify`, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      'Authorization': `Bearer ${data.token}`,
                      'X-Device-ID': deviceId
                    },
                    body: JSON.stringify({ device_id: deviceId, device_info: deviceInfo })
                  });

                  console.log('[AuthContext] Token 验证状态:', verifyResponse.status);

                  if (verifyResponse.ok) {
                    const verifyData = await verifyResponse.json();
                    console.log('[AuthContext v3.0.23] ✅ SSO 登录成功（REST API），用户:', verifyData.user);

                    // 保存 Token 和用户信息
                    saveTokenWithTimestamp(data.token, verifyData.user);
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
                // 🆕 v3.0.24: 发送设备信息（缓存 Token 验证也需要）
                const deviceId = getOrCreateDeviceId();
                const deviceInfo = getDeviceInfo();
                const verifyResponse = await fetch(`${API_URL}/api/auth/verify`, {
                  method: 'POST',
                  headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${cachedToken}`,
                    'X-Device-ID': deviceId
                  },
                  body: JSON.stringify({ device_id: deviceId, device_info: deviceInfo })
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
                  // 🆕 v3.0.24: 发送设备信息
                  const deviceId = getOrCreateDeviceId();
                  const deviceInfo = getDeviceInfo();
                  const verifyResponse = await fetch(`${API_URL}/api/auth/verify`, {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                      'Authorization': `Bearer ${data.token}`,
                      'X-Device-ID': deviceId
                    },
                    body: JSON.stringify({ device_id: deviceId, device_info: deviceInfo })
                  });

                  if (verifyResponse.ok) {
                    const verifyData = await verifyResponse.json();
                    console.log('[AuthContext v3.0.23] ✅ REST API Token 验证成功，用户:', verifyData.user);

                    // 保存 Token 和用户信息
                    saveTokenWithTimestamp(data.token, verifyData.user);
                    setUser(verifyData.user);
                    setIsLoading(false);

                    // 🎯 v3.0.15: 已登录用户自动跳转到分析页面
                    console.log('[AuthContext v3.0.23] 🔀 检测到已登录，跳转到分析页面');
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
  if (pathname === '/auth/login' || pathname === '/auth/callback' || pathname === '/auth/login/manual' || pathname === '/auth/logout' || pathname === '/auth/kicked') {
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
