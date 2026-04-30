'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, Sparkles, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';

/**
 * /search 页面 - 独立搜索入口
 *
 * v7.290: 提供干净的搜索界面，创建会话后跳转到 /search/[session_id]
 * 方案A架构：首页统一入口 + 独立搜索页（可选）
 */
export default function SearchPage() {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setError('请输入搜索内容');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      console.log('🔍 [搜索页] 创建搜索会话:', trimmedQuery);
      const data = await api.createSearchSession(trimmedQuery, true);

      if (data.success && data.session_id) {
        console.log('✅ [搜索页] 搜索会话创建成功，跳转到:', data.session_id);

        // 🆕 v7.290: 记录会话创建时间到 localStorage，用于区分新旧会话
        const recentSessionsJson = localStorage.getItem('recent_search_sessions');
        const recentSessions: Record<string, number> = recentSessionsJson ? JSON.parse(recentSessionsJson) : {};
        recentSessions[data.session_id] = Date.now();
        localStorage.setItem('recent_search_sessions', JSON.stringify(recentSessions));

        // 跳转到搜索结果页面
        router.push(`/search/${data.session_id}`);
      } else {
        setError('创建搜索会话失败，请重试');
        setIsLoading(false);
      }
    } catch (err) {
      console.error('❌ [搜索页] 创建搜索会话失败:', err);
      setError('网络错误，请重试');
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-50 dark:from-gray-900 dark:via-gray-900 dark:to-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-3xl">
        {/* Logo和标题 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-indigo-600 mb-4 shadow-lg">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            AI 深度搜索
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            从一代创业者的视角，给出设计概念
          </p>
        </div>

        {/* 搜索表单 */}
        <form onSubmit={handleSearch} className="relative">
          <div className="relative">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSearch(e);
                }
              }}
              placeholder="输入您的搜索查询...&#10;例如：从一代创业者的视角，给出设计概念：深圳湾海景别墅"
              disabled={isLoading}
              className="w-full px-6 py-4 pr-14 rounded-2xl border-2 border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:border-indigo-500 dark:focus:border-indigo-400 resize-none transition-all shadow-sm hover:shadow-md focus:shadow-lg"
              rows={4}
            />
            <button
              type="submit"
              disabled={isLoading || !query.trim()}
              className="absolute right-3 bottom-3 p-3 rounded-xl bg-gradient-to-r from-purple-500 to-indigo-600 hover:from-purple-600 hover:to-indigo-700 disabled:from-gray-300 disabled:to-gray-400 dark:disabled:from-gray-700 dark:disabled:to-gray-600 disabled:cursor-not-allowed text-white transition-all shadow-lg hover:shadow-xl disabled:shadow-none"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Search className="w-5 h-5" />
              )}
            </button>
          </div>

          {/* 错误提示 */}
          {error && (
            <div className="mt-3 px-4 py-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* 提示信息 */}
          <div className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
            按 <kbd className="px-2 py-1 rounded bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 font-mono text-xs">Enter</kbd> 搜索 ·{' '}
            <kbd className="px-2 py-1 rounded bg-gray-100 dark:bg-gray-800 border border-gray-300 dark:border-gray-700 font-mono text-xs">Shift + Enter</kbd> 换行
          </div>
        </form>

        {/* 示例查询 */}
        <div className="mt-8">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-3 flex items-center justify-center gap-2">
            <Sparkles className="w-4 h-4" />
            试试这些查询：
          </p>
          <div className="flex flex-wrap gap-2 justify-center">
            {[
              '深圳湾海景别墅设计理念',
              '现代简约风格住宅设计',
              '创业者办公空间规划',
              '文化与美学融合的室内设计'
            ].map((example) => (
              <button
                key={example}
                onClick={() => setQuery(example)}
                disabled={isLoading}
                className="px-4 py-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 text-gray-700 dark:text-gray-300 text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {example}
              </button>
            ))}
          </div>
        </div>

        {/* 返回首页链接 */}
        <div className="mt-8 text-center">
          <button
            onClick={() => router.push('/')}
            className="text-sm text-gray-500 dark:text-gray-400 hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          >
            ← 返回首页
          </button>
        </div>
      </div>
    </div>
  );
}
