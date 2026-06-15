'use client';

import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';

interface ExpertStat {
  expert_role: string;
  image_count: number;
}

interface AspectRatioStat {
  aspect_ratio: string;
  count: number;
}

interface DateTrend {
  date: string;
  count: number;
}

interface SessionInfo {
  session_id: string;
  image_count: number;
  total_size_mb: number;
  created_at: string;
}

interface ConceptMapsStatsResponse {
  total_images: number;
  total_sessions: number;
  total_storage_mb: number;
  avg_images_per_session: number;
  expert_distribution: ExpertStat[];
  aspect_ratio_distribution: AspectRatioStat[];
  date_trend: DateTrend[];
  top_sessions: SessionInfo[];
  time_range_days: number;
  timestamp: string;
  message?: string;
}

export default function ConceptMapsPage() {
  const [stats, setStats] = useState<ConceptMapsStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<number>(7);

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

      const response = await axios.get<ConceptMapsStatsResponse>(
        `/api/admin/concept-maps/stats?days=${timeRange}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      setStats(response.data);
    } catch (err: any) {
      console.error('获取概念图统计失败:', err);
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

  // 专家角色显示名称映射
  const expertDisplayNames: Record<string, string> = {
    '2-1': '🎨 设计总监',
    '3-1': '🏗️ 结构工程师',
    '4-1': '💡 照明设计师',
    '5-1': '🌿 景观设计师',
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

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">🎨 概念图监控</h1>
          <p className="text-gray-600 mt-1">
            实时监控概念图生成情况、存储占用和专家分布
          </p>
        </div>
        <div className="flex items-center space-x-4">
          {/* 时间范围选择器 */}
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(Number(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value={1}>最近 1 天</option>
            <option value={3}>最近 3 天</option>
            <option value={7}>最近 7 天</option>
            <option value={14}>最近 14 天</option>
            <option value={30}>最近 30 天</option>
          </select>
          <button
            onClick={fetchStats}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            🔄 刷新
          </button>
        </div>
      </div>

      {/* 核心指标概览 */}
      <div className="bg-gradient-to-r from-purple-500 to-pink-600 rounded-lg p-6 text-white">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div>
            <p className="text-purple-100 text-sm">总生成数</p>
            <p className="text-4xl font-bold mt-1">{stats?.total_images || 0}</p>
          </div>
          <div>
            <p className="text-purple-100 text-sm">活跃会话</p>
            <p className="text-4xl font-bold mt-1">{stats?.total_sessions || 0}</p>
          </div>
          <div>
            <p className="text-purple-100 text-sm">存储占用</p>
            <p className="text-4xl font-bold mt-1">{stats?.total_storage_mb || 0} MB</p>
          </div>
          <div>
            <p className="text-purple-100 text-sm">平均/会话</p>
            <p className="text-4xl font-bold mt-1">{stats?.avg_images_per_session || 0}</p>
          </div>
        </div>
      </div>

      {/* 数据为空提示 */}
      {stats?.message ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <div className="text-6xl mb-4">📭</div>
          <p className="text-gray-700 text-lg">{stats.message}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 专家分布 */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">👥 专家分布</h3>
            <div className="space-y-3">
              {stats?.expert_distribution.map((expert) => {
                const displayName = expertDisplayNames[expert.expert_role] || expert.expert_role;
                const percentage = stats.total_images > 0
                  ? ((expert.image_count / stats.total_images) * 100).toFixed(1)
                  : 0;

                return (
                  <div key={expert.expert_role}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-gray-700 font-medium">{displayName}</span>
                      <span className="text-gray-600">
                        {expert.image_count} 张 ({percentage}%)
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-purple-500 h-2 rounded-full transition-all"
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 宽高比分布 */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">📐 宽高比分布</h3>
            <div className="space-y-3">
              {stats?.aspect_ratio_distribution.map((item) => {
                const percentage = stats.total_images > 0
                  ? ((item.count / stats.total_images) * 100).toFixed(1)
                  : 0;

                const colors: Record<string, string> = {
                  '16:9': 'bg-blue-500',
                  '9:16': 'bg-green-500',
                  '1:1': 'bg-orange-500',
                };

                return (
                  <div key={item.aspect_ratio}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-gray-700 font-medium">{item.aspect_ratio}</span>
                      <span className="text-gray-600">
                        {item.count} 张 ({percentage}%)
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`${colors[item.aspect_ratio] || 'bg-gray-500'} h-2 rounded-full transition-all`}
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 生成趋势 */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">📈 生成趋势</h3>
            <div className="space-y-3">
              {stats?.date_trend.map((item, idx) => {
                const maxCount = Math.max(...(stats?.date_trend.map(d => d.count) || [1]));
                const percentage = ((item.count / maxCount) * 100).toFixed(0);

                return (
                  <div key={item.date}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="text-gray-700">{item.date}</span>
                      <span className="text-gray-600 font-semibold">{item.count} 张</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all"
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Top 会话 */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-xl font-bold text-gray-900 mb-4">🏆 Top 会话</h3>
            <div className="space-y-3">
              {stats?.top_sessions.slice(0, 5).map((session, idx) => (
                <div
                  key={session.session_id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-white ${
                      idx === 0 ? 'bg-yellow-500' : idx === 1 ? 'bg-gray-400' : idx === 2 ? 'bg-orange-600' : 'bg-gray-300'
                    }`}>
                      {idx + 1}
                    </div>
                    <div>
                      <p className="text-sm text-gray-700 font-mono truncate max-w-[200px]">
                        {session.session_id}
                      </p>
                      <p className="text-xs text-gray-500">
                        {new Date(session.created_at).toLocaleDateString('zh-CN')}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-purple-600">{session.image_count}</p>
                    <p className="text-xs text-gray-500">{session.total_size_mb} MB</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 底部时间戳 */}
      <div className="text-center text-sm text-gray-500">
        最后更新: {stats?.timestamp ? new Date(stats.timestamp).toLocaleString('zh-CN') : '-'}
      </div>
    </div>
  );
}
