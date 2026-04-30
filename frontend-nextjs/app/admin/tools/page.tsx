'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';

interface TopQuery {
  query: string;
  count: number;
}

interface ToolStat {
  tool_name: string;
  total_calls: number;
  success_count: number;
  fail_count: number;
  success_rate: number;
  avg_duration_ms: number;
  top_queries: TopQuery[];
}

interface ToolsStatsResponse {
  tools: ToolStat[];
  total_calls: number;
  time_range_hours: number;
  timestamp: string;
  message?: string;
}

// 🔥 v7.153: 新增工具调用率接口
interface RoleCallRate {
  role_id: string;
  session_count: number;
  total_calls: number;
  calls_per_session: number;
  success_rate: number;
}

interface CallRateResponse {
  role_call_rates: RoleCallRate[];
  overall: {
    total_sessions: number;
    sessions_with_tools: number;
    sessions_without_tools: number;
    tool_usage_rate: number;
  };
  time_range_hours: number;
  timestamp: string;
}

export default function ToolsPage() {
  const [stats, setStats] = useState<ToolsStatsResponse | null>(null);
  const [callRate, setCallRate] = useState<CallRateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<number>(24);

  const fetchStats = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('wp_jwt_token');
      if (!token) {
        setError('未登录，请先登录管理员账号');
        setLoading(false);
        return;
      }

      // 并行获取工具统计和调用率
      const [statsResponse, callRateResponse] = await Promise.all([
        axios.get<ToolsStatsResponse>(
          `http://localhost:8000/api/admin/tools/stats?hours=${timeRange}`,
          { headers: { Authorization: `Bearer ${token}` } }
        ),
        axios.get<CallRateResponse>(
          `http://localhost:8000/api/admin/tools/call-rate?hours=${timeRange}`,
          { headers: { Authorization: `Bearer ${token}` } }
        ).catch(() => ({ data: null })),  // 调用率接口失败不影响主页面
      ]);

      setStats(statsResponse.data);
      setCallRate(callRateResponse.data);
    } catch (err: any) {
      console.error('获取工具统计失败:', err);
      setError(err.response?.data?.detail || '获取数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();

    // 每60秒自动刷新
    const interval = setInterval(fetchStats, 60000);
    return () => clearInterval(interval);
  }, [timeRange]);

  // 工具显示名称映射
  const toolDisplayNames: Record<string, string> = {
    tavily_search: '🌐 Tavily (国际搜索)',
    arxiv_search: '📚 arXiv (学术论文)',
    ragflow_kb: '🗂️ RAGFlow (知识库)',
    milvus: '🗃️ Milvus (向量知识库)',
    bocha_search: '🔍 Bocha (中文搜索)',
  };

  // 工具颜色主题
  const toolColors: Record<string, string> = {
    tavily_search: 'blue',
    arxiv_search: 'purple',
    ragflow_kb: 'green',
    milvus: 'teal',
    bocha_search: 'orange',
  };

  const getColorClasses = (color: string) => {
    const colorMap: Record<string, { bg: string; text: string; border: string; progress: string }> = {
      blue: { bg: 'bg-blue-50', text: 'text-blue-600', border: 'border-blue-200', progress: 'bg-blue-500' },
      purple: { bg: 'bg-purple-50', text: 'text-purple-600', border: 'border-purple-200', progress: 'bg-purple-500' },
      green: { bg: 'bg-green-50', text: 'text-green-600', border: 'border-green-200', progress: 'bg-green-500' },
      teal: { bg: 'bg-teal-50', text: 'text-teal-600', border: 'border-teal-200', progress: 'bg-teal-500' },
      orange: { bg: 'bg-orange-50', text: 'text-orange-600', border: 'border-orange-200', progress: 'bg-orange-500' },
    };
    return colorMap[color] || colorMap.blue;
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
          <h1 className="text-3xl font-bold text-gray-900">🔍 搜索工具监控</h1>
          <p className="text-gray-600 mt-1">
            实时监控四大搜索工具的调用情况和性能表现
          </p>
        </div>
        <div className="flex items-center space-x-4">
          {/* 时间范围选择器 */}
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(Number(e.target.value))}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value={1}>最近 1 小时</option>
            <option value={6}>最近 6 小时</option>
            <option value={24}>最近 24 小时</option>
            <option value={72}>最近 3 天</option>
            <option value={168}>最近 7 天</option>
          </select>
          <button
            onClick={fetchStats}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            🔄 刷新
          </button>
        </div>
      </div>

      {/* 统计概览 */}
      <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div>
            <p className="text-blue-100 text-sm">总调用次数</p>
            <p className="text-4xl font-bold mt-1">{stats?.total_calls || 0}</p>
          </div>
          <div>
            <p className="text-blue-100 text-sm">活跃工具数</p>
            <p className="text-4xl font-bold mt-1">{stats?.tools.length || 0}</p>
          </div>
          <div>
            <p className="text-blue-100 text-sm">工具调用率</p>
            <p className="text-4xl font-bold mt-1">{callRate?.overall?.tool_usage_rate || 0}%</p>
          </div>
          <div>
            <p className="text-blue-100 text-sm">统计时间范围</p>
            <p className="text-4xl font-bold mt-1">{stats?.time_range_hours || 24}h</p>
          </div>
        </div>
      </div>

      {/* 🔥 v7.153: 工具调用率监控卡片 */}
      {callRate && callRate.role_call_rates.length > 0 && (
        <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">📊 角色工具调用率</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            {/* 总体统计 */}
            <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">使用工具的会话</p>
                  <p className="text-2xl font-bold text-green-600 mt-1">
                    {callRate.overall.sessions_with_tools} / {callRate.overall.total_sessions}
                  </p>
                </div>
                <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xl font-bold">{callRate.overall.tool_usage_rate}%</span>
                </div>
              </div>
            </div>
            <div className="bg-gradient-to-r from-red-50 to-orange-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">未调用工具的会话</p>
                  <p className="text-2xl font-bold text-red-600 mt-1">
                    {callRate.overall.sessions_without_tools}
                  </p>
                </div>
                <div className="w-16 h-16 bg-red-500 rounded-full flex items-center justify-center">
                  <span className="text-white text-xl">⚠️</span>
                </div>
              </div>
            </div>
          </div>

          {/* 各角色调用率表格 */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-2 text-left">角色ID</th>
                  <th className="px-4 py-2 text-right">会话数</th>
                  <th className="px-4 py-2 text-right">总调用</th>
                  <th className="px-4 py-2 text-right">每会话调用</th>
                  <th className="px-4 py-2 text-right">成功率</th>
                </tr>
              </thead>
              <tbody>
                {callRate.role_call_rates.map((role) => (
                  <tr key={role.role_id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium">{role.role_id}</td>
                    <td className="px-4 py-2 text-right">{role.session_count}</td>
                    <td className="px-4 py-2 text-right">{role.total_calls}</td>
                    <td className="px-4 py-2 text-right">
                      <span className={`font-bold ${role.calls_per_session > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {role.calls_per_session}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-right">
                      <span className={`font-bold ${role.success_rate >= 90 ? 'text-green-600' : role.success_rate >= 70 ? 'text-yellow-600' : 'text-red-600'}`}>
                        {role.success_rate}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 工具详情卡片 */}
      {stats?.message ? (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <div className="text-6xl mb-4">📭</div>
          <p className="text-gray-700 text-lg">{stats.message}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {stats?.tools.map((tool) => {
            const displayName = toolDisplayNames[tool.tool_name] || tool.tool_name;
            const colorScheme = toolColors[tool.tool_name] || 'blue';
            const colors = getColorClasses(colorScheme);

            return (
              <div
                key={tool.tool_name}
                className={`${colors.bg} border ${colors.border} rounded-lg p-6 hover:shadow-lg transition-shadow`}
              >
                {/* 工具名称 */}
                <div className="flex items-center justify-between mb-4">
                  <h3 className={`text-xl font-bold ${colors.text}`}>{displayName}</h3>
                  <span className={`px-3 py-1 ${colors.text} bg-white rounded-full text-sm font-semibold`}>
                    {tool.total_calls} 次调用
                  </span>
                </div>

                {/* 关键指标 */}
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="text-center">
                    <p className="text-gray-600 text-sm">成功率</p>
                    <p className={`text-2xl font-bold ${colors.text} mt-1`}>
                      {tool.success_rate.toFixed(1)}%
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-gray-600 text-sm">平均耗时</p>
                    <p className={`text-2xl font-bold ${colors.text} mt-1`}>
                      {tool.avg_duration_ms.toFixed(0)}ms
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-gray-600 text-sm">失败次数</p>
                    <p className={`text-2xl font-bold ${colors.text} mt-1`}>{tool.fail_count}</p>
                  </div>
                </div>

                {/* 成功率进度条 */}
                <div className="mb-4">
                  <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                    <span>调用情况</span>
                    <span>
                      {tool.success_count} 成功 / {tool.fail_count} 失败
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`${colors.progress} h-2 rounded-full transition-all`}
                      style={{ width: `${tool.success_rate}%` }}
                    ></div>
                  </div>
                </div>

                {/* Top 查询 */}
                {tool.top_queries.length > 0 && (
                  <div>
                    <p className="text-gray-700 font-semibold text-sm mb-2">🔥 热门查询</p>
                    <div className="space-y-1">
                      {tool.top_queries.slice(0, 3).map((query, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between text-sm bg-white rounded px-3 py-2"
                        >
                          <span className="text-gray-700 truncate flex-1 mr-2">
                            {query.query}
                          </span>
                          <span className={`${colors.text} font-semibold`}>{query.count}次</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* 底部时间戳 */}
      <div className="text-center text-sm text-gray-500">
        最后更新: {stats?.timestamp ? new Date(stats.timestamp).toLocaleString('zh-CN') : '-'}
      </div>
    </div>
  );
}
