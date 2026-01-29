'use client';

/**
 * 登录页面（自动跳转到 WPCOM 用户中心 SSO）
 * 直接重定向到 WPCOM 用户中心登录，无需额外操作
 *
 * 🆕 v7.277: 开发模式跳过 SSO，直接使用测试用户
 */

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

// 🆕 v7.277: 开发模式配置
const DEV_MODE = process.env.NEXT_PUBLIC_DEV_MODE === 'true';
const DEV_SKIP_AUTH = process.env.NEXT_PUBLIC_DEV_SKIP_AUTH === 'true';

export default function LoginPage() {
  const router = useRouter();

  // 页面加载时自动跳转到 WordPress 嵌入页面
  useEffect(() => {
    // 🆕 v7.277: 开发模式跳过 SSO
    if (DEV_MODE && DEV_SKIP_AUTH) {
      console.log('[LoginPage v7.277] 🔧 开发模式：跳过 SSO，直接进入首页');
      router.push('/');
      return;
    }

    const wordpressEmbedUrl = 'https://www.ucppt.com/nextjs';

    // 立即跳转
    window.location.href = wordpressEmbedUrl;
  }, [router]);

  // 🆕 v7.277: 开发模式显示不同的内容
  if (DEV_MODE && DEV_SKIP_AUTH) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-400 to-red-500 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-2xl p-8 w-full max-w-md text-center">
          <div className="mb-6">
            <div className="text-5xl mb-4">🔧</div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              开发模式
            </h1>
            <p className="text-gray-600">
              正在跳过登录验证...
            </p>
          </div>
        </div>
      </div>
    );
  }

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
