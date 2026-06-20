'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import axios from 'axios';
import { AlertTriangle, CheckCircle2, Loader2, RefreshCw, ShieldCheck } from 'lucide-react';

interface GovernanceReviewItem {
  id: string;
  module: string;
  object_type: string;
  object_id: string;
  title: string;
  review_status: string;
  source: string;
  risk: string;
  target_admin_path: string;
  metadata?: Record<string, unknown>;
  tenant_id?: string;
  workspace_id?: string;
}

interface GovernanceReviewQueue {
  schema_version: string;
  summary: {
    total_pending: number;
    by_module: Record<string, number>;
  };
  items: GovernanceReviewItem[];
}

function getAuthHeaders() {
  const token = typeof window !== 'undefined' ? localStorage.getItem('app_auth_token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function adminApi(path: string) {
  const base = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8001';
  return `${base}${path}`;
}

function riskClass(risk: string) {
  if (risk === 'P0') return 'border-red-200 bg-red-50 text-red-700';
  if (risk === 'P1') return 'border-amber-200 bg-amber-50 text-amber-700';
  return 'border-slate-200 bg-slate-50 text-slate-700';
}

export default function GovernanceReviewQueuePage() {
  const [queue, setQueue] = useState<GovernanceReviewQueue | null>(null);
  const [loading, setLoading] = useState(true);
  const [approvingItemId, setApprovingItemId] = useState('');
  const [applyingRegistryItemId, setApplyingRegistryItemId] = useState('');
  const [tenantId, setTenantId] = useState('');
  const [workspaceId, setWorkspaceId] = useState('');
  const [error, setError] = useState('');

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams();
      if (tenantId.trim()) params.set('tenant_id', tenantId.trim());
      if (workspaceId.trim()) params.set('workspace_id', workspaceId.trim());
      const query = params.toString();
      const response = await axios.get(
        adminApi(`/api/admin/governance/review-queue${query ? `?${query}` : ''}`),
        { headers: getAuthHeaders() },
      );
      setQueue(response.data);
    } catch (err) {
      console.error('加载治理复核队列失败:', err);
      setError('加载治理复核队列失败');
    } finally {
      setLoading(false);
    }
  }, [tenantId, workspaceId]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  const canApproveItem = (item: GovernanceReviewItem) => (
    item.module === 'knowledge_asset'
    && item.object_type === 'asset_draft'
    && item.review_status === 'pending'
    && Boolean(item.tenant_id || tenantId.trim())
    && Boolean(item.workspace_id || workspaceId.trim())
  );

  const canApplyBlueprintRegistryPatch = (item: GovernanceReviewItem) => (
    item.module === 'demand_reconstruction'
    && item.object_type === 'blueprint_fragment_draft'
    && item.review_status === 'approved'
    && Boolean(item.tenant_id || tenantId.trim())
    && Boolean(item.workspace_id || workspaceId.trim())
  );

  const approveItem = async (item: GovernanceReviewItem) => {
    if (!canApproveItem(item)) return;

    setApprovingItemId(item.id);
    setError('');
    try {
      await axios.post(
        adminApi(`/api/admin/governance/review-queue/${item.module}/${item.object_id}/approve`),
        {
          tenant_id: item.tenant_id || tenantId.trim(),
          workspace_id: item.workspace_id || workspaceId.trim(),
          reviewer_id: 'admin',
        },
        { headers: getAuthHeaders() },
      );
      await loadQueue();
    } catch (err) {
      console.error('批准知识资产草稿失败:', err);
      setError('批准知识资产草稿失败');
    } finally {
      setApprovingItemId('');
    }
  };

  const applyBlueprintRegistryPatch = async (item: GovernanceReviewItem) => {
    if (!canApplyBlueprintRegistryPatch(item)) return;

    setApplyingRegistryItemId(item.id);
    setError('');
    try {
      await axios.post(
        adminApi(`/api/admin/governance-review-queue/blueprint-fragment-drafts/${item.object_id}/registry-patch/apply`),
        {
          tenant_id: item.tenant_id || tenantId.trim(),
          workspace_id: item.workspace_id || workspaceId.trim(),
          reviewer_id: 'admin',
        },
        { headers: getAuthHeaders() },
      );
      await loadQueue();
    } catch (err) {
      console.error('应用蓝图片段 registry patch 失败:', err);
      setError('应用蓝图片段 registry patch 失败');
    } finally {
      setApplyingRegistryItemId('');
    }
  };

  const moduleEntries = useMemo(
    () => Object.entries(queue?.summary.by_module || {}).sort((a, b) => b[1] - a[1]),
    [queue],
  );

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-950">治理复核中心</h1>
          <p className="mt-1 text-sm text-slate-600">
            汇总需要人工复核后才能沉淀为系统事实的候选对象。
          </p>
        </div>
        <button
          type="button"
          onClick={loadQueue}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </button>
      </div>

      <div className="mb-6 grid gap-3 rounded-lg border border-slate-200 bg-white p-4 md:grid-cols-[1fr_1fr_auto]">
        <label className="text-sm font-medium text-slate-700">
          租户 ID
          <input
            value={tenantId}
            onChange={(event) => setTenantId(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
            placeholder="tenant-a"
          />
        </label>
        <label className="text-sm font-medium text-slate-700">
          工作区 ID
          <input
            value={workspaceId}
            onChange={(event) => setWorkspaceId(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
            placeholder="workspace-a"
          />
        </label>
        <div className="flex items-end text-xs text-slate-500">
          DB 复核项按租户和工作区隔离；不填写时只显示全局候选。
        </div>
      </div>

      {error && (
        <div className="mb-6 flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <AlertTriangle className="h-4 w-4" />
          {error}
        </div>
      )}

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <section className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-slate-600">待复核事项</div>
              <div className="mt-2 text-3xl font-semibold text-slate-950">
                {queue?.summary.total_pending ?? 0}
              </div>
            </div>
            <ShieldCheck className="h-8 w-8 text-blue-600" />
          </div>
        </section>
        <section className="rounded-lg border border-slate-200 bg-white p-4 md:col-span-2">
          <div className="mb-3 text-sm font-medium text-slate-700">模块分布</div>
          <div className="flex flex-wrap gap-2">
            {moduleEntries.length === 0 ? (
              <span className="inline-flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-sm text-emerald-700">
                <CheckCircle2 className="h-4 w-4" />
                当前没有待复核候选
              </span>
            ) : (
              moduleEntries.map(([module, count]) => (
                <span
                  key={module}
                  className="rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-700"
                >
                  {module} {count}
                </span>
              ))
            )}
          </div>
        </section>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-4 py-3">
          <h2 className="text-base font-semibold text-slate-950">复核队列</h2>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 py-12 text-sm text-slate-600">
            <Loader2 className="h-4 w-4 animate-spin" />
            加载中...
          </div>
        ) : (queue?.items.length || 0) === 0 ? (
          <div className="py-12 text-center text-sm text-slate-500">暂无待复核事项</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {queue?.items.map((item) => (
              <article key={item.id} className="grid gap-4 px-4 py-4 lg:grid-cols-[1fr_auto]">
                <div>
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <span className={`rounded-md border px-2 py-0.5 text-xs font-medium ${riskClass(item.risk)}`}>
                      {item.risk}
                    </span>
                    <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-600">
                      {item.module}
                    </span>
                    <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs text-slate-600">
                      {item.object_type}
                    </span>
                    <span className="rounded-md border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                      {item.review_status}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-slate-950">{item.title}</h3>
                  <div className="mt-2 grid gap-2 text-xs text-slate-600 sm:grid-cols-2">
                    <div>来源：{item.source}</div>
                    <div>对象：{item.object_id}</div>
                  </div>
                  {item.metadata && Object.keys(item.metadata).length > 0 && (
                    <pre className="mt-3 overflow-x-auto rounded-md bg-slate-950 p-3 text-xs text-slate-100">
                      {JSON.stringify(item.metadata, null, 2)}
                    </pre>
                  )}
                </div>
                <div className="flex flex-wrap items-start gap-2 lg:justify-end">
                  {canApproveItem(item) && (
                    <button
                      type="button"
                      onClick={() => approveItem(item)}
                      disabled={approvingItemId === item.id}
                      className="inline-flex items-center gap-2 rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {approvingItemId === item.id && <Loader2 className="h-4 w-4 animate-spin" />}
                      批准入库
                    </button>
                  )}
                  {canApplyBlueprintRegistryPatch(item) && (
                    <button
                      type="button"
                      onClick={() => applyBlueprintRegistryPatch(item)}
                      disabled={applyingRegistryItemId === item.id}
                      className="inline-flex items-center gap-2 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {applyingRegistryItemId === item.id && <Loader2 className="h-4 w-4 animate-spin" />}
                      应用到蓝图 registry
                    </button>
                  )}
                  <Link
                    href={item.target_admin_path}
                    className="inline-flex items-center rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    打开治理页
                  </Link>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
