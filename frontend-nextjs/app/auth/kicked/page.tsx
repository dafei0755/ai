'use client';

/**
 * 被踢出提示页面
 * 当用户在其他设备登录时，当前设备会被踢出并跳转到此页面
 * 
 * v3.0.24 新增
 */

import { useEffect } from 'react';
import Link from 'next/link';
import { MonitorSmartphone, LogIn, Home } from 'lucide-react';

export default function KickedPage() {
  // 清除本地存储的 Token（确保用户需要重新登录）
  useEffect(() => {
    localStorage.removeItem('wp_jwt_token');
    localStorage.removeItem('wp_jwt_user');
    localStorage.removeItem('wp_jwt_token_timestamp');
  }, []);

  return (
    <div className="min-h-screen bg-[var(--background)] flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-[var(--card-bg)] rounded-2xl shadow-xl p-8 text-center">
        {/* 图标 */}
        <div className="w-20 h-20 mx-auto mb-6 bg-orange-500/20 rounded-full flex items-center justify-center">
          <MonitorSmartphone className="w-10 h-10 text-orange-500" />
        </div>

        {/* 标题 */}
        <h1 className="text-2xl font-bold text-[var(--foreground)] mb-3">
          账号已在其他设备登录
        </h1>

        {/* 说明 */}
        <p className="text-[var(--foreground-secondary)] mb-6">
          为了保护您的账号安全，同一账号只能在一台设备上登录。
          <br />
          如果这不是您的操作，请立即修改密码。
        </p>

        {/* 提示框 */}
        <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4 mb-6">
          <p className="text-sm text-orange-400">
            💡 如需在此设备继续使用，请重新登录
          </p>
        </div>

        {/* 操作按钮 */}
        <div className="space-y-3">
          <a
            href="https://www.ucppt.com/login"
            className="w-full inline-flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            <LogIn className="w-5 h-5" />
            重新登录
          </a>

          <Link
            href="/"
            className="w-full inline-flex items-center justify-center gap-2 px-6 py-3 bg-[var(--background)] hover:bg-[var(--hover-bg)] text-[var(--foreground-secondary)] rounded-lg transition-colors border border-[var(--border-color)]"
          >
            <Home className="w-5 h-5" />
            返回首页
          </Link>
        </div>

        {/* 底部说明 */}
        <p className="mt-6 text-xs text-[var(--foreground-secondary)]">
          如有疑问，请联系客服
        </p>
      </div>
    </div>
  );
}
