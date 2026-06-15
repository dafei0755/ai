'use client';

import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';

interface TrendData {
  date?: string;
  week?: string;
  month?: string;
  year?: string;
  count: number;
}

interface TypeDist {
  type: string;
  count: number;
}

interface StatusDist {
  status: string;
  count: number;
}

interface Keyword {
  word: string;
  count: number;
}

interface ConversationsAnalyticsResponse {
  total_conversations: number;
  time_range_days: number;
  daily_trend: TrendData[];
  weekly_trend: TrendData[];
  monthly_trend: TrendData[];
  yearly_trend: TrendData[];
  type_distribution: TypeDist[];
  status_distribution: StatusDist[];
  top_keywords: Keyword[];
  timestamp: string;
}

export default function ConversationsPage() {
  const [stats, setStats] = useState<ConversationsAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<number>(30);
  const [trendView, setTrendView] = useState<'daily' | 'weekly' | 'monthly' | 'yearly'>('daily');

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('app_auth_token');
      if (!token) {
        setError('未登录，请先登录管理员账号');
        setLoading(false);
        return;
      }

      const response = await axios.get<ConversationsAnalyticsResponse>(
        `/api/admin/conversations/analytics?days=${timeRange}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      setStats(response.data);
    } catch (err: any) {
      console.error('获取对话分析失败:', err);
      setError(err.response?.data?.detail || '获取数据失败');
    } finally {
      setLoading(false);
    }
  }, [timeRange]);

  useEffect(() => {
    fetchStats();

    // 每60秒自动刷新
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // 状态显示名称映射
  const statusDisplayNames: Record<string, string> = {
    completed: '✅ 已完成',
    active: '⏳ 进行中',
    failed: '❌ 失败',
    pending: '⏸️ 等待中',
  };

  // 获取当前趋势数据
  const getCurrentTrendData = () => {
    if (!stats) return [];
    switch (trendView) {
      case 'daily':
        return stats.daily_trend;
      case 'weekly':
        return stats.weekly_trend;
      case 'monthly':
        return stats.monthly_trend;
      case 'yearly':
        return stats.yearly_trend;
      default:
        return stats.daily_trend;
    }
  };

  const getTrendLabel = (item: TrendData) => {
    if (item.date) return item.date;
    if (item.week) return item.week;
    if (item.month) return item.month;
    if (item.year) return item.year;
    return '';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex">
          <div className="text-red-600 text-2xl mr-3">❌</div>
          <div>
            <h3 className="text-red-800 font-semibold mb-1">加载失败</h3>
            <p className="text-red-700">{error}</p>
            <button
              onClick={fetchStats}
              className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
            >
              重试
            </button>
          </div>
        </div>
      </div>
    );
  }

  const trendData = getCurrentTrendData();
  const maxCount = Math.max(...trendData.map(d => d.count), 1);

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">💬 对话分析</h1>
          <p className="text-gray-600 mt-1">
            洞察用户对话趋势、类型分布和热门关键词
          </p>
        </div>
        <div className="flex items-center space-x-4">
          {/* 时间范围选择器 */}
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(Number(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value={7}>最近 7 天</option>
            <option value={30}>最近 30 天</option>
            <option value={90}>最近 90 天</option>
            <option value={180}>最近 180 天</option>
            <option value={365}>最近 365 天</option>
          </select>
          <button
            onClick={fetchStats}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            🔄 刷新
          </button>
        </div>
      </div>

      {/* 核心指标 */}
      <div className="bg-gradient-to-r from-blue-500 to-indigo-600 rounded-lg p-6 text-white">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <p className="text-blue-100 text-sm">总对话数</p>
            <p className="text-4xl font-bold mt-1">{stats?.total_conversations || 0}</p>
          </div>
          <div>
            <p className="text-blue-100 text-sm">统计范围</p>
            <p className="text-4xl font-bold mt-1">{stats?.time_range_days || 0} 天</p>
          </div>
          <div>
            <p className="text-blue-100 text-sm">日均对话</p>
            <p className="text-4xl font-bold mt-1">
              {stats
                ? Math.round(stats.total_conversations / stats.time_range_days)
                : 0}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 时间趋势图 */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-gray-900">📈 对话趋势</h3>
            <div className="flex space-x-2">
              {['daily', 'weekly', 'monthly', 'yearly'].map((view) => (
                <button
                  key={view}
                  onClick={() => setTrendView(view as any)}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                    trendView === view
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {view === 'daily' && '每日'}
                  {view === 'weekly' && '每周'}
                  {view === 'monthly' && '每月'}
                  {view === 'yearly' && '每年'}
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {trendData.map((item, idx) => {
              const percentage = ((item.count / maxCount) * 100).toFixed(0);
              const label = getTrendLabel(item);

              return (
                <div key={idx}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-gray-700 font-mono">{label}</span>
                    <span className="text-gray-600 font-semibold">{item.count} 次</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className="bg-gradient-to-r from-blue-500 to-indigo-500 h-3 rounded-full transition-all"
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 类型分布 */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">🏷️ 项目类型分布</h3>
          <div className="space-y-3">
            {stats?.type_distribution.map((item, idx) => {
              const percentage = stats.total_conversations > 0
                ? ((item.count / stats.total_conversations) * 100).toFixed(1)
                : 0;

              const colors = [
                'bg-blue-500',
                'bg-green-500',
                'bg-orange-500',
                'bg-purple-500',
                'bg-pink-500',
              ];

              return (
                <div key={idx}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-gray-700 font-medium">{item.type}</span>
                    <span className="text-gray-600">
                      {item.count} ({percentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`${colors[idx % colors.length]} h-2 rounded-full transition-all`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 状态分布 */}
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">📊 对话状态分布</h3>
          <div className="space-y-3">
            {stats?.status_distribution.map((item, idx) => {
              const percentage = stats.total_conversations > 0
                ? ((item.count / stats.total_conversations) * 100).toFixed(1)
                : 0;

              const colorMap: Record<string, string> = {
                completed: 'bg-green-500',
                active: 'bg-yellow-500',
                failed: 'bg-red-500',
                pending: 'bg-gray-500',
              };

              return (
                <div key={idx}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-gray-700 font-medium">
                      {statusDisplayNames[item.status] || item.status}
                    </span>
                    <span className="text-gray-600">
                      {item.count} ({percentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`${colorMap[item.status] || 'bg-gray-500'} h-2 rounded-full transition-all`}
                      style={{ width: `${percentage}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 热门关键词云 */}
        <div className="bg-white border border-gray-200 rounded-lg p-6 lg:col-span-2">
          <h3 className="text-xl font-bold text-gray-900 mb-4">☁️ 热门关键词云</h3>
          <div className="flex flex-wrap gap-2 max-h-64 overflow-y-auto">
            {stats?.top_keywords.map((keyword, idx) => {
              // 根据频率调整字体大小（10-40px）
              const maxFreq = Math.max(...stats.top_keywords.map(k => k.count), 1);
              const fontSize = 10 + (keyword.count / maxFreq) * 30;

              // 颜色变化
              const colors = [
                'text-blue-600',
                'text-green-600',
                'text-orange-600',
                'text-purple-600',
                'text-pink-600',
                'text-indigo-600',
                'text-red-600',
                'text-teal-600',
              ];

              return (
                <span
                  key={idx}
                  className={`inline-block px-3 py-1 rounded-lg bg-gray-100 hover:bg-gray-200 transition-all cursor-default ${
                    colors[idx % colors.length]
                  }`}
                  style={{ fontSize: `${fontSize}px` }}
                  title={`${keyword.word}: ${keyword.count} 次`}
                >
                  {keyword.word}
                </span>
              );
            })}
          </div>
        </div>
      </div>

      {/* 底部时间戳 */}
      <div className="text-center text-sm text-gray-500">
        最后更新: {stats?.timestamp ? new Date(stats.timestamp).toLocaleString('zh-CN') : '-'}
      </div>
    </div>
  );
}
