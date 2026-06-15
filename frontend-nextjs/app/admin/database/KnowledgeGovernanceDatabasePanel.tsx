'use client';

import { useState } from 'react';

interface KnowledgeGovernanceDatabaseHealth {
  schema_version: string;
  status: string;
  backend: string;
  table_counts: Record<string, number>;
  connection_pool: Record<string, unknown>;
}

interface KnowledgeGovernanceAuditEvent {
  event_id: number;
  action: string;
  object_type: string;
  object_id: string;
  created_at: string;
}

function authHeaders(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('app_auth_token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function KnowledgeGovernanceDatabasePanel({
  apiBase,
}: {
  apiBase: string;
}) {
  const [tenantId, setTenantId] = useState('');
  const [workspaceId, setWorkspaceId] = useState('');
  const [health, setHealth] = useState<KnowledgeGovernanceDatabaseHealth | null>(null);
  const [events, setEvents] = useState<KnowledgeGovernanceAuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadGovernanceDatabase = async () => {
    const tenant = tenantId.trim();
    const workspace = workspaceId.trim();
    if (!tenant) {
      setError('请输入租户 ID');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({ tenant_id: tenant });
      if (workspace) params.set('workspace_id', workspace);
      const auditParams = new URLSearchParams(params);
      auditParams.set('limit', '20');

      const [healthResponse, auditResponse] = await Promise.all([
        fetch(`${apiBase}/api/admin/knowledge-governance/database-health?${params.toString()}`, {
          headers: authHeaders(),
        }),
        fetch(`${apiBase}/api/admin/knowledge-governance/audit-events?${auditParams.toString()}`, {
          headers: authHeaders(),
        }),
      ]);
      if (!healthResponse.ok) throw new Error(`health HTTP ${healthResponse.status}`);
      if (!auditResponse.ok) throw new Error(`audit HTTP ${auditResponse.status}`);

      const healthData = await healthResponse.json();
      const auditData = await auditResponse.json();
      setHealth(healthData);
      setEvents(auditData.events || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载知识治理数据库失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-lg">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-gray-900">知识治理数据库</h2>
          <p className="mt-1 text-sm text-gray-500">
            查看知识资产草稿、已批准卡、复核队列和审计事件的隔离作用域状态。
          </p>
        </div>
        <button
          type="button"
          onClick={loadGovernanceDatabase}
          disabled={loading}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? '加载中...' : '查看知识治理 DB'}
        </button>
      </div>

      <div className="mb-4 grid gap-3 md:grid-cols-2">
        <label className="text-sm font-medium text-gray-700">
          知识治理租户 ID
          <input
            value={tenantId}
            onChange={(event) => setTenantId(event.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            placeholder="tenant-a"
          />
        </label>
        <label className="text-sm font-medium text-gray-700">
          知识治理工作区 ID
          <input
            value={workspaceId}
            onChange={(event) => setWorkspaceId(event.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            placeholder="workspace-a"
          />
        </label>
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {health && (
        <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
          <div className="rounded-lg border border-gray-200 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">表统计</h3>
              <span className="rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-700">
                {health.status} / {health.backend}
              </span>
            </div>
            <div className="space-y-2">
              {Object.entries(health.table_counts).map(([tableName, count]) => (
                <div key={tableName} className="flex items-center justify-between text-sm">
                  <span className="font-mono text-gray-700">{tableName}</span>
                  <span className="font-semibold text-gray-900">{count}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 rounded-md bg-gray-50 p-3 text-xs text-gray-600">
              <div>pool_pre_ping: {String(health.connection_pool.pool_pre_ping)}</div>
              <div>pool_size: {String(health.connection_pool.pool_size ?? '-')}</div>
              <div>max_overflow: {String(health.connection_pool.max_overflow ?? '-')}</div>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 p-4">
            <h3 className="mb-3 font-semibold text-gray-900">最近审计事件</h3>
            {events.length === 0 ? (
              <div className="text-sm text-gray-500">暂无审计事件</div>
            ) : (
              <div className="space-y-3">
                {events.map((event) => (
                  <div key={event.event_id} className="rounded-md border border-gray-100 bg-gray-50 p-3 text-sm">
                    <div className="font-semibold text-gray-900">{event.action}</div>
                    <div className="mt-1 font-mono text-xs text-gray-600">{event.object_type} / {event.object_id}</div>
                    <div className="mt-1 text-xs text-gray-500">{event.created_at}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
