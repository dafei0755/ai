'use client';

/**
 * 手动登录页面（备用入口）
 * 仅供特殊情况使用，正常流程直接使用 SSO
 */

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { loginWithWordPress } from '@/lib/wp-auth';
import Link from 'next/link';

export default function ManualLoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const result = await loginWithWordPress(username, password);

      if (result.status === 'success') {
        setSuccess(`✅ 登录成功！欢迎 ${result.user?.name || result.user?.username}`);
        
        // 延迟 1 秒后跳转到首页
        setTimeout(() => {
          router.push('/');
        }, 1000);
      } else {
        setError(result.message || '登录失败，请重试');
      }
    } catch (err) {
      setError('发生错误，请稍后重试');
      console.error('登录异常:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 w-full max-w-md">
        {/* 标题 */}
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            手动登录
          </h1>
          <p className="text-gray-600">
            使用 WordPress 用户名和密码登录
          </p>
          
          {/* 警告提示 */}
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-yellow-700 text-sm">
              ⚠️ 这是备用登录入口，推荐使用 
              <Link href="/" className="text-blue-600 hover:underline ml-1">
                SSO 单点登录
              </Link>
            </p>
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}

        {/* 成功提示 */}
        {success && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-green-700 text-sm">{success}</p>
          </div>
        )}

        {/* 登录表单 */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* 用户名输入 */}
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
              用户名
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="输入 WordPress 用户名"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
              disabled={loading}
              required
            />
          </div>

          {/* 密码输入 */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
              密码
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="输入密码"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
              disabled={loading}
              required
            />
          </div>

          {/* 登录按钮 */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-medium py-2 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg
                  className="animate-spin h-5 w-5 mr-2"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                登录中...
              </span>
            ) : (
              '登 录'
            )}
          </button>
        </form>

        {/* 返回链接 */}
        <div className="mt-6 text-center">
          <Link 
            href="/" 
            className="text-blue-600 hover:text-blue-700 text-sm font-medium"
          >
            ← 返回首页（使用 SSO 登录）
          </Link>
        </div>

        {/* 信息提示 */}
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-blue-700 text-sm mb-2">
            💡 <strong>为什么推荐 SSO？</strong>
          </p>
          <ul className="text-blue-600 text-xs space-y-1 list-disc list-inside">
            <li>无需重复输入密码</li>
            <li>已登录主站自动认证（~1秒）</li>
            <li>更安全，Token 自动管理</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
