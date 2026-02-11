'use client';

import { useState, useEffect, useRef } from 'react';
import axios from 'axios';

interface SystemMetrics {
  system: {
    cpu_percent: number;
    memory_percent: number;
    memory_used_gb: number;
    memory_total_gb: number;
    disk_percent: number;
  };
  sessions: {
    active_count: number;
  };
  performance: {
    total_requests: number;
    avg_response_time: number;
    requests_per_minute: number;
    error_count: number;
  };
  timestamp: string;
}

interface ToolsStats {
  total_calls: number;
  tools: Array<{ tool_name: string; total_calls: number }>;
}

interface ConceptMapsStats {
  total_images: number;
  total_storage_mb: number;
}

interface ConversationsStats {
  total_conversations: number;
  daily_trend: Array<{ date: string; count: number }>;
}

interface UsersStats {
  total_users: number;
  total_sessions: number;
}

export default function AdminDashboardPage() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [toolsStats, setToolsStats] = useState<ToolsStats | null>(null);
  const [conceptMapsStats, setConceptMapsStats] = useState<ConceptMapsStats | null>(null);
  const [conversationsStats, setConversationsStats] = useState<ConversationsStats | null>(null);
  const [usersStats, setUsersStats] = useState<UsersStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const fetchMetrics = async () => {
    try {
      const token = localStorage.getItem('wp_jwt_token');
      if (!token) {
        throw new Error('未登录');
      }

      // 并行获取系统指标、工具统计、概念图统计、对话统计和用户统计
      const [metricsResponse, toolsResponse, conceptMapsResponse, conversationsResponse, usersResponse] = await Promise.all([
        axios.get<SystemMetrics>(
          '/api/admin/metrics/summary',
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        ),
        axios.get<ToolsStats>(
          '/api/admin/tools/stats?hours=24',
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        ).catch(() => ({ data: { total_calls: 0, tools: [] } })), // 容错处理
        axios.get<ConceptMapsStats>(
          '/api/admin/concept-maps/stats?days=7',
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        ).catch(() => ({ data: { total_images: 0, total_storage_mb: 0 } })), // 容错处理
        axios.get<ConversationsStats>(
          '/api/admin/conversations/analytics?days=30',
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        ).catch(() => ({ data: { total_conversations: 0, daily_trend: [] } })), // 容错处理
        axios.get<UsersStats>(
          '/api/admin/users/analytics?time_range=7d',
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        ).catch(() => ({ data: { total_users: 0, total_sessions: 0 } })) // 容错处理
      ]);

      setMetrics(metricsResponse.data);
      setToolsStats(toolsResponse.data);
      setConceptMapsStats(conceptMapsResponse.data);
      setConversationsStats(conversationsResponse.data);
      setUsersStats(usersResponse.data);
      setError(null);
      setLastUpdate(new Date());
    } catch (err: any) {
      console.error('获取监控数据失败:', err);
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 立即获取一次
    fetchMetrics();

    // 启动轮询（60秒间隔）
    intervalRef.current = setInterval(fetchMetrics, 60000);

    // 清理函数
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">加载监控数据...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <h3 className="text-red-800 font-semibold mb-2">错误</h3>
        <p className="text-red-600">{error}</p>
        <button
          onClick={fetchMetrics}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
        >
          重试
        </button>
      </div>
    );
  }

  if (!metrics) {
    return <div>无数据</div>;
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-800">系统监控仪表板</h1>
        <div className="text-sm text-gray-500">
          最后更新: {lastUpdate.toLocaleTimeString('zh-CN')}
          <button
            onClick={fetchMetrics}
            className="ml-4 px-3 py-1 text-blue-600 hover:bg-blue-50 rounded"
          >
            🔄 刷新
          </button>
        </div>
      </div>

      {/* 系统状态卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* CPU使用率 */}
        <MetricCard
          title="CPU 使用率"
          value={`${metrics.system.cpu_percent}%`}
          status={getStatusColor(metrics.system.cpu_percent, 80, 90)}
          icon="⚡"
        />

        {/* 内存使用率 */}
        <MetricCard
          title="内存使用"
          value={`${metrics.system.memory_percent}%`}
          subtitle={`${metrics.system.memory_used_gb}GB / ${metrics.system.memory_total_gb}GB`}
          status={getStatusColor(metrics.system.memory_percent, 80, 90)}
          icon="💾"
        />

        {/* 磁盘使用率 */}
        <MetricCard
          title="磁盘使用"
          value={`${metrics.system.disk_percent}%`}
          status={getStatusColor(metrics.system.disk_percent, 80, 90)}
          icon="💿"
        />

        {/* 活跃会话数 */}
        <MetricCard
          title="活跃会话"
          value={metrics.sessions.active_count}
          status="normal"
          icon="👥"
        />
      </div>

      {/* 性能指标卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-8 gap-6">
        <MetricCard
          title="总请求数"
          value={metrics.performance.total_requests}
          icon="📊"
        />

        <MetricCard
          title="平均响应时间"
          value={`${metrics.performance.avg_response_time.toFixed(2)}ms`}
          status={getStatusColor(metrics.performance.avg_response_time, 500, 1000)}
          icon="⏱️"
        />

        <MetricCard
          title="请求/分钟"
          value={metrics.performance.requests_per_minute}
          icon="📈"
        />

        <MetricCard
          title="错误数"
          value={metrics.performance.error_count}
          status={metrics.performance.error_count > 0 ? 'warning' : 'normal'}
          icon="⚠️"
        />

        {/* 工具调用总数 */}
        <MetricCard
          title="工具调用 (24h)"
          value={toolsStats?.total_calls || 0}
          status="normal"
          icon="🔍"
          link="/admin/tools"
        />

        {/* 搜索过滤器 */}
        <MetricCard
          title="搜索过滤器"
          value="管理"
          subtitle="黑白名单配置"
          status="normal"
          icon="🛡️"
          link="/admin/search-filters"
        />

        {/* 概念图统计 */}
        <MetricCard
          title="概念图 (7d)"
          value={conceptMapsStats?.total_images || 0}
          subtitle={`${conceptMapsStats?.total_storage_mb || 0} MB`}
          status="normal"
          icon="🎨"
          link="/admin/concept-maps"
        />

        {/* 对话统计 */}
        <MetricCard
          title="对话总数 (30d)"
          value={conversationsStats?.total_conversations || 0}
          status="normal"
          icon="💬"
          link="/admin/conversations"
        />

        {/* 用户统计 */}
        <MetricCard
          title="活跃用户 (7d)"
          value={usersStats?.total_users || 0}
          subtitle={`${usersStats?.total_sessions || 0} 会话`}
          status="normal"
          icon="👥"
          link="/admin/users"
        />
      </div>

      {/* 提示信息 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-blue-800">
          💡 <strong>提示：</strong>数据每60秒自动刷新。点击右上角&ldquo;刷新&rdquo;按钮可立即更新数据。
        </p>
      </div>
    </div>
  );
}

// 指标卡片组件
function MetricCard({
  title,
  value,
  subtitle,
  status = 'normal',
  icon,
  link
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  status?: 'normal' | 'warning' | 'danger';
  icon?: string;
  link?: string;
}) {
  const statusColors = {
    normal: 'border-green-200 bg-green-50',
    warning: 'border-yellow-200 bg-yellow-50',
    danger: 'border-red-200 bg-red-50'
  };

  const textColors = {
    normal: 'text-green-800',
    warning: 'text-yellow-800',
    danger: 'text-red-800'
  };

  const cardContent = (
    <div className={`p-6 rounded-lg border-2 ${statusColors[status]} transition-all ${link ? 'cursor-pointer hover:shadow-lg' : ''}`}>
      <div className="flex items-start justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-600">{title}</h3>
        {icon && <span className="text-2xl">{icon}</span>}
      </div>
      <p className={`text-3xl font-bold ${textColors[status]}`}>{value}</p>
      {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
      {link && <p className="text-xs text-blue-600 mt-2">点击查看详情 →</p>}
    </div>
  );

  if (link) {
    return (
      <a href={link}>
        {cardContent}
      </a>
    );
  }

  return cardContent;
}

// 获取状态颜色
function getStatusColor(value: number, warningThreshold: number, dangerThreshold: number): 'normal' | 'warning' | 'danger' {
  if (value >= dangerThreshold) return 'danger';
  if (value >= warningThreshold) return 'warning';
  return 'normal';
}
