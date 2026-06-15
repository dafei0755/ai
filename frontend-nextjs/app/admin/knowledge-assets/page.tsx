'use client';

import { useEffect, useMemo, useState } from 'react';

type ReviewStatus = 'needs_review' | 'approved' | 'rejected' | 'needs_revision';
type TabKey = 'review' | 'approved' | 'consumption' | 'settlements' | 'submit';

interface KnowledgeAsset {
  asset_id: string;
  source_type: string;
  asset_type: string;
  title: string;
  lifecycle_status?: ReviewStatus;
  package_ids?: string[];
  ontology_dimension_ids?: string[];
  source_evidence_level?: string;
  source_machine_id?: string;
  batch_id?: string;
  reviewer_id?: string;
  reviewer_note?: string;
  created_at?: string;
  updated_at?: string;
  payload?: Record<string, unknown>;
}

interface Stats {
  candidates: number;
  needs_review: number;
  approved: number;
  rejected: number;
  needs_revision: number;
  consumption_events: number;
  settlement_events: number;
}

interface ConsumptionEvent {
  consumption_id: string;
  project_id?: string;
  session_id?: string;
  consumed_asset_ids?: string[];
  recalled_not_used_asset_ids?: string[];
  missing_slots?: string[];
  ceiling_level?: string;
  consumed_at?: string;
}

interface SettlementEvent {
  settlement_event_id: string;
  consumption_id?: string;
  asset_id?: string;
  outcome?: string;
  attribution?: string;
  evidence_strength?: string;
  observation?: string;
  created_at?: string;
}

interface GoldenReviewSuggestionItem {
  id: number;
  review_priority?: string;
  remediation_family?: string;
  suggestion_decision?: string;
  suggested_gold_expected_project_type?: string;
  suggested_gold_expected_spatial_extent?: string;
  suggested_gold_expected_project_stage?: string;
  suggested_gold_expected_core_tension?: string;
  suggested_gold_expected_output_depth?: string;
  prompt_excerpt?: string;
}

interface SystemicRemediationItem {
  id: string;
  priority?: string;
  module?: string;
  governance_mode?: string;
  risk?: string;
  mechanism?: string;
  verification_gate?: string;
  evidence_count?: number;
  ui_guardrail?: {
    scope?: string;
    violation_policy?: string;
    forbidden_terms?: string[];
    required_action?: string;
  };
}

interface GoldenReviewStatus {
  review_status?: string;
  next_action?: string;
  completion?: {
    total_rows?: number;
    complete_rows?: number;
    incomplete_rows?: number;
  };
  quality_gate?: {
    gate_status?: string;
    required_items?: number;
  };
  terminal_copy_guardrail?: {
    guardrail_scope?: string;
    violation_policy?: string;
    summary?: {
      forbidden_term_count?: number;
      violation_count?: number;
    };
    violations?: Array<{
      path?: string;
      line?: number;
      term?: string;
      excerpt?: string;
    }>;
  };
  suggestions?: {
    summary?: {
      total?: number;
      ready_for_fast_review?: number;
      needs_human_decision?: number;
    };
    items?: GoldenReviewSuggestionItem[];
  };
  systemic_remediation?: {
    summary?: {
      systemic_actions?: number;
      must_not_hardcode_cases?: boolean;
    };
    principles?: string[];
    items?: SystemicRemediationItem[];
  };
}

const statusLabels: Record<ReviewStatus, string> = {
  needs_review: '待审核',
  approved: '已批准',
  rejected: '已拒绝',
  needs_revision: '需修改',
};

const sourceTypeLabels: Record<string, string> = {
  external_generation: '外部生成链',
  internal_settlement: '内部自学习链',
  expert_note: '专家笔记',
  case_material: '案例材料',
};

const defaultCandidate = {
  asset_id: '',
  source_type: 'external_generation',
  source_machine_id: 'local-rd-node-01',
  batch_id: '',
  asset_type: 'KnowledgeCard',
  title: '',
  package_ids: '',
  ontology_dimension_ids: '',
  source_evidence_level: 'E2_research',
  payload: '{\n  "summary": ""\n}',
};

function getAuthHeaders(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('app_auth_token') : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function asArray(value?: string[]) {
  return value && value.length > 0 ? value.join(', ') : '-';
}

function formatDate(value?: string) {
  if (!value) return '-';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN');
}

function parseCsv(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function getSummary(payload?: Record<string, unknown>) {
  if (!payload) return '-';
  const summary = payload.summary;
  if (typeof summary === 'string' && summary.trim()) return summary;
  return JSON.stringify(payload, null, 2);
}

export default function KnowledgeAssetsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>('review');
  const [statusFilter, setStatusFilter] = useState<ReviewStatus>('needs_review');
  const [stats, setStats] = useState<Stats>({
    candidates: 0,
    needs_review: 0,
    approved: 0,
    rejected: 0,
    needs_revision: 0,
    consumption_events: 0,
    settlement_events: 0,
  });
  const [candidates, setCandidates] = useState<KnowledgeAsset[]>([]);
  const [approvedAssets, setApprovedAssets] = useState<KnowledgeAsset[]>([]);
  const [consumptionEvents, setConsumptionEvents] = useState<ConsumptionEvent[]>([]);
  const [settlementEvents, setSettlementEvents] = useState<SettlementEvent[]>([]);
  const [goldenReviewStatus, setGoldenReviewStatus] = useState<GoldenReviewStatus | null>(null);
  const [selected, setSelected] = useState<KnowledgeAsset | null>(null);
  const [reviewNote, setReviewNote] = useState('');
  const [form, setForm] = useState(defaultCandidate);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const statusOptions = useMemo(
    () => Object.entries(statusLabels) as Array<[ReviewStatus, string]>,
    []
  );

  useEffect(() => {
    loadAll(statusFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  async function loadAll(candidateStatus = statusFilter) {
    setLoading(true);
    setMessage('');
    try {
      const headers = getAuthHeaders();
      const [
        statsResponse,
        candidatesResponse,
        approvedResponse,
        consumptionResponse,
        settlementResponse,
        goldenReviewResponse,
      ] = await Promise.all([
        fetch('/api/admin/knowledge-assets/stats', { headers }),
        fetch(`/api/admin/knowledge-assets/candidates?status=${candidateStatus}`, { headers }),
        fetch('/api/admin/knowledge-assets/approved', { headers }),
        fetch('/api/admin/knowledge-assets/consumption-events', { headers }),
        fetch('/api/admin/knowledge-assets/settlement-events', { headers }),
        fetch('/api/admin/knowledge-assets/golden-review/status', { headers }),
      ]);

      if (!statsResponse.ok) throw new Error('加载统计失败');
      if (!candidatesResponse.ok) throw new Error('加载候选资产失败');
      if (!approvedResponse.ok) throw new Error('加载已批准资产失败');
      if (!consumptionResponse.ok) throw new Error('加载消费台账失败');
      if (!settlementResponse.ok) throw new Error('加载结算事件失败');
      if (!goldenReviewResponse.ok) throw new Error('加载 Golden 复核状态失败');

      const statsData = await statsResponse.json();
      const candidatesData = await candidatesResponse.json();
      const approvedData = await approvedResponse.json();
      const consumptionData = await consumptionResponse.json();
      const settlementData = await settlementResponse.json();
      const goldenReviewData = await goldenReviewResponse.json();

      setStats(statsData);
      setCandidates(candidatesData.items || []);
      setApprovedAssets(approvedData.items || []);
      setConsumptionEvents(consumptionData.items || []);
      setSettlementEvents(settlementData.items || []);
      setGoldenReviewStatus(goldenReviewData);
      setSelected((current) => current || (candidatesData.items || [])[0] || null);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }

  async function submitCandidate() {
    setMessage('');
    try {
      const payload = JSON.parse(form.payload || '{}');
      const body = {
        asset_id: form.asset_id || undefined,
        source_type: form.source_type,
        source_machine_id: form.source_machine_id || undefined,
        batch_id: form.batch_id || undefined,
        asset_type: form.asset_type,
        title: form.title,
        package_ids: parseCsv(form.package_ids),
        ontology_dimension_ids: parseCsv(form.ontology_dimension_ids),
        source_evidence_level: form.source_evidence_level,
        payload,
      };

      const response = await fetch('/api/admin/knowledge-assets/candidates', {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) throw new Error('提交候选资产失败');
      setMessage('候选资产已进入人工审核队列');
      setForm(defaultCandidate);
      setStatusFilter('needs_review');
      setActiveTab('review');
      await loadAll('needs_review');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '提交失败，请检查 JSON');
    }
  }

  async function reviewCandidate(assetId: string, action: 'approve' | 'reject' | 'needs-revision') {
    setMessage('');
    try {
      const body = action === 'approve' ? { reviewer_note: reviewNote } : { reason: reviewNote };
      const response = await fetch(`/api/admin/knowledge-assets/candidates/${assetId}/${action}`, {
        method: 'POST',
        headers: {
          ...getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) throw new Error('审核操作失败');
      setReviewNote('');
      setSelected(null);
      setMessage('审核状态已更新');
      await loadAll(statusFilter);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : '审核失败');
    }
  }

  return (
    <div className="space-y-6">
      <header className="rounded-lg border bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">知识资产审核系统</h1>
            <p className="mt-2 text-sm text-gray-600">
              外部生成链和内部自学习链只能提交候选资产，人工审核通过后才进入运行时可召回资产库。
            </p>
          </div>
          <button
            onClick={() => loadAll(statusFilter)}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            刷新
          </button>
        </div>
      </header>

      {message && (
        <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          {message}
        </div>
      )}

      <section className="grid gap-4 md:grid-cols-4">
        <StatCard label="待审核" value={stats.needs_review} />
        <StatCard label="已批准" value={stats.approved} />
        <StatCard label="消费台账" value={stats.consumption_events} />
        <StatCard label="结算事件" value={stats.settlement_events} />
      </section>

      {goldenReviewStatus && <GoldenReviewPanel status={goldenReviewStatus} />}

      <section className="rounded-lg border bg-white shadow-sm">
        <div className="flex flex-wrap gap-2 border-b p-4">
          <TabButton active={activeTab === 'review'} onClick={() => setActiveTab('review')}>
            候选审核
          </TabButton>
          <TabButton active={activeTab === 'approved'} onClick={() => setActiveTab('approved')}>
            已批准资产
          </TabButton>
          <TabButton active={activeTab === 'consumption'} onClick={() => setActiveTab('consumption')}>
            消费台账
          </TabButton>
          <TabButton active={activeTab === 'settlements'} onClick={() => setActiveTab('settlements')}>
            结算事件
          </TabButton>
          <TabButton active={activeTab === 'submit'} onClick={() => setActiveTab('submit')}>
            提交候选
          </TabButton>
        </div>

        {loading && <div className="p-4 text-sm text-gray-500">加载中...</div>}

        {activeTab === 'review' && (
          <div className="grid min-h-[520px] gap-0 lg:grid-cols-[360px_1fr]">
            <aside className="border-r p-4">
              <div className="mb-4">
                <label className="mb-1 block text-sm font-medium text-gray-700">审核状态</label>
                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value as ReviewStatus)}
                  className="w-full rounded-md border px-3 py-2 text-sm"
                >
                  {statusOptions.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                {candidates.map((item) => (
                  <button
                    key={item.asset_id}
                    onClick={() => setSelected(item)}
                    className={`w-full rounded-md border p-3 text-left text-sm hover:border-blue-400 ${
                      selected?.asset_id === item.asset_id ? 'border-blue-500 bg-blue-50' : 'bg-white'
                    }`}
                  >
                    <div className="font-medium text-gray-900">{item.title || item.asset_id}</div>
                    <div className="mt-1 text-xs text-gray-500">{item.asset_type} · {item.asset_id}</div>
                  </button>
                ))}
                {candidates.length === 0 && <div className="text-sm text-gray-500">暂无候选资产</div>}
              </div>
            </aside>

            <main className="p-4">
              {selected ? (
                <AssetDetail item={selected}>
                  <div className="mt-4 space-y-3 border-t pt-4">
                    <label className="block text-sm font-medium text-gray-700">审核意见</label>
                    <textarea
                      value={reviewNote}
                      onChange={(event) => setReviewNote(event.target.value)}
                      rows={3}
                      className="w-full rounded-md border px-3 py-2 text-sm"
                      placeholder="记录通过、拒绝或退回修改的理由"
                    />
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={() => reviewCandidate(selected.asset_id, 'approve')}
                        className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
                      >
                        批准入库
                      </button>
                      <button
                        onClick={() => reviewCandidate(selected.asset_id, 'needs-revision')}
                        className="rounded-md bg-amber-600 px-4 py-2 text-sm font-medium text-white hover:bg-amber-700"
                      >
                        退回修改
                      </button>
                      <button
                        onClick={() => reviewCandidate(selected.asset_id, 'reject')}
                        className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
                      >
                        拒绝
                      </button>
                    </div>
                  </div>
                </AssetDetail>
              ) : (
                <div className="text-sm text-gray-500">请选择一条候选资产。</div>
              )}
            </main>
          </div>
        )}

        {activeTab === 'approved' && (
          <AssetList items={approvedAssets} emptyText="暂无已批准资产" />
        )}

        {activeTab === 'consumption' && (
          <div className="divide-y">
            {consumptionEvents.map((item) => (
              <div key={item.consumption_id} className="p-4 text-sm">
                <div className="font-medium text-gray-900">{item.consumption_id}</div>
                <div className="mt-2 grid gap-2 text-gray-600 md:grid-cols-2">
                  <Info label="项目" value={item.project_id || '-'} />
                  <Info label="会话" value={item.session_id || '-'} />
                  <Info label="已消费卡" value={asArray(item.consumed_asset_ids)} />
                  <Info label="召回未使用" value={asArray(item.recalled_not_used_asset_ids)} />
                  <Info label="缺口" value={asArray(item.missing_slots)} />
                  <Info label="封顶" value={item.ceiling_level || '-'} />
                  <Info label="时间" value={formatDate(item.consumed_at)} />
                </div>
              </div>
            ))}
            {consumptionEvents.length === 0 && <div className="p-4 text-sm text-gray-500">暂无消费台账</div>}
          </div>
        )}

        {activeTab === 'settlements' && (
          <div className="divide-y">
            {settlementEvents.map((item) => (
              <div key={item.settlement_event_id} className="p-4 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-gray-900">{item.settlement_event_id}</span>
                  <Badge>{item.outcome || '-'}</Badge>
                  <Badge>{item.attribution || '-'}</Badge>
                  <Badge>{item.evidence_strength || '-'}</Badge>
                </div>
                <div className="mt-2 grid gap-2 text-gray-600 md:grid-cols-2">
                  <Info label="消费事件" value={item.consumption_id || '-'} />
                  <Info label="资产" value={item.asset_id || '-'} />
                  <Info label="时间" value={formatDate(item.created_at)} />
                </div>
                <p className="mt-2 whitespace-pre-wrap rounded-md bg-gray-50 p-3 text-gray-700">
                  {item.observation || '-'}
                </p>
              </div>
            ))}
            {settlementEvents.length === 0 && <div className="p-4 text-sm text-gray-500">暂无结算事件</div>}
          </div>
        )}

        {activeTab === 'submit' && (
          <div className="grid gap-4 p-4 lg:grid-cols-2">
            <FormField label="资产 ID（可空）" value={form.asset_id} onChange={(value) => setForm({ ...form, asset_id: value })} />
            <FormField label="标题" value={form.title} onChange={(value) => setForm({ ...form, title: value })} />
            <FormField label="来源类型" value={form.source_type} onChange={(value) => setForm({ ...form, source_type: value })} />
            <FormField label="资产类型" value={form.asset_type} onChange={(value) => setForm({ ...form, asset_type: value })} />
            <FormField label="来源机器" value={form.source_machine_id} onChange={(value) => setForm({ ...form, source_machine_id: value })} />
            <FormField label="批次 ID" value={form.batch_id} onChange={(value) => setForm({ ...form, batch_id: value })} />
            <FormField label="知识包 ID（逗号分隔）" value={form.package_ids} onChange={(value) => setForm({ ...form, package_ids: value })} />
            <FormField label="本体论维度（逗号分隔）" value={form.ontology_dimension_ids} onChange={(value) => setForm({ ...form, ontology_dimension_ids: value })} />
            <FormField label="证据等级" value={form.source_evidence_level} onChange={(value) => setForm({ ...form, source_evidence_level: value })} />
            <label className="block lg:col-span-2">
              <span className="mb-1 block text-sm font-medium text-gray-700">Payload JSON</span>
              <textarea
                value={form.payload}
                onChange={(event) => setForm({ ...form, payload: event.target.value })}
                rows={10}
                className="w-full rounded-md border px-3 py-2 font-mono text-sm"
              />
            </label>
            <div className="lg:col-span-2">
              <button
                onClick={submitCandidate}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                提交候选资产
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function getGoldenReviewStatusLabel(status?: string) {
  if (status === 'needs_human_review') return '需人工复核';
  if (status === 'complete') return '已完成';
  if (status === 'not_started') return '未开始';
  return status || '未知状态';
}

function getRemediationModuleLabel(module?: string) {
  const labels: Record<string, string> = {
    SpaceClassificationService: '空间分类识别',
    SchemeAdvisorEntryService: '首轮回应与追问',
    OutputCeilingPolicy: '输出深度封顶',
    FrontendHumanLanguageMapping: '前端人话表达',
    ProjectTypeRegistry: '项目类型 Registry',
    KnowledgeCoverageAndRecall: '知识覆盖与召回',
    ContextPacketLensActivation: 'context_packet 激活',
    GoldenReviewWorkflow: 'Golden 人工复核',
  };
  return module ? labels[module] || module : '未归类模块';
}

function GoldenReviewPanel({ status }: { status: GoldenReviewStatus }) {
  const summary = status.suggestions?.summary || {};
  const total = summary.total ?? status.completion?.total_rows ?? 0;
  const readyForFastReview = summary.ready_for_fast_review ?? 0;
  const needsHumanDecision = summary.needs_human_decision ?? 0;
  const suggestionItems = status.suggestions?.items || [];
  const remediation = status.systemic_remediation;
  const remediationSummary = remediation?.summary || {};
  const remediationItems = remediation?.items || [];
  const terminalCopyGuardrail = status.terminal_copy_guardrail;
  const terminalCopyViolations = terminalCopyGuardrail?.summary?.violation_count ?? 0;

  return (
    <section className="rounded-lg border bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-lg font-semibold text-gray-900">方案高参 Golden 复核</h2>
            <Badge>{getGoldenReviewStatusLabel(status.review_status)}</Badge>
          </div>
          <p className="mt-2 text-sm text-gray-600">
            这里只展示机器建议和人工复核进度，不自动写入标准答案，也不自动批准任何知识资产。
          </p>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-500">待复核题目</div>
          <div className="mt-1 text-3xl font-semibold text-gray-900">{total}</div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <div className="rounded-md border border-gray-200 p-3">
          <div className="text-sm text-gray-500">快速复核</div>
          <div className="mt-1 text-base font-semibold text-gray-900">
            {readyForFastReview} 条可快速复核
          </div>
        </div>
        <div className="rounded-md border border-gray-200 p-3">
          <div className="text-sm text-gray-500">人工裁决</div>
          <div className="mt-1 text-base font-semibold text-gray-900">
            {needsHumanDecision} 条需人工裁决
          </div>
        </div>
        <div className="rounded-md border border-gray-200 p-3">
          <div className="text-sm text-gray-500">质量闸</div>
          <div className="mt-1 text-base font-semibold text-gray-900">
            {status.quality_gate?.gate_status === 'pass' ? '通过' : '未通过'}
          </div>
        </div>
        {terminalCopyGuardrail && (
          <div className="rounded-md border border-gray-200 p-3">
            <div className="text-sm text-gray-500">终端文案扫描</div>
            <div
              className={`mt-1 text-base font-semibold ${
                terminalCopyViolations > 0 ? 'text-red-700' : 'text-green-700'
              }`}
            >
              {terminalCopyViolations > 0 ? `${terminalCopyViolations} 个违规` : '通过'}
            </div>
          </div>
        )}
      </div>

      {suggestionItems.length > 0 && (
        <div className="mt-4 space-y-3">
          <h3 className="text-sm font-semibold text-gray-900">优先复核样例</h3>
          {suggestionItems.slice(0, 3).map((item) => (
            <article key={item.id} className="rounded-md border border-gray-200 p-3 text-sm">
              <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
                <Badge>#{item.id}</Badge>
                {item.review_priority && <Badge>{item.review_priority}</Badge>}
                {item.remediation_family && <span>{item.remediation_family}</span>}
              </div>
              {item.suggested_gold_expected_core_tension && (
                <p className="mt-2 font-medium text-gray-900">
                  {item.suggested_gold_expected_core_tension}
                </p>
              )}
              {item.prompt_excerpt && (
                <p className="mt-1 line-clamp-2 text-gray-600">{item.prompt_excerpt}</p>
              )}
            </article>
          ))}
        </div>
      )}

      {remediation && (
        <div className="mt-5 border-t pt-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-gray-900">系统性整改清单</h3>
              <p className="mt-1 text-sm text-gray-600">
                从 190 条压力测试归纳机制问题，优先整改算法、Registry 和人话表达，不按单题打补丁。
              </p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              <Badge>{remediationSummary.systemic_actions ?? remediationItems.length} 个整改项</Badge>
              {remediationSummary.must_not_hardcode_cases && <Badge>禁止个案硬编码</Badge>}
            </div>
          </div>

          {remediationItems.length > 0 && (
            <div className="mt-3 grid gap-3 lg:grid-cols-2">
              {remediationItems.slice(0, 4).map((item) => (
                <article key={item.id} className="rounded-md border border-gray-200 p-3 text-sm">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-gray-500">
                    <Badge>{item.priority || '-'}</Badge>
                    <span>{getRemediationModuleLabel(item.module)}</span>
                    {typeof item.evidence_count === 'number' && (
                      <span>{item.evidence_count} 条证据</span>
                    )}
                  </div>
                  {item.risk && <p className="mt-2 font-medium text-gray-900">{item.risk}</p>}
                  {item.mechanism && <p className="mt-1 line-clamp-2 text-gray-600">{item.mechanism}</p>}
                  {item.ui_guardrail?.forbidden_terms?.length ? (
                    <div className="mt-2 rounded-md bg-amber-50 p-2 text-xs text-amber-900">
                      <div className="font-semibold">禁用术语检查</div>
                      <div className="mt-1">{item.ui_guardrail.forbidden_terms.slice(0, 6).join('、')}</div>
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-gray-900">{value}</div>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-md px-3 py-2 text-sm font-medium ${
        active ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
      }`}
    >
      {children}
    </button>
  );
}

function AssetList({ items, emptyText }: { items: KnowledgeAsset[]; emptyText: string }) {
  return (
    <div className="divide-y">
      {items.map((item) => (
        <AssetDetail key={item.asset_id} item={item} compact />
      ))}
      {items.length === 0 && <div className="p-4 text-sm text-gray-500">{emptyText}</div>}
    </div>
  );
}

function AssetDetail({
  item,
  compact,
  children,
}: {
  item: KnowledgeAsset;
  compact?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <article className={compact ? 'p-4' : ''}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{item.title || item.asset_id}</h2>
          <div className="mt-1 flex flex-wrap gap-2 text-xs text-gray-500">
            <Badge>{item.asset_id}</Badge>
            <Badge>{item.asset_type}</Badge>
            <Badge>{sourceTypeLabels[item.source_type] || item.source_type}</Badge>
            {item.lifecycle_status && <Badge>{statusLabels[item.lifecycle_status] || item.lifecycle_status}</Badge>}
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-2 text-sm text-gray-600 md:grid-cols-2">
        <Info label="知识包" value={asArray(item.package_ids)} />
        <Info label="本体论维度" value={asArray(item.ontology_dimension_ids)} />
        <Info label="证据等级" value={item.source_evidence_level || '-'} />
        <Info label="来源机器" value={item.source_machine_id || '-'} />
        <Info label="批次" value={item.batch_id || '-'} />
        <Info label="创建时间" value={formatDate(item.created_at)} />
        <Info label="审核人" value={item.reviewer_id || '-'} />
        <Info label="审核意见" value={item.reviewer_note || '-'} />
      </div>

      <pre className="mt-4 max-h-72 overflow-auto rounded-md bg-gray-50 p-3 text-xs text-gray-700">
        {getSummary(item.payload)}
      </pre>

      {children}
    </article>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-gray-500">{label}：</span>
      <span className="break-words text-gray-800">{value}</span>
    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-0.5 text-xs text-gray-600">
      {children}
    </span>
  );
}

function FormField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-gray-700">{label}</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-md border px-3 py-2 text-sm"
      />
    </label>
  );
}
