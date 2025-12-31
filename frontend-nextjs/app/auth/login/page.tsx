'use client';

/**
 * 登录页面（自动跳转到 WPCOM 用户中心 SSO）
 * 直接重定向到 WPCOM 用户中心登录，无需额外操作
 */

import { useEffect } from 'react';
import Link from 'next/link';

export default function LoginPage() {
  // 页面加载时自动跳转到 WordPress 嵌入页面
  useEffect(() => {
    const wordpressEmbedUrl = 'https://www.ucppt.com/nextjs';

    // 立即跳转
    window.location.href = wordpressEmbedUrl;
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 w-full max-w-md text-center">
        {/* 跳转提示 */}
        <div className="mb-6">
          <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-blue-500 border-r-transparent mb-4"></div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            正在跳转到登录页面...
          </h1>
          <p className="text-gray-600">
            请稍候，即将跳转到 WPCOM 用户中心登录
          </p>
        </div>

        {/* 备用链接 */}
        <div className="pt-6 border-t border-gray-200">
          <p className="text-sm text-gray-500 mb-2">如果没有自动跳转：</p>
          <Link 
            href="/auth/login/manual" 
            className="text-blue-600 hover:text-blue-700 font-medium text-sm"
          >
            使用密码登录 →
          </Link>
        </div>
      </div>
    </div>
  );
}
