'use client';

/**
 * OAuth 回调处理页面
 * 接收 WordPress 登录后返回的 JWT Token
 */

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { setWPToken } from '@/lib/wp-auth';
import { Loader2, CheckCircle2, XCircle } from 'lucide-react';

export default function AuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing');
  const [message, setMessage] = useState('正在处理登录信息...');

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // 从 URL 参数获取 Token
        const token = searchParams.get('token');
        const error = searchParams.get('error');

        if (error) {
          setStatus('error');
          setMessage(decodeURIComponent(error));
          setTimeout(() => router.push('/auth/login'), 3000);
          return;
        }

        if (!token) {
          setStatus('error');
          setMessage('未接收到有效的登录凭证');
          setTimeout(() => router.push('/auth/login'), 3000);
          return;
        }

        // 验证 Token 并获取用户信息（调用 Python 后端）
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
        const response = await fetch(`${API_URL}/api/auth/verify`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        });

        if (!response.ok) {
          throw new Error('Token 验证失败');
        }

        const data = await response.json();

        // 保存 Token 和用户信息
        setWPToken(token, data.user);

        setStatus('success');
        setMessage(`欢迎回来，${data.user?.name || data.user?.username}！`);

        // 延迟跳转到首页
        setTimeout(() => {
          router.push('/');
        }, 1500);

      } catch (err) {
        console.error('❌ 登录回调处理失败:', err);
        setStatus('error');
        setMessage('登录处理失败，请重试');
        setTimeout(() => router.push('/auth/login'), 3000);
      }
    };

    handleCallback();
  }, [searchParams, router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 w-full max-w-md">
        <div className="text-center">
          {status === 'processing' && (
            <>
              <Loader2 className="w-16 h-16 mx-auto mb-4 text-blue-600 animate-spin" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">处理中</h2>
              <p className="text-gray-600">{message}</p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircle2 className="w-16 h-16 mx-auto mb-4 text-green-600" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">登录成功</h2>
              <p className="text-gray-600">{message}</p>
              <p className="text-sm text-gray-500 mt-2">正在跳转到首页...</p>
            </>
          )}

          {status === 'error' && (
            <>
              <XCircle className="w-16 h-16 mx-auto mb-4 text-red-600" />
              <h2 className="text-2xl font-bold text-gray-900 mb-2">登录失败</h2>
              <p className="text-gray-600">{message}</p>
              <p className="text-sm text-gray-500 mt-2">即将返回登录页...</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
