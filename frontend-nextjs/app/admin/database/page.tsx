'use client';

import { useState, useEffect, useCallback } from 'react';

interface DatabaseStats {
  file_size_mb: number;
  total_records: number;
  status_distribution: Record<string, number>;
  avg_size_mb: number;
  health_status: 'HEALTHY' | 'WARNING' | 'CRITICAL';
  thresholds: {
    healthy_max_mb: number;
    warning_max_mb: number;
  };
}

interface DatabaseHealth {
  health_status: 'HEALTHY' | 'WARNING' | 'CRITICAL';
  file_size_mb: number;
  total_records: number;
  alerts: Array<{ level: string; message: string }>;
  recommendations: string[];
  thresholds: {
    healthy: string;
    warning: string;
    critical: string;
  };
}

interface VacuumResult {
  size_before_mb: number;
  size_after_mb: number;
  freed_mb: number;
  duration_seconds: number;
  improvement_percent: number;
}

interface ArchiveResult {
  sessions_found: number;
  sessions_archived: number;
  output_file: string | null;
  dry_run: boolean;
  freed_space_mb?: number;
  message: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function DatabaseMonitoringPage() {
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [health, setHealth] = useState<DatabaseHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [vacuumLoading, setVacuumLoading] = useState(false);
  const [archiveLoading, setArchiveLoading] = useState(false);
  const [archiveDays, setArchiveDays] = useState(90);
  const [archiveDryRun, setArchiveDryRun] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [actionResult, setActionResult] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // 获取认证头
  const getAuthHeaders = () => {
    const token = localStorage.getItem('wp_jwt_token');
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    };
  };

  // 获取数据库统计信息
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/database/stats`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data.status === 'success') {
        setStats(data.data);
      }
    } catch (err) {
      console.error('获取数据库统计失败:', err);
      throw err;
    }
  }, []);

  // 获取数据库健康状态
  const fetchHealth = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/database/health`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data.status === 'success') {
        setHealth(data.data);
      }
    } catch (err) {
      console.error('获取数据库健康状态失败:', err);
      throw err;
    }
  }, []);

  // 刷新所有数据
  const refreshData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([fetchStats(), fetchHealth()]);
      setLastRefresh(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取数据失败');
    } finally {
      setLoading(false);
    }
  }, [fetchStats, fetchHealth]);

  // 执行 VACUUM 压缩
  const handleVacuum = async () => {
    if (!confirm('确定要执行 VACUUM 压缩吗？此操作可能需要几秒到几分钟时间。')) {
      return;
    }

    setVacuumLoading(true);
    setActionResult(null);
    try {
      const response = await fetch(`${API_BASE}/api/admin/database/vacuum`, {
        method: 'POST',
        headers: getAuthHeaders(),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data.status === 'success') {
        const result = data.data as VacuumResult;
        setActionResult({
          type: 'success',
          message: `VACUUM 完成！释放空间: ${result.freed_mb.toFixed(2)} MB (${result.improvement_percent.toFixed(1)}%)，耗时: ${result.duration_seconds.toFixed(2)} 秒`,
        });
        await refreshData();
      }
    } catch (err) {
      setActionResult({
        type: 'error',
        message: `VACUUM 失败: ${err instanceof Error ? err.message : '未知错误'}`,
      });
    } finally {
      setVacuumLoading(false);
    }
  };

  // 归档旧会话
  const handleArchive = async () => {
    const confirmMsg = archiveDryRun
      ? `将模拟归档 ${archiveDays} 天前的会话（不会实际删除数据）`
      : `确定要归档 ${archiveDays} 天前的会话吗？此操作将导出数据到冷存储并从主库删除。`;

    if (!confirm(confirmMsg)) {
      return;
    }

    setArchiveLoading(true);
    setActionResult(null);
    try {
      const response = await fetch(
        `${API_BASE}/api/admin/database/archive?days=${archiveDays}&dry_run=${archiveDryRun}`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
        }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data.status === 'success') {
        const result = data.data as ArchiveResult;
        if (archiveDryRun) {
          setActionResult({
            type: 'success',
            message: `模拟运行完成：找到 ${result.sessions_found} 个可归档会话`,
          });
        } else {
          setActionResult({
            type: 'success',
            message: `归档完成！已归档 ${result.sessions_archived} 个会话，释放 ${result.freed_space_mb?.toFixed(2) || 0} MB`,
          });
          await refreshData();
        }
      }
    } catch (err) {
      setActionResult({
        type: 'error',
        message: `归档失败: ${err instanceof Error ? err.message : '未知错误'}`,
      });
    } finally {
      setArchiveLoading(false);
    }
  };

  // 初始化加载
  useEffect(() => {
    refreshData();
    // 每 60 秒自动刷新
    const interval = setInterval(refreshData, 60000);
    return () => clearInterval(interval);
  }, [refreshData]);

  // 健康状态配置
  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'HEALTHY':
        return { icon: '🟢', color: 'bg-green-100 text-green-800 border-green-300', bgColor: 'from-green-50 to-emerald-50', progressColor: 'bg-green-500' };
      case 'WARNING':
        return { icon: '🟡', color: 'bg-yellow-100 text-yellow-800 border-yellow-300', bgColor: 'from-yellow-50 to-amber-50', progressColor: 'bg-yellow-500' };
      case 'CRITICAL':
        return { icon: '🔴', color: 'bg-red-100 text-red-800 border-red-300', bgColor: 'from-red-50 to-orange-50', progressColor: 'bg-red-500' };
      default:
        return { icon: '⚪', color: 'bg-gray-100 text-gray-800 border-gray-300', bgColor: 'from-gray-50 to-slate-50', progressColor: 'bg-gray-500' };
    }
  };

  // 格式化大小
  const formatSize = (mb: number | undefined | null): string => {
    if (mb === undefined || mb === null) return '-';
    if (mb >= 1024) {
      return `${(mb / 1024).toFixed(2)} GB`;
    }
    return `${mb.toFixed(2)} MB`;
  };

  // 计算进度百分比（基于阈值）
  const getProgressPercent = (): number => {
    if (!stats) return 0;
    const maxMb = stats.thresholds?.warning_max_mb || 51200; // 默认 50GB
    const percent = (stats.file_size_mb / maxMb) * 100;
    return Math.min(percent, 100);
  };

  // 获取最大阈值（用于显示）
  const getMaxThreshold = (): number => {
    return stats?.thresholds?.warning_max_mb || 51200; // 默认 50GB
  };

  if (loading && !stats) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600">加载数据库监控数据...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="space-y-6 p-6">
        <div className="bg-red-50 border border-red-300 rounded-xl p-6 text-center">
          <div className="text-4xl mb-4">❌</div>
          <h2 className="text-xl font-bold text-red-900 mb-2">无法连接到数据库监控 API</h2>
          <p className="text-red-700 mb-4">{error}</p>
          <button
            onClick={refreshData}
            className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  const statusConfig = stats ? getStatusConfig(stats.health_status) : getStatusConfig('');

  return (
    <div className="space-y-6 p-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">🗄️ 数据库监控</h1>
          <p className="text-sm text-gray-500 mt-1">
            会话数据库健康状态与维护工具 (archived_sessions.db)
          </p>
        </div>
        <div className="flex items-center gap-4">
          {lastRefresh && (
            <span className="text-sm text-gray-500">
              最后刷新: {lastRefresh.toLocaleTimeString('zh-CN')}
            </span>
          )}
          <button
            onClick={refreshData}
            disabled={loading}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              loading
                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {loading ? '刷新中...' : '🔄 刷新'}
          </button>
        </div>
      </div>

      {/* 操作结果提示 */}
      {actionResult && (
        <div
          className={`rounded-xl p-4 border-2 ${
            actionResult.type === 'success'
              ? 'bg-green-50 border-green-300 text-green-800'
              : 'bg-red-50 border-red-300 text-red-800'
          }`}
        >
          <div className="flex items-center gap-3">
            <span className="text-2xl">{actionResult.type === 'success' ? '✅' : '❌'}</span>
            <span className="font-medium">{actionResult.message}</span>
            <button
              onClick={() => setActionResult(null)}
              className="ml-auto text-gray-500 hover:text-gray-700"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* 健康状态卡片 */}
      {stats && (
        <div className={`bg-gradient-to-br ${statusConfig.bgColor} rounded-xl shadow-lg border-2 ${statusConfig.color.split(' ')[2]} p-6`}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-gray-900">
              {statusConfig.icon} 数据库健康状态
            </h2>
            <span className={`px-4 py-2 rounded-full font-bold ${statusConfig.color}`}>
              {stats.health_status}
            </span>
          </div>

          {/* 进度条 */}
          <div className="mb-4">
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>数据库大小</span>
              <span>{formatSize(stats.file_size_mb)} / {formatSize(getMaxThreshold())}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
              <div
                className={`h-full ${statusConfig.progressColor} transition-all duration-500`}
                style={{ width: `${getProgressPercent()}%` }}
              ></div>
            </div>
          </div>

          {/* 阈值说明 */}
          <div className="flex gap-4 text-sm">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-green-500 rounded-full"></span>
              正常: &lt; 10 GB
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-yellow-500 rounded-full"></span>
              警告: 10-50 GB
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-red-500 rounded-full"></span>
              严重: &gt; 50 GB
            </span>
          </div>
        </div>
      )}

      {/* 统计信息卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-5">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">📊</span>
            <span className="text-gray-600 text-sm">数据库大小</span>
          </div>
          <div className="text-3xl font-bold text-gray-900">
            {stats ? formatSize(stats.file_size_mb) : '-'}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-5">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">📝</span>
            <span className="text-gray-600 text-sm">总会话数</span>
          </div>
          <div className="text-3xl font-bold text-gray-900">
            {stats?.total_records?.toLocaleString() || '-'}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-5">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">📏</span>
            <span className="text-gray-600 text-sm">平均会话大小</span>
          </div>
          <div className="text-3xl font-bold text-gray-900">
            {stats?.avg_size_mb != null ? `${stats.avg_size_mb.toFixed(2)} MB` : '-'}
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-5">
          <div className="flex items-center gap-3 mb-2">
            <span className="text-2xl">✅</span>
            <span className="text-gray-600 text-sm">完成 / 失败</span>
          </div>
          <div className="text-3xl font-bold text-gray-900">
            {stats?.status_distribution ? (
              <>
                <span className="text-green-600">{stats.status_distribution.completed || 0}</span>
                <span className="text-gray-400 mx-1">/</span>
                <span className="text-red-600">{stats.status_distribution.failed || 0}</span>
              </>
            ) : '-'}
          </div>
        </div>
      </div>

      {/* 告警和建议 */}
      {health && (health.alerts.length > 0 || health.recommendations.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* 告警信息 */}
          {health.alerts.length > 0 && (
            <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-5">
              <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                <span>⚠️</span> 告警信息
              </h3>
              <div className="space-y-3">
                {health.alerts.map((alert, index) => (
                  <div
                    key={index}
                    className={`p-3 rounded-lg ${
                      alert.level === 'error' || alert.level === 'critical'
                        ? 'bg-red-50 border border-red-200 text-red-800'
                        : alert.level === 'warning'
                        ? 'bg-yellow-50 border border-yellow-200 text-yellow-800'
                        : 'bg-blue-50 border border-blue-200 text-blue-800'
                    }`}
                  >
                    {alert.message}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 维护建议 */}
          {health.recommendations.length > 0 && (
            <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-5">
              <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                <span>💡</span> 维护建议
              </h3>
              <ul className="space-y-2">
                {health.recommendations.map((rec, index) => (
                  <li key={index} className="flex items-start gap-2 text-gray-700">
                    <span className="text-blue-500 mt-1">•</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* 维护操作 */}
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-6 flex items-center gap-2">
          <span>🔧</span> 维护操作
        </h3>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* VACUUM 压缩 */}
          <div className="border border-gray-200 rounded-lg p-5">
            <h4 className="font-bold text-gray-900 mb-2 flex items-center gap-2">
              <span>🗜️</span> VACUUM 压缩
            </h4>
            <p className="text-sm text-gray-600 mb-4">
              回收数据库中未使用的空间，优化查询性能。建议在大量删除操作后执行。
            </p>
            <button
              onClick={handleVacuum}
              disabled={vacuumLoading || stats?.health_status === 'HEALTHY'}
              className={`w-full px-4 py-3 rounded-lg font-medium transition-all ${
                vacuumLoading
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : stats?.health_status === 'HEALTHY'
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              {vacuumLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin">⏳</span> 执行中...
                </span>
              ) : stats?.health_status === 'HEALTHY' ? (
                '数据库健康，无需压缩'
              ) : (
                '执行 VACUUM 压缩'
              )}
            </button>
          </div>

          {/* 归档旧会话 */}
          <div className="border border-gray-200 rounded-lg p-5">
            <h4 className="font-bold text-gray-900 mb-2 flex items-center gap-2">
              <span>📦</span> 归档旧会话
            </h4>
            <p className="text-sm text-gray-600 mb-4">
              将旧会话导出到冷存储（JSON 文件），并从主数据库删除以释放空间。
            </p>

            <div className="space-y-3 mb-4">
              <div className="flex items-center gap-3">
                <label className="text-sm text-gray-600 whitespace-nowrap">归档天数前:</label>
                <input
                  type="number"
                  value={archiveDays}
                  onChange={(e) => setArchiveDays(Math.max(1, parseInt(e.target.value) || 90))}
                  min="1"
                  max="365"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <span className="text-sm text-gray-500">天</span>
              </div>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={archiveDryRun}
                  onChange={(e) => setArchiveDryRun(e.target.checked)}
                  className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                />
                <span className="text-sm text-gray-600">模拟运行（不实际删除数据）</span>
              </label>
            </div>

            <button
              onClick={handleArchive}
              disabled={archiveLoading}
              className={`w-full px-4 py-3 rounded-lg font-medium transition-all ${
                archiveLoading
                  ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                  : archiveDryRun
                  ? 'bg-amber-600 text-white hover:bg-amber-700'
                  : 'bg-red-600 text-white hover:bg-red-700'
              }`}
            >
              {archiveLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin">⏳</span> 处理中...
                </span>
              ) : archiveDryRun ? (
                '🔍 模拟归档（预览）'
              ) : (
                '⚠️ 执行归档（将删除数据）'
              )}
            </button>
          </div>
        </div>
      </div>

      {/* 帮助信息 */}
      <div className="bg-gray-50 rounded-xl border border-gray-200 p-6">
        <details>
          <summary className="cursor-pointer font-bold text-gray-900 hover:text-blue-600 transition-colors">
            💡 使用帮助 & 命令行工具
          </summary>
          <div className="mt-4 space-y-4 text-sm text-gray-700">
            <div>
              <h4 className="font-semibold mb-2">命令行工具：</h4>
              <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto">
{`# 查看数据库统计信息
python scripts/database_maintenance.py --stats

# 执行 VACUUM 压缩
python scripts/database_maintenance.py --vacuum

# 归档30天前的会话（模拟）
python scripts/database_maintenance.py --archive --days 30 --dry-run

# 归档30天前的会话（实际执行）
python scripts/database_maintenance.py --archive --days 30

# 清理90天前的失败会话
python scripts/database_maintenance.py --clean-failed --days 90

# 执行完整维护流程
python scripts/database_maintenance.py --all`}
              </pre>
            </div>

            <div>
              <h4 className="font-semibold mb-2">定时任务设置：</h4>
              <pre className="bg-gray-900 text-green-400 p-4 rounded-lg overflow-x-auto">
{`# Windows 任务计划程序（每周日凌晨2点自动维护）
schtasks /create /tn "LangGraph数据库维护" /tr "python D:\\11-20\\langgraph-design\\scripts\\auto_archive_scheduler.py --once" /sc weekly /d SUN /st 02:00`}
              </pre>
            </div>

            <p className="text-gray-500">
              📖 详细文档：<a href="/ADMIN_DATABASE_MONITORING_GUIDE.md" className="text-blue-600 hover:underline">ADMIN_DATABASE_MONITORING_GUIDE.md</a>
            </p>
          </div>
        </details>
      </div>
    </div>
  );
}
