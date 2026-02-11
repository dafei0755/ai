'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // 检查用户是否登录并具有管理员权限
    const token = localStorage.getItem('wp_jwt_token');
    if (!token) {
      // 未登录：显示提示信息而不是自动跳转
      setIsLoading(false);
      setIsAuthenticated(false);
      return;
    }

    // TODO: 验证token并检查管理员角色
    // 这里应该调用后端API验证，暂时简化处理
    setIsAuthenticated(true);
    setIsLoading(false);
  }, [router]);

  // 加载中
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  // 未登录：显示提示
  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-blue-500 to-purple-600">
        <div className="bg-white rounded-lg shadow-2xl p-8 max-w-md text-center">
          <div className="mb-6">
            <div className="text-6xl mb-4">🔒</div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              需要管理员权限
            </h1>
            <p className="text-gray-600 mb-6">
              访问管理后台需要使用管理员账号登录
            </p>
          </div>

          <div className="space-y-4">
            <a
              href="https://www.ucppt.com/nextjs"
              className="block w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              前往 WordPress 登录
            </a>
            <Link
              href="/"
              className="block w-full px-6 py-3 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
            >
              返回首页
            </Link>
          </div>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-sm text-gray-500">
              💡 提示：需要具有 <code className="bg-gray-100 px-2 py-1 rounded">administrator</code> 角色的账号
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-100 admin-layout">
      {/* 侧边栏 */}
      <aside className="w-64 bg-white shadow-lg flex flex-col h-full">
        <div className="p-4 border-b flex-shrink-0">
          <h1 className="text-xl font-bold text-gray-800">管理后台</h1>
          <p className="text-sm text-gray-500 mt-1">System Admin</p>
        </div>

        <nav className="p-4 flex-1 overflow-y-auto">
          <ul className="space-y-2">
            <li>
              <Link
                href="/admin/dashboard"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">📊</span>
                仪表板
              </Link>
            </li>
            <li>
              <Link
                href="/admin/monitoring"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">📈</span>
                系统监控
              </Link>
            </li>
            <li>
              <Link
                href="/admin/database"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">🗄️</span>
                数据库监控
              </Link>
            </li>
            <li>
              <Link
                href="/admin/sessions"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">💬</span>
                会话管理
              </Link>
            </li>
            <li>
              <Link
                href="/admin/conversations"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">💬</span>
                对话分析
              </Link>
            </li>
            <li>
              <Link
                href="/admin/users"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">👥</span>
                用户分析
              </Link>
            </li>
            <li>
              <Link
                href="/admin/tools"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">🔍</span>
                搜索工具
              </Link>
            </li>
            <li>
              <Link
                href="/admin/search-filters"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">🛡️</span>
                搜索过滤器
              </Link>
            </li>
            <li>
              <Link
                href="/admin/knowledge-base"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">📚</span>
                知识库管理
              </Link>
            </li>
            <li>
              <Link
                href="/admin/capability-boundary"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">⚠️</span>
                能力边界监控
              </Link>
            </li>
            <li>
              <Link
                href="/admin/concept-maps"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">🎨</span>
                概念图
              </Link>
            </li>
            <li>
              <Link
                href="/admin/dimension-learning"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">🧠</span>
                维度学习
              </Link>
            </li>
            <li>
              <Link
                href="/admin/ontology"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">🔷</span>
                动态本体论
              </Link>
            </li>
            <li>
              <Link
                href="/admin/ontology/review"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">✅</span>
                本体论扩展审核
              </Link>
            </li>
            <li>
              <Link
                href="/admin/logs"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">📝</span>
                日志查看
              </Link>
            </li>
            <li>
              <Link
                href="/admin/config"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">⚙️</span>
                配置管理
              </Link>
            </li>
            <li className="pt-4 mt-4 border-t">
              <div className="px-4 py-2 text-xs font-semibold text-gray-500 uppercase">
                精选展示
              </div>
            </li>
            <li>
              <a
                href="/showcase"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">🎬</span>
                展示页面
                <span className="ml-auto text-xs text-gray-400">↗</span>
              </a>
            </li>
            <li>
              <Link
                href="/admin/showcase-config"
                className="flex items-center px-4 py-2 text-gray-700 hover:bg-blue-50 hover:text-blue-600 rounded-lg transition-colors"
              >
                <span className="mr-3">⚙️</span>
                展示配置
              </Link>
            </li>
          </ul>
        </nav>

        {/* 固定底部操作区 */}
        <div className="border-t border-gray-200 p-4 flex-shrink-0">
          <Link
            href="/"
            className="flex items-center justify-center w-full px-4 py-2 text-gray-700 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <span className="mr-2">🏠</span>
            返回首页
          </Link>
        </div>
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 overflow-y-auto">
        {/* 顶部栏 */}
        <header className="bg-white shadow-sm border-b">
          <div className="flex items-center justify-between px-6 py-4">
            <h2 className="text-2xl font-semibold text-gray-800">管理员控制台</h2>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                {new Date().toLocaleDateString('zh-CN')}
              </span>
              <button
                onClick={() => {
                  localStorage.removeItem('wp_jwt_token');
                  router.push('/auth/login');
                }}
                className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              >
                退出登录
              </button>
            </div>
          </div>
        </header>

        {/* 页面内容 */}
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
}
