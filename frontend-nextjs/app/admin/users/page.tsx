'use client';

/**
 * 用户信息分析页面
 *
 * 功能：
 * 1. 在线用户数量统计（按天/周/月/年）
 * 2. 用户地区分布地图可视化
 * 3. 用户对话数量排行榜（可筛选时间）
 */

import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';

// 数据类型定义
interface UserAnalyticsResponse {
  status: string;
  time_range: string;
  total_users: number;
  total_sessions: number;
  date_range: {
    start: string;
    end: string;
  };
  online_users: {
    daily: Array<{ date: string; count: number }>;
    weekly: Array<{ week: string; count: number }>;
    monthly: Array<{ month: string; count: number }>;
    yearly: Array<{ year: string; count: number }>;
  };
  region_distribution: Array<{ region: string; count: number }>;
  user_rankings: Array<{ user_id: string; conversation_count: number }>;
  timestamp: string;
}

export default function UsersAnalyticsPage() {
  const [stats, setStats] = useState<UserAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<string>('7d');
  const [trendView, setTrendView] = useState<'daily' | 'weekly' | 'monthly' | 'yearly'>('daily');

  // 获取用户分析数据
  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('app_auth_token');
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

      const response = await axios.get<UserAnalyticsResponse>(
        `${API_URL}/api/admin/users/analytics?time_range=${timeRange}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      setStats(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载失败');
      console.error('❌ 获取用户分析失败:', err);
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

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">加载中...</div>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-red-500">错误: {error}</div>
      </div>
    );
  }

  if (!stats) return null;

  // 获取当前趋势数据
  const currentTrendData = stats.online_users[trendView];

  // 计算地区分布的最大值（用于进度条）
  const maxRegionCount = Math.max(...stats.region_distribution.map(r => r.count), 1);

  // 中国地区颜色映射（模拟地图效果）
  const regionColors = [
    'bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-red-500',
    'bg-purple-500', 'bg-pink-500', 'bg-indigo-500', 'bg-teal-500'
  ];

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold">👥 用户分析</h1>
        <p className="text-gray-600 mt-2">
          用户活跃度、地区分布和对话排行榜
        </p>
      </div>

      {/* 时间范围选择器 */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center gap-4">
          <span className="font-semibold">时间范围：</span>
          {['1d', '7d', '30d', '365d'].map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-4 py-2 rounded transition-colors ${
                timeRange === range
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 hover:bg-gray-200'
              }`}
            >
              {range === '1d' && '1天'}
              {range === '7d' && '7天'}
              {range === '30d' && '30天'}
              {range === '365d' && '1年'}
            </button>
          ))}
          <div className="ml-auto text-sm text-gray-500">
            数据范围: {stats.date_range.start} ~ {stats.date_range.end}
          </div>
        </div>
      </div>

      {/* 核心指标卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* 总用户数 */}
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg shadow p-6 text-white">
          <div className="text-sm opacity-90">总用户数</div>
          <div className="text-4xl font-bold mt-2">{stats.total_users}</div>
          <div className="text-sm mt-2 opacity-75">
            {stats.time_range === '1d' && '最近1天'}
            {stats.time_range === '7d' && '最近7天'}
            {stats.time_range === '30d' && '最近30天'}
            {stats.time_range === '365d' && '最近1年'}
          </div>
        </div>

        {/* 总会话数 */}
        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-lg shadow p-6 text-white">
          <div className="text-sm opacity-90">总会话数</div>
          <div className="text-4xl font-bold mt-2">{stats.total_sessions}</div>
          <div className="text-sm mt-2 opacity-75">
            平均 {(stats.total_sessions / Math.max(stats.total_users, 1)).toFixed(1)} 会话/用户
          </div>
        </div>

        {/* 活跃地区数 */}
        <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg shadow p-6 text-white">
          <div className="text-sm opacity-90">活跃地区</div>
          <div className="text-4xl font-bold mt-2">{stats.region_distribution.length}</div>
          <div className="text-sm mt-2 opacity-75">
            覆盖 {stats.region_distribution.length} 个城市/地区
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 在线用户趋势图 */}
        <div className="bg-white rounded-lg shadow p-6 lg:col-span-2">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">📈 在线用户趋势</h2>
            <div className="flex gap-2">
              {(['daily', 'weekly', 'monthly', 'yearly'] as const).map((view) => (
                <button
                  key={view}
                  onClick={() => setTrendView(view)}
                  className={`px-3 py-1 rounded text-sm transition-colors ${
                    trendView === view
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 hover:bg-gray-200'
                  }`}
                >
                  {view === 'daily' && '按天'}
                  {view === 'weekly' && '按周'}
                  {view === 'monthly' && '按月'}
                  {view === 'yearly' && '按年'}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2 max-h-96 overflow-y-auto">
            {currentTrendData.length === 0 ? (
              <div className="text-center text-gray-400 py-8">暂无数据</div>
            ) : (
              currentTrendData.map((item, index) => {
                const label = 'date' in item ? item.date : 'week' in item ? item.week : 'month' in item ? item.month : (item as any).year;
                const maxCount = Math.max(...currentTrendData.map(d => d.count), 1);
                const percentage = (item.count / maxCount) * 100;

                return (
                  <div key={index} className="flex items-center gap-4">
                    <div className="w-32 text-sm text-gray-600 font-mono">{label}</div>
                    <div className="flex-1 bg-gray-100 rounded-full h-8 relative overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-blue-400 to-blue-600 h-full rounded-full transition-all duration-500 flex items-center justify-end px-3"
                        style={{ width: `${percentage}%` }}
                      >
                        <span className="text-white text-sm font-semibold">{item.count}</span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* 地区分布地图 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">🗺️ 地区分布</h2>

          <div className="space-y-3 max-h-[500px] overflow-y-auto">
            {stats.region_distribution.length === 0 ? (
              <div className="text-center text-gray-400 py-8">暂无地区数据</div>
            ) : (
              stats.region_distribution.map((region, index) => {
                const percentage = (region.count / maxRegionCount) * 100;
                const colorClass = regionColors[index % regionColors.length];

                return (
                  <div key={index} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="font-medium">{region.region}</span>
                      <span className="text-gray-600">{region.count} 会话</span>
                    </div>
                    <div className="bg-gray-100 rounded-full h-6 relative overflow-hidden">
                      <div
                        className={`${colorClass} h-full rounded-full transition-all duration-500 flex items-center justify-end px-2`}
                        style={{ width: `${percentage}%` }}
                      >
                        <span className="text-white text-xs font-semibold">
                          {percentage.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* 用户对话排行榜 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">🏆 用户对话排行榜</h2>

          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {stats.user_rankings.length === 0 ? (
              <div className="text-center text-gray-400 py-8">暂无排行数据</div>
            ) : (
              stats.user_rankings.map((user, index) => {
                // 排名徽章
                let badgeClass = 'bg-gray-100 text-gray-600';
                let badgeIcon = '🔸';

                if (index === 0) {
                  badgeClass = 'bg-yellow-100 text-yellow-700';
                  badgeIcon = '🥇';
                } else if (index === 1) {
                  badgeClass = 'bg-gray-200 text-gray-700';
                  badgeIcon = '🥈';
                } else if (index === 2) {
                  badgeClass = 'bg-orange-100 text-orange-700';
                  badgeIcon = '🥉';
                }

                return (
                  <div
                    key={index}
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className={`w-10 h-10 rounded-full ${badgeClass} flex items-center justify-center font-bold text-lg`}>
                      {badgeIcon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{user.user_id}</div>
                      <div className="text-sm text-gray-500">
                        {user.conversation_count} 次对话
                      </div>
                    </div>
                    <div className="text-2xl font-bold text-gray-300">
                      #{index + 1}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* 最后更新时间 */}
      <div className="text-center text-sm text-gray-500">
        最后更新: {new Date(stats.timestamp).toLocaleString('zh-CN')}
      </div>
    </div>
  );
}
