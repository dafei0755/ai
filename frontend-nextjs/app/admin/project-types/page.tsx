'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';

// ── 类型定义 ──────────────────────────────────────────────────────────────────

interface ProjectType {
  type_id: string;
  name: string;
  name_en: string;
  priority: number;
  include_in_prompt: boolean;
  keyword_count: number;
  is_extension: boolean;
  source: string;
}

interface TypeCandidate {
  id: number;
  type_id_suggestion: string;
  name_zh: string;
  name_en: string;
  description: string;
  source: string;
  source_session_id: string | null;
  sample_inputs: string[];
  occurrence_count: number;
  suggested_keywords: string[];
  suggested_secondary_keywords: string[];
  confidence_score: number;
  review_status: string;
  created_at: string;
}

interface Statistics {
  total?: number;
  pending?: { count: number; avg_confidence: number };
  approved?: { count: number };
  rejected?: { count: number };
  high_frequency?: number;
}

interface ApproveFormData {
  type_id: string;
  name_zh: string;
  name_en: string;
  keywords: string; // comma-separated
  secondary_keywords: string; // comma-separated
  priority: number;
  min_secondary_hits: number;
  include_in_prompt: boolean;
  reviewer_note: string;
}

// ── 工具函数 ──────────────────────────────────────────────────────────────────

function getAuthHeaders() {
  const token = localStorage.getItem('wp_jwt_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function confidenceColor(score: number) {
  if (score >= 0.8) return 'text-green-600 bg-green-50';
  if (score >= 0.5) return 'text-yellow-600 bg-yellow-50';
  return 'text-red-600 bg-red-50';
}

function sourceLabel(source: string) {
  const map: Record<string, string> = {
    user_input: '用户输入',
    crawler: '爬虫数据',
    manual: '手动录入',
  };
  return map[source] || source;
}

// ── 审批弹窗 ──────────────────────────────────────────────────────────────────

function ApproveModal({
  candidate,
  onClose,
  onDone,
}: {
  candidate: TypeCandidate;
  onClose: () => void;
  onDone: (hasGaps?: boolean) => void;
}) {
  const [form, setForm] = useState<ApproveFormData>({
    type_id: candidate.type_id_suggestion,
    name_zh: candidate.name_zh,
    name_en: candidate.name_en || '',
    keywords: candidate.suggested_keywords.join(', '),
    secondary_keywords: candidate.suggested_secondary_keywords.join(', '),
    priority: 6,
    min_secondary_hits: 0,
    include_in_prompt: true,
    reviewer_note: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [coverageAlert, setCoverageAlert] = useState<{
    ontology_missing: boolean;
    few_shot_weak: boolean;
    total_ontology_gaps: number;
    total_few_shot_weak: number;
    approved_type_id: string;
  } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await axios.post(
        `/api/admin/project-types/candidates/${candidate.id}/approve`,
        {
          type_id: form.type_id.trim(),
          name_zh: form.name_zh.trim(),
          name_en: form.name_en.trim(),
          keywords: form.keywords.split(',').map((k) => k.trim()).filter(Boolean),
          secondary_keywords: form.secondary_keywords.split(',').map((k) => k.trim()).filter(Boolean),
          priority: form.priority,
          min_secondary_hits: form.min_secondary_hits,
          include_in_prompt: form.include_in_prompt,
          reviewer_note: form.reviewer_note,
        },
        { headers: getAuthHeaders() }
      );
      const alert = res.data?.coverage_alert;
      // 若有覆盖缺口则先展示，让管理员确认后再关闭
      if (alert && (alert.ontology_missing || alert.few_shot_weak)) {
        setCoverageAlert({ ...alert, approved_type_id: form.type_id.trim() });
      } else {
        onDone();
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || '审批失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b">
          <h3 className="text-xl font-bold text-gray-900">审批新类型候选</h3>
          <p className="text-sm text-gray-500 mt-1">确认参数后点击「审批通过」，类型将立即生效</p>
        </div>

        {/* ── 审批成功：覆盖缺口提醒 ──────────────────────────────────────── */}
        {coverageAlert && (
          <div className="p-6 space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="font-semibold text-green-800 mb-1">✅ 类型「{coverageAlert.approved_type_id}」已审批并生效</p>
              <p className="text-sm text-green-700">检测器已热重载，该类型可立即使用。</p>
            </div>

            <p className="text-sm font-semibold text-gray-700">⚠️ 但以下知识层尚未跟进，建议补充：</p>

            {coverageAlert.ontology_missing && (
              <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4 text-sm">
                <p className="font-semibold text-yellow-800 mb-2">📐 本体论框架缺失（共 {coverageAlert.total_ontology_gaps} 个类型无框架）</p>
                <p className="text-yellow-700 mb-3">该类型在 <code className="bg-yellow-100 px-1 rounded">ontology.yaml</code> 中没有对应的设计分析框架，LLM 将使用通用框架（质量下降）。</p>
                <p className="text-xs text-yellow-600 font-mono bg-yellow-100 p-2 rounded">
                  # 在后端运行以生成草稿：<br />
                  {`KnowledgeCoverageAuditor.generate_ontology_draft('${coverageAlert.approved_type_id}')`}<br />
                  # 草稿输出至：data/ontology_drafts/{coverageAlert.approved_type_id}.yaml
                </p>
              </div>
            )}

            {coverageAlert.few_shot_weak && (
              <div className="bg-blue-50 border border-blue-300 rounded-lg p-4 text-sm">
                <p className="font-semibold text-blue-800 mb-2">📋 Few-shot 示例覆盖薄弱（共 {coverageAlert.total_few_shot_weak} 个类型弱覆盖）</p>
                <p className="text-blue-700 mb-3">该类型在 <code className="bg-blue-100 px-1 rounded">examples_registry.yaml</code> 中没有匹配标签，任务分解的示例选择会降级到 fallback。</p>
                <p className="text-xs text-blue-600 font-mono bg-blue-100 p-2 rounded">
                  # 在后端运行以生成 registry 条目草稿：<br />
                  {`KnowledgeCoverageAuditor.generate_few_shot_draft('${coverageAlert.approved_type_id}')`}<br />
                  # 草稿输出至：data/few_shot_drafts/{coverageAlert.approved_type_id}_registry_entry.yaml
                </p>
              </div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => { setCoverageAlert(null); onDone(false); }}
                className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50 text-gray-600"
              >
                稍后处理
              </button>
              <button
                onClick={() => { setCoverageAlert(null); onDone(true); }}
                className="px-6 py-2 text-sm bg-amber-600 text-white rounded-lg hover:bg-amber-700"
              >
                前往「知识体缺口」标签 →
              </button>
            </div>
          </div>
        )}

        {/* ── 审批表单 ─────────────────────────────────────────────────────── */}
        {!coverageAlert && (
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* 来源信息（只读） */}
          <div className="bg-gray-50 rounded-lg p-4 text-sm space-y-1">
            <div><span className="text-gray-500">来源：</span>{sourceLabel(candidate.source)}</div>
            <div><span className="text-gray-500">出现次数：</span>{candidate.occurrence_count}</div>
            <div><span className="text-gray-500">置信度：</span>{(candidate.confidence_score * 100).toFixed(0)}%</div>
            {candidate.sample_inputs.length > 0 && (
              <div>
                <span className="text-gray-500">样例输入：</span>
                <ul className="list-disc list-inside mt-1 text-gray-700">
                  {candidate.sample_inputs.slice(0, 3).map((s, i) => (
                    <li key={i} className="truncate max-w-md">{s}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">英文 ID *</label>
              <input
                type="text"
                value={form.type_id}
                onChange={(e) => setForm({ ...form, type_id: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500"
                placeholder="如 auto_showroom"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">中文名称 *</label>
              <input
                type="text"
                value={form.name_zh}
                onChange={(e) => setForm({ ...form, name_zh: e.target.value })}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
                placeholder="如 汽车展厅"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">英文检索词</label>
            <input
              type="text"
              value={form.name_en}
              onChange={(e) => setForm({ ...form, name_en: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
              placeholder="如 auto showroom car display space"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              主关键词 * <span className="text-gray-400 font-normal">（逗号分隔，权重×2）</span>
            </label>
            <textarea
              value={form.keywords}
              onChange={(e) => setForm({ ...form, keywords: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
              rows={2}
              placeholder="如 汽车展厅, 4S店, 新能源展示, 车展"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              次要关键词 <span className="text-gray-400 font-normal">（逗号分隔，权重×1）</span>
            </label>
            <textarea
              value={form.secondary_keywords}
              onChange={(e) => setForm({ ...form, secondary_keywords: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
              rows={2}
              placeholder="如 展示空间, 品牌体验, 试驾"
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">优先级（1-15）</label>
              <input
                type="number"
                min={1} max={15}
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: parseInt(e.target.value) || 6 })}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">最低次要命中数</label>
              <input
                type="number"
                min={0} max={10}
                value={form.min_secondary_hits}
                onChange={(e) => setForm({ ...form, min_secondary_hits: parseInt(e.target.value) || 0 })}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-end pb-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.include_in_prompt}
                  onChange={(e) => setForm({ ...form, include_in_prompt: e.target.checked })}
                  className="w-4 h-4 accent-blue-600"
                />
                <span className="text-sm font-medium text-gray-700">写入 Prompt</span>
              </label>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">审核备注</label>
            <input
              type="text"
              value={form.reviewer_note}
              onChange={(e) => setForm({ ...form, reviewer_note: e.target.value })}
              className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500"
              placeholder="可选"
            />
          </div>

          {error && (
            <div className="bg-red-50 text-red-700 text-sm p-3 rounded-lg">{error}</div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              {loading ? '提交中...' : '审批通过'}
            </button>
          </div>
        </form>
        )}
      </div>
    </div>
  );
}

// ── 主页面 ────────────────────────────────────────────────────────────────────

export default function ProjectTypesPage() {
  const [tab, setTab] = useState<'registry' | 'candidates' | 'coverage'>('candidates');
  const [types, setTypes] = useState<ProjectType[]>([]);
  const [candidates, setCandidates] = useState<TypeCandidate[]>([]);
  const [stats, setStats] = useState<Statistics>({});
  const [loading, setLoading] = useState(true);
  const [approveTarget, setApproveTarget] = useState<TypeCandidate | null>(null);

  // 新增候选表单
  const [showAddForm, setShowAddForm] = useState(false);
  const [addForm, setAddForm] = useState({
    type_id_suggestion: '',
    name_zh: '',
    name_en: '',
    description: '',
    suggested_keywords: '',
    sample_inputs: '',
  });
  const [addLoading, setAddLoading] = useState(false);

  const [statusFilter, setStatusFilter] = useState('pending');

  // ── 知识体覆盖度缺口 ────────────────────────────────────────────────────────
  const [coverageReport, setCoverageReport] = useState<{
    ontology_missing: string[];
    ontology_orphans: string[];
    few_shot_low_coverage: string[];
    detector_count: number;
    ontology_count: number;
  } | null>(null);
  const [coverageLoading, setCoverageLoading] = useState(false);

  const fetchCoverage = async () => {
    setCoverageLoading(true);
    try {
      const res = await axios.get('/api/admin/project-types/coverage-audit', { headers: getAuthHeaders() });
      setCoverageReport(res.data.report ?? null);
    } catch {
      // 接口不可用时静默，不影响主流程
    } finally {
      setCoverageLoading(false);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const headers = getAuthHeaders();
      const [typesRes, candidatesRes] = await Promise.all([
        axios.get('/api/admin/project-types', { headers }),
        axios.get(`/api/admin/project-types/candidates?status=${statusFilter}&limit=100`, { headers }),
      ]);
      setTypes(typesRes.data.items || []);
      setCandidates(candidatesRes.data.items || []);
      setStats(candidatesRes.data.statistics || {});
    } catch (e) {
      console.error('获取类型数据失败:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    fetchCoverage();
  }, [statusFilter]);

  const handleReject = async (id: number) => {
    if (!confirm('确认拒绝该候选类型？')) return;
    try {
      await axios.post(
        `/api/admin/project-types/candidates/${id}/reject`,
        { reason: '管理员拒绝' },
        { headers: getAuthHeaders() }
      );
      fetchData();
    } catch (e) {
      alert('操作失败');
    }
  };

  const handleRevokeExtension = async (typeId: string) => {
    if (!confirm(`确认撤销扩展类型「${typeId}」？此操作将立即生效。`)) return;
    try {
      await axios.delete(`/api/admin/project-types/extensions/${typeId}`, {
        headers: getAuthHeaders(),
      });
      fetchData();
    } catch (e: any) {
      alert(e.response?.data?.detail || '撤销失败');
    }
  };

  const handleAddCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddLoading(true);
    try {
      await axios.post(
        '/api/admin/project-types/candidates',
        {
          type_id_suggestion: addForm.type_id_suggestion,
          name_zh: addForm.name_zh,
          name_en: addForm.name_en,
          description: addForm.description,
          suggested_keywords: addForm.suggested_keywords.split(',').map((k) => k.trim()).filter(Boolean),
          sample_inputs: addForm.sample_inputs.split('\n').map((s) => s.trim()).filter(Boolean),
        },
        { headers: getAuthHeaders() }
      );
      setShowAddForm(false);
      setAddForm({ type_id_suggestion: '', name_zh: '', name_en: '', description: '', suggested_keywords: '', sample_inputs: '' });
      fetchData();
    } catch (e: any) {
      alert(e.response?.data?.detail || '创建失败');
    } finally {
      setAddLoading(false);
    }
  };

  const pendingCount = (stats.pending as any)?.count ?? candidates.filter((c) => c.review_status === 'pending').length;

  return (
    <div className="space-y-6 p-6 bg-gray-50 min-h-screen">
      {/* 标题栏 */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">🏷️ 项目类型管理</h1>
          <p className="text-gray-600">管理系统项目分类体系，审核自动发现的新类型候选</p>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
        >
          ＋ 手动新增候选
        </button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-5">
          <p className="text-sm text-gray-500 mb-1">已注册类型</p>
          <p className="text-3xl font-bold text-blue-600">{types.length}</p>
          <p className="text-xs text-gray-400 mt-1">静态 + 扩展</p>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <p className="text-sm text-gray-500 mb-1">扩展类型</p>
          <p className="text-3xl font-bold text-purple-600">{types.filter((t) => t.is_extension).length}</p>
          <p className="text-xs text-gray-400 mt-1">管理员审批追加</p>
        </div>
        <div className="bg-white rounded-lg shadow p-5 border-l-4 border-yellow-400">
          <p className="text-sm text-gray-500 mb-1">待审核候选</p>
          <p className="text-3xl font-bold text-yellow-600">{pendingCount}</p>
          <p className="text-xs text-gray-400 mt-1">系统自动发现</p>
        </div>
        <div className="bg-white rounded-lg shadow p-5">
          <p className="text-sm text-gray-500 mb-1">高频候选</p>
          <p className="text-3xl font-bold text-orange-600">{(stats as any).high_frequency ?? '—'}</p>
          <p className="text-xs text-gray-400 mt-1">出现≥3次</p>
        </div>
      </div>

      {/* ── 知识体缺口常驻横幅（有缺口时才显示）─────────────────────────── */}
      {coverageReport && (coverageReport.ontology_missing.length > 0 || coverageReport.few_shot_low_coverage.length > 0) && (
        <div
          onClick={() => setTab('coverage')}
          className="flex items-center justify-between bg-amber-50 border border-amber-200 rounded-xl px-5 py-3 cursor-pointer hover:bg-amber-100 transition-colors"
        >
          <div className="flex items-center gap-3 text-sm flex-wrap">
            <span className="font-semibold text-amber-700">⚠️ 知识体缺口待处理</span>
            {coverageReport.ontology_missing.length > 0 && (
              <span className="bg-amber-100 border border-amber-300 text-amber-800 px-2.5 py-0.5 rounded-full text-xs font-medium">
                本体论缺框架 {coverageReport.ontology_missing.length} 个
              </span>
            )}
            {coverageReport.few_shot_low_coverage.length > 0 && (
              <span className="bg-blue-100 border border-blue-200 text-blue-700 px-2.5 py-0.5 rounded-full text-xs font-medium">
                Few-shot 弱覆盖 {coverageReport.few_shot_low_coverage.length} 个
              </span>
            )}
            {coverageReport.ontology_orphans.length > 0 && (
              <span className="bg-gray-100 border border-gray-200 text-gray-600 px-2.5 py-0.5 rounded-full text-xs">
                本体论孤儿 {coverageReport.ontology_orphans.length} 个
              </span>
            )}
          </div>
          <span className="text-xs text-amber-600 font-medium whitespace-nowrap ml-4">点击查看 →</span>
        </div>
      )}

      {/* Tab 切换 */}
      <div className="bg-white rounded-xl shadow overflow-hidden">
        <div className="flex border-b">
          {([
            { key: 'candidates', label: `候选审核`, badge: pendingCount > 0 ? pendingCount : null, badgeColor: 'bg-yellow-500' },
            { key: 'registry', label: '分类体系', badge: null, badgeColor: '' },
            {
              key: 'coverage',
              label: '知识体缺口',
              badge: coverageReport ? coverageReport.ontology_missing.length + coverageReport.few_shot_low_coverage.length : null,
              badgeColor: 'bg-red-500',
            },
          ] as { key: string; label: string; badge: number | null; badgeColor: string }[]).map(({ key, label, badge, badgeColor }) => (
            <button
              key={key}
              onClick={() => setTab(key as typeof tab)}
              className={`relative px-6 py-4 text-sm font-medium transition-colors ${
                tab === key
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {label}
              {badge !== null && badge > 0 && (
                <span className={`ml-2 ${badgeColor} text-white text-xs font-bold px-1.5 py-0.5 rounded-full`}>
                  {badge}
                </span>
              )}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <>
            {/* ── 候选审核 tab ────────────────────────────────────────────── */}
            {tab === 'candidates' && (
              <div className="p-6">
                {/* 状态筛选 */}
                <div className="flex gap-2 mb-4">
                  {['pending', 'approved', 'rejected'].map((s) => (
                    <button
                      key={s}
                      onClick={() => setStatusFilter(s)}
                      className={`px-3 py-1.5 text-xs rounded-full font-medium transition-colors ${
                        statusFilter === s
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {s === 'pending' ? '待审核' : s === 'approved' ? '已通过' : '已拒绝'}
                    </button>
                  ))}
                </div>

                {candidates.length === 0 ? (
                  <div className="text-center py-16 text-gray-400">
                    <div className="text-5xl mb-4">🎉</div>
                    <p>暂无{statusFilter === 'pending' ? '待审核' : ''}候选类型</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {candidates.map((c) => (
                      <div key={c.id} className="border rounded-xl p-5 hover:border-blue-200 transition-colors">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-3 mb-2">
                              <span className="font-mono text-sm bg-gray-100 px-2 py-0.5 rounded">
                                {c.type_id_suggestion}
                              </span>
                              <span className="font-semibold text-gray-900">{c.name_zh}</span>
                              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${confidenceColor(c.confidence_score)}`}>
                                {(c.confidence_score * 100).toFixed(0)}% 置信
                              </span>
                            </div>

                            <div className="flex flex-wrap gap-3 text-xs text-gray-500 mb-3">
                              <span>来源: {sourceLabel(c.source)}</span>
                              <span>出现: {c.occurrence_count} 次</span>
                              <span>创建: {new Date(c.created_at).toLocaleDateString('zh-CN')}</span>
                              {c.source_session_id && (
                                <span className="font-mono">会话: {c.source_session_id.slice(-8)}</span>
                              )}
                            </div>

                            {c.suggested_keywords.length > 0 && (
                              <div className="flex flex-wrap gap-1.5 mb-2">
                                {c.suggested_keywords.map((kw, i) => (
                                  <span key={i} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                                    {kw}
                                  </span>
                                ))}
                              </div>
                            )}

                            {c.sample_inputs.length > 0 && (
                              <p className="text-xs text-gray-400 truncate">
                                样例：{c.sample_inputs[0]}
                              </p>
                            )}
                          </div>

                          {c.review_status === 'pending' && (
                            <div className="flex gap-2 shrink-0">
                              <button
                                onClick={() => setApproveTarget(c)}
                                className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
                              >
                                审批
                              </button>
                              <button
                                onClick={() => handleReject(c.id)}
                                className="px-4 py-2 text-sm border border-red-300 text-red-600 rounded-lg hover:bg-red-50"
                              >
                                拒绝
                              </button>
                            </div>
                          )}
                          {c.review_status !== 'pending' && (
                            <span className={`text-xs px-3 py-1.5 rounded-full font-medium ${
                              c.review_status === 'approved'
                                ? 'bg-green-100 text-green-700'
                                : 'bg-red-100 text-red-700'
                            }`}>
                              {c.review_status === 'approved' ? '已通过' : '已拒绝'}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* ── 知识体缺口 tab ───────────────────────────────────────────── */}
            {tab === 'coverage' && (
              <div className="p-6 space-y-6">
                {coverageLoading ? (
                  <div className="flex justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500"></div>
                  </div>
                ) : !coverageReport ? (
                  <div className="text-center py-12 text-gray-400">暂无审计数据，刷新后重试</div>
                ) : (
                  <>
                    {/* 总体状态 */}
                    <div className="grid grid-cols-3 gap-4">
                      <div className="bg-gray-50 rounded-lg p-4 text-center">
                        <p className="text-2xl font-bold text-gray-800">{coverageReport.detector_count}</p>
                        <p className="text-xs text-gray-500 mt-1">检测器类型</p>
                      </div>
                      <div className={`rounded-lg p-4 text-center ${
                        coverageReport.ontology_missing.length > 0 ? 'bg-amber-50 border border-amber-200' : 'bg-green-50'
                      }`}>
                        <p className={`text-2xl font-bold ${
                          coverageReport.ontology_missing.length > 0 ? 'text-amber-700' : 'text-green-700'
                        }`}>
                          {coverageReport.ontology_count} / {coverageReport.detector_count}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">本体论框架覆盖</p>
                      </div>
                      <div className={`rounded-lg p-4 text-center ${
                        coverageReport.few_shot_low_coverage.length > 0 ? 'bg-blue-50 border border-blue-200' : 'bg-green-50'
                      }`}>
                        <p className={`text-2xl font-bold ${
                          coverageReport.few_shot_low_coverage.length > 0 ? 'text-blue-700' : 'text-green-700'
                        }`}>
                          {coverageReport.detector_count - coverageReport.few_shot_low_coverage.length} / {coverageReport.detector_count}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">Few-shot 充分覆盖</p>
                      </div>
                    </div>

                    {/* 本体论缺失 */}
                    {coverageReport.ontology_missing.length > 0 && (
                      <div className="border border-amber-200 rounded-xl overflow-hidden">
                        <div className="bg-amber-50 px-5 py-3 flex items-center justify-between">
                          <div>
                            <h3 className="font-semibold text-amber-800">📐 本体论框架缺失 ({coverageReport.ontology_missing.length} 个)</h3>
                            <p className="text-xs text-amber-600 mt-0.5">这些类型在 <code className="bg-amber-100 px-1 rounded">knowledge_base/ontology.yaml</code> 中没有框架，LLM 将退回通用框架（洞察深度下降）</p>
                          </div>
                        </div>
                        <div className="divide-y">
                          {coverageReport.ontology_missing.map((tid) => (
                            <div key={tid} className="px-5 py-3 flex items-center justify-between hover:bg-gray-50">
                              <code className="text-sm font-mono text-gray-800">{tid}</code>
                              <div className="text-xs text-gray-400 font-mono bg-gray-100 px-3 py-1.5 rounded ml-4 flex-1 max-w-lg">
                                {`KnowledgeCoverageAuditor.generate_ontology_draft('${tid}')`}
                                <span className="ml-2 text-gray-300">→ data/ontology_drafts/{tid}.yaml</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Few-shot 弱覆盖 */}
                    {coverageReport.few_shot_low_coverage.length > 0 && (
                      <div className="border border-blue-200 rounded-xl overflow-hidden">
                        <div className="bg-blue-50 px-5 py-3">
                          <h3 className="font-semibold text-blue-800">📋 Few-shot 弱覆盖 ({coverageReport.few_shot_low_coverage.length} 个)</h3>
                          <p className="text-xs text-blue-600 mt-0.5">这些类型在 <code className="bg-blue-100 px-1 rounded">config/prompts/few_shot_examples/examples_registry.yaml</code> 中缺少匹配标签，任务分解将退回 fallback 示例</p>
                        </div>
                        <div className="divide-y">
                          {coverageReport.few_shot_low_coverage.map((tid) => (
                            <div key={tid} className="px-5 py-3 flex items-center justify-between hover:bg-gray-50">
                              <code className="text-sm font-mono text-gray-800">{tid}</code>
                              <div className="text-xs text-gray-400 font-mono bg-gray-100 px-3 py-1.5 rounded ml-4 flex-1 max-w-lg">
                                {`KnowledgeCoverageAuditor.generate_few_shot_draft('${tid}')`}
                                <span className="ml-2 text-gray-300">→ data/few_shot_drafts/{tid}_registry_entry.yaml</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 本体论孤儿 */}
                    {coverageReport.ontology_orphans.length > 0 && (
                      <div className="border border-gray-200 rounded-xl overflow-hidden">
                        <div className="bg-gray-50 px-5 py-3">
                          <h3 className="font-semibold text-gray-700">🗑️ 本体论孤儿框架 ({coverageReport.ontology_orphans.length} 个)</h3>
                          <p className="text-xs text-gray-500 mt-0.5">ontology.yaml 里存在但检测器已不认识的旧类型 ID，可以考虑重命名或删除</p>
                        </div>
                        <div className="flex flex-wrap gap-2 px-5 py-3">
                          {coverageReport.ontology_orphans.map((tid) => (
                            <code key={tid} className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded">{tid}</code>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* 全部对齐时的庆祝状态 */}
                    {coverageReport.ontology_missing.length === 0 &&
                      coverageReport.few_shot_low_coverage.length === 0 &&
                      coverageReport.ontology_orphans.length === 0 && (
                      <div className="text-center py-12">
                        <div className="text-5xl mb-3">✅</div>
                        <p className="text-gray-600 font-medium">三层知识体系完全对齐</p>
                        <p className="text-sm text-gray-400 mt-1">检测器 / 本体论 / Few-shot 覆盖度一致</p>
                      </div>
                    )}

                    <div className="flex justify-end">
                      <button
                        onClick={fetchCoverage}
                        disabled={coverageLoading}
                        className="text-sm text-gray-500 hover:text-gray-700 underline"
                      >
                        重新检查
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* ── 当前分类体系 tab ─────────────────────────────────────────── */}
            {tab === 'registry' && (
              <div className="p-6">
                <p className="text-sm text-gray-500 mb-4">
                  内置类型（蓝色）定义在 <code className="bg-gray-100 px-1 rounded">services/project_type_detector.py</code> 中；
                  扩展类型（紫色）来自管理员审批，存储于 <code className="bg-gray-100 px-1 rounded">data/project_type_extensions.json</code>，可撤销。
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-xs text-gray-500 border-b">
                        <th className="pb-3 pr-4">类型 ID</th>
                        <th className="pb-3 pr-4">中文名</th>
                        <th className="pb-3 pr-4">优先级</th>
                        <th className="pb-3 pr-4">关键词数</th>
                        <th className="pb-3 pr-4">写入 Prompt</th>
                        <th className="pb-3">来源</th>
                        <th className="pb-3"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {types.map((t) => (
                        <tr key={t.type_id} className="hover:bg-gray-50">
                          <td className="py-3 pr-4 font-mono text-xs">{t.type_id}</td>
                          <td className="py-3 pr-4 font-medium">{t.name}</td>
                          <td className="py-3 pr-4">
                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                              t.priority >= 10 ? 'bg-red-100 text-red-700' :
                              t.priority >= 7 ? 'bg-orange-100 text-orange-700' :
                              'bg-gray-100 text-gray-600'
                            }`}>
                              P{t.priority}
                            </span>
                          </td>
                          <td className="py-3 pr-4 text-gray-600">{t.keyword_count}</td>
                          <td className="py-3 pr-4">
                            {t.include_in_prompt ? (
                              <span className="text-green-600">✓</span>
                            ) : (
                              <span className="text-gray-300">—</span>
                            )}
                          </td>
                          <td className="py-3 pr-4">
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              t.is_extension
                                ? 'bg-purple-100 text-purple-700'
                                : 'bg-blue-100 text-blue-700'
                            }`}>
                              {t.is_extension ? '扩展' : '内置'}
                            </span>
                          </td>
                          <td className="py-3 text-right">
                            {t.is_extension && (
                              <button
                                onClick={() => handleRevokeExtension(t.type_id)}
                                className="text-xs text-red-500 hover:text-red-700 hover:underline"
                              >
                                撤销
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* ── 审批弹窗 ───────────────────────────────────────────────────────── */}
      {approveTarget && (
        <ApproveModal
          candidate={approveTarget}
          onClose={() => setApproveTarget(null)}
          onDone={(hasGaps?: boolean) => {
            setApproveTarget(null);
            fetchData();
            fetchCoverage();
            if (hasGaps) setTab('coverage');
          }}
        />
      )}

      {/* ── 手动新增候选弹窗 ────────────────────────────────────────────────── */}
      {showAddForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg">
            <div className="p-6 border-b">
              <h3 className="text-xl font-bold text-gray-900">手动添加候选类型</h3>
            </div>
            <form onSubmit={handleAddCandidate} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">建议英文 ID *</label>
                  <input
                    type="text"
                    value={addForm.type_id_suggestion}
                    onChange={(e) => setAddForm({ ...addForm, type_id_suggestion: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm font-mono"
                    placeholder="如 auto_showroom"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">中文名 *</label>
                  <input
                    type="text"
                    value={addForm.name_zh}
                    onChange={(e) => setAddForm({ ...addForm, name_zh: e.target.value })}
                    className="w-full border rounded-lg px-3 py-2 text-sm"
                    placeholder="如 汽车展厅"
                    required
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">建议关键词（逗号分隔）</label>
                <input
                  type="text"
                  value={addForm.suggested_keywords}
                  onChange={(e) => setAddForm({ ...addForm, suggested_keywords: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  placeholder="如 汽车, 4S店, 新能源展示"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">说明</label>
                <input
                  type="text"
                  value={addForm.description}
                  onChange={(e) => setAddForm({ ...addForm, description: e.target.value })}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  placeholder="可选"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddForm(false)}
                  className="px-4 py-2 text-sm border rounded-lg hover:bg-gray-50"
                >
                  取消
                </button>
                <button
                  type="submit"
                  disabled={addLoading}
                  className="px-6 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {addLoading ? '提交中...' : '创建候选'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
