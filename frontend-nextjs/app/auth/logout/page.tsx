'use client';

/**
 * 退出登录成功页面
 * 提示用户已退出，并提供重新登录选项
 */

import { LogOut, Home, ExternalLink } from 'lucide-react';

export default function LogoutSuccessPage() {
  const handleRelogin = () => {
    // 跳转到 WordPress 嵌入页面（WordPress 已登录用户会自动重新登录）
    window.location.href = 'https://www.ucppt.com/nextjs';
  };

  const handleWordPressLogout = () => {
    // 跳转到 WordPress 登出页面（彻底退出）
    window.location.href = 'https://www.ucppt.com/wp-login.php?action=logout';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-500 to-red-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-2xl p-8 w-full max-w-md">
        <div className="text-center">
          {/* 图标 */}
          <div className="mx-auto w-20 h-20 bg-orange-100 rounded-full flex items-center justify-center mb-4">
            <LogOut className="w-10 h-10 text-orange-600" />
          </div>

          {/* 标题 */}
          <h1 className="text-2xl font-bold text-gray-900 mb-2">退出成功</h1>
          <p className="text-gray-600 mb-6">您已成功退出极致概念 AI 设计高参</p>

          {/* 提示信息 */}
          <div className="bg-blue-50 rounded-lg p-4 mb-6">
            <p className="text-sm text-blue-800">
              您已退出 Next.js 应用
            </p>
            <p className="text-xs text-blue-600 mt-1">
              如需彻底退出，请在 WordPress 也执行登出操作
            </p>
          </div>

          {/* 返回登录引导页按钮 */}
          <button
            onClick={handleRelogin}
            className="w-full bg-orange-600 hover:bg-orange-700 text-white font-medium py-3 px-6 rounded-lg transition-colors flex items-center justify-center space-x-2 mb-3"
          >
            <Home className="w-5 h-5" />
            <span>重新登录应用</span>
          </button>

          {/* WordPress 退出按钮 */}
          <button
            onClick={handleWordPressLogout}
            className="w-full bg-white hover:bg-gray-50 text-gray-700 border border-gray-300 font-medium py-3 px-6 rounded-lg transition-colors flex items-center justify-center space-x-2"
          >
            <ExternalLink className="w-5 h-5" />
            <span>在 WordPress 也退出登录</span>
          </button>

          {/* 返回主站链接 */}
          <a
            href="https://www.ucppt.com"
            className="inline-block mt-4 text-sm text-gray-500 hover:text-orange-600 transition-colors"
          >
            返回设计知外主站
          </a>
        </div>
      </div>
    </div>
  );
}
