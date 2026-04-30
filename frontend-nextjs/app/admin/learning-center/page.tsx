'use client';

import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { toast } from 'sonner';

// ============================================================================
// Types
// ============================================================================

interface SubsystemInfo {
  name: string;
  code: string;
  status: 'active' | 'error';
  error?: string;
  [key: string]: any;
}

interface SchedulerTask {
  description: string;
  enabled: boolean;
  interval_seconds: number;
  last_run: string | null;
  run_count: number;
  error_count: number;
  last_result_status: 'success' | 'error' | 'never_run';
}

interface SchedulerStatus {
  running: boolean;
  total_tasks: number;
  enabled_tasks: number;
  tasks: Record<string, SchedulerTask>;
  error?: string;
}

interface LearningData {
  subsystems: Record<string, SubsystemInfo>;
  scheduler: SchedulerStatus;
  total_subsystems: number;
  active_count: number;
  error_count: number;
}

// ============================================================================
// Helpers
// ============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

function getHeaders() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('wp_jwt_token') : null;
  return { Authorization: `Bearer ${token}` };
}

function formatInterval(seconds: number): string {
  if (seconds >= 86400) return `${Math.round(seconds / 86400)}天`;
  if (seconds >= 3600) return `${Math.round(seconds / 3600)}小时`;
  return `${Math.round(seconds / 60)}分钟`;
}

function formatTime(iso: string | null): string {
  if (!iso) return '从未执行';
  try {
    return new Date(iso).toLocaleString('zh-CN');
  } catch {
    return iso;
  }
}

// ============================================================================
// Sub-components
// ============================================================================

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-green-100 text-green-800',
    error: 'bg-red-100 text-red-800',
    running: 'bg-blue-100 text-blue-800',
    stopped: 'bg-gray-100 text-gray-800',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-600'}`}>
      {status === 'active' ? '正常' : status === 'error' ? '异常' : status === 'running' ? '运行中' : '已停止'}
    </span>
  );
}

function SubsystemCard({ id, info }: { id: string; info: SubsystemInfo }) {
  const detailKeys = Object.keys(info).filter(
    (k) => !['name', 'code', 'status', 'error'].includes(k)
  );

  const labelMap: Record<string, string> = {
    active_dimensions: '活跃维度',
    pending_candidates: '待审候选',
    total_sessions: '学习会话数',
    pending_promotions: '待晋升标签',
    quality_level: '质量等级',
    control_action: '控制动作',
    emergency_mode: '紧急模式',
    history_size: '历史记录数',
    total_reports: '报告总数',
    registered_types: '注册类型数',
    user_history_entries: '用户历史条目',
  };

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="text-xs text-gray-400 font-mono">{info.code}</span>
          <h3 className="text-base font-semibold text-gray-800">{info.name}</h3>
        </div>
        <StatusBadge status={info.status} />
      </div>

      {info.error ? (
        <p className="text-sm text-red-600 bg-red-50 rounded p-2">{info.error}</p>
      ) : (
        <div className="space-y-1.5">
          {detailKeys.map((k) => {
            const val = info[k];
            const label = labelMap[k] || k;
            let display: string;
            if (typeof val === 'boolean') display = val ? '是' : '否';
            else if (typeof val === 'object') display = JSON.stringify(val);
            else display = String(val);

            return (
              <div key={k} className="flex justify-between text-sm">
                <span className="text-gray-500">{label}</span>
                <span className="text-gray-800 font-medium">{display}</span>
              </div>
            );
          })}
          {detailKeys.length === 0 && (
            <p className="text-sm text-gray-400">暂无详细数据</p>
          )}
        </div>
      )}
    </div>
  );
}

function SchedulerPanel({
  scheduler,
  onStart,
  onStop,
  onRunTask,
  onRunAll,
  actionLoading,
}: {
  scheduler: SchedulerStatus;
  onStart: () => void;
  onStop: () => void;
  onRunTask: (name: string) => void;
  onRunAll: () => void;
  actionLoading: string | null;
}) {
  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">学习调度器</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            管理 {scheduler.total_tasks} 个定时任务，已启用 {scheduler.enabled_tasks} 个
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={scheduler.running ? 'running' : 'stopped'} />
          {scheduler.running ? (
            <button
              onClick={onStop}
              disabled={actionLoading === 'stop'}
              className="px-3 py-1.5 text-sm bg-red-50 text-red-700 rounded-lg hover:bg-red-100 disabled:opacity-50"
            >
              {actionLoading === 'stop' ? '停止中...' : '停止'}
            </button>
          ) : (
            <button
              onClick={onStart}
              disabled={actionLoading === 'start'}
              className="px-3 py-1.5 text-sm bg-green-50 text-green-700 rounded-lg hover:bg-green-100 disabled:opacity-50"
            >
              {actionLoading === 'start' ? '启动中...' : '启动'}
            </button>
          )}
          <button
            onClick={onRunAll}
            disabled={actionLoading === 'run-all'}
            className="px-3 py-1.5 text-sm bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 disabled:opacity-50"
          >
            {actionLoading === 'run-all' ? '执行中...' : '全部执行'}
          </button>
        </div>
      </div>

      {scheduler.error && (
        <p className="text-sm text-red-600 bg-red-50 rounded p-2 mb-4">{scheduler.error}</p>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead>
            <tr className="text-left text-gray-500">
              <th className="pb-2 font-medium">任务名称</th>
              <th className="pb-2 font-medium">描述</th>
              <th className="pb-2 font-medium">间隔</th>
              <th className="pb-2 font-medium">上次执行</th>
              <th className="pb-2 font-medium">执行/错误</th>
              <th className="pb-2 font-medium">状态</th>
              <th className="pb-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {Object.entries(scheduler.tasks || {}).map(([name, task]) => (
              <tr key={name}>
                <td className="py-2 font-mono text-xs text-gray-700">{name}</td>
                <td className="py-2 text-gray-600">{task.description}</td>
                <td className="py-2 text-gray-600">{formatInterval(task.interval_seconds)}</td>
                <td className="py-2 text-gray-600">{formatTime(task.last_run)}</td>
                <td className="py-2">
                  <span className="text-green-700">{task.run_count}</span>
                  {' / '}
                  <span className={task.error_count > 0 ? 'text-red-600' : 'text-gray-400'}>
                    {task.error_count}
                  </span>
                </td>
                <td className="py-2">
                  {task.enabled ? (
                    <span className="text-green-600 text-xs">启用</span>
                  ) : (
                    <span className="text-gray-400 text-xs">禁用</span>
                  )}
                </td>
                <td className="py-2">
                  <button
                    onClick={() => onRunTask(name)}
                    disabled={actionLoading === name}
                    className="px-2 py-1 text-xs bg-blue-50 text-blue-700 rounded hover:bg-blue-100 disabled:opacity-50"
                  >
                    {actionLoading === name ? '...' : '执行'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============================================================================
// Main Page
// ============================================================================

export default function LearningCenterPage() {
  const [data, setData] = useState<LearningData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/admin/learning/subsystems/status`, {
        headers: getHeaders(),
      });
      setData(res.data.data);
      setError(null);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || '加载失败';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const schedulerAction = async (action: string, taskName?: string) => {
    const key = taskName || action;
    setActionLoading(key);
    try {
      const url = taskName
        ? `${API_BASE}/api/admin/learning/scheduler/run/${taskName}`
        : `${API_BASE}/api/admin/learning/scheduler/${action}`;
      const res = await axios.post(url, null, { headers: getHeaders() });
      toast.success(res.data.message || `${action} 成功`);
      await fetchData();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || `${action} 失败`);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600 mx-auto mb-3"></div>
          <p className="text-gray-500 text-sm">加载自学习系统状态...</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <p className="text-red-700 font-medium mb-2">加载失败</p>
        <p className="text-red-600 text-sm mb-4">{error}</p>
        <button
          onClick={() => { setLoading(true); fetchData(); }}
          className="px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200"
        >
          重试
        </button>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">自学习中心</h1>
          <p className="text-sm text-gray-500 mt-1">
            集中管理 {data.total_subsystems} 个自学习子系统和调度任务
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-sm">
            <span className="inline-block w-2 h-2 rounded-full bg-green-500"></span>
            <span className="text-gray-600">{data.active_count} 正常</span>
          </div>
          {data.error_count > 0 && (
            <div className="flex items-center gap-1.5 text-sm">
              <span className="inline-block w-2 h-2 rounded-full bg-red-500"></span>
              <span className="text-red-600">{data.error_count} 异常</span>
            </div>
          )}
          <button
            onClick={() => { setLoading(true); fetchData(); }}
            className="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
          >
            刷新
          </button>
        </div>
      </div>

      {/* Subsystem Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Object.entries(data.subsystems).map(([id, info]) => (
          <SubsystemCard key={id} id={id} info={info} />
        ))}
      </div>

      {/* Scheduler */}
      <SchedulerPanel
        scheduler={data.scheduler}
        onStart={() => schedulerAction('start')}
        onStop={() => schedulerAction('stop')}
        onRunTask={(name) => schedulerAction('run', name)}
        onRunAll={() => schedulerAction('run-all')}
        actionLoading={actionLoading}
      />
    </div>
  );
}
