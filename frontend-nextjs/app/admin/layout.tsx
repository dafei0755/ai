'use client';

import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';

const navItems = [
  { href: '/admin/dashboard', icon: '📊', label: '仪表板' },
  { href: '/admin/monitoring', icon: '📈', label: '系统监控' },
  { href: '/admin/database', icon: '🗄️', label: '数据库监控' },
  { href: '/admin/sessions', icon: '💬', label: '会话管理' },
  { href: '/admin/conversations', icon: '💭', label: '对话分析' },
  { href: '/admin/users', icon: '👥', label: '用户分析' },
  { href: '/admin/tools', icon: '🔍', label: '搜索工具' },
  { href: '/admin/search-filters', icon: '🛡️', label: '搜索过滤器' },
  { href: '/admin/knowledge-base', icon: '📚', label: '知识库管理' },
  { href: '/admin/knowledge-assets', icon: '🧾', label: '知识资产审核' },
  { href: '/admin/review-queue', icon: '✅', label: '治理复核中心' },
  { href: '/admin/capability-boundary', icon: '⚠️', label: '能力边界监控' },
  { href: '/admin/concept-maps', icon: '🎨', label: '概念图' },
  { href: '/admin/dimension-learning', icon: '🧠', label: '维度学习' },
  { href: '/admin/learning-center', icon: '🔁', label: '自学习中心' },
  { href: '/admin/project-types', icon: '🏷️', label: '空间分类' },
  { href: '/admin/ontology', icon: '🧬', label: '本体论' },
  { href: '/admin/ontology/review', icon: '✅', label: '本体论扩展审核' },
];

const showcaseItems = [
  { href: '/showcase', icon: '🎯', label: '展示页面', external: true },
  { href: '/admin/showcase-config', icon: '⚙️', label: '展示配置' },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isLoading, isAuthenticated, logout } = useAuth();

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-100">
        <div className="text-center">
          <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600" />
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex h-screen items-center justify-center bg-gradient-to-br from-blue-500 to-purple-600">
        <div className="max-w-md rounded-lg bg-white p-8 text-center shadow-2xl">
          <div className="mb-6">
            <div className="mb-4 text-6xl">🔐</div>
            <h1 className="mb-2 text-2xl font-bold text-gray-900">需要管理员权限</h1>
            <p className="mb-6 text-gray-600">访问管理后台需要使用方案高参管理员账号登录。</p>
          </div>

          <div className="space-y-4">
            <Link
              href="/auth/login"
              className="block w-full rounded-lg bg-blue-600 px-6 py-3 font-medium text-white transition-colors hover:bg-blue-700"
            >
              前往内部登录
            </Link>
            <Link
              href="/"
              className="block w-full rounded-lg bg-gray-200 px-6 py-3 font-medium text-gray-700 transition-colors hover:bg-gray-300"
            >
              返回首页
            </Link>
          </div>

          <div className="mt-6 border-t border-gray-200 pt-6">
            <p className="text-sm text-gray-500">
              提示：当前已取消旧外部会员打通，后续由独立会员系统接管。
            </p>
          </div>
        </div>
      </div>
    );
  }

  const renderLink = (item: { href: string; icon: string; label: string; external?: boolean }) => {
    const className =
      'flex items-center rounded-lg px-4 py-2 text-gray-700 transition-colors hover:bg-blue-50 hover:text-blue-600';

    if (item.external) {
      return (
        <a
          key={item.href}
          href={item.href}
          target="_blank"
          rel="noopener noreferrer"
          className={className}
        >
          <span className="mr-3">{item.icon}</span>
          {item.label}
          <span className="ml-auto text-xs text-gray-400">↗</span>
        </a>
      );
    }

    return (
      <Link key={item.href} href={item.href} className={className}>
        <span className="mr-3">{item.icon}</span>
        {item.label}
      </Link>
    );
  };

  return (
    <div className="admin-layout flex h-screen bg-gray-100">
      <aside className="flex h-full w-64 flex-col bg-white shadow-lg">
        <div className="flex-shrink-0 border-b p-4">
          <h1 className="text-xl font-bold text-gray-800">管理后台</h1>
          <p className="mt-1 text-sm text-gray-500">System Admin</p>
        </div>

        <nav className="flex-1 overflow-y-auto p-4">
          <ul className="space-y-2">
            {navItems.map((item) => (
              <li key={item.href}>{renderLink(item)}</li>
            ))}
            <li className="mt-4 border-t pt-4">
              <div className="px-4 py-2 text-xs font-semibold uppercase text-gray-500">精选展示</div>
            </li>
            {showcaseItems.map((item) => (
              <li key={item.href}>{renderLink(item)}</li>
            ))}
          </ul>
        </nav>

        <div className="flex-shrink-0 border-t border-gray-200 p-4">
          <Link
            href="/"
            className="flex w-full items-center justify-center rounded-lg bg-gray-50 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-100"
          >
            <span className="mr-2">🏠</span>
            返回首页
          </Link>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <header className="border-b bg-white shadow-sm">
          <div className="flex items-center justify-between px-6 py-4">
            <h2 className="text-2xl font-semibold text-gray-800">管理员控制台</h2>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">{new Date().toLocaleDateString('zh-CN')}</span>
              <button
                onClick={logout}
                className="rounded-lg px-4 py-2 text-sm text-gray-700 transition-colors hover:bg-gray-100"
              >
                退出登录
              </button>
            </div>
          </div>
        </header>

        <div className="p-6">{children}</div>
      </main>
    </div>
  );
}
